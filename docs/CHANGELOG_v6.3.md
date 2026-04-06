# Changelog - Version 6.3

## Release Date: 2026-02-15

## Overview

Version 6.3 introduces **persistent user preferences** using `.env` file storage. The application now remembers your settings across sessions, providing a seamless user experience.

---

## ✨ New Features

### 1. Settings Persistence System

**Remembers your preferences automatically:**
- ✅ **Last Active Tab** - Opens the tab you were using when you closed the app
- ✅ **Downloader Save Path** - Remembers your preferred download folder
- ✅ **Downloader Quality** - Remembers your preferred video quality (1080p, 720p, etc.)

**How it works:**
- Settings are stored in `.env` file (separate from `config.json`)
- `.env` is created automatically from `.env.example` on first run
- All preferences saved immediately when changed
- No manual configuration required

### 2. PO Token Support (Experimental)

**For HD quality downloads (720p+):**
- Added `YOUTUBE_PO_TOKEN` field in `.env`
- Supports manual PO token entry for HD quality access
- See `docs/YOUTUBE_PO_TOKEN_GUIDE.md` for extraction methods

---

## 📝 Documentation

### New Documentation Files

1. **`docs/YOUTUBE_PO_TOKEN_GUIDE.md`**
   - Comprehensive guide to PO token extraction
   - 4 solution options (from easiest to most advanced)
   - Step-by-step instructions with examples
   - Troubleshooting tips

2. **`.env.example`**
   - Template for user settings
   - Commented explanations for each setting
   - Automatically copied to `.env` on first run

3. **`docs/CHANGELOG_v6.3.md`** (this file)
   - Complete changelog for v6.3
   - Implementation details
   - Migration guide

---

## 🔧 Technical Changes

### New Files Created

```
utils/
  settings_manager.py          # Settings persistence manager

docs/
  YOUTUBE_PO_TOKEN_GUIDE.md    # PO token extraction guide
  CHANGELOG_v6.3.md            # This changelog

.env.example                   # Settings template
```

### Modified Files

```
main.py                        # SettingsManager initialization
views/main_window.py           # Tab persistence integration
controllers/downloader_controller.py  # Path & quality persistence
```

### Key Implementation Details

#### SettingsManager Class

**Location:** `utils/settings_manager.py`

**Features:**
- Read/write `.env` file while preserving comments
- Type-safe getters (string, int)
- Convenience methods for common settings
- Automatic `.env` creation from example
- Error handling with sensible defaults

**API:**
```python
settings = SettingsManager()

# Generic methods
settings.get(key, default)       # Get string value
settings.get_int(key, default)   # Get integer value
settings.set(key, value)         # Set value (auto-saves)

# Convenience methods
settings.get_last_active_tab()           # Returns int (0-6)
settings.set_last_active_tab(index)      # Saves tab index
settings.get_downloader_save_path()      # Returns path string
settings.set_downloader_save_path(path)  # Saves path
settings.get_downloader_quality()        # Returns quality string
settings.set_downloader_quality(quality) # Saves quality
settings.get_youtube_po_token()          # Returns token or None
settings.set_youtube_po_token(token)     # Saves token
```

#### Integration Points

**main.py:**
```python
# Initialize settings manager first
settings = SettingsManager()

# Pass to main window
window = MainWindow(root, settings)

# Inject into downloader controller
window.downloader_tab.controller.set_settings_manager(settings)
```

**main_window.py:**
```python
# Store settings reference
self.settings = settings_manager

# Restore last active tab after UI setup
self._restore_last_active_tab()

# Bind tab change event
self.notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)

# Save tab on change
def _on_tab_changed(self, event=None):
    current_tab = self.notebook.index(self.notebook.select())
    self.settings.set_last_active_tab(current_tab)
```

**downloader_controller.py:**
```python
# Inject settings manager
def set_settings_manager(self, settings_manager):
    self.settings = settings_manager
    
    # Restore saved path
    saved_path = self.settings.get_downloader_save_path()
    if saved_path:
        self.view.download_path_var.set(saved_path)
        self.model.set_download_path(saved_path)
    
    # Restore saved quality
    saved_quality = self.settings.get_downloader_quality()
    if saved_quality:
        self.view.resolution_var.set(saved_quality)
        self.model.set_resolution(saved_quality)

# Save on change
def set_download_path(self, path):
    self.model.set_download_path(path)
    if self.settings:
        self.settings.set_downloader_save_path(path)

def set_resolution(self, resolution):
    self.model.set_resolution(resolution)
    if self.settings:
        self.settings.set_downloader_quality(resolution)
```

