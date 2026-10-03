# Printed Bulletin PR 2b: the Bulletin Step

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the second half of printed bulletin PR 2 (PR 2 planning answer 1, 2026-10-02): **the Bulletin step and the week's own fields**, as **two PRs, backend first** (clarification 19): **PR 2b-1** (T1-T6: migration `0006_services_bulletin` with the owner's before and after steps, the API saving, opening and carrying the fields, the printed bulletin printing them; the builder unchanged, today's pages keep working) merges and deploys first; **PR 2b-2** (T7-T12: the draft v3, the Bulletin step, carry forward, the card) merges after 2b-1 is live and checked. After both merge, the Service Builder has five steps: a new optional step **4 Bulletin** sits between **3 Liturgy** and **5 Review & send**. On it a member fills in the prelude and postlude (title and composer); sees **Who leads** (the worship leader, liturgist and organist from the 2a Bulletin settings) and can change one of them for this week, or, behind **Change who leads a part**, one part's leader; fills in the announcements (ushers and counters, deacon of the week, coffee hour, this week's activities, prayers and concerns, items for collection, other announcements); and can paste a reading's text for a translation the app cannot fetch. A new draft starts from last week's music and announcements (the church's latest saved service dated before the draft's date), each such box marked "From last week. Check before printing." until it is edited or kept; the marks are saved with the service, and "Save as new service" treats a saved service as a new week the same way. The printed bulletin (PDF and Word version) prints all of it; a blank field prints nothing, the last [placeholders] for the music and the announcements are gone, and with every announcement blank the announcements page is left out (the cover picture's box stays until PR 3). The Printed bulletin card lists the week's blank fields and the boxes from last week not yet checked. The fields are saved with the service: the draft goes to version 3, `ServiceDraft.bulletin` is optional (a page from before 2b-2 keeps working and still prints PR 1's placeholders) and `services` gains one nullable JSON column in migration **`0006_services_bulletin`**, after the owner's backup, read-only counts and SQL preview (PR 2 planning answer 8). The Word working copies (`POST /documents`) do not change. No new package or variable; production Streamlit (branch `streamlit-frozen`) is untouched.

**Architecture:** Backend first, in its own PR. `0006_services_bulletin` (expand-only, batch mode as 0004 and 0005) adds `services.bulletin JSON NULL` (the model's column is `JSON(none_as_null=True)`, so a Python `None` is SQL NULL); `backend/migrations/README.md` gains "Before 0006_services_bulletin" with the owner's four steps, its SQL pinned by tests. `backend/service_bulletin.py` (new, pure) defines `ServiceBulletin` (`Music`, `Announcements`, this week's people, the part leaders, the pasted texts, `unchecked`), the tolerant `read` (a free text's every line break a newline, U+2028 and U+2029 included; a pasted reading's blank lines one paragraph break), `to_json`, `carried()` and `map_texts`. `printed_bulletin` prints the music, this week's people and part leaders (`WeekSettings`, the 2a settings with the week's changes over them), the announcements page (none when every announcement is blank; the PDF and Word renderers then leave the page out) and a pasted reading (no credit line for it; a fetched reading beside it gets its own); with no bulletin posted it prints PR 1's placeholders (`PLACEHOLDERS`). In the API, `ServiceDraft` gains an optional `bulletin` (`api/schemas.ServiceBulletin`, every field present, limits, no line-break check); `usecases.archive` cleans it (Word-safe), stores it (`POST` without it: NULL; `PUT` without it: kept), reads it back on `GET`, and `previous_bulletin` answers `GET /services/previous-bulletin?before=YYYY-MM-DD` (the music and announcements of the church's latest service dated before that date) through `repos.services.previous_service`; `usecases.documents.build_printed` prints the posted bulletin and fetches only the readings without pasted text. OpenAPI regenerated. Frontend (PR 2b-2): the draft v3 (`schema.ts`: `bulletin`, the step id "bulletin"; `migrate.ts`: 2 → 3 with an empty bulletin), `lib/draft/bulletin.ts` (the edits, carry forward a box at a time, "Save as new service" (`followSaveMode`), the payload with `unchecked`, "Not filled in" and "not checked yet"), the mapping (`bulletin` in the payload only when something is filled in, so a draft "Saved" before 2b stays "Saved"), the bodies (`serviceBody` always sends it, cut to the limits; `savedCopyFingerprint` reads it as the server stores it), the statuses ("Optional" or "n to check"; `isPristine`), `usePreviousBulletin`, the step (`components/builder/bulletin/`, route `/builder/bulletin`), the carry hook `useBulletinCarry` (the Bulletin step and the Printed bulletin card), the five-step bar, `/builder`'s fallback to Review for a step not in the bar, and the card's lines.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy 2, Alembic, reportlab 5 and python-docx (PR 1's renderers), pytest (SQLite; Postgres for `@pytest.mark.postgres`); Next 16, React 19, TypeScript 5, zod, Base UI, TanStack Query 5, Vitest 3 with Testing Library; openapi-typescript for `schema.d.ts`.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`: owner answers 2, 3, 5, 8; "PR 2 planning answers" 1 and 3-8 (binding); "What prints where"; "Scripture text"; "API"; "Data model" (weekly fields, carry forward); "The Bulletin step and the settings panel"; "Scope by PR".
- The PR 2a plan `docs/superpowers/plans/2026-10-02-printed-bulletin-2a.md` (the format model; its "Questions for the owner" 1-14, answered "all recommended" and binding: 1 the settings page and its link from the step, 4 the standing roles and stars, 5 the weekly placeholders until 2b, 9 the card's wording, which this PR changes as planned) and the 5a-2 plan `docs/superpowers/plans/2026-10-02-slice-5a2-saving.md` (the model for a production migration: the README's "Before 0005_services_extras" steps and its T9).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.3 (`ServiceDraft`), §1.5 (errors), §1.7 (`If-Match`), §2.2 (layers), §2.5 (logs), §3.1, §3.4, §3.5 (migrations: expand-only, the chain), §4.4 (keys), §4.6 (the draft: versioning, never destroy typed input), §4.7 (steps), §4.8 (forms, 44 px).
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `9c731e1` = `origin/main` `1b0b7a3` (PR #46, printed bulletin PR 2a) plus "Runbook: printed bulletin PR 2a record (owner's phone check)", then this plan's commits; 2026-10-03): backend `1395 passed, 16 skipped`; Postgres-marked `16 passed, 1395 deselected` (local Postgres 16); frontend `675 passed` in 85 files; typecheck and lint clean; Alembic head `0005_services_extras` (5 revision files, production too: runbook "Slice 5a-2 record"); 4 runbook owner markers. `ServiceDraft` (`api/schemas.py`) has `extra="forbid"`; `PUT /services/{id}` is a full replace; `GET /services/{service_id}` takes a UUID (a static path must be declared before it); `IsoDate` only checks the date shape when used as `Annotated[IsoDate, Query()]` (as `/lectionary/readings`). `draftToServicePayload` is what the "Unsaved changes" fingerprint hashes, and `serviceBody` is the body of every save and download. No frontend code calls a builder route that does not exist; `installFakeApi` fails a test on any request without a handler, so the three test files that render Review (`review-send-step`, `builder-shell`, `liturgy-step`) need the new route.
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch head (see "Build notes"). The plan was then reviewed (2026-10-03) and its fixes built and replayed the same way ("Plan review fixes" in "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -3` (or `| tail -1` where a step says so); the suite `.venv/bin/python -m pytest -q | tail -1`. Postgres-marked tests run only with `TEST_DATABASE_URL` set to a local, throwaway Postgres (`tests/pg_helpers.require_local_test_url`); without it they skip, and CI's `backend-postgres` job runs them (after `alembic upgrade head`, `alembic check`, `alembic downgrade base`, `alembic upgrade head`). Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes (T3, PR 2b-1), so T3 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand. T3 also adds the matching fixture and type names, so typecheck stays clean at every commit.
- No new package, no new variable. One migration, `0006_services_bulletin` (T1), whose `down_revision` is `0005_services_extras`.
- Branch `claude/slice-2-plan-4q33le`, at `9c731e1` plus this plan's commits (`WIP plan: printed bulletin PR 2b …`, `Plan: printed bulletin PR 2b (the Bulletin step)` and the later plan commits), then T1-T4 (PR 2b-1). After PR 2b-1 merges, the same branch is fast-forwarded to `main` (T6 Step 7), takes the 2b-1 record and then T7-T10 (PR 2b-2). Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes: PR 2b-1 only after T6 Steps 1-3 (backup, counts, SQL); PR 2b-2 only after PR 2b-1 is live and checked (T6 Steps 5-6; T11 Step 1 checks the live API).
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- Each PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes its tests line: PR 2b-1 `Tests: backend 1395 → 1425 passed, 16 → 17 skipped; frontend 675 in 85 files (unchanged)`; PR 2b-2 `Tests: frontend 675 → 698 in 85 → 87 files; backend 1425 passed, 17 skipped (unchanged)`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 16 and has no em dashes; existing copy keeps its own punctuation.
- **PR 2b-1 before PR 2b-2, and each tolerates the other** (clarification 19): nothing in T1-T4 changes a page, a component, the draft, a query or a request body (T5 Step 3 checks it); nothing in T7-T10 changes the server, the API files, a workflow or a package (T11 Step 3 checks it). PR 3 follows the same order.
- No church id, email address, token, database URL or real person's name, address, phone or email in any doc, commit, test or record. The tests use invented details only: "Example Church", "Rev. Alex Example", "Sam Sample", "Jordan Doe", "Pat Example", "Lee Sample", "Rev. Guest", "The Example family", "Morning Voluntary", "Festive Postlude", "For all who are ill.". None of the owner's sample bulletin's content enters the repo. Prayers and concerns can name people and their health: they live only in the service's bulletin, never in a log line, a commit or the record (clarification 15).
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action (the backup run included). Owner steps go one at a time, in plain words.

### How the file directives below read
As in the PR 2a plan: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written (top to bottom within a file, so an anchor is unique in the file as the previous directives left it). A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted.

### Baselines and counts
- Starting baselines: backend **1395 passed, 16 skipped**; Postgres-marked **16 passed, 1395 deselected** (with a local Postgres); frontend **675 passed in 85 files**, typecheck and lint clean; Alembic head **`0005_services_extras`** (5 revision files); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new `it(`.

  | After | PR | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|---|
  | T1 | 2b-1 | +4, +1 skipped (`test_migrations.py` 4; `test_services_postgres.py` 1, Postgres only; `test_schema_check.py`, `test_api_app.py` edited) | 1399 passed, 17 skipped | 0 | 675 in 85 |
  | T2 | 2b-1 | +14 (`test_service_bulletin.py` 9, one test in five cases; `test_printed_bulletin.py` 4; `test_printed_render.py` 1; `test_api_printed.py` edited) | 1413 passed, 17 skipped | 0 | 675 in 85 |
  | T3 | 2b-1 | +12 (`test_usecase_archive.py` 4; `test_api_services.py` 7, two tests and five new 422 cases; `test_api_printed.py` 1; `test_no_streamlit_in_core.py` edited) | 1425 passed, 17 skipped | 0 | 675 in 85 |
  | T4 | 2b-1 | 0 (no test edited: the new items sit under the existing "## Printed bulletin") | 1425 passed, 17 skipped | 0 | 675 in 85 |
  | T5, T6 | 2b-1 | 0 (verification, the merge, the record) | 1425 passed, 17 skipped | 0 | 675 in 85 |
  | T7 | 2b-2 | 0 | 1425 passed, 17 skipped | +15 (`bulletin.test.ts` 9, `documents.test.ts` 3, `migrate.test.ts` 1, `status.test.ts` 1, `mapping.test.ts` 1; `schema.test.ts`, `store.test.ts`, `keys.test.ts` edited) | 690 in 86 |
  | T8 | 2b-2 | 0 | 1425 passed, 17 skipped | +7 (`bulletin-step.test.tsx`; `builder-shell.test.tsx`, `status.test.ts`, `review-send-step.test.tsx` edited) | 697 in 87 |
  | T9 | 2b-2 | 0 | 1425 passed, 17 skipped | +1 (`review-send-step.test.tsx`; `liturgy-step.test.tsx` edited) | 698 in 87 |
  | T10-T12 | 2b-2 | 0 | 1425 passed, 17 skipped | 0 | 698 in 87 |

- Per PR: **PR 2b-1** backend 1395 → 1425 passed, 16 → 17 skipped, frontend 675 in 85 (unchanged); **PR 2b-2** frontend 675 → 698 in 85 → 87 files, backend unchanged.
- CI `backend-postgres` goes from `16 passed, 1395 deselected` to `17 passed, 1399 deselected` after T1 and `17 passed, 1425 deselected` from T3 on (PR 2b-2 leaves it there). With a local Postgres (`TEST_DATABASE_URL`), the same numbers locally.

### Layering and code rules (carried)
- `service_bulletin`, `printed_bulletin`, `usecases/archive.py`, `usecases/documents.py` and `repos/services.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains `service_bulletin`, T3); the route is a plain `def` with one usecase call, no SQL and no try/except (F §2.2 rule 1); the query lives in `repos.services` and filters on `church_id` (F §1.2).
- Logs carry ids, counts and durations, never a bulletin's text (F §2.5; clarification 15). Neither PR adds a log line; `archive.<create|replace|delete>` and `documents.printed` are unchanged and tested to carry no text.
- Pages and components never call `apiFetch`: `usePreviousBulletin` uses `useApi()` (F §4.5). The draft is changed only through `useDraft()` (`update` for typing, `autoUpdate` for the carry, F §4.6).
- Touch targets 44 px below `md` (`h-11` inputs, `size="touch"` buttons; textareas are 64 px or more); text wraps at 375 px; no raw HTML (F §4.8); the kit's `Input`, `Textarea`, `Label`, `Button` (Base UI shadcn, as the codebase uses).
- Expand-only migration (F §3.4): one nullable column, no default, no backfill, no index.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** (branch `streamlit-frozen`) is frozen and retired for real use; merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge; Railway's Pre-deploy Command `alembic upgrade head` applies migrations.
4. **The spec's decisions** stand as written in S, with the PR 2 planning answers below winning where S's earlier text differs (T4 amends S's "Data model" to match).
5. **Layout B**, the PR 1 plan's twelve answers and the PR 2a plan's fourteen (all "all recommended") stand. PR 2a is merged as PR #46 and recorded.

### PR 2 planning answers (Beau, 2026-10-02, "all recommended"; binding)
1. **PR 2 splits in two.** PR 2a (the Bulletin settings) is merged. **PR 2b, the Bulletin step** (this plan): prelude and postlude, the announcements, pasted reading text, carry forward, the draft v3 and migration `0006_services_bulletin`. Then PR 3 (cover picture).
2. **Admins only** change the Bulletin settings (2a; unchanged here: a week's change of who leads is the draft's, any member).
3. **A blank field prints nothing** (no line, no [placeholder]); the Printed bulletin card lists what is still empty ("Not filled in: ..."). 2b adds the weekly fields.
4. **Announcements:** ushers and counters, deacon of the week, coffee hour, activities, prayers and concerns, collection items, plus one **"Other announcements"** box.
5. **Carry forward with a check:** every announcement carries forward (answer 3), and each carried-over box shows "From last week. Check before printing." until it is edited.
6. **The Bulletin step is optional:** it never blocks Review, the Word copies or the printed bulletin.
7. **Who leads:** the step shows the three people at the top (from settings, changeable for this week); changing one part's leader sits behind "Change who leads a part".
8. **Migration 0006** follows 0005's routine: a backup, read-only counts and the `--sql` preview before the merge, a check query after the deploy, one step at a time.

**Later, out of scope:** PR 3 (the cover picture: `cover_image_id`, `bulletin_images`, migration `0007_bulletin_images`; `ServiceDraft.bulletin` refuses unknown fields, so PR 3 adds the field to the model), 6a (Settings; the Bulletin settings page moves there), the folded booklet, Voices of the Church.

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended).

1. **[owner-visible] What 2b ships** (planning answer 1), in two PRs (clarification 19). PR 2b-1: migration `0006_services_bulletin`, `ServiceDraft.bulletin`, `ServiceOut.bulletin`, `GET /services/previous-bulletin` and the weekly fields printed in the PDF and the Word version when a page sends them. PR 2b-2: the Bulletin step with its fields, carry forward, pasted reading text, the card's new lines and the draft v3. Not here: the cover picture (PR 3; its box keeps printing "[Cover picture]"), any change to the Bulletin settings page or its API, the Word working copies (clarification 18), the summary panel (it shows no bulletin block; "Follow-ups").
2. **[owner-visible] The step and the step bar** (S "The Bulletin step"; planning answer 6; F §4.7). A fifth step, **Bulletin**, number 4, route `/builder/bulletin`, between Liturgy and Review & send (now number 5): Liturgy's footer reads "Next: Bulletin", Bulletin's "Back" and "Next: Review". Below `lg` the bar's line reads "Step 4 of 5 · Bulletin" over five segments (each 44 px tall and about 60 px wide at 375 px, `grid-cols-5`); from `lg` each step shows its number, label and status. The Bulletin step's status is never "Complete" or a count: it is **"Optional"** (muted) or, while boxes from last week are still to check, **"{n} to check"** (for example "2 to check"). It never adds a line to Review's "Still to do" and never turns off a download or Save.
3. **[owner-visible] Music** (answer 2; S "What prints where"). Per piece a **title** (200 characters) and a **composer** (100). Printed as in the sample: "PRELUDE: ‘{title}’" with the organist's name on the right and "- {composer}" under it (POSTLUDE the same). A blank title prints "PRELUDE:" with the composer under it; a blank composer prints no composer line; with both blank the whole PRELUDE (or POSTLUDE) line is left out, the organist's name included (answer 3).
4. **[owner-visible] Who leads** (planning answer 7; S "Data model"). **Worship leader**, **Liturgist** and **Organist** show the Bulletin settings' names (help: "From the bulletin settings. A change here is for this week only."); typing a different name changes it for this week only ("Changed for this week." with **Undo the change**); typing the settings' name back, or **Undo the change**, follows the settings again; a blank field means no one this week (that header line and those parts print no name). Stored as `people: {worship_leader, liturgist, organist}`, each `null` (follow the settings) or this week's text. **Change who leads a part** (outlined, `aria-expanded`) opens one field per part (the 21 parts of 2a, in the printed order) with "Usually {name}" or "Usually no one" under it: the usual leader is the settings' name for the part's role, never this week's change (plan review fix M6); a name there prints on that part this week only, a blank one follows the usual leader (so "no one" for a single part this week is done in Bulletin settings; question 3). Stored as `leaders: {element key: name}`. The button carries `aria-controls` only while the panel is shown (plan review fix M7). If the settings cannot be loaded, **Who leads** shows "Bulletin settings could not be loaded." with **Try again** instead of its fields (no field could tell a usual name from a change). The header and every part's name follow this week's people (`printed_bulletin.WeekSettings`). The settings themselves never change from the step.
5. **[owner-visible] Announcements** (planning answer 4; S "What prints where"). **Ushers and counters** (200), **Deacon of the week** (100) and **Coffee hour** (200) are one line each ("Ushers/Counters: …", "Deacon of the Week: …", "Coffee Hour: …", bold labels, as PR 1); **This week's activities** (4000), **Prayers and concerns** (4000), **Items for collection** (2000) and **Other announcements** (4000) are free text that keeps its line breaks, each under its heading ("THIS WEEK’S ACTIVITIES AT A GLANCE", "PRAYERS AND CONCERNS", "ITEMS FOR COLLECTION", and "OTHER ANNOUNCEMENTS", new, last). The page keeps PR 1's "ANNOUNCEMENTS" and date at the top and stays the last page.
6. **[owner-visible] A blank weekly field prints nothing** (planning answer 3). A blank announcement leaves out its line, or its heading and text. **With every announcement blank there is no announcements page at all** (PDF: the order of worship's last page is the last page, an odd count leaving the last right half blank; Word: no announcements page). The alternative, a page with only "ANNOUNCEMENTS" and the date, is question 5. The last [placeholders] of PR 1 for the music and the announcements are gone; "[Cover picture]", "[Sermon title]" (a blank sermon title) and "[Reading text unavailable]" stay (PR 3; the order of worship; a fetch failure). A body with **no** bulletin at all (a page from before PR 2b-2; after PR 2b-1 and before 2b-2 every page) still prints PR 1's placeholders (`printed_bulletin.PLACEHOLDERS`), so PR 2b-1 changes nothing the owner sees; from PR 2b-2 every body sends a bulletin.
7. **[owner-visible] Carry forward** (planning answer 5; S "Data model"; the spec does not say when). Precisely:
   - **From what:** the church's latest service whose date is before the draft's date (the latest date, then the latest save; an undated service never counts; another church's never). Its music and announcements carry; this week's people, the part leaders and the pasted texts never do (S). A service saved before 2b has no bulletin and so carries nothing (the latest service decides, even when an older one had announcements; question 6). The cover picture id is PR 3's.
   - **When:** only for a draft that is **not a saved service** (`editing` null: a new draft, or one started before 2b-2), with a real date and **no save whose outcome is unknown** (`save_key_fingerprint` null: a carry would change the body, so the next Save would rotate the save key and could save the service twice; plan review fix I2), when the **Bulletin step** or **Review & send** shows it (the two places that show or print the bulletin; `useBulletinCarry`), once per date (`carried_for`). If the date then changes (step 1, or the pristine draft's roll-forward to the next Sunday), it carries again for the new date into every box not edited (replacing what it carried, blank where the new source has nothing). **Opening a saved service never carries.**
   - **"Edited", a box at a time** (`bulletin.edited`, plan review fix M1): a music or announcement box typed in, changed in any way (cleared included) or kept with **Keep as is**. Last week's never carries into that box again for this draft; the boxes not touched still carry (typing in one box while the lookup is slow, or after it failed, does not stop the others). The people, the part leaders and the pasted texts do not count (they never carry).
   - **The check:** each box that received last week's text shows "From last week. Check before printing." (its field described by it) with **Keep as is** (named "Keep {box} as is" for screen readers), until that box is edited or kept (`bulletin.carried`). Keep as is is this plan's addition to answer 5, so a box that is right as it is need not be retyped (question 7). The step bar says "{n} to check"; the Printed bulletin card says "From last week, not checked yet: …" (clarification 9). **The marks are saved with the service** (`bulletin.unchecked`, plan review fix I3), so opening it from Services, on any device, shows the same boxes still to check (question 16). Nothing ever stops a download over it (planning answer 6).
   - **"Save as new service"** (plan review fix I4; question 17): a saved service whose date on step 1 now differs from its saved date is treated as a new week when the Bulletin step or Review shows it (`followSaveMode`): every filled music and announcement box is marked "From last week. Check before printing.", and this week's people, the part leaders and the pasted texts start empty (the people follow the settings). What it empties is set aside in the draft (`bulletin.set_aside`) and comes back if the date goes back to the saved one (a name or text typed meanwhile wins; a saved mark returns only on a box not touched meanwhile), so nothing typed is lost. Nothing happens while a save's outcome is unknown. Once saved as the new service, the set-aside copy is dropped.
   - **How:** `GET /services/previous-bulletin?before=<draft date>` (any member, church-scoped), fetched only while carrying is due, applied through `autoUpdate` with the check repeated in the recipe against the latest draft (F §4.6: never over typed input; only the visible tab carries, as the lectionary fill). A failed lookup shows "Last week's announcements could not be loaded." with **Try again** on the step (`role="alert"`), and it **stays** (typing in a box included) until a retry succeeds or every box is edited; Review shows nothing for it and prints without.
8. **[owner-visible] Pasted reading text** (answer 5; S "Scripture text"). Under **Reading text**, one box per reading the files print (the first reading and the New Testament reading, as `effectivePicks` resolves them), labelled "First Reading: {reference}" and "New Testament Reading: {reference}"; with no readings chosen, "Choose the readings on step 1 to paste their text.". The text is kept with its reading's reference, so choosing another reading shows an empty box (and choosing the first again brings the text back); only the texts of the two readings printed are sent. A pasted text prints instead of the fetched one, as paragraphs (a blank line starts a new one; a run of blank lines is one paragraph break, and every line break pasted from another app, U+2028 and U+2029 included, is a line break), **is not fetched** (no `scripture` token is charged for it), and gets **no credit line** of its own (the pasted text is the church's own translation; the help line says to include the translation's notice if it asks for one). The credit line follows what was fetched (plan review fix M9; question 9): both readings fetched, "Scripture readings are from the {label}." as today; one pasted and the other fetched, "The {First Reading | New Testament Reading} is from the {label}." for the fetched one (for example "The New Testament Reading is from the World English Bible (WEB)."); every printed reading pasted, no line. A pasted text is at most 10 000 characters (question 13).
9. **[owner-visible] The Printed bulletin card** (planning answer 3; 2a's clarification 9 as changed here). PR 1's line "For now, the music and the announcements print as [placeholders]." goes. After the 2a sentence "The church's details, the people who lead and the service time come from the bulletin settings." comes "The music, the announcements and this week's changes to who leads come from the Bulletin step.", then, above the downloads: "Not filled in: {list}." where the list is the 2a standing fields (the three people as this week has them: a person changed on the step counts as filled in, one cleared for this week as not), then "prelude", "postlude" and "announcements" (only when every announcement is blank); while the settings load or if they fail, only the week's part. Then, when any box still holds last week's text unchecked, "From last week, not checked yet: {list}." (labels: prelude, postlude, ushers and counters, deacon of the week, coffee hour, activities, prayers and concerns, collection items, other announcements). The card also runs the carry (clarification 7), so a bulletin printed without opening the Bulletin step has last week's. Its downloads, gates, toasts, save tip and **Bulletin settings** button are unchanged.
10. **[owner-visible] Saving and opening** (S "Data model"; 5a-3's Save). Save stores the bulletin with the service; opening it from **Services** restores every field as saved (the pasted texts under their readings' references), with nothing marked "From last week". A change on the Bulletin step makes Review say "Unsaved changes". `draftToServicePayload` (what the fingerprint hashes) holds `bulletin` only when something is filled in, so a draft that was "Saved" before 2b stays "Saved" after its migration; every body sent (`serviceBody`: the saves, the Word copies, the printed bulletin) always carries `bulletin`, each text cut to its limit, so a save that clears every field clears the saved ones. On the server a `POST` without `bulletin` (a client from before 2b) stores NULL and a `PUT` without it keeps the saved one; the 409 "is it my own save?" check (`savedCopyFingerprint`) compares the bulletin too, read as the server stores it (a one-line field's tabs and control characters one space, a free text's line breaks newlines, a pasted reading's blank lines one paragraph break, the unchecked boxes in order; plan review fix M3), so a tab pasted into a title never looks like someone else's change. The "From last week" marks are saved with the service as `unchecked` (clarification 7) and come back when it is opened.
11. **The draft v3** (F §4.6 "Versioning"). `DRAFT_VERSION` 3; `STEP_IDS` gains "bulletin" (`last_step` may hold it); `bulletin: {prelude, postlude, people, leaders, announcements, pasted (by reference), carried (the boxes still to check), edited (the boxes touched), carried_for, set_aside (Save as new service)}` (`freshBulletin()` in `freshDraft`). `migrations[2]` adds `freshBulletin()` and changes nothing else (a draft in progress is never lost; it carries like a new one unless it is a saved service). A version 4 draft (a later rollback) is a restore error, as today. An open tab still on version 2 code is handled by 5a-3's rule (never adopted; written over). A rollback of PR 2b-2 keeps this reader (clarification 20), so no draft is lost.
12. **The API** (S API). `ServiceDraft.bulletin: Optional[ServiceBulletin] = None` with `ServiceBulletin {prelude, postlude: {title, composer}, people: {worship_leader, liturgist, organist: string | null}, leaders: {ElementKey: string}, announcements: {ushers, deacon, coffee_hour, activities, prayer_concerns, collection, other}, reading_text: {ot, nt}, unchecked: [prelude | postlude | ushers | … | other]}`, every field present, `extra="forbid"` at every level, each text within its limit (clarifications 3-5, 8; `service_bulletin.MAX_LENGTH`), the leaders' keys the 21 element keys: a bad bulletin is the usual 422 naming the field (`bulletin.announcements.ushers`, `bulletin.leaders.anthem.[key]`, `bulletin.cover_image_id`, `bulletin.reading_text.nt`, `bulletin.unchecked.0`). No line-break check (unlike 2a's settings): `service_bulletin.read` makes a one-line field one line (each run of control characters, U+2028/U+2029 and C1 controls becomes a space) and a free text's every line break a newline (`\r\n`, `\r`, a vertical tab, a form feed, U+0085, U+2028 and U+2029; plan review fix M2: reportlab's fonts would print U+2028 as "?"), so a download never meets a 422 for a pasted line break and the PDF never prints "?" for one. `read` keeps the known `unchecked` boxes once each, in order. `ServiceOut.bulletin: ServiceBulletin`, always present (an empty one for a service saved without it). `GET /services/previous-bulletin?before=YYYY-MM-DD` (`require_church`; `before` required and a real date, else 422) answers `PreviousBulletinOut {service_id, service_date_iso, bulletin}`: the source service and the carried part (the people null, the leaders `{}` and the texts blank), or `null`, `null` and an empty bulletin. It is declared before `/services/{service_id}`. No `Idempotency-Key`, no rate limit (a local read). `POST /documents` and `POST /documents/printed` accept `bulletin` through `ServiceDraft` (the Word copies ignore it).
13. **Storage** (S "Data model"; F §3.4, §3.5). `services.bulletin JSON NULL` in `0006_services_bulletin` (`down_revision` `0005_services_extras`; batch mode both ways, so `--sql` and Postgres get a plain `ALTER TABLE … ADD COLUMN bulletin JSON`, under `env.py`'s 5 s lock timeout; adding a nullable column without a default changes only the catalog). The model's column is `JSON(none_as_null=True)`: SQLAlchemy's `JSON` otherwise stores a Python `None` as the JSON value `null`, which `IS NOT NULL` counts (found while planning). A save stores `service_bulletin`'s `to_json()` of the cleaned input (every text Word-safe through `archive._xml_safe`, trimmed and cut); `GET` reads it tolerantly (`service_bulletin.read`: a missing or malformed value is blank). Tests: up from 0005 with a row kept and a later insert without the column (NULL), down giving back the 0005 table, the exact offline SQL, the drift at the baseline and the head constants (`test_schema_check.py`, `test_api_app.py`; 5a-2's 0005 upgrade test now upgrades to `0005_services_extras`, not head), and the owner's two queries on Postgres. The 5a-2 Postgres test of the 0005 queries now expects the head's version.
14. **[owner-visible] The owner's production steps** (planning answer 8; 0005's routine), around **PR 2b-1**'s merge. `backend/migrations/README.md` gains "Before 0006_services_bulletin (printed bulletin PR 2b-1)": (1) a `db-backup` run; (2) one read-only query giving `version` (`0005_services_extras`), `services` and `churches`; (3) the `--sql` preview, rendered by the agent without a database (6 lines: `BEGIN;`, the two timeouts, `ALTER TABLE services ADD COLUMN bulletin JSON;`, the version update, `COMMIT;`), pinned by `test_the_readme_shows_the_0006_preview_exactly`; (4) after the deploy, a read-only query giving `0006_services_bulletin`, `1` and `with_bulletin` `0` (no page sends a bulletin before PR 2b-2), then step 2 again (the same counts, or more). Both queries run in a Postgres test (T1). T6 takes the owner through them one at a time, then through a short phone check that the builder works as before (item 18). Reverting keeps `0006` (README "Reverting PR 2b-2 or PR 2b-1"; T12 Step R).
15. **Privacy and logging** (F §2.5). Prayers and concerns can name people and their health. They live only in the draft (the member's own browser storage) and in the saved service's `bulletin` (the same as the liturgy texts: any member of that church can open the service); they are printed only in the files the member downloads. No log line carries a bulletin's text (`archive.*` and `documents.printed` log ids, counts, sizes and durations; T3 tests both); a 422 names the field, never its value. The tests and docs use invented text only; the owner's check and the record never copy a name from the prayers.
16. **[owner-visible] Every new user-facing string** (no em dashes). The step: "Bulletin" (the step's label, short name and heading); "Optional. What this week's printed bulletin adds to the service. A box left blank is left off the bulletin."; the groups "Music", "Who leads", "Announcements", "Reading text"; "Prelude title", "Prelude composer", "Postlude title", "Postlude composer"; "From the bulletin settings. A change here is for this week only."; "Worship leader", "Liturgist", "Organist" (2a's words); "Changed for this week."; "Undo the change" (for screen readers "Undo the change to {person}"); "Change who leads a part"; "A name here prints on that part this week only. Leave it blank for the usual leader."; the 21 part names (2a's); "Usually {name}", "Usually no one"; "Ushers and counters", "Deacon of the week", "Coffee hour", "This week's activities", "Prayers and concerns", "Items for collection", "Other announcements"; "Paste a reading's text to print it instead of the text the app fetches, for a translation the app cannot fetch. Include the translation's notice if it asks for one."; "First Reading: {reference}", "New Testament Reading: {reference}"; "Choose the readings on step 1 to paste their text."; "From last week. Check before printing."; "Keep as is" (for screen readers "Keep {box} as is"); "Last week's announcements could not be loaded."; "Bulletin settings could not be loaded."; "Try again"; "Bulletin settings" (2a's button). The step bar: "Optional", "{n} to check", "Step {n} of 5". The card: "The music, the announcements and this week's changes to who leads come from the Bulletin step."; "Not filled in: …" gains "prelude", "postlude", "announcements"; "From last week, not checked yet: {list}." with the labels of clarification 9. In the files: "OTHER ANNOUNCEMENTS"; "The First Reading is from the {label}." and "The New Testament Reading is from the {label}." (clarification 8). Gone from PR 2b-2 on: "For now, the music and the announcements print as [placeholders]." and, in every body a 2b-2 page sends, PR 1's weekly placeholders ("[Prelude title]", "[Postlude title]", "[Composer]", "[Names]", "[Name]", "[Activities]", "[Prayer concerns]", "[Collection items]"; still printed for a body with no bulletin, clarification 6).
17. **Docs** (T4, T10). T4 (PR 2b-1): `docs/manual-verification.md` gains "### Printed bulletin PR 2b: the Bulletin step" at the end, inside "## Printed bulletin" (a `###` heading, so `test_slice1_docs.py`'s pin of the last eight `##` headings does not move and no test changes; T4 Step 2 checks it), with a note on the two PRs and that Review & send is step 5 from PR 2b-2, and items 16-18 (the owner's steps around 0006 and the check that the builder works as before); S's "Data model" gains `people`, "other", `unchecked` and the planned carry rule (the spec said nothing of when it happens; Save as new service included), and "Scope by PR" the backend-first order. T10 (PR 2b-2): items 19-27 (the phone check, carry forward on the Sunday after a saved service, the agent's checks), and PR 1's item 2 says where the music and announcements come from after 2b-2. The runbook records are T6's (`### Printed bulletin PR 2b-1 record`, riding along in PR 2b-2) and T12's (`### Printed bulletin PR 2b-2 record`, its own records PR), each before `## Backups`.
18. **What does not change.** The Word working copies (`POST /documents`, the bulletin and pastor's copies) print as before and ignore `bulletin` (S answer 7 kept them as they are; no strong reason to add the music or announcements there; question 15). The Bulletin settings page, its API and storage. `liturgy` keeps only the eight sections. `service_archive.py` (Streamlit's), `env.py`, the workflows, `package.json`, `requirements*.txt`, `app.py`, Streamlit.
19. **[owner-visible] Two PRs, backend first** (plan review fix I1; question 14). The two halves deploy separately, so no window opens in which a new page talks to an old server. **PR 2b-1** (T1-T4: the migration, `service_bulletin`, the printing, the API, the regenerated types, the docs and spec) merges first, after the owner's backup, counts and SQL; it changes no page, component, draft, query or request body (T5 Step 3), so the pages already live keep working against it: they send no `bulletin` (a `POST` stores NULL, a `PUT` keeps the saved one, a download prints PR 1's placeholders), and the extra `ServiceOut.bulletin` is ignored. While Railway deploys it, the old server keeps serving the same pages; if its pre-deploy `alembic upgrade head` fails (the 5 s lock timeout), nothing breaks, since no page needs the new server yet: redeploy. **PR 2b-2** (T7-T10: the draft v3, the step, the card, the docs) merges only after `/openapi.json` in production lists `/services/previous-bulletin` and the owner's checks of T6 passed (T11 Step 1); it changes no server code, API file, workflow or package (T11 Step 3), so its deploy is Vercel's alone, and an old page still open meanwhile keeps working against the same server. The 2a record rides along in PR 2b-1 and the 2b-1 record in PR 2b-2. **PR 3** (`cover_image_id`, `bulletin_images`, `0007_bulletin_images`) follows the same order: its migration and API first, its page second ("Follow-ups").
20. **[owner-visible] Rolling back** (plan review fix M4; T12 Step R). PR 2b-2 is reverted first and alone: the revert keeps the draft's v3 reader (`schema.ts`, `migrate.ts`, their tests, and `/builder`'s fallback to Review for a step not in the bar, which PR 2b-2 adds), so every member's draft opens as it was, its Bulletin fields kept unused until the step returns; the reverted pages send no `bulletin`, which the 2b-1 server takes (a `PUT` keeps what was saved). Checked while planning: that revert typechecks, lints and passes 676 frontend tests (85 files), and a v3 draft left on the Bulletin step opens Review with its fields. PR 2b-1 is reverted only after that (PR 2b-2's pages would otherwise send `bulletin` to a server that refuses it), keeping `0006` as before.

