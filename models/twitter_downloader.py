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

logger = logging.getLogger(__name__)


class TwitterDownloader:
    """Download videos from Twitter/X using yt-dlp."""

    def __init__(self) -> None:
        self.download_path: Optional[Path] = None
        self.selected_resolution: str = "Best Available"
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.is_downloading: bool = False

    # --------------------------- Configuration ---------------------------

    def set_download_path(self, path: str) -> None:
        self.download_path = Path(path)
        logger.info(f"[Twitter] Download path set to: {self.download_path}")

    def set_resolution(self, resolution: str) -> None:
        if resolution in YouTubeDownloader.RESOLUTION_FORMATS:
            self.selected_resolution = resolution
        else:
            logger.warning(f"[Twitter] Unknown resolution '{resolution}', using Best Available")
            self.selected_resolution = "Best Available"

    def set_po_token(self, token: Optional[str]) -> None:  # Kept for interface compatibility
        # PO tokens are not used for Twitter; ignore.
        return

    def get_po_token(self) -> Optional[str]:
        return None

    def has_po_token(self) -> bool:
        return False

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.progress_callback = callback

    # --------------------------- Helpers ---------------------------

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        if self.progress_callback:
            self.progress_callback(d)

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

    def cancel_download(self) -> None:
        self.is_downloading = False
        logger.info("[Twitter] Download cancellation requested")
