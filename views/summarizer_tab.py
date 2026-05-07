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

Version: 1.0
Created: 2026-05-06
"""

import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from typing import Optional, Dict, Any

from config import LLM_WEBHOOK_URL, LLM_MODEL
from utils.prompt_presets import PROMPT_PRESETS, PRESET_NAMES, DEFAULT_PROMPT_KEY
from utils.logger import logger
from views.base_tab import BaseTab


class SummarizerTab(BaseTab):
    """
    Unified summarizer tab that replaces file_tab.py and youtube_summarizer_tab.py.
    
    Handles both file and YouTube input modes and sends content directly to
    OpenAI-compatible LLM webhooks instead of using n8n workflows.
    """
    
    def __init__(self, parent):
        """
        Initialize Summarizer tab.
        
        Args:
            parent: Parent widget (ttk.Notebook)
        """
        # Initialize variables BEFORE calling super().__init__()
        # Input mode
        self.input_mode_var = tk.StringVar(value="file")  # "file" or "youtube"
        
        # File mode state
        self.file_path_var = tk.StringVar(value="No file selected")
        self.current_file_directory = None
        self.current_file_basename = None
        
        # YouTube mode state
        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value=".txt")
        
        # LLM settings
        self.webhook_var = tk.StringVar(value=LLM_WEBHOOK_URL or "http://localhost:1234")
        self.model_var = tk.StringVar(value=LLM_MODEL or "local-model")
        self.save_settings_var = tk.BooleanVar(value=False)
        
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
        
        logger.info("SummarizerTab initialized - unified file/YouTube summarization with LLM")
    
    def _setup_ui(self):
        """Setup the complete UI with all sections."""
        # Configure row weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)  # Content/response section expands
        
        # Setup sections in order
        self._setup_input_section()             # row=0
        self._setup_settings_section()          # row=1
        self._setup_file_info_section()         # row=2
        self._setup_content_response_section()  # row=3 (weight=1)
        self._setup_action_bar()                # row=4
        
        # Initialize mode visibility
        self._on_mode_changed()
        
        logger.debug("SummarizerTab UI setup complete")
    
    def _setup_input_section(self):
        """Setup input section with file/YouTube mode selection."""
        input_frame = ttk.LabelFrame(self, text="Input", padding="10")
        input_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Mode selection radio buttons
        mode_frame = ttk.Frame(input_frame)
        mode_frame.grid(row=0, column=0, sticky="w", pady=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="📄 File",
            value="file",
            variable=self.input_mode_var,
            command=self._on_mode_changed
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="🎬 YouTube URL",
            value="youtube",
            variable=self.input_mode_var,
            command=self._on_mode_changed
        ).pack(side=tk.LEFT, padx=5)
        
        # File mode frame
        self._file_frame = ttk.Frame(input_frame)
        file_row = 1
        
        ttk.Label(self._file_frame, text="File:").grid(row=file_row, column=0, sticky="w")
        ttk.Label(
            self._file_frame,
            textvariable=self.file_path_var,
            relief="sunken",
            anchor="w"
        ).grid(row=file_row, column=1, sticky="ew", padx=5)
        
        ttk.Button(
            self._file_frame,
            text="Browse…",
            command=self._browse_file
        ).grid(row=file_row, column=2, padx=5)
        
        self._file_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        # YouTube mode frame
        self._youtube_frame = ttk.Frame(input_frame)
        youtube_row = 1
        
        ttk.Label(self._youtube_frame, text="URL:").grid(row=youtube_row, column=0, sticky="w")
        self.url_entry = ttk.Entry(
            self._youtube_frame,
            textvariable=self.url_var
        )
        self.url_entry.grid(row=youtube_row, column=1, sticky="ew", padx=5)
        self.url_var.set("https://")
        
        youtube_row += 1
        ttk.Label(self._youtube_frame, text="Format:").grid(row=youtube_row, column=0, sticky="w")
        format_combo = ttk.Combobox(
            self._youtube_frame,
            textvariable=self.format_var,
            values=[".txt", ".srt", ".vtt", ".json"],
            state="readonly",
            width=8
        )
        format_combo.grid(row=youtube_row, column=1, sticky="w", padx=5)
        
        self._youtube_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        # Configure column weights
        input_frame.columnconfigure(1, weight=1)
    
    def _on_mode_changed(self):
        """Handle input mode changes (file ↔ YouTube)."""
        if self.input_mode_var.get() == "file":
            self._file_frame.grid()
            self._youtube_frame.grid_remove()
            self.file_info_frame.grid()
        else:
            self._youtube_frame.grid()
            self._file_frame.grid_remove()
            self.file_info_frame.grid_remove()
        
        logger.debug(f"Input mode changed to: {self.input_mode_var.get()}")
    
    def _setup_settings_section(self):
        """Setup LLM settings section."""
        settings_frame = ttk.LabelFrame(self, text="Summarizer Settings", padding="10")
        settings_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        
        settings_frame.columnconfigure(1, weight=1)
        
        # Webhook URL
        row = 0
        ttk.Label(settings_frame, text="Webhook URL:").grid(row=row, column=0, sticky="w")
        self.webhook_entry = ttk.Entry(
            settings_frame,
            textvariable=self.webhook_var
        )
        self.webhook_entry.grid(row=row, column=1, sticky="ew", padx=5)
        
        ttk.Checkbutton(
            settings_frame,
            text="Save to .env",
            variable=self.save_settings_var
        ).grid(row=row, column=2, sticky="w", padx=5)
        
        # Model name
        row += 1
        ttk.Label(settings_frame, text="Model:").grid(row=row, column=0, sticky="w")
        self.model_entry = ttk.Entry(
            settings_frame,
            textvariable=self.model_var
        )
        self.model_entry.grid(row=row, column=1, sticky="ew", padx=5)
        
        # Prompt preset
        row += 1
        ttk.Label(settings_frame, text="Prompt Preset:").grid(row=row, column=0, sticky="w")
        prompt_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.prompt_preset_var,
            values=PRESET_NAMES,
            state="readonly",
            width=30
        )
        prompt_combo.grid(row=row, column=1, sticky="w", padx=5)
        prompt_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)
        
        # Prompt text area
        row += 1
        self.prompt_text = scrolledtext.ScrolledText(
            settings_frame,
            height=4,
            wrap=tk.WORD,
            font=("Segoe UI", 9)
        )
        self.prompt_text.grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)
        
        # Insert default prompt
        self.prompt_text.insert("1.0", PROMPT_PRESETS[DEFAULT_PROMPT_KEY])
    
    def _on_preset_changed(self, event=None):
        """Handle prompt preset selection changes."""
        key = self.prompt_preset_var.get()
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", PROMPT_PRESETS.get(key, ""))
        logger.debug(f"Prompt preset changed to: {key}")
    
    def _setup_file_info_section(self):
        """Setup file information display section."""
        self.file_info_frame = ttk.LabelFrame(self, text="File Info", padding="10")
        self.file_info_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(self.file_info_frame)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        self.info_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            state="disabled",
            height=4,
            yscrollcommand=scrollbar.set
        )
        self.info_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.info_text.yview)
        
        # Initial content
        self.info_text.config(state="normal")
        self.info_text.insert("1.0", "No file selected")
        self.info_text.config(state="disabled")
    
    def _setup_content_response_section(self):
        """Setup content preview and response display sections."""
        content_frame = ttk.Frame(self)
        content_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure grid weights
        content_frame.rowconfigure(0, weight=1)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        
        # Content preview (left)
        content_preview_frame = ttk.LabelFrame(
            content_frame,
            text="Content Preview & Edit",
            padding="5"
        )
        content_preview_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=0)
        
        self.content_text = scrolledtext.ScrolledText(
            content_preview_frame,
            height=20,
            wrap=tk.WORD,
            font=("Courier", 10)
        )
        self.content_text.pack(fill="both", expand=True)
        
        # Response display (right)
        response_frame = ttk.LabelFrame(
            content_frame,
            text="Response",
            padding="5"
        )
        response_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=0)
        
        self.response_text = scrolledtext.ScrolledText(
            response_frame,
            height=20,
            wrap=tk.WORD,
            font=("Courier", 10),
            state="disabled"
        )
        self.response_text.pack(fill="both", expand=True)
        
        # Add context menu to response text
        self._register_context_menu(self.response_text, [
            {"label": "Copy All", "command": self._copy_all_response},
            {"label": "Clear", "command": self._clear_response}
        ])
        
        # Initial response content
        self.response_text.config(state="normal")
        self.response_text.insert("1.0", 
            "Select a file or enter a YouTube URL and click Summarize to get started…"
        )
        self.response_text.config(state="disabled")
    
    def _setup_action_bar(self):
        """Setup action bar with buttons and export controls."""
        action_frame = ttk.Frame(self)
        action_frame.grid(row=4, column=0, sticky="ew", padx=5, pady=5)
        
        # Summarize button
        self.send_btn = ttk.Button(
            action_frame,
            text="✨ Summarize",
            command=self._send_clicked
        )
        self.send_btn.grid(row=0, column=0, padx=5)
        
        # Export controls frame
        export_controls_frame = ttk.Frame(action_frame)
        export_controls_frame.grid(row=0, column=1, sticky="ew", padx=10)
        export_controls_frame.columnconfigure(0, weight=1)
        
        # Export preferences
        ttk.Checkbutton(
            export_controls_frame,
            text="Use original location",
            variable=self.use_original_location_var
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(
            export_controls_frame,
            text="Auto .txt",
            variable=self.auto_export_txt_var
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(
            export_controls_frame,
            text="Auto .docx",
            variable=self.auto_export_docx_var
        ).pack(side=tk.LEFT, padx=5)
        
        # Export buttons
        ttk.Label(export_controls_frame, text="Export:").pack(side=tk.LEFT, padx=5)
        
        self.export_txt_btn = ttk.Button(
            export_controls_frame,
            text="📄 .txt",
            command=self._export_txt_clicked,
            state="disabled"
        )
        self.export_txt_btn.pack(side=tk.LEFT, padx=2)
        
        self.export_docx_btn = ttk.Button(
            export_controls_frame,
            text="📝 .docx",
            command=self._export_docx_clicked,
            state="disabled"
        )
        self.export_docx_btn.pack(side=tk.LEFT, padx=2)
        
        self.copy_btn = ttk.Button(
            export_controls_frame,
            text="📋 Copy",
            command=self._copy_clicked,
            state="disabled"
        )
        self.copy_btn.pack(side=tk.LEFT, padx=2)
        
        # Clear button
        self.clear_btn = ttk.Button(
            action_frame,
            text="Clear All",
            command=self._clear_clicked
        )
        self.clear_btn.grid(row=0, column=2, padx=5)
        
        # Progress bar (created but not visible initially)
        self.progress = ttk.Progressbar(
            action_frame,
            mode="indeterminate"
        )
    
    # Context menu helpers
    def _copy_all_response(self):
        """Copy all response text to clipboard."""
        content = self.response_text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.update()
            self.set_status(f"Copied {len(content)} characters to clipboard")
    
    def _clear_response(self):
        """Clear response text."""
        self.response_text.config(state="normal")
        self.response_text.delete("1.0", tk.END)
        self.response_text.insert("1.0", "Response cleared")
        self.response_text.config(state="disabled")
        self.set_status("Response cleared")
    
    # Button handlers
    def _browse_file(self):
        """Browse for file."""
        filetypes = [
            ("Text Files", ".txt"),
            ("Subtitle Files", ".srt .vtt"),
            ("JSON Files", ".json"),
            ("Word Documents", ".docx"),
            ("All Files", ".*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Select file to summarize",
            filetypes=filetypes
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
    
    # Getters
    def get_input_mode(self) -> str:
        """Get current input mode."""
        return self.input_mode_var.get()
    
    def get_file_path(self) -> Optional[str]:
        """Get selected file path."""
        path = self.file_path_var.get()
        return path if path and path != "No file selected" else None
    
    def get_youtube_url(self) -> str:
        """Get YouTube URL."""
        return self.url_var.get().strip()
    
    def get_transcription_format(self) -> str:
        """Get transcription format."""
        return self.format_var.get()
    
    def get_webhook_url(self) -> str:
        """Get webhook URL."""
        return self.webhook_var.get().strip()
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_var.get().strip()
    
    def get_save_settings(self) -> bool:
        """Get save settings preference."""
        return self.save_settings_var.get()
    
    def get_prompt(self) -> str:
        """Get current prompt text."""
        return self.prompt_text.get("1.0", tk.END).strip()
    
    def get_content(self) -> str:
        """Get content text (satisfies BaseTab abstract method)."""
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
            "original_basename": self.current_file_basename
        }
    
    # Setters
    def set_file_path(self, path: Optional[str]):
        """Set file path and store directory/basename."""
        if path:
            self.file_path_var.set(path)
            self.current_file_directory = os.path.dirname(path)
            self.current_file_basename = os.path.basename(path)
        else:
            self.file_path_var.set("No file selected")
            self.current_file_directory = None
            self.current_file_basename = None
    
    def set_content(self, text: str):
        """Set content text."""
        self.content_text.config(state="normal")
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", text)
        self.content_text.config(state="normal")
    
    def set_file_info(self, info: Optional[dict]):
        """Set file information display."""
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", tk.END)
        
        if info:
            lines = [
                f"Name: {info.get('name', 'Unknown')}",
                f"Size: {info.get('size_kb', 0):.2f} KB",
                f"Lines: {info.get('lines', 0)}",
                f"Type: {info.get('type', 'Unknown')}"
            ]
            self.info_text.insert("1.0", "\n".join(lines))
        else:
            self.info_text.insert("1.0", "No file selected")
        
        self.info_text.config(state="disabled")
    
    def set_status(self, msg: str):
        """Set status message (override BaseTab default)."""
        logger.info(f"SummarizerTab: {msg}")
        # Note: This tab doesn't have a status bar, so just log
        # The controller can handle status display in main window
    
    def display_response(self, text: str):
        """Display response text."""
        self.response_text.config(state="normal")
        self.response_text.delete("1.0", tk.END)
        self.response_text.insert("1.0", text)
        self.response_text.config(state="disabled")
    
    def show_loading(self, show: bool):
        """Show or hide loading indicator."""
        if show:
            self.progress.grid(row=5, column=0, sticky="ew", pady=5)
            self.send_btn.config(state="disabled")
            self.progress.start()
        else:
            self.progress.grid_remove()
            self.send_btn.config(state="normal")
            self.progress.stop()
    
    def set_export_buttons_enabled(self, enabled: bool):
        """Enable or disable export buttons."""
        state = "normal" if enabled else "disabled"
        self.export_txt_btn.config(state=state)
        self.export_docx_btn.config(state=state)
        self.copy_btn.config(state=state)
    
    # BaseTab abstract method implementations
    def clear_all(self):
        """Reset all UI elements to initial state."""
        # Reset input mode and file state
        self.input_mode_var.set("file")
        self.file_path_var.set("No file selected")
        self.current_file_directory = None
        self.current_file_basename = None
        
        # Reset YouTube state
        self.url_var.set("https://")
        
        # Clear content areas
        self.content_text.delete("1.0", tk.END)
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", "No file selected")
        self.info_text.config(state="disabled")
        
        # Reset response
        self.response_text.config(state="normal")
        self.response_text.delete("1.0", tk.END)
        self.response_text.insert("1.0", 
            "Select a file or enter a YouTube URL and click Summarize to get started…")
        self.response_text.config(state="disabled")
        
        # Reset export buttons
        self.set_export_buttons_enabled(False)
        
        # Restore frame visibility for current mode
        self._on_mode_changed()
        
        self.set_status("Cleared all")