### Risks
- **A lock on `services` at deploy time** (PR 2b-1). `ALTER TABLE` waits for a conflicting lock; `lock_timeout` turns that into a failed deploy after 5 s with the previous release still serving (T6 Step 5 checks the deploy and `/health/ready`, which answers 503 `schema_behind` while the database is behind the release). With the two PRs, a failed or slow deploy leaves nothing broken: no page needs the new server until PR 2b-2, which merges only after T11 Step 1 sees the new route live.
- **The deploy windows** (clarification 19). PR 2b-1: Vercel redeploys pages that are byte for byte today's (the regenerated types change no code that runs), and Railway's old and new servers both take what those pages send. PR 2b-2: Railway redeploys the same server; an old page left open meanwhile keeps working (it sends no `bulletin`). A rollback runs in the same order reversed (clarification 20).
- **Carry happens in the browser, on the Bulletin step and Review.** A download tapped in the first moment on Review, before last week's answer arrives, prints without it (the card then shows the carried lines; download again). A draft never shown on either step never carries (it cannot print without Review). While a save's outcome is unknown nothing carries; the next answered save (or a retry of the same body) lets it.
- **The latest service decides** (clarification 7): if last week's service was saved before PR 2b-2 (or with nothing filled in), nothing carries, even if an older service had announcements.
- **"Save as new service" changes the draft when the step or Review shows it** (clarification 7): a member who changes a saved service's date only to look sees this week's names emptied; changing the date back brings them back (set aside in the draft, not lost).
- **Prayers and concerns are visible to every member who opens the service** (as every saved field is). Named in clarification 15 and question 11.
- **SQLite and JSON:** the archive tests run on SQLite, where `bulletin` is TEXT holding JSON; the Postgres tests (T1) cover the real `json` type with the owner's queries, and CI runs the alembic cycle on Postgres 17.
- **Long free text** flows: a long prayer list makes the announcements page run on to another page (the PDF flows; the booklet keeps reading order). The limits (4000 characters a box, a pasted reading 10 000 with its blank lines collapsed) keep a week to a few pages; the plan review measured the worst cases (three 4000-character boxes of short lines: 77 sides in 3 s; two 20 000-character pastes of blank lines, before the new limit and collapse: 164 sides, Word in 4 s): nothing errors and nothing escapes the frame.

## File Structure

**Created**

| Path | What | Task (PR) |
|---|---|---|
| `backend/migrations/versions/0006_services_bulletin.py` | `services.bulletin` | T1 (2b-1) |
| `backend/service_bulletin.py` (+ `backend/tests/test_service_bulletin.py`) | `ServiceBulletin`, `Music`, `Announcements`, `read`, `MAX_LENGTH`, `ANNOUNCEMENT_KEYS`, `CARRY_KEYS` | T2 (2b-1) |
| `frontend/src/lib/draft/bulletin.ts` (+ `.test.ts`) | the edits, carry forward, Save as new service, the payload, `bulletinFromService`, "Not filled in", "not checked yet", the step status | T7 (2b-2) |
| `frontend/src/app/(signed-in)/(church)/builder/bulletin/page.tsx`, `frontend/src/components/builder/bulletin/bulletin-step.tsx` (+ `.test.tsx`), `frontend/src/components/builder/bulletin/use-bulletin-carry.ts` | the step's route, the step, the carry hook | T8 (2b-2) |

**Modified**

| Path | Change | Task (PR) |
|---|---|---|
| `backend/db/models.py`, `backend/migrations/README.md` | `Service.bulletin`; the head, the 0006 row, "Before 0006_services_bulletin", "Reverting PR 2b-2 or PR 2b-1" | T1 (2b-1) |
| `backend/tests/test_migrations.py`, `backend/tests/test_schema_check.py`, `backend/tests/test_api_app.py`, `backend/tests/test_services_postgres.py` | the 0006 tests, the README pin; the head and the baseline drift; the owner's queries on Postgres | T1 (2b-1) |
| `backend/printed_bulletin.py`, `backend/printed_pdf.py`, `backend/printed_docx.py` | the music, `WeekSettings`, the announcements page (none when blank), pasted readings and the credit line, `PLACEHOLDERS`; the renderers leave an empty page out | T2 (2b-1) |
| `backend/tests/test_printed_bulletin.py`, `backend/tests/test_printed_render.py`, `backend/tests/test_api_printed.py` | `WEEK`; the new content and render tests; (T3) the posted bulletin prints | T2, T3 (2b-1) |
| `backend/api/schemas.py`, `backend/api/routes/services.py`, `backend/usecases/archive.py`, `backend/repos/services.py`, `backend/usecases/documents.py` | `ServiceBulletin` and `PreviousBulletinOut`, `ServiceDraft.bulletin`, `ServiceOut.bulletin`; the route; save, open, `previous_bulletin`; `previous_service`; the posted bulletin and pasted readings printed | T3 (2b-1) |
| `backend/tests/test_usecase_archive.py`, `backend/tests/test_api_services.py`, `backend/tests/test_no_streamlit_in_core.py` | the archive's bulletin and carry; the API's; `service_bulletin` | T3 (2b-1) |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated | T3 (2b-1) |
| `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts` | `ServiceBulletin`, `PreviousBulletin`; `serviceBulletin()`, `savedService().bulletin` (T3), `previousBulletin()` (T8) | T3 (2b-1), T8 (2b-2) |
| `docs/manual-verification.md`, `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md` | "### Printed bulletin PR 2b: the Bulletin step" and items 16-18; S's "Data model" and "Scope by PR" (T4); items 19-27 and PR 1's item 2 (T10) | T4 (2b-1), T10 (2b-2) |
| `docs/ops-runbook.md` | the PR 2a record (`9c731e1`, rides along in PR 2b-1); "### Printed bulletin PR 2b-1 record" (T6, rides along in PR 2b-2); "### Printed bulletin PR 2b-2 record" (the records PR) | T6, T12 |
| `frontend/src/lib/draft/schema.ts`, `migrate.ts`, `mapping.ts`, `status.ts`, `frontend/src/lib/documents.ts`, `frontend/src/lib/queries/keys.ts`, `frontend/src/lib/queries/services.ts`, `frontend/src/components/builder/step-progress.tsx` | the draft v3; 2 → 3; the payload, `serviceToDraft`, `markSaved`; the status and `isPristine`; `serviceBody`, `savedCopyFingerprint`; `keys.previousBulletin`; `usePreviousBulletin`; the new status texts (T7), five columns (T8) | T7, T8 (2b-2) |
| `frontend/src/lib/draft/schema.test.ts`, `migrate.test.ts`, `store.test.ts`, `mapping.test.ts`, `status.test.ts`, `frontend/src/lib/documents.test.ts`, `frontend/src/lib/queries/keys.test.ts` | version 3; the new cases | T7, T8 (2b-2) |
| `frontend/src/lib/draft/steps.ts`, `frontend/src/app/(signed-in)/(church)/builder/page.tsx`, `frontend/src/components/builder/review/review-send-step.tsx`, `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/components/builder/review/review-send-step.test.tsx` | five steps; `/builder`'s fallback; Review's "Step 5" comment; the step bar's tests | T8, T9 (2b-2) |
| `frontend/src/components/builder/review/printed-card.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.test.tsx` | the card's lines and the carry; the new route in the test that renders Review | T9 (2b-2) |

**Counts in the PRs:** **PR 2b-1** 31 paths: 4 created (this plan, `0006_services_bulletin.py`, `service_bulletin.py`, `test_service_bulletin.py`), 27 modified (the 26 backend, API, fixture and docs paths above and `docs/ops-runbook.md`, the PR 2a record `9c731e1`, which rides along until merged). **PR 2b-2** 31 paths: 6 created (`bulletin.ts` and its test, the step, its test, its route, the carry hook), 25 modified (24 frontend and docs paths and `docs/ops-runbook.md`, the PR 2b-1 record). **Untouched:** `service_output.py`, `worship_service.py`, `api/routes/documents.py`, `bulletin_settings.py`, the Bulletin settings page and its API, `migrations/env.py`, `service_archive.py`, `documents-card.tsx`, the summary panel, the workflows, the packages, `app.py`, Streamlit.

**Task order and review batches:** PR 2b-1: T1 → T4, each one commit and a backup push; one review of the batch with its fixes as `Fix: …` commits (T4 Step 4); T5 verifies and opens the draft PR on the owner's yes; T6 takes the owner through the backup, the counts and the SQL, merges on the owner's yes, checks production and the builder, and commits the 2b-1 record. PR 2b-2, only then: T7 → T10, the same way (review in T10 Step 4); T11 checks that 2b-1 is live, verifies and opens the draft PR on the owner's yes; T12 merges on the owner's yes, runs the phone check and writes the record (its own records PR).

---

## PR 2b-1: the server (T1-T6)

T1-T4 are PR 2b-1's commits: the migration, the week's fields printed, the API, the docs. The builder does not change: the old pages send no `bulletin` and keep working (clarification 19). T5 verifies and opens the draft PR; T6 takes the owner through the backup, the counts and the SQL, merges on the owner's yes, checks production and writes the 2b-1 record, which rides along in PR 2b-2. Nothing of PR 2b-2 is started before T6 Step 7 (PR 2b-2 merges only after 2b-1 is live and checked).

### Task 1: Migration `0006_services_bulletin` and the owner's steps (planning answer 8; S "Data model"; F §3.1, §3.4, §3.5; clarifications 13, 14)

**Files:**
- Create: `backend/migrations/versions/0006_services_bulletin.py`
- Modify: `backend/tests/test_migrations.py`, `backend/tests/test_schema_check.py`, `backend/tests/test_api_app.py`, `backend/tests/test_services_postgres.py`, `backend/db/models.py`, `backend/migrations/README.md`

5a-2's 0005 upgrade test upgraded to `head`; it now upgrades to `0005_services_extras`, so it keeps checking 0005's own columns. The 0005 owner-query test on Postgres expects the head's version (the test database is always at head).

- [ ] **Step 1 (agent): Write the failing tests**

**In `backend/tests/test_api_app.py`, replace:**

````python
SCHEMA_HEAD = "0005_services_extras"
````

**with:**

````python
SCHEMA_HEAD = "0006_services_bulletin"
````

**In `backend/tests/test_migrations.py`, replace:**

````python
            kept = _insert_legacy_service(conn, church_id, user_id)
            before = _services_shape(conn)
        _alembic(sqlite_url, "upgrade", "head")
        with engine.begin() as conn:
````

**with:**

````python
            kept = _insert_legacy_service(conn, church_id, user_id)
            before = _services_shape(conn)
        _alembic(sqlite_url, "upgrade", "0005_services_extras")
        with engine.begin() as conn:
````

**In `backend/tests/test_migrations.py`, replace:**

````python
    assert block.splitlines() == PREVIEW_0005
````

**with:**

````python
    assert block.splitlines() == PREVIEW_0005


# --- Printed bulletin PR 2b: 0006_services_bulletin (F §3.4, §3.5; printed bulletin spec "Data model") ---

# What `alembic upgrade 0005_services_extras:0006_services_bulletin --sql` prints on
# Postgres, comments and blank lines left out: the preview the owner reads before
# the merge (PR 2 planning answer 8; backend/migrations/README.md).
PREVIEW_0006 = [
    "BEGIN;",
    "SET LOCAL lock_timeout = '5s';",
    "SET LOCAL statement_timeout = '60s';",
    "ALTER TABLE services ADD COLUMN bulletin JSON;",
    "UPDATE alembic_version SET version_num='0006_services_bulletin' "
    "WHERE alembic_version.version_num = '0005_services_extras';",
    "COMMIT;",
]


def test_0006_adds_the_nullable_bulletin_column_and_keeps_rows(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0005_services_extras")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            kept = _insert_legacy_service(conn, church_id, user_id)
            before = _services_shape(conn)
        _alembic(sqlite_url, "upgrade", "head")
        with engine.begin() as conn:
            at_head = _services_shape(conn)
            inserted = _insert_legacy_service(conn, church_id, user_id, date_iso="2026-10-04")
            rows = conn.execute(sa.text("SELECT id, occasion, bulletin FROM services ORDER BY service_date_iso")).all()
    finally:
        engine.dispose()
    assert at_head["columns"] == before["columns"] + [("bulletin", "JSON", True)]
    assert (at_head["pk"], at_head["fks"], at_head["indexes"]) == (before["pk"], before["fks"], before["indexes"])
    # The row from before keeps its data; an insert that does not name the column gets NULL.
    assert [(uuid.UUID(str(r.id)), r.occasion, r.bulletin) for r in rows] == [
        (kept, "Pentecost 17", None), (inserted, "Pentecost 17", None)]


def test_0006_downgrade_gives_back_the_0005_services_table(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0005_services_extras")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            before = _services_shape(conn)
        _alembic(sqlite_url, "upgrade", "head")
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            _insert_legacy_service(conn, church_id, user_id)
            conn.execute(sa.text("""UPDATE services SET custom_elements = '[]', hymnal = 'GG2013',
                                    bulletin = '{"announcements": {"coffee_hour": "Sam Sample"}}'"""))
        _alembic(sqlite_url, "downgrade", "0005_services_extras")
        with engine.connect() as conn:
            after = _services_shape(conn)
            rows = conn.execute(sa.text("SELECT occasion, hymnal FROM services")).all()
            version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()
    assert after == before          # the table copy kept every other column, key and index
    assert [tuple(r) for r in rows] == [("Pentecost 17", "GG2013")]
    assert version == "0005_services_extras"


def test_offline_sql_for_0006_is_one_column_add_under_the_timeouts():
    cfg = alembic_config(url="postgresql://preview@localhost:1/preview", configure_logger=False)
    cfg.output_buffer = buffer = io.StringIO()
    command.upgrade(cfg, "0005_services_extras:0006_services_bulletin", sql=True)
    lines = [line for line in buffer.getvalue().splitlines() if line.strip() and not line.startswith("--")]
    assert lines == PREVIEW_0006


def test_the_readme_shows_the_0006_preview_exactly():
    """The owner reads backend/migrations/README.md → "Before 0006_services_bulletin",
    step 3, against the agent's rendering; both must be PREVIEW_0006."""
    readme = (Path(__file__).resolve().parents[1] / "migrations" / "README.md").read_text(encoding="utf-8")
    section = readme.split("\n## Before 0006_services_bulletin (printed bulletin PR 2b-1)\n", 1)[1]
    step = section.split("\n### Step 3: Read the SQL the upgrade will run\n", 1)[1].split("\n### ", 1)[0]
    block = "BEGIN;" + step.split("\n```\nBEGIN;", 1)[1].split("\n```", 1)[0]   # the bare fence
    assert block.splitlines() == PREVIEW_0006
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
EXPECTED_HEAD = "0005_services_extras"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
# 0004's invites changes, then 0005's services changes (slice 5a-2).
````

**with:**

````python
EXPECTED_HEAD = "0006_services_bulletin"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
# 0004's invites changes, then 0005's and 0006's services changes (slice 5a-2,
# printed bulletin PR 2b).
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
    "add_column invites.reusable",
````

**with:**

````python
    "add_column invites.reusable",
    "add_column services.bulletin",
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_head_is_0005_services_extras():
````

**with:**

````python
def test_head_is_0006_services_bulletin():
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_and_0005_changes(tmp_path):
````

**with:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_0005_and_0006_changes(tmp_path):
````

**In `backend/tests/test_services_postgres.py`, replace:**

````python
    # The 5a-2 save has 3 slots; the other five are old-style; "", NULL and "Sept 13" are undated.
    assert counts == {"version": "0005_services_extras", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0005_services_extras", "new_columns": 2, "new_index": 1}
````

**with:**

````python
    # The 5a-2 save has 3 slots; the other five are old-style; "", NULL and "Sept 13" are undated. The
    # test database is at head (0006_services_bulletin since printed bulletin PR 2b).
    assert counts == {"version": "0006_services_bulletin", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0006_services_bulletin", "new_columns": 2, "new_index": 1}


def readme_0006_sql(n: int) -> str:
    """The n-th ```sql block of README "Before 0006_services_bulletin": 0 is step 2's counts, 1 step 4's check."""
    section = README.read_text(encoding="utf-8").split(
        "\n## Before 0006_services_bulletin (printed bulletin PR 2b-1)\n", 1)[1]
    return re.findall(r"```sql\n(.*?)```", section, re.S)[n]


@pytest.mark.postgres
def test_the_owner_s_read_only_queries_around_0006(world):
    user, church = world
    other = create_church(name="Other", timezone="America/New_York", owner_user_id=user)
    with session_scope() as s:
        for church_id, bulletin in ((church, None), (church, {"announcements": {"coffee_hour": "Sam Sample"}}),
                                    (other, None)):
            s.add(Service(church_id=church_id, service_date_iso="2026-09-27", occasion="", hymns=[], liturgy={},
                          scriptures=[], bulletin=bulletin))
    with session_scope() as s:
        counts = dict(s.execute(text(readme_0006_sql(0))).mappings().one())
        applied = dict(s.execute(text(readme_0006_sql(1))).mappings().one())
    assert counts == {"version": "0006_services_bulletin", "services": 3, "churches": 2}
    assert applied == {"version": "0006_services_bulletin", "new_column": 1, "with_bulletin": 1}
````

- [ ] **Step 2 (agent): Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py 2>&1 | tail -1`
**Expected:** `15 failed, 56 passed, 4 skipped in <t>s`: the four 0006 tests (no revision `0006_services_bulletin` yet; no README section), nine head and drift tests in `test_schema_check.py`, two startup tests in `test_api_app.py`. (With a local Postgres, the two owner-query tests in `test_services_postgres.py` fail too.)

- [ ] **Step 3 (agent): The revision, the model, the README**

**In `backend/db/models.py`, replace:**

````python
    hymnal = Column(String, nullable=True)          # the hymnal the hymns came from
````

**with:**

````python
    hymnal = Column(String, nullable=True)          # the hymnal the hymns came from
    # Revision 0006_services_bulletin (printed bulletin PR 2b): the printed
    # bulletin's weekly fields (service_bulletin.py). NULL: never filled in
    # (every service saved before PR 2b), read as an empty bulletin. A Python
    # None is stored as SQL NULL, never as the JSON value null.
    bulletin = Column(JSON(none_as_null=True), nullable=True)
````

**In `backend/migrations/README.md`, replace:**

````markdown
  `NNNN_short_slug.py`. Head is `0005_services_extras`.
````

**with:**

````markdown
  `NNNN_short_slug.py`. Head is `0006_services_bulletin`.
````

**In `backend/migrations/README.md`, replace:**

````markdown
| `0005_services_extras` | Slice 5a-2: `services.custom_elements` (JSON) and `services.hymnal` (VARCHAR), both nullable with no default and no backfill, and the index `ix_services_church_date` on `services (church_id, service_date_iso)`. Before it reaches production: "Before 0005_services_extras" below. |
````

**with:**

````markdown
| `0005_services_extras` | Slice 5a-2: `services.custom_elements` (JSON) and `services.hymnal` (VARCHAR), both nullable with no default and no backfill, and the index `ix_services_church_date` on `services (church_id, service_date_iso)`. Before it reaches production: "Before 0005_services_extras" below. |
| `0006_services_bulletin` | Printed bulletin PR 2b: `services.bulletin` (JSON), nullable with no default and no backfill: the printed bulletin's weekly fields. Before it reaches production: "Before 0006_services_bulletin" below. |
````

**In `backend/migrations/README.md`, replace:**

````markdown
for this.
````

**with:**

````markdown
for this.

## Before 0006_services_bulletin (printed bulletin PR 2b-1)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0006_services_bulletin` when the printed bulletin PR 2b-1 (the server's
half of PR 2b; the Bulletin step, PR 2b-2, merges after it is live) merges.
First, as
the owner decided on 2026-10-02 (PR 2 planning answer 8, the same routine as
0005): a backup, read-only counts of the saved services, and a look at the
SQL; after the deploy, one read-only check. One step at a time. Nothing here
changes data. The agent guides the owner and records the results in
`docs/ops-runbook.md` → "Printed bulletin PR 2b-1 record", never with an email
address, a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL.

### Step 2: Count the saved services (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run:

```sql
-- Read-only: what the archive holds before 0006. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       count(*) AS services,
       count(DISTINCT church_id) AS churches
FROM services;
```

One row. Expected before the merge: `version` is `0005_services_extras`
(anything else: stop); `services` is the number of saved services in all
churches and `churches` the number of churches that saved at least one.

### Step 3: Read the SQL the upgrade will run

The agent renders it from the PR's code without connecting to any database
(from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0005_services_extras:0006_services_bulletin --sql 2>/dev/null | grep -v -e '^--' -e '^$'
```

Expected, exactly (`backend/tests/test_migrations.py` pins it):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE services ADD COLUMN bulletin JSON;
UPDATE alembic_version SET version_num='0006_services_bulletin' WHERE alembic_version.version_num = '0005_services_extras';
COMMIT;
```

One new empty column, in one transaction: no row is copied, changed or
deleted. If another connection holds a lock on `services` for more than
5 s, the deploy fails and the previous release keeps serving; run the
deploy again.

### Step 4: After the deploy (read-only)

SQL Editor:

```sql
-- Read-only: is 0006 applied? Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'services'
           AND column_name = 'bulletin') AS new_column,
       (SELECT count(*) FROM services WHERE bulletin IS NOT NULL) AS with_bulletin;
```

Expected: `0006_services_bulletin`, `1`, and `with_bulletin` `0` (no page
sends a bulletin until PR 2b-2's Bulletin step; from then on every save
stores one). Then step 2's query again: the same `services` and
`churches` (or more, by the services saved since the deploy; never fewer).

### Reverting PR 2b-2 or PR 2b-1

PR 2b-2 (the Bulletin step) changes no schema: revert it first, as the
plan's Step R says. Revert PR 2b-1 only after PR 2b-2 is reverted and live
(the Bulletin step sends `bulletin`, which the API before 2b-1 refuses).
For PR 2b-1 the schema stays at `0006_services_bulletin`: the column is nullable and the
code before 2b-1 ignores it. Revert the merge commit, then restore
`backend/migrations/versions/0006_services_bulletin.py` and the `Service`
column in `backend/db/models.py` from the merge commit in the same PR, so
Railway's `alembic upgrade head` still finds the database at head and
`alembic check` stays clean. Never `alembic downgrade` production for this:
the weekly fields saved since the merge stay in the column, unread, and come
back when 2b-1 does.
````

**Create `backend/migrations/versions/0006_services_bulletin.py`:**

````python
"""Services: the printed bulletin's weekly fields (printed bulletin spec, "Data model"; PR 2b)

Expand-only (F §3.4): one nullable JSON column, no backfill, no server
default, no index. Existing rows keep NULL, which the API reads as an empty
bulletin (nothing filled in).
- services.bulletin JSON NULL: what the service's printed bulletin prints
  each week: the prelude and postlude, this week's people and part leaders,
  the announcements and any pasted reading text (service_bulletin.py).
  A new column rather than a key inside services.liturgy, which holds only
  the eight liturgy sections and which every reader filters to them.

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and statement_timeout
'60s') first, so a lock held elsewhere fails the deploy after 5 s instead of
queueing every query behind it; the previous release keeps serving. Adding a
nullable column without a default changes only the catalog. Both directions
use op.batch_alter_table, as 0004 and 0005 do: plain ALTER TABLE on Postgres
and in --sql, a table copy on SQLite when the column is dropped.

Revision ID: 0006_services_bulletin
Revises: 0005_services_extras
Create Date: 2026-10-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_services_bulletin"
down_revision = "0005_services_extras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.add_column(sa.Column("bulletin", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.drop_column("bulletin")
````

- [ ] **Step 4 (agent): Run the files, the offline SQL and the suite (and Postgres if at hand)**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_models.py 2>&1 | tail -1
(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0005_services_extras:0006_services_bulletin --sql 2>/dev/null | grep -v -e '^--' -e '^$')
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `75 passed, 4 skipped in <t>s`; the six lines of clarification 14 exactly (README step 3); `1399 passed, 17 skipped in <t>s`. With a local, throwaway Postgres: `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `17 passed, 1399 deselected` (and a `1 warning` from the onboarding timing test, as on `main`), and CI's cycle by hand on an empty database there (from `backend/`, `DATABASE_URL=<local url of an empty database>`): `../.venv/bin/alembic upgrade head`, `check` (`No new upgrade operations detected.`), `downgrade base`, `upgrade head`, `check`; without one, say so (CI's `backend-postgres` runs them).

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/migrations/versions/0006_services_bulletin.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py
git commit -q -m "Migration 0006_services_bulletin: services.bulletin (printed bulletin PR 2b-1)" -m "Expand-only (F 3.4): one nullable JSON column with no default and no
backfill, for the printed bulletin's weekly fields; batch mode both
ways, as 0004 and 0005, under env.py's 5 s lock timeout. The model's
column stores a Python None as SQL NULL. migrations/README.md gains
'Before 0006_services_bulletin': the backup, the read-only counts, the
SQL preview and the after-deploy check (PR 2 planning answer 8); both
queries run on Postgres and the preview is pinned to the rendered SQL.
Tests: up from 0005 keeping rows, down to the 0005 table, the exact
offline SQL; the head and the baseline drift." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1399 passed, 17 skipped`; frontend `675 passed` in 85 files.

### Task 2: The week's fields print: `service_bulletin` and `printed_bulletin` (planning answers 3, 4, 7; S "What prints where", "Scripture text"; clarifications 3-6, 8, 10, 19)

**Files:**
- Create: `backend/tests/test_service_bulletin.py`, `backend/service_bulletin.py`
- Modify: `backend/tests/test_printed_bulletin.py`, `backend/tests/test_printed_render.py`, `backend/tests/test_api_printed.py`, `backend/printed_bulletin.py`, `backend/printed_pdf.py`, `backend/printed_docx.py`

The PR 1 and 2a tests now pass `WEEK` (invented music and announcements) and expect them where PR 1 expected the weekly [placeholders]; `test_printed_render.py` imports `WEEK` with `SETTINGS`. A `PrintedService` with no bulletin (`None`: nothing posted, a page from before PR 2b-2) still prints PR 1's placeholders, so `test_api_printed.py`'s 2a test, which posts no bulletin, keeps its placeholder check (only its comment changes).

- [ ] **Step 1: Write the failing tests**

**In `backend/tests/test_api_printed.py`, replace:**

````python
    assert "‘[Prelude title]’" in text and "Coffee Hour: [Name]" in text           # the weekly fields: PR 2b
````

**with:**

````python
    # No bulletin was posted (a page from before the Bulletin step): PR 1's weekly placeholders (PR 2b-1).
    assert "‘[Prelude title]’" in text and "Coffee Hour: [Name]" in text
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
printed_bulletin.py), with the church's bulletin settings (PR 2a)."""
````

**with:**

````python
printed_bulletin.py), with the church's bulletin settings (PR 2a) and the
week's own fields from the Bulletin step (PR 2b)."""
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
import printed_bulletin as pb
````

**with:**

````python
import printed_bulletin as pb
import service_bulletin as sb
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
    worship_leader="Rev. Alex Example", liturgist="Sam Sample", organist="Jordan Doe")
````

**with:**

````python
    worship_leader="Rev. Alex Example", liturgist="Sam Sample", organist="Jordan Doe")
# Invented details: a week with the music and every announcement filled in (PR 2b).
WEEK = sb.ServiceBulletin(
    prelude=sb.Music("Morning Voluntary", "Pat Example"), postlude=sb.Music("Festive Postlude", "Lee Sample"),
    announcements=sb.Announcements(
        ushers="Sam Sample, Jordan Doe", deacon="Alex Example", coffee_hour="The Example family",
        activities="Tuesday: Bible study at 10 a.m.\nWednesday: Choir at 7 p.m.",
        prayer_concerns="For all who are ill.", collection="Canned goods for the food pantry.",
        other="The office is closed on Monday."))
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
                settings=SETTINGS)
````

**with:**

````python
                settings=SETTINGS, bulletin=WEEK)
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
    assert by_text["PRELUDE:  ‘[Prelude title]’"].right == "Jordan Doe"
````

**with:**

````python
    assert by_text["PRELUDE:  ‘Morning Voluntary’"].right == "Jordan Doe"
    i = texts(lines).index("PRELUDE:  ‘Morning Voluntary’")
    assert lines[i + 1] == pb.Line("indent", (pb.Span("- Pat Example"),))
    i = texts(lines).index("POSTLUDE:  ‘Festive Postlude’")
    assert (lines[i].right, lines[i + 1].text) == ("Jordan Doe", "- Lee Sample")
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
        "ANNOUNCEMENTS", "October 4, 2026", "Ushers/Counters: [Names]", "Deacon of the Week: [Name]",
        "Coffee Hour: [Name]", "THIS WEEK’S ACTIVITIES AT A GLANCE", "[Activities]", "PRAYERS AND CONCERNS",
        "[Prayer concerns]", "ITEMS FOR COLLECTION", "[Collection items]"]
````

**with:**

````python
        "ANNOUNCEMENTS", "October 4, 2026", "Ushers/Counters: Sam Sample, Jordan Doe",
        "Deacon of the Week: Alex Example", "Coffee Hour: The Example family",
        "THIS WEEK’S ACTIVITIES AT A GLANCE", "Tuesday: Bible study at 10 a.m.\nWednesday: Choir at 7 p.m.",
        "PRAYERS AND CONCERNS", "For all who are ill.", "ITEMS FOR COLLECTION", "Canned goods for the food pantry.",
        "OTHER ANNOUNCEMENTS", "The office is closed on Monday."]
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
    assert by_text["*PRELUDE:  ‘[Prelude title]’"].right == ""               # starred; no role now
````

**with:**

````python
    assert by_text["*PRELUDE:  ‘Morning Voluntary’"].right == ""             # starred; no role now
````

**In `backend/tests/test_printed_bulletin.py`, replace:**

````python
    assert texts(pb.order_of_worship(starred))[-1] == "*Congregation stands if able"
````

**with:**

````python
    assert texts(pb.order_of_worship(starred))[-1] == "*Congregation stands if able"


def test_a_blank_weekly_field_prints_nothing():
    """PR 2 planning answer 3: no line and no [placeholder] for a blank weekly field."""
    half = sb.ServiceBulletin(prelude=sb.Music("", "Pat Example"), postlude=sb.Music("Festive Postlude", ""),
                              announcements=sb.Announcements(coffee_hour="The Example family",
                                                             prayer_concerns="For all who are ill."))
    lines = texts(pb.order_of_worship(service(bulletin=half)))
    i = lines.index("PRELUDE:")
    assert lines[i + 1] == "- Pat Example"
    i = lines.index("POSTLUDE:  ‘Festive Postlude’")
    assert lines[i + 1] == "ENDING"                                      # no composer line
    assert texts(pb.announcements(service(bulletin=half))) == [
        "ANNOUNCEMENTS", "October 4, 2026", "Coffee Hour: The Example family", "PRAYERS AND CONCERNS",
        "For all who are ill."]
    empty = texts(pb.order_of_worship(service(bulletin=sb.ServiceBulletin())))
    assert not any(line.startswith(("PRELUDE", "POSTLUDE", "- ")) for line in empty)
    assert not any("[" in line for line in empty if line != "SERMON:  “[Sermon title]”" and "unavailable" not in line)
    assert pb.announcements(service(bulletin=sb.ServiceBulletin())) == []   # the page is left out


def test_this_week_s_people_and_part_leaders_print_over_the_settings():
    week = dataclasses.replace(WEEK, people={"worship_leader": "Rev. Guest", "liturgist": "", "organist": None},
                               leaders={"sermon": "Pat Example", "offering": "Lee Sample"})
    lines = pb.order_of_worship(service(bulletin=week))
    by_text = {line.text: line for line in lines}
    assert texts(lines[:4]) == ["THE SERVICE FOR THE LORD’S DAY", "Example Church", "Rev. Guest, Worship Leader",
                                "Jordan Doe, Organist"]                    # this week: no liturgist
    assert by_text["NEW TESTAMENT READING:  Matthew 21:33-46"].right == "Rev. Guest"
    assert by_text["CALL TO WORSHIP"].right == ""
    assert by_text["SERMON:  “Who Said?”"].right == "Pat Example"
    assert by_text["OFFERING OUR GIFTS"].right == "Lee Sample"            # a part with no standing role
    assert by_text["PRELUDE:  ‘Morning Voluntary’"].right == "Jordan Doe"


def test_pasted_reading_text_prints_and_the_credit_line_names_only_fetched_text():
    """A pasted text prints with no credit line; when the other reading is fetched, the line names it (plan
    review fix M9); with every reading pasted, there is none."""
    nt = pb.Reading("Matthew 21:33-46", "Jesus said, What do you think?", pasted=True)
    lines = texts(pb.order_of_worship(service(nt=nt)))
    i = lines.index("NEW TESTAMENT READING:  Matthew 21:33-46")
    assert lines[i + 1:i + 4] == ["Jesus said, What do you think?",
                                  "The First Reading is from the World English Bible (WEB).", "SERMON:  “Who Said?”"]
    assert not any(line.startswith("Scripture readings are from") for line in lines)
    ot = pb.Reading("Psalm 80:7-15", "Turn us again, God.", pasted=True)
    lines = texts(pb.order_of_worship(service(ot=ot)))
    assert "The New Testament Reading is from the World English Bible (WEB)." in lines
    lines = texts(pb.order_of_worship(service(ot=ot, nt=nt)))
    assert not any(" is from the " in line or " are from the " in line for line in lines)
    lines = texts(pb.order_of_worship(service(ot=None, nt=nt)))
    assert not any(" is from the " in line or " are from the " in line for line in lines)


def test_no_bulletin_posted_prints_pr_1_s_placeholders():
    """A page from before the Bulletin step (PR 2b-2) posts no bulletin: the music and the announcements
    print as PR 1 printed them, so PR 2b-1 changes nothing that page shows."""
    lines = texts(pb.order_of_worship(service(bulletin=None)))
    i = lines.index("PRELUDE:  ‘[Prelude title]’")
    assert lines[i + 1] == "- [Composer]"
    i = lines.index("POSTLUDE:  ‘[Postlude title]’")
    assert lines[i + 1] == "- [Composer]"
    assert lines[2:4] == ["Rev. Alex Example, Worship Leader", "Sam Sample, Liturgist"]
    assert texts(pb.announcements(service(bulletin=None))) == [
        "ANNOUNCEMENTS", "October 4, 2026", "Ushers/Counters: [Names]", "Deacon of the Week: [Name]",
        "Coffee Hour: [Name]", "THIS WEEK’S ACTIVITIES AT A GLANCE", "[Activities]", "PRAYERS AND CONCERNS",
        "[Prayer concerns]", "ITEMS FOR COLLECTION", "[Collection items]"]
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
with pypdf and python-docx."""
````

**with:**

````python
with pypdf and python-docx. PR 2b: the week's music and announcements, and
no announcements page when every announcement is blank."""
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
from tests.test_printed_bulletin import SETTINGS
````

**with:**

````python
import service_bulletin as sb
from tests.test_printed_bulletin import SETTINGS, WEEK
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
                             pb.Reading("Matthew 21:23-32", VERSE * verses), "World English Bible (WEB)", SETTINGS)
````

**with:**

````python
                             pb.Reading("Matthew 21:23-32", VERSE * verses), "World English Bible (WEB)", SETTINGS,
                             WEEK)
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
    assert pages[3].startswith("3 ANNOUNCEMENTS September 27, 2026") and pages[3].endswith("[Collection items]")
````

**with:**

````python
    assert pages[3].startswith("3 ANNOUNCEMENTS September 27, 2026 Ushers/Counters: Sam Sample, Jordan Doe")
    assert pages[3].endswith("OTHER ANNOUNCEMENTS The office is closed on Monday.")
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
                     "POSTLUDE: ‘[Postlude title]’ Jordan Doe", "Go in peace. - A Friend"):
````

**with:**

````python
                     "POSTLUDE: ‘Festive Postlude’ Jordan Doe", "- Lee Sample", "Go in peace. - A Friend",
                     "Tuesday: Bible study at 10 a.m. Wednesday: Choir at 7 p.m."):
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
                     "FB: Example Church", "Coffee Hour: [Name]"):
````

**with:**

````python
                     "FB: Example Church", "Coffee Hour: The Example family",
                     "Tuesday: Bible study at 10 a.m.\nWednesday: Choir at 7 p.m."):
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
    assert children == sorted(children, key=order.index)
````

**with:**

````python
    assert children == sorted(children, key=order.index)


def test_with_every_announcement_blank_the_announcements_page_is_left_out():
    """PR 2b: a blank announcement prints nothing, and with none at all there is no announcements page; the
    order of worship's last page is the last page (an odd count leaves the last right half blank)."""
    ps = dataclasses.replace(service(), bulletin=sb.ServiceBulletin(prelude=WEEK.prelude))
    pages = halves(printed_pdf.render_pdf(ps))
    assert len(pages) == 4 and pages[3] == ""
    assert pages[2].startswith("2 And he answered") and pages[2].endswith("*Congregation stands if able")
    assert "ANNOUNCEMENTS September" not in " ".join(pages)
    doc = Document(BytesIO(printed_docx.render_docx(ps)))
    assert [p.text for p in doc.paragraphs if p.paragraph_format.page_break_before] == [
        "THE SERVICE FOR THE LORD’S DAY"]
    assert doc.paragraphs[-1].text == "*Congregation stands if able"
````

**Create `backend/tests/test_service_bulletin.py`:**

````python
"""A service's weekly bulletin fields (printed bulletin spec, "Data model";
PR 2b; service_bulletin.py): the tolerant read, the stored shape and what
carries forward to the next week."""
import pytest

import service_bulletin as sb

EMPTY_JSON = {
    "prelude": {"title": "", "composer": ""}, "postlude": {"title": "", "composer": ""},
    "people": {"worship_leader": None, "liturgist": None, "organist": None}, "leaders": {},
    "announcements": {"ushers": "", "deacon": "", "coffee_hour": "", "activities": "", "prayer_concerns": "",
                      "collection": "", "other": ""},
    "reading_text": {"ot": "", "nt": ""}, "unchecked": [],
}


@pytest.mark.parametrize("raw", [None, {}, "x", [], {"prelude": "x", "people": [], "announcements": 5}])
def test_nothing_stored_reads_as_an_empty_bulletin(raw):
    assert sb.read(raw) == sb.ServiceBulletin()
    assert sb.read(raw).to_json() == EMPTY_JSON
    assert sb.read(raw).is_blank()


def test_a_stored_value_reads_back_clean():
    stored = {
        "prelude": {"title": "  Morning\nVoluntary ", "composer": "Pat Example"},
        "postlude": {"title": "Festive Postlude", "composer": 7},
        "people": {"worship_leader": " Rev. Guest ", "liturgist": "", "organist": 3, "pastor": "x"},
        "leaders": {"sermon": " Rev. Guest\t", "nope": "Sam Sample", "welcome": "  ", "offering": None},
        "announcements": {"ushers": "Sam Sample,\r\nJordan Doe", "deacon": "x" * 150,
                          "activities": "  Tuesday: Bible study.\nWednesday: Choir.  ", "other": None},
        "reading_text": {"ot": " In you, Lord, I put my trust.\n\nAmen. ", "nt": ["x"]},
        "unchecked": ["coffee_hour", "nope", 3, "prelude", "coffee_hour"],
        "cover_image_id": "later",
    }
    b = sb.read(stored)
    assert b.prelude == sb.Music("Morning Voluntary", "Pat Example")
    assert b.postlude == sb.Music("Festive Postlude", "")
    assert b.people == {"worship_leader": "Rev. Guest", "liturgist": "", "organist": None}
    assert b.leaders == {"sermon": "Rev. Guest"}
    assert (b.announcements.ushers, b.announcements.deacon) == ("Sam Sample, Jordan Doe", "x" * 100)
    assert b.announcements.activities == "Tuesday: Bible study.\nWednesday: Choir."
    assert (b.ot_text, b.nt_text) == ("In you, Lord, I put my trust.\n\nAmen.", "")
    assert b.unchecked == ("prelude", "coffee_hour")                     # known boxes, once each, in order
    assert not b.is_blank()
    assert sb.read(b.to_json()) == b


