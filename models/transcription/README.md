# Transcription Services

Local Whisper and transcribe-anything CLI wrapper for audio/video transcription.

## Purpose

This subpackage provides:
- Direct Whisper integration for Python transcription
- CLI wrapper for transcribe-anything tool
- Multiple output formats (SRT, TXT, VTT, JSON)
- YouTube-specific download+transcribe workflows
- GPU/CPU automatic detection

## Contents

| File | Purpose |
|------|---------|
| `__init__.py` | Exports public API (TranscribeModel, YouTubeTranscriber) |
| `model.py` | Direct Whisper transcription |
| `cli_runner.py` | CLI tool wrapper |
| `outputs.py` | Format conversion (SRT, TXT, VTT, JSON) |
| `sanitizer.py` | Filename and content sanitization |
| `youtube.py` | YouTube download + transcribe pipeline |

## Architecture

```
transcription/
├── model.py (Whisper direct)
├── cli_runner.py (CLI wrapper)
├── outputs.py (format conversion)
├── sanitizer.py (input cleaning)
└── youtube.py (YouTube integration)
```

## Transcription Paths

### 1. Whisper Direct (model.py)
Used by VideoSubtitlerController:
- Pure Python Whisper integration
- Best for video subtitling
- GPU acceleration when available
- Direct model loading

### 2. CLI via transcribe-anything (cli_runner.py)
Used by TranscriberController, BulkTranscriberController:
- Command-line tool wrapper
- Supports more formats
- Better for bulk processing
- Separate process isolation

## Output Formats

Supported formats via outputs.py:

| Format | Extension | Purpose |
|--------|-----------|---------|
| SRT | .srt | Subtitles with timing |
| TXT | .txt | Plain text transcript |
| VTT | .vtt | WebVTT subtitles |
| JSON | .json | Structured transcription data |

## YouTube Integration

Specialized YouTube workflow (youtube.py):

1. **Download**: Use yt-dlp to get video
2. **Transcribe**: Process with Whisper
3. **Format**: Convert to desired output
4. **Cleanup**: Remove temporary files

## GPU/CPU Considerations

- **GPU Preferred**: Whisper uses CUDA when available
- **Fallback**: Automatically uses CPU if no GPU
- **Memory**: Large files may require chunking
- **Performance**: GPU significantly faster for video

## Configuration

Transcription settings via environment variables:

```env
# Whisper Configuration
WHISPER_MODEL=base  # or tiny, small, medium, large
WHISPER_DEVICE=cuda  # or cpu
WHISPER_LANGUAGE=auto  # or specific language code
```

## Usage Examples

### Direct Whisper

```python
from models.transcription.model import TranscribeModel

model = TranscribeModel()
result = model.transcribe_file("video.mp4", device="cuda")
print(result.srt_content)  # Subtitle content
```

### CLI Wrapper

```python
from models.transcription.cli_runner import CLITranscriber

transcriber = CLITranscriber()
result = transcriber.transcribe("audio.mp3", format="srt")
result.save("output.srt")
```

### YouTube Pipeline

```python
from models.transcription.youtube import YouTubeTranscriber

transcriber = YouTubeTranscriber()
srt_content = transcriber.download_and_transcribe(
    "https://youtube.com/watch?v=...",
    quality="1080p"
)
```

## Integration

Used by multiple controllers:
- VideoSubtitlerController (Whisper direct)
- TranscriberController (CLI wrapper)
- BulkTranscriberController (CLI wrapper)

## Extending

To add new transcription features:

1. **Add Format**: Extend outputs.py
2. **Enhance Model**: Update model.py
3. **Support Tool**: Add to cli_runner.py
4. **Test**: Verify with sample media

## Testing

Test with sample media files:

```python
from models.transcription.model import TranscribeModel

# Test with short audio file
model = TranscribeModel()
result = model.transcribe_file("test.wav", device="cpu")

assert result.success
assert len(result.srt_content) > 0
```

## Performance Tips

1. **GPU Acceleration**: Use CUDA for video files
2. **Batch Processing**: Use CLI for bulk operations
3. **Format Selection**: Choose appropriate output format
4. **Memory Management**: Process large files in chunks
5. **Error Handling**: Validate inputs before processing