"""
Constants for Bulk Summarizer Tab

Centralizes all configuration values, file types, and default settings.

Version: 5.0.3
Created: 2026-01-31
"""

# File type definitions
FILE_TYPES = {
    "txt": "TXT",
    "srt": "SRT (Subtitles)",
    "docx": "DOCX",
    "pdf": "PDF"
}

# Output format definitions
OUTPUT_FORMATS = {
    "separate": "Separate Files (Uncombined)",
    "combined": "Combined File (Single output)"
}

# Default settings
DEFAULT_FILE_TYPES = ["txt"]  # Default to TXT only
DEFAULT_OUTPUT_SEPARATE = True
DEFAULT_OUTPUT_COMBINED = False
DEFAULT_RECURSIVE = False

# Log status indicators
STATUS_INDICATORS = {
    "success": "✓",
    "error": "✗",
    "info": "•",
    "warning": "⚠"
}

# UI text
NO_FOLDER_TEXT = "[No folder selected]"
DEFAULT_OUTPUT_TEXT = "[Default (Parent folder)]"
