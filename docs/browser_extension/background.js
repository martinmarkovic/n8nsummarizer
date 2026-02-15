// PO Token Extractor - Background Service Worker

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'storeToken') {
    // Store token with timestamp
    chrome.storage.local.set({
      lastToken: request.token,
      tokenTimestamp: Date.now()
    }, () => {
      console.log('PO Token stored successfully');
      sendResponse({ success: true });
    });
    return true; // Required for async response
  }
});

// Optional: Monitor cookie changes
chrome.cookies.onChanged.addListener((changeInfo) => {
  if (changeInfo.cookie.name === 'VISITOR_INFO1_LIVE' && changeInfo.cookie.domain === '.youtube.com') {
    console.log('YouTube visitor cookie updated');
  }
});

// Extension installed/updated
chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') {
    console.log('PO Token Extractor installed');
    
    // Open welcome page (optional)
    // chrome.tabs.create({ url: 'https://github.com/martinmarkovic/n8nsummarizer' });
  } else if (details.reason === 'update') {
    console.log('PO Token Extractor updated to version', chrome.runtime.getManifest().version);
  }
});