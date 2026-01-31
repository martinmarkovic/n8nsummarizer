"""
Bulk Transcriber Preferences - .env file persistence

Manages saving and loading user preferences for the Bulk Transcriber tab.
Handles .env file I/O while preserving other application settings.

Version: 1.0
Created: 2026-01-31
Phase: v5.0.4 - Phase 3 Code Quality
"""

from pathlib import Path
from .constants import (
    ENV_PREFIX,
    DEFAULT_MEDIA_TYPES,
    DEFAULT_OUTPUT_FORMATS,
    DEFAULT_RECURSIVE
)
from utils.logger import logger


class BulkTranscriberPreferences:
    """
    Manages .env persistence for Bulk Transcriber preferences.
    
    Responsibilities:
    - Load preferences from .env on startup
    - Save preferences to .env when changed
    - Preserve non-transcriber settings in .env
    - Provide defaults if .env missing or corrupt
    """
    
    # Environment variable keys
    KEY_MEDIA_TYPES = f"{ENV_PREFIX}MEDIA_TYPES"
    KEY_OUTPUT_FORMATS = f"{ENV_PREFIX}OUTPUT_FORMATS"
    KEY_RECURSIVE = f"{ENV_PREFIX}RECURSIVE_SUBFOLDERS"
    
    def __init__(self, env_path: str = ".env"):
        """
        Initialize preferences manager.
        
        Args:
            env_path: Path to .env file (default ".env")
        """
        self.env_path = Path(env_path)
    
    def load(self) -> dict:
        """
        Load preferences from .env file.
        
        Returns:
            Dict with keys:
            - media_types: list of selected extensions
            - output_formats: list of selected formats
            - recursive_subfolders: bool
        """
        preferences = {
            "media_types": DEFAULT_MEDIA_TYPES.copy(),
            "output_formats": DEFAULT_OUTPUT_FORMATS.copy(),
            "recursive_subfolders": DEFAULT_RECURSIVE
        }
        
        try:
            if self.env_path.exists():
                with open(self.env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        
                        if line.startswith(self.KEY_MEDIA_TYPES):
                            value = line.split("=", 1)[1]
                            if value:
                                preferences["media_types"] = value.split(",")
                        
                        elif line.startswith(self.KEY_OUTPUT_FORMATS):
                            value = line.split("=", 1)[1]
                            if value:
                                preferences["output_formats"] = value.split(",")
                        
                        elif line.startswith(self.KEY_RECURSIVE):
                            value = line.split("=", 1)[1]
                            preferences["recursive_subfolders"] = value.lower() == "true"
                
                logger.info("Bulk Transcriber preferences loaded from .env")
            else:
                logger.info("No .env file found, using default Bulk Transcriber preferences")
        
        except Exception as e:
            logger.warning(f"Error loading Bulk Transcriber preferences: {str(e)}, using defaults")
        
        return preferences
    
    def save(self, media_types: list, output_formats: list, recursive_subfolders: bool):
        """
        Save preferences to .env file.
        Preserves all non-transcriber settings.
        
        Args:
            media_types: List of selected media type extensions
            output_formats: List of selected output format extensions
            recursive_subfolders: Boolean for recursive scanning
        """
        try:
            # Read existing .env content, filtering out our keys
            env_content = {}
            if self.env_path.exists():
                with open(self.env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith(ENV_PREFIX):
                            parts = line.split("=", 1)
                            if len(parts) == 2:
                                env_content[parts[0]] = parts[1]
            
            # Build preference strings with defaults if empty
            media_types_str = ",".join(media_types) if media_types else "mp4"
            output_formats_str = ",".join(output_formats) if output_formats else "srt"
            
            # Update with our preferences
            env_content[self.KEY_MEDIA_TYPES] = media_types_str
            env_content[self.KEY_OUTPUT_FORMATS] = output_formats_str
            env_content[self.KEY_RECURSIVE] = str(recursive_subfolders)
            
            # Write back to .env
            with open(self.env_path, "w") as f:
                for key, value in env_content.items():
                    f.write(f"{key}={value}\n")
            
            logger.info("Bulk Transcriber preferences saved to .env")
        
        except Exception as e:
            logger.warning(f"Error saving Bulk Transcriber preferences: {str(e)}")
