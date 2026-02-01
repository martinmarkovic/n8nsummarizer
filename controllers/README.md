# Controllers Layer

Business logic and coordination between views and models.

## Controllers

### `file_controller.py`
Coordinates File Summarizer tab:
- Handles file selection and loading
- Sends content to n8n for summarization
- Manages export (TXT, DOCX)
- Preference persistence

### `youtube_summarizer_controller.py`
Coordinates YouTube Summarization:
- Extracts video metadata
- Sends to n8n for transcription
- Summarizes transcript
- Export options

### `transcriber_controller.py`
Coordinates Transcriber tab:
- Handles media file selection
- Sends to n8n for transcription
- Format conversion (SRT, TXT, VTT, JSON)
- Export management

### `bulk_summarizer_controller.py`
Coordinates Bulk Summarizer:
- Scans folders for matching file types
- Processes files in batches
- Progress tracking and logging
- Output location management

### `bulk_transcriber_controller.py`
Coordinates Bulk Transcriber:
- Scans folders for media files
- Processes media in batches
- Multiple output format generation
- Progress tracking and logging

## Pattern

All controllers follow:
1. Receive view reference in `__init__`
2. Bind UI event handlers to controller methods
3. Call models for data/processing
4. Update view with results
5. Handle errors and logging

## Usage

Controllers are instantiated in `main.py` and passed their respective tab views:

```python
from controllers.file_controller import FileController

file_controller = FileController(window.file_tab)
```

Controllers orchestrate workflows but **never directly manipulate UI** - they call view methods.
