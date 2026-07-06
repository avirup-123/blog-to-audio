# Chrome Extension Auth & Free-Tier Quota Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `blog-to-audio-extension` Chrome extension actually convert audio again by requiring Google sign-in (reusing the website's Supabase session), enforce a combined 10-conversions/day free-tier limit across website + extension, and show a plain limit message when it's hit.

**Architecture:** The extension gets a stable ID (via a pinned manifest key) so the website can message it directly after Google sign-in via `chrome.runtime.sendMessage`. The extension's background script stores the session in `chrome.storage.local`; the popup reads it, refreshes the token when needed, and calls the existing `/convert` endpoint with the correct payload shape. The backend adds a quota check to `/convert` using the existing `conversions` table — no new tables.

**Tech Stack:** Flask (`api/index.py`), Supabase (Postgres + Auth + `supabase-py`), Chrome Extension Manifest V3 (vanilla JS, no build step), Supabase JS SDK (website only, via CDN).

## Global Constraints

- Daily quota: 10 conversions per user per UTC calendar day, combined across website and extension (from spec section 2).
- Limit message text, verbatim: `You've used all 10 free conversions today.` (from spec section 3 — plain text, no button, no link).
- No payment/upsell button or form of any kind in this pass (explicitly out of scope per spec).
- No automated test suite exists in this project (confirmed: no `tests/` directory, no test framework in `requirements.txt`). All verification in this plan is manual (curl commands with expected output, or manual browser/extension steps), per the spec's "Testing approach" section.
- The extension's private signing key (`extension-key.pem`) must never be committed to git.

---

## File Map

| File | Change |
|---|---|
| `blog-to-audio-extension/manifest.json` | Modify — add stable `key`, `storage` permission, Supabase host permission, `externally_connectable` |
| `.gitignore` | Modify — ignore the new private key file |
| `api/index.py` | Modify — add quota check in `/convert` (backend), add extension-messaging JS (website) |
| `blog-to-audio-extension/background.js` | Modify — add listener that stores the session pushed from the website |
| `blog-to-audio-extension/popup.html` | Modify — add sign-in screen markup, remove broken feedback section |
| `blog-to-audio-extension/popup.js` | Modify — auth-state handling, token refresh, fixed `/convert` call |

---

### Task 1: Pin the extension's ID and configure its manifest permissions

**Files:**
- Modify: `blog-to-audio-extension/manifest.json`
- Create: `blog-to-audio-extension/extension-key.pem` (never committed)
- Modify: `.gitignore`

**Interfaces:**
- Produces: a stable Chrome extension ID (a 32-character string Chrome derives from the public key), which Task 5 (website) needs as a literal constant.

- [ ] **Step 1: Generate a private key for the extension**

Run from the repo root:

```bash
openssl genrsa -out blog-to-audio-extension/extension-key.pem 2048
```

Expected: a file `blog-to-audio-extension/extension-key.pem` is created (starts with `-----BEGIN PRIVATE KEY-----`).

- [ ] **Step 2: Ignore the private key in git**

Read `.gitignore` (currently contains `.vercel`, `.env`, `__pycache__/`) and add a new line:

```
blog-to-audio-extension/extension-key.pem
```

- [ ] **Step 3: Derive the base64 public key and add it to manifest.json**

Run:

```bash
openssl rsa -in blog-to-audio-extension/extension-key.pem -pubout -outform DER 2>/dev/null | openssl base64 -A
```

Expected: prints one long base64 string with no line breaks.

Open `blog-to-audio-extension/manifest.json` and add a `"key"` field with that string as the value, right after `"manifest_version"`:

```json
{
  "manifest_version": 3,
  "key": "PASTE_THE_BASE64_STRING_FROM_STEP_3_HERE",
  "name": "Text to Audio Online",
  "version": "1.0",
  "description": "Convert any blog or article into audio instantly. Paste a URL or text and get an MP3 in seconds.",
  "permissions": ["activeTab", "tabs", "storage"],
  "host_permissions": [
    "https://text-to-audio-online.vercel.app/*",
    "https://pkaeridjackeiggllsxs.supabase.co/*"
  ],
  "externally_connectable": {
    "matches": ["https://text-to-audio-online.vercel.app/*"]
  },
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "icons": {
    "16": "icons/icon16.png",
    "48": "icons/icon48.png",
    "128": "icons/icon128.png"
  }
}
```

