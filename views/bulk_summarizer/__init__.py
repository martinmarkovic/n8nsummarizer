"""
Bulk Summarizer Module - Modularized in v5.0.3 Phase 2

This package provides the bulk file summarization interface with improved modularity:
- FileTypeSelector: Manages file type selection UI and state
- Preferences: Handles .env persistence
- UIComponents: UI layout and widget creation
- Constants: Centralized configuration values
- BulkSummarizerTab: Main tab class (simplified)

Version: 5.0.3
Created: 2026-01-31
"""

from .tab import BulkSummarizerTab

__all__ = ['BulkSummarizerTab']
