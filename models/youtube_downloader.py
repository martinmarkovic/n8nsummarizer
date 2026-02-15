"""
YouTube Downloader Model - yt-dlp wrapper for video downloads (v6.4)

Provides core functionality for downloading YouTube videos with:
- Quality/resolution selection
- PO Token support for HD downloads
- Progress tracking
- Error handling
- Destination folder management

Uses yt-dlp library for robust video downloading.

Created: 2026-02-15
Version: 6.4.2 - Full PO Token integration

IMPORTANT: As of February 2026, YouTube requires PO Tokens for qualities above 360p.
With PO tokens provided, all qualities up to 4K are supported.
"""

import yt_dlp
from pathlib import Path
from typing import Optional, Callable, Dict, Any
import logging

logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """
    Model for downloading YouTube videos using yt-dlp.
    
    Handles video download operations with configurable quality,
    destination folder, PO token support, and progress tracking.
    
    PO Token enables HD downloads (720p, 1080p, 4K).
    """
    
    # Resolution presets mapping to yt-dlp format strings
    RESOLUTION_FORMATS = {
        "Best Available": "best",
        "2160p (4K)": "best[height<=2160]",
        "1440p (2K)": "best[height<=1440]",
        "1080p (Full HD)": "best[height<=1080]",
        "720p (HD)": "best[height<=720]",
        "480p": "best[height<=480]",
        "360p": "best[height<=360]",
        "Audio Only (MP3)": "bestaudio/best",
    }
    
    def __init__(self):
        """Initialize YouTube downloader."""
        self.download_path: Optional[Path] = None
        self.selected_resolution: str = "Best Available"
        self.progress_callback: Optional[Callable] = None
        self.is_downloading: bool = False
        self._po_token: Optional[str] = None
        self._po_token_warning_shown: bool = False
        
    def set_download_path(self, path: str) -> None:
        """Set destination folder for downloads.
        
        Args:
            path: String path to download directory
        """
        self.download_path = Path(path)
        logger.info(f"Download path set to: {self.download_path}")
        
    def set_resolution(self, resolution: str) -> None:
        """Set preferred video resolution.
        
        Args:
            resolution: Resolution preset key (e.g., '1080p (Full HD)')
        """
        if resolution in self.RESOLUTION_FORMATS:
            self.selected_resolution = resolution
            logger.info(f"Resolution set to: {resolution}")
            
            # Warn user about PO token requirement if not set
            if not self._po_token and not self._po_token_warning_shown and \
               resolution not in ["360p", "480p", "Audio Only (MP3)"]:
                logger.warning("="*60)
                logger.warning("YouTube Limitation: PO Token Required")
                logger.warning("="*60)
                logger.warning(f"You selected: {resolution}")
                logger.warning("Due to YouTube restrictions (Feb 2026), downloads are")
                logger.warning("limited to 360p without PO Tokens.")
                logger.warning("")
                logger.warning("Please provide PO Token in the Downloader tab to enable")
                logger.warning("higher quality downloads (720p, 1080p, 4K).")
                logger.warning("")
                logger.warning("Use the browser extension to extract PO Token easily.")
                logger.warning("="*60)
                self._po_token_warning_shown = True
        else:
            logger.warning(f"Unknown resolution '{resolution}', using Best Available")
            self.selected_resolution = "Best Available"
    
    def set_po_token(self, token: Optional[str]) -> None:
        """Set PO Token for HD downloads.
        
        Args:
            token: YouTube visitor data token (visitor_data or VISITOR_INFO1_LIVE value)
                  Can be None or empty string to clear token
        """
        # Clean and validate token
        if token:
            token = token.strip()
            
            # Remove 'web+' prefix if present (from cookie extraction)
            if token.startswith('web+'):
                token = token[4:]
                
            if len(token) < 10:
                logger.warning(f"PO Token seems too short ({len(token)} chars). May be invalid.")
                self._po_token = None
                return
                
            self._po_token = token
            logger.info(f"✓ PO Token set ({len(token)} chars) - HD downloads enabled")
            logger.info(f"Token preview: {token[:20]}...")
        else:
            self._po_token = None
            logger.info("PO Token cleared - downloads limited to 360p")
    
    def get_po_token(self) -> Optional[str]:
        """Get current PO Token.
        
        Returns:
            Current PO token or None if not set
        """
        return self._po_token
    
    def has_po_token(self) -> bool:
        """Check if PO Token is configured.
        
        Returns:
            True if PO token is set and valid
        """
        return self._po_token is not None and len(self._po_token) >= 10
            
    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback function for download progress updates.
        
        Args:
            callback: Function to call with progress info dict
        """
        self.progress_callback = callback
        
    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """Internal progress hook called by yt-dlp.
        
        Args:
            d: Progress info dictionary from yt-dlp
        """
        if self.progress_callback:
            self.progress_callback(d)
            
    def validate_url(self, url: str) -> tuple[bool, str]:
        """Validate if URL is a valid YouTube URL.
        
        Args:
            url: YouTube video URL
            
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
                # Use android client for info extraction
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android'],
                    }
                },
            }
            
            # Add PO token if available
            if self.has_po_token():
                ydl_opts['extractor_args']['youtube']['po_token'] = [f'web+{self._po_token}']
            
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
        """Download YouTube video with configured settings.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Tuple of (success, message)
        """
        if self.is_downloading:
            return False, "Download already in progress"
            
        # Validate URL
        is_valid, msg = self.validate_url(url)
        if not is_valid:
            return False, msg
            
        # Check download path
        if not self.download_path:
            return False, "No download path set"
            
        # Create download directory if it doesn't exist
        try:
            self.download_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Failed to create download directory: {str(e)}"
            
        # Configure yt-dlp options
        format_string = self.RESOLUTION_FORMATS[self.selected_resolution]
        
        # Build yt-dlp options
        ydl_opts = {
            'format': format_string,
            'outtmpl': str(self.download_path / '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'quiet': False,
            'no_warnings': False,
            # Use android client as base
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                }
            },
        }
        
        # Add PO token if available for HD downloads
        if self.has_po_token():
            # yt-dlp expects format: web+<token>
            po_token_value = f'web+{self._po_token}'
            ydl_opts['extractor_args']['youtube']['po_token'] = [po_token_value]
            logger.info(f"✓ Using PO Token for HD download (token length: {len(self._po_token)})")
        else:
            logger.warning("⚠ No PO Token - download may be limited to 360p")
        
        # Add audio extraction options if Audio Only selected
        if self.selected_resolution == "Audio Only (MP3)":
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        
        # Perform download
        self.is_downloading = True
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Starting download: {url}")
                logger.info(f"Resolution requested: {self.selected_resolution}")
                logger.info(f"Format string: {format_string}")
                logger.info(f"PO Token: {'✓ Enabled' if self.has_po_token() else '✗ Not set'}")
                logger.info(f"Destination: {self.download_path}")
                
                ydl.download([url])
                
                self.is_downloading = False
                
                # Success message based on PO token status
                if self.has_po_token():
                    return True, f"Download completed successfully at {self.selected_resolution} quality."
                elif self.selected_resolution not in ["360p", "480p", "Audio Only (MP3)"]:
                    return True, ("Download completed. NOTE: Without PO Token, actual quality "
                                "may be limited to 360p. Provide PO Token for HD downloads.")
                else:
                    return True, "Download completed successfully."
                
        except Exception as e:
            self.is_downloading = False
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg)
            
            # Provide helpful error message if PO token related
            if "Sign in to confirm you're not a bot" in str(e) or "HTTP Error 403" in str(e):
                error_msg += "\n\nThis may be due to missing or invalid PO Token. "
                error_msg += "Please extract a fresh PO Token using the browser extension."
            
            return False, error_msg
            
    def cancel_download(self) -> None:
        """Cancel current download operation.
        
        Note: yt-dlp doesn't provide direct cancellation,
        this flag prevents new downloads from starting.
        """
        self.is_downloading = False
        logger.info("Download cancellation requested")
        
    @staticmethod
    def get_available_resolutions() -> list[str]:
        """Get list of available resolution presets.
        
        Returns:
            List of resolution preset names
        """
        return list(YouTubeDownloader.RESOLUTION_FORMATS.keys())
