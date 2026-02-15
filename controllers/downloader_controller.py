"""
Downloader Controller - Orchestrates YouTube video downloads (v6.3)

Mediates between:
- DownloaderTab view (UI)
- YouTubeDownloader model (download logic)
- SettingsManager (persistent preferences)

Handles:
- User actions (button clicks, input validation)
- Progress updates to UI
- Error handling and user feedback
- Threading for non-blocking downloads
- Settings persistence (path, quality)

Created: 2026-02-15
Version: 6.3
"""

import threading
from pathlib import Path
from typing import Optional

from models.youtube_downloader import YouTubeDownloader
from utils.logger import logger


class DownloaderController:
    """
    Controller for YouTube downloader operations.
    
    Coordinates between view and model, handling downloads
    in background threads to keep UI responsive.
    
    New in v6.3:
    - Settings persistence (remembers download path and quality)
    """
    
    def __init__(self, view):
        """
        Initialize controller.
        
        Args:
            view: DownloaderTab view instance
        """
        self.view = view
        self.model = YouTubeDownloader()
        self.download_thread: Optional[threading.Thread] = None
        self.settings = None  # Will be set by main.py after initialization
        
        # Set up model callbacks
        self.model.set_progress_callback(self._on_progress)
        
        logger.info("DownloaderController initialized")
    
    def set_settings_manager(self, settings_manager):
        """
        Inject settings manager for persistent preferences.
        
        This is called by main.py after controller is created.
        Restores saved download path and quality if available.
        
        Args:
            settings_manager: SettingsManager instance
        """
        self.settings = settings_manager
        
        # Restore saved download path
        saved_path = self.settings.get_downloader_save_path()
        if saved_path and Path(saved_path).exists():
            self.view.download_path_var.set(saved_path)
            self.model.set_download_path(saved_path)
            logger.info(f"Restored download path: {saved_path}")
        
        # Restore saved quality
        saved_quality = self.settings.get_downloader_quality()
        if saved_quality:
            self.view.resolution_var.set(saved_quality)
            self.model.set_resolution(saved_quality)
            logger.info(f"Restored quality: {saved_quality}")
        
        logger.info("SettingsManager configured")
        
    def validate_url(self, url: str) -> tuple[bool, str]:
        """Validate YouTube URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Tuple of (is_valid, message)
        """
        return self.model.validate_url(url)
        
    def set_download_path(self, path: str) -> None:
        """Set download destination folder and save to settings.
        
        Args:
            path: Path to download directory
        """
        self.model.set_download_path(path)
        
        # Save to settings if available
        if self.settings:
            self.settings.set_downloader_save_path(path)
            logger.info(f"Download path saved: {path}")
        else:
            logger.info(f"Download path set: {path}")
        
    def set_resolution(self, resolution: str) -> None:
        """Set preferred video resolution and save to settings.
        
        Args:
            resolution: Resolution preset name
        """
        self.model.set_resolution(resolution)
        
        # Save to settings if available
        if self.settings:
            self.settings.set_downloader_quality(resolution)
            logger.info(f"Resolution saved: {resolution}")
        else:
            logger.info(f"Resolution set: {resolution}")
        
    def get_available_resolutions(self) -> list[str]:
        """Get list of available resolution presets.
        
        Returns:
            List of resolution options
        """
        return YouTubeDownloader.get_available_resolutions()
        
    def fetch_video_info(self, url: str) -> None:
        """Fetch video information in background.
        
        Args:
            url: YouTube video URL
        """
        def fetch():
            self.view.update_status("Fetching video information...")
            info = self.model.get_video_info(url)
            
            if info:
                # Format duration
                duration = info['duration']
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
                
                # Format view count
                views = info.get('view_count', 0)
                if views >= 1_000_000:
                    views_str = f"{views/1_000_000:.1f}M views"
                elif views >= 1_000:
                    views_str = f"{views/1_000:.1f}K views"
                else:
                    views_str = f"{views} views"
                
                info_text = f"""
Title: {info['title']}
Uploader: {info['uploader']}
Duration: {duration_str}
Views: {views_str}
"""
                self.view.display_video_info(info_text)
                self.view.update_status("Video information loaded")
            else:
                self.view.display_video_info("Failed to fetch video information")
                self.view.update_status("Error fetching video info")
                
        thread = threading.Thread(target=fetch, daemon=True)
        thread.start()
        
    def start_download(self) -> None:
        """Start video download in background thread."""
        # Get URL from view
        url = self.view.get_url()
        
        # Validate URL
        is_valid, msg = self.validate_url(url)
        if not is_valid:
            self.view.show_error(msg)
            self.view.update_status(f"Error: {msg}")
            return
            
        # Check if download path is set
        download_path = self.view.get_download_path()
        if not download_path or download_path == "[No folder selected]":
            self.view.show_error("Please select a download folder")
            self.view.update_status("Error: No download folder selected")
            return
            
        # Check if already downloading
        if self.download_thread and self.download_thread.is_alive():
            self.view.show_error("Download already in progress")
            return
            
        # Update UI state
        self.view.set_download_button_state(False)  # Disable download button
        self.view.clear_log()
        self.view.log_message(f"Starting download: {url}")
        self.view.log_message(f"Resolution: {self.model.selected_resolution}")
        self.view.log_message(f"Destination: {download_path}")
        self.view.update_status("Download in progress...")
        
        # Start download in background
        def download():
            success, message = self.model.download_video(url)
            
            # Update UI on completion (schedule in main thread)
            self.view.after_download(success, message)
            
        self.download_thread = threading.Thread(target=download, daemon=True)
        self.download_thread.start()
        logger.info(f"Download started: {url}")
        
    def _on_progress(self, progress_info: dict) -> None:
        """Handle progress updates from model.
        
        Args:
            progress_info: Progress information dict from yt-dlp
        """
        status = progress_info.get('status')
        
        if status == 'downloading':
            # Extract progress data
            downloaded = progress_info.get('downloaded_bytes', 0)
            total = progress_info.get('total_bytes') or progress_info.get('total_bytes_estimate', 0)
            speed = progress_info.get('speed', 0)
            eta = progress_info.get('eta', 0)
            
            # Format for display
            if total > 0:
                percent = (downloaded / total) * 100
                downloaded_mb = downloaded / (1024 * 1024)
                total_mb = total / (1024 * 1024)
                speed_mb = speed / (1024 * 1024) if speed else 0
                
                progress_text = f"Downloading: {percent:.1f}% ({downloaded_mb:.1f}/{total_mb:.1f} MB) - {speed_mb:.2f} MB/s"
                
                if eta:
                    progress_text += f" - ETA: {eta}s"
                    
                self.view.update_progress(progress_text)
                
        elif status == 'finished':
            self.view.update_progress("Download finished, processing...")
            self.view.log_message("Download completed, merging formats...")
            
        elif status == 'error':
            error_msg = progress_info.get('error', 'Unknown error')
            self.view.log_message(f"Error: {error_msg}")
            
    def on_download_complete(self, success: bool, message: str) -> None:
        """Handle download completion.
        
        Args:
            success: Whether download was successful
            message: Result message
        """
        # Re-enable download button
        self.view.set_download_button_state(True)
        
        if success:
            self.view.log_message("✓ " + message)
            self.view.update_status("Download completed successfully")
            self.view.show_success(message)
        else:
            self.view.log_message("✗ " + message)
            self.view.update_status(f"Download failed")
            self.view.show_error(message)
            
        logger.info(f"Download complete: success={success}, message={message}")
