"""LLM Client

OpenAI-compatible chat completions client.

Works with any server that implements POST /v1/chat/completions,
including LM Studio, Ollama (with openai compatibility), vLLM, Jan, and any
hosted OpenAI-compatible endpoint.

Features:
- Symmetric API with N8NModel for easy controller integration
- Automatic content chunking for large inputs
- Environment-based configuration
- Robust error handling and logging
"""

import requests
import re
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass

from .config import LLMClientConfig
from models.n8n.chunking import ContentChunker
from utils.logger import logger


class LLMClient:
    """OpenAI-compatible chat completions client.
    
    Works with any server that implements POST /v1/chat/completions,
    including LM Studio, Ollama (with openai compatibility), vLLM, Jan, and any
hosted OpenAI-compatible endpoint.
    """
    
    def __init__(
        self,
        webhook_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[int] = None,
        use_openai_format: Optional[bool] = None
    ) -> None:
        """Initialize LLMClient.
        
        Args:
            webhook_url: Optional webhook URL override
            model_name: Optional model name override
            timeout: Optional timeout override in seconds
            use_openai_format: Optional format override (True for OpenAI, False for simple prompt)
        """
        # Build configuration
        if webhook_url or model_name or timeout or use_openai_format:
            self.config = LLMClientConfig(
                webhook_url=webhook_url or LLMClientConfig.from_env().webhook_url,
                model_name=model_name or LLMClientConfig.from_env().model_name,
                timeout=timeout or LLMClientConfig.from_env().timeout,
                use_openai_format=use_openai_format if use_openai_format is not None else LLMClientConfig.from_env().use_openai_format
            )
        else:
            self.config = LLMClientConfig.from_env()
        
        # Reuse existing ContentChunker from n8n module
        self.chunker = ContentChunker(self.config.chunk_size_bytes)
        
        logger.info(
            f"LLMClient initialized with config: "
            f"webhook_url={self.config.webhook_url}, "
            f"model_name={self.config.model_name}, "
            f"timeout={self.config.timeout}s, "
            f"chunk_size={self.config.chunk_size_bytes} bytes"
        )
    
    def send_content(
        self,
        file_name: str,
        content: str,
        prompt: str,
        file_size_bytes: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send content to LLM with automatic chunking for large files.
        
        Same outer signature shape as N8NModel.send_content() for controller symmetry.
        
        Args:
            file_name: Name of the file being processed
            content: Text content to summarize
            prompt: Prompt template to use for summarization
            file_size_bytes: Optional file size in bytes for chunking
            metadata: Optional additional metadata
            
        Returns:
            Tuple of (success: bool, summary_text: Optional[str], error_msg: Optional[str])
        """
        content_len = len(content)
        
        # Estimate file size if not provided
        if file_size_bytes is None:
            file_size_bytes = content_len * 2  # Rough estimate: 2 bytes per char
            logger.warning(
                f"file_size_bytes not provided, estimating as "
                f"{file_size_bytes} bytes ({file_size_bytes/1024:.1f}KB)"
            )
        
        file_kb = file_size_bytes / 1024
        chunk_kb = self.config.chunk_size_bytes / 1024
        
        logger.info(f"LLM Processing: {file_name}")
        logger.info(f"  File size: {file_size_bytes} bytes ({file_kb:.1f}KB)")
        logger.info(f"  Content: {content_len} characters")
        logger.info(f"  Chunk strategy: {self.config.chunk_size_bytes} bytes ({chunk_kb:.0f}KB) per chunk")
        
        # Small file - send as single request
        if file_size_bytes <= self.config.chunk_size_bytes:
            logger.info(
                f"File size ({file_kb:.1f}KB) within chunk limit, sending as single chunk"
            )
            return self._send_single(content, prompt)
        
        # Large file - chunk and process
        num_chunks = self.chunker.calculate_num_chunks(file_size_bytes)
        logger.info(f"File exceeds chunk size, splitting into {num_chunks} chunks…")
        
        chunks = self.chunker.split_content(content, file_size_bytes)
        logger.info(f"Split into {len(chunks)} chunks")
        
        return self._send_chunked_content(chunks, prompt)
    
    def _send_single(
        self,
        content: str,
        prompt: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send a single chunk to LLM server.
        
        Args:
            content: Content chunk to process
            prompt: Prompt template to use
            
        Returns:
            Tuple of (success: bool, summary_text: Optional[str], error_msg: Optional[str])
        """
        if not self.config.webhook_url:
            error = "LLM webhook URL not configured"
            logger.error(error)
            return False, None, error
        
        try:
            # Simple approach like Translation tab - use URL exactly as provided
            endpoint = self.config.webhook_url.strip()
            
            # Standard request format (prompt-based for maximum compatibility)
            request_body = {
                "prompt": f"{prompt}\n\n{content}",
                "model": self.config.model_name,
                "stream": False
            }
            
            logger.info(f"Sending to LLM endpoint: {endpoint}")
            logger.debug(f"Request body: {request_body}")
            
            response = requests.post(
                endpoint,
                json=request_body,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            # Handle successful response with flexible parsing
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    
                    # Try multiple response formats (like Translation tab)
                    try:
                        # OpenAI chat format
                        summary = response_data["choices"][0]["message"]["content"]
                        # Strip <think>...</think> blocks produced by reasoning models
                        # (e.g. DeepSeek-R1, QwQ) before returning the clean response
                        summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL).strip()
                    except KeyError:
                         try:
                             # Text completion format
                             summary = response_data["choices"][0]["text"]
                             # Strip <think>...</think> blocks produced by reasoning models
                             # (e.g. DeepSeek-R1, QwQ) before returning the clean response
                             summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL).strip()
                         except KeyError:
                             try:
                                 # Simple response format
                                 summary = response_data["response"]
                                 # Strip <think>...</think> blocks produced by reasoning models
                                 # (e.g. DeepSeek-R1, QwQ) before returning the clean response
                                 summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL).strip()
                             except KeyError:
                                 # Fallback to first available text field
                                 if "choices" in response_data and len(response_data["choices"]) > 0:
                                     first_choice = response_data["choices"][0]
                                     if isinstance(first_choice, dict):
                                         for key, value in first_choice.items():
                                             if isinstance(value, str) and key in ["text", "content", "output", "result"]:
                                                 summary = value
                                                 # Strip <think>...</think> blocks produced by reasoning models
                                                 # (e.g. DeepSeek-R1, QwQ) before returning the clean response
                                                 summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL).strip()
                                                 break
                                 else:
                                     # Last resort: use raw response text
                                     summary = response.text
                                     # Strip <think>...</think> blocks produced by reasoning models
                                     # (e.g. DeepSeek-R1, QwQ) before returning the clean response
                                     summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL).strip()
                    
                    logger.info(f"Successfully received LLM response ({len(summary)} characters)")
                    return True, summary, None
                    
                except (IndexError, ValueError) as e:
                    error = f"Invalid LLM response format: {str(e)}. Response: {response.text[:200]}"
                    logger.error(error)
                    return False, None, error
            
            # Handle error responses
            error = f"LLM server returned {response.status_code}: {response.text[:200]}"
            logger.error(error)
            return False, None, error
            
        except requests.exceptions.Timeout:
            error = f"LLM request timeout (>{self.config.timeout}s)"
            logger.error(error)
            return False, None, error
            
        except requests.exceptions.ConnectionError as e:
            error = f"Cannot reach LLM server: {str(e)}"
            logger.error(error)
            return False, None, error
            
        except requests.exceptions.RequestException as e:
            error = f"LLM request failed: {str(e)}"
            logger.error(error)
            return False, None, error
            
        except Exception as e:
            error = f"Unexpected LLM error: {str(e)}"
            logger.error(error, exc_info=True)
            return False, None, error
    
    def _send_chunked_content(
        self,
        chunks: List[str],
        prompt: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send multiple chunks to LLM and combine results.
        
        Args:
            chunks: List of content chunks
            prompt: Prompt template to use
            
        Returns:
            Tuple of (success: bool, combined_summary: Optional[str], error_msg: Optional[str])
        """
        summaries: List[str] = []
        failed_chunks: List[Tuple[int, str]] = []
        
        total = len(chunks)
        for idx, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {idx}/{total} ({len(chunk)} chars)")
            
            success, summary, error = self._send_single(chunk, prompt)
            
            if success:
                if summary:
                    summaries.append(summary)
                    logger.info(f"Chunk {idx} completed successfully")
                else:
                    logger.warning(f"Chunk {idx} returned empty response")
            else:
                error_msg = error or "Unknown error"
                logger.error(f"Chunk {idx} failed: {error_msg}")
                failed_chunks.append((idx, error_msg))
        
        # Handle failures
        if failed_chunks:
            error_summary = ", ".join([f"Chunk {idx}: {msg}" for idx, msg in failed_chunks])
            logger.warning(f"{len(failed_chunks)}/{total} chunks failed - {error_summary}")
        
        # Return combined results or error
        if not summaries:
            if failed_chunks:
                error = f"Failed to get content from chunks: {len(failed_chunks)} failed"
                logger.error(error)
                return False, None, error
            else:
                # All chunks returned empty - this shouldn't happen but handle gracefully
                warning = f"All {total} chunks returned empty"
                logger.warning(warning)
                return True, "", None
        
        # Combine summaries with separator
        combined = "\n\n---\n\n".join(summaries)
        logger.info(f"Successfully extracted content from {len(summaries)}/{total} chunks")
        
        return True, combined, None
    
    def test_connection(self) -> bool:
        """Test connection to LLM server.
        
        Attempts to fetch available models from /v1/models endpoint.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            endpoint = f"{self.config.webhook_url.rstrip('/')}/v1/models"
            logger.info(f"Testing connection to LLM server: {endpoint}")
            
            response = requests.get(
                endpoint,
                timeout=5,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("LLM server connection test passed")
                return True
            else:
                logger.warning(f"LLM server returned unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"LLM connection test failed: {str(e)}")
            return False
    
    def save_settings_to_env(self, webhook_url: str, model_name: str) -> bool:
        """Save settings to .env file.
        
        Delegates to config.save_to_env() and updates internal config on success.
        
        Args:
            webhook_url: Webhook URL to save
            model_name: Model name to save
            
        Returns:
            True if save succeeded, False if failed
        """
        success = self.config.save_to_env(webhook_url, model_name)
        
        if success:
            # Update internal config to match saved values
            self.config.webhook_url = webhook_url
            self.config.model_name = model_name
            logger.info("Updated LLMClient config with saved settings")
        
        return success