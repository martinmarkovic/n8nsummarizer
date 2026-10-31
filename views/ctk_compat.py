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

    def __init__(self, master, title: str = "", padding: int = 14, **kwargs):
        # Soft "card" look: rounded corners and a subtle surface fill that sits
        # just above the window background, with no hard 1px border. Visible
        # borders on every frame are what make a CTk layout read as dated.
        kwargs.setdefault("corner_radius", 10)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("fg_color", ("gray94", "gray17"))
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._title_label = None
        top_pad = padding
        if title:
            # Muted heading: reads as a section label instead of competing with
            # the window title.
            self._title_label = ctk.CTkLabel(
                self,
                text=title,
                anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=("gray35", "gray70"),
            )
            self._title_label.grid(
                row=0, column=0, sticky="ew", padx=padding, pady=(padding, 2)
            )
            top_pad = 6

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

    def apply_palette(self, p: dict):
        """Theme the card surface and its muted heading."""
        self.configure(fg_color=p["card"])
        if self._title_label is not None:
            # Marked self-styling so the generic walker does not turn this
            # muted heading into normal body text.
            self._title_label._theme_skip = True
            self._title_label.configure(
                text_color=p["text_dim"], fg_color="transparent"
            )


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

    # Horizontal gap between tab pills, in pixels.
    _TAB_GAP = 6

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        # row 0 = tab strip, row 1 = active tab content
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # The strip is a rounded surface holding the tab "pills".
        # Marked self-styling: this widget and its pills are painted by
        # apply_palette(), so the generic theme walker must not touch them.
        self._tab_bar = ctk.CTkFrame(
            self, corner_radius=10, fg_color=("gray90", "gray14")
        )
        self._tab_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._tab_bar._theme_skip = True
        self._tab_bar._theme_skip_children = True

        self._palette = None  # set by apply_palette()
        self._tab_font = ctk.CTkFont(size=13)
        self._tabs = []  # [{"widget":, "text":, "button":}]
        self._current_index = None
        self._tab_changed_callbacks = []
        self._reflow_columns = None  # last layout used, to avoid redundant work

        # Reflow the pills whenever the notebook is resized so they wrap onto
        # extra rows instead of overflowing off the right edge.
        self.bind("<Configure>", self._on_resize)

    # -- responsive tab strip ----------------------------------------------

    def _fit_button_width(self, text: str) -> int:
        """Width needed for a tab pill to show *text* without clipping."""
        try:
            return self._tab_font.measure(text) + 30
        except Exception:
            # measure() needs a live Tk font; fall back to a rough estimate.
            return max(90, len(text) * 9 + 30)

    def _on_resize(self, _event=None):
        # Defer to idle so winfo_width() reports the post-resize value.
        self.after_idle(self._reflow_tabs)

    def _reflow_tabs(self):
        """
        Lay the tab pills out in as many rows as the current width needs.

        Without this, seven tabs on a narrow window simply run off the edge -
        the classic fixed-layout failure. Buttons are re-gridded only when the
        wrap actually changes, so this is cheap to call on every resize.
        """
        if not self._tabs:
            return
        available = self.winfo_width()
        if available <= 1:
            return

        row = col = 0
        used = 0
        layout = []
        for entry in self._tabs:
            width = entry["button"].winfo_reqwidth() + self._TAB_GAP
            # Wrap, but never leave a row completely empty.
            if col > 0 and used + width > available:
                row += 1
                col = 0
                used = 0
            layout.append((row, col))
            used += width
            col += 1

        if layout == self._reflow_columns:
            return
        self._reflow_columns = layout

        for entry, (r, c) in zip(self._tabs, layout):
            entry["button"].grid_configure(row=r, column=c)

    # -- ttk.Notebook API ---------------------------------------------------

    def add(self, child, text: str = "", **_ignored):
        """Append *child* as a new tab labelled *text*."""
        button = ctk.CTkButton(
            self._tab_bar,
            text=text,
            corner_radius=8,
            height=34,
            width=self._fit_button_width(text),
            font=self._tab_font,
            command=lambda w=child: self.select(w),
        )
        button.grid(
            row=0,
            column=len(self._tabs),
            padx=(self._TAB_GAP, 0),
            pady=self._TAB_GAP,
            sticky="w",
        )

        self._tabs.append({"widget": child, "text": text, "button": button})
        self._reflow_columns = None  # force a re-layout on the next resize

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
            entry["button"].configure(
                text=options["text"],
                width=self._fit_button_width(options["text"]),
            )
            self._reflow_columns = None
            self.after_idle(self._reflow_tabs)
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
        """
        Highlight the active tab pill and keep the inactive ones flat.

        Colours come from the palette supplied by :meth:`apply_palette` so the
        strip follows the user's accent choice. The fallbacks below are only
        used before the first theme pass runs.
        """
        p = self._palette
        if p:
            active_fg = p["accent"]
            active_hover = p["accent_hover"]
            active_text = p["on_accent"]
            idle_hover = p["subtle_hover"]
            idle_text = p["text"]
        else:
            active_fg = ("#3a7ebf", "#1f6aa5")
            active_hover = ("#36719f", "#144870")
            active_text = "#ffffff"
            idle_hover = ("gray82", "gray25")
            idle_text = ("gray25", "gray85")

        for i, entry in enumerate(self._tabs):
            if i == self._current_index:
                entry["button"].configure(
                    fg_color=active_fg,
                    hover_color=active_hover,
                    text_color=active_text,
                )
            else:
                # Flat until hovered - keeps the strip calm instead of a wall
                # of identical buttons.
                entry["button"].configure(
                    fg_color="transparent",
                    hover_color=idle_hover,
                    text_color=idle_text,
                )

    def apply_palette(self, p: dict):
        """Theme the pill bar and re-paint the pills from the palette."""
        self._palette = p
        self._tab_bar.configure(fg_color=p["subtle"])
        self._refresh_tab_buttons()

    def _regrid_tab_buttons(self):
        for i, entry in enumerate(self._tabs):
            entry["button"].grid_configure(column=i)
        self._refresh_tab_buttons()

    def set_tab_font(self, font):
        """
        Apply *font* to every tab pill (app-wide font size control).

        Pill widths are measured from the font, so they are recomputed here and
        the strip is re-laid-out: a larger font may need fewer tabs per row.
        """
        self._tab_font = font
        for entry in self._tabs:
            entry["button"].configure(
                font=font, width=self._fit_button_width(entry["text"])
            )
        self._reflow_columns = None
        self.after_idle(self._reflow_tabs)


