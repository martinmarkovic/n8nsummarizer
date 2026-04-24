"""
Translation Tab - UI for translation workflows (v6.8.9)

Pure View component following MVC pattern.

Responsibilities:
    - UI layout and widgets
    - Display data from controller
    - Emit events/callbacks to controller
    - No business logic or direct API calls

Follows the same pattern as other tabs in the project.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

from views.base_tab import BaseTab
from views.resizable_panes import ResizablePanes


class TranslationTab(BaseTab):
    """Translation workflow UI (pure view, no business logic)."""

    def __init__(self, notebook):
        self.notebook = notebook

        # State variables (UI state only)
        self.source_file_path = tk.StringVar(value="[No file selected]")
        self.webhook_url = tk.StringVar(value="")
        self.target_language = tk.StringVar(value="Croatian")
        self.is_translating = tk.BooleanVar(value=False)

        # Callback properties - will be wired by controller
        self.on_file_selected = None
        self.on_translate_clicked = None
        self.on_restore_default_webhook = None
        self.on_clear_clicked = None

        super().__init__(notebook, "🌐 Translation")

    def _setup_ui(self):
        """Build translation UI (file picker + resizable side-by-side textboxes + webhook field)."""
        # Configure grid for controls and resizable panes
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Resizable panes row

        # Row 0: File selection + webhook URL
        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        top_frame.columnconfigure(1, weight=1)

        # File selection and translation controls
        file_btn = ttk.Button(
            top_frame, text="[Browse file...]", command=self._browse_file
        )
        file_btn.grid(row=0, column=0, padx=(0, 8), pady=5, sticky=tk.W)

        # Translate button (isolated from file_btn)
        translate_btn = ttk.Button(
            top_frame, text="Translate", command=self._start_translation
        )
        translate_btn.grid(row=0, column=2, padx=(8, 0), pady=5, sticky=tk.W)

        file_label = ttk.Label(top_frame, textvariable=self.source_file_path)
        file_label.grid(row=0, column=1, padx=4, pady=5, sticky=(tk.W, tk.E))

        # Loading indicator widgets
        self.progress_bar = ttk.Progressbar(top_frame, mode="indeterminate")
        self.progress_bar.grid(row=0, column=4, padx=(10, 0), pady=5, sticky=tk.W)

        self.status_label = ttk.Label(top_frame, text="")
        self.status_label.grid(row=0, column=5, padx=(5, 0), pady=5, sticky=tk.W)

        # Store button references for state management
        self.file_btn = file_btn
        self.translate_btn = translate_btn

        # Webhook URL and language selection
        ttk.Label(top_frame, text="Translation Webhook URL:").grid(
            row=1, column=0, padx=(0, 8), pady=5, sticky=tk.W
        )

        webhook_entry = ttk.Entry(top_frame, textvariable=self.webhook_url)
        webhook_entry.grid(row=1, column=1, padx=4, pady=5, sticky=(tk.W, tk.E))

        # Restore defaults button
        restore_btn = ttk.Button(
            top_frame, text="Restore Default", command=self._restore_default_webhook
        )
        restore_btn.grid(row=1, column=2, padx=(8, 0), pady=5, sticky=tk.W)

        # Language dropdown
        ttk.Label(top_frame, text="Translate to:").grid(
            row=1, column=3, padx=(8, 0), pady=5, sticky=tk.W
        )

        language_dropdown = ttk.Combobox(
            top_frame, textvariable=self.target_language, values=["Croatian", "Deutsch"]
        )
        language_dropdown.grid(row=1, column=4, padx=(0, 8), pady=5, sticky=tk.W)

        # Row 1: Resizable panes with source (left) and translation (right)
        self.panes = ResizablePanes(self)
        self.panes.grid(
            row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(0, 10)
        )

        # Setup left pane (Source text)
        source_frame = ttk.LabelFrame(self.panes.left_pane, text="Source")
        source_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        source_frame.rowconfigure(0, weight=1)
        source_frame.columnconfigure(0, weight=1)

        self.source_text = tk.Text(source_frame, wrap=tk.WORD, height=12)
        self.source_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        source_scroll = ttk.Scrollbar(source_frame, command=self.source_text.yview)
        source_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.source_text.configure(yscrollcommand=source_scroll.set)

        # Setup right pane (Translation text)
        target_frame = ttk.LabelFrame(self.panes.right_pane, text="Translation")
        target_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        target_frame.rowconfigure(0, weight=1)
        target_frame.columnconfigure(0, weight=1)

        self.target_text = tk.Text(target_frame, wrap=tk.WORD, height=12)
        self.target_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        target_scroll = ttk.Scrollbar(target_frame, command=self.target_text.yview)
        target_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.target_text.configure(yscrollcommand=target_scroll.set)

        # Wire context menu for translation export and forward functionality
        self._register_context_menu(
            self.target_text,
            [
                {"label": "Export as .txt", "command": self._export_translation_txt},
                {"label": "Export as .srt", "command": self._export_translation_srt},
                {"separator": True},
                {
                    "label": "Forward to Summarization",
                    "command": self._forward_to_summarization,
                },
            ],
        )

    # --- View Methods (called by controller) ---

    def set_file_path(self, file_path: str):
        """Set the file path display"""
        self.source_file_path.set(file_path)

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
        """Set webhook URL"""
        self.webhook_url.set(url)

    def set_status(self, message: str):
        """Set status message"""
        self.status_label.config(text=message)

    def set_translating_state(self, is_translating: bool):
        """Set translation state and update UI controls"""
        self.is_translating.set(is_translating)

        if is_translating:
            self.translate_btn.config(state="disabled")
            self.file_btn.config(state="disabled")
            self.progress_bar.start()
        else:
            self.translate_btn.config(state="normal")
            self.file_btn.config(state="normal")
            self.progress_bar.stop()

    def get_translating_state(self) -> bool:
        """Get current translation state"""
        return self.is_translating.get()

    def show_error(self, message: str):
        """Show error message to user"""
        # Override base method to show in UI
        self.target_text.delete("1.0", tk.END)
        self.target_text.insert(tk.END, f"Error: {message}")

    # --- Callback Methods (trigger controller) ---

    def _browse_file(self):
        """Handle file browse button click - emit callback to controller"""
        if self.is_translating.get():
            return

        file_path = filedialog.askopenfilename(title="Select file to translate")
        if file_path:
            if self.on_file_selected:
                self.on_file_selected(file_path)

    def _start_translation(self):
        """Handle translate button click - emit callback to controller"""
        if self.on_translate_clicked:
            self.on_translate_clicked()

    def _restore_default_webhook(self):
        """Handle restore default webhook button click - emit callback to controller"""
        if self.on_restore_default_webhook:
            self.on_restore_default_webhook()

    # --- Getter Methods (used by controller) ---

    def get_source_text(self) -> str:
        """Get current source text content"""
        return self.source_text.get("1.0", tk.END).strip()

    def get_webhook_url(self) -> str:
        """Get current webhook URL"""
        return self.webhook_url.get()

    def get_target_language(self) -> str:
        """Get selected target language"""
        return self.target_language.get()

    def get_file_path(self) -> str:
        """Get the current file path"""
        return self.source_file_path.get()

    def _export_translation_txt(self):
        """Export translated text as .txt file via context menu."""
        # Get text from target text widget
        text_content = self.target_text.get("1.0", tk.END).strip()

        # Check if there's content to export
        if not text_content:
            messagebox.showwarning(
                title="Nothing to export", message="Translated text is empty."
            )
            return

        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Translation",
        )

        # If user confirmed the save
        if file_path:
            try:
                # Write the content to file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text_content)

                # Show success message
                messagebox.showinfo(
                    title="Exported", message=f"Translation saved to:\n{file_path}"
                )
            except IOError as e:
                 # Show error if write fails
                messagebox.showerror(title="Export Failed", message=str(e))

    def _export_translation_srt(self):
        """Export translated text as .srt file via context menu."""
        # Get text from target text widget
        text_content = self.target_text.get("1.0", tk.END).strip()

        # Check if there's content to export
        if not text_content:
            messagebox.showwarning(
                title="Nothing to export", message="Translated text is empty."
            )
            return

        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".srt",
            filetypes=[("SubRip subtitles", "*.srt"), ("All files", "*.*")],
            title="Export SRT Translation",
        )

        # If user confirmed the save
        if file_path:
            try:
                # Write the content to file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text_content)

                # Show success message
                messagebox.showinfo(
                    title="Exported", message=f"SRT translation saved to:\n{file_path}"
                )
            except IOError as e:
                # Show error if write fails
                messagebox.showerror(title="Export Failed", message=str(e))

    def _forward_to_summarization(self):
        """Forward translated text to summarization tab via context menu."""
        # Get text from target text widget
        text_content = self.target_text.get("1.0", tk.END).strip()

        # Check if there's content to forward
        if not text_content:
            messagebox.showwarning(
                title="Nothing to forward", message="Translated text is empty."
            )
            return

        # Clean the text by removing think tags
        cleaned_text = text_content.replace("<think>", "").replace("</think>", "")
        cleaned_text = " ".join(cleaned_text.split()).strip()

        # Get main window to access summarization tab
        main_window = self.get_main_window()
        if main_window and hasattr(main_window, "youtube_summarizer_tab"):
            # Forward text directly to summarization tab
            main_window.youtube_summarizer_tab.set_summary_content(cleaned_text)

            messagebox.showinfo(
                title="Forwarded Successfully",
                message=f"Translation forwarded to summarization tab ({len(cleaned_text)} characters)",
            )
        else:
            # Fallback: Store text for manual pasting
            self._forwarded_text = cleaned_text
            messagebox.showinfo(
                title="Ready to Forward",
                message="Text is ready. Use the 'Paste Forwarded Text' function in the summarization tab.",
            )
            return

        # Clean the text by removing think tags
        cleaned_text = text_content.replace("<think>", "").replace("</think>", "")
        cleaned_text = " ".join(cleaned_text.split()).strip()

        # Show confirmation
        response = messagebox.askyesno(
            title="Forward to Summarization",
            message=f"Forward {len(cleaned_text)} characters to summarization tab?",
        )

        if response:  # User confirmed
            # Store the text to be forwarded
            self._forwarded_text = cleaned_text

            messagebox.showinfo(
                title="Ready to Forward",
                message="Text is ready. Use the 'Paste Forwarded Text' function in the summarization tab.",
            )

    # --- BaseTab abstract method implementations ---

    def get_content(self) -> str:
        """Return the current source text content."""
        return self.get_source_text()

    def clear_all(self):
        """Clear source/target text and reset file path."""
        self.source_text.delete("1.0", tk.END)
        self.target_text.delete("1.0", tk.END)
        self.source_file_path.set("[No file selected]")
        self.set_status("")
