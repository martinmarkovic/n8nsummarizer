# Translation Services

LM Studio / local LLM translation backend with specialized SRT subtitle support.

## Purpose

This subpackage provides:
- Translation API communication (LM Studio, OpenAI-compatible)
- Text chunking for large documents
- Specialized SRT subtitle translation
- Subtitle structure preservation
- Error handling and recovery

## Contents

| File | Purpose |
|------|---------|
| `__init__.py` | Exports public API (TranslationService, TranslationChunker) |
| `service.py` | API communication with retry logic |
| `chunking.py` | Text splitting for translation |
| `srt_support.py` | Subtitle parsing and reconstruction |

## Architecture

```
translation/
├── service.py (API communication)
├── chunking.py (text splitting)
└── srt_support.py (subtitle handling)
```

## Usage Example

```python
from models.translation import TranslationService, TranslationChunker

# Initialize service
service = TranslationService()

# Translate text
success, translated, error = service.translate_text(
    "Hello world", 
    "es"  # Spanish
)

if success:
    print(translated)  # "Hola mundo"
```

## SRT Translation Pipeline

Specialized workflow for subtitle translation:

1. **Parse SRT**: Extract subtitles with timing
2. **Batch Subtitles**: Group into translation batches
3. **Encode Batch**: Add position markers (<T1>, <T2>, etc.)
4. **Translate Batch**: Send to translation API
5. **Decode Response**: Extract translations by position
6. **Validate**: Ensure all subtitles translated
7. **Reconstruct**: Rebuild SRT with translations
8. **Validate Structure**: Verify SRT format

**Why Special Handling?**
- Subtitle indices must be preserved
- Timing information must be maintained
- Structure must remain valid SRT format
- Partial failures need recovery

## Chunking Strategies

### Plain Text
- Split by character count
- Simple sequential processing
- Recombine results in order

### SRT Files
- Preserve subtitle boundaries
- Add position markers
- Validate index preservation
- Handle partial failures

## Error Recovery

Comprehensive error handling for SRT translation:

1. **Batch Validation**: Check decoded response structure
2. **Truncation Detection**: Identify LM Studio truncation patterns
3. **Automatic Retry**: Recover missing translations
4. **Fallback Strategies**: Smaller batches for problematic content
5. **Partial Success**: Return available translations with placeholders

## Configuration

```env
# Translation Configuration
TRANSLATION_URL=http://127.0.0.1:1234/v1/completions
TRANSLATION_TIMEOUT=300
TRANSLATION_MAX_TOKENS=70000
TRANSLATION_CHUNK_SIZE=4500
TRANSLATION_BATCH_MAX_ITEMS=5
TRANSLATION_BATCH_MAX_CHARS=800
```

## Integration

Used by TranslationModel as the translation backend:

```python
from models.translation import TranslationService

class TranslationModel:
    def __init__(self):
        self.service = TranslationService()
    
    def translate(self, text, target_lang):
        return self.service.translate(text, target_lang)
```

## Extending

To add new translation features:

1. **Add API Method**: Extend service.py
2. **Update Chunker**: Handle new content types
3. **Enhance SRT Support**: Add new subtitle formats
4. **Test**: Verify with translation API

## Testing

Test with mock translation API:

```python
from unittest.mock import Mock
from models.translation.service import TranslationService

# Mock API response
mock_response = Mock(status_code=200)
mock_response.json.return_value = {"choices": [{"text": "translated"}]}

# Test service
service = TranslationService()
# ... test translation methods
```