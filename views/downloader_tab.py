"""
Downloader Tab - Video downloader interface (v9.0, CustomTkinter)

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
Version: 9.0.0 - Migrated from ttk to CustomTkinter with the card-based
    responsive layout used by the Summarizer tab. The public interface
    consumed by DownloaderController is unchanged.

Note on cookie variables: ``__init__`` used to create
``instagram_cookie_file_var`` / ``instagram_cookie_browser_var`` while the UI
and the controller used ``cookie_file_var`` / ``cookie_browser_var``, so the
first pair was dead state that never reflected anything on screen. The names
are now aliases for the same variables.
"""

import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from views.base_tab import CTkBaseTab
from views.ctk_compat import CTkSection, CTkCollapsibleSection
from controllers.downloader_controller import DownloaderController
from utils.i18n import t
from utils.logger import logger

# Shown in the quality dropdown between video and audio presets.
_SEPARATOR = "─────────────────"

_COOKIE_BROWSERS = ["", "chrome", "firefox", "edge", "safari", "chromium"]


class DownloaderTab(CTkBaseTab):
    """Video downloader tab with full UI and controller integration."""

    # Below this width the two top cards stack vertically.
    _STACK_BREAKPOINT = 1100

    def __init__(self, notebook):
        self.notebook = notebook

        # State variables
        self.url_var = tk.StringVar()
        self.download_path_var = tk.StringVar(value=t("downloader.status.no_folder"))
        self.resolution_var = tk.StringVar()
        self.po_token_var = tk.StringVar()
        self.progress_var = tk.StringVar(value=t("downloader.status.ready"))

        # Instagram / Facebook cookie settings.
        # cookie_* are the names the controller reads; the instagram_* names are
        # kept as aliases so any older reference still sees the same variable.
        self.cookie_file_var = tk.StringVar()
        self.cookie_browser_var = tk.StringVar()
        self.instagram_cookie_file_var = self.cookie_file_var
        self.instagram_cookie_browser_var = self.cookie_browser_var
        self.facebook_cookie_file_var = tk.StringVar()
        self.facebook_cookie_browser_var = tk.StringVar()

        # Controller will be initialized after UI setup
        self.controller = None

        super().__init__(notebook, "📥 Downloader")

        # Initialize controller after UI is ready
        self.controller = DownloaderController(self)

        # Populate resolution dropdown with all presets (video + audio)
        self._populate_resolution_dropdown()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """
        Layout:
            0  source card + destination/quality card (stacking when narrow)
            1  PO token (collapsible)
            2  Instagram / Facebook cookies (collapsible, auto-shown by URL)
            3  video info card
            4  progress + log   <- expanding region
            5  action bar
        """
        # Content goes in self.body (the scroll-when-needed area from
        # CTkBaseTab), not self, so short windows can still reach everything.
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(4, weight=1)

        self._stacked = False

        self._setup_top_row()
        self._setup_po_token_section()
        self._setup_cookies_section()
        self._setup_info_section()
        self._setup_log_section()
        self._setup_action_bar()

        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _event=None):
        self.after_idle(self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        """Stack the source and destination cards on narrow windows."""
        width = self.winfo_width()
        if width <= 1:
            width = self.winfo_toplevel().winfo_width()
        if width <= 1:
            return
        stacked = width < self._STACK_BREAKPOINT
        if stacked == self._stacked:
            return
        self._stacked = stacked

        if stacked:
            self._top_row.grid_columnconfigure(1, weight=0)
            self._dest_section.grid_configure(row=1, column=0, padx=0, pady=(10, 0))
        else:
            self._top_row.grid_columnconfigure(1, weight=1)
            self._dest_section.grid_configure(row=0, column=1, padx=(10, 0), pady=0)

    def _setup_top_row(self):
        self._top_row = ctk.CTkFrame(self.body, fg_color="transparent")
        self._top_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._top_row.grid_columnconfigure(0, weight=1)
        self._top_row.grid_columnconfigure(1, weight=1)

        self._setup_source_section()
        self._setup_destination_section()

    def _setup_source_section(self):
        """URL entry plus the inspect actions."""
        section = CTkSection(self._top_row, title=t("downloader.lbl.youtube_url"))
        section.grid(row=0, column=0, sticky="new")
        self._source_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        url_entry = ctk.CTkEntry(
            body, textvariable=self.url_var, height=34, placeholder_text="https://"
        )
        url_entry.grid(row=0, column=0, columnspan=2, sticky="ew")
        url_entry.bind('<KeyRelease>', self._on_url_change)
        self._register_entry_context_menu(url_entry)

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ctk.CTkButton(
            buttons, text=t("downloader.btn.info"), width=90, height=30,
            command=self._fetch_video_info,
        ).grid(row=0, column=0, padx=(0, 6))

        # Enumerate a multi-item post (e.g. Instagram carousel) so the user can
        # pick which images/videos to download.
        ctk.CTkButton(
            buttons, text="List Items", width=100, height=30,
            command=self._list_items,
        ).grid(row=0, column=1)

    def _setup_destination_section(self):
        """Destination folder and quality preset."""
        section = CTkSection(self._top_row, title=t("downloader.frame.settings"))
        section.grid(row=0, column=1, sticky="new", padx=(10, 0))
        self._dest_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body, text=t("downloader.lbl.save_to"), anchor="w",
            text_color=("gray40", "gray65"),
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ctk.CTkLabel(
            body,
            textvariable=self.download_path_var,
            anchor="w",
            fg_color=("gray88", "gray24"),
            corner_radius=8,
            height=32,
            padx=10,
        ).grid(row=1, column=0, sticky="ew", pady=(2, 0))

        ctk.CTkButton(
            body, text=t("downloader.btn.browse"), width=100, height=32,
            command=self._browse_folder,
        ).grid(row=1, column=1, padx=(8, 0), pady=(2, 0))

        ctk.CTkLabel(
            body, text=t("downloader.lbl.quality"), anchor="w",
            text_color=("gray40", "gray65"),
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # Readonly dropdown -> CTkOptionMenu. Values are filled in by
        # _populate_resolution_dropdown once the controller exists.
        self.resolution_combo = ctk.CTkOptionMenu(
            body, values=[""], command=self._on_resolution_change, height=32
        )
        self.resolution_combo.grid(row=3, column=0, sticky="ew", pady=(2, 0))

    def _setup_po_token_section(self):
        """YouTube PO token, folded away by default."""
        section = CTkCollapsibleSection(
            self.body, title=t("downloader.lbl.po_token"), expanded=False
        )
        section.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._po_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        po_token_entry = ctk.CTkEntry(
            body,
            textvariable=self.po_token_var,
            height=32,
            show="*",  # Hide token like a password
        )
        po_token_entry.grid(row=0, column=0, sticky="ew")
        po_token_entry.bind('<FocusOut>', self._on_po_token_change)
        po_token_entry.bind('<Return>', self._on_po_token_change)
        self._register_entry_context_menu(po_token_entry)

        ctk.CTkButton(
            body, text=t("downloader.btn.help"), width=110, height=32,
            command=self._show_po_token_help,
        ).grid(row=0, column=1, padx=(8, 0))

    def _setup_cookies_section(self):
        """
        Instagram / Facebook cookie settings.

        Collapsed and hidden until the URL looks like Instagram or Facebook,
        which is when these fields actually matter.
        """
        section = CTkCollapsibleSection(
            self.body, title=t("downloader.frame.instagram"), expanded=False
        )
        self._cookies_section = section
        # Kept under the old attribute name used by _on_url_change.
        self.instagram_frame = section
        body = section.body
        body.grid_columnconfigure(1, weight=1)

        row = 0
        # --- Instagram cookie file ---
        ctk.CTkLabel(
            body, text=t("downloader.lbl.cookie_file"), anchor="w",
            text_color=("gray40", "gray65"),
        ).grid(row=row, column=0, sticky="w", padx=(0, 8))

        cookie_file_entry = ctk.CTkEntry(
            body, textvariable=self.cookie_file_var, height=32
        )
        cookie_file_entry.grid(row=row, column=1, sticky="ew")
        cookie_file_entry.bind('<FocusOut>', self._on_cookie_file_change)
        self._register_entry_context_menu(cookie_file_entry)

        ctk.CTkButton(
            body, text=t("downloader.btn.browse"), width=90, height=32,
            command=self._browse_cookie_file,
        ).grid(row=row, column=2, padx=(8, 0))

        # --- Instagram cookie browser ---
        row += 1
        ctk.CTkLabel(
            body, text=t("downloader.lbl.cookie_browser"), anchor="w",
            text_color=("gray40", "gray65"),
        ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=(8, 0))

        self.cookie_browser_combo = ctk.CTkOptionMenu(
            body,
            variable=self.cookie_browser_var,
            values=_COOKIE_BROWSERS,
            command=self._on_cookie_browser_change,
            width=160,
            height=32,
        )
        self.cookie_browser_combo.grid(row=row, column=1, sticky="w", pady=(8, 0))

        row += 1
        ctk.CTkLabel(
            body, text=t("downloader.lbl.cookie_help"), anchor="w",
            justify="left", wraplength=700, text_color=("gray45", "gray60"),
        ).grid(row=row, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        # --- Facebook cookie file ---
        row += 1
        ctk.CTkLabel(
            body, text=t("downloader.lbl.facebook_cookie_file"), anchor="w",
            text_color=("gray40", "gray65"),
        ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=(12, 0))

        facebook_cookie_file_entry = ctk.CTkEntry(
            body, textvariable=self.facebook_cookie_file_var, height=32
        )
        facebook_cookie_file_entry.grid(row=row, column=1, sticky="ew", pady=(12, 0))
        facebook_cookie_file_entry.bind('<FocusOut>', self._on_facebook_cookie_file_change)
        self._register_entry_context_menu(facebook_cookie_file_entry)

        ctk.CTkButton(
            body, text=t("downloader.btn.browse"), width=90, height=32,
            command=self._browse_facebook_cookie_file,
        ).grid(row=row, column=2, padx=(8, 0), pady=(12, 0))

        # --- Facebook cookie browser ---
        row += 1
        ctk.CTkLabel(
            body, text=t("downloader.lbl.facebook_cookie_browser"), anchor="w",
            text_color=("gray40", "gray65"),
        ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=(8, 0))

        self.facebook_cookie_browser_combo = ctk.CTkOptionMenu(
            body,
            variable=self.facebook_cookie_browser_var,
            values=_COOKIE_BROWSERS,
            command=self._on_facebook_cookie_browser_change,
            width=160,
            height=32,
        )
        self.facebook_cookie_browser_combo.grid(
            row=row, column=1, sticky="w", pady=(8, 0)
        )

        row += 1
        ctk.CTkLabel(
            body, text=t("downloader.lbl.facebook_cookie_help"), anchor="w",
            justify="left", wraplength=700, text_color=("gray45", "gray60"),
        ).grid(row=row, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        # Hidden until an Instagram/Facebook URL is entered.
        section.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        section.grid_remove()

    def _setup_info_section(self):
        """Video info readout."""
        section = CTkSection(self.body, title=t("downloader.frame.video_info"), padding=10)
        section.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self._info_section = section
        section.body.grid_columnconfigure(0, weight=1)

        self.info_text = ctk.CTkTextbox(
            section.body,
            height=84,
            wrap="word",
            activate_scrollbars=True,
            corner_radius=8,
            font=("Segoe UI", 12),
            state="disabled",
        )
        self.info_text.grid(row=0, column=0, sticky="ew")

    def _setup_log_section(self):
        """Progress line and status log."""
        section = CTkSection(self.body, title=t("downloader.frame.progress"), padding=10)
        section.grid(row=4, column=0, sticky="nsew")
        self._log_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            body, textvariable=self.progress_var, anchor="w",
            text_color=("gray35", "gray70"),
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.status_log = ctk.CTkTextbox(
            body,
            wrap="word",
            font=("Cascadia Mono", 12),
            activate_scrollbars=True,
            corner_radius=8,
        )
        self.status_log.grid(row=1, column=0, sticky="nsew")
        self._register_context_menu(self.status_log, [{"copy": True}])

    def _setup_action_bar(self):
        """Primary download action."""
        action_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        action_frame.grid(row=5, column=0, sticky="ew", pady=(10, 0))
        action_frame.grid_columnconfigure(1, weight=1)

        self.download_btn = ctk.CTkButton(
            action_frame,
            text=t("downloader.btn.download"),
            command=self._start_download,
            width=170,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.download_btn.grid(row=0, column=0, padx=(0, 10))

        self.clear_btn = ctk.CTkButton(
            action_frame,
            text=t("common.clear"),
            command=self.clear_all,
            width=110,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
        )
        self.clear_btn.grid(row=0, column=1, sticky="w")

    # ------------------------------------------------------------------
    # Resolution dropdown
    # ------------------------------------------------------------------

    def _populate_resolution_dropdown(self):
        """Populate resolution dropdown with video quality and audio-only options."""
        if not self.controller:
            return

        all_resolutions = self.controller.get_available_resolutions()

        video_resolutions = [r for r in all_resolutions if not r.startswith("Audio Only")]
        audio_resolutions = [r for r in all_resolutions if r.startswith("Audio Only")]

        display_values = video_resolutions.copy()
        if audio_resolutions:
            display_values.append(_SEPARATOR)  # Visual separator
            display_values.extend(audio_resolutions)

        self.resolution_combo.configure(values=display_values or [""])

        # Set default to first video option (Best Available)
        if video_resolutions:
            self.resolution_var.set(video_resolutions[0])
            self.resolution_combo.set(video_resolutions[0])
            self.controller.set_resolution(video_resolutions[0])

    def populate_resolutions(self):
        """Backwards-compatible alias for _populate_resolution_dropdown()."""
        self._populate_resolution_dropdown()

    def _on_resolution_change(self, selected=None):
        """Handle resolution selection change."""
        resolution = selected if selected is not None else self.resolution_var.get()

        # Skip the separator line: revert to the first video option.
        if resolution.startswith("─"):
            if self.controller:
                resolutions = self.controller.get_available_resolutions()
                video_resolutions = [
                    r for r in resolutions if not r.startswith("Audio Only")
                ]
                if video_resolutions:
                    self.resolution_var.set(video_resolutions[0])
                    self.resolution_combo.set(video_resolutions[0])
            return

        self.resolution_var.set(resolution)
        if self.controller:
            self.controller.set_resolution(resolution)
            self.log_message(
                t("downloader.log.quality_changed").format(resolution=resolution)
            )

    # ------------------------------------------------------------------
    # Input handlers
    # ------------------------------------------------------------------

    def _browse_folder(self):
        """Open folder browser dialog for selecting download destination."""
        folder = filedialog.askdirectory(title=t("downloader.dialog.select_folder"))
        if folder:
            self.download_path_var.set(folder)
            if self.controller:
                self.controller.set_download_path(folder)
                self.log_message(t("downloader.log.folder_set").format(path=folder))

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
        messagebox.showinfo(
            t("downloader.help.po_token_title"), t("downloader.help.po_token_body")
        )

    def _browse_cookie_file(self):
        """Browse for cookie file."""
        file_path = filedialog.askopenfilename(
            title=t("downloader.dialog.select_cookie"),
            filetypes=[
                (t("downloader.filetype.cookie"), "*.txt"),
                (t("downloader.filetype.all"), "*.*"),
            ],
        )
        if file_path:
            self.cookie_file_var.set(file_path)
            if self.controller:
                self.controller.set_instagram_cookie_file(file_path)
            self.log_message(
                t("downloader.log.instagram_cookie_file_set").format(path=file_path)
            )

    def _browse_facebook_cookie_file(self):
        """Browse for Facebook cookie file."""
        file_path = filedialog.askopenfilename(
            title=t("downloader.dialog.select_facebook_cookie"),
            filetypes=[
                (t("downloader.filetype.cookie"), "*.txt"),
                (t("downloader.filetype.all"), "*.*"),
            ],
        )
        if file_path:
            self.facebook_cookie_file_var.set(file_path)
            if self.controller:
                self.controller.set_facebook_cookie_file(file_path)
            self.log_message(
                t("downloader.log.facebook_cookie_file_set").format(path=file_path)
            )

    def _on_cookie_file_change(self, event=None):
        """Handle cookie file input change."""
        path = self.cookie_file_var.get().strip()
        if self.controller:
            self.controller.set_instagram_cookie_file(path)
            if path:
                self.log_message(
                    t("downloader.log.instagram_cookie_file_set").format(path=path)
                )
            else:
                self.log_message(t("downloader.log.instagram_cookie_file_cleared"))

    def _on_cookie_browser_change(self, event=None):
        """Handle cookie browser selection change."""
        browser = self.cookie_browser_var.get()
        if self.controller:
            self.controller.set_instagram_cookie_browser(browser)
            if browser:
                self.log_message(
                    t("downloader.log.instagram_cookie_browser_set").format(browser=browser)
                )
            else:
                self.log_message(t("downloader.log.instagram_cookie_browser_cleared"))

    def _on_facebook_cookie_file_change(self, event=None):
        """Handle Facebook cookie file input change."""
        path = self.facebook_cookie_file_var.get().strip()
        if self.controller:
            self.controller.set_facebook_cookie_file(path)
            if path:
                self.log_message(
                    t("downloader.log.facebook_cookie_file_set").format(path=path)
                )
            else:
                self.log_message(t("downloader.log.facebook_cookie_file_cleared"))

    def _on_facebook_cookie_browser_change(self, event=None):
        """Handle Facebook cookie browser selection change."""
        browser = self.facebook_cookie_browser_var.get()
        if self.controller:
            self.controller.set_facebook_cookie_browser(browser)
            if browser:
                self.log_message(
                    t("downloader.log.facebook_cookie_browser_set").format(browser=browser)
                )
            else:
                self.log_message(t("downloader.log.facebook_cookie_browser_cleared"))

    def _on_url_change(self, event=None):
        """Reveal the cookie card when an Instagram or Facebook URL is entered."""
        url = self.url_var.get().strip().lower()
        is_instagram = "instagram.com" in url or "instagr.am" in url
        is_facebook = "facebook.com" in url or "fb.watch" in url or "fb.com" in url

        if is_instagram or is_facebook:
            self._cookies_section.grid()
            # Open it the first time it becomes relevant so the fields are seen.
            if not getattr(self, "_cookies_auto_expanded", False):
                self._cookies_section.set_expanded(True)
                self._cookies_auto_expanded = True
        else:
            self._cookies_section.grid_remove()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _fetch_video_info(self):
        """Fetch and display video information."""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(
                t("downloader.msg.no_url_title"), t("downloader.msg.no_url_body")
            )
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
        self.set_download_button_state(False)
        self.controller.list_items(
            url, lambda ok, res, u=url: self._on_items_listed(u, ok, res)
        )

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
            # Nothing to choose - just download it
            self.log_message("Only one item — downloading it directly.")
            self.controller.start_download_selected(url, [1])
            return

        self._open_selection_dialog(url, entries)

    def _open_selection_dialog(self, url, entries):
        """Show a checkbox list of items with a Download Selected action."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Select items to download")
        dialog.geometry("560x460")
        dialog.transient(self.winfo_toplevel())
        # Grab after the window is mapped, otherwise it can fail on Windows.
        dialog.after(100, dialog.grab_set)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            dialog,
            text=f"{len(entries)} items found. Choose which to download:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 6))

        # CTkScrollableFrame replaces the manual Canvas + Scrollbar wiring.
        scroll = ctk.CTkScrollableFrame(dialog)
        scroll.grid(row=1, column=0, sticky="nsew", padx=14)
        scroll.grid_columnconfigure(0, weight=1)

        item_vars = []
        for i, e in enumerate(entries):
            var = tk.BooleanVar(value=True)  # default: download everything
            item_vars.append((e["index"], var))

            kind = e.get("kind", "unknown")
            icon = {"video": "🎬", "image": "🖼", "unknown": "❔"}.get(kind, "❔")
            dims = ""
            if e.get("width") and e.get("height"):
                dims = f" {e['width']}x{e['height']}"
            dur = f" {int(e['duration'])}s" if e.get("duration") else ""
            ext = f" .{e['ext']}" if e.get("ext") else ""
            label = f"#{e['index']}  {icon} {kind}{dims}{dur}{ext}"

            ctk.CTkCheckBox(
                scroll, text=label, variable=var,
                checkbox_width=18, checkbox_height=18,
            ).grid(row=i, column=0, sticky="w", pady=2)

        # Select all / none helpers
        helpers = ctk.CTkFrame(dialog, fg_color="transparent")
        helpers.grid(row=2, column=0, sticky="ew", padx=14, pady=(8, 0))

        def _set_all(value):
            for _, v in item_vars:
                v.set(value)

        ctk.CTkButton(
            helpers, text="Select All", width=100, height=30,
            command=lambda: _set_all(True),
        ).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkButton(
            helpers, text="Select None", width=100, height=30,
            fg_color="transparent", border_width=1,
            border_color=("gray70", "gray40"), text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
            command=lambda: _set_all(False),
        ).grid(row=0, column=1)

        # Action buttons
        actions = ctk.CTkFrame(dialog, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=14, pady=12)
        actions.grid_columnconfigure(0, weight=1)

        def _download_selected():
            chosen = [idx for idx, v in item_vars if v.get()]
            if not chosen:
                messagebox.showinfo(
                    "Nothing selected", "Select at least one item.", parent=dialog
                )
                return
            dialog.destroy()
            self.controller.start_download_selected(url, chosen)

        ctk.CTkButton(
            actions, text="Download Selected", width=160, height=34,
            command=_download_selected,
        ).grid(row=0, column=2)
        ctk.CTkButton(
            actions, text="Cancel", width=100, height=34,
            fg_color="transparent", border_width=1,
            border_color=("gray70", "gray40"), text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
            command=dialog.destroy,
        ).grid(row=0, column=1, padx=(0, 8))

    # ------------------------------------------------------------------
    # View Helper Methods (called by controller)
    # ------------------------------------------------------------------

    def get_url(self) -> str:
        """Get current URL from input field."""
        return self.url_var.get().strip()

    def get_po_token(self) -> str:
        """Get current PO Token from input field."""
        return self.po_token_var.get().strip()

    def get_download_path(self) -> str:
        """Get current download path."""
        return self.download_path_var.get()

    def display_video_info(self, info: str):
        """Display video information in the info text widget."""
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert(tk.END, info)
        self.info_text.configure(state="disabled")

    def update_progress(self, progress: str):
        """Update progress display."""
        self.progress_var.set(progress)

    def update_status(self, status: str):
        """Update status (no-op; the main window owns the status bar)."""
        pass

    def log_message(self, message: str):
        """Add message to status log."""
        self.status_log.insert(tk.END, message + "\n")
        self.status_log.see(tk.END)  # Auto-scroll to bottom

    def clear_log(self):
        """Clear the status log."""
        self.status_log.delete("1.0", tk.END)

    def set_download_button_state(self, enabled: bool):
        """Enable or disable download button."""
        self.download_btn.configure(state="normal" if enabled else "disabled")

    def show_error(self, message: str):
        """Show error dialog."""
        logger.error(f"[{self.tab_name}] {message}")
        messagebox.showerror(t("downloader.msg.error_title"), message)

    def show_success(self, message: str):
        """Show success dialog."""
        messagebox.showinfo(t("downloader.msg.complete_title"), message)

    def after_download(self, success: bool, message: str):
        """Called after download completes (from background thread)."""
        # Schedule UI update in main thread
        self.after(0, lambda: self.controller.on_download_complete(success, message))

    # ------------------------------------------------------------------
    # CTkBaseTab abstract method implementations
    # ------------------------------------------------------------------

    def get_content(self) -> str:
        """Return current URL content."""
        return self.url_var.get()

    def clear_all(self):
        """Clear all input fields and logs."""
        self.url_var.set("")
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.configure(state="disabled")
        self.status_log.delete("1.0", tk.END)
        self.progress_var.set(t("downloader.status.ready"))
        # Don't clear download path and PO token - user likely wants to reuse them

    # ------------------------------------------------------------------
    # Theming hook used by MainWindow
    # ------------------------------------------------------------------

    def apply_font_size(self, size: int):
        """
        Apply the app-wide font size to this tab's text areas.

        Labels, controls and section headings are scaled centrally by
        :func:`views.ctk_theme.apply_font_scale`.
        """
        from views.ctk_theme import font_sizes
        sizes = font_sizes(size)
        self.status_log.configure(font=("Cascadia Mono", sizes["mono"]))
        self.info_text.configure(font=("Segoe UI", sizes["label"]))
