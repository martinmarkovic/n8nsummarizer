"""
YouTube Summarizer Tab v3.0 - YouTube transcription + n8n summarization

Responsibilities:
    - Accept YouTube URL input
    - Select transcription format
    - Display transcription status
    - Display summarized content
    - Export summary (txt, srt)
    - Copy to clipboard
    - Show loading states

Events (callbacks set by controller):
    - on_transcribe_clicked: User clicked Transcribe button
    - on_export_txt_clicked: User clicked Export .txt
    - on_export_srt_clicked: User clicked Export .srt
    - on_copy_clipboard_clicked: User clicked Copy to Clipboard

Version: 3.0
Created: 2025-12-07
"""
import tkinter as tk
from tkinter import ttk, messagebox
from views.base_tab import BaseTab


class YouTubeSummarizerTab(BaseTab):
    """
    Tab for transcribing YouTube videos and summarizing via n8n.
    
    Features:
    - YouTube URL input with validation
    - Transcription format selection
    - Transcript + summarization processing
    - Summary display
    - Three export options (.txt, .srt, clipboard)
    - Real-time status updates
    - Loading indicators
    """
    
    def __init__(self, notebook):
        """
        Initialize YouTube Summarizer tab.
        
        Args:
            notebook: Parent ttk.Notebook widget
        """
        super().__init__(notebook)
        
        # Callbacks (set by controller)
        self.on_transcribe_clicked = None
        self.on_export_txt_clicked = None
        self.on_export_srt_clicked = None
        self.on_copy_clipboard_clicked = None
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """
        Setup the tab UI with input and output sections.
        """
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Input section
        self._setup_input_section(main_frame)
        
        # Output section
        self._setup_output_section(main_frame)
    
    def _setup_input_section(self, parent):
        """
        Setup input section (URL + format selection + transcribe button).
        """
        input_frame = ttk.LabelFrame(parent, text="YouTube URL", padding="10")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        # YouTube URL label and entry
        ttk.Label(input_frame, text="URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(input_frame, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.url_entry.insert(0, "https://")
        
        # Format selection
        ttk.Label(input_frame, text="Format:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.format_var = tk.StringVar(value=".txt")
        format_combo = ttk.Combobox(
            input_frame,
            textvariable=self.format_var,
            values=[".txt", ".srt", ".vtt", ".json"],
            state="readonly",
            width=10
        )
        format_combo.grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        
        # Transcribe button
        self.transcribe_btn = ttk.Button(
            input_frame,
            text="🎬 Transcribe",
            command=self._on_transcribe_btn_clicked
        )
        self.transcribe_btn.grid(row=0, column=4, sticky=tk.W)
        
        # Status label
        self.input_status_var = tk.StringVar(value="Ready")
        self.input_status_label = ttk.Label(
            input_frame,
            textvariable=self.input_status_var,
            foreground="green",
            font=("Segoe UI", 9)
        )
        self.input_status_label.grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=(5, 0))
    
    def _setup_output_section(self, parent):
        """
        Setup output section (summary display + export buttons).
        """
        output_frame = ttk.LabelFrame(parent, text="Summary", padding="10")
        output_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        # Summary text display
        text_frame = ttk.Frame(output_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        self.summary_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            height=15,
            font=("Segoe UI", 10)
        )
        self.summary_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.config(command=self.summary_text.yview)
        
        # Display placeholder
        self.summary_text.insert(tk.END, "Enter a YouTube URL and click Transcribe to get started...")
        self.summary_text.config(state=tk.DISABLED)
        
        # Button frame
        button_frame = ttk.Frame(output_frame)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)
        
        # Export buttons
        self.export_txt_btn = ttk.Button(
            button_frame,
            text="💾 Export .txt",
            command=self._on_export_txt_clicked,
            state=tk.DISABLED
        )
        self.export_txt_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.export_srt_btn = ttk.Button(
            button_frame,
            text="📝 Export .srt",
            command=self._on_export_srt_clicked,
            state=tk.DISABLED
        )
        self.export_srt_btn.grid(row=0, column=1, sticky=tk.W, padx=(0, 5))
        
        self.copy_btn = ttk.Button(
            button_frame,
            text="📋 Copy to Clipboard",
            command=self._on_copy_clicked,
            state=tk.DISABLED
        )
        self.copy_btn.grid(row=0, column=2, sticky=tk.W)
        
        # Output status label
        self.output_status_var = tk.StringVar(value="")
        self.output_status_label = ttk.Label(
            output_frame,
            textvariable=self.output_status_var,
            foreground="blue",
            font=("Segoe UI", 9)
        )
        self.output_status_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
    
    # User event callbacks
    
    def _on_transcribe_btn_clicked(self):
        """Handle transcribe button click."""
        if self.on_transcribe_clicked:
            self.on_transcribe_clicked()
    
    def _on_export_txt_clicked(self):
        """Handle export .txt button click."""
        if self.on_export_txt_clicked:
            self.on_export_txt_clicked()
    
    def _on_export_srt_clicked(self):
        """Handle export .srt button click."""
        if self.on_export_srt_clicked:
            self.on_export_srt_clicked()
    
    def _on_copy_clicked(self):
        """Handle copy to clipboard button click."""
        if self.on_copy_clipboard_clicked:
            self.on_copy_clipboard_clicked()
    
    # Getters
    
    def get_youtube_url(self) -> str:
        """
        Get YouTube URL from input field.
        
        Returns:
            URL string
        """
        return self.url_var.get().strip()
    
    def get_transcription_format(self) -> str:
        """
        Get selected transcription format.
        
        Returns:
            Format string (e.g., '.txt', '.srt')
        """
        return self.format_var.get()
    
    def get_summary_content(self) -> str:
        """
        Get summary text content.
        
        Returns:
            Summary text
        """
        return self.summary_text.get("1.0", tk.END).strip()
    
    # Setters and state management
    
    def set_summary_content(self, content: str):
        """
        Set summary text content.
        
        Args:
            content: Summary text to display
        """
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, content)
        self.summary_text.config(state=tk.DISABLED)
    
    def set_input_status(self, message: str, color: str = "blue"):
        """
        Set input section status message.
        
        Args:
            message: Status message
            color: Text color (blue=info, green=success, red=error)
        """
        self.input_status_var.set(message)
        self.input_status_label.config(foreground=color)
    
    def set_output_status(self, message: str, color: str = "blue"):
        """
        Set output section status message.
        
        Args:
            message: Status message
            color: Text color (blue=info, green=success, red=error)
        """
        self.output_status_var.set(message)
        self.output_status_label.config(foreground=color)
    
    def set_transcribe_button_enabled(self, enabled: bool):
        """
        Enable/disable transcribe button.
        
        Args:
            enabled: True to enable, False to disable
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        self.transcribe_btn.config(state=state)
    
    def set_export_buttons_enabled(self, enabled: bool):
        """
        Enable/disable all export buttons.
        
        Args:
            enabled: True to enable, False to disable
        """
        state = tk.NORMAL if enabled else tk.DISABLED
        self.export_txt_btn.config(state=state)
        self.export_srt_btn.config(state=state)
        self.copy_btn.config(state=state)
    
    def set_format_enabled(self, enabled: bool):
        """
        Enable/disable format selection during processing.
        
        Args:
            enabled: True to enable, False to disable
        """
        # Note: Combobox state management happens via widget reference
        pass
    
    def show_error(self, message: str):
        """
        Show error message to user.
        
        Args:
            message: Error message
        """
        messagebox.showerror("Error", message)
        self.set_input_status("Error", "red")
    
    def show_success(self, message: str):
        """
        Show success message to user.
        
        Args:
            message: Success message
        """
        messagebox.showinfo("Success", message)
    
    def clear_all(self):
        """
        Clear all fields and reset to initial state.
        """
        self.url_var.set("https://")
        self.format_var.set(".txt")
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "Enter a YouTube URL and click Transcribe to get started...")
        self.summary_text.config(state=tk.DISABLED)
        self.set_input_status("Ready", "green")
        self.set_output_status("", "blue")
        self.set_export_buttons_enabled(False)
        self.set_transcribe_button_enabled(True)
