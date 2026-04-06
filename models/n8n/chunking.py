"""Content chunking helpers for N8NModel.

This module contains logic for calculating chunk counts based on the
original file size in bytes and splitting the in-memory text content
into approximately equal-sized pieces while attempting to respect
paragraph/sentence/word boundaries.
"""

from __future__ import annotations

from typing import List

from utils.logger import logger


class ContentChunker:
    """Handle intelligent content splitting with boundary detection."""

    def __init__(self, chunk_size_bytes: int) -> None:
        self.chunk_size_bytes = chunk_size_bytes

    # NOTE: The following methods are adapted from the original
    # models/n8n_model.py implementation to keep behaviour identical.

    def calculate_num_chunks(self, file_size_bytes: int) -> int:
        """Calculate number of chunks from FILE SIZE IN BYTES.

        Uses ceiling division to ensure no content is lost. Strategy is:
        50 KB per chunk (measured in actual file bytes), but the
        exact size is configured by :attr:`chunk_size_bytes`.
        """

        num_chunks = (file_size_bytes + self.chunk_size_bytes - 1) // self.chunk_size_bytes
        num_chunks = max(1, num_chunks)

        file_kb = file_size_bytes / 1024
        chunk_kb = self.chunk_size_bytes / 1024
        logger.debug(
            f"File {file_size_bytes} bytes ({file_kb:.1f} KB): "
            f"{num_chunks} chunks × {chunk_kb:.0f}KB"
        )
        return num_chunks

    def split_content(self, content: str, file_size_bytes: int) -> List[str]:
        """Split content into chunks based on file size.

        Behaviour matches the original `_split_into_chunks` method:
        - Determine number of chunks from file size
        - Compute approximate char count per chunk
        - Try to split at paragraph ("\n\n"), then newline, then space
        - Fall back to hard split if no boundary is found
        """

        content_len = len(content)
        num_chunks = self.calculate_num_chunks(file_size_bytes)

        logger.info(
            f"Splitting content ({content_len} chars from {file_size_bytes} bytes) "
            f"into {num_chunks} chunks"
        )

        if num_chunks == 1:
            logger.debug("Content fits in a single chunk")
            return [content]

        chunks: List[str] = []
        chars_per_chunk = (content_len + num_chunks - 1) // num_chunks
        logger.debug(
            f"Target: {chars_per_chunk} chars per chunk (total {content_len} chars)"
        )

        start = 0
        for chunk_num in range(num_chunks):
            if chunk_num == num_chunks - 1:
                end = content_len
                logger.debug(
                    f"Chunk {chunk_num + 1}/{num_chunks}: Last chunk "
                    f"from {start} to {end} ({end - start} chars)"
                )
            else:
                end = start + chars_per_chunk
                search_start = max(start, end - chars_per_chunk // 4)
                search_end = min(content_len, end + chars_per_chunk // 4)

                end = self._find_boundary(content, start, end, search_start, search_end)

            chunk_text = content[start:end]
            chunks.append(chunk_text)
            logger.info(
                f"Chunk {chunk_num + 1}/{num_chunks}: {len(chunk_text)} chars"
            )

            start = end

        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    def _find_boundary(
        self,
        content: str,
        start: int,
        proposed_end: int,
        search_start: int,
        search_end: int,
    ) -> int:
        """Try to find a sensible boundary near the proposed end.

        Preference order:
        1. Paragraph boundary ("\n\n")
        2. Line boundary ("\n")
        3. Word boundary (space)
        4. Hard split at the proposed end
        """

        paragraph_end = content.rfind("\n\n", search_start, search_end)
        if paragraph_end != -1 and paragraph_end > start:
            logger.debug("Split chunk at paragraph boundary")
            return paragraph_end + 2

        sentence_end = content.rfind("\n", search_start, search_end)
        if sentence_end != -1 and sentence_end > start:
            logger.debug("Split chunk at line boundary")
            return sentence_end + 1

        space_end = content.rfind(" ", search_start, search_end)
        if space_end != -1 and space_end > start:
            logger.debug("Split chunk at word boundary")
            return space_end + 1

        logger.debug("No boundary found, performing hard split")
        return proposed_end
