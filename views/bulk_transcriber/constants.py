"""
Bulk Transcriber Constants - Configuration values

Defines media types, output formats, and default settings.

Version: 1.0
Created: 2026-01-31
Phase: v5.0.4 - Phase 3 Code Quality
"""

# Media type definitions
# Dictionary format: extension -> display name
MEDIA_TYPES_VIDEO = {
    "mp4": "MP4 (Default)",
    "mov": "MOV",
    "avi": "AVI",
    "mkv": "MKV",
    "webm": "WebM"
}

MEDIA_TYPES_AUDIO = {
    "mp3": "MP3",
    "wav": "WAV",
    "m4a": "M4A",
    "flac": "FLAC",
    "aac": "AAC",
    "wma": "WMA"
}

# Output format definitions
OUTPUT_FORMATS = {
    "srt": "SRT (Default - Subtitles)",
    "txt": "TXT (Plain text)",
    "vtt": "VTT (WebVTT format)",
    "json": "JSON (Structured data)"
}

# Default selections
DEFAULT_MEDIA_TYPES = ["mp4"]  # Default to MP4 only
DEFAULT_OUTPUT_FORMATS = ["srt"]  # Default to SRT only
DEFAULT_RECURSIVE = False  # Default to non-recursive scanning

# Environment variable prefix
ENV_PREFIX = "BULK_TRANS_"
