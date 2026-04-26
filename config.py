"""
Configuration module for n8n Summarizer v6.0
"""

import os
from dotenv import load_dotenv

load_dotenv()

# n8n Configuration
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL", "http://localhost:5678/webhook-test/hook1"
)
N8N_TIMEOUT = int(
    os.getenv("N8N_TIMEOUT", "120")
)  # Increased from 30 to 120 seconds for large files

# Translation Configuration
TRANSLATION_DEFAULT_URL = os.getenv(
    "TRANSLATION_URL", "http://127.0.0.1:1234/v1/completions"
)
TRANSLATION_TIMEOUT = int(
    os.getenv("TRANSLATION_TIMEOUT", "300")
)  # 5 minutes for large translations
TRANSLATION_MAX_TOKENS = int(
    os.getenv("TRANSLATION_MAX_TOKENS", "70000")
)  # Max tokens per API call (increased to 70000)
TRANSLATION_CHUNK_SIZE = int(
    os.getenv("TRANSLATION_CHUNK_SIZE", "4500")
)  # Characters per chunk (approximate)
TRANSLATION_BATCH_MAX_ITEMS = int(
    os.getenv("TRANSLATION_BATCH_MAX_ITEMS", "5")
)  # Max subtitles per batch (reduced for reliability)
TRANSLATION_BATCH_MAX_CHARS = int(
    os.getenv("TRANSLATION_BATCH_MAX_CHARS", "800")
)  # Max characters per batch (reduced for reliability)

# Application Settings
APP_TITLE = "n8n Summarizer"
APP_WIDTH = 1400
APP_HEIGHT = 800
DEFAULT_ENCODING = "utf-8"
SUPPORTED_EXTENSIONS = [".txt", ".log", ".csv", ".json", ".xml", ".srt", ".docx"]

# Theme Configuration
DEFAULT_THEME = os.getenv("APP_THEME", "light")  # 'light' or 'dark'

# Light Mode Colors
LIGHT_THEME = {
    "bg_primary": "#f7f9fb",
    "bg_secondary": "#ffffff",
    "text_primary": "#1f2329",
    "text_secondary": "#616061",
    "accent": "#5e5240",  # Brown
    "accent_light": "#e8dfd5",
    "border": "#d1d2d3",
    "button_bg": "#f7f9fb",
    "button_hover": "#e8e9eb",
}

# Dark Mode Colors (Slack-inspired with pure black accents)
DARK_THEME = {
    "bg_primary": "#1a1d21",  # Dark gray (not pure black)
    "bg_secondary": "#222529",  # Slightly lighter gray
    "text_primary": "#e8e8e8",  # Almost white, very light gray
    "text_secondary": "#9ca3af",  # Medium gray for secondary text
    "accent": "#000000",  # Pure black for section labels
    "accent_light": "#1a1a1a",  # Very dark gray for hover
    "border": "#374151",  # Dark border
    "button_bg": "#2d3139",  # Button background
    "button_hover": "#383c45",  # Button hover
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "scanner.log")

# File size limits (in MB)
MAX_FILE_SIZE_MB = 50
MAX_CONTENT_LENGTH = 500000  # Characters, for webhook safety

# Export Settings
EXPORT_DIR = os.path.join(os.path.dirname(__file__), "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

# Export Preferences (defaults from config, overridden by .env after first use)
DEFAULT_USE_ORIGINAL_LOCATION = (
    os.getenv("EXPORT_USE_ORIGINAL_LOCATION", "true").lower() == "true"
)
DEFAULT_AUTO_EXPORT_TXT = os.getenv("EXPORT_AUTO_TXT", "false").lower() == "true"
DEFAULT_AUTO_EXPORT_DOCX = os.getenv("EXPORT_AUTO_DOCX", "false").lower() == "true"
