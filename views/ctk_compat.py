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
from math import hypot

import customtkinter as ctk

from utils.logger import logger


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


# ---------------------------------------------------------------------------
# Gradient rendering
# ---------------------------------------------------------------------------

_GRADIENT_MODES = {
    "top_left", "top", "top_right",
    "left", "center", "right",
    "bottom_left", "bottom", "bottom_right",
}


def _parse_gradient_color(color: str):
    """Return a canonical #rrggbb colour, or None for invalid input."""
    value = (color or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(channel * 2 for channel in value)
    if len(value) != 6:
        return None
    try:
        int(value, 16)
    except ValueError:
        return None
    return f"#{value.lower()}"


def normalize_gradient_spec(start: str, end: str, mode: str = "bottom"):
    """Validate a user-selected two-colour directional gradient."""
    start, end = _parse_gradient_color(start), _parse_gradient_color(end)
    mode = (mode or "bottom").strip().lower()
    if not start or not end or mode not in _GRADIENT_MODES:
        return None
    return {"start": start, "end": end, "mode": mode}


def render_gradient_image(width: int, height: int, spec: dict):
    """Build a Pillow RGB image for a directional or centered radial gradient.

    ``spec['mode']`` identifies the point at which the end colour lands. The
    start colour begins at the opposite edge/corner. Thus ``top_left`` flows
    from bottom-right to top-left and ``bottom`` flows top-to-bottom. ``center``
    is radial: start at the center, end at the outer edge/corners.
    """
    try:
        from PIL import Image
    except ImportError:
        logger.debug("Pillow unavailable; gradient background disabled")
        return None

    valid = normalize_gradient_spec(
        spec.get("start", ""), spec.get("end", ""), spec.get("mode", "bottom")
    ) if isinstance(spec, dict) else None
    if not valid:
        return None

    def rgb(value):
        return tuple(int(value[index:index + 2], 16) for index in (1, 3, 5))

    start, end, mode = rgb(valid["start"]), rgb(valid["end"]), valid["mode"]
    # Calculate at a compact resolution then let Pillow scale it. This keeps
    # live window resizing smooth without producing visible banding.
    out_width, out_height = max(int(width), 1), max(int(height), 1)
    sample_width, sample_height = min(out_width, 256), min(out_height, 256)
    image = Image.new("RGB", (sample_width, sample_height))
    pixels = []

    if mode == "center":
        center_x, center_y = 0.5, 0.5
        max_distance = hypot(0.5, 0.5)
        for y in range(sample_height):
            py = y / max(sample_height - 1, 1)
            for x in range(sample_width):
                px = x / max(sample_width - 1, 1)
                ratio = min(1.0, hypot(px - center_x, py - center_y) / max_distance)
                pixels.append(tuple(
                    round(start[i] + (end[i] - start[i]) * ratio) for i in range(3)
                ))
    else:
        end_points = {
            "top_left": (0.0, 0.0), "top": (0.5, 0.0), "top_right": (1.0, 0.0),
            "left": (0.0, 0.5),                         "right": (1.0, 0.5),
            "bottom_left": (0.0, 1.0), "bottom": (0.5, 1.0), "bottom_right": (1.0, 1.0),
        }
        end_x, end_y = end_points[mode]
        start_x, start_y = 1.0 - end_x, 1.0 - end_y
        vector_x, vector_y = end_x - start_x, end_y - start_y
        length_squared = vector_x * vector_x + vector_y * vector_y
        for y in range(sample_height):
            py = y / max(sample_height - 1, 1)
            for x in range(sample_width):
                px = x / max(sample_width - 1, 1)
                ratio = ((px - start_x) * vector_x + (py - start_y) * vector_y) / length_squared
                ratio = max(0.0, min(1.0, ratio))
                pixels.append(tuple(
                    round(start[i] + (end[i] - start[i]) * ratio) for i in range(3)
                ))

    image.putdata(pixels)
    resampling = getattr(Image, "Resampling", Image)
    return image.resize((out_width, out_height), resampling.BILINEAR)


def render_gradient_photoimage(width: int, height: int, spec: dict):
    """Build a Tk-ready gradient image; the caller must retain the reference."""
    image = render_gradient_image(width, height, spec)
    if image is None:
        return None
    from PIL import ImageTk
    return ImageTk.PhotoImage(image)


class CTkGradientFrame(ctk.CTkFrame):
    """A solid CTk surface that can visibly render the selected gradient.

    CTk's ``transparent`` colour resolves to a flat inherited background, not
    alpha. This frame instead places a Pillow image above its own flat drawing
    canvas while its normal native child widgets stay on top. It also paints
    aligned crops into transparent CTk layout frames beneath it, avoiding the
    flat rectangles that would otherwise cover the image.
    """

    def __init__(self, master, *, flat_palette_key: str = "bg", **kwargs):
        kwargs.setdefault("corner_radius", 0)
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)
        self._flat_palette_key = flat_palette_key
        self._theme_skip = True
        self._gradient_spec = None
        self._gradient_rgb = None
        self._gradient_image = None
        self._gradient_size = None
        self._gradient_overlay_frames = []
        self.bind("<Configure>", self._on_gradient_resize, add="+")

    def _on_gradient_resize(self, _event=None):
        self.after_idle(self._render_gradient)

    def apply_palette(self, palette: dict):
        """Apply the fallback surface and render/clear the chrome gradient."""
        self._flat_color = palette[self._flat_palette_key]
        self._gradient_spec = palette.get("gradient")
        self.configure(fg_color=self._flat_color, bg_color=self._flat_color)
        if self._gradient_spec:
            self._render_gradient(force=True)
        else:
            self._clear_gradient()

    def _gradient_overlay_candidates(self, parent=None):
        parent = self if parent is None else parent
        if parent is self or (
            isinstance(parent, ctk.CTkFrame)
            and str(parent.cget("fg_color")) == "transparent"
        ):
            yield parent
        try:
            children = parent.winfo_children()
        except tk.TclError:
            return
        for child in children:
            # A solid child is deliberately a card/control surface. Its own
            # transparent descendants inherit that solid surface, not chrome.
            if isinstance(child, ctk.CTkFrame) and str(child.cget("fg_color")) != "transparent":
                continue
            yield from self._gradient_overlay_candidates(child)

    def _track_overlay_frame(self, frame):
        """Refresh the host once a transparent child receives its real size."""
        if getattr(frame, "_chrome_gradient_resize_owner", None) is self:
            return

        def refresh_after_layout(_event, owner=self):
            owner.after_idle(owner._render_gradient)

        frame.bind("<Configure>", refresh_after_layout, add="+")
        frame._chrome_gradient_resize_owner = self

    def _paint_overlay(self, frame):
        if self._gradient_rgb is None:
            return
        canvas = getattr(frame, "_canvas", None)
        if canvas is None:
            return
        try:
            width, height = canvas.winfo_width(), canvas.winfo_height()
            if width <= 1 or height <= 1:
                return
            offset_x = round(frame.winfo_rootx() - self.winfo_rootx())
            offset_y = round(frame.winfo_rooty() - self.winfo_rooty())
            image = self._gradient_rgb.crop(
                (offset_x, offset_y, offset_x + width, offset_y + height)
            )
            from PIL import ImageTk
            photo = ImageTk.PhotoImage(image)
            canvas.delete("chrome_gradient_backdrop")
            canvas.create_image(
                0, 0, anchor="nw", image=photo, tags="chrome_gradient_backdrop"
            )
            canvas.tag_raise("chrome_gradient_backdrop")
            frame._chrome_gradient_image = photo
        except (ImportError, tk.TclError):
            pass

    def _clear_gradient(self):
        for frame in self._gradient_overlay_frames:
            try:
                frame._canvas.delete("chrome_gradient_backdrop")
                frame._chrome_gradient_image = None
            except (AttributeError, tk.TclError):
                pass
        self._gradient_overlay_frames = []
        self._gradient_rgb = None
        self._gradient_image = None
        self._gradient_size = None

    def _render_gradient(self, force: bool = False):
        if not self._gradient_spec or not self.winfo_exists():
            return
        try:
            width, height = self._canvas.winfo_width(), self._canvas.winfo_height()
        except tk.TclError:
            return
        if width <= 1 or height <= 1:
            return
        key = (
            width, height, self._gradient_spec["start"],
            self._gradient_spec["end"], self._gradient_spec["mode"],
        )
        if force or key != self._gradient_size:
            image = render_gradient_image(width, height, self._gradient_spec)
            if image is None:
                self._clear_gradient()
                return
            self._gradient_rgb = image
            self._gradient_size = key

        self._gradient_overlay_frames = list(self._gradient_overlay_candidates())
        for frame in self._gradient_overlay_frames:
            self._track_overlay_frame(frame)
            self._paint_overlay(frame)


