"""
Picture to Text Tab - OCR via a local OpenAI-compatible vision model.

Pure View component following the MVC pattern used by the other tabs. It lets
the user pick an image, choose a local provider / endpoint / vision model
(reusing the same provider conventions as the Translation and Summarizer
tabs), run extraction, and read the resulting text.

All business logic (encoding the image, building the request, calling the
server) lives in :class:`models.ocr_model.OCRModel`, driven by
:class:`controllers.picture_to_text_controller.PictureToTextController`.
"""

import threading
import tkinter as tk
from tkinter import filedialog
from typing import List, Optional

import customtkinter as ctk

from config import LLM_WEBHOOK_URL, LLM_MODEL, LLM_PROVIDER, PROVIDER_CONFIG
from models.llm_client.discovery import discover_models, ModelOption
from views.base_tab import CTkBaseTab
from views.ctk_compat import CTkSection, CTkCollapsibleSection
from utils.logger import logger
from utils.i18n import t

# Semantic colours for the connection dot, as (light, dark) pairs.
_STATUS_COLORS = {
    "ok": ("#15803d", "#4ade80"),
    "error": ("#b91c1c", "#f87171"),
    "pending": ("#b45309", "#fbbf24"),
}

# File dialog filter for supported image inputs.
_IMAGE_FILETYPES = [
    ("Images", "*.png *.jpg *.jpeg *.gif *.bmp *.webp *.tif *.tiff"),
    ("All files", "*.*"),
]

# Largest preview thumbnail (keeps the UI tidy regardless of source size).
_PREVIEW_MAX = (320, 320)


