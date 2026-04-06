"""
File Tab - File Summarizer tab UI

Responsibilities:
    - Display file selection interface
    - Show file preview and response side-by-side
    - Provide webhook override settings
    - Show file metadata
    - Handle export preferences
    - Provide standard methods for controller

Use:
    >>> tab = FileTab(notebook)
    >>> controller = FileController(tab)
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from config import N8N_WEBHOOK_URL
from utils.logger import logger
from views.base_tab import BaseTab


class FileTab(BaseTab):
    """File Summarizer tab - upload file and send to n8n for summarization"""
    
    def __init__(self, parent):
        """
        Initialize File tab.
        
        Args:
            parent: Parent widget (ttk.Notebook or similar)
        """
        # Webhook override state
        self.webhook_override_var = tk.BooleanVar(value=False)
        self.custom_webhook_var = tk.StringVar(value=N8N_WEBHOOK_URL or '')
        
        # Export preferences
        self.use_original_location_var = tk.BooleanVar(value=False)
        self.auto_export_txt_var = tk.BooleanVar(value=False)
        self.auto_export_docx_var = tk.BooleanVar(value=False)
        
        # Store file info for smart export naming
        self.current_file_directory = None
        self.current_file_basename = None
        
        # UI state for loading indicator
        self._loading = False
        
        super().__init__(parent, "File Summarizer")
        
        # Tab-specific callbacks
        self.on_file_selected = None
        self.on_send_clicked = None
        self.on_export_txt = None
        self.on_export_docx = None
        
        logger.info("FileTab initialized")
    
    def _setup_ui(self):
        """Setup File tab UI"""
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)  # Content area expands
        
        # File Selection Section
        self._setup_file_selection_section()
        
        # Webhook Override Section
        self._setup_webhook_section()
        
        # File Info Section
        self._setup_file_info_section()
        
        # Content and Response Section (expandable)
        self._setup_content_response_section()
        
        # Bottom Action Bar
        self._setup_action_bar()
    
    def _setup_file_selection_section(self):
        """Setup file selection UI"""
        file_frame = ttk.LabelFrame(self, text="File Selection", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        self.file_path_var = tk.StringVar(value="No file selected")
        self.path_label = ttk.Label(file_frame, textvariable=self.file_path_var)
        self.path_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        
        button_frame = ttk.Frame(file_frame)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        browse_btn = ttk.Button(button_frame, text="Browse File", command=self._browse_file)
        browse_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
    
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
    
    def _setup_file_info_section(self):
        """Setup file info display UI"""
        info_frame = ttk.LabelFrame(self, text="File Info", padding="10")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(0, weight=1)
        
        self.info_text = tk.Text(info_frame, height=4, state=tk.DISABLED, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.config(yscrollcommand=info_scrollbar.set)
    
    def _setup_content_response_section(self):
        """Setup content preview and response display"""
        content_response_frame = ttk.Frame(self)
        content_response_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        content_response_frame.columnconfigure(0, weight=1)
        content_response_frame.columnconfigure(1, weight=1)
        content_response_frame.rowconfigure(0, weight=1)
        
        # Content Preview (Left)
        content_frame = ttk.LabelFrame(content_response_frame, text="Content Preview & Edit", padding="10")
        content_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        self.content_text = scrolledtext.ScrolledText(
            content_frame, height=20, width=65, wrap=tk.WORD, font=("Courier", 10)
        )
        self.content_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
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
        
        # Send to n8n button
        self.send_btn = ttk.Button(bottom_frame, text="Send to n8n", command=self._send_clicked)
        self.send_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        # Export controls
        export_controls_frame = ttk.Frame(bottom_frame)
        export_controls_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        ttk.Checkbutton(
            export_controls_frame,
            text="Use original location",
            variable=self.use_original_location_var
        ).grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        ttk.Checkbutton(
            export_controls_frame,
            text="Auto .txt",
            variable=self.auto_export_txt_var
        ).grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        ttk.Checkbutton(
            export_controls_frame,
            text="Auto .docx",
            variable=self.auto_export_docx_var
        ).grid(row=0, column=2, sticky=tk.W, padx=(0, 20))
        
        ttk.Label(export_controls_frame, text="Export:").grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        
        self.export_txt_btn = ttk.Button(export_controls_frame, text="📄 .txt", command=self._export_txt_clicked)
        self.export_txt_btn.grid(row=0, column=4, padx=(0, 5))
        
        self.export_docx_btn = ttk.Button(export_controls_frame, text="📝 .docx", command=self._export_docx_clicked)
        self.export_docx_btn.grid(row=0, column=5)
        
        # Clear button
        self.clear_btn = ttk.Button(bottom_frame, text="Clear All", command=self._clear_clicked)
        self.clear_btn.grid(row=0, column=2, sticky=tk.E, padx=(20, 0))
        
        # Loading indicator
        self.progress = ttk.Progressbar(bottom_frame, mode='indeterminate')
    
    # Button callbacks
    
    def _browse_file(self):
        """Handle browse file button"""
        filetypes = [
            ("All Supported", "*.txt *.log *.csv *.json *.xml *.srt *.docx"),
            ("Text Files", "*.txt"),
            ("Log Files", "*.log"),
            ("CSV Files", "*.csv"),
            ("JSON Files", "*.json"),
            ("XML Files", "*.xml"),
            ("Subtitles", "*.srt"),
            ("Word Documents", "*.docx"),
            ("All Files", "*.*")
        ]
        file_path = filedialog.askopenfilename(title="Select a file", filetypes=filetypes)
        if file_path:
            self.current_file_directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            self.current_file_basename = os.path.splitext(filename)[0]
            
            logger.info(f"File selected: {file_path}")
            if self.on_file_selected:
                self.on_file_selected(file_path)
    
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
        """Get file content"""
        return self.content_text.get('1.0', tk.END).rstrip()
    
    def get_response_content(self) -> str:
        """Get response content"""
        return self.response_text.get('1.0', tk.END).rstrip()
    
    def get_file_path(self) -> str:
        """Get current file path"""
        text = self.file_path_var.get()
        if text.startswith("[FILE] "):
            return text[7:]  # Remove "[FILE] " prefix
        return None
    
    def set_content(self, content: str):
        """Set file content"""
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete('1.0', tk.END)
        if content:
            self.content_text.insert('1.0', content)
        self.content_text.config(state=tk.NORMAL)
    
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
    
    def set_file_path(self, file_path: str):
        """Set file path display"""
        if file_path:
            self.file_path_var.set(f"[FILE] {file_path}")
            self.current_file_directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            self.current_file_basename = os.path.splitext(filename)[0]
        else:
            self.file_path_var.set("No file selected")
            self.current_file_directory = None
            self.current_file_basename = None
    
    def set_file_info(self, info_dict: dict):
        """Set file info display"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete('1.0', tk.END)
        if info_dict:
            info_text = f"File: {info_dict.get('name', 'N/A')} | "
            info_text += f"Size: {info_dict.get('size_kb', 0):.2f} KB | "
            info_text += f"Lines: {info_dict.get('lines', 0)} | "
            info_text += f"Characters: {info_dict.get('characters', 0)} | "
            info_text += f"Characters (no spaces): {info_dict.get('characters_no_spaces', 0)}\n"
            info_text += f"Path: {info_dict.get('path', 'N/A')}"
            self.info_text.insert('1.0', info_text)
        self.info_text.config(state=tk.DISABLED)
    
    def get_webhook_override(self) -> dict:
        """Get webhook override state"""
        return {
            'override': self.webhook_override_var.get(),
            'custom_url': self.custom_webhook_var.get().strip()
        }
    
    def get_export_preferences(self) -> dict:
        """Get export preferences"""
        return {
            'use_original_location': self.use_original_location_var.get(),
            'auto_export_txt': self.auto_export_txt_var.get(),
            'auto_export_docx': self.auto_export_docx_var.get(),
            'original_directory': self.current_file_directory,
            'original_basename': self.current_file_basename
        }
    
    def clear_all(self):
        """Clear all tab data"""
        self.set_file_path(None)
        self.set_content("")
        self.set_response("")
        self.set_file_info(None)
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
            self.send_btn.config(state=tk.DISABLED)
        elif not show and self._loading:
            self._loading = False
            self.progress.stop()
            self.progress.grid_remove()
            self.send_btn.config(state=tk.NORMAL)
    
    def set_status(self, message: str):
        """Set status message"""
        logger.info(f"[FileTab] {message}")
