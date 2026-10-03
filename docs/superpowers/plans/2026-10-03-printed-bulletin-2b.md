# Printed Bulletin PR 2b: the Bulletin Step

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the second half of printed bulletin PR 2 (PR 2 planning answer 1, 2026-10-02): **the Bulletin step and the week's own fields.** After it merges, the Service Builder has five steps: a new optional step **4 Bulletin** sits between **3 Liturgy** and **5 Review & send**. On it a member fills in the prelude and postlude (title and composer); sees **Who leads** (the worship leader, liturgist and organist from the 2a Bulletin settings) and can change one of them for this week, or, behind **Change who leads a part**, one part's leader; fills in the announcements (ushers and counters, deacon of the week, coffee hour, this week's activities, prayers and concerns, items for collection, other announcements); and can paste a reading's text for a translation the app cannot fetch. A new draft starts from last week's music and announcements (the church's latest saved service dated before the draft's date), each such box marked "From last week. Check before printing." until it is edited or kept. The printed bulletin (PDF and Word version) prints all of it; a blank field prints nothing, the last [placeholders] for the music and the announcements are gone, and with every announcement blank the announcements page is left out (the cover picture's box stays until PR 3). The Printed bulletin card lists the week's blank fields and the boxes from last week not yet checked. The fields are saved with the service: the draft goes to version 3, `ServiceDraft.bulletin` is optional (a client from before 2b keeps working) and `services` gains one nullable JSON column in migration **`0006_services_bulletin`**, after the owner's backup, read-only counts and SQL preview (PR 2 planning answer 8). The Word working copies (`POST /documents`) do not change. No new package or variable; production Streamlit (branch `streamlit-frozen`) is untouched.

