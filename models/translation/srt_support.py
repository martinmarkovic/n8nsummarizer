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


def decode_text_only_batch(response_text: str, expected_count: int = None) -> Dict[int, str]:
    """
    Parse translated lines in the same marker format.
    Enhanced to handle both multi-line and consolidated response formats.

    Args:
        response_text: Translated text with markers

    Returns:
        Dict mapping subtitle index -> translated text
    """
    decoded = {}

    if not response_text:
        return decoded

    # Log the complete raw response for analysis
    logger.info(f"=== RESPONSE ANALYSIS ===")
    logger.info(f"Response length: {len(response_text)} characters")
    logger.info(f"Response lines: {len(response_text.split(chr(10)))} lines")
    
    # Show first 10 lines for diagnostic purposes
    for i, line in enumerate(response_text.split('\n')[:10], 1):
        logger.info(f"Line {i}: {line[:80]}...")
    
    if len(response_text.split('\n')) > 10:
        logger.info(f"... and {len(response_text.split(chr(10))) - 10} more lines")
    
    # Clean response text by removing common wrappers
    cleaned_text = response_text.strip()

    # Remove code fences if present
    if cleaned_text.startswith('```') and cleaned_text.endswith('```'):
        cleaned_text = cleaned_text[3:-3].strip()
        logger.info("Removed code fence wrapping")

    # Remove common prefixes
    for prefix in ["Sure, here's the translation:", "Here you go:", "Here's the translation:"]:
        if cleaned_text.startswith(prefix):
            cleaned_text = cleaned_text[len(prefix):].strip()
            logger.info(f"Removed prefix: '{prefix}'")
            break

    # Check for consolidated format (multiple markers on single line)
    if len(cleaned_text.split('\n')) == 1 and '<T' in cleaned_text:
        logger.info("Detected consolidated response format (multiple markers on single line)")
        # Parse consolidated format: <T1> text1 <T2> text2 <T3> text3...
        consolidated_pattern = r'<T(\d+)>([^<]*)'
        matches = list(re.finditer(consolidated_pattern, cleaned_text))
        
        if matches and len(matches) > 1:
            logger.info(f"Found {len(matches)} markers in consolidated format")
            for match in matches:
                try:
                    index = int(match.group(1))
                    text = match.group(2).strip()
                    decoded[index] = text
                    logger.info(f"✓ Consolidated match for index {index}: {text[:50]}...")
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse consolidated match: {e}")
            
            if decoded:
                logger.info(f"✅ Consolidated decoding successful: {len(decoded)} entries")
                return decoded

    # Split by lines and process each line (standard multi-line format)
    lines = cleaned_text.split('\n')
    logger.info(f"Processing {len(lines)} cleaned lines for marker matching")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try multiple marker patterns in order of likelihood
        patterns = [
            r'^<T(\d+)>\s*(.*)$',      # Standard: <T1> text
            r'^\[T(\d+)>\s*(.*)$',     # Square brackets with >: [T1> text
            r'^\[T(\d+)\]\s*(.*)$',    # Square brackets: [T1] text
            r'^(\d+)\.\.?\s*(.*)$',   # Numbered list: 1. text or 1. text
            r'^\*\s*<T(\d+)>\s*(.*)$', # Bullet with marker: * <T1> text
        ]

        decoded_line = False
        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) >= 2:
                        index = int(match.group(1))
                        text = match.group(2).strip()
                        decoded[index] = text
                        decoded_line = True
                        logger.info(f"✓ Matched pattern for index {index}: {text[:50]}...")
                        break
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse match: {e}")
                    continue

        if not decoded_line:
            logger.warning(f"⚠️  Unmatched line: {line[:100]}...")

    logger.info(f"✅ Decoding complete: {len(decoded)} entries from {len(lines)} lines")
    if len(decoded) == 0 and len(lines) > 0:
        logger.error(f"❌ No markers found in {len(lines)} lines of response")
        logger.error("Response preview:")
        for i, line in enumerate(lines[:5], 1):
            logger.error(f"  {i}: {line[:80]}...")
    
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
    logger.info(f"=== VALIDATION CHECK ===")
    logger.info(f"Expected indices ({len(expected_indices)}): {expected_indices}")
    logger.info(f"Decoded indices ({len(decoded)}): {list(decoded.keys())}")
    
    if len(decoded) < len(expected_indices):
        logger.warning(f"⚠️  Potential issue: Only {len(decoded)}/{len(expected_indices)} entries decoded")
    
    # Check for missing indices
    missing_indices = [idx for idx in expected_indices if idx not in decoded]
    if missing_indices:
        logger.error(f"❌ MISSING INDICES: {missing_indices}")
        logger.error("This suggests the translation service returned a different format than expected")
        logger.error("Expected marker format: <T1> text, <T2> text, etc.")
        logger.error("Please check the response analysis logs above for actual format")
    
    if len(decoded) != len(expected_indices):
        missing_count = len(expected_indices) - len(decoded)
        error_msg = f"Index count mismatch: expected {len(expected_indices)}, got {len(decoded)} ({missing_count} missing)"
        logger.error(f"❌ VALIDATION FAILED: {error_msg}")
        return False, error_msg

    if missing_indices:
        error_msg = f"Missing indices: {missing_indices[:10]}" + ("..." if len(missing_indices) > 10 else "")
        logger.error(f"❌ VALIDATION FAILED: {error_msg}")
        return False, error_msg

    logger.info("✅ VALIDATION PASSED: All expected indices present")
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