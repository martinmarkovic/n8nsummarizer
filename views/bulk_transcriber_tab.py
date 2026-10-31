"""
Bulk Transcriber Tab - v2.0 (CustomTkinter)

Manages the bulk audio/video transcription interface:
- Media type selection (mp4, mov, avi, mkv, webm, mp3, wav, m4a, flac, aac, wma, opus)
- Output format options (SRT, TXT, VTT, JSON)
- Folder selection with browse button
- Output location selection (default parent folder or custom)
- Recursive subfolder scanning option
- Progress tracking
- Status logging
- Remember last choice in .env

Layout (v2.0):
- Row 0: source folder card (full width)
- Row 1: draggable split - scrollable options (left) | status log (right)
- Row 2: action bar (Start / Cancel / status)

Version: 2.0
Created: 2026-01-06
Updated: 2026-03-15 (v1.2 - Scrollable left column for HiDPI)
Updated: 2026-10-30 (v2.0 - Migrated from ttk to CustomTkinter with the
    card-based layout used by the Summarizer tab. The public interface
    consumed by BulkTranscriberController is unchanged.)

Preference storage fix folded into this migration (same bug as the Bulk
Summarizer tab): ``_save_preferences`` rebuilt .env from parsed ``KEY=VALUE``
lines, so comment lines - which contain no ``=`` - were silently dropped every
time a checkbox changed. It also used a path relative to the working directory.
Preferences now go through SettingsManager, which edits values in place.
"""

from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk

from views.base_tab import CTkBaseTab
from views.ctk_compat import CTkSection, CTkSplitter
from utils.logger import logger
from utils.i18n import t


