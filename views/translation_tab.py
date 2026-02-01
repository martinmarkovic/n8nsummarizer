"""
Translation Tab - Translation feature for subtitle and document files

Provides:
    - File selection for translation
    - Source and target language selection
    - Translation model selection
    - Output format options
    - Progress tracking and status updates

Created: 2026-02-01
Version: 1.0
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional

from views.base_tab import BaseTab
from utils.logger import logger


class TranslationTab(BaseTab):
    """
    Translation tab for translating subtitle and document files.
    
    Features:
    - File selection and browsing
    - Source and target language selection
    - Translation model configuration
    - Output format options
    - Progress tracking
    - Status logging
    """
    
    # Supported languages
    LANGUAGES = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "pt": "Portuguese",
        "ru": "Russian",
        "ja": "Japanese",
        "zh": "Chinese",
        "ar": "Arabic",
        "hi": "Hindi",
        "ko": "Korean",
    }
    
    # Supported file types
    FILE_TYPES = [
        ("Subtitle Files", "*.srt *.vtt"),
        ("Text Files", "*.txt"),
        ("All Files", "*.*")
    ]
    
    def __init__(self, parent):
        """
        Initialize Translation tab.
        
        Args:
            parent: Parent widget (usually ttk.Notebook)
        """
        # Initialize state variables BEFORE calling super().__init__
        # because super().__init__() calls _setup_ui()
        self.selected_file: Optional[Path] = None
        
        # Call parent initializer (which will call _setup_ui)
        super().__init__(parent, "Translation")
        
        logger.info("TranslationTab initialized")
    
    def _setup_ui(self):
        """
        Setup Translation tab UI components.
        
        Creates:
        - File selection section
        - Language selection (source and target)
        - Model configuration
        - Output options
        - Action buttons
        - Status log
        """
        # Main container
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)  # Status log expands
        
        # File selection section
        self._setup_file_selection()
        
        # Language selection section
        self._setup_language_selection()
        
        # Output options section
        self._setup_output_options()
        
        # Action buttons section
        self._setup_action_buttons()
        
        # Status log section
        self._setup_status_log()
    
    def _setup_file_selection(self):
        """
        Setup file selection section.
        """
        file_frame = ttk.LabelFrame(self, text="📄 Select File to Translate", padding="10")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        
        # File path display
        self.file_path_var = tk.StringVar(value="No file selected")
        file_path_label = ttk.Label(
            file_frame,
            textvariable=self.file_path_var,
            wraplength=500,
            foreground="gray"
        )
        file_path_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Browse button
        browse_btn = ttk.Button(
            file_frame,
            text="📂 Browse File...",
            command=self._browse_file
        )
        browse_btn.grid(row=1, column=0, sticky=tk.W)
    
    def _setup_language_selection(self):
        """
        Setup language selection section.
        """
        lang_frame = ttk.LabelFrame(self, text="🌍 Language Settings", padding="10")
        lang_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        lang_frame.columnconfigure(1, weight=1)
        
        # Source language
        ttk.Label(lang_frame, text="Source Language:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.source_lang_var = tk.StringVar(value="en")
        source_lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.source_lang_var,
            values=[f"{code} - {name}" for code, name in self.LANGUAGES.items()],
            state="readonly",
            width=30
        )
        source_lang_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        source_lang_combo.set("en - English")
        
        # Target language
        ttk.Label(lang_frame, text="Target Language:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        self.target_lang_var = tk.StringVar(value="es")
        target_lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.target_lang_var,
            values=[f"{code} - {name}" for code, name in self.LANGUAGES.items()],
            state="readonly",
            width=30
        )
        target_lang_combo.grid(row=1, column=1, sticky=(tk.W, tk.E))
        target_lang_combo.set("es - Spanish")
    
    def _setup_output_options(self):
        """
        Setup output options section.
        """
        output_frame = ttk.LabelFrame(self, text="💾 Output Options", padding="10")
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)
        
        # Output folder
        ttk.Label(output_frame, text="Output Folder:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        output_btn_frame = ttk.Frame(output_frame)
        output_btn_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        self.output_same_folder_var = tk.BooleanVar(value=True)
        same_folder_check = ttk.Checkbutton(
            output_btn_frame,
            text="Same as source file",
            variable=self.output_same_folder_var
        )
        same_folder_check.pack(side=tk.LEFT)
        
        browse_output_btn = ttk.Button(
            output_btn_frame,
            text="Browse...",
            command=self._browse_output_folder
        )
        browse_output_btn.pack(side=tk.LEFT, padx=(10, 0))
    
    def _setup_action_buttons(self):
        """
        Setup action buttons section.
        """
        button_frame = ttk.Frame(self, padding="10")
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Translate button
        self.translate_btn = ttk.Button(
            button_frame,
            text="🌐 Translate",
            command=self._translate_clicked
        )
        self.translate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Clear button
        clear_btn = ttk.Button(
            button_frame,
            text="🗑 Clear",
            command=self._clear_clicked
        )
        clear_btn.pack(side=tk.LEFT)
    
    def _setup_status_log(self):
        """
        Setup status log section.
        """
        log_frame = ttk.LabelFrame(self, text="📋 Status Log", padding="10")
        log_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Status log with scrollbar
        self.status_log = tk.Text(
            log_frame,
            height=10,
            wrap=tk.WORD,
            font=("Segoe UI", 10)
        )
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.status_log.yview)
        self.status_log.configure(yscrollcommand=scrollbar.set)
        
        self.status_log.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Add initial message
        self._log("Translation tab ready. Select a file to begin.")
    
    # Event handlers
    
    def _browse_file(self):
        """
        Handle browse file button click.
        """
        filename = filedialog.askopenfilename(
            title="Select File to Translate",
            filetypes=self.FILE_TYPES
        )
        
        if filename:
            self.selected_file = Path(filename)
            self.file_path_var.set(str(self.selected_file))
            self._log(f"Selected file: {self.selected_file.name}")
            logger.info(f"File selected for translation: {self.selected_file}")
    
    def _browse_output_folder(self):
        """
        Handle browse output folder button click.
        """
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self._log(f"Output folder: {folder}")
            logger.info(f"Output folder selected: {folder}")
    
    def _translate_clicked(self):
        """
        Handle translate button click.
        """
        if not self.selected_file:
            messagebox.showwarning(
                "No File Selected",
                "Please select a file to translate."
            )
            return
        
        self._log("Translation feature coming soon...")
        logger.info("Translation requested (feature not yet implemented)")
    
    def _log(self, message: str):
        """
        Add message to status log.
        
        Args:
            message: Message to log
        """
        self.status_log.insert(tk.END, f"{message}\n")
        self.status_log.see(tk.END)
    
    # Abstract method implementations
    
    def get_content(self) -> str:
        """
        Get current tab content (status log).
        
        Returns:
            str: Current status log content
        """
        return self.status_log.get("1.0", tk.END)
    
    def clear_all(self):
        """
        Clear all tab data and reset to initial state.
        """
        # Clear file selection
        self.selected_file = None
        self.file_path_var.set("No file selected")
        
        # Reset language selections to defaults
        self.source_lang_var.set("en")
        self.target_lang_var.set("es")
        
        # Reset output options
        self.output_same_folder_var.set(True)
        
        # Clear status log
        self.status_log.delete("1.0", tk.END)
        self._log("Translation tab cleared. Ready for new translation.")
        
        logger.info("TranslationTab cleared")
