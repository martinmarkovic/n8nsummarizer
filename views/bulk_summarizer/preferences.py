"""
Preference Management for Bulk Summarizer

Handles loading and saving of tab preferences to .env file.
Isolates .env file operations from main tab logic.

Version: 5.0.3
Created: 2026-01-31
"""

from pathlib import Path
from typing import Dict, List
from utils.logger import logger
from .constants import DEFAULT_FILE_TYPES, DEFAULT_OUTPUT_SEPARATE, DEFAULT_OUTPUT_COMBINED, DEFAULT_RECURSIVE


class BulkSummarizerPreferences:
    """
    Manages .env persistence for bulk summarizer settings.
    
    Handles:
    - Loading preferences from .env
    - Saving preferences to .env
    - Default values when .env doesn't exist
    - Preserving non-bulk settings in .env
    """
    
    ENV_PREFIX = "BULK_"
    
    def __init__(self):
        self.env_path = Path(".env")
    
    def load(self) -> Dict:
        """
        Load preferences from .env file.
        
        Returns:
            Dict with keys:
            - file_types: List of selected file type keys
            - output_separate: bool
            - output_combined: bool
            - recursive_subfolders: bool
        """
        try:
            if not self.env_path.exists():
                logger.info("No .env file found, using defaults")
                return self._get_defaults()
            
            prefs = self._get_defaults()
            
            with open(self.env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{self.ENV_PREFIX}FILE_TYPES="):
                        file_types_str = line.split("=", 1)[1]
                        prefs["file_types"] = file_types_str.split(",") if file_types_str else DEFAULT_FILE_TYPES
                    elif line.startswith(f"{self.ENV_PREFIX}OUTPUT_SEPARATE="):
                        prefs["output_separate"] = line.split("=", 1)[1].lower() == "true"
                    elif line.startswith(f"{self.ENV_PREFIX}OUTPUT_COMBINED="):
                        prefs["output_combined"] = line.split("=", 1)[1].lower() == "true"
                    elif line.startswith(f"{self.ENV_PREFIX}RECURSIVE_SUBFOLDERS="):
                        prefs["recursive_subfolders"] = line.split("=", 1)[1].lower() == "true"
            
            logger.info("Bulk Summarizer preferences loaded")
            return prefs
        
        except Exception as e:
            logger.warning(f"Could not load preferences: {str(e)}")
            return self._get_defaults()
    
    def save(self, file_types: List[str], output_separate: bool, 
             output_combined: bool, recursive_subfolders: bool):
        """
        Save preferences to .env file.
        
        Args:
            file_types: List of selected file type keys
            output_separate: Whether separate output is enabled
            output_combined: Whether combined output is enabled
            recursive_subfolders: Whether recursive scanning is enabled
        """
        try:
            # Read existing .env content (preserve non-bulk settings)
            env_content = {}
            if self.env_path.exists():
                with open(self.env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith(self.ENV_PREFIX):
                            key_value = line.split("=", 1)
                            if len(key_value) == 2:
                                env_content[key_value[0]] = key_value[1]
            
            # Update with new bulk preferences
            file_types_str = ",".join(file_types) if file_types else "txt"
            env_content[f"{self.ENV_PREFIX}FILE_TYPES"] = file_types_str
            env_content[f"{self.ENV_PREFIX}OUTPUT_SEPARATE"] = str(output_separate)
            env_content[f"{self.ENV_PREFIX}OUTPUT_COMBINED"] = str(output_combined)
            env_content[f"{self.ENV_PREFIX}RECURSIVE_SUBFOLDERS"] = str(recursive_subfolders)
            
            # Write back to .env
            with open(self.env_path, "w") as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            
            logger.info("Bulk Summarizer preferences saved")
        
        except Exception as e:
            logger.warning(f"Could not save preferences: {str(e)}")
    
    def _get_defaults(self) -> Dict:
        """Get default preferences"""
        return {
            "file_types": DEFAULT_FILE_TYPES,
            "output_separate": DEFAULT_OUTPUT_SEPARATE,
            "output_combined": DEFAULT_OUTPUT_COMBINED,
            "recursive_subfolders": DEFAULT_RECURSIVE
        }
