# Slice 6a-1: the Settings Area and the Church Page

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first of slice 6a's three PRs (owner's 6a planning answers of 2026-10-05, answer 2): **the Settings area and its Church page.** After it merges, the menu at the top of every church page has a third item, **Settings**, after **Builder** and **Services**. It opens `/settings`, which goes to `/settings/church`: a "Settings" heading ("You're the owner of Example Church."), a short section nav (**Church**, and **Bulletin**, the existing Bulletin settings page until 6a-3 moves it in), and the **Church profile**. There an owner or admin changes the church's name, its time zone (the existing time zone picker, with "Use this device's time zone"), the default Bible translation, the default hymnal and the default Benediction, and taps **Save profile**; only the fields that changed are sent (`PATCH /church`), and the builder follows at once with no reload (the passages' translation, the hymnal it opens, the Benediction card that follows the church's default). A member sees the same profile as plain text with "Only admins can edit the church profile.". Leaving the page with unsaved changes asks first ("Discard unsaved changes?"), through one shared guard that the Bulletin settings page now uses too (the church menu's "Join or create a church…" asks as well). The Benediction card's hint "Admins can change it in Settings." links to the new page. No migration (Alembic head stays `0007_bulletin_images`), no new package or variable, no draft change.

**Architecture:** Backend first. `repos.churches._lock_live_church` becomes the public `lock_church` (the one church-row lock, 6a spec "Assumed interfaces"); a new `usecases/members.py` holds `lock_and_read_actor(s, church_id, actor_id)` (the 6b spec's shared helper: lock the church row, re-read the caller's role under the lock), and a new `usecases/church_admin.py` holds `require_admin_role`, the pure `clean_profile_patch` and `update_profile`, which runs the whole write in one session: lock and re-read, role check, validate, then `repos.churches.update_profile` (name, time zone and a settings merge in one read-modify-write of the locked row; every other settings key stays). `PATCH /church` (`require_admin`; `ChurchPatchIn`, every field optional, `extra="forbid"`) sits beside `GET /church` in `api/routes/me.py` and answers the same `ChurchProfileOut`. The Benediction's key-presence rule (`""` = no default) is already `liturgy_config.resolve_default_benediction`'s, so it is only tested through the new write. Frontend: `lib/settings/profile.ts` (the form, the diff, 6a's `rebaseForm`, the select items), `useUpdateChurch` in `lib/queries/church.ts` (caches the answer as the profile, refreshes `/me` and, when the hymnal changed, `/hymnals`), `components/app/leave-guard.tsx` (the Bulletin settings page's guard, moved and widened to every in-app link, with `confirmLeave` for the church menu's "Join or create a church…"), the Settings shell (`settings/layout.tsx`, `settings/page.tsx`, `components/settings/sections.ts` and `settings-nav.tsx`, the **Settings** menu item), the Church page (`components/settings/church-settings-page.tsx`, with `TimezoneCombobox` gaining a `warning` and an out-of-list value), and the Benediction hint's link in `section-card.tsx`.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy, pytest; Next 16, React 19, TypeScript 5, Base UI (Select, Combobox, AlertDialog), TanStack Query 5, sonner, Vitest 3 with Testing Library.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md`, read with its amendments; the newest two ("Amendment 2026-10-05: owner's 6a planning answers" and "later the same day": 5b returns after 6a-1 and adds Account and Contacts to this Settings shell) are binding and win where the older text differs. This plan is 6a-1 only: S's "Settings nav", "Church profile" (UX §1), `PATCH /church` (API, Semantics), the locking rule, the Benediction hand-off and the builder's invalidations.
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.2 (guards), §1.5 (errors), §1.7 (settings JSON writes under `SELECT … FOR UPDATE`), §2.2 (layers), §4.1 (routes), §4.2 (the header and nav), §4.4 (keys and invalidation), §4.8 and §4.9 (forms, 44 px, Base UI Select and Combobox).
- The 6b spec `docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md` ("Assumed interfaces" row 6a; `usecases/members.py`): where `lock_and_read_actor` lives and what it does.
- The model plan `docs/superpowers/plans/2026-10-02-printed-bulletin-2a.md` (format; its clarification 10 is the Bulletin settings page whose guard and rules this PR reuses).
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `3d5daad` = `origin/main` `875aefc` plus the Voices V1 commits and their revert `7829a57` (net: docs only), the 6a spec amendments `56e2dc5` and `3d5daad`, and this plan's commits; 2026-10-05): backend `1487 passed, 23 skipped`; frontend `734 passed` in 88 files; typecheck and lint clean; Alembic head `0007_bulletin_images` (7 revision files); 4 runbook owner markers. What exists, against S's "Assumed interfaces" (deviations in clarification 16): `timezones.is_valid_timezone` (exact, case-sensitive; `POST /churches` and `GET /church`'s `timezone_valid` use it); `TimezoneCombobox` and `lib/timezones.ts` (no `warning` prop yet); `GET /church` → `ChurchProfileOut` with `timezone_valid`, `bible_translation`, `effective_translation(_label)`, `default_hymnal`, `effective_hymnal`, `default_benediction` (from `resolve_default_benediction`: `""` kept, unset or "Halverson" = the full Halverson text, tested in `test_api_church_profile.py`); `GET /translations`, `GET /hymnals` (`effective_hymnal`); `require_admin` (the role 403 "Only church admins can do this.", no `details`); `repos.churches._lock_live_church` and `_merge_settings` (locked, no `session` parameter); **no** `lock_church`, `lock_and_read_actor`, `usecases/members.py`, `usecases/church_admin.py`, Settings layout, `sections.ts`, leave-guard module or `PATCH /church`; `handleAuthErrors` already ignores a 403 without `no_church_access` (no `forbiddenIsRole` meta exists); the Bulletin settings page (`/bulletin-settings`) has its own `beforeunload` and Back-link guard; the Benediction hint comes from `GET /liturgy/config` (`liturgy_config.py`); `scripture_fetcher` still reads `ESV_API_KEY` itself.
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch head (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -3`; the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes (T2), so T2 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand.
- No new package, no new variable, no migration.
- Branch `claude/slice-2-plan-4q33le`, at `3d5daad` plus this plan's commits (`WIP plan: slice 6a-1 …`, `Plan: slice 6a-1 (the Settings area and the Church page)`, and any later plan commit) and the runbook fix `Runbook: persona editing is no longer part of 6a (6a-1 plan review M11)`, then T1-T8. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1487 → 1523 passed, 23 → 24 skipped; frontend 734 → 756 in 88 → 92 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 14 and has no em dashes; existing copy keeps its own punctuation.
- No church id, email address, token, database URL or real person's name in any doc, commit, test or record. The tests use the fixtures' "Grace" and "Example Church" and `@example.com` addresses only.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.

### How the file directives below read
As in the 2a plan: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted.

### Baselines and counts
- Starting baselines: backend **1487 passed, 23 skipped**; frontend **734 passed in 88 files**, typecheck and lint clean; Alembic head **`0007_bulletin_images`** (7 revision files; no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new `it(`.

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +3 (`test_church_admin.py`; `test_no_streamlit_in_core.py` edited) | 1490 passed, 23 skipped | 0 | 734 in 88 |
  | T2 | +33 passed, +1 skipped (`test_church_admin.py` 19, one test in thirteen cases; `test_api_church_profile.py` 14, one test in seven cases; `test_church_admin_postgres.py` 1, skipped without `TEST_DATABASE_URL`) | 1523 passed, 24 skipped | 0 | 734 in 88 |
  | T3 | 0 | 1523 passed, 24 skipped | +4 (`profile.test.ts`) | 738 in 89 |
  | T4 | 0 | 1523 passed, 24 skipped | +3 (`leave-guard.test.tsx`; `bulletin-settings-page.test.tsx` and `app-header.test.tsx` unchanged and passing) | 741 in 90 |
  | T5 | 0 | 1523 passed, 24 skipped | +2 (`settings-layout.test.tsx`; `app-header.test.tsx` edited) | 743 in 91 |
  | T6 | 0 | 1523 passed, 24 skipped | +13 (`church-settings-page.test.tsx` 12, `timezone-combobox.test.tsx` 1) | 756 in 92 |
  | T7 | 0 | 1523 passed, 24 skipped | 0 (`liturgy-step.test.tsx` edited) | 756 in 92 |
  | T8 | 0 (`test_slice1_docs.py` edited) | 1523 passed, 24 skipped | 0 | 756 in 92 |

- CI `backend-postgres` goes from `23 passed, 1487 deselected` to `24 passed, 1523 deselected` (T2's `test_church_admin_postgres.py`; clarification 12). Locally, without `TEST_DATABASE_URL`, that test is one of the 24 skipped.

### Layering and code rules (carried)
- `usecases/members.py` and `usecases/church_admin.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains both, T1); the route is a plain `def` with no SQL and no try/except (F §2.2 rule 1); the write goes through `repos.churches` (no SQL in the usecase).
- Logs carry ids, never a setting's text (F §2.5). This PR adds no log line.
- Pages and components never call `apiFetch`: the queries use `useApi()` (F §4.5).
- Touch targets 44 px below `md`; text wraps at 375 px; no raw HTML (F §4.8); inputs `text-base md:text-sm` (the kit's `Input` and `Textarea` already are).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** is retired (branch `streamlit-frozen`, untouched); merges never reach it, so S's Streamlit compatibility notes and manual check 10 do not apply.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **The 6a planning answers of 2026-10-05** ("all recommended"; binding): (1) the pages are Church, Hymns, Liturgy prompts, then Prayers, Rubric and the Bulletin settings page moved into Settings; Contacts dropped; (2) three PRs: **6a-1** the Settings shell and Church (this plan), **6a-2** Hymns, **6a-3** Liturgy prompts, Prayers, Rubric and Bulletin settings moved in; (3) persona editing moves to "Hear it from the pews"; (4) roles as written: admins change the church, everyone reads; (5) only admins delete hymns (6a-2); (6) removing a hymnal is included (6a-2); (7) no emailing for now.
5. **Later the same day** (binding): answer 7 is reversed; 5b (Gmail, emailing, contacts) comes back after 6a-1 with its own planning round, and adds `/settings/account` and Contacts to this Settings shell. So the shell's section list is one constant later PRs add to (clarification 3).

**Later, out of scope:** 6a-2 (Hymns), 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings moved under `/settings`, `PATCH /rubric` and `PUT /church/bulletin-settings` under the lock), 5b (Account, Contacts, email), 6b (People, Danger zone).

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended).

1. **[owner-visible] What 6a-1 ships** (answer 2). The Settings area (`/settings` → `/settings/church`, its heading and section nav), the **Settings** item in the top menu, the Church page, `PATCH /church` with the locked write and the role re-read, the Benediction hint's link, and the leave guard shared with Bulletin settings. Not here: Hymns, hymnals, hymn deletion (6a-2); Liturgy prompts, Prayers, Rubric, moving Bulletin settings (6a-3); Account, Contacts, email (5b); People (6b).
2. **[owner-visible] Reaching Settings** (S "a way to reach Settings"; F §4.2). `AppNav`'s `NAV_ITEMS` gains **Settings** (`/settings`) after Builder and Services: a link in the header row from `md`, the third segment of the row under the header on a phone (each segment about 110 px at 375 px; 44 px tall). It is marked current on every `/settings/…` page. The account menu is unchanged.
3. **[owner-visible] The Settings area** (S "Settings nav"; answers 1, 5). `app/(signed-in)/(church)/settings/layout.tsx` renders, inside the church layout, a `PageHeader` "Settings" with "You're the owner of {church}." / "You're an admin of {church}." / "You're a member of {church}." (S's caption, reworded without its em dash), then the section nav (`components/settings/settings-nav.tsx`, `aria-label="Settings sections"`, from `SETTINGS_SECTIONS` in `components/settings/sections.ts`) and the section's page: on a phone the nav is a row of links above the page, from `md` a column beside it (the page `max-w-3xl`). Each link is 44 px tall below `md`, with `aria-current="page"` on the current one. After 6a-1 the list is **Church** (`/settings/church`) and **Bulletin** (`/bulletin-settings`: the existing page, unchanged, still with its **Back to Review & send**, until 6a-3 moves it under `/settings`); 6a-2 adds Hymns, 6a-3 Liturgy prompts, Prayers and Rubric, 5b Account and Contacts. `/settings` goes to `SETTINGS_SECTIONS[0].href` (`router.replace`, as the home page goes to `/builder`). Every role sees every section; each page says what a member may do.
4. **[owner-visible] The Church page for admins** (S UX §1). Under the heading "Church profile" (an `h2`; the area's `h1` is "Settings"):
   - **Church name**: a text field (200 characters). The server refuses a name with a line break or any other control character (clarification 9).
   - **Time zone**: the existing `TimezoneCombobox` with its help line. A stored zone the list does not have (`timezone_valid: false`, or one this browser lacks) shows as chosen (the combobox adds it as an item) and, while it is the stored one and not recognized, "Timezone not recognized. Choose one from the list." under the field. Under it, a text button "Use this device's time zone ({zone})" when the device's zone is in the list and differs from the field's.
   - **Default Bible translation**: a Select of `GET /translations`' items; help "Used for passage text in the builder, in every service that has not switched to another translation (saved services too, when reopened). Anyone can switch it for a single service." (clarification 11). A stored translation this server does not offer (for example `esv` without a key) shows as "ESV (not available on this server)" and stays selected. While `GET /translations` loads, or when it fails, the items come from the profile itself (the translation in effect, and a stored one that differs from it, which is then one the server does not offer), so a stored translation is never labelled as another one.
   - **Default hymnal**: a Select of the church's hymnals (`GET /hymnals`); help "The hymnal the builder opens with, in every unsaved service that has not switched to another hymnal. You can switch hymnals for a single service." (clarification 11). A stored default the church no longer has shows as "{code} (no longer in your hymnals)" and stays selected. With exactly one hymnal (counted from `GET /hymnals`' items, never from the select's items), plain text "{code} (your only hymnal)". With none, "Your church has no hymns yet, so there is no default hymnal." (S's line pointed at the Hymns page, which comes in 6a-2), also when a stored default is left over from hymns since removed.
   - **Default Benediction**: a text box (4 rows, grows, 4 000 characters); help "Pre-fills the Benediction card in each new service, and in unsaved services whose card still shows the default. Leave it blank to let the AI write the benediction." (S's line said only "each new service"; `DraftProvider.setLiturgyDefaults` also moves every unsaved card whose origin is "default", on every member's device at its next profile read). S's "Halverson" note is dropped (S amendment 2026-10-02: the word now prints the full text).
   - **Save profile** (filled, full width on a phone, 44 px, "Saving…" while pending), disabled until something would be sent. Success toasts "Profile saved.".
5. **[owner-visible] Members read a plain summary** (answer 4). A member sees "Only admins can edit the church profile." (S's banner) above the five values as text (the time zone as listed, the translation's label, the hymnal the builder uses, as "{effective} (the builder uses this; {stored} is no longer in your hymnals)" when a stored default is gone, or the no-hymnals line, the Benediction or "None. The AI writes the benediction."), with no fields and no Save: the Bulletin settings page's pattern (2a clarification 3), not S's disabled fields.
6. **Only what changed is sent; the rebase** (S "Every page"). The form keeps a baseline (`profileFormFrom(profile)`: the stored translation and hymnal when set, else the ones in effect; `""` for the hymnal when there is none) and the edits. `diffProfile` sends each field whose cleaned value (trimmed; the Benediction's line ends as `\n`) differs from the baseline's, never a `""` hymnal; so a null stored translation or hymnal is never written by a save that does not change it, and a stale one survives. Newer server data (a refetch on focus, another tab's save) rebases the form with the generic `rebaseForm` (an untouched field takes the new value, an edited one keeps the edit). After a save, the fields as sent take what was stored and a field typed while "Saving…" showed keeps the typing (the 2a page's rule).
7. **Errors.** A 422 that names fields shows each message under its field in the error colour (`role="alert"` for the fields the page draws; the combobox draws its own), marks the field `aria-invalid` and focuses the first; the toast shows the server's message as for any failed save. Editing a field clears its error. A role 403 (an admin demoted meanwhile) toasts "Only church admins can do this." and refetches the profile, so the page turns into the member's summary; a 401 or a lost church toasts nothing more (the app handles them). A failed profile read shows the usual `ErrorState` with **Retry**; the first load shows skeletons.
8. **[owner-visible] The leave guard** (S "Leave guard"; the 2a page's guard). `components/app/leave-guard.tsx` exports `<LeaveGuard when={dirty} />`: while `when`, closing or reloading the tab shows the browser's own warning (`beforeunload`, with `returnValue = ""`), and a capture-phase click listener on `document` stops a plain click (button 0, no modifier key) on any same-origin `http:` or `https:` link to another page (no `target`, no `download`; a `blob:` or `data:` link shares the page's origin but is a file, so it goes on) and asks "Discard unsaved changes?" ("Your changes on this page haven't been saved."; **Keep editing** stays; **Discard changes** clicks the link again with the guard standing aside, so the link's own handler navigates as it would have, Next's `<Link replace>` replacing, and a plain `<a>` with no handler goes on with `router.push`). So the top menu, the Settings nav and a page's own links are all covered. The church menu's **Join or create a church…** is a menu item, not a link: `church-switcher.tsx` wraps its `router.push("/welcome")` in the guard's `confirmLeave(leave)`, which runs `leave` at once, or only after **Discard changes** while a guard has unsaved edits (S's leave-guard list names this item). The Church page and the Bulletin settings page both use the guard (the latter's own `beforeunload` and Back-link code go; its nine tests pass unchanged). Not covered, as S accepts for Back/Forward and Log out: the browser's Back and Forward, Log out, and choosing another church in the church menu (S wanted the church switch covered too; left out to keep 6a-1 small, "Questions for the owner" 8).
9. **`PATCH /church`** (S API, Semantics, Models). `ChurchPatchIn` (`extra="forbid"`; `name` ≤ 200, `timezone` ≤ 64, `bible_translation` ≤ 20, `default_hymnal` ≤ 20, `default_benediction` ≤ 4000; each optional, and omitted or null means unchanged), `require_admin`, in `api/routes/me.py` beside `GET /church` (S: "the route module serving GET /church"). It answers `ChurchProfileOut` built as `GET /church` builds it, with the stored name and the role re-read under the lock. The usecase checks the fields sent in the order name, timezone, bible_translation, default_hymnal and raises the first failure with S's message and field: "Church name is required.", then "Church name can't contain line breaks or control characters." (new in 6a-1: any character of `bulletin_settings.NOT_ONE_LINE`, the C0 and C1 controls, DEL and U+2028/U+2029, as the bulletin settings' one-line fields; the name prints on one line in the bulletin's header and title, and a NUL would be a 500 on Postgres, which refuses it in text), "Timezone is required.", "Unknown timezone." (`is_valid_timezone`, so `PATCH` and `timezone_valid` agree), "Unknown or unavailable translation." (against `scripture_fetcher.available_translations()` at write time), "Choose one of your church's hymnals." (against the church's hymnal codes read under the lock). The Benediction is stored with `\r\n` as `\n` and trimmed; `""` is stored and then read back as `""` (no default; S amendment 2026-10-02's key-presence rule, already `resolve_default_benediction`'s). Nothing is written unless every field sent is valid; an empty or all-null body writes nothing and answers the profile. A smuggled `church_id` is a 422 (`extra="forbid"`). No `Idempotency-Key`, no rate-limit bucket (F §1.6, §1.8).
10. **The lock and the role re-read** (S "Locking"; the 6b spec). `repos.churches._lock_live_church` is renamed `lock_church` (same body; its two callers updated), so there is one lock helper. `usecases/members.py` (new; 6b adds its functions here) holds `lock_and_read_actor(s, church_id, actor_id) -> str`: `lock_church` (None → `Forbidden("You don't have access to this church.", details={"reason": "no_church_access"})`), then the caller's membership re-read in the same session (gone → the same 403), returning the role. `usecases/church_admin.py` (new) holds `require_admin_role(role)` (`Forbidden("Only church admins can do this.")`, no `details`), `clean_profile_patch` (pure) and `update_profile`. `repos.churches.update_profile(church_id, *, name, timezone, settings_patch, session)` sets the columns and merges the patch into the settings of the row it locks. In 6a-1 only `PATCH /church` takes this path; `PATCH /rubric` and `PUT /church/bulletin-settings` move under it with their pages in 6a-3 (clarification 16).
11. **The builder sees a change at once** (S Queries; F §4.4). `useUpdateChurch` (`lib/queries/church.ts`): on success it cancels a profile read in flight, puts the answer in `["church", id, "profile"]` (the church layout's `ChurchProvider`, the readings step's translation, the hymns step's profile and the draft's Benediction default all read it), invalidates `["me"]` (the switcher's name) and, when `default_hymnal` was sent, `["church", id, "hymnals"]` (the hymns step opens on `GET /hymnals`' `effective_hymnal`). Translation and Benediction need nothing more: a draft whose translation is null follows the profile (slice 2), and only Benediction cards whose origin is "default" follow it (slice 4, `DraftProvider.setLiturgyDefaults`). **[owner-visible] What a change reaches** (existing behaviour that 6a-1 makes reachable; no code change): the draft stores no pick when a service's translation or hymnal is set to the one in effect (`setTranslation` in `lib/draft/readings.ts`, `setHymnal` in `lib/hymns/picks.ts`), so a service where someone picked by hand the translation or hymnal that was then the default follows a later change of the default too; and a saved service reopens with the church's translation (`serviceToDraft`; its hymnal and its Benediction are the saved ones). Storing an explicit pick would be a draft-schema change, not for 6a-1. The translation and hymnal help lines say so (clarification 4), the phone check expects it (T10 Step 3), and "Questions for the owner" 11 puts it to the owner.
12. **Concurrency.** The write is one transaction holding `SELECT … FOR UPDATE` on the church row, and the settings are merged from the locked row, so a concurrent translation, rubric, prompts or bulletin settings write waits rather than being lost. SQLite ignores `FOR UPDATE`; T2's `test_the_profile_is_read_and_written_under_one_row_lock` checks (compiled for Postgres) that every read of the church row in the write asks for the lock, in the writing session. On real Postgres, T2's `test_church_admin_postgres.py` (`@pytest.mark.postgres`, run by CI's `backend-postgres`) holds a profile save inside the lock and checks that the two locked settings writers that exist today, `set_bulletin_settings` and `update_church_rubric`, wait for it and that every key survives (`Session.get(..., with_for_update=True)` does not refresh an object already loaded, so only Postgres proves the merge reads the row after the lock). S's pairing with `PUT /church/liturgy-prompts` can join it when 6a-3 adds that route. **[owner-visible] Two admins saving the profile at once:** a field only one of them changed keeps that change (only changed fields are sent, and the rebase never sends an untouched field); the same field changed by both keeps the later save (no `If-Match`, as S Risk 6 and the 2a page).
13. **The Benediction hint's link** (S "Hand-off from 4"). The hint comes from `GET /liturgy/config` ("Your church's default benediction. Admins can change it in Settings."); `SectionCard` renders its last "Settings" and what follows it ("Settings.") as a link to `/settings/church`, for every role, only on a Benediction card that follows the church's default. The link includes the full stop so the card's accessible description reads the hint unchanged (S: the word only; a test of the description pins this).
14. **[owner-visible] Every new user-facing string** (no em dashes). Top menu: "Settings". Settings area: "Settings"; "You're the owner of {church}.", "You're an admin of {church}.", "You're a member of {church}."; the nav "Church", "Bulletin" (screen readers: "Settings sections"). Church page: "Church profile"; "Church name"; "Time zone" and its help (existing); "Timezone not recognized. Choose one from the list."; "Use this device's time zone ({zone})"; "Default Bible translation" with "Used for passage text in the builder, in every service that has not switched to another translation (saved services too, when reopened). Anyone can switch it for a single service." and "{ID} (not available on this server)"; "Default hymnal" with "The hymnal the builder opens with, in every unsaved service that has not switched to another hymnal. You can switch hymnals for a single service.", "{code} (no longer in your hymnals)", "{code} (your only hymnal)", "Your church has no hymns yet, so there is no default hymnal."; "Default Benediction" with "Pre-fills the Benediction card in each new service, and in unsaved services whose card still shows the default. Leave it blank to let the AI write the benediction."; "Save profile"; "Profile saved." (toast); "Only admins can edit the church profile."; "{effective} (the builder uses this; {stored} is no longer in your hymnals)" (a member's summary); "None. The AI writes the benediction.". Leave guard (2a's words, now shared): "Discard unsaved changes?", "Your changes on this page haven't been saved.", "Discard changes", "Keep editing". From the server (S's, and one new): "Church name is required.", "Church name can't contain line breaks or control characters." (new), "Timezone is required.", "Unknown timezone.", "Unknown or unavailable translation.", "Choose one of your church's hymnals.", "Only church admins can do this.", "Too long (max {n} characters).". Reused: "Saving…", "Retry", the skeleton's "Loading", the error toasts.
15. **Docs.** T8 appends "## Slice 6a" to `docs/manual-verification.md` with items 1-8 (owner items 1-4 after the merge) and moves `test_slice1_docs.py`'s pin from the last eight `##` headings to the last nine (the new heading last). The runbook record is T10's (`### Slice 6a-1 record` before `## Backups`).
16. **Deviations from S** (each the lean choice for 6a-1; none changes a later PR's contract):
    - `lock_and_read_actor` is created in `usecases/members.py` with the 6b spec's signature (S: "if 6a lands first"); `_lock_live_church` is renamed `lock_church` as S says; `_merge_settings` is **not** renamed `merge_settings` and gains no `session` parameter yet: the profile write has its own locked read-modify-write (`repos.churches.update_profile`), and 6a-3 renames it when the prompts and prayers writes need a session.
    - Only `PATCH /church` re-reads the role under the lock in 6a-1; `PATCH /rubric` (S amendment 2026-09-26) and `PUT /church/bulletin-settings` keep `require_admin` alone until 6a-3 brings their pages.
    - S's `ProfilePatch`/`CleanProfile` dataclasses are a `dict` of the fields sent and a `(columns, settings_patch)` pair; `update_profile(church_id, actor_id, changes)` returns `{"name", "role"}` and the route completes the answer with `get_church_profile`.
    - The ESV key move (S "Hand-off from 2": `ESV_API_KEY` into `api/settings.py`, `scripture_fetcher` taking `esv_key`, deleting `streamlit_tests/test_settings_prompts_translation.py`) is **not** in 6a-1: `PATCH /church` validates against the same `available_translations()` that `GET /church` and `GET /translations` use, so they agree ("Questions for the owner" 9).
    - No `meta: { forbiddenIsRole: true }`: `handleAuthErrors` already leaves a role 403 alone; `useUpdateChurch`'s own `onError` toasts it and refetches the profile.
    - Members get a plain summary instead of disabled fields (clarification 5); the Halverson note is dropped (S amendment 2026-10-02); the no-hymnals line does not link to Hymns (6a-2 can add the link); the leave guard is a component with one small `confirmLeave(leave)` for the church menu's "Join or create a church…", not `useLeaveGuard` plus a registry, and does not cover choosing another church (clarification 8).
    - S's Postgres race test pairs the profile with the bulletin settings and rubric writers that exist today, not with `PUT /church/liturgy-prompts` (6a-3 adds that route; clarification 12).
    - The Benediction hint's link is "Settings." with its full stop, where S links the word only, so the card's accessible description still reads the hint exactly (`review-step.test.tsx` pins it; clarification 13).
    - The church name's line-break and control-character check and its message are new (S had only "required"; clarification 9).
    - The Benediction's help line says it also reaches unsaved services that still follow the default, and the translation and hymnal help lines say what a change reaches (S's lines did not; clarifications 4 and 11).
    - S's Settings caption is reworded without its em dash (clarification 3); the nav is "Church" and "Bulletin" (S's list without the pages of later PRs).

### Risks
- **A demoted admin's save** of the rubric or the bulletin settings still passes `require_admin` and writes milliseconds later (no re-read under the lock) until 6a-3; the profile is covered from this PR.
- **SQLite ignores `FOR UPDATE`.** The tests cannot show the lock itself; T2's test checks the write asks for it, and the write's shape (one session, the settings merged from the locked row) is the one `_merge_settings` and `update_church_rubric` already use in production.
- **Browser and server time zone lists can differ** (S Risk 4): a zone the browser offers but Python's tzdata lacks is a 422 "Unknown timezone." under the field. The device shortcut is offered only for a zone the browser lists.
- **Choosing another church** in the church menu does not ask before discarding unsaved Church or Bulletin settings edits (clarification 8; "Join or create a church…" does ask). Switching church remounts the page, so the edits are lost without a question, as with the browser's Back button.
- **The PATCH answer mixes two moments** (no change; plan review M10): its name and role come from the locked write, the other fields from `get_church_profile` read after the commit, so under a concurrent write the answer can carry another writer's translation or Benediction with this write's name. It is harmless: the next refetch corrects it.
- **A change of the default reaches services people may think they chose** (clarification 11; "Questions for the owner" 11): accepted as existing behaviour, said in the help lines.
- **The Settings nav's "Bulletin"** opens a page outside the Settings area (no Settings nav there, its own Back link) until 6a-3 moves it; the top menu's Settings item is not marked current on it.
- **The `default_hymnal` select** offers only the church's hymnals; picking one of several is checked by the server against the hymnals read under the lock, so a hymnal removed in the same instant is a 422 under the field.

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/usecases/members.py`, `backend/usecases/church_admin.py` (+ `backend/tests/test_church_admin.py`, and in T2 `backend/tests/test_church_admin_postgres.py`) | `lock_and_read_actor`; `require_admin_role`, then (T2) `clean_profile_patch`, `update_profile` and the Postgres race test | T1, T2 |
| `frontend/src/lib/settings/profile.ts` (+ `.test.ts`) | `ProfileForm`, `profileFormFrom`, `diffProfile`, `hasChanges`, `rebaseForm`, `translationItems`, `hymnalItems` | T3 |
| `frontend/src/components/app/leave-guard.tsx` (+ `.test.tsx`) | `LeaveGuard`, `confirmLeave`, `DISCARD_TITLE` | T4 |
| `frontend/src/components/settings/sections.ts`, `frontend/src/components/settings/settings-nav.tsx` (+ `settings-layout.test.tsx`), `frontend/src/app/(signed-in)/(church)/settings/layout.tsx`, `frontend/src/app/(signed-in)/(church)/settings/page.tsx` | the Settings area | T5 |
| `frontend/src/components/settings/church-settings-page.tsx` (+ `.test.tsx`), `frontend/src/app/(signed-in)/(church)/settings/church/page.tsx` | the Church page and its route | T6 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/repos/churches.py` | `_lock_live_church` → `lock_church`; (T2) `update_profile` | T1, T2 |
| `backend/tests/test_no_streamlit_in_core.py` | the two new modules | T1 |
| `backend/api/routes/me.py`, `backend/tests/test_api_church_profile.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | `ChurchPatchIn` and `PATCH /church`; its API tests; regenerated | T2 |
| `frontend/src/lib/api/types.ts`, `frontend/src/lib/queries/church.ts` | `ChurchPatch`; `useUpdateChurch`, `PROFILE_SAVED` | T3 |
| `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx` | uses `LeaveGuard` (its own guard removed) | T4 |
| `frontend/src/components/app/church-switcher.tsx` | "Join or create a church…" goes through `confirmLeave` | T4 |
| `frontend/src/components/app/app-nav.tsx`, `frontend/src/components/app/app-header.test.tsx` | the **Settings** item | T5 |
| `frontend/src/components/app/timezone-combobox.tsx`, `frontend/src/components/app/timezone-combobox.test.tsx` | `warning`; an out-of-list value as an item | T6 |
| `frontend/src/components/builder/liturgy/section-card.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.test.tsx` | the hint's link | T7 |
| `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py` | "## Slice 6a"; the pin of the last nine headings | T8 |
| `docs/ops-runbook.md` | "### Slice 6a-1 record" (the records PR, after the merge) | T10 |

**Counts in the PR:** 42 paths: 20 created (this plan, the sixteen new code and test files above, and the Voices V1 plan, design and rights check, which ride along), 22 modified (the seventeen code, test and API paths above, `docs/manual-verification.md`, and the 6a spec (its two amendments of 2026-10-05), the Voices decisions, the pews idea and `docs/ops-runbook.md` (the Voices notes), which ride along until merged). **Untouched:** migrations, `db/models.py`, `api/deps.py`, `api/schemas.py`, `liturgy_config.py`, `scripture_fetcher.py`, `api/routes/rubric.py`, `api/routes/bulletin_settings.py`, `bulletin_settings.py` (T2 imports its `NOT_ONE_LINE`), the draft schema, `app.py`, Streamlit.

**Task order and review batch:** T1 → T8, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T9 verifies and opens the draft PR on the owner's yes; T10 merges on the owner's yes, runs the phone check and writes the record.

---

## The server (T1-T2)

### Task 1: The church-row lock and the role re-read (S "Locking"; 6b spec `lock_and_read_actor`; clarification 10)

**Files:**
- Create: `backend/tests/test_church_admin.py`, `backend/usecases/members.py`, `backend/usecases/church_admin.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`, `backend/repos/churches.py`

- [ ] **Step 1: Write the failing tests**

`test_church_admin.py` imports `_record_church_row_access` from `test_church_settings.py` (the 2a lock check: each load of a church row, compiled for Postgres, says whether it asks `FOR UPDATE`).

**Create `backend/tests/test_church_admin.py`:**

````python
"""The church-row lock and the role re-read every church write starts with
(6a spec, "Semantics" → Locking; 6b spec, `lock_and_read_actor`), and
`usecases.church_admin` (slice 6a-1)."""
import pytest

from db import session_scope
from domain_errors import Forbidden
from repos import churches
from repos.memberships import add_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import church_admin
from usecases.members import lock_and_read_actor

NO_ACCESS = {"reason": "no_church_access"}


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com")
    admin = make_user(email="admin@example.com")
    member = make_user(email="member@example.com")
    cid = make_church(name="Example Church", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    return {"church": cid, "owner": owner, "admin": admin, "member": member}


def _actor_role(world, who: str) -> str:
    with session_scope() as s:
        return lock_and_read_actor(s, world["church"], world[who])


def test_the_role_is_read_under_the_church_row_lock(world):
    assert [_actor_role(world, who) for who in ("owner", "admin", "member")] == ["owner", "admin", "member"]
    set_role(world["admin"], world["church"], "member")        # demoted after the guard read "admin"
    assert _actor_role(world, "admin") == "member"
    with _record_church_row_access() as (reads, _writes):
        _actor_role(world, "owner")
    assert [locked for _session, locked in reads] == [True]


def test_a_church_or_a_membership_gone_is_no_church_access(world, make_user):
    outsider = make_user(email="outsider@example.com")
    with pytest.raises(Forbidden) as gone:
        with session_scope() as s:
            lock_and_read_actor(s, world["church"], outsider)
    assert (gone.value.message, gone.value.details) == ("You don't have access to this church.", NO_ACCESS)
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        _actor_role(world, "owner")
    assert deleted.value.details == NO_ACCESS


def test_require_admin_role():
    church_admin.require_admin_role("owner")
    church_admin.require_admin_role("admin")
    with pytest.raises(Forbidden) as denied:
        church_admin.require_admin_role("member")
    assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images; "
````

**with:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin; "
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_admin.py 2>&1 | tail -3` then `.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1`
**Expected** (`usecases.members` does not exist yet: `ModuleNotFoundError` above these lines; then the import check names the missing module):
```
ERROR backend/tests/test_church_admin.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```
```
1 failed, 2 passed in <t>s
```

- [ ] **Step 3: Rename the lock, add `lock_and_read_actor` and `require_admin_role`**

**In `backend/repos/churches.py`, replace:**

````python
def _lock_live_church(session, church_id) -> Optional[Church]:
    """Load the church row with SELECT ... FOR UPDATE (Postgres; SQLite ignores
    it), so a concurrent settings write waits for this transaction instead of
    overwriting it. None if the church is missing or soft-deleted."""
````

**with:**

````python
def lock_church(session, church_id) -> Optional[Church]:
    """Load the church row with SELECT ... FOR UPDATE (Postgres; SQLite ignores
    it), so a concurrent settings write waits for this transaction instead of
    overwriting it. None if the church is missing or soft-deleted. The one
    church-row lock (6a spec, "Assumed interfaces"): every church write takes
    it, directly or through usecases.members.lock_and_read_actor."""
````

**In `backend/repos/churches.py`, replace:**

````python
    with session_scope() as session:
        church = _lock_live_church(session, church_id)
        if church is None:
````

**with:**

````python
    with session_scope() as session:
        church = lock_church(session, church_id)
        if church is None:
````

**In `backend/repos/churches.py`, replace:**

````python
        church = _lock_live_church(session, church_id)
````

**with:**

````python
        church = lock_church(session, church_id)
````

**Create `backend/usecases/members.py`:**

````python
"""The church's members (6b spec, `usecases/members.py`). Slice 6a-1 creates
the module with only the helper every church write shares (6a and 6b specs,
"Assumed interfaces"); 6b adds its member and invite functions here.

lock_and_read_actor runs inside the write's own session: it locks the church
row (repos.churches.lock_church, SELECT ... FOR UPDATE) and re-reads the
caller's membership under that lock, so the role a write acts on is the one
stored now, never the snapshot require_church or require_admin read in an
earlier transaction. No FastAPI, Starlette or Streamlit here
(usecases/__init__.py).
"""
import uuid

from sqlalchemy.orm import Session

from domain_errors import Forbidden
from repos import churches, memberships

# require_church's own 403 (api/deps.py): a church soft-deleted, or a
# membership removed, after the guard ran looks exactly like no access.
NO_ACCESS_MESSAGE = "You don't have access to this church."


def lock_and_read_actor(s: Session, church_id: uuid.UUID, actor_id: uuid.UUID) -> str:
    """Lock the church row in `s` and return the caller's role read under the
    lock ("owner", "admin" or "member"). Raises Forbidden (403, details.reason
    no_church_access) when the church is missing or soft-deleted, or the
    caller is no longer a member."""
    if churches.lock_church(s, church_id) is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    role = memberships.get_role(actor_id, church_id, session=s)
    if role is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    return role
````

**Create `backend/usecases/church_admin.py`:**

````python
"""Church administration (6a spec, `usecases/church_admin.py`): the writes an
owner or admin makes to the church itself. Slice 6a-1 has the profile
(PATCH /church); 6a-2, 6a-3 and 6b add their writes here.

Every write opens one session, starts with
usecases.members.lock_and_read_actor (the church-row lock and the caller's
role re-read under it) and then require_admin_role on that re-read role, so
an admin demoted after require_admin ran gets the role 403 and nothing is
written. No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
from domain_errors import Forbidden
from tenancy import is_admin

# require_admin's message (api/deps.py): one wording for the role 403.
ADMINS_ONLY_MESSAGE = "Only church admins can do this."


def require_admin_role(role: str) -> None:
    """Raise the role 403 (no details, so the client never treats it as a lost
    church) unless `role` is owner or admin."""
    if not is_admin(role):
        raise Forbidden(ADMINS_ONLY_MESSAGE)
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_admin.py backend/tests/test_church_settings.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `grep -rn "_lock_live_church" backend --include=*.py; echo "old name grep exit $?"` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`16 passed in <t>s`; `old name grep exit 1`; `1490 passed, 23 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/repos/churches.py backend/usecases/members.py backend/usecases/church_admin.py backend/tests/test_church_admin.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Slice 6a-1: the church-row lock and the role re-read under it" -m "repos.churches._lock_live_church becomes lock_church, the one church-row
lock. usecases/members.py (6b's module, created here with only this)
holds lock_and_read_actor: lock the church row and re-read the caller's
role under the lock, or the no_church_access 403 when the church or the
membership is gone. usecases/church_admin.py starts with
require_admin_role (the role 403, no details)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1490 passed, 23 skipped`; frontend `734 passed` in 88 files.

### Task 2: `PATCH /church` (S API, Semantics, Models; clarifications 9, 10, 12)

**Files:**
- Create: `backend/tests/test_church_admin_postgres.py`
- Modify: `backend/tests/test_church_admin.py`, `backend/tests/test_api_church_profile.py`, `backend/repos/churches.py`, `backend/usecases/church_admin.py`, `backend/api/routes/me.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (regenerated)

- [ ] **Step 1: Write the failing tests**

`test_only_the_fields_sent_are_written_and_other_settings_stay` and `test_a_profile_save_keeps_every_other_setting` seed every key the app keeps in `churches.settings` (`bible_translation`, `default_hymnal`, `default_benediction`, `bulletin`, `rubric`, `liturgy_prompts`, `prayer_library`) plus one it does not know, save the translation, the Benediction and the hymnal, and compare the whole dict, so a write that replaced the settings instead of merging them fails. The ESV case runs where it is enforced: `PATCH` reads `scripture_fetcher.available_translations()`, which reads `ESV_API_KEY` at call time, so the test sets and unsets that variable. `test_church_admin_postgres.py` is skipped without `TEST_DATABASE_URL`.

**In `backend/tests/test_church_admin.py`, replace:**

````python
from domain_errors import Forbidden
from repos import churches
from repos.memberships import add_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import church_admin
````

**with:**

````python
from db.models import Church
from domain_errors import Forbidden, InvalidInput
from repos import churches
from repos.hymns import add_hymn
from repos.memberships import add_membership, remove_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import church_admin, church_profile
````

**Append to `backend/tests/test_church_admin.py`:**

````python


# --- PATCH /church: clean_profile_patch and update_profile (slice 6a-1) ------------------------------

TRANSLATIONS = ("web", "kjv", "asv")


@pytest.mark.parametrize("changes, field, message", [
    ({"name": "   "}, "name", "Church name is required."),
    ({"name": "Gr\x00ace"}, "name", "Church name can't contain line breaks or control characters."),
    ({"name": "Grace\nChurch"}, "name", "Church name can't contain line breaks or control characters."),
    ({"timezone": ""}, "timezone", "Timezone is required."),
    ({"timezone": "Mars/Olympus"}, "timezone", "Unknown timezone."),
    ({"timezone": "America/New York"}, "timezone", "Unknown timezone."),
    ({"timezone": "../etc"}, "timezone", "Unknown timezone."),
    ({"timezone": "america/new_york"}, "timezone", "Unknown timezone."),
    ({"bible_translation": "xyz"}, "bible_translation", "Unknown or unavailable translation."),
    ({"bible_translation": "esv"}, "bible_translation", "Unknown or unavailable translation."),
    ({"default_hymnal": "PH1990"}, "default_hymnal", "Choose one of your church's hymnals."),
    ({"default_hymnal": "PH1990", "bible_translation": "xyz", "timezone": "x", "name": " "}, "name",
     "Church name is required."),
    ({"default_hymnal": "PH1990", "bible_translation": "xyz"}, "bible_translation",
     "Unknown or unavailable translation."),
])
def test_a_bad_field_is_named_and_the_first_in_order_wins(changes, field, message):
    with pytest.raises(InvalidInput) as bad:
        church_admin.clean_profile_patch(changes, translations=TRANSLATIONS, church_hymnals=("GG2013",))
    assert (bad.value.field, bad.value.message) == (field, message)


def test_the_fields_sent_are_cleaned_and_nothing_else():
    clean = church_admin.clean_profile_patch
    assert clean({}, translations=TRANSLATIONS, church_hymnals=()) == ({}, {})
    assert clean({"name": " Example Church ", "timezone": " America/Chicago ", "bible_translation": "kjv",
                  "default_hymnal": "GG2013", "default_benediction": "  Go in peace.\r\nAmen.\r\n"},
                 translations=TRANSLATIONS, church_hymnals=("GG2013",)) == (
        {"name": "Example Church", "timezone": "America/Chicago"},
        {"bible_translation": "kjv", "default_hymnal": "GG2013", "default_benediction": "Go in peace.\nAmen."},
    )
    assert clean({"default_benediction": "   "}, translations=(), church_hymnals=()) == ({}, {"default_benediction": ""})


def _church(world) -> dict:
    return churches.get_church(world["church"])


# Every key the app keeps in churches.settings, plus one it does not know: a profile save changes only its own.
EVERY_SETTING = {
    "bible_translation": "esv",
    "default_hymnal": "HL1955",
    "default_benediction": "Halverson",
    "bulletin": {"phone": "555-0100", "starred": ["call_to_worship"]},
    "rubric": {"prefer_familiar": False},
    "liturgy_prompts": {"benediction": "Go."},
    "prayer_library": {"confession": ["Merciful God, we confess."]},
    "foo": 1,
}


def test_only_the_fields_sent_are_written_and_other_settings_stay(world, monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    add_hymn(world["church"], hymnal="GG2013", number=1, title="Holy, Holy, Holy")
    churches.update_church(world["church"], settings=EVERY_SETTING)
    stored = church_admin.update_profile(world["church"], world["admin"], {"name": "Example Church Two"})
    assert stored == {"name": "Example Church Two", "role": "admin"}
    church = _church(world)
    assert (church["name"], church["timezone"]) == ("Example Church Two", "America/New_York")
    assert church["settings"] == EVERY_SETTING

    church_admin.update_profile(world["church"], world["owner"], {
        "bible_translation": "kjv", "default_benediction": "Go in peace.", "default_hymnal": "GG2013"})
    assert _church(world)["settings"] == {**EVERY_SETTING, "bible_translation": "kjv",
                                          "default_benediction": "Go in peace.", "default_hymnal": "GG2013"}

    church_admin.update_profile(world["church"], world["owner"], {"default_benediction": ""})
    assert _church(world)["settings"]["default_benediction"] == ""
    assert church_profile.get_church_profile(world["church"]).default_benediction == ""


def test_one_bad_field_writes_nothing(world):
    with pytest.raises(InvalidInput):
        church_admin.update_profile(world["church"], world["owner"],
                                    {"name": "Renamed", "default_benediction": "Go.", "bible_translation": "xyz"})
    church = _church(world)
    assert (church["name"], church["settings"]) == ("Example Church", {})


def test_the_default_hymnal_must_be_one_the_church_has(world):
    add_hymn(world["church"], hymnal="GG2013", number=1, title="Holy, Holy, Holy")
    with pytest.raises(InvalidInput) as bad:
        church_admin.update_profile(world["church"], world["owner"], {"default_hymnal": "PH1990"})
    assert bad.value.field == "default_hymnal"
    church_admin.update_profile(world["church"], world["owner"], {"default_hymnal": "GG2013"})
    assert _church(world)["settings"] == {"default_hymnal": "GG2013"}


def test_a_demoted_admin_or_a_removed_member_writes_nothing(world):
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    with pytest.raises(Forbidden) as demoted:
        church_admin.update_profile(world["church"], world["admin"], {"name": "Renamed"})
    assert (demoted.value.message, demoted.value.details) == ("Only church admins can do this.", None)
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        church_admin.update_profile(world["church"], world["member"], {"name": "Renamed"})
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        church_admin.update_profile(world["church"], world["owner"], {"name": "Renamed"})
    assert deleted.value.details == NO_ACCESS
    with session_scope() as s:
        assert s.get(Church, world["church"]).name == "Example Church"


def test_the_profile_is_read_and_written_under_one_row_lock(world):
    with _record_church_row_access() as (reads, writes):
        church_admin.update_profile(world["church"], world["owner"], {"name": "Renamed", "bible_translation": "kjv"})
    assert len(writes) == 1
    assert reads and all(session is writes[0] and locked for session, locked in reads)
````

**In `backend/tests/test_api_church_profile.py`, replace:**

````python
from repos import churches
````

**with:**

````python
from repos import churches
from repos.hymns import add_hymn
````

**Append to `backend/tests/test_api_church_profile.py`:**

````python


# --- PATCH /church (slice 6a-1) ------------------------------------------------------------------------

def _patch(client, church_id, body, email=EMAIL):
    return client.patch("/church", headers=church_headers(email, church_id), json=body)


def test_an_admin_changes_the_profile_and_get_answers_the_same(client, make_user, make_church, no_esv_key):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    add_membership(make_user(email="admin@example.com"), cid, "admin")
    r = _patch(client, cid, {"name": " Example Church ", "timezone": "America/Chicago",
                             "bible_translation": "kjv", "default_benediction": "Go in peace."},
               email="admin@example.com")
    assert r.status_code == 200, r.text
    assert r.json() == {**_profile(client, cid, email="admin@example.com"), "role": "admin"}
    assert {k: r.json()[k] for k in ("name", "timezone", "bible_translation", "default_benediction")} == {
        "name": "Example Church", "timezone": "America/Chicago", "bible_translation": "kjv",
        "default_benediction": "Go in peace."}


def test_an_empty_or_all_null_patch_changes_nothing(client, make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    before = _profile(client, cid)
    for body in ({}, {"name": None, "timezone": None, "default_benediction": None}):
        r = _patch(client, cid, body)
        assert (r.status_code, r.json()) == (200, before), body


def test_a_member_cannot_change_the_profile(client, make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    add_membership(make_user(email="member@example.com"), cid, "member")
    for body in ({"name": "Renamed"}, {"bible_translation": "kjv"}):
        r = _patch(client, cid, body, email="member@example.com")
        assert r.status_code == 403, r.text
        error = dict(r.json()["error"])
        error.pop("request_id")
        assert error == {"code": "forbidden", "message": "Only church admins can do this."}
    assert _profile(client, cid)["name"] == "Grace"


@pytest.mark.parametrize("body, field, message", [
    ({"name": "  "}, "name", "Church name is required."),
    ({"name": "Gr\x00ace"}, "name", "Church name can't contain line breaks or control characters."),
    ({"timezone": "Mars/Olympus"}, "timezone", "Unknown timezone."),
    ({"bible_translation": "klingon"}, "bible_translation", "Unknown or unavailable translation."),
    ({"default_hymnal": "PH1990"}, "default_hymnal", "Choose one of your church's hymnals."),
    ({"name": "x" * 201}, "name", "Too long (max 200 characters)."),
    ({"default_benediction": "x" * 4001}, "default_benediction", "Too long (max 4000 characters)."),
])
def test_a_bad_field_is_a_422_naming_it_and_nothing_is_written(client, make_user, make_church, body, field, message):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    r = _patch(client, cid, {"default_benediction": "Go.", **body})
    assert r.status_code == 422, r.text
    assert (r.json()["error"]["code"], r.json()["error"]["fields"]) == ("invalid_request", {field: message})
    assert _profile(client, cid)["default_benediction"] == HALVERSON


def test_a_church_id_in_the_body_is_refused_and_isolation(client, isolation_world):
    world = isolation_world
    r = _patch(client, world.church_a, {"name": "Taken", "church_id": str(world.church_b)}, email=world.a)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    assert_church_isolated(client, "PATCH", "/church", world=world, json={"name": "Church A"})
    assert churches.get_church(world.church_b)["name"] == "Church B"


def test_an_unavailable_stored_translation_survives_a_name_change(client, make_user, make_church, no_esv_key):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    churches.set_church_translation(cid, "esv")
    r = _patch(client, cid, {"name": "Renamed"})
    assert (r.status_code, r.json()["bible_translation"], r.json()["effective_translation"]) == (200, "esv", "web")


def test_the_esv_is_accepted_only_where_its_key_is_set(client, make_user, make_church, monkeypatch):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    r = _patch(client, cid, {"bible_translation": "esv"})
    assert (r.status_code, r.json()["error"]["fields"]) == (
        422, {"bible_translation": "Unknown or unavailable translation."})
    assert _profile(client, cid)["bible_translation"] is None

    monkeypatch.setenv("ESV_API_KEY", "test-key")            # scripture_fetcher reads it at call time
    r = _patch(client, cid, {"bible_translation": "esv"})
    assert r.status_code == 200, r.text
    assert (r.json()["bible_translation"], r.json()["effective_translation"]) == ("esv", "esv")


def test_a_profile_save_keeps_every_other_setting(client, make_user, make_church, no_esv_key):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    add_hymn(cid, hymnal="GG2013", number=1, title="Holy, Holy, Holy")
    every = {"bible_translation": "esv", "default_hymnal": "HL1955", "default_benediction": "Halverson",
             "bulletin": {"phone": "555-0100"}, "rubric": {"prefer_familiar": False},
             "liturgy_prompts": {"benediction": "Go."}, "prayer_library": {"confession": ["Merciful God."]},
             "foo": 1}
    churches.update_church(cid, settings=every)
    r = _patch(client, cid, {"bible_translation": "kjv", "default_benediction": "", "default_hymnal": "GG2013"})
    assert r.status_code == 200, r.text
    assert churches.get_church(cid)["settings"] == {**every, "bible_translation": "kjv",
                                                    "default_benediction": "", "default_hymnal": "GG2013"}
````

**Create `backend/tests/test_church_admin_postgres.py`:**

````python
"""PATCH /church's write on real Postgres (6a spec, "Semantics" → Locking;
slice 6a-1): while a profile save holds the church-row lock, the other
locked settings writers (the bulletin settings, the rubric) wait for it, and
when it commits every key survives.

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs it. SQLite
ignores FOR UPDATE, so test_church_admin.py can only check that the lock is
asked for; this is the proof that the profile's merge reads the row after the
lock. Forcing the race: clean_profile_patch, which update_profile calls
through the module attribute after taking the lock, waits until the test lets
it go. A save that never gets there makes the test fail after 10 s instead
of passing vacuously.
"""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from repos import churches
from repos.churches import create_church
from repos.users import ensure_user
from usecases import church_admin

pytestmark = pytest.mark.postgres


@pytest.fixture
def world(pg_db):
    owner = ensure_user("owner@example.com", "Owner").id
    return owner, create_church(name="Grace", timezone="America/New_York", owner_user_id=owner)


def test_other_settings_writers_wait_for_a_profile_save_and_every_key_survives(world, monkeypatch):
    owner, church_id = world
    inside, release = threading.Event(), threading.Event()
    clean = church_admin.clean_profile_patch

    def held(*args, **kwargs):
        inside.set()                   # update_profile holds the church-row lock here
        assert release.wait(10), "the test never released the profile save"
        return clean(*args, **kwargs)

    monkeypatch.setattr(church_admin, "clean_profile_patch", held)
    with ThreadPoolExecutor(3) as pool:
        profile = pool.submit(church_admin.update_profile, church_id, owner, {"default_benediction": "Go in peace."})
        assert inside.wait(10), "the profile save never took the lock"
        bulletin = pool.submit(churches.set_bulletin_settings, church_id, {"phone": "555-0100"})
        rubric = pool.submit(churches.update_church_rubric, church_id, {"prefer_familiar": False})
        done = threading.Event()
        done.wait(1)                   # time for either writer to finish if nothing held it
        assert not bulletin.done() and not rubric.done(), "the other settings writers did not wait for the lock"
        release.set()
        profile.result(10)
        bulletin.result(10)
        rubric.result(10)
    settings = churches.get_church(church_id)["settings"]
    assert settings["default_benediction"] == "Go in peace."
    assert settings["bulletin"] == {"phone": "555-0100"}
    assert settings["rubric"] == {"prefer_familiar": False}
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_admin.py backend/tests/test_api_church_profile.py 2>&1 | tail -3`
**Expected** (`clean_profile_patch` and `update_profile` do not exist yet, and `PATCH /church` is a 405):
```
FAILED backend/tests/test_api_church_profile.py::test_the_esv_is_accepted_only_where_its_key_is_set
FAILED backend/tests/test_api_church_profile.py::test_a_profile_save_keeps_every_other_setting
33 failed, 12 passed in <t>s
```

- [ ] **Step 3: Write the repo write, the usecase and the route**

**Append to `backend/repos/churches.py`:**

````python


def update_profile(church_id, *, name=None, timezone=None, settings_patch=None,
                   session: Optional[Session] = None) -> bool:
    """PATCH /church (6a spec): set the name and the time zone when given and
    merge `settings_patch` into the settings JSON, in one read-modify-write of
    the row lock_church locks, so every other settings key stays as stored.
    False, with nothing written, when the church is missing or soft-deleted."""
    if session is not None:
        return _update_profile(session, church_id, name, timezone, settings_patch)
    with session_scope() as own:
        return _update_profile(own, church_id, name, timezone, settings_patch)


def _update_profile(session, church_id, name, timezone, settings_patch) -> bool:
    church = lock_church(session, church_id)
    if church is None:
        return False
    if name is not None:
        church.name = name
    if timezone is not None:
        church.timezone = timezone
    if settings_patch:
        church.settings = {**(church.settings or {}), **settings_patch}
    return True
````

**In `backend/usecases/church_admin.py`, replace:**

````python
from domain_errors import Forbidden
from tenancy import is_admin

# require_admin's message (api/deps.py): one wording for the role 403.
ADMINS_ONLY_MESSAGE = "Only church admins can do this."
````

**with:**

````python
import re
import uuid
from collections.abc import Collection, Mapping

import scripture_fetcher
from db import session_scope
from bulletin_settings import NOT_ONE_LINE
from domain_errors import Forbidden, InvalidInput
from repos import churches
from repos import hymns as hymn_repo
from tenancy import is_admin
from timezones import is_valid_timezone
from usecases.members import lock_and_read_actor

# require_admin's message (api/deps.py): one wording for the role 403.
ADMINS_ONLY_MESSAGE = "Only church admins can do this."

# The church's name prints on one line (the bulletin's header and title): no control character (NUL, which
# Postgres refuses in text, among them), no C1 control and no U+2028/U+2029, as the bulletin settings' lines.
_NOT_ONE_LINE = re.compile(f"[{NOT_ONE_LINE}]")
````

**Append to `backend/usecases/church_admin.py`:**

````python


def clean_profile_patch(changes: Mapping[str, str], *, translations: Collection[str],
                        church_hymnals: Collection[str]) -> tuple[dict[str, str], dict[str, str]]:
    """PATCH /church's provided fields, cleaned and checked (pure).

    `changes` holds only the fields sent (a null is not sent). The checks run
    in the order name, timezone, bible_translation, default_hymnal, and the
    first failure raises InvalidInput naming its field. The name and the time
    zone are trimmed; the name must hold no control character or line
    separator (bulletin_settings.NOT_ONE_LINE: it prints on one line); the time zone must be exactly an IANA name
    (timezones.is_valid_timezone, as POST /churches and GET /church's
    timezone_valid); the translation must be one of `translations` (offered on
    this deployment now) and the hymnal one of `church_hymnals`; the
    Benediction's line ends become "\\n" and it is trimmed, and "" is kept (the
    church then has no default Benediction). Returns (columns, settings_patch).
    """
    columns: dict[str, str] = {}
    settings: dict[str, str] = {}
    if "name" in changes:
        columns["name"] = changes["name"].strip()
        if not columns["name"]:
            raise InvalidInput("Church name is required.", field="name")
        if _NOT_ONE_LINE.search(columns["name"]):
            raise InvalidInput("Church name can't contain line breaks or control characters.", field="name")
    if "timezone" in changes:
        columns["timezone"] = changes["timezone"].strip()
        if not columns["timezone"]:
            raise InvalidInput("Timezone is required.", field="timezone")
        if not is_valid_timezone(columns["timezone"]):
            raise InvalidInput("Unknown timezone.", field="timezone")
    if "bible_translation" in changes:
        settings["bible_translation"] = changes["bible_translation"].strip()
        if settings["bible_translation"] not in translations:
            raise InvalidInput("Unknown or unavailable translation.", field="bible_translation")
    if "default_hymnal" in changes:
        settings["default_hymnal"] = changes["default_hymnal"].strip()
        if settings["default_hymnal"] not in church_hymnals:
            raise InvalidInput("Choose one of your church's hymnals.", field="default_hymnal")
    if "default_benediction" in changes:
        text = changes["default_benediction"].replace("\r\n", "\n").replace("\r", "\n")
        settings["default_benediction"] = text.strip()
    return columns, settings


def update_profile(church_id: uuid.UUID, actor_id: uuid.UUID, changes: Mapping[str, str]) -> dict:
    """PATCH /church (6a spec, Semantics): write the provided fields, all or
    nothing, in one transaction under the church-row lock, with the caller's
    role re-read under it. Returns {"name", "role"}: the name as stored and
    the caller's re-read role (for the answer, which GET /church's profile
    completes)."""
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        require_admin_role(role)
        hymnals = ([h.code for h in hymn_repo.hymnal_summaries(church_id, session=s)]
                   if "default_hymnal" in changes else [])
        offered = [tid for tid, _label in scripture_fetcher.available_translations()]
        columns, settings_patch = clean_profile_patch(changes, translations=offered, church_hymnals=hymnals)
        churches.update_profile(church_id, **columns, settings_patch=settings_patch, session=s)
        name = churches.get_church(church_id, session=s)["name"]
    return {"name": name, "role": role}
````

**In `backend/api/routes/me.py`, replace:**

````python

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.schemas import ChurchOut, ChurchProfileOut, MeOut, UserOut
from repos.churches import list_user_churches
from usecases import church_profile
````

**with:**

````python
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from api.schemas import ChurchOut, ChurchProfileOut, MeOut, UserOut
from repos.churches import list_user_churches
from usecases import church_admin, church_profile
````

**Append to `backend/api/routes/me.py`:**

````python


class ChurchPatchIn(BaseModel):
    """PATCH /church (6a spec, Models): every field optional; omitted or null
    leaves it unchanged. "" for default_benediction means no default."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=200)
    timezone: str | None = Field(None, max_length=64)
    bible_translation: str | None = Field(None, max_length=20)
    default_hymnal: str | None = Field(None, max_length=20)
    default_benediction: str | None = Field(None, max_length=4000)


