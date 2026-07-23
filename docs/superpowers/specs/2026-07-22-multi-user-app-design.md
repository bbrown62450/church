# Multi-Church Support — Design Spec

**Date:** 2026-07-22
**Status:** Approved (design); ready for implementation planning
**App:** Worship Service Builder (Streamlit)

## Summary

Turn the single-tenant Worship Service Builder into a multi-church application.
Multiple churches use one deployment, each fully isolated: their own hymnal,
service archive, contacts, and members. People sign in with Google; anyone can
create a new church (becoming its owner) or join an existing one by invite.
Church content moves from Notion + local JSON files into one Postgres database
(Supabase in production, SQLite for local development).

This work also fixes four security bugs that exist in the app today and would
become dangerous once multiple churches share it.

## Goals

- **User registration pathway** — first Google sign-in creates an account; a
  person with no church is guided to create one or join by invite.
- **Multiple logins** — framework-managed, cookie-backed sessions so many people
  use the app concurrently, each as themselves.
- **Configurable email destination** — per-church contacts managed on a Settings
  page; the hardcoded default recipients are removed.
- **True multi-tenancy** — every church's data is isolated and access is
  verified server-side on every request.

## Non-Goals (YAGNI)

- Payment/billing, per-church subscription tiers.
- Per-church OpenAI or Notion keys (a single shared `OPENAI_API_KEY` serves all
  churches; Notion is removed as a runtime dependency).
- Granular role systems beyond owner/admin/member.
- A full REST/API backend or SPA frontend — the app stays Streamlit.
- Super-admin approval workflow for new churches — onboarding is self-serve.

## Key Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Tenancy | Multiple churches, fully isolated |
| Auth | Sign in with Google (Streamlit native OIDC) |
| Storage | App database — Supabase Postgres (prod), SQLite (local dev) |
| Hosting | Streamlit Community Cloud + Supabase |
| Onboarding | Self-serve church creation; joining requires an invite |
| Hymn library | Every new church starts with a copy of a shared starter hymnal |
| AI costs | Single shared app `OPENAI_API_KEY` |
| Roles | owner / admin / member per church |

---

## 1. Authentication & Identity

### Sign-in (identity)

Use Streamlit's native OIDC authentication: `st.login()`, `st.user`,
`st.logout()`, with Google as the provider. This provides cookie-backed sessions
out of the box and removes the need for any hand-rolled login/session code. The
existing shared `APP_PASSWORD` gate is **removed**. Registration is implicit:
the first Google sign-in creates the user record.

**Login uses only `openid` + `email` scopes.** These are non-sensitive, so login
works for anyone immediately with no Google verification process.

Configuration lives in `.streamlit/secrets.toml` under `[auth]`:

```toml
[auth]
redirect_uri = "https://<app>/oauth2callback"   # localhost:8501/oauth2callback in dev
cookie_secret = "<strong random string>"
client_id = "<google client id>"
client_secret = "<google client secret>"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

- `redirect_uri` **must** end in `/oauth2callback` and must be registered on the
  Google OAuth client. It differs between dev (`localhost:8501`) and prod
  (Streamlit Cloud URL), so each environment needs its own secret value.
- The identity cookie lasts **30 days** and is **not configurable**.
- `st.logout()` clears only the app's local cookie, **not** the Google session;
  a later `st.login()` may silently re-authenticate. Acceptable for this app.
- Use `st.user` (GA in Streamlit ≥ 1.45), **not** the removed
  `st.experimental_user`.

`st.user` exposes: `is_logged_in`, `email`, `email_verified`, `name`,
`picture`, `sub` (stable Google user id), and standard OIDC claims. The user
record is keyed on a **normalized (lower-cased) email**; `sub` is stored as a
stable secondary identifier.

### Sending email (separate, opt-in permission)

Sending a bulletin needs the **sensitive** `gmail.send` scope, which is subject
to Google verification limits (100 test users until verified). We therefore keep
this **separate and opt-in**: only people who actually email the bulletin ever
grant it.

- Identity comes from `st.login` (above). The **`gmail.send` grant** keeps the
  existing `google_oauth.py` authorization-code flow, invoked by an explicit
  **"Connect your Gmail"** button.
- Because `st.login` already establishes identity, the manual `gmail.send` flow
  no longer needs `openid`/`userinfo.email` — the connected sender is always the
  logged-in `st.user.email`, verified server-side.
- **Removed:** the `?gmail=<email>` URL-parameter mechanism (a spoofing bug —
  see §4) and the legacy shared SMTP App Password fallback
  (`GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD`).

### Google OAuth client configuration

By default, a **single** Google OAuth web-application client backs both flows,
with **two** registered redirect URIs (each must match exactly — scheme, host,
path, trailing slash). Using a **dedicated** client for `gmail.send` is a safer
alternative left open for implementation (see §6 Open Verification Items):

1. `https://<app>/oauth2callback` — for `st.login` (handled internally by
   Streamlit; never reaches app code).
