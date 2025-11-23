"""
File Scanner Model - Handles file reading and text extraction
"""
import os
from config import DEFAULT_ENCODING
from utils.logger import logger
from utils.validators import validate_file, validate_content_not_empty


class FileScanner:
    """Model for scanning and extracting text from files"""
    
    def __init__(self):
        self.current_file = None
        self.current_content = None
    
    def read_file(self, file_path):
        """
        Read file content with validation
        
        Args:
            file_path (str): Path to file to read
            
        Returns:
            tuple: (success: bool, content: str or None, error_msg: str or None)
        """
        # Validate file
        valid, error = validate_file(file_path)
        if not valid:
            logger.error(f"File validation failed: {error}")
            return False, None, error
        
        try:
            with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
                content = f.read()
            
            # Validate content not empty
            valid, error = validate_content_not_empty(content)
            if not valid:
                logger.warning(f"File is empty: {file_path}")
                return False, None, error
            
            self.current_file = file_path
            self.current_content = content
            logger.info(f"Successfully read file: {file_path}")
            return True, content, None
            
        except UnicodeDecodeError as e:
            error_msg = f"Failed to decode file (encoding issue): {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def get_file_info(self):
        """Get info about currently loaded file"""
        if not self.current_file:
            return None
        
        return {
            'name': os.path.basename(self.current_file),
            'path': self.current_file,
            'size': os.path.getsize(self.current_file),
            'size_kb': os.path.getsize(self.current_file) / 1024,
            'lines': len(self.current_content.splitlines()) if self.current_content else 0
        }
    
    def clear(self):
        """Clear current file and content"""
        self.current_file = None
        self.current_content = None
        logger.info("Cleared current file")
    
    def get_content(self):
        """Get current file content"""
        return self.current_content