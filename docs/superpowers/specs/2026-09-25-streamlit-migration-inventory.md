# Streamlit to FastAPI + React: migration inventory

Scope: the worktree at `.claude/worktrees/duplicate-wire-activity-review-6370f5`, branch `claude/react-fastapi-slice0`. This merges seven area inventories into one. Where they disagreed I checked the code; section 0 lists what was checked. No files were changed.

> **Amendment 2026-09-26: the service rubric (PR #4) is now current behavior.** PR #4 ("Service rubric", merged to `main` on 2026-09-26; design `2026-09-25-service-rubric-design.md`) added behavior that both Streamlit and the API already run: per-church rubric checklists and hymn preferences, hymn year and familiarity facts, rubric-aware hymn ranking, and rubric checklists plus sermon-text themes in the liturgy prompts. It is inventoried in D10, E9, G11, H13–H14, the `hymns`/`hymn_catalog`/`churches` rows of I, the `/rubric` rows of §2.2, a §3 row, §4 and §6. Line references in those additions are to `main` at `475c748` (after PR #4 and PR #6); older references elsewhere in this document still point at the original snapshot. Production Streamlit (`liturgy-next`) runs from `main` today, and the ops freeze cuts `streamlit-frozen` after PR #4, so the frozen app keeps all of this behavior.
>
> The prayer library (`docs/superpowers/specs/2026-09-26-prayer-library-design.md`, PR #7) is **new-app only** (owner decision): Streamlit has no counterpart, so there is no current behavior to inventory. Slices 4 and 6a carry it. The same holds for the service reviewer (`docs/superpowers/specs/2026-09-26-service-reviewer-design.md`, PR #8), an add-on right after slice 4. Its change to the default system prompt's season wording lands only with that add-on, so current behavior (E6) and frozen Streamlit keep the old wording.

---

## 0. Conventions and reconciled findings

**Conventions**
- All paths are relative to the repo root. Backend modules are imported by top-level name: `backend/` is put on `sys.path` at app.py:12 and in pytest.ini (`pythonpath = . backend`). So `repos.hymns.list_hymns` means `backend/repos/hymns.py`.
- Guard names:
  - `none`: public.
  - `user`: `get_current_user` (backend/api/deps.py:51-72).
  - `church`: `require_church`, which reads the X-Church-Id header (deps.py:75-82).
  - `admin`: `require_admin` (deps.py:85-88).
  - `owner`: a new `require_owner` dependency that must be added to deps.py. It does not exist yet.
- Product context from the spec (docs/superpowers/specs/2026-09-25-react-fastapi-migration-design.md:13-20): there is one real tester, and the only parallel-run requirement is keeping their data. Several recommendations below depend on this:
  - Fixing bugs even where that changes behavior is acceptable.
  - Keep the period where Streamlit and React both run short.
  - While both run, keep stored data readable by both apps.

**Contradictions between readers, resolved in code**
1. **Does a query string survive sign-in?** The proxy keeps it on the redirect: it clones `nextUrl` and changes only the pathname (frontend/src/lib/supabase/proxy.ts:35-38). The login page then drops it, because it signs in with `redirectTo: ${origin}/auth/callback` (frontend/src/app/login/page.tsx:28-31). The callback always redirects to `/` (frontend/src/app/auth/callback/route.ts:11). Net effect: an `?invite=` code, or a Gmail `code`/`state` that arrives while the user is signed out, is lost.
2. **Does the bulletin copy include the sermon title?** Yes. Both copies pass `include_sermon=True` (app.py:996, 1019). The button help "Liturgy only" (app.py:984), the caption "no sermon" (app.py:1092) and the build_docx docstring (backend/worship_service.py:802) are all wrong.
3. **Which success messages does the user actually see?**
   - Visible: "Liturgy generated…" (app.py:945) and "Email sent…" (app.py:1135), because no rerun follows them.
   - Never visible, because `st.rerun()` runs right after: Join (app.py:295), Create (317), Prepare (1004, 1027), Save (1054/1059/1063), Profile, Prompts and Contact saves in Settings.
   - The AI-suggestion message survives only because it is stored in session state (app.py:810-824).
4. **What can a malformed prompt template raise?** `liturgy_prompts.render` raises `ValueError` for `{curly`, `{0}`, a lone `}` and `{"a": 1}`. It raises `AttributeError` for `{foo.bar}` (verified with `.venv/bin/python`). The API must catch broadly, not only `ValueError`.
5. **Scripture matcher over-matching** is confirmed (verified):
   - "Isaiah 9:6" matches "Genesis 9:6" through the variant "is 9:6".
   - "Mark 1:9-15" matches "Mark 10:45".
   - "Psalm 1" matches "Psalm 119".
   - "John 3:1-17" matches "1 John 3:16".
6. **PH1990 CSV:** 605 rows but only 571 distinct lower-cased titles. Its columns are `number,title,tune` only (verified).
7. **Church timezone:** it is stored and edited (repos/churches.py:17, 39, 81-82; streamlit_views/settings.py:61-74, 180-197; app.py:303-315). Nothing reads it at runtime (grep).
8. **Line reference:** the `bible_translation` session seeding is at app.py:371-377.
9. **GitHub repo:** visibility is PUBLIC and there are no Actions secrets (`gh repo view`, `gh secret list`).
10. **No Streamlit calls under `backend/`:** no `st.*`, `session_state` or `st.cache_*` (grep). Streamlit is mentioned only in docstrings and comments: auth.py:6, 26; tenancy.py:5; google_oauth.py:19-21, 134, 195; db/engine.py:30; api/security.py:110-113; migrate_to_db.py:570.
11. **Endpoint naming** differed between readers. Section 2 normalizes it.
12. **No client query cache yet:** the frontend has no query-cache library (frontend/package.json). Wherever this document says "query cache", that is a new dependency (for example TanStack Query) or a small hand-rolled cache.

---

## 1. Feature inventory

Each feature lists what it does, the user steps, the domain code it reuses, the role it needs, external services, edge cases and messages, and existing tests.

### A. App shell, identity and tenancy

**A1. Bootstrap, page config, navigation**
- **What it does:**
  - Puts backend/ on the path (app.py:12). Loads `.env` and sets up logging from `LOG_LEVEL`, default INFO (app.py:56-64).
  - Page config: title "Worship Service Builder", a cross icon, wide layout (app.py:105-109).
  - Creates the schema once per process with `@st.cache_resource` (app.py:169-173, called at 328).
  - After church resolution it builds two pages with `st.navigation`: "Service Builder" (the default) and "Settings" (app.py:352-362). Both pages close over the same `user` and `active` for the current rerun.
  - Sidebar order: nav; church switcher (only with 2+ churches, app.py:344); Gmail section (345); a divider with the caption "Signed in as {email} · {church}" and "Log out" (346-350); then, on the Service Builder page only, "Service archive" (520-543).
  - Session defaults are set at app.py:111-145. `docx_bytes` and `service_date` (114-119) are never read.
- **Reuses:** `db.init_db` (backend/db/engine.py:60-63). The FastAPI lifespan already calls it (backend/api/main.py:24-31).
- **Role:** member of at least one church. Users with no church get onboarding and no nav (app.py:340-342).
- **Notes:** the role is re-derived on every rerun. The React header already has the switcher and account menu (frontend/src/components/app-header.tsx:30-87). The home page shows placeholder cards (frontend/src/app/page.tsx:102-130).
- **Tests:** backend/tests/test_api_app.py (health, error shape, CORS, lifespan warning, API does not import streamlit).

**A2. Login gate and user upsert**
- **What it does:**
  - `require_login` (streamlit_auth.py:16-41) runs on every rerun. When signed out it shows "Please sign in with Google to continue." and a "Sign in with Google" button that calls `st.login`, then `st.stop()`.
  - When signed in it calls `auth.upsert_from_claims` (backend/auth.py:23-60). That function normalizes the email (strip, lower), inserts the user or updates `google_sub`/`name`/`picture` when they are truthy, and always stamps `last_login_at`. A missing email raises `ValueError('OIDC claims are missing an email address.')`.
  - API equivalent, already built: `get_current_user` (deps.py:51-72). It verifies the Supabase JWT (RS256/ES256, 30 s leeway, `app_metadata.provider == 'google'`, backend/api/security.py:58-101), maps claims with `sub=None` (security.py:104-122) and upserts on every request. JWKS outage → 503 "Sign-in is temporarily unavailable. Try again shortly." A missing email → 401 "Please sign in."
- **Role:** none (this is the gate).
- **External:** Google OIDC through Streamlit `[auth]` secrets, with redirect `<app>/oauth2callback`. Supabase Auth JWKS on the new stack.
- **Edge cases:**
  - An upsert on every rerun or request makes `last_login_at` mean "last seen" and turns every API call into a write transaction.
  - First-request race: two concurrent first requests for a new email both INSERT. The second hits `users.email` UNIQUE and raises `IntegrityError`, which is not caught (deps.py:63-66), so the client gets a 500. This can happen today: React StrictMode in dev runs the `/me` effect twice (frontend/src/app/page.tsx:71-89).
  - The API never writes `google_sub`. Users are matched by email only.
  - `repos/users.upsert_user` (users.py:25-57) duplicates the upsert with different overwrite rules (it overwrites when a value is not None) and is called only from tests.
  - `streamlit_auth.current_user_id` (44-55) is dead code.
  - `name` and `picture` come from Supabase `user_metadata`, which the user can edit. They are shown to other members.
- **Tests:** test_auth.py, test_users_repo.py, test_api_me.py (including `test_me_matches_existing_streamlit_user_by_email`), test_api_security.py.

**A3. Query-param capture (`?invite=`, `?church=`) and OAuth param cleanup**
- **What it does:**
  - `capture_query_params` runs on the first line of `main()` (ui_helpers.py:10-18, app.py:325). It copies `?invite=` into `pending_invite_code` and `?church=` into `active_church_id`. A missing param never erases an earlier value.
  - `clear_oauth_query_params` deletes only the OAuth keys `code, state, scope, authuser, hd, prompt, gmail_oauth` (ui_helpers.py:7, 21-25).
  - The one blanket `st.query_params.clear()` runs after a successful invite join (app.py:294).
- **Role:** none (runs before the gate).
- **Edge cases and bugs, do not port:**
  - `?church=` stays in the URL and is re-applied on every rerun, which overrides the switcher.
  - A captured invite is silently ignored for users who already have a church.
  - No invite URL is generated anywhere.
  - Google's `?error=access_denied` is not handled.
  - The Gmail redirect lands at the bare root in a new tab, which is a new session.
- **Tests:** streamlit_tests/test_app_helpers.py (3 tests).

**A4. Active-church resolution and zero-church routing**
- **What it does:**
  - `require_active_church` (streamlit_tenancy.py:64-88) validates `session['active_church_id']` with `tenancy.validate_active_church` (backend/tenancy.py:33-54). That function coerces the id to a UUID, requires a membership in a church that is not soft-deleted, and re-derives the role.
  - On failure it falls back to `list_user_churches(user_id)[0]`. That list is ordered by church name (repos/churches.py:44-52), so the fallback is the alphabetically first church.
  - With no churches it clears state and returns None, and `main()` then renders onboarding. On success it writes id, name and role back to session.
  - API: `require_church` returns 403 "You don't have access to this church." when the header is missing, malformed, not a membership, or points to a deleted church.
  - Frontend: `pickActiveChurch` picks the stored id if the user is still a member, else the first church (frontend/src/lib/church.ts:11-13). The choice is confirmed with `GET /church` and stored in localStorage `activeChurchId`.
- **Role:** signed in.
- **Edge cases:**
  - When Streamlit falls back to another church it does not clear the old church's state; `clear_all_church_state` runs only at zero churches (streamlit_tenancy.py:72-81). The cached hymnal, archive and liturgy carry over.
  - Parity gap: on a 403, React clears the choice and shows the toast "You no longer have access to that church. Pick another." (page.tsx:59-63) but does not pick another church.
  - A forged or malformed id returns None and never raises.
- **Tests:** streamlit_tests/test_streamlit_tenancy.py, backend/tests/test_tenancy.py, test_api_me.py (the church cases), frontend/src/lib/church.test.ts, latest.test.ts.

**A5. Church switcher**
- **What it does:** `render_church_switcher` (app.py:239-256) calls `list_user_churches` on every rerun and returns early with fewer than 2 churches. It shows a sidebar selectbox "Church" whose options are church names (`{name: id}`, key `church_switcher`). A change pops `CHURCH_SCOPED_SESSION_KEYS` (app.py:221-236), sets `active_church_id` and reruns.
- **Role:** member of 2 or more churches.
- **Edge cases:**
  - Bug: keyed by name, so churches with the same name collapse into one entry (app.py:246).
  - The switcher is reachable only through data created outside the UI. Onboarding only runs at zero churches, so nobody can join or create a second church.
  - React already keys the switcher by id and drops stale responses (app-header.tsx:37-56, frontend/src/lib/latest.ts).
- **Tests:** test_streamlit_tenancy.py, streamlit_tests/test_selectbox_safety.py.

**A6. Logout**
- **What it does:** "Log out" (key `logout_btn`, app.py:349). `do_logout` runs `clear_all_church_state` and then `st.logout()` (streamlit_auth.py:58-67), which clears the app cookie but not the Google session. React already does `storeChurchId(null)` + `supabase.auth.signOut()` + `router.replace('/login')`, and treats any 401 as sign-out (page.tsx:32-44).
- **Edge cases:** zero-church users have no logout button in Streamlit, because the sidebar block comes after the onboarding return. React must also clear its query caches on logout.

**A7. Church-scoped session reset (cross-cutting)**
- There are two reset lists and they disagree:
  - app.py:221-231, used by the switcher, includes `bible_translation`, `active_hymnal`, `selected_ot_ref`, `selected_nt_ref`, and the dead keys `open_man`, `resp_man`, `close_man`, `_hymn_title_to_info`.
  - streamlit_tenancy.py:13-36, used for logout and zero churches, has different dead keys (`opening_man`, `response_man`, `closing_man`) plus the `liturgy_` prefix. The prefix also pops the reading-set radio key `liturgy_selector`.
- Neither list resets:
  - Output state: `docx_bytes_secretary`, `docx_bytes_pastor`, `email_recipients`, `secretary_email_extra`, `email_message`.
  - Draft fields: `sermon_title`, `occasion`, `scriptures_text`, `scripture_full_texts`.
  - Lectionary and date state: `lectionary_readings`, `lectionary_readings_list`, `last_lectionary_date`, `service_date_picked`.
  - Inputs: `extra_scripture`, `custom_label`, `custom_text`, `custom_place`, `translation_picker`, `select_ot`, `select_nt`.
  - The Settings `prompt_*` widget keys, and the auto-keyed checkboxes (exclude-recent, the section ticks).
- Consequence: a Word file prepared for church A can be downloaded or emailed while church B is active, using church B's contact list, with the filename and subject rebuilt from the current date (app.py:1072, 1124).
- **React rule:** key the whole builder draft, prepared documents, email form and query caches by church id; reset on switch; drop in-flight responses with `createLatestTracker`.

### B. Onboarding

**B1. Join a church by invite code**
- **What it does:** `render_onboarding` (app.py:269-298):
  - Title "Welcome to Worship Service Builder" and caption "Signed in as {email}. You don't belong to a church yet."
  - With a captured code, an info box: "You opened an invite link. Review and accept it below."
  - Tabs "Join a church" / "Create a church". The Join tab has an "Invite code" field prefilled with the captured code and a "Join church" button.
  - `pick_invite_code` (ui_helpers.py:50-55) uses the typed value if it is not blank, otherwise the captured code (both stripped). Empty → "Enter an invite code, or open your invite link again."
  - It then calls `accept_invite(code, user_id)` (backend/repos/invites.py:66-109). Any exception is shown as `str(e)`.
  - On success: pop the captured code, clear all query params, rerun. The success text is never seen.
  - On failure: `msg or 'That invite code is not valid.'`
- **`accept_invite` checks, in order:**
  1. Unknown code → "Invalid invite code."
  2. Revoked → "This invite has been revoked."
  3. Expired (naive timestamps treated as UTC) → "This invite has expired."
  4. Email-bound and already accepted → "This invite has already been used."
  5. Church missing or soft-deleted → "This church is no longer available."
  6. Email-bound and the user's email differs (case-insensitive) → "This invite was issued for a different email address."
  7. Otherwise it adds a membership with `invite.role` if none exists (already a member → success, role unchanged). Email-bound invites get `accepted_at` stamped, even for an existing member. It returns `(True, 'Joined {name}.')`.
- Code-only invites can be reused until they expire (7-day TTL, invites.py:40-55).
- **Role:** signed in with zero churches in Streamlit. The domain function itself only needs a user.
- **Edge cases:**
  - `accept_invite` does not return the church id.
  - A concurrent double-accept by the same user hits the memberships primary key (500).
  - A bogus role stored on an invite (there is no CHECK constraint on `invites.role`) makes accept raise `IntegrityError`.
  - After the rerun the only church becomes active through the fallback.
- **Tests:** streamlit_tests/test_onboarding.py (`pick_invite_code`, accept a captured invite), backend/tests/test_invites_repo.py (all rejection paths, already-member no-op, email-bound single use, revoke scoped to church).

**B2. Create a church**
- **What it does:** form `onboard_create_church` (app.py:300-320):
  - Fields: "Church name", and "Timezone" (default `America/New_York`, help "e.g. America/New_York — drives first-Sunday and the 12-week window."). Submit is "Create church".
  - Both are trimmed and required: "Church name is required." / "Timezone is required."
  - It calls `create_church(name, timezone, owner_user_id)` (repos/churches.py:11-28), sets `active_church_id`, shows "Church created. Loading…" and reruns. Any exception → "Could not create church: {e}", with the raw text.
  - `create_church` runs in one transaction: insert the Church (settings `{}`), add an owner Membership, and `seed_church_from_catalog` (repos/hymns.py:169-193). The seed copies every `hymn_catalog` row, from every hymnal, with one ORM add per row and a single flush.
- **Role:** signed in with zero churches in Streamlit. The domain function makes the caller owner.
- **Edge cases:**
  - Timezone is free text, never validated as IANA, and never used. The help text is misleading.
  - Not idempotent: a double submit creates two churches, each with a full hymnal copy.
  - Duplicate names are allowed.
  - An empty catalog gives an empty hymnal, which shows the warning described in D1.
  - A captured invite is not cleared after a create.
- **Tests:** streamlit_tests/test_onboarding.py::test_create_church_makes_owner_and_seeds_hymnal; backend/tests/test_churches_repo.py::test_create_church_is_atomic_owns_and_seeds; test_hymns_repo.py (seed count).

**B3. How invites and church deletion affect onboarding** (see G8 and G10)
- Admins only ever see a raw code ("Invite code: `{code}`", settings.py:350). No joinable link is built anywhere.
- Deleting a church revokes its pending invites. Accepting a revoked invite fails with "This invite has been revoked.", which is checked before "This church is no longer available."

### C. Service Builder: readings

**C1. Service date and automatic lectionary load**
- **What it does:**
  - `st.date_input("Service date")` defaults to `date.today()` (server-local) with key `service_date_picked` and help "Occasion and lectionary readings load automatically for this date." (app.py:416-423).
  - `service_date_str` is `'%B %d, %Y'`, zero-padded, for example "March 01, 2026" (app.py:425).
  - When the ISO date differs from `last_lectionary_date` (app.py:429), it shows the info "Loading occasion and readings…" and a spinner, then calls `get_readings_for_date_string(service_date_str)` (app.py:434-437).
  - It stores `last_lectionary_date` and `lectionary_readings_list`.
  - If there are sets: pick the last set (`readings_list[-1]`), set `occasion = liturgical_date` and `scriptures_text` = the scriptures joined by newlines, and clear `scripture_full_texts`, `selected_ot_ref`, `selected_nt_ref` (445-455).
  - If there are none: clear the readings and blank `occasion` and `scriptures_text` (456-460), which destroys anything the user typed. It always reruns (463).
- **Where the date is used downstream:**
  - Docx title (app.py:987).
  - Archive `service_date` and `service_date_iso` (1039-1040).
  - `record_usage` (1003).
  - Email subject "Worship service — {date}" (1124).
  - File names through `safe_date` (1072).
  - The first-Sunday communion default (969-971).
  - Clearing `editing_service_id` when the date changes (1029-1035).
- **Role:** any member (the lectionary is global data).
- **External:** Lectio API `https://lectio-api.org/api/v1/readings` (15 s, not cached) and the Vanderbilt CSV `https://lectionary.library.vanderbilt.edu/calendar/{year}/?season=all&download=csv` (20 s, cached per process). A cold load can take up to about 35 s, blocking the whole page.
- **Edge cases:**
  - `st.error('Could not load lectionary: {e}')` (440) is wiped by the rerun, and the domain code returns `[]` without raising, so failures are effectively silent.
  - Every date is normalized to the Sunday on or before it, so weekday feasts (Ash Wednesday, Christmas Day on a weekday, Good Friday) cannot be reached.
  - `date.today()` is the server's date: UTC on Railway, so a US-evening user gets tomorrow.
  - Loading an archived service sets `last_lectionary_date` to suppress the auto-load (app.py:388).
- **Tests:** none.

**C2. Lectionary sourcing and merge rules** (backend/vanderbilt_lectionary.py)
- **Parsing:** tries the formats `'%B %d, %Y','%b %d, %Y','%Y-%m-%d','%m/%d/%Y','%d %B %Y'` and returns `[]` when none parse (345-354). Normalizes to the Sunday on or before (357).
- **Lectio** (`_get_readings_from_lectio`, 259-330): params `date` + `tradition=rcl`. Reads `data['data']` (empty → None). Per reading type it skips `isAlternative` and keeps the first citation (298-304). Scriptures are the non-empty ones in the order `[first, psalm, second, gospel]` (311). `calendar_date` uses `'%b %d, %Y'` (314-318).
- **Vanderbilt** (`get_readings_for_date(d)`, called with the original date, 365):
  - Computes the liturgical year from the unnormalized date with a fixed Nov 29 cutoff (25-30).
  - Downloads and parses the year CSV (147-190): finds the header line containing "Calendar Date" and "Liturgical Date", uses fixed field names, and keeps rows whose date parses.
  - Takes all rows on the exact Sunday, else the latest row on or before it (214-256).
  - `_row_to_reading` drops cells that start with "http" (193-211).
- **Merge** (368-396):
  - Neither source → `[]`.
  - No Lectio → the Vanderbilt sets.
  - Vanderbilt has one set or none → `[lectio]`.
  - Vanderbilt has more than one → keep Vanderbilt's order, but replace the first set whose name contains "passion" with the Lectio set, relabelled with the Vanderbilt name. If no set contains "passion", append the Lectio set, which then becomes the default (the last set).
- **Reading set shape:** `{liturgical_date, calendar_date, first_reading, psalm, second_reading, gospel, scriptures[]}`.
- **Edge cases:**
  - `_cache` is a process-global dict with no TTL (22). Any failure is cached as `[]` forever (163-166, 176-178), so one 403 disables Palm Sunday splitting until restart. This matters much more in a long-lived uvicorn process.
  - Year-boundary bug (verified): 2027-11-28 maps to 2026-27 while 2027-11-29 maps to 2027-28.
  - The nearest-previous fallback can return a weekday feast row, or a row from weeks earlier.
  - Sundays with several Vanderbilt rows but no "passion" get a possibly duplicate Lectio set appended.
  - Lectio alternative readings are dropped.
- **Tests:** none.

**C3. Liturgical name (occasion) derivation**
- Lectio's `dayName` wins (287-288). Otherwise `_liturgical_sunday_name` (83-144) computes Lent 1-5 and Palm Sunday, Advent 1-4, Baptism of the Lord, 2nd-9th after Epiphany, Transfiguration, Easter Sunday, and Easter 2-7.
- Otherwise the label is `f'{season} — Year {year}'` (293), or `'Sunday'` (295).
- Vanderbilt sets use the CSV "Liturgical Date" column.
- **Edge cases:** Pentecost is not labelled by the fallback. Labels are inconsistent ("in Lent" versus "of Advent"). The `year` argument is unused.
- **Tests:** none.

**C4. Multiple reading sets ("Liturgy" radio)**
- Shown only when there is more than one set (app.py:475-498). The radio "Liturgy" lists each set's `liturgical_date`, with help "This date has multiple liturgies in the RCL. Select which one to use."
- The default is the current set, else the last one. `_on_liturgy_change` (481-489) replaces `occasion` and `scriptures_text` and clears the passage texts and OT/NT picks.
- **Edge cases:** options are keyed by name, so duplicate names collapse. Switching overwrites user edits without asking. After loading an archived service the radio shows the previous date's sets.

**C5. Occasion field**
- `st.text_input("Occasion / Sunday")`, key `occasion`, help "Auto-filled from lectionary; you can edit if needed.", plus the caption "RCL: {calendar_date} — {liturgical_date}" (app.py:499-507).
- It must be created after the lectionary block (comment at app.py:411-415).
- **Used by:** AI suggestions (766), `generate_liturgy` (937), the docx title "Worship Service\n{occasion}" (worship_service.py:819), the archive (1041), and the sidebar label (540).
- **Edge cases:** no validation, so empty is allowed. Lost on date or set change. Not reset on church switch.

**C6. Scripture list (manual entry and editing)**
- `st.text_area("Scripture readings (one per line)")`, key `scriptures_text`, height 120, placeholder "Filled from lectionary for the selected date.", help "e.g. Matthew 17:1–8 — auto-filled from the lectionary; edit as needed." (app.py:510-517).
- `scriptures` = the stripped lines that are not blank (518). This list, not the lectionary object, feeds Readings, the OT/NT pickers, hymn search (673), AI suggestions (767), `generate_liturgy` (938), build_docx (988) and the archive (1042).
- **Edge cases:** no reference validation. Duplicates produce duplicate expanders. The help example uses an en dash, which bible-api may not parse.

**C7. Readings header and captions**
- Shown only when `scriptures` is not empty (app.py:548-554). Header "Readings".
- With a lectionary set the caption is "RCL: … Edit the Scripture list in the sidebar to use your own."; otherwise "Using the Scripture list from the sidebar. Edit it to add or change references."
- The copy is stale: the list is in the top row, not the sidebar. Do not port it.

**C8. Bible translation: session picker and church-default seeding**
- `scripture_fetcher.TRANSLATIONS` (26-37), in display order: web, kjv, asv, ylt, dra, darby, bbe, oeb-us, webbe (bible-api), and esv (ESV API). `available_translations()` (48-55) hides esv unless `ESV_API_KEY` is set.
- Seeding (app.py:371-377): if missing, `bible_translation = get_church_translation(church_id) or 'web'`. If the value is not available, it is forced to 'web'.
- Picker (556-577): selectbox "Bible translation", key `translation_picker`, help "Used for the passage text shown below. This is study text only — the bulletin lists the references, not the verse text." A change sets `bible_translation`, clears `scripture_full_texts` and reruns. Caption: "Passage text shown in **{label}**."
- The per-session choice is never saved, not even in the archive. It also controls the passage-text fetch used by AI suggestions (770-772).
- **Role:** member for the picker. The church default is admin-only (G3).
- **Edge cases:** the church default is read once per session, so a change in Settings does not reach an open builder. `translation_picker` is not reset on church switch.
- **Tests:** backend/tests/test_scripture_translations.py (ESV gating, labels, routing), test_church_settings.py.

**C9. Load full passage text**
- Button "Load full text for all readings" (app.py:579). Under the spinner "Fetching passage text…" it fetches each reference sequentially, skipping cached ones unless the cached value is the sentinel `[Could not load text]` (583-584). It stores the text or the sentinel and reruns.
- Each reference gets a collapsed expander. It shows the text with `st.text`, or the caption "Click “Load full text for all readings” to fetch text." There is no per-reading fetch.
- `fetch_passage` (scripture_fetcher.py:143-182):
  - `' or '` alternatives are fetched recursively and joined as `--- {alt} ---\n\n{text}`.
  - Otherwise the reference is split on `;`. A book name is carried into parts like `3:1-7` (124-140).
  - Parts are routed by source. bible-api: `GET https://bible-api.com/{ref lowercased, %20}?translation=` with a 15 s timeout (65-84). ESV: `GET https://api.esv.org/v3/passage/text/` with `Token` auth, headings, footnotes, verse numbers and references off, and the short copyright on (87-113).
  - Every exception is logged and becomes `None`.
- **External:** bible-api.com (free, rate-limited by IP); api.esv.org (key required; Crossway terms limit caching).
- **Edge cases:**
  - The worst case is many sequential 15 s calls.
  - URL encoding is minimal, so en dashes, "9a"/"9b" verse parts and parentheses may fail.
  - The `' or '` split is case-sensitive.
  - The sentinel string leaks into domain code (worship_service.py:433).
  - `build_docx` accepts `scripture_full_texts` but never uses it (worship_service.py:794).
- **Tests:** test_scripture_translations.py (routing only).

**C10. OT/NT reading selection**
- `_expand_ref_options` splits `' or '` (app.py:79-87). `_is_nt_ref` matches `_NT_BOOKS` exactly or by prefix, longest names first (70-76, 90-97). Everything else is OT, including Psalms and unknown text (100-102).
- Selectboxes "Use as Old Testament reading" (key `select_ot`) and "Use as New Testament reading" (key `select_nt`) show "— Select —" for empty. The choice is written back to `selected_ot_ref` / `selected_nt_ref` (598-631).
- **Used by:**
  - The docx: the OT reading is `selected_ot_ref or scriptures[0]` and the NT reading is `selected_nt_ref or scriptures[1]` (worship_service.py:874-886).
  - AI suggestions, which also have a second, substring-based NT heuristic (worship_service.py:436-445).
  - The archive.
- **Edge cases:**
  - In RCL order, with no NT pick, the Psalm prints as the "New Testament Reading".
  - Abbreviations such as "Matt" or "Rom" are classified as OT.
  - Stale `select_*` widget values can survive a reset.
- **Tests:** none.

### D. Service Builder: hymns

**D1. Hymnal load, cache, refresh, empty warning**
- `list_hymns(church_id)` (repos/hymns.py:34-42) loads every hymnal of the church, ordered by number then title, as flat Notion-style dicts (20-31). It runs once per session under the spinner "Loading this church's hymnal…" and is cached in `_cached_all_hymns` (app.py:636-646).
- On error: "Could not load hymns: {e}. Click **Refresh hymn list** to retry." The empty result is cached, so there is no retry until Refresh.
- "Refresh hymn list" (key `refresh_hymns`, 723-725) is the only way to see Settings edits.
- `build_title_to_info` (ui_helpers.py:39-47) keys by lower-cased title. An empty map shows "This church's hymnal is empty. Add hymns on the **Settings → Hymns** page to enable hymn selection." (730-733) and hides search, pickers and AI.
- **Edge cases:**
  - Duplicate titles collapse, last one wins, so 34 PH1990 hymns can never be picked.
  - NULL numbers sort first on SQLite and last on Postgres.
- **Tests:** test_hymns_repo.py::test_add_hymn_maps_to_flat_notion_keys; test_app_helpers.py (display helpers).

**D2. Hymnal switcher**
- `hymnals_present` = sorted distinct `Hymnal` values (app.py:650). With more than one, a selectbox "Hymnal" (key `active_hymnal`, help "Which hymnal to choose hymns from for this service.") filters the list in memory (651-663). The default is alphabetical (GG2013 before PH1990).
- **Edge cases:**
  - Not saved with the service.
  - A same-title pick silently rebinds to the other hymnal's number.
  - Search results are not cleared on switch.
  - Settings "Add hymn" always writes GG2013 (repos/hymns.py:64), so a PH1990-only church that adds one hymn suddenly gets a switcher.
  - `list_church_hymnals` and the hymnal filter in `list_hymns` exist, but the UI does not use them.
- **Tests:** test_hymnals.py.

**D3. "Find hymns matching any of the scriptures"**
- Expander (expanded) with "Additional scripture (optional)" (placeholder "e.g. Matthew 17 or Psalm 99", key `extra_scripture`) (app.py:666-672).
- The references are the scripture lines plus the extra one. With none: "Enter scripture readings above, or add one in the field above."
- Otherwise, under "Searching hymnal…", it calls `hymns_by_scripture(None, ref, limit=50, all_hymns=all_hymns)` per reference and dedupes by id in first-seen order (681-688). No match: "No hymns in your hymnal matching those references. Try shorter refs (e.g. 'Matthew 17')." (691), and old results stay.
- Rendering: caption "Matching: …", the first 20 results as `[#{num} — {title}]({link}) · [▶ listen]({link})` or plain text. `num or '—'`. Then the Hymnary.org credit and copyright caption (697-714). Results are read-only: there is no way to assign one to a slot.
- **Edge cases:**
  - Stale results persist.
  - Titles and links are inserted into markdown unescaped, and titles are member-editable.
  - PH1990 has no scripture refs, so it never matches.
- **Tests:** none.

**D4. Scripture-matching engine** (worship_service.py:161-361)
- `' or '` alternatives are expanded. Variants come from `_scripture_search_variants` (234-284): the original; book + chapter; chapter:verses with any a/b suffix removed; the first verse; and the first two abbreviations from `_BOOK_ABBREVS` (162-231) plus the rest.
- A hymn matches when its "Scripture References" contains any variant as a case-insensitive substring. The pool is walked in list order until the limit.
- With `all_hymns=None` the old Notion path runs and crashes when `db=None`.
- **Edge cases:**
  - Over-matching (verified, see section 0).
  - No reverse abbreviation: "Matt 17" does not find "Matthew 17", and "Psalm 99" does not find "Psalms 99".
  - With `;` references, only the first chapter gets variants.
- **Tests:** none.

**D5. "Exclude hymns used in the last 12 weeks"**
- A checkbox, default off, with no explicit key (app.py:718-722).
- When checked, `get_recently_used_identifiers(church_id, 12)` (hymn_usage.py:50-61) returns the `(number, lower(title))` pairs with `date_iso >= UTC today - 12 weeks`, with no upper bound. It is queried on every rerun. Matching titles are removed from the pickers only, with the caption "Hymns used in the last 12 weeks are excluded ({n} excluded)." (735-746).
- **Edge cases:**
  - Confirmed bug: Prepare records the picks, then reruns; the picks are now excluded, and `safe_hymn_selectbox` silently resets them to '' (259-266). The next Prepare or Save therefore gets no hymns. The same filter drops a loaded service's own hymns.
  - AI candidates and search results ignore the filter, and an AI-applied recent hymn is silently cleared.
  - The window uses UTC, not the church timezone.
  - Usage has no hymnal dimension.
- **Tests:** test_hymn_usage.py (church scoping, window).

**D6. Opening / Response / Closing pickers**
- An `@st.fragment` with three columns (app.py:826-845):
  - "Opening" / "Gathering / call to worship" / "Opening hymn" (key `opening`)
  - "After sermon" / "Response to scripture (NT reading)" / "Response hymn" (key `response`)
  - "Closing" / "Joyful / sending" / "Closing hymn" (key `closing`)
- Options are `[''] + titles_sorted` (lower-cased title keys). The label shows the title with no number (748-751). Stale values are coerced to '' before render.
- `hymns_ordered` (847-851) is the list of filled slots, in order, with empty slots dropped.
- **Used by:** `generate_liturgy` (hymns[0] becomes `{opening_hymn}`), build_docx ("First/Second/Third Hymn" by position), the archive snapshot `{title, number}`, and `record_usage`.
- **Edge cases:**
  - Positional bug: with no opening hymn, the response hymn prints as "First Hymn", becomes `{opening_hymn}`, and reloads into the Opening slot.
  - Duplicate titles cannot be told apart.
  - The same hymn can be used in several slots.
- **Tests:** streamlit_tests/test_selectbox_safety.py.

**D7. AI hymn suggestions ("Suggest hymns (AI)")**
- **Button:** key `suggest_hymns_btn`, help "Use AI to suggest opening (gathering), response (scripture-based), and closing (joyful) hymns.", shown only when there are titles (app.py:753-757). There is no upfront key check.
- **Call:** `st.progress(0, 'Starting…')`, then `suggest_hymns_for_service(db=None, occasion, scriptures, selected_nt_ref, scripture_full_texts, scripture_text_fetcher=lambda ref: get_passage_text(ref, session translation), limit_per_slot=5, progress_callback, all_hymns=<selected hymnal, not filtered by recent use>)` (758-776).
- **Domain steps** (worship_service.py:380-579):
  1. A non-ASCII key raises `ValueError` ("…Re-paste it in Settings → Secrets."). No key or no openai package → empty slots.
  2. 0.02 "Preparing scripture text…": NT text from the cache, else a synchronous fetch with errors swallowed. The sentinel is removed.
  3. 0.1 "Using cached hymn list…".
  4. 0.15-0.40 "Searching hymns for {ref}…": `hymns_by_scripture(limit=30)` per reference or alternative.
  5. Candidates: Theme keyword sets for opening and closing (364-377), else `all_hymns[:80]`. Response = the scripture matches, else `all_hymns[:80]`. Each list is capped at 60 in the prompt.
  6. 0.45 "Building prompt for AI…".
  7. 0.55 "Calling AI to select hymns…": `chat.completions.create(model=OPENAI_MODEL or 'gpt-3.5-turbo', temperature=0.3)`. No timeout, no max_tokens, no JSON mode. Markdown fences are stripped, then `json.loads`. Any exception → empty slots.
  8. 0.9 "Applying suggestions…": each title resolves by exact lower-cased title, else by the first substring match in either direction.
- **Back in app.py:** only the first suggestion per slot is applied, through `_find_key` (781-806). The message is "AI suggestions applied: **Opening**: X | **Response**: Y | **Closing**: Z", or "AI could not match any suggestions to your hymn list. Try different scriptures or check the logs.", or "Could not suggest hymns: {e}". It is shown as a warning when it contains "could not", else success (808-824).
- **External:** OpenAI (shared key); bible-api or ESV when the NT text is not preloaded.
- **Edge cases:**
  - Every failure (no key, upstream error, bad JSON) shows the misleading "could not match".
  - The OpenAI SDK defaults (about 600 s read timeout, 2 retries) mean a request can hang for minutes.
  - PH1990 candidates are hymns #1-60, which are all Advent hymns.
  - The fuzzy resolve can pick the wrong hymn.
  - The non-ASCII-key message leaks configuration detail to members.
- **Tests:** none.
- **Amendment 2026-09-26 (PR #4):** steps 5 and 7 changed. Candidates are now ranked by the church's rubric and cut to 60 with places kept for newer hymns, the fixed "ROLE REQUIREMENTS" text is replaced by the rubric's slot checklists, each candidate line shows its year and hymnal count, and `app.py` passes `rubric=get_church_rubric(church_id)`. See D10. Tests now exist: backend/tests/test_suggest_hymns.py and test_hymn_ranking.py.

**D8. Hymn display, numbers, Hymnary links, dead audio**
- `hymn_display_info` (worship_service.py:582-609) is used for search results and AI. It returns title (not stripped, "Unknown" if missing), number, link, and `audio_url`, always built from the GG2013 CDN pattern (612-629).
- `hymn_display_from_flat` (ui_helpers.py:28-36) is used for pickers, docx, archive and usage. It returns title (stripped), number, link.
- `resolve_hymnary_audio_url` (632-683) and its unbounded cache keyed by number (28) are dead: nothing passes `resolve_audio=True`.
- Links come from the catalog, or from the import pattern `https://hymnary.org/hymn/{HYMNAL}/{n}`.
- **Edge cases:** the docx prints `'{title} — #{number}'`, which becomes `#None` for a hymn without a number (worship_service.py:847/906/933). `hymnary_link` is member-editable, so its scheme must be validated before it is rendered as an href.
- **Amendment 2026-09-26 (PR #4):** `hymn_display_info(hymn, *, resolve_audio=False, prefer_before_year=None)` (worship_service.py:628) also returns `year` (Text Year), `hymnal_count` and `newer_than_preferred` (true only when the year is known and `>= prefer_before_year`). The AI path passes the rubric's year; the Streamlit UI shows none of the three yet. `_hymn_to_dict` (repos/hymns.py) exposes the new columns as `"Text Year"` and `"Hymnal Count"`.

**D9. Manual hymn entry fields (`*_man`): removed**
- Commit 527ddb5 removed them in favor of the empty-hymnal warning. Only key names remain in the reset lists (app.py:224; streamlit_tenancy.py:25-27). Do not port unless the product owner asks for free-text hymns (see question 13).

**D10. Service rubric in hymn suggestions (amendment 2026-09-26, PR #4; no new screen)**
- **Rubric** (`backend/service_rubric.py`): `DEFAULT_RUBRIC` holds a checklist per hymn slot (`HYMN_SLOTS` = opening, response, closing, labelled by `HYMN_SLOT_LABELS`), a checklist per liturgy section (the 8 `SECTION_ORDER` keys), `prefer_before_year` (default 1970) and `prefer_familiar` (default true). `merge_rubric(overrides)` applies a church's valid sparse overrides and silently ignores unknown keys and invalid stored values, so a bad stored value never breaks suggestions or generation. Storage and editing: G11.
- **Hymn facts:** nullable integer columns `text_year` (year the words were written) and `hymnal_count` (hymnals that include the text; the familiarity signal) on `hymns` and `hymn_catalog` (db/models.py). `seed_church_from_catalog` copies them. They are filled only by the ops backfill (H14); hymns added later (Settings "Add hymn", `import_hymnal.py`) start unknown (`NULL`).
- **Ranking** (`backend/hymn_ranking.py`, pure; used by `suggest_hymns_for_service`, worship_service.py:389):
  - `rank_candidates(hymns, *, prefer_before_year, prefer_familiar)`: a stable sort, first by era (words written before the year, then unknown, then newer), then, when `prefer_familiar` is on, by `hymnal_count` descending, where an unknown count ranks as the median of the known counts in that list.
  - `shortlist(ranked, *, limit, prefer_before_year, reserve)`: cuts to `limit` in ranked order, keeping up to `reserve` places for the best unknown-year and newer hymns (taken from each group in turn); unused reserved places go back to older hymns. The suggester uses `_CANDIDATES_PER_SLOT = 60` and `_CANDIDATES_KEPT_FOR_NEWER = 12` (worship_service.py:374-375).
  - Each slot's list is ranked then shortlisted: opening and closing from the theme-matched hymns, response from the scripture matches. A slot with no matches falls back to the **whole ranked hymnal** cut the same way (was `all_hymns[:80]`). The theme keyword sets `_OPENING_THEMES` / `_CLOSING_THEMES` (worship_service.py:367-368) still pre-filter opening and closing; they match the default checklists, not an edited one (a known limit in the rubric spec).
  - For a hymnal with no facts and no themes (PH1990 today), ranking is a no-op, so the D7 edge case "PH1990 candidates are hymns #1-60, all Advent" still holds.
- **Prompt:** the fixed ROLE REQUIREMENTS text is replaced by the three slot checklists (`format_checklist("Opening (Gathering) Hymn", …)` → "A good Opening (Gathering) Hymn:" plus one "- point" per line), followed by `PREFERENCES: Prefer hymns written before {year}[ and hymns found in many hymnals]; choose a newer hymn only when it fits clearly better. Each candidate shows when its words were written and how many hymnals include it, when known.` (worship_service.py:531-551). Each candidate line gains `hymn_ranking.facts_note`, for example `(written 1826, in 1,322 hymnals)`, when either fact is known.
- **Call site:** app.py:768-780 passes `rubric=get_church_rubric(church_id)`, read on each click.
- **Tests:** backend/tests/test_service_rubric.py, test_hymn_ranking.py, test_suggest_hymns.py, test_hymns_repo.py (facts mapping and seeding).

### E. Service Builder: liturgy

**E1. Sermon title**
- `st.text_input("Sermon title (for bulletin)", key="sermon_title", placeholder="[Sermon title]")` (app.py:854).
- Not sent to the AI and not previewed. Used by build_docx, which prints "[Sermon title]" when blank (worship_service.py:889-894), and by the archive.
- Restored on load (392). Not reset on church switch.

**E2. "Your text (optional — leave blank to generate)" overrides**
- Expander with eight text areas keyed `liturgy_<section>`, 80 px tall (140 for Prayers of the People), placeholder "Leave blank to generate with AI" (app.py:856-875). Labels: Call to Worship, Opening Prayer, Prayer of Confession, Assurance of Pardon, Prayer for Illumination, Prayers of the People, Offertory Prayer, "Benediction (default: Halverson)".
- On Generate, values are stripped, blanks dropped, and passed as `user_overrides` (930-934). They are used verbatim, but only for sections that are also ticked (worship_service.py:735-738). The generated result is never written back into these boxes.
- Loading an archived service writes the saved text into all 8 boxes (app.py:397-400). A later Generate then only calls the AI for blank sections.
- This is the only way to edit liturgy text today.
- **Edge cases:**
  - Override text for an unticked section is silently ignored.
  - With no usable OpenAI client, `generate_liturgy` returns placeholder text for every section and discards the overrides (708-724).
  - The UI blocks Generate entirely without `OPENAI_API_KEY`, even when every section has override text (app.py:927-928).

**E3. Benediction default "Halverson"**
- `DEFAULT_BENEDICTION = "Halverson"` (app.py:67) is seeded whenever the key is missing (136-137), including after a church switch.
- The benediction is therefore an override and not AI-written by default. The literal word "Halverson" prints in the preview and the docx.
- The AI benediction prompt (liturgy_prompts.py:113-118) runs only if the box is cleared. Loading a service with no benediction blanks the box.

**E4. "Liturgy to generate" section ticks**
- Eight keyless checkboxes (app.py:877-895). All default on except Prayers of the People.
- Not saved or scoped. Generation replaces the liturgy dict wholesale, so unticked sections disappear. With all unticked the result is `{}`: the success message still shows, but Preview, Prepare and Save are hidden.

**E5. Custom elements (e.g. Children's Moment)**
- Expander "Add custom element (e.g. Children's Moment, anthem)" with the caption about the Word doc. Fields: Label (`custom_label`), Text (`custom_text`), "Place after" (`custom_place`) over the 17 `CUSTOM_PLACEMENTS` (app.py:148-166, 897-924).
- "Add custom element" appends `{label, text, insert_after}` only when the label is not blank, silently otherwise. The inputs are not cleared.
- Each element shows as "**{label}** — placed after {placement}" with a "Remove" button (`rm_custom_{i}`).
- build_docx emits each one as a Heading 2 label, the text if present, and a blank line at its anchor (worship_service.py:769-780).
- **Edge cases:**
  - Not archived: `save_kw` has no custom elements (app.py:1038-1049) and the Service model has no column.
  - Loading a service does not clear them, so they carry over into the loaded service.
  - Anchors are emitted even when the anchoring section is absent.
  - An unknown `insert_after` makes `next()` raise `StopIteration` (920).
- **Tests:** test_streamlit_tenancy.py (custom elements are church-scoped).

**E6. Generate liturgy (OpenAI)**
- **Button:** primary "Generate liturgy". Without the env key: "Set **OPENAI_API_KEY** in `.env` to generate liturgy." (app.py:926-928).
- **Call:** otherwise, under "Writing liturgy…", `generate_liturgy(occasion, scriptures=<all lines>, hymns=hymns_ordered, sections, user_overrides, prompt_overrides=get_church_prompts(church_id))` (936-943). Church prompts are read fresh on each click.
- **Result:** replaces `session.liturgy`, then "Liturgy generated. Review below and download Word." (visible). The call is not wrapped in try/except.
- **Domain** (worship_service.py:686-766):
  - `merge_prompts(overrides)`.
  - A non-ASCII key gives an error string for every section; no key gives "[Configure OPENAI_API_KEY to generate {s}.]" for every section.
  - Hymn lines are `- {title} (#{number})`. Scripture lines are `- {ref}`, or "None specified.". `opening_hymn` = `hymns[0].title` or "N/A".
  - Per section, in order: an override is used verbatim; no template gives ''; otherwise `render(template)` is sent to `chat.completions.create(model=OPENAI_MODEL default 'gpt-3.5-turbo', system+user, max_tokens=1024)`.
  - Calls are sequential: 6 by default. There is no explicit timeout.
  - A per-section exception becomes the section text `[Error generating {section}: {e}]`.
- **External:** OpenAI, shared key, no rate limit.
- **Edge cases:**
  - `render` runs outside the try block, so a malformed admin template crashes the whole generation (section 0, item 4).
  - `(#None)` appears in `{hymns}` for a hymn without a number.
  - `max_tokens=1024` can truncate Prayers of the People.
  - Reasoning models set through `OPENAI_MODEL` may reject `max_tokens`.
  - Raw provider errors are shown and can be saved or printed.
  - Messages mention "Settings → Secrets" and `.env`, which do not apply on Railway.
- **Tests:** test_liturgy_prompts.py (merge and render only).
- **Amendment 2026-09-26 (PR #4):** the call (app.py:941-956) also passes `rubric=get_church_rubric(church_id)` and `sermon_text=sermon_text_for(...)`, and each generated section's prompt gains the rubric checklist and the sermon-text themes. See E9. Tests now exist: backend/tests/test_generate_liturgy.py.

**E7. Preview (read-only)**
- Shown when the liturgy is not empty (app.py:947-966). For each of the 8 sections with text: subheader, `st.text` (monospace, no markdown), divider. Assurance gets "\n\nPeople: Thanks be to God! Amen." appended.
- Omits hymns, readings, sermon title, the Affirmation of Faith, communion and custom elements, all of which are in the docx.
- Docx formatting to mirror (worship_service.py:44-75, 148-158):
  - Call to Worship is split on Leader:/People: markers, with People lines bold.
  - Confession is entirely bold.
  - Assurance gets "Leader: " prepended (any leading one stripped first) plus a bold "People: Thanks be to God! Amen.".
- **Edge cases:** error placeholders are previewed as if they were liturgy. Legacy Notion-era dicts may use other keys, so the preview is blank while the liturgy counts as present.

**E8. Communion toggle**
- `is_first_sunday = day <= 7 and weekday == Sunday` for the picked date, set only when the key is absent (app.py:968-971).
- Checkbox "Include communion liturgy (The Sacrament of the Lord's Supper)", key `include_communion`, help "Checked by default on the first Sunday of the month."
- When on, build_docx inserts a static communion text after the Second Hymn (worship_service.py:78-145, 910-913).
- Archived and restored.
- **Edge cases:** the default does not update when the date changes afterwards; it ignores church timezone; the text is not per church and not previewed.
- **Tests:** test_service_archive.py (persisted).

**E9. Rubric checklists and sermon-text themes in the liturgy prompts (amendment 2026-09-26, PR #4; no new screen)**
- `generate_liturgy(..., rubric=None, sermon_text=None)` (worship_service.py:762). `rubric` is merged over the defaults (`service_rubric.merge_rubric`), so `None`, sparse overrides and a full rubric all work.
- For each section it sends to the AI, after `render()`, it appends in code (not as template placeholders, so churches with edited prompts get them too):
  1. the section's checklist, `service_rubric.format_checklist(SECTION_LABELS[section], rubric["prayers"][section])` → "A good {Section Label}:" plus one "- point" line per item (worship_service.py:836-839);
  2. when `sermon_text` is given, `_sermon_text_block` (worship_service.py:747): "Sermon text ({ref}), for themes only; do not quote, cite, or name it:" then the text cut to `SERMON_TEXT_LIMIT = 2000` characters. It is skipped when the reference or text is blank or the passage failed to load (`"[Could not load text]"`).
- Override (typed) sections are never sent, so neither block touches them.
- **Sermon text source:** `ui_helpers.sermon_text_for(ref, cached_texts, fetch)` (ui_helpers.py:100) takes `st.session_state["selected_nt_ref"]` and the passage already loaded on the page (`scripture_full_texts`); when it is missing or failed, it fetches with the session's Bible translation (including ESV) and keeps a successful fetch in the session cache. A failed or empty fetch is logged and yields `None`, so generation never breaks on it.
- **Default prompt changes:** `prayer_for_illumination` now says "Write no more than 3 sentences" (was 3-5) and `offertory_prayer` "No more than three sentences" (was three to five), matching their checklists' "is no more than 3 sentences" (liturgy_prompts.py).
- **Tests:** backend/tests/test_generate_liturgy.py (default and church checklists, partial rubric, edited prompts, sermon text appended, truncated and skipped, typed sections never sent), test_liturgy_prompts.py (the two defaults), streamlit_tests/test_app_helpers.py (`sermon_text_for`).

### F. Output: documents, usage, archive, Gmail, email

**F1. Prepare bulletin copy and pastor's copy**
- Shown when the liturgy is not empty (app.py:978-1028). Buttons "Prepare bulletin copy" (`prep_sec`) and "Prepare pastor's copy" (`prep_pastor`, help "Full order of worship, including sermon and Prayers of the People.").
- Both call build_docx with occasion, `service_date_str`, scriptures, `hymns_ordered`, liturgy, `include_placeholders=True` (unused), sermon_title, the OT/NT refs, `scripture_full_texts` (unused), `include_sermon=True`, communion and custom elements. The only difference: `include_prayers_of_the_people` is False for the bulletin and True for the pastor copy.
- Bytes go to `docx_bytes_secretary` / `docx_bytes_pastor`. When hymns exist, `record_usage` runs and its return value is ignored. Then a success message and a rerun.
- **Edge cases:**
  - Errors are not caught: a missing python-docx raises `RuntimeError`, and DB errors produce a traceback.
  - Prayers of the People only prints if it was generated, and it is unticked by default, so by default the two copies are identical.
  - Only the bulletin can be emailed.
- **Tests:** none for build_docx.

**F2. Word layout** (`build_docx`, worship_service.py:783-948)
- Times New Roman 11 pt. Centered bold 16 pt "Worship Service\n{occasion}", then a 12 pt date line and a blank line.
- Sections are Heading 2, each followed by a blank line and then any custom elements anchored after it:
  1. Call to Worship
  2. Opening Prayer
  3. First Hymn
  4. Prayer of Confession (bold)
  5. Assurance of Pardon
  6. Prayer for Illumination
  7. Old Testament Reading
  8. New Testament Reading
  9. Sermon Title, when `include_sermon`
  10. Affirmation of Faith, always "Apostles' Creed"
  11. Second Hymn
  12. Communion (Heading 1 plus fixed text), when included
  13. Prayers of the People (pastor copy, only if present)
  14. Offertory Prayer
  15. Third Hymn
  16. "Before Benediction" anchor, then Benediction, then the "end" anchor
- Returns BytesIO. Keys outside the 8 known sections are ignored.

**F3. Download prepared documents**
- Shown whenever either byte blob exists (app.py:1069-1092). `safe_date = service_date_str.replace(', ', '_').replace(' ', '_')`, for example "October_04_2026".
- Files `worship_{safe_date}.docx` and `worship_pastor_{safe_date}.docx`, with MIME `application/vnd.openxmlformats-officedocument.wordprocessingml.document`. The caption is inaccurate (section 0, item 2).
- **Edge cases:** the bytes can be stale. They survive form edits, date changes, loads and church switches, and the filename uses the current date.

**F4. Hymn usage recording**
- Recorded only on Prepare (app.py:1002-1003, 1025-1026). Not on Save, not on Email.
- `record_usage` (hymn_usage.py:64-104):
  - Parses 5 date formats and returns False if none match.
  - Skips blank titles and coerces the number to int or None.
  - SELECTs the existing `(number, title)` pairs for that date, then inserts the missing ones. The comparison uses the exact title case.
- Never removes rows, so a changed pick leaves the old hymn recorded.
- The DB unique constraint `uq_hymn_usage_dedupe` covers `(church_id, date_iso, number, title)`. NULL numbers do not collide.
- **Edge cases:** the check-then-insert pattern can race and raise `IntegrityError`. Future-dated services count as recent.
- **Tests:** test_hymn_usage.py (4 tests), test_migrate_archive.py::test_import_usage_dedupes.

**F5. Service archive list (sidebar)**
- Subheader "Service archive" (app.py:520-543). Cached in `_cached_saved_services`, from `list_saved_services(church_id)`: every row with full JSON, ordered by `saved_at` desc (service_archive.py:45-58).
- Error: "Could not load archive: {e}. Click **Refresh archive** to retry." "Refresh archive" pops the cache. Empty: "No saved services yet. Generate liturgy and click “Save this service to archive”."
- Otherwise it shows the first 20 as buttons "{service_date} — {occasion}" (help "Load this service into the form").
- There is no delete, search or paging, even though `delete_service` exists (service_archive.py:150-159).
- **Tests:** test_service_archive.py::test_list_saved_services_is_church_scoped.

**F6. Load an archived service into the form**
- Runs at app.py:379-405. `get_service(id, church_id)` (church-scoped). It restores:
  - `service_date_picked` (parse errors swallowed)
  - `last_lectionary_date`, which suppresses the auto-load
  - `occasion`, `scriptures_text`, `liturgy`, `sermon_title`, the OT/NT refs, `include_communion`, `editing_service_id`
  - all 8 `liturgy_*` boxes
  - the slots by position: `opening/response/closing = hymns[i].title.lower()`
- Then it reruns. A service that is not found is silently ignored.
- **Not restored or cleared:** the lectionary sets (the RCL caption and radio go stale), custom elements (carried over), prepared docx bytes, the passage cache, translation, hymnal.
- **Edge cases:** slots shift when the saved list was compacted. Renamed or deleted hymns are silently dropped. The exclude filter drops the service's own hymns.
- **Tests:** test_service_archive.py (get is church-scoped).

**F7. Save to archive / Save changes**
- On every rerun while editing, `get_service` checks the stored `service_date_iso`. A different date clears `editing_service_id`, which turns the next save into a new service (app.py:1029-1035).
- Label: "Save changes" when editing, else "Save this service to archive" (key `save_archive`).
- Payload (1038-1049): `service_date` (display string), `service_date_iso`, occasion, scriptures, `hymns_ordered` (snapshotted to `{title, number}`, service_archive.py:22-23), liturgy, sermon_title, the OT/NT refs, `include_communion`.
- Editing: `update_service` (full replace; bumps `saved_at`). If that returns None, it falls back to `save_service(created_by=user_id)`. Otherwise it calls `save_service` and sets `editing_service_id`.
- Messages: "Service updated in archive." / "Service saved to archive." / "Archive save failed: {e}". The cache is invalidated and the page reruns.
- **Not saved:** custom elements, translation, hymnal, reading-set choice, section ticks, the exclude flag.
- **Edge cases:** any member can overwrite any service. Last write wins.
- **Tests:** test_service_archive.py (snapshot shape; get/update/delete church-scoped).

**F8. Gmail connection status, connect, disconnect (sidebar)**
- `_render_gmail_sidebar` (app.py:198-218) renders only for users with a church.
- It pops and shows `oauth_error`. Then:
  - Not configured (needs `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `GOOGLE_OAUTH_REDIRECT_URI`, google_oauth.py:86-88): "Per-user Gmail sending isn't configured on this deployment."
  - Connected (a `gmail_tokens` row with a refresh token): "Connected: {login email}" and "Disconnect", which deletes the row.
  - Otherwise: "Connect Google to send worship emails from your own Gmail." and `st.link_button("Connect your Gmail", build_auth_url(create_state(user_id)))`. This opens a new tab and inserts a new `oauth_states` row on every render.
- Scopes are `openid`, `userinfo.email`, `gmail.send`, with `access_type=offline` and `prompt=consent` (google_oauth.py:47-51, 129-146). The state is `token_urlsafe(32)` with a 10-minute TTL (149-162).
- Tokens are scoped to the user, not the church.
- **Tests:** test_gmail_token_store.py, test_oauth_state.py, test_gmail_exchange.py::test_scopes_unchanged.

**F9. Gmail OAuth callback**
- In `main()`, after login and before church resolution: `should_handle_gmail_callback` checks that both `code` and `state` are present (google_oauth.py:190-201; app.py:334-336).
- `_handle_gmail_callback` (app.py:176-195): `consume_state` is single-use and deletes the row even when it has expired (google_oauth.py:165-187). None, or a different user, → `oauth_error = "Sign-in expired or was invalid. Please try again."`
- Otherwise `exchange_code(code, user_id)` (204-257):
  - "Sign in before connecting a Gmail account." when the user's email is unknown.
  - Token POST; on failure `Google API error {status}: {msg}`.
  - "Google did not return an access token."
  - userinfo GET; "Could not read your email address from Google."
  - Email mismatch → "That Google account doesn't match your signed-in email. Connect the Gmail account you're logged in with."
  - Save the token. With no refresh token and no existing connection: "Google did not return a refresh token. Remove this app's access at https://myaccount.google.com/permissions and connect again."
- Any exception text goes into `oauth_error`. The OAuth keys are cleared and the page reruns.
- **External:** Google token and userinfo endpoints, 30 s timeout each (up to about 60 s).
- **Edge cases:** a denied consent (`?error=` with no code) is ignored and leaves an orphaned state row. Network exceptions show raw text.
- **Tests:** test_oauth_state.py, test_gmail_exchange.py.

**F10. Email the bulletin copy**
- Shown only when bulletin bytes exist: expander "Email bulletin copy" with caption "Send the bulletin .docx and a friendly message via Gmail." (app.py:1094-1135).
- Status line: configured and connected → "Sending as **{login email}** (your connected Gmail)."; configured but not connected → warning "Connect your Gmail in the sidebar to send from your own account."; not configured → nothing.
- Inputs: multiselect "Recipients" over "Name <email>" (key `email_recipients`), "Additional emails (comma-separated)" (key `secretary_email_extra`), "Message" (key `email_message`, no default).
- "Send email" (key `send_email_sec`):
  - No recipients → "Please select at least one recipient or enter an email address."
  - Not connected → "Connect your Gmail in the sidebar first, then try again."
  - Otherwise: subject "Worship service — {date}", body `(message or 'Hi! Here’s the worship bulletin for this Sunday.').strip()`, attachment `worship_{safe_date}.docx`.
- `send_email` (google_oauth.py:304-369) takes From only from the stored `google_email`. All recipients go in one To header. Plain text body; attachment as octet-stream. It returns an error string, shown as "Email failed: {err}", or "Email sent to {n} recipient(s)."
- A 400 or 401 on token refresh disconnects the user (288-294).
- **Edge cases:**
  - The attachment can be stale.
  - With Gmail not configured, the user is told to connect, which is impossible.
  - A stale multiselect label can raise `KeyError` (1115).
  - There is no email validation or dedupe.
- **Tests:** test_gmail_exchange.py::test_send_email_refuses_when_user_not_connected. The success path and MIME composition are untested.

### G. Settings (streamlit_views/settings.py)

**G1. Page shell and permission helpers**
- Open to any member (app.py:355-362). `st.title("Settings")`, caption "{church} — you are **{role}**.", 7 tabs (settings.py:184-190).
- All DB queries run on every rerun. Timezone is read with a raw ORM session (180-182).
- Helpers re-check the role from the DB (33-55):
  - `_require_admin` → "You must be an admin to do that."
  - `_require_member` → "You are not a member of this church."
  - `_require_owner` → "Only the owner can do that."
- `get_role` does not exclude soft-deleted churches. The API must always run `require_church` first.
- The helpers are Streamlit-free, but the module imports streamlit (line 11).

**G2. Church profile (name, timezone)**
- Form `church_profile`: "Church name", "Timezone". Non-admins see "Only admins can edit the church profile." and a disabled "Save profile".
- `submit_profile_update` (61-74) requires admin and trims: "Church name is required." / "Timezone is required." / "Church not found.". It writes through its own ORM session.
- Then `submit_translation` runs in a second transaction. Success: "Profile updated.".
- **Edge cases:** not atomic; no timezone validation. `update_church(settings=…)` would replace the whole settings JSON, so do not use it for this.
- **Tests:** test_settings_profile_contacts.py, test_churches_repo.py::test_update_church_changes_profile.

**G3. Default Bible translation (inside the profile form)**
- Selectbox "Default Bible translation" (help "Default for on-screen passage text; anyone can switch it per session.") over `available_translations()`. The current value is the church default or 'web'. An unavailable stored value falls back to index 0 (198-208).
- `submit_translation` (162-168) requires admin: "Unknown or unavailable translation." Stored with `set_church_translation`, a shallow `_merge_settings` read-modify-write (repos/churches.py:87-96, 128-129).
- **Edge cases:** if `ESV_API_KEY` is removed, the next profile save silently overwrites an "esv" default with "web".
- **Tests:** test_settings_prompts_translation.py, test_church_settings.py.
- **Amendment 2026-09-26 (PR #4):** `_merge_settings` (repos/churches.py:98) now loads the church row with `SELECT … FOR UPDATE` (`_lock_live_church`, repos/churches.py:88; a no-op on SQLite) and writes a new dict in the same transaction, so concurrent Streamlit settings saves (translation, prompts, rubric) no longer lose each other's keys on Postgres.

**G4. Contacts**
- List for all members: `list_contacts`, ordered by `created_at` then name (email_contacts.py:24-37), shown as "**{name}** — {email}".
- Admins see "Delete" (`del_contact_{id}`, no confirmation, the IDOR-safe bool result is ignored) and the form "Name"/"Email" → `submit_add_contact`: "Email is required.", no format check, no dedupe, "Contact added.". Non-admins see "Only admins can add or remove contacts.".
- **Tests:** test_email_contacts.py, test_settings_profile_contacts.py.

**G5. Hymn library**
- Caption "Members may edit this church's hymnal.", then "{N} hymns." (all hymnals) and only the first 50 as "#{n or —} — {title}", each with "Delete" (286-312).
- Add form (any member): Title, Number (text; `int` only if all digits, else silently None), Scripture references.
  - `submit_add_hymn`: "Hymn title is required."; hymnal is always GG2013; "Hymn added.".
- `submit_update_hymn` exists but has no UI. `update_hymn` replaces every field (title required; omitted fields become None; hymnal cannot change) (repos/hymns.py:130-156).
- Delete: any member, no confirmation, bool ignored.
- **Edge cases:**
  - The builder's hymn cache is not invalidated.
  - On Postgres, NULL-number hymns sort last and can fall outside the first 50, so they cannot be seen or deleted.
- **Tests:** test_hymns_repo.py, test_hymnals.py, test_settings_profile_contacts.py::test_member_can_add_hymn.

**G6. Liturgy prompts (view, save, reset)**
- Caption plus `PLACEHOLDER_HELP` ("Placeholders you can use: {occasion}, {scriptures}, {opening_hymn}, {hymns}. Unknown placeholders are ignored (they render as blank).").
- Non-admins see "Only admins can edit the prompts (you can read them below)." and disabled boxes.
- Nine text areas: "Overall voice (system prompt)", then the `SECTION_ORDER` labels. Each shows the override or the default, with " • customized" when overridden. 200 px for system and Prayers of the People, 110 px otherwise; key `prompt_{key}` (218-259).
- "Save prompts" → `submit_prompts`: keeps `PROMPT_KEYS` whose stripped value is not blank and differs from the default, then `set_church_prompts` replaces `liturgy_prompts` entirely. "Prompts saved.".
- "Reset all to defaults" → `{}`, "Prompts reset to defaults.".
- **Edge cases:**
  - Malformed braces are accepted on save and crash generation later.
  - Streamlit keyed text areas can show stale text after a save, reset or church switch.
  - No length limits.
- **Tests:** test_settings_prompts_translation.py, test_church_settings.py, test_liturgy_prompts.py.

**G7. Members (list, change role, remove)**
- Every member sees every member's name, email and role, ordered by email: "**{name or email}** ({email}) — {role}" (314-336).
- Admins get, on every row except their own, a role select [member, admin, owner] with "Update" (shown only when changed) and "Remove".
- `set_role` (repos/memberships.py:59-72): demoting an owner or admin locks the admin rows and raises `LastAdminError('Cannot demote the last owner/admin of this church.')`. A non-member target is a silent no-op. An invalid role raises `IntegrityError` from the DB CHECK.
- `remove_membership` (75-94): the same lock, with "Cannot remove the last owner/admin of this church.". It sets `services.created_by` to NULL, then deletes the membership.
- **Edge cases (verified):**
  - Any admin can grant "owner", including to themselves through a direct call. They can also demote or remove the owner while another admin remains, which can leave the church with no owner.
  - There is no "leave church" action.
- **Tests:** test_memberships_repo.py, test_settings_members_invites.py.

**G8. Invites (create, list, revoke)**
- Admin only (others see "Only admins can manage invites."). Form: "Bind to email (optional)", Role [member, admin].
- `do_create_invite` → `create_invite`: 256-bit code, 7-day TTL, lower-cased email. Shows "Invite code: `{code}`".
- The list shows active invites, newest first, as "`{code}` — {email or any} — {role}" with "Revoke" (IDOR-safe, silent no-op for other churches) (338-361). Expiry and creator are not shown.
- **Edge cases (verified):**
  - The role is not validated server-side, so an "owner" invite can be created.
  - `UniqueConstraint('church_id','email')` applies to every row (db/models.py:95), so re-inviting an email (even after revoke, expiry or acceptance) raises `IntegrityError`.
  - Code-only invites stay listed after use.
- **Tests:** test_invites_repo.py, test_settings_members_invites.py::test_admin_can_create_invite.

**G9. Transfer ownership (Danger zone)**
- Owner only; others see "Only the owner can transfer ownership or delete the church.".
- "New owner" select lists the other members; with none: "Invite another member first to transfer ownership.".
- `transfer_ownership` makes two separate `set_role` calls: target to owner, then caller to admin (130-133). Success: "Ownership transferred. You are now an admin.".
- **Edge cases (verified):** transferring to a non-member leaves the church with no owner. The two steps are not atomic.
- **Tests:** test_settings_members_invites.py::test_owner_only_transfer_and_delete (rejection path only).

**G10. Delete church (soft delete)**
- "Type the church name to confirm" (`delete_confirm`) plus the primary button "Delete church". The exact, case-sensitive comparison happens only in the render code (385); a mismatch shows "Church name did not match.".
- `delete_this_church` → `soft_delete_church`: sets `deleted_at` and revokes pending invites in one transaction (repos/churches.py:55-71). Then it pops `active_church_id`, shows "Church deleted." and reruns into the fallback church, keeping the old church's cached state.
- No restore and no hard purge.
- **Tests:** test_churches_repo.py (soft delete, revoke), test_tenancy.py::test_validate_rejects_soft_deleted_church.

**G11. Service rubric storage and API (amendment 2026-09-26, PR #4; no Streamlit screen)**
- Each church stores **only its overrides** in `churches.settings["rubric"]`, the same shape as `DEFAULT_RUBRIC` but sparse, for example `{"hymns": {"closing": [...]}, "prefer_before_year": 1960}`. A church that never edits anything picks up improved defaults automatically.
- Repo functions (repos/churches.py:129-160): `get_church_rubric_overrides(church_id)` (`{}` when none or not a dict), `get_church_rubric(church_id)` (merged), `update_church_rubric(church_id, patch)`. The update validates with `service_rubric.validate_patch`, then reads the stored overrides from the row it locks (`_lock_live_church`), applies them with `apply_patch` and writes `{**settings, "rubric": overrides}` in that transaction, so two admins patching at once cannot drop each other's change. `null` for one checklist or one setting removes that override (reset granularity is one checklist or one setting); a group left empty is dropped.
- **Validation** (`validate_patch`, raises `ValueError` with these exact messages): "The rubric update must be an object."; "'{key}' must be an object of checklists."; "Unknown {hymns|prayers} checklist: '{sub}'."; "Unknown rubric setting: '{key}'."; "A checklist must be a non-empty list of points." (an empty list is invalid; reset with `null`); "A checklist can have at most 12 points."; "Each checklist point must be non-empty text."; "Checklist points cannot contain control characters."; "Each checklist point must be at most 300 characters." (after trimming; whitespace runs, line breaks included, collapse to single spaces); "The preferred year must be between 1500 and {current year}."; "prefer_familiar must be true or false."
- **API** (backend/api/routes/rubric.py, registered in `api/main.py`; `RubricOut` in api/schemas.py): `GET /rubric` (`require_church`) returns `{"rubric": <merged>, "customized": ["hymns.closing", "prefer_before_year", …]}` (dotted names of the valid stored overrides, in rubric order, `service_rubric.customized_keys`). `PATCH /rubric` (`require_admin`) takes the sparse patch as a plain JSON object and returns the same shape; a `ValueError` becomes `ApiError(422, "invalid_rubric", <message>)` with no `fields`, and a non-object body is FastAPI's 422 `invalid_request`. The role is the one `require_admin` read; the write does not re-read it under the lock.
- **Who reads it:** Streamlit's hymn suggestions and liturgy generation (D10, E9) on every click, via `get_church_rubric`. Nothing in Streamlit writes it, and there is no editor anywhere yet; PR #4 leaves the editor to settings slice 6.
- **Tests:** backend/tests/test_api_rubric.py (member reads, non-member 403, member PATCH 403, admin and owner PATCH, reset with `null`, readable 422, non-object body, per-church isolation), test_church_settings.py (merge, isolation, locked update), test_service_rubric.py.

### H. Operations, scripts and legacy code

Each item is marked with its fate: **KEEP**, **API/UI** (needs an in-app equivalent), or **DELETE**.

| Item | What it does | Fate |
|---|---|---|
| H1 `backend/migrate_to_db.py` | One-time import from Notion and legacy JSON. Founder user, then `hymn_catalog` upsert keyed by `(number, lower title)`, then founder church (create + seed), then services (the `_sermon_title`/`_include_communion` metadata is pulled out; truncated liturgies of 1990+ characters are imported empty), then usage, then contacts. `validate_enrichment` exits with code 2 (lines 1-593). Hazards: archive pages without "Saved at" are duplicated on every re-run (178-179, 291-297); a renamed founder church creates a second church (139-142); the Notion multi-select Theme list was written into a Text column (93), which is **plausible** to have stored `{A,"B"}` literals on Postgres. | DELETE at cutover, **after** exporting `hymn_catalog` to a versioned seed file |
| H2 `backend/migrate_add_hymnal.py` | Postgres-only `ALTER TABLE … ADD COLUMN IF NOT EXISTS hymnal … DEFAULT 'GG2013'` on `hymns` and `hymn_catalog`. Does not create `ix_hymns_church_hymnal`. | DELETE once confirmed applied; replace with Alembic |
| H3 `backend/import_hymnal.py` | CLI (`--church-id`, `--hymnal`, `--csv`) with no role check. `load_rows` reads UTF-8 (a BOM breaks the "number" header), skips blank titles, falls back from theme to "topics", and builds the Hymnary link. `import_hymns` (repos/hymns.py:84-127) is idempotent per `(hymnal, int number, lower title)`, fills only non-blank enrichment fields, never deletes. The docstring path (7-8) is stale. | KEEP as CLI, plus admin **API/UI** |
| H4 `backend/keepalive.py` + `.github/workflows/keepalive.yml` | Daily `SELECT 1` against Supabase at 09:17 UTC. No secret exists yet, so it will fail. GitHub disables schedules in public repos after 60 days without activity. | KEEP; consider an off-GitHub pinger |
| H5 `.github/workflows/backup.yml` | Daily `pg_dump` to a gzipped workflow artifact kept 30 days. **In a public repo, those artifacts are downloadable by any signed-in GitHub user.** They would contain users, contacts and plaintext Gmail refresh tokens. The SQLAlchemy URL scheme `postgresql+psycopg2://` is rejected by `pg_dump`. The apt client version may not match the server. | KEEP, but fix before adding the secret |
| H6 `.github/workflows/ci.yml` | Backend: Python 3.11, `pip install -r requirements-dev.txt` (which pulls in Streamlit), pytest over `backend/tests` and `streamlit_tests`. Frontend: Node 22, lint, typecheck, vitest, build. | KEEP; update at cutover |
| H7 `.github/workflows/keep-awake.yml` | Playwright visits liturgy.streamlit.app and liturgy-stg.streamlit.app every 6 h to prevent hibernation. | DELETE at cutover |
| H8 `backend/notion_archive.py`, `backend/notion_usage.py` | Old Notion-backed archive and usage store. Zero importers. Latent `with _client()` on None bug. | DELETE now |
| H9 `backend/notion_hymns.py` | Notion hymns client, imported by migrate_to_db and the legacy scripts, and by worship_service.py:20-21 for type checking only. | DELETE with H1 |
| H10 `fill_from_hymnary.py`, `add_hymnary_links.py`, `fix_hymn_titles.py`, `select_sunday_hymns.py` | Notion-bound Hymnary scraping and fixes. `fill_from_hymnary` uses Playwright and takes about 45-60 minutes for ~700 hymns. It is the only reason `playwright` is a runtime dependency. | DELETE; any DB enrichment later must be a background job |
| H11 `backend/email_send.py` | Shared SMTP sender using `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD`. Zero importers. Would bypass the per-user sender check. | DELETE now |
| H12 Config, env, deps, docs | The DB default is `sqlite:///data/church.db` (db/engine.py:24) but the docs say `data/app.db`. `ESV_API_KEY` and `LOG_LEVEL` are missing from `backend/.env.example`. `backend/requirements.txt` ships `playwright` and `notion-client`. `shadcn` is a runtime dependency in `frontend/package.json`. README sections at 10-14 and 48-119 and docs/manual-verification.md sections 1-3 describe Streamlit. | KEEP; rewrite at cutover |
| H13 `backend/migrate_add_hymn_facts.py` (amendment 2026-09-26, PR #4) | Idempotent one-off: adds `text_year INTEGER` and `hymnal_count INTEGER` to `hymns` and `hymn_catalog` where the SQLAlchemy inspector shows them missing (works on Postgres and SQLite). Prints the target database first (password hidden). **Already applied to production Supabase** before PR #4 merged. Test: backend/tests/test_migrate_hymn_facts.py. README "Service rubric: hymn year and familiarity" step 1 documents it. | DELETE in slice 1 with H2, once the Alembic baseline and `0002_reconcile` cover the columns |
| H14 `backend/backfill_hymn_facts.py` + `backend/hymnary_facts.py` (amendment 2026-09-26, PR #4) | Ops CLI (`--dry-run`) that fills blank `text_year` and `hymnal_count` on `hymn_catalog` and `hymns` from Hymnary.org's public scripture API (never the bot-protected website): one request per scripture reference, about 1 s apart, cached per reference; matches by normalized title or first line; fills blanks only, so manual corrections survive; leaves a row unknown when a request fails or a response hit the 100-text cap; prints coverage. Uses `httpx`; `load_dotenv()` runs in the CLI entry module only. PH1990 has no scripture references, so its hymns stay unknown. Re-run after a hymnal import or added hymns. Test: backend/tests/test_hymnary_facts.py (no network). | KEEP as an ops CLI (not an API route) |

### I. Data model, scoping and functions with no UI

| Table | Scope | Notes relevant to the API |
|---|---|---|
| users (models.py:33-42) | global | `email` is UNIQUE and normalized (race on insert). `google_sub` is UNIQUE and nullable. |
| churches (45-53) | tenant root | `timezone` is free text and unused. `settings` JSON holds `liturgy_prompts` and `bible_translation`, and since PR #4 (amendment 2026-09-26) the sparse `rubric` overrides (G11). Soft delete through `deleted_at`, no purge job. |
| memberships (56-73) | church | Primary key `(church_id, user_id)`. Role CHECK in owner/admin/member. |
| invites (76-97) | church | `code` UNIQUE. `role` has **no CHECK**. `UNIQUE(church_id,email)` covers every row, which contradicts the comment at line 84. |
| hymn_catalog (100-111) | global, read-only | Seed source. Empty in local DBs. Since PR #4 (amendment 2026-09-26): nullable `text_year` and `hymnal_count` (D10), already added in production by H13. |
| hymns (114-134) | church | No uniqueness. `hymnal` defaults to GG2013. Since PR #4 (amendment 2026-09-26): nullable `text_year` and `hymnal_count`, copied from the catalog on seed and filled by H14; `NULL` means unknown. |
| services (137-160) | church | Date stored as two strings. `hymns` JSON is a `[{title, number}]` snapshot. No `custom_elements` column. `saved_at` rewritten on every update. |
| hymn_usage (163-182) | church | UNIQUE `(church, date_iso, number, title)`; NULL numbers do not collide. |
| contacts (185-199) | church | No uniqueness, no format check. |
| gmail_tokens (202-211) | user | `refresh_token` stored as plaintext. |
| oauth_states (214-223) | user | Deleted only when consumed; never purged. |

- **Trust boundary:** every church-scoped repo function trusts its `church_id` argument. Always pass `ActiveChurch.id`. Never take a church id from the body, path or query.
- **Global lookups that must never be exposed:** `repos.users.get_user`, `get_user_by_email` (email enumeration), `google_oauth._user_email`. `repos.invites.get_invite_by_code` is a global lookup by secret code.
- **Id types:**
  - `repos/churches|memberships|invites|users` do not coerce strings to UUID. On SQLite a string raises `StatementError`, and `revoke_invite(id, str(church_id))` silently does nothing because a UUID never equals a string.
  - `hymns`, `service_archive`, `email_contacts` and `hymn_usage` use `_as_uuid`, which raises `ValueError` (a 500) on malformed input.
  - Type every path id as `uuid.UUID`.
- **Domain functions with no UI or no runtime caller:** `service_archive.delete_service`, `email_contacts.get_contacts_for_display`, `repos.hymns.list_church_hymnals` (CLI only), `repos.hymns.update_hymn` (helper only), `repos.hymns.import_hymns` (CLI only), `repos.churches.update_church`, `repos.memberships.count_admins` and `add_membership`, `repos.invites.get_invite_by_code`, `repos.users.upsert_user` and `get_user_by_email`, `streamlit_auth.current_user_id`, `worship_service.resolve_hymnary_audio_url`, `email_send.send_gmail`. Amendment 2026-09-26: `repos.churches.update_church_rubric` has no UI caller (API only, `PATCH /rubric`).

---

## 2. API surface

### 2.1 Conventions for every new route
- Resource naming:
  - Church-scoped collections are top-level plural nouns (`/hymns`, `/services`, `/contacts`, `/members`, `/invites`) and rely on X-Church-Id plus the guard.
  - The active church itself is the singleton `/church`, and its settings sit under it (`/church/liturgy-prompts`).
  - Global reference data (`/lectionary/readings`, `/translations`, `/scripture/passages`, `/liturgy/config`) is `user`-guarded.
- Validate user-facing input inside the route and raise `ApiError`. `RequestValidationError` flattens everything into "The request was not valid." (backend/api/errors.py:49-51).
- Add status codes that `_HTTP_CODES` lacks by using `ApiError(status, code, message)` explicitly: 409 `conflict`/`last_admin`/`invite_exists`, 429 `rate_limited`, 502 `upstream_error`, 503 `*_unavailable`, 504 `upstream_timeout`.
- Type ids as `uuid.UUID`, so a malformed id is a 422 instead of a 500.
- Return a JSON body from DELETE routes: `apiFetch` always calls `res.json()` on success (frontend/src/lib/api.ts:43). For `.docx`, add a blob variant of `apiFetch`, and add `expose_headers=['Content-Disposition']` (plus `Idempotency-Key` in `allow_headers` if used) to the CORS setup (backend/api/main.py:37-42).
- Routes that do blocking I/O (httpx, requests, sync OpenAI) must be plain `def` so they run in the threadpool, not `async def`.
- Add a per-user rate limit on AI, scripture and email routes. With a single uvicorn worker (backend/Procfile), an in-memory token bucket keyed by user id is enough.
- **Shared draft schema** `ServiceDraft`, used by `/services`, `/documents` and `/bulletin-emails`:
  - `service_date_iso: date`, `occasion: str`, `scriptures: [str]` (≤20 items, ≤200 chars each)
  - `hymns: {opening, response, closing}`, each `HymnRef` or null, where `HymnRef = {hymn_id?: uuid, title, number: int|null, hymnal?}`
  - `liturgy: {section: str}`, limited to the 8 `SECTION_ORDER` keys
  - `sermon_title`, `selected_ot_ref`, `selected_nt_ref`, `include_communion: bool`
  - `custom_elements: [{label (required, ≤200), text (≤10000), insert_after: one of the 17 placements}]` (≤30)
  - The server derives `service_date_display` as `date.strftime('%B %d, %Y')`, so archive labels and usage parsing stay identical to existing rows.

### 2.2 Endpoint table

Latency: **fast** is under about 1 s. **EXT** means an external HTTP call. **LONG** means it can exceed 10 s.

| Method | Path | Guard | Slice | Purpose | Request | Response | Reuses | Latency |
|---|---|---|---|---|---|---|---|---|
| GET | /health | none | 0 (exists) | Liveness | – | `{ok:true}` | routes/health.py | fast |
| GET | /me | user | 0 (exists) | Identity and churches (sorted by name) | – | `{user:{id,email,name,picture}, churches:[{id,name,role}]}` | auth.upsert_from_claims, list_user_churches | fast |
| GET | /church | church | 0 (extend in 2) | Confirm the active church; add profile fields | X-Church-Id | `{id,name,role, timezone, bible_translation (stored or null), effective_translation}`; 403 | validate_active_church, get_church, get_church_translation, available_translations | fast |
| POST | /churches | user | 1 | Create church; caller becomes owner; seed hymnal | `{name, timezone}` (trimmed; IANA check with zoneinfo); optional Idempotency-Key | 201 `{id,name,role:'owner'}`; 400 "Church name is required." or "Timezone is required." or "Unknown timezone." | repos.churches.create_church (+ seed_church_from_catalog) | 1-3 s (seed) |
| POST | /invites/accept | user (no X-Church-Id) | 1 | Join by code, also for users who already have a church | `{code}` | 200 `{church:{id,name,role}, message:'Joined {name}.'}`; 400 `invite_rejected` with one of the 6 messages in B1; 400 "Enter an invite code, or open your invite link again." | accept_invite, extended to return church_id and a reason code; IntegrityError on double accept counts as success | fast |
| POST | /invites/preview | user | 1 (optional) | Show church and role before accepting | `{code}` | `{church_name, role, expires_at, email_bound}` or the same 400s, read-only | get_invite_by_code + get_church | fast |
| GET | /lectionary/readings | user | 2 | Reading sets for the Sunday on or before a date | `?date=YYYY-MM-DD` | `{requested_date, sunday_date, normalized, service_date_display, reading_sets:[{liturgical_date, calendar_date, first_reading, psalm, second_reading, gospel, scriptures}], default_index (last set or null), message}` (200 with empty sets when both sources fail) | vanderbilt_lectionary.get_readings_for_date_string(iso) with a TTL cache | **EXT/LONG** up to ~35 s cold |
| GET | /translations | user | 2 | Translation options | – | `{default:'web', esv_available, items:[{id,label}]}` | scripture_fetcher.available_translations, esv_configured | fast |
| POST | /scripture/passages | user | 2 | Passage text (all at once, or one for lazy expanders) | `{refs:[str] 1..12, translation}` | `{translation, translation_label, passages:[{reference, text or null, ok}]}`; 422 "Unknown or unavailable translation." | scripture_fetcher.get_passage_text | **EXT/LONG** 15 s per part |
| POST | /scripture/references/classify | user | 2 (optional) | OT/NT picker options | `{scriptures:[str]}` | `{options:[{ref, testament}], ot_options, nt_options}` | new backend/scripture_refs.py (from app.py:69-102) | fast |
| GET | /hymnals | church | 3 | Hymnal switcher | – | `{hymnals:[{code,count}], default}` | list_church_hymnals (+ a count helper) | fast |
| GET | /hymns | church | 3 (paging used in 6) | Pickers and Settings list | `?hymnal=&q=&limit=&offset=&recent_weeks=12&exclude_usage_date=` | `{total, recently_used_count, items:[{id, hymnal, title, number, link, scripture_refs, theme, recently_used}]}`; every row keyed by id; NULL numbers explicitly last | list_hymns, get_recently_used_identifiers (plus an exclude-date parameter), is_hymn_recently_used, hymn_display_from_flat (moved to backend) | fast |
| POST | /hymns/scripture-matches | church | 3 | "Find hymns matching" over the church's hymnal on the server | `{refs:[str] 1..20, hymnal?, limit_per_ref=50, max_results=20}` | `{refs_used, total_matched, hymns:[{id,title,number,hymnal,link}]}`; 422 "Enter scripture readings above, or add one in the field above." | hymns_by_scripture(all_hymns=list_hymns(church.id, hymnal)) | fast |
| POST | /hymns/suggestions | church | 3 | AI picks per slot | `{occasion, scriptures, selected_nt_ref?, nt_text? (≤20k), translation?, hymnal?, limit_per_slot=5 (1-10), exclude_recent=false, recent_weeks=12}` | `{opening:[Hymn], response:[Hymn], closing:[Hymn], picks:{opening,response,closing}, message}`; 503 `ai_not_configured`; 502 `ai_upstream_error`; 504 `ai_timeout`; 429 | suggest_hymns_for_service, refactored (see section 3) | **LONG** 5-60 s |
| POST | /hymns/suggestions/stream | church | 3 (optional) | Progress over SSE | same | `text/event-stream`: `progress{message,pct}`, `result`, `error` | same, with progress_callback feeding a queue | **LONG** |
| GET | /liturgy/config | user | 4 | Constants the builder UI needs | – | `{sections:[{key,label,override_label,default_selected,rows}], custom_placements:[{key,label}], default_overrides:{benediction:'Halverson'}, assurance_response, communion:{default_rule:'first_sunday_of_month', title, blocks}}` | liturgy_prompts.SECTION_ORDER and SECTION_LABELS; DEFAULT_BENEDICTION, CUSTOM_PLACEMENTS and the communion text moved into backend | fast |
| POST | /liturgy/generate | church | 4 | Generate the ticked sections; override text is used verbatim | `{occasion (≤300), scriptures, hymns:{opening,response,closing: hymn_id or null}, sections:[SectionKey], overrides:{SectionKey:str (≤20000)}}` | `{liturgy:{…}, sources:{key:'override' or 'generated' or 'error'}, errors:{key:{code,message}}}`; 503 `ai_unavailable` (only when a section needs AI); 422 `prompt_invalid` naming the section; 429 | generate_liturgy (refactored), get_church_prompts, new repos.hymns.get_hymn(id, church_id) | **LONG** ~5-20 s per section |
| GET | /services | church | 5a | Archive list (summary only) | `?limit=20&offset=0` | `{items:[{id, service_date, service_date_iso, occasion, saved_at, created_by}], total}` | list_saved_services (+ SQL limit/offset, projection) | fast |
| GET | /services/{service_id} | church | 5a | Load a service | uuid | `ServiceOut` (service_archive._to_dict shape); 404 | get_service | fast |
| POST | /services | church | 5a | Save new | `ServiceDraft` | 201 `ServiceOut` | save_service(created_by=user.id) | fast |
| PUT | /services/{service_id} | church | 5a | "Save changes" (full replace) | `ServiceDraft`; optional If-Match `saved_at` | 200; 404 (client falls back to POST, as app.py:1055-1059 does); 409 stale | update_service | fast |
| DELETE | /services/{service_id} | church (product decision) | 5a | New: delete from archive | – | `{deleted:true}`; 404 | delete_service | fast |
| POST | /documents | church | 5a | Build the bulletin or pastor `.docx` from the draft; records hymn usage | `{variant:'bulletin' or 'pastor', service: ServiceDraft}` | 200 docx bytes with `Content-Disposition: attachment; filename=worship_{Month}_{DD}_{YYYY}.docx` or `worship_pastor_…` | new service_output.build_service_docx → build_docx; record_usage (conflict-safe) | ~0.2-1 s |
| POST | /documents/preview | church | 5a (optional) | Full order of worship as blocks, matching the docx | same | `{blocks:[{kind, text, runs?}]}` | build_docx split into build_order_of_worship + render | fast |
| GET | /contacts | church | 5b | Recipient picker and Settings list | – | `{contacts:[{id,name,email}]}` | list_contacts | fast |
| GET | /gmail-connection | user | 5b | Status | – | `{configured, connected, google_email}` | is_configured, is_connected, plus reading GmailToken.google_email | fast |
| POST | /gmail-connection/auth-url | user | 5b | Start consent; one state per click | – | `{auth_url}`; 503 `gmail_not_configured` "Per-user Gmail sending isn't configured on this deployment." | create_state + build_auth_url (+ purge expired states) | fast |
| POST | /gmail-connection | user | 5b | Finish consent: the frontend `/gmail/callback` page posts code and state | `{code, state}` | 200 `{connected:true, google_email}`; 400 `gmail_state_invalid` "Sign-in expired or was invalid. Please try again."; 400 `gmail_connect_failed` (exchange_code RuntimeError text); 502 network | consume_state (must equal the caller) + exchange_code | **EXT** up to ~60 s |
| DELETE | /gmail-connection | user | 5b | Disconnect | – | `{connected:false}` | disconnect | fast |
| POST | /bulletin-emails | church | 5b | Email the bulletin from the caller's Gmail; the server rebuilds the docx | `{service: ServiceDraft, contact_ids:[uuid], additional_emails:[EmailStr], message?}`; Idempotency-Key recommended | `{sent:true, recipient_count}`; 400 `no_recipients` "Please select at least one recipient or enter an email address."; 409 `gmail_not_connected`; 503 `gmail_not_configured`; 502 `gmail_send_failed` (+ `disconnected` flag) | build_service_docx, list_contacts (church-scoped id lookup), send_email | **EXT** up to ~60 s |
| POST | /hymn-usage | church | 5a (optional) | Only if usage recording is separated from `/documents` | `{service_date_iso, hymns:[{title, number}]}` | `{recorded}`; 422 bad date | record_usage | fast |
| PATCH | /church | admin | 6 | Name, timezone and default translation in one transaction | `{name?, timezone?, bible_translation?}` | same shape as GET /church; 400 "Church name is required." or "Timezone is required." or "Unknown or unavailable translation." | logic from settings.py:61-74 and 162-168 moved to backend/church_admin.py; locked settings merge | fast |
| DELETE | /church | owner | 6 | Soft delete; confirmation checked on the server | `{confirm_name}` | `{deleted:true}`; 400 "Church name did not match." | soft_delete_church | fast |
| POST | /church/transfer-ownership | owner | 6 | Atomic transfer | `{user_id}` (an existing member other than the caller) | `{members:[…]}`; 404 not a member; 400 self | new single-transaction repo function | fast |
| GET | /church/liturgy-prompts | church | 6 | Read prompts | – | `{placeholder_help, can_edit, fields:[{key,label,default,override,customized}]}` (system first) | get_church_prompts, liturgy_prompts.* | fast |
| PUT | /church/liturgy-prompts | admin | 6 | Save; full replace (omitted keys go back to default) | `{prompts:{key:str}}` | same as GET; 422 `prompt_invalid` naming the section | submit_prompts cleaning (moved) + test-render validation | fast |
| DELETE | /church/liturgy-prompts | admin | 6 | Reset all | – | same as GET | set_church_prompts(church_id, {}) | fast |
| POST | /contacts | admin | 6 | Add | `{name?, email: EmailStr}` | 201 contact; 400 "Email is required." | add_contact | fast |
| DELETE | /contacts/{contact_id} | admin | 6 | Delete | uuid | `{deleted:true}`; 404 | delete_contact | fast |
| POST | /hymns | church | 6 | Add a hymn (members allowed) | `{title, number?: int ≥0, scripture_refs?, theme?, hymnary_link? (https only), hymnal? (church default)}` | 201 hymn; 400 "Hymn title is required." | add_hymn | fast |
| PATCH | /hymns/{hymn_id} | church | 6 | Edit (new UI); the server merges before a full replace | partial fields | hymn; 404 | new get_hymn + update_hymn | fast |
| DELETE | /hymns/{hymn_id} | church | 6 | Delete | uuid | `{deleted:true}`; 404 | delete_hymn | fast |
| GET | /hymnal-sources | admin | 6 | Bundled hymnals that can be added | – | `{sources:[{code:'PH1990', label, hymns:605, has_scripture_refs:false, present}]}` | registry + list_church_hymnals | fast |
| POST | /hymnals | admin | 6 | Import a bundled hymnal, or upload a CSV | JSON `{code, source:'bundled'}` or multipart `{hymnal (^[A-Za-z0-9_-]{2,20}$), file (≤1 MB CSV)}` | `{hymnal, inserted, updated, total, hymnals}`; 422 bad CSV | import_hymnal.load_rows (read a stream as utf-8-sig) + import_hymns | ~1-3 s |
| DELETE | /hymnals/{code} | admin | 6 (optional, new) | Remove a mistaken import | – | `{deleted, hymnals}` | new delete_hymnal(church_id, code) | fast |
| GET | /members | church | 6 | List | – | `[{user_id,email,name,role,is_me}]` | list_members | fast |
| PATCH | /members/{user_id} | admin (owner rules) | 6 | Change role | `{role:'member' or 'admin'}` | member; 404; 409 `last_admin` "Cannot demote the last owner/admin of this church."; 403 when the target is the owner or yourself | set_role (after a membership pre-check) | fast |
| DELETE | /members/{user_id} | admin (owner rules) | 6 | Remove (and, if the product owner agrees, leave) | – | `{removed:true}`; 404; 409 `last_admin` "Cannot remove the last owner/admin of this church." | remove_membership | fast |
| GET | /invites | admin | 6 | Active invites | – | `[{id, code, url, email, role, created_by, expires_at}]` | list_invites | fast |
| POST | /invites | admin | 6 | Create | `{role:'member' or 'admin', email?: EmailStr}` | 201 `{id, code, url, email, role, expires_at}`; 409 `invite_exists` | create_invite (return id and expiry) | fast |
| DELETE | /invites/{invite_id} | admin | 6 | Revoke | uuid | `{revoked:true}`; 404 | revoke_invite (must return a found flag) | fast |
| GET | /health/ready | none | ops (optional) | DB readiness; can also act as an off-GitHub keep-alive target | – | `{ok, db}`; 503 | SELECT 1 on the process engine | fast |
| GET | /rubric | church | **exists** (PR #4; amendment 2026-09-26). Editor UI in 6a | Read the church's service rubric | – | `RubricOut {rubric: {hymns: {slot: [str]}, prayers: {SectionKey: [str]}, prefer_before_year: int, prefer_familiar: bool}, customized: [str]}` | routes/rubric.py; get_church_rubric_overrides, service_rubric.merge_rubric, customized_keys | fast |
| PATCH | /rubric | admin | **exists** (PR #4; amendment 2026-09-26). Editor UI in 6a | Sparse update; `null` resets one checklist or setting | plain JSON object, e.g. `{"prayers": {"benediction": [...]}, "prefer_before_year": null}` | same as GET; 422 `invalid_rubric` with the G11 message (no `fields`); 422 `invalid_request` for a non-object body; 403 for members | update_church_rubric (locked), service_rubric.validate_patch | fast |

### 2.3 Long-running endpoints: approach

The main recommendation: **use synchronous `def` routes with explicit upstream timeouts and fan-out on the client or inside the request. Do not add a job queue.** The reasons:
- One tester, one uvicorn worker, and an always-on Railway service.
- The browser calls Railway directly (`NEXT_PUBLIC_API_URL`), so Vercel function limits do not apply. Still confirm Railway's HTTP request timeout.

| Endpoint | Today | Recommendation |
|---|---|---|
| GET /lectionary/readings | Up to ~35 s cold (Lectio 15 s + Vanderbilt 20 s), sequential. Failures cached forever. | Sync. Server TTL cache keyed by Sunday (success ~24 h, failure ~5 min). Replace `_cache` with timestamped entries. Optionally fetch Lectio and Vanderbilt in parallel. The UI must not wipe typed fields on failure. |
| POST /scripture/passages | Sequential, 15 s per part or alternative. | Sync with bounded concurrency (3-4 workers). The client can also load each reading lazily when its expander opens. Cache public-domain translations by `(translation, ref)`; follow Crossway terms for ESV (default: no server cache). |
| POST /hymns/suggestions | No OpenAI timeout (about 600 s, 2 retries). May also fetch NT text inline. | Sync. `OpenAI(timeout≈45, max_retries=1)`. The client sends `nt_text` when it already has it. Show a spinner, not a fake progress bar. Add SSE later only if the product owner wants step messages. |
| POST /liturgy/generate | 6-8 sequential calls, no timeout. | The client sends one request per ticked section in parallel and fills the preview as each returns. The server also runs multi-section requests concurrently (ThreadPoolExecutor). Per-call timeout about 60 s, one retry. |
| POST /gmail-connection | 2 Google calls, 30 s each. | Sync; spinner on the callback page. |
| POST /bulletin-emails | Docx build + refresh + send (2 calls, 30 s each). | Sync. Disable the button and use an Idempotency-Key so a retry cannot send twice. |
| POST /churches | Seeds ~700 rows one ORM add at a time. | Sync. Disable the button. Idempotency-Key. Optionally a bulk `INSERT … SELECT`. |
| POST /hymnals | 605 rows. | Sync. Any Hymnary scraping enrichment would be a separate background job, out of scope. |

---

## 3. Streamlit coupling to remove

`backend/` has **no** `st.*` calls, session state or Streamlit caches (grep). The coupling sits in the Streamlit-side modules and in UI-shaped behavior inside the domain modules.

| Location | Coupling | Fix | Slice |
|---|---|---|---|
| app.py (whole module) | `import streamlit` and `st.set_page_config` at import time (17, 105-109) mean the API cannot import any of its domain logic | Move out: NT classifier (69-102) → backend/scripture_refs.py; `DEFAULT_BENEDICTION` (67), `CUSTOM_PLACEMENTS` (148-166), the four copies of the section list (398-399, 857-866, 880-895, 950-959) and the first-Sunday rule (969-971) → liturgy_prompts or a new liturgy_config module; `safe_date`, variant flags, the `hymns_ordered` mapping and usage recording (847-851, 978-1028, 1072) → backend/service_output.py; the email subject, body and recipient merge (1115-1131) → service_output.compose_bulletin_email | 2-5 |
| app.py:428-464, 481-489 | Lectionary orchestration and reading-set switching are session mutations; the error is lost to the rerun | A pure `lectionary_service.load_for_date(date)` behind GET /lectionary/readings. Occasion and scripture state live in the client, with an explicit reset rule and a frontend test. | 2 |
| app.py:371-377, 556-577 | Translation default resolution lives in the render | `resolve_effective_translation(church_id)` in backend; the per-session override is client state | 2 |
| app.py:579-597; worship_service.py:433 | Passage cache in session; the `[Could not load text]` sentinel leaks into domain code | `fetch_passages(refs, translation)` returning null on failure; drop the sentinel in suggest | 2-3 |
| app.py:636-646, 723-725; 520-535 | `_cached_all_hymns` and `_cached_saved_services` session caches with manual Refresh buttons | Client query cache keyed `[churchId, …]`, invalidated after mutations. Refresh becomes a refetch. Never cache an error as empty. | 3, 5a |
| app.py:648-663, 676-695, 735-746 | Hymnal filter, search loop and exclusion filter are UI logic | Server-side filter by hymnal; `hymn_search.search_by_refs`; a `recently_used` flag in GET /hymns | 3 |
| app.py:753-824, 770-772 | First-pick apply, `_find_key`, messages classified by the substring "Could not", `st.progress`, and a closure that reads the session translation | Structured response with `picks`; HTTP errors; translation passed explicitly | 3 |
| app.py:259-266, 401-404, 847-851 | Picks are lower-cased titles, flattened by position | React state holds `{opening,response,closing}` hymn ids; the API takes slot-keyed hymns | 3-5 |
| app.py:926-945 | Generate reads overrides from session, gates on an env var, is not wrapped in try/except | `liturgy_service.generate_for_church(...)` behind POST /liturgy/generate | 4 |
| ui_helpers.py `sermon_text_for` (amendment 2026-09-26, PR #4); app.py:941-956 | The sermon text for the liturgy prompt comes from the page's session passage cache (fetched in the session translation, ESV included) | The client sends the effective NT reference and its already-loaded passage text with each generate request (never ESV text; slice 4 amendment); the backend only formats it | 4 |
| app.py:1029-1067 | Editing-id lifecycle (a `get_service` call every rerun), update-then-insert fallback | The client keeps `editingServiceId` and `editingDateIso`; PUT, then POST on 404 | 5a |
| app.py:176-218, 334-336 | Gmail callback read from `st.query_params` at the app root; `create_state` on every render; errors passed through `oauth_error` | `/gmail-connection` endpoints, a frontend `/gmail/callback` page, state created on click only | 5b |
| app.py:169-173 | `@st.cache_resource` around `init_db` | Already replaced by the lifespan (api/main.py:24-31) | done |
| app.py:221-256; streamlit_tenancy.py:13-88 | Hand-maintained church reset lists that disagree; session-based tenancy | Key all client state by church id; `require_church` plus `pickActiveChurch` (add a fallback on 403). Delete at cutover. | 1, 7 |
| streamlit_auth.py | `st.user`, `st.login`, `st.logout`, `st.stop`; `current_user_id` is dead | Replaced by `get_current_user` + Supabase `signOut`. Delete. | 7 |
| streamlit_views/settings.py:11, 33-168 | Tested permission helpers and validation messages live in a module that imports streamlit | Move to backend/church_admin.py and re-export from settings.py until cutover. Add the module to test_no_streamlit_in_core.py. Map `NotAuthorizedError` → 403, `ValueError` → 400, `LastAdminError` → 409. | 6 (the prompt-validation part in 4) |
| streamlit_views/settings.py:180-182, 69-74, 388, 229-237 | Direct ORM access in the view and helper; popping the active church; keyed prompt widgets that go stale | Use repos; one-transaction PATCH; the client refetches /me and clears caches after delete; the prompt form re-initializes from the server on load, save, reset and church switch | 6 |
| ui_helpers.py | Query-param capture, invite pick, selectbox coercion, title-keyed map | Port capture and pick to the frontend `/join` route. Move `hymn_display_from_flat` into backend (merge with `hymn_display_info`, add id and hymnal, drop `audio_url`). Drop the rest. | 1, 3, 7 |
| backend/google_oauth.py:190-201, 17-24, 129-136 | `should_handle_gmail_callback` and docstrings assume the redirect lands on the Streamlit root | Point `GOOGLE_OAUTH_REDIRECT_URI` on Railway to `https://<frontend>/gmail/callback`. Delete the function and its tests at cutover. | 5b, 7 |
| backend/worship_service.py:20-21, 287-343, 447-450 | Notion fallback (`db: NotionHymnsDB`, crashes when `db=None`), "Loading hymn list from Notion…" | Make `all_hymns` required, drop `db` and the TYPE_CHECKING import | 3 |
| backend/worship_service.py:406-417, 539-541, 705-724, 763-764 | UI-shaped error handling: empty slots or error text returned as content; "Settings → Secrets" wording; overrides discarded when there is no client | Typed exceptions (`AIUnavailable`, `AIUpstreamError`, `PromptInvalid`) and per-section status; apply overrides before requiring a client; configurable timeouts | 3, 4 |
| backend/worship_service.py:28, 612-683 | Dead audio resolver; process cache keyed only by number, hard-coded GG2013 | Delete | 3 or 7 |
| backend/worship_service.py:790, 794 | Unused `include_placeholders` and `scripture_full_texts` parameters | Leave out of the API contract | 5a |
| backend/worship_service.py:16, 23 (also import_hymnal.py, migrate_add_hymnal.py, notion_hymns.py) | `load_dotenv()` at import time | Load env only in entry points | 7 |
| backend/vanderbilt_lectionary.py:22, 163-166, 176-178 | Implicit process cache that stores failures forever | Timestamped entries with a short TTL for failures | 2 |
| backend/repos/invites.py:66-109 | Returns `(bool, message)` shaped for `st.success`/`st.error`; no church id or reason code | Return a result object `{ok, reason_code, message, church_id}` with the same messages | 1 |
| backend/db/engine.py:24, 30 | Comment cites Streamlit reruns (the setting is still needed for the FastAPI threadpool); default DB path differs from the docs | Fix the comment; make the default absolute or required | 7 |
| pytest.ini, requirements*.txt, test_foundation_setup.py:17-28, test_docs.py | CI installs Streamlit and asserts Streamlit docs, config and deps | See the cutover checklist | 7 |

---

## 4. Cross-cutting risks

**Tenancy and authorization**
- Every church-scoped repo trusts its `church_id` argument (section 1, I). Pass only `ActiveChurch.id`. Resolve client-supplied hymn and contact ids within the church. Load prompt overrides on the server.
- Global lookups must not be exposed (`get_user_by_email`, `get_invite_by_code` beyond a minimal preview).
- Ownership integrity (verified):
  - Admins can grant or revoke "owner", including to themselves, and can demote or remove the owner.
  - Transfer to a non-member, or to yourself, leaves the church with no owner. The two steps are not atomic.
  - Invites accept any role string, and there is no DB CHECK.
  - The API needs: at least one owner at all times; only owners grant or revoke owner; no self-role changes; atomic transfer; invite role restricted to member or admin.
- Code-only invites can be reused for 7 days and may carry the admin role. Treat codes as bearer secrets: send them in POST bodies, never in API paths, keep them out of logs, and replace browser history after reading `/join?code=`.
- Permission parity (decide explicitly, see section 7): every member can see all members' emails, edit or delete any service and any hymn, and send the church bulletin to any address.

**Concurrency and data integrity**
- User upsert race on the first request, which returns a 500 (deps.py:63-66). Fix it with `INSERT … ON CONFLICT (email)`, or catch and re-select. Consider throttling the `last_login_at` write.
- `record_usage` check-then-insert races, for example the client preparing both copies at once. Use `ON CONFLICT DO NOTHING`. NULL-number duplicates are not blocked by the constraint.
- A concurrent `accept_invite` hits the memberships primary key: map it to success.
- `_merge_settings` is a read-modify-write, so concurrent prompt and translation saves can lose one of them. Use `SELECT … FOR UPDATE`. **Amendment 2026-09-26:** PR #4 already did this in `repos/churches.py` (`_lock_live_church`, G3, G11); the remaining work is the API's single locked merge helper with a `session` parameter (6a).
- `update_service` is last-write-wins. Optionally use `saved_at` as an ETag.
- Multi-step writes are not atomic, because each repo call opens its own `session_scope`: profile save, transfer, save-then-usage. Add service-layer functions that take a session. Keep the property that no DB connection is held during OpenAI or Google calls.
- SQLite differs from production: foreign keys are not enforced outside tests (conftest.py:29-34), `with_for_update` does nothing, datetimes are naive, and NULL ordering is reversed.

**Secrets and ops security**
- **Critical:** the repo is PUBLIC and backup.yml uploads an unencrypted `pg_dump` as a workflow artifact. Do not add the `DATABASE_URL` secret until the dump is encrypted or sent to private storage, or the repo is made private.
- Gmail refresh tokens are plaintext in the DB (models.py:209). Consider encryption at rest.
- `OPENAI_API_KEY`, `ESV_API_KEY` and `GOOGLE_CLIENT_SECRET` stay on the backend (spec invariant 1). The passages endpoint must proxy ESV.
- Error text from OpenAI, Google and the DB currently reaches users (app.py:290-291, 319-320, 192-193; `[Error generating …]`). The API should surface only known domain messages and send everything else to the generic 500.

**OAuth flows that change shape**
- The Gmail `gmail.send` redirect moves from the Streamlit root to a frontend page such as `/gmail/callback`, which POSTs `{code, state}` with the bearer token. A backend GET redirect target cannot carry the Supabase token, so it cannot re-check the user.
- Both redirect URIs must be registered on the Google client while both apps run. `exchange_code` sends `GOOGLE_OAUTH_REDIRECT_URI` from its own deployment's env, so Railway and Streamlit Cloud must each keep their own value.
- The callback page must not be `/auth/callback`, which is the Supabase code exchange.
- A signed-out user landing on `/gmail/callback` is redirected to `/login?code=…&state=…` and the values are then lost (section 0, item 1). Show "Try connecting again." A Google `?error=` on that path would show the login page's generic "Sign-in didn't complete" message.
- Handle `?error=access_denied` on the callback page (Streamlit ignores it). Purge expired `oauth_states`.
- Invite links do not survive Supabase login today. Store the code in sessionStorage before redirecting to `/login`, or pass a validated same-origin `next` path that is also on Supabase's redirect allow-list.

**File downloads through the API**
- Word files are generated per request from the posted draft, which removes the stale-bytes problem (a behavior change).
- The frontend needs a blob fetch (`apiFetch` always parses JSON) and must either read `Content-Disposition` (needs CORS `expose_headers`) or build the filename itself.
- A `python-docx` import failure raises `RuntimeError`: map it to 500 and keep python-docx in requirements.

**Caching that Streamlit provided implicitly**
- `st.cache_resource(init_db)` → already the lifespan.
- The per-session hymn, archive, passage and search caches → a client query cache keyed by church. Settings mutations must invalidate the builder's hymns (today they do not).
- Process caches become more important in a long-lived API: the Vanderbilt failure-forever cache, and the dead audio cache.
- The church default translation must be re-read after Settings changes it.

**External APIs: rate limits and latency**
- OpenAI: shared key, cost exposure, now scriptable through the API. Rate-limit per user and per church, cap prompt size, and never accept a client-supplied hymn list.
- bible-api.com: free and rate-limited per IP, and every user now shares the Railway IP. ESV: key required and Crossway terms limit volume and storage.
- Lectio and Vanderbilt: no key. Vanderbilt "often returns 403 or HTML".
- Gmail: per-account sending limits. A 400 or 401 on token refresh silently disconnects the user.
- Notion: migration only.

**Schema, migrations, coexistence**
- There is no migration tool. `create_all` never alters tables. Adopt Alembic with a baseline of the current production schema before the first change. Planned changes: partial unique index on pending invites, a CHECK on `invites.role`, optionally `services.custom_elements`, and the missing `ix_hymns_church_hymnal` if applicable. **Amendment 2026-09-26:** the current production schema now includes `text_year` and `hymnal_count` on `hymns` and `hymn_catalog` (PR #4, added by the one-off H13), so the baseline must include them.
- While both apps run on the same database:
  - Keep `services.hymns` as a list the Streamlit loader can read (app.py:401-404 calls `hymns[i].get('title')`, so no `None` entries). Recommendation: always store 3 entries `{slot, title, number, hymn_id, hymnal}`, with `title: ''` for an empty slot, and extend `_hymn_snapshot` to keep the extra keys.
  - Keep `service_date_display` in `'%B %d, %Y'`.
  - Keep `liturgy` keyed by the 8 section names.
  - If a new `custom_elements` column is added, its `update_service` parameter must default to "leave unchanged", so Streamlit saves do not wipe it.
- Connection pools: both apps hold a 5+10 pool against the Supabase session pooler, and each API request uses at least 2 checkouts.

**Time and date semantics**
- `date.today()` runs on the server (UTC on Railway).
- The 12-week window uses the UTC date and has no upper bound.
- First Sunday is computed from the plain date.
- The church timezone is ignored everywhere.
- Every date normalizes to the previous Sunday.

**Content hazards**
- Error placeholders are stored as liturgy and printed.
- The "Halverson" literal.
- `#None` in the docx.
- The Psalm printed as the NT reading.
- Unescaped titles and links in markdown. React must render them as text, with anchors only for https links.
- Hymn themes may hold Postgres array literals (plausible).

**Test gaps to close during migration**
- No tests at all for:
  - `vanderbilt_lectionary` (Sunday normalization, names, merge, CSV)
  - `fetch_passage` splitting
  - the OT/NT classifier
  - `_scripture_search_variants` and `hymns_by_scripture`
  - `suggest_hymns_for_service`, `generate_liturgy`, `build_docx` (variants, anchors)
  - email composition and the `send_email` success path
  - the save/update fallback
  - onboarding flows end to end
  - the user-mismatch callback path
  - church-switch resets
- Write characterization tests before refactoring, with OpenAI and HTTP stubbed.

---

## 5. Slice breakdown for slices 1-7

| Slice | Contents | Depends on | Size |
|---|---|---|---|
| **Now (ops, independent)** | Fix backup.yml (strip `+psycopg2`, match the pg client version, encrypt or private storage) before adding the secret. Delete dead modules with zero importers: `email_send.py`, `notion_archive.py`, `notion_usage.py`, `select_sunday_hymns.py`, `add_hymnary_links.py`, `fix_hymn_titles.py`. Add `ESV_API_KEY` and `LOG_LEVEL` to backend/.env.example. | – | S |
| **1 Onboarding** | **Backend:** POST /churches (IANA validation, exact messages, Idempotency-Key, optional bulk seed); POST /invites/accept (result object with church_id and reason code; double-accept counts as success); optional POST /invites/preview; **user-upsert race fix**; Alembic baseline, since later slices need it. **Frontend:** zero-church screen with Join and Create tabs and a logout; `/join?code=` route that stores the code before login and consumes it after; select the new church and refetch /me after join or create; on 403 fall back to the next church. **Decisions:** the invite link format (moved here from 6); whether existing members can join or create another church. **Tests:** every rejection message, already-member no-op, seed count, validation messages. | 0 | S-M |
| **2 Readings** | **Builder foundation:** page layout (per the product decision), a single draft store keyed by church id (used by 3-5), local date default. **Backend:** GET /lectionary/readings with TTL cache and the Vanderbilt cache fix (+ year-boundary fix or test); GET /translations; extend GET /church with `effective_translation` (moved here from 6); POST /scripture/passages with bounded concurrency. **OT/NT:** move the classifier to backend/scripture_refs.py and port it to TypeScript with shared fixtures. Reading-set switcher and occasion/scripture editing that does not destroy user input. **Tests:** network-free fixture tests for the lectionary, passages and classifier. | 1 (shell only) | M |
| **3 Hymns** | GET /hymnals; GET /hymns (slim, keyed by id, `recently_used`, excluding the draft's own date); POST /hymns/scripture-matches; POST /hymns/suggestions (drop the Notion path, typed errors, OpenAI timeout, return ids, optional exclude_recent, `nt_text` input); picks as hymn ids per slot; show numbers in the picker; notice instead of silently clearing a pick. Move `hymn_display_from_flat` into backend and delete the dead audio code. Characterization tests for the matcher and suggestions. Out of scope: usage recording (5a), hymn CRUD (6). | 2 | M-L |
| **4 Liturgy** | GET /liturgy/config (move constants + communion text); POST /liturgy/generate (explicit slot hymns, per-section structured errors, overrides without a client, concurrency, timeout, `max_completion_tokens` compatibility, render errors → 422 `prompt_invalid`); client fans out one call per section; section ticks; "Halverson" default; custom elements (client state, validated placements); editable preview (per the product decision); communion toggle whose default recomputes on date change until the user touches it; sermon title. Add the prompt test-render validator here (reused by 6). | 3 (hymn ids) | M |
| **5a Word + archive** | backend/service_output.py (variant flags, filename, slot-keyed docx labels, `#None` fix, the NT fallback decision, conflict-safe usage recording); POST /documents (+ blob fetch, CORS expose); /services CRUD with summary list and paging; client load mapping that clears custom elements and prepared docs and skips the lectionary fetch; `services.hymns` slot-compatible storage; custom-element persistence per the product decision (Alembic migration if yes). | 2-4 | M |
| **5b Gmail + email** | `/gmail-connection` endpoints, frontend `/gmail/callback` page (including `?error=`), Google console redirect URI, `oauth_states` cleanup; GET /contacts (moved here from 6); POST /bulletin-emails (server-side docx rebuild, EmailStr validation and dedupe, To vs BCC decision, error mapping, idempotency). | 5a | M |
| **6 Settings** | Move settings helpers to backend/church_admin.py; add `require_owner`. **6a:** PATCH /church (atomic), contacts CRUD, hymn CRUD with paging, search and hymnal field (+ builder cache invalidation), GET /hymnal-sources + POST /hymnals (+ optional DELETE), prompt GET/PUT/DELETE with validation. **6b:** members with the owner-protection policy; invites with role validation, invite URL and copy button, 409 mapping or partial-unique-index migration; atomic transfer; DELETE /church with server-side confirmation (client clears caches and refetches /me). Port every streamlit_tests assertion into API tests. | 1 (join link), 4 (prompt validator) | L (split into 6a M + 6b M) |
| **7 Cutover** | Everything in section 6. Before deleting: export `hymn_catalog` to a versioned seed plus a seed CLI, and finish the Alembic adoption. | 1-6 | M |

Moves compared with the original roadmap:
- Invite link format and the `/join` route: 6 → 1.
- Upsert race fix and Alembic baseline: into 1.
- Church-default translation read: 6 → 2. The write stays in 6.
- Prompt validator: into 4.
- Usage recording: into 5a, with the exclude-own-date parameter in 3.
- GET /contacts: 6 → 5b.
- Hymnal import: from the ops CLI into 6.
- Slice 5 split into 5a and 5b; slice 6 split into 6a and 6b.

**Amendment 2026-09-26.** Work added to this breakdown after it was written (the index `2026-09-25-full-migration-design.md` and each slice spec carry the detail):
- **1:** the Alembic baseline includes `text_year` and `hymnal_count` (PR #4); `migrate_add_hymn_facts.py` (H13) is deleted with `migrate_add_hymnal.py`. The backfill (H14) stays an ops CLI.
- **3:** suggestions keep PR #4's rubric behavior (D10): ranked candidates, slot checklists and facts in the prompt; hymn DTOs carry the year, hymnal count and a "newer than preferred" flag, and the step labels newer hymns with their year.
- **4:** generation keeps PR #4's per-section checklist and sermon-text themes (E9), and adds the prayer library's voice profile and example (PR #7; new app only).
- **6a:** a rubric editor over the existing `GET`/`PATCH /rubric` (G11), and the Prayers page with its API (PR #7; new app only).

---

## 6. Cutover checklist (retiring Streamlit)

**Code to delete**
- [ ] `app.py`, `streamlit_views/`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`, `streamlit_tests/` (after porting their assertions into API tests: role checks, last-admin, owner-only transfer and delete, prompt default dropping, translation validation, member can add hymn, create church seeds, accept captured invite).
- [ ] `backend/google_oauth.should_handle_gmail_callback` and its cases in backend/tests/test_oauth_state.py. Update the module and build_auth_url docstrings.
- [ ] `backend/worship_service.py`: Notion fallback and the `NotionHymnsDB` TYPE_CHECKING import, the audio resolver and its cache, unused build_docx parameters, the "Settings → Secrets" messages, `load_dotenv()` at import.
- [ ] After the catalog export: `backend/migrate_to_db.py`, `backend/notion_hymns.py`, `backend/fill_from_hymnary.py`, and backend/tests/test_migrate_hymns.py and test_migrate_archive.py.
- [ ] Once Alembic covers it: `backend/migrate_add_hymnal.py`, and (amendment 2026-09-26) `backend/migrate_add_hymn_facts.py` with backend/tests/test_migrate_hymn_facts.py (both deleted in slice 1). `backend/backfill_hymn_facts.py` and `backend/hymnary_facts.py` stay as ops tools.
- [ ] Any remaining dead modules (section 1, H8, H10, H11).
- [ ] `repos/users.upsert_user`, or consolidate it with `auth.upsert_from_claims`. `streamlit_auth.current_user_id` goes with its file.

**Tests, CI, dependencies**
- [ ] `pytest.ini`: `pythonpath = backend`, `testpaths = backend/tests`.
- [ ] `requirements-dev.txt`: `-r backend/requirements.txt` + pytest. Delete the root `requirements.txt`.
- [ ] `backend/requirements.txt`: remove `playwright` and `notion-client` (or move to an ops file). Check whether `requests` should be replaced by httpx.
- [ ] Rewrite backend/tests/test_foundation_setup.py:17-28 and test_docs.py (drop the `[auth]`, `/oauth2callback`, "bare app root" and `migrate_to_db` assertions).
- [ ] Extend backend/tests/test_no_streamlit_in_core.py to cover every module the API imports (or rely on test_api_app.py:104-107 once all routes are mounted).
- [ ] Delete `.github/workflows/keep-awake.yml`. Update ci.yml if anything changed. Move `shadcn` to devDependencies.

**Config and docs**
- [ ] Delete the root `.env.example`, which documents the Streamlit `[auth]` block and `http://localhost:8501/`. Keep `backend/.env.example` and `frontend/.env.example` complete.
- [ ] Fix the db/engine.py comment (line 30) and the default URL (line 24).
- [ ] Rewrite README.md (Streamlit sections at 10-14 and 48-119) and docs/manual-verification.md sections 1-3, covering Supabase, Railway, Vercel, the new Gmail callback and the invite links. Replace the create-next-app boilerplate in frontend/README.md.
- [ ] Remove the `streamlit` entry from the local `.claude/launch.json`. Update stale Streamlit mentions in docstrings (auth.py, tenancy.py, api/security.py:110-113, migrate_to_db.py:570).

**External services**
- [ ] Delete the Streamlit Cloud apps `liturgy` and `liturgy-stg`, and their stored secrets.
- [ ] Rotate the DB password and OpenAI key that lived there.
- [ ] Google OAuth client: remove the streamlit.app `/oauth2callback` and bare-root redirect URIs; keep only the frontend `/gmail/callback` URIs.
- [ ] Supabase Auth: confirm the redirect allow-list (production, localhost, any `/join` or `next` paths).
- [ ] Provide a staging environment to replace liturgy-stg (Vercel previews cannot sign in today).
- [ ] Keep-alive: confirm `keepalive.yml` has its secret, or move to an off-GitHub pinger against `/health/ready`.
- [ ] Backups: encrypted or private before enabling.

**Data**
- [ ] Export `hymn_catalog` to a versioned CSV plus a seed CLI (reuse `import_hymnal.load_rows`). Otherwise fresh databases give every new church an empty hymnal.
- [ ] Normalize any `{A,"B"}` array-literal themes (plausible legacy data).
- [ ] Optionally purge stale `oauth_states` and decide on a hard purge of soft-deleted churches.
- [ ] Verify the production schema matches the Alembic head, including `ix_hymns_church_hymnal`.

---

## 7. Open design questions for the product owner

1. **Page structure: one long page or a step-by-step flow?** Options: (a) one scrolling page as today; (b) steps (Readings → Hymns → Liturgy → Output) with a persistent summary; (c) tabs. **Recommendation:** (b) on mobile and a two-column single page on desktop, over one shared draft store. It fits the mobile-first goal, and each step maps to a slice.

2. **Editing liturgy in the preview.** Options: (a) keep separate "Your text" boxes plus a read-only preview; (b) merge them into editable section cards, each with a "Regenerate" button; (c) a rich-text editor. **Recommendation:** (b), keeping today's rule that non-blank text is used verbatim and only blank ticked sections go to the AI. Show error states on a card instead of storing error text.

3. **Word download, email only, or both? And does the bulletin include the sermon title?** Today both copies can be downloaded, only the bulletin can be emailed, and the bulletin does include the sermon title despite the caption. **Recommendation:** keep both downloads and bulletin email. Regenerate documents on demand, so there are no stale files. Ask whether the bulletin should include the sermon title; the "(for bulletin)" field label suggests yes, so fix the caption.

4. **When should hymn usage be recorded?** Options: on Prepare (today, adds only), on Save, on Email, or "replace the usage set for that date on Save". **Recommendation:** replace per date on Save. This removes stale entries and ties usage to the archived record. Always exclude the draft's own date from the "recent" filter.

5. **What should an archived service hold?** Currently lost: custom elements, translation, hymnal, reading-set choice. Options: (a) keep as today; (b) add a `custom_elements` column (needs Alembic); (c) store them under a reserved key inside the `liturgy` JSON, which needs no schema change and which Streamlit carries through untouched. **Recommendation:** (b) for custom elements and hymnal; do not persist translation. Also consider saving the unsaved draft per church in localStorage.

6. **Default service date and church timezone.** Today: server date, any weekday, normalized to the previous Sunday; the church timezone is unused. **Recommendation:** default to the next Sunday in the church's timezone, computed on the client. Use the church timezone for the 12-week window and the first-Sunday rule. Validate timezones as IANA. Weekday services (Ash Wednesday, Christmas Eve, Good Friday) need a separate decision; support them later with a manual occasion.

7. **Joining or creating an additional church.** Streamlit only offers this at zero churches. **Recommendation:** allow "Join with a code" and "Create a church" from the church switcher for everyone. The planned user-guarded endpoints already support it.

8. **Role policy.**
   - Who may grant owner, and can admins remove the owner?
   - Should members see everyone's email?
   - Can any member edit or delete any service and any hymn?
   - Should there be a "leave church" action?
   - **Recommendation:** owner-only for owner changes; admins cannot touch the owner or their own role; members may edit services and hymns (per the spec) but deleting a service needs a confirmation; add "leave church" for non-last admins.

9. **Invites.** Options: code-only multi-use (today) versus single-use, and the link format. **Recommendation:** single-use by default, with an optional "multi-use for 7 days" checkbox. Link format `https://<frontend>/join?code=…`, shown with a copy button. Fix re-inviting the same email with a partial unique index.

10. **AI hymn suggestions: auto-apply or choose?** Today the first pick per slot is applied and the other four are discarded. **Recommendation:** fill each slot with the top pick and show the others as one-tap alternatives. Respect "exclude recent" in the candidates. Show a spinner rather than step-by-step progress unless step messages are wanted, which would need SSE.

11. **Generating liturgy without an OpenAI key.** Today Generate is blocked entirely without a key, even when every section has override text. **Recommendation:** allow it: return the overrides, and show "AI not configured" only for sections that need generation.

12. **Default benediction "Halverson".** It currently prints the literal word. Options: keep it; replace it with the full Halverson text; make it a per-church setting. **Recommendation:** make it a per-church default benediction text in Settings, seeded with the current value.

13. **Free-text hymns not in the hymnal.** These were removed deliberately (commit 527ddb5). **Recommendation:** keep them removed. Users add the hymn in Settings. Revisit only if asked.

14. **Readings fixes that change behavior.** With no NT pick, the docx prints the Psalm as the "New Testament Reading". Loading an archived service leaves the old lectionary shown. Scripture matching over-matches. **Recommendation:** fix all three. NT fallback = the Second reading or Gospel from the classifier. Reload reading sets when loading a service. Tighten matching to word and verse boundaries. Given a single tester, these behavior changes are acceptable.

15. **Email recipients: To or BCC, and the default message.** Today everyone is in one To header and the default body is "Hi! Here’s the worship bulletin for this Sunday.". **Recommendation:** use BCC when there are several contacts, the sender in To, and keep the default body as an editable prefill.

16. **Hymnal management in the app.** Options: bundled PH1990 import only, CSV upload, per-church default hymnal. **Recommendation:** admins can add bundled hymnals plus a per-church default hymnal, and "Add hymn" asks which hymnal. Defer CSV upload unless another church needs it. Tell users that PH1990 has no scripture data, so matching and AI suggestions will be weaker for it.

17. **How long should Streamlit and React run side by side, and should Streamlit bugs be fixed?** **Recommendation:** freeze Streamlit (fixes for data safety only). Move the tester to React as soon as slices 2-5 reach parity, keeping the shared data compatible as described in section 4. Cut over right after slice 6, so the redirect-URI, shared-schema and connection-pool issues last only a short time.