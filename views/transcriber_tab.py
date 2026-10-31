"""
Transcriber Tab v3.0 - CustomTkinter

Responsibilities:
    - Display transcription interface
    - Allow local file or YouTube URL input
    - Show output SRT with copy-to-clipboard
    - Output location selection (original vs custom)
    - Export buttons for individual formats
    - File format selection via checkboxes

Connects to TranscriberController for business logic.

Created: 2025-12-07 (v2.3)
Enhanced: 2025-12-07 (v2.4 - Layout and output options)
Updated: 2026-10-30 (v3.0 - Migrated from ttk to CustomTkinter with the
    card-based responsive layout used by the Summarizer tab. The public
    interface consumed by TranscriberController is unchanged.)

Widget notes:
- CTk widgets reject ``.config()``; always use ``.configure()``.
- Mode and device pickers are segmented controls, so their labels are mapped
  back to the values the controller expects via ``_*_labels`` dicts.
"""

import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from views.base_tab import CTkBaseTab
from views.ctk_compat import CTkSection, CTkCollapsibleSection
from utils.i18n import t
from utils.logger import logger


class TranscriberTab(CTkBaseTab):
    """
    Transcriber tab UI for transcribe-anything integration.

    Features:
    - Local file or YouTube URL transcription
    - Device selection
    - SRT transcript display with copy button
    - Output location selection
    - Export buttons for individual formats
    - File format checkboxes
    - Responsive, card-based layout
    """

    # Below this width the two top cards stack instead of sitting side by side.
    _STACK_BREAKPOINT = 1100

    def __init__(self, parent, settings_manager=None):
        """
        Initialize Transcriber tab.

        Args:
            parent: Parent widget (the notebook)
            settings_manager: SettingsManager instance for persistent preferences
        """
        self.settings = settings_manager

        # Initialize variables BEFORE calling super().__init__()
        self.mode_var = tk.StringVar(value="local")
        self.device_var = tk.StringVar(value="cuda")
        self.file_path_var = tk.StringVar()
        self.url_var = tk.StringVar()

        # Load saved output location preference or default to "original"
        default_output_location = "original"
        default_custom_path = ""
        if self.settings:
            default_output_location = self.settings.get_transcriber_output_location()
            default_custom_path = self.settings.get_transcriber_custom_path()

        self.output_location_var = tk.StringVar(value=default_output_location)
        self.output_custom_path_var = tk.StringVar(value=default_custom_path)

        # Output format checkboxes
        self.keep_txt_var = tk.BooleanVar(value=True)
        self.keep_srt_var = tk.BooleanVar(value=True)
        self.keep_vtt_var = tk.BooleanVar(value=False)
        self.keep_json_var = tk.BooleanVar(value=False)
        self.keep_tsv_var = tk.BooleanVar(value=False)

        # Now call parent init (which calls _setup_ui())
        super().__init__(parent, "Transcriber")

        # Callbacks for controller (set after UI is created)
        self.on_file_selected = None
        self.on_transcribe_clicked = None
        self.on_copy_clicked = None
        self.on_export_txt_clicked = None
        self.on_export_srt_clicked = None
        self.on_clear_clicked = None

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """
        Setup transcriber tab UI.

        Layout:
            0  source card + options card (stacking when narrow)
            1  output location (collapsible)
            2  transcript  <- expanding region
            3  action bar
        """
        # Content goes in self.body (the scroll-when-needed area from
        # CTkBaseTab), not self, so short windows can still reach everything.
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(2, weight=1)  # Transcript area expands

        # Responsive state must exist before any layout runs.
        self._stacked = False

        self._setup_top_row()
        self._setup_output_location_section()
        self._setup_output_section()
        self._setup_action_bar()

        # Initial visibility
        self._toggle_input_mode()
        self._toggle_output_location(save=False)

        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _event=None):
        self.after_idle(self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        """Stack the source and options cards on narrow windows."""
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
            self._options_section.grid_configure(
                row=1, column=0, padx=0, pady=(10, 0)
            )
        else:
            self._top_row.grid_columnconfigure(1, weight=1)
            self._options_section.grid_configure(
                row=0, column=1, padx=(10, 0), pady=0
            )

    def _setup_top_row(self):
        """Container for the source and options cards."""
        self._top_row = ctk.CTkFrame(self.body, fg_color="transparent")
        self._top_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._top_row.grid_columnconfigure(0, weight=1)
        self._top_row.grid_columnconfigure(1, weight=1)

        self._setup_source_section()
        self._setup_options_section()

    def _setup_source_section(self):
        """Mode selection plus the matching input widgets."""
        section = CTkSection(self._top_row, title=t("transcriber.frame.input"))
        section.grid(row=0, column=0, sticky="new")
        self._source_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        # Mode: segmented control reads better than two loose radio buttons.
        self._mode_labels = {
            t("transcriber.radio.local_file"): "local",
            "YouTube URL": "youtube",
        }
        self._mode_values = {v: k for k, v in self._mode_labels.items()}

        self.mode_selector = ctk.CTkSegmentedButton(
            body,
            values=list(self._mode_labels.keys()),
            command=self._on_mode_selected,
            height=32,
            font=ctk.CTkFont(size=13),
        )
        self.mode_selector.grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.mode_selector.set(self._mode_values[self.mode_var.get()])

        # --- Local file row ---
        self.local_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.local_frame.grid_columnconfigure(0, weight=1)

        self.file_entry = ctk.CTkEntry(
            self.local_frame,
            textvariable=self.file_path_var,
            height=34,
            placeholder_text=t("transcriber.lbl.file"),
        )
        self.file_entry.grid(row=0, column=0, sticky="ew")
        self._register_entry_context_menu(self.file_entry)

        self.browse_btn = ctk.CTkButton(
            self.local_frame,
            text=t("transcriber.btn.browse"),
            command=self._browse_file,
            width=100,
            height=34,
        )
        self.browse_btn.grid(row=0, column=1, padx=(8, 0))

        self.local_frame.grid(row=1, column=0, sticky="ew")

        # --- YouTube URL row ---
        self.youtube_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.youtube_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            self.youtube_frame,
            textvariable=self.url_var,
            height=34,
            placeholder_text="https://",
        )
        self.url_entry.grid(row=0, column=0, sticky="ew")
        self._register_entry_context_menu(self.url_entry)

        self.youtube_frame.grid(row=1, column=0, sticky="ew")

    def _setup_options_section(self):
        """Device selection and output formats."""
        section = CTkSection(self._top_row, title=t("transcriber.frame.device"))
        # Geometry managed by _apply_responsive_layout.
        section.grid(row=0, column=1, sticky="new", padx=(10, 0))
        self._options_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        self._device_labels = {
            "CPU": "cpu",
            "CUDA (GPU)": "cuda",
            "Insane": "insane",
            "MPS (Mac)": "mps",
        }
        self._device_values = {v: k for k, v in self._device_labels.items()}

        self.device_selector = ctk.CTkSegmentedButton(
            body,
            values=list(self._device_labels.keys()),
            command=self._on_device_selected,
            height=32,
            font=ctk.CTkFont(size=12),
        )
        self.device_selector.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.device_selector.set(self._device_values.get(self.device_var.get(), "CUDA (GPU)"))

        ctk.CTkLabel(
            body,
            text=t("transcriber.frame.output_formats"),
            anchor="w",
            text_color=("gray40", "gray65"),
        ).grid(row=1, column=0, sticky="w", pady=(0, 4))

        formats_row = ctk.CTkFrame(body, fg_color="transparent")
        formats_row.grid(row=2, column=0, sticky="ew")

        for i, (label, var) in enumerate((
            (".txt", self.keep_txt_var),
            (".srt", self.keep_srt_var),
            (".vtt", self.keep_vtt_var),
            (".json", self.keep_json_var),
            (".tsv", self.keep_tsv_var),
        )):
            ctk.CTkCheckBox(
                formats_row,
                text=label,
                variable=var,
                checkbox_width=18,
                checkbox_height=18,
                width=60,
            ).grid(row=0, column=i, sticky="w", padx=(0, 10))

    def _setup_output_location_section(self):
        """Output location, folded away by default when set to 'original'."""
        section = CTkCollapsibleSection(
            self.body,
            title=t("transcriber.frame.output_location"),
            expanded=self.output_location_var.get() == "custom",
        )
        section.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._output_location_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        self._location_labels = {
            t("transcriber.radio.original_location"): "original",
            t("transcriber.radio.custom_destination"): "custom",
        }
        self._location_values = {v: k for k, v in self._location_labels.items()}

        self.location_selector = ctk.CTkSegmentedButton(
            body,
            values=list(self._location_labels.keys()),
            command=self._on_location_selected,
            height=32,
            font=ctk.CTkFont(size=13),
        )
        self.location_selector.grid(row=0, column=0, sticky="w")
        self.location_selector.set(
            self._location_values.get(self.output_location_var.get(),
                                      self._location_values["original"])
        )

        # Custom path row (shown only for the custom destination)
        self.custom_path_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.custom_path_frame.grid_columnconfigure(0, weight=1)

        self.custom_path_entry = ctk.CTkEntry(
            self.custom_path_frame,
            textvariable=self.output_custom_path_var,
            height=34,
            placeholder_text=t("transcriber.lbl.path"),
        )
        self.custom_path_entry.grid(row=0, column=0, sticky="ew")
        self._register_entry_context_menu(self.custom_path_entry)

        self.browse_output_btn = ctk.CTkButton(
            self.custom_path_frame,
            text=t("transcriber.btn.browse"),
            command=self._browse_output_folder,
            width=100,
            height=34,
        )
        self.browse_output_btn.grid(row=0, column=1, padx=(8, 0))

        self.custom_path_frame.grid(row=1, column=0, sticky="ew", pady=(10, 0))

    def _setup_output_section(self):
        """Transcript display with its own toolbar (expandable)."""
        section = CTkSection(self.body, title=t("transcriber.frame.transcript"), padding=10)
        section.grid(row=2, column=0, sticky="nsew")
        self._transcript_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)  # Text area expands

        # Toolbar: these act on the transcript, so they live with it rather
        # than in the main action bar.
        toolbar = ctk.CTkFrame(body, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        toolbar.grid_columnconfigure(3, weight=1)

        self.copy_btn = ctk.CTkButton(
            toolbar, text=t("transcriber.btn.copy"),
            command=self._copy_transcript, width=110, height=30,
        )
        self.copy_btn.grid(row=0, column=0, padx=(0, 6))

        self.export_txt_btn = ctk.CTkButton(
            toolbar, text=t("transcriber.btn.export_txt"),
            command=self._export_txt, width=110, height=30,
        )
        self.export_txt_btn.grid(row=0, column=1, padx=(0, 6))

        self.export_srt_btn = ctk.CTkButton(
            toolbar, text=t("transcriber.btn.export_srt"),
            command=self._export_srt, width=110, height=30,
        )
        self.export_srt_btn.grid(row=0, column=2, padx=(0, 6))

        self.copy_status = ctk.CTkLabel(
            toolbar, text="", anchor="w", text_color=("gray40", "gray65")
        )
        self.copy_status.grid(row=0, column=3, sticky="w", padx=(6, 0))

        # CTkTextbox brings its own scrollbar, so no manual Scrollbar needed.
        self.transcript_text = ctk.CTkTextbox(
            body,
            wrap="word",
            font=("Cascadia Mono", 12),
            activate_scrollbars=True,
            corner_radius=8,
        )
        self.transcript_text.grid(row=1, column=0, sticky="nsew")

        # Right-click context menu (copy/paste + TTS + fullscreen)
        self._register_context_menu(
            self.transcript_text,
            [
                {"copy": True},
                {"paste": True},
                {"separator": True},
                {"tts_read": lambda: self._selection_or_all(self.transcript_text)},
                {"tts_stop": True},
                {"separator": True},
                {"fullscreen": True, "title": t("transcriber.fullscreen.transcript"),
                 "editable": True},
            ],
        )

    def _setup_action_bar(self):
        """Primary actions plus an inline status line."""
        action_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        action_frame.grid_columnconfigure(2, weight=1)

        self.transcribe_btn = ctk.CTkButton(
            action_frame,
            text=t("transcriber.btn.transcribe"),
            command=self._transcribe_clicked,
            width=170,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.transcribe_btn.grid(row=0, column=0, padx=(0, 10))

        self.clear_btn = ctk.CTkButton(
            action_frame,
            text=t("transcriber.btn.clear"),
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
        self.clear_btn.grid(row=0, column=1, padx=(0, 10))

        # Status line: replaces the old sunken ttk label.
        self.status_label = ctk.CTkLabel(
            action_frame,
            text=t("transcriber.status.ready"),
            anchor="w",
            justify="left",
            text_color=("gray35", "gray70"),
        )
        self.status_label.grid(row=0, column=2, sticky="ew")

        self.loading_label = ctk.CTkLabel(action_frame, text="", anchor="e")
        self.loading_label.grid(row=0, column=3, sticky="e", padx=(10, 0))

    # ------------------------------------------------------------------
    # Mode / option handlers
    # ------------------------------------------------------------------

    def _on_mode_selected(self, label: str):
        mode = self._mode_labels.get(label)
        if mode and mode != self.mode_var.get():
            self.mode_var.set(mode)
            self._toggle_input_mode()

    def _on_device_selected(self, label: str):
        device = self._device_labels.get(label)
        if device:
            self.device_var.set(device)

    def _on_location_selected(self, label: str):
        location = self._location_labels.get(label)
        if location and location != self.output_location_var.get():
            self.output_location_var.set(location)
            self._toggle_output_location()

    def _toggle_input_mode(self):
        """Toggle between local file and YouTube URL input"""
        if self.mode_var.get() == "local":
            self.local_frame.grid()
            self.youtube_frame.grid_remove()
        else:
            self.youtube_frame.grid()
            self.local_frame.grid_remove()

        if hasattr(self, "mode_selector"):
            label = self._mode_values.get(self.mode_var.get())
            if label and self.mode_selector.get() != label:
                self.mode_selector.set(label)

    def _toggle_output_location(self, save: bool = True):
        """Show the custom path row only for a custom destination."""
        is_custom = self.output_location_var.get() == "custom"
        if is_custom:
            self.custom_path_frame.grid()
            self._output_location_section.set_expanded(True)
        else:
            self.custom_path_frame.grid_remove()

        # Save output location preference
        if save and self.settings:
            self.settings.set_transcriber_output_location(self.output_location_var.get())

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _browse_file(self):
        """Browse for local file"""
        supported_formats = [
            (t("transcriber.filetype.media"),
             "*.mp4 *.avi *.mov *.mkv *.mp3 *.wav *.flac *.m4a"),
            (t("transcriber.filetype.all"), "*.*"),
        ]
        file_path = filedialog.askopenfilename(
            title=t("transcriber.dialog.select_media"),
            filetypes=supported_formats,
        )
        if file_path:
            self.file_path_var.set(file_path)
            if self.on_file_selected:
                self.on_file_selected(file_path)

    def _browse_output_folder(self):
        """Browse for custom output folder and save preference"""
        folder = filedialog.askdirectory(title=t("transcriber.dialog.select_output_folder"))
        if folder:
            self.output_custom_path_var.set(folder)
            # Save custom path preference
            if self.settings:
                self.settings.set_transcriber_custom_path(folder)

    def _transcribe_clicked(self):
        """Handle transcribe button click"""
        if self.on_transcribe_clicked:
            self.on_transcribe_clicked()

    def _copy_transcript(self):
        """Copy transcript to clipboard"""
        if self.on_copy_clicked:
            self.on_copy_clicked()

    def _export_txt(self):
        """Export transcript as .txt"""
        if self.on_export_txt_clicked:
            self.on_export_txt_clicked()

    def _export_srt(self):
        """Export transcript as .srt"""
        if self.on_export_srt_clicked:
            self.on_export_srt_clicked()

    def _clear_clicked(self):
        """Handle clear button click"""
        if self.on_clear_clicked:
            self.on_clear_clicked()

    # ------------------------------------------------------------------
    # Public methods for controller
    # ------------------------------------------------------------------

    def get_mode(self) -> str:
        """Get current mode (local or youtube)"""
        return self.mode_var.get()

    def get_file_path(self) -> str:
        """Get selected file path"""
        return self.file_path_var.get()

    def get_youtube_url(self) -> str:
        """Get YouTube URL"""
        return self.url_var.get()

    def get_device(self) -> str:
        """Get selected device"""
        return self.device_var.get()

    def get_output_location(self) -> str:
        """Get output location choice (original or custom)"""
        return self.output_location_var.get()

    def get_output_path(self) -> str:
        """Get custom output path"""
        return self.output_custom_path_var.get()

    def get_keep_formats(self) -> list:
        """Get list of formats to keep"""
        formats = []
        if self.keep_txt_var.get():
            formats.append('.txt')
        if self.keep_srt_var.get():
            formats.append('.srt')
        if self.keep_vtt_var.get():
            formats.append('.vtt')
        if self.keep_json_var.get():
            formats.append('.json')
        if self.keep_tsv_var.get():
            formats.append('.tsv')
        return formats

    def set_transcript(self, content: str):
        """Set transcript text"""
        self.transcript_text.delete('1.0', tk.END)
        self.transcript_text.insert('1.0', content)

    def get_transcript(self) -> str:
        """Get current transcript"""
        return self.transcript_text.get('1.0', tk.END).rstrip()

    def set_status(self, message: str):
        """Set status message"""
        self.status_label.configure(text=message)

    def show_error(self, message: str):
        """
        Log the error and surface it inline.

        The base implementation only logs, which meant transcription failures
        were invisible in the UI. The status line makes them visible without
        interrupting the user with a modal dialog.
        """
        logger.error(f"[{self.tab_name}] Error: {message}")
        if hasattr(self, "status_label"):
            self.status_label.configure(text=message)

    def show_loading(self, show: bool = True):
        """Show/hide loading indicator"""
        if show:
            self.loading_label.configure(text=t("transcriber.status.transcribing"))
            self.transcribe_btn.configure(state="disabled")
        else:
            self.loading_label.configure(text="")
            self.transcribe_btn.configure(state="normal")

    def clear_all(self):
        """Clear all data"""
        self.file_path_var.set("")
        self.url_var.set("")
        self.transcript_text.delete('1.0', tk.END)
        self.set_status(t("transcriber.status.cleared"))
        self.copy_status.configure(text="")

    def copy_to_clipboard(self) -> bool:
        """Copy transcript to clipboard"""
        try:
            content = self.get_transcript()
            if not content.strip():
                self.show_error(t("transcriber.msg.no_transcript_copy"))
                return False

            self.clipboard_clear()
            self.clipboard_append(content)
            self.update_idletasks()

            self.copy_status.configure(text=t("transcriber.status.copied"))
            return True
        except Exception as e:
            self.show_error(t("transcriber.msg.copy_failed").format(error=str(e)))
            return False

    def get_content(self) -> str:
        """Get current content (transcript)"""
        return self.get_transcript()

    # ------------------------------------------------------------------
    # Theming hook used by MainWindow
    # ------------------------------------------------------------------

    def apply_font_size(self, size: int):
        """
        Apply the app-wide font size to this tab's transcript pane.

        Labels, controls and section headings are scaled centrally by
        :func:`views.ctk_theme.apply_font_scale`.
        """
        from views.ctk_theme import font_sizes
        self.transcript_text.configure(
            font=("Cascadia Mono", font_sizes(size)["mono"])
        )
