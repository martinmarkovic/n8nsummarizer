"""YouTube helper functions for TranscribeModel."""

from __future__ import annotations

import re
from typing import Optional

from utils.logger import logger


def get_youtube_title(url: str) -> Optional[str]:
    """Fetch YouTube video title for output naming.

    Uses yt-dlp if available, otherwise falls back to youtube-dl.
    """

    try:
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
        except ImportError:
            try:
                import youtube_dl

                ydl_opts = {"quiet": True, "no_warnings": True}
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get("title")
                    if title:
                        title = re.sub(r"[\\/*?:\"<>|]", "_", title)
                        if len(title) > 200:
                            title = title[:200]
                        return title
            except ImportError:
                logger.warning("Neither yt-dlp nor youtube-dl available")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch YouTube title: %s", exc)

    return None


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


def validate_youtube_url(url: str) -> bool:
    """Return True if *url* looks like a YouTube URL."""

    url_lower = url.lower()
    youtube_patterns = [
        "youtube.com/watch",
        "youtu.be/",
        "youtube.com/embed/",
        "youtube.com/v/",
    ]
    return any(pattern in url_lower for pattern in youtube_patterns)
