"""
File Model - Business logic for file operations

Responsibilities:
    - Read files (text, csv, json, .docx, .srt)
    - Extract file information (size, line count, character count)
    - Validate file format
    - Export to text/docx formats
    
This is PURE business logic - NO UI dependencies.
Can be tested independently without GUI.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from config import DEFAULT_ENCODING, EXPORT_DIR
from utils.logger import logger
from utils.validators import validate_file, validate_content_not_empty


class FileModel:
    """Handles all file-related operations"""
    
    def read_file(self, file_path: str) -> tuple[bool, str, str]:
        """
        Read file content with support for multiple formats.
        Supports: .txt, .srt, .json, .docx, and text-based formats.
        
        Args:
            file_path (str): Path to file to read
            
        Returns:
            tuple: (success: bool, content: str, error_msg: str or None)
            
        Example:
            >>> model = FileModel()
            >>> success, content, error = model.read_file('test.txt')
            >>> if success:
            ...     print(f"Read {len(content)} characters")
        """
        # Validate file exists and is readable
        valid, error = validate_file(file_path)
        if not valid:
            logger.error(f"File validation failed: {error}")
            return False, "", error
        
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
            
            # Validate content is not empty
            valid, error = validate_content_not_empty(content)
            if not valid:
                logger.warning(f"File is empty: {file_path}")
                return False, "", error
            
            logger.info(f"Successfully read file: {file_path} ({ext})")
            return True, content, None
            
        except UnicodeDecodeError as e:
            error = f"File encoding error - try .txt format: {str(e)}"
            logger.error(error)
            return False, "", error
        except Exception as e:
            error = f"Error reading file: {str(e)}"
            logger.error(error)
            return False, "", error
    
    def _read_docx(self, file_path: str) -> str:
        """Read .docx file and extract text"""
        try:
            from docx import Document
            doc = Document(file_path)
            text = '\n'.join([para.text for para in doc.paragraphs])
            return text
        except ImportError:
            logger.warning("python-docx not installed")
            raise ImportError("python-docx library required to read DOCX files. Install with: pip install python-docx")
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            raise
    
    def _read_json(self, file_path: str) -> str:
        """Read .json file and pretty-print it"""
        with open(file_path, 'r', encoding=DEFAULT_ENCODING) as f:
            data = json.load(f)
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    def _read_srt(self, file_path: str) -> str:
        """Read .srt subtitle file and extract text only (skip timecodes)"""
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
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Extract file metadata.
        
        Args:
            file_path (str): Path to file
            
        Returns:
            dict: File information
                {
                    'name': filename,
                    'path': full_path,
                    'size_kb': size in KB,
                    'lines': line count,
                    'characters': total characters,
                    'characters_no_spaces': without whitespace
                }
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return {}
            
            # Read file to count lines/characters
            success, content, error = self.read_file(file_path)
            if not success:
                return {}
            
            file_stat = os.stat(file_path)
            
            return {
                'name': os.path.basename(file_path),
                'path': file_path,
                'size': file_stat.st_size,
                'size_kb': file_stat.st_size / 1024,
                'lines': len(content.split('\n')),
                'characters': len(content),
                'characters_no_spaces': len(content.replace(' ', '').replace('\n', ''))
            }
        except Exception as e:
            logger.error(f"Error getting file info: {e}")
            return {}
    
    def export_txt(self, content: str, filepath: str) -> tuple[bool, str]:
        """
        Export content as .txt file.
        
        Args:
            content (str): Content to export
            filepath (str): Where to save file
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Exported .txt to: {filepath}")
            return True, f"Exported to {filepath}"
        except Exception as e:
            error = f"Export failed: {str(e)}"
            logger.error(error)
            return False, error
    
    def export_docx(self, content: str, filepath: str) -> tuple[bool, str]:
        """
        Export content as .docx file.
        
        Args:
            content (str): Content to export
            filepath (str): Where to save file
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            from docx import Document
            
            document = Document()
            document.add_heading('n8n Response Summary', 0)
            document.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            document.add_paragraph()
            
            # Split content into paragraphs for better formatting
            for paragraph in content.split('\n'):
                if paragraph.strip():
                    document.add_paragraph(paragraph)
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            document.save(filepath)
            
            logger.info(f"Exported .docx to: {filepath}")
            return True, f"Exported to {filepath}"
        except ImportError:
            error = "python-docx not installed. Install with: pip install python-docx"
            logger.error(error)
            return False, error
        except Exception as e:
            error = f"Export failed: {str(e)}"
            logger.error(error)
            return False, error
    
    def generate_filename(self, original_path: str, suffix: str = "_Summary", 
                         format: str = "txt") -> str:
        """
        Generate export filename intelligently.
        
        Args:
            original_path (str): Original file path
            suffix (str): Suffix to add before extension
            format (str): File format ('txt' or 'docx')
            
        Returns:
            str: New filename
            
        Example:
            >>> model = FileModel()
            >>> filename = model.generate_filename(
            ...     '/path/to/document.pdf',
            ...     suffix='_Summary',
            ...     format='txt'
            ... )
            >>> print(filename)
            '/path/to/document_Summary.txt'
        """
        base = os.path.splitext(original_path)[0]
        return f"{base}{suffix}.{format}"
    
    def generate_timestamp_filename(self, format: str = "txt") -> str:
        """
        Generate filename based on current timestamp.
        
        Args:
            format (str): File format ('txt' or 'docx')
            
        Returns:
            str: Filename like 'n8n_response_20250207_144235.txt'
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"n8n_response_{timestamp}.{format}"
