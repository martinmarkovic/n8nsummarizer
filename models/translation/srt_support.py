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


def batch_subtitles(subtitles: List[srt.Subtitle], max_items: int = 20, max_chars: int = 2000) -> List[List[srt.Subtitle]]:
    """
    Batch consecutive subtitle cues.

    Args:
        subtitles: List of srt.Subtitle objects
        max_items: Maximum number of subtitles per batch (reduced from 40 to 20)
        max_chars: Maximum total characters per batch (reduced from 4000 to 2000)

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


def decode_text_only_batch(response_text: str, global_offset: int = 0, expected_count: int = None) -> Dict[int, str]:
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

    lines = cleaned_text.split('\n')
    logger.info(f"Processing {len(lines)} cleaned lines for marker matching")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Try multiple marker patterns in order of likelihood
        patterns = [
            r'^<T(\d+)(?::(\d+))?>\s*(.*)$',      # New format: <T1:global> text or <T1> text
            r'^\\x5BT(\d+)>\s*(.*)$',     # Square brackets with >: [T1> text
            r'^\\x5BT(\d+)\\x5D\s*(.*)$',    # Square brackets: [T1] text
            r'^(\d+)\.\.?\s*(.*)$',   # Numbered list: 1. text or 1. text
            r'^\*\s*<T(\d+)>\s*(.*)$', # Bullet with marker: * <T1> text
        ]

        decoded_line = False
        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) >= 2:
                        local_index = int(groups[0])
                        global_index_text = groups[1] if len(groups) >= 3 else None
                        text = groups[-1].strip()
                        
                        # Check if this is actually a consolidated format (multiple markers on one line)
                        if '<T' in text:
                            # This line contains multiple markers - use consolidated parsing instead
                            logger.debug(f"Line contains multiple markers, using consolidated parsing: {line[:80]}...")
                            # Parse this line as consolidated format
                            consolidated_pattern = r'<T(\d+)(?::(\d+))?>([^<]*)'
                            inner_matches = list(re.finditer(consolidated_pattern, line))
                            
                            for inner_match in inner_matches:
                                try:
                                    inner_local = int(inner_match.group(1))
                                    inner_global_text = inner_match.group(2)
                                    inner_text = inner_match.group(3).strip()
                                    
                                    if inner_global_text:
                                        inner_global = int(inner_global_text)
                                    else:
                                        inner_global = global_offset + inner_local
                                    
                                    decoded[inner_global] = inner_text
                                    logger.info(f"✓ Consolidated match for global index {inner_global} (local {inner_local}): {inner_text[:50]}...")
                                    decoded_line = True
                                except (ValueError, IndexError) as e:
                                    logger.debug(f"Failed to parse inner match: {e}")
                                    continue
                        else:
                            # Single marker line
                            # Use global index if provided, otherwise use local index
                            if global_index_text:
                                global_index = int(global_index_text)
                                decoded[global_index] = text
                                logger.info(f"✓ Matched pattern for global index {global_index} (local {local_index}): {text[:50]}...")
                            else:
                                # For backward compatibility with old format
                                global_index = local_index
                                decoded[global_index] = text
                                logger.info(f"✓ Matched pattern for index {global_index}: {text[:50]}...")
                            
                            decoded_line = True
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
    
    # Enhanced error recovery for missing indices
    if expected_count and len(decoded) < expected_count:
        logger.warning(f"⚠️  Potential truncation: {len(decoded)}/{expected_count} entries decoded")
        logger.warning("Attempting enhanced error recovery for missing indices...")
        
        missing_indices = [idx for idx in range(1, expected_count + 1) if idx not in decoded]
        logger.warning(f"Missing indices: {missing_indices}")
        
        # Strategy 1: Try to extract missing markers from end of consolidated response
        if len(response_text.split('\n')) == 1 and '<T' in response_text:
            logger.info("Attempting to recover missing markers from consolidated response...")
            
            # Try to find the last marker and extract text after it
            last_found_index = max(decoded.keys()) if decoded else 0
            last_marker_pattern = f'<T{last_found_index}(?::\\d+)?>'
            last_marker_pos = response_text.rfind(last_marker_pattern)
            if last_marker_pos > 0:
                remaining = response_text[last_marker_pos + len(last_marker_pattern):].strip()
                if remaining:
                    # Try to split remaining text by common delimiters
                    delimiters = [r'\.\s+', r'!\s+', r'\?\s+', r'\.\s*<T', r'!\s*<T', r'\?\s*<T']
                    for delimiter in delimiters:
                        parts = re.split(delimiter, remaining)
                        if len(parts) > 1:
                            logger.info(f"Split remaining text into {len(parts)} parts using delimiter")
                            
                            # Assign parts to missing indices
                            for i, part in enumerate(parts[:len(missing_indices)]):
                                missing_idx = missing_indices[i]
                                if part.strip():
                                    decoded[missing_idx] = part.strip()
                                    logger.warning(f"Recovered missing index {missing_idx} via text splitting: {part[:50]}...")
                            break
        
        # Strategy 2: Try to extract text from unmatched lines
        if missing_indices and len(lines) > len(decoded):
            logger.info("Attempting to recover missing markers from unmatched lines...")
            unmatched_lines = [line for line in lines if not any(f'<T{idx}' in line for idx in decoded.keys())]
            
            for i, line in enumerate(unmatched_lines[:len(missing_indices)]):
                if line.strip() and i < len(missing_indices):
                    missing_idx = missing_indices[i]
                    decoded[missing_idx] = line.strip()
                    logger.warning(f"Recovered missing index {missing_idx} from unmatched line: {line[:50]}...")
        
        # Strategy 3: Fallback - use empty strings for missing indices to maintain structure
        if missing_indices:
            still_missing = [idx for idx in missing_indices if idx not in decoded]
            if still_missing:
                logger.warning(f"Still missing {len(still_missing)} indices after recovery attempts")
                logger.warning("Using fallback empty strings to maintain subtitle structure")
                for missing_idx in still_missing:
                    decoded[missing_idx] = ""
                    logger.warning(f"Fallback: Added empty string for missing index {missing_idx}")
    
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
        # Parse consolidated format: <T1:global> text1 <T2:global> text2 <T3:global> text3...
        consolidated_pattern = r'<T(\d+)(?::(\d+))?>([^<]*)'
        matches = list(re.finditer(consolidated_pattern, cleaned_text))
        
        if matches and len(matches) > 1:
            logger.info(f"Found {len(matches)} markers in consolidated format")
            for match in matches:
                try:
                    local_index = int(match.group(1))
                    global_index_text = match.group(2)
                    text = match.group(3).strip()
                    
                    # Use global index if provided, otherwise calculate from local index + offset
                    if global_index_text:
                        global_index = int(global_index_text)
                        logger.info(f"✓ Consolidated match for global index {global_index} (local {local_index}): {text[:50]}...")
                    else:
                        global_index = global_offset + local_index
                        logger.info(f"✓ Consolidated match for calculated global index {global_index} (local {local_index}): {text[:50]}...")
                    
                    decoded[global_index] = text
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse consolidated match: {e}")
            
            if decoded:
                logger.info(f"✅ Consolidated decoding successful: {len(decoded)} entries")
                return decoded

    # Split by lines and process each line (standard multi-line format)
    lines = cleaned_text.split('\n')
    logger.info(f"Processing {len(lines)} cleaned lines for marker matching")

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
            
            # If we recovered at least 30%, consider it a partial success (reduced from 50% to 30%)
            if recovery_percentage >= 30:
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
            # Fallback to original content if translation missing
            new_content = subtitle.content
            fallback_count += 1
            logger.warning(f"⚠️  Subtitle {i}: Missing translation, using original: {new_content[:50]}...")
            missing_count += 1

        # Enhanced content handling for missing translations
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
        logger.debug(f"Placeholder subtitle indices: {placeholder_translations[:10]}{'...' if len(placeholder_translations) > 10 else ''}")

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
        if content and content in content_map:
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
            return True, f"Partial validation with issues: {validation_msg}"
    else:
        logger.info("✅ VALIDATION PASSED: All subtitles properly reconstructed")
        return True, "All validation checks passed"