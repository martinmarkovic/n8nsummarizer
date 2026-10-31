"""
Summarizer Tab - Unified File and YouTube Summarization Interface

Replaces file_tab.py and youtube_summarizer_tab.py with a single tab that handles
both file and YouTube input modes and sends directly to any OpenAI-compatible
LLM webhook (LM Studio, Ollama, vLLM, etc.) without going through n8n.

Features:
- Dual input modes: File upload or YouTube URL
- Direct LLM webhook integration (no n8n dependency)
- Prompt preset selection with custom editing
- Content preview and response display
- Export functionality (txt, docx, copy)
- Configuration persistence to .env
- Progress indicators and status updates

Version: 2.0
Created: 2026-05-06
Updated: 2026-10-30 - Migrated from ttk to CustomTkinter (first tab of the
    incremental UI migration). The public interface is unchanged: every getter,
    setter and callback consumed by SummarizerController and BulkSummarizerTab
    behaves exactly as before.

Widget notes for future migration work:
- CTk widgets reject ``.config()``; always use ``.configure()``.
- Read-only dropdowns are CTkOptionMenu (not Combobox), so selection is handled
  with a ``command=`` callback instead of a ``<<ComboboxSelected>>`` binding.
- CTkTextbox has built-in scrollbars, so the manual Scrollbar wiring is gone.
"""

import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, Dict, Any, List

import customtkinter as ctk

from config import LLM_WEBHOOK_URL, LLM_MODEL, LLM_PROVIDER, PROVIDER_CONFIG
from utils.prompt_presets import PROMPT_PRESETS, PRESET_NAMES, DEFAULT_PROMPT_KEY
from utils.prompt_manager import PromptManager
from utils.logger import logger
from models.llm_client.discovery import discover_models, ModelOption
from views.base_tab import CTkBaseTab
from views.ctk_compat import CTkSection, CTkCollapsibleSection, CTkSplitter
from utils.i18n import t

# Colors for the connection status dot, as (light_mode, dark_mode) pairs so the
# dot stays legible in both appearance modes.
_STATUS_COLORS = {
    "ok": ("#15803d", "#4ade80"),
    "error": ("#b91c1c", "#f87171"),
    "pending": ("#b45309", "#fbbf24"),
}