@router.patch("/church", response_model=ChurchProfileOut,
              responses=error_responses(401, 403, 422, 503))
def update_church(payload: ChurchPatchIn, active: ActiveChurch = Depends(require_admin),
                  user: CurrentUser = Depends(get_current_user)) -> ChurchProfileOut:
    """Owners and admins change the church's profile: only the fields sent,
    in one locked transaction (usecases.church_admin.update_profile). Answers
    the profile as GET /church does, with the role re-read under the lock."""
    stored = church_admin.update_profile(active.id, user.id, payload.model_dump(exclude_none=True))
    profile = church_profile.get_church_profile(active.id)
    return ChurchProfileOut(id=active.id, name=stored["name"], role=stored["role"], **asdict(profile))
````

- [ ] **Step 4: Regenerate the API files, see the tests pass, and the suites**

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git diff --stat -- frontend/src/lib/api | tail -1` then `.venv/bin/python -m pytest -q backend/tests/test_church_admin.py backend/tests/test_api_church_profile.py backend/tests/test_openapi_contract.py backend/tests/test_route_guards.py backend/tests/test_church_settings.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
` 2 files changed, 256 insertions(+), 1 deletion(-)`; `63 passed in <t>s`; `1523 passed, 24 skipped in <t>s`; `typecheck 0`, `lint 0` (the new `ChurchPatchIn` type is not used until T3).

