# Text File Scanner - Extended v1.5

Python GUI application for sending file content to n8n webhooks and receiving summarization responses, with **dark/light mode toggle**, **export functionality**, and **smart auto-export**.

## ✨ New in v1.5

### 🖤 Pure Black Accents in Dark Mode
- **Pure black section labels** (#000000) in dark mode
- Better contrast and visual clarity
- Sharper, more professional appearance

### 🎯 Smart Export Filenames
- **Intelligent naming**: Exports now use `[OriginalFileName]_Summary.txt/.docx`
- **No more generic timestamps**: Get meaningful filenames automatically
- **Example**: `meeting_notes.txt` → exports as `meeting_notes_Summary.txt` and `meeting_notes_Summary.docx`

### ⚡ Auto-Export After Summarization
- **One-click automation**: Check "Auto-export as .txt and .docx after summarization"
- **Both formats at once**: Automatically creates .txt AND .docx files
- **No interruptions**: Silent export - no file dialogs, just results
- **Smart locations**: Respects "Use original file location" setting

## Features

### Core Functionality
- 📁 **File Selection** - Browse and load text files (.txt, .log, .csv, .json, .xml, .srt, .docx)
- 🔗 **n8n Webhook Integration** - Send content to configured n8n webhook
- ⏱️ **Real-time Response** - Receive and display summarization from n8n
- 🧵 **Non-blocking UI** - Background threading prevents GUI freezes
- ⚙️ **Webhook Override** - Customize webhook URL directly in GUI
- 💾 **Persistent Settings** - Save webhook and theme to `.env`

### Export Features
- 💾 **Smart Filenames** - `[OriginalName]_Summary.txt/.docx`
- ⚡ **Auto-Export** - Automatic .txt + .docx after summarization
- 📂 **Location Control**:
  - ☑️ **Use original file location** - Save exports next to source file
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
   - ☑️ Check "Auto-export as .txt and .docx" for automatic saving
   - ☑️ Check "Use original file location" to save next to source file
4. **Send Request** - Click "Send to n8n"
5. **View Response** - Summary appears in right pane
6. **Automatic Export** - If enabled, both files save automatically!

### Export Workflow Examples

#### Example 1: Auto-Export to Original Location
**Setup:**
- File: `C:\Documents\meeting_notes.txt`
- ☑️ Auto-export enabled
- ☑️ Use original location enabled

**Result after summarization:**
- `C:\Documents\meeting_notes_Summary.txt` (created automatically)
- `C:\Documents\meeting_notes_Summary.docx` (created automatically)
- No file dialogs - instant save!

#### Example 2: Auto-Export to Default Location
**Setup:**
- File: `C:\Documents\meeting_notes.txt`
- ☑️ Auto-export enabled
- ☐ Use original location disabled

**Result after summarization:**
- `exports/meeting_notes_Summary.txt`
- `exports/meeting_notes_Summary.docx`
- Files in default exports folder

#### Example 3: Manual Export with Smart Filenames
**Setup:**
- File: `budget_2024.csv`
- ☐ Auto-export disabled

**Steps:**
1. Get summarization response
2. Click "📄 Export as .txt" or "📝 Export as .docx"
3. Default filename: `budget_2024_Summary.txt` or `budget_2024_Summary.docx`
4. Choose location and save

### Dark/Light Mode
- **Toggle** - Click moon (🌙) or sun (☀️) button in header
- **Pure black accents** - Section labels turn black in dark mode
- **Automatic persistence** - Choice saved to `.env`
- **Restart behavior** - Loads saved theme on startup

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
- ⚡ **NEW**: Auto-export checkbox - automatically saves both .txt and .docx after summarization
- 🔇 **IMPROVED**: Silent auto-export - no file dialogs when enabled
- 📁 **IMPROVED**: Export filename logic unified across manual and auto-export

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