class PictureToTextTab(CTkBaseTab):
    """Picture-to-text (OCR) workflow UI (pure view, no business logic)."""

    def __init__(self, notebook):
        self.notebook = notebook

        # UI state
        self.image_path_var = tk.StringVar(value=t("picture_to_text.no_image"))
        self.is_extracting = tk.BooleanVar(value=False)

        # LLM / provider settings (same ids as the other tabs)
        self.provider_var = tk.StringVar(value=LLM_PROVIDER or "lmstudio")
        self.webhook_var = tk.StringVar(value=LLM_WEBHOOK_URL or "http://127.0.0.1:1234/v1")
        self.model_var = tk.StringVar(value=LLM_MODEL or "local-model")
        self.models_status = tk.StringVar(value="")
        self.available_models: List[ModelOption] = []

        # label <-> id maps for the model dropdown
        self._model_id_mapping = {}       # label -> id
        self._model_display_mapping = {}  # id -> label
        self.status_indicator = None

        # The absolute image path (image_path_var holds a friendly display).
        self._selected_image_path: Optional[str] = None
        # Held references so Tk does not garbage-collect the preview image.
        self._preview_image = None

        # Callbacks wired by the controller
        self.on_image_selected = None
        self.on_extract_clicked = None
        self.on_clear_clicked = None

        super().__init__(notebook, "🖼 " + t("picture_to_text.title"))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """
        Build the OCR UI.

        Layout (inside self.body, the scroll-when-needed area):
            0  image picker + preview card
            1  LLM settings (collapsible)
            2  prompt card
            3  extracted-text pane   <- expanding region
            4  action bar
        """
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(3, weight=1)

        self._setup_image_section()
        self._setup_llm_settings_section()
        self._setup_prompt_section()
        self._setup_output_section()
        self._setup_action_bar()

        # Discover models once the UI exists.
        self.after(100, self._discover_models)

    def _setup_image_section(self):
        """Image picker with a preview thumbnail."""
        section = CTkSection(self.body, title=t("picture_to_text.frame.image"))
        section.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        body = section.body
        body.grid_columnconfigure(1, weight=1)

        self.image_btn = ctk.CTkButton(
            body,
            text=t("picture_to_text.btn.browse"),
            command=self._browse_image,
            width=130,
            height=34,
        )
        self.image_btn.grid(row=0, column=0, padx=(0, 8), sticky="w")

        ctk.CTkLabel(
            body,
            textvariable=self.image_path_var,
            anchor="w",
            fg_color=("gray88", "gray24"),
            corner_radius=8,
            height=34,
            padx=10,
        ).grid(row=0, column=1, sticky="ew")

        # Preview area — placeholder text until an image loads.
        self.preview_label = ctk.CTkLabel(
            body,
            text=t("picture_to_text.preview.empty"),
            width=_PREVIEW_MAX[0],
            height=180,
            fg_color=("gray92", "gray20"),
            corner_radius=8,
            text_color=("gray45", "gray60"),
        )
        self.preview_label._font_skip = True  # image host, not scalable text
        self.preview_label.grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )

    def _setup_llm_settings_section(self):
        """Provider / endpoint / model, folded away by default."""
        section = CTkCollapsibleSection(
            self.body, title=t("picture_to_text.lbl.provider"), expanded=True
        )
        section.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        body = section.body
        body.grid_columnconfigure(1, weight=1)

        # --- Provider ---
        row = 0
        provider_frame = ctk.CTkFrame(body, fg_color="transparent")
        provider_frame.grid(row=row, column=0, columnspan=4, sticky="w")

        self._provider_labels = {
            "LM Studio": "lmstudio",
            "Unsloth Local": "unsloth",
            "Ollama Local": "ollama-local",
        }
        self._provider_values = {v: k for k, v in self._provider_labels.items()}

        self.provider_selector = ctk.CTkSegmentedButton(
            provider_frame,
            values=list(self._provider_labels.keys()),
            command=self._on_provider_selected,
            height=32,
            font=ctk.CTkFont(size=13),
        )
        self.provider_selector.grid(row=0, column=0, sticky="w")
        self.provider_selector.set(
            self._provider_values.get(self.provider_var.get(), "LM Studio")
        )

        # --- Connection status ---
        row += 1
        status_frame = ctk.CTkFrame(body, fg_color="transparent")
        status_frame.grid(row=row, column=0, columnspan=4, sticky="w", pady=(8, 0))

        self.status_indicator = ctk.CTkLabel(status_frame, text="●", width=14)
        self.status_indicator._theme_skip = True
        self.status_indicator._font_skip = True
        self.status_indicator.grid(row=0, column=0, padx=(0, 5))

        self.status_label_llm = ctk.CTkLabel(
            status_frame, textvariable=self.models_status, anchor="w"
        )
        self.status_label_llm.grid(row=0, column=1, sticky="w")

        # --- Base URL ---
        row += 1
        ctk.CTkLabel(
            body, text=t("picture_to_text.lbl.base_url"), text_color=("gray40", "gray65")
        ).grid(row=row, column=0, sticky="w", pady=(10, 0))

        self.webhook_entry = ctk.CTkEntry(body, textvariable=self.webhook_var, height=32)
        self.webhook_entry.grid(row=row, column=1, sticky="ew", padx=8, pady=(10, 0))
        self._register_entry_context_menu(self.webhook_entry)

        ctk.CTkButton(
            body,
            text=t("picture_to_text.btn.test"),
            command=self._test_connection,
            width=70,
            height=32,
        ).grid(row=row, column=2, padx=(0, 8), pady=(10, 0))

        # --- Model ---
        row += 1
        ctk.CTkLabel(
            body, text=t("picture_to_text.lbl.model"), text_color=("gray40", "gray65")
        ).grid(row=row, column=0, sticky="w", pady=(10, 0))

        self.model_combo = ctk.CTkOptionMenu(
            body, values=[], command=self._on_model_selected, height=32
        )
        self.model_combo.grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=8, pady=(10, 0)
        )
        if self.model_var.get():
            self.model_combo.set(self.model_var.get())

        ctk.CTkLabel(
            body,
            text=t("picture_to_text.lbl.model_hint"),
            text_color=("gray45", "gray60"),
            wraplength=560,
            justify="left",
        ).grid(row=row + 1, column=0, columnspan=4, sticky="w", pady=(6, 0))

    def _setup_prompt_section(self):
        """Editable instruction prompt sent with the image."""
        section = CTkCollapsibleSection(
            self.body, title=t("picture_to_text.lbl.prompt"), expanded=False
        )
        section.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        body = section.body
        body.grid_columnconfigure(0, weight=1)

        self.prompt_text = ctk.CTkTextbox(
            body, wrap="word", height=90, font=("Cascadia Mono", 12), corner_radius=8
        )
        self.prompt_text.grid(row=0, column=0, sticky="ew")
        self.prompt_text.insert("1.0", t("picture_to_text.prompt.default"))

        self._register_context_menu(
            self.prompt_text,
            [{"copy": True}, {"paste": True}],
        )

    def _setup_output_section(self):
        """Extracted-text pane."""
        section = CTkSection(
            self.body, title=t("picture_to_text.frame.output"), padding=10
        )
        section.grid(row=3, column=0, sticky="nsew")
        section.body.grid_rowconfigure(0, weight=1)
        section.body.grid_columnconfigure(0, weight=1)

        self.output_text = ctk.CTkTextbox(
            section.body,
            wrap="word",
            font=("Cascadia Mono", 12),
            activate_scrollbars=True,
            corner_radius=8,
        )
        self.output_text.grid(row=0, column=0, sticky="nsew")

        self._register_context_menu(
            self.output_text,
            [
                {"copy": True},
                {"paste": True},
                {"separator": True},
                {"tts_read": lambda: self._selection_or_all(self.output_text)},
                {"tts_stop": True},
                {"separator": True},
                {"fullscreen": True, "title": t("picture_to_text.frame.output"),
                 "editable": True},
            ],
        )

    def _setup_action_bar(self):
        """Primary action, progress and status."""
        action_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        action_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        action_frame.grid_columnconfigure(2, weight=1)

        self.extract_btn = ctk.CTkButton(
            action_frame,
            text=t("picture_to_text.btn.extract"),
            command=self._start_extraction,
            width=170,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.extract_btn.grid(row=0, column=0, padx=(0, 10))

        self.clear_btn = ctk.CTkButton(
            action_frame,
            text=t("common.clear"),
            command=self._clear_clicked,
            width=110,
            height=38,
            corner_radius=8,
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray30", "gray80"),
            hover_color=("gray85", "gray28"),
        )
        self.clear_btn.grid(row=0, column=1, padx=(0, 10))

        self.status_label = ctk.CTkLabel(
            action_frame, text="", anchor="w", text_color=("gray35", "gray70")
        )
        self.status_label.grid(row=0, column=2, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(
            action_frame, mode="indeterminate", height=6, width=160
        )
        self.progress_bar.grid(row=0, column=3, padx=(10, 0))
        self.progress_bar.grid_remove()

    # ------------------------------------------------------------------
    # View methods (called by controller)
    # ------------------------------------------------------------------

    def set_image_path(self, file_path: str):
        """Record the selected image path and refresh the preview."""
        self._selected_image_path = file_path or None
        self.image_path_var.set(file_path or t("picture_to_text.no_image"))
        self._update_preview(file_path)

    def set_output_text(self, text: str):
        """Replace the extracted-text pane content."""
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, text or "")

    def set_status(self, message: str):
        """Set the inline status message."""
        self.status_label.configure(text=message)

    def set_extracting_state(self, is_extracting: bool):
        """Toggle controls and the progress bar during extraction."""
        self.is_extracting.set(is_extracting)
        if is_extracting:
            self.extract_btn.configure(state="disabled")
            self.image_btn.configure(state="disabled")
            self.progress_bar.grid()
            self.progress_bar.start()
        else:
            self.extract_btn.configure(state="normal")
            self.image_btn.configure(state="normal")
            self.progress_bar.stop()
            self.progress_bar.grid_remove()

    def get_extracting_state(self) -> bool:
        return self.is_extracting.get()

    def show_error(self, message: str):
        """Show an error in the output pane and log it."""
        logger.error(f"[{self.tab_name}] Error: {message}")
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, f"Error: {message}")

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _update_preview(self, file_path: str):
        """Render a thumbnail of the chosen image, or restore the placeholder."""
        if not file_path:
            self._preview_image = None
            self.preview_label.configure(
                image=None, text=t("picture_to_text.preview.empty")
            )
            return

        try:
            from PIL import Image

            with Image.open(file_path) as img:
                img = img.convert("RGB")
                img.thumbnail(_PREVIEW_MAX)
                size = img.size
                self._preview_image = ctk.CTkImage(
                    light_image=img, dark_image=img, size=size
                )
            self.preview_label.configure(image=self._preview_image, text="")
        except Exception as exc:
            # A failed preview must not block extraction; the server reads the
            # file itself. Just show why the thumbnail is missing.
            logger.debug(f"Could not render image preview: {exc}", exc_info=True)
            self._preview_image = None
            self.preview_label.configure(
                image=None, text=t("picture_to_text.preview.failed")
            )

    # ------------------------------------------------------------------
    # Callback methods (trigger controller)
    # ------------------------------------------------------------------

    def _browse_image(self):
        if self.is_extracting.get():
            return
        file_path = filedialog.askopenfilename(
            title=t("picture_to_text.dialog.select_image"),
            filetypes=_IMAGE_FILETYPES,
        )
        if file_path and self.on_image_selected:
            self.on_image_selected(file_path)

    def _start_extraction(self):
        if self.on_extract_clicked:
            self.on_extract_clicked()

    def _clear_clicked(self):
        if self.on_clear_clicked:
            self.on_clear_clicked()
        else:
            self.clear_all()

    # --- provider / model controls (same behaviour as Translation tab) ---

    def _on_provider_selected(self, label: str):
        provider = self._provider_labels.get(label)
        if provider and provider != self.provider_var.get():
            self.provider_var.set(provider)
            self._on_provider_changed()

    def _on_provider_changed(self):
        provider = self.provider_var.get()
        config = PROVIDER_CONFIG.get(provider)
        if config:
            self.webhook_var.set(config["default_base_url"])
            self.model_var.set("")
            self.model_combo.configure(values=[])
            self.model_combo.set("")
            self._discover_models()

    def _test_connection(self):
        self._discover_models()

    def _set_status_dot(self, state: str):
        if self.status_indicator is not None:
            self.status_indicator.configure(
                text_color=_STATUS_COLORS.get(state, _STATUS_COLORS["pending"])
            )

    def _discover_models(self):
        provider = self.provider_var.get()
        base_url = self.webhook_var.get().strip()

        if not provider or not base_url:
            self.models_status.set(t("picture_to_text.status.need_provider"))
            self._set_status_dot("error")
            return

        self.models_status.set(t("picture_to_text.status.connecting"))
        self._set_status_dot("pending")
        self.update_idletasks()

        def discovery_task():
            try:
                models, status, error = discover_models(provider, base_url)
                self.after(0, lambda: self._update_models_ui(models, status, error))
            except Exception as e:
                self.after(0, lambda: self._update_models_ui([], "error", str(e)))

        threading.Thread(target=discovery_task, daemon=True).start()

    def _update_models_ui(self, models, status, error):
        self.available_models = models

        if status == "ok":
            self.models_status.set(t("picture_to_text.status.connected"))
            self._set_status_dot("ok")
        elif status == "error":
            self.models_status.set(t("picture_to_text.status.unreachable"))
            self._set_status_dot("error")
        else:
            self.models_status.set(t("picture_to_text.status.connecting"))
            self._set_status_dot("pending")

        if models:
            self._model_id_mapping = {m["label"]: m["id"] for m in models}
            self._model_display_mapping = {m["id"]: m["label"] for m in models}

            model_labels = [m["label"] for m in models]
            self.model_combo.configure(values=model_labels)

            current_id = self.model_var.get()
            if not current_id:
                self.model_var.set(models[0]["id"])
                self.model_combo.set(models[0]["label"])
            else:
                self.model_combo.set(
                    self._model_display_mapping.get(current_id, current_id)
                )
        else:
            self.model_combo.configure(values=[])
            self.model_combo.set("")
            self.model_var.set("")

    def _on_model_selected(self, selected_label: str):
        selected_label = (selected_label or "").strip()
        if not selected_label:
            return
        if selected_label in self._model_id_mapping:
            model_id = self._model_id_mapping[selected_label]
            logger.info(f"Converted model label to ID: '{selected_label}' -> '{model_id}'")
            self.model_var.set(model_id)
        else:
            self.model_var.set(selected_label)

    # ------------------------------------------------------------------
    # Getters (used by controller)
    # ------------------------------------------------------------------

    def get_image_path(self) -> Optional[str]:
        return self._selected_image_path

    def get_provider(self) -> str:
        return self.provider_var.get()

    def get_webhook_url(self) -> str:
        return self.webhook_var.get().strip()

    def get_model_name(self) -> str:
        return self.model_var.get().strip()

    def get_prompt(self) -> str:
        return self.prompt_text.get("1.0", tk.END).strip()

    # ------------------------------------------------------------------
    # CTkBaseTab abstract method implementations
    # ------------------------------------------------------------------

    def get_content(self) -> str:
        """Return the extracted text."""
        return self.output_text.get("1.0", tk.END).strip()

    def clear_all(self):
        """Clear the image, preview and output."""
        self.output_text.delete("1.0", tk.END)
        self.set_image_path("")
        self.set_status("")

    # ------------------------------------------------------------------
    # Theming hook used by MainWindow
    # ------------------------------------------------------------------

    def apply_font_size(self, size: int):
        """Scale the monospace text panes with the app-wide font size."""
        from views.ctk_theme import font_sizes
        mono = font_sizes(size)["mono"]
        self.output_text.configure(font=("Cascadia Mono", mono))
        self.prompt_text.configure(font=("Cascadia Mono", mono))
