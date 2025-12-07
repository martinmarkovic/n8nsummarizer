# v3.0 Roadmap - YouTube Summarization Tab

**Status:** PLANNING  
**Version:** 3.0.0  
**Created:** 2025-12-07  
**Target:** Production Ready  

---

## 📋 Overview

v3.0 introduces a new **YouTube Summarization** tab that:
1. Transcribes YouTube URLs directly
2. Sends transcript to n8n for summarization
3. Displays summarized content in the tab
4. Exports results in multiple formats

---

## 🎯 Tab Structure (v3.0)

### Current v2.5 Structure:
```
Tabs:
├─ 📄 Tab 1: File Summarizer
└─ 🎬 Tab 2: Transcriber
```

### New v3.0 Structure:
```
Tabs:
├─ 📄 Tab 1: File Summarizer
├─ 🎬 Tab 2: YouTube Summarization  (NEW)
└─ 📹 Tab 3: Transcriber (moved from position 2)
```

---

## 🏗️ YouTube Summarization Tab (Tab 2) - Specifications

### **Input Section:**
- YouTube URL input field
- Dropdown: Select output format for transcription
  - `.txt` (default)
  - `.srt`
  - `.vtt`
  - `.json`
- Transcribe button
- Status indicator (loading spinner)

### **Processing Flow:**
```
1. User enters YouTube URL
2. Click "Transcribe" button
3. TranscriberController calls TranscribeModel.transcribe_youtube()
4. Transcription output → .txt file saved to "Transcriber output section" folder
5. Read .txt file content
6. N8NModel sends content to n8n webhook for summarization
7. Wait for n8n response
8. Display summary in "Output" section
9. Summary processing complete
```

### **Output Section:**
- Large text area showing summarized content
- Three action buttons below:
  1. **Export .txt** - Save summary as .txt file
  2. **Export .srt** - Format and save as .srt file (useful for captions)
  3. **Copy to Clipboard** - Copy summary text to clipboard
- Status messages

### **File Handling:**
- Transcription: Save to standard "Transcriber output section" folder
- Summary exports: Save to standard export folder (from config)

---

## 📂 Implementation Tasks

### **1. Create YouTubeSummarizer Tab (View)**
**File:** `views/youtube_summarizer_tab.py`

**Components:**
- Inherit from `BaseTab`
- **Input Frame:**
  - YouTube URL entry widget
  - Format selection dropdown (ComboBox)
  - Transcribe button
  - Loading indicator
- **Output Frame:**
  - Summary text display (Text widget)
  - Three action buttons: Export .txt, Export .srt, Copy Clipboard
  - Status label

**Callbacks to implement:**
- `on_transcribe_clicked` - Event when user clicks Transcribe
- `on_export_txt_clicked` - Export summary as .txt
- `on_export_srt_clicked` - Export summary as .srt
- `on_copy_clicked` - Copy to clipboard

### **2. Create YouTubeSummarizerController (Controller)**
**File:** `controllers/youtube_summarizer_controller.py`

**Responsibilities:**
- Wire YouTubeSummarizerTab UI events
- Orchestrate TranscribeModel for YouTube transcription
- Save transcript to disk
- Call N8NModel for summarization
- Handle export operations
- Manage threading for async operations
- Error handling and user feedback

**Key Methods:**
- `handle_transcribe_clicked()` - Validate URL, call TranscribeModel
- `_transcribe_youtube_thread()` - Background transcription
- `_send_to_n8n_thread()` - Background summarization
- `handle_export_txt()` - Export summary as .txt
- `handle_export_srt()` - Format summary as .srt and export
- `handle_copy_clipboard()` - Copy summary text

### **3. Update main_window.py**
**Changes:**
- Add YouTubeSummarizerTab to notebook
- Position: Tab index 1 (between File Summarizer and Transcriber)
- Update theme application for new tab

**Code:**
```python
# After FileTab:
self.youtube_summarizer_tab = YouTubeSummarizerTab(self.notebook)
self.notebook.add(self.youtube_summarizer_tab, text="🎬 YouTube Summarization")

# Transcriber becomes Tab 3:
self.transcriber_tab = TranscriberTab(self.notebook)
self.notebook.add(self.transcriber_tab, text="📹 Transcriber")
```

### **4. Update main.py**
**Changes:**
- Initialize YouTubeSummarizerController
- Wire to YouTubeSummarizerTab

**Code:**
```python
# After file_controller:
youtube_summarizer_controller = YouTubeSummarizerController(window.youtube_summarizer_tab)
logger.info("YouTubeSummarizerController initialized")

# Then transcriber_controller:
transcriber_controller = TranscriberController(window.transcriber_tab)
```