2. `https://<app>/` (app root) — for the manual `gmail.send` flow.

The manual flow's redirect target **must stay at the app root** — never
`/oauth2callback`, or it collides with Streamlit's internal handler. To avoid the
handler grabbing a login `?code=`, the manual redirect carries an explicit marker
(e.g. `?gmail_oauth=1`) and `_handle_gmail_oauth_callback()` processes a `?code=`
**only** when that marker is present.

> **Verification step (required during implementation):** enabling `[auth]`
> auto-enables Streamlit's CORS/XSRF protection. The manual flow's return to the
> app root with query params is a top-level GET and is expected to work, but this
> is not documented as guaranteed. Test the full Connect-Gmail round-trip on the
> deployed URL before relying on it.

---

## 2. Data Model & Multi-Tenancy

### Storage layer

All church content moves into a relational database accessed via **SQLAlchemy
2.x**, selected by a `DATABASE_URL` environment variable:

- **Production:** Supabase Postgres.
- **Local development:** SQLite.

To keep both backends working from one set of models:

- Use **generic SQLAlchemy types** — `sqlalchemy.Uuid`, `sqlalchemy.JSON` — never
  `postgresql.UUID`/`JSONB`.
- Use **Python-side defaults** — `default=uuid.uuid4`,
  `default=lambda: datetime.now(timezone.utc)` — never server defaults like
  `gen_random_uuid()`/`now()` (they don't exist in SQLite).
- Timestamps are stored as UTC (`timestamptz` in Postgres). Calendar dates
  (`service_date`) are stored as `DATE`, distinct from `saved_at`.
- Cache the engine with `@st.cache_resource`; set `pool_pre_ping=True` and a
  modest `pool_recycle` so connections retired by the Supabase pooler don't
  surface as stale-connection errors.

The existing modules (`service_archive.py`, `hymn_usage.py`, `email_contacts.py`,
and the hymn data source) are rewritten against the database behind a small data
layer. Their public functions gain a `church_id` parameter (and `user_id` where
authorship applies). Notion is removed as a **runtime** dependency; the Notion
client is used only by the one-time migration script (§3).

### The active-church guard (the core of tenancy)

The active church is kept in `st.session_state`, but it is **untrusted input**.
A single `require_active_church()` runs at the top of every page render and:

1. Reads the candidate `active_church_id` from session (and any `?church=` param)
   as untrusted.
2. `SELECT role FROM memberships WHERE user_id = :me AND church_id = :active`,
   and confirms the church is not soft-deleted.
3. If no matching membership → discard the value; fall back to the user's real
   membership list, or the zero-church empty state.
4. Re-derives the **role** for this request from that query — never from a
   session-cached role.
5. Passes the **validated** `church_id` into every church-scoped query.

No church-scoped code path runs without passing through this guard. Admin-only
actions re-check `role IN ('owner','admin')` at execution time, not just by
hiding UI.

### Tables

Foreign keys and `ON DELETE` behavior are explicit per table. Church content
cascades to the **church**, never to a user.

**`users`**
- `id` (uuid, pk), `email` (not null, **unique, normalized lower-case**),
  `google_sub` (unique), `name`, `picture`, `created_at`, `last_login_at`.

**`churches`**
- `id` (uuid, pk), `name` (not null), `timezone` (not null, e.g.
  `America/New_York` — drives "first Sunday of month" and the 12-week window),
  `settings` (JSON), `created_at`, `deleted_at` (nullable — **soft delete**).

**`memberships`**
- `church_id` (fk → churches, on delete cascade), `user_id` (fk → users, on
  delete cascade), `role` (not null, `CHECK role IN ('owner','admin','member')`),
  `created_at`.
- **Composite PK `(church_id, user_id)`** (no duplicate memberships) plus a
  **secondary index on `user_id`** (the per-request "my churches" lookup).
- Invariant: **a church always has ≥ 1 owner/admin.** The remove/demote/leave
  operations reject when they would drop the admin count to zero, enforced under
  a row lock (`SELECT ... FOR UPDATE`) so concurrent mutual-removal can't zero it.
- The creator is assigned `owner` and cannot be demoted/removed while last.

**`invites`**
- `id` (uuid, pk), `church_id` (fk → churches, on delete cascade), `code` (not
  null, unique — ≥ 128 bits from `secrets.token_urlsafe`), `email` (nullable;
  when set, `UNIQUE(church_id, email)` for pending), `role` (default `member`),
  `created_by` (fk → users, on delete set null), `created_at`, `expires_at` (not
  null, ~7 days), `revoked` (bool), `accepted_at` (nullable).
- Accept is a no-op if the user is already a member (relies on the membership
  unique constraint). Codes are single-church-scoped and revocable.

**`hymn_catalog`** (shared starter hymnal — the template)
- `id` (uuid, pk), `title`, `number`, `scripture_refs` (text), `topics`/`theme`,
  `hymnary_link`, `audio_url`, and any other enrichment fields from the current
  Notion hymn schema.
- A **separate table** (not null-`church_id` rows in `hymns`), so the template
  can never leak into a church-scoped query and a church's edits never mutate it.

**`hymns`** (per-church, editable)
- `id` (uuid, pk), `church_id` (not null, fk → churches, on delete cascade),
  same content columns as `hymn_catalog`.
- **Index `(church_id)`** (and `(church_id, number)` for number lookups).
- Seeded from `hymn_catalog` at church creation (see below).

**`services`** (archive)
- `id` (uuid, pk), `church_id` (not null, fk → churches, on delete cascade),
  `created_by` (fk → users, **on delete set null** — history survives the
  author leaving), `service_date` (DATE, nullable), `occasion`, `scriptures`
  (JSON), `hymns` (JSON — **denormalized title/number snapshot**, no FK to
  `hymns`), `liturgy` (JSON), `sermon_title`, `selected_ot_ref`,
  `selected_nt_ref`, `include_communion` (bool), `saved_at` (not null, timestamptz).
- **Index `(church_id, saved_at DESC)`** for the archive list.

**`hymn_usage`** (drives "exclude hymns used in last 12 weeks")
- `id` (uuid, pk), `church_id` (not null, fk → churches, on delete cascade),
  `service_date` (DATE), `hymn_number`, `hymn_title` (**denormalized**, no FK to
  `hymns`), `recorded_at`.
- **Index `(church_id, service_date)`**. Writes are idempotent per
  `(church_id, service_date, hymn_number, hymn_title)` so re-preparing a bulletin
  doesn't inflate the exclusion set. Read/write both filter by `church_id`.

**`contacts`** (configurable email destinations)
- `id` (uuid, pk), `church_id` (not null, fk → churches, on delete cascade),
  `name`, `email` (not null), `created_at`.

**`gmail_tokens`** (**user-scoped, not church-scoped**)
- `user_id` (fk → users, on delete cascade, **unique**), `refresh_token` (not
  null), `google_email`, `created_at`.
- A person connects Gmail once and can send in any church they belong to.
  Stored with restricted file/row access (see §4).

**`oauth_states`** (CSRF state for the gmail.send flow — survives the redirect)
- `state` (pk, not null, unique), `user_id` (fk → users, on delete cascade),
  `created_at`, `expires_at` (not null, short TTL). **Single-use:** deleted on
  callback.

### Church creation & the starter hymnal

Creating a church, in **one transaction**:

1. Insert the `churches` row (creator supplies name + timezone).
2. Insert the creator's `memberships` row with role `owner`.
3. `INSERT INTO hymns (church_id, ...) SELECT :new_church_id, ... FROM hymn_catalog`
   — seed the editable per-church hymnal synchronously.

Because seeding is atomic with creation, no admin ever sees a half-populated or
empty hymnal. Creation is idempotent (a retry does not double-seed).

**Trade-off documented:** each church owns an independent copy of the hymnal, so
later corrections to `hymn_catalog` do **not** propagate to existing churches
(matches the "each church edits freely" decision). If catalog-wide corrections
become important later, they are applied via a one-off migration script. Row
count (≈700 hymns × N churches) is well within Postgres limits at this scale;
the free-tier 500 MB ceiling and upgrade path are noted in §6.

### Lifecycle rules

- **Remove a member:** deletes only their `memberships` row. Church services,
  hymns, contacts, and usage are untouched; their authored `services.created_by`
  becomes null.
- **Zero-church user:** allowed to exist and log in; shown an empty state
  ("ask an admin to invite you, or create a church"). Never auto-assigned to a
  church, never auto-deleted (they may be re-invited by email). Their personal
  `gmail_tokens` persist.
- **Delete a church:** soft delete (`deleted_at`). Excluded from all queries;
  retained for a grace period; hard-purged later by a maintenance job. Pending
  invites are cascade-removed.

---

## 3. Data Migration (one-time)

Beau's existing data lives in **Notion** (hymns, archive, usage) and Streamlit
Cloud secrets — there is no local `data/` directory on this machine. The
migration script therefore reads from Notion (using the current Notion client)
and writes into the new database as the **founder church**, with Beau as
**owner**.

Steps:

1. **Founder user & church.** Create Beau's `users` row and a `churches` row;
   assign `owner`.
2. **Hymn catalog (top priority).** Read the enriched Notion hymn database (~700
   hymns, with scripture refs, themes, Hymnary links backfilled by
   `fill_from_hymnary.py`) into **`hymn_catalog`**, then seed a copy into the
   founder church's `hymns`. **Validation:** after import, a sample scripture
   lookup must return matches and enrichment fields must be populated; empty
   results are treated as a migration failure, not user error. Key hymns by
   `(number, normalized title)` so duplicate-title settings (e.g. multiple
   "Gloria") are not collapsed.
3. **Service archive.** Import Notion archive pages under the founder church.
   - **Known lossy source (confirmed):** Notion stored each liturgy as a single
     rich-text field truncated at **2000 chars**, so fully-generated bulletins
     were already truncated before this project. The script **detects** likely
     truncation (length ≈ 2000 and `json.loads` failure) and **flags** those
     rows in a migration report rather than silently importing `{}`. Liturgy
     text is AI-regenerable, so this is flag-and-continue, not a blocker.
   - `sermon_title` and `include_communion` are **not** Notion properties — they
     are embedded in the liturgy JSON meta (`_sermon_title`,
     `_include_communion`). Extract them from the parsed JSON; handle the
     truncated case where they're gone.
   - Carry the original `saved_at` through verbatim (don't stamp import time) so
     archive ordering is preserved. Tolerate null `service_date`.
4. **Hymn usage.** Import under the founder church, deduped by
   `(church_id, service_date, hymn_number, hymn_title)`.
5. **Contacts.** Migrate the current saved contacts to the **founder church
   only**. The hardcoded `DEFAULT_CONTACTS` (real personal/office emails) are
   **removed from the code** so no other church ever inherits them.
6. **Gmail tokens.** **Not migrated.** Users click "Connect your Gmail" once
   after launch (tokens are bound to the OAuth client anyway; reconnecting is one
   click and avoids importing dead credentials).

The script is **re-runnable to convergence** (safe after a partial failure),
using the stable dedupe keys above, and prints a summary report (counts +
flagged rows).

---

## 4. Security

Four issues below exist in the **current** app and are fixed as part of this work
because multi-church sharing amplifies them.

1. **Sender spoofing (existing).** Today the active sender is read from
   `?gmail=<email>` / session and only checked for "a token exists," letting
   anyone send as anyone who ever connected. **Fix:** delete all reads of
   `?gmail=`; derive the sender solely from `st.user.email`; assert
   `is_connected(st.user.email)`; add a defense-in-depth check in
   `google_oauth.send_email` that the sender matches the authenticated caller.
2. **Cross-church data access / IDOR (existing, critical under multi-tenancy).**
   `get_service(id)` returns any service by id with no owner check. **Fix:** every
   read/list/update/delete filters by the verified `church_id`; ids outside the
   caller's church return "not found" (avoid enumeration).
3. **OAuth CSRF state not enforced (existing).** The expected `state` lives in
   `session_state`, which doesn't survive the OAuth redirect, so the check is
   skipped. **Fix:** persist state in `oauth_states` (single-use, short TTL,
   bound to the logged-in user); require an exact match on callback and reject
   when absent — never treat missing state as pass.
4. **Token exchange before authentication (existing).** The callback exchanges a
   code and writes a token before any login gate. **Fix:** require a valid
   `st.login` session before processing the gmail callback; refuse to save a
   token unless the Google-returned email matches the logged-in user.

Additional controls:

- **Invite codes:** ≥ 128-bit `secrets.token_urlsafe`, single-church-scoped,
  expiring (~7 days), revocable, single-use where email-bound; no enumerable
  error/timing differences.
- **Authorization:** `church_id` is always derived server-side from the caller's
  membership, never from a query param, form field, or client-set session value.
  Admin actions re-check role server-side on every action.
- **Gmail refresh tokens:** stored with restricted access; `data/` remains
  gitignored (verify). Prefer a dedicated OAuth client for `gmail.send` if
  practical; drop `include_granted_scopes` unless incremental auth is needed.
- **Query-param hygiene:** on the first line of `main()`, read `?invite=` /
  `?church=` into `session_state` before any gate or OAuth handling; replace
  blanket `st.query_params.clear()` with targeted deletion of only the OAuth
  keys, so invite/church params survive the login and Gmail round-trips.

---

## 5. Pages, Roles & Onboarding

### Pages (Streamlit `st.navigation` / `st.Page`)

- **Service Builder** — the existing screen; unchanged in feel. Church-scoped
  data and the church switcher are the only visible additions.
- **Settings** — church profile (name, timezone); **contacts** CRUD (the
  configurable email destinations); **members & invites** management. Admin-gated
  sections re-check role server-side.

### Roles

- **owner** — everything an admin can do; cannot be removed/demoted while last;
  can transfer ownership and soft-delete the church.
- **admin** — invite/remove members, change member roles, edit church settings &
  contacts.
- **member** — build services, generate liturgy, send from their own connected
  Gmail, edit hymns, manage the archive.

### Onboarding

- A signed-in user **with no membership** sees a choice: **Create a church**
  (become owner; supply name + timezone) or **Enter an invite code / open an
  invite link** (`?invite=CODE`, captured on first render) to join as a member.
- A **church switcher** in the sidebar appears for users in more than one church.
  Switching runs an explicit reset that pops **all** church-scoped session state —
  `_cached_all_hymns`, `_hymn_title_to_info`, `_cached_saved_services`,
  `scripture_hymns`, `scripture_refs_used`, `opening`/`response`/`closing` (and
  the manual `*_man` keys), `editing_service_id`, `load_service_id`, `liturgy`
  and `liturgy_*`, `include_communion`, `custom_elements` — so a stale
  previous-church read is impossible. Caches are keyed by `church_id`.
- **Selectbox safety:** every hymn selectbox guards its stored session value —
  if the value isn't in the new church's options, it resets to `""` instead of
  raising `StreamlitAPIException` (a hard crash today when switching churches).
- **Empty state:** a member whose church has hymns sees the normal UI (the
  starter hymnal guarantees non-empty at creation). Any genuinely empty-hymnal
  case shows an explicit message, not a silent swap to free-text inputs.

---

## 6. Operations & Dependencies

### Supabase / hosting

- **Connection string:** use the Supabase **session pooler** host
  (`aws-0-<region>.pooler.supabase.com`, port 5432, user
  `postgres.<project-ref>`) — **not** the direct `db.<ref>.supabase.co` host,
  which is IPv6-only on the free tier and unreachable from Streamlit Community
  Cloud's IPv4-only egress. Store as `DATABASE_URL` in Streamlit secrets.
- **Keep-alive (required):** the free Supabase project pauses after 7 days idle.
  Add a scheduled lightweight query (e.g. a GitHub Actions daily cron) so the
  first visitor each week doesn't hit a paused/cold database.
- **Backups (required):** the free tier retains **no** backups. Add a scheduled
  `pg_dump`/export job. Do not treat Supabase Free as durable on its own.
- **Limits & upgrade path:** free tier gives 500 MB DB, ample connections for a
  handful of churches. Document that scaling to many churches may require the paid
  tier (which also enables direct IPv4 connections).

### Dependencies (`requirements.txt`)

- `streamlit[auth]>=1.45.0` (native `st.user` GA; pulls in `Authlib>=1.3.2`).
- `SQLAlchemy>=2.0`.
- `psycopg2-binary` (Postgres driver; note psycopg2 avoids the transaction-pooler
  prepared-statement pitfalls).
- **Remove** the Notion client from runtime requirements (migration script may
  import it separately / as a dev dependency).

### Secrets summary

- `[auth]` block: `redirect_uri`, `cookie_secret`, `client_id`, `client_secret`,
  `server_metadata_url` (per-environment `redirect_uri`).
- `DATABASE_URL` (session-pooler URL).
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_OAUTH_REDIRECT_URI`
  (app-root) for the `gmail.send` flow.
- `OPENAI_API_KEY` (shared, unchanged).
- **Removed:** `APP_PASSWORD`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`,
  `NOTION_*` (runtime).

---

## Testing Strategy

- **Tenancy isolation (highest priority):** Church A's services, hymns, usage,
  and contacts are never readable/writable from Church B. Test the IDOR path
  directly (attempt `get_service` on another church's id → not found). Test that
  `require_active_church()` rejects a forged `?church=`/session value.
- **Usage scoping:** Church A's recent-hymn exclusions don't affect Church B's
  dropdowns.
- **Lifecycle invariants:** last-admin removal/demotion/leave is rejected;
  concurrent mutual-removal cannot zero admins; removing a member preserves
  church content and nulls authorship; soft-deleted churches disappear from all
  queries.
- **Church switching:** switching resets caches and never crashes a selectbox;
  no previous-church data bleeds through.
- **Onboarding & invites:** create-church seeds the hymnal atomically; invite
  link survives login + Gmail-connect round-trips; expired/revoked codes fail
  cleanly; accepting when already a member is a no-op.
- **Auth/OAuth:** sender is always the logged-in user (spoofing attempt via
  `?gmail=` fails); gmail callback rejects missing/invalid `state`; token save
  requires an authenticated session and matching email; the two OAuth flows don't
  collide on the deployed URL (manual verification step).
- **Backend portability:** the model/data layer runs on both SQLite (dev) and
  Postgres (prod).
- **Migration:** re-running is idempotent; truncated-liturgy rows are flagged;
  `saved_at` ordering preserved; contacts land only in the founder church;
  hymn enrichment validated.

## Open Verification Items (resolve during implementation)

1. Confirm on the **deployed** Streamlit Cloud URL that the manual `gmail.send`
   return to app root (with `[auth]` CORS/XSRF enabled) delivers `?code=` to app
   code as expected.
2. Confirm the exact enriched Notion hymn schema field names to map into
   `hymn_catalog`.
3. Decide whether to register a **dedicated** Google OAuth client for
   `gmail.send` vs. reuse the login client with two redirect URIs (spec allows
   either; dedicated is slightly safer).