With a local throwaway Postgres (never a real database), `TEST_DATABASE_URL=postgresql://postgres@localhost:<port>/postgres .venv/bin/python -m pytest -q -m postgres 2>&1 | tail -1` gives `24 passed, 1523 deselected, 1 warning in <t>s` (the new race test among them); without one, CI's `backend-postgres` runs it.

- [ ] **Step 5: Commit**

```bash
git add backend/repos/churches.py backend/usecases/church_admin.py backend/api/routes/me.py backend/tests/test_church_admin.py backend/tests/test_api_church_profile.py backend/tests/test_church_admin_postgres.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Slice 6a-1: PATCH /church" -m "Owners and admins change the church's name, time zone, default
translation, default hymnal and default Benediction: only the fields
sent, checked in S's order with S's messages, all or nothing, in one
transaction that locks the church row and re-reads the caller's role
under it. The settings are merged from the locked row, so every other
key stays (a Postgres test holds a save in the lock and checks the
bulletin settings and rubric writers wait); a blank Benediction is stored
as \"no default\"; a name with a control character is refused. The
answer is GET /church's profile. OpenAPI and the types regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1523 passed, 24 skipped`; frontend `734 passed` in 88 files.

## The app (T3-T7)

### Task 3: The Church form's rules and `useUpdateChurch` (clarifications 6, 7, 11)

