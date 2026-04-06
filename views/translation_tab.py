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
import threading
import queue
import requests
import json

from views.base_tab import BaseTab


class TranslationTab(BaseTab):
    """Basic UI for upcoming translation workflows (no backend yet)."""

    def __init__(self, notebook):
        self.notebook = notebook

        # State variables
        self.source_file_path = tk.StringVar(value="[No file selected]")
        self.webhook_url = tk.StringVar(value="")
        self.target_language = tk.StringVar(value="Croatian")

        # Thread management
        self.translation_thread = None
        self.translation_queue = queue.Queue()
        self.is_translating = tk.BooleanVar(value=False)

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

        # File selection and translation controls
        file_btn = ttk.Button(
            top_frame, text="[Browse file...]", command=self._browse_file
        )
        file_btn.grid(row=0, column=0, padx=(0, 8), pady=5, sticky=tk.W)

        # Translate button (isolated from file_btn)
        translate_btn = ttk.Button(
            top_frame, text="Translate", command=self._start_translation_thread
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

        self.target_language = tk.StringVar(value="Croatian")
        language_dropdown = ttk.Combobox(
            top_frame, textvariable=self.target_language, values=["Croatian", "Deutsch"]
        )
        language_dropdown.grid(row=1, column=4, padx=(0, 8), pady=5, sticky=tk.W)

        # Row 1: Source text (loaded content)
        source_frame = ttk.LabelFrame(self, text="Source Text (Loaded)")
        source_frame.grid(
            row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(0, 5)
        )
        source_frame.rowconfigure(0, weight=1)
        source_frame.columnconfigure(0, weight=1)

        self.source_text = tk.Text(source_frame, wrap=tk.WORD, height=12)
        self.source_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        source_scroll = ttk.Scrollbar(source_frame, command=self.source_text.yview)
        source_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.source_text.configure(yscrollcommand=source_scroll.set)

        # Row 2: Translated text (future response)
        target_frame = ttk.LabelFrame(self, text="Translated Text (Future Response)")
        target_frame.grid(
            row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(5, 10)
        )
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
        if self.is_translating.get():
            return
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

    def _start_translation_thread(self):
        """Start translation in worker thread."""
        if self.is_translating.get():
            return  # Prevent duplicate translations

        source_text = self.source_text.get("1.0", tk.END).strip()
        if not source_text:
            self.target_text.delete("1.0", tk.END)
            self.target_text.insert(tk.END, "No text to translate.")
            return

        # Save current webhook URL to .env for persistence
        current_url = self.webhook_url.get()
        if current_url and current_url != "http://127.0.0.1:1234/v1/completions":
            self._save_webhook_to_env(current_url)

        # Update UI state
        self.is_translating.set(True)
        self.translate_btn.config(state="disabled")
        self.file_btn.config(state="disabled")
        self.progress_bar.start()
        self.status_label.config(text="Translating...")

        # Clear previous result
        self.target_text.delete("1.0", tk.END)

        # Start worker thread
        self.translation_thread = threading.Thread(
            target=self._translation_worker,
            args=(source_text, self.target_language.get(), self.translation_queue),
            daemon=True,
        )
        self.translation_thread.start()

        # Start checking for results
        self.after(100, self._check_translation_result)

    def _restore_default_webhook(self):
        """Restore default webhook URL."""
        from config import TRANSLATION_DEFAULT_URL

        self.webhook_url.set(TRANSLATION_DEFAULT_URL)
        self._save_webhook_to_env(TRANSLATION_DEFAULT_URL)
        self.status_label.config(text=f"Restored default: {TRANSLATION_DEFAULT_URL}")

    def _save_webhook_to_env(self, url):
        """Save webhook URL to .env file for persistence."""
        import os

        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

        # Read existing .env
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()

        # Update or add TRANSLATION_URL
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("TRANSLATION_URL="):
                lines[i] = f"TRANSLATION_URL={url}\n"
                updated = True
                break

        if not updated:
            lines.append(f"TRANSLATION_URL={url}\n")

        # Write back to .env
        with open(env_path, "w") as f:
            f.writelines(lines)

    def _translation_worker(self, text, target_language, result_queue):
        """Worker thread for translation."""
        try:
            # Use custom webhook URL or default
            endpoint = self.webhook_url.get() or "http://127.0.0.1:1234/v1/completions"
            headers = {"Content-Type": "application/json"}

            # Display which endpoint is being used (via queue)
            result_queue.put(("info", f"Sending to: {endpoint}"))

            prompt_template = f"Output translation only. Translate following text to {target_language}: {text}"

            payload = {
                "model": "translategemma:4b-it",
                "prompt": prompt_template,
                "temperature": 0.3,
                "max_tokens": 500,
            }

            response = requests.post(
                endpoint,
                headers=headers,
                data=json.dumps(payload),
                timeout=300,  # 5 minutes for very large texts
            )

            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                translated_text = response_data.get("choices", [{}])[0].get("text", "")
                result_queue.put(("success", translated_text))
            else:
                result_queue.put(
                    ("error", f"HTTP {response.status_code}: {response.text[:200]}")
                )

        except requests.exceptions.Timeout:
            result_queue.put(("timeout", "Request timed out after 5 minutes"))
        except requests.exceptions.ConnectionError:
            result_queue.put(("connection_error", "Cannot connect to LM Studio"))
        except Exception as e:
            result_queue.put(("error", str(e)))

    def _check_translation_result(self):
        """Check for translation result from worker thread."""
        try:
            # Non-blocking check for result
            status, message = self.translation_queue.get_nowait()

            if status == "info":
                # Update status label with endpoint info
                self.status_label.config(text=message)
                # Continue checking for actual result
                self.after(100, self._check_translation_result)
                return

            # Update UI
            self.progress_bar.stop()
            self.is_translating.set(False)
            self.translate_btn.config(state="normal")
            self.file_btn.config(state="normal")

            if status == "success":
                self.target_text.delete("1.0", tk.END)
                self.target_text.insert(tk.END, message)
            else:
                self.target_text.delete("1.0", tk.END)
                self.target_text.insert(tk.END, f"Translation failed: {message}")

        except queue.Empty:
            # Check again after 100ms
            if self.is_translating.get():
                self.after(100, self._check_translation_result)

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
