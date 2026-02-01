# Models Layer

Data access and external service integration.

## Core Models

### `file_model.py`
Handles file reading and parsing:
- Text files (`.txt`, `.srt`, `.log`, `.csv`, `.json`, `.xml`)
- DOCX files (Word documents)
- PDF files (text extraction)
- Character encoding detection
- File validation (size limits, format checks)

### `n8n_model.py`
Wrapper for n8n webhook integration (summary, transcription, translation).

### `transcribe_model.py`
Handles media file transcription via n8n webhooks.

## Sub-packages

### `models/n8n/`
N8N webhook clients:
- `summary_client.py` - Text summarization requests
- `transcribe_client.py` - Media transcription requests

### `models/transcription/`
Transcription utilities:
- `format_converter.py` - Convert between SRT, TXT, VTT, JSON formats
- `parser.py` - Parse transcription responses

## Usage

Models are instantiated by controllers and called to retrieve/process data:

```python
from models.file_model import FileModel
from models.n8n_model import N8NModel

file_model = FileModel()
content = file_model.read_file("/path/to/file.txt")

n8n = N8NModel()
response = n8n.send_summarize_request(content)
```

Models have **no UI dependencies** - purely data and business logic.
