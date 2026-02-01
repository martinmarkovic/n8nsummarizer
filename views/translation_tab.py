"""
Translation Tab - Placeholder for future translation workflows (v6.0)

Basic UI only (no backend logic yet).

Intended behavior (future):
- Let user load a file and display its contents in a source textbox
- Send the content/file to a translation webhook (n8n or external)
- Display translated text from LLM / service in target textbox

Current state: UI skeleton only, wired to main window as 6th tab.
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path

from views.base_tab import BaseTab


class TranslationTab(BaseTab):
    """Basic UI for upcoming translation workflows (no backend yet)."""

    def __init__(self, notebook):
        self.notebook = notebook

        # State variables
        self.source_file_path = tk.StringVar(value="[No file selected]")
        self.webhook_url = tk.StringVar(value="")

        super().__init__(notebook, "🌐 Translation")

    def _setup_ui(self):
        """Build basic translation UI (file picker + two textboxes + webhook field)."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        # Row 0: File selection + webhook URL
        top_frame = ttk.Frame(self)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        top_frame.columnconfigure(1, weight=1)

        # File selection
        file_btn = ttk.Button(top_frame, text="[Browse file...]", command=self._browse_file)
        file_btn.grid(row=0, column=0, padx=(0, 8), pady=5, sticky=tk.W)

        file_label = ttk.Label(top_frame, textvariable=self.source_file_path)
        file_label.grid(row=0, column=1, padx=4, pady=5, sticky=(tk.W, tk.E))

        # Webhook URL
        ttk.Label(top_frame, text="Translation Webhook URL:").grid(
            row=1, column=0, padx=(0, 8), pady=5, sticky=tk.W
        )

        webhook_entry = ttk.Entry(top_frame, textvariable=self.webhook_url)
        webhook_entry.grid(row=1, column=1, padx=4, pady=5, sticky=(tk.W, tk.E))

        # Row 1: Source text (loaded content)
        source_frame = ttk.LabelFrame(self, text="Source Text (Loaded)")
        source_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(0, 5))
        source_frame.rowconfigure(0, weight=1)
        source_frame.columnconfigure(0, weight=1)

        self.source_text = tk.Text(source_frame, wrap=tk.WORD, height=12)
        self.source_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        source_scroll = ttk.Scrollbar(source_frame, command=self.source_text.yview)
        source_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.source_text.configure(yscrollcommand=source_scroll.set)

        # Row 2: Translated text (future response)
        target_frame = ttk.LabelFrame(self, text="Translated Text (Future Response)")
        target_frame.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(5, 10))
        target_frame.rowconfigure(0, weight=1)
        target_frame.columnconfigure(0, weight=1)

        self.target_text = tk.Text(target_frame, wrap=tk.WORD, height=12)
        self.target_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        target_scroll = ttk.Scrollbar(target_frame, command=self.target_text.yview)
        target_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.target_text.configure(yscrollcommand=target_scroll.set)

        # Note: No backend wiring yet; this will be added in a later step.

    def _browse_file(self):
        """Let the user pick a file and load its contents into the source textbox."""
        file_path = filedialog.askopenfilename(title="Select file to translate")
        if not file_path:
            return

        self.source_file_path.set(file_path)

        try:
            # Simple text load; binary/complex formats will be handled later
            path = Path(file_path)
            text = path.read_text(encoding="utf-8", errors="replace")
            self.source_text.delete("1.0", tk.END)
            self.source_text.insert(tk.END, text)
        except Exception as exc:
            # Minimal inline error reporting; controllers will handle richer flows later
            self.source_text.delete("1.0", tk.END)
            self.source_text.insert(tk.END, f"Error loading file: {exc}")

    # --- BaseTab abstract method implementations ---

    def get_content(self) -> str:
        """Return the current source text content.

        For now we expose the loaded source text so future controllers
        can send it to a translation workflow.
        """
        return self.source_text.get("1.0", tk.END).strip()

    def clear_all(self):
        """Clear source/target text and reset file path.

        Keeps webhook URL so users don't lose their configured endpoint
        when clearing the current content.
        """
        self.source_text.delete("1.0", tk.END)
        self.target_text.delete("1.0", tk.END)
        self.source_file_path.set("[No file selected]")