**Architecture:** Backend first. `0006_services_bulletin` (expand-only, batch mode as 0004 and 0005) adds `services.bulletin JSON NULL` (the model's column is `JSON(none_as_null=True)`, so a Python `None` is SQL NULL); `backend/migrations/README.md` gains "Before 0006_services_bulletin" with the owner's four steps, its SQL pinned by tests. `backend/service_bulletin.py` (new, pure) defines `ServiceBulletin` (`Music`, `Announcements`, this week's people, the part leaders, the pasted texts), the tolerant `read`, `to_json`, `carried()` and `map_texts`. `printed_bulletin` prints the music, this week's people and part leaders (`WeekSettings`, the 2a settings with the week's changes over them), the announcements page (none when every announcement is blank; the PDF and Word renderers then leave the page out) and a pasted reading (no credit line). In the API, `ServiceDraft` gains an optional `bulletin` (`api/schemas.ServiceBulletin`, every field present, limits, no line-break check); `usecases.archive` cleans it (Word-safe), stores it (`POST` without it: NULL; `PUT` without it: kept), reads it back on `GET`, and `previous_bulletin` answers `GET /services/previous-bulletin?before=YYYY-MM-DD` (the music and announcements of the church's latest service dated before that date) through `repos.services.previous_service`; `usecases.documents.build_printed` prints the posted bulletin and fetches only the readings without pasted text. OpenAPI regenerated. Frontend: the draft v3 (`schema.ts`: `bulletin`, the step id "bulletin"; `migrate.ts`: 2 → 3 with an empty bulletin), `lib/draft/bulletin.ts` (the edits, carry forward, the payload, "Not filled in" and "not checked yet"), the mapping (`bulletin` in the payload only when something is filled in, so a draft "Saved" before 2b stays "Saved"), the bodies (`serviceBody` always sends it, cut to the limits), the statuses ("Optional" or "n to check"; `isPristine`), `usePreviousBulletin`, the step (`components/builder/bulletin/`, route `/builder/bulletin`), the carry hook `useBulletinCarry` (the Bulletin step and the Printed bulletin card), the five-step bar and the card's lines.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy 2, Alembic, reportlab 5 and python-docx (PR 1's renderers), pytest (SQLite; Postgres for `@pytest.mark.postgres`); Next 16, React 19, TypeScript 5, zod, Base UI, TanStack Query 5, Vitest 3 with Testing Library; openapi-typescript for `schema.d.ts`.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`: owner answers 2, 3, 5, 8; "PR 2 planning answers" 1 and 3-8 (binding); "What prints where"; "Scripture text"; "API"; "Data model" (weekly fields, carry forward); "The Bulletin step and the settings panel"; "Scope by PR".
- The PR 2a plan `docs/superpowers/plans/2026-10-02-printed-bulletin-2a.md` (the format model; its "Questions for the owner" 1-14, answered "all recommended" and binding: 1 the settings page and its link from the step, 4 the standing roles and stars, 5 the weekly placeholders until 2b, 9 the card's wording, which this PR changes as planned) and the 5a-2 plan `docs/superpowers/plans/2026-10-02-slice-5a2-saving.md` (the model for a production migration: the README's "Before 0005_services_extras" steps and its T9).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.3 (`ServiceDraft`), §1.5 (errors), §1.7 (`If-Match`), §2.2 (layers), §2.5 (logs), §3.1, §3.4, §3.5 (migrations: expand-only, the chain), §4.4 (keys), §4.6 (the draft: versioning, never destroy typed input), §4.7 (steps), §4.8 (forms, 44 px).
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `9c731e1` = `origin/main` `1b0b7a3` (PR #46, printed bulletin PR 2a) plus "Runbook: printed bulletin PR 2a record (owner's phone check)", then this plan's commits; 2026-10-03): backend `1395 passed, 16 skipped`; Postgres-marked `16 passed, 1395 deselected` (local Postgres 16); frontend `675 passed` in 85 files; typecheck and lint clean; Alembic head `0005_services_extras` (5 revision files, production too: runbook "Slice 5a-2 record"); 4 runbook owner markers. `ServiceDraft` (`api/schemas.py`) has `extra="forbid"`; `PUT /services/{id}` is a full replace; `GET /services/{service_id}` takes a UUID (a static path must be declared before it); `IsoDate` only checks the date shape when used as `Annotated[IsoDate, Query()]` (as `/lectionary/readings`). `draftToServicePayload` is what the "Unsaved changes" fingerprint hashes, and `serviceBody` is the body of every save and download. No frontend code calls a builder route that does not exist; `installFakeApi` fails a test on any request without a handler, so the three test files that render Review (`review-send-step`, `builder-shell`, `liturgy-step`) need the new route.
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch head (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -3` (or `| tail -1` where a step says so); the suite `.venv/bin/python -m pytest -q | tail -1`. Postgres-marked tests run only with `TEST_DATABASE_URL` set to a local, throwaway Postgres (`tests/pg_helpers.require_local_test_url`); without it they skip, and CI's `backend-postgres` job runs them (after `alembic upgrade head`, `alembic check`, `alembic downgrade base`, `alembic upgrade head`). Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes (T3), so T3 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand. T3 also adds the matching fixture and type names, so typecheck stays clean at every commit.
- No new package, no new variable. One migration, `0006_services_bulletin` (T1), whose `down_revision` is `0005_services_extras`.
- Branch `claude/slice-2-plan-4q33le`, at `9c731e1` plus this plan's commits (`WIP plan: printed bulletin PR 2b …` and `Plan: printed bulletin PR 2b (the Bulletin step)`, and any later plan commit), then T1-T7. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes, and only after T9 Steps 1-3 (backup, counts, SQL).
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1395 → 1421 passed, 16 → 17 skipped; frontend 675 → 693 in 85 → 87 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 16 and has no em dashes; existing copy keeps its own punctuation.
- No church id, email address, token, database URL or real person's name, address, phone or email in any doc, commit, test or record. The tests use invented details only: "Example Church", "Rev. Alex Example", "Sam Sample", "Jordan Doe", "Pat Example", "Lee Sample", "Rev. Guest", "The Example family", "Morning Voluntary", "Festive Postlude", "For all who are ill.". None of the owner's sample bulletin's content enters the repo. Prayers and concerns can name people and their health: they live only in the service's bulletin, never in a log line, a commit or the record (clarification 15).
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action (the backup run included). Owner steps go one at a time, in plain words.

### How the file directives below read
As in the PR 2a plan: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written (top to bottom within a file, so an anchor is unique in the file as the previous directives left it). A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted.

### Baselines and counts
- Starting baselines: backend **1395 passed, 16 skipped**; Postgres-marked **16 passed, 1395 deselected** (with a local Postgres); frontend **675 passed in 85 files**, typecheck and lint clean; Alembic head **`0005_services_extras`** (5 revision files); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new `it(`.

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +4, +1 skipped (`test_migrations.py` 4; `test_services_postgres.py` 1, Postgres only; `test_schema_check.py`, `test_api_app.py` edited) | 1399 passed, 17 skipped | 0 | 675 in 85 |
  | T2 | +12 (`test_service_bulletin.py` 8, one test in five cases; `test_printed_bulletin.py` 3; `test_printed_render.py` 1; `test_api_printed.py` edited) | 1411 passed, 17 skipped | 0 | 675 in 85 |
  | T3 | +10 (`test_usecase_archive.py` 4; `test_api_services.py` 5, two tests and three new 422 cases; `test_api_printed.py` 1; `test_no_streamlit_in_core.py` edited) | 1421 passed, 17 skipped | 0 | 675 in 85 |
  | T4 | 0 | 1421 passed, 17 skipped | +12 (`bulletin.test.ts` 7, `migrate.test.ts` 1, `documents.test.ts` 2, `status.test.ts` 1, `mapping.test.ts` 1; `schema.test.ts`, `store.test.ts`, `keys.test.ts` edited) | 687 in 86 |
  | T5 | 0 | 1421 passed, 17 skipped | +5 (`bulletin-step.test.tsx`; `builder-shell.test.tsx`, `status.test.ts`, `review-send-step.test.tsx` edited) | 692 in 87 |
  | T6 | 0 | 1421 passed, 17 skipped | +1 (`review-send-step.test.tsx`; `liturgy-step.test.tsx` edited) | 693 in 87 |
  | T7 | 0 (no test edited: the new items sit under the existing "## Printed bulletin") | 1421 passed, 17 skipped | 0 | 693 in 87 |

- CI `backend-postgres` goes from `16 passed, 1395 deselected` to `17 passed, 1399 deselected` after T1 and `17 passed, 1421 deselected` at the end. With a local Postgres (`TEST_DATABASE_URL`), the same numbers locally.

### Layering and code rules (carried)
- `service_bulletin`, `printed_bulletin`, `usecases/archive.py`, `usecases/documents.py` and `repos/services.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains `service_bulletin`, T3); the route is a plain `def` with one usecase call, no SQL and no try/except (F §2.2 rule 1); the query lives in `repos.services` and filters on `church_id` (F §1.2).
- Logs carry ids, counts and durations, never a bulletin's text (F §2.5; clarification 15). This PR adds no log line; `archive.<create|replace|delete>` and `documents.printed` are unchanged and tested to carry no text.
- Pages and components never call `apiFetch`: `usePreviousBulletin` uses `useApi()` (F §4.5). The draft is changed only through `useDraft()` (`update` for typing, `autoUpdate` for the carry, F §4.6).
- Touch targets 44 px below `md` (`h-11` inputs, `size="touch"` buttons; textareas are 64 px or more); text wraps at 375 px; no raw HTML (F §4.8); the kit's `Input`, `Textarea`, `Label`, `Button` (Base UI shadcn, as the codebase uses).
- Expand-only migration (F §3.4): one nullable column, no default, no backfill, no index.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** (branch `streamlit-frozen`) is frozen and retired for real use; merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge; Railway's Pre-deploy Command `alembic upgrade head` applies migrations.
4. **The spec's decisions** stand as written in S, with the PR 2 planning answers below winning where S's earlier text differs (T7 amends S's "Data model" to match).
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

1. **[owner-visible] What 2b ships** (planning answer 1). The Bulletin step with its fields, carry forward, pasted reading text, the weekly fields printed in the PDF and the Word version, the card's new lines, the draft v3, `ServiceDraft.bulletin`, `ServiceOut.bulletin`, `GET /services/previous-bulletin` and migration `0006_services_bulletin`. Not here: the cover picture (PR 3; its box keeps printing "[Cover picture]"), any change to the Bulletin settings page or its API, the Word working copies (clarification 18), the summary panel (it shows no bulletin block; "Follow-ups").
2. **[owner-visible] The step and the step bar** (S "The Bulletin step"; planning answer 6; F §4.7). A fifth step, **Bulletin**, number 4, route `/builder/bulletin`, between Liturgy and Review & send (now number 5): Liturgy's footer reads "Next: Bulletin", Bulletin's "Back" and "Next: Review". Below `lg` the bar's line reads "Step 4 of 5 · Bulletin" over five segments (each 44 px tall and about 60 px wide at 375 px, `grid-cols-5`); from `lg` each step shows its number, label and status. The Bulletin step's status is never "Complete" or a count: it is **"Optional"** (muted) or, while boxes from last week are still to check, **"{n} to check"** (for example "2 to check"). It never adds a line to Review's "Still to do" and never turns off a download or Save.
3. **[owner-visible] Music** (answer 2; S "What prints where"). Per piece a **title** (200 characters) and a **composer** (100). Printed as in the sample: "PRELUDE: ‘{title}’" with the organist's name on the right and "- {composer}" under it (POSTLUDE the same). A blank title prints "PRELUDE:" with the composer under it; a blank composer prints no composer line; with both blank the whole PRELUDE (or POSTLUDE) line is left out, the organist's name included (answer 3).
4. **[owner-visible] Who leads** (planning answer 7; S "Data model"). **Worship leader**, **Liturgist** and **Organist** show the Bulletin settings' names (help: "From the bulletin settings. A change here is for this week only."); typing a different name changes it for this week only ("Changed for this week." with **Undo the change**); typing the settings' name back, or **Undo the change**, follows the settings again; a blank field means no one this week (that header line and those parts print no name). Stored as `people: {worship_leader, liturgist, organist}`, each `null` (follow the settings) or this week's text. **Change who leads a part** (outlined, `aria-expanded`) opens one field per part (the 21 parts of 2a, in the printed order) with "Usually {name}" or "Usually no one" under it; a name there prints on that part this week only, a blank one follows the usual leader (so "no one" for a single part this week is done in Bulletin settings; question 3). Stored as `leaders: {element key: name}`. The header and every part's name follow this week's people (`printed_bulletin.WeekSettings`). The settings themselves never change from the step.
5. **[owner-visible] Announcements** (planning answer 4; S "What prints where"). **Ushers and counters** (200), **Deacon of the week** (100) and **Coffee hour** (200) are one line each ("Ushers/Counters: …", "Deacon of the Week: …", "Coffee Hour: …", bold labels, as PR 1); **This week's activities** (4000), **Prayers and concerns** (4000), **Items for collection** (2000) and **Other announcements** (4000) are free text that keeps its line breaks, each under its heading ("THIS WEEK’S ACTIVITIES AT A GLANCE", "PRAYERS AND CONCERNS", "ITEMS FOR COLLECTION", and "OTHER ANNOUNCEMENTS", new, last). The page keeps PR 1's "ANNOUNCEMENTS" and date at the top and stays the last page.
6. **[owner-visible] A blank weekly field prints nothing** (planning answer 3). A blank announcement leaves out its line, or its heading and text. **With every announcement blank there is no announcements page at all** (PDF: the order of worship's last page is the last page, an odd count leaving the last right half blank; Word: no announcements page). The alternative, a page with only "ANNOUNCEMENTS" and the date, is question 5. The last [placeholders] of PR 1 for the music and the announcements are gone; "[Cover picture]", "[Sermon title]" (a blank sermon title) and "[Reading text unavailable]" stay (PR 3; the order of worship; a fetch failure).
7. **[owner-visible] Carry forward** (planning answer 5; S "Data model"; the spec does not say when). Precisely:
   - **From what:** the church's latest service whose date is before the draft's date (the latest date, then the latest save; an undated service never counts; another church's never). Its music and announcements carry; this week's people, the part leaders and the pasted texts never do (S). A service saved before 2b has no bulletin and so carries nothing (the latest service decides, even when an older one had announcements; question 6). The cover picture id is PR 3's.
   - **When:** only for a draft that is **not a saved service** (`editing` null: a new draft, or one started before 2b), with a real date, when the **Bulletin step** or **Review & send** shows it (the two places that show or print the bulletin; `useBulletinCarry`), once per date (`carried_for`). If the date then changes (step 1, or the pristine draft's roll-forward to the next Sunday) and nothing on the step's music or announcements was **edited**, it carries again for the new date (replacing what it carried, blank where the new source has nothing). **Opening a saved service never carries**, and a saved service changed to a new date ("Save as new service") does not either: its fields are what was saved.
   - **"Edited"** (`bulletin.edited`): a music or announcement box typed in, changed in any way (cleared included) or kept with **Keep as is**. After that, last week's never carries in again for this draft. The people, the part leaders and the pasted texts do not count (they never carry).
   - **The check:** each box that received last week's text shows "From last week. Check before printing." (its field described by it) with **Keep as is** (named "Keep {box} as is" for screen readers), until that box is edited or kept (`bulletin.carried`). Keep as is is this plan's addition to answer 5, so a box that is right as it is need not be retyped (question 7). The step bar says "{n} to check"; the Printed bulletin card says "From last week, not checked yet: …" (clarification 9). Nothing ever stops a download over it (planning answer 6).
   - **How:** `GET /services/previous-bulletin?before=<draft date>` (any member, church-scoped), fetched only while carrying is due, applied through `autoUpdate` with the check repeated in the recipe against the latest draft (F §4.6: never over typed input; only the visible tab carries, as the lectionary fill). A failed lookup shows "Last week's announcements could not be loaded." with **Try again** on the step (`role="alert"`); Review shows nothing for it and prints without.
8. **[owner-visible] Pasted reading text** (answer 5; S "Scripture text"). Under **Reading text**, one box per reading the files print (the first reading and the New Testament reading, as `effectivePicks` resolves them), labelled "First Reading: {reference}" and "New Testament Reading: {reference}"; with no readings chosen, "Choose the readings on step 1 to paste their text.". The text is kept with its reading's reference, so choosing another reading shows an empty box (and choosing the first again brings the text back); only the texts of the two readings printed are sent. A pasted text prints instead of the fetched one, as paragraphs (a blank line starts a new one), **is not fetched** (no `scripture` token is charged for it), and **leaves out the credit line** "Scripture readings are from …" (the pasted text is the church's own translation; the help line says to include the translation's notice if it asks for one; question 9).
9. **[owner-visible] The Printed bulletin card** (planning answer 3; 2a's clarification 9 as changed here). PR 1's line "For now, the music and the announcements print as [placeholders]." goes. After the 2a sentence "The church's details, the people who lead and the service time come from the bulletin settings." comes "The music, the announcements and this week's changes to who leads come from the Bulletin step.", then, above the downloads: "Not filled in: {list}." where the list is the 2a standing fields (the three people as this week has them: a person changed on the step counts as filled in, one cleared for this week as not), then "prelude", "postlude" and "announcements" (only when every announcement is blank); while the settings load or if they fail, only the week's part. Then, when any box still holds last week's text unchecked, "From last week, not checked yet: {list}." (labels: prelude, postlude, ushers and counters, deacon of the week, coffee hour, activities, prayers and concerns, collection items, other announcements). The card also runs the carry (clarification 7), so a bulletin printed without opening the Bulletin step has last week's. Its downloads, gates, toasts, save tip and **Bulletin settings** button are unchanged.
10. **[owner-visible] Saving and opening** (S "Data model"; 5a-3's Save). Save stores the bulletin with the service; opening it from **Services** restores every field as saved (the pasted texts under their readings' references), with nothing marked "From last week". A change on the Bulletin step makes Review say "Unsaved changes". `draftToServicePayload` (what the fingerprint hashes) holds `bulletin` only when something is filled in, so a draft that was "Saved" before 2b stays "Saved" after its migration; every body sent (`serviceBody`: the saves, the Word copies, the printed bulletin) always carries `bulletin`, each text cut to its limit, so a save that clears every field clears the saved ones. On the server a `POST` without `bulletin` (a client from before 2b) stores NULL and a `PUT` without it keeps the saved one; the 409 "is it my own save?" check (`savedCopyFingerprint`) compares the bulletin too. The "From last week" marks are the draft's own and are not saved.
11. **The draft v3** (F §4.6 "Versioning"). `DRAFT_VERSION` 3; `STEP_IDS` gains "bulletin" (`last_step` may hold it); `bulletin: {prelude, postlude, people, leaders, announcements, pasted (by reference), carried (the boxes still to check), edited, carried_for}` (`freshBulletin()` in `freshDraft`). `migrations[2]` adds `freshBulletin()` and changes nothing else (a draft in progress is never lost; it carries like a new one unless it is a saved service). A version 4 draft (a later rollback) is a restore error, as today. An open tab still on version 2 code is handled by 5a-3's rule (never adopted; written over).
12. **The API** (S API). `ServiceDraft.bulletin: Optional[ServiceBulletin] = None` with `ServiceBulletin {prelude, postlude: {title, composer}, people: {worship_leader, liturgist, organist: string | null}, leaders: {ElementKey: string}, announcements: {ushers, deacon, coffee_hour, activities, prayer_concerns, collection, other}, reading_text: {ot, nt}}`, every field present, `extra="forbid"` at every level, each text within its limit (clarifications 3-5, 8; `service_bulletin.MAX_LENGTH`), the leaders' keys the 21 element keys: a bad bulletin is the usual 422 naming the field (`bulletin.announcements.ushers`, `bulletin.leaders.anthem.[key]`, `bulletin.cover_image_id`). No line-break check (unlike 2a's settings): `service_bulletin.read` makes a one-line field one line (each run of control characters, U+2028/U+2029 and C1 controls becomes a space), so a download never meets a 422 for a pasted line break. `ServiceOut.bulletin: ServiceBulletin`, always present (an empty one for a service saved without it). `GET /services/previous-bulletin?before=YYYY-MM-DD` (`require_church`; `before` required and a real date, else 422) answers `PreviousBulletinOut {service_id, service_date_iso, bulletin}`: the source service and the carried part (the people null, the leaders `{}` and the texts blank), or `null`, `null` and an empty bulletin. It is declared before `/services/{service_id}`. No `Idempotency-Key`, no rate limit (a local read). `POST /documents` and `POST /documents/printed` accept `bulletin` through `ServiceDraft` (the Word copies ignore it).
13. **Storage** (S "Data model"; F §3.4, §3.5). `services.bulletin JSON NULL` in `0006_services_bulletin` (`down_revision` `0005_services_extras`; batch mode both ways, so `--sql` and Postgres get a plain `ALTER TABLE … ADD COLUMN bulletin JSON`, under `env.py`'s 5 s lock timeout; adding a nullable column without a default changes only the catalog). The model's column is `JSON(none_as_null=True)`: SQLAlchemy's `JSON` otherwise stores a Python `None` as the JSON value `null`, which `IS NOT NULL` counts (found while planning). A save stores `service_bulletin`'s `to_json()` of the cleaned input (every text Word-safe through `archive._xml_safe`, trimmed and cut); `GET` reads it tolerantly (`service_bulletin.read`: a missing or malformed value is blank). Tests: up from 0005 with a row kept and a later insert without the column (NULL), down giving back the 0005 table, the exact offline SQL, the drift at the baseline and the head constants (`test_schema_check.py`, `test_api_app.py`; 5a-2's 0005 upgrade test now upgrades to `0005_services_extras`, not head), and the owner's two queries on Postgres. The 5a-2 Postgres test of the 0005 queries now expects the head's version.
14. **[owner-visible] The owner's production steps** (planning answer 8; 0005's routine). `backend/migrations/README.md` gains "Before 0006_services_bulletin (printed bulletin PR 2b)": (1) a `db-backup` run; (2) one read-only query giving `version` (`0005_services_extras`), `services` and `churches`; (3) the `--sql` preview, rendered by the agent without a database (6 lines: `BEGIN;`, the two timeouts, `ALTER TABLE services ADD COLUMN bulletin JSON;`, the version update, `COMMIT;`), pinned by `test_the_readme_shows_the_0006_preview_exactly`; (4) after the deploy, a read-only query giving `0006_services_bulletin`, `1` and `with_bulletin` (0, or the few services saved since the deploy), then step 2 again (the same counts, or more). Both queries run in a Postgres test (T1). T9 takes the owner through them one at a time. Reverting 2b keeps `0006` (README "Reverting 2b"; T9 Step R).
15. **Privacy and logging** (F §2.5). Prayers and concerns can name people and their health. They live only in the draft (the member's own browser storage) and in the saved service's `bulletin` (the same as the liturgy texts: any member of that church can open the service); they are printed only in the files the member downloads. No log line carries a bulletin's text (`archive.*` and `documents.printed` log ids, counts, sizes and durations; T3 tests both); a 422 names the field, never its value. The tests and docs use invented text only; the owner's check and the record never copy a name from the prayers.
16. **[owner-visible] Every new user-facing string** (no em dashes). The step: "Bulletin" (the step's label, short name and heading); "Optional. What this week's printed bulletin adds to the service. A box left blank is left off the bulletin."; the groups "Music", "Who leads", "Announcements", "Reading text"; "Prelude title", "Prelude composer", "Postlude title", "Postlude composer"; "From the bulletin settings. A change here is for this week only."; "Worship leader", "Liturgist", "Organist" (2a's words); "Changed for this week."; "Undo the change" (for screen readers "Undo the change to {person}"); "Change who leads a part"; "A name here prints on that part this week only. Leave it blank for the usual leader."; the 21 part names (2a's); "Usually {name}", "Usually no one"; "Ushers and counters", "Deacon of the week", "Coffee hour", "This week's activities", "Prayers and concerns", "Items for collection", "Other announcements"; "Paste a reading's text to print it instead of the text the app fetches, for a translation the app cannot fetch. Include the translation's notice if it asks for one."; "First Reading: {reference}", "New Testament Reading: {reference}"; "Choose the readings on step 1 to paste their text."; "From last week. Check before printing."; "Keep as is" (for screen readers "Keep {box} as is"); "Last week's announcements could not be loaded."; "Try again"; "Bulletin settings" (2a's button). The step bar: "Optional", "{n} to check", "Step {n} of 5". The card: "The music, the announcements and this week's changes to who leads come from the Bulletin step."; "Not filled in: …" gains "prelude", "postlude", "announcements"; "From last week, not checked yet: {list}." with the labels of clarification 9. In the files: "OTHER ANNOUNCEMENTS". Gone: "For now, the music and the announcements print as [placeholders]." and PR 1's weekly placeholders ("[Prelude title]", "[Postlude title]", "[Composer]", "[Names]", "[Name]", "[Activities]", "[Prayer concerns]", "[Collection items]").
17. **Docs** (T7). `docs/manual-verification.md` gains "### Printed bulletin PR 2b: the Bulletin step" with items 16-24 at the end, inside "## Printed bulletin" (a `###` heading, so `test_slice1_docs.py`'s pin of the last eight `##` headings does not move and no test changes; T7 Step 2 checks it), with a note that Review & send is now step 5; PR 1's item 2 says where the music and announcements come from after 2b. S's "Data model" gains `people`, "other" and the planned carry rule (the spec said nothing of when it happens). The runbook record is T9's (`### Printed bulletin PR 2b record` before `## Backups`).
18. **What does not change.** The Word working copies (`POST /documents`, the bulletin and pastor's copies) print as before and ignore `bulletin` (S answer 7 kept them as they are; no strong reason to add the music or announcements there; question 15). The Bulletin settings page, its API and storage. `liturgy` keeps only the eight sections. `service_archive.py` (Streamlit's), `env.py`, the workflows, `package.json`, `requirements*.txt`, `app.py`, Streamlit.

### Risks
- **A lock on `services` at deploy time.** `ALTER TABLE` waits for a conflicting lock; `lock_timeout` turns that into a failed deploy after 5 s with the previous release still serving (T9 Step 5 checks the deploy and `/health/ready`, which answers 503 `schema_behind` while the database is behind the release).
- **The two deploys are not simultaneous.** Vercel (the frontend) can be live a minute or two before Railway has migrated and started the new API. In that window a reloaded page sends `bulletin` to the old API, whose `ServiceDraft` refuses unknown fields: a save or download answers "The request was not valid." (and an old cached page talking to the new API is fine: `bulletin` is optional). T9 waits for Railway's deploy before the phone check; the owner should not build a service in those minutes. Not made safe in code: sending `bulletin` only when filled would stop a save from clearing it.
- **Carry happens in the browser, on the Bulletin step and Review.** A download tapped in the first moment on Review, before last week's answer arrives, prints without it (the card then shows the carried lines; download again). A draft never shown on either step never carries (it cannot print without Review).
- **The latest service decides** (clarification 7): if last week's service was saved before 2b (or with nothing filled in), nothing carries, even if an older service had announcements.
- **Pasted text replaces the credit line for both readings** (clarification 8), so a church pasting only one reading and fetching the other prints no credit line for the fetched one; the public-domain translations need none and ESV text carries its own "(ESV)".
- **Prayers and concerns are visible to every member who opens the service** (as every saved field is). Named in clarification 15 and question 11.
- **SQLite and JSON:** the archive tests run on SQLite, where `bulletin` is TEXT holding JSON; the Postgres tests (T1) cover the real `json` type with the owner's queries, and CI runs the alembic cycle on Postgres 17.
- **Long free text** flows: a long prayer list makes the announcements page run on to another page (the PDF flows; the booklet keeps reading order). The limits (4000 characters) keep it to a page or two.

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/migrations/versions/0006_services_bulletin.py` | `services.bulletin` | T1 |
| `backend/service_bulletin.py` (+ `backend/tests/test_service_bulletin.py`) | `ServiceBulletin`, `Music`, `Announcements`, `read`, `MAX_LENGTH`, `ANNOUNCEMENT_KEYS` | T2 |
| `frontend/src/lib/draft/bulletin.ts` (+ `.test.ts`) | the edits, carry forward, the payload, `bulletinFromService`, "Not filled in", "not checked yet", the step status | T4 |
| `frontend/src/app/(signed-in)/(church)/builder/bulletin/page.tsx`, `frontend/src/components/builder/bulletin/bulletin-step.tsx` (+ `.test.tsx`), `frontend/src/components/builder/bulletin/use-bulletin-carry.ts` | the step's route, the step, the carry hook | T5 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/db/models.py`, `backend/migrations/README.md` | `Service.bulletin`; the head, the 0006 row, "Before 0006_services_bulletin" | T1 |
| `backend/tests/test_migrations.py`, `backend/tests/test_schema_check.py`, `backend/tests/test_api_app.py`, `backend/tests/test_services_postgres.py` | the 0006 tests, the README pin; the head and the baseline drift; the owner's queries on Postgres | T1 |
| `backend/printed_bulletin.py`, `backend/printed_pdf.py`, `backend/printed_docx.py` | the music, `WeekSettings`, the announcements page (none when blank), pasted readings; the renderers leave an empty page out | T2 |
| `backend/tests/test_printed_bulletin.py`, `backend/tests/test_printed_render.py`, `backend/tests/test_api_printed.py` | `WEEK`; the new content and render tests; (T3) the posted bulletin prints | T2, T3 |
| `backend/api/schemas.py`, `backend/api/routes/services.py`, `backend/usecases/archive.py`, `backend/repos/services.py`, `backend/usecases/documents.py` | `ServiceBulletin` and `PreviousBulletinOut`, `ServiceDraft.bulletin`, `ServiceOut.bulletin`; the route; save, open, `previous_bulletin`; `previous_service`; the posted bulletin and pasted readings printed | T3 |
| `backend/tests/test_usecase_archive.py`, `backend/tests/test_api_services.py`, `backend/tests/test_no_streamlit_in_core.py` | the archive's bulletin and carry; the API's; `service_bulletin` | T3 |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated | T3 |
| `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts` | `ServiceBulletin`, `PreviousBulletin`; `serviceBulletin()`, `savedService().bulletin` (T3), `previousBulletin()` (T5) | T3, T5 |
| `frontend/src/lib/draft/schema.ts`, `migrate.ts`, `mapping.ts`, `status.ts`, `frontend/src/lib/documents.ts`, `frontend/src/lib/queries/keys.ts`, `frontend/src/lib/queries/services.ts`, `frontend/src/components/builder/step-progress.tsx` | the draft v3; 2 → 3; the payload and `serviceToDraft`; the status and `isPristine`; `serviceBody`, `savedCopyFingerprint`; `keys.previousBulletin`; `usePreviousBulletin`; the new status texts (T4), five columns (T5) | T4, T5 |
| `frontend/src/lib/draft/schema.test.ts`, `migrate.test.ts`, `store.test.ts`, `mapping.test.ts`, `status.test.ts`, `frontend/src/lib/documents.test.ts`, `frontend/src/lib/queries/keys.test.ts` | version 3; the new cases | T4, T5 |
| `frontend/src/lib/draft/steps.ts`, `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/components/builder/review/review-send-step.test.tsx` | five steps; the step bar's tests | T5, T6 |
| `frontend/src/components/builder/review/printed-card.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.test.tsx` | the card's lines and the carry; the new route in the test that renders Review | T6 |
| `docs/manual-verification.md`, `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md` | "### Printed bulletin PR 2b: the Bulletin step", PR 1's item 2; S's "Data model" | T7 |
| `docs/ops-runbook.md` | the PR 2a record (`9c731e1`, rides along until merged); "### Printed bulletin PR 2b record" (the records PR, after the merge) | T9 |

**Counts in the PR:** 57 paths: 10 created (this plan and the nine new code and test files above), 47 modified (the 46 code, test, API and docs paths above, and `docs/ops-runbook.md` (the PR 2a record `9c731e1`), which rides along until merged). **Untouched:** `service_output.py`, `worship_service.py`, `api/routes/documents.py`, `bulletin_settings.py`, the Bulletin settings page and its API, `migrations/env.py`, `service_archive.py`, `documents-card.tsx`, the summary panel, the workflows, the packages, `app.py`, Streamlit.

**Task order and review batch:** T1 → T7, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T8 verifies and opens the draft PR on the owner's yes; T9 takes the owner through the backup, the counts and the SQL, merges on the owner's yes, checks production, runs the phone check and writes the record.

---

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
    section = readme.split("\n## Before 0006_services_bulletin (printed bulletin PR 2b)\n", 1)[1]
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
        "\n## Before 0006_services_bulletin (printed bulletin PR 2b)\n", 1)[1]
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

