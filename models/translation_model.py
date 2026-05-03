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
    TRANSLATION_BATCH_MAX_ITEMS,
    TRANSLATION_BATCH_MAX_CHARS,
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
    rebuild_subtitles_with_translations,
    validate_rebuilt_subtitles
)
from models.translation.file_handler import TranslationFileHandler


class TranslationModel:
    """Translation facade that coordinates service calls and business logic.
    
    Acts as a facade over TranslationService and TranslationFileHandler,
    providing a unified interface for translation operations while
    delegating specific responsibilities to specialized components.
    
    Responsibilities:
        - Translation workflow coordination
        - Service orchestration
        - Error handling and retry logic
        - Translation quality management
        
    Delegates:
        - File operations → TranslationFileHandler
        - API communication → TranslationService
        - Text chunking → TranslationChunker
        - SRT processing → srt_support module
    """
    
    def __init__(self, max_tokens: int = None, chunk_size: int = None, batch_max_items: int = None, batch_max_chars: int = None):
        """Initialize translation model with default configuration."""
        self.webhook_url = TRANSLATION_DEFAULT_URL
        self.max_tokens = max_tokens or TRANSLATION_MAX_TOKENS
        self.chunk_size = chunk_size or TRANSLATION_CHUNK_SIZE
        self.batch_max_items = batch_max_items or TRANSLATION_BATCH_MAX_ITEMS
        self.batch_max_chars = batch_max_chars or TRANSLATION_BATCH_MAX_CHARS

        # Initialize services (facade pattern - delegate to specialized components)
        self.chunker = TranslationChunker(
            max_chunk_size=self.chunk_size, max_tokens=self.max_tokens
        )
        self.translation_service = TranslationService(
            webhook_url=TRANSLATION_DEFAULT_URL, max_tokens=self.max_tokens
        )
        self.file_handler = TranslationFileHandler()

        logger.info(
            f"TranslationModel initialized with default webhook: {self.webhook_url}"
        )
        logger.info(
            f"Translation chunking: max_tokens={self.max_tokens}, chunk_size={self.chunk_size}"
        )
        logger.info(
            f"SRT batching: max_items={self.batch_max_items}, max_chars={self.batch_max_chars} (reduced for better reliability)"
        )

    def set_current_file_path(self, path: str):
        """
        Set the current file path.
        
        Args:
            path: Path to the current file
        """
        self.file_handler.set_current_file_path(path)
        logger.info(f"Set current file path: {path}")

    def get_current_file_path(self) -> str:
        """
        Get the current file path.
        
        Returns:
            str: The current file path
        """
        return self.file_handler.get_current_file_path()

    def is_srt_source(self, text: str) -> bool:
        """
        Return True if current file path ends with .srt or content is SRT-like.
        
        Args:
            text: Text content to analyze
            
        Returns:
            bool: True if source appears to be SRT
        """
        return self.file_handler.is_srt_source(text)

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
        
    def set_batch_size(self, max_items: int = None, max_chars: int = None):
        """Set batch size for SRT translation."""
        if max_items is not None:
            self.batch_max_items = max_items
        if max_chars is not None:
            self.batch_max_chars = max_chars
        logger.info(f"Updated batch size to max_items={self.batch_max_items}, max_chars={self.batch_max_chars}")

    def get_translation_stats(self) -> dict:
        """Get translation statistics."""
        return {
            "max_tokens": self.max_tokens,
            "chunk_size": self.chunk_size,
            "batch_size": {"max_items": self.batch_max_items, "max_chars": self.batch_max_chars},
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

            # Batch subtitles for translation (using smaller batches to prevent LM Studio truncation)
            batches = batch_subtitles(subtitles, max_items=self.batch_max_items, max_chars=self.batch_max_chars)
            logger.info(f"Created {len(batches)} batches for translation (max {self.batch_max_items} items, {self.batch_max_chars} chars per batch)")

            # Track translations by subtitle index
            all_translations = {}
            failed_batches = []
            global_offset = 0  # Track global subtitle index offset

            # Process each batch
            for batch_idx, batch in enumerate(batches, 1):
                logger.info(f"Processing batch {batch_idx}/{len(batches)} with {len(batch)} subtitles (global offset: {global_offset})")

                # Encode batch as text-only with markers and global offset
                encoded_batch = encode_text_only_batch(batch, global_offset)

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
                    decoded = decode_text_only_batch(cleaned_text, global_offset)
                    logger.info(f"Batch {batch_idx} decoded {len(decoded)} entries from response")

                    # Get expected indices for this batch (global indices)
                    expected_indices = list(range(global_offset + 1, global_offset + len(batch) + 1))

                    # Validate decoded response
                    valid, validation_msg = validate_decoded_batch(decoded, expected_indices)
                    if valid:
                        # Merge translations
                        all_translations.update(decoded)
                        logger.info(f"Batch {batch_idx} translated successfully: {len(decoded)} subtitles")
                        # Update global offset for next batch
                        global_offset += len(batch)
                    else:
                        error_msg = f"Validation failed for batch {batch_idx}: {validation_msg}"
                        logger.error(error_msg)
                        
                        # Calculate recovery percentage for this batch
                        recovery_percentage = (len(decoded) / len(expected_indices)) * 100 if expected_indices else 0
                        logger.warning(f"Batch {batch_idx} recovery rate: {recovery_percentage:.1f}% ({len(decoded)}/{len(expected_indices)})")
                        
                        # Check if this looks like LM Studio truncation (missing end translations)
                        if self._is_likely_truncation(decoded, expected_indices):
                            logger.info(f"🔧 Attempting LM Studio truncation recovery for batch {batch_idx}")
                             
                            # Try to recover missing translations
                            recovered_translations = self._retry_missing_translations(
                                batch, decoded, target_language, global_offset
                            )
                             
                            if recovered_translations:
                                all_translations.update(recovered_translations)
                                final_recovery = len(decoded) + len(recovered_translations)
                                logger.info(f"✅ Recovery successful: {final_recovery}/{len(expected_indices)} translations after retry")
                                 
                                # Check if we now have sufficient recovery
                                if final_recovery >= len(expected_indices) * 0.7:  # Reduced from 80% to 70% recovery
                                    logger.info(f"🎯 Batch {batch_idx} sufficiently recovered: {final_recovery}/{len(expected_indices)} ({final_recovery/len(expected_indices)*100:.1f}%)")
                                    global_offset += len(batch)
                                    continue  # Skip the failure processing
                            else:
                                logger.warning(f"⚠️  Partial recovery: {len(recovered_translations)} additional translations recovered")
                        
                        # Enhanced error recovery: retry with smaller batch size if recovery is very low
                        if recovery_percentage < 40:  # Reduced from 50% to 40% recovery
                            logger.info(f"Attempting retry for batch {batch_idx} with smaller size...")
                            
                            # Split the failed batch into smaller chunks
                            retry_batches = batch_subtitles(batch, max_items=2, max_chars=500)
                            logger.info(f"Split failed batch into {len(retry_batches)} smaller batches for retry")
                            
                            # Process each retry batch
                            for retry_idx, retry_batch in enumerate(retry_batches, 1):
                                logger.info(f"  Retry {retry_idx}/{len(retry_batches)}: {len(retry_batch)} subtitles")
                                
                                # Encode retry batch
                                retry_encoded = encode_text_only_batch(retry_batch, global_offset)
                                
                                # Translate retry batch
                                retry_success, retry_text, retry_error, retry_metadata = (
                                    self.translation_service.translate_chunk(
                                        chunk=retry_encoded,
                                        target_language=target_language,
                                        chunk_index=batch_idx,
                                        total_chunks=len(batches),
                                        mode="srt_text_only"
                                    )
                                )
                                
                                if retry_success:
                                    retry_cleaned = self.translation_service.clean_translation_output(retry_text)
                                    retry_decoded = decode_text_only_batch(retry_cleaned, global_offset)
                                    
                                    # Validate retry batch
                                    retry_expected = list(range(global_offset + 1, global_offset + len(retry_batch) + 1))
                                    retry_valid, retry_msg = validate_decoded_batch(retry_decoded, retry_expected)
                                    
                                    if retry_valid:
                                        all_translations.update(retry_decoded)
                                        logger.info(f"  Retry {retry_idx} successful: {len(retry_decoded)} translations")
                                    else:
                                        logger.warning(f"  Retry {retry_idx} also failed: {retry_msg}")
                                else:
                                    logger.error(f"  Retry {retry_idx} translation failed: {retry_error}")
                                
                                # Update global offset for next retry batch
                                global_offset += len(retry_batch)
                            
                            # Update failure tracking
                            retry_success_count = sum(1 for k in all_translations.keys() if k in expected_indices)
                            if retry_success_count > 0:
                                logger.info(f"Batch {batch_idx} partial recovery: {retry_success_count}/{len(batch)} translations after retry")
                            else:
                                failed_batches.append((batch_idx, error_msg))
                        else:
                            failed_batches.append((batch_idx, error_msg))
                            # Still update global offset to maintain correct indexing for subsequent batches
                            global_offset += len(batch)
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

            # Validate rebuilt subtitles
            validation_passed, validation_msg = validate_rebuilt_subtitles(subtitles, translated_subtitles)
            if not validation_passed:
                logger.error(f"Subtitle reconstruction validation failed: {validation_msg}")
                # Continue with partial result rather than failing completely

            # Compose final SRT
            final_srt = compose_srt(translated_subtitles)

            logger.info(f"Successfully translated {len(all_translations)}/{len(subtitles)} subtitles")
            logger.info(f"Validation result: {validation_msg}")

            # Enhanced user feedback for partial successes
            if failed_batches:
                error_details = ", ".join([f"Batch {idx}: {err}" for idx, err in failed_batches])
                logger.warning(f"Partial success - some batches failed: {error_details}")
                
                # Calculate detailed statistics
                success_rate = (len(all_translations) / len(subtitles)) * 100
                missing_count = len(subtitles) - len(all_translations)
                
                # Generate user-friendly feedback
                feedback_msg = f"Partial translation completed\n"
                feedback_msg += f"✅ Success: {len(all_translations)}/{len(subtitles)} subtitles ({success_rate:.1f}%)\n"
                feedback_msg += f"⚠️  Missing: {missing_count} subtitles\n"
                feedback_msg += f"🔍 Failed batches: {len(failed_batches)}\n"
                
                # Add specific advice based on failure patterns
                if len(failed_batches) > 1:
                    feedback_msg += "💡 Multiple batches failed - consider checking translation service status\n"
                
                if success_rate < 50:
                    feedback_msg += "💡 Low success rate - try smaller files or simpler content\n"
                
                if success_rate < 80:
                    feedback_msg += "💡 Some translations may be missing or incomplete. Consider retrying with smaller batches.\n"
                
                feedback_msg += "📋 Missing translations use placeholders: [TRANSLATION MISSING FOR SUBTITLE X]\n"
                feedback_msg += "🔄 You can retry the translation to recover missing subtitles."
                
                logger.info(f"User feedback prepared: {feedback_msg.replace(chr(10), ' | ')}")
                return True, final_srt, feedback_msg

            return True, final_srt, None

        except Exception as e:
            error_msg = f"SRT translation error: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

    def _is_likely_truncation(self, decoded: Dict[int, str], expected_indices: List[int]) -> bool:
        """
        Detect if missing translations follow LM Studio truncation pattern.
        Truncation typically removes translations from the END of batches.
        """
        if not decoded or not expected_indices:
            return False
            
        decoded_indices = sorted(decoded.keys())
        missing_indices = [idx for idx in expected_indices if idx not in decoded_indices]
        
        if not missing_indices:
            return False
            
        # Check if missing indices are at the end (truncation pattern)
        max_decoded = max(decoded_indices)
        min_missing = min(missing_indices)
        
        # If all missing indices are > max decoded index, it's likely truncation
        if min_missing > max_decoded:
            return True
            
        # Check if missing indices form a consecutive block at the end
        expected_set = set(expected_indices)
        decoded_set = set(decoded_indices)
        missing_set = expected_set - decoded_set
        
        if missing_set:
            max_expected = max(expected_indices)
            missing_sorted = sorted(missing_set)
            
            # Check if missing indices are consecutive and at the end
            if missing_sorted == list(range(min(missing_sorted), max(missing_sorted) + 1)):
                if max(missing_sorted) == max_expected:
                    return True
        
        return False

    def _retry_missing_translations(self, batch: List[srt.Subtitle], decoded: Dict[int, str], 
                                   target_language: str, global_offset: int) -> Dict[int, str]:
        """
        Attempt to recover translations that were truncated by LM Studio.
        
        Args:
            batch: Original batch of subtitles
            decoded: Successfully decoded translations
            target_language: Target language for translation
            global_offset: Global index offset for this batch
            
        Returns:
            Dictionary of recovered translations
        """
        recovered = {}
        
        # Identify missing indices
        expected_indices = list(range(global_offset + 1, global_offset + len(batch) + 1))
        missing_indices = [idx for idx in expected_indices if idx not in decoded]
        
        if not missing_indices:
            return recovered
            
        logger.warning(f"🔧 Attempting to recover {len(missing_indices)} missing translations")
        
        # Strategy: Retry missing translations in small groups of 2
        for i in range(0, len(missing_indices), 2):
            group_indices = missing_indices[i:i+2]
            
            # Create mini-batch with just the missing subtitles
            mini_batch = []
            for local_idx in range(len(batch)):
                global_idx = global_offset + local_idx + 1
                if global_idx in group_indices:
                    mini_batch.append(batch[local_idx])
            
            if mini_batch:
                # Encode the mini-batch
                mini_encoded = encode_text_only_batch(mini_batch, group_indices[0] - 1)
                
                # Retry translation with smaller chunk
                retry_success, retry_text, retry_error, _ = (
                    self.translation_service.translate_chunk(
                        chunk=mini_encoded,
                        target_language=target_language,
                        chunk_index=99,  # Special index for retries
                        total_chunks=1,
                        mode="srt_retry"
                    )
                )
                
                if retry_success:
                    # Decode the retry response
                    retry_cleaned = self.translation_service.clean_translation_output(retry_text)
                    retry_decoded = decode_text_only_batch(retry_cleaned, group_indices[0] - 1, expected_count=len(group_indices))
                    
                    # Merge recovered translations
                    for idx, translation in retry_decoded.items():
                        if idx not in recovered:
                            recovered[idx] = translation
                            logger.info(f"✅ Recovered translation {idx} in retry")
                else:
                    logger.warning(f"❌ Retry failed for indices {group_indices}: {retry_error}")
        
        # If no translations were recovered, try a fallback approach
        if not recovered:
            logger.warning("⚠️  No translations recovered, attempting fallback approach...")
            
            # Fallback: Try to recover translations one by one
            for missing_idx in missing_indices:
                # Find the subtitle corresponding to the missing index
                local_idx = missing_idx - global_offset - 1
                if 0 <= local_idx < len(batch):
                    subtitle = batch[local_idx]
                    
                    # Encode the single subtitle
                    single_encoded = encode_text_only_batch([subtitle], missing_idx - 1)
                    
                    # Retry translation with a single subtitle
                    single_success, single_text, single_error, _ = (
                        self.translation_service.translate_chunk(
                            chunk=single_encoded,
                            target_language=target_language,
                            chunk_index=99,  # Special index for retries
                            total_chunks=1,
                            mode="srt_single_retry"
                        )
                    )
                    
                    if single_success:
                        # Decode the single subtitle response
                        single_cleaned = self.translation_service.clean_translation_output(single_text)
                        single_decoded = decode_text_only_batch(single_cleaned, missing_idx - 1, expected_count=1)
                        
                        # Merge recovered translation
                        for idx, translation in single_decoded.items():
                            if idx not in recovered:
                                recovered[idx] = translation
                                logger.info(f"✅ Recovered translation {idx} in single retry")
                    else:
                        logger.debug(f"❌ Single retry failed for index {missing_idx}: {single_error}")
        
        return recovered

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
        return self.file_handler.load_file_content(file_path)

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
