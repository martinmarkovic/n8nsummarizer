# n8n Summarizer v6.0

Desktop application for summarizing text files, transcribing media, and bulk processing via n8n webhooks.

## Features

- **File Summarizer** - Load text/srt/docx/pdf files and summarize via n8n
- **YouTube Summarization** - Transcribe and summarize YouTube videos
- **Transcriber** - Convert audio/video to text (11 media formats)
- **Bulk Summarizer** - Process entire folders of documents
- **Bulk Transcriber** - Process entire folders of media files
- **Translation** - UI placeholder for future translation workflows (v6.0)

## Quick Start

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and configure n8n webhook URLs
3. Run: `python main.py` or `runGui.bat`

## Architecture

**MVC Pattern:**
- `views/` - UI tabs (Tkinter)
- `controllers/` - Business logic and event handlers
- `models/` - Data access and n8n integration
- `utils/` - Shared utilities (logger, file scanner)

**Modular Tabs (v5.0.3+):**
- `views/bulk_summarizer/` - Refactored into 6 focused modules
- `views/bulk_transcriber/` - Refactored into 7 focused modules

## Documentation

- `models/README.md` - Model layer details
- `views/README.md` - View layer and tab structure
- `controllers/README.md` - Controller layer and workflows
- Package-level READMEs in `views/bulk_summarizer/` and `views/bulk_transcriber/`

## Version

Current: **v6.0** (February 2026)
