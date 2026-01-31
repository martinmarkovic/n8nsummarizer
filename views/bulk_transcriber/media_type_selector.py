"""
Media Type Selector Component - Manages media format selection UI

Handles video and audio format checkboxes with validation.
Separate from output format selection for clarity.

Version: 1.0
Created: 2026-01-31
Phase: v5.0.4 - Phase 3 Code Quality
"""

import tkinter as tk
from tkinter import ttk
from .constants import MEDIA_TYPES_VIDEO, MEDIA_TYPES_AUDIO, DEFAULT_MEDIA_TYPES


class MediaTypeSelector:
    """
    Manages media type selection (video and audio formats).
    
    Responsibilities:
    - Create and manage checkbox UI for video formats
    - Create and manage checkbox UI for audio formats
    - Validate selection (at least one type must be selected)
    - Provide selected types as list
    """
    
    def __init__(self, parent_tab):
        """
        Initialize media type selector.
        
        Args:
            parent_tab: The parent BulkTranscriberTab instance
        """
        self.parent_tab = parent_tab
        
        # Create BooleanVars for video formats
        self.video_vars = {}
        for ext in MEDIA_TYPES_VIDEO.keys():
            default = ext in DEFAULT_MEDIA_TYPES
            self.video_vars[ext] = tk.BooleanVar(value=default)
        
        # Create BooleanVars for audio formats
        self.audio_vars = {}
        for ext in MEDIA_TYPES_AUDIO.keys():
            default = ext in DEFAULT_MEDIA_TYPES
            self.audio_vars[ext] = tk.BooleanVar(value=default)
    
    def build_video_ui(self, parent_frame, row: int, column: int = 0):
        """
        Build video format selection UI.
        
        Args:
            parent_frame: Parent widget to contain the frame
            row: Grid row position
            column: Grid column position (default 0)
        """
        video_frame = ttk.LabelFrame(parent_frame, text="Video Formats")
        video_frame.grid(row=row, column=column, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        for ext, label in MEDIA_TYPES_VIDEO.items():
            ttk.Checkbutton(
                video_frame,
                text=label,
                variable=self.video_vars[ext],
                command=self._on_selection_changed
            ).pack(anchor=tk.W, padx=10, pady=3)
    
    def build_audio_ui(self, parent_frame, row: int, column: int = 0):
        """
        Build audio format selection UI.
        
        Args:
            parent_frame: Parent widget to contain the frame
            row: Grid row position
            column: Grid column position (default 0)
        """
        audio_frame = ttk.LabelFrame(parent_frame, text="Audio Formats")
        audio_frame.grid(row=row, column=column, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        for ext, label in MEDIA_TYPES_AUDIO.items():
            ttk.Checkbutton(
                audio_frame,
                text=label,
                variable=self.audio_vars[ext],
                command=self._on_selection_changed
            ).pack(anchor=tk.W, padx=10, pady=3)
    
    def get_selected_types(self) -> list:
        """
        Get list of selected media type extensions.
        
        Returns:
            List of selected extensions (e.g., ["mp4", "mp3", "wav"])
        """
        selected = []
        
        # Add selected video formats
        for ext, var in self.video_vars.items():
            if var.get():
                selected.append(ext)
        
        # Add selected audio formats
        for ext, var in self.audio_vars.items():
            if var.get():
                selected.append(ext)
        
        return selected
    
    def has_selection(self) -> bool:
        """
        Check if at least one media type is selected.
        
        Returns:
            True if one or more types selected, False otherwise
        """
        return len(self.get_selected_types()) > 0
    
    def set_types(self, media_types: list):
        """
        Set selected media types programmatically.
        
        Args:
            media_types: List of extension strings to enable
        """
        # Reset all to False
        for var in self.video_vars.values():
            var.set(False)
        for var in self.audio_vars.values():
            var.set(False)
        
        # Enable specified types
        for ext in media_types:
            if ext in self.video_vars:
                self.video_vars[ext].set(True)
            elif ext in self.audio_vars:
                self.audio_vars[ext].set(True)
    
    def _on_selection_changed(self):
        """
        Internal callback when selection changes.
        Validates and notifies parent.
        """
        # Validate at least one type selected
        if not self.has_selection():
            self.parent_tab.append_log(
                "At least one media format must be selected",
                "warning"
            )
        
        # Notify parent to update button state and save preferences
        if hasattr(self.parent_tab, '_update_start_button_state'):
            self.parent_tab._update_start_button_state()
        if hasattr(self.parent_tab, '_save_preferences'):
            self.parent_tab._save_preferences()
