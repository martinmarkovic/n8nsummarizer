"""
Main Window GUI v6.3 - Settings Persistence

This window manages:
- Header (title + font size + theme toggle)
- Tab container (notebook)
- Tab initialization (7 tabs total)
- Theme management
- Font size management with .env persistence
- Status bar
- Tab selection persistence (remembers last active tab)

All tab-specific UI code moved to individual tab files.
Easy to add new tabs by creating new tab classes and initializing them here.

v6.3 Changes:
- Added tab persistence (remembers last active tab across sessions)
- Integrated SettingsManager for persistent preferences

v6.2 Changes:
- Fixed quality selection in Downloader tab (now properly downloads 720p/1080p)

v6.1 Changes:
- Added 7th tab: Downloader (YouTube video download functionality)
- Updated version references from v6.0 to v6.1

v6.0 Changes:
- Added 6th tab: Translation (UI placeholder for future translation workflows)
- Updated version references from v5.0 to v6.0

Created: 2025-11-30
Version: 6.3
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from dotenv import load_dotenv
import os
import subprocess
import threading

from config import (
    APP_TITLE,
    APP_WIDTH,
    APP_HEIGHT,
    DEFAULT_THEME,
    DARK_THEME,
    LIGHT_THEME,
)
from utils.logger import logger
from utils.settings_manager import SettingsManager
from utils.prompt_manager import PromptManager
from utils.version import get_titled_version
from views.summarizer_tab import SummarizerTab  # NEW v9.3
from views.transcriber_tab import TranscriberTab
from views.bulk_summarizer_tab import BulkSummarizerTab
from views.bulk_transcriber_tab import BulkTranscriberTab
from views.translation_tab import TranslationTab
from views.downloader_tab import DownloaderTab
from views.video_subtitler_tab import VideoSubtitlerTab

# Load environment variables
load_dotenv()


class MainWindow:
    """
    Main GUI window with tabbed interface.

    Manages:
    - Header and navigation
    - Font size control with .env persistence
    - Tab container (notebook)
    - Tab initialization
    - Theme management
    - Status bar
    - Tab selection persistence

        Tab order (v9.5):
        1. Summarizer (index 0)
        2. Transcriber (index 1)
        3. Bulk Summarizer (index 2)
        4. Bulk Transcriber (index 3)
        5. Translation (index 4)
        6. Downloader (index 5)
        7. Video Subtitler (index 6)
    """

    # Font sizes (allowed range for validation; user can type any value in [MIN, MAX])
    FONT_MIN = 8
    FONT_MAX = 20
    FONT_SIZES = [8, 10, 12, 14, 16, 18, 20]  # kept for legacy load validation
    DEFAULT_FONT_SIZE = 10
    ENV_KEY_FONT_SIZE = "APP_FONT_SIZE"
    ENV_FILE = ".env"

    # Hardcoded fallback paths (shown as placeholder/default in Settings)
    DEFAULT_TRANSCRIBE_PATH = "F:/Python scripts/n8nsummarizer/myenv/Scripts/transcribe-anything.exe"
    DEFAULT_FFMPEG_PATH = "ffmpeg"

    def __init__(self, root, settings_manager: SettingsManager):
        """
        Initialize main window.

        Args:
            root: Tkinter root window
            settings_manager: SettingsManager instance for persistent preferences
        """
        self.root = root
        # App title with version derived from the current git branch, e.g. "Media SwissKnife (v13.5.2)"
        self.app_title_display = get_titled_version(APP_TITLE)
        self.root.title(self.app_title_display)
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.resizable(True, True)

        # Store settings manager
        self.settings = settings_manager

        # Theme state - load from .env or use default
        self.current_theme = self._load_theme_from_env()
        # Start with the base palette; _rebuild_theme_colors will overlay any saved
        # custom colors from .env on top of it.
        self.theme_colors = LIGHT_THEME if self.current_theme == "light" else DARK_THEME

        # Font size state - load from .env if available
        self.current_font_size = self._load_font_size_from_env()

        # Theme callback
        self.on_theme_toggle = None

        # Setup UI
        self._setup_ui()

        # Sync path overrides from .env into os.environ so cli_runner sees them
        self._sync_path_env_vars()

        # Overlay any saved custom colors before the first paint
        self._rebuild_theme_colors()

        # Apply theme first (sets the clam theme + colors), then font size so the
        # font configuration wins and isn't reset by the theme's own font settings.
        self._apply_theme()
        self._apply_font_size()

        # Restore last active tab AFTER all tabs are created
        self._restore_last_active_tab()

        # Bind tab change event to save preference
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        logger.info(
            f"MainWindow initialized (v6.3 - {self.current_theme} theme, {self.current_font_size}px font)"
        )

    def _restore_last_active_tab(self):
        """
        Restore the last active tab from settings.

        Called after all tabs are initialized.
        """
        try:
            last_tab = self.settings.get_last_active_tab()
            # Validate tab index (0-6 for 7 tabs)
            if 0 <= last_tab <= 6:
                self.notebook.select(last_tab)
                logger.info(f"Restored last active tab: {last_tab}")
            else:
                logger.warning(f"Invalid tab index {last_tab}, using default (0)")
                self.notebook.select(0)
        except Exception as e:
            logger.error(f"Error restoring last active tab: {str(e)}")
            self.notebook.select(0)

    def _on_tab_changed(self, event=None):
        """
        Handle tab change event - save current tab to settings.

        Args:
            event: Tkinter event (unused)
        """
        try:
            current_tab = self.notebook.index(self.notebook.select())
            self.settings.set_last_active_tab(current_tab)
            logger.debug(f"Saved current tab to settings: {current_tab}")
        except Exception as e:
            logger.error(f"Error saving current tab: {str(e)}")

    def _load_font_size_from_env(self) -> int:
        """
        Load font size preference from .env file.

        Returns:
            Font size in pixels. Returns DEFAULT_FONT_SIZE if not found or invalid.
        """
        try:
            env_font_size = os.getenv(self.ENV_KEY_FONT_SIZE)
            if env_font_size:
                font_size = int(env_font_size)
                # Clamp to allowed range
                if self.FONT_MIN <= font_size <= self.FONT_MAX:
                    logger.info(f"Loaded font size from .env: {font_size}px")
                    return font_size
                else:
                    clamped = max(self.FONT_MIN, min(self.FONT_MAX, font_size))
                    logger.warning(
                        f"Font size {font_size} out of range, clamping to {clamped}"
                    )
                    return clamped
            else:
                logger.debug("No font size preference found in .env, using default")
                return self.DEFAULT_FONT_SIZE
        except (ValueError, TypeError) as e:
            logger.warning(
                f"Error parsing font size from .env: {str(e)}, using default"
            )
            return self.DEFAULT_FONT_SIZE

    def _save_font_size_to_env(self, font_size: int) -> bool:
        """Save font size preference to .env via SettingsManager (preserves comments)."""
        try:
            self.settings.set(self.ENV_KEY_FONT_SIZE, str(font_size))
            logger.info(f"Saved font size preference to .env: {font_size}px")
            return True
        except Exception as e:
            logger.error(f"Error saving font size to .env: {str(e)}")
            return False

    def _setup_ui(self):
        """
        Setup main window UI.

        Creates:
        - Main frame
        - Header (title + font size + theme toggle)
        - Tab notebook with all tabs (7 total)
        - Status bar
        """
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Tab area expands

        # Header with Title + Font Size + Theme Toggle
        self._setup_header(main_frame)

        # Notebook with tabs
        self._setup_tabs(main_frame)

        # Status bar
        self._setup_status_bar(main_frame)

    def _setup_header(self, parent):
        """
        Setup header with title, font size controls, theme toggle, and settings button.

        Args:
            parent: Parent frame
        """
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        header_frame.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(
            header_frame, text=self.app_title_display, font=("Segoe UI", 14, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky=tk.W)

        # Controls on the right side
        controls_frame = ttk.Frame(header_frame)
        controls_frame.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))

        ttk.Label(controls_frame, text="Font:").pack(side=tk.LEFT, padx=(0, 4))

        # Decrease button — steps by 2 (original behaviour)
        self.font_decrease_btn = ttk.Button(
            controls_frame, text="🔍-", width=3, command=self._decrease_font_size
        )
        self.font_decrease_btn.pack(side=tk.LEFT, padx=(0, 2))

        # Font size entry — type any integer in [FONT_MIN, FONT_MAX] for precise
        # control (not restricted to the +2/-2 steps of the buttons). A plain Entry
        # is used (not a Spinbox) so there are no redundant arrow controls.
        vcmd = (self.root.register(self._validate_font_entry), "%P")
        self.font_size_var = tk.StringVar(value=str(self.current_font_size))
        self.font_entry = ttk.Entry(
            controls_frame,
            textvariable=self.font_size_var,
            width=4,
            justify=tk.CENTER,
            validate="key",
            validatecommand=vcmd,
        )
        self.font_entry.pack(side=tk.LEFT, padx=(0, 2))
        # Commit typed value on Enter or focus-out
        self.font_entry.bind("<Return>",   lambda _e: self._on_font_entry_commit())
        self.font_entry.bind("<FocusOut>", lambda _e: self._on_font_entry_commit())

        ttk.Label(controls_frame, text="px").pack(side=tk.LEFT, padx=(0, 2))

        # Increase button — steps by 2 (original behaviour)
        self.font_increase_btn = ttk.Button(
            controls_frame, text="🔍+", width=3, command=self._increase_font_size
        )
        self.font_increase_btn.pack(side=tk.LEFT, padx=(2, 12))

        # Theme toggle button
        self.theme_btn = ttk.Button(
            controls_frame,
            text="🌙 Dark Mode" if self.current_theme == "light" else "☀️ Light Mode",
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Settings button (replaces old cogwheel → deps manager direct link)
        self.settings_btn = ttk.Button(
            controls_frame, text="⚙ Settings", command=self._open_settings
        )
        self.settings_btn.pack(side=tk.LEFT)

    def _setup_tabs(self, parent):
        """
        Setup tab notebook with all tabs.

        Tab order (v8.1):
        0. File Summarizer
        1. YouTube Summarization
        2. Transcriber
        3. Bulk Summarizer
        4. Bulk Transcriber
        5. Translation
        6. Downloader
        7. Video Subtitler

        Args:
            parent: Parent frame
        """
        # Create notebook (tab container)
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(
            row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10)
        )

        # Initialize PromptManager
        self.prompt_manager = PromptManager()

        # Tab 0: Summarizer (NEW v9.3 - replaces File and YouTube tabs)
        self.summarizer_tab = SummarizerTab(self.notebook, prompt_manager=self.prompt_manager)
        self.notebook.add(self.summarizer_tab, text="📝 Summarizer")
        
        # Tab 1: Transcriber
        self.transcriber_tab = TranscriberTab(self.notebook, self.settings)
        self.notebook.add(self.transcriber_tab, text="🗡 Transcriber")

        # Tab 1: Bulk Summarizer
        self.bulk_summarizer_tab = BulkSummarizerTab(self.notebook)
        self.notebook.add(self.bulk_summarizer_tab, text="📦 Bulk Summarizer")

        # Tab 2: Bulk Transcriber
        self.bulk_transcriber_tab = BulkTranscriberTab(self.notebook)
        self.notebook.add(self.bulk_transcriber_tab, text="🎬 Bulk Transcriber")

        # Tab 3: Translation
        self.translation_tab = TranslationTab(self.notebook)
        self.notebook.add(self.translation_tab, text="🌐 Translation")

        # Tab 4: Downloader
        self.downloader_tab = DownloaderTab(self.notebook)
        self.notebook.add(self.downloader_tab, text="📥 Downloader")

        # Tab 5: Video Subtitler
        self.video_subtitler_tab = VideoSubtitlerTab(self.notebook)
        self.notebook.add(self.video_subtitler_tab, text="🎞 Video Subtitler")

        logger.info("All tabs initialized (v9.5 - Removed File and YouTube Summarizer tabs)")

    def _setup_status_bar(self, parent):
        """
        Setup status bar and progress indicator.

        Args:
            parent: Parent frame
        """
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(
            status_frame, textvariable=self.status_var, relief=tk.SUNKEN
        )
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))

    def _apply_theme(self):
        """
        Apply current theme colors to all widgets.
        """
        style = ttk.Style()
        style.theme_use("clam")

        colors = self.theme_colors

        # Base style ('.') — every ttk widget inherits from this. Setting it here
        # guarantees any element not explicitly styled below (e.g. the header bar)
        # still gets the theme background/foreground instead of staying light.
        style.configure(
            ".",
            background=colors["bg_primary"],
            foreground=colors["text_primary"],
            fieldbackground=colors["bg_secondary"],
            bordercolor=colors["border"],
            troughcolor=colors["bg_secondary"],
        )

        # Configure widget styles
        style.configure(
            "TLabel", background=colors["bg_primary"], foreground=colors["text_primary"]
        )
        style.configure("TFrame", background=colors["bg_primary"])
        style.configure(
            "TLabelFrame", background=colors["bg_primary"], bordercolor=colors["border"]
        )
        style.configure(
            "TLabelFrame.Label",
            background=colors["bg_primary"],
            foreground=colors["accent"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "TButton",
            font=("Segoe UI", 10),
            background=colors["button_bg"],
            foreground=colors["text_primary"],
        )
        style.map("TButton", background=[("active", colors["button_hover"])])
        style.configure(
            "TCheckbutton",
            background=colors["bg_primary"],
            foreground=colors["text_primary"],
        )
        style.configure(
            "TRadiobutton",
            background=colors["bg_primary"],
            foreground=colors["text_primary"],
        )
        style.configure(
            "TEntry",
            fieldbackground=colors["bg_secondary"],
            foreground=colors["text_primary"],
        )
        style.configure("TNotebook", background=colors["bg_primary"])
        style.configure(
            "TNotebook.Tab",
            background=colors["bg_secondary"],
            foreground=colors["text_primary"],
        )
        style.map("TNotebook.Tab", background=[("selected", colors["bg_primary"])])

        # Combobox (readonly dropdowns) — otherwise they stay light in dark mode
        style.configure(
            "TCombobox",
            fieldbackground=colors["bg_secondary"],
            background=colors["button_bg"],
            foreground=colors["text_primary"],
            arrowcolor=colors["text_primary"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", colors["bg_secondary"])],
            foreground=[("readonly", colors["text_primary"])],
        )
        # Dropdown list colors (the popdown listbox is a separate Tk option)
        self.root.option_add("*TCombobox*Listbox.background", colors["bg_secondary"])
        self.root.option_add("*TCombobox*Listbox.foreground", colors["text_primary"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", colors["button_hover"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", colors["text_primary"])

        # Spinbox / Scale share the frame background
        style.configure("TSpinbox", fieldbackground=colors["bg_secondary"], foreground=colors["text_primary"])
        style.configure("Horizontal.TScale", background=colors["bg_primary"])

        # Apply to root
        self.root.configure(bg=colors["bg_primary"])

        # Update text widget colors in tabs
        text_bg = colors["bg_secondary"]
        text_fg = colors["text_primary"]

        # Summarizer tab
        if hasattr(self, "summarizer_tab"):
            self.summarizer_tab.content_text.configure(
                bg=text_bg, fg=text_fg, insertbackground=text_fg
            )
            self.summarizer_tab.response_text.configure(
                bg=text_bg, fg=text_fg, insertbackground=text_fg
            )
            self.summarizer_tab.info_text.configure(bg=text_bg, fg=text_fg)

        # Transcriber tab
        if hasattr(self, "transcriber_tab"):
            self.transcriber_tab.transcript_text.configure(
                bg=text_bg, fg=text_fg, insertbackground=text_fg
            )

        # Bulk Summarizer tab
        if hasattr(self, "bulk_summarizer_tab"):
            self.bulk_summarizer_tab.status_log.configure(
                bg=text_bg, fg=text_fg, insertbackground=text_fg
            )

        # Bulk Transcriber tab
        if hasattr(self, "bulk_transcriber_tab"):
            self.bulk_transcriber_tab.status_log.configure(
                bg=text_bg, fg=text_fg, insertbackground=text_fg
            )

        # Translation tab
        if hasattr(self, "translation_tab"):
            self.translation_tab.source_text.configure(
                bg=text_bg, fg=text_fg, insertbackground=text_fg
            )
            self.translation_tab.target_text.configure(
                bg=text_bg, fg=text_fg, insertbackground=text_fg
            )

        # Downloader tab
        if hasattr(self, "downloader_tab"):
            self.downloader_tab.status_log.configure(
                bg=text_bg, fg=text_fg, insertbackground=text_fg
            )

        # Video Subtitler tab
        if hasattr(self, "video_subtitler_tab"):
            self.video_subtitler_tab.srt_text.configure(
                bg=text_bg, fg=text_fg, insertbackground=text_fg
            )
            if hasattr(self.video_subtitler_tab, "translated_srt_text"):
                self.video_subtitler_tab.translated_srt_text.configure(
                    bg=text_bg, fg=text_fg, insertbackground=text_fg
                )
            if hasattr(self.video_subtitler_tab, "ffmpeg_status_var"):
                # FFmpeg status label uses the same colors as other status labels
                pass  # The label automatically inherits from theme configuration

        # Catch-all: recolor every tk.Text / ScrolledText widget across all tabs.
        # This covers any widget not explicitly listed above (e.g. the prompt editor).
        if hasattr(self, "notebook"):
            self._recolor_text_widgets(self.notebook, text_bg, text_fg)

        # Title label
        if hasattr(self, "title_label"):
            self.title_label.configure(foreground=colors["text_primary"])

        # Reassert font sizes — _apply_theme sets some hardcoded fonts, so re-run
        # the font sizing to keep the user's chosen size after a theme toggle.
        if hasattr(self, "notebook"):
            self._apply_font_size()

        logger.info(f"Applied {self.current_theme} theme")

    def _recolor_text_widgets(self, parent, bg, fg):
        """
        Recursively recolor every tk.Text / ScrolledText widget under `parent`.

        ttk widgets are styled via ttk.Style, but classic tk.Text widgets need
        their bg/fg set explicitly or they stay light ("cream") in dark mode.
        """
        for child in parent.winfo_children():
            try:
                if isinstance(child, tk.Text):  # ScrolledText subclasses tk.Text
                    child.configure(bg=bg, fg=fg, insertbackground=fg)
            except tk.TclError:
                pass
            # Recurse into containers
            if child.winfo_children():
                self._recolor_text_widgets(child, bg, fg)

    def _toggle_theme(self):
        """
        Toggle between dark and light mode.

        Choosing a mode is a full reset: any custom colors (background / text /
        accent) are cleared so the pure light or dark palette applies to
        everything, not just the font.
        """
        self.current_theme = "dark" if self.current_theme == "light" else "light"

        # Clear saved custom colors so the base palette fully takes over
        for key in ("APP_COLOR_BG", "APP_COLOR_TEXT", "APP_COLOR_ACCENT"):
            self.settings.set(key, "")

        # Use the pure base palette for the chosen mode
        self.theme_colors = DARK_THEME if self.current_theme == "dark" else LIGHT_THEME

        # Update button text
        self.theme_btn.configure(
            text="🌙 Dark Mode" if self.current_theme == "light" else "☀️ Light Mode"
        )

        # Apply new theme
        self._apply_theme()

        # Save theme preference to .env
        self._save_theme_to_env(self.current_theme)

        # Call callback if set
        if self.on_theme_toggle:
            self.on_theme_toggle(self.current_theme)

    # ------------------------------------------------------------------
    # Settings dialog
    # ------------------------------------------------------------------

    def _open_settings(self):
        """Open the Settings popup window.

        Sections:
        - Appearance  — custom theme colors (bg + text) and font size
        - Paths       — FFmpeg and transcribe-anything paths
        - Tools       — shortcut to the Dependencies Manager
        """
        # Prevent multiple instances
        if (
            hasattr(self, "_settings_window")
            and self._settings_window
            and self._settings_window.winfo_exists()
        ):
            self._settings_window.lift()
            return

        win = tk.Toplevel(self.root)
        win.title("⚙ Settings")
        win.geometry("560x540")
        win.minsize(420, 300)
        win.resizable(True, True)
        win.grab_set()
        self._settings_window = win

        # Apply current theme colors to the popup
        colors = self.theme_colors
        win.configure(bg=colors["bg_primary"])

        # --- Pinned action-button bar at the bottom (always visible) ---
        btn_bar = ttk.Frame(win, padding=(14, 10))
        btn_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Scrollable body (canvas + vertical scrollbar) ---
        body = ttk.Frame(win)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(body, highlightthickness=0, bg=colors["bg_primary"])
        vscroll = ttk.Scrollbar(body, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        outer = ttk.Frame(canvas, padding=14)
        outer_id = canvas.create_window((0, 0), window=outer, anchor="nw")

        # Keep the scroll region in sync with the content size
        def _on_outer_config(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        outer.bind("<Configure>", _on_outer_config)

        # Stretch the inner frame to the canvas width so content fills horizontally
        def _on_canvas_config(event):
            canvas.itemconfigure(outer_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_config)

        # Mouse-wheel scrolling (safe: the dialog is modal via grab_set)
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        win.bind("<MouseWheel>", _on_mousewheel)

        ttk.Label(outer, text="Settings", font=("Segoe UI", 13, "bold")).pack(
            anchor=tk.W, pady=(0, 12)
        )

        # ── Appearance ────────────────────────────────────────────────
        appear_frame = ttk.LabelFrame(outer, text="Appearance", padding=10)
        appear_frame.pack(fill=tk.X, pady=(0, 10))

        # --- Theme colors ---
        color_row = ttk.Frame(appear_frame)
        color_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(color_row, text="Theme colors  (leave blank to use default light/dark palette):",
                  wraplength=480).pack(anchor=tk.W, pady=(0, 6))

        # Load currently saved custom colors (may be empty = "use default")
        saved_bg     = self.settings.get("APP_COLOR_BG", "")
        saved_text   = self.settings.get("APP_COLOR_TEXT", "")
        saved_accent = self.settings.get("APP_COLOR_ACCENT", "")

        # Background color
        bg_row = ttk.Frame(appear_frame)
        bg_row.pack(fill=tk.X, pady=2)
        ttk.Label(bg_row, text="Background:", width=14, anchor=tk.W).pack(side=tk.LEFT)
        bg_var = tk.StringVar(value=saved_bg)
        bg_entry = ttk.Entry(bg_row, textvariable=bg_var, width=10)
        bg_entry.pack(side=tk.LEFT, padx=(0, 6))
        bg_preview = tk.Label(
            bg_row,
            bg=saved_bg if saved_bg else colors["bg_primary"],
            width=3,
            relief=tk.SOLID,
            borderwidth=1,
        )
        bg_preview.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            bg_row,
            text="Pick…",
            command=lambda: self._pick_color(bg_var, bg_preview, "Background color"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            bg_row,
            text="Clear",
            command=lambda: self._clear_color(bg_var, bg_preview, colors["bg_primary"]),
        ).pack(side=tk.LEFT)

        # Text / foreground color
        text_row = ttk.Frame(appear_frame)
        text_row.pack(fill=tk.X, pady=2)
        ttk.Label(text_row, text="Text:", width=14, anchor=tk.W).pack(side=tk.LEFT)
        text_var = tk.StringVar(value=saved_text)
        text_entry = ttk.Entry(text_row, textvariable=text_var, width=10)
        text_entry.pack(side=tk.LEFT, padx=(0, 6))
        text_preview = tk.Label(
            text_row,
            bg=saved_text if saved_text else colors["text_primary"],
            width=3,
            relief=tk.SOLID,
            borderwidth=1,
        )
        text_preview.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            text_row,
            text="Pick…",
            command=lambda: self._pick_color(text_var, text_preview, "Text color"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            text_row,
            text="Clear",
            command=lambda: self._clear_color(text_var, text_preview, colors["text_primary"]),
        ).pack(side=tk.LEFT)

        # Accent color — borders, buttons, section labels, secondary text
        accent_row = ttk.Frame(appear_frame)
        accent_row.pack(fill=tk.X, pady=2)
        ttk.Label(accent_row, text="Accent:", width=14, anchor=tk.W).pack(side=tk.LEFT)
        accent_var = tk.StringVar(value=saved_accent)
        accent_entry = ttk.Entry(accent_row, textvariable=accent_var, width=10)
        accent_entry.pack(side=tk.LEFT, padx=(0, 6))
        accent_preview = tk.Label(
            accent_row,
            bg=saved_accent if saved_accent else colors["accent"],
            width=3,
            relief=tk.SOLID,
            borderwidth=1,
        )
        accent_preview.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            accent_row,
            text="Pick…",
            command=lambda: self._pick_color(accent_var, accent_preview, "Accent color"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            accent_row,
            text="Clear",
            command=lambda: self._clear_color(accent_var, accent_preview, colors["accent"]),
        ).pack(side=tk.LEFT)

        ttk.Label(
            appear_frame,
            text="  Accent tints borders, buttons, tabs and section labels.",
            foreground=colors.get("text_secondary", "gray"),
        ).pack(anchor=tk.W, pady=(2, 0))

        # Live-sync preview squares when user types a hex value manually
        def _sync_preview(var, preview):
            val = var.get().strip()
            if val and (len(val) in (4, 7)) and val.startswith("#"):
                try:
                    preview.configure(bg=val)
                except tk.TclError:
                    pass

        bg_var.trace_add("write", lambda *_: _sync_preview(bg_var, bg_preview))
        text_var.trace_add("write", lambda *_: _sync_preview(text_var, text_preview))
        accent_var.trace_add("write", lambda *_: _sync_preview(accent_var, accent_preview))

        # --- Font size ---
        font_row = ttk.Frame(appear_frame)
        font_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(font_row, text="Font size:", width=14, anchor=tk.W).pack(side=tk.LEFT)
        ttk.Label(
            font_row,
            text=f"(currently {self.current_font_size}px — change via the header controls)",
            foreground=colors["text_secondary"] if "text_secondary" in colors else "gray",
        ).pack(side=tk.LEFT)

        # ── Paths ─────────────────────────────────────────────────────
        paths_frame = ttk.LabelFrame(outer, text="Paths", padding=10)
        paths_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            paths_frame,
            text="Paths saved to .env override the built-in defaults.",
            wraplength=480,
        ).pack(anchor=tk.W, pady=(0, 8))

        # FFmpeg
        ffmpeg_row = ttk.Frame(paths_frame)
        ffmpeg_row.pack(fill=tk.X, pady=2)
        ttk.Label(ffmpeg_row, text="FFmpeg:", width=20, anchor=tk.W).pack(side=tk.LEFT)
        saved_ffmpeg = self.settings.get("FFMPEG_PATH", "")
        ffmpeg_var = tk.StringVar(value=saved_ffmpeg)
        ttk.Entry(ffmpeg_row, textvariable=ffmpeg_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
        )
        ttk.Button(
            ffmpeg_row,
            text="Browse…",
            command=lambda: self._browse_exe(ffmpeg_var),
        ).pack(side=tk.LEFT)
        # placeholder hint
        ttk.Label(
            paths_frame,
            text=f"  Default: {self.DEFAULT_FFMPEG_PATH}  (searched on system PATH if blank)",
            foreground=colors.get("text_secondary", "gray"),
        ).pack(anchor=tk.W)

        ttk.Label(
            paths_frame,
            text="  (transcribe-anything is a pip package — manage its version in the Dependencies Manager below.)",
            foreground=colors.get("text_secondary", "gray"),
            wraplength=480,
        ).pack(anchor=tk.W, pady=(6, 0))

        # ── Tools ─────────────────────────────────────────────────────
        tools_frame = ttk.LabelFrame(outer, text="Tools", padding=10)
        tools_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Button(
            tools_frame,
            text="⬆  Dependencies Manager…",
            command=lambda: [win.grab_release(), self._open_deps_manager()],
        ).pack(anchor=tk.W)

        # ── Buttons (packed into the pinned bottom bar) ───────────────
        def _apply_and_close():
            self._apply_settings_from_dialog(
                bg_var.get().strip(),
                text_var.get().strip(),
                accent_var.get().strip(),
                ffmpeg_var.get().strip(),
            )
            win.destroy()

        def _apply_only():
            self._apply_settings_from_dialog(
                bg_var.get().strip(),
                text_var.get().strip(),
                accent_var.get().strip(),
                ffmpeg_var.get().strip(),
            )

        ttk.Button(btn_bar, text="Apply & Close", command=_apply_and_close).pack(
            side=tk.RIGHT, padx=(6, 0)
        )
        ttk.Button(btn_bar, text="Apply", command=_apply_only).pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text="Cancel", command=win.destroy).pack(side=tk.LEFT)

    def _pick_color(self, var: tk.StringVar, preview: tk.Label, title: str):
        """Open the system color-chooser and write the result into *var*."""
        from tkinter import colorchooser
        initial = var.get().strip() or None
        result = colorchooser.askcolor(color=initial, title=title, parent=self.root)
        if result and result[1]:
            hex_color = result[1]
            var.set(hex_color)
            try:
                preview.configure(bg=hex_color)
            except tk.TclError:
                pass

    def _clear_color(self, var: tk.StringVar, preview: tk.Label, fallback_color: str):
        """Clear the custom color var and reset the preview to the theme fallback."""
        var.set("")
        try:
            preview.configure(bg=fallback_color)
        except tk.TclError:
            pass

    def _browse_exe(self, var: tk.StringVar):
        """Open a file-browse dialog and put the chosen path into *var*."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")],
        )
        if path:
            var.set(path)

    def _apply_settings_from_dialog(
        self,
        bg_color: str,
        text_color: str,
        accent_color: str,
        ffmpeg_path: str,
    ):
        """Persist settings from the dialog and apply theme / path changes live."""
        # --- Paths (save to .env and sync into os.environ for this session) ---
        self.settings.set("FFMPEG_PATH", ffmpeg_path)
        # Keep os.environ in sync so cli_runner picks up new values immediately
        if ffmpeg_path:
            os.environ["FFMPEG_PATH"] = ffmpeg_path
        else:
            os.environ.pop("FFMPEG_PATH", None)
        logger.info(f"Saved paths — FFMPEG_PATH={ffmpeg_path!r}")

        # --- Colors ---
        self.settings.set("APP_COLOR_BG", bg_color)
        self.settings.set("APP_COLOR_TEXT", text_color)
        self.settings.set("APP_COLOR_ACCENT", accent_color)
        logger.info(f"Saved colors — BG={bg_color!r}, TEXT={text_color!r}, ACCENT={accent_color!r}")

        # Rebuild the active theme dict with custom colors if provided, then re-apply
        self._rebuild_theme_colors()
        self._apply_theme()

    def _sync_path_env_vars(self):
        """Sync FFMPEG_PATH / TRANSCRIBE_PATH from SettingsManager into os.environ.

        load_dotenv() runs at import time from config.py, so values already in
        .env are usually picked up.  This call ensures anything written by
        SettingsManager (which keeps its own dict) is also reflected in
        os.environ for cli_runner to read via os.getenv().
        """
        for key in ("FFMPEG_PATH", "TRANSCRIBE_PATH"):
            val = self.settings.get(key, "").strip()
            if val:
                os.environ[key] = val
            else:
                os.environ.pop(key, None)

    def _rebuild_theme_colors(self):
        """Rebuild self.theme_colors using saved custom colors (if any).

        Custom colors from .env override their counterparts in the current
        LIGHT/DARK palette; anything left blank keeps the base palette value.
          - APP_COLOR_BG     → bg_primary, bg_secondary
          - APP_COLOR_TEXT   → text_primary
          - APP_COLOR_ACCENT → accent, border, button_bg, button_hover,
                               accent_light, text_secondary
        """
        base = DARK_THEME if self.current_theme == "dark" else LIGHT_THEME
        # Start from a fresh copy so we don't mutate the module-level constant
        merged = dict(base)

        custom_bg     = self.settings.get("APP_COLOR_BG", "").strip()
        custom_text   = self.settings.get("APP_COLOR_TEXT", "").strip()
        custom_accent = self.settings.get("APP_COLOR_ACCENT", "").strip()

        if custom_bg:
            merged["bg_primary"]   = custom_bg
            merged["bg_secondary"] = custom_bg   # keep both bg keys consistent
        if custom_text:
            merged["text_primary"] = custom_text
        if custom_accent:
            # Accent drives all the "chrome": borders, buttons, tabs, labels.
            merged["accent"]        = custom_accent
            merged["border"]        = custom_accent
            merged["button_bg"]     = custom_accent
            merged["button_hover"]  = custom_accent
            merged["accent_light"]  = custom_accent
            merged["text_secondary"] = custom_accent

        self.theme_colors = merged

    def _open_deps_manager(self):
        """
        Open the Dependencies Manager popup window.

        Shows a list of key dependencies with their current installed version
        and individual Update buttons. Output from each command streams into
        a shared log area at the bottom of the window.
        """
        import importlib.metadata as _md
        import re as _re

        # Prevent opening multiple instances
        if hasattr(self, "_deps_window") and self._deps_window and self._deps_window.winfo_exists():
            self._deps_window.lift()
            return

        # (display_name, pip_package)  — pip_package None means a system dependency
        DEPS = [
            ("yt-dlp",              "yt-dlp"),
            ("transcribe-anything", "transcribe-anything"),
            ("openai-whisper",      "openai-whisper"),
            ("requests",            "requests"),
            ("python-docx",         "python-docx"),
            ("python-dotenv",       "python-dotenv"),
            ("openai",              "openai"),
            ("ffmpeg",              None),  # system dep, no pip management
        ]

        _NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        win = tk.Toplevel(self.root)
        win.title("⚙ Dependencies Manager")
        win.geometry("680x560")
        win.resizable(True, True)
        win.grab_set()
        self._deps_window = win

        outer = ttk.Frame(win, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="Dependencies Manager", font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))

        # --- Dependency rows ---
        rows_frame = ttk.LabelFrame(outer, text="Installed versions", padding=8)
        rows_frame.pack(fill=tk.X, pady=(0, 8))

        # Store per-row version display vars so we can update them
        version_vars = {}

        def _append_log(text):
            log_text.configure(state=tk.NORMAL)
            log_text.insert(tk.END, text)
            log_text.see(tk.END)
            log_text.configure(state=tk.DISABLED)

        # --- version helpers (run off the UI thread) ---
        def _installed_version(pkg):
            """Return the currently installed version string, or a status word."""
            if pkg is None:  # ffmpeg / system dependency
                try:
                    out = subprocess.run(
                        ["ffmpeg", "-version"], capture_output=True, text=True,
                        timeout=10, creationflags=_NO_WINDOW,
                    )
                    if out.returncode == 0:
                        m = _re.search(r"ffmpeg version (\S+)", out.stdout)
                        return m.group(1) if m else "installed"
                    return "not found"
                except FileNotFoundError:
                    return "not found"
                except Exception:
                    return "unknown"
            try:
                return _md.version(pkg)
            except Exception:
                return "not installed"

        def _available_versions(pkg):
            """Return list of available versions from PyPI (newest first), or []."""
            try:
                out = subprocess.run(
                    ["pip", "index", "versions", pkg], capture_output=True, text=True,
                    timeout=60, creationflags=_NO_WINDOW,
                )
                text = (out.stdout or "") + (out.stderr or "")
                m = _re.search(r"Available versions:\s*(.+)", text)
                if not m:
                    return []
                return [v.strip() for v in m.group(1).split(",") if v.strip()]
            except Exception:
                return []

        def _previous_version(pkg, current):
            """Find the highest available version strictly below `current`."""
            versions = _available_versions(pkg)
            if not versions:
                return None
            try:
                from packaging.version import parse as _vparse
                cur = _vparse(current)
                lowers = [v for v in versions if _vparse(v) < cur]
                return max(lowers, key=_vparse) if lowers else None
            except Exception:
                # Fallback: pip lists newest-first, so the entry after current is previous
                if current in versions:
                    idx = versions.index(current)
                    return versions[idx + 1] if idx + 1 < len(versions) else None
                return versions[1] if len(versions) > 1 else None

        def _refresh_version(pkg, name):
            """Refresh the displayed installed version for a single row."""
            def _worker():
                ver = _installed_version(pkg)
                win.after(0, lambda: version_vars[name].set(ver))
            threading.Thread(target=_worker, daemon=True).start()

        def _run_cmd(cmd, name, pkg, btns, refresh=True):
            """Run a command in a background thread, stream output, then refresh version."""
            def _worker():
                for b in btns:
                    win.after(0, lambda b=b: b.configure(state=tk.DISABLED))
                win.after(0, lambda: _append_log(f"\n▶ {' '.join(cmd)}\n"))
                try:
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, creationflags=_NO_WINDOW,
                    )
                    for line in proc.stdout:
                        win.after(0, lambda l=line: _append_log(l))
                    proc.wait()
                    if proc.returncode == 0:
                        win.after(0, lambda: _append_log("  [OK] done\n"))
                    else:
                        win.after(0, lambda: _append_log(f"  [FAILED] exit code {proc.returncode}\n"))
                except FileNotFoundError:
                    win.after(0, lambda: _append_log(f"  command not found: {cmd[0]}\n"))
                except Exception as exc:
                    win.after(0, lambda e=exc: _append_log(f"  error: {e}\n"))
                finally:
                    for b in btns:
                        win.after(0, lambda b=b: b.configure(state=tk.NORMAL))
                    if refresh:
                        _refresh_version(pkg, name)
            threading.Thread(target=_worker, daemon=True).start()

        def _downgrade(name, pkg, btns):
            """Find and install the version just below the currently installed one."""
            def _worker():
                for b in btns:
                    win.after(0, lambda b=b: b.configure(state=tk.DISABLED))
                cur = _installed_version(pkg)
                win.after(0, lambda: _append_log(
                    f"\n▶ Finding previous version of {pkg} (current: {cur})…\n"))
                prev = _previous_version(pkg, cur)
                if not prev:
                    win.after(0, lambda: _append_log(
                        f"  Could not determine a previous version for {pkg}.\n"))
                    for b in btns:
                        win.after(0, lambda b=b: b.configure(state=tk.NORMAL))
                    return
                win.after(0, lambda: _append_log(f"  Downgrading {pkg} → {prev}\n"))
                # Re-enable buttons; _run_cmd manages its own disable/enable + refresh
                for b in btns:
                    win.after(0, lambda b=b: b.configure(state=tk.NORMAL))
                win.after(0, lambda: _run_cmd(
                    ["pip", "install", f"{pkg}=={prev}"], name, pkg, btns))
            threading.Thread(target=_worker, daemon=True).start()

        for name, pkg in DEPS:
            row = ttk.Frame(rows_frame)
            row.pack(fill=tk.X, pady=2)

            ttk.Label(row, text=name, width=18, anchor=tk.W).pack(side=tk.LEFT)

            version_var = tk.StringVar(value="checking…")
            version_vars[name] = version_var
            ttk.Label(row, textvariable=version_var, width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(4, 8))

            row_btns = []
            if pkg:
                upd_btn = ttk.Button(row, text="Update", width=8)
                dng_btn = ttk.Button(row, text="Downgrade", width=10)
                row_btns = [upd_btn, dng_btn]
                upd_btn.configure(command=lambda n=name, p=pkg, bs=row_btns: _run_cmd(
                    ["pip", "install", "--upgrade", p], n, p, bs))
                dng_btn.configure(command=lambda n=name, p=pkg, bs=row_btns: _downgrade(n, p, bs))
                upd_btn.pack(side=tk.LEFT, padx=(0, 4))
                dng_btn.pack(side=tk.LEFT)
            else:
                ttk.Label(row, text="(system)", foreground="gray").pack(side=tk.LEFT)

        # --- Update all button ---
        def _update_all():
            for name, pkg in DEPS:
                if pkg:
                    _run_cmd(["pip", "install", "--upgrade", pkg], name, pkg, [update_all_btn])
        update_all_btn = ttk.Button(outer, text="⬆ Update All pip packages", command=_update_all)
        update_all_btn.pack(anchor=tk.W, pady=(0, 8))

        # --- Log area ---
        log_frame = ttk.LabelFrame(outer, text="Output", padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED,
                           font=("Consolas", 9))
        log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, command=log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        log_text.configure(yscrollcommand=log_scroll.set)

        ttk.Button(outer, text="Close", command=win.destroy).pack(anchor=tk.E, pady=(6, 0))

        # Populate the current installed version for every row on open
        for _name, _pkg in DEPS:
            _refresh_version(_pkg, _name)

    def _save_theme_to_env(self, theme):
        """
        Save theme preference to .env file.
        """
        import os
        from dotenv import dotenv_values, set_key

        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

        # Use python-dotenv to update .env file
        set_key(env_path, "APP_THEME", theme)

    def _load_theme_from_env(self):
        """
        Load theme preference from .env file or use default.
        """
        import os
        from dotenv import dotenv_values

        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

        # Load .env values
        if os.path.exists(env_path):
            env_values = dotenv_values(env_path)
            return env_values.get("APP_THEME", DEFAULT_THEME)

        return DEFAULT_THEME

    def _validate_font_entry(self, new_value: str) -> bool:
        """Validate the font entry: allow empty (mid-typing) or 1-2 digits."""
        return new_value == "" or (new_value.isdigit() and len(new_value) <= 2)

    def _on_font_entry_commit(self):
        """Apply the font size currently typed in the entry, clamping to [FONT_MIN, FONT_MAX]."""
        try:
            val = int(self.font_size_var.get())
        except (ValueError, TypeError):
            # Empty or non-numeric — restore last good value
            self.font_size_var.set(str(self.current_font_size))
            return
        val = max(self.FONT_MIN, min(self.FONT_MAX, val))
        self.font_size_var.set(str(val))
        if val != self.current_font_size:
            self.current_font_size = val
            self._apply_font_size()
            self._save_font_size_to_env(self.current_font_size)
            logger.info(f"Font size set to {self.current_font_size}px (saved to .env)")

    def _increase_font_size(self):
        """Increase font size by 2 (capped at FONT_MAX). Original button behaviour."""
        new = min(self.FONT_MAX, self.current_font_size + 2)
        self.font_size_var.set(str(new))
        self._on_font_entry_commit()

    def _decrease_font_size(self):
        """Decrease font size by 2 (floored at FONT_MIN). Original button behaviour."""
        new = max(self.FONT_MIN, self.current_font_size - 2)
        self.font_size_var.set(str(new))
        self._on_font_entry_commit()

    def _apply_font_size(self):
        """
        Apply current font size to all text widgets.

        v6.3: Applies to all tabs including Downloader
        """
        # Keep spinbox display in sync
        self.font_size_var.set(str(self.current_font_size))

        fs = self.current_font_size

        # --- Update ttk.Style so all labels, buttons, entries, checkboxes etc scale ---
        style = ttk.Style()
        style.configure("TLabel",        font=("Segoe UI", fs))
        style.configure("TButton",       font=("Segoe UI", fs))
        style.configure("TCheckbutton",  font=("Segoe UI", fs))
        style.configure("TRadiobutton",  font=("Segoe UI", fs))
        style.configure("TEntry",        font=("Segoe UI", fs))
        style.configure("TCombobox",     font=("Segoe UI", fs))
        style.configure("TLabelFrame.Label", font=("Segoe UI", fs))
        style.configure("TNotebook.Tab", font=("Segoe UI", fs))

        # Title label stays bold and slightly larger than the chosen size
        if hasattr(self, "title_label"):
            self.title_label.configure(font=("Segoe UI", max(fs + 2, 12), "bold"))

        # Apply to Summarizer tab
        if hasattr(self, "summarizer_tab"):
            self.summarizer_tab.content_text.configure(font=("Segoe UI", fs))
            self.summarizer_tab.response_text.configure(font=("Segoe UI", fs))
            self.summarizer_tab.info_text.configure(font=("Segoe UI", max(fs - 1, 8)))

        # Apply to Transcriber tab
        if hasattr(self, "transcriber_tab"):
            self.transcriber_tab.transcript_text.configure(font=("Segoe UI", fs))

        # Apply to Bulk Summarizer tab
        if hasattr(self, "bulk_summarizer_tab"):
            self.bulk_summarizer_tab.status_log.configure(font=("Segoe UI", fs))

        # Apply to Bulk Transcriber tab
        if hasattr(self, "bulk_transcriber_tab"):
            self.bulk_transcriber_tab.status_log.configure(font=("Segoe UI", fs))

        # Apply to Translation tab
        if hasattr(self, "translation_tab"):
            self.translation_tab.source_text.configure(font=("Segoe UI", fs))
            self.translation_tab.target_text.configure(font=("Segoe UI", fs))

        # Apply to Downloader tab
        if hasattr(self, "downloader_tab"):
            self.downloader_tab.status_log.configure(font=("Segoe UI", fs))

        # Apply to Video Subtitler tab
        if hasattr(self, "video_subtitler_tab"):
            self.video_subtitler_tab.srt_text.configure(font=("Segoe UI", fs))
            if hasattr(self.video_subtitler_tab, "translated_srt_text"):
                self.video_subtitler_tab.translated_srt_text.configure(font=("Segoe UI", fs))

        logger.debug(f"Applied font size {fs}px to all widgets")

    # Status bar methods

    def set_status(self, message: str):
        """
        Set status bar message.

        Args:
            message: Status message
        """
        self.status_var.set(message)
        logger.info(f"Status: {message}")

    # Convenience methods to access current tab

    def get_current_tab(self):
        """
        Get currently active tab.

        Returns:
            Current tab widget or None
        """
        tab_index = self.notebook.index(self.notebook.select())
        if tab_index == 0:
            return self.summarizer_tab
        elif tab_index == 1:
            return self.transcriber_tab
        elif tab_index == 2:
            return self.bulk_summarizer_tab
        elif tab_index == 3:
            return self.bulk_transcriber_tab
        elif tab_index == 4:
            return self.translation_tab
        elif tab_index == 5:
            return self.downloader_tab
        elif tab_index == 6:
            return self.video_subtitler_tab
        return None