def test_what_carries_forward_is_the_music_and_the_announcements():
    week = sb.read({"prelude": {"title": "Morning Voluntary", "composer": ""}, "people": {"organist": "Sam Sample"},
                    "leaders": {"sermon": "Rev. Guest"}, "announcements": {"coffee_hour": "The Example family"},
                    "reading_text": {"nt": "Pasted."}, "unchecked": ["prelude"]})
    assert week.carried() == sb.ServiceBulletin(prelude=sb.Music("Morning Voluntary", ""),
                                                announcements=sb.Announcements(coffee_hour="The Example family"))


def test_map_texts_changes_every_text_and_keeps_the_standing_people():
    week = sb.read({"prelude": {"title": "a"}, "people": {"liturgist": "b"}, "leaders": {"sermon": "c"},
                    "announcements": {"other": "d"}, "reading_text": {"ot": "e"}})
    upper = week.map_texts(str.upper)
    assert upper.to_json()["prelude"]["title"] == "A"
    assert upper.people == {"worship_leader": None, "liturgist": "B", "organist": None}
    assert (upper.leaders, upper.announcements.other, upper.ot_text) == ({"sermon": "C"}, "D", "E")


def test_every_line_break_in_a_free_text_is_a_newline_and_a_pasted_reading_keeps_one_blank_line():
    """Plan review fix M2: U+2028, U+2029 and U+0085 (pasted from Pages or Word) would print as "?" in the
    PDF; a pasted reading's runs of blank lines are one paragraph break, and it is cut at 10 000."""
    b = sb.read({"announcements": {"prayer_concerns": "For Sam\u2028For Lee\u2029For all\x85Amen.\r\nEnd",
                                   "coffee_hour": "The Example\u2028family"},
                 "reading_text": {"ot": "Verse one.\r\n\r\n \n\nVerse two.\u2029\u2029Verse three.\nAmen.",
                                  "nt": "x" * 12_000}})
    assert b.announcements.prayer_concerns == "For Sam\nFor Lee\nFor all\nAmen.\nEnd"
    assert b.announcements.coffee_hour == "The Example family"
    assert b.ot_text == "Verse one.\n\nVerse two.\n\nVerse three.\nAmen."
    assert b.nt_text == "x" * 10_000
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py 2>&1 | tail -3` then `.venv/bin/python -m pytest -q backend/tests/test_api_printed.py 2>&1 | tail -1`
**Expected** (`service_bulletin` does not exist yet: `ModuleNotFoundError` above these lines; `test_printed_render.py` imports from `test_printed_bulletin.py`):
```
ERROR backend/tests/test_printed_render.py
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
3 errors in <t>s
```
then `12 passed in <t>s` (the 2a test's comment changed only; nothing posted still prints the placeholders).

- [ ] **Step 3: `service_bulletin` and the printing**

**In `backend/printed_bulletin.py`, replace:**

````python
  The weekly fields (the music, the announcements, the cover picture) print
  as [bracketed placeholders] until PR 2b's Bulletin step and PR 3 fill them.
````

**with:**

````python
- The week's own fields come from the Bulletin step (PR 2b,
  service_bulletin): the prelude and postlude, this week's people and part
  leaders (over the settings' names), the announcements and any pasted
  reading text. A blank one prints nothing too; with every announcement
  blank there is no announcements page. A pasted reading prints no credit
  line; when the other reading is fetched, its own credit line names it
  ("The New Testament Reading is from the ..."). A service posted with no
  bulletin at all (a page from before the Bulletin step, PR 2b-2) prints
  PR 1's [placeholders] for the music and the announcements (PLACEHOLDERS).
  The cover picture prints as a [bracketed placeholder] until PR 3.
````

**In `backend/printed_bulletin.py`, replace:**

````python
from dataclasses import dataclass, field
````

**with:**

````python
from dataclasses import dataclass, field, fields
````

**In `backend/printed_bulletin.py`, replace:**

````python
from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS
````

**with:**

````python
from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS
from service_bulletin import Announcements, Music, ServiceBulletin
````

**In `backend/printed_bulletin.py`, replace:**

````python
# The weekly fields' placeholders, until PR 2b's Bulletin step and PR 3 fill them.
PRELUDE = ("[Prelude title]", "[Composer]")
POSTLUDE = ("[Postlude title]", "[Composer]")
````

**with:**

````python
# PR 1's weekly placeholders, printed when no bulletin was posted (a page from before PR 2b-2's Bulletin step).
PLACEHOLDERS = ServiceBulletin(
    prelude=Music("[Prelude title]", "[Composer]"), postlude=Music("[Postlude title]", "[Composer]"),
    announcements=Announcements(ushers="[Names]", deacon="[Name]", coffee_hour="[Name]", activities="[Activities]",
                                prayer_concerns="[Prayer concerns]", collection="[Collection items]"))
# The cover picture's place, until PR 3 prints the picture.
````

**In `backend/printed_bulletin.py`, replace:**

````python
    text: Optional[str]            # None: the text could not be fetched (TEXT_UNAVAILABLE prints)
````

**with:**

````python
    text: Optional[str]            # None: the text could not be fetched (TEXT_UNAVAILABLE prints)
    pasted: bool = False           # the Bulletin step's pasted text (PR 2b), not fetched
````

**In `backend/printed_bulletin.py`, replace:**

````python
    settings: BulletinSettings = BulletinSettings()      # the church's standing settings (PR 2a)
````

**with:**

````python
    settings: BulletinSettings = BulletinSettings()      # the church's standing settings (PR 2a)
    bulletin: Optional[ServiceBulletin] = None           # the week's own fields (PR 2b); None: none posted


def week(ps: PrintedService) -> ServiceBulletin:
    """The week's fields as they print: PR 1's placeholders when no bulletin was posted."""
    return PLACEHOLDERS if ps.bulletin is None else ps.bulletin


@dataclass(frozen=True)
class WeekSettings(BulletinSettings):
    """The standing settings as this week prints them (PR 2b): the people
    with this week's names, and a part's leader this week over its role's."""
    part_leaders: Mapping[str, str] = field(default_factory=dict)

    def leader(self, key: str) -> str:
        return self.part_leaders.get(key) or super().leader(key)


def this_week(ps: PrintedService) -> WeekSettings:
    """ps.settings with ps.bulletin's people (a name set for this week, "" for no one) and part leaders."""
    values = {f.name: getattr(ps.settings, f.name) for f in fields(BulletinSettings)}
    values.update({role: name for role, name in week(ps).people.items() if name is not None})
    return WeekSettings(**values, part_leaders=dict(week(ps).leaders))
````

**In `backend/printed_bulletin.py`, replace:**

````python
def _music(s: BulletinSettings, key: str, label: str, piece: tuple[str, str]) -> list[Line]:
    title, composer = piece
    return [_element(s, key, f"{label}:", Span("  "), Span(f"‘{title}’", bold=True, italic=True)),
            Line("indent", (Span(f"- {composer}"),))]
````

**with:**

````python
def _music(s: BulletinSettings, key: str, label: str, piece: Music) -> list[Line]:
    """PRELUDE: ‘title’ with "- composer" under it; a blank title or composer
    prints nothing of its own, and a piece with neither prints nothing at all."""
    if not piece.title and not piece.composer:
        return []
    title = (Span("  "), Span(f"‘{piece.title}’", bold=True, italic=True)) if piece.title else ()
    composer = [Line("indent", (Span(f"- {piece.composer}"),))] if piece.composer else []
    return [_element(s, key, f"{label}:", *title), *composer]
````

**In `backend/printed_bulletin.py`, replace:**

````python
    ("{name}, Worship Leader"), and the date with the service time across."""
    s = ps.settings
````

**with:**

````python
    ("{name}, Worship Leader"), and the date with the service time across."""
    s = this_week(ps)
````

**In `backend/printed_bulletin.py`, replace:**

````python
    s = ps.settings
````

**with:**

````python
    s = this_week(ps)
````

**In `backend/printed_bulletin.py`, replace:**

````python
        *_music(s, "prelude", "Prelude", PRELUDE),
````

**with:**

````python
        *_music(s, "prelude", "Prelude", week(ps).prelude),
````

**In `backend/printed_bulletin.py`, replace:**

````python
    if (ps.ot or ps.nt) and ps.translation_label:
        lines.append(Line("credit", (Span(f"Scripture readings are from the {ps.translation_label}.", italic=True),)))
````

**with:**

````python
    lines += _credit(ps)
````

**In `backend/printed_bulletin.py`, replace:**

````python
    lines += _music(s, "postlude", "Postlude", POSTLUDE)
````

**with:**

````python
    lines += _music(s, "postlude", "Postlude", week(ps).postlude)
````

**In `backend/printed_bulletin.py`, replace:**

````python
def announcements(ps: PrintedService) -> list[Line]:
    """The back page: PR 2's announcements form, as placeholders for now."""
````

**with:**

````python
# The announcements page (PR 2b; PR 2 planning answer 4), in the sample's order, "Other announcements" last.
NAMED_ANNOUNCEMENTS = (("ushers", "Ushers/Counters: "), ("deacon", "Deacon of the Week: "),
                       ("coffee_hour", "Coffee Hour: "))
ANNOUNCEMENT_SECTIONS = (("activities", "THIS WEEK’S ACTIVITIES AT A GLANCE"),
                         ("prayer_concerns", "PRAYERS AND CONCERNS"), ("collection", "ITEMS FOR COLLECTION"),
                         ("other", "OTHER ANNOUNCEMENTS"))


def _credit(ps: PrintedService) -> list[Line]:
    """The translation's credit line, for fetched text only: a pasted text is
    the church's own (PR 2b). With both readings fetched, "Scripture readings
    are from the {label}."; with one pasted and the other fetched, a line
    naming the fetched one; with every reading pasted, none."""
    readings = [(name, r) for name, r in (("First Reading", ps.ot), ("New Testament Reading", ps.nt)) if r]
    fetched = [name for name, r in readings if not r.pasted]
    if not fetched or not ps.translation_label:
        return []
    if len(fetched) == len(readings):
        text = f"Scripture readings are from the {ps.translation_label}."
    else:
        text = f"The {fetched[0]} is from the {ps.translation_label}."
    return [Line("credit", (Span(text, italic=True),))]


def announcements(ps: PrintedService) -> list[Line]:
    """The back page: each announcement filled in this week (a free text
    keeps its lines), the blank ones left out; nothing at all when every one
    is blank, and the renderers then leave the page out."""
    a = week(ps).announcements
    lines = [Line("center", (Span(label, bold=True), Span(getattr(a, key))))
             for key, label in NAMED_ANNOUNCEMENTS if getattr(a, key)]
    for key, title in ANNOUNCEMENT_SECTIONS:
        if getattr(a, key):
            lines += [_section(title), Line("center", (Span(getattr(a, key)),))]
    if not lines:
        return []
````

**In `backend/printed_bulletin.py`, replace:**

````python
        Line("center", (Span("Ushers/Counters: ", bold=True), Span("[Names]"))),
        Line("center", (Span("Deacon of the Week: ", bold=True), Span("[Name]"))),
        Line("center", (Span("Coffee Hour: ", bold=True), Span("[Name]"))),
        _section("THIS WEEK’S ACTIVITIES AT A GLANCE"),
        Line("center", (Span("[Activities]"),)),
        _section("PRAYERS AND CONCERNS"),
        Line("center", (Span("[Prayer concerns]"),)),
        _section("ITEMS FOR COLLECTION"),
        Line("center", (Span("[Collection items]"),)),
````

**with:**

````python
        *lines,
````

**In `backend/printed_docx.py`, replace:**

````python
order of worship and the announcements, each starting a page, numbered from
the first inside page. An element's leader sits at a right tab stop. To print
````

**with:**

````python
order of worship and the announcements (left out when every announcement is
blank, PR 2b), each starting a page, numbered from the first inside page.
A free text's line breaks stay line breaks (python-docx turns "\n" into
one). An element's leader sits at a right tab stop. To print
````

**In `backend/printed_docx.py`, replace:**

````python
    for part in (pb.order_of_worship(ps), pb.announcements(ps)):
````

**with:**

````python
    for part in (pb.order_of_worship(ps), pb.announcements(ps)):
        if not part:                                   # every announcement blank: no page (PR 2b)
            continue
````

**In `backend/printed_pdf.py`, replace:**

````python
pages 2 and 3, and so on, with the announcements page last. Nothing is
folded or padded: an odd page count leaves the last side's right half blank.
````

**with:**

````python
pages 2 and 3, and so on, with the announcements page last (left out when
every announcement is blank, PR 2b). Nothing is folded or padded: an odd
page count leaves the last side's right half blank.
````

**In `backend/printed_pdf.py`, replace:**

````python
    story.append(FrameBreak())
    story += [f for line in pb.announcements(ps) for f in _flowables(line, width)]
````

**with:**

````python
    back = pb.announcements(ps)
    if back:                                               # every announcement blank: no page (PR 2b)
        story.append(FrameBreak())
        story += [f for line in back for f in _flowables(line, width)]
````

**Create `backend/service_bulletin.py`:**

````python
"""A service's weekly bulletin fields (printed bulletin spec, "Data model";
PR 2b): what the Bulletin step fills in for one week's printed bulletin,
stored in services.bulletin (migration 0006_services_bulletin).

- ServiceBulletin: the prelude and postlude (title, composer); this week's
  worship leader, liturgist and organist (None: the standing name from the
  bulletin settings; "": no one this week); a part's leader this week by
  element key (bulletin_settings.ELEMENT_KEYS); the announcements (ushers and
  counters, deacon of the week, coffee hour, activities, prayers and
  concerns, collection items, other announcements; PR 2 planning answer 4);
  the pasted text of the two readings (pasted wins over fetched); and the
  boxes whose text came from last week and are not checked yet
  (`unchecked`, so "From last week. Check before printing." comes back when
  the service is opened again; plan review fix I3).
- read(raw): a stored or posted value read tolerantly: anything that is not
  an object, a missing key or a value of the wrong type is blank (a person
  None); an unknown element key and a blank part leader are dropped; every
  text is trimmed and cut to its limit, and every one-line text (the music,
  the people, the part leaders, the ushers, the deacon and the coffee hour)
  has each run of line breaks, tabs or other control characters made one
  space. The free texts (activities, prayers and concerns, collection items,
  other announcements, the pasted readings) keep their lines, every line
  break as "\n" (a Windows or old-Mac ending, a vertical tab, a form feed,
  U+0085, U+2028 and U+2029 included, which the PDF would print as "?"), and
  a pasted reading's runs of blank lines become one paragraph break.
  `unchecked` keeps the known boxes, once each, in the step's order.
- to_json: the stored shape (what GET /services/{id} answers as `bulletin`).
- carried(): what a new week starts from (PR 2 planning answer 5): the music
  and the announcements; the people, the part leaders, the pasted texts and
  `unchecked` start empty.
- map_texts(fn): the same bulletin with fn applied to every text
  (usecases.archive makes them Word-safe with it).
Pure: no database, FastAPI or rendering here. Prayer concerns can hold names
and health news: nothing here logs, and no caller logs a bulletin's text.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields
from typing import Optional

from bulletin_settings import ELEMENT_KEYS, NOT_ONE_LINE, ROLES

ANNOUNCEMENT_KEYS = ("ushers", "deacon", "coffee_hour", "activities", "prayer_concerns", "collection", "other")
ONE_LINE_ANNOUNCEMENTS = ("ushers", "deacon", "coffee_hour")
# The boxes that carry forward to the next week (PR 2 planning answer 5), in the Bulletin step's order.
CARRY_KEYS = ("prelude", "postlude", *ANNOUNCEMENT_KEYS)

# The longest value each text takes; ServiceDraft refuses longer (422), and read() cuts a stored one.
MAX_LENGTH = {"title": 200, "composer": 100, "person": 100, "ushers": 200, "deacon": 100, "coffee_hour": 200,
              "activities": 4000, "prayer_concerns": 4000, "collection": 2000, "other": 4000,
              "reading_text": 10_000}

_NOT_ONE_LINE_RUN = re.compile(f" *[{NOT_ONE_LINE}][{NOT_ONE_LINE} ]*")
# Every way a pasted text can break a line, as one "\n" (U+2028 and U+2029 would print as "?" in the PDF).
_LINE_BREAK = re.compile(r"\r\n?|[\x0b\x0c\x85\u2028\u2029]")
# A run of blank lines (spaces allowed) in a pasted reading: one paragraph break.
_BLANK_LINES = re.compile(r"\n(?:[ \t]*\n)+")


@dataclass(frozen=True)
class Music:
    title: str = ""
    composer: str = ""


@dataclass(frozen=True)
class Announcements:
    ushers: str = ""                # Ushers/Counters
    deacon: str = ""                # Deacon of the Week
    coffee_hour: str = ""
    activities: str = ""            # This week's activities at a glance
    prayer_concerns: str = ""
    collection: str = ""            # Items for collection
    other: str = ""                 # Other announcements


def _no_one_changed() -> dict[str, Optional[str]]:
    return {role: None for role in ROLES}


@dataclass(frozen=True)
class ServiceBulletin:
    prelude: Music = Music()
    postlude: Music = Music()
    # This week's people: None prints the standing name (bulletin settings), "" no one.
    people: Mapping[str, Optional[str]] = field(default_factory=_no_one_changed)
    # A part's leader this week (element key -> name), over its standing role's name.
    leaders: Mapping[str, str] = field(default_factory=dict)
    announcements: Announcements = Announcements()
    ot_text: str = ""               # pasted text of the first reading (wins over the fetched text)
    nt_text: str = ""               # pasted text of the New Testament reading
    # The boxes (CARRY_KEYS) holding last week's text, not checked yet; saved so the marks come back on open.
    unchecked: tuple[str, ...] = ()

    def is_blank(self) -> bool:
        return self == ServiceBulletin()

    def carried(self) -> ServiceBulletin:
        """What the next week starts from: the music and the announcements."""
        return ServiceBulletin(prelude=self.prelude, postlude=self.postlude, announcements=self.announcements)

    def map_texts(self, fn: Callable[[str], str]) -> ServiceBulletin:
        """Every text through fn; a person left to the settings (None) stays None."""
        return ServiceBulletin(
            prelude=Music(fn(self.prelude.title), fn(self.prelude.composer)),
            postlude=Music(fn(self.postlude.title), fn(self.postlude.composer)),
            people={role: None if name is None else fn(name) for role, name in self.people.items()},
            leaders={key: fn(name) for key, name in self.leaders.items()},
            announcements=Announcements(**{f.name: fn(getattr(self.announcements, f.name))
                                           for f in fields(Announcements)}),
            ot_text=fn(self.ot_text), nt_text=fn(self.nt_text), unchecked=self.unchecked)

    def to_json(self) -> dict:
        return {
            "prelude": {"title": self.prelude.title, "composer": self.prelude.composer},
            "postlude": {"title": self.postlude.title, "composer": self.postlude.composer},
            "people": {role: self.people.get(role) for role in ROLES},
            "leaders": {key: self.leaders[key] for key in ELEMENT_KEYS if key in self.leaders},
            "announcements": {key: getattr(self.announcements, key) for key in ANNOUNCEMENT_KEYS},
            "reading_text": {"ot": self.ot_text, "nt": self.nt_text},
            "unchecked": list(self.unchecked),
        }


def _object(value: object) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _text(value: object, limit: int, *, one_line: bool, paragraphs: bool = False) -> str:
    if not isinstance(value, str):
        return ""
    if one_line:
        value = _NOT_ONE_LINE_RUN.sub(" ", value)
    else:
        value = _LINE_BREAK.sub("\n", value)
        if paragraphs:
            value = _BLANK_LINES.sub("\n\n", value)
    return value.strip()[:limit].strip()


def _unchecked(value: object) -> tuple[str, ...]:
    keys = {key for key in value if isinstance(key, str)} if isinstance(value, list) else set()
    return tuple(key for key in CARRY_KEYS if key in keys)


def _music(value: object) -> Music:
    raw = _object(value)
    return Music(_text(raw.get("title"), MAX_LENGTH["title"], one_line=True),
                 _text(raw.get("composer"), MAX_LENGTH["composer"], one_line=True))


def read(raw: object) -> ServiceBulletin:
    """A stored or posted bulletin, read tolerantly (see the module docstring)."""
    stored = _object(raw)
    people = _object(stored.get("people"))
    leaders = _object(stored.get("leaders"))
    announcements = _object(stored.get("announcements"))
    reading_text = _object(stored.get("reading_text"))
    return ServiceBulletin(
        prelude=_music(stored.get("prelude")),
        postlude=_music(stored.get("postlude")),
        people={role: _text(people[role], MAX_LENGTH["person"], one_line=True)
                if isinstance(people.get(role), str) else None for role in ROLES},
        leaders={key: name for key in ELEMENT_KEYS
                 if (name := _text(leaders.get(key), MAX_LENGTH["person"], one_line=True))},
        announcements=Announcements(**{key: _text(announcements.get(key), MAX_LENGTH[key],
                                                  one_line=key in ONE_LINE_ANNOUNCEMENTS)
                                       for key in ANNOUNCEMENT_KEYS}),
        ot_text=_text(reading_text.get("ot"), MAX_LENGTH["reading_text"], one_line=False, paragraphs=True),
        nt_text=_text(reading_text.get("nt"), MAX_LENGTH["reading_text"], one_line=False, paragraphs=True),
        unchecked=_unchecked(stored.get("unchecked")),
    )
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py backend/tests/test_api_printed.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:** `46 passed in <t>s`; `1413 passed, 17 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/service_bulletin.py backend/printed_bulletin.py backend/printed_pdf.py backend/printed_docx.py backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py backend/tests/test_api_printed.py
git commit -q -m "Printed bulletin PR 2b-1: the week's fields print" -m "service_bulletin holds a service's weekly bulletin fields (the music,
this week's people and part leaders, the announcements, the pasted
reading text, the boxes still to check), read tolerantly: every line
break of a free text a newline (U+2028 and U+2029 included), a pasted
reading's blank lines one paragraph break. The printed bulletin prints
them over the settings: a blank one prints nothing, with every
announcement blank there is no announcements page, Other announcements
prints last, a pasted reading prints with no credit line and a fetched
one beside it with its own. Nothing posted (a page from before the
Bulletin step) prints PR 1's placeholders." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1413 passed, 17 skipped`; frontend `675 passed` in 85 files.

### Task 3: The API saves, opens, carries and prints the bulletin (S API, "Data model"; F §1.2, §1.3, §2.2; clarifications 7, 8, 10, 12, 15, 19)

**Files:**
- Modify: `backend/tests/test_usecase_archive.py`, `backend/tests/test_api_services.py`, `backend/tests/test_api_printed.py`, `backend/tests/test_no_streamlit_in_core.py`, `backend/api/schemas.py`, `backend/usecases/archive.py`, `backend/repos/services.py`, `backend/api/routes/services.py`, `backend/usecases/documents.py`, `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (the last two regenerated)

`ServiceOut.bulletin` is required in the regenerated types, so the frontend fixture `savedService()` gains `bulletin: serviceBulletin()` in this commit (typecheck stays clean; no frontend test changes count). Nothing in the frontend reads it yet: the pages of PR 2b-1 are the pages of today.

- [ ] **Step 1: Write the failing tests**

**Append to `backend/tests/test_api_printed.py`:**

````python


def test_the_week_s_fields_print_and_a_pasted_reading_is_neither_fetched_nor_charged(client, church, owner,
                                                                                  calls, caplog):
    """PR 2b: the music, this week's people and part leaders, the announcements and a pasted reading."""
    with session_scope() as s:
        s.get(Church, church).settings = {"bulletin": {"liturgist": "Sam Sample", "organist": "Jordan Doe"}}
    bulletin = {
        "prelude": {"title": "Morning Voluntary", "composer": "Pat Example"},
        "postlude": {"title": "Festive Postlude", "composer": ""},
        "people": {"worship_leader": "Rev. Guest", "liturgist": "", "organist": None},
        "leaders": {"sermon": "Pat Example"},
        "announcements": {"ushers": "Sam Sample", "deacon": "", "coffee_hour": "The Example family",
                          "activities": "", "prayer_concerns": "For all who are ill.", "collection": "",
                          "other": ""},
        "reading_text": {"ot": "", "nt": "Pasted text of the reading."},
        "unchecked": ["prelude"],
    }
    ratelimit.consume("scripture", user_id=owner, cost=59)                   # one token left: one part
    caplog.set_level(logging.INFO, logger="usecases.documents")
    r = post(client, church, {"format": "pdf", "service": {**SERVICE, "bulletin": bulletin}})
    assert r.status_code == 200, r.text
    assert calls == [("Isaiah 5:1-7", "web")]                                # the pasted one is not fetched
    text = pdf_text(r.content)
    for expected in ("Rev. Guest, Worship Leader Jordan Doe, Organist October 4, 2026",
                     "PRELUDE: ‘Morning Voluntary’ Jordan Doe - Pat Example", "SERMON: “Living Water” Pat Example",
                     "NEW TESTAMENT READING: Philippians 3:4b-14 Rev. Guest Pasted text of the reading.",
                     "POSTLUDE: ‘Festive Postlude’ Jordan Doe", "ANNOUNCEMENTS October 4, 2026",
                     "Ushers/Counters: Sam Sample Coffee Hour: The Example family PRAYERS AND CONCERNS "
                     "For all who are ill."):
        assert expected in text, expected
    assert "Sam Sample, Liturgist" not in text and "Scripture readings are from" not in text
    assert "The First Reading is from the World English Bible (WEB)." in text   # the fetched one only
    (record,) = [r for r in caplog.records if r.getMessage().startswith("documents.printed")]
    assert "ill" not in record.getMessage() and "Example" not in record.getMessage()
````

**In `backend/tests/test_api_services.py`, replace:**

````python
    "custom_elements": [{"label": "Anthem", "text": "Choir", "insert_after": "sermon"}],
````

**with:**

````python
    "custom_elements": [{"label": "Anthem", "text": "Choir", "insert_after": "sermon"}],
}
# Printed bulletin PR 2b: the week's bulletin fields (invented).
BLANK_BULLETIN = {
    "prelude": {"title": "", "composer": ""}, "postlude": {"title": "", "composer": ""},
    "people": {"worship_leader": None, "liturgist": None, "organist": None}, "leaders": {},
    "announcements": {"ushers": "", "deacon": "", "coffee_hour": "", "activities": "", "prayer_concerns": "",
                      "collection": "", "other": ""},
    "reading_text": {"ot": "", "nt": ""}, "unchecked": [],
}
BULLETIN = {
    **BLANK_BULLETIN,
    "prelude": {"title": "Morning Voluntary", "composer": "Pat Example"},
    "people": {"worship_leader": "Rev. Guest", "liturgist": "", "organist": None},
    "leaders": {"sermon": "Rev. Guest"},
    "announcements": {**BLANK_BULLETIN["announcements"], "ushers": "Sam Sample", "coffee_hour": "The Example family",
                      "prayer_concerns": "For all who are ill."},
    "reading_text": {"ot": "", "nt": "Pasted text."},
    "unchecked": ["prelude", "coffee_hour"],
````

**In `backend/tests/test_api_services.py`, replace:**

````python
    assert_church_isolated(client, "POST", "/services", world=world, json=SERVICE)
````

**with:**

````python
    assert_church_isolated(client, "POST", "/services", world=world, json=SERVICE)
    assert_church_isolated(client, "GET", "/services/previous-bulletin?before=2026-10-11", world=world)
````

**In `backend/tests/test_api_services.py`, replace:**

````python
    ({"custom_elements": [{"label": " ", "text": "", "insert_after": "end"}]}, "custom_elements.0.label"),
````

**with:**

````python
    ({"custom_elements": [{"label": " ", "text": "", "insert_after": "end"}]}, "custom_elements.0.label"),
    ({"bulletin": {**BULLETIN, "leaders": {"anthem": "Sam Sample"}}}, "bulletin.leaders.anthem.[key]"),
    ({"bulletin": {**BULLETIN, "announcements": {**BULLETIN["announcements"], "ushers": "x" * 201}}},
     "bulletin.announcements.ushers"),
    ({"bulletin": {**BULLETIN, "cover_image_id": "x"}}, "bulletin.cover_image_id"),
    ({"bulletin": {**BULLETIN, "reading_text": {"ot": "", "nt": "x" * 10_001}}}, "bulletin.reading_text.nt"),
    ({"bulletin": {**BULLETIN, "unchecked": ["cover"]}}, "bulletin.unchecked.0"),
````

**In `backend/tests/test_api_services.py`, replace:**

````python
    assert call(client, "GET", f"/services/{first['id']}", second).status_code == 404
````

**with:**

````python
    assert call(client, "GET", f"/services/{first['id']}", second).status_code == 404


def test_the_week_s_bulletin_is_saved_and_opened_and_an_older_client_keeps_it(client, church):
    made = create(client, church, {**SERVICE, "bulletin": BULLETIN})
    assert made["bulletin"] == BULLETIN
    path = f"/services/{made['id']}"
    assert call(client, "GET", path, church).json()["bulletin"] == BULLETIN
    # A client from before 2b sends no bulletin: the saved one stays.
    r = call(client, "PUT", path, church, json=SERVICE, **{"If-Match": made["saved_at"]})
    assert (r.status_code, r.json()["bulletin"]) == (200, BULLETIN)
    assert create(client, church)["bulletin"] == BLANK_BULLETIN               # none sent: nothing filled in


def test_last_week_s_bulletin_carries_the_music_and_the_announcements(client, church):
    made = create(client, church, {**SERVICE, "service_date_iso": "2026-09-27", "bulletin": BULLETIN})
    r = call(client, "GET", "/services/previous-bulletin?before=2026-10-04", church)
    assert r.status_code == 200, r.text
    assert r.json() == {"service_id": made["id"], "service_date_iso": "2026-09-27", "bulletin": {
        **BLANK_BULLETIN, "prelude": BULLETIN["prelude"], "announcements": BULLETIN["announcements"]}}
    r = call(client, "GET", "/services/previous-bulletin?before=2026-09-27", church)
    assert r.json() == {"service_id": None, "service_date_iso": None, "bulletin": BLANK_BULLETIN}
    for query in ("", "?before=2026-02-30", "?before=2026-10-04T00:00:00"):
        r = call(client, "GET", f"/services/previous-bulletin{query}", church)
        assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request"), query
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "printed_bulletin, printed_pdf, printed_docx, bulletin_settings, usecases.church_bulletin; "
````

**with:**

````python
            "printed_bulletin, printed_pdf, printed_docx, bulletin_settings, usecases.church_bulletin, service_bulletin; "
````

**In `backend/tests/test_usecase_archive.py`, replace:**

````python
concurrent saves are in test_services_postgres.py."""
````

**with:**

````python
concurrent saves are in test_services_postgres.py."""
import dataclasses
````

**In `backend/tests/test_usecase_archive.py`, replace:**

````python
from repos.services import DATED_PREFIX
````

**with:**

````python
from repos.services import DATED_PREFIX
from service_bulletin import Announcements, ServiceBulletin
from service_bulletin import read as read_bulletin
````

**In `backend/tests/test_usecase_archive.py`, replace:**

````python
    assert not any("Communion" in line or "Old Favorite" in line for line in lines)
````

**with:**

````python
    assert not any("Communion" in line or "Old Favorite" in line for line in lines)


# --- printed bulletin PR 2b: the week's bulletin fields --------------------------

# Invented: what the Bulletin step sends for one week (a control character pasted into the prayers).
WEEK = read_bulletin({
    "prelude": {"title": " Morning Voluntary ", "composer": "Pat Example"},
    "people": {"worship_leader": "Rev. Guest"}, "leaders": {"sermon": "Rev. Guest"},
    "announcements": {"coffee_hour": "The Example family", "prayer_concerns": "For all who are ill.\x01"},
    "reading_text": {"nt": "Pasted text."}, "unchecked": ["coffee_hour"]})
BLANK = ServiceBulletin().to_json()


def stored_bulletin(service_id):
    with session_scope() as s:
        return s.get(Service, service_id).bulletin


def test_a_save_stores_the_week_s_bulletin_word_safe_and_never_logs_it(church, pastor, caplog):
    with caplog.at_level(logging.INFO, logger="usecases.archive"):
        record = archive.create_service(church, pastor, service(bulletin=WEEK))
    raw = stored_bulletin(record.id)
    assert raw["announcements"]["prayer_concerns"] == "For all who are ill."
    assert raw["people"] == {"worship_leader": "Rev. Guest", "liturgist": None, "organist": None}
    assert (raw["prelude"], raw["leaders"], raw["reading_text"]) == (
        {"title": "Morning Voluntary", "composer": "Pat Example"}, {"sermon": "Rev. Guest"},
        {"ot": "", "nt": "Pasted text."})
    assert raw["unchecked"] == ["coffee_hour"]                       # the marks come back on open (fix I3)
    assert record.bulletin == raw and archive.get_service(church, record.id).bulletin == raw
    assert not any("ill" in r.getMessage() or "Example family" in r.getMessage() for r in caplog.records)


def test_no_bulletin_sent_stores_none_and_a_replace_without_one_keeps_the_saved_one(church, pastor):
    record = archive.create_service(church, pastor, service())
    assert stored_bulletin(record.id) is None and record.bulletin == BLANK
    again = archive.replace_service(church, record.id, service(bulletin=WEEK), if_match=record.saved_at)
    kept = archive.replace_service(church, record.id, service(), if_match=again.saved_at)    # an older client
    assert kept.bulletin == again.bulletin and kept.bulletin["leaders"] == {"sermon": "Rev. Guest"}
    cleared = archive.replace_service(church, record.id, service(bulletin=ServiceBulletin()), if_match=kept.saved_at)
    assert cleared.bulletin == BLANK and stored_bulletin(record.id) == BLANK


def test_last_week_s_bulletin_is_the_latest_service_dated_before_the_date(church, pastor, make_church):
    def save(church_id, day, coffee):
        week = dataclasses.replace(WEEK, announcements=Announcements(coffee_hour=coffee))
        return archive.create_service(church_id, pastor, service(service_date=day, bulletin=week))

    save(church, date(2026, 9, 20), "Two weeks ago")
    save(church, date(2026, 9, 27), "Last week, first save")
    later = save(church, date(2026, 9, 27), "Last week, saved later")
    save(church, D, "This week")                                # the date itself is not before it
    legacy_row(church, service_date_iso="", bulletin={"announcements": {"coffee_hour": "Undated"}})
    save(make_church(name="Other", owner_user_id=pastor), date(2026, 10, 1), "Another church")
    found = archive.previous_bulletin(church, D)
    assert (found.service_id, found.service_date_iso) == (later.id, "2026-09-27")
    # Only the music and the announcements carry; the people, part leaders and pasted text start empty.
    assert found.bulletin == ServiceBulletin(prelude=WEEK.prelude, announcements=Announcements(
        coffee_hour="Last week, saved later")).to_json()
    nothing = archive.previous_bulletin(church, date(2026, 9, 20))
    assert (nothing.service_id, nothing.service_date_iso, nothing.bulletin) == (None, None, BLANK)


def test_a_service_saved_before_2b_carries_an_empty_bulletin(church, pastor):
    archive.create_service(church, pastor, service(service_date=date(2026, 9, 20), bulletin=WEEK))
    legacy = legacy_row(church, service_date_iso="2026-09-27")             # bulletin NULL
    found = archive.previous_bulletin(church, D)
    assert (found.service_id, found.bulletin) == (legacy, BLANK)
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_usecase_archive.py backend/tests/test_api_services.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1`
**Expected:** `12 failed, 65 passed in <t>s`: the four usecase tests (`ServiceInput` has no `bulletin`), the seven API tests and cases (`bulletin` is an extra field, a 422 naming `bulletin` rather than the field inside it; no `/services/previous-bulletin`, a 422 for the id), the printed one (a 422 too). `test_no_streamlit_in_core.py` passes (the module exists since T2).

- [ ] **Step 3: The schemas, the usecases, the repo, the route, the download, the types**

**In `backend/api/schemas.py`, replace:**

````python
import liturgy_config
````

**with:**

````python
import bulletin_settings
import liturgy_config
import service_bulletin
````

**In `backend/api/schemas.py`, replace:**

````python

class ServiceDraft(BaseModel):
````

**with:**

````python

# --- printed bulletin PR 2b: the week's bulletin fields (service_bulletin; spec "Data model") ---

def _bulletin_text(name: str):
    return Annotated[str, Field(max_length=service_bulletin.MAX_LENGTH[name])]


class BulletinMusic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: _bulletin_text("title")
    composer: _bulletin_text("composer")


class BulletinPeople(BaseModel):
    """This week's people: null prints the standing name from the bulletin settings, "" no one."""

    model_config = ConfigDict(extra="forbid")

    worship_leader: Optional[_bulletin_text("person")]
    liturgist: Optional[_bulletin_text("person")]
    organist: Optional[_bulletin_text("person")]


class BulletinAnnouncements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ushers: _bulletin_text("ushers")
    deacon: _bulletin_text("deacon")
    coffee_hour: _bulletin_text("coffee_hour")
    activities: _bulletin_text("activities")
    prayer_concerns: _bulletin_text("prayer_concerns")
    collection: _bulletin_text("collection")
    other: _bulletin_text("other")


class BulletinReadingText(BaseModel):
    """Pasted text of the first and New Testament readings ("" = fetch it)."""

    model_config = ConfigDict(extra="forbid")

    ot: _bulletin_text("reading_text")
    nt: _bulletin_text("reading_text")


