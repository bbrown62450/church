# Printed Bulletin PR 2a: Bulletin Settings

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first half of printed bulletin PR 2 (PR 2 planning answer 1, 2026-10-02): **the church's standing bulletin settings, printed at once.** After it merges, the **Printed bulletin** card on step 4 of the Service Builder (`/builder/review`) says where the standing details come from, lists the ones still blank above the download buttons ("Not filled in: phone, organist."), and has a **Bulletin settings** button that opens a new page, `/bulletin-settings`. There an owner or admin fills in the church's address (up to three lines), phone, email, website and Facebook name, the service time, the standing worship leader, liturgist and organist, who leads each part of the service and which parts the congregation stands for, the stand note and the Gloria Patri words, and taps **Save settings**; a member sees the same settings as a plain read-only summary. Every member's printed bulletin (the PDF and the Word version) then prints them: the contact lines on the cover, the three people in the header ("Rev. Alex Example, Worship Leader"), the service time across from the date, each part's leader's name on the right, the stars, the stand note and the Gloria Patri words. A blank field prints nothing (no line, no [placeholder]; answer 3). The weekly fields (the prelude and postlude, the announcements, the cover picture) keep PR 1's [placeholders] until PR 2b and PR 3. The settings live in `churches.settings["bulletin"]`: **no migration** (Alembic head stays `0005_services_extras`), no draft change, no new package or variable; production Streamlit (branch `streamlit-frozen`) is untouched.

