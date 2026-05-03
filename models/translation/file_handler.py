"""
Translation File Handler - File operations for translation workflow (Phase 4)

Handles file-related operations for the translation workflow:
- File path management
- File content loading
- File type detection (especially SRT files)

This component separates file I/O concerns from translation business logic,
making the TranslationModel more focused on its core translation responsibilities.

Created: 2026-05-03
Version: 1.0.0 - Phase 4 Architectural Improvements
"""

import os
from pathlib import Path
from typing import Tuple, Optional
from utils.logger import logger


class TranslationFileHandler:
    """Handles file operations for translation workflow."""
    
    def __init__(self):
        """Initialize file handler."""
        self.current_file_path = None
    
    def set_current_file_path(self, path: str):
        """
        Set the current file path.
        
        Args:
            path: Path to the current file
        """
        self.current_file_path = path
        logger.info(f"Set current file path: {self.current_file_path}")
    
    def get_current_file_path(self) -> str:
        """
        Get the current file path.
        
        Returns:
            str: The current file path
        """
        return self.current_file_path
    
    def is_srt_source(self, text: str) -> bool:
        """
        Return True if current file path ends with .srt or content is SRT-like.
        
        Args:
            text: Text content to analyze
            
        Returns:
            bool: True if source appears to be SRT
        """
        # Check file extension first
        if self.current_file_path and self.current_file_path.lower().endswith('.srt'):
            return True
        
        # Fallback to content detection using SRT support module
        from models.translation.srt_support import is_srt_like
        return is_srt_like(text)
    
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
    
    def get_file_info(self) -> dict:
        """
        Get information about the current file.
        
        Returns:
            Dictionary with file information or empty dict if no file set
        """
        if not self.current_file_path:
            return {}
        
        try:
            file_path = Path(self.current_file_path)
            return {
                'name': file_path.name,
                'path': str(file_path),
                'exists': file_path.exists(),
                'size': file_path.stat().st_size if file_path.exists() else 0,
                'extension': file_path.suffix.lower()
            }
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return {}
    
    def clear_file(self) -> None:
        """Clear current file information."""
        self.current_file_path = None
        logger.info("Cleared current file information")