"""
Validators utility module
"""
import os
from config import SUPPORTED_EXTENSIONS, DEFAULT_ENCODING


def validate_file_exists(file_path):
    """Check if file exists"""
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    return True, None


def validate_file_extension(file_path):
    """Check if file has supported extension"""
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        return False, f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
    return True, None


def validate_file_readable(file_path):
    """Check if file is readable"""
    if not os.access(file_path, os.R_OK):
        return False, f"File is not readable: {file_path}"
    return True, None


def validate_file(file_path):
    """Validate file: exists, has correct extension, and is readable"""
    valid, msg = validate_file_exists(file_path)
    if not valid:
        return valid, msg
    
    valid, msg = validate_file_extension(file_path)
    if not valid:
        return valid, msg
    
    valid, msg = validate_file_readable(file_path)
    return valid, msg


def validate_content_not_empty(content):
    """Check if content is not empty"""
    if not content or not content.strip():
        return False, "File content is empty"
    return True, None