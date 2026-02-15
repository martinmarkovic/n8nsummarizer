"""
Downloader Tab - YouTube video downloader interface (v6.1)

Provides UI for downloading YouTube videos with:
- URL input field
- Destination folder selection
- Resolution/quality chooser
- Download button
- Progress display
- Status log

Integrated with DownloaderController for download operations.

Created: 2026-02-15
Version: 6.1.1 - Fixed resolution dropdown population
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from views.base_tab import BaseTab
from controllers.downloader_controller import DownloaderController


class DownloaderTab(BaseTab):
    """YouTube video downloader tab with full UI and controller integration."""

    def __init__(self, notebook):
        self.notebook = notebook
        
        # State variables
        self.url_var = tk.StringVar()
        self.download_path_var = tk.StringVar(value="[No folder selected]")
        self.resolution_var = tk.StringVar()
        self.progress_var = tk.StringVar(value="Ready")
        
        # Controller will be initialized after UI setup
        self.controller = None
        
        super().__init__(notebook, "📥 Downloader")
        
        # Initialize controller after UI is ready
        self.controller = DownloaderController(self)
        
        # Populate resolution dropdown and set default
        resolutions = self.controller.get_available_resolutions()
        if resolutions:
            self.resolution_combo['values'] = resolutions  # FIX: Populate combobox
            self.resolution_var.set(resolutions[0])  # "Best Available"
            self.controller.set_resolution(resolutions[0])

    def _setup_ui(self):
        """Build downloader UI with input controls and status display."""
        # Configure grid - 3 main rows
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Log area expands
        
        # === Row 0: Input Controls Frame ===
        controls_frame = ttk.LabelFrame(self, text="Download Settings", padding=15)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        controls_frame.columnconfigure(1, weight=1)
        
        # URL Input
        ttk.Label(controls_frame, text="YouTube URL:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5
        )
        
        url_entry = ttk.Entry(controls_frame, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Info button
        info_btn = ttk.Button(
            controls_frame,
            text="Info",
            width=8,
            command=self._fetch_video_info
        )
        info_btn.grid(row=0, column=2, padx=(5, 0), pady=5)
        
        # Destination Folder
        ttk.Label(controls_frame, text="Save to:").grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=5
        )
        
        path_label = ttk.Label(
            controls_frame,
            textvariable=self.download_path_var,
            foreground="gray"
        )
        path_label.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        browse_btn = ttk.Button(
            controls_frame,
            text="Browse...",
            command=self._browse_folder
        )
        browse_btn.grid(row=1, column=2, padx=(5, 0), pady=5)
        
        # Resolution Selection
        ttk.Label(controls_frame, text="Quality:").grid(
            row=2, column=0, sticky=tk.W, padx=(0, 10), pady=5
        )
        
        # Resolution combobox - will be populated in __init__ after controller is ready
        self.resolution_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.resolution_var,
            state="readonly",
            width=20
        )
        self.resolution_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        self.resolution_combo.bind('<<ComboboxSelected>>', self._on_resolution_change)
        
        # Download Button
        self.download_btn = ttk.Button(
            controls_frame,
            text="⬇ Download",
            command=self._start_download,
            width=12
        )
        self.download_btn.grid(row=2, column=2, padx=(5, 0), pady=5)
        
        # === Row 1: Video Info Display ===
        info_frame = ttk.LabelFrame(self, text="Video Information", padding=10)
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=(0, 10))
        info_frame.columnconfigure(0, weight=1)
        
        self.info_text = tk.Text(info_frame, height=4, wrap=tk.WORD, state=tk.DISABLED)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # === Row 2: Progress & Log ===
        log_frame = ttk.LabelFrame(self, text="Download Progress", padding=10)
        log_frame.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(0, 10))
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)
        
        # Progress label
        progress_label = ttk.Label(
            log_frame,
            textvariable=self.progress_var,
            foreground="blue"
        )
        progress_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Status log
        self.status_log = tk.Text(log_frame, wrap=tk.WORD, height=10)
        self.status_log.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        log_scroll = ttk.Scrollbar(log_frame, command=self.status_log.yview)
        log_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.status_log.configure(yscrollcommand=log_scroll.set)
        
    def populate_resolutions(self):
        """Populate resolution combobox after controller is initialized."""
        if self.controller:
            resolutions = self.controller.get_available_resolutions()
            self.resolution_combo['values'] = resolutions
            
    def _browse_folder(self):
        """Open folder browser dialog for selecting download destination."""
        folder = filedialog.askdirectory(title="Select Download Folder")
        if folder:
            self.download_path_var.set(folder)
            if self.controller:
                self.controller.set_download_path(folder)
                self.log_message(f"Download folder set: {folder}")
                
    def _on_resolution_change(self, event=None):
        """Handle resolution selection change."""
        resolution = self.resolution_var.get()
        if self.controller:
            self.controller.set_resolution(resolution)
            self.log_message(f"Quality changed to: {resolution}")
            
    def _fetch_video_info(self):
        """Fetch and display video information."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a YouTube URL first")
            return
            
        if self.controller:
            self.controller.fetch_video_info(url)
            
    def _start_download(self):
        """Initiate download process."""
        if self.controller:
            self.controller.start_download()
            
    # === View Helper Methods (called by controller) ===
    
    def get_url(self) -> str:
        """Get current URL from input field.
        
        Returns:
            YouTube URL string
        """
        return self.url_var.get().strip()
        
    def get_download_path(self) -> str:
        """Get current download path.
        
        Returns:
            Download folder path string
        """
        return self.download_path_var.get()
        
    def display_video_info(self, info: str):
        """Display video information in info text widget.
        
        Args:
            info: Formatted video info string
        """
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, info)
        self.info_text.config(state=tk.DISABLED)
        
    def update_progress(self, progress: str):
        """Update progress display.
        
        Args:
            progress: Progress message string
        """
        self.progress_var.set(progress)
        
    def update_status(self, status: str):
        """Update status (for main window status bar if needed).
        
        Args:
            status: Status message
        """
        # Could update main window status bar here if needed
        pass
        
    def log_message(self, message: str):
        """Add message to status log.
        
        Args:
            message: Log message to display
        """
        self.status_log.insert(tk.END, message + "\n")
        self.status_log.see(tk.END)  # Auto-scroll to bottom
        
    def clear_log(self):
        """Clear the status log."""
        self.status_log.delete("1.0", tk.END)
        
    def set_download_button_state(self, enabled: bool):
        """Enable or disable download button.
        
        Args:
            enabled: True to enable, False to disable
        """
        self.download_btn.config(state=tk.NORMAL if enabled else tk.DISABLED)
        
    def show_error(self, message: str):
        """Show error dialog.
        
        Args:
            message: Error message
        """
        messagebox.showerror("Download Error", message)
        
    def show_success(self, message: str):
        """Show success dialog.
        
        Args:
            message: Success message
        """
        messagebox.showinfo("Download Complete", message)
        
    def after_download(self, success: bool, message: str):
        """Called after download completes (from background thread).
        
        Args:
            success: Whether download succeeded
            message: Result message
        """
        # Schedule UI update in main thread
        self.after(0, lambda: self.controller.on_download_complete(success, message))
        
    # === BaseTab Abstract Method Implementations ===
    
    def get_content(self) -> str:
        """Return current URL content.
        
        Returns:
            Current YouTube URL
        """
        return self.url_var.get()
        
    def clear_all(self):
        """Clear all input fields and logs."""
        self.url_var.set("")
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        self.info_text.config(state=tk.DISABLED)
        self.status_log.delete("1.0", tk.END)
        self.progress_var.set("Ready")
        # Don't clear download path - user likely wants to reuse it
