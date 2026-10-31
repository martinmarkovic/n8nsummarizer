"""
CustomTkinter theming bridge.

CustomTkinter widgets do not read from ``ttk.Style``, so the app's theme
settings (Settings -> Appearance: background / text / accent) never reached
them: CTk widgets kept their built-in blue regardless of what the user chose.
This module closes that gap.

Two pieces:

``build_palette(theme_colors)``
    Expands the app's small theme dict (``bg_primary``, ``text_primary``,
    ``accent``, ...) into every colour the CTk widgets need, deriving hover
    states and - importantly - a text colour that stays readable on top of
    whatever accent the user picked.

``apply_palette(widget, palette)``
    Walks a widget tree and restyles each CTk widget for its type.

Opting out
----------
Some widgets style themselves (the notebook's tab pills, the splitter grip,
a section header, a semantic status dot). They set one of two markers:

``_theme_skip``
    Do not restyle this widget; it manages its own colours.
``_theme_skip_children``
    Do not descend into this widget's children.

Any widget exposing ``apply_palette(palette)`` gets called so it can theme its
own internals.
"""

import tkinter as tk

import customtkinter as ctk

from utils.logger import logger


# ---------------------------------------------------------------------------
# Colour maths
# ---------------------------------------------------------------------------

def _parse_hex(color: str):
    """Return (r, g, b) for a #rgb / #rrggbb string, or None if unparseable."""
    if not isinstance(color, str):
        return None
    value = color.strip()
    if not value.startswith("#"):
        return None
    value = value[1:]
    try:
        if len(value) == 3:
            return tuple(int(c * 2, 16) for c in value)
        if len(value) == 6:
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None
    return None


def _to_hex(rgb) -> str:
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _mix(color: str, other: str, amount: float) -> str:
    """Blend *color* toward *other* by *amount* (0..1)."""
    a, b = _parse_hex(color), _parse_hex(other)
    if not a or not b:
        return color
    return _to_hex(a[i] + (b[i] - a[i]) * amount for i in range(3))


def _lighten(color: str, amount: float) -> str:
    return _mix(color, "#ffffff", amount)


def _darken(color: str, amount: float) -> str:
    return _mix(color, "#000000", amount)


def relative_luminance(color: str) -> float:
    """Perceived brightness of *color* in 0..1 (0.5 is the usual mid-point)."""
    rgb = _parse_hex(color)
    if not rgb:
        return 0.5
    r, g, b = (c / 255.0 for c in rgb)
    # Rec. 709 luma - good enough for picking readable text.
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_text(background: str) -> str:
    """
    Pick black or white text so it stays readable on *background*.

    Without this, a user-chosen light accent (yellow, pale green) would get
    white text and become unreadable.
    """
    return "#111111" if relative_luminance(background) > 0.55 else "#ffffff"


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