# ---------------------------------------------------------------------------
# Collapsible section
# ---------------------------------------------------------------------------

class CTkCollapsibleSection(ctk.CTkFrame):
    """
    A :class:`CTkSection` whose body can be folded away by clicking the header.

    Useful for configuration panels that are needed occasionally but otherwise
    steal vertical space from the content the user actually works in. Children
    go into ``.body``, same as :class:`CTkSection`.
    """

    def __init__(
        self,
        master,
        title: str = "",
        padding: int = 14,
        expanded: bool = True,
        on_toggle=None,
        **kwargs,
    ):
        kwargs.setdefault("corner_radius", 10)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("fg_color", ("gray94", "gray17"))
        super().__init__(master, **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._padding = padding
        self._expanded = bool(expanded)
        self._on_toggle = on_toggle
        self._title = title

        # Header doubles as the toggle. A flat, full-width button keeps the
        # whole strip clickable without looking like a form control.
        self._header = ctk.CTkButton(
            self,
            text=self._header_text(),
            anchor="w",
            height=28,
            corner_radius=8,
            fg_color="transparent",
            hover_color=("gray88", "gray23"),
            text_color=("gray35", "gray70"),
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.toggle,
        )
        self._header.grid(row=0, column=0, sticky="ew", padx=padding - 6,
                          pady=(padding - 4, 2))

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid_columnconfigure(0, weight=1)
        if self._expanded:
            self._grid_body()

    def _header_text(self) -> str:
        chevron = "\u25be" if self._expanded else "\u25b8"  # ▾ / ▸
        return f"{chevron}  {self._title}"

    def _grid_body(self):
        self.body.grid(
            row=1, column=0, sticky="nsew",
            padx=self._padding, pady=(4, self._padding),
        )

    def toggle(self):
        """Fold or unfold the body."""
        self.set_expanded(not self._expanded)

    def set_expanded(self, expanded: bool):
        """Explicitly fold (False) or unfold (True) the body."""
        expanded = bool(expanded)
        if expanded == self._expanded:
            return
        self._expanded = expanded
        if expanded:
            self._grid_body()
        else:
            self.body.grid_remove()
        self._header.configure(text=self._header_text())
        if callable(self._on_toggle):
            self._on_toggle(expanded)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_title(self, title: str):
        """Update the section heading (used when re-applying translations)."""
        self._title = title
        self._header.configure(text=self._header_text())

    def set_title_font(self, font):
        """Keep the heading in sync with the app-wide font size."""
        self._header.configure(font=font)

    def apply_palette(self, p: dict):
        """Theme the card surface and keep the header flat and muted."""
        self.configure(fg_color=p["card"])
        # Self-styling: the generic walker would otherwise fill this header
        # with the accent colour like any other button.
        self._header._theme_skip = True
        self._header.configure(
            fg_color="transparent",
            hover_color=p["subtle_hover"],
            text_color=p["text_dim"],
        )


# ---------------------------------------------------------------------------
# Draggable splitter
# ---------------------------------------------------------------------------

class CTkSplitter(ctk.CTkFrame):
    """
    Two side-by-side panes with a draggable divider.

    Replaces a hard-coded 50/50 grid so the user can decide how much room the
    left and right panes get. Add content to ``.left`` and ``.right``.

    The split is stored as a ratio and applied through grid column weights
    (scaled to integers), which keeps the panes proportional when the window
    itself is resized.
    """

    _SCALE = 1000
    _GRIP_WIDTH = 8

    def __init__(self, master, ratio: float = 0.5, min_ratio: float = 0.15, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        self._ratio = ratio
        self._min_ratio = min_ratio

        self.grid_rowconfigure(0, weight=1)

        self.left = ctk.CTkFrame(self, fg_color="transparent")
        self.left.grid(row=0, column=0, sticky="nsew")

        # The grip is deliberately subtle: a rounded bar that brightens on
        # hover, rather than a 3D ridge.
        self._grip = ctk.CTkFrame(
            self,
            width=self._GRIP_WIDTH,
            corner_radius=4,
            fg_color=("gray85", "gray25"),
        )
        self._grip.grid(row=0, column=1, sticky="ns", padx=3, pady=18)
        self._grip.grid_propagate(False)

        self.right = ctk.CTkFrame(self, fg_color="transparent")
        self.right.grid(row=0, column=2, sticky="nsew")

        # Hover colours; replaced by apply_palette() once a theme is applied.
        self._idle_color = ("gray85", "gray25")
        self._hover_color = ("gray70", "gray38")

        self._apply_ratio()
        self._bind_grip()

    def _bind_grip(self):
        for target in (self._grip, getattr(self._grip, "_canvas", None)):
            if target is None:
                continue
            try:
                target.configure(cursor="sb_h_double_arrow")
            except Exception:
                pass
            target.bind("<B1-Motion>", self._on_drag)
            target.bind("<Enter>", lambda _e: self._grip.configure(
                fg_color=self._hover_color))
            target.bind("<Leave>", lambda _e: self._grip.configure(
                fg_color=self._idle_color))

    def _on_drag(self, event):
        total = self.winfo_width()
        if total <= 1:
            return
        # event.x is relative to the grip, so add its offset within the frame.
        x = self._grip.winfo_x() + event.x
        ratio = x / total
        self.set_ratio(ratio)

    def _apply_ratio(self):
        left = max(1, int(self._ratio * self._SCALE))
        right = max(1, self._SCALE - left)
        self.grid_columnconfigure(0, weight=left)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=right)

    def set_ratio(self, ratio: float):
        """Set the split position, clamped to the configured minimum."""
        ratio = max(self._min_ratio, min(1.0 - self._min_ratio, float(ratio)))
        if abs(ratio - self._ratio) < 0.002:
            return
        self._ratio = ratio
        self._apply_ratio()

    def get_ratio(self) -> float:
        return self._ratio

    def apply_palette(self, p: dict):
        """Theme the drag grip and remember the colours for hover states."""
        self._idle_color = p["subtle_hover"]
        self._hover_color = p["accent"]
        # Self-styling: the grip is a filled frame, so the generic walker
        # would repaint it as a card surface and it would vanish.
        self._grip._theme_skip = True
        self._grip._theme_skip_children = True
        self._grip.configure(fg_color=self._idle_color)
