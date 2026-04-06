# YouTube PO Token Extractor

**Browser extension for n8n Summarizer - Automatically extracts YouTube PO Token for HD quality downloads.**

---

## 🚀 Quick Start

### Installation

#### Chrome / Opera / Brave / Edge

1. **Download the extension folder**
   ```bash
   # Clone the repository or download as ZIP
   git clone https://github.com/martinmarkovic/n8nsummarizer.git
   cd n8nsummarizer/docs/browser_extension
   ```

2. **Open Extensions page**
   - Chrome: `chrome://extensions/`
   - Opera: `opera://extensions/`
   - Brave: `brave://extensions/`
   - Edge: `edge://extensions/`

3. **Enable Developer Mode**
   - Toggle the "Developer mode" switch (top-right)

4. **Load the extension**
   - Click "Load unpacked"
   - Select the `docs/browser_extension` folder
   - Extension icon appears in toolbar

---

## 📝 Usage

### Extract PO Token (Simple)

1. **Open YouTube**
   - Navigate to any YouTube video (e.g., https://youtube.com/watch?v=...)

2. **Click extension icon**
   - Extension icon in browser toolbar (key icon 🔑)

3. **Click "Extract PO Token"**
   - Token is automatically extracted from cookies
   - Token copied to clipboard
   - Success message shows

4. **Paste in n8n Summarizer**
   - Open n8n Summarizer app
   - Go to Downloader tab
   - Paste token in "PO Token" field
   - Token is saved automatically

---

## ℹ️ How It Works

### Technical Details

**PO Token = YouTube visitor cookie value**

The extension:
1. Reads `VISITOR_INFO1_LIVE` cookie from `.youtube.com`
2. Formats as `web+{cookie_value}`
3. Copies to clipboard
4. Stores locally with timestamp

**Why it works:**
- YouTube uses this cookie to track visitors
- yt-dlp (YouTube downloader) uses it for authentication
- Required for HD quality (720p+) access

**Token lifespan:**
- Typically lasts **2-7 days**
- Refreshes automatically when you visit YouTube
- Extension shows last extraction date

---

## 🔒 Privacy & Security

### What This Extension Does

✅ **Only reads YouTube cookies** (`.youtube.com` domain)
✅ **Only accesses cookies when you click "Extract"**
✅ **Stores token locally in browser** (not sent anywhere)
✅ **No network requests** (completely offline)
✅ **No tracking or analytics**
✅ **Open source** (inspect code in this folder)

### Permissions Explained

| Permission | Why Needed |
|------------|------------|
| `cookies` | Read YouTube visitor cookie for PO token |
| `tabs` | Check if current tab is YouTube |
| `activeTab` | Access current tab URL |
| `clipboardWrite` | Copy token to clipboard |
| `*://*.youtube.com/*` | Access YouTube cookies only |

**No permissions for:**
- ❌ Reading other websites
- ❌ Accessing browsing history
- ❌ Sending data externally

---

## 🛠️ Troubleshooting

### "VISITOR_INFO1_LIVE cookie not found"

**Solution:**
1. Make sure you're on a YouTube page
2. Refresh the YouTube page
3. Play any video
4. Try extracting again

### "Please open a YouTube page first"

**Solution:**
- Navigate to https://youtube.com
- Then click extension icon

### Token doesn't work in n8n Summarizer

**Check:**
1. Token copied completely (starts with `web+`)
2. Token pasted without extra spaces
3. Token is recent (< 7 days old)
4. Try extracting fresh token

### Extension icon not showing

**Solution:**
1. Open `chrome://extensions/`
2. Check if extension is enabled
3. Click puzzle icon in toolbar
4. Pin "YouTube PO Token Extractor"

---

## 📚 Files Overview

```
browser_extension/
├── manifest.json       # Extension configuration
├── popup.html          # Extension popup UI
├── popup.js            # Token extraction logic
├── background.js       # Background service worker
├── icon16.png          # Extension icon (16x16)
├── icon48.png          # Extension icon (48x48)
├── icon128.png         # Extension icon (128x128)
└── README.md           # This file
```

### Key Files

**manifest.json**
- Extension metadata and permissions
- Defines popup, background worker, icons

**popup.html / popup.js**
- User interface (button, status, instructions)
- Cookie extraction logic
- Clipboard copy functionality

**background.js**
- Service worker (runs in background)
- Token storage management
- Cookie change monitoring (optional)

---

## 🔄 Updating the Extension

### Manual Update

1. Pull latest code:
   ```bash
   git pull origin v6.4
   ```

2. Reload extension:
   - Go to `chrome://extensions/`
   - Click reload icon on extension card

### Version History

- **v1.0.0** (2026-02-15) - Initial release
  - Cookie-based token extraction
  - One-click copy to clipboard
  - Token storage with timestamp

---

## ❓ FAQ

**Q: Is this safe to use?**
A: Yes! The extension only reads YouTube cookies and runs completely offline. No data is sent anywhere.

**Q: Why do I need a PO Token?**
A: YouTube requires it for downloading HD quality (720p+) videos. Without it, you can only download lower quality.

**Q: How often do I need to extract a new token?**
A: Every 2-7 days. The extension shows the age of your last extracted token.

**Q: Can I use this on Firefox?**
A: Not yet. This version is for Chromium browsers (Chrome, Opera, Brave, Edge). Firefox support coming soon.

**Q: Does this violate YouTube's terms?**
A: This tool is for personal use with content you have permission to download. Respect copyright laws and YouTube's terms of service.

---

## 🐛 Reporting Issues

If you encounter problems:

1. Check the [Troubleshooting](#troubleshooting) section
2. Open browser console (F12) and check for errors
3. Report issue on GitHub: https://github.com/martinmarkovic/n8nsummarizer/issues

Include:
- Browser name and version
- Extension version
- Error message or behavior
- Steps to reproduce

---

## 📜 License

Same as n8n Summarizer project.

---

**Last Updated:** 2026-02-15 | **Version:** 1.0.0
