# PO Token Quick Start Guide

**Enable HD YouTube downloads (720p, 1080p, 4K) in 2 minutes**

---

## ⚡ Quick Method (Browser Extension - Recommended)

### **Step 1: Install Extension** (One-time setup)

```bash
cd n8nsummarizer
git pull origin v6.4
```

1. Open Chrome/Edge
2. Go to `chrome://extensions/`
3. Enable "Developer mode" (top right)
4. Click "Load unpacked"
5. Select: `n8nsummarizer/docs/browser_extension/`
6. Extension installed! ✓

### **Step 2: Extract Token** (Every 7-30 days)

1. **Open any YouTube video** in your browser
2. **Play video** for 5 seconds
3. **Click extension icon** (YouTube logo)
4. **Click "Extract PO Token"**
5. **Token copied to clipboard!** ✅

### **Step 3: Use in Downloader**

1. Open n8n Summarizer app
2. Go to **Downloader** tab
3. **Paste token** in "PO Token" field
4. **Select HD quality** (720p, 1080p, 4K)
5. **Download!** 🎉

**Status indicator:**
- ✅ Green checkmark = Valid token, HD enabled
- ❌ Red X = Invalid/missing token, 360p only

---

## 💻 Manual Method (DevTools)

**If extension doesn't work:**

1. **Open YouTube video** and play it
2. **Press F12** (open DevTools)
3. **Click Console tab**
4. **Paste and run:**

```javascript
(function() {
  if (window.ytcfg && window.ytcfg.get) {
    const token = window.ytcfg.get('VISITOR_DATA');
    if (token) {
      console.log('✅ Token found:', token);
      navigator.clipboard.writeText(token);
      console.log('📋 Copied to clipboard!');
      return token;
    }
  }
  console.error('❌ Token not found. Play video and try again.');
})();
```

5. **Token copied!** Paste in Downloader tab

---

## ❓ FAQ

### **How long is token valid?**
7-30 days typically. Extract new token if downloads fail.

### **Do I need to be logged into YouTube?**
No, but logged-in tokens may last longer.

### **What if token doesn't work?**
1. Extract fresh token
2. Try different video
3. Clear browser cache
4. See troubleshooting guide

### **Can I use same token for multiple videos?**
Yes! One token works for all downloads until it expires.

### **What quality can I download?**
With PO Token:
- ✅ 4K (2160p)
- ✅ 2K (1440p)  
- ✅ 1080p Full HD
- ✅ 720p HD
- ✅ 480p
- ✅ 360p
- ✅ Audio only (MP3)

Without PO Token:
- ❌ Limited to 360p maximum

---

## 🔧 Troubleshooting

### **Extension says "VISITOR_INFO1_LIVE cookie not found"**

**Update to v6.4.1+:**
```bash
cd n8nsummarizer
git pull origin v6.4
```

Then reload extension:
1. Go to `chrome://extensions/`
2. Find "YouTube PO Token Extractor"
3. Click reload button (🔄)

**v6.4.1 uses 5 extraction methods**, much more reliable.

### **Download fails with "Sign in to confirm you're not a bot"**

1. Extract fresh PO token
2. Make sure token was pasted correctly
3. Try token from different browser/video

### **Extension not working at all**

Use manual DevTools method above, or see:
- `docs/browser_extension/TROUBLESHOOTING.md`
- `docs/YOUTUBE_PO_TOKEN_GUIDE.md`

---

## 📚 Full Documentation

**Browser Extension:**
- Installation: `docs/browser_extension/INSTALLATION.md`
- Troubleshooting: `docs/browser_extension/TROUBLESHOOTING.md`
- README: `docs/browser_extension/README.md`

**Manual Methods:**
- Complete guide: `docs/YOUTUBE_PO_TOKEN_GUIDE.md`
- Python script method
- yt-dlp command line
- Cookie extraction

**Application:**
- Main README: `README.md`
- Setup guide: `docs/SETUP.md`

---

## ✅ Success Checklist

**You know it's working when:**

- [ ] Extension shows "✅ PO Token copied!"
- [ ] Downloader shows green checkmark next to token field
- [ ] HD quality options available (720p, 1080p, 4K)
- [ ] Download completes with "Download completed successfully at [quality]"
- [ ] Video file size is appropriate for quality:
  - 1080p: ~100-300 MB per 10 min
  - 720p: ~50-150 MB per 10 min  
  - 360p: ~20-50 MB per 10 min

---

## 👨‍💻 Technical Details

**What is PO Token?**
YouTube's `visitor_data` value used to verify legitimate client.

**Where does extension get it?**
5 extraction methods:
1. `ytInitialPlayerResponse` - Player data
2. `ytcfg.VISITOR_DATA` - Config object
3. `INNERTUBE_CONTEXT` - API context
4. `ytInitialData` - Page data
5. Cookies - Fallback

**How is it used?**
Passed to yt-dlp as `po_token` extractor argument:
```python
'extractor_args': {
    'youtube': {
        'po_token': ['web+<your_token>']
    }
}
```

**Format:**
- Raw token from YouTube: `CgtlWkJwN0x2SFFoUSiMn...`
- In yt-dlp: `web+CgtlWkJwN0x2SFFoUSiMn...`
- App handles prefix automatically

---

**Last Updated:** 2026-02-15  
**Version:** 6.4.2

**Need help?** See `TROUBLESHOOTING.md` or open GitHub issue.