**Architecture:** Backend first. `backend/bulletin_settings.py` (new, pure) defines `BulletinSettings` (the fields, the 21 element keys, the three roles, the limits and the defaults, which are PR 1's: the sample's stars and leader roles, "Congregation stands if able", the traditional Gloria Patri, everything else blank), `read(settings)` (the stored value read tolerantly, field by field) and `to_json()` (the stored and answered shape). `printed_bulletin.PrintedService` gains `settings: BulletinSettings`, and the order of worship, the header and the cover read the stars, the leaders, the names, the time, the contact lines and the words from it instead of PR 1's constants. `GET /church/bulletin-settings` (`require_church`, any member) and `PUT /church/bulletin-settings` (`require_admin`) live in `api/routes/bulletin_settings.py` over `usecases/church_bulletin.py`; the PUT stores the cleaned body whole as `settings["bulletin"]` through `repos.churches.set_bulletin_settings`, a locked read-modify-write (`SELECT … FOR UPDATE` in `_merge_settings`) that keeps every other settings key. `usecases.documents.build_printed` passes `church_bulletin.read_settings(church["settings"])` (the settings are already read with the church's name; every stored text is made Word-safe on the way). `printed_pdf` shrinks the cover's contact lines to the room left on the cover (`KeepInFrame`), so the order of worship always starts on page 1. Frontend: `lib/bulletin-settings.ts` (the parts' labels, the form mapping, "Not filled in"), `lib/queries/bulletin-settings.ts` (`useBulletinSettings`, `useSaveBulletinSettings`), the page `components/bulletin-settings/bulletin-settings-page.tsx` at `app/(signed-in)/(church)/bulletin-settings/page.tsx` (fetched again on opening; 6a's rebase and leave-guard rules for settings forms; a read-only summary for members), and the card's new lines.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy, reportlab 5 and python-docx (PR 1's renderers; the PDF cover gains a `KeepInFrame`), pytest; Next 16, React 19, TypeScript 5, Base UI (Select, Switch), TanStack Query 5, sonner, Vitest 3 with Testing Library.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`: owner answers 2, 8, 9; "PR 2 planning answers" 1-3 and 7 (binding); "What prints where"; "Data model" (standing settings in `churches.settings["bulletin"]`); "The Bulletin step and the settings panel"; "Scope by PR".
- The PR 1 plan `docs/superpowers/plans/2026-10-02-printed-bulletin-1.md` (the format model; its clarifications 7-9, 15 and 17 are what this PR changes) and the 5a-3 plan `docs/superpowers/plans/2026-10-02-slice-5a3-save-services.md`.
- The 6a spec `docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md` (members see a settings page read-only with a banner; 6a's locked writes and `lock_and_read_actor`; 6a later moves this panel into Settings without changing the storage).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.2 (guards), §1.5 (errors), §1.7 (settings JSON writes under `SELECT … FOR UPDATE`), §2.2 (layers), §4.1 (routes), §4.4 (keys), §4.8 and §4.9 (forms, 44 px, Base UI Select).
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `4ed23fd` = `origin/main` `d79f301` plus "Runbook: printed bulletin PR 1 record (owner's phone check; print test pending)" `350f9a5`, "Spec: printed bulletin PR 2 planning answers" `f2bddda` and this plan's WIP commit; 2026-10-02): backend `1357 passed, 16 skipped`; frontend `660 passed` in 83 files; typecheck and lint clean; Alembic head `0005_services_extras` (5 revision files); 4 runbook owner markers. `require_admin` (`api/deps.py`) guards `PATCH /rubric` today and raises the role 403 "Only church admins can do this." (no `details.reason`, so the frontend's `handleAuthErrors` does not treat it as a lost church). `repos.churches._merge_settings` shallow-merges a patch into `churches.settings` under `_lock_live_church` (`SELECT … FOR UPDATE`); `set_church_translation` and `set_church_prompts` use it. `build_printed` already reads `churches.get_church` (name and settings) in its one short session. No code writes `churches.settings` whole.
- Every task's code was written and run by the planner in a throwaway worktree of `f2bddda`, and the plan's directives were then replayed onto a fresh worktree of the branch head (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -3`; the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes (T3), so T3 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand.
- No new package, no new variable, no migration.
- Branch `claude/slice-2-plan-4q33le`, at `4ed23fd` plus this plan's commits (`WIP plan: printed bulletin PR 2a (bulletin settings)`, `Plan: printed bulletin PR 2a (bulletin settings)`, and any later plan commit), then T1-T7. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1357 → 1385 passed, 16 → 16 skipped; frontend 660 → 672 in 83 → 85 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 15 and has no em dashes; existing copy keeps its own punctuation.
- No church id, email address, token, database URL or real person's name, address, phone or email in any doc, commit, test or record. The tests use invented details only: "Example Church", "100 Example Street", "Springfield, ST 00000", "(555) 010-0100", `office@example.com`, `example.com`, "Rev. Alex Example", "Sam Sample", "Jordan Doe". None of the owner's sample bulletin's content enters the repo.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.

### How the file directives below read
As in the PR 1 plan: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted.

### Baselines and counts
- Starting baselines: backend **1357 passed, 16 skipped**; frontend **660 passed in 83 files**, typecheck and lint clean; Alembic head **`0005_services_extras`** (5 revision files; no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new `it(`.

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +8 (`test_bulletin_settings.py`, one test in six cases) | 1365 passed, 16 skipped | 0 | 660 in 83 |
  | T2 | +3 (`test_printed_bulletin.py` 2; `test_printed_render.py` 1; `test_api_printed.py` edited) | 1368 passed, 16 skipped | 0 | 660 in 83 |
  | T3 | +17 (`test_api_bulletin_settings.py` 15, one test in eight cases; `test_api_printed.py` 2; `test_no_streamlit_in_core.py`, `test_church_settings.py` edited) | 1385 passed, 16 skipped | 0 | 660 in 83 |
  | T4 | 0 | 1385 passed, 16 skipped | +5 (`bulletin-settings.test.ts` 4, `church.test.ts` 1; `keys.test.ts` edited) | 665 in 84 |
  | T5 | 0 | 1385 passed, 16 skipped | +6 (`bulletin-settings-page.test.tsx`) | 671 in 85 |
  | T6 | 0 | 1385 passed, 16 skipped | +1 (`review-send-step.test.tsx`; `builder-shell.test.tsx`, `liturgy-step.test.tsx` edited) | 672 in 85 |
  | T7 | 0 (no test edited: the new items sit under the existing "## Printed bulletin") | 1385 passed, 16 skipped | 0 | 672 in 85 |
  | Build review fixes | +10 (`test_bulletin_settings.py` 1; `test_api_bulletin_settings.py` 4, one test in three cases; `test_printed_render.py` 4, one test in three cases; `test_printed_bulletin.py` 1; `test_api_printed.py` edited) | 1395 passed, 16 skipped | +3 (`bulletin-settings-page.test.tsx`) | 675 in 85 |

- CI `backend-postgres` goes from `16 passed, 1357 deselected` to `16 passed, 1395 deselected` (no new Postgres test; clarification 6 and "Risks").

### Layering and code rules (carried)
- `bulletin_settings`, `printed_bulletin` and `usecases/church_bulletin.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains `bulletin_settings` and `usecases.church_bulletin`, T3); the routes are plain `def` with no SQL and no try/except (F §2.2 rule 1); the write goes through `repos.churches` (no SQL in the usecase).
- Logs carry ids, never a setting's text (F §2.5). This PR adds no log line; `documents.printed …` is unchanged.
- Pages and components never call `apiFetch`: `lib/queries/bulletin-settings.ts` uses `useApi()` (F §4.5).
- Touch targets 44 px below `md`; text wraps at 375 px; no raw HTML (F §4.8); inputs `text-base md:text-sm` (the kit's `Input` and `Textarea` already are).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** (branch `streamlit-frozen`) is frozen and retired for real use; merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **The spec's decisions** stand as written in S, with the PR 2 planning answers below winning where S's earlier text differs (clarification 5).
5. **Layout B** and the PR 1 plan's twelve answers stand (PR 1 is merged as PR #45 and recorded).

### PR 2 planning answers (Beau, 2026-10-02, "all recommended"; binding)
1. **PR 2 splits in two.** **PR 2a, Bulletin settings** (this plan): the panel and `GET`/`PUT /church/bulletin-settings` for the church details, the standing worship leader, liturgist and organist, the service time, the stand note, the starred elements and the Gloria Patri words, printed at once; no migration, no draft change. **PR 2b, the Bulletin step:** prelude and postlude, the announcements, pasted reading text, carry forward, the draft v3 and migration `0006_services_bulletin`. Order: 2a, 2b, then PR 3 (cover picture).
2. **Admins only** change the Bulletin settings; every member's printed bulletin uses them.
3. **A blank field prints nothing** (no line, no [placeholder]); the Printed bulletin card lists what is still empty ("Not filled in: ...") so it is caught before printing. In 2a this covers the standing settings; 2b adds the weekly fields.
4. **Announcements** (2b): ushers and counters, deacon of the week, coffee hour, activities, prayers and concerns, collection items, plus one "Other announcements" box.
5. **Carry forward with a check** (2b).
6. **The Bulletin step is optional** (2b): it never blocks Review, the Word copies or the printed bulletin.
7. **Who leads** (2b's step): the three people at the top, from settings, changeable for this week; a part's leader behind "Change who leads a part". 2a provides the standing people and each part's standing role.
8. **Migration 0006** (2b) follows 0005's routine.

**Later, out of scope:** PR 2b (the Bulletin step, the weekly fields, `services.bulletin` with migration `0006_services_bulletin`, carry forward, pasted reading text, the draft v3), PR 3 (the cover picture), 6a (moving this panel into Settings), Voices of the Church.

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended).

1. **[owner-visible] What 2a ships** (planning answer 1). The standing settings (`bulletin_settings`), `GET`/`PUT /church/bulletin-settings`, the settings printed in the PDF and the Word version, the **Bulletin settings** page, and the Printed bulletin card's new lines. Not here: the Bulletin step, any weekly field, the draft's `bulletin`, `services.bulletin`, a migration, carry forward, pasted reading text, the cover picture. The Word documents card (the pastor's and bulletin copies) does not change and does not use the settings.
2. **[owner-visible] Where the panel lives until 6a** (S "The Bulletin step and the settings panel"; answer 8). A page of its own, `/bulletin-settings`, inside the church layout (the header, the church switcher and the nav stay), reached from the **Bulletin settings** button on the Printed bulletin card; the page has **Back to Review & send**. It is not in the main nav: 6a adds "Settings" and moves this page there without changing the storage. In 2b the Bulletin step links to it too (S). A page rather than a dialog: 21 parts with a leader and a star each, two long texts and eleven fields do not fit a dialog on a phone, and a page keeps its address for the Back button.
3. **[owner-visible] Who sees what** (planning answer 2; 6a's pattern). Any member can open the page and read every field. Owners and admins (`owner`, `admin`) edit and see **Save settings**; a member sees "Only admins can edit the bulletin settings. You can read them below." (6a's verb) above a plain read-only summary: each field's value as text ("Not filled in" for a blank one), and each part as a line such as "Sermon: Worship leader" or "Opening hymn: No one, congregation stands"; no fields, selects, switches or Save (plan review: 21 greyed-out rows read badly on a phone). The server enforces it (`require_admin`; a member's `PUT` is the role 403 "Only church admins can do this.", which the page would toast if it ever happened). The card's button shows for everyone.
4. **[owner-visible] The fields and how each prints** (answer 2; S "What prints where", "Data model"):
   - **Address** (up to 3 lines, each up to 60 characters): one cover line each, under the picture's box, in order. The form is one text box, a line per line; blank lines are dropped.
   - **Phone** (40), **Email** (100), **Website** (100): one cover line each, as typed. Nothing checks their form (they are printed, never used to send). On a phone the fields bring up the phone, email and web keyboards (`inputMode`; not `type="email"` or `type="url"`, which would make the browser refuse a website typed as "example.com"), with the browser's autofill off (they are the church's details, not the user's).
   - **Facebook name** (60): the cover line "FB: {name}", as the sample.
   - **The cover's limits** (plan review): 60, 100, 100 and 60 keep the contact lines short enough for the cover page; even at every limit, with a church name of two lines, the PDF shrinks the contact lines to fit (clarification 12), so the order of worship always starts on page 1.
   - **One line each:** every text but the Gloria Patri words prints on one line, so `PUT` refuses a line break, a tab or any other control character in it (a 422 naming the field); the address's lines are split by the form before sending.
   - **Service time** (40, free text such as "10:30 a.m."): right-aligned on the date line under the header, as the sample.
   - **Worship leader**, **Liturgist**, **Organist** (100 each): the header lines "{name}, Worship Leader", "{name}, Liturgist", "{name}, Organist", in that order; and the name on the right of each part that role leads.
   - **Each part** (the 21 parts the printed order of worship can show, clarification 13): who leads it (No one, Worship leader, Liturgist or Organist) and whether the congregation stands for it (the star before its label).
   - **Stand note** (200): printed at the end of the service after a star, "*{note}", and only when at least one part printed this week carries the star (plan review: no orphan note when nothing is starred, or when every starred part is left out this week). The star is not typed: a typed leading "*" is dropped when saved.
   - **Gloria Patri words** (1000): printed in bold italics under "SUNG RESPONSE: “Gloria Patri”".
5. **[owner-visible] A blank field prints nothing, and the defaults** (planning answer 3). A blank address, phone, email, website, Facebook name, service time or person prints nothing at all: no line, no "FB:", no "{blank}, Organist", no name on the right. A blank stand note leaves the closing note out; blank Gloria Patri words leave the words out (the "SUNG RESPONSE: “Gloria Patri”" line stays: it is part of the order of worship). Before anyone saves, the settings read as the defaults: every detail, person and the time **blank**, so they print nothing from the day this merges (PR 1's "[Street address]", "[Worship leader]", "[Service time]" and the like are gone) and the card lists them; the parts' leaders and stars, the stand note "Congregation stands if able" and the traditional Gloria Patri words start at PR 1's values (the owner's sample), so a church that never opens the page keeps today's stars, roles and words. **Spec note:** S "Data model" said "a missing or malformed value is the placeholder"; that was written before planning answer 3, which is later and binding, so a missing value is the default above and never a [placeholder]. T7 amends that sentence in S.
6. **Storage and concurrency** (S "Data model"; F §1.7). The settings are one object under `churches.settings["bulletin"]`, in the shape `GET` answers (clarification 7). `PUT` stores the whole object (it is the whole form) through `repos.churches.set_bulletin_settings`, which calls `_merge_settings(church_id, {"bulletin": value})`: one transaction that locks the church row (`SELECT … FOR UPDATE`), reads the settings JSON from the locked row, replaces only the `"bulletin"` key and writes it back, so `bible_translation`, `default_hymnal`, `default_benediction`, `rubric`, `liturgy_prompts` and anything else stored there are never touched, and a concurrent translation or rubric write waits rather than being lost. **[owner-visible] Two admins saving the bulletin settings at once: the later save wins** (no `If-Match`). Why: one small admin-only form edited a few times a year; the settings JSON has no version column to compare (adding one is a migration, which answer 1 rules out), and a stamp kept inside the JSON would need a conflict dialog for a case that is very unlikely in a church with one or two admins; the page shows what is stored after each save, and it follows 6a's client-side rule (clarification 10): it opens on a fresh fetch, and newer server data updates every field the admin has not edited, so a save never sends back an older value the admin did not touch. The role is checked by `require_admin` before the write, not again under the lock, exactly as `PATCH /rubric` does today; 6a moves both writes under `lock_and_read_actor`. SQLite ignores `FOR UPDATE` (F §1.7's known gap); nothing here needs a Postgres-only test, because the write is `_merge_settings`, already used in production.
7. **The API.** `GET /church/bulletin-settings` (`require_church`; any member) answers `BulletinSettings`: `{address_lines: string[] (≤ 3, each ≤ 60), phone, email, website, facebook, service_time, worship_leader, liturgist, organist, stand_note, gloria_patri_words: string (limits in clarification 4), starred: ElementKey[], leaders: {ElementKey: "worship_leader" | "liturgist" | "organist"}}`. `PUT` (`require_admin`) takes the same object, `extra="forbid"`, **every field required** (it replaces the whole object), each text trimmed and within its limit, every text but `gloria_patri_words` free of control characters, C1 controls (U+0085 among them) and U+2028/U+2029 (one printed line: no line break or tab), `starred` and `leaders` limited to the 21 keys and the 3 roles; a bad body is the usual 422 `invalid_request` with `fields` (for example `phone`, `address_lines`, `address_lines.0`, `starred.0`, `leaders.sermon`, `leaders.anthem.[key]`, `extra`) and stores nothing. Before storing, every text goes through `archive._xml_safe` (as a service's texts do, so the Word version can always hold it) and then `bulletin_settings.read` (together `church_bulletin.read_settings`, which `GET` and the printed bulletin use too, so a value written by any other path is made Word-safe as well), which trims, drops blank address lines, drops a leading "*" from the stand note, removes duplicate stars, and orders `starred` and `leaders` as the printed order; `PUT` answers what is then stored (a re-read). No `Idempotency-Key` (the same body stores the same value) and no rate-limit bucket (F §1.6, §1.8: a small local write). `GET` reads tolerantly: a missing settings object, a missing key, a value of the wrong type or an unknown key or role falls back field by field to the default (clarification 5), every text but `gloria_patri_words` reads as one line (each run of those characters becomes one space; build review fix I1), and a text longer than its limit is cut to it, so `GET` always answers something `PUT` would accept. A church gone between the guard and the read is the guard's 403 (`no_church_access`). OpenAPI gains the two operations and `BulletinSettings`.
8. **[owner-visible] The weekly fields keep PR 1's placeholders until 2b.** The prelude and postlude ("PRELUDE: ‘[Prelude title]’" with "- [Composer]", and the postlude's), the cover picture's box ("[Cover picture]"), the announcements page ("Ushers/Counters: [Names]" and the rest), "[Sermon title]" for a blank sermon title and "[Reading text unavailable]" all print as in PR 1. Planning answer 3 makes a blank weekly field print nothing too, but only together with the Bulletin step that fills them (2b): removing the music and the announcements now would leave a bulletin with no prelude line and an announcements page of bare headings and no way to fill them. The prelude's and postlude's leader is now the organist's name from the settings (or nothing). The card says "For now, the music and the announcements print as [placeholders]."
9. **[owner-visible] The Printed bulletin card** (planning answer 3). Its heading, summary, two downloads and their lines, gates, toasts and save tip are unchanged. The PR 1 line "For now, the church's details, the people who lead, the music and the announcements print as [placeholders]." becomes "For now, the music and the announcements print as [placeholders]."; under it, still above the download buttons (plan review: on a phone the list must be read before **Download printed bulletin** is tapped), "The church's details, the people who lead and the service time come from the bulletin settings.", then, when any is blank, "Not filled in: {list}." (for example "Not filled in: phone, organist."); under the downloads (and the save tip) a **Bulletin settings** button (outlined, full width on a phone, 44 px) to `/bulletin-settings`. The list names, in the page's order, each blank one of: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist, stand note, Gloria Patri words. Nothing about the settings ever turns a download off: while they load or if they fail, the card shows the sentence and the button, and no list.
10. **[owner-visible] The page** (F §4.8; 6a's rules for settings forms). `PageHeader` "Bulletin settings" with "What every printed bulletin uses. A field left blank is left off the bulletin." and **Back to Review & send** (outlined, 44 px). For admins, five groups, each a fieldset with its legend: **Church details** (Address with "Up to 3 lines, as printed on the cover.", Phone, Email, Website, Facebook name with "Printed as FB: and the name."); **Service** (Service time with "Printed across from the date, for example 10:30 a.m."); **Who leads** (Worship leader, Liturgist, Organist); **Each part** ("Who leads each part, and the parts the congregation stands for (printed with a star)." then, per part, its name, a select named "{part}: led by" with No one, Worship leader, Liturgist, Organist, and a switch "Stands" named "{part}: congregation stands"); **Printed words** (Stand note with "Printed at the end of the service, after a star.", Gloria Patri words). Then **Save settings** (filled, full width on a phone, "Saving…" while pending). Members see the summary of clarification 3 under the same five headings. A load shows skeletons; a failed load the usual error with **Retry**. Each text field has its limit as `maxLength`.
    - **Fresh on opening** (plan review): the page fetches the settings again when it opens (`useBulletinSettings({ fresh: true })`: `refetchOnMount: "always"`), even when the card cached them minutes ago, and shows the form only once that fetch is back (skeletons until then), so the form never starts from an older value. Once shown, a failed background refetch keeps the form.
    - **Rebase** (6a's rule, `rebaseForm`): the form keeps a baseline (the last server value) and the current edits. When newer server data arrives (a refetch on window focus, or this page's own save), each value the admin has not touched (a text, a part's leader, a part's star; current equals the baseline) takes the new server value, each touched one keeps the edit, and the baseline becomes the new value. After a save, the fields as sent take what was stored (trimmed, the stand note's star dropped); a field changed while "Saving…" showed keeps what was typed.
    - **Leave guard** (6a's rule; the app has no app-wide guard yet): while the form has unsaved edits, closing or reloading the tab shows the browser's own warning (`beforeunload`), and **Back to Review & send** asks "Discard unsaved changes?" ("Your changes on this page haven't been saved."; **Discard changes**, **Keep editing**). The header links, the nav and the church switcher do not ask yet: 6a's `useLeaveGuard` adds that for every settings page.
    - **Errors** (the app's field-error pattern, announced): the address is checked on Save ("Use up to 3 lines of up to 60 characters each." under it, in the error colour, `role="alert"`, the field `aria-invalid`, described by it, and focused; nothing sent). A 422 that names fields (`fields`, for example a line break pasted into the phone) shows the server's short message ("Not a valid value.", "Too long (max 40 characters).") the same way under each named field and focuses the first; the toast shows the server's message as for any failed save. Editing a field clears its error.
    - Success toasts "Bulletin settings saved" (the result is not otherwise visible) and the form shows what was stored; a failure toasts the server's message (none after a 401 or a lost church).
11. **The leader select's "No one"** is a real choice (the part prints no leader), not a placeholder item, so F §4.9 item 3's "never add a sentinel item" does not apply; it maps to the part being absent from `leaders`.
12. **Reading the settings to print, and the cover's fit.** `build_printed` already reads `churches.get_church` (the name and the settings) in its one short session; it passes `church_bulletin.read_settings(church["settings"])` to `PrintedService` (`bulletin_settings.read` of the stored texts made Word-safe with `archive._xml_safe`: a value written by any other path, the frozen Streamlit merge, ops SQL or a later writer, can never make the Word version fail), so a download costs no extra query. The Word version (`printed_docx`) needs no change: it renders `printed_bulletin`'s lines, and an empty cover contact list or a date line with no time already renders (a line with no `right` prints without the leader's column). **The PDF's cover** (`printed_pdf._story`) is a fixed stack in a 540 pt page: the title, the picture's 300 pt box and 30 pt of space leave about 158 pt for the contact lines (about 106 pt under a church name of two lines), which typical details fit (six short lines take 90 pt) but the longest values the limits allow do not; so the contact lines go in a `KeepInFrame(..., mode="shrink")` sized to the room left, and shrink only when they would not fit (T2's `test_the_longest_details_still_fit_the_cover`: every field at its limit and a church name of two lines still give side 1 = cover | page 1). **The Word cover** cannot shrink the same way; its picture box is shorter (about 150 pt), so at every limit its cover needs about 380 of its 540 pt and stays one page. That is an estimate: python-docx has no layout engine and LibreOffice Writer is not installed here, so no test can check Word's page breaks; the owner's phone check opens the Word version (T9 Step 3). A character the PDF's standard fonts cannot print shows as "?" (PR 1's `to_pdf_text`), as for any text.
13. **The parts and their names.** The 21 keys are PR 1's element keys, in the printed order: `prelude`, `welcome`, `call_to_worship`, `opening_prayer`, `first_hymn`, `prayer_of_confession`, `assurance`, `gloria_patri`, `prayer_for_illumination`, `ot_reading`, `nt_reading`, `sermon`, `affirmation_of_faith`, `second_hymn`, `prayers_of_the_people`, `offering`, `doxology`, `offertory_prayer`, `third_hymn`, `benediction`, `postlude`. The page names them Prelude, Welcome and Announcements, Call to Worship, Opening Prayer, Opening hymn, Prayer of Confession, Assurance of Pardon, Gloria Patri, Prayer for Illumination, First Reading, New Testament Reading, Sermon, Affirmation of Faith, Response hymn, Prayers of the People, Offering, Doxology, Offertory Prayer, Closing hymn, Benediction, Postlude (the hymns as the Hymns step names its slots). A custom element and the communion liturgy's headings have no key: no star, no leader (as in PR 1).
14. **Isolation and access.** Both routes are church-scoped (`test_route_guards.py` passes unchanged: `require_admin` depends on `require_church`); a non-member and a member of another church get the `no_church_access` 403 for both (T3's isolation test).
15. **[owner-visible] Every new user-facing string** (no em dashes). On the card: "The church's details, the people who lead and the service time come from the bulletin settings."; "For now, the music and the announcements print as [placeholders]." (replacing PR 1's line); "Not filled in: {list}." with the labels "address", "phone", "email", "website", "Facebook name", "service time", "worship leader", "liturgist", "organist", "stand note", "Gloria Patri words"; "Bulletin settings" (the button). On the page: "Bulletin settings" (the heading); "What every printed bulletin uses. A field left blank is left off the bulletin."; "Back to Review & send"; "Only admins can edit the bulletin settings. You can read them below."; the legends and headings "Church details", "Service", "Who leads", "Each part", "Printed words"; the labels "Address", "Phone", "Email", "Website", "Facebook name", "Service time", "Worship leader", "Liturgist", "Organist", "Stand note", "Gloria Patri words"; the help lines "Up to 3 lines, as printed on the cover.", "Printed as FB: and the name.", "Printed across from the date, for example 10:30 a.m.", "Printed at the end of the service, after a star.", "Who leads each part, and the parts the congregation stands for (printed with a star)."; the 21 part names (clarification 13); "No one", "Worship leader", "Liturgist", "Organist" (the select); "Stands"; for screen readers "{part}: led by" and "{part}: congregation stands"; "Use up to 3 lines of up to 60 characters each."; "Save settings"; "Bulletin settings saved" (toast); in the member's summary "Not filled in" (a blank field) and "{part}: {who leads}" with ", congregation stands" for a starred part; the leave guard's "Discard unsaved changes?", "Your changes on this page haven't been saved.", "Discard changes" and "Keep editing" (6a's words). Reused as they are: "Saving…", the skeleton's "Loading", the error state and its "Retry", the existing error toasts, the server's 422 field messages ("Not a valid value.", "Too long (max {n} characters)."). In the files: the header lines "{name}, Worship Leader", "{name}, Liturgist", "{name}, Organist"; "FB: {name}"; "*{stand note}"; the default stand note "Congregation stands if able" (PR 1's text without the star, which is printed). From the server: "Only church admins can do this." (`require_admin`'s, unchanged).
16. **Docs.** T7 appends "### Printed bulletin PR 2a: bulletin settings" with items 7-15 at the end of `docs/manual-verification.md`, inside the existing "## Printed bulletin" section (PR 1's text says "PR 2 and PR 3 add their own items here"). A `###` heading, so `test_slice1_docs.py`'s pin of the last eight `##` headings does not move and no test changes. T7 also amends PR 1's item 2 (it said the names print as [placeholders]) and S's "Data model" sentence (clarification 5). The runbook record is T9's (`### Printed bulletin PR 2a record` before `## Backups`, as PR 1's).

### Risks
- **The bulletin loses PR 1's [placeholders] for the standing details the moment this merges** (clarification 5). Until an admin saves the settings, the cover has no contact lines and the header no people. That is answer 3's intent, and the card says what is not filled in; T9's first phone step fills them in.
- **Two admins saving at once:** the later save wins (clarification 6). Very unlikely; the loser sees their save toast and, on reload, the other admin's values.
- **A demoted admin's save in flight** passes `require_admin` and writes milliseconds later; the role is not re-read under the lock (as `PATCH /rubric`). 6a closes both with `lock_and_read_actor`.
- **SQLite ignores `FOR UPDATE`.** The unit tests cannot show the lock itself; the write is the existing `_merge_settings`, which `backend-postgres` already exercises through the translation and prompt writes in production use, and T3 adds `set_bulletin_settings` to `test_church_settings.py::test_settings_writes_lock_the_church_row`, which checks (compiled for Postgres) that each settings write loads the church row `FOR UPDATE` (a guard if the function is ever rewritten without `_merge_settings`). No new Postgres test.
- **Characters outside Windows-1252** in a name or an address print as "?" in the PDF (PR 1's fonts); the Word version prints them. The phone check looks at the cover and header.
- **Long values:** the cover's limits (address lines 60, email and website 100, Facebook name 60) keep the contact lines short, and the PDF shrinks them when even those would overflow the cover (clarification 12; T2's render test at every limit), so the order of worship always starts on page 1. The Word cover is not shrunk; by estimate it fits at every limit, and no test can check Word's page breaks (clarification 12). A name may be 100 characters: in the header it wraps, and on a part it takes the 120 pt leader column (about 21 characters a line in Times 11), so a very long name makes tall leader cells on each part it leads and can add a page; accepted (real names are short, and the limit caps it).
- **Frozen Streamlit** never reads or writes `"bulletin"`; its settings writes go through the same locked merge (F §1.7 amendment), which keeps this key.
- **The leave guard is partial until 6a:** unsaved edits are guarded on a reload or close of the tab and on **Back to Review & send**, not on the header links, the nav or the church switcher (no app-wide guard exists yet; 6a's `useLeaveGuard` adds it). Leaving that way loses the edits without a question.
- **The stored settings JSON is assumed to be an object:** `_merge_settings` raises `TypeError` (a 500) if `churches.settings` were ever not an object. Pre-existing and shared with the translation and prompts writes, so not 2a's to fix; listed under "Follow-ups".

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/bulletin_settings.py` (+ `backend/tests/test_bulletin_settings.py`) | `BulletinSettings` (`leader`, `to_json`), `read`, `ELEMENT_KEYS`, `ROLES`, `MAX_LENGTH`, `MAX_ADDRESS_LINES`, the defaults, `GLORIA_PATRI` (moved from `printed_bulletin`) | T1 |
| `backend/usecases/church_bulletin.py`, `backend/api/routes/bulletin_settings.py` (+ `backend/tests/test_api_bulletin_settings.py`) | `read_settings`, `get_bulletin_settings`, `save_bulletin_settings`; the `BulletinSettings` model (one-line texts), `GET` and `PUT /church/bulletin-settings` | T3 |
| `frontend/src/lib/bulletin-settings.ts` (+ `.test.ts`), `frontend/src/lib/queries/bulletin-settings.ts` | `ELEMENTS`, `ROLES`, `MAX_LENGTH`, the form mapping, `addressError`, `rebaseForm`, `isDirty`, `formErrors`, `notFilledIn`, `notFilledInLine`; `useBulletinSettings` (with `{ fresh: true }` for the page), `useSaveBulletinSettings` | T4 |
| `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx` (+ `.test.tsx`), `frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx` | the page (the admin's form with the fresh fetch, the rebase, the leave guard and the field errors; the member's summary) and its route | T5 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/printed_bulletin.py` | `PrintedService.settings`; stars, leaders, header, time, contact lines, stand note (only under a printed star) and Gloria Patri words from it; PR 1's standing placeholders and constants removed | T2 |
| `backend/printed_pdf.py` | the cover's contact lines shrink to the room left on the cover (`KeepInFrame`) | T2 |
| `backend/tests/test_printed_bulletin.py`, `backend/tests/test_printed_render.py`, `backend/tests/test_api_printed.py` | the filled-in `SETTINGS`; names for placeholders; two new content tests and one render test at every limit; (T3) the stored settings print, and a stored control character still prints in Word | T2, T3 |
| `backend/repos/churches.py`, `backend/api/main.py`, `backend/usecases/documents.py`, `backend/tests/test_no_streamlit_in_core.py`, `backend/tests/test_church_settings.py` | `set_bulletin_settings`; the router; the settings (Word-safe) passed to `PrintedService`; two modules; the new write in the row-lock test | T3 |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated | T3 |
| `frontend/src/lib/api/types.ts`, `frontend/src/lib/queries/keys.ts` (+ `keys.test.ts`), `frontend/src/lib/church.ts` (+ `church.test.ts`), `frontend/src/test/fixtures/index.ts` | `BulletinSettings`; `keys.bulletinSettings`; `isAdmin`; `bulletinSettings()`, `filledBulletinSettings()`, `GLORIA_PATRI` | T4 |
| `frontend/src/components/builder/review/printed-card.tsx` (+ `review-send-step.test.tsx`), `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.test.tsx` | the settings sentence and "Not filled in" above the downloads, the button below them, and the new placeholder line; the fake route in the three tests that render Review | T6 |
| `docs/manual-verification.md`, `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md` | "### Printed bulletin PR 2a: bulletin settings", PR 1's item 2 amended; S's "Data model" sentence (clarification 5) | T7 |
| `docs/ops-runbook.md` | "### Printed bulletin PR 2a record" (the records PR, after the merge) | T9 |

**Counts in the PR:** 38 paths: 12 created (this plan and the eleven new code and test files above), 26 modified (the 22 code, test and API paths above, `printed_docx.py` (the build review's centered cover box), `docs/manual-verification.md`, the spec (its PR 2 planning answers, `f2bddda`, and T7's sentence) and `docs/ops-runbook.md` (the PR 1 record `350f9a5`), which ride along until merged). **Untouched:** migrations, `db/models.py`, `api/schemas.py`, `api/deps.py`, `service_output.py`, the draft schema, `documents-card.tsx`, `app-nav.tsx`, `app.py`, Streamlit.

**Task order and review batch:** T1 → T7, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T8 verifies and opens the draft PR on the owner's yes; T9 merges on the owner's yes, runs the phone check and writes the record.

---

### Task 1: The standing settings: `bulletin_settings` (answer 2; planning answer 3; S "Data model"; clarifications 4, 5, 7, 13)

**Files:**
- Create: `backend/tests/test_bulletin_settings.py`, `backend/bulletin_settings.py`

- [ ] **Step 1: Write the failing test**

**Create `backend/tests/test_bulletin_settings.py`:**

````python
"""The church's standing bulletin settings (printed bulletin spec, PR 2a;
bulletin_settings.py): the defaults, the tolerant read and the stored shape."""
import pytest

import bulletin_settings as bs

DEFAULT_JSON = {
    "address_lines": [], "phone": "", "email": "", "website": "", "facebook": "", "service_time": "",
    "worship_leader": "", "liturgist": "", "organist": "", "stand_note": "Congregation stands if able",
    "gloria_patri_words": bs.GLORIA_PATRI,
    "starred": ["first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "doxology", "third_hymn",
                "benediction"],
    "leaders": {"prelude": "organist", "welcome": "liturgist", "call_to_worship": "liturgist",
                "opening_prayer": "liturgist", "prayer_of_confession": "liturgist", "assurance": "liturgist",
                "prayer_for_illumination": "liturgist", "ot_reading": "liturgist", "nt_reading": "worship_leader",
                "sermon": "worship_leader", "prayers_of_the_people": "worship_leader",
                "offertory_prayer": "worship_leader", "postlude": "organist"},
}


@pytest.mark.parametrize("settings", [None, {}, {"bulletin": None}, {"bulletin": "x"}, {"bulletin": []}, "x"])
def test_nothing_stored_reads_the_defaults(settings):
    assert bs.read(settings) == bs.BulletinSettings()
    assert bs.read(settings).to_json() == DEFAULT_JSON


def test_a_stored_value_reads_back_clean_and_in_order():
    stored = {"bible_translation": "kjv", "bulletin": {
        "address_lines": ["  100 Example Street ", "", "Springfield, ST 00000", "Line three", "Line four"],
        "phone": " (555) 010-0100 ", "email": "office@example.com", "website": "example.com",
        "facebook": "Example Church", "service_time": "10:30 a.m.", "worship_leader": "Rev. Alex Example",
        "liturgist": "Sam Sample", "organist": "Jordan Doe", "stand_note": " **Please stand if able ",
        "gloria_patri_words": "Glory be.", "starred": ["sermon", "prelude", "nope", "prelude"],
        "leaders": {"sermon": "organist", "prelude": "liturgist", "nope": "organist", "welcome": "pastor"},
    }}
    s = bs.read(stored)
    assert s.address_lines == ("100 Example Street", "Springfield, ST 00000", "Line three")
    assert (s.phone, s.stand_note, s.starred) == ("(555) 010-0100", "Please stand if able",
                                                 frozenset({"prelude", "sermon"}))
    assert s.to_json()["starred"] == ["prelude", "sermon"]
    assert s.to_json()["leaders"] == {"prelude": "liturgist", "sermon": "organist"}
    assert (s.leader("sermon"), s.leader("prelude"), s.leader("welcome")) == ("Jordan Doe", "Sam Sample", "")
    assert bs.read({"bulletin": s.to_json()}) == s


def test_a_field_of_the_wrong_type_is_its_default_and_a_long_text_is_cut():
    s = bs.read({"bulletin": {"phone": 5, "address_lines": "100 Example Street", "starred": "sermon",
                              "leaders": ["sermon"], "stand_note": None, "organist": "x" * 150,
                              "gloria_patri_words": ""}})
    assert s == bs.BulletinSettings(organist="x" * 100, gloria_patri_words="")
    assert s.leader("prelude") == "x" * 100 and s.leader("sermon") == ""
````

- [ ] **Step 2: See it fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_bulletin_settings.py 2>&1 | tail -3`
**Expected** (`bulletin_settings` does not exist yet: `ModuleNotFoundError` above these lines):
```
ERROR backend/tests/test_bulletin_settings.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: Write `bulletin_settings`**

**Create `backend/bulletin_settings.py`:**

````python
"""The church's standing bulletin settings (printed bulletin spec, PR 2a):
what every week's printed bulletin prints the same way, stored in
churches.settings["bulletin"] (no column, no migration).

- BulletinSettings: the church's contact lines, the service time, the three
  people who lead (worship leader, liturgist, organist), which elements each
  of them leads, which elements carry the stand star, the stand note and the
  Gloria Patri words.
- read(settings): the stored value read tolerantly. A missing settings object,
  a missing "bulletin" key or a field of the wrong type is that field's
  default; unknown element keys and roles are dropped, and a text longer than
  its limit is cut to it (so GET always answers within PUT's limits). The defaults are PR 1's
  (the owner's sample): no contact lines, no names and no time (a blank field
  prints nothing, PR 2 planning answer 3), the sample's stars and leader roles,
  "Congregation stands if able" and the traditional Gloria Patri.
- to_json: the stored shape (what GET and PUT /church/bulletin-settings answer).
  PUT stores read({"bulletin": body}).to_json(), so the stored value is
  always clean: trimmed, blank address lines dropped, the stand note without
  its star, the starred keys and the leaders in ELEMENT_KEYS order.
Pure: no database, FastAPI or rendering here.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["worship_leader", "liturgist", "organist"]
ROLES: tuple[Role, ...] = ("worship_leader", "liturgist", "organist")

# Every element the printed order of worship can star or give a leader, in its order.
ELEMENT_KEYS = (
    "prelude", "welcome", "call_to_worship", "opening_prayer", "first_hymn", "prayer_of_confession", "assurance",
    "gloria_patri", "prayer_for_illumination", "ot_reading", "nt_reading", "sermon", "affirmation_of_faith",
    "second_hymn", "prayers_of_the_people", "offering", "doxology", "offertory_prayer", "third_hymn",
    "benediction", "postlude",
)

# The longest value each field takes (PUT /church/bulletin-settings refuses longer). The cover's
# limits keep its contact lines short enough for the cover page (printed_pdf also shrinks them to fit).
MAX_ADDRESS_LINES = 3
MAX_LENGTH = {"address_line": 60, "phone": 40, "email": 100, "website": 100, "facebook": 60,
              "service_time": 40, "person": 100, "stand_note": 200, "gloria_patri_words": 1000}

# The owner's sample (PR 1's defaults).
DEFAULT_LEADERS: dict[str, Role] = {
    "prelude": "organist", "welcome": "liturgist", "call_to_worship": "liturgist", "opening_prayer": "liturgist",
    "prayer_of_confession": "liturgist", "assurance": "liturgist", "prayer_for_illumination": "liturgist",
    "ot_reading": "liturgist", "nt_reading": "worship_leader", "sermon": "worship_leader",
    "prayers_of_the_people": "worship_leader", "offertory_prayer": "worship_leader", "postlude": "organist",
}
DEFAULT_STARRED = frozenset({"first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "doxology",
                             "third_hymn", "benediction"})
DEFAULT_STAND_NOTE = "Congregation stands if able"
GLORIA_PATRI = ("Glory be to the Father, and to the Son, and to the Holy Ghost; as it was in the "
                "beginning, is now, and ever shall be, world without end. Amen, amen.")

_LIMIT = {"worship_leader": "person", "liturgist": "person", "organist": "person"}
_TEXT_FIELDS = ("phone", "email", "website", "facebook", "service_time", "worship_leader", "liturgist", "organist",
                "stand_note", "gloria_patri_words")


@dataclass(frozen=True)
class BulletinSettings:
    address_lines: tuple[str, ...] = ()
    phone: str = ""
    email: str = ""
    website: str = ""
    facebook: str = ""
    service_time: str = ""
    worship_leader: str = ""
    liturgist: str = ""
    organist: str = ""
    stand_note: str = DEFAULT_STAND_NOTE          # printed after a star: "*Congregation stands if able"
    starred: frozenset[str] = DEFAULT_STARRED
    gloria_patri_words: str = GLORIA_PATRI
    leaders: Mapping[str, Role] = field(default_factory=lambda: dict(DEFAULT_LEADERS))

    def leader(self, key: str) -> str:
        """The name of the person who leads element `key`; "" when no role or no name."""
        role = self.leaders.get(key)
        return getattr(self, role) if role in ROLES else ""

    def to_json(self) -> dict:
        """The stored shape; lists and the leaders in ELEMENT_KEYS order."""
        return {
            "address_lines": list(self.address_lines),
            **{name: getattr(self, name) for name in _TEXT_FIELDS},
            "starred": [key for key in ELEMENT_KEYS if key in self.starred],
            "leaders": {key: self.leaders[key] for key in ELEMENT_KEYS if key in self.leaders},
        }


def read(settings: object) -> BulletinSettings:
    """churches.settings["bulletin"], read tolerantly (see the module docstring)."""
    stored = settings.get("bulletin") if isinstance(settings, Mapping) else None
    if not isinstance(stored, Mapping):
        return BulletinSettings()
    values: dict = {}
    for name in _TEXT_FIELDS:
        value = stored.get(name)
        if isinstance(value, str):
            value = value.strip().lstrip("*").strip() if name == "stand_note" else value.strip()   # the star is printed
            values[name] = value[:MAX_LENGTH[_LIMIT.get(name, name)]]
    lines = stored.get("address_lines")
    if isinstance(lines, list):
        values["address_lines"] = tuple(line.strip()[:MAX_LENGTH["address_line"]] for line in lines
                                        if isinstance(line, str) and line.strip())[:MAX_ADDRESS_LINES]
    starred = stored.get("starred")
    if isinstance(starred, list):
        values["starred"] = frozenset(key for key in starred if key in ELEMENT_KEYS)
    leaders = stored.get("leaders")
    if isinstance(leaders, Mapping):
        values["leaders"] = {key: role for key, role in leaders.items() if key in ELEMENT_KEYS and role in ROLES}
    return BulletinSettings(**values)
````

- [ ] **Step 4: See it pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_bulletin_settings.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:** `8 passed in <t>s`; `1365 passed, 16 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/bulletin_settings.py backend/tests/test_bulletin_settings.py
git commit -q -m "Printed bulletin PR 2a: the standing bulletin settings" -m "bulletin_settings holds the church's standing bulletin settings: the
contact lines, the service time, the three people and what each leads,
the stars, the stand note and the Gloria Patri words, read tolerantly
from churches.settings[\"bulletin\"] with PR 1's sample values as the
defaults and every detail blank until saved." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1365 passed, 16 skipped`; frontend `660 passed` in 83 files.

### Task 2: The booklet prints the settings: `printed_bulletin`, and the cover fits (planning answer 3; S "What prints where"; clarifications 4, 5, 8, 12)

**Files:**
- Modify: `backend/tests/test_printed_bulletin.py`, `backend/tests/test_printed_render.py`, `backend/tests/test_api_printed.py`, `backend/printed_bulletin.py`, `backend/printed_pdf.py`

The PR 1 tests now pass `SETTINGS` (invented names and details) and expect them where PR 1 expected `[Worship leader]` and the other standing placeholders; `test_api_printed.py`'s first test, whose church saved nothing, expects no names at all. `test_printed_render.py` imports `SETTINGS` from `test_printed_bulletin.py` (only the constant, so no test is collected twice). The stand note prints only under a printed star; a render test puts every field at its limit under a church name of two lines and checks that the order of worship still starts on page 1.

- [ ] **Step 1: Write the failing tests**

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
"""The printed bulletin's content (printed bulletin spec, PR 1;
printed_bulletin.py)."""
import datetime

import printed_bulletin as pb
````

**with:**

````python
"""The printed bulletin's content (printed bulletin spec, PR 1;
printed_bulletin.py), with the church's bulletin settings (PR 2a)."""
import datetime

import bulletin_settings as bs
import printed_bulletin as pb
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
SUNDAY = datetime.date(2026, 10, 4)
````

**with:**

````python
SUNDAY = datetime.date(2026, 10, 4)
# Invented details: a church's settings with every standing field filled in.
SETTINGS = bs.BulletinSettings(
    address_lines=("100 Example Street", "Springfield, ST 00000"), phone="(555) 010-0100",
    email="office@example.com", website="example.com", facebook="Example Church", service_time="10:30 a.m.",
    worship_leader="Rev. Alex Example", liturgist="Sam Sample", organist="Jordan Doe")
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
                nt=pb.Reading("Matthew 21:33-46", None), translation_label="World English Bible (WEB)")
````

**with:**

````python
                nt=pb.Reading("Matthew 21:33-46", None), translation_label="World English Bible (WEB)",
                settings=SETTINGS)
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
    assert texts(lines[:5]) == ["THE SERVICE FOR THE LORD’S DAY", "Example Church",
                                "[Worship leader], Worship Leader", "[Liturgist], Liturgist", "[Organist], Organist"]
    assert lines[5].right == "[Service time]"
````

**with:**

````python
    assert texts(lines[:5]) == ["THE SERVICE FOR THE LORD’S DAY", "Example Church",
                                "Rev. Alex Example, Worship Leader", "Sam Sample, Liturgist", "Jordan Doe, Organist"]
    assert lines[5].right == "10:30 a.m."
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
    assert by_text["CALL TO WORSHIP"].right == "[Liturgist]"
    assert by_text["NEW TESTAMENT READING:  Matthew 21:33-46"].right == "[Worship leader]"
    assert by_text["PRELUDE:  ‘[Prelude title]’"].right == "[Organist]"
    assert by_text["SERMON:  “Who Said?”"].right == "[Worship leader]"
````

**with:**

````python
    assert by_text["CALL TO WORSHIP"].right == "Sam Sample"
    assert by_text["NEW TESTAMENT READING:  Matthew 21:33-46"].right == "Rev. Alex Example"
    assert by_text["PRELUDE:  ‘[Prelude title]’"].right == "Jordan Doe"
    assert by_text["SERMON:  “Who Said?”"].right == "Rev. Alex Example"
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
        "Example Church", "[Cover picture]", "Matthew 21:33-46", "October 4, 2026", "[Street address]",
        "[City, State ZIP]", "[Phone]", "[Email]", "[Website]", "FB: [Facebook name]"]
````

**with:**

````python
        "Example Church", "[Cover picture]", "Matthew 21:33-46", "October 4, 2026", "100 Example Street",
        "Springfield, ST 00000", "(555) 010-0100", "office@example.com", "example.com", "FB: Example Church"]
````

**Append to `backend/tests/test_printed_bulletin.py`:**

````python


def test_a_blank_setting_prints_nothing():
    lines = pb.order_of_worship(service(settings=bs.BulletinSettings()))       # nothing saved yet
    assert texts(lines[:3]) == ["THE SERVICE FOR THE LORD’S DAY", "Example Church", "October 4, 2026"]
    assert lines[2].right == ""
    assert all(line.right == "" for line in lines)                          # roles, but no names
    assert texts(pb.cover(service(settings=bs.BulletinSettings(phone="(555) 010-0100", facebook="Example Church")))
                 )[4:] == ["(555) 010-0100", "FB: Example Church"]
    assert texts(pb.cover(service(settings=bs.BulletinSettings())))[4:] == []
    bare = texts(pb.order_of_worship(service(settings=bs.BulletinSettings(
        stand_note="", gloria_patri_words="", starred=frozenset(), leaders={}))))
    i = bare.index("SUNG RESPONSE:  “Gloria Patri”")
    assert bare[i + 1] == "PRAYER FOR ILLUMINATION"                         # no words under it
    assert not any(line.startswith("*") for line in bare)                   # no stars, no stand note
    assert bare[-1] == "ENDING"
    unstarred = texts(pb.order_of_worship(service(ot=None, settings=bs.BulletinSettings(
        starred=frozenset({"ot_reading"})))))                               # starred, but not printed this week
    assert unstarred[-1] == "ENDING" and not any(line.startswith("*") for line in unstarred)


def test_the_settings_choose_the_stars_the_leaders_and_the_words():
    settings = bs.BulletinSettings(organist="Jordan Doe", starred=frozenset({"prelude", "sermon"}),
                                   leaders={"sermon": "organist", "welcome": "liturgist"},
                                   stand_note="Please stand if able", gloria_patri_words="Glory be.")
    lines = pb.order_of_worship(service(settings=settings))
    by_text = {line.text: line for line in lines}
    assert by_text["*PRELUDE:  ‘[Prelude title]’"].right == ""               # starred; no role now
    assert by_text["*SERMON:  “Who Said?”"].right == "Jordan Doe"
    assert by_text["WELCOME AND ANNOUNCEMENTS"].right == ""                 # a role with no name
    assert "HYMN:  #409  “God Is Here!”" in by_text and "Glory be." in by_text
    assert lines[-1] == pb.Line("note", (pb.Span("*Please stand if able"),))
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
from service_output import ResolvedHymn, ResolvedService
````

**with:**

````python
from service_output import ResolvedHymn, ResolvedService
from tests.test_printed_bulletin import SETTINGS
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
                             pb.Reading("Matthew 21:23-32", VERSE * verses), "World English Bible (WEB)")
````

**with:**

````python
                             pb.Reading("Matthew 21:23-32", VERSE * verses), "World English Bible (WEB)", SETTINGS)
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
    assert pages[0].startswith("Example Church [Cover picture] Matthew 21:23-32 September 27, 2026 [Street address]")
    assert pages[0].endswith("FB: [Facebook name]")
    assert pages[1].startswith("1 THE SERVICE FOR THE LORD’S DAY Example Church [Worship leader], Worship Leader")
````

**with:**

````python
    assert pages[0].startswith("Example Church [Cover picture] Matthew 21:23-32 September 27, 2026 100 Example Street")
    assert pages[0].endswith("FB: Example Church")
    assert pages[1].startswith("1 THE SERVICE FOR THE LORD’S DAY Example Church Rev. Alex Example, Worship Leader")
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
    assert f"NEW TESTAMENT READING: Matthew 21:23-32 [Worship leader] {VERSE.strip()}" in pages[1]
````

**with:**

````python
    assert f"NEW TESTAMENT READING: Matthew 21:23-32 Rev. Alex Example {VERSE.strip()}" in pages[1]
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
                     "CALL TO WORSHIP [Liturgist]", "Leader: Lift up your hearts.",
````

**with:**

````python
                     "CALL TO WORSHIP Sam Sample", "Leader: Lift up your hearts.",
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
"NEW TESTAMENT READING: Matthew 21:23-32 [Worship leader]",
````

**with:**

````python
"NEW TESTAMENT READING: Matthew 21:23-32 Rev. Alex Example",
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
                     "POSTLUDE: ‘[Postlude title]’ [Organist]", "Go in peace. - A Friend"):
