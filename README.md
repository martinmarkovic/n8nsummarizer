# Media SwissKnife

Multi-source media processing desktop application built with Python/Tkinter.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp .env.example .env
# Edit .env with your API keys and settings

# Run the application
python main.py  # or runGui.bat on Windows
```

## Features

Media SwissKnife provides comprehensive media processing capabilities:

- **File Summarization**: Summarize text files (txt, srt, docx, pdf)
- **YouTube Processing**: Download and summarize YouTube videos with transcription
- **Single File Transcription**: Transcribe audio/video files (mp4, mp3, wav, m4a, flac, aac, wma, mov, avi, mkv, webm)
- **Bulk Summarization**: Process multiple files with advanced options
- **Bulk Transcription**: Transcribe multiple media files with format selection
- **Translation**: Translate text and subtitles using LM Studio or compatible APIs
- **Video Download**: Download videos from YouTube, Twitter, and Instagram
- **Video Subtitler**: Download, transcribe, translate, and burn subtitles into videos

## Architecture

MVC (Model-View-Controller) architecture:

- **Models**: Data processing, API communication, file operations
- **Views**: Tkinter UI components and tabs
- **Controllers**: Orchestrate workflows between views and models

## Requirements

```
requests>=2.31.0
python-dotenv>=1.0.0
python-docx>=0.8.11
tkinter-tooltip>=2.1.0
yt-dlp>=2024.0.0
srt>=0.0.6
openai-whisper>=2024.0.0
```

## Configuration

| Variable | Purpose | Example |
|----------|---------|---------|
| `LAST_ACTIVE_TAB` | Last active tab index | `0` (File Tab) |
| `DOWNLOADER_SAVE_PATH` | Default download folder | `/path/to/downloads` |
| `DOWNLOADER_QUALITY` | Video download quality | `Best Available`, `1080p (Full HD)` |
| `YOUTUBE_PO_TOKEN` | YouTube PO token for HD | `your_po_token_here` |
| `N8N_WEBHOOK_URL` | n8n webhook endpoint | `http://localhost:5678/webhook` |
| `TRANSLATION_URL` | Translation API endpoint | `http://127.0.0.1:1234/v1/completions` |

## Folder Structure

```
media-swissknife/
├── controllers/       # UI orchestration and workflow coordination
├── models/            # Business logic, data processing, and API communication
├── views/             # Tkinter UI components and tabs
├── utils/             # Shared utilities and helpers
├── tests/             # Test suite
├── docs/              # Documentation and guides
├── main.py            # Application entry point
├── config.py          # Configuration constants
├── requirements.txt   # Python dependencies
└── .env.example       # Environment configuration template
```

## Documentation

See [docs/](docs/) for detailed guides, changelogs, and technical documentation.

## Tabs Overview

| Tab | Controller | Description |
|-----|-----------|-------------|
| File Summarizer | FileController | Summarize individual text files |
| YouTube Summarizer | YouTubeSummarizerController | Download and summarize YouTube videos |
| Transcriber | TranscriberController | Transcribe single audio/video files |
| Bulk Summarizer | BulkSummarizerController | Process multiple files for summarization |
| Bulk Transcriber | BulkTranscriberController | Transcribe multiple media files |
| Translation | TranslationController | Translate text and subtitles |
| Downloader | DownloaderController | Download videos from multiple platforms |
| Video Subtitler | VideoSubtitlerController | Complete subtitle workflow (download → transcribe → translate → burn) |

## Development

### Adding New Features

1. **Models**: Add data processing logic in `models/`
2. **Views**: Create UI components in `views/`
3. **Controllers**: Wire them together in `controllers/`
4. **Integration**: Register in `main.py`

### Testing

```bash
python -m pytest tests/
```

## Support

For issues and feature requests, please open a GitHub issue.

## License

[Specify license information here]

## Contributing

Contributions are welcome! Please follow the existing code style and architecture patterns.