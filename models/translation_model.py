"""
Translation Model - Business logic for translation functionality

Responsibilities:
    - Translation API communication (LM Studio/n8n webhooks)
    - File content loading and extraction
    - Webhook URL persistence
    - Translation prompt construction
    - Error handling and validation
    - Chunked translation for large documents

This model follows the same pattern as other models in the project
(e.g., models/n8n/client.py, models/file_model.py).
"""

import os
import json
from pathlib import Path
from typing import Tuple, Optional, List
from config import (
    TRANSLATION_DEFAULT_URL,
    TRANSLATION_MAX_TOKENS,
    TRANSLATION_CHUNK_SIZE,
)
from utils.logger import logger
from models.translation.chunking import TranslationChunker
from models.translation.service import TranslationService
from models.translation.srt_support import (
    is_srt_like,
    parse_srt,
    compose_srt,
    batch_subtitles,
    encode_text_only_batch,
    decode_text_only_batch,
    validate_decoded_batch,
    rebuild_subtitles_with_translations
)


class TranslationModel:
    """Translation business logic and data operations."""

    def __init__(self, max_tokens: int = None, chunk_size: int = None):
        """Initialize translation model with default configuration."""
        self.webhook_url = TRANSLATION_DEFAULT_URL
        self.max_tokens = max_tokens or TRANSLATION_MAX_TOKENS
        self.chunk_size = chunk_size or TRANSLATION_CHUNK_SIZE
        self.current_file_path = None

        # Initialize services
        self.chunker = TranslationChunker(
            max_chunk_size=self.chunk_size, max_tokens=self.max_tokens
        )
        self.translation_service = TranslationService(
            webhook_url=TRANSLATION_DEFAULT_URL, max_tokens=self.max_tokens
        )

        logger.info(
            f"TranslationModel initialized with default webhook: {self.webhook_url}"
        )
        logger.info(
            f"Translation chunking: max_tokens={self.max_tokens}, chunk_size={self.chunk_size}"
        )

    def set_current_file_path(self, path: str):
        """
        Set the current file path.

        Args:
            path: Path to the current file
        """
        self.current_file_path = path
        logger.info(f"Set current file path: {self.current_file_path}")

    def get_current_file_path(self) -> str:
        """
        Get the current file path.

        Returns:
            str: The current file path
        """
        return self.current_file_path

    def is_srt_source(self, text: str) -> bool:
        """
        Return True if current file path ends with .srt or content is SRT-like.

        Args:
            text: Text content to analyze

        Returns:
            bool: True if source appears to be SRT
        """
        # Check file extension first
        if self.current_file_path and self.current_file_path.lower().endswith('.srt'):
            return True

        # Fallback to content detection
        return is_srt_like(text)

    def set_max_tokens(self, max_tokens: int):
        """Set maximum tokens for translation API calls."""
        self.max_tokens = max_tokens
        self.chunker.max_tokens = max_tokens
        self.translation_service.max_tokens = max_tokens
        logger.info(f"Updated max_tokens to {max_tokens}")

    def set_chunk_size(self, chunk_size: int):
        """Set chunk size for text splitting."""
        self.chunk_size = chunk_size
        self.chunker.max_chunk_size = chunk_size
        logger.info(f"Updated chunk_size to {chunk_size}")

    def get_translation_stats(self) -> dict:
        """Get translation statistics."""
        return {
            "max_tokens": self.max_tokens,
            "chunk_size": self.chunk_size,
            "retries": self.translation_service.get_retry_stats(),
        }

    def translate_srt(self, text: str, target_language: str) -> Tuple[bool, str, Optional[str]]:
        """
        Translate SRT file using specialized pipeline that preserves subtitle structure.

        Args:
            text: Original SRT text
            target_language: Target language for translation

        Returns:
            Tuple of (success: bool, result: str, error: Optional[str])
        """
        logger.info(f"Starting SRT translation workflow")

        try:
            # Parse SRT into subtitle objects
            subtitles = parse_srt(text)
            if not subtitles:
                return False, "", "Failed to parse SRT content"

            logger.info(f"Parsed {len(subtitles)} subtitles from SRT")

            # Batch subtitles for translation
            batches = batch_subtitles(subtitles)
            logger.info(f"Created {len(batches)} batches for translation")

            # Track translations by subtitle index
            all_translations = {}
            failed_batches = []

            # Process each batch
            for batch_idx, batch in enumerate(batches, 1):
                logger.info(f"Processing batch {batch_idx}/{len(batches)} with {len(batch)} subtitles")

                # Encode batch as text-only with markers
                encoded_batch = encode_text_only_batch(batch)

                # Translate this batch
                success, translated_text, error, metadata = (
                    self.translation_service.translate_chunk(
                        chunk=encoded_batch,
                        target_language=target_language,
                        chunk_index=batch_idx,
                        total_chunks=len(batches),
                        mode="srt_text_only"
                    )
                )

                if success:
                    # Clean and decode the translated text back into segments
                    cleaned_text = self.translation_service.clean_translation_output(translated_text)
                    decoded = decode_text_only_batch(cleaned_text)
                    logger.info(f"Batch {batch_idx} decoded {len(decoded)} entries from response")

                    # Get expected indices for this batch
                    expected_indices = list(range(1, len(batch) + 1))

                    # Validate decoded response
                    valid, validation_msg = validate_decoded_batch(decoded, expected_indices)
                    if valid:
                        # Merge translations
                        all_translations.update(decoded)
                        logger.info(f"Batch {batch_idx} translated successfully: {len(decoded)} subtitles")
                    else:
                        error_msg = f"Validation failed for batch {batch_idx}: {validation_msg}"
                        logger.error(error_msg)
                        failed_batches.append((batch_idx, error_msg))
                else:
                    error_msg = f"Translation failed for batch {batch_idx}: {error}"
                    logger.error(error_msg)
                    failed_batches.append((batch_idx, error_msg))

            # Check if we have any successful translations
            if not all_translations and failed_batches:
                error_details = ", ".join([f"Batch {idx}" for idx, _ in failed_batches])
                return False, "", f"All batches failed: {error_details}"

            # Rebuild subtitles with translations
            translated_subtitles = rebuild_subtitles_with_translations(subtitles, all_translations)

            # Compose final SRT
            final_srt = compose_srt(translated_subtitles)

            logger.info(f"Successfully translated {len(all_translations)}/{len(subtitles)} subtitles")

            # Return partial success if some batches failed
            if failed_batches:
                error_details = ", ".join([f"Batch {idx}: {err}" for idx, err in failed_batches])
                logger.warning(f"Partial success - some batches failed: {error_details}")
                return True, final_srt, f"Partial translation - {len(failed_batches)} batches failed"

            return True, final_srt, None

        except Exception as e:
            error_msg = f"SRT translation error: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

    def translate_text(
        self, text: str, target_language: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Translate text using chunked approach for large documents.

        For small texts: Single API call
        For large texts: Intelligent chunking with retry logic

        Args:
            text: Source text to translate
            target_language: Target language for translation

        Returns:
            Tuple of (success: bool, result: str, error: Optional[str])
        """
        if not text or not text.strip():
            return False, "", "No text provided for translation"

        if not self.webhook_url:
            return False, "", "Translation webhook URL not configured"

        # Update service with current webhook URL
        self.translation_service.webhook_url = self.webhook_url

        try:
            # Check if this is SRT content
            if self.is_srt_source(text):
                logger.info("Detected SRT source - using SRT translation pipeline")
                return self.translate_srt(text, target_language)

            # Regular text translation
            if self._needs_chunking(text):
                logger.info(f"Text requires chunking (length: {len(text)} chars)")
                return self._translate_with_chunking(text, target_language)
            else:
                logger.info(f"Text fits in single chunk (length: {len(text)} chars)")
                return self._translate_single_chunk(text, target_language)

        except Exception as e:
            error_msg = f"Unexpected translation error: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

    def _needs_chunking(self, text: str) -> bool:
        """Determine if text needs chunking based on size and token estimate."""
        # Rough estimate: 1 token ≈ 4 characters
        estimated_tokens = len(text) // 4

        # Chunk if exceeds 80% of max_tokens to be safe
        if estimated_tokens > self.max_tokens * 0.8:
            return True

        # Also chunk if text is very long (regardless of token estimate)
        if len(text) > self.chunk_size:
            return True

        return False

    def _translate_single_chunk(
        self, text: str, target_language: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Translate text in single chunk (for small texts)."""
        success, translated_text, error, metadata = (
            self.translation_service.translate_chunk(
                chunk=text,
                target_language=target_language,
                chunk_index=1,
                total_chunks=1,
            )
        )

        if success:
            # Clean the translation output by removing think tags
            translated_text = self.translation_service.clean_translation_output(
                translated_text
            )
            logger.info(
                f"Single chunk translation successful, {len(translated_text)} characters"
            )
            return True, translated_text, None
        else:
            logger.error(f"Single chunk translation failed: {error}")
            return False, "", error

    def _translate_with_chunking(
        self, text: str, target_language: str
    ) -> Tuple[bool, str, Optional[str]]:
        """Translate text using chunked approach."""
        logger.info(f"Starting chunked translation for {len(text)} characters")

        # Split text into chunks
        chunks = self.chunker.chunk_text(text)
        total_chunks = len(chunks)

        if total_chunks == 0:
            return False, "", "No chunks generated from text"

        translated_chunks = []
        failed_chunks = []

        # Translate each chunk
        for i, chunk in enumerate(chunks, 1):
            success, translated_text, error, metadata = (
                self.translation_service.translate_chunk(
                    chunk=chunk,
                    target_language=target_language,
                    chunk_index=i,
                    total_chunks=total_chunks,
                )
            )

            if success:
                translated_chunks.append(translated_text)
                logger.info(
                    f"Chunk {i}/{total_chunks} translated successfully ({len(translated_text)} chars)"
                )
            else:
                failed_chunks.append((i, error or "Unknown error"))
                logger.error(f"Chunk {i}/{total_chunks} failed: {error}")

        # Check results
        if failed_chunks:
            error_details = ", ".join(
                [f"Chunk {idx}: {err}" for idx, err in failed_chunks]
            )
            error_msg = f"Translation partially failed. {len(failed_chunks)}/{total_chunks} chunks failed: {error_details}"

            # Return partial result if we have some translations
            if translated_chunks:
                partial_result = "".join(translated_chunks)
                # Clean the translation output by removing think tags
                partial_result = self.translation_service.clean_translation_output(
                    partial_result
                )
                logger.warning(
                    f"Returning partial translation: {len(partial_result)} characters from {len(translated_chunks)}/{total_chunks} chunks"
                )
                return True, partial_result, error_msg
            else:
                return False, "", error_msg

        # Combine all translated chunks
        final_translation = "".join(translated_chunks)
        # Clean the translation output by removing think tags
        final_translation = self.translation_service.clean_translation_output(
            final_translation
        )
        logger.info(
            f"Chunked translation completed. {len(chunks)} chunks → {len(final_translation)} characters"
        )

        # Log retry statistics
        retry_stats = self.translation_service.get_retry_stats()
        if retry_stats["total_retries"] > 0:
            logger.info(
                f"Translation retries: {retry_stats['total_retries']} total retries across all chunks"
            )

        return True, final_translation, None

    def load_file_content(self, file_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        Load text content from file.

        Args:
            file_path: Path to file to load

        Returns:
            Tuple of (success: bool, content: str, error: Optional[str])
        """
        if not file_path or not os.path.exists(file_path):
            return False, "", f"File not found: {file_path}"

        try:
            path = Path(file_path)
            content = path.read_text(encoding="utf-8", errors="replace")
            logger.info(f"Loaded file: {file_path} ({len(content)} characters)")
            return True, content, None

        except Exception as e:
            error_msg = f"Error loading file {file_path}: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

    def save_webhook_to_env(self, url: str) -> bool:
        """
        Save webhook URL to .env file for persistence.

        Args:
            url: Webhook URL to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

            # Read existing .env
            lines = []
            if os.path.exists(env_path):
                with open(env_path, "r") as f:
                    lines = f.readlines()

            # Update or add TRANSLATION_URL
            updated = False
            for i, line in enumerate(lines):
                if line.startswith("TRANSLATION_URL="):
                    lines[i] = f"TRANSLATION_URL={url}\n"
                    updated = True
                    break

            if not updated:
                lines.append(f"TRANSLATION_URL={url}\n")

            # Write back to .env
            with open(env_path, "w") as f:
                f.writelines(lines)

            logger.info(f"Saved translation webhook to .env: {url}")
            self.webhook_url = url
            return True

        except Exception as e:
            logger.error(f"Failed to save webhook to .env: {str(e)}")
            return False

    def restore_default_webhook(self) -> str:
        """
        Restore default webhook URL.

        Returns:
            str: The restored default URL
        """
        self.webhook_url = TRANSLATION_DEFAULT_URL
        logger.info(f"Restored default translation webhook: {self.webhook_url}")
        return self.webhook_url

    def set_webhook_url(self, url: str):
        """
        Set webhook URL in memory (does not persist to .env).

        Args:
            url: Webhook URL to use
        """
        self.webhook_url = url
        logger.info(f"Set translation webhook URL: {self.webhook_url}")
