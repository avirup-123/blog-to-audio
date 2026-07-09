const API = 'https://text-to-audio-online.vercel.app';
const SUPABASE_URL = 'https://pkaeridjackeiggllsxs.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBrYWVyaWRqYWNrZWlnZ2xsc3hzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3NzEwMTQsImV4cCI6MjA5NzM0NzAxNH0.P2xHr2wUcdDUfb8bErspbC9K2O5li4eWEq15XHnzXFE';

const CIRCUMFERENCE = 2 * Math.PI * 26;
let progressTimer = null;

function showSignedOutState() {
  document.getElementById('signinScreen').style.display = 'block';
  document.getElementById('appContent').style.display = 'none';
}

function showSignedInState(email) {
  document.getElementById('signinScreen').style.display = 'none';
  document.getElementById('appContent').style.display = 'block';
  document.getElementById('userEmail').textContent = email;
}

function getStoredSession() {
  return new Promise((resolve) => {
    chrome.storage.local.get('authSession', (result) => resolve(result.authSession || null));
  });
}

async function getValidAccessToken() {
  const session = await getStoredSession();
  if (!session) return null;
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (session.expires_at && session.expires_at > nowSeconds + 60) {
    return session.access_token;
  }
  try {
    const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': SUPABASE_ANON_KEY },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    });
    if (!res.ok) throw new Error('refresh failed');
    const refreshed = await res.json();
    const newSession = {
      access_token: refreshed.access_token,
      refresh_token: refreshed.refresh_token,
      expires_at: nowSeconds + refreshed.expires_in,
      email: session.email,
    };
    await new Promise((resolve) => chrome.storage.local.set({ authSession: newSession }, resolve));
    return newSession.access_token;
  } catch (e) {
    await new Promise((resolve) => chrome.storage.local.remove('authSession', resolve));
    return null;
  }
}

window.addEventListener('unhandledrejection', (e) => {
  if (e.reason && String(e.reason).includes('ort-wasm')) e.preventDefault();
}, true);
window.addEventListener('error', (e) => {
  if (e.message && e.message.includes('ort-wasm')) { e.preventDefault(); return false; }
}, true);

window.addEventListener('DOMContentLoaded', async () => {
  const session = await getStoredSession();
  if (session) {
    showSignedInState(session.email);
  } else {
    showSignedOutState();
  }

  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0] && tabs[0].url && tabs[0].url.startsWith('http')) {
      document.getElementById('blogUrl').value = tabs[0].url;
    }
  });
});

document.getElementById('btnSignIn').addEventListener('click', () => {
  chrome.tabs.create({ url: `${API}/?ext_signin=1` });
});

document.getElementById('btnSignOut').addEventListener('click', () => {
  chrome.storage.local.remove('authSession', showSignedOutState);
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.authSession && changes.authSession.newValue) {
    showSignedInState(changes.authSession.newValue.email);
  }
});

document.getElementById('tabUrl').addEventListener('click', () => switchTab('url'));
document.getElementById('tabText').addEventListener('click', () => switchTab('text'));

document.getElementById('btnUrl').addEventListener('click', convertUrl);
document.getElementById('btnText').addEventListener('click', convertText);

document.getElementById('btnNewUrl').addEventListener('click', () => resetPanel('Url'));
document.getElementById('btnNewText').addEventListener('click', () => resetPanel('Text'));

document.getElementById('pasteText').addEventListener('input', () => {
  document.getElementById('charCount').textContent = document.getElementById('pasteText').value.length;
});

function switchTab(tab) {
  document.getElementById('tabUrl').classList.toggle('active', tab === 'url');
  document.getElementById('tabText').classList.toggle('active', tab === 'text');
  document.getElementById('tab-url').classList.toggle('active', tab === 'url');
  document.getElementById('tab-text').classList.toggle('active', tab === 'text');
}

function lerpColor(pct) {
  const r = Math.round(129 + (74 - 129) * pct);
  const g = Math.round(140 + (222 - 140) * pct);
  const b = Math.round(248 + (128 - 248) * pct);
  return `rgb(${r},${g},${b})`;
}

