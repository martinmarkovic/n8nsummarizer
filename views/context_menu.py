"""
App-wide reusable right-click context menu for tkinter Text widgets.

This module provides a clean, reusable context menu system that can be used
by any tab in the application without duplicating boilerplate code.
"""

import tkinter as tk
from utils import tts_engine_pyttsx3


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

    def add_copy_command(self, label: str = "Copy"):
        """
        Add a 'Copy' command that copies the current selection to the clipboard,
        or the whole widget content if nothing is selected.

        Works for both tk.Text / ScrolledText and (ttk.)Entry widgets.
        """
        def copy_command():
            w = self.widget
            text = ""
            if isinstance(w, tk.Text):
                try:
                    if w.tag_ranges("sel"):
                        text = w.get("sel.first", "sel.last")
                    else:
                        text = w.get("1.0", tk.END)
                except tk.TclError:
                    text = ""
            else:  # (ttk.)Entry and similar
                try:
                    if w.selection_present():
                        text = w.selection_get()
                    else:
                        text = w.get()
                except (tk.TclError, AttributeError):
                    try:
                        text = w.get()
                    except Exception:
                        text = ""
            text = text.rstrip("\n") if text else ""
            if text:
                w.clipboard_clear()
                w.clipboard_append(text)
                w.update_idletasks()

        self._items.append({"type": "command", "label": label, "command": copy_command})

    def add_paste_command(self, label: str = "Paste"):
        """
        Add a 'Paste' command that inserts clipboard text at the cursor,
        replacing the current selection if one exists.

        Uses the widget's native <<Paste>> handling so it behaves correctly for
        both tk.Text / ScrolledText and (ttk.)Entry widgets. No-op on read-only
        or disabled widgets, or when the clipboard is empty.
        """
        def paste_command():
            w = self.widget
            # Skip if clipboard is empty / non-text
            try:
                if not w.clipboard_get():
                    return
            except tk.TclError:
                return
            # Don't try to paste into a disabled/read-only widget
            try:
                state = str(w.cget("state"))
                if state in ("disabled", "readonly"):
                    return
            except tk.TclError:
                pass
            w.focus_set()
            w.event_generate("<<Paste>>")

        self._items.append({"type": "command", "label": label, "command": paste_command})

    def add_tts_read_command(self, text_getter):
        """
        Add a TTS 'Read in Voice' command to the context menu.
        
        Args:
            text_getter: Callable that returns the text to speak (evaluated at click-time)
        """
        def read_command():
            text = text_getter()
            tts_engine_pyttsx3.speak(text)
        
        self._items.append({
            "type": "command",
            "label": "Read in Voice",
            "command": read_command
        })

    def add_tts_stop_command(self):
        """
        Add a TTS 'Stop Reading' command to the context menu.
        """
        self._items.append({
            "type": "command",
            "label": "Stop Reading",
            "command": tts_engine_pyttsx3.stop
        })

    def add_fullscreen_command(self, title="Fullscreen", editable=False, label="⛶ Fullscreen"):
        """
        Add a 'Fullscreen' command that opens this widget's content in a
        maximized, selectable window.

        Args:
            title: Title for the fullscreen window
            editable: If True, edits sync back to this widget on close
            label: Menu item label
        """
        def open_full():
            from views.fullscreen import open_fullscreen
            open_fullscreen(self.widget, title=title, editable=editable)

        self._items.append({
            "type": "command",
            "label": label,
            "command": open_full
        })

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