---

## 💾 .env File Structure

### Settings Stored in .env

```ini
# === Application Window Settings ===
LAST_ACTIVE_TAB=0

# === Downloader Settings ===
DOWNLOADER_SAVE_PATH=/path/to/downloads
DOWNLOADER_QUALITY=Best Available

# === YouTube PO Token (Optional) ===
YOUTUBE_PO_TOKEN=

# === Font Size (Already Existed) ===
APP_FONT_SIZE=10
```

### Settings NOT in .env

**These remain in `config.json` (app configuration, not user preferences):**
- LLM model settings
- API URLs and keys
- n8n webhook configurations
- System-level settings

**Distinction:**
- `config.json` = Application configuration (rarely changes)
- `.env` = User preferences (changes frequently)

---

## 🚀 User Experience Improvements

### Before v6.3
- App always opened to first tab (File Summarizer)
- Download folder selection required every session
- Quality preference reset to default every session
- Manual re-configuration after each restart

### After v6.3
- App opens to your last-used tab automatically
- Download folder remembered across sessions
- Quality preference persists (e.g., stays on "1080p")
- Zero reconfiguration - seamless experience

---

## 🔍 Testing v6.3

### Verification Steps

1. **Tab Persistence:**
   - Open app
   - Switch to Downloader tab (or any tab)
   - Close app
   - Reopen app
   - ✅ Should open directly to Downloader tab

2. **Download Path Persistence:**
   - Go to Downloader tab
   - Click "Browse..." and select folder
   - Close app
   - Reopen app
   - Go to Downloader tab
   - ✅ Folder path should be pre-filled

3. **Quality Persistence:**
   - Select "1080p (Full HD)" quality
   - Close app
   - Reopen app
   - ✅ Quality dropdown should show "1080p (Full HD)"

4. **.env File Creation:**
   - Delete `.env` if exists
   - Run app
   - ✅ `.env` should be created from `.env.example`

---

## ⚠️ Breaking Changes

**None.** Version 6.3 is fully backward compatible.

- Existing installations will work without modification
- `.env` is created automatically if missing
- No migration steps required

---

## 🐛 Bug Fixes

- None (no bugs fixed in this release - pure feature addition)

---

## 📝 Notes

### Why .env Instead of config.json?

**Design Decision:**
- `config.json` = Application-level configuration (API keys, models, endpoints)
- `.env` = User-level preferences (last tab, download path, quality)

**Benefits:**
- Clear separation of concerns
- `.env` gitignored by default (won't commit personal paths)
- Standard practice in modern applications
- Easy to understand and manually edit

### Font Size Setting

Note: `APP_FONT_SIZE` was already stored in `.env` before v6.3. This release adds **three new settings** to the same file:
- `LAST_ACTIVE_TAB`
- `DOWNLOADER_SAVE_PATH`
- `DOWNLOADER_QUALITY`

---

## 🔮 Future Enhancements

### Planned for Future Versions

1. **PO Token UI Field** (v6.4)
   - Add input field for PO token in Downloader tab
   - Token validation before use
   - Expiry detection with warnings

2. **More Persistent Settings** (v6.5+)
   - Last used LLM model
   - Last summary output folder
   - Window size and position
   - Theme preference (dark/light)

3. **Settings UI Panel** (v7.0)
   - Dedicated settings/preferences tab
   - Visual interface for all .env settings
   - Reset to defaults button

---

## 👥 Credits

**Development:** martinmarkovic  
**Version:** 6.3  
**Release Date:** February 15, 2026  
**Branch:** v6.3  

---

## 📚 Related Documentation

- **PO Token Guide:** `docs/YOUTUBE_PO_TOKEN_GUIDE.md`
- **Settings Template:** `.env.example`
- **Main README:** `README.md`

---

*Last Updated: 2026-02-15*
