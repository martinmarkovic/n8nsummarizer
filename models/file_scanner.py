"""
Enhanced File Scanner Model - Supports .srt, .json, .docx
"""
import os
import json
from config import DEFAULT_ENCODING
from utils.logger import logger
from utils.validators import validate_file, validate_content_not_empty


class FileScanner:
    """Model for scanning and extracting text from multiple file types"""
    
    def __init__(self):
        self.current_file = None
        self.current_content = None
    
    def read_file(self, file_path):
        """
        Read file content with validation - supports .txt, .srt, .json, .docx, etc.
        
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
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            # Handle different file types
            if ext == '.docx':
                content = self._read_docx(file_path)
            elif ext == '.json':
                content = self._read_json(file_path)
            elif ext == '.srt':
                content = self._read_srt(file_path)
            else:
                # Default: read as text
                with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
                    content = f.read()
            
            # Validate content not empty
            valid, error = validate_content_not_empty(content)
            if not valid:
                logger.warning(f"File is empty: {file_path}")
                return False, None, error
            
            self.current_file = file_path
            self.current_content = content
            logger.info(f"Successfully read file: {file_path} ({ext})")
            return True, content, None
            
        except UnicodeDecodeError as e:
            error_msg = f"Failed to decode file (encoding issue): {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    def _read_docx(self, file_path):
        """Read .docx file and extract text"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = '\n'.join([para.text for para in doc.paragraphs])
            return text
        except ImportError:
            logger.warning("python-docx not installed, returning filename instead")
            return f"[DOCX file: {os.path.basename(file_path)} - install 'python-docx' to read content]"
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            raise
    
    def _read_json(self, file_path):
        """Read .json file and pretty-print it"""
        with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
            data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _read_srt(self, file_path):
        """Read .srt subtitle file and extract text"""
        with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
            content = f.read()
        
        # Parse SRT: extract only subtitle text (skip numbers and timecodes)
        lines = content.split('\n')
        subtitles = []
        for line in lines:
            # Skip empty lines, numbers, and timecode lines
            line = line.strip()
            if line and not line.isdigit() and '-->' not in line:
                subtitles.append(line)
        
        return '\n'.join(subtitles)
    
    def get_file_info(self):
        """Get info about currently loaded file including character count"""
        if not self.current_file:
            return None
        
        char_count = len(self.current_content) if self.current_content else 0
        
        return {
            'name': os.path.basename(self.current_file),
            'path': self.current_file,
            'size': os.path.getsize(self.current_file),
            'size_kb': os.path.getsize(self.current_file) / 1024,
            'lines': len(self.current_content.splitlines()) if self.current_content else 0,
            'characters': char_count,
            'characters_no_spaces': len(self.current_content.replace(' ', '')) if self.current_content else 0
        }
    
    def clear(self):
        """Clear current file and content"""
        self.current_file = None
        self.current_content = None
        logger.info("Cleared current file")
    
    def get_content(self):
        """Get current file content"""
        return self.current_content