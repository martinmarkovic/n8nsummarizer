"""
Video Downloader Router - dispatches to site-specific downloaders (v8.2)

Supports downloading from:
- YouTube (single videos and playlists, with resume support)
- Twitter/X (tweet videos)
- Instagram (reels and posts, where accessible)
- Facebook (public videos, reels, and fb.watch links)

Keeps a unified interface for the DownloaderController and view.

Created: 2026-02-17
Version: 8.2.0 - Multi-source router (YouTube, Twitter, Instagram, Facebook)
"""

from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
from urllib.parse import urlparse

from models.youtube_downloader import YouTubeDownloader
from models.twitter_downloader import TwitterDownloader
from models.instagram_downloader import InstagramDownloader
from models.facebook_downloader import FacebookDownloader
from utils.logger import logger


class VideoDownloader:
    """Router model that delegates to site-specific downloaders.
    
    This keeps the controller/view API identical while supporting
    multiple platforms behind the scenes.
    
    All platform downloaders (YouTubeDownloader, TwitterDownloader, InstagramDownloader)
    extend BaseDownloader for shared configuration and state management.
    """

    def __init__(self) -> None:
        self.youtube = YouTubeDownloader()
        self.twitter = TwitterDownloader()
        self.instagram = InstagramDownloader()
        self.facebook = FacebookDownloader()

        self.download_path: Optional[Path] = None
        self.selected_resolution: str = "Best Available"
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None

        # Ensure all backends use the same callback initially
        self._sync_progress_callback()

    # --------------------------- Internal helpers ---------------------------

    def _detect_source(self, url: str) -> str:
        """Detect source platform from URL.

        Returns one of: 'youtube', 'twitter', 'instagram', 'facebook', 'unknown'.
        """
        try:
            parsed = urlparse(url)
            host = (parsed.netloc or "").lower()
        except Exception:
            return "unknown"

        if any(h in host for h in ["youtube.com", "youtu.be"]):
            return "youtube"

        if "twitter.com" in host or host.endswith(".twitter.com") or "x.com" in host:
            return "twitter"

        if "instagram.com" in host or "instagr.am" in host:
            return "instagram"

        if any(h in host for h in ["facebook.com", "fb.watch", "fb.com"]) or "facebook.com" in url:
            return "facebook"

        # Basic heuristic for embedded/shortened links could be added later
        return "unknown"

    def _active_model_for_url(self, url: str):
        source = self._detect_source(url)
        if source == "youtube":
            return self.youtube, source
        if source == "twitter":
            return self.twitter, source
        if source == "instagram":
            return self.instagram, source
        if source == "facebook":
            return self.facebook, source
        return None, source

    def _sync_progress_callback(self) -> None:
        """Apply current progress callback to all backends."""
        if self.progress_callback is None:
            return
        self.youtube.set_progress_callback(self.progress_callback)
        self.twitter.set_progress_callback(self.progress_callback)
        self.instagram.set_progress_callback(self.progress_callback)
        self.facebook.set_progress_callback(self.progress_callback)

    # --------------------------- Public API ---------------------------

    def set_download_path(self, path: str) -> None:
        self.download_path = Path(path)
        self.youtube.set_download_path(path)
        self.twitter.set_download_path(path)
        self.instagram.set_download_path(path)
        self.facebook.set_download_path(path)
        logger.info(f"Download path set for all sources: {self.download_path}")

    def set_resolution(self, resolution: str) -> None:
        self.selected_resolution = resolution
        self.youtube.set_resolution(resolution)
        self.twitter.set_resolution(resolution)
        self.instagram.set_resolution(resolution)
        self.facebook.set_resolution(resolution)
        logger.info(f"Resolution preset set for all sources: {resolution}")

    def set_po_token(self, token: Optional[str]) -> None:
        """PO Token is only meaningful for YouTube.

        Stored on the YouTube backend; ignored for others.
        """
        self.youtube.set_po_token(token)

    def get_po_token(self) -> Optional[str]:
        return self.youtube.get_po_token()

    def has_po_token(self) -> bool:
        return self.youtube.has_po_token()

    # Instagram cookie authentication methods
    def set_instagram_cookie_file(self, path: str) -> None:
        """Set cookie file path for Instagram story downloads."""
        self.instagram.set_cookie_file(path)
        logger.info(f"Instagram cookie file configured: {path}")

    def set_instagram_cookie_browser(self, browser: str) -> None:
        """Set browser name for Instagram cookie extraction."""
        self.instagram.set_cookie_browser(browser)
        logger.info(f"Instagram cookie browser configured: {browser}")

    # Facebook cookie authentication methods
    def set_facebook_cookie_file(self, path: str) -> None:
        """Set cookie file path for Facebook private video downloads."""
        self.facebook.set_cookie_file(path)
        logger.info(f"Facebook cookie file configured: {path}")

    def set_facebook_cookie_browser(self, browser: str) -> None:
        """Set browser name for Facebook cookie extraction."""
        self.facebook.set_cookie_browser(browser)
        logger.info(f"Facebook cookie browser configured: {browser}")

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.progress_callback = callback
        self._sync_progress_callback()

    @staticmethod
    def get_available_resolutions() -> list[str]:
        """Use YouTube's preset list for all sources."""
        return YouTubeDownloader.get_available_resolutions()

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """Validate URL for any supported platform."""
        url = (url or "").strip()
        if not url:
            return False, "URL cannot be empty"

        model, source = self._active_model_for_url(url)
        if model is None:
            return False, "Unsupported URL. Only YouTube, Twitter, Instagram, and Facebook are supported."

        if source == "youtube":
            return self.youtube.validate_url(url)

        # For Twitter/Instagram/Facebook, do light validation here and let yt-dlp
        # raise a more detailed error if something is wrong.
        if source == "twitter":
            return True, "Valid Twitter/X URL"
        if source == "instagram":
            return True, "Valid Instagram URL"
        if source == "facebook":
            return True, "Valid Facebook URL"

        return False, "Unsupported URL. Only YouTube, Twitter, Instagram, and Facebook are supported."

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract video information, if supported.

        Currently this primarily targets YouTube; for other platforms
        a minimal info dict may be returned or None on error.
        """
        model, source = self._active_model_for_url(url)
        if model is None:
            return None
        try:
            return model.get_video_info(url)
        except Exception as exc:  # Defensive: backend may not implement fully
            logger.error(f"Error getting video info for {source}: {exc}")
            return None

    def download_video(self, url: str) -> Tuple[bool, str]:
        """Download the video using the appropriate backend."""
        model, source = self._active_model_for_url(url)
        if model is None:
            return False, "Unsupported URL. Only YouTube, Twitter, Instagram, and Facebook are supported."

        logger.info(f"Source detected for download: {source}")
        return model.download_video(url)

    def list_entries(self, url: str):
        """List the individual downloadable items behind a URL (e.g. an
        Instagram carousel with multiple images/videos).

        Returns (True, [entries]) or (False, error_message). Only backends that
        implement ``list_entries`` are supported (currently Instagram).
        """
        model, source = self._active_model_for_url(url)
        if model is None:
            return False, "Unsupported URL. Only YouTube, Twitter, Instagram, and Facebook are supported."
        if hasattr(model, "list_entries"):
            logger.info(f"Listing items for source: {source}")
            return model.list_entries(url)
        return False, f"Listing individual items isn't supported for {source} yet."

    def download_items(self, url: str, indices=None) -> Tuple[bool, str]:
        """Download all or specific 1-based item indices from a multi-item URL.

        Falls back to a normal single download for backends that don't support
        item selection.
        """
        model, source = self._active_model_for_url(url)
        if model is None:
            return False, "Unsupported URL. Only YouTube, Twitter, Instagram, and Facebook are supported."
        if hasattr(model, "download_items"):
            logger.info(f"Downloading selected items for source: {source} (items={indices or 'all'})")
            return model.download_items(url, indices)
        # Backend without selective support — just download normally
        return model.download_video(url)

    def cancel_download(self) -> None:
        """Cancel download on all backends (best-effort)."""
        self.youtube.cancel_download()
        self.twitter.cancel_download()
        self.instagram.cancel_download()
        self.facebook.cancel_download()
