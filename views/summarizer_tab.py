"""
Summarizer Tab - Unified File and YouTube Summarization Interface

Replaces file_tab.py and youtube_summarizer_tab.py with a single tab that handles
both file and YouTube input modes and sends directly to any OpenAI-compatible
LLM webhook (LM Studio, Ollama, vLLM, etc.) without going through n8n.

Features:
- Dual input modes: File upload or YouTube URL
- Direct LLM webhook integration (no n8n dependency)
- Prompt preset selection with custom editing
- Content preview and response display
- Export functionality (txt, docx, copy)
- Configuration persistence to .env
- Progress indicators and status updates

Version: 1.0
Created: 2026-05-06
"""

import os
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
from typing import Optional, Dict, Any, List

from config import LLM_WEBHOOK_URL, LLM_MODEL, LLM_PROVIDER, PROVIDER_CONFIG
from utils.prompt_presets import PROMPT_PRESETS, PRESET_NAMES, DEFAULT_PROMPT_KEY
from utils.prompt_manager import PromptManager
from utils.logger import logger
from models.llm_client.discovery import discover_models, Provider, ModelOption
from views.base_tab import BaseTab


class SummarizerTab(BaseTab):
    """
    Unified summarizer tab that replaces file_tab.py and youtube_summarizer_tab.py.
    
    Handles both file and YouTube input modes and sends content directly to
    OpenAI-compatible LLM webhooks instead of using n8n workflows.
    """
    
    def __init__(self, parent, prompt_manager=None, settings_manager=None):
        """
        Initialize Summarizer tab.

        Args:
            parent: Parent widget (ttk.Notebook)
            prompt_manager: Optional PromptManager instance for managing prompts
            settings_manager: Optional SettingsManager instance for persistent preferences
        """
        # Initialize variables BEFORE calling super().__init__()
        # Input mode
        self.input_mode_var = tk.StringVar(value="file")  # "file" or "youtube"
        
        # File mode state
        self.file_path_var = tk.StringVar(value="No file selected")
        self.current_file_directory = None
        self.current_file_basename = None
        
        # YouTube mode state
        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value=".txt")
        
        # LLM settings
        self.provider_var = tk.StringVar(value=LLM_PROVIDER or "lmstudio")
        self.webhook_var = tk.StringVar(value=LLM_WEBHOOK_URL or "http://127.0.0.1:1234/v1")
        self.model_var = tk.StringVar(value=LLM_MODEL or "local-model")
        self.save_settings_var = tk.BooleanVar(value=True)  # Changed to True for automatic saving
        
        # Clean up any existing corrupted model name from .env
        self._cleanup_model_name()
        
        # Model discovery state
        self.available_models: List[ModelOption] = []
        self.models_status = tk.StringVar(value="")
        self.models_error = tk.StringVar(value="")
        self.status_indicator = None  # Will be set in _setup_ui
        
        # Model ID to label mapping for display purposes
        self._model_id_mapping = {}  # label -> id
        self._model_display_mapping = {}  # id -> label
        
        # Prompt management
        self.prompt_manager = prompt_manager
        self._last_valid_preset = DEFAULT_PROMPT_KEY
        
        # Settings management
        self.settings = settings_manager

        # Initialize model discovery on first load
        # Note: We'll call this after UI is fully set up

        # Prompt
        self.prompt_preset_var = tk.StringVar(value=DEFAULT_PROMPT_KEY)
        # self.prompt_text widget created in _setup_ui
        
        # Export preferences
        self.use_original_location_var = tk.BooleanVar(value=False)
        self.auto_export_txt_var = tk.BooleanVar(value=False)
        self.auto_export_docx_var = tk.BooleanVar(value=False)
        
        # Loading state
        self._loading = False
        
        # Call parent init (triggers _setup_ui)
        super().__init__(parent, "📝 Summarizer")
        
        # Callbacks set by controller
        self.on_file_selected = None
        self.on_send_clicked = None
        self.on_export_txt = None
        self.on_export_docx = None
        self.on_copy_clicked = None
        self.on_clear_clicked = None
        # Called with the response text when "Send to Translation tab" is picked.
        # Wired in main.py to set the Translation tab's source box and switch tabs.
        self.on_send_to_translation = None
        
        logger.info("SummarizerTab initialized - unified file/YouTube summarization with LLM")
    
    def _setup_ui(self):
        """Setup the complete UI with all sections."""
        # Configure row weights
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)  # Content/response section expands
        
        # Setup sections in order
        self._setup_input_section()             # row=0, column=0
        self._setup_file_info_section()         # row=0, column=1
        self._setup_settings_section()          # row=1, column=0, columnspan=2
        self._setup_content_response_section()  # row=2 (weight=1), column=0, columnspan=2
        self._setup_action_bar()                # row=3, column=0, columnspan=2
        
        # Initialize mode visibility
        self._on_mode_changed()
        
        # Trigger initial model discovery
        self.after(100, self._discover_models)
        
        logger.debug("SummarizerTab UI setup complete")
    
    def _setup_input_section(self):
        """Setup input section with file/YouTube mode selection."""
        input_frame = ttk.LabelFrame(self, text="Input", padding="10")
        input_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Mode selection radio buttons
        mode_frame = ttk.Frame(input_frame)
        mode_frame.grid(row=0, column=0, sticky="w", pady=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="📄 File",
            value="file",
            variable=self.input_mode_var,
            command=self._on_mode_changed
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            mode_frame,
            text="🎬 Video URL",
            value="youtube",
            variable=self.input_mode_var,
            command=self._on_mode_changed
        ).pack(side=tk.LEFT, padx=5)
        
        # File mode frame
        self._file_frame = ttk.Frame(input_frame)
        file_row = 1
        
        ttk.Label(self._file_frame, text="File:").grid(row=file_row, column=0, sticky="w")
        ttk.Label(
            self._file_frame,
            textvariable=self.file_path_var,
            relief="sunken",
            anchor="w"
        ).grid(row=file_row, column=1, sticky="ew", padx=5)
        
        ttk.Button(
            self._file_frame,
            text="Browse…",
            command=self._browse_file
        ).grid(row=file_row, column=2, padx=5)
        
        self._file_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        # YouTube mode frame
        self._youtube_frame = ttk.Frame(input_frame)
        youtube_row = 1
        
        ttk.Label(self._youtube_frame, text="URL:").grid(row=youtube_row, column=0, sticky="w")
        self.url_entry = ttk.Entry(
            self._youtube_frame,
            textvariable=self.url_var,
            width=50  # Make wider like other tabs
        )
        self.url_entry.grid(row=youtube_row, column=1, sticky=(tk.W, tk.E), padx=5)
        self.url_var.set("https://")
        self._register_entry_context_menu(self.url_entry)
        
        youtube_row += 1
        ttk.Label(self._youtube_frame, text="Format:").grid(row=youtube_row, column=0, sticky="w")
        format_combo = ttk.Combobox(
            self._youtube_frame,
            textvariable=self.format_var,
            values=[".txt", ".srt", ".vtt", ".json"],
            state="readonly",
            width=8
        )
        format_combo.grid(row=youtube_row, column=1, sticky="w", padx=5)

        youtube_row += 1
        self.force_retranscribe_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self._youtube_frame,
            text="Force re-transcribe (ignore loaded content)",
            variable=self.force_retranscribe_var
        ).grid(row=youtube_row, column=1, sticky="w", padx=5)

        self._youtube_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        # Configure column weights
        input_frame.columnconfigure(1, weight=1)
    
    def _on_mode_changed(self):
        """Handle input mode changes (file ↔ YouTube)."""
        if self.input_mode_var.get() == "file":
            self._file_frame.grid()
            self._youtube_frame.grid_remove()
            self.file_info_frame.grid()
        else:
            self._youtube_frame.grid()
            self._file_frame.grid_remove()
            self.file_info_frame.grid_remove()
        
        logger.debug(f"Input mode changed to: {self.input_mode_var.get()}")
    
    def _setup_settings_section(self):
        """Setup LLM settings section."""
        settings_frame = ttk.LabelFrame(self, text="Summarizer Settings", padding="10")
        settings_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        settings_frame.columnconfigure(1, weight=1)
        
        # Provider selection
        row = 0
        ttk.Label(settings_frame, text="Provider:").grid(row=row, column=0, sticky="w")
        
        provider_frame = ttk.Frame(settings_frame)
        provider_frame.grid(row=row, column=1, sticky="w")
        
        ttk.Radiobutton(
            provider_frame,
            text="LM Studio",
            value="lmstudio",
            variable=self.provider_var,
            command=self._on_provider_changed
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(
            provider_frame,
            text="Ollama Local",
            value="ollama-local",
            variable=self.provider_var,
            command=self._on_provider_changed
        ).pack(side=tk.LEFT, padx=5)
        
        # Status indicator
        row += 1
        status_frame = ttk.Frame(settings_frame)
        status_frame.grid(row=row, column=0, columnspan=3, sticky="w")
        
        self.status_indicator = ttk.Label(status_frame, text="●", font=("Segoe UI", 10))
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_label = ttk.Label(status_frame, textvariable=self.models_status)
        self.status_label.pack(side=tk.LEFT)
        
        # Base URL
        row += 1
        ttk.Label(settings_frame, text="Base URL:").grid(row=row, column=0, sticky="w")
        self.webhook_entry = ttk.Entry(
            settings_frame,
            textvariable=self.webhook_var
        )
        self.webhook_entry.grid(row=row, column=1, sticky="ew", padx=5)
        self._register_entry_context_menu(self.webhook_entry)
        
        # Test connection button
        ttk.Button(
            settings_frame,
            text="Test",
            command=self._test_connection,
            width=6
        ).grid(row=row, column=2, padx=5)
        
        ttk.Checkbutton(
            settings_frame,
            text="Remember settings",
            variable=self.save_settings_var
        ).grid(row=row, column=3, sticky="w", padx=5)
        
        # Model name (changed to combobox)
        row += 1
        ttk.Label(settings_frame, text="Model:").grid(row=row, column=0, sticky="w")
        self.model_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.model_var,
            state="readonly",
            width=30  # Set moderate width for model names
        )
        self.model_combo.grid(row=row, column=1, sticky="ew", padx=5)
        
        # Prompt preset
        row += 1
        ttk.Label(settings_frame, text="Prompt Preset:").grid(row=row, column=0, sticky="w")
        self.prompt_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.prompt_preset_var,
            state="readonly",
            width=30
        )
        self.prompt_combo.grid(row=row, column=1, sticky="w", padx=5)
        self.prompt_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)
        self.prompt_combo.bind("<Button-3>", self._on_preset_combo_rightclick)
        self._last_valid_preset = DEFAULT_PROMPT_KEY

        # Visible delete button for custom presets (enabled only when a custom preset is selected)
        self.delete_preset_btn = ttk.Button(
            settings_frame, text="🗑", width=3, command=self._delete_custom_prompt
        )
        self.delete_preset_btn.grid(row=row, column=2, sticky="w", padx=(0, 5))
        # Keep its enabled/disabled state in sync with the current selection
        self.prompt_combo.bind("<<ComboboxSelected>>", self._update_delete_btn_state, add="+")
        
        # Prompt text area
        row += 1
        self.prompt_text = scrolledtext.ScrolledText(
            settings_frame,
            height=4,
            wrap=tk.WORD,
            font=("Segoe UI", 9)
        )
        self.prompt_text.grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)
        self.prompt_text.bind("<Button-3>", self._on_prompt_text_rightclick)
        
        # Load presets using prompt_manager if available
        names = self.prompt_manager.get_names() if self.prompt_manager else PRESET_NAMES
        default_key = self.prompt_manager.get_default() if self.prompt_manager else DEFAULT_PROMPT_KEY
        default_prompt = self.prompt_manager.get_prompt(default_key) if self.prompt_manager else PROMPT_PRESETS[DEFAULT_PROMPT_KEY]
        
        self.prompt_combo.config(values=names)
        self.prompt_preset_var.set(default_key)
        self.prompt_text.insert("1.0", default_prompt)
        self._update_delete_btn_state()

    def _on_provider_changed(self):
        """Handle provider selection changes."""
        provider = self.provider_var.get()
        config = PROVIDER_CONFIG.get(provider)

        if config:
            # Update base URL to provider default
            default_url = config['default_base_url']
            self.webhook_var.set(default_url)

            # Clear current model selection
            self.model_var.set("")

            # Trigger model discovery
            self._discover_models()

    def _test_connection(self):
        """Test connection to LLM server and discover models."""
        self._discover_models()

    def _discover_models(self):
        """Discover available models from current provider."""
        provider = self.provider_var.get()
        base_url = self.webhook_var.get().strip()

        if not provider or not base_url:
            self.models_status.set("Error: Provider and URL required")
            if self.status_indicator:
                self.status_indicator.config(foreground="red")
            return

        # Show loading state
        self.models_status.set("Connecting...")
        if self.status_indicator:
            self.status_indicator.config(foreground="orange")
        self.update()

        # Run discovery in background to avoid UI freeze
        def discovery_task():
            try:
                models, status, error = discover_models(provider, base_url)

                # Update UI on main thread
                self.after(0, lambda: self._update_models_ui(models, status, error))
            except Exception as e:
                self.after(0, lambda: self._update_models_ui([], 'error', str(e)))

        # Start discovery in background thread
        import threading
        threading.Thread(target=discovery_task, daemon=True).start()

    def _update_models_ui(self, models, status, error):
        """Update UI with model discovery results."""
        self.available_models = models

        # Update status indicator
        if status == 'ok':
            self.models_status.set("Connected")
            if self.status_indicator:
                self.status_indicator.config(foreground="green")
            self.models_error.set("")
        elif status == 'error':
            self.models_status.set("Cannot reach server")
            if self.status_indicator:
                self.status_indicator.config(foreground="red")
            self.models_error.set(error or "Unknown error")
        else:
            self.models_status.set("Connecting...")
            if self.status_indicator:
                self.status_indicator.config(foreground="orange")

        # Update model dropdown
        if models:
            # Store mapping of display labels to model IDs
            self._model_id_mapping = {model['label']: model['id'] for model in models}
            # Reverse mapping for display
            self._model_display_mapping = {model['id']: model['label'] for model in models}
            
            # Use labels for display in dropdown
            model_labels = [model['label'] for model in models]
            self.model_combo.config(values=model_labels)
            # Bind event handler for when user selects from dropdown
            self.model_combo.bind("<<ComboboxSelected>>", self._on_model_combobox_selected)
            # Select first model if none selected (use ID, not label)
            if not self.model_var.get():
                self.model_var.set(models[0]['id'])
        else:
            self.model_combo.config(values=[])
            self.model_var.set("")

    def _on_preset_changed(self, event=None):
        """Handle prompt preset selection changes."""
        key = self.prompt_preset_var.get()
        if key == PromptManager.SEPARATOR:
            self.prompt_preset_var.set(self._last_valid_preset)
            return
        self._last_valid_preset = key
        if self.prompt_manager:
            text = self.prompt_manager.get_prompt(key)
            # Save the selected preset as the new default
            self.prompt_manager.set_default(key)
        else:
            text = PROMPT_PRESETS.get(key, "")
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", text)
        logger.debug(f"Prompt preset changed to: {key}")
    
    def _reload_presets(self):
        """Reload prompt presets into dropdown"""
        if not self.prompt_manager:
            return
        names = self.prompt_manager.get_names()
        self.prompt_combo.config(values=names)
        current = self.prompt_preset_var.get()
        if current not in names or current == PromptManager.SEPARATOR:
            fallback = self.prompt_manager.get_default()
            self.prompt_preset_var.set(fallback)
            self._last_valid_preset = fallback
            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.insert("1.0", self.prompt_manager.get_prompt(fallback))
        self._update_delete_btn_state()
        


    def _speak_text(self, text):
        """
        Speak text using pyttsx3 TTS.
        
        Args:
            text: Text to speak
        """
        from utils import tts_engine_pyttsx3
        tts_engine_pyttsx3.speak(text)

    def _selection_or_all(self, widget):
        """Return the current selection in `widget`, or its full text if nothing is selected."""
        try:
            if widget.tag_ranges("sel"):
                selected = widget.get("sel.first", "sel.last")
                if selected and selected.strip():
                    return selected
        except tk.TclError:
            pass
        return widget.get("1.0", tk.END)

    def _make_readonly_selectable(self, widget):
        """
        Make a Text widget read-only while still allowing selection and copy.

        A widget with state="disabled" cannot be selected with the mouse, which
        would break selection-based TTS. Instead we keep it enabled and block
        edit keystrokes, allowing navigation, selection, and copy/select-all.
        """
        def _block_edit(event):
            # Allow Ctrl/Command shortcuts (copy, select-all, etc.)
            if event.state & 0x4:  # Control held
                return
            # Allow navigation keys
            if event.keysym in (
                "Left", "Right", "Up", "Down", "Home", "End",
                "Prior", "Next", "Shift_L", "Shift_R", "Control_L", "Control_R",
            ):
                return
            return "break"  # Block everything else (typing/deleting)

        widget.bind("<Key>", _block_edit)
        # Block paste and cut explicitly
        widget.bind("<<Paste>>", lambda e: "break")
        widget.bind("<<Cut>>", lambda e: "break")

    def _set_readonly_text(self, widget, text):
        """Replace the content of a read-only-selectable Text widget."""
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)

    def _on_prompt_text_rightclick(self, event):
        """Handle right-click on prompt textbox (Copy/Paste + Save as prompt)."""
        menu = tk.Menu(self, tearoff=0)

        def _paste():
            self.prompt_text.focus_set()
            self.prompt_text.event_generate("<<Paste>>")

        def _copy():
            self.prompt_text.event_generate("<<Copy>>")

        menu.add_command(label="Paste", command=_paste)
        menu.add_command(label="Copy", command=_copy)
        if self.prompt_manager:
            menu.add_separator()
            menu.add_command(label="💾 Save as prompt", command=self._save_prompt_as_custom)
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()
    
    def _save_prompt_as_custom(self):
        """Save current prompt text as a custom prompt"""
        if not self.prompt_manager:
            return
        text = self.prompt_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Empty prompt", "Cannot save an empty prompt.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Save prompt")
        dialog.resizable(False, False)
        dialog.grab_set()
        ttk.Label(dialog, text="Preset name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=10)
        name_entry.focus_set()
        def do_save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Missing name", "Please enter a name.", parent=dialog)
                return
            try:
                self.prompt_manager.add_custom(name, text)
                self._reload_presets()
                self.prompt_preset_var.set(name)
                self._last_valid_preset = name
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=dialog)
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=do_save).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        dialog.bind("<Return>", lambda e: do_save())
    
    def _on_preset_combo_rightclick(self, event):
        """Handle right-click on preset dropdown"""
        if not self.prompt_manager:
            return
        selected = self.prompt_preset_var.get()
        menu = tk.Menu(self, tearoff=0)
        if self.prompt_manager and self.prompt_manager.is_custom(selected):
            menu.add_command(label="🗑 Delete prompt", command=self._delete_custom_prompt)
        else:
            menu.add_command(label="Cannot delete default prompt", state="disabled")
        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()
    
    def _delete_custom_prompt(self):
        """Delete a custom prompt"""
        if not self.prompt_manager:
            return
        name = self.prompt_preset_var.get()
        # Guard: only custom presets are deletable
        if not self.prompt_manager.is_custom(name):
            messagebox.showinfo(
                "Cannot delete",
                "Only custom presets (below the separator line) can be deleted."
            )
            return
        if not messagebox.askyesno("Delete prompt", f"Delete custom prompt '{name}'?\nThis cannot be undone."):
            return
        try:
            self.prompt_manager.delete_custom(name)
            self._reload_presets()
            self._update_delete_btn_state()
        except (ValueError, KeyError) as e:
            messagebox.showerror("Error", str(e))

    def _update_delete_btn_state(self, event=None):
        """Enable the delete button only when a deletable custom preset is selected."""
        if not hasattr(self, "delete_preset_btn"):
            return
        name = self.prompt_preset_var.get()
        is_custom = bool(self.prompt_manager and self.prompt_manager.is_custom(name))
        self.delete_preset_btn.config(state="normal" if is_custom else "disabled")
    
    def _setup_file_info_section(self):
        """Setup file information display section."""
        self.file_info_frame = ttk.LabelFrame(self, text="File Info", padding="10")
        self.file_info_frame.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(self.file_info_frame)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        self.info_text = tk.Text(
            text_frame,
            wrap=tk.WORD,
            state="disabled",
            height=4,
            yscrollcommand=scrollbar.set
        )
        self.info_text.pack(fill="both", expand=True)
        scrollbar.config(command=self.info_text.yview)
        
        # Initial content
        self.info_text.config(state="normal")
        self.info_text.insert("1.0", "No file selected")
        self.info_text.config(state="disabled")
    
    def _setup_content_response_section(self):
        """Setup content preview and response display sections."""
        content_frame = ttk.Frame(self)
        content_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        
        # Configure grid weights
        content_frame.rowconfigure(0, weight=1)
        content_frame.columnconfigure(0, weight=1)
        content_frame.columnconfigure(1, weight=1)
        
        # Content preview (left)
        content_preview_frame = ttk.LabelFrame(
            content_frame,
            text="Content Preview & Edit",
            padding="5"
        )
        content_preview_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=0)
        
        self.content_text = scrolledtext.ScrolledText(
            content_preview_frame,
            height=20,
            wrap=tk.WORD,
            font=("Courier", 10)
        )
        self.content_text.pack(fill="both", expand=True)
        
        # Add TTS context menu to content preview text
        from views.context_menu import AppContextMenu
        content_menu = AppContextMenu(self.content_text)
        content_menu.add_copy_command()
        content_menu.add_paste_command()
        content_menu.add_separator()
        content_menu.add_tts_read_command(lambda: self._selection_or_all(self.content_text))
        content_menu.add_tts_stop_command()
        content_menu.add_separator()
        content_menu.add_fullscreen_command(title="Content Preview & Edit", editable=True)
        content_menu.bind()
        
        # Response display (right)
        response_frame = ttk.LabelFrame(
            content_frame,
            text="Response",
            padding="5"
        )
        response_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=0)
        
        self.response_text = scrolledtext.ScrolledText(
            response_frame,
            height=20,
            wrap=tk.WORD,
            font=("Courier", 10)
        )
        self.response_text.pack(fill="both", expand=True)
        # Read-only, but still selectable so TTS can read from a selection
        self._make_readonly_selectable(self.response_text)
        
        # Single consolidated context menu for the response: copy/clear + TTS + fullscreen
        from views.context_menu import AppContextMenu
        menu = AppContextMenu(self.response_text)
        menu.add_command("Copy All", self._copy_all_response)
        menu.add_command("Clear", self._clear_response)
        menu.add_separator()
        menu.add_command("Send to Translation tab", self._send_to_translation)
        menu.add_separator()
        menu.add_tts_read_command(lambda: self._selection_or_all(self.response_text))
        menu.add_tts_stop_command()
        menu.add_separator()
        menu.add_fullscreen_command(title="Response", editable=False)
        menu.bind()
        
        # Initial response content
        self._set_readonly_text(self.response_text,
            "Select a file or enter a YouTube URL and click Summarize to get started…"
        )
    
    def _setup_action_bar(self):
        """Setup action bar with buttons and export controls."""
        action_frame = ttk.Frame(self)
        action_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        
        # Summarize button
        self.send_btn = ttk.Button(
            action_frame,
            text="✨ Summarize",
            command=self._send_clicked
        )
        self.send_btn.grid(row=0, column=0, padx=5)
        
        # Export controls frame
        export_controls_frame = ttk.Frame(action_frame)
        export_controls_frame.grid(row=0, column=1, sticky="ew", padx=10)
        export_controls_frame.columnconfigure(0, weight=1)
        
        # Export preferences
        ttk.Checkbutton(
            export_controls_frame,
            text="Use original location",
            variable=self.use_original_location_var
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(
            export_controls_frame,
            text="Auto .txt",
            variable=self.auto_export_txt_var
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Checkbutton(
            export_controls_frame,
            text="Auto .docx",
            variable=self.auto_export_docx_var
        ).pack(side=tk.LEFT, padx=5)
        
        # Export buttons
        ttk.Label(export_controls_frame, text="Export:").pack(side=tk.LEFT, padx=5)
        
        self.export_txt_btn = ttk.Button(
            export_controls_frame,
            text="📄 .txt",
            command=self._export_txt_clicked,
            state="disabled"
        )
        self.export_txt_btn.pack(side=tk.LEFT, padx=2)
        
        self.export_docx_btn = ttk.Button(
            export_controls_frame,
            text="📝 .docx",
            command=self._export_docx_clicked,
            state="disabled"
        )
        self.export_docx_btn.pack(side=tk.LEFT, padx=2)
        
        self.copy_btn = ttk.Button(
            export_controls_frame,
            text="📋 Copy",
            command=self._copy_clicked,
            state="disabled"
        )
        self.copy_btn.pack(side=tk.LEFT, padx=2)
        
        # Clear button
        self.clear_btn = ttk.Button(
            action_frame,
            text="Clear All",
            command=self._clear_clicked
        )
        self.clear_btn.grid(row=0, column=2, padx=5)
        
        # Progress bar (created but not visible initially)
        self.progress = ttk.Progressbar(
            action_frame,
            mode="indeterminate"
        )
    
    # Context menu helpers
    def _copy_all_response(self):
        """Copy all response text to clipboard."""
        content = self.response_text.get("1.0", tk.END).strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            self.update()
            self.set_status(f"Copied {len(content)} characters to clipboard")
    
    def _clear_response(self):
        """Clear response text."""
        self._set_readonly_text(self.response_text, "Response cleared")
        self.set_status("Response cleared")

    def _send_to_translation(self):
        """Send the response text to the Translation tab's Source box and switch to it."""
        text = self.response_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo(
                "Nothing to send", "The response is empty — summarize something first."
            )
            return

        if callable(self.on_send_to_translation):
            self.on_send_to_translation(text)
            self.set_status(f"Sent {len(text)} characters to the Translation tab")
        else:
            logger.warning("on_send_to_translation not wired; cannot forward to Translation tab")
            messagebox.showwarning(
                "Unavailable",
                "The Translation tab isn't available to receive this text.",
            )
    
    # Button handlers
    def _browse_file(self):
        """Browse for file."""
        filetypes = [
            ("All Files", ".*"),  # Make this first and default
            ("Text Files", ".txt"),
            ("Subtitle Files", ".srt .vtt"),
            ("JSON Files", ".json"),
            ("Word Documents", ".docx")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Select file to summarize",
            filetypes=filetypes
        )
        
        if file_path:
            self.set_file_path(file_path)
            if self.on_file_selected:
                self.on_file_selected(file_path)
    
    def _send_clicked(self):
        """Handle summarize button click."""
        if self.on_send_clicked:
            self.on_send_clicked()
    
    def _export_txt_clicked(self):
        """Handle export txt button click."""
        if self.on_export_txt:
            self.on_export_txt()
    
    def _export_docx_clicked(self):
        """Handle export docx button click."""
        if self.on_export_docx:
            self.on_export_docx()
    
    def _copy_clicked(self):
        """Handle copy button click."""
        if self.on_copy_clicked:
            self.on_copy_clicked()
    
    def _clear_clicked(self):
        """Handle clear button click."""
        if self.on_clear_clicked:
            self.on_clear_clicked()
        else:
            self.clear_all()
    
    # Getters
    def get_input_mode(self) -> str:
        """Get current input mode."""
        return self.input_mode_var.get()
    
    def get_file_path(self) -> Optional[str]:
        """Get selected file path."""
        path = self.file_path_var.get()
        return path if path and path != "No file selected" else None
    
    def get_youtube_url(self) -> str:
        """Get YouTube URL."""
        return self.url_var.get().strip()
    
    def get_transcription_format(self) -> str:
        """Get transcription format."""
        return self.format_var.get()

    def get_force_retranscribe(self) -> bool:
        """Get force re-transcribe preference."""
        return getattr(self, 'force_retranscribe_var', tk.BooleanVar()).get()

    def get_webhook_url(self) -> str:
        """Get webhook URL."""
        return self.webhook_var.get().strip()
    
    def _clean_env_file(self, old_value: str, new_value: str):
        """Clean up corrupted model name in .env file."""
        try:
            from pathlib import Path
            env_path = Path(__file__).parent.parent / '.env'
            
            if env_path.exists():
                content = env_path.read_text(encoding='utf-8')
                
                # Replace the corrupted model name in the .env file
                updated_content = content.replace(
                    f'LLM_MODEL={old_value}',
                    f'LLM_MODEL={new_value}'
                )
                
                if updated_content != content:
                    env_path.write_text(updated_content, encoding='utf-8')
                    logger.info(f"Cleaned .env file: LLM_MODEL updated from '{old_value}' to '{new_value}'")
        except Exception as e:
            logger.error(f"Failed to clean .env file: {e}")
    
    def _cleanup_model_name(self):
        """Clean up corrupted model names that may exist in .env file."""
        current_value = self.model_var.get().strip()
        if not current_value:
            return
        
        # Check if the current value contains size description in parentheses
        # Pattern: model-name (size)
        import re
        match = re.match(r'^(.+?)\s+\([^)]+\)$', current_value)
        if match:
            # Extract just the model name part
            clean_model_name = match.group(1)
            logger.info(f"Cleaned up corrupted model name: '{current_value}' -> '{clean_model_name}'")
            self.model_var.set(clean_model_name)
            
            # Also clean the .env file to prevent future corruption
            self._clean_env_file(current_value, clean_model_name)
    
    def _on_model_combobox_selected(self, event=None):
        """Handle model selection from dropdown - convert label to ID if needed."""
        selected_label = self.model_combo.get().strip()
        if not selected_label:
            return
        
        # If the selected value is a label (contains size description), convert to ID
        if selected_label in self._model_id_mapping:
            model_id = self._model_id_mapping[selected_label]
            logger.info(f"Converted model label to ID: '{selected_label}' -> '{model_id}'")
            self.model_var.set(model_id)
        else:
            # If it's already an ID or unknown, use as-is
            self.model_var.set(selected_label)
    
    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_var.get().strip()
    
    def get_save_settings(self) -> bool:
        """Get save settings preference."""
        return self.save_settings_var.get()
    
    def get_provider(self) -> str:
        """Get current provider."""
        return self.provider_var.get()
    
    def get_prompt(self) -> str:
        """Get current prompt text."""
        return self.prompt_text.get("1.0", tk.END).strip()
    
    def get_content(self) -> str:
        """Get content text (satisfies BaseTab abstract method)."""
        return self.content_text.get("1.0", tk.END).strip()
    
    def get_response_content(self) -> str:
        """Get response text."""
        return self.response_text.get("1.0", tk.END).strip()
    
    def get_export_preferences(self) -> Dict[str, Any]:
        """Get export preferences."""
        return {
            "use_original_location": self.use_original_location_var.get(),
            "auto_export_txt": self.auto_export_txt_var.get(),
            "auto_export_docx": self.auto_export_docx_var.get(),
            "original_directory": self.current_file_directory,
            "original_basename": self.current_file_basename
        }
    
    # Setters
    def set_file_path(self, path: Optional[str]):
        """Set file path and store directory/basename."""
        if path:
            self.file_path_var.set(path)
            self.current_file_directory = os.path.dirname(path)
            self.current_file_basename = os.path.basename(path)
        else:
            self.file_path_var.set("No file selected")
            self.current_file_directory = None
            self.current_file_basename = None
    
    def set_content(self, text: str):
        """Set content text."""
        self.content_text.config(state="normal")
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", text)
        self.content_text.config(state="normal")
    
    def set_file_info(self, info: Optional[dict]):
        """Set file information display."""
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", tk.END)
        
        if info:
            lines = [
                f"Name: {info.get('name', 'Unknown')}",
                f"Size: {info.get('size_kb', 0):.2f} KB",
                f"Lines: {info.get('lines', 0)}",
                f"Type: {info.get('type', 'Unknown')}"
            ]
            self.info_text.insert("1.0", "\n".join(lines))
        else:
            self.info_text.insert("1.0", "No file selected")
        
        self.info_text.config(state="disabled")
    
    def set_status(self, msg: str):
        """Set status message (override BaseTab default)."""
        logger.info(f"SummarizerTab: {msg}")
        # Note: This tab doesn't have a status bar, so just log
        # The controller can handle status display in main window
    
    def display_response(self, text: str):
        """Display response text."""
        self._set_readonly_text(self.response_text, text)
    
    def show_loading(self, show: bool):
        """Show or hide loading indicator."""
        if show:
            self.progress.grid(row=5, column=0, sticky="ew", pady=5)
            self.send_btn.config(state="disabled")
            self.progress.start()
        else:
            self.progress.grid_remove()
            self.send_btn.config(state="normal")
            self.progress.stop()
    
    def set_export_buttons_enabled(self, enabled: bool):
        """Enable or disable export buttons."""
        state = "normal" if enabled else "disabled"
        self.export_txt_btn.config(state=state)
        self.export_docx_btn.config(state=state)
        self.copy_btn.config(state=state)
    
    # BaseTab abstract method implementations
    def clear_all(self):
        """Reset all UI elements to initial state."""
        # Reset input mode and file state
        self.input_mode_var.set("file")
        self.file_path_var.set("No file selected")
        self.current_file_directory = None
        self.current_file_basename = None
        
        # Reset YouTube state
        self.url_var.set("https://")
        
        # Clear content areas
        self.content_text.delete("1.0", tk.END)
        self.info_text.config(state="normal")
        self.info_text.delete("1.0", tk.END)
        self.info_text.insert("1.0", "No file selected")
        self.info_text.config(state="disabled")
        
        # Reset response
        self._set_readonly_text(self.response_text,
            "Select a file or enter a YouTube URL and click Summarize to get started…")
        
        # Reset export buttons
        self.set_export_buttons_enabled(False)
        
        # Restore frame visibility for current mode
        self._on_mode_changed()
        
        self.set_status("Cleared all")