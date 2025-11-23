"""
Configuration module for Text File Scanner
"""
import os
from dotenv import load_dotenv

load_dotenv()

# n8n Configuration
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook-test/hook1')
N8N_TIMEOUT = int(os.getenv('N8N_TIMEOUT', '10'))

# Application Settings
APP_TITLE = "Text File Scanner"
APP_WIDTH = 600
APP_HEIGHT = 700
DEFAULT_ENCODING = 'utf-8'
SUPPORTED_EXTENSIONS = ['.txt', '.log', '.csv', '.json', '.xml']

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'scanner.log')