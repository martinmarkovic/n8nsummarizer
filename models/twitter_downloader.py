"""
Twitter/X Downloader Model - yt-dlp wrapper for tweet videos (v6.8)

Handles: single tweet video downloads with unified resolution presets.
Uses the same format mapping as YouTubeDownloader for consistency.
"""

import yt_dlp
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
import logging

from models.youtube_downloader import YouTubeDownloader
from models.base_downloader import BaseDownloader

logger = logging.getLogger(__name__)


class TwitterDownloader(BaseDownloader):
    """Download videos from Twitter/X using yt-dlp.
    
    Extends BaseDownloader with Twitter-specific functionality:
    - Uses YouTubeDownloader's resolution presets for consistency
    - Implements Twitter URL handling and video info extraction
    - Provides Twitter-specific download options
    """
    
    def __init__(self) -> None:
        super().__init__()

    # --------------------------- Twitter-Specific Configuration ---------------------------
    
    def set_po_token(self, token: Optional[str]) -> None:  # Kept for interface compatibility
        # PO tokens are not used for Twitter; ignore.
        return
    
    def get_po_token(self) -> Optional[str]:
        return None
    
    def has_po_token(self) -> bool:
        return False
    
    # Note: set_download_path(), set_resolution(), set_progress_callback(), and _progress_hook()
    # are inherited from BaseDownloader and should not be overridden unless platform-specific
    # behavior is required.

    # --------------------------- Public API ---------------------------

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract tweet video information without downloading."""
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", "Unknown"),
                    "view_count": info.get("view_count", 0),
                }
        except Exception as exc:
            logger.error(f"[Twitter] Error extracting video info: {exc}")
            return None

    def download_video(self, url: str) -> Tuple[bool, str]:
        """Download a Twitter/X video using current settings."""
        if self.is_downloading:
            return False, "Download already in progress"

        # Validate download path using base class utility
        path_ok, path_error = self._ensure_download_path_exists()
        if not path_ok:
            return False, path_error

        # Map resolution preset to yt-dlp format string from YouTubeDownloader
        format_string = YouTubeDownloader.RESOLUTION_FORMATS[self.selected_resolution]

        ydl_opts: Dict[str, Any] = {
            "format": format_string,
            "outtmpl": str(self.download_path / "%(title)s.%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "quiet": False,
            "no_warnings": False,
        }

        # If audio-only preset is selected, extract MP3
        if self.selected_resolution.startswith("Audio Only"):
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]

        self.is_downloading = True
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"[Twitter] Starting download: {url}")
                logger.info(f"[Twitter] Resolution preset: {self.selected_resolution}")
                logger.info(f"[Twitter] Format string: {format_string}")
                logger.info(f"[Twitter] Destination: {self.download_path}")

                ydl.download([url])

            self.is_downloading = False
            return True, f"Twitter/X download completed at {self.selected_resolution} quality."
        except Exception as exc:
            self.is_downloading = False
            error_msg = f"Twitter/X download failed: {exc}"
            logger.error(error_msg)
            return False, error_msg

    # cancel_download() is inherited from BaseDownloader
