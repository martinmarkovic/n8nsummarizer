// PO Token Extractor - Popup Script

const extractBtn = document.getElementById('extractBtn');
const statusDiv = document.getElementById('status');
const tokenDisplay = document.getElementById('tokenDisplay');

// Extract PO Token when button clicked
extractBtn.addEventListener('click', async () => {
  try {
    // Update UI state
    extractBtn.disabled = true;
    extractBtn.textContent = 'Extracting...';
    statusDiv.className = 'info';
    statusDiv.textContent = 'Checking YouTube cookies...';
    tokenDisplay.classList.remove('show');
    
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Check if on YouTube
    if (!tab.url.includes('youtube.com')) {
      throw new Error('Please open a YouTube page first');
    }
    
    // Get cookies from YouTube
    const cookies = await chrome.cookies.getAll({ domain: '.youtube.com' });
    
    // Find VISITOR_INFO1_LIVE cookie (contains PO token data)
    const visitorCookie = cookies.find(c => c.name === 'VISITOR_INFO1_LIVE');
    
    if (!visitorCookie) {
      throw new Error('VISITOR_INFO1_LIVE cookie not found. Try refreshing YouTube.');
    }
    
    // The PO token is derived from the cookie value
    // In production yt-dlp usage, you'd use: web+{cookie_value}
    const poToken = `web+${visitorCookie.value}`;
    
    // Copy to clipboard
    await navigator.clipboard.writeText(poToken);
    
    // Show success
    statusDiv.className = 'success';
    statusDiv.textContent = '✅ PO Token copied to clipboard! Paste it in n8n Summarizer.';
    
    // Show token (first 50 chars for verification)
    tokenDisplay.textContent = `Token: ${poToken.substring(0, 50)}...`;
    tokenDisplay.classList.add('show');
    
    // Log success
    console.log('PO Token extracted successfully');
    
    // Send to background script for storage (optional)
    chrome.runtime.sendMessage({
      action: 'storeToken',
      token: poToken
    });
    
  } catch (error) {
    // Show error
    statusDiv.className = 'error';
    statusDiv.textContent = `❌ Error: ${error.message}`;
    console.error('Extraction error:', error);
  } finally {
    // Reset button
    extractBtn.disabled = false;
    extractBtn.textContent = 'Extract PO Token';
  }
});

// Auto-load saved token on popup open (optional)
chrome.storage.local.get(['lastToken', 'tokenTimestamp'], (result) => {
  if (result.lastToken) {
    const age = Date.now() - (result.tokenTimestamp || 0);
    const daysOld = Math.floor(age / (1000 * 60 * 60 * 24));
    
    if (daysOld < 7) {
      tokenDisplay.textContent = `Last extracted: ${daysOld} day(s) ago\n${result.lastToken.substring(0, 50)}...`;
      tokenDisplay.classList.add('show');
    }
  }
});