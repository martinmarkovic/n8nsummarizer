"""
Reusable fullscreen viewer for tkinter Text widgets.

Provides a small "expand" (⛶) button that can be attached to any frame holding
a Text widget. Clicking it opens a maximized window showing the same content in
a large, selectable text area, with an X/Close button (and Escape to close).

The fullscreen view also carries the "Read in Voice"/"Stop Reading" context
menu, reading a selection when present, otherwise the whole text.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext

from utils import tts_engine_pyttsx3


def _selection_or_all(widget) -> str:
    """Return the current selection, or the full widget text if nothing selected."""
    try:
        if widget.tag_ranges("sel"):
            selected = widget.get("sel.first", "sel.last")
            if selected and selected.strip():
                return selected
    except tk.TclError:
        pass
    return widget.get("1.0", tk.END)


def _make_readonly_selectable(widget):
    """Keep a Text widget selectable/copyable but block edits."""
    def _block_edit(event):
        if event.state & 0x4:  # Ctrl held → allow copy / select-all
            return
        if event.keysym in (
            "Left", "Right", "Up", "Down", "Home", "End",
            "Prior", "Next", "Shift_L", "Shift_R", "Control_L", "Control_R",
        ):
            return
        return "break"
    widget.bind("<Key>", _block_edit)
    widget.bind("<<Paste>>", lambda e: "break")
    widget.bind("<<Cut>>", lambda e: "break")


def open_fullscreen(source_widget, title="Fullscreen", editable=False, font=None):
    """
    Open a maximized window displaying the content of `source_widget`.

    Args:
        source_widget: The Text/ScrolledText widget to mirror.
        title: Window title.
        editable: If True, edits in the fullscreen view are written back to the
            source widget on close. If False, the view is read-only (selectable).
        font: Optional font tuple for the fullscreen text area.
    """
    top = tk.Toplevel(source_widget.winfo_toplevel())
    top.title(title)
    top.geometry("1100x750")
    try:
        top.state("zoomed")  # Maximize on Windows
    except tk.TclError:
        pass
    top.transient(source_widget.winfo_toplevel())

    container = ttk.Frame(top, padding=8)
    container.pack(fill=tk.BOTH, expand=True)
    container.rowconfigure(1, weight=1)
    container.columnconfigure(0, weight=1)

    # Top bar with title + close button
    bar = ttk.Frame(container)
    bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    bar.columnconfigure(0, weight=1)
    ttk.Label(bar, text=title, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
    close_btn = ttk.Button(bar, text="✕ Close", width=10, command=lambda: _close())
    close_btn.grid(row=0, column=1, sticky="e")

    # Large text area
    text = scrolledtext.ScrolledText(
        container, wrap=tk.WORD, font=font or ("Segoe UI", 13)
    )
    text.grid(row=1, column=0, sticky="nsew")

    # Populate with the source content
    content = source_widget.get("1.0", tk.END)
    text.insert("1.0", content)

    # Inherit the source widget's colors so the fullscreen view matches the theme
    try:
        bg = source_widget.cget("bg")
        fg = source_widget.cget("fg")
        text.configure(bg=bg, fg=fg, insertbackground=fg)
        container.configure(style="TFrame")
    except tk.TclError:
        pass

    if not editable:
        _make_readonly_selectable(text)

    # TTS context menu (reads selection when present)
    from views.context_menu import AppContextMenu
    menu = AppContextMenu(text)
    menu.add_tts_read_command(lambda: _selection_or_all(text))
    menu.add_tts_stop_command()
    menu.bind()

    def _close():
        # Stop any narration started from the fullscreen view
        try:
            tts_engine_pyttsx3.stop()
        except Exception:
            pass
        if editable:
            new_content = text.get("1.0", tk.END)
            # Preserve source read-only behaviour: delete/insert works regardless of key bindings
            source_widget.delete("1.0", tk.END)
            source_widget.insert("1.0", new_content.rstrip("\n"))
        top.destroy()

    top.protocol("WM_DELETE_WINDOW", _close)
    top.bind("<Escape>", lambda e: _close())
    text.focus_set()
    return top


def attach_fullscreen_button(frame, text_widget, title="Fullscreen", editable=False, font=None):
    """
    Place a small expand (⛶) button in the top-right corner of `frame` that opens
    a fullscreen view of `text_widget`.

    Args:
        frame: The container (e.g. a LabelFrame) to overlay the button on.
        text_widget: The Text widget whose content is shown fullscreen.
        title: Fullscreen window title.
        editable: Whether edits sync back to the source widget on close.
        font: Optional font for the fullscreen text area.

    Returns:
        The created button.
    """
    btn = ttk.Button(
        frame,
        text="⛶",
        width=2,
        command=lambda: open_fullscreen(text_widget, title=title, editable=editable, font=font),
    )
    # Overlay in the top-right corner without disturbing existing layout
    btn.place(relx=1.0, x=-2, y=-2, anchor="ne")
    return btn
