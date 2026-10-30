"""
CustomTkinter compatibility helpers for the incremental ttk -> CTk migration.

The app is being moved from ttk to CustomTkinter one tab at a time. During the
transition the CTk shell has to host both migrated (CTk) and un-migrated (ttk)
tabs, so this module provides the glue:

- ``unwrap_text``  — CTkTextbox stores a real ``tk.Text`` internally. Helpers
  that expect a classic Text widget (context menus, the fullscreen viewer,
  ``cget("bg")``) must operate on that inner widget, because CTkTextbox itself
  raises ``ValueError`` for classic options like ``bg`` / ``fg`` / ``state``.

- ``CTkNotebook`` — a tab container that mimics the slice of the
  ``ttk.Notebook`` API the app actually uses (``add``, ``select``, ``index``,
  ``tabs``, ``tab``, ``forget`` and the ``<<NotebookTabChanged>>`` binding), so
  existing call sites such as ``notebook.select(translation_tab)`` and the
  tab-index persistence in MainWindow keep working untouched.

- ``CTkSection`` — CustomTkinter has no ``LabelFrame`` equivalent, so this is a
  titled, bordered frame. Children go into ``section.body``.

Created during the v10 UI migration.
"""

import tkinter as tk

import customtkinter as ctk


# ---------------------------------------------------------------------------
# Text widget helpers
# ---------------------------------------------------------------------------

def unwrap_text(widget):
    """
    Return the underlying ``tk.Text`` for a CTkTextbox, or *widget* unchanged.

    CTkTextbox is a CTkFrame wrapping a real ``tk.Text`` (``_textbox``). Code
    written against classic Tk (``isinstance(w, tk.Text)``, ``w.cget("bg")``,
    ``w.cget("state")``) breaks on the wrapper but works fine on the inner
    widget, so call this before handing a textbox to such helpers.
    """
    inner = getattr(widget, "_textbox", None)
    if isinstance(inner, tk.Text):
        return inner
    return widget


def unwrap_input(widget):
    """
    Return the classic Tk widget behind a CustomTkinter input widget.

    Handles CTkTextbox (wraps ``tk.Text``) and CTkEntry (wraps ``tk.Entry``),
    and returns anything else unchanged. Use this for generic helpers that need
    classic Tk behaviour such as ``selection_present()``, ``cget("state")`` or
    ``<<Paste>>`` event generation.
    """
    textbox = getattr(widget, "_textbox", None)
    if isinstance(textbox, tk.Text):
        return textbox
    entry = getattr(widget, "_entry", None)
    if isinstance(entry, tk.Entry):
        return entry
    return widget


def is_ctk_widget(widget) -> bool:
    """True if *widget* is managed by CustomTkinter (so it themes itself)."""
    return isinstance(widget, ctk.CTkBaseClass)


def owned_by_ctk(widget) -> bool:
    """
    True if *widget* is a classic Tk widget that belongs to a CTk widget.

    MainWindow recursively recolors every ``tk.Text`` it can find so that dark
    mode works for ttk tabs. The ``tk.Text`` inside a CTkTextbox must be left
    alone or that manual recoloring fights CustomTkinter's own theming.
    """
    parent = getattr(widget, "master", None)
    while parent is not None:
        if is_ctk_widget(parent):
            return True
        parent = getattr(parent, "master", None)
    return False


# ---------------------------------------------------------------------------
# Titled section (replacement for ttk.LabelFrame)
# ---------------------------------------------------------------------------

