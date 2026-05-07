"""YouTube helper functions for TranscribeModel."""

from __future__ import annotations

import re
from typing import Optional

from utils.logger import logger


def get_video_title(url: str) -> Optional[str]:
    """Fetch video title for any yt-dlp-supported URL."""

    try:
        from yt_dlp import YoutubeDL

        ydl_opts = {"quiet": True, "no_warnings": True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title")
            if title:
                title = re.sub(r"[\\/*?:\"<>|]", "_", title)
                if len(title) > 200:
                    title = title[:200]
                return title
    except Exception as exc:
        logger.warning("Could not fetch video title: %s", exc)

    return None


def get_youtube_title(url: str) -> Optional[str]:
    """Backward-compatible alias for get_video_title."""
    return get_video_title(url)


def extract_youtube_id(url: str) -> Optional[str]:
    """Extract video ID from a YouTube URL."""

    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/)([^&\?/]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def extract_video_slug(url: str) -> str:
    """Extract a short identifier from any video URL for use as fallback name."""
    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if parts:
            slug = parts[-1]
            slug = slug.split("?")[0].split("&")[0]
            if slug:
                return re.sub(r"[\\/*?:\"<>|]", "_", slug)[:80]
    except Exception:
        pass

    return "video"


def validate_video_url(url: str) -> bool:
    """Return True if url looks like any yt-dlp-supported video URL."""
    url_lower = url.lower().strip()
    return url_lower.startswith(("http://", "https://"))


def validate_youtube_url(url: str) -> bool:
    """Backward-compatible alias for validate_video_url."""
    return validate_video_url(url)
