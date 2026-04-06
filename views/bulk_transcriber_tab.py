"""
Bulk Transcriber Tab - v1.2 Scrollable left column for HiDPI displays

Manages the bulk audio/video transcription interface:
- Media type selection with multiple checkboxes (mp4, mp3, wav, m4a, flac, aac, wma, mov, avi, mkv, webm)
- Output format options with checkmarks (SRT, TXT, VTT, JSON)
- Folder selection with browse button
- Output location selection (default parent folder or custom)
- Recursive subfolder scanning option
- Progress tracking
- Status logging
- Remember last choice in .env
- Scrollable left column for HiDPI / high Windows display scaling (NEW v1.2)

Layout (v1.2):
- Row 0: Browse section (100% width)
- Row 1: Left scrollable column (controls) + Right column (status log)

Version: 1.2
Created: 2026-01-06
Phase: v5.0 - Bulk Transcription
Updated: 2026-01-06 (v5.0.1 - Two-column layout + Start button fix)
Updated: 2026-03-15 (v1.2 - Scrollable left column for HiDPI)
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from datetime import datetime
import os
from views.base_tab import BaseTab
from utils.logger import logger


class BulkTranscriberTab(BaseTab):
    """UI for bulk media transcription (v1.2 - scrollable left panel)"""

    def __init__(self, notebook):
        # CRITICAL: Initialize variables BEFORE calling super().__init__()
        self.notebook = notebook
        self.source_folder_var = tk.StringVar(value="[No folder selected]")
        self.output_folder_var = tk.StringVar(value="[Default (Parent folder)]")

        # Media type selections (video and audio formats)
        # Video formats
        self.media_type_mp4  = tk.BooleanVar(value=True)
        self.media_type_mov  = tk.BooleanVar(value=False)
        self.media_type_avi  = tk.BooleanVar(value=False)
        self.media_type_mkv  = tk.BooleanVar(value=False)
        self.media_type_webm = tk.BooleanVar(value=False)

        # Audio formats
        self.media_type_mp3  = tk.BooleanVar(value=False)
        self.media_type_wav  = tk.BooleanVar(value=False)
        self.media_type_m4a  = tk.BooleanVar(value=False)
        self.media_type_flac = tk.BooleanVar(value=False)
        self.media_type_aac  = tk.BooleanVar(value=False)
        self.media_type_wma  = tk.BooleanVar(value=False)
        self.media_type_opus = tk.BooleanVar(value=False)

        # Output format options (transcript formats)
        self.output_format_srt  = tk.BooleanVar(value=True)
        self.output_format_txt  = tk.BooleanVar(value=False)
        self.output_format_vtt  = tk.BooleanVar(value=False)
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
        logger.info("BulkTranscriberTab initialized (v1.2)")

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

        self._setup_folder_selection()
        self._setup_scrollable_left_panel()
        self._setup_status_log()

    def _setup_scrollable_left_panel(self):
        """
        Wraps all left-column controls inside a Canvas so they can be
        scrolled vertically when the window is too small (e.g. 125%+
        Windows DPI scaling). Mousewheel also works.
        """
        outer = ttk.Frame(self)
        outer.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=0, pady=0)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        canvas = tk.Canvas(outer, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))

        inner = ttk.Frame(canvas)
        inner.columnconfigure(0, weight=1)
        canvas_window = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        inner.bind("<Configure>", _on_inner_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self._left_inner = inner

        # Build all control sections inside scrollable inner frame
        self._setup_media_type_video()
        self._setup_media_type_audio()
        self._setup_recursive_option()
        self._setup_output_format()
        self._setup_output_location()
        self._setup_processing_section()
        self._setup_progress_section()

    def _setup_folder_selection(self):
        """Folder selection - full width at top (row 0)"""
        folder_frame = ttk.LabelFrame(self, text="Select Media Folder")
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
        folder = filedialog.askdirectory(title="Select folder with media files to transcribe")
        if folder:
            self.source_folder_var.set(folder)
            file_count = self._count_matching_files(folder)
            self.append_log(
                f"Folder selected: {Path(folder).name} ({file_count} matching media files)",
                "info"
            )
            if file_count > 0:
                self.start_button.config(state=tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)
                self.append_log("No media files found in selected folder", "warning")
            self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")

    def _count_matching_files(self, folder: str) -> int:
        """Count media files matching selected types"""
        folder_path = Path(folder)
        count = 0
        glob_method = folder_path.rglob if self.recursive_subfolders.get() else folder_path.glob

        type_patterns = [
            (self.media_type_mp4,  "*.mp4"),
            (self.media_type_mov,  "*.mov"),
            (self.media_type_avi,  "*.avi"),
            (self.media_type_mkv,  "*.mkv"),
            (self.media_type_webm, "*.webm"),
            (self.media_type_mp3,  "*.mp3"),
            (self.media_type_wav,  "*.wav"),
            (self.media_type_m4a,  "*.m4a"),
            (self.media_type_flac, "*.flac"),
            (self.media_type_aac,  "*.aac"),
            (self.media_type_wma,  "*.wma"),
            (self.media_type_opus, "*.opus"),
        ]
        for var, pattern in type_patterns:
            if var.get():
                count += len(list(glob_method(pattern)))
        return count

    def _setup_media_type_video(self):
        """Checkboxes for video format selection - inside scrollable left panel"""
        video_frame = ttk.LabelFrame(self._left_inner, text="Video Formats")
        video_frame.pack(fill=tk.X, padx=10, pady=10)

        formats = [
            ("MP4 (Default)", self.media_type_mp4),
            ("MOV",           self.media_type_mov),
            ("AVI",           self.media_type_avi),
            ("MKV",           self.media_type_mkv),
            ("WebM",          self.media_type_webm),
        ]
        for label, var in formats:
            ttk.Checkbutton(
                video_frame, text=label, variable=var,
                command=self._on_media_type_changed
            ).pack(anchor=tk.W, padx=10, pady=3)

    def _setup_media_type_audio(self):
        """Checkboxes for audio format selection - inside scrollable left panel"""
        audio_frame = ttk.LabelFrame(self._left_inner, text="Audio Formats")
        audio_frame.pack(fill=tk.X, padx=10, pady=10)

        formats = [
            ("MP3",  self.media_type_mp3),
            ("WAV",  self.media_type_wav),
            ("M4A",  self.media_type_m4a),
            ("FLAC", self.media_type_flac),
            ("AAC",  self.media_type_aac),
            ("WMA",  self.media_type_wma),
            ("OPUS", self.media_type_opus),
        ]
        for label, var in formats:
            ttk.Checkbutton(
                audio_frame, text=label, variable=var,
                command=self._on_media_type_changed
            ).pack(anchor=tk.W, padx=10, pady=3)

    def _any_media_type_selected(self) -> bool:
        return any([
            self.media_type_mp4.get(),  self.media_type_mov.get(),
            self.media_type_avi.get(),  self.media_type_mkv.get(),
            self.media_type_webm.get(), self.media_type_mp3.get(),
            self.media_type_wav.get(),  self.media_type_m4a.get(),
            self.media_type_flac.get(), self.media_type_aac.get(),
            self.media_type_wma.get(),  self.media_type_opus.get(),
        ])

    def _update_start_button_state(self):
        if not self._any_media_type_selected():
            self.start_button.config(state=tk.DISABLED)
            return
        folder = self.get_source_folder()
        if not folder:
            self.start_button.config(state=tk.DISABLED)
            return
        file_count = self._count_matching_files(folder)
        self.start_button.config(state=tk.NORMAL if file_count > 0 else tk.DISABLED)

    def _on_media_type_changed(self):
        if not self._any_media_type_selected():
            self.append_log("At least one media format must be selected", "warning")
        self._update_start_button_state()
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
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            label = "with subfolders" if self.recursive_subfolders.get() else "without subfolders"
            self.append_log(
                f"Scanning mode updated ({label}): {file_count} matching files", "info"
            )
            self._update_start_button_state()
        self._save_preferences()

    def _setup_output_format(self):
        """Checkboxes for transcript output format options - inside scrollable left panel"""
        output_frame = ttk.LabelFrame(self._left_inner, text="Output Transcript Formats")
        output_frame.pack(fill=tk.X, padx=10, pady=10)

        formats = [
            ("SRT (Default - Subtitles)", self.output_format_srt),
            ("TXT (Plain text)",           self.output_format_txt),
            ("VTT (WebVTT format)",        self.output_format_vtt),
            ("JSON (Structured data)",     self.output_format_json),
        ]
        for label, var in formats:
            ttk.Checkbutton(
                output_frame, text=label, variable=var,
                command=self._save_preferences
            ).pack(anchor=tk.W, padx=10, pady=3)

        ttk.Label(
            output_frame,
            text="Note: At least one output format must be selected",
            foreground="gray",
            font=("TkDefaultFont", 9)
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
        if self.output_location_default.get():
            folder = self.get_source_folder()
            if folder:
                self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")

    def _browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select output folder for transcripts")
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
            text="Start Transcribing",
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

    def get_media_types(self) -> list:
        types = []
        if self.media_type_mp4.get():  types.append("mp4")
        if self.media_type_mov.get():  types.append("mov")
        if self.media_type_avi.get():  types.append("avi")
        if self.media_type_mkv.get():  types.append("mkv")
        if self.media_type_webm.get(): types.append("webm")
        if self.media_type_mp3.get():  types.append("mp3")
        if self.media_type_wav.get():  types.append("wav")
        if self.media_type_m4a.get():  types.append("m4a")
        if self.media_type_flac.get(): types.append("flac")
        if self.media_type_aac.get():  types.append("aac")
        if self.media_type_wma.get():  types.append("wma")
        if self.media_type_opus.get(): types.append("opus")
        return types

    def get_output_formats(self) -> dict:
        return {
            "srt":  self.output_format_srt.get(),
            "txt":  self.output_format_txt.get(),
            "vtt":  self.output_format_vtt.get(),
            "json": self.output_format_json.get(),
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
        logger.debug(
            f"Bulk Transcriber Start button clicked. "
            f"Callback registered: {self.on_start_requested is not None}"
        )
        if self.on_start_requested:
            self.on_start_requested()
        else:
            logger.warning("No start callback registered for Bulk Transcriber!")
            self.append_log("ERROR: Start callback not registered. Check main.py", "error")

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

    def _load_preferences(self):
        """Load saved preferences from .env file"""
        try:
            env_path = Path(".env")
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("BULK_TRANS_MEDIA_TYPES="):
                            media_types = line.split("=")[1].split(",")
                            self.media_type_mp4.set("mp4"   in media_types)
                            self.media_type_mov.set("mov"   in media_types)
                            self.media_type_avi.set("avi"   in media_types)
                            self.media_type_mkv.set("mkv"   in media_types)
                            self.media_type_webm.set("webm" in media_types)
                            self.media_type_mp3.set("mp3"   in media_types)
                            self.media_type_wav.set("wav"   in media_types)
                            self.media_type_m4a.set("m4a"   in media_types)
                            self.media_type_flac.set("flac" in media_types)
                            self.media_type_aac.set("aac"   in media_types)
                            self.media_type_wma.set("wma"   in media_types)
                            self.media_type_opus.set("opus" in media_types)
                        elif line.startswith("BULK_TRANS_OUTPUT_FORMATS="):
                            output_formats = line.split("=")[1].split(",")
                            self.output_format_srt.set("srt"   in output_formats)
                            self.output_format_txt.set("txt"   in output_formats)
                            self.output_format_vtt.set("vtt"   in output_formats)
                            self.output_format_json.set("json" in output_formats)
                        elif line.startswith("BULK_TRANS_RECURSIVE_SUBFOLDERS="):
                            self.recursive_subfolders.set(
                                line.split("=")[1].lower() == "true"
                            )
            logger.info("Bulk Transcriber preferences loaded")
        except Exception as e:
            logger.warning(f"Could not load preferences: {str(e)}")

    def _save_preferences(self):
        """Save preferences to .env file"""
        try:
            env_path = Path(".env")

            media_types = []
            if self.media_type_mp4.get():  media_types.append("mp4")
            if self.media_type_mov.get():  media_types.append("mov")
            if self.media_type_avi.get():  media_types.append("avi")
            if self.media_type_mkv.get():  media_types.append("mkv")
            if self.media_type_webm.get(): media_types.append("webm")
            if self.media_type_mp3.get():  media_types.append("mp3")
            if self.media_type_wav.get():  media_types.append("wav")
            if self.media_type_m4a.get():  media_types.append("m4a")
            if self.media_type_flac.get(): media_types.append("flac")
            if self.media_type_aac.get():  media_types.append("aac")
            if self.media_type_wma.get():  media_types.append("wma")
            if self.media_type_opus.get(): media_types.append("opus")

            output_formats = []
            if self.output_format_srt.get():  output_formats.append("srt")
            if self.output_format_txt.get():  output_formats.append("txt")
            if self.output_format_vtt.get():  output_formats.append("vtt")
            if self.output_format_json.get(): output_formats.append("json")

            media_types_str   = ",".join(media_types)   if media_types   else "mp4"
            output_formats_str = ",".join(output_formats) if output_formats else "srt"

            env_content = {}
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("BULK_TRANS_"):
                            kv = line.split("=", 1)
                            if len(kv) == 2:
                                env_content[kv[0]] = kv[1]

            env_content["BULK_TRANS_MEDIA_TYPES"]          = media_types_str
            env_content["BULK_TRANS_OUTPUT_FORMATS"]       = output_formats_str
            env_content["BULK_TRANS_RECURSIVE_SUBFOLDERS"] = str(self.recursive_subfolders.get())

            with open(env_path, "w") as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")

            logger.info("Bulk Transcriber preferences saved")
        except Exception as e:
            logger.warning(f"Could not save preferences: {str(e)}")
