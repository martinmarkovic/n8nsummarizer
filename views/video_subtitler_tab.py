"""
Video Subtitler Tab - download/pick a video, transcribe to SRT, translate, burn in.

Migrated to CustomTkinter (2026-10-30) with the card-based responsive layout
used by the Summarizer tab. The public interface consumed by
VideoSubtitlerController is unchanged.

Notes for this tab specifically:
- CustomTkinter has no Spinbox, so the six numeric style fields use a compact
  ``_int_stepper`` (minus / entry / plus) built here. The underlying variables
  are still ``tk.IntVar``, so ``get_subtitle_style()`` keeps its contract - but
  the values are now read through ``_safe_int`` because a user can type
  anything into an entry, and ``IntVar.get()`` raises TclError on garbage.
- Buttons live next to the content they act on (transcript toolbar, translation
  toolbar, burn card) rather than in one distant action bar.
"""

import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from views.base_tab import CTkBaseTab
from views.ctk_compat import CTkSection, CTkCollapsibleSection, CTkSplitter
from utils.i18n import t
from utils.logger import logger


class VideoSubtitlerTab(CTkBaseTab):
    """Video Subtitler tab with download + transcription UI."""

    # Below this width the source and burn cards stack vertically.
    _STACK_BREAKPOINT = 1200

    # ASS/libass colour codes in &HAABBGGRR (alpha 00 = opaque)
    SUBTITLE_COLORS = {
        "White": "&H00FFFFFF",
        "Yellow": "&H0000FFFF",
        "Cyan": "&H00FFFF00",
        "Green": "&H0000FF00",
        "Orange": "&H0000A5FF",
        "Red": "&H000000FF",
        "Black": "&H00000000",
    }

    # Alignment lookup: (vertical, horizontal) -> ASS numpad alignment
    _ALIGN_MAP = {
        ("Bottom", "Left"): 1, ("Bottom", "Center"): 2, ("Bottom", "Right"): 3,
        ("Middle", "Left"): 4, ("Middle", "Center"): 5, ("Middle", "Right"): 6,
        ("Top", "Left"): 7,    ("Top", "Center"): 8,    ("Top", "Right"): 9,
    }

    # libass renders subtitles in a small reference canvas before scaling to
    # the video. These limits keep the Advanced panel expressive while
    # preventing a single oversized glyph from consuming the whole frame.
    _STYLE_LIMITS = {
        "font_size": (10, 32, 16),
        "outline_width": (0, 4, 1),
        "shadow": (0, 4, 0),
        "margin_v": (0, 80, 20),
        "scale_x": (75, 125, 100),
        "scale_y": (75, 125, 100),
    }

    def __init__(self, notebook):
        self.notebook = notebook

        # State variables
        self.url_var = tk.StringVar()
        self.input_mode = tk.StringVar(value="url")  # "url" or "local"
        self.local_file_path = tk.StringVar()
        self.model_var = tk.StringVar(value="base")
        self.language_var = tk.StringVar(value="auto")
        self.progress_var = tk.StringVar(value=t("video_subtitler.status.ready"))
        self.progress_pct_var = tk.StringVar(value="0%")
        self.output_dir_var = tk.StringVar(value="")
        self.translate_lang_var = tk.StringVar(value="Croatian")

        # Translation LLM info (for display)
        self.translation_llm_label_var = tk.StringVar(
            value=t("video_subtitler.llm.not_configured")
        )

        # Controller will be initialized after UI setup
        self.controller = None

        super().__init__(notebook, "🎞 Video Subtitler")

    # ------------------------------------------------------------------
    # Small widget helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_int(var, default=0):
        """
        Read an IntVar that is backed by a free-text entry.

        ``IntVar.get()`` raises TclError when the entry holds anything
        non-numeric, which is easy to do now that these are plain entries
        rather than Spinboxes.
        """
        try:
            return int(var.get())
        except (tk.TclError, ValueError, TypeError):
            return default

    @staticmethod
    def _clamp_int(value, default: int, minimum: int, maximum: int) -> int:
        """Convert *value* to a safe integer within an inclusive range."""
        try:
            value = int(value)
        except (tk.TclError, ValueError, TypeError):
            value = default
        return max(minimum, min(maximum, value))

    def _style_int(self, name: str, var) -> int:
        """Read one Advanced setting with the same limits shown in the UI."""
        minimum, maximum, default = self._STYLE_LIMITS[name]
        return self._clamp_int(self._safe_int(var, default), default, minimum, maximum)

    def _int_stepper(self, parent, var, from_, to, width=52):
        """
        Compact numeric field: [-] [value] [+].

        Stands in for ttk.Spinbox, which CustomTkinter does not provide.
        Returns the containing frame so the caller can grid it.
        """
        holder = ctk.CTkFrame(parent, fg_color="transparent")

        def _nudge(delta):
            value = self._safe_int(var, from_) + delta
            var.set(max(from_, min(to, value)))

        def _clamp_on_commit(_event=None):
            var.set(max(from_, min(to, self._safe_int(var, from_))))

        minus = ctk.CTkButton(
            holder, text="\u2212", width=26, height=26, corner_radius=6,
            fg_color="transparent", text_color=("gray25", "gray85"),
            hover_color=("gray82", "gray30"),
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: _nudge(-1),
        )
        # Fixed-size glyph buttons: scaling these with the app font would burst
        # the 26px stepper.
        minus._font_skip = True
        minus.grid(row=0, column=0)

        entry = ctk.CTkEntry(
            holder, textvariable=var, width=width, height=26,
            justify="center", border_width=0, corner_radius=6,
        )
        # Part of the grouped stepper: keep it seamless inside the group.
        entry._borderless = True
        entry.grid(row=0, column=1, padx=2)
        entry.bind("<FocusOut>", _clamp_on_commit)
        entry.bind("<Return>", _clamp_on_commit)

        plus = ctk.CTkButton(
            holder, text="+", width=26, height=26, corner_radius=6,
            fg_color="transparent", text_color=("gray25", "gray85"),
            hover_color=("gray82", "gray30"),
            font=ctk.CTkFont(size=14, weight="bold"),
            command=lambda: _nudge(1),
        )
        plus._font_skip = True
        plus.grid(row=0, column=2)

        return holder

    @staticmethod
    def _muted(parent, text, **kw):
        """A secondary/explanatory label."""
        kw.setdefault("anchor", "w")
        kw.setdefault("text_color", ("gray40", "gray65"))
        return ctk.CTkLabel(parent, text=text, **kw)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """
        Layout:
            0  source card + burn card (stacking when narrow)
            1  progress card
            2  transcript / translation split   <- expanding region
        """
        # Content goes in self.body (the scroll-when-needed area from
        # CTkBaseTab), not self, so short windows can still reach everything.
        # This tab in particular has a tall burn-options card.
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(2, weight=1)

        self._stacked = False

        self._setup_top_row()
        self._setup_progress_section()
        self._setup_text_split()

        # Mode change handler (also keeps the segmented control in sync)
        self.input_mode.trace("w", self._on_mode_change)
        self._on_mode_change()

        # Reflect the default burn mode in the style panel's visibility
        self._on_burn_mode_change()

        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, _event=None):
        self.after_idle(self._apply_responsive_layout)

    def _apply_responsive_layout(self):
        """Stack the source and burn cards on narrow windows."""
        width = self.winfo_width()
        if width <= 1:
            width = self.winfo_toplevel().winfo_width()
        if width <= 1:
            return
        stacked = width < self._STACK_BREAKPOINT
        if stacked == self._stacked:
            return
        self._stacked = stacked

        if stacked:
            self._top_row.grid_columnconfigure(1, weight=0)
            self._burn_section.grid_configure(row=1, column=0, padx=0, pady=(10, 0))
        else:
            self._top_row.grid_columnconfigure(1, weight=1)
            self._burn_section.grid_configure(row=0, column=1, padx=(10, 0), pady=0)

    def _setup_top_row(self):
        self._top_row = ctk.CTkFrame(self.body, fg_color="transparent")
        self._top_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._top_row.grid_columnconfigure(0, weight=1)
        self._top_row.grid_columnconfigure(1, weight=1)

        self._setup_source_section()
        self._setup_burn_section()

    # ---------------------------- source ------------------------------

    def _setup_source_section(self):
        """Input source, whisper options and the start actions."""
        section = CTkSection(
            self._top_row, title=t("video_subtitler.frame.source_settings")
        )
        section.grid(row=0, column=0, sticky="new")
        self._source_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        row = 0
        # Mode selection (URL vs Local File)
        self._mode_labels = {
            "URL": "url",
            t("video_subtitler.radio.local_file"): "local",
        }
        self._mode_values = {v: k for k, v in self._mode_labels.items()}

        self.mode_selector = ctk.CTkSegmentedButton(
            body,
            values=list(self._mode_labels.keys()),
            command=self._on_mode_selected,
            height=32,
            font=ctk.CTkFont(size=13),
        )
        self.mode_selector.grid(row=row, column=0, sticky="w", pady=(0, 10))
        self.mode_selector.set(self._mode_values[self.input_mode.get()])

        # --- URL input ---
        row += 1
        self.url_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.url_frame.grid(row=row, column=0, sticky="ew")
        self.url_frame.grid_columnconfigure(0, weight=1)

        url_entry = ctk.CTkEntry(
            self.url_frame, textvariable=self.url_var, height=34,
            placeholder_text=t("video_subtitler.lbl.video_url"),
        )
        url_entry.grid(row=0, column=0, sticky="ew")
        self._register_entry_context_menu(url_entry)

        # --- Local file input ---
        self.local_frame = ctk.CTkFrame(body, fg_color="transparent")
        self.local_frame.grid(row=row, column=0, sticky="ew")
        self.local_frame.grid_columnconfigure(0, weight=1)

        local_file_entry = ctk.CTkEntry(
            self.local_frame, textvariable=self.local_file_path, height=34,
            state="readonly", placeholder_text=t("video_subtitler.lbl.local_file"),
        )
        local_file_entry.grid(row=0, column=0, sticky="ew")
        self._register_entry_context_menu(local_file_entry, allow_paste=False)

        ctk.CTkButton(
            self.local_frame, text=t("video_subtitler.btn.browse"),
            command=self._browse_local_file, width=90, height=34,
        ).grid(row=0, column=1, padx=(8, 0))

        self.local_frame.grid_remove()  # URL mode is the default

        # --- Whisper model + language ---
        row += 1
        opts = ctk.CTkFrame(body, fg_color="transparent")
        opts.grid(row=row, column=0, sticky="ew", pady=(10, 0))

        self._muted(opts, t("video_subtitler.lbl.whisper_model")).grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        ctk.CTkOptionMenu(
            opts, variable=self.model_var,
            values=["tiny", "base", "small", "medium", "large"],
            width=110, height=30,
        ).grid(row=0, column=1, padx=(0, 14))

        self._muted(opts, t("video_subtitler.lbl.language")).grid(
            row=0, column=2, sticky="w", padx=(0, 6)
        )
        ctk.CTkOptionMenu(
            opts, variable=self.language_var,
            values=["auto", "en", "hr", "de", "fr", "es", "it", "pt", "ru", "ja", "zh"],
            width=90, height=30,
        ).grid(row=0, column=3)

        # --- Output folder ---
        row += 1
        self._muted(body, t("video_subtitler.lbl.output_folder")).grid(
            row=row, column=0, sticky="w", pady=(10, 2)
        )

        row += 1
        out_row = ctk.CTkFrame(body, fg_color="transparent")
        out_row.grid(row=row, column=0, sticky="ew")
        out_row.grid_columnconfigure(0, weight=1)

        output_entry = ctk.CTkEntry(
            out_row, textvariable=self.output_dir_var, height=32, state="readonly"
        )
        output_entry.grid(row=0, column=0, sticky="ew")
        self._register_entry_context_menu(output_entry, allow_paste=False)

        ctk.CTkButton(
            out_row, text=t("video_subtitler.btn.change"),
            command=self._on_change_output_folder, width=90, height=32,
        ).grid(row=0, column=1, padx=(8, 0))

        # --- Translate target + LLM info ---
        row += 1
        tr_row = ctk.CTkFrame(body, fg_color="transparent")
        tr_row.grid(row=row, column=0, sticky="ew", pady=(10, 0))

        self._muted(tr_row, t("video_subtitler.lbl.translate_to")).grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        ctk.CTkOptionMenu(
            tr_row, variable=self.translate_lang_var,
            values=["English", "Croatian", "German", "French", "Spanish",
                    "Italian", "Portuguese", "Russian", "Japanese", "Chinese"],
            width=140, height=30,
        ).grid(row=0, column=1)

        row += 1
        ctk.CTkLabel(
            body, textvariable=self.translation_llm_label_var, anchor="w",
            justify="left", wraplength=460, text_color=("gray45", "gray60"),
        ).grid(row=row, column=0, sticky="ew", pady=(6, 0))

        # --- Start / Auto ---
        row += 1
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=row, column=0, sticky="ew", pady=(12, 0))

        self.start_btn = ctk.CTkButton(
            actions, text=t("video_subtitler.btn.start"), command=self._on_start,
            width=130, height=36, corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 8))

        self.auto_btn = ctk.CTkButton(
            actions, text=t("video_subtitler.btn.auto"), command=self._on_auto,
            width=120, height=36, corner_radius=8,
            fg_color="transparent", border_width=1,
            border_color=("gray70", "gray40"), text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
        )
        self.auto_btn.grid(row=0, column=1)

    # ----------------------------- burn -------------------------------

    def _setup_burn_section(self):
        """Subtitle burn-in options."""
        section = CTkSection(self._top_row, title=t("video_subtitler.frame.burn"))
        section.grid(row=0, column=1, sticky="new", padx=(10, 0))
        self._burn_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        row = 0
        self.use_original_name_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            body, text=t("video_subtitler.chk.name_after_original"),
            variable=self.use_original_name_var,
            checkbox_width=18, checkbox_height=18,
        ).grid(row=row, column=0, sticky="w")

        # Burn mode: Simple (minimal, known-good command - default) vs
        # Advanced (full subtitle style panel).
        row += 1
        mode_row = ctk.CTkFrame(body, fg_color="transparent")
        mode_row.grid(row=row, column=0, sticky="ew", pady=(10, 0))

        self._muted(mode_row, t("video_subtitler.lbl.rendering")).grid(row=0, column=0, padx=(0, 8))

        self.burn_mode_var = tk.StringVar(value="simple")
        self._burn_mode_labels = {
            t("video_subtitler.mode.simple"): "simple",
            t("video_subtitler.mode.advanced"): "advanced",
        }
        self._burn_mode_values = {v: k for k, v in self._burn_mode_labels.items()}

        self.burn_mode_selector = ctk.CTkSegmentedButton(
            mode_row, values=list(self._burn_mode_labels.keys()),
            command=self._on_burn_mode_selected, height=30,
            font=ctk.CTkFont(size=12),
        )
        self.burn_mode_selector.grid(row=0, column=1)
        self.burn_mode_selector.set(self._burn_mode_values["simple"])
        self.burn_mode_var.trace("w", self._on_burn_mode_change)

        # Subtitle source
        row += 1
        self._muted(body, t("video_subtitler.lbl.subtitle_source")).grid(
            row=row, column=0, sticky="w", pady=(10, 2)
        )

        row += 1
        self.subtitle_source_var = tk.StringVar(value="translated")
        self._source_labels = {
            t("video_subtitler.radio.translated_srt"): "translated",
            t("video_subtitler.radio.original_srt"): "original",
        }
        self._source_values = {v: k for k, v in self._source_labels.items()}

        self.subtitle_source_selector = ctk.CTkSegmentedButton(
            body, values=list(self._source_labels.keys()),
            command=self._on_subtitle_source_selected, height=30,
            font=ctk.CTkFont(size=12),
        )
        self.subtitle_source_selector.grid(row=row, column=0, sticky="ew")
        self.subtitle_source_selector.set(self._source_values["translated"])

        # Dark background + opacity
        row += 1
        self.dark_bg_var = tk.BooleanVar(value=False)  # outlined text is more usable
        ctk.CTkCheckBox(
            body, text=t("video_subtitler.chk.dark_bg"), variable=self.dark_bg_var,
            checkbox_width=18, checkbox_height=18,
        ).grid(row=row, column=0, sticky="w", pady=(10, 0))

        row += 1
        opacity_row = ctk.CTkFrame(body, fg_color="transparent")
        opacity_row.grid(row=row, column=0, sticky="ew", pady=(8, 0))
        opacity_row.grid_columnconfigure(1, weight=1)

        self._muted(opacity_row, t("video_subtitler.lbl.background_opacity")).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )

        self.bg_opacity_var = tk.DoubleVar(value=0.6)
        ctk.CTkSlider(
            opacity_row, from_=0.1, to=0.7, variable=self.bg_opacity_var, height=16
        ).grid(row=0, column=1, sticky="ew")

        self.opacity_label_var = tk.StringVar(value="0.60")
        ctk.CTkLabel(opacity_row, textvariable=self.opacity_label_var, width=40).grid(
            row=0, column=2, padx=(8, 0)
        )

        def _update_opacity_label(*_args):
            self.opacity_label_var.set(f"{self.bg_opacity_var.get():.2f}")
        self.bg_opacity_var.trace("w", _update_opacity_label)

        # Style panel (Advanced only)
        row += 1
        self._build_subtitle_style_panel(body, start_row=row)

        # Burn action + status
        row += 1
        self.burn_btn = ctk.CTkButton(
            body, text=t("video_subtitler.btn.burn"), command=self._on_burn_clicked,
            state="disabled", height=36, corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.burn_btn.grid(row=row, column=0, sticky="ew", pady=(12, 0))

        row += 1
        self.ffmpeg_status_var = tk.StringVar(value="")
        ctk.CTkLabel(
            body, textvariable=self.ffmpeg_status_var, anchor="w", justify="left",
            wraplength=460, text_color=("gray45", "gray60"),
        ).grid(row=row, column=0, sticky="ew", pady=(6, 0))

        row += 1
        self.open_output_btn = ctk.CTkButton(
            body, text=t("video_subtitler.btn.open_output"),
            command=self._open_output_file, state="disabled", height=32,
            corner_radius=8, fg_color="transparent", border_width=1,
            border_color=("gray70", "gray40"), text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
        )
        self.open_output_btn.grid(row=row, column=0, sticky="ew", pady=(8, 0))

    def _build_subtitle_style_panel(self, parent, start_row):
        """Build the subtitle appearance controls (Advanced burn mode)."""
        style_frame = CTkCollapsibleSection(
            parent, title=t("video_subtitler.frame.subtitle_style"),
            padding=10, expanded=True,
        )
        style_frame.grid(row=start_row, column=0, sticky="ew", pady=(12, 0))
        # Keep a reference so the Simple/Advanced toggle can show/hide it
        self.style_frame = style_frame
        body = style_frame.body
        for c in range(4):
            body.grid_columnconfigure(c, weight=1)

        color_names = list(self.SUBTITLE_COLORS.keys())

        # Font size.
        # NOTE: the subtitles filter renders in a 384x288 reference space and
        # scales up to the video resolution, so ~16 gives normal-looking
        # captions on 720p/1080p. Higher values quickly get oversized.
        self._muted(body, t("video_subtitler.lbl.font_size")).grid(
            row=0, column=0, sticky="w", pady=2
        )
        self.font_size_var = tk.IntVar(value=16)
        self._int_stepper(body, self.font_size_var, 10, 32).grid(
            row=0, column=1, sticky="w", pady=2
        )

        # Bold / Italic
        self.bold_var = tk.BooleanVar(value=False)
        self.italic_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            body, text=t("video_subtitler.chk.bold"), variable=self.bold_var,
            checkbox_width=18, checkbox_height=18, width=70,
        ).grid(row=0, column=2, sticky="w", pady=2)
        ctk.CTkCheckBox(
            body, text=t("video_subtitler.chk.italic"), variable=self.italic_var,
            checkbox_width=18, checkbox_height=18, width=70,
        ).grid(row=0, column=3, sticky="w", pady=2)

        # Text colour
        self._muted(body, t("video_subtitler.lbl.text_colour")).grid(
            row=1, column=0, sticky="w", pady=2
        )
        self.text_color_var = tk.StringVar(value="White")
        ctk.CTkOptionMenu(
            body, variable=self.text_color_var, values=color_names, width=100, height=28
        ).grid(row=1, column=1, sticky="w", pady=2)

        # Outline colour
        self._muted(body, t("video_subtitler.lbl.outline_colour")).grid(
            row=1, column=2, sticky="w", pady=2
        )
        self.outline_color_var = tk.StringVar(value="Black")
        ctk.CTkOptionMenu(
            body, variable=self.outline_color_var, values=color_names,
            width=100, height=28,
        ).grid(row=1, column=3, sticky="w", pady=2)

        # Outline width
        self._muted(body, t("video_subtitler.lbl.outline_width")).grid(
            row=2, column=0, sticky="w", pady=2
        )
        self.outline_width_var = tk.IntVar(value=1)
        self._int_stepper(body, self.outline_width_var, 0, 4).grid(
            row=2, column=1, sticky="w", pady=2
        )

        # Shadow depth
        self._muted(body, t("video_subtitler.lbl.shadow")).grid(
            row=2, column=2, sticky="w", pady=2
        )
        self.shadow_var = tk.IntVar(value=0)
        self._int_stepper(body, self.shadow_var, 0, 4).grid(
            row=2, column=3, sticky="w", pady=2
        )

        # Position: vertical + horizontal alignment
        self._muted(body, t("video_subtitler.lbl.position")).grid(
            row=3, column=0, sticky="w", pady=2
        )
        self.v_align_var = tk.StringVar(value="Bottom")
        ctk.CTkOptionMenu(
            body, variable=self.v_align_var, values=["Bottom", "Middle", "Top"],
            width=100, height=28,
        ).grid(row=3, column=1, sticky="w", pady=2)
        self.h_align_var = tk.StringVar(value="Center")
        ctk.CTkOptionMenu(
            body, variable=self.h_align_var, values=["Left", "Center", "Right"],
            width=100, height=28,
        ).grid(row=3, column=2, sticky="w", pady=2)

        # Vertical margin (distance from edge)
        self._muted(body, t("video_subtitler.lbl.vertical_margin")).grid(
            row=4, column=0, sticky="w", pady=2
        )
        self.margin_v_var = tk.IntVar(value=20)
        self._int_stepper(body, self.margin_v_var, 0, 80, width=60).grid(
            row=4, column=1, sticky="w", pady=2
        )

        # Horizontal / vertical scale (percent)
        self._muted(body, t("video_subtitler.lbl.horizontal_scale")).grid(
            row=5, column=0, sticky="w", pady=2
        )
        self.scale_x_var = tk.IntVar(value=100)
        self._int_stepper(body, self.scale_x_var, 75, 125, width=60).grid(
            row=5, column=1, sticky="w", pady=2
        )
        self._muted(body, t("video_subtitler.lbl.vertical_scale")).grid(
            row=5, column=2, sticky="w", pady=2
        )
        self.scale_y_var = tk.IntVar(value=100)
        self._int_stepper(body, self.scale_y_var, 75, 125, width=60).grid(
            row=5, column=3, sticky="w", pady=2
        )

        self._muted(
            body, t("video_subtitler.hint.advanced_style"), wraplength=460,
            justify="left",
        ).grid(row=6, column=0, columnspan=4, sticky="ew", pady=(8, 0))

    # --------------------------- progress -----------------------------

    def _setup_progress_section(self):
        section = CTkSection(
            self.body, title=t("video_subtitler.frame.progress"), padding=10
        )
        section.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._progress_section = section
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        bar_row = ctk.CTkFrame(body, fg_color="transparent")
        bar_row.grid(row=0, column=0, sticky="ew")
        bar_row.grid_columnconfigure(0, weight=1)

        self.progress_bar = ctk.CTkProgressBar(bar_row, mode="determinate", height=10)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        ctk.CTkLabel(bar_row, textvariable=self.progress_pct_var, width=56).grid(
            row=0, column=1
        )

        ctk.CTkLabel(
            body, textvariable=self.progress_var, anchor="w", justify="left",
            wraplength=1100, text_color=("gray35", "gray70"),
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))

    # ------------------------- text panes -----------------------------

    def _setup_text_split(self):
        """Transcript and translation side by side with a draggable divider."""
        self._split = CTkSplitter(self.body, ratio=0.5)
        self._split.grid(row=2, column=0, sticky="nsew")

        # --- Transcription (left) ---
        srt_section = CTkSection(
            self._split.left, title=t("video_subtitler.frame.transcription"), padding=10
        )
        srt_section.grid(row=0, column=0, sticky="nsew")
        self._split.left.grid_rowconfigure(0, weight=1)
        self._split.left.grid_columnconfigure(0, weight=1)
        self._srt_section = srt_section
        body = srt_section.body
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self.srt_text = ctk.CTkTextbox(
            body, wrap="word", font=("Cascadia Mono", 12),
            activate_scrollbars=True, corner_radius=8,
        )
        self.srt_text.grid(row=0, column=0, sticky="nsew")

        # Enable burn button when SRT content is present
        self.srt_text.bind("<<Modified>>", self._on_srt_text_modified)

        self._register_context_menu(
            self.srt_text,
            [
                {"copy": True},
                {"paste": True},
                {"separator": True},
                {"tts_read": lambda: self._selection_or_all(self.srt_text)},
                {"tts_stop": True},
                {"separator": True},
                {"fullscreen": True,
                 "title": t("video_subtitler.fullscreen.transcription_srt"),
                 "editable": True},
            ],
        )

        srt_tools = ctk.CTkFrame(body, fg_color="transparent")
        srt_tools.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        ctk.CTkButton(
            srt_tools, text=t("video_subtitler.btn.open_temp_folder"),
            command=self._open_temp_folder, height=30,
        ).grid(row=0, column=0, padx=(0, 6))

        ctk.CTkButton(
            srt_tools, text=t("video_subtitler.btn.copy_srt_path"),
            command=self._copy_srt_path, height=30,
            fg_color="transparent", border_width=1,
            border_color=("gray70", "gray40"), text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
        ).grid(row=0, column=1)

        # --- Translation (right) ---
        tr_section = CTkSection(
            self._split.right, title=t("video_subtitler.frame.translation"), padding=10
        )
        tr_section.grid(row=0, column=0, sticky="nsew")
        self._split.right.grid_rowconfigure(0, weight=1)
        self._split.right.grid_columnconfigure(0, weight=1)
        self._translation_section = tr_section
        tbody = tr_section.body
        tbody.grid_columnconfigure(0, weight=1)
        tbody.grid_rowconfigure(0, weight=1)

        self.translated_srt_text = ctk.CTkTextbox(
            tbody, wrap="word", font=("Cascadia Mono", 12),
            activate_scrollbars=True, corner_radius=8,
        )
        self.translated_srt_text.grid(row=0, column=0, sticky="nsew")

        # Enable burn button when translated SRT content is present
        self.translated_srt_text.bind(
            "<<Modified>>", self._on_translated_srt_text_modified
        )

        self._register_context_menu(
            self.translated_srt_text,
            [
                {"copy": True},
                {"paste": True},
                {"separator": True},
                {"tts_read": lambda: self._selection_or_all(self.translated_srt_text)},
                {"tts_stop": True},
                {"separator": True},
                {"fullscreen": True,
                 "title": t("video_subtitler.fullscreen.translated_srt"),
                 "editable": True},
            ],
        )

        tr_tools = ctk.CTkFrame(tbody, fg_color="transparent")
        tr_tools.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        self.translate_btn = ctk.CTkButton(
            tr_tools, text=t("video_subtitler.btn.translate_srt"),
            command=self._on_translate_clicked, state="disabled", height=30,
        )
        self.translate_btn.grid(row=0, column=0, padx=(0, 6))

        ctk.CTkButton(
            tr_tools, text=t("video_subtitler.btn.save_translated_srt"),
            command=self._on_save_translated, height=30,
            fg_color="transparent", border_width=1,
            border_color=("gray70", "gray40"), text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
        ).grid(row=0, column=1)

    # ------------------------------------------------------------------
    # Mode / option handlers
    # ------------------------------------------------------------------

    def _on_mode_selected(self, label: str):
        mode = self._mode_labels.get(label)
        if mode and mode != self.input_mode.get():
            self.input_mode.set(mode)  # trace triggers _on_mode_change

    def _on_mode_change(self, *args):
        """Handle input mode change (URL vs Local File)."""
        if self.input_mode.get() == "url":
            self.url_frame.grid()
            self.local_frame.grid_remove()
        else:
            self.url_frame.grid_remove()
            self.local_frame.grid()

        if hasattr(self, "mode_selector"):
            label = self._mode_values.get(self.input_mode.get())
            if label and self.mode_selector.get() != label:
                self.mode_selector.set(label)

    def _on_burn_mode_selected(self, label: str):
        mode = self._burn_mode_labels.get(label)
        if mode and mode != self.burn_mode_var.get():
            self.burn_mode_var.set(mode)  # trace triggers _on_burn_mode_change

    def _on_burn_mode_change(self, *args):
        """Show the Subtitle Style panel only in Advanced mode."""
        if not hasattr(self, "style_frame"):
            return
        try:
            if self.burn_mode_var.get() == "advanced":
                self.style_frame.grid()
            else:
                self.style_frame.grid_remove()
        except tk.TclError:
            pass

        if hasattr(self, "burn_mode_selector"):
            label = self._burn_mode_values.get(self.burn_mode_var.get())
            if label and self.burn_mode_selector.get() != label:
                self.burn_mode_selector.set(label)

    def _on_subtitle_source_selected(self, label: str):
        value = self._source_labels.get(label)
        if value:
            self.subtitle_source_var.set(value)

    def _sync_subtitle_source_selector(self):
        """Keep the segmented control in step with subtitle_source_var."""
        if hasattr(self, "subtitle_source_selector"):
            label = self._source_values.get(self.subtitle_source_var.get())
            if label and self.subtitle_source_selector.get() != label:
                self.subtitle_source_selector.set(label)

    def get_burn_mode(self) -> str:
        """Return the current burn mode ('simple' or 'advanced')."""
        return self.burn_mode_var.get()

    def get_subtitle_style(self) -> dict:
        """Return the current subtitle style options as a dict for the controller."""
        return {
            "font_size": self._style_int("font_size", self.font_size_var),
            "bold": self.bold_var.get(),
            "italic": self.italic_var.get(),
            "primary_colour": self.SUBTITLE_COLORS.get(
                self.text_color_var.get(), "&H00FFFFFF"
            ),
            "outline_colour": self.SUBTITLE_COLORS.get(
                self.outline_color_var.get(), "&H00000000"
            ),
            "outline": self._style_int("outline_width", self.outline_width_var),
            "shadow": self._style_int("shadow", self.shadow_var),
            "alignment": self._ALIGN_MAP.get(
                (self.v_align_var.get(), self.h_align_var.get()), 2
            ),
            "margin_v": self._style_int("margin_v", self.margin_v_var),
            "scale_x": self._style_int("scale_x", self.scale_x_var),
            "scale_y": self._style_int("scale_y", self.scale_y_var),
        }

    def get_burn_prefs(self) -> dict:
        """
        Return the raw burn/style selections for persistence (color names, not
        ASS codes, so they can be restored into the dropdowns).
        """
        return {
            "font_size": self._style_int("font_size", self.font_size_var),
            "bold": self.bold_var.get(),
            "italic": self.italic_var.get(),
            "text_color": self.text_color_var.get(),
            "outline_color": self.outline_color_var.get(),
            "outline_width": self._style_int("outline_width", self.outline_width_var),
            "shadow": self._style_int("shadow", self.shadow_var),
            "v_align": self.v_align_var.get(),
            "h_align": self.h_align_var.get(),
            "margin_v": self._style_int("margin_v", self.margin_v_var),
            "scale_x": self._style_int("scale_x", self.scale_x_var),
            "scale_y": self._style_int("scale_y", self.scale_y_var),
            "dark_bg": self.dark_bg_var.get(),
            "bg_opacity": round(self.bg_opacity_var.get(), 2),
            "burn_mode": self.burn_mode_var.get(),
        }

    def apply_burn_prefs(self, prefs: dict) -> None:
        """Apply previously-saved burn/style selections to the controls."""
        if not prefs:
            return
        setters = {
            "font_size": self.font_size_var.set,
            "bold": self.bold_var.set,
            "italic": self.italic_var.set,
            "text_color": self.text_color_var.set,
            "outline_color": self.outline_color_var.set,
            "outline_width": self.outline_width_var.set,
            "shadow": self.shadow_var.set,
            "v_align": self.v_align_var.set,
            "h_align": self.h_align_var.set,
            "margin_v": self.margin_v_var.set,
            "scale_x": self.scale_x_var.set,
            "scale_y": self.scale_y_var.set,
            "dark_bg": self.dark_bg_var.set,
            "bg_opacity": self.bg_opacity_var.set,
            "burn_mode": self.burn_mode_var.set,
        }
        for key, setter in setters.items():
            if key in prefs and prefs[key] is not None:
                try:
                    value = prefs[key]
                    if key in self._STYLE_LIMITS:
                        minimum, maximum, default = self._STYLE_LIMITS[key]
                        value = self._clamp_int(value, default, minimum, maximum)
                    setter(value)
                except Exception:
                    logger.debug(f"Could not restore burn pref {key!r}", exc_info=True)
        # Reflect a restored mode in the style panel's visibility
        self._on_burn_mode_change()

    def set_controller(self, controller):
        """Set the controller for this view."""
        self.controller = controller

    # ------------------------------------------------------------------
    # UI Event Handlers
    # ------------------------------------------------------------------

    def _on_start(self):
        """Handle start button click."""
        if self.controller:
            self.controller.on_start()

    def _on_auto(self):
        """Handle auto button click."""
        if self.controller:
            self.controller.on_auto()

    def _browse_local_file(self):
        """Browse for local video file."""
        supported_formats = [
            (t("video_subtitler.filetype.video"), "*.mp4 *.avi *.mov *.mkv *.webm"),
            (t("video_subtitler.filetype.audio"), "*.mp3 *.wav *.flac *.m4a"),
            (t("video_subtitler.filetype.all"), "*.*"),
        ]
        file_path = filedialog.askopenfilename(
            title=t("video_subtitler.dialog.select_media"),
            filetypes=supported_formats,
        )
        if file_path:
            self.local_file_path.set(file_path)

    def _open_temp_folder(self):
        """Open temp_subtitler folder."""
        try:
            temp_dir = Path("temp_subtitler")
            if temp_dir.exists():
                os.startfile(str(temp_dir))
            else:
                messagebox.showinfo(
                    t("video_subtitler.msg.info_title"),
                    t("video_subtitler.msg.temp_not_exist"),
                )
        except Exception as e:
            messagebox.showerror(
                t("video_subtitler.msg.error_title"),
                t("video_subtitler.msg.could_not_open_folder").format(error=e),
            )

    def _copy_srt_path(self):
        """Copy SRT path to clipboard."""
        srt_path = "temp_subtitler/video.srt"
        self.clipboard_clear()
        self.clipboard_append(srt_path)
        self.log_message(
            t("video_subtitler.status.copied_clipboard").format(path=srt_path)
        )

    def _on_srt_text_modified(self, event=None):
        """Enable burn button (original source) when SRT content is present."""
        # Reset the modified flag so the event fires again next time
        self.srt_text.edit_modified(False)
        has_content = bool(self.srt_text.get("1.0", tk.END).strip())
        if has_content:
            self.burn_btn.configure(state="normal")
            # Switch the source to "original" unless a translation exists
            if (self.subtitle_source_var.get() != "translated"
                    or not self.translated_srt_text.get("1.0", tk.END).strip()):
                self.subtitle_source_var.set("original")
                self._sync_subtitle_source_selector()

    def _on_translated_srt_text_modified(self, event=None):
        """Enable burn button (translated source) when translated SRT is present."""
        self.translated_srt_text.edit_modified(False)
        has_content = bool(self.translated_srt_text.get("1.0", tk.END).strip())
        if has_content:
            self.burn_btn.configure(state="normal")
            self.subtitle_source_var.set("translated")
            self._sync_subtitle_source_selector()

    def _on_translate_clicked(self):
        """Handle translate button click."""
        if self.controller and hasattr(self.controller, 'on_translate'):
            self.controller.on_translate()

    def _on_save_translated(self):
        """Save translated SRT to file."""
        translated_srt = self.get_translated_srt()
        if not translated_srt:
            messagebox.showinfo(
                t("video_subtitler.msg.info_title"),
                t("video_subtitler.msg.no_translated_to_save"),
            )
            return

        file_path = filedialog.asksaveasfilename(
            title=t("video_subtitler.dialog.save_translated"),
            defaultextension=".srt",
            filetypes=[
                (t("video_subtitler.filetype.srt"), "*.srt"),
                (t("video_subtitler.filetype.all"), "*.*"),
            ],
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(translated_srt)
                messagebox.showinfo(
                    t("video_subtitler.msg.success_title"),
                    t("video_subtitler.msg.translated_saved").format(path=file_path),
                )
            except Exception as e:
                messagebox.showerror(
                    t("video_subtitler.msg.error_title"),
                    t("video_subtitler.msg.failed_save").format(error=e),
                )

    def _on_burn_clicked(self):
        """Handle burn button click."""
        if self.controller and hasattr(self.controller, 'on_burn'):
            self.controller.on_burn()

    def _open_output_file(self):
        """Open output video file."""
        if self.controller and hasattr(self.controller, 'output_video_path'):
            try:
                os.startfile(str(self.controller.output_video_path))
            except Exception as e:
                messagebox.showerror(
                    t("video_subtitler.msg.error_title"),
                    t("video_subtitler.msg.could_not_open_file").format(error=e),
                )
        else:
            messagebox.showinfo(
                t("video_subtitler.msg.info_title"),
                t("video_subtitler.msg.no_output_file"),
            )

    def _on_change_output_folder(self):
        """Handle change output folder button click."""
        chosen = filedialog.askdirectory(
            title=t("video_subtitler.dialog.select_output_folder")
        )
        if chosen:
            self.output_dir_var.set(chosen)
            if self.controller:
                self.controller.set_output_dir(chosen)

    # ------------------------------------------------------------------
    # View Helper Methods (called by controller)
    # ------------------------------------------------------------------

    def get_url(self) -> str:
        """Get current URL from input field."""
        return self.url_var.get().strip()

    def get_local_file_path(self) -> str:
        """Get selected local file path."""
        return self.local_file_path.get().strip()

    def get_input_mode(self) -> str:
        """Get current input mode."""
        return self.input_mode.get()

    def get_whisper_model(self) -> str:
        """Get selected Whisper model."""
        return self.model_var.get()

    def get_language(self) -> str:
        """Get selected language."""
        return self.language_var.get()

    def update_progress(self, pct: float, message: str):
        """
        Update progress bar and status.

        The controller reports 0-100; CTkProgressBar wants a 0..1 fraction.
        """
        self.progress_bar.set(min(max(pct / 100.0, 0.0), 1.0))
        self.progress_pct_var.set(f"{pct:.1f}%")
        self.progress_var.set(message)

    def update_status(self, message: str):
        """Update status message."""
        self.progress_var.set(message)

    def display_srt(self, text: str):
        """Display SRT text in the text widget."""
        self.srt_text.delete("1.0", tk.END)
        self.srt_text.insert(tk.END, text)

    def set_busy(self, is_busy: bool):
        """Enable or disable start button."""
        self.start_btn.configure(state="disabled" if is_busy else "normal")

    def show_error(self, message: str):
        """Show error dialog."""
        logger.error(f"[{self.tab_name}] {message}")
        messagebox.showerror(t("video_subtitler.msg.error_title"), message)

    def log_message(self, message: str):
        """Add message to status (for simple logging)."""
        current = self.progress_var.get()
        if current != t("video_subtitler.status.ready"):
            self.progress_var.set(f"{current} | {message}")
        else:
            self.progress_var.set(message)

    def get_target_language(self) -> str:
        """Get target language for translation."""
        return self.translate_lang_var.get()

    def update_translation_llm_label(self, provider, model):
        """Update the translation LLM info label."""
        if provider and model:
            self.translation_llm_label_var.set(
                t("video_subtitler.llm.configured").format(
                    provider=provider, model=model
                )
            )
        else:
            self.translation_llm_label_var.set(
                t("video_subtitler.llm.not_configured")
            )

    def display_translated_srt(self, text: str):
        """Display translated SRT text."""
        self.translated_srt_text.delete("1.0", tk.END)
        self.translated_srt_text.insert(tk.END, text)

    def enable_translate_btn(self):
        """Enable translate button."""
        self.translate_btn.configure(state="normal")

    def get_translated_srt(self) -> str:
        """Get translated SRT content."""
        return self.translated_srt_text.get("1.0", tk.END).strip()

    def get_subtitle_source(self) -> str:
        """Get subtitle source selection."""
        return self.subtitle_source_var.get()

    def enable_burn_btn(self):
        """Enable burn button."""
        self.burn_btn.configure(state="normal")

    def enable_open_btn(self):
        """Enable open output file button."""
        self.open_output_btn.configure(state="normal")

    def update_ffmpeg_status(self, msg: str):
        """Update FFmpeg status message."""
        self.ffmpeg_status_var.set(msg)

    def get_use_original_name(self) -> bool:
        """Get use original name setting."""
        return self.use_original_name_var.get()

    def get_dark_bg(self) -> bool:
        """Get dark background setting."""
        return self.dark_bg_var.get()

    def get_bg_opacity(self) -> float:
        """Get background opacity setting."""
        return round(self.bg_opacity_var.get(), 2)

    # ------------------------------------------------------------------
    # CTkBaseTab abstract method implementations
    # ------------------------------------------------------------------

    def get_content(self) -> str:
        """Return current SRT content."""
        return self.srt_text.get("1.0", tk.END)

    def clear_all(self):
        """Clear all input fields and SRT text."""
        self.url_var.set("")
        self.model_var.set("base")
        self.language_var.set("auto")
        self.progress_bar.set(0)
        self.progress_pct_var.set("0%")
        self.progress_var.set(t("video_subtitler.status.ready"))
        self.srt_text.delete("1.0", tk.END)

        # Clear translation section
        if hasattr(self, "translated_srt_text"):
            self.translated_srt_text.delete("1.0", tk.END)
        if hasattr(self, "translate_btn"):
            self.translate_btn.configure(state="disabled")

        # Clear FFmpeg section
        if hasattr(self, "burn_btn"):
            self.burn_btn.configure(state="disabled")
        if hasattr(self, "open_output_btn"):
            self.open_output_btn.configure(state="disabled")
        if hasattr(self, "ffmpeg_status_var"):
            self.ffmpeg_status_var.set("")

    # ------------------------------------------------------------------
    # Theming hook used by MainWindow
    # ------------------------------------------------------------------

    def apply_font_size(self, size: int):
        """
        Apply the app-wide font size to this tab's SRT panes.

        Labels, controls and section headings are scaled centrally by
        :func:`views.ctk_theme.apply_font_scale`.
        """
        from views.ctk_theme import font_sizes
        mono = font_sizes(size)["mono"]
        self.srt_text.configure(font=("Cascadia Mono", mono))
        self.translated_srt_text.configure(font=("Cascadia Mono", mono))
