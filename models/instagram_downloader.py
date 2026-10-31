"""
Instagram Downloader Model - yt-dlp wrapper for Instagram videos (v6.8)

Handles: reels and posts (public / directly accessible URLs) with
unified resolution presets.
Handles: stories and highlights (requires cookie-based authentication)
Uses the same format mapping as YouTubeDownloader for consistency.
"""

import yt_dlp
from typing import Optional, Dict, Any, Tuple
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
        """Download an Instagram story or highlight (cookie authentication required).

        A story tray contains multiple items that may be images and/or videos,
        so it's routed through the same mixed-media engine as carousels:
        videos via yt-dlp, images via direct fetch. Cookies are applied there.
        """
        logger.info(f"[Instagram] Story/highlight download: {url}")
        logger.info(f"[Instagram] Cookie source: {self.get_cookie_source()}")
        if not (self.cookie_file or self.cookie_browser):
            logger.warning("[Instagram] No cookies configured — story download will likely fail")
        return self.download_items(url, indices=None)

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

    _IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "heic", "gif"}
    _VIDEO_EXTENSIONS = {"mp4", "webm", "mkv", "mov", "avi"}

    @classmethod
    def _classify_entry(cls, entry: Dict[str, Any]) -> str:
        """Classify carousel media using entry fields *and* yt-dlp formats."""
        if not entry:
            return "unknown"
        declared_type = str(entry.get("media_type") or entry.get("type") or "").lower()
        if declared_type in {"image", "photo"}:
            return "image"
        if declared_type in {"video", "reel"}:
            return "video"

        vcodec = entry.get("vcodec")
        ext = (entry.get("ext") or "").lower()
        if entry.get("duration") or (vcodec and vcodec != "none") or ext in cls._VIDEO_EXTENSIONS:
            return "video"
        if ext in cls._IMAGE_EXTENSIONS:
            return "image"

        formats = entry.get("formats") or []
        if any(
            (f.get("vcodec") and f.get("vcodec") != "none")
            or (f.get("ext") or "").lower() in cls._VIDEO_EXTENSIONS
            for f in formats
        ):
            return "video"
        if any(
            (f.get("ext") or "").lower() in cls._IMAGE_EXTENSIONS
            for f in formats
        ):
            return "image"
        return "unknown"

    @classmethod
    def _best_media_format(cls, entry: Dict[str, Any], kind: str) -> Dict[str, Any]:
        """Return the largest matching yt-dlp format for display metadata."""
        candidates = []
        for media_format in entry.get("formats") or []:
            ext = (media_format.get("ext") or "").lower()
            if kind == "image" and ext in cls._IMAGE_EXTENSIONS:
                candidates.append(media_format)
            elif kind == "video" and (
                (media_format.get("vcodec") and media_format.get("vcodec") != "none")
                or ext in cls._VIDEO_EXTENSIONS
            ):
                candidates.append(media_format)
        return max(
            candidates,
            key=lambda f: (f.get("width") or 0) * (f.get("height") or 0),
            default={},
        )

    @staticmethod
    def _thumbnail_url(entry: Dict[str, Any], kind: str) -> Optional[str]:
        """Return yt-dlp's preview URL, falling back to confirmed image media."""
        thumbnail = entry.get("thumbnail")
        if thumbnail:
            return thumbnail
        thumbnails = entry.get("thumbnails") or []
        for candidate in reversed(thumbnails):
            if candidate.get("url"):
                return candidate["url"]
        if kind == "image":
            return InstagramDownloader._best_image_url(entry)
        return None

    def _extract_entries_info(self, url: str):
        """Run a single extract_info and return the list of raw entry dicts.

        For a carousel this is ``info['entries']``; for a single post it's
        ``[info]``. Returns None if nothing could be extracted.
        """
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "ignoreerrors": True,
        }
        opts.update(self._cookie_opts())
        with yt_dlp.YoutubeDL(opts) as ydl:
            self._apply_cookies(ydl)
            info = ydl.extract_info(url, download=False)
        if not info:
            return None
        entries = info.get("entries")
        if entries is None:
            entries = [info]
        return entries

    @staticmethod
    def _best_image_url(entry: Dict[str, Any]) -> Optional[str]:
        """Pick the highest-resolution still-image URL from an entry."""
        best_url = None
        best_area = -1
        for f in (entry.get("formats") or []):
            ext = (f.get("ext") or "").lower()
            u = f.get("url")
            if not u or ext not in InstagramDownloader._IMAGE_EXTENSIONS:
                continue
            area = (f.get("width") or 0) * (f.get("height") or 0)
            if area >= best_area:
                best_area = area
                best_url = u
        return best_url or entry.get("url") or entry.get("thumbnail")

    def _download_image(self, img_url: str, entry: Dict[str, Any], index: int) -> None:
        """Download a still image directly (bypasses yt-dlp format selection).

        Instagram images have no audio/video stream, so yt-dlp's best/b
        selectors skip them; fetching the media URL directly is reliable.
        """
        import urllib.request

        raw_title = str(entry.get("title") or entry.get("id") or f"image_{index}")
        safe = "".join(c for c in raw_title if c.isalnum() or c in " ._-").strip()
        safe = (safe[:70] or f"image_{index}")
        ext = (entry.get("ext") or "jpg").lower()
        if ext not in ("jpg", "jpeg", "png", "webp"):
            ext = "jpg"
        item_id = entry.get("id") or ""
        dest = self.download_path / f"{safe} [{item_id}_{index}].{ext}"

        req = urllib.request.Request(img_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        with open(dest, "wb") as fh:
            fh.write(data)
        logger.info(f"[Instagram] Saved image: {dest}")
        # Nudge the UI so it registers activity for instant image saves
        if self.progress_callback:
            try:
                self.progress_callback({"status": "finished", "filename": str(dest)})
            except Exception:
                pass

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
            raw_entries = self._extract_entries_info(url)
            if raw_entries is None:
                return False, "No information could be extracted from this URL."

            entries = []
            for i, e in enumerate(raw_entries, start=1):
                if not e:
                    entries.append({
                        "index": i, "title": f"Item {i} (unavailable)", "ext": "",
                        "kind": "unknown", "width": 0, "height": 0,
                        "duration": 0, "id": "",
                    })
                    continue
                kind = self._classify_entry(e)
                best_format = self._best_media_format(e, kind)
                entries.append({
                    "index": i,
                    "title": e.get("title") or e.get("description") or e.get("id") or f"Item {i}",
                    "ext": (e.get("ext") or best_format.get("ext") or "").lower(),
                    "kind": kind,
                    "width": e.get("width") or best_format.get("width") or 0,
                    "height": e.get("height") or best_format.get("height") or 0,
                    "duration": e.get("duration") or best_format.get("duration") or 0,
                    "id": e.get("id") or "",
                    "thumbnail_url": self._thumbnail_url(e, kind),
                })
            return True, entries
        except Exception as exc:
            logger.error(f"[Instagram] Failed to list entries for {url}: {exc}")
            return False, str(exc)

    def download_items(self, url: str, indices=None) -> Tuple[bool, str]:
        """Download all items (indices=None) or specific 1-based item indices.

        Carousel-aware and mixed-media aware:
        - Video items are downloaded with yt-dlp using the selected resolution.
        - Image items are downloaded directly by URL (yt-dlp's best/b selectors
          skip audio/video-less formats, so images need a direct fetch).
        """
        if self.is_downloading:
            return False, "Download already in progress"

        path_ok, path_error = self._ensure_download_path_exists()
        if not path_ok:
            return False, path_error

        is_audio_only = self.selected_resolution.startswith("Audio Only")

        self.is_downloading = True
        try:
            entries = self._extract_entries_info(url)
            if not entries:
                self.is_downloading = False
                return False, "Could not extract any items from this URL."

            # Re-extraction can reorder or omit carousel items. Prefer the
            # stable extractor ID sent by the selection dialog; retain integer
            # positions only for callers using the old API.
            indexed = {i: entry for i, entry in enumerate(entries, start=1) if entry}
            selected_ids = {
                str(selection.get("id"))
                for selection in (indices or [])
                if isinstance(selection, dict) and selection.get("id")
            }
            selected_positions = {
                int(selection.get("index", 0))
                for selection in (indices or [])
                if isinstance(selection, dict) and not selection.get("id")
            }
            selected_positions.update(
                int(selection) for selection in (indices or [])
                if isinstance(selection, int)
            )

            selected = []
            for index, entry in indexed.items():
                entry_id = str(entry.get("id") or "")
                if selected_ids or selected_positions:
                    if entry_id and entry_id in selected_ids:
                        selected.append((index, entry))
                    elif not entry_id and index in selected_positions:
                        selected.append((index, entry))
                else:
                    selected.append((index, entry))

            video_indices = []
            image_targets = []  # (index, entry)
            unknown_indices = []
            for index, entry in selected:
                kind = self._classify_entry(entry)
                if kind == "image":
                    image_targets.append((index, entry))
                elif kind == "video":
                    video_indices.append(index)
                else:
                    unknown_indices.append(index)

            successes = 0
            failures = len(unknown_indices)
            if unknown_indices:
                logger.warning(
                    "[Instagram] Skipping unclassified selected item(s): %s",
                    ", ".join(str(index) for index in unknown_indices),
                )
            if indices and not selected:
                return False, "The selected Instagram items are no longer available. Please list them again."

            logger.info(
                f"[Instagram] Download plan for {url}: "
                f"{len(video_indices)} video(s), {len(image_targets)} image(s), "
                f"resolution={self.selected_resolution}"
            )

            # --- 1) Videos (and audio-only) via yt-dlp ---
            if video_indices:
                fmt = YouTubeDownloader.RESOLUTION_FORMATS[self.selected_resolution]
                if not is_audio_only:
                    fmt = f"{fmt}/b"  # permissive fallback
                vopts: Dict[str, Any] = {
                    "format": fmt,
                    "outtmpl": str(self.download_path / "%(title).70s [%(id)s].%(ext)s"),
                    "progress_hooks": [self._progress_hook],
                    "quiet": False,
                    "no_warnings": False,
                    "ignoreerrors": True,
                    "noplaylist": False,
                    "playlist_items": ",".join(str(i) for i in video_indices),
                }
                vopts.update(self._cookie_opts())
                if is_audio_only:
                    vopts["postprocessors"] = [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ]
                try:
                    with yt_dlp.YoutubeDL(vopts) as ydl:
                        self._apply_cookies(ydl)
                        result = ydl.download([url])
                    if result in (None, 0):
                        successes += len(video_indices)
                    else:
                        logger.error("[Instagram] yt-dlp returned status %s", result)
                        failures += len(video_indices)
                except Exception as exc:
                    logger.error(f"[Instagram] Video download failed: {exc}")
                    failures += len(video_indices)

            # --- 2) Images via direct download (not in audio-only mode) ---
            if image_targets:
                if is_audio_only:
                    logger.info(
                        "[Instagram] Skipping %d image(s) in Audio Only mode",
                        len(image_targets),
                    )
                else:
                    for i, e in image_targets:
                        img_url = self._best_image_url(e)
                        if not img_url:
                            logger.warning(f"[Instagram] No image URL for item {i}")
                            failures += 1
                            continue
                        try:
                            self._download_image(img_url, e, i)
                            successes += 1
                        except Exception as exc:
                            logger.error(f"[Instagram] Image item {i} failed: {exc}")
                            failures += 1

            self.is_downloading = False

            if successes and not failures:
                return True, f"Downloaded {successes} item(s) from Instagram."
            if successes and failures:
                return True, f"Downloaded {successes} item(s); {failures} failed or skipped."
            return False, "No items could be downloaded from this URL."
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