## Before 0006_services_bulletin (printed bulletin PR 2b)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0006_services_bulletin` when the printed bulletin PR 2b merges. First, as
the owner decided on 2026-10-02 (PR 2 planning answer 8, the same routine as
0005): a backup, read-only counts of the saved services, and a look at the
SQL; after the deploy, one read-only check. One step at a time. Nothing here
changes data. The agent guides the owner and records the results in
`docs/ops-runbook.md` → "Printed bulletin PR 2b record", never with an email
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

Expected: `0006_services_bulletin`, `1`, and `with_bulletin` `0` (or the
few services saved since the deploy: a save from the new app always
stores a bulletin). Then step 2's query again: the same `services` and
`churches` (or more, by the services saved since the deploy; never fewer).

### Reverting 2b

The schema stays at `0006_services_bulletin`: the column is nullable and the
code before 2b ignores it. Revert the merge commit, then restore
`backend/migrations/versions/0006_services_bulletin.py` and the `Service`
column in `backend/db/models.py` from the merge commit in the same PR, so
Railway's `alembic upgrade head` still finds the database at head and
`alembic check` stays clean. Never `alembic downgrade` production for this:
the weekly fields saved since the merge stay in the column, unread, and come
back when 2b does.
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

**Expected:** `75 passed, 4 skipped in <t>s`; the six lines of clarification 14 exactly (README step 3); `1399 passed, 17 skipped in <t>s`. With a local, throwaway Postgres: `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `17 passed, 1399 deselected`, and CI's cycle by hand on an empty database there (from `backend/`, `DATABASE_URL=<local url of an empty database>`): `../.venv/bin/alembic upgrade head`, `check` (`No new upgrade operations detected.`), `downgrade base`, `upgrade head`, `check`; without one, say so (CI's `backend-postgres` runs them).

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/migrations/versions/0006_services_bulletin.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py
git commit -q -m "Migration 0006_services_bulletin: services.bulletin (printed bulletin PR 2b)" -m "Expand-only (F 3.4): one nullable JSON column with no default and no
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

### Task 2: The week's fields print: `service_bulletin` and `printed_bulletin` (planning answers 3, 4, 7; S "What prints where", "Scripture text"; clarifications 3-6, 8)

**Files:**
- Create: `backend/tests/test_service_bulletin.py`, `backend/service_bulletin.py`
- Modify: `backend/tests/test_printed_bulletin.py`, `backend/tests/test_printed_render.py`, `backend/tests/test_api_printed.py`, `backend/printed_bulletin.py`, `backend/printed_pdf.py`, `backend/printed_docx.py`

The PR 1 and 2a tests now pass `WEEK` (invented music and announcements) and expect them where PR 1 expected the weekly [placeholders]; `test_printed_render.py` imports `WEEK` with `SETTINGS`. `test_api_printed.py`'s 2a test, which posts no bulletin, now expects no prelude, postlude or announcements at all.

- [ ] **Step 1: Write the failing tests**

**In `backend/tests/test_api_printed.py`, replace:**

````python
    assert "‘[Prelude title]’" in text and "Coffee Hour: [Name]" in text           # the weekly fields: PR 2b
````

**with:**

````python
    # No weekly field was sent, so none prints: no prelude, postlude or announcements page (PR 2b).
    for gone in ("PRELUDE", "POSTLUDE", "[Prelude title]", "ANNOUNCEMENTS October", "Coffee Hour", "[Names]"):
        assert gone not in text, gone
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


def test_pasted_reading_text_prints_and_leaves_the_credit_line_out():
    pasted = service(nt=pb.Reading("Matthew 21:33-46", "Jesus said, What do you think?", pasted=True))
    lines = texts(pb.order_of_worship(pasted))
    i = lines.index("NEW TESTAMENT READING:  Matthew 21:33-46")
    assert lines[i + 1:i + 3] == ["Jesus said, What do you think?", "SERMON:  “Who Said?”"]
    assert not any(line.startswith("Scripture readings are from") for line in lines)
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
    "reading_text": {"ot": "", "nt": ""},
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
    assert not b.is_blank()
    assert sb.read(b.to_json()) == b


def test_what_carries_forward_is_the_music_and_the_announcements():
    week = sb.read({"prelude": {"title": "Morning Voluntary", "composer": ""}, "people": {"organist": "Sam Sample"},
                    "leaders": {"sermon": "Rev. Guest"}, "announcements": {"coffee_hour": "The Example family"},
                    "reading_text": {"nt": "Pasted."}})
    assert week.carried() == sb.ServiceBulletin(prelude=sb.Music("Morning Voluntary", ""),
                                                announcements=sb.Announcements(coffee_hour="The Example family"))


def test_map_texts_changes_every_text_and_keeps_the_standing_people():
    week = sb.read({"prelude": {"title": "a"}, "people": {"liturgist": "b"}, "leaders": {"sermon": "c"},
                    "announcements": {"other": "d"}, "reading_text": {"ot": "e"}})
    upper = week.map_texts(str.upper)
    assert upper.to_json()["prelude"]["title"] == "A"
    assert upper.people == {"worship_leader": None, "liturgist": "B", "organist": None}
    assert (upper.leaders, upper.announcements.other, upper.ot_text) == ({"sermon": "C"}, "D", "E")
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py 2>&1 | tail -3` then `.venv/bin/python -m pytest -q backend/tests/test_api_printed.py 2>&1 | tail -1`
**Expected** (`service_bulletin` does not exist yet: `ModuleNotFoundError` above these lines; `test_printed_render.py` imports from `test_printed_bulletin.py`):
```
ERROR backend/tests/test_printed_render.py
!!!!!!!!!!!!!!!!!!! Interrupted: 3 errors during collection !!!!!!!!!!!!!!!!!!!!
3 errors in <t>s
```
then `1 failed, 11 passed in <t>s` (PR 1's "‘[Prelude title]’" still prints).

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
  blank there is no announcements page. The cover picture prints as a
  [bracketed placeholder] until PR 3.
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
from service_bulletin import Music, ServiceBulletin
````

**In `backend/printed_bulletin.py`, replace:**

````python
# The weekly fields' placeholders, until PR 2b's Bulletin step and PR 3 fill them.
PRELUDE = ("[Prelude title]", "[Composer]")
POSTLUDE = ("[Postlude title]", "[Composer]")
````

**with:**

````python
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
    bulletin: ServiceBulletin = ServiceBulletin()        # the week's own fields (PR 2b)


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
    values.update({role: name for role, name in ps.bulletin.people.items() if name is not None})
    return WeekSettings(**values, part_leaders=dict(ps.bulletin.leaders))
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
        *_music(s, "prelude", "Prelude", ps.bulletin.prelude),
````

**In `backend/printed_bulletin.py`, replace:**

````python
    if (ps.ot or ps.nt) and ps.translation_label:
````

**with:**

````python
    # Fetched text only: a pasted text is the church's own translation (PR 2b), so no credit line is printed.
    if (ps.ot or ps.nt) and ps.translation_label and not any(r.pasted for r in (ps.ot, ps.nt) if r):
````

**In `backend/printed_bulletin.py`, replace:**

````python
    lines += _music(s, "postlude", "Postlude", POSTLUDE)
````

**with:**

````python
    lines += _music(s, "postlude", "Postlude", ps.bulletin.postlude)
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


def announcements(ps: PrintedService) -> list[Line]:
    """The back page: each announcement filled in this week (a free text
    keeps its lines), the blank ones left out; nothing at all when every one
    is blank, and the renderers then leave the page out."""
    a = ps.bulletin.announcements
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
  and the pasted text of the two readings (pasted wins over fetched).
- read(raw): a stored or posted value read tolerantly: anything that is not
  an object, a missing key or a value of the wrong type is blank (a person
  None); an unknown element key and a blank part leader are dropped; every
  text is trimmed and cut to its limit, and every one-line text (the music,
  the people, the part leaders, the ushers, the deacon and the coffee hour)
  has each run of line breaks, tabs or other control characters made one
  space. The free texts (activities, prayers and concerns, collection items,
  other announcements, the pasted readings) keep their lines.
- to_json: the stored shape (what GET /services/{id} answers as `bulletin`).
- carried(): what a new week starts from (PR 2 planning answer 5): the music
  and the announcements; the people, the part leaders and the pasted texts
  start empty.
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

# The longest value each text takes; ServiceDraft refuses longer (422), and read() cuts a stored one.
MAX_LENGTH = {"title": 200, "composer": 100, "person": 100, "ushers": 200, "deacon": 100, "coffee_hour": 200,
              "activities": 4000, "prayer_concerns": 4000, "collection": 2000, "other": 4000,
              "reading_text": 20_000}

_NOT_ONE_LINE_RUN = re.compile(f" *[{NOT_ONE_LINE}][{NOT_ONE_LINE} ]*")


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
            ot_text=fn(self.ot_text), nt_text=fn(self.nt_text))

    def to_json(self) -> dict:
        return {
            "prelude": {"title": self.prelude.title, "composer": self.prelude.composer},
            "postlude": {"title": self.postlude.title, "composer": self.postlude.composer},
            "people": {role: self.people.get(role) for role in ROLES},
            "leaders": {key: self.leaders[key] for key in ELEMENT_KEYS if key in self.leaders},
            "announcements": {key: getattr(self.announcements, key) for key in ANNOUNCEMENT_KEYS},
            "reading_text": {"ot": self.ot_text, "nt": self.nt_text},
        }


