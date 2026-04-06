# Browser Extension Installation Guide

**Quick guide to install YouTube PO Token Extractor extension**

---

## 👉 Prerequisites

- Chrome, Opera, Brave, or Edge browser
- n8n Summarizer v6.4+
- YouTube account (logged in)

---

## 📦 Step 1: Get the Extension Files

### Option A: From Git Repository

```bash
# If you already have the repo
cd n8nsummarizer
git checkout v6.4
git pull origin v6.4

# Extension is in: docs/browser_extension/
```

### Option B: Download Directly

1. Go to: https://github.com/martinmarkovic/n8nsummarizer/tree/v6.4/docs/browser_extension
2. Click "Code" → "Download ZIP"
3. Extract the ZIP file
4. Navigate to `n8nsummarizer-v6.4/docs/browser_extension/`

---

## 🔧 Step 2: Install Extension

### Chrome

1. **Open Extensions page**
   - Navigate to: `chrome://extensions/`
   - Or: Menu → Extensions → Manage Extensions

2. **Enable Developer Mode**
   - Toggle switch in **top-right corner**

3. **Load extension**
   - Click **"Load unpacked"** button (top-left)
   - Browse to `docs/browser_extension` folder
   - Click **"Select Folder"**

4. **Verify installation**
   - Extension card appears
   - Shows: "YouTube PO Token Extractor"
   - Status: Enabled

5. **Pin to toolbar (optional)**
   - Click puzzle icon in toolbar
   - Find "YouTube PO Token Extractor"
   - Click pin icon

### Opera

1. **Open Extensions page**
   - Navigate to: `opera://extensions/`
   - Or: Menu → Extensions → Extensions

2. **Enable Developer Mode**
   - Toggle "Developer mode" in top-right

3. **Load extension**
   - Click **"Load unpacked"**
   - Select `docs/browser_extension` folder

4. **Pin to toolbar**
   - Same as Chrome instructions

### Brave

1. **Open Extensions page**
   - Navigate to: `brave://extensions/`

2. **Enable Developer Mode**
   - Toggle in top-right

3. **Load extension**
   - Click **"Load unpacked"**
   - Select `docs/browser_extension` folder

### Edge

1. **Open Extensions page**
   - Navigate to: `edge://extensions/`
   - Or: Menu → Extensions → Manage Extensions

2. **Enable Developer Mode**
   - Toggle in bottom-left

3. **Load extension**
   - Click **"Load unpacked"**
   - Select `docs/browser_extension` folder

---

## ✅ Step 3: Test the Extension

### Quick Test

1. **Open YouTube**
   ```
   https://www.youtube.com/watch?v=dQw4w9WgXcQ
   ```
   (Any video works)

2. **Click extension icon**
   - Look for key icon 🔑 in toolbar
   - Popup window opens

3. **Extract token**
   - Click **"Extract PO Token"** button
   - Wait 1-2 seconds
   - Success message: "✅ PO Token copied to clipboard!"

4. **Verify clipboard**
   - Open text editor
   - Paste (Ctrl+V / Cmd+V)
   - Should see: `web+ABCDEF...` (long string)

---

## 📝 Step 4: Use in n8n Summarizer

1. **Open n8n Summarizer app**
   ```bash
   python main.py
   ```

2. **Go to Downloader tab**
   - Click "Downloader" tab (last tab)

3. **Paste PO Token**
   - Find "PO Token:" field
   - Paste token (Ctrl+V)
   - Token is hidden (shows as `***`)
   - Press Enter or Tab to save

4. **Confirm saved**
   - Log message: "PO Token updated (required for HD quality)"
   - Token saved to `.env` file automatically

5. **Test download**
   - Enter YouTube URL
   - Select quality: "1080p (Full HD)"
   - Click Download
   - Should work without errors

---

## 📌 Icon Placeholder Note

**The extension currently uses placeholder icons.**

To create custom icons:

1. Create 3 PNG files:
   - `icon16.png` (16x16 pixels)
   - `icon48.png` (48x48 pixels)
   - `icon128.png` (128x128 pixels)

2. Save in `docs/browser_extension/` folder

3. Design ideas:
   - Key icon 🔑 (token/unlock theme)
   - YouTube logo + key
   - "YT" text + download arrow

4. Reload extension after adding icons

**For now, extension works without custom icons** (browser shows default icon).

---

## 🔄 Updating the Extension

### When v6.5 or later is released:

1. **Pull latest code**
   ```bash
   cd n8nsummarizer
   git pull origin main
   ```

2. **Reload extension**
   - Go to extensions page
   - Find "YouTube PO Token Extractor"
   - Click reload icon (🔄)

3. **Check version**
   - Version number updates in extension card

---

## ⚠️ Troubleshooting Installation

### "Cannot load extension" error

**Cause:** Wrong folder selected

**Solution:**
- Make sure you select the `browser_extension` folder itself
- Not the parent `docs` folder
- Not a subfolder
- Folder must contain `manifest.json`

### "Manifest file is missing or unreadable"

**Cause:** File permissions or incomplete download

**Solution:**
```bash
# Check files exist
ls docs/browser_extension/

# Should see:
# manifest.json
# popup.html
# popup.js
# background.js
# README.md
```

### Extension loads but no icon appears

**Cause:** Icon files missing (expected, they're placeholders)

**Solution:**
- Extension still works!
- Browser shows default puzzle piece icon
- Click Extensions puzzle icon → Find "YouTube PO Token Extractor"
- Or create custom icons (see Icon Placeholder Note above)

### "Developer mode is disabled"

**Cause:** Corporate/school policy or browser restriction

**Solution:**
- Check with IT department
- Or use personal computer
- Developer mode is required for unpacked extensions

---

## 📚 Additional Resources

- **Extension README:** `docs/browser_extension/README.md`
- **Extension Usage:** See README.md → Usage section
- **PO Token Guide:** `docs/YOUTUBE_PO_TOKEN_GUIDE.md`
- **Main App README:** `README.md`

---

## ❓ Still Having Issues?

1. Read full extension README: `docs/browser_extension/README.md`
2. Check main PO Token guide: `docs/YOUTUBE_PO_TOKEN_GUIDE.md`
3. Open GitHub issue: https://github.com/martinmarkovic/n8nsummarizer/issues

---

**Last Updated:** 2026-02-15
**Extension Version:** 1.0.0
**App Version:** 6.4
