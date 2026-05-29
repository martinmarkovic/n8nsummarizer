#!/usr/bin/env python3
"""
Test script for Facebook video downloader functionality.

This script tests the Facebook downloader integration without requiring the full GUI.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.facebook_downloader import FacebookDownloader
from utils.url_utils import is_facebook_url, classify_facebook_url, normalize_facebook_url, extract_facebook_video_id

def test_url_utils():
    """Test Facebook URL utility functions."""
    print("Testing Facebook URL utilities...")
    
    # Test various Facebook URL formats
    test_urls = [
        "https://www.facebook.com/watch?v=123456789",
        "https://fb.watch/abc123/",
        "https://m.facebook.com/watch?v=987654321",
        "https://www.facebook.com/reel/1234567890",
        "https://www.facebook.com/page/videos/123456789/",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Non-Facebook URL
        "invalid-url",
        "",
    ]
    
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        is_fb = is_facebook_url(url)
        print(f"  is_facebook_url: {is_fb}")
        
        if is_fb:
            url_type = classify_facebook_url(url)
            print(f"  classify_facebook_url: {url_type}")
            
            normalized = normalize_facebook_url(url)
            print(f"  normalize_facebook_url: {normalized}")
            
            video_id = extract_facebook_video_id(url)
            print(f"  extract_facebook_video_id: {video_id}")

def test_facebook_downloader():
    """Test Facebook downloader basic functionality."""
    print("\n" + "="*60)
    print("Testing FacebookDownloader...")
    
    try:
        downloader = FacebookDownloader()
        print("[OK] FacebookDownloader created successfully")
        
        # Test basic properties
        print(f"  Download path: {downloader.download_path}")
        print(f"  Selected resolution: {downloader.selected_resolution}")
        print(f"  Is downloading: {downloader.is_downloading}")
        
        # Test cookie settings
        downloader.set_cookie_file("/path/to/cookies.txt")
        print(f"  Cookie file: {downloader.get_cookie_file()}")
        
        downloader.set_cookie_browser("chrome")
        print(f"  Cookie browser: {downloader.get_cookie_browser()}")
        
        # Test resolution setting
        downloader.set_resolution("1080p (Full HD)")
        print(f"  Resolution after change: {downloader.selected_resolution}")
        
        # Test download path setting
        test_path = "/tmp/test_downloads"
        downloader.set_download_path(test_path)
        print(f"  Download path after change: {downloader.download_path}")
        
        print("[OK] All FacebookDownloader tests passed")
        
    except Exception as e:
        print(f"[ERROR] FacebookDownloader test failed: {e}")
        import traceback
        traceback.print_exc()

def test_video_downloader_integration():
    """Test VideoDownloader router integration with Facebook."""
    print("\n" + "="*60)
    print("Testing VideoDownloader integration...")
    
    try:
        from models.video_downloader import VideoDownloader
        
        downloader = VideoDownloader()
        print("✓ VideoDownloader created successfully")
        
        # Test Facebook URL detection
        test_urls = [
            "https://www.facebook.com/watch?v=123456789",
            "https://fb.watch/abc123/",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        ]
        
        for url in test_urls:
            source = downloader._detect_source(url)
            model, detected_source = downloader._active_model_for_url(url)
            is_valid, message = downloader.validate_url(url)
            
            print(f"\nTesting URL: {url}")
            print(f"  Detected source: {source}")
            print(f"  Active model: {type(model).__name__ if model else None}")
            print(f"  Validation: {is_valid} - {message}")
        
        print("[OK] VideoDownloader integration tests passed")
        
    except Exception as e:
        print(f"[ERROR] VideoDownloader integration test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Facebook Video Downloader Test Suite")
    print("="*60)
    
    test_url_utils()
    test_facebook_downloader()
    test_video_downloader_integration()
    
    print("\n" + "="*60)
    print("Test suite completed!")