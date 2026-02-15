# Changelog - Version 6.4

## Release Date: 2026-02-15

## Overview

Version 6.4 introduces **PO Token GUI integration** and a **browser extension** for automatic token extraction, making HD quality YouTube downloads seamless.

---

## ✨ New Features

### 1. PO Token Input Field in GUI

**New input field in Downloader tab:**
- 🔑 **PO Token field** - Next to Quality selector
- 🔒 **Password-style hiding** - Token displayed as `***`
- 💾 **Auto-save to .env** - Persists across sessions
- ❓ **Help button** - Quick instructions
- ✅ **Easy paste** - Copy from extension, paste here

**Location:**
```
Downloader Tab
  ├─ YouTube URL
  ├─ Save to: [Browse...]
  ├─ Quality: [1080p (Full HD)] [Download]
  └─ PO Token: [***************] [Help]
```

### 2. Browser Extension for Automatic Extraction

**One-click PO Token extraction:**
- 🌐 **Works on all Chromium browsers** (Chrome, Opera, Brave, Edge)
- 💁 **One-click extraction** - No manual cookie hunting
- 📋 **Auto-copy to clipboard** - Ready to paste immediately
- 💾 **Local storage** - Remembers last token with timestamp
- 🔒 **Privacy-focused** - No network requests, completely offline
- 📝 **Open source** - Inspect all code

**Extension features:**
```
🔑 YouTube PO Token Extractor
┌────────────────────────────────┐
│ Extract PO Token for HD     │
│ quality downloads            │
│                              │
│ [ Extract PO Token ]         │
│                              │
│ ✅ Token copied to clipboard! │
│ Token: web+ABCDEF...         │
│                              │
│ Instructions:                │
│ 1. Open YouTube video        │
│ 2. Click "Extract"            │
│ 3. Paste in n8n Summarizer   │
└────────────────────────────────┘
```

### 3. Enhanced Settings Persistence

**PO Token now persists:**
- Saved to `.env` file automatically
- Restored on app restart
- Synced between controller and settings

**Updated `.env` structure:**
```ini
# Application Window Settings
LAST_ACTIVE_TAB=6

# Downloader Settings
DOWNLOADER_SAVE_PATH=/path/to/downloads
DOWNLOADER_QUALITY=1080p (Full HD)

# YouTube PO Token (v6.4)
YOUTUBE_PO_TOKEN=web+YOUR_TOKEN_HERE

# Font Size
APP_FONT_SIZE=10
```

---

## 📝 Documentation

### New Documentation Files

1. **`docs/browser_extension/`** - Complete extension package
   - `manifest.json` - Extension configuration
   - `popup.html` - User interface
   - `popup.js` - Token extraction logic
   - `background.js` - Background service worker
   - `README.md` - Extension documentation
   - `INSTALLATION.md` - Step-by-step installation guide
   - Icon files (placeholders)

2. **`docs/CHANGELOG_v6.4.md`** (this file)
   - Complete changelog for v6.4
   - Feature descriptions
   - Usage instructions

---

## 🔧 Technical Changes

### Modified Files

```
views/downloader_tab.py
  - Added po_token_var StringVar
  - Added PO Token entry field (password style)
  - Added Help button with instructions
  - Added _on_po_token_change() handler
  - Added _show_po_token_help() dialog
  - Added get_po_token() method

controllers/downloader_controller.py
  - Added set_po_token() method
  - Integrated PO token with settings
  - Restore saved token on startup
  - Pass token to model before download
  - Log token usage
```

### New Files

```
docs/browser_extension/
  ├── manifest.json           # Extension metadata
  ├── popup.html              # UI interface
  ├── popup.js                # Token extraction
  ├── background.js           # Service worker
  ├── README.md               # Extension docs
  ├── INSTALLATION.md         # Install guide
  ├── icon16.png              # 16x16 icon
  ├── icon48.png              # 48x48 icon
  └── icon128.png             # 128x128 icon
```

---

## 🚀 User Workflow

### Complete HD Download Workflow

**Step 1: Install Browser Extension**
```
1. Open chrome://extensions/
2. Enable Developer Mode
3. Load unpacked extension
4. Select docs/browser_extension/ folder
5. Extension icon appears in toolbar
```

**Step 2: Extract PO Token**
```
1. Open any YouTube video
2. Click extension icon (🔑)
3. Click "Extract PO Token"
4. Token copied to clipboard
5. Success message shows
```

**Step 3: Configure n8n Summarizer**
```
1. Open n8n Summarizer app
2. Go to Downloader tab
3. Paste token in PO Token field
4. Token auto-saves to .env
5. Ready for HD downloads
```

**Step 4: Download HD Video**
```
1. Enter YouTube URL
2. Select "1080p (Full HD)" quality
3. Click Download
4. HD video downloads successfully
```

---

## 🔍 Testing v6.4

### Verification Steps

**1. GUI PO Token Field:**
- [ ] Open Downloader tab
- [ ] See "PO Token:" label and field
- [ ] Field displays as password (***)
- [ ] Help button shows instructions
- [ ] Paste test token
- [ ] Log shows "PO Token updated"

**2. Browser Extension:**
- [ ] Extension loads without errors
- [ ] Icon appears in toolbar
- [ ] Popup opens with UI
- [ ] "Extract" button works
- [ ] Token copied to clipboard
- [ ] Success message displays

**3. Settings Persistence:**
- [ ] Paste token in GUI
- [ ] Close app
- [ ] Check `.env` file
- [ ] `YOUTUBE_PO_TOKEN=web+...` present
- [ ] Reopen app
- [ ] Token field restored (shows ***)

