# React + FastAPI Migration — Roadmap and Slice 0 (Foundation) Design

**Date:** 2026-09-25
**Status:** Draft for review

## Goal

Move the Worship Service Builder off Streamlit to a Next.js (React) frontend and a
FastAPI backend, reusing the existing Python domain code. Motivations, in equal
weight: a polished mobile-friendly UI, a foundation for a real multi-church
product, and a conventional stack that doubles as working-group demo material.

## Context

- Starting point is the multi-church branch `claude/multi-user-app-support-edd5eb`
  (SQLAlchemy + Supabase Postgres, Streamlit OIDC login, church tenancy, ~30 test
  files), which is merged into `main` first.
- Only one real tester exists. No parallel-run requirement beyond keeping their
  data; switch over whenever parity is reached.
- Budget: ~$5–10/month for an always-on backend.

## Decisions

| Topic | Decision |
|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind, shadcn/ui, mobile-first |
| Backend | FastAPI wrapping existing modules (`repos/`, `tenancy.py`, `auth.py`, `worship_service.py`, `vanderbilt_lectionary.py`, `scripture_fetcher.py`, `google_oauth.py`, python-docx export) |
| Auth | Supabase Auth, Google provider only |
| Database | Existing Supabase Postgres; **no schema changes** in slice 0 |
| Hosting | Frontend on Vercel; backend on Railway (always-on); Supabase unchanged |
| Repo | Monorepo: `backend/` and `frontend/` |
| Migration strategy | Vertical slices; Streamlit stays until the final slice |

## Architecture

```
Browser ──► Next.js (Vercel)
              │  Supabase Auth (Google) → access token (JWT)
              │  API calls: Authorization: Bearer <jwt>, X-Church-Id: <uuid>
              ▼
          FastAPI (Railway)
              │  get_current_user: verify JWT → upsert_from_claims → user_id
              │  require_church:   validate_active_church(church_id, user_id) → role
              │  thin routes → existing domain modules
              ▼
          Supabase Postgres (existing tables)
```

Invariants:

1. Secrets (OpenAI, Google client secret, Gmail tokens, DB URL) exist only on the
   backend.
2. The backend never trusts a client-supplied church id; membership and role are
   re-derived from the database on every request via `validate_active_church`.
3. Routes stay thin. Domain logic lives in existing tested modules; Streamlit
   coupling is extracted from them only as each slice needs it.

## Roadmap

Each slice gets its own spec → plan → implementation cycle. This document
specifies slice 0 in detail; later slices are listed for sequencing only.

0. **Foundation** — merge, restructure, auth, tenancy guard, `/me`, deploys,
   signed-in shell with church switcher. *(this spec)*
1. **Onboarding** — create a church (seeded hymnal) / join by invite.
2. **Service Builder: readings** — date picker, lectionary lookup, scripture text,
   OT/NT selection.
3. **Service Builder: hymns** — hymnal list, scripture-matched suggestions,
   opening/response/closing picks, recent-usage exclusion.
4. **Service Builder: liturgy** — element selection, custom elements, OpenAI
   generation, preview/edit.
5. **Output** — Word export (bulletin + pastor copies), Gmail connect + send,
   service archive (save/load).
6. **Settings** — profile, contacts, hymns, liturgy prompts, members, invites,
   danger zone.
7. **Cutover** — delete Streamlit, its dependencies, the root `app.py`,
   `streamlit_views/`, `streamlit_auth.py`, and `streamlit_tenancy.py`.

## Slice 0 — Foundation

### 0.1 Merge

Merge `claude/multi-user-app-support-edd5eb` into `main` via PR. Its test suite
must pass on `main` before any further work.

### 0.2 Repository restructure

```
backend/
  api/                 # new: main.py, deps.py, errors.py, routes/
  db/  repos/          # moved
  tenancy.py auth.py worship_service.py vanderbilt_lectionary.py
  scripture_fetcher.py google_oauth.py ... (all current Python modules)
  tests/               # moved, plus new api tests
  requirements.txt
  .env.example
frontend/
  (Next.js app)
  .env.example
app.py                 # Streamlit entry, stays at root; adds backend/ to sys.path
streamlit_views/       # current views/ (Streamlit settings UI)
streamlit_auth.py      # Streamlit helpers split out of auth.py
streamlit_tenancy.py   # Streamlit helpers split out of tenancy.py
requirements.txt       # "-r backend/requirements.txt" + streamlit[auth]
```

- Moves use `git mv` to preserve history.
- `streamlit` is removed from `backend/requirements.txt`. Today four modules
  import it: `app.py`, `views/settings.py`, `auth.py`, and `tenancy.py`. The first
  two are Streamlit UI and stay at the repo root with the Streamlit app (`app.py`,
  `views/` renamed to `streamlit_views/`). `auth.py` and `tenancy.py`
  are needed by the API, so their Streamlit-specific helpers (`require_login`,
  `current_user_id`, `do_logout`, `require_active_church`, session-state key
  lists) move to root-level `streamlit_auth.py` / `streamlit_tenancy.py`, leaving
  `backend/auth.py` and `backend/tenancy.py` free of Streamlit imports. A test
  asserts that importing `api.main` does not import `streamlit`.
- The Streamlit entry keeps its name and location (`app.py` at the root) because
  Streamlit Community Cloud cannot change an existing app's main file path in
  place; the live Streamlit apps therefore need no settings change.
- Streamlit-only tests move to a root `streamlit_tests/` folder; a root
  `pytest.ini` runs `backend/tests` and `streamlit_tests` together.
- `.github/workflows/keepalive.yml` and `backup.yml` are updated for new paths.

