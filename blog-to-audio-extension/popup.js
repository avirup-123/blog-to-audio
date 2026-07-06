const API = 'https://text-to-audio-online.vercel.app';

// Permanently suppress ort-wasm errors from other extensions injecting into this popup
window.addEventListener('unhandledrejection', (e) => {
  if (e.reason && String(e.reason).includes('ort-wasm')) e.preventDefault();
}, true);
window.addEventListener('error', (e) => {
  if (e.message && e.message.includes('ort-wasm')) { e.preventDefault(); return false; }
}, true);

// Auto-fill current tab URL
window.addEventListener('DOMContentLoaded', () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0] && tabs[0].url && tabs[0].url.startsWith('http')) {
      document.getElementById('blogUrl').value = tabs[0].url;
    }
  });
});

// Tab switching
document.getElementById('tabUrl').addEventListener('click', () => switchTab('url'));
document.getElementById('tabText').addEventListener('click', () => switchTab('text'));

// Convert buttons
document.getElementById('btnUrl').addEventListener('click', convertUrl);
document.getElementById('btnText').addEventListener('click', convertText);

// Feedback
document.getElementById('btnFeedback').addEventListener('click', sendFeedback);

// Char counter
document.getElementById('pasteText').addEventListener('input', () => {
  document.getElementById('charCount').textContent = document.getElementById('pasteText').value.length;
});

function switchTab(tab) {
  document.getElementById('tabUrl').classList.toggle('active', tab === 'url');
  document.getElementById('tabText').classList.toggle('active', tab === 'text');
  document.getElementById('tab-url').classList.toggle('active', tab === 'url');
  document.getElementById('tab-text').classList.toggle('active', tab === 'text');
}

async function convertUrl() {
  const url = document.getElementById('blogUrl').value.trim();
  if (!url) { showError('errorUrl', 'Please enter a URL'); return; }

  setLoading('Url', true);
  hideError('errorUrl');
  document.getElementById('resultUrl').classList.remove('show');

  try {
    const fetchRes = await fetch(`${API}/api/fetch-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });
    const fetchData = await fetchRes.json();
    if (!fetchRes.ok) throw new Error(fetchData.error || 'Failed to fetch URL');
    await doConvert(fetchData.text, 'Url');
  } catch (err) {
    if (!String(err).includes('ort-wasm')) showError('errorUrl', err.message);
    setLoading('Url', false);
  }
}

async function convertText() {
  const text = document.getElementById('pasteText').value.trim();
  if (!text) { showError('errorText', 'Please paste some text'); return; }
  if (text.length > 5000) { showError('errorText', 'Max 5000 characters'); return; }

  setLoading('Text', true);
  hideError('errorText');
  document.getElementById('resultText').classList.remove('show');

  try {
    await doConvert(text, 'Text');
  } catch (err) {
    if (!String(err).includes('ort-wasm')) showError('errorText', err.message);
    setLoading('Text', false);
  }
}

async function doConvert(text, suffix) {
  const res = await fetch(`${API}/api/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, language: 'en' })
  });

  if (!res.ok) {
    const d = await res.json();
    throw new Error(d.error || 'Conversion failed');
  }

  const blob = await res.blob();
  const dataUrl = await new Promise((resolve) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.readAsDataURL(blob);
  });

  document.getElementById(`audio${suffix}`).src = dataUrl;
  const dl = document.getElementById(`dl${suffix}`);
  dl.href = dataUrl;
  dl.download = 'audio.mp3';
  document.getElementById(`result${suffix}`).classList.add('show');
  setLoading(suffix, false);
}

async function sendFeedback() {
  const message = document.getElementById('feedbackText').value.trim();
  if (!message) return;
  const btn = document.getElementById('btnFeedback');
  btn.disabled = true;
  btn.textContent = 'Sending...';
  try {
    await fetch(`${API}/api/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    document.getElementById('feedbackText').value = '';
    document.getElementById('feedbackOk').classList.add('show');
    setTimeout(() => document.getElementById('feedbackOk').classList.remove('show'), 3000);
  } catch (e) { }
  finally { btn.disabled = false; btn.textContent = 'Send Feedback'; }
}

function setLoading(suffix, loading) {
  document.getElementById(`loader${suffix}`).classList.toggle('show', loading);
  document.getElementById(`btn${suffix}`).disabled = loading;
}
function showError(id, msg) { const el = document.getElementById(id); el.textContent = msg; el.classList.add('show'); }
function hideError(id) { document.getElementById(id).classList.remove('show'); }
