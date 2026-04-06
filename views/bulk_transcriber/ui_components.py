"""
Bulk Transcriber UI Components - Layout builder

Builds all UI sections for the Bulk Transcriber tab.
Separates presentation from business logic.

Version: 1.0
Created: 2026-01-31
Phase: v5.0.4 - Phase 3 Code Quality
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from datetime import datetime


class BulkTranscriberUI:
    """
    Builds UI components for Bulk Transcriber tab.
    
    Responsibilities:
    - Create folder selection section
    - Create recursive option section
    - Create output location section
    - Create processing buttons section
    - Create progress section
    - Create status log section
    - Handle grid layout
    """
    
    def __init__(self, parent_tab):
        """
        Initialize UI builder.
        
        Args:
            parent_tab: The parent BulkTranscriberTab instance
        """
        self.tab = parent_tab
    
    def setup_grid(self):
        """
        Configure grid layout for two-column design.
        - Column 0: Controls (fixed width)
        - Column 1: Status log (expands)
        - Row 8: Expands vertically for log
        """
        self.tab.columnconfigure(0, weight=0)
        self.tab.columnconfigure(1, weight=1)
        self.tab.rowconfigure(8, weight=1)
    
    def build_folder_selection(self, source_folder_var: tk.StringVar):
        """
        Build folder selection section (full width at top).
        
        Args:
            source_folder_var: StringVar for selected folder path
        """
        folder_frame = ttk.LabelFrame(self.tab, text="Select Media Folder")
        folder_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
        folder_frame.columnconfigure(1, weight=1)
        
        ttk.Button(
            folder_frame,
            text="[Browse...]",
            command=self.tab._browse_folder
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(
            folder_frame,
            textvariable=source_folder_var
        ).pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
    
    def build_recursive_option(self, recursive_var: tk.BooleanVar, row: int, column: int = 0):
        """
        Build recursive scanning option section.
        
        Args:
            recursive_var: BooleanVar for recursive option
            row: Grid row position
            column: Grid column position (default 0)
        """
        recursive_frame = ttk.LabelFrame(self.tab, text="Scanning Options")
        recursive_frame.grid(row=row, column=column, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Checkbutton(
            recursive_frame,
            text="Scan Subfolders (recursive scanning)",
            variable=recursive_var,
            command=self.tab._on_recursive_changed
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        info_label = ttk.Label(
            recursive_frame,
            text="When enabled: Scans all subfolders and maintains folder structure in output",
            foreground="gray",
            font=("TkDefaultFont", 9)
        )
        info_label.pack(anchor=tk.W, padx=30, pady=(0, 5))
    
    def build_output_location(self, output_folder_var: tk.StringVar, 
                            output_default_var: tk.BooleanVar,
                            row: int, column: int = 0):
        """
        Build output location section.
        
        Args:
            output_folder_var: StringVar for output folder path
            output_default_var: BooleanVar for default location option
            row: Grid row position
            column: Grid column position (default 0)
        """
        loc_frame = ttk.LabelFrame(self.tab, text="Output Location")
        loc_frame.grid(row=row, column=column, sticky=(tk.W, tk.E), padx=10, pady=10)
        loc_frame.columnconfigure(1, weight=1)
        
        ttk.Radiobutton(
            loc_frame,
            text="Default (Parent folder of source)",
            variable=output_default_var,
            value=True,
            command=self.tab._on_output_location_changed
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        button_frame = ttk.Frame(loc_frame)
        button_frame.pack(anchor=tk.W, padx=10, pady=5)
        
        ttk.Radiobutton(
            button_frame,
            text="Custom Location:",
            variable=output_default_var,
            value=False,
            command=self.tab._on_output_location_changed
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="[Browse...]",
            command=self.tab._browse_output_folder
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            loc_frame,
            textvariable=output_folder_var
        ).pack(anchor=tk.W, padx=30, pady=5)
    
    def build_processing_section(self, row: int, column: int = 0) -> tuple:
        """
        Build processing buttons section.
        
        Args:
            row: Grid row position
            column: Grid column position (default 0)
        
        Returns:
            Tuple of (start_button, cancel_button, status_label)
        """
        proc_frame = ttk.LabelFrame(self.tab, text="Processing")
        proc_frame.grid(row=row, column=column, sticky=(tk.W, tk.E), padx=10, pady=10)
        proc_frame.columnconfigure(0, weight=1)
        
        info_frame = ttk.Frame(proc_frame)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        status_label = ttk.Label(
            info_frame,
            text="Ready",
            foreground="green"
        )
        status_label.pack(side=tk.LEFT)
        
        button_frame = ttk.Frame(proc_frame)
        button_frame.pack(pady=10)
        
        start_button = ttk.Button(
            button_frame,
            text="Start Transcribing",
            command=self.tab._on_start_clicked,
            state=tk.DISABLED
        )
        start_button.pack(side=tk.LEFT, padx=5)
        
        cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.tab._on_cancel_clicked,
            state=tk.DISABLED
        )
        cancel_button.pack(side=tk.LEFT, padx=5)
        
        return start_button, cancel_button, status_label
    
    def build_progress_section(self, row: int, column: int = 0) -> tuple:
        """
        Build progress tracking section.
        
        Args:
            row: Grid row position
            column: Grid column position (default 0)
        
        Returns:
            Tuple of (current_file_var, progress_bar, progress_text_var)
        """
        prog_frame = ttk.LabelFrame(self.tab, text="Progress")
        prog_frame.grid(row=row, column=column, sticky=(tk.W, tk.E), padx=10, pady=10)
        prog_frame.columnconfigure(0, weight=1)
        
        current_file_var = tk.StringVar(value="Idle")
        ttk.Label(prog_frame, textvariable=current_file_var).pack(anchor=tk.W, padx=10, pady=5)
        
        progress_bar = ttk.Progressbar(
            prog_frame,
            mode='determinate',
            length=400
        )
        progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        progress_text_var = tk.StringVar(value="0 / 0 files")
        ttk.Label(prog_frame, textvariable=progress_text_var).pack(anchor=tk.W, padx=10, pady=5)
        
        return current_file_var, progress_bar, progress_text_var
    
    def build_status_log(self, row: int, rowspan: int = 7, column: int = 1) -> tk.Text:
        """
        Build status log section (right column).
        
        Args:
            row: Grid row position
            rowspan: Number of rows to span
            column: Grid column position (default 1)
        
        Returns:
            Text widget for log display
        """
        log_frame = ttk.LabelFrame(self.tab, text="Status Log")
        log_frame.grid(row=row, column=column, rowspan=rowspan,
                      sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        status_log = tk.Text(
            log_frame,
            height=10,
            width=40,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        status_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=status_log.yview)
        
        return status_log