(`storage` permission is new — needed for `chrome.storage.local`. `host_permissions` gains the Supabase project URL, needed for the token-refresh call in Task 4. `externally_connectable` is new — this is what lets the website message the extension.)

- [ ] **Step 4: Load the extension and record its stable ID**

1. Open Chrome, go to `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. If "Text to Audio Online" is already loaded, click **Remove** first
4. Click **Load unpacked**, select the `blog-to-audio-extension` folder
5. Chrome shows an **ID** field under the extension's name (a 32-lowercase-letter string) — copy it exactly. This value is needed verbatim in Task 5.

- [ ] **Step 5: Verify the ID is stable across reloads**

1. Click the reload icon (circular arrow) on the extension's card in `chrome://extensions`
2. Confirm the **ID** shown is identical to Step 4's value
3. Click **Remove**, then **Load unpacked** again (same folder)
4. Confirm the ID is still identical — this proves the `"key"` field pins it

- [ ] **Step 6: Commit**

```bash
git add blog-to-audio-extension/manifest.json .gitignore
git commit -m "Pin extension ID and add storage/messaging permissions"
```

---

### Task 2: Enforce the daily conversion quota in the backend

**Files:**
- Modify: `api/index.py:1001-1017` (the start of the `/convert` route)

**Interfaces:**
- Consumes: `_verify_supabase_token()` (existing, `api/index.py:372`), `_load_supabase()` (existing, `api/index.py:34`)
- Produces: on `429`, JSON body `{"error": "You've used all 10 free conversions today.", "daily_limit_reached": true, "used": <int>, "limit": 10}`. On success, the existing response gains two new keys: `"conversions_used_today"` (int) and `"daily_limit"` (10). Both the website's existing `showError(data.error || ...)` pattern (`api/index.py:938`) and the extension's error handling (Task 6) already display whatever string is in `data.error` — no special-casing needed for the message to show up.

- [ ] **Step 1: Read the current route start**

Confirm the current code at `api/index.py:1001-1017` reads:

```python
@app.route("/convert", methods=["POST"])
def convert():
    user_id = _verify_supabase_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"error": "Please sign in again"}), 401

    data = request.get_json()
    input_type = data.get("input_type")
    url = data.get("url", "").strip()
    text = data.get("text", "").strip()
    slug = data.get("slug", "").strip()
    voice = data.get("voice", "en-US-JennyNeural")
    lang = data.get("lang", "en")

    if voice not in ALL_VOICES:
        voice = LANGUAGES.get(lang, LANGUAGES["en"])["default_voice"]
```

- [ ] **Step 2: Insert the quota check right after the auth check**

Add a `datetime` import at the top of the file (near the other stdlib imports at `api/index.py:1-9`):

```python
from datetime import datetime, timezone
```

Then change the route to:

```python
@app.route("/convert", methods=["POST"])
def convert():
    user_id = _verify_supabase_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"error": "Please sign in again"}), 401

    DAILY_LIMIT = 10
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).isoformat()
    client = _load_supabase()
    count_resp = (
        client.table("conversions")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", today_start)
        .execute()
    )
    used_today = count_resp.count or 0
    if used_today >= DAILY_LIMIT:
        return jsonify({
            "error": "You've used all 10 free conversions today.",
            "daily_limit_reached": True,
            "used": used_today,
            "limit": DAILY_LIMIT,
        }), 429

    data = request.get_json()
    input_type = data.get("input_type")
    url = data.get("url", "").strip()
    text = data.get("text", "").strip()
    slug = data.get("slug", "").strip()
    voice = data.get("voice", "en-US-JennyNeural")
    lang = data.get("lang", "en")

    if voice not in ALL_VOICES:
        voice = LANGUAGES.get(lang, LANGUAGES["en"])["default_voice"]
```

- [ ] **Step 3: Add the usage count to the success response**

Find the final `return jsonify({...})` in `/convert` (currently `api/index.py:1080-1090`):

```python
        return jsonify({
            "success": True,
            "input_source": input_source,
            "word_count_cleaned": wc,
            "condensation_applied": condensed,
            "translated": lang != "en",
            "word_count_final": final_wc if condensed else wc,
            "estimated_duration": estimate_duration(final_wc),
            "filename": f"{file_slug}.mp3",
            "audio_base64": audio_b64,
        })
```