class CTkSection(ctk.CTkFrame):
    """
    A titled, bordered container standing in for ``ttk.LabelFrame``.

    Add children to ``.body``, not to the section itself::

        sec = CTkSection(parent, title="Input")
        sec.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(sec.body, text="File:").grid(row=0, column=0)
    """

    def __init__(self, master, title: str = "", padding: int = 10, **kwargs):
        kwargs.setdefault("corner_radius", 8)
        kwargs.setdefault("border_width", 1)
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._title_label = None
        top_pad = padding
        if title:
            self._title_label = ctk.CTkLabel(
                self,
                text=title,
                anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            self._title_label.grid(
                row=0, column=0, sticky="ew", padx=padding, pady=(padding, 0)
            )
            top_pad = 4

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(
            row=1, column=0, sticky="nsew", padx=padding, pady=(top_pad, padding)
        )
        self.body.grid_columnconfigure(0, weight=1)

    def set_title(self, title: str):
        """Update the section heading (used when re-applying translations)."""
        if self._title_label is not None:
            self._title_label.configure(text=title)

    def set_title_font(self, font):
        """Keep the heading in sync with the app-wide font size."""
        if self._title_label is not None:
            self._title_label.configure(font=font)


# ---------------------------------------------------------------------------
# Notebook replacement
# ---------------------------------------------------------------------------

class CTkNotebook(ctk.CTkFrame):
    """
    A CustomTkinter tab container that speaks enough ``ttk.Notebook`` to be a
    drop-in for this app.

    Tabs are children of the notebook itself (same as ``ttk.Notebook``), so
    ``SummarizerTab(self.notebook)`` keeps working. Only one child is gridded
    at a time; the rest are ``grid_remove()``d.

    Supported ttk.Notebook surface:
        add(child, text=...)          select(widget | index | name | None)
        index("end" | widget | name)  tabs()
        tab(widget, text=...)         forget(widget | index)
        bind("<<NotebookTabChanged>>", cb)

    ``select()`` with no argument returns the *widget* (ttk returns a widget
    name string). That is fine here because this class's ``index()`` accepts
    widgets, and every call site pairs the two: ``index(select())``.
    """

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        # row 0 = tab strip, row 1 = active tab content
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        self._tab_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self._tabs = []  # [{"widget":, "text":, "button":}]
        self._current_index = None
        self._tab_changed_callbacks = []

    # -- ttk.Notebook API ---------------------------------------------------

    def add(self, child, text: str = "", **_ignored):
        """Append *child* as a new tab labelled *text*."""
        button = ctk.CTkButton(
            self._tab_bar,
            text=text,
            corner_radius=6,
            height=32,
            command=lambda w=child: self.select(w),
        )
        button.grid(row=0, column=len(self._tabs), padx=(0, 4), sticky="w")

        self._tabs.append({"widget": child, "text": text, "button": button})

        # First tab added becomes the visible one.
        if self._current_index is None:
            self.select(0)
        else:
            child.grid(row=1, column=0, sticky="nsew")
            child.grid_remove()
        return child

    def select(self, tab_id=None):
        """
        Select a tab, or return the currently selected tab widget.

        *tab_id* may be a child widget, an integer index, or a Tk widget name.
        """
        if tab_id is None:
            if self._current_index is None:
                return None
            return self._tabs[self._current_index]["widget"]

        index = self.index(tab_id)
        if index is None or not (0 <= index < len(self._tabs)):
            return None
        if index == self._current_index:
            return self._tabs[index]["widget"]

        # Hide the outgoing tab
        if self._current_index is not None:
            self._tabs[self._current_index]["widget"].grid_remove()

        self._current_index = index
        entry = self._tabs[index]
        entry["widget"].grid(row=1, column=0, sticky="nsew")

        self._refresh_tab_buttons()
        self._fire_tab_changed()
        return entry["widget"]

    def index(self, tab_id):
        """Resolve *tab_id* to an integer index. ``"end"`` gives the tab count."""
        if tab_id == "end":
            return len(self._tabs)
        if isinstance(tab_id, int):
            return tab_id
        # Widget instance
        for i, entry in enumerate(self._tabs):
            if entry["widget"] is tab_id:
                return i
        # Tk widget pathname (what ttk.Notebook.select() would have returned)
        name = str(tab_id)
        for i, entry in enumerate(self._tabs):
            if str(entry["widget"]) == name:
                return i
        return None

    def tabs(self):
        """Tuple of tab widget names, mirroring ``ttk.Notebook.tabs()``."""
        return tuple(str(entry["widget"]) for entry in self._tabs)

    def tab(self, tab_id, **options):
        """Get or set per-tab options. Only ``text`` is supported."""
        index = self.index(tab_id)
        if index is None or not (0 <= index < len(self._tabs)):
            return None
        entry = self._tabs[index]
        if not options:
            return {"text": entry["text"]}
        if "text" in options:
            entry["text"] = options["text"]
            entry["button"].configure(text=options["text"])
        return None

    def forget(self, tab_id):
        """Remove a tab from the notebook (widget itself is not destroyed)."""
        index = self.index(tab_id)
        if index is None or not (0 <= index < len(self._tabs)):
            return
        entry = self._tabs.pop(index)
        entry["button"].destroy()
        entry["widget"].grid_remove()

        if self._current_index is not None:
            if self._current_index == index:
                self._current_index = None
                if self._tabs:
                    self.select(min(index, len(self._tabs) - 1))
            elif self._current_index > index:
                self._current_index -= 1
        self._regrid_tab_buttons()

    def bind(self, sequence=None, command=None, add=True):
        """
        Intercept ``<<NotebookTabChanged>>`` and forward everything else.

        CTk widgets forward ``bind`` to an internal canvas, so a virtual event
        generated on this frame would never reach the handler. Registering the
        callback directly keeps MainWindow's existing bind call working.
        """
        if sequence == "<<NotebookTabChanged>>":
            if callable(command):
                self._tab_changed_callbacks.append(command)
            return None
        return super().bind(sequence, command, add)

    # -- internals ----------------------------------------------------------

    def _fire_tab_changed(self):
        for callback in list(self._tab_changed_callbacks):
            try:
                callback(None)
            except TypeError:
                # Allow handlers that take no event argument
                callback()
            except Exception:
                from utils.logger import logger
                logger.error("Error in <<NotebookTabChanged>> handler", exc_info=True)

    def _refresh_tab_buttons(self):
        """Highlight the active tab button and mute the inactive ones."""
        for i, entry in enumerate(self._tabs):
            active = i == self._current_index
            if active:
                entry["button"].configure(
                    fg_color=("#3a7ebf", "#1f6aa5"),
                    text_color=("#ffffff", "#ffffff"),
                )
            else:
                entry["button"].configure(
                    fg_color="transparent",
                    text_color=("gray20", "gray80"),
                )

    def _regrid_tab_buttons(self):
        for i, entry in enumerate(self._tabs):
            entry["button"].grid_configure(column=i)
        self._refresh_tab_buttons()

    def set_tab_font(self, font):
        """Apply *font* to every tab button (app-wide font size control)."""
        for entry in self._tabs:
            entry["button"].configure(font=font)
