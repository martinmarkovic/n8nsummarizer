# n8n Summarizer - Branches Overview

## Current Development Status (2025-12-11)

### Branch Hierarchy

```
v3.1 (Base)
    └── v4.0 (Phase 4.1 UI Only)
            └── v4.1 (Phase 4.1 Complete Implementation)
                    └── v4.2 (Phase 4.2 Advanced Options) ← CURRENT
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
**Status**: UI Complete - Ready for Controller Integration
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

**Next Steps**:
- Update BulkSummarizerController to handle:
  - Multiple file types
  - Output format generation
  - Custom output paths

**Link**: [v4.2 Branch](https://github.com/martinmarkovic/n8nsummarizer/tree/v4.2)

---

## Feature Comparison Matrix

| Feature | v3.1 | v4.0 | v4.1 | v4.2 |
|---------|------|------|------|------|
| File Summarizer | ✅ | ✅ | ✅ | ✅ |
| YouTube Summarizer | ✅ | ✅ | ✅ | ✅ |
| Transcriber | ✅ | ✅ | ✅ | ✅ |
| Bulk Processing | ❌ | UI only | ✅ | ✅ |
| Multiple File Types | ❌ | 2 types | 2 types | 4 types |
| Output Format Options | ❌ | ❌ | Single | Multiple ✅ |
| Custom Output Location | ❌ | ❌ | ❌ | ✅ |
| Preference Persistence | ❌ | ❌ | ❌ | ✅ |
| Combined Output | ❌ | ❌ | ❌ | Planned |

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

---

## Roadmap

### Phase 4.2 ✓ COMPLETE (UI)
- [x] File type checkboxes (txt, srt, docx, pdf)
- [x] Output format options
- [x] Output location selection
- [x] Preference persistence
- [ ] Controller integration
- [ ] Combined file generation
- [ ] PDF text extraction
- [ ] SRT subtitle handling

### Phase 4.3 - Summarization Types (4-5 weeks)
- Simple vs Standard vs Agentic
- Different N8N instructions
- Metadata handling
- Custom prompt templates

### Phase 5.0 - Knowledge Base (6-8 weeks)
- Vector database (Chroma)
- Local LLM (Ollama)
- RAG pipeline
- Agent reasoning

---

## Version History

| Version | Date | Focus |
|---------|------|-------|
| v3.1 | Earlier | Base: File, YouTube, Transcriber |
| v4.0 | 2025-12-10 | Bulk UI Foundation |
| v4.1 | 2025-12-10 | Bulk Processing Complete |
| v4.2 | 2025-12-11 | Advanced Options & Persistence |

---

## Quick Links

- **Repository**: https://github.com/martinmarkovic/n8nsummarizer
- **Latest (v4.2)**: https://github.com/martinmarkovic/n8nsummarizer/tree/v4.2
- **Phase 4.2 Summary**: [PHASE_4.2_SUMMARY.md](./PHASE_4.2_SUMMARY.md)
- **Issues**: https://github.com/martinmarkovic/n8nsummarizer/issues

---

**Last Updated**: 2025-12-11 19:35 UTC
**Current Active Branch**: v4.2