Change it to:

```python
        return jsonify({
            "success": True,
            "input_source": input_source,
            "word_count_cleaned": wc,
            "condensation_applied": condensed,
            "translated": lang != "en",
            "word_count_final": final_wc if condensed else wc,
            "estimated_duration": estimate_duration(final_wc),
            "filename": f"{file_slug}.mp3",
            "audio_base64": audio_b64,
            "conversions_used_today": used_today + 1,
            "daily_limit": DAILY_LIMIT,
        })
```

- [ ] **Step 4: Deploy and manually verify the quota check**

Deploy: `vercel --prod --yes`

Get a real access token: sign in at `https://text-to-audio-online.vercel.app`, open browser DevTools console, and run:

```js
JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k => k.includes('auth-token')))).access_token
```

Copy the printed token. Then, from a terminal, run 11 conversions in a row (replace `TOKEN` with the copied value):

```bash
for i in $(seq 1 11); do
  curl -s -o /dev/null -w "%{http_code}\n" https://text-to-audio-online.vercel.app/convert \
    -H "Authorization: Bearer TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"input_type":"manual","text":"This is a short test sentence for quota checking.","slug":"quota-test","lang":"en"}'
done
```

Expected: the first 10 lines print `200`, the 11th prints `429`.

Then confirm the message body on the 11th request:

```bash
curl -s https://text-to-audio-online.vercel.app/convert \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_type":"manual","text":"test","slug":"quota-test","lang":"en"}'
```

Expected JSON: `{"error": "You've used all 10 free conversions today.", "daily_limit_reached": true, "used": 10, "limit": 10}`

- [ ] **Step 5: Commit**

```bash
git add api/index.py
git commit -m "Enforce 10 conversions/day quota on /convert"
```

---

### Task 3: Background script stores the session pushed from the website

**Files:**
- Modify: `blog-to-audio-extension/background.js`

**Interfaces:**
- Consumes: `chrome.runtime.onMessageExternal` (Chrome API, available because Task 1 declared `externally_connectable`)
- Produces: `chrome.storage.local` key `authSession` with shape `{ access_token: string, refresh_token: string, expires_at: number, email: string }`. Task 4 and Task 6 read this key.

- [ ] **Step 1: Read the current file**

Confirm `blog-to-audio-extension/background.js` currently reads:

```js
chrome.action.onClicked.addListener((tab) => {
  const url = (tab && tab.url && tab.url.startsWith('http')) ? tab.url : '';
  chrome.tabs.create({
    url: chrome.runtime.getURL('popup.html') + (url ? '?url=' + encodeURIComponent(url) : '')
  });
});
```

- [ ] **Step 2: Add the external message listener**

Append this to the end of `blog-to-audio-extension/background.js`:

```js
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
```

- [ ] **Step 3: Manually verify the listener registers without error**

1. Go to `chrome://extensions`, find "Text to Audio Online", click **Reload**
2. Click **service worker** (or **background page**) link on the extension's card to open its console
3. Confirm there are no red errors in that console after reload

