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
                logger.info(f"[Instagram] Loaded cookie file: {self.cookie_file}")
            except Exception as exc:
                logger.error(f"[Instagram] Failed to load cookie file {self.cookie_file}: {exc}")
    
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
            "outtmpl": str(self.download_path / "%(title)s [%(id)s].%(ext)s"),
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
                self._apply_cookies(ydl)
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
            logger.error(f"[Instagram] Error extracting video info: {exc}")
            return None

    def _cookie_opts(self) -> Dict[str, Any]:
        """Return yt-dlp options carrying the configured cookie source."""
        opts: Dict[str, Any] = {}
        if self.cookie_file:
            opts["cookies"] = self.cookie_file
        elif self.cookie_browser:
            opts["cookies_from_browser"] = self.cookie_browser
        return opts

    @staticmethod
    def _classify_entry(entry: Dict[str, Any]) -> str:
        """Best-effort classification of a carousel entry as video/image/unknown."""
        if not entry:
            return "unknown"
        vcodec = entry.get("vcodec")
        ext = (entry.get("ext") or "").lower()
        if entry.get("duration") or (vcodec and vcodec != "none") or ext in (
            "mp4", "webm", "mkv", "mov", "avi"
        ):
            return "video"
        if ext in ("jpg", "jpeg", "png", "webp", "heic", "gif"):
            return "image"
        return "unknown"

    def list_entries(self, url: str) -> Tuple[bool, Any]:
        """Enumerate the downloadable items behind an Instagram URL.

        A carousel ('/p/…') can hold multiple images and/or videos. This returns
        the list yt-dlp sees so the UI can let the user pick which to download.

        Returns:
            (True, [entry_dict, ...]) on success, or (False, error_message).
            Each entry dict: index (1-based), title, ext, kind, width, height,
            duration, id.
        """
        try:
            opts: Dict[str, Any] = {
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "ignoreerrors": True,  # keep going even if one item can't be read
            }
            opts.update(self._cookie_opts())
            with yt_dlp.YoutubeDL(opts) as ydl:
                self._apply_cookies(ydl)
                info = ydl.extract_info(url, download=False)

            if not info:
                return False, "No information could be extracted from this URL."

            raw_entries = info.get("entries")
            if raw_entries is None:
                raw_entries = [info]  # single (non-carousel) item

            entries = []
            for i, e in enumerate(raw_entries, start=1):
                if not e:
                    entries.append({
                        "index": i, "title": f"Item {i} (unavailable)", "ext": "",
                        "kind": "unknown", "width": 0, "height": 0,
                        "duration": 0, "id": "",
                    })
                    continue
                entries.append({
                    "index": i,
                    "title": e.get("title") or e.get("description") or e.get("id") or f"Item {i}",
                    "ext": (e.get("ext") or "").lower(),
                    "kind": self._classify_entry(e),
                    "width": e.get("width") or 0,
                    "height": e.get("height") or 0,
                    "duration": e.get("duration") or 0,
                    "id": e.get("id") or "",
                })
            return True, entries
        except Exception as exc:
            logger.error(f"[Instagram] Failed to list entries for {url}: {exc}")
            return False, str(exc)

    def download_items(self, url: str, indices=None) -> Tuple[bool, str]:
        """Download all items (indices=None) or specific 1-based item indices.

        Carousel-aware: uses ``ignoreerrors`` so an item with no downloadable
        media (e.g. a still image on an older yt-dlp) is skipped instead of
        aborting the whole post, and appends a permissive format fallback so
        image items can be fetched too.
        """
        if self.is_downloading:
            return False, "Download already in progress"

        path_ok, path_error = self._ensure_download_path_exists()
        if not path_ok:
            return False, path_error

        format_string = YouTubeDownloader.RESOLUTION_FORMATS[self.selected_resolution]
        is_audio_only = self.selected_resolution.startswith("Audio Only")
        # Append a bare "best" fallback so single-format image items can be
        # selected too (does not affect video/audio selection above it).
        if not is_audio_only:
            format_string = f"{format_string}/b"

        ydl_opts: Dict[str, Any] = {
            "format": format_string,
            # playlist_index keeps carousel items from overwriting each other
            "outtmpl": str(self.download_path / "%(title).70s [%(id)s].%(ext)s"),
            "progress_hooks": [self._progress_hook],
            "quiet": False,
            "no_warnings": False,
            "ignoreerrors": True,
            "noplaylist": False,  # a carousel is a playlist to yt-dlp
        }
        ydl_opts.update(self._cookie_opts())

        if indices:
            ydl_opts["playlist_items"] = ",".join(str(int(i)) for i in indices)

        if is_audio_only:
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
                logger.info(f"[Instagram] Starting download: {url}")
                logger.info(f"[Instagram] Resolution preset: {self.selected_resolution}")
                logger.info(f"[Instagram] Format string: {format_string}")
                logger.info(f"[Instagram] Items: {ydl_opts.get('playlist_items', 'all')}")
                logger.info(f"[Instagram] Destination: {self.download_path}")
                logger.info(f"[Instagram] Cookie source: {self.get_cookie_source()}")

                ydl.download([url])

            self.is_downloading = False
            scope = f"{len(indices)} selected item(s)" if indices else "all items"
            return True, f"Instagram download completed ({scope}) at {self.selected_resolution} quality."
        except Exception as exc:
            self.is_downloading = False
            error_msg = f"Instagram download failed: {exc}"
            logger.error(error_msg)
            return False, error_msg

    def download_video(self, url: str) -> Tuple[bool, str]:
        """Download an Instagram post/reel using current settings.

        Stories use the dedicated cookie-based path. Everything else is routed
        through the carousel-aware downloader so multi-image/video posts work.
        """
        if self.is_instagram_story(url):
            logger.info("[Instagram] Story URL detected — using story-specific download")
            return self.download_story(url)

        # Posts and reels may be carousels (multiple images/videos). Download
        # every item; items with no downloadable media are skipped rather than
        # failing the whole post.
        return self.download_items(url, indices=None)

    # cancel_download() is inherited from BaseDownloader
