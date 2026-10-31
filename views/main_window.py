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
from dotenv import load_dotenv
import os
import re
import subprocess
import threading

import customtkinter as ctk

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
from utils import i18n
from utils.i18n import t
from views.summarizer_tab import SummarizerTab  # NEW v9.3
from views.transcriber_tab import TranscriberTab
from views.bulk_summarizer_tab import BulkSummarizerTab
from views.bulk_transcriber_tab import BulkTranscriberTab
from views.translation_tab import TranslationTab
from views.downloader_tab import DownloaderTab
from views.video_subtitler_tab import VideoSubtitlerTab
from views.ctk_compat import (
    CTkGradientFrame, CTkNotebook, owned_by_ctk, normalize_gradient_spec,
)
from views.ctk_theme import build_palette, apply_palette, apply_font_scale, font_sizes

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

    The on-screen tab order is defined by :attr:`TAB_ORDER`.
    """

    # On-screen tab order: (attribute name, translation key).
    #
    # This is the single source of truth for tab order. Index-based lookups
    # elsewhere derive from the notebook itself rather than hardcoding
    # positions, so reordering this list is all that is needed.
    TAB_ORDER = (
        ("summarizer_tab", "tab.summarizer"),
        ("downloader_tab", "tab.downloader"),
        ("translation_tab", "tab.translation"),
        ("transcriber_tab", "tab.transcriber"),
        ("video_subtitler_tab", "tab.video_subtitler"),
        ("bulk_summarizer_tab", "tab.bulk_summarizer"),
        ("bulk_transcriber_tab", "tab.bulk_transcriber"),
    )

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
        # Minimum size: below this the layout stops being usable even with the
        # tabs' scroll containers.
        self.root.minsize(820, 520)

        # Publish ourselves on the Tk root so tabs can find the main window.
        # MainWindow is not a widget, so it never appears in a widget's master
        # chain; without this, BaseTab.get_main_window() can never resolve and
        # cross-tab actions (e.g. Translation -> Summarizer) do nothing.
        self.root.main_window = self

        # Store settings manager
        self.settings = settings_manager

        # Localization: load the saved UI language and activate it BEFORE any
        # widgets are built, so every t(...) lookup during _setup_ui() resolves
        # to the chosen language. (Restart-to-apply: a language change only
        # takes full effect on the next launch.)
        i18n.set_language(self.settings.get_language())

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

        # Chrome-style tab hotkeys (Ctrl+1..Ctrl+8, Ctrl+9 = last tab)
        self._setup_tab_hotkeys()

        # Restore the window size/position from the last session, and save it
        # again on close. Done last so the layout is already built and the
        # restored size is applied to a complete window.
        self._last_normal_geometry = None
        self._restore_window_geometry()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        logger.info(
            f"MainWindow initialized (v6.3 - {self.current_theme} theme, {self.current_font_size}px font)"
        )

    # ------------------------------------------------------------------
    # Window size / position persistence
    # ------------------------------------------------------------------

    # Smallest window we are willing to restore; anything smaller is treated
    # as a corrupt value rather than shrinking the app into uselessness.
    _MIN_RESTORE_W = 820
    _MIN_RESTORE_H = 520

    def _parse_geometry(self, geometry: str):
        """
        Parse a Tk geometry string into (w, h, x, y).

        Returns None if it does not match "WxH+X+Y" (negative offsets, which
        are valid on multi-monitor setups, are accepted).
        """
        match = re.fullmatch(
            r"(\d+)x(\d+)([+-]\d+)([+-]\d+)", (geometry or "").strip()
        )
        if not match:
            return None
        w, h, x, y = match.groups()
        return int(w), int(h), int(x), int(y)

    def _geometry_is_visible(self, w: int, h: int, x: int, y: int) -> bool:
        """
        True if the window would land somewhere the user can actually see.

        Guards against restoring onto a monitor that is no longer attached: a
        saved position from a second screen can put the title bar completely
        off-canvas, leaving a window that cannot be moved or closed.
        """
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Require a reasonable slice of the title bar to be on-screen.
        margin = 120
        if x + w < margin or x > screen_w - margin:
            return False
        if y < -10 or y > screen_h - 80:
            return False
        return True

    def _restore_window_geometry(self):
        """Restore the size/position (and maximized state) from last session."""
        try:
            saved = self.settings.get_window_geometry()
            parsed = self._parse_geometry(saved)

            if parsed:
                w, h, x, y = parsed
                if w < self._MIN_RESTORE_W or h < self._MIN_RESTORE_H:
                    logger.info(
                        f"Ignoring saved window size {w}x{h} (below minimum)"
                    )
                elif not self._geometry_is_visible(w, h, x, y):
                    # Keep the size, drop the off-screen position.
                    self.root.geometry(f"{w}x{h}")
                    logger.info(
                        f"Saved window position {x},{y} is off-screen; "
                        f"restored size only"
                    )
                else:
                    self.root.geometry(saved)
                    logger.info(f"Restored window geometry: {saved}")
            elif saved:
                logger.warning(f"Could not parse saved window geometry: {saved!r}")

            # Remember the normal (un-maximized) geometry from here on.
            self.root.update_idletasks()
            self._last_normal_geometry = self.root.geometry()

            if self.settings.get_window_maximized():
                self.root.state("zoomed")
                logger.info("Restored maximized window state")
        except Exception as e:
            logger.error(f"Error restoring window geometry: {e}")
            self._last_normal_geometry = None

        # Track the normal geometry as the user moves/resizes, because
        # root.geometry() reports the *zoomed* box while maximized and would
        # otherwise overwrite the restore size with the screen size.
        self.root.bind("<Configure>", self._on_window_configure, add="+")

    def _on_window_configure(self, event=None):
        """Record the last normal (non-maximized) geometry."""
        if event is not None and event.widget is not self.root:
            return
        try:
            if self.root.state() == "normal":
                self._last_normal_geometry = self.root.geometry()
        except tk.TclError:
            pass

    def _save_window_geometry(self):
        """Persist the window size/position and maximized state."""
        try:
            try:
                maximized = self.root.state() == "zoomed"
            except tk.TclError:
                maximized = False

            geometry = getattr(self, "_last_normal_geometry", None)
            if not maximized:
                geometry = self.root.geometry()

            if self._parse_geometry(geometry):
                self.settings.set_window_geometry(geometry)
            self.settings.set_window_maximized(maximized)
            logger.info(
                f"Saved window geometry: {geometry} (maximized={maximized})"
            )
        except Exception as e:
            logger.error(f"Error saving window geometry: {e}")

    def _on_close(self):
        """Save window state, then close."""
        self._save_window_geometry()
        self.root.destroy()

    def _setup_tab_hotkeys(self):
        """
        Bind Chrome-style keyboard shortcuts for switching tabs.

        - Ctrl+1 … Ctrl+8 select the tab at that position (1-based)
        - Ctrl+9 always selects the last tab

        Both the number row and the numeric keypad are bound. Shortcuts are
        registered with bind_all so they work regardless of which widget
        (text box, entry, etc.) currently has focus.
        """
        for n in range(1, 9):  # 1..8 → tab index 0..7
            self.root.bind_all(
                f"<Control-Key-{n}>",
                lambda e, idx=n - 1: self._select_tab_by_index(idx),
            )
            self.root.bind_all(
                f"<Control-KP_{n}>",
                lambda e, idx=n - 1: self._select_tab_by_index(idx),
            )

        # Ctrl+9 → last tab (matches Chrome)
        self.root.bind_all("<Control-Key-9>", lambda e: self._select_tab_by_index(-1))
        self.root.bind_all("<Control-KP_9>", lambda e: self._select_tab_by_index(-1))

    def _select_tab_by_index(self, index):
        """
        Select the notebook tab at `index`. A negative index selects the last
        tab. Out-of-range indices are ignored.
        """
        try:
            total = self.notebook.index("end")
            if total == 0:
                return "break"
            if index < 0:
                index = total - 1
            if 0 <= index < total:
                self.notebook.select(index)
        except tk.TclError:
            pass
        return "break"

    def _restore_last_active_tab(self):
        """
        Restore the last active tab from settings.

        Called after all tabs are initialized.
        """
        try:
            last_tab = self.settings.get_last_active_tab()
            # Validate against the actual number of tabs, not a hardcoded 6.
            if 0 <= last_tab < len(self.TAB_ORDER):
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
        # Main frame. CTkFrame has no `padding` option, so the 10px inset is
        # applied via the grid call instead.
        main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
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
        header_frame = CTkGradientFrame(parent, flat_palette_key="bg")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        header_frame.columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            header_frame,
            text=self.app_title_display,
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        )
        # Sized explicitly in _apply_font_size (title role), so the generic
        # label pass must leave it alone.
        self.title_label._font_skip = True
        self.title_label.grid(row=0, column=0, sticky="w")

        # Controls on the right side
        controls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        controls_frame.grid(row=0, column=1, sticky="e", padx=(10, 0))

        # Font stepper: grouped on its own rounded surface so the three
        # controls read as one unit instead of three loose buttons.
        font_group = ctk.CTkFrame(
            controls_frame, corner_radius=8, fg_color=("gray90", "gray20")
        )
        font_group.grid(row=0, column=0, padx=(0, 10))

        col = 0
        ctk.CTkLabel(
            font_group,
            text=t("header.font"),
            text_color=("gray40", "gray65"),
        ).grid(row=0, column=col, padx=(10, 6), pady=4)
        col += 1

        # Decrease button — steps by 2 (original behaviour)
        self.font_decrease_btn = ctk.CTkButton(
            font_group,
            text="\u2212",  # proper minus sign
            width=28,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="transparent",
            text_color=("gray25", "gray85"),
            hover_color=("gray82", "gray30"),
            command=self._decrease_font_size,
        )
        # Fixed-size glyph button: it must not resize itself when the font
        # size it controls changes.
        self.font_decrease_btn._font_skip = True
        self.font_decrease_btn.grid(row=0, column=col, padx=(0, 2), pady=4)
        col += 1

        # Font size entry — type any integer in [FONT_MIN, FONT_MAX] for precise
        # control (not restricted to the +2/-2 steps of the buttons).
        # CTkEntry has no validatecommand, so digits are filtered with a trace on
        # the variable instead of a key-validation callback.
        self.font_size_var = tk.StringVar(value=str(self.current_font_size))
        self.font_size_var.trace_add("write", self._sanitize_font_entry)
        self.font_entry = ctk.CTkEntry(
            font_group,
            textvariable=self.font_size_var,
            width=42,
            height=26,
            corner_radius=6,
            border_width=0,
            justify="center",
        )
        # Part of the grouped stepper: keep it seamless inside the group.
        self.font_entry._borderless = True
        self.font_entry.grid(row=0, column=col, padx=0, pady=4)
        col += 1
        # Commit typed value on Enter or focus-out
        self.font_entry.bind("<Return>",   lambda _e: self._on_font_entry_commit())
        self.font_entry.bind("<FocusOut>", lambda _e: self._on_font_entry_commit())

        # Increase button — steps by 2 (original behaviour)
        self.font_increase_btn = ctk.CTkButton(
            font_group,
            text="+",
            width=28,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="transparent",
            text_color=("gray25", "gray85"),
            hover_color=("gray82", "gray30"),
            command=self._increase_font_size,
        )
        self.font_increase_btn._font_skip = True
        self.font_increase_btn.grid(row=0, column=col, padx=(2, 10), pady=4)

        # Theme toggle — secondary action, outlined rather than filled.
        self.theme_btn = ctk.CTkButton(
            controls_frame,
            text=t("header.dark_mode") if self.current_theme == "light" else t("header.light_mode"),
            command=self._toggle_theme,
            width=118,
            height=34,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray25", "gray85"),
            hover_color=("gray85", "gray28"),
        )
        self.theme_btn.grid(row=0, column=1, padx=(0, 8))

        # Settings button (replaces old cogwheel → deps manager direct link)
        self.settings_btn = ctk.CTkButton(
            controls_frame,
            text=t("header.settings"),
            command=self._open_settings,
            width=104,
            height=34,
            corner_radius=8,
        )
        self.settings_btn.grid(row=0, column=2)

    def _setup_tabs(self, parent):
        """
        Setup tab notebook with all tabs.

        The display order lives in :attr:`TAB_ORDER`.

        Args:
            parent: Parent frame
        """
        # Create notebook (tab container).
        # CTkNotebook mimics the slice of the ttk.Notebook API this app uses, so
        # tabs that are still ttk-based keep working unchanged while the shell
        # gets the CustomTkinter look.
        self.notebook = CTkNotebook(parent)
        self.notebook.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

        # Initialize PromptManager
        self.prompt_manager = PromptManager()

        # --- Construct the tabs ---
        # Construction is kept separate from ordering below, so the on-screen
        # order is defined in exactly one place (TAB_ORDER) instead of being an
        # accident of the order these lines happen to run in.
        self.summarizer_tab = SummarizerTab(
            self.notebook,
            prompt_manager=self.prompt_manager,
            settings_manager=self.settings,
        )
        self.transcriber_tab = TranscriberTab(self.notebook, self.settings)
        self.bulk_summarizer_tab = BulkSummarizerTab(
            self.notebook,
            prompt_manager=self.prompt_manager,
            settings_manager=self.settings,
        )
        self.bulk_transcriber_tab = BulkTranscriberTab(
            self.notebook, settings_manager=self.settings
        )
        self.translation_tab = TranslationTab(self.notebook)
        self.downloader_tab = DownloaderTab(self.notebook)
        self.video_subtitler_tab = VideoSubtitlerTab(self.notebook)

        # --- Display order ---
        # Single-item work comes first, the bulk/batch tools last.
        for attr, label_key in self.TAB_ORDER:
            self.notebook.add(getattr(self, attr), text=t(label_key))

        logger.info(f"All tabs initialized ({len(self.TAB_ORDER)} tabs)")

    def _setup_status_bar(self, parent):
        """
        Setup status bar and progress indicator.

        Args:
            parent: Parent frame
        """
        status_frame = ctk.CTkFrame(parent, fg_color="transparent")
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.columnconfigure(0, weight=1)

        # A quiet status strip: no sunken relief, just a small dot and muted
        # text so it informs without competing with the content.
        bar = ctk.CTkFrame(
            status_frame, corner_radius=8, fg_color=("gray90", "gray16"), height=30
        )
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(1, weight=1)

        # Semantic colour (healthy/ready), not branding - excluded from the
        # palette pass so it keeps its meaning under any accent.
        status_dot = ctk.CTkLabel(
            bar, text="\u25cf", width=12, text_color=("#15803d", "#4ade80")
        )
        status_dot._theme_skip = True
        status_dot._font_skip = True  # glyph, not text
        status_dot.grid(row=0, column=0, padx=(10, 6), pady=4)

        self.status_var = tk.StringVar(value=t("status.ready"))
        self.status_label = ctk.CTkLabel(
            bar,
            textvariable=self.status_var,
            anchor="w",
            text_color=("gray30", "gray75"),
        )
        self.status_label.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=4)

    def _apply_theme(self):
        """
        Apply current theme colors to all widgets.
        """
        # Drive CustomTkinter's own light/dark mode. Migrated widgets theme
        # themselves from this; the ttk styling below still covers the tabs that
        # have not been migrated yet.
        ctk.set_appearance_mode("dark" if self.current_theme == "dark" else "light")

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

        # Apply to root. A CTk root takes `fg_color`, not the classic `bg`.
        try:
            self.root.configure(fg_color=colors["bg_primary"])
        except (ValueError, tk.TclError):
            logger.debug("Could not set root fg_color", exc_info=True)

        # Update text widget colors in tabs
        text_bg = colors["bg_secondary"]
        text_fg = colors["text_primary"]

        # Recolor every classic tk.Text / ScrolledText widget across all tabs.
        #
        # This replaces the old per-tab list (transcript_text, status_log,
        # source_text, srt_text, ...). That list had to name every widget
        # explicitly, and it broke as tabs migrated to CustomTkinter, because
        # CTk widgets raise ValueError for bg/fg. The recursive walk finds the
        # same widgets, needs no maintenance, and skips CTk-owned ones (which
        # the palette pass below handles instead).
        if hasattr(self, "notebook"):
            self._recolor_text_widgets(self.notebook, text_bg, text_fg)

        # --- CustomTkinter widgets -------------------------------------------
        # CTk widgets ignore ttk.Style, so without this pass they keep their
        # built-in blue and the Settings colours (background / text / accent)
        # never reach the migrated tabs, the header or the tab strip.
        self.ctk_palette = build_palette(
            colors,
            is_dark=self.current_theme == "dark",
            gradient=self._active_gradient(),
        )
        apply_palette(self.root, self.ctk_palette)

        # Title label (CTkLabel uses `text_color`, not `foreground`)
        if hasattr(self, "title_label"):
            self.title_label.configure(text_color=colors["text_primary"])

        # Reassert font sizes — _apply_theme sets some hardcoded fonts, so re-run
        # the font sizing to keep the user's chosen size after a theme toggle.
        if hasattr(self, "notebook"):
            self._apply_font_size()

        logger.info(f"Applied {self.current_theme} theme")

    def _active_gradient(self):
        """Return the validated selected gradient spec, or None when disabled."""
        if not self.settings.get_gradient_enabled():
            return None
        start, end = self.settings.get_gradient_colors()
        return normalize_gradient_spec(
            start, end, self.settings.get_gradient_direction()
        )

    def _recolor_text_widgets(self, parent, bg, fg):
        """
        Recursively recolor every tk.Text / ScrolledText widget under `parent`.

        ttk widgets are styled via ttk.Style, but classic tk.Text widgets need
        their bg/fg set explicitly or they stay light ("cream") in dark mode.
        """
        for child in parent.winfo_children():
            try:
                if isinstance(child, tk.Text):  # ScrolledText subclasses tk.Text
                    # A CTkTextbox wraps a real tk.Text. Recoloring that inner
                    # widget directly would override CustomTkinter's own
                    # theming, so leave CTk-owned text widgets alone.
                    if not owned_by_ctk(child):
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
            text=t("header.dark_mode") if self.current_theme == "light" else t("header.light_mode")
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
        win.title(t("settings.title"))
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

        ttk.Label(outer, text=t("settings.heading"), font=("Segoe UI", 13, "bold")).pack(
            anchor=tk.W, pady=(0, 12)
        )

        # ── Appearance ────────────────────────────────────────────────
        appear_frame = ttk.LabelFrame(outer, text=t("settings.appearance"), padding=10)
        appear_frame.pack(fill=tk.X, pady=(0, 10))

        # --- Theme colors ---
        color_row = ttk.Frame(appear_frame)
        color_row.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(color_row, text=t("settings.theme_colors_hint"),
                  wraplength=480).pack(anchor=tk.W, pady=(0, 6))

        # Load currently saved custom colors (may be empty = "use default")
        saved_bg     = self.settings.get("APP_COLOR_BG", "")
        saved_text   = self.settings.get("APP_COLOR_TEXT", "")
        saved_accent = self.settings.get("APP_COLOR_ACCENT", "")

        # Background color
        bg_row = ttk.Frame(appear_frame)
        bg_row.pack(fill=tk.X, pady=2)
        ttk.Label(bg_row, text=t("settings.color.background"), width=14, anchor=tk.W).pack(side=tk.LEFT)
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
            text=t("settings.btn.pick"),
            command=lambda: self._pick_color(bg_var, bg_preview, t("settings.color.pick_bg_title")),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            bg_row,
            text=t("settings.btn.clear"),
            command=lambda: self._clear_color(bg_var, bg_preview, colors["bg_primary"]),
        ).pack(side=tk.LEFT)

        # Text / foreground color
        text_row = ttk.Frame(appear_frame)
        text_row.pack(fill=tk.X, pady=2)
        ttk.Label(text_row, text=t("settings.color.text"), width=14, anchor=tk.W).pack(side=tk.LEFT)
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
            text=t("settings.btn.pick"),
            command=lambda: self._pick_color(text_var, text_preview, t("settings.color.pick_text_title")),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            text_row,
            text=t("settings.btn.clear"),
            command=lambda: self._clear_color(text_var, text_preview, colors["text_primary"]),
        ).pack(side=tk.LEFT)

        # Accent color — borders, buttons, section labels, secondary text
        accent_row = ttk.Frame(appear_frame)
        accent_row.pack(fill=tk.X, pady=2)
        ttk.Label(accent_row, text=t("settings.color.accent"), width=14, anchor=tk.W).pack(side=tk.LEFT)
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
            text=t("settings.btn.pick"),
            command=lambda: self._pick_color(accent_var, accent_preview, t("settings.color.pick_accent_title")),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            accent_row,
            text=t("settings.btn.clear"),
            command=lambda: self._clear_color(accent_var, accent_preview, colors["accent"]),
        ).pack(side=tk.LEFT)

        ttk.Label(
            appear_frame,
            text=t("settings.accent_hint"),
            foreground=colors.get("text_secondary", "gray"),
        ).pack(anchor=tk.W, pady=(2, 0))

        # --- Background gradient ---
        ttk.Separator(appear_frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, pady=(10, 8)
        )

        gradient_enabled_var = tk.BooleanVar(
            value=self.settings.get_gradient_enabled()
        )
        saved_grad_start, saved_grad_end = self.settings.get_gradient_colors()

        ttk.Checkbutton(
            appear_frame,
            text=t("settings.gradient_enable"),
            variable=gradient_enabled_var,
        ).pack(anchor=tk.W)

        # Gradient start
        grad_start_row = ttk.Frame(appear_frame)
        grad_start_row.pack(fill=tk.X, pady=2)
        ttk.Label(grad_start_row, text=t("settings.gradient_from"),
                  width=14, anchor=tk.W).pack(side=tk.LEFT)
        grad_start_var = tk.StringVar(value=saved_grad_start)
        ttk.Entry(grad_start_row, textvariable=grad_start_var, width=10).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        grad_start_preview = tk.Label(
            grad_start_row,
            bg=saved_grad_start if saved_grad_start else colors["bg_primary"],
            width=3, relief=tk.SOLID, borderwidth=1,
        )
        grad_start_preview.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            grad_start_row,
            text=t("settings.btn.pick"),
            command=lambda: self._pick_color(
                grad_start_var, grad_start_preview,
                t("settings.gradient_pick_from"),
            ),
        ).pack(side=tk.LEFT)

        # Gradient end
        grad_end_row = ttk.Frame(appear_frame)
        grad_end_row.pack(fill=tk.X, pady=2)
        ttk.Label(grad_end_row, text=t("settings.gradient_to"),
                  width=14, anchor=tk.W).pack(side=tk.LEFT)
        grad_end_var = tk.StringVar(value=saved_grad_end)
        ttk.Entry(grad_end_row, textvariable=grad_end_var, width=10).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        grad_end_preview = tk.Label(
            grad_end_row,
            bg=saved_grad_end if saved_grad_end else colors["bg_primary"],
            width=3, relief=tk.SOLID, borderwidth=1,
        )
        grad_end_preview.pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            grad_end_row,
            text=t("settings.btn.pick"),
            command=lambda: self._pick_color(
                grad_end_var, grad_end_preview, t("settings.gradient_pick_to")
            ),
        ).pack(side=tk.LEFT)

        # Direction matrix: each arrow indicates where the end colour lands.
        # Center is a radial "ball" gradient: start in the middle, end at the
        # perimeter. Bottom-center preserves the previous top-to-bottom mode.
        gradient_direction_var = tk.StringVar(
            value=self.settings.get_gradient_direction()
        )
        ttk.Label(
            appear_frame, text=t("settings.gradient_direction")
        ).pack(anchor=tk.W, pady=(8, 2))
        direction_grid = ttk.Frame(appear_frame)
        direction_grid.pack(anchor=tk.W)
        direction_choices = (
            ("top_left", "↖"), ("top", "↑"), ("top_right", "↗"),
            ("left", "←"), ("center", "●"), ("right", "→"),
            ("bottom_left", "↙"), ("bottom", "↓"), ("bottom_right", "↘"),
        )
        for index, (mode, symbol) in enumerate(direction_choices):
            ttk.Radiobutton(
                direction_grid, text=symbol, value=mode,
                variable=gradient_direction_var,
            ).grid(row=index // 3, column=index % 3, padx=3, pady=1, sticky="w")

        direction_caption_var = tk.StringVar()
        direction_captions = {
            "top_left": t("settings.gradient_flow.top_left"),
            "top": t("settings.gradient_flow.top"),
            "top_right": t("settings.gradient_flow.top_right"),
            "left": t("settings.gradient_flow.left"),
            "center": t("settings.gradient_flow.center"),
            "right": t("settings.gradient_flow.right"),
            "bottom_left": t("settings.gradient_flow.bottom_left"),
            "bottom": t("settings.gradient_flow.bottom"),
            "bottom_right": t("settings.gradient_flow.bottom_right"),
        }
        def _update_gradient_direction_caption(*_args):
            direction_caption_var.set(
                direction_captions.get(
                    gradient_direction_var.get(), direction_captions["bottom"]
                )
            )
        gradient_direction_var.trace_add("write", _update_gradient_direction_caption)
        _update_gradient_direction_caption()
        ttk.Label(
            appear_frame, textvariable=direction_caption_var,
            foreground=colors.get("text_secondary", "gray"),
        ).pack(anchor=tk.W)

        ttk.Label(
            appear_frame,
            text=t("settings.gradient_hint"),
            foreground=colors.get("text_secondary", "gray"),
            wraplength=480,
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

        # --- Language ---
        lang_row = ttk.Frame(appear_frame)
        lang_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(lang_row, text=t("settings.language"), width=14, anchor=tk.W).pack(side=tk.LEFT)
        lang_var = tk.StringVar(value=i18n.name_for_code(i18n.get_language()))
        ttk.Combobox(
            lang_row,
            textvariable=lang_var,
            state="readonly",
            width=16,
            values=[i18n.name_for_code(code) for code in i18n.SUPPORTED_LANGUAGES],
        ).pack(side=tk.LEFT)
        ttk.Label(
            appear_frame,
            text=t("settings.language_hint"),
            foreground=colors.get("text_secondary", "gray"),
        ).pack(anchor=tk.W, pady=(2, 0))

        # --- Font size ---
        font_row = ttk.Frame(appear_frame)
        font_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(font_row, text=t("settings.font_size"), width=14, anchor=tk.W).pack(side=tk.LEFT)
        ttk.Label(
            font_row,
            text=t("settings.font_size_hint").format(size=self.current_font_size),
            foreground=colors["text_secondary"] if "text_secondary" in colors else "gray",
        ).pack(side=tk.LEFT)

        # ── Paths ─────────────────────────────────────────────────────
        paths_frame = ttk.LabelFrame(outer, text=t("settings.paths"), padding=10)
        paths_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            paths_frame,
            text=t("settings.paths_hint"),
            wraplength=480,
        ).pack(anchor=tk.W, pady=(0, 8))

        # FFmpeg
        ffmpeg_row = ttk.Frame(paths_frame)
        ffmpeg_row.pack(fill=tk.X, pady=2)
        ttk.Label(ffmpeg_row, text=t("settings.ffmpeg"), width=20, anchor=tk.W).pack(side=tk.LEFT)
        saved_ffmpeg = self.settings.get("FFMPEG_PATH", "")
        ffmpeg_var = tk.StringVar(value=saved_ffmpeg)
        ttk.Entry(ffmpeg_row, textvariable=ffmpeg_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6)
        )
        ttk.Button(
            ffmpeg_row,
            text=t("settings.btn.browse"),
            command=lambda: self._browse_exe(ffmpeg_var),
        ).pack(side=tk.LEFT)
        # placeholder hint
        ttk.Label(
            paths_frame,
            text=t("settings.ffmpeg_default_hint").format(path=self.DEFAULT_FFMPEG_PATH),
            foreground=colors.get("text_secondary", "gray"),
        ).pack(anchor=tk.W)

        ttk.Label(
            paths_frame,
            text=t("settings.transcribe_hint"),
            foreground=colors.get("text_secondary", "gray"),
            wraplength=480,
        ).pack(anchor=tk.W, pady=(6, 0))

        # ── Tools ─────────────────────────────────────────────────────
        tools_frame = ttk.LabelFrame(outer, text=t("settings.tools"), padding=10)
        tools_frame.pack(fill=tk.X, pady=(0, 12))

        ttk.Button(
            tools_frame,
            text=t("settings.deps_manager_btn"),
            command=lambda: [win.grab_release(), self._open_deps_manager()],
        ).pack(anchor=tk.W)

        # ── Buttons (packed into the pinned bottom bar) ───────────────
        def _notify_restart_if_needed(language_changed):
            """Show the restart-to-apply prompt when the language was changed."""
            if language_changed:
                from tkinter import messagebox
                messagebox.showinfo(
                    t("settings.restart_title"),
                    t("settings.restart_message"),
                    parent=win,
                )

        def _collect():
            return dict(
                bg_color=bg_var.get().strip(),
                text_color=text_var.get().strip(),
                accent_color=accent_var.get().strip(),
                ffmpeg_path=ffmpeg_var.get().strip(),
                language=i18n.code_for_name(lang_var.get()),
                gradient_enabled=gradient_enabled_var.get(),
                gradient_start=grad_start_var.get().strip(),
                gradient_end=grad_end_var.get().strip(),
                gradient_direction=gradient_direction_var.get(),
            )

        def _apply_and_close():
            language_changed = self._apply_settings_from_dialog(**_collect())
            _notify_restart_if_needed(language_changed)
            win.destroy()

        def _apply_only():
            language_changed = self._apply_settings_from_dialog(**_collect())
            _notify_restart_if_needed(language_changed)

        ttk.Button(btn_bar, text=t("settings.apply_close"), command=_apply_and_close).pack(
            side=tk.RIGHT, padx=(6, 0)
        )
        ttk.Button(btn_bar, text=t("settings.apply"), command=_apply_only).pack(side=tk.RIGHT)
        ttk.Button(btn_bar, text=t("settings.cancel"), command=win.destroy).pack(side=tk.LEFT)

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
            title=t("settings.browse_exe_title"),
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
        language: str = None,
        gradient_enabled: bool = None,
        gradient_start: str = None,
        gradient_end: str = None,
        gradient_direction: str = None,
    ) -> bool:
        """Persist settings from the dialog and apply theme / path changes live.

        Theme, color and path changes take effect immediately. The UI language
        is restart-to-apply: it is saved here but only rendered on the next
        launch (widgets read their text once, at construction).

        Returns:
            True if the UI language was changed (so the caller can prompt for a
            restart), False otherwise.
        """
        # --- Language (restart-to-apply) ---
        language_changed = False
        if language:
            prev_language = self.settings.get_language()
            if language != prev_language:
                self.settings.set_language(language)
                language_changed = True
                logger.info(
                    f"Saved UI language: {prev_language!r} → {language!r} (restart required)"
                )

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

        # --- Background gradient ---
        if (
            gradient_enabled is not None
            or gradient_start is not None
            or gradient_end is not None
            or gradient_direction is not None
        ):
            current_start, current_end = self.settings.get_gradient_colors()
            self.settings.set_gradient(
                self.settings.get_gradient_enabled()
                if gradient_enabled is None else bool(gradient_enabled),
                current_start if gradient_start is None else gradient_start,
                current_end if gradient_end is None else gradient_end,
                self.settings.get_gradient_direction()
                if gradient_direction is None else gradient_direction,
            )
        logger.info(
            f"Saved gradient — enabled={gradient_enabled}, from={gradient_start!r}, "
            f"to={gradient_end!r}, direction={gradient_direction!r}"
        )

        # Rebuild the active theme dict with custom colors if provided, then re-apply
        self._rebuild_theme_colors()
        self._apply_theme()

        return language_changed

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
            ("CustomTkinter",       "customtkinter"),
            ("Pillow (gradients)",  "Pillow"),
            ("yt-dlp",              "yt-dlp"),
            ("transcribe-anything", "transcribe-anything"),
            ("openai-whisper",      "openai-whisper"),
            ("srt",                 "srt"),
            ("pyttsx3 (text-to-speech)", "pyttsx3"),
            ("pywin32 (Windows TTS)", "pywin32"),
            ("requests",            "requests"),
            ("python-docx",         "python-docx"),
            ("python-dotenv",       "python-dotenv"),
            ("ffmpeg",              None),  # system executable, not a PyPI package
        ]

        _NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        win = tk.Toplevel(self.root)
        win.title(t("deps.title"))
        win.geometry("680x560")
        win.resizable(True, True)
        win.grab_set()
        self._deps_window = win

        outer = ttk.Frame(win, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text=t("deps.heading"), font=("Segoe UI", 12, "bold")).pack(anchor=tk.W, pady=(0, 8))

        # --- Dependency rows ---
        rows_frame = ttk.LabelFrame(outer, text=t("deps.installed_versions"), padding=8)
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

        def _check_update(name, pkg, btns):
            """Check whether a newer version exists (without installing) and log the result."""
            def _worker():
                for b in btns:
                    win.after(0, lambda b=b: b.configure(state=tk.DISABLED))
                try:
                    cur = _installed_version(pkg)

                    # System dependency (ffmpeg) — no PyPI to compare against
                    if pkg is None:
                        win.after(0, lambda: _append_log(
                            f"\n▶ {name}: installed {cur} — system dependency, "
                            f"check/update manually.\n"))
                        return

                    win.after(0, lambda: _append_log(
                        f"\n▶ Checking {pkg} (installed: {cur})…\n"))

                    versions = _available_versions(pkg)
                    if not versions:
                        win.after(0, lambda: _append_log(
                            f"  Could not retrieve available versions for {pkg}.\n"))
                        return

                    # Determine the newest available version
                    try:
                        from packaging.version import parse as _vparse
                        latest = max(versions, key=_vparse)
                        newer = (
                            cur not in ("not installed", "unknown")
                            and _vparse(latest) > _vparse(cur)
                        )
                    except Exception:
                        latest = versions[0]  # pip lists newest-first
                        newer = cur not in ("not installed", "unknown") and latest != cur

                    if cur in ("not installed", "unknown"):
                        win.after(0, lambda: _append_log(
                            f"  Latest available: {latest} (not currently installed)\n"))
                    elif newer:
                        win.after(0, lambda: _append_log(
                            f"  [UPDATE AVAILABLE] {pkg}: {cur} → {latest}\n"))
                    else:
                        win.after(0, lambda: _append_log(
                            f"  [UP TO DATE] {pkg} {cur} (latest: {latest})\n"))
                finally:
                    for b in btns:
                        win.after(0, lambda b=b: b.configure(state=tk.NORMAL))
            threading.Thread(target=_worker, daemon=True).start()

        for name, pkg in DEPS:
            row = ttk.Frame(rows_frame)
            row.pack(fill=tk.X, pady=2)

            ttk.Label(row, text=name, width=18, anchor=tk.W).pack(side=tk.LEFT)

            version_var = tk.StringVar(value=t("deps.checking"))
            version_vars[name] = version_var
            ttk.Label(row, textvariable=version_var, width=18, anchor=tk.W).pack(side=tk.LEFT, padx=(4, 8))

            row_btns = []
            if pkg:
                upd_btn = ttk.Button(row, text=t("deps.btn.update"), width=8)
                dng_btn = ttk.Button(row, text=t("deps.btn.downgrade"), width=10)
                chk_btn = ttk.Button(row, text=t("deps.btn.check"), width=8)
                row_btns = [upd_btn, dng_btn, chk_btn]
                upd_btn.configure(command=lambda n=name, p=pkg, bs=row_btns: _run_cmd(
                    ["pip", "install", "--upgrade", p], n, p, bs))
                dng_btn.configure(command=lambda n=name, p=pkg, bs=row_btns: _downgrade(n, p, bs))
                chk_btn.configure(command=lambda n=name, p=pkg, bs=row_btns: _check_update(n, p, bs))
                upd_btn.pack(side=tk.LEFT, padx=(0, 4))
                dng_btn.pack(side=tk.LEFT, padx=(0, 4))
                chk_btn.pack(side=tk.LEFT)
            else:
                # System dependency (ffmpeg): no pip Update/Downgrade, but still a Check button
                chk_btn = ttk.Button(row, text=t("deps.btn.check"), width=8)
                row_btns = [chk_btn]
                chk_btn.configure(command=lambda n=name, p=pkg, bs=row_btns: _check_update(n, p, bs))
                ttk.Label(row, text=t("deps.system"), foreground="gray").pack(side=tk.LEFT, padx=(0, 6))
                chk_btn.pack(side=tk.LEFT)

        # --- Update all button ---
        def _update_all():
            for name, pkg in DEPS:
                if pkg:
                    _run_cmd(["pip", "install", "--upgrade", pkg], name, pkg, [update_all_btn])
        update_all_btn = ttk.Button(outer, text=t("deps.btn.update_all"), command=_update_all)
        update_all_btn.pack(anchor=tk.W, pady=(0, 8))

        # --- Log area ---
        log_frame = ttk.LabelFrame(outer, text=t("deps.output"), padding=4)
        log_frame.pack(fill=tk.BOTH, expand=True)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED,
                           font=("Consolas", 9))
        log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, command=log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        log_text.configure(yscrollcommand=log_scroll.set)

        ttk.Button(outer, text=t("deps.btn.close"), command=win.destroy).pack(anchor=tk.E, pady=(6, 0))

        # Populate the current installed version for every row on open
        for _name, _pkg in DEPS:
            _refresh_version(_pkg, _name)

    def _save_theme_to_env(self, theme):
        """
        Save theme preference to .env file.
        """
        import os
        from dotenv import set_key

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

    def _sanitize_font_entry(self, *_args):
        """
        Keep the font entry to at most two digits.

        CTkEntry offers no ``validatecommand``, so instead of rejecting
        keystrokes we strip anything invalid right after it is written to the
        variable. The guard flag prevents the trace from recursing when this
        method writes the corrected value back.
        """
        if getattr(self, "_sanitizing_font_entry", False):
            return
        raw = self.font_size_var.get()
        cleaned = "".join(ch for ch in raw if ch.isdigit())[:2]
        if cleaned != raw:
            self._sanitizing_font_entry = True
            try:
                self.font_size_var.set(cleaned)
            finally:
                self._sanitizing_font_entry = False

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

        sizes = font_sizes(fs)

        # Scale every label, checkbox, dropdown and button across the app.
        # Without this pass those widgets keep CustomTkinter's fixed size 13
        # forever, so at larger font settings the field labels ("Burn mode",
        # "Provider", "Prompt preset", ...) looked far too small next to the
        # text they describe.
        apply_font_scale(self.root, fs)

        # Title label stays bold and clearly above everything else
        if hasattr(self, "title_label"):
            self.title_label.configure(
                font=ctk.CTkFont(size=sizes["title"], weight="bold")
            )

        # Tab strip buttons (CTkNotebook is not styled by ttk.Style)
        if hasattr(self, "notebook") and hasattr(self.notebook, "set_tab_font"):
            self.notebook.set_tab_font(ctk.CTkFont(size=sizes["label"]))

        # Per-tab text areas.
        #
        # Every tab is now CustomTkinter and owns its own typography via
        # apply_font_size(), because they mix monospace document panes with
        # UI-font metadata boxes - something a single font for every widget
        # cannot express. The getattr/callable guards keep this safe if a tab
        # is ever added without the hook.
        for tab_attr in (
            "summarizer_tab", "transcriber_tab", "translation_tab",
            "bulk_summarizer_tab", "bulk_transcriber_tab", "downloader_tab",
            "video_subtitler_tab",
        ):
            tab = getattr(self, tab_attr, None)
            hook = getattr(tab, "apply_font_size", None) if tab else None
            if callable(hook):
                hook(fs)
            elif tab is not None:
                logger.debug(f"{tab_attr} has no apply_font_size hook")

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
        # The notebook already knows which widget is showing, so ask it rather
        # than mapping hardcoded indices to attributes - that mapping silently
        # returned the wrong tab the moment the display order changed.
        return self.notebook.select()
