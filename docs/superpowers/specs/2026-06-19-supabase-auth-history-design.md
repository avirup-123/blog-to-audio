# Supabase Auth + Conversion History — Design Spec

Date: 2026-06-19

## Goal

Add Google login (via Supabase Auth) to the Text to Audio Online tool, gating the converter behind login, and persist a history of each user's conversions with Row Level Security so users only ever see their own rows.

## Supabase Project

- Project URL: `https://pkaeridjackeiggllsxs.supabase.co`
- Keys stored as Vercel environment variables (not committed to code):
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY` (public, used in frontend JS)
  - `SUPABASE_SERVICE_KEY` (secret, backend-only, used to verify JWTs and insert rows bypassing RLS safely since we trust the verified `user_id`)
- Google OAuth provider enabled in Supabase Authentication → Providers, with Site URL set to `https://text-to-audio-online.vercel.app`.

## Architecture

The existing single-file Vercel app (`api/index.py`) keeps its current structure. Additions:

1. **Frontend**: Supabase JS client (loaded via CDN `<script>` tag, no build step) handles:
   - Checking session state on load
   - "Sign in with Google" button → `supabase.auth.signInWithOAuth({ provider: 'google' })`
   - "Sign out" button → `supabase.auth.signOut()`
   - Gating the converter UI: if no session, show only the sign-in screen; if session exists, show the converter + a "History" tab
   - Attaching `Authorization: Bearer <access_token>` header on `/convert` fetch calls
   - Fetching conversion history directly from Supabase via the JS client (`supabase.from('conversions').select()`), relying on RLS — no new backend route needed for reads

2. **Backend** (`api/index.py`):
   - Token verification: backend calls Supabase's REST `GET /auth/v1/user` endpoint with the access token on each `/convert` request to confirm the session is valid and retrieve the `user_id`. This adds one small network round-trip per conversion but avoids managing an extra JWT secret.
   - `/convert` route changes:
     - Require `Authorization: Bearer <token>` header
     - Call Supabase to verify the token → extract `user_id`
     - If missing/invalid → 401 JSON error, frontend redirects to sign-in
     - After successful conversion, insert a row into `conversions` using the `supabase-py` client with the service key (server-side, bypasses RLS by design since we've already verified the user_id ourselves)
   - New dependency: `supabase` (supabase-py)

## Database Schema

```sql
create table conversions (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references auth.users(id) not null,
  input_source text not null,        -- "URL: https://..." or "Pasted text"
  source_snippet text,               -- first 100 chars of the input for display
  language text not null,             -- "hi", "en", etc.
  voice text not null,                -- "hi-IN-SwaraNeural"
  word_count integer not null,
  condensed boolean default false,
  translated boolean default false,
  estimated_duration text not null,   -- "3m 24s"
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

No update/delete policies — history is append-only and immutable from the client's perspective.

## Auth Flow

1. Page loads → Supabase JS checks for an existing session (handles OAuth redirect callback automatically)
2. Not logged in → show only a centered "Sign in with Google" card; hide tabs/converter/FAQ
3. User clicks sign in → Google OAuth popup/redirect → returns to site with active session
4. Logged in → show header with user email + "Sign out", show converter tabs (URL / Paste Text / History)
5. On convert: frontend sends `Authorization: Bearer <access_token>`; backend verifies JWT, runs conversion, inserts history row, returns audio
6. History tab: frontend queries Supabase directly (`select * from conversions order by created_at desc`), RLS ensures only the user's own rows return

## Error Handling

- Invalid/expired JWT on `/convert` → 401 with `{"error": "Please sign in again"}`; frontend catches this and shows the sign-in screen
- Supabase insert failure (e.g., network blip) → log server-side, but still return the generated audio to the user (history logging must never block the core conversion feature)

## UI Changes

- Header bar: user email + Sign Out button (only visible when logged in)
- Centered sign-in card replacing the whole converter section when logged out
- New "History" tab next to "From URL" / "Paste Text", rendering a simple table: Date | Source | Language | Voice | Duration

## Scope Boundaries

- No password/email auth — Google only, per user's existing request
- No audio re-download from history (log-only, per user's choice)
- No admin view — every user only ever sees their own data, no exceptions
