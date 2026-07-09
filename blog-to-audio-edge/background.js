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
  return true;
});
