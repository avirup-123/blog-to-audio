# GA4 + Google Search Console Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Google Analytics 4 page-view + custom-event tracking and Google Search Console site verification to the Text to Audio Online site, by embedding static tags and small JS hooks into the existing `build_html()` f-string in `api/index.py`.

**Architecture:** Two static `<head>` additions (GSC verification meta tag, GA4 gtag.js snippet) plus three `gtag('event', ...)` calls added to existing JS functions (`onAuthStateChange` callback, `showResult`, `showError`). No new routes, no new dependencies, no env vars — both IDs are public and hardcoded directly into the file.

**Tech Stack:** Flask single-file app (`api/index.py`), gtag.js (Google's GA4 client library, loaded via CDN), no build step.

## Global Constraints

- GA4 Measurement ID: `G-R7SJW1JQCM`
- GSC verification meta tag content: `oA67qNSCSvFVF177lFk0pxZrZPRoSJjAWC-7uoIUHaE`
- Both IDs are public-facing — hardcode directly in `api/index.py`, no env vars.
- No new routes, no new dependencies, no backend changes.
- The whole HTML/CSS/JS is one Python f-string returned by `build_html()` — literal JS curly braces must be escaped as `{{`/`}}` per the file's existing convention throughout.
- `sign_in` event must fire only on actual sign-in (Supabase's `'SIGNED_IN'` auth event), not on every page-load session restore (`'INITIAL_SESSION'`).
- No enhanced ecommerce, no custom dimensions beyond `language`/`voice`/`message` params on the three events.
- No automated sitemap re-submission — that remains a manual one-time action by the user in the GSC dashboard, not part of this plan.

---

### Task 1: Add GSC verification meta tag and GA4 base snippet to `<head>`

**Files:**
- Modify: `api/index.py:476-490` (the `<head>` block)

**Interfaces:**
- Produces: nothing consumed by later tasks — this task only adds static tags, no JS state.

- [ ] **Step 1: Add the GSC verification meta tag**

In `api/index.py`, find this block (around line 482-483):

```html
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://text-to-audio-online.vercel.app/">
```

Add the GSC verification tag right after the `<meta name="robots" ...>` line:

```html
    <meta name="robots" content="index, follow">
    <meta name="google-site-verification" content="oA67qNSCSvFVF177lFk0pxZrZPRoSJjAWC-7uoIUHaE" />
    <link rel="canonical" href="https://text-to-audio-online.vercel.app/">
```

- [ ] **Step 2: Add the GA4 base snippet**

Find this line (around line 490, the last `<meta name="twitter:description" ...>` tag before the FAQ JSON-LD `<script>` block):

```html
    <meta name="twitter:description" content="Convert any blog post or text into natural-sounding MP3 audio for free. 60+ AI voices, 19 languages.">
    <script type="application/ld+json">
```

Insert the GA4 snippet between them:

```html
    <meta name="twitter:description" content="Convert any blog post or text into natural-sounding MP3 audio for free. 60+ AI voices, 19 languages.">
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-R7SJW1JQCM"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-R7SJW1JQCM');
    </script>
    <script type="application/ld+json">
```

Note the `{{` / `}}` escaping on the `function gtag(){{dataLayer.push(arguments);}}` line — this is a Python f-string, so literal JS braces must be doubled, matching the file's existing convention seen throughout the rest of the script blocks.

- [ ] **Step 3: Verify the file still compiles and `build_html()` produces valid output**

Run:
```bash
cd "C:\Users\Avirup\Pictures\blog-to-audio" && python -m py_compile api/index.py
```
Expected: no output, exit code 0.

Run:
```bash
cd "C:\Users\Avirup\Pictures\blog-to-audio" && python -c "from api.index import build_html; html = build_html(); assert 'google-site-verification' in html; assert 'G-R7SJW1JQCM' in html; assert 'gtag' in html; print('OK', len(html))"
```
Expected output: `OK <some number>` with no exceptions.

- [ ] **Step 4: Commit**

```bash
cd "C:\Users\Avirup\Pictures\blog-to-audio" && git add api/index.py && git commit -m "Add GA4 base snippet and Google Search Console verification meta tag"
```

---

### Task 2: Add custom GA4 events for sign-in, conversion success, and conversion error

**Files:**
- Modify: `api/index.py:790-791` (the Supabase auth state listener)
- Modify: `api/index.py:872-876` (the `showError` function)
- Modify: `api/index.py:877-895` (the `showResult` function)

**Interfaces:**
- Consumes: the `gtag` function defined in Task 1's snippet (global function, callable as `gtag('event', name, params)`), and the existing `currentLang` variable (line 801) plus the `voice-select` DOM element (line 679) for the `conversion_success` event's params.
- Produces: nothing consumed by later tasks — this is the last task in the plan.

- [ ] **Step 1: Fire `sign_in` only on the `'SIGNED_IN'` Supabase auth event**

Find this line (around line 791):

```javascript
    supabaseClient.auth.onAuthStateChange((_event, session) => applyAuthState(session));
```

Replace it with:

```javascript
    supabaseClient.auth.onAuthStateChange((_event, session) => {{
        applyAuthState(session);
        if (_event === 'SIGNED_IN') {{
            gtag('event', 'sign_in');
        }}
    }});
```

This fires the event only on the actual sign-in transition (Supabase reports `'SIGNED_IN'` distinctly from `'INITIAL_SESSION'`, which is what fires when a stored session is restored on page load), satisfying the global constraint.

- [ ] **Step 2: Fire `conversion_error` inside `showError`**

Find this function (around line 872-876):

```javascript
    function showError(msg) {{
        const el = document.getElementById('error');
        el.textContent = msg; el.classList.add('show');
        document.getElementById('result').classList.remove('show');
    }}
```

Add the `gtag` call as the first line inside the function body:

```javascript
    function showError(msg) {{
        gtag('event', 'conversion_error', {{ message: msg }});
        const el = document.getElementById('error');
        el.textContent = msg; el.classList.add('show');
        document.getElementById('result').classList.remove('show');
    }}
```

- [ ] **Step 3: Fire `conversion_success` inside `showResult`**

Find this function (around line 877-895, ending with `loadHistory();` then a closing `}}`):

```javascript
    function showResult(data) {{
        document.getElementById('error').classList.remove('show');
        document.getElementById('r-source').textContent = data.input_source;
```

Add the `gtag` call as the first line inside the function body, using `currentLang` and the currently-selected voice from the `voice-select` dropdown:

```javascript
    function showResult(data) {{
        gtag('event', 'conversion_success', {{ language: currentLang, voice: document.getElementById('voice-select').value }});
        document.getElementById('error').classList.remove('show');
        document.getElementById('r-source').textContent = data.input_source;
```

- [ ] **Step 4: Verify the file still compiles and the new event calls are present**

Run:
```bash
cd "C:\Users\Avirup\Pictures\blog-to-audio" && python -m py_compile api/index.py
```
Expected: no output, exit code 0.

Run:
```bash
cd "C:\Users\Avirup\Pictures\blog-to-audio" && python -c "
from api.index import build_html
html = build_html()
assert \"gtag('event', 'sign_in')\" in html
assert \"gtag('event', 'conversion_error'\" in html
assert \"gtag('event', 'conversion_success'\" in html
assert \"_event === 'SIGNED_IN'\" in html
print('OK', len(html))
"
```
Expected output: `OK <some number>` with no exceptions.

- [ ] **Step 5: Commit**

```bash
cd "C:\Users\Avirup\Pictures\blog-to-audio" && git add api/index.py && git commit -m "Add GA4 custom events for sign-in, conversion success, and conversion error"
```

---

### Task 3: Deploy and verify GA4 + GSC are live in production

**Files:** None (deployment + manual verification only)

**Interfaces:** None — terminal task.

- [ ] **Step 1: Deploy to Vercel production**

```bash
cd "C:\Users\Avirup\Pictures\blog-to-audio" && vercel --prod
```

- [ ] **Step 2: Verify the GSC meta tag is live**

```bash
curl -s "https://text-to-audio-online.vercel.app/" | grep "google-site-verification"
```
Expected output contains: `<meta name="google-site-verification" content="oA67qNSCSvFVF177lFk0pxZrZPRoSJjAWC-7uoIUHaE" />`

- [ ] **Step 3: Verify the GA4 snippet is live**

```bash
curl -s "https://text-to-audio-online.vercel.app/" | grep "G-R7SJW1JQCM"
```
Expected output contains two matches: the `gtag/js?id=G-R7SJW1JQCM` script src, and the `gtag('config', 'G-R7SJW1JQCM');` call.

- [ ] **Step 4: User completes GSC verification**

This is a manual action for the user (not a code or CLI step): go to https://search.google.com/search-console, open the `https://text-to-audio-online.vercel.app` property, click **Verify**. Once verified, go to **Sitemaps** in the left sidebar and submit `https://text-to-audio-online.vercel.app/sitemap.xml`.

- [ ] **Step 5: User confirms GA4 is receiving data**

This is a manual action for the user: go to https://analytics.google.com, open the property, go to **Reports → Realtime**, visit the live site in a browser, and confirm at least one active user shows up in the Realtime report within a minute or two.

No commit for this task (deployment + manual verification only).
