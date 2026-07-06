# Chrome Extension Auth & Free-Tier Quota — Design Spec

Date: 2026-07-06

## Background

The `blog-to-audio-extension` Chrome extension was built against an earlier
version of the backend API. Since then, the website added Supabase Google
auth and now requires a Bearer token on `POST /convert` (see
`api/index.py:1001-1005`). The extension's `popup.js` currently:

- Calls endpoints that don't exist (`/api/fetch-url`, `/api/convert` instead
  of the real `/convert`)
- Sends no auth token
- Expects a raw audio blob response, but `/convert` returns JSON with
  `audio_base64`

This causes every conversion attempt to fail with a JSON-parse error (the
server returns Vercel's default HTML 404 page for the wrong paths).

Separately, the user intends to monetize the extension. Requiring sign-in
ties usage to an identified account, which enables a free-tier usage cap and
a future upgrade path, and unifies conversion history across the website and
extension (both write to the same `conversions` table).

## Goals

1. Fix the extension so conversions actually work against the current
   `/convert` API contract.
2. Require Google sign-in in the extension, reusing the website's existing
   Supabase auth — no new OAuth configuration needed.
3. Enforce a combined (website + extension) free-tier limit of 10
   conversions per user per UTC calendar day.
4. Show a plain limit-reached message when the cap is hit. No payment
   integration in this pass — that is an explicit future project.

## Out of scope

- Any real payment processing (Stripe, Dodo Payments, etc.) — deferred to a
  future spec once a processor is chosen. Ship the extension first.
- Per-user timezone handling for the daily quota — UTC calendar day is used
  uniformly.
- Any change to the website's existing sign-in UI/flow.

## Design

### 1. Sign-in flow (extension ↔ website handshake)

- On popup open, the extension checks `chrome.storage.local` for a saved
  Supabase session (`access_token`, `refresh_token`, `expires_at`, user
  email).
- If none is found (or the refresh token is invalid), the popup shows a
  sign-in screen with a single "Sign in with Google" button instead of the
  converter UI.
- Clicking it opens `https://text-to-audio-online.vercel.app/?ext_signin=1`
  in a new browser tab, using the site's existing Google OAuth flow
  unchanged.
- Once the website's Supabase client establishes a session, it checks for
  `?ext_signin=1` in the URL. If present, it sends the session to the
  extension via
  `chrome.runtime.sendMessage(EXTENSION_ID, { type: 'AUTH_SESSION', access_token, refresh_token, expires_at, email })`.
  This requires the website's page script to know the extension's ID (a
  constant, since the ID is pinned — see below) and the extension to declare
  `externally_connectable` in its manifest, restricted to
  `https://text-to-audio-online.vercel.app/*`, so no other site can push a
  session into the extension.
- The extension's background script listens for this message, saves the
  session to `chrome.storage.local`, and if the popup is open, tells it to
  refresh into the signed-in state.
- The website tab shows "You're signed in — you can close this tab" and can
  auto-close after ~2 seconds (`window.close()`; falls back to leaving the
  message up if the browser blocks the auto-close).

**Extension ID stability:** unpacked extensions get a random ID per install,
which would break `externally_connectable` targeting and require updating
the website's extension ID constant every time it's reloaded during
development. Fix: generate a fixed RSA keypair and add the public key to
`manifest.json`'s `"key"` field. This pins the extension's ID permanently
across unpacked loads and eventual Chrome Web Store publishing.

**Token refresh:** Supabase access tokens expire after about an hour. Before
each conversion, the extension checks `expires_at`; if expired or close to
expiring, it calls Supabase's
`POST {SUPABASE_URL}/auth/v1/token?grant_type=refresh_token` directly with
the stored `refresh_token` and the anon key (no website round-trip needed),
and updates `chrome.storage.local` with the new tokens.

**Sign-out:** a "Sign out" link/button in the popup clears
`chrome.storage.local` and returns to the sign-in screen.

### 2. Quota enforcement (backend)

- `/convert` currently authenticates the user via `_verify_supabase_token`
  and then proceeds straight to fetching/converting. Add a check
  immediately after authentication, before any fetch/Gemini/TTS work:
  - Query the `conversions` table (already has `user_id`, `created_at`) for
    `COUNT(*) WHERE user_id = :user_id AND created_at >= :start_of_today_utc`.
  - If the count is `>= 10`, return
    `jsonify({"error": "daily_limit_reached", "used": count, "limit": 10}), 429`
    without doing any expensive work.
  - Otherwise proceed as today, and include
    `"conversions_used_today": count + 1, "daily_limit": 10` in the success
    response (count + 1 because this conversion is about to be logged).
- This applies uniformly to both the website and the extension since both
  call the same endpoint and log to the same table — no source-tagging
  needed.

### 3. Upsell / limit messaging (frontend)

- Both the website and extension check for the `429` /
  `daily_limit_reached` response and display, in their existing error
  display areas (`.error-msg` on the website, `.error` div in the
  extension):

  ```
  You've used all 10 free conversions today.
  ```

- Plain text only — no button, no link, no `$5` messaging. Any future
  upsell/payment UI is a separate project.

### 4. Fixing the extension's conversion call

`popup.js` needs to be rewritten to match the real API contract:

- `doConvert(text, suffix)` currently `fetch`es a non-existent
  `/api/convert` and calls `res.blob()`. Replace with:
  - `POST {API}/convert` with header `Authorization: Bearer <access_token>`
    (pulled from `chrome.storage.local`, refreshing first if needed).
  - Body: `{ input_type: 'url' | 'manual', url, text, slug, voice, lang }`
    matching `api/index.py:1001-1034`. For the "manual" (pasted text) path,
    a `slug` is required by the backend — the extension will auto-generate
    one (e.g. from a timestamp) since there's no filename field in the
    popup UI.
  - Parse the JSON response, decode `audio_base64` into a blob URL for the
    `<audio>` element and download link (instead of using `res.blob()`
    directly).
  - On `429` with `daily_limit_reached`, show the plain limit message
    instead of a generic error.
  - On `401`, treat as session expired: clear stored session, show the
    sign-in screen.
- Remove the now-obsolete `convertUrl()` call to a separate
  `/api/fetch-url` endpoint — URL fetching happens server-side inside
  `/convert` itself (`input_type: 'url'`).
- Remove the `sendFeedback()` call to `/api/feedback`, which also doesn't
  exist on the backend. (Not part of this design's goals — flagged here so
  it isn't silently left broken. Default to hiding the feedback box for now
  unless a real endpoint is added.)

### 5. End-to-end flow

1. Popup opens, no session found → sign-in screen shown.
2. User clicks "Sign in" → website tab opens with `?ext_signin=1` →
   completes Google OAuth → website messages the session to the extension
   → extension stores it, tab shows a confirmation and closes.
3. User reopens the popup → session found → converter UI shown.
4. User converts → extension refreshes the token if needed → calls
   `POST /convert` with the Bearer token and correct payload → gets back
   `audio_base64` + `conversions_used_today`, or a `429` limit response.
5. Limit hit → plain "You've used all 10 free conversions today." message
   shown, no conversion attempted.
6. Sign-out clears the stored session and returns to the sign-in screen.

## Error handling

| Condition | Behavior |
|---|---|
| No session in `chrome.storage.local` | Show sign-in screen |
| Access token expired | Silently refresh via Supabase refresh endpoint before the request |
| Refresh token invalid/expired | Clear storage, show sign-in screen |
| `429 daily_limit_reached` | Show plain limit message, no retry |
| `401` from `/convert` (e.g. token revoked) | Clear storage, show sign-in screen |
| Other `4xx/5xx` from `/convert` | Show the server's `error` message in the existing error div, as today |

## Testing approach

- Manual testing only (no automated test suite exists for this project):
  1. Load the extension unpacked, confirm the sign-in screen appears with
     no stored session.
  2. Complete sign-in via the website tab, confirm the extension picks up
     the session and shows the converter UI.
  3. Convert a blog URL and pasted text; confirm real audio is returned and
     playable/downloadable.
  4. Manually insert 10 rows into `conversions` for the test user (or
     convert 10 times) and confirm the 11th attempt shows the limit message
     without hitting Gemini/TTS.
  5. Confirm sign-out clears the session and returns to the sign-in screen.
  6. Reload the extension (simulating a new unpacked install) and confirm
     the pinned `"key"` in `manifest.json` keeps the same extension ID, so
     `externally_connectable` still works.
