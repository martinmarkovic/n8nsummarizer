// PO Token Extractor - Popup Script (v6.4.1 - Page Context Injection)

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
    statusDiv.textContent = 'Analyzing YouTube page...';
    tokenDisplay.classList.remove('show');
    
    // Get current tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    
    // Check if on YouTube
    if (!tab.url.includes('youtube.com')) {
      throw new Error('Please open a YouTube page first');
    }
    
    statusDiv.textContent = 'Extracting visitor data...';
    
    // Inject content script to extract token from page
    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: extractTokenFromPage
    });
    
    const result = results[0].result;
    
    if (!result.success) {
      throw new Error(result.error || 'Failed to extract token from page');
    }
    
    const poToken = result.token;
    
    // Validate token format
    if (!poToken || poToken.length < 20) {
      throw new Error('Invalid token format. Token seems too short.');
    }
    
    // Copy to clipboard
    await navigator.clipboard.writeText(poToken);
    
    // Show success
    statusDiv.className = 'success';
    statusDiv.textContent = `✅ PO Token copied! Method: ${result.method}`;
    
    // Show token (first 50 chars for verification)
    const preview = poToken.length > 50 ? `${poToken.substring(0, 50)}...` : poToken;
    tokenDisplay.textContent = `Token: ${preview}`;
    tokenDisplay.classList.add('show');
    
    // Log success
    console.log('PO Token extracted successfully');
    console.log('Method:', result.method);
    console.log('Token length:', poToken.length);
    
    // Send to background script for storage
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

// Function injected into YouTube page (runs in page context)
function extractTokenFromPage() {
  try {
    // Method 1: Try to get from ytInitialPlayerResponse (most reliable)
    if (window.ytInitialPlayerResponse && 
        window.ytInitialPlayerResponse.responseContext && 
        window.ytInitialPlayerResponse.responseContext.serviceTrackingParams) {
      
      const trackingParams = window.ytInitialPlayerResponse.responseContext.serviceTrackingParams;
      
      // Look for visitor data in tracking params
      for (const param of trackingParams) {
        if (param.params) {
          for (const p of param.params) {
            if (p.key === 'visitor_data' && p.value) {
              return {
                success: true,
                token: p.value,
                method: 'ytInitialPlayerResponse'
              };
            }
          }
        }
      }
    }
    
    // Method 2: Try to get from ytcfg (YouTube config)
    if (window.ytcfg && typeof window.ytcfg.get === 'function') {
      const visitorData = window.ytcfg.get('VISITOR_DATA');
      if (visitorData) {
        return {
          success: true,
          token: visitorData,
          method: 'ytcfg.VISITOR_DATA'
        };
      }
      
      const innertube = window.ytcfg.get('INNERTUBE_CONTEXT');
      if (innertube && innertube.client && innertube.client.visitorData) {
        return {
          success: true,
          token: innertube.client.visitorData,
          method: 'INNERTUBE_CONTEXT'
        };
      }
    }
    
    // Method 3: Try to extract from page HTML (ytInitialData)
    if (window.ytInitialData) {
      const dataStr = JSON.stringify(window.ytInitialData);
      const visitorMatch = dataStr.match(/"visitorData":"([^"]+)"/);
      if (visitorMatch && visitorMatch[1]) {
        return {
          success: true,
          token: visitorMatch[1],
          method: 'ytInitialData'
        };
      }
    }
    
    // Method 4: Try cookies as fallback
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'VISITOR_INFO1_LIVE' && value) {
        return {
          success: true,
          token: `web+${value}`,
          method: 'cookie'
        };
      }
    }
    
    // Method 5: Extract from any script tags containing visitorData
    const scripts = document.querySelectorAll('script');
    for (const script of scripts) {
      if (script.textContent && script.textContent.includes('visitorData')) {
        const match = script.textContent.match(/["']visitorData["']\s*:\s*["']([^"']+)["']/);
        if (match && match[1]) {
          return {
            success: true,
            token: match[1],
            method: 'script_tag'
          };
        }
      }
    }
    
    // If all methods fail
    return {
      success: false,
      error: 'Could not find visitor data. Make sure you:\n1. Are on a YouTube video page\n2. Have played a video\n3. Are logged into YouTube (recommended)'
    };
    
  } catch (err) {
    return {
      success: false,
      error: `Extraction failed: ${err.message}`
    };
  }
}

// Auto-load saved token on popup open (optional)
chrome.storage.local.get(['lastToken', 'tokenTimestamp'], (result) => {
  if (result.lastToken) {
    const age = Date.now() - (result.tokenTimestamp || 0);
    const daysOld = Math.floor(age / (1000 * 60 * 60 * 24));
    
    if (daysOld < 7) {
      const preview = result.lastToken.length > 50 
        ? `${result.lastToken.substring(0, 50)}...` 
        : result.lastToken;
      tokenDisplay.textContent = `Last extracted: ${daysOld} day(s) ago\n${preview}`;
      tokenDisplay.classList.add('show');
    }
  }
});