def _object(value: object) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _text(value: object, limit: int, *, one_line: bool) -> str:
    if not isinstance(value, str):
        return ""
    if one_line:
        value = _NOT_ONE_LINE_RUN.sub(" ", value)
    return value.strip()[:limit].strip()


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
        ot_text=_text(reading_text.get("ot"), MAX_LENGTH["reading_text"], one_line=False),
        nt_text=_text(reading_text.get("nt"), MAX_LENGTH["reading_text"], one_line=False),
    )
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py backend/tests/test_api_printed.py 2>&1 | tail -1` then `grep -rn "Prelude title\]\|\[Names\]\|\[Collection items\]" backend --include=*.py --exclude-dir=tests; echo "placeholders grep exit $?"` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:** `44 passed in <t>s`; `placeholders grep exit 1`; `1411 passed, 17 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/service_bulletin.py backend/printed_bulletin.py backend/printed_pdf.py backend/printed_docx.py backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py backend/tests/test_api_printed.py
git commit -q -m "Printed bulletin PR 2b: the week's fields print" -m "service_bulletin holds a service's weekly bulletin fields (the music,
this week's people and part leaders, the announcements, the pasted
reading text), read tolerantly. The printed bulletin prints them over
the settings: a blank one prints nothing, with every announcement blank
there is no announcements page, Other announcements prints last, and a
pasted reading prints with no credit line. PR 1's weekly placeholders
are gone; the cover picture's stays until PR 3." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1411 passed, 17 skipped`; frontend `675 passed` in 85 files.

### Task 3: The API saves, opens, carries and prints the bulletin (S API, "Data model"; F §1.2, §1.3, §2.2; clarifications 7, 8, 10, 12, 15)

**Files:**
- Modify: `backend/tests/test_usecase_archive.py`, `backend/tests/test_api_services.py`, `backend/tests/test_api_printed.py`, `backend/tests/test_no_streamlit_in_core.py`, `backend/api/schemas.py`, `backend/usecases/archive.py`, `backend/repos/services.py`, `backend/api/routes/services.py`, `backend/usecases/documents.py`, `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (the last two regenerated)

`ServiceOut.bulletin` is required in the regenerated types, so the frontend fixture `savedService()` gains `bulletin: serviceBulletin()` in this commit (typecheck stays clean; no frontend test changes count).

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
    "reading_text": {"ot": "", "nt": ""},
}
BULLETIN = {
    **BLANK_BULLETIN,
    "prelude": {"title": "Morning Voluntary", "composer": "Pat Example"},
    "people": {"worship_leader": "Rev. Guest", "liturgist": "", "organist": None},
    "leaders": {"sermon": "Rev. Guest"},
    "announcements": {**BLANK_BULLETIN["announcements"], "ushers": "Sam Sample", "coffee_hour": "The Example family",
                      "prayer_concerns": "For all who are ill."},
    "reading_text": {"ot": "", "nt": "Pasted text."},
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
    "reading_text": {"nt": "Pasted text."}})
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
**Expected:** `10 failed, 65 passed in <t>s`: the four usecase tests (`ServiceInput` has no `bulletin`), the five API tests and cases (`bulletin` is an extra field, a 422; no `/services/previous-bulletin`, a 422 for the id), the printed one (a 422 too). `test_no_streamlit_in_core.py` passes (the module exists since T2).

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
    download never meets a 422 for one."""

    model_config = ConfigDict(extra="forbid")

    prelude: BulletinMusic
    postlude: BulletinMusic
    people: BulletinPeople
    leaders: dict[Literal[bulletin_settings.ELEMENT_KEYS], _bulletin_text("person")]
    announcements: BulletinAnnouncements
    reading_text: BulletinReadingText


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
fetched nor charged. The log line never carries a bulletin's text.
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
    week = clean.bulletin or ServiceBulletin()
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
        settings=church_bulletin.read_settings(church["settings"]), bulletin=week)
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
````

- [ ] **Step 4: Regenerate the API files; see them pass, the suite, types and lint**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api >/dev/null) && git diff --stat -- frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts | tail -1
.venv/bin/python -m pytest -q backend/tests/test_usecase_archive.py backend/tests/test_api_services.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `Wrote <repo>/frontend/src/lib/api/openapi.json`, then ` 2 files changed, 523 insertions(+), 1 deletion(-)`; `75 passed in <t>s`; `1421 passed, 17 skipped in <t>s` (`test_openapi_contract.py` and `test_route_guards.py` pass unchanged); ` Test Files  85 passed (85)`, `      Tests  675 passed (675)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add backend/api/schemas.py backend/usecases/archive.py backend/repos/services.py backend/api/routes/services.py backend/usecases/documents.py backend/tests/test_usecase_archive.py backend/tests/test_api_services.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts frontend/src/lib/api/types.ts frontend/src/test/fixtures/index.ts
git commit -q -m "Printed bulletin PR 2b: the API saves, opens, carries and prints the bulletin" -m "ServiceDraft gains an optional bulletin (every field present, within
its limits; a client from before 2b sends none: a POST stores NULL and
a PUT keeps the saved one); ServiceOut answers it, empty when none was
saved. GET /services/previous-bulletin?before= answers the music and
announcements of the church's latest service dated before that date,
for carry forward. The printed bulletin prints the posted fields, and a
pasted reading is neither fetched nor charged. Every text is made
Word-safe and none is logged. OpenAPI snapshot and types regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1421 passed, 17 skipped`; frontend `675 passed` in 85 files.

### Task 4: The draft v3 and the bulletin on the client (F §4.4, §4.6, §4.7; clarifications 2, 7-11)

**Files:**
- Create: `frontend/src/lib/draft/bulletin.test.ts`, `frontend/src/lib/draft/bulletin.ts`
- Modify: `frontend/src/lib/draft/schema.test.ts`, `frontend/src/lib/draft/migrate.test.ts`, `frontend/src/lib/draft/store.test.ts`, `frontend/src/lib/draft/mapping.test.ts`, `frontend/src/lib/draft/status.test.ts`, `frontend/src/lib/documents.test.ts`, `frontend/src/lib/queries/keys.test.ts`, `frontend/src/lib/draft/schema.ts`, `frontend/src/lib/draft/migrate.ts`, `frontend/src/lib/draft/mapping.ts`, `frontend/src/lib/draft/status.ts`, `frontend/src/lib/documents.ts`, `frontend/src/lib/queries/keys.ts`, `frontend/src/lib/queries/services.ts`, `frontend/src/components/builder/step-progress.tsx`

The existing tests that pin the version (2 → 3, a "future" version 3 → 4) change with it. `step-progress.tsx` gains only the two new status texts here (the switch must cover every `StepStatus`); its five columns and the step itself are T5's, so the step bar is unchanged until then ("bulletin" is not in `SHIPPED_STEPS` yet).

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
    expect(printedRequest(d, "pdf").service.bulletin).toEqual(bulletin);
  });

  it("count in savedCopyFingerprint: another device's announcements are someone else's change", () => {
    const theirs = savedService({ bulletin: serviceBulletin({ announcements: { ...serviceBulletin().announcements, deacon: "Alex Example" } }) });
    const sent = { ...theirs, bulletin: { ...theirs.bulletin, announcements: { ...theirs.bulletin.announcements, deacon: " Alex Example\r\n" } } };
    expect(savedCopyFingerprint(sent)).toBe(savedCopyFingerprint(theirs));
    expect(savedCopyFingerprint({ ...theirs, bulletin: serviceBulletin() })).not.toBe(savedCopyFingerprint(theirs));
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
      carried_for: "2026-10-04",
    });
    expect(shouldCarry(c)).toBe(false); // once per date
    expect(applyCarry(c, lastWeek(), "2026-10-04")).toBe(c);
    expect(applyCarry(d, lastWeek(), "2026-10-11")).toBe(d); // the date moved meanwhile
    // Nothing saved before the date: nothing carries, and it is not looked up again for that date.
    const none = applyCarry(d, { service_id: null, service_date_iso: null, bulletin: serviceBulletin() }, "2026-10-04");
    expect(none.bulletin).toMatchObject({ carried: [], carried_for: "2026-10-04" });
  });

  it("carries again for a new date while nothing carried was touched, and never once a box is edited or kept", () => {
    const moved = setDate(carried(), "2026-10-11", "user");
    expect(shouldCarry(moved)).toBe(true);
    const again = applyCarry(moved, lastWeek({ bulletin: serviceBulletin() }), "2026-10-11");
    expect(again.bulletin).toMatchObject({ prelude: { title: "" }, announcements: { ushers: "" }, carried: [] });
    for (const touched of [
      setAnnouncement(carried(), "coffee_hour", "The Sample family"),
      setAnnouncement(carried(), "coffee_hour", ""), // cleared is edited too
      keepCarried(carried(), "ushers"),
      setAnnouncement(testDraft(), "other", "Typed before any carry."),
    ]) {
      expect(shouldCarry(setDate(touched, "2026-10-11", "user"))).toBe(false);
    }
    // The people, a part's leader and pasted text never stop it: they never carry.
    expect(shouldCarry(setPerson(setPartLeader(testDraft(), "sermon", "Rev. Guest"), "organist", ""))).toBe(true);
  });

  it("never carries into a saved service or a draft without a real date", () => {
    expect(shouldCarry({ ...testDraft(), editing: { service_id: "s1", saved_at: "x", date_iso: "2026-10-04" } })).toBe(false);
    expect(shouldCarry(setDate(testDraft(), "", "user"))).toBe(false);
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
    // Another NT pick: its own box, empty; the text pasted for Philippians stays in the draft.
    const other = setPick(d, "nt", "Matthew 21:33-46");
    expect(bulletinPayload(other).reading_text.nt).toBe("");
    expect(bulletinPayload(setPick(other, "nt", "Philippians 3:4b-14")).reading_text.nt).toBe("Pasted for the NT.");
  });

  it("opens a saved service's bulletin as it was saved, its pasted text under the reading's reference, nothing to check", () => {
    const saved = serviceBulletin({
      people: { worship_leader: null, liturgist: "Sam Sample", organist: null },
      leaders: { sermon: "Rev. Guest" },
      reading_text: { ot: "", nt: "Pasted text." },
    });
    const b = bulletinFromService(saved, savedService());
    expect(b).toMatchObject({ people: saved.people, leaders: saved.leaders, carried: [], carried_for: null });
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

import { setAnnouncement, setPastedText } from "./bulletin";
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
    });
    const d = opened(savedService({ bulletin }));
    expect(draftToServicePayload(d).bulletin).toEqual(bulletin);
    expect(reviewStatus(d)).toBe("saved");
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
        edited: false,
        carried_for: null,
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
   × DraftStore changes (S store.ts) > never adopts a draft an older version of the app wrote, however new, and writes over it (slice 5a-3: an old tab) <t>ms
   × DraftStore changes (S store.ts) > puts its draft back over an old tab's with nothing to write, and a store loaded from the old tab's takes it (build review M3) <t>ms
   × draft schema and freshDraft (F §4.6) > a fresh draft is dated next Sunday with every field empty and the F §4.6 defaults <t>ms
   × draft schema and freshDraft (F §4.6) > accepts an empty date and generous strings, and rejects impossible values <t>ms
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
````

**with:**

````ts
 * `normalizePlacement` does on the Liturgy step, and the Bulletin step's
 * fields (printed bulletin PR 2b) always, each text cut to its limit.
 */
import type { components } from "@/lib/api/schema";
import type { ServiceBulletin } from "@/lib/api/types";
import { emptyServiceBulletin, MAX_LENGTH as BULLETIN_MAX } from "@/lib/draft/bulletin";
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
  };
}

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

/** A bulletin as the archive keeps it: every text Word-safe and trimmed, blank part leaders left out. */
function savedBulletin(b: ServiceBulletin, clean: (text: string) => string) {
  const music = (m: ServiceBulletin["prelude"]) => ({ title: clean(m.title), composer: clean(m.composer) });
  return {
    prelude: music(b.prelude),
    postlude: music(b.postlude),
    people: Object.fromEntries(Object.entries(b.people).map(([role, name]) => [role, name === null ? null : clean(name)])),
    leaders: Object.fromEntries(Object.entries(b.leaders).map(([key, name]) => [key, clean(name)]).filter(([, name]) => name !== "")),
    announcements: Object.fromEntries(Object.entries(b.announcements).map(([key, text]) => [key, clean(text)])),
    reading_text: { ot: clean(b.reading_text.ot), nt: clean(b.reading_text.nt) },
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
 *   A draft that is not a saved service (`editing` null), with a real date,
 *   whose music and announcement boxes are all blank or still hold last
 *   week's text unedited, takes the music and the announcements of the
 *   church's latest service dated before its date
 *   (`GET /services/previous-bulletin`), once per date (`carried_for`). A
 *   new date carries again while no music or announcement box was typed in,
 *   edited, cleared or kept (`edited`); after that it never carries again.
 *   The people, the part leaders and the pasted texts never carry. Opening a
 *   saved service never carries.
 * - `bulletinPayload`: the draft's bulletin as `ServiceDraft.bulletin`, the
 *   texts trimmed, the pasted texts of the readings the files print.
 * - `bulletinFromService`: a saved service's bulletin as the draft's.
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
  reading_text: 20_000,
} as const;

export type Piece = "prelude" | "postlude";

function withBulletin(d: DraftV1, next: DraftBulletin): DraftV1 {
  return { ...d, bulletin: next };
}

/** `carried` without `key`: the box was edited or kept. */
function checked(b: DraftBulletin, key: CarryKey): CarryKey[] {
  return b.carried.filter((k) => k !== key);
}

export function setMusic(d: DraftV1, piece: Piece, field: "title" | "composer", value: string): DraftV1 {
  const b = d.bulletin;
  if (b[piece][field] === value) return d;
  return withBulletin(d, { ...b, [piece]: { ...b[piece], [field]: value }, carried: checked(b, piece), edited: true });
}

export function setAnnouncement(d: DraftV1, key: AnnouncementKey, value: string): DraftV1 {
  const b = d.bulletin;
  if (b.announcements[key] === value) return d;
  return withBulletin(d, { ...b, announcements: { ...b.announcements, [key]: value }, carried: checked(b, key), edited: true });
}

/** "Keep as is": last week's text stays, and the box no longer asks to be checked. */
export function keepCarried(d: DraftV1, key: CarryKey): DraftV1 {
  const b = d.bulletin;
  return b.carried.includes(key) ? withBulletin(d, { ...b, carried: checked(b, key), edited: true }) : d;
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
    isValidDateIso(date) &&
    inSupportedRange(date) &&
    d.bulletin.carried_for !== date &&
    !d.bulletin.edited
  );
}

/**
 * Last week's music and announcements in place of the boxes (blank or still
 * carried), each filled box marked "From last week", for `forDate`; the draft
 * unchanged when carrying is no longer due or the date moved meanwhile.
 */
export function applyCarry(d: DraftV1, previous: PreviousBulletin, forDate: string): DraftV1 {
  if (d.readings.date_iso !== forDate || !shouldCarry(d)) return d;
  const p = previous.bulletin;
  const next: DraftBulletin = {
    ...d.bulletin,
    prelude: { ...p.prelude },
    postlude: { ...p.postlude },
    announcements: { ...p.announcements },
    carried_for: forDate,
  };
  return withBulletin(d, { ...next, carried: CARRY_KEYS.filter((key) => filled(next, key)) });
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
  };
}

/**
 * The draft's bulletin as `ServiceDraft.bulletin`: every text trimmed; the
 * people as set (null: the settings' name); the part leaders with a name, in
 * the printed order; the pasted texts of the two readings the files print
 * (`effectivePicks`), so a text pasted for a reading no longer chosen is not sent.
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
  };
}

/** Nothing filled in: what a service saved without a bulletin reads as. */
export function isBlankBulletin(p: ServiceBulletin): boolean {
  return JSON.stringify(p) === JSON.stringify(emptyServiceBulletin());
}

/**
 * A saved service's bulletin as the draft's (`serviceToDraft`): nothing
 * marked "From last week" and no carry (a saved service never carries); each
 * pasted text kept under the reference of the reading it was saved for.
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
    carried: [],
    edited: false,
    carried_for: null,
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
    // A server from before PR 2b (the minutes between the two deploys) sends none.
    bulletin: bulletinFromService(service.bulletin ?? emptyServiceBulletin(), service),
  };
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
const bulletin = z.object({
  prelude: music,
  postlude: music,
  /** This week's name for each person; null follows the bulletin settings, "" is no one this week. */
  people: z.object(Object.fromEntries(PEOPLE.map((key) => [key, text.nullable()])) as Record<Person, z.ZodNullable<typeof text>>),
  /** A part's leader this week, by element key (`bulletin_settings.ELEMENT_KEYS`). */
  leaders: z.record(text, text),
  announcements: z.object(Object.fromEntries(ANNOUNCEMENT_KEYS.map((key) => [key, text])) as Record<AnnouncementKey, typeof text>),
  /** Pasted reading text by the reading's reference, so a changed reading starts with an empty box. */
  pasted: z.record(text, text),
  /** The boxes still holding last week's text, not edited or kept since. */
  carried: z.array(z.enum(CARRY_KEYS)),
  /** A music or announcement box was typed in, edited or kept: last week's never carries in again. */
  edited: z.boolean(),
  /** The date last week's bulletin was looked up for; null: not yet. */
  carried_for: dateIso.nullable(),
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
    edited: false,
    carried_for: null,
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
    !b.edited &&
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
**Expected:** `      Tests  69 passed (69)`; ` Test Files  86 passed (86)`, `      Tests  687 passed (687)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/draft/bulletin.ts frontend/src/lib/draft/bulletin.test.ts frontend/src/lib/draft/schema.ts frontend/src/lib/draft/schema.test.ts frontend/src/lib/draft/migrate.ts frontend/src/lib/draft/migrate.test.ts frontend/src/lib/draft/store.test.ts frontend/src/lib/draft/mapping.ts frontend/src/lib/draft/mapping.test.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/status.test.ts frontend/src/lib/documents.ts frontend/src/lib/documents.test.ts frontend/src/lib/queries/keys.ts frontend/src/lib/queries/keys.test.ts frontend/src/lib/queries/services.ts frontend/src/components/builder/step-progress.tsx
git commit -q -m "Printed bulletin PR 2b: the draft v3 and the bulletin on the client" -m "The draft gains the Bulletin step's fields (version 3; a version 2
draft migrates with an empty bulletin) and the step id. lib/draft/
bulletin.ts edits them, carries last week's music and announcements
into a new draft once per date until a box is edited or kept, builds
the payload (the pasted text of the readings printed), opens a saved
service's, and says what is not filled in or not checked. The payload
holds the bulletin only when something is filled in, so a draft saved
before 2b stays Saved; every body sends it, cut to the limits." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1421 passed, 17 skipped`; frontend `687 passed` in 86 files.