````

**with:**

````python
                     "POSTLUDE: ‘[Postlude title]’ Jordan Doe", "Go in peace. - A Friend"):
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
    for expected in ("*HYMN:  #409  “God Is Here!”", "CALL TO WORSHIP\t[Liturgist]",
                     "People: We come, ready to listen and learn.", "FIRST READING:  Psalm 25:1-9\t[Liturgist]",
````

**with:**

````python
    for expected in ("*HYMN:  #409  “God Is Here!”", "CALL TO WORSHIP\tSam Sample",
                     "People: We come, ready to listen and learn.", "FIRST READING:  Psalm 25:1-9\tSam Sample",
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
                     "FB: [Facebook name]", "Coffee Hour: [Name]"):
````

**with:**

````python
                     "FB: Example Church", "Coffee Hour: [Name]"):
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
import datetime
from io import BytesIO
````

**with:**

````python
import dataclasses
import datetime
from io import BytesIO
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
import printed_bulletin as pb
import printed_docx
````

**with:**

````python
import bulletin_settings as bs
import printed_bulletin as pb
import printed_docx
````

**Append to `backend/tests/test_printed_render.py`:**

````python


def test_the_longest_details_still_fit_the_cover():
    """PR 2a: at every limit, with a church name of two lines, the contact lines shrink to fit the cover, so
    the order of worship still starts on page 1 (side 1 stays the cover and page 1)."""
    def longest(field: str, word: str) -> str:
        return (word * bs.MAX_LENGTH[field])[:bs.MAX_LENGTH[field]].strip()

    settings = bs.BulletinSettings(
        address_lines=tuple(longest("address_line", f"{n}00 Example Street ") for n in (1, 2, 3)),
        phone=longest("phone", "(555) 010-0100 "), email=longest("email", "office.")[:-12] + "@example.com",
        website=longest("website", "example.com/"), facebook=longest("facebook", "Example Church "),
        **{role: longest("person", "Alex Example ") for role in bs.ROLES})
    ps = dataclasses.replace(service(), church_name="The First Presbyterian Church of Springfield", settings=settings)
    pages = halves(printed_pdf.render_pdf(ps))
    assert pages[0].startswith("The First Presbyterian Church of Springfield [Cover picture]")
    assert pages[0].endswith(f"FB: {settings.facebook}")
    assert pages[1].startswith("1 THE SERVICE FOR THE LORD’S DAY The First Presbyterian Church of Springfield")
````

**In `backend/tests/test_api_printed.py`, replace:**

````python
    assert "FIRST READING: Isaiah 5:1-7 [Liturgist] [Reading text unavailable] NEW TESTAMENT" in text
    assert "NEW TESTAMENT READING: Philippians 3:4b-14 [Worship leader] Text of Philippians 3:4-14 (kjv). Second verse." in text
````

**with:**

````python
    assert "FIRST READING: Isaiah 5:1-7 [Reading text unavailable] NEW TESTAMENT" in text      # no names saved yet
    assert "NEW TESTAMENT READING: Philippians 3:4b-14 Text of Philippians 3:4-14 (kjv). Second verse." in text
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py backend/tests/test_api_printed.py 2>&1 | tail -3`
**Expected** (`PrintedService` has no `settings` yet, and PR 1 still prints the placeholders):
```
FAILED backend/tests/test_printed_render.py::test_the_longest_details_still_fit_the_cover
FAILED backend/tests/test_api_printed.py::test_the_pdf_downloads_with_the_file_headers_and_the_readings_text
12 failed, 13 passed in <t>s
```

- [ ] **Step 3: Print the settings**

`_element` and the helpers that build elements take the settings (`s`) first; the header moves to `_header`, and `contact_lines` builds the cover's lines. `GLORIA_PATRI` is now imported from `bulletin_settings`, so `pb.GLORIA_PATRI` still names it.

**In `backend/printed_bulletin.py`, replace:**

````python
- Anything the app does not know yet (the church's address, the people who
  lead, the music, the announcements) prints as a [bracketed placeholder];
  PR 2 fills them from the Bulletin step and the bulletin settings.
````

**with:**

````python
- The standing details (the church's contact lines, the people who lead and
  what each leads, the service time, the stars, the stand note and the Gloria
  Patri words) come from the church's bulletin settings (PR 2a,
  bulletin_settings); a blank one prints nothing (PR 2 planning answer 3).
  The weekly fields (the music, the announcements, the cover picture) print
  as [bracketed placeholders] until PR 2b's Bulletin step and PR 3 fill them.
````

**In `backend/printed_bulletin.py`, replace:**

````python
from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS
````

**with:**

````python
from bulletin_settings import GLORIA_PATRI, BulletinSettings
from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS
````

**In `backend/printed_bulletin.py`, replace:**

````python
# PR 1's placeholders: what PR 2's settings and Bulletin step fill in.
WORSHIP_LEADER = "[Worship leader]"
LITURGIST = "[Liturgist]"
ORGANIST = "[Organist]"
SERVICE_TIME = "[Service time]"
CONTACT_LINES = ("[Street address]", "[City, State ZIP]", "[Phone]", "[Email]", "[Website]",
                 "FB: [Facebook name]")
PRELUDE
````

**with:**

````python
# The weekly fields' placeholders, until PR 2b's Bulletin step and PR 3 fill them.
PRELUDE
````

**In `backend/printed_bulletin.py`, replace:**

````python

# Who leads each element until PR 2's settings say (the owner's sample).
LEADERS: dict[str, str] = {
    "prelude": ORGANIST, "welcome": LITURGIST, "call_to_worship": LITURGIST, "opening_prayer": LITURGIST,
    "prayer_of_confession": LITURGIST, "assurance": LITURGIST, "prayer_for_illumination": LITURGIST,
    "ot_reading": LITURGIST, "nt_reading": WORSHIP_LEADER, "sermon": WORSHIP_LEADER,
    "prayers_of_the_people": WORSHIP_LEADER, "offertory_prayer": WORSHIP_LEADER, "postlude": ORGANIST,
}
# The elements printed with the star of STAND_NOTE (the owner's sample).
STARRED = frozenset({"first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "doxology",
                     "third_hymn", "benediction"})
STAND_NOTE = "*Congregation stands if able"

GLORIA_PATRI = ("Glory be to the Father, and to the Son, and to the Holy Ghost; as it was in the "
                "beginning, is now, and ever shall be, world without end. Amen, amen.")
APOSTLES_CREED
````

**with:**

````python

# The header's people, as "{name}, Worship Leader" (bulletin_settings.ROLES order).
ROLE_TITLES = {"worship_leader": "Worship Leader", "liturgist": "Liturgist", "organist": "Organist"}

APOSTLES_CREED
````

**In `backend/printed_bulletin.py`, replace:**

````python
    nt: Optional[Reading] = None
    translation_label: str = ""
````

**with:**

````python
    nt: Optional[Reading] = None
    translation_label: str = ""
    settings: BulletinSettings = BulletinSettings()      # the church's standing settings (PR 2a)
````

**In `backend/printed_bulletin.py`, replace:**

````python
def _star(key: str) -> str:
    return "*" if key in STARRED else ""


def _element(key: str, label: str, *value: Span) -> Line:
    """An element's heading: the label in capitals and bold, then its value,
    and the leader right-aligned."""
    return Line("element", (Span(f"{_star(key)}{label.upper()}", bold=True), *value), right=LEADERS.get(key, ""))
````

**with:**

````python
def _element(s: BulletinSettings, key: str, label: str, *value: Span) -> Line:
    """An element's heading: the label in capitals and bold (with the stand
    star when the settings star it), then its value, and the leader's name
    right-aligned (none when the element has no role or the role no name)."""
    star = "*" if key in s.starred else ""
    return Line("element", (Span(f"{star}{label.upper()}", bold=True), *value), right=s.leader(key))
````

**In `backend/printed_bulletin.py`, replace:**

````python
def _hymn(key: str, hymn: Optional[ResolvedHymn]) -> list[Line]:
````

**with:**

````python
def _hymn(s: BulletinSettings, key: str, hymn: Optional[ResolvedHymn]) -> list[Line]:
````

**In `backend/printed_bulletin.py`, replace:**

````python
    return [_element(key, "Hymn:", Span("  "), *number, _quoted(hymn.title))]


def _text_element(key: str, label: str, text: str, style: Style = "body") -> list[Line]:
    if not text:
        return []
    return [_element(key, label), Line(style, (Span(text, bold=style == "bold"),))]


def _custom(anchor: str, resolved: ResolvedService) -> list[Line]:
    lines = []
    for element in resolved.custom_elements:
        if element.insert_after == anchor and element.label:
            lines.append(_element("", element.label))
````

**with:**

````python
    return [_element(s, key, "Hymn:", Span("  "), *number, _quoted(hymn.title))]


def _text_element(s: BulletinSettings, key: str, label: str, text: str, style: Style = "body") -> list[Line]:
    if not text:
        return []
    return [_element(s, key, label), Line(style, (Span(text, bold=style == "bold"),))]


def _custom(s: BulletinSettings, anchor: str, resolved: ResolvedService) -> list[Line]:
    lines = []
    for element in resolved.custom_elements:
        if element.insert_after == anchor and element.label:
            lines.append(_element(s, "", element.label))
````

**In `backend/printed_bulletin.py`, replace:**

````python
def _reading(key: str, label: str, reading: Optional[Reading]) -> list[Line]:
    if reading is None:
        return []
    lines = [_element(key,
````

**with:**

````python
def _reading(s: BulletinSettings, key: str, label: str, reading: Optional[Reading]) -> list[Line]:
    if reading is None:
        return []
    lines = [_element(s, key,
````

**In `backend/printed_bulletin.py`, replace:**

````python
def _communion() -> list[Line]:
````

**with:**

````python
def _communion(s: BulletinSettings) -> list[Line]:
````

**In `backend/printed_bulletin.py`, replace:**

````python
            lines.append(_element("", block.text))
````

**with:**

````python
            lines.append(_element(s, "", block.text))
````

**In `backend/printed_bulletin.py`, replace:**

````python
def _music(key: str, label: str, piece: tuple[str, str]) -> list[Line]:
    title, composer = piece
    return [_element(key,
````

**with:**

````python
def _music(s: BulletinSettings, key: str, label: str, piece: tuple[str, str]) -> list[Line]:
    title, composer = piece
    return [_element(s, key,
````

**In `backend/printed_bulletin.py`, replace:**

````python
def order_of_worship(ps: PrintedService) -> list[Line]:
    """The inside pages: the service header, then the elements in OUTLINE
    order with the sample's additions, each custom element after its anchor."""
    r = ps.resolved
    lit: Mapping[str, str] = r.liturgy
    hymns = r.hymns
    sermon = r.sermon_title.strip() or "[Sermon title]"
    lines: list[Line] = [
        Line("header", (Span("THE SERVICE FOR THE LORD’S DAY", bold=True),)),
        Line("header", (Span(ps.church_name, bold=True),)),
        Line("header", (Span(f"{WORSHIP_LEADER}, Worship Leader", bold=True),)),
        Line("header", (Span(f"{LITURGIST}, Liturgist", bold=True),)),
        Line("header", (Span(f"{ORGANIST}, Organist", bold=True),)),
        Line("element", (Span(printed_date(r.service_date), bold=True),), right=SERVICE_TIME),
        _section("GATHERING FOR WORSHIP"),
        *_music("prelude", "Prelude", PRELUDE),
        _element("welcome", "Welcome and Announcements"),
    ]
    if lit.get("call_to_worship"):
        lines += [_element("call_to_worship", "Call to Worship"), *_leader_people(lit["call_to_worship"])]
    lines += _custom("call_to_worship", r)
    lines += _text_element("opening_prayer", "Opening Prayer", lit.get("opening_prayer", ""))
    lines += _custom("opening_prayer", r)
    lines += _hymn("first_hymn", hymns.get("opening"))
    lines += _custom("first_hymn", r)
    lines += _text_element("prayer_of_confession", "Prayer of Confession", lit.get("prayer_of_confession", ""), "bold")
    lines += _custom("prayer_of_confession", r)
    if lit.get("assurance"):
        lines += [_element("assurance", "Assurance of Pardon"), *_assurance(lit["assurance"])]
    lines += _custom("assurance", r)
    lines += [_element("gloria_patri", "Sung Response:", Span("  "), _quoted("Gloria Patri")),
              Line("bold", (Span(GLORIA_PATRI, bold=True, italic=True),))]
    lines += _text_element("prayer_for_illumination", "Prayer for Illumination", lit.get("prayer_for_illumination", ""))
    lines += _custom("prayer_for_illumination", r)
    lines.append(_section("RECEIVING THE WORD"))
    lines += _reading("ot_reading", "First Reading", ps.ot)
    lines += _custom("ot_reading", r)
    lines += _reading("nt_reading", "New Testament Reading", ps.nt)
    if (ps.ot or ps.nt) and ps.translation_label:
        lines.append(Line("credit", (Span(f"Scripture readings are from the {ps.translation_label}.", italic=True),)))
    lines += _custom("nt_reading", r)
    lines.append(_element("sermon", "Sermon:", Span("  "), _quoted(sermon)))
    lines += _custom("sermon", r)
    lines += [_element("affirmation_of_faith", "Affirmation of Faith:", Span("  "),
                       Span("“The Apostles’ Creed”", bold=True)),
              Line("bold", (Span(APOSTLES_CREED, bold=True),))]
    lines += _custom("affirmation_of_faith", r)
    lines += _hymn("second_hymn", hymns.get("response"))
    lines += _custom("second_hymn", r)
    if r.include_communion:
        lines += _communion()
    lines += _custom("communion", r)
    lines.append(_element("prayers_of_the_people", "Prayers of the People/The Lord’s Prayer"))
    lines += _custom("prayers_of_the_people", r)
    lines += [_section("RESPONDING TO THE WORD"),
              _element("offering", "Offering Our Gifts"),
              _element("doxology", "Sung Response:", Span("  "), _quoted("Doxology"))]
    lines += _text_element("offertory_prayer", "Offertory Prayer", lit.get("offertory_prayer", ""))
    lines += _custom("offertory_prayer", r)
    lines.append(_section("SENDING OUT TO SERVE"))
    lines += _hymn("third_hymn", hymns.get("closing"))
    lines += _custom("third_hymn", r)
    lines += _custom("benediction", r)
    lines += _text_element("benediction", "Benediction", lit.get("benediction", ""))
    lines += _music("postlude", "Postlude", POSTLUDE)
    lines += _custom("end", r)
    lines.append(Line("note", (Span(STAND_NOTE),)))
    return lines


def cover(ps: PrintedService) -> list[Line]:
    """The front page: the church's name, the picture's place with the
    sermon reading and the date over it, and the church's contact lines."""
    reading = ps.nt or ps.ot
    return [
        Line("title", (Span(ps.church_name, bold=True),)),
        Line("box", (Span(COVER_PICTURE),)),
        Line("box", (Span(reading.reference if reading else ""),)),
        Line("box", (Span(printed_date(ps.resolved.service_date)),)),
        *(Line("contact", (Span(text),)) for text in CONTACT_LINES),
    ]


````

**with:**

````python
def _header(ps: PrintedService) -> list[Line]:
    """"THE SERVICE FOR THE LORD'S DAY", the church, each person with a name
    ("{name}, Worship Leader"), and the date with the service time across."""
    s = ps.settings
    people = [Line("header", (Span(f"{getattr(s, role)}, {title}", bold=True),))
              for role, title in ROLE_TITLES.items() if getattr(s, role)]
    return [
        Line("header", (Span("THE SERVICE FOR THE LORD’S DAY", bold=True),)),
        Line("header", (Span(ps.church_name, bold=True),)),
        *people,
        Line("element", (Span(printed_date(ps.resolved.service_date), bold=True),), right=s.service_time),
    ]


def order_of_worship(ps: PrintedService) -> list[Line]:
    """The inside pages: the service header, then the elements in OUTLINE
    order with the sample's additions, each custom element after its anchor."""
    r = ps.resolved
    s = ps.settings
    lit: Mapping[str, str] = r.liturgy
    hymns = r.hymns
    sermon = r.sermon_title.strip() or "[Sermon title]"
    lines: list[Line] = [
        *_header(ps),
        _section("GATHERING FOR WORSHIP"),
        *_music(s, "prelude", "Prelude", PRELUDE),
        _element(s, "welcome", "Welcome and Announcements"),
    ]
    if lit.get("call_to_worship"):
        lines += [_element(s, "call_to_worship", "Call to Worship"), *_leader_people(lit["call_to_worship"])]
    lines += _custom(s, "call_to_worship", r)
    lines += _text_element(s, "opening_prayer", "Opening Prayer", lit.get("opening_prayer", ""))
    lines += _custom(s, "opening_prayer", r)
    lines += _hymn(s, "first_hymn", hymns.get("opening"))
    lines += _custom(s, "first_hymn", r)
    lines += _text_element(s, "prayer_of_confession", "Prayer of Confession", lit.get("prayer_of_confession", ""),
                           "bold")
    lines += _custom(s, "prayer_of_confession", r)
    if lit.get("assurance"):
        lines += [_element(s, "assurance", "Assurance of Pardon"), *_assurance(lit["assurance"])]
    lines += _custom(s, "assurance", r)
    lines.append(_element(s, "gloria_patri", "Sung Response:", Span("  "), _quoted("Gloria Patri")))
    if s.gloria_patri_words:
        lines.append(Line("bold", (Span(s.gloria_patri_words, bold=True, italic=True),)))
    lines += _text_element(s, "prayer_for_illumination", "Prayer for Illumination",
                           lit.get("prayer_for_illumination", ""))
    lines += _custom(s, "prayer_for_illumination", r)
    lines.append(_section("RECEIVING THE WORD"))
    lines += _reading(s, "ot_reading", "First Reading", ps.ot)
    lines += _custom(s, "ot_reading", r)
    lines += _reading(s, "nt_reading", "New Testament Reading", ps.nt)
    if (ps.ot or ps.nt) and ps.translation_label:
        lines.append(Line("credit", (Span(f"Scripture readings are from the {ps.translation_label}.", italic=True),)))
    lines += _custom(s, "nt_reading", r)
    lines.append(_element(s, "sermon", "Sermon:", Span("  "), _quoted(sermon)))
    lines += _custom(s, "sermon", r)
    lines += [_element(s, "affirmation_of_faith", "Affirmation of Faith:", Span("  "),
                       Span("“The Apostles’ Creed”", bold=True)),
              Line("bold", (Span(APOSTLES_CREED, bold=True),))]
    lines += _custom(s, "affirmation_of_faith", r)
    lines += _hymn(s, "second_hymn", hymns.get("response"))
    lines += _custom(s, "second_hymn", r)
    if r.include_communion:
        lines += _communion(s)
    lines += _custom(s, "communion", r)
    lines.append(_element(s, "prayers_of_the_people", "Prayers of the People/The Lord’s Prayer"))
    lines += _custom(s, "prayers_of_the_people", r)
    lines += [_section("RESPONDING TO THE WORD"),
              _element(s, "offering", "Offering Our Gifts"),
              _element(s, "doxology", "Sung Response:", Span("  "), _quoted("Doxology"))]
    lines += _text_element(s, "offertory_prayer", "Offertory Prayer", lit.get("offertory_prayer", ""))
    lines += _custom(s, "offertory_prayer", r)
    lines.append(_section("SENDING OUT TO SERVE"))
    lines += _hymn(s, "third_hymn", hymns.get("closing"))
    lines += _custom(s, "third_hymn", r)
    lines += _custom(s, "benediction", r)
    lines += _text_element(s, "benediction", "Benediction", lit.get("benediction", ""))
    lines += _music(s, "postlude", "Postlude", POSTLUDE)
    lines += _custom(s, "end", r)
    if s.stand_note and any(line.style == "element" and line.text.startswith("*") for line in lines):
        lines.append(Line("note", (Span(f"*{s.stand_note}"),)))       # only under a star that printed
    return lines


def contact_lines(s: BulletinSettings) -> list[str]:
    """The cover's contact lines from the settings, the blank ones left out:
    the address lines, the phone, the email, the website, "FB: {name}"."""
    facebook = [f"FB: {s.facebook}"] if s.facebook else []
    return [*s.address_lines, *(text for text in (s.phone, s.email, s.website) if text), *facebook]


def cover(ps: PrintedService) -> list[Line]:
    """The front page: the church's name, the picture's place with the
    sermon reading and the date over it, and the church's contact lines."""
    reading = ps.nt or ps.ot
    return [
        Line("title", (Span(ps.church_name, bold=True),)),
        Line("box", (Span(COVER_PICTURE),)),
        Line("box", (Span(reading.reference if reading else ""),)),
        Line("box", (Span(printed_date(ps.resolved.service_date)),)),
        *(Line("contact", (Span(text),)) for text in contact_lines(ps.settings)),
    ]


````

The PDF's cover shrinks its contact lines to the room the title and the picture's box leave (reportlab's `KeepInFrame`, mode `"shrink"`), so even at every limit the order of worship starts on page 1; lines of typical length print at full size.

**In `backend/printed_pdf.py`, replace:**

````python
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, FrameBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)
````

**with:**

````python
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, FrameBreak, KeepInFrame, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)
````

**In `backend/printed_pdf.py`, replace:**

````python
def _story(ps: pb.PrintedService, width: float) -> list[Flowable]:
    cover = pb.cover(ps)
    title, label, reference, date, *contact = cover
    story: list[Flowable] = [
        Paragraph(_markup(title), STYLES["title"]),
        _CoverPicture(width - 60, 300, label.text, reference.text, date.text),
        Spacer(1, 30),
        *(Paragraph(_markup(line), STYLES["contact"]) for line in contact),
        FrameBreak(),
    ]
````

**with:**

````python
def _contact(lines: list[pb.Line], width: float, height: float) -> Flowable:
    """The cover's contact lines, shrunk to fit what the title and the picture
    leave of the cover page (PR 2a), so the order of worship always starts on
    page 1. Lines of typical length fit at full size."""
    paragraphs = [Paragraph(_markup(line), STYLES["contact"]) for line in lines]
    return KeepInFrame(width, height, paragraphs, mode="shrink")


def _story(ps: pb.PrintedService, width: float) -> list[Flowable]:
    cover = pb.cover(ps)
    title, label, reference, date, *contact = cover
    heading = Paragraph(_markup(title), STYLES["title"])
    picture = 300 + 30                                     # the picture's box and the space under it
    room = pb.PAGE_HEIGHT - 2 * MARGIN - heading.wrap(width, pb.PAGE_HEIGHT)[1] - STYLES["title"].spaceAfter - picture
    story: list[Flowable] = [
        heading,
        _CoverPicture(width - 60, 300, label.text, reference.text, date.text),
        Spacer(1, 30),
        _contact(contact, width, max(room, 30.0)),
        FrameBreak(),
    ]
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py backend/tests/test_api_printed.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1` then `grep -nwE "WORSHIP_LEADER|LITURGIST|ORGANIST|SERVICE_TIME|CONTACT_LINES|STAND_NOTE|STARRED|LEADERS" backend/*.py backend/usecases/*.py; echo "constants grep exit $?"`
**Expected:** `25 passed in <t>s`; `1368 passed, 16 skipped in <t>s`; `constants grep exit 1` (PR 1's constants are gone; `-w` matches whole words only, so `bulletin_settings`'s own `DEFAULT_LEADERS`, `DEFAULT_STARRED` and `DEFAULT_STAND_NOTE` do not match).