**Files:**
- Create: `frontend/src/lib/settings/profile.test.ts`, `frontend/src/lib/settings/profile.ts`
- Modify: `frontend/src/lib/api/types.ts`, `frontend/src/lib/queries/church.ts`

- [ ] **Step 1: Write the failing test**

**Create `frontend/src/lib/settings/profile.test.ts`:**

````ts
import { describe, expect, it } from "vitest";

import { churchProfile, hymnals, translations } from "@/test/fixtures";

import { diffProfile, hasChanges, hymnalItems, profileFormFrom, rebaseForm, translationItems } from "./profile";

describe("the Church page's form (slice 6a-1)", () => {
  it("starts at the stored values, or the ones in effect, and sends only what changed, cleaned", () => {
    const base = profileFormFrom(churchProfile({ bible_translation: null, default_hymnal: null }));
    expect(base).toMatchObject({ name: "Grace", timezone: "America/New_York", bible_translation: "web", default_hymnal: "GG2013" });
    expect(diffProfile(base, base)).toEqual({});
    expect(hasChanges(base, { ...base, name: " Grace " })).toBe(false);
    expect(diffProfile(base, { ...base, name: " Example Church " })).toEqual({ name: "Example Church" });
    expect(diffProfile(base, { ...base, default_benediction: "" })).toEqual({ default_benediction: "" });
    expect(diffProfile(base, { ...base, default_benediction: " Go in peace.\r\nAmen. " })).toEqual({
      default_benediction: "Go in peace.\nAmen.",
    });
    expect(diffProfile(base, { ...base, bible_translation: "kjv", default_hymnal: "PH1990" })).toEqual({
      bible_translation: "kjv",
      default_hymnal: "PH1990",
    });
  });

  it("keeps a stale stored translation or hymnal, and never sends a hymnal when the church has none", () => {
    const stale = profileFormFrom(churchProfile({ bible_translation: "esv", default_hymnal: "PH1990" }));
    expect([stale.bible_translation, stale.default_hymnal]).toEqual(["esv", "PH1990"]);
    expect(diffProfile(stale, { ...stale, name: "Renamed" })).toEqual({ name: "Renamed" });
    const none = profileFormFrom(churchProfile({ default_hymnal: null, effective_hymnal: null }));
    expect(none.default_hymnal).toBe("");
    expect(diffProfile({ ...none, default_hymnal: "GG2013" }, none)).toEqual({});
  });

  it("rebases on newer data: untouched fields take it, edited ones keep the edit", () => {
    const base = profileFormFrom(churchProfile());
    const edited = { ...base, default_benediction: "Go in peace." };
    const next = profileFormFrom(churchProfile({ name: "Grace Renamed" }));
    const rebased = rebaseForm(base, edited, next);
    expect(rebased).toEqual({ ...next, default_benediction: "Go in peace." });
    expect(diffProfile(next, rebased)).toEqual({ default_benediction: "Go in peace." });
  });

  it("lists a stored translation or hymnal that is no longer offered, and nothing more", () => {
    expect(translationItems(translations(), "kjv")).toEqual({
      web: "World English Bible (WEB)",
      kjv: "King James Version (KJV)",
      esv: "English Standard Version (ESV)",
    });
    expect(translationItems(translations({ items: [{ id: "web", label: "World English Bible (WEB)" }] }), "esv")).toEqual({
      web: "World English Bible (WEB)",
      esv: "ESV (not available on this server)",
    });
    expect(hymnalItems(hymnals(), null)).toEqual({ GG2013: "GG2013" });
    expect(hymnalItems(hymnals(), "PH1990")).toEqual({ GG2013: "GG2013", PH1990: "PH1990 (no longer in your hymnals)" });
  });
});
````

- [ ] **Step 2: See it fail**

Run: `(cd frontend && npx vitest run src/lib/settings/profile.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`profile.ts` does not exist yet):
```
 FAIL  |unit| src/lib/settings/profile.test.ts [ src/lib/settings/profile.test.ts ]
      Tests  no tests
