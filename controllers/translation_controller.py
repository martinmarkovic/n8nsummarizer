"""
Translation Controller - Coordinates Translation tab ↔ TranslationModel

Responsibilities:
    - Listen to Translation tab UI events
    - Call TranslationModel to process translation requests
    - Update view with results
    - Handle errors gracefully
    - Manage threading for blocking operations

Controller is THIN - just coordinates, doesn't contain business logic.
Follows the same pattern as other controllers in the project.
"""

import threading
import queue
import os
from models.translation_model import TranslationModel
from utils.logger import logger


class TranslationController:
    """Coordinates Translation tab UI and TranslationModel"""

    def __init__(self, view):
        """
        Initialize controller with view reference.

        Args:
            view: Translation tab view instance
        """
        self.view = view
        self.model = TranslationModel()

        # Thread management
        self.translation_thread = None
        self.translation_queue = queue.Queue()

        # Wire up view callbacks
        self.view.on_file_selected = self.handle_file_selected
        self.view.on_translate_clicked = self.handle_translate_clicked
        self.view.on_restore_default_webhook = self.handle_restore_default_webhook
        self.view.on_clear_clicked = self.handle_clear_clicked

        # Show default webhook URL in the field on startup
        self.view.set_webhook_url(self.model.webhook_url)

        logger.info("TranslationController initialized")

    def handle_file_selected(self, file_path: str):
        """Handle file selection from view"""
        logger.info(f"File selected for translation: {file_path}")

        # Use model to read file
        success, content, error = self.model.load_file_content(file_path)

        if success:
            self.view.set_file_path(file_path)
            self.view.set_source_text(content)
            self.view.set_status(f"Loaded: {os.path.basename(file_path)}")
        else:
            self.view.show_error(f"Failed to load file: {error}")
            self.view.set_file_path("")
            self.view.set_source_text("")

    def handle_translate_clicked(self):
        """Handle Translate button click - starts background thread"""
        logger.info("Translate button clicked")

        # Validate we have content to translate
        source_text = self.view.get_source_text()
        if not source_text or not source_text.strip():
            self.view.show_error(
                "No text to translate. Please load a file or enter text."
            )
            return

        # Always use webhook field value; fall back to default if empty
        webhook_url = self.view.get_webhook_url().strip()
        if webhook_url:
            self.model.set_webhook_url(webhook_url)
        else:
            default_url = self.model.restore_default_webhook()
            self.view.set_webhook_url(default_url)
            logger.info(f"Webhook field was empty, using default: {default_url}")

        # Get target language
        target_language = self.view.get_target_language()

        # Update UI state for translation in progress
        self.view.set_translating_state(True)
        self.view.set_status(f"Translating to {target_language}...")
        self.view.clear_target_text()

        # Start translation in background thread
        self.translation_thread = threading.Thread(
            target=self._translation_worker,
            args=(source_text, target_language),
            daemon=True,
        )
        self.translation_thread.start()

        # Start checking for results
        self._check_translation_result()

    def _translation_worker(self, text: str, target_language: str):
        """Worker thread for translation"""
        try:
            # Send translation request through model
            success, translated_text, error = self.model.translate_text(
                text, target_language
            )

            if success:
                self.translation_queue.put(("success", translated_text))
            else:
                self.translation_queue.put(
                    ("error", error or "Unknown translation error")
                )

        except Exception as e:
            error_msg = f"Unexpected translation error: {str(e)}"
            logger.error(error_msg)
            self.translation_queue.put(("error", error_msg))

    def _check_translation_result(self):
        """Check for translation result from worker thread"""
        try:
            # Non-blocking check for result
            status, message = self.translation_queue.get_nowait()

            # Update UI
            self.view.set_translating_state(False)

            if status == "success":
                self.view.set_target_text(message)
                self.view.set_status("Translation completed successfully")
            else:
                self.view.show_error(f"Translation failed: {message}")
                self.view.set_status(f"Translation failed: {message}")

        except queue.Empty:
            # Check again after 100ms if still translating
            if self.view.get_translating_state():
                self.view.root.after(100, self._check_translation_result)

    def handle_restore_default_webhook(self):
        """Handle Restore Default Webhook button click"""
        logger.info("Restoring default translation webhook")

        # Restore default in model
        default_url = self.model.restore_default_webhook()

        # Update view
        self.view.set_webhook_url(default_url)

        # Save to .env
        if self.model.save_webhook_to_env(default_url):
            self.view.set_status(f"Restored default webhook: {default_url}")
        else:
            self.view.show_error("Failed to save default webhook to .env")

    def handle_clear_clicked(self):
        """Handle Clear button click"""
        logger.info("Clear button clicked")
        self.view.clear_all()
        self.view.set_status("Ready")