def build_palette(theme_colors: dict, is_dark: bool = None,
                  gradient: tuple = None) -> dict:
    """
    Expand the app theme dict into the full set of colours CTk widgets need.

    Args:
        theme_colors: the app's active palette (``MainWindow.theme_colors``),
            already merged with any custom colours from Settings.
        is_dark: force dark/light derivation. Defaults to inferring it from the
            background brightness, which also does the right thing when the
            user picks a dark custom background in light mode.
        gradient: optional ``(start, end)`` pair for a two-stop background
            gradient. Stored on the palette for the containers that can paint
            it; the rest of the palette is still derived from the flat
            background so text contrast stays predictable.
    """
    bg = theme_colors.get("bg_primary", "#f7f9fb")
    surface = theme_colors.get("bg_secondary", bg)
    text = theme_colors.get("text_primary", "#1f2329")
    # Muted text sits closer to the body colour than it used to; at 0.45 the
    # small field labels washed out enough to read as "too small".
    text_dim = theme_colors.get("text_secondary", _mix(text, bg, 0.3))
    accent = theme_colors.get("accent", "#3a7ebf")
    border = theme_colors.get("border", _mix(bg, text, 0.2))

    if is_dark is None:
        is_dark = relative_luminance(bg) < 0.5

    # A very dark or very light accent gives no room for a hover state in one
    # direction, so pick the direction with headroom.
    accent_lum = relative_luminance(accent)
    if accent_lum < 0.15:
        accent_hover = _lighten(accent, 0.25)
    elif accent_lum > 0.85:
        accent_hover = _darken(accent, 0.15)
    else:
        accent_hover = _darken(accent, 0.12) if not is_dark else _lighten(accent, 0.12)

    # Raised surfaces (cards) must read as clearly distinct from the window.
    #
    # Cards are *lighter* than the window, which is what makes them look
    # raised. A previous version darkened them by 3% in light mode, which on a
    # near-white background made every card blend into one flat sheet.
    if is_dark:
        card = _lighten(bg, 0.08)
        subtle = _lighten(bg, 0.14)
        subtle_hover = _lighten(bg, 0.20)
        field = _lighten(bg, 0.04)
    else:
        # On a light background push cards toward white; if the background is
        # already white there is no headroom, so step the card down instead so
        # the two never collapse into the same colour.
        if relative_luminance(bg) > 0.93:
            card = _darken(bg, 0.045)
            subtle = _darken(bg, 0.10)
            subtle_hover = _darken(bg, 0.16)
            field = "#ffffff"
        else:
            card = _lighten(bg, 0.55)
            subtle = _lighten(bg, 0.35)
            subtle_hover = _lighten(bg, 0.25)
            field = _lighten(bg, 0.72)

    return {
        "is_dark": is_dark,
        "gradient": gradient,
        "bg": bg,
        "card": card,
        "surface": surface,
        "subtle": subtle,
        "subtle_hover": subtle_hover,
        "field": field,
        "text": text,
        "text_dim": text_dim,
        "accent": accent,
        "accent_hover": accent_hover,
        "on_accent": contrast_text(accent),
        "border": border,
    }


# ---------------------------------------------------------------------------
# Applying the palette
# ---------------------------------------------------------------------------

def _is_transparent(widget, option: str = "fg_color") -> bool:
    """True if *widget*'s colour option is intentionally transparent."""
    try:
        return str(widget.cget(option)) == "transparent"
    except Exception:
        return False


def _style_button(widget, p):
    """
    Style a button, preserving the primary / secondary distinction.

    A transparent button is an outlined "secondary" action in this app, so it
    keeps its transparency and only gets readable text, border and hover.
    """
    if _is_transparent(widget):
        updates = {
            "text_color": p["text"],
            "hover_color": p["subtle_hover"],
        }
        try:
            if float(widget.cget("border_width")) > 0:
                updates["border_color"] = p["border"]
        except Exception:
            pass
        widget.configure(**updates)
    else:
        widget.configure(
            fg_color=p["accent"],
            hover_color=p["accent_hover"],
            text_color=p["on_accent"],
        )


