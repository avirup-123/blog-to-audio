chrome.action.onClicked.addListener((tab) => {
  const url = (tab && tab.url && tab.url.startsWith('http')) ? tab.url : '';
  chrome.tabs.create({
    url: chrome.runtime.getURL('popup.html') + (url ? '?url=' + encodeURIComponent(url) : '')
  });
});

chrome.runtime.onMessageExternal.addListener((message, sender, sendResponse) => {
  if (!message || message.type !== 'AUTH_SESSION') return;
  chrome.storage.local.set({
    authSession: {
      access_token: message.access_token,
      refresh_token: message.refresh_token,
      expires_at: message.expires_at,
      email: message.email,
    },
  }, () => {
    sendResponse({ received: true });
  });
  return true; // keep the message channel open for the async sendResponse
});
