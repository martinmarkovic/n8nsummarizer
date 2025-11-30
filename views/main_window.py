"""
Extended Main Window GUI - Tkinter with theme toggle + export functionality
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
    """Main GUI window with dark/light mode and export functionality"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
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
        """Setup UI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Header with Title + Theme Toggle
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        header_frame.columnconfigure(0, weight=1)
        
        self.title_label = ttk.Label(header_frame, text=APP_TITLE, font=("Segoe UI", 14, "bold"))
        self.title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Theme toggle button
        self.theme_btn = ttk.Button(
            header_frame, 
            text="🌙 Dark Mode" if self.current_theme == 'light' else "☀️ Light Mode",
            command=self._toggle_theme
        )
        self.theme_btn.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))
        
        # File Selection Section
        self.file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        self.file_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.file_frame.columnconfigure(0, weight=1)
        
        self.file_path_var = tk.StringVar(value="No file selected")
        self.path_label = ttk.Label(self.file_frame, textvariable=self.file_path_var)
        self.path_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        
        button_frame = ttk.Frame(self.file_frame)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        browse_btn = ttk.Button(button_frame, text="Browse File", command=self._browse_file)
        browse_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # Webhook Override Section
        self.webhook_frame = ttk.LabelFrame(main_frame, text="n8n Webhook Override", padding="10")
        self.webhook_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.webhook_frame.columnconfigure(0, weight=1)
        
        override_check = ttk.Checkbutton(
            self.webhook_frame, 
            text="Save to .env when sending",
            variable=self.webhook_override_var
        )
        override_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(self.webhook_frame, text="Webhook URL:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        webhook_entry_frame = ttk.Frame(self.webhook_frame)
        webhook_entry_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        webhook_entry_frame.columnconfigure(0, weight=1)
        
        self.webhook_entry = ttk.Entry(webhook_entry_frame, textvariable=self.custom_webhook_var, width=80)
        self.webhook_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # File Info Section
        self.info_frame = ttk.LabelFrame(main_frame, text="File Info", padding="10")
        self.info_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.info_frame.columnconfigure(0, weight=1)
        
        self.info_text = tk.Text(self.info_frame, height=5, width=100, state=tk.DISABLED, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        info_scrollbar = ttk.Scrollbar(self.info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.config(yscrollcommand=info_scrollbar.set)
        
        # Content and Response Section
        content_response_frame = ttk.Frame(main_frame)
        content_response_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        content_response_frame.columnconfigure(0, weight=1)
        content_response_frame.columnconfigure(1, weight=1)
        content_response_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Content Preview (Left)
        self.content_frame = ttk.LabelFrame(content_response_frame, text="Content Preview & Edit", padding="10")
        self.content_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)
        
        self.content_text = scrolledtext.ScrolledText(
            self.content_frame, height=20, width=65, wrap=tk.WORD, font=("Courier", 15)
        )
        self.content_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Response Section (Right) with Export Controls
        response_container = ttk.Frame(content_response_frame)
        response_container.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        response_container.columnconfigure(0, weight=1)
        response_container.rowconfigure(0, weight=1)
        
        self.response_frame = ttk.LabelFrame(response_container, text="n8n Response", padding="10")
        self.response_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.response_frame.columnconfigure(0, weight=1)
        self.response_frame.rowconfigure(0, weight=1)
        
        self.response_text = scrolledtext.ScrolledText(
            self.response_frame, height=20, width=65, wrap=tk.WORD, font=("Courier", 15), state=tk.DISABLED
        )
        self.response_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Export Controls (below response box)
        export_controls_frame = ttk.Frame(response_container)
        export_controls_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        export_controls_frame.columnconfigure(0, weight=1)
        
        # Export location checkbox (checked by default)
        export_check1 = ttk.Checkbutton(
            export_controls_frame,
            text="Use original file location for export",
            variable=self.use_original_location_var
        )
        export_check1.grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 2))
        
        # Separate auto-export checkboxes
        export_check2 = ttk.Checkbutton(
            export_controls_frame,
            text="Auto-export as .txt after summarization",
            variable=self.auto_export_txt_var
        )
        export_check2.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 2))
        
        export_check3 = ttk.Checkbutton(
            export_controls_frame,
            text="Auto-export as .docx after summarization",
            variable=self.auto_export_docx_var
        )
        export_check3.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        
        # Export buttons
        export_buttons_frame = ttk.Frame(export_controls_frame)
        export_buttons_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        ttk.Label(export_buttons_frame, text="Export Response:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.export_txt_btn = ttk.Button(export_buttons_frame, text="📄 Export as .txt", command=self._export_txt_clicked)
        self.export_txt_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.export_docx_btn = ttk.Button(export_buttons_frame, text="📝 Export as .docx", command=self._export_docx_clicked)
        self.export_docx_btn.grid(row=0, column=2)
        
        # Buttons Section
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        button_frame.columnconfigure(1, weight=1)
        
        self.send_btn = ttk.Button(button_frame, text="Send to n8n", command=self._send_clicked)
        self.send_btn.grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        self.clear_btn = ttk.Button(button_frame, text="Clear All", command=self._clear_clicked)
        self.clear_btn.grid(row=0, column=1, padx=5, sticky=tk.E)
        
        # Status Bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
    
    def _apply_theme(self):
        """Apply current theme colors"""
        style = ttk.Style()
        style.theme_use('clam')
        
        colors = self.theme_colors
        
        # Configure widget styles
        style.configure('TLabel', background=colors['bg_primary'], foreground=colors['text_primary'])
        style.configure('TFrame', background=colors['bg_primary'])
        style.configure('TLabelFrame', background=colors['bg_primary'], bordercolor=colors['border'])
        style.configure('TLabelFrame.Label', background=colors['bg_primary'], foreground=colors['accent'], font=('Segoe UI', 30))
        style.configure('TButton', font=('Segoe UI', 13), background=colors['button_bg'], foreground=colors['text_primary'])
        style.map('TButton', background=[('active', colors['button_hover'])])
        style.configure('TCheckbutton', background=colors['bg_primary'], foreground=colors['text_primary'])
        style.configure('TEntry', fieldbackground=colors['bg_secondary'], foreground=colors['text_primary'])
        
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
        
        logger.info(f"Applied {self.current_theme} theme")
    
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
        self.set_status(f"[OK] {message}", 'success')
        messagebox.showinfo("Success", message)
    
    def show_error(self, message):
        self.set_status(f"[ERROR] {message}", 'error')
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
        self.set_status("Cleared")
