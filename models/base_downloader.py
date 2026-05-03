"""
Base Downloader - Shared abstraction for platform-specific downloaders (Phase 4)

Provides common configuration and state management for all downloaders:
- YouTubeDownloader
- TwitterDownloader  
- InstagramDownloader

Eliminates code duplication while maintaining platform-specific functionality.

Created: 2026-05-03
Version: 1.0.0 - Phase 4 Architectural Improvements
"""

from pathlib import Path
from typing import Optional, Callable, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseDownloader:
    """Base class for all platform-specific video downloaders.
    
    Provides common configuration, state management, and utility methods
    that are shared across all downloader implementations.
    """
    
    def __init__(self):
        """Initialize base downloader with default configuration."""
        # Common configuration properties
        self.download_path: Optional[Path] = None
        self.selected_resolution: str = "Best Available"
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.is_downloading: bool = False
    
    # --------------------------- Configuration ---------------------------
    
    def set_download_path(self, path: str) -> None:
        """Set destination folder for downloads.
        
        Args:
            path: String path to download directory
        """
        self.download_path = Path(path)
        logger.info(f"{self.__class__.__name__} download path set to: {self.download_path}")
    
    def set_resolution(self, resolution: str) -> None:
        """Set preferred video/audio resolution preset.
        
        Args:
            resolution: Resolution preset key (e.g., '1080p (Full HD)', 'Audio Only (Best)')
        """
        self.selected_resolution = resolution
        logger.info(f"{self.__class__.__name__} resolution preset set to: {resolution}")
    
    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback function for download progress updates.
        
        Args:
            callback: Function to call with progress info dict from yt-dlp
        """
        self.progress_callback = callback
    
    # --------------------------- Download Control ---------------------------
    
    def cancel_download(self) -> None:
        """Cancel current download operation.
        
        Note: This sets a flag to prevent new downloads; yt-dlp doesn't support
        direct cancellation of in-progress downloads.
        """
        self.is_downloading = False
        logger.info(f"{self.__class__.__name__} download cancellation requested")
    
    # --------------------------- Progress Handling ---------------------------
    
    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """Internal progress hook called by yt-dlp.
        
        Forwards progress events to the configured callback if set.
        
        Args:
            d: Progress info dictionary from yt-dlp
        """
        if self.progress_callback:
            self.progress_callback(d)
    
    # --------------------------- Utility Methods ---------------------------
    
    def _ensure_download_path_exists(self) -> Tuple[bool, Optional[str]]:
        """Ensure download path exists and is writable.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if not self.download_path:
            return False, "No download path set"
        
        try:
            self.download_path.mkdir(parents=True, exist_ok=True)
            return True, None
        except Exception as e:
            error_msg = f"Failed to create download directory: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _validate_download_not_in_progress(self) -> Tuple[bool, Optional[str]]:
        """Validate that a download is not already in progress.
        
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        if self.is_downloading:
            return False, "Download already in progress"
        return True, None