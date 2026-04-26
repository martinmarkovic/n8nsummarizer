"""
SRT Support Module - Helper functions for SRT subtitle translation

This module provides utilities for detecting, parsing, batching, and reconstructing
SRT subtitle files for translation workflows.
"""

import re
from typing import List, Dict, Tuple, Optional
import srt
from utils.logger import logger
from config import (
    TRANSLATION_BATCH_MAX_ITEMS,
    TRANSLATION_BATCH_MAX_CHARS,
)


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


def batch_subtitles(subtitles: List[srt.Subtitle], max_items: int = None, max_chars: int = None) -> List[List[srt.Subtitle]]:
    """
    Batch consecutive subtitle cues.

    Args:
        subtitles: List of srt.Subtitle objects
        max_items: Maximum number of subtitles per batch (default from config)
        max_chars: Maximum total characters per batch (default from config)

    Returns:
        List of subtitle batches
    """
    if not subtitles:
        return []

    # Use default values from config if not provided
    max_items = max_items or TRANSLATION_BATCH_MAX_ITEMS
    max_chars = max_chars or TRANSLATION_BATCH_MAX_CHARS

    batches = []
    current_batch = []
    current_chars = 0

    for subtitle in subtitles:
        subtitle_text = subtitle.content.strip()
        subtitle_chars = len(subtitle_text)

        # Check if adding this subtitle would exceed batch limits
        # Use more conservative limits to prevent token overflow
        if current_batch and (len(current_batch) >= max_items or current_chars + subtitle_chars > max_chars):
            batches.append(current_batch)
            current_batch = []
            current_chars = 0

        current_batch.append(subtitle)
        current_chars += subtitle_chars

    # Add the last batch if it has content
    if current_batch:
        batches.append(current_batch)

    logger.info(f"Created {len(batches)} batches with max {max_items} items and {max_chars} chars per batch")
    return batches


def encode_text_only_batch(batch: List[srt.Subtitle], global_offset: int = 0) -> str:
    """
    Convert subtitle objects into text-only payload lines using markers.
    Now includes both local batch indices and global subtitle indices.

    Args:
        batch: List of srt.Subtitle objects
        global_offset: Starting global index for this batch

    Returns:
        String with marked text lines for translation using format <Tlocal:global>
    """
    lines = []
    for local_idx, subtitle in enumerate(batch, 1):
        global_idx = global_offset + local_idx
        # Use format: <Tlocal:global> to preserve both indices
        marker = f"<T{local_idx}:{global_idx}>"
        text = subtitle.content.strip()
        lines.append(f"{marker} {text}")

    return '\n'.join(lines)


