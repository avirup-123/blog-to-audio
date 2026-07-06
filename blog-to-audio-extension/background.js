chrome.action.onClicked.addListener((tab) => {
  const url = (tab && tab.url && tab.url.startsWith('http')) ? tab.url : '';
  chrome.tabs.create({
    url: chrome.runtime.getURL('popup.html') + (url ? '?url=' + encodeURIComponent(url) : '')
  });
});
