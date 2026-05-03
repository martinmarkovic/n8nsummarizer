# Shared Utilities

Stateless utilities used across all layers of the application. These components provide common functionality without business logic or UI dependencies.

## Purpose

The utils layer provides:
- File system operations
- Centralized logging
- Configuration management
- Input validation
- Shared helper functions

**Key Principle**: Utilities are stateless and have no dependencies on other layers.

## Contents

| File | Purpose |
|------|---------|
| `__init__.py` | Package initialization (empty) |
| `file_scanner.py` | File path discovery and counting |
| `logger.py` | Centralized logging configuration |
| `settings_manager.py` | .env file persistence |
| `validators.py` | Input validation functions |

## Important Distinctions

### File Scanner Utilities

**CRITICAL**: There are two different `file_scanner` components:

1. **`utils/file_scanner.py`** (FileScanner)
   - **Purpose**: File path discovery only
   - **Methods**: `scan()`, `count()`, `scan_with_patterns()`
   - **Scope**: Find files matching patterns in directories
   - **Usage**: Bulk operations, file discovery

2. **`models/file_scanner.py`** (FileReader - renamed in Phase 3)
   - **Purpose**: File content reading
   - **Methods**: `read_file()`, `get_file_info()`
   - **Scope**: Read text content from files
   - **Usage**: Individual file processing

**Example Comparison**:

```python
from utils.file_scanner import FileScanner
from models.file_reader import FileReader

# Find files (path discovery)
files = FileScanner.scan("/documents", [".txt", ".srt"])

# Read file content
reader = FileReader()
success, content, error = reader.read_file("document.txt")
```

## Detailed Components

### file_scanner.py

File system discovery utilities:

```python
from utils.file_scanner import FileScanner

# Count files matching extensions
file_count = FileScanner.count("/videos", [".mp4", ".mov"], recursive=True)

# Scan for files
video_files = FileScanner.scan("/videos", [".mp4", ".mkv"])

# Complex pattern matching
files = FileScanner.scan_with_patterns("/data", {
    "videos": ["*.mp4", "*.mov"],
    "subtitles": ["*.srt"]
})
```

**Features**:
- Recursive directory scanning
- Multiple extension support
- Case-insensitive matching
- Efficient path-only operations (no content reading)

### logger.py

Centralized logging configuration:

```python
from utils.logger import logger

# Standard logging
logger.info("Application started")
logger.warning("Disk space low")
logger.error("Failed to process file", exc_info=True)

# Debug logging (only shown in DEBUG mode)
logger.debug("Detailed processing information")
```

**Configuration**:
```env
LOG_LEVEL=INFO  # INFO, DEBUG, WARNING, ERROR
LOG_FILE=logs/scanner.log
```

### settings_manager.py

Persistent user preferences using .env files:

```python
from utils.settings_manager import SettingsManager

# Initialize
settings = SettingsManager()

# Get setting with default
save_path = settings.get("DOWNLOADER_SAVE_PATH", "/downloads")

# Set setting (auto-saves)
settings.set("DOWNLOADER_QUALITY", "1080p (Full HD)")

# Type-safe getters
tab_index = settings.get_int("LAST_ACTIVE_TAB", 0)
```

**Features**:
- Automatic .env file creation
- Comment preservation
- Type conversion helpers
- Thread-safe operations

### validators.py

Input validation functions:

```python
from utils.validators import validate_file, validate_url

# Validate file existence and type
is_valid, error = validate_file("document.txt")

# Validate URL format
is_valid, error = validate_url("https://example.com")
```

**Common Validations**:
- File existence and readability
- URL format validation
- Content non-empty checks
- Extension validation

## Usage Patterns

### File Discovery Workflow

```python
from utils.file_scanner import FileScanner

# Find all media files
scanner = FileScanner()
files = scanner.scan("/media", [".mp4", ".mov", ".avi", ".mkv"])

# Process each file
for file_path in files:
    print(f"Found: {file_path}")
```

### Settings Management

```python
from utils.settings_manager import SettingsManager

# Initialize settings
settings = SettingsManager()

# Load and use settings
last_tab = settings.get_int("LAST_ACTIVE_TAB", 0)
quality = settings.get("DOWNLOADER_QUALITY", "Best Available")

# Update settings
settings.set("DOWNLOADER_SAVE_PATH", "/new/downloads")
settings.set("LAST_ACTIVE_TAB", "2")
```

### Logging Best Practices

```python
import logging
from utils.logger import logger

# Module-level logging
module_logger = logging.getLogger(__name__)

# Application events
logger.info("Processing started")

# Warnings
logger.warning("Approaching storage limit")

# Errors with context
try:
    process_file("data.txt")
except Exception as e:
    logger.error("File processing failed", exc_info=True)

# Debug information (only in DEBUG mode)
logger.debug(f"Detailed processing stats: {stats}")
```

## Adding New Utilities

To add a new utility:

1. **Define Purpose**: Clear single responsibility
2. **Keep Stateless**: No instance variables
3. **Minimal Dependencies**: Only import standard library
4. **Add Documentation**: Update this README
5. **Test Thoroughly**: Verify edge cases

## Testing Utilities

Test utilities independently:

```python
from utils.file_scanner import FileScanner
from utils.validators import validate_file

# Test file scanner
test_files = [
    "test1.txt",
    "test2.srt", 
    "subfolder/test3.mp4"
]
# ... verify scan results

# Test validators
assert validate_file("existing.txt")[0] == True
assert validate_file("missing.txt")[0] == False
```

## Performance Considerations

1. **File Scanner**: Optimized for path-only operations
2. **Settings**: Cached in memory after loading
3. **Logging**: Asynchronous to avoid blocking
4. **Validators**: Early failure for invalid inputs

## Common Pitfalls

1. **Confusing File Scanners**: Remember the difference between path discovery and content reading
2. **Thread Safety**: SettingsManager is thread-safe, but avoid concurrent .env writes
3. **Logging Levels**: DEBUG logs can impact performance in production
4. **File Paths**: Always use Path objects for cross-platform compatibility