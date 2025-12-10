"""
Bulk Summarizer Tab - Phase 4.1 UI

Manages the bulk file summarization interface:
- Folder selection
- File type selection (txt, docx, both)
- Progress tracking
- Status logging

Version: 4.0
Created: 2025-12-10
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from datetime import datetime
from views.base_tab import BaseTab
from utils.logger import logger


class BulkSummarizerTab(BaseTab):
    """UI for bulk file summarization (Phase 4.1)"""
    
    def __init__(self, notebook):
        super().__init__(notebook, "Bulk Summarizer")
        self.notebook = notebook
        
        # Variables
        self.source_folder_var = tk.StringVar(value="[No folder selected]")
        self.file_type_var = tk.StringVar(value="txt")
        
        # Callback registration
        self.on_start_requested = None
        self.on_cancel_requested = None
        
        logger.info("BulkSummarizerTab initialized")
    
    def _setup_ui(self):
        """
        Setup bulk summarizer UI.
        
        Sections:
        1. Folder Selection
        2. File Type Selection
        3. Processing Controls
        4. Progress Tracking
        5. Status Log
        """
        # Make tab expand
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)
        
        self._setup_folder_selection()
        self._setup_file_type()
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
    
    def _count_matching_files(self, folder: str) -> int:
        """Count files matching selected type"""
        folder_path = Path(folder)
        file_type = self.file_type_var.get()
        
        if file_type == "txt":
            return len(list(folder_path.glob("*.txt")))
        elif file_type == "docx":
            return len(list(folder_path.glob("*.docx")))
        else:  # both
            return len(list(folder_path.glob("*.txt"))) + len(list(folder_path.glob("*.docx")))
    
    def _setup_file_type(self):
        """Radio buttons for file type selection"""
        type_frame = ttk.LabelFrame(self, text="File Type Selection")
        type_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        types = [
            ("TXT files only", "txt"),
            ("DOCX files only", "docx"),
            ("Both TXT and DOCX", "both")
        ]
        
        for label, value in types:
            ttk.Radiobutton(
                type_frame,
                text=label,
                variable=self.file_type_var,
                value=value,
                command=self._on_file_type_changed
            ).pack(anchor=tk.W, padx=10, pady=5)
    
    def _on_file_type_changed(self):
        """Called when file type selection changes"""
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            self.append_log(
                f"File type changed: {file_count} matching files",
                "info"
            )
            # Update start button state
            if file_count > 0:
                self.start_button.config(state=tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)
    
    def _setup_processing_section(self):
        """Start/Cancel buttons"""
        proc_frame = ttk.LabelFrame(self, text="Processing")
        proc_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
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
        prog_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
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
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), 
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
    
    def get_file_type(self) -> str:
        """Get file type selection: 'txt', 'docx', or 'both'"""
        return self.file_type_var.get()
    
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
        self.file_type_var.set("txt")
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
