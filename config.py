"""
Configuration module for Text File Scanner - Extended Version with Theme Support
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

# Theme Configuration
DEFAULT_THEME = os.getenv('APP_THEME', 'light')  # 'light' or 'dark'

# Light Mode Colors
LIGHT_THEME = {
    'bg_primary': '#f7f9fb',
    'bg_secondary': '#ffffff',
    'text_primary': '#1f2329',
    'text_secondary': '#616061',
    'accent': '#5e5240',  # Brown
    'accent_light': '#e8dfd5',
    'border': '#d1d2d3',
    'button_bg': '#f7f9fb',
    'button_hover': '#e8e9eb',
}

# Dark Mode Colors (Slack-inspired)
DARK_THEME = {
    'bg_primary': '#1a1d21',      # Dark gray (not pure black)
    'bg_secondary': '#222529',    # Slightly lighter gray
    'text_primary': '#e8e8e8',    # Almost white, very light gray
    'text_secondary': '#9ca3af',  # Medium gray for secondary text
    'accent': '#8b5cf6',          # Pleasant purple
    'accent_light': '#6d28d9',    # Darker purple for hover
    'border': '#374151',          # Dark border
    'button_bg': '#2d3139',       # Button background
    'button_hover': '#383c45',    # Button hover
}

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'logs', 'scanner.log')

# File size limits (in MB)
MAX_FILE_SIZE_MB = 50
MAX_CONTENT_LENGTH = 500000  # Characters, for webhook safety

# Export Settings
EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)
