# YouTube PO Token Guide for HD Quality Downloads

## Current Situation (February 2026)

YouTube now requires **PO (Proof of Origin) Tokens** for video qualities above 360p. Without a PO token:
- ✅ **360p works** - No token needed
- ❌ **720p, 1080p, 4K blocked** - Requires PO token

This affects ALL downloaders using yt-dlp, not just this application.

## Solution Options

### Option 1: Accept 360p (Easiest)

**No setup required.** Just download at 360p quality.

**Pros:**
- Works immediately
- No configuration
- Reliable

**Cons:**
- Lower quality

---

### Option 2: Semi-Automatic PO Token (Recommended)

**Extract token from browser once, use for several days.**

#### Steps:

1. **Open YouTube in Chrome/Firefox** (logged out or logged in)

2. **Open DevTools** (F12)

3. **Go to Network tab**

4. **Play any video**

5. **Find the `videoplayback` request** in Network tab

6. **Look for `pot=` parameter** in the URL
   - Example: `...&pot=aA1bB2cC3dD4...`
   - Copy the entire value after `pot=`

7. **Add to your `.env` file:**
   ```
   YOUTUBE_PO_TOKEN=web+aA1bB2cC3dD4...
   ```

**Token Lifetime:** Usually valid for **2-7 days**

**Pros:**
- Works for 720p+
- Only need to update every few days
- Simple browser-based extraction

**Cons:**
- Manual extraction required
- Token expires periodically

**Visual Guide:**
```
DevTools → Network → Filter: videoplayback
↓
Click on videoplayback request
↓
Headers tab → Request URL
↓
Find: &pot=XXXXXXXX&
↓
Copy XXXXXXXX value
```

---

### Option 3: Automatic PO Token Provider (Advanced)

**Run a service that generates tokens automatically.**

Uses **bgutil-ytdlp-pot-provider** - a tool that generates PO tokens on-demand.

#### Docker Setup (Easiest):

```bash
# Start the token provider service
docker run --name bgutil-provider -d -p 4416:4416 --init brainicism/bgutil-ytdlp-pot-provider
```

#### Python Plugin:

```bash
# Install the plugin
python3 -m pip install -U bgutil-ytdlp-pot-provider
```

The plugin will automatically fetch tokens from the Docker service.

**Requirements:**
- Docker installed OR Node.js >= 18
- yt-dlp >= 2024.09.27

**Pros:**
- Fully automatic
- Tokens generated on-demand
- No manual updates

**Cons:**
- Requires Docker/Node.js setup
- Additional service running
- More complex

**Resources:**
- GitHub: https://github.com/Brainicism/bgutil-ytdlp-pot-provider
- PyPI: https://pypi.org/project/bgutil-ytdlp-pot-provider/

---

### Option 4: Browser Cookie Extraction (Alternative)

**Use your logged-in YouTube session cookies.**

This was attempted but Windows 11 has DPAPI encryption issues with Chrome cookies.

**Status:** ❌ Not working reliably on Windows 11

**If you want to try:**
```bash
yt-dlp --cookies-from-browser chrome VIDEO_URL
```

**Known Issues:**
- DPAPI decryption fails on Windows 11
- Cookie extraction requires browser-specific handling
- Session cookies expire frequently

---

## Implementation Status in This App

### ✅ Already Implemented (v6.3):
- Settings persistence (remembers quality/path/tab)
- PO Token support via `.env` file
- Clear warnings about 360p limitation
- Android client fallback (works for 360p)

### 🔄 To Implement:
- PO token field in Downloader UI (for Option 2)
- Optional: bgutil integration (for Option 3)

### 📝 Current Workaround:

**Manual .env editing:**
1. Extract token using Option 2 steps above
2. Open `.env` file in project root
3. Add line: `YOUTUBE_PO_TOKEN=web+YOUR_TOKEN_HERE`
4. Save and restart app
5. Downloads will now use the token for HD quality

---

## Testing Your Token

To verify your PO token works:

```bash
yt-dlp --extractor-args "youtube:po_token=web+YOUR_TOKEN" -f best[height<=720] VIDEO_URL
```

If successful, you should see:
- No "PO Token required" warnings
- Format selection includes 720p options
- Download proceeds at requested quality

---

## Troubleshooting

### "PO Token required" warning still appears
- Token may be expired - extract a new one
- Token format must be: `web+TOKEN_VALUE` (include the `web+` prefix)
- Check `.env` file syntax (no spaces around `=`)

### Token expires quickly
- Logged-out tokens last longer than logged-in
- Consider Option 3 (automatic provider) for frequent use

### Downloads still 360p with token
- Verify token is actually loaded (check logs)
- Token must match the client type (use `web+` prefix)
- Try extracting a fresh token

---

## Recommended Approach

**For casual use:**
→ **Option 2** (Semi-automatic browser extraction)
- Extract token every few days
- Add to `.env` file
- Restart app

**For heavy use:**
→ **Option 3** (Automatic provider service)
- One-time Docker setup
- Never worry about tokens again

**For minimal hassle:**
→ **Option 1** (Accept 360p)
- Just works, no configuration

---

## Additional Resources

- **Official yt-dlp PO Token Guide:** https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide
- **bgutil Provider:** https://github.com/Brainicism/bgutil-ytdlp-pot-provider
- **YouTube Extractor Wiki:** https://github.com/yt-dlp/yt-dlp/wiki/Extractors

---

## Future Improvements

Potential enhancements for this app:
1. **UI for token input** - Add field in Downloader tab
2. **Token validation** - Test token before using
3. **Expiry detection** - Warn when token needs refresh
4. **bgutil integration** - Built-in automatic provider
5. **Token extraction helper** - Browser automation to grab token

---

*Last updated: 2026-02-15*
*Status: 360p works, HD requires PO token*
