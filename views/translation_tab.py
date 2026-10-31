"""
Translation Tab - UI for translation workflows (v7.0, CustomTkinter)

Pure View component following MVC pattern.

Responsibilities:
    - UI layout and widgets
    - Display data from controller
    - Emit events/callbacks to controller
    - No business logic or direct API calls

Updated: 2026-10-30 (v7.0 - Migrated from ttk to CustomTkinter with the
    card-based responsive layout used by the Summarizer tab. The public
    interface consumed by TranslationController is unchanged.)

Fixes folded into this migration (all pre-existing):
    - ``set_webhook_url`` / the first ``get_webhook_url`` referenced
      ``self.webhook_url``, which never existed (the variable is
      ``webhook_var``), so calling them raised AttributeError. There were also
      two ``get_webhook_url`` definitions, the second silently shadowing the
      first.
    - "Forward to summarization" targeted ``main_window.youtube_summarizer_tab``,
      a tab that no longer exists, so it always fell through to the "copy it
      yourself" fallback. It now targets the current Summarizer tab. The
      unreachable duplicate block after that branch is gone.
"""

import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List

import customtkinter as ctk

from config import LLM_WEBHOOK_URL, LLM_MODEL, LLM_PROVIDER, PROVIDER_CONFIG
from models.llm_client.discovery import discover_models, ModelOption
from views.base_tab import CTkBaseTab
from views.ctk_compat import CTkSection, CTkCollapsibleSection, CTkSplitter
from utils.logger import logger
from utils.i18n import t

# Semantic colours for the connection dot, as (light, dark) pairs.
_STATUS_COLORS = {
    "ok": ("#15803d", "#4ade80"),
    "error": ("#b91c1c", "#f87171"),
    "pending": ("#b45309", "#fbbf24"),
}


