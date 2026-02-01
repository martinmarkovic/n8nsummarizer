"""
Main Window GUI v6.0 - Translation Tab Integration

This window manages:
- Header (title + font size + theme toggle)
- Tab container (notebook)
- Tab initialization (6 tabs total)
- Theme management
- Font size management with .env persistence
- Status bar

All tab-specific UI code moved to individual tab files.
Easy to add new tabs by creating new tab classes and initializing them here.

v6.0 Changes:
- Added 6th tab: Translation (UI placeholder for future translation workflows)
- Updated version references from v5.0 to v6.0

Created: 2025-11-30
Version: 6.0
"""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from dotenv import load_dotenv
import os

from config import (
    APP_TITLE, APP_WIDTH, APP_HEIGHT, DEFAULT_THEME, DARK_THEME, LIGHT_THEME
)
from utils.logger import logger
from views.file_tab import FileTab
from views.youtube_summarizer_tab import YouTubeSummarizerTab
from views.transcriber_tab import TranscriberTab
from views.bulk_summarizer_tab import BulkSummarizerTab
from views.bulk_transcriber_tab import BulkTranscriberTab
from views.translation_tab import TranslationTab

# Load environment variables
load_dotenv()


class MainWindow:
    """
    Main GUI window with tabbed interface.
    
    Manages:
    - Header and navigation
    - Font size control with .env persistence
    - Tab container (notebook)
    - Tab initialization
    - Theme management
    - Status bar
    
    Tab order (v6.0):
    1. File Summarizer
    2. YouTube Summarization
    3. Transcriber
    4. Bulk Summarizer
    5. Bulk Transcriber
    6. Translation (UI only)
    """
    
    # Font sizes
    FONT_SIZES = [8, 10, 12, 14, 16, 18, 20]
    DEFAULT_FONT_SIZE = 10
    ENV_KEY_FONT_SIZE = "APP_FONT_SIZE"
    ENV_FILE = ".env"
    
    def __init__(self, root):
        """
        Initialize main window.
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title(f"{APP_TITLE} v6.0")
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.resizable(True, True)
        
        # Theme state
        self.current_theme = DEFAULT_THEME
        self.theme_colors = LIGHT_THEME if self.current_theme == 'light' else DARK_THEME
        
        # Font size state - load from .env if available
        self.current_font_size = self._load_font_size_from_env()
        
        # Theme callback
        self.on_theme_toggle = None
        
        # Setup UI
        self._setup_ui()
        
        # IMPORTANT: Apply loaded font size AFTER tabs are created
        # This ensures all text widgets exist before we try to configure them
        self._apply_font_size()
        
        self._apply_theme()
        
        logger.info(f"MainWindow initialized (v6.0 - {self.current_theme} theme, {self.current_font_size}px font)")
    
    def _load_font_size_from_env(self) -> int:
        """
        Load font size preference from .env file.
        
        Returns:
            Font size in pixels. Returns DEFAULT_FONT_SIZE if not found or invalid.
        """
        try:
            env_font_size = os.getenv(self.ENV_KEY_FONT_SIZE)
            if env_font_size:
                font_size = int(env_font_size)
                # Validate that it's in our FONT_SIZES list
                if font_size in self.FONT_SIZES:
                    logger.info(f"Loaded font size from .env: {font_size}px")
                    return font_size
                else:
                    logger.warning(f"Font size {font_size} not in allowed sizes, using default")
                    return self.DEFAULT_FONT_SIZE
            else:
                logger.debug("No font size preference found in .env, using default")
                return self.DEFAULT_FONT_SIZE
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing font size from .env: {str(e)}, using default")
            return self.DEFAULT_FONT_SIZE
    
    def _save_font_size_to_env(self, font_size: int) -> bool:
        """
        Save font size preference to .env file.
        
        Updates or creates APP_FONT_SIZE in .env file without overwriting other settings.
        
        Args:
            font_size: Font size in pixels to save
        
        Returns:
            True if successful, False otherwise
        """
        try:
            env_path = Path(self.ENV_FILE)
            
            # Read existing .env content
            env_content = {}
            if env_path.exists():
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                # Skip APP_FONT_SIZE as we'll add updated version
                                if key.strip() != self.ENV_KEY_FONT_SIZE:
                                    env_content[key.strip()] = value.strip()
            
            # Add/update font size
            env_content[self.ENV_KEY_FONT_SIZE] = str(font_size)
            
            # Write back to .env
            with open(env_path, 'w') as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            
            logger.info(f"Saved font size preference to .env: {font_size}px")
            return True
        
        except Exception as e:
            logger.error(f"Error saving font size to .env: {str(e)}")
            return False
    
    def _setup_ui(self):
        """
        Setup main window UI.
        
        Creates:
        - Main frame
        - Header (title + font size + theme toggle)
        - Tab notebook with all tabs (6 total)
        - Status bar
        """
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Tab area expands
        
        # Header with Title + Font Size + Theme Toggle
        self._setup_header(main_frame)
        
        # Notebook with tabs
        self._setup_tabs(main_frame)
        
        # Status bar
        self._setup_status_bar(main_frame)
    
    def _setup_header(self, parent):
        """
        Setup header with title, font size controls, and theme toggle.
        
        Args:
            parent: Parent frame
        """
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        header_frame.columnconfigure(0, weight=1)
        
        self.title_label = ttk.Label(
            header_frame,
            text=f"{APP_TITLE} v6.0",
            font=("Segoe UI", 14, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Font size controls
        controls_frame = ttk.Frame(header_frame)
        controls_frame.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))
        
        ttk.Label(controls_frame, text="Font:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Decrease font button
        self.font_decrease_btn = ttk.Button(
            controls_frame,
            text="🔍-",
            width=3,
            command=self._decrease_font_size
        )
        self.font_decrease_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        # Font size display - Initialize with current font size
        self.font_size_var = tk.StringVar(value=f"{self.current_font_size}px")
        self.font_size_label = ttk.Label(
            controls_frame,
            textvariable=self.font_size_var,
            width=6,
            anchor=tk.CENTER
        )
        self.font_size_label.pack(side=tk.LEFT, padx=2)
        
        # Increase font button
        self.font_increase_btn = ttk.Button(
            controls_frame,
            text="🔍+",
            width=3,
            command=self._increase_font_size
        )
        self.font_increase_btn.pack(side=tk.LEFT, padx=(2, 15))
        
        # Theme toggle button
        self.theme_btn = ttk.Button(
            controls_frame,
            text="🌙 Dark Mode" if self.current_theme == 'light' else "☀️ Light Mode",
            command=self._toggle_theme
        )
        self.theme_btn.pack(side=tk.LEFT)
    
    def _setup_tabs(self, parent):
        """
        Setup tab notebook with all tabs.
        
        Tab order (v6.0):
        1. File Summarizer
        2. YouTube Summarization
        3. Transcriber
        4. Bulk Summarizer
        5. Bulk Transcriber
        6. Translation (UI only)
        
        Args:
            parent: Parent frame
        """
        # Create notebook (tab container)
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Tab 1: File Summarizer
        self.file_tab = FileTab(self.notebook)
        self.notebook.add(self.file_tab, text="📄 File Summarizer")
        
        # Tab 2: YouTube Summarization
        self.youtube_summarizer_tab = YouTubeSummarizerTab(self.notebook)
        self.notebook.add(self.youtube_summarizer_tab, text="🎜 YouTube Summarization")
        
        # Tab 3: Transcriber
        self.transcriber_tab = TranscriberTab(self.notebook)
        self.notebook.add(self.transcriber_tab, text="🗡 Transcriber")
        
        # Tab 4: Bulk Summarizer
        self.bulk_summarizer_tab = BulkSummarizerTab(self.notebook)
        self.notebook.add(self.bulk_summarizer_tab, text="📦 Bulk Summarizer")
        
        # Tab 5: Bulk Transcriber
        self.bulk_transcriber_tab = BulkTranscriberTab(self.notebook)
        self.notebook.add(self.bulk_transcriber_tab, text="🎬 Bulk Transcriber")
        
        # Tab 6: Translation (NEW in v6.0)
        self.translation_tab = TranslationTab(self.notebook)
        self.notebook.add(self.translation_tab, text="🌐 Translation")
        
        logger.info("All tabs initialized (v6.0 - Translation tab added)")
    
    def _setup_status_bar(self, parent):
        """
        Setup status bar and progress indicator.
        
        Args:
            parent: Parent frame
        """
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(
            status_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN
        )
        self.status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))
    
    def _apply_theme(self):
        """
        Apply current theme colors to all widgets.
        """
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
        style.configure('TRadiobutton', background=colors['bg_primary'], foreground=colors['text_primary'])
        style.configure('TEntry', fieldbackground=colors['bg_secondary'], foreground=colors['text_primary'])
        style.configure('TNotebook', background=colors['bg_primary'])
        style.configure('TNotebook.Tab', background=colors['bg_secondary'], foreground=colors['text_primary'])
        style.map('TNotebook.Tab', background=[('selected', colors['bg_primary'])])
        
        # Apply to root
        self.root.configure(bg=colors['bg_primary'])
        
        # Update text widget colors in tabs
        text_bg = colors['bg_secondary']
        text_fg = colors['text_primary']
        
        # File tab
        if hasattr(self, 'file_tab'):
            self.file_tab.content_text.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
            self.file_tab.response_text.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
            self.file_tab.info_text.configure(bg=text_bg, fg=text_fg)
            self.file_tab.path_label.configure(foreground=colors['text_secondary'])
        
        # YouTube Summarizer tab
        if hasattr(self, 'youtube_summarizer_tab'):
            self.youtube_summarizer_tab.summary_text.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        
        # Transcriber tab
        if hasattr(self, 'transcriber_tab'):
            self.transcriber_tab.transcript_text.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        
        # Bulk Summarizer tab
        if hasattr(self, 'bulk_summarizer_tab'):
            self.bulk_summarizer_tab.status_log.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        
        # Bulk Transcriber tab
        if hasattr(self, 'bulk_transcriber_tab'):
            self.bulk_transcriber_tab.status_log.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        
        # Translation tab (NEW)
        if hasattr(self, 'translation_tab'):
            self.translation_tab.source_text.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
            self.translation_tab.target_text.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        
        # Title label
        if hasattr(self, 'title_label'):
            self.title_label.configure(foreground=colors['text_primary'])
        
        logger.info(f"Applied {self.current_theme} theme")
    
    def _toggle_theme(self):
        """
        Toggle between dark and light mode.
        """
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.theme_colors = DARK_THEME if self.current_theme == 'dark' else LIGHT_THEME
        
        # Update button text
        self.theme_btn.configure(
            text="🌙 Dark Mode" if self.current_theme == 'light' else "☀️ Light Mode"
        )
        
        # Apply new theme
        self._apply_theme()
        
        # Call callback if set
        if self.on_theme_toggle:
            self.on_theme_toggle(self.current_theme)
    
    def _increase_font_size(self):
        """
        Increase font size of all text widgets and save preference to .env
        """
        # Find next size
        current_index = self.FONT_SIZES.index(self.current_font_size)
        if current_index < len(self.FONT_SIZES) - 1:
            self.current_font_size = self.FONT_SIZES[current_index + 1]
            self._apply_font_size()
            # Save to .env
            self._save_font_size_to_env(self.current_font_size)
            logger.info(f"Font size increased to {self.current_font_size}px (saved to .env)")
    
    def _decrease_font_size(self):
        """
        Decrease font size of all text widgets and save preference to .env
        """
        # Find previous size
        current_index = self.FONT_SIZES.index(self.current_font_size)
        if current_index > 0:
            self.current_font_size = self.FONT_SIZES[current_index - 1]
            self._apply_font_size()
            # Save to .env
            self._save_font_size_to_env(self.current_font_size)
            logger.info(f"Font size decreased to {self.current_font_size}px (saved to .env)")
    
    def _apply_font_size(self):
        """
        Apply current font size to all text widgets.
        
        v6.0: Now also applies to Translation tab
        """
        # Update display label
        self.font_size_var.set(f"{self.current_font_size}px")
        
        # Apply to File tab
        if hasattr(self, 'file_tab'):
            self.file_tab.content_text.configure(font=("Segoe UI", self.current_font_size))
            self.file_tab.response_text.configure(font=("Segoe UI", self.current_font_size))
            self.file_tab.info_text.configure(font=("Segoe UI", self.current_font_size - 1))
        
        # Apply to YouTube Summarizer tab
        if hasattr(self, 'youtube_summarizer_tab'):
            self.youtube_summarizer_tab.summary_text.configure(font=("Segoe UI", self.current_font_size))
        
        # Apply to Transcriber tab
        if hasattr(self, 'transcriber_tab'):
            self.transcriber_tab.transcript_text.configure(font=("Segoe UI", self.current_font_size))
        
        # Apply to Bulk Summarizer tab
        if hasattr(self, 'bulk_summarizer_tab'):
            self.bulk_summarizer_tab.status_log.configure(font=("Segoe UI", self.current_font_size))
        
        # Apply to Bulk Transcriber tab
        if hasattr(self, 'bulk_transcriber_tab'):
            self.bulk_transcriber_tab.status_log.configure(font=("Segoe UI", self.current_font_size))
        
        # Apply to Translation tab (NEW)
        if hasattr(self, 'translation_tab'):
            self.translation_tab.source_text.configure(font=("Segoe UI", self.current_font_size))
            self.translation_tab.target_text.configure(font=("Segoe UI", self.current_font_size))
        
        logger.debug(f"Applied font size {self.current_font_size}px to all text widgets")
    
    # Status bar methods
    
    def set_status(self, message: str):
        """
        Set status bar message.
        
        Args:
            message: Status message
        """
        self.status_var.set(message)
        logger.info(f"Status: {message}")
    
    # Convenience methods to access current tab
    
    def get_current_tab(self):
        """
        Get currently active tab.
        
        Returns:
            Current tab widget or None
        """
        tab_index = self.notebook.index(self.notebook.select())
        if tab_index == 0:
            return self.file_tab
        elif tab_index == 1:
            return self.youtube_summarizer_tab
        elif tab_index == 2:
            return self.transcriber_tab
        elif tab_index == 3:
            return self.bulk_summarizer_tab
        elif tab_index == 4:
            return self.bulk_transcriber_tab
        elif tab_index == 5:
            return self.translation_tab
        return None