class SummarizerTab(CTkBaseTab):
    """
    Unified summarizer tab that replaces file_tab.py and youtube_summarizer_tab.py.

    Handles both file and YouTube input modes and sends content directly to
    OpenAI-compatible LLM webhooks instead of using n8n workflows.
    """

    def __init__(self, parent, prompt_manager=None, settings_manager=None):
        """
        Initialize Summarizer tab.

        Args:
            parent: Parent widget (the notebook)
            prompt_manager: Optional PromptManager instance for managing prompts
            settings_manager: Optional SettingsManager instance for persistent preferences
        """
        # Initialize variables BEFORE calling super().__init__()
        # Input mode - restored from persisted settings when available so the
        # tab reopens on whichever mode (file / youtube) was last used.
        initial_mode = "file"
        if settings_manager is not None:
            initial_mode = settings_manager.get_summarizer_input_mode()
        self.input_mode_var = tk.StringVar(value=initial_mode)  # "file" or "youtube"

        # File mode state
        self.file_path_var = tk.StringVar(value=t("summarizer.no_file"))
        self.current_file_directory = None
        self.current_file_basename = None

        # YouTube mode state
        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value=".txt")

        # LLM settings
        self.provider_var = tk.StringVar(value=LLM_PROVIDER or "lmstudio")
        self.webhook_var = tk.StringVar(value=LLM_WEBHOOK_URL or "http://127.0.0.1:1234/v1")
        self.model_var = tk.StringVar(value=LLM_MODEL or "local-model")
        self.save_settings_var = tk.BooleanVar(value=True)  # Automatic saving

        # Clean up any existing corrupted model name from .env
        self._cleanup_model_name()

        # Model discovery state
        self.available_models: List[ModelOption] = []
        self.models_status = tk.StringVar(value="")
        self.models_error = tk.StringVar(value="")
        self.status_indicator = None  # Will be set in _setup_ui

        # Model ID to label mapping for display purposes
        self._model_id_mapping = {}  # label -> id
        self._model_display_mapping = {}  # id -> label

        # Prompt management
        self.prompt_manager = prompt_manager
        self._last_valid_preset = DEFAULT_PROMPT_KEY

        # Settings management
        self.settings = settings_manager

        # Prompt
        self.prompt_preset_var = tk.StringVar(value=DEFAULT_PROMPT_KEY)
        # self.prompt_text widget created in _setup_ui

        # Export preferences
        self.use_original_location_var = tk.BooleanVar(value=False)
        self.auto_export_txt_var = tk.BooleanVar(value=False)
        self.auto_export_docx_var = tk.BooleanVar(value=False)

        # Loading state
        self._loading = False

        # Call parent init (triggers _setup_ui)
        super().__init__(parent, "📝 Summarizer")

        # Callbacks set by controller
        self.on_file_selected = None
        self.on_send_clicked = None
        self.on_export_txt = None
        self.on_export_docx = None
        self.on_copy_clicked = None
        self.on_clear_clicked = None
        # Called with the response text when "Send to Translation tab" is picked.
        # Wired in main.py to set the Translation tab's source box and switch tabs.
        self.on_send_to_translation = None

        logger.info("SummarizerTab initialized - unified file/YouTube summarization with LLM")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    # Below this window width the two top cards stack vertically instead of
    # sitting side by side.
    _STACK_BREAKPOINT = 1100

    def _setup_ui(self):
        """
        Setup the complete UI.

        Layout (rows of the tab itself):
            0  top cards: input + file info (side by side, stacking when narrow)
            1  LLM settings (collapsible, so it can get out of the way)
            2  content / response split  <- the expanding region
            3  action bar
            4  progress bar (only gridded while working)
        """
        # Content goes in self.body (the scroll-when-needed area from
        # CTkBaseTab), not self, so short windows can still reach everything.
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(2, weight=1)  # Content/response split expands

        # Responsive state must exist before any layout runs: _place_file_info
        # reads it. Starts wide, then the first <Configure> corrects it.
        self._stacked = False

        self._setup_top_row()
        self._setup_settings_section()
        self._setup_content_response_section()
        self._setup_action_bar()

        # Initialize mode visibility
        self._on_mode_changed()

        # Responsive: restack the top cards as the window width changes.
        self.bind("<Configure>", self._on_resize)

        # Trigger initial model discovery
        self.after(100, self._discover_models)

        logger.debug("SummarizerTab UI setup complete")

    def _on_resize(self, _event=None):
        """Re-evaluate the responsive layout after a resize settles."""
        self.after_idle(self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        """
        Stack the input and file-info cards vertically on narrow windows.

        A fixed two-column grid squeezes both cards into unusable slivers when
        the window is small, which is exactly what makes a layout feel rigid.
        """
        width = self.winfo_width()
        if width <= 1:
            # Not realized yet (or currently hidden): fall back to the window
            # width so the first paint is not stuck on the wide layout.
            width = self.winfo_toplevel().winfo_width()
        if width <= 1:
            return
        stacked = width < self._STACK_BREAKPOINT
        if stacked == self._stacked:
            return
        self._stacked = stacked
        self._top_row.grid_columnconfigure(1, weight=0 if stacked else 1)
        self._place_file_info()

    def _place_file_info(self):
        """
        Position (or hide) the file-info card.

        Both the responsive layout and the input-mode toggle want a say here,
        so this is the single owner of that card's geometry. It has to be,
        because grid_configure() on a grid_remove()d widget does not bring the
        widget back - the two callers would otherwise silently fight.
        """
        if self.input_mode_var.get() != "file":
            self._file_info_section.grid_remove()
            return

        if self._stacked:
            self._file_info_section.grid(
                row=1, column=0, sticky="ew", padx=0, pady=(10, 0)
            )
        else:
            self._file_info_section.grid(
                row=0, column=1, sticky="new", padx=(10, 0), pady=0
            )

    def _setup_top_row(self):
        """Container for the input and file-info cards."""
        self._top_row = ctk.CTkFrame(self.body, fg_color="transparent")
        self._top_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._top_row.grid_columnconfigure(0, weight=1)
        self._top_row.grid_columnconfigure(1, weight=1)

        self._setup_input_section()
        self._setup_file_info_section()

    def _setup_input_section(self):
        """Setup input section with file/YouTube mode selection."""
        section = CTkSection(self._top_row, title=t("summarizer.frame.input"))
        section.grid(row=0, column=0, sticky="new")
        input_frame = section.body
        self._input_section = section
        input_frame.grid_columnconfigure(0, weight=1)

        # Mode selection: a segmented control is the modern idiom for a small
        # set of mutually exclusive choices, and it reads far better than two
        # loose radio buttons.
        self._mode_labels = {
            t("summarizer.radio.file"): "file",
            t("summarizer.radio.video_url"): "youtube",
        }
        self._mode_values = {v: k for k, v in self._mode_labels.items()}

        self.mode_selector = ctk.CTkSegmentedButton(
            input_frame,
            values=list(self._mode_labels.keys()),
            command=self._on_mode_selected,
            height=32,
            font=ctk.CTkFont(size=13),
        )
        self.mode_selector.grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.mode_selector.set(self._mode_values[self.input_mode_var.get()])

        # --- File mode frame ---
        self._file_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        self._file_frame.grid_columnconfigure(0, weight=1)

        # The chosen path gets its own full-width row so long paths stay
        # readable instead of being crushed between a label and a button.
        self.file_path_label = ctk.CTkLabel(
            self._file_frame,
            textvariable=self.file_path_var,
            anchor="w",
            justify="left",
            fg_color=("gray88", "gray24"),
            corner_radius=8,
            height=34,
            padx=10,
        )
        self.file_path_label.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            self._file_frame,
            text=t("summarizer.btn.browse"),
            command=self._browse_file,
            width=100,
            height=34,
        ).grid(row=0, column=1, padx=(8, 0))

        self._file_frame.grid(row=1, column=0, sticky="ew")

        # --- YouTube mode frame ---
        self._youtube_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        self._youtube_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            self._youtube_frame,
            textvariable=self.url_var,
            height=34,
            placeholder_text="https://",
        )
        self.url_entry.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.url_var.set("https://")
        self._register_entry_context_menu(self.url_entry)

        # Format + re-transcribe sit together on one compact row.
        options_row = ctk.CTkFrame(self._youtube_frame, fg_color="transparent")
        options_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        ctk.CTkLabel(
            options_row,
            text=t("summarizer.lbl.format"),
            text_color=("gray40", "gray65"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.format_combo = ctk.CTkOptionMenu(
            options_row,
            variable=self.format_var,
            values=[".txt", ".srt", ".vtt", ".json"],
            width=100,
            height=30,
        )
        self.format_combo.grid(row=0, column=1, sticky="w")

        self.force_retranscribe_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            self._youtube_frame,
            text=t("summarizer.chk.force_retranscribe"),
            variable=self.force_retranscribe_var,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

        self._youtube_frame.grid(row=1, column=0, sticky="ew")

    def _settings_expanded_default(self) -> bool:
        """Whether the LLM settings panel starts expanded (persisted)."""
        if self.settings is None:
            return True
        return self.settings.get("SUMMARIZER_SETTINGS_EXPANDED", "true").lower() != "false"

    def _on_settings_toggled(self, expanded: bool):
        """Remember whether the user keeps the settings panel open."""
        if self.settings is not None:
            self.settings.set(
                "SUMMARIZER_SETTINGS_EXPANDED", "true" if expanded else "false"
            )

    def _on_mode_selected(self, label: str):
        """Translate a segmented-button label back into the mode value."""
        mode = self._mode_labels.get(label)
        if mode and mode != self.input_mode_var.get():
            self.input_mode_var.set(mode)
            self._on_mode_changed()

    def _on_mode_changed(self):
        """Handle input mode changes (file <-> YouTube)."""
        mode = self.input_mode_var.get()
        if mode == "file":
            self._file_frame.grid()
            self._youtube_frame.grid_remove()
        else:
            self._youtube_frame.grid()
            self._file_frame.grid_remove()

        # The file-info card is shown only in file mode; _place_file_info owns
        # its geometry so this stays consistent with the responsive layout.
        self._place_file_info()

        # Keep the segmented control in sync when the mode is changed
        # programmatically (e.g. restored from settings).
        if hasattr(self, "mode_selector"):
            label = self._mode_values.get(mode)
            if label and self.mode_selector.get() != label:
                self.mode_selector.set(label)

        # Persist the choice so the tab reopens in the same mode next launch.
        if self.settings is not None:
            self.settings.set_summarizer_input_mode(mode)

        logger.debug(f"Input mode changed to: {mode}")

    def _setup_file_info_section(self):
        """Setup file information display section."""
        section = CTkSection(self._top_row, title=t("summarizer.frame.file_info"))
        # Geometry is managed by _place_file_info (responsive + mode aware).
        self._file_info_section = section
        # Kept for backwards compatibility with any code referencing the frame
        self.file_info_frame = section

        section.body.grid_rowconfigure(0, weight=1)

        # CTkTextbox brings its own scrollbar, so no manual Scrollbar needed.
        self.info_text = ctk.CTkTextbox(
            section.body,
            wrap="word",
            height=96,
            activate_scrollbars=True,
            fg_color="transparent",
            font=("Segoe UI", 12),
        )
        self.info_text.grid(row=0, column=0, sticky="nsew")

        # Initial content
        self.info_text.insert("1.0", t("summarizer.no_file"))
        self.info_text.configure(state="disabled")

    def _setup_settings_section(self):
        """Setup LLM settings section."""
        # Collapsible: this panel is configured once in a while but otherwise
        # just steals vertical space from the content/response area.
        section = CTkCollapsibleSection(
            self.body,
            title=t("summarizer.frame.settings"),
            expanded=self._settings_expanded_default(),
            on_toggle=self._on_settings_toggled,
        )
        section.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        settings_frame = section.body
        self._settings_section = section

        settings_frame.grid_columnconfigure(1, weight=1)

        # --- Provider selection ---
        row = 0
        ctk.CTkLabel(settings_frame, text=t("summarizer.lbl.provider")).grid(
            row=row, column=0, sticky="w", pady=2
        )

        provider_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        provider_frame.grid(row=row, column=1, sticky="w", pady=2)

        ctk.CTkRadioButton(
            provider_frame,
            text="LM Studio",
            value="lmstudio",
            variable=self.provider_var,
            command=self._on_provider_changed,
            radiobutton_width=18,
            radiobutton_height=18,
        ).grid(row=0, column=0, padx=(0, 12))

        ctk.CTkRadioButton(
            provider_frame,
            text="Unsloth Local",
            value="unsloth",
            variable=self.provider_var,
            command=self._on_provider_changed,
            radiobutton_width=18,
            radiobutton_height=18,
        ).grid(row=0, column=1, padx=(0, 12))

        ctk.CTkRadioButton(
            provider_frame,
            text="Ollama Local",
            value="ollama-local",
            variable=self.provider_var,
            command=self._on_provider_changed,
            radiobutton_width=18,
            radiobutton_height=18,
        ).grid(row=0, column=2, padx=(0, 12))

        # --- Status indicator ---
        row += 1
        status_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        status_frame.grid(row=row, column=0, columnspan=4, sticky="w", pady=2)

        # Connection state dot: red/amber/green is semantic, so it opts out of
        # the accent palette pass (see _set_status_dot).
        self.status_indicator = ctk.CTkLabel(status_frame, text="●", width=14)
        self.status_indicator._theme_skip = True
        self.status_indicator._font_skip = True  # glyph, not text
        self.status_indicator.grid(row=0, column=0, padx=(0, 5))

        self.status_label = ctk.CTkLabel(status_frame, textvariable=self.models_status)
        self.status_label.grid(row=0, column=1, sticky="w")

        # --- Base URL ---
        row += 1
        ctk.CTkLabel(settings_frame, text=t("summarizer.lbl.base_url")).grid(
            row=row, column=0, sticky="w", pady=2
        )
        self.webhook_entry = ctk.CTkEntry(settings_frame, textvariable=self.webhook_var)
        self.webhook_entry.grid(row=row, column=1, sticky="ew", padx=6, pady=2)
        self._register_entry_context_menu(self.webhook_entry)

        ctk.CTkButton(
            settings_frame,
            text=t("summarizer.btn.test"),
            command=self._test_connection,
            width=70,
        ).grid(row=row, column=2, padx=5, pady=2)

        ctk.CTkCheckBox(
            settings_frame,
            text=t("summarizer.chk.remember"),
            variable=self.save_settings_var,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=row, column=3, sticky="w", padx=5, pady=2)

        # --- Model name ---
        row += 1
        ctk.CTkLabel(settings_frame, text=t("summarizer.lbl.model")).grid(
            row=row, column=0, sticky="w", pady=2
        )
        self.model_combo = ctk.CTkOptionMenu(
            settings_frame,
            values=[],
            command=self._on_model_selected,
        )
        self.model_combo.grid(row=row, column=1, sticky="ew", padx=6, pady=2)
        # Show whatever is currently configured until discovery replaces it
        if self.model_var.get():
            self.model_combo.set(self.model_var.get())

        # --- Prompt preset ---
        row += 1
        ctk.CTkLabel(settings_frame, text=t("summarizer.lbl.prompt_preset")).grid(
            row=row, column=0, sticky="w", pady=2
        )
        self.prompt_combo = ctk.CTkOptionMenu(
            settings_frame,
            variable=self.prompt_preset_var,
            values=[],
            command=self._on_preset_selected,
            width=280,
        )
        self.prompt_combo.grid(row=row, column=1, sticky="w", padx=6, pady=2)
        self._bind_right_click(self.prompt_combo, self._on_preset_combo_rightclick)
        self._last_valid_preset = DEFAULT_PROMPT_KEY

        # Visible delete button for custom presets (enabled only for custom ones)
        self.delete_preset_btn = ctk.CTkButton(
            settings_frame,
            text="🗑",
            width=36,
            command=self._delete_custom_prompt,
        )
        self.delete_preset_btn.grid(row=row, column=2, sticky="w", padx=(0, 5), pady=2)

        # --- Prompt text area ---
        row += 1
        self.prompt_text = ctk.CTkTextbox(
            settings_frame,
            height=104,
            wrap="word",
            activate_scrollbars=True,
            corner_radius=8,
            font=("Segoe UI", 12),
        )
        self.prompt_text.grid(row=row, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        self.prompt_text.bind("<Button-3>", self._on_prompt_text_rightclick)

        # Load presets using prompt_manager if available
        names = self.prompt_manager.get_names() if self.prompt_manager else PRESET_NAMES
        default_key = (
            self.prompt_manager.get_default() if self.prompt_manager else DEFAULT_PROMPT_KEY
        )
        default_prompt = (
            self.prompt_manager.get_prompt(default_key)
            if self.prompt_manager
            else PROMPT_PRESETS[DEFAULT_PROMPT_KEY]
        )

        self.prompt_combo.configure(values=list(names))
        self.prompt_preset_var.set(default_key)
        self.prompt_text.insert("1.0", default_prompt)
        self._update_delete_btn_state()

    def _setup_content_response_section(self):
        """Setup content preview and response display sections."""
        # A draggable splitter instead of a hard 50/50 grid, so the user can
        # give the preview or the response more room as needed.
        self._split = CTkSplitter(self.body, ratio=0.5)
        self._split.grid(row=2, column=0, sticky="nsew")

        # --- Content preview (left) ---
        preview_section = CTkSection(
            self._split.left, title=t("summarizer.frame.content_preview"), padding=10
        )
        preview_section.grid(row=0, column=0, sticky="nsew")
        self._split.left.grid_rowconfigure(0, weight=1)
        self._split.left.grid_columnconfigure(0, weight=1)
        preview_section.body.grid_rowconfigure(0, weight=1)
        self._preview_section = preview_section

        self.content_text = ctk.CTkTextbox(
            preview_section.body,
            wrap="word",
            font=("Cascadia Mono", 12),
            activate_scrollbars=True,
            corner_radius=8,
        )
        self.content_text.grid(row=0, column=0, sticky="nsew")

        from views.context_menu import AppContextMenu
        content_menu = AppContextMenu(self.content_text)
        content_menu.add_copy_command()
        content_menu.add_paste_command()
        content_menu.add_separator()
        content_menu.add_tts_read_command(lambda: self._selection_or_all(self.content_text))
        content_menu.add_tts_stop_command()
        content_menu.add_separator()
        content_menu.add_fullscreen_command(
            title=t("summarizer.frame.content_preview"), editable=True
        )
        content_menu.bind()

        # --- Response display (right) ---
        response_section = CTkSection(
            self._split.right, title=t("summarizer.frame.response"), padding=10
        )
        response_section.grid(row=0, column=0, sticky="nsew")
        self._split.right.grid_rowconfigure(0, weight=1)
        self._split.right.grid_columnconfigure(0, weight=1)
        response_section.body.grid_rowconfigure(0, weight=1)
        self._response_section = response_section

        self.response_text = ctk.CTkTextbox(
            response_section.body,
            wrap="word",
            font=("Cascadia Mono", 12),
            activate_scrollbars=True,
            corner_radius=8,
        )
        self.response_text.grid(row=0, column=0, sticky="nsew")
        # Read-only, but still selectable so TTS can read from a selection
        self._make_readonly_selectable(self.response_text)

        # Single consolidated context menu: copy/clear + TTS + fullscreen
        menu = AppContextMenu(self.response_text)
        menu.add_command(t("summarizer.menu.copy_all"), self._copy_all_response)
        menu.add_command(t("summarizer.menu.clear"), self._clear_response)
        menu.add_separator()
        menu.add_command(t("summarizer.menu.send_to_translation"), self._send_to_translation)
        menu.add_separator()
        menu.add_tts_read_command(lambda: self._selection_or_all(self.response_text))
        menu.add_tts_stop_command()
        menu.add_separator()
        menu.add_fullscreen_command(title=t("summarizer.frame.response"), editable=False)
        menu.bind()

        # Initial response content
        self._set_readonly_text(self.response_text, t("summarizer.text.get_started"))

    def _setup_action_bar(self):
        """Setup action bar with buttons and export controls."""
        action_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        action_frame.grid_columnconfigure(1, weight=1)

        # Summarize button - the primary action, so it gets real visual weight.
        self.send_btn = ctk.CTkButton(
            action_frame,
            text=t("summarizer.btn.summarize"),
            command=self._send_clicked,
            width=170,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.send_btn.grid(row=0, column=0, padx=(0, 10))

        # Export controls frame
        export_controls_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        export_controls_frame.grid(row=0, column=1, sticky="w")

        col = 0
        ctk.CTkCheckBox(
            export_controls_frame,
            text=t("summarizer.chk.use_original_location"),
            variable=self.use_original_location_var,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=0, column=col, padx=5)
        col += 1

        ctk.CTkCheckBox(
            export_controls_frame,
            text=t("summarizer.chk.auto_txt"),
            variable=self.auto_export_txt_var,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=0, column=col, padx=5)
        col += 1

        ctk.CTkCheckBox(
            export_controls_frame,
            text=t("summarizer.chk.auto_docx"),
            variable=self.auto_export_docx_var,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=0, column=col, padx=5)
        col += 1

        ctk.CTkLabel(export_controls_frame, text=t("summarizer.lbl.export")).grid(
            row=0, column=col, padx=(12, 4)
        )
        col += 1

        self.export_txt_btn = ctk.CTkButton(
            export_controls_frame,
            text="📄 .txt",
            command=self._export_txt_clicked,
            state="disabled",
            width=80,
        )
        self.export_txt_btn.grid(row=0, column=col, padx=2)
        col += 1

        self.export_docx_btn = ctk.CTkButton(
            export_controls_frame,
            text="📝 .docx",
            command=self._export_docx_clicked,
            state="disabled",
            width=90,
        )
        self.export_docx_btn.grid(row=0, column=col, padx=2)
        col += 1

        self.copy_btn = ctk.CTkButton(
            export_controls_frame,
            text=t("summarizer.btn.copy"),
            command=self._copy_clicked,
            state="disabled",
            width=90,
        )
        self.copy_btn.grid(row=0, column=col, padx=2)

        # Clear button
        # Secondary/destructive action: present but visually quiet.
        self.clear_btn = ctk.CTkButton(
            action_frame,
            text=t("summarizer.btn.clear_all"),
            command=self._clear_clicked,
            width=110,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
        )
        self.clear_btn.grid(row=0, column=2, padx=(10, 0))

        # Progress bar (created but not visible initially)
        self.progress = ctk.CTkProgressBar(self.body, mode="indeterminate", height=6)

    # ------------------------------------------------------------------
    # Small widget helpers
    # ------------------------------------------------------------------

    def _bind_right_click(self, widget, handler):
        """
        Bind right-click on a CustomTkinter composite widget.

        CTk widgets forward ``bind`` to an internal canvas, so a right-click on
        the text label part of an option menu can be missed. Bind the wrapper
        and its known internals, ignoring any that are absent.
        """
        targets = [widget]
        for attr in ("_canvas", "_text_label"):
            inner = getattr(widget, attr, None)
            if inner is not None:
                targets.append(inner)
        for target in targets:
            try:
                target.bind("<Button-3>", handler)
            except Exception:
                logger.debug(f"Could not bind right-click on {target!r}", exc_info=True)

    def _set_status_dot(self, state: str):
        """Color the connection status dot: 'ok', 'error' or 'pending'."""
        if self.status_indicator is None:
            return
        self.status_indicator.configure(
            text_color=_STATUS_COLORS.get(state, _STATUS_COLORS["pending"])
        )

    def _make_readonly_selectable(self, widget):
        """
        Make a text widget read-only while still allowing selection and copy.

        A widget with state="disabled" cannot be selected with the mouse, which
        would break selection-based TTS. Instead we keep it enabled and block
        edit keystrokes, allowing navigation, selection, and copy/select-all.
        """
        def _block_edit(event):
            # Allow Ctrl/Command shortcuts (copy, select-all, etc.)
            if event.state & 0x4:  # Control held
                return
            # Allow navigation keys
            if event.keysym in (
                "Left", "Right", "Up", "Down", "Home", "End",
                "Prior", "Next", "Shift_L", "Shift_R", "Control_L", "Control_R",
            ):
                return
            return "break"  # Block everything else (typing/deleting)

        widget.bind("<Key>", _block_edit)
        # Block paste and cut explicitly
        widget.bind("<<Paste>>", lambda e: "break")
        widget.bind("<<Cut>>", lambda e: "break")

    def _set_readonly_text(self, widget, text):
        """Replace the content of a read-only-selectable text widget."""
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)

    # ------------------------------------------------------------------
    # LLM provider / model discovery
    # ------------------------------------------------------------------

    def _on_provider_changed(self):
        """Handle provider selection changes."""
        provider = self.provider_var.get()
        config = PROVIDER_CONFIG.get(provider)

        if config:
            # Update base URL to provider default
            self.webhook_var.set(config["default_base_url"])

            # Clear current model selection
            self.model_var.set("")
            self.model_combo.configure(values=[])
            self.model_combo.set("")

            # Trigger model discovery
            self._discover_models()

    def _test_connection(self):
        """Test connection to LLM server and discover models."""
        self._discover_models()

    def _discover_models(self):
        """Discover available models from current provider."""
        provider = self.provider_var.get()
        base_url = self.webhook_var.get().strip()

        if not provider or not base_url:
            self.models_status.set(t("summarizer.status.need_provider"))
            self._set_status_dot("error")
            return

        # Show loading state
        self.models_status.set(t("summarizer.status.connecting"))
        self._set_status_dot("pending")
        self.update_idletasks()

        # Run discovery in background to avoid UI freeze
        def discovery_task():
            try:
                models, status, error = discover_models(provider, base_url)
                self.after(0, lambda: self._update_models_ui(models, status, error))
            except Exception as e:
                self.after(0, lambda: self._update_models_ui([], "error", str(e)))

        threading.Thread(target=discovery_task, daemon=True).start()

    def _update_models_ui(self, models, status, error):
        """Update UI with model discovery results."""
        self.available_models = models

        # Update status indicator
        if status == "ok":
            self.models_status.set(t("summarizer.status.connected"))
            self._set_status_dot("ok")
            self.models_error.set("")
        elif status == "error":
            self.models_status.set(t("summarizer.status.unreachable"))
            self._set_status_dot("error")
            self.models_error.set(error or "Unknown error")
        else:
            self.models_status.set(t("summarizer.status.connecting"))
            self._set_status_dot("pending")

        # Update model dropdown
        if models:
            self._model_id_mapping = {m["label"]: m["id"] for m in models}
            self._model_display_mapping = {m["id"]: m["label"] for m in models}

            model_labels = [m["label"] for m in models]
            self.model_combo.configure(values=model_labels)

            # Select first model if none selected (store the ID, show the label)
            current_id = self.model_var.get()
            if not current_id:
                self.model_var.set(models[0]["id"])
                self.model_combo.set(models[0]["label"])
            else:
                # Show the friendly label for the already-configured model
                self.model_combo.set(
                    self._model_display_mapping.get(current_id, current_id)
                )
        else:
            self.model_combo.configure(values=[])
            self.model_combo.set("")
            self.model_var.set("")

    def _on_model_selected(self, selected_label: str):
        """
        Handle model selection from the dropdown.

        The dropdown shows friendly labels (``name (size)``) while the rest of
        the app needs the bare model ID, so translate before storing.
        """
        selected_label = (selected_label or "").strip()
        if not selected_label:
            return

        if selected_label in self._model_id_mapping:
            model_id = self._model_id_mapping[selected_label]
            logger.info(f"Converted model label to ID: '{selected_label}' -> '{model_id}'")
            self.model_var.set(model_id)
        else:
            # Already an ID, or unknown - use as-is
            self.model_var.set(selected_label)

    def _on_model_combobox_selected(self, event=None):
        """Backwards-compatible alias for the old Combobox event handler."""
        self._on_model_selected(self.model_combo.get())

    # ------------------------------------------------------------------
    # Prompt presets
    # ------------------------------------------------------------------

    def _on_preset_selected(self, _value=None):
        """CTkOptionMenu command callback for the preset dropdown."""
        self._on_preset_changed()
        self._update_delete_btn_state()

    def _on_preset_changed(self, event=None):
        """Handle prompt preset selection changes."""
        key = self.prompt_preset_var.get()
        if key == PromptManager.SEPARATOR:
            self.prompt_preset_var.set(self._last_valid_preset)
            return
        self._last_valid_preset = key
        if self.prompt_manager:
            text = self.prompt_manager.get_prompt(key)
            # Save the selected preset as the new default
            self.prompt_manager.set_default(key)
        else:
            text = PROMPT_PRESETS.get(key, "")
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", text)
        logger.debug(f"Prompt preset changed to: {key}")

    def _reload_presets(self):
        """Reload prompt presets into dropdown"""
        if not self.prompt_manager:
            return
        names = list(self.prompt_manager.get_names())
        self.prompt_combo.configure(values=names)
        current = self.prompt_preset_var.get()
        if current not in names or current == PromptManager.SEPARATOR:
            fallback = self.prompt_manager.get_default()
            self.prompt_preset_var.set(fallback)
            self._last_valid_preset = fallback
            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.insert("1.0", self.prompt_manager.get_prompt(fallback))
        self._update_delete_btn_state()

    def _speak_text(self, text):
        """
        Speak text using pyttsx3 TTS.

        Args:
            text: Text to speak
        """
        from utils import tts_engine_pyttsx3
        tts_engine_pyttsx3.speak(text)

    def _on_prompt_text_rightclick(self, event):
        """Handle right-click on prompt textbox (Copy/Paste + Save as prompt)."""
        menu = tk.Menu(self, tearoff=0)

        def _paste():
            self.prompt_text.focus_set()
            self.prompt_text.event_generate("<<Paste>>")

        def _copy():
            self.prompt_text.event_generate("<<Copy>>")

        menu.add_command(label=t("summarizer.menu.paste"), command=_paste)
        menu.add_command(label=t("summarizer.menu.copy"), command=_copy)
        if self.prompt_manager:
            menu.add_separator()
            menu.add_command(
                label=t("summarizer.menu.save_prompt"), command=self._save_prompt_as_custom
            )
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    def _save_prompt_as_custom(self):
        """Save current prompt text as a custom prompt"""
        if not self.prompt_manager:
            return
        text = self.prompt_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning(
                t("summarizer.msg.empty_prompt_title"), t("summarizer.msg.empty_prompt_body")
            )
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(t("summarizer.dialog.save_prompt_title"))
        dialog.resizable(False, False)
        dialog.geometry("380x150")
        # Let the window appear before grabbing input, otherwise the grab can
        # fail on Windows while the toplevel is still being mapped.
        dialog.after(100, dialog.grab_set)

        ctk.CTkLabel(dialog, text=t("summarizer.lbl.preset_name")).grid(
            row=0, column=0, padx=12, pady=14, sticky="w"
        )
        name_var = tk.StringVar()
        name_entry = ctk.CTkEntry(dialog, textvariable=name_var, width=200)
        name_entry.grid(row=0, column=1, padx=12, pady=14)
        name_entry.focus_set()

        def do_save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning(
                    t("summarizer.msg.missing_name_title"),
                    t("summarizer.msg.missing_name_body"),
                    parent=dialog,
                )
                return
            try:
                self.prompt_manager.add_custom(name, text)
                self._reload_presets()
                self.prompt_preset_var.set(name)
                self._last_valid_preset = name
                self._update_delete_btn_state()
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror(t("summarizer.msg.error_title"), str(e), parent=dialog)

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
        ctk.CTkButton(
            btn_frame, text=t("summarizer.btn.save"), command=do_save, width=90
        ).grid(row=0, column=0, padx=5)
        ctk.CTkButton(
            btn_frame,
            text=t("summarizer.btn.cancel"),
            command=dialog.destroy,
            width=90,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
        ).grid(row=0, column=1, padx=5)
        dialog.bind("<Return>", lambda e: do_save())

    def _on_preset_combo_rightclick(self, event):
        """Handle right-click on preset dropdown"""
        if not self.prompt_manager:
            return
        selected = self.prompt_preset_var.get()
        menu = tk.Menu(self, tearoff=0)
        if self.prompt_manager.is_custom(selected):
            menu.add_command(
                label=t("summarizer.menu.delete_prompt"), command=self._delete_custom_prompt
            )
        else:
            menu.add_command(
                label=t("summarizer.menu.cannot_delete_default"), state="disabled"
            )
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    def _delete_custom_prompt(self):
        """Delete a custom prompt"""
        if not self.prompt_manager:
            return
        name = self.prompt_preset_var.get()
        # Guard: only custom presets are deletable
        if not self.prompt_manager.is_custom(name):
            messagebox.showinfo(
                t("summarizer.msg.cannot_delete_title"),
                t("summarizer.msg.cannot_delete_body"),
            )
            return
        if not messagebox.askyesno(
            t("summarizer.msg.delete_prompt_title"),
            t("summarizer.msg.delete_prompt_body").format(name=name),
        ):
            return
        try:
            self.prompt_manager.delete_custom(name)
            self._reload_presets()
            self._update_delete_btn_state()
        except (ValueError, KeyError) as e:
            messagebox.showerror(t("summarizer.msg.error_title"), str(e))

    def _update_delete_btn_state(self, event=None):
        """Enable the delete button only when a deletable custom preset is selected."""
        if not hasattr(self, "delete_preset_btn"):
            return
        name = self.prompt_preset_var.get()
        is_custom = bool(self.prompt_manager and self.prompt_manager.is_custom(name))
        self.delete_preset_btn.configure(state="normal" if is_custom else "disabled")

    # ------------------------------------------------------------------
    # Context menu helpers
    # ------------------------------------------------------------------

    def _copy_all_response(self):
        """Copy all response text to clipboard."""
        content = self.response_text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.update_idletasks()
            self.set_status(t("summarizer.status.copied").format(n=len(content)))

    def _clear_response(self):
        """Clear response text."""
        self._set_readonly_text(self.response_text, t("summarizer.text.response_cleared"))
        self.set_status(t("summarizer.text.response_cleared"))

    def _send_to_translation(self):
        """Send the response text to the Translation tab's Source box and switch to it."""
        text = self.response_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo(
                t("summarizer.msg.nothing_send_title"), t("summarizer.msg.nothing_send_body")
            )
            return

        if callable(self.on_send_to_translation):
            self.on_send_to_translation(text)
            self.set_status(t("summarizer.status.sent_to_translation").format(n=len(text)))
        else:
            logger.warning("on_send_to_translation not wired; cannot forward to Translation tab")
            messagebox.showwarning(
                t("summarizer.msg.unavailable_title"),
                t("summarizer.msg.unavailable_body"),
            )

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _browse_file(self):
        """Browse for file."""
        filetypes = [
            (t("summarizer.filetype.all"), ".*"),  # First entry is the default
            (t("summarizer.filetype.text"), ".txt"),
            (t("summarizer.filetype.subtitle"), ".srt .vtt"),
            (t("summarizer.filetype.json"), ".json"),
            (t("summarizer.filetype.word"), ".docx"),
        ]

        file_path = filedialog.askopenfilename(
            title=t("summarizer.dialog.select_file"), filetypes=filetypes
        )

        if file_path:
            self.set_file_path(file_path)
            if self.on_file_selected:
                self.on_file_selected(file_path)

    def _send_clicked(self):
        """Handle summarize button click."""
        if self.on_send_clicked:
            self.on_send_clicked()

    def _export_txt_clicked(self):
        """Handle export txt button click."""
        if self.on_export_txt:
            self.on_export_txt()

    def _export_docx_clicked(self):
        """Handle export docx button click."""
        if self.on_export_docx:
            self.on_export_docx()

    def _copy_clicked(self):
        """Handle copy button click."""
        if self.on_copy_clicked:
            self.on_copy_clicked()

    def _clear_clicked(self):
        """Handle clear button click."""
        if self.on_clear_clicked:
            self.on_clear_clicked()
        else:
            self.clear_all()

    # ------------------------------------------------------------------
    # Getters
    # ------------------------------------------------------------------

    def get_input_mode(self) -> str:
        """Get current input mode."""
        return self.input_mode_var.get()

    def get_file_path(self) -> Optional[str]:
        """Get selected file path."""
        path = self.file_path_var.get()
        return path if path and path != t("summarizer.no_file") else None

    def get_youtube_url(self) -> str:
        """Get YouTube URL."""
        return self.url_var.get().strip()

    def get_transcription_format(self) -> str:
        """Get transcription format."""
        return self.format_var.get()

    def get_force_retranscribe(self) -> bool:
        """Get force re-transcribe preference."""
        return getattr(self, "force_retranscribe_var", tk.BooleanVar()).get()

    def get_webhook_url(self) -> str:
        """Get webhook URL."""
        return self.webhook_var.get().strip()

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_var.get().strip()

    def get_save_settings(self) -> bool:
        """Get save settings preference."""
        return self.save_settings_var.get()

    def get_provider(self) -> str:
        """Get current provider."""
        return self.provider_var.get()

    def get_prompt(self) -> str:
        """Get current prompt text."""
        return self.prompt_text.get("1.0", tk.END).strip()

    def get_content(self) -> str:
        """Get content text (satisfies CTkBaseTab abstract method)."""
        return self.content_text.get("1.0", tk.END).strip()

    def get_response_content(self) -> str:
        """Get response text."""
        return self.response_text.get("1.0", tk.END).strip()

    def get_export_preferences(self) -> Dict[str, Any]:
        """Get export preferences."""
        return {
            "use_original_location": self.use_original_location_var.get(),
            "auto_export_txt": self.auto_export_txt_var.get(),
            "auto_export_docx": self.auto_export_docx_var.get(),
            "original_directory": self.current_file_directory,
            "original_basename": self.current_file_basename,
        }

    # ------------------------------------------------------------------
    # .env model-name cleanup
    # ------------------------------------------------------------------

    def _clean_env_file(self, old_value: str, new_value: str):
        """Clean up corrupted model name in .env file."""
        try:
            from pathlib import Path
            env_path = Path(__file__).parent.parent / ".env"

            if env_path.exists():
                content = env_path.read_text(encoding="utf-8")

                updated_content = content.replace(
                    f"LLM_MODEL={old_value}", f"LLM_MODEL={new_value}"
                )

                if updated_content != content:
                    env_path.write_text(updated_content, encoding="utf-8")
                    logger.info(
                        f"Cleaned .env file: LLM_MODEL updated from '{old_value}' to '{new_value}'"
                    )
        except Exception as e:
            logger.error(f"Failed to clean .env file: {e}")

    def _cleanup_model_name(self):
        """Clean up corrupted model names that may exist in .env file."""
        current_value = self.model_var.get().strip()
        if not current_value:
            return

        # Pattern: "model-name (size)" - strip the trailing size description
        match = re.match(r"^(.+?)\s+\([^)]+\)$", current_value)
        if match:
            clean_model_name = match.group(1)
            logger.info(
                f"Cleaned up corrupted model name: '{current_value}' -> '{clean_model_name}'"
            )
            self.model_var.set(clean_model_name)
            self._clean_env_file(current_value, clean_model_name)

    # ------------------------------------------------------------------
    # Setters
    # ------------------------------------------------------------------

    def set_file_path(self, path: Optional[str]):
        """Set file path and store directory/basename."""
        if path:
            self.file_path_var.set(path)
            self.current_file_directory = os.path.dirname(path)
            self.current_file_basename = os.path.basename(path)
        else:
            self.file_path_var.set(t("summarizer.no_file"))
            self.current_file_directory = None
            self.current_file_basename = None

    def set_content(self, text: str):
        """Set content text."""
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", text)

    def set_file_info(self, info: Optional[dict]):
        """Set file information display."""
        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", tk.END)

        if info:
            lines = [
                t("summarizer.info.name").format(
                    name=info.get("name", t("summarizer.info.unknown"))
                ),
                t("summarizer.info.size").format(size=info.get("size_kb", 0)),
                t("summarizer.info.lines").format(lines=info.get("lines", 0)),
                t("summarizer.info.type").format(
                    type=info.get("type", t("summarizer.info.unknown"))
                ),
            ]
            self.info_text.insert("1.0", "\n".join(lines))
        else:
            self.info_text.insert("1.0", t("summarizer.no_file"))

        self.info_text.configure(state="disabled")

    def set_status(self, msg: str):
        """Set status message (override TabMixin default)."""
        logger.info(f"SummarizerTab: {msg}")
        # This tab has no status bar of its own; the controller surfaces status
        # through the main window.

    def display_response(self, text: str):
        """Display response text."""
        self._set_readonly_text(self.response_text, text)

    def show_loading(self, show: bool):
        """Show or hide loading indicator."""
        self._loading = show
        if show:
            self.progress.grid(row=4, column=0, sticky="ew", pady=(10, 0))
            self.send_btn.configure(state="disabled")
            self.progress.start()
        else:
            self.progress.stop()
            self.progress.grid_remove()
            self.send_btn.configure(state="normal")

    def set_export_buttons_enabled(self, enabled: bool):
        """Enable or disable export buttons."""
        state = "normal" if enabled else "disabled"
        self.export_txt_btn.configure(state=state)
        self.export_docx_btn.configure(state=state)
        self.copy_btn.configure(state=state)

    # ------------------------------------------------------------------
    # CTkBaseTab abstract method implementations
    # ------------------------------------------------------------------

    def clear_all(self):
        """Reset all UI elements to initial state.

        The input mode (file / youtube) is intentionally left untouched: "Clear
        All" clears content, not the user's chosen input mode, and forcing it
        back to "file" would overwrite the persisted preference.
        """
        # Reset file state
        self.file_path_var.set(t("summarizer.no_file"))
        self.current_file_directory = None
        self.current_file_basename = None

        # Reset YouTube state
        self.url_var.set("https://")

        # Clear content areas
        self.content_text.configure(state="normal")
        self.content_text.delete("1.0", tk.END)

        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", t("summarizer.no_file"))
        self.info_text.configure(state="disabled")

        # Reset response
        self._set_readonly_text(self.response_text, t("summarizer.text.get_started"))

        # Reset export buttons
        self.set_export_buttons_enabled(False)

        # Restore frame visibility for current mode
        self._on_mode_changed()

        self.set_status(t("summarizer.status.cleared_all"))

    # ------------------------------------------------------------------
    # Theming hooks used by MainWindow
    # ------------------------------------------------------------------

    def apply_theme_colors(self, bg: str, fg: str):
        """
        Apply the app's theme colors to this tab's text areas.

        MainWindow calls this instead of setting ``bg``/``fg``/``insertbackground``
        directly, because CTk widgets raise ValueError for those classic Tk
        options and expect ``fg_color`` / ``text_color`` instead.

        This keeps the custom-color feature in Settings working for this tab:
        the textboxes follow the chosen background and text colors, while
        buttons and dropdowns follow CustomTkinter's light/dark theme.
        """
        for textbox in (self.content_text, self.response_text, self.prompt_text):
            try:
                textbox.configure(fg_color=bg, text_color=fg)
            except (ValueError, tk.TclError):
                logger.debug("Could not apply theme colors to textbox", exc_info=True)

        # The file-info box reads as part of its card, so it keeps a
        # transparent background and only takes the text color.
        try:
            self.info_text.configure(text_color=fg)
        except (ValueError, tk.TclError):
            logger.debug("Could not apply theme color to info box", exc_info=True)

        # The caret lives on the inner tk.Text and is not exposed by CTkTextbox.
        from views.ctk_compat import unwrap_text
        for textbox in (self.content_text, self.response_text, self.prompt_text):
            inner = unwrap_text(textbox)
            try:
                inner.configure(insertbackground=fg)
            except tk.TclError:
                logger.debug("Could not set caret color", exc_info=True)

    def apply_font_size(self, size: int):
        """
        Apply the app-wide font size to this tab's text panes.

        Only the text areas are handled here: labels, buttons, dropdowns and
        the section headings are scaled centrally by
        :func:`views.ctk_theme.apply_font_scale`, so this hook stays limited to
        the panes whose font *family* is tab-specific.
        """
        from views.ctk_theme import font_sizes
        sizes = font_sizes(size)

        # Monospace for the document panes (alignment matters for transcripts
        # and subtitles), UI font for the smaller metadata/prompt boxes.
        self.content_text.configure(font=("Cascadia Mono", sizes["mono"]))
        self.response_text.configure(font=("Cascadia Mono", sizes["mono"]))
        self.info_text.configure(font=("Segoe UI", sizes["label"]))
        self.prompt_text.configure(font=("Segoe UI", sizes["label"]))
