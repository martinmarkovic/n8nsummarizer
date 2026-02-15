"""
YouTube Downloader Model - yt-dlp wrapper for video downloads (v6.2)

Provides core functionality for downloading YouTube videos with:
- Quality/resolution selection
- Progress tracking
- Error handling
- Destination folder management

Uses yt-dlp library for robust video downloading.

Created: 2026-02-15
Version: 6.2.5 - Use browser cookies for authentication (bypasses PO Token requirements)
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
    destination folder, and progress tracking.
    
    Uses browser cookies for authentication to bypass PO Token requirements.
    """
    
    # Resolution presets mapping to yt-dlp format strings
    # Using height-based selection with proper fallbacks
    RESOLUTION_FORMATS = {
        "Best Available": "bv*+ba/b",  # Best video + best audio
        "2160p (4K)": "bv*[height<=2160]+ba/b[height<=2160]",
        "1440p (2K)": "bv*[height<=1440]+ba/b[height<=1440]",
        "1080p (Full HD)": "bv*[height<=1080]+ba/b[height<=1080]",
        "720p (HD)": "bv*[height<=720]+ba/b[height<=720]",
        "480p": "bv*[height<=480]+ba/b[height<=480]",
        "360p": "bv*[height<=360]+ba/b[height<=360]",
        "Audio Only (MP3)": "ba/b",
    }
    
    def __init__(self):
        """Initialize YouTube downloader."""
        self.download_path: Optional[Path] = None
        self.selected_resolution: str = "Best Available"
        self.progress_callback: Optional[Callable] = None
        self.is_downloading: bool = False
        
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
        else:
            logger.warning(f"Unknown resolution '{resolution}', using Best Available")
            self.selected_resolution = "Best Available"
            
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
                # Use cookies from browser
                'cookiesfrombrowser': ('chrome',),  # or 'firefox', 'edge', 'safari'
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
            # Use cookies from browser - this bypasses ALL token requirements
            'cookiesfrombrowser': ('chrome',),  # Will try: chrome, firefox, edge, safari, etc.
        }
        
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
                logger.info(f"Resolution: {self.selected_resolution}")
                logger.info(f"Format string: {format_string}")
                logger.info(f"Using browser cookies for authentication")
                logger.info(f"Destination: {self.download_path}")
                
                ydl.download([url])
                
                self.is_downloading = False
                return True, "Download completed successfully"
                
        except Exception as e:
            self.is_downloading = False
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg)
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