class ServiceBulletin(BaseModel):
    """The printed bulletin's weekly fields (PR 2b), every field present. Texts
    are not checked for line breaks: the server reads them tolerantly
    (service_bulletin.read: a one-line field's line breaks become spaces), so a
    download never meets a 422 for one. `unchecked` names the boxes whose text
    came from last week and is not checked yet."""

    model_config = ConfigDict(extra="forbid")

    prelude: BulletinMusic
    postlude: BulletinMusic
    people: BulletinPeople
    leaders: dict[Literal[bulletin_settings.ELEMENT_KEYS], _bulletin_text("person")]
    announcements: BulletinAnnouncements
    reading_text: BulletinReadingText
    # The boxes still holding last week's text, not checked yet (saved, so the marks come back on open).
    unchecked: list[Literal[service_bulletin.CARRY_KEYS]] = Field(max_length=len(service_bulletin.CARRY_KEYS))


class ServiceDraft(BaseModel):
````

**In `backend/api/schemas.py`, replace:**

````python
    SectionKey are imported unchanged. Usecases take `to_input()`."""
````

**with:**

````python
    SectionKey are imported unchanged. Usecases take `to_input()`.
    `bulletin` (printed bulletin PR 2b) is optional, so a client from before
    2b keeps working: a POST without it saves no bulletin, a PUT without it
    keeps the saved one."""
````

**In `backend/api/schemas.py`, replace:**

````python
                                                   max_length=liturgy_config.LIMITS.max_custom_elements)
````

**with:**

````python
                                                   max_length=liturgy_config.LIMITS.max_custom_elements)
    bulletin: Optional[ServiceBulletin] = None
````

**In `backend/api/schemas.py`, replace:**

````python
            custom_elements=tuple(CustomElement(e.label, e.text, e.insert_after) for e in self.custom_elements))
````

**with:**

````python
            custom_elements=tuple(CustomElement(e.label, e.text, e.insert_after) for e in self.custom_elements),
            bulletin=None if self.bulletin is None else service_bulletin.read(self.bulletin.model_dump()))
````

**In `backend/api/schemas.py`, replace:**

````python
    custom_elements: list[CustomElementOut]
````

**with:**

````python
    custom_elements: list[CustomElementOut]
    bulletin: ServiceBulletin           # PR 2b; nothing filled in for a service saved without one
````

**In `backend/api/schemas.py`, replace:**

````python
    saved_at: str
    created_by: Optional[AuthorOut]
````

**with:**

````python
    saved_at: str
    created_by: Optional[AuthorOut]


class PreviousBulletinOut(BaseModel):
    """GET /services/previous-bulletin (PR 2b, carry forward): the music and the
    announcements of the church's latest service dated before the date (the
    people, part leaders and pasted texts empty), or nulls and an empty
    bulletin when there is none."""

    service_id: Optional[uuid.UUID]
    service_date_iso: Optional[str]
    bulletin: ServiceBulletin
````

**In `backend/usecases/archive.py`, replace:**

````python

No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
````

**with:**

````python

Printed bulletin PR 2b adds the week's bulletin fields (service_bulletin):
clean_input makes them Word-safe; a save stores them in services.bulletin;
a POST without them stores NULL and a PUT without them keeps the saved ones
(a client from before 2b); opening reads them tolerantly (NULL is an empty
bulletin). previous_bulletin gives what a new week carries forward. Nothing
logs a bulletin's text (prayer concerns can name people).

No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
````

**In `backend/usecases/archive.py`, replace:**

````python
from repos import services as services_repo
````

**with:**

````python
from repos import services as services_repo
from service_bulletin import ServiceBulletin
from service_bulletin import read as read_bulletin
````

**In `backend/usecases/archive.py`, replace:**

````python
    custom_elements: tuple[CustomElement, ...] = ()
````

**with:**

````python
    custom_elements: tuple[CustomElement, ...] = ()
    bulletin: Optional[ServiceBulletin] = None   # None: not sent (a client from before printed bulletin PR 2b)
````

**In `backend/usecases/archive.py`, replace:**

````python
                              for e in data.custom_elements),
````

**with:**

````python
                              for e in data.custom_elements),
        bulletin=None if data.bulletin is None else data.bulletin.map_texts(clean),
````

**In `backend/usecases/archive.py`, replace:**

````python
    custom_elements: list[CustomElement]
````

**with:**

````python
    custom_elements: list[CustomElement]
    bulletin: dict                              # service_bulletin's stored shape; empty when none was saved
````

**In `backend/usecases/archive.py`, replace:**

````python
    offset: int
````

**with:**

````python
    offset: int


@dataclass(frozen=True)
class PreviousBulletinData:
    service_id: Optional[uuid.UUID]             # None: no service dated before the date
    service_date_iso: Optional[str]
    bulletin: dict                              # what carries: the music and the announcements
````

**In `backend/usecases/archive.py`, replace:**

````python
                            for e in clean.custom_elements],
````

**with:**

````python
                            for e in clean.custom_elements],
        # Not sent: a POST stores NULL, a PUT keeps the saved bulletin (printed bulletin PR 2b).
        **({} if clean.bulletin is None else {"bulletin": clean.bulletin.to_json()}),
````

**In `backend/usecases/archive.py`, replace:**

````python
        custom_elements=_archived_custom_elements(row.custom_elements),
````

**with:**

````python
        custom_elements=_archived_custom_elements(row.custom_elements),
        bulletin=read_bulletin(row.bulletin).to_json(),
````

**In `backend/usecases/archive.py`, replace:**

````python
    _log("delete", cid, deleted_id, usage_rows, started)
````

**with:**

````python
    _log("delete", cid, deleted_id, usage_rows, started)


def previous_bulletin(church_id: uuid.UUID, before: datetime.date) -> PreviousBulletinData:
    """GET /services/previous-bulletin (printed bulletin PR 2b, carry forward):
    the church's latest service dated before `before` (the latest date, then
    the latest save; undated services never count) and what of its bulletin
    carries to a new week: the music and the announcements. A service saved
    without a bulletin (before 2b) carries an empty one."""
    cid = as_uuid(church_id)
    with session_scope() as s:
        row = services_repo.previous_service(cid, before.isoformat(), session=s)
        if row is None:
            return PreviousBulletinData(None, None, ServiceBulletin().to_json())
        return PreviousBulletinData(row.id, normalize_date_iso(row.service_date_iso),
                                    read_bulletin(row.bulletin).carried().to_json())
````

**Append to `backend/repos/services.py`:**

````python


def previous_service(church_id, before_iso: str, *, session: Session) -> Optional[Service]:
    """The church's service with the latest real date before `before_iso`
    (YYYY-MM-DD), then the latest save, then the highest id (LIST_ORDER), or
    None. Undated rows (SORT_DATE NULL) never count (printed bulletin PR 2b)."""
    stmt = (select(Service).where(Service.church_id == as_uuid(church_id), SORT_DATE < before_iso)
            .order_by(*LIST_ORDER).limit(1))
    return session.execute(stmt).scalar_one_or_none()
````

**In `backend/api/routes/services.py`, replace:**

````python
- GET /services: 20 a page by default, newest service date first, undated last.
````

**with:**

````python
- GET /services: 20 a page by default, newest service date first, undated last.
- GET /services/previous-bulletin?before=YYYY-MM-DD (printed bulletin PR 2b):
  what a new week's bulletin carries forward from the latest service dated
  before that date. Declared before /services/{service_id}, which would
  otherwise take "previous-bulletin" as an id.
````

**In `backend/api/routes/services.py`, replace:**

````python
from typing import Optional
````

**with:**

````python
from typing import Annotated, Optional
````

**In `backend/api/routes/services.py`, replace:**

````python
from api.schemas import DeletedOut, Page, ServiceDraft, ServiceOut, ServiceSummary
````

**with:**

````python
from api.schemas import DeletedOut, IsoDate, Page, PreviousBulletinOut, ServiceDraft, ServiceOut, ServiceSummary
````

**In `backend/api/routes/services.py`, replace:**

````python
                                limit=page.limit, offset=page.offset)
````

**with:**

````python
                                limit=page.limit, offset=page.offset)


@router.get("/services/previous-bulletin", response_model=PreviousBulletinOut,
            responses=error_responses(401, 403, 422, 503))
def previous_bulletin(before: Annotated[IsoDate, Query()],
                      church: ActiveChurch = Depends(require_church)) -> PreviousBulletinOut:
    return PreviousBulletinOut(**asdict(archive.previous_bulletin(church.id, before)))
````

**In `backend/usecases/documents.py`, replace:**

````python
words.
````

**with:**

````python
words. PR 2b adds the week's own fields as posted (the draft's bulletin):
the music, this week's people and part leaders, the announcements, and a
pasted reading text, which prints instead of the fetched one and is neither
fetched nor charged; a body with no bulletin (a page from before PR 2b-2)
prints PR 1's placeholders. The log line never carries a bulletin's text.
````

**In `backend/usecases/documents.py`, replace:**

````python
from db import session_scope
````

**with:**

````python
from db import session_scope
from service_bulletin import ServiceBulletin
````

**In `backend/usecases/documents.py`, replace:**

````python
    refs = [ref for ref in (ot, nt) if ref]
    texts = reading_texts(refs, tid, charge) if refs else {}
    printed = printed_bulletin.PrintedService(
        church_name=archive._xml_safe(church["name"] or "").strip(), resolved=resolved,
        ot=None if ot is None else printed_bulletin.Reading(ot, texts.get(ot)),
        nt=None if nt is None else printed_bulletin.Reading(nt, texts.get(nt)),
        translation_label=scripture_fetcher.translation_label(tid),
        settings=church_bulletin.read_settings(church["settings"]))
````

**with:**

````python
    week = ServiceBulletin() if clean.bulletin is None else clean.bulletin
    pasted = ((ot, week.ot_text), (nt, week.nt_text))
    refs = [ref for ref, text in pasted if ref and not text]           # a pasted reading is not fetched
    texts = reading_texts(refs, tid, charge) if refs else {}

    def reading(ref: Optional[str], text: str) -> Optional[printed_bulletin.Reading]:
        if ref is None:
            return None
        return printed_bulletin.Reading(ref, text, pasted=True) if text else printed_bulletin.Reading(
            ref, texts.get(ref))

    printed = printed_bulletin.PrintedService(
        church_name=archive._xml_safe(church["name"] or "").strip(), resolved=resolved,
        ot=reading(*pasted[0]), nt=reading(*pasted[1]),
        translation_label=scripture_fetcher.translation_label(tid),
        settings=church_bulletin.read_settings(church["settings"]),
        bulletin=clean.bulletin)                        # None (a page from before PR 2b-2): PR 1's placeholders
````

**In `frontend/src/lib/api/types.ts`, replace:**

````ts
export type DeletedOut = components["schemas"]["DeletedOut"];
````

**with:**

````ts
export type DeletedOut = components["schemas"]["DeletedOut"];
/**
 * A service's printed-bulletin fields (printed bulletin PR 2b): the music, this
 * week's people and part leaders, the announcements and the pasted reading
 * text; and `GET /services/previous-bulletin`, what a new week carries forward.
 */
export type ServiceBulletin = components["schemas"]["ServiceBulletin"];
export type PreviousBulletin = components["schemas"]["PreviousBulletinOut"];
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  SectionResult,
````

**with:**

````ts
  SectionResult,
  ServiceBulletin,
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
    created_by: { id: USER_ID, name: "Pat Pastor" },
    saved_at: "2026-10-01T14:42:00.123456+00:00",
````

**with:**

````ts
    bulletin: serviceBulletin(),
    created_by: { id: USER_ID, name: "Pat Pastor" },
    saved_at: "2026-10-01T14:42:00.123456+00:00",
    ...overrides,
  };
}

/** A service's bulletin fields (printed bulletin PR 2b) with nothing filled in, unless overridden. */
export function serviceBulletin(overrides: Partial<ServiceBulletin> = {}): ServiceBulletin {
  return {
    prelude: { title: "", composer: "" },
    postlude: { title: "", composer: "" },
    people: { worship_leader: null, liturgist: null, organist: null },
    leaders: {},
    announcements: { ushers: "", deacon: "", coffee_hour: "", activities: "", prayer_concerns: "", collection: "", other: "" },
    reading_text: { ot: "", nt: "" },
    unchecked: [],
````

- [ ] **Step 4: Regenerate the API files; see them pass, the suite, types and lint**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api >/dev/null) && git diff --stat -- frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts | tail -1
.venv/bin/python -m pytest -q backend/tests/test_usecase_archive.py backend/tests/test_api_services.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `Wrote <repo>/frontend/src/lib/api/openapi.json`, then ` 2 files changed, 546 insertions(+), 1 deletion(-)`; `77 passed in <t>s`; `1425 passed, 17 skipped in <t>s` (`test_openapi_contract.py` and `test_route_guards.py` pass unchanged); ` Test Files  85 passed (85)`, `      Tests  675 passed (675)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add backend/api/schemas.py backend/usecases/archive.py backend/repos/services.py backend/api/routes/services.py backend/usecases/documents.py backend/tests/test_usecase_archive.py backend/tests/test_api_services.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts frontend/src/lib/api/types.ts frontend/src/test/fixtures/index.ts
git commit -q -m "Printed bulletin PR 2b-1: the API saves, opens, carries and prints the bulletin" -m "ServiceDraft gains an optional bulletin (every field present, within
its limits, the boxes still to check included; a page from before the
Bulletin step sends none: a POST stores NULL, a PUT keeps the saved one
and the printed bulletin prints PR 1's placeholders); ServiceOut answers
it, empty when none was saved. GET /services/previous-bulletin?before=
answers the music and announcements of the church's latest service dated
before that date, for carry forward. The printed bulletin prints the
posted fields, and a pasted reading is neither fetched nor charged.
Every text is made Word-safe and none is logged. OpenAPI snapshot and
types regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1425 passed, 17 skipped`; frontend `675 passed` in 85 files.

### Task 4: Docs: the owner's checks for PR 2b-1 and the spec's data model (planning answers 1, 5, 8; clarifications 17, 19)

**Files:**
- Modify: `docs/manual-verification.md`, `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`

- [ ] **Step 1: Append the 2b heading and items 16-18; amend the spec's "Data model" and "Scope by PR"**

**Append to `docs/manual-verification.md`:**

````markdown

### Printed bulletin PR 2b: the Bulletin step

PR 2b ships as two PRs, backend first: **PR 2b-1** (migration
`0006_services_bulletin`; the server saves, opens, carries and prints the
week's fields; the builder itself does not change) and, once 2b-1 is live
and checked, **PR 2b-2** (the Bulletin step). From PR 2b-2 the builder has
five steps: **4 Bulletin** comes before **5 Review & send** (earlier items
say "4 Review & send"). Before the PR 2b-1 merge the owner runs the steps of
`backend/migrations/README.md` → "Before 0006_services_bulletin" (items 16
and 17); after each merge, the owner's guided check (one step at a time on
the phone) covers the items marked "(owner, after PR 2b-1)" or "(owner,
after PR 2b-2)". The results go into `docs/ops-runbook.md` → "Printed
bulletin PR 2b-1 record" and "Printed bulletin PR 2b-2 record". Use
invented announcements for the checks, or the church's real ones only on
the owner's own phone; record what the page and the files show, never a
name from the prayers and concerns, an email address, a phone number, a
street address or a church id.

- [ ] (owner, before the PR 2b-1 merge) **16.** A green `db-backup` run; the read-only counts (version `0005_services_extras`, saved services, churches); the SQL preview read: one `ADD COLUMN bulletin JSON` between `BEGIN;` and `COMMIT;`, under the 5 s lock timeout.
- [ ] (owner, after PR 2b-1) **17.** The after-deploy query shows `0006_services_bulletin`, `1` and `with_bulletin` `0`, and the counts are unchanged (or grew by the services saved since).
- [ ] (owner, after PR 2b-1) **18.** The builder works as before (four steps): open a saved service from **Services**, tap **Save changes**, and download the printed bulletin from **4 Review & send**: the save works, and the PDF still prints the music and the announcements as [placeholders], as the Printed bulletin card says.
````

**In `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`, replace:**

````markdown
  composer}, postlude: {title, composer}, leaders: {element key: name}, announcements: {ushers,
  deacon, coffee_hour, activities, prayer_concerns, collection}, reading_text: {ot, nt},
  cover_image_id}`. The draft gains the field with a version bump (v2 to v3, migrating with an
````

**with:**

````markdown
  composer}, postlude: {title, composer}, people: {worship_leader, liturgist, organist} (null:
  the settings' name; PR 2 planning answer 7), leaders: {element key: name}, announcements:
  {ushers, deacon, coffee_hour, activities, prayer_concerns, collection, other} (answer 4),
  reading_text: {ot, nt}, unchecked: [box]}` (`unchecked`: the boxes still holding last week's
  text, not checked yet, so the marks come back when the service is opened again), and PR 3 adds
  `cover_image_id` (PR 2b plan, `docs/superpowers/plans/2026-10-03-printed-bulletin-2b.md`). The draft gains the field with a version bump (v2 to v3, migrating with an
````

**In `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`, replace:**

````markdown
  picture id; the per-element leaders and pasted reading texts start empty.
````

**with:**

````markdown
  picture id; the per-element leaders and pasted reading texts start empty. As planned for PR 2b:
  only a draft that is not a saved service, when the Bulletin step or Review & send shows it for
  its date, into each box not yet typed in, edited or kept (a box at a time); each carried box
  shows "From last week. Check before printing." until it is edited or kept (planning answer 5),
  and the marks are saved with the service. A saved service saved again as a new service on
  another date ("Save as new service") is treated the same way: its music and announcements are
  marked to check, and this week's people, the part leaders and the pasted texts start empty.
````

**In `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`, replace:**

````markdown
  guided phone check.
````

**with:**

````markdown
  guided phone check. PR 2b ships backend first as two PRs: 2b-1 (the migration, the API saving,
  opening, carrying and printing the weekly fields; a page from before 2b-2 keeps working and
  prints PR 1's placeholders) is merged and live before 2b-2 (the draft v3, the Bulletin step,
  carry forward and the card). PR 3 follows the same order (its API and migration first).
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '^## ' docs/manual-verification.md | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md docs/superpowers/specs/2026-10-02-printed-bulletin-design.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected:** `89 passed in <t>s` (`test_slice1_docs.py` pins the last eight `##` headings, ending `## Printed bulletin`: the new heading is a `###`, so the pin holds); `282:## Printed bulletin`; `4`; `0`; ` 2 files changed, 39 insertions(+), 5 deletions(-)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md docs/superpowers/specs/2026-10-02-printed-bulletin-design.md
git commit -q -m "Docs: printed bulletin PR 2b-1 manual checks and the spec's data model" -m "docs/manual-verification.md gains \"### Printed bulletin PR 2b: the
Bulletin step\" under \"## Printed bulletin\": PR 2b ships backend first in
two PRs; the owner's steps around migration 0006 and the check that the
builder works as before after PR 2b-1 (items 16-18). The spec's \"Data
model\" gains people, other announcements, the unchecked boxes and when
carry forward happens (Save as new service included); \"Scope by PR\"
says 2b-1 ships before 2b-2 and PR 3 follows the same order." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1425 passed, 17 skipped`; frontend `675 passed` in 85 files.

- [ ] **Step 4 (controller): Review the batch (T1-T4) and backup push**

One review of PR 2b-1: the revision is expand-only and its `--sql` is exactly clarification 14's six lines; the README's queries are read-only and match the Postgres test; `ServiceDraft.bulletin` is optional, a `POST` without it stores NULL, a `PUT` without it keeps the saved one, and a download without it prints PR 1's placeholders (the old pages change in nothing); every bulletin text is Word-safe and none is logged; a free text's U+2028, U+2029 and U+0085 are newlines; `previous_bulletin` filters on the church, skips undated rows and takes the latest date then the latest save; the printed bulletin prints nothing for a blank field and leaves the announcements page out when it is empty, in both renderers; a pasted reading is neither fetched nor charged, and the credit line names only fetched text; the regenerated types change no page. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

### Task 5: Verification and the draft PR 2b-1 (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N1>` PR 2b-1's number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
git merge-base --is-ancestor 9c731e1 origin/main; echo "PR 2a record on main: $?"
ls backend/migrations/versions | grep -c '^0'
git ls-tree --name-only origin/main backend/migrations/versions/ | grep -c '/0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `PR 2a record on main: 1` (it rides along: Step 3's list has `M docs/ops-runbook.md`; `0` if a records PR merged it meanwhile, and then that line is absent); `6`; `5`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 5)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner. **If `main` gained a migration** (the last count is not 5), stop: `0006` must be renumbered onto the new head (F §3.5 chain rule) before anything else, and the owner told.

- [ ] **Step 2 (agent): Both suites, Postgres, the frontend, types, lint, the build, a sample booklet**

```bash
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/builder/")
(cd backend && ../.venv/bin/python -c "
import datetime, bulletin_settings as bs, printed_bulletin as pb, printed_pdf, printed_docx, service_bulletin as sb
from service_output import ResolvedService, ResolvedHymn
r = ResolvedService(service_date=datetime.date(2026, 10, 11), hymns={'opening': ResolvedHymn('God Is Here!', 409), 'response': None, 'closing': None}, liturgy={'call_to_worship': 'Leader: Lift up your hearts. People: We lift them up.'}, sermon_title='Who Said?')
s = bs.read({'bulletin': {'address_lines': ['100 Example Street', 'Springfield, ST 00000'], 'phone': '(555) 010-0100', 'service_time': '10:30 a.m.', 'worship_leader': 'Rev. Alex Example', 'liturgist': 'Sam Sample', 'organist': 'Jordan Doe'}})
w = sb.read({'prelude': {'title': 'Morning Voluntary', 'composer': 'Pat Example'}, 'postlude': {'title': 'Festive Postlude', 'composer': 'Lee Sample'}, 'people': {'worship_leader': 'Rev. Guest'}, 'leaders': {'sermon': 'Pat Example'}, 'announcements': {'ushers': 'Sam Sample, Jordan Doe', 'deacon': 'Alex Example', 'coffee_hour': 'The Example family', 'activities': 'Tuesday: Bible study at 10 a.m. Wednesday: Choir at 7 p.m.', 'prayer_concerns': 'For all who are ill.', 'collection': 'Canned goods for the food pantry.', 'other': 'The office is closed on Monday.'}, 'reading_text': {'nt': 'Jesus said, What do you think?'}})
ps = pb.PrintedService('Example Church', r, pb.Reading('Psalm 25:1-9', 'In you, Lord, I put my trust. ' * 30), pb.Reading('Matthew 21:23-32', w.nt_text, pasted=True), 'World English Bible (WEB)', s, w)
open('<scratch>/printed2b-sample.pdf', 'wb').write(printed_pdf.render_pdf(ps)); open('<scratch>/printed2b-sample.docx', 'wb').write(printed_docx.render_docx(ps)); print('sample written')
")
```

**Expected:** `1425 passed, 17 skipped in <t>s`; ` Test Files  85 passed (85)` and `      Tests  675 passed (675)` with no `×` or `FAIL` line; `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s`, the builder's route lines (`○ /builder/hymns`, `○ /builder/liturgy`, `○ /builder/readings`, `○ /builder/review`: no `/builder/bulletin` yet) and no `Error` (a font `Failed to fetch` only: say so and rely on CI); `sample written`. With a local, throwaway Postgres also `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `17 passed, 1425 deselected`. Open the sample PDF and look at it: two sides; page 1's header with "Rev. Guest, Worship Leader", "PRELUDE: ‘Morning Voluntary’" with "Jordan Doe" and "- Pat Example", the NT reading "Jesus said, What do you think?" followed by "The First Reading is from the World English Bible (WEB).", "SERMON: “Who Said?”" with "Pat Example"; page 2 ending with the postlude and "*Congregation stands if able"; page 3 the announcements, each filled field, the activities on two lines (no "?"), "OTHER ANNOUNCEMENTS" last. Attach both samples to the owner's message in Step 4 if the channel allows files, else describe them.

- [ ] **Step 3 (agent): The API files match, the preview, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0005_services_extras:0006_services_bulletin --sql 2>/dev/null | grep -v -e '^--' -e '^$')
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/service_bulletin.py backend/printed_bulletin.py backend/usecases/archive.py backend/usecases/documents.py backend/repos/services.py; echo "imports grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations/env.py backend/service_archive.py backend/service_output.py backend/bulletin_settings.py backend/api/routes/documents.py .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt app.py streamlit_views streamlit_tests frontend/src/components frontend/src/app frontend/src/lib/draft frontend/src/lib/queries frontend/src/lib/documents.ts | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); the six preview lines of clarification 14 exactly; `imports grep exit 1`; exactly these paths (without `M docs/ops-runbook.md` when Step 1 printed `0`):
```
M	backend/api/routes/services.py
M	backend/api/schemas.py
M	backend/db/models.py
M	backend/migrations/README.md
A	backend/migrations/versions/0006_services_bulletin.py
M	backend/printed_bulletin.py
M	backend/printed_docx.py
M	backend/printed_pdf.py
M	backend/repos/services.py
A	backend/service_bulletin.py
M	backend/tests/test_api_app.py
M	backend/tests/test_api_printed.py
M	backend/tests/test_api_services.py
M	backend/tests/test_migrations.py
M	backend/tests/test_no_streamlit_in_core.py
M	backend/tests/test_printed_bulletin.py
M	backend/tests/test_printed_render.py
M	backend/tests/test_schema_check.py
A	backend/tests/test_service_bulletin.py
M	backend/tests/test_services_postgres.py
M	backend/tests/test_usecase_archive.py
M	backend/usecases/archive.py
M	backend/usecases/documents.py
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-03-printed-bulletin-2b.md
M	docs/superpowers/specs/2026-10-02-printed-bulletin-design.md
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/types.ts
M	frontend/src/test/fixtures/index.ts
```
`0` (no page, component, draft, query or body code: the builder is unchanged); the subjects oldest first: `Runbook: printed bulletin PR 2a record (owner's phone check)` (when it rides along), the plan commits (`WIP plan: printed bulletin PR 2b …`, `Plan: printed bulletin PR 2b (the Bulletin step)` and any later plan commit), then T1-T4's four subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR 2b-1**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> The first half of the Bulletin step (printed bulletin PR 2b-1, the server's part) is verified on this machine: backend 1425 passed, 17 skipped (1395 and 16 before; the new skipped one is a database check that CI runs on Postgres); frontend unchanged at 675 tests in 85 files; typecheck, lint and the production build are clean. It adds one database change, migration 0006 (one new empty column), and teaches the server to save, open and print a service's bulletin fields (the music, the announcements, this week's names, pasted reading text). Nothing you see changes yet: the builder keeps its four steps, and the printed bulletin keeps its [placeholders] until the second PR (2b-2, the Bulletin step itself), which I will open only after this one is live and checked. Before it merges I will ask you for the backup, the counts and a look at the SQL, one at a time. May I open the pull request as a **draft** titled "Printed bulletin PR 2b-1: the server saves and prints the bulletin fields", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/printed2b1-pr-body.md" <<'BODY'
Printed bulletin PR 2b-1: the server's half of the Bulletin step (PR 2 planning answers of 2026-10-02; PR 2b ships backend first in two PRs). Spec: docs/superpowers/specs/2026-10-02-printed-bulletin-design.md. Plan: docs/superpowers/plans/2026-10-03-printed-bulletin-2b.md (Tasks 1-6). One migration (0006_services_bulletin); no new package or variable. The builder does not change: today's pages send no bulletin and keep working.

- Migration 0006_services_bulletin (expand-only): services.bulletin JSON NULL. No backfill. env.py's 5 s lock timeout applies. Before the merge: a backup, read-only counts and the SQL preview (backend/migrations/README.md, "Before 0006_services_bulletin").
- service_bulletin (pure): the prelude and postlude, this week's people and part leaders, the announcements (with Other announcements), the pasted reading text, the boxes still to check; read tolerantly (every line break of a free text a newline, U+2028 and U+2029 included).
- The printed bulletin prints them: a blank field prints nothing, no announcements page when all are blank, a pasted reading with no credit line and no fetch (a fetched one beside it keeps its own line). A body without a bulletin (today's pages) prints PR 1's placeholders as before.
- API: ServiceDraft.bulletin (optional: a POST without it stores NULL, a PUT without it keeps the saved one), ServiceOut.bulletin, GET /services/previous-bulletin?before= for carry forward. OpenAPI and types regenerated.
- docs/manual-verification.md: "### Printed bulletin PR 2b: the Bulletin step", items 16-18; the spec's data model.

Next: PR 2b-2 (the Bulletin step), opened after this one is live and checked. Then PR 3 (the cover picture), backend first in the same way.

Tests: backend 1395 → 1425 passed, 16 → 17 skipped; frontend 675 in 85 files (unchanged)

After merge (Task 6): the owner's after-deploy check (one read-only query) and a short phone check that the builder works as before, then a "Printed bulletin PR 2b-1 record" in docs/ops-runbook.md (it rides along in PR 2b-2).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Printed bulletin PR 2b-1: the server saves and prints the bulletin fields" \
  --body-file "<scratch>/printed2b1-pr-body.md"
gh pr checks <N1> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1425 passed, 17 skipped`, backend-postgres `17 passed, 1425 deselected` (after its `alembic upgrade head`, `alembic check`, `downgrade base`, `upgrade head` steps, now through `0006`), frontend `675 passed` in 85 files. Then send: "PR #<N1> is green: backend 1425 passed, 17 skipped; the Postgres job ran the migration up, down and up again and passed its 17 tests; 675 frontend tests in 85 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you, after the backup, the counts and the SQL check." On the yes: `gh pr ready <N1> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_migrations.py` (the 0006 tests, the README pin), `test_schema_check.py`, `test_api_app.py`, `test_services_postgres.py`, CI's alembic cycle | T1 |
| `test_service_bulletin.py`, `test_printed_bulletin.py`, `test_printed_render.py` | T2 |
| `test_usecase_archive.py`, `test_api_services.py`, `test_api_printed.py`, `test_no_streamlit_in_core.py`, `test_openapi_contract.py`, `test_route_guards.py`, typecheck | T3 (`test_api_printed.py`'s 2a test: T2) |
| `test_slice1_docs.py`, `test_docs.py` | T4 |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, printed bulletin PR 2b-1 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1425 passed, 17 skipped`; frontend `675 passed` in 85 files.

### Task 6: PR 2b-1: before the merge (backup, counts, SQL), the merge, the after-deploy check, the owner's check, the record (OWNER + agent)

The owner's steps go **one at a time** (send one, wait for the report or "next"). The agent writes each result into `<scratch>/printed2b1-t6-results.md` (not committed). Record numbers and what the screens and files showed, never a token, an email address, a phone number, a street address, a church id or a database URL. The queries are the ones in `backend/migrations/README.md` → "Before 0006_services_bulletin" (pinned by T1's tests); copy them from there.

**Files:** Modify (Step 7): `docs/ops-runbook.md`: insert `### Printed bulletin PR 2b-1 record` right before `## Backups` (after the last `###` record above it; today "Printed bulletin PR 2a record", whose table's last row starts `| Follow-ups |`). A `###` heading, because `test_ops_workflows.py` pins the `##` list. The record is committed on the branch and rides along in PR 2b-2 (no records PR of its own).

- [ ] **Step 1 (agent → OWNER, then agent): The backup**

Check first (not replayed): `gh pr view <N1> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send:

> PR #<N1> (printed bulletin PR 2b-1, the server's half) is ready and green. Before it merges you asked for three checks, as for migration 0005; here is the first. May I start a fresh database backup now (the db-backup workflow on main, about a minute)? Nothing else happens yet.

On a clear yes (not replayed):

```bash
gh workflow run db-backup --ref main -R bbrown62450/church
RUN=$(gh run list -R bbrown62450/church --workflow backup.yml --branch main --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId'); echo "$RUN"
gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 15 >/dev/null; echo "backup exit $?"
gh run view "$RUN" -R bbrown62450/church --json url,conclusion --jq '"\(.conclusion) \(.url)"'
gh api "repos/bbrown62450/church/actions/runs/$RUN/artifacts" --jq '.artifacts[] | "\(.name) \(.size_in_bytes)"'
```

**Expected:** a run id (started a few seconds ago; if `gh run list` shows an older run, wait and list again); `backup exit 0`; `success <run URL>`; `db-backup <bytes>`. Record the URL and the size. A failure: stop and tell the owner; nothing merges without a green backup.

- [ ] **Step 2 (OWNER, then agent): The counts (read-only)**

Send, with the query from README step 2 pasted in full inside a code block:

> Second check: one read-only query; it only counts. Open Supabase → your project → SQL Editor → New query, paste the query below, and press Run. You should see one row with three values. Please tell me what each column shows: version, services, churches.

**Expected:** `version` `0005_services_extras`; `services` the number of saved services in all churches; `churches` the number of churches with at least one. Record the three values. If `version` is not `0005_services_extras`, stop and tell the owner what it means before going on.

- [ ] **Step 3 (agent → OWNER): The SQL the migration will run**

(not replayed)
```bash
git fetch origin && git status -sb | head -1
(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0005_services_extras:0006_services_bulletin --sql 2>/dev/null | grep -v -e '^--' -e '^$')
```

**Expected:** the branch even with `origin/claude/slice-2-plan-4q33le` (the PR's code); the six lines of clarification 14 exactly. Send them in a code block with:

> Third check: these are the six lines of SQL the migration will run on the database when the PR merges, rendered from the PR's code without touching the database. In plain words: start one transaction; give up after 5 seconds if the services table is busy (the old version then keeps running and we retry); add one empty column to the saved services, to hold each service's bulletin fields; note the new version; finish. No row is copied, changed or deleted. Does that look right to you?

Record the owner's answer.

- [ ] **Step 4 (agent → OWNER): Ask to merge, then merge**

Send: "The backup is green, the counts are recorded and you have read the SQL. May I merge PR #<N1> with a merge commit? Railway then runs the migration before the new server starts. The website does not change with this PR, so you can keep using the builder while it deploys; I will tell you when it is live, then ask for one more read-only query and a short phone check." On a clear yes (not replayed):

```bash
gh pr merge <N1> --merge -R bbrown62450/church
gh pr view <N1> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N1> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both.

- [ ] **Step 5 (agent, then OWNER): The deploy and the after-deploy check (manual-verification item 17)**

About three minutes after the merge (not replayed):

```bash
curl -s https://church-production-74ca.up.railway.app/health/ready; echo
curl -s https://church-production-74ca.up.railway.app/openapi.json | grep -c '"/services/previous-bulletin"'
curl -s -o /dev/null -w '%{http_code}\n' "https://church-production-74ca.up.railway.app/services/previous-bulletin?before=2026-10-11"
```

**Expected:** `{"ok":true,"db":"ok"}` (in production this answers 503 `schema_behind` while the database is behind the release, so `ok` means `0006` is applied and the new release is live); `1`; `401` (the route exists and wants a sign-in). If `/openapi.json` still lacks the route, wait a minute and retry; after ten minutes, ask the owner to open Railway → the API service → Deployments and read the newest deployment's status (a failed pre-deploy on the 5 s lock timeout: the old server keeps serving and nothing is broken, since the website does not need the new server yet; redeploy on the owner's yes). Then send, with README step 4's query in a code block, and step 2's query again:

> The new server is live. One more read-only check: in the SQL Editor, run the first query below; it should show 0006_services_bulletin, 1, and 0 (nothing uses the new column until the Bulletin step arrives). Then run the counting query from before again; the numbers should be the same as last time, or a little higher if a service was saved meanwhile. Also, if you have Railway open: the newest deployment's logs should include a line "Running upgrade 0005_services_extras -> 0006_services_bulletin". What do you see?

Record the values. A version other than `0006_services_bulletin`, a `with_bulletin` other than `0`, or fewer services than before: stop and look before anything else.

- [ ] **Step 6 (OWNER, then agent): Phone: the builder works as before (item 18)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. Open a saved service from **Services**, then on **4 Review & send** tap **Save changes**, then **Download printed bulletin**. Does the save work, and does the PDF still show the music and the announcements as [placeholders], as the Printed bulletin card says? (Nothing is meant to change yet.)

Record the answers. Anything else than "works as before": stop; it is a PR 2b-1 problem to fix (or revert, README "Reverting PR 2b-2 or PR 2b-1") before PR 2b-2.

- [ ] **Step 7 (agent): Write the PR 2b-1 record (it rides along in PR 2b-2)**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it (today `### Printed bulletin PR 2a record`). Insert, right before `## Backups` (one blank line on each side):

```markdown
### Printed bulletin PR 2b-1 record

Printed bulletin PR 2b-1 (the server's half of PR 2b: migration
`0006_services_bulletin`, the API saving, opening, carrying and printing
a service's bulletin fields; the builder unchanged) merged as PR #<N1>,
the first of the two PRs of printed bulletin PR 2b (backend first; PR 2
planning answers of 2026-10-02). Production moved from
`0005_services_extras` to `0006_services_bulletin` (one empty nullable
column on `services`). The steps follow `backend/migrations/README.md` →
"Before 0006_services_bulletin", and the owner's check covered the
"(owner, before the PR 2b-1 merge)" and "(owner, after PR 2b-1)" items of
`docs/manual-verification.md` → "Printed bulletin". No token, email
address, phone number, street address, church id or database URL is
recorded here.

| Step | Result | Date |
|---|---|---|
| 1. Backup | `db-backup` run <run URL>: success, artifact `db-backup` (<bytes> bytes, encrypted) | <date> |
| 2. Counts before (SQL Editor, read-only) | version `0005_services_extras`; <n> saved services; <n> churches | <date> |
| 3. SQL preview | Rendered from the PR's code without a database: the six lines of the README (one `ADD COLUMN bulletin JSON`, under the 5 s lock timeout); read by the owner: <answer> | <date> |
| Merge and deploy | PR #<N1> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`; `/openapi.json` lists `/services/previous-bulletin`; signed out: 401. <Railway log line "Running upgrade 0005_services_extras -> 0006_services_bulletin" seen by the owner. / Not checked.> | <date> |
| 4. After the deploy (read-only) | `0006_services_bulletin`, `1`, with_bulletin `0`; counts again: <unchanged / …> | <date> |
| 5. The builder as before (phone: <phone and browser>) | <A saved service saved again; the printed bulletin still shows the music and announcements as [placeholders]. / …> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: PR 2b-2 (the Bulletin step), then PR 3 (the cover picture, backend first) | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye: the second grep below catches an email address and a "(555)"-style phone, not a street address, a phone number written another way or a name, so check that none is in it. Then (not replayed):

```bash
sed -n '/^### Printed bulletin PR 2b-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Printed bulletin PR 2b-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|\([0-9]{3}\)'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: printed bulletin PR 2b-1 record (backup, counts, SQL preview, merge, migration 0006)" -m "Records printed bulletin PR 2b-1 (PR #<N1>): the backup, the read-only
counts and the SQL preview before the merge, the merge and the deploy of
0006_services_bulletin, the after-deploy check and the owner's check that
the builder works as before. No token, email, phone number, address,
church id or database URL is recorded. Rides along in PR 2b-2." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit; the push (a backup push of the branch, no PR). Then tell the owner: "PR 2b-1 is live and recorded. Next I build PR 2b-2, the Bulletin step itself, and come back to you before opening it." PR 2b-2's tasks start now, on the same branch (now even with `main` plus this record).

Expected counts after this task: backend `1425 passed, 17 skipped` on `main`; frontend `675 passed` in 85 files.

## PR 2b-2: the Bulletin step (T7-T12)

Started only after T6 (PR 2b-1 is merged, live and checked, its record committed on the branch). T7-T10 are PR 2b-2's commits: the draft v3, the step, the card, the docs. T11 verifies and opens the draft PR; T12 merges it on the owner's yes, checks the phone and writes the record (its own records PR).

### Task 7: The draft v3 and the bulletin on the client (F §4.4, §4.6, §4.7; clarifications 2, 7-11)

**Files:**
- Create: `frontend/src/lib/draft/bulletin.test.ts`, `frontend/src/lib/draft/bulletin.ts`
- Modify: `frontend/src/lib/draft/schema.test.ts`, `frontend/src/lib/draft/migrate.test.ts`, `frontend/src/lib/draft/store.test.ts`, `frontend/src/lib/draft/mapping.test.ts`, `frontend/src/lib/draft/status.test.ts`, `frontend/src/lib/documents.test.ts`, `frontend/src/lib/queries/keys.test.ts`, `frontend/src/lib/draft/schema.ts`, `frontend/src/lib/draft/migrate.ts`, `frontend/src/lib/draft/mapping.ts`, `frontend/src/lib/draft/status.ts`, `frontend/src/lib/documents.ts`, `frontend/src/lib/queries/keys.ts`, `frontend/src/lib/queries/services.ts`, `frontend/src/components/builder/step-progress.tsx`

The existing tests that pin the version (2 → 3, a "future" version 3 → 4) change with it. `step-progress.tsx` gains only the two new status texts here (the switch must cover every `StepStatus`); its five columns and the step itself are T8's, so the step bar is unchanged until then ("bulletin" is not in `SHIPPED_STEPS` yet).

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/lib/documents.test.ts`, replace:**

````ts
import { gg2013, savedService, testDraft } from "@/test/fixtures";
````

**with:**

````ts
import { setAnnouncement, setPerson } from "@/lib/draft/bulletin";
import { gg2013, savedService, serviceBulletin, testDraft } from "@/test/fixtures";
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````ts
        ],
