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

logger = logging.getLogger(__name__)


class InstagramDownloader:
    """Download videos from Instagram using yt-dlp."""

    def __init__(self) -> None:
        self.download_path: Optional[Path] = None
        self.selected_resolution: str = "Best Available"
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.is_downloading: bool = False
        
        # Story-specific configuration
        self.cookie_file: str = ""
        self.cookie_browser: str = ""

    # --------------------------- Configuration ---------------------------

    def set_download_path(self, path: str) -> None:
        self.download_path = Path(path)
        logger.info(f"[Instagram] Download path set to: {self.download_path}")

    def set_resolution(self, resolution: str) -> None:
        if resolution in YouTubeDownloader.RESOLUTION_FORMATS:
            self.selected_resolution = resolution
        else:
            logger.warning(f"[Instagram] Unknown resolution '{resolution}', using Best Available")
            self.selected_resolution = "Best Available"

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

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.progress_callback = callback

    # --------------------------- Helpers ---------------------------

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        if self.progress_callback:
            self.progress_callback(d)

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

        if not self.download_path:
            return False, "No download path set"

        try:
            self.download_path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return False, f"Failed to create download directory: {exc}"

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

        if not self.download_path:
            return False, "No download path set"

        try:
            self.download_path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return False, f"Failed to create download directory: {exc}"

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

    def cancel_download(self) -> None:
        self.is_downloading = False
        logger.info("[Instagram] Download cancellation requested")
