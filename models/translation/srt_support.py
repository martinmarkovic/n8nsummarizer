"""
SRT Support Module - Helper functions for SRT subtitle translation

This module provides utilities for detecting, parsing, batching, and reconstructing
SRT subtitle files for translation workflows.
"""

import re
from typing import List, Dict, Tuple, Optional
import srt
from utils.logger import logger


def is_srt_like(text: str) -> bool:
    """
    Detect SRT-like content using cue-number + timestamp pattern.

    Args:
        text: Text content to analyze

    Returns:
        bool: True if the text appears to be SRT format
    """
    # SRT pattern: number followed by timestamp line
    srt_pattern = r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}'
    return bool(re.search(srt_pattern, text))


def parse_srt(text: str) -> List[srt.Subtitle]:
    """
    Use the srt library to parse the text into subtitle objects.

    Args:
        text: Raw SRT content

    Returns:
        List of srt.Subtitle objects
    """
    try:
        return list(srt.parse(text))
    except Exception as e:
        # Return empty list if parsing fails
        return []


def compose_srt(subtitles: List[srt.Subtitle]) -> str:
    """
    Use the srt library to serialize subtitles back into a valid SRT string.

    Args:
        subtitles: List of srt.Subtitle objects

    Returns:
        Valid SRT formatted string
    """
    try:
        return srt.compose(subtitles)
    except Exception as e:
        return ""


def batch_subtitles(subtitles: List[srt.Subtitle], max_items: int = 40, max_chars: int = 4000) -> List[List[srt.Subtitle]]:
    """
    Batch consecutive subtitle cues.

    Args:
        subtitles: List of srt.Subtitle objects
        max_items: Maximum number of subtitles per batch
        max_chars: Maximum total characters per batch

    Returns:
        List of subtitle batches
    """
    if not subtitles:
        return []

    batches = []
    current_batch = []
    current_chars = 0

    for subtitle in subtitles:
        subtitle_text = subtitle.content.strip()
        subtitle_chars = len(subtitle_text)

        # Check if adding this subtitle would exceed batch limits
        if current_batch and (len(current_batch) >= max_items or current_chars + subtitle_chars > max_chars):
            batches.append(current_batch)
            current_batch = []
            current_chars = 0

        current_batch.append(subtitle)
        current_chars += subtitle_chars

    # Add the last batch if it has content
    if current_batch:
        batches.append(current_batch)

    return batches


def encode_text_only_batch(batch: List[srt.Subtitle]) -> str:
    """
    Convert subtitle objects into text-only payload lines using markers.

    Args:
        batch: List of srt.Subtitle objects

    Returns:
        String with marked text lines for translation
    """
    lines = []
    for i, subtitle in enumerate(batch, 1):
        # Use batch index as marker number (1-based)
        marker = f"<T{i}>"
        text = subtitle.content.strip()
        lines.append(f"{marker} {text}")

    return '\n'.join(lines)


def decode_text_only_batch(response_text: str) -> Dict[int, str]:
    """
    Parse translated lines in the same marker format.

    Args:
        response_text: Translated text with markers

    Returns:
        Dict mapping subtitle index -> translated text
    """
    decoded = {}

    if not response_text:
        return decoded

    # Split by lines and process each line
    lines = response_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Extract marker and text
        match = re.match(r'^<T(\d+)>\s*(.*)$', line)
        if match:
            try:
                index = int(match.group(1))
                text = match.group(2).strip()
                decoded[index] = text
            except (ValueError, IndexError):
                # Skip malformed lines
                continue

    return decoded


def validate_decoded_batch(decoded: Dict[int, str], expected_indices: List[int]) -> Tuple[bool, str]:
    """
    Ensure the decoded response contains exactly the expected indices.

    Args:
        decoded: Decoded response dictionary
        expected_indices: List of expected subtitle indices

    Returns:
        Tuple of (bool: validation result, str: detailed error message)
    """
    if not decoded and not expected_indices:
        return True, "Empty batch - validation passed"

    # Log detailed debugging information
    logger.debug(f"Validation - Expected {len(expected_indices)} indices: {expected_indices}")
    logger.debug(f"Validation - Decoded {len(decoded)} indices: {list(decoded.keys())}")
    logger.debug(f"Validation - Decoded content preview: {str(decoded)[:200]}...")

    if len(decoded) != len(expected_indices):
        missing_count = len(expected_indices) - len(decoded)
        error_msg = f"Index count mismatch: expected {len(expected_indices)}, got {len(decoded)} ({missing_count} missing)"
        logger.error(error_msg)
        return False, error_msg

    # Check that all expected indices are present
    missing_indices = [idx for idx in expected_indices if idx not in decoded]
    if missing_indices:
        error_msg = f"Missing indices: {missing_indices[:10]}" + ("..." if len(missing_indices) > 10 else "")
        logger.error(error_msg)
        return False, error_msg

    logger.info("Validation passed - all expected indices present")
    return True, "Validation passed"


def rebuild_subtitles_with_translations(original_subtitles: List[srt.Subtitle], 
                                        translations: Dict[int, str]) -> List[srt.Subtitle]:
    """
    Replace subtitle content with translated text while preserving timing and structure.

    Args:
        original_subtitles: Original list of subtitle objects
        translations: Dictionary mapping indices to translated text

    Returns:
        List of subtitle objects with translated content
    """
    if not original_subtitles:
        return []

    # Create a copy of original subtitles to avoid modifying the original
    translated_subtitles = []

    for i, subtitle in enumerate(original_subtitles, 1):
        # Create a new subtitle with the same timing but translated content
        if i in translations:
            new_content = translations[i]
        else:
            # Fallback to original content if translation missing
            new_content = subtitle.content

        new_subtitle = srt.Subtitle(
            index=subtitle.index,
            start=subtitle.start,
            end=subtitle.end,
            content=new_content
        )
        translated_subtitles.append(new_subtitle)

    return translated_subtitles