(Full end-to-end verification — that a real message from the website actually lands here — happens in Task 5's manual test, once the website side exists.)

- [ ] **Step 4: Commit**

```bash
git add blog-to-audio-extension/background.js
git commit -m "Store auth session pushed from the website via externally_connectable"
```

---

### Task 4: Popup shows a sign-in screen when there's no stored session

**Files:**
- Modify: `blog-to-audio-extension/popup.html`

**Interfaces:**
- Produces: a `#signinScreen` div (hidden by default via inline `style="display:none"`, toggled by Task 6's JS) with a `#btnSignIn` button, and wraps all existing converter markup in a `#appContent` div (also hidden by default) so Task 6 can toggle between the two.

- [ ] **Step 1: Add the sign-in screen and wrap the existing body content**

In `blog-to-audio-extension/popup.html`, replace:

```html
<body>
  <div class="header">
    <h1>🎙️ Text to Audio Online</h1>
    <p>Convert any blog to audio instantly</p>
  </div>

  <div class="body">
    <div class="tabs">
```

with:

```html
<body>
  <div class="header">
    <h1>🎙️ Text to Audio Online</h1>
    <p>Convert any blog to audio instantly</p>
  </div>

  <div class="body" id="signinScreen" style="display:none; text-align:center; padding-top: 30px;">
    <p style="color:#94a3b8; font-size:0.85em; margin-bottom:14px;">Sign in to convert blogs to audio.</p>
    <button class="btn-convert" id="btnSignIn" style="width:auto; padding: 10px 20px;">Sign in with Google</button>
  </div>

  <div class="body" id="appContent" style="display:none;">
    <div class="topbar" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
      <span id="userEmail" style="font-size:0.72em; color:#94a3b8;"></span>
      <button id="btnSignOut" style="background:none; border:none; color:#818cf8; font-size:0.72em; cursor:pointer; font-family:inherit;">Sign out</button>
    </div>
    <div class="tabs">
```

- [ ] **Step 2: Close the new wrapper div**

Replace:

```html
    <hr>
    <div class="feedback-label">💬 Share Feedback</div>
    <textarea class="feedback-box" id="feedbackText" placeholder="How was your experience?"></textarea>
    <button class="btn-feedback" id="btnFeedback">Send Feedback</button>
    <div class="feedback-ok" id="feedbackOk">✅ Thanks for your feedback!</div>
  </div>

  <div class="footer">text-to-audio-online.vercel.app</div>
```

with (dropping the feedback section entirely — it calls a `/api/feedback` endpoint that doesn't exist on the backend):

```html
  </div>

  <div class="footer">text-to-audio-online.vercel.app</div>
```

- [ ] **Step 3: Manually verify the markup**

1. Reload the extension at `chrome://extensions`, open the popup
2. Confirm the popup renders blank/empty body (both `signinScreen` and `appContent` are `display:none` — this is expected until Task 6 adds the JS that shows one of them)
3. Confirm no console errors in the popup's DevTools (right-click popup → Inspect)

- [ ] **Step 4: Commit**

```bash
git add blog-to-audio-extension/popup.html
git commit -m "Add sign-in screen markup, remove broken feedback section"
```

---

### Task 5: Website pushes the session to the extension after sign-in

**Files:**
- Modify: `api/index.py:798-811` (the Supabase auth-state JS block)

**Interfaces:**
- Consumes: `EXTENSION_ID` — replace `EXTENSION_ID_PLACEHOLDER` in Step 1 with the literal ID string recorded in Task 1, Step 4.
- Consumes: `chrome.runtime.sendMessage` (only present when the Chrome extension is installed; guarded with a existence check so this is a no-op for users without it installed)

- [ ] **Step 1: Add the extension-messaging function**

In `api/index.py`, find this block (currently at `api/index.py:798-811`):

```javascript
    supabaseClient.auth.getSession().then(({{ data }}) => applyAuthState(data.session));
    supabaseClient.auth.onAuthStateChange((_event, session) => {{
        applyAuthState(session);
        if (_event === 'SIGNED_IN') {{
            gtag('event', 'sign_in');
        }}
    }});

    document.getElementById('btn-google-signin').addEventListener('click', () => {{
        supabaseClient.auth.signInWithOAuth({{ provider: 'google' }});
    }});
    document.getElementById('btn-signout').addEventListener('click', () => {{
        supabaseClient.auth.signOut();
    }});
```

Replace it with:

```javascript
    const EXTENSION_ID = 'EXTENSION_ID_PLACEHOLDER';

    function maybeSendSessionToExtension(session) {{
        const params = new URLSearchParams(window.location.search);
        if (params.get('ext_signin') !== '1' || !session) return;
        if (typeof chrome === 'undefined' || !chrome.runtime || !chrome.runtime.sendMessage) return;
        chrome.runtime.sendMessage(EXTENSION_ID, {{
            type: 'AUTH_SESSION',
            access_token: session.access_token,
            refresh_token: session.refresh_token,
            expires_at: session.expires_at,
            email: session.user.email,
        }}, () => {{
            document.body.innerHTML = '<div style="padding:4rem 2rem; text-align:center; color:#e2e8f0;">' +
                '<h1 style="font-size:1.3rem; margin-bottom:0.5rem;">Signed in!</h1>' +
                '<p style="color:#94a3b8;">You can close this tab and return to the extension.</p></div>';
            setTimeout(() => window.close(), 2000);
        }});
    }}

    supabaseClient.auth.getSession().then(({{ data }}) => {{
        applyAuthState(data.session);
        maybeSendSessionToExtension(data.session);
    }});
    supabaseClient.auth.onAuthStateChange((_event, session) => {{
        applyAuthState(session);
        if (_event === 'SIGNED_IN') {{
            gtag('event', 'sign_in');
            maybeSendSessionToExtension(session);
        }}
    }});

    document.getElementById('btn-google-signin').addEventListener('click', () => {{
        supabaseClient.auth.signInWithOAuth({{ provider: 'google' }});
    }});
    document.getElementById('btn-signout').addEventListener('click', () => {{
        supabaseClient.auth.signOut();
    }});
```

Then replace `EXTENSION_ID_PLACEHOLDER` in the line you just added with the literal 32-character ID recorded in Task 1, Step 4 (e.g. `const EXTENSION_ID = 'ognacopmnhflbabaadbgihippfmnninm';` — use your own recorded value, not this example).

- [ ] **Step 2: Deploy**

```bash
vercel --prod --yes
```

- [ ] **Step 3: Manually verify the full sign-in handshake**

1. Make sure the extension is loaded unpacked (Task 1) and Task 3's background listener is in place
2. In Chrome, navigate to `https://text-to-audio-online.vercel.app/?ext_signin=1`
3. Sign in with Google if not already signed in
4. Expected: the page replaces itself with "Signed in! You can close this tab..." and the tab closes itself after ~2 seconds
5. Open the extension's background service worker console (`chrome://extensions` → service worker link) and confirm no errors were logged during the message
6. Open the extension popup and run in its DevTools console: `chrome.storage.local.get('authSession', console.log)` — confirm it prints an object with `access_token`, `refresh_token`, `expires_at`, and your email

- [ ] **Step 4: Commit**

```bash
git add api/index.py
git commit -m "Push Supabase session to the extension after sign-in"
```

---

### Task 6: Popup auth-state management, token refresh, and sign-out

**Files:**
- Modify: `blog-to-audio-extension/popup.js`

**Interfaces:**
- Consumes: `chrome.storage.local` key `authSession` (written by Task 3's background listener)
- Produces: `getValidAccessToken()` — an async function returning a valid (refreshed if needed) access token string, or `null` if there's no session / refresh failed. Task 7 calls this before every `/convert` request.
- Produces: `showSignedOutState()` / `showSignedInState(email)` — toggle `#signinScreen` and `#appContent` visibility. Called on popup load and after sign-out.

- [ ] **Step 1: Add auth constants and state functions at the top of popup.js**

In `blog-to-audio-extension/popup.js`, replace the first line:

```js
const API = 'https://text-to-audio-online.vercel.app';
```

with:

```js
const API = 'https://text-to-audio-online.vercel.app';
const SUPABASE_URL = 'https://pkaeridjackeiggllsxs.supabase.co';
const SUPABASE_ANON_KEY = 'REPLACE_WITH_VALUE_FROM_DOTENV_SUPABASE_ANON_KEY';

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
```

Note: replace `REPLACE_WITH_VALUE_FROM_DOTENV_SUPABASE_ANON_KEY` with the actual `SUPABASE_ANON_KEY` value from the `.env` file at the project root. This is safe to hardcode in the extension's client-side code — Supabase anon keys are public by design (access is enforced by Row Level Security on the server, not by keeping this key secret), and the website already exposes this same value in its rendered page source (`api/index.py:750`).

- [ ] **Step 2: Wire up sign-in/sign-out buttons and initial state check**

Find this block in `popup.js`:

```js
// Auto-fill current tab URL
window.addEventListener('DOMContentLoaded', () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs && tabs[0] && tabs[0].url && tabs[0].url.startsWith('http')) {
      document.getElementById('blogUrl').value = tabs[0].url;
    }
  });
});
```

Replace it with:

```js
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
```

(The `chrome.storage.onChanged` listener means: if the popup is already open when the website pushes a session in via the background script, it flips to the signed-in view live, without needing to be reopened.)

- [ ] **Step 3: Manually verify sign-in and sign-out**

1. Reload the extension, open the popup — confirm the sign-in screen shows (not the converter)
2. Click **Sign in with Google** — confirm it opens `https://text-to-audio-online.vercel.app/?ext_signin=1` in a new tab
3. Complete sign-in on that tab (per Task 5's test) — confirm the tab closes itself
4. Reopen the extension popup — confirm it now shows the converter UI with your email in the top bar
5. Click **Sign out** — confirm the popup reverts to the sign-in screen
6. Run in the popup's DevTools console: `chrome.storage.local.get('authSession', console.log)` — confirm it prints `{}` (empty)

- [ ] **Step 4: Commit**

```bash
git add blog-to-audio-extension/popup.js
git commit -m "Add auth-state management, token refresh, and sign-out to popup"
```

---

### Task 7: Fix the conversion calls to match the real /convert API

**Files:**
- Modify: `blog-to-audio-extension/popup.js`

**Interfaces:**
- Consumes: `getValidAccessToken()` (Task 6)
- Consumes: `showSignedOutState()` (Task 6) — called on a `401` response
- Produces: nothing new consumed by later tasks (this is the last task)

- [ ] **Step 1: Replace convertUrl(), convertText(), and doConvert() with the corrected API contract**

Find this block in `popup.js`:

```js
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
```

Replace it with:

```js
async function convertUrl() {
  const url = document.getElementById('blogUrl').value.trim();
  if (!url) { showError('errorUrl', 'Please enter a URL'); return; }

  setLoading('Url', true);
  hideError('errorUrl');
  document.getElementById('resultUrl').classList.remove('show');

  try {
    await doConvert({ input_type: 'url', url, lang: 'en' }, 'Url');
  } catch (err) {
    if (!String(err).includes('ort-wasm')) showError('errorUrl', err.message);
  } finally {
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
    const slug = 'extension-' + Date.now();
    await doConvert({ input_type: 'manual', text, slug, lang: 'en' }, 'Text');
  } catch (err) {
    if (!String(err).includes('ort-wasm')) showError('errorText', err.message);
  } finally {
    setLoading('Text', false);
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
```

- [ ] **Step 2: Remove the now-dead feedback wiring**

Find and delete these two lines (the feedback textarea/button no longer exist in the HTML after Task 4):

```js
// Feedback
document.getElementById('btnFeedback').addEventListener('click', sendFeedback);
```

And delete the entire `sendFeedback()` function:

```js
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
```

- [ ] **Step 3: Manually verify end-to-end conversion**

1. Reload the extension, sign in (per Task 6's test)
2. On the "Blog URL" tab, the current tab's URL should already be auto-filled if you're on an http(s) page — otherwise paste any public blog URL
3. Click **Convert to Audio** — confirm a spinner shows, then an audio player and "Download MP3" link appear, and the audio actually plays
4. Switch to "Paste Text" tab, paste a short paragraph, click **Convert to Audio** — confirm the same result
5. Click **Download MP3** — confirm a valid `.mp3` file downloads and plays outside the browser

- [ ] **Step 4: Manually verify the quota limit surfaces in the extension**

1. Using the same curl loop from Task 2 Step 4 (or by converting via the extension 10 times), exhaust the day's quota for your account
2. In the extension popup, attempt one more conversion
3. Confirm the error div shows exactly: `You've used all 10 free conversions today.`

- [ ] **Step 5: Commit**

```bash
git add blog-to-audio-extension/popup.js
git commit -m "Fix extension conversion calls to match /convert API contract"
```

---

## Self-Review Notes

- **Spec coverage:** Section 1 (sign-in handshake) → Tasks 1, 3, 5, 6. Section 2 (quota enforcement) → Task 2. Section 3 (upsell/limit messaging) → Task 2 (backend message) + Task 7 Step 4 (verification it surfaces). Section 4 (fixing the conversion call) → Task 7. Section 5 (end-to-end flow) → verified across Task 5 Step 3, Task 6 Step 3, Task 7 Steps 3-4. Error handling table → 401 handling in Task 7 Step 1, expired-token refresh in Task 6 Step 1, 429 in Task 2 + Task 7.
- **Feedback removal:** flagged in the spec as "not part of this design's goals" but "flagged here so it isn't silently left broken" — handled directly in Tasks 4 and 7 since leaving dead code that calls a nonexistent endpoint (and a UI element with no purpose) would fail review.
- **No placeholders left unresolved:** `EXTENSION_ID_PLACEHOLDER` and `REPLACE_WITH_VALUE_FROM_DOTENV_SUPABASE_ANON_KEY` are both resolved by concrete, mechanical steps (copy a value produced in an earlier task / read a value from an existing local file) — not vague guidance.
