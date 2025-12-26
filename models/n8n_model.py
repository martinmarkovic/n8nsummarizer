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
    
    # Configuration
    DEFAULT_CHUNK_SIZE = 50000  # 50KB per chunk (safe for most webhook implementations)
    MAX_CHUNK_SIZE = 100000     # 100KB absolute maximum
    MIN_CHUNK_SIZE = 5000       # 5KB minimum to avoid too many requests
    
    def __init__(self, webhook_url: str = None, timeout: int = None, chunk_size: int = None):
        """
        Initialize n8n client with optional chunking.
        
        Args:
            webhook_url (str): Override default webhook URL from config
            timeout (int): Request timeout in seconds
            chunk_size (int): Characters per chunk (default: 50KB, max: 100KB)
        """
        self.webhook_url = webhook_url or N8N_WEBHOOK_URL
        self.timeout = timeout or N8N_TIMEOUT
        self.chunk_size = self._validate_chunk_size(chunk_size or self.DEFAULT_CHUNK_SIZE)
        self.last_response = None
        
        logger.info(f"N8NModel initialized with chunk_size={self.chunk_size} characters")
    
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
    
    def _split_into_chunks(self, content: str, overlap: int = 500) -> List[str]:
        """
        Split content into chunks with overlap for context preservation.
        
        Tries to split on paragraph boundaries (double newlines) when possible
        to maintain semantic structure.
        
        Args:
            content (str): Text to split
            overlap (int): Characters to overlap between chunks (for context)
            
        Returns:
            List[str]: List of content chunks
        """
        if len(content) <= self.chunk_size:
            return [content]
        
        chunks = []
        start = 0
        
        while start < len(content):
            # Calculate end position
            end = start + self.chunk_size
            
            if end >= len(content):
                # Last chunk - take everything remaining
                chunks.append(content[start:])
                break
            
            # Try to find paragraph boundary (double newline) before end
            paragraph_end = content.rfind('\n\n', start + self.chunk_size // 2, end)
            
            if paragraph_end != -1 and paragraph_end > start + self.chunk_size // 2:
                # Found good paragraph boundary
                end = paragraph_end + 2  # Include the double newline
                logger.debug(f"Chunk split at paragraph boundary (pos {end})")
            else:
                # No paragraph boundary, try sentence (newline)
                sentence_end = content.rfind('\n', start + self.chunk_size // 2, end)
                if sentence_end != -1 and sentence_end > start + self.chunk_size // 2:
                    end = sentence_end + 1
                    logger.debug(f"Chunk split at sentence boundary (pos {end})")
                else:
                    # No natural boundary, split at space
                    space_end = content.rfind(' ', start + self.chunk_size // 2, end)
                    if space_end != -1 and space_end > start + self.chunk_size // 2:
                        end = space_end + 1
                        logger.debug(f"Chunk split at space (pos {end})")
            
            # Add overlap from end of this chunk to start of next
            if start > 0:
                overlap_start = max(0, start - overlap)
                chunks.append(content[overlap_start:end])
            else:
                chunks.append(content[start:end])
            
            start = end - overlap  # Move start position considering overlap
        
        return chunks
    
    def send_content(self, file_name: str, content: str, 
                    metadata: dict = None) -> Tuple[bool, str, str]:
        """
        Send content to n8n for processing, with automatic chunking for large files.
        
        For files larger than chunk_size:
        1. Automatically splits into chunks
        2. Sends each chunk separately with position info
        3. Combines partial summaries into final output
        
        Args:
            file_name (str): Name of file
            content (str): Content to send
            metadata (dict): Optional metadata
            
        Returns:
            tuple: (success: bool, summary: str or None, error_msg: str or None)
            
        Example:
            >>> model = N8NModel()
            >>> # Large file is automatically chunked
            >>> success, summary, error = model.send_content(
            ...     'large_document.txt',
            ...     'Very long content...',
            ... )
        """
        content_size = len(content)
        
        # Log file size
        size_kb = content_size / 1024
        logger.info(f"Processing: {file_name} ({size_kb:.1f} KB, chunk_size={self.chunk_size} chars)")
        
        # Check if chunking is needed
        if content_size <= self.chunk_size:
            # Small file - send as is
            logger.debug(f"File size ({content_size}) within chunk limit, sending as single chunk")
            return self._send_single_chunk(file_name, content, metadata, chunk_number=None, total_chunks=None)
        
        # Large file - chunk and process
        logger.info(f"File exceeds chunk size, splitting into multiple chunks...")
        chunks = self._split_into_chunks(content)
        logger.info(f"Split into {len(chunks)} chunks")
        
        return self._send_chunked_content(file_name, chunks, metadata)
    
    def _send_single_chunk(self, file_name: str, content: str, metadata: dict = None,
                          chunk_number: int = None, total_chunks: int = None) -> Tuple[bool, str, str]:
        """
        Send a single chunk to n8n.
        
        v4.4.2: Handle empty responses correctly - empty doesn't mean failure!
        v4.4.3: Mark empty responses for filtering later
        
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
        
        Args:
            response_data: Response from n8n (dict, str, etc.)
            
        Returns:
            str: Extracted summary or stringified response. None if truly empty.
        """
        if response_data is None:
            logger.debug("Response is None")
            return None
        
        if isinstance(response_data, str):
            # Check if it's an empty string
            if response_data.strip() == "":
                logger.debug("Response is empty string")
                return None
            return response_data
        
        if isinstance(response_data, dict):
            # Try common keys first
            for key in ['summary', 'summarization', 'result', 'output', 'text', 'content']:
                if key in response_data:
                    value = response_data[key]
                    if isinstance(value, str):
                        if value.strip():
                            logger.debug(f"Found summary in key '{key}'")
                            return value
                    elif isinstance(value, dict):
                        logger.debug(f"Found dict summary in key '{key}'")
                        return json.dumps(value, indent=2)
                    else:
                        logger.debug(f"Found value in key '{key}': {type(value)}")
                        return str(value)
            
            # If no common keys, check if dict is empty
            if not response_data:
                logger.debug("Response dict is empty")
                return None
            
            # Return pretty-printed JSON if not empty
            logger.debug("Returning full response as JSON")
            return json.dumps(response_data, indent=2)
        
        # For other types, stringify
        str_response = str(response_data)
        if str_response.strip():
            return str_response
        else:
            logger.debug(f"Response is empty after stringification")
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
