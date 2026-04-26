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
        url = self.tab.get_url()
        if not url:
            self.tab.show_error("Please enter a video URL.")
            return
        whisper_model = self.tab.get_whisper_model()
        language = self.tab.get_language()
        self.tab.set_busy(True)
        self._thread = threading.Thread(
            target=self._run, args=(url, whisper_model, language), daemon=True
        )
        self._thread.start()

    def _run(self, url, whisper_model, language):
        try:
            self.tab.after(0, lambda: self.tab.update_status("⬇ Downloading video..."))
            self.tab.after(0, lambda: self.tab.update_progress(0, "Downloading..."))

            def dl_progress(pct, speed, eta):
                speed_mb = (speed or 0) / (1024 * 1024)
                msg = f"Downloading: {pct:.1f}% — {speed_mb:.2f} MB/s — ETA: {eta}s"
                self.tab.after(0, lambda p=pct, m=msg: self.tab.update_progress(p, m))

            video_path = self.model.download_video(url, progress_cb=dl_progress)
            self.tab.after(0, lambda: self.tab.update_progress(100, "Download complete."))
            self.tab.after(0, lambda: self.tab.update_status("🎙 Transcribing..."))

            def tx_progress(pct, msg):
                self.tab.after(0, lambda p=pct, m=msg: self极.tab.update_progress(p, m))

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
            logger.error(f"VideoSubtitler Phase 1 error: {e}", exc_info=True)
            self.tab.after(0, lambda: self.tab.update_status(f"❌ Error: {e}"))
            self.tab.after(0, lambda: self.tab.show_error(str(e)))
        finally:
            self.tab.after(0, lambda: self.tab.set_busy(False))