def _style_widget(widget, p):
    """Apply the palette to a single CTk widget based on its type."""
    # Order matters: check the more specific classes first, because several CTk
    # widgets subclass CTkFrame.
    if isinstance(widget, ctk.CTkButton):
        _style_button(widget, p)

    elif isinstance(widget, ctk.CTkSegmentedButton):
        # CTk has no per-state text colour here: one text_color covers both the
        # selected and unselected segments. So if the accent would swallow the
        # text, use an accent *tint* for the selection instead of the full
        # accent - selection stays obvious and the label stays readable.
        selected = p["accent"]
        if abs(relative_luminance(selected) - relative_luminance(p["text"])) < 0.35:
            selected = _mix(p["accent"], p["bg"], 0.6)
        widget.configure(
            fg_color=p["subtle"],
            selected_color=selected,
            selected_hover_color=_darken(selected, 0.08),
            unselected_color=p["subtle"],
            unselected_hover_color=p["subtle_hover"],
            text_color=p["text"],
        )

    elif isinstance(widget, ctk.CTkOptionMenu):
        widget.configure(
            fg_color=p["accent"],
            button_color=_darken(p["accent"], 0.12),
            button_hover_color=p["accent_hover"],
            text_color=p["on_accent"],
            dropdown_fg_color=p["field"],
            dropdown_text_color=p["text"],
            dropdown_hover_color=p["subtle_hover"],
        )

    elif isinstance(widget, ctk.CTkComboBox):
        widget.configure(
            fg_color=p["field"],
            border_color=p["border"],
            button_color=p["accent"],
            button_hover_color=p["accent_hover"],
            text_color=p["text"],
        )

    elif isinstance(widget, ctk.CTkEntry):
        updates = {
            "fg_color": p["field"],
            "border_color": p["border"],
            "text_color": p["text"],
            "placeholder_text_color": p["text_dim"],
        }
        # Entries that sit inside a grouped control (the font stepper, the
        # numeric steppers) are deliberately seamless; a border would carve
        # them out of the group.
        if not getattr(widget, "_borderless", False):
            updates["border_width"] = 1
        widget.configure(**updates)

    elif isinstance(widget, ctk.CTkTextbox):
        # A visible edge matters here: on a light theme both the card and the
        # field are near-white, so without a border the text area reads as a
        # stray white rectangle rather than an input.
        widget.configure(
            fg_color=p["field"],
            border_width=1,
            border_color=p["border"],
            text_color=p["text"],
            scrollbar_button_color=p["subtle_hover"],
            scrollbar_button_hover_color=p["border"],
        )
        # The caret lives on the inner tk.Text and CTk does not expose it.
        inner = getattr(widget, "_textbox", None)
        if isinstance(inner, tk.Text):
            try:
                inner.configure(insertbackground=p["text"])
            except tk.TclError:
                pass

    elif isinstance(widget, ctk.CTkCheckBox):
        widget.configure(
            fg_color=p["accent"],
            hover_color=p["accent_hover"],
            text_color=p["text"],
            border_color=p["border"],
            checkmark_color=p["on_accent"],
        )

    elif isinstance(widget, ctk.CTkRadioButton):
        widget.configure(
            fg_color=p["accent"],
            hover_color=p["accent_hover"],
            text_color=p["text"],
            border_color=p["border"],
        )

    elif isinstance(widget, ctk.CTkSwitch):
        widget.configure(
            progress_color=p["accent"],
            text_color=p["text"],
            button_color=p["field"],
        )

    elif isinstance(widget, ctk.CTkSlider):
        widget.configure(
            progress_color=p["accent"],
            button_color=p["accent"],
            button_hover_color=p["accent_hover"],
        )

    elif isinstance(widget, ctk.CTkProgressBar):
        widget.configure(progress_color=p["accent"], fg_color=p["subtle"])

    elif isinstance(widget, ctk.CTkScrollbar):
        widget.configure(button_color=p["subtle_hover"], button_hover_color=p["border"])

    elif isinstance(widget, ctk.CTkLabel):
        widget.configure(text_color=p["text"])
        # Filled labels (used as read-only fields) keep a surface colour.
        if not _is_transparent(widget):
            widget.configure(fg_color=p["subtle"])

    elif isinstance(widget, ctk.CTkScrollableFrame):
        if not _is_transparent(widget):
            widget.configure(fg_color=p["card"])

    elif isinstance(widget, ctk.CTkFrame):
        # Transparent frames are layout containers - leave them alone so the
        # window background shows through.
        if not _is_transparent(widget):
            widget.configure(fg_color=p["card"])


def apply_palette(widget, palette: dict):
    """
    Recursively apply *palette* to *widget* and its descendants.

    Honours ``_theme_skip`` / ``_theme_skip_children`` and calls any
    ``apply_palette`` method a widget provides so composite widgets can theme
    their own internals.
    """
    # Let composite widgets theme themselves first.
    own = getattr(widget, "apply_palette", None)
    if callable(own) and own.__self__ is widget:
        try:
            own(palette)
        except Exception:
            logger.debug(f"apply_palette failed on {widget!r}", exc_info=True)

    if not getattr(widget, "_theme_skip", False):
        try:
            _style_widget(widget, palette)
        except Exception:
            # One bad widget must not abort the whole theme pass.
            logger.debug(f"Could not theme {widget!r}", exc_info=True)

    if getattr(widget, "_theme_skip_children", False):
        return

    try:
        children = widget.winfo_children()
    except Exception:
        return
    for child in children:
        apply_palette(child, palette)


