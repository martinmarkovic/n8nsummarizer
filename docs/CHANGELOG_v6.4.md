# Changelog - Version 6.4 (2026-02-15)

## Overview

**Branch:** v6.4  
**Release Date:** 2026-02-15  
**Status:** ✅ Production Ready

**Major Feature:** YouTube PO Token Integration for HD Downloads

---

## Version Timeline

### v6.4.4 - SABR Streaming Fix (CURRENT STABLE)

**Released:** 2026-02-15 17:00 CET

**Problem Solved:**
- YouTube enforcing SABR streaming for web client
- n-challenge bot detection blocking downloads
- "No formats available" errors
- Downloads completely failing

**Solution:**
- Switched from `web` to `tv_embedded` client
- Bypasses SABR streaming enforcement
- Avoids n-challenge requirement
- Works with or without PO token

**Changes:**
- Updated `models/youtube_downloader.py`
  - Changed player_client: `web` → `tv_embedded`
  - Updated logging to show tv_embedded
  - Added note about SABR/n-challenge avoidance
- Created `docs/SABR_STREAMING_FIX.md`
- Updated `docs/PO_TOKEN_ISSUE_RESOLUTION.md`

**Benefits:**
- ✅ No SABR warnings
- ✅ No n-challenge errors
- ✅ No JavaScript runtime needed
- ✅ PO token optional (but recommended)
- ✅ Stable, reliable HD downloads

**Commit:** `17621b84` - Fix SABR streaming issue by using tv_embedded client

---

### v6.4.3 - Client Format Matching

**Released:** 2026-02-15 16:00 CET

**Problem Solved:**
- Downloads limited to 360p despite PO token
- Android client rejecting web-format tokens

**Solution:**
- Switched from `android` to `web` client
- Matched client type to token format

**Changes:**
- Updated `models/youtube_downloader.py`
  - Changed player_client: `android` → `web`
  - Added detailed client/token logging
- Created `docs/PO_TOKEN_ISSUE_RESOLUTION.md`

**Result:**
- ✅ Token accepted by web client
- ❌ But triggered new issue: SABR streaming

**Commit:** `0f81355b` - Fix PO Token with web client matching

**Note:** Superseded by v6.4.4 due to SABR issue

---

### v6.4.2 - PO Token Integration

**Released:** 2026-02-15 14:00 CET

**Features Added:**
- PO token support in YouTubeDownloader
- `set_po_token()` method
- `get_po_token()` method  
- `has_po_token()` method
- Token validation and formatting
- Integration with yt-dlp extractor args

**Changes:**
- Updated `models/youtube_downloader.py`
  - Added PO token handling methods
  - Added token to yt-dlp options
  - Added warning for HD without token
- Updated `controllers/downloader_controller.py`
  - Connected GUI to model PO token methods
  - Added token persistence via settings

**Issues:**
- Used android client (mismatch with web tokens)
- Token rejected/ignored
- Downloads still limited to 360p

**Commit:** `8f32a19c` - Add PO token support to downloader

---

### v6.4.1 - Browser Extension Fix

**Released:** 2026-02-15 12:00 CET

**Problem Solved:**
- Cookie extraction failing
- PO token extraction unreliable

**Solution:**
- Implemented 5 extraction methods
- Added page context injection
- Improved error handling

**Changes:**
- Updated `docs/browser_extension/content.js`
  - Added playerResponse extraction
  - Added interceptor method
  - Added innertubeApiKey + visitorData method
  - Added page script injection
  - Added fetch interception
- Updated extraction priority logic

**Result:**
- ✅ Token extraction working
- Browser extension reliable

**Commit:** `7a45d82e` - Fix browser extension with multiple methods

---

### v6.4.0 - Initial PO Token Support

**Released:** 2026-02-15 10:00 CET

**Features Added:**
- Browser extension for PO token extraction
- PO token input field in Downloader tab
- Settings persistence system
- Documentation

**New Files:**
- `docs/browser_extension/` - Extension code
  - `manifest.json` - Chrome extension manifest
  - `popup.html` - Extension UI
  - `popup.js` - UI logic
  - `content.js` - Token extraction
  - `background.js` - Background tasks
- `utils/settings_manager.py` - Settings persistence
- `docs/YOUTUBE_PO_TOKEN_GUIDE.md` - Main guide
- `docs/PO_TOKEN_QUICK_START.md` - Quick start

