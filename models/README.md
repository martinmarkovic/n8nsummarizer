# Models Layer

Data processing, external API communication, and tool integration. Models handle all business logic and data operations without any UI dependencies or tkinter imports.

## Purpose

The models layer is responsible for:
- Data processing and transformation
- External API communication (n8n, translation services)
- Local tool integration (Whisper, yt-dlp, FFmpeg)
- File operations and content management
- Business rules and validation

**Key Principle**: Models never import or reference UI components. They provide pure data processing capabilities.

## Contents

### Core Model Files

| File | Purpose |
|------|---------|
| `base_downloader.py` | Base class for all platform-specific downloaders |
| `video_downloader.py` | Router for platform-specific video downloaders |
| `youtube_downloader.py` | YouTube video downloading using yt-dlp |
| `twitter_downloader.py` | Twitter/X video downloading using yt-dlp |
| `instagram_downloader.py` | Instagram video downloading using yt-dlp |
| `file_model.py` | File reading and content extraction |
| `transcribe_model.py` | Audio/video transcription using Whisper |
| `translation_model.py` | Text translation coordination (facade) |
| `n8n_model.py` | n8n webhook communication |
| `http_client.py` | HTTP client for API communication |

### Subpackages

| Package | Purpose |
|--------|---------|
| `models/n8n/` | n8n webhook communication layer |
| `models/translation/` | Translation services and SRT support |
| `models/transcription/` | Whisper transcription wrapper |

## Architecture

### BaseDownloader Pattern

All platform-specific downloaders extend `BaseDownloader` for shared configuration:

```
BaseDownloader (abstract)
├── YouTubeDownloader (concrete)
├── TwitterDownloader (concrete)
└── InstagramDownloader (concrete)
```

**Shared Configuration**:
- `download_path`: Destination folder
- `selected_resolution`: Quality preset
- `progress_callback`: Download progress updates
- `is_downloading`: Current download state

**Shared Methods**:
- `set_download_path(path)`: Configure download location
- `set_resolution(resolution)`: Set quality preset
- `set_progress_callback(callback)`: Register progress handler
- `cancel_download()`: Abort current download
- `_progress_hook(d)`: Forward progress to callback

### VideoDownloader Router

`VideoDownloader` acts as a router that:
1. Detects source platform from URL
2. Delegates to appropriate platform downloader
3. Provides unified interface to controllers
4. Manages cross-cutting concerns (progress callbacks, settings)

```python
# Usage example
downloader = VideoDownloader()
downloader.set_download_path("/downloads")
downloader.set_resolution("1080p (Full HD)")
success, message = downloader.download_video(url)
```

### Translation Facade Pattern

`TranslationModel` acts as a facade coordinating:
- `TranslationFileHandler`: File operations
- `TranslationService`: API communication
- `TranslationChunker`: Text chunking
- `srt_support`: Subtitle processing

```python
# Usage example
translator = TranslationModel()
translator.set_current_file_path("video.srt")
success, result, error = translator.translate_srt(content, "es")
```

## Key Conventions

1. **No UI Dependencies**: Models never import tkinter or view components
2. **Single Responsibility**: Each model handles one specific domain
3. **Clean Interfaces**: Public methods well-documented with type hints
4. **Error Handling**: Robust error handling with logging
5. **Logging**: Consistent logging for debugging and monitoring

## Subpackage Details

### models/n8n/

Handles n8n webhook communication for summarization workflows.

**See**: [models/n8n/README.md](n8n/README.md)

### models/translation/

Provides translation services with LM Studio/local LLM support and specialized SRT handling.

**See**: [models/translation/README.md](translation/README.md)

### models/transcription/

Whisper transcription wrapper for local audio/video processing.

**See**: [models/transcription/README.md](transcription/README.md)

## Adding New Models

To add a new model:

1. **Define Responsibility**: Clear single purpose
2. **Implement Interface**: Follow existing patterns
3. **Add Documentation**: Update this README
4. **No UI Dependencies**: Keep models UI-free
5. **Test Thoroughly**: Ensure robust error handling

## Testing Models

Models can be tested independently of UI:

```python
# Example test
def test_file_model():
    model = FileModel()
    success, content, error = model.read_file("test.txt")
    assert success
    assert content == "expected content"
```

## Common Patterns

### Progress Callbacks

```python
def progress_callback(progress_dict):
    print(f"Progress: {progress_dict['percent']}%")

downloader.set_progress_callback(progress_callback)
```

### Error Handling

```python
try:
    success, result, error = model.process(data)
    if not success:
        logger.error(f"Operation failed: {error}")
        return False, error
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    return False, "Internal error"
```

### Configuration Management

```python
# Use environment variables with fallbacks
timeout = int(os.getenv("API_TIMEOUT", "30"))
url = os.getenv("API_URL", "http://localhost:5000")
```