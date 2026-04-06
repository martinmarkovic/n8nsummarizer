"""
Bulk Transcriber Tab - Simplified Main Class (Phase 3 Refactored)

Coordinates modular components for bulk audio/video transcription interface.
Reduced from 850+ lines to ~250 lines through modularization.

Version: 2.0
Created: 2026-01-31
Phase: v5.0.4 - Phase 3 Code Quality Improvements
"""

import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from datetime import datetime

from views.base_tab import BaseTab
from utils.logger import logger
from utils.file_scanner import FileScanner

from .media_type_selector import MediaTypeSelector
from .output_format_selector import OutputFormatSelector
from .preferences import BulkTranscriberPreferences
from .ui_components import BulkTranscriberUI


class BulkTranscriberTab(BaseTab):
    """
    Main tab class for bulk media transcription.
    
    Acts as coordinator, delegating to specialized modules:
    - MediaTypeSelector: Manages video/audio format selection
    - OutputFormatSelector: Manages transcript format selection
    - BulkTranscriberPreferences: Handles .env persistence
    - BulkTranscriberUI: Builds UI layout
    - FileScanner: Centralized file counting utility
    """
    
    def __init__(self, notebook):
        # CRITICAL: Initialize variables BEFORE calling super().__init__()
        self.notebook = notebook
        self.source_folder_var = tk.StringVar(value="[No folder selected]")
        self.output_folder_var = tk.StringVar(value="[Default (Parent folder)]")
        
        # Recursive subfolder scanning
        self.recursive_subfolders = tk.BooleanVar(value=False)
        
        # Output location
        self.output_location_default = tk.BooleanVar(value=True)
        
        # Callback registration
        self.on_start_requested = None
        self.on_cancel_requested = None
        
        # Initialize modular components
        self.media_type_selector = MediaTypeSelector(self)
        self.output_format_selector = OutputFormatSelector(self)
        self.preferences = BulkTranscriberPreferences()
        self.ui = BulkTranscriberUI(self)
        
        # NOW call parent init (which calls _setup_ui())
        super().__init__(notebook, "🎬 Bulk Transcriber")
        
        # Load saved preferences from .env
        self._load_preferences()
        
        logger.info("BulkTranscriberTab initialized (Phase 3 refactored)")
    
    def _setup_ui(self):
        """
        Setup UI using modular components.
        
        Layout:
        - Row 0: Browse section (full width)
        - Rows 1-7: Left column (controls) + Right column (status log)
        """
        # Configure grid layout
        self.ui.setup_grid()
        
        # Row 0: Browse section (full width)
        self.ui.build_folder_selection(self.source_folder_var)
        
        # Left column - Controls
        self.media_type_selector.build_video_ui(self, row=1)
        self.media_type_selector.build_audio_ui(self, row=2)
        self.ui.build_recursive_option(self.recursive_subfolders, row=3)
        self.output_format_selector.build_ui(self, row=4)
        self.ui.build_output_location(
            self.output_folder_var,
            self.output_location_default,
            row=5
        )
        
        # Processing and progress sections
        self.start_button, self.cancel_button, self.status_label = \
            self.ui.build_processing_section(row=6)
        
        self.current_file_var, self.progress_bar, self.progress_text_var = \
            self.ui.build_progress_section(row=7)
        
        # Right column - Status log (spans rows 1-7)
        self.status_log = self.ui.build_status_log(row=1, rowspan=7)
    
    # Folder and file management
    
    def _browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title="Select folder with media files to transcribe")
        if folder:
            self.source_folder_var.set(folder)
            
            # Count files using centralized FileScanner
            extensions = self.media_type_selector.get_selected_types()
            file_count = FileScanner.count_files(
                folder,
                extensions,
                recursive=self.recursive_subfolders.get()
            )
            
            self.append_log(
                f"Folder selected: {Path(folder).name} ({file_count} matching media files)",
                "info"
            )
            
            # Update button state
            self._update_start_button_state()
            
            # Auto-set output location to parent folder (default)
            self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")
    
    def _update_start_button_state(self):
        """Update start button state based on folder + media types"""
        folder = self.get_source_folder()
        has_media_types = self.media_type_selector.has_selection()
        
        # Must have folder and at least one media type
        if not folder or not has_media_types:
            self.start_button.config(state=tk.DISABLED)
            return
        
        # Check for matching files
        extensions = self.media_type_selector.get_selected_types()
        file_count = FileScanner.count_files(
            folder,
            extensions,
            recursive=self.recursive_subfolders.get()
        )
        
        if file_count > 0:
            self.start_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.DISABLED)
    
    # Event handlers
    
    def _on_recursive_changed(self):
        """Called when recursive subfolder option changes"""
        folder = self.get_source_folder()
        if folder:
            extensions = self.media_type_selector.get_selected_types()
            file_count = FileScanner.count_files(
                folder,
                extensions,
                recursive=self.recursive_subfolders.get()
            )
            
            recursive_status = "with subfolders" if self.recursive_subfolders.get() else "without subfolders"
            self.append_log(
                f"Scanning mode updated ({recursive_status}): {file_count} matching files",
                "info"
            )
            self._update_start_button_state()
        
        self._save_preferences()
    
    def _on_output_location_changed(self):
        """Called when output location changes"""
        if self.output_location_default.get():
            folder = self.get_source_folder()
            if folder:
                self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")
    
    def _browse_output_folder(self):
        """Open folder selection dialog for output"""
        folder = filedialog.askdirectory(title="Select output folder for transcripts")
        if folder:
            self.output_folder_var.set(folder)
            self.output_location_default.set(False)
            self.append_log(
                f"Output folder set to: {Path(folder).name}",
                "info"
            )
    
    def _on_start_clicked(self):
        """Called when Start button clicked"""
        logger.debug(f"Bulk Transcriber Start button clicked. Callback registered: {self.on_start_requested is not None}")
        if self.on_start_requested:
            self.on_start_requested()
        else:
            logger.warning("No start callback registered for Bulk Transcriber!")
            self.append_log("ERROR: Start callback not registered. Check main.py", "error")
    
    def _on_cancel_clicked(self):
        """Called when Cancel button clicked"""
        if self.on_cancel_requested:
            self.on_cancel_requested()
    
    # Public API methods
    
    def get_source_folder(self) -> str:
        """Get selected folder path"""
        folder = self.source_folder_var.get()
        return folder if folder != "[No folder selected]" else None
    
    def get_output_folder(self) -> str:
        """Get output folder path"""
        folder = self.source_folder_var.get()
        
        if self.output_location_default.get() and folder:
            return str(Path(folder).parent)
        else:
            output = self.output_folder_var.get()
            return output if "[" not in output else None
    
    def get_media_types(self) -> list:
        """Get selected media types as list"""
        return self.media_type_selector.get_selected_types()
    
    def get_output_formats(self) -> dict:
        """Get output format options"""
        return self.output_format_selector.get_selected_formats()
    
    def get_recursive_option(self) -> bool:
        """Get recursive subfolder scanning option"""
        return self.recursive_subfolders.get()
    
    def set_processing_enabled(self, enabled: bool):
        """Enable/disable processing buttons"""
        self.start_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def update_progress(self, current: int, total: int):
        """Update progress bar and text"""
        percentage = (current / total * 100) if total > 0 else 0
        self.progress_bar['value'] = percentage
        self.progress_text_var.set(f"{current} / {total} files")
    
    def set_current_file(self, filename: str):
        """Update current file being processed"""
        self.current_file_var.set(f"Processing: {filename}")
    
    def append_log(self, message: str, status: str = "info"):
        """Append message to status log"""
        self.status_log.config(state=tk.NORMAL)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        indicators = {
            "success": "✓",
            "error": "✗",
            "info": "•",
            "warning": "⚠"
        }
        indicator = indicators.get(status, "•")
        
        log_line = f"[{timestamp}] {indicator} {message}\n"
        self.status_log.insert(tk.END, log_line)
        self.status_log.see(tk.END)
        self.status_log.config(state=tk.DISABLED)
    
    def clear_all(self):
        """Clear all tab data"""
        self.source_folder_var.set("[No folder selected]")
        self.output_folder_var.set("[Default (Parent folder)]")
        self.progress_bar['value'] = 0
        self.progress_text_var.set("0 / 0 files")
        self.current_file_var.set("Idle")
        self.status_log.config(state=tk.NORMAL)
        self.status_log.delete('1.0', tk.END)
        self.status_log.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
    
    def get_content(self) -> str:
        """Get current tab content (log)"""
        return self.status_log.get('1.0', tk.END)
    
    # Callback registration
    
    def set_on_start_requested(self, callback):
        """Register callback for start button"""
        self.on_start_requested = callback
        logger.info(f"Bulk Transcriber start callback registered: {callback}")
    
    def set_on_cancel_requested(self, callback):
        """Register callback for cancel button"""
        self.on_cancel_requested = callback
    
    # Preference management (delegates to preferences module)
    
    def _load_preferences(self):
        """Load saved preferences from .env file"""
        try:
            prefs = self.preferences.load()
            
            # Apply media types
            self.media_type_selector.set_types(prefs["media_types"])
            
            # Apply output formats
            self.output_format_selector.set_formats(prefs["output_formats"])
            
            # Apply recursive option
            self.recursive_subfolders.set(prefs["recursive_subfolders"])
            
            logger.info("Bulk Transcriber preferences loaded")
        except Exception as e:
            logger.warning(f"Could not load preferences: {str(e)}")
    
    def _save_preferences(self):
        """Save preferences to .env file"""
        try:
            media_types = self.media_type_selector.get_selected_types()
            output_formats = self.output_format_selector.get_selected_format_list()
            recursive = self.recursive_subfolders.get()
            
            self.preferences.save(media_types, output_formats, recursive)
        except Exception as e:
            logger.warning(f"Could not save preferences: {str(e)}")
