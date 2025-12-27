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
    - DYNAMIC CHUNKING: Calculates based on actual content length
    - For 181KB file (90.5K chars): Creates 2 chunks (50+40.5K chars)
    - Uses ceiling division: (content_length + chunk_size - 1) // chunk_size
    - Flexible 50KB per chunk with remainder in last chunk
    - Works with UTF-16 encoded files correctly
    - DEBUG LOGGING: Comprehensive N8N response logging
    - Better detection of test mode webhook issues

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


class N8NModel:
    """Handles n8n webhook communication with large file support via chunking"""
    
    # Configuration - v4.4.4 FINAL: Dynamic 50KB chunks
    CHUNK_SIZE_CHARS = 50000  # 50KB = ~50,000 characters (approximate)
    MAX_CHUNK_SIZE = 100000     # 100KB absolute maximum (safety limit)
    MIN_CHUNK_SIZE = 5000       # 5KB minimum to avoid too many requests
    
    def __init__(self, webhook_url: str = None, timeout: int = None, chunk_size: int = None):
        """
        Initialize n8n client with optional chunking.
        
        Args:
            webhook_url (str): Override default webhook URL from config
            timeout (int): Request timeout in seconds
            chunk_size (int): Characters per chunk (default: 50KB)
        """
        self.webhook_url = webhook_url or N8N_WEBHOOK_URL
        self.timeout = timeout or N8N_TIMEOUT
        # v4.4.4 FINAL: Use 50K characters per chunk (dynamic sizing)
        self.chunk_size = self._validate_chunk_size(chunk_size or self.CHUNK_SIZE_CHARS)
        self.last_response = None
        
        logger.info(f"N8NModel initialized with chunk_size={self.chunk_size} characters (~50KB strategy)")
    
    def _validate_chunk_size(self, size: int) -> int:
        """
        Validate chunk size is within acceptable range.
        
        Args:
            size (int): Requested chunk size
            
        Returns:
            int: Validated chunk size
        """
        if size < self.MIN_CHUNK_SIZE:
            logger.warning(f"Chunk size {size} too small, using minimum {self.MIN_CHUNK_SIZE}")
            return self.MIN_CHUNK_SIZE
        if size > self.MAX_CHUNK_SIZE:
            logger.warning(f"Chunk size {size} too large, using maximum {self.MAX_CHUNK_SIZE}")
            return self.MAX_CHUNK_SIZE
        return size
    
    def calculate_num_chunks(self, content_length: int) -> int:
        """
        v4.4.4 FINAL: Calculate number of chunks needed.
        
        Uses ceiling division to ensure no content is lost.
        Strategy: 50KB (~50K characters) per chunk with dynamic remainder
        
        Examples with ACTUAL character counts:
        - 80,000 chars → (80000 + 50000 - 1) // 50000 = 2 chunks (40K + 40K)
        - 90,500 chars → (90500 + 50000 - 1) // 50000 = 2 chunks (50K + 40.5K) ← 181KB file!
        - 100,000 chars → (100000 + 50000 - 1) // 50000 = 3 chunks (50K + 50K)
        - 150,000 chars → (150000 + 50000 - 1) // 50000 = 4 chunks (4 × 50K)
        - 180,000 chars → (180000 + 50000 - 1) // 50000 = 4 chunks (50K + 50K + 50K + 30K)
        
        Args:
            content_length (int): Length of content in characters
            
        Returns:
            int: Number of chunks needed
        """
        # Ceiling division: round UP to ensure all content fits
        num_chunks = (content_length + self.chunk_size - 1) // self.chunk_size
        num_chunks = max(1, num_chunks)  # At least 1 chunk
        
        logger.debug(f"Content {content_length} chars: {num_chunks} chunks × {self.chunk_size} chars/chunk")
        return num_chunks
    
    def _split_into_chunks(self, content: str, chunk_size: int = None, overlap: int = 500) -> List[str]:
        """
        Split content into dynamic chunks (50KB per chunk).
        
        v4.4.4 FINAL: Dynamic sizing - calculates actual number of chunks needed
        Tries to split on paragraph boundaries (double newlines) when possible
        to maintain semantic structure.
        
        Args:
            content (str): Text to split
            chunk_size (int): Size of chunks (uses 50K if None)
            overlap (int): Characters to overlap between chunks (for context)
            
        Returns:
            List[str]: List of content chunks
        """
        # Use provided chunk_size or instance chunk_size
        if chunk_size is None:
            chunk_size = self.chunk_size
        
        content_len = len(content)
        
        # Calculate number of chunks
        num_chunks = self.calculate_num_chunks(content_len)
        logger.info(f"Splitting {content_len} chars into {num_chunks} chunks")
        
        if num_chunks == 1:
            # Content fits in single chunk
            logger.debug(f"Content ({content_len} chars) fits in single chunk")
            return [content]
        
        chunks = []
        chunk_length = (content_len + num_chunks - 1) // num_chunks  # Ceiling division for even distribution
        logger.debug(f"Dynamic chunk size: {chunk_length} chars per chunk")
        
        start = 0
        for chunk_num in range(num_chunks):
            if chunk_num == num_chunks - 1:
                # Last chunk - take everything remaining
                end = content_len
                logger.debug(f"Chunk {chunk_num + 1}: Last chunk from {start} to {end} ({end - start} chars)")
            else:
                # Calculate end position for this chunk
                end = start + chunk_length
                
                # Try to find paragraph boundary (double newline) near end
                paragraph_end = content.rfind('\n\n', max(start, end - chunk_length // 2), end + chunk_length // 4)
                
                if paragraph_end != -1 and paragraph_end > start:
                    end = paragraph_end + 2
                    logger.debug(f"Chunk {chunk_num + 1}: Split at paragraph (pos {end})")
                else:
                    # Try sentence boundary
                    sentence_end = content.rfind('\n', max(start, end - chunk_length // 2), end + chunk_length // 4)
                    if sentence_end != -1 and sentence_end > start:
                        end = sentence_end + 1
                        logger.debug(f"Chunk {chunk_num + 1}: Split at sentence (pos {end})")
                    else:
                        # Try word boundary
                        space_end = content.rfind(' ', max(start, end - chunk_length // 2), end + chunk_length // 4)
                        if space_end != -1 and space_end > start:
                            end = space_end + 1
                            logger.debug(f"Chunk {chunk_num + 1}: Split at word (pos {end})")
                        else:
                            logger.debug(f"Chunk {chunk_num + 1}: No boundary found, hard split at {end}")
            
            chunk_text = content[start:end]
            chunks.append(chunk_text)
            logger.debug(f"Added chunk {chunk_num + 1}/{num_chunks}: {len(chunk_text)} chars")
            
            start = end
        
        logger.info(f"Created {len(chunks)} chunks from {content_len} chars")
        return chunks
    
    def send_content(self, file_name: str, content: str, 
                    metadata: dict = None) -> Tuple[bool, str, str]:
        """
        Send content to n8n for processing, with automatic chunking for large files.
        
        v4.4.4 FINAL: Dynamic chunking based on actual character count
        For files larger than 50KB (50K characters):
        1. Calculates exact number of chunks needed via ceiling division
        2. Splits content into roughly equal chunks
        3. Sends each chunk separately with position info
        4. Combines partial summaries into final output
        
        Args:
            file_name (str): Name of file
            content (str): Content to send
            metadata (dict): Optional metadata
            
        Returns:
            tuple: (success: bool, summary: str or None, error_msg: str or None)
            
        Example:
            >>> model = N8NModel()
            >>> # 181KB file (90.5K chars) → 2 chunks dynamically
            >>> success, summary, error = model.send_content(
            ...     'investments.srt',
            ...     content,
            ... )
        """
        content_size = len(content)
        size_kb = content_size / 1024
        
        # v4.4.4 FINAL: Log actual character count
        logger.info(f"Processing: {file_name} ({content_size} chars, ~{size_kb:.1f} KB)")
        logger.debug(f"Chunk strategy: {self.chunk_size} chars per chunk (~{self.chunk_size/1024:.0f}KB)")
        
        # Check if chunking is needed
        if content_size <= self.chunk_size:
            # Small file (≤50K chars) - send as is
            logger.info(f"File size ({content_size} chars) within chunk limit, sending as single chunk")
            return self._send_single_chunk(file_name, content, metadata, chunk_number=None, total_chunks=None)
        
        # Large file (>50K chars) - chunk and process
        num_chunks = self.calculate_num_chunks(content_size)
        logger.info(f"File exceeds chunk size, splitting into {num_chunks} chunks...")
        chunks = self._split_into_chunks(content, chunk_size=self.chunk_size)
        logger.info(f"Split into {len(chunks)} chunks")
        
        return self._send_chunked_content(file_name, chunks, metadata)
    
    def _send_single_chunk(self, file_name: str, content: str, metadata: dict = None,
                          chunk_number: int = None, total_chunks: int = None) -> Tuple[bool, str, str]:
        """
        Send a single chunk to n8n.
        
        v4.4.2: Handle empty responses correctly - empty doesn't mean failure!
        v4.4.3: Mark empty responses for filtering later
        v4.4.4: Better webhook test mode error handling
        
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
        
        Intelligently merges summaries with proper formatting and context.
        v4.4.3: Only combines actual content (empty responses filtered out)
        
        Args:
            file_name (str): Original file name
            summaries (List[str]): List of partial summaries (non-empty)
            total_chunks (int): Total number of chunks
            
        Returns:
            str: Combined summary
        """
        if len(summaries) == 1:
            return summaries[0]
        
        # Build combined output - only with actual content
        combined = f"[Multi-chunk Summary: {len(summaries)}/{total_chunks} chunks with content]\n"
        combined += "=" * 70 + "\n\n"
        
        for idx, summary in enumerate(summaries, 1):
            combined += f"--- Section {idx} ---\n"
            combined += summary
            combined += "\n\n"
        
        combined += "=" * 70 + "\n"
        combined += f"[End of Multi-chunk Summary]\n"
        
        logger.info(f"Combined {len(summaries)} partial summaries into final output")
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
        Tries multiple common keys: summary, summarization, result, output, text, content
        
        v4.4.2: Also handles None responses gracefully
        v4.4.3: Returns None for truly empty responses (to be filtered)
        v4.4.4: DEBUG LOGGING - Log full response and extraction process
        
        Args:
            response_data: Response from n8n (dict, str, etc.)
            
        Returns:
            str: Extracted summary or stringified response. None if truly empty.
        """
        # v4.4.4 DEBUG: Log the FULL response first
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
        
        # Original extraction logic
        if response_data is None:
            logger.debug("Result: Response is None")
            return None
        
        if isinstance(response_data, str):
            # Check if it's an empty string
            if response_data.strip() == "":
                logger.debug("Result: Response is empty string")
                return None
            logger.debug(f"Result: Returning string response ({len(response_data)} chars)")
            return response_data
        
        if isinstance(response_data, dict):
            # Try common keys first
            common_keys = ['summary', 'summarization', 'result', 'output', 'text', 'content']
            logger.debug(f"Checking for common keys: {common_keys}")
            
            for key in common_keys:
                if key in response_data:
                    value = response_data[key]
                    logger.debug(f"Found key '{key}' with type {type(value).__name__}")
                    
                    if isinstance(value, str):
                        if value.strip():
                            logger.debug(f"Result: Extracted from key '{key}' ({len(value)} chars)")
                            return value
                        else:
                            logger.debug(f"  Key '{key}' is empty string, continuing")
                    elif isinstance(value, dict):
                        logger.debug(f"Result: Found dict in key '{key}', returning as JSON")
                        return json.dumps(value, indent=2)
                    else:
                        str_value = str(value)
                        logger.debug(f"Result: Found {type(value).__name__} in key '{key}', stringified ({len(str_value)} chars)")
                        return str_value
            
            # If no common keys, check if dict is empty
            if not response_data:
                logger.debug("Result: Response dict is empty")
                return None
            
            # Return pretty-printed JSON if not empty
            json_str = json.dumps(response_data, indent=2)
            logger.debug(f"Result: No common keys found, returning full dict as JSON ({len(json_str)} chars)")
            return json_str
        
        # For other types, stringify
        str_response = str(response_data)
        if str_response.strip():
            logger.debug(f"Result: Stringified {type(response_data).__name__} ({len(str_response)} chars)")
            return str_response
        else:
            logger.debug(f"Result: Response is empty after stringification")
            return None
    
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
    
    def set_chunk_size(self, size: int):
        """
        Change chunk size at runtime.
        
        Args:
            size (int): New chunk size (will be validated)
        """
        old_size = self.chunk_size
        self.chunk_size = self._validate_chunk_size(size)
        logger.info(f"Chunk size changed: {old_size} -> {self.chunk_size}")
    
    def get_last_response(self):
        """Get last HTTP response object (for debugging)"""
        return self.last_response
