"""
Main Window GUI v2.4 - Enhanced UI with Output Options

This window manages:
- Header (title + theme toggle)
- Tab container (notebook)
- Tab initialization (FileTab, TranscriberTab)
- Theme management
- Status bar

All tab-specific UI code moved to individual tab files.
Easy to add new tabs by creating new tab classes and initializing them here.

Created: 2025-11-30
Refactored: 2025-12-07 (v2.2 - Views refactoring)
Updated: 2025-12-07 (v2.3 - Transcriber tab integration)
Enhanced: 2025-12-07 (v2.4 - UI improvements and output options)
Version: 2.4
"""
import tkinter as tk
from tkinter import ttk, messagebox
from config import (
    APP_TITLE, APP_WIDTH, APP_HEIGHT, DEFAULT_THEME, DARK_THEME, LIGHT_THEME
)
from utils.logger import logger
from views.file_tab import FileTab
from views.transcriber_tab import TranscriberTab


class MainWindow:
    """
    Main GUI window with tabbed interface.
    
    Manages:
    - Header and navigation
    - Tab container (notebook)
    - Tab initialization
    - Theme management
    - Status bar
    """
    
    def __init__(self, root):
        """
        Initialize main window.
        
        Args:
            root: Tkinter root window
        """
        self.root = root
        self.root.title(f"{APP_TITLE} v2.4")
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.resizable(True, True)
        
        # Theme state
        self.current_theme = DEFAULT_THEME
        self.theme_colors = LIGHT_THEME if self.current_theme == 'light' else DARK_THEME
        
        # Theme callback
        self.on_theme_toggle = None
        
        # Setup UI
        self._setup_ui()
        self._apply_theme()
        
        logger.info(f"MainWindow initialized (v2.4 - {self.current_theme} theme)")
    
    def _setup_ui(self):
        """
        Setup main window UI.
        
        Creates:
        - Main frame
        - Header (title + theme toggle)
        - Tab notebook with FileTab and TranscriberTab
        - Status bar
        """
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)  # Tab area expands
        
        # Header with Title + Theme Toggle
        self._setup_header(main_frame)
        
        # Notebook with tabs
        self._setup_tabs(main_frame)
        
        # Status bar
        self._setup_status_bar(main_frame)
    
    def _setup_header(self, parent):
        """
        Setup header with title and theme toggle.
        
        Args:
            parent: Parent frame
        """
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        header_frame.columnconfigure(0, weight=1)
        
        self.title_label = ttk.Label(
            header_frame,
            text=f"{APP_TITLE} v2.4",
            font=("Segoe UI", 14, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Theme toggle button
        self.theme_btn = ttk.Button(
            header_frame,
            text="🌙 Dark Mode" if self.current_theme == 'light' else "☀️ Light Mode",
            command=self._toggle_theme
        )
        self.theme_btn.grid(row=0, column=1, sticky=tk.E, padx=(10, 0))
    
    def _setup_tabs(self, parent):
        """
        Setup tab notebook with FileTab and TranscriberTab.
        
        Args:
            parent: Parent frame
        """
        # Create notebook (tab container)
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # File Summarizer Tab
        self.file_tab = FileTab(self.notebook)
        self.notebook.add(self.file_tab, text="📄 File Summarizer")
        
        # Transcriber Tab (Local Files + YouTube URLs)
        self.transcriber_tab = TranscriberTab(self.notebook)
        self.notebook.add(self.transcriber_tab, text="🎬 Transcriber")
        
        # NOTE: To add new tabs in future:
        # 1. Create new tab class inheriting from BaseTab in views/
        # 2. Initialize here: self.my_tab = MyTab(self.notebook)
        # 3. Add to notebook: self.notebook.add(self.my_tab, text="📌 Tab Name")
        # 4. That's it! The pattern is consistent.
    
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
        
        # Transcriber tab
        if hasattr(self, 'transcriber_tab'):
            self.transcriber_tab.transcript_text.configure(bg=text_bg, fg=text_fg, insertbackground=text_fg)
        
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
            Current tab widget (FileTab or TranscriberTab)
        """
        tab_index = self.notebook.index(self.notebook.select())
        if tab_index == 0:
            return self.file_tab
        elif tab_index == 1:
            return self.transcriber_tab
        return None
