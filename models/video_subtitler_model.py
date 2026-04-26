"""
VideoSubtitlerModel - Phase 1: Download + Transcribe
Handles download via yt-dlp and transcription via Whisper.
Fixed temp paths: temp_subtitler/video.mp4 and temp_subtitler/video.srt
"""
from pathlib import Path
import yt_dlp
import whisper

TEMP_DIR = Path("temp_subtitler")
VIDEO_PATH = TEMP_DIR / "video.mp4"
SRT_PATH = TEMP_DIR / "video.srt"

class VideoSubtitlerModel:
    def __init__(self):
        TEMP_DIR.mkdir(exist_ok=True)

    def download_video(self, url: str, progress_cb=None) -> Path:
        """Download video to VIDEO_PATH using yt-dlp. Overwrites existing."""
        def hook(d):
            if progress_cb and d.get("status") == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 1)
                speed = d.get("speed", 0) or 0
                eta = d.get("eta", 0) or 0
                pct = (downloaded / total * 100) if total else 0
                progress_cb(pct, speed, eta)

        ydl_opts = {
            "outtmpl": str(TEMP_DIR / "video.%(ext)s"),
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "progress_hooks": [hook],
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # yt-dlp may produce video.mp4 directly or video.webm etc — find actual file
        candidates = list(TEMP_DIR.glob("video.*"))
        mp4_files = [f for f in candidates if f.suffix == ".mp4"]
        if mp4_files:
            return mp4_files[0]
        elif candidates:
            return candidates[0]
        raise FileNotFoundError("yt-dlp did not produce a video file in temp_subtitler/")

    def transcribe_video(self, video_path: Path, whisper_model: str = "base", language: str = None, progress_cb=None) -> Path:
        """Transcribe video_path with Whisper and write SRT_PATH. Returns SRT_PATH."""
        if progress_cb:
            progress_cb(0, "Loading Whisper model...")
        model = whisper.load_model(whisper_model)
        if progress_cb:
            progress_cb(50, "Transcribing...")
        options = {}
        if language and language != "auto":
            options["language"] = language
        result = model.transcribe(str(video_path), **options)
        srt_content = self._segments_to_srt(result["segments"])
        SRT_PATH.write_text(srt_content, encoding="utf-8")
        return SRT_PATH

    def _segments_to_srt(self, segments) -> str:
        lines = []
        for i, seg in enumerate(segments, 1):
            start = self._fmt_time(seg["start"])
            end = self._fmt_time(seg["end"])
            lines.append(f"{i}\n{start} --> {end}\n{seg['text'].strip()}\n")
        return "\n".join(lines)

    def _fmt_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def get_srt_path(self) -> Path:
        return SRT_PATH

    def get_video_path(self) -> Path:
        return VIDEO_PATH

    def srt_exists(self) -> bool:
        return SRT_PATH.exists()

    def video_exists(self) -> bool:
        return VIDEO_PATH.exists()