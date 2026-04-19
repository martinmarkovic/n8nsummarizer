"""
Translation Model - Business logic for translation functionality

Responsibilities:
    - Translation API communication (LM Studio/n8n webhooks)
    - File content loading and extraction
    - Webhook URL persistence
    - Translation prompt construction
    - Error handling and validation

This model follows the same pattern as other models in the project
(e.g., models/n8n/client.py, models/file_model.py).
"""

import os
import json
from pathlib import Path
from typing import Tuple, Optional
import requests
from config import TRANSLATION_DEFAULT_URL
from utils.logger import logger


class TranslationModel:
    """Translation business logic and data operations."""

    def __init__(self):
        """Initialize translation model with default configuration."""
        self.webhook_url = TRANSLATION_DEFAULT_URL
        logger.info(
            f"TranslationModel initialized with default webhook: {self.webhook_url}"
        )

    def translate_text(
        self, text: str, target_language: str
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Send text to translation webhook and return translated result.

        Args:
            text: Source text to translate
            target_language: Target language for translation

        Returns:
            Tuple of (success: bool, result: str, error: Optional[str])
        """
        if not text or not text.strip():
            return False, "", "No text provided for translation"

        if not self.webhook_url:
            return False, "", "Translation webhook URL not configured"

        try:
            # Construct translation prompt
            prompt_template = f"Output translation only. Translate following text to {target_language}: {text}"

            payload = {
                "model": "translategemma:4b-it",
                "prompt": prompt_template,
                "temperature": 0.3,
                "max_tokens": 500,
            }

            logger.info(f"Sending translation request to: {self.webhook_url}")
            logger.debug(f"Translation payload size: {len(json.dumps(payload))} bytes")

            response = requests.post(
                self.webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
                timeout=300,  # 5 minutes for very large texts
            )

            logger.info(f"Translation API response status: {response.status_code}")

            if response.status_code in [200, 201, 202]:
                response_data = response.json()
                translated_text = response_data.get("choices", [{}])[0].get("text", "")
                logger.info(
                    f"Translation successful, received {len(translated_text)} characters"
                )
                return True, translated_text, None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"Translation API error: {error_msg}")
                return False, "", error_msg

        except requests.exceptions.Timeout:
            error_msg = "Request timed out after 5 minutes"
            logger.error(error_msg)
            return False, "", error_msg

        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to translation service (LM Studio)"
            logger.error(error_msg)
            return False, "", error_msg

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response from translation service: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

        except Exception as e:
            error_msg = f"Unexpected translation error: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

    def load_file_content(self, file_path: str) -> Tuple[bool, str, Optional[str]]:
        """
        Load text content from file.

        Args:
            file_path: Path to file to load

        Returns:
            Tuple of (success: bool, content: str, error: Optional[str])
        """
        if not file_path or not os.path.exists(file_path):
            return False, "", f"File not found: {file_path}"

        try:
            path = Path(file_path)
            content = path.read_text(encoding="utf-8", errors="replace")
            logger.info(f"Loaded file: {file_path} ({len(content)} characters)")
            return True, content, None

        except Exception as e:
            error_msg = f"Error loading file {file_path}: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg

    def save_webhook_to_env(self, url: str) -> bool:
        """
        Save webhook URL to .env file for persistence.

        Args:
            url: Webhook URL to save

        Returns:
            bool: True if successful, False otherwise
        """
        try:
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

            logger.info(f"Saved translation webhook to .env: {url}")
            self.webhook_url = url
            return True

        except Exception as e:
            logger.error(f"Failed to save webhook to .env: {str(e)}")
            return False

    def restore_default_webhook(self) -> str:
        """
        Restore default webhook URL.

        Returns:
            str: The restored default URL
        """
        self.webhook_url = TRANSLATION_DEFAULT_URL
        logger.info(f"Restored default translation webhook: {self.webhook_url}")
        return self.webhook_url

    def set_webhook_url(self, url: str):
        """
        Set webhook URL in memory (does not persist to .env).

        Args:
            url: Webhook URL to use
        """
        self.webhook_url = url
        logger.info(f"Set translation webhook URL: {self.webhook_url}")