- [ ] **Step 5: Commit**

```bash
git add backend/printed_bulletin.py backend/printed_pdf.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py backend/tests/test_api_printed.py
git commit -q -m "Printed bulletin PR 2a: the booklet prints the standing settings" -m "PrintedService carries the church's bulletin settings: the cover's
contact lines, the header's people, the service time, each part's leader
and star, the stand note (under a printed star only) and the Gloria Patri
words come from them, and a blank one prints nothing. The PDF shrinks the
cover's contact lines when they would not fit, so the order of worship
always starts on page 1. The weekly fields keep PR 1's placeholders until
PR 2b." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1368 passed, 16 skipped`; frontend `660 passed` in 83 files.

### Task 3: `GET` and `PUT /church/bulletin-settings`, and the download reads them (planning answers 1-3; S API, "Data model"; F §1.7; clarifications 3, 6, 7, 12, 14)

**Files:**
- Create: `backend/tests/test_api_bulletin_settings.py`, `backend/usecases/church_bulletin.py`, `backend/api/routes/bulletin_settings.py`
- Modify: `backend/tests/test_api_printed.py`, `backend/tests/test_no_streamlit_in_core.py`, `backend/tests/test_church_settings.py`, `backend/repos/churches.py`, `backend/api/main.py`, `backend/usecases/documents.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (regenerated)

- [ ] **Step 1: Write the failing tests**

**Create `backend/tests/test_api_bulletin_settings.py`:**

````python
"""GET and PUT /church/bulletin-settings (printed bulletin spec, PR 2a; PR 2
planning answers 1 and 2): any member reads them, admins and owners change
them, stored whole in churches.settings["bulletin"] next to the church's
other settings."""
import pytest

from db import session_scope
from db.models import Church
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)
from tests.test_bulletin_settings import DEFAULT_JSON

PATH = "/church/bulletin-settings"
BODY = {
    "address_lines": ["100 Example Street", "Springfield, ST 00000"], "phone": "(555) 010-0100",
    "email": "office@example.com", "website": "example.com", "facebook": "Example Church",
    "service_time": "10:30 a.m.", "worship_leader": "Rev. Alex Example", "liturgist": "Sam Sample",
    "organist": "Jordan Doe", "stand_note": "Congregation stands if able", "gloria_patri_words": "Glory be.",
    "starred": ["first_hymn", "doxology"], "leaders": {"sermon": "worship_leader", "postlude": "organist"},
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    """Owned by owner@example.com, with admin@ and member@ in it."""
    cid = make_church(name="Example Church", owner_user_id=make_user(email="owner@example.com"))
    add_membership(make_user(email="admin@example.com"), cid, "admin")
    add_membership(make_user(email="member@example.com"), cid, "member")
    return cid


def get(client, church, email="member@example.com"):
    return client.get(PATH, headers=church_headers(email, church))


def put(client, church, body, email="admin@example.com"):
    return client.put(PATH, json=body, headers=church_headers(email, church))


def stored(church) -> dict:
    with session_scope() as s:
        return s.get(Church, church).settings


def test_a_member_reads_the_defaults_before_anything_is_saved(client, church):
    r = get(client, church)
    assert r.status_code == 200, r.text
    assert r.json() == DEFAULT_JSON


def test_an_admin_saves_them_whole_and_the_other_settings_stay(client, church):
    with session_scope() as s:
        s.get(Church, church).settings = {"bible_translation": "kjv", "default_hymnal": "GG2013"}
    r = put(client, church, BODY)
    assert r.status_code == 200, r.text
    assert r.json() == BODY
    assert get(client, church).json() == BODY
    assert stored(church) == {"bible_translation": "kjv", "default_hymnal": "GG2013", "bulletin": BODY}
    smaller = {**BODY, "starred": [], "leaders": {}, "address_lines": []}
    assert put(client, church, smaller, email="owner@example.com").json() == smaller       # owners too
    assert stored(church)["bulletin"] == smaller and stored(church)["bible_translation"] == "kjv"


def test_what_is_saved_is_trimmed_and_in_order(client, church):
    r = put(client, church, {**BODY, "phone": "  (555) 010-0100 ", "address_lines": [" 100 Example Street ", " "],
                             "stand_note": "*Please stand if able", "starred": ["doxology", "first_hymn", "doxology"],
                             "gloria_patri_words": "Glory\x00 be.\r\nAmen.",
                             "leaders": {"postlude": "organist", "sermon": "worship_leader"}})
    assert r.status_code == 200, r.text
    assert r.json() == {**BODY, "address_lines": ["100 Example Street"], "stand_note": "Please stand if able",
                        "gloria_patri_words": "Glory be.\nAmen."}
    assert list(stored(church)["bulletin"]["leaders"]) == ["sermon", "postlude"]


def test_a_member_cannot_change_them(client, church):
    r = put(client, church, BODY, email="member@example.com")
    assert r.status_code == 403, r.text
    assert r.json()["error"]["code"] == "forbidden"
    assert r.json()["error"]["message"] == "Only church admins can do this."
    assert "bulletin" not in stored(church)


def test_a_stored_value_of_the_wrong_shape_reads_as_the_defaults(client, church):
    with session_scope() as s:
        s.get(Church, church).settings = {"bulletin": {"phone": 7, "starred": "x", "leaders": {"sermon": "pastor"},
                                                       "organist": "Jordan Doe"}}
    assert get(client, church).json() == {**DEFAULT_JSON, "organist": "Jordan Doe", "leaders": {}}


@pytest.mark.parametrize("change, field", [
    ({"phone": "1" * 41}, "phone"),
    ({"phone": "(555)\n010-0100"}, "phone"),
    ({"address_lines": ["100 Example\tStreet"]}, "address_lines.0"),
    ({"address_lines": ["a", "b", "c", "d"]}, "address_lines"),
    ({"starred": ["anthem"]}, "starred.0"),
    ({"leaders": {"sermon": "pastor"}}, "leaders.sermon"),
    ({"leaders": {"anthem": "organist"}}, "leaders.anthem.[key]"),
    ({"extra": "x"}, "extra"),
])
def test_a_bad_body_is_a_422_naming_the_field(client, church, change, field):
    r = put(client, church, {**BODY, **change})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"], r.text
    assert "bulletin" not in stored(church)


def test_every_field_is_required(client, church):
    body = {k: v for k, v in BODY.items() if k != "gloria_patri_words"}
    r = put(client, church, body)
    assert r.status_code == 422 and "gloria_patri_words" in r.json()["error"]["fields"], r.text


def test_only_members_of_the_church(client, isolation_world):
    assert_church_isolated(client, "GET", PATH, world=isolation_world)
    assert_church_isolated(client, "PUT", PATH, world=isolation_world, json=BODY)
````

**Append to `backend/tests/test_api_printed.py`:**

````python


def test_the_church_s_bulletin_settings_print_for_every_member(client, church, make_user, calls):
    """PR 2a: the details an admin saved print on everyone's bulletin; a blank one prints nothing."""
    with session_scope() as s:
        s.get(Church, church).settings = {"bulletin": {
            "address_lines": ["100 Example Street"], "phone": "", "facebook": "Example Church",
            "service_time": "10:30 a.m.", "worship_leader": "Rev. Alex Example", "liturgist": "Sam Sample",
            "organist": "", "starred": ["sermon"], "leaders": {"sermon": "worship_leader", "nt_reading": "liturgist"},
            "stand_note": "Please stand if able", "gloria_patri_words": "Glory be."}}
    member = make_user(email="member@example.com")
    add_membership(member, church, "member")
    r = post(client, church, {"format": "pdf", "service": SERVICE}, email="member@example.com")
    assert r.status_code == 200, r.text
    text = pdf_text(r.content)
    assert "October 4, 2026 100 Example Street FB: Example Church 1 THE SERVICE FOR THE LORD’S DAY Example Church " \
           "Rev. Alex Example, Worship Leader Sam Sample, Liturgist October 4, 2026 10:30 a.m." in text
    assert "NEW TESTAMENT READING: Philippians 3:4b-14 Sam Sample" in text
    assert "*SERMON: “Living Water” Rev. Alex Example" in text and "*HYMN" not in text
    assert "Glory be." in text and text.count("*Please stand if able") == 1
    for gone in ("Organist", "[Organist]", "[Liturgist]", "[Worship leader]", "[Service time]", "[Phone]", "[Email]"):
        assert gone not in text, gone
    assert "‘[Prelude title]’" in text and "Coffee Hour: [Name]" in text           # the weekly fields: PR 2b


def test_a_stored_control_character_still_prints_in_word(client, church, calls):
    """PR 2a: settings written by another path are made Word-safe when printed, as the PUT makes them."""
    with session_scope() as s:
        s.get(Church, church).settings = {"bulletin": {"organist": "Jordan\x01 Doe", "phone": "(555)\x0b010-0100"}}
    r = post(client, church, {"format": "docx", "service": SERVICE})
    assert r.status_code == 200, r.text
    paragraphs = [p.text for p in Document(BytesIO(r.content)).paragraphs]
    assert "Jordan Doe, Organist" in paragraphs and "(555)\n010-0100" in paragraphs
````

**In `backend/tests/test_church_settings.py`, replace:**

````python
    get_church_rubric, get_church_rubric_overrides, update_church_rubric,
)
````

**with:**

````python
    get_church_rubric, get_church_rubric_overrides, update_church_rubric,
    set_bulletin_settings,
)
````

**In `backend/tests/test_church_settings.py`, replace:**

````python
                  lambda: set_church_prompts(cid, {"benediction": "Go in peace."})):
````

**with:**

````python
                  lambda: set_church_prompts(cid, {"benediction": "Go in peace."}),
                  lambda: set_bulletin_settings(cid, {"phone": "(555) 010-0100"})):
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "printed_bulletin, printed_pdf, printed_docx; "
````

**with:**

````python
            "printed_bulletin, printed_pdf, printed_docx, bulletin_settings, usecases.church_bulletin; "
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_bulletin_settings.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -4` then `.venv/bin/python -m pytest -q backend/tests/test_church_settings.py 2>&1 | tail -3`
**Expected** (the route does not exist yet: every request is a 404, a member's PUT included; the printed bulletin does not read the settings; `usecases.church_bulletin` cannot be imported; `set_bulletin_settings` does not exist, so `test_church_settings.py` cannot be collected: `ImportError` above its lines):
```
FAILED backend/tests/test_api_printed.py::test_the_church_s_bulletin_settings_print_for_every_member
FAILED backend/tests/test_api_printed.py::test_a_stored_control_character_still_prints_in_word
FAILED backend/tests/test_no_streamlit_in_core.py::test_usecases_package_imports_no_fastapi_or_streamlit
18 failed, 12 passed in <t>s
```
```
ERROR backend/tests/test_church_settings.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: The repo function, the usecase, the route, and the download**

**Append to `backend/repos/churches.py`:**

````python


def set_bulletin_settings(church_id, value: dict) -> None:
    """Store the church's bulletin settings (printed bulletin spec, PR 2a) as
    settings["bulletin"], whole, under the row lock: every other settings key
    (the translation, the hymnal, the rubric, the prompts) stays as stored."""
    _merge_settings(church_id, {"bulletin": value})
````

**Create `backend/usecases/church_bulletin.py`:**

````python
"""The church's bulletin settings (printed bulletin spec, PR 2a): GET and PUT
/church/bulletin-settings.

get_bulletin_settings reads churches.settings["bulletin"] tolerantly
(read_settings: bulletin_settings.read of the stored texts made Word-safe,
which build_printed uses too, so a value written by any other path never
breaks the Word version). save_bulletin_settings stores the validated body
whole as settings["bulletin"] in one locked read-modify-write
(repos.churches.set_bulletin_settings), so the church's other settings are
never touched; two admins saving at once both succeed and the later save is
what stays (plan clarification 6). It stores the body as read_settings
cleans it and answers what is stored. Every text goes through
archive._xml_safe first (as the service's texts do), so the Word version can
always hold it. A church missing or soft-deleted is require_church's 403. No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import uuid
from collections.abc import Mapping

import bulletin_settings
from domain_errors import Forbidden
from repos import churches
from usecases import archive

NO_ACCESS_MESSAGE = "You don't have access to this church."      # usecases.church_profile's


def _safe(value: object) -> object:
    if isinstance(value, str):
        return archive._xml_safe(value)
    if isinstance(value, list):
        return [_safe(item) for item in value]
    return value


def read_settings(settings: object) -> bulletin_settings.BulletinSettings:
    """A church's stored settings JSON as the bulletin settings, every text Word-safe."""
    stored = settings.get("bulletin") if isinstance(settings, Mapping) else None
    if not isinstance(stored, Mapping):
        return bulletin_settings.read(None)
    return bulletin_settings.read({"bulletin": {name: _safe(value) for name, value in stored.items()}})


def get_bulletin_settings(church_id: uuid.UUID) -> bulletin_settings.BulletinSettings:
    church = churches.get_church(church_id)
    if church is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    return read_settings(church["settings"])


def save_bulletin_settings(church_id: uuid.UUID, body: Mapping) -> bulletin_settings.BulletinSettings:
    """`body` is PUT's validated body (every field, within its limits)."""
    churches.set_bulletin_settings(church_id, read_settings({"bulletin": body}).to_json())
    return get_bulletin_settings(church_id)
````

**Create `backend/api/routes/bulletin_settings.py`:**

````python
"""GET and PUT /church/bulletin-settings (printed bulletin spec, PR 2a; PR 2
planning answers 1 and 2): the church's standing bulletin settings, which
every member's printed bulletin uses.

GET: any member (require_church); a church that never saved them reads the
defaults. PUT: admins and owners only (require_admin; a member's PUT is the
role 403 "Only church admins can do this."), the whole object every time
(extra="forbid", every field required), each text trimmed and within its
limit, every text but the Gloria Patri words on one line (no line break, tab
or other control character: a 422 naming the field), the starred elements and the leaders from bulletin_settings'
ELEMENT_KEYS and ROLES. It answers what is stored. No Idempotency-Key (a PUT
of the same body stores the same value) and no If-Match: the later of two
saves wins (plan clarification 6). Plain `def`, no SQL, no try/except
(F §2.2 rule 1).
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

import bulletin_settings as bs
from api.deps import ActiveChurch, require_admin, require_church
from api.errors import error_responses
from usecases import church_bulletin

router = APIRouter()

ElementKey = Literal[bs.ELEMENT_KEYS]
Role = Literal[bs.ROLES]


# One printed line: no control character (a line break or a tab would break the cover or the header).
ONE_LINE = r"^[^\x00-\x1f\x7f]*$"


def _text(field: str):
    pattern = None if field == "gloria_patri_words" else ONE_LINE
    return Annotated[str, StringConstraints(strip_whitespace=True, max_length=bs.MAX_LENGTH[field], pattern=pattern)]


class BulletinSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_lines: list[_text("address_line")] = Field(max_length=bs.MAX_ADDRESS_LINES)
    phone: _text("phone")
    email: _text("email")
    website: _text("website")
    facebook: _text("facebook")
    service_time: _text("service_time")
    worship_leader: _text("person")
    liturgist: _text("person")
    organist: _text("person")
    stand_note: _text("stand_note")
    starred: list[ElementKey] = Field(max_length=len(bs.ELEMENT_KEYS))
    gloria_patri_words: _text("gloria_patri_words")
    leaders: dict[ElementKey, Role]


@router.get("/church/bulletin-settings", response_model=BulletinSettings,
            responses=error_responses(401, 403, 422, 503))
def read_bulletin_settings(church: ActiveChurch = Depends(require_church)) -> BulletinSettings:
    return BulletinSettings(**church_bulletin.get_bulletin_settings(church.id).to_json())


@router.put("/church/bulletin-settings", response_model=BulletinSettings,
            responses=error_responses(401, 403, 422, 503))
def save_bulletin_settings(payload: BulletinSettings,
                           church: ActiveChurch = Depends(require_admin)) -> BulletinSettings:
    return BulletinSettings(**church_bulletin.save_bulletin_settings(church.id, payload.model_dump()).to_json())
````

**In `backend/api/main.py`, replace:**

````python
from api.routes import (churches, documents, health, hymnals, hymns, invites, lectionary, liturgy,
                        liturgy_review, me, reference, rubric, scripture, services)
````

**with:**

````python
from api.routes import (bulletin_settings, churches, documents, health, hymnals, hymns, invites, lectionary,
                        liturgy, liturgy_review, me, reference, rubric, scripture, services)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(rubric.router)
````

**with:**

````python
    app.include_router(rubric.router)
    app.include_router(bulletin_settings.router)
````

**In `backend/usecases/documents.py`, replace:**

````python
does not come back prints "[Reading text unavailable]", never an error.
````

**with:**

````python
does not come back prints "[Reading text unavailable]", never an error.
PR 2a adds the church's bulletin settings (church_bulletin.read_settings of
the settings read with the name, every text Word-safe): the contact lines,
the people, the service time, the stars, the stand note and the Gloria Patri
words.
````

**In `backend/usecases/documents.py`, replace:**

````python
from usecases import archive, passages
````

**with:**

````python
from usecases import archive, church_bulletin, passages
````

**In `backend/usecases/documents.py`, replace:**

````python
        translation_label=scripture_fetcher.translation_label(tid))
    content = printed_pdf
````

**with:**

````python
        translation_label=scripture_fetcher.translation_label(tid),
        settings=church_bulletin.read_settings(church["settings"]))
    content = printed_pdf
````

- [ ] **Step 4: Regenerate the API files; see them pass, and the suite**

Run: `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api >/dev/null) && git diff --stat -- frontend/src/lib/api` then `grep -c '"/church/bulletin-settings"' frontend/src/lib/api/openapi.json` then `.venv/bin/python -m pytest -q backend/tests/test_api_bulletin_settings.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_church_settings.py backend/tests/test_openapi_contract.py backend/tests/test_route_guards.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?")`
**Expected:** `Wrote …/frontend/src/lib/api/openapi.json`, then ` frontend/src/lib/api/openapi.json | 351 +++…`, ` frontend/src/lib/api/schema.d.ts  | 171 +++…`, ` 2 files changed, 522 insertions(+)`; `1`; `48 passed in <t>s`; `1385 passed, 16 skipped in <t>s`; `typecheck 0`.

