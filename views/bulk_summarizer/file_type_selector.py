"""
File Type Selector for Bulk Summarizer

Manages file type selection UI and state with multiple checkboxes.
Provides methods to get selected types and validate selection.

Version: 5.0.3
Created: 2026-01-31
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Callable, Optional
from .constants import FILE_TYPES


class FileTypeSelector:
    """
    Manages file type selection UI and state.
    
    Provides:
    - Dynamic checkbox creation from FILE_TYPES dict
    - State management for each file type
    - Selection validation (at least one must be selected)
    - List of selected file types
    """
    
    def __init__(self, parent, default_selected: Optional[List[str]] = None):
        """
        Initialize file type selector.
        
        Args:
            parent: Parent tkinter widget
            default_selected: List of file type keys to select by default
        """
        self.parent = parent
        self.file_types = FILE_TYPES
        
        # Create BooleanVar for each file type
        self.vars: Dict[str, tk.BooleanVar] = {}
        for file_key in self.file_types.keys():
            default_value = file_key in default_selected if default_selected else False
            self.vars[file_key] = tk.BooleanVar(value=default_value)
        
        self.on_change_callback: Optional[Callable] = None
    
    def create_ui(self, parent_frame: ttk.LabelFrame, on_change: Optional[Callable] = None):
        """
        Create checkbox UI for all file types.
        
        Args:
            parent_frame: LabelFrame to contain checkboxes
            on_change: Callback function when any checkbox changes
        """
        self.on_change_callback = on_change
        
        for file_key, file_label in self.file_types.items():
            ttk.Checkbutton(
                parent_frame,
                text=file_label,
                variable=self.vars[file_key],
                command=self._on_checkbox_changed
            ).pack(anchor=tk.W, padx=10, pady=5)
    
    def _on_checkbox_changed(self):
        """Internal handler for checkbox changes"""
        if self.on_change_callback:
            self.on_change_callback()
    
    def get_selected(self) -> List[str]:
        """
        Get list of selected file type keys.
        
        Returns:
            List of file type keys (e.g., ['txt', 'srt'])
        """
        return [key for key, var in self.vars.items() if var.get()]
    
    def has_selection(self) -> bool:
        """
        Check if at least one file type is selected.
        
        Returns:
            True if at least one type selected
        """
        return any(var.get() for var in self.vars.values())
    
    def set_selected(self, file_types: List[str]):
        """
        Set which file types are selected.
        
        Args:
            file_types: List of file type keys to select
        """
        for key, var in self.vars.items():
            var.set(key in file_types)