### Task 5: The Bulletin step (S "The Bulletin step"; planning answers 4-7; F §4.7, §4.8; clarifications 2-8, 16)

**Files:**
- Create: `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, `frontend/src/app/(signed-in)/(church)/builder/bulletin/page.tsx`, `frontend/src/components/builder/bulletin/bulletin-step.tsx`, `frontend/src/components/builder/bulletin/use-bulletin-carry.ts`
- Modify: `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/draft/status.test.ts`, `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/lib/draft/steps.ts`, `frontend/src/components/builder/step-progress.tsx`

The builder shell's test renders every step route, the Bulletin step's included, and the step bar's five links; Review's step bar tests move from the fourth link to the fifth.

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
    fail = false;
    await user.click(within(alert).getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Coffee hour" })).toHaveValue("The Example family"));
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

    const toggle = within(group).getByRole("button", { name: "Change who leads a part" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(within(group).queryByRole("textbox", { name: "Sermon" })).toBeNull();
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const sermon = within(group).getByRole("textbox", { name: "Sermon" });
    expect(sermon).toHaveAccessibleDescription("Usually Rev. Alex Example");
    expect(within(group).getByRole("textbox", { name: "Offering" })).toHaveAccessibleDescription("Usually no one");
    await user.type(sermon, "Rev. Guest");
    await waitFor(() => expect(stored().bulletin.leaders).toEqual({ sermon: "Rev. Guest" }));
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
function weekName(draft: DraftV1, settings: BulletinSettings | undefined, role: Person): string {
  return draft.bulletin.people[role] ?? settings?.[role] ?? "";
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
              onChange={(v) => update((d) => setPerson(d, key, settings !== undefined && v === settings[key] ? null : v))}
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
        aria-controls="bulletin-parts"
        onClick={() => setPartsOpen((open) => !open)}
      >
        Change who leads a part
      </Button>
      {partsOpen ? (
        <div id="bulletin-parts" className="grid gap-4">
          <p className="text-sm text-muted-foreground">{PARTS_HELP}</p>
          {ELEMENTS.map(({ key, label }) => {
            const role = settings?.leaders[key];
            const usual = role ? weekName(draft, settings, role) : "";
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
 * service, a real date, nothing on the step's music or announcements typed
 * or kept, not yet looked up for this date), it reads last week's bulletin
 * (`GET /services/previous-bulletin?before=<date>`) and carries its music and
 * announcements in through `autoUpdate` (stamped 1 ms after the draft it
 * changes, so it never outranks typing in another tab), checking again
 * inside the recipe against the latest draft. Only the visible tab carries,
 * as the lectionary fill (`usePageVisible`).
 */
import { useEffect } from "react";

import { usePageVisible } from "@/components/builder/lectionary-sync";
import { applyCarry, shouldCarry } from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { usePreviousBulletin } from "@/lib/queries/services";

export function useBulletinCarry(): { failed: boolean; retry: () => void } {
  const { draft, autoUpdate } = useDraft();
  const date = draft.readings.date_iso;
  const due = shouldCarry(draft);
  const query = usePreviousBulletin(date, due);
  const visible = usePageVisible();
  const data = query.data;

  useEffect(() => {
    if (!due || !visible || data === undefined) return;
    autoUpdate((d) => applyCarry(d, data, date));
  }, [due, visible, data, date, autoUpdate]);

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

- [ ] **Step 4: See them pass (three runs), the suite, types and lint**

Run: the Step 2 command three times, then the suite, typecheck and lint.
**Expected:** three times `      Tests  53 passed (53)`; ` Test Files  87 passed (87)`, `      Tests  692 passed (692)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add 'frontend/src/app/(signed-in)/(church)/builder/bulletin/page.tsx' frontend/src/components/builder/bulletin/bulletin-step.tsx frontend/src/components/builder/bulletin/bulletin-step.test.tsx frontend/src/components/builder/bulletin/use-bulletin-carry.ts frontend/src/lib/draft/steps.ts frontend/src/components/builder/step-progress.tsx frontend/src/test/fixtures/index.ts frontend/src/lib/draft/status.test.ts frontend/src/components/builder/builder-shell.test.tsx frontend/src/components/builder/review/review-send-step.test.tsx
git commit -q -m "Printed bulletin PR 2b: the Bulletin step" -m "A fifth, optional step between Liturgy and Review & send: the prelude
and postlude, who leads (the settings' people, changeable for this
week, and a part's leader behind Change who leads a part), the
announcements, and per reading a box for pasted text. Last week's music
and announcements carry into a new draft, each box marked From last
week until it is edited or kept. The step bar has five steps and says
Optional or how many boxes are still to check." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1421 passed, 17 skipped`; frontend `692 passed` in 87 files.

### Task 6: The Printed bulletin card: the week's fields (planning answers 3, 5, 6; clarifications 7, 9, 16)

**Files:**
- Modify: `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, `frontend/src/components/builder/review/printed-card.tsx`

The card runs the carry, so the two test files that render Review without the builder shell's routes (`review-send-step`, `liturgy-step`) answer `GET /services/previous-bulletin` (`builder-shell` has it since T5).

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
**Expected:** three times `      Tests  78 passed (78)`; ` Test Files  87 passed (87)`, `      Tests  693 passed (693)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/builder/review/printed-card.tsx frontend/src/components/builder/review/review-send-step.test.tsx frontend/src/components/builder/liturgy/liturgy-step.test.tsx
git commit -q -m "Printed bulletin PR 2b: the Printed bulletin card lists the week's fields" -m "The card no longer says the music and the announcements print as
placeholders: it says they come from the Bulletin step, adds the
prelude, the postlude and the announcements to Not filled in (with
this week's people), lists the boxes from last week not yet checked,
and carries last week's in, so a bulletin printed from Review without
opening the Bulletin step has them." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1421 passed, 17 skipped`; frontend `693 passed` in 87 files.

### Task 7: Docs: the manual check items and the spec (planning answers 1-8; clarification 17)

**Files:**
- Modify: `docs/manual-verification.md`, `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`

- [ ] **Step 1: Amend PR 1's item 2 and the spec's "Data model", append the items**

**In `docs/manual-verification.md`, replace:**

````markdown
- [ ] (owner, after PR 1) **2.** In that PDF the readings are printed in full in the translation chosen on step 1, followed by "Scripture readings are from the …"; hymns read like `*HYMN: #409 "God Is Here!"`; the people lines are bold; the music and announcements show as [placeholders] (after PR 2a the church's details and the names come from **Bulletin settings**; a blank one prints nothing).
````

**with:**

````markdown
- [ ] (owner, after PR 1) **2.** In that PDF the readings are printed in full in the translation chosen on step 1, followed by "Scripture readings are from the …"; hymns read like `*HYMN: #409 "God Is Here!"`; the people lines are bold; the music and announcements show as [placeholders] (after PR 2a the church's details and the names come from **Bulletin settings**, after PR 2b the music and the announcements from the **Bulletin** step; a blank one prints nothing).
````

**In `docs/manual-verification.md`, replace:**

````markdown
- [ ] **15.** On **Bulletin settings**, change a field without saving and tap **Back to Review & send**: "Discard unsaved changes?" asks first; **Keep editing** stays with the change, **Discard changes** goes back. Reloading the tab with a change unsaved shows the browser's own warning.
````

**with:**

````markdown
- [ ] **15.** On **Bulletin settings**, change a field without saving and tap **Back to Review & send**: "Discard unsaved changes?" asks first; **Keep editing** stays with the change, **Discard changes** goes back. Reloading the tab with a change unsaved shows the browser's own warning.

### Printed bulletin PR 2b: the Bulletin step

From PR 2b the builder has five steps: **4 Bulletin** comes before
**5 Review & send** (earlier items say "4 Review & send"). Before the merge
the owner runs the steps of `backend/migrations/README.md` → "Before
0006_services_bulletin" (items 16 and 17); after it, the owner's guided check
(one step at a time on the phone) covers the items marked "(owner, after PR
2b)". The results go into `docs/ops-runbook.md` → "Printed bulletin PR 2b
record". Use invented announcements for the checks, or the church's real
ones only on the owner's own phone; record what the page and the files
show, never a name from the prayers and concerns, an email address, a phone
number, a street address or a church id.

- [ ] (owner, before the PR 2b merge) **16.** A green `db-backup` run; the read-only counts (version `0005_services_extras`, saved services, churches); the SQL preview read: one `ADD COLUMN bulletin JSON` between `BEGIN;` and `COMMIT;`, under the 5 s lock timeout.
- [ ] (owner, after PR 2b) **17.** The after-deploy query shows `0006_services_bulletin`, `1` and `with_bulletin` `0` (or the few services saved since), and the counts are unchanged (or grew by those saves).
- [ ] (owner, after PR 2b) **18.** The step bar shows five steps and fits at 375 px with no sideways scroll; **4 Bulletin** says "Optional". On **Bulletin**: **Music**, **Who leads**, **Announcements** and **Reading text**, every field and button easy to tap (44 px).
- [ ] (owner, after PR 2b) **19.** Fill in the prelude and postlude (title and composer), the ushers and counters, the coffee hour and one line of activities, leave the rest blank, and download the printed bulletin from **5 Review & send**: the prelude and postlude print with their composers and the organist's name; the announcements page shows only what was filled in (no heading or line for a blank one); the Printed bulletin card no longer says anything prints as [placeholders] and lists the blank ones ("Not filled in: …"). The Word version shows the same.
- [ ] (owner, after PR 2b) **20.** Under **Who leads**, change one person for this week ("Changed for this week.") and, behind **Change who leads a part**, the Sermon's leader; download again: page 1's header and the Sermon follow the change; **Bulletin settings** still has the usual names.
- [ ] (owner, after PR 2b) **21.** Save the service. Start a **New service** for the next Sunday and open **4 Bulletin**: last week's music and announcements are there, each with "From last week. Check before printing."; **Who leads** shows the usual names and the reading boxes are empty. On **5 Review & send** the card says "From last week, not checked yet: …". Change one box and tap **Keep as is** on another: their notes go, and the card's list shortens.
- [ ] **22.** Paste a reading's text under **Reading text** and download: the PDF prints the pasted text under that reading, with no "Scripture readings are from …" line, and the download fetches only the other reading.
- [ ] **23.** Clear every announcement and download: there is no announcements page in the PDF or the Word version (the card lists "announcements" as not filled in).
- [ ] **24.** Open a saved service from **Services**: its bulletin fields are as saved, nothing says "From last week", nothing from another week comes in, and Review says "Saved". A draft started before PR 2b opens with everything it had (and an empty Bulletin step).
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
  reading_text: {ot, nt}}`, and PR 3 adds `cover_image_id` (PR 2b plan,
  `docs/superpowers/plans/2026-10-03-printed-bulletin-2b.md`). The draft gains the field with a version bump (v2 to v3, migrating with an
````

**In `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`, replace:**

````markdown
  picture id; the per-element leaders and pasted reading texts start empty.
````

**with:**

````markdown
  picture id; the per-element leaders and pasted reading texts start empty. As planned for PR 2b:
  only a draft that is not a saved service, when the Bulletin step or Review & send first shows it
  for its date, until a music or announcement box is typed in, edited or kept; each carried box
  shows "From last week. Check before printing." until it is edited or kept (planning answer 5).
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '^## ' docs/manual-verification.md | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md docs/superpowers/specs/2026-10-02-printed-bulletin-design.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected:** `89 passed in <t>s` (`test_slice1_docs.py` pins the last eight `##` headings, ending `## Printed bulletin`: the new heading is a `###`, so the pin holds); `282:## Printed bulletin`; `4`; `0`; ` 2 files changed, 33 insertions(+), 5 deletions(-)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md docs/superpowers/specs/2026-10-02-printed-bulletin-design.md
git commit -q -m "Docs: printed bulletin PR 2b manual checks" -m "docs/manual-verification.md gains \"### Printed bulletin PR 2b: the
Bulletin step\" under \"## Printed bulletin\": the owner's steps around
migration 0006, the phone check after PR 2b (the five steps, the music
and announcements printed, who leads this week, carry forward with its
check) and the agent's checks (pasted text, no announcements page, an
opened service, an old draft). PR 1's item 2 says where the music and
announcements come from now; the spec's \"Data model\" gains people,
other announcements and when carry forward happens." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1421 passed, 17 skipped`; frontend `693 passed` in 87 files.

- [ ] **Step 4 (controller): Review the batch (T1-T7) and backup push**

One review of the whole batch: the revision is expand-only and its `--sql` is exactly clarification 14's six lines; the README's queries are read-only and match the Postgres test; `ServiceDraft.bulletin` is optional, a `POST` without it stores NULL and a `PUT` without it keeps the saved one; every bulletin text is Word-safe and none is logged; `previous_bulletin` filters on the church, skips undated rows and takes the latest date then the latest save; the printed bulletin prints nothing for a blank field and leaves the announcements page out when it is empty, in both renderers; a pasted reading is neither fetched nor charged; the draft's 2 → 3 migration keeps everything and a "Saved" draft stays Saved; carry forward never touches a saved service or an edited box and runs only through `autoUpdate`; the step's fields are 44 px and labelled; the copy is clarification 16's. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

### Task 8: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

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

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `PR 2a record on main: 1` (it rides along: Step 3's list has `M docs/ops-runbook.md`; `0` if a records PR merged it meanwhile, and then that line is absent); `6`; `5`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 8)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner. **If `main` gained a migration** (the last count is not 5), stop: `0006` must be renumbered onto the new head (F §3.5 chain rule) before anything else, and the owner told.

- [ ] **Step 2 (agent): Both suites, Postgres, the frontend three times, types, lint, the build, a sample booklet**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/builder/bulletin")
(cd backend && ../.venv/bin/python -c "
import datetime, bulletin_settings as bs, printed_bulletin as pb, printed_pdf, printed_docx, service_bulletin as sb
from service_output import ResolvedService, ResolvedHymn
r = ResolvedService(service_date=datetime.date(2026, 10, 11), hymns={'opening': ResolvedHymn('God Is Here!', 409), 'response': None, 'closing': None}, liturgy={'call_to_worship': 'Leader: Lift up your hearts. People: We lift them up.'}, sermon_title='Who Said?')
s = bs.read({'bulletin': {'address_lines': ['100 Example Street', 'Springfield, ST 00000'], 'phone': '(555) 010-0100', 'service_time': '10:30 a.m.', 'worship_leader': 'Rev. Alex Example', 'liturgist': 'Sam Sample', 'organist': 'Jordan Doe'}})
w = sb.read({'prelude': {'title': 'Morning Voluntary', 'composer': 'Pat Example'}, 'postlude': {'title': 'Festive Postlude', 'composer': 'Lee Sample'}, 'people': {'worship_leader': 'Rev. Guest'}, 'leaders': {'sermon': 'Pat Example'}, 'announcements': {'ushers': 'Sam Sample, Jordan Doe', 'deacon': 'Alex Example', 'coffee_hour': 'The Example family', 'activities': 'Tuesday: Bible study at 10 a.m.\nWednesday: Choir at 7 p.m.', 'prayer_concerns': 'For all who are ill.', 'collection': 'Canned goods for the food pantry.', 'other': 'The office is closed on Monday.'}, 'reading_text': {'nt': 'Jesus said, What do you think?'}})
ps = pb.PrintedService('Example Church', r, pb.Reading('Psalm 25:1-9', 'In you, Lord, I put my trust. ' * 30), pb.Reading('Matthew 21:23-32', w.nt_text, pasted=True), 'World English Bible (WEB)', s, w)
open('<scratch>/printed2b-sample.pdf', 'wb').write(printed_pdf.render_pdf(ps)); open('<scratch>/printed2b-sample.docx', 'wb').write(printed_docx.render_docx(ps)); print('sample written')
")
```

**Expected:** `1421 passed, 17 skipped in <t>s`; three times ` Test Files  87 passed (87)` and `      Tests  693 passed (693)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s`, a route line `○ /builder/bulletin`, and no `Error` (a font `Failed to fetch` only: say so and rely on CI); `sample written`. With a local, throwaway Postgres also `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `17 passed, 1421 deselected`. Open the sample PDF and look at it: two sides; page 1's header with "Rev. Guest, Worship Leader", "PRELUDE: ‘Morning Voluntary’" with "Jordan Doe" and "- Pat Example", the NT reading "Jesus said, What do you think?" with no credit line, "SERMON: “Who Said?”" with "Pat Example"; page 2 ending with the postlude and "*Congregation stands if able"; page 3 the announcements, each filled field, "OTHER ANNOUNCEMENTS" last. Attach both samples to the owner's message in Step 4 if the channel allows files, else describe them.

- [ ] **Step 3 (agent): The API files match, the preview, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0005_services_extras:0006_services_bulletin --sql 2>/dev/null | grep -v -e '^--' -e '^$')
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/service_bulletin.py backend/printed_bulletin.py backend/usecases/archive.py backend/usecases/documents.py backend/repos/services.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations/env.py backend/service_archive.py backend/service_output.py backend/bulletin_settings.py backend/api/routes/documents.py .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); the six preview lines of clarification 14 exactly; `imports grep exit 1`; `raw html grep exit 1`; exactly these paths (without `M docs/ops-runbook.md` when Step 1 printed `0`):
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
A	frontend/src/app/(signed-in)/(church)/builder/bulletin/page.tsx
M	frontend/src/components/builder/builder-shell.test.tsx
A	frontend/src/components/builder/bulletin/bulletin-step.test.tsx
A	frontend/src/components/builder/bulletin/bulletin-step.tsx
A	frontend/src/components/builder/bulletin/use-bulletin-carry.ts
M	frontend/src/components/builder/liturgy/liturgy-step.test.tsx
M	frontend/src/components/builder/review/printed-card.tsx
M	frontend/src/components/builder/review/review-send-step.test.tsx
M	frontend/src/components/builder/step-progress.tsx
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/types.ts
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
`0`; the subjects oldest first: `Runbook: printed bulletin PR 2a record (owner's phone check)` (when it rides along), the plan commits (`WIP plan: printed bulletin PR 2b …`, `Plan: printed bulletin PR 2b (the Bulletin step)` and any later plan commit), then T1-T7's seven subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> The Bulletin step (printed bulletin PR 2b) is verified on this machine: backend 1421 passed, 17 skipped (1395 and 16 before; the new skipped one is a database check that CI runs on Postgres); frontend 693 tests in 87 files (675 in 85 before), three runs in a row; typecheck, lint and the production build are clean. It adds a fifth step, "4 Bulletin", with the prelude and postlude, who leads this week, the announcements and a box to paste a reading's text; a new service starts from last week's music and announcements, each marked "From last week. Check before printing."; the printed bulletin prints them all and leaves out anything blank (and the announcements page when there are none). It saves them with the service, which needs one database change, migration 0006: one new empty column. Before it merges I will ask you for the backup, the counts and a look at the SQL, one at a time. May I open the pull request as a **draft** titled "Printed bulletin PR 2b: the Bulletin step", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/printed2b-pr-body.md" <<'BODY'
Printed bulletin PR 2b: the Bulletin step and the week's own fields (PR 2 planning answers of 2026-10-02). Spec: docs/superpowers/specs/2026-10-02-printed-bulletin-design.md. Plan: docs/superpowers/plans/2026-10-03-printed-bulletin-2b.md. One migration (0006_services_bulletin); no new package or variable.

- Migration 0006_services_bulletin (expand-only): services.bulletin JSON NULL. No backfill. env.py's 5 s lock timeout applies. Before the merge: a backup, read-only counts and the SQL preview (backend/migrations/README.md, "Before 0006_services_bulletin").
- service_bulletin (pure): the prelude and postlude, this week's people and part leaders, the announcements (with Other announcements), the pasted reading text; read tolerantly.
- The printed bulletin prints them: a blank field prints nothing, no announcements page when all are blank, a pasted reading with no credit line and no fetch. PR 1's weekly placeholders are gone (the cover picture's stays until PR 3).
- API: ServiceDraft.bulletin (optional: a POST without it stores NULL, a PUT without it keeps the saved one), ServiceOut.bulletin, GET /services/previous-bulletin?before= for carry forward.
- Frontend: the draft v3 (a v2 draft migrates with an empty bulletin and stays Saved), the Bulletin step (/builder/bulletin; five steps in the bar), carry forward of last week's music and announcements with "From last week. Check before printing." and Keep as is, the Printed bulletin card's lines.
- docs/manual-verification.md: "### Printed bulletin PR 2b: the Bulletin step".

