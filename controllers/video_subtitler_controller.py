"""
VideoSubtitlerController - Phase 1
Wires VideoSubtitlerTab UI to VideoSubtitlerModel.
Runs download + transcription in a single daemon thread.
"""
import threading
from models.video_subtitler_model import VideoSubtitlerModel
from utils.logger import logger


class VideoSubtitlerController:
    def __init__(self, tab):
        self.tab = tab
        self.model = VideoSubtitlerModel()
        self._thread = None
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
        """Process URL-based video."""
        whisper_model = self.tab.get_whisper_model()
        language = self.tab.get_language()
        
        try:
            self.tab.after(0, lambda: self.tab.update_status("⬇ Downloading video..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "Downloading..."))

            def dl_progress(pct, speed, eta):
                speed_mb = (speed or 0) / (1024 * 1024)
                msg = f"Downloading: {pct:.1f}% — {speed_mb:.2f} MB/s — ETA: {eta}s"
                self.tab.after(0, lambda p=pct, m=msg: self.tab.update_progress(p, m))

            video_path = self.model.download_video(url, progress_cb=dl_progress)
            self.tab.after(0, lambda: self.tab.update_progress(100, "Download complete."))
            self.tab._run_transcription(video_path, whisper_model, language)
        except Exception as e:
            logger.error(f"VideoSubtitler URL error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            self.tab.after(0, lambda e=e: self.tab.show_error(str(e)))
        finally:
            self.tab.after(0, lambda: self.tab.set_busy(False))

    def _run_local(self, file_path):
        """Process local video file."""
        whisper_model = self.tab.get_whisper_model()
        language = self.tab.get_language()
        
        try:
            self.tab.after(0, lambda: self.tab.update_status("📁 Processing local file..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "Processing..."))

            def file_progress(pct, msg):
                self.tab.after(0, lambda p=pct, m=msg: self.tab.update_progress(p, m))

            video_path = self.model.process_local_video(Path(file_path), progress_cb=file_progress)
            self.tab.after(0, lambda: self.tab.update_progress(100, "File processing complete."))
            self.tab._run_transcription(video_path, whisper_model, language)
        except Exception as e:
            logger.error(f"VideoSubtitler Local File error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            self.tab.after(0, lambda e=e: self.tab.show_error(str(e)))
        finally:
            self.tab.after(0, lambda: self.tab.set_busy(False))

    def _run_transcription(self, video_path, whisper_model, language):
        """Run transcription on prepared video file."""
        try:
            self.tab.after(0, lambda: self.tab.update_status("🎙 Transcribing..."))

            def tx_progress(pct, msg):
                self.tab.after(0, lambda p=pct, m=msg: self.tab.update_progress(p, m))

            srt_path = self.model.transcribe_video(
                video_path, whisper_model=whisper_model,
                language=None if language == "auto" else language,
                progress_cb=tx_progress
            )
            srt_text = srt_path.read_text(encoding="utf-8")
            self.tab.after(0, lambda t=srt_text: self.tab.display_srt(t))
            self.tab.after(0, lambda: self.tab.update_progress(100, "Done."))
            self.tab.after(0, lambda: self.tab.update_status(
                f"✅ Done. SRT saved to: {srt_path}"
            ))
        except Exception as e:
            logger.error(f"VideoSubtitler Transcription error: {e}", exc_info=True)
            self.tab.after(0, lambda e=e: self.tab.update_status(f"❌ Error: {e}"))
            raise  # Re-raise to handle in outer except
