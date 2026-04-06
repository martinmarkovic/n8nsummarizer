"""
Settings Manager - Persistent user preferences using .env file (v6.3)

Manages user settings that should persist across application sessions:
- Last active tab
- Downloader save path and quality
- Optional YouTube PO token

Settings are stored in .env file (not in config.json which is for app configuration).

Created: 2026-02-15
Version: 6.3.0
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    Manages persistent user settings stored in .env file.
    
    Handles reading and writing user preferences that should be
    remembered between application sessions.
    """
    
    def __init__(self, env_file: str = ".env"):
        """Initialize settings manager.
        
        Args:
            env_file: Path to .env file (relative to project root)
        """
        # Get project root (parent of utils directory)
        project_root = Path(__file__).parent.parent
        self.env_file = project_root / env_file
        self.settings = {}
        
        # Create .env from .env.example if it doesn't exist
        if not self.env_file.exists():
            example_file = project_root / ".env.example"
            if example_file.exists():
                import shutil
                shutil.copy(example_file, self.env_file)
                logger.info(f"Created .env from .env.example")
            else:
                # Create empty .env
                self.env_file.touch()
                logger.info(f"Created empty .env file")
        
        self.load_settings()
    
    def load_settings(self) -> None:
        """Load settings from .env file."""
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    
                    # Parse KEY=VALUE
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        self.settings[key] = value
            
            logger.info(f"Loaded {len(self.settings)} settings from {self.env_file}")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self.settings = {}
    
    def save_settings(self) -> None:
        """Save settings to .env file.
        
        Preserves comments and structure, only updates values.
        """
        try:
            # Read existing file to preserve comments
            lines = []
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            
            # Update values while preserving structure
            updated_keys = set()
            new_lines = []
            
            for line in lines:
                stripped = line.strip()
                
                # Keep comments and empty lines as-is
                if not stripped or stripped.startswith('#'):
                    new_lines.append(line)
                    continue
                
                # Update existing key=value pairs
                if '=' in stripped:
                    key = stripped.split('=', 1)[0].strip()
                    if key in self.settings:
                        new_lines.append(f"{key}={self.settings[key]}\n")
                        updated_keys.add(key)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            # Append new keys that weren't in the file
            for key, value in self.settings.items():
                if key not in updated_keys:
                    new_lines.append(f"{key}={value}\n")
            
            # Write back to file
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            logger.info(f"Saved {len(self.settings)} settings to {self.env_file}")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
    
    def get(self, key: str, default: str = "") -> str:
        """Get setting value.
        
        Args:
            key: Setting key
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get setting value as integer.
        
        Args:
            key: Setting key
            default: Default value if key not found or conversion fails
            
        Returns:
            Setting value as int or default
        """
        value = self.settings.get(key, "")
        try:
            return int(value) if value else default
        except ValueError:
            return default
    
    def set(self, key: str, value: str) -> None:
        """Set setting value.
        
        Args:
            key: Setting key
            value: Setting value
        """
        self.settings[key] = str(value)
        self.save_settings()
    
    # Convenience methods for common settings
    
    def get_last_active_tab(self) -> int:
        """Get last active tab index (0=Summarizer, 1=Translator, 2=Downloader)."""
        return self.get_int("LAST_ACTIVE_TAB", 0)
    
    def set_last_active_tab(self, tab_index: int) -> None:
        """Set last active tab index."""
        self.set("LAST_ACTIVE_TAB", str(tab_index))
    
    def get_downloader_save_path(self) -> str:
        """Get last downloader save path."""
        return self.get("DOWNLOADER_SAVE_PATH", "")
    
    def set_downloader_save_path(self, path: str) -> None:
        """Set downloader save path."""
        self.set("DOWNLOADER_SAVE_PATH", path)
    
    def get_downloader_quality(self) -> str:
        """Get last selected downloader quality."""
        return self.get("DOWNLOADER_QUALITY", "Best Available")
    
    def set_downloader_quality(self, quality: str) -> None:
        """Set downloader quality."""
        self.set("DOWNLOADER_QUALITY", quality)
    
    def get_youtube_po_token(self) -> Optional[str]:
        """Get YouTube PO token if set."""
        token = self.get("YOUTUBE_PO_TOKEN", "")
        return token if token else None
    
    def set_youtube_po_token(self, token: str) -> None:
        """Set YouTube PO token."""
        self.set("YOUTUBE_PO_TOKEN", token)
