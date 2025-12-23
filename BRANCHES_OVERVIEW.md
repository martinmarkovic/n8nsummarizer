# n8n Summarizer - Branches Overview

## Current Development Status (2025-12-23)

### Branch Hierarchy

```
v3.1 (Base)
    └── v4.0 (Phase 4.1 UI Only)
            └── v4.1 (Phase 4.1 Complete Implementation)
                    └── v4.2 (Phase 4.2 Advanced Options)
                            └── v4.3 (Phase 4.3 Enhanced UX) ← CURRENT
```

---

## Branch Details

### 💾 v3.1 - Base Version
**Status**: Stable ✓
**Features**:
- File Summarizer (single file)
- YouTube Summarizer with transcription
- Transcriber
- N8N webhook integration

**Link**: [v3.1 Branch](https://github.com/martinmarkovic/n8nsummarizer/tree/v3.1)

---

### 📦 v4.0 - Bulk Summarizer UI Only
**Status**: Functional UI (No processing)
**Created**: 2025-12-10
**Purpose**: Phase 4.1 UI Foundation

**New in v4.0**:
- BulkSummarizerTab with basic UI
- Folder selection
- File type radio buttons (txt, docx, both)
- Progress tracking UI
- Status log

**What's Missing**:
- No controller (processing logic)
- No file operations
- Only UI placeholder

**Commits**: 3
- Add BulkSummarizerTab UI
- Update main_window.py
- Update main.py (partial)

**Link**: [v4.0 Branch](https://github.com/martinmarkovic/n8nsummarizer/tree/v4.0)

---

### 📎 v4.1 - Phase 4.1 Complete
**Status**: Fully Functional ✓
**Created**: 2025-12-10
**Purpose**: Complete bulk file processing

**New in v4.1** (on top of v4.0):
- BulkSummarizerController with full processing logic
- File discovery (txt, docx)
- Background threading
- Sequential file processing
- N8N integration for summarization
- Real-time progress tracking
- Error handling and recovery
- Output folder management
- Completion statistics

**Key Methods**:
- `handle_start_processing()` - Validation and launch
- `_process_folder_background()` - Background worker
- `_read_file()` - File reading (.txt, .docx)
- `_save_summary()` - Summary output

**Commits**: 3
- Add BulkSummarizerController (full implementation)
- Update main.py to v4.1
- Update main_window.py to v4.1

**Link**: [v4.1 Branch](https://github.com/martinmarkovic/n8nsummarizer/tree/v4.1)

---

### 🌟 v4.2 - Phase 4.2 Advanced Options
**Status**: UI Complete - Ready for Controller Integration ✓
**Created**: 2025-12-11
**Purpose**: Advanced configuration and output options

**New in v4.2** (on top of v4.1):

#### UI Enhancements
- **File Type Selection**
  - Changed from radio buttons to checkboxes
  - Now supports: txt, srt, docx, pdf
  - Multiple types can be selected
  - At least one required

- **Output Format Options**
  - "Separate Files" (individual summaries)
  - "Combined File" (merged output)
  - Both can be selected simultaneously
  - At least one required

- **Output Location Selection**
  - "Default" (parent folder of source)
  - "Custom" (user-selected location)
  - Browse button for custom selection

#### Preference Persistence
- Save to `.env` file
- Auto-load on startup
- Preferences saved:
  - `BULK_FILE_TYPES` (comma-separated)
  - `BULK_OUTPUT_SEPARATE` (boolean)
  - `BULK_OUTPUT_COMBINED` (boolean)

**Files Modified**:
- `views/bulk_summarizer_tab.py` (complete redesign, ~550 lines)
- `main.py` (version update)
- `views/main_window.py` (version update, style additions)

**New Features**:
- `_load_preferences()` - Load from .env
- `_save_preferences()` - Save to .env
- `get_file_types()` - Return list of selected types
- `get_output_formats()` - Return format options dict
- `get_output_folder()` - Handle default/custom locations

**Commits**: 4
- Phase 4.2: Complete UI redesign with advanced options
- Phase 4.2: Update main.py for v4.2
- Phase 4.2: Update main_window.py for v4.2
- Add Phase 4.2 implementation summary

**Link**: [v4.2 Branch](https://github.com/martinmarkovic/n8nsummarizer/tree/v4.2)

---

### ✨ v4.3 - Phase 4.3 Enhanced UX & Preferences
**Status**: Production Ready ✓
**Created**: 2025-12-23
**Purpose**: Improved UX and preference persistence

**New in v4.3** (on top of v4.2):

#### 1. Smart Output Folder Naming
- Output folders now use original folder name + "- Summarized"
- Much clearer which output corresponds to which input
- **Before**: `/data/Reports/` → `/data/Summaries/` ❌ (unclear)
- **After**: `/data/Reports/` → `/data/Reports - Summarized/` ✅ (clear!)

**Benefits**:
- Context-aware naming
- Easier organization of multiple bulk operations
- More professional output structure
- Works with multiple input folders without confusion

**Implementation**:
- Updated `_create_output_folder()` in BulkSummarizerController
- Detects original folder name
- Appends " - Summarized" suffix
- Custom locations still respected

#### 2. Font Size Preference Persistence
- Font size adjustments now saved to .env
- Remembered across app sessions
- No need to readjust on every launch

**Implementation**:
- New method `_load_font_size_from_env()` - Loads on startup
- New method `_save_font_size_to_env()` - Saves after adjustment
- Updated `__init__()` to load from .env
- Updated `_increase_font_size()` and `_decrease_font_size()` to save
- .env variable: `APP_FONT_SIZE` (valid: [8, 10, 12, 14, 16, 18, 20])

**Benefits**:
- Better accessibility (users can set preferred size once)
- Improved usability (no repeated adjustments)
- Scope: All text widgets (File Summarizer, YouTube, Transcriber, Bulk)

**Files Modified**:
- `controllers/bulk_summarizer_controller.py` - Output naming
- `views/main_window.py` - Font persistence

**New Files**:
- `PHASE_4.3_SUMMARY.md` - Comprehensive documentation
- `V4.3_CHANGELOG.md` - Quick reference guide

**Commits**: 4
- Fix v4.3: Output folder naming uses original folder name + "- Summarized"
- Implement v4.3: Save and load font size preference from .env
- Add v4.3 phase summary with improvements documentation
- Add v4.3 changelog with quick reference

**Backward Compatibility**: 
- ✅ Fully backward compatible
- ✅ No breaking changes
- ✅ No data migration required
- ✅ Existing .env settings preserved

**Link**: [v4.3 Branch](https://github.com/martinmarkovic/n8nsummarizer/tree/v4.3)

---

## Feature Comparison Matrix

| Feature | v3.1 | v4.0 | v4.1 | v4.2 | v4.3 |
|---------|------|------|------|------|------|
| File Summarizer | ✅ | ✅ | ✅ | ✅ | ✅ |
| YouTube Summarizer | ✅ | ✅ | ✅ | ✅ | ✅ |
| Transcriber | ✅ | ✅ | ✅ | ✅ | ✅ |
| Bulk Processing | ❌ | UI only | ✅ | ✅ | ✅ |
| Multiple File Types | ❌ | 2 types | 2 types | 4 types | 4 types |
| Output Format Options | ❌ | ❌ | Single | Multiple ✅ | Multiple ✅ |
| Custom Output Location | ❌ | ❌ | ❌ | ✅ | ✅ |
| Preference Persistence | ❌ | ❌ | ❌ | ✅ | ✅ |
| Combined Output | ❌ | ❌ | ❌ | Planned | Planned |
| Smart Output Naming | ❌ | ❌ | ❌ | ❌ | ✅ |
| Font Size Persistence | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Testing Instructions

### Test v4.0
```bash
git checkout v4.0
python main.py
# UI should appear, no processing functionality
```

### Test v4.1
```bash
git checkout v4.1
python main.py
# Full bulk processing should work
# Create test folder with .txt and .docx files
# Select folder, start processing
```

### Test v4.2
```bash
git checkout v4.2
python main.py
# New advanced options should appear
# Verify file type checkboxes
# Verify output format options
# Verify location selection
# Check .env file for saved preferences
```

### Test v4.3
```bash
git checkout v4.3
python main.py

# Test 1: Output Folder Naming
# Create folder: /test/data/MyDocuments/
# Add some .txt files
# Run bulk summarizer
# Verify output: /test/data/MyDocuments - Summarized/ ✓

# Test 2: Font Size Persistence
# Click font size + button (increase)
# Verify APP_FONT_SIZE in .env is updated
# Restart application
# Verify font size is preserved ✓
# Font size + and - buttons save preference ✓
```

---

## Roadmap

### Phase 4.3 ✓ COMPLETE
- [x] Smart output folder naming
- [x] Font size preference persistence
- [x] Comprehensive documentation
- [x] Backward compatibility

### Phase 4.4 - Output Format Implementation (4-5 weeks)
- [ ] Combined file generation (single output with all summaries)
- [ ] Separate file output (individual summary files)
- [ ] SRT subtitle handling
- [ ] PDF text extraction
- [ ] Format validation

### Phase 5.0 - Summarization Types (6-8 weeks)
- Simple vs Standard vs Agentic
- Different N8N instructions
- Metadata handling
- Custom prompt templates

### Phase 6.0 - Knowledge Base (8-10 weeks)
- Vector database (Chroma)
- Local LLM (Ollama)
- RAG pipeline
- Agent reasoning

---

## Version History

| Version | Date | Focus | Status |
|---------|------|-------|--------|
| v3.1 | Earlier | Base: File, YouTube, Transcriber | Stable ✓ |
| v4.0 | 2025-12-10 | Bulk UI Foundation | Complete |
| v4.1 | 2025-12-10 | Bulk Processing Complete | Functional ✓ |
| v4.2 | 2025-12-11 | Advanced Options & Persistence | Ready ✓ |
| v4.3 | 2025-12-23 | Enhanced UX & Font Persistence | **Production ✓** |

---

## Key Improvements Summary

### v4.0 → v4.1
✅ Added complete bulk processing functionality
✅ Implemented background threading
✅ Integrated N8N summarization

### v4.1 → v4.2
✅ Added advanced file type selection (4 types)
✅ Added output format options (separate/combined)
✅ Added preference persistence to .env

### v4.2 → v4.3
✅ Fixed output folder naming (context-aware)
✅ Implemented font size persistence
✅ Improved UX for multiple bulk operations
✅ Enhanced accessibility with persistent font size

---

## Quick Links

- **Repository**: https://github.com/martinmarkovic/n8nsummarizer
- **Latest (v4.3)**: https://github.com/martinmarkovic/n8nsummarizer/tree/v4.3
- **Phase 4.3 Summary**: [PHASE_4.3_SUMMARY.md](./PHASE_4.3_SUMMARY.md)
- **v4.3 Changelog**: [V4.3_CHANGELOG.md](./V4.3_CHANGELOG.md)
- **Issues**: https://github.com/martinmarkovic/n8nsummarizer/issues

---

**Last Updated**: 2025-12-23 19:25 UTC  
**Current Active Branch**: v4.3  
**Status**: Production Ready ✅
