"""
App-wide reusable right-click context menu for tkinter Text widgets.

This module provides a clean, reusable context menu system that can be used
by any tab in the application without duplicating boilerplate code.
"""

import tkinter as tk


class AppContextMenu:
    """
    Reusable right-click context menu for tkinter Text widgets.

    Usage:
        menu = AppContextMenu(widget)
        menu.add_command("Export as .txt", callback_fn)
        menu.add_separator()
        menu.add_command("Copy all", callback_fn)
        menu.bind()  # attaches <Button-3> to widget
    """

    def __init__(self, widget: tk.Text):
        """
        Initialize context menu for a Text widget.

        Args:
            widget: The tk.Text widget to attach the menu to
        """
        self.widget = widget
        self._menu = tk.Menu(widget, tearoff=0)
        self._items = []  # List of item definitions

    def add_command(self, label: str, command):
        """
        Add a command item to the context menu.

        Args:
            label: Display text for the menu item
            command: Callable to execute when item is clicked
        """
        self._items.append({"type": "command", "label": label, "command": command})

    def add_separator(self):
        """Add a separator line to the context menu."""
        self._items.append({"type": "separator"})

    def bind(self):
        """Build the menu and bind it to the widget's right-click event."""
        self._build_menu()
        self.widget.bind("<Button-3>", self._show)

    def _build_menu(self):
        """Build the tk.Menu from internal item definitions."""
        # Clear existing menu
        self._menu.delete(0, tk.END)

        # Add items from definitions
        for item in self._items:
            if item["type"] == "command":
                self._menu.add_command(label=item["label"], command=item["command"])
            elif item["type"] == "separator":
                self._menu.add_separator()

    def _show(self, event):
        """
        Show the context menu at the mouse position.

        Args:
            event: Tkinter event containing mouse coordinates
        """
        # Focus the widget to ensure proper event handling
        self.widget.focus_set()

        # Show menu at mouse position
        self._menu.post(event.x_root, event.y_root)

    def rebuild(self):
        """
        Clear and rebuild menu from internal definitions.

        Useful if items change after initial bind.
        """
        self._build_menu()
