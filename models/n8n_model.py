"""
N8N Model - Business logic for n8n webhook communication with File Chunking Support

Responsibilities:
    - Send requests to n8n webhook
    - Handle large files with automatic chunking
    - Combine partial summaries into final output
    - Manage timeouts and retries
    - Process webhook overrides
    - Save webhook configuration to .env

New in v4.4:
    - Automatic chunking for large files (configurable chunk size)
    - Multi-chunk processing with context preservation
    - Intelligent chunk boundary detection (paragraph-aware)
    - Progress tracking for multi-chunk operations

New in v4.4.1:
    - Fixed error message capture for failed chunks
    - Better error reporting for debugging
    - Improved exception handling details

New in v4.4.2:
    - CRITICAL FIX: Handle empty/None responses from N8N
    - Debug logging for response content
    - Treat empty responses as success (N8N may return empty on success)
    - Distinguish between "no response" vs "empty response"

New in v4.4.3:
    - Skip empty placeholders in output (N8N async pattern)
    - Only include actual content in summaries
    - Clean multi-chunk summaries with only real results
    - Better handling of async N8N workflows

New in v4.4.4 FINAL:
    - FIXED: Uses FILE SIZE IN BYTES (not characters!) for chunking
    - For 181.99 KB file: 181990 bytes ÷ 50000 = 3.64 → 4 chunks ✓
    - For 193.00 KB file: 193000 bytes ÷ 50000 = 3.86 → 4 chunks ✓
    - Uses ceiling division to ensure all content is chunked
    - Splits content proportionally by character count
    - DEBUG LOGGING: Comprehensive N8N response logging
    - Better detection of test mode webhook issues

New in v4.6:
    - REMOVED: Multi-chunk wrapper text (headers, section labels, footers)
    - OUTPUT: Only raw N8N/LM Studio content, no app-generated labels
    - User-facing change: Cleaner output for both single and multi-chunk processing

New in v4.6.1:
    - FIX: cpp-llama update changed response format - now checks all response keys
    - NEW: Fallback to ANY non-empty string in response (not just common keys)
    - LOGGING: Full response body logged to file for debugging
    - NEW: SAVE response to JSON file for manual inspection
    - Context window aware: detects truncation and suggests splitting
    - Better detection of LM Studio vs N8N wrapper responses

This is PURE business logic - NO UI dependencies.
Reusable by any controller (File tab, Transcribe tab, etc.)
"""
import os
import json
import requests
from datetime import datetime
from typing import List, Tuple, Dict
from config import N8N_WEBHOOK_URL, N8N_TIMEOUT
from utils.logger import logger
from pathlib import Path