````

**with:**

````ts
        ],
        bulletin: serviceBulletin(), // always sent (printed bulletin PR 2b), here with nothing filled in
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````ts

describe("savedCopyFingerprint (5a-3 build review M2)", () => {
````

**with:**

````ts

describe("the bulletin fields in the body (printed bulletin PR 2b)", () => {
  it("are always sent, trimmed and cut to the server's limits", () => {
    let d = setAnnouncement(testDraft(), "prayer_concerns", ` ${"p".repeat(4005)}`);
    d = setPerson(setAnnouncement(d, "ushers", "Sam Sample "), "organist", "o".repeat(105));
    const { bulletin } = documentRequest(d, "bulletin").service;
    expect(bulletin?.announcements.ushers).toBe("Sam Sample");
    expect(bulletin?.announcements.prayer_concerns).toHaveLength(4000);
    expect(bulletin?.people).toEqual({ worship_leader: null, liturgist: null, organist: "o".repeat(100) });
    expect(bulletin?.unchecked).toEqual([]);
    expect(printedRequest(d, "pdf").service.bulletin).toEqual(bulletin);
  });

  it("count in savedCopyFingerprint: another device's announcements are someone else's change", () => {
    const theirs = savedService({ bulletin: serviceBulletin({ announcements: { ...serviceBulletin().announcements, deacon: "Alex Example" } }) });
    const sent = { ...theirs, bulletin: { ...theirs.bulletin, announcements: { ...theirs.bulletin.announcements, deacon: " Alex Example\r\n" } } };
    expect(savedCopyFingerprint(sent)).toBe(savedCopyFingerprint(theirs));
    expect(savedCopyFingerprint({ ...theirs, bulletin: serviceBulletin() })).not.toBe(savedCopyFingerprint(theirs));
  });

  it("read the body as the server stores it, so my own save is never someone else's change (plan review fix M3)", () => {
    const stored = serviceBulletin({
      prelude: { title: "Toccata in F", composer: "Pat Example" },
      announcements: { ...serviceBulletin().announcements, coffee_hour: "The Example family", prayer_concerns: "For Sam\nFor Lee\nFor all" },
      reading_text: { ot: "Verse one.\n\nVerse two.", nt: "" },
      unchecked: ["prelude", "coffee_hour"],
    });
    const sent = serviceBulletin({
      prelude: { title: "Toccata\tin F ", composer: "Pat\u2028Example" },
      announcements: { ...serviceBulletin().announcements, coffee_hour: "The Example\r\nfamily", prayer_concerns: "For Sam\u2028For Lee\x85For all" },
      reading_text: { ot: "Verse one.\r\n\r\n \n\u2029Verse two.", nt: "" },
      unchecked: ["coffee_hour", "prelude"],
    });
    const theirs = savedService({ bulletin: stored });
    expect(savedCopyFingerprint({ ...theirs, bulletin: sent })).toBe(savedCopyFingerprint(theirs));
    const changed = { ...stored, announcements: { ...stored.announcements, prayer_concerns: "For Sam For Lee For all" } };
    expect(savedCopyFingerprint({ ...theirs, bulletin: changed })).not.toBe(savedCopyFingerprint(theirs));
  });
});

describe("savedCopyFingerprint (5a-3 build review M2)", () => {
````

**Create `frontend/src/lib/draft/bulletin.test.ts`:**

````ts
import { describe, expect, it } from "vitest";

import type { PreviousBulletin } from "@/lib/api/types";
import { filledBulletinSettings, savedService, serviceBulletin, testDraft } from "@/test/fixtures";

import {
  applyCarry,
  bulletinFromService,
  bulletinPayload,
  bulletinStatus,
  followSaveMode,
  keepCarried,
  notChecked,
  notCheckedLine,
  printedNotFilledIn,
  setAnnouncement,
  setMusic,
  setPartLeader,
  setPastedText,
  setPerson,
  shouldCarry,
} from "./bulletin";
import { markSaved } from "./mapping";
import { editScriptureLines, setDate, setPick } from "./readings";
import type { DraftV1 } from "./schema";

/** Last week's service (invented): the music and three announcements. */
function lastWeek(overrides: Partial<PreviousBulletin> = {}): PreviousBulletin {
  return {
    service_id: "s-last",
    service_date_iso: "2026-09-27",
    bulletin: serviceBulletin({
      prelude: { title: "Morning Voluntary", composer: "Pat Example" },
      announcements: {
        ...serviceBulletin().announcements,
        ushers: "Sam Sample",
        coffee_hour: "The Example family",
        prayer_concerns: "For all who are ill.",
      },
    }),
    ...overrides,
  };
}

const carried = (d: DraftV1 = testDraft()) => applyCarry(d, lastWeek(), d.readings.date_iso);

describe("carry forward (PR 2 planning answer 5)", () => {
  it("carries last week's music and announcements into a new draft once for its date, each marked to check", () => {
    const d = testDraft();
    expect(shouldCarry(d)).toBe(true);
    const c = carried(d);
    expect(c.bulletin).toMatchObject({
      prelude: { title: "Morning Voluntary", composer: "Pat Example" },
      announcements: { ushers: "Sam Sample", coffee_hour: "The Example family", prayer_concerns: "For all who are ill." },
      carried: ["prelude", "ushers", "coffee_hour", "prayer_concerns"],
      edited: [],
      carried_for: "2026-10-04",
    });
    expect(shouldCarry(c)).toBe(false); // once per date
    expect(applyCarry(c, lastWeek(), "2026-10-04")).toBe(c);
    expect(applyCarry(d, lastWeek(), "2026-10-11")).toBe(d); // the date moved meanwhile
    // Nothing saved before the date: nothing carries, and it is not looked up again for that date.
    const none = applyCarry(d, { service_id: null, service_date_iso: null, bulletin: serviceBulletin() }, "2026-10-04");
    expect(none.bulletin).toMatchObject({ carried: [], carried_for: "2026-10-04" });
  });

  it("carries again for a new date into every box not edited or kept, a box at a time (plan review fix M1)", () => {
    const moved = setDate(carried(), "2026-10-11", "user");
    expect(shouldCarry(moved)).toBe(true);
    const again = applyCarry(moved, lastWeek({ bulletin: serviceBulletin() }), "2026-10-11");
    expect(again.bulletin).toMatchObject({ prelude: { title: "" }, announcements: { ushers: "" }, carried: [] });
    // Typed, cleared or kept: that box stays as it is; the others still carry.
    let d = setAnnouncement(carried(), "coffee_hour", "The Sample family");
    d = keepCarried(setAnnouncement(d, "prayer_concerns", ""), "ushers");
    expect(d.bulletin.edited).toEqual(["ushers", "coffee_hour", "prayer_concerns"]);
    const next = applyCarry(setDate(d, "2026-10-11", "user"), lastWeek({ bulletin: serviceBulletin({ prelude: { title: "Festive Postlude", composer: "" } }) }), "2026-10-11");
    expect(next.bulletin).toMatchObject({
      prelude: { title: "Festive Postlude", composer: "" },
      announcements: { ushers: "Sam Sample", coffee_hour: "The Sample family", prayer_concerns: "" },
      carried: ["prelude"],
    });
    // A box typed before the carry arrives (or after a failed lookup) does not stop the others.
    const early = setAnnouncement(testDraft(), "other", "Typed before any carry.");
    expect(shouldCarry(early)).toBe(true);
    expect(carried(early).bulletin).toMatchObject({
      announcements: { other: "Typed before any carry.", ushers: "Sam Sample" },
      carried: ["prelude", "ushers", "coffee_hour", "prayer_concerns"],
    });
    // Every box touched: nothing is left to carry.
    const all = (["prelude", "postlude"] as const).reduce(
      (x, piece) => setMusic(x, piece, "title", "Typed"),
      (["ushers", "deacon", "coffee_hour", "activities", "prayer_concerns", "collection", "other"] as const).reduce(
        (x, key) => setAnnouncement(x, key, "Typed"),
        testDraft(),
      ),
    );
    expect(shouldCarry(all)).toBe(false);
    // The people, a part's leader and pasted text never stop it: they never carry.
    expect(shouldCarry(setPerson(setPartLeader(testDraft(), "sermon", "Rev. Guest"), "organist", ""))).toBe(true);
  });

  it("never carries into a saved service, a draft without a real date, or while a save's outcome is unknown (plan review fix I2)", () => {
    expect(shouldCarry({ ...testDraft(), editing: { service_id: "s1", saved_at: "x", date_iso: "2026-10-04" } })).toBe(false);
    expect(shouldCarry(setDate(testDraft(), "", "user"))).toBe(false);
    const pending = { ...testDraft(), save_key_fingerprint: "the body of a POST whose answer was lost" };
    expect(shouldCarry(pending)).toBe(false);
    expect(carried(pending)).toBe(pending);
  });
});

describe("Save as new service (plan review fix I4)", () => {
  const saved = serviceBulletin({
    prelude: { title: "Morning Voluntary", composer: "Pat Example" },
    people: { worship_leader: "Rev. Guest", liturgist: null, organist: null },
    leaders: { sermon: "Rev. Guest" },
    announcements: { ...serviceBulletin().announcements, coffee_hour: "The Example family" },
    reading_text: { ot: "", nt: "Pasted text." },
    unchecked: ["coffee_hour"],
  });
  const opened = (): DraftV1 => ({
    ...testDraft(),
    editing: { service_id: "s-last", saved_at: "2026-09-27T12:00:00+00:00", date_iso: "2026-10-04" },
    bulletin: bulletinFromService(saved, savedService()),
  });

  it("on another date marks the music and announcements to check and starts this week's people, leaders and texts empty", () => {
    const d = opened();
    expect(followSaveMode(d)).toBe(d); // the saved date: nothing changes
    const copy = followSaveMode(setDate(d, "2026-10-11", "user"));
    expect(copy.bulletin).toMatchObject({
      prelude: saved.prelude,
      announcements: { coffee_hour: "The Example family" },
      people: { worship_leader: null, liturgist: null, organist: null },
      leaders: {},
      pasted: {},
      carried: ["prelude", "coffee_hour"],
      set_aside: { people: saved.people, leaders: saved.leaders, pasted: { "Matthew 21:33-46": "Pasted text." }, carried: ["coffee_hour"] },
    });
    expect(followSaveMode(copy)).toBe(copy);
    expect(bulletinPayload(copy).unchecked).toEqual(["prelude", "coffee_hour"]);
    // Saved as the new service: what was set aside belongs to the other one.
    const savedCopy = markSaved(copy, savedService({ service_date_iso: "2026-10-11" }), "fp");
    expect(savedCopy.bulletin.set_aside).toBeNull();
    expect(followSaveMode(savedCopy)).toBe(savedCopy);
  });

  it("puts back what it set aside on the saved date, keeping anything typed meanwhile, and waits for an unknown save", () => {
    let copy = followSaveMode(setDate(opened(), "2026-10-11", "user"));
    copy = setAnnouncement(setPerson(copy, "organist", "Jordan Doe"), "coffee_hour", "The Sample family");
    const back = followSaveMode(setDate(copy, "2026-10-04", "user"));
    expect(back.bulletin).toMatchObject({
      people: { worship_leader: "Rev. Guest", liturgist: null, organist: "Jordan Doe" },
      leaders: { sermon: "Rev. Guest" },
      pasted: { "Matthew 21:33-46": "Pasted text." },
      announcements: { coffee_hour: "The Sample family" },
      carried: [], // the coffee hour was edited meanwhile
      set_aside: null,
    });
    const pending = { ...setDate(opened(), "2026-10-11", "user"), save_key_fingerprint: "fp" };
    expect(followSaveMode(pending)).toBe(pending);
  });
});

describe("editing the Bulletin step", () => {
  it("an edit or Keep as is clears a box's From last week; the other boxes keep theirs", () => {
    let d = carried();
    d = setMusic(d, "prelude", "composer", "Pat Example, arr.");
    d = keepCarried(d, "ushers");
    expect(d.bulletin.carried).toEqual(["coffee_hour", "prayer_concerns"]);
    expect(d.bulletin.announcements.ushers).toBe("Sam Sample");
    expect(notChecked(d)).toEqual(["coffee hour", "prayers and concerns"]);
    expect(notCheckedLine(notChecked(d))).toBe("From last week, not checked yet: coffee hour, prayers and concerns.");
    expect(bulletinStatus(d)).toEqual({ kind: "to_check", count: 2 });
    expect(bulletinStatus(testDraft())).toEqual({ kind: "optional" });
    expect(setAnnouncement(d, "deacon", "")).toBe(d); // no change, same draft
  });

  it("sends the fields trimmed, the people as set, the part leaders with a name and the pasted text of the readings printed", () => {
    let d = editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46");
    d = setMusic(d, "postlude", "title", "  Festive Postlude ");
    d = setPerson(setPerson(d, "worship_leader", " Rev. Guest "), "liturgist", "");
    d = setPartLeader(setPartLeader(setPartLeader(d, "sermon", "Pat Example "), "offering", "x"), "offering", "");
    d = setPastedText(d, "Philippians 3:4b-14", " Pasted for the NT. ");
    d = setPastedText(d, "Psalm 23", "For a reading no longer chosen.");
    d = setAnnouncement(d, "activities", " Tuesday: Bible study.\nWednesday: Choir. ");
    const p = bulletinPayload(d);
    expect(p.postlude).toEqual({ title: "Festive Postlude", composer: "" });
    expect(p.people).toEqual({ worship_leader: "Rev. Guest", liturgist: "", organist: null });
    expect(p.leaders).toEqual({ sermon: "Pat Example" });
    expect(p.announcements.activities).toBe("Tuesday: Bible study.\nWednesday: Choir.");
    expect(p.reading_text).toEqual({ ot: "", nt: "Pasted for the NT." });
    expect(p.unchecked).toEqual([]);
    expect(bulletinPayload(carried()).unchecked).toEqual(["prelude", "ushers", "coffee_hour", "prayer_concerns"]);
    // Another NT pick: its own box, empty; the text pasted for Philippians stays in the draft.
    const other = setPick(d, "nt", "Matthew 21:33-46");
    expect(bulletinPayload(other).reading_text.nt).toBe("");
    expect(bulletinPayload(setPick(other, "nt", "Philippians 3:4b-14")).reading_text.nt).toBe("Pasted for the NT.");
  });

  it("opens a saved service's bulletin as it was saved, its pasted text under the reading's reference, its unchecked boxes marked again", () => {
    const saved = serviceBulletin({
      people: { worship_leader: null, liturgist: "Sam Sample", organist: null },
      leaders: { sermon: "Rev. Guest" },
      reading_text: { ot: "", nt: "Pasted text." },
      unchecked: ["coffee_hour", "prelude"],
    });
    const b = bulletinFromService(saved, savedService());
    expect(b).toMatchObject({ people: saved.people, leaders: saved.leaders, carried: ["prelude", "coffee_hour"], edited: [], carried_for: null });
    expect(bulletinFromService(serviceBulletin(), savedService()).carried).toEqual([]);
    expect(b.pasted).toEqual({ "Matthew 21:33-46": "Pasted text." }); // savedService picks the Gospel
  });
});

describe("printedNotFilledIn (PR 2 planning answer 3)", () => {
  it("lists the blank standing fields, this week's people as changed, then the prelude, postlude and announcements", () => {
    const settings = filledBulletinSettings({ phone: "", organist: "" });
    expect(printedNotFilledIn(settings, testDraft())).toEqual(["phone", "organist", "prelude", "postlude", "announcements"]);
    let d = setPerson(setPerson(testDraft(), "organist", "Jordan Doe"), "liturgist", "");
    d = setMusic(setAnnouncement(d, "deacon", "Alex Example"), "prelude", "title", "Morning Voluntary");
    expect(printedNotFilledIn(settings, d)).toEqual(["phone", "liturgist", "postlude"]);
    expect(printedNotFilledIn(undefined, d)).toEqual(["postlude"]); // settings still loading
  });
});
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````ts
import { churchProfile, hymnId, lectionary, savedService, SERVICE_ID, testDraft, USER_ID } from "@/test/fixtures";

````

**with:**

````ts
import { churchProfile, hymnId, lectionary, savedService, SERVICE_ID, serviceBulletin, testDraft, USER_ID } from "@/test/fixtures";

import { keepCarried, setAnnouncement, setPastedText } from "./bulletin";
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````ts
    expect(d).toMatchObject({
      version: 2,
````

**with:**

````ts
    expect(d).toMatchObject({
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````ts
      save_key_fingerprint: null,
````

**with:**

````ts
      save_key_fingerprint: null,
      version: 3,
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````ts

  it("markSaved records the save and keeps a default Benediction and communion as saved (owner answer 4)", () => {
````

**with:**

````ts

  it("opens a saved service's bulletin fields Saved, and an edit to them is an unsaved change (PR 2b)", () => {
    const bulletin = serviceBulletin({
      prelude: { title: "Morning Voluntary", composer: "Pat Example" },
      people: { worship_leader: "Rev. Guest", liturgist: null, organist: "" },
      leaders: { sermon: "Rev. Guest" },
      reading_text: { ot: "", nt: "Pasted text." },
      unchecked: ["prelude"],
    });
    const d = opened(savedService({ bulletin }));
    expect(draftToServicePayload(d).bulletin).toEqual(bulletin);
    expect(reviewStatus(d)).toBe("saved");
    expect(d.bulletin.carried).toEqual(["prelude"]); // still to check, on any device (plan review fix I3)
    expect(reviewStatus(keepCarried(d, "prelude"))).toBe("unsaved_changes");
    expect(reviewStatus(setAnnouncement(d, "coffee_hour", "The Example family"))).toBe("unsaved_changes");
    expect(reviewStatus(setPastedText(d, "Matthew 21:33-46", ""))).toBe("unsaved_changes");
    // Nothing filled in: no bulletin in the payload, so a draft saved before PR 2b keeps its fingerprint.
    expect("bulletin" in draftToServicePayload(opened())).toBe(false);
  });

  it("markSaved records the save and keeps a default Benediction and communion as saved (owner answer 4)", () => {
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
import { DraftRestoreError, migrate, migrations, parseStoredDraft, type Migration } from "./migrate";
````

**with:**

````ts
import { DraftRestoreError, migrate, migrations, parseStoredDraft, type Migration } from "./migrate";
import { fingerprint } from "./fingerprint";
import { draftToServicePayload } from "./mapping";
import { freshBulletin } from "./schema";
import { reviewStatus } from "./status";
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
    expect(Object.keys(migrations)).toEqual(["1"]);
````

**with:**

````ts
    expect(Object.keys(migrations)).toEqual(["1", "2"]);
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
    expect(parseStoredDraft(JSON.stringify(v1), OWNER)).toEqual({ ...testDraft(), save_key: v1.save_key, version: 2 });
    expect(parseStoredDraft(JSON.stringify({ ...v1, editing }), OWNER)).toMatchObject({
      version: 2,
````

**with:**

````ts
    expect(parseStoredDraft(JSON.stringify(v1), OWNER)).toEqual({ ...testDraft(), save_key: v1.save_key });
    expect(parseStoredDraft(JSON.stringify({ ...v1, editing }), OWNER)).toMatchObject({
      version: 3,
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
    expect(parseStoredDraft(JSON.stringify(undated), OWNER).editing).toEqual({ ...editing, date_iso: null });
````

**with:**

````ts
    expect(parseStoredDraft(JSON.stringify(undated), OWNER).editing).toEqual({ ...editing, date_iso: null });
  });

  it("migrates a version 2 draft: an empty bulletin, nothing else changed, and a saved draft stays Saved (PR 2b)", () => {
    const { bulletin, ...v2 } = { ...testDraft(), version: 2 };
    expect(bulletin).toEqual(freshBulletin());
    // 5a-3's fingerprint: the payload had no bulletin, as today's has none while nothing is filled in.
    const payload = draftToServicePayload(testDraft());
    expect("bulletin" in payload).toBe(false);
    const editing = { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-10-04" };
    const saved = { ...v2, editing, saved_fingerprint: fingerprint(payload), last_step: "review" };
    const migrated = parseStoredDraft(JSON.stringify(saved), OWNER);
    expect(migrated).toEqual({ ...testDraft(), ...saved, version: 3, bulletin: freshBulletin() });
    expect(reviewStatus(migrated)).toBe("saved");
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
      ["a future version", JSON.stringify({ ...d, version: 3 })],
````

**with:**

````ts
      ["a future version", JSON.stringify({ ...d, version: 4 })],
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
import { churchZone, corruptDraftKey, draftKey, draftV1Schema, DRAFT_VERSION, freshDraft, SECTION_KEYS } from "./schema";
````

**with:**

````ts
import { churchZone, corruptDraftKey, draftKey, draftV1Schema, DRAFT_VERSION, freshBulletin, freshDraft, SECTION_KEYS } from "./schema";
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
    expect(DRAFT_VERSION).toBe(2);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 2,
````

**with:**

````ts
    expect(DRAFT_VERSION).toBe(3);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 3,
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
      liturgy: { sermon_title: "", include_communion: true, communion_origin: "default", custom_elements: [] },
    });
````

**with:**

````ts
      liturgy: { sermon_title: "", include_communion: true, communion_origin: "default", custom_elements: [] },
      bulletin: {
        prelude: { title: "", composer: "" },
        postlude: { title: "", composer: "" },
        people: { worship_leader: null, liturgist: null, organist: null },
        leaders: {},
        announcements: { ushers: "", deacon: "", coffee_hour: "", activities: "", prayer_concerns: "", collection: "", other: "" },
        pasted: {},
        carried: [],
        edited: [],
        carried_for: null,
        set_aside: null,
      },
    });
    expect(d.bulletin).toEqual(freshBulletin());
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
      { ...d, version: 3 },
````

**with:**

````ts
      { ...d, version: 4 },
      { ...d, bulletin: undefined }, // version 3 needs the bulletin (PR 2b)
      { ...d, bulletin: { ...d.bulletin, carried: ["sermon"] } },
      { ...d, bulletin: { ...d.bulletin, carried_for: "2026-02-30" } },
      { ...d, bulletin: { ...d.bulletin, edited: ["hymns"] } },
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
import { lectionary, testDraft } from "@/test/fixtures";
````

**with:**

````ts
import { lectionary, serviceBulletin, testDraft } from "@/test/fixtures";
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
import { SHIPPED_STEPS, STEPS, stepById, stepFromPath } from "./steps";
````

**with:**

````ts
import { SHIPPED_STEPS, STEPS, stepById, stepFromPath } from "./steps";
import { applyCarry, keepCarried, setAnnouncement, setPartLeader, setPastedText, setPerson } from "./bulletin";
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
const HYMN: HymnPick = { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" };
````

**with:**

````ts
const HYMN: HymnPick = { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" };

/** A new draft with last week's coffee hour carried in (printed bulletin PR 2b). */
function carriedDraft(): DraftV1 {
  const announcements = { ...serviceBulletin().announcements, coffee_hour: "The Example family" };
  const previous = { service_id: "s0", service_date_iso: "2026-09-27", bulletin: serviceBulletin({ announcements }) };
  return applyCarry(testDraft(), previous, "2026-10-04");
}
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
    ];
    for (const [name, d] of cases) expect(isPristine(d), name).toBe(false);
````

**with:**

````ts
      // Printed bulletin PR 2b: anything typed on the Bulletin step.
      ["an announcement", setAnnouncement(testDraft(), "coffee_hour", "The Example family")],
      ["last week's kept", keepCarried(carriedDraft(), "coffee_hour")],
      ["a person this week", setPerson(testDraft(), "organist", "")],
      ["a part's leader", setPartLeader(testDraft(), "sermon", "Rev. Guest")],
      ["pasted text", setPastedText(testDraft(), "Psalm 23", "The Lord is my shepherd.")],
    ];
    for (const [name, d] of cases) expect(isPristine(d), name).toBe(false);
    // Last week's text carried in and not touched comes back on its own: nothing to lose.
    expect(isPristine(carriedDraft())).toBe(true);
  });
});

describe("the Bulletin step's status (printed bulletin PR 2b)", () => {
  it("is Soon until it ships, then Optional, or how many boxes from last week are still to check", () => {
    expect(stepStatus(testDraft(), "bulletin", ALL)).toEqual({ kind: "soon" });
    const shipped = new Set<StepId>([...ALL, "bulletin"]);
    expect(stepStatus(testDraft(), "bulletin", shipped)).toEqual({ kind: "optional" });
    expect(stepStatus(carriedDraft(), "bulletin", shipped)).toEqual({ kind: "to_check", count: 1 });
    expect(stillNeeded(carriedDraft(), shipped)).toEqual(stillNeeded(testDraft(), shipped)); // never "Still to do"
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 3 }), JSON.stringify({ version: 1 })]) {
````

**with:**

````ts
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 4 }), JSON.stringify({ version: 1 })]) {
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    const raw = JSON.stringify({ ...testDraft(), version: 3 });
````

**with:**

````ts
    const raw = JSON.stringify({ ...testDraft(), version: 4 });
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    store.flush();
    expect(stored(data)).toMatchObject({ version: 2, readings: { occasion: "Mine" } });
````

**with:**

````ts
    store.flush();
    expect(stored(data)).toMatchObject({ version: 3, readings: { occasion: "Mine" } });
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    expect(stored(data)).toMatchObject({ version: 2, readings: { occasion: "Mine" } });
````

**with:**

````ts
    expect(stored(data)).toMatchObject({ version: 3, readings: { occasion: "Mine" } });
````

**In `frontend/src/lib/queries/keys.test.ts`, replace:**

````ts
      keys.bulletinSettings(id),
````

**with:**

````ts
      keys.bulletinSettings(id),
      keys.previousBulletin(id, "2026-10-11"),
````

**In `frontend/src/lib/queries/keys.test.ts`, replace:**

````ts
      ["bulletin-settings"],
````

**with:**

````ts
      ["bulletin-settings"],
      ["services", "previous-bulletin", "2026-10-11"], // under the services prefix: a save refreshes it (PR 2b)
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/draft/bulletin.test.ts src/lib/draft/schema.test.ts src/lib/draft/migrate.test.ts src/lib/draft/store.test.ts src/lib/draft/mapping.test.ts src/lib/draft/status.test.ts src/lib/documents.test.ts src/lib/queries/keys.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`bulletin.ts` does not exist yet, so four files cannot load):
```
   × draft schema and freshDraft (F §4.6) > a fresh draft is dated next Sunday with every field empty and the F §4.6 defaults <t>ms
   × draft schema and freshDraft (F §4.6) > accepts an empty date and generous strings, and rejects impossible values <t>ms
   × DraftStore changes (S store.ts) > never adopts a draft an older version of the app wrote, however new, and writes over it (slice 5a-3: an old tab) <t>ms
   × DraftStore changes (S store.ts) > puts its draft back over an old tab's with nothing to write, and a store loaded from the old tab's takes it (build review M3) <t>ms
   × draft migrate and parseStoredDraft (F §4.6 Versioning) > round-trips a stored draft <t>ms
   × draft migrate and parseStoredDraft (F §4.6 Versioning) > migrates a version 1 draft: editing gains the draft's date, and save_key_fingerprint starts null (slice 5a-3) <t>ms
   × draft migrate and parseStoredDraft (F §4.6 Versioning) > migrates a version 2 draft: an empty bulletin, nothing else changed, and a saved draft stays Saved (PR 2b) <t>ms
   × keys > starts every church-scoped key with ['church', id] <t>ms
 FAIL  |unit| src/lib/documents.test.ts [ src/lib/documents.test.ts ]
 FAIL  |unit| src/lib/draft/bulletin.test.ts [ src/lib/draft/bulletin.test.ts ]
 FAIL  |unit| src/lib/draft/mapping.test.ts [ src/lib/draft/mapping.test.ts ]
 FAIL  |unit| src/lib/draft/status.test.ts [ src/lib/draft/status.test.ts ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 8 ⎯⎯⎯⎯⎯⎯⎯
      Tests  8 failed | 23 passed (31)
```

- [ ] **Step 3: The draft v3, the bulletin library, the mapping, the bodies, the statuses, the key and the query**

**In `frontend/src/components/builder/step-progress.tsx`, replace:**

````tsx
      return "Soon";
````

**with:**

````tsx
      return "Soon";
    case "optional":
      return "Optional";
    case "to_check":
      return `${status.count} to check`;
````

**In `frontend/src/components/builder/step-progress.tsx`, replace:**

````tsx
          const muted = status.kind === "soon" || status.kind === "not_in_archive";
````

**with:**

````tsx
          const muted = status.kind === "soon" || status.kind === "not_in_archive" || status.kind === "optional";
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
 * `normalizePlacement` does on the Liturgy step.
 */
import type { components } from "@/lib/api/schema";
import { fingerprint } from "@/lib/draft/fingerprint";
import { draftToServicePayload } from "@/lib/draft/mapping";
import { SLOTS, type DraftV1, type Slot } from "@/lib/draft/schema";
````

**with:**

````ts
 * `normalizePlacement` does on the Liturgy step, and the Bulletin step's
 * fields (printed bulletin PR 2b) always, each text cut to its limit.
 */
import type { components } from "@/lib/api/schema";
import type { ServiceBulletin } from "@/lib/api/types";
import { emptyServiceBulletin, MAX_LENGTH as BULLETIN_MAX } from "@/lib/draft/bulletin";
import { fingerprint } from "@/lib/draft/fingerprint";
import { draftToServicePayload } from "@/lib/draft/mapping";
import { CARRY_KEYS, SLOTS, type DraftV1, type Slot } from "@/lib/draft/schema";
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts

/** Blank as the server reads a label: nothing left after `wordSafe` and trimming. */
````

**with:**

````ts

/** The bulletin fields within the server's limits (`service_bulletin.MAX_LENGTH`). */
function clipBulletin(b: ServiceBulletin): ServiceBulletin {
  const person = (name: string | null) => (name === null ? null : clipChars(name, BULLETIN_MAX.person));
  return {
    prelude: { title: clipChars(b.prelude.title, BULLETIN_MAX.title), composer: clipChars(b.prelude.composer, BULLETIN_MAX.composer) },
    postlude: { title: clipChars(b.postlude.title, BULLETIN_MAX.title), composer: clipChars(b.postlude.composer, BULLETIN_MAX.composer) },
    people: { worship_leader: person(b.people.worship_leader), liturgist: person(b.people.liturgist), organist: person(b.people.organist) },
    leaders: Object.fromEntries(Object.entries(b.leaders).map(([key, name]) => [key, clipChars(name, BULLETIN_MAX.person)])),
    announcements: {
      ushers: clipChars(b.announcements.ushers, BULLETIN_MAX.ushers),
      deacon: clipChars(b.announcements.deacon, BULLETIN_MAX.deacon),
      coffee_hour: clipChars(b.announcements.coffee_hour, BULLETIN_MAX.coffee_hour),
      activities: clipChars(b.announcements.activities, BULLETIN_MAX.activities),
      prayer_concerns: clipChars(b.announcements.prayer_concerns, BULLETIN_MAX.prayer_concerns),
      collection: clipChars(b.announcements.collection, BULLETIN_MAX.collection),
      other: clipChars(b.announcements.other, BULLETIN_MAX.other),
    },
    reading_text: { ot: clipChars(b.reading_text.ot, BULLETIN_MAX.reading_text), nt: clipChars(b.reading_text.nt, BULLETIN_MAX.reading_text) },
    unchecked: [...b.unchecked],
  };
}

/** `service_bulletin.read`'s one-line fields: each run of control characters (and the spaces around it) is one space. */
const NOT_ONE_LINE_RUN = / *[\x00-\x1f\x7f-\x9f\u2028\u2029][\x00-\x1f\x7f-\x9f\u2028\u2029 ]*/g;
/** `service_bulletin.read`'s free texts: every line break is "\n" (U+2028 and U+2029 would print as "?"). */
const LINE_BREAK = /\r\n?|[\v\f\x85\u2028\u2029]/g;
/** `service_bulletin.read`'s pasted readings: a run of blank lines is one paragraph break. */
const BLANK_LINES = /\n(?:[ \t]*\n)+/g;

const oneLine = (text: string) => text.replace(NOT_ONE_LINE_RUN, " ");
const lines = (text: string) => text.replace(LINE_BREAK, "\n");
const paragraphs = (text: string) => lines(text).replace(BLANK_LINES, "\n\n");

/** Blank as the server reads a label: nothing left after `wordSafe` and trimming. */
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
 * today's limits included).
````

**with:**

````ts
 * today's limits included). The bulletin is always sent (printed bulletin
 * PR 2b), so a save that clears every bulletin field clears the saved ones;
 * only a client from before 2b sends none (and a PUT then keeps them).
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
      })),
````

**with:**

````ts
      })),
    bulletin: clipBulletin(payload.bulletin ?? emptyServiceBulletin()),
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
  custom_elements?: { label: string; text: string; insert_after: string }[];
````

**with:**

````ts
  custom_elements?: { label: string; text: string; insert_after: string }[];
  /** Printed bulletin PR 2b; missing reads as nothing filled in. */
  bulletin?: ServiceBulletin | null;
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
 * limit never looks like someone else's change (5a-3 build review M2).
````

**with:**

````ts
 * limit never looks like someone else's change (5a-3 build review M2). The
 * bulletin fields count too (printed bulletin PR 2b): another device's
 * change to the announcements is someone else's change.
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
  });
````

**with:**

````ts
    bulletin: savedBulletin(s.bulletin ?? emptyServiceBulletin(), clean),
  });
}

/**
 * A bulletin as the archive keeps it (`service_bulletin.read`, then Word-safe
 * and trimmed): a one-line field's control characters one space, a free
 * text's line breaks "\n", a pasted reading's blank lines one paragraph
 * break, blank part leaders left out, the unchecked boxes in order (plan
 * review fix M3: a tab pasted into a title is not someone else's change).
 */
