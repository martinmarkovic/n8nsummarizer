"""
Video Utilities - Helper functions for video processing

Provides utility functions for video download progress tracking,
model callbacks, and translation operations.
"""
from pathlib import Path
import yt_dlp
from utils.logger import logger


def download_progress_hook(progress_info, tab_callback=None):
    """
    Progress hook for yt-dlp downloads.
    
    Args:
        progress_info: yt-dlp progress dictionary
        tab_callback: Optional callback function to update UI (percent, message)
        
    Returns:
        None, but calls tab_callback if provided
    """
    status = progress_info.get('status')
    if status == 'downloading':
        downloaded = progress_info.get('downloaded_bytes', 0)
        total = progress_info.get('total_bytes') or progress_info.get('total_bytes_estimate', 0)
        speed = progress_info.get('speed', 0)
        eta = progress_info.get('eta', 0)
        
        if total > 0:
            percent = (downloaded / total) * 100
            speed_mb = (speed or 0) / (1024 * 1024)
            msg = f"Downloading: {percent:.1f}% — {speed_mb:.2f} MB/s — ETA: {eta}s"
            if tab_callback:
                tab_callback(percent, msg)


def model_progress_callback(percent: float, speed: float = 0, eta: int = 0, message: str = None, tab_callback=None):
    """
    Progress callback for VideoSubtitlerModel operations.
    
    Args:
        percent: Progress percentage (0-100)
        speed: Speed in bytes per second
        eta: Estimated time remaining in seconds
        message: Optional custom message
        tab_callback: Optional callback to update UI (percent, message)
        
    Returns:
        None, but calls tab_callback if provided
    """
    if message:
        msg = f"{message}: {percent:.1f}%"
    else:
        speed_mb = speed / (1024 * 1024) if speed else 0
        msg = f"Processing: {percent:.1f}% — {speed_mb:.2f} MB/s — ETA: {eta}s"
    
    if tab_callback:
        tab_callback(percent, msg)


def create_download_progress_wrapper(controller_callback):
    """
    Create a wrapper to adapt yt-dlp progress dict to model callback format.
    
    Args:
        controller_callback: Callback function with signature (percent, speed, eta)
        
    Returns:
        Wrapper function that converts yt-dlp format to controller format
    """
    def wrapper(progress_info):
        """Convert yt-dlp progress dict to (percent, speed, eta) format."""
        if progress_info.get('status') == 'downloading':
            downloaded = progress_info.get('downloaded_bytes', 0)
            total = progress_info.get('total_bytes') or progress_info.get('total_bytes_estimate', 1)
            speed = progress_info.get('speed', 0) or 0
            eta = progress_info.get('eta', 0) or 0
            pct = (downloaded / total * 100) if total else 0
            return controller_callback(pct, speed, eta)
    return wrapper


def run_translation_sync(translation_model, srt_path, target_language, tab_callbacks=None):
    """
    Run translation synchronously for auto pipeline.
    
    Args:
        translation_model: TranslationModel instance
        srt_path: Path to SRT file
        target_language: Target language code
        tab_callbacks: Dictionary of tab callback functions:
            - 'after': tab.after function for thread-safe UI updates
            - 'display_translated_srt': Function to display translated SRT
            - 'update_status': Function to update status
            - 'enable_burn_btn': Function to enable burn button
            
    Returns:
        bool: True if translation succeeded, False otherwise
    """
    if tab_callbacks is None:
        tab_callbacks = {}
        
    try:
        # Get SRT content
        srt_text = srt_path.read_text(encoding="utf-8")
        
        # Set file path so TranslationModel detects SRT mode
        translation_model.set_current_file_path(str(srt_path))
        
        # Translate the SRT
        success, translated, error = translation_model.translate_srt(srt_text, target_language)
        
        if success:
            # Display translated SRT and save to file
            if 'display_translated_srt' in tab_callbacks:
                display_func = tab_callbacks['display_translated_srt']
                if 'after' in tab_callbacks:
                    tab_callbacks['after'](0, lambda t=translated: display_func(t))
                else:
                    display_func(translated)
            
            # Save translated SRT file
            translated_srt_path = srt_path.parent / "video_translated.srt"
            translated_srt_path.write_text(translated, encoding="utf-8")
            
            # Update status
            if 'update_status' in tab_callbacks:
                status_msg = f"✅ Translation complete. Saved to: {translated_srt_path}"
                if 'after' in tab_callbacks:
                    tab_callbacks['after'](0, lambda: tab_callbacks['update_status'](status_msg))
                else:
                    tab_callbacks['update_status'](status_msg)
            
            # Enable burn button
            if 'enable_burn_btn' in tab_callbacks:
                if 'after' in tab_callbacks:
                    tab_callbacks['after'](0, lambda: tab_callbacks['enable_burn_btn']())
                else:
                    tab_callbacks['enable_burn_btn']()
            
            return True
        else:
            # Translation failed
            if 'update_status' in tab_callbacks:
                error_msg = f"❌ Translation failed: {error}"
                if 'after' in tab_callbacks:
                    tab_callbacks['after'](0, lambda e=error: tab_callbacks['update_status'](error_msg))
                else:
                    tab_callbacks['update_status'](error_msg)
            return False
            
    except Exception as e:
        logger.error(f"Auto translation error: {e}", exc_info=True)
        if 'update_status' in tab_callbacks:
            error_msg = f"❌ Translation error: {e}"
            if 'after' in tab_callbacks:
                tab_callbacks['after'](0, lambda e=e: tab_callbacks['update_status'](error_msg))
            else:
                tab_callbacks['update_status'](error_msg)
        return False