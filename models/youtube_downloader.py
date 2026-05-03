""" 
YouTube Downloader Model - yt-dlp wrapper for video downloads (v6.7)

Provides core functionality for downloading YouTube videos with:
- Quality/resolution selection
- Playlist (bulk) downloads when a playlist URL is provided
- Resume-from-item support using playlist index in URL
- Audio-only modes (best/worst) via format presets
- Progress tracking
- Error handling
- Destination folder management

Uses yt-dlp library for robust video downloading.

Created: 2026-02-15
Version: 6.7.0 - Resume playlist downloads from current item when index is present

NOTE: Uses simplified format strings that work reliably without
custom clients or PO tokens.
"""

import yt_dlp
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
import logging
from urllib.parse import urlparse, parse_qs

from models.base_downloader import BaseDownloader

logger = logging.getLogger(__name__)


class YouTubeDownloader(BaseDownloader):
    """Model for downloading YouTube videos using yt-dlp.
    
    Extends BaseDownloader with YouTube-specific functionality including:
    - Quality/resolution selection with format presets
    - Playlist (bulk) downloads with resume-from-item support
    - Audio-only modes via format presets
    - PO token management (stored for future use)
    - YouTube-specific URL validation and video info extraction
    
    Uses simplified format strings for reliable downloads.
    """
    
    # Resolution presets mapping to yt-dlp format strings
    # Pattern for video: bv*[height<=N]+ba/b[height<=N]
    # bv* = best video, ba = best audio, b = best (fallback)
    RESOLUTION_FORMATS = {
        "Best Available": "bv*+ba/b",
        "2160p (4K)": "bv*[height<=2160]+ba/b[height<=2160]",
        "1440p (2K)": "bv*[height<=1440]+ba/b[height<=1440]",
        "1080p (Full HD)": "bv*[height<=1080]+ba/b[height<=1080]",
        "720p (HD)": "bv*[height<=720]+ba/b[height<=720]",
        "480p": "bv*[height<=480]+ba/b[height<=480]",
        "360p": "bv*[height<=360]+ba/b[height<=360]",
        # Audio-only presets
        "Audio Only (Best)": "bestaudio/best",
        "Audio Only (Worst)": "worstaudio/worst",
    }
    
    def __init__(self):
        """Initialize YouTube downloader."""
        super().__init__()
        self._po_token: Optional[str] = None  # Stored for future use (not applied)
        
    # --------------------------- YouTube-Specific Configuration ---------------------------
    def set_po_token(self, token: Optional[str]) -> None:
        """Store PO Token for future use (not currently used in downloads).
        
        Args:
            token: YouTube PO token
                  Can be None or empty string to clear token
        """
        if token:
            token = token.strip()
            self._po_token = token if len(token) >= 10 else None
            if self._po_token:
                logger.info(f"PO Token stored ({len(token)} chars) - saved for future use")
            else:
                logger.warning("PO Token too short, not stored")
        else:
            self._po_token = None
            logger.info("PO Token cleared")
        
    def get_po_token(self) -> Optional[str]:
        """Get current PO Token.
        
        Returns:
            Current PO token or None if not set
        """
        return self._po_token
        
    def has_po_token(self) -> bool:
        """Check if PO Token is configured.
        
        Returns:
            True if PO token is set and appears valid
        """
        return self._po_token is not None and len(self._po_token) >= 10
    
    # Note: set_download_path(), set_resolution(), set_progress_callback(), and _progress_hook()
    # are inherited from BaseDownloader and should not be overridden unless platform-specific
    # behavior is required.
            
    @staticmethod
    def _is_playlist_url(url: str) -> bool:
        """Heuristic check whether a YouTube URL is a playlist.
        
        Looks for `list` parameter commonly used in playlist URLs.
        """
        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            if "list" in query:
                return True
            # Also treat /playlist URLs as playlists
            if "playlist" in parsed.path:
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _get_playlist_start_index(url: str) -> Optional[int]:
        """Extract playlist start index from a watch URL if present.

        Typical playlist watch URLs look like:
        https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID&index=12

        In that case this returns 12, so downloads can resume from item 12
        onward using yt-dlp's `playliststart` option.
        """
        try:
            parsed = urlparse(url)
            query = parse_qs(parsed.query)
            # YouTube commonly uses `index` as 1-based position in playlist
            if "index" in query and query["index"]:
                raw = query["index"][0]
                idx = int(raw)
                if idx >= 1:
                    return idx
        except Exception:
            pass
        return None
            
    # --------------------------- Public API ---------------------------
    def validate_url(self, url: str) -> tuple[bool, str]:
        """Validate if URL is a valid YouTube URL.
        
        Args:
            url: YouTube video or playlist URL
            
        Returns:
            Tuple of (is_valid, message)
        """
        if not url or not url.strip():
            return False, "URL cannot be empty"
            
        url = url.strip()
        
        # Basic YouTube URL validation
        valid_patterns = [
            "youtube.com/watch",
            "youtu.be/",
            "youtube.com/shorts/",
            "youtube.com/embed/",
            "youtube.com/playlist",
        ]
        
        if any(pattern in url for pattern in valid_patterns):
            return True, "Valid YouTube URL"
        else:
            return False, "Not a valid YouTube URL"
            
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract video information without downloading.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with video info or None if error
        """
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                }
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            return None
            
    def download_video(self, url: str) -> tuple[bool, str]:
        """Download YouTube video or playlist with configured settings.
        
        Args:
            url: YouTube video or playlist URL
            
        Returns:
            Tuple of (success, message)
        """
        if self.is_downloading:
            return False, "Download already in progress"
            
        # Validate URL
        is_valid, msg = self.validate_url(url)
        if not is_valid:
            return False, msg
            
        # Validate download path using base class utility
        path_ok, path_error = self._ensure_download_path_exists()
        if not path_ok:
            return False, path_error
            
        # Configure yt-dlp options with simplified format string
        format_string = self.RESOLUTION_FORMATS[self.selected_resolution]
        
        # Minimal yt-dlp options - let yt-dlp use its defaults
        ydl_opts: Dict[str, Any] = {
            'format': format_string,
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'quiet': False,
            'no_warnings': False,
        }
        
        # If audio-only preset, add postprocessors for MP3 conversion
        if self.selected_resolution.startswith("Audio Only"):
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                # Use 192 kbps as a balanced default; yt-dlp may upscale/downscale
                'preferredquality': '192',
            }]
        
        is_playlist = self._is_playlist_url(url)

        # If this is a playlist URL that includes a valid index parameter,
        # resume from that item forward using playliststart.
        if is_playlist:
            start_idx = self._get_playlist_start_index(url)
            if start_idx is not None:
                ydl_opts['playliststart'] = start_idx
                logger.info(
                    "Detected playlist URL with index=%s - will download from item %s onward",
                    start_idx,
                    start_idx,
                )
            else:
                logger.info("Detected playlist URL - yt-dlp will download all items in the playlist")
        else:
            logger.info("Detected single video URL")
        
        # Perform download
        self.is_downloading = True
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Starting download: {url}")
                logger.info(f"Resolution preset: {self.selected_resolution}")
                logger.info(f"Format string: {format_string}")
                logger.info(f"Destination: {self.download_path}")
                
                # Passing the playlist or single URL lets yt-dlp handle bulk vs single
                ydl.download([url])
                
                self.is_downloading = False
                
                if is_playlist:
                    # Message depends on whether a start index was used
                    start_idx = self._get_playlist_start_index(url)
                    if start_idx is not None:
                        return True, (
                            f"Playlist download from item {start_idx} onward completed at "
                            f"{self.selected_resolution} quality."
                        )
                    return True, f"Playlist download completed at {self.selected_resolution} quality."
                else:
                    return True, f"Download completed successfully at {self.selected_resolution} quality."
                
        except Exception as e:
            self.is_downloading = False
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    # cancel_download() is inherited from BaseDownloader
        
    @staticmethod
    def get_available_resolutions() -> list[str]:
        """Get list of available resolution presets.
        
        Returns:
            List of resolution preset names
        """
        return list(YouTubeDownloader.RESOLUTION_FORMATS.keys())