- [ ] **Step 5: Commit**

```bash
git add backend/usecases/church_bulletin.py backend/api/routes/bulletin_settings.py backend/repos/churches.py backend/api/main.py backend/usecases/documents.py backend/tests/test_api_bulletin_settings.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_church_settings.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Printed bulletin PR 2a: GET and PUT /church/bulletin-settings" -m "Any member reads the church's bulletin settings; owners and admins
save them whole as churches.settings[\"bulletin\"] in one locked
read-modify-write that keeps every other settings key (the later of two
saves wins). Every text but the Gloria Patri words is one line. The
printed bulletin reads them with the church's name, made Word-safe, so
every member's bulletin prints them." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1385 passed, 16 skipped`; frontend `660 passed` in 83 files.

### Task 4: The settings on the client: types, keys, queries, the form mapping and "Not filled in" (F §4.4, §4.5; clarifications 3, 9, 13)

**Files:**
- Create: `frontend/src/lib/bulletin-settings.test.ts`, `frontend/src/lib/bulletin-settings.ts`, `frontend/src/lib/queries/bulletin-settings.ts`
- Modify: `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/queries/keys.test.ts`, `frontend/src/lib/church.test.ts`, `frontend/src/lib/api/types.ts`, `frontend/src/lib/queries/keys.ts`, `frontend/src/lib/church.ts`

- [ ] **Step 1: Write the failing tests (and the fixtures)**

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
import type {
  ChurchProfile,
````

**with:**

````ts
import type {
  BulletinSettings,
  ChurchProfile,
````

**Append to `frontend/src/test/fixtures/index.ts`:**

````ts

/** The Gloria Patri's traditional words (`bulletin_settings.GLORIA_PATRI`). */
export const GLORIA_PATRI =
  "Glory be to the Father, and to the Son, and to the Holy Ghost; as it was in the beginning, is now, and ever shall be, world without end. Amen, amen.";

/**
 * `GET /church/bulletin-settings` (printed bulletin PR 2a) for a church that
 * never saved them: the server's defaults, unless overridden.
 */
export function bulletinSettings(overrides: Partial<BulletinSettings> = {}): BulletinSettings {
  return {
    address_lines: [],
    phone: "",
    email: "",
    website: "",
    facebook: "",
    service_time: "",
    worship_leader: "",
    liturgist: "",
    organist: "",
    stand_note: "Congregation stands if able",
    gloria_patri_words: GLORIA_PATRI,
    starred: ["first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "doxology", "third_hymn", "benediction"],
    leaders: {
      prelude: "organist",
      welcome: "liturgist",
      call_to_worship: "liturgist",
      opening_prayer: "liturgist",
      prayer_of_confession: "liturgist",
      assurance: "liturgist",
      prayer_for_illumination: "liturgist",
      ot_reading: "liturgist",
      nt_reading: "worship_leader",
      sermon: "worship_leader",
      prayers_of_the_people: "worship_leader",
      offertory_prayer: "worship_leader",
      postlude: "organist",
    },
    ...overrides,
  };
}

/** Every standing field filled in (invented details). */
export function filledBulletinSettings(overrides: Partial<BulletinSettings> = {}): BulletinSettings {
  return bulletinSettings({
    address_lines: ["100 Example Street", "Springfield, ST 00000"],
    phone: "(555) 010-0100",
    email: "office@example.com",
    website: "example.com",
    facebook: "Example Church",
    service_time: "10:30 a.m.",
    worship_leader: "Rev. Alex Example",
    liturgist: "Sam Sample",
    organist: "Jordan Doe",
    ...overrides,
  });
}
````

**In `frontend/src/lib/queries/keys.test.ts`, replace:**

````ts
      keys.prayerLibrary(id),
    ];
````

**with:**

````ts
      keys.prayerLibrary(id),
      keys.bulletinSettings(id),
    ];
````

**In `frontend/src/lib/queries/keys.test.ts`, replace:**

````ts
      ["prayer-library"],
    ]);
````

**with:**

````ts
      ["prayer-library"],
      ["bulletin-settings"],
    ]);
````

**In `frontend/src/lib/church.test.ts`, replace:**

````ts
import { type Church, pickActiveChurch, roleLabel } from "./church";
````

**with:**

````ts
import { type Church, isAdmin, pickActiveChurch, roleLabel } from "./church";
````

**In `frontend/src/lib/church.test.ts`, replace:**

````ts
    expect((["owner", "admin", "member"] as const).map(roleLabel)).toEqual(["Owner", "Admin", "Member"]);
  });
});
````

**with:**

````ts
    expect((["owner", "admin", "member"] as const).map(roleLabel)).toEqual(["Owner", "Admin", "Member"]);
  });
});

describe("isAdmin", () => {
  it("lets owners and admins edit the church's settings (printed bulletin PR 2a)", () => {
    expect((["owner", "admin", "member"] as const).map(isAdmin)).toEqual([true, true, false]);
  });
});
````

**Create `frontend/src/lib/bulletin-settings.test.ts`:**

````ts
import { describe, expect, it } from "vitest";

import { bulletinSettings, filledBulletinSettings } from "@/test/fixtures";

import {
  addressError,
  ELEMENTS,
  formErrors,
  formFromSettings,
  isDirty,
  notFilledIn,
  notFilledInLine,
  rebaseForm,
  settingsFromForm,
} from "./bulletin-settings";

describe("bulletin settings (printed bulletin PR 2a)", () => {
  it("edits the address as one text and sends it back as trimmed lines, the parts in the printed order", () => {
    const s = filledBulletinSettings({ starred: ["doxology", "prelude"], leaders: { sermon: "organist", prelude: "liturgist" } });
    const form = formFromSettings(s);
    expect(form.address).toBe("100 Example Street\nSpringfield, ST 00000");
    expect(settingsFromForm(form)).toEqual({ ...s, starred: ["prelude", "doxology"], leaders: { prelude: "liturgist", sermon: "organist" } });
    expect(settingsFromForm({ ...form, address: " 100 Example Street \n\n  \nSpringfield " }).address_lines).toEqual([
      "100 Example Street",
      "Springfield",
    ]);
    expect(ELEMENTS).toHaveLength(21);
  });

  it("allows up to three address lines of up to 60 characters, and names the field a 422 names", () => {
    expect(addressError("a\nb\n\nc")).toBeNull();
    expect(addressError("x".repeat(60))).toBeNull();
    expect(addressError("a\nb\nc\nd")).toBe("Use up to 3 lines of up to 60 characters each.");
    expect(addressError("x".repeat(61))).toBe("Use up to 3 lines of up to 60 characters each.");
    expect(formErrors({ "address_lines.0": "Not a valid value.", phone: "Too long (max 40 characters).", starred: "x" })).toEqual({
      address: "Not a valid value.",
      phone: "Too long (max 40 characters).",
    });
  });

  it("rebases the form on newer data: what was not edited takes the new value, what was edited stays", () => {
    const baseline = formFromSettings(bulletinSettings());
    const current = {
      ...baseline,
      phone: "(555) 010-0100",
      starred: baseline.starred.filter((key) => key !== "doxology"),
      leaders: { ...baseline.leaders, sermon: "organist" as const },
    };
    expect(isDirty(baseline, baseline)).toBe(false);
    expect(isDirty(baseline, current)).toBe(true);
    const next = formFromSettings(
      filledBulletinSettings({ phone: "(555) 999-0000", starred: ["prelude", "doxology"], leaders: { prelude: "liturgist" } }),
    );
    const rebased = rebaseForm(baseline, current, next);
    expect(rebased).toEqual({
      ...next,
      phone: "(555) 010-0100",
      starred: ["prelude"],
      leaders: { prelude: "liturgist", sermon: "organist" },
    });
    expect(isDirty(next, rebased)).toBe(true);
    expect(rebaseForm(baseline, baseline, next)).toEqual(next);
  });

  it("lists the blank standing fields in the page's order", () => {
    expect(notFilledIn(filledBulletinSettings())).toEqual([]);
    expect(notFilledIn(bulletinSettings())).toEqual([
      "address",
      "phone",
      "email",
      "website",
      "Facebook name",
      "service time",
      "worship leader",
      "liturgist",
      "organist",
    ]);
    const missing = notFilledIn(filledBulletinSettings({ phone: " ", organist: "", stand_note: "", gloria_patri_words: "" }));
    expect(notFilledInLine(missing)).toBe("Not filled in: phone, organist, stand note, Gloria Patri words.");
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/bulletin-settings.test.ts src/lib/queries/keys.test.ts src/lib/church.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`bulletin-settings.ts` does not exist; `keys.bulletinSettings` and `isAdmin` are not functions yet):
```
   × keys > starts every church-scoped key with ['church', id] <t>ms
   × isAdmin > lets owners and admins edit the church's settings (printed bulletin PR 2a) <t>ms
 FAIL  |unit| src/lib/bulletin-settings.test.ts [ src/lib/bulletin-settings.test.ts ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
      Tests  2 failed | 7 passed (9)
```

- [ ] **Step 3: The types, the key, `isAdmin`, the library and the queries**

**Append to `frontend/src/lib/api/types.ts`:**

````ts

/** `GET`/`PUT /church/bulletin-settings` (printed bulletin PR 2a): the church's standing bulletin settings. */
export type BulletinSettings = components["schemas"]["BulletinSettings"];
````

**In `frontend/src/lib/queries/keys.ts`, replace:**

````ts
  prayerLibrary: (id: string) => ["church", id, "prayer-library"] as const,
````

**with:**

````ts
  prayerLibrary: (id: string) => ["church", id, "prayer-library"] as const,
  bulletinSettings: (id: string) => ["church", id, "bulletin-settings"] as const,
````

**In `frontend/src/lib/church.ts`, replace:**

````ts
export function readStoredChurchId
````

**with:**

````ts
/** Owners and admins: who may edit the church's settings (the server's `require_admin`). */
export function isAdmin(role: Church["role"]): boolean {
  return role === "owner" || role === "admin";
}

export function readStoredChurchId
````

**Create `frontend/src/lib/bulletin-settings.ts`:**

````ts
/**
 * The church's standing bulletin settings (printed bulletin spec, PR 2a):
 * the parts of the order of worship they name, the form the Bulletin
 * settings page edits, and what the Printed bulletin card lists as not
 * filled in (PR 2 planning answer 3: a blank field prints nothing, so the
 * card says which are blank before anyone prints). The form follows 6a's
 * rule for settings forms: newer server data rebases it (a field not edited
 * takes the new value, an edited one keeps the edit), and the page warns
 * before leaving with unsaved edits.
 *
 * The limits mirror `backend/bulletin_settings.py` (`MAX_LENGTH`,
 * `MAX_ADDRESS_LINES`); the server checks them again.
 */
import type { BulletinSettings } from "@/lib/api/types";

export type ElementKey = BulletinSettings["starred"][number];
export type Role = NonNullable<BulletinSettings["leaders"][ElementKey]>;
export type TextField = Exclude<keyof BulletinSettings, "address_lines" | "starred" | "leaders">;

export const ROLES: readonly { key: Role; label: string }[] = [
  { key: "worship_leader", label: "Worship leader" },
  { key: "liturgist", label: "Liturgist" },
  { key: "organist", label: "Organist" },
];

/** The printed order of worship's parts, in its order (`bulletin_settings.ELEMENT_KEYS`). */
export const ELEMENTS: readonly { key: ElementKey; label: string }[] = [
  { key: "prelude", label: "Prelude" },
  { key: "welcome", label: "Welcome and Announcements" },
  { key: "call_to_worship", label: "Call to Worship" },
  { key: "opening_prayer", label: "Opening Prayer" },
  { key: "first_hymn", label: "Opening hymn" },
  { key: "prayer_of_confession", label: "Prayer of Confession" },
  { key: "assurance", label: "Assurance of Pardon" },
  { key: "gloria_patri", label: "Gloria Patri" },
  { key: "prayer_for_illumination", label: "Prayer for Illumination" },
  { key: "ot_reading", label: "First Reading" },
  { key: "nt_reading", label: "New Testament Reading" },
  { key: "sermon", label: "Sermon" },
  { key: "affirmation_of_faith", label: "Affirmation of Faith" },
  { key: "second_hymn", label: "Response hymn" },
  { key: "prayers_of_the_people", label: "Prayers of the People" },
  { key: "offering", label: "Offering" },
  { key: "doxology", label: "Doxology" },
  { key: "offertory_prayer", label: "Offertory Prayer" },
  { key: "third_hymn", label: "Closing hymn" },
  { key: "benediction", label: "Benediction" },
  { key: "postlude", label: "Postlude" },
];

export const MAX_ADDRESS_LINES = 3;
export const MAX_LENGTH: Record<TextField | "address_line", number> = {
  address_line: 60,
  phone: 40,
  email: 100,
  website: 100,
  facebook: 60,
  service_time: 40,
  worship_leader: 100,
  liturgist: 100,
  organist: 100,
  stand_note: 200,
  gloria_patri_words: 1000,
};

/** The page's form: the settings with the address as one text, a line each. */
export type BulletinForm = Omit<BulletinSettings, "address_lines"> & { address: string };
/** The form's text fields: the address and every other text. */
export type FormField = "address" | TextField;
const FORM_FIELDS: readonly FormField[] = [
  "address",
  "phone",
  "email",
  "website",
  "facebook",
  "service_time",
  "worship_leader",
  "liturgist",
  "organist",
  "stand_note",
  "gloria_patri_words",
];

export function formFromSettings(s: BulletinSettings): BulletinForm {
  const { address_lines, ...rest } = s;
  return { ...rest, address: address_lines.join("\n") };
}

/** The address's lines as the server stores them: trimmed, blank ones dropped. */
export function addressLines(address: string): string[] {
  return address
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line !== "");
}

/** The address's problem, or null: at most 3 lines of at most 60 characters. */
export function addressError(address: string): string | null {
  const lines = addressLines(address);
  if (lines.length > MAX_ADDRESS_LINES || lines.some((line) => line.length > MAX_LENGTH.address_line)) {
    return `Use up to ${MAX_ADDRESS_LINES} lines of up to ${MAX_LENGTH.address_line} characters each.`;
  }
  return null;
}

/** `PUT /church/bulletin-settings`'s body: every field, the starred parts and the leaders in the printed order. */
export function settingsFromForm(f: BulletinForm): BulletinSettings {
  const { address, starred, leaders, ...text } = f;
  const order = ELEMENTS.map((e) => e.key);
  return {
    ...text,
    address_lines: addressLines(address),
    starred: order.filter((key) => starred.includes(key)),
    leaders: Object.fromEntries(order.filter((key) => leaders[key]).map((key) => [key, leaders[key]])),
  };
}

/**
 * 6a's rebase rule (one value per text, per part's leader and per part's star):
 * each value still equal to `baseline` (not edited) takes `next`'s; each edited
 * one keeps `current`'s. Used when newer server data arrives while the form is
 * open, and after a save (with the form as sent as the baseline, so what was
 * typed while saving is kept).
 */
export function rebaseForm(baseline: BulletinForm, current: BulletinForm, next: BulletinForm): BulletinForm {
  const out: BulletinForm = { ...next };
  for (const field of FORM_FIELDS) {
    if (current[field] !== baseline[field]) out[field] = current[field];
  }
  const starred = (f: BulletinForm, key: ElementKey) => f.starred.includes(key);
  out.starred = ELEMENTS.map((e) => e.key).filter((key) =>
    starred(current, key) !== starred(baseline, key) ? starred(current, key) : starred(next, key),
  );
  const leaders: BulletinForm["leaders"] = {};
  for (const { key } of ELEMENTS) {
    const role = current.leaders[key] !== baseline.leaders[key] ? current.leaders[key] : next.leaders[key];
    if (role) leaders[key] = role;
  }
  out.leaders = leaders;
  return out;
}

/** Whether the form has edits not yet saved (anything that differs from `baseline`). */
export function isDirty(baseline: BulletinForm, current: BulletinForm): boolean {
  return (
    FORM_FIELDS.some((field) => current[field] !== baseline[field]) ||
    ELEMENTS.some(
      ({ key }) =>
        current.leaders[key] !== baseline.leaders[key] || current.starred.includes(key) !== baseline.starred.includes(key),
    )
  );
}

/** A 422's `fields` ("phone", "address_lines.0", …) by the form field each names. */
export function formErrors(fields: Record<string, string>): Partial<Record<FormField, string>> {
  const errors: Partial<Record<FormField, string>> = {};
  for (const [name, message] of Object.entries(fields)) {
    const head = name.split(".")[0];
    const field = head === "address_lines" ? "address" : (FORM_FIELDS.find((f) => f === head) ?? null);
    if (field && !errors[field]) errors[field] = message;
  }
  return errors;
}

/** What a blank field is called in "Not filled in: …", in the page's order. */
const MISSING_LABELS: readonly [keyof BulletinSettings, string][] = [
  ["address_lines", "address"],
  ["phone", "phone"],
  ["email", "email"],
  ["website", "website"],
  ["facebook", "Facebook name"],
  ["service_time", "service time"],
  ["worship_leader", "worship leader"],
  ["liturgist", "liturgist"],
  ["organist", "organist"],
  ["stand_note", "stand note"],
  ["gloria_patri_words", "Gloria Patri words"],
];

/** The standing fields that are blank (and so print nothing), by their labels. */
export function notFilledIn(s: BulletinSettings): string[] {
  return MISSING_LABELS.filter(([field]) => {
    const value = s[field];
    return Array.isArray(value) ? value.length === 0 : typeof value === "string" && value.trim() === "";
  }).map(([, label]) => label);
}

/** "Not filled in: phone, organist." */
export function notFilledInLine(missing: readonly string[]): string {
  return `Not filled in: ${missing.join(", ")}.`;
}
````

**Create `frontend/src/lib/queries/bulletin-settings.ts`:**

````ts
/**
 * The church's bulletin settings (printed bulletin spec, PR 2a; F §4.4).
 *
 * - `useBulletinSettings()`: `GET /church/bulletin-settings` under
 *   ["church", id, "bulletin-settings"]; any member. The Printed bulletin
 *   card reads it for "Not filled in: …"; the Bulletin settings page shows it,
 *   with `{ fresh: true }`: fetched again on opening the page even when cached,
 *   so the form never starts from an older value.
 * - `useSaveBulletinSettings()`: `PUT` the whole object (admins). Success
 *   caches the answer (what is stored) and toasts "Bulletin settings saved";
 *   a failure toasts the server's message (a member's role 403 included),
 *   except a 401 or a lost church, which the app already reports.
 */
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { BulletinSettings } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const SETTINGS_SAVED = "Bulletin settings saved";
const PATH = "/church/bulletin-settings";

export function useBulletinSettings({ fresh = false }: { fresh?: boolean } = {}): UseQueryResult<
  BulletinSettings,
  ApiError
> {
  const api = useApi();
  const church = useChurch();
  return useQuery<BulletinSettings, ApiError>({
    queryKey: keys.bulletinSettings(church.id),
    queryFn: ({ signal }) => api.church<BulletinSettings>(PATH, { signal }),
    refetchOnMount: fresh ? "always" : true,
  });
}

export function useSaveBulletinSettings() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<BulletinSettings, ApiError, BulletinSettings>({
    mutationFn: (body) => api.church<BulletinSettings>(PATH, { method: "PUT", json: body }),
    onSuccess: (saved) => {
      queryClient.setQueryData(keys.bulletinSettings(church.id), saved);
      toast.success(SETTINGS_SAVED);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      toast.error(errorToastMessage(e));
    },
  });
}
````

- [ ] **Step 4: See them pass, the suite, types and lint**

Run: `(cd frontend && npx vitest run src/lib/bulletin-settings.test.ts src/lib/queries/keys.test.ts src/lib/church.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then the suite, then typecheck and lint.
**Expected:** `      Tests  13 passed (13)`; ` Test Files  84 passed (84)` and `      Tests  665 passed (665)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/bulletin-settings.ts frontend/src/lib/bulletin-settings.test.ts frontend/src/lib/queries/bulletin-settings.ts frontend/src/lib/api/types.ts frontend/src/lib/queries/keys.ts frontend/src/lib/queries/keys.test.ts frontend/src/lib/church.ts frontend/src/lib/church.test.ts frontend/src/test/fixtures/index.ts
git commit -q -m "Printed bulletin PR 2a: the settings on the client" -m "The BulletinSettings type and its query key, useBulletinSettings and
useSaveBulletinSettings, isAdmin, and lib/bulletin-settings: the parts'
names in the printed order, the page's form (the address as one text),
6a's rebase rule for it, the address check, a 422's fields by form field
and the \"Not filled in\" list." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1385 passed, 16 skipped`; frontend `665 passed` in 84 files.

### Task 5: The Bulletin settings page (answer 8; planning answer 2; F §4.1, §4.8, §4.9; clarifications 2, 3, 10, 11, 15)

**Files:**
- Create: `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`, `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, `frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx`

- [ ] **Step 1: Write the failing tests**

**Create `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`:**

````tsx
/**
 * The Bulletin settings page (printed bulletin spec, PR 2a; PR 2 planning
 * answers 1-3): admins edit and save the whole form, members read a summary.
 * The page renders as the route does, with a Toaster.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it } from "vitest";

import BulletinSettingsRoute from "@/app/(signed-in)/(church)/bulletin-settings/page";
import { Toaster } from "@/components/ui/sonner";
import type { BulletinSettings, Church } from "@/lib/api/types";
import { makeQueryClient } from "@/lib/queries/client";
import { SETTINGS_SAVED } from "@/lib/queries/bulletin-settings";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { bulletinSettings, church, filledBulletinSettings, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { ADMINS_ONLY, DISCARD_TITLE } from "./bulletin-settings-page";

const PATH = "/church/bulletin-settings";

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}, cached?: BulletinSettings) {
  const api = installFakeApi({ [`GET ${PATH}`]: filledBulletinSettings(), ...routes });
  const active = church({ role });
  const queryClient = makeQueryClient({ queries: { retry: false } });
  if (cached) queryClient.setQueryData(keys.bulletinSettings(active.id), cached);
  const view = renderWithProviders(
    <>
      <BulletinSettingsRoute />
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/bulletin-settings", queryClient },
  );
  return { ...view, api };
}

function puts(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "PUT" && r.path === PATH);
}

function leaveWarned(): boolean {
  const event = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(event);
  return event.defaultPrevented;
}

afterEach(() => {
  toast.dismiss();
});

describe("Bulletin settings (printed bulletin PR 2a)", () => {
  it("lets an admin change the details, who leads a part and the stars, and saves the whole form", async () => {
    const { api, user } = renderPage("admin", { [`PUT ${PATH}`]: (r: RecordedRequest) => r.body });
    const phone = await screen.findByLabelText("Phone");
    expect(phone).toHaveValue("(555) 010-0100");
    expect(phone).toHaveAttribute("inputmode", "tel");
    expect(screen.getByLabelText("Address")).toHaveValue("100 Example Street\nSpringfield, ST 00000");
    expect(screen.queryByText(ADMINS_ONLY)).toBeNull();
    await user.clear(phone);
    await user.clear(screen.getByLabelText("Service time"));
    await user.type(screen.getByLabelText("Service time"), "9:00 a.m.");
    await user.click(screen.getByRole("combobox", { name: "Sermon: led by" }));
    await user.click(await screen.findByRole("option", { name: "Organist" }));
    await user.click(screen.getByRole("switch", { name: "Prelude: congregation stands" }));
    await user.click(screen.getByRole("switch", { name: "Doxology: congregation stands" }));
    const save = screen.getByRole("button", { name: "Save settings" });
    expect(save).toHaveClass("h-11");
    await user.click(save);
    expect(await screen.findByText(SETTINGS_SAVED)).toBeInTheDocument();
    const expected = filledBulletinSettings({
      phone: "",
      service_time: "9:00 a.m.",
      starred: ["prelude", "first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "third_hymn", "benediction"],
      leaders: { ...bulletinSettings().leaders, sermon: "organist" },
    });
    expect(puts(api)).toHaveLength(1);
    expect(puts(api)[0].body).toEqual(expected);
    // The starred parts (toEqual checked their order) and the leaders in the printed order.
    expect(Object.keys((puts(api)[0].body as typeof expected).leaders)).toEqual(Object.keys(expected.leaders));
    expect(leaveWarned()).toBe(false); // saved: nothing to lose
  });

  it("shows a member the settings as plain text, with no fields and no Save", async () => {
    renderPage("member", { [`GET ${PATH}`]: filledBulletinSettings({ email: "" }) });
    expect(await screen.findByText(ADMINS_ONLY)).toBeInTheDocument();
    const main = screen.getByRole("main");
    expect(within(main).getByText("(555) 010-0100")).toBeInTheDocument();
    expect(within(main).getByText("Not filled in")).toBeInTheDocument(); // the email
    expect(within(main).getByText("Sermon:").parentElement).toHaveTextContent("Sermon: Worship leader");
    expect(within(main).getByText("Opening hymn:").parentElement).toHaveTextContent(
      "Opening hymn: No one, congregation stands",
    );
    expect(within(main).queryAllByRole("textbox")).toEqual([]);
    expect(within(main).queryAllByRole("switch")).toEqual([]);
    expect(screen.queryByRole("button", { name: "Save settings" })).toBeNull();
  });

  it("checks the address before saving, and shows a field the server refuses as an error under it", async () => {
    const { api, user } = renderPage("admin", {
      [`PUT ${PATH}`]: fakeError(422, "invalid_request", "The request was not valid.", {
        fields: { phone: "Not a valid value." },
      }),
    });
    const address = await screen.findByLabelText("Address");
    await user.type(address, "\nLine three\nLine four");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    const problem = screen.getByRole("alert");
    expect(problem).toHaveTextContent("Use up to 3 lines of up to 60 characters each.");
    expect(problem).toHaveClass("text-destructive");
    expect(address).toHaveAttribute("aria-invalid", "true");
    expect(address).toHaveAccessibleDescription(
      "Up to 3 lines, as printed on the cover. Use up to 3 lines of up to 60 characters each.",
    );
    expect(address).toHaveFocus();
    expect(puts(api)).toEqual([]);
    await user.clear(address);
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    expect(await screen.findByText("The request was not valid.")).toBeInTheDocument();
    const phone = screen.getByLabelText("Phone");
    await waitFor(() => expect(phone).toHaveAttribute("aria-invalid", "true"));
    expect(phone).toHaveAccessibleDescription("Not a valid value.");
    expect(phone).toHaveFocus();
    expect(address).not.toHaveAttribute("aria-invalid");
    expect((puts(api)[0].body as { address_lines: string[] }).address_lines).toEqual([]);
    expect(within(screen.getByRole("main")).getByRole("link", { name: "Back to Review & send" })).toHaveAttribute(
      "href",
      "/builder/review",
    );
  });

  it("opens on the settings fetched now, and newer data updates only the fields not edited", async () => {
    const { api, user, queryClient } = renderPage(
      "admin",
      { [`PUT ${PATH}`]: (r: RecordedRequest) => r.body },
      bulletinSettings(), // an older copy in the cache
    );
    const phone = await screen.findByLabelText("Phone");
    expect(phone).toHaveValue("(555) 010-0100"); // not the cached blank
    await user.clear(phone);
    await user.type(phone, "(555) 010-0199");
    await user.click(screen.getByRole("switch", { name: "Prelude: congregation stands" }));
    // Meanwhile another admin saved a new organist, phone and stars.
    api.set(
      `GET ${PATH}`,
      filledBulletinSettings({ organist: "Pat Example", phone: "(555) 010-0155", starred: ["doxology"] }),
    );
    await act(() => queryClient.refetchQueries({ queryKey: keys.bulletinSettings(church().id) }));
    await waitFor(() => expect(screen.getByLabelText("Organist")).toHaveValue("Pat Example"));
    expect(phone).toHaveValue("(555) 010-0199");
    expect(screen.getByRole("switch", { name: "Prelude: congregation stands" })).toBeChecked();
    expect(screen.getByRole("switch", { name: "Doxology: congregation stands" })).toBeChecked();
    expect(screen.getByRole("switch", { name: "Sermon: congregation stands" })).not.toBeChecked();
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    await waitFor(() => expect(puts(api)).toHaveLength(1));
    expect(puts(api)[0].body).toMatchObject({ organist: "Pat Example", phone: "(555) 010-0199", starred: ["prelude", "doxology"] });
  });

  it("keeps what is typed while saving, and shows what was stored everywhere else", async () => {
    let answer: (body: unknown) => void = () => {};
    const { api, user } = renderPage("admin", {
      [`PUT ${PATH}`]: () =>
        new Promise((resolve) => {
          answer = resolve;
        }),
    });
    const standNote = await screen.findByLabelText("Stand note");
    await user.clear(standNote);
    await user.type(standNote, "*Please stand if able");
    await user.click(screen.getByRole("button", { name: "Save settings" }));
    await waitFor(() => expect(puts(api)).toHaveLength(1));
    await user.type(screen.getByLabelText("Organist"), " Jr.");
    answer(filledBulletinSettings({ stand_note: "Please stand if able" })); // the server drops the star
    expect(await screen.findByText(SETTINGS_SAVED)).toBeInTheDocument();
    expect(standNote).toHaveValue("Please stand if able");
    expect(screen.getByLabelText("Organist")).toHaveValue("Jordan Doe Jr.");
    expect(leaveWarned()).toBe(true); // the organist is not saved yet
  });

  it("asks before leaving with unsaved edits", async () => {
    const { user } = renderPage("admin");
    const organist = await screen.findByLabelText("Organist");
    const back = within(screen.getByRole("main")).getByRole("link", { name: "Back to Review & send" });
    expect(leaveWarned()).toBe(false);
    await user.type(organist, " Jr.");
    expect(leaveWarned()).toBe(true);
    await user.click(back);
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(organist).toHaveValue("Jordan Doe Jr.");
    expect(testRouter.push).not.toHaveBeenCalled();
    await user.click(back);
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder/review");
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/bulletin-settings 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the file cannot load: the route does not exist yet):
```
 FAIL  |dom| src/components/bulletin-settings/bulletin-settings-page.test.tsx [ src/components/bulletin-settings/bulletin-settings-page.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: Write the page and its route**

**Create `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`:**

````tsx
"use client";

import Link from "next/link";
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
import { PageHeader } from "@/components/app/page-header";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import type { BulletinSettings } from "@/lib/api/types";
import {
  addressError,
  ELEMENTS,
  formErrors,
  formFromSettings,
  isDirty,
  MAX_LENGTH,
  rebaseForm,
  ROLES,
  settingsFromForm,
  type BulletinForm,
  type ElementKey,
  type FormField,
  type Role,
  type TextField,
} from "@/lib/bulletin-settings";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useBulletinSettings, useSaveBulletinSettings } from "@/lib/queries/bulletin-settings";

export const PAGE_DESCRIPTION = "What every printed bulletin uses. A field left blank is left off the bulletin.";
export const ADMINS_ONLY = "Only admins can edit the bulletin settings. You can read them below.";
export const DISCARD_TITLE = "Discard unsaved changes?";
const DISCARD_BODY = "Your changes on this page haven't been saved.";
const NOT_FILLED_IN = "Not filled in";
const BACK_HREF = "/builder/review";
const NO_ONE: string = "none"; // "No one" leads this part: a real choice, not a placeholder (F §4.9 item 3)
const LEADER_ITEMS: Record<string, string> = {
  [NO_ONE]: "No one",
  ...Object.fromEntries(ROLES.map((r) => [r.key, r.label])),
};

type TextSpec = { field: TextField; label: string; help?: string; long?: boolean };

const CHURCH_FIELDS: readonly TextSpec[] = [
  { field: "phone", label: "Phone" },
  { field: "email", label: "Email" },
  { field: "website", label: "Website" },
  { field: "facebook", label: "Facebook name", help: "Printed as FB: and the name." },
];
const SERVICE_FIELDS: readonly TextSpec[] = [
  { field: "service_time", label: "Service time", help: "Printed across from the date, for example 10:30 a.m." },
];
const PEOPLE_FIELDS: readonly TextSpec[] = [
  { field: "worship_leader", label: "Worship leader" },
  { field: "liturgist", label: "Liturgist" },
  { field: "organist", label: "Organist" },
];
const WORDS_FIELDS: readonly TextSpec[] = [
  { field: "stand_note", label: "Stand note", help: "Printed at the end of the service, after a star." },
  { field: "gloria_patri_words", label: "Gloria Patri words", long: true },
];

/**
 * The phone, email and website keyboards (no `type="email"` or `type="url"`:
 * the browser would refuse a website typed as "example.com"). The browser's
 * own autofill is off: these are the church's details, not the user's.
 */
const INPUT_PROPS: Partial<Record<TextField, ComponentProps<"input">>> = {
  phone: { type: "tel", inputMode: "tel", autoComplete: "off" },
  email: { inputMode: "email", autoComplete: "off", autoCapitalize: "none", spellCheck: false },
  website: { inputMode: "url", autoComplete: "off", autoCapitalize: "none", spellCheck: false },
};

function PageSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="grid gap-4">
      {[0, 1, 2].map((i) => (
        <Skeleton key={i} className="h-40 w-full" />
      ))}
    </div>
  );
}