function savedBulletin(b: ServiceBulletin, clean: (text: string) => string) {
  const line = (text: string) => clean(oneLine(text));
  const music = (m: ServiceBulletin["prelude"]) => ({ title: line(m.title), composer: line(m.composer) });
  const free = new Set<string>(["activities", "prayer_concerns", "collection", "other"]);
  return {
    prelude: music(b.prelude),
    postlude: music(b.postlude),
    people: Object.fromEntries(Object.entries(b.people).map(([role, name]) => [role, name === null ? null : line(name)])),
    leaders: Object.fromEntries(Object.entries(b.leaders).map(([key, name]) => [key, line(name)]).filter(([, name]) => name !== "")),
    announcements: Object.fromEntries(
      Object.entries(b.announcements).map(([key, text]) => [key, free.has(key) ? clean(lines(text)) : line(text)]),
    ),
    reading_text: { ot: clean(paragraphs(b.reading_text.ot)), nt: clean(paragraphs(b.reading_text.nt)) },
    unchecked: CARRY_KEYS.filter((key) => (b.unchecked ?? []).includes(key)),
  };
````

**Create `frontend/src/lib/draft/bulletin.ts`:**

````ts
/**
 * The Bulletin step's weekly fields in the draft (printed bulletin PR 2b;
 * spec "Data model", "The Bulletin step"): the prelude and postlude, this
 * week's people and part leaders, the announcements and the pasted reading
 * text. Pure.
 *
 * - Edits (`setMusic`, `setAnnouncement`, `setPerson`, `setPartLeader`,
 *   `setPastedText`, `keepCarried`). A box holding last week's text shows
 *   "From last week. Check before printing." until it is edited (its text
 *   changed in any way, cleared included) or kept as it is ("Keep as is").
 * - Carry forward (PR 2 planning answer 5): `shouldCarry` and `applyCarry`.
 *   A draft that is not a saved service (`editing` null), with a real date
 *   and no save whose outcome is still unknown (`save_key_fingerprint` null:
 *   a carry would change the body and so the save key, plan review fix I2),
 *   takes the music and the announcements of the church's latest service
 *   dated before its date (`GET /services/previous-bulletin`) into every box
 *   not yet typed in, edited, cleared or kept (`edited`, a box at a time),
 *   once per date (`carried_for`); a new date carries again into those
 *   boxes. The people, the part leaders and the pasted texts never carry.
 *   Opening a saved service never carries.
 * - "Save as new service" (`followSaveMode`, plan review fix I4): a saved
 *   service whose date now differs from the saved one is treated as a new
 *   week: every filled music and announcement box is marked "From last
 *   week", and this week's people, the part leaders and the pasted texts
 *   start empty (set aside, and put back if the date goes back to the
 *   saved one).
 * - `bulletinPayload`: the draft's bulletin as `ServiceDraft.bulletin`, the
 *   texts trimmed, the pasted texts of the readings the files print, and
 *   the boxes still to check (`unchecked`, so the marks are saved with the
 *   service, plan review fix I3).
 * - `bulletinFromService`: a saved service's bulletin as the draft's, its
 *   unchecked boxes marked again.
 * - What the Printed bulletin card and the step bar say: `printedNotFilledIn`,
 *   `notChecked`, `bulletinStatus`.
 */
import type { BulletinSettings, PreviousBulletin, ServiceBulletin } from "@/lib/api/types";
import { ELEMENTS, notFilledIn } from "@/lib/bulletin-settings";
import { inSupportedRange, isValidDateIso } from "@/lib/dates";
import { resolveReadings } from "@/lib/scripture-refs";

import { effectivePicks } from "./readings";
import {
  ANNOUNCEMENT_KEYS,
  CARRY_KEYS,
  PEOPLE,
  type AnnouncementKey,
  type CarryKey,
  type DraftBulletin,
  type DraftV1,
  type Person,
} from "./schema";

/** `service_bulletin.MAX_LENGTH`: the server refuses a longer text (422); `serviceBody` cuts to them. */
export const MAX_LENGTH = {
  title: 200,
  composer: 100,
  person: 100,
  ushers: 200,
  deacon: 100,
  coffee_hour: 200,
  activities: 4000,
  prayer_concerns: 4000,
  collection: 2000,
  other: 4000,
  reading_text: 10_000,
} as const;

export type Piece = "prelude" | "postlude";

function withBulletin(d: DraftV1, next: DraftBulletin): DraftV1 {
  return { ...d, bulletin: next };
}

/** The box `key` edited or kept: no longer to check, and last week's never carries into it again. */
function touched(b: DraftBulletin, key: CarryKey): Pick<DraftBulletin, "carried" | "edited"> {
  return {
    carried: b.carried.filter((k) => k !== key),
    edited: b.edited.includes(key) ? b.edited : CARRY_KEYS.filter((k) => k === key || b.edited.includes(k)),
  };
}

export function setMusic(d: DraftV1, piece: Piece, field: "title" | "composer", value: string): DraftV1 {
  const b = d.bulletin;
  if (b[piece][field] === value) return d;
  return withBulletin(d, { ...b, [piece]: { ...b[piece], [field]: value }, ...touched(b, piece) });
}

export function setAnnouncement(d: DraftV1, key: AnnouncementKey, value: string): DraftV1 {
  const b = d.bulletin;
  if (b.announcements[key] === value) return d;
  return withBulletin(d, { ...b, announcements: { ...b.announcements, [key]: value }, ...touched(b, key) });
}

/** "Keep as is": last week's text stays, and the box no longer asks to be checked. */
export function keepCarried(d: DraftV1, key: CarryKey): DraftV1 {
  const b = d.bulletin;
  return b.carried.includes(key) ? withBulletin(d, { ...b, ...touched(b, key) }) : d;
}

/** This week's name for a person: null follows the bulletin settings, "" is no one this week. */
export function setPerson(d: DraftV1, person: Person, value: string | null): DraftV1 {
  const b = d.bulletin;
  if (b.people[person] === value) return d;
  return withBulletin(d, { ...b, people: { ...b.people, [person]: value } });
}

/** A part's leader this week; a blank one follows the part's standing leader. */
export function setPartLeader(d: DraftV1, key: string, value: string): DraftV1 {
  const b = d.bulletin;
  if ((b.leaders[key] ?? "") === value) return d;
  const leaders = { ...b.leaders };
  if (value === "") delete leaders[key];
  else leaders[key] = value;
  return withBulletin(d, { ...b, leaders });
}

/** The pasted text of the reading `reference` (kept by reference: a changed reading starts with an empty box). */
export function setPastedText(d: DraftV1, reference: string, value: string): DraftV1 {
  const b = d.bulletin;
  if ((b.pasted[reference] ?? "") === value) return d;
  const pasted = { ...b.pasted };
  if (value === "") delete pasted[reference];
  else pasted[reference] = value;
  return withBulletin(d, { ...b, pasted });
}

function filled(b: Pick<DraftBulletin, Piece | "announcements">, key: CarryKey): boolean {
  if (key === "prelude" || key === "postlude") return b[key].title.trim() !== "" || b[key].composer.trim() !== "";
  return b.announcements[key].trim() !== "";
}

/** Last week's bulletin should be looked up and carried in now (see the module comment). */
export function shouldCarry(d: DraftV1): boolean {
  const date = d.readings.date_iso;
  return (
    d.editing === null &&
    d.save_key_fingerprint === null &&
    isValidDateIso(date) &&
    inSupportedRange(date) &&
    d.bulletin.carried_for !== date &&
    d.bulletin.edited.length < CARRY_KEYS.length
  );
}

/**
 * Last week's music and announcements in every box not yet edited or kept,
 * each filled one marked "From last week", for `forDate`; the draft
 * unchanged when carrying is no longer due or the date moved meanwhile.
 */
export function applyCarry(d: DraftV1, previous: PreviousBulletin, forDate: string): DraftV1 {
  if (d.readings.date_iso !== forDate || !shouldCarry(d)) return d;
  const b = d.bulletin;
  const p = previous.bulletin;
  const open = (key: CarryKey) => !b.edited.includes(key);
  const next: DraftBulletin = {
    ...b,
    prelude: open("prelude") ? { ...p.prelude } : b.prelude,
    postlude: open("postlude") ? { ...p.postlude } : b.postlude,
    announcements: Object.fromEntries(
      ANNOUNCEMENT_KEYS.map((key) => [key, open(key) ? p.announcements[key] : b.announcements[key]]),
    ) as DraftBulletin["announcements"],
    carried_for: forDate,
  };
  return withBulletin(d, { ...next, carried: CARRY_KEYS.filter((key) => open(key) && filled(next, key)) });
}

const NO_ONE_CHANGED: DraftBulletin["people"] = { worship_leader: null, liturgist: null, organist: null };

/**
 * "Save as new service" (plan review fix I4): a saved service whose date
 * now differs from its saved date is a new week. Its people, part leaders,
 * pasted texts and marks are set aside, this week's start empty, and every
 * filled music and announcement box is marked "From last week. Check before
 * printing.". Back on the saved date, what was set aside returns: a name or
 * text typed meanwhile wins, and a saved mark returns only on a box not
 * edited or kept meanwhile. Nothing happens while a save's outcome is
 * unknown (`save_key_fingerprint`); the draft unchanged when nothing is due.
 */
export function followSaveMode(d: DraftV1): DraftV1 {
  const editing = d.editing;
  const date = d.readings.date_iso;
  const b = d.bulletin;
  if (editing === null || d.save_key_fingerprint !== null) return d;
  if (date !== editing.date_iso && isValidDateIso(date) && b.set_aside === null) {
    return withBulletin(d, {
      ...b,
      people: NO_ONE_CHANGED,
      leaders: {},
      pasted: {},
      carried: CARRY_KEYS.filter((key) => filled(b, key)),
      edited: [],
      set_aside: { people: b.people, leaders: b.leaders, pasted: b.pasted, carried: b.carried, edited: b.edited },
    });
  }
  if (date === editing.date_iso && b.set_aside !== null) {
    const aside = b.set_aside;
    return withBulletin(d, {
      ...b,
      people: Object.fromEntries(PEOPLE.map((p) => [p, b.people[p] ?? aside.people[p]])) as DraftBulletin["people"],
      leaders: { ...aside.leaders, ...b.leaders },
      pasted: { ...aside.pasted, ...b.pasted },
      carried: aside.carried.filter((key) => b.carried.includes(key)),
      edited: CARRY_KEYS.filter((key) => aside.edited.includes(key) || b.edited.includes(key)),
      set_aside: null,
    });
  }
  return d;
}

/** `ServiceDraft.bulletin` with nothing filled in. */
export function emptyServiceBulletin(): ServiceBulletin {
  return {
    prelude: { title: "", composer: "" },
    postlude: { title: "", composer: "" },
    people: { worship_leader: null, liturgist: null, organist: null },
    leaders: {},
    announcements: { ushers: "", deacon: "", coffee_hour: "", activities: "", prayer_concerns: "", collection: "", other: "" },
    reading_text: { ot: "", nt: "" },
    unchecked: [],
  };
}

/**
 * The draft's bulletin as `ServiceDraft.bulletin`: every text trimmed; the
 * people as set (null: the settings' name); the part leaders with a name, in
 * the printed order; the pasted texts of the two readings the files print
 * (`effectivePicks`), so a text pasted for a reading no longer chosen is not
 * sent; the boxes still to check, in the step's order.
 */
export function bulletinPayload(d: DraftV1): ServiceBulletin {
  const b = d.bulletin;
  const picks = effectivePicks(d);
  const pasted = (ref: string | null) => (ref === null ? "" : (b.pasted[ref] ?? "").trim());
  return {
    prelude: { title: b.prelude.title.trim(), composer: b.prelude.composer.trim() },
    postlude: { title: b.postlude.title.trim(), composer: b.postlude.composer.trim() },
    people: Object.fromEntries(PEOPLE.map((p) => [p, b.people[p]?.trim() ?? null])) as ServiceBulletin["people"],
    leaders: Object.fromEntries(
      ELEMENTS.map(({ key }) => [key, (b.leaders[key] ?? "").trim()]).filter(([, name]) => name !== ""),
    ),
    announcements: Object.fromEntries(
      ANNOUNCEMENT_KEYS.map((key) => [key, b.announcements[key].trim()]),
    ) as ServiceBulletin["announcements"],
    reading_text: { ot: pasted(picks.ot), nt: pasted(picks.nt) },
    unchecked: CARRY_KEYS.filter((key) => b.carried.includes(key)),
  };
}

/** Nothing filled in: what a service saved without a bulletin reads as. */
export function isBlankBulletin(p: ServiceBulletin): boolean {
  return JSON.stringify(p) === JSON.stringify(emptyServiceBulletin());
}

/**
 * A saved service's bulletin as the draft's (`serviceToDraft`): the boxes
 * saved as not checked yet marked "From last week" again (plan review fix
 * I3), no carry (a saved service never carries); each pasted text kept
 * under the reference of the reading it was saved for.
 */
export function bulletinFromService(
  saved: ServiceBulletin,
  readings: { scriptures: readonly string[]; selected_ot_ref: string; selected_nt_ref: string },
): DraftBulletin {
  const picks = resolveReadings(readings.scriptures, readings.selected_ot_ref, readings.selected_nt_ref);
  const pasted: Record<string, string> = {};
  if (picks.ot !== null && saved.reading_text.ot !== "") pasted[picks.ot] = saved.reading_text.ot;
  if (picks.nt !== null && saved.reading_text.nt !== "") pasted[picks.nt] = saved.reading_text.nt;
  return {
    prelude: { ...saved.prelude },
    postlude: { ...saved.postlude },
    people: { ...saved.people },
    leaders: { ...saved.leaders },
    announcements: { ...saved.announcements },
    pasted,
    carried: CARRY_KEYS.filter((key) => (saved.unchecked ?? []).includes(key)),
    edited: [],
    carried_for: null,
    set_aside: null,
  };
}

/** What "From last week, not checked yet: …" calls each box. */
const CARRY_LABELS: Record<CarryKey, string> = {
  prelude: "prelude",
  postlude: "postlude",
  ushers: "ushers and counters",
  deacon: "deacon of the week",
  coffee_hour: "coffee hour",
  activities: "activities",
  prayer_concerns: "prayers and concerns",
  collection: "collection items",
  other: "other announcements",
};

/** The boxes still holding last week's text, unchecked, by label, in the step's order. */
export function notChecked(d: DraftV1): string[] {
  return CARRY_KEYS.filter((key) => d.bulletin.carried.includes(key)).map((key) => CARRY_LABELS[key]);
}

/** "From last week, not checked yet: coffee hour, activities." */
export function notCheckedLine(labels: readonly string[]): string {
  return `From last week, not checked yet: ${labels.join(", ")}.`;
}

/**
 * What the printed bulletin leaves out this week (PR 2 planning answer 3), in
 * the card's "Not filled in" order: the standing fields from the settings,
 * the three people as this week has them (when the settings are loaded), then
 * the prelude, the postlude and the announcements (all of them blank).
 */
export function printedNotFilledIn(settings: BulletinSettings | undefined, d: DraftV1): string[] {
  const p = bulletinPayload(d);
  const standing =
    settings === undefined
      ? []
      : notFilledIn({ ...settings, ...Object.fromEntries(PEOPLE.map((r) => [r, p.people[r] ?? settings[r]])) });
  const weekly = [
    ...(filled(p, "prelude") ? [] : ["prelude"]),
    ...(filled(p, "postlude") ? [] : ["postlude"]),
    ...(ANNOUNCEMENT_KEYS.some((key) => filled(p, key)) ? [] : ["announcements"]),
  ];
  return [...standing, ...weekly];
}

/** The step bar's status for the optional Bulletin step: "Optional", or how many boxes from last week to check. */
export function bulletinStatus(d: DraftV1): { kind: "optional" } | { kind: "to_check"; count: number } {
  const count = d.bulletin.carried.length;
  return count === 0 ? { kind: "optional" } : { kind: "to_check", count };
}
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````ts
 */
import type { ArchivedHymn, ServiceOut } from "@/lib/api/types";
````

**with:**

````ts
 *
 * Printed bulletin PR 2b: the payload holds the Bulletin step's fields as
 * `bulletin` (`bulletinPayload`) only when something is filled in, so a
 * draft saved before PR 2b keeps its fingerprint and stays "Saved" after the
 * draft v3 migration; the bodies sent always carry it (`serviceBody`).
 */
import type { ArchivedHymn, ServiceBulletin, ServiceOut } from "@/lib/api/types";
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````ts

import { fingerprint } from "./fingerprint";
````

**with:**

````ts

import { bulletinFromService, bulletinPayload, emptyServiceBulletin, isBlankBulletin } from "./bulletin";
import { fingerprint } from "./fingerprint";
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````ts
  hymnal: string | null;
````

**with:**

````ts
  hymnal: string | null;
  /** The Bulletin step's fields (printed bulletin PR 2b); left out when nothing is filled in. */
  bulletin?: ServiceBulletin;
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````ts
 * with a label, trimmed, without their ids.
````

**with:**

````ts
 * with a label, trimmed, without their ids; the bulletin fields when any is
 * filled in (PR 2b).
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````ts
  const picks = effectivePicks(draft);
````

**with:**

````ts
  const picks = effectivePicks(draft);
  const bulletin = bulletinPayload(draft);
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````ts
    hymnal: draft.hymns.hymnal,
````

**with:**

````ts
    hymnal: draft.hymns.hymnal,
    ...(isBlankBulletin(bulletin) ? {} : { bulletin }),
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````ts
 * them. `editing` names the service, its `saved_at` and its date; the
````

**with:**

````ts
 * them; the bulletin fields as saved, with nothing to check and no carry
 * (PR 2b). `editing` names the service, its `saved_at` and its date; the
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````ts
    },
  };
````

**with:**

````ts
    },
    // A server from before PR 2b-1 (only if it were reverted) sends none.
    bulletin: bulletinFromService(service.bulletin ?? emptyServiceBulletin(), service),
  };
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````ts
    liturgy: { ...d.liturgy, cards, communion_origin },
````

**with:**

````ts
    liturgy: { ...d.liturgy, cards, communion_origin },
    // Saved: what "Save as new service" set aside belongs to the other service (PR 2b-2).
    bulletin: { ...d.bulletin, set_aside: null },
````

**In `frontend/src/lib/draft/migrate.ts`, replace:**

````ts
import { DRAFT_VERSION, draftV1Schema, type DraftV1 } from "./schema";
````

**with:**

````ts
import { DRAFT_VERSION, draftV1Schema, freshBulletin, type DraftV1 } from "./schema";
````

**In `frontend/src/lib/draft/migrate.ts`, replace:**

````ts
 * 5a-3.
````

**with:**

````ts
 * 5a-3.
 *
 * 2 → 3 (printed bulletin PR 2b): `bulletin` starts empty (`freshBulletin`),
 * so an in-progress draft keeps everything else; last week's bulletin carries
 * in later like a new draft's, unless the draft is a saved service.
````

**In `frontend/src/lib/draft/migrate.ts`, replace:**

````ts
  },
````

**with:**

````ts
  },
  2: (draft) => ({ ...draft, bulletin: freshBulletin() }),
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
 * The per-church unsaved draft, version 2 (F §4.6; S "Draft store").
````

**with:**

````ts
 * The per-church unsaved draft, version 3 (F §4.6; S "Draft store").
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
 * `save_key_fingerprint` (`save-key.ts`). The names `DraftV1` and
````

**with:**

````ts
 * `save_key_fingerprint` (`save-key.ts`). Version 3 (printed bulletin PR 2b)
 * adds `bulletin`, the Bulletin step's weekly fields (`bulletin.ts`), and the
 * step id "bulletin". The names `DraftV1` and
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
export const DRAFT_VERSION = 2;

export const STEP_IDS = ["readings", "hymns", "liturgy", "review"] as const;
````

**with:**

````ts
export const DRAFT_VERSION = 3;

export const STEP_IDS = ["readings", "hymns", "liturgy", "bulletin", "review"] as const;
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts

export const draftV1Schema = z.object({
````

**with:**

````ts

/** The three people the Bulletin step can change for one week (`bulletin_settings.ROLES`). */
export const PEOPLE = ["worship_leader", "liturgist", "organist"] as const;
export type Person = (typeof PEOPLE)[number];
/** The announcements (PR 2 planning answer 4), in the printed order. */
export const ANNOUNCEMENT_KEYS = ["ushers", "deacon", "coffee_hour", "activities", "prayer_concerns", "collection", "other"] as const;
export type AnnouncementKey = (typeof ANNOUNCEMENT_KEYS)[number];
/** The boxes that carry forward from last week (PR 2 planning answer 5): the music and each announcement. */
export const CARRY_KEYS = ["prelude", "postlude", ...ANNOUNCEMENT_KEYS] as const;
export type CarryKey = (typeof CARRY_KEYS)[number];

const music = z.object({ title: text, composer: text });
const carryKeys = z.array(z.enum(CARRY_KEYS));
/** This week's name for each person; null follows the bulletin settings, "" is no one this week. */
const people = z.object(Object.fromEntries(PEOPLE.map((key) => [key, text.nullable()])) as Record<Person, z.ZodNullable<typeof text>>);
const bulletin = z.object({
  prelude: music,
  postlude: music,
  people,
  /** A part's leader this week, by element key (`bulletin_settings.ELEMENT_KEYS`). */
  leaders: z.record(text, text),
  announcements: z.object(Object.fromEntries(ANNOUNCEMENT_KEYS.map((key) => [key, text])) as Record<AnnouncementKey, typeof text>),
  /** Pasted reading text by the reading's reference, so a changed reading starts with an empty box. */
  pasted: z.record(text, text),
  /** The boxes still holding last week's text, not edited or kept since (saved with the service as `unchecked`). */
  carried: carryKeys,
  /** The boxes typed in, edited or kept: last week's never carries into them again (a box at a time). */
  edited: carryKeys,
  /** The date last week's bulletin was looked up for; null: not yet. */
  carried_for: dateIso.nullable(),
  /**
   * A saved service on another date ("Save as new service"): its people,
   * part leaders, pasted texts and marks, set aside while the date differs
   * from the saved one and put back if it is the saved date again; null
   * otherwise (`bulletin.ts` `followSaveMode`).
   */
  set_aside: z
    .object({ people, leaders: z.record(text, text), pasted: z.record(text, text), carried: carryKeys, edited: carryKeys })
    .nullable(),
});
export type DraftBulletin = z.infer<typeof bulletin>;

export const draftV1Schema = z.object({
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
  }),
});
````

**with:**

````ts
  }),
  bulletin,
});
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
 * first Sunday, a new save key with no pending fingerprint, on step 1.
````

**with:**

````ts
 * first Sunday, an empty Bulletin step (PR 2b; last week's carries in when
 * the Bulletin step or Review shows it), a new save key with no pending
 * fingerprint, on step 1.
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
    },
  };
````

**with:**

````ts
    },
    bulletin: freshBulletin(),
  };
}

/** An empty Bulletin step: nothing filled in, the settings' people, no carry looked up yet. */
export function freshBulletin(): DraftBulletin {
  return {
    prelude: { title: "", composer: "" },
    postlude: { title: "", composer: "" },
    people: { worship_leader: null, liturgist: null, organist: null },
    leaders: {},
    announcements: { ushers: "", deacon: "", coffee_hour: "", activities: "", prayer_concerns: "", collection: "", other: "" },
    pasted: {},
    carried: [],
    edited: [],
    carried_for: null,
    set_aside: null,
  };
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts

import { fingerprint } from "./fingerprint";
````

**with:**

````ts

import { bulletinStatus } from "./bulletin";
import { fingerprint } from "./fingerprint";
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
  | { kind: "soon" }
````

**with:**

````ts
  | { kind: "soon" }
  /** The Bulletin step (printed bulletin PR 2b): never required, the muted "Optional"... */
  | { kind: "optional" }
  /** ...or how many boxes still hold last week's text, unchecked: "2 to check". */
  | { kind: "to_check"; count: number }
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
  if (!shipped.has(step)) return { kind: "soon" };
````

**with:**

````ts
  if (!shipped.has(step)) return { kind: "soon" };
  if (step === "bulletin") return bulletinStatus(draft);
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
 * trimming) do not (owner answer 1, 2026-09-30, slice 4b).
````

**with:**

````ts
 * trimming) do not (owner answer 1, 2026-09-30, slice 4b). On the Bulletin
 * step (printed bulletin PR 2b) a box typed, edited or kept counts, and so
 * does a person, a part's leader or a pasted text; last week's text carried
 * in and not touched does not (it comes back on its own).
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
  const l = draft.liturgy;
````

**with:**

````ts
  const l = draft.liturgy;
  const b = draft.bulletin;
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
    l.custom_elements.length === 0 &&
````

**with:**

````ts
    l.custom_elements.length === 0 &&
    b.edited.length === 0 &&
    Object.values(b.people).every((name) => name === null) &&
    Object.keys(b.leaders).length === 0 &&
    Object.keys(b.pasted).length === 0 &&
````

**In `frontend/src/lib/queries/keys.ts`, replace:**

````ts
  service: (id: string, serviceId: string) => ["church", id, "service", serviceId] as const,
````

**with:**

````ts
  service: (id: string, serviceId: string) => ["church", id, "service", serviceId] as const,
  /** Under the services prefix, so a save or a delete (which refresh it) changes what carries forward (PR 2b). */
  previousBulletin: (id: string, dateIso: string) => ["church", id, "services", "previous-bulletin", dateIso] as const,
````

**In `frontend/src/lib/queries/services.ts`, replace:**

````ts
 *   server's order), "Show more" reading the next offset.
````

**with:**

````ts
 *   server's order), "Show more" reading the next offset.
 * - `usePreviousBulletin(date, enabled)`: last week's bulletin, for carry
 *   forward (printed bulletin PR 2b).
````

**In `frontend/src/lib/queries/services.ts`, replace:**

````ts
import { useInfiniteQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
````

**with:**

````ts
import { useInfiniteQuery, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
````

**In `frontend/src/lib/queries/services.ts`, replace:**

````ts
import type { DeletedOut, ServiceOut, ServicePage } from "@/lib/api/types";
````

**with:**

````ts
import type { DeletedOut, PreviousBulletin, ServiceOut, ServicePage } from "@/lib/api/types";
````

**In `frontend/src/lib/queries/services.ts`, replace:**

````ts
      return last.items.length > 0 && next < last.total ? next : undefined;
    },
  });
````

**with:**

````ts
      return last.items.length > 0 && next < last.total ? next : undefined;
    },
  });
}

/**
 * `GET /services/previous-bulletin?before=` (printed bulletin PR 2b): what a
 * new week's bulletin carries forward from the latest service dated before
 * `dateIso`. Fetched only while carrying is due (`enabled`); under the
 * services key, so a save or a delete refreshes it.
 */