Later: PR 3 (the cover picture), 6a (Settings).

Tests: backend 1395 → 1421 passed, 16 → 17 skipped; frontend 675 → 693 in 85 → 87 files

After merge (Task 9): the owner's after-deploy check (one read-only query) and a guided phone check, then a "Printed bulletin PR 2b record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Printed bulletin PR 2b: the Bulletin step" \
  --body-file "<scratch>/printed2b-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1421 passed, 17 skipped`, backend-postgres `17 passed, 1421 deselected` (after its `alembic upgrade head`, `alembic check`, `downgrade base`, `upgrade head` steps, now through `0006`), frontend `693 passed` in 87 files. Then send: "PR #<N> is green: backend 1421 passed, 17 skipped; the Postgres job ran the migration up, down and up again and passed its 17 tests; 693 frontend tests in 87 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you, after the backup, the counts and the SQL check." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_migrations.py` (the 0006 tests, the README pin), `test_schema_check.py`, `test_api_app.py`, `test_services_postgres.py`, CI's alembic cycle | T1 |
| `test_service_bulletin.py`, `test_printed_bulletin.py`, `test_printed_render.py` | T2 |
| `test_usecase_archive.py`, `test_api_services.py`, `test_api_printed.py`, `test_no_streamlit_in_core.py`, `test_openapi_contract.py`, `test_route_guards.py` | T3 (`test_api_printed.py`'s 2a test: T2) |
| `bulletin.test.ts`, `schema.test.ts`, `migrate.test.ts`, `store.test.ts`, `mapping.test.ts`, `documents.test.ts`, `keys.test.ts`, `status.test.ts` | T4 (`status.test.ts`'s steps test: T5) |
| `bulletin-step.test.tsx`, `builder-shell.test.tsx` | T5 |
| `review-send-step.test.tsx`, `liturgy-step.test.tsx` | T6 (the step bar's indexes: T5) |
| `test_slice1_docs.py`, `test_docs.py` | T7 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, printed bulletin PR 2b final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1421 passed, 17 skipped`; frontend `693 passed` in 87 files.

### Task 9: Before the merge (backup, counts, SQL), the merge, the after-deploy check, the phone check, the record (OWNER + agent)

The owner's steps go **one at a time** (send one, wait for the report or "next"). The agent writes each result into `<scratch>/printed2b-t9-results.md` (not committed). Record numbers and what the screens and files showed, never a token, an email address, a phone number, a street address, a church id, a database URL or a name from the prayers and concerns. The queries are the ones in `backend/migrations/README.md` → "Before 0006_services_bulletin" (pinned by T1's tests); copy them from there.

**Files:** Modify (the records PR, Step 11): `docs/ops-runbook.md`: insert `### Printed bulletin PR 2b record` right before `## Backups` (after the last `###` record above it; today "Printed bulletin PR 2a record", whose table's last row starts `| Follow-ups |`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER, then agent): The backup**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send:

> PR #<N> (printed bulletin PR 2b, the Bulletin step) is ready and green. Before it merges you asked for three checks, as for migration 0005; here is the first. May I start a fresh database backup now (the db-backup workflow on main, about a minute)? Nothing else happens yet.

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

Send: "The backup is green, the counts are recorded and you have read the SQL. May I merge PR #<N> with a merge commit? Railway then runs the migration before the new version starts. For the few minutes until both the website and the server are updated, please don't build or download a service; I will tell you when it is live, then ask for one more read-only query and a short phone check, one step at a time." On a clear yes (not replayed):

```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both.

- [ ] **Step 5 (agent, then OWNER): The deploy and the after-deploy check (manual-verification item 17)**

About three minutes after the merge (not replayed):

```bash
curl -s https://church-production-74ca.up.railway.app/health/ready; echo
curl -s https://church-production-74ca.up.railway.app/openapi.json | grep -c '"/services/previous-bulletin"'
curl -s -o /dev/null -w '%{http_code}\n' "https://church-production-74ca.up.railway.app/services/previous-bulletin?before=2026-10-11"
```

**Expected:** `{"ok":true,"db":"ok"}` (in production this answers 503 `schema_behind` while the database is behind the release, so `ok` means `0006` is applied and the new release is live); `1`; `401` (the route exists and wants a sign-in). If `/openapi.json` still lacks the route, wait a minute and retry; after ten minutes, ask the owner to open Railway → the API service → Deployments and read the newest deployment's status. Then send, with README step 4's query in a code block, and step 2's query again:

> The new version is live. One more read-only check: in the SQL Editor, run the first query below; it should show 0006_services_bulletin, 1, and 0 (or a small number, if someone saved a service since). Then run the counting query from before again; the numbers should be the same as last time, or a little higher if a service was saved meanwhile. Also, if you have Railway open: the newest deployment's logs should include a line "Running upgrade 0005_services_extras -> 0006_services_bulletin". What do you see?

Record the values. A version other than `0006_services_bulletin`, or fewer services than before: stop and look before anything else.

- [ ] **Step 6 (OWNER, then agent): Phone, step 1 of 4: the step (item 18)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. Open the Service Builder. Does the step bar at the top show five steps, with no sideways scrolling? Tap step 4, **Bulletin**: does it say "Optional" in the step list, and show **Music**, **Who leads**, **Announcements** and **Reading text**? Are the fields and buttons easy to tap?

- [ ] **Step 7 (OWNER, then agent): Phone, step 2 of 4: the music and announcements printed (item 19)**

> On **Bulletin**, fill in this Sunday's prelude and postlude (title and composer) and the announcements you have (leave any you don't use blank). Then go to **5 Review & send** and tap **Download printed bulletin**. Do the prelude and postlude print with their composers and the organist's name? Does the announcements page show what you filled in, and nothing for the blank ones? Does the Printed bulletin card still say anything about [placeholders]? Then tap **Download Word version**: does it show the same?

Record the answers (never the announcements' text).

- [ ] **Step 8 (OWNER, then agent): Phone, step 3 of 4: who leads this week (item 20)**

> Back on **Bulletin**, under **Who leads**, change one person just for this week (for example a guest preacher as worship leader; "Changed for this week." shows), and tap **Change who leads a part** and type a name for the **Sermon**. Download the printed bulletin again: do page 1's header and the Sermon line show the change? Then open **Bulletin settings**: are your usual names unchanged? (Tap **Undo the change** afterwards if this was only a test.)

- [ ] **Step 9 (OWNER, then agent): Phone, step 4 of 4: carry forward (item 21)**

> On **5 Review & send**, tap **Save to archive**. Then open the menu (⋮) → **New service** (it will be for the next Sunday) and go to **4 Bulletin**: are last week's music and announcements there, each with "From last week. Check before printing."? Are **Who leads** back to the usual names and the reading boxes empty? Change one of the boxes, and tap **Keep as is** on another: do their notes go away? On **5 Review & send**, does the card list "From last week, not checked yet: …" for the rest? You can then delete this test service from **Services** if you don't want it.

- [ ] **Step 10 (agent): The agent's own checks (items 22-24), the results**

On the production URL, in a test church the agent may change (one of the two slice 1 test churches the owner kept, never the owner's own church), signed in as its owner if the session has a test account, else skipped and recorded as "not run": item 22 (paste a reading's text; the PDF prints it with no credit line), item 23 (clear every announcement; no announcements page), item 24 (open a saved service; its fields as saved, nothing from last week, "Saved"). Then write each step's result, with the date, into `<scratch>/printed2b-t9-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 11 (agent): Write the record**

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
### Printed bulletin PR 2b record

Printed bulletin PR 2b (the Bulletin step: the prelude and postlude, who
leads this week, the announcements and pasted reading text, carried
forward from last week with a check, printed in the PDF and the Word
version, a blank one printing nothing; saved with the service in
`services.bulletin`) merged as PR #<N>, the second half of printed
bulletin PR 2 (PR 2 planning answers of 2026-10-02). Production moved
from `0005_services_extras` to `0006_services_bulletin` (one empty
nullable column on `services`). The steps follow
`backend/migrations/README.md` → "Before 0006_services_bulletin", and the
owner's check covered the "(owner, after PR 2b)" items of
`docs/manual-verification.md` → "Printed bulletin". No token, email
address, phone number, street address, church id, database URL or name
from the prayers and concerns is recorded here.

| Step | Result | Date |
|---|---|---|
| 1. Backup | `db-backup` run <run URL>: success, artifact `db-backup` (<bytes> bytes, encrypted) | <date> |
| 2. Counts before (SQL Editor, read-only) | version `0005_services_extras`; <n> saved services; <n> churches | <date> |
| 3. SQL preview | Rendered from the PR's code without a database: the six lines of the README (one `ADD COLUMN bulletin JSON`, under the 5 s lock timeout); read by the owner: <answer> | <date> |
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`; `/openapi.json` lists `/services/previous-bulletin`; signed out: 401. <Railway log line "Running upgrade 0005_services_extras -> 0006_services_bulletin" seen by the owner. / Not checked.> | <date> |
| 4. After the deploy (read-only) | `0006_services_bulletin`, `1`, with_bulletin <n>; counts again: <unchanged / …> | <date> |
| 5. The step (phone: <phone and browser>) | <Five steps, no sideways scroll; Bulletin "Optional" with its four groups; easy to tap. / …> | <date> |
| 6. Music and announcements printed | <The prelude and postlude with composers and the organist; only the filled announcements; no [placeholders] note; the Word version the same. / Differences: …> | <date> |
| 7. Who leads this week | <The header and the Sermon followed the change; the settings unchanged. / …> | <date> |
| 8. Carry forward | <Last week's music and announcements came in, each marked; who leads and the reading boxes empty; an edit and Keep as is cleared their notes; the card listed the rest. / …> | <date> |
| Agent checks | <Items 22-24 in a test church: <results>. / Not run: <why>.> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: printed bulletin PR 3 (the cover picture), 6a (Settings). Still open from PR 1: the print test at the church | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye: the second grep below catches an email address and a "(555)"-style phone, not a street address, a phone number written another way or a name, so check that none is in it. Then (not replayed):

```bash
sed -n '/^### Printed bulletin PR 2b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Printed bulletin PR 2b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|\([0-9]{3}\)'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: printed bulletin PR 2b record (backup, counts, SQL preview, merge, migration 0006, phone check)" -m "Records printed bulletin PR 2b (PR #<N>): the backup, the read-only
counts and the SQL preview before the merge, the merge and the deploy of
0006_services_bulletin, the after-deploy check and the owner's four-step
phone check. No token, email, phone number, address, church id, database
URL or name from the prayers and concerns is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 12 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The printed bulletin PR 2b record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: printed bulletin PR 2b record" \
  --body "Records printed bulletin PR 2b (PR #<N>) in docs/ops-runbook.md → Printed bulletin PR 2b record: the backup, the counts and the SQL preview before the merge, the deploy of 0006_services_bulletin and the owner's checks. No token, email, phone number, address, church id, database URL or name from the prayers is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Printed bulletin PR 2b is live and recorded; <n> follow-ups. Next: the PR 3 plan (the cover picture)."

- [ ] **Step R (only if the release must come out): Revert, keeping `0006`**

On the owner's yes for each outward command (README "Reverting 2b"): a branch `claude/revert-printed-2b` from `origin/main`; `git revert -m 1 --no-commit <merge sha>`; then put back the schema and its tests from the merge commit, `git checkout <merge sha> -- backend/migrations/versions/0006_services_bulletin.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py`; a commit "Revert printed bulletin PR 2b (PR #<N>), keeping migration 0006" with the trailer; both suites (`1399 passed, 17 skipped`: the baseline plus T1's four and its Postgres one; `675 passed` in 85); a PR, CI, and the merge on the owner's yes; record it in the record. Never `alembic downgrade` production for this: the database stays at `0006_services_bulletin`, which the older code ignores. The weekly fields saved meanwhile stay in the column, unread, and come back with 2b; a draft already migrated to version 3 in a browser is a "future version" to the older code, which backs it up and starts a fresh draft (its "restore failed" notice), so the revert costs each member's unsaved draft once; say so to the owner before reverting.

Expected counts after this task: backend `1421 passed, 17 skipped` on `main`; frontend `693 passed` in 87 files. The records PR adds no test.

---
## Build notes

**How this plan was written (2026-10-03).** Each task's code was built and run in a throwaway worktree of the branch head (`eadd365`: `9c731e1` and the plan's first commit), with the repo's `.venv` (a symlink), a hard-linked copy of `frontend/node_modules` (`cp -al`; Turbopack's production build refuses a `node_modules` symlink that points outside the project) and a local, throwaway Postgres 16 (`initdb` under `/var/lib/postgresql`, port 5433; CI uses 17), one commit for each task's tests and one for its code. The directives were generated from those commits by a script (a new file as **Create**, an addition at the end of a file as **Append**, every other change as **In … replace** with the context grown until the block occurs once in the file as it stands at that point), so the plan's blocks are the built code. While building:
- **`JSON` stores `None` as JSON `null`.** The first Postgres run of the owner's after-deploy query counted three services `WITH bulletin IS NOT NULL` where one had a bulletin: SQLAlchemy's `JSON` type writes a Python `None` as the JSON value `null` unless `none_as_null=True`. The model's column is `JSON(none_as_null=True)` (no DDL change: `alembic check` stays clean), so a service saved without a bulletin is SQL NULL, as the README's query assumes.
- **5a-2's 0005 test upgraded to `head`;** with 0006 it saw the new column too. It now upgrades to `0005_services_extras` (T1's tests), and 5a-2's Postgres test of the 0005 queries expects the head's version.
- **`IsoDate` needs `Annotated[IsoDate, Query()]`.** Written as `before: IsoDate = Query(...)`, FastAPI accepted `2026-10-04T00:00:00` (the shape check did not run); in the `Annotated` form, as `/lectionary/readings` has it, it is the 422 the T3 test expects.
- **"Edited" is a flag, not a comparison.** The first carry rule ("every box blank or still carried") treated a carried box the user cleared as untouched, so a date change would have carried it back in; T4's test of a cleared box caught it. `bulletin.edited` is set by any edit or Keep as is (clarification 7).
- **The fingerprint leaves an empty bulletin out.** With the bulletin always in `draftToServicePayload`, every draft "Saved" before 2b would have turned "Unsaved changes" after the v3 migration; T4's migration test pins that it stays "Saved".
- **The regenerated types need the fixture in the same commit.** `ServiceOut.bulletin` is required, so T3 adds `serviceBulletin()` to `savedService()` and the type names to `types.ts`; without it T3's commit would leave typecheck failing until T4.
- **A sample booklet** (T8 Step 2's snippet) rendered to images: side 1 the cover and page 1 (the week's worship leader in the header, the prelude with the organist and the composer, the pasted NT text with no credit line, the Sermon's week leader), side 2 page 2 (the postlude, the stand note) and page 3 (the announcements, "OTHER ANNOUNCEMENTS" last). Read back as the tests do.
- **CI's alembic cycle by hand** on the local Postgres: `upgrade head`, `check` (`No new upgrade operations detected.`), `downgrade base`, `upgrade head`, `check`: all clean, before and after the `none_as_null` change.

**Replay of the finished plan (2026-10-03).** The directives of T1-T7 were applied in order (by a script that parses the plan's **Create**, **Append** and **In … replace** blocks step by step) onto a fresh detached worktree of the branch head (`8317032`: `9c731e1` and the plan's WIP commits on `origin/main` `1b0b7a3`), with the repo's `.venv`, a hard-linked copy of `frontend/node_modules` and the local Postgres 16 (`TEST_DATABASE_URL`). Each step's commands were run as written and each task committed with its Step 5 (Step 3 for T7) block:
- All 195 directives applied (T1 8 + 5, T2 17 + 19, T3 9 + 27, T4 27 + 39, T5 18 + 9, T6 8 + 5, T7 4); every Replace anchor occurred exactly once. After T7, `backend`, `frontend/src` and `docs` (but the plans) equaled the build worktree's (`diff -r`: empty), and `git status` was clean after every commit.
- Baselines before T1: backend `1395 passed, 16 skipped`; Postgres-marked `16 passed, 1395 deselected`; frontend `675 passed` in 85 files.
- Every "see it fail" output is quoted from this replay (times as `<t>`): T1 `15 failed, 56 passed, 4 skipped`; T2 the three collection errors and `1 failed, 11 passed`; T3 `10 failed, 65 passed`; T4 eight failures and four files that cannot load (`8 failed | 23 passed (31)`); T5 `3 failed | 34 passed (37)` with two files that cannot load; T6 `3 failed | 75 passed (78)`.
- Every count matched the table: backend 1399, 1411, 1421 (17 skipped from T1); Postgres-marked `17 passed, 1399 deselected`, `… 1411 …`, `… 1421 deselected`; T1's files `75 passed, 4 skipped` and the six preview lines; T2's `44 passed` and `placeholders grep exit 1`; T3's `75 passed`, the OpenAPI export and `gen:api` `2 files changed, 523 insertions(+), 1 deletion(-)`, frontend still `675` in 85, typecheck 0, lint 0; frontend 687 in 86, 692 in 87, 693 in 87; T4's files `69 passed`, T5's `53 passed` and T6's `78 passed` three times each, no flaky run; typecheck 0 and lint 0 after every frontend task; T7 `89 passed`, `282:## Printed bulletin`, `4`, `0`, `2 files changed, 33 insertions(+), 5 deletions(-)`.
- T8 Steps 1-3 in the replay worktree: 6 revision files; regenerating `openapi.json` and `schema.d.ts` changed nothing; the imports and raw HTML greps exit 1; the 57 paths exactly (with `M docs/ops-runbook.md`); `0` paths among `env.py`, `service_archive.py`, `service_output.py`, `bulletin_settings.py`, `api/routes/documents.py`, the workflows, the packages, `app.py` and Streamlit; every commit has the trailer; no em dash in any added line outside the plans; the production build `✓ Compiled successfully` with `○ /builder/bulletin`. CI's alembic cycle on the local Postgres (`upgrade head`, `check`, `downgrade base`, `upgrade head`, `check`): clean.
- Fixed in the plan by the first replays: an anchor unique only with its final newline (`created_by: Optional[AuthorOut]` in `schemas.py`), a deleted line that left a blank one (`version: 2,` in `mapping.test.ts`), T2's placeholder grep (now `--exclude-dir=tests`: the test's own list of what must be gone matched), and the quoted outputs (vitest's "Failed Tests n" line, the export's "Wrote …" line).
- Not run while planning: the pushes, the PR and CI, the backup, the owner's queries on production, the merge, Railway's and Vercel's deploys and the phone check (T9).

## Spec coverage

| Owner answer or S item | Task(s) and tests |
|---|---|
| Planning answer 1: 2b is the step, the weekly fields, pasted text, carry forward, the draft v3 and 0006 | T1-T7; T8 Step 3 (the paths; nothing in the Bulletin settings, the Word copies, the packages, the workflows or Streamlit) |
| Planning answer 3: a blank field prints nothing; the card lists what is empty | T2 `test_a_blank_weekly_field_prints_nothing`, `test_with_every_announcement_blank_the_announcements_page_is_left_out`; T3 `test_the_church_s_bulletin_settings_print_for_every_member` (none sent, none printed); T4 "lists the blank standing fields, this week's people as changed, then the prelude, postlude and announcements"; T6 "lists the bulletin settings still blank…", "carries last week's…" |
| Planning answer 4: the announcements with "Other announcements" | T2 `test_the_cover_and_the_back_page` (the page in order, "OTHER ANNOUNCEMENTS" last); T5 "shows the music, who leads, the announcements…" |
| Planning answer 5: carry forward with a check | T3 `test_last_week_s_bulletin_is_the_latest_service_dated_before_the_date`, `test_a_service_saved_before_2b_carries_an_empty_bulletin`, `test_last_week_s_bulletin_carries_the_music_and_the_announcements`; T4 the three "carry forward" tests and "an edit or Keep as is clears…"; T5 "carries last week's…", "never carries into a saved service…"; T6 "carries last week's music and announcements in, lists what to check, and prints them" |
| Planning answer 6: optional, never blocks | T4 "the Bulletin step's status" (never in Still to do); T5 (the bar says Optional; `builder-shell` Review's Still to do unchanged); T6 (downloads enabled) |
| Planning answer 7: who leads, this week's change, "Change who leads a part" | T2 `test_this_week_s_people_and_part_leaders_print_over_the_settings`; T3 the printed test (Rev. Guest, no liturgist, Pat Example on the Sermon); T4 the payload test; T5 "shows the three people from the bulletin settings…" |
| Planning answer 8: backup, counts, preview, after-deploy check, one at a time | T1 `test_offline_sql_for_0006_is_one_column_add_under_the_timeouts`, `test_the_readme_shows_the_0006_preview_exactly`, `test_the_owner_s_read_only_queries_around_0006`; T9 Steps 1-5 |
| Answer 5 and S "Scripture text": pasted text wins over fetched | T2 `test_pasted_reading_text_prints_and_leaves_the_credit_line_out`; T3 `test_the_week_s_fields_print_and_a_pasted_reading_is_neither_fetched_nor_charged`; T4 (by reference); T5 "has a box per reading…" |
| S "Data model": the draft v3, `ServiceDraft.bulletin` optional, `services.bulletin` in 0006 | T1 `test_0006_adds_the_nullable_bulletin_column_and_keeps_rows`, `test_0006_downgrade_gives_back_the_0005_services_table`, the head and drift tests; T3 `test_a_save_stores_the_week_s_bulletin_word_safe_and_never_logs_it`, `test_no_bulletin_sent_stores_none_and_a_replace_without_one_keeps_the_saved_one`, `test_the_week_s_bulletin_is_saved_and_opened_and_an_older_client_keeps_it`, the 422 cases; T4 the schema and migration tests, "opens a saved service's bulletin fields Saved…" |
| S "The Bulletin step": the fifth step, fits 375 px | T5 (`grid-cols-5`, `h-11` fields; `builder-shell` five links and footers); T9 Step 6 |
| F §4.6 (never destroy typed input; versioning) | T4 (carry only through `applyCarry`'s checks; 2 → 3 keeps everything); T5 (`autoUpdate`) |
| F §2.5 (logs without text) | T3 the archive and printed tests (no prayer text in a log line) |
| Layering (no FastAPI or Streamlit below the API) | T3 `test_no_streamlit_in_core.py` (`service_bulletin` added); T8 imports grep |
| OpenAPI and types regenerated | T3 Step 4; T8 Step 3; `test_openapi_contract.py` |
| Answer 10: a guided phone check after each PR | T9 Steps 6-9; `docs/manual-verification.md` "### Printed bulletin PR 2b: the Bulletin step" (T7) |

S items **not** in 2b: the cover picture (`cover_image_id`, "Keep last week's picture", `bulletin_images`, migration `0007_bulletin_images`: PR 3); the Bulletin settings' move into Settings (6a).

## Follow-ups (not in 2b)

- The summary panel (the bottom sheet and the `lg` column) shows no Bulletin block; the step bar's status covers it. A block could list the music and the announcement count.
- A part cannot be set to "no one" for a single week from the step (a blank field follows the usual leader; clarification 4); Bulletin settings does it for every week.
- PR 3 adds `cover_image_id` to `ServiceBulletin` (the model refuses unknown fields) and carries it forward with the music and announcements.
- The deploy window (Risks): a field the new frontend sends is refused by the old API for the minutes between the two deploys. A general fix (the API ignoring unknown fields of a newer client for a release) is a platform decision, not 2b's.

## Questions for the owner

Your answers of 2026-10-02 (the ten answers, layout B, the PR 1 plan's twelve, the eight PR 2 planning answers) and of 2026-10-03 (the PR 2a plan's fourteen) are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **A fifth step, "Bulletin", before Review & send** (clarification 2): the step bar shows five steps (they fit a phone screen; the line above them reads "Step 4 of 5 · Bulletin"), and Review & send becomes step 5. The Bulletin step's status is "Optional", or "2 to check" while boxes from last week are unchecked; it never appears in "Still to do" and never turns off a download or Save. Recommended: accept.
2. **Music** (clarification 3): a title and a composer for the prelude and the postlude, printed as on your bulletin ("PRELUDE: ‘title’", the organist's name on the right, "- composer" under it). A piece with neither title nor composer leaves the whole line out. Recommended: accept.
3. **Who leads this week** (clarification 4): the worship leader, liturgist and organist show your Bulletin settings' names; changing one here is for this week only ("Changed for this week.", with **Undo the change**), and clearing one means no one this week. Behind **Change who leads a part**, a name for any part, this week only (each shows "Usually {name}"); a blank one keeps the usual leader, so setting "no one" for a single part is done in Bulletin settings. The settings themselves never change from this step. Recommended: accept.
4. **The announcements** (clarification 5): ushers and counters, deacon of the week and coffee hour as one line each, as on your bulletin; activities, prayers and concerns, items for collection and other announcements as free text that keeps your line breaks, each under its heading; "Other announcements" prints last under "OTHER ANNOUNCEMENTS". Recommended: accept.
5. **With no announcements at all, no announcements page** (clarification 6): a blank announcement prints nothing (no heading, no line), and when every one is blank the page is left out of the PDF and the Word version (the bulletin is a page shorter; the card lists "announcements" as not filled in). The other choice is a page with only "ANNOUNCEMENTS" and the date. Recommended: leave the page out.
6. **What carries forward, and from where** (clarification 7): a new service starts from the music and the announcements of your latest saved service dated before it (the latest date, then the latest save). This week's names, the part leaders and pasted readings start empty. If the latest service was saved before this update (or with nothing filled in), nothing carries, even if an older one had announcements. Recommended: accept.
7. **When it carries, and "Keep as is"** (clarification 7): it happens when a new service (never one opened from Services) is shown on the Bulletin step or on Review & send; if you then change the date before touching any music or announcement box, it carries again from the right week; once you type in, change, clear or keep a box, it never carries again for that service. Each carried box says "From last week. Check before printing." until you change it; this plan adds a **Keep as is** button beside it so a box that is right need not be retyped (your answer 5 said "until it is edited"). Recommended: yes, add Keep as is.
8. **The Printed bulletin card** (clarification 9): "For now, the music and the announcements print as [placeholders]." goes; it says "The music, the announcements and this week's changes to who leads come from the Bulletin step."; "Not filled in: …" adds prelude, postlude and announcements (and counts this week's names); and "From last week, not checked yet: …" lists the boxes still to check, above the download buttons. Recommended: accept.
9. **Pasted reading text** (clarification 8): one box per printed reading ("First Reading: …", "New Testament Reading: …"); the text stays with that reading (pick another reading and its box is empty); it prints instead of the text the app fetches, the app does not fetch that reading, and the line "Scripture readings are from the …" is left out when any reading is pasted (paste the translation's own notice with the text if it asks for one). Recommended: accept.
10. **Saving** (clarification 10): the Bulletin step's fields are saved with the service and come back when you open it from Services; a change to them shows "Unsaved changes". A service saved before this update stays "Saved". Recommended: accept.
11. **Prayers and concerns are kept with the service** (clarification 15): like the rest of a saved service, any member of your church who opens it can read them; they are never written to the app's logs, and the check and the record never copy a name from them. Recommended: accept.
12. **The checks around the merge** (clarification 14; Task 9): as for migration 0005, one at a time: I start the backup on your yes; you run one read-only counting query; I show you the six lines of SQL (one new empty column) and explain them; after the deploy, one more read-only query, then four short phone steps. If this PR ever has to be undone, the new column stays (empty or holding the saved fields, harmless), and each member's unsaved draft starts fresh once. Recommended: accept.
13. **The limits** (clarifications 3-5, 8): titles 200 characters, composers and names 100, ushers and coffee hour 200, deacon 100, activities, prayers and other announcements 4000 each, collection items 2000, a pasted reading 20 000. Recommended: accept.
14. **A few minutes after the merge** (Risks): until both the website and the server have updated (a few minutes), a page reloaded early can answer "The request was not valid." on a save or download. I will tell you when both are live before the phone check. Recommended: accept.
15. **The Word copies stay as they are** (clarification 18): the bulletin copy and the pastor's copy (the working files) do not get the music or the announcements; the printed bulletin's Word version has them. Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T8); the backup on your yes, the counts and the SQL check, the merge on your yes, the after-deploy query, the four phone steps and the records PR (T9).
