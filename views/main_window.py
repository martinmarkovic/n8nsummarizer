"""
Extended Main Window GUI - Tkinter with webhook override + double text size
"""
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from config import APP_TITLE, APP_WIDTH, APP_HEIGHT, SUPPORTED_EXTENSIONS, N8N_WEBHOOK_URL
from utils.logger import logger


class MainWindow:
    """Main GUI window for Text File Scanner - Extended with webhook override"""
    
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.resizable(True, True)
        
        # Callbacks
        self.on_file_selected = None
        self.on_send_clicked = None
        self.on_clear_clicked = None
        
        # Webhook override state
        self.webhook_override_var = tk.BooleanVar(value=False)
        self.custom_webhook_var = tk.StringVar(value=N8N_WEBHOOK_URL or '')
        
        self._setup_ui()
        self._apply_styling()
    
    def _setup_ui(self):
        """Setup UI components with side-by-side layout + webhook override"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text=APP_TITLE, font=("Segoe UI", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky=tk.W)
        
        # File Selection Section
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        self.file_path_var = tk.StringVar(value="No file selected")
        path_label = ttk.Label(file_frame, textvariable=self.file_path_var, foreground="#666")
        path_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        
        button_frame = ttk.Frame(file_frame)
        button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        browse_btn = ttk.Button(button_frame, text="Browse File", command=self._browse_file)
        browse_btn.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # WEBHOOK OVERRIDE SECTION - NEW
        webhook_frame = ttk.LabelFrame(main_frame, text="n8n Webhook Override", padding="10")
        webhook_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        webhook_frame.columnconfigure(0, weight=1)
        
        # Checkbox
        override_check = ttk.Checkbutton(
            webhook_frame, 
            text="Override config default webhook",
            variable=self.webhook_override_var
        )
        override_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        # Webhook URL input
        ttk.Label(webhook_frame, text="Custom Webhook URL:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        
        webhook_entry_frame = ttk.Frame(webhook_frame)
        webhook_entry_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        webhook_entry_frame.columnconfigure(0, weight=1)
        
        self.webhook_entry = ttk.Entry(webhook_entry_frame, textvariable=self.custom_webhook_var, width=80)
        self.webhook_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # File Info Section (moved down)
        info_frame = ttk.LabelFrame(main_frame, text="File Info", padding="10")
        info_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        info_frame.columnconfigure(0, weight=1)
        
        self.info_text = tk.Text(info_frame, height=5, width=100, state=tk.DISABLED, wrap=tk.WORD)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.config(yscrollcommand=info_scrollbar.set)
        
        # Content and Response Section (Side by side) - DOUBLE TEXT SIZE
        content_response_frame = ttk.Frame(main_frame)
        content_response_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        content_response_frame.columnconfigure(0, weight=1)
        content_response_frame.columnconfigure(1, weight=1)
        content_response_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Content Preview Section (Left)
        content_frame = ttk.LabelFrame(content_response_frame, text="Content Preview & Edit", padding="10")
        content_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        self.content_text = scrolledtext.ScrolledText(
            content_frame, height=20, width=65, wrap=tk.WORD, font=("Courier", 18)
        )
        self.content_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Response Section (Right) - DOUBLE TEXT SIZE
        response_frame = ttk.LabelFrame(content_response_frame, text="n8n Response", padding="10")
        response_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        response_frame.columnconfigure(0, weight=1)
        response_frame.rowconfigure(0, weight=1)
        
        self.response_text = scrolledtext.ScrolledText(
            response_frame, height=20, width=65, wrap=tk.WORD, font=("Courier", 18), state=tk.DISABLED
        )
        self.response_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
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
        status_frame.grid(row=6, row=5, column=0, columnspan=2, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
    
    def _apply_styling(self):
        """Apply custom styling"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background='#f7f9fb')
        style.configure('TFrame', background='#f7f9fb')
        style.configure('TLabelFrame', background='#f7f9fb')
        style.configure('TLabelFrame.Label', background='#f7f9fb')
        style.configure('TButton', font=('Segoe UI', 10))
    
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
            logger.info(f"User selected file: {file_path}")
            if self.on_file_selected:
                self.on_file_selected(file_path)
    
    def _send_clicked(self):
        if self.on_send_clicked:
            self.on_send_clicked()
    
    def _clear_clicked(self):
        if self.on_clear_clicked:
            self.on_clear_clicked()
    
    def get_webhook_override(self):
        """Get webhook override state for controller"""
        return {
            'override': self.webhook_override_var.get(),
            'custom_url': self.custom_webhook_var.get().strip()
        }
    
    def set_file_path(self, file_path):
        if file_path:
            self.file_path_var.set(f"[FILE] {file_path}")
        else:
            self.file_path_var.set("No file selected")
    
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
        """
        Display n8n response/summarization
        
        Args:
            response_text (str): Response text to display
        """
        self.set_response(response_text)
        logger.info(f"Displayed response: {len(response_text)} characters")
    
    def append_response(self, text):
        """Append to response textbox"""
        self.response_text.config(state=tk.NORMAL)
        self.response_text.insert(tk.END, text + "\n")
        self.response_text.see(tk.END)
        self.response_text.config(state=tk.DISABLED)
    
    def set_file_info(self, info_dict):
        """Update file info display with character count"""
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
