"""
Configuration module for Text File Scanner - Extended Version
"""
import os
from dotenv import load_dotenv

load_dotenv()

# n8n Configuration
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook-test/hook1')
N8N_TIMEOUT = int(os.getenv('N8N_TIMEOUT', '30'))

# Application Settings
APP_TITLE = "Text File Scanner - Extended"
APP_WIDTH = 1400  # Twice wider (was 600)
APP_HEIGHT = 800
DEFAULT_ENCODING = 'utf-8'
SUPPORTED_EXTENSIONS = ['.txt', '.log', '.csv', '.json', '.xml', '.srt', '.docx']

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'scanner.log')

# File size limits (in MB)
MAX_FILE_SIZE_MB = 50
MAX_CONTENT_LENGTH = 500000  # Characters, for webhook safety