# ---------------------------------------------------------------------------
# Text widget helpers
# ---------------------------------------------------------------------------
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
            # Sized via set_title_font() with the heading size. Without this
            # flag the generic font pass would walk in afterwards and reset it
            # to the smaller body/label size.
            self._title_label._font_skip = True
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
        """
        Theme the card surface and its muted heading.

        A hairline border is applied as well as the fill: when the user picks a
        custom background close in tone to the card colour, fill alone leaves
        the sections invisible.
        """
        self.configure(
            fg_color=p["card"], border_width=1, border_color=p["border"]
        )
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
    # At this point the app's content has switched to its compact/responsive
    # layout. Keep the navigation equally compact instead of growing a second
    # row of tiny tab buttons.
    _COMPACT_BREAKPOINT = 980
    _MAX_VISIBLE_TABS = 3

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        # row 0 = tab strip, row 1 = active tab content
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # The strip is a rounded surface holding the tab "pills".
        # Marked self-styling: this widget and its pills are painted by
        # apply_palette(), so the generic theme walker must not touch them.
        # Square host: the visible gradient image is rectangular, while the
        # rounded tab pills remain solid controls above this background.
        self._tab_bar = CTkGradientFrame(
            self, flat_palette_key="subtle", corner_radius=0
        )
        self._tab_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._tab_bar.grid_columnconfigure(1, weight=1)
        self._tab_bar._theme_skip = True
        self._tab_bar._theme_skip_children = True

        # All pills belong to this viewport. In a wide window it spans the
        # whole strip; in compact mode it sits between previous/next buttons
        # and shows no more than three pills at a time.
        self._tab_viewport = ctk.CTkFrame(self._tab_bar, fg_color="transparent")
        self._tab_viewport.grid(row=0, column=0, columnspan=3, sticky="ew")
        for column in range(self._MAX_VISIBLE_TABS):
            self._tab_viewport.grid_columnconfigure(column, weight=1)
        self._previous_tab_button = ctk.CTkButton(
            self._tab_bar, text="‹", width=30, height=34, corner_radius=8,
            command=lambda: self._shift_tab_view(-1),
        )
        self._next_tab_button = ctk.CTkButton(
            self._tab_bar, text="›", width=30, height=34, corner_radius=8,
            command=lambda: self._shift_tab_view(1),
        )

        self._palette = None  # set by apply_palette()
        self._tab_font = ctk.CTkFont(size=13)
        self._tabs = []  # [{"widget":, "text":, "button":}]
        self._current_index = None
        self._tab_changed_callbacks = []
        self._reflow_columns = None  # last layout used, to avoid redundant work
        self._compact_tabs = False
        self._visible_tab_start = 0

        # Reflow the pills whenever the notebook is resized. A compact strip
        # replaces wrapping once the normal row would stop fitting.
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

    def _needs_compact_tabs(self, available: int) -> bool:
        """Whether the tab strip should use its three-pill pager."""
        if available < self._COMPACT_BREAKPOINT:
            return True
        try:
            required = sum(
                entry["button"].winfo_reqwidth() + self._TAB_GAP
                for entry in self._tabs
            )
        except tk.TclError:
            return False
        return required > available

    def _ensure_selected_visible(self, index: int) -> bool:
        """Move the compact viewport just enough to reveal *index*."""
        if not self._compact_tabs:
            return False
        last_start = max(0, len(self._tabs) - self._MAX_VISIBLE_TABS)
        start = self._visible_tab_start
        if index < start:
            start = index
        elif index >= start + self._MAX_VISIBLE_TABS:
            start = index - self._MAX_VISIBLE_TABS + 1
        start = max(0, min(start, last_start))
        changed = start != self._visible_tab_start
        self._visible_tab_start = start
        return changed

    def _shift_tab_view(self, direction: int):
        """Browse the compact tab pills without changing the active tab."""
        if not self._compact_tabs:
            return
        last_start = max(0, len(self._tabs) - self._MAX_VISIBLE_TABS)
        start = max(0, min(self._visible_tab_start + direction, last_start))
        if start != self._visible_tab_start:
            self._visible_tab_start = start
            self._render_tab_strip(force=True)

    def _style_navigation_buttons(self):
        """Keep pager arrows consistent with the user-selected palette."""
        p = self._palette
        updates = {
            "fg_color": "transparent",
            "hover_color": p["subtle_hover"] if p else ("gray82", "gray25"),
            "text_color": p["text"] if p else ("gray25", "gray85"),
        }
        for button in (self._previous_tab_button, self._next_tab_button):
            button.configure(**updates)

    def _render_tab_strip(self, force: bool = False):
        """Render either the normal row or compact three-pill pager."""
        if not self._tabs or not self.winfo_exists():
            return
        try:
            available = self._tab_bar.winfo_width()
        except tk.TclError:
            return
        if available <= 1:
            return

        compact = self._needs_compact_tabs(available)
        if compact != self._compact_tabs:
            self._compact_tabs = compact
            force = True
            # Entering compact mode should keep the active tab visible, but
            # subsequent arrow presses are allowed to browse elsewhere.
            if compact:
                self._ensure_selected_visible(self._current_index or 0)
        if not compact:
            self._visible_tab_start = 0

        if compact:
            visible = range(
                self._visible_tab_start,
                min(self._visible_tab_start + self._MAX_VISIBLE_TABS, len(self._tabs)),
            )
            layout = ("compact", self._visible_tab_start, len(self._tabs))
        else:
            visible = range(len(self._tabs))
            layout = ("wide", len(self._tabs))

        if not force and layout == self._reflow_columns:
            return
        self._reflow_columns = layout

        # Only compact mode uses equal-width viewport columns. In wide mode
        # every pill must retain its natural width and pack contiguously from
        # the left; leaving weights on the first three columns spreads them
        # across the strip and visually separates the tab sequence.
        for column in range(max(len(self._tabs), self._MAX_VISIBLE_TABS)):
            self._tab_viewport.grid_columnconfigure(
                column,
                weight=1 if compact and column < self._MAX_VISIBLE_TABS else 0,
            )

        # The viewport uses all three bar columns normally, or the centre
        # column in compact mode so the arrows flank the visible tab pills.
        self._tab_viewport.grid_configure(
            column=1 if compact else 0,
            columnspan=1 if compact else 3,
        )
        if compact:
            self._previous_tab_button.grid(row=0, column=0, padx=(self._TAB_GAP, 2), pady=0)
            self._next_tab_button.grid(row=0, column=2, padx=(2, self._TAB_GAP), pady=0)
            last_start = max(0, len(self._tabs) - self._MAX_VISIBLE_TABS)
            self._previous_tab_button.configure(
                state="normal" if self._visible_tab_start > 0 else "disabled"
            )
            self._next_tab_button.configure(
                state="normal" if self._visible_tab_start < last_start else "disabled"
            )
        else:
            self._previous_tab_button.grid_remove()
            self._next_tab_button.grid_remove()

        visible = set(visible)
        for i, entry in enumerate(self._tabs):
            if i in visible:
                entry["button"].grid(
                    row=0,
                    column=(i - self._visible_tab_start) if compact else i,
                    padx=(self._TAB_GAP, 0),
                    pady=0,
                    sticky="ew" if compact else "w",
                )
            else:
                entry["button"].grid_remove()

        self._style_navigation_buttons()
        self._refresh_tab_buttons()

    def _reflow_tabs(self):
        """Re-evaluate whether the strip needs its compact pager."""
        try:
            self._render_tab_strip()
        except tk.TclError:
            pass  # widget torn down mid-idle callback

    # -- ttk.Notebook API ---------------------------------------------------

    def add(self, child, text: str = "", **_ignored):
        """Append *child* as a new tab labelled *text*."""
        button = ctk.CTkButton(
            self._tab_viewport,
            text=text,
            corner_radius=8,
            height=34,
            width=self._fit_button_width(text),
            font=self._tab_font,
            command=lambda w=child: self.select(w),
        )
        self._tabs.append({"widget": child, "text": text, "button": button})
        self._reflow_columns = None  # force a re-layout on the next resize

        # First tab added becomes the visible one.
        if self._current_index is None:
            self.select(0)
        else:
            child.grid(row=1, column=0, sticky="nsew")
            child.grid_remove()
        self.after_idle(self._reflow_tabs)
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
            # A programmatic select (hotkey / cross-tab action) should reveal
            # an already-active tab if the user browsed its pill off-screen.
            if self._ensure_selected_visible(index):
                self._render_tab_strip(force=True)
            return self._tabs[index]["widget"]

        # Hide the outgoing tab
        if self._current_index is not None:
            self._tabs[self._current_index]["widget"].grid_remove()

        self._current_index = index
        entry = self._tabs[index]
        entry["widget"].grid(row=1, column=0, sticky="nsew")

        self._ensure_selected_visible(index)
        self._render_tab_strip()
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
        """Theme the pill bar, pager arrows, and tab pills from the palette."""
        self._palette = p
        self._tab_bar.apply_palette(p)
        self._style_navigation_buttons()
        self._refresh_tab_buttons()

    def _regrid_tab_buttons(self):
        """Re-render after tabs are removed without exposing hidden pills."""
        self._visible_tab_start = min(
            self._visible_tab_start,
            max(0, len(self._tabs) - self._MAX_VISIBLE_TABS),
        )
        self._reflow_columns = None
        self._render_tab_strip(force=True)

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
        # Sized via set_title_font() with the heading size; excluded from the
        # generic font pass so it is not reset to the body/label size.
        self._header._font_skip = True
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
        self.configure(
            fg_color=p["card"], border_width=1, border_color=p["border"]
        )
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


