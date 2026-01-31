"""
Bulk Summarizer Tab - Simplified in v5.0.3 Phase 2

Manages the bulk file summarization interface with modular architecture:
- FileTypeSelector handles file type UI and state
- Preferences handles .env persistence
- UIComponents handles all layout and widgets
- FileScanner provides centralized file counting

Main tab class reduced from 680 to ~200 lines.

Version: 5.0.3
Created: 2026-01-31
"""

import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from views.base_tab import BaseTab
from utils.logger import logger
from utils.file_scanner import FileScanner
from .file_type_selector import FileTypeSelector
from .preferences import BulkSummarizerPreferences
from .ui_components import BulkSummarizerUI
from .constants import NO_FOLDER_TEXT, DEFAULT_OUTPUT_TEXT


class BulkSummarizerTab(BaseTab):
    """
    Simplified bulk file summarizer tab.
    
    Responsibilities:
    - Coordinate between UI components
    - Handle user interactions
    - Manage tab state
    - Provide interface for controller
    
    Delegates:
    - File type selection -> FileTypeSelector
    - Preference management -> BulkSummarizerPreferences
    - UI layout -> BulkSummarizerUI
    - File scanning -> FileScanner
    """
    
    def __init__(self, notebook):
        # Initialize variables BEFORE calling super().__init__()
        self.notebook = notebook
        self.source_folder_var = tk.StringVar(value=NO_FOLDER_TEXT)
        self.output_folder_var = tk.StringVar(value=DEFAULT_OUTPUT_TEXT)
        
        # Output format options
        self.output_separate = tk.BooleanVar(value=True)
        self.output_combined = tk.BooleanVar(value=False)
        
        # Recursive subfolder scanning (v4.7)
        self.recursive_subfolders = tk.BooleanVar(value=False)
        
        # Output location
        self.output_location_default = tk.BooleanVar(value=True)
        
        # Callback registration
        self.on_start_requested = None
        self.on_cancel_requested = None
        
        # Initialize modular components
        self.preferences = BulkSummarizerPreferences()
        self.file_type_selector = None  # Created in _setup_ui
        self.ui = None  # Created in _setup_ui
        
        # Call parent init (triggers _setup_ui)
        super().__init__(notebook, "📦 Bulk Summarizer")
        
        # Load saved preferences
        self._load_preferences()
        
        logger.info("BulkSummarizerTab initialized (v5.0.3 modular)")
    
    def _setup_ui(self):
        """
        Setup UI using modular components.
        
        Delegates most UI creation to BulkSummarizerUI.
        """
        # Create UI components builder
        self.ui = BulkSummarizerUI(self)
        
        # Setup layout with callbacks
        self.ui.setup_layout({
            "source_folder_var": self.source_folder_var,
            "output_folder_var": self.output_folder_var,
            "browse_folder_callback": self._browse_folder,
            "browse_output_callback": self._browse_output_folder,
            "start_callback": self._on_start_clicked,
            "cancel_callback": self._on_cancel_clicked
        })
        
        # Create file type selector and UI (Row 1)
        type_frame = self.ui.create_file_type_frame()
        self.file_type_selector = FileTypeSelector(self, default_selected=["txt"])
        self.file_type_selector.create_ui(type_frame, on_change=self._on_file_type_changed)
        
        # Create other UI sections
        self.ui.create_recursive_frame(self.recursive_subfolders, self._on_recursive_changed)
        self.ui.create_output_format_frame(self.output_separate, self.output_combined)
        self.ui.create_output_location_frame(
            self.output_location_default,
            self._browse_output_folder,
            self._on_output_location_changed
        )
        self.ui.create_processing_section(self._on_start_clicked, self._on_cancel_clicked)
        self.ui.create_progress_section()
    
    # Folder selection
    
    def _browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title="Select folder to summarize")
        if folder:
            self.source_folder_var.set(folder)
            file_count = self._count_matching_files()
            self.ui.append_log(
                f"Folder selected: {Path(folder).name} ({file_count} matching files)",
                "info"
            )
            
            # Enable/disable start button based on file count
            self.ui.set_buttons_enabled(start_enabled=(file_count > 0), cancel_enabled=False)
            
            if file_count == 0:
                self.ui.append_log("No matching files found", "warning")
            
            # Auto-set output location to parent folder (default)
            self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")
    
    def _browse_output_folder(self):
        """Open folder selection dialog for output"""
        folder = filedialog.askdirectory(title="Select output folder for summaries")
        if folder:
            self.output_folder_var.set(folder)
            self.output_location_default.set(False)
            self.ui.append_log(f"Output folder set to: {Path(folder).name}", "info")
    
    # File counting
    
    def _count_matching_files(self) -> int:
        """Count files matching selected types using FileScanner"""
        folder = self.get_source_folder()
        if not folder:
            return 0
        
        extensions = self.file_type_selector.get_selected()
        recursive = self.recursive_subfolders.get()
        
        return FileScanner.count(folder, extensions, recursive)
    
    # Event handlers
    
    def _on_file_type_changed(self):
        """Called when file type selection changes"""
        # Validate at least one type selected
        if not self.file_type_selector.has_selection():
            self.ui.append_log("At least one file type must be selected", "warning")
            self.ui.set_buttons_enabled(start_enabled=False, cancel_enabled=False)
            return
        
        # Update file count
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files()
            self.ui.append_log(f"File types updated: {file_count} matching files", "info")
            self.ui.set_buttons_enabled(start_enabled=(file_count > 0), cancel_enabled=False)
        
        # Save preferences
        self._save_preferences()
    
    def _on_recursive_changed(self):
        """Called when recursive subfolder option changes"""
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files()
            recursive_status = "with subfolders" if self.recursive_subfolders.get() else "without subfolders"
            self.ui.append_log(f"Scanning mode updated ({recursive_status}): {file_count} matching files", "info")
            self.ui.set_buttons_enabled(start_enabled=(file_count > 0), cancel_enabled=False)
        
        # Save preferences
        self._save_preferences()
    
    def _on_output_location_changed(self):
        """Called when output location changes"""
        if self.output_location_default.get():
            folder = self.get_source_folder()
            if folder:
                self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")
    
    def _on_start_clicked(self):
        """Called when Start button clicked"""
        if self.on_start_requested:
            self.on_start_requested()
    
    def _on_cancel_clicked(self):
        """Called when Cancel button clicked"""
        if self.on_cancel_requested:
            self.on_cancel_requested()
    
    # Public interface methods (for controller)
    
    def get_source_folder(self) -> str:
        """Get selected folder path"""
        folder = self.source_folder_var.get()
        return folder if folder != NO_FOLDER_TEXT else None
    
    def get_output_folder(self) -> str:
        """Get output folder path"""
        folder = self.source_folder_var.get()
        
        if self.output_location_default.get() and folder:
            return str(Path(folder).parent)
        else:
            output = self.output_folder_var.get()
            return output if "[" not in output else None
    
    def get_file_types(self) -> list:
        """Get selected file types as list"""
        return self.file_type_selector.get_selected()
    
    def get_output_formats(self) -> dict:
        """Get output format options"""
        return {
            "separate": self.output_separate.get(),
            "combined": self.output_combined.get()
        }
    
    def get_recursive_option(self) -> bool:
        """Get recursive subfolder scanning option"""
        return self.recursive_subfolders.get()
    
    def set_processing_enabled(self, enabled: bool):
        """Enable/disable processing buttons (backward compatibility)"""
        self.ui.set_buttons_enabled(start_enabled=enabled, cancel_enabled=enabled)
    
    def update_progress(self, current: int, total: int):
        """Update progress bar and text"""
        self.ui.update_progress(current, total)
    
    def set_current_file(self, filename: str):
        """Update current file being processed"""
        self.ui.set_current_file(filename)
    
    def append_log(self, message: str, status: str = "info"):
        """Append message to status log"""
        self.ui.append_log(message, status)
    
    def clear_all(self):
        """Clear all tab data"""
        self.source_folder_var.set(NO_FOLDER_TEXT)
        self.output_folder_var.set(DEFAULT_OUTPUT_TEXT)
        self.ui.reset_progress()
        self.ui.clear_log()
        self.ui.set_buttons_enabled(start_enabled=False, cancel_enabled=False)
    
    def get_content(self) -> str:
        """Get current tab content (log)"""
        return self.ui.get_log_content()
    
    # Callback registration
    
    def set_on_start_requested(self, callback):
        """Register callback for start button"""
        self.on_start_requested = callback
    
    def set_on_cancel_requested(self, callback):
        """Register callback for cancel button"""
        self.on_cancel_requested = callback
    
    # Preference management
    
    def _load_preferences(self):
        """Load saved preferences using BulkSummarizerPreferences"""
        prefs = self.preferences.load()
        
        # Apply to UI
        self.file_type_selector.set_selected(prefs["file_types"])
        self.output_separate.set(prefs["output_separate"])
        self.output_combined.set(prefs["output_combined"])
        self.recursive_subfolders.set(prefs["recursive_subfolders"])
    
    def _save_preferences(self):
        """Save preferences using BulkSummarizerPreferences"""
        self.preferences.save(
            file_types=self.file_type_selector.get_selected(),
            output_separate=self.output_separate.get(),
            output_combined=self.output_combined.get(),
            recursive_subfolders=self.recursive_subfolders.get()
        )