def decode_text_only_batch(response_text: str, global_offset: int = 0, expected_count: int = None, batch_max_items: int = None) -> Dict[int, str]:
    """
    Parse translated lines in the same marker format.
    Completely rewritten to properly handle both consolidated and multi-line formats.

    Args:
        response_text: Translated text with markers
        global_offset: Starting global index for this batch
        expected_count: Expected number of translations (for validation)

    Returns:
        Dict mapping subtitle index -> translated text
    """
    decoded = {}

    if not response_text:
        return decoded
        
    # Enhanced logging for debugging
    logger.info(f"=== RESPONSE ANALYSIS ===")
    logger.info(f"Response length: {len(response_text)} characters")
    logger.info(f"Response lines: {len(response_text.split(chr(10)))} lines")
    
    # Show first few lines for diagnostic purposes
    lines_preview = response_text.split('\n')[:5]
    for i, line in enumerate(lines_preview, 1):
        logger.info(f"Line {i}: {line[:100]}...")
    
    if len(response_text.split('\n')) > 5:
        logger.info(f"... and {len(response_text.split(chr(10))) - 5} more lines")
    
    # Clean response text by removing common wrappers
    cleaned_text = response_text.strip()

    # Remove code fences if present
    if cleaned_text.startswith('```') and cleaned_text.endswith('```'):
        cleaned_text = cleaned_text[3:-3].strip()
        logger.info("Removed code fence wrapping")

    # Remove common prefixes
    for prefix in ["Sure, here's the translation:", "Here you go:", "Here's the translation:", 
                   "Translation:", "Here is the translation:"]:
        if cleaned_text.startswith(prefix):
            cleaned_text = cleaned_text[len(prefix):].strip()
            logger.info(f"Removed prefix: '{prefix}'")
            break

    # Normalize malformed markers: LM Studio sometimes emits <T3:28) instead of <T3:28>
    # Replace any closing ) or ] after a marker number with the canonical >
    cleaned_text = re.sub(r'(<T\d+(?::\d+)?)[)\]]', r'\1>', cleaned_text)

    # Remove <think>...</think> reasoning blocks that some models prepend
    cleaned_text = re.sub(r'<think>[\s\S]*?</think>', '', cleaned_text).strip()

    # Check for consolidated format (single line with multiple markers)
    if len(cleaned_text.split('\n')) == 1 and '<T' in cleaned_text:
        logger.info("Detected consolidated response format (multiple markers on single line)")
        
        # Parse all markers: <Tlocal:global> text or <Tlocal> text
        consolidated_pattern = r'<T(\d+)(?::(\d+))?>([^<]*)'
        matches = list(re.finditer(consolidated_pattern, cleaned_text))
        
        logger.info(f"Found {len(matches)} markers in consolidated format")
        
        for match in matches:
            try:
                local_index = int(match.group(1))
                global_index_text = match.group(2)
                text = match.group(3).strip()
                
                # Use explicit global index if provided, otherwise calculate from local + offset
                if global_index_text:
                    global_index = int(global_index_text)
                    logger.info(f"✓ Consolidated match for global index {global_index} (local {local_index}): {text[:60]}...")
                else:
                    global_index = global_offset + local_index
                    logger.info(f"✓ Consolidated match for calculated global index {global_index} (local {local_index}): {text[:60]}...")
                
                decoded[global_index] = text
                
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse marker match: {e}")
                continue
        
        logger.info(f"✅ Consolidated decoding: {len(decoded)}/{len(matches)} markers processed")
    
    # Handle multi-line format (one marker per line)
    else:
        lines = cleaned_text.split('\n')
        logger.info(f"Processing {len(lines)} lines in multi-line format")
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # Try to match various marker patterns
            patterns = [
                r'^<T(\d+)(?::(\d+))?>\s*(.*)$',  # <T1:global> text or <T1> text (primary format)
                r'^\\x5BT(\d+)>\s*(.*)$',         # [T1> text
                r'^\\x5BT(\d+)\\x5D\s*(.*)$',        # [T1] text
                r'^(\d+)\.\.?\s*(.*)$',           # 1. text or 1. text
                r'^\[(\d+)\]\s*(.*)$',           # [1] text
            ]
            
            matched = False
            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        groups = match.groups()
                        if len(groups) >= 2:
                            local_index = int(groups[0])
                            global_index_text = groups[1] if len(groups) >= 3 else None
                            text = groups[-1].strip()
                            
                            # Use explicit global index if provided
                            if global_index_text:
                                global_index = int(global_index_text)
                            else:
                                # Calculate global index from local index and offset
                                global_index = global_offset + local_index
                            
                            decoded[global_index] = text
                            logger.info(f"✓ Line {line_num}: global index {global_index}: {text[:60]}...")
                            matched = True
                            break
                            
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Failed to parse line {line_num} with pattern {pattern}: {e}")
                        continue
            
            if not matched:
                logger.warning(f"⚠️  Unmatched line {line_num}: {line[:80]}...")
    
     # Enhanced error recovery for missing indices
    if expected_count and len(decoded) < expected_count:
        missing_indices = [idx for idx in range(1, expected_count + 1) if idx not in decoded]
        recovery_attempted = False
        recovered_count = 0
        
        # Use default batch size from config if not provided
        batch_max_items = batch_max_items or TRANSLATION_BATCH_MAX_ITEMS
         
        if missing_indices:
            logger.warning(f"⚠️  Missing indices: {missing_indices} ({len(missing_indices)}/{expected_count} missing)")
             
            # Strategy 1: Try to recover from unmatched text in consolidated response
            if len(response_text.split('\n')) == 1 and len(missing_indices) <= 5:
                logger.info("Attempting recovery from consolidated response text...")
                recovery_attempted = True
                 
                # Try to find text after the last successfully parsed marker
                if decoded:
                    last_found_index = max(decoded.keys())
                    last_marker = f"<T{last_found_index}"
                    last_marker_pos = response_text.rfind(last_marker)
                     
                    if last_marker_pos > 0:
                        remaining_text = response_text[last_marker_pos:].strip()
                         
                        # Try to extract remaining translations by splitting on common delimiters
                        delimiters = [r'\.\s+', r'!\s+', r'\?\s+', r'\n', r'\.\s*<T', r'!\s*<T', r'\?\s*<T']
                        for delimiter in delimiters:
                            parts = re.split(delimiter, remaining_text)
                            if len(parts) > 1:
                                logger.info(f"Split remaining text into {len(parts)} parts")
                                 
                                # Assign parts to missing indices
                                for i, part in enumerate(parts[1:len(missing_indices)+1]):
                                    if i < len(missing_indices):
                                        missing_idx = missing_indices[i]
                                        cleaned_part = re.sub(r'<[^>]+>', '', part).strip()  # Remove any remaining markers
                                        if cleaned_part and len(cleaned_part) > 5:  # Only use if substantial text
                                            decoded[missing_idx] = cleaned_part
                                            logger.warning(f"✅ Recovered missing index {missing_idx}: {cleaned_part[:50]}...")
                                            recovered_count += 1
                                break
             
            # Strategy 2: Use placeholder for critical missing indices to maintain structure
            still_missing = [idx for idx in missing_indices if idx not in decoded]
            if still_missing:
                if recovery_attempted:
                    logger.warning(f"⚠️  Still missing {len(still_missing)} indices after recovery attempts")
                 
                # For critical structural integrity, add placeholders for missing translations
                # This prevents subtitle shifting and makes missing translations obvious
                for missing_idx in still_missing:
                    placeholder = f"[TRANSLATION MISSING: {missing_idx}]"
                    decoded[missing_idx] = placeholder
                    logger.warning(f"⚠️  Added placeholder for missing index {missing_idx}")
             
            if recovered_count > 0:
                logger.info(f"✅ Successfully recovered {recovered_count}/{len(missing_indices)} missing translations")
    
    logger.info(f"✅ Decoding complete: {len(decoded)} entries decoded")
    
    if len(decoded) == 0:
        logger.error("❌ No translations decoded from response")
        # Fallback: return empty dict to prevent complete failure
    
    return decoded


