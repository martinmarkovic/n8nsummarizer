"""
Output Format Selector Component - Manages transcript format selection UI

Handles output format checkboxes (SRT, TXT, VTT, JSON) with validation.
Separate from media type selection for clarity.

Version: 1.0
Created: 2026-01-31
Phase: v5.0.4 - Phase 3 Code Quality
"""

import tkinter as tk
from tkinter import ttk
from .constants import OUTPUT_FORMATS, DEFAULT_OUTPUT_FORMATS


class OutputFormatSelector:
    """
    Manages output transcript format selection.
    
    Responsibilities:
    - Create and manage checkbox UI for output formats
    - Validate selection (at least one format must be selected)
    - Provide selected formats as dict
    """
    
    def __init__(self, parent_tab):
        """
        Initialize output format selector.
        
        Args:
            parent_tab: The parent BulkTranscriberTab instance
        """
        self.parent_tab = parent_tab
        
        # Create BooleanVars for output formats
        self.format_vars = {}
        for ext in OUTPUT_FORMATS.keys():
            default = ext in DEFAULT_OUTPUT_FORMATS
            self.format_vars[ext] = tk.BooleanVar(value=default)
    
    def build_ui(self, parent_frame, row: int, column: int = 0):
        """
        Build output format selection UI.
        
        Args:
            parent_frame: Parent widget to contain the frame
            row: Grid row position
            column: Grid column position (default 0)
        """
        output_frame = ttk.LabelFrame(parent_frame, text="Output Transcript Formats")
        output_frame.grid(row=row, column=column, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        for ext, label in OUTPUT_FORMATS.items():
            ttk.Checkbutton(
                output_frame,
                text=label,
                variable=self.format_vars[ext],
                command=self._on_selection_changed
            ).pack(anchor=tk.W, padx=10, pady=3)
        
        # Add info label
        info_label = ttk.Label(
            output_frame,
            text="Note: At least one output format must be selected",
            foreground="gray",
            font=("TkDefaultFont", 9)
        )
        info_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
    
    def get_selected_formats(self) -> dict:
        """
        Get dict of output format selections.
        
        Returns:
            Dict mapping format names to boolean values
            Example: {"srt": True, "txt": False, "vtt": False, "json": True}
        """
        return {ext: var.get() for ext, var in self.format_vars.items()}
    
    def get_selected_format_list(self) -> list:
        """
        Get list of selected output format extensions.
        
        Returns:
            List of selected extensions (e.g., ["srt", "txt"])
        """
        return [ext for ext, var in self.format_vars.items() if var.get()]
    
    def has_selection(self) -> bool:
        """
        Check if at least one output format is selected.
        
        Returns:
            True if one or more formats selected, False otherwise
        """
        return len(self.get_selected_format_list()) > 0
    
    def set_formats(self, formats: list):
        """
        Set selected output formats programmatically.
        
        Args:
            formats: List of format extension strings to enable
        """
        # Reset all to False
        for var in self.format_vars.values():
            var.set(False)
        
        # Enable specified formats
        for ext in formats:
            if ext in self.format_vars:
                self.format_vars[ext].set(True)
    
    def _on_selection_changed(self):
        """
        Internal callback when selection changes.
        Notifies parent to save preferences.
        """
        # Notify parent to save preferences
        if hasattr(self.parent_tab, '_save_preferences'):
            self.parent_tab._save_preferences()
