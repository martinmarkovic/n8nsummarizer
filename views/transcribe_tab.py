"""
Transcribe Tab - YouTube Transcriber tab UI

Responsibilities:
    - Display YouTube URL input
    - Fetch and display transcripts
    - Show response from n8n
    - Provide webhook override settings
    - Provide export functionality
    - Provide standard methods for controller

Use:
    >>> tab = TranscribeTab(notebook)
    >>> controller = TranscribeController(tab)
"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from config import N8N_WEBHOOK_URL
from utils.logger import logger
from views.base_tab import BaseTab


class TranscribeTab(BaseTab):
    """YouTube Transcriber tab - fetch transcript and send to n8n for summarization"""
    
    def __init__(self, parent):
        """
        Initialize Transcribe tab.
        
        Args:
            parent: Parent widget (ttk.Notebook or similar)
        """
        # Webhook override state
        self.webhook_override_var = tk.BooleanVar(value=False)
        self.custom_webhook_var = tk.StringVar(value=N8N_WEBHOOK_URL or '')
        
        # Transcript metadata
        self.current_video_id = None
        self.current_video_title = None
        
        # UI state for loading indicator
        self._loading = False
        
        super().__init__(parent, "YouTube Transcriber")
        
        # Tab-specific callbacks
        self.on_fetch_clicked = None
        self.on_send_clicked = None
        self.on_export_txt = None
        self.on_export_docx = None
        
        logger.info("TranscribeTab initialized")
    
    def _setup_ui(self):
        """Setup Transcribe tab UI"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)  # Content area expands
        
        # YouTube URL Input Section
        self._setup_youtube_input_section()
        
        # Webhook Override Section
        self._setup_webhook_section()
        
        # Transcript Info Section
        self._setup_transcript_info_section()
        
        # Transcript and Response Section (expandable)
        self._setup_transcript_response_section()
        
        # Bottom Action Bar
        self._setup_action_bar()
    
    def _setup_youtube_input_section(self):
        """Setup YouTube URL input UI"""
        youtube_frame = ttk.LabelFrame(self, text="YouTube Video", padding="10")
        youtube_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        youtube_frame.columnconfigure(1, weight=1)
        
        ttk.Label(youtube_frame, text="Video URL:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.url_entry = ttk.Entry(youtube_frame)
        self.url_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(
            youtube_frame,
            text="Supports: youtube.com, youtu.be, or video ID",
            font=("Segoe UI", 9, "italic")
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W)
    
    def _setup_webhook_section(self):
        """Setup webhook override UI"""
        webhook_frame = ttk.LabelFrame(self, text="n8n Webhook Override", padding="10")
        webhook_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        webhook_frame.columnconfigure(1, weight=1)
        
        override_check = ttk.Checkbutton(
            webhook_frame,
            text="Save to .env when sending",
            variable=self.webhook_override_var
        )
        override_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(webhook_frame, text="Webhook URL:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        self.webhook_entry = ttk.Entry(webhook_frame, textvariable=self.custom_webhook_var)
        self.webhook_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
    
    def _setup_transcript_info_section(self):
        """Setup transcript info display UI"""
        info_frame = ttk.LabelFrame(self, text="Transcript Info", padding="10")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(0, weight=1)
        
        self.info_text = tk.Text(info_frame, height=3, state=tk.DISABLED, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.config(yscrollcommand=info_scrollbar.set)
    
    def _setup_transcript_response_section(self):
        """Setup transcript and response display"""
        content_response_frame = ttk.Frame(self)
        content_response_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        content_response_frame.columnconfigure(0, weight=1)
        content_response_frame.columnconfigure(1, weight=1)
        content_response_frame.rowconfigure(0, weight=1)
        
        # Transcript Preview (Left)
        transcript_frame = ttk.LabelFrame(content_response_frame, text="Transcript", padding="10")
        transcript_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)
        
        self.transcript_text = scrolledtext.ScrolledText(
            transcript_frame, height=20, width=65, wrap=tk.WORD, font=("Courier", 10), state=tk.DISABLED
        )
        self.transcript_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Response Section (Right)
        response_frame = ttk.LabelFrame(content_response_frame, text="n8n Response", padding="10")
        response_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        response_frame.columnconfigure(0, weight=1)
        response_frame.rowconfigure(0, weight=1)
        
        self.response_text = scrolledtext.ScrolledText(
            response_frame, height=20, width=65, wrap=tk.WORD, font=("Courier", 10), state=tk.DISABLED
        )
        self.response_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def _setup_action_bar(self):
        """Setup bottom action bar with buttons and controls"""
        bottom_frame = ttk.Frame(self)
        bottom_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        bottom_frame.columnconfigure(1, weight=1)
        
        # Fetch and Send buttons
        button_frame = ttk.Frame(bottom_frame)
        button_frame.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        self.fetch_btn = ttk.Button(button_frame, text="Fetch Transcript", command=self._fetch_clicked)
        self.fetch_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.send_btn = ttk.Button(button_frame, text="Send to n8n", command=self._send_clicked)
        self.send_btn.grid(row=0, column=1, sticky=tk.W)
        
        # Export controls (middle section)
        export_frame = ttk.Frame(bottom_frame)
        export_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Label(export_frame, text="Export:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.export_txt_btn = ttk.Button(export_frame, text="📄 .txt", command=self._export_txt_clicked)
        self.export_txt_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.export_docx_btn = ttk.Button(export_frame, text="📝 .docx", command=self._export_docx_clicked)
        self.export_docx_btn.grid(row=0, column=2)
        
        # Clear button (right)
        self.clear_btn = ttk.Button(bottom_frame, text="Clear All", command=self._clear_clicked)
        self.clear_btn.grid(row=0, column=2, sticky=tk.E, padx=(20, 0))
        
        # Loading indicator
        self.progress = ttk.Progressbar(bottom_frame, mode='indeterminate')
    
    # Button callbacks
    
    def _fetch_clicked(self):
        """Handle fetch transcript button"""
        if self.on_fetch_clicked:
            self.on_fetch_clicked()
    
    def _send_clicked(self):
        """Handle send button"""
        if self.on_send_clicked:
            self.on_send_clicked()
    
    def _export_txt_clicked(self):
        """Handle export .txt button"""
        if self.on_export_txt:
            self.on_export_txt()
    
    def _export_docx_clicked(self):
        """Handle export .docx button"""
        if self.on_export_docx:
            self.on_export_docx()
    
    # Standard tab methods
    
    def get_content(self) -> str:
        """Get current content (transcript or response)"""
        # Return transcript if available, otherwise response
        transcript = self.get_transcript()
        if transcript and transcript.strip():
            return transcript
        return self.get_response_content()
    
    def get_transcript(self) -> str:
        """Get transcript content"""
        return self.transcript_text.get('1.0', tk.END).rstrip()
    
    def get_response_content(self) -> str:
        """Get response content"""
        return self.response_text.get('1.0', tk.END).rstrip()
    
    def get_youtube_url(self) -> str:
        """Get YouTube URL from input"""
        return self.url_entry.get().strip()
    
    def get_video_title(self) -> str:
        """Get video title/ID"""
        return self.current_video_title
    
    def set_transcript(self, content: str, video_id: str = None, video_title: str = None):
        """Set transcript content"""
        self.transcript_text.config(state=tk.NORMAL)
        self.transcript_text.delete('1.0', tk.END)
        if content:
            self.transcript_text.insert('1.0', content)
        self.transcript_text.config(state=tk.DISABLED)
        
        # Store video metadata
        if video_id:
            self.current_video_id = video_id
        if video_title:
            self.current_video_title = video_title
    
    def set_response(self, response: str):
        """Set response content"""
        self.response_text.config(state=tk.NORMAL)
        self.response_text.delete('1.0', tk.END)
        if response:
            self.response_text.insert('1.0', response)
        self.response_text.config(state=tk.DISABLED)
    
    def display_response(self, response: str):
        """Display response"""
        self.set_response(response)
    
    def set_transcript_info(self, info_dict: dict):
        """Set transcript info display"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete('1.0', tk.END)
        if info_dict:
            info_text = f"Video ID: {info_dict.get('video_id', 'N/A')} | "
            info_text += f"Characters: {info_dict.get('characters', 0):,} | "
            info_text += f"Lines: {info_dict.get('lines', 0)}"
            self.info_text.insert('1.0', info_text)
        self.info_text.config(state=tk.DISABLED)
    
    def get_webhook_override(self) -> dict:
        """Get webhook override state"""
        return {
            'override': self.webhook_override_var.get(),
            'custom_url': self.custom_webhook_var.get().strip()
        }
    
    def clear_all(self):
        """Clear all tab data"""
        self.url_entry.delete(0, tk.END)
        self.transcript_text.config(state=tk.NORMAL)
        self.transcript_text.delete('1.0', tk.END)
        self.transcript_text.config(state=tk.DISABLED)
        self.set_response("")
        self.set_transcript_info(None)
        self.current_video_id = None
        self.current_video_title = None
        self.set_status("Cleared")
    
    def show_success(self, message: str):
        """Show success message"""
        self.set_status(f"✓ {message}")
        messagebox.showinfo("Success", message)
    
    def show_error(self, message: str):
        """Show error message"""
        self.set_status(f"✗ {message}")
        messagebox.showerror("Error", message)
    
    def show_loading(self, show: bool = True):
        """Show/hide loading indicator"""
        if show and not self._loading:
            self._loading = True
            self.progress.grid(row=0, column=2, sticky=(tk.W, tk.E), padx=(20, 0))
            self.progress.start()
            self.fetch_btn.config(state=tk.DISABLED)
            self.send_btn.config(state=tk.DISABLED)
        elif not show and self._loading:
            self._loading = False
            self.progress.stop()
            self.progress.grid_remove()
            self.fetch_btn.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
    
    def set_status(self, message: str):
        """Set status message"""
        logger.info(f"[TranscribeTab] {message}")
