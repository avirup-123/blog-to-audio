# Supabase Auth + Conversion History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gate the Text to Audio converter behind Google login (via Supabase Auth) and log every conversion to a `conversions` table with Row Level Security so each user only ever sees their own history.

**Architecture:** The existing single-file Vercel app (`api/index.py`) gains: (1) a Supabase JS client loaded via CDN in the HTML for login/logout and reading history directly with RLS, (2) a backend token-verification call to Supabase's `/auth/v1/user` endpoint on `/convert`, and (3) a server-side insert into `conversions` using the Supabase service key after each successful conversion.

**Tech Stack:** Flask, Supabase (Postgres + Auth), `supabase-py` (backend), `@supabase/supabase-js` (CDN, frontend), existing edge-tts/Gemini pipeline unchanged.

## Global Constraints

- Supabase Project URL: `https://pkaeridjackeiggllsxs.supabase.co`
- `SUPABASE_ANON_KEY` is public — safe to embed in frontend JS.
- `SUPABASE_SERVICE_KEY` is secret — backend-only, set as a Vercel env var, never committed to code.
- Site URL for OAuth redirects: `https://text-to-audio-online.vercel.app`
- No password/email auth — Google only.
- No audio re-download from history (log-only).
- History insert failures must never block returning the generated audio to the user.
- `/convert` requires a valid `Authorization: Bearer <token>` header — no anonymous conversions.

---

### Task 1: Create the `conversions` table with RLS in Supabase

**Files:** None (this is a Supabase dashboard / SQL action, no local files)

**Interfaces:**
- Produces: a `conversions` table that Task 3's backend insert and Task 4's frontend history query both depend on, with exactly these columns: `id, user_id, input_source, source_snippet, language, voice, word_count, condensed, translated, estimated_duration, created_at`.

- [ ] **Step 1: Run the schema SQL in the Supabase SQL Editor**

Go to the Supabase dashboard (`https://pkaeridjackeiggllsxs.supabase.co` project) → SQL Editor → New query → paste and run:

```sql
create table conversions (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users(id) not null,
  input_source text not null,
  source_snippet text,
  language text not null,
  voice text not null,
  word_count integer not null,
  condensed boolean default false,
  translated boolean default false,
  estimated_duration text not null,
  created_at timestamptz default now()
);

alter table conversions enable row level security;

create policy "Users select own conversions"
  on conversions for select
  using (auth.uid() = user_id);

create policy "Users insert own conversions"
  on conversions for insert
  with check (auth.uid() = user_id);
```

- [ ] **Step 2: Verify the table exists**

In the Supabase dashboard, go to Table Editor → confirm `conversions` appears with the 11 columns above and a shield icon indicating RLS is enabled.

- [ ] **Step 3: Verify Google auth provider is enabled**

Go to Authentication → Providers → confirm Google is toggled on with Client ID/Secret filled in, and Authentication → URL Configuration → confirm Site URL is `https://text-to-audio-online.vercel.app`.

No commit needed for this task (no local files changed).

---

### Task 2: Add Supabase env vars and `supabase-py` dependency

**Files:**
- Modify: `requirements.txt`
- Modify (local only, not committed): Vercel project env vars via `vercel env add` or dashboard

