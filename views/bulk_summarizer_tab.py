"""
Bulk Summarizer Tab - Phase 4.2 Advanced Options

Manages the bulk file summarization interface:
- File type selection with multiple checkboxes (txt, srt, docx, pdf)
- Output format options (separate files, combined file)
- Output location selection (default or custom)
- Progress tracking
- Status logging
- Remember last choice in .env

Version: 4.2
Created: 2025-12-10
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from datetime import datetime
import os
from views.base_tab import BaseTab
from utils.logger import logger


class BulkSummarizerTab(BaseTab):
    """UI for bulk file summarization (Phase 4.2)"""
    
    def __init__(self, notebook):
        # CRITICAL: Initialize variables BEFORE calling super().__init__()
        # super().__init__() calls _setup_ui() which needs these variables
        self.notebook = notebook
        self.source_folder_var = tk.StringVar(value="[No folder selected]")
        self.output_folder_var = tk.StringVar(value="[Default (Parent folder)]")
        
        # File type selections (multiple checkboxes)
        self.file_type_txt = tk.BooleanVar(value=True)
        self.file_type_srt = tk.BooleanVar(value=False)
        self.file_type_docx = tk.BooleanVar(value=False)
        self.file_type_pdf = tk.BooleanVar(value=False)
        
        # Output format options (multiple checkboxes)
        self.output_separate = tk.BooleanVar(value=True)
        self.output_combined = tk.BooleanVar(value=False)
        
        # Output location
        self.output_location_default = tk.BooleanVar(value=True)
        
        # Callback registration
        self.on_start_requested = None
        self.on_cancel_requested = None
        
        # NOW call parent init (which calls _setup_ui())
        super().__init__(notebook, "Bulk Summarizer")
        
        # Load saved preferences from .env
        self._load_preferences()
        
        logger.info("BulkSummarizerTab initialized")
    
    def _setup_ui(self):
        """
        Setup bulk summarizer UI.
        
        Sections:
        1. Folder Selection
        2. File Type Selection (Checkboxes)
        3. Output Format Options (Checkboxes)
        4. Output Location Selection
        5. Processing Controls
        6. Progress Tracking
        7. Status Log
        """
        # Make tab expand
        self.columnconfigure(0, weight=1)
        self.rowconfigure(6, weight=1)
        
        self._setup_folder_selection()
        self._setup_file_type()
        self._setup_output_format()
        self._setup_output_location()
        self._setup_processing_section()
        self._setup_progress_section()
        self._setup_status_log()
    
    def _setup_folder_selection(self):
        """Folder selection with browse button"""
        folder_frame = ttk.LabelFrame(self, text="Select Source Folder")
        folder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        folder_frame.columnconfigure(1, weight=1)
        
        ttk.Button(
            folder_frame,
            text="[Browse...]",
            command=self._browse_folder
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(
            folder_frame,
            textvariable=self.source_folder_var
        ).pack(side=tk.LEFT, padx=10, pady=5)
    
    def _browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title="Select folder to summarize")
        if folder:
            self.source_folder_var.set(folder)
            file_count = self._count_matching_files(folder)
            self.append_log(
                f"Folder selected: {Path(folder).name} ({file_count} matching files)",
                "info"
            )
            # Enable start button
            if file_count > 0:
                self.start_button.config(state=tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)
                self.append_log("No matching files found", "warning")
            
            # Auto-set output location to parent folder (default)
            parent_folder = str(Path(folder).parent)
            self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")
    
    def _count_matching_files(self, folder: str) -> int:
        """Count files matching selected types"""
        folder_path = Path(folder)
        count = 0
        
        if self.file_type_txt.get():
            count += len(list(folder_path.glob("*.txt")))
        if self.file_type_srt.get():
            count += len(list(folder_path.glob("*.srt")))
        if self.file_type_docx.get():
            count += len(list(folder_path.glob("*.docx")))
        if self.file_type_pdf.get():
            count += len(list(folder_path.glob("*.pdf")))
        
        return count
    
    def _setup_file_type(self):
        """Checkboxes for file type selection (multiple)"""
        type_frame = ttk.LabelFrame(self, text="File Types to Scan")
        type_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        files = [
            ("TXT", self.file_type_txt),
            ("SRT (Subtitles)", self.file_type_srt),
            ("DOCX", self.file_type_docx),
            ("PDF", self.file_type_pdf)
        ]
        
        for label, var in files:
            ttk.Checkbutton(
                type_frame,
                text=label,
                variable=var,
                command=self._on_file_type_changed
            ).pack(anchor=tk.W, padx=10, pady=5)
    
    def _on_file_type_changed(self):
        """Called when file type selection changes"""
        # Check if at least one file type is selected
        if not any([self.file_type_txt.get(), self.file_type_srt.get(), 
                   self.file_type_docx.get(), self.file_type_pdf.get()]):
            self.append_log("At least one file type must be selected", "warning")
            self.start_button.config(state=tk.DISABLED)
            return
        
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            self.append_log(
                f"File types updated: {file_count} matching files",
                "info"
            )
            # Update start button state
            if file_count > 0:
                self.start_button.config(state=tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)
        
        # Save preferences
        self._save_preferences()
    
    def _setup_output_format(self):
        """Checkboxes for output format options"""
        output_frame = ttk.LabelFrame(self, text="Output Format Options")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Checkbutton(
            output_frame,
            text="Separate Files (Uncombined)",
            variable=self.output_separate
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        ttk.Checkbutton(
            output_frame,
            text="Combined File (Single output)",
            variable=self.output_combined
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        info_label = ttk.Label(
            output_frame,
            text="Note: At least one output format must be selected",
            foreground="gray"
        )
        info_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
    
    def _setup_output_location(self):
        """Radio buttons for output location"""
        loc_frame = ttk.LabelFrame(self, text="Output Location")
        loc_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        loc_frame.columnconfigure(1, weight=1)
        
        ttk.Radiobutton(
            loc_frame,
            text="Default (Parent folder of source)",
            variable=self.output_location_default,
            value=True,
            command=self._on_output_location_changed
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        button_frame = ttk.Frame(loc_frame)
        button_frame.pack(anchor=tk.W, padx=10, pady=5)
        
        ttk.Radiobutton(
            button_frame,
            text="Custom Location:",
            variable=self.output_location_default,
            value=False,
            command=self._on_output_location_changed
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="[Browse...]",
            command=self._browse_output_folder
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            loc_frame,
            textvariable=self.output_folder_var
        ).pack(anchor=tk.W, padx=30, pady=5)
    
    def _on_output_location_changed(self):
        """Called when output location changes"""
        if self.output_location_default.get():
            folder = self.get_source_folder()
            if folder:
                self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")
    
    def _browse_output_folder(self):
        """Open folder selection dialog for output"""
        folder = filedialog.askdirectory(title="Select output folder for summaries")
        if folder:
            self.output_folder_var.set(folder)
            self.output_location_default.set(False)
            self.append_log(
                f"Output folder set to: {Path(folder).name}",
                "info"
            )
    
    def _setup_processing_section(self):
        """Start/Cancel buttons"""
        proc_frame = ttk.LabelFrame(self, text="Processing")
        proc_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        proc_frame.columnconfigure(0, weight=1)
        
        info_frame = ttk.Frame(proc_frame)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(
            info_frame,
            text="Ready",
            foreground="green"
        )
        self.status_label.pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(proc_frame)
        button_frame.pack(pady=10)
        
        self.start_button = ttk.Button(
            button_frame,
            text="Start Processing",
            command=self._on_start_clicked,
            state=tk.DISABLED
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel_clicked,
            state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT, padx=5)
    
    def _setup_progress_section(self):
        """Progress bar and current file info"""
        prog_frame = ttk.LabelFrame(self, text="Progress")
        prog_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        prog_frame.columnconfigure(0, weight=1)
        
        self.current_file_var = tk.StringVar(value="Idle")
        ttk.Label(prog_frame, textvariable=self.current_file_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.progress_bar = ttk.Progressbar(
            prog_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        self.progress_text_var = tk.StringVar(value="0 / 0 files")
        ttk.Label(prog_frame, textvariable=self.progress_text_var).pack(anchor=tk.W, padx=10, pady=5)
    
    def _setup_status_log(self):
        """Status log with scroll"""
        log_frame = ttk.LabelFrame(self, text="Status Log")
        log_frame.grid(row=6, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), 
                      padx=10, pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_log = tk.Text(
            log_frame,
            height=10,
            width=60,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        self.status_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.status_log.yview)
    
    # Public methods
    
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
    
    def get_file_types(self) -> list:
        """Get selected file types as list"""
        types = []
        if self.file_type_txt.get():
            types.append("txt")
        if self.file_type_srt.get():
            types.append("srt")
        if self.file_type_docx.get():
            types.append("docx")
        if self.file_type_pdf.get():
            types.append("pdf")
        return types
    
    def get_output_formats(self) -> dict:
        """Get output format options"""
        return {
            "separate": self.output_separate.get(),
            "combined": self.output_combined.get()
        }
    
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
    
    # Event handlers
    
    def _on_start_clicked(self):
        """Called when Start button clicked"""
        if self.on_start_requested:
            self.on_start_requested()
    
    def _on_cancel_clicked(self):
        """Called when Cancel button clicked"""
        if self.on_cancel_requested:
            self.on_cancel_requested()
    
    # Callback registration
    
    def set_on_start_requested(self, callback):
        """Register callback for start button"""
        self.on_start_requested = callback
    
    def set_on_cancel_requested(self, callback):
        """Register callback for cancel button"""
        self.on_cancel_requested = callback
    
    # Preference management
    
    def _load_preferences(self):
        """Load saved preferences from .env file"""
        try:
            env_path = Path(".env")
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("BULK_FILE_TYPES="):
                            file_types = line.split("=")[1].split(",")
                            self.file_type_txt.set("txt" in file_types)
                            self.file_type_srt.set("srt" in file_types)
                            self.file_type_docx.set("docx" in file_types)
                            self.file_type_pdf.set("pdf" in file_types)
                        elif line.startswith("BULK_OUTPUT_SEPARATE="):
                            self.output_separate.set(line.split("=")[1].lower() == "true")
                        elif line.startswith("BULK_OUTPUT_COMBINED="):
                            self.output_combined.set(line.split("=")[1].lower() == "true")
            logger.info("Bulk Summarizer preferences loaded")
        except Exception as e:
            logger.warning(f"Could not load preferences: {str(e)}")
    
    def _save_preferences(self):
        """Save preferences to .env file"""
        try:
            env_path = Path(".env")
            
            # Build file types string
            file_types = []
            if self.file_type_txt.get():
                file_types.append("txt")
            if self.file_type_srt.get():
                file_types.append("srt")
            if self.file_type_docx.get():
                file_types.append("docx")
            if self.file_type_pdf.get():
                file_types.append("pdf")
            
            file_types_str = ",".join(file_types) if file_types else "txt"
            
            # Read existing .env
            env_content = {}
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("BULK_"):
                            key_value = line.split("=", 1)
                            if len(key_value) == 2:
                                env_content[key_value[0]] = key_value[1]
            
            # Update with new preferences
            env_content["BULK_FILE_TYPES"] = file_types_str
            env_content["BULK_OUTPUT_SEPARATE"] = str(self.output_separate.get())
            env_content["BULK_OUTPUT_COMBINED"] = str(self.output_combined.get())
            
            # Write back
            with open(env_path, "w") as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            
            logger.info("Bulk Summarizer preferences saved")
        except Exception as e:
            logger.warning(f"Could not save preferences: {str(e)}")
