"""
Logging utility module

v4.4.3: Fixed Unicode encoding issue on Windows console
Problem: checkmark (✓) and cross (✗) caused UnicodeEncodeError in cp1250 encoding
Solution: Force UTF-8 encoding for console output
"""
import logging
import os
import sys
from config import LOG_LEVEL, LOG_FILE

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configure logger
logger = logging.getLogger('TextFileScanner')
logger.setLevel(getattr(logging, LOG_LEVEL))

# File handler - UTF-8 encoding for all unicode support
file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
file_handler.setLevel(getattr(logging, LOG_LEVEL))

# Console handler with UTF-8 encoding
# This fixes the UnicodeEncodeError on Windows console (cp1250 encoding issue)
try:
    # Try to reconfigure stdout to use UTF-8
    if sys.stdout.encoding and 'utf' not in sys.stdout.encoding.lower():
        # Windows console often uses cp1250, switch to UTF-8 for unicode support
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
except:
    pass  # If reconfiguration fails, continue with default

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(getattr(logging, LOG_LEVEL))

# Formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Add handlers
logger.addHandler(file_handler)
logger.addHandler(console_handler)
