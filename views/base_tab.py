"""
Base Tab - Abstract base classes for all application tabs

Provides:
    - Standardized interface for all tabs
    - Common callback definitions
    - Standard methods (clear, export, etc.)
    - Template structure for consistency

Two base classes are available, both sharing the same behaviour via TabMixin:

    BaseTab     - ttk.Frame based (legacy tabs, unchanged behaviour)
    CTkBaseTab  - customtkinter.CTkFrame based (migrated tabs)

This split exists so the ttk -> CustomTkinter migration can proceed one tab at
a time: a tab only needs to swap its base class and its widgets, while all the
shared helpers (context menus, status/error reporting, root lookup) stay in one
place.

Convention:
    Every tab should inherit from BaseTab or CTkBaseTab and implement:
    - _setup_ui() - Create tab-specific UI
    - get_content() - Return current content
    - clear_all() - Clear all tab data
    - Optional: custom methods for tab-specific features
"""

from abc import ABC, abstractmethod
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from utils.logger import logger
from utils.i18n import t


class TabMixin:
    """
    Shared tab behaviour, independent of the widget toolkit.

    Holds everything that does not depend on whether the tab is a ttk.Frame or
    a CTkFrame, so both base classes expose an identical interface to
    controllers.
    """

    def _init_tab(self, parent, tab_name: str):
        """
        Common initialization. Called by the concrete base class __init__ after
        the underlying frame has been constructed.

        Args:
            parent: Parent widget (the notebook)
            tab_name: Display name for the tab (e.g. 'File Summarizer')
        """
        self.tab_name = tab_name
        self.root = self._get_root(parent)

        # Standard callbacks - implement in subclass or controller
        self.on_clear_clicked = None

        logger.info(f"Initializing {tab_name} tab")

        # Setup tab UI
        self._setup_ui()

    def _get_root(self, widget):
        """
        Get root window from any widget.

        Works for both tk.Tk and customtkinter.CTk roots, since CTk subclasses
        tk.Tk.
        """
        current = widget
        while current is not None:
            if isinstance(current, tk.Tk):
                return current
            current = current.master
        return None

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
            self.set_status(t("common.cleared"))

    def get_main_window(self):
        """
        Get the MainWindow instance so a tab can reach its sibling tabs.

        MainWindow is a plain object, not a widget, so it never appears in the
        ``master`` chain. Walking that chain therefore always returned None and
        every cross-tab feature built on it silently did nothing. MainWindow
        now publishes itself as ``main_window`` on the Tk root, so the lookup
        is: climb to a widget carrying that attribute and return it.

        Returns:
            MainWindow instance, or None if it has not registered yet.
        """
        current = self
        while current is not None:
            window = getattr(current, "main_window", None)
            if window is not None:
                return window
            # Legacy shape: an object in the chain that *is* the main window.
            if hasattr(current, "summarizer_tab"):
                return current
            current = getattr(current, "master", None)
        return None

    def _register_context_menu(self, widget, items: list) -> "AppContextMenu":
        """
        Register a right-click context menu on a Text widget.

        Args:
            widget: The text widget to attach the menu to (tk.Text,
                    ScrolledText or CTkTextbox).
            items: List of dicts, each with:
                   {"label": str, "command": callable}
                   or {"separator": True}

        Returns:
            AppContextMenu instance (so caller can keep a reference if needed)
        """
        # Lazy import to avoid circular dependencies
        from views.context_menu import AppContextMenu

        # Create and configure the context menu
        menu = AppContextMenu(widget)

        # Add items from the definitions
        for item in items:
            if "separator" in item:
                menu.add_separator()
            elif item.get("copy"):
                menu.add_copy_command(item.get("label"))
            elif item.get("paste"):
                menu.add_paste_command(item.get("label"))
            elif item.get("tts_read"):
                menu.add_tts_read_command(item["tts_read"])
            elif item.get("tts_stop"):
                menu.add_tts_stop_command()
            elif item.get("fullscreen"):
                menu.add_fullscreen_command(
                    title=item.get("title"),
                    editable=item.get("editable", False),
                )
            else:
                menu.add_command(item["label"], item["command"])

        # Build and bind the menu
        menu.bind()

        return menu

    def _register_entry_context_menu(self, entry, allow_paste: bool = True) -> "AppContextMenu":
        """
        Attach a simple right-click context menu (Copy + optional Paste) to a
        small single-line widget such as an Entry used for URLs or paths.

        Args:
            entry: The Entry widget to attach the menu to (ttk.Entry or CTkEntry).
            allow_paste: Include a Paste item (skip for read-only fields).

        Returns:
            The AppContextMenu instance.
        """
        from views.context_menu import AppContextMenu

        menu = AppContextMenu(entry)
        if allow_paste:
            menu.add_paste_command()
        menu.add_copy_command()
        menu.bind()
        return menu

    def _selection_or_all(self, widget) -> str:
        """
        Return the current text selection in `widget`, or its full text if
        nothing is selected. Used by TTS "Read in Voice".
        """
        from views.ctk_compat import unwrap_text

        widget = unwrap_text(widget)
        try:
            if widget.tag_ranges("sel"):
                selected = widget.get("sel.first", "sel.last")
                if selected and selected.strip():
                    return selected
        except tk.TclError:
            pass
        return widget.get("1.0", tk.END)

    def get_forwarded_text(self) -> str:
        """
        Get text that was forwarded from another tab (e.g., translation tab).

        Returns:
            Forwarded text, or empty string if none
        """
        return getattr(self, "_forwarded_text", "")

    def clear_forwarded_text(self):
        """Clear any forwarded text."""
        if hasattr(self, "_forwarded_text"):
            del self._forwarded_text


class BaseTab(TabMixin, ttk.Frame, ABC):
    """
    Abstract base class for ttk-based application tabs.

    Used by all tabs that have not yet been migrated to CustomTkinter.
    """

    def __init__(self, parent, tab_name: str):
        """
        Initialize base tab.

        Args:
            parent: Parent widget (the notebook)
            tab_name: Display name for tab (e.g., 'File Summarizer')
        """
        ttk.Frame.__init__(self, parent, padding="10")
        self._init_tab(parent, tab_name)

    @abstractmethod
    def _setup_ui(self):
        """
        Setup tab UI components.
        Must be implemented by subclass.

        Example:
            def _setup_ui(self):
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
        """
        pass


class CTkBaseTab(TabMixin, ctk.CTkFrame, ABC):
    """
    Abstract base class for CustomTkinter-based application tabs.

    Behaves identically to BaseTab from a controller's point of view. The frame
    is transparent so it picks up the window background, and padding is applied
    by children via padx/pady (CTkFrame has no ``padding`` option).
    """

    def __init__(self, parent, tab_name: str):
        """
        Initialize CTk base tab.

        Args:
            parent: Parent widget (the notebook)
            tab_name: Display name for tab
        """
        ctk.CTkFrame.__init__(self, parent, fg_color="transparent")
        self._init_tab(parent, tab_name)

    @abstractmethod
    def _setup_ui(self):
        """Setup tab UI components. Must be implemented by subclass."""
        pass

    @abstractmethod
    def get_content(self) -> str:
        """Get current tab content. Must be implemented by subclass."""
        pass

    @abstractmethod
    def clear_all(self):
        """Clear all tab data. Must be implemented by subclass."""
        pass
