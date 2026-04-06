# Browser Extension Troubleshooting Guide

**Solutions for common PO Token extraction issues**

---

## ❌ "VISITOR_INFO1_LIVE cookie not found"

### Problem
Extension can't find the YouTube visitor cookie.

### Solution (v6.4.1)

**Extension updated!** v6.4.1 uses multiple extraction methods:
1. Page context data (most reliable)
2. YouTube config objects
3. Cookies (fallback)

**Update steps:**
```bash
# Pull latest v6.4
cd n8nsummarizer
git pull origin v6.4

# Reload extension
1. Go to chrome://extensions/
2. Find "YouTube PO Token Extractor"
3. Click reload button (🔄)
```

**New extraction methods:**
- ✅ `ytInitialPlayerResponse` - Player data
- ✅ `ytcfg.VISITOR_DATA` - YouTube config
- ✅ `INNERTUBE_CONTEXT` - API context
- ✅ `ytInitialData` - Page data
- ✅ Script tags - Embedded data
- ✅ Cookies - Last fallback

---

## 🔧 Manual Token Extraction (Alternative)

**If extension still fails, use browser DevTools:**

### Method 1: Console Extraction (Easiest)

1. **Open YouTube video**
   - Any video will work
   - Play the video briefly

2. **Open DevTools Console**
   - Press `F12`
   - Click "Console" tab

3. **Run extraction script**
   ```javascript
   // Copy and paste this entire block:
   (function() {
     // Try ytcfg first
     if (window.ytcfg && window.ytcfg.get) {
       const visitorData = window.ytcfg.get('VISITOR_DATA');
       if (visitorData) {
         console.log('Token found!');
         console.log('Copy this token:');
         console.log(visitorData);
         navigator.clipboard.writeText(visitorData);
         return visitorData;
       }
     }
     
     // Try ytInitialPlayerResponse
     if (window.ytInitialPlayerResponse && 
         window.ytInitialPlayerResponse.responseContext && 
         window.ytInitialPlayerResponse.responseContext.serviceTrackingParams) {
       const params = window.ytInitialPlayerResponse.responseContext.serviceTrackingParams;
       for (const param of params) {
         if (param.params) {
           for (const p of param.params) {
             if (p.key === 'visitor_data' && p.value) {
               console.log('Token found!');
               console.log('Copy this token:');
               console.log(p.value);
               navigator.clipboard.writeText(p.value);
               return p.value;
             }
           }
         }
       }
     }
     
     console.error('Token not found. Try playing video and run again.');
   })();
   ```

4. **Token copied to clipboard**
   - If successful: "Token found!" message
   - Token automatically copied
   - Paste in n8n Summarizer

### Method 2: Network Tab Extraction

1. **Open DevTools Network tab**
   - Press `F12`
   - Click "Network" tab
   - Clear existing requests (🚫 icon)

2. **Play YouTube video**
   - Play any video
   - Wait 5 seconds

3. **Filter requests**
   - In filter box, type: `videoplayback`
   - Or type: `player`

4. **Find visitor data**
   - Click any `videoplayback` request
   - Click "Headers" tab
   - Scroll to "Query String Parameters"
   - Look for `pot=` parameter
   - Or look for `visitor_data=` parameter

5. **Copy token value**
   - Copy the value after `visitor_data=`
   - If using `pot=`, use the value as-is

---

## 🔍 Extension Debugging

### Check Extension Console

1. **Open extensions page**
   ```
   chrome://extensions/
   ```

2. **Enable Developer Mode**
   - Toggle if not already enabled

3. **Inspect extension**
   - Find "YouTube PO Token Extractor"
   - Click "Inspect views: service worker"
   - Console shows background errors

4. **Check for errors**
   - Look for red error messages
   - Report errors on GitHub issues

### Test Extraction Methods

**On YouTube video page, open Console (F12), test each method:**

```javascript
// Test 1: ytcfg
console.log('ytcfg.VISITOR_DATA:', 
  window.ytcfg?.get('VISITOR_DATA'));

// Test 2: INNERTUBE_CONTEXT
console.log('INNERTUBE visitorData:', 
  window.ytcfg?.get('INNERTUBE_CONTEXT')?.client?.visitorData);

// Test 3: ytInitialPlayerResponse
console.log('ytInitialPlayerResponse exists:', 
  !!window.ytInitialPlayerResponse);

// Test 4: Cookies
console.log('Cookies:', document.cookie);
```

**What to expect:**
- At least ONE method should return a value
- Value should be 20+ characters
- If ALL return `undefined`, YouTube page may not be fully loaded

---

## 🎯 Best Practices

### For Reliable Extraction

1. **Use YouTube while logged in**
   - Logged-in users have more stable tokens
   - Guest mode may have limited data

2. **Use video page, not homepage**
   - Open actual video: `youtube.com/watch?v=...`
   - Not search page or channel page

3. **Play video first**
   - Let video buffer for 5 seconds
   - This ensures player data is loaded

4. **Use popular videos**
   - Well-cached videos load faster
   - All YouTube data structures present

5. **Refresh if needed**
   - Hard refresh: `Ctrl+Shift+R` (Windows/Linux)
   - Or: `Cmd+Shift+R` (Mac)

---

## ⚠️ Common Issues

### "Could not find visitor data"

**Causes:**
- Page not fully loaded
- Ad blocker interfering
- YouTube A/B testing different page structure

**Solutions:**
1. Refresh page and wait 10 seconds
2. Disable ad blockers temporarily
3. Try different video
4. Try incognito mode
5. Use manual console extraction

### "Invalid token format. Token seems too short"

**Causes:**
- Extracted wrong value
- Incomplete extraction

**Solutions:**
1. Try extraction again
2. Check if token is > 20 characters
3. Use manual console method

### "Extraction failed: Cannot read properties"

**Causes:**
- Extension trying to access unavailable objects
- Page structure changed

**Solutions:**
1. Update extension to v6.4.1+
2. Try manual extraction
3. Report issue with browser console errors

---

## 🆘 Still Not Working?

### Fallback: Manual PO Token Guide

Use the comprehensive manual guide:
```
docs/YOUTUBE_PO_TOKEN_GUIDE.md
```

**4 manual methods available:**
1. Browser DevTools (Network tab)
2. Cookie extraction tools
3. Python script
4. yt-dlp direct extraction

### Report Issue

**If extension completely fails:**

1. **Collect diagnostic info:**
   ```
   Browser: Chrome 121.0.6167.85
   Extension: v6.4.1
   YouTube: Logged in / Guest
   Video URL: https://youtube.com/watch?v=...
   Error message: [full error text]
   Console errors: [F12 console output]
   ```

2. **Open GitHub issue:**
   https://github.com/martinmarkovic/n8nsummarizer/issues

3. **Include:**
   - Browser and extension version
   - Full error message
   - Console output (F12 → Console)
   - Steps you tried

---

## 📚 Additional Resources

- **Extension README:** `README.md`
- **Installation Guide:** `INSTALLATION.md`
- **Manual PO Token Guide:** `../YOUTUBE_PO_TOKEN_GUIDE.md`
- **Main App README:** `../../README.md`

---

## 🔄 Version History

**v6.4.1** (2026-02-15)
- Added 5 extraction methods (not just cookies)
- Page context injection for direct access
- Much more reliable extraction
- Better error messages

**v6.4.0** (2026-02-15)
- Initial release
- Cookie-only extraction
- Basic error handling

---

**Last Updated:** 2026-02-15  
**Extension Version:** 1.0.1
