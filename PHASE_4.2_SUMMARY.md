# Phase 4.2 - Advanced Bulk Options

## Overview
Phase 4.2 introduces advanced configuration options for the Bulk Summarizer feature, including:
- Multiple file type selection (with checkboxes)
- Output format options (separate or combined files)
- Custom output location selection
- Preference persistence in .env

## New Features

### 1. **File Type Selection (Checkboxes)**
- **Replaced**: "Both TXT and DOCX" radio button option
- **New**: 4 independent checkboxes for file types
  - TXT files
  - SRT files (subtitles)
  - DOCX files
  - PDF files
- **Behavior**: Multiple types can be selected simultaneously
- **Default**: TXT is checked by default
- **Validation**: At least one file type must be selected

### 2. **Output Format Options**
- **Separate Files** (Uncombined) - Creates individual summary file for each source file
- **Combined File** - Merges all summaries into a single output file
- **Behavior**: Both options can be selected to generate both formats
- **Default**: "Separate Files" is checked by default

### 3. **Output Location Selection**
- **Default Location**: Saves to parent folder of source folder (keeps existing behavior)
- **Custom Location**: User can browse and select any custom output directory
- **Behavior**: Radio buttons for location mode selection
- **Auto-set**: When folder is selected, output location auto-updates to parent folder name

### 4. **Preference Persistence**
- **Storage**: Preferences saved to `.env` file
- **Saved Preferences**:
  - `BULK_FILE_TYPES` - Comma-separated list (e.g., `txt,docx,pdf`)
  - `BULK_OUTPUT_SEPARATE` - Boolean (True/False)
  - `BULK_OUTPUT_COMBINED` - Boolean (True/False)
- **Load on Startup**: Previous selections automatically restored
- **Save on Change**: Preferences updated whenever file type selection changes

## UI Layout (v4.2)

```
┌─────────────────────────────────────────────┐
│ Select Source Folder                         │
│ [Browse...] [Folder Name]                    │
├─────────────────────────────────────────────┤
│ File Types to Scan                           │
│ ☐ TXT                                        │
│ ☐ SRT (Subtitles)                            │
│ ☐ DOCX                                       │
│ ☐ PDF                                        │
├─────────────────────────────────────────────┤
│ Output Format Options                        │
│ ☐ Separate Files (Uncombined)                │
│ ☐ Combined File (Single output)              │
│ Note: At least one output format must be...  │
├─────────────────────────────────────────────┤
│ Output Location                              │
│ ◉ Default (Parent folder of source)          │
│ ○ Custom Location:  [Browse...]              │
│   [Current Selection]                        │
├─────────────────────────────────────────────┤
│ Processing                                   │
│ Ready                                        │
│ [Start Processing]  [Cancel]                 │
├─────────────────────────────────────────────┤
│ Progress                                     │
│ Processing: file.txt                         │
│ [████████░░░░░░░░░░░░░░░░░░░]               │
│ 5 / 10 files                                 │
├─────────────────────────────────────────────┤
│ Status Log                                   │
│ [14:23:15] • Folder selected: documents...  │
│ [14:23:20] • File types updated: 15 files   │
│ [14:23:25] ✓ Processing complete            │
└─────────────────────────────────────────────┘
```

## Implementation Details

### Files Modified
1. **views/bulk_summarizer_tab.py** (COMPLETE REDESIGN)
   - 370 lines → ~550 lines with new options
   - Changed from radio buttons to checkboxes for file types
   - Added output format selection
   - Added output location selection with radio buttons
   - Implemented preference load/save methods
   - Updated method signatures:
     - `get_file_types()` → returns list of selected types
     - `get_output_formats()` → returns dict with separate/combined flags
     - `get_output_folder()` → handles default/custom location

2. **main.py**
   - Updated version to v4.2
   - Updated docstring with new features
   - Added logging for preference persistence

3. **views/main_window.py**
   - Updated version to v4.2
   - Added TRadiobutton style configuration
   - Updated docstring
   - Updated logging

### New Methods (bulk_summarizer_tab.py)

**Preference Management:**
```python
def _load_preferences(self)
    """Load saved preferences from .env file"""

def _save_preferences(self)
    """Save preferences to .env file"""
```

**Output Methods:**
```python
def get_output_folder(self) -> str
    """Get output folder path (default or custom)"""

def get_output_formats(self) -> dict
    """Get output format options {separate, combined}"""
```

**File Type Handling:**
```python
def get_file_types(self) -> list
    """Get selected file types as list"""

def _count_matching_files(self, folder: str) -> int
    """Count files matching ALL selected types"""
```

## Controller Integration (Planned for next update)

The `BulkSummarizerController` will need to be updated to:

1. **File Discovery**
   - Use `get_file_types()` to determine file patterns
   - Search for multiple file extensions
   - Example: `*.txt`, `*.srt`, `*.docx`, `*.pdf`

2. **Output Generation**
   - Check `get_output_formats()` dict
   - Generate separate files if `separate: True`
   - Generate combined file if `combined: True`
   - Handle both formats simultaneously

3. **Output Location**
   - Use `get_output_folder()` for file writing
   - Create directories as needed
   - Handle custom path scenarios

4. **Preference Persistence**
   - No action needed - handled by tab's load/save methods
   - Controller receives already-loaded preferences

## .env File Format

```
BULK_FILE_TYPES=txt,srt,docx,pdf
BULK_OUTPUT_SEPARATE=True
BULK_OUTPUT_COMBINED=False
```

## Testing Checklist

- [x] UI renders correctly with new sections
- [ ] File type checkboxes work independently
- [ ] At least one file type required (validation)
- [ ] Output format checkboxes work independently
- [ ] Default location works correctly
- [ ] Custom location browse and selection works
- [ ] Preferences save to .env on startup
- [ ] Preferences load from .env on next startup
- [ ] File counting works with multiple types
- [ ] UI responds with correct data to controller

## Next Steps (Phase 4.3)

**Summarization Type Selection:**
- Simple vs Standard vs Agentic summarization
- Different N8N instructions per type
- Metadata handling
- Estimated timeline: 4-5 weeks

## Git Information

**Branch**: v4.2
**Created from**: v4.1
**Commits**:
1. Phase 4.2: Complete UI redesign with advanced options
2. Phase 4.2: Update main.py for v4.2
3. Phase 4.2: Update main_window.py for v4.2

**Links**:
- [v4.2 Branch](https://github.com/martinmarkovic/n8nsummarizer/tree/v4.2)
- [v4.1 Branch](https://github.com/martinmarkovic/n8nsummarizer/tree/v4.1)
- [v4.0 Branch](https://github.com/martinmarkovic/n8nsummarizer/tree/v4.0)

---

**Implementation Date**: 2025-12-11
**Status**: ✅ UI COMPLETE - Awaiting controller integration
