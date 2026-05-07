#!/usr/bin/env python3
"""
Test script for prompt presets and LLM configuration
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_prompt_presets():
    """Test the prompt presets module"""
    print("Testing prompt presets...")
    
    try:
        from utils.prompt_presets import PROMPT_PRESETS, DEFAULT_PROMPT_KEY, PRESET_NAMES, get_prompt_with_content
        
        # Test 1: Check all presets exist
        expected_presets = [
            "General Summary",
            "Meeting Notes", 
            "Technical Document",
            "Research / Article",
            "Interview / Transcript"
        ]
        
        assert len(PROMPT_PRESETS) == 5, f"Expected 5 presets, got {len(PROMPT_PRESETS)}"
        
        for preset_name in expected_presets:
            assert preset_name in PROMPT_PRESETS, f"Missing preset: {preset_name}"
            print(f"[OK] Found preset: {preset_name}")
        
        # Test 2: Check default key
        assert DEFAULT_PROMPT_KEY == "General Summary", f"Default key should be 'General Summary', got {DEFAULT_PROMPT_KEY}"
        print(f"[OK] Default prompt key: {DEFAULT_PROMPT_KEY}")
        
        # Test 3: Check preset names list
        assert PRESET_NAMES == list(PROMPT_PRESETS.keys()), "PRESET_NAMES doesn't match preset keys"
        print(f"[OK] Preset names list: {len(PRESET_NAMES)} items")
        
        # Test 4: Test get_prompt_with_content function
        test_content = "This is test content for summarization."
        prompt = get_prompt_with_content("General Summary", test_content)
        assert test_content in prompt, "Content not found in generated prompt"
        print(f"[OK] get_prompt_with_content() works correctly")
        
        # Test 5: Check prompt structure
        general_prompt = PROMPT_PRESETS["General Summary"]
        assert "{content}" in general_prompt, "Prompt should contain {content} placeholder"
        print(f"[OK] Prompts contain proper placeholders")
        
        print("\n[SUCCESS] All prompt presets tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Prompt presets test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_configuration():
    """Test the LLM configuration"""
    print("\nTesting LLM configuration...")
    
    try:
        from config import LLM_WEBHOOK_URL, LLM_MODEL, LLM_TIMEOUT
        
        # Test default values
        assert LLM_WEBHOOK_URL == "http://localhost:1234", f"Expected default LLM_WEBHOOK_URL, got {LLM_WEBHOOK_URL}"
        print(f"[OK] LLM_WEBHOOK_URL: {LLM_WEBHOOK_URL}")
        
        assert LLM_MODEL == "local-model", f"Expected default LLM_MODEL, got {LLM_MODEL}"
        print(f"[OK] LLM_MODEL: {LLM_MODEL}")
        
        assert LLM_TIMEOUT == 120, f"Expected default LLM_TIMEOUT of 120, got {LLM_TIMEOUT}"
        assert isinstance(LLM_TIMEOUT, int), f"LLM_TIMEOUT should be int, got {type(LLM_TIMEOUT)}"
        print(f"[OK] LLM_TIMEOUT: {LLM_TIMEOUT} (type: {type(LLM_TIMEOUT).__name__})")
        
        print("\n[SUCCESS] All LLM configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ LLM configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_env_file():
    """Test that .env.example has been updated"""
    print("\nTesting .env.example updates...")
    
    try:
        with open('.env.example', 'r') as f:
            content = f.read()
        
        # Check for LLM configuration entries
        required_entries = [
            "LLM_WEBHOOK_URL=",
            "LLM_MODEL=",
            "LLM_TIMEOUT="
        ]
        
        for entry in required_entries:
            assert entry in content, f"Missing entry in .env.example: {entry}"
            print(f"[OK] Found in .env.example: {entry}")
        
        # Check for comment section
        assert "LLM Webhook" in content, "Missing LLM Webhook comment section"
        print("[OK] Found LLM Webhook comment section")
        
        print("\n[SUCCESS] All .env.example tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ .env.example test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing v9.0 LLM and Prompt Presets Implementation")
    print("=" * 60)
    
    results = []
    
    # Run all test functions
    results.append(test_prompt_presets())
    results.append(test_llm_configuration())
    results.append(test_env_file())
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"[SUCCESS] ALL TESTS PASSED ({passed}/{total})")
        print("\n[SUCCESS] v9.0 implementation is working correctly!")
        return 0
    else:
        print(f"[FAILED] SOME TESTS FAILED ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(main())