function startProgress(suffix) {
  const ring = document.getElementById(`ring${suffix}`);
  const pctEl = document.getElementById(`pct${suffix}`);
  let progress = 0;
  ring.style.strokeDasharray = CIRCUMFERENCE;
  ring.style.strokeDashoffset = CIRCUMFERENCE;
  ring.style.stroke = lerpColor(0);
  pctEl.style.color = lerpColor(0);
  pctEl.textContent = '0%';

  if (progressTimer) clearInterval(progressTimer);
  progressTimer = setInterval(() => {
    if (progress < 60) {
      progress += 2;
    } else if (progress < 85) {
      progress += 0.5;
    } else if (progress < 95) {
      progress += 0.15;
    }
    progress = Math.min(progress, 95);
    const offset = CIRCUMFERENCE - (progress / 100) * CIRCUMFERENCE;
    ring.style.strokeDashoffset = offset;
    const color = lerpColor(progress / 100);
    ring.style.stroke = color;
    pctEl.style.color = color;
    pctEl.textContent = Math.round(progress) + '%';
  }, 200);
}

function completeProgress(suffix) {
  if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
  const ring = document.getElementById(`ring${suffix}`);
  const pctEl = document.getElementById(`pct${suffix}`);
  ring.style.strokeDashoffset = 0;
  ring.style.stroke = lerpColor(1);
  pctEl.style.color = lerpColor(1);
  pctEl.textContent = '100%';
}

function stopProgress(suffix) {
  if (progressTimer) { clearInterval(progressTimer); progressTimer = null; }
}

function resetPanel(suffix) {
  document.getElementById(`inputArea${suffix}`).classList.remove('hidden');
  document.getElementById(`result${suffix}`).classList.remove('show');
  hideError(`error${suffix}`);
}

async function convertUrl() {
  const url = document.getElementById('blogUrl').value.trim();
  if (!url) { showError('errorUrl', 'Please enter a URL'); return; }

  document.getElementById('inputAreaUrl').classList.add('hidden');
  document.getElementById('loaderUrl').classList.add('show');
  hideError('errorUrl');
  document.getElementById('resultUrl').classList.remove('show');
  startProgress('Url');

  try {
    const voice = document.getElementById('voiceSelect').value;
    await doConvert({ input_type: 'url', url, voice, lang: 'en' }, 'Url');
    completeProgress('Url');
    setTimeout(() => document.getElementById('loaderUrl').classList.remove('show'), 500);
  } catch (err) {
    stopProgress('Url');
    document.getElementById('loaderUrl').classList.remove('show');
    document.getElementById('inputAreaUrl').classList.remove('hidden');
    if (!String(err).includes('ort-wasm')) showError('errorUrl', err.message);
  }
}

async function convertText() {
  const text = document.getElementById('pasteText').value.trim();
  if (!text) { showError('errorText', 'Please paste some text'); return; }
  if (text.length > 5000) { showError('errorText', 'Max 5000 characters'); return; }

  document.getElementById('inputAreaText').classList.add('hidden');
  document.getElementById('loaderText').classList.add('show');
  hideError('errorText');
  document.getElementById('resultText').classList.remove('show');
  startProgress('Text');

  try {
    const slug = 'extension-' + Date.now();
    const voice = document.getElementById('voiceSelect').value;
    await doConvert({ input_type: 'manual', text, slug, voice, lang: 'en' }, 'Text');
    completeProgress('Text');
    setTimeout(() => document.getElementById('loaderText').classList.remove('show'), 500);
  } catch (err) {
    stopProgress('Text');
    document.getElementById('loaderText').classList.remove('show');
    document.getElementById('inputAreaText').classList.remove('hidden');
    if (!String(err).includes('ort-wasm')) showError('errorText', err.message);
  }
}

async function doConvert(body, suffix) {
  const token = await getValidAccessToken();
  if (!token) {
    showSignedOutState();
    throw new Error('Please sign in again');
  }

  const res = await fetch(`${API}/convert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
    body: JSON.stringify(body),
  });

  if (res.status === 401) {
    showSignedOutState();
    throw new Error('Please sign in again');
  }

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || 'Conversion failed');
  }

  const byteChars = atob(data.audio_base64);
  const byteNumbers = new Array(byteChars.length);
  for (let i = 0; i < byteChars.length; i++) byteNumbers[i] = byteChars.charCodeAt(i);
  const blob = new Blob([new Uint8Array(byteNumbers)], { type: 'audio/mpeg' });
  const audioUrl = URL.createObjectURL(blob);

  document.getElementById(`audio${suffix}`).src = audioUrl;
  const dl = document.getElementById(`dl${suffix}`);
  dl.href = audioUrl;
  dl.download = data.filename || 'audio.mp3';
  document.getElementById(`result${suffix}`).classList.add('show');
}

function showError(id, msg) { const el = document.getElementById(id); el.textContent = msg; el.classList.add('show'); }
function hideError(id) { document.getElementById(id).classList.remove('show'); }
