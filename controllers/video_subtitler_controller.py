"""
VideoSubtitlerController - Phase 1
Wires VideoSubtitlerTab UI to existing transcription models.
Runs download + transcription in a single daemon thread.
"""
import threading
import shutil
import yt_dlp
from pathlib import Path
from models.transcription import TranscribeModel
from utils.logger import logger

TEMP_DIR = Path("temp_subtitler")


class VideoSubtitlerController:
    def __init__(self, tab):
        self.tab = tab
        self.transcribe_model = TranscribeModel()
        self._thread = None
        self.srt_path = None
        tab.set_controller(self)
        logger.info("VideoSubtitlerController initialized")

    def on_start(self):
        if self._thread and self._thread.is_alive():
            self.tab.show_error("Already running. Please wait.")
            return
        
        input_mode = self.tab.get_input_mode()
        
        if input_mode == "url":
            url = self.tab.get_url()
            if not url:
                self.tab.show_error("Please enter a video URL.")
                return
            self.tab.set_busy(True)
            self._thread = threading.Thread(
                target=self._run_url, args=(url,), daemon=True
            )
        else:
            file_path = self.tab.get_local_file_path()
            if not file_path:
                self.tab.show_error("Please select a local video file.")
                return
            self.tab.set_busy(True)
            self._thread = threading.Thread(
                target=self._run_local, args=(file_path,), daemon=True
            )
        
        self._thread.start()

    def _run_url(self, url):
        """Process URL-based video using yt-dlp direct download."""
        try:
            self.tab.after(0, lambda: self.tab.update_status("⬇ Downloading video..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "Downloading..."))

            # Ensure temp directory exists
            TEMP_DIR.mkdir(exist_ok=True)
            
            # yt-dlp options with fixed output filename "video.%(ext)s"
            ydl_opts = {
                'format': 'bv*+ba/b',  # Best video + best audio / best fallback
                'outtmpl': str(TEMP_DIR / 'video.%(ext)s'),  # Fixed filename pattern
                'progress_hooks': [self._download_progress_hook],
                'quiet': True,
                'no_warnings': True,
            }
            
            # Download the video
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            self.tab.after(0, lambda: self.tab.update_progress(100, "Download complete."))
            
            # Find the downloaded video file
            downloaded_files = list(TEMP_DIR.glob("video.*"))
            if not downloaded_files:
                raise FileNotFoundError("No video file found after download")
            
            # Use the first matching file (should be video.mp4, video.webm, etc.)
            video_path = downloaded_files[0]
            
            # Run transcription (video file remains in temp directory for other steps)
            self._run_transcription(str(video_path))
            
        except Exception as e:
            logger.error(f"VideoSubtitler URL error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            self.tab.after(0, lambda e=e: self.tab.show_error(str(e)))
        finally:
            self.tab.after(0, lambda: self.tab.set_busy(False))

    def _download_progress_hook(self, progress_info):
        """Progress hook for yt-dlp downloads."""
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
                self.tab.after(0, lambda p=percent, m=msg: self.tab.update_progress(p, m))

    def _run_local(self, file_path):
        """Process local video file."""
        try:
            self.tab.after(0, lambda: self.tab.update_status("📁 Processing local file..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "Processing..."))

            # Ensure temp directory exists
            TEMP_DIR.mkdir(exist_ok=True)
            
            # Copy file to temp directory with fixed filename pattern
            source_path = Path(file_path)
            final_video_path = TEMP_DIR / "video.mp4"  # Always use .mp4 for consistency
            if final_video_path.exists():
                final_video_path.unlink()
            
            shutil.copy2(source_path, final_video_path)
            self.tab.after(0, lambda: self.tab.update_progress(100, "File processing complete."))
            
            # Run transcription (video file remains in temp directory for other steps)
            self._run_transcription(str(final_video_path))
            
        except Exception as e:
            logger.error(f"VideoSubtitler Local File error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            self.tab.after(0, lambda e=e: self.tab.show_error(str(e)))
        finally:
            self.tab.after(0, lambda: self.tab.set_busy(False))

    def _run_transcription(self, video_path):
        """Run transcription on prepared video file."""
        try:
            self.tab.after(0, lambda: self.tab.update_status("🎙 Transcribing..."))

            # Call transcribe_file with exact parameters from instructions
            # Keep video formats to preserve video file for other processing steps
            success, srt_content, error_msg, metadata = self.transcribe_model.transcribe_file(
                file_path=video_path,
                device="cuda",
                output_dir=str(TEMP_DIR),
                keep_formats=[".srt", ".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv"]
            )
            
            if not success:
                raise Exception(error_msg)
            
            # Store SRT path for Phase 2 use
            self.srt_path = TEMP_DIR / "video.srt"
            
            # Display SRT content
            self.tab.after(0, lambda t=srt_content: self.tab.display_srt(t))
            self.tab.after(0, lambda: self.tab.update_progress(100, "Done."))
            self.tab.after(0, lambda: self.tab.update_status(
                f"✅ Done. SRT saved to: {self.srt_path}"
            ))
            
        except Exception as e:
            logger.error(f"VideoSubtitler Transcription error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            raise