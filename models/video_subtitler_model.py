"""
VideoSubtitlerModel - Phase 1: Download + Transcribe
Handles download via yt-dlp and transcription via Whisper.
Fixed temp paths: temp_subtitler/video.mp4 and temp_subtitler/video.srt
"""
from pathlib import Path
import yt_dlp

TEMP_DIR = Path("temp_subtitler")
VIDEO_PATH = TEMP_DIR / "video.mp4"
SRT_PATH = TEMP_DIR / "video.srt"

# Whisper will be imported lazily to avoid startup issues
_whisper_available = None
_whisper_import_error = None

class VideoSubtitlerModel:
    def __init__(self):
        TEMP_DIR.mkdir(exist_ok=True)

    def download_video(self, url: str, progress_cb=None) -> Path:
        """Download video to VIDEO_PATH using yt-dlp. Overwrites existing."""
        def hook(d):
            if progress_cb and d.get("status") == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total = d.get("total_bytes")
                speed = d.get("speed", 0) or 0
                eta = d.get("eta", 0) or 0
                pct = (downloaded / total * 100) if total else 0
                # Check callback signature and call appropriately
                try:
                    # Try calling with 3 arguments first (new style)
                    progress_cb(pct, speed, eta)
                except TypeError:
                    # Fall back to single argument (old style)
                    progress_cb(d)

        ydl_opts = {
            "outtmpl": str(TEMP_DIR / "video.%(ext)s"),
            "format": "bv*+ba/b",  # Best video + best audio / best fallback
            "merge_output_format": "mp4",
            "postprocessors": [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Fixed typo: preferedformat (one 'r') not preferredformat (two 'r's)
            }],
            "progress_hooks": [hook],
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([url])
            except Exception as e:
                # Enhanced error handling for download failures
                error_msg = str(e)
                if "No supported JavaScript runtime" in error_msg:
                    raise Exception(
                        f"YouTube download failed: {error_msg}\n"
                        "This typically occurs when yt-dlp cannot extract YouTube content "
                        "due to missing JavaScript runtime. Install Node.js or configure "
                        "yt-dlp with --js-runtimes flag."
                    )
                elif "no video formats" in error_msg.lower():
                    raise Exception(
                        f"YouTube download failed: {error_msg}\n"
                        "The video may be unavailable, private, or region-restricted."
                    )
                else:
                    raise Exception(f"YouTube download failed: {error_msg}")
        # yt-dlp may produce video.mp4 directly or video.webm etc — find actual file
        candidates = list(TEMP_DIR.glob("video.*"))
        mp4_files = [f for f in candidates if f.suffix == ".mp4"]
        if mp4_files:
            return mp4_files[0]
        elif candidates:
            return candidates[0]
        raise FileNotFoundError("yt-dlp did not produce a video file in temp_subtitler/")

    def download_and_process_video(self, url: str, progress_cb=None) -> Path:
        """Complete video download and processing pipeline for URL input."""
        try:
            # Clean temp folder before starting
            self.clean_temp_folder()
            
            # Download the video
            video_path = self.download_video(url, progress_cb)
            
            return video_path
            
        except Exception as e:
            raise Exception(f"Failed to download and process video: {str(e)}")

    def process_local_video_file(self, source_path: Path, progress_cb=None) -> Path:
        """Complete local file processing pipeline."""
        try:
            # Clean temp folder before starting
            self.clean_temp_folder()
            
            # Copy file to temp directory with fixed filename pattern
            final_video_path = TEMP_DIR / "video.mp4"
            if final_video_path.exists():
                final_video_path.unlink()
            
            import shutil
            shutil.copy2(source_path, final_video_path)
            
            if progress_cb:
                progress_cb(100, "File processing complete.")
            
            return final_video_path
            
        except Exception as e:
            raise Exception(f"Failed to process local video: {str(e)}")

    def process_local_video(self, file_path: Path, progress_cb=None) -> Path:
        """Process local video file for transcription."""
        if progress_cb:
            progress_cb(0, "Validating file...")
        
        # Validate file exists and is readable
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file format
        supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.mp3', '.wav', '.flac', '.m4a']
        if file_path.suffix.lower() not in supported_formats:
            raise ValueError(f"Unsupported file format: {file_path.suffix}. Supported: {', '.join(supported_formats)}")
        
        if progress_cb:
            progress_cb(50, "Copying file for processing...")
        
        # Copy to temp folder with unique name to avoid conflicts
        import shutil
        import uuid
        temp_filename = f"local_{uuid.uuid4().hex[:8]}{file_path.suffix}"
        target_path = TEMP_DIR / temp_filename
        shutil.copy2(file_path, target_path)
        
        if progress_cb:
            progress_cb(100, "File ready for transcription.")
        
        return target_path

    def transcribe_video(self, video_path: Path, whisper_model: str = "base", language: str = None, progress_cb=None) -> Path:
        """Transcribe video_path with Whisper and write SRT_PATH. Returns SRT_PATH."""
        if progress_cb:
            progress_cb(0, "Loading Whisper model...")
        whisper = self._ensure_whisper_available()
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

    def _ensure_whisper_available(self):
        """Lazy import whisper and handle import errors."""
        global _whisper_available, _whisper_import_error
        
        if _whisper_available is None:
            try:
                import whisper
                _whisper_available = whisper
            except Exception as e:
                _whisper_import_error = e
                _whisper_available = False
                raise ImportError(f"Whisper not available: {e}")
        
        if _whisper_available is False:
            raise ImportError(f"Whisper not available: {_whisper_import_error}")
        
        return _whisper_available

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

    def clean_temp_folder(self):
        """Clean temp folder of previous SRT files and videos."""
        if not TEMP_DIR.exists():
            return
        
        # Remove previous SRT files and video files
        for file in TEMP_DIR.iterdir():
            if file.is_file():
                if file.suffix.lower() in {".srt", ".mp4", ".webm", ".mkv", ".avi", ".mov"}:
                    try:
                        file.unlink()
                    except Exception as e:
                        pass  # Silent cleanup