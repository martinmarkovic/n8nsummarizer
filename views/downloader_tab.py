"""
Downloader Tab - Video downloader interface (v8.2)

Provides UI for downloading videos from multiple platforms:
- URL input field (supports YouTube, Twitter, Instagram, Facebook)
- Destination folder selection
- Resolution/quality chooser (including audio-only presets)
- PO Token input field (YouTube only)
- Instagram/Facebook cookie options (for private content)
- Download button
- Progress display
- Status log

Integrated with DownloaderController for download operations.

Created: 2026-02-15
Version: 8.2.0 - Added Facebook video download support
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from views.base_tab import BaseTab
from controllers.downloader_controller import DownloaderController
from utils.i18n import t


class DownloaderTab(BaseTab):
    """YouTube video downloader tab with full UI and controller integration."""

    def __init__(self, notebook):
        self.notebook = notebook
        
        # State variables
        self.url_var = tk.StringVar()
        self.download_path_var = tk.StringVar(value=t("downloader.status.no_folder"))
        self.resolution_var = tk.StringVar()
        self.po_token_var = tk.StringVar()
        self.progress_var = tk.StringVar(value=t("downloader.status.ready"))
        
        # Instagram/Facebook cookie settings
        self.instagram_cookie_file_var = tk.StringVar()
        self.instagram_cookie_browser_var = tk.StringVar()
        self.facebook_cookie_file_var = tk.StringVar()
        self.facebook_cookie_browser_var = tk.StringVar()
        
        # Controller will be initialized after UI setup
        self.controller = None
        
        super().__init__(notebook, "📥 Downloader")
        
        # Initialize controller after UI is ready
        self.controller = DownloaderController(self)
        
        # Populate resolution dropdown with all presets (video + audio)
        self._populate_resolution_dropdown()

    def _populate_resolution_dropdown(self):
        """Populate resolution dropdown with video quality and audio-only options."""
        if not self.controller:
            return
            
        # Get all available presets from controller/model
        all_resolutions = self.controller.get_available_resolutions()
        
        # Separate video and audio presets for display organization
        video_resolutions = [r for r in all_resolutions if not r.startswith("Audio Only")]
        audio_resolutions = [r for r in all_resolutions if r.startswith("Audio Only")]
        
        # Combine with separator for visual clarity
        display_values = video_resolutions.copy()
        if audio_resolutions:
            display_values.append("─────────────────")  # Visual separator
            display_values.extend(audio_resolutions)
        
        self.resolution_combo['values'] = display_values
        
        # Set default to first video option (Best Available)
        if video_resolutions:
            self.resolution_var.set(video_resolutions[0])
            self.controller.set_resolution(video_resolutions[0])

    def _setup_ui(self):
        """Build downloader UI with input controls and status display."""
        # Configure grid - 3 main rows
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Log area expands
        
        # === Row 0: Input Controls Frame ===
        controls_frame = ttk.LabelFrame(self, text=t("downloader.frame.settings"), padding=15)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        controls_frame.columnconfigure(1, weight=1)
        
        # URL Input
        ttk.Label(controls_frame, text=t("downloader.lbl.youtube_url")).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5
        )
        
        url_entry = ttk.Entry(controls_frame, textvariable=self.url_var)
        url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        url_entry.bind('<KeyRelease>', self._on_url_change)
        self._register_entry_context_menu(url_entry)
        
        # Info button
        info_btn = ttk.Button(
            controls_frame,
            text=t("downloader.btn.info"),
            width=8,
            command=self._fetch_video_info
        )
        info_btn.grid(row=0, column=2, padx=(5, 0), pady=5)

        # List Items button — enumerate a multi-item post (e.g. Instagram
        # carousel) so the user can pick which images/videos to download.
        list_btn = ttk.Button(
            controls_frame,
            text="List Items",
            width=10,
            command=self._list_items
        )
        list_btn.grid(row=0, column=3, padx=(5, 0), pady=5)
        
        # Destination Folder
        ttk.Label(controls_frame, text=t("downloader.lbl.save_to")).grid(
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
            text=t("downloader.btn.browse"),
            command=self._browse_folder
        )
        browse_btn.grid(row=1, column=2, padx=(5, 0), pady=5)
        
        # === Row 2: Quality Selection ===
        ttk.Label(controls_frame, text=t("downloader.lbl.quality")).grid(
            row=2, column=0, sticky=tk.W, padx=(0, 10), pady=5
        )
        
        # Resolution combobox - will be populated in __init__ after controller is ready
        # Now includes video quality presets AND audio-only presets (v6.6)
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
            text=t("downloader.btn.download"),
            command=self._start_download,
            width=12
        )
        self.download_btn.grid(row=2, column=2, padx=(5, 0), pady=5)
        
        # === Row 3: PO Token Input ===
        ttk.Label(controls_frame, text=t("downloader.lbl.po_token")).grid(
            row=3, column=0, sticky=tk.W, padx=(0, 10), pady=5
        )
        
        po_token_entry = ttk.Entry(
            controls_frame,
            textvariable=self.po_token_var,
            show="*"  # Hide token like password
        )
        po_token_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        po_token_entry.bind('<FocusOut>', self._on_po_token_change)
        po_token_entry.bind('<Return>', self._on_po_token_change)
        self._register_entry_context_menu(po_token_entry)
        
        # Help button for PO Token
        help_btn = ttk.Button(
            controls_frame,
            text=t("downloader.btn.help"),
            width=12,
        command=self._show_po_token_help
        )
        help_btn.grid(row=3, column=2, padx=(5, 0), pady=5)
        
        # === Row 4: Instagram Settings (initially hidden) ===
        self.instagram_frame = ttk.LabelFrame(controls_frame, text=t("downloader.frame.instagram"))
        self.instagram_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(20, 5))
        self.instagram_frame.columnconfigure(1, weight=1)
        self.instagram_frame.grid_remove()  # Hidden by default
        
        # Cookie File Path
        ttk.Label(self.instagram_frame, text=t("downloader.lbl.cookie_file")).grid(
            row=0, column=0, sticky=tk.W, padx=(10, 5), pady=5
        )
        
        self.cookie_file_var = tk.StringVar()
        cookie_file_entry = ttk.Entry(
            self.instagram_frame,
            textvariable=self.cookie_file_var
        )
        cookie_file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=5)
        cookie_file_entry.bind('<FocusOut>', self._on_cookie_file_change)
        self._register_entry_context_menu(cookie_file_entry)
        
        cookie_browse_btn = ttk.Button(
            self.instagram_frame,
            text=t("downloader.btn.browse"),
            width=10,
            command=self._browse_cookie_file
        )
        cookie_browse_btn.grid(row=0, column=2, padx=(0, 10), pady=5)
        
        # Cookie Browser
        ttk.Label(self.instagram_frame, text=t("downloader.lbl.cookie_browser")).grid(
            row=1, column=0, sticky=tk.W, padx=(10, 5), pady=5
        )
        
        self.cookie_browser_var = tk.StringVar()
        cookie_browser_combo = ttk.Combobox(
            self.instagram_frame,
            textvariable=self.cookie_browser_var,
            values=["", "chrome", "firefox", "edge", "safari", "chromium"],
            state="readonly",
            width=15
        )
        cookie_browser_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 5), pady=5)
        cookie_browser_combo.bind('<<ComboboxSelected>>', self._on_cookie_browser_change)
        
        # Help text
        help_label = ttk.Label(
            self.instagram_frame,
            text=t("downloader.lbl.cookie_help"),
            foreground="gray",
            font=("TkDefaultFont", 8)
        )
        help_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=10, pady=(0, 5))
        
        # Facebook Cookie Settings
        ttk.Label(self.instagram_frame, text=t("downloader.lbl.facebook_cookie_file")).grid(
            row=3, column=0, sticky=tk.W, padx=(10, 5), pady=5
        )
        
        facebook_cookie_file_entry = ttk.Entry(
            self.instagram_frame,
            textvariable=self.facebook_cookie_file_var
        )
        facebook_cookie_file_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=5)
        facebook_cookie_file_entry.bind('<FocusOut>', self._on_facebook_cookie_file_change)
        self._register_entry_context_menu(facebook_cookie_file_entry)
        
        facebook_cookie_browse_btn = ttk.Button(
            self.instagram_frame,
            text=t("downloader.btn.browse"),
            width=10,
            command=self._browse_facebook_cookie_file
        )
        facebook_cookie_browse_btn.grid(row=3, column=2, padx=(0, 10), pady=5)
        
        # Facebook Cookie Browser
        ttk.Label(self.instagram_frame, text=t("downloader.lbl.facebook_cookie_browser")).grid(
            row=4, column=0, sticky=tk.W, padx=(10, 5), pady=5
        )
        
        facebook_cookie_browser_combo = ttk.Combobox(
            self.instagram_frame,
            textvariable=self.facebook_cookie_browser_var,
            values=["", "chrome", "firefox", "edge", "safari", "chromium"],
            state="readonly",
            width=15
        )
        facebook_cookie_browser_combo.grid(row=4, column=1, sticky=tk.W, padx=(0, 5), pady=5)
        facebook_cookie_browser_combo.bind('<<ComboboxSelected>>', self._on_facebook_cookie_browser_change)
        
        # Facebook Help text
        facebook_help_label = ttk.Label(
            self.instagram_frame,
            text=t("downloader.lbl.facebook_cookie_help"),
            foreground="gray",
            font=("TkDefaultFont", 8)
        )
        facebook_help_label.grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=10, pady=(0, 5))
        
        # === Row 1: Video Info Display ===
        info_frame = ttk.LabelFrame(self, text=t("downloader.frame.video_info"), padding=10)
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=(0, 10))
        info_frame.columnconfigure(0, weight=1)
        
        self.info_text = tk.Text(info_frame, height=4, wrap=tk.WORD, state=tk.DISABLED)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # === Row 2: Progress & Log ===
        log_frame = ttk.LabelFrame(self, text=t("downloader.frame.progress"), padding=10)
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
        self._register_context_menu(self.status_log, [{"copy": True}])
        
        log_scroll = ttk.Scrollbar(log_frame, command=self.status_log.yview)
        log_scroll.grid(row=1, column=1, sticky=(tk.N, tk.S))
        self.status_log.configure(yscrollcommand=log_scroll.set)
        
    def populate_resolutions(self):
        """Populate resolution combobox after controller is initialized."""
        # This method exists for backward compatibility but is replaced by
        # _populate_resolution_dropdown() in v6.6
        self._populate_resolution_dropdown()
            
    def _browse_folder(self):
        """Open folder browser dialog for selecting download destination."""
        folder = filedialog.askdirectory(title=t("downloader.dialog.select_folder"))
        if folder:
            self.download_path_var.set(folder)
            if self.controller:
                self.controller.set_download_path(folder)
                self.log_message(t("downloader.log.folder_set").format(path=folder))
                
    def _on_resolution_change(self, event=None):
        """Handle resolution selection change."""
        resolution = self.resolution_var.get()
        
        # Skip if user selected the separator line
        if resolution.startswith("─"):
            # Revert to previous selection (first video option)
            if self.controller:
                resolutions = self.controller.get_available_resolutions()
                video_resolutions = [r for r in resolutions if not r.startswith("Audio Only")]
                if video_resolutions:
                    self.resolution_var.set(video_resolutions[0])
            return
            
        if self.controller:
            self.controller.set_resolution(resolution)
            self.log_message(t("downloader.log.quality_changed").format(resolution=resolution))
    
    def _on_po_token_change(self, event=None):
        """Handle PO Token input change."""
        token = self.po_token_var.get().strip()
        if self.controller:
            self.controller.set_po_token(token)
            if token:
                self.log_message(t("downloader.log.token_updated"))
            else:
                self.log_message(t("downloader.log.token_cleared"))
    
    def _show_po_token_help(self):
        """Show help dialog for PO Token."""
        help_text = t("downloader.help.po_token_body")
        messagebox.showinfo(t("downloader.help.po_token_title"), help_text)
            
    # Instagram cookie methods
    def _browse_cookie_file(self):
        """Browse for cookie file."""
        file_path = filedialog.askopenfilename(
            title=t("downloader.dialog.select_cookie"),
            filetypes=[(t("downloader.filetype.cookie"), "*.txt"), (t("downloader.filetype.all"), "*.*")]
        )
        if file_path:
            self.cookie_file_var.set(file_path)
            self.controller.set_instagram_cookie_file(file_path)
            self.log_message(t("downloader.log.instagram_cookie_file_set").format(path=file_path))

    def _browse_facebook_cookie_file(self):
        """Browse for Facebook cookie file."""
        file_path = filedialog.askopenfilename(
            title=t("downloader.dialog.select_facebook_cookie"),
            filetypes=[(t("downloader.filetype.cookie"), "*.txt"), (t("downloader.filetype.all"), "*.*")]
        )
        if file_path:
            self.facebook_cookie_file_var.set(file_path)
            self.controller.set_facebook_cookie_file(file_path)
            self.log_message(t("downloader.log.facebook_cookie_file_set").format(path=file_path))
    
    def _on_cookie_file_change(self, event=None):
        """Handle cookie file input change."""
        path = self.cookie_file_var.get().strip()
        if self.controller:
            self.controller.set_instagram_cookie_file(path)
            if path:
                self.log_message(t("downloader.log.instagram_cookie_file_set").format(path=path))
            else:
                self.log_message(t("downloader.log.instagram_cookie_file_cleared"))
    
    def _on_cookie_browser_change(self, event=None):
        """Handle cookie browser selection change."""
        browser = self.cookie_browser_var.get()
        if self.controller:
            self.controller.set_instagram_cookie_browser(browser)
            if browser:
                self.log_message(t("downloader.log.instagram_cookie_browser_set").format(browser=browser))
            else:
                self.log_message(t("downloader.log.instagram_cookie_browser_cleared"))

    def _on_facebook_cookie_file_change(self, event=None):
        """Handle Facebook cookie file input change."""
        path = self.facebook_cookie_file_var.get().strip()
        if self.controller:
            self.controller.set_facebook_cookie_file(path)
            if path:
                self.log_message(t("downloader.log.facebook_cookie_file_set").format(path=path))
            else:
                self.log_message(t("downloader.log.facebook_cookie_file_cleared"))

    def _on_facebook_cookie_browser_change(self, event=None):
        """Handle Facebook cookie browser selection change."""
        browser = self.facebook_cookie_browser_var.get()
        if self.controller:
            self.controller.set_facebook_cookie_browser(browser)
            if browser:
                self.log_message(t("downloader.log.facebook_cookie_browser_set").format(browser=browser))
            else:
                self.log_message(t("downloader.log.facebook_cookie_browser_cleared"))
    
    def _on_url_change(self, event=None):
        """Handle URL change - show Instagram settings if Instagram or Facebook URL detected."""
        url = self.url_var.get().strip()
        is_instagram = "instagram.com" in url.lower() or "instagr.am" in url.lower()
        is_facebook = "facebook.com" in url.lower() or "fb.watch" in url.lower() or "fb.com" in url.lower()
        
        if is_instagram or is_facebook:
            self.instagram_frame.grid()
        else:
            self.instagram_frame.grid_remove()
            
    def _fetch_video_info(self):
        """Fetch and display video information."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(t("downloader.msg.no_url_title"), t("downloader.msg.no_url_body"))
            return
            
        if self.controller:
            self.controller.fetch_video_info(url)
            
    def _start_download(self):
        """Initiate download process."""
        if self.controller:
            self.controller.start_download()

    def _list_items(self):
        """List the individual items behind the URL and open a pick dialog."""
        url = self.url_var.get().strip()
        if not url or url == "https://":
            self.show_error("Please enter a URL first.")
            return
        if not self.controller:
            return
        self.log_message(f"Listing items for: {url} …")
        # Disable the download button while we query
        self.set_download_button_state(False)
        self.controller.list_items(url, lambda ok, res, u=url: self._on_items_listed(u, ok, res))

    def _on_items_listed(self, url, success, result):
        """Handle the result of a list_items request (runs on UI thread)."""
        self.set_download_button_state(True)
        if not success:
            self.log_message(f"✗ Could not list items: {result}")
            self.show_error(f"Could not list items:\n{result}")
            return

        entries = result or []
        if not entries:
            self.show_error("No downloadable items were found for this URL.")
            return

        self.log_message(f"Found {len(entries)} item(s).")
        if len(entries) == 1:
            # Nothing to choose — just download it
            self.log_message("Only one item — downloading it directly.")
            self.controller.start_download_selected(url, [1])
            return

        self._open_selection_dialog(url, entries)

    def _open_selection_dialog(self, url, entries):
        """Show a checkbox list of items with a Download Selected action."""
        dialog = tk.Toplevel(self)
        dialog.title("Select items to download")
        dialog.geometry("520x420")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ttk.Label(
            dialog,
            text=f"{len(entries)} items found. Choose which to download:",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor=tk.W, padx=12, pady=(12, 6))

        # Scrollable checkbox area
        outer = ttk.Frame(dialog)
        outer.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        canvas = tk.Canvas(outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        item_vars = []
        for e in entries:
            var = tk.BooleanVar(value=True)  # default: download everything
            item_vars.append((e["index"], var))

            kind = e.get("kind", "unknown")
            icon = {"video": "🎬", "image": "🖼", "unknown": "❔"}.get(kind, "❔")
            dims = ""
            if e.get("width") and e.get("height"):
                dims = f" {e['width']}x{e['height']}"
            dur = ""
            if e.get("duration"):
                dur = f" {int(e['duration'])}s"
            ext = f" .{e['ext']}" if e.get("ext") else ""
            label = f"#{e['index']}  {icon} {kind}{dims}{dur}{ext}"

            ttk.Checkbutton(inner, text=label, variable=var).pack(anchor=tk.W, pady=1)

        # Select all / none helpers
        btns_top = ttk.Frame(dialog)
        btns_top.pack(fill=tk.X, padx=12)

        def _set_all(value):
            for _, v in item_vars:
                v.set(value)

        ttk.Button(btns_top, text="Select All", command=lambda: _set_all(True)).pack(side=tk.LEFT)
        ttk.Button(btns_top, text="Select None", command=lambda: _set_all(False)).pack(side=tk.LEFT, padx=(6, 0))

        # Action buttons
        actions = ttk.Frame(dialog)
        actions.pack(fill=tk.X, padx=12, pady=10)

        def _download_selected():
            chosen = [idx for idx, v in item_vars if v.get()]
            if not chosen:
                messagebox.showinfo("Nothing selected", "Select at least one item.", parent=dialog)
                return
            dialog.destroy()
            self.controller.start_download_selected(url, chosen)

        ttk.Button(actions, text="Download Selected", command=_download_selected).pack(side=tk.RIGHT)
        ttk.Button(actions, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=(0, 6))
            
    # === View Helper Methods (called by controller) ===
    
    def get_url(self) -> str:
        """Get current URL from input field.
        
        Returns:
            YouTube URL string
        """
        return self.url_var.get().strip()
    
    def get_po_token(self) -> str:
        """Get current PO Token from input field.
        
        Returns:
            PO Token string or empty string
        """
        return self.po_token_var.get().strip()
        
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
        messagebox.showerror(t("downloader.msg.error_title"), message)
        
    def show_success(self, message: str):
        """Show success dialog.
        
        Args:
            message: Success message
        """
        messagebox.showinfo(t("downloader.msg.complete_title"), message)
        
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
        self.progress_var.set(t("downloader.status.ready"))
        # Don't clear download path and PO token - user likely wants to reuse them
