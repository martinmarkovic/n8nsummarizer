"""
Video Subtitler Tab - Phase 1: Download video + transcribe to SRT

Follows the same pattern as DownloaderTab with BaseTab subclass.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from pathlib import Path

from views.base_tab import BaseTab

class VideoSubtitlerTab(BaseTab):
    """Video Subtitler tab with download + transcription UI."""

    def __init__(self, notebook):
        self.notebook = notebook
        
        # State variables
        self.url_var = tk.StringVar()
        self.input_mode = tk.StringVar(value="url")  # "url" or "local"
        self.local_file_path = tk.StringVar()
        self.model_var = tk.StringVar(value="base")
        self.language_var = tk.StringVar(value="auto")
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_pct_var = tk.StringVar(value="0%")
        
        # Controller will be initialized after UI setup
        self.controller = None
        
        super().__init__(notebook, "🎞 Video Subtitler")
        
    def _setup_ui(self):
        """Build Video Subtitler UI with input controls and progress display."""
        # Configure grid - make all content scrollable
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)  # Main area expands
        
        # Create a canvas with scrollbar for the entire tab
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Add mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure scrollable frame grid
        scrollable_frame.columnconfigure(0, weight=1)
        
        # === Row 0: Download & Transcribe Settings ===
        settings_frame = ttk.LabelFrame(scrollable_frame, text="Video Source Settings", padding=15)
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        settings_frame.columnconfigure(1, weight=1)
        
        # Mode selection (URL vs Local File)
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        ttk.Radiobutton(mode_frame, text="URL", variable=self.input_mode, value="url").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(mode_frame, text="Local File", variable=self.input_mode, value="local").pack(side=tk.LEFT)
        
        # URL Input Frame
        self.url_frame = ttk.Frame(settings_frame)
        self.url_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(self.url_frame, text="Video URL:").pack(side=tk.LEFT, padx=(0, 5))
        
        url_entry = ttk.Entry(self.url_frame, textvariable=self.url_var)
        url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        # Local File Input Frame (initially hidden)
        self.local_frame = ttk.Frame(settings_frame)
        self.local_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.local_frame.grid_remove()  # Hidden by default
        
        ttk.Label(self.local_frame, text="Local File:").pack(side=tk.LEFT, padx=(0, 5))
        
        local_file_entry = ttk.Entry(self.local_frame, textvariable=self.local_file_path, state="readonly")
        local_file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(self.local_frame, text="Browse", command=self._browse_local_file, width=8).pack(side=tk.LEFT)
        
        # Start button
        self.start_btn = ttk.Button(
            settings_frame,
            text="▶ Start",
            command=self._on_start,
            width=8
        )
        self.start_btn.grid(row=2, column=2, sticky=tk.E, padx=(5, 0), pady=5)
        
        # Mode change handler
        self.input_mode.trace("w", self._on_mode_change)
        
        # Whisper Model
        ttk.Label(settings_frame, text="Whisper Model:").grid(
            row=3, column=0, sticky=tk.W, padx=(0, 10), pady=5
        )
        
        model_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.model_var,
            values=["tiny", "base", "small", "medium", "large"],
            state="readonly",
            width=10
        )
        model_combo.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Language
        ttk.Label(settings_frame, text="Language:").grid(
            row=3, column=2, sticky=tk.W, padx=(10, 10), pady=5
        )
        
        language_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.language_var,
            values=["auto", "en", "hr", "de", "fr", "es", "it", "pt", "极ru", "ja", "zh"],
            state="readonly",
            width=8
        )
        language_combo.grid(row=3, column=3, sticky=tk.W, padx=(0, 10), pady=5)
        
        # === Row 1: Progress ===
        progress_frame = ttk.LabelFrame(scrollable_frame, text="Progress", padding=10)
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            length=400
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10), pady=5)
        
        # Progress percentage
        ttk.Label(progress_frame, textvariable=self.progress_pct_var).grid(
            row=0, column=1, sticky=tk.W, pady=5
        )
        
        # Status label
        status_label = ttk.Label(
            progress_frame,
            textvariable=self.progress_var,
            foreground="blue"
        )
        status_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # === Row 2: Transcription (SRT) ===
        srt_frame = ttk.LabelFrame(scrollable_frame, text="Transcription (SRT)", padding=10)
        srt_frame.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(0, 10))
        srt_frame.rowconfigure(0, weight=1)
        srt_frame.columnconfigure(0, weight=1)
        
        # SRT text widget
        self.srt_text = tk.Text(srt_frame, wrap=tk.WORD, height=15)
        self.srt_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        srt_scroll = ttk.Scrollbar(srt_frame, command=self.srt_text.yview)
        srt_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.srt_text.configure(yscrollcommand=srt_scroll.set)
        
        # Button frame
        button_frame = ttk.Frame(srt_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Open temp folder button
        open_btn = ttk.Button(
            button_frame,
            text="📂 Open Temp Folder",
            command=self._open_temp_folder,
            width=15
        )
        open_btn.grid(row=0, column=0, padx=(0, 5))
        
        # Copy SRT path button
        copy_btn = ttk.Button(
            button_frame,
            text="📋 Copy SRT Path",
            command=self._copy_srt_path,
            width=15
        )
        copy_btn.grid(row=0, column=1)
        
        # === Row 3: Translation ===
        translation_frame = ttk.LabelFrame(scrollable_frame, text="Translation", padding=10)
        translation_frame.grid(row=3, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(0, 10))
        translation_frame.columnconfigure(1, weight=1)
        
        # Target language selection
        ttk.Label(translation_frame, text="Translate to:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5), pady=5
        )
        
        self.translate_lang_var = tk.StringVar(value="English")
        lang_combo = ttk.Combobox(
            translation_frame,
            textvariable=self.translate_lang_var,
            values=["English", "Croatian", "German", "French", "Spanish", "Italian", "Portuguese", "Russian", "Japanese", "Chinese"],
            state="readonly",
            width=12
        )
        lang_combo.grid(row=0, column=1, sticky=tk.W, padx=(0, 10), pady=5)
        
        # Translate button
        self.translate_btn = ttk.Button(
            translation_frame,
            text="🌐 Translate SRT",
            command=self._on_translate_clicked,
            state=tk.DISABLED,
            width=15
        )
        self.translate_btn.grid(row=0, column=2, padx=(5, 0), pady=5)
        
        # Translated SRT text widget
        self.translated_srt_text = tk.Text(translation_frame, wrap=tk.WORD, height=12)
        self.translated_srt_text.grid(row=1, column=0, columnspan=3, sticky=(tk.N, tk.S, tk.E, tk.W), pady=(5, 5))
        
        translated_scroll = ttk.Scrollbar(translation_frame, command=self.translated_srt_text.yview)
        translated_scroll.grid(row=1, column=3, sticky=(tk.N, tk.S))
        self.translated_srt_text.configure(yscrollcommand=translated_scroll.set)
        
        # Save translated SRT button
        ttk.Button(
            translation_frame,
            text="💾 Save Translated SRT",
            command=self._on_save_translated,
            width=15
        ).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        
        # Configure row weights for expansion
        translation_frame.rowconfigure(1, weight=1)
        
        # === Row 4: Burn Subtitles (FFmpeg) ===
        burn_frame = ttk.LabelFrame(scrollable_frame, text="Burn Subtitles (FFmpeg)", padding=10)
        burn_frame.grid(row=4, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(0, 10))
        burn_frame.columnconfigure(1, weight=1)
        
        # Subtitle source selection
        ttk.Label(burn_frame, text="Subtitle source:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5), pady=5
        )
        
        self.subtitle_source_var = tk.StringVar(value="translated")
        source_frame = ttk.Frame(burn_frame)
        source_frame.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(source_frame, text="Translated SRT", variable=self.subtitle_source_var, value="translated").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(source_frame, text="Original SRT", variable=self.subtitle_source_var, value="original").pack(side=tk.LEFT)
        
        # Burn button
        self.burn_btn = ttk.Button(
            burn_frame,
            text="🔥 Burn Subtitles into Video",
            command=self._on_burn_clicked,
            state=tk.DISABLED,
            width=20
        )
        self.burn_btn.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(5, 5))
        
        # FFmpeg status
        self.ffmpeg_status_var = tk.StringVar(value="")
        status_label = ttk.Label(
            burn_frame,
            textvariable=self.ffmpeg_status_var,
            foreground="blue"
        )
        status_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # Open output file button
        self.open_output_btn = ttk.Button(
            burn_frame,
            text="📂 Open Output File",
            command=self._open_output_file,
            state=tk.DISABLED,
            width=20
        )
        self.open_output_btn.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
    def set_controller(self, controller):
        """Set the controller for this view."""
        self.controller = controller
    
    # === UI Event Handlers ===
    def _on_start(self):
        """Handle start button click."""
        if self.controller:
            self.controller.on_start()
    
    def _on_mode_change(self, *args):
        """Handle input mode change (URL vs Local File)."""
        if self.input_mode.get() == "url":
            self.url_frame.grid()
            self.local_frame.grid_remove()
        else:
            self.url_frame.grid_remove()
            self.local_frame.grid()
    
    def _browse_local_file(self):
        """Browse for local video file."""
        supported_formats = [
            ("Video Files", "*.mp4 *.avi *.mov *.mkv *.webm"),
            ("Audio Files", "*.mp3 *.wav *.flac *.m4a"),
            ("All Files", "*.*")
        ]
        file_path = filedialog.askopenfilename(
            title="Select video/audio file",
            filetypes=supported_formats
        )
        if file_path:
            self.local_file_path.set(file_path)
    
    def _open_temp_folder(self):
        """Open temp_subtitler folder."""
        try:
            temp_dir = Path("temp_subtitler")
            if temp_dir.exists():
                os.startfile(str(temp_dir))
            else:
                messagebox.showinfo("Info", "Temp folder does not exist yet.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open folder: {e}")
    
    def _copy_srt_path(self):
        """Copy SRT path to clipboard."""
        srt_path = "temp_subtitler/video.srt"
        self.clipboard_clear()
        self.clipboard_append(srt_path)
        self.log_message(f"Copied to clipboard: {srt_path}")
    
    # === View Helper Methods (called by controller) ===
    def get_url(self) -> str:
        """Get current URL from input field."""
        return self.url_var.get().strip()
    
    def get_local_file_path(self) -> str:
        """Get selected local file path."""
        return self.local_file_path.get().strip()
    
    def get_input_mode(self) -> str:
        """Get current input mode."""
        return self.input_mode.get()
    
    def get_whisper_model(self) -> str:
        """Get selected Whisper model."""
        return self.model_var.get()
    
    def get_language(self) -> str:
        """Get selected language."""
        return self.language_var.get()
    
    def update_progress(self, pct: float, message: str):
        """Update progress bar and status."""
        self.progress_bar["value"] = pct
        self.progress_pct_var.set(f"{pct:.1f}%")
        self.progress_var.set(message)
    
    def update_status(self, message: str):
        """Update status message."""
        self.progress_var.set(message)
    
    def display_srt(self, text: str):
        """Display SRT text in the text widget."""
        self.srt_text.delete("1.0", tk.END)
        self.srt_text.insert(tk.END, text)
    
    def set_busy(self, is_busy: bool):
        """Enable or disable start button."""
        self.start_btn.config(state=tk.DISABLED if is_busy else tk.NORMAL)
    
    def show_error(self, message: str):
        """Show error dialog."""
        messagebox.showerror("Error", message)
    
    def log_message(self, message: str):
        """Add message to status (for simple logging)."""
        current = self.progress_var.get()
        if current != "Ready":
            self.progress_var.set(f"{current} | {message}")
        else:
            self.progress_var.set(message)
    
    # === BaseTab Abstract Method Implementations ===
    def get_content(self) -> str:
        """Return current SRT content."""
        return self.srt_text.get("1.0", tk.END)
    
    def clear_all(self):
        """Clear all input fields and SRT text."""
        self.url_var.set("")
        self.model_var.set("base")
        self.language_var.set("auto")
        self.progress_bar["value"] = 0
        self.progress_pct_var.set("0%")
        self.progress_var.set("Ready")
        self.srt_text.delete("1.0", tk.END)
        
        # Clear translation section
        if hasattr(self, "translated_srt_text"):
            self.translated_srt_text.delete("1.0", tk.END)
        if hasattr(self, "translate_btn"):
            self.translate_btn.config(state=tk.DISABLED)
        
        # Clear FFmpeg section
        if hasattr(self, "burn_btn"):
            self.burn_btn.config(state=tk.DISABLED)
        if hasattr(self, "open_output_btn"):
            self.open_output_btn.config(state=tk.DISABLED)
        if hasattr(self, "ffmpeg_status_var"):
            self.ffmpeg_status_var.set("")
    
    # === Translation Methods ===
    def get_target_language(self) -> str:
        """Get target language for translation."""
        return self.translate_lang_var.get()
    
    def display_translated_srt(self, text: str):
        """Display translated SRT text."""
        self.translated_srt_text.delete("1.0", tk.END)
        self.translated_srt_text.insert(tk.END, text)
    
    def enable_translate_btn(self):
        """Enable translate button."""
        self.translate_btn.config(state=tk.NORMAL)
    
    def get_translated_srt(self) -> str:
        """Get translated SRT content."""
        return self.translated_srt_text.get("1.0", tk.END).strip()
    
    def _on_translate_clicked(self):
        """Handle translate button click."""
        if self.controller and hasattr(self.controller, 'on_translate'):
            self.controller.on_translate()
    
    def _on_save_translated(self):
        """Save translated SRT to file."""
        translated_srt = self.get_translated_srt()
        if not translated_srt:
            messagebox.showinfo("Info", "No translated SRT content to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Translated SRT",
            defaultextension=".srt",
            filetypes=[("SRT Files", "*.srt"), ("All Files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(translated_srt)
                messagebox.showinfo("Success", f"Translated SRT saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")
    
    # === FFmpeg Methods ===
    def get_subtitle_source(self) -> str:
        """Get subtitle source selection."""
        return self.subtitle_source_var.get()
    
    def enable_burn_btn(self):
        """Enable burn button."""
        self.burn_btn.config(state=tk.NORMAL)
    
    def enable_open_btn(self):
        """Enable open output file button."""
        self.open_output_btn.config(state=tk.NORMAL)
    
    def update_ffmpeg_status(self, msg: str):
        """Update FFmpeg status message."""
        self.ffmpeg_status_var.set(msg)
    
    def _on_burn_clicked(self):
        """Handle burn button click."""
        if self.controller and hasattr(self.controller, 'on_burn'):
            self.controller.on_burn()
    
    def _open_output_file(self):
        """Open output video file."""
        if self.controller and hasattr(self.controller, 'output_video_path'):
            try:
                os.startfile(str(self.controller.output_video_path))
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {e}")
        else:
            messagebox.showinfo("Info", "No output file available yet.")
