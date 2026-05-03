"""
Instagram Downloader Model - yt-dlp wrapper for Instagram videos (v6.8)

Handles: reels and posts (public / directly accessible URLs) with
unified resolution presets.
Handles: stories and highlights (requires cookie-based authentication)
Uses the same format mapping as YouTubeDownloader for consistency.
"""

import yt_dlp
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
import logging

from models.youtube_downloader import YouTubeDownloader
from models.base_downloader import BaseDownloader

logger = logging.getLogger(__name__)


class InstagramDownloader(BaseDownloader):
    """Download videos from Instagram using yt-dlp.
    
    Extends BaseDownloader with Instagram-specific functionality:
    - Uses YouTubeDownloader's resolution presets for consistency
    - Implements Instagram URL detection and story handling
    - Provides cookie-based authentication for stories
    - Handles both public posts/reels and private stories
    """
    
    def __init__(self) -> None:
        super().__init__()
        
        # Story-specific configuration
        self.cookie_file: str = ""
        self.cookie_browser: str = ""

    # --------------------------- Instagram-Specific Configuration ---------------------------
    
    def set_po_token(self, token: Optional[str]) -> None:  # Kept for interface compatibility
        # PO tokens are not used for Instagram; ignore.
        return
    
    def get_po_token(self) -> Optional[str]:
        return None
    
    def has_po_token(self) -> bool:
        return False
    
    # --------------------------- Story/Cookie Configuration ---------------------------
    
    def set_cookie_file(self, path: str) -> None:
        """Set cookie file path for Instagram story downloads."""
        self.cookie_file = path
        logger.info(f"[Instagram] Cookie file set: {path}")
    
    def set_cookie_browser(self, browser: str) -> None:
        """Set browser name for cookie extraction."""
        self.cookie_browser = browser
        logger.info(f"[Instagram] Cookie browser set: {browser}")
    
    def get_cookie_source(self) -> str:
        """Return description of configured cookie source."""
        if self.cookie_file:
            return f"Cookie file: {self.cookie_file}"
        elif self.cookie_browser:
            return f"Browser cookies: {self.cookie_browser}"
        else:
            return "No cookie authentication configured"
    
    # Note: set_download_path(), set_resolution(), set_progress_callback(), and _progress_hook()
    # are inherited from BaseDownloader and should not be overridden unless platform-specific
    # behavior is required.

    # --------------------------- URL Detection ---------------------------

    @staticmethod
    def is_instagram_story(url: str) -> bool:
        """Check if URL points to an Instagram story or highlight reel."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            path = (parsed.path or "").lower()
            return ("/stories/highlights/" in path or "/stories/" in path)
        except Exception:
            return False

    # --------------------------- Public API ---------------------------

    def download_story(self, url: str) -> Tuple[bool, str]:
        """Download an Instagram story using cookie authentication."""
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
            # Story-specific options
            "ignoreerrors": True,  # Stories playlist may have expired items
            "extract_flat": False,
            "noplaylist": False,  # Stories are treated as playlists by yt-dlp
        }

        # Add cookie authentication
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
                logger.info(f"[Instagram] Starting story download: {url}")
                logger.info(f"[Instagram] Resolution preset: {self.selected_resolution}")
                logger.info(f"[Instagram] Format string: {format_string}")
                logger.info(f"[Instagram] Destination: {self.download_path}")
                logger.info(f"[Instagram] Cookie source: {self.get_cookie_source()}")
                logger.debug(f"[Instagram] Story download opts: {ydl_opts}")

                ydl.download([url])

            self.is_downloading = False
            return True, f"Instagram story download completed at {self.selected_resolution} quality."
        except Exception as exc:
            self.is_downloading = False
            error_msg = f"Instagram story download failed: {exc}"
            logger.error(error_msg)
            return False, error_msg

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract Instagram video information without downloading."""
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
            logger.error(f"[Instagram] Error extracting video info: {exc}")
            return None

    def download_video(self, url: str) -> Tuple[bool, str]:
        """Download an Instagram video using current settings."""
        # Check if this is a story URL and handle with specialized method
        if self.is_instagram_story(url):
            logger.info("[Instagram] Story URL detected — using story-specific download")
            return self.download_story(url)

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
                logger.info(f"[Instagram] Starting download: {url}")
                logger.info(f"[Instagram] Resolution preset: {self.selected_resolution}")
                logger.info(f"[Instagram] Format string: {format_string}")
                logger.info(f"[Instagram] Destination: {self.download_path}")

                ydl.download([url])

            self.is_downloading = False
            return True, f"Instagram download completed at {self.selected_resolution} quality."
        except Exception as exc:
            self.is_downloading = False
            error_msg = f"Instagram download failed: {exc}"
            logger.error(error_msg)
            return False, error_msg

    # cancel_download() is inherited from BaseDownloader
