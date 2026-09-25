# Slice 1 — Onboarding and joining churches (with platform foundations) — Design

**Date:** 2026-09-25
**Status:** Draft  **Depends on:** slice 0 (done, live); the ops slice (identity fix §2.4, `db/upsert.py::insert_ignore`, `RequestIdMiddleware` + request-id contextvar + `UnhandledErrorMiddleware` §2.5, `redirect_slashes=False`, Data API lockdown §3.6 done by hand, Streamlit freeze §6.1)  **Size:** L — shipped as two PRs: **1a platform** (M, no new features) then **1b onboarding** (S–M)

**Consumed by:** slice 2 (layouts, `ChurchProvider`, `useApi`, query client, test harness, UI kit, `domain_errors.RateLimited`), 5b (`lib/storage.ts`, `safeInternalPath`, `lib/idempotency.ts` key tracker), 5a/6a (`Page`/`ItemList` schemas, idempotency store), 6a (`timezones.is_valid_timezone`, `TimezoneCombobox`), 6b (`invites.reusable`/`accepted_by`, accept semantics, `buildInviteUrl`, `useMembershipChanged`, `assert_church_isolated`).

References: foundations spec `2026-09-25-migration-foundations-design.md` (cited "F§n"); inventory `2026-09-25-streamlit-migration-inventory.md` (cited "inv §n"). File:line references are to the tree at commit `50fda65`.

