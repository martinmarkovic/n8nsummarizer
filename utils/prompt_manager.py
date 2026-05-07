"""
Prompt Manager Module

Manages prompt presets with a two-tier system: default prompts (read-only)
and custom prompts (user-managed). Provides methods for loading, saving,
and managing prompts.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any


class PromptManager:
    """Manages prompt presets with default and custom tiers."""

    SEPARATOR = "───────────"

    def __init__(self, prompts_file: str = "data/prompts.json"):
        """
        Initialize the PromptManager.

        Args:
            prompts_file: Path to the prompts JSON file
        """
        self.prompts_file = prompts_file
        self.defaults: List[Dict[str, str]] = []
        self.custom: List[Dict[str, str]] = []
        self.default_selected: str = ""
        self._load()

    def _load(self) -> None:
        """Load prompts from the JSON file."""
        try:
            with open(self.prompts_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Migrate old structure if necessary
            if "presets" in data:
                self.defaults = [{"name": k, "prompt": v} for k, v in data["presets"].items()]
                self.custom = []
                self.default_selected = data.get("default_selected", "General Summary")
                self._write()
                return

            # Load new structure
            self.defaults = data.get("defaults", [])
            self.custom = data.get("custom", [])
            self.default_selected = data.get("default_selected", "General Summary")

        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is invalid, create default structure
            self.defaults = []
            self.custom = []
            self.default_selected = "General Summary"
            self._write()

    def _write(self) -> None:
        """Write prompts to the JSON file."""
        data = {
            "defaults": self.defaults,
            "custom": self.custom,
            "default_selected": self.default_selected
        }

        # Ensure the data directory exists
        os.makedirs(os.path.dirname(self.prompts_file), exist_ok=True)

        with open(self.prompts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_names(self) -> List[str]:
        """
        Get a list of all prompt names.

        Returns:
            List of names with defaults first, then separator, then custom
        """
        names = [prompt["name"] for prompt in self.defaults]

        if self.custom:
            names.append(self.SEPARATOR)
            names.extend(prompt["name"] for prompt in self.custom)

        return names

    def get_prompt(self, name: str) -> str:
        """
        Get the prompt text for a given name.

        Args:
            name: Name of the prompt

        Returns:
            The prompt text

        Raises:
            KeyError: If the prompt is not found
        """
        # Search defaults first
        for prompt in self.defaults:
            if prompt["name"] == name:
                return prompt["prompt"]

        # Then search custom
        for prompt in self.custom:
            if prompt["name"] == name:
                return prompt["prompt"]

        raise KeyError(f"Prompt '{name}' not found")

    def get_default(self) -> str:
        """
        Get the default selected prompt name.

        Returns:
            The default selected prompt name
        """
        return self.default_selected

    def set_default(self, name: str) -> None:
        """
        Set the default selected prompt.

        Args:
            name: Name of the prompt to set as default

        Raises:
            ValueError: If the name is the separator
        """
        if name == self.SEPARATOR:
            raise ValueError("Cannot set separator as default")

        # Verify the name exists
        if not self.is_default(name) and not self.is_custom(name):
            raise ValueError(f"Prompt '{name}' not found")

        self.default_selected = name
        self._write()

    def is_custom(self, name: str) -> bool:
        """
        Check if a prompt is custom.

        Args:
            name: Name of the prompt

        Returns:
            True if the prompt is custom, False otherwise
        """
        return any(prompt["name"] == name for prompt in self.custom)

    def is_default(self, name: str) -> bool:
        """
        Check if a prompt is a default.

        Args:
            name: Name of the prompt

        Returns:
            True if the prompt is a default, False otherwise
        """
        return any(prompt["name"] == name for prompt in self.defaults)

    def add_custom(self, name: str, prompt: str) -> None:
        """
        Add a custom prompt.

        Args:
            name: Name of the custom prompt
            prompt: Prompt text

        Raises:
            ValueError: If the name already exists or is the separator
        """
        if name == self.SEPARATOR:
            raise ValueError("Prompt name cannot be the separator")

        if self.is_default(name):
            raise ValueError(f"Prompt '{name}' already exists as a default")

        if self.is_custom(name):
            raise ValueError(f"Prompt '{name}' already exists as a custom prompt")

        self.custom.append({"name": name, "prompt": prompt})
        self._write()

    def delete_custom(self, name: str) -> None:
        """
        Delete a custom prompt.

        Args:
            name: Name of the custom prompt to delete

        Raises:
            ValueError: If the prompt is a default or the separator
            KeyError: If the prompt is not found
        """
        if name == self.SEPARATOR:
            raise ValueError("Cannot delete the separator")

        if self.is_default(name):
            raise ValueError("Cannot delete a default prompt")

        # Find and remove the custom prompt
        for i, prompt in enumerate(self.custom):
            if prompt["name"] == name:
                del self.custom[i]
                
                # If the deleted prompt was the default, reset to first default
                if self.default_selected == name:
                    self.default_selected = self.defaults[0]["name"] if self.defaults else ""
                    
                self._write()
                return

        raise KeyError(f"Custom prompt '{name}' not found")
