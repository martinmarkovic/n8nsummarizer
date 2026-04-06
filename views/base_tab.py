"""
Base Tab - Abstract base class for all application tabs

Provides:
    - Standardized interface for all tabs
    - Common callback definitions
    - Standard methods (clear, export, etc.)
    - Template structure for consistency

Convention:
    Every tab should inherit from BaseTab and implement:
    - _setup_ui() - Create tab-specific UI
    - get_content() - Return current content
    - clear_all() - Clear all tab data
    - Optional: custom methods for tab-specific features

Future tabs can be added following this pattern.
"""
from abc import ABC, abstractmethod
import tkinter as tk
from tkinter import ttk
from utils.logger import logger


class BaseTab(ttk.Frame, ABC):
    """
    Abstract base class for application tabs.
    
    All tabs should inherit from this class and implement required methods.
    """
    
    def __init__(self, parent, tab_name: str):
        """
        Initialize base tab.
        
        Args:
            parent: Parent widget (usually ttk.Notebook)
            tab_name: Display name for tab (e.g., 'File Summarizer')
        """
        super().__init__(parent, padding="10")
        
        self.tab_name = tab_name
        self.root = self._get_root(parent)
        
        # Standard callbacks - implement in subclass or controller
        self.on_clear_clicked = None
        
        logger.info(f"Initializing {tab_name} tab")
        
        # Setup tab UI
        self._setup_ui()
    
    def _get_root(self, widget):
        """Get root window from any widget"""
        current = widget
        while current is not None:
            if isinstance(current, tk.Tk):
                return current
            current = current.master
        return None
    
    @abstractmethod
    def _setup_ui(self):
        """
        Setup tab UI components.
        Must be implemented by subclass.
        
        Example:
            def _setup_ui(self):
                # Create your UI components here
                frame = ttk.LabelFrame(self, text="My Section")
                frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        """
        pass
    
    @abstractmethod
    def get_content(self) -> str:
        """
        Get current tab content.
        Must be implemented by subclass.
        
        Returns:
            str: Current content or empty string
        """
        pass
    
    @abstractmethod
    def clear_all(self):
        """
        Clear all tab data.
        Must be implemented by subclass.
        
        Example:
            def clear_all(self):
                self.content_text.delete('1.0', tk.END)
                self.response_text.delete('1.0', tk.END)
        """
        pass
    
    # Standard methods - implement in subclass if needed
    
    def set_status(self, message: str):
        """
        Set tab status message.
        Default implementation posts to logger.
        Override in subclass to show in UI.
        """
        logger.info(f"[{self.tab_name}] {message}")
    
    def show_error(self, message: str):
        """
        Show error message.
        Default implementation posts to logger.
        Override in subclass to show as messagebox.
        """
        logger.error(f"[{self.tab_name}] Error: {message}")
    
    def show_success(self, message: str):
        """
        Show success message.
        Default implementation posts to logger.
        Override in subclass to show as messagebox.
        """
        logger.info(f"[{self.tab_name}] Success: {message}")
    
    def show_loading(self, show: bool = True):
        """
        Show/hide loading indicator.
        Default implementation does nothing.
        Override in subclass to show progress bar.
        """
        pass
    
    # Callback wiring
    
    def _clear_clicked(self):
        """Handle clear button click"""
        if self.on_clear_clicked:
            self.on_clear_clicked()
        else:
            self.clear_all()
            self.set_status("Cleared")