F's "Amendments from slice specs" pass records this slice's rules in the foundations spec before implementation starts: F§1.2 (`PUBLIC` also lists FastAPI's `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc`), F§1.5 (`db_unavailable` 503, with `details.reason = "schema_behind"` for the readiness gate; `RateLimited` is the one 429 mechanism, always with `details.retry_after_seconds`), F§1.6 (a client key is rotated after any 4xx and after any body change, as in 5a and 5b), F§1.8 (`church_create` is a 3-per-minute burst bucket behind 1b's durable cap), F§3.3 (Railway's deploy health check is `/health/ready`) and F§7.2 (the Combobox pattern is built in slice 1). Where this spec cites those sections it means the amended text.

---

## Goal

1. Let any signed-in user **create a church** (becoming its owner, with a seeded hymnal) or **join one by invite**, both at first sign-in and at any later time from the church switcher (owner decision 9).
2. Make invite links work end to end: `https://<frontend>/join?code=…` survives Google sign-in, previews the church, and joins it. Single-use by default (owner decision 6); the link-creation UI is slice 6b.
3. Build the platform pieces F§7.2 assigns to slice 1 so every later slice only writes its feature: Alembic, the error/usecase/idempotency layer, guard and contract tests, the Postgres CI job, TanStack Query, the API client, the signed-in and church layouts, the UI kit, the Combobox pattern (F§4.9.5, first used by `TimezoneCombobox`) and the DOM test harness.

---

## Scope / Out of scope

### In scope

**1a — Platform (PR 1, no new features)**
- Alembic setup and revisions `0001_baseline` … `0004_invites_reusable`, the production stamping runbook (with its RLS precondition and the Railway config-file-path step), `backend/railway.toml` pre-deploy migration, `backend/db/schema_check.py` + `backend/scripts/schema_drift.py`, startup revision and RLS checks, the production readiness gate on a schema behind head, removal of `create_all` from the API lifespan, deletion of `backend/migrate_add_hymnal.py` (F§3, F§2.6 items 3–5).
- `backend/domain_errors.py`, `db/ids.py::as_uuid`, error body `fields`/`details`, Pydantic 422 field mapping, and the ops handoff code `db_unavailable` (503) in both registries (F§1.5, F§2.2; ops "Error code registry addition").
- `backend/usecases/` package (empty `__init__` plus `onboarding.py` in 1b).
- `backend/api/idempotency.py` (F§1.6).
- `test_route_guards.py`, `tests/api_helpers.py::assert_church_isolated`, the no-network autouse fixture, `pg_db` fixture and `postgres` marker, `test_openapi_contract.py` + `scripts/export_openapi.py`, `test_migrations.py`, extended `test_no_streamlit_in_core.py` (F§1.2, F§1.11, F§5.1).
- CI: `backend-postgres` job, whose service image is `postgres:<PG_MAJOR>` (the major in `backup.yml`; ops' `test_ops_workflows.py` already fails on a mismatch, so slice 1 adds no test of its own); frontend `gen:api` diff step (F§5.4).
- The Postgres re-run of the ops slice's concurrent first-request test (F§7.3).
- Frontend: TanStack Query client + keys + auth events, amended API client + `useApi` (`ApiError.requestId` from the body, falling back to the `X-Request-Id` header — ops handoff), `lib/storage.ts`, `lib/urls.ts`, route groups `(signed-in)` / `(church)`, `ChurchProvider` with keyed remount and hydration-safe `useStoredChurchId`, 403 fallback to the next church, `queryClient.clear()` on sign-out, a **stub `/welcome`** (the slice-0 "No church yet" card, so the zero-church redirect never lands on a 404 between the two merges), UI kit (F§4.8) with the `touch` button size, `react/no-danger` lint rule, Vitest `unit` + `dom` projects with Testing Library, `renderWithProviders`, `installFakeApi` (F§4.2, F§4.4, F§4.5, F§5.2).

**1b — Onboarding (PR 2)**
- `POST /churches` (with a per-user creation cap), `POST /invites/preview`, `POST /invites/accept`; `usecases/onboarding.py`; `timezones.py`; bulk hymnal seed.
- `/welcome` (Join and Create tabs; replaces the 1a stub), `/join?code=…`, `/login?next=…`, proxy `next` handling and `/join` as a public path, church switcher as a menu with **"Join or create a church…"** (F§4.1, F§4.3); `lib/idempotency.ts` key tracker for the create form.

### Inventory coverage (every in-scope current behavior)

| Inventory item | Current behavior (file:line) | Slice 1 outcome |
|---|---|---|
| A1 bootstrap / nav | `st.navigation`, sidebar, `init_db` via `st.cache_resource` (app.py:105-173, 325-362) | Shell = `(signed-in)` + `(church)` layouts and `AppHeader`. `create_all` leaves the API lifespan (Alembic owns schema). Nav items arrive with their slices (2+). |
| A2 login gate + upsert | `require_login` / `upsert_from_claims` (streamlit_auth.py:16-41; auth.py:23-60); API upsert every request (deps.py:55-76) | Race fix, cache and hourly `last_login_at` ship in **ops** (F§2.4). Slice 1 adds the Postgres re-run of the concurrency test. `/me` unchanged. |
| A3 `?invite=` / `?church=` capture | `capture_query_params` (ui_helpers.py:10-18, app.py:325) | `?invite=` → replaced by public `/join?code=` with sessionStorage capture (**changed**). `?church=` → **dropped** (inv A3 "do not port"). OAuth param cleanup → 5b. |
| A4 active-church resolution | `require_active_church` falls back to alphabetical first (streamlit_tenancy.py:64-88); React clears choice on 403 but doesn't re-pick (page.tsx:59-63) | `(church)` layout: stored id → `GET /church` → on 403 toast + re-pick next church; none → `/welcome`. Server check unchanged (`require_church`). |
| A5 switcher | Selectbox keyed by name, only with ≥2 churches (app.py:239-256) | Dropdown menu keyed by id, shown with ≥1 church, plus "Join or create a church…" (**changed**, decision 9). |
| A6 logout | `do_logout`; zero-church users have no logout (app.py:340-350) | Account menu "Log out" everywhere, including `/welcome`; clears query cache and `wsb:` session keys (**changed**). |
| A7 church-scoped reset | Two disagreeing reset lists (app.py:221-231; streamlit_tenancy.py:13-36) | Keyed remount of everything under `(church)` + `removeQueries(["church", oldId])` on switch. Draft keying is slice 2. |
| B1 join by code | `render_onboarding` Join tab, `pick_invite_code`, `accept_invite` 6 checks (app.py:269-298; ui_helpers.py:50-55; repos/invites.py:66-109) | Same checks, same messages, same order; typed result with reason code and church id; preview step; reusable flag; double-accept = success; role clamp. Details in §API. |
| B2 create church | Form with trimmed required name + free-text timezone, `create_church` atomic seed (app.py:300-320; repos/churches.py:11-28; repos/hymns.py:169-193) | Same messages plus "Unknown timezone." (IANA check); searchable time-zone list defaulting to the browser zone; idempotent; bulk seed in the same transaction; success visible. |
| B3 invites vs deletion | Revoked checked before church availability; soft delete revokes pending invites (repos/churches.py:55-71) | Carried over unchanged (tests pin the order). Raw-code display in Settings → 6b. |
| inv §4 "invite codes are bearer secrets" | — | POST bodies only, `history.replaceState`, never logged. |
| inv §6 streamlit_tests | `streamlit_tests/test_onboarding.py` (5 tests) | Ported to API/usecase/Vitest tests in 1b; the file is deleted in the same PR because moving `accept_invite` breaks it (F§2.3.7). |

### Out of scope (moved to named slices)

| Item | Slice | Interface this slice provides |
|---|---|---|
| Creating, listing, revoking invites; Copy link button; "Reusable for 7 days" checkbox | 6b | `repos.invites.create_invite(..., reusable: bool = False)`; `lib/urls.ts::buildInviteUrl(code, origin?)` |
| `POST /church/leave`, transfer ownership, delete church, `require_owner`, `0006_invites_integrity` | 6b | `useMembershipChanged({selectChurchId: null})` for post-leave/delete re-pick; `/welcome` as the zero-church landing |
| Member list with emails, role changes | 6b | — |
| `church_create` in-memory rate-limit bucket (3 per minute per user) on `POST /churches` — a burst guard in front of 1b's durable per-user cap, which it cannot pre-empt (§Rate limits) | 2 (limiter built there) | Route accepts an extra dependency; `domain_errors.RateLimited` (429 + `Retry-After` + `details.retry_after_seconds`), which slice 2's `ratelimit.consume` raises; the create form already shows any 429 message inline |
| `GET /church` gains `timezone`, `timezone_valid`, `bible_translation`, `effective_translation` | 2 | `ChurchProvider` passes through whatever `ChurchOut` contains; `timezones.is_valid_timezone()` |
| Editing name/timezone (`PATCH /church`), default hymnal, bundled hymnals | 6a | `timezones.is_valid_timezone()` |
| `/` → `/builder` redirect; nav items; draft store and draft pruning on `/me` | 2 | `useMeContext()` exposes `me.user.id` and `me.churches` |
| Gmail return path, `/gmail/callback` | 5b | `lib/storage.ts`, `safeInternalPath()` |
| Deleting Streamlit onboarding code (`render_onboarding`, `ui_helpers.pick_invite_code`, `capture_query_params`, `streamlit_tenancy.py`) | 7 | — |
| Hard purge of soft-deleted churches | not planned (7 decides) | — |

---

## User experience

Mobile first: every screen is a single column, `max-w-md` (onboarding) with 16 px gutters, primary actions full-width `size="touch"` (44 px). Inputs use `text-base md:text-sm`. Verified at 375 px and desktop.

### Routes

| Path | Who | Purpose |
|---|---|---|
| `/login?next=…` | public | Google sign-in; stores a validated `next` |
| `/join?code=…` | public | Captures the code, previews and joins |
| `/welcome?tab=join\|create` | signed in | Zero-church onboarding; also the switcher's "Join or create a church…" |
| `/` | signed in, ≥1 church | Home with placeholder cards (slice 2 turns it into a redirect to `/builder`) |

### Flow A — first sign-in, no church

1. Sign in → `/auth/callback` → `/` → the `(church)` layout finds `me.churches = []` → `router.replace("/welcome")`.
2. `/welcome` shows:
   - H1 **"Welcome to Worship Service Builder"**, sub "Signed in as {email}. You don't belong to a church yet."
   - A two-segment tab control **"Join a church" / "Create a church"**. Default tab: `join` (parity), or the `?tab=` value. Changing tabs updates `?tab=` with `router.replace` so refresh keeps it.
   - Header: app name on the left, account menu (name, email, **Log out**) on the right.
3. **Join tab**
   - If `wsb:pendingInviteCode` is set: info alert "You opened an invite link. Review and accept it below.", the field is prefilled and the preview runs automatically.
   - Field **"Invite link or code"**, helper "Paste the link or code from your invite." It accepts a raw code or a pasted `…/join?code=…` link (`extractInviteCode`).
   - **Continue** → `POST /invites/preview` → preview card (below). Blank → inline "Enter an invite code, or open your invite link again." (checked on the client too, same text).
4. **Create tab**
   - Intro "Start a new church. You'll be its owner and can invite others."
   - **"Church name"** (placeholder "e.g. First Presbyterian Church", max 200).
   - **"Time zone"**: `TimezoneCombobox`, the first use of the F§4.9.5 Combobox pattern (F§7.2 assigns it to slice 1), over `Intl.supportedValuesOf("timeZone")`, default = the browser's zone (`Intl.DateTimeFormat().resolvedOptions().timeZone`) when it is in the list, else `America/New_York`. Items show the IANA id with `_` as spaces (value is the id). At most 50 matches render, with "Type to search" (F§4.9.5). Helper: "Sets the default service date (the next Sunday in this time zone)." If `Intl.supportedValuesOf` is missing, the field is a plain text input with the same helper, validated by the server.
   - Caption: "Your church gets its own copy of the starter hymnal."
   - **Create church** → `PendingButton` "Creating church…"; after 8 s a line "Still working — this can take up to a minute." (F§1.8).
   - The client checks first, with the server's exact messages, and sends nothing when either fails: trimmed name empty → "Church name is required."; time zone empty → "Timezone is required.". The message shows inline under the field and the first invalid field gets focus.
   - Server 422s show the same way (`fields.name` / `fields.timezone`): the two messages above (if the client check was bypassed) and "Unknown timezone." (text-input fallback, or a browser zone missing from `tzdata`).
   - 429 `rate_limited` (the per-user cap, or from slice 2 on the burst bucket; §Rate limits) → inline alert above the button with the server message; handled locally, no global toast.
   - Idempotency-Key per attempt (§Idempotency): an identical retry after a lost response reuses the key; any 4xx or any edit gets a fresh one, so a corrected resubmit never meets a stored 422 or `idempotency_mismatch`.
   - Success → toast **"Created {name}. You're the owner."** → the new church becomes active → `/`.

### Flow B — invite link

1. Anyone opens `https://worship-service-builder.vercel.app/join?code=XYZ`. The proxy lets `/join` through signed out.
2. On mount `/join` writes `sessionStorage["wsb:pendingInviteCode"] = "XYZ"` and calls `history.replaceState(null, "", "/join")`, so the code leaves the address bar and history. It also clears `wsb:postLoginPath`.
3. **Signed out** → card: title **"You're invited"**, body "Sign in with Google to see and accept your invite to Worship Service Builder.", button **Sign in with Google** → `/login?next=/join` → Google → `/auth/callback` → `/` → the `(signed-in)` layout follows the stored path back to `/join`.
4. **Signed in** → `POST /invites/preview` (skeleton card while loading) → preview card:
   - Title: **{church_name}**
   - `already_member: false`: "You're invited to join as a member." / "…as an admin." (the clamped role the invite grants). Email-bound only: "This invite is for {your email}." Then "Invite expires {Month D, YYYY}." (formatted in the browser's zone).
   - `already_member: true`: the single line "You're already a member of {church_name}." replaces the role, email and expiry lines, so an existing member is never told they will join as an admin when their role will not change.
   - Buttons: **Join {church_name}** (or **Open {church_name}** when `already_member`) as primary, and **Not now** (clears the pending code, goes to `/` — which goes on to `/welcome` for a zero-church user).
   - Footer: "Signed in as {email} · Use a different account".
   - The explicit tap departs from owner decision 6's wording ("opening the link … joins the church"); see behavior change 4. The owner's answer is needed **before 1b starts**: if approved, F§4.3 records it as an amendment to decision 6 and this flow stands; if declined, F§4.3 changes to auto-accept after sign-in and steps 4–5 become the `autoAccept` flow in behavior change 4.
5. **Join / Open** → `PendingButton` "Joining…" → `POST /invites/accept` (for an existing member this changes nothing and does not consume a code-only invite; it returns the church id the preview withholds) → clear the pending code → `useMembershipChanged({selectChurchId: church.id})` → toast with the server message (**"Joined {name}."** or **"You're already a member of {name}."**) → `/`. (Slice 2 makes `/` redirect to `/builder`, which completes F§4.3's "goes to /builder".)
6. **Rejected** (preview or accept) → error card with the server message, plus:
   - reasons `unknown`, `revoked`, `expired`, `used`, `church_unavailable`: second line **"Ask for a new invite link."**, pending code cleared, button "Go to home" (`/`).
   - reason `email_mismatch`: second line "You're signed in as {email}.", button **Use a different Google account** (signs out *keeping* the pending code, then `/login?next=/join&select_account=1`, which passes `prompt=select_account` to Google). The pending code is kept.
7. **No code** (no `code` param and nothing stored) → card "This invite link is incomplete." / "Open the link from your invite again, or ask for a new one." with "Go to home".
8. A signed-in user who already has churches uses the same flow (decision 9); the joined church becomes active.

### Flow C — join or create from the switcher

- The header's church control is a menu: label "Your churches", a radio list of the user's churches (name, with the role in muted text so same-name churches are distinguishable), a separator, then **"Join or create a church…"** → `/welcome`.
- For a user with churches, `/welcome` shows H1 **"Join or create a church"**, sub "Signed in as {email}.", and a "← Back to {active church}" link. Everything else is Flow A.

### Flow D — resolution, switching, lost access, sign-out

- **Resolution** (`(church)` layout): pick the stored `activeChurchId` if it is still in `me.churches`, else the first church (by name). The stored id is read before the first client render that picks a church, so no other church is ever requested or shown first. Confirm with `GET /church`. Shell skeleton while confirming.
- **Switch**: choosing another church stores its id, remounts everything under `(church)` (`<Fragment key={church.id}>`), and cancels/removes the old church's queries.
- **Lost access** (`GET /church`, or any church-scoped request, returns 403 with `details.reason = "no_church_access"`): toast **"You no longer have access to {name}."**, refetch `/me`, pick the next church excluding that id; none left → `/welcome`.
- **Log out** (account menu): `queryClient.clear()` → `storeChurchId(null)` → remove `wsb:pendingInviteCode` and `wsb:postLoginPath` → `supabase.auth.signOut({ scope: "local" })` → `/login`.
- **Session expired** (any 401): same, except the pending invite code is kept and the redirect is `/login?next=<current path>` when `safeInternalPath` accepts it, so the user returns where they were.
- **Sign-out scope.** Every sign-out path — explicit Log out, the automatic 401 path and "Use a different Google account" — uses `scope: "local"`: it ends this browser's session only. supabase-js v2 defaults to `"global"`, which would let one API 401 on one device (clock skew beyond the 30 s leeway, a token the API rejects) end the user's sessions on every device. Explicit Log out is also local, matching Streamlit's per-browser logout; if the owner wants Log out to end every session, only that one call changes to `"global"`.

### Loading, empty and error states

| Where | Loading | Error |
|---|---|---|
| `(signed-in)` layout (`/me`) | Shell skeleton | 401 → sign out; network/5xx → full-page `ErrorState` "Can't reach the server." / "Something went wrong. (Ref: …)" + **Retry** |
| `(church)` layout (`GET /church`) | Header shows the candidate name; body skeleton | 403 no_church_access → fallback; other → `ErrorState` + Retry |
| Preview | Skeleton card | Rejection card (above); network/timeout → inline `ErrorState` with Retry, code kept |
| Accept / Create | `PendingButton` | 422 inline fields; 400 rejection card; 429 inline alert (create); network/timeout/5xx → toast "Can't reach the server. Check your connection and try again." / "Something went wrong. (Ref: …)" (an unchanged create retry reuses the same Idempotency-Key, so it is safe; any 4xx or edit gets a new key) |

---

## API

Conventions: F§1. All bodies `snake_case`; request models `ConfigDict(extra="forbid")`; human rules in the usecase with exact messages; every route declares `response_model` and `responses=error_responses(...)` so the error body appears in OpenAPI.

| Method | Path | Guard | Request | Response | Errors |
|---|---|---|---|---|---|
| POST | `/churches` | user (`X-Church-Id` ignored) | `CreateChurchIn {name: str = "" (max 200), timezone: str = "" (max 64)}`; optional header `Idempotency-Key: <uuid>` | **201** `ChurchOut {id, name, role: "owner"}` | 401 `unauthenticated`; 422 `invalid_request` "Church name is required." (`fields.name`), "Timezone is required." / "Unknown timezone." (`fields.timezone`), "The request was not valid." (size/type/extra, with `fields`), "Idempotency-Key must be a UUID."; 422 `idempotency_mismatch` "This request was already sent with different details."; 429 `rate_limited` "You've created 5 churches in the last 24 hours. Try again later." + `Retry-After` + `details.retry_after_seconds` (from slice 2, also the `church_create` burst bucket's 429 with the limiter's message); 503 `auth_unavailable`; 500 `internal_error` |
| POST | `/invites/preview` | user | `InviteCodeIn {code: str = "" (max 256)}` | 200 `InvitePreviewOut {church_name: str, role: "member"\|"admin", expires_at: datetime, email_bound: bool, already_member: bool}` | 401; 422 `invalid_request` "Enter an invite code, or open your invite link again." (`fields.code`); 400 `invite_rejected` (table below) with `details.reason`; 503; 500 |
| POST | `/invites/accept` | user | `InviteCodeIn` | 200 `InviteAcceptOut {church: ChurchOut, already_member: bool, message: str}` | same as preview |
| GET | `/church` | church | — | `ChurchOut {id, name, role}` (unchanged) | 403 `forbidden` "You don't have access to this church." **now with `details: {"reason": "no_church_access"}`** |
| GET | `/me` | user | — | unchanged | unchanged |

`ChurchOut.role` becomes `Literal["owner", "admin", "member"]` (additive: it narrows the generated TS type).

### Invite checks (shared by preview and accept, in this order — parity with repos/invites.py:79-98)

| # | Condition | `details.reason` | Message (exact) |
|---|---|---|---|
| 0 | `code.strip()` empty | — (422 `invalid_request`) | Enter an invite code, or open your invite link again. |
| 1 | No invite with this code | `unknown` | Invalid invite code. |
| 2 | `revoked` | `revoked` | This invite has been revoked. |
| 3 | `expires_at < now` (naive = UTC) | `expired` | This invite has expired. |
| 4 | `not reusable and accepted_at is not null`, **unless** `accepted_by == caller` and the caller is still a member | `used` | This invite has already been used. |
| 5 | Church missing or soft-deleted | `church_unavailable` | This church is no longer available. |
| 6 | Email-bound and caller email ≠ invite email (case-insensitive) | `email_mismatch` | This invite was issued for a different email address. |

All six are `400 invite_rejected`. The code is stripped before lookup. The caller's email is `CurrentUser.email` (already normalized).

### Accept semantics

- **Role granted** = `_clamp_role(invite.role)`: `member`/`admin` as stored; `owner` → `admin` (matching the F§6.2 repair); anything else → `member`. A clamp logs WARNING with the invite id. This removes the `IntegrityError` 500 of inv B1.
- **Existing member** → 200, `already_member: true`, `church.role` = their current role (never changed), message "You're already a member of {name}.". A code-only invite is **not** consumed by an existing member (so an admin testing their own link doesn't burn it). An email-bound, not-yet-accepted invite **is** stamped (parity with invites.py:107-108).
- **New member** → the invite is consumed first if it is not reusable (conditional update, below), then the membership is inserted with `ON CONFLICT DO NOTHING`; 200 with `already_member = not inserted` — `false` and "Joined {name}." when this request inserted the row, `true` and "You're already a member of {name}." when a concurrent request by the same user inserted it first.
- **Reusable** invites are never stamped; they stay usable until they expire or are revoked.
- **Idempotent for the same user**: a sequential repeat (retry, or reopening a consumed single-use link after joining) returns 200 `already_member: true`. Concurrent duplicates (double-click) both return 200 with one membership; exactly one of them reports `already_member: false`. A user who was removed from the church and reopens their consumed link gets "This invite has already been used." (check 4), so a removal cannot be undone with an old link.
- **Two users racing** for one single-use invite: exactly one joins; the other gets `used`.

### Preview semantics

Read-only: no membership, no stamp. Runs checks 0–6. Returns only the five fields above — never the invite id, code, church id, creator or bound email (F§7.4). `already_member` describes the caller, not the invite, so it discloses nothing the caller could not learn from `/me`; it is an addition to F§7.4's list of four.
- `role` is `_clamp_role(invite.role)` — the same clamp accept applies — so an invite stored with `owner` previews as `admin` and a bogus role as `member`, never a response-validation 500.
- `expires_at` is normalized with `as_utc` (the existing `_as_utc`, invites.py:18-23, exported) so it always serializes as ISO 8601 with an offset (F§1.3); SQLite's naive values would otherwise read as browser-local time.
- `already_member` = the caller already has a membership in the invite's church.

A consumed single-use invite accepted by the caller previews normally (check 4's exception) with `already_member: true`, and accepting it then returns `already_member: true`.

### Idempotency on `POST /churches`

Server, per F§1.6: key = `(user_id, "POST", "/churches", Idempotency-Key)`, 15-minute TTL, body hash = SHA-256 of `payload.model_dump(mode="json")` serialized with sorted keys. A replay returns the stored status and body with header `Idempotent-Replayed: true`. 2xx and 4xx are stored, **except a 429 `RateLimited`**; 5xx and 429 are not (the entry is dropped so a retry re-executes — for a 429, once `Retry-After` has passed). This keeps 5b's rule that a limiter 429 is never replayed. Same key + different body → 422 `idempotency_mismatch`. No key → no idempotency. `POST /invites/accept` needs no key: it is idempotent by construction.

Client key lifetime — F§1.6 as amended (slices 1, 5a and 5b replace "one key per form mount" with rotation after any 4xx), because the server stores 4xx responses: the form **reuses** a key only for a retry with an unchanged body after `network_error`, `timeout` or a 5xx (outcome unknown), or while that request is still in flight (double tap). It takes a **new** key after any definitive response (2xx or 4xx) and whenever the body changes. So a 422 "Church name is required." followed by a corrected name sends a new key and succeeds, instead of replaying the stored 422 or hitting `idempotency_mismatch`. Implemented by `lib/idempotency.ts` (§Frontend).

### Rate limits

Invite routes: none. Invite codes are 256-bit (`secrets.token_urlsafe(32)`, invites.py:43), so guessing is infeasible.

`POST /churches`: each call copies the whole `hymn_catalog` into `hymns` on the database the frozen Streamlit app also uses, and any Google account can sign in, so 1b ships a **durable per-user cap** rather than waiting for slice 2's limiter. In `usecases.onboarding.create_church`, before any insert: count the churches where the caller holds an `owner` membership and `churches.created_at > now − 24 h`, **including soft-deleted ones** (so delete-and-recreate does not reset it). At 5 or more → `RateLimited("You've created 5 churches in the last 24 hours. Try again later.", retry_after_seconds=<until the oldest of them is 24 h old, at least 1>)` → 429 `rate_limited` with `Retry-After` and `details.retry_after_seconds`. It is database-backed, so it survives restarts; two exactly concurrent creates may both pass at 4, which is an acceptable bound. It is raised inside `run_idempotent`, which never stores a `RateLimited` (§Idempotency).

Slice 2 adds the in-memory `rate_limit("church_create")` bucket (F§1.8): **3 per minute per user**, a cheap burst guard in front of the cap. As a route dependency it runs before validation and before idempotency replay, so a 422 or an identical-key retry also spends a token; 3 per minute leaves room for a correction plus a retry. Its threshold is deliberately not 5 per day, so it never pre-empts the cap: a user who reaches 5 creates in 24 h at a normal pace gets the cap's message, not the limiter's generic "Too many requests. Try again in {n} seconds.". Its 429 is the same `RateLimited` (raised by `ratelimit.consume`). Slice 1's API cap test makes a single `POST` after seeding five recent churches, so the burst bucket cannot interfere with it; slice 2 keeps that test green unchanged.

---

## Backend changes

### Modules added (1a)

| Module | Contents |
|---|---|
| `backend/domain_errors.py` | `DomainError(message, *, code=None, field=None, details=None)` and `InvalidInput`, `NotFound`, `Forbidden`, `Conflict`, `Rejected`, `NotConfigured`, `Busy`, `UpstreamError`, `UpstreamTimeout` with the statuses/default codes of F§2.2 item 4, plus `RateLimited(message, *, retry_after_seconds)` (429, `rate_limited`; it always sets `details = {"retry_after_seconds": n}` and the handler adds `Retry-After: n`). `RateLimited` is the **only** 429 mechanism (F§1.5, F§2.2): 1b's cap raises it, and slice 2's `ratelimit.consume` raises it for every bucket (no `ApiError` 429, no `ApiError.headers`). `ERROR_CODES: dict[str, int]` is the F§1.5 registry, including **`db_unavailable: 503`** (ops handoff; ops' `api/errors.db_unavailable()` helper keeps working and uses it). No FastAPI import. |
| `backend/db/schema_check.py` | Shared by `migrations/env.py`, the lifespan, `/health/ready`, the drift script and `test_migrations.py`. `alembic_config() -> Config` built from the absolute path `Path(__file__).resolve().parents[1] / "alembic.ini"` (never the working directory); `include_object(...)` (skips reflected tables not in our metadata, e.g. `alembic_version`); `revision_state(conn) -> RevisionState(current, head, state)` where `state` is `"current"`, `"behind"` (current is `None` or a known non-head revision) or `"ahead"` (current unknown to this release's scripts, e.g. a rolled-back release); `schema_diff(conn) -> list` = `compare_metadata(MigrationContext.configure(conn, opts={"include_object": include_object, "compare_type": True}), Base.metadata)`. |
| `backend/scripts/schema_drift.py` | Runbook step 6. Connects with `DATABASE_URL`, prints `revision_state` and each `schema_diff` entry one per line, exits 0 when the diff is empty and 1 otherwise. Unlike `alembic check`, it works on a database that is not at head. |
| `backend/db/ids.py` | `as_uuid(value) -> uuid.UUID`; raises `NotFound` for `None`, malformed strings or wrong types. Used by every repo function slice 1 creates or changes; other repos adopt it as their slice touches them. |
| `backend/usecases/__init__.py` | Package marker; docstring states the layer rules (F§2.2). |
| `backend/api/idempotency.py` | `idempotency_key(required: bool = False)` dependency factory (reads `Idempotency-Key`; 422 `invalid_request` "Idempotency-Key must be a UUID." when malformed; when `required=True` and absent, 422 "Missing Idempotency-Key header." — used by 5b); `IdempotencyStore` (dict + per-key `threading.Lock`, TTL 15 min, lazy expiry on access, bounded to 10 000 entries) and `run_idempotent(*, user_id, route, key, payload, status_code, call) -> Response`. `call` returns a Pydantic model; `DomainError`s raised inside are converted with `errors.domain_error_response()` and stored, **except `RateLimited`**: its 429 is returned but the entry is dropped (as for a 5xx), so the same key re-executes after `Retry-After` (5b relies on this for its `email` charge). |
| `backend/scripts/export_openapi.py` | Writes `frontend/src/lib/api/openapi.json` from `create_app().openapi()` with `sort_keys=True, indent=2` and a trailing newline. |
| `backend/migrations/` + `backend/alembic.ini` | §Data and migrations. |
| `backend/railway.toml` | `[deploy] preDeployCommand = ["alembic upgrade head"]`, `healthcheckPath = "/health/ready"`. Start command stays in `Procfile`. Railway does **not** look for this file under the service's root directory (`/backend`): the service setting "Config-as-code" path must be set to `/backend/railway.toml` by hand (runbook step 7), or neither setting applies. Railway's deploy health check moves from `/health` to `/health/ready` (F§3.3 as amended) so that a release whose schema is behind head fails its deploy health check and the previous release keeps serving (Modules changed → `api/main.py`). `/health` stays ops' dependency-free liveness probe, unchanged. |

### Modules changed (1a)

- **`api/errors.py`**
  - `ApiError(status, code, message, *, details=None)`. No `headers` parameter: every 429 is a `RateLimited`.
  - Body builder `_body(code, message, *, fields=None, details=None)` always adds `request_id` from the ops contextvar.
  - `@app.exception_handler(DomainError)` → status/code/message; `fields = {exc.field: exc.message}` when `field` is set; `details` when set; for `RateLimited`, the `Retry-After` header (its `details.retry_after_seconds` is already set). Exposed as `domain_error_response(exc) -> JSONResponse` for the idempotency store.
  - The code registry is `domain_errors.ERROR_CODES` (including `db_unavailable`); the frontend `ApiErrorCode` union mirrors it (`test_error_registry.py`).
  - `RequestValidationError` → 422 "The request was not valid." with `fields`: location with the leading `body`/`query`/`header` removed, joined by `.`; messages "Required." (`missing`), "Too long (max N characters)." (`string_too_long`, N from `ctx.max_length`), "Not a valid value." (anything else, including `extra_forbidden`).
  - `ErrorBody` Pydantic model and `error_responses(*statuses) -> dict` for route decorators.
- **`api/deps.py`**: `require_church` raises `forbidden(details={"reason": "no_church_access"})`. Role 403s (`require_admin`, later `require_owner`) carry no `reason`, so the client never falls back on a role denial. This is the one signal the frontend uses to detect lost church access, and every slice keeps it.
- **`api/schemas.py`**: `ChurchOut.role: Literal[...]`; add `ErrorBody` re-export; add the shared generics `Page[T] {items, total, limit, offset}` and `ItemList[T] {items}` (F§1.3, F§1.4) for 3/5a/6a. `GET /church` stays in `routes/me.py` in this slice.
- **`api/main.py`**
  - Lifespan: **remove `init_db()`** (the ops slice cannot remove it because Alembic does not exist yet; if ops already did, skip). Add the revision check via `schema_check.revision_state` (WARNING `schema revision X != head Y` when they differ; stored on `app.state.schema_state`) and, on Postgres, the RLS check (WARNING naming every `public` table with `rowsecurity = false`). Both checks catch and log their own errors (ERROR, state `unknown`) and never block startup. Because `alembic_config()` uses an absolute path, the check finds the scripts whether the process starts in `backend/` (Railway, CLI) or at the repo root (pytest).
  - **Readiness gate** (`api/routes/health.py`, ops' `/health/ready`): when `APP_ENV=production` and `app.state.schema_state` is `behind`, it returns 503 `db_unavailable` "The database schema is behind this release." with `details: {"reason": "schema_behind", "current": X, "head": Y}` (the code stays `db_unavailable`; F§1.5's registry documents the `schema_behind` reason), and the startup line is logged at ERROR. The gate reads the state fixed at startup and is checked before ops' memoized `SELECT 1` probe, so the memo never hides it. `ahead` stays 200 (expand-only migrations keep an older release working, so a Railway rollback is never blocked); `unknown` stays 200 (the check itself failed; its ERROR is logged). Outside production nothing changes, so ops' readiness tests on SQLite are unaffected. When Railway reads `railway.toml`, `healthcheckPath = "/health/ready"` means a release that starts on a behind-head schema (for example, the pre-deploy command was overridden in the UI) fails its health check and never goes live. When Railway does not read the file, the health check does not apply either, but the 503 still turns keepalive's daily run red and the ERROR line is in the deploy log.
  - Mount `churches` and `invites` routers (1b).
- **`db/models.py`**: `Invite.reusable = Column(Boolean, nullable=False, default=False, server_default=sa.false())`; `Invite.accepted_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL", name="fk_invites_accepted_by_users"))`. Amend the module docstring: columns added while Streamlit still runs also declare a server default (F§3.4).
- **`backend/requirements.txt`**: add `alembic>=1.13` and `tzdata` (Python's `zoneinfo` needs an IANA database; Railway's image may not ship one). Pin `fastapi` and `pydantic` to exact minor versions (`fastapi==0.1xx.*`, `pydantic==2.x.*`, the versions currently resolved) so the committed OpenAPI snapshot is stable.
- **`pytest.ini`**: `markers = postgres: needs TEST_DATABASE_URL (runs in the backend-postgres CI job)`.
- **Deleted:** `backend/migrate_add_hymnal.py` (after `0002` covers it).

### Modules added (1b)

**`backend/timezones.py`**
```python
@lru_cache(maxsize=1)
def _zones() -> frozenset[str]: return frozenset(zoneinfo.available_timezones())
def is_valid_timezone(name: str) -> bool: return name in _zones()   # exact, case-sensitive
```
Reused by slice 2 (`timezone_valid`) and 6a (`PATCH /church`).

**`backend/usecases/onboarding.py`** (no FastAPI, no Streamlit; `now` injectable for tests)
```python
@dataclass(frozen=True)
class ChurchSummary: id: uuid.UUID; name: str; role: str
@dataclass(frozen=True)
class InvitePreview: church_name: str; role: str; expires_at: datetime; email_bound: bool; already_member: bool
# role is _clamp_role(invite.role); expires_at is as_utc(invite.expires_at) (always aware UTC)
@dataclass(frozen=True)
class InviteAccepted: church: ChurchSummary; already_member: bool; message: str

class InviteRejectReason(StrEnum): unknown, revoked, expired, used, church_unavailable, email_mismatch

def create_church(*, user_id, name, timezone) -> ChurchSummary
def preview_invite(*, user_id, user_email, code, now=None) -> InvitePreview
def accept_invite(*, user_id, user_email, code, now=None) -> InviteAccepted
```
- `create_church` (`now` injectable): strip; `InvalidInput(field="name", "Church name is required.")`; `InvalidInput(field="timezone", "Timezone is required.")`; `is_valid_timezone` else `InvalidInput(field="timezone", "Unknown timezone.")`. Then one `with session_scope() as s:` around the per-user cap (`repos.churches.recent_owned_creations(user_id, since=now - 24h, session=s)` → `(count, oldest_created_at)`; ≥ 5 → `RateLimited`, §Rate limits) and `repos.churches.create_church(..., session=s)` (church + owner membership + seed). Returns the stored (trimmed) name.
- `preview_invite` / `accept_invite`: a private `_evaluate(inv, church, user_id, user_email, member_role, now) -> InviteRejectReason | None` implements checks 1–6; rejection raises `Rejected(message, code="invite_rejected", details={"reason": reason})`.
- `accept_invite` flow, all in one `session_scope`:
  ```
  inv = repos.invites.find_by_code(code, session=s)            # ORM row or None
  church = repos.churches.get_church(inv.church_id, session=s) if inv else None
  member_role = repos.memberships.get_role(user_id, church.id, session=s) if church else None
  reason = _evaluate(...)  → Rejected
  if member_role:
      if inv.email is not None and not inv.reusable and inv.accepted_at is None:
          repos.invites.claim(inv.id, user_id, now, session=s)   # parity stamp
      return InviteAccepted(ChurchSummary(church.id, church.name, member_role), True,
                            f"You're already a member of {church.name}.")
  if not inv.reusable and not repos.invites.claim(inv.id, user_id, now, session=s):
      s.refresh(inv)                                              # someone else won, or our own concurrent request
      if inv.accepted_by != user_id: raise Rejected(used)
  role, inserted = repos.memberships.ensure_membership(church.id, user_id, _clamp_role(inv.role), session=s)
  if not inserted:                                                # our own concurrent request inserted it first
      return InviteAccepted(ChurchSummary(church.id, church.name, role), True,
                            f"You're already a member of {church.name}.")
  return InviteAccepted(ChurchSummary(church.id, church.name, role), False, f"Joined {church.name}.")
  ```
  `claim` is the portable race guard: `UPDATE invites SET accepted_at=:now, accepted_by=:uid WHERE id=:id AND accepted_at IS NULL`, returning `rowcount == 1`. On Postgres a concurrent claimer blocks on the row lock and then sees zero rows; on SQLite writers serialize. `ensure_membership` uses `insert_ignore(Membership)` (ops), takes `inserted = result.rowcount == 1` (0 when `ON CONFLICT DO NOTHING` skipped, on both dialects), then re-selects the role, so a concurrent same-user accept never hits the primary key (F§7.4) and exactly one of two concurrent same-user accepts reports `already_member: false`.
- `preview_invite` flow: the same lookups and `_evaluate` in a read-only `session_scope`, then `InvitePreview(church.name, _clamp_role(inv.role), as_utc(inv.expires_at), inv.email is not None, member_role is not None)`.
- **Logging** (one line each, no code, no email): `church_created church_id user_id hymns_seeded duration_ms`; `church_create_limited user_id count`; `invite_accepted invite_id church_id user_id already_member`; `invite_rejected reason invite_id` (`invite_id=none` for unknown codes).

**`backend/api/routes/churches.py`**: `POST /churches` → `run_idempotent(..., call=lambda: ChurchOut(**asdict(onboarding.create_church(...))), status_code=201)`. Plain `def`.

**`backend/api/routes/invites.py`**: `POST /invites/preview`, `POST /invites/accept`. Slice 6b adds `GET/POST /invites` and `DELETE /invites/{invite_id}` to this module; the fixed paths `/invites/preview` and `/invites/accept` must stay declared before any `/invites/{invite_id}` route.

### Repo changes (1b) — each new or changed function gains `session: Session | None = None` (F§2.2 item 3)

| Function | Change |
|---|---|
| `repos.churches.create_church` (churches.py:11-28) | `session` param; ids through `as_uuid`. Signature otherwise unchanged. |
| `repos.churches.get_church` (31-41) | `session` param. |
| `repos.churches.recent_owned_creations(user_id, *, since, session) -> tuple[int, datetime \| None]` | New; count and oldest `created_at` of churches where the user holds an `owner` membership and `created_at > since`, soft-deleted included (the per-user cap). |
| `repos.hymns.seed_church_from_catalog` (hymns.py:169-193) | Replace one ORM `add` per row with Core `session.execute(insert(Hymn), rows)` where `rows` are dicts with a Python `uuid4()` id per row (portable; uses SQLAlchemy's insertmanyvalues batching). Same columns copied, same return value, still no commit. If production timing exceeds 5 s, switch the Postgres path to `INSERT … SELECT gen_random_uuid(), …` (see Risks). |
| `repos.invites.create_invite` (invites.py:40-55) | `reusable: bool = False` kwarg (6b wires it to the API). Return value unchanged. |
| `repos.invites._to_dict` | Adds `reusable`, `accepted_by`. |
| `repos.invites._as_utc` (18-23) | Exported as `as_utc` (the private name stays as an alias) for the preview's `expires_at`. |
| `repos.invites.find_by_code(code, *, session)` | New; returns the ORM row. Internal to usecases; never exposed by a route. |
| `repos.invites.claim(invite_id, user_id, now, *, session) -> bool` | New; conditional update above. |
| `repos.invites.accept_invite` (66-109) | **Removed**; logic moves to `usecases.onboarding.accept_invite` (F§2.3.3). Its tests are ported. If ops took the F§6.1.6 contingency (Streamlit not redeployed from `streamlit-frozen`), keep it instead as a wrapper returning `(ok, message)` over the usecase and keep `streamlit_tests/test_onboarding.py`. |
| `repos.memberships.get_role` (memberships.py:29-32) | `session` param. |
| `repos.memberships.ensure_membership(church_id, user_id, role, *, session) -> tuple[str, bool]` | New; `insert_ignore` then select; returns `(role, inserted)` where `inserted` is `rowcount == 1`. |

### Streamlit coupling removed

- `ui_helpers.capture_query_params` (`?invite=` half) and `pick_invite_code` → frontend `/join` capture and `extractInviteCode` (inv §3 row "ui_helpers.py").
- `repos.invites.accept_invite`'s `(bool, str)` UI-shaped return → typed usecase result with `reason` and church id (inv §3 row "backend/repos/invites.py:66-109").
- `streamlit_tenancy.require_active_church` fallback and reset lists → `(church)` layout + keyed remount (inv §3 row "app.py:221-256").
- `app.py:render_onboarding` / `render_church_switcher` → `/welcome` / `ChurchSwitcher`.
- `test_no_streamlit_in_core.py` also imports `api.main` (all routers mounted) and `usecases.onboarding` in a subprocess and asserts `streamlit` is not in `sys.modules`.
- `app.py` on `main` will no longer import after `accept_invite` moves. That is expected: production Streamlit runs from `streamlit-frozen` (F D2), and no test imports `app.py`.

### Tenancy and data-access notes

- The three new routes are **user-scoped**; they never read `X-Church-Id`. The church comes only from the invite row or from the new row. They are added to `USER_SCOPED` in `test_route_guards.py` in the same PR.
- `find_by_code` is a global lookup by secret; only `usecases.onboarding` calls it, and the API returns nothing beyond the preview fields.
- `GET /church` stays the only church-scoped route in slice 1; it gets the `assert_church_isolated` test (the 403 half; it has no resource id).

---

## Data and migrations

### Alembic setup (1a) — as F§3.1

- `backend/alembic.ini`: `script_location = %(here)s/migrations`, `prepend_sys_path = %(here)s`. Alembic resolves bare relative paths against the working directory, so `migrations` / `.` would work from `backend/` (Railway, CLI) but not from the repo root, where pytest runs (`pytest.ini`: `pythonpath = . backend`). Code never builds a `Config` from a relative path; it uses `db.schema_check.alembic_config()`.
- `backend/migrations/env.py`: `target_metadata = db.models.Base.metadata`; URL from `db.engine._normalize_url(db.engine._database_url())`; `render_as_batch=True` on SQLite; `compare_type=True`, `compare_server_default=False`; `include_object` imported from `db.schema_check` (skips reflected tables not in our metadata); supports offline (`--sql`) mode; on Postgres runs `SET lock_timeout = '5s'` and `SET statement_timeout = '60s'` first. Does **not** call `load_dotenv` implicitly beyond what `db.engine` already reads (the laptop runbook exports `DATABASE_URL` explicitly).
- File names `NNNN_short_slug.py`; every revision has a working `downgrade()`; every new constraint is explicitly named.

### Revisions

| Revision | Upgrade | Downgrade | Notes |
|---|---|---|---|
| `0001_baseline` | Creates the 11 tables exactly as `db/models.py` at `50fda65` (users, churches, memberships, invites, hymn_catalog, hymns, services, hymn_usage, contacts, gmail_tokens, oauth_states), including `ix_hymns_church_hymnal` | Drops them | Fresh databases only (CI, new local dev). Production is **stamped**. |
| `0002_reconcile` | `op.create_index("ix_hymns_church_hymnal", "hymns", ["church_id", "hymnal"], if_not_exists=True)` plus any other difference the runbook's drift script reports, each guarded with `IF NOT EXISTS` | **No-op** for every object the `0001` baseline declares (including `ix_hymns_church_hymnal`), with a comment: on a fresh database 0001 created them and 0001's downgrade drops them, so dropping them here would break 0001's own `drop_index` and the `downgrade base` cycle. Only a drift fix that is not part of the 0001 model schema gets a guarded `drop_…(if_exists=True)` (none expected). | No data touched. `migrate_add_hymnal.py` deleted in the same PR. |
| `0003_lockdown` | Postgres only (no-op on SQLite), one `DO $$ … $$` block run as the migrating (app) role: **(1) precondition** — unless `current_user` has `rolbypassrls`, every `public` table must be owned by `current_user`; otherwise `RAISE EXCEPTION '0003_lockdown: role % has no BYPASSRLS and does not own: %. Enabling RLS would hide their rows from the app. See migrations/README.md "RLS precondition".'`; **(2)** for each `public` table with `relrowsecurity = false` (incl. `alembic_version`): if owned by `current_user`, `ENABLE ROW LEVEL SECURITY`, else `RAISE EXCEPTION '0003_lockdown: cannot enable RLS on % (owned by %, migrating as %) …'`; tables ops already enabled are skipped; **(3)** if role `anon` exists: `REVOKE ALL ON ALL TABLES` and `ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated`, and the matching `ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES / ON SEQUENCES FROM anon, authenticated` (same statements as the ops SQL). | `DISABLE ROW LEVEL SECURITY` only; grants are deliberately **not** restored (a comment says so) | Idempotent when ops applied the lockdown by hand. It never half-applies: a `RAISE` aborts the upgrade transaction (Postgres DDL is transactional), the deploy fails and the previous release keeps serving. The runbook checks the same precondition before merging (step 0). |
| `0004_invites_reusable` | `invites.reusable BOOLEAN NOT NULL DEFAULT false`; `invites.accepted_by UUID NULL` + FK `fk_invites_accepted_by_users` → `users(id) ON DELETE SET NULL`; data step `UPDATE invites SET reusable = true WHERE email IS NULL` (via a lightweight `sa.table` so the literal is dialect-correct) | Drop FK and both columns (batch on SQLite) | Existing code-only invites keep their 7-day multi-use meaning; existing email-bound invites stay single-use. |

### Production runbook (in `backend/migrations/README.md`; owner runs it from a laptop **before merging PR 1a**)

0. **RLS precondition** (ops handed this question to slice 1; ops Risks item 1). Read `docs/ops-runbook.md` → "Supabase lockdown record", or rerun through the same pooler URL: `select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;` and `select current_user, rolbypassrls from pg_roles where rolname = current_user;`.
   - **The app role owns every `public` table, or has BYPASSRLS** → proceed; `0003` will pass its own check and only enable RLS where ops skipped it.
   - **Otherwise** → stop before stamping. Neither fix can live in `0003`: `ENABLE ROW LEVEL SECURITY` and `CREATE POLICY` both require table ownership, and the migration runs as the app role. The owner runs one fix by hand in the SQL editor as the current table owner and records it (date, SQL, before/after query output) in the lockdown record:
     - **preferred:** `ALTER TABLE public.<t> OWNER TO <app role>;` for each table the app role does not own (keeps "RLS with no policies" = deny-all for `anon`/`authenticated` with no policy to maintain);
     - **alternative, only if ownership cannot be transferred:** for each such table, as its owner, `CREATE POLICY app_all ON public.<t> TO <app role> USING (true) WITH CHECK (true);` then `ENABLE ROW LEVEL SECURITY`. The 1a PR must then widen `0003`'s precondition to accept a table that already has RLS enabled and an `app_all` policy for `current_user`, with a test on CI Postgres.

     Rerun the two queries; continue only when the first branch holds (or the alternative is in place and 0003 amended).
1. `pg_dump` backup with a client matching the server major (ops backup procedure), kept encrypted.
2. `SHOW server_version;` → record the major in the README. It must equal `PG_MAJOR` in `backup.yml` and the CI Postgres image major (ops' `test_ops_workflows.py` enforces that the latter two are equal).
3. From `backend/` on the 1a branch with `DATABASE_URL` exported: `alembic current` → expect no revision.
4. `alembic stamp 0001_baseline`.
5. `alembic upgrade 0001_baseline:head --sql > upgrade.sql` and read it. (Offline mode cannot read the database, so without the explicit start revision it would render from base, including every 0001 `CREATE TABLE` and the `alembic_version` DDL.) Expect only the 0002 index, the 0003 `DO` block and `REVOKE`/`ALTER DEFAULT PRIVILEGES` statements, the 0004 columns, FK and `UPDATE`, and the `UPDATE alembic_version` lines.
6. `python scripts/schema_drift.py` (`alembic check` refuses here with "Target database is not up to date." because the database is at 0001 and head is 0004). Expected diff, exactly: `add_column invites.reusable`, `add_column invites.accepted_by`, `add_fk fk_invites_accepted_by_users`, and `add_index ix_hymns_church_hymnal` only if it is missing. Any other difference: if it is expand-safe (F§3.4), add it to `0002` with an `IF NOT EXISTS` guard and repeat from 5; otherwise stop and resolve with the owner before merging.
7. **Railway config path.** In the Railway service → Settings → Config-as-code, set the path to `/backend/railway.toml` (Railway does not look under the service's root directory). Do it immediately before merging, so the merge deploy is the first to read it.
8. Merge. In the merge deploy's log confirm that the **pre-deploy** step ran `alembic upgrade head` (0002 → 0004 lines) and that the `/health/ready` health check passed. If there is no pre-deploy step, the setting did not take — and then the `/health/ready` health check did not apply either, so the release is live on a behind-head schema (`/health/ready` returns 503 `db_unavailable` with `details.reason = "schema_behind"` and the startup ERROR is in the log): at once run `alembic upgrade head` from the laptop (step 3's environment), fix step 7, and redeploy. 1a serves no route that reads the new `invites` columns, so the window is harmless in 1a; in any later PR it would not be.
9. `alembic current` shows `0004_invites_reusable (head)`; `alembic check` (valid now that the database is at head) prints "No new upgrade operations detected."; paste both outputs, the step 6 output and the deploy-log lines into the PR.
10. Streamlit smoke check (F§6.3), including creating an invite in Streamlit to prove inserts still work with the new columns.

If step 4 is skipped by mistake, `0001` fails with "relation already exists", the deploy fails and the previous release keeps serving; run steps 3–9 and redeploy. If `0003` raises its precondition error, the whole upgrade rolls back; go back to step 0. **Never downgrade production below `0003`** (it would disable the ops lockdown); to back out `0004` only, `alembic downgrade 0003_lockdown`.

**Local dev** (README): fresh database → `cd backend && alembic upgrade head`; a database made by the old `create_all` → `alembic stamp 0001_baseline && alembic upgrade head`. Tests keep `create_all` in fixtures.

### Compatibility with the frozen Streamlit app (F§3.4, F§6.2)

| Change | Effect on frozen Streamlit |
|---|---|
| `alembic_version` table; RLS + revoked grants | None: its ORM never maps `alembic_version`; it connects with the same pooler role as the API, which owns the tables or has BYPASSRLS (runbook step 0, from the ops lockdown record). |
| `ix_hymns_church_hymnal` | None. |
| `invites.reusable` (server default `false`) | Its inserts get `false`, so a code-only invite it creates is **single-use in the new app**; Streamlit's own accept ignores the flag (known gap, F§6.2). |
| `invites.accepted_by` | Not mapped; its updates leave it untouched. |
| Code-only single-use invites stamped by the new app | Streamlit's `list_invites` already hides accepted rows, so used links disappear from its list too. |
| Churches created via `POST /churches` | Visible in Streamlit (`settings = {}`, owner membership, seeded hymns — the same rows its own create makes). Its switcher still keys by name (inv A5), a frozen bug. |
| Memberships created via accept | Visible in Streamlit; roles are always `member`/`admin` (never `owner`). |

No JSON shapes Streamlit reads are changed. `churches.settings` is not written by slice 1.

---

## Frontend changes

Before writing Next.js code, read the relevant guide in `frontend/node_modules/next/dist/docs/` (frontend/AGENTS.md): `proxy.ts` not middleware; `useSearchParams` needs a Suspense boundary; check that `window.history.replaceState` integrates with the App Router in Next 16.

### Dependencies and tooling (1a)

- Runtime: `@tanstack/react-query` v5.
- Dev: `jsdom`, `@testing-library/react`, `@testing-library/dom`, `@testing-library/user-event`, `@testing-library/jest-dom`, `@vitejs/plugin-react`, `openapi-typescript` — versions compatible with pinned Vitest 3.
- Scripts: `"gen:api": "openapi-typescript src/lib/api/openapi.json -o src/lib/api/schema.d.ts"`.
- `vitest.config.ts`: the two projects of F§5.2 (`unit` node `*.test.ts`, `dom` jsdom `*.test.tsx` with `src/test/setup-dom.ts`).
- `eslint.config.mjs`: `"react/no-danger": "error"`.
- shadcn (base-nova) components added with `npx shadcn@latest add input label tabs alert alert-dialog combobox`; `button` gains `size: { touch: "h-11 px-4" }`.

### File map

```
src/app/layout.tsx                          + <Providers> (client) around children; Toaster stays
src/app/providers.tsx                       QueryClientProvider (1a)
src/app/login/page.tsx                      reads ?next and ?select_account (1b)
src/app/join/page.tsx + join-client.tsx     public invite page (1b)
src/app/(signed-in)/layout.tsx              session → useMe → post-login redirect → MeProvider (1a; redirect in 1b)
src/app/(signed-in)/welcome/page.tsx        1a: stub — the slice-0 "No church yet" / "Creating or joining a church is
                                            coming in the next update." card under AppHeader (account menu with Log out);
                                            1b: replaced by the Join / Create tabs
src/app/(signed-in)/(church)/layout.tsx     church resolution, AppHeader, ChurchProvider, keyed remount (1a)
src/app/(signed-in)/(church)/page.tsx       placeholder cards (moved from src/app/page.tsx; no-church card removed)
src/components/app/app-header.tsx           moved from components/app-header.tsx; hosts ChurchSwitcher + AccountMenu
src/components/app/church-switcher.tsx      DropdownMenu + RadioGroup + "Join or create a church…" (1b adds the item)
src/components/app/account-menu.tsx         name, email, role label, Log out
src/components/app/{empty-state,error-state,pending-button,confirm-dialog,page-header}.tsx   UI kit (F§4.8)
src/components/onboarding/join-invite.tsx   code → preview → accept state machine; used by /join and /welcome
src/components/onboarding/create-church-form.tsx
src/components/app/timezone-combobox.tsx    TimezoneCombobox {value, onChange, error}: Base UI Combobox with `items`, at most
                                            50 filtered matches and a "Type to search" hint (the F§4.9.5 pattern, built here
                                            per F§7.2), or a text input when Intl.supportedValuesOf is missing; reused by
                                            6a's church profile form. Slice 3's SearchCombobox follows the same pattern for
                                            the hymn picker; it is not used for time zones.
src/lib/api/client.ts                       moved from lib/api.ts (+ api.test.ts → client.test.ts)
src/lib/api/{errors,timeouts,types}.ts, openapi.json, schema.d.ts
src/lib/queries/{client,keys,auth-events,me,church,onboarding,membership}.ts
src/lib/auth.ts                             getAccessToken(), useSignOut()
src/lib/church.ts                           pickActiveChurch (+ excluded ids), roleLabel, read/storeChurchId, useStoredChurchId;
                                            types re-exported from api/types
src/lib/church-context.tsx                  ChurchProvider, useChurch()
src/lib/storage.ts, urls.ts, post-login.ts, timezones.ts
src/lib/idempotency.ts                      createKeyTracker() (1b; 5b's createSendKeyTracker builds on it)
src/lib/supabase/proxy.ts                   PUBLIC_PATHS + next
src/test/{setup-dom.ts,render.tsx,fake-api.ts,fixtures/}
```

### API client and query layer (1a)

- `client.ts`: `apiFetch<T>(path, opts)` stays backward compatible and adds `method`, `json`, `idempotencyKey`, `ifMatch`, `timeoutMs` (default 20 000), `signal` (combined manually with the timeout). `ApiError` gains `fields`, `requestId`, `retryAfterSeconds`, `details`. `requestId` = `error.request_id` from the body, falling back to the `X-Request-Id` response header when the body lacks it (non-JSON bodies, proxy errors; ops handoff). Client codes: `network_error`, `timeout` ("This is taking too long. Try again."), `aborted`. `apiFetchBlob` is slice 5a.
- `timeouts.ts`: `POST /churches` 30 000; everything else in slice 1 uses the default.
- `errors.ts`: `ApiErrorCode` union mirroring `domain_errors.ERROR_CODES` (F§1.5 plus `db_unavailable`) plus client codes; `InviteRejectReason` union; `isNoChurchAccess(e)` = `e.code === "forbidden" && e.details?.reason === "no_church_access"`.
- `types.ts`: `Church = components["schemas"]["ChurchOut"]`, `Me = components["schemas"]["MeOut"]`, `InvitePreview`, `InviteAccepted`. `lib/church.ts` stops declaring its own `Church`/`Me`.
- `auth.ts`: `getAccessToken()` (Supabase `getSession`, throws `ApiError(401, "unauthenticated", …)` when absent); `useSignOut()` → `(opts?: {keepPendingInvite?: boolean; next?: string}) => Promise<void>` implementing Flow D; it always calls `supabase.auth.signOut({ scope: "local" })`, never the global default.
- `useApi()` (in `queries/client.ts`): `{ user: <T>(path, opts) => …, church: <T>(path, opts) => … }`; `church` reads `useChurch().id` and throws if used outside `ChurchProvider`.
- `queries/client.ts`: the `QueryClient` of F§4.4; `handleAuthErrors` emits `authEvents.signOutRequired()` on 401 and `authEvents.churchAccessLost(churchId)` on `isNoChurchAccess`. `churchId` comes from the query key (`["church", id, …]`) or from `mutation.meta.churchId` (set automatically by a `useChurchMutation` helper).
- `queries/keys.ts`: the full key factory of F§4.4 (later slices only add entries). Slice 1 uses `keys.me()` and `keys.churchProfile(id)`.
- `queries/me.ts`: `useMe()` → `GET /me` via `api.user`.
- `queries/church.ts`: `useChurchProfile(id)` → `GET /church` with `churchId: id`.
- `lib/idempotency.ts` (1b): `createKeyTracker({ fingerprint = stableStringify })` → `{ keyFor(body): string; settle(outcome: "success" | "client_error" | "uncertain"): void }`. `keyFor` returns the current key when the body's fingerprint matches the pending one, else a new `crypto.randomUUID()`. `settle("success")` (2xx) and `settle("client_error")` (any 4xx) drop the key; `settle("uncertain")` (`network_error`, `timeout`, `aborted`, 5xx) keeps it so an identical retry replays. `stableStringify` sorts object keys. 5b's `createSendKeyTracker` is this tracker with the draft fingerprint.
- `queries/onboarding.ts` (1b): `useCreateChurch()` (mutation; the form holds one `createKeyTracker()` per mount in a ref, calls `keyFor(body)` on each submit and `settle(...)` from the mutation result; the mutation marks 422 and 429 as handled locally), `usePreviewInvite()` and `useAcceptInvite()` (mutations — the code is a secret and never goes into a query key).
- `queries/membership.ts` (1b): `useMembershipChanged()` → `async ({ selectChurchId }: { selectChurchId?: string | null }) => void`: if given, `storeChurchId(selectChurchId)`; `await queryClient.fetchQuery({ queryKey: keys.me(), staleTime: 0 })` so the new church is in `/me` **before** navigation (otherwise the layout's `pickActiveChurch` would fall back and overwrite the stored id); then `router.replace(me.churches.length ? "/" : "/welcome")`. 6b calls it with `selectChurchId: null` after leave/delete.

### Storage and URL helpers

- `storage.ts`: `readSession/writeSession/removeSession/readLocal/writeLocal/removeLocal`, all try/catch, all no-ops on the server. Keys: `wsb:pendingInviteCode`, `wsb:postLoginPath` (session); `activeChurchId` (local, unchanged name).
- `urls.ts`:
  - `safeInternalPath(raw): string | null` — string ≤ 512; starts with exactly one `/`; no `//`, `\`, control characters, whitespace, `?`, `#`, or `..` segment; first segment in `{join, builder, services, settings, welcome}` with a segment boundary (`/joinx` rejected).
  - `extractInviteCode(input): string` — trimmed; if it parses as a URL (or contains `?code=`/`&code=`), the decoded `code` param; else the trimmed input.
  - `buildInviteUrl(code, origin = window.location.origin)` → `${origin}/join?code=${encodeURIComponent(code)}` (used by 6b).
  - `safeHttpsUrl(raw): string | null` — `https:` URLs only (first used in 3).
- `post-login.ts`: `storePostLoginPath(path)` stores `{path, at}`; `peekPostLoginPath(now)` returns the path if `safeInternalPath` accepts it and it is < 10 min old; `clearPostLoginPath()`.
- `timezones.ts`: `listTimezones(): string[] | null` (`Intl.supportedValuesOf` or null), `browserTimezone()`, `defaultTimezone(list)`.

### Routing, proxy and login (1b)

- `lib/supabase/proxy.ts` (proxy.ts:4, 34-38): `PUBLIC_PATHS = {"/login", "/auth/callback", "/join"}`. A signed-out request to any other path redirects to `/login`, with `?next=<pathname>` when the pathname is not `/`. `url.search` is **reset** (path only), which also stops OAuth parameters leaking into `/login` (inv §0 item 1).
- `/login` (login/page.tsx:28-31): `next = safeInternalPath(searchParams.get("next"))`; if set, `storePostLoginPath(next)` before `signInWithOAuth`. `?select_account=1` adds `queryParams: { prompt: "select_account" }`. `/auth/callback` is unchanged (still redirects to `/`; nothing new on the Supabase allow-list).
- `(signed-in)/layout.tsx` follows the stored path. It is done here, not in the root page, because the `(church)` layout would otherwise redirect a zero-church user to `/welcome` first. In an effect (never during render, to keep SSR and hydration identical): `const target = peekPostLoginPath()`; if `target && target !== pathname` → `router.replace(target)` and keep the skeleton; if `target === pathname` → `clearPostLoginPath()`. `/join` clears it on mount (it sits outside this layout). The logic is idempotent under StrictMode's double effects.

### Layouts (1a)

- **`(signed-in)/layout.tsx`**: `useMe()`; skeleton until `/me` and the post-login check are done; `ErrorState` on non-401 failure; provides `MeContext` (`useMeContext()` → `Me`), which slice 2 uses for the draft key and pruning.
- **`(church)/layout.tsx`**:
  1. `activeId = useStoredChurchId()` (`lib/church.ts`): `useSyncExternalStore(subscribe, getSnapshot, () => undefined)`. The client snapshot is a module-level value read from `localStorage` once, on first client use, and updated by `storeChurchId`, which notifies subscribers in this tab (other tabs' writes are not followed until reload, so a tab never switches church under the user). The server/hydration snapshot is `undefined` = "not read yet". No effect initializes it, so the first client render that can pick a church already has the stored id. `excluded: Set<string>` state.
  2. While `activeId === undefined` → shell skeleton, no candidate. Then `candidate = pickActiveChurch(me.churches.filter(c => !excluded.has(c.id)), activeId)`; none → `router.replace("/welcome")`.
  3. `useChurchProfile(candidate?.id, { enabled: candidate != null })`; on success, `storeChurchId(profile.id)` only when `profile.id === candidate.id` and it differs from `activeId` (this persists the fallback pick; cached data for any other church can never overwrite the stored choice).
  4. Render `<AppHeader …/><ChurchProvider value={profile}><Fragment key={profile.id}>{children}</Fragment></ChurchProvider>`.
  5. Subscribes to `authEvents.churchAccessLost(id)`: if `id === candidate.id` → toast "You no longer have access to {candidate.name}.", add to `excluded`, `invalidateQueries(keys.me())`. The profile query's own 403 goes through the same path.
  6. Switching (`onSelectChurch(id)`): `storeChurchId(id)` (which updates `activeId`). An effect keyed on the active id cancels and removes `["church", oldId]` queries in its cleanup, after the new church has rendered.
  7. Tests reset the module-level value with `resetStoredChurchIdForTests()`; `storeChurchId(null)` on sign-out resets it too.

### Pages (1b)

- **`/welcome`**: F§4.1. Uses `useMeContext()`; title/sub per Flow A/C; `Tabs` bound to `?tab=`. Join tab = `<JoinInvite initialCode={readSession(pendingInviteCode)} autoPreview />`; Create tab = `<CreateChurchForm />`. The minimal header is `AppHeader` without the switcher.
- **`/join`**: server `page.tsx` exports `metadata` (title "Join a church", `robots: noindex`) and renders a client component in `<Suspense>`. Mount effect: capture `code` → `writeSession` → `history.replaceState(null, "", "/join")`; `clearPostLoginPath()`. Determines signed-in state with `supabase.auth.getSession()`; signed in → `useMe()` for the email and `<JoinInvite initialCode=… autoPreview />`.
- **`JoinInvite`** states: `enter` (Welcome only) → `previewing` → `preview(alreadyMember)` → `joining` → done; `rejected(reason, message)`; `error(retryable)`. It never stores rejection text. The `preview` copy and button label follow `already_member` (Flow B step 4).
- **`CreateChurchForm`**: native `<form onSubmit>`; controlled inputs; Enter submits; submit disabled while pending. On submit: client checks (Flow A) → `keyFor(body)` → mutate → `settle(...)`. 422 → inline field message + focus; 429 → inline alert; network/timeout/5xx → toast, key kept for an identical retry. On success `useMembershipChanged({ selectChurchId: church.id })` + toast.
- **Home `/`**: the slice-0 placeholder cards, reading the church from `useChurch()`.

### Draft store

Slice 1 does not use the draft store (built in slice 2). It provides what slice 2 needs: `useMeContext().user.id` for the key, `me.churches` for pruning, and the `(church)` keyed remount.

---

## Behavior changes vs Streamlit

| # | Streamlit today | New app | Reason |
|---|---|---|---|
| 1 | Join/create only at zero churches (app.py:340-342) | Available any time from the switcher; an invite link works for users who already have churches (inv A3 "silently ignored") | Decision 9 |
| 2 | `/?invite=CODE` captured at the root (ui_helpers.py:10-18) | `/join?code=CODE`, public, stored in sessionStorage across sign-in, removed from the address bar | Decision 6; F D14 |
| 3 | `/?church=ID` overrides the switcher on every rerun | Not supported | Bug (inv A3) |
| 4 | Join is one step | Preview (church, role, expiry) then **Join {church}** | Safer bearer-code UX (a forwarded or mistaken link never joins silently). **Departs from owner decision 6's wording** ("opening the link … joins the church") and follows F§4.3; **needs the owner's answer before 1b starts.** If approved, F§4.3 records it as an amendment to decision 6. If declined, F§4.3 changes to auto-accept after sign-in and this slice adopts the fallback: `/join` calls `POST /invites/accept` right after sign-in (a `JoinInvite autoAccept` prop, a "Joining…" skeleton card) and goes straight to Flow B step 5's selection, toast and `/`; Flow B step 4 (the preview card) then applies only to the Welcome tab's pasted code, and the rejection and email-mismatch cards are unchanged. The `/join` DOM tests, acceptance criterion 10 and manual check 2 change with it (§Testing). |
| 5 | New code-only invites are reusable for 7 days | New invites are single-use unless marked reusable (6b). Pre-existing code-only invites stay reusable (0004 data step). Code-only invites created later by frozen Streamlit are single-use here. | Decision 6 |
| 6 | Email-bound invite reopened by its accepter → "already been used" | Same user, still a member → success "You're already a member of {name}."; removed member → still "already been used" | Idempotent accept |
| 7 | Existing member accepting a code-only invite: no-op | Same, and it does not consume a single-use invite | Admins can test their own link |
| 8 | Concurrent double-accept → 500 (PK violation) | 200 for both, one membership; one says "Joined", the other "already a member" | F§7.4 |
| 9 | Invite with a bogus role → `IntegrityError` 500 | `owner` → joins as admin; other unknown → member; WARNING logged | Safety until 6b's CHECK |
| 10 | Used code-only invites stay listed | Single-use invites are stamped and drop off the pending list | Follows from 5 |
| 11 | Timezone is free text, default `America/New_York`, help text claims it drives first-Sunday and the 12-week window | Searchable IANA list defaulting to the browser's zone; server rejects non-IANA with "Unknown timezone."; help text says what it actually does | inv B2; F§7.4 |
| 12 | Double submit creates two churches; blank name / timezone checked before the server call (app.py:307-310) | Idempotency-Key reused only for an identical retry after an unknown outcome, new after any 4xx or edit; blank name / timezone checked on the client with the same messages | F§1.6 (as amended; same rule as 5a and 5b) |
| 13 | "Could not create church: {raw exception}" and `str(e)` on join errors (app.py:290-291, 319-320) | Only defined messages; unexpected errors show "Something went wrong. (Ref: …)" | F§1.5 never leak |
| 14 | Success messages never visible (rerun) | Toasts "Created {name}. You're the owner." / "Joined {name}." | inv §0 item 3 |
| 15 | Joined church becomes active via the alphabetical fallback | The joined or created church is explicitly selected | Correct with several churches |
| 16 | Captured code: typed value wins, blank falls back to the captured one (ui_helpers.py:50-55) | The field is prefilled with the captured code and exactly its content is used; it also accepts a pasted link | Simpler; same outcome in practice |
| 17 | Captured invite kept after creating a church | Kept until joined, rejected, dismissed ("Not now") or explicit Log out | Lets the user join after creating |
| 18 | Switcher keyed by name, hidden with one church | Keyed by id, always shown, shows role, hosts "Join or create a church…" | inv A5 bug; decision 9 |
| 19 | Losing access falls back silently; React slice 0 cleared the choice without re-picking | Toast "You no longer have access to {name}." and automatic fallback | F§7.3 |
| 20 | No logout at zero churches | Log out on every signed-in screen | inv A6 |
| 21 | Church switch leaves stale state (inv A7) | Keyed remount + query removal per church | F§4.2 |
| 22 | Log out keeps nothing app-side but session state | Clears the query cache, active church and `wsb:` session keys | F§4.2 |
| 23 | Signed-out deep links lose their query (proxy.ts:35-38 kept it but login dropped it) | `?next=<path>` round trip for allow-listed paths; queries never forwarded | F§4.3 |
| 24 | No limit on creating churches | At most 5 new churches per user per rolling 24 h (soft-deleted ones count); the 6th gets "You've created 5 churches in the last 24 hours. Try again later." | Each create copies the whole catalog into the shared database |
| 25 | Streamlit logout is per browser; slice 0's React Log out used supabase-js's default global scope | Every sign-out (Log out, automatic 401, account switch) ends this browser's session only | A single API 401 must not sign the user out on every device |

---

## Testing

TDD: each item below is written before its implementation. Characterization tests for `accept_invite` exist already (test_invites_repo.py); they are **ported** to the usecase first and kept green through the move.

### Backend — platform (1a)

- `test_domain_errors.py`: each `DomainError` subclass → status and default code; `field` → `fields`; `details` passthrough; `request_id` always present; `ApiError(details=…)`; `RateLimited` → 429 with a `Retry-After` header and `details.retry_after_seconds` equal to it; `ERROR_CODES["db_unavailable"] == 503`.
- `test_error_registry.py`: every key of `domain_errors.ERROR_CODES` appears as a string literal in the `ApiErrorCode` union in `frontend/src/lib/api/errors.ts` (read as text), so the union stays complete (ops handoff).
- `test_api_app.py` (extended): Pydantic 422 `fields` for missing, too-long and extra fields with the exact short messages; `require_church` 403 carries `details.reason = "no_church_access"`; `require_admin` 403 has no `reason`; lifespan no longer creates tables (fresh SQLite URL → no tables after startup); the exact WARNING `schema revision None != head 0004_invites_reusable` on a fresh database **and no ERROR from the check** (so it cannot pass because the scripts were not found); RLS check is skipped on SQLite; readiness gate: with `APP_ENV=production` and `app.state.schema_state` stubbed to `behind` → `/health/ready` 503 `db_unavailable` with `details.reason = "schema_behind"`; `ahead` and `unknown` → 200; outside production `behind` → 200.
- `test_schema_check.py` (runs with the repo root as working directory, as pytest does): `alembic_config()` finds the scripts and head is `0004_invites_reusable`; `revision_state` on an empty SQLite file → `behind` (current `None`), after `upgrade head` → `current`, with `alembic_version` holding an unknown revision → `ahead`; `schema_diff` on a database at `0001_baseline` (`alembic upgrade 0001_baseline`, the stand-in for a stamped production) lists exactly the 0004 columns and FK; `scripts/schema_drift.py` exits 1 there and 0 at head.
- `test_idempotency.py` (store unit tests + a throwaway route): replay returns the same status/body and `Idempotent-Replayed: true`; 4xx stored; 5xx not stored and re-executed; a `RateLimited` raised inside the call → 429 with `Retry-After`, not stored, and the same key re-executes the call; different body → 422 `idempotency_mismatch`; key scoped per user and per route; concurrent same-key requests (threads + barrier) run the call once; TTL expiry with an injected clock; malformed key → 422.
- `test_route_guards.py`: walks `app.routes`; every route not in `PUBLIC` (`/health`, `/health/ready`, `/openapi.json`, `/docs`, `/docs/oauth2-redirect`, `/redoc` — F§1.2 as amended) or `USER_SCOPED` (`GET /me`, `POST /churches`, `POST /invites/preview`, `POST /invites/accept`) has `require_church` in its dependency tree; `USER_SCOPED` routes have `get_current_user`. A second test builds an app with a deliberately unguarded route and asserts the walker flags it.
- `tests/api_helpers.py`: `auth_headers(email)`, `church_headers(email, church_id)`, fixture `isolation_world` (church A with member a@, church B with member b@, outsider o@), and `assert_church_isolated(client, method, path, *, world, json=None, resource_path_b=None)`: (1) outsider and a@ with `X-Church-Id = B` → 403 `forbidden` + `no_church_access`; (2) when `resource_path_b` is given, a@ with `X-Church-Id = A` → 404 `not_found`. Used on `GET /church`.
- `conftest.py`: autouse no-network fixture (patches `socket.socket.connect`; localhost/127.0.0.1 allowed) plus a test proving an outbound connect raises; `pg_db` fixture (binds `TEST_DATABASE_URL`, truncates every table except `alembic_version` before each test, skips without the env var).
- `test_migrations.py`: SQLite `upgrade head` on an empty file → `schema_diff` empty → `downgrade base` → `upgrade head` (this also proves 0002's downgrade leaves the baseline's index for 0001 to drop); every revision file defines `downgrade`; `0004` data step marks only `email IS NULL` rows reusable (seed rows at `0003`, upgrade, assert); `alembic upgrade 0001_baseline:head --sql` renders no `CREATE TABLE`. `@pytest.mark.postgres`: upgrading as a test-created non-superuser role without BYPASSRLS, with one `public` table owned by a different role, `0003` raises the precondition message and leaves every table's `relrowsecurity` unchanged (whole upgrade rolled back); run twice → idempotent.
- `test_openapi_contract.py`: committed `frontend/src/lib/api/openapi.json` equals the live schema; failure prints `python backend/scripts/export_openapi.py`.
- `test_no_streamlit_in_core.py`: extended as above.
- `test_ci_workflow.py`: asserts the `backend-postgres` job, its alembic steps and `pytest -m postgres`, and the frontend `gen:api` + `git diff --exit-code` step. It does **not** check the Postgres major: ops' `test_ops_workflows.py` already fails when `ci.yml`'s `postgres:<N>` image differs from `PG_MAJOR` in `backup.yml`, and that stays the only such check.
- `test_foundation_setup.py`: asserts `alembic` and `tzdata` in `backend/requirements.txt`; `backend/railway.toml` with the pre-deploy command and `healthcheckPath = "/health/ready"`; `alembic.ini` uses `%(here)s` for `script_location` and `prepend_sys_path`.
- `@pytest.mark.postgres`: the ops concurrent-first-request test re-run on Postgres (both 200, same user id).

### Backend — onboarding (1b)

- `test_timezones.py`: `America/New_York`, `UTC`, `Europe/London` valid; `america/new_york`, `Mars/Olympus`, `../etc/passwd`, `""` invalid.
- `test_usecase_onboarding.py` (ported from test_invites_repo.py accept tests and streamlit_tests/test_onboarding.py, then extended):
  - every check 0–6 → exact message and reason; **order** (revoked beats church-unavailable after `soft_delete_church`; expired beats used; used beats email mismatch);
  - accept adds membership with the invite role; `already_member` no-op keeps `owner`;
  - code-only single-use: first user joins and stamps `accepted_at`/`accepted_by`; second user → `used`; same user again → `already_member`; removed member → `used`;
  - reusable: three users join, never stamped, still listed by `list_invites`;
  - existing member does not consume a code-only single-use invite; does stamp an unaccepted email-bound one;
  - email-bound case-insensitive match; legacy accepted email-bound with `accepted_by` NULL → `used`;
  - `_clamp_role`: `owner` → `admin`, `foo` → `member`, WARNING logged;
  - naive `expires_at` treated as UTC; injected `now`;
  - preview never writes (row counts unchanged) and returns exactly five fields; an invite stored with role `owner` previews as `admin` and `foo` as `member`; a naive stored `expires_at` comes back timezone-aware UTC; `already_member` true for an existing member and false otherwise;
  - `ensure_membership` returns `inserted = False` when the row already exists; an accept whose membership insert is skipped returns `already_member: true` with "You're already a member of {name}.";
  - `create_church`: trimming, the three messages, owner membership, seeded count = catalog count with identical column values, atomicity (seed raising → no church, no membership); cap: 5 creates in 24 h succeed, the 6th raises `RateLimited` with the exact message and `retry_after_seconds` (also in `details`) = time until the oldest is 24 h old; a church created 25 h ago does not count; a soft-deleted one does; a church where the user is only `admin` does not.
- `test_api_churches.py`: 401 without token; 201 body; `/me` then lists the church; the same church is accepted by `GET /church`; `X-Church-Id` of another church is ignored; duplicate names allowed; a second church for an existing member; 422 messages with `fields`; name of 201 chars → `fields.name` "Too long (max 200 characters)."; extra field → 422; Idempotency-Key replay → one church, identical body; mismatch → 422 `idempotency_mismatch`; blank name with key K → 422, then the corrected body with a new key → 201 (the flow the client uses); with five churches the user created in the last 24 h already seeded through `repos.churches.create_church` (not through HTTP, so slice 2's 3-per-minute burst bucket is never reached), the next `POST /churches` → 429 `rate_limited` with the cap message, a `Retry-After` header and `details.retry_after_seconds`, and a retry with the same Idempotency-Key is re-executed, not replayed (429 again, without `Idempotent-Replayed`). Slice 2 must keep this test passing unchanged.
- `test_api_invites.py`: 401; each rejection via HTTP → 400 `invite_rejected` with exact message and `details.reason`; blank code → 422 with `fields.code`; response key sets exactly as specified (no id/code/church_id in preview); preview of an invite stored with role `owner` → 200 with `role: "admin"` (not a 500); on SQLite, `expires_at` in the JSON ends in `Z` or `+00:00`; `X-Church-Id` ignored; after accept `GET /church` with the new id → 200; `caplog` contains neither the code nor the email after preview/accept/reject.
- `@pytest.mark.postgres`: two users accept one single-use invite concurrently → exactly one `Joined`, one `used`, one membership; one user double-accepts concurrently (single-use and reusable invites) → both 200, one membership, exactly one `already_member: false`; create church with a 700-row catalog completes in < 3 s.
- Removed with their assertions ported: accept tests in `backend/tests/test_invites_repo.py`; `streamlit_tests/test_onboarding.py` (all five: typed-wins / fallback / blank → `extractInviteCode` + JoinInvite tests; create seeds → usecase + API tests; accept captured invite → usecase + `/join` tests).

### Frontend

Unit (`*.test.ts`, node):
- `urls.test.ts`: `safeInternalPath` accepts `/join`, `/builder/hymns`, `/settings/people`; rejects `//evil.com`, `/\evil.com`, `https://evil.com`, `javascript:alert(1)`, `/joinx`, `/join?code=x`, `/settings/../x`, `""`, 600-char paths. `extractInviteCode` for a raw code, full URL, scheme-less `…/join?code=`, encoded code, whitespace. `buildInviteUrl` round-trips through `extractInviteCode`. `safeHttpsUrl`.
- `post-login.test.ts`: store/peek/clear; expiry after 10 min; invalid stored path ignored.
- `client.test.ts` (existing api.test.ts cases kept): JSON body + method; `Idempotency-Key` header; timeout → `timeout`; abort → `aborted`; error body `fields`/`details`/`request_id` parsed; `requestId` taken from the `X-Request-Id` header when the body has no `request_id` (including a non-JSON 502 body); `Retry-After` parsed.
- `idempotency.test.ts`: same body → same key until settled; `settle("uncertain")` keeps it; `settle("client_error")` and `settle("success")` drop it; a changed body → new key even while one is pending; `stableStringify` ignores key order.
- `church.test.ts`: `pickActiveChurch` with excluded ids; `roleLabel`; `useStoredChurchId` returns `undefined` from the server snapshot, the stored id on the client, follows `storeChurchId` in the same tab and ignores a `storage` event from another tab.
- `queries/client.test.ts`: `isRetryable`; `handleAuthErrors` emits sign-out on 401, `churchAccessLost(id)` only for `no_church_access` (not for a role 403), with the id from the key or mutation meta.
- `timezones.test.ts`: default = browser zone when listed, else `America/New_York`; null list → text-input mode.
- `proxy.test.ts` (stubbed Supabase client): `/join?code=x` signed out passes through; `/builder?x=1` signed out → `/login?next=%2Fbuilder` with no other query; `/` → `/login` without `next`.

DOM (`*.test.tsx`, jsdom, `renderWithProviders` + `installFakeApi`):
- `timezone-combobox.test.tsx` (the Combobox pattern, owned by slice 1 per F§7.2; 6a extends this file): opens on click; renders at most 50 matches with the "Type to search" hint; typing `new york` (spaces for `_`) finds `America/New_York`; keyboard selection calls `onChange` with the IANA id; `error` renders below the field; a null zone list renders a plain text input with the same helper.
- `(church)` layout: stored id used; stale stored id → first church; with a cached profile for church A (first by name) and the stored id B, only `GET /church` with `X-Church-Id: B` is sent, the header never shows A's name, and the stored id stays B; `GET /church` 403 `no_church_access` → toast "You no longer have access to Grace.", `/me` refetched, next church confirmed; last church lost → `router.replace("/welcome")`; zero churches → `/welcome`; switching remounts children (a child's local state resets) and removes the old church's queries; a role 403 from a church query does **not** trigger fallback.
- `AppHeader`: radio list keyed by id with two same-name churches both selectable; "Join or create a church…" navigates to `/welcome`; account menu shows role label; Log out clears the query cache, `activeChurchId`, `wsb:pendingInviteCode` and calls `signOut({ scope: "local" })`; a 401 from any query also signs out with `scope: "local"`.
- `/welcome` stub (1a): renders the "No church yet" card and the account menu's Log out; replaced in 1b by the tests below.
- `/welcome`: zero-church copy vs has-church copy with back link; tab from `?tab=create`; pending code → info alert + automatic preview; Create happy path (request body, `Idempotency-Key` present); blank name or empty time zone → the exact message inline, focus, **no request sent**; server 422 "Unknown timezone." → inline + focus, then fixing the field and resubmitting sends a **new** key and succeeds; network error → retry with the same body sends the **same** key; network error → edit the name → retry sends a new key; 5xx → retry sends the same key; 429 → inline alert with the server message and no global toast; success → `/me` refetched **before** `router.replace("/")`, stored church id = new id, toast.
- `/join`: signed out → sign-in card, `sessionStorage` holds the code, `history.replaceState` called with `/join`, link to `/login?next=/join`; signed in → preview card copy (member/admin, email-bound line, expiry) → Join → accept request body `{code}`, pending code cleared, church selected, toast "Joined Grace."; preview with `already_member: true` → "You're already a member of Grace." with no role line and an **Open Grace** button, whose accept selects the church and toasts "You're already a member of Grace."; "Use a different Google account" calls `signOut({ scope: "local" })`; each rejection → message + "Ask for a new invite link." and code cleared; `email_mismatch` → "Use a different Google account" keeps the code and goes to `/login?next=/join&select_account=1`; no code → incomplete-link card. *If the owner declines the preview step (behavior change 4):* signed in → the accept request `{code}` is sent on mount with no preview request and no Join tap, then the same selection, toasts ("Joined Grace." / "You're already a member of Grace.") and `/`; rejections and `email_mismatch` as above; the preview-card cases move to the `/welcome` Join-tab tests.
- `/login`: valid `next` stored; invalid `next` ignored; `select_account=1` passes `prompt: "select_account"`.
- `(signed-in)` layout: stored post-login path `/join` → `router.replace("/join")` before children render; same path → cleared.

### Manual checks (appended to `docs/manual-verification.md` as "Slice 1"; production Vercel URL at 375 px and desktop)

1. (After 1a) Runbook step 0 result recorded; Railway's Config-as-code path is `/backend/railway.toml`; the merge deploy log shows the **pre-deploy** `alembic upgrade head` and a passing `/health/ready` health check; `alembic current` = head; `alembic check` clean (outputs in the PR). A new Google account signing in right after the 1a merge lands on the stub `/welcome` (not a 404) and can log out.
2. Signed out, open a fresh single-use `/join?code=…` link (create it in Streamlit or with the CLI until 6b): the address bar shows `/join`; sign in; preview shows the church and role; **Join** lands on home with that church active and the toast. (With the behavior change 4 fallback: signing in joins directly, with no preview or tap.)
3. Reopen the same link with another Google account → "This invite has already been used." + "Ask for a new invite link."; with the first account → the preview says "You're already a member of …" and **Open …** switches to it.
4. Email-bound invite opened with the wrong account → "Use a different Google account" shows Google's account chooser → correct account → joins.
5. A brand-new Google account lands on `/welcome`; create a church with the default time zone; it becomes active with role Owner; its hymn count matches `hymn_catalog`.
6. Double-tap **Create church** on a slow connection → one church. Submit with a blank name → "Church name is required." with no request in the network panel; fill it in → the church is created.
7. From the switcher, "Join or create a church…" → create a second church → both listed; switching changes the role shown.
8. Remove your membership of one church in Streamlit while the new app is open; refocus → "You no longer have access to …" and fallback.
9. Log out from `/welcome`; a session signed in on a second device stays signed in.
10. No horizontal scroll at 375 px on `/welcome`, `/join`, home; inputs don't zoom on iOS; tap targets ≥ 44 px.
11. Streamlit smoke (F§6.3) plus: create an invite in Streamlit, soft-delete a test church in Streamlit and confirm its invite shows "This invite has been revoked." in the new app.

---

## Acceptance criteria

1. On empty SQLite and on CI Postgres, `alembic upgrade head` matches the models (`schema_diff` empty, `alembic check` clean); `downgrade base` then `upgrade head` succeed; `0003` refuses, with its precondition message and without partial changes, when the app role neither owns a table nor has BYPASSRLS. *(CI)*
2. The RLS precondition (runbook step 0) is recorded; production is stamped per the runbook, with the step 5 SQL and step 6 drift output as expected; Railway's Config-as-code path is `/backend/railway.toml` and the merge deploy's pre-deploy step reaches `0004_invites_reusable (head)`; `alembic check` is clean; all outputs are recorded in the 1a PR. *(deployed)*
3. The API lifespan no longer calls `create_all`; startup logs a revision mismatch (found from any working directory) and, on Postgres, any table without RLS; in production a schema behind head makes `/health/ready` return 503, so such a release fails its Railway health check. *(test + deployed log)*
4. `test_route_guards.py`, `test_openapi_contract.py` and the frontend `gen:api` diff run in CI; a deliberately unguarded church route fails the guard test. The `backend-postgres` job runs the alembic cycle and `pytest -m postgres`, and all three jobs are required on `main`. *(CI)*
5. Every `DomainError` maps to the F§1.5 registry (including `db_unavailable`), which the frontend `ApiErrorCode` union mirrors; a Pydantic 422 carries `fields`; every error body has `request_id`, and the client falls back to the `X-Request-Id` header; `require_church` 403s carry `details.reason = "no_church_access"`; every 429 is a `RateLimited` with `Retry-After` and `details.retry_after_seconds`, and `run_idempotent` never stores it; the CI Postgres image major equals `PG_MAJOR` in `backup.yml` (checked by ops' `test_ops_workflows.py`). *(test)*
6. `POST /churches` with valid input returns 201 `{id, name, role: "owner"}`, creates exactly one church, one owner membership and one hymn per catalog row in one transaction; the three validation messages are exact (and checked on the client first for blank name/time zone); replaying the same Idempotency-Key returns the first response and creates nothing; after a 422 the corrected resubmit uses a new key and succeeds; the 6th create by one user within 24 h returns 429 `rate_limited`. *(test)*
7. `POST /invites/preview` and `POST /invites/accept` enforce checks 0–6 in order with the exact messages and `details.reason`; preview writes nothing and returns exactly `church_name`, `role` (clamped), `expires_at` (with offset), `email_bound`, `already_member`. *(test)*
8. A single-use invite admits exactly one new user, including under concurrent accepts on Postgres; the same user's sequential repeat accepts return 200 `already_member: true`; the same user's concurrent accepts both return 200 with one membership, exactly one reporting `already_member: false`; reusable invites admit several users; existing members never change role and never consume a code-only invite. *(test)*
9. Invite codes never appear in an API path, a log line or the browser address bar after `/join` loads. *(test + deployed)*
10. Opening `/join?code=…` signed out, signing in and tapping **Join** joins the church and makes it active (with the behavior change 4 fallback, signing in joins without the tap); the same works for a user who already has churches. *(deployed)*
11. A zero-church user is sent to `/welcome`, can create a church (browser time zone preselected; non-IANA rejected with "Unknown timezone.") and lands on home with it active. *(test + deployed)*
12. The switcher lists churches by id with roles and offers "Join or create a church…"; switching remounts church-scoped UI and removes the old church's queries; resolution never requests or shows a church other than the stored one first. After the 1a merge alone, a zero-church user lands on the stub `/welcome`, never a 404. *(test + deployed)*
13. Losing access to the active church shows "You no longer have access to {name}." and selects the next church, or `/welcome` when none remain; a role-based 403 never triggers this. *(test)*
14. Log out (from any screen, including `/welcome`) clears the query cache, the stored church and the `wsb:` session keys; a 401 signs out but keeps a pending invite and returns the user to their allow-listed path after sign-in; every sign-out uses `scope: "local"`. *(test)*
15. `.tsx` DOM tests run in the `dom` Vitest project; `react/no-danger` is enforced; the UI kit components exist with tests for `ErrorState` retry and `PendingButton`. *(CI)*
16. No module imported by `api.main` imports `streamlit`; `streamlit_tests/test_onboarding.py` is gone and each of its assertions exists as a backend or frontend test. *(CI)*
17. Manual checklist items 1–11 pass on the production URL at 375 px and desktop, and the Streamlit smoke check passes after each of the two merges. *(deployed)*

---

## Risks and open questions

1. **Open, owner: preview-then-Join vs decision 6's "opening the link joins".** Behavior change 4 keeps an explicit **Join** tap (F§4.3) as a safeguard for bearer codes. The owner's answer is needed before 1b starts. If approved, F§4.3 records it as an amendment to decision 6. If declined, F§4.3 changes to auto-accept after sign-in and this slice adopts the `JoinInvite autoAccept` fallback, updating Flow B, behavior change 4 and the `/join` DOM tests as described there (a small change to `JoinInvite`).
2. **Unknown production drift.** The drift script after stamping may report differences beyond `ix_hymns_church_hymnal`. Expand-safe ones go into `0002`; anything else (type or nullability mismatch) blocks the 1a merge until resolved with the owner. The runbook makes this a pre-merge step so a surprise never reaches a deploy.
3. **Seed time on production.** ~700 catalog rows through the Supabase pooler inside one transaction are expected well under 3 s with batched inserts, but this is unmeasured. The 1b PR records the timing from the Postgres CI test and one production create; above 5 s, switch the Postgres path to `INSERT … SELECT gen_random_uuid(), … FROM hymn_catalog` (Postgres 13+ built-in).
4. **In-memory idempotency store.** A retry that spans a Railway redeploy or restart loses the stored key and could create a second church. Accepted for one worker and one tester (F§1.6); revisit with the Postgres-backed store if `--workers` ever exceeds 1. The per-user creation cap bounds the damage either way.
5. **RLS precondition unknown until the ops record is read.** If the app role neither owns every table nor has BYPASSRLS, 1a waits on a manual ownership transfer (runbook step 0). `0003` refuses rather than half-applying, so a missed step fails the deploy instead of hiding rows from both apps.
6. **Railway config-as-code path.** If the service's config path is not `/backend/railway.toml`, neither the pre-deploy migration nor the `/health/ready` health check (F§3.3 as amended; `/health` remains the liveness probe) applies. Runbook steps 7–8 set and verify it; the production readiness gate turns keepalive red if a behind-head release ever runs.
7. **Browser support for the time-zone list.** `Intl.supportedValuesOf` needs Safari 15.4+; older browsers get the plain text field with server validation. Browser zone ids missing from Python's `tzdata` (e.g. very new zones) would be rejected; `tzdata` is pinned to a recent release to keep this rare.
8. **Google account chooser.** `prompt=select_account` must pass through Supabase's `queryParams` to Google; verify during 1b. If it does not, the email-mismatch card instead says "Sign out of Google in this browser, then try again."
9. **Next 16 `history.replaceState`.** The code capture relies on native `replaceState` integrating with the App Router; verify against the bundled Next docs before building `/join`. The fallback is `router.replace("/join", { scroll: false })` after capture.
10. **Vercel request logs** still record `/join?code=…` (F§7.4, accepted); single-use invites limit the exposure.
11. **Ops ordering.** Slice 1 assumes ops has merged `ensure_user`, the request-id contextvar and `insert_ignore`. If 1a starts first, it takes F§2.4/§2.5 as its first tasks rather than stubbing them.
