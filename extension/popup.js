let mp3Blob = null;
let mp3Filename = "audio.mp3";

// --- Tab switching ---
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById("panel-" + tab.dataset.tab).classList.add("active");
    hideAll();
  });
});

// --- Auto-populate current tab URL ---
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs[0]?.url) {
    document.getElementById("url-input").value = tabs[0].url;
  }
});

// --- Status updates from offscreen ---
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === "status") {
    showStatus(msg.detail || msg.stage);
  }
});

// --- Convert from URL ---
document.getElementById("btn-url").addEventListener("click", async () => {
  hideAll();
  const btn = document.getElementById("btn-url");

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) return showError("No active tab found");

  setLoading(btn, true);
  showStatus("Extracting content from page...");

  try {
    const extractResp = await sendMessage({ type: "extract", tabId: tab.id });
    if (!extractResp.ok) throw new Error(extractResp.error);

    const rawText = extractResp.text;
    if (!rawText?.trim()) throw new Error("Could not extract content from this page");

    showStatus("Processing...");
    const convertResp = await sendMessage({
      type: "convert",
      data: { rawText, url: tab.url }
    });
    if (!convertResp.ok) throw new Error(convertResp.error);

    showResult(convertResp.result);
  } catch (e) {
    showError(e.message);
  } finally {
    setLoading(btn, false);
  }
});

// --- Convert from manual paste ---
document.getElementById("btn-manual").addEventListener("click", async () => {
  hideAll();
  const btn = document.getElementById("btn-manual");
  const text = document.getElementById("text-input").value.trim();
  const slug = document.getElementById("slug-input").value.trim();

  if (!text) return showError("Please paste your blog content");
  if (!slug) return showError("Please enter a filename slug");

  setLoading(btn, true);
  showStatus("Processing...");

  try {
    const resp = await sendMessage({
      type: "convert",
      data: { rawText: text, slug }
    });
    if (!resp.ok) throw new Error(resp.error);
    showResult(resp.result);
  } catch (e) {
    showError(e.message);
  } finally {
    setLoading(btn, false);
  }
});

// --- Download ---
document.getElementById("btn-download").addEventListener("click", () => {
  if (!mp3Blob) return;
  const url = URL.createObjectURL(mp3Blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = mp3Filename;
  a.click();
  URL.revokeObjectURL(url);
});

// --- Helpers ---

function sendMessage(msg) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(msg, (resp) => {
      if (chrome.runtime.lastError) {
        resolve({ ok: false, error: chrome.runtime.lastError.message });
      } else {
        resolve(resp || { ok: false, error: "No response" });
      }
    });
  });
}

function setLoading(btn, loading) {
  btn.disabled = loading;
  if (loading) {
    btn.dataset.origText = btn.textContent;
    btn.innerHTML = '<span class="spinner"></span>Converting...';
  } else {
    btn.textContent = btn.dataset.origText || btn.textContent;
  }
}

function showStatus(text) {
  const el = document.getElementById("status");
  document.getElementById("status-text").textContent = text;
  el.classList.add("show");
}

function showError(msg) {
  document.getElementById("status").classList.remove("show");
  const el = document.getElementById("error");
  el.textContent = msg;
  el.classList.add("show");
  document.getElementById("result").classList.remove("show");
}

function showResult(data) {
  document.getElementById("status").classList.remove("show");
  document.getElementById("error").classList.remove("show");

  document.getElementById("r-source").textContent = data.inputSource || "Current page";
  document.getElementById("r-wc").textContent = data.wordCountCleaned;
  document.getElementById("r-condensed").textContent = data.condensed ? "Yes" : "No";
  document.getElementById("r-duration").textContent = data.estimatedDuration;

  // Convert base64 to blob
  const binary = atob(data.mp3Base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  mp3Blob = new Blob([bytes], { type: "audio/mpeg" });
  mp3Filename = data.filename;

  document.getElementById("result").classList.add("show");
}

function hideAll() {
  document.getElementById("status").classList.remove("show");
  document.getElementById("error").classList.remove("show");
  document.getElementById("result").classList.remove("show");
}
