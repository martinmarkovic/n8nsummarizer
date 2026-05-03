"""
Comprehensive test for SRT translation pipeline
Tests all scenarios: perfect markers, consolidated format, truncated responses

Note: This file has been moved from root to tests/ directory as part of Phase 3 cleanup.
"""

import sys
sys.path.insert(0, '..')

from models.translation.srt_support import (
    decode_text_only_batch,
    validate_decoded_batch,
    parse_srt,
    compose_srt,
    batch_subtitles,
    encode_text_only_batch
)

def test_all_scenarios():
    """Test all SRT response scenarios"""
    
    print("=== SRT Translation Pipeline: Comprehensive Test ===")
    
    # Test 1: Perfect multi-line markers
    print("\n1. Testing perfect multi-line markers...")
    perfect_response = '''<T1> First subtitle
<T2> Second subtitle
<T3> Third subtitle'''
    
    result1 = decode_text_only_batch(perfect_response, 3)
    valid1, msg1 = validate_decoded_batch(result1, [1, 2, 3])
    print(f"   Result: {len(result1)} entries, Validation: {valid1}")
    assert len(result1) == 3 and valid1, "Perfect markers failed"
    
    # Test 2: Consolidated format
    print("\n2. Testing consolidated format...")
    consolidated_response = '<T1> First <T2> Second <T3> Third'
    
    result2 = decode_text_only_batch(consolidated_response, 3)
    valid2, msg2 = validate_decoded_batch(result2, [1, 2, 3])
    print(f"   Result: {len(result2)} entries, Validation: {valid2}")
    assert len(result2) == 3 and valid2, "Consolidated format failed"
    
    # Test 3: Truncated response
    print("\n3. Testing truncated response...")
    truncated_response = '<T1> First <T2> Second <T3> Partial'
    
    result3 = decode_text_only_batch(truncated_response, 40)
    print(f"   Result: {len(result3)} entries (expected 40)")
    # Should get 3 entries and trigger position fallback
    
    # Test 4: Mixed format
    print("\n4. Testing mixed format...")
    mixed_response = '''<T1> First line
<T2> Second line
<T3> Third line <T4> Fourth on same line'''
    
    result4 = decode_text_only_batch(mixed_response, 4)
    print(f"   Result: {len(result4)} entries")
    valid4, msg4 = validate_decoded_batch(result4, [1, 2, 3, 4])
    print(f"   Validation: {valid4}")
    
    # Test 5: Full pipeline
    print("\n5. Testing full SRT roundtrip...")
    srt_content = '''1
00:00:01,000 --> 00:00:03,000
First subtitle

2
00:00:03,500 --> 00:00:05,000
Second subtitle'''
    
    subtitles = parse_srt(srt_content)
    print(f"   Parsed {len(subtitles)} subtitles")
    
    batches = batch_subtitles(subtitles)
    print(f"   Created {len(batches)} batches")
    
    encoded = encode_text_only_batch(batches[0])
    print(f"   Encoded batch:\n{encoded}")
    
    # Test complete pipeline
    print("\n=== All Tests Completed ===")

if __name__ == "__main__":
    test_all_scenarios()