# ---------------------------------------------------------------------------
# Scroll-when-needed container
# ---------------------------------------------------------------------------

def _scrolls_itself(widget) -> bool:
    """
    True for widgets that own their vertical wheel behaviour.

    A transcript pane should scroll its own text when the pointer is over it,
    rather than scrolling the page out from under the user.
    """
    if not isinstance(widget, (tk.Text, tk.Listbox)):
        return False
    try:
        first, last = widget.yview()
    except Exception:
        return True
    # Only claim the wheel while there is actually something to scroll;
    # otherwise fall through so the page keeps moving.
    return (float(last) - float(first)) < 1.0


def _dispatch_wheel(event):
    """
    Route a wheel event to the nearest enclosing CTkAutoScrollFrame.

    This replaces per-container ``<Enter>``/``<Leave>`` binding, which looked
    scoped but did not work: Tk fires ``<Leave>`` on the container as soon as
    the pointer moves onto one of its own children, so hovering any card tore
    the binding down and only the bare canvas still scrolled.

    Walking up from ``event.widget`` means the wheel works over every
    descendant - labels, cards, buttons - without binding each one.
    """
    widget = getattr(event, "widget", None)
    if not isinstance(widget, tk.Misc):
        return

    if _scrolls_itself(widget):
        return

    node = widget
    while node is not None:
        if isinstance(node, CTkAutoScrollFrame):
            node.scroll_by_wheel(event)
            return
        node = getattr(node, "master", None)


