# Text File Scanner - Extended v1.4

Python GUI application for sending file content to n8n webhooks and receiving summarization responses, with **dark/light mode toggle** and **export functionality**.

## ✨ New in v1.4

### 🌙 Dark/Light Mode Toggle
- **Slack-inspired dark theme** with pleasant purple accents
- **Light mode** with clean, modern brown tones
- **Persistent preference** saved to `.env`
- **One-click toggle** button in header
- **Purple section labels** in dark mode (File Selection, Webhook Override, File Info, etc.)

### 📤 Export Response Functionality
- **Export as .txt** - Plain text export with timestamp
- **Export as .docx** - Formatted Word document export
- **Export location options**:
  - ☑️ **Use original file location** - Auto-save to source file's folder (no dialog)
  - ☐ **Custom location** - Choose location with file dialog
- **Automatic timestamps** in filenames

## Features

### Core Functionality
- 📁 **File Selection** - Browse and load text files (.txt, .log, .csv, .json, .xml, .srt, .docx)
- 🔗 **n8n Webhook Integration** - Send content to configured n8n webhook
- ⏱️ **Real-time Response** - Receive and display summarization from n8n
- 🧵 **Non-blocking UI** - Background threading prevents GUI freezes
- ⚙️ **Webhook Override** - Customize webhook URL directly in GUI
- 💾 **Persistent Settings** - Save webhook and theme to `.env`

### UI Features
- **Side-by-side layout** - Content preview and response display
- **Editable content** - Modify file content before sending
- **File info display** - Size, lines, characters, path
- **Progress indicator** - Visual feedback during processing
- **Large, readable fonts** - 30pt labels, 15pt text, 13pt buttons

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/martinmarkovic/n8nsummarizer.git
cd n8nsummarizer
git checkout v1.4
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
3. **Configure Webhook** - Enter or verify webhook URL
4. **Send Request** - Click "Send to n8n"
5. **View Response** - Summary appears in right pane
6. **Export** (optional) - Save response as .txt or .docx

### Dark/Light Mode
- **Toggle** - Click moon (🌙) or sun (☀️) button in header
- **Automatic persistence** - Choice saved to `.env`
- **Restart behavior** - Loads saved theme on startup
- **Purple accents** - All section labels turn purple in dark mode

### Export Responses

**Export Location Options:**

1. **☑️ Use original file location for export** (checkbox)
   - When **checked**: Exports save to the same folder as the loaded file
   - No file dialog shown - instant save
   - Perfect for keeping exports with source files

2. **☐ Use original file location for export** (unchecked)
   - When **unchecked**: File dialog appears
   - Choose custom save location
   - Default folder: `exports/`

**Export Steps:**
1. Ensure response content is displayed
2. (Optional) Check "Use original file location" to auto-save
3. Click **📄 Export as .txt** or **📝 Export as .docx**
4. If checkbox unchecked, choose location in dialog
5. Files saved with automatic timestamps

**Export formats:**
- `.txt` - Plain text with original formatting
- `.docx` - Word document with heading, timestamp, and formatted content

**Example filenames:**
- `n8n_response_20251129_142030.txt`
- `n8n_response_20251129_142030.docx`

## Theme Colors

### Light Mode
- **Background**: `#f7f9fb` (Light gray-blue)
- **Surface**: `#ffffff` (White)
- **Accent**: `#5e5240` (Brown)
- **Text**: `#1f2329` (Almost black)

### Dark Mode (Slack-Inspired)
- **Background**: `#1a1d21` (Dark gray, not pure black)
- **Surface**: `#222529` (Slightly lighter gray)
- **Accent**: `#8b5cf6` (Pleasant purple) ⭐
- **Text**: `#e8e8e8` (Almost white, very light gray)

**Purple Accent Zones (Dark Mode):**
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

### v1.4.1 (2025-11-29) - Latest
- 💜 **FIXED**: Purple accents now properly applied to all section labels in dark mode
- ☑️ **NEW**: "Use original file location for export" checkbox
  - Auto-saves exports to source file folder when checked
  - No file dialog interruption
- 📁 **IMPROVED**: Export location preference persists during session

### v1.4.0 (2025-11-29)
- ✨ **NEW**: Dark/light mode toggle with Slack-inspired dark theme
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

## License

MIT License - feel free to use and modify!

---

**Built with ❤️ using Python + Tkinter + n8n**
