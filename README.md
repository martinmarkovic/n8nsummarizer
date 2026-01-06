# Text File Scanner - Extended v1.5

Python GUI application for sending file content to n8n webhooks and receiving summarization responses, with **dark/light mode toggle**, **export functionality**, and **smart auto-export with persistent preferences**.

## ✨ New in v1.5

### 🖤 Pure Black Accents in Dark Mode
- **Pure black section labels** (#000000) in dark mode
- Better contrast and visual clarity
- Sharper, more professional appearance

### 🎯 Smart Export Filenames
- **Intelligent naming**: Exports now use `[OriginalFileName]_Summary.txt/.docx`
- **No more generic timestamps**: Get meaningful filenames automatically
- **Example**: `meeting_notes.txt` → exports as `meeting_notes_Summary.txt` and `meeting_notes_Summary.docx`

### ⚙️ Separate Auto-Export Controls
- **Two independent checkboxes**:
  - ☐ Auto-export as .txt after summarization
  - ☐ Auto-export as .docx after summarization
- **Mix and match**: Export only .txt, only .docx, or both
- **Default**: Both unchecked (manual export only)

### 💾 Persistent Export Preferences
- **Remember your choices**: Settings saved to `.env` after first "Send to n8n"
- **Defaults from config**: Initial values from `config.py`
- **Auto-persistence**: No need to manually save preferences
- **Settings remembered**:
  - ✅ Use original file location (default: checked)
  - ☐ Auto-export .txt (default: unchecked)
  - ☐ Auto-export .docx (default: unchecked)

## Features

### Core Functionality
- 📁 **File Selection** - Browse and load text files (.txt, .log, .csv, .json, .xml, .srt, .docx)
- 🔗 **n8n Webhook Integration** - Send content to configured n8n webhook
- ⏱️ **Real-time Response** - Receive and display summarization from n8n
- 🧵 **Non-blocking UI** - Background threading prevents GUI freezes
- ⚙️ **Webhook Override** - Customize webhook URL directly in GUI
- 💾 **Persistent Settings** - Save webhook, theme, and export preferences to `.env`

### Export Features
- 💾 **Smart Filenames** - `[OriginalName]_Summary.txt/.docx`
- ⚡ **Flexible Auto-Export** - Choose .txt, .docx, both, or neither
- 💾 **Persistent Preferences** - Settings remembered in `.env`
- 📂 **Location Control**:
  - ✅ **Use original file location** - Save exports next to source file (default: checked)
  - ☐ **Custom location** - Choose with file dialog
- 📄 **Manual Export** - Export as .txt or .docx anytime

### UI Features
- **Side-by-side layout** - Content preview and response display
- **Editable content** - Modify file content before sending
- **File info display** - Size, lines, characters, path
- **Progress indicator** - Visual feedback during processing
- **Large, readable fonts** - 30pt labels, 15pt text, 13pt buttons
- 🌙/**☀️ Dark/Light Mode** - Toggle with persistent preference

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/martinmarkovic/n8nsummarizer.git
cd n8nsummarizer
git checkout v1.5
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Required packages:**
- `requests` - HTTP requests to n8n
- `python-dotenv` - Environment variable management
- `python-docx` - Word document export (.docx)

### 4. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` with your settings:
```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/hook1
N8N_TIMEOUT=120
APP_THEME=light  # or 'dark'

# Export Preferences (auto-saved after first use)
EXPORT_USE_ORIGINAL_LOCATION=true
EXPORT_AUTO_TXT=false
EXPORT_AUTO_DOCX=false
```

## Usage

### Start Application
```bash
python main.py
```

### Basic Workflow
1. **Select File** - Click "Browse File" to load a text file
2. **Review Content** - Check/edit content in left pane
3. **Configure Export** (optional):
   - ✅ **Use original file location** - Checked by default
   - ☐ Check "Auto-export as .txt" for automatic .txt export
   - ☐ Check "Auto-export as .docx" for automatic .docx export
   - Can enable both, one, or neither
4. **Send Request** - Click "Send to n8n"
5. **Preferences Saved** - Your checkbox choices saved to `.env` automatically
6. **View Response** - Summary appears in right pane
7. **Automatic Export** - If enabled, files save automatically!

### Export Workflow Examples

#### Example 1: Auto-Export Both Formats to Original Location
**Setup:**
- File: `C:\Documents\meeting_notes.txt`
- ✅ Use original location (default)
- ✅ Auto-export .txt (you checked it)
- ✅ Auto-export .docx (you checked it)

**Result after "Send to n8n":**
- Settings saved to `.env`
- `C:\Documents\meeting_notes_Summary.txt` (created automatically)
- `C:\Documents\meeting_notes_Summary.docx` (created automatically)
- No file dialogs - instant save!
- **Next time:** Same settings loaded automatically

#### Example 2: Auto-Export Only .txt
**Setup:**
- File: `budget_2024.csv`
- ✅ Use original location
- ✅ Auto-export .txt only
- ☐ Auto-export .docx (unchecked)

**Result after "Send to n8n":**
- Settings saved to `.env`
- Only `budget_2024_Summary.txt` created
- No .docx file
- **Next time:** Same settings loaded

#### Example 3: Manual Export Only (Default)
**Setup:**
- File: `transcript.srt`
- ✅ Use original location
- ☐ Auto-export .txt (default: unchecked)
- ☐ Auto-export .docx (default: unchecked)

**Result:**
1. Get summarization response
2. No automatic exports
3. Click "📄 Export as .txt" or "📝 Export as .docx" manually
4. Default filename: `transcript_Summary.txt` or `transcript_Summary.docx`
5. Saves to original location (no dialog)

### Dark/Light Mode
- **Toggle** - Click moon (🌙) or sun (☀️) button in header
- **Pure black accents** - Section labels turn black in dark mode
- **Automatic persistence** - Choice saved to `.env`
- **Restart behavior** - Loads saved theme on startup

## Preference Persistence

### How It Works

**First Time (from config.py):**
```
App starts → Loads defaults:
  ✅ Use original location = true (from config)
  ☐ Auto .txt = false (from config)
  ☐ Auto .docx = false (from config)
```

**After First "Send to n8n":**
```
You check/uncheck boxes → Click "Send to n8n"
  → Current checkbox states saved to .env
  → Settings persist for next session
```

**Next Session:**
```
App starts → Loads from .env:
  ✅ Use original location = (your saved choice)
  ☐ Auto .txt = (your saved choice)
  ☐ Auto .docx = (your saved choice)
```

### .env File After Use

```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/hook1
N8N_TIMEOUT=120
APP_THEME=dark

# These get added/updated after first "Send to n8n"
EXPORT_USE_ORIGINAL_LOCATION=true
EXPORT_AUTO_TXT=true
EXPORT_AUTO_DOCX=false
```

## Theme Colors

### Light Mode
- **Background**: `#f7f9fb` (Light gray-blue)
- **Surface**: `#ffffff` (White)
- **Accent**: `#5e5240` (Brown)
- **Text**: `#1f2329` (Almost black)

### Dark Mode (Professional Black Accents)
- **Background**: `#1a1d21` (Dark gray, not pure black)
- **Surface**: `#222529` (Slightly lighter gray)
- **Accent**: `#000000` (Pure black) ⭐
- **Text**: `#e8e8e8` (Almost white, very light gray)

**Pure Black Accent Zones (Dark Mode):**
- Section labels: "File Selection", "n8n Webhook Override", "File Info"
- Content frames: "Content Preview & Edit", "n8n Response"

## Dependencies

**Core:**
- Python 3.8+
- tkinter (usually included with Python)

**Packages:**
```
requests==2.31.0
python-dotenv==1.0.0
python-docx==1.1.0
```

Install with:
```bash
pip install -r requirements.txt
```

## Changelog

### v1.5.0 (2025-11-30) - Latest
- 🖤 **CHANGED**: Dark mode accents now pure black (#000000) instead of purple
- 🎯 **NEW**: Smart export filenames - `[OriginalName]_Summary.txt/.docx`
- ⚙️ **NEW**: Separate auto-export checkboxes for .txt and .docx
- 💾 **NEW**: Export preferences persist to `.env` automatically
- ✅ **CHANGED**: "Use original file location" now checked by default
- 🔄 **IMPROVED**: First-time defaults from config, then saved to .env
- 💾 **IMPROVED**: Settings remembered across sessions
- 🎛️ **IMPROVED**: More granular export control (choose .txt, .docx, both, or neither)

### v1.4.1 (2025-11-29)
- 💜 **FIXED**: Purple accents properly applied to all section labels in dark mode
- ☑️ **NEW**: "Use original file location for export" checkbox
  - Auto-saves exports to source file folder when checked
  - No file dialog interruption
- 📁 **IMPROVED**: Export location preference persists during session

### v1.4.0 (2025-11-29)
- ✨ **NEW**: Dark/light mode toggle
- ✨ **NEW**: Export response as .txt or .docx
- 💜 **NEW**: Pleasant purple accents in dark mode
- 💾 **IMPROVED**: Theme preference persists to .env
- 📁 **IMPROVED**: Automatic exports folder creation

### v1.3 (2025-11-29)
- 🧵 **FIXED**: Non-blocking UI with background threading
- 🖊️ **IMPROVED**: Larger fonts (30pt labels, 13pt buttons)
- ⚡ **FIXED**: Removed blocking startup connection test
- ⏳ **IMPROVED**: Real-time status messages during requests

### v1.2 (2025-11-28)
- ⚙️ **NEW**: Webhook override in GUI
- 💾 **NEW**: Save webhook to .env option
- 🔗 **IMPROVED**: Always use GUI webhook for requests

## Export Filename Examples

**Smart filenames automatically adapt:**

| Original File | Export Filenames |
|---------------|------------------|
| `meeting_notes.txt` | `meeting_notes_Summary.txt`<br>`meeting_notes_Summary.docx` |
| `budget_2024.csv` | `budget_2024_Summary.txt`<br>`budget_2024_Summary.docx` |
| `transcript.srt` | `transcript_Summary.txt`<br>`transcript_Summary.docx` |
| `analysis.log` | `analysis_Summary.txt`<br>`analysis_Summary.docx` |

**Note**: If no file is loaded, exports use timestamp format: `n8n_response_20251130_143022.txt`

## License

MIT License - feel free to use and modify!

---

**Built with ❤️ using Python + Tkinter + n8n**
