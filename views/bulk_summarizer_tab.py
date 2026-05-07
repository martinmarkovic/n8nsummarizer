"""
Bulk Summarizer Tab - v5.1 (.opus support + scrollable left column)

Manages the bulk file summarization interface:
- File type selection with multiple checkboxes (txt, srt, docx, pdf, opus)
- Output format options (separate files, combined file)
- Output location selection (default or custom)
- Recursive subfolder scanning option
- Progress tracking
- Status logging
- Remember last choice in .env
- Scrollable left column for HiDPI / high Windows display scaling (NEW v5.1)

Layout (v5.1):
- Row 0: Browse section (100% width)
- Row 1: Left scrollable column (controls) + Right column (status log)

Version: 5.1
Created: 2025-12-10
Updated: 2026-01-06 (v4.7 - Added recursive subfolder support)
Updated: 2026-01-06 (v5.0.1 - Two-column layout)
Updated: 2026-03-15 (v5.1 - .opus support + scrollable left column)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from datetime import datetime
import os
from views.base_tab import BaseTab
from utils.logger import logger
from utils.prompt_manager import PromptManager


class BulkSummarizerTab(BaseTab):
    """UI for bulk file summarization (v5.1 - .opus + scrollable left column)"""

    def __init__(self, notebook, prompt_manager=None):
        self.notebook = notebook
        self.source_folder_var = tk.StringVar(value="[No folder selected]")
        self.output_folder_var = tk.StringVar(value="[Default (Parent folder)]")

        # File type selections
        self.file_type_txt = tk.BooleanVar(value=True)
        self.file_type_srt = tk.BooleanVar(value=False)
        self.file_type_docx = tk.BooleanVar(value=False)
        self.file_type_pdf = tk.BooleanVar(value=False)
        self.file_type_opus = tk.BooleanVar(value=False)  # NEW v5.1

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

        # Callback registration
        self.on_start_requested = None
        self.on_cancel_requested = None

        super().__init__(notebook, "\U0001f4e6 Bulk Summarizer")
        self._load_preferences()
        logger.info("BulkSummarizerTab initialized (v5.1)")

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """
        Two-column layout.
        Column 0: scrollable left panel (all controls)
        Column 1: status log (expands)
        """
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=0)  # browse row - fixed
        self.rowconfigure(1, weight=1)  # main content row - expands

        # Row 0: Browse (full width)
        self._setup_folder_selection()

        # Row 1 Col 0: Scrollable left panel
        self._setup_scrollable_left_panel()

        # Row 1 Col 1: Status log
        self._setup_status_log()

    def _setup_scrollable_left_panel(self):
        """
        Wraps all left-column controls inside a Canvas so they can be
        scrolled vertically when the window is too small (e.g. 150%+
        Windows DPI scaling). Mousewheel also works.
        """
        # Outer frame that sits in the grid
        outer = ttk.Frame(self)
        outer.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=0, pady=0)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        # Canvas + vertical scrollbar
        canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))

        # Inner frame that holds all control widgets
        inner = ttk.Frame(canvas)
        inner.columnconfigure(0, weight=1)
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            # Keep inner frame width = canvas width
            canvas.itemconfig(canvas_window, width=event.width)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Keep a reference so control setup methods can pack into it
        self._left_inner = inner

        # Build all left-column control sections inside inner frame
        self._setup_file_type()
        self._setup_recursive_option()
        self._setup_output_format()
        self._setup_output_location()
        self._setup_processing_section()
        self._setup_progress_section()

    def _setup_folder_selection(self):
        """Folder selection - full width at top (row 0)"""
        folder_frame = ttk.LabelFrame(self, text="Select Source Folder")
        folder_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=10, pady=10)
        folder_frame.columnconfigure(1, weight=1)

        ttk.Button(
            folder_frame,
            text="[Browse...]",
            command=self._browse_folder
        ).pack(side=tk.LEFT, padx=5, pady=5)

        ttk.Label(
            folder_frame,
            textvariable=self.source_folder_var
        ).pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)

    def _browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title="Select folder to summarize")
        if folder:
            self.source_folder_var.set(folder)
            file_count = self._count_matching_files(folder)
            self.append_log(
                f"Folder selected: {Path(folder).name} ({file_count} matching files)",
                "info"
            )
            if file_count > 0:
                self.start_button.config(state=tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)
                self.append_log("No matching files found", "warning")
            self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")

    def _count_matching_files(self, folder: str) -> int:
        """Count files matching selected types"""
        folder_path = Path(folder)
        count = 0
        use_rglob = self.recursive_subfolders.get()

        type_patterns = [
            (self.file_type_txt,  "*.txt"),
            (self.file_type_srt,  "*.srt"),
            (self.file_type_docx, "*.docx"),
            (self.file_type_pdf,  "*.pdf"),
            (self.file_type_opus, "*.opus"),  # NEW v5.1
        ]
        for var, pattern in type_patterns:
            if var.get():
                if use_rglob:
                    count += len(list(folder_path.rglob(pattern)))
                else:
                    count += len(list(folder_path.glob(pattern)))
        return count

    def _setup_file_type(self):
        """Checkboxes for file type selection - inside scrollable left panel"""
        type_frame = ttk.LabelFrame(self._left_inner, text="File Types to Scan")
        type_frame.pack(fill=tk.X, padx=10, pady=10)

        files = [
            ("TXT",                self.file_type_txt),
            ("SRT (Subtitles)",    self.file_type_srt),
            ("DOCX",               self.file_type_docx),
            ("PDF",                self.file_type_pdf),
            ("OPUS (Audio transcript)", self.file_type_opus),  # NEW v5.1
        ]

        for label, var in files:
            ttk.Checkbutton(
                type_frame,
                text=label,
                variable=var,
                command=self._on_file_type_changed
            ).pack(anchor=tk.W, padx=10, pady=5)

    def _on_file_type_changed(self):
        """Called when file type selection changes"""
        if not any([
            self.file_type_txt.get(), self.file_type_srt.get(),
            self.file_type_docx.get(), self.file_type_pdf.get(),
            self.file_type_opus.get()
        ]):
            self.append_log("At least one file type must be selected", "warning")
            self.start_button.config(state=tk.DISABLED)
            return

        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            self.append_log(f"File types updated: {file_count} matching files", "info")
            self.start_button.config(state=tk.NORMAL if file_count > 0 else tk.DISABLED)
        self._save_preferences()

    def _setup_recursive_option(self):
        """Recursive subfolder scanning checkbox - inside scrollable left panel"""
        recursive_frame = ttk.LabelFrame(self._left_inner, text="Scanning Options")
        recursive_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Checkbutton(
            recursive_frame,
            text="Scan Subfolders (recursive scanning)",
            variable=self.recursive_subfolders,
            command=self._on_recursive_changed
        ).pack(anchor=tk.W, padx=10, pady=5)

        ttk.Label(
            recursive_frame,
            text="When enabled: Scans all subfolders and maintains folder structure in output",
            foreground="gray",
            font=("TkDefaultFont", 9)
        ).pack(anchor=tk.W, padx=30, pady=(0, 5))

    def _on_recursive_changed(self):
        """Called when recursive subfolder option changes"""
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            label = "with subfolders" if self.recursive_subfolders.get() else "without subfolders"
            self.append_log(f"Scanning mode updated ({label}): {file_count} matching files", "info")
            self.start_button.config(state=tk.NORMAL if file_count > 0 else tk.DISABLED)
        self._save_preferences()

    def _setup_output_format(self):
        """Output format checkboxes - inside scrollable left panel"""
        output_frame = ttk.LabelFrame(self._left_inner, text="Output Format Options")
        output_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Checkbutton(
            output_frame,
            text="Separate Files (Uncombined)",
            variable=self.output_separate
        ).pack(anchor=tk.W, padx=10, pady=5)

        ttk.Checkbutton(
            output_frame,
            text="Combined File (Single output)",
            variable=self.output_combined
        ).pack(anchor=tk.W, padx=10, pady=5)

        ttk.Label(
            output_frame,
            text="Note: At least one output format must be selected",
            foreground="gray"
        ).pack(anchor=tk.W, padx=10, pady=(10, 5))

    def _setup_output_location(self):
        """Output location radio buttons - inside scrollable left panel"""
        loc_frame = ttk.LabelFrame(self._left_inner, text="Output Location")
        loc_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Radiobutton(
            loc_frame,
            text="Default (Parent folder of source)",
            variable=self.output_location_default,
            value=True,
            command=self._on_output_location_changed
        ).pack(anchor=tk.W, padx=10, pady=5)

        button_frame = ttk.Frame(loc_frame)
        button_frame.pack(anchor=tk.W, padx=10, pady=5)

        ttk.Radiobutton(
            button_frame,
            text="Custom Location:",
            variable=self.output_location_default,
            value=False,
            command=self._on_output_location_changed
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            button_frame,
            text="[Browse...]",
            command=self._browse_output_folder
        ).pack(side=tk.LEFT, padx=5)

        ttk.Label(
            loc_frame,
            textvariable=self.output_folder_var
        ).pack(anchor=tk.W, padx=30, pady=5)

    def _on_output_location_changed(self):
        """Called when output location changes"""
        if self.output_location_default.get():
            folder = self.get_source_folder()
            if folder:
                self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")

    def _browse_output_folder(self):
        """Open folder selection dialog for output"""
        folder = filedialog.askdirectory(title="Select output folder for summaries")
        if folder:
            self.output_folder_var.set(folder)
            self.output_location_default.set(False)
            self.append_log(f"Output folder set to: {Path(folder).name}", "info")

    def _setup_processing_section(self):
        """Start/Cancel buttons - inside scrollable left panel"""
        proc_frame = ttk.LabelFrame(self._left_inner, text="Processing")
        proc_frame.pack(fill=tk.X, padx=10, pady=10)

        info_frame = ttk.Frame(proc_frame)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_label = ttk.Label(info_frame, text="Ready", foreground="green")
        self.status_label.pack(side=tk.LEFT)

        button_frame = ttk.Frame(proc_frame)
        button_frame.pack(pady=10)

        self.start_button = ttk.Button(
            button_frame,
            text="Start Processing",
            command=self._on_start_clicked,
            state=tk.DISABLED
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel_clicked,
            state=tk.DISABLED
        )
        self.cancel_button.pack(side=tk.LEFT, padx=5)

    def _setup_progress_section(self):
        """Progress bar - inside scrollable left panel"""
        prog_frame = ttk.LabelFrame(self._left_inner, text="Progress")
        prog_frame.pack(fill=tk.X, padx=10, pady=10)

        self.current_file_var = tk.StringVar(value="Idle")
        ttk.Label(prog_frame, textvariable=self.current_file_var).pack(
            anchor=tk.W, padx=10, pady=5
        )

        self.progress_bar = ttk.Progressbar(
            prog_frame,
            mode='determinate',
            length=300
        )
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)

        self.progress_text_var = tk.StringVar(value="0 / 0 files")
        ttk.Label(prog_frame, textvariable=self.progress_text_var).pack(
            anchor=tk.W, padx=10, pady=5
        )

    def _setup_status_log(self):
        """Status log with scroll - right column (row 1, col 1)"""
        log_frame = ttk.LabelFrame(self, text="Status Log")
        log_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_source_folder(self) -> str:
        folder = self.source_folder_var.get()
        return folder if folder != "[No folder selected]" else None

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
        if self.file_type_txt.get():  types.append("txt")
        if self.file_type_srt.get():  types.append("srt")
        if self.file_type_docx.get(): types.append("docx")
        if self.file_type_pdf.get():  types.append("pdf")
        if self.file_type_opus.get(): types.append("opus")  # NEW v5.1
        return types

    def get_output_formats(self) -> dict:
        return {
            "separate": self.output_separate.get(),
            "combined": self.output_combined.get()
        }

    def get_recursive_option(self) -> bool:
        return self.recursive_subfolders.get()

    def set_processing_enabled(self, enabled: bool):
        self.start_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL if enabled else tk.DISABLED)

    def update_progress(self, current: int, total: int):
        percentage = (current / total * 100) if total > 0 else 0
        self.progress_bar['value'] = percentage
        self.progress_text_var.set(f"{current} / {total} files")

    def set_current_file(self, filename: str):
        self.current_file_var.set(f"Processing: {filename}")

    def append_log(self, message: str, status: str = "info"):
        self.status_log.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        indicators = {"success": "\u2713", "error": "\u2717", "info": "\u2022", "warning": "\u26a0"}
        indicator = indicators.get(status, "\u2022")
        self.status_log.insert(tk.END, f"[{timestamp}] {indicator} {message}\n")
        self.status_log.see(tk.END)
        self.status_log.config(state=tk.DISABLED)

    def clear_all(self):
        self.source_folder_var.set("[No folder selected]")
        self.output_folder_var.set("[Default (Parent folder)]")
        self.progress_bar['value'] = 0
        self.progress_text_var.set("0 / 0 files")
        self.current_file_var.set("Idle")
        self.status_log.config(state=tk.NORMAL)
        self.status_log.delete('1.0', tk.END)
        self.status_log.config(state=tk.DISABLED)
        self.start_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)

    def get_content(self) -> str:
        return self.status_log.get('1.0', tk.END)

    # ------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------

    def _on_start_clicked(self):
        if self.on_start_requested:
            self.on_start_requested()

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

    def _load_preferences(self):
        """Load saved preferences from .env file"""
        try:
            env_path = Path(".env")
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("BULK_FILE_TYPES="):
                            file_types = line.split("=")[1].split(",")
                            self.file_type_txt.set("txt" in file_types)
                            self.file_type_srt.set("srt" in file_types)
                            self.file_type_docx.set("docx" in file_types)
                            self.file_type_pdf.set("pdf" in file_types)
                            self.file_type_opus.set("opus" in file_types)  # NEW v5.1
                        elif line.startswith("BULK_OUTPUT_SEPARATE="):
                            self.output_separate.set(line.split("=")[1].lower() == "true")
                        elif line.startswith("BULK_OUTPUT_COMBINED="):
                            self.output_combined.set(line.split("=")[1].lower() == "true")
                        elif line.startswith("BULK_RECURSIVE_SUBFOLDERS="):
                            self.recursive_subfolders.set(line.split("=")[1].lower() == "true")
            logger.info("Bulk Summarizer preferences loaded")
        except Exception as e:
            logger.warning(f"Could not load preferences: {str(e)}")

    def _save_preferences(self):
        """Save preferences to .env file"""
        try:
            env_path = Path(".env")
            file_types = []
            if self.file_type_txt.get():  file_types.append("txt")
            if self.file_type_srt.get():  file_types.append("srt")
            if self.file_type_docx.get(): file_types.append("docx")
            if self.file_type_pdf.get():  file_types.append("pdf")
            if self.file_type_opus.get(): file_types.append("opus")  # NEW v5.1

            file_types_str = ",".join(file_types) if file_types else "txt"

            env_content = {}
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("BULK_"):
                            kv = line.split("=", 1)
                            if len(kv) == 2:
                                env_content[kv[0]] = kv[1]

            env_content["BULK_FILE_TYPES"] = file_types_str
            env_content["BULK_OUTPUT_SEPARATE"] = str(self.output_separate.get())
            env_content["BULK_OUTPUT_COMBINED"] = str(self.output_combined.get())
            env_content["BULK_RECURSIVE_SUBFOLDERS"] = str(self.recursive_subfolders.get())

            with open(env_path, "w") as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")

            logger.info("Bulk Summarizer preferences saved")
        except Exception as e:
            logger.warning(f"Could not save preferences: {str(e)}")
