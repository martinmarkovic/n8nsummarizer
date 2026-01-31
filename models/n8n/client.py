"""N8N webhook client for sending content to n8n workflows.

This is the high-level client used by controllers. It delegates
chunking and response parsing to helper components while keeping
backwards-compatible behaviour with the original N8NModel.
"""

import os
from typing import Optional, Tuple, Dict, List

import requests
from datetime import datetime

from config import N8N_WEBHOOK_URL, N8N_TIMEOUT
from utils.logger import logger

from .config import ChunkConfig
from .chunking import ContentChunker
from .response_parser import ResponseParser


class N8NModel:
    """Main n8n webhook communication client.

    This class preserves the original public API of models/n8n_model.py
    while delegating responsibilities to:
      • ChunkConfig    – configuration & validation
      • ContentChunker – file/content splitting
      • ResponseParser – summary extraction & combination
    """

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        timeout: Optional[int] = None,
        chunk_size: Optional[int] = None,
    ) -> None:
        self.config = ChunkConfig(
            webhook_url=webhook_url or N8N_WEBHOOK_URL,
            timeout=timeout or N8N_TIMEOUT,
            chunk_size_bytes=chunk_size,
        )

        self.chunker = ContentChunker(self.config.chunk_size_bytes)
        self.parser = ResponseParser()
        self.last_response: Optional[requests.Response] = None

        kb_size = self.config.chunk_size_bytes / 1024
        logger.info(
            f"N8NModel initialized with chunk_size={self.config.chunk_size_bytes} bytes ({kb_size:.0f}KB)"
        )

    # ------------------------------------------------------------------
    # Public API – kept compatible with original implementation
    # ------------------------------------------------------------------

    def send_content(
        self,
        file_name: str,
        content: str,
        file_size_bytes: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send content to n8n with automatic chunking for large files.

        Behaviour is equivalent to the original send_content method:
        - Small files (≤ chunk_size) → one request
        - Large files               → split into N chunks
        - Multi-chunk responses are combined into a single string
        """

        content_len = len(content)

        if file_size_bytes is None:
            # Fallback estimate from content length (kept from original)
            file_size_bytes = content_len * 2
            logger.warning(
                "file_size_bytes not provided, estimating as "
                f"{file_size_bytes} bytes ({file_size_bytes/1024:.1f}KB)"
            )

        file_kb = file_size_bytes / 1024
        chunk_kb = self.config.chunk_size_bytes / 1024

        logger.info(f"Processing: {file_name}")
        logger.info(f"  File size: {file_size_bytes} bytes ({file_kb:.1f}KB)")
        logger.info(f"  Content: {content_len} characters")
        logger.info(
            f"  Chunk strategy: {self.config.chunk_size_bytes} bytes ({chunk_kb:.0f}KB) per chunk"
        )

        # Small file – send as a single request
        if file_size_bytes <= self.config.chunk_size_bytes:
            logger.info(
                f"File size ({file_kb:.1f}KB) within chunk limit, sending as single chunk"
            )
            return self._send_single_chunk(
                file_name=file_name,
                content=content,
                metadata=metadata,
                chunk_number=None,
                total_chunks=None,
            )

        # Large file – chunk and process
        num_chunks = self.chunker.calculate_num_chunks(file_size_bytes)
        logger.info(f"File exceeds chunk size, splitting into {num_chunks} chunks…")

        chunks = self.chunker.split_content(content, file_size_bytes)
        logger.info(f"Split into {len(chunks)} chunks")

        return self._send_chunked_content(file_name, chunks, metadata)

    def test_connection(self) -> bool:
        """Test webhook connectivity.

        Returns True if the webhook is reachable and returns a status code
        in the typical success range (200/201/202/400/404) – behaviour
        preserved from the previous implementation.
        """

        try:
            logger.info(f"Testing connection to {self.config.webhook_url}")
            response = requests.post(
                self.config.webhook_url,
                json={"test": True},
                timeout=5,
            )
            is_reachable = response.status_code in [200, 201, 202, 400, 404]
            if is_reachable:
                logger.info("n8n connection test passed")
            else:
                logger.warning(
                    f"n8n returned unexpected status during test: {response.status_code}"
                )
            return is_reachable
        except Exception as e:  # noqa: BLE001 – propagate as False
            logger.error(f"Connection test failed: {str(e)}")
            return False

    def save_webhook_to_env(self, webhook_url: str) -> bool:
        """Proxy helper to persist webhook URL to .env via configuration."""

        ok = self.config.save_webhook_to_env(webhook_url)
        if ok:
            self.config.webhook_url = webhook_url
        return ok

    def set_chunk_size(self, size_bytes: int) -> None:
        """Change chunk size at runtime with validation.

        This mirrors the original behaviour but delegates the validation
        to :class:`ChunkConfig`.
        """

        old_size = self.config.chunk_size_bytes
        self.config.chunk_size_bytes = self.config.validate_chunk_size_bytes(size_bytes)
        self.chunker.chunk_size_bytes = self.config.chunk_size_bytes
        logger.info(f"Chunk size changed: {old_size} -> {self.config.chunk_size_bytes} bytes")

    def get_last_response(self) -> Optional[requests.Response]:
        """Return the last raw HTTP response object (for debugging)."""

        return self.last_response

    # ------------------------------------------------------------------
    # Internal helpers – adapted from original implementation
    # ------------------------------------------------------------------

    def _send_single_chunk(
        self,
        file_name: str,
        content: str,
        metadata: Optional[Dict] = None,
        chunk_number: Optional[int] = None,
        total_chunks: Optional[int] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send a single chunk to n8n.

        Preserves all behaviours from the previous implementation:
        - HTTP error handling
        - Empty-but-successful responses
        - Summary extraction via ResponseParser
        """

        if not self.config.webhook_url:
            error = "n8n webhook URL not configured"
            logger.error(error)
            return False, None, error

        try:
            payload: Dict[str, object] = {
                "file_name": file_name,
                "content": content,
                "timestamp": datetime.now().isoformat(),
            }

            if chunk_number is not None:
                payload["chunk_number"] = chunk_number
                payload["total_chunks"] = total_chunks
                logger.debug(f"Sending chunk {chunk_number}/{total_chunks}")

            if metadata:
                payload["metadata"] = metadata

            logger.info(f"Sending to n8n: {self.config.webhook_url}")

            response = requests.post(
                self.config.webhook_url,
                json=payload,
                timeout=self.config.timeout,
                headers={"Content-Type": "application/json"},
            )

            self.last_response = response

            # Special handling for webhook test mode 404s kept from original
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    if "not registered" in str(error_data):
                        error = (
                            "n8n returned 404: "
                            f"{error_data.get('message', 'Webhook not registered')}"
                        )
                        logger.error(error)
                        return False, None, error
                except Exception:  # noqa: BLE001
                    pass

            if response.status_code not in [200, 201, 202]:
                error = f"n8n returned {response.status_code}: {response.text[:200]}"
                logger.error(error)
                return False, None, error

            # Parse response – JSON preferred, fallback to text
            try:
                response_data: object = response.json()
                logger.debug(f"Response JSON: {str(response_data)[:200]}…")
            except Exception:  # noqa: BLE001
                response_data = response.text
                logger.debug(f"Response text: {str(response_data)[:200]}…")

            summary = self.parser.extract_summary(response_data)

            # Empty-but-successful responses (async pattern)
            if summary is None or summary == "":
                logger.info(
                    "N8N returned 200 with empty response (async processing pattern)"
                )
                return True, None, None

            logger.info(
                f"Successfully received response from n8n (Status: {response.status_code})"
            )
            return True, summary, None

        except requests.exceptions.Timeout:
            error = f"Request timeout (>{self.config.timeout}s)"
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
        except Exception as e:  # noqa: BLE001
            error = f"Unexpected error: {str(e)}"
            logger.error(error)
            return False, None, error

    def _send_chunked_content(
        self,
        file_name: str,
        chunks: List[str],
        metadata: Optional[Dict] = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Send multiple chunks to n8n and combine non-empty results."""

        summaries: List[str] = []
        empty_chunks: List[int] = []
        failed_chunks: List[Tuple[int, str]] = []

        total = len(chunks)
        for idx, chunk in enumerate(chunks, 1):
            logger.info(f"Processing chunk {idx}/{total} ({len(chunk)} chars)")

            chunk_meta = dict(metadata or {})
            chunk_meta["chunk_index"] = idx
            chunk_meta["total_chunks"] = total

            success, summary, error = self._send_single_chunk(
                file_name=file_name,
                content=chunk,
                metadata=chunk_meta,
                chunk_number=idx,
                total_chunks=total,
            )

            if success:
                if summary is None:
                    logger.info(
                        f"Chunk {idx} returned empty (async N8N pattern – treated as success)"
                    )
                    empty_chunks.append(idx)
                else:
                    summaries.append(summary)
                    logger.info(f"Chunk {idx} completed successfully with content")
            else:
                error_msg = error or "Unknown error"
                logger.error(f"Chunk {idx} failed: {error_msg}")
                failed_chunks.append((idx, error_msg))

        if empty_chunks:
            logger.info(
                f"Chunks with empty responses (async pattern): {empty_chunks}"
            )

        if not summaries:
            if empty_chunks and not failed_chunks:
                warning = (
                    f"All {total} chunks returned empty (N8N still processing?)"
                )
                logger.warning(warning)
                return True,
                "[All chunks processed but no content returned - N8N may still be processing]",
                None

            error = (
                "Failed to get content from chunks: "
                f"{len(failed_chunks)} failed, {len(empty_chunks)} empty"
            )
            logger.error(error)
            return False, None, error

        if failed_chunks:
            error_summary = ", ".join(
                [f"Chunk {idx}: {msg}" for idx, msg in failed_chunks]
            )
            logger.warning(
                f"{len(failed_chunks)} of {total} chunks failed - {error_summary}"
            )

        combined = self.parser.combine_summaries(file_name, summaries, total)
        logger.info(
            f"Successfully extracted content from {len(summaries)}/{total} chunks"
        )

        return True, combined, None