**Interfaces:**
- Produces: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` available via `os.getenv(...)` in `api/index.py` (consumed by Task 3), and the `supabase` pip package importable.

- [ ] **Step 1: Add `supabase` to requirements.txt**

Read current `requirements.txt`:
```
flask
requests
beautifulsoup4
google-genai
edge-tts
python-dotenv
```

Edit it to:
```
flask
requests
beautifulsoup4
google-genai
edge-tts
python-dotenv
supabase
```

- [ ] **Step 2: Add env vars to local `.env` for testing**

Add these three lines to `C:\Users\Avirup\Pictures\blog-to-audio\.env` (alongside the existing `GEMINI_API_KEY` line):

```
SUPABASE_URL=https://pkaeridjackeiggllsxs.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBrYWVyaWRqYWNrZWlnZ2xsc3hzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODE3NzEwMTQsImV4cCI6MjA5NzM0NzAxNH0.P2xHr2wUcdDUfb8bErspbC9K2O5li4eWEq15XHnzXFE
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBrYWVyaWRqYWNrZWlnZ2xsc3hzIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTc3MTAxNCwiZXhwIjoyMDk3MzQ3MDE0fQ.QbA40eMWKPgenN78ug7xywnulRrOQhbmBdPG5o5VfzQ
```

- [ ] **Step 3: Install the dependency locally and verify import**

Run: `pip install supabase`
Then verify: `python -c "from supabase import create_client; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Add the same three env vars on Vercel**

Run (from the project directory, with Vercel CLI linked):
```bash
vercel env add SUPABASE_URL production
vercel env add SUPABASE_ANON_KEY production
vercel env add SUPABASE_SERVICE_KEY production
```
Paste the corresponding value at each prompt (same values as Step 2). If the Vercel CLI isn't linked/available, add them via the Vercel dashboard → Project → Settings → Environment Variables instead.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "Add supabase-py dependency for auth and conversion history"
```

(`.env` is expected to already be gitignored — do not commit it. If it is not gitignored, add it to `.gitignore` before committing this task instead of committing the secrets.)

---

### Task 3: Verify auth tokens and log conversions in `/convert`

**Files:**
- Modify: `api/index.py:1-30` (imports/lazy-loaders)
- Modify: `api/index.py:814-890` (the `/convert` route)
- Test: manual curl-based test (no existing test suite in this project; Flask app has no `tests/` directory)

**Interfaces:**
- Consumes: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` env vars from Task 2.
- Produces: `_verify_supabase_token(token) -> str | None` (returns `user_id` or `None`), `_log_conversion(user_id, ...)` used only inside this task — not consumed elsewhere.

- [ ] **Step 1: Add a lazy Supabase client loader next to the existing `_load_edge_tts`/`_load_genai` pattern**

In `api/index.py`, after line 30 (`return genai`), add:

```python
supabase_client = None

def _load_supabase():
    global supabase_client
    if supabase_client is None:
        from supabase import create_client
        url = os.getenv("SUPABASE_URL", "").strip()
        key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
        supabase_client = create_client(url, key)
    return supabase_client
```

- [ ] **Step 2: Add the token verification helper**

After `_get_gemini_key()` (around line 358), add:

```python
def _verify_supabase_token(auth_header):
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        return None
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    resp = http_requests.get(
        f"{supabase_url}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {token}",
            "apikey": os.getenv("SUPABASE_ANON_KEY", "").strip(),
        },
        timeout=10,
    )
    if resp.status_code != 200:
        return None
    return resp.json().get("id")
```

- [ ] **Step 3: Add the history-logging helper**

Right after `_verify_supabase_token`, add:

```python
def _log_conversion(user_id, input_source, language, voice, word_count_val, condensed, translated, duration):
    try:
        client = _load_supabase()
        client.table("conversions").insert({
            "user_id": user_id,
            "input_source": input_source,
            "source_snippet": input_source[:100],
            "language": language,
            "voice": voice,
            "word_count": word_count_val,
            "condensed": condensed,
            "translated": translated,
            "estimated_duration": duration,
        }).execute()
    except Exception:
        print(f"CONVERSION LOG ERROR: {traceback.format_exc()}", file=sys.stderr, flush=True)
```

- [ ] **Step 4: Gate `/convert` on a valid token and log on success**

In `api/index.py`, the `/convert` route currently starts at line 814:

```python
@app.route("/convert", methods=["POST"])
def convert():
    data = request.get_json()
```

Change it to verify auth first:

```python
@app.route("/convert", methods=["POST"])
def convert():
    user_id = _verify_supabase_token(request.headers.get("Authorization"))
    if not user_id:
        return jsonify({"error": "Please sign in again"}), 401

    data = request.get_json()
```