def theme_skip(widget, children: bool = False):
    """Mark *widget* as self-styling so :func:`apply_palette` leaves it alone."""
    widget._theme_skip = True
    if children:
        widget._theme_skip_children = True
    return widget


# ---------------------------------------------------------------------------
# Font scaling
# ---------------------------------------------------------------------------
#
# The header font control used to resize only the document panes and the
# section headings. Everything else - field labels, checkboxes, dropdowns,
# buttons - kept CustomTkinter's built-in size 13 forever, so at larger font
# settings those labels looked disproportionately small. These helpers scale
# the whole UI from one base number.

def font_sizes(base: int) -> dict:
    """
    Derive the UI type scale from the user's chosen font size.

    The floors stop the UI from becoming unreadable at the low end of the
    range, and every role moves together so the hierarchy is preserved:
    headings stay a step above labels, document text a step below.
    """
    base = int(base)
    return {
        "label": max(base + 4, 13),    # field labels, checkboxes, dropdowns
        "heading": max(base + 5, 14),  # section card titles (bold)
        "mono": max(base + 2, 11),     # transcript / response panes
        "title": max(base + 12, 22),   # window title
    }


def _font_spec(widget, size: int):
    """
    Build a font for *widget* at *size*, preserving its family and weight.

    A widget's current font may be a CTkFont or a plain tuple, so both shapes
    are handled; bold stays bold.
    """
    family, weight = None, "normal"
    try:
        current = widget.cget("font")
    except Exception:
        current = None

    if isinstance(current, tuple):
        if len(current) >= 1:
            family = current[0]
        if len(current) >= 3 and "bold" in str(current[2]).lower():
            weight = "bold"
    elif current is not None:
        try:
            family = current.cget("family")
            if str(current.cget("weight")).lower() == "bold":
                weight = "bold"
        except Exception:
            pass

    if family:
        return ctk.CTkFont(family=family, size=size, weight=weight)
    return ctk.CTkFont(size=size, weight=weight)


# Widget types that should follow the "label" size.
_SCALED_TYPES = (
    ctk.CTkLabel,
    ctk.CTkCheckBox,
    ctk.CTkRadioButton,
    ctk.CTkOptionMenu,
    ctk.CTkComboBox,
    ctk.CTkSegmentedButton,
    ctk.CTkEntry,
    ctk.CTkButton,
    ctk.CTkSwitch,
)


def apply_font_scale(widget, base: int):
    """
    Recursively scale fonts under *widget* from the base font size.

    Skips:
    - anything marked ``_font_skip`` (e.g. the app title, tab strip, and the
      icon-ish stepper buttons that must stay compact),
    - CTkTextbox, because each tab picks its own family for document panes and
      applies it in its ``apply_font_size`` hook.

    Composite widgets exposing ``set_title_font`` (the section cards) get the
    heading size so headings stay a step above body text.
    """
    sizes = font_sizes(base)

    if not getattr(widget, "_font_skip", False):
        setter = getattr(widget, "set_title_font", None)
        if callable(setter):
            try:
                setter(ctk.CTkFont(size=sizes["heading"], weight="bold"))
            except Exception:
                logger.debug(f"Could not set title font on {widget!r}", exc_info=True)
        elif isinstance(widget, ctk.CTkTextbox):
            pass  # owned by the tab's apply_font_size
        elif isinstance(widget, _SCALED_TYPES):
            try:
                widget.configure(font=_font_spec(widget, sizes["label"]))
            except Exception:
                logger.debug(f"Could not scale font on {widget!r}", exc_info=True)

    try:
        children = widget.winfo_children()
    except Exception:
        return
    for child in children:
        apply_font_scale(child, base)