/**
 * `/bulletin-settings` (printed bulletin spec, PR 2a; PR 2 planning answers
 * 1-3): the church's standing bulletin settings, which every member's
 * printed bulletin uses. Admins and owners edit and save the whole form;
 * members read a plain summary, with a note that only admins can edit it.
 * Until 6a folds it into Settings, the Printed bulletin card on Review & send
 * links here.
 *
 * The settings are fetched again on opening the page (even when cached), and
 * the form shows only once that fetch is back, so it never starts from an
 * older value. 6a's rules for settings forms: newer server data rebases the
 * form (`rebaseForm`), and leaving with unsaved edits asks first (the
 * browser's warning on a reload or close, "Discard unsaved changes?" on
 * **Back to Review & send**).
 */
export function BulletinSettingsPage() {
  const church = useChurch();
  const canEdit = isAdmin(church.role);
  const settings = useBulletinSettings({ fresh: true });
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [leaving, setLeaving] = useState(false);
  // Shown once the fetch made on opening the page is back; then kept, so a failed background refetch keeps the form.
  if (!ready && settings.isFetchedAfterMount && settings.isSuccess) setReady(true);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function onBack(event: MouseEvent<HTMLAnchorElement>) {
    if (!dirty) return;
    event.preventDefault();
    setLeaving(true);
  }

  return (
    <main className="mx-auto grid w-full max-w-2xl content-start gap-4 px-4 py-4">
      <PageHeader
        title="Bulletin settings"
        description={PAGE_DESCRIPTION}
        actions={
          <Link href={BACK_HREF} onClick={onBack} className={buttonVariants({ variant: "outline", size: "touch" })}>
            Back to Review &amp; send
          </Link>
        }
      />
      {ready && settings.data ? (
        canEdit ? (
          <SettingsForm settings={settings.data} onDirtyChange={setDirty} />
        ) : (
          <SettingsSummary settings={settings.data} />
        )
      ) : settings.isError ? (
        <ErrorState error={settings.error} onRetry={() => void settings.refetch()} retrying={settings.isFetching} />
      ) : (
        <PageSkeleton />
      )}
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
    </main>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="grid gap-4 rounded-lg border p-4">
      <legend className="px-1 text-base font-medium">{title}</legend>
      {children}
    </fieldset>
  );
}

function FieldError({ id, message }: { id: string; message?: string }) {
  return message ? (
    <p id={id} role="alert" className="text-sm text-destructive">
      {message}
    </p>
  ) : null;
}

type FormState = { source: BulletinSettings; baseline: BulletinForm; form: BulletinForm };

function SettingsForm({
  settings,
  onDirtyChange,
}: {
  settings: BulletinSettings;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const save = useSaveBulletinSettings();
  const [state, setState] = useState<FormState>(() => {
    const form = formFromSettings(settings);
    return { source: settings, baseline: form, form };
  });
  const [errors, setErrors] = useState<Partial<Record<FormField, string>>>({});
  const addressRef = useRef<HTMLTextAreaElement>(null);
  const { form, baseline } = state;
  const dirty = isDirty(baseline, form);

  // Newer server data (a refetch, or this page's own save in the cache): rebase (6a).
  if (settings !== state.source) {
    const next = formFromSettings(settings);
    setState({ source: settings, baseline: next, form: rebaseForm(baseline, form, next) });
  }

  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);

  const update = (field: FormField | null, change: (f: BulletinForm) => BulletinForm) => {
    setState((s) => ({ ...s, form: change(s.form) }));
    if (field && errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
  };
  const setLeader = (key: ElementKey, role: Role | null) =>
    update(null, (f) => {
      const leaders = { ...f.leaders };
      if (role === null) delete leaders[key];
      else leaders[key] = role;
      return { ...f, leaders };
    });
  const setStarred = (key: ElementKey, on: boolean) =>
    update(null, (f) => ({ ...f, starred: on ? [...f.starred, key] : f.starred.filter((k) => k !== key) }));

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (save.isPending) return;
    const problem = addressError(form.address);
    setErrors(problem ? { address: problem } : {});
    if (problem) {
      addressRef.current?.focus();
      return;
    }
    const sent = form;
    save.mutate(settingsFromForm(sent), {
      // What was typed while saving stays; everything else shows what was stored.
      onSuccess: (saved) =>
        setState((s) => {
          const next = formFromSettings(saved);
          return { ...s, baseline: next, form: rebaseForm(sent, s.form, next) };
        }),
      onError: (e) => {
        if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return;
        const found = formErrors(e.fields);
        setErrors(found);
        const first = (Object.keys(found) as FormField[])[0];
        if (first) document.getElementById(`bulletin-${first}`)?.focus();
      },
    });
  }

  const describedBy = (...ids: (string | false | undefined)[]) => ids.filter(Boolean).join(" ") || undefined;

  const text = ({ field, label, help, long }: TextSpec) => {
    const id = `bulletin-${field}`;
    const error = errors[field];
    const props = {
      id,
      value: form[field],
      maxLength: MAX_LENGTH[field],
      "aria-invalid": error ? true : undefined,
      "aria-describedby": describedBy(help && `${id}-help`, error && `${id}-error`),
      onChange: (e: { target: { value: string } }) => update(field, (f) => ({ ...f, [field]: e.target.value })),
    };
    return (
      <div key={field} className="grid gap-1.5">
        <Label htmlFor={id}>{label}</Label>
        {long ? <Textarea {...props} /> : <Input {...INPUT_PROPS[field]} {...props} className="h-11" />}
        {help ? (
          <p id={`${id}-help`} className="text-sm text-muted-foreground">
            {help}
          </p>
        ) : null}
        <FieldError id={`${id}-error`} message={error} />
      </div>
    );
  };

  return (
    <form onSubmit={onSubmit} className="grid gap-4" aria-label="Bulletin settings">
      <Section title="Church details">
        <div className="grid gap-1.5">
          <Label htmlFor="bulletin-address">Address</Label>
          <Textarea
            id="bulletin-address"
            ref={addressRef}
            value={form.address}
            aria-invalid={errors.address ? true : undefined}
            aria-describedby={describedBy("bulletin-address-help", errors.address && "bulletin-address-error")}
            onChange={(e) => update("address", (f) => ({ ...f, address: e.target.value }))}
          />
          <p id="bulletin-address-help" className="text-sm text-muted-foreground">
            Up to 3 lines, as printed on the cover.
          </p>
          <FieldError id="bulletin-address-error" message={errors.address} />
        </div>
        {CHURCH_FIELDS.map(text)}
      </Section>
      <Section title="Service">{SERVICE_FIELDS.map(text)}</Section>
      <Section title="Who leads">{PEOPLE_FIELDS.map(text)}</Section>
      <Section title="Each part">
        <p className="text-sm text-muted-foreground">
          Who leads each part, and the parts the congregation stands for (printed with a star).
        </p>
        <ul className="grid gap-3">
          {ELEMENTS.map(({ key, label }) => (
            <li key={key} className="grid gap-2 border-t pt-3 first:border-t-0 first:pt-0 sm:grid-cols-[1fr_auto_auto] sm:items-center">
              <span className="text-sm font-medium">{label}</span>
              <Select
                value={form.leaders[key] ?? NO_ONE}
                items={LEADER_ITEMS}
                onValueChange={(value) => {
                  if (typeof value === "string") setLeader(key, value === NO_ONE ? null : (value as Role));
                }}
              >
                <SelectTrigger aria-label={`${label}: led by`} className="h-11 w-full sm:w-44 data-[size=default]:h-11">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(LEADER_ITEMS).map(([value, name]) => (
                    <SelectItem key={value} value={value}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <label className="flex h-11 items-center gap-3 text-sm">
                <Switch
                  checked={form.starred.includes(key)}
                  onCheckedChange={(checked) => setStarred(key, checked)}
                  aria-label={`${label}: congregation stands`}
                  className="after:-inset-y-3.5"
                />
                <span aria-hidden="true">Stands</span>
              </label>
            </li>
          ))}
        </ul>
      </Section>
      <Section title="Printed words">{WORDS_FIELDS.map(text)}</Section>
      <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending}>
        Save settings
      </PendingButton>
    </form>
  );
}

function SummarySection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-3 rounded-lg border p-4">
      <h2 className="text-base font-medium">{title}</h2>
      {children}
    </section>
  );
}

function SummaryItem({ label, value }: { label: string; value: string | readonly string[] }) {
  const lines = typeof value === "string" ? [value].filter((v) => v.trim() !== "") : value;
  return (
    <div className="grid gap-0.5">
      <dt className="text-sm font-medium">{label}</dt>
      <dd className="text-sm whitespace-pre-line break-words">
        {lines.length > 0 ? lines.join("\n") : <span className="text-muted-foreground">{NOT_FILLED_IN}</span>}
      </dd>
    </div>
  );
}

