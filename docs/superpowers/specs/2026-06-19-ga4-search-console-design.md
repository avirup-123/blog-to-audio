# GA4 + Google Search Console Integration — Design Spec

Date: 2026-06-19

## Goal

Add Google Analytics 4 tracking and Google Search Console verification to the Text to Audio Online site, so the user can see traffic/usage analytics and get the site indexed in Google Search.

## Provided Values

- GA4 Measurement ID: `G-R7SJW1JQCM`
- GSC verification meta tag: `<meta name="google-site-verification" content="oA67qNSCSvFVF177lFk0pxZrZPRoSJjAWC-7uoIUHaE" />`
- GSC property type: URL prefix, scoped to `https://text-to-audio-online.vercel.app`

These are public-facing identifiers, safe to hardcode directly into `api/index.py` — no env vars needed.

## Architecture

Both additions are static `<head>` tags embedded in the existing `build_html()` f-string in `api/index.py`. No new routes, no new dependencies, no backend changes for the base tracking. Three custom GA4 events are added to existing JS functions to track sign-ins and conversions.

## Changes

### 1. GSC verification meta tag

Added once, as a literal line, anywhere in the existing `<head>` block (alongside other meta tags):

```html
<meta name="google-site-verification" content="oA67qNSCSvFVF177lFk0pxZrZPRoSJjAWC-7uoIUHaE" />
```

### 2. GA4 base snippet

Added in `<head>`, this auto-tracks page views with no further code:

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-R7SJW1JQCM"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-R7SJW1JQCM');
</script>
```

(Note: since this lives inside a Python f-string, literal JS braces must be escaped as `{{`/`}}` per the file's existing convention.)

### 3. Custom GA4 events

Three events, added to existing JS functions — no new functions, no new user-facing behavior:

- **`sign_in`**: fired once inside `applyAuthState(session)`, only on the transition from no-session to a session existing (not on every page load where a session is restored from storage). Implementation approach: track a module-level flag (e.g. `let hasFiredSignIn = false`) that prevents re-firing on session-restore calls to `applyAuthState`. Actually — simpler and more correct: fire it specifically inside the `btn-google-signin` click handler's resulting auth state change, not from every `applyAuthState` call. The cleanest implementation: rely on Supabase's `onAuthStateChange` event name, which Supabase itself reports (`'SIGNED_IN'` vs `'INITIAL_SESSION'` vs `'SIGNED_OUT'`) — fire `gtag('event', 'sign_in')` only when the event is `'SIGNED_IN'`.
- **`conversion_success`**: fired inside `showResult(data)`, with params `{{ language: currentLang, voice: <selected voice id> }}`.
- **`conversion_error`**: fired inside `showError(msg)`, with param `{{ message: msg }}`.

## Sitemap Submission

One-time manual action, not code: once GSC verification passes (user clicks "Verify" in the GSC dashboard after this deploys), the user submits `https://text-to-audio-online.vercel.app/sitemap.xml` via Search Console's Sitemaps section. The sitemap route already exists (`/sitemap.xml`, added in earlier work) — no changes needed there.

## Error Handling

None needed — gtag.js calls are fire-and-forget; if the GA4 script fails to load (network issue, ad blocker), `gtag` becomes a no-op or undefined and should not throw if called defensively. Wrap calls in a guard: only call `gtag(...)` if `typeof gtag === 'function'` (or rely on the snippet's own `dataLayer.push` shim, which always exists once the inline script runs, regardless of whether the external script loaded — this is safe by design since `gtag()` pushes to `dataLayer` synchronously and the external script drains it asynchronously whenever it loads).

## Scope Boundaries

- No GA4 Admin API or server-side tracking — client-side gtag.js only.
- No enhanced ecommerce, no custom dimensions beyond `language`/`voice`/`message` params on the three events.
- No automated sitemap re-submission — one-time manual action by the user.
- No changes to existing `/sitemap.xml` or `/robots.txt` routes.