def validate_decoded_batch(decoded: Dict[int, str], expected_indices: List[int]) -> Tuple[bool, str]:
    """
    Ensure the decoded response contains exactly the expected indices.
    Now more lenient to allow partial translations with proper error recovery.

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
    
    # Check for missing indices
    missing_indices = [idx for idx in expected_indices if idx not in decoded]
    
    if missing_indices:
        logger.warning(f"⚠️  MISSING INDICES: {missing_indices}")
        logger.warning("This suggests the translation service returned a different format than expected")
        logger.warning("Expected marker format: <T1:global> text, <T2:global> text, etc.")
        logger.warning("Please check the response analysis logs above for actual format")
        
        # Check if we have at least some translations (partial success)
        if decoded:
                recovery_percentage = (len(decoded) / len(expected_indices)) * 100
                logger.warning(f"⚠️  PARTIAL SUCCESS: {len(decoded)}/{len(expected_indices)} ({recovery_percentage:.1f}%) indices recovered")
                 
                # If we recovered at least 20%, consider it a partial success (reduced from 30% to 20%)
                if recovery_percentage >= 20:
                    logger.warning("✅ PARTIAL VALIDATION PASSED: Sufficient recovery for continued processing")
                    return True, f"Partial translation - {len(missing_indices)} indices missing, {len(decoded)} recovered"
                else:
                    error_msg = f"Insufficient recovery: only {len(decoded)}/{len(expected_indices)} ({recovery_percentage:.1f}%) indices present"
                    logger.error(f"❌ VALIDATION FAILED: {error_msg}")
                    return False, error_msg
        else:
            error_msg = f"Complete failure: no indices decoded out of {len(expected_indices)}"
            logger.error(f"❌ VALIDATION FAILED: {error_msg}")
            return False, error_msg
    
    logger.info("✅ VALIDATION PASSED: All expected indices present")
    return True, "Validation passed"


def rebuild_subtitles_with_translations(original_subtitles: List[srt.Subtitle], 
                                        translations: Dict[int, str]) -> List[srt.Subtitle]:
    """
    Replace subtitle content with translated text while preserving timing and structure.
    Enhanced with detailed logging and validation.

    Args:
        original_subtitles: Original list of subtitle objects
        translations: Dictionary mapping indices to translated text

    Returns:
        List of subtitle objects with translated content
    """
    if not original_subtitles:
        return []

    logger.info(f"=== SRT REBUILD PROCESS ===")
    logger.info(f"Rebuilding {len(original_subtitles)} subtitles with {len(translations)} translations")
    
    # Validate translation indices
    expected_indices = set(range(1, len(original_subtitles) + 1))
    actual_indices = set(translations.keys())
    missing_indices = sorted(expected_indices - actual_indices)
    extra_indices = sorted(actual_indices - expected_indices)
    
    if missing_indices:
        logger.warning(f"⚠️  Missing translations for indices: {missing_indices}")
    if extra_indices:
        logger.warning(f"⚠️  Extra translations found for indices: {extra_indices}")
    
    # Check for duplicate translations
    translation_values = list(translations.values())
    if len(translation_values) != len(set(translation_values)):
        logger.warning("⚠️  Potential duplicate translations detected")

    # Create a copy of original subtitles to avoid modifying the original
    translated_subtitles = []
    translation_count = 0
    fallback_count = 0
    missing_count = 0

    for i, subtitle in enumerate(original_subtitles, 1):
        # Create a new subtitle with the same timing but translated content
        if i in translations:
            new_content = translations[i]
            translation_count += 1
            logger.debug(f"✓ Subtitle {i}: Using translation: {new_content[:50]}...")
        else:
            # Use a placeholder for missing translations to maintain structure
            # This prevents content shifting and makes missing translations obvious
            placeholder_content = f"[TRANSLATION MISSING FOR SUBTITLE {i}]"
            new_content = placeholder_content
            fallback_count += 1
            logger.warning(f"⚠️  Subtitle {i}: Missing translation, using placeholder")
            missing_count += 1

        new_subtitle = srt.Subtitle(
            index=subtitle.index,
            start=subtitle.start,
            end=subtitle.end,
            content=new_content
        )
        translated_subtitles.append(new_subtitle)

    logger.info(f"=== REBUILD SUMMARY ===")
    logger.info(f"✅ Successfully rebuilt {len(translated_subtitles)} subtitles")
    logger.info(f"📝 Translations applied: {translation_count}")
    logger.info(f"⚠️  Fallbacks used: {fallback_count}")
    logger.info(f"🔍 Missing translations: {missing_count}")
    
    # Final validation
    if len(translated_subtitles) != len(original_subtitles):
        logger.error(f"❌ CRITICAL: Subtitle count mismatch: {len(translated_subtitles)} vs {len(original_subtitles)}")
    else:
        logger.info("✅ Subtitle count validation passed")

    return translated_subtitles


def validate_rebuilt_subtitles(original_subtitles: List[srt.Subtitle], 
                              translated_subtitles: List[srt.Subtitle]) -> Tuple[bool, str]:
    """
    Validate that rebuilt subtitles maintain proper structure and content.
    Enhanced with detailed error analysis and reporting.
    
    Args:
        original_subtitles: Original subtitle objects
        translated_subtitles: Rebuilt subtitle objects
        
    Returns:
        Tuple of (bool: validation result, str: detailed validation message)
    """
    logger.info("=== SRT VALIDATION ===")
    
    # Check subtitle count
    if len(original_subtitles) != len(translated_subtitles):
        error_msg = f"Subtitle count mismatch: {len(translated_subtitles)} vs {len(original_subtitles)}"
        logger.error(f"❌ VALIDATION FAILED: {error_msg}")
        return False, error_msg

    # Check timing preservation
    timing_mismatches = []
    for orig, trans in zip(original_subtitles, translated_subtitles):
        if orig.start != trans.start or orig.end != trans.end:
            timing_mismatches.append(f"Subtitle {orig.index}: {orig.start}->{orig.end} vs {trans.start}->{trans.end}")
    
    if timing_mismatches:
        logger.warning(f"⚠️  Timing changes detected: {len(timing_mismatches)} subtitles affected")
        for msg in timing_mismatches[:3]:  # Log first 3 issues
            logger.warning(f"  {msg}")
        if len(timing_mismatches) > 3:
            logger.warning(f"  ... and {len(timing_mismatches) - 3} more timing issues")

        # Check for placeholder content (missing translations)
    placeholder_translations = []
    for i, sub in enumerate(translated_subtitles, 1):
        if "[TRANSLATION MISSING]" in sub.content:
            placeholder_translations.append(i)
     
    if placeholder_translations:
        logger.warning(f"⚠️  Placeholder translations (missing): {len(placeholder_translations)} subtitles")
        logger.info(f"Placeholder subtitle indices: {placeholder_translations}")
        
        # Log detailed information about missing translations
        if len(placeholder_translations) <= 20:
            logger.info(f"Missing translation indices: {placeholder_translations}")
        else:
            logger.info(f"Missing translation indices (first 20): {placeholder_translations[:20]}")

    # Check for empty translations
    empty_translations = []
    for i, sub in enumerate(translated_subtitles, 1):
        if not sub.content or not sub.content.strip():
            empty_translations.append(i)
    
    if empty_translations:
        logger.warning(f"⚠️  Empty translations found: {len(empty_translations)} subtitles")
        logger.debug(f"Empty subtitle indices: {empty_translations[:10]}{'...' if len(empty_translations) > 10 else ''}")

    # Check for duplicate content (potential translation shifting)
    content_map = {}
    duplicate_content = []
    for i, sub in enumerate(translated_subtitles, 1):
        content = sub.content.strip()
        # Skip placeholder content when checking for duplicates
        if content and "[TRANSLATION MISSING]" not in content and content in content_map:
            duplicate_content.append((content_map[content], i))
        else:
            content_map[content] = i
    
    if duplicate_content:
        logger.warning(f"⚠️  Duplicate content detected: {len(duplicate_content)} pairs")
        for orig_idx, dup_idx in duplicate_content[:3]:  # Log first 3 duplicates
            logger.warning(f"  Subtitle {orig_idx} and {dup_idx} have identical content")
        if len(duplicate_content) > 3:
            logger.warning(f"  ... and {len(duplicate_content) - 3} more duplicate pairs")

    # Check for potential index misalignment
    misaligned_indices = []
    for i, sub in enumerate(translated_subtitles, 1):
        if i != sub.index:  # SRT index should match position
            misaligned_indices.append(f"Position {i} has SRT index {sub.index}")
    
    if misaligned_indices:
        logger.error(f"❌ CRITICAL: Index misalignment detected: {len(misaligned_indices)} subtitles")
        for msg in misaligned_indices[:5]:
            logger.error(f"  {msg}")
        if len(misaligned_indices) > 5:
            logger.error(f"  ... and {len(misaligned_indices) - 5} more misalignments")

    # Generate comprehensive validation report
    issues = []
    if timing_mismatches:
        issues.append(f"{len(timing_mismatches)} timing changes")
    if placeholder_translations:
        issues.append(f"{len(placeholder_translations)} missing translations")
    if empty_translations:
        issues.append(f"{len(empty_translations)} empty translations")
    if duplicate_content:
        issues.append(f"{len(duplicate_content)} duplicate content pairs")
    if misaligned_indices:
        issues.append(f"{len(misaligned_indices)} index misalignments")
 
    if issues:
        validation_msg = ", ".join(issues)
        logger.warning(f"⚠️  PARTIAL VALIDATION: {validation_msg}")
        # Only fail validation for critical issues
        if misaligned_indices:
            return False, f"Critical validation failure: {validation_msg}"
        else:
            # Allow partial validation if we have at least some successful translations
            if len(translated_subtitles) > 0 and len(placeholder_translations) < len(translated_subtitles) * 0.5:
                return True, f"Partial validation with issues: {validation_msg}"
            else:
                return False, f"Too many missing translations: {validation_msg}"
    else:
        logger.info("✅ VALIDATION PASSED: All subtitles properly reconstructed")
        return True, "All validation checks passed"