# Views Layer

UI components built with Tkinter.

## Main Window

`main_window.py` - Application shell with 6 tabs, theme toggle, font size controls.

## Tabs

### Single-File Tabs
1. `file_tab.py` - File Summarizer (load file, send to n8n, display summary)
2. `youtube_summarizer_tab.py` - YouTube Summarization (URL → transcript → summary)
3. `transcriber_tab.py` - Transcriber (audio/video → text formats)

### Bulk Processing Tabs (Modular Packages)
4. `bulk_summarizer/` - Bulk Summarizer (folder of docs → summaries)
   - `tab.py` - Main coordinator (~200 lines)
   - `file_type_selector.py` - File type checkboxes
   - `preferences.py` - .env persistence
   - `ui_components.py` - Layout builder
   - `constants.py` - Configuration

5. `bulk_transcriber/` - Bulk Transcriber (folder of media → transcripts)
   - `tab.py` - Main coordinator (~250 lines)
   - `media_type_selector.py` - Video/audio format checkboxes
   - `output_format_selector.py` - Output format checkboxes
   - `preferences.py` - .env persistence
   - `ui_components.py` - Layout builder
   - `constants.py` - Configuration

6. `translation_tab.py` - Translation (UI placeholder, no backend yet - v6.0)

## Base Class

`base_tab.py` - Shared tab functionality (status updates, logging, common methods).

All tabs inherit from `BaseTab` and implement `_setup_ui()`.

## Modular Design (v5.0.3+)

Bulk tabs refactored into packages with single-responsibility modules:
- **71% code reduction** in main tab files
- **Independently testable** components
- **Reusable** selectors and UI builders
- **Clean separation** of UI, state, and persistence
