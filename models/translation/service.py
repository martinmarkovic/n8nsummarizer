"""
Translation Service

Handles LM Studio/OpenAI-compatible API calls with retry logic and chunk management.
"""

import json
import time
from typing import Tuple, Optional, Dict, Any
import requests
from config import TRANSLATION_DEFAULT_URL, TRANSLATION_TIMEOUT
from utils.logger import logger


class TranslationService:
    """Handles translation API calls with retry and error handling."""

    def __init__(
        self, webhook_url: str = None, max_tokens: int = 70000, timeout: int = 300
    ):
        """
        Initialize translation service.

        Args:
            webhook_url: LM Studio/OpenAI-compatible endpoint
            max_tokens: Maximum tokens for each API call
            timeout: Request timeout in seconds
        """
        self.webhook_url = webhook_url or TRANSLATION_DEFAULT_URL
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.retry_count = 0
        self.max_retries = 3

    def translate_chunk(
        self,
        chunk: str,
        target_language: str,
        chunk_index: int = None,
        total_chunks: int = None,
        mode: str = "plain"
    ) -> Tuple[bool, str, Optional[str], Optional[Dict[str, Any]]]:
        """
        Translate a single chunk with retry logic.

        Args:
            chunk: Text chunk to translate
            target_language: Target language
            chunk_index: Current chunk index (for logging)
            total_chunks: Total number of chunks (for logging)

        Returns:
            Tuple of (success, translated_text, error, response_metadata)
        """
        if not chunk or not chunk.strip():
            return False, "", "Empty chunk provided", None

        if not self.webhook_url:
            return False, "", "Translation webhook URL not configured", None

        # Use local variable for max_tokens to avoid mutating instance state
        current_max_tokens = self.max_tokens

        # Build translation prompt based on mode
        if mode == "srt_text_only":
            # Specialized prompt for SRT text-only translation
            # Enhanced to be more explicit about marker preservation
            prompt_template = (
                "<|im_start|>system\n"
                "You are a subtitle translator. "
                "CRITICAL: Preserve ALL <Tn> markers exactly as they appear. "
                "Translate ONLY the text after each <Tn> marker. "
                "Keep every marker unchanged. "
                "Keep the same number of markers. "
                "Keep the same order of markers. "
                "Output MUST contain ALL markers from <T1> to the highest <Tn> in the input. "
                "Do not add explanations, notes, timestamps, numbering, or code fences. "
                "Do not omit any markers. "
                "Do not combine markers. "
                "Do not modify marker format.<|im_end|>\n"
                f"<|im_start|>user\nTranslate the following subtitle texts to {target_language}:\n{chunk}<|im_end|>\n"
                "<|im_start|>assistant\n"
            )
        else:
            # Plain text translation (existing behavior)
            prompt_template = (
                "<|im_start|>system\n"
                "You are a translator. Output ONLY the translated text. "
                "No explanations. No commentary. No extra content.<|im_end|>\n"
                f"<|im_start|>user\nTranslate to {target_language}:\n{chunk}<|im_end|>\n"
                "<|im_start|>assistant\n"
            )

        payload = {
            "prompt": prompt_template,
            "temperature": 0.3,
            "max_tokens": current_max_tokens,
            "stream": False,
        }

        # Add chunk metadata if available
        if chunk_index is not None and total_chunks is not None:
            payload["metadata"] = {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            }

        logger.info(
            f"Translating chunk {chunk_index}/{total_chunks} ({len(chunk)} chars, max_tokens={current_max_tokens})"
        )
        logger.debug(f"Translation payload: {json.dumps(payload, indent=2)[:500]}...")

        attempt = 1
        last_error = None

        while attempt <= self.max_retries:
            success, translated_text, error, metadata = self._make_translation_request(
                payload
            )

            if success:
                # Check for length-based completion
                finish_reason = metadata.get("finish_reason", "") if metadata else ""

                if finish_reason == "length":
                    logger.warning(
                        f"Chunk {chunk_index} hit token limit (finish_reason=length)"
                    )

                    # Retry with increased max_tokens if possible (local variable only)
                     if current_max_tokens < 70000 and attempt < self.max_retries:
                         old_tokens = current_max_tokens
                         current_max_tokens = min(current_max_tokens * 2, 70000)
                        logger.info(
                            f"Retrying chunk {chunk_index} with increased max_tokens: {old_tokens} -> {current_max_tokens}"
                        )
                        attempt += 1
                        self.retry_count += 1
                        continue
                    else:
                        return (
                            False,
                            translated_text,
                            f"Chunk {chunk_index} too large even with max_tokens={current_max_tokens}",
                            metadata,
                        )

                return True, translated_text, None, metadata

            # Handle specific errors that might be retryable
            if "timeout" in str(error).lower() or "connection" in str(error).lower():
                if attempt < self.max_retries:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Retryable error on chunk {chunk_index}, attempt {attempt}/{self.max_retries}: {error}"
                    )
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    attempt += 1
                    self.retry_count += 1
                    continue

            last_error = error
            attempt += 1
            self.retry_count += 1

        return (
            False,
            "",
            f"Failed after {self.max_retries} attempts: {last_error}",
            None,
        )

    def _make_translation_request(
        self, payload: Dict[str, Any]
    ) -> Tuple[bool, str, Optional[str], Optional[Dict[str, Any]]]:
        """Make actual HTTP request to translation API."""
        try:
            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=self.timeout,
            )

            logger.debug(f"Translation API response status: {response.status_code}")

            if response.status_code in [200, 201, 202]:
                response_data = response.json()

                # Extract translated text
                translated_text = ""
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    translated_text = response_data["choices"][0].get("text", "")
                elif "text" in response_data:
                    translated_text = response_data["text"]

                # Extract metadata
                metadata = {
                    "status_code": response.status_code,
                    "model": response_data.get("model", "unknown"),
                    "finish_reason": response_data.get("choices", [{}])[0].get(
                        "finish_reason", ""
                    )
                    if "choices" in response_data
                    else "",
                    "usage": response_data.get("usage", {}),
                }

                logger.info(
                    f"Translation successful, received {len(translated_text)} characters"
                )
                return True, translated_text, None, metadata
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"Translation API error: {error_msg}")
                return False, "", error_msg, None

        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {self.timeout}s"
            logger.error(error_msg)
            return False, "", error_msg, None

        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to translation service (LM Studio)"
            logger.error(error_msg)
            return False, "", error_msg, None

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response from translation service: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg, None

        except Exception as e:
            error_msg = f"Unexpected translation error: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg, None

    def get_retry_stats(self) -> Dict[str, int]:
        """Get retry statistics."""
        return {
            "total_retries": self.retry_count,
            "max_retries_per_chunk": self.max_retries,
        }

    def rebuild(self):
        """Reset retry statistics."""
        self.retry_count = 0

    def clean_translation_output(self, text: str) -> str:
        """
        Clean translation output by removing <think>...</think> blocks and
        normalising whitespace without destroying structural newlines used
        by the marker-based SRT decoder.

        Args:
            text: Translation text that may contain think tags

        Returns:
            Cleaned text with think blocks removed
        """
        import re as _re
        if not text:
            return text

        # Remove full <think>...</think> blocks (including their content)
        # These are reasoning traces emitted by models like Qwen-3 and DeepSeek
        cleaned = _re.sub(r'<think>[\s\S]*?</think>', '', text)

        # Remove any stray open/close think tags that weren't part of a complete block
        cleaned = cleaned.replace("<think>", "").replace("</think>", "")

        # Collapse runs of blank lines to a single newline, but preserve
        # meaningful newlines so the multi-line marker decoder still works
        cleaned = _re.sub(r'\n{3,}', '\n\n', cleaned)

        return cleaned.strip()