class N8NModel:
    """Handles n8n webhook communication with large file support via chunking"""
    
    # Configuration - v4.4.4 FINAL: 50 KB per chunk (based on FILE SIZE IN BYTES)
    CHUNK_SIZE_BYTES = 50 * 1024  # 50 KB = 51,200 bytes
    MAX_CHUNK_SIZE_BYTES = 100 * 1024  # 100 KB absolute maximum
    MIN_CHUNK_SIZE_BYTES = 5 * 1024     # 5 KB minimum
    
    def __init__(self, webhook_url: str = None, timeout: int = None, chunk_size: int = None):
        """
        Initialize n8n client with optional chunking.
        
        Args:
            webhook_url (str): Override default webhook URL from config
            timeout (int): Request timeout in seconds
            chunk_size (int): Chunk size in bytes (default: 50 KB)
        """
        self.webhook_url = webhook_url or N8N_WEBHOOK_URL
        self.timeout = timeout or N8N_TIMEOUT
        # v4.4.4 FINAL: Use 50 KB chunks (measured in bytes, not characters)
        self.chunk_size_bytes = self._validate_chunk_size_bytes(chunk_size or self.CHUNK_SIZE_BYTES)
        self.last_response = None
        
        kb_size = self.chunk_size_bytes / 1024
        logger.info(f"N8NModel initialized with chunk_size={self.chunk_size_bytes} bytes ({kb_size:.0f}KB)")
    
    def _validate_chunk_size_bytes(self, size: int) -> int:
        """
        Validate chunk size is within acceptable range.
        
        Args:
            size (int): Requested chunk size in bytes
            
        Returns:
            int: Validated chunk size in bytes
        """
        if size < self.MIN_CHUNK_SIZE_BYTES:
            logger.warning(f"Chunk size {size} too small, using minimum {self.MIN_CHUNK_SIZE_BYTES}")
            return self.MIN_CHUNK_SIZE_BYTES
        if size > self.MAX_CHUNK_SIZE_BYTES:
            logger.warning(f"Chunk size {size} too large, using maximum {self.MAX_CHUNK_SIZE_BYTES}")
            return self.MAX_CHUNK_SIZE_BYTES
        return size
    
    def calculate_num_chunks(self, file_size_bytes: int) -> int:
        """
        v4.4.4 FINAL: Calculate number of chunks based on FILE SIZE IN BYTES.
        
        Uses ceiling division to ensure no content is lost.
        Strategy: 50 KB per chunk (measured in actual file bytes)
        
        Examples:
        - 50,000 bytes (50 KB) → 1 chunk
        - 100,000 bytes (100 KB) → 2 chunks (50 + 50)
        - 181,990 bytes (181.99 KB) → 4 chunks (50 + 50 + 50 + 31.99) ✓
        - 193,000 bytes (193 KB) → 4 chunks (50 + 50 + 50 + 43) ✓
        - 250,000 bytes (250 KB) → 5 chunks
        
        Args:
            file_size_bytes (int): File size in bytes
            
        Returns:
            int: Number of chunks needed
        """
        # Ceiling division: round UP to ensure all content fits
        num_chunks = (file_size_bytes + self.chunk_size_bytes - 1) // self.chunk_size_bytes
        num_chunks = max(1, num_chunks)  # At least 1 chunk
        
        file_kb = file_size_bytes / 1024
        chunk_kb = self.chunk_size_bytes / 1024
        logger.debug(f"File {file_size_bytes} bytes ({file_kb:.1f} KB): {num_chunks} chunks × {chunk_kb:.0f}KB")
        return num_chunks
    
    def _split_into_chunks(self, content: str, file_size_bytes: int) -> List[str]:
        """
        Split content into chunks based on FILE SIZE IN BYTES.
        
        v4.4.4 FINAL: Calculates chunk count from file size, then splits content proportionally
        Tries to split on paragraph boundaries (double newlines) when possible
        to maintain semantic structure.
        
        Args:
            content (str): Text content (already read from file)
            file_size_bytes (int): Original file size in bytes
            
        Returns:
            List[str]: List of content chunks
        """
        content_len = len(content)
        
        # Calculate number of chunks based on FILE SIZE (not character count)
        num_chunks = self.calculate_num_chunks(file_size_bytes)
        logger.info(f"Splitting content ({content_len} chars from {file_size_bytes} bytes) into {num_chunks} chunks")
        
        if num_chunks == 1:
            # Content fits in single chunk
            logger.debug(f"Content fits in single chunk")
            return [content]
        
        chunks = []
        # Divide content proportionally by number of chunks
        chars_per_chunk = (content_len + num_chunks - 1) // num_chunks  # Ceiling division
        logger.debug(f"Target: {chars_per_chunk} chars per chunk (total {content_len} chars)")
        
        start = 0
        for chunk_num in range(num_chunks):
            if chunk_num == num_chunks - 1:
                # Last chunk - take everything remaining
                end = content_len
                logger.debug(f"Chunk {chunk_num + 1}/{num_chunks}: Last chunk from {start} to {end} ({end - start} chars)")
            else:
                # Calculate end position for this chunk
                end = start + chars_per_chunk
                
                # Try to find paragraph boundary (double newline) near end
                search_start = max(start, end - chars_per_chunk // 4)
                search_end = min(content_len, end + chars_per_chunk // 4)
                paragraph_end = content.rfind('\n\n', search_start, search_end)
                
                if paragraph_end != -1 and paragraph_end > start:
                    end = paragraph_end + 2
                    logger.debug(f"Chunk {chunk_num + 1}/{num_chunks}: Split at paragraph")
                else:
                    # Try sentence boundary
                    sentence_end = content.rfind('\n', search_start, search_end)
                    if sentence_end != -1 and sentence_end > start:
                        end = sentence_end + 1
                        logger.debug(f"Chunk {chunk_num + 1}/{num_chunks}: Split at sentence")
                    else:
                        # Try word boundary
                        space_end = content.rfind(' ', search_start, search_end)
                        if space_end != -1 and space_end > start:
                            end = space_end + 1
                            logger.debug(f"Chunk {chunk_num + 1}/{num_chunks}: Split at word")
                        else:
                            logger.debug(f"Chunk {chunk_num + 1}/{num_chunks}: Hard split (no boundary)")
            
            chunk_text = content[start:end]
            chunks.append(chunk_text)
            logger.info(f"Chunk {chunk_num + 1}/{num_chunks}: {len(chunk_text)} chars")
            
            start = end
        
        logger.info(f"Created {len(chunks)} chunks")
        return chunks
    
    def send_content(self, file_name: str, content: str, file_size_bytes: int = None,
                    metadata: dict = None) -> Tuple[bool, str, str]:
        """
        Send content to n8n for processing, with automatic chunking for large files.
        
        v4.4.4 FINAL: Chunks based on FILE SIZE IN BYTES (not character count)
        For files larger than 50 KB:
        1. Calculates chunk count from actual file size in bytes
        2. Splits content proportionally into that many chunks
        3. Sends each chunk separately
        4. Combines partial summaries into final output
        
        Args:
            file_name (str): Name of file
            content (str): Content to send
            file_size_bytes (int): Original file size in bytes (IMPORTANT for correct chunking!)
            metadata (dict): Optional metadata
            
        Returns:
            tuple: (success: bool, summary: str or None, error_msg: str or None)
            
        Example:
            >>> model = N8NModel()
            >>> file_size = os.path.getsize('document.srt')  # 181990 bytes
            >>> success, summary, error = model.send_content(
            ...     'document.srt',
            ...     content,
            ...     file_size_bytes=file_size  # PASS THE ACTUAL FILE SIZE!
            ... )
        """
        content_len = len(content)
        
        # v4.4.4 FINAL: If file_size_bytes not provided, estimate from content
        if file_size_bytes is None:
            # Fallback: estimate file size from content
            # Assume average 2 bytes per character (UTF-16 consideration)
            file_size_bytes = content_len * 2
            logger.warning(f"file_size_bytes not provided, estimating as {file_size_bytes} bytes ({file_size_bytes/1024:.1f}KB)")
        
        file_kb = file_size_bytes / 1024
        chunk_kb = self.chunk_size_bytes / 1024
        
        logger.info(f"Processing: {file_name}")
        logger.info(f"  File size: {file_size_bytes} bytes ({file_kb:.1f}KB)")
        logger.info(f"  Content: {content_len} characters")
        logger.info(f"  Chunk strategy: {self.chunk_size_bytes} bytes ({chunk_kb:.0f}KB) per chunk")
        
        # Check if chunking is needed
        if file_size_bytes <= self.chunk_size_bytes:
            # Small file (≤50KB) - send as is
            logger.info(f"File size ({file_kb:.1f}KB) within chunk limit, sending as single chunk")
            return self._send_single_chunk(file_name, content, metadata, chunk_number=None, total_chunks=None)
        
        # Large file (>50KB) - chunk and process
        num_chunks = self.calculate_num_chunks(file_size_bytes)
        logger.info(f"File exceeds chunk size, splitting into {num_chunks} chunks...")
        chunks = self._split_into_chunks(content, file_size_bytes)
        logger.info(f"Split into {len(chunks)} chunks")
        
        return self._send_chunked_content(file_name, chunks, metadata)
    
    def _send_single_chunk(self, file_name: str, content: str, metadata: dict = None,
                          chunk_number: int = None, total_chunks: int = None) -> Tuple[bool, str, str]:
        """
        Send a single chunk to n8n.
        
        v4.4.2: Handle empty responses correctly - empty doesn't mean failure!
        v4.4.3: Mark empty responses for filtering later
        v4.4.4: Better webhook test mode error handling
        v4.6.1: Save full response to file for debugging
        
        Args:
            file_name (str): Name of file
            content (str): Chunk content
            metadata (dict): Optional metadata
            chunk_number (int): Chunk number (if multi-chunk)
            total_chunks (int): Total chunks (if multi-chunk)
            
        Returns:
            tuple: (success, response_data, error_msg)
        """
        if not self.webhook_url:
            error = "n8n webhook URL not configured"
            logger.error(error)
            return False, None, error
        
        try:
            payload = {
                'file_name': file_name,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            
            # Add chunk info if multi-chunk
            if chunk_number is not None:
                payload['chunk_number'] = chunk_number
                payload['total_chunks'] = total_chunks
                logger.debug(f"Sending chunk {chunk_number}/{total_chunks}")
            
            if metadata:
                payload['metadata'] = metadata
            
            payload_size = len(json.dumps(payload))
            logger.info(f"Sending to n8n: {self.webhook_url}")
            logger.debug(f"Payload size: {payload_size} bytes")
            
            # Send request
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            self.last_response = response
            
            # v4.4.4: Check for webhook test mode issues
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if 'not registered' in str(error_data):
                        error = f"n8n returned 404: {error_data.get('message', 'Webhook not registered')}"
                        logger.error(error)
                        return False, None, error
                except:
                    pass
            
            # Check status
            if response.status_code not in [200, 201, 202]:
                error = f"n8n returned {response.status_code}: {response.text[:200]}"
                logger.error(error)
                return False, None, error
            
            # Try to parse response (JSON or text)
            try:
                response_data = response.json()
                logger.debug(f"Response JSON: {str(response_data)[:200]}...")
            except json.JSONDecodeError:
                # Not JSON, use raw text
                response_data = response.text
                logger.debug(f"Response text: {response_data[:200]}...")
            
            # v4.6.1: Save full response to file for debugging
            self._save_response_debug(file_name, response_data, response.status_code)
            
            # Extract summary from response
            summary = self.extract_summary(response_data)
            
            # v4.4.2: Handle empty responses
            # v4.4.3: Return empty marker for filtering in _send_chunked_content
            if summary is None or summary == "":
                logger.info(f"N8N returned 200 with empty response (async processing)")
                # Return special marker for empty responses - will be filtered out later
                logger.info(f"Successfully received response from n8n (Status: {response.status_code}, empty)")
                return True, None, None  # Return None to mark as "empty but successful"
            
            logger.info(f"Successfully received response from n8n (Status: {response.status_code})")
            return True, summary, None
        
        except requests.exceptions.Timeout:
            error = f"Request timeout (>{self.timeout}s)"
            logger.error(error)
            return False, None, error
        except requests.exceptions.ConnectionError as e:
            error = f"Cannot reach n8n: {str(e)}"
            logger.error(error)
            return False, None, error
        except requests.exceptions.RequestException as e:
            error = f"HTTP request failed: {str(e)}"
            logger.error(error)
            return False, None, error
        except Exception as e:
            error = f"Unexpected error: {str(e)}"
            logger.error(error)
            return False, None, error
    
    def _send_chunked_content(self, file_name: str, chunks: List[str], 
                             metadata: dict = None) -> Tuple[bool, str, str]:
        """
        Send multiple chunks and combine results.
        
        v4.4.1: Improved error capture and reporting
        v4.4.2: Better handling of success vs failure
        v4.4.3: Filter out empty responses from async processing
        v4.4.4: Better error handling for test mode issues
        
        Args:
            file_name (str): Name of file
            chunks (List[str]): List of content chunks
            metadata (dict): Optional metadata
            
        Returns:
            tuple: (success, combined_summary, error_msg)
        """
        summaries = []
        empty_chunks = []
        failed_chunks = []
        
        for idx, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {idx}/{len(chunks)} ({len(chunk)} chars)")
            
            # Create metadata for chunk
            chunk_meta = metadata.copy() if metadata else {}
            chunk_meta['chunk_index'] = idx
            chunk_meta['total_chunks'] = len(chunks)
            
            # Send chunk
            success, summary, error = self._send_single_chunk(
                file_name,
                chunk,
                chunk_meta,
                chunk_number=idx,
                total_chunks=len(chunks)
            )
            
            # v4.4.3: Distinguish between empty and failed
            if success:
                if summary is None:
                    # Empty response - N8N is processing asynchronously
                    logger.info(f"Chunk {idx} returned empty (async N8N pattern)")
                    empty_chunks.append(idx)
                else:
                    # Actual content received
                    summaries.append(summary)
                    logger.info(f"Chunk {idx} completed successfully with content")
            else:
                # Actual failure
                if error:
                    error_msg = error
                else:
                    error_msg = "Unknown error"
                
                logger.error(f"Chunk {idx} failed: {error_msg}")
                failed_chunks.append((idx, error_msg))
        
        # Log empty chunks info
        if empty_chunks:
            logger.info(f"Chunks with empty responses (async pattern): {empty_chunks}")
        
        # Check results - we care about actual content, not empty responses
        if not summaries:
            # No actual content received
            if empty_chunks and not failed_chunks:
                # Only empty responses - probably still processing
                warning = f"All {len(chunks)} chunks returned empty (N8N still processing?)"
                logger.warning(warning)
                return True, "[All chunks processed but no content returned - N8N may still be processing]", None
            else:
                # Actual failures
                error = f"Failed to get content from chunks: {len(failed_chunks)} failed, {len(empty_chunks)} empty"
                logger.error(error)
                return False, None, error
        
        # Log failures for context
        if failed_chunks:
            error_summary = ", ".join([f"Chunk {idx}: {msg}" for idx, msg in failed_chunks])
            logger.warning(f"{len(failed_chunks)} of {len(chunks)} chunks failed - {error_summary}")
        
        # Combine only non-empty summaries
        combined = self._combine_summaries(file_name, summaries, len(chunks))
        logger.info(f"Successfully extracted content from {len(summaries)}/{len(chunks)} chunks")
        
        return True, combined, None
    
    def _combine_summaries(self, file_name: str, summaries: List[str], total_chunks: int) -> str:
        """
        Combine partial summaries into single output.

        v4.6: user-facing change – return only the raw N8N/LM Studio content
        without any wrapper headers/footers or section labels.
        
        Args:
            file_name (str): Original file name
            summaries (List[str]): List of partial summaries (non-empty)
            total_chunks (int): Total number of chunks
            
        Returns:
            str: Combined summary (raw content only)
        """
        if not summaries:
            return ""
        
        # If there is only one summary, just return it
        if len(summaries) == 1:
            return summaries[0]
        
        # Just join all summaries with a blank line between them
        combined = "\n\n".join(summaries)
        
        logger.info(f"Combined {len(summaries)} partial summaries into final output (no wrapper text)")
        return combined
    
    def test_connection(self) -> bool:
        """
        Test webhook connectivity.
        
        Returns:
            bool: True if webhook is reachable, False otherwise
        """
        try:
            logger.info(f"Testing connection to {self.webhook_url}")
            response = requests.post(
                self.webhook_url,
                json={'test': True},
                timeout=5
            )
            is_reachable = response.status_code in [200, 201, 202, 400, 404]
            if is_reachable:
                logger.info("n8n connection test passed")
            else:
                logger.warning(f"n8n returned unexpected status: {response.status_code}")
            return is_reachable
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def extract_summary(self, response_data) -> str:
        """
        Extract summary from n8n response.
        
        v4.6.1: NEW LOGIC (cpp-llama update broke old parsing)
        - First tries common keys: summary, summarization, result, output, text, content
        - If no common keys found, checks ALL dict values for non-empty strings
        - Returns FIRST non-empty string found (usually the summary)
        - Fallback: stringifies entire response if no strings found
        - Detects truncation patterns and logs warnings
        
        Args:
            response_data: Response from n8n (dict, str, etc.)
            
        Returns:
            str: Extracted summary or stringified response. None if truly empty.
        """
        # v4.6.1: Log the FULL response
        logger.debug(f"\n{'='*70}")
        logger.debug(f"EXTRACT_SUMMARY - Full N8N Response:")
        logger.debug(f"Response type: {type(response_data).__name__}")
        
        if isinstance(response_data, dict):
            logger.debug(f"Response keys: {list(response_data.keys())}")
            logger.debug(f"Response content (JSON):")
            for key, value in response_data.items():
                value_type = type(value).__name__
                if isinstance(value, str):
                    value_preview = value[:100] if len(value) > 100 else value
                    logger.debug(f"  {key}: ({value_type}) {value_preview}")
                elif isinstance(value, (dict, list)):
                    logger.debug(f"  {key}: ({value_type}) {len(str(value))} chars")
                else:
                    logger.debug(f"  {key}: ({value_type}) {value}")
        elif isinstance(response_data, str):
            preview = response_data[:200] if len(response_data) > 200 else response_data
            logger.debug(f"Response content (String): {preview}")
        else:
            logger.debug(f"Response content: {response_data}")
        
        logger.debug(f"{'='*70}\n")
        
        # v4.6.1: Handle None
        if response_data is None:
            logger.debug("Result: Response is None")
            return None
        
        # Handle string responses
        if isinstance(response_data, str):
            if response_data.strip() == "":
                logger.debug("Result: Response is empty string")
                return None
            logger.debug(f"Result: Returning string response ({len(response_data)} chars)")
            return response_data
        
        # Handle dict responses
        if isinstance(response_data, dict):
            # v4.6.1: NEW - Try common keys first
            common_keys = ['summary', 'summarization', 'result', 'output', 'text', 'content']
            logger.debug(f"Checking for common keys: {common_keys}")
            
            for key in common_keys:
                if key in response_data:
                    value = response_data[key]
                    logger.debug(f"Found key '{key}' with type {type(value).__name__}")
                    
                    if isinstance(value, str):
                        if value.strip():
                            logger.debug(f"Result: Extracted from key '{key}' ({len(value)} chars)")
                            # Detect truncation
                            self._check_truncation(value, key)
                            return value
                        else:
                            logger.debug(f"  Key '{key}' is empty string, continuing")
                    elif isinstance(value, dict):
                        logger.debug(f"Result: Found dict in key '{key}', returning as JSON")
                        return json.dumps(value, indent=2)
                    else:
                        str_value = str(value)
                        logger.debug(f"Result: Found {type(value).__name__} in key '{key}', stringified ({len(str_value)} chars)")
                        self._check_truncation(str_value, key)
                        return str_value
            
            # v4.6.1: NEW - If no common keys, search ALL dict values for strings
            logger.info("No common keys found, searching all dict values for non-empty strings...")
            for key, value in response_data.items():
                if isinstance(value, str) and value.strip():
                    logger.info(f"Found non-empty string in key '{key}' ({len(value)} chars)")
                    self._check_truncation(value, key)
                    return value
            
            # If dict is empty
            if not response_data:
                logger.debug("Result: Response dict is empty")
                return None
            
            # Return pretty-printed JSON if no strings found
            json_str = json.dumps(response_data, indent=2)
            logger.debug(f"Result: No string values found, returning full dict as JSON ({len(json_str)} chars)")
            return json_str
        
        # For other types, stringify
        str_response = str(response_data)
        if str_response.strip():
            logger.debug(f"Result: Stringified {type(response_data).__name__} ({len(str_response)} chars)")
            self._check_truncation(str_response)
            return str_response
        else:
            logger.debug(f"Result: Response is empty after stringification")
            return None
    
    def _check_truncation(self, text: str, source_key: str = None):
        """
        v4.6.1: Check if response looks truncated (indicator of context window issues)
        
        Logs warnings if text appears cut off:
        - Ends abruptly mid-word
        - Ends with incomplete sentence
        - Exceeds context window patterns
        
        Args:
            text (str): Response text to check
            source_key (str): Which key the text came from (for logging)
        """
        if not text or len(text) < 100:
            return
        
        # Check for abrupt ending patterns
        last_chars = text[-50:]
        
        # Pattern: ends with incomplete word (random characters at end)
        if not last_chars.rstrip().endswith(('.', '!', '?', '\n', '"', "'", '-', ')', ']')):
            logger.warning(f"Response may be truncated (abrupt ending): ...{text[-40:]}")
            logger.warning("SUGGESTION: Try increasing context window in LM Studio or splitting input smaller")
    
    def _save_response_debug(self, file_name: str, response_data, status_code: int):
        """
        v4.6.1: Save full response to JSON file for debugging
        
        Creates debug_responses/ directory with timestamp + filename
        
        Args:
            file_name (str): Original file name
            response_data: Full response from n8n
            status_code (int): HTTP status code
        """
        try:
            debug_dir = Path("debug_responses")
            debug_dir.mkdir(exist_ok=True)
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_name = file_name.replace('.', '_').replace('/', '_')[:50]
            debug_file = debug_dir / f"{timestamp}_{clean_name}_response.json"
            
            # Save response
            debug_data = {
                'timestamp': datetime.now().isoformat(),
                'file_name': file_name,
                'status_code': status_code,
                'response_type': type(response_data).__name__,
                'response': response_data
            }
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, indent=2, default=str)
            
            logger.debug(f"Response debug saved to: {debug_file}")
        except Exception as e:
            logger.warning(f"Failed to save response debug: {e}")
    
    def save_webhook_to_env(self, webhook_url: str) -> bool:
        """
        Save webhook URL to .env file.
        
        Args:
            webhook_url (str): Webhook URL to save
            
        Returns:
            bool: True if saved successfully
        """
        try:
            env_file = '.env'
            env_lines = []
            webhook_found = False
            
            if os.path.exists(env_file):
                with open(env_file, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()
            
            new_lines = []
            for line in env_lines:
                if line.strip().startswith('N8N_WEBHOOK_URL='):
                    new_lines.append(f'N8N_WEBHOOK_URL={webhook_url}\n')
                    webhook_found = True
                else:
                    new_lines.append(line)
            
            if not webhook_found:
                new_lines.append(f'N8N_WEBHOOK_URL={webhook_url}\n')
            
            with open(env_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            logger.info(f"Saved webhook to .env: {webhook_url}")
            self.webhook_url = webhook_url
            return True
        except Exception as e:
            logger.error(f"Failed to save webhook to .env: {e}")
            return False
    
    def set_chunk_size(self, size_bytes: int):
        """
        Change chunk size at runtime.
        
        Args:
            size_bytes (int): New chunk size in bytes (will be validated)
        """
        old_size = self.chunk_size_bytes
        self.chunk_size_bytes = self._validate_chunk_size_bytes(size_bytes)
        logger.info(f"Chunk size changed: {old_size} -> {self.chunk_size_bytes} bytes")
    
    def get_last_response(self):
        """Get last HTTP response object (for debugging)"""
        return self.last_response