**Changes:**
- Updated `views/downloader_tab.py`
  - Added PO token input field
  - Added "Extract PO Token" instructions
- Updated `controllers/downloader_controller.py`  
  - Added PO token handling
  - Connected to settings manager
- Updated `main.py`
  - Initialized settings manager
  - Loaded saved PO token on startup

**Issues:**
- Cookie extraction not working reliably
- Extension needed improvements

**Commit:** `5d21f93a` - Initial YouTube PO token support

---

## Migration Guide

### From Any Previous Version to v6.4.4

**Step 1: Pull Latest**
```bash
cd F:\Python scripts\n8nsummarizer
git pull origin v6.4
```

**Step 2: Verify**
```bash
grep "Version:" models/youtube_downloader.py
# Should show: 6.4.4

grep "'player_client'" models/youtube_downloader.py
# Should show: ['tv_embedded']
```

**Step 3: Test**
- Restart application
- Download any video
- Check logs for "tv_embedded"
- Verify no SABR/n-challenge warnings
- Confirm HD download succeeds

---

## Breaking Changes

**None** - All changes backward compatible

**Optional Migration:**
- Extract PO token with browser extension
- Token automatically saved to `.env`
- Improves quality and reliability

---

## Known Issues

**None in v6.4.4**

**Previous Issues (All Fixed):**
- ✅ Client/token format mismatch (fixed in 6.4.3)
- ✅ SABR streaming blocking (fixed in 6.4.4)
- ✅ n-challenge errors (fixed in 6.4.4)

---

## Dependencies

**No New Dependencies Required**

**Optional (for development):**
- Chrome/Edge browser (for extension)
- Latest yt-dlp (recommended: `pip install -U yt-dlp`)

**NOT Required:**
- ❌ Deno (not needed with tv_embedded)
- ❌ Node.js (not needed with tv_embedded)
- ❌ EJS solver (not needed with tv_embedded)

---

## Performance

**Download Speed:**
- Same as before (network-limited)

**Reliability:**
- ✅ Significantly improved (no SABR/n-challenge failures)

**Quality:**
- ✅ Full HD/4K available with tv_embedded
- ✅ Works with or without PO token

---

## Testing

**Tested Scenarios:**
- ✅ HD download with PO token (720p, 1080p, 4K)
- ✅ HD download without PO token
- ✅ Multiple consecutive downloads
- ✅ Long videos (>1 hour)
- ✅ Various video types (music, vlogs, tutorials)
- ✅ Token persistence across restarts

**Test Results:**
- All scenarios passing
- No SABR warnings observed
- No n-challenge errors observed
- Consistent HD quality

---

## Documentation

**New Documentation:**
- `docs/SABR_STREAMING_FIX.md` - SABR issue and solution
- `docs/PO_TOKEN_ISSUE_RESOLUTION.md` - Complete timeline
- `docs/CHANGELOG_v6.4.md` - This file
- `docs/PO_TOKEN_QUICK_START.md` - Quick start guide
- `docs/YOUTUBE_PO_TOKEN_GUIDE.md` - Comprehensive guide

**Updated Documentation:**
- All guides updated for tv_embedded client
- Troubleshooting sections enhanced
- Testing checklists added

---

## Credits

**Research & Implementation:**
- YouTube restrictions analysis
- yt-dlp client comparison  
- SABR streaming investigation
- n-challenge research

**References:**
- [yt-dlp Issue #12482](https://github.com/yt-dlp/yt-dlp/issues/12482) - SABR formats
- [yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)
- Community discussions on Reddit and GitHub

---

## Future Plans

**Monitoring:**
- Watch for YouTube changes affecting tv_embedded
- Track yt-dlp updates
- Monitor SABR rollout status

**Potential Enhancements:**
- Auto-update yt-dlp
- Alternative client fallback
- Enhanced error recovery

---

## Summary

**v6.4 Branch Achievements:**

✅ **Added:** Complete PO token support
✅ **Added:** Browser extension for easy token extraction  
✅ **Added:** Automatic token persistence
✅ **Fixed:** Client/token format matching
✅ **Fixed:** SABR streaming bypass
✅ **Fixed:** n-challenge avoidance
✅ **Result:** Reliable HD YouTube downloads

**Status:** Production Ready 🚀

---

**Last Updated:** 2026-02-15  
**Current Stable Version:** 6.4.4
