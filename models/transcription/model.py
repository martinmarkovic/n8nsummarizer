"""High-level transcription model extracted from models/transcribe_model.py.

This module keeps the public TranscribeModel API but delegates
low-level concerns (running the CLI, processing outputs, filename
sanitisation, YouTube helpers) to dedicated helper modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from utils.logger import logger

from .cli_runner import run_transcribe_cli
from .outputs import process_outputs
from .youtube import (
    get_youtube_title,
    extract_youtube_id,
    validate_youtube_url,
)
from .sanitizer import sanitize_filename


class TranscribeModel:
    """High-level transcription orchestrator.

    Responsibilities (same as original):
    - Call transcribe-anything CLI for local files and YouTube URLs
    - Manage output files (SRT, TXT, etc.)
    - Handle user-selected file formats
    - Delete unwanted formats
    - Return SRT transcript content
    - Handle device selection
    - Be Windows MAX_PATH aware
    """

    WINDOWS_MAX_PATH = 260
    SAFE_FILENAME_MAX = 80

    def __init__(self, transcribe_path: Optional[str] = None) -> None:
        self.transcribe_path = (
            transcribe_path or "F:\\Python scripts\\Transcribe anything"
        )
        self.supported_formats = {
            # Video
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".mkv",
            ".flv",
            ".webm",
            ".mpg",
            ".mpeg",
            ".m4v",
            ".3gp",
            ".ogv",
            ".ts",
            ".vob",
            ".asf",
            ".rm",
            ".rmvb",
            ".divx",
            ".xvid",
            ".f4v",
            # Audio
            ".mp3",
            ".wav",
            ".flac",
            ".aac",
            ".ogg",
            ".wma",
            ".m4a",
            ".opus",
            ".aiff",
            ".au",
        }
        logger.info(
            "TranscribeModel initialised (transcribe-anything wrapper, MAX_PATH compliant)"
        )

    # ------------------------------------------------------------------
    # Public API – file transcription
    # ------------------------------------------------------------------

    def transcribe_file(
        self,
        file_path: str,
        device: str = "cuda",
        output_dir: Optional[str] = None,
        keep_formats: Optional[List[str]] = None,
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[Dict]]:
        """Transcribe a local media file.

        Returns:
            (success, srt_content, error_msg, metadata_dict)
        """

        try:
            path_obj = Path(file_path)

            if not path_obj.exists():
                return False, None, f"File not found: {path_obj}", None

            if path_obj.suffix.lower() not in self.supported_formats:
                return False, None, f"Unsupported format: {path_obj.suffix}", None

            if keep_formats is None:
                keep_formats = [".txt", ".srt"]

            out_dir = Path(output_dir) if output_dir else path_obj.parent
            out_dir.mkdir(parents=True, exist_ok=True)

            base_name = sanitize_filename(path_obj.stem, out_dir)
            logger.info("Original filename: %s", path_obj.stem)
            logger.info("Sanitized filename: %s", base_name)

            success, error = run_transcribe_cli(
                input_path=str(path_obj),
                output_dir=str(out_dir),
                device=device,
            )
            if not success:
                return False, None, error, None

            transcript_content, metadata = process_outputs(
                output_dir=out_dir,
                base_name=base_name,
                keep_formats=keep_formats,
                source_type="file",
                url=None,
            )

            if transcript_content is None:
                return False, None, "No transcript generated", None

            logger.info("Successfully transcribed: %s", path_obj.name)
            return True, transcript_content, None, metadata

        except Exception as exc:  # noqa: BLE001
            error = f"Error transcribing file: {exc}"
            logger.error(error, exc_info=True)
            return False, None, error, None

    # ------------------------------------------------------------------
    # Public API – YouTube transcription
    # ------------------------------------------------------------------

    def transcribe_youtube(
        self,
        youtube_url: str,
        device: str = "cuda",
        output_dir: Optional[str] = None,
        keep_formats: Optional[List[str]] = None,
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[Dict]]:
        """Transcribe a YouTube video.

        Returns:
            (success, srt_content, error_msg, metadata_dict)
        """

        try:
            if not validate_youtube_url(youtube_url):
                return False, None, "Invalid YouTube URL", None

            if keep_formats is None:
                keep_formats = [".txt", ".srt"]

            out_dir = (
                Path(output_dir)
                if output_dir
                else Path.home() / "Documents" / "Transcribe Anything"
            )
            out_dir.mkdir(parents=True, exist_ok=True)

            base_name = get_youtube_title(youtube_url)
            if not base_name:
                video_id = extract_youtube_id(youtube_url)
                base_name = video_id if video_id else "youtube_video"

            base_name = sanitize_filename(base_name, out_dir)
            logger.info("Transcribing YouTube video: %s", base_name)

            success, error = run_transcribe_cli(
                input_path=youtube_url,
                output_dir=str(out_dir),
                device=device,
            )
            if not success:
                return False, None, error, None

            transcript_content, metadata = process_outputs(
                output_dir=out_dir,
                base_name=base_name,
                keep_formats=keep_formats,
                source_type="youtube",
                url=youtube_url,
            )

            if transcript_content is None:
                return False, None, "No transcript generated", None

            logger.info("Successfully transcribed YouTube video: %s", base_name)
            return True, transcript_content, None, metadata

        except Exception as exc:  # noqa: BLE001
            error = f"Error transcribing YouTube: {exc}"
            logger.error(error, exc_info=True)
            return False, None, error, None

    # ------------------------------------------------------------------
    # Utility API
    # ------------------------------------------------------------------

    @staticmethod
    def get_supported_formats() -> set:
        """Return the set of supported media extensions."""

        # Kept static for backwards compatibility
        return {
            # Video
            ".mp4",
            ".avi",
            ".mov",
            ".wmv",
            ".mkv",
            ".flv",
            ".webm",
            ".mpg",
            ".mpeg",
            ".m4v",
            ".3gp",
            ".ogv",
            ".ts",
            ".vob",
            ".asf",
            ".rm",
            ".rmvb",
            ".divx",
            ".xvid",
            ".f4v",
            # Audio
            ".mp3",
            ".wav",
            ".flac",
            ".aac",
            ".ogg",
            ".wma",
            ".m4a",
            ".opus",
            ".aiff",
            ".au",
        }