Then, in the success path (the `return jsonify({...})` block currently at lines 877-887), insert a logging call immediately before that `return`:

```python
        input_source = f"URL: {url}" if input_type == "url" else "Pasted text"
        _log_conversion(
            user_id=user_id,
            input_source=input_source,
            language=lang,
            voice=voice,
            word_count_val=final_wc if condensed else wc,
            condensed=condensed,
            translated=lang != "en",
            duration=estimate_duration(final_wc),
        )

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

(Note: `input_source` replaces the inline ternary that was previously duplicated only inside the `jsonify` call — this removes that duplication.)

- [ ] **Step 5: Manually verify the 401 path**

Run the Flask dev server locally (`python -m flask --app api/index run` from the project root, or however it's normally run locally — check `app.py` for the existing local-run pattern first), then:

```bash
curl -s -X POST http://localhost:5000/convert -H "Content-Type: application/json" -d '{"input_type":"manual","text":"hello","slug":"test"}'
```
Expected: `{"error":"Please sign in again"}` with HTTP 401.

- [ ] **Step 6: Manually verify the success + logging path**

This requires a real Supabase access token. Obtain one by signing in via the deployed/local frontend once Task 4 is done (the browser console can run `(await supabase.auth.getSession()).data.session.access_token` to print it), then:

```bash
curl -s -X POST http://localhost:5000/convert -H "Content-Type: application/json" -H "Authorization: Bearer <token>" -d '{"input_type":"manual","text":"This is a short test paragraph for conversion.","slug":"test","voice":"en-US-JennyNeural","lang":"en"}'
```
Expected: JSON response with `"success": true` and a row appears in the Supabase Table Editor under `conversions` with the matching `user_id`.

(This step is deferred until Task 4's frontend exists to obtain a token — note it as a follow-up check after Task 4, not a blocker for committing Task 3.)

- [ ] **Step 7: Commit**

```bash
git add api/index.py
git commit -m "Require Supabase auth and log conversion history on /convert"
```

---

### Task 4: Add Google sign-in, sign-out, and conversion gating to the frontend

**Files:**
- Modify: `api/index.py:425-440` (head section, add Supabase JS CDN script)
- Modify: `api/index.py:465-568` (CSS, add auth-screen and header styles)
- Modify: `api/index.py:570-637` (HTML body, add header bar + sign-in screen, wrap existing converter in a gated container)
- Modify: `api/index.py:637-782` (JS, add Supabase client init, auth state handling, attach bearer token to `/convert` fetch)

**Interfaces:**
- Consumes: `SUPABASE_URL`, `SUPABASE_ANON_KEY` — these must be embedded as JS string literals in `build_html()` (the anon key is public, safe to embed), read via `os.getenv(...)` inside `build_html()`.
- Produces: a `window.supabase` client instance and a global `currentSession` variable that Task 5 (history tab) reads.

- [ ] **Step 1: Add the Supabase JS CDN script tag and embed config values**

In `build_html()`, find the `<head>` section. After the existing `<script type="application/ld+json">...</script>` block (ends at line 464) and before `<style>` (line 465), add:

```python
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js"></script>
```

This must be a literal addition inside the f-string returned by `build_html()`.

- [ ] **Step 2: Add CSS for the header bar and sign-in screen**

Inside the `<style>` block, right before the closing `</style>` (just before line 568's `@media` block ends — add these new rules before the existing `@media (max-width: 600px)` block at line 552 so the media query can override them too):

```css
        .topbar {{
            position: fixed; top: 0; left: 0; right: 0; height: 56px;
            display: flex; align-items: center; justify-content: flex-end;
            padding: 0 1.5rem; background: #0f172a; border-bottom: 1px solid #1e293b;
            z-index: 10; display: none;
        }}
        .topbar.show {{ display: flex; }}
        .topbar-user {{ display: flex; align-items: center; gap: 0.75rem; font-size: 0.85rem; color: #94a3b8; }}
        .btn-signout {{
            background: #1e293b; color: #e2e8f0; border: 1px solid #334155; border-radius: 6px;
            padding: 0.4rem 0.85rem; font-size: 0.82rem; cursor: pointer; font-family: inherit;
        }}
        .btn-signout:hover {{ background: #253046; }}
        .signin-screen {{
            display: none; flex-direction: column; align-items: center; justify-content: center;
            min-height: 60vh; text-align: center; padding: 2rem;
        }}
        .signin-screen.show {{ display: flex; }}
        .signin-screen h1 {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
        .signin-screen p {{ color: #94a3b8; margin-bottom: 1.5rem; }}
        .btn-google {{
            display: flex; align-items: center; gap: 0.6rem; background: #fff; color: #1f1f1f;
            border: none; border-radius: 8px; padding: 0.75rem 1.5rem; font-size: 0.95rem;
            font-weight: 500; cursor: pointer; font-family: inherit;
        }}
        .btn-google:hover {{ background: #f1f1f1; }}
        .app-content {{ display: none; }}
        .app-content.show {{ display: block; }}
```

- [ ] **Step 3: Add the header bar and sign-in screen markup, wrap the existing converter**

In the HTML body, find the opening `<body>` tag (line 570) and the `<div class="hero">` that follows it (line 571). Change:

```html
<body>
    <div class="hero"><div class="container">
```

to:

```html
<body>
    <div class="topbar" id="topbar">
        <div class="topbar-user">
            <span id="user-email"></span>
            <button class="btn-signout" id="btn-signout">Sign out</button>
        </div>
    </div>
    <div class="signin-screen" id="signin-screen">
        <h1>Text to Audio Online</h1>
        <p>Sign in with Google to start converting blog posts to audio</p>
        <button class="btn-google" id="btn-google-signin">Sign in with Google</button>
    </div>
    <div class="app-content" id="app-content">
    <div class="hero"><div class="container">
```

Then find the end of that container/hero structure. Currently the FAQ section closes with (lines 635-636):

```html
        </div>
    </div></div>
```

Change the final `</div></div>` to close the new `app-content` wrapper too:

```html
        </div>
    </div></div></div>
```

- [ ] **Step 4: Embed Supabase config and add auth JS logic**

In the `<script>` block, find the top where `const LANGS = {lang_json};` is declared (line 638). Right before it, add the Supabase client init using values from `os.getenv`:

```python
    const SUPABASE_URL = '{os.getenv("SUPABASE_URL", "").strip()}';
    const SUPABASE_ANON_KEY = '{os.getenv("SUPABASE_ANON_KEY", "").strip()}';
    const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    let currentSession = null;

    function applyAuthState(session) {{
        currentSession = session;
        const topbar = document.getElementById('topbar');
        const signinScreen = document.getElementById('signin-screen');
        const appContent = document.getElementById('app-content');
        if (session) {{
            topbar.classList.add('show');
            signinScreen.classList.remove('show');
            appContent.classList.add('show');
            document.getElementById('user-email').textContent = session.user.email;
        }} else {{
            topbar.classList.remove('show');
            signinScreen.classList.add('show');
            appContent.classList.remove('show');
        }}
    }}

    supabaseClient.auth.getSession().then(({{ data }}) => applyAuthState(data.session));
    supabaseClient.auth.onAuthStateChange((_event, session) => applyAuthState(session));

    document.getElementById('btn-google-signin').addEventListener('click', () => {{
        supabaseClient.auth.signInWithOAuth({{ provider: 'google' }});
    }});
    document.getElementById('btn-signout').addEventListener('click', () => {{
        supabaseClient.auth.signOut();
    }});

    const LANGS = {lang_json};
```

This is a Python f-string, so the embedded `{os.getenv(...)}` expressions are evaluated by Python when `build_html()` runs, and the literal JS braces `{{` / `}}` follow the file's existing escaping convention (the whole HTML is one big f-string with `{{`/`}}` for literal JS braces, as seen throughout the existing code).

- [ ] **Step 5: Attach the bearer token to the `/convert` fetch call**

Find the `convert()` function (around line 738-755):

```javascript
    async function convert(body, btn) {{
        hideResults();
        const L = LANGS[currentLang];
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span>' + L.btn_converting;
        try {{
            const resp = await fetch('/convert', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(body),
            }});
```

Change the `headers` to include the bearer token, and handle 401 by re-showing the sign-in screen:

```javascript
    async function convert(body, btn) {{
        hideResults();
        const L = LANGS[currentLang];
        const originalText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span>' + L.btn_converting;
        try {{
            const resp = await fetch('/convert', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + (currentSession ? currentSession.access_token : ''),
                }},
                body: JSON.stringify(body),
            }});
            if (resp.status === 401) {{
                applyAuthState(null);
                showError('Please sign in again');
                return;
            }}
```

(The existing line `const data = await resp.json();` and onward stays as-is right after this new block — only the `headers` object and the new 401 check are inserted.)

- [ ] **Step 6: Manually verify the gated UI**

Run the local Flask server, open `http://localhost:5000/` in a browser. Expected: only the "Sign in with Google" screen is visible, no converter/FAQ visible. Click "Sign in with Google", complete the OAuth flow. Expected: redirected back to the site, the topbar now shows the user's email and a Sign out button, and the converter + FAQ are now visible.

- [ ] **Step 7: Manually verify a full conversion end-to-end while signed in**

While signed in, paste short text in the "Paste Text" tab, give it a slug, click Convert. Expected: audio plays back successfully, and a new row appears in the Supabase `conversions` table for that user.

- [ ] **Step 8: Manually verify sign-out re-gates the UI**

Click "Sign out". Expected: immediately returns to the sign-in screen.

- [ ] **Step 9: Commit**

```bash
git add api/index.py
git commit -m "Add Google sign-in gating and session-aware /convert auth to frontend"
```

---

### Task 5: Add a History tab showing the signed-in user's past conversions

**Files:**
- Modify: `api/index.py:574-577` (tabs markup)
- Modify: `api/index.py:588-605` (panels markup, add a third panel)
- Modify: `api/index.py:476-485` (tab/panel CSS — likely no changes needed, reuse existing `.tab`/`.panel` classes)
- Modify: `api/index.py` JS (add history-loading function, wire into the existing tab-click handler and into `applyAuthState`)

**Interfaces:**
- Consumes: `supabaseClient` and `currentSession` from Task 4.
- Produces: nothing consumed by later tasks (this is the last task).

- [ ] **Step 1: Add the History tab button**

Find the tabs markup (lines 574-577):

```html
        <div class="tabs">
            <button class="tab active" data-tab="url" id="t-tab-url">From URL</button>
            <button class="tab" data-tab="manual" id="t-tab-paste">Paste Text</button>
        </div>
```

Add a third tab:

```html
        <div class="tabs">
            <button class="tab active" data-tab="url" id="t-tab-url">From URL</button>
            <button class="tab" data-tab="manual" id="t-tab-paste">Paste Text</button>
            <button class="tab" data-tab="history" id="t-tab-history">History</button>
        </div>
```

- [ ] **Step 2: Add the History panel markup**

After the existing `panel-manual` div closes (around line 605, right before `<div class="error-msg" id="error">`), add a new panel:

```html
        <div id="panel-history" class="panel">
            <table class="history-table" id="history-table">
                <thead>
                    <tr><th>Date</th><th>Source</th><th>Language</th><th>Voice</th><th>Duration</th></tr>
                </thead>
                <tbody id="history-tbody"></tbody>
            </table>
            <p id="history-empty" style="display:none; color:#94a3b8; font-size:0.9rem;">No conversions yet.</p>
        </div>
```

- [ ] **Step 3: Add table CSS**

In the `<style>` block, add (anywhere among the other component styles, e.g. right after the `.faq` rules around line 545):

```css
        .history-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
        .history-table th {{ text-align: left; color: #94a3b8; padding: 0.5rem; border-bottom: 1px solid #334155; font-weight: 500; }}
        .history-table td {{ padding: 0.5rem; border-bottom: 1px solid #1e293b; color: #e2e8f0; }}
```

- [ ] **Step 4: Add the history-loading JS function**

In the `<script>` block, after `applyAuthState` is defined (Task 4, Step 4), add:

```javascript
    async function loadHistory() {{
        if (!currentSession) return;
        const {{ data, error }} = await supabaseClient
            .from('conversions')
            .select('*')
            .order('created_at', {{ ascending: false }});
        const tbody = document.getElementById('history-tbody');
        const empty = document.getElementById('history-empty');
        tbody.innerHTML = '';
        if (error || !data || data.length === 0) {{
            empty.style.display = 'block';
            return;
        }}
        empty.style.display = 'none';
        for (const row of data) {{
            const tr = document.createElement('tr');
            const date = new Date(row.created_at).toLocaleString();
            tr.innerHTML = '<td>' + date + '</td><td>' + row.source_snippet + '</td><td>' + row.language + '</td><td>' + row.voice + '</td><td>' + row.estimated_duration + '</td>';
            tbody.appendChild(tr);
        }}
    }}
```

- [ ] **Step 5: Wire the History tab into the existing tab-click handler**

Find the existing tab-click handler (around lines 695-703):

```javascript
    document.querySelectorAll('.tab').forEach(tab => {{
        tab.addEventListener('click', () => {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
            hideResults();
        }});
    }});
```

Change it to call `loadHistory()` when the history tab is clicked:

```javascript
    document.querySelectorAll('.tab').forEach(tab => {{
        tab.addEventListener('click', () => {{
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
            hideResults();
            if (tab.dataset.tab === 'history') loadHistory();
        }});
    }});
```

- [ ] **Step 6: Refresh history after a successful conversion**

Find the `showResult(data)` function (around lines 714-731). At the end of the function, right before its closing `}}`, add a call to refresh history so a just-completed conversion shows up immediately if the user switches tabs:

```javascript
        document.getElementById('result').classList.add('show');
        loadHistory();
    }}
```

(This replaces the original final line `document.getElementById('result').classList.add('show');` followed directly by the closing brace — the `loadHistory();` call is the only addition.)

- [ ] **Step 7: Manually verify the History tab**

While signed in, perform one conversion, then click the "History" tab. Expected: a table row appears showing the just-completed conversion's date, source, language, voice, and duration. Sign out and sign back in as a different Google account (or verify via the Supabase Table Editor) — expected: that second account's History tab shows zero rows from the first account, confirming RLS works.

- [ ] **Step 8: Commit**

```bash
git add api/index.py
git commit -m "Add conversion history tab backed by Supabase with RLS"
```

---

### Task 6: Deploy to Vercel and verify production end-to-end

**Files:** None (deployment + manual verification only)

**Interfaces:** None — terminal task.

- [ ] **Step 1: Confirm all three Supabase env vars are set on Vercel production**

Run: `vercel env ls`
Expected: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` all listed for the `production` environment (added in Task 2, Step 4).

- [ ] **Step 2: Deploy**

```bash
vercel --prod
```

- [ ] **Step 3: Verify production sign-in flow**

Visit `https://text-to-audio-online.vercel.app`. Expected: sign-in screen shown. Click "Sign in with Google", complete the flow. Expected: redirected back, signed in, converter visible.

- [ ] **Step 4: Verify production conversion + history**

Convert a short piece of text while signed in. Expected: audio returns successfully. Click History tab. Expected: the new conversion appears.

- [ ] **Step 5: Verify production sign-out**

Click Sign out. Expected: returns to sign-in screen, refreshing the page keeps it signed out until signing in again.

No commit for this task (deployment only, no code changes).
