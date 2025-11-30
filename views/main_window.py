"""
Main Window GUI v2.0 - Tabbed Interface

This is the main window with tabbed interface supporting multiple features:
- Tab 1: File Summarizer (current functionality)
- Tab 2: YouTube Summarizer (placeholder for future implementation)

Created: 2025-11-30
Version: 2.0
"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
from datetime import datetime
from config import (
    APP_TITLE, APP_WIDTH, APP_HEIGHT, SUPPORTED_EXTENSIONS, 
    N8N_WEBHOOK_URL, DARK_THEME, LIGHT_THEME, DEFAULT_THEME, EXPORT_DIR,
    DEFAULT_USE_ORIGINAL_LOCATION, DEFAULT_AUTO_EXPORT_TXT, DEFAULT_AUTO_EXPORT_DOCX
)
from utils.logger import logger


class MainWindow:
    """Main GUI window with tabbed interface for multiple features"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_TITLE} v2.0")
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.resizable(True, True)
        
        # Callbacks
        self.on_file_selected = None
        self.on_send_clicked = None
        self.on_clear_clicked = None
        self.on_export_txt = None
        self.on_export_docx = None
        self.on_theme_toggle = None
        
        # Webhook override state
        self.webhook_override_var = tk.BooleanVar(value=False)
        self.custom_webhook_var = tk.StringVar(value=N8N_WEBHOOK_URL or '')
        
        # Export preferences - Load from config defaults
        self.use_original_location_var = tk.BooleanVar(value=DEFAULT_USE_ORIGINAL_LOCATION)
        self.auto_export_txt_var = tk.BooleanVar(value=DEFAULT_AUTO_EXPORT_TXT)
        self.auto_export_docx_var = tk.BooleanVar(value=DEFAULT_AUTO_EXPORT_DOCX)
        
        # Theme state
        self.current_theme = DEFAULT_THEME
        self.theme_colors = LIGHT_THEME if self.current_theme == 'light' else DARK_THEME
        
        # Store current file info for smart export naming
        self.current_file_directory = None
        self.current_file_basename = None
        
        self._setup_ui()
        self._apply_theme()
    
    def _setup_ui(self):
        """Setup UI components with tabbed interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Tab area expands
        
        # Header with Title + Theme Toggle
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        header_frame.columnconfigure(0, weight=1)
        
        self.title_label = ttk.Label(header_frame, text=f"{APP_TITLE} v2.0", font=("Segoe UI", 14, "bold"))
        self.title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Theme toggle button
        self.theme_btn = ttk.Button(
            header_frame, 
            text="🌙 Dark Mode" if self.current_theme == 'light' else "☀️ Light Mode",
            command=self._toggle_theme
        )
        self.theme_btn.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))
        
        # Create Notebook (Tabbed Interface)
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Tab 1: File Summarizer (current functionality)
        self.file_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.file_tab, text="📄 File Summarizer")
        self._setup_file_tab()
        
        # Tab 2: YouTube Summarizer (placeholder)
        self.youtube_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.youtube_tab, text="🎥 YouTube")
        self._setup_youtube_tab()
        
        # Status Bar (global - below tabs)
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="Ready - File Summarizer")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
    
    def _setup_file_tab(self):
        """Setup File Summarizer tab with current functionality"""
        self.file_tab.columnconfigure(0, weight=1)
        self.file_tab.rowconfigure(3, weight=1)  # Content area expands
        
        # File Selection Section
        file_frame = ttk.LabelFrame(self.file_tab, text="File Selection", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        self.file_path_var = tk.StringVar(value="No file selected")
        self.path_label = ttk.Label(file_frame, textvariable=self.file_path_var)
        self.path_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        
        button_frame = ttk.Frame(file_frame)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        browse_btn = ttk.Button(button_frame, text="Browse File", command=self._browse_file)
        browse_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # Webhook Override Section
        webhook_frame = ttk.LabelFrame(self.file_tab, text="n8n Webhook Override", padding="10")
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
        
        # File Info Section
        info_frame = ttk.LabelFrame(self.file_tab, text="File Info", padding="10")
        info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(0, weight=1)
        
        self.info_text = tk.Text(info_frame, height=4, state=tk.DISABLED, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.config(yscrollcommand=info_scrollbar.set)
        
        # Content and Response Section
        content_response_frame = ttk.Frame(self.file_tab)
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
        
        # Bottom Action Bar - Send to n8n, Export Controls, and Clear All
        bottom_frame = ttk.Frame(self.file_tab)
        bottom_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        bottom_frame.columnconfigure(1, weight=1)  # Middle section expands
        
        # Left: Send to n8n button
        self.send_btn = ttk.Button(bottom_frame, text="Send to n8n", command=self._send_clicked)
        self.send_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        # Middle: Export Controls (compact horizontal layout)
        export_controls_frame = ttk.Frame(bottom_frame)
        export_controls_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Checkboxes (horizontal)
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
        
        # Export buttons
        ttk.Label(export_controls_frame, text="Export:").grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        
        self.export_txt_btn = ttk.Button(export_controls_frame, text="📄 .txt", command=self._export_txt_clicked)
        self.export_txt_btn.grid(row=0, column=4, padx=(0, 5))
        
        self.export_docx_btn = ttk.Button(export_controls_frame, text="📝 .docx", command=self._export_docx_clicked)
        self.export_docx_btn.grid(row=0, column=5)
        
        # Right: Clear All button
        self.clear_btn = ttk.Button(bottom_frame, text="Clear All", command=self._clear_clicked)
        self.clear_btn.grid(row=0, column=2, sticky=tk.E, padx=(20, 0))
    
    def _setup_youtube_tab(self):
        """Setup YouTube Summarizer tab (placeholder)"""
        self.youtube_tab.columnconfigure(0, weight=1)
        self.youtube_tab.rowconfigure(0, weight=1)
        
        # Placeholder content
        placeholder_frame = ttk.Frame(self.youtube_tab)
        placeholder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        placeholder_frame.columnconfigure(0, weight=1)
        placeholder_frame.rowconfigure(0, weight=1)
        
        # Centered message
        message_frame = ttk.Frame(placeholder_frame)
        message_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        ttk.Label(
            message_frame, 
            text="🎥 YouTube Summarizer", 
            font=("Segoe UI", 18, "bold")
        ).pack(pady=(0, 10))
        
        ttk.Label(
            message_frame,
            text="Coming soon in v2.1!",
            font=("Segoe UI", 12)
        ).pack(pady=(0, 5))
        
        ttk.Label(
            message_frame,
            text="Features planned:",
            font=("Segoe UI", 10, "bold")
        ).pack(pady=(10, 5))
        
        features = [
            "• Enter YouTube video URL",
            "• Fetch video metadata",
            "• Download transcript automatically",
            "• Send to n8n for summarization",
            "• Export transcript + summary"
        ]
        
        for feature in features:
            ttk.Label(
                message_frame,
                text=feature,
                font=("Segoe UI", 10)
            ).pack(anchor=tk.W, pady=2)
    
    def _apply_theme(self):
        """Apply current theme colors"""
        style = ttk.Style()
        style.theme_use('clam')
        
        colors = self.theme_colors
        
        # Configure widget styles
        style.configure('TLabel', background=colors['bg_primary'], foreground=colors['text_primary'])
        style.configure('TFrame', background=colors['bg_primary'])
        style.configure('TLabelFrame', background=colors['bg_primary'], bordercolor=colors['border'])
        style.configure('TLabelFrame.Label', background=colors['bg_primary'], foreground=colors['accent'], font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10), background=colors['button_bg'], foreground=colors['text_primary'])
        style.map('TButton', background=[('active', colors['button_hover'])])
        style.configure('TCheckbutton', background=colors['bg_primary'], foreground=colors['text_primary'])
        style.configure('TEntry', fieldbackground=colors['bg_secondary'], foreground=colors['text_primary'])
        style.configure('TNotebook', background=colors['bg_primary'])
        style.configure('TNotebook.Tab', background=colors['bg_secondary'], foreground=colors['text_primary'])
        style.map('TNotebook.Tab', background=[('selected', colors['bg_primary'])])
        
        # Apply to root and text widgets
        self.root.configure(bg=colors['bg_primary'])
        
        # Text widgets
        text_bg = colors['bg_secondary']
        text_fg = colors['text_primary']
        
        self.content_text.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        self.response_text.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        self.info_text.configure(bg=text_bg, fg=text_fg)
        
        # Path label color
        self.path_label.configure(foreground=colors['text_secondary'])
        
        # Title label color
        self.title_label.configure(foreground=colors['text_primary'])
        
        logger.info(f"Applied {self.current_theme} theme to v2.0 tabbed interface")
    
    def _toggle_theme(self):
        """Toggle between dark and light mode"""
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.theme_colors = DARK_THEME if self.current_theme == 'dark' else LIGHT_THEME
        
        # Update button text
        self.theme_btn.configure(
            text="🌙 Dark Mode" if self.current_theme == 'light' else "☀️ Light Mode"
        )
        
        # Apply new theme
        self._apply_theme()
        
        # Call controller callback to save preference
        if self.on_theme_toggle:
            self.on_theme_toggle(self.current_theme)
    
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
            # Store directory and basename for smart export naming
            self.current_file_directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            self.current_file_basename = os.path.splitext(filename)[0]  # Remove extension
            
            logger.info(f"User selected file: {file_path}")
            logger.info(f"File directory stored: {self.current_file_directory}")
            logger.info(f"File basename stored: {self.current_file_basename}")
            
            if self.on_file_selected:
                self.on_file_selected(file_path)
    
    def _send_clicked(self):
        if self.on_send_clicked:
            self.on_send_clicked()
    
    def _clear_clicked(self):
        if self.on_clear_clicked:
            self.on_clear_clicked()
    
    def _export_txt_clicked(self):
        """Export response as .txt file"""
        if self.on_export_txt:
            self.on_export_txt()
    
    def _export_docx_clicked(self):
        """Export response as .docx file"""
        if self.on_export_docx:
            self.on_export_docx()
    
    def get_webhook_override(self):
        """Get webhook override state"""
        return {
            'override': self.webhook_override_var.get(),
            'custom_url': self.custom_webhook_var.get().strip()
        }
    
    def get_export_preferences(self):
        """Get export preferences"""
        return {
            'use_original_location': self.use_original_location_var.get(),
            'auto_export_txt': self.auto_export_txt_var.get(),
            'auto_export_docx': self.auto_export_docx_var.get(),
            'original_directory': self.current_file_directory,
            'original_basename': self.current_file_basename
        }
    
    def get_response_content(self):
        """Get current response text content"""
        return self.response_text.get('1.0', tk.END).rstrip()
    
    def set_file_path(self, file_path):
        if file_path:
            self.file_path_var.set(f"[FILE] {file_path}")
            # Store directory and basename
            self.current_file_directory = os.path.dirname(file_path)
            filename = os.path.basename(file_path)
            self.current_file_basename = os.path.splitext(filename)[0]
        else:
            self.file_path_var.set("No file selected")
            self.current_file_directory = None
            self.current_file_basename = None
    
    def set_content(self, content):
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete('1.0', tk.END)
        if content:
            self.content_text.insert('1.0', content)
        self.content_text.config(state=tk.NORMAL)
    
    def get_content(self):
        return self.content_text.get('1.0', tk.END).rstrip()
    
    def set_response(self, response):
        """Set response textbox content"""
        self.response_text.config(state=tk.NORMAL)
        self.response_text.delete('1.0', tk.END)
        if response:
            self.response_text.insert('1.0', response)
        self.response_text.config(state=tk.DISABLED)
    
    def display_response(self, response_text):
        """Display n8n response/summarization"""
        self.set_response(response_text)
        logger.info(f"Displayed response: {len(response_text)} characters")
    
    def append_response(self, text):
        """Append to response textbox"""
        self.response_text.config(state=tk.NORMAL)
        self.response_text.insert(tk.END, text + "\n")
        self.response_text.see(tk.END)
        self.response_text.config(state=tk.DISABLED)
    
    def set_file_info(self, info_dict):
        """Update file info display"""
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
    
    def set_status(self, message, status_type='info'):
        self.status_var.set(message)
        logger.info(f"Status: {message}")
    
    def show_success(self, message):
        self.set_status(f"✓ {message}", 'success')
        messagebox.showinfo("Success", message)
    
    def show_error(self, message):
        self.set_status(f"✗ {message}", 'error')
        messagebox.showerror("Error", message)
    
    def show_loading(self, show=True):
        if show:
            self.progress.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
            self.progress.start()
            self.send_btn.config(state=tk.DISABLED)
        else:
            self.progress.stop()
            self.progress.grid_remove()
            self.send_btn.config(state=tk.NORMAL)
    
    def clear_all(self):
        self.set_file_path(None)
        self.set_content("")
        self.set_response("")
        self.set_file_info(None)
        self.set_status("Cleared - Ready")
