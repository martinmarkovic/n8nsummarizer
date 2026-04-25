"""
Translation Chunking Service

Provides intelligent text chunking for large document translation.
Supports paragraph-first, sentence fallback, and hard split strategies.
"""

import re
from typing import List, Tuple
from utils.logger import logger


class TranslationChunker:
    """Intelligent text chunking for translation."""

    def __init__(self, max_chunk_size: int = 2000, max_tokens: int = 6000):
        """
        Initialize chunker with configuration.

        Args:
            max_chunk_size: Maximum characters per chunk (approximate)
            max_tokens: Maximum tokens for LM Studio (used for validation)
        """
        self.max_chunk_size = max_chunk_size
        self.max_tokens = max_tokens

        # Patterns for intelligent splitting
        self.paragraph_pattern = r"\n\s*\n"  # Two or more newlines
        self.sentence_pattern = r"(?<=[.!?])\s+"  # Sentence boundaries
        self.hard_split_pattern = r"(?<=\.|,|;|:|\s)"  # Fallback split points

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks using intelligent strategy.

        Strategy:
        1. Paragraph-first: Split by paragraphs if possible
        2. Sentence fallback: Split by sentences for oversized paragraphs
        3. Hard split: Fallback to word boundaries for very long sentences

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        chunks = []
        remaining_text = text.strip()
        chunk_index = 1

        while remaining_text:
            chunk, remaining_text = self._extract_next_chunk(
                remaining_text, chunk_index
            )
            if chunk:
                chunks.append(chunk)
                chunk_index += 1

        logger.info(f"Split text into {len(chunks)} chunks for translation")
        return chunks

    def _extract_next_chunk(self, text: str, chunk_index: int) -> Tuple[str, str]:
        """
        Extract next chunk using intelligent strategy.

        Args:
            text: Remaining text to process
            chunk_index: Current chunk number (for logging)

        Returns:
            Tuple of (chunk, remaining_text)
        """
        original_length = len(text)

        # Strategy 1: Try paragraph splitting first
        if "\n\n" in text or "\r\n\r\n" in text:
            paragraphs = self._split_paragraphs(text)
            if len(paragraphs) > 1:
                chunk, remaining = self._build_chunk_from_paragraphs(paragraphs)
                if chunk:
                    logger.debug(
                        f"Chunk {chunk_index}: Paragraph-based split ({len(chunk)} chars)"
                    )
                    return chunk, remaining

        # Strategy 2: Try sentence splitting
        sentences = self._split_sentences(text)
        if len(sentences) > 1:
            chunk, remaining = self._build_chunk_from_sentences(sentences)
            if chunk:
                logger.debug(
                    f"Chunk {chunk_index}: Sentence-based split ({len(chunk)} chars)"
                )
                return chunk, remaining

        # Strategy 3: Hard split (fallback)
        if len(text) > self.max_chunk_size:
            # Find a reasonable split point near max_chunk_size
            split_pos = self._find_hard_split_point(text)
            chunk = text[:split_pos].strip()
            remaining = text[split_pos:].strip()
            logger.debug(
                f"Chunk {chunk_index}: Hard split at position {split_pos} ({len(chunk)} chars)"
            )
            return chunk, remaining

        # Text fits in one chunk
        logger.debug(
            f"Chunk {chunk_index}: Full text fits in one chunk ({len(text)} chars)"
        )
        return text, ""

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text by paragraphs (double newlines)."""
        return re.split(self.paragraph_pattern, text)

    def _split_sentences(self, text: str) -> List[str]:
        """Split text by sentences."""
        return re.split(self.sentence_pattern, text)

    def _build_chunk_from_paragraphs(self, paragraphs: List[str]) -> Tuple[str, str]:
        """Build chunk by adding paragraphs until we reach max size."""
        chunk = []
        remaining_paragraphs = []
        current_size = 0

        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Check if adding this paragraph would exceed max size
            if (
                current_size + len(paragraph) + 2 <= self.max_chunk_size
            ):  # +2 for newlines
                chunk.append(paragraph)
                current_size += len(paragraph) + 2
            else:
                remaining_paragraphs = paragraphs[i:]
                break

        if chunk:
            return "\n\n".join(chunk), "\n\n".join(remaining_paragraphs)
        return "", paragraphs

    def _build_chunk_from_sentences(self, sentences: List[str]) -> Tuple[str, str]:
        """Build chunk by adding sentences until we reach max size."""
        chunk = []
        remaining_sentences = []
        current_size = 0

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence would exceed max size
            if current_size + len(sentence) + 1 <= self.max_chunk_size:  # +1 for space
                chunk.append(sentence)
                current_size += len(sentence) + 1
            else:
                remaining_sentences = sentences[i:]
                break

        if chunk:
            return " ".join(chunk), " ".join(remaining_sentences)
        return "", sentences

    def _find_hard_split_point(self, text: str) -> int:
        """Find a reasonable hard split point near max_chunk_size."""
        # Look for split points in reverse order from max_chunk_size
        search_start = min(self.max_chunk_size, len(text) - 1)

        # Try to find a word boundary
        for i in range(search_start, max(0, search_start - 100), -1):
            if text[i] in " .,;:!?\n\t":
                return i + 1

        # If no good split point found, split at max_chunk_size
        return min(self.max_chunk_size, len(text))

    def validate_chunk_size(self, chunk: str) -> bool:
        """Validate that chunk size is reasonable for LM Studio."""
        # Rough estimate: 1 token ≈ 4 characters
        estimated_tokens = len(chunk) // 4
        return estimated_tokens <= self.max_tokens