def _install_wheel_dispatcher(widget):
    """
    Install the wheel dispatcher on this widget's toplevel, exactly once.

    The flag lives on the toplevel so repeated tab construction does not stack
    duplicate handlers (which would scroll several lines per notch).
    """
    try:
        root = widget.winfo_toplevel()
    except Exception:
        return
    if getattr(root, "_ctk_wheel_dispatcher", False):
        return
    root.bind_all("<MouseWheel>", _dispatch_wheel, add="+")
    root._ctk_wheel_dispatcher = True


class CTkAutoScrollFrame(ctk.CTkFrame):
    """
    A container that scrolls **only when its content does not fit**.

    ``CTkScrollableFrame`` always sizes its content to the natural height, which
    would break the tabs here: their transcript / response panes are meant to
    grow and fill a large window. Conversely a plain frame leaves controls
    unreachable once the window gets short - the action bar simply falls off
    the bottom.

    This widget gives both behaviours. The content is placed in a canvas
    window whose height is ``max(visible height, required height)``:

    - window taller than the content -> the content is stretched to fill, so
      ``grid_rowconfigure(weight=1)`` inside still expands as before,
    - window shorter than the content -> the window keeps the required height
      and the canvas scrolls, with the scrollbar appearing automatically.

    Add children to ``.inner``.
    """

    def __init__(self, master, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # A classic Canvas is required: CTk has no scrollable viewport
        # primitive that supports stretching its content window.
        #
        # NOTE the attribute name. CTkFrame keeps its own internal canvas in
        # ``self._canvas`` and overrides winfo_children() to filter that
        # attribute out of the child list. Naming this canvas ``_canvas`` would
        # shadow it, which both breaks the frame's own drawing and makes every
        # widget inside this container invisible to tree walks - the theme and
        # font passes silently stop at this frame.
        self._view = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self._view.grid(row=0, column=0, sticky="nsew")

        self._scrollbar = ctk.CTkScrollbar(self, command=self._view.yview)
        self._view.configure(yscrollcommand=self._on_scroll_set)
        self._scrollbar_visible = False

        self.inner = ctk.CTkFrame(self._view, fg_color="transparent")
        # apply_palette() assigns this canvas-hosted frame its explicit
        # backdrop colour. Exclude only the frame itself from generic CTkFrame
        # styling, otherwise that later pass replaces the backdrop with the
        # raised card fill and cards visually merge into their surrounding gap.
        # Its children still recurse and receive normal palette/font styling.
        self.inner._theme_skip = True
        self._window = self._view.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self.inner.grid_columnconfigure(0, weight=1)

        self._view.bind("<Configure>", self._on_configure)
        self.inner.bind("<Configure>", self._on_configure)

        self._sync_pending = False

        # Background state: a flat colour or a two-colour gradient spec.
        self._bg_color = None
        self._gradient = None          # {start, end, mode} or None
        self._gradient_rgb = None      # full content-sized Pillow image
        self._gradient_image = None    # canvas PhotoImage; kept alive for Tk
        self._gradient_item = None
        self._gradient_size = None
        self._gradient_overlay_frames = []

        _install_wheel_dispatcher(self)

    # -- geometry ----------------------------------------------------------

    def _on_configure(self, _event=None):
        """Coalesce the many Configure events a resize produces into one sync."""
        if self._sync_pending:
            return
        self._sync_pending = True
        self.after_idle(self._sync)

    def _sync(self):
        self._sync_pending = False
        try:
            width = self._view.winfo_width()
            height = self._view.winfo_height()
            if width <= 1 or height <= 1:
                return

            required = self.inner.winfo_reqheight()
            content_height = max(height, required)

            self._view.itemconfigure(
                self._window, width=width, height=content_height
            )
            self._view.configure(scrollregion=(0, 0, width, content_height))

            self._set_scrollbar_visible(required > height)
            if required <= height:
                # Nothing to scroll: make sure we are not left mid-scroll after
                # the window grows.
                self._view.yview_moveto(0)

            # Re-paint the backdrop to the new size.
            if self._gradient:
                self._render_gradient()
        except tk.TclError:
            pass  # widget torn down mid-callback

    def _set_scrollbar_visible(self, visible: bool):
        if visible == self._scrollbar_visible:
            return
        self._scrollbar_visible = visible
        if visible:
            self._scrollbar.grid(row=0, column=1, sticky="ns")
        else:
            self._scrollbar.grid_remove()

    def _on_scroll_set(self, first, last):
        self._scrollbar.set(first, last)

    # -- mouse wheel -------------------------------------------------------

    def can_scroll(self) -> bool:
        """True when there is more content than visible space."""
        return self._scrollbar_visible

    def scroll_by_wheel(self, event) -> None:
        """Scroll in response to a wheel event dispatched from anywhere inside."""
        if not self._scrollbar_visible:
            return
        delta = getattr(event, "delta", 0)
        if not delta:
            return
        self._view.yview_scroll(int(-1 * (delta / 120)), "units")

    # -- theming -----------------------------------------------------------

    def apply_palette(self, p: dict):
        """
        Match the canvas to the window background.

        The canvas is a classic Tk widget, so the CTk palette walker cannot
        colour it; left alone it shows up as a white rectangle.
        """
        self._bg_color = p["bg"]
        gradient = p.get("gradient")
        self._gradient = gradient if gradient else None

        try:
            self._view.configure(bg=self._bg_color)
            # ``inner`` is a CTkFrame embedded in a classic Tk Canvas.  CTk's
            # "transparent" mode copies its master's background *once* when
            # constructed; it does not track a later Canvas ``bg`` change.
            # The canvas therefore became dark while this frame kept the
            # default light colour, producing the white gutters visible around
            # and between cards. Give the content surface the explicit palette
            # colour so every exposed strip matches the tab background.
            self.inner.configure(
                # CTk draws a frame through its own internal canvas.  Both the
                # fill and backing colour must be set: `fg_color` alone leaves
                # that canvas at its original `systemButtonFace`, which can
                # still leak white around transparent child layout frames.
                fg_color=self._bg_color,
                bg_color=self._bg_color,
            )
        except tk.TclError:
            return

        if self._gradient:
            self._render_gradient(force=True)
        else:
            self._clear_gradient()

    # -- gradient backdrop -------------------------------------------------

    def _clear_gradient(self):
        if self._gradient_item is not None:
            try:
                self._view.delete(self._gradient_item)
            except tk.TclError:
                pass
        for frame in self._gradient_overlay_frames:
            try:
                frame._canvas.delete("gradient_backdrop")
                frame._gradient_overlay_image = None
            except (AttributeError, tk.TclError):
                pass
        self._gradient_overlay_frames = []
        self._gradient_item = None
        self._gradient_image = None
        self._gradient_rgb = None
        self._gradient_size = None

    def _gradient_overlay_candidates(self, parent=None):
        """Yield the page surface and transparent CTk layout frames below it."""
        parent = self.inner if parent is None else parent
        if parent is self.inner or (
            isinstance(parent, ctk.CTkFrame)
            and str(parent.cget("fg_color")) == "transparent"
        ):
            yield parent
        try:
            children = parent.winfo_children()
        except tk.TclError:
            return
        for child in children:
            yield from self._gradient_overlay_candidates(child)

    def _paint_gradient_overlay(self, frame):
        """Draw this frame's aligned crop over its CTk background drawing."""
        if self._gradient_rgb is None:
            return
        canvas = getattr(frame, "_canvas", None)
        if canvas is None:
            return
        try:
            width, height = canvas.winfo_width(), canvas.winfo_height()
            if width <= 1 or height <= 1:
                return
            origin_x = round(frame.winfo_rootx() - self.inner.winfo_rootx())
            origin_y = round(frame.winfo_rooty() - self.inner.winfo_rooty())
            crop = self._gradient_rgb.crop(
                (origin_x, origin_y, origin_x + width, origin_y + height)
            )
            from PIL import ImageTk
            image = ImageTk.PhotoImage(crop)
            canvas.delete("gradient_backdrop")
            canvas.create_image(
                0, 0, anchor="nw", image=image, tags="gradient_backdrop"
            )
            # The standard CTk fill is below this image; child controls are
            # independent native windows and remain above it.
            canvas.tag_raise("gradient_backdrop")
            frame._gradient_overlay_image = image
        except (ImportError, tk.TclError):
            pass

    def _refresh_gradient_overlays(self):
        """Overlay the gradient on every visible transparent page surface."""
        if self._gradient_rgb is None:
            return
        frames = list(self._gradient_overlay_candidates())
        self._gradient_overlay_frames = frames
        for frame in frames:
            self._paint_gradient_overlay(frame)

    def _render_gradient(self, force: bool = False):
        """Render the selected gradient for the scrollable content area."""
        if not self._gradient:
            return
        try:
            width = max(self._view.winfo_width(), 1)
            height = max(
                self._view.winfo_height(), self.inner.winfo_reqheight(), 1
            )
        except tk.TclError:
            return

        if width <= 1 or height <= 1:
            return
        gradient_key = (
            width, height, self._gradient["start"], self._gradient["end"],
            self._gradient["mode"],
        )
        if not force and gradient_key == self._gradient_size:
            self._refresh_gradient_overlays()
            return

        image = render_gradient_image(width, height, self._gradient)
        if image is None:
            # Pillow unavailable or invalid saved settings: flat fallback.
            self._clear_gradient()
            return

        self._gradient_rgb = image
        self._gradient_size = gradient_key
        from PIL import ImageTk
        self._gradient_image = ImageTk.PhotoImage(image)
        if self._gradient_item is None:
            self._gradient_item = self._view.create_image(
                0, 0, anchor="nw", image=self._gradient_image
            )
        else:
            self._view.itemconfigure(self._gradient_item, image=self._gradient_image)
        self._view.tag_lower(self._gradient_item)
        self._refresh_gradient_overlays()
