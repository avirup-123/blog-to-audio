let offscreenReady = false;

async function ensureOffscreen() {
  if (offscreenReady) return;
  const contexts = await chrome.runtime.getContexts({
    contextTypes: ["OFFSCREEN_DOCUMENT"],
  });
  if (contexts.length === 0) {
    await chrome.offscreen.createDocument({
      url: "offscreen.html",
      reasons: ["WORKERS"],
      justification: "Run Piper TTS WASM for audio generation",
    });
  }
  offscreenReady = true;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "extract") {
    extractContent(msg.tabId).then(
      text => sendResponse({ ok: true, text }),
      err => sendResponse({ ok: false, error: err.message })
    );
    return true;
  }

  if (msg.type === "convert") {
    runConversion(msg.data).then(
      result => sendResponse({ ok: true, result }),
      err => sendResponse({ ok: false, error: err.message })
    );
    return true;
  }

  if (msg.type === "status") {
    // Forward status from offscreen to popup
    chrome.runtime.sendMessage(msg).catch(() => {});
  }
});

async function extractContent(tabId) {
  const results = await chrome.scripting.executeScript({
    target: { tabId },
    files: ["content.js"],
  });
  return results?.[0]?.result || "";
}

async function runConversion(data) {
  await ensureOffscreen();

  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      { type: "process", data },
      (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else if (response?.ok) {
          resolve(response.result);
        } else {
          reject(new Error(response?.error || "Unknown error"));
        }
      }
    );
  });
}
