"""
Bulk Transcriber Package - Phase 3 Refactoring (v5.0.4)

Modular package for bulk audio/video transcription interface.

Public API:
    BulkTranscriberTab - Main tab class for the transcription interface

Internal Modules:
    constants - Configuration values for media types and output formats
    media_type_selector - Media type selection UI component
    output_format_selector - Output format selection UI component
    preferences - .env file persistence for user preferences
    ui_components - UI layout builder

Version: 1.0
Created: 2026-01-31
Phase: v5.0.4 - Phase 3 Code Quality Improvements
"""

from .tab import BulkTranscriberTab

__all__ = ["BulkTranscriberTab"]
