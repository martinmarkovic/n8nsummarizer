"""
Bulk Summarizer Tab - v6.0 (CustomTkinter)

Manages the bulk file summarization interface:
- File type selection with multiple checkboxes (txt, srt, docx, pdf, opus)
- Output format options (separate files, combined file)
- Output location selection (default or custom)
- Recursive subfolder scanning option
- Progress tracking
- Status logging
- Remember last choice in .env

Layout (v6.0):
- Row 0: source folder card (full width)
- Row 1: draggable split - scrollable options (left) | status log (right)
- Row 2: action bar (Start / Cancel / progress)

Version: 6.0
Created: 2025-12-10
Updated: 2026-01-06 (v4.7 - Added recursive subfolder support)
Updated: 2026-03-15 (v5.1 - .opus support + scrollable left column)
Updated: 2026-10-30 (v6.0 - Migrated from ttk to CustomTkinter with the
    card-based responsive layout used by the Summarizer tab. The public
    interface consumed by BulkSummarizerController is unchanged.)

Preference storage fix folded into this migration:
    ``_save_preferences`` used to rewrite .env itself, rebuilding the file from
    parsed ``KEY=VALUE`` lines. Comment lines have no ``=``, so they were
    dropped - every change to the file-type checkboxes silently deleted every
    comment in .env. It also used a path relative to the current working
    directory, so launching from elsewhere wrote a second .env. Preferences now
    go through SettingsManager, which updates values in place and preserves
    comments and layout.
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


class BulkSummarizerTab(CTkBaseTab):
    """UI for bulk file summarization (v6.0 - CustomTkinter)."""

    # This tab scrolls its own left column and lets the log pane fill, so it
    # does not want the base class's whole-tab scroll wrapper.
    SCROLLABLE = False

    def __init__(self, notebook, prompt_manager=None, settings_manager=None):
        self.notebook = notebook
        self.settings = settings_manager

        self.source_folder_var = tk.StringVar(value=t("bulk_summarizer.folder.none"))
        self.output_folder_var = tk.StringVar(
            value=t("bulk_summarizer.folder.default_parent")
        )

        # File type selections
        self.file_type_txt = tk.BooleanVar(value=True)
        self.file_type_srt = tk.BooleanVar(value=False)
        self.file_type_docx = tk.BooleanVar(value=False)
        self.file_type_pdf = tk.BooleanVar(value=False)
        self.file_type_opus = tk.BooleanVar(value=False)

        # Output format options
        self.output_separate = tk.BooleanVar(value=True)
        self.output_combined = tk.BooleanVar(value=False)

        # Recursive subfolder scanning
        self.recursive_subfolders = tk.BooleanVar(value=False)

        # Output location
        self.output_location_default = tk.BooleanVar(value=True)

        # Prompt management
        self.prompt_manager = prompt_manager
        self._last_valid_preset = None

        # LLM Settings inheritance - reference to SummarizerTab
        self.summarizer_tab = None

        # Callback registration
        self.on_start_requested = None
        self.on_cancel_requested = None

        super().__init__(notebook, "📦 Bulk Summarizer")
        self._load_preferences()
        logger.info("BulkSummarizerTab initialized (v6.0)")

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
        section = CTkSection(
            self, title=t("bulk_summarizer.frame.select_source_folder")
        )
        section.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._folder_section = section
        body = section.body
        body.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            body,
            text=t("bulk_summarizer.btn.browse"),
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

        # --- Left: scrollable options ---
        # CTkScrollableFrame replaces the hand-rolled Canvas + Scrollbar +
        # mousewheel plumbing the ttk version needed. The old version also
        # bound <MouseWheel> with bind_all, which hijacked scrolling for the
        # whole app, not just this panel.
        self._split.left.grid_rowconfigure(0, weight=1)
        self._split.left.grid_columnconfigure(0, weight=1)

        self._options_scroll = ctk.CTkScrollableFrame(
            self._split.left, fg_color="transparent"
        )
        self._options_scroll.grid(row=0, column=0, sticky="nsew")
        self._options_scroll.grid_columnconfigure(0, weight=1)

        self._left_inner = self._options_scroll  # kept for backwards reference

        self._setup_llm_settings_info()
        self._setup_file_type()
        self._setup_scanning_options()
        self._setup_output_format()
        self._setup_output_location()
        self._setup_progress_section()

        # --- Right: status log ---
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

    # ------------------------------------------------------------------
    # Left column cards
    # ------------------------------------------------------------------

    def _setup_llm_settings_info(self):
        """LLM settings inherited from the Summarizer tab."""
        section = self._left_card(t("bulk_summarizer.frame.llm_settings"))
        self._llm_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        self.provider_info_var = tk.StringVar(
            value=t("bulk_summarizer.llm.provider_not_connected")
        )
        self.webhook_info_var = tk.StringVar(
            value=t("bulk_summarizer.llm.base_url_not_configured")
        )
        self.model_info_var = tk.StringVar(
            value=t("bulk_summarizer.llm.model_not_selected")
        )
        self.prompt_info_var = tk.StringVar(
            value=t("bulk_summarizer.llm.prompt_not_selected")
        )

        row = 0
        for var in (self.provider_info_var, self.webhook_info_var,
                    self.model_info_var, self.prompt_info_var):
            ctk.CTkLabel(
                body, textvariable=var, anchor="w", justify="left", wraplength=360
            ).grid(row=row, column=0, sticky="ew", pady=1)
            row += 1

        ctk.CTkButton(
            body,
            text=t("bulk_summarizer.btn.refresh_settings"),
            command=self._refresh_llm_settings_display,
            height=30,
        ).grid(row=row, column=0, sticky="w", pady=(8, 0))
        row += 1

        ctk.CTkLabel(
            body,
            text=t("bulk_summarizer.lbl.llm_inherit_note"),
            anchor="w",
            justify="left",
            wraplength=360,
            text_color=("gray45", "gray60"),
        ).grid(row=row, column=0, sticky="ew", pady=(6, 0))

    def _setup_file_type(self):
        """Checkboxes for file type selection."""
        section = self._left_card(t("bulk_summarizer.frame.file_types"))
        self._file_type_section = section
        body = section.body

        files = [
            (t("bulk_summarizer.filetype.txt"), self.file_type_txt),
            (t("bulk_summarizer.filetype.srt"), self.file_type_srt),
            (t("bulk_summarizer.filetype.docx"), self.file_type_docx),
            (t("bulk_summarizer.filetype.pdf"), self.file_type_pdf),
            (t("bulk_summarizer.filetype.opus"), self.file_type_opus),
        ]

        # Two columns: five stacked checkboxes wasted a lot of vertical space.
        for i, (label, var) in enumerate(files):
            ctk.CTkCheckBox(
                body,
                text=label,
                variable=var,
                command=self._on_file_type_changed,
                checkbox_width=18,
                checkbox_height=18,
            ).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 12), pady=3)

    def _setup_scanning_options(self):
        """Recursive subfolder scanning."""
        section = self._left_card(t("bulk_summarizer.frame.scanning_options"))
        self._scanning_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkCheckBox(
            body,
            text=t("bulk_summarizer.chk.scan_subfolders"),
            variable=self.recursive_subfolders,
            command=self._on_recursive_changed,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            body,
            text=t("bulk_summarizer.lbl.recursive_hint"),
            anchor="w",
            justify="left",
            wraplength=360,
            text_color=("gray45", "gray60"),
        ).grid(row=1, column=0, sticky="ew", pady=(4, 0))

    def _setup_output_format(self):
        """Output format checkboxes."""
        section = self._left_card(t("bulk_summarizer.frame.output_format"))
        self._output_format_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkCheckBox(
            body,
            text=t("bulk_summarizer.chk.separate_files"),
            variable=self.output_separate,
            command=self._save_preferences,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=0, column=0, sticky="w", pady=2)

        ctk.CTkCheckBox(
            body,
            text=t("bulk_summarizer.chk.combined_file"),
            variable=self.output_combined,
            command=self._save_preferences,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=1, column=0, sticky="w", pady=2)

        ctk.CTkLabel(
            body,
            text=t("bulk_summarizer.lbl.output_format_note"),
            anchor="w",
            justify="left",
            wraplength=360,
            text_color=("gray45", "gray60"),
        ).grid(row=2, column=0, sticky="ew", pady=(6, 0))

    def _setup_output_location(self):
        """Output location choice plus the resolved destination."""
        section = self._left_card(t("bulk_summarizer.frame.output_location"))
        self._output_location_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        # A two-way choice reads better as a segmented control than as two
        # radio buttons bound to a BooleanVar.
        self._location_labels = {
            t("bulk_summarizer.rb.default_location"): True,
            t("bulk_summarizer.rb.custom_location"): False,
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
            text=t("bulk_summarizer.btn.browse"),
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
        section = self._left_card(t("bulk_summarizer.frame.progress"))
        self._progress_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        self.current_file_var = tk.StringVar(value=t("bulk_summarizer.progress.idle"))
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
            value=t("bulk_summarizer.progress.files").format(current=0, total=0)
        )
        ctk.CTkLabel(
            body, textvariable=self.progress_text_var, anchor="w",
            text_color=("gray45", "gray60"),
        ).grid(row=2, column=0, sticky="ew")

    def _setup_status_log(self):
        """Status log - right pane."""
        section = CTkSection(
            self._split.right, title=t("bulk_summarizer.frame.status_log"), padding=10
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
            text=t("bulk_summarizer.btn.start"),
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
            text=t("bulk_summarizer.btn.cancel"),
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
            text=t("bulk_summarizer.status.ready"),
            anchor="w",
            text_color=("gray35", "gray70"),
        )
        self.status_label.grid(row=0, column=2, sticky="ew")

    # ------------------------------------------------------------------
    # Folder handling
    # ------------------------------------------------------------------

    def _browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title=t("bulk_summarizer.dialog.select_folder"))
        if folder:
            self.source_folder_var.set(folder)
            file_count = self._count_matching_files(folder)
            self.append_log(
                t("bulk_summarizer.log.folder_selected").format(
                    name=Path(folder).name, count=file_count
                ),
                "info",
            )
            self._set_start_enabled(file_count > 0)
            if file_count == 0:
                self.append_log(t("bulk_summarizer.log.no_matching"), "warning")
            self.output_folder_var.set(
                t("bulk_summarizer.folder.default_named").format(
                    name=Path(folder).parent.name
                )
            )

    def _count_matching_files(self, folder: str) -> int:
        """Count files matching selected types"""
        folder_path = Path(folder)
        count = 0
        use_rglob = self.recursive_subfolders.get()

        type_patterns = [
            (self.file_type_txt, "*.txt"),
            (self.file_type_srt, "*.srt"),
            (self.file_type_docx, "*.docx"),
            (self.file_type_pdf, "*.pdf"),
            (self.file_type_opus, "*.opus"),
        ]
        for var, pattern in type_patterns:
            if var.get():
                if use_rglob:
                    count += len(list(folder_path.rglob(pattern)))
                else:
                    count += len(list(folder_path.glob(pattern)))
        return count

    def _set_start_enabled(self, enabled: bool):
        """Enable or disable the Start button."""
        self.start_button.configure(state="normal" if enabled else "disabled")

    def _on_file_type_changed(self):
        """Called when file type selection changes"""
        if not any([
            self.file_type_txt.get(), self.file_type_srt.get(),
            self.file_type_docx.get(), self.file_type_pdf.get(),
            self.file_type_opus.get(),
        ]):
            self.append_log(t("bulk_summarizer.log.min_one_type"), "warning")
            self._set_start_enabled(False)
            return

        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            self.append_log(
                t("bulk_summarizer.log.file_types_updated").format(count=file_count),
                "info",
            )
            self._set_start_enabled(file_count > 0)
        self._save_preferences()

    def _on_recursive_changed(self):
        """Called when recursive subfolder option changes"""
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            label = (
                t("bulk_summarizer.log.scan_with_subfolders")
                if self.recursive_subfolders.get()
                else t("bulk_summarizer.log.scan_without_subfolders")
            )
            self.append_log(
                t("bulk_summarizer.log.scanning_mode_updated").format(
                    label=label, count=file_count
                ),
                "info",
            )
            self._set_start_enabled(file_count > 0)
        self._save_preferences()

    def _on_location_selected(self, label: str):
        """Segmented-button handler for the output location choice."""
        value = self._location_labels.get(label)
        if value is not None and value != self.output_location_default.get():
            self.output_location_default.set(value)
            self._on_output_location_changed()

    def _on_output_location_changed(self):
        """Called when output location changes"""
        if self.output_location_default.get():
            folder = self.get_source_folder()
            if folder:
                self.output_folder_var.set(
                    t("bulk_summarizer.folder.default_named").format(
                        name=Path(folder).parent.name
                    )
                )

    def _browse_output_folder(self):
        """Open folder selection dialog for output"""
        folder = filedialog.askdirectory(title=t("bulk_summarizer.dialog.select_output"))
        if folder:
            self.output_folder_var.set(folder)
            self.output_location_default.set(False)
            if hasattr(self, "location_selector"):
                self.location_selector.set(self._location_values[False])
            self.append_log(
                t("bulk_summarizer.log.output_folder_set").format(name=Path(folder).name),
                "info",
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_source_folder(self) -> str:
        folder = self.source_folder_var.get()
        return folder if folder != t("bulk_summarizer.folder.none") else None

    def get_output_folder(self) -> str:
        folder = self.source_folder_var.get()
        if self.output_location_default.get() and folder:
            return str(Path(folder).parent)
        else:
            output = self.output_folder_var.get()
            return output if "[" not in output else None

    def get_file_types(self) -> list:
        """Return selected file type strings (including opus if checked)"""
        types = []
        if self.file_type_txt.get():
            types.append("txt")
        if self.file_type_srt.get():
            types.append("srt")
        if self.file_type_docx.get():
            types.append("docx")
        if self.file_type_pdf.get():
            types.append("pdf")
        if self.file_type_opus.get():
            types.append("opus")
        return types

    def get_output_formats(self) -> dict:
        return {
            "separate": self.output_separate.get(),
            "combined": self.output_combined.get(),
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
            text=t("bulk_summarizer.status.ready") if enabled else
            t("bulk_summarizer.progress.processing").format(filename="...")
        )

    def update_progress(self, current: int, total: int):
        # CTkProgressBar takes a 0..1 fraction, not a 0..100 value.
        fraction = (current / total) if total > 0 else 0
        self.progress_bar.set(min(max(fraction, 0.0), 1.0))
        self.progress_text_var.set(
            t("bulk_summarizer.progress.files").format(current=current, total=total)
        )

    def set_current_file(self, filename: str):
        self.current_file_var.set(
            t("bulk_summarizer.progress.processing").format(filename=filename)
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
        self.source_folder_var.set(t("bulk_summarizer.folder.none"))
        self.output_folder_var.set(t("bulk_summarizer.folder.default_parent"))
        self.progress_bar.set(0)
        self.progress_text_var.set(
            t("bulk_summarizer.progress.files").format(current=0, total=0)
        )
        self.current_file_var.set(t("bulk_summarizer.progress.idle"))
        self.status_log.configure(state="normal")
        self.status_log.delete('1.0', tk.END)
        self.status_log.configure(state="disabled")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="disabled")

    def set_summarizer_tab(self, tab):
        """Set reference to SummarizerTab for inheriting LLM settings."""
        self.summarizer_tab = tab
        logger.info("BulkSummarizerTab linked to SummarizerTab for LLM settings")

    def get_summarizer_settings(self) -> dict:
        """Returns LLM settings read from the SummarizerTab instance."""
        if not self.summarizer_tab:
            return None
        return {
            'provider': self.summarizer_tab.get_provider(),
            'webhook_url': self.summarizer_tab.get_webhook_url(),
            'model_name': self.summarizer_tab.get_model_name(),
            'prompt': self.summarizer_tab.get_prompt(),
        }

    def get_content(self) -> str:
        return self.status_log.get('1.0', tk.END)

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def _on_start_clicked(self):
        # Refresh LLM settings display before starting
        self._refresh_llm_settings_display()
        if self.on_start_requested:
            self.on_start_requested()

    def _refresh_llm_settings_display(self):
        """Update the LLM settings info panel with current values from Summarizer tab"""
        settings = self.get_summarizer_settings() if self.summarizer_tab else None

        if not settings:
            self.provider_info_var.set(
                t("bulk_summarizer.llm.provider_not_connected") if not self.summarizer_tab
                else t("bulk_summarizer.llm.provider_not_configured")
            )
            self.webhook_info_var.set(t("bulk_summarizer.llm.base_url_not_configured"))
            self.model_info_var.set(t("bulk_summarizer.llm.model_not_selected"))
            self.prompt_info_var.set(t("bulk_summarizer.llm.prompt_not_selected"))
            return

        prompt = settings['prompt'] or ""
        prompt_preview = (prompt[:50] + "...") if len(prompt) > 50 else prompt

        self.provider_info_var.set(
            t("bulk_summarizer.llm.provider").format(value=settings['provider'])
        )
        self.webhook_info_var.set(
            t("bulk_summarizer.llm.base_url").format(value=settings['webhook_url'])
        )
        self.model_info_var.set(
            t("bulk_summarizer.llm.model").format(value=settings['model_name'])
        )
        self.prompt_info_var.set(
            t("bulk_summarizer.llm.prompt").format(value=prompt_preview)
        )

    def _on_cancel_clicked(self):
        if self.on_cancel_requested:
            self.on_cancel_requested()

    def set_on_start_requested(self, callback):
        self.on_start_requested = callback

    def set_on_cancel_requested(self, callback):
        self.on_cancel_requested = callback

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    _PREF_FILE_TYPES = "BULK_FILE_TYPES"
    _PREF_SEPARATE = "BULK_OUTPUT_SEPARATE"
    _PREF_COMBINED = "BULK_OUTPUT_COMBINED"
    _PREF_RECURSIVE = "BULK_RECURSIVE_SUBFOLDERS"

    def _load_preferences(self):
        """Load saved preferences via SettingsManager."""
        if self.settings is None:
            logger.debug("No SettingsManager; using default bulk preferences")
            return
        try:
            file_types = self.settings.get(self._PREF_FILE_TYPES, "txt")
            selected = {p.strip() for p in file_types.split(",") if p.strip()}
            self.file_type_txt.set("txt" in selected)
            self.file_type_srt.set("srt" in selected)
            self.file_type_docx.set("docx" in selected)
            self.file_type_pdf.set("pdf" in selected)
            self.file_type_opus.set("opus" in selected)

            self.output_separate.set(
                self.settings.get(self._PREF_SEPARATE, "True").lower() == "true"
            )
            self.output_combined.set(
                self.settings.get(self._PREF_COMBINED, "False").lower() == "true"
            )
            self.recursive_subfolders.set(
                self.settings.get(self._PREF_RECURSIVE, "False").lower() == "true"
            )
            logger.info("Bulk Summarizer preferences loaded")
        except Exception as e:
            logger.warning(f"Could not load preferences: {str(e)}")

    def _save_preferences(self):
        """
        Save preferences via SettingsManager.

        SettingsManager rewrites only the values it owns and leaves comments and
        unrelated keys untouched, which the previous hand-rolled writer did not.
        """
        if self.settings is None:
            return
        try:
            file_types = self.get_file_types()
            self.settings.set(
                self._PREF_FILE_TYPES, ",".join(file_types) if file_types else "txt"
            )
            self.settings.set(self._PREF_SEPARATE, str(self.output_separate.get()))
            self.settings.set(self._PREF_COMBINED, str(self.output_combined.get()))
            self.settings.set(self._PREF_RECURSIVE, str(self.recursive_subfolders.get()))
            logger.info("Bulk Summarizer preferences saved")
        except Exception as e:
            logger.warning(f"Could not save preferences: {str(e)}")

    # ------------------------------------------------------------------
    # Theming hook used by MainWindow
    # ------------------------------------------------------------------

    def apply_font_size(self, size: int):
        """
        Apply the app-wide font size to this tab's log area.

        Labels, controls and section headings are scaled centrally by
        :func:`views.ctk_theme.apply_font_scale`.
        """
        from views.ctk_theme import font_sizes
        self.status_log.configure(font=("Cascadia Mono", font_sizes(size)["mono"]))
