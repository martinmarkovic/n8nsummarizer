"""
Facebook Downloader Model - yt-dlp wrapper for Facebook videos

Handles: public Facebook video downloads with unified resolution presets.
Uses the same format mapping as YouTubeDownloader for consistency.
"""

import yt_dlp
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
import logging

from models.base_downloader import BaseDownloader
from models.youtube_downloader import YouTubeDownloader

logger = logging.getLogger(__name__)


class FacebookDownloader(BaseDownloader):
    """Download videos from Facebook using yt-dlp.

    Extends BaseDownloader with Facebook-specific functionality:
    - Uses YouTubeDownloader's resolution presets for consistency
    - Implements Facebook URL handling and video info extraction
    - Provides Facebook-specific download options
    """

    def __init__(self) -> None:
        super().__init__()
        self.cookie_file: str = ""
        self.cookie_browser: str = ""

    # --------------------------- Facebook-Specific Configuration ---------------------------

    def set_cookie_file(self, path: str) -> None:
        """Set cookie file path for Facebook private video downloads."""
        self.cookie_file = path
        logger.info(f"[Facebook] Cookie file set: {path}")

    def set_cookie_browser(self, browser: str) -> None:
        """Set browser name for Facebook cookie extraction."""
        self.cookie_browser = browser
        logger.info(f"[Facebook] Cookie browser set: {browser}")

    def get_cookie_file(self) -> str:
        """Get current cookie file path."""
        return self.cookie_file

    def get_cookie_browser(self) -> str:
        """Get current cookie browser."""
        return self.cookie_browser

    def _apply_cookies(self, ydl: "yt_dlp.YoutubeDL") -> None:
        """Load cookie file into the YoutubeDL cookie jar.

        yt-dlp 2026.6.9 has a regression where passing ``cookies`` in the opts
        dict does not populate the cookie jar, so cookie-based authentication
        silently fails. Manually loading the file restores the expected
        behaviour. Browser-cookie extraction is unaffected.
        """
        if self.cookie_file:
            try:
                ydl.cookiejar.load(self.cookie_file)
                logger.info(f"[Facebook] Loaded cookie file: {self.cookie_file}")
            except Exception as exc:
                logger.error(f"[Facebook] Failed to load cookie file {self.cookie_file}: {exc}")

    # --------------------------- Public API ---------------------------

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract Facebook video information without downloading."""
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
            }
            if self.cookie_file:
                ydl_opts["cookies"] = self.cookie_file
            elif self.cookie_browser:
                ydl_opts["cookies_from_browser"] = self.cookie_browser
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self._apply_cookies(ydl)
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", "Unknown"),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", "Unknown"),
                    "view_count": info.get("view_count", 0),
                }
        except Exception as exc:
            logger.error(f"[Facebook] Error extracting video info: {exc}")
            return None

    def download_video(self, url: str) -> Tuple[bool, str]:
        """Download a Facebook video using current settings."""
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

        # Add cookie authentication for private videos
        if self.cookie_file:
            ydl_opts["cookies"] = self.cookie_file
        elif self.cookie_browser:
            ydl_opts["cookies_from_browser"] = self.cookie_browser

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
                self._apply_cookies(ydl)
                logger.info(f"[Facebook] Starting download: {url}")
                logger.info(f"[Facebook] Resolution preset: {self.selected_resolution}")
                logger.info(f"[Facebook] Format string: {format_string}")
                logger.info(f"[Facebook] Destination: {self.download_path}")

                ydl.download([url])

            self.is_downloading = False
            return True, f"Facebook download completed at {self.selected_resolution} quality."
        except Exception as exc:
            self.is_downloading = False
            error_msg = f"Facebook download failed: {exc}"
            logger.error(error_msg)
            return False, error_msg