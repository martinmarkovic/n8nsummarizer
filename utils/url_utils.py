"""
URL Utilities - Helper functions for URL detection and classification

Provides URL detection and classification functions for various platforms.
"""

import re
from urllib.parse import urlparse
from typing import Optional, Tuple


def is_facebook_url(url: str) -> bool:
    """Check if URL is a Facebook video URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be a Facebook video URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
        
    url_lower = url.lower().strip()
    
    # Check for Facebook domains
    facebook_domains = ["facebook.com", "fb.watch", "fb.com", "m.facebook.com"]
    if any(domain in url_lower for domain in facebook_domains):
        return True
        
    # Check for Facebook watch URLs
    if re.search(r'facebook\.com/watch', url_lower):
        return True
        
    # Check for Facebook reel URLs
    if re.search(r'facebook\.com/reel', url_lower):
        return True
        
    # Check for Facebook video URLs
    if re.search(r'facebook\.com/\w+/videos', url_lower):
        return True
        
    return False


def classify_facebook_url(url: str) -> str:
    """Classify Facebook URL type.
    
    Args:
        url: Facebook URL to classify
        
    Returns:
        One of: 'watch', 'reel', 'video', 'fb_watch', 'unknown'
    """
    if not is_facebook_url(url):
        return "unknown"
        
    url_lower = url.lower().strip()
    
    # fb.watch short links
    if "fb.watch/" in url_lower:
        return "fb_watch"
        
    # Watch URLs
    if re.search(r'facebook\.com/watch', url_lower):
        return "watch"
        
    # Reel URLs
    if re.search(r'facebook\.com/reel', url_lower):
        return "reel"
        
    # Standard video URLs
    if re.search(r'facebook\.com/\w+/videos', url_lower):
        return "video"
        
    return "unknown"


def normalize_facebook_url(url: str) -> str:
    """Normalize Facebook URL to consistent format.
    
    Args:
        url: Facebook URL to normalize
        
    Returns:
        Normalized URL, or original URL if normalization fails
    """
    if not is_facebook_url(url):
        return url
        
    try:
        parsed = urlparse(url)
        
        # Handle fb.watch URLs - keep as-is since they're already short
        if "fb.watch" in parsed.netloc:
            return url
            
        # Remove query parameters for cleaner URLs
        if parsed.query:
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return clean_url
            
        return url
        
    except Exception:
        return url


def extract_facebook_video_id(url: str) -> Optional[str]:
    """Extract video ID from Facebook URL.
    
    Args:
        url: Facebook URL
        
    Returns:
        Video ID if found, None otherwise
    """
    if not is_facebook_url(url):
        return None
        
    url_lower = url.lower().strip()
    
    # Try to extract from watch URLs
    watch_match = re.search(r'facebook\.com/watch\?v=([^&]+)', url_lower)
    if watch_match:
        return watch_match.group(1)
        
    # Try to extract from reel URLs
    reel_match = re.search(r'facebook\.com/reel/([^/?]+)', url_lower)
    if reel_match:
        return reel_match.group(1)
        
    # Try to extract from standard video URLs
    video_match = re.search(r'facebook\.com/\w+/videos/([^/?]+)', url_lower)
    if video_match:
        return video_match.group(1)
        
    # Try to extract from fb.watch URLs
    fb_watch_match = re.search(r'fb\.watch/([^/?]+)', url_lower)
    if fb_watch_match:
        return fb_watch_match.group(1)
        
    return None


def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube video URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be a YouTube video URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
        
    url_lower = url.lower().strip()
    
    # Check for YouTube domains
    youtube_domains = ["youtube.com", "youtu.be", "youtube-nocookie.com"]
    if any(domain in url_lower for domain in youtube_domains):
        return True
        
    # Check for YouTube watch URLs
    if re.search(r'youtube\.com/watch', url_lower):
        return True
        
    # Check for YouTube short URLs
    if re.search(r'youtu\.be/', url_lower):
        return True
        
    return False


def is_twitter_url(url: str) -> bool:
    """Check if URL is a Twitter video URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be a Twitter video URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
        
    url_lower = url.lower().strip()
    
    # Check for Twitter domains
    twitter_domains = ["twitter.com", "x.com"]
    if any(domain in url_lower for domain in twitter_domains):
        return True
        
    return False


def is_instagram_url(url: str) -> bool:
    """Check if URL is an Instagram video URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL appears to be an Instagram video URL, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
        
    url_lower = url.lower().strip()
    
    # Check for Instagram domains
    instagram_domains = ["instagram.com", "instagr.am"]
    if any(domain in url_lower for domain in instagram_domains):
        return True
        
    return False