```

- [ ] **Step 3: Write the form's rules and the mutation**

`useUpdateChurch` is used by the Church page (T6), whose tests cover its cache work and its toasts.

**In `frontend/src/lib/api/types.ts`, replace:**

````ts
export type ChurchProfile = components["schemas"]["ChurchProfileOut"];
````

**with:**

````ts
export type ChurchProfile = components["schemas"]["ChurchProfileOut"];
/** `PATCH /church` (slice 6a-1): only the fields that change; omitted (or null) leaves one as stored. */
export type ChurchPatch = components["schemas"]["ChurchPatchIn"];
````

**Create `frontend/src/lib/settings/profile.ts`:**

````ts
/**
 * The Church page's form (slice 6a-1; 6a spec "Church profile"). The form
 * keeps a baseline (built from the last profile the server sent) and the
 * current edits; a save sends only the fields that differ, trimmed as the
 * server trims them, so a field nobody touched is never written and another
 * admin's change to it is never put back.
 */
import type { ChurchPatch, ChurchProfile, Hymnals, Translations } from "@/lib/api/types";

export type ProfileForm = {
  name: string;
  timezone: string;
  bible_translation: string;
  default_hymnal: string;
  default_benediction: string;
};

const FIELDS = ["name", "timezone", "bible_translation", "default_hymnal", "default_benediction"] as const;

/**
 * The form a profile starts at, and the baseline: the stored translation and
 * hymnal when set (even one no longer offered), else the ones in effect; ""
 * for the hymnal when the church has none (the field is then not shown).
 */
export function profileFormFrom(p: ChurchProfile): ProfileForm {
  return {
    name: p.name,
    timezone: p.timezone,
    bible_translation: p.bible_translation ?? p.effective_translation,
    default_hymnal: p.default_hymnal ?? p.effective_hymnal ?? "",
    default_benediction: p.default_benediction,
  };
}

/** A field as the server stores it: trimmed, and the Benediction's line ends as "\n". */
function cleaned(field: keyof ProfileForm, value: string): string {
  return (field === "default_benediction" ? value.replace(/\r\n?/g, "\n") : value).trim();
}

/** `PATCH /church`'s body: each field whose cleaned value differs from the baseline's, cleaned. Never a "" hymnal. */
export function diffProfile(baseline: ProfileForm, current: ProfileForm): ChurchPatch {
  const patch: ChurchPatch = {};
  for (const field of FIELDS) {
    const value = cleaned(field, current[field]);
    if (value === cleaned(field, baseline[field])) continue;
    if (field === "default_hymnal" && value === "") continue;
    patch[field] = value;
  }
  return patch;
}

/** True while a save would send something. */
export function hasChanges(baseline: ProfileForm, current: ProfileForm): boolean {
  return Object.keys(diffProfile(baseline, current)).length > 0;
}

/**
 * 6a's rebase rule for a settings form: newer server data (`next`) replaces
 * each field the user has not edited (still equal to `oldBaseline`), and each
 * edited field keeps the edit.
 */
export function rebaseForm<T extends Record<string, string>>(oldBaseline: T, current: T, next: T): T {
  const out = { ...next };
  for (const key of Object.keys(next) as (keyof T)[]) {
    if (current[key] !== oldBaseline[key]) out[key] = current[key];
  }
  return out;
}

/** The translation select's items: the server's, plus a stored one no longer offered here, kept selectable. */
export function translationItems(translations: Translations | undefined, stored: string | null): Record<string, string> {
  const items: Record<string, string> = Object.fromEntries((translations?.items ?? []).map((t) => [t.id, t.label]));
  if (stored !== null && !(stored in items)) items[stored] = `${stored.toUpperCase()} (not available on this server)`;
  return items;
}

/** The hymnal select's items: the church's hymnals, plus a stored default it no longer has, kept selectable. */
export function hymnalItems(hymnals: Hymnals | undefined, stored: string | null): Record<string, string> {
  const items: Record<string, string> = Object.fromEntries((hymnals?.items ?? []).map((h) => [h.code, h.code]));
  if (stored !== null && !(stored in items)) items[stored] = `${stored} (no longer in your hymnals)`;
  return items;
}
````

**In `frontend/src/lib/queries/church.ts`, replace:**

````ts
import { skipToken, useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { ChurchProfile } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";
````

**with:**

````ts
import { skipToken, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { ChurchPatch, ChurchProfile } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const PROFILE_SAVED = "Profile saved.";
````

**Append to `frontend/src/lib/queries/church.ts`:**

````ts

/**
 * `PATCH /church` (slice 6a-1; admins): only the fields that change. Success
 * cancels a profile read in flight (it may predate the save), caches the
 * answer as the profile, so the header, the builder's translation and its
 * Benediction default follow at once, refreshes `/me` (the switcher's name)
 * and, when the default hymnal was sent, `GET /hymnals` (the Hymns step's
 * hymnal), and toasts "Profile saved.". A failure toasts the server's message,
 * except a 401 or a lost church, which the app already reports; a role 403
 * (an admin demoted meanwhile) also refetches the profile, so the page turns
 * read-only.
 */
export function useUpdateChurch() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<ChurchProfile, ApiError, ChurchPatch>({
    mutationFn: (patch) => api.church<ChurchProfile>("/church", { method: "PATCH", json: patch }),
    onSuccess: async (saved, patch) => {
      await queryClient.cancelQueries({ queryKey: keys.churchProfile(church.id) });
      queryClient.setQueryData(keys.churchProfile(church.id), saved);
      void queryClient.invalidateQueries({ queryKey: keys.me() });
      if (patch.default_hymnal !== undefined) void queryClient.invalidateQueries({ queryKey: keys.hymnals(church.id) });
      toast.success(PROFILE_SAVED);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
    },
  });
}
````

- [ ] **Step 4: See it pass, and the suite**

Run: `(cd frontend && npx vitest run src/lib/settings/profile.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
`      Tests  4 passed (4)`; ` Test Files  89 passed (89)` and `      Tests  738 passed (738)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/lib/settings/profile.ts frontend/src/lib/settings/profile.test.ts frontend/src/lib/queries/church.ts
git commit -q -m "Slice 6a-1: the Church form's rules and useUpdateChurch" -m "lib/settings/profile.ts: the Church form from a profile (stored values,
else the ones in effect), the patch of only what changed (cleaned as the
server cleans it, never a blank hymnal), 6a's rebase rule and the
translation and hymnal items that keep a stale stored value. The
PATCH /church mutation caches the answer as the profile, refreshes /me
and, when the hymnal changed, /hymnals." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1523 passed, 24 skipped`; frontend `738 passed` in 89 files.

### Task 4: One leave guard for settings pages (S "Leave guard"; clarification 8)

**Files:**
- Create: `frontend/src/components/app/leave-guard.test.tsx`, `frontend/src/components/app/leave-guard.tsx`
- Modify: `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, `frontend/src/components/app/church-switcher.tsx`

- [ ] **Step 1: Write the failing test**

The Bulletin settings page's own guard tests (`bulletin-settings-page.test.tsx`: the dialog on **Back to Review & send**, the reload warning, a modified click) stay as they are and must keep passing once the page uses the shared guard; so must `app-header.test.tsx`'s "Join or create a church…" test (no unsaved edits there, so it goes on at once). The new tests cover a `blob:` link (it goes on), a link with its own handler (after **Discard changes** its handler runs, so a replace stays a replace) and "Join or create a church…" with and without unsaved edits.

**Create `frontend/src/components/app/leave-guard.test.tsx`:**

````tsx
/**
 * The leave guard every settings form uses (slice 6a-1; the Bulletin settings
 * page's guard, shared): any in-app link to another page asks first while
 * there are unsaved edits; other links, and every link without edits, go on.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChurchSwitcher } from "@/components/app/church-switcher";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { DISCARD_TITLE, LeaveGuard } from "./leave-guard";

function Links({ dirty }: { dirty: boolean }) {
  return (
    <>
      <a href="/services?tab=saved">Services</a>
      <a href="#top">Top of this page</a>
      <a href="/services" target="_blank" rel="noreferrer">
        New tab
      </a>
      <a href="https://example.com/help">Help</a>
      <a href={`blob:${window.location.origin}/picture-1`}>Picture</a>
      <a
        href="/builder"
        onClick={(event) => {
          event.preventDefault(); // as Next's <Link replace> does
          testRouter.replace("/builder");
        }}
      >
        Builder
      </a>
      <LeaveGuard when={dirty} />
    </>
  );
}

/** Clicks `link`; true when the click went on as a link click (nothing prevented it). */
function followed(link: HTMLElement): boolean {
  const event = new MouseEvent("click", { bubbles: true, cancelable: true, button: 0 });
  act(() => {
    link.addEventListener("click", (e) => e.preventDefault(), { once: true }); // jsdom cannot navigate
    link.dispatchEvent(event);
  });
  return screen.queryByRole("alertdialog") === null;
}

describe("LeaveGuard (slice 6a-1)", () => {
  it("asks before an in-app link to another page while dirty, and only then", async () => {
    const { user, rerender } = renderWithProviders(<Links dirty={false} />, { path: "/settings/church" });
    expect(followed(screen.getByRole("link", { name: "Services" }))).toBe(true);

    rerender(<Links dirty />);
    for (const name of ["Top of this page", "New tab", "Help", "Picture"]) {
      expect(followed(screen.getByRole("link", { name }))).toBe(true);
    }
    await user.click(screen.getByRole("link", { name: "Services" }));
    const dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/services?tab=saved");
  });

  it("after Discard changes, the link's own handler navigates, so a replace stays a replace", async () => {
    const { user } = renderWithProviders(<Links dirty />, { path: "/settings/church" });
    await user.click(screen.getByRole("link", { name: "Builder" }));
    expect(testRouter.replace).not.toHaveBeenCalled();
    const dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.replace).toHaveBeenCalledWith("/builder");
    expect(testRouter.push).not.toHaveBeenCalled();
  });

  it("asks before the church menu's Join or create a church… while dirty, and not otherwise", async () => {
    const church = { id: "c-1", name: "Grace", role: "admin" } as const;
    const menu = (dirty: boolean) => (
      <>
        <ChurchSwitcher churches={[church]} activeId="c-1" onSelect={vi.fn()} />
        <LeaveGuard when={dirty} />
      </>
    );
    const { user, rerender } = renderWithProviders(menu(true), { path: "/settings/church" });
    const join = async () => {
      await user.click(screen.getByRole("button", { name: "Active church: Grace" }));
      await user.click(await screen.findByRole("menuitem", { name: "Join or create a church…" }));
    };

    await join();
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(testRouter.push).not.toHaveBeenCalled();
    await join();
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/welcome");

    testRouter.push.mockClear();
    rerender(menu(false));
    await join();
    expect(testRouter.push).toHaveBeenCalledWith("/welcome");
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });
});
````

- [ ] **Step 2: See it fail**

Run: `(cd frontend && npx vitest run src/components/app/leave-guard.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`leave-guard.tsx` does not exist yet):
```
 FAIL  |dom| src/components/app/leave-guard.test.tsx [ src/components/app/leave-guard.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: Write the guard; the Bulletin settings page uses it**

**Create `frontend/src/components/app/leave-guard.tsx`:**

````tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";

export const DISCARD_TITLE = "Discard unsaved changes?";
const DISCARD_BODY = "Your changes on this page haven't been saved.";

type Leave = () => void;

/** The mounted guard while it has unsaved edits to protect (one settings page at a time), else null. */
let activeGuard: ((leave: Leave) => void) | null = null;

/**
 * For a way out of the page that is not a link (the church menu's "Join or
 * create a church…"): while a `LeaveGuard` has unsaved edits, `leave` runs
 * only after "Discard changes"; otherwise it runs at once.
 */
export function confirmLeave(leave: Leave): void {
  if (activeGuard !== null) activeGuard(leave);
  else leave();
}

/** The link a click would follow to another in-app page, or null when the click should go ahead as usual. */
function guardedLink(event: MouseEvent): { link: HTMLAnchorElement; href: string } | null {
  if (event.defaultPrevented || event.button !== 0) return null;
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return null; // a new tab or window
  const link = event.target instanceof Element ? event.target.closest("a[href]") : null;
  if (!(link instanceof HTMLAnchorElement) || link.hasAttribute("download")) return null;
  if (link.target !== "" && link.target !== "_self") return null;
  const url = new URL(link.href, window.location.href);
  // A blob: or data: URL can share the page's origin, but it is a file, not a page of the app.
  if (url.protocol !== "http:" && url.protocol !== "https:") return null;
  if (url.origin !== window.location.origin) return null;
  if (url.pathname === window.location.pathname && url.search === window.location.search) return null;
  return { link, href: `${url.pathname}${url.search}${url.hash}` };
}

/**
 * 6a's leave guard for a settings form (slice 6a-1; the Bulletin settings
 * page's guard, moved here so every settings page shares it). While `when`
 * is true:
 * - closing or reloading the tab shows the browser's own warning;
 * - a plain click on any in-app link to another page (the settings nav, the
 *   header's nav, a page's own links) asks "Discard unsaved changes?" first:
 *   **Discard changes** goes on, **Keep editing** stays with the edits.
 * A modified or middle click opens the link as usual. After **Discard
 * changes** the link is clicked again with the guard standing aside, so its
 * own handler navigates as it would have (a `<Link replace>` replaces); a link
 * with no handler of its own goes on with `router.push`. "Join or create a
 * church…" asks through `confirmLeave`. The browser's Back and Forward
 * buttons, Log out and choosing another church in the church menu are not
 * covered.
 */
export function LeaveGuard({ when }: { when: boolean }) {
  const router = useRouter();
  const [leave, setLeave] = useState<Leave | null>(null);
  const standAside = useRef(false);

  useEffect(() => {
    if (!when) return;
    const ask = (next: Leave) => setLeave(() => next);
    activeGuard = ask;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = ""; // older Chrome and Edge, and some webviews, ask only when this is set
    };
    // Capture, on the document: runs before the link's own handler (Next's Link), which it stops.
    const intercept = (event: MouseEvent) => {
      if (standAside.current) return;
      const found = guardedLink(event);
      if (found === null) return;
      event.preventDefault();
      event.stopPropagation();
      ask(() => follow(found.link, found.href));
    };
    // The link again, its own handler included; when nothing handled it (a plain <a>), router.push.
    const follow = (link: HTMLAnchorElement, href: string) => {
      if (!link.isConnected) {
        router.push(href);
        return;
      }
      const fallback = (event: MouseEvent) => {
        if (event.defaultPrevented) return;
        event.preventDefault();
        router.push(href);
      };
      document.addEventListener("click", fallback, { once: true });
      standAside.current = true;
      try {
        link.click();
      } finally {
        standAside.current = false;
        document.removeEventListener("click", fallback);
      }
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", intercept, true);
    return () => {
      if (activeGuard === ask) activeGuard = null;
      window.removeEventListener("beforeunload", warn);
      document.removeEventListener("click", intercept, true);
    };
  }, [when, router]);

  return (
    <ConfirmDialog
      open={leave !== null}
      onOpenChange={(open) => {
        if (!open) setLeave(null);
      }}
      title={DISCARD_TITLE}
      description={DISCARD_BODY}
      confirmLabel="Discard changes"
      cancelLabel="Keep editing"
      destructive
      onConfirm={() => {
        setLeave(null);
        leave?.();
      }}
    />
  );
}
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
import { useRouter } from "next/navigation";
import {
  useEffect,
  useRef,
  useState,
  type ComponentProps,
  type FormEvent,
  type MouseEvent,
  type ReactNode,
} from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
````

**with:**

````tsx
import { useEffect, useRef, useState, type ComponentProps, type FormEvent, type ReactNode } from "react";

import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
export const DISCARD_TITLE = "Discard unsaved changes?";
const DISCARD_BODY = "Your changes on this page haven't been saved.";
````

**with:**

````tsx
export { DISCARD_TITLE } from "@/components/app/leave-guard";
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
 * form (`rebaseForm`), and leaving with unsaved edits asks first (the
 * browser's warning on a reload or close, "Discard unsaved changes?" on
 * **Back to Review & send**).
````

**with:**

````tsx
 * form (`rebaseForm`), and leaving with unsaved edits asks first
 * (`LeaveGuard`: the browser's warning on a reload or close, "Discard
 * unsaved changes?" on **Back to Review & send** and any other in-app link).
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [leaving, setLeaving] = useState(false);
  // Shown once the fetch made on opening the page is back; then kept, so a failed background refetch keeps the form.
  if (!ready && settings.isFetchedAfterMount && settings.isSuccess) setReady(true);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = ""; // older Chrome and Edge, and some webviews, ask only when this is set
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function onBack(event: MouseEvent<HTMLAnchorElement>) {
    // A modified or other-button click opens a new tab or window, as a link does; this page stays as it is.
    const modified = event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0;
    if (!dirty || modified) return;
    event.preventDefault();
    setLeaving(true);
  }
````

**with:**

````tsx
  const [ready, setReady] = useState(false);
  const [dirty, setDirty] = useState(false);
  // Shown once the fetch made on opening the page is back; then kept, so a failed background refetch keeps the form.
  if (!ready && settings.isFetchedAfterMount && settings.isSuccess) setReady(true);
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
          <Link href={BACK_HREF} onClick={onBack} className={buttonVariants({ variant: "outline", size: "touch" })}>
````

**with:**

````tsx
          <Link href={BACK_HREF} className={buttonVariants({ variant: "outline", size: "touch" })}>
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
      <ConfirmDialog
        open={leaving}
        onOpenChange={setLeaving}
        title={DISCARD_TITLE}
        description={DISCARD_BODY}
        confirmLabel="Discard changes"
        cancelLabel="Keep editing"
        destructive
        onConfirm={() => {
          setLeaving(false);
          setDirty(false);
          router.push(BACK_HREF);
        }}
      />
````

**with:**

````tsx
      <LeaveGuard when={dirty} />
````

**In `frontend/src/components/app/church-switcher.tsx`, replace:**

````tsx

import { buttonVariants } from "@/components/ui/button";
````

**with:**

````tsx

import { confirmLeave } from "@/components/app/leave-guard";
import { buttonVariants } from "@/components/ui/button";
````

**In `frontend/src/components/app/church-switcher.tsx`, replace:**

````tsx
 * (1b clarification 31). A user with one church sees the same menu.
````

**with:**

````tsx
 * (1b clarification 31), asking first while a settings page has unsaved
 * edits (`confirmLeave`, slice 6a-1). A user with one church sees the same menu.
````

**In `frontend/src/components/app/church-switcher.tsx`, replace:**

````tsx
        <DropdownMenuItem onClick={() => router.push("/welcome")}>Join or create a church…</DropdownMenuItem>
````

**with:**

````tsx
        <DropdownMenuItem onClick={() => confirmLeave(() => router.push("/welcome"))}>Join or create a church…</DropdownMenuItem>
````

- [ ] **Step 4: See them pass (three times), and the suite**

Run: `(cd frontend && npx vitest run src/components/app/leave-guard.test.tsx src/components/bulletin-settings/bulletin-settings-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (three times) then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
three times `      Tests  12 passed (12)` (the guard's 3 and the Bulletin settings page's 9, unchanged); ` Test Files  90 passed (90)` and `      Tests  741 passed (741)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/app/leave-guard.tsx frontend/src/components/app/leave-guard.test.tsx frontend/src/components/bulletin-settings/bulletin-settings-page.tsx frontend/src/components/app/church-switcher.tsx
git commit -q -m "Slice 6a-1: one leave guard for settings pages" -m "LeaveGuard: while a settings form has unsaved edits, a reload or close
shows the browser's warning and a plain click on any in-app link to
another page asks \"Discard unsaved changes?\" first; after Discard
changes the link's own handler navigates (a replace stays a replace), and
a blob: link is left alone. The church menu's \"Join or create a
church…\" asks too (confirmLeave). The Bulletin settings page's own guard
(its Back link only) moves into it, so that page now also asks on the
menu links; its tests are unchanged." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1523 passed, 24 skipped`; frontend `741 passed` in 90 files.

### Task 5: The Settings area and its menu item (S "Settings nav"; F §4.2; clarifications 2, 3)

**Files:**
- Create: `frontend/src/components/settings/settings-layout.test.tsx`, `frontend/src/components/settings/sections.ts`, `frontend/src/components/settings/settings-nav.tsx`, `frontend/src/app/(signed-in)/(church)/settings/layout.tsx`, `frontend/src/app/(signed-in)/(church)/settings/page.tsx`
- Modify: `frontend/src/components/app/app-header.test.tsx`, `frontend/src/components/app/app-nav.tsx`

- [ ] **Step 1: Write the failing tests**

**Create `frontend/src/components/settings/settings-layout.test.tsx`:**

````tsx
/** The Settings area's shell (slice 6a-1; 6a spec "Settings nav"): the heading, the section nav, `/settings`. */
import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import SettingsHome from "@/app/(signed-in)/(church)/settings/page";
import type { Church } from "@/lib/api/types";
import { church, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

function renderShell(role: Church["role"], path = "/settings/church") {
  const active = church({ role });
  return renderWithProviders(
    <SettingsLayout>
      <p>The section</p>
    </SettingsLayout>,
    { me: me({ churches: [active] }), church: active, path },
  );
}

describe("the Settings area (slice 6a-1)", () => {
  it("shows the heading, who you are in the church, and the sections with the current one marked", () => {
    const { unmount } = renderShell("admin");
    expect(screen.getByRole("heading", { level: 1, name: "Settings" })).toBeInTheDocument();
    expect(screen.getByText("You're an admin of Grace.")).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Settings sections" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["Church", "/settings/church"],
      ["Bulletin", "/bulletin-settings"],
    ]);
    expect(links[0]).toHaveAttribute("aria-current", "page");
    expect(links[1]).not.toHaveAttribute("aria-current");
    expect(links[0]).toHaveClass("h-11", "md:h-9");
    expect(screen.getByText("The section")).toBeInTheDocument();
    unmount();

    renderShell("owner");
    expect(screen.getByText("You're the owner of Grace.")).toBeInTheDocument();
  });

  it("shows a member the same sections, and /settings opens Church", () => {
    renderShell("member", "/settings");
    expect(screen.getByText("You're a member of Grace.")).toBeInTheDocument();
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(2);
    renderWithProviders(<SettingsHome />, { path: "/settings" });
    expect(testRouter.replace).toHaveBeenCalledWith("/settings/church");
  });
});
````

**In `frontend/src/components/app/app-header.test.tsx`, replace:**

````tsx
  it("shows the Builder and Services nav items on church pages, current under /builder, and no nav without churches (F §4.2)", () => {
````

**with:**

````tsx
  it("shows the Builder, Services and Settings nav items on church pages, current under /builder, and no nav without churches (F §4.2)", () => {
````

**In `frontend/src/components/app/app-header.test.tsx`, replace:**

````tsx
      ["Services", "/services"],
````

**with:**

````tsx
      ["Services", "/services"],
      ["Settings", "/settings"],
````

**In `frontend/src/components/app/app-header.test.tsx`, replace:**

````tsx

    render(<AppHeader user={pat} onSignOut={vi.fn()} />);
````

**with:**

````tsx

    setTestPath("/settings/church");
    const { unmount: unmountSettings } = render(
      <AppHeader user={pat} churches={[graceAdmin]} active={graceAdmin} onSelectChurch={vi.fn()} onSignOut={vi.fn()} />,
    );
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("aria-current", "page");
    unmountSettings();

    render(<AppHeader user={pat} onSignOut={vi.fn()} />);
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx src/components/app/app-header.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the layout does not exist yet; the menu has no Settings item):
```
   × AppHeader > shows the Builder, Services and Settings nav items on church pages, current under /builder, and no nav without churches (F §4.2) <t>ms
 FAIL  |dom| src/components/settings/settings-layout.test.tsx [ src/components/settings/settings-layout.test.tsx ]
      Tests  1 failed | 5 passed (6)
```

- [ ] **Step 3: Write the Settings area and the menu item**

**Create `frontend/src/components/settings/sections.ts`:**

````ts
/**
 * The Settings area's pages, in the nav's order (6a spec "Settings nav"; slice
 * 6a-1). `/settings` opens the first. 6a-2 adds Hymns; 6a-3 Liturgy prompts,
 * Prayers and Rubric, and moves Bulletin settings in (its entry then points
 * under /settings); 5b adds Account and Contacts.
 */
export const SETTINGS_SECTIONS = [
  { href: "/settings/church", label: "Church" },
  { href: "/bulletin-settings", label: "Bulletin" },
] as const;
````

**Create `frontend/src/components/settings/settings-nav.tsx`:**

````tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

import { SETTINGS_SECTIONS } from "./sections";

/** The Settings area's section nav: a row of links on phones, a column beside the page from `md`. */
export function SettingsNav() {
  const pathname = usePathname();
  return (
    <nav aria-label="Settings sections">
      <ul className="flex flex-wrap gap-1 md:flex-col">
        {SETTINGS_SECTIONS.map((section) => {
          const current = pathname === section.href || pathname.startsWith(`${section.href}/`);
          return (
            <li key={section.href}>
              <Link
                href={section.href}
                aria-current={current ? "page" : undefined}
                className={cn(
                  "flex h-11 items-center rounded-md px-3 text-sm font-medium text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring md:h-9",
                  "hover:text-foreground aria-[current=page]:bg-muted aria-[current=page]:text-foreground",
                )}
              >
                {section.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/layout.tsx`:**

````tsx
"use client";

import type { ReactNode } from "react";

import { PageHeader } from "@/components/app/page-header";
import { SettingsNav } from "@/components/settings/settings-nav";
import type { Church } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

const YOU_ARE: Record<Church["role"], string> = { owner: "the owner", admin: "an admin", member: "a member" };

/**
 * The Settings area (6a spec "Settings nav"; slice 6a-1): the "Settings"
 * heading with who you are in the church, the section nav, and the section's
 * page beside it from `md` (under it on phones).
 */
export default function SettingsLayout({ children }: { children: ReactNode }) {
  const church = useChurch();
  return (
    <main className="mx-auto grid w-full max-w-5xl content-start gap-4 px-4 py-4">
      <PageHeader title="Settings" description={`You're ${YOU_ARE[church.role]} of ${church.name}.`} />
      <div className="grid gap-4 md:grid-cols-[11rem_minmax(0,1fr)] md:items-start">
        <SettingsNav />
        <div className="min-w-0 max-w-3xl">{children}</div>
      </div>
    </main>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/page.tsx`:**

````tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { SETTINGS_SECTIONS } from "@/components/settings/sections";

/** `/settings` opens the first section, Church (6a spec "Settings nav"). */
export default function SettingsHome() {
  const router = useRouter();

  useEffect(() => {
    router.replace(SETTINGS_SECTIONS[0].href);
  }, [router]);

  return <Skeleton aria-busy="true" className="h-40 w-full" />;
}
````

**In `frontend/src/components/app/app-nav.tsx`, replace:**

````tsx
/** Nav items in order; each appears once its slice ships (F §4.2): "Services" from 5a-3; 5b or 6a adds "Settings". */
export const NAV_ITEMS = [
  { href: "/builder", label: "Builder" },
  { href: "/services", label: "Services" },
````

**with:**

````tsx
/** Nav items in order; each appears once its slice ships (F §4.2): "Services" from 5a-3, "Settings" from 6a-1. */
export const NAV_ITEMS = [
  { href: "/builder", label: "Builder" },
  { href: "/services", label: "Services" },
  { href: "/settings", label: "Settings" },
````

- [ ] **Step 4: See them pass, and the suite**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx src/components/app/app-header.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
`      Tests  8 passed (8)`; ` Test Files  91 passed (91)` and `      Tests  743 passed (743)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/sections.ts frontend/src/components/settings/settings-nav.tsx frontend/src/components/settings/settings-layout.test.tsx 'frontend/src/app/(signed-in)/(church)/settings/layout.tsx' 'frontend/src/app/(signed-in)/(church)/settings/page.tsx' frontend/src/components/app/app-nav.tsx frontend/src/components/app/app-header.test.tsx
git commit -q -m "Slice 6a-1: the Settings area and its menu item" -m "The top menu gains Settings. /settings opens the first section; the
Settings layout shows the heading, who you are in the church and the
section nav (Church, and Bulletin until 6a-3 moves that page in), from
SETTINGS_SECTIONS, which 6a-2, 6a-3 and 5b add to." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1523 passed, 24 skipped`; frontend `743 passed` in 91 files.

### Task 6: The Church page (S UX §1; clarifications 4-7, 11, 14)

**Files:**
- Create: `frontend/src/components/settings/church-settings-page.test.tsx`, `frontend/src/components/settings/church-settings-page.tsx`, `frontend/src/app/(signed-in)/(church)/settings/church/page.tsx`
- Modify: `frontend/src/components/app/timezone-combobox.test.tsx`, `frontend/src/components/app/timezone-combobox.tsx`

- [ ] **Step 1: Write the failing tests**

The page's tests render it inside the Settings layout (T5), as the route is. Three of them cover a stored default hymnal with no hymns left (the no-hymns line, never "your only hymnal"), a stored translation while `GET /translations` fails (never labelled as another one) and a member's summary with a stored hymnal that is gone (the hymnal the builder uses, the stored one noted). The browser lists three zones and reports `America/Chicago` (as `create-church-form.test.tsx` does), never the runner's own zone.

**Create `frontend/src/components/settings/church-settings-page.test.tsx`:**

````tsx
/**
 * Settings → Church (slice 6a-1; 6a spec "Church profile"): admins edit and
 * save only what changed, members read. Rendered inside the Settings layout,
 * as the route is, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import ChurchSettingsRoute from "@/app/(signed-in)/(church)/settings/church/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, ChurchProfile } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { PROFILE_SAVED } from "@/lib/queries/church";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, hymnals, me, translations } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { ADMINS_ONLY, BENEDICTION_HELP, HYMNAL_HELP, TIMEZONE_NOT_RECOGNIZED, TRANSLATION_HELP } from "./church-settings-page";

const ZONES = ["America/Chicago", "America/New_York", "Europe/London"];
const REAL_OPTIONS = new Intl.DateTimeFormat().resolvedOptions();

beforeEach(() => {
  vi.spyOn(Intl, "supportedValuesOf").mockReturnValue(ZONES);
  vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({ ...REAL_OPTIONS, timeZone: "America/Chicago" });
});

afterEach(() => {
  toast.dismiss();
});

function renderPage(role: Church["role"] = "admin", profile: Partial<ChurchProfile> = {}, routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({
    "GET /church": churchProfile({ role, ...profile }),
    "GET /translations": translations(),
    "GET /hymnals": hymnals(),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <ChurchSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/church" },
  );
  return { ...view, api };
}

function patches(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "PATCH" && r.path === "/church");
}

const echo = (r: RecordedRequest) => churchProfile(r.body as Partial<ChurchProfile>);

describe("Settings → Church (slice 6a-1)", () => {
  it("lets an admin change only the name: the request sends the name alone and the profile is cached", async () => {
    const { api, user, queryClient } = renderPage("admin", {}, { "PATCH /church": echo });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const name = await screen.findByLabelText("Church name");
    const save = screen.getByRole("button", { name: "Save profile" });
    expect(save).toBeDisabled();
    expect(screen.getByText(TRANSLATION_HELP)).toBeInTheDocument();
    expect(screen.getByText(BENEDICTION_HELP)).toBeInTheDocument();
    expect(await screen.findByText("GG2013 (your only hymnal)")).toBeInTheDocument();
    await user.clear(name);
    await user.type(name, " Example Church ");
    await user.click(save);
    expect(await screen.findByText(PROFILE_SAVED)).toBeInTheDocument();
    expect(patches(api)).toHaveLength(1);
    expect(patches(api)[0].body).toEqual({ name: "Example Church" }); // untouched selects send nothing
    expect(patches(api)[0].headers["x-church-id"]).toBe(church().id);
    expect(queryClient.getQueryData<ChurchProfile>(keys.churchProfile(church().id))?.name).toBe("Example Church");
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.me() });
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: keys.hymnals(church().id) });
    expect(save).toBeDisabled();
  });

  it("shows a member the profile as plain text, with the note and no Save", async () => {
    renderPage("member", { default_benediction: "" });
    expect(await screen.findByText(ADMINS_ONLY)).toBeInTheDocument();
    expect(screen.getByText("America/New York")).toBeInTheDocument();
    expect(screen.getByText("World English Bible (WEB)")).toBeInTheDocument();
    expect(screen.getByText("None. The AI writes the benediction.")).toBeInTheDocument();
    expect(screen.queryAllByRole("textbox")).toEqual([]);
    expect(screen.queryByRole("button", { name: "Save profile" })).toBeNull();
  });

  it("shows a member the hymnal the builder uses, noting a stored one the church no longer has", async () => {
    renderPage("member", { default_hymnal: "HL1955", effective_hymnal: "GG2013" });
    expect(await screen.findByText("GG2013 (the builder uses this; HL1955 is no longer in your hymnals)")).toBeInTheDocument();
    expect(screen.queryByText("HL1955")).toBeNull();
  });

  it("shows a field the server refuses under it and focuses it", async () => {
    const { user } = renderPage("admin", {}, {
      "PATCH /church": fakeError(422, "invalid_request", "Unknown timezone.", { fields: { timezone: "Unknown timezone." } }),
    });
    await user.type(await screen.findByLabelText("Church name"), " Church");
    await user.click(screen.getByRole("button", { name: "Save profile" }));
    const zone = screen.getByLabelText("Time zone");
    await waitFor(() => expect(zone).toHaveFocus());
    expect(zone).toHaveAttribute("aria-invalid", "true");
    expect(document.getElementById("church-timezone-error")).toHaveTextContent("Unknown timezone.");
  });

  it("shows a stored time zone it does not recognize, with the warning, and offers this device's zone", async () => {
    const { user } = renderPage("admin", { timezone: "Eastern", timezone_valid: false });
    const zone = await screen.findByLabelText("Time zone");
    expect(zone).toHaveValue("Eastern");
    expect(screen.getByText(TIMEZONE_NOT_RECOGNIZED)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Use this device's time zone (America/Chicago)" }));
    expect(zone).toHaveValue("America/Chicago");
    expect(screen.queryByText(TIMEZONE_NOT_RECOGNIZED)).toBeNull();
  });

  it("keeps a stale stored translation or hymnal selectable, sends a new hymnal, and says when there are no hymnals", async () => {
    const two = hymnals({ items: [...hymnals().items, { code: "PH1990", hymn_count: 605, scripture_ref_count: 0 }] });
    const { api, user, queryClient, unmount } = renderPage(
      "admin",
      { bible_translation: "esv", default_hymnal: "HL1955" },
      { "GET /translations": translations({ items: [{ id: "web", label: "World English Bible (WEB)" }] }), "GET /hymnals": two, "PATCH /church": echo },
    );
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const translation = await screen.findByRole("combobox", { name: "Default Bible translation" });
    await waitFor(() => expect(translation).toHaveTextContent("ESV (not available on this server)"));
    const hymnal = screen.getByRole("combobox", { name: "Default hymnal" });
    await waitFor(() => expect(hymnal).toHaveTextContent("HL1955 (no longer in your hymnals)"));
    expect(screen.getByText(HYMNAL_HELP)).toBeInTheDocument();
    await user.click(hymnal);
    await user.click(await screen.findByRole("option", { name: "PH1990" }));
    await user.click(screen.getByRole("button", { name: "Save profile" }));
    await screen.findByText(PROFILE_SAVED);
    expect(patches(api)[0].body).toEqual({ default_hymnal: "PH1990" });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.hymnals(church().id) });
    unmount();

    renderPage("admin", { default_hymnal: null, effective_hymnal: null }, { "GET /hymnals": hymnals({ items: [], effective_hymnal: null }) });
    expect(await screen.findByText("Your church has no hymns yet, so there is no default hymnal.")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Default hymnal" })).toBeNull();
  });

  it("says there are no hymns when a stored default hymnal is left but the church has none (never \"your only hymnal\")", async () => {
    const { api } = renderPage(
      "admin",
      { default_hymnal: "GG2013", effective_hymnal: null },
      { "GET /hymnals": hymnals({ items: [], effective_hymnal: null, default_hymnal: "GG2013" }) },
    );
    await waitFor(() => expect(api.requests.some((r) => r.path === "/hymnals")).toBe(true));
    expect(await screen.findByText("Your church has no hymns yet, so there is no default hymnal.")).toBeInTheDocument();
    expect(screen.queryByText(/your only hymnal/)).toBeNull();
  });

  it("never labels a stored translation as another one when the translation list cannot be read", async () => {
    renderPage("admin", { bible_translation: "esv" }, { "GET /translations": fakeError(500, "internal_error", "Something went wrong.") });
    const translation = await screen.findByRole("combobox", { name: "Default Bible translation" });
    await waitFor(() => expect(translation).toHaveTextContent("ESV (not available on this server)"));
    expect(translation).not.toHaveTextContent("World English Bible");
  });

  it("rebases on newer data: another admin's rename shows, and the edited Benediction is kept and sent alone", async () => {
    const { api, user, queryClient } = renderPage("admin", {}, { "PATCH /church": echo });
    const benediction = await screen.findByLabelText("Default Benediction");
    await user.clear(benediction);
    await user.type(benediction, "Go in peace.");
    queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ name: "Grace Renamed" }));
    await waitFor(() => expect(screen.getByLabelText("Church name")).toHaveValue("Grace Renamed"));
    expect(benediction).toHaveValue("Go in peace.");
    await user.click(screen.getByRole("button", { name: "Save profile" }));
    await screen.findByText(PROFILE_SAVED);
    expect(patches(api)[0].body).toEqual({ default_benediction: "Go in peace." });
  });

  it("toasts a role 403, refetches the profile and does not report the church as lost", async () => {
    const lost = vi.fn();
    const off = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("admin", {}, {
      "PATCH /church": fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.type(await screen.findByLabelText("Church name"), " Church");
    await user.click(screen.getByRole("button", { name: "Save profile" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(lost).not.toHaveBeenCalled();
    off();
  });

  it("asks before leaving with unsaved edits, through the Settings nav", async () => {
    const { user } = renderPage("admin");
    const name = await screen.findByLabelText("Church name");
    const bulletin = screen.getByRole("link", { name: "Bulletin" });
    await user.type(name, " Church");
    await user.click(bulletin);
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(name).toHaveValue("Grace Church");
    expect(testRouter.push).not.toHaveBeenCalled();
    await user.click(bulletin);
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/bulletin-settings");
  });

  it("shows the error state with Retry when the profile cannot be read", async () => {
    renderPage("admin", {}, { "GET /church": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
````

**In `frontend/src/components/app/timezone-combobox.test.tsx`, replace:**

````tsx
  });
});
````

**with:**

````tsx
  });

  it("shows a value that is not in the list as chosen, with the warning under the field (6a-1)", async () => {
    stubZones(ZONES);
    const user = userEvent.setup();
    render(<TimezoneCombobox value="Eastern" onChange={() => {}} warning="Timezone not recognized. Choose one from the list." />);

    const input = screen.getByRole("combobox", { name: "Time zone" });
    expect(input).toHaveValue("Eastern");
    expect(input).not.toHaveAttribute("aria-invalid");
    expect(input).toHaveAccessibleDescription(
      "Sets the default service date (the next Sunday in this time zone). Timezone not recognized. Choose one from the list.",
    );
    await user.click(input);
    expect(await screen.findByRole("option", { name: "Eastern", selected: true })).toBeInTheDocument();
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/church-settings-page.test.tsx src/components/app/timezone-combobox.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the page does not exist yet; the combobox has no `warning` and drops a value it does not list):
```
   × TimezoneCombobox > shows a value that is not in the list as chosen, with the warning under the field (6a-1) <t>ms
 FAIL  |dom| src/components/settings/church-settings-page.test.tsx [ src/components/settings/church-settings-page.test.tsx ]
      Tests  1 failed | 6 passed (7)
```

- [ ] **Step 3: Write the page, its route, and the combobox's warning**

**In `frontend/src/components/app/timezone-combobox.tsx`, replace:**

````tsx
  id?: string;
````

**with:**

````tsx
  id?: string;
  /** A note under the field that is not an error (6a's church profile: a stored zone not recognized). */
  warning?: string | null;
````

**In `frontend/src/components/app/timezone-combobox.tsx`, replace:**

````tsx
 * server validates the id.
 */
export function TimezoneCombobox({ value, onChange, error, id }: TimezoneComboboxProps) {
````

**with:**

````tsx
 * server validates the id. A `value` that is not in the list (a zone stored
 * before the check, or one this browser lacks) is added as an item, so it
 * shows as chosen (F §4.9 item 3).
 */
export function TimezoneCombobox({ value, onChange, error, id, warning }: TimezoneComboboxProps) {
````

**In `frontend/src/components/app/timezone-combobox.tsx`, replace:**

````tsx
  const describedBy = error ? `${helperId} ${errorId}` : helperId;

  const [zones] = useState(listTimezones);
````

**with:**

````tsx
  const warningId = `${inputId}-warning`;
  const describedBy = [helperId, warning ? warningId : null, error ? errorId : null].filter(Boolean).join(" ");

  const [listed] = useState(listTimezones);
  const zones = useMemo(
    () => (listed && value !== "" && !listed.includes(value) ? [value, ...listed] : listed),
    [listed, value],
  );
````

**In `frontend/src/components/app/timezone-combobox.tsx`, replace:**

````tsx
      </p>
      {error ? (
````

**with:**

````tsx
      </p>
      {warning ? (
        <p id={warningId} className="text-sm text-amber-700 dark:text-amber-400">
          {warning}
        </p>
      ) : null}
      {error ? (
````

**Create `frontend/src/components/settings/church-settings-page.tsx`:**

````tsx
"use client";

import { useState, type FormEvent, type ReactNode } from "react";

import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
import { PendingButton } from "@/components/app/pending-button";
import { TimezoneCombobox } from "@/components/app/timezone-combobox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import type { ChurchProfile } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useUpdateChurch, useChurchProfile } from "@/lib/queries/church";
import { useHymnals } from "@/lib/queries/hymns";
import { useTranslations } from "@/lib/queries/reference";
import {
  diffProfile,
  hasChanges,
  hymnalItems,
  profileFormFrom,
  rebaseForm,
  translationItems,
  type ProfileForm,
} from "@/lib/settings/profile";
import { browserTimezone, listTimezones, timezoneLabel } from "@/lib/timezones";

export const ADMINS_ONLY = "Only admins can edit the church profile.";
export const TIMEZONE_NOT_RECOGNIZED = "Timezone not recognized. Choose one from the list.";
// A change reaches every service that follows the church's choice (a service whose own pick equals it follows too:
// the draft stores no pick then), and a saved service reopens with the church's translation (6a-1 owner question 11).
export const TRANSLATION_HELP =
  "Used for passage text in the builder, in every service that has not switched to another translation (saved services too, when reopened). Anyone can switch it for a single service.";
export const HYMNAL_HELP =
  "The hymnal the builder opens with, in every unsaved service that has not switched to another hymnal. You can switch hymnals for a single service.";
export const BENEDICTION_HELP =
  "Pre-fills the Benediction card in each new service, and in unsaved services whose card still shows the default. Leave it blank to let the AI write the benediction.";
const NO_HYMNALS = "Your church has no hymns yet, so there is no default hymnal.";
const NO_BENEDICTION = "None. The AI writes the benediction.";

/**
 * `/settings/church` (slice 6a-1; 6a spec "Church profile"): the church's
 * name, time zone, default Bible translation, default hymnal and default
 * Benediction. Owners and admins edit them and save only what changed
 * (`PATCH /church`); members read them, with a note that only admins can
 * edit. 6a's rules for settings forms: newer server data rebases the form
 * (an untouched field takes it, an edited one keeps the edit), and leaving
 * with unsaved edits asks first (`LeaveGuard`).
 */
export function ChurchSettingsPage() {
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  let body: ReactNode;
  if (profile.data) {
    body = isAdmin(profile.data.role) ? <ProfileFormView profile={profile.data} /> : <ProfileSummary profile={profile.data} />;
  } else if (profile.isError) {
    body = <ErrorState error={profile.error} onRetry={() => void profile.refetch()} retrying={profile.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-4">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
    );
  }
  return (
    <section aria-labelledby="church-profile-title" className="grid gap-4">
      <h2 id="church-profile-title" className="text-lg font-semibold">
        Church profile
      </h2>
      {body}
    </section>
  );
}

type Field = keyof ProfileForm;

/** This device's time zone when the browser lists it (or lists none), else null: the shortcut is not offered. */
function listedDeviceZone(): string | null {
  const zone = browserTimezone();
  const zones = listTimezones();
  return zone !== null && (zones === null || zones.includes(zone)) ? zone : null;
}
type FormState = { source: ChurchProfile; baseline: ProfileForm; form: ProfileForm };

function FieldNote({ id, children, error }: { id: string; children: ReactNode; error?: boolean }) {
  return (
    <p id={id} role={error ? "alert" : undefined} className={error ? "text-sm text-destructive" : "text-sm text-muted-foreground"}>
      {children}
    </p>
  );
}

function ProfileFormView({ profile }: { profile: ChurchProfile }) {
  const save = useUpdateChurch();
  const translations = useTranslations();
  const hymnals = useHymnals();
  const [state, setState] = useState<FormState>(() => {
    const form = profileFormFrom(profile);
    return { source: profile, baseline: form, form };
  });
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [deviceZone] = useState(listedDeviceZone);
  const { form, baseline } = state;
  const changed = hasChanges(baseline, form);

  // Newer server data (a refetch, or this page's own save in the cache): rebase (6a).
  if (profile !== state.source) {
    const next = profileFormFrom(profile);
    setState({ source: profile, baseline: next, form: rebaseForm(baseline, form, next) });
  }

  const update = (field: Field, value: string) => {
    setState((s) => ({ ...s, form: { ...s.form, [field]: value } }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (save.isPending || !changed) return;
    const sent = form;
    save.mutate(diffProfile(baseline, sent), {
      // What was typed while saving stays; everything else shows what was stored.
      onSuccess: (saved) =>
        setState((s) => {
          const next = profileFormFrom(saved);
          return { source: saved, baseline: next, form: rebaseForm(sent, s.form, next) };
        }),
      onError: (e) => {
        if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return;
        const found = Object.fromEntries(
          Object.entries(e.fields).filter(([key]) => key in form),
        ) as Partial<Record<Field, string>>;
        setErrors(found);
        const first = (Object.keys(found) as Field[])[0];
        if (first) document.getElementById(`church-${first}`)?.focus();
      },
    });
  }

  const describedBy = (...ids: (string | false | undefined)[]) => ids.filter(Boolean).join(" ") || undefined;
  const errorNote = (field: Field) =>
    errors[field] ? (
      <FieldNote id={`church-${field}-error`} error>
        {errors[field]}
      </FieldNote>
    ) : null;

  // Until GET /translations answers (or when it fails), the profile's own facts: the translation in effect, and a
  // stored one that differs from it is one this server does not offer.
  const translationChoices = translations.data
    ? translationItems(translations.data, profile.bible_translation)
    : {
        [profile.effective_translation]: profile.effective_translation_label,
        ...translationItems(undefined, profile.bible_translation === profile.effective_translation ? null : profile.bible_translation),
      };
  const hymnalChoices = hymnals.data
    ? hymnalItems(hymnals.data, profile.default_hymnal)
    : form.default_hymnal
      ? { [form.default_hymnal]: form.default_hymnal }
      : {};
  // From the church's hymnals (GET /hymnals), never from the choices: a stale stored default is not "your only hymnal".
  const churchHymnals = hymnals.data?.items.map((h) => h.code) ?? null;
  const noHymnals = churchHymnals !== null ? churchHymnals.length === 0 : form.default_hymnal === "";
  const onlyHymnal = churchHymnals !== null && churchHymnals.length === 1 && churchHymnals[0] === form.default_hymnal;

  return (
    <form onSubmit={onSubmit} className="grid gap-5" aria-label="Church profile">
      <div className="grid gap-1.5">
        <Label htmlFor="church-name">Church name</Label>
        <Input
          id="church-name"
          value={form.name}
          maxLength={200}
          className="h-11"
          aria-invalid={errors.name ? true : undefined}
          aria-describedby={describedBy(errors.name && "church-name-error")}
          onChange={(e) => update("name", e.target.value)}
        />
        {errorNote("name")}
      </div>

      <div className="grid gap-1">
        <TimezoneCombobox
          id="church-timezone"
          value={form.timezone}
          onChange={(value) => update("timezone", value)}
          error={errors.timezone}
          warning={!profile.timezone_valid && form.timezone === profile.timezone ? TIMEZONE_NOT_RECOGNIZED : null}
        />
        {deviceZone !== null && deviceZone !== form.timezone ? (
          <Button
            type="button"
            variant="link"
            className="h-11 justify-self-start px-0 md:h-8"
            onClick={() => update("timezone", deviceZone)}
          >
            {`Use this device's time zone (${timezoneLabel(deviceZone)})`}
          </Button>
        ) : null}
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="church-bible_translation">Default Bible translation</Label>
        <Select
          value={form.bible_translation}
          items={translationChoices}
          onValueChange={(value) => {
            if (typeof value === "string") update("bible_translation", value);
          }}
        >
          <SelectTrigger
            id="church-bible_translation"
            className="h-11 w-full data-[size=default]:h-11"
            aria-invalid={errors.bible_translation ? true : undefined}
            aria-describedby={describedBy("church-bible_translation-help", errors.bible_translation && "church-bible_translation-error")}
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {Object.entries(translationChoices).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <FieldNote id="church-bible_translation-help">{TRANSLATION_HELP}</FieldNote>
        {errorNote("bible_translation")}
      </div>

      <div className="grid gap-1.5">
        {noHymnals ? (
          <>
            <p className="text-sm font-medium">Default hymnal</p>
            <p className="text-sm text-muted-foreground">{NO_HYMNALS}</p>
          </>
        ) : onlyHymnal ? (
          <>
            <p className="text-sm font-medium">Default hymnal</p>
            <p className="text-sm">{`${form.default_hymnal} (your only hymnal)`}</p>
          </>
        ) : (
          <>
            <Label htmlFor="church-default_hymnal">Default hymnal</Label>
            <Select
              value={form.default_hymnal}
              items={hymnalChoices}
              onValueChange={(value) => {
                if (typeof value === "string") update("default_hymnal", value);
              }}
            >
              <SelectTrigger
                id="church-default_hymnal"
                className="h-11 w-full data-[size=default]:h-11"
                aria-invalid={errors.default_hymnal ? true : undefined}
                aria-describedby={describedBy("church-default_hymnal-help", errors.default_hymnal && "church-default_hymnal-error")}
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(hymnalChoices).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FieldNote id="church-default_hymnal-help">{HYMNAL_HELP}</FieldNote>
            {errorNote("default_hymnal")}
          </>
        )}
      </div>

      <div className="grid gap-1.5">
        <Label htmlFor="church-default_benediction">Default Benediction</Label>
        <Textarea
          id="church-default_benediction"
          value={form.default_benediction}
          maxLength={4000}
          rows={4}
          className="max-h-[60vh] overflow-y-auto"
          aria-invalid={errors.default_benediction ? true : undefined}
          aria-describedby={describedBy(
            "church-default_benediction-help",
            errors.default_benediction && "church-default_benediction-error",
          )}
          onChange={(e) => update("default_benediction", e.target.value)}
        />
        <FieldNote id="church-default_benediction-help">{BENEDICTION_HELP}</FieldNote>
        {errorNote("default_benediction")}
      </div>

      <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending} disabled={!changed}>
        Save profile
      </PendingButton>
      <LeaveGuard when={changed} />
    </form>
  );
}

function SummaryItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-0.5">
      <dt className="text-sm font-medium">{label}</dt>
      <dd className="text-sm whitespace-pre-line break-words">{children}</dd>
    </div>
  );
}

/** The hymnal the builder opens with, noting a stored default the church no longer has. */
function summaryHymnal(profile: ChurchProfile): string | null {
  const { default_hymnal: stored, effective_hymnal: effective } = profile;
  if (effective === null) return null;
  return stored !== null && stored !== effective
    ? `${effective} (the builder uses this; ${stored} is no longer in your hymnals)`
    : effective;
}

/** What a member sees: the profile as plain text, no controls (as on Bulletin settings). */
function ProfileSummary({ profile }: { profile: ChurchProfile }) {
  const hymnal = summaryHymnal(profile);
  return (
    <div className="grid gap-4">
      <Alert role="status">
        <AlertDescription>{ADMINS_ONLY}</AlertDescription>
      </Alert>
      <dl className="grid gap-3 rounded-lg border p-4">
        <SummaryItem label="Church name">{profile.name}</SummaryItem>
        <SummaryItem label="Time zone">{timezoneLabel(profile.timezone)}</SummaryItem>
        <SummaryItem label="Default Bible translation">{profile.effective_translation_label}</SummaryItem>
        <SummaryItem label="Default hymnal">{hymnal ?? <span className="text-muted-foreground">{NO_HYMNALS}</span>}</SummaryItem>
        <SummaryItem label="Default Benediction">
          {profile.default_benediction.trim() !== "" ? (
            profile.default_benediction
          ) : (
            <span className="text-muted-foreground">{NO_BENEDICTION}</span>
          )}
        </SummaryItem>
      </dl>
    </div>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/church/page.tsx`:**

````tsx
"use client";

import { ChurchSettingsPage } from "@/components/settings/church-settings-page";

/** Settings → Church: the church's profile (slice 6a-1; F §4.1). */
export default function ChurchSettingsRoute() {
  return <ChurchSettingsPage />;
}
````

- [ ] **Step 4: See them pass (three times), and the suite**

Run: `(cd frontend && npx vitest run src/components/settings src/components/app/timezone-combobox.test.tsx src/components/onboarding/create-church-form.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (three times) then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
three times `      Tests  31 passed (31)` (the page's 12, the Settings layout's 2, the combobox's 7, the create form's 10); ` Test Files  92 passed (92)` and `      Tests  756 passed (756)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/church-settings-page.tsx frontend/src/components/settings/church-settings-page.test.tsx 'frontend/src/app/(signed-in)/(church)/settings/church/page.tsx' frontend/src/components/app/timezone-combobox.tsx frontend/src/components/app/timezone-combobox.test.tsx
git commit -q -m "Slice 6a-1: the Church page" -m "Settings → Church: owners and admins change the church's name, time
zone, default translation, default hymnal and default Benediction and
save only what changed; members read them as text. A stale stored
translation or hymnal stays selectable, a stored time zone that is not
recognized shows with a warning, newer server data rebases the form, a
422 shows under its field, and leaving with unsaved edits asks first.
The help lines say what a change of each default reaches.
TimezoneCombobox gains a warning and shows a value it does not list." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1523 passed, 24 skipped`; frontend `756 passed` in 92 files.

### Task 7: The Benediction hint links to Settings (S "Hand-off from 4"; clarification 13)

**Files:**
- Modify: `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, `frontend/src/components/builder/liturgy/section-card.tsx`

- [ ] **Step 1: Write the failing test**

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````tsx
    expect(within(benediction).getByText("Your church's default benediction. Admins can change it in Settings.")).toBeInTheDocument();
````

**with:**

````tsx
    const settings = within(benediction).getByRole("link", { name: "Settings." });
    expect(settings).toHaveAttribute("href", "/settings/church"); // 6a-1: the default lives in Settings → Church
    expect(settings.parentElement).toHaveTextContent("Your church's default benediction. Admins can change it in Settings.");
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````tsx
    expect(within(benediction).queryByText(/Your church's default benediction/)).toBeNull();
````

**with:**

````tsx
    expect(within(benediction).queryByText(/Your church's default benediction/)).toBeNull();
    expect(within(benediction).queryByRole("link", { name: "Settings." })).toBeNull();
````

- [ ] **Step 2: See it fail**

Run: `(cd frontend && npx vitest run src/components/builder/liturgy/liturgy-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected:**
```
   × the Liturgy step (S User experience) > shows the church's default benediction and follows it until edited; Use church default follows it again <t>ms
      Tests  1 failed | 43 passed (44)
```

- [ ] **Step 3: Link the hint**

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
import { useEffect, useRef, useState } from "react";
````

**with:**

````tsx
import { useEffect, useRef, useState, type ReactNode } from "react";
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
 */
export function SectionCard({ spec, assuranceResponse, defaultBenediction, maxLength, aiAvailable }: SectionCardProps) {
````

**with:**

````tsx
 */
/**
 * The Benediction's church-default hint ("… Admins can change it in
 * Settings.", from GET /liturgy/config) with its last "Settings" and what
 * follows it (the full stop) as a link to Settings → Church, where the
 * default lives (6a spec, hand-off from 4; slice 6a-1). The link ends the
 * sentence, so the card's description reads the hint unchanged. Every role
 * gets the link; a member lands on the read-only page.
 */
function withSettingsLink(hint: string): ReactNode {
  const at = hint.lastIndexOf("Settings");
  if (at < 0) return hint;
  return (
    <>
      {hint.slice(0, at)}
      <Link href="/settings/church" className="underline underline-offset-2 hover:text-foreground">
        {hint.slice(at)}
      </Link>
    </>
  );
}

export function SectionCard({ spec, assuranceResponse, defaultBenediction, maxLength, aiAvailable }: SectionCardProps) {
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
              {hint}
````

**with:**

````tsx
              {followsDefault ? withSettingsLink(hint) : hint}
````

- [ ] **Step 4: See it pass, and the suite**

`review-step.test.tsx` pins the Benediction card's accessible description to the whole hint: it must pass unchanged.

Run: `(cd frontend && npx vitest run src/components/builder/liturgy 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
`      Tests  73 passed (73)`; ` Test Files  92 passed (92)` and `      Tests  756 passed (756)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/builder/liturgy/section-card.tsx frontend/src/components/builder/liturgy/liturgy-step.test.tsx
git commit -q -m "Slice 6a-1: the Benediction hint links to Settings" -m "On a Benediction card that follows the church's default, the hint's
closing \"Settings.\" links to Settings → Church, for every role." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1523 passed, 24 skipped`; frontend `756 passed` in 92 files.

## Docs, verification, the PR, the merge (T8-T10)

### Task 8: Docs: the manual check items (clarification 15)

**Files:**
- Modify: `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py`

- [ ] **Step 1: Append the items and move the headings pin**

**In `backend/tests/test_slice1_docs.py`, replace:**

````python
    # checks), the service reviewer "## Service reviewer", slice 5a-1 "## Slice 5a", and the printed bulletin's
    # PR 1 "## Printed bulletin".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-8:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4", "## Service reviewer",
                        "## Slice 5a", "## Printed bulletin"]
````

**with:**

````python
    # checks), the service reviewer "## Service reviewer", slice 5a-1 "## Slice 5a", the printed bulletin's
    # PR 1 "## Printed bulletin" and slice 6a-1 "## Slice 6a".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-9:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4", "## Service reviewer",
                        "## Slice 5a", "## Printed bulletin", "## Slice 6a"]
````

**Append to `docs/manual-verification.md`:**

````markdown

## Slice 6a

Run on the production URL https://worship-service-builder.vercel.app, on an
iPhone with Safari at 375 px and on desktop Chrome. These are the 6a spec's
manual checks for 6a-1 (the Settings area and the Church page), as the
owner's planning answers of 2026-10-05 split 6a into three PRs; 6a-2
(Hymns) and 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings
moved in) add their own items here. After the 6a-1 merge the owner's guided
check (one step at a time on the phone) covers the items marked "(owner,
after 6a-1)"; the results go into `docs/ops-runbook.md` → "Slice 6a-1
record". Record what the page shows, never an email address or a church id.

- [ ] (owner, after 6a-1) **1.** The menu at the top has **Settings** after **Services**. Tap it: **Settings** opens on **Church** ("You're the owner of {church}."), with the sections **Church** and **Bulletin**; **Bulletin** opens the Bulletin settings page.
- [ ] (owner, after 6a-1) **2.** On **Church**, the church's name, time zone, default Bible translation, default hymnal (with one hymnal: "{code} (your only hymnal)") and default Benediction show as saved. Change the default Bible translation and tap **Save profile**: "Profile saved.". Open **Builder** step 1 of a service that has not chosen its own translation: the passages are in the new translation with no reload. Expected, not a bug (6a-1 owner question 11): a service whose translation was picked by hand as the one that was then the default follows the new default too, and so does a saved service when it is reopened. Change it back.
- [ ] (owner, after 6a-1) **3.** Change the default Benediction and save. Start a **New service** (if it asks to clear the current draft, tap **Cancel** and open the liturgy step of the current service instead, when you have not typed its Benediction yourself) and open the liturgy step: the Benediction card shows the new text, and its hint's **Settings.** opens **Settings** → **Church**. A Benediction card you typed yourself is unchanged. Put the Benediction back as it was (if it was the standard Halverson text, type **Halverson**: the word stands for the full text).
- [ ] (owner, after 6a-1) **4.** On **Church**, change the name without saving and tap **Builder** at the top: "Discard unsaved changes?" asks first; **Keep editing** stays with the change, **Discard changes** goes to the builder. At 375 px: no sideways scroll on **Settings**; the fields, the section links and **Save profile** are easy to tap.
- [ ] **5.** Rename the church and save: the church switcher shows the new name with no reload. Rename it back.
- [ ] **6.** The time zone list offers "Use this device's time zone (…)" when the device's zone differs from the church's; tapping it and saving stores it (`GET /church` answers it with `timezone_valid` true).
- [ ] **7.** Signed in as a plain member of the same church: **Settings** → **Church** shows "Only admins can edit the church profile." and the profile as plain text, with no fields and no **Save profile**; the Benediction hint's **Settings.** opens the same page.
- [ ] **8.** Saving the profile keeps the church's other settings: the Bulletin settings, the rubric and the liturgy prompts are as they were.
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected:**
`89 passed in <t>s`; `4`; `0`; ` 2 files changed, 25 insertions(+), 4 deletions(-)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -q -m "Docs: slice 6a-1 manual checks" -m "docs/manual-verification.md gains \"## Slice 6a\": the owner's phone
check after 6a-1 (Settings from the menu, the default translation and
Benediction followed by the builder, the leave guard and the page at
375 px) and the agent's checks (a rename, the device's time zone, a
member, the other settings kept). test_slice1_docs.py pins the last nine
## headings, the new one last." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1523 passed, 24 skipped`; frontend `756 passed` in 92 files.

### Task 9: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
ls backend/migrations/versions | grep -c '^0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `7`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 9)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the frontend three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/settings")
```

**Expected:** `1523 passed, 24 skipped in <t>s`; three times ` Test Files  92 passed (92)` and `      Tests  756 passed (756)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s` and the route lines `├ ○ /bulletin-settings`, `├ ○ /settings` and `├ ○ /settings/church` and no `Error` (a font `Failed to fetch` only: say so and rely on CI).

- [ ] **Step 3 (agent): The API files match, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/usecases/members.py backend/usecases/church_admin.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations backend/db .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); `imports grep exit 1`; `raw html grep exit 1`; exactly these 42 paths (the Voices V1 docs, the runbook's Voices note and its persona-editing fix, and the two 6a spec amendments ride along until merged; the Voices code was reverted on the branch, so it is not in the diff):
```
M	backend/api/routes/me.py
M	backend/repos/churches.py
M	backend/tests/test_api_church_profile.py
A	backend/tests/test_church_admin.py
A	backend/tests/test_church_admin_postgres.py
M	backend/tests/test_no_streamlit_in_core.py
M	backend/tests/test_slice1_docs.py
A	backend/usecases/church_admin.py
A	backend/usecases/members.py
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-05-slice-6a1-settings-church.md
A	docs/superpowers/plans/2026-10-05-voices-v1.md
M	docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md
M	docs/superpowers/specs/2026-10-01-voices-of-the-church-decisions.md
M	docs/superpowers/specs/2026-10-02-pew-voices-idea.md
A	docs/superpowers/specs/2026-10-05-voices-of-the-church-design.md
A	docs/superpowers/specs/2026-10-05-voices-rights-check.md
A	frontend/src/app/(signed-in)/(church)/settings/church/page.tsx
A	frontend/src/app/(signed-in)/(church)/settings/layout.tsx
A	frontend/src/app/(signed-in)/(church)/settings/page.tsx
M	frontend/src/components/app/app-header.test.tsx
M	frontend/src/components/app/app-nav.tsx
M	frontend/src/components/app/church-switcher.tsx
A	frontend/src/components/app/leave-guard.test.tsx
A	frontend/src/components/app/leave-guard.tsx
M	frontend/src/components/app/timezone-combobox.test.tsx
M	frontend/src/components/app/timezone-combobox.tsx
M	frontend/src/components/builder/liturgy/liturgy-step.test.tsx
M	frontend/src/components/builder/liturgy/section-card.tsx
M	frontend/src/components/bulletin-settings/bulletin-settings-page.tsx
A	frontend/src/components/settings/church-settings-page.test.tsx
A	frontend/src/components/settings/church-settings-page.tsx
A	frontend/src/components/settings/sections.ts
A	frontend/src/components/settings/settings-layout.test.tsx
A	frontend/src/components/settings/settings-nav.tsx
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/types.ts
M	frontend/src/lib/queries/church.ts
A	frontend/src/lib/settings/profile.test.ts
A	frontend/src/lib/settings/profile.ts
```
`0`; the subjects oldest first: the branch's commits since `875aefc` (the Voices V1 plan, build and revert, ending `Drop Voices of the Church (owner, 2026-10-05): revert its code, keep its record`), `Spec 6a: owner's planning answers (2026-10-05: three PRs, no Contacts or email, personas move to the pews feature, admins only delete hymns)`, `Spec 6a: the owner wants the full emailing after all (5b and Contacts return after 6a-1)`, the plan commits (`WIP plan: …` and `Plan: slice 6a-1 (the Settings area and the Church page)`), `Runbook: persona editing is no longer part of 6a (6a-1 plan review M11)`, the review-fix plan commits (`WIP plan: slice 6a-1 review fixes (before the replay)` and `Plan: slice 6a-1 review fixes (replayed; build notes)`) and any later plan commit, then T1-T8's eight subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> Settings and the Church page (slice 6a-1) are verified on this machine: backend 1523 passed, 24 skipped (1487 before); frontend 756 tests in 92 files (734 before), three runs in a row; typecheck, lint and the production build are clean. It adds one API route (`PATCH /church`), no database change and no new package. The menu at the top gets **Settings**: it opens on **Church**, where you (and any admin) change the church's name, time zone, default Bible translation, default hymnal and default Benediction; other members see them as text. The builder follows a change with no reload, leaving with unsaved changes asks first (also "Join or create a church…" in the church menu), and the Benediction card's "Settings." links there. The Settings menu also lists **Bulletin** (your Bulletin settings page, unchanged until 6a-3 moves it in). The pull request also carries the Voices of the Church documents and the two 6a spec notes from today (the Voices code itself was removed). May I open the pull request as a **draft** titled "Slice 6a-1: the Settings area and the Church page", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/6a1-pr-body.md" <<'BODY'
Slice 6a-1: the Settings area and the Church page (the first of 6a's three PRs; owner's 6a planning answers of 2026-10-05). Spec: docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md. Plan: docs/superpowers/plans/2026-10-05-slice-6a1-settings-church.md. No database change, no new package or variable, no draft change.

- PATCH /church (owners and admins): name, time zone (exact IANA name), default translation, default hymnal, default Benediction; only the fields sent, all or nothing, in one transaction that locks the church row and re-reads the caller's role under it (usecases/members.lock_and_read_actor, the helper 6b shares; repos.churches.lock_church). Every other settings key stays.
- Settings: a Settings item in the top menu; /settings opens Church; the section nav lists Church and Bulletin (the existing Bulletin settings page, until 6a-3 moves it in).
- The Church page: admins edit and save only what changed (a stale stored translation or hymnal kept, an unrecognized time zone shown with a warning, newer server data rebases the form); members read it as text. The builder follows at once (the profile cache, /me, /hymnals).
- One leave guard (LeaveGuard) for the Church and Bulletin settings pages: any in-app link, and the church menu's "Join or create a church…", asks "Discard unsaved changes?" while there are unsaved edits.
- The Benediction card's hint links "Settings." to Settings → Church.
- docs/manual-verification.md: "## Slice 6a".
- Rides along: the Voices of the Church V1 documents (its code was reverted on this branch) and the 6a spec's two amendments of 2026-10-05.

Later: 6a-2 (Hymns), 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings moved in), 5b (Account, Contacts, email), 6b (People).

Tests: backend 1487 → 1523 passed, 23 → 24 skipped; frontend 734 → 756 in 88 → 92 files

After merge (Task 10): a short check on the owner's phone, then a "Slice 6a-1 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 6a-1: the Settings area and the Church page" \
  --body-file "<scratch>/6a1-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1523 passed, 24 skipped`, backend-postgres `24 passed, 1523 deselected`, frontend `756 passed` in 92 files. Then send: "PR #<N> is green: backend 1523 passed, 24 skipped; 751 frontend tests in 92 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_church_admin.py` (its first three tests), `test_church_settings.py`, `test_no_streamlit_in_core.py` | T1 |
| `test_church_admin.py` (the rest), `test_api_church_profile.py`, `test_church_admin_postgres.py` (CI `backend-postgres`), `test_openapi_contract.py`, `test_route_guards.py` | T2 |
| `profile.test.ts` | T3 |
| `leave-guard.test.tsx`, `bulletin-settings-page.test.tsx`, `app-header.test.tsx` (its "Join or create a church…" test) | T4 |
| `settings-layout.test.tsx`, `app-header.test.tsx` (its nav test) | T5 |
| `church-settings-page.test.tsx`, `timezone-combobox.test.tsx`, `create-church-form.test.tsx` | T6 |
| `liturgy-step.test.tsx`, `review-step.test.tsx` | T7 |
| `test_slice1_docs.py`, `test_docs.py` | T8 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, slice 6a-1 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1523 passed, 24 skipped`; frontend `756 passed` in 92 files.

### Task 10: Merge, the owner's phone check (four steps), the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate (production stays at `0007_bulletin_images`); Railway serves `PATCH /church`, Vercel the Settings area. The owner's check is **one step at a time** (send one, wait for the report or "next"), on the phone, on the production URL, in the owner's own church, signed in as its owner. Every change the check makes to the church's profile is put back in the same step. The agent writes each result into `<scratch>/6a1-t10-results.md` (not committed). Record what the page showed, never a token, an email address, a church id or a person's name.

**Files:** Modify (the records PR, Step 8): `docs/ops-runbook.md`: insert `### Slice 6a-1 record` right before `## Backups` (after the last record above it, today the "Printed bulletin PR 3b record" table, whose last row starts `| Roadmap change |`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (slice 6a-1: Settings and the Church page) is ready, green and up to date with main. There is no database change, and nothing changes for your church until someone saves its profile. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about three minutes for Railway and Vercel before Step 2; a failed deploy keeps the old version running (Step R).

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 4: finding Settings (manual-verification item 1)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. Is there a **Settings** item in the menu at the top, after **Builder** and **Services**? Tap it: does it open **Settings** with "You're the owner of …" and two sections, **Church** and **Bulletin**, with **Church profile** showing your church's name, time zone, default Bible translation, default hymnal and default Benediction? Tap **Bulletin**: does your Bulletin settings page open?

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 4: the translation (item 2)**

> Back on **Settings** → **Church**, note your default Bible translation, choose another one (for example King James Version) and tap **Save profile**: does "Profile saved." show? Open **Builder**, step 1, on a service where you have not picked a translation for that service: are the passages now in the translation you chose, without reloading? (A service where you once picked your usual translation by hand changes too, and so does a saved service when you reopen it: that is expected, not a fault.) Then go back to **Settings** → **Church**, put your usual translation back and save.

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 4: the Benediction (item 3)**

> On **Settings** → **Church**, look at your default Benediction: is it the standard Halverson text ("You go nowhere by accident…")? If not, copy it somewhere safe. Change it to something short such as "Go in peace." and save. In the builder, start a **New service**; if it asks "Start a new service? This clears the current draft on this device.", tap **Cancel** and open the liturgy step of your current service instead (when you have not typed its Benediction yourself). Does the Benediction card show "Go in peace."? Under it, tap **Settings.** in "Admins can change it in Settings.": does **Settings** → **Church** open? Put your Benediction back and save: if it was the standard text, type just the word **Halverson** (it stands for the full text); otherwise paste your copy.

The word "Halverson" restores exactly the standard text (`resolve_default_benediction`), so there is no long text to paste on a phone; a blank field would mean "no default". Record only whether it was restored.

- [ ] **Step 5 (OWNER, then agent): Phone, step 4 of 4: unsaved changes and the phone screen (item 4)**

> On **Settings** → **Church**, add a letter to the church's name but do not save, then tap **Builder** at the top: does "Discard unsaved changes?" ask first? Tap **Keep editing**: is your change still there? Tap **Builder** again and **Discard changes**: does the builder open, and is the name unchanged when you go back to **Settings**? Is the Settings page easy to use on the phone: no sideways scrolling, and the fields, the section links and **Save profile** easy to tap?

- [ ] **Step 6 (agent): The agent's own checks (items 5-8)**

On the production URL, in a test church the agent may change (one of the two slice 1 test churches the owner kept, never the owner's own church), signed in as its owner if the session has a test account, else skipped and recorded as "not run": item 5 (rename, the switcher follows; rename back), item 6 (the device's time zone), item 8 (after a profile save, the Bulletin settings, the rubric and the prompts are as they were). Item 7 needs a plain member's sign-in; record "not run" unless the owner offers one.

- [ ] **Step 7 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/6a1-t10-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 8 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it (today `### Printed bulletin PR 3b record`). Insert, right before `## Backups` (one blank line on each side):

```markdown
### Slice 6a-1 record

Slice 6a-1 (the Settings area and the Church page: a Settings item in the
top menu, `/settings` opening on Church, `PATCH /church` for the name,
time zone, default translation, default hymnal and default Benediction,
written under the church-row lock with the caller's role re-read; one leave
guard for the Church and Bulletin settings pages; the Benediction hint's
link) merged as PR #<N>, the first of slice 6a's three PRs (owner's 6a
planning answers of 2026-10-05). No database change and no new package;
production stays at `0007_bulletin_images`. The owner's check was four
steps on a phone, covering the "(owner, after 6a-1)" items of
`docs/manual-verification.md` → "Slice 6a"; every profile change made for
the check was put back. No token, email address, church id or person's
name is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success | <date> |
| 1. Finding Settings (phone: <phone and browser>) | <Settings in the menu; Church and Bulletin listed; the profile shown; Bulletin opened Bulletin settings. / …> | <date> |
| 2. The translation | <"Profile saved."; the builder's passages followed with no reload; put back. / …> | <date> |
| 3. The Benediction | <A new service's Benediction card showed the new default; the hint's Settings. opened Church; put back. / …> | <date> |
| 4. Unsaved changes and the phone | <"Discard unsaved changes?" asked; Keep editing kept the change; Discard changes left it unsaved; no sideways scroll, easy to tap. / …> | <date> |
| Agent checks | <Items 5, 6 and 8 in a test church: <results>. / Not run: <why>.> Item 7 (a member): <result / not run> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: slice 5b's planning round (Gmail, emailing, contacts; owner, 2026-10-05), 6a-2 (Hymns) and 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings moved in), in the order the owner picks | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye. Then (not replayed):

```bash
sed -n '/^### Slice 6a-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 6a-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 6a-1 record (merged; owner's phone check)" -m "Records slice 6a-1 (PR #<N>): the merge and CI on main and the
owner's four-step phone check (finding Settings, the translation and
the Benediction followed by the builder, the leave guard and the phone
screen). No token, email, church id or person's name is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 9 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 6a-1 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 6a-1 record" \
  --body "Records slice 6a-1 (PR #<N>) in docs/ops-runbook.md → Slice 6a-1 record: the merge and the owner's four-step phone check. No token, email, church id or person's name is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Slice 6a-1 is live and recorded; <n> follow-ups. Next: the order you pick for 5b's planning, 6a-2 and 6a-3."

- [ ] **Step R (only if the release must come out): Revert**

Code only (no schema to undo). On the owner's yes for each outward command: a branch `claude/revert-6a1` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert slice 6a-1 (PR #<N>)" with the trailer, both suites (`1487 passed, 23 skipped`; `734 passed` in 88), a PR, CI, and the merge on the owner's yes; record it in the record. Anything saved through the Church page stays in the church's row (name, time zone, `bible_translation`, `default_hymnal`, `default_benediction`), which the builder already reads, so nothing needs undoing in the data.

Expected counts after this task: backend `1523 passed, 24 skipped` on `main`; frontend `756 passed` in 92 files. The records PR adds no test.

---
## Build notes

**How this plan was written (2026-10-05).** Each task's code was built and run in a throwaway worktree of `426931b` (the branch head `3d5daad` plus the plan's skeleton commit; the repo's `.venv`; a hard-linked copy of `frontend/node_modules`, since Turbopack's production build refuses a `node_modules` symlink that points outside the project), one commit per task; the directives were then generated from those commits (`gen.py`: a new file as **Create**, an addition at the end of a file as **Append**, every other change as **In … replace** with just enough context to occur once in the file as it stands at that point, changes three or fewer lines apart in one block). No package, variable or migration was added. While building:
- **What S assumed and what exists.** No `lock_church`, `lock_and_read_actor`, `usecases/members.py`, `usecases/church_admin.py`, Settings layout or `sections.ts` existed (5b and 6b were never built), so T1 creates the lock helpers with the 6b spec's names and T5 the shell. `resolve_default_benediction` already keeps `""` (S's key-presence rule, slice 4 and the 2026-10-02 amendment), so the Benediction needs no backend change beyond the write; `test_one_bad_field_writes_nothing` and `test_only_the_fields_sent_are_written_and_other_settings_stay` cover it through `PATCH`. `handleAuthErrors` already ignores a role 403, so no `forbiddenIsRole` meta was added (clarification 16).
- **The leave guard moved, not copied.** The Bulletin settings page's `beforeunload` effect, its Back-link `onClick` and its dialog became `LeaveGuard`; the page's nine tests pass unchanged (the document-level capture listener stops a plain click before Next's `Link` runs, and a modified or middle click still reaches the link). The `ConfirmDialog` copy is the 2a page's.
- **The Benediction link includes the full stop.** With only the word "Settings" as the link, jsdom's accessible-description computation gave "… in Settings ." (a space before the full stop) and `review-step.test.tsx`'s pin of the description failed; the link "Settings." keeps the description exactly the hint.
- **The hymnal field counts `GET /hymnals`' items** before it shows "{code} (your only hymnal)" (and waits for them), so a stale stored code never shows as "your only hymnal", neither while the hymnals load nor when the church has none left (plan review M1).
- **The device-zone shortcut** is offered only for a zone the browser lists (a runner or a browser in `UTC`, which ICU does not list, gets no button rather than a 422).

**Plan review fixes (2026-10-05).** An adversarial review of the plan (no Critical findings; 4 Important, 12 Minor) was applied, each fix built and run in a second throwaway worktree of `426931b` (one commit per task again, the directives regenerated from them), then the whole plan replayed (below):
- **I1, other settings keys.** A mutation that replaced the settings JSON instead of merging it (`church.settings = dict(settings_patch)`) passed all 40 of T1-T2's tests. `test_only_the_fields_sent_are_written_and_other_settings_stay` now seeds every key the code keeps in `churches.settings` (`bible_translation`, `default_hymnal`, `default_benediction`, `bulletin`, `rubric`, `liturgy_prompts`, `prayer_library`, found by a grep of `backend`) plus an unknown one, saves the translation, the Benediction and the hymnal, and compares the whole dict; `test_a_profile_save_keeps_every_other_setting` does the same through `PATCH`. With the mutation: `2 failed, 43 passed`.
- **I2, the ESV where it is enforced.** A mutation that offered every translation (`list(scripture_fetcher.TRANSLATIONS)`) passed; `test_the_esv_is_accepted_only_where_its_key_is_set` (no key: 422 naming `bible_translation`; `ESV_API_KEY` set the way the app reads it, from the environment at call time: 200 with `effective_translation` `esv`) fails on it (`1 failed, 44 passed`).
- **I3, what a change reaches** (existing behaviour, no code change): clarification 11, the translation and hymnal help lines, T8 item 2 and T10 Step 3, and "Questions for the owner" 11.
- **I4, the Postgres race test now.** `test_church_admin_postgres.py` holds a profile save inside the lock and checks that `set_bulletin_settings` and `update_church_rubric` wait and every key survives. On a throwaway PG 16 cluster (initialised under `/var/lib/postgresql`, port 5433, never a real database): `24 passed, 1523 deselected`; with `lock_church`'s `with_for_update=True` turned off it fails ("the other settings writers did not wait for the lock").
- **M1-M3 (the Church page).** The hymnal field counts `GET /hymnals`' items, so a stored default with no hymns left shows the no-hymns line, never "(your only hymnal)"; while `GET /translations` loads or fails the items come from the profile, so a stored `esv` reads "ESV (not available on this server)", never as WEB; a member's summary shows the hymnal the builder uses, noting a stored one that is gone. Each has a new test that fails on the old page (`3 failed, 9 passed`).
- **M4, control characters in the name.** `clean_profile_patch` refuses any `bulletin_settings.NOT_ONE_LINE` character (NUL included, which Postgres refuses: the review's probe got a 500) with "Church name can't contain line breaks or control characters." under `name`: two usecase cases and one API case (a NUL over JSON).
- **M5 and M8, the leave guard.** `confirmLeave` guards "Join or create a church…"; a `blob:` or `data:` link is left alone; after **Discard changes** the link is clicked again with the guard standing aside, so its own handler navigates (a replace stays a replace). Each new case fails on its mutation (no protocol check; `router.push` in place of the re-click; the switcher without `confirmLeave`). The Bulletin settings page's nine tests and `app-header.test.tsx` pass unchanged: in jsdom Next's `Link` does not prevent the click, so the guard's fallback `router.push` runs, as before.
- **M6, M7, M9, M11, M12.** The Benediction help line and question 5; T10 Step 4 restores the Benediction by typing **Halverson** and says what to do if **New service** asks to clear the draft; the "Settings." deviation in clarification 16; the runbook's two "including persona editing" rows fixed on the branch (`Runbook: persona editing is no longer part of 6a (6a-1 plan review M11)`, docs only, before T1); the phone nav's layout for 5b in Follow-ups.
- **M10:** no change; noted in Risks.
- Counts: backend T2 +33 passed and +1 skipped (was +28), so 1523 passed, 24 skipped after T2; frontend T4 +3 (was +1) and T6 +13 (was +10), so 741, 743, 756; 42 paths (was 40: the Postgres test and `church-switcher.tsx`).

**Replay of the finished plan (2026-10-05, after the review fixes).** The directives of T1-T8 were applied in order (by `replay.py`, which parses each step's **Create**, **Append** and **In … replace** blocks and runs every command on its "Run:" lines, three times where it says so, then the task's commit block) onto a fresh detached worktree of `1adc1b2` (`WIP plan: slice 6a-1 review fixes (before the replay)`: the branch head `3d5daad` plus the plan's commits and the runbook fix), with the repo's `.venv` (a symlink) and a hard-linked copy of `frontend/node_modules` (`cp -al`):
- All 57 directives applied (T1 2 + 5, T2 5 + 5, T3 1 + 4, T4 1 + 10, T5 4 + 5, T6 2 + 6, T7 2 + 3, T8 2); every Replace anchor occurred exactly once. After T8, `backend` and `frontend/src` equaled the build worktree's, and `docs` too apart from this plan file and the runbook fix (`diff -r`).
- Baselines before T1: backend `1487 passed, 23 skipped`; frontend `734 passed` in 88 files.
- Every "see it fail" output is quoted from this replay (times as `<t>`): T1 the collection error and the import check's `1 failed, 2 passed`; T2 `33 failed, 12 passed` (every new test; the 12 are T1's 3 and the profile's 9); T3 and T4 the new file not loading; T5 and T6 one `×` and the new file not loading; T7 the one edited test.
- Every count matched the table: backend 1490, then 1523 passed and 24 skipped from T2 on; frontend 738 in 89, 741 in 90, 743 in 91, 756 in 92, 756 in 92; the three-times runs (T4 `12 passed`, T6 `31 passed`) the same each time, no flaky run; T2 Step 4 `63 passed`; typecheck 0 and lint 0 after T2-T7. The OpenAPI export and `gen:api` gave ` 2 files changed, 256 insertions(+), 1 deletion(-)`; T8 `89 passed`, `4`, `0`, ` 2 files changed, 25 insertions(+), 4 deletions(-)`.
- T9 Steps 1-3 on the replay worktree after T8: `HEAD..origin/main` 0; the suites `1523 passed, 24 skipped` and three times `92 passed` / `756 passed` with no `×` or `FAIL`; the production build `✓ Compiled successfully` with `○ /bulletin-settings`, `○ /settings` and `○ /settings/church` and no `Error`; the OpenAPI export and `gen:api` changed nothing after T2's commit; the imports and raw HTML greps exit 1; the 42 paths of Step 3 exactly; no migration, `backend/db`, workflow, package or Streamlit path; no em dash in any added line under `backend` or `frontend/src`; every commit has the trailer.
- The Postgres-marked tests on the throwaway PG 16 cluster after T8: `24 passed, 1523 deselected, 1 warning`.
- Not run while planning: the pushes, the PR and CI, the merge, Railway's and Vercel's deploys and the owner's phone check (T10).

## Spec coverage

| Owner answer or S item | Task(s) and tests |
|---|---|
| Answer 2: 6a-1 is the Settings shell and Church | T5 (the shell), T6 (Church); clarification 1 |
| Answer 4: admins change the church, everyone reads | T2 `test_a_member_cannot_change_the_profile`, `test_a_demoted_admin_or_a_removed_member_writes_nothing`; T6 "shows a member the profile as plain text, with the note and no Save" |
| Amendment "later the same day": the shell is the layout 5b adds Account and Contacts to | T5 `SETTINGS_SECTIONS` (one list); clarification 3 |
| S "Settings nav": `/settings` → Church, the nav | T5 "shows the heading, who you are in the church, and the sections with the current one marked", "shows a member the same sections, and /settings opens Church" |
| Reaching Settings from the app | T5 `app-header.test.tsx` (the Settings item, current under `/settings`) |
| S UX §1: the fields, help, stale values, no hymnals, one hymnal | T6 "lets an admin change only the name…", "keeps a stale stored translation or hymnal selectable…", "says there are no hymns when a stored default hymnal is left…", "never labels a stored translation as another one…", "shows a stored time zone it does not recognize…", "shows a member the hymnal the builder uses…"; T3 `translationItems`, `hymnalItems` |
| S "Every page": only changed fields, rebase on refetch, reset after save | T3 "starts at the stored values…", "rebases on newer data…"; T6 "rebases on newer data: another admin's rename shows…" |
| S "Leave guard" (links, and the switcher's "Join or create a church…") | T4 `leave-guard.test.tsx` ("asks before an in-app link…" with a `blob:` link going on, "after Discard changes, the link's own handler navigates…", "asks before the church menu's Join or create a church…"); T6 "asks before leaving with unsaved edits, through the Settings nav"; `bulletin-settings-page.test.tsx` and `app-header.test.tsx` (unchanged) |
| S API `PATCH /church`: messages, fields, order, nothing written on a failure, `extra="forbid"` | T2 `test_a_bad_field_is_named_and_the_first_in_order_wins` (13 cases, a NUL and a line break in the name among them), `test_a_bad_field_is_a_422_naming_it_and_nothing_is_written` (7 cases), `test_the_esv_is_accepted_only_where_its_key_is_set`, `test_a_church_id_in_the_body_is_refused_and_isolation`, `test_an_empty_or_all_null_patch_changes_nothing` |
| S Semantics: one transaction, settings merged, unknown keys kept, stale stored translation survives | T2 `test_only_the_fields_sent_are_written_and_other_settings_stay` and `test_a_profile_save_keeps_every_other_setting` (every settings key seeded, the whole dict compared), `test_an_unavailable_stored_translation_survives_a_name_change`, `test_the_profile_is_read_and_written_under_one_row_lock` |
| S Locking on real Postgres (the race test) | T2 `test_church_admin_postgres.py` `test_other_settings_writers_wait_for_a_profile_save_and_every_key_survives` (CI `backend-postgres`) |
| S Locking: `lock_church`, `lock_and_read_actor`, `require_admin_role` | T1 `test_the_role_is_read_under_the_church_row_lock`, `test_a_church_or_a_membership_gone_is_no_church_access`, `test_require_admin_role`; T2 `test_a_demoted_admin_or_a_removed_member_writes_nothing` |
| The Benediction's key-presence rule (`""` = no default) | T2 `test_the_fields_sent_are_cleaned_and_nothing_else`, `test_only_the_fields_sent_are_written_and_other_settings_stay`; existing `test_default_benediction_is_the_church_s_or_halverson` |
| Timezone IANA check on edit | T2 (the four "Unknown timezone." cases); T6 (the warning, the device's zone); T6 `timezone-combobox.test.tsx` |
| The builder sees translation, hymnal and Benediction changes without a reload | T6 (the profile cached, `["me"]` and `["church", id, "hymnals"]` invalidated); existing `liturgy-step.test.tsx` "shows the church's default benediction and follows it…" (a profile change moves an untouched card); clarification 11 |
| A role 403 does not take the church fallback | T6 "toasts a role 403, refetches the profile and does not report the church as lost" |
| Hand-off from 4: the Benediction hint links to Settings | T7 `liturgy-step.test.tsx`; `review-step.test.tsx` (description unchanged) |
| Isolation and guards | T2 `assert_church_isolated`; `test_route_guards.py` unchanged and passing |
| Layering | T1 `test_no_streamlit_in_core.py` (two modules added); T9 imports grep |
| OpenAPI and types regenerated | T2 Step 4; T9 Step 3; `test_openapi_contract.py` |
| A guided phone check after the PR | T10 Steps 2-5; `docs/manual-verification.md` "## Slice 6a" (T8) |

S items **not** in 6a-1: Hymns, hymnals, hymn facts (6a-2); Liturgy prompts, Prayers, Rubric (with `PATCH /rubric` under the lock and its `defaults`), Bulletin settings moved under `/settings` (6a-3); the ESV key move ("Questions for the owner" 9); Contacts, Account and the email hand-offs (5b, after its own planning round); the race test's pairing with `PUT /church/liturgy-prompts` (6a-3 adds that route).

## Follow-ups (not in 6a-1)

- 6a-3: move `PATCH /rubric` and `PUT /church/bulletin-settings` under `lock_and_read_actor` and `require_admin_role`; rename `_merge_settings` to `merge_settings(…, session=None)` when the prompts and prayers writes need it; add `PUT /church/liturgy-prompts` to `test_church_admin_postgres.py`'s race; point the "Bulletin" entry of `SETTINGS_SECTIONS` under `/settings`.
- 6a-3 or 5b, whichever comes first: on a phone the Settings nav is a wrapping row of 44 px links; it fits today's two, but S's final list of nine would wrap to about three rows at 375 px, so switch the phone row to a horizontal scroller or a Select then (`SETTINGS_SECTIONS` stays one constant; no rework of the layout's place; plan review M12).
- 6a-2: the no-hymnals line on the Church page can link to Hymns once that page exists.
- Choosing another church in the church menu does not ask before discarding unsaved settings edits (clarification 8); `confirmLeave` (already used by "Join or create a church…") is the fix if the owner wants it.
- If the owner does not accept "Questions for the owner" 11: store an explicit translation or hymnal pick (and a saved service's translation) instead of null, a draft-schema change.
- `POST /churches` has the same gap the church name had (a control character, NUL included, is accepted, and a NUL is a 500 on Postgres); the onboarding form can take `church_admin`'s check.
- The ESV key still read by `scripture_fetcher` from the environment (slice 2's recorded deviation), if the owner wants it moved later.
- Carried from 2a: `_merge_settings` raises `TypeError` (a 500) if `churches.settings` is ever not an object; `repos.churches.update_profile` has the same shape (`{**(church.settings or {}), …}`).

## Questions for the owner

**Owner's answer (Beau, 2026-10-06): "sounds good" (all recommended).** Questions 1-11 below are accepted as written and are binding for the build.

Your 6a planning answers of 2026-10-05 (the seven, and the reversal of answer 7 the same day) are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **Where Settings is** (clarification 2): a third item, **Settings**, in the menu at the top, after **Builder** and **Services** (on a phone, the row under the header has three parts). Recommended: accept.
2. **What the Settings area lists until the other pages come** (clarification 3): **Church** and **Bulletin**; **Bulletin** opens your existing Bulletin settings page as it is today (with its **Back to Review & send**), until 6a-3 moves it inside Settings. Hymns comes with 6a-2, Liturgy prompts, Prayers and Rubric with 6a-3, and Account and Contacts with 5b. (The other choice: list only **Church** for now.) Recommended: accept.
3. **The Settings heading** (clarification 3): "Settings", with "You're the owner of {your church}." (or "an admin of", "a member of") under it, then the page's own title, "Church profile". Recommended: accept.
4. **Members read the profile as plain text** (clarification 5): a member sees "Only admins can edit the church profile." and the name, time zone, translation, hymnal and Benediction as text, with no boxes and no Save button, as on Bulletin settings. (The other choice, in the spec: the same boxes, greyed out.) Recommended: accept.
5. **The Church page's wording** (clarifications 4, 5, 9, 14): the labels "Church name", "Time zone", "Default Bible translation", "Default hymnal", "Default Benediction", **Save profile** and "Profile saved."; the help lines "Used for passage text in the builder, in every service that has not switched to another translation (saved services too, when reopened). Anyone can switch it for a single service.", "The hymnal the builder opens with, in every unsaved service that has not switched to another hymnal. You can switch hymnals for a single service." and "Pre-fills the Benediction card in each new service, and in unsaved services whose card still shows the default. Leave it blank to let the AI write the benediction." (the spec's Benediction line said only "in each new service", but a change also refills the card of every unsaved service that still shows the default, on every member's device; the other choice is the spec's shorter line); "Use this device's time zone (…)" under the time zone; "Timezone not recognized. Choose one from the list." for a stored zone the app does not know; "{ID} (not available on this server)" and "{code} (no longer in your hymnals)" for a stored translation or hymnal that is no longer offered, kept as chosen; "{code} (your only hymnal)" with one hymnal; for a member, "{hymnal} (the builder uses this; {code} is no longer in your hymnals)" when the saved default hymnal is gone; and "Church name can't contain line breaks or control characters." when a name has one (only an odd paste can do this; the other choice is to turn such characters quietly into a space). Recommended: accept.
6. **No "Halverson" note** (clarification 4): the spec's note under the Benediction ("The bulletin will print the word Halverson") is left out, because since 2026-10-02 the word prints the full Halverson text. A blank Benediction means no default (the AI writes it). Recommended: accept.
7. **No hymns yet** (clarification 4): a church with no hymns sees "Your church has no hymns yet, so there is no default hymnal." in place of the hymnal field (the spec's line pointed to the Hymns page, which comes in 6a-2). Recommended: accept.
8. **The warning before leaving unsaved changes** (clarification 8): on the Church page and on Bulletin settings, any link in the app (the menu at the top, the Settings sections, a page's own links) and **Join or create a church…** in the church menu ask "Discard unsaved changes?" first, and closing or reloading the tab shows the browser's own warning. Bulletin settings gains the menu links (today only its Back link asks). Not covered: the browser's Back button, Log out, and choosing another church in the church menu (the spec wanted that covered too; it is left out to keep this PR small, and choosing another church with unsaved changes loses them without asking). Recommended: accept.
9. **The ESV key stays where it is** (clarification 16): the spec planned a behind-the-scenes move of the ESV key's setting with 6a; nothing you see depends on it, and the new page checks translations exactly as the rest of the app does today, so it is left out of 6a-1. Recommended: accept (drop it, or leave it for the clean-up at the end of the migration).
10. **Two admins saving the profile at once** (clarification 12): a field only one of them changed keeps that change; the same field changed by both keeps the later save, with no "someone else changed this" warning. While the page is open, a newer save from elsewhere updates every field you have not changed. Recommended: accept.
11. **What a change of the default translation or hymnal reaches** (clarification 11): this is how the builder already works; the Church page only makes it reachable. Changing the default Bible translation changes the passages of every service that uses the church's translation. That includes a service where someone picked that same translation by hand while it was the default (the builder keeps no record of such a pick), and a saved service when you reopen it, for example to print it again. Changing the default hymnal does the same for services not yet saved (a saved service keeps its hymnal). The Benediction is not affected this way: a saved service keeps its own. The help lines under both fields say so briefly, and the phone check expects it. Recommended: accept for now (if not, a later change can make the builder remember a hand-picked translation or hymnal, and the translation a service was saved with).

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T9); the merge on your yes, then four phone checks one at a time, and the records PR (T10).
