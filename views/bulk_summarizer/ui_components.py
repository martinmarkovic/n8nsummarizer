"""
UI Components Builder for Bulk Summarizer Tab

Handles all UI layout and widget creation.
Separates presentation from logic.

Version: 5.0.3
Created: 2026-01-31
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable
from datetime import datetime
from .constants import STATUS_INDICATORS


class BulkSummarizerUI:
    """
    Builds UI components for Bulk Summarizer tab.
    
    Responsibilities:
    - Create all UI widgets
    - Setup layout (two-column grid)
    - Provide access to widgets for controller
    - Handle UI state updates (progress, status)
    """
    
    def __init__(self, parent):
        """
        Initialize UI builder.
        
        Args:
            parent: Parent tab widget
        """
        self.parent = parent
        
        # Widget references (set during setup)
        self.source_folder_var = None
        self.output_folder_var = None
        self.status_label = None
        self.start_button = None
        self.cancel_button = None
        self.progress_bar = None
        self.progress_text_var = None
        self.current_file_var = None
        self.status_log = None
    
    def setup_layout(self, widgets: Dict):
        """
        Setup complete UI layout.
        
        Args:
            widgets: Dict containing all required widget variables and callbacks
                Required keys:
                - source_folder_var: StringVar for source folder path
                - output_folder_var: StringVar for output folder path
                - browse_folder_callback: Callable for browse folder button
                - browse_output_callback: Callable for browse output button
                - start_callback: Callable for start button
                - cancel_callback: Callable for cancel button
        """
        # Store widget references
        self.source_folder_var = widgets["source_folder_var"]
        self.output_folder_var = widgets["output_folder_var"]
        
        # Configure grid (2 columns)
        self.parent.columnconfigure(0, weight=0)  # Left column (controls)
        self.parent.columnconfigure(1, weight=1)  # Right column (status log, expands)
        self.parent.rowconfigure(6, weight=1)     # Status log area expands vertically
        
        # Row 0: Folder selection (full width)
        self._create_folder_selection(widgets["browse_folder_callback"])
        
        # Left column widgets will be added by parent
        # (file type selector, recursive option, output format, etc.)
        
        # Right column (Row 1-6): Status log
        self._create_status_log()
    
    def _create_folder_selection(self, browse_callback: Callable):
        """Create folder selection UI (Row 0, full width)"""
        folder_frame = ttk.LabelFrame(self.parent, text="Select Source Folder")
        folder_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
        folder_frame.columnconfigure(1, weight=1)
        
        ttk.Button(
            folder_frame,
            text="[Browse...]",
            command=browse_callback
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(
            folder_frame,
            textvariable=self.source_folder_var
        ).pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
    
    def create_file_type_frame(self) -> ttk.LabelFrame:
        """Create and return file type selection frame (Row 1, left column)"""
        type_frame = ttk.LabelFrame(self.parent, text="File Types to Scan")
        type_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        return type_frame
    
    def create_recursive_frame(self, recursive_var: tk.BooleanVar, 
                              on_change: Callable) -> ttk.LabelFrame:
        """Create recursive scanning option frame (Row 2, left column)"""
        recursive_frame = ttk.LabelFrame(self.parent, text="Scanning Options")
        recursive_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Checkbutton(
            recursive_frame,
            text="Scan Subfolders (recursive scanning)",
            variable=recursive_var,
            command=on_change
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        info_label = ttk.Label(
            recursive_frame,
            text="When enabled: Scans all subfolders and maintains folder structure in output",
            foreground="gray",
            font=("TkDefaultFont", 9)
        )
        info_label.pack(anchor=tk.W, padx=30, pady=(0, 5))
        
        return recursive_frame
    
    def create_output_format_frame(self, separate_var: tk.BooleanVar,
                                   combined_var: tk.BooleanVar) -> ttk.LabelFrame:
        """Create output format options frame (Row 3, left column)"""
        output_frame = ttk.LabelFrame(self.parent, text="Output Format Options")
        output_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Checkbutton(
            output_frame,
            text="Separate Files (Uncombined)",
            variable=separate_var
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        ttk.Checkbutton(
            output_frame,
            text="Combined File (Single output)",
            variable=combined_var
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        info_label = ttk.Label(
            output_frame,
            text="Note: At least one output format must be selected",
            foreground="gray"
        )
        info_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        return output_frame
    
    def create_output_location_frame(self, location_default_var: tk.BooleanVar,
                                     browse_callback: Callable,
                                     radio_callback: Callable) -> ttk.LabelFrame:
        """Create output location selection frame (Row 4, left column)"""
        loc_frame = ttk.LabelFrame(self.parent, text="Output Location")
        loc_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        loc_frame.columnconfigure(1, weight=1)
        
        ttk.Radiobutton(
            loc_frame,
            text="Default (Parent folder of source)",
            variable=location_default_var,
            value=True,
            command=radio_callback
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        button_frame = ttk.Frame(loc_frame)
        button_frame.pack(anchor=tk.W, padx=10, pady=5)
        
        ttk.Radiobutton(
            button_frame,
            text="Custom Location:",
            variable=location_default_var,
            value=False,
            command=radio_callback
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame,
            text="[Browse...]",
            command=browse_callback
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(
            loc_frame,
            textvariable=self.output_folder_var
        ).pack(anchor=tk.W, padx=30, pady=5)
        
        return loc_frame
    
    def create_processing_section(self, start_callback: Callable,
                                 cancel_callback: Callable) -> ttk.LabelFrame:
        """Create processing buttons section (Row 5, left column)"""
        proc_frame = ttk.LabelFrame(self.parent, text="Processing")
        proc_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
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
            command=start_callback,
            state=tk.DISABLED
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=cancel_callback,
            state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        return proc_frame
    
    def create_progress_section(self) -> ttk.LabelFrame:
        """Create progress bar section (Row 6, left column)"""
        prog_frame = ttk.LabelFrame(self.parent, text="Progress")
        prog_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        prog_frame.columnconfigure(0, weight=1)
        
        self.current_file_var = tk.StringVar(value="Idle")
        ttk.Label(prog_frame, textvariable=self.current_file_var).pack(
            anchor=tk.W, padx=10, pady=5
        )
        
        self.progress_bar = ttk.Progressbar(
            prog_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        self.progress_text_var = tk.StringVar(value="0 / 0 files")
        ttk.Label(prog_frame, textvariable=self.progress_text_var).pack(
            anchor=tk.W, padx=10, pady=5
        )
        
        return prog_frame
    
    def _create_status_log(self):
        """Create status log (Right column, rows 1-6)"""
        log_frame = ttk.LabelFrame(self.parent, text="Status Log")
        log_frame.grid(
            row=1, column=1, rowspan=6, 
            sticky=(tk.W, tk.E, tk.N, tk.S), 
            padx=10, pady=10
        )
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_log = tk.Text(
            log_frame,
            height=10,
            width=40,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        self.status_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.status_log.yview)
    
    # Public methods for UI updates
    
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
        indicator = STATUS_INDICATORS.get(status, STATUS_INDICATORS["info"])
        
        log_line = f"[{timestamp}] {indicator} {message}\n"
        self.status_log.insert(tk.END, log_line)
        self.status_log.see(tk.END)
        self.status_log.config(state=tk.DISABLED)
    
    def clear_log(self):
        """Clear status log"""
        self.status_log.config(state=tk.NORMAL)
        self.status_log.delete('1.0', tk.END)
        self.status_log.config(state=tk.DISABLED)
    
    def reset_progress(self):
        """Reset progress bar and text"""
        self.progress_bar['value'] = 0
        self.progress_text_var.set("0 / 0 files")
        self.current_file_var.set("Idle")
    
    def set_buttons_enabled(self, start_enabled: bool, cancel_enabled: bool):
        """Enable/disable processing buttons"""
        self.start_button.config(state=tk.NORMAL if start_enabled else tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL if cancel_enabled else tk.DISABLED)
    
    def get_log_content(self) -> str:
        """Get current log content"""
        return self.status_log.get('1.0', tk.END)