**4. HD Download:**
- [ ] Extract fresh token
- [ ] Paste in GUI
- [ ] Select 1080p quality
- [ ] Download YouTube video
- [ ] Download succeeds
- [ ] Video is HD quality

---

## 🔒 Privacy & Security

### Browser Extension Security

**What it does:**
✅ Reads YouTube cookies only (`.youtube.com` domain)
✅ Only when you click "Extract"
✅ Stores token locally in browser
✅ No network requests (completely offline)
✅ No tracking or analytics
✅ Open source (inspect all code)

**What it DOESN'T do:**
❌ Access other websites
❌ Read browsing history
❌ Send data externally
❌ Track your activity

### Token Storage

**Where token is stored:**
1. **Browser:** `chrome.storage.local` (encrypted by browser)
2. **n8n Summarizer:** `.env` file (plain text, gitignored)

**Token lifespan:**
- Valid for **2-7 days**
- Automatically refreshes when you visit YouTube
- Extension shows age of last extracted token

---

## ⚠️ Breaking Changes

**None.** Version 6.4 is fully backward compatible.

- v6.3 settings preserved
- Manual PO token entry still works (see v6.3 guide)
- Extension is optional enhancement

---

## 🐛 Bug Fixes

- None (pure feature addition)

---

## 📚 Browser Extension Details

### How Token Extraction Works

**Technical process:**
```javascript
// 1. Get YouTube visitor cookie
const cookies = await chrome.cookies.getAll({
  domain: '.youtube.com'
});

// 2. Find VISITOR_INFO1_LIVE
const visitorCookie = cookies.find(
  c => c.name === 'VISITOR_INFO1_LIVE'
);

// 3. Format as PO token
const poToken = `web+${visitorCookie.value}`;

// 4. Copy to clipboard
await navigator.clipboard.writeText(poToken);
```

**Why this works:**
- YouTube uses `VISITOR_INFO1_LIVE` cookie to identify visitors
- yt-dlp (YouTube downloader) accepts this as PO token
- Format: `web+{cookie_value}`
- Required for HD quality authentication

### Extension Permissions Explained

| Permission | Purpose |
|------------|----------|
| `cookies` | Read YouTube visitor cookie for PO token |
| `tabs` | Check if current tab is YouTube |
| `activeTab` | Access current tab URL |
| `clipboardWrite` | Copy extracted token to clipboard |
| `*://*.youtube.com/*` | Limit access to YouTube domain only |

**All permissions are minimal and necessary.**

---

## 🛠️ Troubleshooting

### Extension Issues

**"VISITOR_INFO1_LIVE cookie not found"**

Solution:
1. Refresh YouTube page
2. Play any video
3. Try extracting again

**"Please open a YouTube page first"**

Solution:
- Navigate to https://youtube.com
- Then click extension icon

**Extension icon not showing**

Solution:
1. Open `chrome://extensions/`
2. Check extension is enabled
3. Click puzzle icon in toolbar
4. Pin "YouTube PO Token Extractor"

### GUI Issues

**PO Token field not visible**

Solution:
- Update to v6.4: `git pull origin v6.4`
- Check you're on correct branch
- Field is below Quality dropdown

**Token not saving**

Solution:
1. Check `.env` file exists
2. Check write permissions
3. Token updates on focus loss or Enter key

**HD downloads still failing**

Solution:
1. Extract fresh token (< 7 days old)
2. Check token format starts with `web+`
3. No extra spaces when pasting
4. Try different video

---

## 🔮 Future Enhancements

### Planned for Future Versions

**v6.5: Token Management UI**
- Token expiry indicator in GUI
- "Refresh Token" button
- Token validation before download
- Warning when token > 5 days old

**v6.6: Firefox Extension**
- Firefox-compatible version
- WebExtensions API
- Same functionality as Chrome version

**v7.0: Advanced Token Features**
- Multiple token profiles
- Automatic token refresh
- Token sync across devices
- Token sharing (optional)

---

## 👥 Credits

**Development:** martinmarkovic  
**Version:** 6.4  
**Release Date:** February 15, 2026  
**Branch:** v6.4  

**Special Thanks:**
- yt-dlp project for PO token support
- Chromium Extensions API
- n8n Summarizer community

---

## 📚 Related Documentation

- **Extension README:** `docs/browser_extension/README.md`
- **Extension Installation:** `docs/browser_extension/INSTALLATION.md`
- **PO Token Guide (Manual):** `docs/YOUTUBE_PO_TOKEN_GUIDE.md`
- **v6.3 Changelog:** `docs/CHANGELOG_v6.3.md`
- **Main README:** `README.md`

---

## 📝 Installation Quick Reference

### For Users Upgrading from v6.3

```bash
# Pull v6.4 branch
git checkout v6.4
git pull origin v6.4

# Install browser extension
# 1. Open chrome://extensions/
# 2. Enable Developer Mode
# 3. Load unpacked: docs/browser_extension/

# Run app
python main.py

# Extract token from extension
# Paste in Downloader tab PO Token field
# Start downloading HD videos!
```

### For New Users

```bash
# Clone repository
git clone https://github.com/martinmarkovic/n8nsummarizer.git
cd n8nsummarizer
git checkout v6.4

# Install dependencies
pip install -r requirements.txt

# Install browser extension (see INSTALLATION.md)

# Run app
python main.py

# Follow first-time setup wizard
```

---

*Last Updated: 2026-02-15*