class BulkTranscriberTab(CTkBaseTab):
    """UI for bulk media transcription (v2.0 - CustomTkinter)."""

    def __init__(self, notebook, settings_manager=None):
        # CRITICAL: Initialize variables BEFORE calling super().__init__()
        self.notebook = notebook
        self.settings = settings_manager

        self.source_folder_var = tk.StringVar(value=t("bulk_transcriber.folder.none"))
        self.output_folder_var = tk.StringVar(
            value=t("bulk_transcriber.folder.default_parent")
        )

        # Media type selections - video formats
        self.media_type_mp4 = tk.BooleanVar(value=True)
        self.media_type_mov = tk.BooleanVar(value=False)
        self.media_type_avi = tk.BooleanVar(value=False)
        self.media_type_mkv = tk.BooleanVar(value=False)
        self.media_type_webm = tk.BooleanVar(value=False)

        # Media type selections - audio formats
        self.media_type_mp3 = tk.BooleanVar(value=False)
        self.media_type_wav = tk.BooleanVar(value=False)
        self.media_type_m4a = tk.BooleanVar(value=False)
        self.media_type_flac = tk.BooleanVar(value=False)
        self.media_type_aac = tk.BooleanVar(value=False)
        self.media_type_wma = tk.BooleanVar(value=False)
        self.media_type_opus = tk.BooleanVar(value=False)

        # Output format options (transcript formats)
        self.output_format_srt = tk.BooleanVar(value=True)
        self.output_format_txt = tk.BooleanVar(value=False)
        self.output_format_vtt = tk.BooleanVar(value=False)
        self.output_format_json = tk.BooleanVar(value=False)

        # Recursive subfolder scanning
        self.recursive_subfolders = tk.BooleanVar(value=False)

        # Output location
        self.output_location_default = tk.BooleanVar(value=True)

        # Callback registration
        self.on_start_requested = None
        self.on_cancel_requested = None

        super().__init__(notebook, "\U0001f3ac Bulk Transcriber")
        self._load_preferences()
        logger.info("BulkTranscriberTab initialized (v2.0)")

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """
        Layout:
            0  source folder card (full width)
            1  split: scrollable options | status log   <- expanding region
            2  action bar
        """
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._setup_folder_selection()
        self._setup_main_split()
        self._setup_action_bar()

    def _setup_folder_selection(self):
        """Source folder card - full width at top."""
        section = CTkSection(self, title=t("bulk_transcriber.frame.select_folder"))
        section.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._folder_section = section
        body = section.body
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            body,
            text=t("bulk_transcriber.btn.browse"),
            command=self._browse_folder,
            width=110,
            height=34,
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkLabel(
            body,
            textvariable=self.source_folder_var,
            anchor="w",
            fg_color=("gray88", "gray24"),
            corner_radius=8,
            height=34,
            padx=10,
        ).grid(row=0, column=1, sticky="ew")

    def _setup_main_split(self):
        """Scrollable options on the left, status log on the right."""
        self._split = CTkSplitter(self, ratio=0.42)
        self._split.grid(row=1, column=0, sticky="nsew")

        # CTkScrollableFrame replaces the hand-rolled Canvas + Scrollbar, and
        # notably the old bind_all("<MouseWheel>") which hijacked the wheel for
        # the entire application rather than just this panel.
        self._split.left.grid_rowconfigure(0, weight=1)
        self._split.left.grid_columnconfigure(0, weight=1)

        self._options_scroll = ctk.CTkScrollableFrame(
            self._split.left, fg_color="transparent"
        )
        self._options_scroll.grid(row=0, column=0, sticky="nsew")
        self._options_scroll.grid_columnconfigure(0, weight=1)
        self._left_inner = self._options_scroll  # backwards reference

        self._setup_media_type_video()
        self._setup_media_type_audio()
        self._setup_recursive_option()
        self._setup_output_format()
        self._setup_output_location()
        self._setup_progress_section()

        self._split.right.grid_rowconfigure(0, weight=1)
        self._split.right.grid_columnconfigure(0, weight=1)
        self._setup_status_log()

    def _next_left_row(self):
        """Grid row counter for the scrollable options column."""
        row = getattr(self, "_left_row", 0)
        self._left_row = row + 1
        return row

    def _left_card(self, title: str):
        """Create a card in the scrollable options column."""
        section = CTkSection(self._options_scroll, title=title)
        section.grid(row=self._next_left_row(), column=0, sticky="ew", pady=(0, 10))
        return section

    def _checkbox_grid(self, parent, items, columns=3, command=None):
        """
        Lay checkboxes out in a grid.

        The ttk version stacked twelve media formats vertically, which made the
        left column far taller than any screen.
        """
        for i, (label, var) in enumerate(items):
            ctk.CTkCheckBox(
                parent,
                text=label,
                variable=var,
                command=command,
                checkbox_width=18,
                checkbox_height=18,
                width=70,
            ).grid(row=i // columns, column=i % columns, sticky="w",
                   padx=(0, 10), pady=3)

    # ------------------------------------------------------------------
    # Left column cards
    # ------------------------------------------------------------------

    def _setup_media_type_video(self):
        """Video format selection."""
        section = self._left_card(t("bulk_transcriber.frame.video"))
        self._video_section = section
        self._checkbox_grid(section.body, [
            (t("bulk_transcriber.media.video.mp4"), self.media_type_mp4),
            (t("bulk_transcriber.media.video.mov"), self.media_type_mov),
            (t("bulk_transcriber.media.video.avi"), self.media_type_avi),
            (t("bulk_transcriber.media.video.mkv"), self.media_type_mkv),
            (t("bulk_transcriber.media.video.webm"), self.media_type_webm),
        ], columns=3, command=self._on_media_type_changed)

    def _setup_media_type_audio(self):
        """Audio format selection."""
        section = self._left_card(t("bulk_transcriber.frame.audio"))
        self._audio_section = section
        self._checkbox_grid(section.body, [
            (t("bulk_transcriber.media.audio.mp3"), self.media_type_mp3),
            (t("bulk_transcriber.media.audio.wav"), self.media_type_wav),
            (t("bulk_transcriber.media.audio.m4a"), self.media_type_m4a),
            (t("bulk_transcriber.media.audio.flac"), self.media_type_flac),
            (t("bulk_transcriber.media.audio.aac"), self.media_type_aac),
            (t("bulk_transcriber.media.audio.wma"), self.media_type_wma),
            (t("bulk_transcriber.media.audio.opus"), self.media_type_opus),
        ], columns=3, command=self._on_media_type_changed)

    def _setup_recursive_option(self):
        """Recursive subfolder scanning."""
        section = self._left_card(t("bulk_transcriber.frame.scanning"))
        self._scanning_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkCheckBox(
            body,
            text=t("bulk_transcriber.chk.scan_subfolders"),
            variable=self.recursive_subfolders,
            command=self._on_recursive_changed,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            body,
            text=t("bulk_transcriber.lbl.recursive_hint"),
            anchor="w",
            justify="left",
            wraplength=360,
            text_color=("gray45", "gray60"),
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

    def _setup_output_format(self):
        """Transcript output formats."""
        section = self._left_card(t("bulk_transcriber.frame.output_formats"))
        self._output_format_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        formats_row = ctk.CTkFrame(body, fg_color="transparent")
        formats_row.grid(row=0, column=0, sticky="ew")

        self._checkbox_grid(formats_row, [
            (t("bulk_transcriber.output.srt"), self.output_format_srt),
            (t("bulk_transcriber.output.txt"), self.output_format_txt),
            (t("bulk_transcriber.output.vtt"), self.output_format_vtt),
            (t("bulk_transcriber.output.json"), self.output_format_json),
        ], columns=4, command=self._save_preferences)

        ctk.CTkLabel(
            body,
            text=t("bulk_transcriber.lbl.output_note"),
            anchor="w",
            justify="left",
            wraplength=360,
            text_color=("gray45", "gray60"),
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))

    def _setup_output_location(self):
        """Output location choice plus the resolved destination."""
        section = self._left_card(t("bulk_transcriber.frame.output_location"))
        self._output_location_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        self._location_labels = {
            t("bulk_transcriber.radio.default_location"): True,
            t("bulk_transcriber.radio.custom_location"): False,
        }
        self._location_values = {v: k for k, v in self._location_labels.items()}

        self.location_selector = ctk.CTkSegmentedButton(
            body,
            values=list(self._location_labels.keys()),
            command=self._on_location_selected,
            height=32,
            font=ctk.CTkFont(size=12),
        )
        self.location_selector.grid(row=0, column=0, sticky="ew")
        self.location_selector.set(
            self._location_values[self.output_location_default.get()]
        )

        ctk.CTkButton(
            body,
            text=t("bulk_transcriber.btn.browse"),
            command=self._browse_output_folder,
            height=30,
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        ctk.CTkLabel(
            body,
            textvariable=self.output_folder_var,
            anchor="w",
            justify="left",
            wraplength=360,
            text_color=("gray45", "gray60"),
        ).grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def _setup_progress_section(self):
        """Progress bar and counters."""
        section = self._left_card(t("bulk_transcriber.frame.progress"))
        self._progress_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        self.current_file_var = tk.StringVar(value=t("bulk_transcriber.lbl.idle"))
        ctk.CTkLabel(
            body,
            textvariable=self.current_file_var,
            anchor="w",
            justify="left",
            wraplength=360,
        ).grid(row=0, column=0, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(body, mode="determinate", height=8)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=8)

        self.progress_text_var = tk.StringVar(
            value=t("bulk_transcriber.progress.files").format(current=0, total=0)
        )
        ctk.CTkLabel(
            body, textvariable=self.progress_text_var, anchor="w",
            text_color=("gray45", "gray60"),
        ).grid(row=2, column=0, sticky="ew")

    def _setup_status_log(self):
        """Status log - right pane."""
        section = CTkSection(
            self._split.right, title=t("bulk_transcriber.frame.status_log"), padding=10
        )
        section.grid(row=0, column=0, sticky="nsew")
        self._log_section = section
        section.body.grid_rowconfigure(0, weight=1)
        section.body.grid_columnconfigure(0, weight=1)

        self.status_log = ctk.CTkTextbox(
            section.body,
            wrap="word",
            font=("Cascadia Mono", 12),
            activate_scrollbars=True,
            corner_radius=8,
            state="disabled",
        )
        self.status_log.grid(row=0, column=0, sticky="nsew")
        self._register_context_menu(self.status_log, [{"copy": True}])

    def _setup_action_bar(self):
        """Start / Cancel and the live status line."""
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        action_frame.grid_columnconfigure(2, weight=1)

        self.start_button = ctk.CTkButton(
            action_frame,
            text=t("bulk_transcriber.btn.start"),
            command=self._on_start_clicked,
            state="disabled",
            width=170,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.start_button.grid(row=0, column=0, padx=(0, 10))

        self.cancel_button = ctk.CTkButton(
            action_frame,
            text=t("bulk_transcriber.btn.cancel"),
            command=self._on_cancel_clicked,
            state="disabled",
            width=110,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
        )
        self.cancel_button.grid(row=0, column=1, padx=(0, 10))

        self.status_label = ctk.CTkLabel(
            action_frame,
            text=t("bulk_transcriber.lbl.ready"),
            anchor="w",
            text_color=("gray35", "gray70"),
        )
        self.status_label.grid(row=0, column=2, sticky="ew")

    # ------------------------------------------------------------------
    # Folder handling
    # ------------------------------------------------------------------

    def _browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title=t("bulk_transcriber.dialog.select_source"))
        if folder:
            self.source_folder_var.set(folder)
            file_count = self._count_matching_files(folder)
            self.append_log(
                t("bulk_transcriber.log.folder_selected").format(
                    name=Path(folder).name, count=file_count
                ),
                "info",
            )
            self._update_start_button_state()
            if file_count == 0:
                self.append_log(t("bulk_transcriber.log.no_media_found"), "warning")
            self.output_folder_var.set(
                t("bulk_transcriber.folder.default_named").format(
                    name=Path(folder).parent.name
                )
            )

    def _count_matching_files(self, folder: str) -> int:
        """Count media files matching selected types"""
        folder_path = Path(folder)
        count = 0
        glob_method = (
            folder_path.rglob if self.recursive_subfolders.get() else folder_path.glob
        )

        type_patterns = [
            (self.media_type_mp4, "*.mp4"),
            (self.media_type_mov, "*.mov"),
            (self.media_type_avi, "*.avi"),
            (self.media_type_mkv, "*.mkv"),
            (self.media_type_webm, "*.webm"),
            (self.media_type_mp3, "*.mp3"),
            (self.media_type_wav, "*.wav"),
            (self.media_type_m4a, "*.m4a"),
            (self.media_type_flac, "*.flac"),
            (self.media_type_aac, "*.aac"),
            (self.media_type_wma, "*.wma"),
            (self.media_type_opus, "*.opus"),
        ]
        for var, pattern in type_patterns:
            if var.get():
                count += len(list(glob_method(pattern)))
        return count

    def _any_media_type_selected(self) -> bool:
        return any([
            self.media_type_mp4.get(), self.media_type_mov.get(),
            self.media_type_avi.get(), self.media_type_mkv.get(),
            self.media_type_webm.get(), self.media_type_mp3.get(),
            self.media_type_wav.get(), self.media_type_m4a.get(),
            self.media_type_flac.get(), self.media_type_aac.get(),
            self.media_type_wma.get(), self.media_type_opus.get(),
        ])

    def _update_start_button_state(self):
        if not self._any_media_type_selected():
            self.start_button.configure(state="disabled")
            return
        folder = self.get_source_folder()
        if not folder:
            self.start_button.configure(state="disabled")
            return
        file_count = self._count_matching_files(folder)
        self.start_button.configure(state="normal" if file_count > 0 else "disabled")

    def _on_media_type_changed(self):
        if not self._any_media_type_selected():
            self.append_log(t("bulk_transcriber.log.min_one_media"), "warning")
        self._update_start_button_state()
        self._save_preferences()

    def _on_recursive_changed(self):
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            label = (
                t("bulk_transcriber.log.with_subfolders")
                if self.recursive_subfolders.get()
                else t("bulk_transcriber.log.without_subfolders")
            )
            self.append_log(
                t("bulk_transcriber.log.scanning_mode").format(
                    label=label, count=file_count
                ),
                "info",
            )
            self._update_start_button_state()
        self._save_preferences()

    def _on_location_selected(self, label: str):
        """Segmented-button handler for the output location choice."""
        value = self._location_labels.get(label)
        if value is not None and value != self.output_location_default.get():
            self.output_location_default.set(value)
            self._on_output_location_changed()

    def _on_output_location_changed(self):
        if self.output_location_default.get():
            folder = self.get_source_folder()
            if folder:
                self.output_folder_var.set(
                    t("bulk_transcriber.folder.default_named").format(
                        name=Path(folder).parent.name
                    )
                )

    def _browse_output_folder(self):
        folder = filedialog.askdirectory(title=t("bulk_transcriber.dialog.select_output"))
        if folder:
            self.output_folder_var.set(folder)
            self.output_location_default.set(False)
            if hasattr(self, "location_selector"):
                self.location_selector.set(self._location_values[False])
            self.append_log(
                t("bulk_transcriber.log.output_folder_set").format(
                    name=Path(folder).name
                ),
                "info",
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_source_folder(self) -> str:
        folder = self.source_folder_var.get()
        return folder if folder != t("bulk_transcriber.folder.none") else None

    def get_output_folder(self) -> str:
        folder = self.source_folder_var.get()
        if self.output_location_default.get() and folder:
            return str(Path(folder).parent)
        else:
            output = self.output_folder_var.get()
            return output if "[" not in output else None

    def get_media_types(self) -> list:
        types = []
        for var, name in (
            (self.media_type_mp4, "mp4"), (self.media_type_mov, "mov"),
            (self.media_type_avi, "avi"), (self.media_type_mkv, "mkv"),
            (self.media_type_webm, "webm"), (self.media_type_mp3, "mp3"),
            (self.media_type_wav, "wav"), (self.media_type_m4a, "m4a"),
            (self.media_type_flac, "flac"), (self.media_type_aac, "aac"),
            (self.media_type_wma, "wma"), (self.media_type_opus, "opus"),
        ):
            if var.get():
                types.append(name)
        return types

    def get_output_formats(self) -> dict:
        return {
            "srt": self.output_format_srt.get(),
            "txt": self.output_format_txt.get(),
            "vtt": self.output_format_vtt.get(),
            "json": self.output_format_json.get(),
        }

    def get_recursive_option(self) -> bool:
        return self.recursive_subfolders.get()

    def set_processing_enabled(self, enabled: bool):
        """
        Enable/disable the processing controls.

        ``enabled=True`` means "idle, ready to start again", so Start becomes
        available and Cancel does not.
        """
        self.start_button.configure(state="normal" if enabled else "disabled")
        self.cancel_button.configure(state="disabled" if enabled else "normal")
        self.status_label.configure(
            text=t("bulk_transcriber.lbl.ready") if enabled else
            t("bulk_transcriber.progress.processing").format(filename="...")
        )

    def update_progress(self, current: int, total: int):
        # CTkProgressBar takes a 0..1 fraction, not a 0..100 value.
        fraction = (current / total) if total > 0 else 0
        self.progress_bar.set(min(max(fraction, 0.0), 1.0))
        self.progress_text_var.set(
            t("bulk_transcriber.progress.files").format(current=current, total=total)
        )

    def set_current_file(self, filename: str):
        self.current_file_var.set(
            t("bulk_transcriber.progress.processing").format(filename=filename)
        )

    def append_log(self, message: str, status: str = "info"):
        self.status_log.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        indicators = {
            "success": "\u2713", "error": "\u2717",
            "info": "\u2022", "warning": "\u26a0",
        }
        indicator = indicators.get(status, "\u2022")
        self.status_log.insert(tk.END, f"[{timestamp}] {indicator} {message}\n")
        self.status_log.see(tk.END)
        self.status_log.configure(state="disabled")

    def clear_all(self):
        self.source_folder_var.set(t("bulk_transcriber.folder.none"))
        self.output_folder_var.set(t("bulk_transcriber.folder.default_parent"))
        self.progress_bar.set(0)
        self.progress_text_var.set(
            t("bulk_transcriber.progress.files").format(current=0, total=0)
        )
        self.current_file_var.set(t("bulk_transcriber.lbl.idle"))
        self.status_log.configure(state="normal")
        self.status_log.delete('1.0', tk.END)
        self.status_log.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")

    def get_content(self) -> str:
        return self.status_log.get('1.0', tk.END)

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def _on_start_clicked(self):
        logger.debug(
            f"Bulk Transcriber Start button clicked. "
            f"Callback registered: {self.on_start_requested is not None}"
        )
        if self.on_start_requested:
            self.on_start_requested()
        else:
            logger.warning("No start callback registered for Bulk Transcriber!")
            self.append_log(t("bulk_transcriber.log.start_callback_missing"), "error")

    def _on_cancel_clicked(self):
        if self.on_cancel_requested:
            self.on_cancel_requested()

    def set_on_start_requested(self, callback):
        self.on_start_requested = callback
        logger.info(f"Bulk Transcriber start callback registered: {callback}")

    def set_on_cancel_requested(self, callback):
        self.on_cancel_requested = callback

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    _PREF_MEDIA_TYPES = "BULK_TRANS_MEDIA_TYPES"
    _PREF_OUTPUT_FORMATS = "BULK_TRANS_OUTPUT_FORMATS"
    _PREF_RECURSIVE = "BULK_TRANS_RECURSIVE_SUBFOLDERS"

    _MEDIA_VARS = (
        ("mp4", "media_type_mp4"), ("mov", "media_type_mov"),
        ("avi", "media_type_avi"), ("mkv", "media_type_mkv"),
        ("webm", "media_type_webm"), ("mp3", "media_type_mp3"),
        ("wav", "media_type_wav"), ("m4a", "media_type_m4a"),
        ("flac", "media_type_flac"), ("aac", "media_type_aac"),
        ("wma", "media_type_wma"), ("opus", "media_type_opus"),
    )
    _FORMAT_VARS = (
        ("srt", "output_format_srt"), ("txt", "output_format_txt"),
        ("vtt", "output_format_vtt"), ("json", "output_format_json"),
    )

    def _load_preferences(self):
        """Load saved preferences via SettingsManager."""
        if self.settings is None:
            logger.debug("No SettingsManager; using default bulk transcriber preferences")
            return
        try:
            media = {
                p.strip()
                for p in self.settings.get(self._PREF_MEDIA_TYPES, "mp4").split(",")
                if p.strip()
            }
            for name, attr in self._MEDIA_VARS:
                getattr(self, attr).set(name in media)

            formats = {
                p.strip()
                for p in self.settings.get(self._PREF_OUTPUT_FORMATS, "srt").split(",")
                if p.strip()
            }
            for name, attr in self._FORMAT_VARS:
                getattr(self, attr).set(name in formats)

            self.recursive_subfolders.set(
                self.settings.get(self._PREF_RECURSIVE, "False").lower() == "true"
            )
            logger.info("Bulk Transcriber preferences loaded")
        except Exception as e:
            logger.warning(f"Could not load preferences: {str(e)}")

    def _save_preferences(self):
        """
        Save preferences via SettingsManager.

        SettingsManager updates only the keys it owns, leaving comments and
        unrelated entries in .env intact.
        """
        if self.settings is None:
            return
        try:
            media = [n for n, attr in self._MEDIA_VARS if getattr(self, attr).get()]
            formats = [n for n, attr in self._FORMAT_VARS if getattr(self, attr).get()]

            self.settings.set(self._PREF_MEDIA_TYPES, ",".join(media) if media else "mp4")
            self.settings.set(
                self._PREF_OUTPUT_FORMATS, ",".join(formats) if formats else "srt"
            )
            self.settings.set(self._PREF_RECURSIVE, str(self.recursive_subfolders.get()))
            logger.info("Bulk Transcriber preferences saved")
        except Exception as e:
            logger.warning(f"Could not save preferences: {str(e)}")

    # ------------------------------------------------------------------
    # Theming hook used by MainWindow
    # ------------------------------------------------------------------

    def apply_font_size(self, size: int):
        """Apply the app-wide font size to this tab's log area."""
        self.status_log.configure(font=("Cascadia Mono", size + 1))

        section_font = ctk.CTkFont(size=max(size + 1, 11), weight="bold")
        for attr in ("_folder_section", "_video_section", "_audio_section",
                     "_scanning_section", "_output_format_section",
                     "_output_location_section", "_progress_section",
                     "_log_section"):
            section = getattr(self, attr, None)
            if section is not None:
                section.set_title_font(section_font)