/** What a member sees: the settings as plain text (6a's read-only view), no controls. */
function SettingsSummary({ settings }: { settings: BulletinSettings }) {
  const items = (specs: readonly TextSpec[]) =>
    specs.map(({ field, label }) => <SummaryItem key={field} label={label} value={settings[field]} />);
  const leader = (key: ElementKey) => ROLES.find((r) => r.key === settings.leaders[key])?.label ?? "No one";
  return (
    <div className="grid gap-4">
      <Alert role="status">
        <AlertDescription>{ADMINS_ONLY}</AlertDescription>
      </Alert>
      <SummarySection title="Church details">
        <dl className="grid gap-3">
          <SummaryItem label="Address" value={settings.address_lines} />
          {items(CHURCH_FIELDS)}
        </dl>
      </SummarySection>
      <SummarySection title="Service">
        <dl className="grid gap-3">{items(SERVICE_FIELDS)}</dl>
      </SummarySection>
      <SummarySection title="Who leads">
        <dl className="grid gap-3">{items(PEOPLE_FIELDS)}</dl>
      </SummarySection>
      <SummarySection title="Each part">
        <ul className="grid gap-1 text-sm">
          {ELEMENTS.map(({ key, label }) => (
            <li key={key}>
              <span className="font-medium">{label}:</span> {leader(key)}
              {settings.starred.includes(key) ? ", congregation stands" : ""}
            </li>
          ))}
        </ul>
      </SummarySection>
      <SummarySection title="Printed words">
        <dl className="grid gap-3">{items(WORDS_FIELDS)}</dl>
      </SummarySection>
    </div>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx`:**

````tsx
"use client";

import { BulletinSettingsPage } from "@/components/bulletin-settings/bulletin-settings-page";

/** Bulletin settings: the church's standing printed bulletin details (printed bulletin spec, PR 2a; F §4.1). */
export default function BulletinSettingsRoute() {
  return <BulletinSettingsPage />;
}
````

- [ ] **Step 4: See them pass (three runs), the suite, types and lint**

Run: `for i in 1 2 3; do (cd frontend && npx vitest run src/components/bulletin-settings 2>&1 | grep -E "^ +× |\[ src/|Tests "); done` then the suite, then typecheck and lint, then `grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"`.
**Expected:** three times `      Tests  6 passed (6)`; ` Test Files  85 passed (85)` and `      Tests  671 passed (671)`; `typecheck 0`, `lint 0`; `raw html grep exit 1`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/bulletin-settings/bulletin-settings-page.tsx frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx 'frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx'
git commit -q -m "Printed bulletin PR 2a: the Bulletin settings page" -m "/bulletin-settings: the church's details, the service time, the three
people, who leads each part and which parts the congregation stands for,
the stand note and the Gloria Patri words. Owners and admins save the
whole form (fetched fresh on opening, newer data rebased into the fields
not edited, a warning before leaving with unsaved edits); members read a
plain summary with a note that only admins can edit it." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1385 passed, 16 skipped`; frontend `671 passed` in 85 files.

### Task 6: The Printed bulletin card: "Not filled in" and the link (planning answer 3; clarifications 8, 9, 15)

**Files:**
- Modify: `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, `frontend/src/components/builder/review/printed-card.tsx`

The card now reads `GET /church/bulletin-settings`, and the fake API fails a test on any request it has no route for, so the three test files that render Review & send gain the route in their default routes (a church that saved nothing).

- [ ] **Step 1: Write the failing test (and the routes)**

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
import {
  church,
  churchProfile,
  DRAFT_NOW,
````

**with:**

````tsx
import {
  bulletinSettings,
  church,
  churchProfile,
  DRAFT_NOW,
  filledBulletinSettings,
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
import { PLACEHOLDERS_NOTE, PRINTED_SUMMARY } from "./printed-card";
````

**with:**

````tsx
import { PLACEHOLDERS_NOTE, PRINTED_SUMMARY, SETTINGS_NOTE } from "./printed-card";
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    "GET /liturgy/config": liturgyConfig(),
    ...routes,
  });
  const view = renderWithProviders(
````

**with:**

````tsx
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    ...routes,
  });
  const view = renderWithProviders(
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(await screen.findByText(HYMN_GONE)).toBeInTheDocument();
    expect(clicks).toEqual([]);
  });
});

// --- slice 5a-3: saving
````

**with:**

````tsx
    expect(await screen.findByText(HYMN_GONE)).toBeInTheDocument();
    expect(clicks).toEqual([]);
  });

  it("lists the bulletin settings still blank and links to them (printed bulletin PR 2a)", async () => {
    const blank = renderReview();
    let card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(within(card).getByText(SETTINGS_NOTE)).toBeInTheDocument();
    expect(
      await within(card).findByText(
        "Not filled in: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist.",
      ),
    ).toBeInTheDocument();
    const download = within(card).getByRole("button", { name: "Download printed bulletin" });
    // The list comes before the downloads (read before printing); the button after them.
    const missing = within(card).getByText(/^Not filled in:/);
    expect(missing.compareDocumentPosition(download) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    const link = within(card).getByRole("link", { name: "Bulletin settings" });
    expect(download.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(link).toHaveAttribute("href", "/bulletin-settings");
    expect(link).toHaveClass("h-11");
    blank.unmount();
    window.localStorage.clear();

    const filled = renderReview(testDraft(), { "GET /church/bulletin-settings": filledBulletinSettings({ organist: "" }) });
    card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(await within(card).findByText("Not filled in: organist.")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download printed bulletin" })).toBeEnabled();
    filled.unmount();
  });
});

// --- slice 5a-3: saving
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
import {
  church,
  churchProfile,
  DRAFT_NOW,
  gg2013,
````

**with:**

````tsx
import {
  bulletinSettings,
  church,
  churchProfile,
  DRAFT_NOW,
  gg2013,
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
    "GET /liturgy/config": liturgyConfig(),
    ...routes,
  });
  return renderWithProviders(<BuilderLayout>{page}</BuilderLayout>
````

**with:**

````tsx
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    ...routes,
  });
  return renderWithProviders(<BuilderLayout>{page}</BuilderLayout>
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````tsx
import {
  church,
  CHURCH_IDS,
````

**with:**

````tsx
import {
  bulletinSettings,
  church,
  CHURCH_IDS,
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````tsx
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    ...routes,
  });
````

**with:**

````tsx
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    ...routes,
  });
````

- [ ] **Step 2: See it fail**

Run: `(cd frontend && npx vitest run src/components/builder/review/review-send-step.test.tsx src/components/builder/builder-shell.test.tsx src/components/builder/liturgy/liturgy-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`SETTINGS_NOTE` is not exported yet; everything else passes):
```
   × Review & send: the printed bulletin (printed bulletin PR 1) > lists the bulletin settings still blank and links to them (printed bulletin PR 2a) <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
      Tests  1 failed | 76 passed (77)
```

- [ ] **Step 3: The card's settings block**

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
import { DownloadIcon } from "lucide-react";
import { useState } from "react";
````

**with:**

````tsx
import { DownloadIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
````

**with:**

````tsx
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { buttonVariants } from "@/components/ui/button";
import { notFilledIn, notFilledInLine } from "@/lib/bulletin-settings";
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
import { useDownloadPrinted } from "@/lib/queries/documents";
````

**with:**

````tsx
import { useBulletinSettings } from "@/lib/queries/bulletin-settings";
import { useDownloadPrinted } from "@/lib/queries/documents";
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
export const PLACEHOLDERS_NOTE =
  "For now, the church's details, the people who lead, the music and the announcements print as [placeholders].";
````

**with:**

````tsx
export const SETTINGS_NOTE =
  "The church's details, the people who lead and the service time come from the bulletin settings.";
export const PLACEHOLDERS_NOTE = "For now, the music and the announcements print as [placeholders].";

/**
 * The bulletin settings' blank fields (PR 2 planning answer 3: a blank field
 * prints nothing, so the card says which are blank), above the downloads so
 * it is read before printing. Nothing while the settings load or if they
 * fail: the downloads never wait for them.
 */
function NotFilledInLine() {
  const settings = useBulletinSettings();
  const missing = settings.data ? notFilledIn(settings.data) : [];
  return missing.length > 0 ? <p className="text-sm">{notFilledInLine(missing)}</p> : null;
}
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
      {downloaded && reviewStatus(draft) !== "saved" ? <p className="text-sm text-muted-foreground">{SAVE_HINT}</p> : null}
    </section>
````

**with:**

````tsx
      {downloaded && reviewStatus(draft) !== "saved" ? <p className="text-sm text-muted-foreground">{SAVE_HINT}</p> : null}
      <Link href="/bulletin-settings" className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}>
        Bulletin settings
      </Link>
    </section>
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
        <p className="text-sm text-muted-foreground">{PLACEHOLDERS_NOTE}</p>
````

**with:**

````tsx
        <p className="text-sm text-muted-foreground">{PLACEHOLDERS_NOTE}</p>
        <p className="text-sm text-muted-foreground">{SETTINGS_NOTE}</p>
        <NotFilledInLine />
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
 * documents card. PR 1 prints what the app does not know yet as
 * [placeholders], and the card says so.
````

**with:**

````tsx
 * documents card. PR 1 prints what the app does not know yet as
 * [placeholders], and the card says so. PR 2a: the standing details come
 * from the church's bulletin settings; the card lists the blank ones above
 * the downloads and links to the Bulletin settings page below them (any
 * member; admins edit there).
````

- [ ] **Step 4: See them pass (three runs), the suite, types and lint**

Run: `for i in 1 2 3; do (cd frontend && npx vitest run src/components/builder/review/review-send-step.test.tsx src/components/builder/builder-shell.test.tsx src/components/builder/liturgy/liturgy-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests "); done` then the suite, then typecheck and lint.
**Expected:** three times `      Tests  77 passed (77)`; ` Test Files  85 passed (85)` and `      Tests  672 passed (672)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/builder/review/printed-card.tsx frontend/src/components/builder/review/review-send-step.test.tsx frontend/src/components/builder/builder-shell.test.tsx frontend/src/components/builder/liturgy/liturgy-step.test.tsx
git commit -q -m "Printed bulletin PR 2a: the card lists what is not filled in" -m "The Printed bulletin card says the standing details come from the
bulletin settings, lists the blank ones above the downloads (\"Not
filled in: ...\") and links to the Bulletin settings page below them;
only the music and the announcements still print as placeholders." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1385 passed, 16 skipped`; frontend `672 passed` in 85 files.

### Task 7: Docs: the manual check items (planning answers 1-3; clarification 16)

**Files:**
- Modify: `docs/manual-verification.md`, `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`

- [ ] **Step 1: Amend PR 1's item 2 and the spec's "Data model", append the items**

PR 1's item 2 said the names print as [placeholders], which is no longer so; the spec's "Data model" said a missing value is the placeholder, which planning answer 3 replaced (clarification 5).

**In `docs/manual-verification.md`, replace:**

````markdown
the people lines are bold; the names, music and announcements show as [placeholders].
````

**with:**

````markdown
the people lines are bold; the music and announcements show as [placeholders] (after PR 2a the church's details and the names come from **Bulletin settings**; a blank one prints nothing).
````

**In `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`, replace:**

````markdown
  leaders: {element key: "worship_leader" | "liturgist" | "organist"}}`. No migration; read
  tolerantly (a missing or malformed value is the placeholder). Admins edit them in the Bulletin
````

**with:**

````markdown
  leaders: {element key: "worship_leader" | "liturgist" | "organist"}}`. No migration; read
  tolerantly (a missing or malformed value reads as its default: the sample's stars, leaders'
  roles, stand note and Gloria Patri words, and blank for every detail and name; a blank value
  prints nothing, PR 2 planning answer 3). Admins edit them in the Bulletin
````

**Append to `docs/manual-verification.md`:**

````markdown

### Printed bulletin PR 2a: bulletin settings

After the PR 2a merge the owner's guided check (one step at a time on the
phone) covers the items marked "(owner, after PR 2a)"; the results go into
`docs/ops-runbook.md` → "Printed bulletin PR 2a record". Record what the page
and the file show, never an email address, a phone number, a street address
or a church id.

- [ ] (owner, after PR 2a) **7.** As an owner or admin, open **4 Review & send**. The **Printed bulletin** card says "The church's details, the people who lead and the service time come from the bulletin settings." and, above the download buttons, lists "Not filled in: …" (before anything is saved: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist); under the downloads is a **Bulletin settings** button. Tap it: the **Bulletin settings** page opens.
- [ ] (owner, after PR 2a) **8.** Fill in the address (two lines), the phone, email, website and Facebook name, the service time and the three people, and tap **Save settings**: "Bulletin settings saved". Reload the page: everything is still there. Back on **Review & send** the "Not filled in" line is gone.
- [ ] (owner, after PR 2a) **9.** Tap **Download printed bulletin**: the cover shows the address lines, the phone, the email, the website and "FB: …"; page 1's header names the three people ("…, Worship Leader", "…, Liturgist", "…, Organist"), the date line ends with the service time, and each part shows its leader's name on the right, as in the sample. The prelude, the postlude and the announcements still show [placeholders] (the Bulletin step comes in PR 2b). Tap **Download Word version**: its cover and page 1 show the same details and names.
- [ ] (owner, after PR 2a) **10.** On **Bulletin settings**, under **Each part**, change who leads one part (for example the Sermon) and switch **Stands** for one part; change the stand note or the Gloria Patri words; save and download again: the bulletin follows each change.
- [ ] **11.** Clear the phone and save: the cover leaves the phone out (no empty line and no [placeholder]), and the card lists "Not filled in: phone."
- [ ] **12.** Signed in as a plain member of the same church: **Bulletin settings** shows "Only admins can edit the bulletin settings. You can read them below." and the settings as plain text (no fields, switches or **Save settings**), each part with who leads it and whether the congregation stands; the member's printed bulletin shows the same details.
- [ ] (owner, after PR 2a) **13.** At 375 px: no sideways scroll on **Bulletin settings**; every field, each part's leader and **Stands**, **Save settings** and **Back to Review & send** are easy to tap (44 px).
- [ ] **14.** After saving the settings, step 1's default translation and the Hymns step's hymnal are unchanged (saving keeps the church's other settings).
- [ ] **15.** On **Bulletin settings**, change a field without saving and tap **Back to Review & send**: "Discard unsaved changes?" asks first; **Keep editing** stays with the change, **Discard changes** goes back. Reloading the tab with a change unsaved shows the browser's own warning.
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md docs/superpowers/specs/2026-10-02-printed-bulletin-design.md | grep '^+' | grep -c '—'` then `git diff --stat`
**Expected:** `89 passed in <t>s`; `4`; `0`; ` docs/manual-verification.md                          | 20 +++++++++++++++++++-`, ` .../specs/2026-10-02-printed-bulletin-design.md      |  4 +++-`, ` 2 files changed, 22 insertions(+), 2 deletions(-)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md docs/superpowers/specs/2026-10-02-printed-bulletin-design.md
git commit -q -m "Docs: printed bulletin PR 2a manual checks" -m "docs/manual-verification.md gains \"### Printed bulletin PR 2a: bulletin
settings\" under \"## Printed bulletin\": the owner's phone check after
PR 2a (the card, the page, the PDF and the Word version with the
settings, a change, the page at 375 px) and the agent's checks (a blank
field, a member, the church's other settings kept, the leave guard).
PR 1's item 2 and the spec's \"Data model\" sentence no longer say a
missing value prints a placeholder." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1385 passed, 16 skipped`; frontend `672 passed` in 85 files.

### Task 8: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
git merge-base --is-ancestor 350f9a5 origin/main; echo "PR 1 record on main: $?"
ls backend/migrations/versions | grep -c '^0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `PR 1 record on main: 1` (it rides along: Step 3's list has `M docs/ops-runbook.md`; `0` if a records PR merged it meanwhile, and then that line is absent); `5`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 8)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the frontend three times, types, lint, the build, a sample booklet**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|bulletin-settings")
(cd backend && ../.venv/bin/python -c "
import datetime, bulletin_settings as bs, printed_bulletin as pb, printed_pdf, printed_docx
from service_output import ResolvedService, ResolvedHymn
r = ResolvedService(service_date=datetime.date(2026, 10, 4), hymns={'opening': ResolvedHymn('God Is Here!', 409), 'response': None, 'closing': None}, liturgy={'call_to_worship': 'Leader: Lift up your hearts. People: We lift them up.'}, sermon_title='Who Said?')
s = bs.read({'bulletin': {'address_lines': ['100 Example Street', 'Springfield, ST 00000'], 'phone': '(555) 010-0100', 'email': 'office@example.com', 'website': 'example.com', 'facebook': 'Example Church', 'service_time': '10:30 a.m.', 'worship_leader': 'Rev. Alex Example', 'liturgist': 'Sam Sample', 'organist': 'Jordan Doe'}})
ps = pb.PrintedService('Example Church', r, pb.Reading('Psalm 25:1-9', 'In you, Lord, I put my trust. ' * 30), pb.Reading('Matthew 21:23-32', 'And he answered. ' * 120), 'World English Bible (WEB)', s)
open('<scratch>/printed2a-sample.pdf', 'wb').write(printed_pdf.render_pdf(ps)); open('<scratch>/printed2a-sample.docx', 'wb').write(printed_docx.render_docx(ps)); print('sample written')
")
```

**Expected:** `1395 passed, 16 skipped in <t>s`; three times ` Test Files  85 passed (85)` and `      Tests  675 passed (675)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s`, a route line for `/bulletin-settings`, and no `Error` (a font `Failed to fetch` only: say so and rely on CI); `sample written`. Open the sample PDF and look at it: the cover with the two address lines, the phone, the email, the website and "FB: Example Church"; page 1's header with the three people and "10:30 a.m." across from the date; "Sam Sample" on the right of the Call to Worship and "Rev. Alex Example" on the Sermon; the prelude still "‘[Prelude title]’" with "Jordan Doe". Attach both samples to the owner's message in Step 4 if the channel allows files, else describe them.

- [ ] **Step 3 (agent): The API files match, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/bulletin_settings.py backend/printed_bulletin.py backend/usecases/church_bulletin.py backend/usecases/documents.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations backend/db .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); `imports grep exit 1`; `raw html grep exit 1`; exactly these paths (without `M docs/ops-runbook.md` when Step 1 printed `0`):
```
M	backend/api/main.py
A	backend/api/routes/bulletin_settings.py
A	backend/bulletin_settings.py
M	backend/printed_bulletin.py
M	backend/printed_docx.py
M	backend/printed_pdf.py
M	backend/repos/churches.py
A	backend/tests/test_api_bulletin_settings.py
M	backend/tests/test_api_printed.py
A	backend/tests/test_bulletin_settings.py
M	backend/tests/test_church_settings.py
M	backend/tests/test_no_streamlit_in_core.py
M	backend/tests/test_printed_bulletin.py
M	backend/tests/test_printed_render.py
A	backend/usecases/church_bulletin.py
M	backend/usecases/documents.py
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-02-printed-bulletin-2a.md
M	docs/superpowers/specs/2026-10-02-printed-bulletin-design.md
A	frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx
M	frontend/src/components/builder/builder-shell.test.tsx
M	frontend/src/components/builder/liturgy/liturgy-step.test.tsx
M	frontend/src/components/builder/review/printed-card.tsx
M	frontend/src/components/builder/review/review-send-step.test.tsx
A	frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx
A	frontend/src/components/bulletin-settings/bulletin-settings-page.tsx
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/types.ts
A	frontend/src/lib/bulletin-settings.test.ts
A	frontend/src/lib/bulletin-settings.ts
M	frontend/src/lib/church.test.ts
M	frontend/src/lib/church.ts
A	frontend/src/lib/queries/bulletin-settings.ts
M	frontend/src/lib/queries/keys.test.ts
M	frontend/src/lib/queries/keys.ts
M	frontend/src/test/fixtures/index.ts
```
`0`; the subjects oldest first: `Runbook: printed bulletin PR 1 record (owner's phone check; print test pending)` (when it rides along), `Spec: printed bulletin PR 2 planning answers (owner, 2026-10-02: split into 2a and 2b)`, the plan commits (`WIP plan: printed bulletin PR 2a (bulletin settings)`, `Plan: printed bulletin PR 2a (bulletin settings)` and any later plan commit), then T1-T7's seven subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> The bulletin settings (printed bulletin PR 2a) are verified on this machine: backend 1395 passed, 16 skipped (1357 before); frontend 675 tests in 85 files (660 before), three runs in a row; typecheck, lint and the production build are clean. It adds two API routes (`GET` and `PUT /church/bulletin-settings`), no database change and no new package. On step 4 the Printed bulletin card now lists what is not filled in and has a "Bulletin settings" button; that page holds your church's address, phone, email, website and Facebook name, the service time, the worship leader, liturgist and organist, who leads each part and which parts the congregation stands for, the stand note and the Gloria Patri words. Admins edit them (other members see them as a plain list); everyone's printed bulletin uses them, and a blank one prints nothing. The prelude, postlude and announcements stay as [placeholders] until the Bulletin step (PR 2b). May I open the pull request as a **draft** titled "Printed bulletin PR 2a: bulletin settings", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/printed2a-pr-body.md" <<'BODY'
Printed bulletin PR 2a: the church's standing bulletin settings, printed at once (PR 2 planning answers of 2026-10-02). Spec: docs/superpowers/specs/2026-10-02-printed-bulletin-design.md. Plan: docs/superpowers/plans/2026-10-02-printed-bulletin-2a.md. No database change (the settings live in churches.settings["bulletin"]), no draft change, no new package or variable.

- bulletin_settings (pure): the contact lines, the service time, the worship leader, liturgist and organist, who leads each part, the stars, the stand note and the Gloria Patri words; read tolerantly with PR 1's sample values as the defaults and every detail blank until saved.
- GET /church/bulletin-settings (any member) and PUT (owners and admins; the role 403 otherwise): the whole object, validated and cleaned, stored in one locked read-modify-write that keeps every other settings key; the later of two saves wins.
- printed_bulletin: the cover, the header, each part's leader and star, the time, the stand note and the Gloria Patri words come from the settings; a blank one prints nothing. The weekly fields keep PR 1's placeholders until PR 2b.
- /bulletin-settings: the page (admins edit, members read), linked from the Printed bulletin card, which now lists what is not filled in.
- docs/manual-verification.md: "### Printed bulletin PR 2a: bulletin settings".

Later: PR 2b (the Bulletin step, the weekly fields, services.bulletin with migration 0006_services_bulletin), PR 3 (the cover picture), 6a (the panel moves into Settings).

Tests: backend 1357 → 1395 passed, 16 → 16 skipped; frontend 660 → 675 in 83 → 85 files

After merge (Task 9): a short check on the owner's phone, then a "Printed bulletin PR 2a record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Printed bulletin PR 2a: bulletin settings" \
  --body-file "<scratch>/printed2a-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1395 passed, 16 skipped`, backend-postgres `16 passed, 1395 deselected`, frontend `675 passed` in 85 files. Then send: "PR #<N> is green: backend 1395 passed, 16 skipped; 675 frontend tests in 85 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_bulletin_settings.py` | T1 |
| `test_printed_bulletin.py`, `test_printed_render.py` | T2 |
| `test_api_bulletin_settings.py`, `test_api_printed.py`, `test_no_streamlit_in_core.py`, `test_church_settings.py`, `test_openapi_contract.py`, `test_route_guards.py` | T3 (`test_api_printed.py`'s first test: T2) |
| `bulletin-settings.test.ts`, `keys.test.ts`, `church.test.ts` | T4 |
| `bulletin-settings-page.test.tsx` | T5 |
| `review-send-step.test.tsx`, `builder-shell.test.tsx`, `liturgy-step.test.tsx` | T6 |
| `test_slice1_docs.py`, `test_docs.py` | T7 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, printed bulletin PR 2a final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1395 passed, 16 skipped`; frontend `675 passed` in 85 files.

### Task 9: Merge, the owner's phone check (four steps), the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate (production stays at `0005_services_extras`); Railway serves the two routes, Vercel the page and the card. The owner's check is **one step at a time** (send one, wait for the report or "next"), on the phone, on the production URL, in the owner's own church, signed in as its owner. The details the owner types are the church's own public details; they are stored in the church's settings, never in the repo or the record. The agent writes each result into `<scratch>/printed2a-t9-results.md` (not committed). Record what the page and the files showed, never a token, an email address, a phone number, a street address, a church id or a church member's name.

**Files:** Modify (the records PR, Step 8): `docs/ops-runbook.md`: insert `### Printed bulletin PR 2a record` right before `## Backups` (after the last record above it, today the "Printed bulletin PR 1 record" table, whose last row starts `| Follow-ups | Next: printed bulletin PR 2`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (printed bulletin PR 2a, the bulletin settings) is ready, green and up to date with main. There is no database change. One thing to know first: from the moment it is live, the printed bulletin leaves out the church's details, the names and the service time until you fill them in on the new Bulletin settings page (the card will list them); the first check step does that. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about three minutes for Railway and Vercel before Step 2; a failed deploy keeps the old version running (Step R).

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 4: the card and the page (manual-verification items 7 and 8)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. Open your service on **4 Review & send**. In the **Printed bulletin** card, above the two download buttons, is there a line "Not filled in: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist.", and under the buttons a **Bulletin settings** button? Tap it. Fill in your church's address (one line per line, as on your bulletin), phone, email, website, Facebook name, the service time (as you print it, for example "10:30 a.m."), and the worship leader, liturgist and organist. Leave **Each part** and **Printed words** as they are for now. Tap **Save settings**: does "Bulletin settings saved" show? Pull down to reload: is everything still there? Then tap **Back to Review & send**: is the "Not filled in" line gone?

Record each answer (not the values typed). **If Save fails**, record the message and stop: it is a follow-up for the owner to decide; the downloads are unaffected.

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 4: the printed bulletin (item 9)**

> Tap **Download printed bulletin** and open the PDF. Is your address, phone, email, website and "FB: …" on the cover under the picture's box? Does page 1 name your worship leader, liturgist and organist under the church's name, with the service time on the right of the date line? Are the names on the right of the parts as on your bulletin (the liturgist from the Welcome through the First Reading, the worship leader from the New Testament Reading through the Offertory Prayer, the organist on the Prelude and Postlude)? The prelude, postlude and announcements still show [placeholders] until the next PR; is anything else missing or wrong compared with your bulletin? Then tap **Download Word version** and open it: does its cover and first page show the same details and names?

Record the answers and any difference the owner names (each a follow-up for the record, 2b's list or the owner to decide).

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 4: a change (item 10)**

> Back on **Bulletin settings**, under **Each part**, pick one change you would really make (for example who leads the Sermon, or whether the congregation stands for a part), and if your church words the stand note or the Gloria Patri differently, change that too. Save, then download the printed bulletin again: does it follow your change? If nothing needs changing, change one thing, check it, and change it back.

- [ ] **Step 5 (OWNER, then agent): Phone, step 4 of 4: the page on the phone (item 13)**

> On **Bulletin settings**: does the page fit the screen with no sideways scrolling, and are the fields, each part's leader and **Stands**, **Save settings** and **Back to Review & send** easy to tap?

- [ ] **Step 6 (agent): The agent's own checks (items 11, 12 and 14)**

On the production URL, in a test church the agent may change (one of the two slice 1 test churches the owner kept, never the owner's own church), signed in as its owner if the session has a test account, else skipped and recorded as "not run": item 11 (clear the phone, save, download: no phone line, "Not filled in: phone."), item 14 (step 1's translation and the Hymns step's hymnal unchanged after a save). Item 12 needs a plain member's sign-in; record "not run" unless the owner offers one. Then fill in the test church's phone again as it was.

- [ ] **Step 7 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/printed2a-t9-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 8 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it (today `### Printed bulletin PR 1 record`). Insert, right before `## Backups` (one blank line on each side):

```markdown
### Printed bulletin PR 2a record

Printed bulletin PR 2a (the church's standing bulletin settings:
`GET`/`PUT /church/bulletin-settings`, stored in `churches.settings`
under `"bulletin"`; the Bulletin settings page, admins edit and members
read; the printed bulletin prints them, a blank one prints nothing; the
Printed bulletin card lists what is not filled in) merged as PR #<N>, the
first half of printed bulletin PR 2 (PR 2 planning answers of
2026-10-02). No database change and no new package; production stays at
`0005_services_extras`. The owner's check was four steps on a phone,
covering the "(owner, after PR 2a)" items of `docs/manual-verification.md`
→ "Printed bulletin". The church's details the owner typed are in its
settings, not here. No token, email address, phone number, street
address, church id or member's name is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success | <date> |
| 1. The card and the page (phone: <phone and browser>) | <"Not filled in" listed the nine fields; the Bulletin settings page opened; Save settings showed "Bulletin settings saved"; the values were still there after a reload; the line was gone on Review. / …> | <date> |
| 2. The printed bulletin | <The cover's contact lines, the header's three people and the service time, and the parts' leaders as the sample; music and announcements still [placeholders]; the Word version the same. / Differences: …> | <date> |
| 3. A change | <Changed <what>; the bulletin followed. / …> | <date> |
| 4. The page on the phone | <No sideways scroll; easy to tap. / …> | <date> |
| Agent checks | <Items 11 and 14 in a test church: <results>. / Not run: <why>.> Item 12 (a member): <result / not run> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: printed bulletin PR 2b (the Bulletin step: prelude and postlude, announcements, pasted reading text, carry forward, migration `0006_services_bulletin`), then PR 3 (the cover picture), 6a (the panel moves into Settings). Still open from PR 1: the print test at the church | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye: the second grep below catches an email address and a "(555)"-style phone, not a street address or a phone number written another way, so check that no street address, phone number, church id or member's name is in it. Then (not replayed):

```bash
sed -n '/^### Printed bulletin PR 2a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Printed bulletin PR 2a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|\([0-9]{3}\)'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: printed bulletin PR 2a record (merged; owner's phone check)" -m "Records printed bulletin PR 2a (PR #<N>): the merge and CI on main and
the owner's four-step phone check (the card and the page, the printed
bulletin with the settings, a change, the page on the phone). No token,
email, phone number, address, church id or member's name is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 9 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The printed bulletin PR 2a record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: printed bulletin PR 2a record" \
  --body "Records printed bulletin PR 2a (PR #<N>) in docs/ops-runbook.md → Printed bulletin PR 2a record: the merge and the owner's four-step phone check. No token, email, phone number, address, church id or member's name is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Printed bulletin PR 2a is live and recorded; <n> follow-ups. Next: the PR 2b plan (the Bulletin step)."

- [ ] **Step R (only if the release must come out): Revert**

Code only (no schema to undo). On the owner's yes for each outward command: a branch `claude/revert-printed-2a` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert printed bulletin PR 2a (PR #<N>)" with the trailer, both suites (`1357 passed, 16 skipped`; `660 passed` in 83), a PR, CI, and the merge on the owner's yes; record it in the record. The printed bulletin then prints PR 1's [placeholders] again. The saved `"bulletin"` key stays in each church's settings, unread and harmless (nothing else reads it), and is used again when the PR comes back; remove it only on the owner's word.

Expected counts after this task: backend `1395 passed, 16 skipped` on `main`; frontend `675 passed` in 85 files. The records PR adds no test.

---
## Build notes

**How this plan was written (2026-10-02).** Each task's code was built and run in a throwaway worktree of `f2bddda` (the repo's `.venv`, a symlink to `frontend/node_modules`); the directives were then generated from that worktree against `f2bddda` (a new file as **Create**, an addition at the end of a file as **Append**, every other change as **In … replace** with just enough context to occur once in the file as it stands at that point). No package, variable or migration was added. While building:
- **The settings are read where the name already is.** `build_printed` reads `churches.get_church` once; `church_bulletin.read_settings(church["settings"])` costs no query. The Word renderer did not change: an empty contact list and a date line with no `right` already rendered. The PDF renderer changed only on the cover (the plan review's fix: the contact lines shrink to fit).
- **PR 1's standing constants left `printed_bulletin`** (`WORSHIP_LEADER`, `LITURGIST`, `ORGANIST`, `SERVICE_TIME`, `CONTACT_LINES`, `STAND_NOTE`, `STARRED`, `LEADERS`); the sample's stars, roles, stand note and Gloria Patri words became `bulletin_settings`' defaults (`DEFAULT_*`, `GLORIA_PATRI`). The weekly placeholders (the prelude and postlude, the cover picture, the announcements) stay in `printed_bulletin`.
- **The PUT body is cleaned by the same `read_settings` as GET and the print path** (`archive._xml_safe`, then `bulletin_settings.read`), so what is stored is always what GET answers, GET's tolerant read cuts an over-long stored text to its limit, and no stored text can make the Word version fail.
- **The page's form keeps a baseline and the edits** (`SettingsForm` mounts once the fetch made on opening is back); newer data rebases it during render (React's "adjust state when a prop changes" pattern, which the lint rules accept), and the church layout keys its children by the church id, so a church switch remounts the page and never carries one church's form into another's.

**Plan review fixes (2026-10-03).** The adversarial review of `c0a6554` found no Critical issue, two Important and twelve Minor ones; the owner's decisions on them are applied here (the owner-visible ones are in "Questions for the owner" as recommended answers):
- **Stale form (Important):** the page fetches the settings again on opening (`refetchOnMount: "always"`) and shows the form only after that fetch; newer server data rebases the form by 6a's rule (`rebaseForm`: an untouched value takes the new one, an edited one stays). T4 tests `rebaseForm` and `isDirty`; T5 tests a cached older copy, a refetch while editing (untouched fields and stars update, edited ones stay, the PUT carries both). Clarifications 6 and 10.
- **Cover overflow (Important):** lower limits (address lines 60, email 100, website 100, Facebook name 60; phone, service time and names as they were) and the PDF's contact lines in a `KeepInFrame(mode="shrink")` sized to the room left (T2, `printed_pdf.py`, now a modified path); T2's `test_the_longest_details_still_fit_the_cover` (every field at its limit, a church name of two lines: the order of worship still starts on page 1; it fails without the shrink). Word: by estimate it fits at the limits; not checkable by a test here (no layout engine; LibreOffice Writer is not installed), so documented in clarification 12 and Risks, and the owner's phone check now opens the Word version. Risks' "Long values" line rewritten.
- **Leave guard:** `beforeunload` while the form has unsaved edits, and "Discard unsaved changes?" (6a's words) on **Back to Review & send**; the app has no in-app navigation guard yet, so the header links, nav and switcher are 6a's (Risks). T5 test.
- **Stand note:** printed only when a printed part carries the star (T2; a case in `test_a_blank_setting_prints_nothing`).
- **"Not filled in" above the downloads** (with the settings sentence); the button stays under them. T6's test checks the order.
- **Typed while saving:** after a save, the fields as sent take what was stored and a field changed meanwhile keeps the typed value (the same rebase, with the form as sent as the baseline). T5 test.
- **Field errors:** the address check and a 422's named fields show under the field in the app's error style (`text-destructive`, `role="alert"`, `aria-invalid`, `aria-describedby`), and focus moves there. T5 test (a 422 on the phone).
- **Members:** a plain read-only summary (text, no greyed-out controls). T5 test.
- **One line:** every text but the Gloria Patri words refuses control characters (`PUT` 422 naming the field; two new 422 cases in T3).
- **Word-safe print path:** `church_bulletin.read_settings` applies `archive._xml_safe` to the stored values for GET and the printed bulletin (T3's `test_a_stored_control_character_still_prints_in_word`, a 500 without it).
- **Lock guard:** `set_bulletin_settings` joins `test_settings_writes_lock_the_church_row` (T3; `test_church_settings.py` is a modified path).
- **Docs:** T7 amends PR 1's item 2 and S's "Data model" sentence (the spec's sentence now says a missing value reads as its default and a blank one prints nothing); item 9 opens the Word version; item 15 (the leave guard); the record's privacy check names street addresses and phone numbers.
- **Polish:** the phone, email and website keyboards (`inputMode`, autofill off, no autocapitalize or spellcheck on email and website); 6a's verb "edit" ("Only admins can edit the bulletin settings. You can read them below."); `isAdmin`'s test in its own `describe`. Long leader names: accepted (Risks). The older `_merge_settings` crash when `churches.settings` is not an object: left, listed under "Follow-ups".
- Counts: backend 1381 → **1385** (T2 +3, T3 +17), frontend 668 → **672** (T4 +5, T5 +6); 35 → **37** paths (`printed_pdf.py` and `test_church_settings.py` modified).

**Replay of the finished plan (2026-10-03, after the review fixes).** The directives of T1-T7 were applied in order (by `replay.py`, which parses the plan's **Create**, **Append** and **In … replace** blocks step by step) onto a fresh detached worktree of the branch head (`c37dfca`: `350f9a5`, `f2bddda` and the plan's commits on `origin/main` `d79f301`), with the repo's `.venv` and a hard-linked copy of `frontend/node_modules` (Turbopack's production build refuses a `node_modules` symlink that points outside the project: "Symlink [project]/node_modules is invalid"; vitest, tsc and eslint accept the symlink). Each step's commands were run as written and each task committed with its Step 5 (Step 3 for T7) block:
- All 83 directives applied (T1 1 + 1, T2 20 + 15, T3 5 + 8, T4 7 + 5, T5 1 + 2, T6 8 + 7, T7 3); every Replace anchor occurred exactly once. After T7, `backend`, `frontend/src` and the two docs equaled the build worktree's (`diff -r`: empty).
- Baselines before T1: backend `1357 passed, 16 skipped`; frontend `660 passed` in 83 files.
- Every "see it fail" output is quoted from this replay (times as `<t>`): T1 the collection error; T2 `12 failed, 13 passed` (the `settings` keyword, PR 1's cover, the cover at every limit); T3 `18 failed, 12 passed` (404s, the printed settings, the Word-safe print, the import) and `test_church_settings.py`'s collection error; T4 2 failed and the new file not loading; T5 the file not loading ("no tests"); T6 the one new test.
- Every count matched the table: backend 1365, 1368, 1385 (16 skipped throughout); T1's file `8 passed`, T2's files `25 passed`, T3's `48 passed`; frontend 665 in 84, 671 in 85, 672 in 85; T4's files `13 passed`, T5's `6 passed` and T6's `77 passed` three times each, no flaky run; typecheck 0 and lint 0 after T3-T6. The OpenAPI export and `gen:api` gave `2 files changed, 522 insertions(+)` and `1`; T7 `89 passed`, `4`, `0`, `2 files changed, 22 insertions(+), 2 deletions(-)`.
- T8 Steps 1-3: `5` revisions (head `0005_services_extras`); both suites (backend `1385 passed, 16 skipped`; frontend `672 passed` in 85 files three times); the production build `✓ Compiled successfully` with a `○ /bulletin-settings` route and no `Error`; the sample snippet wrote both files, and the PDF's text shows the two address lines, the phone, the email, the website and "FB: Example Church" on the cover, the three people and "10:30 a.m." in page 1's header, "Sam Sample" on the Call to Worship, "Rev. Alex Example" on the Sermon and "Jordan Doe" on the prelude, still "‘[Prelude title]’"; the OpenAPI export and `gen:api` changed nothing after T3's commit; the imports and raw HTML greps exit 1; the 37 paths exactly; no migration, `backend/db`, workflow, package or Streamlit path; every commit has the trailer; no em dash in any added line of code, test or docs.
- Fixed in the plan by the first replay (2026-10-03, before the review): T2 Step 4's constants grep had no `-w`, so `bulletin_settings`' `DEFAULT_LEADERS`, `DEFAULT_STARRED` and `DEFAULT_STAND_NOTE` matched (exit 0); with `-w` it exits 1 as quoted. Fixed by this replay: T3 Step 2 runs `test_church_settings.py` on its own (its collection error would otherwise interrupt the other three files); the T2, T3 and T7 commit blocks stage `printed_pdf.py`, `test_church_settings.py` and the spec.
- Not run while planning: the pushes, the PR and CI, the merge, Railway's and Vercel's deploys and the owner's phone check (T9).

**Build review fixes (2026-10-03).** The code review of the build (`5a234ad..033f00d`) found no Critical issue, two Important and six Minor ones; the owner's desktop Word check of the 2a sample added one. Each fix has a test that failed before it:
- **I1, GET answered 500 for a stored control character:** `bulletin_settings.read` now makes every text but the Gloria Patri words one line (each run of control characters, C1 controls and U+2028/U+2029, with the spaces around it, becomes one space; then trimmed and cut), so GET always answers something PUT accepts, and a stored line break no longer prints an extra cover or header line. The Gloria Patri words keep their lines (only `_xml_safe`'s Word-unsafe characters are handled). Tests: `test_every_text_but_the_gloria_patri_words_reads_as_one_line`, `test_a_stored_control_character_reads_as_a_space_and_put_takes_it_back`; `test_a_stored_control_character_still_prints_in_word` now expects the phone on one line.
- **I2, an older read could overwrite a save:** the save's `onSuccess` cancels the settings query before `setQueryData` (as `membership.ts` does). T5 test "keeps what was saved when a read that started before the save answers after it".
- **M1, a long church name pushed page 1 to side 2:** the PDF cover adds the contact block (and the space above it) only when there are contact lines and room for them, with no 30 pt floor. Test: `test_a_long_church_name_still_leaves_page_1_on_side_1` (145 characters with contact lines; 150, 6 title lines, with and without them; names may have 200). Under a name of 6 title lines or more there is no room under the picture, so the contact lines are left off the PDF cover rather than pushing the order of worship off side 1.
- **M2:** the stand note follows only an element the settings star (`Line.starred`), not a custom element whose label starts with "*". Test: `test_a_custom_element_marked_by_hand_does_not_bring_the_stand_note`.
- **M3:** the reload warning also sets `event.returnValue = ""`. T5 test.
- **M4:** a Ctrl, Cmd, Shift, Alt or middle click on **Back to Review & send** works as a link click, with no discard dialog. T5 test.
- **M5:** PUT's one-line check also refuses U+2028, U+2029 and the C1 controls (U+0085 among them) with the same 422 (`bulletin_settings.NOT_ONE_LINE`, shared with the read); OpenAPI regenerated (the pattern only). Test: `test_a_unicode_line_break_is_not_one_line` (three cases).
- **M6:** clarification 7 now says address lines up to 60.
- **Owner's desktop Word check (2026-10-03):** the Word cover's picture-box table sat at the left margin, off center under the centered name and contact lines; it is now centered (`w:jc` center in `tblPr`, in the schema's order). Nothing else on the Word cover changed. Test: `test_the_word_cover_picture_box_is_centered`. `printed_docx.py` is now a modified path (38).
- Counts: backend 1385 → **1395** passed, 16 skipped; frontend 672 → **675** in 85 files (three runs); typecheck 0, lint 0, the production build clean; the OpenAPI export and `gen:api` changed nothing after the fix commit.

## Spec coverage

| Owner answer or S item | Task(s) and tests |
|---|---|
| Planning answer 1: 2a is the settings, the panel, `GET`/`PUT`, printed at once; no migration, no draft change | T1-T6; T8 Step 3 (no migration, `backend/db`, package or Streamlit path; 5 revisions) |
| Planning answer 2: admins only change them; every member's bulletin uses them | T3 `test_a_member_cannot_change_them`, `test_an_admin_saves_them_whole_and_the_other_settings_stay` (admin and owner), `test_the_church_s_bulletin_settings_print_for_every_member`; T5 "shows a member the settings as plain text, with no fields and no Save" |
| Planning answer 3: a blank field prints nothing; the card lists what is empty | T2 `test_a_blank_setting_prints_nothing` (and no stand note without a printed star); T3 `test_the_church_s_bulletin_settings_print_for_every_member` (a blank phone and organist); T4 "lists the blank standing fields in the page's order"; T6 "lists the bulletin settings still blank and links to them" |
| Answer 2 (standing fields: address, phone, email, website, Facebook; worship leader, liturgist, organist; stand note and stars; Gloria Patri words) and S "What prints where" | T1 (the fields and defaults); T2 `test_the_order_of_worship_follows_the_outline_with_the_sample_s_parts`, `test_each_element_prints_as_the_sample`, `test_the_cover_and_the_back_page`, `test_the_settings_choose_the_stars_the_leaders_and_the_words`; T2 render tests (PDF halves, Word tab stops) |
| S "Data model": `churches.settings["bulletin"]`, read tolerantly | T1 `test_nothing_stored_reads_the_defaults` (6 cases), `test_a_field_of_the_wrong_type_is_its_default_and_a_long_text_is_cut`; T3 `test_a_stored_value_of_the_wrong_shape_reads_as_the_defaults`; clarification 5 (the default, not a placeholder) |
| F §1.7: settings writes read-modify-write under the row lock, other keys untouched | T3 `test_an_admin_saves_them_whole_and_the_other_settings_stay` (`bible_translation`, `default_hymnal` kept), `test_church_settings.py::test_settings_writes_lock_the_church_row` (the new write loads the row `FOR UPDATE`); clarification 6 |
| API: shapes, 422s, cleaning, isolation | T3 `test_what_is_saved_is_trimmed_and_in_order`, `test_a_bad_body_is_a_422_naming_the_field` (8 cases), `test_every_field_is_required`, `test_only_members_of_the_church`; `test_route_guards.py`, `test_openapi_contract.py` unchanged and passing |
| Answer 8: the settings panel, folded into 6a later | T5 (the page and its six tests); clarification 2 |
| 6a's rules for settings forms (baseline and rebase; leave guard; inline 422 fields) | T4 "rebases the form on newer data…"; T5 "opens on the settings fetched now, and newer data updates only the fields not edited", "keeps what is typed while saving…", "asks before leaving with unsaved edits", "checks the address before saving, and shows a field the server refuses…"; clarification 10 |
| The cover fits at every limit (plan review) | T2 `test_the_longest_details_still_fit_the_cover`; clarifications 4 and 12 |
| One printed line per text; Word-safe stored values (plan review) | T3 `test_a_bad_body_is_a_422_naming_the_field` (the line-break and tab cases), `test_a_stored_control_character_still_prints_in_word` |
| Weekly fields stay PR 1's until 2b | T3 `test_the_church_s_bulletin_settings_print_for_every_member` (the prelude and "Coffee Hour: [Name]"); clarification 8 |
| F §4.8, §4.9 (44 px, forms, Select, read-only) | T5 (`h-11`, the select and switch names, `readonly`, the address check and focus); T6 (the link's `h-11`) |
| Layering (no FastAPI or Streamlit below the API) | T3 `test_no_streamlit_in_core.py` (two modules added); T8 imports grep |
| OpenAPI and types regenerated | T3 Step 4; T8 Step 3; `test_openapi_contract.py` |
| Answer 10: a guided phone check after each PR | T9 Steps 2-5; `docs/manual-verification.md` "### Printed bulletin PR 2a: bulletin settings" (T7) |

S items **not** in 2a (planning answer 1): the Bulletin step, the weekly fields (prelude and postlude, announcements, per-week leaders, pasted reading text), carry forward, the draft's `bulletin` (v3), `services.bulletin` and migration `0006_services_bulletin` (all 2b); the cover picture (PR 3).

## Follow-ups (not in 2a)

- `repos.churches._merge_settings` raises `TypeError` (a 500) if `churches.settings` is ever not an object (a list or a string written by hand). Pre-existing, shared with the translation and prompts writes; a small fix for a later PR (read a non-object as `{}`), with a test.
- The leave guard covers this page's Back link and a reload or close of the tab only; 6a's `useLeaveGuard` covers the header links, the nav and the church switcher for every settings page.
- The Word version's cover is not shrunk; if a church's real details ever push it to a second page, PR 3 (the cover picture) is the place to measure and fix it.

## Questions for the owner

**Owner's answer (Beau, 2026-10-03): "all recommended, yes start building".** Questions 1-14 below are accepted as written and are binding for the build.

Your answers of 2026-10-02 (the ten answers, layout B, the PR 1 plan's twelve, and the eight PR 2 planning answers) are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended. Questions 11-14 come from the plan review of 2026-10-03.

1. **Where the settings live until Settings arrives (6a)** (clarification 2): a page of its own, "Bulletin settings", opened from a **Bulletin settings** button on the Printed bulletin card (and, in 2b, from the Bulletin step), with **Back to Review & send**. It is not in the top menu; 6a moves it into Settings. Recommended: accept.
2. **Members can open and read the settings, but not change them** (clarification 3): they see "Only admins can edit the bulletin settings. You can read them below." and the settings as a plain list of text (each part as, for example, "Sermon: Worship leader" or "Opening hymn: No one, congregation stands"), not greyed-out boxes and switches; no Save button. The button on the card shows for everyone. (The other choices: greyed-out controls, or hiding the page and the button from members.) Recommended: accept.
3. **Before anyone saves, the details print nothing** (clarification 5): from the day this goes live, the cover's address lines, the people in the header, the service time and the names beside the parts are left off (no more "[Street address]" or "[Worship leader]") until an admin fills them in, and the card lists them as "Not filled in". The first phone check step fills them in. (The other choice is to keep printing PR 1's [placeholders] until the first save.) Recommended: accept.
4. **What starts filled in** (clarification 5): who leads each part and which parts get the star start as your sample (the liturgist from the Welcome through the First Reading, the worship leader from the New Testament Reading through the Offertory Prayer, the organist on the Prelude and Postlude; stars on the three hymns, both sung responses, the Affirmation of Faith and the Benediction), the stand note starts as "Congregation stands if able", and the Gloria Patri as the traditional words. Recommended: accept.
5. **The prelude, postlude and announcements keep their [placeholders] until the Bulletin step (2b)** (clarification 8): your answer 3 makes a blank field print nothing, but these are filled on the Bulletin step, which comes next; leaving them out now would print a bulletin with no prelude line and an announcements page of bare headings. The card says "For now, the music and the announcements print as [placeholders]." Recommended: accept.
6. **The fields and how they print** (clarification 4): the address as up to three lines, each printed on the cover as typed; phone, email and website as typed, one line each; the Facebook name as "FB: {name}"; the service time as typed, across from the date; the three people as "{name}, Worship Leader", "{name}, Liturgist", "{name}, Organist"; the stand note printed at the end after a star (you type it without the star); the Gloria Patri words under "Gloria Patri". Every field but the Gloria Patri words is one line (a line break pasted into one is refused). Recommended: accept.
7. **Each part: who leads and whether people stand** (clarifications 10, 13): a list of the 21 parts (Prelude, Welcome and Announcements, …, Postlude, with the hymns named Opening hymn, Response hymn and Closing hymn as on the Hymns step), each with "No one", "Worship leader", "Liturgist" or "Organist", and a **Stands** switch for the star. Recommended: accept.
8. **Two admins saving at once: the later save wins** (clarifications 6, 10): there is no "someone else changed this" warning; but the page always opens on what is saved now, and while it is open, a newer save from elsewhere updates every field you have not changed (your own changes stay), so a save never puts back an older value you did not touch. Saving never touches your church's other settings (the default translation, hymnal, Benediction, rubric or prompts). Recommended: accept.
9. **The card's wording** (clarifications 9, 15): "The church's details, the people who lead and the service time come from the bulletin settings.", then "Not filled in: …" when any is blank (address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist, stand note, Gloria Patri words), then, under the downloads, the **Bulletin settings** button; and "For now, the music and the announcements print as [placeholders]." in place of PR 1's line. Recommended: accept.
10. **The page's wording** (clarifications 10, 15): "Bulletin settings", "What every printed bulletin uses. A field left blank is left off the bulletin.", the groups Church details, Service, Who leads, Each part and Printed words, their help lines, **Save settings** and "Bulletin settings saved". Recommended: accept.
11. **Shorter limits for the cover's details** (clarifications 4, 12): each address line up to 60 characters, the email and the website up to 100, the Facebook name up to 60 (the phone stays 40, the service time 40, each name 100). Typical details fit easily; at these limits the PDF still fits the cover by printing the contact lines a little smaller when they would not fit, so the service always starts on page 1. (The other choice is the longer limits, 100, 254, 200 and 100, which would rely on the smaller print far more often.) Recommended: accept.
12. **The stand note prints only when a starred part prints** (clarification 4): "*Congregation stands if able" appears at the end only if at least one part on that week's bulletin has the star; with no stars, or when every starred part is left out that week, the note is left off. Recommended: accept.
13. **"Not filled in" above the download buttons** (clarification 9): the list of blank details sits with the card's other notes, above **Download printed bulletin**, so it is read before printing; the **Bulletin settings** button stays under the downloads. Recommended: yes.
14. **A warning before leaving with unsaved changes** (clarification 10): if you change something on Bulletin settings and tap **Back to Review & send** without saving, the page asks "Discard unsaved changes?" (**Discard changes** or **Keep editing**), and closing or reloading the tab shows the browser's own warning. Until Settings arrives (6a), the links at the top of the screen and the church switcher do not ask. Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T8); the merge on your yes, then four phone checks one at a time, and the records PR (T9).