export function usePreviousBulletin(dateIso: string, enabled: boolean) {
  const api = useApi();
  const church = useChurch();
  return useQuery<PreviousBulletin, ApiError>({
    queryKey: keys.previousBulletin(church.id, dateIso),
    queryFn: ({ signal }) => api.church<PreviousBulletin>(`/services/previous-bulletin?before=${dateIso}`, { signal }),
    enabled,
  });
````

- [ ] **Step 4: See them pass, the suite, types and lint**

Run: the Step 2 command, then the suite and `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:** `      Tests  72 passed (72)`; ` Test Files  86 passed (86)`, `      Tests  690 passed (690)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/draft/bulletin.ts frontend/src/lib/draft/bulletin.test.ts frontend/src/lib/draft/schema.ts frontend/src/lib/draft/schema.test.ts frontend/src/lib/draft/migrate.ts frontend/src/lib/draft/migrate.test.ts frontend/src/lib/draft/store.test.ts frontend/src/lib/draft/mapping.ts frontend/src/lib/draft/mapping.test.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/status.test.ts frontend/src/lib/documents.ts frontend/src/lib/documents.test.ts frontend/src/lib/queries/keys.ts frontend/src/lib/queries/keys.test.ts frontend/src/lib/queries/services.ts frontend/src/components/builder/step-progress.tsx
git commit -q -m "Printed bulletin PR 2b-2: the draft v3 and the bulletin on the client" -m "The draft gains the Bulletin step's fields (version 3; a version 2
draft migrates with an empty bulletin) and the step id. lib/draft/
bulletin.ts edits them, carries last week's music and announcements
into a new draft once per date into every box not yet edited or kept
(never while a save's outcome is unknown), treats Save as new service as
a new week, builds the payload (the pasted text of the readings printed,
the boxes still to check), opens a saved service's, and says what is
not filled in or not checked. The payload holds the bulletin only when
something is filled in, so a draft saved before 2b stays Saved; every
body sends it, cut to the limits, and the 409 check reads it as the
server stores it." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1425 passed, 17 skipped`; frontend `690 passed` in 86 files.

### Task 8: The Bulletin step (S "The Bulletin step"; planning answers 4-7; F §4.7, §4.8; clarifications 2-8, 16, 20)

**Files:**
- Create: `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, `frontend/src/app/(signed-in)/(church)/builder/bulletin/page.tsx`, `frontend/src/components/builder/bulletin/bulletin-step.tsx`, `frontend/src/components/builder/bulletin/use-bulletin-carry.ts`
- Modify: `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/draft/status.test.ts`, `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/lib/draft/steps.ts`, `frontend/src/components/builder/step-progress.tsx`, `frontend/src/app/(signed-in)/(church)/builder/page.tsx`, `frontend/src/components/builder/review/review-send-step.tsx`

The builder shell's test renders every step route, the Bulletin step's included, and the step bar's five links; Review's step bar tests move from the fourth link to the fifth. `/builder` opens Review & send for a `last_step` that is no longer in the bar (what a rollback of 2b-2 leaves; clarification 20), and Review's doc comment says "Step 5".

- [ ] **Step 1: Write the failing tests (and the fixture)**

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
import BuilderIndexPage from "@/app/(signed-in)/(church)/builder/page";
````

**with:**

````tsx
import BuilderIndexPage from "@/app/(signed-in)/(church)/builder/page";
import BulletinStepPage from "@/app/(signed-in)/(church)/builder/bulletin/page";
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
  me,
````

**with:**

````tsx
  me,
  previousBulletin,
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
    "GET /church/bulletin-settings": bulletinSettings(),
````

**with:**

````tsx
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
      ["/builder/liturgy", <LiturgyStepPage key="l" />, 3, "Liturgy", ["Back", "Next: Review"]],
      ["/builder/review", <ReviewStepPage key="v" />, 4, "Review & send", ["Back"]],
````

**with:**

````tsx
      ["/builder/liturgy", <LiturgyStepPage key="l" />, 3, "Liturgy", ["Back", "Next: Bulletin"]],
      ["/builder/bulletin", <BulletinStepPage key="b" />, 4, "Bulletin", ["Back", "Next: Review"]],
      ["/builder/review", <ReviewStepPage key="v" />, 5, "Review & send", ["Back"]],
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
      expect(screen.getByText(`Step ${number} of 4 · ${label}`)).toBeInTheDocument();
````

**with:**

````tsx
      expect(screen.getByText(`Step ${number} of 5 · ${label}`)).toBeInTheDocument();
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
        "4 Review & send Not in archive",
````

**with:**

````tsx
        "4 Bulletin Optional", // shipped in printed bulletin PR 2b
        "5 Review & send Not in archive",
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
        "/builder/liturgy",
        "/builder/review",
````

**with:**

````tsx
        "/builder/liturgy",
        "/builder/bulletin",
        "/builder/review",
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else {
````

**with:**

````tsx
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else if (number === 4) {
        // Bulletin is the real step from printed bulletin PR 2b.
        expect(within(card).getByRole("textbox", { name: "Prelude title" })).toBeInTheDocument();
      } else {
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
      if (number === 4) {
````

**with:**

````tsx
      if (number === 5) {
````

**Create `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`:**

````tsx
/**
 * The Bulletin step (printed bulletin PR 2b; spec "The Bulletin step"; PR 2
 * planning answers 4-7). The step renders inside the builder layout; the
 * clock is fixed at Tuesday, September 29, 2026, so a fresh draft is dated
 * Sunday, October 4, 2026. Last week's bulletin (`GET
 * /services/previous-bulletin`) is empty unless a test says otherwise.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import BulletinStepPage from "@/app/(signed-in)/(church)/builder/bulletin/page";
import { editScriptureLines } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  filledBulletinSettings,
  lectionaryRoute,
  me,
  previousBulletin,
  serviceBulletin,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { FROM_LAST_WEEK } from "./bulletin-step";

const KEY = draftKey(USER_ID, church().id);

/** Last week's service (invented): the prelude, the ushers and the coffee hour. */
const LAST_WEEK = previousBulletin({
  service_id: "s-last",
  service_date_iso: "2026-09-27",
  bulletin: serviceBulletin({
    prelude: { title: "Morning Voluntary", composer: "Pat Example" },
    announcements: { ...serviceBulletin().announcements, ushers: "Sam Sample", coffee_hour: "The Example family" },
  }),
});

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

function renderStep(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /church/bulletin-settings": filledBulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    ...routes,
  });
  const view = renderWithProviders(
    <BuilderLayout>
      <BulletinStepPage />
    </BuilderLayout>,
    { me: me(), church: church(), path: "/builder/bulletin" },
  );
  return { ...view, api };
}

function carryRequests(api: { requests: { path: string }[] }) {
  return api.requests.filter((r) => r.path.startsWith("/services/previous-bulletin"));
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the Bulletin step (printed bulletin PR 2b)", () => {
  it("shows the music, who leads, the announcements and the reading text, all optional, and stores what is typed", async () => {
    const { user } = renderStep();
    const step = await screen.findByRole("region", { name: "Bulletin" });
    expect(within(step).getByText(/^Optional\. What this week's printed bulletin adds/)).toBeInTheDocument();
    expect(within(step).getAllByRole("group").map((g) => g.querySelector("legend")?.textContent)).toEqual([
      "Music",
      "Who leads",
      "Announcements",
      "Reading text",
    ]);
    for (const name of ["Prelude title", "Prelude composer", "Postlude title", "Postlude composer", "Ushers and counters",
      "Deacon of the week", "Coffee hour"]) {
      expect(within(step).getByRole("textbox", { name })).toHaveClass("h-11"); // 44 px on a phone
    }
    expect(within(step).getByRole("textbox", { name: "Prayers and concerns" }).tagName).toBe("TEXTAREA");
    expect(within(step).getByText("Choose the readings on step 1 to paste their text.")).toBeInTheDocument();
    expect(within(step).getByRole("link", { name: "Bulletin settings" })).toHaveAttribute("href", "/bulletin-settings");

    await user.type(within(step).getByRole("textbox", { name: "Postlude title" }), "Festive Postlude");
    await user.type(within(step).getByRole("textbox", { name: "Other announcements" }), "The office is closed.");
    await waitFor(() => expect(stored().bulletin.announcements.other).toBe("The office is closed."));
    expect(stored().bulletin.postlude.title).toBe("Festive Postlude");
  });

  it("carries last week's music and announcements into a new draft, each marked until it is edited or kept", async () => {
    const { user, api } = renderStep(testDraft(), { "GET /services/previous-bulletin": LAST_WEEK });
    const step = await screen.findByRole("region", { name: "Bulletin" });
    const coffee = within(step).getByRole("textbox", { name: "Coffee hour" });
    await waitFor(() => expect(coffee).toHaveValue("The Example family"));
    expect(carryRequests(api).map((r) => r.path)).toEqual(["/services/previous-bulletin?before=2026-10-04"]);
    expect(within(step).getByRole("textbox", { name: "Prelude title" })).toHaveValue("Morning Voluntary");
    expect(within(step).getAllByText(FROM_LAST_WEEK)).toHaveLength(3);
    expect(coffee).toHaveAccessibleDescription(FROM_LAST_WEEK);

    await user.clear(coffee);
    await user.type(coffee, "The Sample family");
    await user.click(within(step).getByRole("button", { name: "Keep ushers and counters as is" }));
    expect(within(step).getAllByText(FROM_LAST_WEEK)).toHaveLength(1); // the prelude's, still to check
    await waitFor(() => expect(stored().bulletin.carried).toEqual(["prelude"]));
    expect(stored().bulletin.announcements).toMatchObject({ ushers: "Sam Sample", coffee_hour: "The Sample family" });
    expect(screen.getAllByRole("link").find((a) => a.getAttribute("href") === "/builder/bulletin")).toHaveTextContent(
      "4 Bulletin 1 to check",
    );
  });

  it("never carries into a saved service, and says so with Try again when last week's cannot be loaded", async () => {
    const saved = testDraft((d) => ({ ...d, editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-10-04" } }));
    const first = renderStep(saved, { "GET /services/previous-bulletin": LAST_WEEK });
    await screen.findByRole("region", { name: "Bulletin" });
    expect(screen.getByRole("textbox", { name: "Coffee hour" })).toHaveValue("");
    expect(carryRequests(first.api)).toEqual([]);
    first.unmount();

    let fail = true;
    const { user } = renderStep(testDraft(), {
      "GET /services/previous-bulletin": () => (fail ? fakeError(503, "unavailable", "Try again later.") : LAST_WEEK),
    });
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Last week's announcements could not be loaded.");
    // Typing in one box keeps the message and Try again; the other boxes still carry (plan review fix M1).
    await user.type(screen.getByRole("textbox", { name: "Other announcements" }), "Typed first.");
    expect(screen.getByRole("alert")).toBe(alert);
    fail = false;
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Coffee hour" })).toHaveValue("The Example family"));
    expect(screen.getByRole("textbox", { name: "Other announcements" })).toHaveValue("Typed first.");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the three people from the bulletin settings, changeable for this week, and a part's leader behind a button", async () => {
    const { user } = renderStep();
    const group = await screen.findByRole("group", { name: "Who leads" });
    const organist = await within(group).findByRole("textbox", { name: "Organist" });
    expect(organist).toHaveValue("Jordan Doe");
    expect(within(group).getByRole("textbox", { name: "Worship leader" })).toHaveValue("Rev. Alex Example");
    await user.clear(organist);
    await user.type(organist, "Lee Sample");
    expect(within(group).getByText("Changed for this week.")).toBeInTheDocument();
    await waitFor(() => expect(stored().bulletin.people.organist).toBe("Lee Sample"));
    await user.click(within(group).getByRole("button", { name: "Undo the change to Organist" }));
    expect(organist).toHaveValue("Jordan Doe");
    await waitFor(() => expect(stored().bulletin.people.organist).toBeNull());

    // A guest this week: the parts still say who usually leads them (plan review fix M6).
    const leader = within(group).getByRole("textbox", { name: "Worship leader" });
    await user.clear(leader);
    await user.type(leader, "Rev. Guest");
    const toggle = within(group).getByRole("button", { name: "Change who leads a part" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).not.toHaveAttribute("aria-controls"); // nothing to point at while closed (plan review fix M7)
    expect(within(group).queryByRole("textbox", { name: "Sermon" })).toBeNull();
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(document.getElementById(toggle.getAttribute("aria-controls") ?? "")).not.toBeNull();
    const sermon = within(group).getByRole("textbox", { name: "Sermon" });
    expect(sermon).toHaveAccessibleDescription("Usually Rev. Alex Example");
    expect(within(group).getByRole("textbox", { name: "Offering" })).toHaveAccessibleDescription("Usually no one");
    await user.type(sermon, "Rev. Guest");
    await waitFor(() => expect(stored().bulletin.leaders).toEqual({ sermon: "Rev. Guest" }));
  });

  it("says so with Try again when the bulletin settings cannot be loaded, and shows no field for who leads", async () => {
    let fail = true;
    const { user } = renderStep(testDraft(), {
      "GET /church/bulletin-settings": () => (fail ? fakeError(503, "unavailable", "Try again later.") : filledBulletinSettings()),
    });
    const group = await screen.findByRole("group", { name: "Who leads" });
    const alert = await within(group).findByRole("alert");
    expect(alert).toHaveTextContent("Bulletin settings could not be loaded.");
    expect(within(group).queryByRole("textbox")).toBeNull();
    fail = false;
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await within(group).findByRole("textbox", { name: "Organist" })).toHaveValue("Jordan Doe");
  });

  it("marks a saved service's music and announcements to check on another date, and starts this week's people empty", async () => {
    const saved = testDraft((d) => ({
      ...d,
      editing: { service_id: "s1", saved_at: "2026-09-27T12:00:00+00:00", date_iso: "2026-09-27" },
      bulletin: {
        ...d.bulletin,
        prelude: { title: "Morning Voluntary", composer: "" },
        people: { worship_leader: "Rev. Guest", liturgist: null, organist: null },
        announcements: { ...d.bulletin.announcements, coffee_hour: "The Example family" },
      },
    }));
    const { api } = renderStep(saved);
    const step = await screen.findByRole("region", { name: "Bulletin" });
    await waitFor(() => expect(within(step).getAllByText(FROM_LAST_WEEK)).toHaveLength(2));
    expect(within(step).getByRole("textbox", { name: "Coffee hour" })).toHaveAccessibleDescription(FROM_LAST_WEEK);
    expect(await within(step).findByRole("textbox", { name: "Worship leader" })).toHaveValue("Rev. Alex Example");
    await waitFor(() => expect(stored().bulletin.set_aside?.people.worship_leader).toBe("Rev. Guest"));
    expect(carryRequests(api)).toEqual([]); // a saved service never looks up last week's
  });

  it("has a box per reading the files print, and keeps the pasted text under that reading", async () => {
    const draft = editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46");
    const { user } = renderStep(draft);
    const group = await screen.findByRole("group", { name: "Reading text" });
    expect(within(group).getAllByRole("textbox")).toHaveLength(2);
    const nt = within(group).getByRole("textbox", { name: "New Testament Reading: Philippians 3:4b-14" });
    expect(within(group).getByRole("textbox", { name: "First Reading: Isaiah 5:1-7" })).toHaveValue("");
    await user.type(nt, "Pasted text.");
    await waitFor(() => expect(stored().bulletin.pasted).toEqual({ "Philippians 3:4b-14": "Pasted text." }));
  });
});
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Review & send Not in archive");
````

**with:**

````tsx
    expect(within(progress).getAllByRole("link")[4]).toHaveTextContent("5 Review & send Not in archive");
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Review & send Saved");
````

**with:**

````tsx
    expect(within(progress).getAllByRole("link")[4]).toHaveTextContent("5 Review & send Saved");
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Review & send Unsaved changes");
````

**with:**

````tsx
    expect(within(progress).getAllByRole("link")[4]).toHaveTextContent("5 Review & send Unsaved changes");
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
  it("lists the four steps in order, ships all four (2c, 3b, 4b and Review in 5a-3), and reads a step from its path", () => {
````

**with:**

````ts
  it("lists the five steps in order, ships all five (2c, 3b, 4b, Review in 5a-3, Bulletin in PR 2b), and reads a step from its path", () => {
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
      [3, "Liturgy", "/builder/liturgy", "hymns", "review"],
      [4, "Review & send", "/builder/review", "liturgy", null],
    ]);
    expect([...SHIPPED_STEPS]).toEqual(["readings", "hymns", "liturgy", "review"]);
````

**with:**

````ts
      [3, "Liturgy", "/builder/liturgy", "hymns", "bulletin"],
      [4, "Bulletin", "/builder/bulletin", "liturgy", "review"],
      [5, "Review & send", "/builder/review", "bulletin", null],
    ]);
    expect([...SHIPPED_STEPS]).toEqual(["readings", "hymns", "liturgy", "bulletin", "review"]);
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["incomplete", "incomplete", "incomplete", "not_in_archive"]);
````

**with:**

````ts
    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["incomplete", "incomplete", "incomplete", "optional", "not_in_archive"]);
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  OutlineItem,
````

**with:**

````ts
  OutlineItem,
  PreviousBulletin,
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts

/** One row of `GET /services` (`ServiceSummary`): `savedService()`'s, unless overridden. */
````

**with:**

````ts

/** `GET /services/previous-bulletin` (printed bulletin PR 2b): no service before the date, unless overridden. */
export function previousBulletin(overrides: Partial<PreviousBulletin> = {}): PreviousBulletin {
  return { service_id: null, service_date_iso: null, bulletin: serviceBulletin(), ...overrides };
}

/** One row of `GET /services` (`ServiceSummary`): `savedService()`'s, unless overridden. */
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/builder/bulletin src/components/builder/builder-shell.test.tsx src/lib/draft/status.test.ts src/components/builder/review/review-send-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the step's route does not exist yet):
```
   × steps (S steps.ts) > lists the five steps in order, ships all five (2c, 3b, 4b, Review in 5a-3, Bulletin in PR 2b), and reads a step from its path <t>ms
   × stepStatus (F §4.7) > shows Soon for unshipped steps and Not in archive for Review <t>ms
   × Review & send: saving (slice 5a-3) > saves a new service with the draft's key, saves changes with If-Match, and every status follows <t>ms
 FAIL  |dom| src/components/builder/builder-shell.test.tsx [ src/components/builder/builder-shell.test.tsx ]
 FAIL  |dom| src/components/builder/bulletin/bulletin-step.test.tsx [ src/components/builder/bulletin/bulletin-step.test.tsx ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 3 ⎯⎯⎯⎯⎯⎯⎯
      Tests  3 failed | 34 passed (37)
```

- [ ] **Step 3: The step, its route, the carry hook, the five steps**

**Create `frontend/src/app/(signed-in)/(church)/builder/bulletin/page.tsx`:**

````tsx
"use client";

import { BulletinStep } from "@/components/builder/bulletin/bulletin-step";

/** Step: Bulletin (printed bulletin PR 2b): the printed bulletin's weekly fields. */
export default function BulletinStepPage() {
  return <BulletinStep />;
}
````

**Create `frontend/src/components/builder/bulletin/bulletin-step.tsx`:**

````tsx
"use client";

import Link from "next/link";
import { useState, type ReactNode } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { BulletinSettings } from "@/lib/api/types";
import { ELEMENTS, ROLES } from "@/lib/bulletin-settings";
import {
  keepCarried,
  MAX_LENGTH,
  setAnnouncement,
  setMusic,
  setPartLeader,
  setPastedText,
  setPerson,
  type Piece,
} from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { effectivePicks } from "@/lib/draft/readings";
import type { AnnouncementKey, CarryKey, DraftV1, Person } from "@/lib/draft/schema";
import { useBulletinSettings } from "@/lib/queries/bulletin-settings";

import { useBulletinCarry } from "./use-bulletin-carry";

export const BULLETIN_INTRO =
  "Optional. What this week's printed bulletin adds to the service. A box left blank is left off the bulletin.";
export const FROM_LAST_WEEK = "From last week. Check before printing.";
export const CARRY_FAILED = "Last week's announcements could not be loaded.";
export const SETTINGS_FAILED = "Bulletin settings could not be loaded.";
export const WHO_LEADS_HELP = "From the bulletin settings. A change here is for this week only.";
export const PARTS_HELP = "A name here prints on that part this week only. Leave it blank for the usual leader.";
export const READINGS_HELP =
  "Paste a reading's text to print it instead of the text the app fetches, for a translation the app cannot fetch. Include the translation's notice if it asks for one.";
export const NO_READINGS = "Choose the readings on step 1 to paste their text.";

const ANNOUNCEMENTS: readonly { key: AnnouncementKey; label: string; long: boolean }[] = [
  { key: "ushers", label: "Ushers and counters", long: false },
  { key: "deacon", label: "Deacon of the week", long: false },
  { key: "coffee_hour", label: "Coffee hour", long: false },
  { key: "activities", label: "This week's activities", long: true },
  { key: "prayer_concerns", label: "Prayers and concerns", long: true },
  { key: "collection", label: "Items for collection", long: true },
  { key: "other", label: "Other announcements", long: true },
];

/** "From last week. Check before printing." under a box still holding last week's text, with "Keep as is". */
function CarriedNote({ id, carryKey, name }: { id: string; carryKey: CarryKey; name: string }) {
  const { draft, update } = useDraft();
  if (!draft.bulletin.carried.includes(carryKey)) return null;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
      <p id={id} className="text-sm text-muted-foreground">
        {FROM_LAST_WEEK}
      </p>
      <Button type="button" variant="outline" size="touch" aria-label={`Keep ${name} as is`} onClick={() => update((d) => keepCarried(d, carryKey))}>
        Keep as is
      </Button>
    </div>
  );
}

function Group({ id, title, help, children }: { id: string; title: string; help?: string; children: ReactNode }) {
  return (
    <fieldset aria-describedby={help ? `${id}-help` : undefined} className="grid min-w-0 gap-4 rounded-lg border p-4">
      <legend className="px-1 text-base font-medium">{title}</legend>
      {help ? (
        <p id={`${id}-help`} className="text-sm text-muted-foreground">
          {help}
        </p>
      ) : null}
      {children}
    </fieldset>
  );
}

function TextField({
  id,
  label,
  value,
  maxLength,
  long = false,
  describedBy,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  maxLength: number;
  long?: boolean;
  describedBy?: string;
  onChange: (value: string) => void;
}) {
  const shared = { id, value, maxLength, "aria-describedby": describedBy, onChange: (e: { target: { value: string } }) => onChange(e.target.value) };
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      {long ? <Textarea {...shared} rows={3} /> : <Input {...shared} className="h-11" />}
    </div>
  );
}

function Music({ piece, name }: { piece: Piece; name: string }) {
  const { draft, update } = useDraft();
  const note = `bulletin-${piece}-carried`;
  const describedBy = draft.bulletin.carried.includes(piece) ? note : undefined;
  return (
    <div className="grid gap-3">
      <TextField
        id={`bulletin-${piece}-title`}
        label={`${name} title`}
        value={draft.bulletin[piece].title}
        maxLength={MAX_LENGTH.title}
        describedBy={describedBy}
        onChange={(v) => update((d) => setMusic(d, piece, "title", v))}
      />
      <TextField
        id={`bulletin-${piece}-composer`}
        label={`${name} composer`}
        value={draft.bulletin[piece].composer}
        maxLength={MAX_LENGTH.composer}
        describedBy={describedBy}
        onChange={(v) => update((d) => setMusic(d, piece, "composer", v))}
      />
      <CarriedNote id={note} carryKey={piece} name={name.toLowerCase()} />
    </div>
  );
}

/** This week's name for a role: the week's change, else the settings' name. */
function weekName(draft: DraftV1, settings: BulletinSettings, role: Person): string {
  return draft.bulletin.people[role] ?? settings[role];
}

function WhoLeads() {
  const { draft, update } = useDraft();
  const settingsQuery = useBulletinSettings();
  const settings = settingsQuery.data;
  const [partsOpen, setPartsOpen] = useState(() => Object.keys(draft.bulletin.leaders).length > 0);
  if (settings === undefined && settingsQuery.isPending) {
    return (
      <Group id="bulletin-who" title="Who leads" help={WHO_LEADS_HELP}>
        <div role="status" aria-label="Loading who leads" className="grid gap-3">
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
        </div>
      </Group>
    );
  }
  if (settings === undefined) {
    // Without the settings the usual names are unknown: no field that could store one as this week's change.
    return (
      <Group id="bulletin-who" title="Who leads" help={WHO_LEADS_HELP}>
        <div role="alert" className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <p className="text-sm">{SETTINGS_FAILED}</p>
          <Button type="button" variant="outline" size="touch" onClick={() => void settingsQuery.refetch()}>
            Try again
          </Button>
        </div>
      </Group>
    );
  }
  return (
    <Group id="bulletin-who" title="Who leads" help={WHO_LEADS_HELP}>
      {ROLES.map(({ key, label }) => {
        const changed = draft.bulletin.people[key] !== null;
        return (
          <div key={key} className="grid gap-2">
            <TextField
              id={`bulletin-person-${key}`}
              label={label}
              value={weekName(draft, settings, key)}
              maxLength={MAX_LENGTH.person}
              describedBy={changed ? `bulletin-person-${key}-changed` : undefined}
              onChange={(v) => update((d) => setPerson(d, key, v === settings[key] ? null : v))}
            />
            {changed ? (
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                <p id={`bulletin-person-${key}-changed`} className="text-sm text-muted-foreground">
                  Changed for this week.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  size="touch"
                  aria-label={`Undo the change to ${label}`}
                  onClick={() => update((d) => setPerson(d, key, null))}
                >
                  Undo the change
                </Button>
              </div>
            ) : null}
          </div>
        );
      })}
      <Button
        type="button"
        variant="outline"
        size="touch"
        className="w-full sm:w-fit"
        aria-expanded={partsOpen}
        aria-controls={partsOpen ? "bulletin-parts" : undefined}
        onClick={() => setPartsOpen((open) => !open)}
      >
        Change who leads a part
      </Button>
      {partsOpen ? (
        <div id="bulletin-parts" className="grid gap-4">
          <p className="text-sm text-muted-foreground">{PARTS_HELP}</p>
          {ELEMENTS.map(({ key, label }) => {
            // The usual leader is the settings' name, not this week's change (plan review fix M6).
            const role = settings.leaders[key];
            const usual = role ? settings[role] : "";
            return (
              <div key={key} className="grid gap-2">
                <TextField
                  id={`bulletin-part-${key}`}
                  label={label}
                  value={draft.bulletin.leaders[key] ?? ""}
                  maxLength={MAX_LENGTH.person}
                  describedBy={`bulletin-part-${key}-usual`}
                  onChange={(v) => update((d) => setPartLeader(d, key, v))}
                />
                <p id={`bulletin-part-${key}-usual`} className="text-sm text-muted-foreground">
                  {usual ? `Usually ${usual}` : "Usually no one"}
                </p>
              </div>
            );
          })}
        </div>
      ) : null}
    </Group>
  );
}

function Announcements() {
  const { draft, update } = useDraft();
  return (
    <Group id="bulletin-announcements" title="Announcements">
      {ANNOUNCEMENTS.map(({ key, label, long }) => {
        const note = `bulletin-${key}-carried`;
        return (
          <div key={key} className="grid gap-2">
            <TextField
              id={`bulletin-${key}`}
              label={label}
              value={draft.bulletin.announcements[key]}
              maxLength={MAX_LENGTH[key]}
              long={long}
              describedBy={draft.bulletin.carried.includes(key) ? note : undefined}
              onChange={(v) => update((d) => setAnnouncement(d, key, v))}
            />
            <CarriedNote id={note} carryKey={key} name={label.toLowerCase()} />
          </div>
        );
      })}
    </Group>
  );
}

function ReadingTexts() {
  const { draft, update } = useDraft();
  const picks = effectivePicks(draft);
  const readings = [
    { slot: "ot", name: "First Reading", ref: picks.ot },
    { slot: "nt", name: "New Testament Reading", ref: picks.nt },
  ].filter((r): r is { slot: string; name: string; ref: string } => r.ref !== null);
  return (
    <Group id="bulletin-readings" title="Reading text" help={READINGS_HELP}>
      {readings.length === 0 ? <p className="text-sm text-muted-foreground">{NO_READINGS}</p> : null}
      {readings.map(({ slot, name, ref }) => (
        <TextField
          key={slot}
          id={`bulletin-text-${slot}`}
          label={`${name}: ${ref}`}
          value={draft.bulletin.pasted[ref] ?? ""}
          maxLength={MAX_LENGTH.reading_text}
          long
          onChange={(v) => update((d) => setPastedText(d, ref, v))}
        />
      ))}
    </Group>
  );
}

/**
 * Step 4, Bulletin (printed bulletin PR 2b; spec "The Bulletin step"; PR 2
 * planning answers 4-7): what the week's printed bulletin adds to the
 * service, all optional (it never blocks Review, the Word copies or the
 * printed bulletin). The prelude and postlude; who leads (the bulletin
 * settings' three people, changeable for this week, and each part's leader
 * behind "Change who leads a part"); the announcements; and per reading a
 * box for its pasted text. Last week's music and announcements carry in
 * (`useBulletinCarry`), each such box marked "From last week. Check before
 * printing." until it is edited or kept. It reads and writes only the
 * draft; the Bulletin settings button opens the standing settings.
 */
export function BulletinStep() {
  const carry = useBulletinCarry();
  return (
    <section aria-labelledby="bulletin-step-title" className="grid gap-6">
      <div className="grid gap-1">
        <h2 id="bulletin-step-title" className="text-lg font-semibold">
          Bulletin
        </h2>
        <p className="text-sm text-muted-foreground">{BULLETIN_INTRO}</p>
      </div>
      {carry.failed ? (
        <div role="alert" className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <p className="text-sm">{CARRY_FAILED}</p>
          <Button type="button" variant="outline" size="touch" onClick={carry.retry}>
            Try again
          </Button>
        </div>
      ) : null}
      <Group id="bulletin-music" title="Music">
        <Music piece="prelude" name="Prelude" />
        <Music piece="postlude" name="Postlude" />
      </Group>
      <WhoLeads />
      <Announcements />
      <ReadingTexts />
      <Link href="/bulletin-settings" className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}>
        Bulletin settings
      </Link>
    </section>
  );
}
````

**Create `frontend/src/components/builder/bulletin/use-bulletin-carry.ts`:**

````ts
"use client";

/**
 * Carry forward (printed bulletin PR 2b; PR 2 planning answer 5), run by the
 * Bulletin step and Review & send, the two steps that show or print the
 * bulletin. While carrying is due for the draft (`shouldCarry`: not a saved
 * service, no save with an unknown outcome, a real date, a music or
 * announcement box not yet typed in or kept, not yet looked up for this
 * date), it reads last week's bulletin
 * (`GET /services/previous-bulletin?before=<date>`) and carries its music and
 * announcements into the untouched boxes through `autoUpdate` (stamped 1 ms
 * after the draft it changes, so it never outranks typing in another tab),
 * checking again inside the recipe against the latest draft. A failed
 * lookup stays reported (`failed`) until a retry succeeds, typing in a box
 * included. It also applies "Save as new service" (`followSaveMode`): a
 * saved service on another date has its boxes marked to check and this
 * week's people, leaders and texts emptied. Only the visible tab changes the
 * draft, as the lectionary fill (`usePageVisible`).
 */
import { useEffect } from "react";

import { usePageVisible } from "@/components/builder/lectionary-sync";
import { applyCarry, followSaveMode, shouldCarry } from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { usePreviousBulletin } from "@/lib/queries/services";

export function useBulletinCarry(): { failed: boolean; retry: () => void } {
  const { draft, autoUpdate } = useDraft();
  const date = draft.readings.date_iso;
  const due = shouldCarry(draft);
  const query = usePreviousBulletin(date, due);
  const visible = usePageVisible();
  const data = query.data;
  const copyDue = followSaveMode(draft) !== draft;

  useEffect(() => {
    if (!due || !visible || data === undefined) return;
    autoUpdate((d) => applyCarry(d, data, date));
  }, [due, visible, data, date, autoUpdate]);

  useEffect(() => {
    if (copyDue && visible) autoUpdate(followSaveMode);
  }, [copyDue, visible, autoUpdate]);

  return { failed: due && query.isError, retry: () => void query.refetch() };
}
````

**In `frontend/src/components/builder/step-progress.tsx`, replace:**

````tsx
 * The four steps (F §4.7 "StepProgress"; S "Builder shell"): every step is a
 * link (F D9). Below `lg` a line "Step 1 of 4 · Date & readings" sits above
 * four segments; from `lg` each step shows its number, label and status. The
````

**with:**

````tsx
 * The five steps (F §4.7 "StepProgress"; S "Builder shell"; the Bulletin
 * step from printed bulletin PR 2b): every step is a link (F D9). Below `lg`
 * a line "Step 1 of 5 · Date & readings" sits above five segments (each
 * 44 px tall, about 60 px wide at 375 px); from `lg` each step shows its
 * number, label and status. The
````

**In `frontend/src/components/builder/step-progress.tsx`, replace:**

````tsx
      <ol className="grid grid-cols-4 gap-1.5 lg:gap-3">
````

**with:**

````tsx
      <ol className="grid grid-cols-5 gap-1.5 lg:gap-3">
````

**In `frontend/src/lib/draft/steps.ts`, replace:**

````ts
 * The four builder steps (F §4.7; S "steps.ts"). Every step has its own
 * route and is always reachable (F D9).
````

**with:**

````ts
 * The five builder steps (F §4.7; S "steps.ts"). Every step has its own
 * route and is always reachable (F D9). Printed bulletin PR 2b adds the
 * optional Bulletin step between Liturgy and Review & send.
````

**In `frontend/src/lib/draft/steps.ts`, replace:**

````ts
 * statuses "Saved" and "Unsaved changes" (`reviewStatus`).
````

**with:**

````ts
 * statuses "Saved" and "Unsaved changes" (`reviewStatus`). "bulletin" ships
 * with its step (PR 2b): "Optional", or how many boxes from last week are
 * still to check.
````

**In `frontend/src/lib/draft/steps.ts`, replace:**

````ts
  /** 1-4, as shown in "Step 1 of 4". */
````

**with:**

````ts
  /** 1-5, as shown in "Step 1 of 5". */
````

**In `frontend/src/lib/draft/steps.ts`, replace:**

````ts
  { id: "liturgy", number: 3, label: "Liturgy", short: "Liturgy", href: "/builder/liturgy", previous: "hymns", next: "review" },
  { id: "review", number: 4, label: "Review & send", short: "Review", href: "/builder/review", previous: "liturgy", next: null },
];

export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns", "liturgy", "review"]);
````

**with:**

````ts
  { id: "liturgy", number: 3, label: "Liturgy", short: "Liturgy", href: "/builder/liturgy", previous: "hymns", next: "bulletin" },
  { id: "bulletin", number: 4, label: "Bulletin", short: "Bulletin", href: "/builder/bulletin", previous: "liturgy", next: "review" },
  { id: "review", number: 5, label: "Review & send", short: "Review", href: "/builder/review", previous: "bulletin", next: null },
];

export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns", "liturgy", "bulletin", "review"]);
````

**In `frontend/src/app/(signed-in)/(church)/builder/page.tsx`, replace:**

````tsx

/** `/builder` opens the step the draft was last on (F §4.7 "Navigation"). */
````

**with:**

````tsx
import { STEPS } from "@/lib/draft/steps";

/**
 * `/builder` opens the step the draft was last on (F §4.7 "Navigation"), or
 * Review & send when that step is not in the bar: a draft from a newer
 * release after a rollback (printed bulletin PR 2b-2 plan, Step R).
 */
````

**In `frontend/src/app/(signed-in)/(church)/builder/page.tsx`, replace:**

````tsx
  const target = `/builder/${draft.last_step}`;
````

**with:**

````tsx
  const target = STEPS.find((step) => step.id === draft.last_step)?.href ?? "/builder/review";
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````tsx
 * Step 4, Review & send (slice 5a spec, UX "Review step"; owner answers 1 and
````

**with:**

````tsx
 * Step 5, Review & send (slice 5a spec, UX "Review step"; owner answers 1 and
````

- [ ] **Step 4: See them pass (three runs), the suite, types and lint**

Run: the Step 2 command three times, then the suite, typecheck and lint.
**Expected:** three times `      Tests  55 passed (55)`; ` Test Files  87 passed (87)`, `      Tests  697 passed (697)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add 'frontend/src/app/(signed-in)/(church)/builder/bulletin/page.tsx' 'frontend/src/app/(signed-in)/(church)/builder/page.tsx' frontend/src/components/builder/bulletin/bulletin-step.tsx frontend/src/components/builder/bulletin/bulletin-step.test.tsx frontend/src/components/builder/bulletin/use-bulletin-carry.ts frontend/src/lib/draft/steps.ts frontend/src/components/builder/step-progress.tsx frontend/src/components/builder/review/review-send-step.tsx frontend/src/test/fixtures/index.ts frontend/src/lib/draft/status.test.ts frontend/src/components/builder/builder-shell.test.tsx frontend/src/components/builder/review/review-send-step.test.tsx
git commit -q -m "Printed bulletin PR 2b-2: the Bulletin step" -m "A fifth, optional step between Liturgy and Review & send: the prelude
and postlude, who leads (the settings' people, changeable for this
week, and a part's leader behind Change who leads a part, each with its
usual leader), the announcements, and per reading a box for pasted
text. Last week's music and announcements carry into a new draft, each
box marked From last week until it is edited or kept; a failed lookup
stays on the step with Try again; a saved service on another date is
marked the same way. The step bar has five steps and says Optional or
how many boxes are still to check." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1425 passed, 17 skipped`; frontend `697 passed` in 87 files.

### Task 9: The Printed bulletin card: the week's fields (planning answers 3, 5, 6; clarifications 7, 9, 16)

**Files:**
- Modify: `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, `frontend/src/components/builder/review/printed-card.tsx`

The card runs the carry, so the two test files that render Review without the builder shell's routes (`review-send-step`, `liturgy-step`) answer `GET /services/previous-bulletin` (`builder-shell` has it since T8).

- [ ] **Step 1: Write the failing test (and the routes)**

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````tsx
  me,
````

**with:**

````tsx
  me,
  previousBulletin,
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````tsx
    "GET /church/bulletin-settings": bulletinSettings(),
````

**with:**

````tsx
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
  savedService,
  SERVICE_ID,
````

**with:**

````tsx
  previousBulletin,
  savedService,
  SERVICE_ID,
  serviceBulletin,
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
import { PLACEHOLDERS_NOTE, PRINTED_SUMMARY, SETTINGS_NOTE } from "./printed-card";
````

**with:**

````tsx
import { PRINTED_SUMMARY, SETTINGS_NOTE, WEEKLY_NOTE } from "./printed-card";
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    "GET /church/bulletin-settings": bulletinSettings(),
````

**with:**

````tsx
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(within(card).getByText(PLACEHOLDERS_NOTE)).toBeInTheDocument();
````

**with:**

````tsx
    expect(within(card).getByText(WEEKLY_NOTE)).toBeInTheDocument();
    expect(within(card).queryByText(/\[placeholders\]/)).toBeNull(); // PR 1's note is gone (PR 2b)
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
        "Not filled in: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist.",
````

**with:**

````tsx
        "Not filled in: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist, prelude, postlude, announcements.",
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(await within(card).findByText("Not filled in: organist.")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download printed bulletin" })).toBeEnabled();
    filled.unmount();
````

**with:**

````tsx
    expect(await within(card).findByText("Not filled in: organist, prelude, postlude, announcements.")).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download printed bulletin" })).toBeEnabled();
    filled.unmount();
  });

  it("carries last week's music and announcements in, lists what to check, and prints them (printed bulletin PR 2b)", async () => {
    const lastWeek = previousBulletin({
      service_id: "s-last",
      service_date_iso: "2026-09-27",
      bulletin: serviceBulletin({
        prelude: { title: "Morning Voluntary", composer: "Pat Example" },
        announcements: { ...serviceBulletin().announcements, ushers: "Sam Sample", coffee_hour: "The Example family" },
      }),
    });
    const { api, user } = renderReview(testDraft(), {
      "GET /church/bulletin-settings": filledBulletinSettings(),
      "GET /services/previous-bulletin": lastWeek,
      "POST /documents/printed": pdf(),
    });
    const card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(await within(card).findByText("From last week, not checked yet: prelude, ushers and counters, coffee hour.")).toBeInTheDocument();
    expect(within(card).getByText("Not filled in: postlude.")).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Download printed bulletin" }));
    await waitFor(() => expect(printedRequests(api)).toHaveLength(1));
    expect(printedRequests(api)[0].body).toMatchObject({
      service: { bulletin: { prelude: { title: "Morning Voluntary" }, announcements: { coffee_hour: "The Example family" } } },
    });
    const progress = screen.getByRole("navigation", { name: "Steps" });
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Bulletin 3 to check");
````

- [ ] **Step 2: See it fail**

Run: `(cd frontend && npx vitest run src/components/builder/review/review-send-step.test.tsx src/components/builder/builder-shell.test.tsx src/components/builder/liturgy/liturgy-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected:**
```
   × Review & send: the printed bulletin (printed bulletin PR 1) > shows the card after the Word documents with what it prints and both files <t>ms
   × Review & send: the printed bulletin (printed bulletin PR 1) > lists the bulletin settings still blank and links to them (printed bulletin PR 2a) <t>ms
   × Review & send: the printed bulletin (printed bulletin PR 1) > carries last week's music and announcements in, lists what to check, and prints them (printed bulletin PR 2b) <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 3 ⎯⎯⎯⎯⎯⎯⎯
      Tests  3 failed | 75 passed (78)
```

- [ ] **Step 3: The card's lines and the carry**

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { buttonVariants } from "@/components/ui/button";
import { notFilledIn, notFilledInLine } from "@/lib/bulletin-settings";
````

**with:**

````tsx
import { useBulletinCarry } from "@/components/builder/bulletin/use-bulletin-carry";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { buttonVariants } from "@/components/ui/button";
import { notFilledInLine } from "@/lib/bulletin-settings";
import { notChecked, notCheckedLine, printedNotFilledIn } from "@/lib/draft/bulletin";
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
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
````

**with:**

````tsx
export const WEEKLY_NOTE = "The music, the announcements and this week's changes to who leads come from the Bulletin step.";

/**
 * What the printed bulletin leaves out (PR 2 planning answer 3: a blank field
 * prints nothing, so the card says which are blank), above the downloads so
 * it is read before printing: the blank standing settings (with this week's
 * people), then the prelude, the postlude and the announcements (PR 2b). The
 * settings' part is left out while they load or if they fail: the downloads
 * never wait for them. Then the boxes still holding last week's text,
 * unchecked.
 */
function NotFilledInLines() {
  const { draft } = useDraft();
  const settings = useBulletinSettings();
  const missing = printedNotFilledIn(settings.data, draft);
  const unchecked = notChecked(draft);
  return (
    <>
      {missing.length > 0 ? <p className="text-sm">{notFilledInLine(missing)}</p> : null}
      {unchecked.length > 0 ? <p className="text-sm">{notCheckedLine(unchecked)}</p> : null}
    </>
  );
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
 * documents card. PR 1 prints what the app does not know yet as
 * [placeholders], and the card says so. PR 2a: the standing details come
 * from the church's bulletin settings; the card lists the blank ones above
 * the downloads and links to the Bulletin settings page below them (any
 * member; admins edit there).
````

**with:**

````tsx
 * documents card. PR 2a: the standing details come
 * from the church's bulletin settings; the card lists the blank ones above
 * the downloads and links to the Bulletin settings page below them (any
 * member; admins edit there). PR 2b: the week's own fields come from the
 * Bulletin step and replace PR 1's last [placeholders] (the cover picture's
 * stays until PR 3); the card lists the blank ones and the boxes from last
 * week not checked yet, and carries last week's in here too
 * (`useBulletinCarry`), so a bulletin printed without opening the Bulletin
 * step has them.
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
  const { draft } = useDraft();
  const [downloaded, setDownloaded] = useState(false);
````

**with:**

````tsx
  const { draft } = useDraft();
  useBulletinCarry();
  const [downloaded, setDownloaded] = useState(false);
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
        <p className="text-sm text-muted-foreground">{PLACEHOLDERS_NOTE}</p>
        <p className="text-sm text-muted-foreground">{SETTINGS_NOTE}</p>
        <NotFilledInLine />
````

**with:**

````tsx
        <p className="text-sm text-muted-foreground">{SETTINGS_NOTE}</p>
        <p className="text-sm text-muted-foreground">{WEEKLY_NOTE}</p>
        <NotFilledInLines />
````

- [ ] **Step 4: See them pass (three runs), the suite, types and lint**

Run: the Step 2 command three times, then the suite, typecheck and lint.
**Expected:** three times `      Tests  78 passed (78)`; ` Test Files  87 passed (87)`, `      Tests  698 passed (698)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/builder/review/printed-card.tsx frontend/src/components/builder/review/review-send-step.test.tsx frontend/src/components/builder/liturgy/liturgy-step.test.tsx
git commit -q -m "Printed bulletin PR 2b-2: the Printed bulletin card lists the week's fields" -m "The card no longer says the music and the announcements print as
placeholders: it says they come from the Bulletin step, adds the
prelude, the postlude and the announcements to Not filled in (with
this week's people), lists the boxes from last week not yet checked,
and carries last week's in, so a bulletin printed from Review without
opening the Bulletin step has them." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1425 passed, 17 skipped`; frontend `698 passed` in 87 files.

### Task 10: Docs: the manual check items for PR 2b-2 (planning answers 3-7; clarification 17)

**Files:**
- Modify: `docs/manual-verification.md`

- [ ] **Step 1: Amend PR 1's item 2, append items 19-27**

**In `docs/manual-verification.md`, replace:**

````markdown
- [ ] (owner, after PR 1) **2.** In that PDF the readings are printed in full in the translation chosen on step 1, followed by "Scripture readings are from the …"; hymns read like `*HYMN: #409 "God Is Here!"`; the people lines are bold; the music and announcements show as [placeholders] (after PR 2a the church's details and the names come from **Bulletin settings**; a blank one prints nothing).
````

**with:**

````markdown
- [ ] (owner, after PR 1) **2.** In that PDF the readings are printed in full in the translation chosen on step 1, followed by "Scripture readings are from the …"; hymns read like `*HYMN: #409 "God Is Here!"`; the people lines are bold (after PR 2a the church's details and the names come from **Bulletin settings**, and after PR 2b-2 the music and the announcements from the **Bulletin** step; a blank one prints nothing; before PR 2b-2 they print as [placeholders]).
````

**In `docs/manual-verification.md`, replace:**

````markdown
- [ ] (owner, after PR 2b-1) **18.** The builder works as before (four steps): open a saved service from **Services**, tap **Save changes**, and download the printed bulletin from **4 Review & send**: the save works, and the PDF still prints the music and the announcements as [placeholders], as the Printed bulletin card says.
````

**with:**

````markdown
- [ ] (owner, after PR 2b-1) **18.** The builder works as before (four steps): open a saved service from **Services**, tap **Save changes**, and download the printed bulletin from **4 Review & send**: the save works, and the PDF still prints the music and the announcements as [placeholders], as the Printed bulletin card says.
- [ ] (owner, after PR 2b-2) **19.** The step bar shows five steps and fits at 375 px with no sideways scroll; **4 Bulletin** says "Optional". On **Bulletin**: **Music**, **Who leads**, **Announcements** and **Reading text**, every field and button easy to tap (44 px).
- [ ] (owner, after PR 2b-2) **20.** Fill in the prelude and postlude (title and composer), the ushers and counters, the coffee hour and one line of activities, leave the rest blank, and download the printed bulletin from **5 Review & send**: the prelude and postlude print with their composers and the organist's name; the announcements page shows only what was filled in (no heading or line for a blank one); the Printed bulletin card no longer says anything prints as [placeholders] and lists the blank ones ("Not filled in: …"). The Word version shows the same.
- [ ] (owner, after PR 2b-2) **21.** Under **Who leads**, change one person for this week ("Changed for this week.") and, behind **Change who leads a part**, the Sermon's leader (each part says "Usually" and the settings' name); download again: page 1's header and the Sermon follow the change; **Bulletin settings** still has the usual names.
- [ ] (owner, after PR 2b-2) **22.** Save the service. Start a **New service**, choose the Sunday one week after the saved service's date on step 1, and open **4 Bulletin**: the saved service's music and announcements are there, each with "From last week. Check before printing."; **Who leads** shows the usual names and the reading boxes are empty. On **5 Review & send** the card says "From last week, not checked yet: …". Change one box and tap **Keep as is** on another: their notes go, and the card's list shortens. Save it and open it again from **Services**: the boxes not yet checked still say "From last week".
- [ ] **23.** Paste one reading's text under **Reading text** and download: the PDF prints the pasted text under that reading, the credit line names only the other reading ("The First Reading is from the …", or the New Testament Reading), and the download fetches only the other reading. Paste both: no credit line.
- [ ] **24.** Clear every announcement and download: there is no announcements page in the PDF or the Word version (the card lists "announcements" as not filled in).
- [ ] **25.** Open a saved service from **Services**: its bulletin fields are as saved, only the boxes it was saved with unchecked say "From last week", nothing from another week comes in, and Review says "Saved".
- [ ] **26.** Open a saved service, change its date on step 1 to another Sunday and open **4 Bulletin** ("Save as new service"): its music and announcements each say "From last week. Check before printing.", **Who leads** shows the usual names, no part has a leader of its own and the reading boxes are empty. Change the date back: the names, part leaders and texts come back.
- [ ] **27.** A draft started before PR 2b-2 opens with everything it had, and its Bulletin step fills with last week's music and announcements once last week's service has them (a service saved before PR 2b-2 has none).
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '^## ' docs/manual-verification.md | tail -1` then `git diff -U0 docs/manual-verification.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected:** `89 passed in <t>s`; `282:## Printed bulletin`; `0`; ` 1 file changed, 10 insertions(+), 1 deletion(-)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md
git commit -q -m "Docs: printed bulletin PR 2b-2 manual checks" -m "docs/manual-verification.md gains items 19-27 under \"### Printed
bulletin PR 2b: the Bulletin step\": the phone check after PR 2b-2 (the
five steps, the music and announcements printed, who leads this week,
carry forward with its check on the Sunday after a saved one) and the
agent's checks (pasted text and its credit line, no announcements page,
an opened service with its marks, Save as new service, an old draft).
PR 1's item 2 says where the music and announcements come from now." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1425 passed, 17 skipped`; frontend `698 passed` in 87 files.

- [ ] **Step 4 (controller): Review the batch (T7-T10) and backup push**

One review of PR 2b-2: the draft's 2 → 3 migration keeps everything and a "Saved" draft stays Saved; carry forward never touches a saved service, a box edited or kept, or a draft whose save outcome is unknown, runs only through `autoUpdate`, and a failed lookup stays reported; Save as new service marks the boxes and sets this week's people, leaders and texts aside (back on the saved date); the marks are saved as `unchecked` and come back on open; the 409 check reads the bulletin as the server stores it; the step's fields are 44 px and labelled, `aria-controls` names only a rendered panel, "Usually" names the settings' leader and a settings failure says so; the copy is clarification 16's. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

### Task 11: Verification and the draft PR 2b-2 (owner's yes before the PR is opened and before it is marked ready)

`<N2>` is PR 2b-2's number, `<N1>` PR 2b-1's. As T5: every `gh` command uses `-R bbrown62450/church`; never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): PR 2b-1 is live, and the branch is up to date with `origin/main`**

```bash
git status --short
git fetch origin
curl -s https://church-production-74ca.up.railway.app/openapi.json | grep -c '"/services/previous-bulletin"'
git ls-tree --name-only origin/main backend/migrations/versions/ | grep -c '/0'
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
git log --format=%s -1 origin/main -- docs/ops-runbook.md
```

**Expected:** nothing (or `?? .claude/`); `1` (the live API has PR 2b-1's route: without it, stop, PR 2b-2 must not merge); `6` (`0006` on `main`); `0`; `0`; the subject of the commit that last changed the runbook on `main` (not the 2b-1 record, which rides along here). If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 11)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, Postgres, the frontend three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/builder/bulletin")
```

**Expected:** `1425 passed, 17 skipped in <t>s`; three times ` Test Files  87 passed (87)` and `      Tests  698 passed (698)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s`, a route line `○ /builder/bulletin`, and no `Error` (a font `Failed to fetch` only: say so and rely on CI). With a local, throwaway Postgres also `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `17 passed, 1425 deselected`.

- [ ] **Step 3 (agent): The gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend frontend/src/lib/api .github frontend/package.json frontend/package-lock.json requirements-dev.txt app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status`; `raw html grep exit 1`; exactly these paths (and `M docs/superpowers/plans/2026-10-03-printed-bulletin-2b.md` if a plan commit came after the 2b-1 merge):
```
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	frontend/src/app/(signed-in)/(church)/builder/bulletin/page.tsx
M	frontend/src/app/(signed-in)/(church)/builder/page.tsx
M	frontend/src/components/builder/builder-shell.test.tsx
A	frontend/src/components/builder/bulletin/bulletin-step.test.tsx
A	frontend/src/components/builder/bulletin/bulletin-step.tsx
A	frontend/src/components/builder/bulletin/use-bulletin-carry.ts
M	frontend/src/components/builder/liturgy/liturgy-step.test.tsx
M	frontend/src/components/builder/review/printed-card.tsx
M	frontend/src/components/builder/review/review-send-step.test.tsx
M	frontend/src/components/builder/review/review-send-step.tsx
M	frontend/src/components/builder/step-progress.tsx
M	frontend/src/lib/documents.test.ts
M	frontend/src/lib/documents.ts
A	frontend/src/lib/draft/bulletin.test.ts
A	frontend/src/lib/draft/bulletin.ts
M	frontend/src/lib/draft/mapping.test.ts
M	frontend/src/lib/draft/mapping.ts
M	frontend/src/lib/draft/migrate.test.ts
M	frontend/src/lib/draft/migrate.ts
M	frontend/src/lib/draft/schema.test.ts
M	frontend/src/lib/draft/schema.ts
M	frontend/src/lib/draft/status.test.ts
M	frontend/src/lib/draft/status.ts
M	frontend/src/lib/draft/steps.ts
M	frontend/src/lib/draft/store.test.ts
M	frontend/src/lib/queries/keys.test.ts
M	frontend/src/lib/queries/keys.ts
M	frontend/src/lib/queries/services.ts
M	frontend/src/test/fixtures/index.ts
```
`0` (no server, API, workflow or package change: PR 2b-2 is the frontend and the docs); the subjects oldest first: `Runbook: printed bulletin PR 2b-1 record (backup, counts, SQL preview, merge, migration 0006)`, any later plan commit, then T7-T10's four subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR 2b-2**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> The Bulletin step (printed bulletin PR 2b-2) is verified on this machine: frontend 698 tests in 87 files (675 in 85 before), three runs in a row; backend unchanged at 1425 passed, 17 skipped; typecheck, lint and the production build are clean. It needs no database change (PR 2b-1 already made it, and it is live). It adds a fifth step, "4 Bulletin", with the prelude and postlude, who leads this week, the announcements and a box to paste a reading's text; a new service starts from last week's music and announcements, each marked "From last week. Check before printing." (the marks are saved with the service); "Save as new service" marks them the same way and starts this week's names empty; the printed bulletin prints them all and leaves out anything blank (and the announcements page when there are none). May I open the pull request as a **draft** titled "Printed bulletin PR 2b-2: the Bulletin step", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/printed2b2-pr-body.md" <<'BODY'
Printed bulletin PR 2b-2: the Bulletin step (PR 2 planning answers of 2026-10-02), on the server of PR 2b-1 (#<N1>, live since <date>). Spec: docs/superpowers/specs/2026-10-02-printed-bulletin-design.md. Plan: docs/superpowers/plans/2026-10-03-printed-bulletin-2b.md (Tasks 7-12). No migration, no server change, no new package or variable.

- The draft v3 (a v2 draft migrates with an empty bulletin and stays Saved).
- The Bulletin step (/builder/bulletin; five steps in the bar): the music, who leads this week (each part with its usual leader), the announcements, pasted reading text. A failed settings or carry lookup says so with Try again.
- Carry forward of last week's music and announcements into every box not yet touched, never while a save's outcome is unknown, with "From last week. Check before printing." and Keep as is; the marks are saved with the service. Save as new service marks the boxes the same way and starts this week's people, part leaders and pasted texts empty.
- The Printed bulletin card's lines; the 409 "is it my own save" check reads the bulletin as the server stores it.
- /builder opens Review for a step no longer in the bar (so a rollback keeps every draft).
- docs/manual-verification.md: items 19-27. docs/ops-runbook.md: the PR 2b-1 record (rides along).

Later: PR 3 (the cover picture; backend first, as 2b), 6a (Settings).

Tests: frontend 675 → 698 in 85 → 87 files; backend 1425 passed, 17 skipped (unchanged)

After merge (Task 12): a guided phone check, then a "Printed bulletin PR 2b-2 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Printed bulletin PR 2b-2: the Bulletin step" \
  --body-file "<scratch>/printed2b2-pr-body.md"
gh pr checks <N2> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass`; CI's numbers: backend `1425 passed, 17 skipped`, backend-postgres `17 passed, 1425 deselected`, frontend `698 passed` in 87 files. Then send: "PR #<N2> is green: 698 frontend tests in 87 files; the backend and its Postgres job unchanged and passing; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N2> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `bulletin.test.ts`, `schema.test.ts`, `migrate.test.ts`, `store.test.ts`, `mapping.test.ts`, `documents.test.ts`, `keys.test.ts`, `status.test.ts` | T7 (`status.test.ts`'s steps test: T8) |
| `bulletin-step.test.tsx`, `builder-shell.test.tsx` | T8 |
| `review-send-step.test.tsx`, `liturgy-step.test.tsx` | T9 (the step bar's indexes: T8) |
| `test_slice1_docs.py`, `test_docs.py` | T10 |
| a backend test | PR 2b-1's task (T1-T3): stop and tell the owner first, since that code is live |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, printed bulletin PR 2b-2 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1425 passed, 17 skipped`; frontend `698 passed` in 87 files.

### Task 12: PR 2b-2: the merge, the phone check, the record (OWNER + agent)

The owner's steps go **one at a time**. The agent writes each result into `<scratch>/printed2b2-t12-results.md` (not committed), never a token, an email address, a phone number, a street address, a church id, a database URL or a name from the prayers and concerns.

**Files:** Modify (the records PR, Step 9): `docs/ops-runbook.md`: insert `### Printed bulletin PR 2b-2 record` right before `## Backups` (after `### Printed bulletin PR 2b-1 record`).

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N2> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N2> (the Bulletin step) is ready and green, and the server it needs has been live since PR 2b-1. May I merge it with a merge commit? Only the website changes (no database step); I will tell you when it is live, then ask for a short phone check, one step at a time." On a clear yes (not replayed):

```bash
gh pr merge <N2> --merge -R bbrown62450/church
gh pr view <N2> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N2> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both.

- [ ] **Step 2 (agent): The deploy**

About three minutes after the merge (not replayed): `curl -s https://church-production-74ca.up.railway.app/health/ready; echo` → `{"ok":true,"db":"ok"}` (Railway redeploys the same server code; no migration runs) and `curl -s -o /dev/null -w '%{http_code}\n' https://worship-service-builder.vercel.app/builder/bulletin` → `200` (or a redirect code to the sign-in, `307`: the route exists). Wait for Vercel's production deploy of the merge commit before the phone check.

- [ ] **Step 3 (OWNER, then agent): Phone, step 1 of 4: the step (item 19)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. Open the Service Builder. Does the step bar at the top show five steps, with no sideways scrolling? Tap step 4, **Bulletin**: does it say "Optional" in the step list, and show **Music**, **Who leads**, **Announcements** and **Reading text**? Are the fields and buttons easy to tap?

- [ ] **Step 4 (OWNER, then agent): Phone, step 2 of 4: the music and announcements printed (item 20)**

> On **Bulletin**, fill in this Sunday's prelude and postlude (title and composer) and the announcements you have (leave any you don't use blank). Then go to **5 Review & send** and tap **Download printed bulletin**. Do the prelude and postlude print with their composers and the organist's name? Does the announcements page show what you filled in, and nothing for the blank ones? Does the Printed bulletin card still say anything about [placeholders]? Then tap **Download Word version**: does it show the same?

Record the answers (never the announcements' text).

- [ ] **Step 5 (OWNER, then agent): Phone, step 3 of 4: who leads this week (item 21)**

> Back on **Bulletin**, under **Who leads**, change one person just for this week (for example a guest preacher as worship leader; "Changed for this week." shows), and tap **Change who leads a part**: does each part say "Usually" and your usual name? Type a name for the **Sermon**. Download the printed bulletin again: do page 1's header and the Sermon line show the change? Then open **Bulletin settings**: are your usual names unchanged? (Tap **Undo the change** afterwards if this was only a test.)

- [ ] **Step 6 (OWNER, then agent): Phone, step 4 of 4: carry forward (item 22)**

> On **5 Review & send**, tap **Save to archive**. Then open the menu (⋮) → **New service**, and on step 1 choose the Sunday one week after the service you just saved. Now go to **4 Bulletin**: are that service's music and announcements there, each with "From last week. Check before printing."? Are **Who leads** back to the usual names and the reading boxes empty? Change one of the boxes, and tap **Keep as is** on another: do their notes go away? On **5 Review & send**, does the card list "From last week, not checked yet: …" for the rest? Save it, then open it again from **Services**: do the boxes you did not check still say "From last week"? You can then delete these test services from **Services** if you don't want them.

(New service starts on the coming Sunday, the same Sunday as the service just saved on any day but Sunday; carry forward reads services dated before the draft's date, so the check needs the Sunday after.)

- [ ] **Step 7 (agent): The agent's own checks (items 23-27), the results**

On the production URL, in a test church the agent may change (one of the two slice 1 test churches the owner kept, never the owner's own church), signed in as its owner if the session has a test account, else skipped and recorded as "not run": item 23 (paste one reading's text; the PDF prints it, the credit line names the other reading; paste both: no line), item 24 (clear every announcement; no announcements page), item 25 (open a saved service; its fields as saved, only its unchecked boxes marked, "Saved"), item 26 (Save as new service: marks, usual names, empty texts; the date back: the names come back), item 27 (an old draft). Then write each step's result, with the date, into `<scratch>/printed2b2-t12-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 8 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it: `### Printed bulletin PR 2b-1 record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Printed bulletin PR 2b-2 record

Printed bulletin PR 2b-2 (the Bulletin step: the prelude and postlude,
who leads this week, the announcements and pasted reading text, carried
forward from last week with a check that is saved with the service,
printed in the PDF and the Word version, a blank one printing nothing)
merged as PR #<N2>, the second of the two PRs of printed bulletin PR 2b,
on the server of PR 2b-1 (#<N1>). No database change. The owner's check
covered the "(owner, after PR 2b-2)" items of `docs/manual-verification.md`
→ "Printed bulletin". No token, email address, phone number, street
address, church id, database URL or name from the prayers and concerns is
recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N2> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`; `/builder/bulletin` answers. | <date> |
| 1. The step (phone: <phone and browser>) | <Five steps, no sideways scroll; Bulletin "Optional" with its four groups; easy to tap. / …> | <date> |
| 2. Music and announcements printed | <The prelude and postlude with composers and the organist; only the filled announcements; no [placeholders] note; the Word version the same. / Differences: …> | <date> |
| 3. Who leads this week | <Each part showed its usual leader; the header and the Sermon followed the change; the settings unchanged. / …> | <date> |
| 4. Carry forward | <On the Sunday after, the saved service's music and announcements came in, each marked; who leads and the reading boxes empty; an edit and Keep as is cleared their notes; the card listed the rest; reopened from Services, the unchecked boxes were still marked. / …> | <date> |
| Agent checks | <Items 23-27 in a test church: <results>. / Not run: <why>.> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: printed bulletin PR 3 (the cover picture, backend first), 6a (Settings). Still open from PR 1: the print test at the church | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye (no address, phone number or name). Then (not replayed):

```bash
sed -n '/^### Printed bulletin PR 2b-2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Printed bulletin PR 2b-2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|\([0-9]{3}\)'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: printed bulletin PR 2b-2 record (merge, phone check)" -m "Records printed bulletin PR 2b-2 (PR #<N2>): the merge and the deploy
of the Bulletin step, the owner's four-step phone check and the agent's
checks. No token, email, phone number, address, church id, database URL
or name from the prayers and concerns is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 9 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The printed bulletin PR 2b-2 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: printed bulletin PR 2b-2 record" \
  --body "Records printed bulletin PR 2b-2 (PR #<N2>) in docs/ops-runbook.md → Printed bulletin PR 2b-2 record: the merge, the deploy and the owner's phone check. No token, email, phone number, address, church id, database URL or name from the prayers is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Printed bulletin PR 2b is live and recorded; <n> follow-ups. Next: the PR 3 plan (the cover picture), backend first in the same way."

- [ ] **Step R (only if a release must come out): Revert PR 2b-2 first, keeping the draft v3; PR 2b-1 only after it**

On the owner's yes for each outward command (README "Reverting PR 2b-2 or PR 2b-1"; clarification 20). **PR 2b-2** (the step): a branch `claude/revert-printed-2b-2` from `origin/main`; `git revert -m 1 --no-commit <2b-2 merge sha>`; then put back the draft's reader from the merge commit, so no member's draft is lost: `git checkout <2b-2 merge sha> -- frontend/src/lib/draft/schema.ts frontend/src/lib/draft/schema.test.ts frontend/src/lib/draft/migrate.ts frontend/src/lib/draft/migrate.test.ts frontend/src/lib/draft/store.test.ts 'frontend/src/app/(signed-in)/(church)/builder/page.tsx'` and `sed -i 's/^      version: 2,$/      version: 3,/' frontend/src/lib/draft/mapping.test.ts` (its one pinned version); a commit "Revert printed bulletin PR 2b-2 (PR #<N2>), keeping the draft v3" with the trailer; the frontend suite (`676 passed` in 85: the baseline and the v2 → v3 migration test), typecheck and lint; a PR, CI, and the merge on the owner's yes; record it in the record. The reverted pages read every v3 draft as it is (its bulletin kept, unused, for when the step returns), `/builder` opens Review for a draft left on the Bulletin step, and they send no `bulletin`, which the 2b-1 server takes as before (a PUT keeps the saved one; the printed bulletin prints PR 1's placeholders). Checked while planning: this revert, run on the planning worktree, typechecks, lints and passes `676` tests, and a v3 draft on the Bulletin step opens Review with its fields intact. **PR 2b-1**, only after the 2b-2 revert is live: as before, `git revert -m 1 --no-commit <2b-1 merge sha>`, then `git checkout <2b-1 merge sha> -- backend/migrations/versions/0006_services_bulletin.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py`; both suites (`1399 passed, 17 skipped`: the baseline plus T1's four and its Postgres one; the frontend as it then is). Never `alembic downgrade` production for this: the database stays at `0006_services_bulletin`, which the older code ignores, and the weekly fields saved meanwhile stay in the column, unread, until 2b returns.

Expected counts after this task: backend `1425 passed, 17 skipped` on `main`; frontend `698 passed` in 87 files. The records PR adds no test.

---
## Build notes

**How this plan was written (2026-10-03).** Each task's code was built and run in a throwaway worktree of the branch head (`eadd365`: `9c731e1` and the plan's first commit), with the repo's `.venv` (a symlink), a hard-linked copy of `frontend/node_modules` (`cp -al`; Turbopack's production build refuses a `node_modules` symlink that points outside the project) and a local, throwaway Postgres 16 (`initdb` under `/var/lib/postgresql`, port 5433; CI uses 17), one commit for each task's tests and one for its code. The directives were generated from those commits by a script (a new file as **Create**, an addition at the end of a file as **Append**, every other change as **In … replace** with the context grown until the block occurs once in the file as it stands at that point), so the plan's blocks are the built code. While building:
- **`JSON` stores `None` as JSON `null`.** The first Postgres run of the owner's after-deploy query counted three services `WITH bulletin IS NOT NULL` where one had a bulletin: SQLAlchemy's `JSON` type writes a Python `None` as the JSON value `null` unless `none_as_null=True`. The model's column is `JSON(none_as_null=True)` (no DDL change: `alembic check` stays clean), so a service saved without a bulletin is SQL NULL, as the README's query assumes.
- **5a-2's 0005 test upgraded to `head`;** with 0006 it saw the new column too. It now upgrades to `0005_services_extras` (T1's tests), and 5a-2's Postgres test of the 0005 queries expects the head's version.
- **`IsoDate` needs `Annotated[IsoDate, Query()]`.** Written as `before: IsoDate = Query(...)`, FastAPI accepted `2026-10-04T00:00:00` (the shape check did not run); in the `Annotated` form, as `/lectionary/readings` has it, it is the 422 the T3 test expects.
- **"Edited" is recorded, not compared.** The first carry rule ("every box blank or still carried") treated a carried box the user cleared as untouched, so a date change would have carried it back in; T7's test of a cleared box caught it. `bulletin.edited` records each box edited or kept (clarification 7; a box at a time since the plan review).
- **The fingerprint leaves an empty bulletin out.** With the bulletin always in `draftToServicePayload`, every draft "Saved" before 2b would have turned "Unsaved changes" after the v3 migration; T7's migration test pins that it stays "Saved".
- **The regenerated types need the fixture in the same commit.** `ServiceOut.bulletin` is required, so T3 adds `serviceBulletin()` to `savedService()` and the type names to `types.ts`; without it T3's commit would leave typecheck failing until T7.
- **A sample booklet** (T5 Step 2's snippet) rendered to images: side 1 the cover and page 1 (the week's worship leader in the header, the prelude with the organist and the composer, the pasted NT text, the Sermon's week leader), side 2 page 2 (the postlude, the stand note) and page 3 (the announcements, "OTHER ANNOUNCEMENTS" last). Read back as the tests do.
- **CI's alembic cycle by hand** on the local Postgres: `upgrade head`, `check` (`No new upgrade operations detected.`), `downgrade base`, `upgrade head`, `check`: all clean, before and after the `none_as_null` change.

**Plan review fixes (2026-10-03).** An adversarial review of the plan (against its built tree) found nothing critical; its five important and ten minor findings were decided by the controller and applied, the owner-visible ones as questions 3, 7, 9, 12-14, 16 and 17 below. The code was rebuilt in a second throwaway worktree of `d35a76b` (the first plan's commits cherry-picked, then changed), one commit per task's tests and code as before, and every directive regenerated from it:
- **Two PRs, backend first** (review I1; clarification 19; question 14). The tasks are now T1-T6 (PR 2b-1: the migration, `service_bulletin` and the printing, the API, the docs; the verification, the owner's steps and the merge) and T7-T12 (PR 2b-2: the draft v3, the step, the card, the docs; the verification, the merge, the phone check). To make PR 2b-1 invisible to the pages already live, a body with no bulletin prints PR 1's placeholders (`printed_bulletin.PLACEHOLDERS`; T2's `test_no_bulletin_posted_prints_pr_1_s_placeholders`; `test_api_printed.py`'s 2a test keeps its placeholder check), and T5 Step 3 and T11 Step 3 check that neither PR reaches into the other's files. The README section is now "(printed bulletin PR 2b-1)", its after-deploy count expects `with_bulletin` `0`, and "Reverting PR 2b-2 or PR 2b-1" gives the order.
- **No carry while a save's outcome is unknown** (review I2): `shouldCarry` and `followSaveMode` wait for `save_key_fingerprint` to be null (T7's "never carries … while a save's outcome is unknown").
- **The marks are saved** (review I3; question 16): `ServiceBulletin.unchecked` (a list of the nine boxes, read tolerantly, a 422 for an unknown one), sent by `bulletinPayload`, restored by `bulletinFromService`, compared by the 409 check; `carried()` leaves it empty.
- **Save as new service** (review I4; question 17): `followSaveMode`, run by `useBulletinCarry`, with `bulletin.set_aside` in the draft so changing the date back loses nothing (T7's two tests, T8's step test). `markSaved` drops the set-aside copy.
- **The owner's carry check picks the Sunday after** (review I5): T12 Step 6 and item 22 say to choose, on step 1, the Sunday one week after the saved service.
- **Minor:** `edited` is a list of boxes, so typing in one does not stop the others and a failed lookup stays on the step with Try again (M1; T7's and T8's tests); a free text's U+2028, U+2029 and U+0085 (and `\r\n`, `\r`, a vertical tab, a form feed) are newlines in `service_bulletin.read` (M2), and a pasted reading's blank lines one paragraph break, at most 10 000 characters (question 13); `savedCopyFingerprint` reads the bulletin as `read` and `_xml_safe` store it (M3; checked against the server's output for the same input); a 2b-2 rollback keeps the drafts (M4; clarification 20); items 2 and 27 (was 24) reworded and Review's comment says "Step 5" (M5, M10); "Usually {name}" is the settings' leader and a settings failure says "Bulletin settings could not be loaded." with Try again (M6); `aria-controls` only while the panel is shown (M7); the long-text measurements are in Risks (M8); the credit line names the fetched reading when the other is pasted (M9; question 9).
- **The rollback was run, not only written.** In a third worktree at the built head, T12 Step R's 2b-2 revert (the revert of T7-T10, the six files checked out again, the one `sed`) typechecked, linted and passed `676` frontend tests in 85 files; a probe test (not kept) seeded a v3 draft with `last_step` "bulletin" and a filled announcement, and `/builder` opened `/builder/review` with the draft intact.
- **The blank-line rule is the same on both sides:** `[ \t]` (not `\s`, whose meaning differs between Python and JavaScript) between the line breaks of a run.

**Replay of the finished plan (2026-10-03).** After the plan review fixes, the directives of T1-T4 and T7-T10 were applied in order (by a script that parses the plan's **Create**, **Append** and **In … replace** blocks step by step) onto a fresh detached worktree of the branch head (`9082352`: `d35a76b` and the first review-fix plan commit), with the repo's `.venv`, a hard-linked copy of `frontend/node_modules` and the local Postgres 16 (`TEST_DATABASE_URL`). Each step's commands were run as written and each task committed with its own commit block (T5, T6, T11 and T12 are verification and owner steps; their local commands were run as described below):
- All 201 directives applied (T1 8 + 5, T2 17 + 19, T3 9 + 27, T4 4, T7 27 + 40, T8 18 + 12, T9 8 + 5, T10 2); every Replace anchor occurred exactly once. After T10, `backend`, `frontend/src` and `docs` (but the plans) equaled the build worktree's (`diff -r`: empty), and `git status` was clean after every commit.
- Baselines before T1: backend `1395 passed, 16 skipped`; Postgres-marked `16 passed, 1395 deselected`; frontend `675 passed` in 85 files.
- Every "see it fail" output is quoted from this replay (times as `<t>`): T1 `15 failed, 56 passed, 4 skipped`; T2 the three collection errors, then `12 passed` for `test_api_printed.py`; T3 `12 failed, 65 passed`; T7 eight failures and four files that cannot load (`8 failed | 23 passed (31)`); T8 `3 failed | 34 passed (37)` with two files that cannot load; T9 `3 failed | 75 passed (78)`.
- Every count matched the table: backend 1399, 1413, 1425 (17 skipped from T1); Postgres-marked `17 passed, 1399 deselected`, `… 1413 …`, `… 1425 deselected` (each with the onboarding timing test's `1 warning`, as on `main`); T1's files `75 passed, 4 skipped` and the six preview lines; T2's `46 passed`; T3's `77 passed`, the OpenAPI export and `gen:api` `2 files changed, 546 insertions(+), 1 deletion(-)`, frontend still `675` in 85, typecheck 0, lint 0; T4 `89 passed`, `282:## Printed bulletin`, `4`, `0`, `2 files changed, 39 insertions(+), 5 deletions(-)`; frontend 690 in 86, 697 in 87, 698 in 87; T7's files `72 passed`, T8's `55 passed` and T9's `78 passed` three times each, no flaky run; typecheck 0 and lint 0 after every frontend task; T10 `89 passed`, `282:## Printed bulletin`, `0`, `1 file changed, 10 insertions(+), 1 deletion(-)`.
- T5 Steps 2-3 at T4's commit (PR 2b-1 as it would be opened): `1425 passed, 17 skipped`; Postgres `17 passed, 1425 deselected`; frontend `675` in 85; typecheck 0, lint 0; the production build `✓ Compiled successfully` with the four builder routes and no `/builder/bulletin`; `sample written` (two sides: "Rev. Guest, Worship Leader", the pasted NT text, "The First Reading is from the World English Bible (WEB).", the activities on two lines with no "?", "OTHER ANNOUNCEMENTS"); regenerating `openapi.json` and `schema.d.ts` changed nothing; the six preview lines; `imports grep exit 1`; the 31 paths exactly (with `M docs/ops-runbook.md`); `0` paths among the server-side untouched files and the frontend's pages, components, draft, queries and bodies; every commit has the trailer. CI's alembic cycle on the local Postgres (`upgrade head`, `check`, `downgrade base`, `upgrade head`, `check`): clean.
- T11 Steps 2-3 at T10's commit, with T4's commit standing in for `main` after the 2b-1 merge: `1425 passed, 17 skipped`; Postgres `17 passed, 1425 deselected`; frontend three times `698` in 87; typecheck 0, lint 0; the build with `○ /builder/bulletin`; the API files unchanged; `raw html grep exit 1`; the 30 paths of the list but the 2b-1 record (not written in a replay); `0` server, API, workflow or package paths; T7-T10's four subjects. No em dash in any added line outside the plans, and no new log line.
- T12 Step R's 2b-2 revert, run at the built head: typecheck 0, lint 0, `676 passed` in 85 files; a v3 draft left on the Bulletin step opens Review with its fields (a probe test, not kept).
- Not run while planning: the pushes, the PRs and CI, the backup, the owner's queries on production, the merges, Railway's and Vercel's deploys, the phone checks and the records (T6, T11 Step 1's production check, T12).

## Spec coverage

| Owner answer or S item | Task(s) and tests |
|---|---|
| Planning answer 1: 2b is the step, the weekly fields, pasted text, carry forward, the draft v3 and 0006 | T1-T4 (PR 2b-1), T7-T10 (PR 2b-2); T5 Step 3 and T11 Step 3 (the paths; nothing in the Bulletin settings, the Word copies, the packages, the workflows or Streamlit) |
| Planning answer 3: a blank field prints nothing; the card lists what is empty | T2 `test_a_blank_weekly_field_prints_nothing`, `test_with_every_announcement_blank_the_announcements_page_is_left_out`; T7 "lists the blank standing fields, this week's people as changed, then the prelude, postlude and announcements"; T9 "lists the bulletin settings still blank…", "carries last week's…" |
| Planning answer 4: the announcements with "Other announcements" | T2 `test_the_cover_and_the_back_page` (the page in order, "OTHER ANNOUNCEMENTS" last); T8 "shows the music, who leads, the announcements…" |
| Planning answer 5: carry forward with a check | T3 `test_last_week_s_bulletin_is_the_latest_service_dated_before_the_date`, `test_a_service_saved_before_2b_carries_an_empty_bulletin`, `test_last_week_s_bulletin_carries_the_music_and_the_announcements`; T7 the carry forward tests, "Save as new service" and "an edit or Keep as is clears…"; T8 "carries last week's…", "never carries into a saved service…", "marks a saved service's music and announcements…"; T9 "carries last week's music and announcements in, lists what to check, and prints them" |
| Planning answer 6: optional, never blocks | T7 "the Bulletin step's status" (never in Still to do); T8 (the bar says Optional; `builder-shell` Review's Still to do unchanged); T9 (downloads enabled) |
| Planning answer 7: who leads, this week's change, "Change who leads a part" | T2 `test_this_week_s_people_and_part_leaders_print_over_the_settings`; T3 the printed test (Rev. Guest, no liturgist, Pat Example on the Sermon); T7 the payload test; T8 "shows the three people from the bulletin settings…" (the usual leader under a guest), "says so with Try again when the bulletin settings cannot be loaded…" |
| Planning answer 8: backup, counts, preview, after-deploy check, one at a time | T1 `test_offline_sql_for_0006_is_one_column_add_under_the_timeouts`, `test_the_readme_shows_the_0006_preview_exactly`, `test_the_owner_s_read_only_queries_around_0006`; T6 Steps 1-5 |
| Answer 5 and S "Scripture text": pasted text wins over fetched | T2 `test_pasted_reading_text_prints_and_the_credit_line_names_only_fetched_text`, `test_every_line_break_in_a_free_text_is_a_newline_and_a_pasted_reading_keeps_one_blank_line`; T3 `test_the_week_s_fields_print_and_a_pasted_reading_is_neither_fetched_nor_charged`; T7 (by reference); T8 "has a box per reading…" |
| S "Data model": the draft v3, `ServiceDraft.bulletin` optional, `services.bulletin` in 0006 | T1 `test_0006_adds_the_nullable_bulletin_column_and_keeps_rows`, `test_0006_downgrade_gives_back_the_0005_services_table`, the head and drift tests; T2 `test_no_bulletin_posted_prints_pr_1_s_placeholders`; T3 `test_a_save_stores_the_week_s_bulletin_word_safe_and_never_logs_it`, `test_no_bulletin_sent_stores_none_and_a_replace_without_one_keeps_the_saved_one`, `test_the_week_s_bulletin_is_saved_and_opened_and_an_older_client_keeps_it`, the 422 cases; T7 the schema and migration tests, "opens a saved service's bulletin fields Saved…", the 409 check's reading |
| S "The Bulletin step": the fifth step, fits 375 px | T8 (`grid-cols-5`, `h-11` fields; `builder-shell` five links and footers); T12 Step 3 |
| F §4.6 (never destroy typed input; versioning) | T7 (carry only through `applyCarry`'s checks, a box at a time; `followSaveMode` sets aside and gives back; 2 → 3 keeps everything); T8 (`autoUpdate`); T12 Step R (a rollback keeps the drafts) |
| F §2.5 (logs without text) | T3 the archive and printed tests (no prayer text in a log line) |
| Layering (no FastAPI or Streamlit below the API) | T3 `test_no_streamlit_in_core.py` (`service_bulletin` added); T5 imports grep |
| OpenAPI and types regenerated | T3 Step 4; T5 Step 3, T11 Step 3; `test_openapi_contract.py` |
| Answer 10: a guided phone check after each PR | T6 Step 6 (PR 2b-1: the builder as before), T12 Steps 3-6 (PR 2b-2); `docs/manual-verification.md` "### Printed bulletin PR 2b: the Bulletin step" (T4, T10) |

S items **not** in 2b: the cover picture (`cover_image_id`, "Keep last week's picture", `bulletin_images`, migration `0007_bulletin_images`: PR 3); the Bulletin settings' move into Settings (6a).

## Follow-ups (not in 2b)

- The summary panel (the bottom sheet and the `lg` column) shows no Bulletin block; the step bar's status covers it. A block could list the music and the announcement count.
- A part cannot be set to "no one" for a single week from the step (a blank field follows the usual leader; clarification 4); Bulletin settings does it for every week.
- PR 3 adds `cover_image_id` to `ServiceBulletin` (the model refuses unknown fields) and carries it forward with the music and announcements. Its plan ships backend first, as 2b (clarification 19): the migration `0007_bulletin_images` and the API in one PR, merged and live before the page that sends `cover_image_id`.
- PR 2b-1's placeholders for a body with no bulletin (`printed_bulletin.PLACEHOLDERS`) can go once no page from before PR 2b-2 can be open (for example with PR 3).
- A failed carry lookup is reported on the Bulletin step only; Review's card prints without it and says nothing (clarification 7).

## Questions for the owner

**Owner's answer (Beau, 2026-10-03): "all recommended, yes start building".** Questions 1-17 below are accepted as written and are binding for the build.

Your answers of 2026-10-02 (the ten answers, layout B, the PR 1 plan's twelve, the eight PR 2 planning answers) and of 2026-10-03 (the PR 2a plan's fourteen) are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **A fifth step, "Bulletin", before Review & send** (clarification 2): the step bar shows five steps (they fit a phone screen; the line above them reads "Step 4 of 5 · Bulletin"), and Review & send becomes step 5. The Bulletin step's status is "Optional", or "2 to check" while boxes from last week are unchecked; it never appears in "Still to do" and never turns off a download or Save. Recommended: accept.
2. **Music** (clarification 3): a title and a composer for the prelude and the postlude, printed as on your bulletin ("PRELUDE: ‘title’", the organist's name on the right, "- composer" under it). A piece with neither title nor composer leaves the whole line out. Recommended: accept.
3. **Who leads this week** (clarification 4): the worship leader, liturgist and organist show your Bulletin settings' names; changing one here is for this week only ("Changed for this week.", with **Undo the change**), and clearing one means no one this week. Behind **Change who leads a part**, a name for any part, this week only; each part shows "Usually" and the name from your settings (not this week's change); a blank one keeps the usual leader, so setting "no one" for a single part is done in Bulletin settings. If your settings cannot be loaded, the step says "Bulletin settings could not be loaded." with **Try again** instead of showing empty names. The settings themselves never change from this step. Recommended: accept.
4. **The announcements** (clarification 5): ushers and counters, deacon of the week and coffee hour as one line each, as on your bulletin; activities, prayers and concerns, items for collection and other announcements as free text that keeps your line breaks, each under its heading; "Other announcements" prints last under "OTHER ANNOUNCEMENTS". Recommended: accept.
5. **With no announcements at all, no announcements page** (clarification 6): a blank announcement prints nothing (no heading, no line), and when every one is blank the page is left out of the PDF and the Word version (the bulletin is a page shorter; the card lists "announcements" as not filled in). The other choice is a page with only "ANNOUNCEMENTS" and the date. Recommended: leave the page out.
6. **What carries forward, and from where** (clarification 7): a new service starts from the music and the announcements of your latest saved service dated before it (the latest date, then the latest save). This week's names, the part leaders and pasted readings start empty. If the latest service was saved before this update (or with nothing filled in), nothing carries, even if an older one had announcements. Recommended: accept.
7. **When it carries, and "Keep as is"** (clarification 7): it happens when a new service (never one opened from Services) is shown on the Bulletin step or on Review & send, and never while a save's answer is still unknown; if you then change the date, it carries again from the right week into every box you have not touched; once you type in, change, clear or keep a box, last week's never goes into that box again, while the other boxes still fill. Each carried box says "From last week. Check before printing." until you change it; this plan adds a **Keep as is** button beside it so a box that is right need not be retyped (your answer 5 said "until it is edited"). If last week's cannot be loaded, the step says so with **Try again**, and the message stays until it works. Recommended: yes, add Keep as is.
8. **The Printed bulletin card** (clarification 9): "For now, the music and the announcements print as [placeholders]." goes; it says "The music, the announcements and this week's changes to who leads come from the Bulletin step."; "Not filled in: …" adds prelude, postlude and announcements (and counts this week's names); and "From last week, not checked yet: …" lists the boxes still to check, above the download buttons. Recommended: accept.
9. **Pasted reading text** (clarification 8): one box per printed reading ("First Reading: …", "New Testament Reading: …"); the text stays with that reading (pick another reading and its box is empty); it prints instead of the text the app fetches, and the app does not fetch that reading. The credit line follows what was fetched: with both readings fetched, "Scripture readings are from the …" as today; with one pasted and the other fetched, a line for the fetched one only, for example "The New Testament Reading is from the World English Bible (WEB)."; with both pasted, no line (paste the translation's own notice with the text if it asks for one). Recommended: accept.
10. **Saving** (clarification 10): the Bulletin step's fields are saved with the service and come back when you open it from Services; a change to them shows "Unsaved changes". A service saved before this update stays "Saved". Recommended: accept.
11. **Prayers and concerns are kept with the service** (clarification 15): like the rest of a saved service, any member of your church who opens it can read them; they are never written to the app's logs, and the check and the record never copy a name from them. Recommended: accept.
12. **The checks around the merges, and undoing** (clarifications 14, 20; Tasks 6 and 12): around the first PR, as for migration 0005, one at a time: I start the backup on your yes; you run one read-only counting query; I show you the six lines of SQL (one new empty column) and explain them; after the deploy, one more read-only query and a short phone check that the builder works as before. After the second PR, four short phone steps. If the Bulletin step ever has to be undone, it comes out first and alone, and everyone's unsaved draft is kept (its bulletin fields wait unused until the step returns); the new column stays (empty or holding the saved fields, harmless). Recommended: accept.
13. **The limits** (clarifications 3-5, 8): titles 200 characters, composers and names 100, ushers and coffee hour 200, deacon 100, activities, prayers and other announcements 4000 each, collection items 2000, a pasted reading 10 000 (several blank lines in a row in a pasted reading print as one paragraph break). Recommended: accept.
14. **Two pull requests, the server first** (clarification 19): the first PR (2b-1) brings the database change and teaches the server to save and print the bulletin fields; nothing you see changes, and the printed bulletin keeps its [placeholders]. Only when it is live and your checks pass do I open the second (2b-2), the Bulletin step itself. So no page ever talks to a server that does not understand it, even if a deploy is slow or fails, and you can keep using the app during both deploys. The cover picture (PR 3) will be done the same way, server first. The other choice is one PR, with a few minutes (longer if a deploy fails) in which a save or download can answer "The request was not valid.". Recommended: two PRs.
15. **The Word copies stay as they are** (clarification 18): the bulletin copy and the pastor's copy (the working files) do not get the music or the announcements; the printed bulletin's Word version has them. Recommended: accept.
16. **"From last week" notes are saved with the service** (clarification 7): if you save a service before checking every carried box, the notes stay with it: opening it later from Services, on any device (the secretary's computer, say), still shows "From last week. Check before printing." on those boxes, and the card still lists them, until someone changes them or taps **Keep as is** and saves. The other choice is that the notes belong to one browser only and disappear on save. Recommended: save them with the service.
17. **"Save as new service" starts a new week** (clarification 7): when you open last week's saved service and change its date to make this week's, the music and announcements stay, each marked "From last week. Check before printing.", and this week's names (worship leader, liturgist, organist and any part's leader) go back to your usual ones and the pasted readings are emptied, as for a new service. If you change the date back, they return. The other choice is that a copy keeps everything unmarked, last week's guest preacher included. Recommended: mark them and start the names fresh.

Owner steps still to come: the plan's approval; for PR 2b-1, the draft PR on your yes and ready on your yes (T5), the backup on your yes, the counts and the SQL check, the merge on your yes, the after-deploy query and the short phone check (T6); for PR 2b-2, the draft PR on your yes and ready on your yes (T11), the merge on your yes, the four phone steps and the records PR (T12).