### **5. Enhance N8NModel (if needed)**
**File:** `models/n8n_model.py`

**Check:**
- Does N8NModel.send_content() work with transcript text? ✓ (Yes, generic)
- Does extract_summary() handle YouTube summarization? ✓ (Yes, generic)
- Any YouTube-specific requirements? → Define in planning

### **6. Enhance TranscribeModel (if needed)**
**File:** `models/transcribe_model.py`

**Already has:**
- ✅ `transcribe_youtube()` method
- ✅ YouTube title extraction
- ✅ Smart format loading
- ✅ File management

**Verify:**
- Works with user-selected format? ✅ Yes (keep_formats parameter)
- Returns transcript content? ✅ Yes (srt_content in return tuple)

---

## 🔄 Data Flow (v3.0)

```
YouTubeSummarizerTab (View)
         ↓
   User enters URL
         ↓
YouTubeSummarizerController (Controller)
         ↓
   on_transcribe_clicked()
         ↓ (async thread)
   TranscribeModel.transcribe_youtube()
         ↓
   ✅ Transcript saved to disk (.txt format)
   ✅ Transcript content returned
         ↓
   N8NModel.send_content(transcript_text)
         ↓ (async thread)
   Send to n8n webhook
         ↓
   n8n processes → Returns summary
         ↓
   Display summary in tab
         ↓
   User clicks export/copy buttons
         ↓
   Save or clipboard
```

---

## 📦 File Structure After v3.0

```
views/
├── base_tab.py
├── main_window.py              (UPDATED: Add YouTubeSummarizerTab)
├── file_tab.py
├── youtube_summarizer_tab.py   (NEW)
└── transcriber_tab.py

controllers/
├── file_controller.py
├── youtube_summarizer_controller.py  (NEW)
└── transcriber_controller.py

models/
├── file_model.py
├── transcribe_model.py         (Already supports YouTube)
└── n8n_model.py                (Already generic)

main.py                         (UPDATED: Initialize YouTubeSummarizerController)
main_window.py                  (UPDATED: Add tab to notebook)
```

---

## 🎨 UI/UX Considerations

### **Input Section:**
- Clear placeholder text: "Enter YouTube URL (youtube.com or youtu.be/...)"
- Format dropdown with sensible default (.txt)
- Disable format selection during transcription
- Show loading spinner while transcribing

### **Output Section:**
- Display "Ready" when empty
- Show "Transcribing..." status during transcription
- Show "Summarizing..." status while waiting for n8n
- Display summary with proper text wrapping
- Buttons should be disabled until summary is available

### **Tab Position:**
- Position 1 (0-indexed): File Summarizer (unchanged)
- Position 2 (1-indexed): YouTube Summarization (NEW)
- Position 3 (2-indexed): Transcriber (moved from position 1)

---

## 🧪 Testing Checklist (v3.0)

- [ ] Tab appears in correct position (between File and Transcriber)
- [ ] YouTube URL validation works
- [ ] Transcription completes and saves .txt file
- [ ] Transcript displayed in output area
- [ ] n8n webhook called with transcript text
- [ ] Summary displayed correctly
- [ ] Export .txt creates proper file
- [ ] Export .srt creates proper caption file
- [ ] Copy to clipboard works
- [ ] Error handling for invalid URLs
- [ ] Error handling for network issues
- [ ] Loading indicators show/hide correctly
- [ ] Buttons disable during processing
- [ ] Theme switching applies to new tab

---

## 📝 Implementation Order

1. **Create YouTubeSummarizerTab** (View)
2. **Create YouTubeSummarizerController** (Controller)
3. **Update main_window.py** (Add tab to notebook)
4. **Update main.py** (Initialize controller)
5. **Test all functionality**
6. **Test theme switching**
7. **Merge to v3.0 branch**

---

## 🚀 Version Bumps

**Files to update version number to 3.0:**
- `main_window.py` - Title bar
- `main.py` - Startup log
- All docstrings in new files

---

## 📌 Notes

- Transcriber tab functionality remains UNCHANGED (just repositioned)
- All v2.5 features continue to work
- YouTube summarization is ADDITIVE (no breaking changes)
- Can be merged to main as v3.0 release

---

## 🎯 Success Criteria

✅ v3.0 is complete when:
- YouTube Summarization tab works end-to-end
- Tab positioning is correct (File → YouTube Summary → Transcriber)
- All export options work (.txt, .srt, clipboard)
- Error handling is robust
- UI is clean and matches v2.5 design
- All tests pass
- Ready for production deployment
