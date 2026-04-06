"""
File Scanner Utility - Centralized File Scanning Logic

Provides unified file scanning with extension filters.
Eliminated duplicate code from multiple tabs.

Version: 5.0.3
Created: 2026-01-31
"""

from pathlib import Path
from typing import List


class FileScanner:
    """
    Unified file scanning with extension filters.
    
    Provides:
    - Fast file counting without metadata
    - Recursive and non-recursive scanning
    - Multiple extension support
    - List of matching file paths
    """
    
    @staticmethod
    def count(folder: str, extensions: List[str], recursive: bool = False) -> int:
        """
        Fast count of files matching extensions.
        
        Args:
            folder: Folder path to scan
            extensions: List of extensions to match (e.g., ['txt', 'srt'])
            recursive: Whether to scan subfolders
        
        Returns:
            Number of matching files
        """
        folder_path = Path(folder)
        count = 0
        
        glob_method = folder_path.rglob if recursive else folder_path.glob
        
        for ext in extensions:
            pattern = f"*.{ext}"
            count += len(list(glob_method(pattern)))
        
        return count
    
    @staticmethod
    def scan(folder: str, extensions: List[str], recursive: bool = False) -> List[Path]:
        """
        Scan for files matching extensions.
        
        Args:
            folder: Folder path to scan
            extensions: List of extensions to match
            recursive: Whether to scan subfolders
        
        Returns:
            List of Path objects for matching files
        """
        folder_path = Path(folder)
        files = []
        
        glob_method = folder_path.rglob if recursive else folder_path.glob
        
        for ext in extensions:
            pattern = f"*.{ext}"
            files.extend(glob_method(pattern))
        
        return files