class TranslationTab(CTkBaseTab):
    """Translation workflow UI (pure view, no business logic)."""

    def __init__(self, notebook):
        self.notebook = notebook

        # State variables (UI state only)
        self.source_file_path = tk.StringVar(value=t("translation.no_file"))
        self.target_language = tk.StringVar(value="Croatian")
        self.is_translating = tk.BooleanVar(value=False)

        # LLM Settings
        self.provider_var = tk.StringVar(value=LLM_PROVIDER or "lmstudio")
        self.webhook_var = tk.StringVar(value=LLM_WEBHOOK_URL or "http://127.0.0.1:1234/v1")
        self.model_var = tk.StringVar(value=LLM_MODEL or "local-model")
        self.save_settings_var = tk.BooleanVar(value=True)
        self.models_status = tk.StringVar(value="")
        self.available_models: List[ModelOption] = []

        # Clean up any existing corrupted model name from .env
        self._cleanup_model_name()

        # Model ID to label mapping for display purposes
        self._model_id_mapping = {}  # label -> id
        self._model_display_mapping = {}  # id -> label
        self.status_indicator = None

        # Callback properties - will be wired by controller
        self.on_file_selected = None
        self.on_translate_clicked = None
        self.on_restore_default_webhook = None
        self.on_clear_clicked = None

        super().__init__(notebook, "🌐 Translation")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """
        Build the translation UI.

        Layout:
            0  input card (file + target language)
            1  LLM settings (collapsible)
            2  source / translation split  <- expanding region
            3  action bar
        """
        # Content goes in self.body (the scroll-when-needed area from
        # CTkBaseTab), not self, so short windows can still reach everything.
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(2, weight=1)

        self._setup_input_section()
        self._setup_llm_settings_section()
        self._setup_panes_section()
        self._setup_action_bar()

        # Trigger automatic model discovery after UI is set up
        self.after(100, self._discover_models)

    def _setup_input_section(self):
        """File picker and target language."""
        section = CTkSection(self.body, title=t("translation.frame.source"))
        section.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._input_section = section
        body = section.body
        body.grid_columnconfigure(1, weight=1)

        self.file_btn = ctk.CTkButton(
            body,
            text=t("translation.btn.browse"),
            command=self._browse_file,
            width=110,
            height=34,
        )
        self.file_btn.grid(row=0, column=0, padx=(0, 8))

        # Full-width path display so long paths stay readable.
        ctk.CTkLabel(
            body,
            textvariable=self.source_file_path,
            anchor="w",
            fg_color=("gray88", "gray24"),
            corner_radius=8,
            height=34,
            padx=10,
        ).grid(row=0, column=1, sticky="ew")

        lang_row = ctk.CTkFrame(body, fg_color="transparent")
        lang_row.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        ctk.CTkLabel(
            lang_row,
            text=t("translation.lbl.translate_to"),
            text_color=("gray40", "gray65"),
        ).grid(row=0, column=0, padx=(0, 8))

        # Editable combo box: the preset list is a convenience, not a limit.
        self.language_dropdown = ctk.CTkComboBox(
            lang_row,
            variable=self.target_language,
            values=["Croatian", "Deutsch", "English", "Italian", "Spanish"],
            width=180,
            height=32,
        )
        self.language_dropdown.grid(row=0, column=1)

    def _setup_llm_settings_section(self):
        """LLM provider / endpoint / model, folded away by default."""
        section = CTkCollapsibleSection(
            self.body, title=t("translation.lbl.provider"), expanded=False
        )
        section.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self._llm_section = section
        body = section.body
        body.grid_columnconfigure(1, weight=1)

        # --- Provider ---
        row = 0
        provider_frame = ctk.CTkFrame(body, fg_color="transparent")
        provider_frame.grid(row=row, column=0, columnspan=4, sticky="w")

        self._provider_labels = {"LM Studio": "lmstudio", "Ollama Local": "ollama-local"}
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

        # Semantic colour, so it opts out of the accent palette pass.
        self.status_indicator = ctk.CTkLabel(status_frame, text="●", width=14)
        self.status_indicator._theme_skip = True
        self.status_indicator._font_skip = True  # glyph, not text
        self.status_indicator.grid(row=0, column=0, padx=(0, 5))

        self.status_label_llm = ctk.CTkLabel(
            status_frame, textvariable=self.models_status, anchor="w"
        )
        self.status_label_llm.grid(row=0, column=1, sticky="w")

        # --- Base URL ---
        row += 1
        ctk.CTkLabel(
            body, text=t("translation.lbl.base_url"), text_color=("gray40", "gray65")
        ).grid(row=row, column=0, sticky="w", pady=(10, 0))

        self.webhook_entry = ctk.CTkEntry(body, textvariable=self.webhook_var, height=32)
        self.webhook_entry.grid(row=row, column=1, sticky="ew", padx=8, pady=(10, 0))
        self._register_entry_context_menu(self.webhook_entry)

        ctk.CTkButton(
            body,
            text=t("translation.btn.test"),
            command=self._test_connection,
            width=70,
            height=32,
        ).grid(row=row, column=2, padx=(0, 8), pady=(10, 0))

        ctk.CTkCheckBox(
            body,
            text=t("translation.chk.remember"),
            variable=self.save_settings_var,
            checkbox_width=18,
            checkbox_height=18,
        ).grid(row=row, column=3, sticky="w", pady=(10, 0))

        # --- Model ---
        row += 1
        ctk.CTkLabel(
            body, text=t("translation.lbl.model"), text_color=("gray40", "gray65")
        ).grid(row=row, column=0, sticky="w", pady=(10, 0))

        self.model_combo = ctk.CTkOptionMenu(
            body, values=[], command=self._on_model_selected, height=32
        )
        self.model_combo.grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=8, pady=(10, 0)
        )
        if self.model_var.get():
            self.model_combo.set(self.model_var.get())

    def _setup_panes_section(self):
        """Source and translation side by side, with a draggable divider."""
        self._split = CTkSplitter(self.body, ratio=0.5)
        self._split.grid(row=2, column=0, sticky="nsew")

        # --- Source (left) ---
        source_section = CTkSection(
            self._split.left, title=t("translation.frame.source"), padding=10
        )
        source_section.grid(row=0, column=0, sticky="nsew")
        self._split.left.grid_rowconfigure(0, weight=1)
        self._split.left.grid_columnconfigure(0, weight=1)
        source_section.body.grid_rowconfigure(0, weight=1)
        self._source_section = source_section

        self.source_text = ctk.CTkTextbox(
            source_section.body,
            wrap="word",
            font=("Cascadia Mono", 12),
            activate_scrollbars=True,
            corner_radius=8,
        )
        self.source_text.grid(row=0, column=0, sticky="nsew")

        self._register_context_menu(
            self.source_text,
            [
                {"copy": True},
                {"paste": True},
                {"separator": True},
                {"tts_read": lambda: self._selection_or_all(self.source_text)},
                {"tts_stop": True},
                {"separator": True},
                {"fullscreen": True, "title": t("translation.frame.source"),
                 "editable": True},
            ],
        )

        # --- Translation (right) ---
        target_section = CTkSection(
            self._split.right, title=t("translation.frame.translation"), padding=10
        )
        target_section.grid(row=0, column=0, sticky="nsew")
        self._split.right.grid_rowconfigure(0, weight=1)
        self._split.right.grid_columnconfigure(0, weight=1)
        target_section.body.grid_rowconfigure(0, weight=1)
        self._target_section = target_section

        self.target_text = ctk.CTkTextbox(
            target_section.body,
            wrap="word",
            font=("Cascadia Mono", 12),
            activate_scrollbars=True,
            corner_radius=8,
        )
        self.target_text.grid(row=0, column=0, sticky="nsew")

        self._register_context_menu(
            self.target_text,
            [
                {"copy": True},
                {"paste": True},
                {"separator": True},
                {"label": t("translation.menu.export_txt"),
                 "command": self._export_translation_txt},
                {"label": t("translation.menu.export_srt"),
                 "command": self._export_translation_srt},
                {"separator": True},
                {"label": t("translation.menu.forward"),
                 "command": self._forward_to_summarization},
                {"separator": True},
                {"tts_read": lambda: self._selection_or_all(self.target_text)},
                {"tts_stop": True},
                {"separator": True},
                {"fullscreen": True, "title": t("translation.frame.translation"),
                 "editable": True},
            ],
        )

    def _setup_action_bar(self):
        """Primary action, progress and status."""
        action_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        action_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        action_frame.grid_columnconfigure(2, weight=1)

        self.translate_btn = ctk.CTkButton(
            action_frame,
            text=t("translation.btn.translate"),
            command=self._start_translation,
            width=170,
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.translate_btn.grid(row=0, column=0, padx=(0, 10))

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

        # Thin indeterminate bar, hidden until a translation runs.
        self.progress_bar = ctk.CTkProgressBar(
            action_frame, mode="indeterminate", height=6, width=160
        )
        self.progress_bar.grid(row=0, column=3, padx=(10, 0))
        self.progress_bar.grid_remove()

    # ------------------------------------------------------------------
    # View Methods (called by controller)
    # ------------------------------------------------------------------

    def set_file_path(self, file_path: str):
        """Set the file path display"""
        self.source_file_path.set(file_path or t("translation.no_file"))

    def set_source_text(self, text: str):
        """Set source text content"""
        self.source_text.delete("1.0", tk.END)
        self.source_text.insert(tk.END, text)

    def set_target_text(self, text: str):
        """Set translated text content"""
        self.target_text.delete("1.0", tk.END)
        self.target_text.insert(tk.END, text)

    def clear_target_text(self):
        """Clear translated text"""
        self.target_text.delete("1.0", tk.END)

    def set_webhook_url(self, url: str):
        """Set the LLM base URL."""
        self.webhook_var.set(url)

    def set_status(self, message: str):
        """Set status message"""
        self.status_label.configure(text=message)

    def set_translating_state(self, is_translating: bool):
        """Set translation state and update UI controls"""
        self.is_translating.set(is_translating)

        if is_translating:
            self.translate_btn.configure(state="disabled")
            self.file_btn.configure(state="disabled")
            self.progress_bar.grid()
            self.progress_bar.start()
        else:
            self.translate_btn.configure(state="normal")
            self.file_btn.configure(state="normal")
            self.progress_bar.stop()
            self.progress_bar.grid_remove()

    def get_translating_state(self) -> bool:
        """Get current translation state"""
        return self.is_translating.get()

    def show_error(self, message: str):
        """Show error message to user (in the translation pane)."""
        logger.error(f"[{self.tab_name}] Error: {message}")
        self.target_text.delete("1.0", tk.END)
        self.target_text.insert(tk.END, f"Error: {message}")

    # ------------------------------------------------------------------
    # Callback Methods (trigger controller)
    # ------------------------------------------------------------------

    def _browse_file(self):
        """Handle file browse button click - emit callback to controller"""
        if self.is_translating.get():
            return

        file_path = filedialog.askopenfilename(title=t("translation.dialog.select_file"))
        if file_path:
            if self.on_file_selected:
                self.on_file_selected(file_path)

    def _start_translation(self):
        """Handle translate button click - emit callback to controller"""
        if self.on_translate_clicked:
            self.on_translate_clicked()

    def _on_provider_selected(self, label: str):
        """Segmented-button handler for the provider choice."""
        provider = self._provider_labels.get(label)
        if provider and provider != self.provider_var.get():
            self.provider_var.set(provider)
            self._on_provider_changed()

    def _on_provider_changed(self):
        """Handle provider selection changes."""
        provider = self.provider_var.get()
        config = PROVIDER_CONFIG.get(provider)

        if config:
            # Update base URL to provider default
            self.webhook_var.set(config['default_base_url'])

            # Clear current model selection
            self.model_var.set("")
            self.model_combo.configure(values=[])
            self.model_combo.set("")

            # Trigger model discovery
            self._discover_models()

    def _test_connection(self):
        """Test connection to LLM server and discover models."""
        self._discover_models()

    def _set_status_dot(self, state: str):
        """Color the connection status dot: 'ok', 'error' or 'pending'."""
        if self.status_indicator is not None:
            self.status_indicator.configure(
                text_color=_STATUS_COLORS.get(state, _STATUS_COLORS["pending"])
            )

    def _discover_models(self):
        """Discover available models from current provider."""
        provider = self.provider_var.get()
        base_url = self.webhook_var.get().strip()

        if not provider or not base_url:
            self.models_status.set(t("translation.status.need_provider"))
            self._set_status_dot("error")
            return

        # Show loading state
        self.models_status.set(t("translation.status.connecting"))
        self._set_status_dot("pending")
        self.update_idletasks()

        # Run discovery in background to avoid UI freeze
        def discovery_task():
            try:
                models, status, error = discover_models(provider, base_url)
                self.after(0, lambda: self._update_models_ui(models, status, error))
            except Exception as e:
                self.after(0, lambda: self._update_models_ui([], 'error', str(e)))

        threading.Thread(target=discovery_task, daemon=True).start()

    def _update_models_ui(self, models, status, error):
        """Update UI with model discovery results."""
        self.available_models = models

        if status == 'ok':
            self.models_status.set(t("translation.status.connected"))
            self._set_status_dot("ok")
        elif status == 'error':
            self.models_status.set(t("translation.status.unreachable"))
            self._set_status_dot("error")
        else:
            self.models_status.set(t("translation.status.connecting"))
            self._set_status_dot("pending")

        # Update model dropdown
        if models:
            self._model_id_mapping = {m['label']: m['id'] for m in models}
            self._model_display_mapping = {m['id']: m['label'] for m in models}

            model_labels = [m['label'] for m in models]
            self.model_combo.configure(values=model_labels)

            current_id = self.model_var.get()
            if not current_id:
                self.model_var.set(models[0]['id'])
                self.model_combo.set(models[0]['label'])
            else:
                self.model_combo.set(
                    self._model_display_mapping.get(current_id, current_id)
                )
        else:
            self.model_combo.configure(values=[])
            self.model_combo.set("")
            self.model_var.set("")

    def _on_model_selected(self, selected_label: str):
        """
        Handle model selection from the dropdown.

        The dropdown shows friendly labels (``name (size)``) while the rest of
        the app needs the bare model ID, so translate before storing.
        """
        selected_label = (selected_label or "").strip()
        if not selected_label:
            return

        if selected_label in self._model_id_mapping:
            model_id = self._model_id_mapping[selected_label]
            logger.info(f"Converted model label to ID: '{selected_label}' -> '{model_id}'")
            self.model_var.set(model_id)
        else:
            self.model_var.set(selected_label)

    def _on_model_combobox_selected(self, event=None):
        """Backwards-compatible alias for the old Combobox event handler."""
        self._on_model_selected(self.model_combo.get())

    def _restore_default_webhook(self):
        """Handle restore default webhook button click - emit callback to controller"""
        if self.on_restore_default_webhook:
            self.on_restore_default_webhook()

    def _clear_clicked(self):
        """Handle clear button click - emit callback to controller"""
        if self.on_clear_clicked:
            self.on_clear_clicked()
        else:
            self.clear_all()

    # ------------------------------------------------------------------
    # Getter Methods (used by controller)
    # ------------------------------------------------------------------

    def get_source_text(self) -> str:
        """Get current source text content"""
        return self.source_text.get("1.0", tk.END).strip()

    def get_target_language(self) -> str:
        """Get selected target language"""
        return self.target_language.get()

    def get_file_path(self) -> str:
        """Get the current file path"""
        return self.source_file_path.get()

    def get_provider(self) -> str:
        """Get current provider."""
        return self.provider_var.get()

    def get_webhook_url(self) -> str:
        """Get current LLM base URL."""
        return self.webhook_var.get().strip()

    def get_model_name(self) -> str:
        """Get current model name."""
        return self.model_var.get().strip()

    def get_save_settings(self) -> bool:
        """Get save settings preference."""
        return self.save_settings_var.get()

    # ------------------------------------------------------------------
    # .env model-name cleanup
    # ------------------------------------------------------------------

    def _clean_env_file(self, old_value: str, new_value: str):
        """Clean up corrupted model name in .env file."""
        try:
            from pathlib import Path
            env_path = Path(__file__).parent.parent / '.env'

            if env_path.exists():
                content = env_path.read_text(encoding='utf-8')
                updated_content = content.replace(
                    f'LLM_MODEL={old_value}', f'LLM_MODEL={new_value}'
                )
                if updated_content != content:
                    env_path.write_text(updated_content, encoding='utf-8')
                    logger.info(
                        f"Cleaned .env file: LLM_MODEL updated from '{old_value}' to '{new_value}'"
                    )
        except Exception as e:
            logger.error(f"Failed to clean .env file: {e}")

    def _cleanup_model_name(self):
        """Clean up corrupted model names that may exist in .env file."""
        current_value = self.model_var.get().strip()
        if not current_value:
            return

        # Pattern: "model-name (size)" - strip the trailing size description
        match = re.match(r'^(.+?)\s+\([^)]+\)$', current_value)
        if match:
            clean_model_name = match.group(1)
            logger.info(
                f"Cleaned up corrupted model name: '{current_value}' -> '{clean_model_name}'"
            )
            self.model_var.set(clean_model_name)
            self._clean_env_file(current_value, clean_model_name)

    # ------------------------------------------------------------------
    # Export / forward actions
    # ------------------------------------------------------------------

    def _export_translation(self, extension: str, filetype_key: str, dialog_key: str,
                            saved_key: str):
        """Shared implementation for the .txt / .srt export menu items."""
        text_content = self.target_text.get("1.0", tk.END).strip()

        if not text_content:
            messagebox.showwarning(
                title=t("translation.msg.nothing_export_title"),
                message=t("translation.msg.empty_body"),
            )
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=extension,
            filetypes=[
                (t(filetype_key), f"*{extension}"),
                (t("translation.filetype.all"), "*.*"),
            ],
            title=t(dialog_key),
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text_content)
            messagebox.showinfo(
                title=t("translation.msg.exported_title"),
                message=t(saved_key).format(path=file_path),
            )
        except IOError as e:
            messagebox.showerror(
                title=t("translation.msg.export_failed_title"), message=str(e)
            )

    def _export_translation_txt(self):
        """Export translated text as .txt file via context menu."""
        self._export_translation(
            ".txt", "translation.filetype.text",
            "translation.dialog.export_txt", "translation.msg.saved_txt",
        )

    def _export_translation_srt(self):
        """Export translated text as .srt file via context menu."""
        self._export_translation(
            ".srt", "translation.filetype.srt",
            "translation.dialog.export_srt", "translation.msg.saved_srt",
        )

    def _forward_to_summarization(self):
        """
        Send the translated text to the Summarizer tab's content box.

        Previously this looked for ``youtube_summarizer_tab``, which was
        removed in v9.5, so the feature silently never worked and always fell
        back to "copy it yourself".
        """
        text_content = self.target_text.get("1.0", tk.END).strip()

        if not text_content:
            messagebox.showwarning(
                title=t("translation.msg.nothing_forward_title"),
                message=t("translation.msg.empty_body"),
            )
            return

        # Strip reasoning tags some local models emit, then collapse whitespace.
        cleaned_text = text_content.replace("<think>", "").replace("</think>", "")
        cleaned_text = " ".join(cleaned_text.split()).strip()

        main_window = self.get_main_window()
        summarizer = getattr(main_window, "summarizer_tab", None) if main_window else None

        if summarizer is not None and hasattr(summarizer, "set_content"):
            summarizer.set_content(cleaned_text)
            # Bring the destination into view so the result is obvious.
            try:
                main_window.notebook.select(summarizer)
            except Exception:
                logger.debug("Could not switch to the Summarizer tab", exc_info=True)
            messagebox.showinfo(
                title=t("translation.msg.forwarded_title"),
                message=t("translation.msg.forwarded_body").format(n=len(cleaned_text)),
            )
            return

        # Fallback: stash the text so get_forwarded_text() can retrieve it.
        self._forwarded_text = cleaned_text
        logger.warning("Summarizer tab unavailable; stored forwarded text instead")
        messagebox.showinfo(
            title=t("translation.msg.ready_forward_title"),
            message=t("translation.msg.ready_forward_body"),
        )

    # ------------------------------------------------------------------
    # CTkBaseTab abstract method implementations
    # ------------------------------------------------------------------

    def get_content(self) -> str:
        """Return the current source text content."""
        return self.get_source_text()

    def clear_all(self):
        """Clear source/target text and reset file path."""
        self.source_text.delete("1.0", tk.END)
        self.target_text.delete("1.0", tk.END)
        self.source_file_path.set(t("translation.no_file"))
        self.set_status("")

    # ------------------------------------------------------------------
    # Theming hook used by MainWindow
    # ------------------------------------------------------------------

    def apply_font_size(self, size: int):
        """
        Apply the app-wide font size to this tab's text panes.

        Labels, controls and section headings are scaled centrally by
        :func:`views.ctk_theme.apply_font_scale`.
        """
        from views.ctk_theme import font_sizes
        mono = font_sizes(size)["mono"]
        self.source_text.configure(font=("Cascadia Mono", mono))
        self.target_text.configure(font=("Cascadia Mono", mono))
