"""
Bulk Transcriber Tab - Phase 5.0 Bulk Transcription Support

Manages the bulk audio/video transcription interface:
- Media type selection with multiple checkboxes (mp4, mp3, wav, m4a, flac, aac, wma, mov, avi, mkv, webm)
- Output format options with checkmarks (SRT, TXT, VTT, JSON)
- Folder selection with browse button
- Output location selection (default parent folder or custom)
- Recursive subfolder scanning option
- Progress tracking
- Status logging
- Remember last choice in .env

Version: 1.0
Created: 2026-01-06
Phase: v5.0 - Bulk Transcription
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from datetime import datetime
import os
from views.base_tab import BaseTab
from utils.logger import logger


class BulkTranscriberTab(BaseTab):
    """UI for bulk media transcription (Phase 5.0)"""
    
    def __init__(self, notebook):
        # CRITICAL: Initialize variables BEFORE calling super().__init__()
        self.notebook = notebook
        self.source_folder_var = tk.StringVar(value="[No folder selected]")
        self.output_folder_var = tk.StringVar(value="[Default (Parent folder)]")
        
        # Media type selections (video and audio formats)
        # Video formats
        self.media_type_mp4 = tk.BooleanVar(value=True)      # Default
        self.media_type_mov = tk.BooleanVar(value=False)
        self.media_type_avi = tk.BooleanVar(value=False)
        self.media_type_mkv = tk.BooleanVar(value=False)
        self.media_type_webm = tk.BooleanVar(value=False)
        
        # Audio formats
        self.media_type_mp3 = tk.BooleanVar(value=False)
        self.media_type_wav = tk.BooleanVar(value=False)
        self.media_type_m4a = tk.BooleanVar(value=False)
        self.media_type_flac = tk.BooleanVar(value=False)
        self.media_type_aac = tk.BooleanVar(value=False)
        self.media_type_wma = tk.BooleanVar(value=False)
        
        # Output format options (transcript formats)
        self.output_format_srt = tk.BooleanVar(value=True)   # Default
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
        
        # NOW call parent init (which calls _setup_ui())
        super().__init__(notebook, "🎬 Bulk Transcriber")
        
        # Load saved preferences from .env
        self._load_preferences()
        
        logger.info("BulkTranscriberTab initialized")
    
    def _setup_ui(self):
        """
        Setup bulk transcriber UI.
        
        Sections:
        1. Folder Selection
        2. Media Type Selection (Checkboxes - Video)
        3. Media Type Selection (Checkboxes - Audio)
        4. Scanning Options (Recursive)
        5. Output Format Options (Checkboxes)
        6. Output Location Selection
        7. Processing Controls
        8. Progress Tracking
        9. Status Log
        """
        # Make tab expand
        self.columnconfigure(0, weight=1)
        self.rowconfigure(8, weight=1)
        
        self._setup_folder_selection()
        self._setup_media_type_video()      # NEW: Video formats
        self._setup_media_type_audio()      # NEW: Audio formats
        self._setup_recursive_option()
        self._setup_output_format()
        self._setup_output_location()
        self._setup_processing_section()
        self._setup_progress_section()
        self._setup_status_log()
    
    def _setup_folder_selection(self):
        """Folder selection with browse button"""
        folder_frame = ttk.LabelFrame(self, text="Select Media Folder")
        folder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        folder_frame.columnconfigure(1, weight=1)
        
        ttk.Button(
            folder_frame,
            text="[Browse...]",
            command=self._browse_folder
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(
            folder_frame,
            textvariable=self.source_folder_var
        ).pack(side=tk.LEFT, padx=10, pady=5)
    
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
            # Enable start button if media files found
            if file_count > 0:
                self.start_button.config(state=tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)
                self.append_log("No media files found in selected folder", "warning")
            
            # Auto-set output location to parent folder (default)
            self.output_folder_var.set(f"[Default: {Path(folder).parent.name}]")
    
    def _count_matching_files(self, folder: str) -> int:
        """Count media files matching selected types"""
        folder_path = Path(folder)
        count = 0
        
        # Video formats
        if self.media_type_mp4.get():
            count += len(list(folder_path.rglob("*.mp4") if self.recursive_subfolders.get() else folder_path.glob("*.mp4")))
        if self.media_type_mov.get():
            count += len(list(folder_path.rglob("*.mov") if self.recursive_subfolders.get() else folder_path.glob("*.mov")))
        if self.media_type_avi.get():
            count += len(list(folder_path.rglob("*.avi") if self.recursive_subfolders.get() else folder_path.glob("*.avi")))
        if self.media_type_mkv.get():
            count += len(list(folder_path.rglob("*.mkv") if self.recursive_subfolders.get() else folder_path.glob("*.mkv")))
        if self.media_type_webm.get():
            count += len(list(folder_path.rglob("*.webm") if self.recursive_subfolders.get() else folder_path.glob("*.webm")))
        
        # Audio formats
        if self.media_type_mp3.get():
            count += len(list(folder_path.rglob("*.mp3") if self.recursive_subfolders.get() else folder_path.glob("*.mp3")))
        if self.media_type_wav.get():
            count += len(list(folder_path.rglob("*.wav") if self.recursive_subfolders.get() else folder_path.glob("*.wav")))
        if self.media_type_m4a.get():
            count += len(list(folder_path.rglob("*.m4a") if self.recursive_subfolders.get() else folder_path.glob("*.m4a")))
        if self.media_type_flac.get():
            count += len(list(folder_path.rglob("*.flac") if self.recursive_subfolders.get() else folder_path.glob("*.flac")))
        if self.media_type_aac.get():
            count += len(list(folder_path.rglob("*.aac") if self.recursive_subfolders.get() else folder_path.glob("*.aac")))
        if self.media_type_wma.get():
            count += len(list(folder_path.rglob("*.wma") if self.recursive_subfolders.get() else folder_path.glob("*.wma")))
        
        return count
    
    def _setup_media_type_video(self):
        """Checkboxes for video format selection"""
        video_frame = ttk.LabelFrame(self, text="Video Formats")
        video_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        formats = [
            ("MP4 (Default)", self.media_type_mp4),
            ("MOV", self.media_type_mov),
            ("AVI", self.media_type_avi),
            ("MKV", self.media_type_mkv),
            ("WebM", self.media_type_webm)
        ]
        
        for label, var in formats:
            ttk.Checkbutton(
                video_frame,
                text=label,
                variable=var,
                command=self._on_media_type_changed
            ).pack(anchor=tk.W, padx=10, pady=3)
    
    def _setup_media_type_audio(self):
        """Checkboxes for audio format selection"""
        audio_frame = ttk.LabelFrame(self, text="Audio Formats")
        audio_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        formats = [
            ("MP3", self.media_type_mp3),
            ("WAV", self.media_type_wav),
            ("M4A", self.media_type_m4a),
            ("FLAC", self.media_type_flac),
            ("AAC", self.media_type_aac),
            ("WMA", self.media_type_wma)
        ]
        
        for label, var in formats:
            ttk.Checkbutton(
                audio_frame,
                text=label,
                variable=var,
                command=self._on_media_type_changed
            ).pack(anchor=tk.W, padx=10, pady=3)
    
    def _on_media_type_changed(self):
        """Called when media type selection changes"""
        if not any([self.media_type_mp4.get(), self.media_type_mov.get(), 
                   self.media_type_avi.get(), self.media_type_mkv.get(),
                   self.media_type_webm.get(), self.media_type_mp3.get(),
                   self.media_type_wav.get(), self.media_type_m4a.get(),
                   self.media_type_flac.get(), self.media_type_aac.get(),
                   self.media_type_wma.get()]):
            self.append_log("At least one media format must be selected", "warning")
            self.start_button.config(state=tk.DISABLED)
            return
        
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            self.append_log(
                f"Media formats updated: {file_count} matching files",
                "info"
            )
            if file_count > 0:
                self.start_button.config(state=tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)
        
        self._save_preferences()
    
    def _setup_recursive_option(self):
        """Checkbox for recursive subfolder scanning"""
        recursive_frame = ttk.LabelFrame(self, text="Scanning Options")
        recursive_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        ttk.Checkbutton(
            recursive_frame,
            text="Scan Subfolders (recursive scanning)",
            variable=self.recursive_subfolders,
            command=self._on_recursive_changed
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        info_label = ttk.Label(
            recursive_frame,
            text="When enabled: Scans all subfolders and maintains folder structure in output",
            foreground="gray",
            font=("TkDefaultFont", 9)
        )
        info_label.pack(anchor=tk.W, padx=30, pady=(0, 5))
    
    def _on_recursive_changed(self):
        """Called when recursive subfolder option changes"""
        folder = self.get_source_folder()
        if folder:
            file_count = self._count_matching_files(folder)
            recursive_status = "with subfolders" if self.recursive_subfolders.get() else "without subfolders"
            self.append_log(
                f"Scanning mode updated ({recursive_status}): {file_count} matching files",
                "info"
            )
            if file_count > 0:
                self.start_button.config(state=tk.NORMAL)
            else:
                self.start_button.config(state=tk.DISABLED)
        
        self._save_preferences()
    
    def _setup_output_format(self):
        """Checkboxes for transcript output format options"""
        output_frame = ttk.LabelFrame(self, text="Output Transcript Formats")
        output_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        formats = [
            ("SRT (Default - Subtitles)", self.output_format_srt),
            ("TXT (Plain text)", self.output_format_txt),
            ("VTT (WebVTT format)", self.output_format_vtt),
            ("JSON (Structured data)", self.output_format_json)
        ]
        
        for label, var in formats:
            ttk.Checkbutton(
                output_frame,
                text=label,
                variable=var,
                command=self._save_preferences
            ).pack(anchor=tk.W, padx=10, pady=3)
        
        info_label = ttk.Label(
            output_frame,
            text="Note: At least one output format must be selected",
            foreground="gray",
            font=("TkDefaultFont", 9)
        )
        info_label.pack(anchor=tk.W, padx=10, pady=(10, 5))
    
    def _setup_output_location(self):
        """Radio buttons for output location"""
        loc_frame = ttk.LabelFrame(self, text="Output Location")
        loc_frame.grid(row=5, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        loc_frame.columnconfigure(1, weight=1)
        
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
        folder = filedialog.askdirectory(title="Select output folder for transcripts")
        if folder:
            self.output_folder_var.set(folder)
            self.output_location_default.set(False)
            self.append_log(
                f"Output folder set to: {Path(folder).name}",
                "info"
            )
    
    def _setup_processing_section(self):
        """Start/Cancel buttons"""
        proc_frame = ttk.LabelFrame(self, text="Processing")
        proc_frame.grid(row=6, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        proc_frame.columnconfigure(0, weight=1)
        
        info_frame = ttk.Frame(proc_frame)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(
            info_frame,
            text="Ready",
            foreground="green"
        )
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
        """Progress bar and current file info"""
        prog_frame = ttk.LabelFrame(self, text="Progress")
        prog_frame.grid(row=7, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        prog_frame.columnconfigure(0, weight=1)
        
        self.current_file_var = tk.StringVar(value="Idle")
        ttk.Label(prog_frame, textvariable=self.current_file_var).pack(anchor=tk.W, padx=10, pady=5)
        
        self.progress_bar = ttk.Progressbar(
            prog_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(fill=tk.X, padx=10, pady=10)
        
        self.progress_text_var = tk.StringVar(value="0 / 0 files")
        ttk.Label(prog_frame, textvariable=self.progress_text_var).pack(anchor=tk.W, padx=10, pady=5)
    
    def _setup_status_log(self):
        """Status log with scroll"""
        log_frame = ttk.LabelFrame(self, text="Status Log")
        log_frame.grid(row=8, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), 
                      padx=10, pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.status_log = tk.Text(
            log_frame,
            height=10,
            width=60,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        self.status_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.status_log.yview)
    
    # Public methods
    
    def get_source_folder(self) -> str:
        """Get selected folder path"""
        folder = self.source_folder_var.get()
        return folder if folder != "[No folder selected]" else None
    
    def get_output_folder(self) -> str:
        """Get output folder path"""
        folder = self.source_folder_var.get()
        
        if self.output_location_default.get() and folder:
            return str(Path(folder).parent)
        else:
            output = self.output_folder_var.get()
            return output if "[" not in output else None
    
    def get_media_types(self) -> list:
        """Get selected media types as list"""
        types = []
        # Video formats
        if self.media_type_mp4.get():
            types.append("mp4")
        if self.media_type_mov.get():
            types.append("mov")
        if self.media_type_avi.get():
            types.append("avi")
        if self.media_type_mkv.get():
            types.append("mkv")
        if self.media_type_webm.get():
            types.append("webm")
        # Audio formats
        if self.media_type_mp3.get():
            types.append("mp3")
        if self.media_type_wav.get():
            types.append("wav")
        if self.media_type_m4a.get():
            types.append("m4a")
        if self.media_type_flac.get():
            types.append("flac")
        if self.media_type_aac.get():
            types.append("aac")
        if self.media_type_wma.get():
            types.append("wma")
        return types
    
    def get_output_formats(self) -> dict:
        """Get output format options"""
        return {
            "srt": self.output_format_srt.get(),
            "txt": self.output_format_txt.get(),
            "vtt": self.output_format_vtt.get(),
            "json": self.output_format_json.get()
        }
    
    def get_recursive_option(self) -> bool:
        """Get recursive subfolder scanning option"""
        return self.recursive_subfolders.get()
    
    def set_processing_enabled(self, enabled: bool):
        """Enable/disable processing buttons"""
        self.start_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
        self.cancel_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def update_progress(self, current: int, total: int):
        """Update progress bar and text"""
        percentage = (current / total * 100) if total > 0 else 0
        self.progress_bar['value'] = percentage
        self.progress_text_var.set(f"{current} / {total} files")
    
    def set_current_file(self, filename: str):
        """Update current file being processed"""
        self.current_file_var.set(f"Processing: {filename}")
    
    def append_log(self, message: str, status: str = "info"):
        """Append message to status log"""
        self.status_log.config(state=tk.NORMAL)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        indicators = {
            "success": "✓",
            "error": "✗",
            "info": "•",
            "warning": "⚠"
        }
        indicator = indicators.get(status, "•")
        
        log_line = f"[{timestamp}] {indicator} {message}\n"
        self.status_log.insert(tk.END, log_line)
        self.status_log.see(tk.END)
        self.status_log.config(state=tk.DISABLED)
    
    def clear_all(self):
        """Clear all tab data"""
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
        """Get current tab content (log)"""
        return self.status_log.get('1.0', tk.END)
    
    # Event handlers
    
    def _on_start_clicked(self):
        """Called when Start button clicked"""
        if self.on_start_requested:
            self.on_start_requested()
    
    def _on_cancel_clicked(self):
        """Called when Cancel button clicked"""
        if self.on_cancel_requested:
            self.on_cancel_requested()
    
    # Callback registration
    
    def set_on_start_requested(self, callback):
        """Register callback for start button"""
        self.on_start_requested = callback
    
    def set_on_cancel_requested(self, callback):
        """Register callback for cancel button"""
        self.on_cancel_requested = callback
    
    # Preference management
    
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
                            # Video
                            self.media_type_mp4.set("mp4" in media_types)
                            self.media_type_mov.set("mov" in media_types)
                            self.media_type_avi.set("avi" in media_types)
                            self.media_type_mkv.set("mkv" in media_types)
                            self.media_type_webm.set("webm" in media_types)
                            # Audio
                            self.media_type_mp3.set("mp3" in media_types)
                            self.media_type_wav.set("wav" in media_types)
                            self.media_type_m4a.set("m4a" in media_types)
                            self.media_type_flac.set("flac" in media_types)
                            self.media_type_aac.set("aac" in media_types)
                            self.media_type_wma.set("wma" in media_types)
                        elif line.startswith("BULK_TRANS_OUTPUT_FORMATS="):
                            output_formats = line.split("=")[1].split(",")
                            self.output_format_srt.set("srt" in output_formats)
                            self.output_format_txt.set("txt" in output_formats)
                            self.output_format_vtt.set("vtt" in output_formats)
                            self.output_format_json.set("json" in output_formats)
                        elif line.startswith("BULK_TRANS_RECURSIVE_SUBFOLDERS="):
                            self.recursive_subfolders.set(line.split("=")[1].lower() == "true")
            logger.info("Bulk Transcriber preferences loaded")
        except Exception as e:
            logger.warning(f"Could not load preferences: {str(e)}")
    
    def _save_preferences(self):
        """Save preferences to .env file"""
        try:
            env_path = Path(".env")
            
            # Build media types string
            media_types = []
            if self.media_type_mp4.get():
                media_types.append("mp4")
            if self.media_type_mov.get():
                media_types.append("mov")
            if self.media_type_avi.get():
                media_types.append("avi")
            if self.media_type_mkv.get():
                media_types.append("mkv")
            if self.media_type_webm.get():
                media_types.append("webm")
            if self.media_type_mp3.get():
                media_types.append("mp3")
            if self.media_type_wav.get():
                media_types.append("wav")
            if self.media_type_m4a.get():
                media_types.append("m4a")
            if self.media_type_flac.get():
                media_types.append("flac")
            if self.media_type_aac.get():
                media_types.append("aac")
            if self.media_type_wma.get():
                media_types.append("wma")
            
            media_types_str = ",".join(media_types) if media_types else "mp4"
            
            # Build output formats string
            output_formats = []
            if self.output_format_srt.get():
                output_formats.append("srt")
            if self.output_format_txt.get():
                output_formats.append("txt")
            if self.output_format_vtt.get():
                output_formats.append("vtt")
            if self.output_format_json.get():
                output_formats.append("json")
            
            output_formats_str = ",".join(output_formats) if output_formats else "srt"
            
            # Read existing .env
            env_content = {}
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("BULK_TRANS_"):
                            key_value = line.split("=", 1)
                            if len(key_value) == 2:
                                env_content[key_value[0]] = key_value[1]
            
            # Update with new preferences
            env_content["BULK_TRANS_MEDIA_TYPES"] = media_types_str
            env_content["BULK_TRANS_OUTPUT_FORMATS"] = output_formats_str
            env_content["BULK_TRANS_RECURSIVE_SUBFOLDERS"] = str(self.recursive_subfolders.get())
            
            # Write back
            with open(env_path, "w") as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            
            logger.info("Bulk Transcriber preferences saved")
        except Exception as e:
            logger.warning(f"Could not save preferences: {str(e)}")
