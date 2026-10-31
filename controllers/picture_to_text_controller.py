"""
Picture to Text Controller - Coordinates PictureToTextTab <-> OCRModel.

Responsibilities:
    - Listen to Picture to Text tab UI events
    - Call OCRModel to run image-to-text extraction
    - Update the view with results and errors
    - Run the blocking request on a background thread

Controller is THIN - it coordinates, it does not contain OCR logic.
Follows the same pattern as TranslationController.
"""

import os
import queue
import threading

from models.ocr_model import OCRModel
from utils.logger import logger


class PictureToTextController:
    """Coordinates the Picture to Text tab UI and the OCR model."""

    def __init__(self, view):
        """
        Args:
            view: PictureToTextTab view instance.
        """
        self.view = view
        self.model = OCRModel()

        # Background thread management
        self.extraction_thread = None
        self.result_queue = queue.Queue()

        # Wire up view callbacks
        self.view.on_image_selected = self.handle_image_selected
        self.view.on_extract_clicked = self.handle_extract_clicked
        self.view.on_clear_clicked = self.handle_clear_clicked

        logger.info("PictureToTextController initialized")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def handle_image_selected(self, file_path: str):
        """Store the selected image and show its name as status."""
        logger.info(f"Image selected for OCR: {file_path}")
        self.view.set_image_path(file_path)
        self.view.set_status(f"Loaded: {os.path.basename(file_path)}")

    def handle_extract_clicked(self):
        """Validate inputs and start extraction on a background thread."""
        logger.info("Extract text clicked")

        image_path = self.view.get_image_path()
        if not image_path:
            self.view.show_error("No image selected. Choose an image first.")
            return

        provider = self.view.get_provider()
        base_url = self.view.get_webhook_url()
        model_name = self.view.get_model_name()
        prompt = self.view.get_prompt()

        if not model_name:
            self.view.show_error(
                "No model selected. Test the connection and pick a model first."
            )
            return

        self.view.set_extracting_state(True)
        self.view.set_status("Extracting text...")
        self.view.set_output_text("")

        self.extraction_thread = threading.Thread(
            target=self._extraction_worker,
            args=(image_path, provider, base_url, model_name, prompt),
            daemon=True,
        )
        self.extraction_thread.start()
        self._check_result()

    def handle_clear_clicked(self):
        """Clear the tab."""
        logger.info("Clear clicked")
        self.view.clear_all()
        self.view.set_status("Ready")

    # ------------------------------------------------------------------
    # Worker + polling
    # ------------------------------------------------------------------

    def _extraction_worker(self, image_path, provider, base_url, model_name, prompt):
        """Background thread: run the OCR request and queue the result."""
        try:
            success, text, error = self.model.extract_text(
                image_path=image_path,
                provider=provider,
                base_url=base_url,
                model_name=model_name,
                prompt=prompt,
            )
            if success:
                self.result_queue.put(("success", text or ""))
            else:
                self.result_queue.put(("error", error or "Unknown OCR error"))
        except Exception as e:
            error_msg = f"Unexpected OCR error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.result_queue.put(("error", error_msg))

    def _check_result(self):
        """Poll the result queue from the UI thread."""
        try:
            status, message = self.result_queue.get_nowait()
            self.view.set_extracting_state(False)
            if status == "success":
                self.view.set_output_text(message)
                self.view.set_status("Extraction complete")
            else:
                self.view.show_error(message)
                self.view.set_status(f"Extraction failed: {message}")
        except queue.Empty:
            if self.view.get_extracting_state():
                self.view.root.after(100, self._check_result)
