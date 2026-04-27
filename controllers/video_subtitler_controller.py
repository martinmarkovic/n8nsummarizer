"""
VideoSubtitlerController - Phase 1
Wires VideoSubtitlerTab UI to existing transcription models.
Runs download + transcription in a single daemon thread.
"""
import threading
import shutil
import yt_dlp
import tkinter as tk
import re
from pathlib import Path
from models.transcription import TranscribeModel
from models.translation_model import TranslationModel
from utils.logger import logger

TEMP_DIR = Path("temp_subtitler")
TRANSCRIBE_OUT_DIR = TEMP_DIR / "out"


class VideoSubtitlerController:
    def __init__(self, tab):
        self.tab = tab
        self.transcribe_model = TranscribeModel()
        self.translation_model = TranslationModel()
        self._thread = None
        self.srt_path = None
        self.translated_srt_path = None
        self.output_video_path = None
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

            # Ensure output directory exists and is clean
            TRANSCRIBE_OUT_DIR.mkdir(parents=True, exist_ok=True)
            for f in TRANSCRIBE_OUT_DIR.iterdir():
                if f.is_file():
                    f.unlink()

            # Call transcribe_file with separate output directory
            success, srt_content, error_msg, metadata = self.transcribe_model.transcribe_file(
                file_path=video_path,
                device="cuda",
                output_dir=str(TRANSCRIBE_OUT_DIR),
                keep_formats=[".srt"]
            )
            
            if not success:
                raise Exception(error_msg)
            
            # Copy SRT file from output directory to main temp directory
            srt_source = TRANSCRIBE_OUT_DIR / "video.srt"
            if srt_source.exists():
                shutil.copy2(srt_source, TEMP_DIR / "video.srt")
            
            # Store SRT path for Phase 2 use
            self.srt_path = TEMP_DIR / "video.srt"
            
            # Display SRT content
            self.tab.after(0, lambda t=srt_content: self.tab.display_srt(t))
            self.tab.after(0, lambda: self.tab.enable_translate_btn())  # Enable translation
            self.tab.after(0, lambda: self.tab.update_progress(100, "Done."))
            self.tab.after(0, lambda: self.tab.update_status(
                f"✅ Done. SRT saved to: {self.srt_path}"
            ))
            
        except Exception as e:
            logger.error(f"VideoSubtitler Transcription error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            raise
    
    def on_translate(self):
        """Handle translation request from view."""
        # Disable translate button during translation
        self.tab.translate_btn.config(state=tk.DISABLED)
        
        # Run translation in background thread
        translation_thread = threading.Thread(target=self._run_translation, daemon=True)
        translation_thread.start()
    
    def _run_translation(self):
        """Run translation in background thread."""
        try:
            # Get target language and SRT content
            lang = self.tab.get_target_language()
            srt_text = self.srt_path.read_text(encoding="utf-8")
            
            # Set file path so TranslationModel detects SRT mode
            self.translation_model.set_current_file_path(str(self.srt_path))
            
            # Translate the SRT
            success, translated, error = self.translation_model.translate_text(srt_text, lang)
            
            if success:
                # Display translated SRT and save to file
                self.tab.after(0, lambda t=translated: self.tab.display_translated_srt(t))
                
                # Save translated SRT file
                self.translated_srt_path = TEMP_DIR / "video_translated.srt"
                self.translated_srt_path.write_text(translated, encoding="utf-8")
                
                self.tab.after(0, lambda: self.tab.update_status(
                    f"✅ Translation complete. Saved to: {self.translated_srt_path}"
                ))
                self.tab.after(0, lambda: self.tab.enable_burn_btn())  # Enable burn button
            else:
                self.tab.after(0, lambda e=error: self.tab.show_error(f"Translation failed: {e}"))
                
        except Exception as e:
            logger.error(f"VideoSubtitler Translation error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.show_error(f"Translation error: {e}"))
            
        finally:
            # Re-enable translate button
            self.tab.after(0, lambda: self.tab.translate_btn.config(state=tk.NORMAL))
    
    def on_burn(self):
        """Handle burn request from view."""
        # Disable burn button during processing
        self.tab.burn_btn.config(state=tk.DISABLED)
        
        # Run FFmpeg in background thread
        ffmpeg_thread = threading.Thread(target=self._run_ffmpeg, daemon=True)
        ffmpeg_thread.start()
    
    def _run_ffmpeg(self):
        """Run FFmpeg subtitle burning in background thread."""
        try:
            # Determine subtitle file
            source = self.tab.get_subtitle_source()
            srt_file = TEMP_DIR / ("video_translated.srt" if source == "translated" else "video.srt")
            
            if not srt_file.exists():
                self.tab.after(0, lambda: self.tab.show_error(f"Subtitle file not found: {srt_file}"))
                return
            
            # Find input video file
            input_video = next(TEMP_DIR.glob("video.*"), None)
            if not input_video or input_video.suffix.lower() not in [".mp4", ".webm", ".mkv", ".avi"]:
                self.tab.after(0, lambda: self.tab.show_error("No video file found in temp folder"))
                return
            
            # Set output path
            output_path = TEMP_DIR / "video_subtitled.mp4"
            self.output_video_path = output_path
            
            # Build FFmpeg command with forward slashes for Windows compatibility
            srt_path_fixed = str(srt_file).replace("\\", "/")
            cmd = [
                "ffmpeg", "-y",
                "-i", str(input_video),
                "-vf", f"subtitles={srt_path_fixed}",
                "-c:a", "copy",
                str(output_path)
            ]
            
            self.tab.after(0, lambda: self.tab.update_ffmpeg_status("🔄 Starting FFmpeg..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "FFmpeg: Starting"))
            
            # Run FFmpeg with progress parsing
            import subprocess
            
            # First get total duration using ffprobe
            duration_cmd = [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(input_video)
            ]
            
            try:
                duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=30)
                total_duration = float(duration_result.stdout.strip()) if duration_result.returncode == 0 else 0
            except (subprocess.TimeoutExpired, ValueError):
                total_duration = 0
            
            # Run FFmpeg and parse progress
            process = subprocess.Popen(cmd, stderr=subprocess.PIPE, universal_newlines=True)
            
            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None:
                    break
                
                # Parse time progress from FFmpeg output
                if "time=" in line:
                    time_match = re.search(r"time=([0-9:.]+)", line)
                    if time_match:
                        time_str = time_match.group(1)
                        # Convert HH:MM:SS.ms to seconds
                        time_parts = time_str.split(":")
                        if len(time_parts) == 3:
                            hours, minutes, seconds = map(float, time_parts)
                            elapsed_seconds = hours * 3600 + minutes * 60 + seconds
                            
                            if total_duration > 0:
                                percent = (elapsed_seconds / total_duration) * 100
                                self.tab.after(0, lambda p=percent: self.tab.update_progress(p, f"FFmpeg: {p:.1f}%"))
            
            returncode = process.wait()
            
            if returncode == 0:
                self.tab.after(0, lambda: self.tab.update_ffmpeg_status("✅ Done! Subtitles burned."))
                self.tab.after(0, lambda: self.tab.enable_open_btn())
                self.tab.after(0, lambda: self.tab.update_progress(100, "Burn complete."))
            else:
                # Get last 500 chars of stderr for error message
                stderr_output = process.stderr.read() if process.stderr else ""
                error_msg = stderr_output[-500:] if len(stderr_output) > 500 else stderr_output
                self.tab.after(0, lambda: self.tab.show_error(f"FFmpeg failed: {error_msg}"))
                
        except Exception as e:
            logger.error(f"VideoSubtitler FFmpeg error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.show_error(f"FFmpeg error: {e}"))
            
        finally:
            # Re-enable burn button
            self.tab.after(0, lambda: self.tab.burn_btn.config(state=tk.NORMAL))