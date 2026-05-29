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
from models.llm_client import LLMClient
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
        self.llm_client = LLMClient()  # NEW: LLM client for direct LLM communication

        # Thread management
        self.translation_thread = None
        self.translation_queue = queue.Queue()

        # Callbacks for LLM settings changes
        self._llm_settings_callbacks = []

        # Wire up view callbacks
        self.view.on_file_selected = self.handle_file_selected
        self.view.on_translate_clicked = self.handle_translate_clicked
        self.view.on_restore_default_webhook = self.handle_restore_default_webhook
        self.view.on_clear_clicked = self.handle_clear_clicked

        # Initialize LLM settings from view defaults
        self._update_llm_client_from_view()

        logger.info("TranslationController initialized")

    def register_llm_settings_callback(self, callback):
        """Register a callback to be notified when LLM settings change.
        
        Args:
            callback: Function that takes (provider, model, url) parameters
        """
        self._llm_settings_callbacks.append(callback)
        logger.info(f"Registered LLM settings callback, total callbacks: {len(self._llm_settings_callbacks)}")

    def _notify_llm_settings_changed(self):
        """Notify all registered callbacks that LLM settings have changed."""
        provider = self.view.get_provider()
        model = self.view.get_model_name()
        url = self.view.get_webhook_url()
        
        for callback in self._llm_settings_callbacks:
            try:
                callback(provider, model, url)
            except Exception as e:
                logger.error(f"Error calling LLM settings callback: {e}")
        
        logger.info(f"Notified {len(self._llm_settings_callbacks)} callbacks about LLM settings change")

    def handle_file_selected(self, file_path: str):
        """Handle file selection from view"""
        logger.info(f"File selected for translation: {file_path}")

        # Use model to read file
        success, content, error = self.model.load_file_content(file_path)

        if success:
            self.view.set_file_path(file_path)
            self.view.set_source_text(content)
            self.view.set_status(f"Loaded: {os.path.basename(file_path)}")
            # Set current file path for SRT detection
            self.model.set_current_file_path(file_path)
        else:
            self.view.show_error(f"Failed to load file: {error}")
            self.view.set_file_path("")
            self.view.set_source_text("")
            self.model.set_current_file_path(None)

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

        # Update LLM client and model with current view settings
        self._update_llm_client_from_view()
        
        # Update translation model with LLM settings
        provider = self.view.get_provider()
        webhook_url = self.view.get_webhook_url()
        model_name = self.view.get_model_name()
        self.model.set_llm_settings(provider, webhook_url, model_name)
        
        # Get target language
        target_language = self.view.get_target_language()

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

    def _update_llm_client_from_view(self):
        """Update LLM client configuration from view settings."""
        try:
            provider = self.view.get_provider()
            webhook_url = self.view.get_webhook_url()
            model_name = self.view.get_model_name()
            
            if not webhook_url:
                webhook_url = "http://127.0.0.1:1234/v1"  # Fallback to default
                self.view.webhook_var.set(webhook_url)
            
            if not model_name:
                model_name = "local-model"  # Fallback to default
                self.view.model_var.set(model_name)
            
            # Update LLM client configuration
            self.llm_client.config.webhook_url = webhook_url
            self.llm_client.config.model_name = model_name
            self.llm_client.config.provider = provider
            
            # Save to .env if requested
            if self.view.get_save_settings():
                self.llm_client.save_settings_to_env(webhook_url, model_name, provider)
            
            logger.info(
                f"Translation LLM client configured: provider={provider}, "
                f"model={model_name}, url={webhook_url}"
            )
            
            # Notify registered callbacks about the settings change
            self._notify_llm_settings_changed()
            
            return True
        except Exception as e:
            logger.error(f"Failed to update translation LLM client: {str(e)}")
            return False

    def handle_restore_default_webhook(self):
        """Handle Restore Default Webhook button click"""
        logger.info("Restoring default translation webhook")

        # Restore default provider and URL
        self.view.provider_var.set("lmstudio")
        self.view.webhook_var.set("http://127.0.0.1:1234/v1")
        self.view.model_var.set("local-model")
        
        # Update LLM client
        self._update_llm_client_from_view()
        
        self.view.set_status("Restored default LLM settings")

    def handle_clear_clicked(self):
        """Handle Clear button click"""
        logger.info("Clear button clicked")
        self.view.clear_all()
        self.view.set_status("Ready")
