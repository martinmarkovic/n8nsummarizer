"""Configuration helpers for N8NModel and chunking.

This module centralises configuration values and validation logic that
were previously embedded directly in the monolithic n8n_model.py file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from utils.logger import logger


@dataclass
class ChunkConfig:
    """Configuration container for N8N chunked processing.

    The defaults mirror the original implementation:
    - 50 KB per chunk
    - 5 KB minimum
    - 100 KB maximum
    """

    webhook_url: str
    timeout: int
    chunk_size_bytes: int

    # Default limits (kept from original constants)
    DEFAULT_CHUNK_SIZE_BYTES: int = 50 * 1024
    MAX_CHUNK_SIZE_BYTES: int = 100 * 1024
    MIN_CHUNK_SIZE_BYTES: int = 5 * 1024

    def __init__(
        self,
        webhook_url: str,
        timeout: int,
        chunk_size_bytes: Optional[int] = None,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.chunk_size_bytes = self.validate_chunk_size_bytes(
            chunk_size_bytes or self.DEFAULT_CHUNK_SIZE_BYTES
        )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def validate_chunk_size_bytes(self, size: int) -> int:
        """Validate and clamp chunk size within acceptable range."""

        if size < self.MIN_CHUNK_SIZE_BYTES:
            logger.warning(
                "Chunk size %s too small, using minimum %s",
                size,
                self.MIN_CHUNK_SIZE_BYTES,
            )
            return self.MIN_CHUNK_SIZE_BYTES

        if size > self.MAX_CHUNK_SIZE_BYTES:
            logger.warning(
                "Chunk size %s too large, using maximum %s",
                size,
                self.MAX_CHUNK_SIZE_BYTES,
            )
            return self.MAX_CHUNK_SIZE_BYTES

        return size

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def save_webhook_to_env(self, webhook_url: str) -> bool:
        """Persist webhook URL to a local .env file.

        This mirrors the behaviour previously implemented directly in
        models/n8n_model.py, but keeps concerns separated from the main
        client.
        """

        try:
            env_file = ".env"
            env_lines = []
            webhook_found = False

            if os.path.exists(env_file):
                with open(env_file, "r", encoding="utf-8") as f:
                    env_lines = f.readlines()

            new_lines = []
            for line in env_lines:
                if line.strip().startswith("N8N_WEBHOOK_URL="):
                    new_lines.append(f"N8N_WEBHOOK_URL={webhook_url}\n")
                    webhook_found = True
                else:
                    new_lines.append(line)

            if not webhook_found:
                new_lines.append(f"N8N_WEBHOOK_URL={webhook_url}\n")

            with open(env_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            logger.info("Saved webhook to .env: %s", webhook_url)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to save webhook to .env: %s", exc)
            return False
