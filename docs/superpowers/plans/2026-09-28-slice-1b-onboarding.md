# Slice 1b — Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR 1b of slice 1, onboarding on the new app. A signed-in user with no church can create one: it is seeded with its own copy of the starter hymnal, and a durable cap allows 5 creates per user per 24 hours. `POST /churches` takes an Idempotency-Key, so a retried tap never makes a second church. A user can also join a church by invite: the invite link opens `/join`, survives sign-in, shows a preview card, and joins on one tap (`POST /invites/preview`, `POST /invites/accept`). `/welcome` gets real Join and Create tabs, the church switcher gains "Join or create a church…", and sign-in returns to the deep link it started from. `repos.invites.accept_invite` is removed and its tests are ported. The F §4.3 amendment (preview, then Join) is recorded, and manual checks 2–11 are written and then run on production. There is no migration: the head stays `0004_invites_reusable`. Production Streamlit (https://liturgy-frozen.streamlit.app/) is untouched.

**Architecture:** Below the API, `backend/timezones.py` (exact IANA check), the repos (`session=` parameters, `create_church_seeded`, `recent_owned_creations`, a bulk Core seed, `find_by_code`, `claim` and `ensure_membership`) and `backend/usecases/onboarding.py` import no FastAPI. The usecase module holds `create_church` with the cap, the shared invite checks 0–6, the role clamp, `preview_invite` and `accept_invite`. It calls repos through module attributes so tests can patch them. Each thin `def` route parses the body, resolves the user, and calls one usecase. `POST /churches` runs inside 1a's `run_idempotent`, and a 429 is never stored. The engine sets `hide_parameters=True`, so a database error's traceback never carries an invite code or an email. On the frontend:
- `lib/idempotency.ts`, `lib/post-login.ts` and `lib/timezones.ts` are small pure modules.
- `lib/queries/onboarding.ts` and `lib/queries/membership.ts` add the three mutations and `useMembershipChanged`, which stores the new church, refetches `/me` through `meQueryOptions` and goes to `/`.
- The components are `TimezoneCombobox`, `JoinInvite` and `CreateChurchForm`.
- The pages are `/join`, a Server Component with metadata around a client page in `<Suspense>`, which handles its own 401s, and `/welcome`.
- The proxy, `/login` and the `(signed-in)` layout carry the post-login path through Google sign-in.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141.1, Pydantic 2.13.5, SQLAlchemy 2.1.1, Alembic 1.20 (no new revision), tzdata, pytest 9 (SQLite locally; `postgres:17` in CI, `-m postgres`); Next 16.3.6, React 19.2.8, TanStack Query v5 (5.104 locked), Vitest 3.2.7 (`unit` and `dom` projects, jsdom, Testing Library), openapi-typescript 7, `@base-ui/react` 1.8.0 with shadcn 4.21.0 (base-nova), sonner; GitHub Actions (`backend`, `backend-postgres`, `frontend`, all required on `main`), Railway, Vercel, Supabase Postgres 17.6.

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md` (the 1b parts, Testing, Manual checks, AC6–AC17, Risks).
- Foundations ("F §n"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`.
- Slice 1a plan ("P1a"): `docs/superpowers/plans/2026-09-26-slice-1a-platform.md` (conventions, 1a names, the hand-offs to 1b; 1a minors are cited as T<n>-m<k>).
- Production facts: `docs/ops-runbook.md`; manual checks: `docs/manual-verification.md`.
- Facts checked for this plan (tree `0295b37`, 1a merged and live):
  - Backend baseline `697 passed, 5 skipped`, frontend baseline `126 passed` in 23 files, the Alembic head `0004_invites_reusable`, and 4 runbook owner markers.
  - Every task's code was run by its writer in a throwaway worktree at `0295b37`, with stand-ins built to the earlier tasks' interfaces where those were not yet written. The exceptions are the Postgres tests (Task 8, CI only), the pushes and CI runs (Tasks 8, 20, 21) and the OWNER steps.
  - Where the code and the outline disagreed, the code won. Each such case is stated in its task and summarised in clarifications 50–63.

## Global Constraints

"T<n>" below means Task n of this plan; "NB", "NF", "NC" are the planning notes on backend, frontend and carry-over items (their findings are folded into the clarifications).

**Commands and process**
- Python `.venv/bin/python` (3.11) from the repo root; cwd resets between commands; frontend in `(cd frontend && …)`;
  no foreground `sleep`. Test commands: `.venv/bin/python -m pytest -q <file> 2>&1 | tail -3`; suite
  `.venv/bin/python -m pytest -q | tail -1`; `(cd frontend && npx vitest run <file>)`; per frontend task
  `(cd frontend && npm test && npm run typecheck && npm run lint)`; T15, T17, T20 also run the build:
  `(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build)`.
- OpenAPI after any route or schema change: `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)`, both files committed with the route.
- Branch `claude/slice-1b-plan` from `0295b37`; first commit = the plan. Stage by name; `.claude/` stays untracked.
  `main` is protected (`backend`, `backend-postgres`, `frontend`; up to date): merge `origin/main` and rerun both
  suites before merge; `gh pr merge <N> --merge -R bbrown62450/church` only on the owner's explicit yes.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; subject "Area: plain words (F §x, S …)";
  TDD, failing test first, failure quoted. PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
  and "Tests: backend 697 → 797 passed, 5 → 9 skipped; frontend 126 → 221 in 23 → 34 files" (owner answer 4 is yes).
- Baselines: backend **697 passed, 5 skipped**; frontend **126 passed in 23 files**. If either differs, stop and ask.
  Cumulative counts after each task (recounted from the tests as written): backend 705 (T1), 717 (T2), 728 (T3), 746 (T4),
  761 (T5), 775 (T6), 799 (T7) passed with 5 skipped; 799 + 9 skipped (T8, four Postgres tests); 796 + 9s (T14 deletes the last
  three Streamlit onboarding tests); 797 + 9s (T19). Frontend (tests / files): 143/26 (T9), 152/28 (T10), 157/28 (T11), 163/29 (T12),
  171/31 (T13), 192/32 (T14), 204/33 (T15), 214/34 (T16), 220/34 (T17), 221/34 (T18); unchanged through T21. CI `backend-postgres`:
  `9 passed, 797 deselected, 1 warning` at the end. If a task's count differs from its stated line, stop and find the drift.
- Postgres is CI-only: T8's tests skip locally and first run on the draft PR (Q5). CI runs `python -m pytest -m postgres -q`
  (`ci.yml:63`, pinned by `test_ci_workflow.py`; do not edit), which hides passing tests' stdout, so the seed timing is a
  `UserWarning` read from the job log's "warnings summary" (clarification 41).
- Next 16 docs first (`frontend/node_modules/next/dist/docs/`): `useSearchParams` needs `<Suspense>` (use-search-params.md:80-88,
  :180-181); `metadata` only in Server Components; native `history.replaceState` integrates with the App Router
  (04-linking-and-navigating.md:345-347, :399-415).
- Base UI (F§4.9): generated components only, hand edits limited to variants (size tap targets at the call site);
  no `asChild` (`render`, `nativeButton={false}` for links); `DropdownMenuLabel` inside `DropdownMenuGroup`; sonner toasts.
- One DOM `afterEach` in `setup-dom.ts` (P1a); tests stub `Intl.supportedValuesOf` and
  `Intl.DateTimeFormat().resolvedOptions().timeZone`, never the runner's TZ; expiry tests use a midday-UTC `expires_at`.
- Layering: `usecases/*`, `timezones.py`, `domain_errors.py`, `db/*` import no fastapi/starlette/streamlit; routes
  parse, guard, call **one** usecase, no SQL, no try/except for domain errors; plain `def` routes (`run_idempotent` blocks).
- Log hygiene: never log invite codes, emails, bodies, tokens, query strings. Log lines: the four S INFO lines (`church_created`,
  `church_create_limited`, `invite_accepted`, `invite_rejected`) plus the role-clamp WARNING with the invite id. The engine sets
  `hide_parameters=True` (clarification 37), so an unhandled DB error's traceback (`api/errors.py:184`) carries no bound code/email.
- Not in 1b: `church_create` burst bucket (2), `/`→`/builder` (2), invite create/list/revoke UI (6b), `require_owner` (6b),
  `GET /church` new fields (2), deleting Streamlit onboarding code (7). `app.py`, `ui_helpers.py`, `streamlit_tenancy.py` untouched.
- Owner-marker check: `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = 4; 1b adds none.

**Server contract (exact)**
- `POST /churches` → **201** `ChurchOut {id, name, role: "owner"}`; guard user (`X-Church-Id` ignored);
  `responses=error_responses(401, 422, 429, 503)`. `CreateChurchIn {name: str = "" (max 200), timezone: str = "" (max 64)}`, `extra="forbid"`.
- `POST /invites/preview` → 200 `InvitePreviewOut {church_name: str, role: Literal["member","admin"], expires_at: datetime, email_bound: bool, already_member: bool}`;
  `POST /invites/accept` → 200 `InviteAcceptOut {church: ChurchOut, already_member: bool, message: str}`; both
  `InviteCodeIn {code: str = "" (max 256)}`, `responses=error_responses(400, 401, 422, 503)`, no Idempotency-Key.
- 422 `invalid_request`: "Church name is required." (`fields.name`); "Timezone is required." (`fields.timezone`);
  "Unknown timezone." (`fields.timezone`); "Enter an invite code, or open your invite link again." (`fields.code`);
  Pydantic "The request was not valid." with "Required." / "Too long (max N characters)." / "Not a valid value.";
  "Idempotency-Key must be a UUID." (no `fields`). 422 `idempotency_mismatch` "This request was already sent with different details.".
- 429 `rate_limited` "You've created 5 churches in the last 24 hours. Try again later." + `Retry-After: n` +
  `details.retry_after_seconds = n`, n = seconds until the oldest counted church is 24 h old, ceil, at least 1;
  never stored by `run_idempotent`; a same-key retry re-executes (no `Idempotent-Replayed`).
- Cap: count churches where the caller holds `owner` and `churches.created_at > now − 24 h`, soft-deleted included; ≥ 5 → 429.
- 400 `invite_rejected`, `details.reason` → message, in this order (code stripped first; 0 is the 422 above):
  1 `unknown` "Invalid invite code." · 2 `revoked` "This invite has been revoked." · 3 `expired` "This invite has expired."
  (`expires_at < now`, naive = UTC) · 4 `used` "This invite has already been used." (not reusable and accepted, unless
  `accepted_by == caller` and caller still a member) · 5 `church_unavailable` "This church is no longer available." ·
  6 `email_mismatch` "This invite was issued for a different email address." (case-insensitive vs `CurrentUser.email`).
- Accept messages: "Joined {name}." (`already_member: false`); "You're already a member of {name}." (`true`).
  Role clamp: `member`/`admin` as stored, `owner` → `admin`, anything else → `member`, WARNING with the invite id.
- Other: 401 `unauthenticated` "Please sign in."; 503 `auth_unavailable` "Sign-in is temporarily unavailable. Try again shortly.";
  500 `internal_error` "Something went wrong.". `fields` appears only on a 422 (`api/errors.py:146`; T3-m1): a 400 never has `fields`.
- Idempotency: key `(user_id, "POST", "/churches", Idempotency-Key)`, TTL 15 min, SHA-256 of sorted-keys JSON body;
  2xx and DomainError 4xx stored except `RateLimited`; 5xx and non-domain errors dropped; replay header `Idempotent-Replayed: true`.
- Log lines (one each): `church_created church_id=… user_id=… hymns_seeded=… duration_ms=…`;
  `church_create_limited user_id=… count=…`; `invite_accepted invite_id=… church_id=… user_id=… already_member=…`;
  `invite_rejected reason=… invite_id=…` (`invite_id=none` for unknown codes).

**Client copy (exact)**
- `/welcome` zero-church: H1 "Welcome to Worship Service Builder"; sub "Signed in as {email}. You don't belong to a church yet."
  Has-church: H1 "Join or create a church"; sub "Signed in as {email}."; link "← Back to {active church}". Tabs "Join a church" /
  "Create a church"; default `join`; `?tab=join|create`; tab change → `router.replace("/welcome?tab=…", { scroll: false })`.
- Join tab: alert "You opened an invite link. Review and accept it below."; label "Invite link or code"; helper
  "Paste the link or code from your invite."; button "Continue"; blank → "Enter an invite code, or open your invite link again." (client, same text).
- Create tab: intro "Start a new church. You'll be its owner and can invite others."; "Church name" (placeholder
  "e.g. First Presbyterian Church", max 200); "Time zone" helper "Sets the default service date (the next Sunday in this time zone).";
  caption "Your church gets its own copy of the starter hymnal."; button "Create church"; pending "Creating church…";
  after 8 s "Still working — this can take up to a minute."; client checks "Church name is required." / "Timezone is required."
  (no request sent, first invalid field focused); success toast "Created {name}. You're the owner." → church selected → `/`.
- `TimezoneCombobox {value, onChange, error}`: items = `Intl.supportedValuesOf("timeZone")`, label = id with `_` → space,
  value = id; at most **50** matches with the hint "Type to search"; default = browser zone when listed, else `America/New_York`;
  `Intl.supportedValuesOf` missing → plain text input, same helper.
- `/join`: metadata title "Join a church", `robots: { index: false, follow: false }`. Signed out: "You're invited" /
  "Sign in with Google to see and accept your invite to Worship Service Builder." / button "Sign in with Google" → `/login?next=/join`.
  Preview: title `{church_name}`; "You're invited to join as a member." / "You're invited to join as an admin."; email-bound
  "This invite is for {your email}."; "Invite expires {Month D, YYYY}." (browser zone); `already_member`: only
  "You're already a member of {church_name}."; buttons "Join {church_name}" / "Open {church_name}" and "Not now" (clears code → `/`);
  footer "Signed in as {email} · Use a different account"; pending "Joining…". Rejected: server message + "Ask for a new invite link."
  + "Go to home" (code cleared); `email_mismatch`: + "You're signed in as {email}." + "Use a different Google account" (code kept →
  `/login?next=/join&select_account=1`). No code: "This invite link is incomplete." / "Open the link from your invite again, or ask for a new one." + "Go to home".
  Risk 8 fallback line (only if the chooser does not appear): "Sign out of Google in this browser, then try again.".
- Toasts: network/timeout use `e.message` ("Can't reach the server. Check your connection and try again." /
  "This is taking too long. Try again."); 5xx "Something went wrong. (Ref: {first 8 of requestId})"; accept toast = server `message`.
  Inline `ErrorState` "Can't reach the server." + Retry (preview). Switcher item "Join or create a church…".

**Constants**
- Session keys `wsb:pendingInviteCode`, `wsb:postLoginPath` (JSON `{path, at}`, the shape 1a's `use-sign-out.test.tsx:30` seeds);
  local `activeChurchId`. Post-login expiry **10 minutes**. `safeInternalPath`: ≤ 512 chars, one leading `/`, no `//`, `\`,
  control chars, whitespace, `?`, `#`, `..`; first segment in `{join, builder, services, settings, welcome}` with a boundary.
- Timeouts: default 20 000 ms; `POST /churches` 30 000 ms. Mutations `retry: false`. Key tracker: reuse only after
  `network_error`/`timeout`/`aborted`/5xx with an identical body or while in flight; new key after any 2xx/4xx or body change.
- Mobile: onboarding `max-w-md`, 16 px gutters, primary actions full width `size="touch"` (`h-11`); inputs `text-base md:text-sm`;
  inputs, combobox input and tabs sized `h-11` at the call site (generated `Input`/`InputGroup`/`TabsList` are `h-8`).

## Owner decisions

**Binding decisions (from the outline):**

1. **Preview card, then a Join tap** (behavior change 4 approved). The `autoAccept` fallback is not built. T19 records the
   approval in F: D14 row (:42), the amendments-table §4.3 row (:63) and §4.3 body (:732-734, replaced by a dated amendment to
   decision 6), and closes S's open items (Risk 1, Flow B note, BC4 row, manual 2 and AC10 parentheticals, the `/join`
   fallback-test sentence). Applied in T14, T15, T19.
2. **Standing permission:** safety/reliability fixes with no owner-visible change may deviate from S/P1a; each is recorded
   as a numbered clarification "(owner decision 2; deviation from S …)". Applied: clarifications 4, 19–23, 37, 42, 45 below.
3. **Production Streamlit is https://liturgy-frozen.streamlit.app/** (branch `streamlit-frozen`, `7978a5e`); merges to main
   never reach it; `liturgy-next` is deleted. So F§6.1.6's contingency does not apply: `accept_invite` is removed (T5) and
   manual checks use liturgy-frozen (T19, T21).
4. **Railway Pre-deploy Command (`alembic upgrade head`) and Healthcheck Path (`/health/ready`) live in the Railway UI**
   (Config as Code closed); `backend/railway.toml` only records them. 1b changes neither; S's config-path text is history.
5. **`main` is branch-protected** (`backend`, `backend-postgres`, `frontend`, up to date required): T20/T21 gates.

**Owner answers (2026-09-28, binding for the plan).** The owner accepted every recommendation ("go with all seven"):

1. F§4.3 amendment dated **2026-09-26**: "Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6)" in D14, the §4.3 row and §4.3 body; delete the auto-accept fallback text there and in S.
2. Manual-check invites are created in **liturgy-frozen** (Settings → Invites) only; no create_invite script.
3. All six extra F doc fixes in this PR (docs only): §7.4 `already_member`; §1.6 idempotency key has no church (5a/6b/5b add it; 1a T4-m1); §3.3 Railway settings in the UI; §6.1 liturgy-frozen; F:415 and F:1266 accept result/race handling; §4.3 step 2 signed-out wording.
4. **Yes** to both visible 1a leftovers in T11: full-page Retry shows pending and ignores repeat taps (T22-m2); one shared, screen-reader-announced loading skeleton for both layouts (T23-m3).
5. **Yes** to the early DRAFT PR after T8: the agent pushes and opens it without asking again; marking it ready still needs the owner's yes.
6. **Yes**: drop 1a's "weekday, tester not using the app" merge rule for 1b (no DB change; liturgy-frozen never sees merges); merge on the owner's yes at any time.
7. **Yes**: a new "Slice 1b record" section in docs/ops-runbook.md after the slice 1a stamping record, filled by a docs-only claude/slice-1b-records PR; the manual checklist's preamble points to it.
8. **Yes** to the new copy "No matching time zone." for the TimezoneCombobox's empty filter (T12), approved 2026-09-28.

## Spec clarifications

1. Line refs at `0295b37`: `churches.create_church` :12-29, `get_church` :32-42, `hymns.seed_church_from_catalog` :171-197,
   `ui_helpers.pick_invite_code` :56-60, `capture_query_params` :16; `invites.py` and `memberships.get_role` refs exact.
2. `get_church` returns `dict | None` (`{"id","name","timezone","settings"}`); the usecase uses `church["id"]`, `church["name"]` (NB C2).
3. Bulk seed: `if rows:` guard (an empty `execute(insert(Hymn), [])` inserts a default row → IntegrityError), return
   `len(rows)` (ORM bulk result has no `rowcount`), import `insert`, keep `session` **positional** (`migrate_to_db.py:152`,
   `churches.py:27`, `test_hymns_repo.py:93,112`) (NB C3).
4. `claim` uses `update(Invite).…execution_options(synchronize_session=False)` and the usecase still `s.refresh(inv)`: the
   default sync writes the caller's `accepted_by` into the in-memory row even at rowcount 0 (verified). Owner decision 2.
5. `hymns_seeded` needs a source: new `repos.churches.create_church_seeded(...) -> tuple[uuid.UUID, int]`; `create_church`
   wraps it and keeps returning the id (Streamlit, `migrate_to_db.py`, ~40 test call sites) (NB C5).
6. Usecase `create_church` gains `now: datetime | None = None` (S text says injectable; its signature omits it) (NB C6).
7. Python forms: `InvalidInput("Church name is required.", field="name")`; `Rejected(msg, code="invite_rejected",
   details={"reason": reason.value})` (`Rejected` has no default code) (NB C7).
8. `fields` only on 422 (T3-m1): tests never expect `fields` on a 400 (NB C8).
9. Same-commit couplings: route module + mount + `USER_SCOPED` + `test_api_app` expected + OpenAPI/`schema.d.ts` (NB C10).
   Every route lists 422 in `error_responses`, and `test_routes_document_the_error_body` subtracts the success status
   (`{"200","201"}`), since `/churches` returns 201 (NB C11).
10. Dependency order on `POST /churches`: `get_current_user` before `idempotency_key()` (no token + bad key → 401) (NB C12).
11. `test_slice1_docs.py::test_manual_verification_has_the_slice_1_section` changes with T19: `count("- [ ] ")` 3 → 13, new
    needles; "## Slice 1" stays the last `## ` heading (NB C13).
12. S "GET /church stays the only church-scoped route" is stale: `CHURCH_SCOPED_TODAY` = `GET /church`, `GET /rubric`,
    `PATCH /rubric` (NB C14). S's `railway.toml` text is superseded by owner decision 4 (NB C15).
13. Postgres tests cannot use `tmp_db`/`make_user`/`make_church`/`seed_catalog`; use `pg_db` + `make_api_client()` as
    `test_identity.py:360-376`, seeding through `session_scope` on the pg engine (NB C16).
14. Legacy consumed email-bound invites (`accepted_by` NULL) → `used` even for a current member (parity; NB C20).
    `repos/users.py:38` keeps its own `_as_utc`. S supersedes F:415 (accept return shape) and F:1266 (IntegrityError =
    success) with typed dataclasses + `insert_ignore` (NB C21/C22); T19 edits both lines and adds amendment rows (Q3).
15. Ported `test_email_bound_invite_matches_email_and_is_single_use`: its last assertion (same user re-accepts → "used")
    becomes `already_member: true` (behavior change 6); "removed member → used" covers the old intent.
16. The 1a hand-off name for the store is `api.idempotency.store`; the conftest fixture calls `reset_idempotency_for_tests()`.
17. `useSignOut` gains `SignOutOptions.selectAccount?: boolean` → `/login?next=%2Fjoin&select_account=1`; the code encodes
    `next` (1a asserts `/login?next=%2Fwelcome`), so tests compare parsed URLs, not S's literal `/login?next=/join` (NF C1).
18. The email-mismatch button **and** the footer link go through `useSignOut({ keepPendingInvite: true, next: "/join", selectAccount: true })`,
    never a raw `supabase.auth.signOut`, so 3e27edb's cookie expiry applies. Labels stay as S: footer "Use a different account",
    card button "Use a different Google account" (NF C12).
19. `/join` handles 401 itself: it subscribes to `authEvents.onSignOutRequired` → `signOut({ keepPendingInvite: true, next: "/join" })`
    (the only subscriber today is the `(signed-in)` layout, which `/join` sits outside) (NF C2; owner decision 2).
20. `/join` decides signed-in via `getAccessToken()`: token → signed in; `ApiError` 401 → sign-in card; `network_error`
    (be61d10) → inline `ErrorState` + Retry, never the sign-in card (NF C4; owner decision 2).
21. 1a clarification 27 remedy chosen here (1b adds the first pushed navigations: switcher item, "← Back to …" link):
    `lib/auth.ts` exports `endSignOut()`; `/login` calls it on mount (sign-out is complete by then). Back into a cached
    signed-in page then refetches `/me` and signs out cleanly instead of showing the skeleton forever (NF C3; owner decision 2).
    This supersedes P1a clarification 27's "slice 2" hand-off. T10 rewrites the `lib/auth.ts:4-9` header ("cleared only by a
    full page load" → "cleared by `endSignOut()` when `/login` mounts, or by a full page load") and the `(signed-in)/layout.tsx:14-17`
    comment if it repeats that wording.
22. Post-login follow: **clear before following** (S says peek, clear only on arrival). An allow-listed path with no route
    yet (`/builder`, `/services`, `/settings`) would otherwise re-redirect every visit to `/` for 10 min. A ref keeps the
    skeleton so StrictMode's second effect does not render children (NF C7; owner decision 2).
23. `useMembershipChanged` (uses `fetchQuery({ ...meQueryOptions(api), staleTime: 0 })`, clarification 38): if it fails, `queryClient.resetQueries({ queryKey: keys.me() })` and still
    `router.replace("/")`; the stored new id is kept, the `(signed-in)` layout shows skeleton/ErrorState until `/me` returns,
    so the `(church)` layout never overwrites the new id with a fallback (NF R2; owner decision 2).
24. Toast text: new `errorToastMessage(e)` in `lib/api/errors.ts` = `e.message` for `network_error`/`timeout`/`aborted`,
    else `describeError(e)` (which gives the short "Can't reach the server." used by `ErrorState`) (NF C8).
25. "Still working — this can take up to a minute." is kept verbatim (F§1.8's shared line) although `POST /churches`
    times out at 30 s; the timeout retry reuses the key, so it is safe (NF C9).
26. No global mutation-error toast exists, so no `meta.handledLocally` flag; components choose inline vs toast (NF §2).
27. Risk 9 closed: native `replaceState` is supported (docs cited above). Consequence: `useSearchParams().get("code")`
    becomes null after capture, so `/join` captures once (effect → sessionStorage → state) and never re-derives "no code" (NF §3.1).
28. `/welcome` needs `<Suspense>` around its `?tab=` reader; `/join/page.tsx` is a Server Component rendering `join-client.tsx`
    in `<Suspense>`. `/welcome` stays metadata-less (client page, as P1a).
29. Auto-preview runs once per code (ref guard; StrictMode double effects) and is never auto-retried (NF R3).
30. `/welcome` reads the pending code in a `useState` initializer (hydration-safe; NF R4); its back link resolves the active
    church with `pickActiveChurch(me.churches, useStoredChurchId())` and renders only once the store is read (≠ `undefined`).
31. The switcher item uses `useRouter().push("/welcome")` inside `ChurchSwitcher` (no prop plumbing; `(church)` layout
    unchanged except the shared `ShellSkeleton` if Q4 is yes); the back link is a Next `Link href="/"`. Both are pushes; clarification 21 makes Back safe.
32. `CORS` does not expose `Idempotent-Replayed`; the client does not need it (F:307). A replayed body keeps the first
    `request_id` (accepted).
33. No invite CLI exists (`backend/scripts/` has only `export_openapi.py`, `schema_drift.py`): manual checks create invites in
    liturgy-frozen Settings → Invites (single-use in the new app, `reusable = false`) (Q2).
34. No migration in 1b: no stamping, runbook, drift, backup gate or Railway/Supabase change; the merge deploy's pre-deploy
    `alembic upgrade head` prints no `Running upgrade` line.
35. `pick_invite_code` parity is by design different (behavior change 16): the field is prefilled with the pending code and
    exactly its content is used. The three Streamlit asserts are ported as JoinInvite tests (T14): edited field wins;
    pending code used when untouched; blank or whitespace-only → client message, no request.
36. Known limit kept (T18-m1): the 30 s timer does not cover a hung token refresh; `PendingButton` can stay pending.
37. **Engine `hide_parameters=True`** for both dialects in `db/engine.py:_engine_kwargs` (T1). Without it an unhandled DB error
    on `find_by_code` (pooler drop, timeout, SSL) puts the bound invite code in the `logger.exception` traceback
    (`api/errors.py:184`) and so in Railway's logs (AC9, F§2.5). `test_engine.py` checks kwargs one by one, so nothing else
    breaks (owner decision 2; no visible change).
38. **`meQueryOptions(api: Api)`** exported from `lib/queries/me.ts` = `{ queryKey: keys.me(), queryFn: ({ signal }) => api.user<Me>("/me", { signal }) }`;
    `useMe` spreads it, `useMembershipChanged` calls `fetchQuery({ ...meQueryOptions(api), staleTime: 0 })`. `makeQueryClient` has
    no default `queryFn`, so a bare `fetchQuery({ queryKey })` works only while a `useMe` observer happens to be mounted;
    `staleTime: 0` makes a fresh cached `/me` (< 30 s) refetch so the new church is in it before `replace("/")` (T13).
39. **`/login` never clears the stored post-login path.** It stores a valid `next` and otherwise leaves the stored value
    alone: `/auth/callback` failures and a Google cancel return to `/login?error=auth` with no `next` (`callback/route.ts:12`),
    and clearing there would lose `/join` after a failed or cancelled sign-in (AC14). Clarification 22's clear-before-follow
    already removes the 10-minute trap (NF C7's "companion" is dropped).
40. **Usecase calls repos through module attributes** (`from repos import churches, invites, memberships` → `invites.claim(...)`,
    `memberships.ensure_membership(...)`), so T5's claim-lost tests and T8's barrier wrappers can monkeypatch them
    (pattern `test_identity.py:219-233`: wrapper does `barrier.wait(timeout=10)` then delegates).
41. **Seed timing is a `UserWarning`**: `warnings.warn(f"hymn seed: {n} rows in {ms} ms", UserWarning)` in the T8 timing
    test (pytest's warnings summary prints it under `-q`); T8/T20 read it from the `backend-postgres` log. `ci.yml` unchanged.
42. **Retry-After counts from the (count − 4)-th oldest** counted church, not the oldest (owner decision 2; deviation from S
    Rate limits "until the oldest"): with 6+ counted (frozen Streamlit has no cap; two concurrent creates can pass at 4), the
    oldest ageing out still leaves ≥ 5. `recent_owned_creations` returns the ascending aware-UTC `created_at` list;
    `n = max(1, ceil((times[count − 5] + 24 h − now).total_seconds()))`. The UI never shows `n` (the 429 alert is the message).
43. **Known limit: `UTC` and `Etc/*` are not selectable.** ICU's 418 ids (`intl-zones.txt`) have neither; `Asia/Calcutta`
    and `Europe/Kiev` are its canonical names and the server accepts both. Adding `"UTC"` is owner-visible; left for 6a.
44. **`create_invite` gains `session: Session | None = None`** (S Repo changes 1b heading; `repos/users.py:45-80` pattern).
45. **`/join` metadata adds `referrer: "no-referrer"`** (Next `generate-metadata.md:365`), so the code-bearing URL is never
    sent as a Referer before the mount effect runs `replaceState` (NF R7; owner decision 2; no visible change).
46. **`settleOutcome(e: unknown): "client_error" | "uncertain"`** in `lib/idempotency.ts`: `ApiError` with status 400–499 →
    `client_error`; status 0 (`network_error`/`timeout`/`aborted`), ≥ 500 or a non-`ApiError` → `uncertain`. The create form
    uses it; 5b reuses it.
47. **`/join` gates `useMe({ enabled: signedIn === true })`**: an enabled-from-mount `/me` would 401 for a signed-out visitor,
    and clarification 19's subscriber would then redirect to `/login?next=%2Fjoin`, skipping the "You're invited" card. A
    `/me` 5xx on `/join` shows `ErrorState` + Retry.
48. **Port-then-delete for `streamlit_tests/test_onboarding.py`** (F§2.3.7): T3 removes `test_create_church_makes_owner_and_seeds_hymnal`
    (ported there), T5 removes `test_accept_captured_invite_joins_as_member` (the only `accept_invite` importer, `:32`),
    T14 deletes the file after porting the three `pick_invite_code` asserts.
49. **T23-m2 deferred**: with Q4 yes, 1b changes only the skeleton import in `(church)/layout.tsx`, not its ref-based query
    removal; the StrictMode test goes with the next edit of that logic (slice 2).

**Clarifications added while writing the tasks (code wins over the outline; each is stated in full in its task):**

50. **Bulk seed through the Core table** (Task 2; extends clarification 3): `insert(Hymn.__table__)`, not `insert(Hymn)`. The ORM bulk path leaves out `None` values and sends one INSERT per null pattern. The test caught 2 INSERTs for 2 rows. The Core form is one `executemany`, which psycopg2 batches (helps Risk 3). No visible change (owner decision 2).
51. **`_create_church` flushes the owner membership before the seed** (Task 2): sessions are `autoflush=False`, and the old per-row seed's `flush()` did this as a side effect. `recent_owned_creations` passes `since` through `as_utc`, because SQLite compares naive UTC text.
52. **Usecase helpers the outline did not name** (Tasks 3–5):
    - `BLANK_CODE_MESSAGE`, `_strip_code(code)` (check 0) and `_load_invite(s, code, user_id) -> (inv, church, member_role)` are defined in Task 4 and reused by Task 5.
    - The role-clamp WARNING text is `invite_role_clamped invite_id=<id> granted=<role>`.
    - `InviteRejectReason` values equal their names.
    - Both the church name and the time zone are stripped before the checks.
53. **`soft_delete_church` revokes pending invites** (`repos/churches.py:64-72`). So the `church_unavailable` tests set `churches.deleted_at` directly, and "revoked beats church_unavailable" uses `soft_delete_church` itself (Task 4).
54. **The DB-error log test runs a real failing statement** (Task 7). A hand-built `OperationalError(…, {"code": code}, …)` defaults to `hide_parameters=False` and always prints `[parameters: …]`. So the patched `find_by_code` runs `SELECT id FROM invites_gone WHERE code = :code` through `get_engine()`, and the test asserts `[SQL parameters hidden due to hide_parameters=True]`.
55. **`test_no_streamlit_in_core.py` anchors:** the router assert is at `:54`, not `:48`. Tasks 6 and 7 each append one line after it. The usecases import string is at `:20`: Task 1 edits `:19-20`, and Task 3 replaces the whole function.
56. **`(signed-in)` layout** (Task 11):
    - The stored path is read once, in a `useState` initializer at mount. `eslint`'s `react-hooks/set-state-in-effect` rejects the effect-only version.
    - The effect still clears, then redirects (clarification 22).
    - The busy Retry keeps the error it was pressed on, because TanStack 5.104 resets a data-less errored query to `pending` on refetch.
    - `church-layout.test.tsx` gains one assertion. `lib/post-login.ts`'s header gets one line corrected.
57. **`TimezoneCombobox`** (Task 12):
    - It owns the whole field: the label "Time zone", the helper and the error (`aria-invalid`, `aria-describedby`, no `role="alert"`). `id` is the `<input>`'s id in both modes.
    - Only the `"input-change"` reason updates the query, because Base UI has no `"input-paste"`.
    - Testing Library computes an empty name for the open combobox, so tests take the input while the list is closed.
    - New copy "No matching time zone." for an empty filter. Approved by the owner on 2026-09-28 (owner answer 8).
58. **`JoinInvite`** (Task 14):
    - The auto-preview runs once per mount.
    - Any 4xx other than 401 is a rejection. A 401 or `aborted` changes nothing, because the page's subscriber signs out.
    - Both account-switch controls write the code in use to `wsb:pendingInviteCode` before `signOut(…selectAccount…)`.
    - "Go to home" and "Not now" use `router.replace("/")`.
    - The StrictMode test uses RTL's `reactStrictMode: true`, since a nested `<StrictMode>` does not double effects in React 19.2.8.
59. **`/join`** (Task 15): "Sign in with Google" is `<Button render={<Link href="/login?next=%2Fjoin" />} nativeButton={false}>`, which is role button on an `<a>`. This is the first `next/link` in `src/`, because a plain `<a href="/">` fails `@next/next/no-html-link-for-pages`. `/join` adds no footer of its own: the footer is inside `JoinInvite`.
60. **`CreateChurchForm`** (Task 16):
    - The body is sent trimmed, and the key fingerprint uses the trimmed body.
    - After a 201 the button stays pending until `useMembershipChanged` navigates.
    - The success toast comes before `useMembershipChanged`, in S's order.
    - A 422 with no `fields.name` or `fields.timezone` (e.g. `idempotency_mismatch`) is a toast.
    - `defaultTimezone(null)` is `America/New_York` (Task 9).
61. **Manual checks** (Tasks 19, 21):
    - A creates "1b Invite Test" in the new app, not in liturgy-frozen. Frozen Streamlit offers Create only to an account with no church (`app.py:344-347` on `streamlit-frozen`).
    - B and C both start with no church.
    - The run order is 2, 3, 5, 6, 4, 7, 8, 9, 10, 11, so check 4 runs after C has churches.
    - Only the §4.3 approval is dated 2026-09-26. The Q3 amendment rows are dated 2026-09-28.
62. **Grep gates** (Tasks 3, 5, 14, 20) use `grep -I` (and `--include='*.py'` for AC16), so stale `__pycache__/*.pyc` files never match.
63. **Counts include owner answer 4 (Q4 = yes):** frontend 221 passed in 34 files, where the outline says 220. Task 5 has two commits and Task 19 has two TDD cycles, each with its own commit.

## File Structure

Backend
- A `backend/timezones.py` — `is_valid_timezone(name)` over a cached `zoneinfo.available_timezones()` set (T1)
- A `backend/tests/test_timezones.py` — valid/invalid names (T1)
- M `backend/db/engine.py` — `hide_parameters=True` in `_engine_kwargs` (T1; clarification 37)
- M `backend/tests/test_engine.py` — `test_engine_hides_bound_parameters` (T1)
- M `backend/tests/conftest.py` — autouse `_fresh_idempotency_store` calling `reset_idempotency_for_tests()` (T1)
- M `backend/tests/api_helpers.py` — messages on the `:105`, `:113` asserts (T13-m1) (T1)
- M `backend/tests/test_no_streamlit_in_core.py` — `:19-20` import list gains `timezones` (T1) and `usecases.onboarding` (T3, whole function replaced); after `:54` one assert each for `'api.routes.churches'` (T6) and `'api.routes.invites'` (T7)
- M `backend/repos/churches.py` — `session` params, `as_uuid`, `create_church_seeded`, `recent_owned_creations` (T2)
- M `backend/repos/hymns.py` — bulk `seed_church_from_catalog` (T2)
- M `backend/repos/invites.py` — `reusable` + `session` kwargs, `_to_dict` keys, `as_utc`, `find_by_code`, `claim` (T2); `accept_invite` removed (T5)
- M `backend/repos/memberships.py` — `get_role(..., session=)`, `ensure_membership` (T2)
- M `backend/tests/test_churches_repo.py`, `test_hymns_repo.py`, `test_memberships_repo.py` — new repo tests (T2)
- M `backend/tests/test_invites_repo.py` — new repo tests (T2); 4 accept tests deleted, `:76`/`:89` accept halves removed, import line fixed (T5)
- A `backend/usecases/onboarding.py` — dataclasses, `create_church` + cap (T3); `preview_invite`, `_evaluate`, `_clamp_role`, `REJECT_MESSAGES` (T4); `accept_invite` (T5)
- A `backend/tests/test_usecase_onboarding.py` — create/cap tests (T3); preview/rejection tests (T4); accept tests (T5)
- M then D `streamlit_tests/test_onboarding.py` — create test removed (T3), accept test removed (T5), file deleted after the
  three `pick_invite_code` ports (T14) (clarification 48)
- M `backend/api/schemas.py` — `CreateChurchIn` (T6), `InviteCodeIn`, `InvitePreviewOut`, `InviteAcceptOut` (T7); docstring "Request and response models"
- A `backend/api/routes/churches.py` — `POST /churches` (T6)
- A `backend/api/routes/invites.py` — `POST /invites/preview`, `POST /invites/accept` (T7)
- M `backend/api/main.py` — mount `churches` (T6), `invites` (T7)
- M `backend/tests/test_route_guards.py` — `USER_SCOPED` + routes (T6, T7)
- M `backend/tests/test_api_app.py` — error-doc expectations, success-status subtraction (T6, T7)
- A `backend/tests/test_api_churches.py` (T6); A `backend/tests/test_api_invites.py` (T7)
- A `backend/tests/test_onboarding_postgres.py` — `@pytest.mark.postgres` race and timing tests (T8)
- M `backend/tests/test_slice1_docs.py` — manual-section counts/needles; F§4.3 amendment test (T19)

Frontend (`frontend/src/`)
- M `lib/api/openapi.json`, `lib/api/schema.d.ts` — regenerated (T6, T7)
- A `lib/idempotency.ts` + `lib/idempotency.test.ts` — `createKeyTracker`, `stableStringify`, `settleOutcome` (T9)
- A `lib/post-login.ts` + `lib/post-login.test.ts` — `storePostLoginPath`, `peekPostLoginPath`, `clearPostLoginPath` (T9)
- A `lib/timezones.ts` + `lib/timezones.test.ts` — `listTimezones`, `browserTimezone`, `defaultTimezone`, `timezoneLabel` (T9)
- M `lib/api/errors.ts` + `lib/api/errors.test.ts` — `errorToastMessage` (T9)
- M `lib/supabase/proxy.ts`; A `lib/supabase/proxy.test.ts` (node, `vi.mock("@supabase/ssr")`) (T10)
- M `app/login/page.tsx`; A `app/login/login.test.tsx` (T10)
- M `lib/auth.ts` (`selectAccount`, `endSignOut`, header comment per clarification 21); M `lib/use-sign-out.test.tsx` (T10)
- M `test/mocks.ts` — `supabaseAuth.signInWithOAuth` + default (T10)
- M `app/(signed-in)/layout.tsx`; M `app/(signed-in)/signed-in-layout.test.tsx` (T11)
- A `components/app/shell-skeleton.tsx`; M `app/(signed-in)/(church)/layout.tsx` (shared skeleton, if Q4 yes) (T11)
- M `components/app/error-state.tsx` + `error-state.test.tsx` — `retrying?` prop (if Q4 yes) (T11)
- A `components/app/timezone-combobox.tsx` + `timezone-combobox.test.tsx` (T12)
- M `lib/api/types.ts` — `InvitePreview`, `InviteAccepted`, `CreateChurchBody` (T13)
- A `lib/queries/onboarding.ts` + `onboarding.test.tsx`; A `lib/queries/membership.ts` + `membership.test.tsx` (T13)
- M `lib/queries/me.ts` — export `meQueryOptions(api)`; `useMe` spreads it (T13; clarification 38)
- M `test/fixtures/index.ts` — `invitePreview()`, `inviteAccepted()` builders (T13)
- A `components/onboarding/join-invite.tsx` + `join-invite.test.tsx` (T14)
- A `app/join/page.tsx` (metadata incl. `referrer: "no-referrer"`), `app/join/join-client.tsx`, `app/join/join.test.tsx` (T15)
- A `components/onboarding/create-church-form.tsx` + `create-church-form.test.tsx` (T16)
- M `app/(signed-in)/welcome/page.tsx`; M `app/(signed-in)/welcome/welcome.test.tsx` (stub test replaced) (T17)
- M `components/app/church-switcher.tsx`; M `components/app/app-header.test.tsx` (T18)

Docs
- A `docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md` (T1, first commit)
- M `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` — D14, §4.3 row + body, §7.4, §1.6, §3.3, §6.1 (T19; last four per Q3)
- M `docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md` — close open items (T19)
- M `docs/manual-verification.md` — "## Slice 1" preamble + items 2–11 (T19)
- M `docs/ops-runbook.md` — `### Slice 1b record` (records PR, T21)

Also touched (named in the tasks' **Files:**, not in the outline's list):
- M `frontend/src/lib/post-login.ts` — header line (T11, after T9 creates it)
- M `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx` — one skeleton assertion in the zero-church test (T11)
- M `streamlit_tests/test_onboarding.py` then D (T3, T5, T14; listed above); `docs/ops-runbook.md` changes only in the records PR (T21)
- The whole branch diff is 76 paths (32 A, 1 D, 43 M); T20 checks it against an exact list.

---
### Task 1: Preflight, `timezones.py`, the engine hides bound parameters, test-harness hand-offs (S Modules added 1b; P1a :1888; 1a minor T13-m1; clarification 37)

This task commits the plan, checks the baseline, and adds the three pieces later tasks build on: the IANA name check (`timezones.is_valid_timezone`, used by Task 3), `hide_parameters=True` on the engine (so an unhandled DB error in Task 7's invite routes never writes a bound invite code or email to the logs), and the autouse reset of the process-wide idempotency store that the 1a plan handed to 1b (Task 6's `POST /churches` is the store's first real route). It also gives the two bare asserts in `tests/api_helpers.py` messages (1a minor T13-m1): pytest does not rewrite asserts in that module, so today a failure there prints an empty `AssertionError`. Nothing here needs Postgres, and the frontend does not change.

**Files:**
- Commit (Step 0): `docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md` (this plan; the branch's first commit)
- Create: `backend/timezones.py`
- Modify: `backend/db/engine.py:68` (`_engine_kwargs`: the `kwargs = {...}` line)
- Modify: `backend/tests/conftest.py` (insert after line 169, the end of `_fresh_readiness_memo`: autouse `_fresh_idempotency_store`)
- Modify: `backend/tests/api_helpers.py:105` and `:113` (assert messages)
- Test: `backend/tests/test_timezones.py` (new, 7 tests)
- Test: `backend/tests/test_engine.py` (append after line 155: 1 test)
- Test: `backend/tests/test_no_streamlit_in_core.py:19-20` (the import list gains `timezones`; no count change)

**Interfaces:**
- Consumes:
  - `api.idempotency.reset_idempotency_for_tests() -> None` (`backend/api/idempotency.py:144`; clears the process-wide `api.idempotency.store`, `:141`).
  - `db.engine._engine_kwargs(url: str) -> dict` (`backend/db/engine.py:66-80`) and `db.engine._make_engine(url: str) -> Engine` (`:83-85`).
  - `tests.api_helpers.assert_church_isolated(client, method, path, *, world, json=None, resource_path_b=None)` (`:80-118`) and `IsolationWorld(church_a, church_b, a="a@example.com", b="b@example.com", outsider="o@example.com")` (`:54-62`).
  - `test_engine.py`'s `PG_URL = "postgresql://u:p@h/db"` (`:83`) and fixture `pool_env` (`:86-91`).
- Produces:
  - `timezones._zones() -> frozenset[str]`, decorated `@lru_cache(maxsize=1)`: `frozenset(zoneinfo.available_timezones())`, read once per process.
  - `timezones.is_valid_timezone(name: str) -> bool`: `name in _zones()` (exact, case-sensitive; not a `ZoneInfo(name)` lookup). Later users: Task 3 (`usecases.onboarding.create_church`), slice 2 (`GET /church` `timezone_valid`), 6a (`PATCH /church`).
  - `db.engine._engine_kwargs(url)` now always includes `"hide_parameters": True` (SQLite and Postgres), so a `sqlalchemy.exc.DBAPIError`'s text carries `[SQL parameters hidden due to hide_parameters=True]` instead of the bound values. Later users: Task 7 (`test_db_error_logs_hold_no_code_or_email`), Task 20 (grep gate).
  - Autouse fixture `_fresh_idempotency_store` in `backend/tests/conftest.py`: calls `api.idempotency.reset_idempotency_for_tests()` before every test when `api.idempotency` is already in `sys.modules` (the deferred-import rule at the top of `conftest.py`). Later users: Task 6 (`test_api_churches.py`), 5a, 5b, 6b. `test_idempotency.py:47-52` keeps its own `_fresh_store` fixture unchanged (it also clears after each test).
  - `assert_church_isolated`'s two message-less asserts now read `f"{method} {path} as {email} in church B: {r.text}"` and `f"{method} {resource_path_b} as {world.a} in church A: {r.text}"`. Later users: every church-scoped route's isolation test (slice 2 on).

Counts after this task: backend **705 passed, 5 skipped** (697 + 8); frontend **126 passed in 23 files** (unchanged).

- [ ] **Step 0 (agent): Commit this plan (the branch's first commit)**

Skip this step if `git log --oneline origin/main..HEAD -- docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md` already prints a line (the controller may commit the plan before dispatching Task 1).

```bash
git status --short
git add docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md
git commit -m "Plan: slice 1b onboarding (F, S slice 1; owner answers 2026-09-28)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

**Expected:** before the commit, `git status --short` lists exactly `?? .claude/` and `?? docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md` (`.claude/` stays untracked and is never staged). Afterwards the last line is `<sha> Plan: slice 1b onboarding (F, S slice 1; owner answers 2026-09-28)`.

- [ ] **Step 1 (agent): Check the branch and the baseline**

```bash
git fetch origin
git status -sb | head -1
git log --oneline -1 origin/main
git log --oneline origin/main..HEAD
grep -n '^def reset_idempotency_for_tests() -> None:$' backend/api/idempotency.py
grep -n '^def _engine_kwargs(url: str) -> dict:$' backend/db/engine.py
grep -c hide_parameters backend/db/engine.py
test ! -e backend/timezones.py && test ! -e backend/usecases/onboarding.py && echo "no 1b modules yet"
ls backend/migrations/versions/*.py | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
```

**Expected,** in order:
- `## claude/slice-1b-plan...origin/main [ahead 1]` (only the plan commit on this branch);
- `0295b37 Merge pull request #17 from bbrown62450/claude/slice-1a-records`;
- exactly one line, the plan commit from Step 0;
- `144:def reset_idempotency_for_tests() -> None:`;
- `66:def _engine_kwargs(url: str) -> dict:`;
- `0`;
- `no 1b modules yet`;
- `backend/migrations/versions/0004_invites_reusable.py` (the head stays `0004_invites_reusable`; 1b adds no migration);
- `4` (`wc` pads it with spaces; 1b adds no owner marker);
- `697 passed, 5 skipped in <t>s`;
- ` Test Files  23 passed (23)` and `      Tests  126 passed (126)`.

If the branch line shows `behind`, run `git diff --name-only 0295b37 origin/main`. When every listed path is under `docs/`, merge it now: `git merge origin/main -m "Merge origin/main into claude/slice-1b-plan" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"` (the branch holds only the plan, so no conflict), then rerun this step and expect `[ahead 2]`, two lines from `git log --oneline origin/main..HEAD` and the same counts. If any other path is listed, a count differs (backend other than `697 passed, 5 skipped`, frontend other than 126 in 23 files) or a grep line differs, stop and ask the owner.

- [ ] **Step 2 (agent): Write the failing tests**

Create `backend/tests/test_timezones.py`:

```python
"""One IANA check everywhere (F §7.4 "Church timezone"; S Modules added 1b):
exact, case-sensitive membership in zoneinfo.available_timezones()."""
import pytest

from timezones import is_valid_timezone


@pytest.mark.parametrize("name", ["America/New_York", "UTC", "Europe/London"])
def test_valid_timezones(name):
    assert is_valid_timezone(name) is True


@pytest.mark.parametrize("name", ["america/new_york", "Mars/Olympus", "../etc/passwd", ""])
def test_invalid_timezones(name):
    assert is_valid_timezone(name) is False
```

In `backend/tests/test_engine.py`, append after line 155 (the end of `test_postgres_engine_uses_the_pool_size_without_connecting`; `pytest` and `text` are already imported at lines 1-2):

```python


# --- slice 1b: bound parameters stay out of error text (AC9, F §2.5; 1b clarification 37) ---

def test_engine_hides_bound_parameters(pool_env, tmp_path):
    """An unhandled DB error is logged with its traceback (api/errors.py), and
    SQLAlchemy's message lists the bound values by default: an invite code or
    an email would reach the logs. Both dialects hide them."""
    from sqlalchemy.exc import OperationalError

    from db.engine import _engine_kwargs, _make_engine

    assert _engine_kwargs(PG_URL)["hide_parameters"] is True
    assert _engine_kwargs("sqlite:///data/app.db")["hide_parameters"] is True

    engine = _make_engine(f"sqlite:///{tmp_path / 'h.db'}")
    try:
        with engine.connect() as conn, pytest.raises(OperationalError) as exc:
            conn.execute(text("SELECT id FROM invites WHERE code = :code"), {"code": "SECRET-CODE-123"})
    finally:
        engine.dispose()
    assert "no such table: invites" in str(exc.value)
    assert "[SQL parameters hidden due to hide_parameters=True]" in str(exc.value)
    assert "SECRET-CODE-123" not in str(exc.value)
```

(Checked on `0295b37`: with SQLAlchemy's default `hide_parameters=False` the message ends `[parameters: ('SECRET-CODE-123',)]`, so the last assert is not vacuous. The other `_engine_kwargs` tests, `test_engine.py:94-145`, check keys one by one, so the new key breaks none of them.)

In `backend/tests/test_no_streamlit_in_core.py`, replace lines 19-20:

```python
    # usecases, domain_errors and db.ids are below the API layer (F §2.2).
    code = ("import sys, usecases, domain_errors, db.ids; "
```

with:

```python
    # usecases, domain_errors, db.ids and timezones are below the API layer (F §2.2).
    code = ("import sys, usecases, domain_errors, db.ids, timezones; "
```

(Task 3 adds `usecases.onboarding` to the same import list.)

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_timezones.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_engine.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | grep -m1 ModuleNotFoundError
```

**Expected:**
- `ERROR backend/tests/test_timezones.py`, `Interrupted: 1 error during collection`, `1 error in <t>s` (the collection error is `ModuleNotFoundError: No module named 'timezones'`);
- `FAILED backend/tests/test_engine.py::test_engine_hides_bound_parameters - KeyError: 'hide_parameters'` (pytest may shorten the reason to `Key...`) and `1 failed, 19 passed in <t>s`;
- `FAILED backend/tests/test_no_streamlit_in_core.py::test_usecases_package_imports_no_fastapi_or_streamlit` and `1 failed, 2 passed in <t>s`;
- `E         ModuleNotFoundError: No module named 'timezones'` (the subprocess's stderr in the assert message).

- [ ] **Step 4 (agent): Create `backend/timezones.py`**

```python
"""IANA time zone names: one check everywhere (F §7.4 "Church timezone"; S Modules added 1b).

A name is valid when it is exactly, case-sensitively, one of
zoneinfo.available_timezones(). It is not a ZoneInfo(name) lookup: on a
case-insensitive disk (macOS) ZoneInfo("america/new_york") loads, and
ZoneInfo("posixrules") loads a file that is not a zone name. The set merges
the system zoneinfo directory with the tzdata package, so a laptop and Railway
may differ at the edges; every name the browser offers (ICU) is in both.

No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py). Users:
usecases.onboarding.create_church (1b), GET /church timezone_valid (slice 2),
PATCH /church (6a).
"""
import zoneinfo
from functools import lru_cache


@lru_cache(maxsize=1)
def _zones() -> frozenset[str]:
    """Every IANA name this process knows, read once."""
    return frozenset(zoneinfo.available_timezones())


def is_valid_timezone(name: str) -> bool:
    """True when `name` is exactly an IANA zone name (case-sensitive)."""
    return name in _zones()
```

(Checked on this laptop at `0295b37`: `zoneinfo.ZoneInfo("america/new_york")` and `ZoneInfo("posixrules")` both load, while neither name is in `available_timezones()`; that is why the check is set membership.)

- [ ] **Step 5 (agent): Hide bound parameters on the engine (`backend/db/engine.py`)**

Replace line 68:

```python
    kwargs = {"pool_pre_ping": True, "future": True}
```

with:

```python
    # hide_parameters: an unhandled DB error is logged with its traceback
    # (api/errors.py), and SQLAlchemy's message would list the bound values,
    # such as an invite code or an email (AC9, F §2.5; 1b clarification 37).
    kwargs = {"pool_pre_ping": True, "future": True, "hide_parameters": True}
```

Nothing else in the file changes. `migrations/env.py:77`, `scripts/schema_drift.py:38` and the test helpers build their own engines for schema work and never bind an invite code or email; they are unchanged.

- [ ] **Step 6 (agent): Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_timezones.py backend/tests/test_engine.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
```

**Expected:** `30 passed in <t>s` (7 + 20 + 3).

- [ ] **Step 7 (agent): Reset the idempotency store before every test (`backend/tests/conftest.py`)**

First confirm no such fixture runs yet:

```bash
.venv/bin/python -m pytest -q --setup-plan backend/tests/test_timezones.py 2>&1 | grep -c 'SETUP    F _fresh_idempotency_store'
```

**Expected:** `0`.

Insert after line 169 (the `yield` that ends `_fresh_readiness_memo`), so that the new fixture sits between `_fresh_readiness_memo` and the `# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---` comment, with two blank lines on each side:

```python


@pytest.fixture(autouse=True)
def _fresh_idempotency_store():
    """run_idempotent keeps responses in one process-wide store for 15 minutes
    (api.idempotency.store; POST /churches is its first real route, 1b). Each
    test starts with it empty, so nothing an earlier test stored, or left
    there when it failed, can replay, conflict or count toward MAX_ENTRIES
    here (the 1a plan's hand-off to 1b).

    Resets only when api.idempotency is already imported: a stored response
    can exist only then (the deferred-import rule at the top of this file)."""
    import sys

    idempotency = sys.modules.get("api.idempotency")
    if idempotency is not None:
        idempotency.reset_idempotency_for_tests()
    yield
```

The result around the insertion reads:

```python
    health = sys.modules.get("db.health")
    if health is not None:
        health.reset_readiness_for_tests()
    yield


@pytest.fixture(autouse=True)
def _fresh_idempotency_store():
    ...
    yield


# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---
```

Then:

```bash
.venv/bin/python -m pytest -q --setup-plan backend/tests/test_timezones.py 2>&1 | grep -c 'SETUP    F _fresh_idempotency_store'
.venv/bin/python -m pytest -q backend/tests/test_idempotency.py 2>&1 | tail -1
```

**Expected:** `7` (the fixture sets up for each of the 7 timezone tests), then `15 passed in <t>s` (`test_idempotency.py` keeps its own `_fresh_store`, lines 47-52, unchanged).

- [ ] **Step 8 (agent): Messages on the two bare asserts in `backend/tests/api_helpers.py` (1a minor T13-m1)**

pytest rewrites asserts only in test modules and conftest, so a failing bare assert in `api_helpers.py` prints an empty message. Show that first:

```bash
PYTHONPATH=backend .venv/bin/python - <<'EOF'
import uuid
from types import SimpleNamespace as NS
from tests.api_helpers import IsolationWorld, assert_church_isolated
body = {"error": {"code": "forbidden", "message": "Nope.", "details": {}, "request_id": "r"}}
client = NS(request=lambda *a, **k: NS(status_code=403, text="BODY", json=lambda: body))
try:
    assert_church_isolated(client, "GET", "/church", world=IsolationWorld(uuid.uuid4(), uuid.uuid4()))
except AssertionError as e:
    print(f"AssertionError: {e}|")
EOF
```

**Expected:** `AssertionError: |` (nothing between the colon and the bar).

Replace line 105:

```python
        assert _error_without_request_id(r) == NO_CHURCH_ACCESS
```

with:

```python
        assert _error_without_request_id(r) == NO_CHURCH_ACCESS, (
            f"{method} {path} as {email} in church B: {r.text}"
        )
```

and line 113:

```python
        assert r.json()["error"]["code"] == "not_found"
```

with:

```python
        assert r.json()["error"]["code"] == "not_found", (
            f"{method} {resource_path_b} as {world.a} in church A: {r.text}"
        )
```

Rerun the same heredoc command.

**Expected:** `AssertionError: GET /church as o@example.com in church B: BODY|`. The messages carry test emails and response bodies only (never an app log line), matching the status asserts on lines 104 and 110-112.

- [ ] **Step 9 (agent): Run the isolation tests and the whole suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_isolation.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `3 passed in <t>s`; then `705 passed, 5 skipped in <t>s` (697 + 8: `test_timezones.py` 7, `test_engine.py` 1); then exactly:

```
 M backend/db/engine.py
 M backend/tests/api_helpers.py
 M backend/tests/conftest.py
 M backend/tests/test_engine.py
 M backend/tests/test_no_streamlit_in_core.py
?? .claude/
?? backend/tests/test_timezones.py
?? backend/timezones.py
```

- [ ] **Step 10 (agent): Commit**

```bash
git add backend/timezones.py backend/tests/test_timezones.py backend/db/engine.py backend/tests/test_engine.py \
        backend/tests/conftest.py backend/tests/api_helpers.py backend/tests/test_no_streamlit_in_core.py
git commit -m "Backend: timezones.is_valid_timezone, engine hides bound parameters, idempotency store reset per test (S Modules added 1b; 1b clarification 37)

timezones.is_valid_timezone is exact, case-sensitive membership in
zoneinfo.available_timezones() (F §7.4), not a ZoneInfo lookup.
The engine sets hide_parameters=True for SQLite and Postgres, so an
unhandled DB error's logged traceback never carries a bound invite code
or email (AC9, F §2.5). An autouse fixture clears the process-wide
idempotency store before each test (1a plan hand-off), and the two bare
asserts in tests/api_helpers.py get messages (1a minor T13-m1).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

**Expected:** `<sha> Backend: timezones.is_valid_timezone, engine hides bound parameters, idempotency store reset per test (S Modules added 1b; 1b clarification 37)`; `git status --short` then lists only `?? .claude/`.
### Task 2: Repos: `session` parameters, the create-cap query, a bulk hymnal seed and the invite primitives (S Repo changes 1b; clarifications 1-5, 42, 44)

This task changes only `backend/repos/` and their tests. Tasks 3-5 build the onboarding usecases on these functions, and every changed or new function takes an optional `session`, so one usecase transaction can hold the cap check, the church and its seed, or the invite checks and the claim (F §2.2 item 3; the `repos/users.py:45-80` pattern: `if session is not None: return _impl(session, …)`, otherwise `with session_scope() as own:`). A passed `session` is never committed by the repo. Nothing here is reachable over HTTP yet, and Streamlit keeps working: every existing signature stays call-compatible (`session` is keyword-only everywhere except the seed, whose `session` stays positional, clarification 3).

Four details found while writing this task (all tested below):
- **The bulk seed is a Core insert on the table, `insert(Hymn.__table__)`, not `insert(Hymn)`.** The ORM form takes SQLAlchemy's "ORM bulk INSERT" path, which leaves `None` values out of each row and then issues one INSERT per run of rows with the same null pattern. The catalog's `audio_url`, `text_year` and `hymnal_count` are often `None`, so a 700-row seed would become many statements (verified here: two catalog rows with different nulls gave two INSERTs). The Core form sends every key in every row, so the whole list is one executemany, which psycopg2 batches with insertmanyvalues (`use_insertmanyvalues_wo_returning` is on for psycopg2 in SQLAlchemy 2.1). No `Hymn` object is built per row. This extends clarification 3 (owner decision 2; no visible change; it serves Risk 3's timing).
- **`claim` uses `synchronize_session=False`** (clarification 4). Verified here: with the default, `test_claim_zero_rows_leaves_loaded_row_untouched` fails with `assert (UUID('…') is None)`, because the loser's id is copied into the row the session loaded before the winner committed.
- **`_create_church` flushes the owner membership before the seed.** The session has `autoflush=False` (`db/engine.py:26`), and the old per-row `session.add` seed flushed the membership as a side effect; the Core insert does not.
- **`repos/churches.py` imports `as_utc` from `repos/invites.py`** for `recent_owned_creations` (aware UTC even from SQLite, whose `created_at` comes back naive). `repos.invites` imports no other repo, so there is no cycle. `recent_owned_creations` also runs `since` through `as_utc`, because SQLite compares the stored naive UTC text: a `since` in another offset would otherwise be off by that offset (the last assert of `test_recent_owned_creations_skips_old_and_admin_only`).

Unchanged on purpose: `get_church` and `get_role` gain only `session` (S; no `as_uuid`, so Streamlit's callers at `streamlit_views/settings.py:38,45,52` and `repos/churches.py:110,131,164` behave as before); `create_invite` takes `church_id`/`created_by` as before; `repos/users.py:38` keeps its own `_as_utc` (clarification 14). `accept_invite` stays until Task 5, and still uses `_as_utc`, which becomes an alias of `as_utc`.

**Files:**
- Modify: `backend/repos/churches.py:1-42` (imports, `create_church`, `get_church`; adds `create_church_seeded`, `_create_church`, `_get_church`, `recent_owned_creations`, `_recent_owned_creations`)
- Modify: `backend/repos/hymns.py:9` (import `insert`) and `:171-197` (`seed_church_from_catalog`)
- Modify: `backend/repos/invites.py:1-63` (imports through `get_invite_by_code`; adds `as_utc` with the `_as_utc` alias, `_to_dict` keys, `create_invite(reusable=, session=)`, `find_by_code`, `_find_by_code`, `claim`)
- Modify: `backend/repos/memberships.py:1-6` (imports) and `:29-32` (`get_role`; adds `_get_role`, `ensure_membership`, `_ensure_membership`)
- Test: `backend/tests/test_churches_repo.py` (header `:1-10`; 4 tests appended after `:63`)
- Test: `backend/tests/test_hymns_repo.py` (header `:1-2`; 2 tests appended after `:115`)
- Test: `backend/tests/test_invites_repo.py` (header `:1-11` gains `import pytest` and a second `from repos.invites import` line, so every later line moves down 2; 5 tests appended after `:104`)
- Test: `backend/tests/test_memberships_repo.py` (import `:9-12`; 1 test appended after `:79`)

**Interfaces:**
- Consumes:
  - `db.ids.as_uuid(value: object) -> uuid.UUID` (`backend/db/ids.py`; `NotFound("Not found.")` for `None`, malformed text or another type).
  - `db.upsert.insert_ignore(table, *, dialect_name: str | None = None)` (`backend/db/upsert.py`; returns the Postgres or SQLite `insert()`, which supports `.on_conflict_do_nothing(index_elements=…)`; the caller applies it).
  - `db.session_scope()` (`backend/db/engine.py:117`; commit on success, rollback on exception; `SessionLocal` is `autoflush=False, expire_on_commit=False`, `:26`).
  - Models `Church`, `Membership`, `Invite`, `Hymn`, `HymnCatalog` (`backend/db/models.py:51-140`; `Invite.reusable`/`accepted_by` from 0004).
  - Fixtures `tmp_db`, `make_user(email=…)`, `make_church(name, timezone, owner_user_id)`, `seed_catalog(n)` (`backend/tests/conftest.py`).
- Produces (`Optional[Session]` is `Session | None`; the files keep their `typing.Optional` style):
  - `repos.churches.create_church(*, name, timezone, owner_user_id, session: Optional[Session] = None) -> uuid.UUID` — unchanged result; `owner_user_id` through `as_uuid`. Later users: Streamlit `app.py:318`, `migrate_to_db.py:142`, ~40 test call sites, Task 6's `test_cap_429_not_replayed`, Task 8.
  - `repos.churches.create_church_seeded(*, name, timezone, owner_user_id, session: Optional[Session] = None) -> tuple[uuid.UUID, int]` — (church id, hymns seeded); `create_church` wraps it. Later user: Task 3 (`churches.create_church_seeded(..., session=s)`, clarification 5).
  - `repos.churches.get_church(church_id, *, session: Optional[Session] = None) -> Optional[dict]` — `{"id", "name", "timezone", "settings"}` or `None` (missing or soft-deleted). Later users: Tasks 4-5 (`church["id"]`, `church["name"]`, clarification 2).
  - `repos.churches.recent_owned_creations(user_id, *, since: datetime, session: Optional[Session] = None) -> list[datetime]` — `created_at` of churches where `user_id` holds `owner` and `created_at > since` (strict), soft-deleted included, ascending, each aware UTC (`tzinfo is timezone.utc`). Later user: Task 3's cap (`count = len(times)`, Retry-After from `times[count - 5]`, clarification 42).
  - `repos.hymns.seed_church_from_catalog(church_id, session: Session) -> int` — `session` positional as before; one `session.execute(insert(Hymn.__table__), rows)` with a `uuid.uuid4()` id per row, skipped when the catalog is empty; returns `len(rows)`; no commit, no flush. Later users: `_create_church`, `migrate_to_db.py:152`, Task 8's 700-row timing test.
  - `repos.invites.as_utc(value: datetime) -> datetime` — naive → UTC, aware → converted to UTC; `repos.invites._as_utc` is the same object. Later users: Task 4 (`InvitePreview.expires_at`, the expiry check), this task's `recent_owned_creations`.
  - `repos.invites._to_dict(inv)` — adds `"reusable"` and `"accepted_by"` to the nine existing keys.
  - `repos.invites.create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7, reusable: bool = False, session: Optional[Session] = None) -> str` — with `session`, adds and flushes the row in the caller's transaction. Later users: Tasks 4, 5, 7, 8 tests; slice 6b's route.
  - `repos.invites.find_by_code(code: str, *, session: Optional[Session] = None) -> Optional[Invite]` — the ORM row (detached, columns loaded, when no `session`). Later users: Tasks 4-5 (`invites.find_by_code(code, session=s)`).
  - `repos.invites.claim(invite_id, user_id, now: datetime, *, session: Optional[Session] = None) -> bool` — `UPDATE invites SET accepted_at = :now, accepted_by = :user_id WHERE id = :invite_id AND accepted_at IS NULL` with `synchronize_session=False`; `True` iff `rowcount == 1`; ids through `as_uuid`; a loaded `Invite` is never changed by it (refresh to read the stored stamp). Later users: Task 5 (`invites.claim(...)` through the module, clarification 40), Task 8's barrier wrapper.
  - `repos.memberships.get_role(user_id, church_id, *, session: Optional[Session] = None) -> Optional[str]`. Later users: Tasks 4-5 (`member_role`).
  - `repos.memberships.ensure_membership(church_id, user_id, role: str, *, session: Optional[Session] = None) -> tuple[str, bool]` — `insert_ignore(Membership.__table__)…on_conflict_do_nothing(index_elements=["church_id", "user_id"])`, then selects the stored role; returns `(stored role, rowcount == 1)`; an existing membership keeps its role; ids through `as_uuid`. Later users: Task 5 (through the module), Task 8's reusable-race wrapper.

Counts after this task: backend **717 passed, 5 skipped** (705 + 12: `test_churches_repo.py` 4, `test_hymns_repo.py` 2, `test_invites_repo.py` 5, `test_memberships_repo.py` 1); frontend **126 passed in 23 files** (unchanged).

- [ ] **Step 1 (agent): Check the starting point**

```bash
git log --oneline -2
.venv/bin/python -m pytest -q | tail -1
grep -rn "seed_church_from_catalog(" backend | grep -v "def seed_church\|\.pyc"
```

**Expected:** Task 1's commit on top (`Backend: timezones.is_valid_timezone, engine hides bound parameters, …`); `705 passed, 5 skipped in <t>s`; exactly four callers, all passing `session` positionally: `backend/migrate_to_db.py:152`, `backend/repos/churches.py:27`, `backend/tests/test_hymns_repo.py:93`, `:112`. If the count differs, stop and ask.

- [ ] **Step 2 (agent): Write the failing tests**

In `backend/tests/test_churches_repo.py`, replace lines 1-10 (the imports, through the closing `)` of `from repos.churches import (`) with:

```python
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select, func, update

from db import session_scope
from db.models import Hymn, Invite, Church
from domain_errors import NotFound
from repos.churches import (
    create_church, create_church_seeded, get_church, list_user_churches,
    recent_owned_creations, soft_delete_church, update_church,
)
from repos.memberships import add_membership
```

and append at the end of the file (after line 63, `assert ch["settings"] == {"theme": "dark"}`):

```python


class _Abort(Exception):
    """Raised inside a caller's session_scope to roll that transaction back."""


NOW = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def _set_created_at(church_id, when):
    """The repo stamps created_at itself; cap tests move it to a fixed time."""
    with session_scope() as s:
        s.execute(update(Church).where(Church.id == church_id).values(created_at=when))


def _hymn_count(church_id=None):
    with session_scope() as s:
        q = select(func.count()).select_from(Hymn)
        if church_id is not None:
            q = q.where(Hymn.church_id == church_id)
        return s.execute(q).scalar_one()


def test_create_church_seeded_returns_id_and_hymn_count(tmp_db, make_user, seed_catalog):
    seed_catalog(4)
    owner = make_user(email="seeded@x.com")
    cid, seeded = create_church_seeded(
        name="Grace", timezone="America/Chicago", owner_user_id=str(owner),  # ids go through as_uuid
    )
    assert isinstance(cid, uuid.UUID)
    assert seeded == 4
    assert _hymn_count(cid) == 4
    assert list_user_churches(owner) == [{"id": cid, "name": "Grace", "role": "owner"}]
    with pytest.raises(NotFound):
        create_church(name="Bad", timezone="UTC", owner_user_id="not-a-uuid")


def test_create_church_uses_caller_session_without_commit(tmp_db, make_user, seed_catalog):
    seed_catalog(2)
    owner = make_user(email="caller@x.com")
    with pytest.raises(_Abort):
        with session_scope() as s:
            cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner, session=s)
            assert get_church(cid, session=s)["name"] == "Grace"
            assert s.execute(
                select(func.count()).select_from(Hymn).where(Hymn.church_id == cid)
            ).scalar_one() == 2
            raise _Abort  # the caller's rollback undoes the church, membership and hymns
    assert get_church(cid) is None
    assert list_user_churches(owner) == []
    assert _hymn_count() == 0


def test_recent_owned_creations_lists_owned_recent_and_soft_deleted(tmp_db, make_user):
    owner = make_user(email="cap@x.com")
    a = create_church(name="A", timezone="UTC", owner_user_id=owner)
    b = create_church(name="B", timezone="UTC", owner_user_id=owner)
    c = create_church(name="C", timezone="UTC", owner_user_id=owner)
    _set_created_at(a, NOW - timedelta(hours=1))
    _set_created_at(b, NOW - timedelta(hours=23))
    _set_created_at(c, NOW - timedelta(hours=5))
    soft_delete_church(b)  # deleting a church does not free a slot

    since = NOW - timedelta(hours=24)
    expected = [NOW - timedelta(hours=23), NOW - timedelta(hours=5), NOW - timedelta(hours=1)]
    times = recent_owned_creations(owner, since=since)
    assert times == expected  # oldest first, soft-deleted included
    assert all(t.tzinfo is timezone.utc for t in times)  # aware UTC, even from SQLite
    with session_scope() as s:
        assert recent_owned_creations(str(owner), since=since, session=s) == expected


def test_recent_owned_creations_skips_old_and_admin_only(tmp_db, make_user):
    owner = make_user(email="cap2@x.com")
    other = make_user(email="other@x.com")
    old = create_church(name="Old", timezone="UTC", owner_user_id=owner)
    edge = create_church(name="Edge", timezone="UTC", owner_user_id=owner)
    new = create_church(name="New", timezone="UTC", owner_user_id=owner)
    theirs = create_church(name="Theirs", timezone="UTC", owner_user_id=other)
    add_membership(owner, theirs, "admin")  # admin there, not owner: not counted
    _set_created_at(old, NOW - timedelta(hours=25))
    _set_created_at(edge, NOW - timedelta(hours=24))  # exactly `since`: not after it
    _set_created_at(new, NOW - timedelta(hours=2))
    _set_created_at(theirs, NOW - timedelta(hours=1))

    since = NOW - timedelta(hours=24)
    assert recent_owned_creations(owner, since=since) == [NOW - timedelta(hours=2)]
    assert recent_owned_creations(other, since=since) == [NOW - timedelta(hours=1)]
    # A non-UTC `since` means the same instant (SQLite compares naive UTC text).
    eastern = since.astimezone(timezone(timedelta(hours=-4)))
    assert recent_owned_creations(owner, since=eastern) == [NOW - timedelta(hours=2)]
```

In `backend/tests/test_hymns_repo.py`, replace lines 1-2:

```python
from db import session_scope
from repos.hymns import (
```

with:

```python
from sqlalchemy import event, select

from db import session_scope
from db.models import Hymn, HymnCatalog
from repos.hymns import (
```

and append at the end of the file (after line 115, `assert hymn["Hymnal Count"] == 1322`):

```python


SEEDED_COLUMNS = ("hymnal", "title", "number", "scripture_refs", "theme",
                  "hymnary_link", "audio_url", "text_year", "hymnal_count")


def _watch_hymn_inserts(engine) -> list:
    """Record each cursor execution that inserts into hymns (an executemany is one)."""
    seen = []

    @event.listens_for(engine, "before_cursor_execute")
    def _record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO HYMNS "):
            seen.append(statement)

    return seen


def test_seed_copies_every_catalog_column_in_bulk(tmp_db, make_user, make_church):
    cid = make_church(owner_user_id=make_user(email="bulk@grace.org"))
    with session_scope() as session:
        session.add_all([
            HymnCatalog(hymnal="GG2013", title="Holy, Holy, Holy", number=138,
                        scripture_refs="Revelation 4:8", theme="trinity, praise",
                        hymnary_link="https://hymnary.org/text/holy_holy_holy",
                        audio_url="https://example.org/138.mp3", text_year=1826,
                        hymnal_count=1322),
            HymnCatalog(hymnal="PH1990", title="Be Thou My Vision", number=339),
        ])
    inserts = _watch_hymn_inserts(tmp_db)
    built = []

    def _count_hymn_objects(target, args, kwargs):
        built.append(1)

    event.listen(Hymn, "init", _count_hymn_objects)
    try:
        with session_scope() as session:
            assert seed_church_from_catalog(cid, session) == 2
    finally:
        event.remove(Hymn, "init", _count_hymn_objects)
    # One INSERT for the whole catalog, and no Hymn object built per row.
    assert len(inserts) == 1
    assert built == []

    with session_scope() as session:
        catalog = session.execute(
            select(HymnCatalog).order_by(HymnCatalog.number)
        ).scalars().all()
        hymns = session.execute(
            select(Hymn).where(Hymn.church_id == cid).order_by(Hymn.number)
        ).scalars().all()
    assert [tuple(getattr(h, col) for col in SEEDED_COLUMNS) for h in hymns] == [
        tuple(getattr(c, col) for col in SEEDED_COLUMNS) for c in catalog
    ]
    assert len({h.id for h in hymns}) == 2
    assert not {h.id for h in hymns} & {c.id for c in catalog}  # fresh ids, not the catalog's


def test_seed_with_empty_catalog_inserts_nothing(tmp_db, make_user, make_church):
    cid = make_church(owner_user_id=make_user(email="empty@grace.org"))
    inserts = _watch_hymn_inserts(tmp_db)
    with session_scope() as session:
        # An empty parameter list would INSERT one all-defaults row (IntegrityError
        # on hymns.church_id), so the seed must skip the statement entirely.
        assert seed_church_from_catalog(cid, session) == 0
    assert inserts == []
    assert list_hymns(cid) == []
```

In `backend/tests/test_invites_repo.py`, replace lines 1-11 (the imports) with the block below. The existing `from repos.invites import (…)` line stays exactly as it is (Task 5 removes `accept_invite` from it); the new names go on a second line:

```python
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select

from db import session_scope
from db.models import Invite, Church
from repos.churches import create_church
from repos.memberships import get_role
from repos.invites import (
    create_invite, get_invite_by_code, accept_invite, list_invites, revoke_invite,
)
from repos.invites import _as_utc, as_utc, claim, find_by_code
```

and append at the end of the file (after line 104, `assert ok is False`; line 106 after the header change):

```python


class _Abort(Exception):
    """Raised inside a caller's session_scope to roll that transaction back."""


NOON = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)


def test_create_invite_reusable_flag_and_dict_keys(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    single = get_invite_by_code(create_invite(church_id=cid, created_by=owner))
    assert single["reusable"] is False and single["accepted_by"] is None
    shared = get_invite_by_code(create_invite(church_id=cid, created_by=owner, reusable=True))
    assert shared["reusable"] is True and shared["accepted_by"] is None

    with pytest.raises(_Abort):
        with session_scope() as s:
            code = create_invite(church_id=cid, created_by=owner, session=s)
            row = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
            assert row.church_id == cid  # written in the caller's transaction ...
            raise _Abort
    assert get_invite_by_code(code) is None  # ... and never committed by the repo


def test_find_by_code_returns_row_or_none(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, email="Bound@X.com", role="admin")
    inv = find_by_code(code)
    assert isinstance(inv, Invite)
    assert (inv.code, inv.church_id, inv.email, inv.role, inv.reusable) == (
        code, cid, "bound@x.com", "admin", False,
    )
    assert find_by_code("no-such-code") is None
    with session_scope() as s:
        assert find_by_code(code, session=s) is s.get(Invite, inv.id)  # the caller's session's row


def test_claim_first_wins_second_gets_false(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    first = make_user(email="first@x.com")
    second = make_user(email="second@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    inv = find_by_code(create_invite(church_id=cid, created_by=owner))

    assert claim(inv.id, first, NOON) is True
    assert claim(inv.id, second, NOON + timedelta(minutes=5)) is False
    with session_scope() as s:
        assert claim(str(inv.id), str(second), NOON, session=s) is False
    stored = find_by_code(inv.code)
    assert stored.accepted_by == first  # stamped once, by the first claimer
    assert as_utc(stored.accepted_at) == NOON


def test_claim_zero_rows_leaves_loaded_row_untouched(tmp_db, make_user):
    """A row loaded before another request stamped it keeps its loaded values
    after a claim that matched nothing (synchronize_session=False); the caller
    refreshes to see the winner, as usecases.onboarding.accept_invite does.
    The default synchronization would copy the loser's id into the row."""
    owner = make_user(email="o@x.com")
    winner = make_user(email="winner@x.com")
    loser = make_user(email="loser@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)

    with session_scope() as s:
        inv = find_by_code(code, session=s)  # loaded while still unclaimed
        assert claim(inv.id, winner, NOON) is True  # another request wins in its own transaction
        assert claim(inv.id, loser, NOON, session=s) is False
        assert inv.accepted_by is None and inv.accepted_at is None  # never the loser's id
        s.refresh(inv)
        assert inv.accepted_by == winner


def test_as_utc_is_exported_and_aliased():
    assert _as_utc is as_utc
    naive = datetime(2026, 9, 28, 12, 0)
    assert as_utc(naive) == NOON and as_utc(naive).tzinfo is timezone.utc
    eastern = datetime(2026, 9, 28, 8, 0, tzinfo=timezone(timedelta(hours=-4)))
    assert as_utc(eastern) == NOON and as_utc(eastern).tzinfo is timezone.utc
```

In `backend/tests/test_memberships_repo.py`, replace lines 9-12:

```python
from repos.memberships import (
    LastAdminError, get_role, add_membership, set_role,
    remove_membership, list_members, count_admins,
)
```

with:

```python
from repos.memberships import (
    LastAdminError, get_role, add_membership, set_role,
    remove_membership, list_members, count_admins, ensure_membership,
)
```

and append at the end of the file (after line 79, `assert count_admins(cid) == 1`):

```python


class _Abort(Exception):
    """Raised inside a caller's session_scope to roll that transaction back."""


def test_ensure_membership_inserts_then_reports_existing(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    joiner = make_user(email="j@x.com")
    late = make_user(email="late@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)

    assert ensure_membership(cid, joiner, "admin") == ("admin", True)
    assert ensure_membership(str(cid), str(joiner), "member") == ("admin", False)  # role kept
    assert ensure_membership(cid, owner, "member") == ("owner", False)
    assert get_role(joiner, cid) == "admin"

    with pytest.raises(_Abort):
        with session_scope() as s:
            assert ensure_membership(cid, late, "member", session=s) == ("member", True)
            assert get_role(late, cid, session=s) == "member"
            raise _Abort
    assert get_role(late, cid) is None  # the caller's rollback removed it
```

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_churches_repo.py backend/tests/test_invites_repo.py backend/tests/test_memberships_repo.py 2>&1 | grep -E "^E +ImportError|during collection" | sed -E 's/ \(\/.*\)$//'
.venv/bin/python -m pytest -q backend/tests/test_hymns_repo.py 2>&1 | grep -E "^E +assert|passed|failed"
```

**Expected:** exactly

```
E   ImportError: cannot import name 'create_church_seeded' from 'repos.churches'
E   ImportError: cannot import name 'as_utc' from 'repos.invites'
E   ImportError: cannot import name 'ensure_membership' from 'repos.memberships'
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
```

then `E       assert [1, 1] == []` and `1 failed, 7 passed in <t>s`: `test_seed_copies_every_catalog_column_in_bulk` fails because today's seed builds one `Hymn` object per row (the `init` listener counted two). `test_seed_with_empty_catalog_inserts_nothing` already passes: it pins the `if rows:` guard the bulk version needs (without it, the empty parameter list inserts one all-defaults row and raises `IntegrityError: NOT NULL constraint failed: hymns.church_id`).

- [ ] **Step 4 (agent): `backend/repos/churches.py`: `session`, `as_uuid`, `create_church_seeded`, `recent_owned_creations`**

Replace lines 1-42 (from `import datetime as _dt` through the `return {…}` dict that ends `get_church`) with the block below. Everything from `def list_user_churches` (line 45) down is unchanged.

```python
import datetime as _dt
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Church, Membership, Invite
from repos.invites import as_utc
from service_rubric import apply_patch, merge_rubric, validate_patch


def create_church(
    *, name, timezone, owner_user_id, session: Optional[Session] = None
) -> uuid.UUID:
    """Create a church, its creator's owner membership, and seed the per-church
    hymnal from the shared catalog — all in one transaction (atomic, so no admin
    ever sees a half-populated hymnal). Returns the new church id.

    Runs in the caller's `session` (no commit) or in its own scope.
    create_church_seeded also returns the number of hymns seeded.
    """
    church_id, _ = create_church_seeded(
        name=name, timezone=timezone, owner_user_id=owner_user_id, session=session
    )
    return church_id


def create_church_seeded(
    *, name, timezone, owner_user_id, session: Optional[Session] = None
) -> tuple[uuid.UUID, int]:
    """create_church, returning (church id, hymns seeded) for the
    `church_created ... hymns_seeded=` log line (usecases.onboarding).
    `owner_user_id` goes through as_uuid (a malformed id is NotFound)."""
    owner_id = as_uuid(owner_user_id)
    if session is not None:
        return _create_church(session, name, timezone, owner_id)
    with session_scope() as own:
        return _create_church(own, name, timezone, owner_id)


def _create_church(session, name, timezone, owner_id) -> tuple[uuid.UUID, int]:
    church = Church(name=name, timezone=timezone)
    session.add(church)
    session.flush()  # assign church.id (Python-side uuid default)
    session.add(Membership(church_id=church.id, user_id=owner_id, role="owner"))
    session.flush()  # the owner membership, before the hymn rows
    # Looked up at call time, so a test can monkeypatch
    # repos.hymns.seed_church_from_catalog (the atomicity test makes it raise).
    from repos.hymns import seed_church_from_catalog
    seeded = seed_church_from_catalog(church.id, session)
    return church.id, seeded


def get_church(church_id, *, session: Optional[Session] = None) -> Optional[dict]:
    """{"id", "name", "timezone", "settings"}, or None when the church is missing
    or soft-deleted. Reads in the caller's `session` or in its own scope."""
    if session is not None:
        return _get_church(session, church_id)
    with session_scope() as own:
        return _get_church(own, church_id)


def _get_church(session, church_id) -> Optional[dict]:
    church = session.get(Church, church_id)
    if church is None or church.deleted_at is not None:
        return None
    return {
        "id": church.id,
        "name": church.name,
        "timezone": church.timezone,
        "settings": church.settings,
    }


def recent_owned_creations(
    user_id, *, since: datetime, session: Optional[Session] = None
) -> list[datetime]:
    """created_at of every church `user_id` holds an owner membership in and
    that was created after `since`, oldest first, as aware UTC. Soft-deleted
    churches count, so deleting a church does not free a slot in the per-user
    create cap (usecases.onboarding.create_church)."""
    uid = as_uuid(user_id)
    since_utc = as_utc(since)  # SQLite compares naive UTC text
    if session is not None:
        return _recent_owned_creations(session, uid, since_utc)
    with session_scope() as own:
        return _recent_owned_creations(own, uid, since_utc)


def _recent_owned_creations(session, user_id, since) -> list[datetime]:
    stamps = session.execute(
        select(Church.created_at)
        .join(Membership, Membership.church_id == Church.id)
        .where(
            Membership.user_id == user_id,
            Membership.role == "owner",
            Church.created_at > since,
        )
        .order_by(Church.created_at)
    ).scalars().all()
    return [as_utc(stamp) for stamp in stamps]
```

- [ ] **Step 5 (agent): `backend/repos/hymns.py`: one Core bulk INSERT for the seed**

Replace line 9:

```python
from sqlalchemy import delete, select
```

with:

```python
from sqlalchemy import delete, insert, select
```

and replace lines 171-197 (the whole `seed_church_from_catalog`, the last function in the file) with:

```python
def seed_church_from_catalog(church_id, session: Session) -> int:
    """CANONICAL seed: copy every hymn_catalog row into a church's hymns.

    One Core INSERT over the hymns table with a fresh id per row, in the
    caller-supplied session (part of create_church's transaction); does NOT
    commit. No Hymn object is built per row, and every row carries the same
    keys, None included, so the whole list is one executemany (psycopg2
    batches it with insertmanyvalues). The ORM form, insert(Hymn), leaves out
    None values and splits the rows into one statement per null pattern.
    An empty catalog inserts nothing: an empty parameter list would insert
    one all-defaults row. Returns the number of hymns seeded.
    """
    cid = _as_uuid(church_id)
    catalog = session.execute(
        select(
            HymnCatalog.hymnal,
            HymnCatalog.title,
            HymnCatalog.number,
            HymnCatalog.scripture_refs,
            HymnCatalog.theme,
            HymnCatalog.hymnary_link,
            HymnCatalog.audio_url,
            HymnCatalog.text_year,
            HymnCatalog.hymnal_count,
        )
    ).all()
    rows = [
        {
            "id": uuid.uuid4(),
            "church_id": cid,
            "hymnal": c.hymnal,
            "title": c.title,
            "number": c.number,
            "scripture_refs": c.scripture_refs,
            "theme": c.theme,
            "hymnary_link": c.hymnary_link,
            "audio_url": c.audio_url,
            "text_year": c.text_year,
            "hymnal_count": c.hymnal_count,
        }
        for c in catalog
    ]
    if rows:
        session.execute(insert(Hymn.__table__), rows)
    return len(rows)
```

- [ ] **Step 6 (agent): `backend/repos/invites.py`: `as_utc`, `_to_dict` keys, `create_invite(reusable=, session=)`, `find_by_code`, `claim`**

Replace lines 1-63 (from `import secrets` through the end of `get_invite_by_code`) with the block below. `accept_invite` (then at lines 134-177), `list_invites` and `revoke_invite` are unchanged; Task 5 removes `accept_invite` and the imports only it uses (`Tuple`, `Church`, `Membership`, `User`).

```python
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Invite, Church, Membership, User


def _normalize_email(email) -> Optional[str]:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None


def as_utc(value: datetime) -> datetime:
    """Normalize a stored timestamp to aware-UTC. SQLite returns naive
    datetimes; Postgres returns aware ones. Assume naive == UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


_as_utc = as_utc  # the private name stays for existing callers


def _to_dict(inv: Invite) -> dict:
    return {
        "id": inv.id,
        "church_id": inv.church_id,
        "code": inv.code,
        "email": inv.email,
        "role": inv.role,
        "created_by": inv.created_by,
        "expires_at": inv.expires_at,
        "revoked": inv.revoked,
        "accepted_at": inv.accepted_at,
        "reusable": inv.reusable,
        "accepted_by": inv.accepted_by,
    }


def create_invite(
    *,
    church_id,
    created_by,
    role="member",
    email=None,
    ttl_days=7,
    reusable: bool = False,
    session: Optional[Session] = None,
) -> str:
    """Create an invite and return its code. Code is >=128 bits of url-safe
    entropy (secrets.token_urlsafe(32) == 256 bits).

    `reusable` lets several people join with the code until it expires or is
    revoked (slice 6b sets it); the default is single-use. Writes in the
    caller's `session` (flushed, not committed) or in its own scope.
    """
    code = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    invite = Invite(
        church_id=church_id,
        code=code,
        email=_normalize_email(email),
        role=role,
        created_by=created_by,
        expires_at=now + timedelta(days=ttl_days),
        revoked=False,
        reusable=reusable,
    )
    if session is not None:
        session.add(invite)
        session.flush()
        return code
    with session_scope() as own:
        own.add(invite)
    return code


def get_invite_by_code(code) -> Optional[dict]:
    with session_scope() as session:
        inv = session.execute(
            select(Invite).where(Invite.code == code)
        ).scalar_one_or_none()
        return _to_dict(inv) if inv is not None else None


def find_by_code(code: str, *, session: Optional[Session] = None) -> Optional[Invite]:
    """The Invite row for `code` (the caller strips it), or None. A global
    lookup by secret: only usecases.onboarding calls it, never a route. Without
    `session` the row comes back detached, its columns loaded."""
    if session is not None:
        return _find_by_code(session, code)
    with session_scope() as own:
        return _find_by_code(own, code)


def _find_by_code(session, code) -> Optional[Invite]:
    return session.execute(
        select(Invite).where(Invite.code == code)
    ).scalar_one_or_none()


def claim(invite_id, user_id, now: datetime, *, session: Optional[Session] = None) -> bool:
    """Stamp an unaccepted invite as accepted by `user_id` at `now`; True when
    this call stamped it:

        UPDATE invites SET accepted_at = :now, accepted_by = :user_id
        WHERE id = :invite_id AND accepted_at IS NULL

    The portable race guard: on Postgres a concurrent claimer waits on the row
    lock and then matches zero rows; SQLite serializes writers.
    synchronize_session=False: the default would copy `user_id` into an Invite
    already loaded in `session` even when no row matched, so a caller that
    needs the stored values refreshes the row.
    """
    stmt = (
        update(Invite)
        .where(Invite.id == as_uuid(invite_id), Invite.accepted_at.is_(None))
        .values(accepted_at=now, accepted_by=as_uuid(user_id))
        .execution_options(synchronize_session=False)
    )
    if session is not None:
        return session.execute(stmt).rowcount == 1
    with session_scope() as own:
        return own.execute(stmt).rowcount == 1
```

- [ ] **Step 7 (agent): `backend/repos/memberships.py`: `get_role(session=)`, `ensure_membership`**

Replace lines 1-6:

```python
from typing import Optional

from sqlalchemy import select, func, update

from db import session_scope
from db.models import Membership, User, Service
```

with:

```python
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Membership, User, Service
from db.upsert import insert_ignore
```

and replace `get_role` (lines 29-32 before the import change, 32-35 after it):

```python
def get_role(user_id, church_id) -> Optional[str]:
    with session_scope() as session:
        m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
        return m.role if m is not None else None
```

with:

```python
def get_role(user_id, church_id, *, session: Optional[Session] = None) -> Optional[str]:
    if session is not None:
        return _get_role(session, user_id, church_id)
    with session_scope() as own:
        return _get_role(own, user_id, church_id)


def _get_role(session, user_id, church_id) -> Optional[str]:
    m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
    return m.role if m is not None else None


def ensure_membership(
    church_id, user_id, role: str, *, session: Optional[Session] = None
) -> tuple[str, bool]:
    """Add `user_id` to `church_id` with `role` unless a membership exists;
    return (stored role, inserted). An existing membership keeps its role
    (role changes go through set_role).

    INSERT ... ON CONFLICT DO NOTHING, then a select: two concurrent same-user
    accepts never hit the primary key; the second waits for the first's row,
    inserts nothing (rowcount 0 on both dialects) and gets inserted=False.
    """
    cid, uid = as_uuid(church_id), as_uuid(user_id)
    if session is not None:
        return _ensure_membership(session, cid, uid, role)
    with session_scope() as own:
        return _ensure_membership(own, cid, uid, role)


def _ensure_membership(session, church_id, user_id, role) -> tuple[str, bool]:
    result = session.execute(
        insert_ignore(Membership.__table__)
        .values(church_id=church_id, user_id=user_id, role=role)
        .on_conflict_do_nothing(index_elements=["church_id", "user_id"])
    )
    stored = session.execute(
        select(Membership.role).where(
            Membership.church_id == church_id, Membership.user_id == user_id
        )
    ).scalar_one()
    return stored, result.rowcount == 1
```

- [ ] **Step 8 (agent): Run the tests to verify they pass, then the whole suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_churches_repo.py backend/tests/test_hymns_repo.py backend/tests/test_invites_repo.py backend/tests/test_memberships_repo.py 2>&1 | tail -3
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `35 passed in <t>s` (churches 4 + 4, hymns 6 + 2, invites 7 + 5, memberships 6 + 1; the existing `test_create_church_is_atomic_owns_and_seeds` at `test_churches_repo.py:13` and `test_hymns_repo.py:83,98,106` pass unchanged). Then `717 passed, 5 skipped in <t>s` (705 + 12). `git status --short` lists exactly the eight files below plus `?? .claude/`. If `test_claim_zero_rows_leaves_loaded_row_untouched` fails with `assert (UUID('…') is None)`, the `.execution_options(synchronize_session=False)` line is missing from `claim`. If `test_seed_copies_every_catalog_column_in_bulk` fails with `assert 2 == 1` on `len(inserts)`, the seed is using `insert(Hymn)` instead of `insert(Hymn.__table__)`.

- [ ] **Step 9 (agent): Commit**

```bash
git add backend/repos/churches.py backend/repos/hymns.py backend/repos/invites.py backend/repos/memberships.py \
        backend/tests/test_churches_repo.py backend/tests/test_hymns_repo.py \
        backend/tests/test_invites_repo.py backend/tests/test_memberships_repo.py
git commit -m "Repos: session parameters, create-cap query, bulk hymnal seed, invite claim and ensure_membership (S Repo changes 1b; F §2.2)

Every changed or new repo function takes an optional session, so one
usecase transaction can hold the cap check, the church and its seed, or
the invite checks and the claim. create_church_seeded returns the hymn
count for the church_created log line; create_church wraps it and keeps
returning the id. recent_owned_creations lists owned churches created in
the window (soft-deleted included), oldest first, as aware UTC.

The hymnal seed is one Core insert on the hymns table (the ORM form drops
None values and splits the rows into one INSERT per null pattern) and
skips an empty catalog. claim is the conditional UPDATE race guard with
synchronize_session=False; ensure_membership is insert-or-ignore on the
membership key, returning (stored role, inserted). create_invite gains
reusable (single-use by default), as_utc is exported, and _to_dict adds
reusable and accepted_by.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

**Expected:** `<sha> Repos: session parameters, create-cap query, bulk hymnal seed, invite claim and ensure_membership (S Repo changes 1b; F §2.2)`; `git status --short` then lists only `?? .claude/`.
### Task 3: `usecases.onboarding.create_church` and the per-user cap (S Modules added 1b, Rate limits; AC6; clarifications 5–7, 40, 42, 48)

This task creates `backend/usecases/onboarding.py` with the create half: the three dataclasses and the reject-reason enum
that Tasks 4 and 5 fill in, and `create_church` with the durable cap of 5 creates per user per 24 hours. The cap and the
insert run in one `session_scope`, so a seed failure leaves nothing behind, and a `RateLimited` raised inside it writes
nothing. `retry_after_seconds` counts from the (count − 4)-th oldest counted church, not the oldest (clarification 42;
owner decision 2; deviation from S Rate limits "until the oldest"): with six or more counted, the oldest ageing out still
leaves five. The usecase calls the repo through its module (`churches.create_church_seeded`), so tests can patch it
(clarification 40). The Streamlit create test is ported here and removed in the same commit (clarification 48).

The repo stamps `churches.created_at` with the real clock (`db/models.py` `_utcnow`), so every cap test injects
`now = NOW` and then moves each church's `created_at` to a fixed offset from `NOW` with an `UPDATE`.

**Files:**
- Create: `backend/usecases/onboarding.py` (create half; Tasks 4 and 5 append), `backend/tests/test_usecase_onboarding.py` (12 tests; Tasks 4 and 5 append)
- Modify: `backend/tests/test_no_streamlit_in_core.py` (`test_usecases_package_imports_no_fastapi_or_streamlit`: the import string at `:20` gains `usecases.onboarding`)
- Modify: `streamlit_tests/test_onboarding.py` (delete `test_create_church_makes_owner_and_seeds_hymnal`, `:19-27` at `0295b37`, ported here; Task 5 removes the accept test, Task 14 deletes the file)
- Test: `backend/tests/test_usecase_onboarding.py`, `backend/tests/test_no_streamlit_in_core.py`, `streamlit_tests/test_onboarding.py`

**Interfaces:**
- Consumes:
  - Task 1: `timezones.is_valid_timezone(name: str) -> bool` (exact, case-sensitive).
  - Task 2: `repos.churches.create_church_seeded(*, name, timezone, owner_user_id, session: Session | None = None) -> tuple[uuid.UUID, int]`
    (church + owner membership + catalog seed, no commit when `session` is given; the int is the number of hymns seeded);
    `repos.churches.recent_owned_creations(user_id, *, since: datetime, session: Session | None = None) -> list[datetime]`
    (ascending, timezone-aware UTC `created_at` of churches where the user holds `owner` and `created_at > since`, soft-deleted
    included); `repos.churches.create_church(*, name, timezone, owner_user_id, session=None) -> uuid.UUID` (tests only).
  - 1a: `db.session_scope()`, `db.ids.as_uuid(value) -> uuid.UUID`, `domain_errors.InvalidInput(message, *, field=...)`
    (422 `invalid_request`), `domain_errors.RateLimited(message, *, retry_after_seconds: float)` (sets `max(1, ceil(n))` and
    `details == {"retry_after_seconds": n}`).
  - Test fixtures (`backend/tests/conftest.py`): `tmp_db`, `make_user(email=...) -> uuid.UUID`, `make_church(name=..., timezone=..., owner_user_id=None) -> uuid.UUID`,
    `seed_catalog(n) -> int`; `repos.churches.get_church`, `list_user_churches`, `soft_delete_church`; `repos.hymns.list_hymns`;
    `repos.memberships.add_membership(user_id, church_id, role)`.
- Produces (module `usecases.onboarding`; imports `from repos import churches, invites, memberships`, clarification 40):
  - `@dataclass(frozen=True) class ChurchSummary: id: uuid.UUID; name: str; role: str` — Task 6 returns `ChurchOut(**asdict(summary))`; Task 5 nests it.
  - `@dataclass(frozen=True) class InvitePreview: church_name: str; role: str; expires_at: datetime; email_bound: bool; already_member: bool` — filled by Task 4.
  - `@dataclass(frozen=True) class InviteAccepted: church: ChurchSummary; already_member: bool; message: str` — filled by Task 5.
  - `class InviteRejectReason(StrEnum)`: `unknown`, `revoked`, `expired`, `used`, `church_unavailable`, `email_mismatch` (values equal the names) — Tasks 4, 5.
  - `CREATE_CAP = 5`, `CREATE_WINDOW = timedelta(hours=24)`, `CAP_MESSAGE = "You've created 5 churches in the last 24 hours. Try again later."`
  - `create_church(*, user_id: uuid.UUID, name: str, timezone: str, now: datetime | None = None) -> ChurchSummary`:
    `as_uuid(user_id)`; strip both inputs; `InvalidInput("Church name is required.", field="name")`, then
    `InvalidInput("Timezone is required.", field="timezone")`, then `InvalidInput("Unknown timezone.", field="timezone")`;
    then one `session_scope`: `_enforce_create_cap` and `churches.create_church_seeded(..., session=s)`; after the commit logs
    `church_created church_id=<uuid> user_id=<uuid> hymns_seeded=<n> duration_ms=<n>`; returns `ChurchSummary(id, <trimmed name>, "owner")`.
    Later users: Task 6 (`POST /churches`, inside `run_idempotent`'s `call`), Task 8 (seed timing).
  - `_enforce_create_cap(user_id: uuid.UUID, now: datetime, session) -> None`: `count = len(recent_owned_creations(user_id, since=now - CREATE_WINDOW, session=session))`;
    at `count >= CREATE_CAP` logs `church_create_limited user_id=<uuid> count=<n>` and raises
    `RateLimited(CAP_MESSAGE, retry_after_seconds=(times[count - CREATE_CAP] + CREATE_WINDOW - now).total_seconds())`.
  - Logger `logging.getLogger("usecases.onboarding")` (`__name__`); Tasks 4 and 5 log on it too.

- [ ] **Step 1 (agent): Check that Tasks 1 and 2 are in**

```bash
git log --oneline -3
ls backend/timezones.py
grep -n "^def create_church_seeded\|^def recent_owned_creations\|^def create_church(" backend/repos/churches.py
ls backend/usecases/
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** Task 2's commit on top; `backend/timezones.py`; three `def` lines (`create_church_seeded`, `create_church(`,
`recent_owned_creations`); `__init__.py` (and `__pycache__`) only, no `onboarding.py`; `717 passed, 5 skipped`. If the
count differs, stop and ask.

- [ ] **Step 2 (agent): Write the failing tests**

Create `backend/tests/test_usecase_onboarding.py`:

```python
"""usecases.onboarding (S Modules added 1b, Rate limits, Testing; slice 1b).

Task 3: create_church and the per-user cap. Tasks 4 and 5 append the invite
preview and accept tests. The cap tests inject `now` and move each church's
created_at to a fixed offset from it, because the repo stamps the real clock.
"""
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

import repos.churches
import repos.hymns
from db import session_scope
from db.models import Church, Membership
from domain_errors import InvalidInput, RateLimited
from repos.churches import get_church, list_user_churches, soft_delete_church
from repos.hymns import list_hymns
from repos.memberships import add_membership
from usecases import onboarding

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
TZ = "America/New_York"
CAP_TEXT = "You've created 5 churches in the last 24 hours. Try again later."


def _set_created_at(church_id, when):
    with session_scope() as s:
        s.execute(update(Church).where(Church.id == church_id).values(created_at=when))


def _owned_church(user_id, hours_ago, name="Earlier"):
    """A church the user owns, created `hours_ago` hours before NOW (repo call: no cap)."""
    church_id = repos.churches.create_church(name=name, timezone=TZ, owner_user_id=user_id)
    _set_created_at(church_id, NOW - timedelta(hours=hours_ago))
    return church_id


def _row_counts():
    """(churches, memberships) in the whole database."""
    with session_scope() as s:
        return (
            s.execute(select(func.count()).select_from(Church)).scalar_one(),
            s.execute(select(func.count()).select_from(Membership)).scalar_one(),
        )


# ---- create_church (Task 3) ----------------------------------------------------


def test_create_church_trims_and_returns_owner_summary(tmp_db, make_user):
    user = make_user(email="founder@b.org")
    summary = onboarding.create_church(
        user_id=user, name="  New Life  ", timezone=" America/Chicago ", now=NOW
    )
    assert isinstance(summary.id, uuid.UUID)
    assert summary == onboarding.ChurchSummary(id=summary.id, name="New Life", role="owner")
    church = get_church(summary.id)
    assert (church["name"], church["timezone"]) == ("New Life", "America/Chicago")
    assert list_user_churches(user) == [{"id": summary.id, "name": "New Life", "role": "owner"}]


@pytest.mark.parametrize(
    ("name", "timezone", "field", "message"),
    [
        ("   ", TZ, "name", "Church name is required."),
        ("Grace", "  ", "timezone", "Timezone is required."),
        ("Grace", "america/new_york", "timezone", "Unknown timezone."),
    ],
    ids=["name-blank", "tz-blank", "tz-unknown"],
)
def test_create_church_rejects(tmp_db, make_user, name, timezone, field, message):
    user = make_user(email="founder@b.org")
    with pytest.raises(InvalidInput) as exc:
        onboarding.create_church(user_id=user, name=name, timezone=timezone, now=NOW)
    assert (exc.value.message, exc.value.field, exc.value.code) == (
        message, field, "invalid_request"
    )
    assert _row_counts() == (0, 0)


def test_create_church_seeds_catalog_with_identical_values(tmp_db, make_user, seed_catalog):
    # Port of streamlit_tests/test_onboarding.py::test_create_church_makes_owner_and_seeds_hymnal.
    seed_catalog(5)
    user = make_user(email="founder@b.org")
    summary = onboarding.create_church(user_id=user, name="New Life", timezone=TZ, now=NOW)
    assert any(c["id"] == summary.id and c["role"] == "owner" for c in list_user_churches(user))
    hymns = list_hymns(summary.id)
    assert len(hymns) == 5  # seeded atomically from the catalog
    assert [
        (h["Hymnal"], h["Hymn Title"], h["Hymn Number"], h["Scripture References"],
         h["Theme"], h["Hymnary.org Link"], h["Audio"], h["Text Year"], h["Hymnal Count"])
        for h in hymns
    ] == [
        ("GG2013", f"Hymn {i}", i, f"John {i}:1-{i + 2}",
         "praise, grace", f"https://hymnary.org/hymn/{i}", None, None, None)
        for i in range(1, 6)
    ]


def test_create_church_is_atomic_when_seed_fails(tmp_db, make_user, seed_catalog, monkeypatch):
    seed_catalog(3)
    user = make_user(email="founder@b.org")

    def boom(*args, **kwargs):
        raise RuntimeError("seed failed")

    # The church repo resolves the seed from repos.hymns at call time; the second
    # patch keeps the test valid if that import ever moves to module level.
    monkeypatch.setattr(repos.hymns, "seed_church_from_catalog", boom)
    monkeypatch.setattr(repos.churches, "seed_church_from_catalog", boom, raising=False)
    with pytest.raises(RuntimeError, match="seed failed"):
        onboarding.create_church(user_id=user, name="New Life", timezone=TZ, now=NOW)
    assert _row_counts() == (0, 0)  # no church, no owner membership


# ---- the per-user cap (S Rate limits; clarification 42) --------------------------


def test_sixth_create_in_24h_is_rate_limited(tmp_db, make_user):
    user = make_user(email="founder@b.org")
    made = [
        onboarding.create_church(user_id=user, name=f"Church {i}", timezone=TZ, now=NOW)
        for i in range(1, 6)
    ]
    for summary, hours_ago in zip(made, [23, 20, 15, 10, 1]):
        _set_created_at(summary.id, NOW - timedelta(hours=hours_ago))
    with pytest.raises(RateLimited) as exc:
        onboarding.create_church(user_id=user, name="Church 6", timezone=TZ, now=NOW)
    assert (exc.value.message, exc.value.code) == (CAP_TEXT, "rate_limited")
    assert exc.value.retry_after_seconds == 3600  # the oldest turns 24 h old in one hour
    assert exc.value.details == {"retry_after_seconds": 3600}
    assert _row_counts() == (5, 5)


def test_retry_after_uses_the_fifth_newest_when_over_cap(tmp_db, make_user):
    # Six counted (the frozen Streamlit app has no cap, and two concurrent creates
    # can both pass at four): when the oldest ages out five remain, so Retry-After
    # runs until the second oldest is 24 h old.
    user = make_user(email="founder@b.org")
    for hours_ago in [23.5, 22, 20, 15, 10, 1]:
        _owned_church(user, hours_ago)
    with pytest.raises(RateLimited) as exc:
        onboarding.create_church(user_id=user, name="Seventh", timezone=TZ, now=NOW)
    assert exc.value.retry_after_seconds == 2 * 3600


def test_cap_ignores_churches_older_than_24h(tmp_db, make_user):
    user = make_user(email="founder@b.org")
    for hours_ago in [25, 20, 15, 10, 1]:
        _owned_church(user, hours_ago)
    summary = onboarding.create_church(user_id=user, name="Another", timezone=TZ, now=NOW)
    assert summary.role == "owner"


def test_cap_counts_soft_deleted(tmp_db, make_user):
    user = make_user(email="founder@b.org")
    church_ids = [_owned_church(user, hours_ago) for hours_ago in [20, 15, 10, 5, 1]]
    soft_delete_church(church_ids[0])  # delete-and-recreate does not reset the cap
    with pytest.raises(RateLimited) as exc:
        onboarding.create_church(user_id=user, name="Again", timezone=TZ, now=NOW)
    assert exc.value.retry_after_seconds == 4 * 3600


def test_cap_ignores_admin_only_churches(tmp_db, make_user, make_church):
    user = make_user(email="helper@b.org")
    for i in range(1, 6):
        church_id = make_church(name=f"Other {i}")  # owned by a fresh user each time
        add_membership(user, church_id, "admin")
        _set_created_at(church_id, NOW - timedelta(hours=1))
    summary = onboarding.create_church(user_id=user, name="My Own", timezone=TZ, now=NOW)
    assert summary.role == "owner"


def test_create_logs_ids_only(tmp_db, make_user, seed_catalog, caplog):
    seed_catalog(5)
    user = make_user(email="founder@b.org")
    for hours_ago in [20, 15, 10, 5]:
        _owned_church(user, hours_ago)
    caplog.set_level(logging.INFO, logger="usecases.onboarding")
    summary = onboarding.create_church(
        user_id=user, name="Secret Name Church", timezone=TZ, now=NOW
    )
    _set_created_at(summary.id, NOW - timedelta(hours=1))
    with pytest.raises(RateLimited):
        onboarding.create_church(user_id=user, name="Secret Name Two", timezone=TZ, now=NOW)
    created, limited = [r.getMessage() for r in caplog.records if r.name == "usecases.onboarding"]
    assert re.fullmatch(
        rf"church_created church_id={summary.id} user_id={user} hymns_seeded=5 duration_ms=\d+",
        created,
    )
    assert limited == f"church_create_limited user_id={user} count=5"
    assert "Secret Name" not in caplog.text
    assert "founder@b.org" not in caplog.text
```

In `backend/tests/test_no_streamlit_in_core.py`, replace the whole function `test_usecases_package_imports_no_fastapi_or_streamlit`
(after Task 1 its import string at `:20` reads `"import sys, usecases, domain_errors, db.ids, timezones; "`) with:

```python
def test_usecases_package_imports_no_fastapi_or_streamlit():
    # usecases (including usecases.onboarding), domain_errors, db.ids and
    # timezones are below the API layer (F §2.2).
    code = ("import sys, usecases, usecases.onboarding, domain_errors, db.ids, timezones; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
            "print(bad); sys.exit(1 if bad else 0)")
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=CODE_DIR, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_onboarding.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3
```

**Expected:** a collection error (`ImportError: cannot import name 'onboarding' from 'usecases'`) ending
`1 error in …`; then `1 failed, 2 passed`: `test_usecases_package_imports_no_fastapi_or_streamlit` fails because its
subprocess raises `ModuleNotFoundError: No module named 'usecases.onboarding'`.

- [ ] **Step 4 (agent): Create `backend/usecases/onboarding.py`**

```python
"""Onboarding usecases: create a church, preview an invite, accept an invite (S Modules added 1b).

Task 3 of slice 1b adds create_church and the per-user cap; Tasks 4 and 5 add
preview_invite and accept_invite. The layer rules are in usecases/__init__.py:
no FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).

Repos are called through their modules (churches.create_church_seeded, not a
from-import), so tests can patch one repo function (clarification 40).

Log lines carry ids, counts and reasons only: never a church name, an email
or an invite code (AC9).
"""
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from db import session_scope
from db.ids import as_uuid
from domain_errors import InvalidInput, RateLimited
from repos import churches, invites, memberships  # noqa: F401  (invites, memberships: Tasks 4-5)
from timezones import is_valid_timezone

logger = logging.getLogger(__name__)

# The durable per-user cap on POST /churches (S Rate limits).
CREATE_CAP = 5
CREATE_WINDOW = timedelta(hours=24)
CAP_MESSAGE = "You've created 5 churches in the last 24 hours. Try again later."


@dataclass(frozen=True)
class ChurchSummary:
    id: uuid.UUID
    name: str
    role: str


@dataclass(frozen=True)
class InvitePreview:
    church_name: str
    role: str  # _clamp_role(invite.role): "member" or "admin"
    expires_at: datetime  # as_utc(invite.expires_at): always timezone-aware UTC
    email_bound: bool
    already_member: bool


@dataclass(frozen=True)
class InviteAccepted:
    church: ChurchSummary
    already_member: bool
    message: str


class InviteRejectReason(StrEnum):
    """details.reason of a 400 invite_rejected, in check order (S Invite checks)."""

    unknown = "unknown"
    revoked = "revoked"
    expired = "expired"
    used = "used"
    church_unavailable = "church_unavailable"
    email_mismatch = "email_mismatch"


def create_church(
    *, user_id: uuid.UUID, name: str, timezone: str, now: datetime | None = None
) -> ChurchSummary:
    """Create a church the caller owns, with its own copy of the hymn catalog.

    Both inputs are stripped first. The checks raise InvalidInput for the field
    they are about, in this order: name, blank timezone, unknown timezone. The
    per-user cap and the insert share one transaction, so a failed seed leaves
    no church and no membership. Returns the stored (trimmed) name.
    """
    user_id = as_uuid(user_id)
    name = (name or "").strip()
    timezone = (timezone or "").strip()
    if not name:
        raise InvalidInput("Church name is required.", field="name")
    if not timezone:
        raise InvalidInput("Timezone is required.", field="timezone")
    if not is_valid_timezone(timezone):
        raise InvalidInput("Unknown timezone.", field="timezone")
    now = now if now is not None else datetime.now(UTC)
    started = time.monotonic()
    with session_scope() as s:
        _enforce_create_cap(user_id, now, s)
        church_id, hymns_seeded = churches.create_church_seeded(
            name=name, timezone=timezone, owner_user_id=user_id, session=s
        )
    logger.info(
        "church_created church_id=%s user_id=%s hymns_seeded=%d duration_ms=%d",
        church_id, user_id, hymns_seeded, round((time.monotonic() - started) * 1000),
    )
    return ChurchSummary(id=church_id, name=name, role="owner")


def _enforce_create_cap(user_id: uuid.UUID, now: datetime, session) -> None:
    """Raise RateLimited when the caller owns CREATE_CAP or more churches created in the window.

    Soft-deleted churches count, so delete-and-recreate does not reset the cap;
    churches the caller only administers do not. Retry-After runs until the
    count would drop below the cap: the (count - 4)-th oldest turning 24 h old,
    which is the oldest when exactly five are counted (clarification 42).
    """
    created = churches.recent_owned_creations(
        user_id, since=now - CREATE_WINDOW, session=session
    )
    count = len(created)
    if count < CREATE_CAP:
        return
    frees_at = created[count - CREATE_CAP] + CREATE_WINDOW
    logger.info("church_create_limited user_id=%s count=%d", user_id, count)
    raise RateLimited(CAP_MESSAGE, retry_after_seconds=(frees_at - now).total_seconds())
```

- [ ] **Step 5 (agent): Remove the ported Streamlit create test**

In `streamlit_tests/test_onboarding.py`, delete this block (`:19-29` at `0295b37`: the test at `:19-27` and the two blank lines after it).
Its assertions (owner membership in `list_user_churches`, five hymns seeded from `seed_catalog(5)`) now live in
`test_create_church_seeds_catalog_with_identical_values`, which also compares the copied values:

```python
def test_create_church_makes_owner_and_seeds_hymnal(tmp_db, make_user, seed_catalog):
    from repos.churches import create_church, list_user_churches
    from repos.hymns import list_hymns
    seed_catalog(5)
    user = make_user(email="founder@b.org")
    cid = create_church(name="New Life", timezone="America/New_York", owner_user_id=user)
    mine = list_user_churches(user)
    assert any(c["id"] == cid and c["role"] == "owner" for c in mine)
    assert len(list_hymns(cid)) == 5  # seeded atomically from the catalog


```

The file keeps its three `pick_invite_code` tests and `test_accept_captured_invite_joins_as_member` (Task 5 ports and
removes that one; Task 14 deletes the file).

- [ ] **Step 6 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_onboarding.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3
.venv/bin/python -m pytest -q streamlit_tests/test_onboarding.py 2>&1 | tail -1
grep -rnI "test_create_church_makes_owner_and_seeds_hymnal" backend streamlit_tests | wc -l
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `15 passed` (12 new + the 3 in `test_no_streamlit_in_core.py`); `4 passed`; `0`; then
`728 passed, 5 skipped` (717 + 12 − 1).

- [ ] **Step 7 (agent): Commit**

```bash
git add backend/usecases/onboarding.py backend/tests/test_usecase_onboarding.py \
        backend/tests/test_no_streamlit_in_core.py streamlit_tests/test_onboarding.py
git commit -m "Onboarding: create_church usecase with the 5-per-24-hours owner cap (S Modules added 1b, Rate limits; AC6)

usecases.onboarding.create_church strips the name and time zone, checks
them in order (name, blank zone, unknown IANA zone) and then, in one
transaction, counts the caller's owned churches created in the last 24
hours (soft-deleted included, admin-only excluded) and creates the church
with its owner membership and hymnal seed. The sixth create raises
RateLimited; Retry-After runs until the (count - 4)-th oldest turns 24 h
old (clarification 42). Logs church_created and church_create_limited with
ids and counts only. The dataclasses and InviteRejectReason for the invite
usecases are declared here. The Streamlit create test is ported and removed
(clarification 48).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit; `git status --short` shows only `?? .claude/`.

Counts after Task 3: backend **728 passed, 5 skipped**; frontend unchanged (**126 passed in 23 files**).
### Task 4: `preview_invite` and the shared invite checks (S Invite checks, Preview semantics; AC7; clarifications 2, 14)

This task appends the invite half's shared pieces to `backend/usecases/onboarding.py`: the six rejection messages, check 0
(`_strip_code`), the three reads both usecases start from (`_load_invite`), the role clamp, checks 1–6 in S's order
(`_evaluate`), the rejection helper that logs `invite_rejected` and raises the 400 (`_reject`), and the read-only
`preview_invite`. Task 5 builds `accept_invite` on the same helpers and adds an `accept` entry to the tests' `INVITE_ACTIONS`,
so every rejection and blank-code test then runs for both actions.

Facts from the code that shape the tests:
- `repos.churches.get_church` returns a dict (`{"id","name","timezone","settings"}`) or `None` for a missing or soft-deleted
  church (clarification 2), so `_evaluate` takes `church: dict | None` and the preview reads `church["name"]`.
- `repos.churches.soft_delete_church` also revokes every pending invite of the church (`repos/churches.py:64-72` at `0295b37`).
  So "revoked beats church_unavailable" is exactly what a soft delete produces, and the `church_unavailable` case sets
  `churches.deleted_at` directly, leaving the invite live (as `test_invites_repo.py:43-54` does today).
- `invites.role` has no CHECK constraint (`db/models.py:91`), so a test can store `owner` or `foo` through
  `create_invite(role=...)`; `memberships.role` does (`:74-78`), which is why the clamp exists.
- SQLite hands back naive datetimes, so every test invite gets a naive midday-UTC `expires_at` (Global Constraints) and the
  clock is injected (`now=INVITE_NOW`), never the real one.
- Task 3's `create_church` has a parameter named `timezone`, so the module imports `UTC` from `datetime`, not `timezone`;
  this task uses `datetime.now(UTC)` the same way. Task 3's test file already defines `NOW` and `_row_counts()`, so this
  task's names are `INVITE_NOW` and `_all_row_counts()`.
- Legacy consumed invites with `accepted_by` NULL get `used` even for a current member (clarification 14): `_evaluate`'s
  check 4 exception needs `accepted_by == caller` **and** a current membership. Task 5 pins the legacy case; this task pins
  the exception and the removed-member case through the preview.

The clamp WARNING is `invite_role_clamped invite_id=<uuid> granted=<role>` (S names only "a WARNING with the invite id";
this is the exact text the plan fixes). The rejection line is S's `invite_rejected reason=<reason> invite_id=<uuid|none>`.
Neither carries the code or an email (AC9).

**Files:**
- Modify: `backend/usecases/onboarding.py` (import block; append the invite checks and `preview_invite` after `_enforce_create_cap`)
- Modify: `backend/tests/test_usecase_onboarding.py` (import block; append 18 tests after Task 3's last test)
- Test: `backend/tests/test_usecase_onboarding.py`, `backend/tests/test_no_streamlit_in_core.py` (unchanged; re-run, since the module gains imports)

**Interfaces:**
- Consumes:
  - Task 2: `repos.invites.find_by_code(code: str, *, session: Session | None = None) -> Invite | None` (the ORM row);
    `repos.invites.as_utc(dt: datetime) -> datetime` (naive → UTC, aware → converted to UTC);
    `repos.churches.get_church(church_id, *, session: Session | None = None) -> dict | None`;
    `repos.memberships.get_role(user_id, church_id, *, session: Session | None = None) -> str | None`.
    All called through the modules imported by Task 3 (`from repos import churches, invites, memberships`; clarification 40).
  - Task 3: `InvitePreview(church_name, role, expires_at, email_bound, already_member)` (frozen dataclass),
    `InviteRejectReason(StrEnum)` (`unknown`, `revoked`, `expired`, `used`, `church_unavailable`, `email_mismatch`; values
    equal the names), `logger = logging.getLogger(__name__)` (`"usecases.onboarding"`); the test file's imports, `tmp_db` use,
    and the conftest fixtures `make_user(email=...)`, `make_church(name=..., timezone=..., owner_user_id=...)` (owner
    membership, no hymns).
  - 1a: `db.session_scope()`, `db.ids.as_uuid`, `domain_errors.InvalidInput(message, *, field=...)` (422 `invalid_request`),
    `domain_errors.Rejected(message, *, code="invite_rejected", details=...)` (400; no default code);
    `repos.invites.create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7, ...) -> str`
    (normalizes the email), `repos.invites.get_invite_by_code(code) -> dict | None`,
    `repos.churches.soft_delete_church(church_id)`, `repos.memberships.add_membership(user_id, church_id, role)`,
    `repos.memberships.remove_membership(user_id, church_id)`.
- Produces (module `usecases.onboarding`):
  - `BLANK_CODE_MESSAGE = "Enter an invite code, or open your invite link again."`
  - `REJECT_MESSAGES: dict[InviteRejectReason, str]` — `unknown` "Invalid invite code.", `revoked` "This invite has been
    revoked.", `expired` "This invite has expired.", `used` "This invite has already been used.", `church_unavailable`
    "This church is no longer available.", `email_mismatch` "This invite was issued for a different email address.".
  - `_strip_code(code: str) -> str` — check 0: returns the stripped code; blank or whitespace-only raises
    `InvalidInput(BLANK_CODE_MESSAGE, field="code")`. Task 5 calls it first.
  - `_load_invite(s, code: str, user_id: uuid.UUID) -> tuple` — `(inv, church, member_role)`: `invites.find_by_code(code, session=s)`,
    then `churches.get_church(inv.church_id, session=s)` if `inv`, then `memberships.get_role(user_id, church["id"], session=s)`
    if `church`; each `None` when its input is. Task 5 calls it inside its own `session_scope`.
  - `_clamp_role(role: str | None, *, invite_id) -> str` — `member`/`admin` as stored; `owner` → `admin`; anything else
    (including `None`) → `member`; a clamp logs WARNING `invite_role_clamped invite_id=<id> granted=<role>`.
  - `_evaluate(inv, church: dict | None, user_id: uuid.UUID, user_email: str, member_role: str | None, now: datetime) -> InviteRejectReason | None`
    — checks 1–6 in order: `inv is None` → `unknown`; `inv.revoked` → `revoked`; `invites.as_utc(inv.expires_at) < now` →
    `expired`; `not inv.reusable and inv.accepted_at is not None` and not (`inv.accepted_by == user_id` and
    `member_role is not None`) → `used`; `church is None` → `church_unavailable`; `inv.email is not None` and
    `inv.email.strip().lower() != user_email.strip().lower()` → `email_mismatch`; else `None`.
  - `_reject(reason: InviteRejectReason, invite_id) -> NoReturn` — logs INFO `invite_rejected reason=<reason> invite_id=<id>`
    (`invite_id=none` when `invite_id is None`) and raises `Rejected(REJECT_MESSAGES[reason], code="invite_rejected",
    details={"reason": reason.value})`. Task 5 calls it for every rejection, including the claim-lost `used`.
  - `preview_invite(*, user_id: uuid.UUID, user_email: str, code: str, now: datetime | None = None) -> InvitePreview` —
    `as_uuid(user_id)`, `_strip_code`, `now` defaults to `datetime.now(UTC)`; one `session_scope`, no writes;
    `_load_invite` → `_evaluate` → `_reject` or `InvitePreview(church_name=church["name"], role=_clamp_role(inv.role, invite_id=inv.id),
    expires_at=invites.as_utc(inv.expires_at), email_bound=inv.email is not None, already_member=member_role is not None)`.
    Later users: Task 7 (`POST /invites/preview`).
  - Test module names Task 5 extends: `INVITE_ACTIONS = {"preview": onboarding.preview_invite}` (Task 5 adds
    `"accept": onboarding.accept_invite`, giving `test_invite_rejections[accept-…]` ×6 and `test_blank_code_is_invalid_input[accept]`),
    `REJECTIONS`, `INVITE_NOW`, `INVITE_EXPIRES`, `JOINER_EMAIL`, `_update_invite(code, **values)`, `_invite(church_id, created_by, **kwargs) -> str`,
    `_invite_id(code)`, `_all_row_counts() -> dict`, fixture `invite_world` (`owner`, `joiner`, `other`, `church_id` of "Grace"),
    `_rejected_code(reason, world) -> str`.

- [ ] **Step 1 (agent): Check that Task 3 is in**

```bash
git log --oneline -3
grep -n "^class InviteRejectReason\|^def create_church\|^def preview_invite\|noqa: F401" backend/usecases/onboarding.py
grep -n "^def find_by_code\|^def as_utc" backend/repos/invites.py
grep -n "^def get_church\|^def get_role" backend/repos/churches.py backend/repos/memberships.py
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** Task 3's commit on top; `class InviteRejectReason(StrEnum):`, `def create_church(` and the
`from repos import churches, invites, memberships  # noqa: F401  (invites, memberships: Tasks 4-5)` line, and **no**
`def preview_invite`; `def find_by_code(` and `def as_utc(` in `repos/invites.py`; `def get_church(church_id, *, session`
and `def get_role(user_id, church_id, *, session` (Task 2); `728 passed, 5 skipped`. If the count differs, stop and ask.

- [ ] **Step 2 (agent): Write the failing tests**

In `backend/tests/test_usecase_onboarding.py`, replace Task 3's import block:

```python
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

import repos.churches
import repos.hymns
from db import session_scope
from db.models import Church, Membership
from domain_errors import InvalidInput, RateLimited
from repos.churches import get_church, list_user_churches, soft_delete_church
from repos.hymns import list_hymns
from repos.memberships import add_membership
from usecases import onboarding
```

with:

```python
import dataclasses
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

import repos.churches
import repos.hymns
import repos.invites
from db import session_scope
from db.models import Church, Invite, Membership, User
from domain_errors import InvalidInput, RateLimited, Rejected
from repos.churches import get_church, list_user_churches, soft_delete_church
from repos.hymns import list_hymns
from repos.memberships import add_membership, get_role, remove_membership
from usecases import onboarding
```

Then append to the end of the file (two blank lines after Task 3's last test, `test_create_logs_ids_only`):

```python
# ---- invite checks and preview_invite (Task 4; Task 5 adds accept) ----------------

# The injected clock for every invite test, and the expiry every test invite
# gets: midday UTC, stored naive because SQLite hands back naive UTC anyway.
INVITE_NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
INVITE_EXPIRES = datetime(2026, 10, 8, 12, 0)

JOINER_EMAIL = "joiner@example.com"

# Every action that runs the shared checks. T5 adds "accept": onboarding.accept_invite.
INVITE_ACTIONS = {"preview": onboarding.preview_invite}

REJECTIONS = {
    "unknown": "Invalid invite code.",
    "revoked": "This invite has been revoked.",
    "expired": "This invite has expired.",
    "used": "This invite has already been used.",
    "church_unavailable": "This church is no longer available.",
    "email_mismatch": "This invite was issued for a different email address.",
}


def _update_invite(code, **values):
    with session_scope() as s:
        s.execute(update(Invite).where(Invite.code == code).values(**values))


def _invite(church_id, created_by, **kwargs) -> str:
    """repos.invites.create_invite, then pin expires_at to INVITE_EXPIRES."""
    code = repos.invites.create_invite(church_id=church_id, created_by=created_by, **kwargs)
    _update_invite(code, expires_at=INVITE_EXPIRES)
    return code


def _invite_id(code):
    with session_scope() as s:
        return s.execute(select(Invite.id).where(Invite.code == code)).scalar_one()


def _all_row_counts() -> dict:
    with session_scope() as s:
        return {
            model.__tablename__: s.execute(select(func.count()).select_from(model)).scalar_one()
            for model in (User, Church, Membership, Invite)
        }


@pytest.fixture
def invite_world(make_user, make_church):
    """An owner, a joiner, a third user, and the church "Grace" (no hymns)."""
    owner = make_user(email="owner@example.com")
    joiner = make_user(email=JOINER_EMAIL)
    other = make_user(email="other@example.com")
    church_id = make_church(name="Grace", timezone="America/New_York", owner_user_id=owner)
    return {"owner": owner, "joiner": joiner, "other": other, "church_id": church_id}


def _rejected_code(reason, world) -> str:
    """An invite that fails exactly check `reason` for the joiner at INVITE_NOW."""
    cid, owner = world["church_id"], world["owner"]
    if reason == "unknown":
        return "no-such-invite-code"
    if reason == "email_mismatch":
        return _invite(cid, owner, email="someone.else@example.com")
    code = _invite(cid, owner)
    if reason == "revoked":
        _update_invite(code, revoked=True)
    elif reason == "expired":
        _update_invite(code, expires_at=datetime(2026, 10, 1, 11, 59))
    elif reason == "used":
        _update_invite(code, accepted_at=datetime(2026, 9, 30, 12, 0), accepted_by=world["other"])
    elif reason == "church_unavailable":
        # Soft-delete the church directly, leaving the invite live (soft_delete_church
        # would revoke it, and check 2 would win).
        with session_scope() as s:
            s.execute(update(Church).where(Church.id == cid).values(deleted_at=INVITE_NOW))
    return code


@pytest.mark.parametrize("reason", list(REJECTIONS))
@pytest.mark.parametrize("action", list(INVITE_ACTIONS))
def test_invite_rejections(action, reason, invite_world, caplog):
    code = _rejected_code(reason, invite_world)
    before = _all_row_counts()
    caplog.set_level(logging.INFO, logger="usecases.onboarding")

    with pytest.raises(Rejected) as exc:
        INVITE_ACTIONS[action](
            user_id=invite_world["joiner"], user_email=JOINER_EMAIL,
            code=f"  {code}\n", now=INVITE_NOW,  # stripped before lookup
        )

    assert exc.value.status == 400
    assert exc.value.code == "invite_rejected"
    assert exc.value.message == REJECTIONS[reason]
    assert exc.value.details == {"reason": reason}
    assert exc.value.field is None
    invite_id = "none" if reason == "unknown" else str(_invite_id(code))
    assert [r.getMessage() for r in caplog.records if r.getMessage().startswith("invite_rejected")] == [
        f"invite_rejected reason={reason} invite_id={invite_id}"
    ]
    assert code not in caplog.text and JOINER_EMAIL not in caplog.text
    assert _all_row_counts() == before


@pytest.mark.parametrize("action", list(INVITE_ACTIONS))
def test_blank_code_is_invalid_input(action, invite_world):
    for blank in ("", "   ", "\t\n"):
        with pytest.raises(InvalidInput) as exc:
            INVITE_ACTIONS[action](
                user_id=invite_world["joiner"], user_email=JOINER_EMAIL, code=blank, now=INVITE_NOW,
            )
        assert exc.value.status == 422
        assert exc.value.code == "invalid_request"
        assert exc.value.message == "Enter an invite code, or open your invite link again."
        assert exc.value.field == "code"


def _preview_reason(world, code) -> str:
    with pytest.raises(Rejected) as exc:
        onboarding.preview_invite(
            user_id=world["joiner"], user_email=JOINER_EMAIL, code=code, now=INVITE_NOW,
        )
    return exc.value.details["reason"]


def test_order_revoked_beats_church_unavailable(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"])
    soft_delete_church(invite_world["church_id"])   # also revokes pending invites
    assert get_church(invite_world["church_id"]) is None
    assert repos.invites.get_invite_by_code(code)["revoked"] is True
    assert _preview_reason(invite_world, code) == "revoked"


def test_order_expired_beats_used(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"])
    _update_invite(
        code, expires_at=datetime(2026, 10, 1, 11, 59),
        accepted_at=datetime(2026, 9, 30, 12, 0), accepted_by=invite_world["other"],
    )
    assert _preview_reason(invite_world, code) == "expired"


def test_order_used_beats_email_mismatch(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"], email="other@example.com")
    _update_invite(code, accepted_at=datetime(2026, 9, 30, 12, 0), accepted_by=invite_world["other"])
    assert _preview_reason(invite_world, code) == "used"


@pytest.mark.parametrize(("stored", "granted"), [("owner", "admin"), ("foo", "member")])
def test_clamp_role(stored, granted, caplog):
    invite_id = uuid.uuid4()
    caplog.set_level(logging.WARNING, logger="usecases.onboarding")
    assert onboarding._clamp_role("member", invite_id=invite_id) == "member"
    assert onboarding._clamp_role("admin", invite_id=invite_id) == "admin"
    assert caplog.records == []                                   # no clamp, no warning

    assert onboarding._clamp_role(stored, invite_id=invite_id) == granted

    [record] = caplog.records
    assert record.levelno == logging.WARNING
    assert record.getMessage() == f"invite_role_clamped invite_id={invite_id} granted={granted}"


def test_naive_expires_at_is_utc_with_injected_now(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"])
    _update_invite(code, expires_at=datetime(2026, 10, 1, 12, 0))   # naive: 12:00 UTC

    def preview_at(now):
        return onboarding.preview_invite(
            user_id=invite_world["joiner"], user_email=JOINER_EMAIL, code=code, now=now,
        )

    # 06:59 at UTC-5 is 11:59 UTC: one minute before expiry, still good.
    assert preview_at(datetime.fromisoformat("2026-10-01T06:59:00-05:00")).church_name == "Grace"
    # Exactly the expiry instant is not "expires_at < now".
    assert preview_at(datetime(2026, 10, 1, 12, 0, tzinfo=UTC)).church_name == "Grace"
    # 07:01 at UTC-5 is 12:01 UTC: expired.
    with pytest.raises(Rejected) as exc:
        preview_at(datetime.fromisoformat("2026-10-01T07:01:00-05:00"))
    assert exc.value.details == {"reason": "expired"}


def test_preview_writes_nothing_and_has_five_fields(invite_world):
    cid, owner, joiner = invite_world["church_id"], invite_world["owner"], invite_world["joiner"]
    code = _invite(cid, owner)
    bound = _invite(cid, owner, email="Joiner@Example.com", role="admin")
    before = _all_row_counts()

    preview = onboarding.preview_invite(user_id=joiner, user_email=JOINER_EMAIL, code=code, now=INVITE_NOW)
    bound_preview = onboarding.preview_invite(user_id=joiner, user_email=JOINER_EMAIL, code=bound, now=INVITE_NOW)

    assert dataclasses.asdict(preview) == {
        "church_name": "Grace",
        "role": "member",
        "expires_at": datetime(2026, 10, 8, 12, 0, tzinfo=UTC),
        "email_bound": False,
        "already_member": False,
    }
    assert (bound_preview.role, bound_preview.email_bound) == ("admin", True)
    assert _all_row_counts() == before
    for c in (code, bound):
        row = repos.invites.get_invite_by_code(c)
        assert (row["accepted_at"], row["revoked"]) == (None, False)
    assert get_role(joiner, cid) is None


@pytest.mark.parametrize(("stored", "granted"), [
    pytest.param("owner", "admin", id="owner"),
    pytest.param("foo", "member", id="foo"),
])
def test_preview_clamps_role(stored, granted, invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"], role=stored)
    preview = onboarding.preview_invite(
        user_id=invite_world["joiner"], user_email=JOINER_EMAIL, code=code, now=INVITE_NOW,
    )
    assert preview.role == granted
    assert repos.invites.get_invite_by_code(code)["role"] == stored   # the row is not repaired


def test_preview_expires_at_is_aware_utc(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"])
    with session_scope() as s:
        assert repos.invites.find_by_code(code, session=s).expires_at.tzinfo is None   # SQLite: naive

    preview = onboarding.preview_invite(
        user_id=invite_world["joiner"], user_email=JOINER_EMAIL, code=code, now=INVITE_NOW,
    )

    assert preview.expires_at.tzinfo is not None
    assert preview.expires_at.utcoffset() == timedelta(0)
    assert preview.expires_at == datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def test_preview_already_member_flag(invite_world):
    cid, owner, joiner = invite_world["church_id"], invite_world["owner"], invite_world["joiner"]
    code = _invite(cid, owner)

    def preview(user_id, email):
        return onboarding.preview_invite(user_id=user_id, user_email=email, code=code, now=INVITE_NOW)

    assert preview(joiner, JOINER_EMAIL).already_member is False
    assert preview(owner, "owner@example.com").already_member is True

    # Consumed by the joiner, who is a member: check 4's exception, previews normally.
    _update_invite(code, accepted_at=datetime(2026, 9, 30, 12, 0), accepted_by=joiner)
    add_membership(joiner, cid, "member")
    assert preview(joiner, JOINER_EMAIL).already_member is True

    # Removed from the church: the old link is "used", so a removal cannot be undone with it.
    remove_membership(joiner, cid)
    with pytest.raises(Rejected) as exc:
        preview(joiner, JOINER_EMAIL)
    assert exc.value.details == {"reason": "used"}
```

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_onboarding.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_usecase_onboarding.py 2>&1 | grep "^E " | head -1
```

**Expected:** `ERROR backend/tests/test_usecase_onboarding.py - AttributeError: module 'usec...`,
`!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!`, `1 error in …`; then
`E   AttributeError: module 'usecases.onboarding' has no attribute 'preview_invite'` (the module-level `INVITE_ACTIONS`
fails at collection, so Task 3's 12 tests are not collected either until Step 4).

- [ ] **Step 4 (agent): Add the invite checks and `preview_invite` to `backend/usecases/onboarding.py`**

Replace Task 3's import lines:

```python
from enum import StrEnum

from db import session_scope
from db.ids import as_uuid
from domain_errors import InvalidInput, RateLimited
from repos import churches, invites, memberships  # noqa: F401  (invites, memberships: Tasks 4-5)
from timezones import is_valid_timezone
```

with (the `noqa` goes: `invites` and `memberships` are used from here on):

```python
from enum import StrEnum
from typing import NoReturn

from db import session_scope
from db.ids import as_uuid
from domain_errors import InvalidInput, RateLimited, Rejected
from repos import churches, invites, memberships
from timezones import is_valid_timezone
```

Then append to the end of the file (two blank lines after `_enforce_create_cap`'s `raise RateLimited(...)` line):

```python
# --- Invites: the shared checks and the preview (S "Invite checks", "Preview semantics") ---

BLANK_CODE_MESSAGE = "Enter an invite code, or open your invite link again."

REJECT_MESSAGES: dict[InviteRejectReason, str] = {
    InviteRejectReason.unknown: "Invalid invite code.",
    InviteRejectReason.revoked: "This invite has been revoked.",
    InviteRejectReason.expired: "This invite has expired.",
    InviteRejectReason.used: "This invite has already been used.",
    InviteRejectReason.church_unavailable: "This church is no longer available.",
    InviteRejectReason.email_mismatch: "This invite was issued for a different email address.",
}

_GRANTABLE_ROLES = ("member", "admin")


def _strip_code(code: str) -> str:
    """Check 0: the code, stripped before lookup; blank is the 422 with fields.code."""
    stripped = (code or "").strip()
    if not stripped:
        raise InvalidInput(BLANK_CODE_MESSAGE, field="code")
    return stripped


def _load_invite(s, code: str, user_id: uuid.UUID) -> tuple:
    """The three reads preview and accept both start from (S accept_invite flow).

    Returns (inv, church, member_role): the Invite row or None; its church as
    repos.churches.get_church's dict, None when missing or soft-deleted; and
    the caller's role there, None when not a member.
    """
    inv = invites.find_by_code(code, session=s)
    church = churches.get_church(inv.church_id, session=s) if inv is not None else None
    member_role = (
        memberships.get_role(user_id, church["id"], session=s) if church is not None else None
    )
    return inv, church, member_role


def _clamp_role(role: str | None, *, invite_id) -> str:
    """The role an invite grants: member/admin as stored, owner -> admin (the
    F §6.2 repair), anything else -> member. A clamp logs one WARNING with the
    invite id (never the code), so the bad row can be found and fixed."""
    if role in _GRANTABLE_ROLES:
        return role
    granted = "admin" if role == "owner" else "member"
    logger.warning("invite_role_clamped invite_id=%s granted=%s", invite_id, granted)
    return granted


def _evaluate(inv, church: dict | None, user_id: uuid.UUID, user_email: str,
              member_role: str | None, now: datetime) -> InviteRejectReason | None:
    """Checks 1-6 of S "Invite checks", in that order; None when the invite is good.

    `church` is repos.churches.get_church's dict (None when missing or
    soft-deleted), `member_role` the caller's role in it (None when not a
    member), `user_email` CurrentUser.email, `now` an aware datetime.
    """
    if inv is None:
        return InviteRejectReason.unknown
    if inv.revoked:
        return InviteRejectReason.revoked
    if invites.as_utc(inv.expires_at) < now:  # naive (SQLite) == UTC
        return InviteRejectReason.expired
    if not inv.reusable and inv.accepted_at is not None:
        # Consumed: only the user who consumed it, while still a member, may
        # open it again (it then previews and accepts as already_member). A
        # removed member, another user, or a legacy stamp with accepted_by
        # NULL gets "used" (clarification 14).
        if not (inv.accepted_by == user_id and member_role is not None):
            return InviteRejectReason.used
    if church is None:
        return InviteRejectReason.church_unavailable
    if inv.email is not None and inv.email.strip().lower() != (user_email or "").strip().lower():
        return InviteRejectReason.email_mismatch
    return None


def _reject(reason: InviteRejectReason, invite_id) -> NoReturn:
    """Log one invite_rejected line (ids only: no code, no email) and raise the 400."""
    logger.info(
        "invite_rejected reason=%s invite_id=%s",
        reason.value, invite_id if invite_id is not None else "none",
    )
    raise Rejected(
        REJECT_MESSAGES[reason], code="invite_rejected", details={"reason": reason.value}
    )


def preview_invite(*, user_id: uuid.UUID, user_email: str, code: str,
                   now: datetime | None = None) -> InvitePreview:
    """What an invite offers the caller, without using it (S "Preview semantics").

    Read-only: one session_scope, no membership, no stamp. Runs checks 0-6
    and returns only the five InvitePreview fields, never the invite id, the
    code, the church id, the creator or the bound email (F §7.4).
    """
    user_id = as_uuid(user_id)
    code = _strip_code(code)
    now = now if now is not None else datetime.now(UTC)
    with session_scope() as s:
        inv, church, member_role = _load_invite(s, code, user_id)
        reason = _evaluate(inv, church, user_id, user_email, member_role, now)
        if reason is not None:
            _reject(reason, inv.id if inv is not None else None)
        return InvitePreview(
            church_name=church["name"],
            role=_clamp_role(inv.role, invite_id=inv.id),
            expires_at=invites.as_utc(inv.expires_at),
            email_bound=inv.email is not None,
            already_member=member_role is not None,
        )
```

- [ ] **Step 5 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_onboarding.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3
.venv/bin/python -m pytest --co -q backend/tests/test_usecase_onboarding.py 2>&1 | grep -c "\[preview\|test_order_\|test_clamp_role\|test_naive_expires\|test_preview_"
grep -n "logger\.\(info\|warning\)" backend/usecases/onboarding.py
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `33 passed` (Task 3's 12 + these 18 + the 3 in `test_no_streamlit_in_core.py`); `18` (the new test ids);
four lines: Task 3's `logger.info(` (`church_created`) and `logger.info("church_create_limited …`, then
`logger.warning("invite_role_clamped invite_id=%s granted=%s", invite_id, granted)` and `logger.info(` (`invite_rejected`),
none of them passing a code or an email; then `746 passed, 5 skipped` (728 + 18). Frontend unchanged (126 in 23 files).

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/usecases/onboarding.py backend/tests/test_usecase_onboarding.py
git commit -m "Onboarding: preview_invite and the shared invite checks (S Invite checks, Preview semantics; AC7)

usecases.onboarding gains the six invite rejection messages, check 0 (a
blank code is a 422 on fields.code), checks 1-6 in S's order (unknown,
revoked, expired with naive = UTC, used unless the caller consumed it and
is still a member, church unavailable, email mismatch case-insensitive),
the role clamp (owner -> admin, anything else -> member, WARNING with the
invite id) and the read-only preview_invite, which returns only the five
preview fields with expires_at in aware UTC. Rejections log
invite_rejected with the reason and invite id only, never the code or an
email. accept_invite (Task 5) reuses the same helpers.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 5: Accept usecase; remove `repos.invites.accept_invite`; port the accept tests (S Accept semantics; AC7, AC8, AC16; clarifications 2, 4, 14, 15, 40, 48)

`accept_invite` moves from the repo into the usecase, following S's pseudo-code with `get_church`'s dict keys (clarification 2). One `session_scope` runs the same lookups and checks 0–6 as Task 4's `preview_invite`, then takes one of two paths:

- **Existing member.** The role is never changed. Only an unaccepted, email-bound, single-use invite is stamped (parity with `repos/invites.py:107-108`), so a member who opens their own code-only link does not use it up.
- **New member.** A single-use invite is claimed first, with `claim`'s conditional UPDATE as the race guard. The membership is then inserted with `ON CONFLICT DO NOTHING`. If the claim writes nothing, the usecase refreshes the row (clarification 4). It rejects with `used` when another user holds the claim, and continues when the caller's own concurrent request holds it. If the insert is skipped, it reports `already_member: true`.

The usecase calls `invites.claim` and `memberships.ensure_membership` as module attributes (clarification 40), so two SQLite tests here can patch them to force both "claim lost" branches, and Task 8's barrier wrappers can do the same on Postgres.

The ported tests land first and pass against the new usecase. Only then are the old ones deleted and `repos.invites.accept_invite` removed (F §2.3.7, clarification 48):
- `test_invites_repo.py`: four accept-only tests go, and the accept halves of two mixed tests go.
- `streamlit_tests/test_onboarding.py`: the accept test goes.

`app.py:43,294` still import the removed function. That is expected: production Streamlit runs from `streamlit-frozen` (owner decision 3), no test or CI step imports `app.py`, and `test_ops_workflows.py:586-589` reads it only as text. **Do not edit `app.py`.**

Two commits: (1) the usecase and its tests; (2) the port deletions and the repo removal.

**Files:**
- Modify: `backend/usecases/onboarding.py` (append `accept_invite` after Task 4's `preview_invite`)
- Modify: `backend/repos/invites.py` (delete `accept_invite`, `:66-111` at `0295b37`, which Task 2 moves down but does not change; drop the now-unused `Tuple`, `Church`, `Membership`, `User` imports at `:3` and `:8`, which Task 2 leaves as they are)
- Modify: `streamlit_tests/test_onboarding.py` (delete `test_accept_captured_invite_joins_as_member`, `:30-39` at `0295b37`, ported here; Task 3 already removed the create test; Task 14 deletes the file)
- Test: `backend/tests/test_usecase_onboarding.py` (header imports gain `repos.memberships`, `create_church` and four `repos.invites` names; Task 4's `INVITE_ACTIONS` gains `"accept"`: +6 rejection cases and +1 blank-code case; append 13 accept tests)
- Test: `backend/tests/test_invites_repo.py` (delete `:24-75`, the four accept-only tests; rewrite `:76-104` without their accept halves; drop `accept_invite` from the import at `:10` and the now-unused `Church` and `get_role` imports at `:6` and `:8`; Task 2's appended tests are untouched)

**Interfaces:**
- Consumes:
  - Task 4, `backend/usecases/onboarding.py`:
    - `_strip_code(code: str) -> str`: check 0. It raises `InvalidInput(BLANK_CODE_MESSAGE, field="code")`, where `BLANK_CODE_MESSAGE = "Enter an invite code, or open your invite link again."`.
    - `_load_invite(s, code: str, user_id: uuid.UUID) -> tuple`: returns `(inv, church, member_role)`. `inv` is the `Invite` row or `None`. `church` is `repos.churches.get_church`'s dict `{"id","name","timezone","settings"}`, or `None` when the church is missing or soft-deleted. `member_role` is `str | None`. It reads through `invites.find_by_code`, `churches.get_church` and `memberships.get_role`, each with `session=s`.
    - `_evaluate(inv, church, user_id, user_email, member_role, now) -> InviteRejectReason | None`.
    - `_clamp_role(role: str | None, *, invite_id) -> str`: logs the WARNING `invite_role_clamped invite_id=… granted=…`.
    - `_reject(reason: InviteRejectReason, invite_id) -> NoReturn`: logs `invite_rejected reason=… invite_id=…|none` and raises `Rejected(REJECT_MESSAGES[reason], code="invite_rejected", details={"reason": reason.value})`.
  - Task 4, `backend/tests/test_usecase_onboarding.py`: `INVITE_ACTIONS: dict[str, Callable]`, which `test_invite_rejections(action, reason, …)` and `test_blank_code_is_invalid_input(action, …)` are parametrized over.
  - Task 3, `backend/usecases/onboarding.py`:
    - `ChurchSummary(id: uuid.UUID, name: str, role: str)` and `InviteAccepted(church: ChurchSummary, already_member: bool, message: str)`, both frozen.
    - `InviteRejectReason.used` and `logger = logging.getLogger(__name__)`.
    - The module imports `uuid`, `from datetime import UTC, datetime, …`, `from db import session_scope` and `from repos import churches, invites, memberships`.
  - Task 3, `backend/tests/test_usecase_onboarding.py`: the header imports `logging`, `from datetime import UTC, datetime, timedelta`, `pytest`, `from sqlalchemy import …, update`, `from db import session_scope` and `from usecases import onboarding`.
  - Task 2, the repos:
    - `repos.invites.claim(invite_id, user_id, now: datetime, *, session: Session | None = None) -> bool`: `rowcount == 1`, with `synchronize_session=False`.
    - `repos.memberships.ensure_membership(church_id, user_id, role: str, *, session: Session | None = None) -> tuple[str, bool]`.
    - `repos.invites.create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7, reusable: bool = False, session: Session | None = None) -> str`.
    - `repos.invites.as_utc(dt: datetime) -> datetime`.
    - `repos.invites.get_invite_by_code(code) -> dict | None`, whose keys now include `reusable` and `accepted_by`.
  - Existing:
    - `repos.churches.create_church(*, name, timezone, owner_user_id)` and `list_user_churches(user_id)`.
    - `repos.invites.list_invites(church_id)`.
    - `repos.memberships.add_membership(user_id, church_id, role)`, `get_role(user_id, church_id)` and `remove_membership(user_id, church_id)`.
    - Fixtures `tmp_db`, `make_user(email=…)`, `monkeypatch` and `caplog`.
- Produces:
  - `usecases.onboarding.accept_invite(*, user_id: uuid.UUID, user_email: str, code: str, now: datetime | None = None) -> InviteAccepted`:
    - Messages: "Joined {name}." with `already_member=False`; "You're already a member of {name}." with `already_member=True`.
    - `church.role` is the member's current role (existing member) or the clamped invite role (new member).
    - It raises `InvalidInput(field="code")` (check 0) or `Rejected(code="invite_rejected", details={"reason": …})` (checks 1–6, and `used` when the claim is lost to another user).
    - On success it logs one INFO line after the commit, `invite_accepted invite_id=<uuid> church_id=<uuid> user_id=<uuid> already_member=<True|False>`, which has no code and no email.
    - Later users: Task 7 (`POST /invites/accept`), Task 8 (Postgres races through the patched module attributes), Task 20 (AC16 grep gates).
  - `repos.invites` without `accept_invite`. The `grep -n "def accept_invite" backend/repos/invites.py` gate prints nothing from here on.

- [ ] **Step 1 (agent): Write the failing tests**

In `backend/tests/test_usecase_onboarding.py`, replace Task 4's two lines

```python
# Every action that runs the shared checks. T5 adds "accept": onboarding.accept_invite.
INVITE_ACTIONS = {"preview": onboarding.preview_invite}
```

with

```python
# Every action that runs the shared checks (S "Invite checks"): preview (Task 4), accept (Task 5).
INVITE_ACTIONS = {"preview": onboarding.preview_invite, "accept": onboarding.accept_invite}
```

This adds `test_invite_rejections[accept-unknown|accept-revoked|accept-expired|accept-used|accept-church_unavailable|accept-email_mismatch]` (6) and `test_blank_code_is_invalid_input[accept]` (1). Task 4's bodies apply unchanged: the exact message, `code == "invite_rejected"`, `details["reason"]`, `field is None`, exactly one `invite_rejected` log line with no code or email, and row counts unchanged (a rejected accept writes nothing). Three of these cases are the ported accept halves:
- `[accept-church_unavailable]` is `test_invites_repo.py:43`: Task 4's case soft-deletes the church directly and leaves the invite live.
- `[accept-expired]` is `:76`.
- `[accept-revoked]` is `:89`.

In the same file's header, replace Task 4's lines

```python
import repos.invites
from db import session_scope
from db.models import Church, Invite, Membership, User
from domain_errors import InvalidInput, RateLimited, Rejected
from repos.churches import get_church, list_user_churches, soft_delete_church
from repos.hymns import list_hymns
```

with (the header owns every import; the accept tests use these names):

```python
import repos.invites
import repos.memberships
from db import session_scope
from db.models import Church, Invite, Membership, User
from domain_errors import InvalidInput, RateLimited, Rejected
from repos.churches import create_church, get_church, list_user_churches, soft_delete_church
from repos.hymns import list_hymns
from repos.invites import as_utc, create_invite, get_invite_by_code, list_invites
```

Then append this block to the end of the same file, after Task 4's last test, with two blank lines before it:

```python
# --- Invites: accept (T5; S "Accept semantics"; AC7, AC8, AC9) ---
# Ported here, then deleted from their old files: test_invites_repo.py :24, :34, :43
# (now test_invite_rejections[accept-church_unavailable]), :57, and the accept halves
# of :76 ([accept-expired]) and :89 ([accept-revoked]); streamlit_tests/test_onboarding.py :30.


def _accept(user_id, email, code, **kwargs):
    return onboarding.accept_invite(user_id=user_id, user_email=email, code=code, **kwargs)


def _stamp(code):
    """(accepted_at as aware UTC or None, accepted_by) of the invite with this code."""
    row = get_invite_by_code(code)
    at = row["accepted_at"]
    return (as_utc(at) if at is not None else None), row["accepted_by"]


def _already(church_id, role, name="Grace"):
    return onboarding.InviteAccepted(
        onboarding.ChurchSummary(church_id, name, role), True,
        f"You're already a member of {name}.",
    )


def test_accept_adds_membership_with_invite_role(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="join@x.com")
    promoted = make_user(email="promoted@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    assert _accept(joiner, "join@x.com", f"  {code}  ") == onboarding.InviteAccepted(   # stripped
        onboarding.ChurchSummary(cid, "Grace", "member"), False, "Joined Grace.")
    assert get_role(joiner, cid) == "member"
    # The granted role is clamped: an invite stored as owner makes an admin, never an owner.
    owner_code = create_invite(church_id=cid, created_by=owner, role="owner")
    assert _accept(promoted, "promoted@x.com", owner_code).church.role == "admin"
    assert get_role(promoted, cid) == "admin"


def test_existing_owner_keeps_role(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    assert _accept(owner, "o@x.com", code) == _already(cid, "owner")
    assert get_role(owner, cid) == "owner"                             # never downgraded


def test_single_use_code_only_lifecycle(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    first = make_user(email="first@x.com")
    second = make_user(email="second@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)              # reusable=False
    now = datetime.now(UTC)

    assert _accept(first, "first@x.com", code, now=now).message == "Joined Grace."
    assert _stamp(code) == (now, first)

    with pytest.raises(Rejected) as rejected:                          # another user
        _accept(second, "second@x.com", code)
    assert rejected.value.details == {"reason": "used"}
    assert get_role(second, cid) is None

    assert _accept(first, "first@x.com", code) == _already(cid, "member")   # same user again
    assert _stamp(code) == (now, first)                                # stamped once

    remove_membership(first, cid)                                      # removed member
    with pytest.raises(Rejected) as rejected:
        _accept(first, "first@x.com", code)
    assert rejected.value.details == {"reason": "used"}
    assert get_role(first, cid) is None


def test_reusable_admits_three_users_never_stamped(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, reusable=True)
    for email in ("a@x.com", "b@x.com", "c@x.com"):
        user = make_user(email=email)
        result = _accept(user, email, code)
        assert (result.already_member, result.message, result.church.role) == (
            False, "Joined Grace.", "member")
        assert get_role(user, cid) == "member"
    assert _stamp(code) == (None, None)
    assert [i["code"] for i in list_invites(cid)] == [code]            # still listed


def test_existing_member_does_not_consume_code_only_single_use(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    admin = make_user(email="admin@x.com")
    newcomer = make_user(email="new@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    code = create_invite(church_id=cid, created_by=admin)             # single-use, code only
    assert _accept(admin, "admin@x.com", code) == _already(cid, "admin")  # testing own link
    assert _stamp(code) == (None, None)
    assert _accept(newcomer, "new@x.com", code).message == "Joined Grace."   # still usable


def test_existing_member_stamps_unaccepted_email_bound(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    member = make_user(email="m@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    add_membership(member, cid, "member")
    code = create_invite(church_id=cid, created_by=owner, email="M@x.com", role="admin")
    now = datetime.now(UTC)
    assert _accept(member, "m@x.com", code, now=now) == _already(cid, "member")
    assert _stamp(code) == (now, member)                               # parity stamp
    assert get_role(member, cid) == "member"                           # role never changed


def test_email_bound_case_insensitive_role_honored(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    wrong = make_user(email="wrong@x.com")
    right = make_user(email="right@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, email="Right@X.com", role="admin")

    with pytest.raises(Rejected) as rejected:                          # mismatched email
        _accept(wrong, "wrong@x.com", code)
    assert rejected.value.details == {"reason": "email_mismatch"}
    assert get_role(wrong, cid) is None

    result = _accept(right, "right@x.com", code)                       # case-insensitive match
    assert (result.already_member, result.message, result.church.role) == (
        False, "Joined C.", "admin")                                   # role honored
    assert get_role(right, cid) == "admin"

    # Clarification 15 (behavior change 6): the same user accepting again is no longer
    # "used"; "removed member -> used" (test_single_use_code_only_lifecycle) keeps the intent.
    assert _accept(right, "right@x.com", code) == _already(cid, "admin", name="C")


def test_legacy_accepted_email_bound_is_used(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    member = make_user(email="m@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, email="m@x.com")
    # Frozen Streamlit stamps only accepted_at (accepted_by stays NULL) and adds the member.
    with session_scope() as s:
        s.execute(update(Invite).where(Invite.code == code)
                  .values(accepted_at=datetime.now(UTC) - timedelta(hours=1)))
    add_membership(member, cid, "member")
    with pytest.raises(Rejected) as rejected:
        _accept(member, "m@x.com", code)
    assert rejected.value.details == {"reason": "used"}               # clarification 14


def test_accept_reports_already_member_when_insert_skipped(tmp_db, make_user, monkeypatch):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, reusable=True)
    # A concurrent request by the same user inserted the membership first.
    monkeypatch.setattr(repos.memberships, "ensure_membership",
                        lambda church_id, user_id, role, *, session=None: (role, False))
    assert _accept(joiner, "j@x.com", code) == _already(cid, "member")


def test_claim_lost_to_another_user_is_used(tmp_db, make_user, monkeypatch):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    rival = make_user(email="rival@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    real_claim = repos.invites.claim

    def rival_won(invite_id, user_id, now, *, session=None):
        assert real_claim(invite_id, rival, now, session=session)     # the rival's request won
        return False

    monkeypatch.setattr(repos.invites, "claim", rival_won)
    with pytest.raises(Rejected) as rejected:
        _accept(joiner, "j@x.com", code)
    assert rejected.value.message == "This invite has already been used."
    assert rejected.value.details == {"reason": "used"}
    assert get_role(joiner, cid) is None


def test_claim_lost_to_own_request_reports_already_member(tmp_db, make_user, monkeypatch):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    real_claim = repos.invites.claim
    real_ensure = repos.memberships.ensure_membership

    def own_request_won(invite_id, user_id, now, *, session=None):
        # The caller's own concurrent request stamped the invite and joined first.
        assert real_claim(invite_id, user_id, now, session=session)
        real_ensure(cid, user_id, "member", session=session)
        return False

    monkeypatch.setattr(repos.invites, "claim", own_request_won)
    assert _accept(joiner, "j@x.com", code) == _already(cid, "member")
    assert get_role(joiner, cid) == "member"
    assert _stamp(code)[1] == joiner


def test_accept_captured_invite_joins_as_member(tmp_db, make_user):
    # Port of streamlit_tests/test_onboarding.py::test_accept_captured_invite_joins_as_member.
    owner = make_user(email="owner@a.org")
    cid = create_church(name="Grace", timezone="America/New_York", owner_user_id=owner)
    joiner = make_user(email="joiner@a.org")
    code = create_invite(church_id=cid, created_by=owner)
    assert _accept(joiner, "joiner@a.org", code).already_member is False
    assert any(c["id"] == cid and c["role"] == "member" for c in list_user_churches(joiner))


def test_invite_logs_have_ids_not_code_or_email(tmp_db, make_user, caplog):
    caplog.set_level(logging.INFO, logger="usecases.onboarding")
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, email="j@x.com")
    invite_id = get_invite_by_code(code)["id"]

    onboarding.preview_invite(user_id=joiner, user_email="j@x.com", code=code)
    _accept(joiner, "j@x.com", code)
    with pytest.raises(Rejected):
        _accept(joiner, "j@x.com", "not-a-real-code")

    assert caplog.messages == [
        f"invite_accepted invite_id={invite_id} church_id={cid} user_id={joiner} already_member=False",
        "invite_rejected reason=unknown invite_id=none",
    ]
    for secret in (code, "not-a-real-code", "j@x.com", "o@x.com"):
        assert secret not in caplog.text
```

- [ ] **Step 2 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_onboarding.py 2>&1 | tail -3
```

**Expected:** a collection error, because `INVITE_ACTIONS` is built at import time:

```
ERROR backend/tests/test_usecase_onboarding.py - AttributeError: module 'usec...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in …
```

(`AttributeError: module 'usecases.onboarding' has no attribute 'accept_invite'` in full.)

- [ ] **Step 3 (agent): Implement `accept_invite`**

Append to the end of `backend/usecases/onboarding.py`, after Task 4's `preview_invite`, with two blank lines before it:

```python
# --- Invites: accept (S "Accept semantics") ---


def accept_invite(*, user_id: uuid.UUID, user_email: str, code: str,
                  now: datetime | None = None) -> InviteAccepted:
    """Join the invite's church, or confirm the caller is already in it (S "Accept semantics").

    One session_scope; checks 0-6 exactly as preview_invite. An existing member
    keeps their role, and only an unaccepted email-bound single-use invite is
    stamped for them (parity with the removed repos.invites function), so a
    member opening their own code-only link never burns it. A new member claims
    a single-use invite first (the conditional UPDATE is the race guard), then
    gets the clamped role through ON CONFLICT DO NOTHING: a lost claim is "used"
    unless the caller's own concurrent request won it, and a skipped insert
    reports already_member. invites.claim and memberships.ensure_membership are
    called through their modules so tests can patch them (clarification 40).
    """
    user_id = as_uuid(user_id)
    code = _strip_code(code)
    now = now if now is not None else datetime.now(UTC)
    with session_scope() as s:
        inv, church, member_role = _load_invite(s, code, user_id)
        reason = _evaluate(inv, church, user_id, user_email, member_role, now)
        if reason is not None:
            _reject(reason, inv.id if inv is not None else None)
        invite_id = inv.id
        if member_role is not None:
            if inv.email is not None and not inv.reusable and inv.accepted_at is None:
                invites.claim(inv.id, user_id, now, session=s)   # parity stamp, role unchanged
            role, already_member = member_role, True
        else:
            if not inv.reusable and not invites.claim(inv.id, user_id, now, session=s):
                s.refresh(inv)   # claim wrote nothing: who holds the invite now?
                if inv.accepted_by != user_id:
                    _reject(InviteRejectReason.used, inv.id)
            role, inserted = memberships.ensure_membership(
                church["id"], user_id, _clamp_role(inv.role, invite_id=inv.id), session=s
            )
            already_member = not inserted
    logger.info(
        "invite_accepted invite_id=%s church_id=%s user_id=%s already_member=%s",
        invite_id, church["id"], user_id, already_member,
    )
    name = church["name"]
    message = f"You're already a member of {name}." if already_member else f"Joined {name}."
    return InviteAccepted(
        church=ChurchSummary(id=church["id"], name=name, role=role),
        already_member=already_member,
        message=message,
    )
```

Nothing else in the module changes. Task 3's `from repos import churches, invites, memberships` and Task 4's helpers already provide every name used here.

- [ ] **Step 4 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_onboarding.py 2>&1 | tail -3
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `50 passed` (Task 3's 12, Task 4's 18 and this task's 20), then `766 passed, 5 skipped` (746 + 20). The old accept tests still pass at this point, because `repos.invites.accept_invite` still exists.

- [ ] **Step 5 (agent): Commit the usecase**

```bash
git add backend/usecases/onboarding.py backend/tests/test_usecase_onboarding.py
git commit -m "Onboarding: accept_invite usecase with claim guard and ported accept tests (S Accept semantics; AC7, AC8)

One transaction runs the preview's checks 0-6. An existing member keeps
their role; only an unaccepted email-bound single-use invite is stamped
for them. A new member claims a single-use invite first, then joins
through ON CONFLICT DO NOTHING. A lost claim is used unless the caller's
own concurrent request won it; a skipped insert reports already_member.
The repos are called through their modules (clarification 40), so two
SQLite tests force both claim-lost branches. Logs invite_accepted with
ids only.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6 (agent): Delete the ported repo and Streamlit tests**

In `backend/tests/test_invites_repo.py`, make four edits. Task 2 added `import pytest`, one more `from repos.invites import …` line after the block below, and tests at the end of the file. It did not change any of the lines replaced here.

1. Replace `from db.models import Invite, Church` with `from db.models import Invite`.
2. Delete the line `from repos.memberships import get_role`.
3. Replace `    create_invite, get_invite_by_code, accept_invite, list_invites, revoke_invite,` with `    create_invite, get_invite_by_code, list_invites, revoke_invite,`.
4. Replace this block (`:24-104` at `0295b37`: the four accept-only tests and the two mixed tests):

```python
def test_accept_invite_adds_membership(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="join@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    ok, msg = accept_invite(code, joiner)
    assert ok is True and "Grace" in msg
    assert get_role(joiner, cid) == "member"


def test_accept_invite_already_member_is_noop(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="Grace", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    ok, msg = accept_invite(code, owner)          # already the owner
    assert ok is True
    assert get_role(owner, cid) == "owner"        # role not downgraded to member


def test_accept_invite_rejects_soft_deleted_church(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="Gone", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    # soft-delete the church directly, leaving the invite live, to hit the
    # church-availability branch specifically.
    with session_scope() as s:
        s.get(Church, cid).deleted_at = datetime.now(timezone.utc)
    ok, msg = accept_invite(code, joiner)
    assert ok is False
    assert get_role(joiner, cid) is None


def test_email_bound_invite_matches_email_and_is_single_use(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    wrong = make_user(email="wrong@x.com")
    right = make_user(email="right@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner, email="Right@X.com", role="admin")

    ok, _ = accept_invite(code, wrong)            # mismatched email
    assert ok is False
    assert get_role(wrong, cid) is None

    ok, _ = accept_invite(code, right)            # case-insensitive match; role honored
    assert ok is True
    assert get_role(right, cid) == "admin"

    ok2, msg2 = accept_invite(code, right)        # single-use consumed
    assert ok2 is False and "used" in msg2.lower()


def test_expired_invite_rejected_and_excluded_from_active(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
        inv.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    ok, msg = accept_invite(code, joiner)
    assert ok is False and "expired" in msg.lower()
    assert list_invites(cid) == []


def test_revoke_invite_blocks_accept_and_is_church_scoped(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    other_owner = make_user(email="oo@x.com")
    joiner = make_user(email="j@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other_cid = create_church(name="D", timezone="UTC", owner_user_id=other_owner)
    code = create_invite(church_id=cid, created_by=owner)
    inv = get_invite_by_code(code)

    revoke_invite(inv["id"], other_cid)           # wrong church -> no-op (IDOR-safe)
    assert [i["code"] for i in list_invites(cid)] == [code]

    revoke_invite(inv["id"], cid)                 # correct church
    assert list_invites(cid) == []
    ok, _ = accept_invite(code, joiner)
    assert ok is False
```

with:

```python
def test_expired_invite_excluded_from_active(tmp_db, make_user):
    # The accept half is test_usecase_onboarding.py::test_invite_rejections[accept-expired].
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
        inv.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    assert list_invites(cid) == []


def test_revoke_invite_is_church_scoped(tmp_db, make_user):
    # The accept half is test_usecase_onboarding.py::test_invite_rejections[accept-revoked].
    owner = make_user(email="o@x.com")
    other_owner = make_user(email="oo@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other_cid = create_church(name="D", timezone="UTC", owner_user_id=other_owner)
    code = create_invite(church_id=cid, created_by=owner)
    inv = get_invite_by_code(code)

    revoke_invite(inv["id"], other_cid)           # wrong church -> no-op (IDOR-safe)
    assert [i["code"] for i in list_invites(cid)] == [code]

    revoke_invite(inv["id"], cid)                 # correct church
    assert list_invites(cid) == []
    assert get_invite_by_code(code)["revoked"] is True
```

Where each deleted assertion now lives:

| Old test | Ported to |
|---|---|
| `test_accept_invite_adds_membership` (`:24`) | `test_accept_adds_membership_with_invite_role` |
| `test_accept_invite_already_member_is_noop` (`:34`) | `test_existing_owner_keeps_role` |
| `test_accept_invite_rejects_soft_deleted_church` (`:43`) | `test_invite_rejections[accept-church_unavailable]` |
| `test_email_bound_invite_matches_email_and_is_single_use` (`:57`) | `test_email_bound_case_insensitive_role_honored` (its last assertion is now `already_member`, clarification 15) |
| The accept half of `:76` | `[accept-expired]` |
| The accept half of `:89` | `[accept-revoked]` |

In `streamlit_tests/test_onboarding.py` (after Task 3), replace:

```python
    assert pick_invite_code("  ", "  ") == ""


def test_accept_captured_invite_joins_as_member(tmp_db, make_user):
    from repos.churches import create_church, list_user_churches
    from repos.invites import create_invite, accept_invite
    owner = make_user(email="owner@a.org")
    cid = create_church(name="Grace", timezone="America/New_York", owner_user_id=owner)
    joiner = make_user(email="joiner@a.org")
    code = create_invite(church_id=cid, created_by=owner)
    ok, _msg = accept_invite(code, joiner)
    assert ok is True
    assert any(c["id"] == cid and c["role"] == "member" for c in list_user_churches(joiner))
```

with:

```python
    assert pick_invite_code("  ", "  ") == ""
```

The file keeps its three `pick_invite_code` tests, which Task 14 ports and then deletes along with the file.

- [ ] **Step 7 (agent): Remove `repos.invites.accept_invite`**

```bash
grep -n "def accept_invite" backend/repos/invites.py
```

**Expected:** one line, `…:def accept_invite(code, user_id) -> Tuple[bool, str]:`. The line number is below Task 2's `claim`.

In `backend/repos/invites.py`, replace this block (the function, the two blank lines after it, and the next `def` as an anchor):

```python
def accept_invite(code, user_id) -> Tuple[bool, str]:
    """Accept an invite for user_id. Returns (ok, message). No enumerable
    difference between distinct failure causes beyond the message text.

    Rejects: unknown/revoked/expired codes; a soft-deleted church; email-bound
    codes whose email does not match the accepting user, or that were already
    used (single-use). Accepting when already a member is a no-op success.
    """
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        inv = session.execute(
            select(Invite).where(Invite.code == code)
        ).scalar_one_or_none()
        if inv is None:
            return (False, "Invalid invite code.")
        if inv.revoked:
            return (False, "This invite has been revoked.")
        if inv.expires_at is not None and _as_utc(inv.expires_at) < now:
            return (False, "This invite has expired.")

        email_bound = inv.email is not None
        if email_bound and inv.accepted_at is not None:
            return (False, "This invite has already been used.")

        church = session.get(Church, inv.church_id)
        if church is None or church.deleted_at is not None:
            return (False, "This church is no longer available.")

        if email_bound:
            user = session.get(User, user_id)
            user_email = user.email if user is not None else None
            if user_email is None or user_email.strip().lower() != inv.email:
                return (False, "This invite was issued for a different email address.")

        existing = session.get(
            Membership, {"church_id": inv.church_id, "user_id": user_id}
        )
        if existing is None:
            session.add(Membership(
                church_id=inv.church_id, user_id=user_id, role=inv.role
            ))
        if email_bound:
            inv.accepted_at = now  # single-use for email-bound invites
        return (True, f"Joined {church.name}.")


def list_invites(church_id) -> list:
```

with:

```python
def list_invites(church_id) -> list:
```

Then fix the imports that only the removed function used:
1. Replace `from typing import Optional, Tuple` with `from typing import Optional`.
2. Replace `from db.models import Invite, Church, Membership, User` with `from db.models import Invite`.

- [ ] **Step 8 (agent): Run the touched files, the suite and the AC16 gates**

```bash
.venv/bin/python -m pytest -q backend/tests/test_invites_repo.py backend/tests/test_usecase_onboarding.py streamlit_tests/test_onboarding.py 2>&1 | tail -3
.venv/bin/python -m pytest -q | tail -1
grep -n "def accept_invite" backend/repos/invites.py
grep -rnwI --include='*.py' accept_invite backend streamlit_tests streamlit_views | grep -v 'usecases/onboarding.py\|api/routes/invites.py\|onboarding\.accept_invite\|from usecases.onboarding import'
grep -n "^from typing\|^from db.models" backend/repos/invites.py
git diff --quiet origin/main -- app.py && echo "app.py untouched"
```

**Expected:**
- `61 passed`: `test_invites_repo.py` 8 (7 − 4 + Task 2's 5), `test_usecase_onboarding.py` 50, `test_onboarding.py` 3.
- Then `761 passed, 5 skipped` (766 − 4 − 1).
- The two `grep` gates print nothing.
- Then the two import lines `from typing import Optional` and `from db.models import Invite`.
- Then `app.py untouched`.

If the second `grep` prints a line, a comment or import still names the old function; reword or remove it (Task 20 runs the same gate).

- [ ] **Step 9 (agent): Commit the removal**

```bash
git add backend/repos/invites.py backend/tests/test_invites_repo.py streamlit_tests/test_onboarding.py
git commit -m "Invites: remove repos.invites.accept_invite after porting its tests (S Streamlit coupling removed; AC16; clarification 48)

The accept logic lives in usecases.onboarding.accept_invite. Its four
accept-only repo tests, the accept halves of the expired and revoke tests,
and Streamlit's accept test were ported there in the previous commit and
are deleted here. The expired and revoke tests keep their list and IDOR
halves under names without \"accept\". app.py is untouched: production
Streamlit runs from streamlit-frozen (owner decision 3) and nothing
imports app.py.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Counts after Task 5: backend **761 passed, 5 skipped** (746 + 20 − 5); frontend unchanged (**126 passed in 23 files**).
### Task 6: `POST /churches` with Idempotency-Key (F §1.6, F-AC7; S API, Idempotency; AC6; clarifications 9, 10, 12)

`POST /churches` is the first real route on 1a's `run_idempotent`. The route parses the body, resolves the user, reads the optional key and calls one usecase (Task 3's `onboarding.create_church`) **inside** `call`, so a replay returns the first response and the cap's 429 is never stored (a same-key retry runs again). It is user-scoped: `get_current_user` and never `require_church`, so `X-Church-Id` is ignored. `get_current_user` is declared before `idempotency_key()`, so a request with no token and a malformed key is 401, not 422 (clarification 10). Four things change in the same commit because tests couple them (clarification 9): the route module, its mount in `api/main.py`, `USER_SCOPED` in `test_route_guards.py`, and the regenerated `openapi.json` + `schema.d.ts` (`test_openapi_contract.py`; CI's `gen:api` diff). The route returns 201, so `test_routes_document_the_error_body` subtracts `{"200", "201"}` instead of `{"200"}`, and the route lists 422 in `error_responses` so FastAPI adds no `HTTPValidationError`. The frontend only gets the regenerated schema; no frontend source or test changes (typecheck stays green). Slice 2 adds the `church_create` burst bucket as one more dependency and must keep `test_cap_429_not_replayed` green unchanged.

The usecase's own rules (trimming, the three messages, the seed, the cap arithmetic, the log lines) are pinned in Task 3's `test_usecase_onboarding.py`; these HTTP tests pin statuses, the error body, the dependency order, X-Church-Id and the key behavior.

**Files:**
- Create: `backend/api/routes/churches.py`
- Create: `backend/tests/test_api_churches.py` (14 tests)
- Modify: `backend/api/schemas.py:1` (module docstring), `:5` (pydantic import), end of file (`CreateChurchIn` after `RubricOut`)
- Modify: `backend/api/main.py:12` (routes import), `:59` (mount after `rubric`)
- Modify: `backend/tests/test_route_guards.py:37-39` (`USER_SCOPED`)
- Modify: `backend/tests/test_api_app.py:270-278` (`test_routes_document_the_error_body`: one expected row, success-status subtraction)
- Modify: `backend/tests/test_no_streamlit_in_core.py:54` (one assert line added after it)
- Modify (generated, never by hand): `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`

**Interfaces:**
- Consumes:
  - `api.deps.get_current_user` → `CurrentUser(id: uuid.UUID, email: str, name, picture)` (email already stripped and lower-cased).
  - `api.idempotency.idempotency_key(required: bool = False)` (dependency factory; absent → `None`; malformed → `InvalidInput("Idempotency-Key must be a UUID.")`, no `fields`).
  - `api.idempotency.run_idempotent(*, user_id: uuid.UUID, route: str, key: uuid.UUID | None, payload: BaseModel, status_code: int, call: Callable[[], BaseModel], method: str = "POST", store=None) -> Response` (stores 2xx and `DomainError` 4xx except `RateLimited`; replay header `Idempotent-Replayed: true`; mismatch → 422 `idempotency_mismatch`).
  - `api.errors.error_responses(*statuses)`; `api.schemas.ChurchOut {id: uuid.UUID, name: str, role: Literal["owner","admin","member"]}`.
  - Task 3: `usecases.onboarding.create_church(*, user_id: uuid.UUID, name: str, timezone: str, now: datetime | None = None) -> ChurchSummary` with `@dataclass(frozen=True) ChurchSummary(id: uuid.UUID, name: str, role: str)`; raises `InvalidInput("Church name is required.", field="name")`, `InvalidInput("Timezone is required.", field="timezone")`, `InvalidInput("Unknown timezone.", field="timezone")`, `RateLimited("You've created 5 churches in the last 24 hours. Try again later.", retry_after_seconds=n)`.
  - Task 2: `repos.churches.create_church(*, name, timezone, owner_user_id, session=None) -> uuid.UUID` (seeds the five cap churches without HTTP).
  - Task 1: autouse `_fresh_idempotency_store` (clears `api.idempotency.store` before each test).
  - Test helpers: `tests.api_helpers.make_api_client()`, `auth_headers(email)`, `church_headers(email, church_id)`; fixtures `tmp_db`, `make_user(email=…)`, `make_church(name=…, owner_user_id=…)`, `seed_catalog(n)`; `repos.memberships.add_membership(user_id, church_id, role)`.
- Produces:
  - `api.schemas.CreateChurchIn(BaseModel)`: `model_config = ConfigDict(extra="forbid")`; `name: str = Field("", max_length=200)`; `timezone: str = Field("", max_length=64)`. OpenAPI component `CreateChurchIn` (`additionalProperties: false`). Later users: Task 13 (`CreateChurchBody` from `components["schemas"]["CreateChurchIn"]`), Task 16.
  - `api.routes.churches.router` (`APIRouter`) with `def create_church(payload: CreateChurchIn, user: CurrentUser = Depends(get_current_user), key: uuid.UUID | None = Depends(idempotency_key())) -> Response`, decorated `@router.post("/churches", status_code=201, response_model=ChurchOut, responses=error_responses(401, 422, 429, 503))`, returning `run_idempotent(user_id=user.id, route="/churches", key=key, payload=payload, status_code=201, call=lambda: ChurchOut(**asdict(onboarding.create_church(user_id=user.id, name=payload.name, timezone=payload.timezone))))`. OpenAPI operation id `create_church_churches_post`; header parameter `Idempotency-Key` (`required: false`). Later users: Task 8 (Postgres seed timing through HTTP), Task 13 (`useCreateChurch`), slice 2 (one more dependency).
  - `USER_SCOPED` gains `("POST", "/churches")`; `test_routes_document_the_error_body` expects `("/churches", "post"): {"401", "422", "429", "503"}` and subtracts `{"200", "201"}` (Task 7 adds its two rows to the same dict).

- [ ] **Step 1 (agent): Write the failing HTTP tests**

Create `backend/tests/test_api_churches.py`:

```python
"""POST /churches over HTTP (S API, Idempotency, Testing; AC6; F-AC7).

The usecase's own rules (trimming, the seed, the cap's arithmetic, the log
lines) are pinned in test_usecase_onboarding.py. These tests pin the HTTP
contract: statuses, the error body, X-Church-Id ignored, the dependency
order, and Idempotency-Key replay through run_idempotent.
"""
import uuid

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Church, Hymn, Membership
from repos.churches import create_church as repo_create_church
from repos.memberships import add_membership
from tests.api_helpers import auth_headers, church_headers, make_api_client

EMAIL = "pastor@example.com"
BODY = {"name": "Grace Church", "timezone": "America/Chicago"}
CAP_MESSAGE = "You've created 5 churches in the last 24 hours. Try again later."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def _count(model) -> int:
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(model)).scalar_one()


def _key_headers(key: uuid.UUID, email: str = EMAIL) -> dict[str, str]:
    return {**auth_headers(email), "Idempotency-Key": str(key)}


def _my_churches(client, email: str = EMAIL) -> list[dict]:
    r = client.get("/me", headers=auth_headers(email))
    assert r.status_code == 200, r.text
    return r.json()["churches"]


def test_requires_token(client):
    r = client.post("/churches", json=BODY)
    assert r.status_code == 401
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("unauthenticated", "Please sign in.")
    assert _count(Church) == 0


def test_bad_key_without_token_is_401(client):
    """get_current_user runs before idempotency_key() (clarification 10)."""
    r = client.post("/churches", json=BODY, headers={"Idempotency-Key": "not-a-uuid"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"

    signed_in = client.post("/churches", json=BODY,
                            headers={**auth_headers(EMAIL), "Idempotency-Key": "not-a-uuid"})
    assert signed_in.status_code == 422
    error = signed_in.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", "Idempotency-Key must be a UUID.")
    assert "fields" not in error
    assert _count(Church) == 0


def test_create_201_listed_in_me_and_usable(client, seed_catalog):
    seed_catalog(3)
    r = client.post("/churches", json={"name": "  Grace Church  ", "timezone": "America/Chicago"},
                    headers=auth_headers(EMAIL))
    assert r.status_code == 201, r.text
    body = r.json()
    assert set(body) == {"id", "name", "role"}
    assert (body["name"], body["role"]) == ("Grace Church", "owner")
    church_id = uuid.UUID(body["id"])

    assert _my_churches(client) == [body]
    usable = client.get("/church", headers=church_headers(EMAIL, church_id))
    assert usable.status_code == 200, usable.text
    assert usable.json() == body
    with session_scope() as s:
        assert s.get(Church, church_id).timezone == "America/Chicago"
        hymns = s.execute(select(func.count()).select_from(Hymn)
                          .where(Hymn.church_id == church_id)).scalar_one()
    assert hymns == 3                                   # one hymn per catalog row (AC6)
    assert (_count(Church), _count(Membership)) == (1, 1)


def test_x_church_id_is_ignored(client, make_user, make_church):
    other = make_church(name="Other Church", owner_user_id=make_user(email="other@example.com"))
    for headers in (church_headers(EMAIL, other), {**auth_headers(EMAIL), "X-Church-Id": "not-a-uuid"}):
        r = client.post("/churches", json=BODY, headers=headers)
        assert r.status_code == 201, r.text
        assert r.json()["role"] == "owner"
    mine = _my_churches(client)
    assert [(c["name"], c["role"]) for c in mine] == [("Grace Church", "owner")] * 2
    assert str(other) not in {c["id"] for c in mine}


def test_duplicate_names_and_second_church_allowed(client, make_user, make_church):
    """Names need not be unique, and a member of one church can create another."""
    member = make_user(email=EMAIL)
    old_first = make_church(name="Old First", owner_user_id=make_user(email="owner@example.com"))
    add_membership(member, old_first, "member")

    mine = client.post("/churches", json=BODY, headers=auth_headers(EMAIL))
    again = client.post("/churches", json=BODY, headers=auth_headers(EMAIL))
    theirs = client.post("/churches", json=BODY, headers=auth_headers("friend@example.com"))
    assert (mine.status_code, again.status_code, theirs.status_code) == (201, 201, 201)
    assert len({mine.json()["id"], again.json()["id"], theirs.json()["id"]}) == 3
    assert [(c["name"], c["role"]) for c in _my_churches(client)] == [
        ("Grace Church", "owner"), ("Grace Church", "owner"), ("Old First", "member")]


@pytest.mark.parametrize("body, message, field", [
    ({"name": "   ", "timezone": "America/Chicago"}, "Church name is required.", "name"),
    ({"name": "Grace Church", "timezone": " "}, "Timezone is required.", "timezone"),
    ({"name": "Grace Church", "timezone": "Mars/Olympus"}, "Unknown timezone.", "timezone"),
], ids=["name", "tz-blank", "tz-unknown"])
def test_validation_messages(client, body, message, field):
    r = client.post("/churches", json=body, headers=auth_headers(EMAIL))
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", message)
    assert error["fields"] == {field: message}
    assert _count(Church) == 0


def test_name_too_long(client):
    r = client.post("/churches", json={"name": "x" * 201, "timezone": "America/Chicago"},
                    headers=auth_headers(EMAIL))
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid.")
    assert error["fields"] == {"name": "Too long (max 200 characters)."}

    zone = client.post("/churches", json={"name": "Grace Church", "timezone": "x" * 65},
                       headers=auth_headers(EMAIL))
    assert zone.status_code == 422
    assert zone.json()["error"]["fields"] == {"timezone": "Too long (max 64 characters)."}
    assert _count(Church) == 0

    at_limit = client.post("/churches", json={"name": "x" * 200, "timezone": "America/Chicago"},
                           headers=auth_headers(EMAIL))
    assert at_limit.status_code == 201, at_limit.text


def test_extra_field_rejected(client):
    r = client.post("/churches", json={**BODY, "owner_user_id": str(uuid.uuid4())},
                    headers=auth_headers(EMAIL))
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid.")
    assert error["fields"] == {"owner_user_id": "Not a valid value."}
    assert _count(Church) == 0


def test_key_replay_one_church_same_body(client):
    """F-AC7: a replay returns the first response and creates one church."""
    key = uuid.uuid4()
    first = client.post("/churches", json=BODY, headers=_key_headers(key))
    again = client.post("/churches", json=BODY, headers=_key_headers(key))
    assert (first.status_code, again.status_code) == (201, 201)
    assert "Idempotent-Replayed" not in first.headers
    assert again.headers["Idempotent-Replayed"] == "true"
    assert again.content == first.content
    assert _count(Church) == 1
    assert _my_churches(client) == [first.json()]


def test_key_mismatch_422(client):
    key = uuid.uuid4()
    assert client.post("/churches", json=BODY, headers=_key_headers(key)).status_code == 201
    r = client.post("/churches", json={**BODY, "name": "Hope Church"}, headers=_key_headers(key))
    assert r.status_code == 422
    error = r.json()["error"]
    assert (error["code"], error["message"]) == (
        "idempotency_mismatch", "This request was already sent with different details.")
    assert "fields" not in error
    assert _count(Church) == 1


def test_blank_then_corrected_with_new_key_201(client):
    """The client's flow (S Idempotency): a 4xx is stored under its key, so the
    corrected body goes out under a new key."""
    blank = {**BODY, "name": ""}
    first_key = uuid.uuid4()
    r = client.post("/churches", json=blank, headers=_key_headers(first_key))
    assert r.status_code == 422
    assert r.json()["error"]["fields"] == {"name": "Church name is required."}
    replay = client.post("/churches", json=blank, headers=_key_headers(first_key))
    assert (replay.status_code, replay.headers.get("Idempotent-Replayed")) == (422, "true")
    stale = client.post("/churches", json=BODY, headers=_key_headers(first_key))
    assert stale.json()["error"]["code"] == "idempotency_mismatch"
    assert _count(Church) == 0

    fixed = client.post("/churches", json=BODY, headers=_key_headers(uuid.uuid4()))
    assert fixed.status_code == 201, fixed.text
    assert fixed.json()["name"] == "Grace Church"
    assert _count(Church) == 1


def test_cap_429_not_replayed(client, make_user):
    """AC6: with five churches this user created in the last 24 h, the sixth is 429.

    The five are made through repos.churches.create_church, not HTTP, so slice 2's
    church_create burst bucket (3 per minute) is never reached: slice 2 keeps
    this test green unchanged. run_idempotent never stores a RateLimited, so the
    same key runs again (429 again, not a replay).
    """
    user_id = make_user(email=EMAIL)
    for n in range(5):
        repo_create_church(name=f"Church {n}", timezone="America/Chicago", owner_user_id=user_id)
    key = uuid.uuid4()

    for _attempt in range(2):
        r = client.post("/churches", json=BODY, headers=_key_headers(key))
        assert r.status_code == 429, r.text
        error = r.json()["error"]
        assert (error["code"], error["message"]) == ("rate_limited", CAP_MESSAGE)
        assert "fields" not in error
        seconds = error["details"]["retry_after_seconds"]
        assert isinstance(seconds, int) and 1 <= seconds <= 24 * 60 * 60
        assert r.headers["Retry-After"] == str(seconds)
        assert "Idempotent-Replayed" not in r.headers
    assert _count(Church) == 5
```

- [ ] **Step 2 (agent): Name the route in the three app-wide tests**

In `backend/tests/test_route_guards.py`, replace:

```python
USER_SCOPED = {
    ("GET", "/me"),
}
```

with:

```python
USER_SCOPED = {
    ("GET", "/me"),
    ("POST", "/churches"),
}
```

In `backend/tests/test_api_app.py` (`test_routes_document_the_error_body`), replace:

```python
        ("/rubric", "patch"): {"401", "403", "422", "503"},
    }
    for (path, method), statuses in expected.items():
        responses = schema["paths"][path][method]["responses"]
        assert set(responses) - {"200"} == statuses, (path, method)
```

with:

```python
        ("/rubric", "patch"): {"401", "403", "422", "503"},
        ("/churches", "post"): {"401", "422", "429", "503"},
    }
    for (path, method), statuses in expected.items():
        responses = schema["paths"][path][method]["responses"]
        assert set(responses) - {"200", "201"} == statuses, (path, method)   # minus the success status
```

In `backend/tests/test_no_streamlit_in_core.py` (end of `test_api_main_with_every_router_does_not_import_streamlit`), replace:

```python
    assert "unmounted: []" in result.stdout
    assert "'api.routes.me'" in result.stdout and "'api.routes.rubric'" in result.stdout
```

with:

```python
    assert "unmounted: []" in result.stdout
    assert "'api.routes.me'" in result.stdout and "'api.routes.rubric'" in result.stdout
    assert "'api.routes.churches'" in result.stdout
```

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_churches.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3
```

**Expected:** `18 failed, 30 passed, 1 skipped in <t>s`. The 14 `test_api_churches.py` tests fail on their first status assert (`assert 404 == 401`, `assert 404 == 201`, …: `POST /churches` is not routed yet); `test_user_scoped_routes_require_a_user` fails with `KeyError: ('POST', '/churches')`; `test_allowlists_name_real_routes` fails on `USER_SCOPED - served == set()`; `test_routes_document_the_error_body` fails with `KeyError: '/churches'`; `test_api_main_with_every_router_does_not_import_streamlit` fails on the new `'api.routes.churches'` assert. The skip is `test_api_app.py`'s Postgres test.

- [ ] **Step 4 (agent): Add `CreateChurchIn` (`backend/api/schemas.py`)**

Replace the first line:

```python
"""Response models (also documented at /docs)."""
```

with:

```python
"""Request and response models (also documented at /docs)."""
```

Replace:

```python
from pydantic import BaseModel
```

with:

```python
from pydantic import BaseModel, ConfigDict, Field
```

Replace the end of the file:

```python
class RubricOut(BaseModel):
    rubric: RubricModel
    customized: list[str]
```

with:

```python
class RubricOut(BaseModel):
    rubric: RubricModel
    customized: list[str]


class CreateChurchIn(BaseModel):
    """The body of POST /churches. A blank name or time zone is left to the
    usecase, whose 422 names the field."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field("", max_length=200)
    timezone: str = Field("", max_length=64)
```

(The docstring is public: it becomes the component's `description` in `openapi.json`, so it carries no spec references.)

- [ ] **Step 5 (agent): Create `backend/api/routes/churches.py`**

```python
"""POST /churches: create a church; the caller becomes its owner (S API, Idempotency).

User-scoped: the route depends on get_current_user and never on
require_church, so X-Church-Id is ignored (F §1.2). get_current_user comes
before idempotency_key(), so no token plus a malformed key is 401, not 422.
The usecase runs inside run_idempotent's `call`: an Idempotency-Key replays
the first response, and the cap's 429 is never stored (F §1.6). Plain `def`,
because run_idempotent blocks on a lock. Slice 2 adds the church_create burst
bucket as one more dependency.
"""
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.schemas import ChurchOut, CreateChurchIn
from usecases import onboarding

router = APIRouter()


@router.post("/churches", status_code=201, response_model=ChurchOut,
             responses=error_responses(401, 422, 429, 503))
def create_church(
    payload: CreateChurchIn,
    user: CurrentUser = Depends(get_current_user),
    key: uuid.UUID | None = Depends(idempotency_key()),
) -> Response:
    return run_idempotent(
        user_id=user.id,
        route="/churches",
        key=key,
        payload=payload,
        status_code=201,
        call=lambda: ChurchOut(**asdict(onboarding.create_church(
            user_id=user.id, name=payload.name, timezone=payload.timezone))),
    )
```

FastAPI runs the two `Depends` in declaration order (the body parameter's place in the signature does not matter); `test_bad_key_without_token_is_401` pins that order.

- [ ] **Step 6 (agent): Mount the router (`backend/api/main.py`)**

Replace:

```python
from api.routes import health, me, rubric
```

with:

```python
from api.routes import churches, health, me, rubric
```

Replace:

```python
    app.include_router(rubric.router)
    return app
```

with:

```python
    app.include_router(rubric.router)
    app.include_router(churches.router)
    return app
```

- [ ] **Step 7 (agent): Run the tests to verify they pass; see the stale OpenAPI file fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_churches.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -3
```

**Expected:** `48 passed, 1 skipped in <t>s`; then `1 failed, 2 passed in <t>s` with `FAILED backend/tests/test_openapi_contract.py::test_committed_openapi_matches_the_live_schema` (the committed `openapi.json` has no `/churches` yet; the next step regenerates it).

If `test_cap_429_not_replayed` gets 201 instead of 429, Task 3's cap is not counting the five churches made by `repos.churches.create_church`: check Task 2's `recent_owned_creations` (owner memberships, `created_at > since`) before touching the route. If `test_create_201_listed_in_me_and_usable` finds 0 hymns, Task 2's bulk seed or Task 3's `create_church_seeded` call is at fault, not this task.

- [ ] **Step 8 (agent): Regenerate `openapi.json` and `schema.d.ts`**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
git diff --numstat -- frontend/src/lib/api
grep -n '"/churches": {\|CreateChurchIn: {\|create_church_churches_post: {' frontend/src/lib/api/schema.d.ts
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -1
```

**Expected:** `Wrote <repo>/frontend/src/lib/api/openapi.json`; openapi-typescript prints `src/lib/api/openapi.json → src/lib/api/schema.d.ts`; the numstat shows additions only (about `122	0	frontend/src/lib/api/openapi.json` and `97	0	frontend/src/lib/api/schema.d.ts`); the grep prints three lines (the `/churches` path, the `CreateChurchIn` component, the `create_church_churches_post` operation); then `3 passed in <t>s`. Never hand-edit either file.

- [ ] **Step 9 (agent): Run both suites, typecheck and lint**

```bash
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test && npm run typecheck && npm run lint)
git status --short
```

**Expected:** `775 passed, 5 skipped in <t>s` (761 after Task 5 + 14); Vitest `Test Files  23 passed (23)` and `Tests  126 passed (126)`; `tsc --noEmit` and `eslint` print no errors; then exactly:

```
 M backend/api/main.py
 M backend/api/schemas.py
 M backend/tests/test_api_app.py
 M backend/tests/test_no_streamlit_in_core.py
 M backend/tests/test_route_guards.py
 M frontend/src/lib/api/openapi.json
 M frontend/src/lib/api/schema.d.ts
?? .claude/
?? backend/api/routes/churches.py
?? backend/tests/test_api_churches.py
```

If `typecheck` fails, the generated schema is stale: rerun Step 8's first command; never hand-edit `schema.d.ts`.

- [ ] **Step 10 (agent): Commit**

```bash
git add backend/api/routes/churches.py backend/api/schemas.py backend/api/main.py \
        backend/tests/test_api_churches.py backend/tests/test_route_guards.py backend/tests/test_api_app.py \
        backend/tests/test_no_streamlit_in_core.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -m "API: POST /churches with Idempotency-Key and the per-user cap (F §1.6; S API, Idempotency; AC6)

201 ChurchOut {id, name, role: owner}. User-scoped (X-Church-Id ignored);
get_current_user runs before idempotency_key(), so no token plus a bad key
is 401. The usecase runs inside run_idempotent: a replay returns the first
response and creates one church (F-AC7), a mismatched body is 422
idempotency_mismatch, and the cap's 429 is never stored, so a same-key retry
runs again. CreateChurchIn forbids extra fields (name max 200, timezone
max 64). USER_SCOPED, the error-doc test and the regenerated openapi.json
and schema.d.ts land in the same commit (1b clarification 9).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** `<sha> API: POST /churches with Idempotency-Key and the per-user cap (F §1.6; S API, Idempotency; AC6)`; `git status --short` then lists only `?? .claude/`.

Counts after Task 6: backend **775 passed, 5 skipped**; frontend **126 passed in 23 files** (unchanged; schema regenerated, typecheck green).
### Task 7: `POST /invites/preview` and `POST /invites/accept` (S API, Invite checks, Preview semantics, Testing `test_api_invites.py`; F §4.3, §7.4; AC7, AC9; clarifications 8, 9, 37, 40)

The two invite routes, over Task 4's `preview_invite` and Task 5's `accept_invite`. Both are user-scoped: the caller comes from the token, `X-Church-Id` is ignored, and neither takes an `Idempotency-Key` (accept is idempotent by construction, S Idempotency). Each route parses `InviteCodeIn`, calls **one** usecase and maps its frozen dataclass to the response model, with no SQL and no `try`/`except` (Global Constraints, Layering): a `Rejected` becomes 400 `invite_rejected` with `details.reason`, the blank code's `InvalidInput(field="code")` becomes a 422 with `fields.code`, both through 1a's `DomainError` handler. The code travels only in the JSON body, never in a path, a query string or a log line (AC9); the routes themselves log nothing.

Same-commit couplings (clarification 9): the route module, its mount in `api/main.py`, the two `USER_SCOPED` entries (`test_route_guards.py:74` and `:91` fail otherwise), the two error-doc rows in `test_api_app.py` (both routes list 422, so FastAPI's `HTTPValidationError` stays out of the schema), the `'api.routes.invites'` assert in `test_no_streamlit_in_core.py`, and the regenerated `openapi.json` + `schema.d.ts` (`test_openapi_contract.py:27` and CI's `gen:api` diff).

`test_api_invites.py` pins the HTTP layer only; the checks' order, the clamp and the accept semantics are Task 4/5's usecase tests. It adds 24 tests: the guard (2), all six rejections on both routes (12), the blank code on both routes (2; `""`, `"   "` and a body without `code` give the same 422), the exact preview and accept bodies (the accept test also repeats the accept: `already_member: true`), the `owner` → `admin` clamp over HTTP, `expires_at` with an offset, `X-Church-Id` ignored, `GET /church` 200 after accept, and two log-hygiene tests. `InviteCodeIn`'s `max_length=256` and `extra="forbid"` are 1a's generic 422 mapping (`test_api_app.py` covers "Too long (max N characters)." and "Not a valid value."); here they are pinned by the committed OpenAPI snapshot (`"maxLength": 256`, `"additionalProperties": false`), which `test_openapi_contract.py` compares on every run.

**Deviation from the outline (code wins; verified in a throwaway worktree at `0295b37` with a stand-in usecase and Task 1's engine change):** the outline's `test_db_error_logs_hold_no_code_or_email` monkeypatches `find_by_code` to raise a hand-built `OperationalError("select …", {"code": code}, Exception("boom"))`. That exception's text always carries `[parameters: ...]`: `hide_parameters` is an engine setting, and a `DBAPIError` built by hand defaults to `hide_parameters=False`, so that test fails whatever the engine does. The replacement below makes the patched `find_by_code` run a real failing statement (`SELECT id FROM invites_gone WHERE code = :code`) through the app's engine, so the driver error really passes through `hide_parameters=True`. With Task 1's line removed, this test fails with `[parameters: ('<the code>',)]` inside `caplog.text`; with it, the log holds `[SQL parameters hidden due to hide_parameters=True]`, which the test asserts.

**Files:**
- Create: `backend/api/routes/invites.py`
- Create: `backend/tests/test_api_invites.py`
- Modify: `backend/api/schemas.py` (`from datetime import datetime`; append `InviteCodeIn`, `InvitePreviewOut`, `InviteAcceptOut` after Task 6's `CreateChurchIn`, the end of the file)
- Modify: `backend/api/main.py` (import and mount `invites`)
- Modify: `backend/tests/test_route_guards.py` (`USER_SCOPED` + 2 routes)
- Modify: `backend/tests/test_api_app.py` (`test_routes_document_the_error_body`: 2 rows)
- Modify: `backend/tests/test_no_streamlit_in_core.py` (one assert appended)
- Modify: `frontend/src/lib/api/openapi.json` (generated by `backend/scripts/export_openapi.py`; never edited by hand)
- Modify: `frontend/src/lib/api/schema.d.ts` (generated by `npm run gen:api`; never edited by hand)

**Interfaces:**
- Consumes:
  - Task 4: `usecases.onboarding.preview_invite(*, user_id: uuid.UUID, user_email: str, code: str, now: datetime | None = None) -> InvitePreview`, where `InvitePreview(church_name: str, role: str, expires_at: datetime, email_bound: bool, already_member: bool)` is frozen, `role` is already clamped to `member`/`admin` and `expires_at` is aware UTC (`invites.as_utc`); rejections raise `Rejected(REJECT_MESSAGES[reason], code="invite_rejected", details={"reason": reason.value})` and log `invite_rejected reason=<reason> invite_id=<id>|none`; a blank or whitespace-only code raises `InvalidInput("Enter an invite code, or open your invite link again.", field="code")`.
  - Task 5: `usecases.onboarding.accept_invite(*, user_id: uuid.UUID, user_email: str, code: str, now: datetime | None = None) -> InviteAccepted`, where `InviteAccepted(church: ChurchSummary, already_member: bool, message: str)` and `ChurchSummary(id: uuid.UUID, name: str, role: str)` are frozen; it logs `invite_accepted invite_id=… church_id=… user_id=… already_member=…`. The usecase calls `invites.find_by_code(code, session=s)` through the module attribute (`from repos import churches, invites, memberships`; clarification 40), which is what lets the DB-error test patch `repos.invites.find_by_code`.
  - Task 2: `repos.invites.create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7, reusable: bool = False, session=None) -> str` (a new code-only invite is single-use); `repos.invites.get_invite_by_code(code) -> dict | None` (1a, keys include `id`, `accepted_at`); `repos.memberships.get_role(user_id, church_id, *, session=None) -> str | None`.
  - Task 1: `db.engine._engine_kwargs` sets `hide_parameters=True` for SQLite and Postgres (clarification 37), so the `tmp_db` engine (built by `reset_engine_for_tests` → `_make_engine` → `_engine_kwargs`) hides bound values too.
  - Task 6's state of the shared files: `api/schemas.py` imports `from pydantic import BaseModel, ConfigDict, Field` and ends with `CreateChurchIn`; `api/main.py` imports `from api.routes import churches, health, me, rubric` and mounts `churches.router`; `USER_SCOPED` ends with `("POST", "/churches"),`; `test_routes_document_the_error_body`'s `expected` ends with `("/churches", "post"): {"401", "422", "429", "503"},` and subtracts `{"200", "201"}`; `test_no_streamlit_in_core.py` ends with Task 6's `'api.routes.churches'` assert.
  - 1a: `api.deps.CurrentUser(id, email, name, picture)` (`email` already `strip().lower()`), `get_current_user`; `api.errors.error_responses(*statuses)`; `api.schemas.ChurchOut(id: uuid.UUID, name: str, role: Literal["owner", "admin", "member"])`; `tests.api_helpers.auth_headers(email)`, `church_headers(email, church_id)`, `make_api_client()`; conftest `tmp_db`, `make_user(email=...) -> uuid.UUID`, `make_church(name=..., owner_user_id=...) -> uuid.UUID`; `db.get_engine()`, `db.session_scope()`; `db.models.Church`, `Invite`.
- Produces:
  - `api.schemas.InviteCodeIn` (`model_config = ConfigDict(extra="forbid")`; `code: str = Field("", max_length=256)`).
  - `api.schemas.InvitePreviewOut(church_name: str, role: Literal["member", "admin"], expires_at: datetime, email_bound: bool, already_member: bool)`: exactly five keys, never the invite id, code, church id, creator or bound email (F §7.4); `expires_at` serializes as ISO 8601 ending `Z` (Pydantic 2.13, aware UTC).
  - `api.schemas.InviteAcceptOut(church: ChurchOut, already_member: bool, message: str)`.
  - `api.routes.invites.router` with `def preview_invite(payload: InviteCodeIn, user: CurrentUser = Depends(get_current_user)) -> InvitePreviewOut` on `POST /invites/preview` (200) and `def accept_invite(payload: InviteCodeIn, user: CurrentUser = Depends(get_current_user)) -> InviteAcceptOut` on `POST /invites/accept` (200); both `responses=error_responses(400, 401, 422, 503)`. Later users: Task 8 (Postgres races over these routes), Task 13 (`usePreviewInvite`, `useAcceptInvite`, `InvitePreview`/`InviteAccepted` types from `schema.d.ts`), Task 14/15 (`JoinInvite`, `/join`), slice 6b (adds `GET`/`POST /invites` and `DELETE /invites/{invite_id}` below these two fixed paths).
  - OpenAPI: paths `POST /invites/accept`, `POST /invites/preview` with responses `['200', '400', '401', '422', '503']`; schemas `InviteAcceptOut`, `InviteCodeIn`, `InvitePreviewOut`.

Counts after this task: backend **799 passed, 5 skipped** (775 + 24); frontend **126 passed in 23 files** (unchanged; only `schema.d.ts` is regenerated).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_api_invites.py`:

```python
"""POST /invites/preview and POST /invites/accept over HTTP (S API, Testing
`test_api_invites.py`; AC7, AC9).

test_usecase_onboarding.py covers every check, their order, the role clamp and
the accept semantics. These tests pin the HTTP layer: the guard, the statuses,
the exact bodies, X-Church-Id being ignored, and that neither the invite code
nor the caller's email reaches a log line, including the traceback of an
unhandled database error (clarification 37).
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from db import get_engine, session_scope
from db.models import Church, Invite
from repos.invites import create_invite, get_invite_by_code
from repos.memberships import get_role
from tests.api_helpers import auth_headers, church_headers, make_api_client

OWNER = "owner@example.com"
JOINER = "joiner@example.com"
BOUND = "bound@example.com"
UNKNOWN_CODE = "no-such-invite-code"
BLANK = "Enter an invite code, or open your invite link again."
ROUTES = ["preview", "accept"]
REJECTIONS = [
    pytest.param("unknown", "Invalid invite code.", id="unknown"),
    pytest.param("revoked", "This invite has been revoked.", id="revoked"),
    pytest.param("expired", "This invite has expired.", id="expired"),
    pytest.param("used", "This invite has already been used.", id="used"),
    pytest.param("church_unavailable", "This church is no longer available.", id="church_unavailable"),
    pytest.param("email_mismatch", "This invite was issued for a different email address.",
                 id="email_mismatch"),
]


@dataclass(frozen=True)
class World:
    client: TestClient
    church_id: uuid.UUID          # "Grace", owned by OWNER
    owner_id: uuid.UUID
    joiner_id: uuid.UUID          # JOINER: signed up, a member of nothing

    def invite(self, **kwargs) -> str:
        """A Grace invite from OWNER (code-only and single-use unless kwargs say otherwise)."""
        return create_invite(church_id=self.church_id, created_by=self.owner_id, **kwargs)

    def post(self, route: str, code: str, *, headers: dict[str, str] | None = None):
        return self.client.post(f"/invites/{route}", headers=headers or auth_headers(JOINER),
                                json={"code": code})


@pytest.fixture
def world(tmp_db, make_user, make_church) -> World:
    owner_id = make_user(email=OWNER)
    church_id = make_church(name="Grace", owner_user_id=owner_id)
    joiner_id = make_user(email=JOINER)    # the token's email resolves to this same user id
    return World(client=make_api_client(), church_id=church_id, owner_id=owner_id, joiner_id=joiner_id)


def _rejected_code(reason: str, world: World, make_user) -> str:
    """A code that JOINER's preview or accept rejects with `reason` (checks 1-6)."""
    if reason == "unknown":
        return UNKNOWN_CODE
    if reason == "expired":
        return world.invite(ttl_days=-1)
    if reason == "email_mismatch":
        return world.invite(email=BOUND)
    first = make_user(email="first@example.com") if reason == "used" else None
    code = world.invite()
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
        if reason == "revoked":
            inv.revoked = True
        elif reason == "used":                   # another user accepted it first
            inv.accepted_at = datetime.now(timezone.utc)
            inv.accepted_by = first
        else:                                    # church_unavailable: soft-deleted, the invite left live
            s.get(Church, world.church_id).deleted_at = datetime.now(timezone.utc)
    return code


@pytest.mark.parametrize("route", ROUTES)
def test_requires_token(world, route):
    code = world.invite()
    r = world.client.post(f"/invites/{route}", json={"code": code})
    assert r.status_code == 401, r.text
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("unauthenticated", "Please sign in.")
    assert get_invite_by_code(code)["accepted_at"] is None


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("reason,message", REJECTIONS)
def test_rejection_over_http(world, make_user, route, reason, message):
    code = _rejected_code(reason, world, make_user)
    r = world.post(route, code)
    assert r.status_code == 400, r.text
    error = r.json()["error"]
    assert (error["code"], error["message"], error["details"]) == (
        "invite_rejected", message, {"reason": reason})
    assert "fields" not in error                 # fields only on a 422 (clarification 8)
    assert get_role(world.joiner_id, world.church_id) is None


@pytest.mark.parametrize("route", ROUTES)
def test_blank_code_422_fields_code(world, route):
    for body in ({"code": ""}, {"code": "   "}, {}):
        r = world.client.post(f"/invites/{route}", headers=auth_headers(JOINER), json=body)
        assert r.status_code == 422, (body, r.text)
        error = r.json()["error"]
        assert (error["code"], error["message"], error["fields"]) == (
            "invalid_request", BLANK, {"code": BLANK}), body


def test_preview_keys_exact(world):
    code = world.invite()
    r = world.post("preview", code)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "church_name": "Grace",
        "role": "member",
        "expires_at": r.json()["expires_at"],
        "email_bound": False,
        "already_member": False,
    }
    invite = get_invite_by_code(code)
    for withheld in (code, str(invite["id"]), str(world.church_id), str(world.owner_id), OWNER):
        assert withheld not in r.text            # F §7.4: no id, code, church id or creator
    assert invite["accepted_at"] is None         # read-only
    assert get_role(world.joiner_id, world.church_id) is None

    bound = world.post("preview", world.invite(email=JOINER.upper()))
    assert bound.status_code == 200, bound.text
    assert bound.json()["email_bound"] is True
    assert JOINER not in bound.text.lower()      # nor the bound email


def test_accept_body_shape(world):
    code = world.invite()
    r = world.post("accept", code)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "church": {"id": str(world.church_id), "name": "Grace", "role": "member"},
        "already_member": False,
        "message": "Joined Grace.",
    }
    assert get_role(world.joiner_id, world.church_id) == "member"

    again = world.post("accept", code)           # the same user repeats: a 200 that changes nothing
    assert again.status_code == 200, again.text
    assert again.json() == {
        "church": {"id": str(world.church_id), "name": "Grace", "role": "member"},
        "already_member": True,
        "message": "You're already a member of Grace.",
    }


def test_preview_owner_role_is_admin(world):
    code = world.invite(role="owner")            # no CHECK on invites.role until 6b
    r = world.post("preview", code)
    assert r.status_code == 200, r.text          # clamped, not a response-validation 500
    assert r.json()["role"] == "admin"
    joined = world.post("accept", code)
    assert joined.status_code == 200, joined.text
    assert joined.json()["church"]["role"] == "admin"
    assert get_role(world.joiner_id, world.church_id) == "admin"


def test_preview_expires_at_has_offset(world):
    r = world.post("preview", world.invite())
    assert r.status_code == 200, r.text
    expires_at = r.json()["expires_at"]
    assert expires_at.endswith("Z") or expires_at.endswith("+00:00"), expires_at
    assert timedelta(days=6) < datetime.fromisoformat(expires_at) - datetime.now(timezone.utc) <= timedelta(days=7)


def test_x_church_id_ignored(world, make_church):
    elsewhere = make_church(name="Elsewhere")    # JOINER belongs to neither church
    headers = church_headers(JOINER, elsewhere)
    code = world.invite()
    preview = world.post("preview", code, headers=headers)
    assert preview.status_code == 200, preview.text
    assert preview.json()["church_name"] == "Grace"
    joined = world.post("accept", code, headers=headers)
    assert joined.status_code == 200, joined.text
    assert joined.json()["church"]["id"] == str(world.church_id)
    assert get_role(world.joiner_id, elsewhere) is None


def test_after_accept_get_church_200(world):
    before = world.client.get("/church", headers=church_headers(JOINER, world.church_id))
    assert before.status_code == 403, before.text
    church_id = world.post("accept", world.invite()).json()["church"]["id"]
    r = world.client.get("/church", headers=church_headers(JOINER, uuid.UUID(church_id)))
    assert r.status_code == 200, r.text
    assert r.json() == {"id": church_id, "name": "Grace", "role": "member"}


def test_logs_hold_no_code_or_email(world, caplog):
    caplog.set_level(logging.INFO)
    code = world.invite()
    mismatch = world.invite(email=BOUND)
    assert world.post("preview", code).status_code == 200
    assert world.post("accept", code).status_code == 200
    assert world.post("accept", UNKNOWN_CODE).status_code == 400
    assert world.post("preview", mismatch).status_code == 400
    assert "invite_accepted invite_id=" in caplog.text           # the lines really were captured
    assert "invite_rejected reason=unknown invite_id=none" in caplog.text
    assert "invite_rejected reason=email_mismatch invite_id=" in caplog.text
    for secret in (code, mismatch, UNKNOWN_CODE, JOINER, BOUND):
        assert secret not in caplog.text, secret


def test_db_error_logs_hold_no_code_or_email(world, caplog, monkeypatch):
    """A database error while looking the code up is a 500 whose logged traceback
    carries neither the code nor the email: the engine hides bound parameters
    (clarification 37), and the app logs the method and path only."""
    import repos.invites

    def find_by_code_db_down(code, *_args, **_kwargs):
        with get_engine().connect() as conn:     # a real driver error with the code bound
            conn.execute(text("SELECT id FROM invites_gone WHERE code = :code"), {"code": code})

    monkeypatch.setattr(repos.invites, "find_by_code", find_by_code_db_down)
    caplog.set_level(logging.INFO)
    code = world.invite()
    client = TestClient(world.client.app, raise_server_exceptions=False)
    r = client.post("/invites/accept", headers=auth_headers(JOINER), json={"code": code})
    assert r.status_code == 500, r.text
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("internal_error", "Something went wrong.")
    assert "Unhandled error on POST /invites/accept" in caplog.text
    assert "invites_gone" in caplog.text         # the driver's error text is in the log
    assert "[SQL parameters hidden due to hide_parameters=True]" in caplog.text
    assert code not in caplog.text and JOINER not in caplog.text
    assert get_role(world.joiner_id, world.church_id) is None
```

In `backend/tests/test_route_guards.py`, replace (Task 6's last `USER_SCOPED` entry and the closing brace):

```python
    ("POST", "/churches"),
}
```

with:

```python
    ("POST", "/churches"),
    ("POST", "/invites/preview"),
    ("POST", "/invites/accept"),
}
```

In `backend/tests/test_api_app.py`, inside `test_routes_document_the_error_body`, replace Task 6's row:

```python
        ("/churches", "post"): {"401", "422", "429", "503"},
```

with:

```python
        ("/churches", "post"): {"401", "422", "429", "503"},
        ("/invites/preview", "post"): {"400", "401", "422", "503"},
        ("/invites/accept", "post"): {"400", "401", "422", "503"},
```

(The loop already subtracts `{"200", "201"}` since Task 6; both invite routes answer 200.)

In `backend/tests/test_no_streamlit_in_core.py`, append one line at the end of `test_api_main_with_every_router_does_not_import_streamlit` (after Task 6's `'api.routes.churches'` assert, the last line of the file):

```python
    assert "'api.routes.invites'" in result.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_invites.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3`

Expected: `28 failed, 30 passed, 1 skipped`. The 24 new tests fail because neither route exists: `assert 404 == 401` / `== 400` / `== 422` / `== 200` / `== 500` (`<Response [404 Not Found]>`), and `KeyError: 'church'` in `test_after_accept_get_church_200` (its 403 control passes first). Four existing tests fail with them: `test_route_guards.py::test_user_scoped_routes_require_a_user` (`KeyError: ('POST', '/invites/accept')`), `::test_allowlists_name_real_routes` (`assert {('POST', '/invites/accept'), ('POST', '/invites/preview')} == set()`), `test_api_app.py::test_routes_document_the_error_body` (`KeyError: '/invites/preview'`) and `test_no_streamlit_in_core.py::test_api_main_with_every_router_does_not_import_streamlit` (`assert "'api.routes.invites'" in ...`). The skip is `test_api_app.py`'s Postgres-only test.

- [ ] **Step 3: Add the request and response models**

In `backend/api/schemas.py`, replace:

```python
import uuid
from typing import Generic, Literal, Optional, TypeVar
```

with:

```python
import uuid
from datetime import datetime
from typing import Generic, Literal, Optional, TypeVar
```

Check that the pydantic import (Task 6) reads `from pydantic import BaseModel, ConfigDict, Field`; if it lacks either name, make it exactly that line. Then append at the end of the file (after Task 6's `CreateChurchIn`):

```python


class InviteCodeIn(BaseModel):
    """POST /invites/preview and /invites/accept: the code, only ever in the body (AC9)."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field("", max_length=256)


class InvitePreviewOut(BaseModel):
    """What an invite offers. Never its id, code, church id, creator or bound email (F §7.4)."""

    church_name: str
    role: Literal["member", "admin"]
    expires_at: datetime
    email_bound: bool
    already_member: bool


class InviteAcceptOut(BaseModel):
    church: ChurchOut
    already_member: bool
    message: str
```

(`code` defaults to `""` so a body without it reaches the usecase's check 0 and gets the exact "Enter an invite code, …" message with `fields.code`, not Pydantic's "Required.". The usecase strips it; Pydantic does not.)

- [ ] **Step 4: Create the route module and mount it**

Create `backend/api/routes/invites.py`:

```python
"""Joining a church with an invite code (S API; F §4.3, §7.4; AC7, AC9).

Both routes are user-scoped: the caller comes from the token and X-Church-Id is
ignored. The code travels only in the JSON body, never in a path or a query
string, and no log line carries it (the usecase logs ids and reasons only).
Plain `def` routes: each parses, calls one usecase and maps its dataclass.

Slice 6b adds GET/POST /invites and DELETE /invites/{invite_id} to this module,
below these two: the fixed paths /invites/preview and /invites/accept must stay
declared before any /invites/{invite_id} route.
"""
from dataclasses import asdict

from fastapi import APIRouter, Depends

from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.schemas import ChurchOut, InviteAcceptOut, InviteCodeIn, InvitePreviewOut
from usecases import onboarding

router = APIRouter()


@router.post("/invites/preview", response_model=InvitePreviewOut,
             responses=error_responses(400, 401, 422, 503))
def preview_invite(payload: InviteCodeIn, user: CurrentUser = Depends(get_current_user)) -> InvitePreviewOut:
    """What the invite offers (church, role, expiry) without joining: writes nothing."""
    preview = onboarding.preview_invite(user_id=user.id, user_email=user.email, code=payload.code)
    return InvitePreviewOut(**asdict(preview))


@router.post("/invites/accept", response_model=InviteAcceptOut,
             responses=error_responses(400, 401, 422, 503))
def accept_invite(payload: InviteCodeIn, user: CurrentUser = Depends(get_current_user)) -> InviteAcceptOut:
    """Join the invite's church; for an existing member, a 200 that changes nothing."""
    accepted = onboarding.accept_invite(user_id=user.id, user_email=user.email, code=payload.code)
    return InviteAcceptOut(church=ChurchOut(**asdict(accepted.church)),
                           already_member=accepted.already_member, message=accepted.message)
```

In `backend/api/main.py`, replace:

```python
from api.routes import churches, health, me, rubric
```

with:

```python
from api.routes import churches, health, invites, me, rubric
```

and replace:

```python
    return app


app = create_app()
```

with:

```python
    app.include_router(invites.router)
    return app


app = create_app()
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_invites.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3`

Expected: `58 passed, 1 skipped`.

- [ ] **Step 6: Regenerate the OpenAPI snapshot and `schema.d.ts`**

Run:

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
.venv/bin/python -c "
import json
s = json.load(open('frontend/src/lib/api/openapi.json'))
print(sorted(s['components']['schemas']))
for path, ops in sorted(s['paths'].items()):
    for method, op in ops.items():
        print(method.upper(), path, sorted(op['responses']))
print(s['components']['schemas']['InviteCodeIn']['properties']['code'], s['components']['schemas']['InviteCodeIn']['additionalProperties'])
print(s['components']['schemas']['InvitePreviewOut']['required'])
"
grep -cE '^ {8}Invite(AcceptOut|CodeIn|PreviewOut): \{' frontend/src/lib/api/schema.d.ts
git diff --stat -- frontend/src/lib/api
```

Expected:

```text
Wrote <repo>/frontend/src/lib/api/openapi.json
🚀 src/lib/api/openapi.json → src/lib/api/schema.d.ts [<t>ms]
['ChurchOut', 'CreateChurchIn', 'ErrorBody', 'ErrorDetail', 'InviteAcceptOut', 'InviteCodeIn', 'InvitePreviewOut', 'MeOut', 'ReadyOut', 'RubricModel', 'RubricOut', 'UserOut']
GET /church ['200', '401', '403', '422', '503']
POST /churches ['201', '401', '422', '429', '503']
GET /health ['200']
GET /health/ready ['200']
POST /invites/accept ['200', '400', '401', '422', '503']
POST /invites/preview ['200', '400', '401', '422', '503']
GET /me ['200', '401', '422', '503']
GET /rubric ['200', '401', '403', '422', '503']
PATCH /rubric ['200', '401', '403', '422', '503']
{'default': '', 'maxLength': 256, 'title': 'Code', 'type': 'string'} False
['church_name', 'role', 'expires_at', 'email_bound', 'already_member']
```

then `3` (the three new `components.schemas` entries in `schema.d.ts`) and `2 files changed` with insertions only (the `openapi-typescript 7.13.0` banner line also prints before the arrow line). The `CreateChurchIn` and `POST /churches` lines are Task 6's and are unchanged.

- [ ] **Step 7: Run the contract test, the suites and the log-hygiene gate**

Run:

```bash
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
grep -n "logger\|logging\|print(" backend/api/routes/invites.py || echo "routes log nothing"
grep -n '"/invites/{' backend/api/routes/invites.py || echo "no code in a path"
(cd frontend && npm test && npm run typecheck && npm run lint)
```

Expected: `3 passed`; `799 passed, 5 skipped` (775 after Task 6 + 24); `routes log nothing`; `no code in a path`; Vitest `Test Files  23 passed (23)` and `Tests  126 passed (126)`, then `tsc --noEmit` and `eslint` with no output (nothing imports the new types until Task 13).

- [ ] **Step 8: Commit**

```bash
git add backend/api/routes/invites.py backend/api/schemas.py backend/api/main.py \
        backend/tests/test_api_invites.py backend/tests/test_route_guards.py \
        backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py \
        frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -m "API: POST /invites/preview and /invites/accept (S API, Invite checks; F §4.3, §7.4; AC7, AC9)

Both routes are user-scoped (X-Church-Id ignored), take InviteCodeIn {code}
(max 256, extra fields rejected) and call one usecase each. Preview returns
exactly church_name, role (clamped), expires_at (aware UTC, ends in Z),
email_bound and already_member; accept returns {church, already_member,
message}. Rejections are 400 invite_rejected with details.reason and no
fields; a blank code is 422 with fields.code. The code stays in the body and
out of every log line, including an unhandled database error's traceback
(engine hide_parameters, clarification 37). USER_SCOPED, the error-doc rows,
the every-router check and the OpenAPI snapshot + schema.d.ts move with the
routes (clarification 9).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
### Task 8: Postgres accept races and the 700-row seed timing; the early draft-PR checkpoint (S Testing "Backend — onboarding (1b)"; AC8; Risk 3; clarifications 13, 40, 41; owner answer 5)

Nothing on this machine runs Postgres, so the three S scenarios that only a real server can show have not run yet: two users racing for one single-use invite, one user double-accepting (single-use and reusable), and a church create that copies a 700-row catalog. SQLite serializes writers, so there the second request never overlaps the first. This task adds them as `@pytest.mark.postgres` tests in one new file. They skip locally and run in CI's `backend-postgres` job (`python -m pytest -m postgres -q`, `ci.yml:63`, pinned by `test_ci_workflow.py`; `ci.yml` is **not** edited). Then the agent pushes the branch and opens a **draft** PR so that job runs before the frontend work starts (Tasks 9–19). Owner answer 5 authorizes the push and the draft PR in advance: do not ask again. The agent never marks the PR ready. That happens in Task 20, on the owner's yes.

**Forcing the race (clarification 40).** Firing two threads at once does not make the requests overlap: the first can finish before the second reads the invite, and the second then takes the sequential `used` or already-a-member path. The single-use cases monkeypatch `repos.invites.claim`, and the reusable case patches `repos.memberships.ensure_membership`. The wrapper does `threading.Barrier(2).wait(timeout=10)` and then calls the real function (pattern `test_identity.py:219-233`). Both requests are then past `_evaluate` and `get_role` before either writes, so the second one really gets the claim that updates 0 rows followed by `s.refresh(inv)`, or the `insert_ignore` that inserts 0 rows. The wrapper records what the real function returned, and the tests assert `[False, True]`. That proves the race path ran. A request that never reaches the wrapper leaves the other waiting. After 10 s the barrier breaks, `BrokenBarrierError` reaches the TestClient (`raise_server_exceptions` is on) and the test errors instead of passing vacuously. The usecase calls both functions through module attributes (`from repos import churches, invites, memberships` → `invites.claim(...)`; Task 3/5), so patching the module attribute reaches it. The Postgres pool (3 + 3 overflow, `db/engine.py:48-49`) covers the two connections held at the barrier.

**Seeding (clarification 13).** `tmp_db`, `make_user`, `make_church` and `seed_catalog` bind SQLite and cannot be used. Users are created through `GET /me`, as a real sign-in does (this also fills the identity cache, so the raced requests write nothing to `users`). Churches, invites and catalog rows are created through the repos and `session_scope()` on `pg_db`'s engine. `pg_db` truncates every table before each test.

**Seed timing (clarification 41).** CI's `-q` run captures a passing test's stdout, so a `print` would be invisible. The test calls `warnings.warn(f"hymn seed: {n} rows in {ms} ms", UserWarning)` before asserting the 3 s budget, so the time appears in the job log's "warnings summary" even when the budget assertion fails. (Checked here: under `pytest -m postgres -q` pytest prints `=== warnings summary ===`, the `UserWarning: hymn seed: 700 rows in 412 ms` line and `1 passed, 1 warning`.) `ms` covers the whole `POST /churches` round trip, so it is an upper bound on the seed.

**No local red step.** Tasks 2–7 already built the behavior these tests check, and S limits these scenarios to Postgres. The local run shows only that the tests are collected and skipped. On CI they can fail for real: the barrier-and-results assertions fail if the race path is not taken, and the budget assertion fails above 3 s.

**Files:**
- Create: `backend/tests/test_onboarding_postgres.py` (4 tests: 3 functions, one parametrized ×2)
- No application code, fixture, `conftest.py` or `ci.yml` change.

**Interfaces:**
- Consumes:
  - fixture `pg_db` (`backend/tests/conftest.py`, 1a): skips with `TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)`; otherwise binds the engine via `reset_engine_for_tests`, runs `alembic upgrade head`, truncates every table except `alembic_version`, and yields the `Engine`;
  - `tests.api_helpers.make_api_client() -> TestClient` and `tests.api_helpers.auth_headers(email: str) -> dict[str, str]` (1a); the autouse `_fresh_identity_cache` (1a) and `_fresh_idempotency_store` (Task 1);
  - `db.session_scope()`; `db.models.Hymn`, `HymnCatalog`, `Invite`, `Membership` (`memberships` PK `(church_id, user_id)`);
  - Task 2: `repos.churches.create_church(*, name, timezone, owner_user_id, session: Session | None = None) -> uuid.UUID`; `repos.invites.create_invite(*, church_id, created_by, role="member", email=None, ttl_days=7, reusable: bool = False, session: Session | None = None) -> str`; `repos.invites.claim(invite_id, user_id, now: datetime, *, session: Session | None = None) -> bool`; `repos.memberships.ensure_membership(church_id, user_id, role: str, *, session: Session | None = None) -> tuple[str, bool]`; `repos.hymns.seed_church_from_catalog` (Core bulk insert, reached through `POST /churches`);
  - Tasks 3 and 5: `usecases.onboarding.create_church` / `accept_invite`, which call `invites.claim(...)` and `memberships.ensure_membership(...)` through module attributes (clarification 40);
  - Task 6: `POST /churches` → 201 `ChurchOut {id, name, role: "owner"}`, optional `Idempotency-Key`; Task 7: `POST /invites/accept` with `InviteCodeIn {code}` → 200 `InviteAcceptOut {church: {id, name, role}, already_member, message}` or 400 `{"error": {"code": "invite_rejected", "message", "details": {"reason"}, "request_id"}}`; 1a: `GET /me` → `MeOut {user: {id, email, name, picture}, churches}`.
- Produces:
  - `backend/tests/test_onboarding_postgres.py`: module fixture `pg_client(pg_db) -> TestClient` (a module-local copy of `test_identity.py`'s); helpers `_user_id(client, email) -> uuid.UUID`, `_church_with_invite(client, *, reusable: bool) -> tuple[uuid.UUID, str]`, `_accept_together(client, monkeypatch, module, name, emails, code) -> tuple[list[httpx.Response], list]`, `_memberships(church_id, *user_ids) -> list[tuple[uuid.UUID, str]]`, `_invite_stamp(code) -> tuple`, `_seed_catalog_rows(n: int) -> None`; tests `test_two_users_race_single_use`, `test_same_user_double_accept[single_use]`, `test_same_user_double_accept[reusable]`, `test_create_church_700_row_catalog_under_3s`.
  - The draft PR `<N>` on `claude/slice-1b-plan` (number and URL from Step 7). Later users: Task 20 (pushes Tasks 9–19, retitles, replaces the body with the CI timing, and runs `gh pr ready` only on the owner's yes), Task 21.
  - The CI line `UserWarning: hymn seed: 700 rows in <ms> ms` (Step 9). Later users: Task 20 (PR body, copied from the final run), Task 21 (the `### Slice 1b record`, S Risk 3).

- [ ] **Step 1: Write the Postgres tests (agent)**

Create `backend/tests/test_onboarding_postgres.py`:

```python
"""Onboarding on real Postgres (slice 1b; S Testing "Backend — onboarding (1b)",
AC8, Risk 3): the accept races and the 700-row seed timing.

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs them with
`python -m pytest -m postgres -q`. The SQLite fixtures (tmp_db, make_user,
make_church, seed_catalog) cannot be used here, since they bind SQLite: users
are created through GET /me, as a real sign-in does, and churches, invites and
catalog rows through the repos on pg_db's engine (session_scope).

Forcing the race: a barrier inside repos.invites.claim (single-use invites) or
repos.memberships.ensure_membership (reusable invites) holds each request until
both have passed the invite checks, so the second one really takes the
"claim updated 0 rows -> refresh" or "ON CONFLICT DO NOTHING inserted 0 rows"
path, not the sequential `used` / already-a-member path. usecases.onboarding
calls both through module attributes (`invites.claim(...)`), so patching the
module attribute reaches it. A request that never reaches the wrapper leaves
the other one waiting: after 10 s the barrier breaks, BrokenBarrierError
reaches the TestClient and the test errors instead of passing vacuously.
"""
import threading
import time
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

import repos.invites
import repos.memberships
from db import session_scope
from db.models import Hymn, HymnCatalog, Invite, Membership
from repos.churches import create_church
from repos.invites import create_invite
from tests.api_helpers import auth_headers

OWNER = "owner@example.com"
ANN = "ann@example.com"
BEN = "ben@example.com"
CATALOG_ROWS = 700
GRACE_MEMBER = {"name": "Grace", "role": "member"}


@pytest.fixture
def pg_client(pg_db):
    from tests.api_helpers import make_api_client

    return make_api_client()


def _user_id(client, email) -> uuid.UUID:
    """Sign `email` in through GET /me (creates the users row, caches the identity)."""
    r = client.get("/me", headers=auth_headers(email))
    assert r.status_code == 200, r.text
    return uuid.UUID(r.json()["user"]["id"])


def _church_with_invite(client, *, reusable: bool) -> tuple[uuid.UUID, str]:
    """Church "Grace" owned by OWNER, and one code-only member invite; returns (church id, code)."""
    owner_id = _user_id(client, OWNER)
    church_id = create_church(name="Grace", timezone="America/New_York", owner_user_id=owner_id)
    code = create_invite(church_id=church_id, created_by=owner_id, reusable=reusable)
    return church_id, code


def _accept_together(client, monkeypatch, module, name, emails, code):
    """POST /invites/accept once per email, both at once. Each request waits at a
    barrier inside `module.name` until the other arrives, then runs the real
    function. Returns (responses in `emails` order, the real function's results)."""
    real = getattr(module, name)
    barrier = threading.Barrier(2)
    results = []

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        result = real(*args, **kwargs)
        results.append(result)
        return result

    monkeypatch.setattr(module, name, together)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(
            lambda email: client.post("/invites/accept", json={"code": code},
                                      headers=auth_headers(email)),
            emails,
        ))
    return responses, results


def _memberships(church_id, *user_ids) -> list[tuple[uuid.UUID, str]]:
    with session_scope() as s:
        rows = s.execute(
            select(Membership.user_id, Membership.role)
            .where(Membership.church_id == church_id, Membership.user_id.in_(user_ids))
        ).all()
        return [(row.user_id, row.role) for row in rows]


def _invite_stamp(code) -> tuple:
    """(accepted_at, accepted_by) of the invite with `code`."""
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
        return inv.accepted_at, inv.accepted_by


@pytest.mark.postgres
def test_two_users_race_single_use(pg_client, monkeypatch):
    """Two users accept one single-use invite at the same moment: exactly one
    joins; the other's claim waits on the row lock, updates 0 rows, and the
    refreshed row names someone else, so it gets 400 `used` (S Accept semantics,
    "Two users racing"; AC8)."""
    church_id, code = _church_with_invite(pg_client, reusable=False)
    ann_id, ben_id = _user_id(pg_client, ANN), _user_id(pg_client, BEN)

    responses, claims = _accept_together(pg_client, monkeypatch, repos.invites, "claim",
                                         [ANN, BEN], code)

    assert sorted(claims) == [False, True]      # both reached claim; one UPDATE matched 0 rows
    assert sorted(r.status_code for r in responses) == [200, 400]
    winner = next(r for r in responses if r.status_code == 200).json()
    loser = next(r for r in responses if r.status_code == 400).json()["error"]
    assert winner["already_member"] is False
    assert winner["message"] == "Joined Grace."
    assert winner["church"] == {"id": str(church_id), **GRACE_MEMBER}
    assert loser["code"] == "invite_rejected"
    assert loser["message"] == "This invite has already been used."
    assert loser["details"] == {"reason": "used"}
    assert "fields" not in loser
    winner_id = ann_id if responses[0].status_code == 200 else ben_id
    assert _memberships(church_id, ann_id, ben_id) == [(winner_id, "member")]
    accepted_at, accepted_by = _invite_stamp(code)
    assert accepted_at is not None
    assert accepted_by == winner_id


@pytest.mark.postgres
@pytest.mark.parametrize("reusable", [False, True], ids=["single_use", "reusable"])
def test_same_user_double_accept(pg_client, monkeypatch, reusable):
    """A double tap: one user sends two accepts at once. Both get 200, one
    membership exists, and exactly one response says `already_member: false`
    (S Accept semantics, "Idempotent for the same user"; AC8).
    Single-use: the second claim updates 0 rows, the refreshed row names the
    caller, and its INSERT ... ON CONFLICT DO NOTHING inserts nothing.
    Reusable (never claimed): the second INSERT waits on the primary key, then
    inserts nothing."""
    church_id, code = _church_with_invite(pg_client, reusable=reusable)
    ann_id = _user_id(pg_client, ANN)
    if reusable:
        module, name = repos.memberships, "ensure_membership"
    else:
        module, name = repos.invites, "claim"

    responses, results = _accept_together(pg_client, monkeypatch, module, name, [ANN, ANN], code)

    if reusable:
        assert sorted(inserted for _role, inserted in results) == [False, True]
    else:
        assert sorted(results) == [False, True]
    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    bodies = [r.json() for r in responses]
    assert sorted(b["already_member"] for b in bodies) == [False, True]
    assert sorted(b["message"] for b in bodies) == [
        "Joined Grace.",
        "You're already a member of Grace.",
    ]
    assert [b["church"] for b in bodies] == [{"id": str(church_id), **GRACE_MEMBER}] * 2
    assert _memberships(church_id, ann_id) == [(ann_id, "member")]
    accepted_at, accepted_by = _invite_stamp(code)
    if reusable:
        assert (accepted_at, accepted_by) == (None, None)    # reusable invites are never stamped
    else:
        assert accepted_at is not None
        assert accepted_by == ann_id


def _seed_catalog_rows(n: int) -> None:
    """`n` hymn_catalog rows with every column filled, like the real catalog."""
    with session_scope() as s:
        s.add_all([
            HymnCatalog(
                hymnal="GG2013",
                title=f"Hymn {i}",
                number=i,
                scripture_refs="Psalm 23; John 3:16",
                theme="Praise and thanksgiving",
                hymnary_link=f"https://hymnary.org/text/hymn_{i}",
                audio_url=f"https://example.org/audio/{i}.mp3",
                text_year=1700 + i % 300,
                hymnal_count=i % 60,
            )
            for i in range(1, n + 1)
        ])


@pytest.mark.postgres
def test_create_church_700_row_catalog_under_3s(pg_client):
    """S Risk 3: POST /churches copies the whole catalog (Core bulk insert,
    slice 1b T2) within 3 s on CI Postgres. The time covers the whole request,
    so it is an upper bound on the seed. It is also emitted as a UserWarning:
    `pytest -m postgres -q` captures a print, but prints warnings in its
    "warnings summary", where the PR copies it from (clarification 41).
    Production above 5 s -> switch the Postgres path to INSERT ... SELECT."""
    _seed_catalog_rows(CATALOG_ROWS)
    headers = auth_headers(OWNER)
    assert pg_client.get("/me", headers=headers).status_code == 200   # users row + identity cache

    start = time.perf_counter()
    r = pg_client.post(
        "/churches",
        json={"name": "Timing Church", "timezone": "America/New_York"},
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    elapsed = time.perf_counter() - start

    assert r.status_code == 201, r.text
    body = r.json()
    assert (body["name"], body["role"]) == ("Timing Church", "owner")
    with session_scope() as s:
        n = s.execute(
            select(func.count()).select_from(Hymn).where(Hymn.church_id == uuid.UUID(body["id"]))
        ).scalar_one()
    ms = round(elapsed * 1000)
    warnings.warn(f"hymn seed: {n} rows in {ms} ms", UserWarning)
    assert n == CATALOG_ROWS
    assert elapsed < 3.0, f"POST /churches with a {CATALOG_ROWS}-row catalog took {ms} ms (budget 3000 ms)"
```

- [ ] **Step 2: Run the new file locally: collected and skipped (agent)**

```bash
.venv/bin/python -m pytest -q -rs backend/tests/test_onboarding_postgres.py 2>&1 | tail -4
.venv/bin/python -m pytest -q -m postgres --collect-only 2>&1 | tail -1
```

Expected (there is no Postgres here, so the tests do not fail; they skip in `pg_db`'s setup):
```
SKIPPED [1] backend/tests/test_onboarding_postgres.py:106: TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)
SKIPPED [2] backend/tests/test_onboarding_postgres.py:136: TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)
SKIPPED [1] backend/tests/test_onboarding_postgres.py:195: TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)
4 skipped in …s
```
and `9/808 tests collected (799 deselected) in …s` (1a's five Postgres tests plus these four; CI's `-m postgres` run selects the same nine).

Collection imports only names that 1a already has. The Task 2–7 names the tests reach at run time are checked here, since the tests themselves first run on CI:

```bash
PYTHONPATH=backend .venv/bin/python -c "
import inspect, repos.invites as i, repos.memberships as m
from api.main import create_app
print(hasattr(i, 'claim'), hasattr(m, 'ensure_membership'), 'reusable' in inspect.signature(i.create_invite).parameters)
paths = create_app().openapi()['paths']
print(sorted(p for p in paths if p in ('/churches', '/invites/accept', '/me')), 'post' in paths.get('/churches', {}), 'post' in paths.get('/invites/accept', {}))
" 2>&1 | tail -2
grep -nE "^from repos import|invites\.claim\(|memberships\.ensure_membership\(" backend/usecases/onboarding.py
grep -nE "import .*\b(claim|ensure_membership)\b" backend/usecases/onboarding.py; echo "direct imports: $?"
```

Expected:
- `True True True`
- `['/churches', '/invites/accept', '/me'] True True` (at `0295b37` the same command prints `False False False` and `['/me'] False False`)
- the `from repos import churches, invites, memberships` line, then at least one `invites.claim(` line and one `memberships.ensure_membership(` line (line numbers vary)
- `direct imports: 1` (no `from repos.invites import claim`, which the monkeypatch would not reach; clarification 40)

A mismatch belongs to the task that owns the name (Task 2 for the repos, Task 5 for the usecase imports, Tasks 6–7 for the routes). Fix it there, not in this file.

- [ ] **Step 3: Run the whole backend suite (agent)**

```bash
.venv/bin/python -m pytest -q | tail -1
```

Expected: `799 passed, 9 skipped in …s` (Task 7's `799 passed, 5 skipped` plus these four skips).

- [ ] **Step 4: Commit (agent)**

```bash
git add backend/tests/test_onboarding_postgres.py
git commit -m "Tests: onboarding accept races and seed timing on Postgres (S Testing 1b, AC8, Risk 3)" -m "Two users racing for one single-use invite (one joins, one gets used),
one user double-accepting a single-use and a reusable invite (both 200,
one membership, exactly one already_member false), and a POST /churches
that copies a 700-row catalog within 3 s. A barrier inside
repos.invites.claim / repos.memberships.ensure_membership holds both
requests until each has passed the invite checks, so the second one takes
the claim-0-rows or ON CONFLICT DO NOTHING path; the tests assert the real
function returned [False, True]. The seed time is a UserWarning, which
pytest -m postgres -q prints in its warnings summary. Skipped locally; run
in CI's backend-postgres job." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Check the branch before the first push (agent, authorized by owner answer 5)**

The owner authorized this push and the draft PR in advance (Owner answers, item 5), so do not ask again. Everything else outward (marking the PR ready, merging, repo settings) still needs the owner's yes.

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline origin/main..HEAD
git diff --name-only origin/main...HEAD | grep -E '(^|/)\.env' ; echo "env files: $?"
gh auth status 2>&1 | grep -E "Logged in|not logged"
gh pr list -R bbrown62450/church --head claude/slice-1b-plan --state open --json number,isDraft,url
```

Expected, in order:
- `?? .claude/`
- the fetch prints nothing or only updated refs
- `0`
- the plan commit and the commits of Tasks 1–8, newest first, with no merge commit
- `env files: 1` (grep found nothing, so no `.env` file is on the branch)
- `Logged in to github.com account …`
- `[]`

- If the count is not `0` (`main` moved), run `git merge origin/main -m "Merge origin/main into claude/slice-1b-plan (Task 8)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`, then `.venv/bin/python -m pytest -q | tail -1` → `799 passed, 9 skipped` (if the merge brought new tests, the count differs by exactly those: stop and ask the owner if it differs any other way), and continue. On a merge conflict, stop and tell the owner.
- If `gh` is not logged in, stop and ask the owner to run `gh auth login` in their own terminal. The agent never handles a token.
- If an open PR already exists for the branch, do not open another. Use its number in Steps 8–10, and tell the owner if it is not a draft (do not convert it).

- [ ] **Step 6: Push the branch (agent, authorized by owner answer 5)**

```bash
git push -u origin claude/slice-1b-plan
```

Expected: `* [new branch]      claude/slice-1b-plan -> claude/slice-1b-plan` and `branch 'claude/slice-1b-plan' set up to track 'origin/claude/slice-1b-plan'.` If the push is rejected, stop and tell the owner. Never force-push.

- [ ] **Step 7: Open the draft PR (agent, authorized by owner answer 5)**

```bash
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-1b-plan \
  --title "Draft: Slice 1b onboarding: create a church, join by invite (CI Postgres checkpoint)" \
  --body-file - <<'EOF'
Draft for the CI Postgres checkpoint (owner answer 5 in the slice 1b plan). Not ready for review and not for merging: Tasks 9–19 (the frontend onboarding screens and the docs) are still to come on this branch, and Task 20 turns this into the real PR.

Plan: docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md. Spec: docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md (1b).

On the branch so far (Tasks 1–8):
- `backend/timezones.py` (`is_valid_timezone`); the engine sets `hide_parameters=True`, so a database error's traceback never carries a bound invite code or email; the idempotency store is reset between tests.
- Repos: `session=` parameters, `create_church_seeded`, `recent_owned_creations`, a bulk hymnal seed, `create_invite(reusable=)`, `find_by_code`, `claim`, `ensure_membership`, `as_utc`.
- `usecases/onboarding.py`: `create_church` with the 5-per-24-hours cap, `preview_invite`, `accept_invite` (invite checks 0–6, role clamp, the `claim` race guard). `repos.invites.accept_invite` is removed; the Streamlit create and accept tests are ported.
- Routes: `POST /churches` (201, Idempotency-Key, 429 with Retry-After), `POST /invites/preview`, `POST /invites/accept`; the OpenAPI snapshot and `schema.d.ts` regenerated.
- `backend/tests/test_onboarding_postgres.py` (`@pytest.mark.postgres`): two users racing for one single-use invite, one user double-accepting (single-use and reusable), and a church create that copies a 700-row catalog within 3 s. The time is in the backend-postgres job's "warnings summary" (`hymn seed: … rows in … ms`).

No migration: head stays `0004_invites_reusable`.

Tests so far: backend 697 → 799 passed, 5 → 9 skipped; frontend unchanged (126 passed in 23 files).

Production Streamlit (https://liturgy-frozen.streamlit.app/) runs from `streamlit-frozen` and is not deployed by this PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
gh pr view claude/slice-1b-plan -R bbrown62450/church --json number,url,isDraft,title
```

Expected: the create command prints `https://github.com/bbrown62450/church/pull/<N>`, and the view prints `"isDraft":true` and a title starting `Draft: Slice 1b onboarding`. Keep `<N>` for the next steps and for Task 20.

- [ ] **Step 8: Watch the checks (agent)**

Run this with the Bash tool's `run_in_background: true`. The watch can outlast the 10-minute foreground limit, and the tool re-invokes the agent when it exits:

```bash
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Expected when it exits: exit code 0 and every check `pass`:
- `backend` (the SQLite suite, `799 passed, 9 skipped`)
- `backend-postgres`
- `frontend` (lint, typecheck, the `gen:api` diff over Tasks 6–7's `schema.d.ts`, `126 passed`, build)
- the Vercel preview deployment

Any `fail` goes to Step 10. From 2026-10-19 GitHub's `ubuntu-latest` becomes Ubuntu 26. If a required job fails after that date, check the runner image before blaming 1b (1a minor T14-m2; also Task 20).

- [ ] **Step 9: Read the `backend-postgres` log and copy the seed timing (agent)**

```bash
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1b-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); echo "run $RUN"
gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "[0-9]+ passed"
JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Running (upgrade|downgrade)|No new upgrade operations detected|pg_smoke: OK|hymn seed: [0-9]+ rows in [0-9]+ ms|[0-9]+ (passed|failed|errors?)( |,)"
```

Shell variables do not carry between commands, so each line that needs `$RUN` or `$JOB` sets it itself. If the first line prints `run ` with no id, the run has not been listed yet: run it again.

Expected:
- jobs: `backend: success`, `backend-postgres: success`, `frontend: success`;
- backend log: `799 passed, 9 skipped in …s`;
- backend-postgres log, in this order:
  - the four `Running upgrade` lines `-> 0001_baseline` … `0003_lockdown -> 0004_invites_reusable` (1b adds no revision);
  - `No new upgrade operations detected.`;
  - the four `Running downgrade` lines, then the four upgrades again;
  - `pg_smoke: OK`;
  - one line ending `UserWarning: hymn seed: 700 rows in <ms> ms` (the source line under it prints `{n}`/`{ms}` literally, so the regex skips it);
  - `9 passed, 799 deselected, 1 warning in …s`.

The `9 passed` covers 1a's five tests (`test_migrations.py`'s three `0003` tests, `test_api_app.py::test_rls_check_names_tables_without_rls` and `test_identity.py::test_concurrent_first_requests_on_postgres_both_succeed_with_one_id`) and this task's four. Note `<ms>` and the run id for Step 10's report. Task 20 copies the final run's line into the PR body.

- [ ] **Step 10: Fix any failure in its owning task, then report (agent)**

If everything in Steps 8–9 matched, go to the report below. Otherwise read the failing step's log:

```bash
gh run view <run-id> -R bbrown62450/church --log-failed | tail -80
```

and fix it in the task that owns it:

| Failing test or step | Owning task (files) |
|---|---|
| `test_two_users_race_single_use` or `test_same_user_double_accept[*]` errors with `BrokenBarrierError` after ~10 s | a request never reached the patched function. Task 5 (`usecases/onboarding.py` does not call `invites.claim` / `memberships.ensure_membership` through the module, clarification 40), or a 4xx before the barrier (read the other response: Task 4's `_evaluate`) |
| `assert sorted(claims) == [False, True]` shows `[True, True]` | Task 2 (`repos/invites.py::claim` lacks `accepted_at IS NULL` in its WHERE, or does not return `rowcount == 1`) |
| a 500 with `IntegrityError` on `memberships_pkey`, or `inserted` `[True, True]` | Task 2 (`repos/memberships.py::ensure_membership` must use `insert_ignore` and `rowcount == 1`) |
| the loser gets 200, or the same user gets 400 `used` | Task 5 (the `s.refresh(inv)` / `accepted_by` branch; `claim` must use `synchronize_session=False`, clarification 4) |
| `test_create_church_700_row_catalog_under_3s`: status or `n == 700` | Task 2 (`repos/hymns.py::seed_church_from_catalog`, `create_church_seeded`), Task 3 (usecase) or Task 6 (route) |
| `test_create_church_700_row_catalog_under_3s`: only the `elapsed < 3.0` assertion | first `gh run rerun <run-id> -R bbrown62450/church --failed` once (a slow runner). If it fails again, stop and tell the owner both timings: S Risk 3's remedy (`INSERT … SELECT gen_random_uuid(), … FROM hymn_catalog` on Postgres) is a design change, and the owner decides |
| a `pg_db` setup error, or any of 1a's five Postgres tests | 1b changed only the engine kwargs (Task 1, `hide_parameters`) under them. Check that first, then report to the owner before changing anything else |
| `backend` job | the task that owns the failing test file (File Structure names it) |
| `frontend` job (`API types match the OpenAPI snapshot`) | Task 6 or Task 7 (rerun `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)` and commit both files) |
| any other `frontend` failure, or the Vercel preview | nothing else in Tasks 1–8 touches `frontend/`: report to the owner before changing anything |

For each fix:
1. Reproduce it locally first, wherever SQLite can show it (for example `.venv/bin/python -m pytest -q backend/tests/test_usecase_onboarding.py 2>&1 | tail -3`, where Task 5's claim-lost tests use the same code path).
2. Change only the owning task's files.
3. Run `.venv/bin/python -m pytest -q | tail -1` → `799 passed, 9 skipped`.
4. Commit with the subject `Fix: <what> (Task <n>, CI Postgres checkpoint)` and the `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` trailer, staging files by name.
5. Have that task re-reviewed (its plan section against the fix's diff) before Task 9.
6. Run `git push` (never `--force`) and repeat Steps 8–9.

An infrastructure failure with no test output (a service container that never became healthy, a timed-out `pip install` or `npm ci`) gets one `gh run rerun <run-id> -R bbrown62450/church --failed` before it counts as a failure.

Report to the owner in one line, then start Task 9: "Draft PR #<N> (<url>): backend-postgres green: 9 passed, including the invite races; hymn seed: 700 rows in <ms> ms on CI Postgres (budget 3 s)." Do not run `gh pr ready`. The PR stays a draft until Task 20 and the owner's yes.

Expected counts after this task: backend `799 passed, 9 skipped` locally (CI `backend-postgres`: `9 passed, 799 deselected, 1 warning`); frontend unchanged at `126 passed` in 23 files.
### Task 9: Client libraries: the idempotency key tracker, the post-login path, time zones, toast text (S Storage and URL helpers, S API client and query layer `lib/idempotency.ts`; F §1.6, §4.3; 1b clarifications 22, 24, 43, 46)

This task adds the four small pure modules the onboarding screens build on, each with its unit tests, and no screen yet. `lib/idempotency.ts` holds the create form's `Idempotency-Key` (one tracker per form mount; Task 16), plus `settleOutcome`, the single place that maps a thrown error to a tracker outcome (Task 16, and 5b later). `lib/post-login.ts` remembers where to go after Google sign-in for 10 minutes (Task 10 stores it on `/login`, Task 11's `(signed-in)` layout follows it, Task 15's `/join` clears it). `lib/timezones.ts` lists the browser's zones and picks the default (Tasks 12, 16, 17). `errorToastMessage` in `lib/api/errors.ts` gives a toast the long network sentence S asks for, while `ErrorState` keeps `describeError`'s short one (Tasks 14, 16). All new tests are `*.test.ts`, so they run in Vitest's Node `unit` project (`vitest.config.ts:17-19`): the post-login test stubs `window` with an in-memory `sessionStorage` exactly as `storage.test.ts:14-43` does, and the time-zone test stubs `Intl.supportedValuesOf` and `Intl.DateTimeFormat().resolvedOptions()` and never depends on the runner's zone (Global Constraints). The backend does not change.

Three choices made here that S leaves open (none is visible to anyone):
- `storePostLoginPath` also runs `safeInternalPath` and stores nothing for a rejected path. Its callers validate first (Task 10's `/login`), so this is a second check; it does not clear an existing value (1b clarification 39: `/login` never clears).
- `peekPostLoginPath` treats a stored time in the future (a clock moved back) as expired, so a value can never outlive its 10 minutes. It never clears anything (StrictMode's double effects stay harmless); clearing is Task 11's and Task 15's job.
- `defaultTimezone(null)` (no list: the combobox's text-input fallback) returns `America/New_York`: S says "browser zone when listed", and with no list nothing is listed.

**Files:**
- Create: `frontend/src/lib/idempotency.ts`
- Create: `frontend/src/lib/post-login.ts`
- Create: `frontend/src/lib/timezones.ts`
- Modify: `frontend/src/lib/api/errors.ts` (append after line 86, the closing `}` of `describeError`: `errorToastMessage`)
- Test: `frontend/src/lib/idempotency.test.ts` (new, 7 tests)
- Test: `frontend/src/lib/post-login.test.ts` (new, 4 tests)
- Test: `frontend/src/lib/timezones.test.ts` (new, 4 tests)
- Test: `frontend/src/lib/api/errors.test.ts` (lines 3-4, the imports; append after line 48: 2 tests)

**Interfaces:**
- Consumes:
  - `ApiError` (`frontend/src/lib/api/client.ts:12-30`: `status: number`, `code: ApiErrorCode`, `message`, `requestId?`, `retryAfterSeconds?`, `fields?`, `details?`; client codes `network_error`, `timeout`, `aborted` carry status 0, `:144-146`) and `NETWORK_MESSAGE = "Can't reach the server. Check your connection and try again."` (`client.ts:50`, test only).
  - `SESSION_KEYS.postLoginPath = "wsb:postLoginPath"`, `readSession(key): string | null`, `writeSession(key, value): void`, `removeSession(key): void` (`frontend/src/lib/storage.ts:8-11`, `:46-56`; all no-ops or null on the server and when storage throws).
  - `safeInternalPath(raw: unknown): string | null` (`frontend/src/lib/urls.ts:32-42`).
  - `describeError(e: unknown): string` (`frontend/src/lib/api/errors.ts:79-86`).
- Produces (all later users are named):
  - `frontend/src/lib/idempotency.ts`:
    - `type SettleOutcome = "success" | "client_error" | "uncertain"`; `type KeyTracker = { keyFor(body: unknown): string; settle(outcome: SettleOutcome): void }`.
    - `stableStringify(value: unknown): string`: `JSON.stringify` with object keys sorted at every depth (arrays keep their order).
    - `createKeyTracker({ fingerprint = stableStringify }: { fingerprint?: (body: unknown) => string } = {}): KeyTracker`. `keyFor` returns the pending key when `fingerprint(body)` equals the pending fingerprint, else a new `crypto.randomUUID()` (which replaces the pending one). `settle("success")` and `settle("client_error")` drop the pending key; `settle("uncertain")` keeps it. Later users: Task 16 (`CreateChurchForm`, one tracker per mount in a ref), 5b (`createSendKeyTracker`).
    - `settleOutcome(e: unknown): "client_error" | "uncertain"`: `ApiError` with `400 <= status <= 499` → `"client_error"`; status 0, a 5xx or any non-`ApiError` → `"uncertain"` (1b clarification 46). Later users: Task 16, 5b.
  - `frontend/src/lib/post-login.ts`:
    - `POST_LOGIN_TTL_MS = 10 * 60_000`.
    - `storePostLoginPath(path: string, now: number = Date.now()): void`: writes `JSON.stringify({ path, at: now })` to `wsb:postLoginPath` (the shape 1a's `use-sign-out.test.tsx:28` seeds) when `safeInternalPath(path)` accepts it; otherwise does nothing. Later user: Task 10 (`/login`).
    - `peekPostLoginPath(now: number = Date.now()): string | null`: the stored path when the value parses as `{path, at}` with a finite numeric `at`, `0 <= now - at < POST_LOGIN_TTL_MS` and `safeInternalPath(path)` accepts it; else null. Never writes. Later users: Task 10 (test), Task 11 (`(signed-in)` layout).
    - `clearPostLoginPath(): void`: `removeSession("wsb:postLoginPath")`. Later users: Task 11, Task 15 (`/join` mount).
  - `frontend/src/lib/timezones.ts`:
    - `FALLBACK_TIMEZONE = "America/New_York"`.
    - `listTimezones(): string[] | null`: `Intl.supportedValuesOf("timeZone")`, or null when that function is missing, throws or returns an empty list. Later users: Task 12 (`TimezoneCombobox`), Task 16, 6a.
    - `browserTimezone(): string | null`: `new Intl.DateTimeFormat().resolvedOptions().timeZone`, or null when it throws or is empty.
    - `defaultTimezone(list: string[] | null): string`: the browser zone when `list` contains it, else `FALLBACK_TIMEZONE`. Later users: Task 16, Task 17 (test: the browser zone preselected).
    - `timezoneLabel(id: string): string`: `id.replaceAll("_", " ")`. Later user: Task 12.
  - `frontend/src/lib/api/errors.ts`: `errorToastMessage(e: unknown): string`: `e.message` for an `ApiError` whose code is `network_error`, `timeout` or `aborted`; else `describeError(e)` (1b clarification 24). Later users: Task 14 (accept toast on network/5xx), Task 16 (create toast).

Counts after this task: backend **799 passed, 9 skipped** (unchanged since Task 8); frontend **143 passed in 26 files** (126 in 23 + 17: idempotency 7, post-login 4, timezones 4, errors 2; three new files).

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
ls frontend/src/lib/idempotency.ts frontend/src/lib/post-login.ts frontend/src/lib/timezones.ts 2>&1 | grep -c "No such file"
grep -c "errorToastMessage" frontend/src/lib/api/errors.ts
```

**Expected:** `git status --short` lists only `?? .claude/`; the last commit is Task 8's; `Test Files  23 passed (23)` and `Tests  126 passed (126)` (Tasks 1–8 add no frontend test; Tasks 6 and 7 only regenerate `openapi.json` and `schema.d.ts`); then `3` (none of the three modules exists); then `0`. If the frontend counts differ, stop and ask.

- [ ] **Step 2 (agent): Write the failing tests**

Create `frontend/src/lib/idempotency.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { createKeyTracker, settleOutcome, stableStringify } from "./idempotency";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const BODY = { name: "New Life", timezone: "America/Chicago" };

describe("createKeyTracker", () => {
  it("gives the same body the same UUID key until it is settled (a double tap while in flight)", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    expect(first).toMatch(UUID);
    expect(tracker.keyFor({ ...BODY })).toBe(first);
    expect(tracker.keyFor(BODY)).toBe(first);
  });

  it("keeps the key after an uncertain outcome, so an identical retry can replay", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    tracker.settle("uncertain");
    expect(tracker.keyFor(BODY)).toBe(first);
    tracker.settle("uncertain");
    expect(tracker.keyFor(BODY)).toBe(first);
  });

  it("drops the key after a client error", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    tracker.settle("client_error");
    const second = tracker.keyFor(BODY);
    expect(second).toMatch(UUID);
    expect(second).not.toBe(first);
  });

  it("drops the key after a success", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    tracker.settle("success");
    const second = tracker.keyFor(BODY);
    expect(second).toMatch(UUID);
    expect(second).not.toBe(first);
  });

  it("gives a changed body a new key, even while the first one is pending", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    tracker.settle("uncertain");
    const edited = tracker.keyFor({ ...BODY, name: "New Life Church" });
    expect(edited).toMatch(UUID);
    expect(edited).not.toBe(first);
    expect(tracker.keyFor({ ...BODY, name: "New Life Church" })).toBe(edited);
  });
});

describe("stableStringify", () => {
  it("ignores object key order at every depth, so a reordered body keeps its key", () => {
    const a = { b: 1, a: { d: [2, { f: 1, e: 0 }], c: "x" } };
    const b = { a: { c: "x", d: [2, { e: 0, f: 1 }] }, b: 1 };
    expect(stableStringify(a)).toBe('{"a":{"c":"x","d":[2,{"e":0,"f":1}]},"b":1}');
    expect(stableStringify(b)).toBe(stableStringify(a));
    expect(stableStringify([3, "x", null])).toBe('[3,"x",null]');

    const tracker = createKeyTracker();
    const first = tracker.keyFor({ name: "Grace", timezone: "Europe/London" });
    expect(tracker.keyFor({ timezone: "Europe/London", name: "Grace" })).toBe(first);
  });
});

describe("settleOutcome", () => {
  it("maps any 4xx to client_error and everything else to uncertain", () => {
    const cases: [unknown, "client_error" | "uncertain"][] = [
      [new ApiError(400, "invite_rejected", "Invalid invite code."), "client_error"],
      [new ApiError(422, "invalid_request", "Unknown timezone.", { fields: { timezone: "Unknown timezone." } }), "client_error"],
      [
        new ApiError(429, "rate_limited", "You've created 5 churches in the last 24 hours. Try again later.", {
          retryAfterSeconds: 60,
        }),
        "client_error",
      ],
      [new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again."), "uncertain"],
      [new ApiError(0, "timeout", "This is taking too long. Try again."), "uncertain"],
      [new ApiError(0, "aborted", "The request was cancelled."), "uncertain"],
      [new ApiError(500, "internal_error", "Something went wrong."), "uncertain"],
      [new ApiError(503, "db_unavailable", "The database is not reachable."), "uncertain"],
      [new Error("boom"), "uncertain"],
    ];
    for (const [error, outcome] of cases) {
      expect(settleOutcome(error), String(error)).toBe(outcome);
    }
  });
});
```

Create `frontend/src/lib/post-login.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST_LOGIN_TTL_MS, clearPostLoginPath, peekPostLoginPath, storePostLoginPath } from "./post-login";
import { SESSION_KEYS, readSession, writeSession } from "./storage";

/** A plain in-memory Storage: the unit project runs in Node, which has no sessionStorage. */
function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (key) => data.get(key) ?? null,
    key: (index) => [...data.keys()][index] ?? null,
    removeItem: (key) => {
      data.delete(key);
    },
    setItem: (key, value) => {
      data.set(key, String(value));
    },
  };
}

/** Midday UTC on 2026-09-28, in milliseconds. */
const AT = Date.UTC(2026, 8, 28, 12, 0, 0);

beforeEach(() => {
  vi.stubGlobal("window", { sessionStorage: memoryStorage(), localStorage: memoryStorage() });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("post-login path", () => {
  it("stores {path, at}, peeks without clearing, and clears", () => {
    storePostLoginPath("/join", AT);
    expect(readSession(SESSION_KEYS.postLoginPath)).toBe(JSON.stringify({ path: "/join", at: AT }));

    expect(peekPostLoginPath(AT + 60_000)).toBe("/join");
    expect(peekPostLoginPath(AT + 60_000)).toBe("/join");

    clearPostLoginPath();
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(peekPostLoginPath(AT + 60_000)).toBeNull();
  });

  it("expires 10 minutes after it was stored, and ignores a time in the future", () => {
    expect(POST_LOGIN_TTL_MS).toBe(600_000);
    storePostLoginPath("/welcome", AT);
    expect(peekPostLoginPath(AT)).toBe("/welcome");
    expect(peekPostLoginPath(AT + POST_LOGIN_TTL_MS - 1)).toBe("/welcome");
    expect(peekPostLoginPath(AT + POST_LOGIN_TTL_MS)).toBeNull();
    expect(peekPostLoginPath(AT - 1)).toBeNull();
  });

  it("ignores a stored path that safeInternalPath rejects, and never stores one", () => {
    for (const path of ["//evil.example/x", "/joinx", "/join?code=abc", "https://evil.example/join"]) {
      writeSession(SESSION_KEYS.postLoginPath, JSON.stringify({ path, at: AT }));
      expect(peekPostLoginPath(AT + 1_000), path).toBeNull();
    }

    clearPostLoginPath();
    storePostLoginPath("https://evil.example/join", AT);
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
  });

  it("ignores malformed JSON and a value of the wrong shape", () => {
    // "/builder" is the raw string 1a's church-layout test seeds (church-layout.test.tsx:302).
    for (const raw of ["/builder", "{", "null", "[]", '"/join"', '{"path":"/join"}', '{"path":"/join","at":"0"}']) {
      writeSession(SESSION_KEYS.postLoginPath, raw);
      expect(peekPostLoginPath(AT), raw).toBeNull();
    }
  });
});
```

Create `frontend/src/lib/timezones.test.ts`:

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { FALLBACK_TIMEZONE, browserTimezone, defaultTimezone, listTimezones, timezoneLabel } from "./timezones";

// Never depend on the runner's zone (CI's is UTC, a laptop's is local): stub both Intl calls.
const REAL_OPTIONS = new Intl.DateTimeFormat().resolvedOptions();
const LIST = ["America/Chicago", "America/New_York", "Asia/Calcutta", "Europe/London"];

function stubBrowserZone(timeZone: string): void {
  vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({ ...REAL_OPTIONS, timeZone });
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("time zones", () => {
  it("defaults to the browser zone when it is listed", () => {
    vi.spyOn(Intl, "supportedValuesOf").mockReturnValue(LIST);
    stubBrowserZone("America/Chicago");
    expect(listTimezones()).toEqual(LIST);
    expect(browserTimezone()).toBe("America/Chicago");
    expect(defaultTimezone(listTimezones())).toBe("America/Chicago");
  });

  it("falls back to America/New_York when the browser zone is not listed or unknown", () => {
    expect(FALLBACK_TIMEZONE).toBe("America/New_York");
    // ICU's list has no UTC, which is what CI's runner reports.
    stubBrowserZone("UTC");
    expect(defaultTimezone(LIST)).toBe("America/New_York");
    // No list (the text-input fallback): nothing is listed, so the fallback.
    expect(defaultTimezone(null)).toBe("America/New_York");
    vi.restoreAllMocks();
    vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockImplementation(() => {
      throw new RangeError("no zone");
    });
    expect(browserTimezone()).toBeNull();
    expect(defaultTimezone(LIST)).toBe("America/New_York");
  });

  it("returns null when Intl.supportedValuesOf is missing, throws or lists nothing", () => {
    vi.stubGlobal("Intl", { DateTimeFormat: Intl.DateTimeFormat });
    expect(listTimezones()).toBeNull();
    vi.unstubAllGlobals();

    vi.spyOn(Intl, "supportedValuesOf").mockImplementation(() => {
      throw new RangeError("Invalid key : timeZone");
    });
    expect(listTimezones()).toBeNull();

    vi.spyOn(Intl, "supportedValuesOf").mockReturnValue([]);
    expect(listTimezones()).toBeNull();
  });

  it("labels a zone by its id with underscores as spaces", () => {
    expect(timezoneLabel("America/New_York")).toBe("America/New York");
    expect(timezoneLabel("America/Argentina/Buenos_Aires")).toBe("America/Argentina/Buenos Aires");
    expect(timezoneLabel("Europe/London")).toBe("Europe/London");
  });
});
```

In `frontend/src/lib/api/errors.test.ts`, replace lines 3-4:

```ts
import { ApiError } from "./client";
import { describeError, isNoChurchAccess } from "./errors";
```

with:

```ts
import { ApiError, NETWORK_MESSAGE } from "./client";
import { describeError, errorToastMessage, isNoChurchAccess } from "./errors";
```

and append after line 48 (the closing `});` of `describe("describeError", …)`), keeping one blank line between the blocks:

```ts
describe("errorToastMessage", () => {
  it("uses the full sentence for a network error, a timeout or a cancel", () => {
    expect(errorToastMessage(new ApiError(0, "network_error", NETWORK_MESSAGE))).toBe(
      "Can't reach the server. Check your connection and try again.",
    );
    expect(errorToastMessage(new ApiError(0, "timeout", "This is taking too long. Try again."))).toBe(
      "This is taking too long. Try again.",
    );
    expect(errorToastMessage(new ApiError(0, "aborted", "The request was cancelled."))).toBe("The request was cancelled.");
  });

  it("falls back to describeError: a 5xx reference, a 4xx message, a generic line", () => {
    const withRef = new ApiError(500, "internal_error", "Something went wrong.", { requestId: "0123456789abcdef" });
    expect(errorToastMessage(withRef)).toBe("Something went wrong. (Ref: 01234567)");
    expect(errorToastMessage(new ApiError(503, "db_unavailable", "The database is not reachable."))).toBe(
      "Something went wrong.",
    );
    expect(errorToastMessage(new ApiError(400, "invite_rejected", "This invite has expired."))).toBe(
      "This invite has expired.",
    );
    expect(errorToastMessage(new TypeError("x is undefined"))).toBe("Something went wrong.");
  });
});
```

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
(cd frontend && npx vitest run src/lib/idempotency.test.ts src/lib/post-login.test.ts src/lib/timezones.test.ts src/lib/api/errors.test.ts 2>&1 | grep -E "Cannot find module|is not a function|Test Files|Tests ")
```

**Expected** (paths shortened to `…`):

```
     → (0 , errorToastMessage) is not a function
     → (0 , errorToastMessage) is not a function
Error: Cannot find module './idempotency' imported from '…/frontend/src/lib/idempotency.test.ts'
Error: Cannot find module './post-login' imported from '…/frontend/src/lib/post-login.test.ts'
Error: Cannot find module './timezones' imported from '…/frontend/src/lib/timezones.test.ts'
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
TypeError: (0 , errorToastMessage) is not a function
TypeError: (0 , errorToastMessage) is not a function
 Test Files  4 failed (4)
      Tests  2 failed | 6 passed (8)
```

The three new files fail to load (their modules do not exist yet); in `errors.test.ts` the two new tests fail and the six existing ones still pass.

- [ ] **Step 4 (agent): Create `frontend/src/lib/idempotency.ts`**

```ts
/**
 * Idempotency keys for a POST that is safe to retry (F §1.6; S "API client and query layer").
 * A form holds one tracker per mount (in a ref), asks `keyFor(body)` on every submit and
 * reports how the request ended with `settle(...)`. The key is reused only while a request
 * with the identical body is in flight or its outcome is unknown (network error, timeout,
 * cancel, 5xx), so a retry replays the first response instead of creating a second church.
 * Any 2xx or 4xx, or a changed body, gets a new key. 5b's `createSendKeyTracker` is this
 * tracker with the draft as the fingerprint.
 */
import { ApiError } from "@/lib/api/client";

/** How a request ended: `success` (2xx), `client_error` (4xx) or `uncertain` (anything else). */
export type SettleOutcome = "success" | "client_error" | "uncertain";

export type KeyTracker = {
  /** The key to send with `body`: the pending key when the body is unchanged, else a new UUID. */
  keyFor(body: unknown): string;
  /** `success` and `client_error` drop the pending key; `uncertain` keeps it for an identical retry. */
  settle(outcome: SettleOutcome): void;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** `JSON.stringify` with object keys sorted at every depth, so key order never changes a fingerprint. */
export function stableStringify(value: unknown): string {
  return JSON.stringify(value, (_key, inner: unknown) =>
    isPlainObject(inner)
      ? Object.fromEntries(Object.keys(inner).sort().map((key) => [key, inner[key]]))
      : inner,
  );
}

export function createKeyTracker({
  fingerprint = stableStringify,
}: { fingerprint?: (body: unknown) => string } = {}): KeyTracker {
  let pending: { key: string; print: string } | null = null;
  return {
    keyFor(body) {
      const print = fingerprint(body);
      if (pending === null || pending.print !== print) {
        pending = { key: crypto.randomUUID(), print };
      }
      return pending.key;
    },
    settle(outcome) {
      if (outcome !== "uncertain") pending = null;
    },
  };
}

/**
 * The `settle` outcome for a failed request (1b clarification 46): a 4xx `ApiError` is a
 * `client_error` (the server answered and stored nothing that a new key could duplicate);
 * status 0 (network error, timeout, cancel), a 5xx or any other thrown value is `uncertain`.
 */
export function settleOutcome(e: unknown): "client_error" | "uncertain" {
  return e instanceof ApiError && e.status >= 400 && e.status <= 499 ? "client_error" : "uncertain";
}
```

- [ ] **Step 5 (agent): Create `frontend/src/lib/post-login.ts`**

```ts
/**
 * The path to return to after sign-in (S "Storage and URL helpers", F §4.3). `/login` stores a
 * validated `next` before OAuth; the `(signed-in)` layout peeks it once `/me` has loaded and
 * clears it before following it (1b clarification 22); `/join` clears it on mount. It lives
 * in sessionStorage (`wsb:postLoginPath`, JSON `{path, at}`) for 10 minutes, and every read
 * goes back through `safeInternalPath`, so a stale, tampered or malformed value is ignored.
 */
import { SESSION_KEYS, readSession, removeSession, writeSession } from "@/lib/storage";
import { safeInternalPath } from "@/lib/urls";

export const POST_LOGIN_TTL_MS = 10 * 60_000;

/** Store `path` with the time it was stored. A path `safeInternalPath` rejects is not stored. */
export function storePostLoginPath(path: string, now: number = Date.now()): void {
  const safe = safeInternalPath(path);
  if (safe === null) return;
  writeSession(SESSION_KEYS.postLoginPath, JSON.stringify({ path: safe, at: now }));
}

/** The stored path if it is safe and less than 10 minutes old, else null. Never clears it. */
export function peekPostLoginPath(now: number = Date.now()): string | null {
  const raw = readSession(SESSION_KEYS.postLoginPath);
  if (raw === null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null) return null;
  const { path, at } = parsed as { path?: unknown; at?: unknown };
  if (typeof at !== "number" || !Number.isFinite(at)) return null;
  const age = now - at;
  if (age < 0 || age >= POST_LOGIN_TTL_MS) return null;
  return safeInternalPath(path);
}

export function clearPostLoginPath(): void {
  removeSession(SESSION_KEYS.postLoginPath);
}
```

- [ ] **Step 6 (agent): Create `frontend/src/lib/timezones.ts`**

`tsconfig.json` has `"lib": ["dom", "dom.iterable", "esnext"]`, so `Intl.supportedValuesOf` and `String.prototype.replaceAll` are typed; the `typeof … !== "function"` check is for browsers that lack it (the combobox then shows a text input).

```ts
/**
 * Time zones for the church form (S "Storage and URL helpers"; F §7.4 "Church timezone").
 * The list is the browser's own `Intl.supportedValuesOf("timeZone")` (ICU's canonical ids,
 * e.g. `Asia/Calcutta`; no `UTC` or `Etc/*`, 1b clarification 43). The server's
 * `timezones.is_valid_timezone` accepts every one of them. Without the list, the combobox
 * falls back to a plain text input.
 */

/** The default when the browser's zone is unknown or not in the list (S Flow A). */
export const FALLBACK_TIMEZONE = "America/New_York";

/** Every zone id the browser knows, or null when it cannot list them. */
export function listTimezones(): string[] | null {
  if (typeof Intl.supportedValuesOf !== "function") return null;
  try {
    const zones = Intl.supportedValuesOf("timeZone");
    return zones.length > 0 ? zones : null;
  } catch {
    return null;
  }
}

/** The browser's own zone id, or null when it reports none. */
export function browserTimezone(): string | null {
  try {
    const zone = new Intl.DateTimeFormat().resolvedOptions().timeZone;
    return typeof zone === "string" && zone !== "" ? zone : null;
  } catch {
    return null;
  }
}

/** The browser's zone when `list` has it, else `America/New_York` (also when there is no list). */
export function defaultTimezone(list: string[] | null): string {
  const zone = browserTimezone();
  return list !== null && zone !== null && list.includes(zone) ? zone : FALLBACK_TIMEZONE;
}

/** What the combobox shows for a zone: its id with `_` as a space (`America/New York`). */
export function timezoneLabel(id: string): string {
  return id.replaceAll("_", " ");
}
```

- [ ] **Step 7 (agent): Add `errorToastMessage` to `frontend/src/lib/api/errors.ts`**

Append after line 86 (the closing `}` of `describeError`, the end of the file), keeping one blank line before it. Nothing above changes, so `backend/tests/test_error_registry.py` (which reads the `ServerErrorCode` union up to its first `;`) is unaffected:

```ts
/**
 * The sentence a toast shows for a failed mutation (1b clarification 24). A network error,
 * timeout or cancel keeps its own full sentence, which says what to do ("Can't reach the
 * server. Check your connection and try again."); anything else is `describeError(e)`.
 * An inline `ErrorState` keeps `describeError`'s short "Can't reach the server.".
 */
export function errorToastMessage(e: unknown): string {
  if (e instanceof ApiError && (e.code === "network_error" || e.code === "timeout" || e.code === "aborted")) {
    return e.message;
  }
  return describeError(e);
}
```

- [ ] **Step 8 (agent): Run the tests to verify they pass, then the whole frontend and backend suites**

```bash
(cd frontend && npx vitest run src/lib/idempotency.test.ts src/lib/post-login.test.ts src/lib/timezones.test.ts src/lib/api/errors.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
.venv/bin/python -m pytest -q backend/tests/test_error_registry.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `Test Files  4 passed (4)` and `Tests  23 passed (23)` (7 + 4 + 4 + 8); then `Test Files  26 passed (26)` and `Tests  143 passed (143)` (126 + 17), `tsc --noEmit` and `eslint` print no errors; then `2 passed in <t>s`; then `799 passed, 9 skipped in <t>s` (no backend change; Task 8's line); `git status --short` lists exactly (plus `?? .claude/`):

```
 M frontend/src/lib/api/errors.test.ts
 M frontend/src/lib/api/errors.ts
?? frontend/src/lib/idempotency.test.ts
?? frontend/src/lib/idempotency.ts
?? frontend/src/lib/post-login.test.ts
?? frontend/src/lib/post-login.ts
?? frontend/src/lib/timezones.test.ts
?? frontend/src/lib/timezones.ts
```

If the post-login tests fail with every value `null`, the `window` stub is missing (the Node project has no `sessionStorage`; `vitest.config.ts:14` also turns Node's own web storage off). If `keyFor` throws `crypto is not defined`, the runner's Node is older than 19 (CI uses 22; this Mac 26). If a time-zone test passes locally but fails in CI, a stub was skipped and the test read the runner's zone.

- [ ] **Step 9 (agent): Commit**

```bash
git add frontend/src/lib/idempotency.ts frontend/src/lib/idempotency.test.ts \
        frontend/src/lib/post-login.ts frontend/src/lib/post-login.test.ts \
        frontend/src/lib/timezones.ts frontend/src/lib/timezones.test.ts \
        frontend/src/lib/api/errors.ts frontend/src/lib/api/errors.test.ts
git status --short
git commit -m "Frontend: idempotency key tracker, post-login path, time zones and toast text (F §1.6, §4.3; S Storage and URL helpers, API client and query layer; 1b clarifications 24, 46)

idempotency.ts: createKeyTracker keeps one Idempotency-Key per body until
the request settles; an uncertain outcome (network error, timeout, cancel,
5xx) keeps it for an identical retry, a 2xx, a 4xx or a changed body gets a
new one. stableStringify sorts object keys; settleOutcome maps a thrown
error to client_error (4xx) or uncertain. post-login.ts stores {path, at}
in wsb:postLoginPath and returns it for 10 minutes, through
safeInternalPath on every read. timezones.ts lists Intl.supportedValuesOf
zones (null without it), picks the browser zone when listed or
America/New_York, and labels ids with spaces. errorToastMessage gives a
toast the full network, timeout or cancel sentence and describeError for
the rest.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** before the commit `git status --short` lists the same eight paths staged (`M ` and `A ` in the first column) plus `?? .claude/`; afterwards `<sha> Frontend: idempotency key tracker, post-login path, time zones and toast text (F §1.6, §4.3; S Storage and URL helpers, API client and query layer; 1b clarifications 24, 46)`, and `git status --short` lists only `?? .claude/`.
### Task 10: Sign-in continuity: the proxy's `next`, `/login` `next` and `select_account`, `useSignOut({ selectAccount })`, sign-out ends on `/login` (S Routing, proxy and login; AC14 return-to-path half; clarifications 17, 21, 39)

This task makes a sign-in return to where it started. Three places change:

- **The proxy** (`lib/supabase/proxy.ts`) lets signed-out visitors open `/join`. It sends every other signed-out request to `/login?next=<path>`, or to `/login` with no `next` when the path is `/`. The redirect drops the original query string. That keeps an invite code, OAuth parameters or anything else out of `/login`. Today the proxy copies the query unchanged (`proxy.ts:35-38`).
- **`/login`** checks `?next=` with `safeInternalPath` and stores it as the post-login path (Task 9) just before Google starts. When `next` is missing or rejected, `/login` **leaves the stored value alone** (clarification 39). A failed or cancelled sign-in comes back as `/login?error=auth` with no `next` (`auth/callback/route.ts:12`), and clearing there would lose `/join`. `?select_account=1` adds `queryParams: { prompt: "select_account" }` (S Risk 8; checked by hand in Task 21, manual check 4). When the page mounts it calls the new `endSignOut()` (clarification 21).
- **`useSignOut`** gains `selectAccount?: boolean`. With it, `{ keepPendingInvite: true, next: "/join", selectAccount: true }` goes to `/login?next=%2Fjoin&select_account=1`. Task 14's `JoinInvite` uses this for the email-mismatch card button and its footer link "Use a different account" (clarification 18); `/join` (Task 15) renders `JoinInvite` and adds no footer of its own. The query is now built with `URLSearchParams`. For every path `safeInternalPath` accepts, this gives the same `next=%2F…` form that 1a's test pins (`/login?next=%2Fwelcome`). The new test compares parsed URLs, not S's literal `/login?next=/join&select_account=1` (clarification 17).

Why `endSignOut()`: 1a's signing-out flag is module state that only a full page load cleared (P1a clarification 27). 1b adds the first push navigations: the switcher item (Task 18) and the "← Back to …" link (Task 17). Here is the failure they allow. The user goes from `/` to `/welcome` (push), logs out, lands on `/login` (replace), then presses browser Back. That would show a client-side `/` with the flag still set, and the `(signed-in)` layout would show its skeleton for good. Every sign-out ends on `/login`, so clearing the flag when `/login` mounts fixes this. The `(signed-in)` layout is already unmounted by then. After Back, the layout loads `/me` again, gets a 401, and signs out cleanly. The header of `lib/auth.ts` (lines 4-9) is rewritten to say this. The `(signed-in)/layout.tsx:14-17` comment does not repeat the "cleared only by a full page load" wording, so that file is **not** touched here (Task 11 edits it).

**Files:**
- Modify: `frontend/src/test/mocks.ts` (`supabaseAuth.signInWithOAuth` spy + default in `resetTestMocks`)
- Modify: `frontend/src/lib/supabase/proxy.ts` (`/join` public; search reset; `?next=<pathname>` unless `/`)
- Modify: `frontend/src/lib/auth.ts` (header comment; `endSignOut`; `SignOutOptions.selectAccount`; the `/login` query)
- Modify: `frontend/src/app/login/page.tsx` (`next` stored, `select_account`, `endSignOut()` on mount)
- Modify: `frontend/src/lib/use-sign-out.test.tsx` (+1 test)
- Create: `frontend/src/lib/supabase/proxy.test.ts` (3 tests, `unit` project, own `vi.mock("@supabase/ssr")`)
- Create: `frontend/src/app/login/login.test.tsx` (5 tests, `dom` project)
- Test: the three test files above
- Not modified: `frontend/src/proxy.ts`, `frontend/src/app/auth/callback/route.ts` (still redirects to `/`; nothing new on the Supabase allow-list), `frontend/src/app/(signed-in)/layout.tsx`

**Interfaces:**
- Consumes:
  - Task 9 (`frontend/src/lib/post-login.ts`): `storePostLoginPath(path: string, now = Date.now()): void` (writes `wsb:postLoginPath` = JSON `{path, at}`), `peekPostLoginPath(now = Date.now()): string | null` (tests only here).
  - 1a: `safeInternalPath(raw: unknown): string | null` (`lib/urls.ts`); `readSession(key)`, `SESSION_KEYS.postLoginPath` (`lib/storage.ts`); `beginSignOut()`, `isSigningOut()`, `resetSigningOutForTests()` (`lib/auth.ts`; `setup-dom.ts:99` still calls the reset after each DOM test); test harness `setTestPath`, `supabaseAuth`, `testRouter` (`test/mocks.ts`), `renderWithProviders` (`test/render.tsx`); `createServerClient` (`@supabase/ssr`), `NextRequest`/`NextResponse` (`next/server`).
- Produces:
  - `lib/supabase/proxy.ts`: module-private `PUBLIC_PATHS = new Set(["/login", "/auth/callback", "/join"])`. `updateSession(request: NextRequest)` keeps its signature; for a signed-out, non-public path it returns `NextResponse.redirect` (307) to `/login` with `url.search = ""`, then `searchParams.set("next", pathname)` when `pathname !== "/"`.
  - `lib/auth.ts`: `export function endSignOut(): void` (clears the flag and notifies subscribers; does nothing when the flag is down). `SignOutOptions.selectAccount?: boolean`. `useSignOut()(opts)` → `router.replace("/login")` or `router.replace("/login?" + URLSearchParams{ next?, select_account? })`. Later users: Task 14 (`JoinInvite`'s "Use a different Google account" button and its footer link "Use a different account") calls `signOut({ keepPendingInvite: true, next: "/join", selectAccount: true })`. Task 15's 401 subscriber calls `signOut({ keepPendingInvite: true, next: "/join" })`.
  - `app/login/page.tsx`: `LoginPage` runs `endSignOut()` in a mount effect. `LoginForm.signIn()` stores `safeInternalPath(searchParams.get("next"))` when it is not null and **never clears**. It calls `signInWithOAuth({ provider: "google", options: { redirectTo: origin + "/auth/callback" } })` and adds `queryParams: { prompt: "select_account" }` only when `select_account === "1"`. Copy is unchanged ("Sign in with Google", "Redirecting…", "Sign-in didn't complete. Please try again.").
  - `test/mocks.ts`: `supabaseAuth.signInWithOAuth: vi.fn()`, reset each test to resolve `{ data: {}, error: null }`. Later users: Task 15's `/join` tests if they tap through to `/login`.

- [ ] **Step 1 (agent): Check that Task 9 is in**

```bash
git log --oneline -2
grep -n "^export" frontend/src/lib/post-login.ts
grep -n "signInWithOAuth\|endSignOut\|selectAccount" frontend/src/test/mocks.ts frontend/src/lib/auth.ts frontend/src/app/login/page.tsx
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** Task 9's commit on top. `post-login.ts` exports `POST_LOGIN_TTL_MS`, `storePostLoginPath`, `peekPostLoginPath` and `clearPostLoginPath`. The second `grep` prints only `frontend/src/app/login/page.tsx:28:    const { error } = await createClient().auth.signInWithOAuth({` (no spy, no `endSignOut`, no `selectAccount` yet). Then `Test Files  26 passed (26)` and `Tests  143 passed (143)`. If either count differs, stop and ask.

- [ ] **Step 2 (agent): Give the test harness a `signInWithOAuth` spy (`frontend/src/test/mocks.ts`)**

`/login` calls `createClient().auth.signInWithOAuth`, and `setup-dom.ts` hands out `supabaseAuth` as `auth`. Without the spy the call throws `signInWithOAuth is not a function` as an unhandled error. Apply these three replacements.

Replace:

```ts
export const supabaseAuth = {
  getSession: vi.fn(),
  signOut: vi.fn(),
};
```

with:

```ts
export const supabaseAuth = {
  getSession: vi.fn(),
  signOut: vi.fn(),
  signInWithOAuth: vi.fn(),
};
```

Replace:

```ts
/** Back to defaults: path "/", a signed-in session, a successful local sign-out. */
```

with:

```ts
/**
 * Back to defaults: path "/", a signed-in session, a successful local sign-out and a
 * Google sign-in that starts without error (the real one then leaves the page).
 */
```

Replace:

```ts
  supabaseAuth.signOut.mockReset();
  supabaseAuth.signOut.mockResolvedValue({ error: null });
}
```

with:

```ts
  supabaseAuth.signOut.mockReset();
  supabaseAuth.signOut.mockResolvedValue({ error: null });
  supabaseAuth.signInWithOAuth.mockReset();
  supabaseAuth.signInWithOAuth.mockResolvedValue({ data: {}, error: null });
}
```

- [ ] **Step 3 (agent): Write the failing tests**

Create `frontend/src/lib/supabase/proxy.test.ts`:

```ts
import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { updateSession } from "./proxy";

// Node project: no setup-dom.ts here, so this file stubs the server client itself.
// `getUser()` resolving `{ user: null }` is a signed-out visitor.
const { getUser } = vi.hoisted(() => ({ getUser: vi.fn() }));
vi.mock("@supabase/ssr", () => ({ createServerClient: () => ({ auth: { getUser } }) }));

const ORIGIN = "https://wsb.example.test";

function visit(pathAndQuery: string): Promise<Response> {
  return updateSession(new NextRequest(new URL(pathAndQuery, ORIGIN)));
}

/** The redirect target as a URL, or null when the proxy let the request through. */
function redirectTarget(response: Response): URL | null {
  const location = response.headers.get("location");
  return location === null ? null : new URL(location);
}

beforeEach(() => {
  getUser.mockReset();
  getUser.mockResolvedValue({ data: { user: null }, error: null });
});

describe("updateSession (S Routing, proxy and login)", () => {
  it("lets a signed-out visitor through to /join with its code", async () => {
    const response = await visit("/join?code=x");

    expect(redirectTarget(response)).toBeNull();
    expect(response.headers.get("x-middleware-next")).toBe("1");
    expect(getUser).toHaveBeenCalledTimes(1);
  });

  it("sends a signed-out deep link to /login?next=<path>, dropping its query", async () => {
    const response = await visit("/builder?x=1");

    expect(response.status).toBe(307);
    const target = redirectTarget(response);
    expect(target?.origin).toBe(ORIGIN);
    expect(target?.pathname).toBe("/login");
    expect(target?.search).toBe("?next=%2Fbuilder");
  });

  it("sends a signed-out / to /login with no next", async () => {
    const response = await visit("/");

    expect(response.status).toBe(307);
    const target = redirectTarget(response);
    expect(target?.pathname).toBe("/login");
    expect(target?.search).toBe("");
  });
});
```

Create `frontend/src/app/login/login.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { beginSignOut, isSigningOut } from "@/lib/auth";
import { peekPostLoginPath, storePostLoginPath } from "@/lib/post-login";
import { readSession, SESSION_KEYS } from "@/lib/storage";
import { setTestPath, supabaseAuth } from "@/test/mocks";

import LoginPage from "./page";

/** Renders `/login` at `path` and taps "Sign in with Google". */
async function signInFrom(path: string): Promise<void> {
  setTestPath(path);
  const user = userEvent.setup();
  render(<LoginPage />);
  await user.click(screen.getByRole("button", { name: "Sign in with Google" }));
  await waitFor(() => expect(supabaseAuth.signInWithOAuth).toHaveBeenCalledTimes(1));
}

function callbackUrl(): string {
  return `${window.location.origin}/auth/callback`;
}

describe("/login (S Routing, proxy and login)", () => {
  it("stores an allow-listed next before it starts the Google sign-in", async () => {
    let storedWhenGoogleStarted: string | null = null;
    supabaseAuth.signInWithOAuth.mockImplementation(async () => {
      storedWhenGoogleStarted = peekPostLoginPath();
      return { data: {}, error: null };
    });

    await signInFrom("/login?next=%2Fjoin");

    expect(storedWhenGoogleStarted).toBe("/join");
    expect(supabaseAuth.signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: callbackUrl() },
    });
  });

  it("ignores a next that safeInternalPath rejects", async () => {
    await signInFrom("/login?next=%2F%2Fevil.example");

    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(supabaseAuth.signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: callbackUrl() },
    });
  });

  it("asks Google for its account chooser when select_account=1", async () => {
    await signInFrom("/login?next=%2Fjoin&select_account=1");

    expect(supabaseAuth.signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: callbackUrl(), queryParams: { prompt: "select_account" } },
    });
    expect(peekPostLoginPath()).toBe("/join");
  });

  it("clears the signing-out flag when it mounts (clarification 21)", () => {
    beginSignOut();
    expect(isSigningOut()).toBe(true);

    render(<LoginPage />);

    expect(isSigningOut()).toBe(false);
  });

  it("keeps a stored /join when a failed sign-in comes back without next (clarification 39)", async () => {
    storePostLoginPath("/join");
    const stored = readSession(SESSION_KEYS.postLoginPath);
    expect(stored).not.toBeNull();

    await signInFrom("/login?error=auth");

    expect(screen.getByText("Sign-in didn't complete. Please try again.")).toBeInTheDocument();
    expect(readSession(SESSION_KEYS.postLoginPath)).toBe(stored);
    expect(peekPostLoginPath()).toBe("/join");
  });
});
```

In `frontend/src/lib/use-sign-out.test.tsx`, add one test between the 401-path test and the first cookie test. Replace:

```tsx
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(isSigningOut()).toBe(true);
  });

  it("removes the Supabase auth cookies itself when signOut resolves with an error (owner-approved)", async () => {
```

with:

```tsx
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(isSigningOut()).toBe(true);
  });

  it("adds select_account=1 when asked, keeping the pending invite (S Flow B email mismatch; clarification 17)", async () => {
    seedSignedInTab();
    const pat = me();
    const { user } = renderWithProviders(
      <LogOut options={{ keepPendingInvite: true, next: "/join", selectAccount: true }} />,
      { me: pat, path: "/join" },
    );

    await user.click(screen.getByRole("button", { name: `Log out ${pat.user.email}` }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledTimes(1));
    const target = new URL(testRouter.replace.mock.calls[0][0], "http://localhost");
    expect(target.pathname).toBe("/login");
    expect([...target.searchParams]).toEqual([
      ["next", "/join"],
      ["select_account", "1"],
    ]);
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe("INVITE-CODE");
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(readStoredChurchId()).toBeNull();
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
  });

  it("removes the Supabase auth cookies itself when signOut resolves with an error (owner-approved)", async () => {
```

(The replaced block's first two lines appear only once. They end the "keeps the pending invite and returns to an allow-listed path when asked (the 401 path)" test at lines 98-100.)

- [ ] **Step 4 (agent): Run the tests to verify they fail**

```bash
(cd frontend && npx vitest run src/lib/supabase/proxy.test.ts src/app/login/login.test.tsx src/lib/use-sign-out.test.tsx 2>&1 | grep -E "×|→|Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | grep "error TS")
```

**Expected:** six failures:
- `× updateSession (S Routing, proxy and login) > lets a signed-out visitor through to /join with its code` → `expected URL { href: 'https://wsb.example.test/login?code=x', … } to be null`. Today `/join` is not public, and the redirect keeps `?code=x`.
- `× … > sends a signed-out deep link to /login?next=<path>, dropping its query` → `expected '?x=1' to be '?next=%2Fbuilder' // Object.is equality`.
- `× useSignOut > adds select_account=1 when asked, keeping the pending invite (S Flow B email mismatch; clarification 17)` → `expected [ [ 'next', '/join' ] ] to deeply equal [ [ 'next', '/join' ], …(1) ]`.
- `× /login (S Routing, proxy and login) > stores an allow-listed next before it starts the Google sign-in` → `expected null to be '/join' // Object.is equality`.
- `× … > asks Google for its account chooser when select_account=1` → `expected "spy" to be called with arguments: [ { provider: 'google', …(1) } ]`.
- `× … > clears the signing-out flag when it mounts (clarification 21)` → `expected true to be false // Object.is equality`.

Then `Test Files  3 failed (3)` and `Tests  6 failed | 7 passed (13)`. Seven tests already pass: the 4 old `useSignOut` tests, proxy `/`, and two `/login` tests. The two `/login` tests are "ignores a next …" and "keeps a stored /join …". Today's page stores nothing, so they pass now. They stay as guards: the new code must store only an accepted `next` and must never clear. Typecheck: `src/lib/use-sign-out.test.tsx(106,66): error TS2353: Object literal may only specify known properties, and 'selectAccount' does not exist in type 'SignOutOptions'.`

- [ ] **Step 5 (agent): Proxy: `/join` public, `next` only, query dropped (`frontend/src/lib/supabase/proxy.ts`)**

Replace the whole file with:

```ts
import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

/** Paths a signed-out visitor may open; `/join` shows its own sign-in card (S Flow B). */
const PUBLIC_PATHS = new Set(["/login", "/auth/callback", "/join"]);

/**
 * Refresh the Supabase session cookie and send signed-out visitors to /login,
 * with `?next=<path>` for any path but `/` (S Routing, proxy and login). The
 * query is dropped: only the path goes to `/login`, which stores it after
 * `safeInternalPath` accepts it.
 */
export async function updateSession(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options),
          );
        },
      },
    },
  );

  // Must run before any redirect decision: it refreshes an expired session.
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const { pathname } = request.nextUrl;
  if (!user && !PUBLIC_PATHS.has(pathname)) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = "";
    if (pathname !== "/") url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }
  return response;
}
```

(The cookie handling and the `getUser()` call are unchanged from 1a.)

- [ ] **Step 6 (agent): `endSignOut`, `selectAccount` and the rewritten flag comment (`frontend/src/lib/auth.ts`)**

Apply these seven replacements.

Replace (header, lines 4-6):

```ts
 * The flag is module state: set once by `beginSignOut()` (Task 19's `useSignOut`
 * calls it first) and cleared only by a full page load, since every sign-in
 * comes back through the Google OAuth redirect. While it is set, no new API
```

with:

```ts
 * The flag is module state: set once by `beginSignOut()` (`useSignOut` calls it
 * first) and cleared by `endSignOut()` when `/login` mounts, or by a full page
 * load. Every sign-out ends on `/login`, so a browser Back into a cached
 * signed-in page finds the flag down and loads `/me` again (slice 1b
 * clarification 21). While it is set, no new API
```

Replace:

```ts
/** True from `beginSignOut()` until the next full page load. */
```

with:

```ts
/** True from `beginSignOut()` until `endSignOut()` or the next full page load. */
```

Replace:

```ts
/** `isSigningOut()` for rendering; the server snapshot is `false`. */
```

with:

```ts
/**
 * Ends a sign-out in this tab: clears the flag. `/login` calls it when it
 * mounts, after `useSignOut` has finished and the signed-in layouts are gone.
 * Idempotent.
 */
export function endSignOut(): void {
  if (!signingOut) return;
  signingOut = false;
  notify();
}

/** `isSigningOut()` for rendering; the server snapshot is `false`. */
```

Replace:

```ts
  /** Where to return after sign-in; used only when `safeInternalPath` accepts it. */
  next?: string;
};
```

with:

```ts
  /** Where to return after sign-in; used only when `safeInternalPath` accepts it. */
  next?: string;
  /** Adds `select_account=1`, so `/login` asks Google for its account chooser (S Flow B email mismatch). */
  selectAccount?: boolean;
};
```

Replace (in the `useSignOut` doc comment):

```ts
 * `?next=` when `next` is an allow-listed path. Never rejects. Needs no
```

with:

```ts
 * `?next=` when `next` is an allow-listed path and `select_account=1` when
 * `selectAccount` is set. Never rejects. Needs no
```

Replace:

```ts
    async ({ keepPendingInvite = false, next }: SignOutOptions = {}) => {
```

with:

```ts
    async ({ keepPendingInvite = false, next, selectAccount = false }: SignOutOptions = {}) => {
```

And replace:

```ts
      const back = next === undefined ? null : safeInternalPath(next);
      router.replace(back ? `/login?next=${encodeURIComponent(back)}` : "/login");
```

with:

```ts
      const back = next === undefined ? null : safeInternalPath(next);
      const query = new URLSearchParams();
      if (back) query.set("next", back);
      if (selectAccount) query.set("select_account", "1");
      const search = query.toString();
      router.replace(search ? `/login?${search}` : "/login");
```

`resetSigningOutForTests` stays as it is: `setup-dom.ts`, `auth.test.ts` and `client.test.ts` still use it.

- [ ] **Step 7 (agent): `/login` stores `next`, passes `select_account`, ends the sign-out (`frontend/src/app/login/page.tsx`)**

Replace the whole file with:

```tsx
"use client";

/**
 * `/login` (S Routing, proxy and login; F §4.3). Google sign-in through Supabase.
 *
 * - `?next=` is stored as the post-login path, only when `safeInternalPath`
 *   accepts it, just before Google starts; the `(signed-in)` layout follows it
 *   after `/auth/callback` lands on `/`. Without a valid `next` the stored path
 *   is left alone: a failed or cancelled sign-in comes back as
 *   `/login?error=auth` with no `next`, and must not lose `/join`
 *   (clarification 39).
 * - `?select_account=1` asks Google for its account chooser (the invite
 *   email-mismatch path, S Flow B).
 * - Mounting ends any sign-out in this tab (`endSignOut()`, clarification 21).
 */
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { endSignOut } from "@/lib/auth";
import { storePostLoginPath } from "@/lib/post-login";
import { createClient } from "@/lib/supabase/client";
import { safeInternalPath } from "@/lib/urls";

function LoginForm() {
  const searchParams = useSearchParams();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const signInError = searchParams.get("error")
    ? "Sign-in didn't complete. Please try again."
    : null;

  async function signIn() {
    setBusy(true);
    setError(null);
    const next = safeInternalPath(searchParams.get("next"));
    if (next) storePostLoginPath(next);
    const selectAccount = searchParams.get("select_account") === "1";
    const { error } = await createClient().auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        ...(selectAccount ? { queryParams: { prompt: "select_account" } } : {}),
      },
    });
    if (error) {
      setError(error.message);
      setBusy(false);
    }
  }

  const message = error ?? signInError;

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>Worship Service Builder</CardTitle>
        <CardDescription>Plan Sunday services with your church.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <Button className="w-full" onClick={signIn} disabled={busy}>
          {busy ? "Redirecting…" : "Sign in with Google"}
        </Button>
        {message && <p className="text-sm text-destructive">{message}</p>}
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  // Every sign-out ends on this page, so the flag comes down here: a browser
  // Back into a cached signed-in page then loads `/me` again instead of
  // showing the skeleton for good (clarification 21).
  useEffect(() => {
    endSignOut();
  }, []);

  return (
    <main className="flex min-h-dvh items-center justify-center p-4">
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
    </main>
  );
}
```

(The card markup, copy and `Suspense` boundary are unchanged from 1a. `useSearchParams` stays inside `Suspense`, as the build requires.)

- [ ] **Step 8 (agent): Run the tests, then the whole frontend suite**

```bash
(cd frontend && npx vitest run src/lib/supabase/proxy.test.ts src/app/login/login.test.tsx src/lib/use-sign-out.test.tsx 2>&1 | grep -E "✓|×|Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
grep -rn "cleared only by a full page load" frontend/src
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `✓ |unit| src/lib/supabase/proxy.test.ts (3 tests)`, `✓ |dom| src/app/login/login.test.tsx (5 tests)`, `✓ |dom| src/lib/use-sign-out.test.tsx (5 tests)`, `Test Files  3 passed (3)`, `Tests  13 passed (13)`. No `stderr`, `act(` or `Warning` lines. Then `Test Files  28 passed (28)` and `Tests  152 passed (152)` (143 + 9: proxy 3, login 5, use-sign-out 1; 26 + 2 new files). `tsc --noEmit` and `eslint` print nothing beyond their banners. The `grep` prints nothing (exit 1). The backend is unchanged at `799 passed, 9 skipped`.

- [ ] **Step 9 (agent): Commit**

```bash
git add frontend/src/lib/supabase/proxy.ts frontend/src/lib/supabase/proxy.test.ts \
        frontend/src/app/login/page.tsx frontend/src/app/login/login.test.tsx \
        frontend/src/lib/auth.ts frontend/src/lib/use-sign-out.test.tsx frontend/src/test/mocks.ts
git commit -m "Frontend: sign-in returns to the deep link; /login next and select_account; sign-out ends on /login (F §4.3, §4.2; S Routing, proxy and login)

The proxy lets signed-out visitors open /join and sends every other
signed-out path to /login?next=<path> (no next for /), dropping the
original query. /login stores an allow-listed next as the post-login path
just before Google starts and never clears it, so a failed or cancelled
sign-in (/login?error=auth) keeps /join (1b clarification 39);
select_account=1 passes prompt=select_account to Google. useSignOut gains
selectAccount for the invite email-mismatch path (clarification 17).
/login calls the new endSignOut() on mount, so a browser Back into a
cached signed-in page after Log out reloads /me instead of showing the
skeleton for good (clarification 21; supersedes 1a clarification 27's
slice 2 hand-off). The test harness gains a signInWithOAuth spy.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
```

**Expected:** `<sha> Frontend: sign-in returns to the deep link; /login next and select_account; sign-out ends on /login (F §4.3, §4.2; S Routing, proxy and login)`; `git status --short` then lists only `?? .claude/`. Do not push (Task 20 pushes Tasks 9–19 to the draft PR).

Tests after this task: backend `799 passed, 9 skipped` (unchanged); frontend `152 passed` (28 files).
### Task 11: `(signed-in)` layout follows the post-login path; one announced loading skeleton; a busy Retry (F §4.3; S Routing; AC14 return-to-path half; clarification 22; owner answer 4: 1a minors T22-m1, T22-m2, T23-m3)

The `(signed-in)` layout finishes AC14's return-to-path half. Task 10's `/login` stores an allow-listed `next` before Google starts. When the user comes back signed in, the auth callback sends them to `/`, and this layout sends them on to the stored path (for example `/join`). S puts the follow here and not in the root, because the `(church)` layout would first send a zero-church user to `/welcome` (S :481; T19 amends F §4.3's "the root reads, clears and follows").

It also takes the two small visible 1a leftovers the owner approved on 2026-09-28 (owner answer 4):
- **T22-m2.** While the full-page Retry runs, the error stays on screen and Retry is disabled, busy and spinning, so a repeat tap does nothing.
- **T23-m3.** One shared `ShellSkeleton` (`role="status"`, named "Loading") is used by both layouts. The `(church)` layout's own copy is deleted.
- **T22-m1.** The test 1a's final review asked for is added: a failed background `/me` refetch keeps the children with no Retry.

**Rules the code implements:**
1. The layout reads the stored path once, when it mounts, in a `useState` initializer. The target is known before the first render, so the children render only when no redirect is leaving the page. The server has no sessionStorage, so the server render and the hydration pass both render the skeleton. `/me` never has data on the hydration pass (there is no server prefetch), so the markup matches.
2. A stored path other than the current one keeps the skeleton up until the pathname changes. The page being left never mounts, never sends a request, and a zero-church user is never sent to `/welcome` on the way. An effect **clears the stored path first**, then calls `router.replace(target)` (clarification 22). A stored path equal to the current one is only cleared.
3. The effect re-reads the store each time it runs. StrictMode's repeated effect therefore finds nothing and does not call `replace` a second time. A path allowed by the allow-list but with no route yet (`/builder`, `/services`, `/settings`) redirects once, not on every visit for 10 minutes.
4. Arriving at the target inside `(signed-in)` (for example `/welcome`) keeps the same layout instance. A render-phase `setLeaving(null)` (React's "adjust state when a prop changes" pattern) then lets the children render. Coming back to `/` later does not redirect again, because the store is already empty.
5. The full-page Retry needs extra state because of how TanStack Query refetches. In TanStack Query 5.104.0, refetching an errored query **with no data** resets it to `status: "pending"` (`@tanstack/query-core/build/modern/query.js:486-495`, `fetchState`). 1a's layout then drops to the skeleton on the first tap, which is the flash T22-m2 describes. So on Retry the layout keeps the error that Retry was pressed on and shows it with `retrying={me.isFetching}` until the refetch settles. If the refetch succeeds, the children render. If it fails, the new error shows with Retry enabled again.
6. `ErrorState` renders Retry through `PendingButton` with `pendingLabel="Retry"`. The pending state adds the spinner, `disabled` and `aria-busy="true"` and keeps the label, so no new copy is introduced. The `(church)` body `ErrorState` is unchanged: it is not full-page, and T22-m2 named only the full-page Retry.

**Deviations from the outline (the code decides; each was verified in a throwaway worktree with a stand-in `lib/post-login.ts` identical to Task 9's):**
- **The outline says "effect-only check (never in render)".** The path is read in a `useState` initializer instead. The outline's design needs a synchronous `setState` in the effect (`setChecked(true)`), and `eslint` failed on it with `react-hooks/set-state-in-effect` (react-hooks v7 rules are at error; 1a's plan :11722 and :12467 keep to them). A ref cannot be read during render either (`react-hooks/refs`). The effect still does every side effect: clearing and `router.replace`. The initializer only reads the store.
- **The outline says "`ErrorState` gains `retrying?: boolean` … passed `me.isFetching`".** On its own this is never visible, for the reason in rule 5 (a throwaway probe showed Retry absent and the skeleton present during the refetch). The layout keeps the error that Retry was pressed on, as above.
- **The outline's test list does not include the layout's use of `retrying`.** 1a's 5xx test is extended to cover it: the error stays on screen, Retry is busy, and a second tap sends nothing. It stays one test.
- **The outline's T11 file list does not include `church-layout.test.tsx`.** Its zero-church test gets one assertion line, so the shared skeleton is proven announced on church pages too. It stays one test.
- **Task 9's `lib/post-login.ts` header says the layout "peeks it once `/me` has loaded".** Its one line is corrected to "reads it when it mounts" (Step 6).

**Visible changes (owner answer 4):**
- While a full-page Retry runs, the error stays on screen and Retry shows a spinner and ignores taps. Before, the page flashed the skeleton.
- On church pages the loading placeholder changes slightly:
  - the header bar is a fixed `w-48` bar, not a full-width one;
  - the avatar is `size-9`, not `size-8`;
  - the two cards sit in a `div`, not an `aria-busy` `<main>`.

  Screen readers now hear "Loading" there too.

`BodySkeleton` (the `(church)` body under a real header) is unchanged. T23-m2 (a StrictMode test of the `(church)` ref-based query removal) is deferred to slice 2 (clarification 49): this task changes only the skeleton import in that file.

Every shell command that names a `(signed-in)` path **quotes it**: zsh treats unquoted parentheses as glob grouping and fails with `no matches found`. The Vitest filters `signed-in-layout`, `error-state` and `church-layout` each match exactly one test file.

**Files:**
- Create: `frontend/src/components/app/shell-skeleton.tsx`
- Modify: `frontend/src/app/(signed-in)/layout.tsx` (whole file replaced; 83 → 103 lines)
- Modify: `frontend/src/app/(signed-in)/(church)/layout.tsx:30-31` (one import added), `:160-173` (the local `ShellSkeleton` and the blank line after it deleted)
- Modify: `frontend/src/components/app/error-state.tsx` (whole file replaced)
- Modify: `frontend/src/lib/post-login.ts` (Task 9's module header: one line)
- Test: `frontend/src/app/(signed-in)/signed-in-layout.test.tsx` (whole file replaced: 3 → 7 tests; 1a's 5xx test extended)
- Test: `frontend/src/components/app/error-state.test.tsx` (3 → 4 tests)
- Test: `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx:242` (one assertion added after it, in the zero-church test; still 15 tests)

**Interfaces:**
- Consumes:
  - Task 9 (`@/lib/post-login`): `peekPostLoginPath(now: number = Date.now()): string | null` (safe and under 10 minutes old, else null; never clears), `clearPostLoginPath(): void`, and, in tests, `storePostLoginPath(path: string, now: number = Date.now()): void` (writes `wsb:postLoginPath` = JSON `{path, at}` through `safeInternalPath`).
  - 1a: `useMe(opts?: { enabled?: boolean }): UseQueryResult<Me, ApiError>` (`@/lib/queries/me`; Task 13 later makes it spread `meQueryOptions(api)` without changing this signature). `useSigningOut()`, `isSigningOut()`, `useSignOut()` (`@/lib/auth`; Task 10 adds `selectAccount` and `endSignOut()`, not used here). `authEvents.onSignOutRequired(cb): () => void` (`@/lib/queries/auth-events`). `MeProvider` (`@/lib/me-context`). `ApiError` (`@/lib/api/client`). `usePathname`, `useRouter` (`next/navigation`; mocked in DOM tests by `setup-dom.ts`).
  - 1a: `PendingButton({ pending: boolean; pendingLabel?: string; …ButtonProps })` (`@/components/app/pending-button`; while pending: `disabled`, `aria-busy="true"`, a `Loader2Icon` spinner, then `pendingLabel`). `Skeleton` (`@/components/ui/skeleton`). `describeError` (`@/lib/api/errors`).
  - Test harness: `renderWithProviders(ui, { path?, queryClient? })` → `RenderResult & { user; queryClient }` (`rerender` keeps the wrapper). `setTestPath(path)`, `testRouter.replace`, `supabaseAuth.signOut`, `TEST_ACCESS_TOKEN` (`@/test/mocks`). `installFakeApi`, `api.set(route, handler)` (a handler may return a promise), `fakeError(status, code, message)` (Ref `4f9a2c1e`) (`@/test/fake-api`). `me()` (email `pat@example.com`) (`@/test/fixtures`). `keys.me()` (`@/lib/queries/keys`). `makeQueryClient(overrides)` (`@/lib/queries/client`) and RTL `render(ui, { reactStrictMode: true })` for the root-StrictMode test.
- Produces:
  - `ShellSkeleton(): JSX.Element` from `@/components/app/shell-skeleton`: `<div role="status" aria-label="Loading" className="min-h-dvh">` containing a header bar and two card placeholders. Used by both layouts. Later users: any full-page wait (tests find it with `getByRole("status", { name: "Loading" })`).
  - `ErrorStateProps.retrying?: boolean` (default `false`) on `ErrorState({ error, onRetry, title?, retrying? })`. While `retrying` is true, Retry is disabled with `aria-busy="true"` and a spinner, and its label stays "Retry". Later users: Task 14/15 (the `/join` preview `ErrorState` may pass its own in-flight flag).
  - `SignedInLayout` contract, for Tasks 15 and 17 and later slices:
    - A stored post-login path is read at mount. It is cleared before `router.replace(target)`, and cleared without navigating when it equals the pathname.
    - The children never render while a redirect is leaving the page, nor on the server or hydration pass. `/welcome`'s `useState` initializer (clarification 30) relies on this.
    - The full-page `ErrorState` stays up with `retrying` while its Retry runs.

- [ ] **Step 1 (agent): Preflight**

Run:
```bash
git log --oneline -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
grep -c "^export function \(peek\|clear\|store\)PostLoginPath" frontend/src/lib/post-login.ts
grep -n "peeks it once" frontend/src/lib/post-login.ts
grep -n "Slice 1b adds the post-login redirect here" "frontend/src/app/(signed-in)/layout.tsx"
grep -n "^function ShellSkeleton" "frontend/src/app/(signed-in)/(church)/layout.tsx"
git diff --quiet 0295b37 -- "frontend/src/app/(signed-in)" frontend/src/components/app && echo "unchanged since 0295b37"
```
**Expected:**
- The last commit is Task 10's: `<sha> Frontend: sign-in returns to the deep link; /login next and select_account; sign-out ends on /login (F §4.3, §4.2; S Routing, proxy and login)`.
- `Test Files  28 passed (28)` and `Tests  152 passed (152)`.
- `3`.
- One line ending `the \`(signed-in)\` layout peeks it once \`/me\` has loaded and` (Task 9's header).
- `21: * Slice 1b adds the post-login redirect here. A \`"use client"\` layout cannot`.
- `160:function ShellSkeleton() {`.
- `unchanged since 0295b37`.

If a count, a line number or the last line differs, stop and ask. Tasks 9 and 10 are not meant to touch these files; Task 10 says so explicitly for `(signed-in)/layout.tsx`.

- [ ] **Step 2 (agent): Write the failing tests**

Replace the whole of `frontend/src/app/(signed-in)/signed-in-layout.test.tsx` with the file below:
- The first and third tests are 1a's, unchanged.
- The second is 1a's 5xx test, extended to cover the busy Retry (T22-m2).
- The last four are new: the StrictMode follow, the same-path clear, clear-before-follow with arrival and return, and T22-m1.

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useMeContext } from "@/lib/me-context";
import { storePostLoginPath } from "@/lib/post-login";
import { makeQueryClient } from "@/lib/queries/client";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { me } from "@/test/fixtures";
import { setTestPath, supabaseAuth, TEST_ACCESS_TOKEN, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import SignedInLayout from "./layout";

/** Stands in for a page under the layout: it reads MeContext. */
function WhoAmI() {
  const current = useMeContext();
  return <p>{current.user.email}</p>;
}

function renderLayout(path = "/") {
  return renderWithProviders(
    <SignedInLayout>
      <WhoAmI />
    </SignedInLayout>,
    { path },
  );
}

/** The raw post-login entry in sessionStorage (`lib/post-login.ts`). */
function storedPostLoginPath(): string | null {
  return window.sessionStorage.getItem("wsb:postLoginPath");
}

describe("(signed-in) layout", () => {
  it("shows the shell skeleton until /me loads, then gives the children MeContext", async () => {
    const api = installFakeApi({ "GET /me": me() });
    renderLayout();

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();

    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading" })).not.toBeInTheDocument();
    expect(api.requests).toHaveLength(1);
    expect(api.requests[0]).toMatchObject({ method: "GET", path: "/me" });
    expect(api.requests[0].headers["Authorization"]).toBe(`Bearer ${TEST_ACCESS_TOKEN}`);
  });

  it("shows a full-page ErrorState on a 5xx from /me; Retry stays busy while it runs and refetches once", async () => {
    const api = installFakeApi({
      "GET /me": fakeError(500, "internal_error", "Something went wrong."),
    });
    const { user } = renderLayout();

    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();
    expect(api.requests).toHaveLength(1);

    let answer!: () => void;
    const answered = new Promise<void>((resolve) => {
      answer = resolve;
    });
    api.set("GET /me", async () => {
      await answered;
      return me();
    });
    await user.click(screen.getByRole("button", { name: "Retry" }));

    // The error stays on screen with a busy Retry; a second tap sends nothing.
    const retry = await screen.findByRole("button", { name: "Retry" });
    await waitFor(() => expect(retry).toBeDisabled());
    expect(retry).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    await user.click(retry);

    answer();
    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(2);
    expect(supabaseAuth.signOut).not.toHaveBeenCalled();
  });

  it("signs out locally on a 401 from /me, keeping a pending invite and the current path", async () => {
    window.sessionStorage.setItem("wsb:pendingInviteCode", "code-123");
    const api = installFakeApi({
      "GET /me": fakeError(401, "unauthenticated", "Please sign in."),
    });
    renderLayout("/welcome");

    await waitFor(() =>
      expect(testRouter.replace).toHaveBeenCalledWith("/login?next=%2Fwelcome"),
    );
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(window.sessionStorage.getItem("wsb:pendingInviteCode")).toBe("code-123");
    expect(api.requests).toHaveLength(1);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it("follows a stored /join once, before any child renders, even under StrictMode", async () => {
    storePostLoginPath("/join");
    installFakeApi({ "GET /me": me() });
    setTestPath("/");
    // StrictMode at the root: React double-invokes effects only there, not for a
    // <StrictMode> nested inside renderWithProviders' wrapper (see Task 14).
    const queryClient = makeQueryClient({ queries: { retry: false } });
    render(
      <QueryClientProvider client={queryClient}>
        <SignedInLayout>
          <WhoAmI />
        </SignedInLayout>
      </QueryClientProvider>,
      { reactStrictMode: true },
    );

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/join"));
    await waitFor(() => expect(queryClient.getQueryData(keys.me())).toBeDefined());
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(storedPostLoginPath()).toBeNull();
    // /me has loaded, but the page being left never renders.
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();
  });

  it("clears a stored path that is the current one and renders the children", async () => {
    storePostLoginPath("/welcome");
    installFakeApi({ "GET /me": me() });
    renderLayout("/welcome");

    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(storedPostLoginPath()).toBeNull();
  });

  it("clears the stored path before following it, so coming back to / does not redirect again", async () => {
    storePostLoginPath("/welcome");
    installFakeApi({ "GET /me": me() });
    const { rerender } = renderLayout("/");

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(storedPostLoginPath()).toBeNull();
    expect(screen.queryByText("pat@example.com")).not.toBeInTheDocument();

    // The redirect arrives: the same layout instance now sees /welcome.
    setTestPath("/welcome");
    rerender(
      <SignedInLayout>
        <WhoAmI />
      </SignedInLayout>,
    );
    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();

    // Back to /: nothing is stored any more, so nothing redirects.
    setTestPath("/");
    rerender(
      <SignedInLayout>
        <WhoAmI />
      </SignedInLayout>,
    );
    expect(screen.getByText("pat@example.com")).toBeInTheDocument();
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
  });

  it("keeps the children and shows no Retry when a background /me refetch fails", async () => {
    const api = installFakeApi({ "GET /me": me() });
    const { queryClient } = renderLayout();
    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();

    api.set("GET /me", fakeError(500, "internal_error", "Something went wrong."));
    await act(() => queryClient.refetchQueries({ queryKey: keys.me() }));

    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(2);
    expect(queryClient.getQueryState(keys.me())?.status).toBe("error");
    expect(screen.getByText("pat@example.com")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading" })).not.toBeInTheDocument();
  });
});
```

In `frontend/src/components/app/error-state.test.tsx`, replace the end of the file:
```tsx
    expect(screen.getByRole("alert")).toHaveTextContent(/^Something went wrong\. \(Ref: 01234567\)$/);
  });
});
```
with:
```tsx
    expect(screen.getByRole("alert")).toHaveTextContent(/^Something went wrong\. \(Ref: 01234567\)$/);
  });

  it("while retrying, Retry is disabled and busy, so a repeat tap does nothing", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const { rerender } = render(
      <ErrorState error={new ApiError(503, "auth_unavailable", "Try again shortly.")} onRetry={onRetry} retrying />,
    );

    const retry = screen.getByRole("button", { name: "Retry" });
    expect(retry).toBeDisabled();
    expect(retry).toHaveAttribute("aria-busy", "true");
    await user.click(retry);
    expect(onRetry).not.toHaveBeenCalled();

    rerender(
      <ErrorState error={new ApiError(503, "auth_unavailable", "Try again shortly.")} onRetry={onRetry} retrying={false} />,
    );
    expect(screen.getByRole("button", { name: "Retry" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Retry" })).not.toHaveAttribute("aria-busy");
  });
});
```

In `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx`, test "sends a user with no church to /welcome without asking for a church" (`:236-242`), replace:
```tsx
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(churchRequests(api)).toEqual([]);
  });

  it("switching remounts the page and removes the old church's queries", async () => {
```
with:
```tsx
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(churchRequests(api)).toEqual([]);
    // The (church) layout's own skeleton (the shared ShellSkeleton) is announced too.
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });

  it("switching remounts the page and removes the old church's queries", async () => {
```
(The `(signed-in)` layout has rendered its children by then, so the only status region on the page is the `(church)` layout's.)

- [ ] **Step 3 (agent): Run the tests to verify they fail**

Run:
```bash
(cd frontend && npx vitest run signed-in-layout error-state church-layout 2>&1 | grep -E "×|FAIL|Error|Test Files|Tests ")
```
**Expected:** six failures, and each fails on its assertion, not on an import:
- `× (signed-in) layout > shows a full-page ErrorState on a 5xx from /me; Retry stays busy while it runs and refetches once`: `TestingLibraryElementError: Unable to find role="button" and name "Retry"`. After the tap, 1a's layout drops to the skeleton (rule 5).
- `× (signed-in) layout > follows a stored /join once, before any child renders, even under StrictMode`: `AssertionError: expected "spy" to be called with arguments: [ '/join' ]`.
- `× (signed-in) layout > clears a stored path that is the current one and renders the children`: `AssertionError: expected '{"path":"/welcome","at":<ms>}' to be null`.
- `× (signed-in) layout > clears the stored path before following it, so coming back to / does not redirect again`: `AssertionError: expected "spy" to be called with arguments: [ '/welcome' ]`.
- `× ErrorState > while retrying, Retry is disabled and busy, so a repeat tap does nothing`: `Error: expect(element).toBeDisabled()`. The prop is not read yet.
- `× (church) layout > sends a user with no church to /welcome without asking for a church`: `TestingLibraryElementError: Unable to find an accessible element with the role "status" and name "Loading"`.

The summary reads `Test Files  3 failed (3)` and `Tests  6 failed | 20 passed (26)`. "keeps the children and shows no Retry when a background /me refetch fails" already passes. It pins 1a's behavior (T22-m1) so the rewrite below keeps it.

- [ ] **Step 4 (agent): Create `frontend/src/components/app/shell-skeleton.tsx`**

```tsx
import { Skeleton } from "@/components/ui/skeleton";

/**
 * The app shell's shape while a layout waits: a header bar and two cards
 * (F §4.8 "Loading"). The `(signed-in)` layout shows it while `/me` loads, a
 * sign-out runs or a post-login redirect leaves; the `(church)` layout shows it
 * until the stored church is read. It is one `role="status"` region named
 * "Loading", so screen readers announce it and tests find it by role and name
 * (1a minor T23-m3: one skeleton for both layouts).
 */
export function ShellSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="min-h-dvh">
      <div className="border-b">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="ml-auto size-9 rounded-full" />
        </div>
      </div>
      <div className="mx-auto grid max-w-3xl gap-4 p-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}
```

- [ ] **Step 5 (agent): Give `ErrorState` a busy Retry (`frontend/src/components/app/error-state.tsx`)**

Replace the whole file with:
```tsx
import { CircleAlertIcon } from "lucide-react";

import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { describeError } from "@/lib/api/errors";

export type ErrorStateProps = {
  /** The failed query's error; describeError picks the sentence (F §4.8, ops handoff Ref). */
  error: unknown;
  /** Usually the query's refetch; called with no arguments. */
  onRetry: () => void;
  /** Optional heading above the sentence. */
  title?: string;
  /** True while the retry runs: Retry is disabled, busy and spinning, so a repeat tap does nothing. */
  retrying?: boolean;
};

/** F §4.8 "Query failed": the message inline with a Retry button. An error is never shown as empty. */
export function ErrorState({ error, onRetry, title, retrying = false }: ErrorStateProps) {
  const message = describeError(error);
  return (
    <div data-slot="error-state" className="flex flex-col items-start gap-3">
      <Alert variant="destructive">
        <CircleAlertIcon aria-hidden="true" />
        {title ? (
          <>
            <AlertTitle>{title}</AlertTitle>
            <AlertDescription>{message}</AlertDescription>
          </>
        ) : (
          <AlertTitle>{message}</AlertTitle>
        )}
      </Alert>
      <PendingButton
        variant="outline"
        size="touch"
        pending={retrying}
        pendingLabel="Retry"
        onClick={() => onRetry()}
      >
        Retry
      </PendingButton>
    </div>
  );
}
```
(`Button` is no longer imported here. `PendingButton` passes `variant`, `size` and `onClick` through to it, and 1a's `pending-button.test.tsx` pins that.)

- [ ] **Step 6 (agent): Follow the post-login path in `frontend/src/app/(signed-in)/layout.tsx`; correct Task 9's header line**

Replace the whole of `frontend/src/app/(signed-in)/layout.tsx` with:
```tsx
"use client";

/**
 * Layout for every signed-in route (F §4.1, §4.2, §4.3; S "Layouts (1a)", Routing).
 *
 * - Loads `/me` and shows the shell skeleton until it arrives.
 * - Follows the post-login path (S Routing; AC14): the path `/login` stored
 *   before sign-in. It is read once, when the layout mounts, in a `useState`
 *   initializer; the server has no sessionStorage, and the hydration pass
 *   renders the skeleton either way because `/me` has not loaded yet, so the
 *   markup matches. A stored path other than the current one keeps the skeleton
 *   up until the pathname changes, so the page being left never mounts or sends
 *   a request; an effect clears the stored path first, then follows it with
 *   `router.replace`. A stored path equal to the current one is just cleared.
 *   Clearing before following means a stored path with no route yet
 *   (`/builder`) redirects once, not on every visit for ten minutes (slice 1b
 *   clarification 22), and StrictMode's repeated effect finds nothing to follow.
 * - A first load that fails with anything but a 401 shows a full-page
 *   `ErrorState` with Retry. While Retry runs, the error stays on screen with a
 *   busy, disabled Retry, so a repeat tap does nothing (a refetch of a query
 *   with no data resets it to pending, so the error Retry was pressed on is
 *   kept here). Once `/me` has loaded, a failed background refetch keeps the
 *   loaded shell: a network blip on window focus never replaces a working page.
 * - A 401 anywhere reaches `handleAuthErrors`, which emits
 *   `authEvents.signOutRequired()`. This layout, the event's only subscriber,
 *   answers with one local sign-out that keeps a pending invite and passes the
 *   current path as `next` (S Flow D "Session expired").
 * - While a sign-out runs (the signing-out flag in `lib/auth.ts`) it renders the
 *   skeleton and disables `/me`. That unmounts the `(church)` subtree and its
 *   `ChurchProvider`, so nothing refetches the cleared cache or stores a church
 *   again before `router.replace("/login")`.
 * - Pages below it read `/me` with `useMeContext()`.
 *
 * A `"use client"` layout cannot export `metadata`; the root layout's title applies.
 */
import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { ErrorState } from "@/components/app/error-state";
import { ShellSkeleton } from "@/components/app/shell-skeleton";
import { ApiError } from "@/lib/api/client";
import { isSigningOut, useSignOut, useSigningOut } from "@/lib/auth";
import { MeProvider } from "@/lib/me-context";
import { clearPostLoginPath, peekPostLoginPath } from "@/lib/post-login";
import { authEvents } from "@/lib/queries/auth-events";
import { useMe } from "@/lib/queries/me";

export default function SignedInLayout({ children }: { children: ReactNode }) {
  const signingOut = useSigningOut();
  const me = useMe({ enabled: !signingOut });
  const signOut = useSignOut();
  const pathname = usePathname();
  const router = useRouter();
  // The redirect this mount is making: from the current path to the stored one.
  const [leaving, setLeaving] = useState<{ from: string } | null>(() => {
    const target = peekPostLoginPath();
    return target !== null && target !== pathname ? { from: pathname } : null;
  });
  // The error Retry was pressed on, shown (with a busy Retry) while it runs.
  const [retriedError, setRetriedError] = useState<unknown>(null);
  // Arrived (or went anywhere else): the page below may render.
  if (leaving !== null && pathname !== leaving.from) setLeaving(null);

  useEffect(
    () =>
      authEvents.onSignOutRequired(() => {
        if (isSigningOut()) return;
        void signOut({ keepPendingInvite: true, next: pathname });
      }),
    [signOut, pathname],
  );

  useEffect(() => {
    const target = peekPostLoginPath();
    if (target === null) return;
    clearPostLoginPath();
    if (target !== pathname) router.replace(target);
  }, [pathname, router]);

  if (signingOut || leaving !== null) return <ShellSkeleton />;
  if (me.data) return <MeProvider value={me.data}>{children}</MeProvider>;
  const error = me.isError ? me.error : me.isFetching ? retriedError : null;
  if (error !== null && !isUnauthenticated(error)) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center p-4">
        <ErrorState
          error={error}
          retrying={me.isFetching}
          onRetry={() => {
            setRetriedError(me.error);
            void me.refetch();
          }}
        />
      </main>
    );
  }
  return <ShellSkeleton />;
}

/** A 401 is already handled: `handleAuthErrors` has started the sign-out. */
function isUnauthenticated(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}
```

Notes for the reviewer:
- Every hook runs on every render; the render-phase `setLeaving(null)` is conditional, so it cannot loop.
- No ref is read during render (`react-hooks/refs`), and no effect body calls `setState` (`react-hooks/set-state-in-effect`).
- `setRetriedError` runs in the click handler.
- The skeleton's `role="status"` / "Loading" contract from 1a is kept, now in the shared component.
- The 401 path is unchanged. Nothing is stored during a sign-out, because `useSignOut` removes `wsb:postLoginPath` before `router.replace("/login…")`.

In `frontend/src/lib/post-login.ts` (Task 9's module header), replace:
```ts
 * validated `next` before OAuth; the `(signed-in)` layout peeks it once `/me` has loaded and
```
with:
```ts
 * validated `next` before OAuth; the `(signed-in)` layout reads it when it mounts and
```

- [ ] **Step 7 (agent): Use the shared skeleton in `frontend/src/app/(signed-in)/(church)/layout.tsx`**

Replace (`:30-31`):
```tsx
import { ErrorState } from "@/components/app/error-state";
import { Skeleton } from "@/components/ui/skeleton";
```
with:
```tsx
import { ErrorState } from "@/components/app/error-state";
import { ShellSkeleton } from "@/components/app/shell-skeleton";
import { Skeleton } from "@/components/ui/skeleton";
```

Delete (`:160-173`, the local skeleton and the blank line after it; `BodySkeleton` below it stays and still uses `Skeleton`):
```tsx
function ShellSkeleton() {
  return (
    <div className="min-h-dvh">
      <div className="border-b">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
          <Skeleton className="h-8 flex-1" />
          <Skeleton className="size-8 rounded-full" />
        </div>
      </div>
      <BodySkeleton />
    </div>
  );
}

```
The layout's `if (candidate === null) return <ShellSkeleton />;` (`:114`) now renders the shared component. Nothing else in the file changes.

- [ ] **Step 8 (agent): Run the tests, the frontend check and the backend suite**

Run:
```bash
(cd frontend && npx vitest run signed-in-layout error-state church-layout 2>&1 | grep -E "✓ \||×|stderr|act\(|Warning|Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
grep -rn "function ShellSkeleton" frontend/src
.venv/bin/python -m pytest -q | tail -1
git status --short
```
**Expected:**
- `✓ |dom| src/components/app/error-state.test.tsx (4 tests)`, `✓ |dom| src/app/(signed-in)/signed-in-layout.test.tsx (7 tests)`, `✓ |dom| src/app/(signed-in)/(church)/church-layout.test.tsx (15 tests)`, `Test Files  3 passed (3)`, `Tests  26 passed (26)`. There are no `×`, `stderr`, `act(` or `Warning` lines.
- `Test Files  28 passed (28)` and `Tests  157 passed (157)`: 152 after Task 10, plus 5 (4 layout tests and 1 `ErrorState` test). There is no new test file, because `shell-skeleton.tsx` is covered through both layouts' tests. `tsc --noEmit` and `eslint` print nothing beyond their banners. If `eslint` reports `react-hooks/set-state-in-effect` or `react-hooks/refs` on `layout.tsx`, a hook was moved into an effect or a ref was added; restore Step 6's file.
- The `grep` prints exactly one line: `frontend/src/components/app/shell-skeleton.tsx:11:export function ShellSkeleton() {`.
- `799 passed, 9 skipped in <t>s` (no backend change).
- `git status --short` lists exactly (plus `?? .claude/`):

```
 M frontend/src/app/(signed-in)/(church)/church-layout.test.tsx
 M frontend/src/app/(signed-in)/(church)/layout.tsx
 M frontend/src/app/(signed-in)/layout.tsx
 M frontend/src/app/(signed-in)/signed-in-layout.test.tsx
 M frontend/src/components/app/error-state.test.tsx
 M frontend/src/components/app/error-state.tsx
 M frontend/src/lib/post-login.ts
?? frontend/src/components/app/shell-skeleton.tsx
```

If a test fails:
- "follows a stored /join once…" calls `replace` twice. The effect must re-read the store and return when it is empty; a stored-path check held in state or a ref is not enough.
- "clears the stored path before following it…" still finds the entry. `clearPostLoginPath()` must run before `router.replace`, not on arrival.
- The 5xx test cannot find a disabled Retry. The layout must keep `retriedError` while `me.isFetching` (rule 5); `retrying={me.isFetching}` alone is never visible.
- A church-layout test fails on "status". Another `role="status"` region is on the page; only `ShellSkeleton` may carry the role.

- [ ] **Step 9 (agent): Commit**

```bash
git add "frontend/src/app/(signed-in)/layout.tsx" \
        "frontend/src/app/(signed-in)/signed-in-layout.test.tsx" \
        "frontend/src/app/(signed-in)/(church)/layout.tsx" \
        "frontend/src/app/(signed-in)/(church)/church-layout.test.tsx" \
        frontend/src/components/app/shell-skeleton.tsx \
        frontend/src/components/app/error-state.tsx \
        frontend/src/components/app/error-state.test.tsx \
        frontend/src/lib/post-login.ts
git status --short
git commit -m "Frontend: the signed-in layout follows the post-login path; one announced loading skeleton; Retry shows it is busy (F §4.3; S Routing; AC14)

The (signed-in) layout reads the path /login stored before sign-in when
it mounts. A different path keeps the skeleton up, so the page being
left never renders, while an effect clears the stored path and then
follows it with router.replace; the current path is just cleared.
Clearing before following means a path with no route yet redirects once,
not on every visit for ten minutes (1b clarification 22), and
StrictMode's repeated effect finds nothing to follow.

Owner answer 4 (1a minors): while the full-page Retry runs, the error
stays on screen and Retry is disabled, busy and spinning, so repeat taps
do nothing (T22-m2; a refetch of a query with no data resets it to
pending, so the layout keeps the error Retry was pressed on). Both
layouts share one ShellSkeleton, a role=status region named Loading
(T23-m3); church pages' placeholder sizes change slightly. A failed
background /me refetch keeps the children with no Retry (T22-m1 test).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --short
```
**Expected:** the first `git status --short` shows the eight paths staged (`M ` for seven, `A  frontend/src/components/app/shell-skeleton.tsx`). The commit prints `<sha> Frontend: the signed-in layout follows the post-login path; one announced loading skeleton; Retry shows it is busy (F §4.3; S Routing; AC14)`, and afterwards only `?? .claude/` remains. Do not push (Task 20 pushes Tasks 9–19 to the draft PR).

Tests after this task: backend `799 passed, 9 skipped` (unchanged); frontend `157 passed` (28 files).
### Task 12: `TimezoneCombobox`, the Combobox pattern for long lists (S Flow A Create tab, Testing Frontend `timezone-combobox.test.tsx`, Risks 7; F §4.9 item 5, §7.2; AC11)

The time-zone field of the Create tab, built as its own component because F §7.2 makes it the first use of the Combobox pattern (F §4.9 item 5: "Long lists use Combobox, which also needs `items`… Render at most 50 filtered matches, with a 'Type to search' hint") and 6a's church profile reuses it. It wraps 1a's generated `components/ui/combobox.tsx` without editing it: the items are Task 9's `listTimezones()` (the browser's `Intl.supportedValuesOf("timeZone")`), each shown as `timezoneLabel(id)` (`_` as a space) with the IANA id as its value; Base UI's `limit={50}` caps the rendered matches, and "Type to search" shows under the list while more than 50 zones match. When `listTimezones()` is null (no `Intl.supportedValuesOf`, e.g. Safari before 15.4; S Risks 7) the field is a plain text input with the same helper and the server validates the id. The component owns the whole field: the label "Time zone", the input, the helper "Sets the default service date (the next Sunday in this time zone)." and the inline error, so Task 16's form renders none of these for the field. The default zone is not chosen here: Task 16 passes `defaultTimezone(listTimezones())` as the initial `value`.

Sizing follows Global Constraints "Mobile" at the call site, never in the generated file: `ComboboxInput` puts its `className` on the `InputGroup` (`combobox.tsx:64`), so `h-11` sizes the group and `*:data-[slot=input-group-control]:h-full` stretches the `<input>` to fill it (the same `*:data-[slot=…]` form the generated `ComboboxContent` uses at `:113`); items get `min-h-11 md:min-h-8`; the fallback `Input` gets `h-11` (it already has `text-base md:text-sm`).

The filter is the component's own `matchesZone` (case-insensitive substring of the label or the raw id, so `new york` and `new_york` both find `America/New_York`), passed as Base UI's `filter` so that the hint's match count and the rendered list use the same rule. The typed query is tracked from `onInputValueChange` (only `details.reason === "input-change"` counts; an item press or the close resets it), which mirrors Base UI's own rule of showing the whole list when the popup opens on a selected value (`AriaCombobox.js:268-269`).

**Notes from the code (the outline's Interfaces are kept; these fill in what it leaves open):**
- The outline lists `ComboboxEmpty` but gives no text. The empty list says **"No matching time zone."** (new owner-visible copy; without it, a query with no match opens an empty box). The "new york" test pins it. The owner approved these words on 2026-09-28 (owner answer 8). If they ever change, edit the `<ComboboxEmpty>` line in `timezone-combobox.tsx` (Step 4) and the two `"No matching time zone."` lines in the "new york" test (Step 2); nothing else quotes it.
- "Type to search" shows only while more than 50 zones match (S: "At most 50 matches render, with 'Type to search'"); once typing narrows the list to 50 or fewer, it goes away. The "new york" test pins both halves.
- The component also uses the Base UI root props `value`, `onValueChange`, `onInputValueChange` and `onOpenChange` besides the outline's `items`, `limit`, `itemToStringLabel`, `filter`. Base UI's `ChangeEventReason` for the combobox has no `"input-paste"` (tsc rejects the comparison); a paste fires the input's change event, so it arrives as `"input-change"`.
- Testing Library quirk (verified): while the list is open, `dom-accessibility-api` computes an **empty** accessible name for the combobox input, so `getByRole("combobox", { name: "Time zone" })` fails then. Tests (here and in Tasks 16, 17) take the input once before opening it and keep the reference. The label's `htmlFor` and `document.getElementById(id)` still resolve to the one `<input>` while open (no duplicate id).
- The tests stub `Intl.supportedValuesOf` itself (Global Constraints), not `listTimezones`: `vi.spyOn(Intl, "supportedValuesOf")` for a fixed list, and `Object.defineProperty(Intl, "supportedValuesOf", { value: undefined, … })` for the missing case, restored by this file's own `afterEach` (not a second global `afterEach`; P1a's one-`afterEach` rule is about `setup-dom.ts`). This relies on Task 9's `listTimezones()` reading `Intl.supportedValuesOf` on every call (it does; no cache).

Verified in a throwaway worktree at `0295b37` with Task 9's `timezones.ts` copied verbatim: the test file fails as quoted in Step 3 before the component exists and passes (6) after; removing `limit` fails the 50-match test, always showing the hint fails the "new york" test, dropping `aria-invalid` fails the error test; `tsc --noEmit` and `eslint` are clean; the whole suite passes.

**Files:**
- Create: `frontend/src/components/app/timezone-combobox.tsx`
- Create: `frontend/src/components/app/timezone-combobox.test.tsx`

**Interfaces:**
- Consumes:
  - Task 9, `frontend/src/lib/timezones.ts`: `listTimezones(): string[] | null` (`Intl.supportedValuesOf("timeZone")`, or null when that function is missing, throws or returns an empty list; read on every call) and `timezoneLabel(id: string): string` (`id.replaceAll("_", " ")`).
  - 1a generated `frontend/src/components/ui/combobox.tsx` (`:280-297`): `Combobox` (= Base UI `Combobox.Root`), `ComboboxInput` (`className` goes on the `InputGroup`; `id`, `aria-invalid`, `aria-describedby` and other props go on Base UI's `Combobox.Input`, which keeps `id` as the `<input>`'s id: `ComboboxInput.js:83`), `ComboboxContent`, `ComboboxList` (children as `(item) => ReactNode`), `ComboboxItem`, `ComboboxEmpty`. No `ComboboxStatus` export; the hint is a plain `<p>`.
  - Base UI 1.8 `Combobox.Root` props: `items`, `limit` (`AriaCombobox.d.ts:205`), `filter` (`:154`), `itemToStringLabel` (`ComboboxRoot.d.ts`), `value` / `onValueChange(value: string | null)`, `onInputValueChange(value: string, details: { reason })`, `onOpenChange(open: boolean)`.
  - 1a `frontend/src/components/ui/input.tsx` `Input`, `frontend/src/components/ui/label.tsx` `Label`.
- Produces (`frontend/src/components/app/timezone-combobox.tsx`):
  - `TimezoneCombobox({ value, onChange, error, id }: TimezoneComboboxProps): JSX.Element`, with `export type TimezoneComboboxProps = { value: string; onChange: (value: string) => void; error?: string | null; id?: string }`.
    - Renders `<Label htmlFor={id}>Time zone</Label>`, then the field, then the helper `<p id="{id}-helper">`, then (when `error` is truthy) the error `<p id="{id}-error">` below it. The input has `aria-describedby="{id}-helper"` or `"{id}-helper {id}-error"`, and `aria-invalid="true"` only while `error` is set. The error `<p>` has no `role="alert"`: Task 16 focuses the field, and the description is read then.
    - Combobox mode (list available): role `combobox`, accessible name "Time zone"; the input shows `timezoneLabel(value)`; picking an item calls `onChange(<IANA id>)` (e.g. `"America/New_York"`); a `null` from Base UI calls `onChange("")`; `value === ""` is passed to Base UI as `null`.
    - Fallback mode (`listTimezones()` null): role `textbox`, name "Time zone"; every keystroke calls `onChange(event.target.value)` (untrimmed; Task 16's client check trims, and so does the server).
    - `id` (default `useId()`) is the `<input>`'s id in both modes, so Task 16 focuses the field with `document.getElementById(id)?.focus()`.
  - `TIMEZONE_MATCH_LIMIT = 50`; `TIMEZONE_HELPER = "Sets the default service date (the next Sunday in this time zone)."`.
  - Later users: Task 16 (`CreateChurchForm`: `value`, `onChange`, `error` = "Timezone is required." / "Unknown timezone.", `id`), Task 17 (test: the browser zone preselected, i.e. the combobox input's value is `timezoneLabel(<stubbed zone>)`), 6a (church profile form; extends `timezone-combobox.test.tsx`).

Counts after this task: backend **799 passed, 9 skipped** (unchanged since Task 8); frontend **163 passed in 29 files** (Task 11 with Q4 yes: 157 in 28; + 6 tests in one new file).

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
ls frontend/src/components/app/timezone-combobox.tsx 2>&1 | grep -c "No such file"
grep -c -E "^export function (listTimezones|timezoneLabel)\(" frontend/src/lib/timezones.ts
grep -n -E "^  ComboboxEmpty,$|ComboboxStatus" frontend/src/components/ui/combobox.tsx
```

**Expected:** `git status --short` lists only `?? .claude/`; the last commit is Task 11's; `Test Files  28 passed (28)` and `Tests  157 passed (157)`; then `1` (the component does not exist yet); then `2` (Task 9's two functions); then exactly one line, `289:  ComboboxEmpty,` (no `ComboboxStatus`). If the frontend counts differ, stop and ask.

- [ ] **Step 2 (agent): Write the failing tests**

Create `frontend/src/components/app/timezone-combobox.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { TimezoneCombobox } from "./timezone-combobox";

// A fixed zone list (never the runner's): 70 filler ids plus three real ones, so the
// full list is over the 50-match cap and "new york" has exactly one match.
const FILLER = Array.from({ length: 70 }, (_, i) => `Test/Zone_${String(i).padStart(2, "0")}`);
const ZONES = ["America/Chicago", "America/New_York", "America/North_Dakota/New_Salem", ...FILLER];

const originalSupportedValuesOf = Object.getOwnPropertyDescriptor(Intl, "supportedValuesOf");

afterEach(() => {
  vi.restoreAllMocks();
  if (originalSupportedValuesOf) Object.defineProperty(Intl, "supportedValuesOf", originalSupportedValuesOf);
});

function stubZones(zones: string[]) {
  vi.spyOn(Intl, "supportedValuesOf").mockReturnValue(zones);
}

function removeSupportedValuesOf() {
  Object.defineProperty(Intl, "supportedValuesOf", { configurable: true, writable: true, value: undefined });
}

/** A controlled host, as the create form uses it. */
function Host({ initial = "", onChange }: { initial?: string; onChange?: (value: string) => void }) {
  const [value, setValue] = useState(initial);
  return (
    <TimezoneCombobox
      value={value}
      onChange={(next) => {
        setValue(next);
        onChange?.(next);
      }}
    />
  );
}

describe("TimezoneCombobox", () => {
  it("opens the zone list on click", async () => {
    stubZones(ZONES);
    const user = userEvent.setup();
    render(<Host initial="America/Chicago" />);

    const input = screen.getByRole("combobox", { name: "Time zone" });
    expect(input).toHaveValue("America/Chicago");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();

    await user.click(input);

    expect(await screen.findByRole("listbox")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "America/New York" })).toBeInTheDocument();
  });

  it("renders at most 50 matches with the Type to search hint", async () => {
    stubZones(ZONES);
    const user = userEvent.setup();
    render(<Host />);

    await user.click(screen.getByRole("combobox", { name: "Time zone" }));

    const listbox = await screen.findByRole("listbox");
    expect(within(listbox).getAllByRole("option")).toHaveLength(50);
    expect(screen.getByText("Type to search")).toBeInTheDocument();
  });

  it("finds America/New_York when typing new york (spaces for underscores)", async () => {
    stubZones(ZONES);
    const user = userEvent.setup();
    render(<Host />);
    // Keep this reference: while the list is open, Testing Library computes an empty
    // accessible name for the combobox, so a second getByRole by name would fail.
    const input = screen.getByRole("combobox", { name: "Time zone" });

    await user.type(input, "new york");

    const listbox = await screen.findByRole("listbox");
    expect(within(listbox).getAllByRole("option").map((option) => option.textContent)).toEqual([
      "America/New York",
    ]);
    expect(screen.queryByText("Type to search")).not.toBeInTheDocument();
    expect(screen.queryByText("No matching time zone.")).not.toBeInTheDocument();

    await user.clear(input);
    await user.type(input, "zzz");

    expect(screen.queryByRole("option")).not.toBeInTheDocument();
    expect(screen.getByText("No matching time zone.")).toBeInTheDocument();
  });

  it("calls onChange with the IANA id on keyboard selection", async () => {
    stubZones(ZONES);
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Host onChange={onChange} />);

    const input = screen.getByRole("combobox", { name: "Time zone" });
    await user.type(input, "new york");
    await screen.findByRole("option", { name: "America/New York" });
    await user.keyboard("{ArrowDown}{Enter}");

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith("America/New_York");
    expect(input).toHaveValue("America/New York");
  });

  it("renders the error below the field and marks the input invalid", () => {
    stubZones(ZONES);
    render(<TimezoneCombobox value="" onChange={() => {}} error="Timezone is required." />);

    const input = screen.getByRole("combobox", { name: "Time zone" });
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription(
      "Sets the default service date (the next Sunday in this time zone). Timezone is required.",
    );
    const helper = screen.getByText("Sets the default service date (the next Sunday in this time zone).");
    const error = screen.getByText("Timezone is required.");
    expect(helper.compareDocumentPosition(error) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("falls back to a plain text input with the same helper when Intl.supportedValuesOf is missing", async () => {
    removeSupportedValuesOf();
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TimezoneCombobox value="" onChange={onChange} id="church-timezone" />);

    const input = screen.getByRole("textbox", { name: "Time zone" });
    expect(input).toHaveAttribute("id", "church-timezone");
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(input).toHaveAccessibleDescription("Sets the default service date (the next Sunday in this time zone).");
    expect(input).not.toHaveAttribute("aria-invalid");

    await user.type(input, "E");
    expect(onChange).toHaveBeenLastCalledWith("E");
  });
});
```

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
(cd frontend && npx vitest run src/components/app/timezone-combobox.test.tsx 2>&1 | grep -E "Failed to resolve|Test Files|Tests ")
```

**Expected:** FAIL before any test runs, because the component does not exist yet:

```
Error: Failed to resolve import "./timezone-combobox" from "src/components/app/timezone-combobox.test.tsx". Does the file exist?
 Test Files  1 failed (1)
      Tests  no tests
```

- [ ] **Step 4 (agent): Create `frontend/src/components/app/timezone-combobox.tsx`**

```tsx
"use client";

import { useId, useMemo, useState } from "react";

import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { listTimezones, timezoneLabel } from "@/lib/timezones";

/** F §4.9 item 5: a long list renders at most this many filtered matches. */
export const TIMEZONE_MATCH_LIMIT = 50;

/** S Flow A Create tab: the field's helper, the same in both modes. */
export const TIMEZONE_HELPER = "Sets the default service date (the next Sunday in this time zone).";

export type TimezoneComboboxProps = {
  /** The IANA id ("" when none). */
  value: string;
  /** Called with the picked IANA id (combobox) or the typed text (fallback). */
  onChange: (value: string) => void;
  /** Inline message under the field; also sets `aria-invalid`. */
  error?: string | null;
  /** The `<input>`'s id in both modes (default: generated), for the label and for focusing. */
  id?: string;
};

/**
 * Matches the typed query against the label (`_` shown as a space) or the raw id,
 * ignoring case: "new york" and "new_york" both find America/New_York.
 */
function matchesZone(zone: string, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (q === "") return true;
  return timezoneLabel(zone).toLowerCase().includes(q) || zone.toLowerCase().includes(q);
}

/**
 * The time-zone picker (S Flow A Create tab; F §4.9 item 5, §7.2): the first use of
 * the Combobox pattern, reused by 6a's church profile. Items are
 * `Intl.supportedValuesOf("timeZone")`; at most 50 matches render, with "Type to search"
 * while more match. Without `Intl.supportedValuesOf` it is a plain text input and the
 * server validates the id.
 */
export function TimezoneCombobox({ value, onChange, error, id }: TimezoneComboboxProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const helperId = `${inputId}-helper`;
  const errorId = `${inputId}-error`;
  const describedBy = error ? `${helperId} ${errorId}` : helperId;

  const [zones] = useState(listTimezones);
  // What the user has typed since the list opened ("" = nothing yet, so every zone matches).
  const [query, setQuery] = useState("");
  const matchCount = useMemo(
    () => (zones ? zones.filter((zone) => matchesZone(zone, query)).length : 0),
    [zones, query],
  );

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={inputId}>Time zone</Label>
      {zones ? (
        <Combobox
          items={zones}
          limit={TIMEZONE_MATCH_LIMIT}
          filter={matchesZone}
          itemToStringLabel={timezoneLabel}
          value={value === "" ? null : value}
          onValueChange={(next) => onChange(next ?? "")}
          onInputValueChange={(next, details) => setQuery(details.reason === "input-change" ? next : "")}
          onOpenChange={(open) => {
            if (!open) setQuery("");
          }}
        >
          <ComboboxInput
            id={inputId}
            className="h-11 w-full *:data-[slot=input-group-control]:h-full"
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
          />
          <ComboboxContent>
            <ComboboxEmpty>No matching time zone.</ComboboxEmpty>
            <ComboboxList>
              {(zone: string) => (
                <ComboboxItem key={zone} value={zone} className="min-h-11 md:min-h-8">
                  {timezoneLabel(zone)}
                </ComboboxItem>
              )}
            </ComboboxList>
            {matchCount > TIMEZONE_MATCH_LIMIT ? (
              <p className="border-t px-2 py-1.5 text-xs text-muted-foreground">Type to search</p>
            ) : null}
          </ComboboxContent>
        </Combobox>
      ) : (
        <Input
          id={inputId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete="off"
          autoCapitalize="none"
          spellCheck={false}
          className="h-11"
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
        />
      )}
      <p id={helperId} className="text-sm text-muted-foreground">
        {TIMEZONE_HELPER}
      </p>
      {error ? (
        <p id={errorId} className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
```

- [ ] **Step 5 (agent): Run the tests to verify they pass, then the whole frontend and backend suites**

```bash
(cd frontend && npx vitest run src/components/app/timezone-combobox.test.tsx 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `Test Files  1 passed (1)` and `Tests  6 passed (6)`; then `Test Files  29 passed (29)` and `Tests  163 passed (163)` (157 + 6), `tsc --noEmit` and `eslint` print no errors; then `799 passed, 9 skipped in <t>s` (no backend change; Task 8's line); `git status --short` lists exactly (plus `?? .claude/`):

```
?? frontend/src/components/app/timezone-combobox.test.tsx
?? frontend/src/components/app/timezone-combobox.tsx
```

If `tsc` reports `This comparison appears to be unintentional` on the `onInputValueChange` line, a `"input-paste"` check was added: Base UI's `ChangeEventReason` has no such value (a paste is `"input-change"`). If the 50-match test counts 73 options, `limit` is missing from the root. If a test fails with `Unable to find an accessible element with the role "combobox" and name "Time zone"`, it queried the input by name while the list was open; take the reference before opening (see the notes above). If a test passes locally but fails in CI with a different option list, a stub was skipped and the test read the runner's zones.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/app/timezone-combobox.tsx frontend/src/components/app/timezone-combobox.test.tsx
git status --short
git commit -m "Frontend: TimezoneCombobox, the Combobox pattern for long lists (F §4.9 item 5, §7.2; S Flow A Create tab)

The Create tab's time-zone field and the first use of the Combobox
pattern (6a reuses it). Items are Intl.supportedValuesOf(\"timeZone\")
shown with spaces for underscores, the value is the IANA id; at most 50
matches render, with \"Type to search\" while more match, and \"No
matching time zone.\" when none do. Typing matches the label or the id,
ignoring case. The component owns the label, the helper and the inline
error (aria-invalid, aria-describedby), sizes the input and items for
44 px taps at the call site, and falls back to a plain text input with
the same helper when Intl.supportedValuesOf is missing.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** after `git add`, `git status --short` shows `A  frontend/src/components/app/timezone-combobox.test.tsx` and `A  frontend/src/components/app/timezone-combobox.tsx` (plus `?? .claude/`); the commit prints `2 files changed, 264 insertions(+)` with both `create mode` lines; `git log --oneline -1` shows the new subject; the final `git status --short` lists only `?? .claude/`.
### Task 13: Query hooks, invite types and the membership change (S API client and query layer 1b; F §4.4; AC11; 1b clarifications 23, 38; 1a T18-m2, T23-m1)

This task adds the query layer the onboarding screens call, and no screen yet (Tasks 14 and 16 render these hooks). `lib/queries/onboarding.ts` holds the three onboarding mutations: `useCreateChurch`, `usePreviewInvite` and `useAcceptInvite`. They are plain `useMutation`s over `useApi().user`, so no `X-Church-Id` is sent, `retry: false` applies (`client.ts:84`), and the mutation cache's `handleAuthErrors` turns a 401 into `signOutRequired`. The invite code goes only in a POST body, never in a query key (S :462). `lib/queries/membership.ts` holds `useMembershipChanged`, the F §4.4 re-pick after a create or join: store the new church, fetch `/me` again, then `replace("/")`. It fetches `/me` through the new `meQueryOptions(api)` (1b clarification 38), because `makeQueryClient` has no default `queryFn` (`client.ts:69-87`) and `useMe` defined its fetcher inline (`me.ts:12-16`). A bare `fetchQuery({ queryKey: keys.me() })` would work only while a `useMe` observer happened to be mounted. `staleTime: 0` makes a `/me` loaded seconds ago (inside the 30 s `staleTime`) refetch, so the new church is in it before navigation.

The five membership tests were checked against four wrong implementations, and each one makes at least one test fail: `staleTime: 0` dropped (tests 2 and 5 fail), a bare `{ queryKey: keys.me() }` (all five fail), no `resetQueries` on failure (test 5 fails), and `storeChurchId(null)` for `null` (test 4 fails).

Choices made here that S leaves open (none is visible to anyone):
- `CreateChurchBody = Required<components["schemas"]["CreateChurchIn"]>`. The server defaults both fields to `""`, so the generated type may mark them optional. The form always sends both, so the key tracker never has to compare a body that is missing a field with one that has it blank.
- `useMembershipChanged` stores `selectChurchId` only when it is a non-empty id. `null`, `undefined` and `""` store nothing and keep the stored church (S: "if given"; outline test "`selectChurchId: null` stores nothing").
- If the `/me` fetch fails, the hook calls `resetQueries` without awaiting it and resolves anyway. With no `useMe` observer, `resetQueries` does not refetch. Under the app's `(signed-in)` layout, its observer's own refetch shows the skeleton and then the ErrorState with Retry (1b clarification 23). The create or join itself succeeded, so the caller still shows its success toast.
- The 1a T18-m2 mutation-401 test lives in `onboarding.test.tsx` and goes through a real hook, not in the Node `client.test.ts`.

**Files:**
- Modify: `frontend/src/lib/api/types.ts` (whole file, 9 lines: three new names after `ErrorBody`)
- Modify: `frontend/src/lib/queries/me.ts` (whole file, 17 lines: `meQueryOptions`; `useMe` spreads it)
- Modify: `frontend/src/test/fixtures/index.ts` (line 5, the type import; append after line 28, the closing `}` of `me`)
- Create: `frontend/src/lib/queries/onboarding.ts`
- Create: `frontend/src/lib/queries/membership.ts`
- Test: `frontend/src/lib/queries/onboarding.test.tsx` (new, 3 tests)
- Test: `frontend/src/lib/queries/membership.test.tsx` (new, 5 tests)

**Interfaces:**
- Consumes:
  - Task 6/7's regenerated `frontend/src/lib/api/schema.d.ts`: `components["schemas"]["CreateChurchIn"]` (`name`, `timezone`: string), `["InvitePreviewOut"]` (`church_name: string`, `role: "member" | "admin"`, `expires_at: string` (date-time), `email_bound: boolean`, `already_member: boolean`), `["InviteAcceptOut"]` (`church: ChurchOut`, `already_member: boolean`, `message: string`).
  - `useApi(): Api` and `type Api = { user: ApiCall; church: ApiCall; forChurch(id): ApiCall }` (`frontend/src/lib/queries/client.ts:113-120`, `:132-142`); `ApiCall` takes `{ method?, json?, idempotencyKey?, signal? }` (`ApiOptions`, `frontend/src/lib/api/client.ts:32-45`; `json` is sent as JSON, `idempotencyKey` as `Idempotency-Key`, `client.ts:106-114`); `ApiError` (`client.ts:12`).
  - `makeQueryClient(overrides)`: the mutation cache's `onError` runs `handleAuthErrors` (401 → `authEvents.signOutRequired()`), mutations `retry: false` (`client.ts:56-87`); `authEvents.onSignOutRequired(listener): () => void` (`frontend/src/lib/queries/auth-events.ts:25-30`).
  - `keys.me() → ["me"]` (`frontend/src/lib/queries/keys.ts:8`); `storeChurchId(id: string | null): void` (`frontend/src/lib/church.ts:65`); `useRouter()` from `next/navigation` (DOM tests: `testRouter`, `setup-dom.ts:20-27`, `test/mocks.ts:13-18`); `timeoutFor` gives `POST /churches` 30 000 ms (`frontend/src/lib/api/timeouts.ts:7`).
  - Test harness: `installFakeApi`, `fakeError`, `type FakeApi` (`frontend/src/test/fake-api.ts`); `church()`, `me()`, `CHURCH_IDS` (`frontend/src/test/fixtures/index.ts`); `ACTIVE_CHURCH_KEY = "activeChurchId"` (`frontend/src/lib/storage.ts`); `ChurchProvider` (`frontend/src/lib/church-context.tsx`).
- Produces:
  - `frontend/src/lib/api/types.ts`: `InvitePreview = components["schemas"]["InvitePreviewOut"]`, `InviteAccepted = components["schemas"]["InviteAcceptOut"]`, `CreateChurchBody = Required<components["schemas"]["CreateChurchIn"]>` (so `{ name: string; timezone: string }`). Later users: Task 14 (`JoinInvite`), Task 15 (`/join`), Task 16 (`CreateChurchForm`).
  - `frontend/src/lib/queries/me.ts`: `meQueryOptions(api: Api)` = `queryOptions<Me, ApiError>({ queryKey: keys.me(), queryFn: ({ signal }) => api.user<Me>("/me", { signal }) })`; `useMe(opts: { enabled?: boolean } = {}): UseQueryResult<Me, ApiError>` keeps its signature and behavior (`useQuery({ ...meQueryOptions(api), enabled: opts.enabled ?? true })`). Later users: `useMembershipChanged`, Task 15 (`useMe({ enabled: signedIn === true })`).
  - `frontend/src/lib/queries/onboarding.ts`:
    - `type CreateChurchVariables = { body: CreateChurchBody; key: string }`.
    - `useCreateChurch(): UseMutationResult<Church, ApiError, CreateChurchVariables>`: `POST /churches`, `json: body`, `Idempotency-Key: key`. Later user: Task 16.
    - `usePreviewInvite(): UseMutationResult<InvitePreview, ApiError, string>`: `POST /invites/preview {code}`. Later users: Task 14, Task 15.
    - `useAcceptInvite(): UseMutationResult<InviteAccepted, ApiError, string>`: `POST /invites/accept {code}`, no `Idempotency-Key`. Later users: Task 14, Task 15.
  - `frontend/src/lib/queries/membership.ts`:
    - `type MembershipChange = { selectChurchId?: string | null }`.
    - `useMembershipChanged(): (change: MembershipChange) => Promise<void>` (stable across renders). It stores `selectChurchId` when it is an id, awaits `queryClient.cancelQueries({ queryKey: keys.me() })` (an in-flight `/me` may predate the change), then `queryClient.fetchQuery({ ...meQueryOptions(api), staleTime: 0 })`, then calls `router.replace("/")`, or `router.replace("/welcome")` when `/me` lists no church. On a failed fetch it calls `queryClient.resetQueries({ queryKey: keys.me() })`, keeps the stored id and calls `router.replace("/")`. It never rejects. The docstring states 6b's `selectChurchId: null` duty (1a T23-m1). Later users: Task 14 (join/open), Task 16 (create), slice 6b (leave, delete).
  - `frontend/src/test/fixtures/index.ts`:
    - `invitePreview(overrides: Partial<InvitePreview> = {}): InvitePreview` = `{ church_name: "Grace", role: "member", expires_at: "2026-10-05T12:00:00Z", email_bound: false, already_member: false, ...overrides }`. The expiry is midday UTC, so it shows as "October 5, 2026" in every zone from UTC−11 to UTC+11.
    - `inviteAccepted(overrides: Partial<InviteAccepted> = {}): InviteAccepted` = `{ church: church({ role: "member" }), already_member: false, message: "Joined Grace.", ...overrides }` (church id `CHURCH_IDS.grace`, name "Grace").
    - Later users: Tasks 14, 15, 17.

Counts after this task: backend **799 passed, 9 skipped** (unchanged since Task 8); frontend **171 passed in 31 files** (Task 12's 163 in 29, which includes Q4's `error_state_retrying_disables_retry` from Task 11, plus 8: onboarding 3 and membership 5, in two new files). The outline's "170 / 31" is the count without Q4. The owner answered yes to Q4, so this task's count is 171.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
grep -cE '^ {8}(CreateChurchIn|InviteAcceptOut|InvitePreviewOut): \{' frontend/src/lib/api/schema.d.ts
ls frontend/src/lib/queries/onboarding.ts frontend/src/lib/queries/membership.ts 2>&1 | grep -c "No such file"
grep -c "meQueryOptions" frontend/src/lib/queries/me.ts
```

**Expected:** `git status --short` lists only `?? .claude/`, and the last commit is Task 12's. The suite prints `Test Files  29 passed (29)` and `Tests  163 passed (163)`. The three counts are `3` (Tasks 6 and 7 regenerated the three schemas), `2` (neither hook module exists yet) and `0`. If the frontend counts differ, or the first count is not `3`, stop and ask.

- [ ] **Step 2 (agent): Add the API type names and the test fixture builders**

Replace all of `frontend/src/lib/api/types.ts` (9 lines) with:

```ts
/**
 * App-facing names for the generated API types (F §1.11). schema.d.ts is
 * generated from openapi.json by `npm run gen:api`; never edit it by hand.
 */
import type { components } from "./schema";

export type Church = components["schemas"]["ChurchOut"];
export type Me = components["schemas"]["MeOut"];
export type ErrorBody = components["schemas"]["ErrorBody"];

/** `POST /invites/preview` (1b): what the invite offers. No church id: that comes with the accept. */
export type InvitePreview = components["schemas"]["InvitePreviewOut"];
/** `POST /invites/accept` (1b): the church (with the caller's role), and the toast text. */
export type InviteAccepted = components["schemas"]["InviteAcceptOut"];
/**
 * `POST /churches`'s body (1b). The schema gives both fields a "" default (a
 * missing field is the same 422 as a blank one); the app always sends both, so
 * the idempotency fingerprint of a body never depends on a left-out field.
 */
export type CreateChurchBody = Required<components["schemas"]["CreateChurchIn"]>;
```

In `frontend/src/test/fixtures/index.ts`, replace line 5:

```ts
import type { Church, Me } from "@/lib/church";
```

with:

```ts
import type { InviteAccepted, InvitePreview } from "@/lib/api/types";
import type { Church, Me } from "@/lib/church";
```

Then append one blank line and this block after line 28 (the closing `}` of `me`), at the end of the file:

```ts
/**
 * `POST /invites/preview`'s body: a member invite to Grace, not bound to an
 * email, for someone not yet a member. It expires at midday UTC, so
 * "Invite expires October 5, 2026." reads the same in every zone from UTC-11 to UTC+11.
 */
export function invitePreview(overrides: Partial<InvitePreview> = {}): InvitePreview {
  return {
    church_name: "Grace",
    role: "member",
    expires_at: "2026-10-05T12:00:00Z",
    email_bound: false,
    already_member: false,
    ...overrides,
  };
}

/** `POST /invites/accept`'s body: Pat joined Grace as a member. */
export function inviteAccepted(overrides: Partial<InviteAccepted> = {}): InviteAccepted {
  return {
    church: church({ role: "member" }),
    already_member: false,
    message: "Joined Grace.",
    ...overrides,
  };
}
```

Run:

```bash
(cd frontend && npm run typecheck)
```

**Expected:** `tsc --noEmit` prints no errors. The new names only alias Task 6/7's generated schemas, so nothing uses them yet.

- [ ] **Step 3 (agent): Write the failing tests**

Create `frontend/src/lib/queries/onboarding.test.tsx`:

```tsx
import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, onTestFinished, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import { ChurchProvider } from "@/lib/church-context";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, inviteAccepted, invitePreview } from "@/test/fixtures";

import { authEvents } from "./auth-events";
import { makeQueryClient } from "./client";
import { useAcceptInvite, useCreateChurch, usePreviewInvite } from "./onboarding";

const KEY = "0b9f8a52-3c1d-4e6f-9a7b-2c4d6e8f0a1b";

/** Renders `hook` inside a `ChurchProvider`, so a church header on a user-scoped call would show. */
function renderInChurch<T>(hook: () => T): { current: T } {
  const queryClient = makeQueryClient({ queries: { retry: false } });
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ChurchProvider value={church()}>{children}</ChurchProvider>
      </QueryClientProvider>
    );
  }
  return renderHook(hook, { wrapper: Wrapper }).result;
}

describe("onboarding mutations", () => {
  it("useCreateChurch posts the body with the Idempotency-Key and no X-Church-Id", async () => {
    const created = church({ id: CHURCH_IDS.hope, name: "New Life", role: "owner" });
    const api = installFakeApi({ "POST /churches": { status: 201, body: created } });
    const result = renderInChurch(() => useCreateChurch());

    let data: unknown;
    await act(async () => {
      data = await result.current.mutateAsync({
        body: { name: "New Life", timezone: "America/Chicago" },
        key: KEY,
      });
    });

    expect(data).toEqual(created);
    expect(api.requests.map((req) => [req.method, req.path, req.body])).toEqual([
      ["POST", "/churches", { name: "New Life", timezone: "America/Chicago" }],
    ]);
    expect(api.requests[0].headers["Idempotency-Key"]).toBe(KEY);
    expect(api.requests[0].headers["X-Church-Id"]).toBeUndefined();
  });

  it("usePreviewInvite and useAcceptInvite post only {code}, with no key and no church header", async () => {
    const api = installFakeApi({
      "POST /invites/preview": invitePreview(),
      "POST /invites/accept": inviteAccepted(),
    });
    const preview = renderInChurch(() => usePreviewInvite());
    const accept = renderInChurch(() => useAcceptInvite());

    let previewed: unknown;
    let accepted: unknown;
    await act(async () => {
      previewed = await preview.current.mutateAsync("ABC123");
      accepted = await accept.current.mutateAsync("ABC123");
    });

    expect(previewed).toEqual(invitePreview());
    expect(accepted).toEqual(inviteAccepted());
    expect(api.requests.map((req) => [req.method, req.path, req.body])).toEqual([
      ["POST", "/invites/preview", { code: "ABC123" }],
      ["POST", "/invites/accept", { code: "ABC123" }],
    ]);
    for (const req of api.requests) {
      expect(req.headers["Idempotency-Key"]).toBeUndefined();
      expect(req.headers["X-Church-Id"]).toBeUndefined();
    }
  });

  it("a 401 from a mutation asks for sign-out (1a T18-m2)", async () => {
    installFakeApi({ "POST /invites/preview": fakeError(401, "unauthenticated", "Please sign in.") });
    const signOutRequired = vi.fn();
    onTestFinished(authEvents.onSignOutRequired(signOutRequired));
    const preview = renderInChurch(() => usePreviewInvite());

    let error: unknown;
    await act(async () => {
      error = await preview.current.mutateAsync("ABC123").catch((e: unknown) => e);
    });

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(401);
    expect(signOutRequired).toHaveBeenCalledTimes(1);
  });
});
```

Create `frontend/src/lib/queries/membership.test.tsx`:

```tsx
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { Me } from "@/lib/api/types";
import { storeChurchId } from "@/lib/church";
import { ACTIVE_CHURCH_KEY } from "@/lib/storage";
import { type FakeApi, fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";

import { makeQueryClient } from "./client";
import { keys } from "./keys";
import { useMembershipChanged } from "./membership";

const GRACE = church();
const HOPE = church({ id: CHURCH_IDS.hope, name: "Hope", role: "owner" });

/**
 * The hook on its own: no `useMe` observer is mounted, so nothing lends `["me"]`
 * a `queryFn` (the hook must bring its own, `meQueryOptions`).
 */
function renderMembershipChanged(queryClient: QueryClient = makeQueryClient({ queries: { retry: false } })) {
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  const { result } = renderHook(() => useMembershipChanged(), { wrapper: Wrapper });
  return { changed: result.current, queryClient };
}

function meRequestCount(api: FakeApi): number {
  return api.requests.filter((req) => req.method === "GET" && req.path === "/me").length;
}

function storedChurchId(): string | null {
  return window.localStorage.getItem(ACTIVE_CHURCH_KEY);
}

describe("useMembershipChanged", () => {
  it("with no useMe mounted, stores the id and has the new /me before replace('/')", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [GRACE, HOPE] }) });
    const { changed, queryClient } = renderMembershipChanged();
    let atReplace: { meRequests: number; stored: string | null; cached: Me | undefined } | undefined;
    testRouter.replace.mockImplementation(() => {
      atReplace = {
        meRequests: meRequestCount(api),
        stored: storedChurchId(),
        cached: queryClient.getQueryData<Me>(keys.me()),
      };
    });

    await act(() => changed({ selectChurchId: CHURCH_IDS.hope }));

    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(atReplace).toEqual({
      meRequests: 1,
      stored: CHURCH_IDS.hope,
      cached: me({ churches: [GRACE, HOPE] }),
    });
  });

  it("refetches a /me cached moments ago (staleTime: 0)", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [GRACE, HOPE] }) });
    const queryClient = makeQueryClient({ queries: { retry: false } });
    queryClient.setQueryData(keys.me(), me()); // just loaded: well inside the 30 s staleTime
    const { changed } = renderMembershipChanged(queryClient);

    await act(() => changed({ selectChurchId: CHURCH_IDS.hope }));

    expect(meRequestCount(api)).toBe(1);
    expect(queryClient.getQueryData<Me>(keys.me())?.churches.map((c) => c.name)).toEqual(["Grace", "Hope"]);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it("goes to /welcome when /me lists no church", async () => {
    installFakeApi({ "GET /me": me({ churches: [] }) });
    const { changed } = renderMembershipChanged();

    await act(() => changed({}));

    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(testRouter.replace).toHaveBeenCalledWith("/welcome");
    expect(storedChurchId()).toBeNull();
  });

  it("selectChurchId: null stores nothing and keeps the stored church", async () => {
    const api = installFakeApi({ "GET /me": me() });
    storeChurchId(CHURCH_IDS.grace);
    const { changed } = renderMembershipChanged();

    await act(() => changed({ selectChurchId: null }));

    expect(storedChurchId()).toBe(CHURCH_IDS.grace);
    expect(meRequestCount(api)).toBe(1);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it("a failed /me resets the cached /me, keeps the stored id and still goes to /", async () => {
    const api = installFakeApi({ "GET /me": fakeError(500, "internal_error", "Something went wrong.") });
    const queryClient = makeQueryClient({ queries: { retry: false } });
    queryClient.setQueryData(keys.me(), me()); // the old list, without Hope
    const { changed } = renderMembershipChanged(queryClient);

    await act(() => changed({ selectChurchId: CHURCH_IDS.hope })); // resolves: the change itself succeeded

    expect(meRequestCount(api)).toBe(1);
    expect(queryClient.getQueryData(keys.me())).toBeUndefined();
    expect(storedChurchId()).toBe(CHURCH_IDS.hope);
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });
});
```

- [ ] **Step 4 (agent): Run the tests to verify they fail**

```bash
(cd frontend && npx vitest run src/lib/queries/onboarding.test.tsx src/lib/queries/membership.test.tsx 2>&1 | grep -E "FAIL|Error:|Test Files|Tests ")
```

**Expected** (both files fail to load, because neither module exists):

```
 FAIL  |dom| src/lib/queries/membership.test.tsx [ src/lib/queries/membership.test.tsx ]
Error: Failed to resolve import "./membership" from "src/lib/queries/membership.test.tsx". Does the file exist?
 FAIL  |dom| src/lib/queries/onboarding.test.tsx [ src/lib/queries/onboarding.test.tsx ]
Error: Failed to resolve import "./onboarding" from "src/lib/queries/onboarding.test.tsx". Does the file exist?
 Test Files  2 failed (2)
      Tests  no tests
```

- [ ] **Step 5 (agent): Export `meQueryOptions` from `frontend/src/lib/queries/me.ts`**

Replace all of `frontend/src/lib/queries/me.ts` (17 lines) with:

```ts
import { queryOptions, useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Me } from "@/lib/api/types";

import { useApi, type Api } from "./client";
import { keys } from "./keys";

/**
 * `GET /me`'s key and fetcher, for every caller (1b clarification 38).
 * `makeQueryClient` has no default `queryFn`, so a bare
 * `fetchQuery({ queryKey: keys.me() })` works only while a `useMe` observer
 * happens to be mounted; `useMembershipChanged` spreads these options instead.
 */
export function meQueryOptions(api: Api) {
  return queryOptions<Me, ApiError>({
    queryKey: keys.me(),
    queryFn: ({ signal }) => api.user<Me>("/me", { signal }),
  });
}

/** `GET /me` (user-scoped): the user and their churches, sorted by name. The `(signed-in)` layout passes `enabled: false` while signing out. */
export function useMe(opts: { enabled?: boolean } = {}): UseQueryResult<Me, ApiError> {
  const api = useApi();
  return useQuery({ ...meQueryOptions(api), enabled: opts.enabled ?? true });
}
```

- [ ] **Step 6 (agent): Create `frontend/src/lib/queries/onboarding.ts`**

```ts
/**
 * Onboarding mutations (S "API client and query layer", slice 1b). All three
 * are user-scoped (`useApi().user`: no `X-Church-Id`) plain `useMutation`s, so
 * `retry: false` and the mutation cache's `handleAuthErrors` apply (a 401 asks
 * the `(signed-in)` layout, or `/join`, to sign out). The invite code is a
 * secret: it travels only in a POST body, never in a query key, a path or a
 * query string (AC9). No hook shows a toast: each component chooses an inline
 * message or a toast (1b clarification 26).
 */
import { useMutation, type UseMutationResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Church, CreateChurchBody, InviteAccepted, InvitePreview } from "@/lib/api/types";

import { useApi } from "./client";

/** `useCreateChurch`'s variables: the body, and the key from the form's `createKeyTracker().keyFor(body)`. */
export type CreateChurchVariables = { body: CreateChurchBody; key: string };

/**
 * `POST /churches` with `Idempotency-Key: key`: 201 `ChurchOut` (role "owner").
 * The form owns the key (lib/idempotency.ts) and reuses it only to retry an
 * identical body after an uncertain outcome. Times out after 30 s
 * (lib/api/timeouts.ts).
 */
export function useCreateChurch(): UseMutationResult<Church, ApiError, CreateChurchVariables> {
  const api = useApi();
  return useMutation<Church, ApiError, CreateChurchVariables>({
    mutationFn: ({ body, key }) =>
      api.user<Church>("/churches", { method: "POST", json: body, idempotencyKey: key }),
  });
}

/** `POST /invites/preview {code}` (read-only). The variable is the invite code. */
export function usePreviewInvite(): UseMutationResult<InvitePreview, ApiError, string> {
  const api = useApi();
  return useMutation<InvitePreview, ApiError, string>({
    mutationFn: (code) => api.user<InvitePreview>("/invites/preview", { method: "POST", json: { code } }),
  });
}

/**
 * `POST /invites/accept {code}`: joins, or reports that the caller is already a
 * member. No Idempotency-Key: a repeat accept is safe by construction (S Idempotency).
 */
export function useAcceptInvite(): UseMutationResult<InviteAccepted, ApiError, string> {
  const api = useApi();
  return useMutation<InviteAccepted, ApiError, string>({
    mutationFn: (code) => api.user<InviteAccepted>("/invites/accept", { method: "POST", json: { code } }),
  });
}
```

- [ ] **Step 7 (agent): Create `frontend/src/lib/queries/membership.ts`**

```ts
/**
 * After a membership change (F §4.4 invalidation map: "create, join, leave or
 * delete church → ["me"], then a re-pick"; S "queries/membership.ts").
 */
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { storeChurchId } from "@/lib/church";

import { useApi } from "./client";
import { keys } from "./keys";
import { meQueryOptions } from "./me";

/** `selectChurchId`: the church to open next (create, join, open); `null` or left out stores nothing. */
export type MembershipChange = { selectChurchId?: string | null };

/**
 * Returns `changed({ selectChurchId })`, which a component awaits after a
 * create, join or open succeeded:
 * 1. stores `selectChurchId` as the active church when it is a church id;
 * 2. fetches `/me` again with `staleTime: 0` (even one loaded seconds ago; an
 *    in-flight `/me` is cancelled first, so it is never reused), so
 *    the new church is in `/me` **before** navigating; otherwise the `(church)`
 *    layout's `pickActiveChurch` would fall back and overwrite the stored id;
 * 3. `router.replace("/")`, or `"/welcome"` when `/me` lists no church.
 *
 * If that `/me` fetch fails (1b clarification 23), the cached `/me` is reset,
 * the stored id is kept and it still goes to `/`: the `(signed-in)` layout
 * shows its skeleton, then an ErrorState with Retry, until `/me` loads, so the
 * `(church)` layout never picks from the old list. It never throws: the change
 * itself succeeded, so the caller still shows its success toast.
 *
 * Slice 6b calls it with `selectChurchId: null` after a leave or delete, while
 * the `(church)` layout still shows the church just left. Any refetch of that
 * church's `GET /church` answers 403 `no_church_access`, and the layout's
 * lost-access toast would fire for a voluntary leave (1a T23-m1). So 6b must
 * have the new `/me` (step 2) before anything refetches that church, or leave
 * `(church)` first.
 */
export function useMembershipChanged(): (change: MembershipChange) => Promise<void> {
  const api = useApi();
  const queryClient = useQueryClient();
  const router = useRouter();
  return useCallback(
    async ({ selectChurchId }: MembershipChange) => {
      if (selectChurchId) storeChurchId(selectChurchId);
      let hasChurch = true;
      try {
        // A /me already in flight may predate the change; fetchQuery would reuse it.
        await queryClient.cancelQueries({ queryKey: keys.me() });
        const me = await queryClient.fetchQuery({ ...meQueryOptions(api), staleTime: 0 });
        hasChurch = me.churches.length > 0;
      } catch {
        void queryClient.resetQueries({ queryKey: keys.me() });
      }
      router.replace(hasChurch ? "/" : "/welcome");
    },
    [api, queryClient, router],
  );
}
```

- [ ] **Step 8 (agent): Run the tests to verify they pass, then the whole frontend and backend suites**

```bash
(cd frontend && npx vitest run src/lib/queries/onboarding.test.tsx src/lib/queries/membership.test.tsx 2>&1 | grep -E "✓|×|Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:**
- The first command prints `✓ |dom| src/lib/queries/onboarding.test.tsx (3 tests)` and `✓ |dom| src/lib/queries/membership.test.tsx (5 tests)` (in either order), then `Test Files  2 passed (2)` and `Tests  8 passed (8)`.
- The second prints `Test Files  31 passed (31)` and `Tests  171 passed (171)` (163 + 8). The 1a `(signed-in)` and `(church)` layout tests still pass, so `useMe` behaves as before. `tsc --noEmit` and `eslint` print no errors.
- The backend prints `799 passed, 9 skipped in <t>s` (no backend change).
- `git status --short` lists exactly these paths, plus `?? .claude/`:

```
 M frontend/src/lib/api/types.ts
 M frontend/src/lib/queries/me.ts
 M frontend/src/test/fixtures/index.ts
?? frontend/src/lib/queries/membership.test.tsx
?? frontend/src/lib/queries/membership.ts
?? frontend/src/lib/queries/onboarding.test.tsx
?? frontend/src/lib/queries/onboarding.ts
```

If a test fails, check these first:
- Every membership test fails and no `GET /me` is recorded: the hook passes a bare `{ queryKey: keys.me() }`. TanStack then rejects with `Missing queryFn`, because no `useMe` observer is mounted.
- Test 2 records no `GET /me`: `staleTime: 0` is missing, so TanStack returns the fresh cached `/me`.
- Test 5 still sees the old `/me` in the cache: the failure path is missing `resetQueries`.
- An onboarding test sees an `X-Church-Id` header: a hook called `useApi().church` instead of `useApi().user`. The 401 test sees `signOutRequired` called 0 times: `mutationFn` caught the error itself, so the mutation never failed.

- [ ] **Step 9 (agent): Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/lib/queries/me.ts frontend/src/test/fixtures/index.ts \
        frontend/src/lib/queries/onboarding.ts frontend/src/lib/queries/onboarding.test.tsx \
        frontend/src/lib/queries/membership.ts frontend/src/lib/queries/membership.test.tsx
git status --short
git commit -m "Frontend: onboarding query hooks, invite types and useMembershipChanged (F §4.4; S API client and query layer; 1b clarifications 23, 38; 1a T18-m2, T23-m1)

onboarding.ts: useCreateChurch posts the create body with the form's
Idempotency-Key; usePreviewInvite and useAcceptInvite post {code} only.
All three are user-scoped mutations (no X-Church-Id, no retry), and a 401
from any of them asks for sign-out through the mutation cache. The code
never enters a query key. membership.ts: useMembershipChanged stores the
new church, fetches /me with staleTime 0 through meQueryOptions (no useMe
observer needed), then replaces to / or /welcome. If that fetch fails it
resets the cached /me, keeps the stored id and still goes to /. me.ts
exports meQueryOptions, and useMe spreads it. types.ts names
InvitePreview, InviteAccepted and CreateChurchBody; the fixtures gain
invitePreview() and inviteAccepted().

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** before the commit, `git status --short` lists the same seven paths staged (`M ` and `A ` in the first column), plus `?? .claude/`. After it, `git log` prints `<sha> Frontend: onboarding query hooks, invite types and useMembershipChanged (F §4.4; S API client and query layer; 1b clarifications 23, 38; 1a T18-m2, T23-m1)`, and `git status --short` lists only `?? .claude/`.
### Task 14: `JoinInvite`: the invite preview card, then a Join tap; the Streamlit `pick_invite_code` tests ported and removed (S Flow A Join tab, Flow B steps 4–6, Pages, Loading table; AC10 code side; AC16 frontend half; 1b clarifications 18, 29, 35, 48)

This task builds the one component both onboarding pages use to join a church with a code. `/welcome`'s Join tab (Task 17) shows it with the "Invite link or code" field; `/join` (Task 15) shows it without the field and passes the captured code with `autoPreview`. It previews first and joins only on an explicit tap (owner decision 1, amendment to decision 6). The states follow S Pages: `enter` (the field only) → `previewing` (skeleton card) → `preview` (church, role, expiry; or the single "already a member" line) → `joining` → `done` (navigating); `rejected` (the server's message and the next step); `error` (preview could not reach the server: inline `ErrorState` with Retry, code kept). Rejection text lives only in component state, never in storage.

It also finishes AC16's port-then-delete (F §2.3.7; clarification 48). Tasks 3 and 5 already removed the create and accept tests from `streamlit_tests/test_onboarding.py`. The three `pick_invite_code` tests left there are ported here as JoinInvite tests (clarification 35; behavior change 16: the field is prefilled with the pending code, and exactly its content is used). The file is then deleted in the same commit:

| Streamlit assert (`streamlit_tests/test_onboarding.py` at `0295b37`) | JoinInvite test |
|---|---|
| `:5-6` typed wins over pending | "an edited field wins over the prefilled pending code (port: typed wins over pending)" |
| `:9-11` falls back to pending (`""`, `None`) | "an untouched prefilled code is previewed once, even in StrictMode (port: falls back to pending)" |
| `:14-16` blank when neither (`None`, `"  "`) | "a blank field shows the client message, …" and "whitespace-only pending code and field send nothing (port: blank when neither)" |

Choices made here that S leaves open (none changes any copy S fixes):
- **Any 4xx other than 401 from preview or accept is a rejection.** A 400 `invite_rejected` uses `details.reason`. Anything else, such as the 422 "Too long (max 256 characters)." for a code over 256 characters, shows its `fields.code` (or its message) on the same card with reason `unknown`, so the card says "Ask for a new invite link." and clears the pending code.
- **Switching accounts stores the code in use first.** Both "Use a different Google account" (card) and "Use a different account" (footer) run `writeSession(SESSION_KEYS.pendingInviteCode, code)`, then `signOut({ keepPendingInvite: true, next: "/join", selectAccount: true })` (clarification 18). S says "the pending code is kept". For `/join` that is already so. For a code typed on `/welcome`, which was never stored, this makes it survive the new sign-in too, because `/join` reads it back.
- **Join uses the previewed code**, not whatever the field holds by then.
- **A 401, or a request cancelled by a sign-out (`aborted`), changes nothing here.** The mutation cache's `handleAuthErrors` asks the page to sign out: the `(signed-in)` layout for `/welcome`, and Task 15's subscriber for `/join`. There is no toast, and the skeleton or pending button stays until the navigation.
- **Auto-preview runs once per mount.** A ref is set in the `useState`-time render and emptied by the first effect run, so StrictMode's second effect sends nothing (clarification 29 says "once per code"). The two callers pass a code that is stable for the component's life: Task 15 captures it once, and Task 17 reads it in a `useState` initializer. On `/welcome` a tab switch (Join → Create → Join) unmounts and remounts the Join panel (Base UI `Tabs` unmount an inactive panel), so the same code is previewed again, and a rejected code shows its rejection card again. The preview is read-only, so this is accepted.
- **"Go to home" and "Not now" use `router.replace("/")`**, not `next/link` (the same navigation as "Not now"; `/join`'s signed-out card in Task 15 and `/welcome`'s "← Back to …" link in Task 17 are the `next/link` users). Continue is disabled while a preview or join is in flight. The `done` state keeps "Joining…" until the navigation, so a second tap cannot resend.
- **The success toast comes after `useMembershipChanged` resolves**, in S Flow B step 5's order: clear the code, then `useMembershipChanged`, then the toast. Task 13's hook never rejects.
- **Accessibility:** the skeleton card is `role="status"` with `aria-label="Loading invite"` (screen-reader only). The rejection card is `role="alert"`. The church name and the rejection message are `<h2>` inside `CardTitle`. The field has `aria-invalid` and `aria-describedby` (helper plus error).
- **The StrictMode test renders with RTL's `reactStrictMode: true`** (StrictMode at the root, around a hand-built `QueryClientProvider`). This was verified in a throwaway worktree on React 19.2.8: a `<StrictMode>` nested inside `renderWithProviders`' wrapper does **not** double-invoke effects, so such a test would pass even without the guard. Step 6 proves that the test catches a missing guard.

**Files:**
- Create: `frontend/src/components/onboarding/join-invite.tsx`
- Delete: `streamlit_tests/test_onboarding.py` (at this point it holds only the three `pick_invite_code` tests; Task 3 removed the create test, Task 5 the accept test)
- Test: `frontend/src/components/onboarding/join-invite.test.tsx` (new, 21 tests)

**Interfaces:**
- Consumes:
  - Task 13: `usePreviewInvite(): UseMutationResult<InvitePreview, ApiError, string>` and `useAcceptInvite(): UseMutationResult<InviteAccepted, ApiError, string>` (`frontend/src/lib/queries/onboarding.ts`; this task uses their stable `mutateAsync`); `useMembershipChanged(): (change: MembershipChange) => Promise<void>` with `MembershipChange = { selectChurchId?: string | null }` (`frontend/src/lib/queries/membership.ts`; stores the id, fetches `/me` with `staleTime: 0`, `router.replace("/")`, never rejects); `InvitePreview` = `{ church_name: string; role: "member" | "admin"; expires_at: string; email_bound: boolean; already_member: boolean }` and `InviteAccepted` = `{ church: Church; already_member: boolean; message: string }` (`frontend/src/lib/api/types.ts`); fixtures `invitePreview(overrides?)` (default Grace, member, `expires_at: "2026-10-05T12:00:00Z"`, not email-bound, not a member) and `inviteAccepted(overrides?)` (default `church({ role: "member" })`, `"Joined Grace."`) in `frontend/src/test/fixtures/index.ts`.
  - Task 10: `useSignOut()` → `(opts?: SignOutOptions) => Promise<void>` with `SignOutOptions = { keepPendingInvite?: boolean; next?: string; selectAccount?: boolean }` (`frontend/src/lib/auth.ts`; `{ keepPendingInvite: true, next: "/join", selectAccount: true }` → `supabase.auth.signOut({ scope: "local" })`, then `router.replace("/login?next=%2Fjoin&select_account=1")`).
  - Task 9: `errorToastMessage(e: unknown): string` (`frontend/src/lib/api/errors.ts`): `e.message` for `network_error`/`timeout`/`aborted`, else `describeError(e)`.
  - 1a: `extractInviteCode(input: string): string` (`frontend/src/lib/urls.ts:54`); `SESSION_KEYS.pendingInviteCode = "wsb:pendingInviteCode"`, `writeSession`, `removeSession` (`frontend/src/lib/storage.ts:8-11`, `:49`, `:53`); `ApiError` (re-exported at `frontend/src/lib/api/errors.ts:4`; `status`, `code`, `message`, `fields?`, `details?`, `requestId?`) and `InviteRejectReason` (`errors.ts:65-71`); `PendingButton({ pending, pendingLabel, … })` (`frontend/src/components/app/pending-button.tsx:13`); `ErrorState({ error, onRetry })` (`frontend/src/components/app/error-state.tsx`; Task 11 adds an optional `retrying`, not used here); generated `Button` (`size="touch"` = `h-11`), `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`, `Input`, `Label`, `Skeleton`; `toast` from `sonner`; `useRouter` from `next/navigation`.
  - Tests: `renderWithProviders` (`frontend/src/test/render.tsx:33`), `installFakeApi`, `fakeError`, `FakeApi` (`frontend/src/test/fake-api.ts`; `fakeError` sets `request_id` `4f9a2c1e…`), `testRouter`, `supabaseAuth` (`frontend/src/test/mocks.ts`), `makeQueryClient` (`frontend/src/lib/queries/client.ts:69`), `NETWORK_MESSAGE` (`frontend/src/lib/api/client.ts:50`), `CHURCH_IDS`, `church`, `me` (fixtures).
- Produces:
  - `frontend/src/components/onboarding/join-invite.tsx`: `JoinInvite({ initialCode?: string; autoPreview?: boolean; email: string; showEntry: boolean })` (`"use client"`), `export type JoinInviteProps`, `export const BLANK_CODE_MESSAGE = "Enter an invite code, or open your invite link again."`. Later users: Task 15 (`<JoinInvite initialCode={code} autoPreview email={me.user.email} showEntry={false} />`) and Task 17 (`<JoinInvite initialCode={pending ?? ""} autoPreview email={…} showEntry />`).
  - Copy (verbatim; S Flow A step 3, Flow B steps 4–6): label "Invite link or code"; helper "Paste the link or code from your invite."; button "Continue"; blank → "Enter an invite code, or open your invite link again."; preview title `{church_name}`; "You're invited to join as a member." / "You're invited to join as an admin."; "This invite is for {email}." (email-bound only); "Invite expires {Month D, YYYY}." (browser zone, `en-US` long month); `already_member` → only "You're already a member of {church_name}."; buttons "Join {church_name}" / "Open {church_name}" (pending "Joining…") and "Not now"; footer "Signed in as {email} ·" + "Use a different account"; rejection: the server message + "Ask for a new invite link." + "Go to home", or for `email_mismatch` "You're signed in as {email}." + "Use a different Google account"; accept success toast = the server `message`; accept network/timeout/5xx toast = `errorToastMessage(e)`.

Counts after this task: backend **796 passed, 9 skipped** (Task 8's 799 minus the three ported Streamlit tests); frontend **192 passed in 32 files** (Task 13's 171 in 31, which includes Q4's extra test, plus 21 in one new file). The outline's "191 / 32" is the count without Q4.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
.venv/bin/python -m pytest -q | tail -1
grep -c "^def test_" streamlit_tests/test_onboarding.py
grep -c "accept_invite\|create_church" streamlit_tests/test_onboarding.py
grep -cE "export function (usePreviewInvite|useAcceptInvite|useMembershipChanged)" frontend/src/lib/queries/onboarding.ts frontend/src/lib/queries/membership.ts
grep -cE "export function (invitePreview|inviteAccepted)" frontend/src/test/fixtures/index.ts
grep -c "selectAccount" frontend/src/lib/auth.ts
grep -c "export function errorToastMessage" frontend/src/lib/api/errors.ts
ls frontend/src/components/onboarding 2>&1 | grep -c "No such file"
```

**Expected:** `git status --short` lists only `?? .claude/`, and the last commit is Task 13's. The frontend prints `Test Files  31 passed (31)` and `Tests  171 passed (171)`. The backend prints `799 passed, 9 skipped in <t>s`. Then: `3` (only the `pick_invite_code` tests are left), `0` (Tasks 3 and 5 removed the create and accept tests), `frontend/src/lib/queries/onboarding.ts:2` and `frontend/src/lib/queries/membership.ts:1`, `2`, a number of at least `2` (Task 10's `SignOutOptions.selectAccount` and its use), `1`, `1` (the directory does not exist yet). If a count differs, stop and ask.

- [ ] **Step 2 (agent): Write the failing test**

Create `frontend/src/components/onboarding/join-invite.test.tsx`:

```tsx
/**
 * `JoinInvite` against the fake API (S Flow A Join tab, Flow B steps 4-6, Loading
 * table rows "Preview" and "Accept / Create"; AC10 code side). The first four
 * tests are the AC16 ports of `streamlit_tests/test_onboarding.py`'s three
 * `pick_invite_code` tests (clarification 35): blank or whitespace-only sends
 * nothing, an edited field wins, an untouched prefilled code is used.
 */
import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { NETWORK_MESSAGE } from "@/lib/api/client";
import { makeQueryClient } from "@/lib/queries/client";
import { ACTIVE_CHURCH_KEY, SESSION_KEYS } from "@/lib/storage";
import { type FakeApi, fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, inviteAccepted, invitePreview, me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { JoinInvite } from "./join-invite";

const EMAIL = "pat@example.com";
const CODE = "GRACE-CODE-1";
const BLANK = "Enter an invite code, or open your invite link again.";
/** Midday UTC, so the date reads the same in every runner time zone. */
const EXPIRES_AT = "2026-10-05T12:00:00Z";

const MEMBER_PREVIEW = invitePreview({
  church_name: "Grace",
  role: "member",
  expires_at: EXPIRES_AT,
  email_bound: false,
  already_member: false,
});
const JOINED = inviteAccepted({
  church: church({ role: "member" }),
  already_member: false,
  message: "Joined Grace.",
});

const REJECTIONS = [
  ["unknown", "Invalid invite code."],
  ["revoked", "This invite has been revoked."],
  ["expired", "This invite has expired."],
  ["used", "This invite has already been used."],
  ["church_unavailable", "This church is no longer available."],
] as const;

function rejected(reason: string, message: string) {
  return fakeError(400, "invite_rejected", message, { details: { reason } });
}

type Props = ComponentProps<typeof JoinInvite>;

/** `/join`'s use unless overridden: the captured code, previewed on mount, no field. */
function renderJoin(props: Partial<Props> = {}) {
  return renderWithProviders(
    <JoinInvite email={EMAIL} initialCode={CODE} autoPreview showEntry={false} {...props} />,
  );
}

function sent(api: FakeApi, path: string): unknown[] {
  return api.requests.filter((r) => r.method === "POST" && r.path === path).map((r) => r.body);
}

/** The last `router.replace` went to `/login?next=/join&select_account=1` (parsed: 1a encodes `next`). */
function expectAccountChooserLogin(): void {
  const target = testRouter.replace.mock.calls.at(-1)?.[0];
  expect(typeof target).toBe("string");
  const url = new URL(target as string, "http://localhost");
  expect(url.pathname).toBe("/login");
  expect(url.searchParams.get("next")).toBe("/join");
  expect(url.searchParams.get("select_account")).toBe("1");
}

describe("JoinInvite", () => {
  let toastSuccess: MockInstance<typeof toast.success>;
  let toastError: MockInstance<typeof toast.error>;

  beforeEach(() => {
    toastSuccess = vi.spyOn(toast, "success").mockImplementation(() => 0);
    toastError = vi.spyOn(toast, "error").mockImplementation(() => 0);
  });

  afterEach(() => {
    toastSuccess.mockRestore();
    toastError.mockRestore();
  });

  it("a blank field shows the client message, focuses the field and sends nothing", async () => {
    const api = installFakeApi({});
    const { user } = renderJoin({ initialCode: undefined, autoPreview: false, showEntry: true });

    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText(BLANK)).toBeInTheDocument();
    const field = screen.getByLabelText("Invite link or code");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(field).toHaveFocus();
    expect(api.requests).toHaveLength(0);
  });

  it("whitespace-only pending code and field send nothing (port: blank when neither)", async () => {
    const api = installFakeApi({});
    const { user } = renderJoin({ initialCode: "  ", autoPreview: true, showEntry: true });

    expect(screen.queryByRole("status", { name: "Loading invite" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText(BLANK)).toBeInTheDocument();
    expect(api.requests).toHaveLength(0);
  });

  it("an edited field wins over the prefilled pending code (port: typed wins over pending)", async () => {
    const api = installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    const { user } = renderJoin({ initialCode: "PENDING", autoPreview: false, showEntry: true });

    const field = screen.getByLabelText("Invite link or code");
    expect(field).toHaveValue("PENDING");
    await user.clear(field);
    await user.type(field, "TYPED");
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(sent(api, "/invites/preview")).toEqual([{ code: "TYPED" }]);
  });

  it("an untouched prefilled code is previewed once, even in StrictMode (port: falls back to pending)", async () => {
    const api = installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    // StrictMode at the root: React double-invokes effects only there, not for a
    // <StrictMode> nested inside renderWithProviders' wrapper.
    render(
      <QueryClientProvider client={makeQueryClient({ queries: { retry: false } })}>
        <JoinInvite email={EMAIL} initialCode="PENDING" autoPreview showEntry />
      </QueryClientProvider>,
      { reactStrictMode: true },
    );

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(sent(api, "/invites/preview")).toEqual([{ code: "PENDING" }]);
  });

  it("a pasted invite link sends only its code", async () => {
    const api = installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    const { user } = renderJoin({ initialCode: undefined, autoPreview: false, showEntry: true });

    await user.type(
      screen.getByLabelText("Invite link or code"),
      "https://worship-service-builder.vercel.app/join?code=ABC123",
    );
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(sent(api, "/invites/preview")).toEqual([{ code: "ABC123" }]);
  });

  it("shows a skeleton card while the preview loads (S Loading table)", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    installFakeApi({
      "POST /invites/preview": async () => {
        await gate;
        return MEMBER_PREVIEW;
      },
    });
    renderJoin();

    expect(screen.getByRole("status", { name: "Loading invite" })).toBeInTheDocument();
    release();
    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: "Loading invite" })).not.toBeInTheDocument();
  });

  it("member preview: role line and expiry, no email line, Join and Not now, footer", async () => {
    installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    renderJoin();

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(screen.getByText("You're invited to join as a member.")).toBeInTheDocument();
    expect(screen.getByText("Invite expires October 5, 2026.")).toBeInTheDocument();
    expect(screen.queryByText(/This invite is for/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Join Grace" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Not now" })).toBeEnabled();
    expect(screen.getByText(`Signed in as ${EMAIL} ·`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Use a different account" })).toBeInTheDocument();
  });

  it("admin, email-bound preview: admin role line and the email line", async () => {
    installFakeApi({
      "POST /invites/preview": invitePreview({ ...MEMBER_PREVIEW, role: "admin", email_bound: true }),
    });
    renderJoin();

    expect(await screen.findByText("You're invited to join as an admin.")).toBeInTheDocument();
    expect(screen.getByText(`This invite is for ${EMAIL}.`)).toBeInTheDocument();
    expect(screen.getByText("Invite expires October 5, 2026.")).toBeInTheDocument();
  });

  it("already a member: one line, and Open Grace accepts, selects the church and toasts the server message", async () => {
    const api = installFakeApi({
      "POST /invites/preview": invitePreview({ ...MEMBER_PREVIEW, role: "admin", already_member: true }),
      "POST /invites/accept": inviteAccepted({
        church: church(),
        already_member: true,
        message: "You're already a member of Grace.",
      }),
      "GET /me": me(),
    });
    const { user } = renderJoin();

    expect(await screen.findByText("You're already a member of Grace.")).toBeInTheDocument();
    expect(screen.queryByText(/You're invited to join/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Invite expires/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open Grace" }));

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith("You're already a member of Grace."));
    expect(sent(api, "/invites/accept")).toEqual([{ code: CODE }]);
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(CHURCH_IDS.grace);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it("Join Grace: pending while accepting, then clears the code, selects the church and toasts", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const api = installFakeApi({
      "POST /invites/preview": MEMBER_PREVIEW,
      "POST /invites/accept": async () => {
        await gate;
        return JOINED;
      },
      "GET /me": me(),
    });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Join Grace" }));
    expect(screen.getByRole("button", { name: "Joining…" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Not now" })).toBeDisabled();
    release();

    await waitFor(() => expect(toastSuccess).toHaveBeenCalledWith("Joined Grace."));
    expect(sent(api, "/invites/accept")).toEqual([{ code: CODE }]);
    expect(api.requests.some((r) => r.method === "GET" && r.path === "/me")).toBe(true);
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(CHURCH_IDS.grace);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it.each(REJECTIONS)("preview rejected (%s): message, ask for a new link, code cleared, Go to home", async (reason, message) => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    installFakeApi({ "POST /invites/preview": rejected(reason, message) });
    const { user } = renderJoin();

    const card = await screen.findByRole("alert");
    expect(within(card).getByRole("heading", { name: message })).toBeInTheDocument();
    expect(within(card).getByText("Ask for a new invite link.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    await user.click(within(card).getByRole("button", { name: "Go to home" }));
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it("an accept that loses the race (400 used) shows the rejection card and clears the code", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    installFakeApi({
      "POST /invites/preview": MEMBER_PREVIEW,
      "POST /invites/accept": rejected("used", "This invite has already been used."),
    });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Join Grace" }));

    const card = await screen.findByRole("alert");
    expect(within(card).getByRole("heading", { name: "This invite has already been used." })).toBeInTheDocument();
    expect(within(card).getByText("Ask for a new invite link.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(toastSuccess).not.toHaveBeenCalled();
    expect(toastError).not.toHaveBeenCalled();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("email_mismatch keeps the code and switches Google accounts (local sign-out, account chooser)", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    installFakeApi({
      "POST /invites/preview": rejected("email_mismatch", "This invite was issued for a different email address."),
    });
    const { user } = renderJoin();

    const card = await screen.findByRole("alert");
    expect(
      within(card).getByRole("heading", { name: "This invite was issued for a different email address." }),
    ).toBeInTheDocument();
    expect(within(card).getByText(`You're signed in as ${EMAIL}.`)).toBeInTheDocument();
    expect(within(card).queryByText("Ask for a new invite link.")).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);

    await user.click(within(card).getByRole("button", { name: "Use a different Google account" }));

    await waitFor(() => expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" }));
    await waitFor(() => expectAccountChooserLogin());
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
  });

  it("a preview network error shows an inline Retry, keeps the code, and Retry sends it again", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    const api = installFakeApi({
      "POST /invites/preview": () => {
        throw new TypeError("Failed to fetch");
      },
    });
    const { user } = renderJoin();

    expect(await screen.findByText("Can't reach the server.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
    expect(toastError).not.toHaveBeenCalled();

    api.set("POST /invites/preview", MEMBER_PREVIEW);
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("heading", { name: "Grace" })).toBeInTheDocument();
    expect(sent(api, "/invites/preview")).toEqual([{ code: CODE }, { code: CODE }]);
  });

  it("an accept network error or 5xx toasts and stays on the preview", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    const api = installFakeApi({
      "POST /invites/preview": MEMBER_PREVIEW,
      "POST /invites/accept": () => {
        throw new TypeError("Failed to fetch");
      },
    });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Join Grace" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledWith(NETWORK_MESSAGE));
    expect(screen.getByRole("button", { name: "Join Grace" })).toBeEnabled();

    api.set("POST /invites/accept", fakeError(500, "internal_error", "Something went wrong."));
    await user.click(screen.getByRole("button", { name: "Join Grace" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledWith("Something went wrong. (Ref: 4f9a2c1e)"));

    expect(screen.getByRole("button", { name: "Join Grace" })).toBeEnabled();
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
    expect(toastSuccess).not.toHaveBeenCalled();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("Not now clears the pending code and goes home without accepting", async () => {
    window.sessionStorage.setItem(SESSION_KEYS.pendingInviteCode, CODE);
    const api = installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Not now" }));

    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(sent(api, "/invites/accept")).toEqual([]);
  });

  it("the footer's Use a different account signs out locally and keeps the code for the next sign-in", async () => {
    installFakeApi({ "POST /invites/preview": MEMBER_PREVIEW });
    const { user } = renderJoin();

    await user.click(await screen.findByRole("button", { name: "Use a different account" }));

    await waitFor(() => expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" }));
    await waitFor(() => expectAccountChooserLogin());
    expect(window.sessionStorage.getItem(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
  });
});
```

- [ ] **Step 3 (agent): Run the test to verify it fails**

```bash
(cd frontend && npx vitest run src/components/onboarding/join-invite.test.tsx 2>&1 | grep -E "Error:|Test Files|Tests ")
```

**Expected:** FAIL because the component does not exist:
```
Error: Failed to resolve import "./join-invite" from "src/components/onboarding/join-invite.test.tsx". Does the file exist?
 Test Files  1 failed (1)
      Tests  no tests
```

- [ ] **Step 4 (agent): Write the component**

Create `frontend/src/components/onboarding/join-invite.tsx`:

```tsx
"use client";

/**
 * Join a church with an invite code: preview first, then an explicit Join tap
 * (S Flow A Join tab, Flow B steps 4-6, Pages; owner decision 1, amendment to
 * decision 6). `/welcome`'s Join tab shows the entry field (`showEntry`); `/join`
 * does not, and passes the captured code with `autoPreview`.
 *
 * States: `enter` (the field only) → `previewing` (skeleton card) → `preview`
 * (church, role, expiry, or "already a member") → `joining` → `done` (navigating);
 * `rejected` (any 4xx other than 401 from preview or accept: the server's message)
 * and `error` (preview could not reach the server: inline ErrorState + Retry).
 * Rejection text lives only in this component's state, never in storage.
 *
 * The pending code (`wsb:pendingInviteCode`) is cleared after a join, after a
 * rejection other than `email_mismatch`, and by "Not now". Switching accounts
 * keeps it, and first stores the code in use, so a code typed on `/welcome`
 * also survives the new sign-in (`/login?next=/join` reads it back).
 *
 * A 401 or a sign-out in progress (`aborted`) changes nothing here: the
 * mutation cache's `handleAuthErrors` asks the page to sign out.
 */
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useId, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, errorToastMessage, type InviteRejectReason } from "@/lib/api/errors";
import type { InvitePreview } from "@/lib/api/types";
import { useSignOut } from "@/lib/auth";
import { useMembershipChanged } from "@/lib/queries/membership";
import { useAcceptInvite, usePreviewInvite } from "@/lib/queries/onboarding";
import { removeSession, SESSION_KEYS, writeSession } from "@/lib/storage";
import { extractInviteCode } from "@/lib/urls";

/** The server's 422 text for a blank code (S Flow A step 3), checked on the client first. */
export const BLANK_CODE_MESSAGE = "Enter an invite code, or open your invite link again.";

const REJECT_REASONS: readonly InviteRejectReason[] = [
  "unknown",
  "revoked",
  "expired",
  "used",
  "church_unavailable",
  "email_mismatch",
];

type State =
  | { kind: "enter" }
  | { kind: "previewing"; code: string }
  | { kind: "preview"; code: string; preview: InvitePreview }
  | { kind: "joining"; code: string; preview: InvitePreview }
  | { kind: "done"; code: string; preview: InvitePreview }
  | { kind: "rejected"; code: string; reason: InviteRejectReason; message: string }
  | { kind: "error"; code: string; error: unknown };

export type JoinInviteProps = {
  /** The pending code (`/welcome`) or the captured one (`/join`); a pasted link works too. */
  initialCode?: string;
  /** Preview `initialCode` once on mount (never retried automatically; clarification 29). */
  autoPreview?: boolean;
  /** The signed-in user's email, for the email-bound, mismatch and footer lines. */
  email: string;
  /** Show the "Invite link or code" field and Continue (`/welcome` only). */
  showEntry: boolean;
};

/** Sign-out is already under way: a 401 (handleAuthErrors signs out) or a request cancelled by it. */
function isSignOutError(e: unknown): boolean {
  return e instanceof ApiError && (e.status === 401 || e.code === "aborted");
}

/** A 4xx the user cannot fix by retrying: the invite (or the code) is not usable. */
function isRejection(e: unknown): e is ApiError {
  return e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 401;
}

function rejectReason(e: ApiError): InviteRejectReason {
  const reason = e.details?.reason;
  return e.code === "invite_rejected" && REJECT_REASONS.includes(reason as InviteRejectReason)
    ? (reason as InviteRejectReason)
    : "unknown";
}

/** "October 5, 2026" in the browser's time zone (S Flow B step 4). */
function formatExpiry(iso: string): string {
  return new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric", year: "numeric" }).format(new Date(iso));
}

export function JoinInvite({ initialCode = "", autoPreview = false, email, showEntry }: JoinInviteProps) {
  const router = useRouter();
  const signOut = useSignOut();
  const membershipChanged = useMembershipChanged();
  const { mutateAsync: previewInvite } = usePreviewInvite();
  const { mutateAsync: acceptInvite } = useAcceptInvite();

  const [field, setField] = useState(initialCode);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [state, setState] = useState<State>(() => {
    const code = autoPreview ? extractInviteCode(initialCode) : "";
    return code ? { kind: "previewing", code } : { kind: "enter" };
  });
  const autoCode = useRef(state.kind === "previewing" ? state.code : null);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();
  const helpId = useId();
  const errorId = useId();

  const reject = useCallback((code: string, e: ApiError) => {
    const reason = rejectReason(e);
    if (reason !== "email_mismatch") removeSession(SESSION_KEYS.pendingInviteCode);
    setState({ kind: "rejected", code, reason, message: e.fields?.code ?? e.message });
  }, []);

  /** Sends the preview; the caller has already shown the `previewing` skeleton. */
  const loadPreview = useCallback(
    async (code: string) => {
      try {
        const preview = await previewInvite(code);
        setState({ kind: "preview", code, preview });
      } catch (e) {
        if (isSignOutError(e)) return;
        if (isRejection(e)) reject(code, e);
        else setState({ kind: "error", code, error: e });
      }
    },
    [previewInvite, reject],
  );

  // `autoPreview`: once per mount, even under StrictMode's double effects, and never
  // retried automatically (clarification 29). The ref is emptied by the first run.
  useEffect(() => {
    const code = autoCode.current;
    if (code === null) return;
    autoCode.current = null;
    void loadPreview(code);
  }, [loadPreview]);

  function startPreview(code: string) {
    setState({ kind: "previewing", code });
    void loadPreview(code);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const code = extractInviteCode(field);
    if (!code) {
      setFieldError(BLANK_CODE_MESSAGE);
      inputRef.current?.focus();
      return;
    }
    setFieldError(null);
    startPreview(code);
  }

  async function join(code: string, preview: InvitePreview) {
    setState({ kind: "joining", code, preview });
    try {
      const accepted = await acceptInvite(code);
      setState({ kind: "done", code, preview });
      removeSession(SESSION_KEYS.pendingInviteCode);
      await membershipChanged({ selectChurchId: accepted.church.id });
      toast.success(accepted.message);
    } catch (e) {
      if (isSignOutError(e)) return;
      if (isRejection(e)) {
        reject(code, e);
        return;
      }
      toast.error(errorToastMessage(e));
      setState({ kind: "preview", code, preview });
    }
  }

  function notNow() {
    removeSession(SESSION_KEYS.pendingInviteCode);
    router.replace("/");
  }

  async function switchAccount(code: string) {
    writeSession(SESSION_KEYS.pendingInviteCode, code);
    await signOut({ keepPendingInvite: true, next: "/join", selectAccount: true });
  }

  const busy = state.kind === "previewing" || state.kind === "joining" || state.kind === "done";

  return (
    <div className="flex flex-col gap-6">
      {showEntry && (
        <form noValidate onSubmit={submit} className="flex flex-col gap-2">
          <Label htmlFor={inputId}>Invite link or code</Label>
          <Input
            ref={inputRef}
            id={inputId}
            value={field}
            onChange={(event) => setField(event.target.value)}
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            aria-invalid={fieldError ? true : undefined}
            aria-describedby={fieldError ? `${helpId} ${errorId}` : helpId}
            className="h-11 text-base md:text-sm"
          />
          <p id={helpId} className="text-sm text-muted-foreground">
            Paste the link or code from your invite.
          </p>
          {fieldError && (
            <p id={errorId} className="text-sm text-destructive">
              {fieldError}
            </p>
          )}
          <Button type="submit" size="touch" className="w-full" disabled={busy}>
            Continue
          </Button>
        </form>
      )}

      {state.kind === "previewing" && (
        <Card role="status" aria-label="Loading invite">
          <CardHeader>
            <Skeleton className="h-5 w-2/3" />
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-11 w-full" />
          </CardContent>
        </Card>
      )}

      {(state.kind === "preview" || state.kind === "joining" || state.kind === "done") && (
        <Card>
          <CardHeader>
            <CardTitle>
              <h2>{state.preview.church_name}</h2>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {state.preview.already_member ? (
              <p>You&apos;re already a member of {state.preview.church_name}.</p>
            ) : (
              <div className="flex flex-col gap-1">
                <p>You&apos;re invited to join as {state.preview.role === "admin" ? "an admin" : "a member"}.</p>
                {state.preview.email_bound && <p>This invite is for {email}.</p>}
                <p className="text-muted-foreground">Invite expires {formatExpiry(state.preview.expires_at)}.</p>
              </div>
            )}
            <div className="flex flex-col gap-2">
              <PendingButton
                size="touch"
                className="w-full"
                pending={state.kind !== "preview"}
                pendingLabel="Joining…"
                onClick={() => void join(state.code, state.preview)}
              >
                {state.preview.already_member ? `Open ${state.preview.church_name}` : `Join ${state.preview.church_name}`}
              </PendingButton>
              <Button variant="outline" size="touch" className="w-full" disabled={busy} onClick={notNow}>
                Not now
              </Button>
            </div>
          </CardContent>
          <CardFooter className="flex-wrap gap-1 text-sm text-muted-foreground">
            <span>Signed in as {email} ·</span>
            <Button
              variant="link"
              className="h-auto p-0"
              disabled={busy}
              onClick={() => void switchAccount(state.code)}
            >
              Use a different account
            </Button>
          </CardFooter>
        </Card>
      )}

      {state.kind === "rejected" && (
        <Card role="alert">
          <CardHeader>
            <CardTitle>
              <h2>{state.message}</h2>
            </CardTitle>
            <CardDescription>
              {state.reason === "email_mismatch" ? `You're signed in as ${email}.` : "Ask for a new invite link."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {state.reason === "email_mismatch" ? (
              <Button size="touch" className="w-full" onClick={() => void switchAccount(state.code)}>
                Use a different Google account
              </Button>
            ) : (
              <Button variant="outline" size="touch" className="w-full" onClick={() => router.replace("/")}>
                Go to home
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {state.kind === "error" && <ErrorState error={state.error} onRetry={() => startPreview(state.code)} />}
    </div>
  );
}
```

- [ ] **Step 5 (agent): Run the test to verify it passes**

```bash
(cd frontend && npx vitest run src/components/onboarding/join-invite.test.tsx 2>&1 | grep -E "✓|×|Test Files|Tests ")
```

**Expected:** `✓ |dom| src/components/onboarding/join-invite.test.tsx (21 tests)`, then `Test Files  1 passed (1)` and `Tests  21 passed (21)`. If a toast test fails with an `ApiError` code in the diff, check Task 9's `errorToastMessage` first. If a sign-out test shows `/login?next=%2Fjoin` without `select_account`, check Task 10's `useSignOut` first.

- [ ] **Step 6 (agent): Prove the StrictMode test catches a missing guard, then restore**

```bash
sed -i.bak 's/^    autoCode.current = null;$/    \/\/ guard removed for this check/' frontend/src/components/onboarding/join-invite.tsx
(cd frontend && npx vitest run src/components/onboarding/join-invite.test.tsx -t "StrictMode" 2>&1 | grep -E "AssertionError|Tests ")
mv frontend/src/components/onboarding/join-invite.tsx.bak frontend/src/components/onboarding/join-invite.tsx
grep -c "^    autoCode.current = null;$" frontend/src/components/onboarding/join-invite.tsx
ls frontend/src/components/onboarding
(cd frontend && npx vitest run src/components/onboarding/join-invite.test.tsx 2>&1 | grep -E "Tests ")
```

**Expected:** with the guard removed, the StrictMode test fails because StrictMode's second effect sent a second preview:
```
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
AssertionError: expected [ { code: 'PENDING' }, …(1) ] to deeply equal [ { code: 'PENDING' } ]
      Tests  1 failed | 20 skipped (21)
```
After the restore: `1`; `join-invite.test.tsx` and `join-invite.tsx` (no `.bak` left); `Tests  21 passed (21)`. If the StrictMode test passes with the guard removed, the test is not rendering StrictMode at the root: it must use `render(…, { reactStrictMode: true })`, not a nested `<StrictMode>`.

- [ ] **Step 7 (agent): Delete the ported Streamlit tests (port-then-delete, F §2.3.7; clarification 48)**

```bash
git rm -q streamlit_tests/test_onboarding.py
grep -rnI "pick_invite_code" streamlit_tests backend | wc -l
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `0` (`ui_helpers.pick_invite_code` itself stays: `app.py` still calls it, and `app.py`/`ui_helpers.py` are untouched in 1b), then `796 passed, 9 skipped in <t>s` (799 − 3).

- [ ] **Step 8 (agent): Run the whole frontend suite, typecheck and lint**

```bash
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
git status --short
```

**Expected:** `Test Files  32 passed (32)` and `Tests  192 passed (192)` (171 + 21). `tsc --noEmit` and `eslint` print no errors (the react-hooks 7 rules pass: no synchronous `setState` in the effect, and the ref is read only in the effect and handlers). `git status --short` lists exactly these, plus `?? .claude/`:
```
D  streamlit_tests/test_onboarding.py
?? frontend/src/components/onboarding/
```

- [ ] **Step 9 (agent): Commit**

```bash
git add frontend/src/components/onboarding/join-invite.tsx frontend/src/components/onboarding/join-invite.test.tsx
git status --short
git commit -m "Onboarding: JoinInvite previews an invite, then joins on a tap; pick_invite_code tests ported (S Flow B 4-6, AC16; owner decision 1; 1b clarifications 18, 29, 35, 48)

JoinInvite is the Join tab on /welcome (with the Invite link or code
field) and the body of /join (captured code, autoPreview). It previews
once per mount, even under StrictMode, and shows a skeleton card while
it loads. The card shows the church, the role the invite grants, the
email line for a bound invite and the expiry, or the single already-a-
member line. Join or Open accepts the previewed code, clears the pending
code, selects the church through useMembershipChanged and toasts the
server message. A rejection shows the server message with Ask for a new
invite link and Go to home, and clears the code. email_mismatch keeps
the code and offers Use a different Google account (local sign-out to
/login?next=/join&select_account=1). A preview network error is an inline
Retry. An accept network error or 5xx is a toast, and the card stays.

The three pick_invite_code tests in streamlit_tests/test_onboarding.py
are ported as JoinInvite tests (typed wins; untouched pending code used;
blank or whitespace sends nothing), and the file is deleted. Tasks 3 and
5 already removed its create and accept tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** before the commit, `git status --short` lists `A  frontend/src/components/onboarding/join-invite.test.tsx`, `A  frontend/src/components/onboarding/join-invite.tsx` and `D  streamlit_tests/test_onboarding.py`, plus `?? .claude/`. After it, `git log` prints `<sha> Onboarding: JoinInvite previews an invite, then joins on a tap; pick_invite_code tests ported (S Flow B 4-6, AC16; owner decision 1; 1b clarifications 18, 29, 35, 48)`, and `git status --short` lists only `?? .claude/`.
### Task 15: `/join` page (S Flow B steps 1–3 and 7; Pages; AC9, AC10; F-AC9; clarifications 19, 20, 27, 28, 45, 47)

This task builds the public invite page. `/join?code=…` stores the code in sessionStorage, takes it out of the address bar with the native `history.replaceState` (Next 16 supports it: `04-linking-and-navigating.md:345-347`, `:399-415`; S Risk 9 closed, clarification 27), clears the stored post-login path, and then shows one of four things: a neutral skeleton, the "You're invited" sign-in card, the incomplete-link card, or Task 14's `JoinInvite` (preview, then a Join tap: owner decision 1).

Design points (each one is pinned by a test below):
- **`page.tsx` is a Server Component.** Next 16 allows `metadata` only there. It renders `JoinClient` in `<Suspense>`, because `useSearchParams` in a static route fails `next build` without one (`use-search-params.md:180-181`; clarification 28). The metadata adds `referrer: "no-referrer"` (clarification 45). Until the mount effect runs `replaceState`, the URL holds the code, and no request may send it as a Referer. The build prerenders `/join` as static. The HTML holds the skeleton fallback and the three head tags checked in Step 7.
- **The code is read once.** After `replaceState`, Next's router reports `useSearchParams().get("code") === null`. So the mount effect captures the code once (a ref guards against StrictMode's second run) and keeps it in state. "No code" is never worked out from the updated URL again (clarification 27). The effect has **no** cleanup flag. StrictMode's second run returns early, so the first run's result must land.
- **Signed in or not comes from `getAccessToken()`** (clarification 20), not `supabase.auth.getSession()` directly. A token means signed in. `ApiError` 401 shows the sign-in card. A token refresh that could not reach Supabase (`network_error`, be61d10) shows `ErrorState` with Retry, never the sign-in card. `aborted` (a sign-out is under way) keeps the skeleton until `/login`.
- **`useMe({ enabled: view.kind === "signed-in" && !signingOut })`** (clarification 47). If `/me` were enabled from mount, a signed-out visitor would get a 401. The page's own subscriber would then send them to `/login`, skipping the "You're invited" card. A `/me` 5xx shows `ErrorState` with Retry.
- **The page answers 401s itself** (clarification 19). `/join` sits outside the `(signed-in)` layout, which is the only other `authEvents.onSignOutRequired` subscriber. A 401 from `/me`, preview or accept therefore calls `signOut({ keepPendingInvite: true, next: "/join" })` here. That is a local sign-out that keeps the code and lands on `/login?next=%2Fjoin`.
- **Links.** "Sign in with Google" is `<Button render={<Link href="/login?next=%2Fjoin" />} nativeButton={false}>`, the F §4.9 form. Base UI gives that `<a>` the `button` role, so the test finds it by role `button`, checks it is an `<a>`, and compares the **parsed** href (clarification 17: `next` is encoded). A plain `<a href="/">` fails lint (`@next/next/no-html-link-for-pages`). So "Go to home" on the incomplete card is a Button with `router.replace("/")`, the same as Task 14's "Go to home" and "Not now".
- **Not here:** the footer "Signed in as {email} · Use a different account", the rejection cards and "Not now". All of these live in `JoinInvite` (Task 14), which this page renders with `showEntry={false}`.
- **Test hygiene** (this file only; `setup-dom.ts` keeps its single global `afterEach`). The capture calls jsdom's real `replaceState`, which changes `window.location`. So a spy is set up in `beforeEach`, and `afterEach` restores it and resets the URL to `/`. Sonner replays still-active toasts to a newly mounted `<Toaster />`, so `beforeEach` runs `toast.dismiss()`. The tests render a `<Toaster />` and assert the toast **text**. They do not depend on whether Task 14 calls `toast.success` or `toast`.

**Files:**
- Create: `frontend/src/app/join/page.tsx`
- Create: `frontend/src/app/join/join-client.tsx`
- Test: `frontend/src/app/join/join.test.tsx` (create)

**Interfaces:**
- Consumes:
  - `readSession(key): string | null`, `writeSession(key, value): void`, `removeSession(key): void`, `SESSION_KEYS.pendingInviteCode = "wsb:pendingInviteCode"`, `SESSION_KEYS.postLoginPath = "wsb:postLoginPath"` (`frontend/src/lib/storage.ts:8-11`, `:46-56`).
  - Task 9: `clearPostLoginPath(): void` (`frontend/src/lib/post-login.ts`).
  - `getAccessToken(): Promise<string>`, which rejects with `ApiError(401, "unauthenticated")` when there is no session, `ApiError(0, "network_error", NETWORK_MESSAGE)` on an `AuthRetryableFetchError`, and `ApiError(0, "aborted")` while signing out. Also `isSigningOut(): boolean`, `useSigningOut(): boolean`, and `useSignOut(): (opts?: SignOutOptions) => Promise<void>` with `{ keepPendingInvite?, next?, selectAccount? }` (Task 10 added `selectAccount`). All are in `frontend/src/lib/auth.ts`.
  - `useMe(opts: { enabled?: boolean }): UseQueryResult<Me, ApiError>` (`frontend/src/lib/queries/me.ts`; Task 13 keeps the signature). `authEvents.onSignOutRequired(listener): () => void` (`frontend/src/lib/queries/auth-events.ts`). `ApiError` (`frontend/src/lib/api/client.ts`).
  - `ErrorState({ error, onRetry })` (`frontend/src/components/app/error-state.tsx`; Task 11's optional `retrying` is not used here). `describeError` gives "Can't reach the server." and "Something went wrong. (Ref: …)".
  - Task 14: `JoinInvite({ initialCode?: string; autoPreview?: boolean; email: string; showEntry: boolean })` (`frontend/src/components/onboarding/join-invite.tsx`): the button "Join {church_name}", a success toast with the server `message` after `useMembershipChanged`, and the footer.
  - Generated `Button` (`render`, `nativeButton`, `size="touch"`), `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `Skeleton`; `Link` from `next/link`; `useRouter`, `useSearchParams` from `next/navigation`.
  - Tests: `installFakeApi`, `fakeError` (`test/fake-api.ts`); `me`, `church`, `CHURCH_IDS` and Task 13's `invitePreview(o)`, `inviteAccepted(o)` (`test/fixtures/index.ts`); `setTestPath`, `supabaseAuth`, `testRouter` (`test/mocks.ts`); `renderWithProviders` (`test/render.tsx`); `makeQueryClient` (`lib/queries/client.ts:69`) and RTL `render(ui, { reactStrictMode: true })` for the root-StrictMode capture test; `Toaster` (`components/ui/sonner.tsx`); `readStoredChurchId`, `storeChurchId` (`lib/church.ts`).
- Produces:
  - `frontend/src/app/join/page.tsx`: `export const metadata: Metadata = { title: "Join a church", robots: { index: false, follow: false }, referrer: "no-referrer" }`; `export default function JoinPage()` → `<Suspense fallback={<JoinSkeleton />}><JoinClient /></Suspense>`.
  - `frontend/src/app/join/join-client.tsx` (`"use client"`): `export function JoinClient()`; `export function JoinSkeleton()` (`role="status"`, `aria-label="Loading"`). Copy, verbatim: "You're invited" / "Sign in with Google to see and accept your invite to Worship Service Builder." / "Sign in with Google" (→ `/login?next=%2Fjoin`); "This invite link is incomplete." / "Open the link from your invite again, or ask for a new one." / "Go to home" (→ `router.replace("/")`). Later users: none in code; Task 21 runs manual checks 2 and 3 against it.

Counts after this task: backend **796 passed, 9 skipped** (unchanged since Task 14); frontend **204 passed in 33 files** (Task 14's 192 in 32, plus 12 in one new file). The outline's "203 / 33" is the count without Q4.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
ls frontend/src/app/join 2>&1 | grep -c "No such file"
grep -c "export function JoinInvite\|export function clearPostLoginPath\|export function invitePreview\|export function inviteAccepted\|selectAccount?: boolean" frontend/src/components/onboarding/join-invite.tsx frontend/src/lib/post-login.ts frontend/src/test/fixtures/index.ts frontend/src/lib/auth.ts
```

**Expected:** `git status --short` lists only `?? .claude/`, and the last commit is Task 14's. The suite prints `Test Files  32 passed (32)` and `Tests  192 passed (192)`. Next comes `1` (no `app/join` yet). The four per-file counts are `join-invite.tsx:1`, `post-login.ts:1`, `index.ts:2` and `auth.ts:1`. If the frontend counts differ, stop and ask.

- [ ] **Step 2 (agent): Write the failing test (`frontend/src/app/join/join.test.tsx`)**

```tsx
import { AuthRetryableFetchError } from "@supabase/supabase-js";
import { QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import { readStoredChurchId, storeChurchId } from "@/lib/church";
import { makeQueryClient } from "@/lib/queries/client";
import { readSession, SESSION_KEYS, writeSession } from "@/lib/storage";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, inviteAccepted, invitePreview, me } from "@/test/fixtures";
import { setTestPath, supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import JoinPage, { metadata } from "./page";

const CODE = "Xy7-invite-CODE";

// This file's own hygiene (setup-dom.ts keeps the one global afterEach): the capture
// calls jsdom's real `replaceState`, which changes `window.location` for later tests,
// and sonner replays still-active toasts to a newly mounted Toaster.
let replaceState: MockInstance<History["replaceState"]>;

beforeEach(() => {
  toast.dismiss();
  replaceState = vi.spyOn(window.history, "replaceState");
});

afterEach(() => {
  replaceState.mockRestore();
  window.history.replaceState(null, "", "/");
});

/** `/join` as the app renders it (the page's Suspense included), with a Toaster for toast text. */
function joinTree() {
  return (
    <>
      <JoinPage />
      <Toaster />
    </>
  );
}

/** Arrive at `path`: the address bar and the router both show it; the spy starts clean. */
function openJoin(path: string) {
  window.history.replaceState(null, "", path);
  replaceState.mockClear();
  return renderWithProviders(joinTree(), { path });
}

function signedOut(): void {
  supabaseAuth.getSession.mockResolvedValue({ data: { session: null }, error: null });
}

/**
 * The parsed href of a link-styled Button. Base UI gives `<Button render={<Link />}
 * nativeButton={false}>` the `button` role, so it is found by that role and checked to be an `<a>`.
 */
function hrefOf(name: string): URL {
  const link = screen.getByRole("button", { name });
  expect(link.tagName).toBe("A");
  return new URL(link.getAttribute("href") ?? "", "http://localhost");
}

describe("/join (slice 1b)", () => {
  it("signed out: stores the code, takes it out of the address bar and shows the sign-in card", async () => {
    signedOut();
    installFakeApi({});
    openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("You're invited")).toBeInTheDocument();
    expect(
      screen.getByText("Sign in with Google to see and accept your invite to Worship Service Builder."),
    ).toBeInTheDocument();
    const signIn = hrefOf("Sign in with Google");
    expect(signIn.pathname).toBe("/login");
    expect([...signIn.searchParams]).toEqual([["next", "/join"]]);

    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
    expect(replaceState).toHaveBeenCalledTimes(1);
    expect(replaceState).toHaveBeenCalledWith(null, "", "/join");
    expect(window.location.pathname + window.location.search).toBe("/join");

    expect(metadata).toEqual({
      title: "Join a church",
      robots: { index: false, follow: false },
      referrer: "no-referrer",
    });
  });

  it("clears the stored post-login path on mount", async () => {
    signedOut();
    installFakeApi({});
    writeSession(SESSION_KEYS.postLoginPath, JSON.stringify({ path: "/join", at: Date.now() }));
    openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("You're invited")).toBeInTheDocument();
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
  });

  it("keeps the captured code when the router's URL loses ?code= after replaceState", async () => {
    signedOut();
    installFakeApi({});
    window.history.replaceState(null, "", `/join?code=${CODE}`);
    replaceState.mockClear();
    setTestPath(`/join?code=${CODE}`);
    // StrictMode at the root (as in Task 14): the capture effect runs twice, and the ref
    // keeps it to one replaceState without losing the first run's code.
    const queryClient = makeQueryClient({ queries: { retry: false } });
    const { rerender } = render(<QueryClientProvider client={queryClient}>{joinTree()}</QueryClientProvider>, {
      reactStrictMode: true,
    });
    expect(await screen.findByText("You're invited")).toBeInTheDocument();

    // What Next's router reports once the native replaceState has run.
    setTestPath("/join");
    rerender(<QueryClientProvider client={queryClient}>{joinTree()}</QueryClientProvider>);

    expect(screen.getByText("You're invited")).toBeInTheDocument();
    expect(screen.queryByText("This invite link is incomplete.")).not.toBeInTheDocument();
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
    expect(replaceState).toHaveBeenCalledTimes(1);
  });

  it("signed in: previews the invite; Join accepts it, selects the church and toasts", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview({ church_name: "Grace", role: "member" }),
      "POST /invites/accept": inviteAccepted({
        church: church({ role: "member" }),
        already_member: false,
        message: "Joined Grace.",
      }),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    const join = await screen.findByRole("button", { name: "Join Grace" });
    api.set("GET /me", me({ churches: [church({ role: "member" })] }));
    await user.click(join);

    expect(await screen.findByText("Joined Grace.")).toBeInTheDocument();
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    expect(readStoredChurchId()).toBe(CHURCH_IDS.grace);
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(
      api.requests.filter((r) => r.method === "POST").map((r) => [r.path, r.body]),
    ).toEqual([
      ["/invites/preview", { code: CODE }],
      ["/invites/accept", { code: CODE }],
    ]);
  });

  it("previews a code stored before sign-in when the URL has none", async () => {
    writeSession(SESSION_KEYS.pendingInviteCode, CODE);
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview({ church_name: "Grace" }),
    });
    openJoin("/join");

    expect(await screen.findByRole("button", { name: "Join Grace" })).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/invites/preview").map((r) => r.body)).toEqual([
      { code: CODE },
    ]);
    expect(replaceState).not.toHaveBeenCalled();
  });

  it("shows the incomplete-link card when there is no code in the URL or in storage", async () => {
    const api = installFakeApi({});
    const { user } = openJoin("/join");

    expect(await screen.findByText("This invite link is incomplete.")).toBeInTheDocument();
    expect(
      screen.getByText("Open the link from your invite again, or ask for a new one."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Go to home" }));
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(api.requests).toEqual([]);
  });

  it("a 401 from the preview signs out locally, keeps the code and returns to /join after sign-in", async () => {
    installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": fakeError(401, "unauthenticated", "Please sign in."),
    });
    openJoin(`/join?code=${CODE}`);

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login?next=%2Fjoin"));
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
  });

  it("a session check that cannot reach Supabase shows ErrorState, not the sign-in card; Retry checks again", async () => {
    supabaseAuth.getSession.mockResolvedValueOnce({
      data: { session: null },
      error: new AuthRetryableFetchError("Failed to fetch", 0),
    });
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview({ church_name: "Grace" }),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("Can't reach the server.")).toBeInTheDocument();
    expect(screen.queryByText("You're invited")).not.toBeInTheDocument();
    expect(api.requests).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("button", { name: "Join Grace" })).toBeInTheDocument();
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe(CODE);
  });

  it("signed out: loads no /me, so nothing signs out and the invited card stays", async () => {
    signedOut();
    const api = installFakeApi({});
    openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("You're invited")).toBeInTheDocument();
    // Let any query that would start on mount run to its end.
    await act(() => new Promise((resolve) => setTimeout(resolve, 0)));

    expect(supabaseAuth.getSession).toHaveBeenCalledTimes(1);
    expect(api.requests).toEqual([]);
    expect(supabaseAuth.signOut).not.toHaveBeenCalled();
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(screen.getByText("You're invited")).toBeInTheDocument();
  });

  it("a /me 5xx shows ErrorState with Retry, and Retry goes on to the preview", async () => {
    const api = installFakeApi({
      "GET /me": fakeError(500, "internal_error", "Something went wrong."),
      "POST /invites/preview": invitePreview({ church_name: "Grace" }),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/invites/preview")).toHaveLength(0);

    api.set("GET /me", me({ churches: [] }));
    await user.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("button", { name: "Join Grace" })).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(2);
  });

  it("a member of Grace who joins Hope ends with Hope selected", async () => {
    storeChurchId(CHURCH_IDS.grace);
    const hope = church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" });
    const api = installFakeApi({
      "GET /me": me(),
      "POST /invites/preview": invitePreview({ church_name: "Hope" }),
      "POST /invites/accept": inviteAccepted({ church: hope, message: "Joined Hope." }),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    const join = await screen.findByRole("button", { name: "Join Hope" });
    api.set("GET /me", me({ churches: [church(), hope] }));
    await user.click(join);

    expect(await screen.findByText("Joined Hope.")).toBeInTheDocument();
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    expect(readStoredChurchId()).toBe(CHURCH_IDS.hope);
  });

  it("the code travels only in POST bodies: never in a request path, query or header, nor the address bar", async () => {
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview({ church_name: "Grace" }),
      "POST /invites/accept": inviteAccepted(),
    });
    const { user } = openJoin(`/join?code=${CODE}`);

    const join = await screen.findByRole("button", { name: "Join Grace" });
    api.set("GET /me", me({ churches: [church({ role: "member" })] }));
    await user.click(join);
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));

    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual([
      "GET /me",
      "POST /invites/preview",
      "POST /invites/accept",
      "GET /me",
    ]);
    for (const request of api.requests) {
      expect(decodeURIComponent(request.path)).not.toContain(CODE);
      expect(JSON.stringify({ ...request.headers })).not.toContain(CODE);
    }
    expect(api.requests.filter((r) => r.body !== undefined).map((r) => r.body)).toEqual([
      { code: CODE },
      { code: CODE },
    ]);
    expect(window.location.href).not.toContain(CODE);
  });
});
```

The twelve tests map to the outline's list as follows:
1. Signed out: the card copy, the code in sessionStorage, `replaceState(null, "", "/join")` called exactly once, the parsed sign-in href, and the `metadata` export.
2. Post-login path cleared.
3. Re-render with `setTestPath("/join")` keeps the code (clarification 27).
4. Signed in: preview, then Join, then toast and church selected (AC10 first half).
5. A stored code with no URL code previews.
6. The incomplete card.
7. A preview 401 goes through this page's own subscriber (clarification 19).
8. A `getAccessToken` network error shows `ErrorState` and Retry (clarification 20).
9. Signed out: no `/me`, no sign-out, no redirect. `getSession` is called exactly once (clarification 47).
10. A `/me` 5xx shows `ErrorState` and Retry.
11. A Grace member joins Hope, and Hope is stored (AC10 second half, Flow B step 8).
12. AC9: every request path, query and header is free of the code. The code appears only in the two POST bodies, and the address bar no longer holds it.

- [ ] **Step 3 (agent): Run the test to verify it fails**

```bash
(cd frontend && npx vitest run src/app/join/join.test.tsx 2>&1 | grep -E "Error:|Test Files|Tests ")
```

**Expected:** `Error: Failed to resolve import "./page" from "src/app/join/join.test.tsx". Does the file exist?`, `Test Files  1 failed (1)`, `Tests  no tests`.

- [ ] **Step 4 (agent): Create the server page (`frontend/src/app/join/page.tsx`)**

```tsx
/**
 * `/join?code=…` (S Flow B, "Pages (1b)"; F §4.3): the public invite page.
 *
 * A Server Component, so it can export `metadata` (Next 16 allows it only in
 * Server Components). The client part reads `useSearchParams`, so it sits in
 * `<Suspense>`: without it `next build` fails for this static route.
 *
 * `referrer: "no-referrer"` (1b clarification 45): until the mount effect runs
 * `replaceState`, the address bar still holds the code, and no request this page
 * makes may carry it as a Referer.
 */
import type { Metadata } from "next";
import { Suspense } from "react";

import { JoinClient, JoinSkeleton } from "./join-client";

export const metadata: Metadata = {
  title: "Join a church",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function JoinPage() {
  return (
    <Suspense fallback={<JoinSkeleton />}>
      <JoinClient />
    </Suspense>
  );
}
```

- [ ] **Step 5 (agent): Create the client part (`frontend/src/app/join/join-client.tsx`)**

```tsx
"use client";

/**
 * The client part of `/join` (S Flow B steps 1-3 and 7; F §4.3). `page.tsx`
 * renders it in `<Suspense>`.
 *
 * - Mount effect, once (a ref, since StrictMode runs effects twice): a `?code=`
 *   goes to `sessionStorage["wsb:pendingInviteCode"]`, and
 *   `history.replaceState(null, "", "/join")` takes it out of the address bar and
 *   history. Next 16 syncs a native `replaceState` into the router, so
 *   `useSearchParams().get("code")` is null afterwards. The code is therefore read
 *   once, here, and "no code" is never worked out from the URL again (1b
 *   clarification 27). The effect also clears the stored post-login path: `/join`
 *   sits outside the `(signed-in)` layout that would follow it.
 * - Signed in or not comes from `getAccessToken()` (clarification 20): a token
 *   means signed in; a 401 shows the "You're invited" card; anything else (a token
 *   refresh that could not reach Supabase) shows `ErrorState` with Retry, never
 *   the sign-in card. A neutral skeleton shows until this is known.
 * - `/me` (for the email) loads only once signed in (clarification 47). An
 *   enabled-from-mount `/me` would 401 for a signed-out visitor and sign them
 *   straight out to `/login`, skipping the "You're invited" card.
 * - A 401 from `/me`, preview or accept reaches `handleAuthErrors`. Its usual
 *   answer comes from the `(signed-in)` layout, which is not mounted here, so this
 *   page subscribes itself: a local sign-out that keeps the pending code and comes
 *   back to `/join` (clarification 19).
 * - Signed in with a code: `JoinInvite` previews it at once (owner decision 1:
 *   the preview card, then a Join tap).
 */
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { ErrorState } from "@/components/app/error-state";
import { JoinInvite } from "@/components/onboarding/join-invite";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { getAccessToken, isSigningOut, useSignOut, useSigningOut } from "@/lib/auth";
import { clearPostLoginPath } from "@/lib/post-login";
import { authEvents } from "@/lib/queries/auth-events";
import { useMe } from "@/lib/queries/me";
import { readSession, removeSession, SESSION_KEYS, writeSession } from "@/lib/storage";

/** Where "Sign in with Google" goes: `/login` stores `next` and Google brings the user back here. */
const SIGN_IN_HREF = `/login?next=${encodeURIComponent("/join")}`;

type View =
  | { kind: "checking" }
  | { kind: "incomplete" }
  | { kind: "signed-out" }
  | { kind: "session-error"; code: string; error: unknown }
  | { kind: "signed-in"; code: string };

/**
 * Flow B step 2: store a `?code=` and take it out of the address bar and history;
 * clear the post-login path. Returns the pending code (the URL's, else one stored
 * before sign-in), or null when there is none. A blank `?code=` removes any stored
 * code, so it shows "This invite link is incomplete." (Flow B step 7).
 */
function captureCode(fromUrl: string | null): string | null {
  if (fromUrl !== null) {
    const trimmed = fromUrl.trim();
    if (trimmed !== "") writeSession(SESSION_KEYS.pendingInviteCode, trimmed);
    // A blank ?code= (a truncated link) is incomplete; never preview an older stored code.
    else removeSession(SESSION_KEYS.pendingInviteCode);
    window.history.replaceState(null, "", "/join");
  }
  clearPostLoginPath();
  const pending = readSession(SESSION_KEYS.pendingInviteCode)?.trim();
  return pending ? pending : null;
}

/** What to show for `code`. Never rejects. */
async function resolveView(code: string | null): Promise<View> {
  if (code === null) return { kind: "incomplete" };
  try {
    await getAccessToken();
    return { kind: "signed-in", code };
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return { kind: "signed-out" };
    // A sign-out is under way (`aborted`); it ends on /login.
    if (e instanceof ApiError && e.code === "aborted") return { kind: "checking" };
    return { kind: "session-error", code, error: e };
  }
}

export function JoinClient() {
  const searchParams = useSearchParams();
  const signingOut = useSigningOut();
  const signOut = useSignOut();
  const [view, setView] = useState<View>({ kind: "checking" });
  const captured = useRef(false);
  const me = useMe({ enabled: view.kind === "signed-in" && !signingOut });

  useEffect(() => {
    if (captured.current) return;
    captured.current = true;
    // No cleanup flag: StrictMode's second run returns early, so the first run's
    // result is the only one and must land.
    void resolveView(captureCode(searchParams.get("code"))).then(setView);
  }, [searchParams]);

  useEffect(
    () =>
      authEvents.onSignOutRequired(() => {
        if (isSigningOut()) return;
        void signOut({ keepPendingInvite: true, next: "/join" });
      }),
    [signOut],
  );

  if (signingOut || view.kind === "checking") return <JoinSkeleton />;
  if (view.kind === "incomplete") return <IncompleteCard />;
  if (view.kind === "signed-out") return <SignInCard />;
  if (view.kind === "session-error") {
    const { code } = view;
    return (
      <JoinFrame>
        <ErrorState
          error={view.error}
          onRetry={() => {
            setView({ kind: "checking" });
            void resolveView(code).then(setView);
          }}
        />
      </JoinFrame>
    );
  }
  if (me.data) {
    return (
      <JoinFrame>
        <JoinInvite initialCode={view.code} autoPreview email={me.data.user.email} showEntry={false} />
      </JoinFrame>
    );
  }
  if (me.isError && !isUnauthenticated(me.error)) {
    return (
      <JoinFrame>
        <ErrorState error={me.error} onRetry={() => void me.refetch()} />
      </JoinFrame>
    );
  }
  return <JoinSkeleton />;
}

/** A 401 is already handled: `handleAuthErrors` emitted `signOutRequired`, which this page answers. */
function isUnauthenticated(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

/** The onboarding column: `max-w-md`, 16 px gutters, centred. */
function JoinFrame({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center p-4">
      {children}
    </main>
  );
}

/** Neutral: shown before the page knows whether anyone is signed in. */
export function JoinSkeleton() {
  return (
    <JoinFrame>
      <div role="status" aria-label="Loading" className="grid gap-3 rounded-xl border p-4">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    </JoinFrame>
  );
}

/** Flow B step 3. */
function SignInCard() {
  return (
    <JoinFrame>
      <Card>
        <CardHeader>
          <CardTitle>{"You're invited"}</CardTitle>
          <CardDescription>
            Sign in with Google to see and accept your invite to Worship Service Builder.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button render={<Link href={SIGN_IN_HREF} />} nativeButton={false} size="touch" className="w-full">
            Sign in with Google
          </Button>
        </CardContent>
      </Card>
    </JoinFrame>
  );
}

/** Flow B step 7: no `code` in the URL and none stored. "Go to home" replaces, as in `JoinInvite`. */
function IncompleteCard() {
  const router = useRouter();
  return (
    <JoinFrame>
      <Card>
        <CardHeader>
          <CardTitle>This invite link is incomplete.</CardTitle>
          <CardDescription>Open the link from your invite again, or ask for a new one.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button size="touch" className="w-full" onClick={() => router.replace("/")}>
            Go to home
          </Button>
        </CardContent>
      </Card>
    </JoinFrame>
  );
}
```

- [ ] **Step 6 (agent): Run the test to verify it passes, then prove the `/me` gate is tested**

```bash
(cd frontend && npx vitest run src/app/join/join.test.tsx 2>&1 | grep -E "Test Files|Tests ")
sed -i.bak 's/useMe({ enabled: view.kind === "signed-in" \&\& !signingOut })/useMe({ enabled: !signingOut })/' frontend/src/app/join/join-client.tsx
grep -c 'useMe({ enabled: !signingOut })' frontend/src/app/join/join-client.tsx
(cd frontend && npx vitest run src/app/join/join.test.tsx 2>&1 | grep -E "Tests ")
mv frontend/src/app/join/join-client.tsx.bak frontend/src/app/join/join-client.tsx
(cd frontend && npx vitest run src/app/join/join.test.tsx 2>&1 | grep -E "Tests ")
```

**Expected:** `Test Files  1 passed (1)` and `Tests  12 passed (12)`. Then `1` (the gate is removed), then `Tests  5 failed | 7 passed (12)`. The five failures are the three signed-out tests, the post-login test and the incomplete-link test. In each, `/me` either 401s into a sign-out or has no handler. After the restore, `Tests  12 passed (12)`. `git status --short` must not list a `.bak` file.

- [ ] **Step 7 (agent): Run the whole frontend suite, typecheck, lint and the build; check the prerendered head**

```bash
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled|/join|rror")
grep -o '<title>[^<]*</title>\|<meta name="robots"[^>]*>\|<meta name="referrer"[^>]*>' frontend/.next/server/app/join.html
git status --short
```

**Expected:** `Test Files  33 passed (33)` and `Tests  204 passed (204)` (192 + 12). `tsc --noEmit` and `eslint` print no errors. The react-hooks 7 rules pass: every `setState` in an effect runs in a promise callback, and the ref is read only in the effect. The build prints `✓ Compiled successfully` and `├ ○ /join` (static; the build fails here if the `<Suspense>` is missing), and no error line. The head check prints exactly `<title>Join a church</title>`, `<meta name="referrer" content="no-referrer"/>` and `<meta name="robots" content="noindex, nofollow"/>`. `git status --short` lists exactly these, plus `?? .claude/`. `.next/` is gitignored.

```
?? frontend/src/app/join/
```

The backend is untouched: **796 passed, 9 skipped** (Task 14's line; no need to rerun).

- [ ] **Step 8 (agent): Commit**

```bash
git add frontend/src/app/join/page.tsx frontend/src/app/join/join-client.tsx frontend/src/app/join/join.test.tsx
git commit -m "$(cat <<'EOF'
Frontend: /join captures the invite code, signs in and previews it (S Flow B, F §4.3)

- page.tsx (server): metadata title "Join a church", robots noindex/nofollow,
  referrer no-referrer (clarification 45); the client part in Suspense.
- join-client.tsx: the code is captured once into sessionStorage, replaceState
  takes it out of the address bar, the post-login path is cleared (clarification
  27); signed-in state from getAccessToken, a network error is ErrorState + Retry
  (clarification 20); /me loads only once signed in (clarification 47); the page
  answers 401s itself, keeping the code (clarification 19); JoinInvite previews.
- join.test.tsx: 12 tests, including AC9 (the code only in POST bodies) and
  AC10's second-church case. Frontend 192 -> 204 tests, 32 -> 33 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
git log --oneline -1
```

**Expected:** one commit with the three new files. `git status --short` then lists only `?? .claude/`.
### Task 16: `CreateChurchForm`, the Create tab (S Flow A Create tab; S "Loading, empty and error states" row "Accept / Create"; AC6, AC11; 1b clarifications 24, 25, 46)

The Create tab's form, as its own component so Task 17's `/welcome` only places it in a tab. It checks the name and time zone on the client with the server's exact messages and sends nothing when either is blank (the first invalid field gets focus), posts `POST /churches` through Task 13's `useCreateChurch` with an `Idempotency-Key` from one Task 9 key tracker per mount, and then handles each outcome the way S's table says: a 422 with `fields.name` / `fields.timezone` shows under the field and focuses it; a 429 shows the server message in an inline alert above the button, with no toast; a network error, timeout or 5xx is a toast (Task 9's `errorToastMessage`: the long "Can't reach the server. Check your connection and try again." or "Something went wrong. (Ref: …)") and keeps the key, so an unchanged retry replays instead of creating a second church (AC6). Any 2xx or 4xx, or an edited body, gets a new key (Task 9's `settleOutcome` decides; 1b clarification 46). After 8 s of pending the line "Still working — this can take up to a minute." shows (F §1.8; kept verbatim although the client times out at 30 s, 1b clarification 25). Success toasts "Created {name}. You're the owner.", then Task 13's `useMembershipChanged` stores the new church, refetches `/me` and goes to `/`. The backend does not change.

Choices made here that S leaves open (none changes what S shows):
- The time-zone field is Task 12's `TimezoneCombobox`, which owns its label "Time zone", its helper "Sets the default service date (the next Sunday in this time zone)." and its inline error. The form renders only the name field's label and error, and gives the combobox an `id` from `useId()` so a failed check can focus it with `document.getElementById(id)`.
- The body is sent trimmed (`{ name: name.trim(), timezone: timezone.trim() }`; the server trims too), and the key tracker fingerprints that trimmed body.
- The button stays pending ("Creating church…") after a 201 until `useMembershipChanged` navigates, so a second tap during the `/me` refetch cannot create a second church under a fresh key.
- The success toast fires before `useMembershipChanged`, in S's order ("toast → the new church becomes active → `/`").
- A 422 without `fields.name` / `fields.timezone` (e.g. `idempotency_mismatch`, which a fresh-key-per-edit tracker should never meet) is a toast with its message.
- The time-zone default is read in a `useState` initializer. It cannot differ from a server render: the `(signed-in)` layout shows its skeleton until `/me` loads, so the form never renders on the server.

Test notes. The tests stub `Intl.supportedValuesOf` and `Intl.DateTimeFormat.prototype.resolvedOptions` (browser zone `America/Chicago`; never the runner's zone, Global Constraints). For "no zone list" they replace the global `Intl` with an object whose prototype is the real `Intl` and whose own `supportedValuesOf` is `undefined`, so `typeof Intl.supportedValuesOf !== "function"` while `Intl.DateTimeFormat` still works. The file's own `afterEach` (not a second global one; P1a's rule is about `setup-dom.ts`) restores spies, globals and real timers. Toasts are asserted through `vi.spyOn(toast, "success" | "error")`, as `church-layout.test.tsx:111-118` does. The 8-second test uses `vi.useFakeTimers()` with `fireEvent` and `act(() => vi.advanceTimersByTimeAsync(…))`, never `waitFor`/`findBy` (their own timers would be fake too).

Verified in a throwaway worktree at `0295b37` with Task 9's `idempotency.ts`, `timezones.ts` and `errorToastMessage`, Task 12's `timezone-combobox.tsx` and Task 13's `me.ts`, `onboarding.ts` and `membership.ts` copied verbatim from their plan steps (and `CreateChurchBody` as `{ name: string; timezone: string }`, which is what Task 13's `Required<components["schemas"]["CreateChurchIn"]>` resolves to): the test file fails as quoted in Step 3 before the component exists and passes (10 of 10, three runs in a row) after; `tsc --noEmit` and `eslint` report nothing in these files. Mutation checks: sending `crypto.randomUUID()` instead of `tracker.keyFor(body)` fails the network-retry and 5xx-retry tests; not focusing the name fails the blank-name test; a 9 000 ms delay fails the "Still working" test; dropping the 429 branch fails the 429 test.

**Files:**
- Create: `frontend/src/components/onboarding/create-church-form.tsx`
- Create: `frontend/src/components/onboarding/create-church-form.test.tsx` (10 tests)

**Interfaces:**
- Consumes:
  - Task 9, `frontend/src/lib/idempotency.ts`: `createKeyTracker(): KeyTracker` with `keyFor(body: unknown): string` and `settle(outcome: "success" | "client_error" | "uncertain"): void`; `settleOutcome(e: unknown): "client_error" | "uncertain"` (4xx `ApiError` → `client_error`; status 0, 5xx or a non-`ApiError` → `uncertain`).
  - Task 9, `frontend/src/lib/timezones.ts`: `listTimezones(): string[] | null`, `defaultTimezone(list: string[] | null): string` (the browser zone when listed, else `"America/New_York"`).
  - Task 9, `frontend/src/lib/api/errors.ts`: `errorToastMessage(e: unknown): string` (`e.message` for `network_error` / `timeout` / `aborted`, else `describeError(e)`, which gives `Something went wrong. (Ref: <first 8 of requestId>)` for a 5xx).
  - Task 12, `frontend/src/components/app/timezone-combobox.tsx`: `TimezoneCombobox({ value, onChange, error, id }: { value: string; onChange: (value: string) => void; error?: string | null; id?: string })`. It renders `<Label htmlFor={id}>Time zone</Label>`, the input (combobox, or a text input when `listTimezones()` is null) with `id` as the `<input>`'s id, the helper and `error` below with `aria-invalid="true"`.
  - Task 13, `frontend/src/lib/queries/onboarding.ts`: `useCreateChurch(): UseMutationResult<Church, ApiError, { body: CreateChurchBody; key: string }>` (`POST /churches`, `json: body`, `Idempotency-Key: key`, no `X-Church-Id`, 30 s timeout from `timeouts.ts:7`, `retry: false`).
  - Task 13, `frontend/src/lib/queries/membership.ts`: `useMembershipChanged(): (change: { selectChurchId?: string | null }) => Promise<void>` (stores the id, `fetchQuery({ ...meQueryOptions(api), staleTime: 0 })`, then `router.replace("/")`, or `"/welcome"` when `/me` lists no church; never rejects).
  - 1a: `PendingButton({ pending, pendingLabel })` (`frontend/src/components/app/pending-button.tsx`; disabled and `aria-busy` while pending), `Alert` / `AlertDescription` (`components/ui/alert.tsx`; `role="alert"`, `variant="destructive"`), `Input` (`components/ui/input.tsx`; `h-8`, sized `h-11` here), `Label`, `Button` size `touch` (`h-11`, via `PendingButton`), `ApiError` (`lib/api/client.ts:12-30`: `status`, `code`, `message`, `fields?`), `Church` (`lib/api/types.ts`), `toast` from `sonner`.
  - Test helpers: `renderWithProviders` (`test/render.tsx`), `installFakeApi` / `fakeError` / `FAKE_REQUEST_ID` (`4f9a2c1e…`) / types `FakeApi`, `FakeResponse`, `RecordedRequest` (`test/fake-api.ts`), `testRouter` (`test/mocks.ts`), `church`, `me`, `CHURCH_IDS` (`test/fixtures/index.ts`), `readStoredChurchId` (`lib/church.ts:35`), `NETWORK_MESSAGE` (`lib/api/client.ts:50`).
- Produces (`frontend/src/components/onboarding/create-church-form.tsx`):
  - `CreateChurchForm(): JSX.Element` (no props): a native `<form noValidate>` with the intro "Start a new church. You'll be its owner and can invite others.", "Church name" (`Input`, placeholder "e.g. First Presbyterian Church", `maxLength={200}`, `h-11`), `TimezoneCombobox`, the caption "Your church gets its own copy of the starter hymnal.", the 429 alert slot, the full-width `size="touch"` "Create church" button (pending label "Creating church…") and the 8 s `role="status"` line. Later user: Task 17 (`/welcome` Create tab).
  - `SLOW_AFTER_MS = 8_000`.

Counts after this task: backend **796 passed, 9 skipped** (unchanged since Task 14 deleted `streamlit_tests/test_onboarding.py`); frontend **214 passed in 34 files** (Task 15's 204 in 33, which includes Q4's +1 from Task 11, plus 10 in one new file). The outline's "213 / 34" is the count without Q4.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
ls frontend/src/components/onboarding/create-church-form.tsx 2>&1 | grep -c "No such file"
grep -c -E "^export function (createKeyTracker|settleOutcome)\(" frontend/src/lib/idempotency.ts
grep -c -E "^export function (listTimezones|defaultTimezone)\(" frontend/src/lib/timezones.ts
grep -c -E "^export function errorToastMessage\(" frontend/src/lib/api/errors.ts
cat frontend/src/lib/queries/onboarding.ts frontend/src/lib/queries/membership.ts frontend/src/components/app/timezone-combobox.tsx | grep -c -E "^export function (useCreateChurch|useMembershipChanged|TimezoneCombobox)\("
```

**Expected:** `git status --short` lists only `?? .claude/`; the last commit is Task 15's; `Test Files  33 passed (33)` and `Tests  204 passed (204)`; then `1` (the form does not exist yet); then `2`, `2`, `1` and `3` (Tasks 9, 12 and 13 are in). If the frontend counts differ, stop and ask.

- [ ] **Step 2 (agent): Write the failing tests**

Create `frontend/src/components/onboarding/create-church-form.test.tsx`:

```tsx
import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { NETWORK_MESSAGE } from "@/lib/api/client";
import { readStoredChurchId } from "@/lib/church";
import { fakeError, installFakeApi, type FakeApi, type FakeResponse, type RecordedRequest } from "@/test/fake-api";
import { CHURCH_IDS, church, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { CreateChurchForm } from "./create-church-form";

const NEW_LIFE = church({ id: CHURCH_IDS.hope, name: "New Life", role: "owner" });
const ZONES = ["America/Chicago", "America/New_York", "Europe/London"];
const REAL_OPTIONS = new Intl.DateTimeFormat().resolvedOptions();
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const STILL_WORKING = "Still working — this can take up to a minute.";
const LIMIT_MESSAGE = "You've created 5 churches in the last 24 hours. Try again later.";

/** The browser lists three zones and reports `America/Chicago` (never the runner's own zone). */
function stubZones(): void {
  vi.spyOn(Intl, "supportedValuesOf").mockReturnValue(ZONES);
  vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({
    ...REAL_OPTIONS,
    timeZone: "America/Chicago",
  });
}

/** A browser without `Intl.supportedValuesOf`: the time zone is a plain text input. */
function stubNoZoneList(): void {
  vi.stubGlobal("Intl", Object.assign(Object.create(Intl) as typeof Intl, { supportedValuesOf: undefined }));
}

function posts(api: FakeApi) {
  return api.requests.filter((req) => req.method === "POST" && req.path === "/churches");
}

function renderForm() {
  return renderWithProviders(<CreateChurchForm />);
}

describe("CreateChurchForm", () => {
  let toastSuccess: MockInstance<typeof toast.success>;
  let toastError: MockInstance<typeof toast.error>;

  beforeEach(() => {
    toastSuccess = vi.spyOn(toast, "success").mockImplementation(() => 0);
    toastError = vi.spyOn(toast, "error").mockImplementation(() => 0);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("creates the church with a UUID Idempotency-Key, refetches /me, selects it and goes home", async () => {
    stubZones();
    const api = installFakeApi({
      "POST /churches": { status: 201, body: NEW_LIFE },
      "GET /me": me({ churches: [church(), NEW_LIFE] }),
    });
    let requestsAtReplace: string[] = [];
    testRouter.replace.mockImplementation(() => {
      requestsAtReplace = api.requests.map((req) => `${req.method} ${req.path}`);
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "  New Life ");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    expect(requestsAtReplace).toEqual(["POST /churches", "GET /me"]);
    const [post] = posts(api);
    expect(post.body).toEqual({ name: "New Life", timezone: "America/Chicago" });
    expect(post.headers["Idempotency-Key"]).toMatch(UUID);
    expect(post.headers["X-Church-Id"]).toBeUndefined();
    expect(readStoredChurchId()).toBe(CHURCH_IDS.hope);
    expect(toastSuccess).toHaveBeenCalledWith("Created New Life. You're the owner.");
    expect(toastError).not.toHaveBeenCalled();
  });

  it("checks a blank name on the client: inline message, focus, no request", async () => {
    stubZones();
    const api = installFakeApi({});
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "   ");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    expect(screen.getByText("Church name is required.")).toBeInTheDocument();
    expect(screen.getByLabelText("Church name")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Church name")).toHaveFocus();
    expect(api.requests).toHaveLength(0);
  });

  it("checks an empty time zone on the client when the browser has no zone list", async () => {
    stubNoZoneList();
    const api = installFakeApi({});
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.clear(screen.getByLabelText("Time zone"));
    await user.click(screen.getByRole("button", { name: "Create church" }));

    expect(screen.getByText("Timezone is required.")).toBeInTheDocument();
    expect(screen.getByLabelText("Time zone")).toHaveFocus();
    expect(screen.queryByText("Church name is required.")).not.toBeInTheDocument();
    expect(api.requests).toHaveLength(0);
  });

  it("shows a 422 'Unknown timezone.' under the field, then a fixed resubmit gets a new key", async () => {
    stubNoZoneList();
    const api = installFakeApi({
      "POST /churches": (req: RecordedRequest) =>
        (req.body as { timezone: string }).timezone === "Mars/Base"
          ? fakeError(422, "invalid_request", "Unknown timezone.", { fields: { timezone: "Unknown timezone." } })
          : { status: 201, body: NEW_LIFE },
      "GET /me": me({ churches: [NEW_LIFE] }),
    });
    const { user } = renderForm();
    const zone = screen.getByLabelText("Time zone");

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.clear(zone);
    await user.type(zone, "Mars/Base");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    expect(await screen.findByText("Unknown timezone.")).toBeInTheDocument();
    expect(zone).toHaveFocus();
    expect(toastError).not.toHaveBeenCalled();

    await user.clear(zone);
    await user.type(zone, "Europe/London");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    const [first, second] = posts(api);
    expect(second.body).toEqual({ name: "New Life", timezone: "Europe/London" });
    expect(second.headers["Idempotency-Key"]).toMatch(UUID);
    expect(second.headers["Idempotency-Key"]).not.toBe(first.headers["Idempotency-Key"]);
    expect(screen.queryByText("Unknown timezone.")).not.toBeInTheDocument();
  });

  it("retries an unchanged body after a network error with the same key", async () => {
    stubZones();
    let calls = 0;
    const api = installFakeApi({
      "POST /churches": () => {
        calls += 1;
        if (calls === 1) throw new TypeError("Failed to fetch");
        return { status: 201, body: NEW_LIFE };
      },
      "GET /me": me({ churches: [NEW_LIFE] }),
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledTimes(1));
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    const [first, second] = posts(api);
    expect(first.headers["Idempotency-Key"]).toMatch(UUID);
    expect(second.headers["Idempotency-Key"]).toBe(first.headers["Idempotency-Key"]);
    expect(second.body).toEqual(first.body);
  });

  it("gets a new key when the body changes after a network error", async () => {
    stubZones();
    let calls = 0;
    const api = installFakeApi({
      "POST /churches": () => {
        calls += 1;
        if (calls === 1) throw new TypeError("Failed to fetch");
        return { status: 201, body: church({ id: CHURCH_IDS.hope, name: "New Life Church", role: "owner" }) };
      },
      "GET /me": me({ churches: [NEW_LIFE] }),
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledTimes(1));
    await user.type(screen.getByLabelText("Church name"), " Church");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    const [first, second] = posts(api);
    expect(second.body).toEqual({ name: "New Life Church", timezone: "America/Chicago" });
    expect(second.headers["Idempotency-Key"]).toMatch(UUID);
    expect(second.headers["Idempotency-Key"]).not.toBe(first.headers["Idempotency-Key"]);
  });

  it("toasts a 5xx with its Ref and retries with the same key", async () => {
    stubZones();
    let calls = 0;
    const api = installFakeApi({
      "POST /churches": () => {
        calls += 1;
        return calls === 1
          ? fakeError(500, "internal_error", "Something went wrong.")
          : { status: 201, body: NEW_LIFE };
      },
      "GET /me": me({ churches: [NEW_LIFE] }),
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));
    await waitFor(() => expect(toastError).toHaveBeenCalledWith("Something went wrong. (Ref: 4f9a2c1e)"));
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    const [first, second] = posts(api);
    expect(second.headers["Idempotency-Key"]).toBe(first.headers["Idempotency-Key"]);
  });

  it("toasts a network error with the full sentence and keeps what was typed", async () => {
    stubZones();
    installFakeApi({
      "POST /churches": () => {
        throw new TypeError("Failed to fetch");
      },
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    await waitFor(() => expect(toastError).toHaveBeenCalledWith(NETWORK_MESSAGE));
    expect(toastError).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText("Church name")).toHaveValue("New Life");
    expect(screen.getByRole("button", { name: "Create church" })).toBeEnabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("shows a 429 in an inline alert above the button, with no toast", async () => {
    stubZones();
    installFakeApi({
      "POST /churches": fakeError(429, "rate_limited", LIMIT_MESSAGE, { details: { retry_after_seconds: 3600 } }),
    });
    const { user } = renderForm();

    await user.type(screen.getByLabelText("Church name"), "New Life");
    await user.click(screen.getByRole("button", { name: "Create church" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(LIMIT_MESSAGE);
    expect(toastError).not.toHaveBeenCalled();
    expect(toastSuccess).not.toHaveBeenCalled();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("shows 'Still working' after 8 s of pending and hides it when the request ends", async () => {
    vi.useFakeTimers();
    stubZones();
    let answer: (response: FakeResponse) => void = () => {};
    installFakeApi({
      "POST /churches": () =>
        new Promise<FakeResponse>((resolve) => {
          answer = resolve;
        }),
    });
    renderForm();

    fireEvent.change(screen.getByLabelText("Church name"), { target: { value: "New Life" } });
    fireEvent.click(screen.getByRole("button", { name: "Create church" }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.getByRole("button", { name: "Creating church…" })).toBeDisabled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(7_999);
    });
    expect(screen.queryByText(STILL_WORKING)).not.toBeInTheDocument();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(screen.getByText(STILL_WORKING)).toBeInTheDocument();

    answer(fakeError(500, "internal_error", "Something went wrong."));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(screen.queryByText(STILL_WORKING)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create church" })).toBeEnabled();
  });
});
```

The ten tests, in S's terms: the happy path (body, UUID key, no `X-Church-Id`, `/me` fetched before `replace("/")`, stored id, toast); blank name → inline, focus, no request; empty time zone in the text fallback → inline, focus, no request; a server 422 "Unknown timezone." → inline and focus, then a fixed resubmit gets a **new** key; network error → unchanged retry → **same** key; network error → edit → **new** key; 5xx → Ref toast → **same** key; the network toast is the long `NETWORK_MESSAGE` and the typed name stays; 429 → inline alert, no toast; "Still working" at 8 s, gone when the request ends.

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
(cd frontend && npx vitest run src/components/onboarding/create-church-form.test.tsx 2>&1 | grep -E "Failed to resolve|Test Files|Tests ")
```

**Expected:** FAIL before any test runs, because the component does not exist yet:

```
Error: Failed to resolve import "./create-church-form" from "src/components/onboarding/create-church-form.test.tsx". Does the file exist?
 Test Files  1 failed (1)
      Tests  no tests
```

- [ ] **Step 4 (agent): Create `frontend/src/components/onboarding/create-church-form.tsx`**

```tsx
"use client";

/**
 * The Create tab of `/welcome` (S Flow A step 4; S "Loading, empty and error states", row
 * "Accept / Create"; AC6, AC11).
 *
 * - The client checks first, with the server's exact messages, and sends nothing when a
 *   check fails: the message shows under the field and the first invalid field gets focus.
 * - One Idempotency-Key tracker per mount (F §1.6): an identical retry after a network
 *   error, timeout or 5xx reuses the key, so the server replays the first answer instead of
 *   creating a second church; any 2xx or 4xx, or an edit, gets a new key, so a corrected
 *   resubmit never meets a stored 422 or `idempotency_mismatch`.
 * - A 422 with `fields.name` / `fields.timezone` shows inline like the client checks; a 429
 *   shows its message in an inline alert above the button (no toast); anything else is a
 *   toast (`errorToastMessage`: the long network sentence, or "Something went wrong. (Ref: …)").
 * - After 8 s of pending, "Still working — this can take up to a minute." (F §1.8; 1b
 *   clarification 25).
 * - Success: toast "Created {name}. You're the owner.", then `useMembershipChanged` stores the
 *   new church, refetches `/me` and goes to `/`. The button stays pending until then, so a
 *   second tap cannot create a second church with a new key.
 *
 * It renders only on the client (the `(signed-in)` layout shows its skeleton until `/me`
 * loads), so the time-zone default in the `useState` initializer cannot differ from a server
 * render.
 */
import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { TimezoneCombobox } from "@/components/app/timezone-combobox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import { errorToastMessage } from "@/lib/api/errors";
import type { Church } from "@/lib/api/types";
import { createKeyTracker, settleOutcome } from "@/lib/idempotency";
import { useMembershipChanged } from "@/lib/queries/membership";
import { useCreateChurch } from "@/lib/queries/onboarding";
import { defaultTimezone, listTimezones } from "@/lib/timezones";

/** How long a create may run before the "Still working" line shows (F §1.8). */
export const SLOW_AFTER_MS = 8_000;

type FieldErrors = { name?: string; timezone?: string };

/** The name and time-zone messages of a 422, or null when it has neither (then it is a toast). */
function fieldErrorsOf(e: unknown): FieldErrors | null {
  if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return null;
  const { name, timezone } = e.fields;
  return name || timezone ? { name, timezone } : null;
}

export function CreateChurchForm() {
  const nameId = useId();
  const timezoneId = useId();
  const nameRef = useRef<HTMLInputElement>(null);
  const [tracker] = useState(() => createKeyTracker());
  const [name, setName] = useState("");
  const [timezone, setTimezone] = useState(() => defaultTimezone(listTimezones()));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [limitMessage, setLimitMessage] = useState<string | null>(null);
  const [slow, setSlow] = useState(false);
  const [created, setCreated] = useState(false);
  const create = useCreateChurch();
  const membershipChanged = useMembershipChanged();
  const pending = create.isPending || created;

  useEffect(() => {
    if (!pending) return;
    const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS);
    return () => clearTimeout(timer);
  }, [pending]);

  function showFieldErrors(next: FieldErrors) {
    setErrors(next);
    if (next.name) nameRef.current?.focus();
    else document.getElementById(timezoneId)?.focus();
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    const body = { name: name.trim(), timezone: timezone.trim() };
    const checks: FieldErrors = {};
    if (body.name === "") checks.name = "Church name is required.";
    if (body.timezone === "") checks.timezone = "Timezone is required.";
    setLimitMessage(null);
    if (checks.name || checks.timezone) {
      showFieldErrors(checks);
      return;
    }
    setErrors({});
    setSlow(false);

    let church: Church;
    try {
      church = await create.mutateAsync({ body, key: tracker.keyFor(body) });
    } catch (e) {
      tracker.settle(settleOutcome(e));
      // A 401 is already signing out (useCreateChurch's handleAuthErrors): no toast.
      if (e instanceof ApiError && (e.status === 401 || e.code === "aborted")) return;
      const fields = fieldErrorsOf(e);
      if (fields) showFieldErrors(fields);
      else if (e instanceof ApiError && e.code === "rate_limited") setLimitMessage(e.message);
      else toast.error(errorToastMessage(e));
      return;
    }
    tracker.settle("success");
    setCreated(true);
    toast.success(`Created ${church.name}. You're the owner.`);
    await membershipChanged({ selectChurchId: church.id });
  }

  return (
    <form noValidate className="grid gap-4" onSubmit={(event) => void onSubmit(event)}>
      <p className="text-sm text-muted-foreground">
        Start a new church. You&apos;ll be its owner and can invite others.
      </p>
      <div className="grid gap-2">
        <Label htmlFor={nameId}>Church name</Label>
        <Input
          ref={nameRef}
          id={nameId}
          name="name"
          autoComplete="off"
          placeholder="e.g. First Presbyterian Church"
          maxLength={200}
          value={name}
          onChange={(event) => setName(event.target.value)}
          aria-invalid={errors.name ? true : undefined}
          aria-describedby={errors.name ? `${nameId}-error` : undefined}
          className="h-11"
        />
        {errors.name ? (
          <p id={`${nameId}-error`} className="text-sm text-destructive">
            {errors.name}
          </p>
        ) : null}
      </div>
      <TimezoneCombobox id={timezoneId} value={timezone} onChange={setTimezone} error={errors.timezone} />
      <p className="text-sm text-muted-foreground">Your church gets its own copy of the starter hymnal.</p>
      {limitMessage ? (
        <Alert variant="destructive">
          <AlertDescription>{limitMessage}</AlertDescription>
        </Alert>
      ) : null}
      <PendingButton type="submit" size="touch" className="w-full" pending={pending} pendingLabel="Creating church…">
        Create church
      </PendingButton>
      {pending && slow ? (
        <p role="status" className="text-sm text-muted-foreground">
          Still working — this can take up to a minute.
        </p>
      ) : null}
    </form>
  );
}
```

- [ ] **Step 5 (agent): Run the tests to verify they pass, then the whole frontend and backend suites**

```bash
(cd frontend && npx vitest run src/components/onboarding/create-church-form.test.tsx 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `Test Files  1 passed (1)` and `Tests  10 passed (10)`; then `Test Files  34 passed (34)` and `Tests  214 passed (214)` (204 + 10), `tsc --noEmit` and `eslint` print no errors; then `796 passed, 9 skipped in <t>s` (no backend change; Task 14's line); `git status --short` lists exactly (plus `?? .claude/`):

```
?? frontend/src/components/onboarding/create-church-form.test.tsx
?? frontend/src/components/onboarding/create-church-form.tsx
```

If `tsc` reports `Parameter 'req' implicitly has an 'any' type` in the test, the `RecordedRequest` annotation on the 422 handler was dropped (`FakeHandler` includes `unknown`, so a handler gets no contextual type). If the 8-second test hangs until Vitest's timeout, a `waitFor` or `findBy` was used while timers are fake. If a key test fails with two different keys where one is expected, the form called `crypto.randomUUID()` or created a tracker per render instead of `useState(() => createKeyTracker())`. If the time-zone tests find two "Time zone" labels, the form rendered its own label; `TimezoneCombobox` owns it (Task 12).

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/onboarding/create-church-form.tsx frontend/src/components/onboarding/create-church-form.test.tsx
git status --short
git commit -m "Frontend: CreateChurchForm, the Create tab (S Flow A Create tab; AC6, AC11)

Church name and TimezoneCombobox (the browser's zone preselected when
listed, else America/New_York). The client checks the trimmed name and
the time zone with the server's messages and sends nothing when either
is blank; the first invalid field gets focus. POST /churches carries an
Idempotency-Key from one key tracker per form: an unchanged retry after
a network error, timeout or 5xx reuses it, any 2xx or 4xx or an edit
gets a new one. A 422 shows under its field, a 429 in an inline alert
above the button, anything else is a toast (the full network sentence
or \"Something went wrong. (Ref: ...)\"). After 8 s \"Still working —
this can take up to a minute.\" Success toasts \"Created {name}. You're
the owner.\", selects the new church, refetches /me and goes to /.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** after `git add`, `git status --short` shows `A  frontend/src/components/onboarding/create-church-form.test.tsx` and `A  frontend/src/components/onboarding/create-church-form.tsx` (plus `?? .claude/`); the commit prints `2 files changed, 450 insertions(+)` with both `create mode` lines; `git log --oneline -1` shows the new subject; the final `git status --short` lists only `?? .claude/`.
### Task 17: `/welcome` with the Join and Create tabs (S Flow A, Flow C, Pages; F §4.1; AC11; replaces the 1a stub; clarifications 28, 30)

This task replaces 1a's stub `/welcome` ("No church yet") with the real page. It is the zero-church landing (the `(church)` layout's `router.replace("/welcome")`, `(church)/layout.tsx:63-65`) and, from Task 18 on, the switcher's "Join or create a church…" target. The page owns the frame and the copy around the two tabs; the tabs' contents are Task 14's `JoinInvite` and Task 16's `CreateChurchForm` (S Pages: "Join tab = `<JoinInvite … autoPreview />`; Create tab = `<CreateChurchForm />`"). The backend does not change.

What the page renders, in order (S Flow A step 2, Flow C; Global Constraints "Client copy"):
- `AppHeader user={me.user} onSignOut={…}` with no `churches`, so it shows the app name "Worship Service Builder" and the account menu, never the switcher (S behavior change 20: a zero-church user can still log out).
- Zero churches: H1 **"Welcome to Worship Service Builder"**, sub "Signed in as {email}. You don't belong to a church yet." With churches: a link **"← Back to {active church}"** (`next/link`, `href="/"`), H1 **"Join or create a church"**, sub "Signed in as {email}.".
- Tabs **"Join a church"** / **"Create a church"**: default `join`; `?tab=create` opens Create; any other value (`?tab=foo`, none) opens Join. A tab change calls `router.replace("/welcome?tab=<tab>", { scroll: false })`, so a refresh keeps the tab.
- Join tab: when `wsb:pendingInviteCode` is set, the info alert **"You opened an invite link. Review and accept it below."** above `<JoinInvite initialCode={code} autoPreview email={me.user.email} showEntry />` (prefilled field, one automatic preview). Without a code, `JoinInvite` in its `enter` state.
- Create tab: `<CreateChurchForm />` (its intro, "Church name", `TimezoneCombobox`, caption and "Create church" button are Task 16's).

**Notes from the code (the outline's Interfaces are kept; these fill in what it leaves open):**
- **Suspense (clarification 28).** Only the tabs read `useSearchParams()`, so only `WelcomeTabs` sits inside `<Suspense fallback={null}>`; the heading and header render outside it. On the client the hook never suspends, so the fallback is never seen; the boundary is for `next build` (`use-search-params.md:180-181`). The page stays a `"use client"` page with no `metadata` (as P1a; the root layout's title applies).
- **Tab state is local, initialised from `?tab=`.** The tab switches at once on a click, and `router.replace` follows. Deriving the tab from `useSearchParams()` alone would lag behind Next's transition and, under the DOM mock (`test/mocks.ts`: the search params change only with `setTestPath`), would never switch. Nothing can change `?tab=` under a mounted `/welcome` (its header has no switcher), so the state never needs re-syncing. Base UI calls `onValueChange` only for a different tab, so clicking the active tab does not replace the URL.
- **The pending code is read in a `useState` initializer inside the Join tab's own component (clarification 30; NF R4).** It never runs on the server: the `(signed-in)` layout renders children only after `/me` loads in the browser. Base UI unmounts an inactive panel, so switching to Create and back remounts `JoinTab`, which reads storage again: a code that `JoinInvite` has cleared (rejected, joined, "Not now") is not prefilled or previewed a second time, as it would be from a page-level read.
- **Known limit: the pending-invite alert stays for the life of the Join panel.** "You opened an invite link. Review and accept it below." follows the `pendingCode` read at mount, so after `JoinInvite` rejects or clears the code it still sits above the result card; switching tabs re-reads storage and drops it. The copy and placement match S ("If `wsb:pendingInviteCode` is set"); hiding it on the invite's outcome needs an `onStateChange` prop on `JoinInvite`, left to a later slice.
- **The back link (clarification 30):** `pickActiveChurch(me.churches, useStoredChurchId())`, the `(church)` layout's own choice (stored id if still a member, else the first by name), rendered only once the store has been read (`!== undefined`). The test stores Hope, which is second by name, so it proves the stored id is used (the outline's example says Grace, which is also the first-by-name fallback and so proves less). It uses `next/link`, which under Vitest resolves to `next/dist/client/link` (the pages-router build), so the tests assert `href="/"` only, never a click (critique M18). Verified: the first run prints no `stderr`, `Warning` or `act(` lines.
- **Sizing (Global Constraints "Mobile"; manual check 10).** `main` is `max-w-md` with `px-4` (16 px gutters). The generated `TabsList` sets `group-data-horizontal/tabs:h-8` and `w-fit` (`tabs.tsx:26`); a plain `h-11` would lose to it, so the call site passes `w-full group-data-horizontal/tabs:h-11`, which `cn`'s tailwind-merge swaps for the generated pair (verified in the rendered class list; the compiled rule is `.group-data-horizontal\/tabs\:h-11:is(:where(.group\/tabs):where([data-orientation=horizontal]) *)`). The back link is `inline-flex h-11` (a 44 px target). `tabs.tsx` itself is not edited (F §4.9 item 1).
- **Who renders which copy.** The page renders the headings, the back link, the tab labels and the Join tab's pending-code alert (the outline gives this task the alert test; `JoinInvite`'s props have no flag for it). `CreateChurchForm` renders the Create intro "Start a new church. You'll be its owner and can invite others." (S Pages: the Create tab *is* `<CreateChurchForm />`). Step 1 checks both with `grep`, and tests 3 and 5 fail with "Found multiple elements" if a string is rendered twice.
- **Time-zone test.** It stubs `Intl.supportedValuesOf` and `Intl.DateTimeFormat.prototype.resolvedOptions` (Global Constraints; Task 9's pattern) and restores them in this file's own `afterEach` (P1a's one-`afterEach` rule is about `setup-dom.ts`). The stubbed zone is `America/Chicago`, which has no `_`, so Task 12's input text `timezoneLabel(value)` equals the id. It queries `getByRole("combobox", { name: "Time zone" })` with the list closed (Task 12's note: the name is empty while the list is open). `getByDisplayValue` is not usable: Base UI also renders a hidden `<input>` with the same value.
- **Log out (test 1).** The keys are stored *after* the page has read storage, so nothing previews, and Log out must remove `wsb:pendingInviteCode` and `activeChurchId` (S A6; AC14). `useSignOut()` without options ends at `/login`.
- `components/app/app-header.tsx:17` still says "without them (the `/welcome` stub)". It is left alone here: Task 18's Step 1 requires `app-header.tsx` unchanged since `0295b37`. Task 19 or a later edit of that file can drop the word "stub".

Verified in a throwaway worktree at `0295b37` with Task 9's `timezones.ts` copied verbatim, Task 13's `invitePreview` builder, and minimal stand-ins for `JoinInvite` (label "Invite link or code", one guarded auto-preview through `useApi().user`, a "Join {church_name}" button) and `CreateChurchForm` (the intro and a Base UI combobox labelled "Time zone" defaulting to `defaultTimezone(listTimezones())`). The new test file fails as quoted in Step 3 against the stub page and passes (7) against Step 4's page, and the whole suite passed there (`Tests  132 passed (132)`: 126 − 1 + 7). `tsc --noEmit` and `eslint` were clean, and the production build listed `○ /welcome` with no Suspense error.

**Files:**
- Modify: `frontend/src/app/(signed-in)/welcome/page.tsx` (whole file replaced)
- Modify: `frontend/src/app/(signed-in)/welcome/welcome.test.tsx` (whole file replaced; 1a's one stub test is removed)

**Interfaces:**
- Consumes:
  - `useMeContext(): Me` (`lib/me-context.tsx:19`); `Me` = `{ user: { id, email: string, name?, picture? }, churches: Church[] }`.
  - `useStoredChurchId(): string | null | undefined` and `pickActiveChurch(churches: Church[], storedId: string | null | undefined, excluded?): Church | null` (`lib/church.ts:77`, `:13`); `type Me` re-exported from `lib/church.ts:6`.
  - `readSession(key: string): string | null`, `SESSION_KEYS.pendingInviteCode` = `"wsb:pendingInviteCode"` (`lib/storage.ts:45`, `:8-11`).
  - `useSignOut(): (opts?: SignOutOptions) => Promise<void>` (`lib/auth.ts:113`; Task 10 adds `selectAccount`, unused here).
  - `AppHeader({ user, churches?, active?, onSelectChurch?, onSignOut })` (`components/app/app-header.tsx:20`): no `churches` → no switcher.
  - Generated `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` (`components/ui/tabs.tsx`; Base UI `Tabs.Root` `value` / `onValueChange(value)`); `Alert`, `AlertDescription` (`components/ui/alert.tsx`; `role="alert"`).
  - `Link` from `next/link`; `useRouter`, `useSearchParams` from `next/navigation`.
  - Task 14: `JoinInvite({ initialCode?: string; autoPreview?: boolean; email: string; showEntry: boolean })` from `frontend/src/components/onboarding/join-invite.tsx` (named export): with `showEntry` it renders the "Invite link or code" field; with `autoPreview` and a non-empty `initialCode` it previews once, then shows the preview card with the button "Join {church_name}".
  - Task 16: `CreateChurchForm()` from `frontend/src/components/onboarding/create-church-form.tsx` (named export): renders the Create intro and Task 12's `TimezoneCombobox` (role `combobox`, name "Time zone") with `defaultTimezone(listTimezones())` as its first value.
  - Tests: Task 13's `invitePreview(overrides?: Partial<InvitePreview>): InvitePreview` (default `{ church_name: "Grace", role: "member", expires_at: "2026-10-05T12:00:00Z", email_bound: false, already_member: false }`); 1a's `me`, `church`, `CHURCH_IDS` (`test/fixtures/index.ts`), `installFakeApi` (`test/fake-api.ts`; `requests[]` of `{ method, path, headers, body }`), `renderWithProviders(ui, { path })` (`test/render.tsx`), `testRouter`, `supabaseAuth` (`test/mocks.ts`), `SignedInLayout` (`app/(signed-in)/layout.tsx`, as Task 11 left it).
- Produces (`frontend/src/app/(signed-in)/welcome/page.tsx`):
  - `export default function WelcomePage(): JSX.Element`, the `/welcome` route (`?tab=join|create`).
  - Module-private: `type WelcomeTab = "join" | "create"`; `parseTab(raw: unknown): WelcomeTab` (`"create"` → `create`, anything else → `join`); `WelcomeHeading({ me })`; `WelcomeTabs({ email })` (the only `useSearchParams` reader, inside `<Suspense fallback={null}>`); `JoinTab({ email })`.
  - Later users: Task 18's switcher item pushes `/welcome`; Task 19's manual checks 5, 7, 9 and 10 use this page; 6b's `useMembershipChanged({ selectChurchId: null })` lands here after leave/delete.

Counts after this task: backend **796 passed, 9 skipped** (unchanged since Task 14); frontend **220 passed in 34 files** (Task 16's 214 in 34, minus the stub test, plus 7; no new file). The outline's "219 / 34" is the count without Q4; the owner answered yes to Q4.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
grep -c '^  it(' "frontend/src/app/(signed-in)/welcome/welcome.test.tsx"
grep -n -E "^export function (JoinInvite|CreateChurchForm)\(" frontend/src/components/onboarding/join-invite.tsx frontend/src/components/onboarding/create-church-form.tsx
grep -rln "Start a new church" frontend/src --include=*.tsx | grep -v '\.test\.tsx$'
grep -rln "You opened an invite link" frontend/src --include=*.tsx | grep -v '\.test\.tsx$' | wc -l
```

**Expected:** `git status --short` lists only `?? .claude/`; the last commit is Task 16's. `Test Files  34 passed (34)` and `Tests  214 passed (214)`. Then `1` (1a's stub test). Then exactly two lines, one `export function JoinInvite(` in `join-invite.tsx` and one `export function CreateChurchForm(` in `create-church-form.tsx`. Then exactly one path, `frontend/src/components/onboarding/create-church-form.tsx` (the Create intro is Task 16's). Then `0` (no component renders the pending-code alert yet: this page does). If the counts differ, if either export is missing or is a default export, or if the intro lives elsewhere or the alert already exists in `join-invite.tsx`, stop and ask: the page below assumes this split of the copy.

- [ ] **Step 2 (agent): Replace the stub test with the `/welcome` tests**

Replace the whole of `frontend/src/app/(signed-in)/welcome/welcome.test.tsx` with:

```tsx
import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, invitePreview, me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import SignedInLayout from "../layout";
import WelcomePage from "./page";

const PENDING_CODE_KEY = "wsb:pendingInviteCode";

function renderWelcome(path = "/welcome") {
  return renderWithProviders(
    <SignedInLayout>
      <WelcomePage />
    </SignedInLayout>,
    { path },
  );
}

describe("/welcome (S Flow A, Flow C)", () => {
  afterEach(() => {
    // Test 7 spies on Intl; put the real functions back for the next test.
    vi.restoreAllMocks();
  });

  it("zero churches: welcome copy, a header without the switcher, Join tab by default, and Log out clears the keys", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [] }) });
    const { user } = renderWelcome();

    expect(
      await screen.findByRole("heading", { level: 1, name: "Welcome to Worship Service Builder" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Signed in as pat@example.com. You don't belong to a church yet."),
    ).toBeInTheDocument();
    expect(screen.getByText("Worship Service Builder")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^(Active church|Choose a church)/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Back to/ })).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Join a church" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Create a church" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByLabelText("Invite link or code")).toBeInTheDocument();

    // Stored after the page read them, so nothing previews: Log out must remove both.
    window.sessionStorage.setItem(PENDING_CODE_KEY, "abc123");
    window.localStorage.setItem("activeChurchId", CHURCH_IDS.grace);

    await user.click(screen.getByRole("button", { name: "Account menu" }));
    await user.click(await screen.findByRole("menuitem", { name: "Log out" }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(window.sessionStorage.getItem(PENDING_CODE_KEY)).toBeNull();
    expect(window.localStorage.getItem("activeChurchId")).toBeNull();
    expect(api.requests.filter((r) => r.path === "/me")).toHaveLength(1);
  });

  it("with churches: join-or-create copy and a link back to the stored church", async () => {
    window.localStorage.setItem("activeChurchId", CHURCH_IDS.hope);
    installFakeApi({
      "GET /me": me({
        churches: [church(), church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" })],
      }),
    });
    renderWelcome();

    expect(
      await screen.findByRole("heading", { level: 1, name: "Join or create a church" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Signed in as pat@example.com.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Back to Hope" })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("link", { name: "← Back to Grace" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^(Active church|Choose a church)/ })).not.toBeInTheDocument();
  });

  it("?tab=create opens on the Create tab", async () => {
    installFakeApi({ "GET /me": me({ churches: [] }) });
    renderWelcome("/welcome?tab=create");

    expect(await screen.findByRole("tab", { name: "Create a church" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(
      screen.getByText("Start a new church. You'll be its owner and can invite others."),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Invite link or code")).not.toBeInTheDocument();
  });

  it("an unknown ?tab= value opens on the Join tab", async () => {
    installFakeApi({ "GET /me": me({ churches: [] }) });
    renderWelcome("/welcome?tab=foo");

    expect(await screen.findByRole("tab", { name: "Join a church" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByLabelText("Invite link or code")).toBeInTheDocument();
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("changing the tab replaces the URL without scrolling", async () => {
    installFakeApi({ "GET /me": me({ churches: [] }) });
    const { user } = renderWelcome();

    await user.click(await screen.findByRole("tab", { name: "Create a church" }));

    expect(testRouter.replace).toHaveBeenCalledWith("/welcome?tab=create", { scroll: false });
    expect(screen.getByRole("tab", { name: "Create a church" })).toHaveAttribute("aria-selected", "true");
    expect(
      screen.getByText("Start a new church. You'll be its owner and can invite others."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Join a church" }));

    expect(testRouter.replace).toHaveBeenLastCalledWith("/welcome?tab=join", { scroll: false });
    expect(screen.getByLabelText("Invite link or code")).toBeInTheDocument();
  });

  it("a pending invite code shows the info alert and previews it once", async () => {
    window.sessionStorage.setItem(PENDING_CODE_KEY, "abc123");
    const api = installFakeApi({
      "GET /me": me({ churches: [] }),
      "POST /invites/preview": invitePreview(),
    });
    renderWelcome();

    expect(
      await screen.findByText("You opened an invite link. Review and accept it below."),
    ).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Join Grace" })).toBeInTheDocument();

    const previews = api.requests.filter((r) => r.path === "/invites/preview");
    expect(previews).toHaveLength(1);
    expect(previews[0].method).toBe("POST");
    expect(previews[0].body).toEqual({ code: "abc123" });
    expect(api.requests.filter((r) => r.path === "/invites/accept")).toHaveLength(0);
  });

  it("the Create tab preselects the browser's time zone", async () => {
    const realOptions = new Intl.DateTimeFormat().resolvedOptions();
    vi.spyOn(Intl, "supportedValuesOf").mockReturnValue([
      "America/Chicago",
      "America/New_York",
      "Europe/London",
    ]);
    vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({
      ...realOptions,
      timeZone: "America/Chicago",
    });
    installFakeApi({ "GET /me": me({ churches: [] }) });
    renderWelcome("/welcome?tab=create");

    expect(await screen.findByRole("combobox", { name: "Time zone" })).toHaveValue("America/Chicago");
  });
});
```

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
(cd frontend && npx vitest run "src/app/(signed-in)/welcome/welcome.test.tsx" 2>&1 | grep -E "^ +(×|→)|Test Files|Tests ")
```

**Expected:** all seven fail against the 1a stub (each after `findBy*`'s 1 s wait), with these reasons:

```
   × /welcome (S Flow A, Flow C) > zero churches: welcome copy, a header without the switcher, Join tab by default, and Log out clears the keys
     → Unable to find role="heading" and name "Welcome to Worship Service Builder"
   × /welcome (S Flow A, Flow C) > with churches: join-or-create copy and a link back to the stored church
     → Unable to find role="heading" and name "Join or create a church"
   × /welcome (S Flow A, Flow C) > ?tab=create opens on the Create tab
     → Unable to find role="tab" and name "Create a church"
   × /welcome (S Flow A, Flow C) > an unknown ?tab= value opens on the Join tab
     → Unable to find role="tab" and name "Join a church"
   × /welcome (S Flow A, Flow C) > changing the tab replaces the URL without scrolling
     → Unable to find role="tab" and name "Create a church"
   × /welcome (S Flow A, Flow C) > a pending invite code shows the info alert and previews it once
     → Unable to find an element with the text: You opened an invite link. Review and accept it below.. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.
   × /welcome (S Flow A, Flow C) > the Create tab preselects the browser's time zone
     → Unable to find role="combobox" and name "Time zone"
 Test Files  1 failed (1)
      Tests  7 failed (7)
```

(Each `×` line also ends with the test's duration.) If the run fails before any test with `does not provide an export named 'invitePreview'`, Task 13's fixture is missing: stop and ask.

- [ ] **Step 4 (agent): Replace the stub page**

Replace the whole of `frontend/src/app/(signed-in)/welcome/page.tsx` with:

```tsx
"use client";

/**
 * `/welcome` (S Flow A, Flow C; F §4.1): join or create a church. It is the
 * zero-church landing (the `(church)` layout sends users with no church here)
 * and the switcher's "Join or create a church…" target.
 *
 * - The header has no church switcher, but keeps the account menu, so a user
 *   with no church can still log out (S behavior change 20).
 * - The heading follows `me.churches`: the zero-church welcome, or "Join or
 *   create a church" with a "← Back to {active church}" link. The active
 *   church is the `(church)` layout's choice (`pickActiveChurch` over the
 *   stored id); the link waits until the stored id has been read.
 * - The tab comes from `?tab=join|create` (anything else is `join`). A tab
 *   change replaces the URL, so a refresh keeps the tab.
 * - The Join tab reads `wsb:pendingInviteCode` when it mounts: with a code it
 *   shows the info alert, prefills the field and previews automatically.
 *
 * `useSearchParams` sits inside `<Suspense>` (Next 16 needs the boundary for a
 * static build, 1b clarification 28). A `"use client"` page exports no
 * `metadata`; the root layout's title applies.
 */
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { AppHeader } from "@/components/app/app-header";
import { CreateChurchForm } from "@/components/onboarding/create-church-form";
import { JoinInvite } from "@/components/onboarding/join-invite";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useSignOut } from "@/lib/auth";
import { pickActiveChurch, useStoredChurchId, type Me } from "@/lib/church";
import { useMeContext } from "@/lib/me-context";
import { readSession, SESSION_KEYS } from "@/lib/storage";

type WelcomeTab = "join" | "create";

/** `?tab=` as a tab: `create` or `join`; anything else (missing, `foo`) is `join` (S Flow A). */
function parseTab(raw: unknown): WelcomeTab {
  return raw === "create" ? "create" : "join";
}

export default function WelcomePage() {
  const me = useMeContext();
  const signOut = useSignOut();

  return (
    <div className="min-h-dvh">
      <AppHeader user={me.user} onSignOut={() => void signOut()} />
      <main className="mx-auto grid max-w-md gap-6 px-4 py-6">
        <WelcomeHeading me={me} />
        <Suspense fallback={null}>
          <WelcomeTabs email={me.user.email} />
        </Suspense>
      </main>
    </div>
  );
}

function WelcomeHeading({ me }: { me: Me }) {
  const storedId = useStoredChurchId();
  const hasChurch = me.churches.length > 0;
  // `undefined` = the stored id is not read yet (hydration): no link until it is.
  const active = hasChurch && storedId !== undefined ? pickActiveChurch(me.churches, storedId) : null;

  return (
    <div className="grid gap-1">
      {active && (
        <Link
          href="/"
          className="inline-flex h-11 items-center self-start text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
        >
          ← Back to {active.name}
        </Link>
      )}
      <h1 className="text-2xl font-semibold">
        {hasChurch ? "Join or create a church" : "Welcome to Worship Service Builder"}
      </h1>
      <p className="text-sm text-muted-foreground">
        {hasChurch
          ? `Signed in as ${me.user.email}.`
          : `Signed in as ${me.user.email}. You don't belong to a church yet.`}
      </p>
    </div>
  );
}

function WelcomeTabs({ email }: { email: string }) {
  const searchParams = useSearchParams();
  const router = useRouter();
  // Local state, so the tab switches at once; the URL follows with replace (no history entry).
  const [tab, setTab] = useState<WelcomeTab>(() => parseTab(searchParams.get("tab")));

  function changeTab(value: unknown) {
    const next = parseTab(value);
    setTab(next);
    router.replace(`/welcome?tab=${next}`, { scroll: false });
  }

  return (
    <Tabs value={tab} onValueChange={changeTab}>
      <TabsList className="w-full group-data-horizontal/tabs:h-11">
        <TabsTrigger value="join">Join a church</TabsTrigger>
        <TabsTrigger value="create">Create a church</TabsTrigger>
      </TabsList>
      <TabsContent value="join" className="pt-2">
        <JoinTab email={email} />
      </TabsContent>
      <TabsContent value="create" className="pt-2">
        <CreateChurchForm />
      </TabsContent>
    </Tabs>
  );
}

function JoinTab({ email }: { email: string }) {
  // Read once per mount of the tab, never during a render on the server: the
  // `(signed-in)` layout renders children only after `/me` loads in the browser.
  // Re-reading on each mount means a code JoinInvite has cleared is not reused.
  const [pendingCode] = useState(() => readSession(SESSION_KEYS.pendingInviteCode));

  return (
    <div className="grid gap-4">
      {pendingCode && (
        <Alert>
          <AlertDescription>You opened an invite link. Review and accept it below.</AlertDescription>
        </Alert>
      )}
      <JoinInvite
        initialCode={pendingCode ?? undefined}
        autoPreview={Boolean(pendingCode)}
        email={email}
        showEntry
      />
    </div>
  );
}
```

- [ ] **Step 5 (agent): Run the tests to verify they pass, then both suites, typecheck, lint and the build**

```bash
(cd frontend && npx vitest run "src/app/(signed-in)/welcome/welcome.test.tsx" 2>&1 | grep -E "✓|×|stderr|Warning|act\(|Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Missing Suspense|useSearchParams|Error|/welcome|Generating static pages")
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:**
- `✓ |dom| src/app/(signed-in)/welcome/welcome.test.tsx (7 tests) <t>ms`, `Test Files  1 passed (1)`, `Tests  7 passed (7)`, and no `×`, `stderr`, `Warning` or `act(` lines (the `next/link` check from critique M18).
- `Test Files  34 passed (34)` and `Tests  220 passed (220)` (214 − 1 stub test + 7; no new file). `tsc --noEmit` and `eslint` print nothing beyond their banners.
- The build prints `✓ Generating static pages using <n> workers (<k>/<k>)` and the route line `└ ○ /welcome` (static; the last route in the table), and no `Missing Suspense boundary with useSearchParams` or `Error` line. A Suspense error means `useSearchParams` was moved out of `WelcomeTabs`; restore Step 4's file.
- `796 passed, 9 skipped in <t>s` (the backend is unchanged since Task 14).
- `git status --short` lists exactly (plus `?? .claude/`):

```
 M frontend/src/app/(signed-in)/welcome/page.tsx
 M frontend/src/app/(signed-in)/welcome/welcome.test.tsx
```

If the pending-code test fails with `Found multiple elements with the text: You opened an invite link…`, Task 14's `JoinInvite` renders the alert too: stop and ask (one of the two must go; the owner-visible copy appears once). If test 3 or 5 fails with `Found multiple elements with the text: Start a new church…`, the same applies to Task 16's form. If the time-zone test finds `America/New York` or the wrong zone, a stub was skipped and the form read the runner's zone.

- [ ] **Step 6 (agent): Commit**

```bash
git add "frontend/src/app/(signed-in)/welcome/page.tsx" "frontend/src/app/(signed-in)/welcome/welcome.test.tsx"
git status --short
git commit -m "Frontend: /welcome Join and Create tabs, replacing the 1a stub (S Flow A, Flow C; F §4.1)

The zero-church landing and the switcher's target: the welcome or
join-or-create heading, a link back to the active church, and Join /
Create tabs bound to ?tab= (router.replace, no scroll). The Join tab
shows the pending-invite alert and previews the stored code once; the
Create tab is CreateChurchForm. useSearchParams sits in Suspense for
the static build. Replaces the stub's one test with seven.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** after `git add`, `git status --short` shows `M  frontend/src/app/(signed-in)/welcome/page.tsx` and `M  frontend/src/app/(signed-in)/welcome/welcome.test.tsx` (plus `?? .claude/`); the commit prints `2 files changed, 255 insertions(+), 29 deletions(-)`; `git log --oneline -1` shows the new subject; the final `git status --short` lists only `?? .claude/`.

Tests after this task: backend `796 passed, 9 skipped` (unchanged); frontend `220 passed` (34 files).
### Task 18: The church switcher's "Join or create a church…" item (S Flow C; F §4.1, §4.9 item 4; AC12 item half; F-AC8; 1b clarification 31)

This task finishes the header's church menu. Under the "Your churches" radio list it adds a separator, then a plain menu item **"Join or create a church…"** that opens `/welcome` (S Flow C: "a separator, then **"Join or create a church…"** → `/welcome`"; F §4.1: "A user with one church sees the same menu"). `/welcome` already shows the has-church copy and the "← Back to {active church}" link (Task 17), so this is the only way in from a church page. The backend does not change.

Choices made here (none needs the owner):
- **Navigation is inside `ChurchSwitcher`.** It calls `useRouter().push("/welcome")`. `AppHeader`'s props and the `(church)` layout do not change: no `onJoinOrCreate` prop is threaded through (1b clarification 31). `useRouter` comes from `next/navigation`. That is the module `setup-dom.ts:20-27` mocks for every DOM test, so the test asserts on `testRouter.push` from `@/test/mocks`.
- **`push`, not `replace`.** Browser Back from `/welcome` returns to the church page the user left. This is one of the two pushed navigations 1b adds; the other is Task 17's back link. It is safe because Task 10's `endSignOut()` runs when `/login` mounts (1b clarification 21). The test checks that `replace` is not called.
- **The item closes the menu by default.** Base UI's `Menu.Item` defaults `closeOnClick` to true. Only the radio items need the explicit `closeOnClick` that 1a gave them. The test waits for the menu to disappear.
- **No tap-target sizing on the item.** It matches its radio siblings and the account menu's "Log out" (1a sized only the two triggers, F §4.8). The generated `dropdown-menu.tsx` is not edited (F §4.9).
- The 1a placeholder sentence in the component's doc comment ("Slice 1b adds a separator and …", `church-switcher.tsx:27`) is replaced with a description of the menu as built.

Verified before writing (throwaway worktree at `0295b37`, Vitest 3.2.7, Base UI as locked): the new test fails as quoted in Step 3, passes after Step 4, and the whole suite passed there (`Tests  127 passed (127)`, i.e. 126 + 1). `tsc --noEmit` and `eslint` are clean. Tasks 9–17 do not touch either file (Task 17's `/welcome` renders `AppHeader` without a switcher), so the edits below apply unchanged on top of Task 17.

**Files:**
- Modify: `frontend/src/components/app/church-switcher.tsx` (whole file replaced, 62 → 69 lines: imports, doc comment, `useRouter`, separator and item after the group)
- Test: `frontend/src/components/app/app-header.test.tsx` (imports at lines 1-6; one test inserted after line 43, the end of the first test: 4 → 5 tests; Vitest `dom` project)
- Unchanged on purpose: `frontend/src/components/app/app-header.tsx` (props unchanged), `frontend/src/app/(signed-in)/(church)/layout.tsx` (no prop plumbing, 1b clarification 31), `frontend/src/components/ui/dropdown-menu.tsx` (generated, F §4.9)

**Interfaces:**
- Consumes:
  - `useRouter` from `next/navigation` (`router.push(href: string, options?)` adds a history entry: `frontend/node_modules/next/dist/docs/01-app/03-api-reference/04-functions/use-router.md:44`). In DOM tests it returns `testRouter` (`frontend/src/test/mocks.ts:13-18`, `push: vi.fn()`, reset before each test by `resetTestMocks()`).
  - `DropdownMenuSeparator` (`frontend/src/components/ui/dropdown-menu.tsx:222-233`, Base UI `Menu.Separator`, `role="separator"`) and `DropdownMenuItem` (`:75-96`, Base UI `Menu.Item`, `role="menuitem"`, `closeOnClick` default true). Both are already exported (`:251-262`) and used by `account-menu.tsx:45-46`.
  - 1a's `ChurchSwitcher({ churches, activeId, onSelect })` (`church-switcher.tsx:18-22`, `:29`) and `AppHeader` (`app-header.tsx:7-13`, `:20`), unchanged.
- Produces:
  - `frontend/src/components/app/church-switcher.tsx`: `export function ChurchSwitcher({ churches, activeId, onSelect }: { churches: Church[]; activeId: string | null; onSelect: (id: string) => void }): JSX.Element`, with the same signature as before. The open menu (`role="menu"`) holds, in document order: the `role="group"` named "Your churches" with one `role="menuitemradio"` per church; one `role="separator"`; one `role="menuitem"` named exactly `Join or create a church…` (U+2026 ellipsis). Choosing it calls `router.push("/welcome")` once, never `onSelect`, and closes the menu.
  - Later users: manual check 7 (Task 19 writes it, Task 21 runs it: "As C: switcher → "Join or create a church…" → `/welcome` → create …"). 6b's owner-only items would go below this one.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -1
git diff --quiet 0295b37 -- frontend/src/components/app/church-switcher.tsx frontend/src/components/app/app-header.tsx frontend/src/components/app/app-header.test.tsx && echo "header files as at 0295b37"
grep -c "useRouter\|DropdownMenuSeparator" frontend/src/components/app/church-switcher.tsx
grep -c '^  it(' frontend/src/components/app/app-header.test.tsx
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** `git status --short` lists only `?? .claude/`, and the last commit is Task 17's. Then `header files as at 0295b37` (no earlier 1b task touched them). Then `0`, because the switcher has no router and no separator yet (`grep -c` also exits 1, which is fine). Then `4`, the four 1a tests. Then `Test Files  34 passed (34)` and `Tests  220 passed (220)`, which is Task 17's count with owner answer Q4 = yes. If the header files differ from `0295b37`, or either count differs, stop and ask: the replacement blocks below assume the 1a text.

- [ ] **Step 2 (agent): Write the failing test**

In `frontend/src/components/app/app-header.test.tsx`, replace the imports (lines 1-6):

```tsx
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/components/app/app-header";
import type { Church, Me } from "@/lib/church";
```

with:

```tsx
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AppHeader } from "@/components/app/app-header";
import type { Church, Me } from "@/lib/church";
import { testRouter } from "@/test/mocks";
```

Then replace the end of the first test (lines 42-43 before the import edit, 43-44 after it; the block occurs once):

```tsx
    expect(onSelectChurch).toHaveBeenCalledTimes(2);
  });
```

with:

```tsx
    expect(onSelectChurch).toHaveBeenCalledTimes(2);
  });

  it("offers Join or create a church… below the list with one church, and it opens /welcome", async () => {
    const onSelectChurch = vi.fn();
    render(
      <AppHeader
        user={pat}
        churches={[graceAdmin]}
        active={graceAdmin}
        onSelectChurch={onSelectChurch}
        onSignOut={vi.fn()}
      />,
    );
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Active church: Grace" }));
    const menu = await screen.findByRole("menu");
    const list = within(menu).getByRole("group", { name: "Your churches" });
    expect(within(list).getAllByRole("menuitemradio")).toHaveLength(1);
    const separator = within(menu).getByRole("separator");
    const item = within(menu).getByRole("menuitem", { name: "Join or create a church…" });
    // S Flow C order: the church list, a separator, then the item.
    expect(list.compareDocumentPosition(separator) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(separator.compareDocumentPosition(item) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await user.click(item);
    expect(testRouter.push).toHaveBeenCalledTimes(1);
    expect(testRouter.push).toHaveBeenCalledWith("/welcome");
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(onSelectChurch).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByRole("menu")).toBeNull());
  });
```

The test uses one church on purpose: F §4.1 says a user with one church sees the same menu. It is the case the Streamlit switcher hid ("only with ≥2 churches", S A5 row).

- [ ] **Step 3 (agent): Run the test to verify it fails**

```bash
(cd frontend && npx vitest run src/components/app/app-header.test.tsx 2>&1 | grep -E "✓|×|→|Test Files|Tests ")
```

**Expected:** the four 1a tests pass (`✓ AppHeader > lists same-name churches …`, `✓ … shows the user's name, email and role label …`, `✓ … calls onSignOut from Log out`, `✓ … shows the app name and no switcher …`). Then:

```
   × AppHeader > offers Join or create a church… below the list with one church, and it opens /welcome
     → Unable to find an accessible element with the role "separator"
```

and `Test Files  1 failed (1)`, `Tests  1 failed | 4 passed (5)`. The menu has no separator yet; the group and its single radio item are found, so the failure is at the separator lookup.

- [ ] **Step 4 (agent): Add the separator and the item to `frontend/src/components/app/church-switcher.tsx`**

Replace the whole file (62 lines) with:

```tsx
"use client";

import { ChevronsUpDownIcon } from "lucide-react";
import { useRouter } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { roleLabel, type Church } from "@/lib/church";
import { cn } from "@/lib/utils";

type Props = {
  churches: Church[];
  activeId: string | null;
  onSelect: (id: string) => void;
};

/**
 * The header's church menu (S Flow C, F §4.1, §4.9 item 4): a radio list keyed
 * and selected by id, each row showing the role so same-name churches differ,
 * then a separator and "Join or create a church…", which pushes `/welcome`
 * (1b clarification 31). A user with one church sees the same menu.
 */
export function ChurchSwitcher({ churches, activeId, onSelect }: Props) {
  const router = useRouter();
  const active = churches.find((c) => c.id === activeId) ?? null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={active ? `Active church: ${active.name}` : "Choose a church"}
        className={cn(
          buttonVariants({ variant: "ghost", size: "touch" }),
          "max-w-full justify-start px-2 font-semibold",
        )}
      >
        <span className="min-w-0 truncate">{active?.name ?? "Choose a church"}</span>
        <ChevronsUpDownIcon aria-hidden className="text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-auto min-w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Your churches</DropdownMenuLabel>
          <DropdownMenuRadioGroup
            value={activeId}
            onValueChange={(id: string) => onSelect(id)}
          >
            {churches.map((c) => (
              <DropdownMenuRadioItem key={c.id} value={c.id} label={c.name} closeOnClick>
                <span className="min-w-0 flex-1 truncate">{c.name}</span>{" "}
                <span className="text-xs text-muted-foreground">{roleLabel(c.role)}</span>
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push("/welcome")}>Join or create a church…</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

The only changes from 1a: the `useRouter` import, `DropdownMenuItem` and `DropdownMenuSeparator` in the import list, the rewritten doc comment, `const router = useRouter();`, and the two lines after `</DropdownMenuGroup>`. The separator and item sit outside the group, so the group's accessible name still covers only the churches (F §4.9: `DropdownMenuLabel` inside `DropdownMenuGroup`).

- [ ] **Step 5 (agent): Run the test to verify it passes, then the whole frontend and backend suites**

```bash
(cd frontend && npx vitest run src/components/app/app-header.test.tsx 2>&1 | grep -E "✓|×|stderr|Warning|Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `✓ |dom| src/components/app/app-header.test.tsx (5 tests)`, `Test Files  1 passed (1)`, `Tests  5 passed (5)`, with no `×`, `stderr` or `Warning` lines. Then `Test Files  34 passed (34)` and `Tests  221 passed (221)` (220 + 1; no new file). The `(church)` layout tests (`church-layout.test.tsx`), which open this menu and pick a radio item, still pass. `tsc --noEmit` and `eslint` print nothing beyond their banners. Then `796 passed, 9 skipped in <t>s`: the backend is unchanged since Task 14. `git status --short` lists exactly (plus `?? .claude/`):

```
 M frontend/src/components/app/app-header.test.tsx
 M frontend/src/components/app/church-switcher.tsx
```

If the new test fails at `testRouter.push` with 0 calls while the menu closes, the item was given `onSelect`/`onValueChange` instead of `onClick`. If it fails waiting for the menu to close, a `closeOnClick={false}` was added.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/app/church-switcher.tsx frontend/src/components/app/app-header.test.tsx
git status --short
git commit -m "Frontend: church switcher gains Join or create a church… (S Flow C; F §4.1, §4.9 item 4; F-AC8; 1b clarification 31)

Below the Your churches radio list the menu now has a separator and a
Join or create a church… item that pushes /welcome, so a user with one
or more churches can reach the Join and Create tabs from any church
page. The switcher calls useRouter itself: AppHeader's props and the
(church) layout are unchanged. The item closes the menu (Base UI
default). Back from /welcome returns to the church page; endSignOut on
/login keeps that safe after a sign-out (1b clarification 21).

Test: app-header.test.tsx, one church, the item follows the list and a
separator, pushes /welcome once, never calls replace or onSelect,
and closes the menu.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** before the commit, `git status --short` lists the two paths staged (`M ` in the first column) plus `?? .claude/`. Afterwards `<sha> Frontend: church switcher gains Join or create a church… (S Flow C; F §4.1, §4.9 item 4; F-AC8; 1b clarification 31)`, and `git status --short` lists only `?? .claude/`.

No OWNER step in this task: the deployed half of AC12 and F-AC8 is manual check 7 (written in Task 19, run in Task 21).

Tests after this task: backend `796 passed, 9 skipped` (unchanged); frontend `221 passed` (34 files).
### Task 19: Docs: the F §4.3 amendment and six F fixes, S's open items closed, manual checks 2–11 (F §4.3, §1.6, §2.3, §3.3, §6.1, §7.4; S Manual checks, Risks 1 and 9; owner answers 1, 2, 3 and 7; clarifications 11, 14, 33)

Docs only, in two TDD cycles. Cycle A records owner answer 1 in F: "Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6)", verbatim in the D14 row, the amendments-table §4.3 row and the §4.3 body. It deletes the auto-accept fallback text in F and S and applies owner answer 3's six docs-only F fixes: §7.4 `already_member`; §1.6 key scope without a church (1a final review T4-m1); §3.3 Railway UI; §6.1 liturgy-frozen; F:415 and F:1266 accept result and race handling (clarification 14); §4.3 step 2's signed-out copy. It also records the two §4.3 wording changes clarification 22 and S :481 imply: Join goes to `/` until slice 2, and the `(signed-in)` layout follows the stored path and clears it before following. S closes Risk 1, the Flow B note, the behavior change 4 row, the manual check 2 and AC10 parentheticals and the `/join` fallback-test sentence, and marks Risk 9 resolved (clarification 27). Cycle B appends S's manual checks 2–11 to `docs/manual-verification.md` → "## Slice 1" (clarification 11). Invites come from liturgy-frozen only (owner answer 2, clarification 33). Accounts are A, B and C, with unique throwaway names and the 5-per-24 h cap, Streamlit creates included. The checks record the seed timing and whether the account chooser appeared, and never an invite code. The preamble points to the "Slice 1b record" (owner answer 7) that Task 21's records PR creates. The "Slice 1b setup" and "Slice 1b regression pass" lines are plain paragraphs, not `- [ ] ` items, so the pinned checkbox count is exactly 13 (critique M11).

Two corrections to NC §C3, checked in the code, are built into the checklist below:
- **"1b Invite Test" is created in the new app, not in Streamlit.** Frozen Streamlit offers create only in its zero-church onboarding: `app.py:344-347` calls `render_onboarding` only when `require_active_church` returns None, and `render_church_switcher` (`app.py:244-261`) has no create entry. A, who already has a church, therefore creates it through the new app's "Join or create a church…" item (Task 18). The church then shows up in liturgy-frozen, where A is its owner and makes the invites.
- **Check 4 runs after check 6, and check 7 after check 4.** NC's order (7 before 4) leaves C as Owner of every church, so in check 7 "switching changes the role shown" could not be seen. In this order C joins "1b Invite Test" as a member in check 4, which still happens after C has churches (owner decision 9), and then in check 7 C creates a third church and switches between Member and Owner.

Line numbers are at `0295b37`. Tasks 1–18 change none of these four files (File Structure), so the numbers still hold when this task runs.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`: D14 row :42; amendments-table §4.3 row :63; five new rows after :77; §1.6 new bullet after :229; §2.3 item 3 :415; §3.3 Railway row :583; §4.3 steps 2–3 :727-728, open item :732-734, post-login bullet :740; §6.1 items 2 and 4 :1130, :1132; §7.4 rows :1258, :1266
- Modify: `docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`: Flow B note :121; behavior change 4 row :515; `/join` DOM-test bullet :600; manual check 2 :607; AC10 :631; Risk 1 :645; Risk 9 :653
- Modify: `docs/manual-verification.md`: "## Slice 1" preamble :74-78; the 1b setup, ten `(after 1b)` items and the regression paragraph appended after :82 (the end of the file, so "## Slice 1" stays the last `## ` heading)
- Test: `backend/tests/test_slice1_docs.py`: docstring :1-4; constants after :19; `test_manual_verification_has_the_slice_1_section` (:157-181) gets new needles and counts 3 → 13; new `test_foundations_records_the_join_tap_amendment` before `test_readme_documents_alembic_for_local_dev` (:184). File: 5 → 6 tests (+1).

**Interfaces:**
- Consumes (names quoted in the docs, as the earlier tasks define them): Task 3's `usecases.onboarding.InviteAccepted {church: ChurchSummary, already_member: bool, message: str}`; Task 5's `usecases.onboarding.accept_invite`, which raises `domain_errors.Rejected` with `details.reason`; Task 2's `repos.invites.claim(invite_id, user_id, now, *, session=None) -> bool` and `repos.memberships.ensure_membership(church_id, user_id, role, *, session=None) -> tuple[str, bool]` (over `db.upsert.insert_ignore`); Task 10's `/login?next=%2Fjoin&select_account=1` → `prompt: "select_account"`; Task 11's clear-before-follow in `(signed-in)/layout.tsx`; client copy from Tasks 14–18 (Global Constraints → Client copy): "You're invited", "Use a different Google account", "Join or create a church…", "Create a church", "Create church", "Created {name}. You're the owner.", "Joined {name}.", "You're already a member of {name}.", "← Back to {active church}", "This invite link is incomplete."; server messages "This invite has already been used.", "This invite was issued for a different email address.", "This invite has been revoked.", "Church name is required."; 1a's toast "You no longer have access to {name}." and account menu "Role: {role}".
- Produces:
  - In `backend/tests/test_slice1_docs.py`: `SPECS`, `FOUNDATIONS`, `SLICE_1_SPEC` (`pathlib.Path`) and `JOIN_TAP_APPROVAL: str = "Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6)"`; `test_foundations_records_the_join_tap_amendment() -> None`.
  - In `docs/manual-verification.md` → "## Slice 1": ten `- [ ] (after 1b) **N.** …` items (N = 2, 3, 5, 6, 4, 7, 8, 9, 10, 11), plus the pointer to `docs/ops-runbook.md` → "Slice 1b record" and to the `claude/slice-1b-records` PR.
- Later users: Task 20 (the PR body lists these amendments; its grep gates are unaffected); Task 21 (the OWNER runs the ten items and the records PR adds `### Slice 1b record` after `### Alembic stamping record (slice 1a)` in `docs/ops-runbook.md`).

Counts before this task: backend **796 passed, 9 skipped** (Task 14's count; Tasks 15–18 change no backend test); frontend **221 passed in 34 files** (Task 18, with Q4). After: backend **797 passed, 9 skipped**; frontend unchanged (no frontend file changes).

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py 2>&1 | tail -1
grep -c 'awaits owner sign-off (§4.3)\|pending owner sign-off before 1b\|Open item: owner sign-off required before 1b merges\|Sign in with Google to join"\|The root reads, clears and follows\|reason_code, message, church_id\|set to `/backend/railway.toml` by hand\|ping only `liturgy.streamlit.app`\|IntegrityError on the membership insert counts as success' docs/superpowers/specs/2026-09-25-migration-foundations-design.md
grep -c 'autoAccept\|Open, owner\|behavior change 4 fallback\|If the owner declines\|with the CLI until 6b\|^9\. \*\*Next 16' docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md
grep -rln 'autoAccept\|owner sign-off' docs | grep -v '/plans/'
```

**Expected:** `git status --short` prints only `?? .claude/`; `5 passed in …s`; `9` (one line per F edit anchor); `7` (S lines :121, :515, :600, :607, :631, :645, :653); the last command lists exactly the two spec files (F and S), so no other doc repeats the fallback. If any number differs, stop and ask the owner.

- [ ] **Step 2 (agent): Write the failing F/S test (cycle A)**

Apply these three replacements to `backend/tests/test_slice1_docs.py` (each `old` occurs exactly once).

`backend/tests/test_slice1_docs.py`, docstring. Replace:

````python
"""Slice 1a docs: the Alembic production runbook in backend/migrations/README.md,
the ops-runbook health-check lines, the README's Alembic notes and the manual
"Slice 1" checks (slice 1 spec → Production runbook, Local dev, Manual checks
item 1; F §3.3, §5.5).
````

with:

````python
"""Slice 1 docs: the Alembic production runbook in backend/migrations/README.md,
the ops-runbook health-check lines, the README's Alembic notes, the manual
"Slice 1" checks (slice 1 spec → Production runbook, Local dev, Manual checks
items 1–11; F §3.3, §5.5) and slice 1b's foundations amendments (F §4.3
preview then Join, approved 2026-09-26, and the six docs-only fixes of the
slice 1b plan's owner answer 3).
````

`backend/tests/test_slice1_docs.py`, constants. Replace:

````python
BACKUP_YML = ROOT / ".github" / "workflows" / "backup.yml"
````

with:

````python
BACKUP_YML = ROOT / ".github" / "workflows" / "backup.yml"
SPECS = ROOT / "docs" / "superpowers" / "specs"
FOUNDATIONS = SPECS / "2026-09-25-migration-foundations-design.md"
SLICE_1_SPEC = SPECS / "2026-09-25-slice-1-onboarding-design.md"
JOIN_TAP_APPROVAL = (
    "Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6)"
)
````

`backend/tests/test_slice1_docs.py`, new test. Replace:

````python
def test_readme_documents_alembic_for_local_dev():
````

with:

````python
def test_foundations_records_the_join_tap_amendment():
    # Slice 1b plan, owner answers 1 (behavior change 4 approved on 2026-09-26)
    # and 3 (six docs-only F fixes); the slice 1 spec closes its open items.
    text = _read(FOUNDATIONS)
    flat = _flat(text)
    d14 = _flat(next(line for line in text.splitlines() if line.startswith("| D14 |")))
    amendments = _section(text, "## Amendments from slice specs")
    rows_43 = [_flat(line) for line in amendments.splitlines() if line.startswith("| §4.3 |")]
    sign_in = _flat(_section(text, "### 4.3 Sign-in continuity"))
    assert JOIN_TAP_APPROVAL in d14
    assert len(rows_43) == 1 and JOIN_TAP_APPROVAL in rows_43[0]
    assert JOIN_TAP_APPROVAL in sign_in
    for gone in (
        "owner sign-off",
        "autoAccept",
        "Sign in with Google to join",
        "The root reads, clears and follows",
        "reason_code",
        "IntegrityError on the membership insert counts as success",
        "set to `/backend/railway.toml` by hand",
        "ping only `liturgy.streamlit.app`",
    ):
        assert gone not in flat, gone
    assert "Sign in with Google to see and accept your invite to Worship Service Builder." in sign_in
    assert "The `(signed-in)` layout reads the stored path, clears it, then follows it" in sign_in
    assert "The key scope has no church." in _flat(_section(text, "### 1.6 Idempotency"))
    assert "Config as Code is closed to this service" in _flat(
        _section(text, "### 3.3 How migrations run"))
    assert "https://liturgy-frozen.streamlit.app/" in _section(text, "### 6.1 The freeze (ops slice)")
    risks = _section(text, "### 7.4 Inventory §4 cross-cutting risks").splitlines()
    lookups = next(line for line in risks if line.startswith("| Global lookups exposed"))
    accept = next(line for line in risks if line.startswith("| Concurrent `accept_invite`"))
    assert "`already_member`" in lookups
    assert "`claim`" in accept and "`insert_ignore`" in accept
    slice_1 = _read(SLICE_1_SPEC)
    for gone in ("autoAccept", "behavior change 4 fallback", "If the owner declines", "Open, owner"):
        assert gone not in slice_1, gone
    assert "Resolved (owner, 2026-09-26)" in slice_1


def test_readme_documents_alembic_for_local_dev():
````

- [ ] **Step 3 (agent): Run it and see it fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py 2>&1 | grep -m1 '^E '
```

**Expected:** `FAILED backend/tests/test_slice1_docs.py::test_foundations_records_the_join_tap_amendment` and `1 failed, 5 passed in …s`; the `E` line is `E       AssertionError: assert 'Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6)' in '| D14 | Invite links | The frontend builds `https://<origin>/join?code=…` itself. `/join` is a public route that keep... tap awaits owner sign-off (§4.3). | Works on localhost and in production with no backend config (owner decision 6). |'` (D14 still says "awaits owner sign-off").

- [ ] **Step 4 (agent): Amend F (owner answers 1 and 3)**

Apply these fourteen replacements to `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`. Each `old` occurs exactly once, and replacing a substring leaves the rest of its line as it is. The first three are the §4.3 approval (answer 1, dated 2026-09-26) and the amendments-table index. The other rows are dated 2026-09-28, the day the owner accepted answer 3, in the table's existing `*(date, owner, slice)*` form (as 1a's §1.5 row).

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, D14 row (:42). Replace:

````markdown
Whether joining then needs an explicit **Join** tap awaits owner sign-off (§4.3).
````

with:

````markdown
Joining then takes a preview and an explicit **Join** tap (§4.3): Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6).
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, amendments-table §4.3 row (:63). Replace:

````markdown
| §4.3 | Preview-then-**Join** on `/join` is **pending owner sign-off before 1b** because it departs from decision 6's wording. The auto-accept fallback is specified. | 1 (resolution) |
````

with:

````markdown
| §4.3 | *(2026-09-26, owner, slice 1b)* Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6): `/join` shows a preview and joins only on an explicit **Join** tap; the auto-accept fallback is withdrawn. *(2026-09-28, slice 1b)* Join goes to `/` until slice 2 redirects `/` to `/builder`; the `(signed-in)` layout, not the root, follows the stored post-login path and clears it before following; step 2 uses slice 1's signed-out copy. | 1 (resolution), 1b |
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, new amendment rows after the last row (:77). Replace:

````markdown
reaches only the new app. | PR #4, PR #8, 4 |
````

with:

````markdown
reaches only the new app. | PR #4, PR #8, 4 |
| §1.6 | *(2026-09-28, owner, slice 1b)* The store key `(user_id, method, route template, key)` has no church. That is right for the user-scoped `POST /churches`; 5a `POST /services`, 6b `POST /invites` and 5b `POST /bulletin-emails` must add the resolved church id to the scope or hash it into the body (1a final review, T4-m1). | 1b |
| §2.3 | *(2026-09-28, owner, slice 1b)* Item 3's example: `usecases.onboarding.accept_invite` returns a typed `InviteAccepted` (`church`, `already_member`, `message`) and raises `Rejected` with `details.reason`, instead of a UI-shaped dict. | 1b |
| §3.3 | *(2026-09-28, owner, slice 1b)* Railway's Config as Code is closed to this service: the Pre-deploy Command and the Healthcheck Path are set in the Railway UI, and `backend/railway.toml` only records them. | 1a (record), 1b |
| §6.1 | *(2026-09-28, owner, slice 1b)* Production Streamlit is https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`) since 2026-09-26; `liturgy` and `liturgy-next` are deleted, `keep-awake` pings liturgy-frozen, and item 6's contingency is not in effect. | ops (record), 1b |
| §7.4 | *(2026-09-28, owner, slice 1b)* The invite preview also returns `already_member`. Concurrent accepts: `invites.claim` (a conditional UPDATE) stamps a single-use invite once and `memberships.ensure_membership` inserts with `insert_ignore`, instead of treating an IntegrityError as success; Postgres race tests cover both. | 1b |
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §1.6 church scope (after :229). Replace:

````markdown
  - This is acceptable because there is one uvicorn worker. If `--workers` ever exceeds 1, move the store to a Postgres table first.
````

with:

````markdown
  - This is acceptable because there is one uvicorn worker. If `--workers` ever exceeds 1, move the store to a Postgres table first.
  - **Church scope** (*amendment 2026-09-28, slice 1b*). The key scope has no church. That is right for `POST /churches`, which is user-scoped. A church-scoped route (5a `POST /services`, 6b `POST /invites`, 5b `POST /bulletin-emails`) must add the resolved church id to the scope, or hash it into the body, so that a key sent to two churches never replays one church's answer to the other.
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §2.3 item 3 (:415). Replace:

````markdown
For example: `accept_invite` returns `{ok, reason_code, message, church_id}`;
````

with:

````markdown
For example: `usecases.onboarding.accept_invite` returns a typed `InviteAccepted` (`church`, `already_member`, `message`) and raises `Rejected` with `details.reason` (*amendment 2026-09-28, slice 1b*);
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §3.3 Railway row (:583). Replace:

````markdown
Railway does not look for the file under the service root (`/backend`), so the service's Config-as-code path is set to `/backend/railway.toml` by hand (slice 1 runbook).
````

with:

````markdown
*(Amendment 2026-09-28, slice 1b.)* Railway's Config as Code is closed to this service (services that never used it cannot opt in), so Railway never reads the file: the same Pre-deploy Command and Healthcheck Path are set in the Railway UI (Settings → Deploy), and the file only records them (ops runbook → Alembic stamping record (slice 1a), step 7).
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §4.3 step 2 (:727). Replace:

````markdown
  2. Signed out: the page shows "Sign in with Google to join" and sends the user to `/login?next=/join`.
````

with:

````markdown
  2. Signed out: the page shows "Sign in with Google to see and accept your invite to Worship Service Builder." and sends the user to `/login?next=/join`.
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §4.3 step 3 (:728). Replace:

````markdown
selects the new church, and goes to `/builder`.
````

with:

````markdown
selects the new church, and goes to `/` (slice 2 makes `/` redirect to `/builder`).
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §4.3 open item (:732-734). Replace:

````markdown
  **Open item: owner sign-off required before 1b merges.** Step 3's explicit **Join** tap departs from the wording of owner decision 6 ("opening the link (signing in if needed) joins the church"). It is proposed as a safeguard, so that a forwarded or mistaken bearer link never joins anyone silently. This is not settled until the owner answers:
  - **If the owner approves,** record the approval here, and this step becomes an amendment to decision 6.
  - **If the owner declines,** step 3 becomes: signed in, `/join` calls `POST /invites/accept` right after sign-in, with no preview and no tap (slice 1's `JoinInvite autoAccept` fallback), then clears the key, invalidates `["me"]`, selects the church and goes to `/builder`. The preview remains only for a code pasted on the Welcome tab. The rejection and email-mismatch cards are unchanged. Slice 1 then updates Flow B, behavior change 4 and the `/join` DOM tests to match.
````

with:

````markdown
  **Amendment to owner decision 6.** Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6). Step 3's explicit **Join** tap departs from the wording of decision 6 ("opening the link (signing in if needed) joins the church") as a safeguard, so that a forwarded or mistaken bearer link never joins anyone silently. There is no auto-accept fallback: a code pasted on the Welcome tab gets the same preview and tap.
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §4.3 post-login path (:740). Replace:

````markdown
  - `/auth/callback` still redirects to `/`. The root reads, clears and follows the stored path.
````

with:

````markdown
  - `/auth/callback` still redirects to `/`. The `(signed-in)` layout reads the stored path, clears it, then follows it (*amendment 2026-09-28, slice 1b*: not the root, because the `(church)` layout would first send a zero-church user to `/welcome`; clearing before following keeps a path with no route yet from redirecting every visit).
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §6.1 item 2 (:1130). Replace:

````markdown
   - The tester's URL stays the same.
````

with:

````markdown
   - The tester's URL stays the same.
   - *(Amendment 2026-09-28, slice 1b.)* In the event, production moved to https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`) on 2026-09-26 and stays there; `liturgy` and `liturgy-next` are deleted, so the tester's URL changed once (ops runbook → Streamlit apps). Item 6's contingency is not in effect.
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §6.1 item 4 (:1132). Replace:

````markdown
4. **Keep-awake.** Update `keep-awake.yml` to ping only `liturgy.streamlit.app`.
````

with:

````markdown
4. **Keep-awake.** Update `keep-awake.yml` to ping only the production Streamlit app, https://liturgy-frozen.streamlit.app/ (*amendment 2026-09-28, slice 1b*).
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §7.4 global lookups row (:1258). Replace:

````markdown
| 1 (preview returns only church name, role, expiry, email-bound), 6b |
````

with:

````markdown
| 1 (preview returns only church name, role, expiry, email-bound and `already_member`: *amendment 2026-09-28, slice 1b*), 6b |
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §7.4 concurrent accept row (:1266). Replace:

````markdown
| 1 | IntegrityError on the membership insert counts as success |
````

with:

````markdown
| 1 | `claim` (a conditional UPDATE) stamps a single-use invite once, and `ensure_membership` inserts with `insert_ignore`, so a concurrent accept never reaches the primary key; Postgres race tests (*amendment 2026-09-28, slice 1b*) |
````

- [ ] **Step 5 (agent): Close S's open items**

Apply these eight replacements to `docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md` (each `old` occurs exactly once). Manual check 2's invite source becomes liturgy-frozen, because there is no invite CLI (owner answer 2, clarification 33).

`docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`, Flow B note (:121). Replace:

````markdown
; see behavior change 4. The owner's answer is needed **before 1b starts**: if approved, F§4.3 records it as an amendment to decision 6 and this flow stands; if declined, F§4.3 changes to auto-accept after sign-in and steps 4–5 become the `autoAccept` flow in behavior change 4.
````

with:

````markdown
; see behavior change 4. Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6), and F§4.3 records it.
````

`docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`, behavior change 4 row (:515). Replace:

````markdown
and follows F§4.3; **needs the owner's answer before 1b starts.** If approved, F§4.3 records it as an amendment to decision 6. If declined, F§4.3 changes to auto-accept after sign-in and this slice adopts the fallback: `/join` calls `POST /invites/accept` right after sign-in (a `JoinInvite autoAccept` prop, a "Joining…" skeleton card) and goes straight to Flow B step 5's selection, toast and `/`; Flow B step 4 (the preview card) then applies only to the Welcome tab's pasted code, and the rejection and email-mismatch cards are unchanged. The `/join` DOM tests, acceptance criterion 10 and manual check 2 change with it (§Testing). |
````

with:

````markdown
and follows F§4.3. Approved by the owner on 2026-09-26; F§4.3 records it as an amendment to decision 6. |
````

`docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`, `/join` DOM-test bullet (:600). Replace:

````markdown
 *If the owner declines the preview step (behavior change 4):* signed in → the accept request `{code}` is sent on mount with no preview request and no Join tap, then the same selection, toasts ("Joined Grace." / "You're already a member of Grace.") and `/`; rejections and `email_mismatch` as above; the preview-card cases move to the `/welcome` Join-tab tests.
````

with nothing: the new string is empty (the deleted text includes its leading space).

`docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`, manual check 2 (:607), invite source. Replace:

````markdown
(create it in Streamlit or with the CLI until 6b)
````

with:

````markdown
(create it in liturgy-frozen, Settings → Invites, until 6b; there is no invite CLI)
````

`docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`, manual check 2 (:607), fallback. Replace:

````markdown
 (With the behavior change 4 fallback: signing in joins directly, with no preview or tap.)
````

with nothing: the new string is empty (the deleted text includes its leading space).

`docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`, acceptance criterion 10 (:631). Replace:

````markdown
 (with the behavior change 4 fallback, signing in joins without the tap)
````

with nothing: the new string is empty (the deleted text includes its leading space).

`docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`, Risk 1 (:645). Replace:

````markdown
1. **Open, owner: preview-then-Join vs decision 6's "opening the link joins".** Behavior change 4 keeps an explicit **Join** tap (F§4.3) as a safeguard for bearer codes. The owner's answer is needed before 1b starts. If approved, F§4.3 records it as an amendment to decision 6. If declined, F§4.3 changes to auto-accept after sign-in and this slice adopts the `JoinInvite autoAccept` fallback, updating Flow B, behavior change 4 and the `/join` DOM tests as described there (a small change to `JoinInvite`).
````

with:

````markdown
1. **Resolved (owner, 2026-09-26): preview-then-Join vs decision 6's "opening the link joins".** Behavior change 4 keeps an explicit **Join** tap (F§4.3) as a safeguard for bearer codes. Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6); F§4.3 records it. The auto-accept fallback is not built.
````

`docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`, Risk 9 (:653). Replace:

````markdown
9. **Next 16 `history.replaceState`.** The code capture relies on native `replaceState` integrating with the App Router; verify against the bundled Next docs before building `/join`. The fallback is `router.replace("/join", { scroll: false })` after capture.
````

with:

````markdown
9. **Resolved: Next 16 `history.replaceState`.** The bundled Next docs (`01-app/01-getting-started/04-linking-and-navigating.md`) say native `window.history.replaceState` integrates with the App Router and `useSearchParams`, so `/join` uses it and needs no `router.replace` fallback. After the capture `useSearchParams().get("code")` is null, so `/join` reads the code once (effect → sessionStorage → state).
````

- [ ] **Step 6 (agent): Run it and see it pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py 2>&1 | tail -1
grep -rln 'autoAccept\|owner sign-off' docs | grep -v '/plans/'
git diff --stat
```

**Expected:** `6 passed in …s`; the `grep` prints nothing (exit 1); `git diff --stat` lists only `backend/tests/test_slice1_docs.py`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` and `docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md`.

- [ ] **Step 7 (agent): Commit cycle A**

```bash
git add docs/superpowers/specs/2026-09-25-migration-foundations-design.md docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md backend/tests/test_slice1_docs.py
git commit -m "Specs: record preview-then-Join (approved 2026-09-26) and six F fixes (F §4.3, §1.6, §2.3, §3.3, §6.1, §7.4; S Risks 1, 9)" -m "F D14, the amendments-table row and the §4.3 body record the owner's approval as an amendment to decision 6 and drop the auto-accept fallback. Join goes to / until slice 2, and the (signed-in) layout follows the stored path, clearing it first. §7.4 adds already_member and replaces the IntegrityError rule with claim + insert_ignore; §2.3 names the typed InviteAccepted; §1.6 notes that the key scope has no church; §3.3 moves the Railway settings to the UI; §6.1 names liturgy-frozen. S closes Risk 1, the Flow B note, behavior change 4, the manual check 2 and AC10 parentheticals and the fallback test sentence; Risk 9 is resolved by the bundled Next docs." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, three files changed.

- [ ] **Step 8 (agent): Write the failing manual-checklist test (cycle B)**

Apply this replacement to `backend/tests/test_slice1_docs.py` (in `test_manual_verification_has_the_slice_1_section`; the `old` occurs exactly once).

`backend/tests/test_slice1_docs.py`, manual-section needles and counts. Replace:

````python
        "https://liturgy-frozen.streamlit.app",
        "Create invite",
    ):
        assert needle in section, needle
    assert "liturgy-next" not in section
    assert section.count("- [ ] ") == 3
    assert "- [x]" not in section
````

with:

````python
        "https://liturgy-frozen.streamlit.app",
        "Create invite",
        # Slice 1b: manual checks 2-11 (plan owner answers 2 and 7).
        "Slice 1b record",
        "claude/slice-1b-records",
        "Settings → Invites",
        "5 churches in 24 hours",
        "Join or create a church…",
        "Joined 1b Invite Test.",
        "This invite has already been used.",
        "Church name is required.",
        "Use a different Google account",
        "select_account",
        "You no longer have access to 1b Invite Test.",
        "This invite has been revoked.",
    ):
        assert needle in section, needle
    assert "liturgy-next" not in section
    assert section.count("- [ ] ") == 13
    assert section.count("- [ ] (after 1a) ") == 3
    assert section.count("- [ ] (after 1b) ") == 10
    assert "- [x]" not in section
````

- [ ] **Step 9 (agent): Run it and see it fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py 2>&1 | grep -m1 '^E '
```

**Expected:** `FAILED backend/tests/test_slice1_docs.py::test_manual_verification_has_the_slice_1_section` and `1 failed, 5 passed in …s`; the `E` line is `E           AssertionError: Slice 1b record` (the first new needle; the preamble does not name the 1b record yet).

- [ ] **Step 10 (agent): Write the manual checks**

Apply these two replacements to `docs/manual-verification.md`. The first `old` is lines :74-78 of the "## Slice 1" preamble. The second is the tail of the file's last line (:82, 1a's Streamlit smoke item, which ends with "then revoke that invite." and a newline); everything after it is appended. Keep each `- [ ] ` item on one line, as the 1a items are. The test compares whitespace-collapsed text and counts `- [ ] (after 1b) `. Placeholders such as `<code>`, "C's email" and "B's email" stay as written: the owner fills them in only in the browser, never in a record.

`docs/manual-verification.md`, "## Slice 1" preamble (:74-78). Replace:

````markdown
https://liturgy-frozen.streamlit.app, the production Streamlit app. Record
each result, with its date, in `docs/ops-runbook.md` → Supabase lockdown
record → "Alembic stamping record (slice 1a)". The items marked "(after 1a)"
come from `backend/migrations/README.md` → Production runbook; slice 1b
appends its own items here.
````

with:

````markdown
https://liturgy-frozen.streamlit.app, the production Streamlit app. Record
each result, with its date, in `docs/ops-runbook.md`: the items marked
"(after 1a)" under Supabase lockdown record → "Alembic stamping record (slice
1a)", and the items marked "(after 1b)" under "Slice 1b record", the section
after it, which the docs-only `claude/slice-1b-records` PR fills. The items
marked "(after 1a)" come from `backend/migrations/README.md` → Production
runbook. The items marked "(after 1b)" are the slice 1 spec's manual checks
2–11 in the order they run: check 4 comes after checks 5 and 6, so that C
already has churches when it joins (owner decision 9), and check 7 after check
4, so that C can switch between Member and Owner. Never record an invite
code, an invite link or an email address.
````

`docs/manual-verification.md`, end of the file (:82): 1b setup, ten items, regression pass. Replace:

````markdown
then revoke that invite.
````

with:

````markdown
then revoke that invite.

Slice 1b setup. Accounts: **A** is the owner's own Google account; **B** and
**C** are two other Google accounts that belong to no church before these
checks (check 8 needs "1b Invite Test" to be B's only church).
Every invite is made in liturgy-frozen: Settings → Invites → **Create
invite**, with its Role (member or admin) and "Bind to email (optional)"; the
app shows the code once. Streamlit invites are single-use in the new app
(`reusable = false`). Build the link by hand as
`https://worship-service-builder.vercel.app/join?code=<code>`, and never put a
code into a record or a chat. Use throwaway churches only, never the tester's,
each with a name no church has yet (frozen Streamlit's switcher keys churches
by name; add a suffix if a name is taken). Each account may create at most 5
churches in 24 hours, soft-deleted churches and churches created in Streamlit
included; these checks create 1 as A and 3 as C. Start as A in the new app:
church switcher → "Join or create a church…" → **Create a church** → Church
name "1b Invite Test" → **Create church** (frozen Streamlit offers
onboarding only to an account with no church). Then in liturgy-frozen as A:
sidebar Church → "1b Invite Test" → Settings → Invites → **Create invite**
(Role member, no email) → build the link.

- [ ] (after 1b) **2.** In a private window, signed out, open the link: the address bar shows `/join` and the "You're invited" card appears. **Sign in with Google** as B → back on `/join`; the preview shows "1b Invite Test", "You're invited to join as a member." and "Invite expires …". **Join 1b Invite Test** → home with "1b Invite Test" active and the toast "Joined 1b Invite Test.". In liturgy-frozen as A, the invite is gone from Settings → Invites (the list hides accepted invites).
- [ ] (after 1b) **3.** In a second browser profile, open the same link and sign in with Google as C → "This invite has already been used." and "Ask for a new invite link."; **Go to home** → `/welcome` (C has no church). In B's window, open the link again → "You're already a member of 1b Invite Test." with no role line; **Open 1b Invite Test** → home with it active and the toast "You're already a member of 1b Invite Test.".
- [ ] (after 1b) **5.** As C on `/welcome`, with DevTools → Network open: **Create a church** → Church name "1b Test C", Time zone left at its default (the browser's zone, preselected) → **Create church** → the toast "Created 1b Test C. You're the owner." and home with "1b Test C" active and "Role: Owner" in the account menu. Record the `churches` request's Timing → "Waiting for server response" (S Risk 3; above 5 s, seeding moves to `INSERT … SELECT` in a follow-up). In the Supabase SQL Editor (read-only): `select (select count(*) from hymn_catalog) as catalog, (select count(*) from hymns h join churches c on c.id = h.church_id where c.name = '1b Test C') as seeded;` → the two numbers are equal.
- [ ] (after 1b) **6.** As C: church switcher → "Join or create a church…" → **Create a church**, with DevTools → Network throttling "Slow 4G". Leave the name blank and tap **Create church** → "Church name is required." under the field and no `churches` request in the Network panel. Enter "1b Test C2" and double-tap **Create church** → exactly one "1b Test C2" in the church menu. Set throttling back to "No throttling".
- [ ] (after 1b) **4.** In liturgy-frozen as A: sidebar Church → "1b Invite Test" → Settings → Invites → **Create invite** with Role member and "Bind to email (optional)" set to C's email → build its link. Open it in B's window (signed in as B) → "This invite was issued for a different email address." and "You're signed in as" with B's email. **Use a different Google account** → Google's account chooser appears (the app asks for it with `prompt=select_account`, S Risk 8; record whether it appeared, since the card has a fallback line if it does not) → choose C → back on `/join` → the preview with "This invite is for" and C's email → **Join 1b Invite Test** → the toast "Joined 1b Invite Test.". C already had churches (owner decision 9).
- [ ] (after 1b) **7.** As C (in "1b Test C", "1b Test C2" and "1b Invite Test"): church switcher → "Join or create a church…" → `/welcome` shows "← Back to" the active church → **Create a church** → "1b Test C3" → the church menu lists all four; switching between "1b Invite Test" and "1b Test C3" changes the role shown (Member, Owner). C has now created 3 churches in 24 hours.
- [ ] (after 1b) **8.** In a new private window, sign in as B and make "1b Invite Test" active. In liturgy-frozen as A: sidebar Church → "1b Invite Test" → Settings → Members → **Remove** next to B. B refocuses the tab → the toast "You no longer have access to 1b Invite Test." and B falls back to another church, or to `/welcome` if B has none.
- [ ] (after 1b) **9.** As B on `/welcome` (church switcher → "Join or create a church…" if B still has a church) → account menu → **Log out** → `/login`. B's session on a second device (a phone), signed in beforehand, stays signed in (`scope: "local"`).
- [ ] (after 1b) **10.** At 375 px: no horizontal scroll on `/welcome` (both tabs), `/join` (the "You're invited", preview and rejected cards, and https://worship-service-builder.vercel.app/join with no code for "This invite link is incomplete.") and home; inputs do not zoom on iOS (font size ≥ 16 px); tap targets ≥ 44 px.
- [ ] (after 1b) **11.** Streamlit smoke on https://liturgy-frozen.streamlit.app (F §6.3): sign in, the church and hymnal load, a saved service loads, Settings opens. As C there: "1b Test C" is in the sidebar Church list and its hymnal loads. As A: sidebar Church → "1b Invite Test" → Settings → Invites → **Create invite** (Role member, no email), then Settings → Danger zone → type "1b Invite Test" → **Delete church** (a soft delete that also revokes its invites); open that invite's link in the new app as C → "This invite has been revoked." (revoked is checked before church_unavailable).

Slice 1b regression pass (F §5.5), after the items above: sign in, switch
church, open home (1b ships no nav items). Optional clean-up: as C in
liturgy-frozen, Settings → Danger zone deletes "1b Test C", "1b Test C2" and
"1b Test C3" (soft deletes; they still count toward C's cap for 24 hours).
````

- [ ] **Step 11 (agent): Run the docs tests, the whole backend suite and the owner-marker check**

```bash
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
grep -c '^- \[ \] (after 1b) ' docs/manual-verification.md
grep -n '^## ' docs/manual-verification.md | tail -1
git diff --stat
```

**Expected:** `89 passed in …s` (`test_slice1_docs.py` 6, plus the unchanged `test_docs.py` and `test_ops_workflows.py`); `797 passed, 9 skipped in …s`; `4`; `10`; `69:## Slice 1`; `git diff --stat` lists only `backend/tests/test_slice1_docs.py` and `docs/manual-verification.md`. The frontend is not rerun, because no frontend file changed: it stays at `221 passed` in 34 files. If the backend count is not 797 + 9 skipped, stop and ask the owner.

- [ ] **Step 12 (agent): Commit cycle B**

```bash
git add docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -m "Docs: slice 1b manual checks 2-11 with liturgy-frozen invites (S Manual checks; owner answers 2, 7)" -m "Ten (after 1b) items under ## Slice 1 in run order (4 after 6, so C has churches and 7 can show Member vs Owner), plus a setup and a regression paragraph with no checkbox. Accounts A/B/C, unique throwaway names, the 5-per-24h cap counting Streamlit creates, the seed timing and whether Google's account chooser appeared. The preamble sends 1b results to the Slice 1b record in docs/ops-runbook.md (records PR claude/slice-1b-records) and forbids recording codes, links or emails. \"1b Invite Test\" is created in the new app, because frozen Streamlit only offers create to an account with no church." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, two files changed. Cumulative after Task 19: backend `797 passed, 9 skipped`; frontend `221 passed` in 34 files.
### Task 20: Whole-branch verification and the slice 1b pull request (owner's yes before the push and before ready) (S Testing, Risks 3; AC16 grep gates; owner decision 5; owner answers 5, 6; 1b clarifications 34, 37, 41)

The whole branch is checked in one place before anyone reviews it: both suites, the Postgres marker count, types, lint, the frontend build (Suspense and `metadata` mistakes only show in `next build`), the two generated API files, the AC16 greps and the other acceptance gates, and the exact list of changed paths. Then, on the owner's yes, the agent pushes the Tasks 9–19 commits to the draft PR that Task 8 opened, waits for CI, copies the final run's Postgres seed timing into a new PR body (clarification 41), retitles the PR and marks it ready for review. Merging is not part of this task (Task 21, its own yes).

`origin/main` may have moved since the branch was cut from `0295b37`. Step 1 merges it if the branch is behind, and every later step runs on the merged tree.

Below, `<scratch>` is the absolute path of the session's scratchpad directory (any empty temp directory will do); write it out literally in each command. `<N>` is the draft PR's number from Task 8, Step 7. Every `gh` command uses `-R bbrown62450/church`.

**Files:** none changed (the plan is already the branch's first commit). A local or CI failure is fixed in the owning task's files (Step 14), never here.

**Interfaces:**
- Consumes:
  - Everything from Tasks 1–19, in particular:
    - the draft PR `<N>` on `claude/slice-1b-plan` (Task 8, Step 7; title `Draft: Slice 1b onboarding: create a church, join by invite (CI Postgres checkpoint)`);
    - the CI line `UserWarning: hymn seed: 700 rows in <ms> ms` in the `backend-postgres` job's "warnings summary" (Task 8's `test_create_church_700_row_catalog_under_3s`; clarification 41);
    - `backend/scripts/export_openapi.py` (prints `Wrote <path>`) and `npm run gen:api` (1a Tasks 13 and 15);
    - `backend/tests/test_route_guards.py::USER_SCOPED` (Tasks 6 and 7), `db.engine._engine_kwargs(url: str) -> dict` (Task 1), the five log calls in `backend/usecases/onboarding.py` (Tasks 3–5);
    - the AC16 port tables: Task 3 (`test_create_church_seeds_catalog_with_identical_values`), Task 5 (`test_accept_captured_invite_joins_as_member` and the `test_invites_repo.py` table), Task 14 (the three `(port: …)` tests in `join-invite.test.tsx`).
  - CI (`.github/workflows/ci.yml`, unchanged by 1b): jobs `backend` (`python -m pytest -q`), `backend-postgres` (steps `Migrate the empty database to head`, `The models match the migrated schema`, `Every revision downgrades`, `Migrate to head again`, `Identity smoke (ops-2)`, `Postgres-only tests`), `frontend` (lint, typecheck, `API types match the OpenAPI snapshot (F §5.4)`, test, build). `pull_request` uses the default activity types, so marking the PR ready does not rerun CI.
- Produces:
  - PR `<N>` (`claude/slice-1b-plan` → `main`), titled `Slice 1b onboarding: create a church, join by invite`, not a draft, CI green on the branch head, its body ending with the `Tests:` line and the 🤖 line, and holding the line `Seed timing (S Risk 3): hymn seed: 700 rows in <ms> ms on CI Postgres (the whole `POST /churches` round trip; backend-postgres, run <run id>); budget 3 s in CI, 5 s in production.` Later users: Task 21 (pre-merge gate, merge, the `### Slice 1b record` copies the CI timing next to the production one).

- [ ] **Step 1: Bring the branch up to date with `origin/main` (agent)**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline -1 origin/main
git log --oneline origin/main..HEAD | tail -1
```

**Expected,** in order: `?? .claude/`; the fetch prints nothing or only updated refs; `0`; `0295b37 Merge pull request #17 from bbrown62450/claude/slice-1a-records` (or a later merge the owner made); the branch's oldest commit, `<sha> Plan: slice 1b onboarding (F, S slice 1; owner answers 2026-09-28)`.
- If the count is not `0`: `git merge origin/main -m "Merge origin/main into claude/slice-1b-plan (Task 20)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. On a conflict, run `git merge --abort`, stop and tell the owner which files conflict (dated records on `main` are never edited by a merge resolution the owner has not seen). Without a conflict, continue: Steps 2–7 run on the merged tree. If the merge brought new tests, the Step 2 and Step 3 totals differ by exactly those; name them in the Step 8 message. Any other difference: stop and ask.
- If `git status --short` shows anything besides `?? .claude/`, stop: commit it in its owning task or ask the owner.

- [ ] **Step 2: Run the backend suite and the Postgres marker count (agent)**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q -m postgres | tail -1
```

**Expected:** `797 passed, 9 skipped in <t>s` (baseline 697 passed, 5 skipped; after Tasks 1–7: 705, 717, 728, 746, 761, 775, 799 passed; Task 8 adds four skips; Task 14 deletes the last three Streamlit tests → 796; Task 19 adds one → 797); then `9 skipped, 797 deselected in <t>s` (exactly nine tests carry the marker: 1a's five and Task 8's four; no `TEST_DATABASE_URL` here). Any other number: stop and find the task whose count drifted (each task's last run step states its cumulative total).

- [ ] **Step 3: Run the frontend tests, types and lint (agent)**

```bash
(cd frontend && npm test && npm run typecheck && npm run lint)
```

**Expected:** Vitest's summary ` Test Files  34 passed (34)` and `      Tests  221 passed (221)` (126 in 23 files at `0295b37`; +17 Task 9, +9 Task 10, +5 Task 11, +6 Task 12, +8 Task 13, +21 Task 14, +12 Task 15, +10 Task 16, +6 Task 17 (7 new, the stub test replaced), +1 Task 18; 11 new test files); no `stderr` block with `act(` or `Warning:`; `tsc --noEmit` prints nothing; `eslint` prints nothing. The command exits 0.

- [ ] **Step 4: Build the frontend with CI's placeholder environment (agent)**

```bash
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build)
(cd frontend && node -e 'const m = require("./.next/app-path-routes-manifest.json"); console.log(Object.values(m).sort().join(" "))')
(cd frontend && test -f .next/server/app/join.html && grep -oE '<title>[^<]*</title>|<meta name="(robots|referrer)" content="[^"]*"' .next/server/app/join.html || echo "join.html not prerendered")
```

**Expected:** the build prints `✓ Compiled successfully`, runs `tsc`, generates the static pages and ends with its route table, with no `Error:` line (in particular no "useSearchParams() should be wrapped in a suspense boundary", no "You are attempting to export "metadata" from a component marked with "use client"" and no "two parallel pages that resolve to the same path"); then exactly:

```
/ /_global-error /_not-found /auth/callback /favicon.ico /join /login /welcome
```

(1a's seven routes plus `/join`, Task 15); then either these three lines in any order:

```
<title>Join a church</title>
<meta name="robots" content="noindex, nofollow"
<meta name="referrer" content="no-referrer"
```

or `join.html not prerendered` when the route table marks `/join` as dynamic (`ƒ`); Task 15's `join.test.tsx` already checks the `metadata` export, so only a missing or different tag in a prerendered `join.html` is a failure (Task 15). The build downloads the Geist fonts through `next/font/google`; if it fails only with `Failed to fetch` for a font (no network), say so in the Step 8 message and rely on CI's `frontend` job, which runs the same build (Step 11 checks it).

- [ ] **Step 5: Check that the generated files match the code (agent)**

```bash
.venv/bin/python backend/scripts/export_openapi.py && git diff --exit-code --stat frontend/src/lib/api/openapi.json; echo "openapi diff exit $?"
(cd frontend && npm run gen:api) && git diff --exit-code --stat frontend/src/lib/api/schema.d.ts; echo "schema diff exit $?"
grep -cE '"/(churches|invites/preview|invites/accept)"' frontend/src/lib/api/openapi.json
git status --short
```

**Expected:** `Wrote /Users/…/frontend/src/lib/api/openapi.json` and `openapi diff exit 0`; openapi-typescript's `🚀 src/lib/api/openapi.json → src/lib/api/schema.d.ts` line and `schema diff exit 0`; `3` (the three 1b paths, one key each); then only `?? .claude/`. A non-zero diff exit means an API change was committed without regenerating: run the same two commands, commit both generated files in the task that changed the API (Task 6 or 7; Step 14's rule), and start again at Step 2.

- [ ] **Step 6: Run the acceptance gates (agent)**

```bash
grep -n "def accept_invite" backend/repos/invites.py; echo "repo accept_invite exit $?"
grep -rnwI --include='*.py' accept_invite backend streamlit_tests streamlit_views | grep -v 'usecases/onboarding.py\|api/routes/invites.py\|onboarding\.accept_invite\|from usecases.onboarding import'; echo "accept_invite gate exit $?"
git diff --quiet origin/main...HEAD -- app.py ui_helpers.py streamlit_tenancy.py; echo "streamlit files diff exit $?"
grep -n "accept_invite" app.py
test ! -e streamlit_tests/test_onboarding.py && echo "test_onboarding.py is gone"
.venv/bin/python -m pytest -q "backend/tests/test_usecase_onboarding.py::test_create_church_seeds_catalog_with_identical_values" "backend/tests/test_usecase_onboarding.py::test_accept_captured_invite_joins_as_member" "backend/tests/test_usecase_onboarding.py::test_accept_adds_membership_with_invite_role" "backend/tests/test_usecase_onboarding.py::test_existing_owner_keeps_role" "backend/tests/test_usecase_onboarding.py::test_invite_rejections[accept-church_unavailable]" "backend/tests/test_usecase_onboarding.py::test_email_bound_case_insensitive_role_honored" "backend/tests/test_usecase_onboarding.py::test_invite_rejections[accept-expired]" "backend/tests/test_usecase_onboarding.py::test_invite_rejections[accept-revoked]" 2>&1 | tail -1
(cd frontend && npx vitest run src/components/onboarding/join-invite.test.tsx -t "port:" 2>&1 | grep -E "^ +Tests ")
```

**Expected,** in order:
- `repo accept_invite exit 1` (no output before it: the repo function is gone; Task 5);
- `accept_invite gate exit 1` (no output before it). `-I --include='*.py'` keeps pytest's `__pycache__/*.pyc` files out; the exclusions allow the usecase's definition, the route's own `def accept_invite` and every `onboarding.accept_invite` call. A printed line is a comment, docstring or import still naming the old function (for example the multi-line import once at `test_invites_repo.py:10`): reword or remove it in the task that owns the file;
- `streamlit files diff exit 0` (`app.py`, `ui_helpers.py`, `streamlit_tenancy.py` untouched; S "Not in 1b");
- exactly `43:from repos.invites import accept_invite` and `294:                    ok, msg = accept_invite(code, user_id)` (`app.py` keeps its lines and cannot be imported on `main` any more; production Streamlit runs from `streamlit-frozen`, owner decision 3);
- `test_onboarding.py is gone`;
- `8 passed in <t>s` (the ported Streamlit create and accept tests, and the six `test_invites_repo.py` accept assertions, Tasks 3 and 5);
- `      Tests  3 passed | 18 skipped (21)` (the three `pick_invite_code` ports, Task 14: "whitespace-only pending code and field send nothing (port: blank when neither)", "an edited field wins over the prefilled pending code (port: typed wins over pending)", "an untouched prefilled code is previewed once, even in StrictMode (port: falls back to pending)").

Then the log, layering, route and configuration gates:

```bash
.venv/bin/python - <<'EOF'
import ast, pathlib
FORBIDDEN = {"code", "email", "user_email", "name", "payload", "body", "token", "authorization"}
LEVELS = {"debug", "info", "warning", "error", "exception", "critical"}
rows = []
for p in ["backend/usecases/onboarding.py", "backend/api/routes/churches.py", "backend/api/routes/invites.py", "backend/timezones.py"]:
    for node in ast.walk(ast.parse(pathlib.Path(p).read_text())):
        f = getattr(node, "func", None)
        if isinstance(node, ast.Call) and isinstance(f, ast.Attribute) and f.attr in LEVELS and isinstance(f.value, ast.Name) and f.value.id in {"logger", "logging", "log"}:
            used = set()
            for arg in list(node.args[1:]) + [k.value for k in node.keywords]:
                for n in ast.walk(arg):
                    if isinstance(n, ast.Name):
                        used.add(n.id)
                    elif isinstance(n, ast.Attribute):
                        used.add(n.attr)
                    elif isinstance(n, ast.Constant) and isinstance(n.value, str):
                        used.add(n.value)
            first = node.args[0].value.split()[0] if node.args and isinstance(node.args[0], ast.Constant) else "<not a literal>"
            rows.append(f"{p} {f.attr} {first} forbidden={sorted(used & FORBIDDEN) or 'none'}")
print("\n".join(sorted(rows, key=lambda r: r.split()[2])) or "no log calls")
EOF
grep -rnE '^\s*(from|import) (fastapi|starlette|streamlit)' backend/domain_errors.py backend/db backend/usecases backend/timezones.py; echo "layering grep exit $?"
(cd backend && ../.venv/bin/python -c "import sys, usecases.onboarding, timezones; print(sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}))")
(cd backend && ../.venv/bin/python -c "import sys, api.main; print(sorted(m for m in sys.modules if m.split('.')[0] == 'streamlit'))")
grep -nE '^\s*(async def|try:|except|(from|import) (sqlalchemy|db|repos)[ .])|session_scope' backend/api/routes/churches.py backend/api/routes/invites.py; echo "routes grep exit $?"
(cd backend && ../.venv/bin/python -c "from db.engine import _engine_kwargs; print(_engine_kwargs('sqlite:///x.db')['hide_parameters'], _engine_kwargs('postgresql://u:p@localhost:1/x')['hide_parameters'])")
(cd backend && ../.venv/bin/python -c "from tests.test_route_guards import USER_SCOPED; print(len(USER_SCOPED), sorted(USER_SCOPED))")
(cd backend && ../.venv/bin/alembic heads)
git diff --name-only origin/main...HEAD -- backend/migrations backend/db/models.py backend/alembic.ini .github docs/ops-runbook.md | wc -l
for r in origin/main HEAD; do git show "$r:docs/ops-runbook.md" | grep -n '\[owner' | grep -v 'An entry marked' | wc -l; done
git diff origin/main...HEAD -- docs/manual-verification.md | grep '^+' | grep -v '^+++' | grep -c 'liturgy-next'
git diff origin/main...HEAD -- docs/manual-verification.md | grep '^+' | grep -v '^+++' | grep -c 'liturgy-frozen'
git diff --name-only origin/main...HEAD | grep -E '(^|/)\.env' ; echo "env files: $?"
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -qx 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected,** in order:
- exactly these five lines (the four S INFO lines and the role-clamp WARNING; no log call in the routes or `timezones.py`; nothing passes a code, an email, a church name, a body or a token; Tasks 3–5):
  ```
  backend/usecases/onboarding.py info church_create_limited forbidden=none
  backend/usecases/onboarding.py info church_created forbidden=none
  backend/usecases/onboarding.py info invite_accepted forbidden=none
  backend/usecases/onboarding.py info invite_rejected forbidden=none
  backend/usecases/onboarding.py warning invite_role_clamped forbidden=none
  ```
- `layering grep exit 1` (no output before it: `usecases/`, `db/`, `domain_errors.py` and `timezones.py` import no FastAPI, Starlette or Streamlit; F §2.2);
- `[]` (the usecase and the IANA check load none of the three, even indirectly);
- `[]` (`api.main` with the `churches` and `invites` routers loads no Streamlit; AC16 first half);
- `routes grep exit 1` (no output before it: plain `def` routes, no SQL, no session, no `try`/`except` for domain errors; Global Constraints "Layering");
- `True True` (the engine hides bound parameters on SQLite and Postgres, clarification 37; Task 1);
- `4 [('GET', '/me'), ('POST', '/churches'), ('POST', '/invites/accept'), ('POST', '/invites/preview')]` (Tasks 6 and 7);
- `0004_invites_reusable (head)` (no migration in 1b, clarification 34);
- `0` (1b touches no migration, model, Alembic config, workflow or runbook; `wc` pads the number with spaces);
- `4` twice (the runbook's `[owner` markers are unchanged; 1b's records go in Task 21's records PR);
- `0` (no added manual-check line names `liturgy-next`; owner decision 3; `grep -c` exits 1 on `0`, which is expected);
- a number of at least `1` (the manual checks use liturgy-frozen, Task 19);
- `env files: 1` (grep found nothing: no `.env` file is on the branch);
- only `trailer check done` (every commit on the branch, merges included, ends with the trailer).

Any other output: stop, find the owning task (Step 14's table) and fix it there.

- [ ] **Step 7: Check the exact list of changed paths (agent)**

```bash
LC_ALL=C sort > "<scratch>/slice1b-expected-paths.txt" <<'EOF'
backend/api/main.py
backend/api/routes/churches.py
backend/api/routes/invites.py
backend/api/schemas.py
backend/db/engine.py
backend/repos/churches.py
backend/repos/hymns.py
backend/repos/invites.py
backend/repos/memberships.py
backend/tests/api_helpers.py
backend/tests/conftest.py
backend/tests/test_api_app.py
backend/tests/test_api_churches.py
backend/tests/test_api_invites.py
backend/tests/test_churches_repo.py
backend/tests/test_engine.py
backend/tests/test_hymns_repo.py
backend/tests/test_invites_repo.py
backend/tests/test_memberships_repo.py
backend/tests/test_no_streamlit_in_core.py
backend/tests/test_onboarding_postgres.py
backend/tests/test_route_guards.py
backend/tests/test_slice1_docs.py
backend/tests/test_timezones.py
backend/tests/test_usecase_onboarding.py
backend/timezones.py
backend/usecases/onboarding.py
docs/manual-verification.md
docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md
docs/superpowers/specs/2026-09-25-migration-foundations-design.md
docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md
frontend/src/app/(signed-in)/(church)/church-layout.test.tsx
frontend/src/app/(signed-in)/(church)/layout.tsx
frontend/src/app/(signed-in)/layout.tsx
frontend/src/app/(signed-in)/signed-in-layout.test.tsx
frontend/src/app/(signed-in)/welcome/page.tsx
frontend/src/app/(signed-in)/welcome/welcome.test.tsx
frontend/src/app/join/join-client.tsx
frontend/src/app/join/join.test.tsx
frontend/src/app/join/page.tsx
frontend/src/app/login/login.test.tsx
frontend/src/app/login/page.tsx
frontend/src/components/app/app-header.test.tsx
frontend/src/components/app/church-switcher.tsx
frontend/src/components/app/error-state.test.tsx
frontend/src/components/app/error-state.tsx
frontend/src/components/app/shell-skeleton.tsx
frontend/src/components/app/timezone-combobox.test.tsx
frontend/src/components/app/timezone-combobox.tsx
frontend/src/components/onboarding/create-church-form.test.tsx
frontend/src/components/onboarding/create-church-form.tsx
frontend/src/components/onboarding/join-invite.test.tsx
frontend/src/components/onboarding/join-invite.tsx
frontend/src/lib/api/errors.test.ts
frontend/src/lib/api/errors.ts
frontend/src/lib/api/openapi.json
frontend/src/lib/api/schema.d.ts
frontend/src/lib/api/types.ts
frontend/src/lib/auth.ts
frontend/src/lib/idempotency.test.ts
frontend/src/lib/idempotency.ts
frontend/src/lib/post-login.test.ts
frontend/src/lib/post-login.ts
frontend/src/lib/queries/me.ts
frontend/src/lib/queries/membership.test.tsx
frontend/src/lib/queries/membership.ts
frontend/src/lib/queries/onboarding.test.tsx
frontend/src/lib/queries/onboarding.ts
frontend/src/lib/supabase/proxy.test.ts
frontend/src/lib/supabase/proxy.ts
frontend/src/lib/timezones.test.ts
frontend/src/lib/timezones.ts
frontend/src/lib/use-sign-out.test.tsx
frontend/src/test/fixtures/index.ts
frontend/src/test/mocks.ts
streamlit_tests/test_onboarding.py
EOF
git diff --name-only --no-renames origin/main...HEAD | LC_ALL=C sort > "<scratch>/slice1b-actual-paths.txt"
wc -l < "<scratch>/slice1b-expected-paths.txt"
wc -l < "<scratch>/slice1b-actual-paths.txt"
LC_ALL=C comm -3 "<scratch>/slice1b-expected-paths.txt" "<scratch>/slice1b-actual-paths.txt"
git diff --name-status --no-renames origin/main...HEAD | cut -c1 | sort | uniq -c
```

**Expected:** `76`; `76`; `comm` prints nothing; then `  32 A`, `   1 D` (`streamlit_tests/test_onboarding.py`, Task 14) and `  43 M`. The 76 are this plan's File Structure list (28 backend and Streamlit paths, 44 frontend paths, 4 docs); `docs/ops-runbook.md` is not among them (Task 21's records PR). Any `comm` line:
- a tab-indented line (changed on the branch, not in the list): find the path in the **Files:** section of the task that touched it (`git log --format='%h %s' origin/main..HEAD -- '<that path>'` names the commit). If that task's **Files:** names it, it is expected: count it and continue. Anything else, in particular `app.py`, `ui_helpers.py`, `streamlit_tenancy.py`, `backend/migrations/…`, `backend/db/models.py`, `.github/workflows/ci.yml`, `frontend/src/components/ui/…`, `frontend/src/proxy.ts` or `frontend/src/app/auth/callback/route.ts`: stop and find why the task touched it;
- an unindented line (in the list, not changed): the owning task's commit is missing; stop and find it.

- [ ] **Step 8 (agent → OWNER): Ask for the go-ahead to push, rewrite the PR and mark it ready**

Pushing new commits, rewriting the PR and marking it ready are outward-facing. Owner answer 5 covered only Task 8's draft checkpoint. Count the new commits and find the PR:

```bash
git rev-list --count origin/claude/slice-1b-plan..HEAD
gh pr list -R bbrown62450/church --head claude/slice-1b-plan --state open --json number,isDraft,url
```

**Expected:** a positive count (the commits made since Task 8's last push: Tasks 9–19, plus Step 1's merge if there was one); one PR with `"isDraft":true` and Task 8's number `<N>`. If the list is `[]` (the draft was closed), Step 12 creates the PR instead of editing it; say so in the message.

Send the owner exactly this message, with `<count>` and `<N>` replaced by the values above, and wait for a clear yes:

> Slice 1b is verified locally: backend 797 passed, 9 skipped; frontend 221 passed in 34 files; typecheck, lint and build clean; OpenAPI and API types in sync; AC16 greps clean (`repos.invites.accept_invite` gone, `app.py` untouched, `streamlit_tests/test_onboarding.py` gone with its five tests ported); no migration; changed paths as planned (76). May I (1) push `claude/slice-1b-plan` (<count> new commits) to draft PR #<N>, (2) once CI is green, retitle it to "Slice 1b onboarding: create a church, join by invite" and replace its body (with the CI seed timing), and (3) mark it ready for review? Merging stays with you (Task 21).

Do only what the owner approves. A yes to (1) and (2) without (3) leaves the PR a draft after Step 12; a yes to (1) alone leaves Task 8's title and body.

- [ ] **Step 9 (agent, on the owner's yes to item 1): Push**

```bash
git fetch origin
test "$(git rev-list --count HEAD..origin/main)" = 0 && git push origin claude/slice-1b-plan || echo "not pushed"
```

**Expected:** `<old sha>..<new sha>  claude/slice-1b-plan -> claude/slice-1b-plan`. On `not pushed`, run `git rev-list --count HEAD..origin/main`: if it is not `0` (`main` moved after Step 1), go back to Step 1 (merge, then Steps 2–7) and push afterwards (the owner's yes still covers it); if it is `0`, the push was rejected: stop and tell the owner. Never force-push.

- [ ] **Step 10: Watch the checks (agent)**

Run with the Bash tool's `run_in_background: true` (the watch can outlast the 10-minute foreground limit; the tool re-invokes the agent when it exits):

```bash
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

**Expected** when it exits: exit code 0 and every check `pass`: `backend`, `backend-postgres`, `frontend`, and the Vercel preview deployment. If it exits at once with the previous head's results (the new run has not registered yet), run it again. Any `fail` goes to Step 14.

- [ ] **Step 11: Read the CI logs and compare (agent)**

```bash
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1b-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); echo "run $RUN"
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1b-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1b-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres" or .name == "frontend") | .name as $j | .steps[] | "\($j) / \(.name): \(.conclusion)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1b-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "[0-9]+ passed"
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1b-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Running (upgrade|downgrade)|No new upgrade operations detected|pg_smoke: OK|hymn seed: [0-9]+ rows in [0-9]+ ms|[0-9]+ (passed|failed|errors?)( |,)"
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1b-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "frontend") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Test Files +[0-9]+ passed|Tests +[0-9]+ passed|Compiled successfully"
```

(Shell variables do not carry between commands, so each line sets `$RUN` and `$JOB` itself. If the first line prints `run ` with no id, the run is not listed yet: run it again.)

**Expected:**
- `run <id>` (keep the id for Step 12);
- jobs: `backend: success`, `backend-postgres: success`, `frontend: success`;
- steps: every step `success`, including `backend-postgres / Migrate the empty database to head`, `… / The models match the migrated schema`, `… / Every revision downgrades`, `… / Migrate to head again`, `… / Identity smoke (ops-2)`, `… / Postgres-only tests`, and `frontend / API types match the OpenAPI snapshot (F §5.4)`;
- backend: `797 passed, 9 skipped in …s`;
- backend-postgres, in this order: the four `Running upgrade` lines (`  -> 0001_baseline` … `0003_lockdown -> 0004_invites_reusable`; 1b adds no revision), `No new upgrade operations detected.`, the four `Running downgrade` lines (`0004_invites_reusable -> 0003_lockdown` … `0001_baseline -> `), the four upgrades again, `pg_smoke: OK`, one line ending `UserWarning: hymn seed: 700 rows in <ms> ms` (the warnings summary; the source line under it prints `{n}`/`{ms}` literally, so the regex skips it), `9 passed, 797 deselected, 1 warning in …s`;
- frontend: `Test Files  34 passed (34)`, `Tests  221 passed (221)`, `✓ Compiled successfully`.

Note `<ms>`. It is under 3000 (the test asserts `< 3.0` s); S Risk 3's production threshold (5 s) is checked in Task 21.

If a required job failed and the date is 2026-10-19 or later, first read the runner image (GitHub moves `ubuntu-latest` to Ubuntu 26 that day; 1a minor T14-m2):

```bash
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1b-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.conclusion == "failure") | .databaseId' | head -1); gh run view -R bbrown62450/church --job "$JOB" --log | grep -m2 -E "Image: |Version: "
```

**Expected:** `Image: ubuntu-24.04` (and its version) as on the draft run; if it shows `ubuntu-26.04` and the failure is in setup (Python or Node install, the Postgres service), report it to the owner before changing any 1b file. Otherwise go to Step 14.

- [ ] **Step 12 (agent, on the owner's yes to item 2): Write the PR body with the CI timing, retitle the PR**

Write the body (quoted heredoc, so the backticks stay literal); the command after it replaces `@SEED_MS@` and `@SEED_RUN@` with the final run's values:

```bash
cat > "<scratch>/slice1b-pr-body.md" <<'EOF'
PR 1b of slice 1: onboarding. A signed-in user can create a church (and becomes its owner) or join one from an invite link or code. Spec: docs/superpowers/specs/2026-09-25-slice-1-onboarding-design.md (1b). Plan: docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md. No migration: head stays `0004_invites_reusable`, so the merge deploy's pre-deploy `alembic upgrade head` is a no-op.

Backend
- `backend/timezones.py` (`is_valid_timezone`: exact, case-sensitive IANA names); the engine sets `hide_parameters=True`; the idempotency store is reset between tests; `tests/api_helpers.py` asserts carry messages (1a minor T13-m1).
- Repos: `session=` on `create_church`, `get_church`, `get_role`, `create_invite`; `create_church_seeded` (id and hymn count); `recent_owned_creations`; the hymnal seed is one bulk insert; `create_invite(reusable=)`; `find_by_code`; `claim` (one conditional UPDATE); `ensure_membership` (`insert_ignore`); `invites.as_utc`.
- `usecases/onboarding.py`: `create_church` (trimmed name, required time zone, IANA check, at most 5 owned churches per 24 hours with soft-deleted ones counted, church + owner + hymnal in one transaction); `preview_invite` (read-only; church name, role, expiry, email-bound, already-member); `accept_invite` (checks 0-6 in S's order and wording; `owner` clamped to `admin`; an existing member never consumes a single-use code; a lost `claim` race is `used`, or `already_member` when the caller won it; reusable invites are never stamped). Log lines hold ids only: `church_created`, `church_create_limited`, `invite_accepted`, `invite_rejected`, and the role-clamp WARNING.
- `repos.invites.accept_invite` is removed. `app.py`, `ui_helpers.py` and `streamlit_tenancy.py` are untouched, so `app.py` no longer imports on `main`; production Streamlit runs from `streamlit-frozen`.
- Routes (user-scoped, `X-Church-Id` ignored): `POST /churches` (201 `ChurchOut`; Idempotency-Key replay for 15 minutes; 429 `rate_limited` with `Retry-After`, never stored), `POST /invites/preview`, `POST /invites/accept` (400 `invite_rejected` with `details.reason`). `USER_SCOPED`, the error docs, the OpenAPI snapshot and `schema.d.ts` updated.
- Postgres-only tests (CI): two users racing for one single-use invite, one user double-accepting (single-use and reusable), and a church create copying a 700-row catalog.

Frontend
- `lib/idempotency.ts` (`createKeyTracker`, `stableStringify`, `settleOutcome`), `lib/post-login.ts` (a 10-minute return path), `lib/timezones.ts`, `errorToastMessage`.
- Sign-in continuity: the proxy lets `/join` through and sends other deep links to `/login?next=…`; `/login` stores `next` and asks Google for the account chooser on `select_account=1`; `useSignOut({ selectAccount })`; `endSignOut()` when `/login` mounts; the `(signed-in)` layout follows the stored path.
- `TimezoneCombobox` (at most 50 matches, "Type to search", a text input when the browser lists no zones); query hooks `useCreateChurch`, `usePreviewInvite`, `useAcceptInvite`, `useMembershipChanged`; `meQueryOptions`.
- `JoinInvite` (preview card, then a Join tap; rejection cards; email mismatch → another Google account), `/join` (captures the code, removes it from the address bar, `noindex`, `no-referrer`), `CreateChurchForm`, `/welcome` with Join and Create tabs, and the switcher item "Join or create a church…".

Docs: F amendments (D14 and §4.3: preview then Join approved by the owner on 2026-09-26, amendment to decision 6; §7.4 `already_member`; §1.6 the idempotency key has no church yet; §3.3 Railway settings live in the UI; §6.1 liturgy-frozen; the accept result and race handling; §4.3 step 2's signed-out wording), S's open items closed, manual checks 2-11 in `docs/manual-verification.md`.

Owner answers (2026-09-28): preview then Join, dated 2026-09-26; manual-check invites come from liturgy-frozen (Settings → Invites); the six F doc fixes above; two 1a leftovers fixed (the full-page Retry shows it is working and ignores repeat taps; one shared loading skeleton, announced to screen readers); the early draft PR; merge on the owner's yes at any time (no database change); results go in a new "Slice 1b record" in `docs/ops-runbook.md` through a docs-only records PR.

Standing-permission fixes (owner decision 2: safety or reliability, no owner-visible change) that differ from S's text:
- Clarification 4: `invites.claim` updates with `synchronize_session=False` and the usecase re-reads the row, so a lost claim is never mistaken for the caller's own.
- Clarification 19: `/join` handles a 401 itself (local sign-out, back to `/login?next=/join`, code kept).
- Clarification 20: `/join` decides "signed in" from the access token; a network error shows Retry, never the sign-in card.
- Clarification 21: `lib/auth.ts` `endSignOut()`, called when `/login` mounts, so Back into a cached signed-in page refetches `/me` instead of showing the skeleton forever (replaces 1a clarification 27's slice 2 hand-off).
- Clarification 22: the `(signed-in)` layout clears the stored return path before following it (S: on arrival), so a path with no page yet cannot redirect every visit for 10 minutes.
- Clarification 23: if `/me` fails after a join or create, the cached `/me` is reset and the app still goes to `/` with the new church stored.
- Clarification 37: the engine hides bound parameters, so a database error's traceback never logs an invite code or email.
- Clarification 42: `Retry-After` counts from the fifth-newest counted church, not the oldest, which stays right when six or more were created (frozen Streamlit has no cap).
- Clarification 45: `/join` sends `Referrer-Policy: no-referrer` through its metadata, so the code-bearing URL is never a Referer.

Known limits kept: the 30-second create timeout does not cover a hung token refresh (clarification 36); `UTC` and `Etc/*` are not in the browser's zone list (clarification 43, for 6a); 1a minor T4-m2 (a double tap whose first create fails with a non-domain error) stays open.

AC16: `streamlit_tests/test_onboarding.py` is gone and each assertion lives on:

| Removed test | Now |
|---|---|
| `test_pick_invite_code_typed_wins_over_pending` | `join-invite.test.tsx` "an edited field wins over the prefilled pending code (port: typed wins over pending)" |
| `test_pick_invite_code_falls_back_to_pending` | `join-invite.test.tsx` "an untouched prefilled code is previewed once, even in StrictMode (port: falls back to pending)" |
| `test_pick_invite_code_blank_when_neither` | `join-invite.test.tsx` "whitespace-only pending code and field send nothing (port: blank when neither)" |
| `test_create_church_makes_owner_and_seeds_hymnal` | `test_usecase_onboarding.py::test_create_church_seeds_catalog_with_identical_values` |
| `test_accept_captured_invite_joins_as_member` | `test_usecase_onboarding.py::test_accept_captured_invite_joins_as_member` |
| `test_invites_repo.py` accept tests (`:24`, `:34`, `:43`, `:57`, and the accept halves of `:76`, `:89`) | `test_accept_adds_membership_with_invite_role`, `test_existing_owner_keeps_role`, `test_invite_rejections[accept-church_unavailable]`, `test_email_bound_case_insensitive_role_honored`, `test_invite_rejections[accept-expired]`, `test_invite_rejections[accept-revoked]` |

Seed timing (S Risk 3): hymn seed: 700 rows in @SEED_MS@ ms on CI Postgres (the whole `POST /churches` round trip; backend-postgres, run @SEED_RUN@); budget 3 s in CI, 5 s in production.

Tests: backend 697 → 797 passed, 5 → 9 skipped; frontend 126 → 221 in 23 → 34 files

After merge (Task 21): the Railway deploy log shows the pre-deploy `alembic upgrade head` with no `Running upgrade` line and a passing `/health/ready`; Vercel Production Ready; manual checks 2-11 at 375 px and on desktop (with one production create's seed timing and whether Google's account chooser appeared); the Streamlit smoke on https://liturgy-frozen.streamlit.app/; then a docs-only records PR. Production Streamlit runs from `streamlit-frozen` and is not deployed by this PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-1b-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres") | .databaseId'); MS=$(gh run view -R bbrown62450/church --job "$JOB" --log | grep -oE 'hymn seed: 700 rows in [0-9]+ ms' | head -1 | grep -oE '[0-9]+ ms$' | cut -d' ' -f1); echo "run=$RUN ms=$MS"; test -n "$MS" && sed -i '' -e "s/@SEED_MS@/$MS/" -e "s/@SEED_RUN@/$RUN/" "<scratch>/slice1b-pr-body.md"; grep -c '@SEED_' "<scratch>/slice1b-pr-body.md"; grep -n 'hymn seed' "<scratch>/slice1b-pr-body.md"; tail -1 "<scratch>/slice1b-pr-body.md"
```

**Expected:** `run=<the Step 11 id> ms=<the Step 11 ms>`; `0` (both markers replaced; `grep -c` exits 1, which is expected); `…:Seed timing (S Risk 3): hymn seed: 700 rows in <ms> ms on CI Postgres (the whole `POST /churches` round trip; backend-postgres, run <id>); budget 3 s in CI, 5 s in production.`; `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. If `ms=` is empty, the log did not hold the line: rerun Step 11's backend-postgres line and do not edit the PR until it does.

If PR `<N>` exists (the usual case):

```bash
gh pr edit <N> -R bbrown62450/church \
  --title "Slice 1b onboarding: create a church, join by invite" \
  --body-file "<scratch>/slice1b-pr-body.md"
gh pr view <N> -R bbrown62450/church --json title,isDraft,headRefOid --jq '"\(.title) | draft=\(.isDraft) | \(.headRefOid)"'
git rev-parse HEAD
```

**Expected:** the edit prints the PR URL; the view prints `Slice 1b onboarding: create a church, join by invite | draft=true | <sha>`, and `git rev-parse HEAD` prints the same `<sha>`.

If Step 8 found no open PR, open it instead (not as a draft: CI is already green on this head):

```bash
gh pr create -R bbrown62450/church --base main --head claude/slice-1b-plan \
  --title "Slice 1b onboarding: create a church, join by invite" \
  --body-file "<scratch>/slice1b-pr-body.md"
```

**Expected:** `https://github.com/bbrown62450/church/pull/<N>`; use this `<N>` from here on, and skip Step 13's `gh pr ready` (the PR is not a draft).

- [ ] **Step 13 (agent, on the owner's yes to item 3): Mark the PR ready, and report**

Only when Steps 10–12 matched:

```bash
gh pr ready <N> -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json isDraft,state,url --jq '"draft=\(.isDraft) \(.state) \(.url)"'
```

**Expected:** `✓ Pull request bbrown62450/church#<N> is marked as "ready for review"`, then `draft=false OPEN https://github.com/bbrown62450/church/pull/<N>`. (CI does not rerun: `ci.yml`'s `pull_request` trigger uses the default activity types, which do not include `ready_for_review`.)

Report to the owner in one message: "PR #<N> (<url>) is ready for review: CI green (backend 797 passed, 9 skipped; backend-postgres 9 passed including the invite races, hymn seed: 700 rows in <ms> ms on CI Postgres, budget 3 s; frontend 221 passed in 34 files, build OK; Vercel preview OK). Next: Task 21, the merge on your yes (any day, owner answer 6), then the deploy watch and manual checks 2–11." If the owner did not approve item 3, say the PR stays a draft and ask again when they want it.

- [ ] **Step 14: Fix any failure in its owning task (agent)**

If Steps 2–7 or 10–12 did not match, read the failure (for CI: `gh run view <run-id> -R bbrown62450/church --log-failed | tail -80`) and fix it in the task that owns it:

| Failing check or test | Owning task (files) |
|---|---|
| `test_timezones.py`, `test_engine.py::test_engine_hides_bound_parameters`, the idempotency reset in `conftest.py`, `api_helpers.py`, the `hide_parameters` gate | Task 1 |
| `test_churches_repo.py`, `test_hymns_repo.py`, `test_memberships_repo.py`, the new `test_invites_repo.py` tests | Task 2 |
| `test_usecase_onboarding.py` create and cap tests, the `church_created` / `church_create_limited` log lines | Task 3 |
| `test_invite_rejections[preview-*]`, `test_blank_code_is_invalid_input[preview]`, `test_order_*`, `test_clamp_role`, `test_preview_*`, the `invite_rejected` / `invite_role_clamped` lines | Task 4 |
| `test_invite_rejections[accept-*]`, the accept and claim-lost tests, the `accept_invite` greps, `test_invites_repo.py` imports | Task 5 |
| `test_api_churches.py`, the `/churches` rows in `test_route_guards.py` / `test_api_app.py`, `openapi.json` drift after `/churches` | Task 6 (regenerate with `.venv/bin/python backend/scripts/export_openapi.py`, then `(cd frontend && npm run gen:api)`, and commit both) |
| `test_api_invites.py`, the invite rows, `openapi.json` / `schema.d.ts` drift after the invite routes, the routes grep | Task 7 (same regeneration) |
| `test_onboarding_postgres.py` in `backend-postgres`, the seed timing | Task 8 (its Step 10 table) |
| `idempotency`, `post-login`, `timezones`, `errors` tests | Task 9 |
| `proxy.test.ts`, `login.test.tsx`, `use-sign-out.test.tsx`, `lib/auth.ts` | Task 10 |
| `signed-in-layout.test.tsx`, `error-state.test.tsx`, `church-layout.test.tsx`, `shell-skeleton.tsx` | Task 11 |
| `timezone-combobox.test.tsx` | Task 12 |
| `onboarding.test.tsx`, `membership.test.tsx`, `lib/api/types.ts`, `lib/queries/me.ts`, `test/fixtures/index.ts` | Task 13 |
| `join-invite.test.tsx`, the three `(port: …)` tests | Task 14 |
| `join.test.tsx`, a build error on `/join` (Suspense, `metadata`), a `join.html` tag | Task 15 |
| `create-church-form.test.tsx` | Task 16 |
| `welcome.test.tsx`, a build error on `/welcome` | Task 17 |
| `app-header.test.tsx`, `church-switcher.tsx` | Task 18 |
| `test_slice1_docs.py`, the manual-verification gates | Task 19 |
| a 1a test outside this list (`test_migrations.py`, `test_identity.py`, `test_ops_workflows.py`, 1a's five Postgres tests, 1a frontend tests other than those above) | 1b should not affect them: report to the owner before changing anything |
| the Vercel preview only | report the preview's build log to the owner before changing anything |

For each fix:
1. Reproduce it locally first where SQLite, Vitest or the build can show it.
2. Change only the owning task's files.
3. Rerun Steps 2–7 (`797 passed, 9 skipped`; `221 passed` in 34 files; clean types, lint, build, generated files and gates).
4. Commit with the subject `Fix: <what> (Task <n>, slice 1b final verification)` and the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, staging files by name.
5. Have that task re-reviewed (its plan section against the fix's diff).
6. Before Step 9 (no yes yet): continue with Step 8. After the owner's yes to item 1: `git push origin claude/slice-1b-plan` (covered by that yes; never `--force`), then repeat Steps 10–12 (Step 12 rewrites the body with the new run's timing).

An infrastructure failure with no test output (a service container that never became healthy, a timed-out `npm ci` or `pip install`) gets one `gh run rerun <run-id> -R bbrown62450/church --failed` before it counts as a failure.

Expected counts after this task: backend `797 passed, 9 skipped` locally (CI `backend`: the same; CI `backend-postgres`: `9 passed, 797 deselected, 1 warning`); frontend `221 passed` in 34 files. No commit unless Step 14 needed a fix.
### Task 21: Merge and after (OWNER + agent): merge, the no-op deploy, manual checks 2–11, the Streamlit smoke check, the slice 1b record (S Manual checks, Risks 3 and 8; AC9–AC12, AC17; F-AC8, F-AC9; owner answers 2, 6, 7)

1b changes no schema. `backend/migrations/versions/` still ends at `0004_invites_reusable`, so the merge deploy's pre-deploy `alembic upgrade head` (set in the Railway UI, owner decision 4) connects, finds the database at head and runs nothing (clarification 34). That means no stamping, no backup gate, no drift check, no laptop `alembic` step, and no Railway, Supabase or branch-protection change. Owner answer 6 drops 1a's "a weekday, when the tester is not using the app" rule: the tester uses https://liturgy-frozen.streamlit.app/, which a merge never reaches (owner decision 3). This task merges PR `<N>` on the owner's yes and watches the deploy. It then walks the owner through manual checks 2–11 on production in small steps, runs the Streamlit smoke check (AC17), and records everything in a docs-only `claude/slice-1b-records` PR (owner answer 7). `docs/manual-verification.md` stays a reusable checklist with unchecked boxes. Its "## Slice 1" preamble already points to the new record (Task 19).

Below, `<N>` is PR 1b's number (Task 8 opened it as a draft; Task 20 marked it ready), and `<scratch>` is the absolute path of the session's scratchpad directory. Write both out literally in each command. Every `gh` command names the repository with `-R bbrown62450/church`. Pushing, commenting on or merging a PR, running a workflow, and any Railway, Supabase or GitHub settings change each need the owner's explicit yes, asked separately. The agent never sees a database URL or any other secret. Nothing below is recorded with an invite code, an email address, a database URL, a password or a database host name. The owner prefers small steps (one OWNER step per message): give one OWNER step, wait for the report (or "next"), then give the next. While the owner reports, the agent writes each result, with its date, into `<scratch>/slice1b-t21-results.md` (not committed; no codes, no emails). Step 18 fills the record from that file.

**Accounts and windows for Steps 5–17.** **A** is the owner's own Google account (owner of the owner's real church). **B** and **C** are two other Google accounts that belong to no church. Signing in with them creates their user rows, which is harmless. Nobody but the owner types their passwords. A stays signed in in a normal Chrome window, for both https://liturgy-frozen.streamlit.app/ and https://worship-service-builder.vercel.app. B and C take turns in Chrome private (Incognito) windows. To switch between them, **close every private window**, which ends that private session and signs it out of Google, then open a new one. "At 375 px" means: in that window open DevTools (⌥⌘I), turn on the device toolbar (⇧⌘M) and pick **iPhone SE** (375 × 667). Every new window needs this again. Throwaway churches only, never the owner's real church. Invites come from liturgy-frozen only (owner answer 2): the church → **Settings** → **Invites** tab → the form with "Bind to email (optional)" and "Role" → **Create invite**, which shows ``Invite code: `…` ``. Such invites are single-use in the new app (`reusable = false`). Build the link by typing `worship-service-builder.vercel.app/join?code=` in the private window's address bar and pasting the code after it. Never paste a code into chat, a record, or a screenshot. The Invites tab lists codes, so never screenshot it. The cap is 5 new churches per account per 24 hours, and it counts soft-deleted churches and churches made in Streamlit. This task creates 1 church for A and 3 for C.

**Why A creates "1b Invite Test" in the new app** (a deviation from the carry-over notes' setup): liturgy-frozen offers **Create a church** only to an account with no church (`app.py:344-347` on `streamlit-frozen`: `render_onboarding` runs only when `require_active_church` returns `None`). A already has a church, so A creates the throwaway church in the new app through the switcher, which also covers check 7 on desktop. Liturgy-frozen shares the database, so it lists that church for A at once, and A makes the invites there.

**Files:**
- Merge (Steps 1–2): no file changes. PR `<N>` (`claude/slice-1b-plan` → `main`) merges with a merge commit.
- Create (not committed): `<scratch>/slice1b-t21-results.md` (the owner's dated reports, Steps 3–17)
- Modify (records PR, Step 18, branch `claude/slice-1b-records` from `origin/main` after the merge): `docs/ops-runbook.md`. Insert `### Slice 1b record` right after `### Alembic stamping record (slice 1a)`'s table (its last row starts `| Manual check 1 (at 375 px and on desktop) |`) and before `## Backups` (about line 227 of `origin/main`). A `###` heading, because `test_ops_workflows.py::test_runbook_has_the_seven_sections_in_order` pins the `##` list.
- Revert path only (Step R): a branch `claude/revert-slice-1b` from `origin/main` holding `git revert -m 1` of the merge commit.
- Test: none new. Dated records are not pinned by tests, as with 1a's records PR (#17).

**Interfaces:**
- Consumes:
  - PR `<N>` from Task 20: ready for review, all checks green. Its body has the line starting `Tests: backend 697 → 797 passed, 5 → 9 skipped` and the CI line `hymn seed: 700 rows in <ms> ms`, copied from the `backend-postgres` job's "warnings summary" (Task 8, clarification 41). Task 20 also records the runner-image watch (`ubuntu-latest` becomes Ubuntu 26 on 2026-10-19).
  - Task 19: `docs/manual-verification.md` → `## Slice 1`, the ten items 2–11 and the preamble naming `docs/ops-runbook.md` → "Slice 1b record".
  - The client copy of Tasks 14–18, verbatim in Global Constraints: `/join` cards, `/welcome` tabs, the create form, the switcher item "Join or create a church…".
  - The server messages and log lines of Tasks 3–7: `church_created church_id=… user_id=… hymns_seeded=… duration_ms=…`, `invite_accepted …`, `invite_rejected reason=… invite_id=…`.
  - Routes `POST /churches`, `POST /invites/preview`, `POST /invites/accept` (Tasks 6–7).
  - 1a's `### Alembic stamping record (slice 1a)` table in `docs/ops-runbook.md`.
  - The Railway UI settings: Pre-deploy Command `alembic upgrade head`, Healthcheck Path `/health/ready` (owner decision 4).
  - The 1a lost-access toast "You no longer have access to {name}." (`(church)/layout.tsx:80,98`), `AccountMenu`'s "Account menu" button, `Role: …` line and "Log out" item.
- Produces:
  - The 1b merge commit on `main`: the Railway API serves the three new routes, still at `0004_invites_reusable (head)`, and Vercel serves `/join`, the new `/welcome` and the switcher item.
  - Records PR `claude/slice-1b-records` with `### Slice 1b record`: the deploy, CI, manual checks 2–11 at 375 px and on desktop, the S Risk 3 seed timing (CI and one production create), the S Risk 8 chooser observation and the Streamlit smoke check.
  - Follow-ups only if seen: a seed above 5 s (switch the Postgres path to `INSERT … SELECT`), or no account chooser (card copy fallback "Sign out of Google in this browser, then try again.").
  - Later users: slice 2 starts from this `main`.

- [ ] **Step 1 (agent): Pre-merge gate**

```bash
git fetch origin
gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus,baseRefName,headRefName,headRefOid --jq '[.state, .isDraft, .mergeable, .mergeStateStatus, .baseRefName, .headRefName, .headRefOid] | @tsv'
git rev-parse origin/claude/slice-1b-plan
git log --oneline origin/claude/slice-1b-plan..origin/main | wc -l
gh pr checks <N> -R bbrown62450/church
gh api repos/bbrown62450/church/branches/main/protection/required_status_checks --jq '.contexts | sort | join(",")'
gh pr view <N> -R bbrown62450/church --json body --jq .body | grep -E '^Tests: backend 697|hymn seed: [0-9]+ rows in [0-9]+ ms'
git diff --quiet origin/main origin/claude/slice-1b-plan -- backend/migrations/env.py backend/migrations/versions backend/db/models.py; echo "exit $?"
git ls-tree --name-only origin/claude/slice-1b-plan backend/migrations/versions/ | grep -c '\.py$'
date -u '+%Y-%m-%d'
```

**Expected:**
- `OPEN	false	MERGEABLE	CLEAN	main	claude/slice-1b-plan	<sha>`, and the next line prints the same `<sha>`.
- `0` (the branch already contains `main`).
- Every check `pass`: `backend`, `backend-postgres`, `frontend`, and the Vercel preview.
- `backend,backend-postgres,frontend`.
- The `Tests: backend 697 → …` line and a line containing `hymn seed: 700 rows in <ms> ms`.
- `exit 0`: no revision, `env.py` or model change, so the deploy's pre-deploy step has nothing to run (clarification 34).
- `4` (`0001_baseline.py` … `0004_invites_reusable.py`).
- Today's date. If it is 2026-10-19 or later and a required job failed, check the job's runner image (`ubuntu-latest` becomes Ubuntu 26 on that date) before blaming 1b (Task 20's watch).

If `gh api …/required_status_checks` answers 404 or 403 instead of the three names, ask the owner to confirm in GitHub → Settings → Branches → the `main` rule that `backend`, `backend-postgres` and `frontend` are required.

If `main` moved (a count other than `0`), merge it into the branch and rerun both suites:

```bash
git switch claude/slice-1b-plan
git merge origin/main -m "Merge origin/main into claude/slice-1b-plan (Task 21)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test && npm run typecheck && npm run lint)
```

Expected: `797 passed, 9 skipped in <t>s` (if the merge brought new tests, the count differs by exactly those; stop and ask the owner if it differs in any other way); Vitest `Test Files  34 passed (34)`, `Tests  221 passed (221)`; `tsc` and `eslint` print nothing beyond their banners. On a merge conflict, stop and tell the owner. Then ask the owner's yes for `git push origin claude/slice-1b-plan` (never force), wait for green checks (`gh pr checks <N> -R bbrown62450/church --watch`), and run this step again. If `mergeStateStatus` is `BLOCKED`, a required check is not green: fix it in the owning task's files. Never merge with `--admin`. If `isDraft` is `true`, Task 20's last step is missing: it runs first.

Then ask the owner, in one message: "PR #<N> (slice 1b) is green, includes `main`, and changes no database schema, so the deploy runs no migration. May I merge it now with a merge commit? (Owner answer 6: any time is fine; liturgy-frozen is not affected.)"

- [ ] **Step 2 (agent, on the owner's yes): Merge**

```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergedAt,mergeCommit --jq '[.state, .mergedAt, .mergeCommit.oid] | @tsv'
git fetch origin
git log -1 --format='%h %s' origin/main
```

Expected: `MERGED	<UTC time>	<merge sha>`, then `<short merge sha> Merge pull request #<N> from bbrown62450/claude/slice-1b-plan`. Use a merge commit (`--merge`), not squash. Write the merge time (UTC and Eastern) and the sha into `<scratch>/slice1b-t21-results.md`. Then tell the owner: "Merged at <time> (<short merge sha>). Railway and Vercel are deploying it now. Step 3 is next: watching that deploy."

- [ ] **Step 3 (OWNER): Watch the merge deploy**

1. Railway → project `talented-nourishment` → the API service (`church`) → **Deployments** → the deployment whose message starts `Merge pull request #<N>` → open it → **Deploy Logs** (if the pre-deploy lines are not there, look in **Build Logs**). Alembic writes to stderr, so Railway may colour its lines red. That alone is not an error.
2. Check the **pre-deploy** part: a `Database: dialect=postgresql driver=psycopg2 host=… database=postgres` line, then `INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.` and `INFO  [alembic.runtime.migration] Will assume transactional DDL.`, and **no** line containing `Running upgrade`.
3. Check the health check: it used `/health/ready` and passed, and the deployment is **Active**.
4. Check the app's startup lines: they include `Database: dialect=postgresql driver=psycopg2 host=… database=postgres`, and no line contains `schema revision`, `Row-level security`, `Traceback` or `ERROR`.
5. Vercel → the `worship-service-builder` project → **Deployments**: the **Production** deployment for the merge commit is **Ready**.

Tell the agent: the date; the pre-deploy lines from `Context impl` to the last line before the app starts, with the host after `host=` replaced by `…`; "health check passed, Active" (or what you saw); "no schema/RLS/Traceback/ERROR lines" (or the lines); Vercel Ready or not.

If something went wrong (in each case the previous release keeps serving):
- A `Running upgrade` line: unexpected, since Step 1 showed no revision change. Stop and send the agent the lines.
- The health check failed: send the agent the startup lines (never a URL with a secret). The fix is a PR, or Step R if it cannot wait.
- Vercel's production build failed: send the agent the build log's error lines. Production keeps the previous frontend, and the fix is a PR.

- [ ] **Step 4 (agent): CI on `main` and the public endpoints**

```bash
gh run list --workflow ci --branch main --limit 3 -R bbrown62450/church --json databaseId,headSha,status,conclusion --jq '.[] | select(.headSha == "<merge sha>") | [.databaseId, .status, .conclusion] | @tsv'
```

The push run can take a few seconds to appear. If nothing prints, run the line again (no `sleep`). Then, with its `databaseId`:

```bash
gh run watch <run-id> --exit-status -R bbrown62450/church
API=https://church-production-74ca.up.railway.app
curl -s "$API/health"; echo
curl -s "$API/health/ready"; echo
curl -s -w ' %{http_code}\n' "$API/me"
curl -s -w ' %{http_code}\n' -X POST "$API/churches" -H 'Content-Type: application/json' -d '{}'
curl -s -w ' %{http_code}\n' -X POST "$API/invites/preview" -H 'Content-Type: application/json' -d '{"code":""}'
curl -s "$API/openapi.json" | .venv/bin/python -c 'import json, sys; p = json.load(sys.stdin)["paths"]; print(sorted(k for k in p if k in ("/churches", "/invites/preview", "/invites/accept")))'
```

**Expected:**
- The run completes successfully (`backend`, `backend-postgres`, `frontend`).
- `{"ok":true}`.
- `{"ok":true,"db":"ok"}`. A 503 body with `"reason":"schema_behind"` would mean a release behind head, which 1b cannot cause: stop and tell the owner.
- Three times `{"error":{"code":"unauthenticated","message":"Please sign in.","request_id":"<32 hex>"}} 401`, with no `fields` or `details` keys. On `POST /churches`, `get_current_user` runs before the Idempotency-Key check (clarification 10).
- `['/churches', '/invites/accept', '/invites/preview']`: the new release is the one serving.

These are public, read-only requests with no token and no invite code. Write the results into `<scratch>/slice1b-t21-results.md`. Then give the owner Step 5.

- [ ] **Step 5 (OWNER): Setup on desktop: "1b Invite Test" and the first invite (manual check 7 on desktop, F-AC8)**

In A's normal window, at full desktop width (device toolbar off):

1. Open https://worship-service-builder.vercel.app → home shows your church.
2. Click the church switcher (top left, your church's name) → **Join or create a church…** → `/welcome`. Check that the heading is "Join or create a church", with "Signed in as <your email>." under it and a link "← Back to <your church>". The two tabs are "Join a church" (selected) and "Create a church".
3. Click **← Back to <your church>** → home. Then use the browser's **Back** button → `/welcome` shows again (no endless loading skeleton). Click **Create a church**.
4. The tab shows "Start a new church. You'll be its owner and can invite others.", a "Church name" field (placeholder "e.g. First Presbyterian Church") and a "Time zone" field already filled with your computer's zone, with `_` shown as a space (for example "America/New York") and the helper "Sets the default service date (the next Sunday in this time zone).". Under them: "Your church gets its own copy of the starter hymnal." and the button **Create church**.
5. Type the name `1b Invite Test` (if you already have a church by that name, use `1b Invite Test 2`, and use that name wherever these steps say "1b Invite Test") → **Create church** → the button reads "Creating church…" → home with **1b Invite Test** active and the toast "Created 1b Invite Test. You're the owner.". Open the switcher: both churches are listed: 1b Invite Test with "Owner", your church with your role there. Click your own church: home switches to it. Switch back to 1b Invite Test.
6. Open https://liturgy-frozen.streamlit.app/ in a new tab (same window) → in the sidebar's church picker choose **1b Invite Test** → **Settings** → **Invites** tab → leave "Bind to email (optional)" empty, Role `member` → **Create invite** → the green box shows `Invite code: …`. Keep this tab open (you will copy the code in Step 6). Don't paste the code anywhere else.

Tell the agent: the date; "heading, back link, Back button, tabs, create, toast, switcher OK" (or what differed); the time zone shown by default; "invite created in liturgy-frozen".

- [ ] **Step 6 (OWNER): Manual check 2 at 375 px: signed out, open the link, sign in as B, Join (F-AC9, AC9, AC10)**

1. Close every private window. Open a new private window, then turn on DevTools at 375 px (iPhone SE). In DevTools open the **Network** tab.
2. In the private window's address bar type `worship-service-builder.vercel.app/join?code=`, paste the code from Step 5, press Return.
3. When the page has loaded, the address bar shows `…vercel.app/join` with **no** `?code=`. The card reads "You're invited" / "Sign in with Google to see and accept your invite to Worship Service Builder." with a **Sign in with Google** button.
4. Tap **Sign in with Google** → Google → sign in as **B** → you come back to `/join` (not home), and a card shows:
   - the title "1b Invite Test";
   - "You're invited to join as a member.";
   - "Invite expires <a date about 7 days away>.";
   - the buttons **Join 1b Invite Test** and **Not now**;
   - at the bottom, "Signed in as <B's email> · Use a different account".
5. Tap **Join 1b Invite Test** → it reads "Joining…" → home with **1b Invite Test** active and the toast "Joined 1b Invite Test.".
6. In the Network tab, type `invites` in the filter box: the rows are named `preview` and `accept` (each may also have a `preflight` row). Click each → Headers: its Request URL ends in `/invites/preview` or `/invites/accept`, with nothing after it.
7. Back in A's liturgy-frozen tab: reload, choose 1b Invite Test → Settings → Invites: that invite is no longer listed (the list hides accepted invites).

Tell the agent: the date and, for each of 3–7, OK or what differed. If an error card or a toast with "(Ref: …)" appears, send a screenshot and the Ref code.

- [ ] **Step 7 (OWNER): Manual check 3, first half, at 375 px: B reopens the same link**

Still in B's private window (375 px): type the same `worship-service-builder.vercel.app/join?code=` + paste the code again → Return. The card shows only "You're already a member of 1b Invite Test." (no "You're invited to join as…" line) with the button **Open 1b Invite Test**. Tap it → home with 1b Invite Test active and the toast "You're already a member of 1b Invite Test.".

Tell the agent: the date, OK or what differed.

- [ ] **Step 8 (OWNER): Manual check 3, second half, at 375 px: C gets "already used"; the code is in no log line (AC9)**

1. Close every private window. Open a new one, turn on 375 px, and open the same link again (address bar + paste the code).
2. "You're invited" → **Sign in with Google** → sign in as **C** → back on `/join`: "This invite has already been used." with "Ask for a new invite link." and a **Go to home** button.
3. Tap **Go to home** → `/welcome` with the heading "Welcome to Worship Service Builder" and "Signed in as <C's email>. You don't belong to a church yet.". Stay here for Step 9.
4. In A's normal window: Railway → the API service → Deployments → the Active deployment → **Deploy Logs** → in the search box type `invite_`. You see one `invite_accepted … already_member=False` line (Step 6), one `invite_accepted … already_member=True` line (Step 7) and one `invite_rejected reason=used invite_id=…` line (this step). Then replace the search with the **first 8 characters of the invite code** (paste, then delete the rest): no log line matches.

Tell the agent: the date; OK or what differed for 2–3; the three kinds of lines seen (no ids needed); "no line has the code".

- [ ] **Step 9 (OWNER): Manual check 5 at 375 px: C creates "1b Test C"; seed timing (S Risk 3, AC11)**

1. In C's private window (375 px, on `/welcome`), with DevTools → **Network** open and its filter empty, tap the **Create a church** tab. The "Time zone" field is prefilled with your computer's zone.
2. Name `1b Test C` → **Create church** → home with **1b Test C** active and the toast "Created 1b Test C. You're the owner.". **Account menu** (the round avatar, top right) shows `Role: Owner`.
3. In Network, type `churches` in the filter. If two rows are named `churches`, pick the one whose **Type** is `fetch` (the other is its `preflight`). Its Headers show Request Method `POST` and Status Code `201`. Open its **Timing** tab and note "Waiting for server response" (for example `1.24 s`).
4. Railway → Deploy Logs → search `church_created` → the newest line ends `hymns_seeded=<n> duration_ms=<ms>`. Note those two numbers only.
5. Supabase → the project → **SQL Editor** → new query → paste and run:

```sql
select (select count(*) from hymn_catalog) as catalog,
       (select count(*) from hymns h join churches c on c.id = h.church_id
         where c.name = '1b Test C' and c.deleted_at is null) as seeded;
```

   The two numbers are equal, and equal to `hymns_seeded` from 4.

Tell the agent: the date; OK or what differed for 1–2; the "Waiting for server response" time; `hymns_seeded` and `duration_ms`; the `catalog` and `seeded` numbers. If `duration_ms` is above 5000 or the Timing is above 5 s, say so: that triggers the `INSERT … SELECT` follow-up (S Risk 3).

- [ ] **Step 10 (OWNER): Manual check 6 at 375 px: blank name, then a double tap on a slow connection**

1. In C's window (375 px): church switcher → **Join or create a church…** → **Create a church** tab. In DevTools → Network, clear the list (the **Clear network log** button, a circle with a line through it) and set the throttling menu (it says "No throttling") to **Slow 4G**.
2. Leave the name empty → tap **Create church** → "Church name is required." shows under the field, the cursor is in the name field, and the Network list stays empty (no `churches` row).
3. Type `1b Test C2` → **double-tap** **Create church** quickly. The button reads "Creating church…" (after 8 s also "Still working — this can take up to a minute.") → home with **1b Test C2** active and the toast "Created 1b Test C2. You're the owner.".
4. Set throttling back to **No throttling**. Open the switcher: exactly one "1b Test C2" (and "1b Test C").

Tell the agent: the date; OK or what differed for 2–4; how many `churches` rows of Type `fetch` the Network list shows (1 expected; 2 with the same Idempotency-Key request header are also fine, since the server replays the first); how many "1b Test C2" churches are listed.

- [ ] **Step 11 (OWNER): Manual check 4 at 375 px: email-bound invite, wrong account, the account chooser (S Risk 8, AC10 with churches)**

1. In A's liturgy-frozen tab: 1b Invite Test → Settings → **Invites** → "Bind to email (optional)": **C's** email, Role `member` → **Create invite**. Keep the code for 2.
2. Close every private window. Open a new one at 375 px → `worship-service-builder.vercel.app/login` → **Sign in with Google** → **B** → home (1b Invite Test). Then type `worship-service-builder.vercel.app/join?code=` + paste the new code → Return.
3. The card reads "This invite was issued for a different email address." and "You're signed in as <B's email>." with the button **Use a different Google account**.
4. Tap it → `/login` → **Sign in with Google**. **Does Google show its account chooser** ("Choose an account", listing B and "Use another account")? Note yes or no.
   - Yes: choose **Use another account** → sign in as **C**.
   - No (Google signs you straight back in as B): note "no chooser", close every private window, open a new one at 375 px, open the same link, **Sign in with Google** → type C's email → sign in as C.
5. Back on `/join` as C: the preview says "You're invited to join as a member." and "This invite is for <C's email>." → **Join 1b Invite Test** → home with 1b Invite Test active and the toast "Joined 1b Invite Test.". C already had churches, which is fine.

Tell the agent: the date; OK or what differed for 3 and 5; **whether the account chooser appeared** (yes/no). "No" makes the card's fallback line a follow-up (S Risk 8).

- [ ] **Step 12 (OWNER): Manual check 7 at 375 px: a third church from the switcher (F-AC8, AC12 item half)**

In C's window (375 px): church switcher → **Join or create a church…** → `/welcome` shows "Join or create a church" and "← Back to 1b Invite Test" → **Create a church** → `1b Test C3` → **Create church** → home with 1b Test C3 active. The switcher lists 1b Invite Test (Member), 1b Test C, 1b Test C2 and 1b Test C3 (Owner). Pick 1b Invite Test → **Account menu** shows `Role: Member`; pick 1b Test C3 → `Role: Owner`. C has now created 3 of 5.

Tell the agent: the date, OK or what differed.

- [ ] **Step 13 (OWNER): Manual check 8 at 375 px: B loses access while the app is open**

1. Close every private window. Open a new one at 375 px → `worship-service-builder.vercel.app` → sign in as **B** → home with 1b Invite Test active (B's only church).
2. In A's liturgy-frozen tab: 1b Invite Test → Settings → **Members** → B's row → **Remove**.
3. Wait 30 seconds. Then click into A's window and back into B's private window (a refocus). If nothing happens, wait another 30 seconds and refocus again.
4. B's window shows the toast "You no longer have access to 1b Invite Test." and lands on `/welcome` ("Welcome to Worship Service Builder": B has no church left).

Tell the agent: the date, OK or what differed (and after how many refocuses).

- [ ] **Step 14 (OWNER): Manual check 9: Log out keeps the other device signed in; no input zoom on iOS**

1. On your **iPhone** (Safari; if you prefer, use Safari on the laptop instead and skip 2): open https://worship-service-builder.vercel.app → sign in as **B** → `/welcome`.
2. On the iPhone, tap the "Invite link or code" field: the page does not zoom in. Tap **Create a church** → tap "Church name": no zoom. Tap somewhere empty to close the keyboard.
3. In B's private window on the laptop (375 px, on `/welcome`): **Account menu** → **Log out** → `/login`.
4. On the iPhone: reload the page → still `/welcome`, signed in as B.

Tell the agent: the date; which second device you used; OK or what differed for 2 (iPhone only), 3 and 4.

- [ ] **Step 15 (OWNER): Manual check 10 at 375 px: no sideways scroll, 16 px inputs, 44 px tap targets**

In the private window at 375 px, sign in as **B** again (`/login` → **Sign in with Google** → B) → `/welcome`:

1. On `/welcome`, **Join a church** tab, then **Create a church** tab: swipe or scroll sideways (trackpad two-finger swipe left/right) → the page does not move sideways, and nothing is cut off at the right edge.
2. Right-click the "Invite link or code" field → **Inspect** → in DevTools **Computed**, type `font-size` in the filter → `16px`; then `height` → `44px`. Do the same for:
   - the **Continue** button (`height` `44px`);
   - on the Create tab, "Church name" (`16px`, `44px`) and **Create church** (`44px`);
   - the time-zone field: `font-size` `16px` on the input that Inspect selects. For its height, click the line just above it in the Elements panel (the `div` with `data-slot="input-group"`) → `44px`;
   - the tab row: Inspect **Join a church**, click the line just above it (the `div` with `role="tablist"`) → `height` `44px`.
3. Open `worship-service-builder.vercel.app/join` (no code) → "This invite link is incomplete." / "Open the link from your invite again, or ask for a new one." and **Go to home**: no sideways scroll; **Go to home** is `44px` tall.
4. Home: B has no church, so **Go to home** lands on `/welcome`. For home itself, use C's view: close every private window, open a new one at 375 px, sign in as **C** → home (a 1b Test church): no sideways scroll, and the switcher and account menu both open and fit on screen.
5. The `/join` cards seen at 375 px in Steps 6–12 (the sign-in card, preview, already a member, already used, wrong email) had no sideways scroll either. If you noticed one, say which.

Tell the agent: the date and OK, or each value that differed (which element, which number).

- [ ] **Step 16 (OWNER): Desktop pass: manual checks 2, 3, 10 and the regression pass on desktop**

Full desktop width everywhere (device toolbar off). Checks 5–7 ran on desktop in Step 5 (A's create from the switcher).

1. In A's liturgy-frozen tab: 1b Invite Test → Settings → **Invites** → no email, Role **admin** → **Create invite**.
2. Close every private window. Open a new one (no device toolbar). Open `worship-service-builder.vercel.app/join?code=` + the new code. The address bar shows `/join` only, and the "You're invited" card fits the page centre → **Sign in with Google** → **B** → back on `/join`: "You're invited to join as an **admin**." → **Join 1b Invite Test** → home with 1b Invite Test active, the toast "Joined 1b Invite Test.", and **Account menu** → `Role: Admin`.
3. Open the same link again → "You're already a member of 1b Invite Test." → **Open 1b Invite Test** → home.
4. Switcher → **Join or create a church…** → `/welcome`: both tabs look right at desktop width (content in a narrow centred column, nothing overlapping), and "← Back to 1b Invite Test" returns home.
5. Open `worship-service-builder.vercel.app/join` (no code) → "This invite link is incomplete." → **Go to home** → home.
6. Regression pass (F §5.5), in A's normal window on the new app: reload → your church or 1b Invite Test loads; switch between the two → home follows; **Account menu** → **Log out** → `/login` → sign in again as A → home.

Tell the agent: the date and, for each of 2–6, OK or what differed.

- [ ] **Step 17 (OWNER): Manual check 11 and the Streamlit smoke check on liturgy-frozen (AC17)**

1. **Smoke** (F §6.3), in A's normal window on https://liturgy-frozen.streamlit.app/: reload; you are signed in (or sign in); **your own church** and its hymnal load; open a saved service → it loads; **Settings** opens.
2. **C's church in Streamlit:** close every private window. Open a new one → https://liturgy-frozen.streamlit.app/ → sign in with Google as **C** → in the sidebar's church picker choose **1b Test C** → **Settings** → **Hymns** tab lists hymns (the starter hymnal). Close the private window.
3. **Revoked by delete**, as A in liturgy-frozen: 1b Invite Test → Settings → **Invites** → no email, member → **Create invite** (keep the code for the next item). Then the **Danger zone** tab → "Delete this church" → type `1b Invite Test` → **Delete church** → "Church deleted.".
4. Close every private window, open a new one → `worship-service-builder.vercel.app/join?code=` + the code from 3 → **Sign in with Google** as **C** → "This invite has been revoked." with "Ask for a new invite link." and **Go to home** (revoked is checked before the church's own state). Close the private window. (Aside: if 1b Invite Test was active in one of A's new-app tabs, refocusing it shows "You no longer have access to 1b Invite Test." and switches to your church: expected.)
5. Streamlit Cloud → `liturgy-frozen` → **Manage app** → logs: after the merge time from Step 2 there is no `Pulling code changes from Github` or `Updated app!` line and no restart. **⋮** → **Settings** still shows branch `streamlit-frozen`.

Tell the agent: the date and, for each of 1–5, OK or what differed. If any Streamlit page fails, send the error text (never a code). The frozen app does not run 1b's code, so a failure there is a shared-database question: stop, and the agent investigates before anything else.

Optional (owner's choice, not needed for the record): soft-delete C's three throwaway churches in liturgy-frozen as C (each church → Settings → Danger zone → type its name → **Delete church**). They still count toward C's cap for 24 hours.

- [ ] **Step 18 (agent): Records PR: the slice 1b record**

```bash
git fetch origin
git switch -c claude/slice-1b-records origin/main
git show origin/main:docs/ops-runbook.md | grep '\[owner' | grep -vc 'An entry marked'
grep -c 'Slice 1b record' docs/manual-verification.md
```

Expected: `4` (the owner markers before this edit); a number of at least `1` (Task 19's preamble already names the record). In `docs/ops-runbook.md`, use Edit to replace the last row of `### Alembic stamping record (slice 1a)` plus the blank line and `## Backups` after it:

```markdown
| Manual check 1 (at 375 px and on desktop) | Owner's account, on desktop and at 375 px (iPhone SE): sign-in, home shows the church, the church menu lists the churches with the role, the account menu shows name, email and `Role: Owner`, Log out returns to `/login`: all OK. The check with an account in no church (the stub `/welcome`) was skipped by the owner. | 2026-09-27 |

## Backups
```

with that same row, one blank line, the block below, one blank line and `## Backups`:

```markdown
### Slice 1b record

Slice 1b (onboarding: create a church, join by invite) merged as PR #<N>
with no database change, so production stays at `0004_invites_reusable`
(head) and the merge deploy's pre-deploy `alembic upgrade head` ran no
upgrade. The manual checks are `docs/manual-verification.md` → Slice 1,
items 2–11, run on the production URLs at 375 px (Chrome device mode,
iPhone SE) and on desktop, with throwaway churches and three Google
accounts: A (the owner), B and C (no church before the checks). Invites
were created in https://liturgy-frozen.streamlit.app (Settings → Invites),
since there is no invite UI in the new app until slice 6b. No invite code,
email address or database URL is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. Pre-deploy `alembic upgrade head`: `Context impl PostgresqlImpl.`, `Will assume transactional DDL.`, no `Running upgrade` line; the `/health/ready` health check passed; Active; no `schema revision`, `Row-level security`, `Traceback` or `ERROR` line; Vercel production Ready | <date> |
| CI and public endpoints | CI on the merge commit green (run <run id>: `backend`, `backend-postgres`, `frontend`). `/health` → `{"ok":true}`; `/health/ready` → `{"ok":true,"db":"ok"}`; signed out, `GET /me`, `POST /churches` and `POST /invites/preview` → 401 `unauthenticated`; `/openapi.json` lists `/churches`, `/invites/preview`, `/invites/accept` | <date> |
| Seed timing (S Risk 3) | CI Postgres (`backend-postgres`, PR #<N>): `hymn seed: 700 rows in <ms> ms` (budget 3 s). Production create of "1b Test C": `church_created … hymns_seeded=<n> duration_ms=<ms>`; DevTools "Waiting for server response" <t> s; hymn count equal to `hymn_catalog` (<n>). <Under 5 s: no change. / Above 5 s: follow-up to seed with `INSERT … SELECT`.> | <date> |
| Account chooser (S Risk 8) | <Google's account chooser appeared on "Use a different Google account" (`prompt=select_account` passes through Supabase). / The chooser did not appear: Google signed B straight back in; follow-up for the card's fallback line "Sign out of Google in this browser, then try again.".> | <date> |
| 2. Signed-out invite link, sign in, Join (375 px) | Address bar `/join` without the code; "You're invited" card; sign-in as B returned to `/join`; preview with church, member role and expiry; Join → home with the church active and "Joined 1b Invite Test."; the requests were `/invites/preview` and `/invites/accept` with no code; the invite left liturgy-frozen's list | <date> |
| 3. Reopened link (375 px) | B: "You're already a member of 1b Invite Test." with no role line, Open → the church with that toast. C: "This invite has already been used." + "Ask for a new invite link."; Go to home → `/welcome`. Railway logs: `invite_accepted` (`already_member=False`, then `True`) and `invite_rejected reason=used`; no log line holds the code (AC9) | <date> |
| 4. Email-bound invite, wrong account (375 px) | B saw "This invite was issued for a different email address." and "You're signed in as" B; "Use a different Google account" → <chooser / no chooser, see Risk 8 row> → C → preview → Join → joined; C already had churches | <date> |
| 5. New account creates a church (375 px) | C on `/welcome` (zero churches), Create tab with the browser's zone preselected (<zone>); "1b Test C" active with `Role: Owner`; hymn count equal to `hymn_catalog` | <date> |
| 6. Double tap and blank name (375 px, Slow 4G) | Blank name → "Church name is required.", no request; double tap on "1b Test C2" → one church (<n> `POST /churches` request(s)) | <date> |
| 7. Switcher "Join or create a church…" (desktop and 375 px) | A on desktop: `/welcome` "Join or create a church", back link and browser Back OK, created "1b Invite Test", both churches listed. C at 375 px: created "1b Test C3"; four churches listed; switching between 1b Invite Test and 1b Test C3 showed Member and Owner | <date> |
| 8. Lost access (375 px) | B removed in liturgy-frozen; after a refocus: "You no longer have access to 1b Invite Test." and `/welcome` | <date> |
| 9. Log out, other device (375 px) | Log out on `/welcome` → `/login`; B on <iPhone Safari / laptop Safari> stayed signed in | <date> |
| 10. Mobile layout (375 px) | No sideways scroll on `/welcome` (both tabs), `/join` (every card) and home; inputs 16 px <, no zoom on the iPhone>; inputs, tabs and primary buttons 44 px tall | <date> |
| Desktop pass (checks 2, 3, 10; F §5.5 regression) | B joined through a fresh admin invite on desktop ("as an admin", `Role: Admin`), reopened it ("already a member"); `/welcome` tabs and `/join` without a code at desktop width; A: sign in, switch church, home, Log out | <date> |
| 11. Streamlit smoke on https://liturgy-frozen.streamlit.app/ (AC17) | Sign-in, the owner's church and hymnal, a saved service and Settings OK; C's "1b Test C" shows its hymnal there; an invite made there for "1b Invite Test", then the church deleted in Danger zone → the new app says "This invite has been revoked."; no code pull in its logs after the merge, branch still `streamlit-frozen` | <date> |
| Follow-ups | <None. / One line per follow-up: what, which S risk.> | <date> |
```

Replace every `<…>` with the owner's values from `<scratch>/slice1b-t21-results.md` and Steps 1–4, keeping only the matching alternative where a cell offers two. A check that went differently records what happened instead of the expected text (for example "the chooser did not appear; C signed in from a fresh private window"). Then:

```bash
sed -n '/^### Slice 1b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 1b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|join\?code|code=|postgres(ql)?://|password|pooler\.supabase\.com'
grep '\[owner' docs/ops-runbook.md | grep -vc 'An entry marked'
git diff --stat origin/main
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:**
- `0` (no `<…>` left; the record uses "under" and "above", never `<`).
- `0` (no email, code, database URL or pooler host).
- `4`, the same as before (1b adds no `[owner` marker).
- ` docs/ops-runbook.md | <n> +` and ` 1 file changed, <n> insertions(+)`.
- `89 passed in <t>s`. That is 88 at `0295b37` plus Task 19's `test_foundations_records_the_join_tap_amendment`. `test_runbook_has_the_seven_sections_in_order` still passes, because the new heading is `###`.
- `797 passed, 9 skipped in <t>s`.

No new test.

```bash
git add docs/ops-runbook.md
git commit -m "Runbook: slice 1b record: onboarding live with no schema change, manual checks 2-11, Streamlit smoke (S Manual checks, Risks 3 and 8; AC17)" -m "Records the slice 1b merge (PR #<N>): the pre-deploy alembic upgrade head
ran no upgrade (production stays at 0004_invites_reusable), the health check
passed, CI and the public endpoints are green; the hymn seed timing on CI
Postgres and one production create; whether Google's account chooser
appeared; manual checks 2-11 at 375 px and on desktop with invites made in
liturgy-frozen; and the Streamlit smoke check on liturgy-frozen. No invite
code, email or database URL is recorded.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 19 (agent, on the owner's yes): Push, open and merge the records PR**

Ask the owner: "The slice 1b record is written (docs/ops-runbook.md only). May I push `claude/slice-1b-records` and open its PR?" On the yes:

```bash
git push -u origin claude/slice-1b-records
gh pr create -R bbrown62450/church --base main --head claude/slice-1b-records \
  --title "Runbook: slice 1b deploy and manual-check record" \
  --body "Records slice 1b (PR #<N>) in docs/ops-runbook.md → Slice 1b record: a merge deploy with no schema change (the pre-deploy alembic upgrade head ran no upgrade; production stays at 0004_invites_reusable), CI and the public endpoints, the hymn seed timing on CI Postgres and one production create (S Risk 3), the account-chooser observation (S Risk 8), manual checks 2-11 at 375 px and on desktop with invites made in liturgy-frozen, and the Streamlit smoke check on liturgy-frozen (AC17). No invite code, email or database URL is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/slice-1b-records -R bbrown62450/church --watch
```

Expected: `* [new branch]      claude/slice-1b-records -> claude/slice-1b-records`; the PR URL; `backend`, `backend-postgres`, `frontend` and the Vercel preview pass. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes:

```bash
gh pr merge claude/slice-1b-records --merge -R bbrown62450/church
gh pr view claude/slice-1b-records -R bbrown62450/church --json state,mergeCommit --jq '[.state, .mergeCommit.oid] | @tsv'
```

Expected: `MERGED	<sha>`. This merge redeploys the API and the frontend. Its pre-deploy step is again a no-op (no `Running upgrade` line) and `/health/ready` passes. The owner may glance at that deployment. Anything else there goes back to Step 3's list. If the seed was above 5 s or the chooser did not appear, offer the follow-up as its own branch and PR (not in this records PR). Then report to the owner: "Slice 1b is live and recorded: create a church, join by invite, the switcher item; no schema change; manual checks 2–11 and the Streamlit smoke check done (<n> follow-ups). Slice 2 can start from `main`."

- [ ] **Step R (only if the 1b release must come out): Revert**

Use this only when the release cannot serve (Step 3's health check) or breaks sign-in or the church pages, and a fix PR would take too long. No database step is needed: 1b adds no revision, so after the revert the 1a code runs on the same `0004_invites_reusable` schema, and the Railway Pre-deploy Command `alembic upgrade head` stays valid (1a has Alembic). Leave both Railway settings as they are. Rows written through 1b are ordinary data for 1a and for liturgy-frozen: new churches with their hymns, memberships, and invites with `accepted_at`/`accepted_by` set (liturgy-frozen's list already hides them). The revert brings back 1a's stub `/welcome`, `repos.invites.accept_invite` and `streamlit_tests/test_onboarding.py`.

Agent, on the owner's yes for each command that leaves this machine:

```bash
git fetch origin
git switch -c claude/revert-slice-1b origin/main
git revert -m 1 --no-commit <merge sha>
git commit -m "Revert slice 1b (PR #<N>): back to the 1a release; no schema change to undo" -m "The 1b merge deploy <what failed>. 1b added no Alembic revision, so the 1a
code runs on the same 0004_invites_reusable schema and Railway's pre-deploy
command and health check stay as they are. Churches, memberships and invites
created through 1b stay as ordinary rows.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm ci --prefer-offline && npm test)
git push -u origin claude/revert-slice-1b
gh pr create -R bbrown62450/church --base main --head claude/revert-slice-1b \
  --title "Revert slice 1b" \
  --body "Reverts the slice 1b merge (PR #<N>) because <what failed>. 1b changed no schema, so nothing is downgraded: production stays at 0004_invites_reusable and the Railway settings are unchanged. Rows created through 1b stay.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/revert-slice-1b -R bbrown62450/church --watch
```

Replace `<merge sha>`, `<N>` and `<what failed>` first. **Expected:**
- `697 passed, 5 skipped in <t>s` (1a's suite; if anything else merged after 1b, the count differs by exactly its tests).
- Vitest `Tests  126 passed (126)` in 23 files. If `npm ci --prefer-offline` cannot install without the network, skip the local frontend run and rely on CI's `frontend` job.
- The PR URL, and every check passes.

Merge on the owner's explicit yes (`gh pr merge claude/revert-slice-1b --merge -R bbrown62450/church`). The OWNER then checks that deployment: a pre-deploy step with no `Running upgrade` line, the `/health/ready` health check passed, Active; and https://worship-service-builder.vercel.app signs in and shows the church, with the stub `/welcome` for an account in no church. Record the revert as a row of `### Slice 1b record` (Step 18), or in its own records PR if Step 18 already merged.

Expected counts after this task: backend `797 passed, 9 skipped` on `main` (CI `backend-postgres`: `9 passed, 797 deselected, 1 warning`); frontend `221 passed` in 34 files. The records PR adds no test.
## Spec coverage

Every S item for 1b (the outline's reconciliation, items 1–55) and every acceptance criterion 1b touches, with the task that delivers or checks it. "DONE" items shipped in 1a; 1b only consumes them.

| # | Spec item (S 1b) | Status at `0295b37` | Task |
|---|---|---|---|
| 1 | `backend/timezones.py` `is_valid_timezone` (exact, case-sensitive, cached set) | NEW | T1 |
| 2 | `tzdata` in requirements | DONE | — |
| 3 | Autouse `reset_idempotency_for_tests()` (P1a :1888 hand-off) | NEW | T1 |
| 4 | Repo `session` params (`create_church`, `get_church`, `get_role`) + `as_uuid` in `create_church` | NEW | T2 |
| 5 | `repos.churches.recent_owned_creations` | NEW | T2 |
| 6 | Bulk hymnal seed (Core `insert(Hymn.__table__)`, clarification 50; same columns, same return) | NEW | T2 |
| 7 | `create_invite(..., reusable=False)`; `_to_dict` + `reusable`, `accepted_by`; `as_utc` export | NEW | T2 |
| 8 | `find_by_code`, `claim`, `ensure_membership` | NEW | T2 |
| 9 | `usecases/onboarding.py` package slot | DONE (package, docstring) | — |
| 10 | Usecase `create_church` + trimming + 3 messages + IANA check + atomic seed | NEW | T3 |
| 11 | Durable per-user cap (5/24 h, soft-deleted count, `RateLimited`, retry_after) | PARTIAL (`RateLimited` DONE) | T3 (usecase), T6 (HTTP) |
| 12 | Log lines `church_created`, `church_create_limited` | NEW | T3 |
| 13 | Invite checks 0–6, order, exact messages, `details.reason` | PARTIAL (checks 1–3, 5 and messages in `repos/invites.py:79-98`) | T4 (`_evaluate`), T5 (accept axis) |
| 14 | Accept semantics (clamp, existing member, stamping, claim race, `ensure_membership`, reusable) | NEW | T5 (+T2 repos, T8 races) |
| 15 | Preview semantics (read-only, five fields, clamp, `as_utc`, `already_member`) | NEW | T4 |
| 16 | Log lines `invite_accepted`, `invite_rejected` (no code, no email) | NEW | T4 (`invite_rejected`), T5 (both; caplog), T1 + T7 (`hide_parameters`, clarification 37) |
| 17 | Remove `repos.invites.accept_invite`; `app.py` untouched and unimportable on main | NEW | T5 |
| 18 | Port + delete `test_invites_repo.py` accept tests and `streamlit_tests/test_onboarding.py` | NEW | T3 (create test ported + removed), T5 (accept test + repo tests), T14 (3 `pick_invite_code` asserts ported, file deleted) (clarification 48) |
| 19 | `POST /churches` 201 `ChurchOut`, `CreateChurchIn` (extra forbid, 200/64), Idempotency-Key via `run_idempotent` | PARTIAL (store, `run_idempotent`, `ChurchOut` DONE) | T6 |
| 20 | `POST /invites/preview`, `POST /invites/accept`, `InviteCodeIn` (256), `InvitePreviewOut`, `InviteAcceptOut` | NEW | T7 |
| 21 | Mount `churches` + `invites` routers; fixed paths before any `/invites/{id}` | NEW | T6, T7 |
| 22 | `USER_SCOPED` + 3 routes in the same commit | NEW | T6, T7 |
| 23 | `test_no_streamlit_in_core.py` imports `api.main` (all routers) + `usecases.onboarding` | PARTIAL (every-router test DONE) | T1, T3, T6, T7 |
| 24 | OpenAPI snapshot + `gen:api` (`schema.d.ts`) | PARTIAL (tooling DONE) | T6, T7 |
| 25 | `GET /church` 403 `details.reason`; `ChurchOut.role` Literal; error codes `invite_rejected`/`idempotency_mismatch`/`rate_limited` | DONE | — |
| 26 | Postgres: two-user race, same-user double accept (single-use + reusable), 700-row create < 3 s | NEW | T8 |
| 27 | No migration (head stays `0004_invites_reusable`) | DONE (0004 in 1a) | T21 confirms no-op deploy |
| 28 | `lib/idempotency.ts` `createKeyTracker`, `stableStringify` | NEW | T9 |
| 29 | `lib/post-login.ts` store/peek/clear, 10 min | NEW | T9 |
| 30 | `lib/timezones.ts` `listTimezones`, `browserTimezone`, `defaultTimezone` | NEW | T9 |
| 31 | `lib/urls.ts` `safeInternalPath`, `extractInviteCode`, `buildInviteUrl`, `safeHttpsUrl` + `urls.test.ts` | DONE | — |
| 32 | `lib/storage.ts` keys; `timeouts.ts` `POST /churches` 30 000; `InviteRejectReason`; `NETWORK_MESSAGE` | DONE | — |
| 33 | Proxy: `/join` public, `?next=<pathname>` (not for `/`), `url.search` reset | NEW | T10 |
| 34 | `/login?next=` stored before OAuth; `?select_account=1` → `prompt: "select_account"` | NEW | T10 |
| 35 | `useSignOut` path to `/login?next=/join&select_account=1` | PARTIAL (`keepPendingInvite`, `next` DONE) | T10 |
| 36 | `(signed-in)` layout follows the stored post-login path | NEW | T11 |
| 37 | `TimezoneCombobox` (50 matches, "Type to search", text fallback) | PARTIAL (`components/ui/combobox.tsx` DONE) | T12 |
| 38 | `types.ts` `InvitePreview`, `InviteAccepted` | NEW | T13 |
| 39 | `queries/onboarding.ts` `useCreateChurch`, `usePreviewInvite`, `useAcceptInvite` | NEW | T13 |
| 40 | `queries/membership.ts` `useMembershipChanged` | NEW | T13 |
| 41 | `JoinInvite` state machine (enter → previewing → preview → joining; rejected; error) | NEW | T14 |
| 42 | `/join` (server `page.tsx` + metadata, `join-client.tsx` in Suspense, capture + `replaceState`, clears post-login) | NEW | T15 |
| 43 | `CreateChurchForm` (client checks, key tracker, 422/429/network handling, 8 s line, success) | NEW | T16 |
| 44 | `/welcome` Join + Create tabs, `?tab=`, both copies, back link (replaces the 1a stub) | PARTIAL (stub DONE) | T17 |
| 45 | Switcher item "Join or create a church…" → `/welcome` | PARTIAL (menu DONE) | T18 |
| 46 | Loading/empty/error table rows for Preview, Accept, Create | NEW | T14–T16 |
| 47 | Flow D (resolution, switch, lost access, Log out, 401, scope local) | DONE | — (return-to-path half: T10, T11) |
| 48 | Home `/` placeholder cards | DONE | — |
| 49 | Frontend tests named in S: urls/client/church/queries-client/(church)-layout | DONE | — |
| 50 | Frontend tests named in S: post-login, idempotency, timezones, proxy, combobox, AppHeader item, /welcome, /join, /login, (signed-in) layout | NEW | T9–T18 |
| 51 | Manual checks 2–11 appended to `docs/manual-verification.md` "## Slice 1" | NEW | T19 (write), T21 (run) |
| 52 | F§4.3 amendment (preview-then-Join approved) + close S's open items (Risk 1, Flow B note, BC4, AC10/manual 2 parentheticals, `/join` fallback test sentence, Risk 9) | NEW | T19 |
| 53 | Streamlit smoke after the 1b merge (AC17) | NEW | T21 |
| 54 | Risk 3 seed timing recorded (CI + one production create) | NEW | T8, T21 |
| 55 | Risk 8 `prompt=select_account` verified | NEW | T21 (manual 4) |

| Acceptance criterion / risk | Task |
|---|---|
| AC6 `POST /churches` 201, one church + owner + seed in one transaction, exact messages, cap, idempotent retry | T2 (seed), T3 (usecase, atomicity, cap), T6 (HTTP, Idempotency-Key, 429 never stored), T16 (form: key reuse on network/5xx), T8 (700-row timing on Postgres) |
| AC7 preview/accept checks 0–6 in order, exact messages, `details.reason`, preview read-only with five fields, role clamp | T4 (checks, preview), T5 (accept), T7 (HTTP bodies, 400/422 shapes) |
| AC8 single-use admits one user under concurrency; same-user repeat → `already_member: true` | T5 (claim-lost SQLite tests), T8 (Postgres barrier races, single-use and reusable) |
| AC9 no invite code in a path, a log line or the address bar | T1 (`hide_parameters=True`), T4/T5 (log lines without code/email), T7 (caplog, real DB error), T15 (`replaceState`, `no-referrer`, code only in bodies), T20 (AST log gate), T21 (Network panel, Railway log search) |
| AC10 `/join` signed out → sign in → Join → church active; existing member → Open | T10 (proxy `next`, `/login` stores the path), T11 (layout follows it), T14, T15, T19 (check 2 text), T21 (manual checks 2, 3) |
| AC11 zero-church user → `/welcome` → create (browser zone preselected; "Unknown timezone.") → home | T9 (`defaultTimezone`), T12, T16, T17, T21 (manual checks 5, 6) |
| AC12 switcher offers "Join or create a church…" (item half) | T18; T21 (manual check 7) |
| AC13 lost access | DONE in 1a; T21 (manual check 8) re-runs it after a 1b join |
| AC14 Log out clears keys; a 401 keeps the pending invite and returns to the allow-listed path | T10 (`selectAccount`, `endSignOut`, `/login` never clears), T11 (clear-before-follow), T15 (`/join` 401 subscriber), T17 (Log out on `/welcome`), T21 (manual check 9) |
| AC16 no `streamlit` under `api.main`; `streamlit_tests/test_onboarding.py` gone, every assertion ported | T3 (create test), T5 (accept test; `repos.invites.accept_invite` removed), T14 (three `pick_invite_code` asserts; file deleted), T6/T7 (`test_no_streamlit_in_core.py`), T20 (grep gates) |
| AC17 manual items 1–11 at 375 px and desktop; Streamlit smoke after the merge | T19 (checks 2–11 written), T21 (run, smoke on liturgy-frozen, records PR) |
| F-AC7 idempotent create | T6 |
| F-AC8 switcher item / church resolution | T18, T21 |
| F-AC9 `/join` capture and metadata | T15, T21 |
| F §4.3 amendment (preview then Join, 2026-09-26) and the six Q3 F fixes; S open items closed | T19 |
| Risk 1 (preview vs auto-join) | Closed by owner answer 1; T19 |
| Risk 3 (seed time) | T2 (bulk Core insert), T8 (CI `UserWarning`), T20 (PR body timing), T21 (production timing in the record) |
| Risk 7 (`Intl.supportedValuesOf` missing) | T9, T12 (text fallback), T16 |
| Risk 8 (`prompt=select_account`) | T10, T14, T21 (manual check 4 records whether the chooser appeared) |
| Risk 9 (native `replaceState`) | Closed from the bundled Next docs (clarification 27); T15, T19 |
| Risk 10 (Vercel request logs keep `/join?code=`) | Accepted (F §7.4); single-use invites |
| 1a hand-offs: idempotency store reset (P1a :1888), T13-m1, T18-m2, T22-m1, T22-m2, T23-m1, T23-m3 | T1, T1, T13, T11, T11, T13, T11; T23-m2 deferred (clarification 49) |
| No migration; `app.py`, `ui_helpers.py`, `streamlit_tenancy.py` untouched | T20 (gates), T21 (no-op deploy check) |