### 0.3 Authentication — `get_current_user`

- Frontend uses `@supabase/ssr`; login redirects through Supabase → Google →
  `/auth/callback`; session stored in cookies.
- Supabase project: Google provider enabled; email/password, magic link, and all
  other providers disabled.
- Backend dependency `get_current_user`:
  1. Read `Authorization: Bearer <jwt>`; missing → 401.
  2. Verify with PyJWT against Supabase JWKS
     (`{SUPABASE_URL}/auth/v1/.well-known/jwks.json`), cached in-process with
     refresh on unknown `kid`. Require valid signature, unexpired `exp`, and
     `aud == "authenticated"`. Any failure → 401.
  3. Require `app_metadata.provider == "google"`; otherwise 401. This is
     enforced in code, not only in Supabase settings, because users are keyed by
     email and a non-Google signup with someone else's email would otherwise
     take over their account.
  4. Map claims to the shape `upsert_from_claims` expects:
     `email` ← `email`; `sub` ← `user_metadata.provider_id` (the Google subject,
     preserving the meaning of the existing `google_sub` column); `name` ←
     `user_metadata.full_name`; `picture` ← `user_metadata.avatar_url`.
  5. Call `upsert_from_claims` and return the user id.
- JWKS unreachable (and no cached key) → 503, never a pass-through.

### 0.4 Tenancy — `require_church` / `require_admin`

- `require_church` depends on `get_current_user`, reads `X-Church-Id`, calls
  `validate_active_church(church_id, user_id)`. Missing, malformed, soft-deleted,
  or non-member → 403. Returns `{church_id, name, role}`.
- `require_admin` additionally requires `tenancy.is_admin(role)`; otherwise 403.
  (Defined now; first used in slice 6.)

### 0.5 Endpoints

| Method/Path | Guard | Response |
|---|---|---|
| `GET /health` | none | `{"ok": true}` |
| `GET /me` | user | `{"user": {id, email, name, picture}, "churches": [{id, name, role}]}` |
| `GET /church` | user + church | `{id, name, role}` |

`/me` uses the existing `repos.churches.list_user_churches`.

### 0.6 Errors

- Uniform body: `{"error": {"code": "<slug>", "message": "<human text>"}}`.
- 401 `unauthenticated`, 403 `forbidden`, 422 `invalid_request`, 503
  `auth_unavailable`, 500 `internal_error`.
- 500s are logged server-side with stack trace; the client gets a generic message.
- CORS: allow only origins in `CORS_ORIGINS` (comma-separated); credentials not
  needed (bearer tokens, not cookies, go to the API).

### 0.7 Frontend

- `/login`: "Sign in with Google" button.
- `/auth/callback`: Supabase code exchange, then redirect to `/`.
- Protected layout: middleware redirects unauthenticated users to `/login`.
- `lib/api.ts`: fetch wrapper adding `Authorization` and `X-Church-Id`; on 401 →
  `/login`; on 403 → clear stored church and show the switcher; other errors →
  toast.
- `/`: app shell (header with active church name, user menu with Log out),
  church switcher populated from `/me`, active church id persisted in
  `localStorage`. Placeholder cards: "Service Builder — coming in slice 2".
  Zero churches → "Onboarding coming in slice 1".
- Mobile-first layout; verified at 375px width and desktop.

### 0.8 Configuration

Backend (Railway env): `DATABASE_URL`, `SUPABASE_URL`, `CORS_ORIGINS`, plus the
existing `OPENAI_API_KEY`, `OPENAI_MODEL`, `GOOGLE_CLIENT_ID`,
`GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` (unused until slice 5, but
carried over).

Frontend (Vercel env): `NEXT_PUBLIC_SUPABASE_URL`,
`NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL`.

Both folders get an `.env.example` listing names without values. No secrets are
committed.

### 0.9 Deployment

| Component | Host | Settings |
|---|---|---|
| `frontend/` | Vercel | Root dir `frontend/`; production deploys from `main` |
| `backend/` | Railway | Root dir `backend/`; start `uvicorn api.main:app --host 0.0.0.0 --port $PORT`; health check `/health` |
| Auth + DB | Supabase | Add the Vercel production URL and `http://localhost:3000` to allowed redirect URLs |
| Streamlit | Streamlit Cloud | Unchanged (entry is still `app.py`) |

### 0.10 Testing

- **Backend (pytest):** JWTs signed with a locally generated RSA key; JWKS fetch
  is overridden to return its public key. Cases: valid token; expired; wrong
  audience; non-Google provider; bad signature; missing header; JWKS
  unavailable → 503. `/me` returns only the caller's churches. `/church` returns
  403 for a church the caller is not a member of (cross-church isolation) and
  for a malformed id. All pre-existing tests pass after the move.
- **Frontend:** Vitest unit tests for `lib/api.ts` and `lib/church.ts`;
  `tsc --noEmit`, ESLint, and `next build` must pass.
- **CI:** new GitHub Actions workflow running backend tests and frontend checks
  on every PR.
- **Manual verification** on deployed URLs: sign in on phone and desktop, see
  the tester's church, switch churches, log out, confirm Streamlit still works.

### 0.11 Out of scope for slice 0

Onboarding, any Service Builder feature, settings, Gmail connect/send, custom
domains, browser end-to-end tests, and removing Streamlit.

## Success criteria for slice 0

1. `main` contains the merged multi-church code with all tests passing.
2. The tester can sign in with Google on the Vercel URL and see their church.
3. A request with another church's id returns 403 (covered by automated test).
4. Streamlit Cloud continues to work against the same database.
5. CI runs on PRs and is green.
