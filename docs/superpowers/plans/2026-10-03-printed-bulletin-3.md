# Printed Bulletin PR 3: the Cover Picture

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship printed bulletin PR 3, **the cover picture** (spec answer 4; PR 3 planning answers of 2026-10-03, "all recommended, the printer is color"), as **two PRs, server first** (planning answer 1, as PR 2b): **PR 3a** (T1-T6: migration `0007_bulletin_images` with the owner's before and after steps, `POST /bulletin-images` and `GET /bulletin-images/{id}`, `bulletin.cover_image_id`, the picture printed in the PDF and the Word version, the 60-day removal; the builder unchanged, today's pages keep working) merges and deploys first; **PR 3b** (T7-T12: the draft v4, the picture on the Bulletin step, carry forward with the "From last week" mark, the card) merges after 3a is live and checked. After both merge, the Bulletin step starts with a **Cover picture** group: **Choose a picture** opens the phone's photos (or camera), the picture uploads and shows as the front page will trim it, **Remove** takes it off, and last week's picture carries forward like the music, marked "From last week. Check before printing." with **Keep as is**. The printed bulletin's cover shows the picture under the church's name, filling a 5.2 x 4.2 in box with its edges trimmed evenly, in color, with the reading and the date in white on a dark see-through band across its bottom (planning answers 2-4); the PDF and the Word version place the same picture. With no picture this week there is no box, and the reading and the date sit centered where the picture would be (planning answer 6). A page from before PR 3b (no bulletin, or one that does not say `cover_image_id`) still prints PR 1's "[Cover picture]" box, now centered under the church's name as the Word version's already is. The picture is stored in Postgres (`bulletin_images`, one new table with row-level security and no grant to Supabase's roles), turned upright, converted to sRGB, at most 1600 px on its long side, as a JPEG of at most 0.6 MB with no camera data (a phone's multi-picture JPEG is a JPEG); a picture no saved service points at goes 60 days after its upload (planning answer 9), on any church's next upload; and because any Google account can create a church, a church keeps at most 160 pictures, all churches' pictures together at most 150 MB, and one picture is prepared at a time (the plan review of 2026-10-03, "Plan review fixes" in Build notes). Any member can upload (planning answer 8). No new package and no new variable; production Streamlit (branch `streamlit-frozen`) is untouched.

**Architecture:** Backend first, in its own PR. `0007_bulletin_images` (expand-only) creates `bulletin_images (id, church_id, content_type, bytes, width, height, created_by, created_at)` with `ix_bulletin_images_church_created` and, on Postgres, `ENABLE ROW LEVEL SECURITY` (0003_lockdown's rule for every `public` table; the first new table since then) and 0003's guarded `REVOKE ALL` from `anon` and `authenticated` for this table; `backend/migrations/README.md` gains "Before 0007_bulletin_images" with the owner's four steps (step 4's query also runs before 0007 is applied) and "Checking the cover pictures' storage", its SQL pinned by tests. `backend/bulletin_image.py` (new, pure, Pillow) has `prepare` (an upload checked: at most 10 MB, a JPEG (a phone's multi-picture JPEG, Pillow's "MPO", included) or a PNG, only those two parsers tried, at most 50 million pixels, 24 million for a PNG; prepared on one worker thread, one at a time, a 429 after 10 s of waiting; a JPEG decoded at a reduced scale when it is large, a large PNG reduced by a whole factor first; turned upright, sRGB (transparent or not), 16-bit grey kept, transparency on white, at most 1600 px, re-encoded at quality 85, then lower and smaller until at most 600 KB, without EXIF) and `cover` (the picture filling the box with a centered crop, the band and the two lines, shrunk together when long, drawn with the Times Bold outline reportlab ships). `service_bulletin` gains `cover_image_id` and `cover_given` (False when the bulletin did not say: a page from before PR 3b) and `CARRY_KEYS` gains "cover" (first); `printed_bulletin.cover_kind` decides "picture", "none" or "placeholder"; `printed_pdf.cover_picture` makes the one JPEG both renderers place (300 dpi in the 372 x 300 pt box). The API: `repos.bulletin_images`, `usecases.bulletin_images` (`upload` removes up to 20 unused pictures older than 60 days of any church in a transaction of its own, then makes room within the church's 160, checks the 150 MB budget and stores; `picture` with its ETag), `api/routes/bulletin_images.py` (the picture is the raw request body: no multipart form, so no python-multipart, which this repo has only through Streamlit; the new `picture` rate-limit bucket; `GET` with `Cache-Control: private, no-cache`, the ETag and a 304, `Vary: Authorization, X-Church-Id` and `nosniff`), the removal and a save locking the picture (`FOR UPDATE`, `FOR SHARE`), `UploadSizeMiddleware` (a body over 10 MB, or without a Content-Length, is a 422 before it is read), `ServiceBulletin.cover_image_id` (optional: left out, a `PUT` keeps the saved picture and the printed bulletin keeps PR 1's box; null, no picture; an id the church does not have is saved and printed as no picture), `usecases.documents.build_printed` reads the picture with the church's name. OpenAPI regenerated (no `-Input`/`-Output` split). Frontend (PR 3b): the draft v4 (`bulletin.cover_image_id`, "cover" first in `CARRY_KEYS`; `migrate.ts`: 3 → 4), `setCover`, carry forward, Keep as is and "Save as new service" for the picture (`lib/draft/bulletin.ts`), the payload leaving a null picture out (so a draft "Saved" before 3b stays "Saved"), `serviceBody` always saying it, a POST leaving "no picture" out (as 2b-2's blank bulletin), `savedCopyFingerprint` comparing it, `lib/queries/bulletin-images.ts` (`checkPicture`, `useUploadBulletinImage` whose own callback puts the picture in the draft even after the step is left, `useBulletinImage`), the step's **Cover picture** group (the preview's object URL made and released in one effect, the printed band drawn over the preview, a note for a small picture), and the card's lines.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy 2, Alembic, Pillow 12 (installed with reportlab 5, already a runtime dependency), reportlab and python-docx (PR 1's renderers), pytest (SQLite; Postgres for `@pytest.mark.postgres`), pypdf in the tests; Next 16, React 19, TypeScript 5, zod, Base UI, TanStack Query 5, Vitest 3 with Testing Library; openapi-typescript for `schema.d.ts`.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`: owner answer 4 (cover picture), 10 (checks); "PR 3 planning answers (Beau, 2026-10-03)" 1-10 (binding); "Data model" (cover picture, carry forward); "API"; "The Bulletin step"; "Scope by PR".
- The PR 2b plan `docs/superpowers/plans/2026-10-03-printed-bulletin-2b.md` (the format model: two PRs backend first, the migration's owner steps, carry forward with marks, Build notes; its "Questions for the owner" 1-17, answered "all recommended" and binding, among them 7 Keep as is, 14 two PRs, 16 the marks saved with the service, 17 Save as new service) and the PR 2a plan `docs/superpowers/plans/2026-10-02-printed-bulletin-2a.md`.
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.2 (church scope), §1.3 (`ServiceDraft`), §1.5 (errors), §1.8 (rate limits, plain `def`), §2.2 (layers), §2.5 (logs), §3.2 and §3.6 (row-level security), §3.4, §3.5 (migrations), §4.4 (keys), §4.5 (`apiFetch`), §4.6 (the draft: versioning, never destroy typed input), §4.8 (forms, 44 px).
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `fbc9598` = `origin/main` `e4f3695` (PR #48, printed bulletin PR 2b-2) plus "Runbook: printed bulletin PR 2b-2 record (owner's phone check)" and "Spec: printed bulletin PR 3 planning answers (owner, 2026-10-03)", then this plan's commits; 2026-10-03): backend `1432 passed, 17 skipped`; Postgres-marked `17 passed, 1432 deselected` (local Postgres 16); frontend `704 passed` in 87 files; typecheck and lint clean; Alembic head `0006_services_bulletin` (6 revision files); 4 runbook owner markers. Pillow 12.3.0 is installed (reportlab requires it; FreeType, littlecms2, JPEG and zlib built in); python-multipart 0.0.32 is installed only because Streamlit requires it (it is not in `backend/requirements.txt`, which Railway installs from `/backend`), so the upload is a raw body. `ServiceBulletin` (`api/schemas.py`) has `extra="forbid"` and is the model of both the request and the response; a field with a default does not split it into `-Input` and `-Output` in OpenAPI (checked). 2b-2's `savedCopyFingerprint` reads the bulletin's fields one by one, so an extra `cover_image_id` in `ServiceOut` changes nothing for a page from before 3b; its `bulletinFromService` filters `unchecked` through its own `CARRY_KEYS`, so a stored "cover" is dropped, not a restore error. `0003_lockdown` enabled row-level security on every table that existed then; `test_0003_is_idempotent_after_the_manual_lockdown` (Postgres) expects it on every table of the models at head, so a new table must turn it on itself. Pillow 12.3 opens a JPEG with a multi-picture (MPF) segment, as iPhone HDR and Samsung portrait photos have, as format "MPO" through the JPEG opener (`Image.open(formats=("JPEG", "MPO", "PNG"))` raises `KeyError: 'MPO'`: MPO has no opener of its own). The PR 1 PDF's "[Cover picture]" box is a reportlab `Flowable`, whose `hAlign` defaults to "LEFT": it sat at the left margin, 60 pt off center (seen in the 2b-2 sample's image).
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch head (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -3` (or `| tail -1` where a step says so); the suite `.venv/bin/python -m pytest -q | tail -1`. Postgres-marked tests run only with `TEST_DATABASE_URL` set to a local, throwaway Postgres (`tests/pg_helpers.require_local_test_url`); without it they skip, and CI's `backend-postgres` job runs them (after `alembic upgrade head`, `alembic check`, `alembic downgrade base`, `alembic upgrade head`). Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes (T3, PR 3a), so T3 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand. T3 also adds the `BulletinImage` type name, so typecheck stays clean at every commit.
- No new package, no new variable. One migration, `0007_bulletin_images` (T1), whose `down_revision` is `0006_services_bulletin`.
- Branch `claude/slice-2-plan-4q33le`, at `fbc9598` plus this plan's commits (`WIP plan: printed bulletin PR 3 …`, `Plan: printed bulletin PR 3 (the cover picture)` and any later plan commit), then T1-T4 (PR 3a). After PR 3a merges, the same branch is fast-forwarded to `main` (T6 Step 7), takes the 3a record and then T7-T10 (PR 3b). Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes: PR 3a only after T6 Steps 1-3 (backup, counts, SQL); PR 3b only after PR 3a is live and checked (T6 Steps 5-6; T11 Step 1 checks the live API).
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- Each PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes its tests line: PR 3a `Tests: backend 1432 → 1477 passed, 17 → 22 skipped; frontend 704 in 87 files (unchanged)`; PR 3b `Tests: frontend 704 → 720 in 87 → 88 files; backend 1477 passed, 22 skipped (unchanged)`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 15 and has no em dashes; existing copy keeps its own punctuation.
- **PR 3a before PR 3b, and each tolerates the other** (clarification 18): nothing in T1-T4 changes a page, a component, the draft, a query or a request body (T5 Step 3 checks it); nothing in T7-T10 changes the server, the API files, a workflow or a package (T11 Step 3 checks it).
- No church id, email address, token, database URL, real person's name, address, phone or email, and **no real photo** in any doc, commit, test or record. The tests make their pictures with Pillow (`backend/tests/picture_helpers.py`: plain colors, stripes and an invented color profile; noise from a seeded generator) or as a few bytes (`frontend`); the invented names are the 2b plan's ("Example Church", "Sam Sample", …). A cover picture can show people: it lives only in `bulletin_images` and in the files a member downloads, never in a log line, a commit or a record (clarification 13).
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action (the backup run included). Owner steps go one at a time, in plain words.

### How the file directives below read
As in the PR 2b plan: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written (top to bottom within a file, so an anchor is unique in the file as the previous directives left it). A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted.

### Baselines and counts
- Starting baselines: backend **1432 passed, 17 skipped**; Postgres-marked **17 passed, 1432 deselected** (with a local Postgres); frontend **704 passed in 87 files**, typecheck and lint clean; Alembic head **`0006_services_bulletin`** (6 revision files); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new `it(`.

  | After | PR | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|---|
  | T1 | 3a | +4, +4 skipped (`test_migrations.py` 4 and 3 Postgres only; `test_services_postgres.py` 1, Postgres only; `test_schema_check.py`, `test_api_app.py` edited) | 1436 passed, 21 skipped | 0 | 704 in 87 |
  | T2 | 3a | +27 (`test_bulletin_image.py` 23, one test in nine cases and one in two; `test_service_bulletin.py` 1; `test_printed_bulletin.py` 1; `test_printed_render.py` 2) | 1463 passed, 21 skipped | 0 | 704 in 87 |
  | T3 | 3a | +14, +1 skipped (`test_api_bulletin_images.py` 11, one test in three cases, and 1 Postgres only; `test_api_services.py` 1; `test_api_printed.py` 1; `test_service_bulletin.py` 1; `test_middleware.py`, `test_ratelimit.py`, `test_no_streamlit_in_core.py` edited) | 1477 passed, 22 skipped | 0 | 704 in 87 |
  | T4-T6 | 3a | 0 (docs; verification, the merge, the record) | 1477 passed, 22 skipped | 0 | 704 in 87 |
  | T7 | 3b | 0 | 1477 passed, 22 skipped | +8 (`bulletin.test.ts` 4, `migrate.test.ts` 1, `documents.test.ts` 1, `bulletin-images.test.ts` 2, new; `schema.test.ts`, `store.test.ts`, `mapping.test.ts`, `review-send-step.test.tsx` edited) | 712 in 88 |
  | T8 | 3b | 0 | 1477 passed, 22 skipped | +7 (`bulletin-step.test.tsx`) | 719 in 88 |
  | T9 | 3b | 0 | 1477 passed, 22 skipped | +1 (`review-send-step.test.tsx`; `bulletin.test.ts` edited) | 720 in 88 |
  | T10-T12 | 3b | 0 | 1477 passed, 22 skipped | 0 | 720 in 88 |

- Per PR: **PR 3a** backend 1432 → 1477 passed, 17 → 22 skipped, frontend 704 in 87 (unchanged); **PR 3b** frontend 704 → 720 in 87 → 88 files, backend unchanged.
- CI `backend-postgres` goes from `17 passed, 1432 deselected` to `21 passed, 1436 deselected` after T1, `21 passed, 1463 deselected` after T2 and `22 passed, 1477 deselected` from T3 on (PR 3b leaves it there). With a local Postgres (`TEST_DATABASE_URL`), the same numbers locally.

### Layering and code rules (carried)
- `bulletin_image`, `service_bulletin`, `printed_bulletin`, `printed_pdf`, `printed_docx`, `usecases/bulletin_images.py`, `usecases/archive.py`, `usecases/documents.py`, `repos/bulletin_images.py` and `repos/services.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains `bulletin_image`, `usecases.bulletin_images`, `repos.bulletin_images`, T3); the routes are plain `def` with one usecase call, no SQL and no try/except (F §2.2 rule 1); every query lives in `repos` and filters on `church_id` (F §1.2). `UploadSizeMiddleware` is pure ASGI, like the other two middlewares.
- Logs carry ids, counts, sizes and durations, never a picture or a bulletin's text (F §2.5; clarification 13). Two new log lines, `bulletin_images.upload church=… image=… bytes_in=… bytes=… size=WxH removed=… ms=…` and the warning `bulletin_images.storage_full church=… total=… budget=…`; `documents.printed` is unchanged.
- Pages and components never call `apiFetch`: the upload and the preview use `useApi()` (F §4.5). The draft is changed only through `useDraft()` (`update` for a choice, `autoUpdate` for the carry, F §4.6).
- Touch targets 44 px below `md` (`size="touch"` buttons); text wraps at 375 px; no raw HTML (F §4.8); the kit's `Button`, `Skeleton` and `PendingButton`. The preview is a plain `<img>` of a `blob:` URL (`next/image` cannot fetch a church-scoped picture), its lint rule turned off on that line with the reason.
- Expand-only migration (F §3.4): one new table, its index, row-level security; no change to another table, no backfill.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** (branch `streamlit-frozen`) is frozen and retired for real use; merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge; Railway's Pre-deploy Command `alembic upgrade head` applies migrations.
4. **The spec's decisions** stand as written in S, with the PR 3 planning answers below winning where S's earlier text differs (T4 amends S's "Data model" to match: JPEG and PNG only, no HEIC).
5. **Layout B**, the PR 1 plan's twelve answers, the PR 2a plan's fourteen and the PR 2b plan's seventeen (all "all recommended") stand. PR 2b is merged (PR #47, #48) and recorded.

### PR 3 planning answers (Beau, 2026-10-03, "all recommended, the printer is color"; binding)
1. **Two PRs, server first** (as PR 2b): **PR 3a** brings the `bulletin_images` table (migration `0007_bulletin_images`), the upload and preview routes, `bulletin.cover_image_id`, and the picture printed in the PDF and the Word version; the deployed pages keep working. **PR 3b** brings the upload on the Bulletin step. 3b opens only after 3a is live and checked.
2. **Text over the picture:** the reading and the date in white on a dark see-through band across the bottom of the picture.
3. **Fit:** the picture fills the box, trimmed evenly at the edges (centered crop).
4. **Color:** the church's printer prints in color, so the picture stays in color.
5. **Formats:** JPEG and PNG only (no HEIC package); Safari is expected to turn an iPhone photo into JPEG on upload, to be verified on the owner's phone during the PR 3b check.
6. **No picture this week:** no box at all; the reading and the date sit centered where the picture would be.
7. **Keep last week's picture:** it carries forward like the music, marked "From last week. Check before printing.", with **Keep as is**.
8. **Who can upload:** any member who can edit the service.
9. **Old pictures:** a picture no saved service points at is removed after 60 days.
10. **Checks:** migration 0007 follows 0006's routine (a backup, read-only counts, the `--sql` preview; after the deploy, one read-only check), a phone check after each PR, and a short print test of a cover with a picture.

**Later, out of scope:** a delete route for one picture (Remove takes it off the bulletin; the picture itself goes with the 60-day removal), shrinking the picture in the browser before the upload (question 6), a picture on the Word working copies, 6a (Settings), the folded booklet, Voices of the Church.

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended).

1. **[owner-visible] What PR 3 ships** (planning answer 1), in two PRs (clarification 18). PR 3a: migration `0007_bulletin_images`, `POST /bulletin-images`, `GET /bulletin-images/{id}`, `ServiceBulletin.cover_image_id` (and "cover" among the boxes to check), the picture printed in the PDF and the Word version when a page sends one, the 60-day removal. PR 3b: the **Cover picture** group on the Bulletin step, carry forward and Keep as is for the picture, "Save as new service" marking it, the card's lines and the draft v4. Not here: the Word working copies (`POST /documents`; clarification 17), the Bulletin settings, a route to delete one picture ("Follow-ups").
2. **[owner-visible] The upload** (S "Data model"; planning answer 5). `POST /bulletin-images` takes the picture itself as the request body (the browser sends the file with its type); a JPEG (a phone's multi-picture JPEG included: an iPhone HDR or a Samsung portrait photo carries a second picture, which Pillow calls "MPO"; the first one is stored) or a PNG, at most 10 MB and 50 million pixels (more than any phone camera's 48 MP; 24 million for a PNG, which is decoded whole: a screenshot or a graphic), else a 422 naming `image` with one of: "Choose a JPEG or PNG picture." (anything else, a file cut short, unreadable or empty included), "The picture is larger than 10 MB. Choose a smaller one.", "The picture has too many pixels. Choose a smaller one.". Only the JPEG and PNG parsers are tried. It is stored turned upright (its EXIF orientation), its colors converted to sRGB when it carries a color profile, transparent or not (an iPhone photo's Display P3 would otherwise print slightly off), a 16-bit grey PNG with its tones kept, a transparent part laid on white, scaled down to at most 1600 px on its long side (never up), as a JPEG (quality 85) **with no camera data** (no EXIF: no location, no time, no phone model) of **at most 600 KB** (a busier picture is saved at a lower quality, then smaller: 75 at 1600 px, 70 at 1400, 65 at 1200, 60 at 1000, then 800 px, until it fits; measured: random noise, the worst case, 545 KB at 1200 x 1200; a phone photo stays at 1600 px, usually 0.2-0.5 MB). A large JPEG is decoded at a half, a quarter or an eighth of its size when that is still at least the stored size (Pillow's draft mode), so a 12 MP phone photo takes about 0.15 s and little memory (measured: a 3.9 MB, 4032 x 3024 photo-like picture became 460 KB at 1600 x 1200). It answers 201 `{id, width, height}`. One picture is prepared at a time in the server (clarification 20). No multipart form: `python-multipart` is installed here only because Streamlit requires it, not in `backend/requirements.txt`, which Railway installs, and the raw body needs nothing new.
3. **[owner-visible] The cover as printed** (planning answers 2-4; S "The sample"). The box is 372 x 300 pt (5.17 x 4.17 in), as PR 1's, centered under the church's name in both files. With a picture, the server makes **one picture of the whole box** (`printed_pdf.cover_picture`, 1550 x 1250 px, 300 dpi): the stored picture scaled to fill the box and trimmed evenly at the edges (a centered crop: a portrait photo loses its top and bottom, a wide one its sides), in color, with a black band at 55 % opacity across its bottom holding the reading (18 pt) and the date (14 pt) in white Times Bold, centered, both shrunk by the same factor when the reading is too long for the width (so it never prints smaller than the date); the PDF and the Word version place that same picture, so they look the same (question 2). The reading is the one the cover printed before (the New Testament reading, else the first reading). In the Word version the band's text is part of the picture (to change it, change the service and download again). A picture that is no longer there (removed, or another church's id) prints as no picture.
4. **[owner-visible] No picture this week** (planning answer 6). No box and no frame: the reading (bold, 18 pt) and the date (bold, 14 pt), black, centered in the box's place, so the contact lines stay where they were. **A page from before PR 3b** sends either no bulletin or one without `cover_image_id`; it still prints PR 1's "[Cover picture]" box with the reading and the date in it (`printed_bulletin.cover_kind` "placeholder"), so PR 3a changes nothing a member sees except that the PDF's box is now centered under the church's name (it sat at the left margin, 60 pt off center; the Word version's was centered on 2026-10-03) (question 1).
5. **[owner-visible] Carry forward and Keep as is** (planning answer 7; the 2b plan's clarification 7). The picture is a box like the music: `CARRY_KEYS` (server and draft) gains "cover", first (the cover is the bulletin's first page and the step's first group). A new draft takes the church's latest service's picture (dated before the draft's date) into the picture's box when it was not chosen, removed or kept yet, marked "From last week. Check before printing." with **Keep as is** (named "Keep as is: cover picture"); choosing another picture, removing it or keeping it clears the mark and stops the carry for that box. "Save as new service" marks a saved service's picture to check, as its music. The mark is saved with the service (`unchecked` holds "cover"). Last week's picture is still in the database (a saved service points at it, so the 60-day removal never takes it).
6. **[owner-visible] Who uploads and who sees** (planning answer 8). Any member of the church (the routes are `require_church`, as `/services`). A picture is served only through `GET /bulletin-images/{id}` with the church's header (another church's id is a 404, F §1.2 rule 2); row-level security on the table keeps Supabase's own web API (the `anon` and `authenticated` roles) from reading it. Every member who opens a service that points at a picture sees it. The browser may keep a fetched picture only for itself and asks the server again each time it is shown (`Cache-Control: private, no-cache`, `Vary: Authorization, X-Church-Id`, an `ETag`: the server answers 304 without the picture when the browser's copy is current, after checking the church), so after a sign-out on a shared device the picture is not shown from the browser's cache without the server's yes; `X-Content-Type-Options: nosniff`. The page keeps a picture's bytes in memory for the session (an id never names other bytes).
7. **[owner-visible] Old pictures** (planning answer 9). A picture uploaded more than 60 days ago that no saved service of its church points at is removed **on any church's next upload** (at most 20 an upload, the church with the oldest such picture first, in a transaction of its own before the new picture is stored; `usecases.bulletin_images.remove_unused`): no job to schedule, and a church that stops uploading (a church made only to fill the storage) still loses its unused pictures; "unused" is still decided per church, and a picture a saved service points at is never removed, whatever its age. A picture chosen in a draft but not yet saved (a draft lives in one browser, so the server cannot see it) has those 60 days. A picture removed on the step, or one whose service was deleted, stays until then (question 8). The removal locks the pictures it looks at (`FOR UPDATE`) before it reads the saved services, and a save locks the picture it points at (`FOR SHARE`, `usecases.archive._with_known_cover`), so a save never ends up pointing at a picture removed meanwhile: whichever comes second waits (a save that waited for a removal saves no picture). The count removed is logged.
8. **[owner-visible] The step's group** (PR 3b; S "The Bulletin step"). **Cover picture**, first on the step, with the help "A JPEG or PNG picture for the front page, with the reading and the date printed over it. Without a picture, the reading and the date print alone."; when there is one, a preview trimmed to the cover's shape (`object-cover` at 372:300, alt "This week's cover picture, as the front page trims it"); **Choose a picture** (**Choose another picture** when there is one) opens the phone's photos or camera (`accept="image/jpeg,image/png"`, no `capture`, so the phone offers both); **Remove** (for screen readers "Remove the cover picture"). Over the preview, a dark see-through strip across its bottom with the reading and the date in white, roughly as the band prints, so it shows what the band covers (question 16; hidden from screen readers, which hear the alt text). A picture under 800 px on its long side as stored (it would print at under about 150 dpi) uploads, and the step says "This picture is small and may print blurry." under the preview. While it uploads the button reads "Uploading…" and a screen reader hears "Uploading the picture…"; the member can leave the step meanwhile: the picture goes in the draft when the upload answers (the upload's own callback, written to the browser at once), unless the draft is another one by then (another service opened, or the date changed). A file that is not a JPEG or PNG, is empty, or is over 10 MB, is refused at once with the server's own words, before any upload; the server's refusal (or a network failure) is said under the buttons (`role="alert"`); the picture already chosen stays. A picture that can no longer be loaded says "The picture could not be loaded." and **Remove** still works. No shrinking in the browser (question 6). The preview's object URL is made and released in one effect keyed by the picture's bytes, so React's StrictMode (on in `next dev`) never shows a released URL.
9. **[owner-visible] The Printed bulletin card** (PR 3b; the 2b plan's clarification 9). The note becomes "The cover picture, the music, the announcements and this week's changes to who leads come from the Bulletin step."; "Not filled in: …" gains "cover picture" (before "prelude") when there is none (question 11); "From last week, not checked yet: …" names it "cover picture", first.
10. **The API** (S API). `ServiceBulletin.cover_image_id: UUID | null`, **optional**: left out (a page from before 3b) the server reads the bulletin as not saying (`service_bulletin.ServiceBulletin.cover_given` False): a `POST` saves no picture, a `PUT` keeps the saved one, a download prints PR 1's box; null is no picture; an id the church does not have is saved and printed as no picture (never a 404 that would block a save). A malformed id is the usual 422 naming `bulletin.cover_image_id`. `unchecked` accepts "cover" (an unknown box stays a 422, `bulletin.unchecked.0`). `ServiceOut.bulletin.cover_image_id` is always present (null when none), and `GET /services/previous-bulletin` carries it. `POST /bulletin-images` (`require_church`, the `picture` bucket: 20 an hour a member and 60 a day a church, question 9; 201 `BulletinImageOut {id, width, height}`; 401, 403, 422 (also a church's 160 pictures all in saved services, and the 150 MB budget reached, clarification 20), 429 (also "Another picture is being prepared. Try again in a few seconds.")) and `GET /bulletin-images/{image_id}` (`image/jpeg`, its ETag; 304 for `If-None-Match` with it; 404 "That picture is no longer available."). The body is read whatever its Content-Type (none included); `application/json` is a 400 from the framework, and the page always sends the file's own type. `UploadSizeMiddleware` answers the 422 for a body whose Content-Length is over 10 MB, or missing ("Send the picture with its size (Content-Length)."), before any of it is read (the route would otherwise read it all into memory first); it runs before the sign-in check, so such a request is a 422 whoever sends it, and it reads nothing. An empty body passes the middleware and the framework (the body has a default), so the sign-in and the church are checked first and the usecase answers "Choose a JPEG or PNG picture.". No `Idempotency-Key` on the upload: a retried upload stores a second copy, which the 60-day removal takes.
11. **Storage** (S "Data model"; F §3.4, §3.5). `bulletin_images` in `0007_bulletin_images` (`down_revision` `0006_services_bulletin`): `id UUID` primary key, `church_id UUID NOT NULL` (`ON DELETE CASCADE`), `content_type VARCHAR NOT NULL` (always `image/jpeg`), `bytes BYTEA NOT NULL` (the picture), `width`, `height INTEGER NOT NULL`, `created_by UUID` (`ON DELETE SET NULL`), `created_at TIMESTAMPTZ NOT NULL`; `ix_bulletin_images_church_created (church_id, created_at)`; on Postgres `ALTER TABLE bulletin_images ENABLE ROW LEVEL SECURITY` (0003's rule; `test_0003_is_idempotent_after_the_manual_lockdown` checks every model table at head) and, when both Supabase roles exist (0003's guard), `REVOKE ALL ON bulletin_images FROM anon, authenticated` in a `DO` block: 0003's `ALTER DEFAULT PRIVILEGES` already leaves them no grant, but only for the role that ran 0003 (plan review M10). A service points at a picture by the JSON key `services.bulletin.cover_image_id` (no foreign key: a column on `services` would be a second schema change for no gain at this size; the removal reads the church's stored bulletins). Its `--sql` preview has trailing spaces on the CREATE TABLE lines, so the README's copy and the test strip them (`| sed 's/ *$//'`). Tests: up from 0006 with the rows kept, down giving back the 0006 tables, the exact offline SQL, the README pin, the drift at the baseline and the head constants, row-level security and the REVOKE (even with default privileges that would grant) on Postgres, the owner's queries and the storage query on Postgres, and step 4's query run before 0007; the slice-1a test of the baseline's offline SQL now expects exactly one CREATE TABLE (0007's).
12. **The draft v4** (F §4.6 "Versioning"). `DRAFT_VERSION` 4; `bulletin.cover_image_id` (null: none); `CARRY_KEYS` gains "cover", first; `migrations[3]` adds `cover_image_id: null` and changes nothing else. `bulletinPayload` (what the "Unsaved changes" fingerprint hashes) holds `cover_image_id` only when there is a picture, so a draft "Saved" before 3b, its bulletin filled in or not, stays "Saved" after its migration (T7's migration test); `serviceBody` (every save and download) always says it (null for none), so a `PUT` saves a Remove and a download prints "no picture" rather than PR 1's box; a `POST` leaves a null picture out (as 2b-2's blank bulletin: a POST sent before 3b whose answer was lost replays instead of saving twice; the server stores no picture either way). The 409 "is it my own save?" check (`savedCopyFingerprint`) compares the picture's id (null and missing alike). A version 5 draft is a restore error, as today.
13. **Privacy and logging** (F §2.5). A cover picture can show people (children included) and is visible to every member of the church who opens the service (question 7). The stored picture keeps no camera data. No log line carries a picture: `bulletin_images.upload` logs the church and picture ids, the sizes in and stored, the pixel size, the count removed and the time; `bulletin_images.storage_full` the church, the total and the budget. The tests make their pictures; the checks use a picture with no one in it, and the records never include a picture.
14. **[owner-visible] The owner's production steps** (planning answer 10; 0006's routine), around **PR 3a**'s merge. `backend/migrations/README.md` gains "Before 0007_bulletin_images (printed bulletin PR 3a)": (1) a `db-backup` run; (2) one read-only query giving `version` (`0006_services_bulletin`), `services`, `with_bulletin` and `database_size` (`pg_size_pretty`, so later records show the pictures' share of the free plan's 500 MB; question 13); (3) the `--sql` preview, rendered by the agent without a database (27 lines: the table, its index, row-level security, the guarded REVOKE, the version update), pinned by `test_the_readme_shows_the_0007_preview_exactly`; (4) after the deploy, a read-only query giving `0007_bulletin_images`, `row_security` `true`, `open_grants` `0` (no grant to `anon` or `authenticated`) and `pictures` `0`, then step 2 again; it uses `to_regclass`, so run before 0007 is applied it answers `0006_services_bulletin` with two empty values instead of an error. The README also gains "Checking the cover pictures' storage" (any time, read-only: pictures, churches, their size against the 150 MB budget, the most in one church, the database's size). The queries run in Postgres tests (T1). T6 Step 5 also sends a 9.5 MB and an 11 MB body to the live API, signed out (401, then 422), so a body limit in Railway's proxy, or a body sent without its length, shows before PR 3b. T6 takes the owner through them one at a time, then through a short phone check that the builder works as before (item 30). After PR 3b: four phone steps (items 32-35) and the print test (item 36). Reverting keeps `0007` (README "Reverting PR 3b or PR 3a").
15. **[owner-visible] Every new user-facing string** (no em dashes). The step: "Cover picture" (the group); "A JPEG or PNG picture for the front page, with the reading and the date printed over it. Without a picture, the reading and the date print alone."; "Choose a picture", "Choose another picture", "Uploading…" (the button while it uploads), "Uploading the picture…" (for screen readers); "Remove" (for screen readers "Remove the cover picture"); "This week's cover picture, as the front page trims it" (the preview's alt text); "This picture is small and may print blurry."; "The picture could not be loaded."; "Keep as is" (for screen readers "Keep as is: cover picture"; 2b's words); "Choose a JPEG or PNG picture.", "The picture is larger than 10 MB. Choose a smaller one." (said before an upload, and by the server); from the server also "The picture has too many pixels. Choose a smaller one.", "Send the picture with its size (Content-Length).", "That picture is no longer available.", "Another picture is being prepared. Try again in a few seconds.", "Your church keeps 160 pictures, all in saved services. Remove the picture from an older service, then try again." and "The app has no room for more pictures right now. Please tell the app's administrator.". The preview's band repeats the reading and the date (no new words). The card: "The cover picture, the music, the announcements and this week's changes to who leads come from the Bulletin step."; "Not filled in: …" and "From last week, not checked yet: …" gain "cover picture". In the files: none new (the reading and the date are PR 1's); "[Cover picture]" stays only for a page from before 3b.
16. **Docs** (T4, T10). T4 (PR 3a): `docs/manual-verification.md` gains "### Printed bulletin PR 3: the cover picture" at the end, inside "## Printed bulletin" (a `###` heading: `test_slice1_docs.py`'s pin of the last eight `##` headings does not move), with the two PRs and items 28-31 (the owner's steps around 0007, the builder as before, the agent's check of the live routes); S's "Data model" says JPEG or PNG only (no HEIC), the raw body, sRGB and no camera data, the id an unknown church picture saves as none, the carry with its mark, the removal on the next upload; "The Bulletin step" and "Scope by PR" follow planning answers 1 and 7. T10 (PR 3b): items 32-37 (the phone check, the iPhone photo of planning answer 5, Remove, carry forward, a refused file, the print test, the agent's checks). The runbook records are T6's (`### Printed bulletin PR 3a record`, riding along in PR 3b) and T12's (`### Printed bulletin PR 3b record`, its own records PR), each before `## Backups`; the 2b-2 record (`9b90d21`) rides along in PR 3a.
17. **What does not change.** The Word working copies (`POST /documents`) print no picture (S answer 7 kept them as they are). The Bulletin settings page, its API and storage. `liturgy` keeps only the eight sections. `service_archive.py` (Streamlit's), `env.py`, the workflows, `package.json`, `requirements*.txt`, `app.py`, Streamlit.
18. **[owner-visible] Two PRs, backend first** (planning answer 1). **PR 3a** (T1-T4) merges first, after the owner's backup, counts and SQL; it changes no page, component, draft, query or request body (T5 Step 3), so the pages already live keep working against it: a 2b-2 page sends a bulletin without `cover_image_id`, which the 3a server saves with no picture (a `POST`) or with the saved one kept (a `PUT`), prints PR 1's box for, and answers with an extra `cover_image_id: null` that 2b-2's code reads past (its 409 check compares fields one by one; its `bulletinFromService` drops an unknown box). While Railway deploys it, the old server keeps serving; if its pre-deploy `alembic upgrade head` fails (the 5 s lock timeout on `churches` or `users` for the foreign keys), nothing breaks, since no page needs the new server yet: redeploy. **PR 3b** (T7-T10) merges only after `/openapi.json` in production lists `/bulletin-images` and the owner's checks of T6 passed (T11 Step 1); it changes no server code, API file, workflow or package (T11 Step 3), so its deploy is Vercel's alone, and an old page still open meanwhile keeps working against the same server. The 2b-2 record rides along in PR 3a and the 3a record in PR 3b.
19. **[owner-visible] Rolling back** (T12 Step R). A fix forward is preferred: 3b's server needs no change. If PR 3b must come out, only the step's picture group goes (T8's commit and T10's, reverted; the draft v4, the carry, the payload and the card stay), so every member's draft opens as it was; until 3b returns, a picture already chosen or carried from last week keeps printing and cannot be changed on the step. Checked while planning: that revert typechecks, lints and passes 713 frontend tests in 88 files. A 2b-2 tab still open after 3b deploys keeps working, with two effects (accepted, question 17): its `PUT` keeps the picture but drops "cover" from the boxes to check (2b-2's own `CARRY_KEYS` filter), so that picture's "From last week" mark is lost; and its downloads of a service with a picture print PR 1's "[Cover picture]" box (it sends no `cover_image_id`). A reload ends both. Reverting the whole of 3b would make every v4 draft a restore error (the 2b-2 reader refuses version 4, and refuses "cover" among its boxes), so it is not offered. PR 3a is reverted only after that and only if needed, keeping `0007` (README "Reverting PR 3b or PR 3a"); the pictures stay in their table, unread.
20. **[owner-visible] Limits that keep one account from hurting every church** (the plan review of 2026-10-03; questions 9, 13, 18). Any Google account can sign in and create a church (as today), so the upload must stay safe whoever calls it. **Memory:** one picture is prepared at a time in the server, on one worker thread (`bulletin_image._WORKER`); another waits its turn up to 10 s, then is a 429 "Another picture is being prepared. Try again in a few seconds." (a phone photo takes about 0.15 s, the largest picture taken under a second). Measured with the review's worst cases (Pillow 12.3, `ru_maxrss`): the worst picture taken, a 24 MP PNG with a palette and transparency (a 3 KB file), needs about 220 MB more for under half a second (an RGBA one 193 MB, a 49 MP progressive JPEG 152 MB, a baseline one 32 MB); twenty such uploads at once leave the process at about 250 MB (173 MB for twenty 49 MP JPEGs); the review's 49 MP PNGs (767 MB each, 3 GB for four at once) are now refused from their header, with no memory. One thread matters: the C allocator keeps freed memory per thread, so twenty threads taking turns under a lock still grew to 2.2 GB. **Storage:** a stored picture is at most 600 KB; a church keeps at most 160 (`MAX_PICTURES`): past that its oldest pictures no saved service points at make room, whatever their age, and when all 160 are in saved services the upload is a 422 "Your church keeps 160 pictures, all in saved services. Remove the picture from an older service, then try again."; and when all churches' pictures together would pass 150 MB (`STORAGE_BUDGET`, against the free plan's 500 MB), every upload is a 422 "The app has no room for more pictures right now. Please tell the app's administrator." with a `bulletin_images.storage_full` warning in Railway's log. The README's "Checking the cover pictures' storage" query shows where things stand. Both numbers are constants in `usecases/bulletin_images.py`.

### Risks
- **A lock at deploy time** (PR 3a). `CREATE TABLE` with two foreign keys takes a short `SHARE ROW EXCLUSIVE` lock on `churches` and `users`; `lock_timeout` turns a conflict into a failed deploy after 5 s with the previous release still serving (T6 Step 5 checks the deploy and `/health/ready`). No page needs the new server until PR 3b.
- **Any Google account can create a church** (existing behavior since slice 1b), so an upload can come from someone who is not a church member anywhere else. That is why the limits of clarification 20 exist: memory, a church's 160 pictures and the 150 MB budget, not only the `picture` bucket (20 an hour a member and 60 a day a church binds one account in one church, not an account that makes churches).
- **Memory on Railway.** One picture at a time on one thread: the measured worst case is about 220 MB more for under half a second (a 24 MP palette PNG with transparency), and twenty uploads at once leave the process at about 250 MB (clarification 20). The request bodies themselves are read by FastAPI before the route runs (up to 10 MB each, refused above that by `UploadSizeMiddleware` before it is read), as any other route's body is today. If Railway's memory is small, lower `MAX_PNG_PIXELS`.
- **Upload size and time on a phone.** A phone photo is 2-5 MB (an iPhone's HEIC sent by Safari as a JPEG; a 48 MP "ProRAW" or "48 MP" setting can exceed 10 MB, which the page refuses with its message). Over a slow mobile connection 5 MB takes 5-20 s; the client waits 60 s (`POST /bulletin-images` in `timeouts.ts`); the member may leave the step meanwhile (clarification 8). Railway's proxy has no body limit documented below 10 MB; T6 Step 5 checks it before PR 3b with a 9.5 MB body (401 signed out: it passed with its length) and an 11 MB one (422). Question 6 asks whether to shrink the picture in the browser first.
- **The database grows.** A stored picture is at most 0.6 MB (a phone photo usually 0.2-0.5 MB: 460 KB measured for a busy 12 MP photo-like picture; 545 KB for random noise, the worst case). One a week is about 25 MB a year a church at most (52 x 0.5 MB), plus pictures tried and not used, for 60 days. A church keeps at most 160 pictures (96 MB at most), and all churches together at most 150 MB; the free plan holds 500 MB. Step 2's `database_size` records the starting point, and each nightly backup grows by the same amount (the `db-backup` artifact). Questions 9 and 13. **One account making churches** can still upload about 20 pictures an hour (12 MB an hour at most), so it could fill the 150 MB budget in about half a day; then every church's uploads are refused until the 60-day removal frees room or the owner removes that church (the README's storage query shows it). The database stays far from 500 MB, so saving services keeps working.
- **A church that uses a new picture every week** reaches 160 pictures in saved services after about three years; from then on each upload asks to remove the picture from an older service first (a Remove and a save on that service, then the upload works). Raising `MAX_PICTURES` is a one-number change (question 18).
- **Room made within a church's 160** removes its oldest unused picture whatever its age, so a picture another member chose in a draft but has not saved yet can go when the church is at 160; that draft then says "The picture could not be loaded." with **Remove**.
- **A picture removed while a draft points at it.** A draft older than 60 days whose picture was never saved, or a service deleted after its picture was carried into a draft not yet saved, prints as no picture; the step says "The picture could not be loaded." with **Remove**. If a save sends such an id, the server saves no picture, and the page's 409 check (comparing its id with the server's null) would read that save as someone else's change; it needs two rare things at once, and the conflict dialog offers both choices.
- **The 2b-2 pages during PR 3a.** They work unchanged (clarification 18); a `PUT` from one keeps the saved picture, so a member using a stale tab cannot remove a picture there (nothing could choose one before 3b).
- **A 2b-2 tab still open after PR 3b deploys** (accepted, question 17): its `PUT` keeps the picture but loses the picture's "From last week" mark, and its downloads print PR 1's "[Cover picture]" box for a service that has a picture (clarification 19). Reloading the page ends it.
- **The Word version's band is part of the picture.** The reading and the date on it cannot be edited in Word; the band's look is the PDF's. A Word user who wants other words over the picture changes the service and downloads again.
- **Privacy.** Every member who opens a service sees its picture; a picture removed from the bulletin stays in the database (and the backups) until the 60-day removal. Photos of people, children especially, are the church's policy to decide (question 7).
- **The print test** (planning answer 10) is the first look at the colors on paper: the stored picture is sRGB and the PDF places it as it is (reportlab does no color management); the band's 55 % may need a change after the test (a one-number change, `bulletin_image.BAND_OPACITY`).

## File Structure

**Created**

| Path | What | Task (PR) |
|---|---|---|
| `backend/migrations/versions/0007_bulletin_images.py` | the `bulletin_images` table, its index, row-level security | T1 (3a) |
| `backend/bulletin_image.py` (+ `backend/tests/test_bulletin_image.py`, `backend/tests/picture_helpers.py`) | `prepare`, `cover`, the limits and messages; the tests' invented pictures | T2 (3a) |
| `backend/repos/bulletin_images.py`, `backend/usecases/bulletin_images.py`, `backend/api/routes/bulletin_images.py` (+ `backend/tests/test_api_bulletin_images.py`) | the queries and their locks; `upload`, `picture`, `remove_unused`, `make_room`, the limits; the two routes | T3 (3a) |
| `frontend/src/lib/queries/bulletin-images.ts` (+ `.test.ts`) | `checkPicture`, `useUploadBulletinImage`, `useBulletinImage` | T7 (3b) |

**Modified**

| Path | Change | Task (PR) |
|---|---|---|
| `backend/db/models.py`, `backend/migrations/README.md` | `BulletinImage`; the head, the 0007 row, "Before 0007_bulletin_images", "Reverting PR 3b or PR 3a" | T1 (3a) |
| `backend/tests/test_migrations.py`, `backend/tests/test_schema_check.py`, `backend/tests/test_api_app.py`, `backend/tests/test_services_postgres.py` | the 0007 tests, the README pin, the baseline's one CREATE TABLE; the head and the baseline drift; the owner's queries on Postgres | T1 (3a) |
| `backend/service_bulletin.py`, `backend/printed_bulletin.py`, `backend/printed_pdf.py`, `backend/printed_docx.py` | `cover_image_id`, `cover_given` (T2), "cover" in `CARRY_KEYS` (T3); `cover_kind`, `COVER_BOX`; `cover_picture` and the three boxes, centered; the same in Word | T2, T3 (3a) |
| `backend/tests/test_service_bulletin.py`, `backend/tests/test_printed_bulletin.py`, `backend/tests/test_printed_render.py` | the cover's read, carry and kinds; the picture and no-picture renders | T2, T3 (3a) |
| `backend/repos/services.py`, `backend/usecases/archive.py`, `backend/usecases/documents.py`, `backend/api/schemas.py`, `backend/api/ratelimit.py`, `backend/api/middleware.py`, `backend/api/main.py` | `stored_bulletins`; the picture saved, kept or none; the picture read for printing; `cover_image_id`, `BulletinImageOut`; the `picture` bucket; `UploadSizeMiddleware`; the router and the middleware | T3 (3a) |
| `backend/tests/test_api_services.py`, `backend/tests/test_api_printed.py`, `backend/tests/test_middleware.py`, `backend/tests/test_ratelimit.py`, `backend/tests/test_no_streamlit_in_core.py` | the API's picture; the order of the middlewares; the buckets; the new pure modules | T3 (3a) |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated | T3 (3a) |
| `frontend/src/lib/api/types.ts` | `BulletinImage` | T3 (3a) |
| `docs/manual-verification.md`, `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md` | "### Printed bulletin PR 3: the cover picture" and items 28-31, S's "Data model", "The Bulletin step", "Scope by PR" (T4); items 32-37 (T10) | T4 (3a), T10 (3b) |
| `docs/ops-runbook.md` | the PR 2b-2 record (`9b90d21`, rides along in PR 3a); "### Printed bulletin PR 3a record" (T6, rides along in PR 3b); "### Printed bulletin PR 3b record" (the records PR) | T6, T12 |
| `frontend/src/lib/draft/schema.ts`, `migrate.ts`, `bulletin.ts`, `frontend/src/lib/documents.ts`, `frontend/src/lib/queries/services.ts`, `frontend/src/lib/queries/keys.ts`, `frontend/src/lib/api/timeouts.ts` | the draft v4; 3 → 4; `setCover`, carry, payload, `withoutNoPicture`, "cover picture" labels (T7) and in "Not filled in" (T9); `serviceBody`, `savedCopyFingerprint`; a POST leaves "no picture" out; `keys.bulletinImage`; 60 s for the upload | T7, T9 (3b) |
| `frontend/src/lib/draft/schema.test.ts`, `migrate.test.ts`, `store.test.ts`, `mapping.test.ts`, `bulletin.test.ts`, `frontend/src/lib/documents.test.ts`, `frontend/src/test/fixtures/index.ts` | version 4; the picture's cases; `serviceBulletin()` with `cover_image_id: null`, `bulletinImage()` | T7, T8, T9 (3b) |
| `frontend/src/components/builder/bulletin/bulletin-step.tsx` (+ `.test.tsx`) | the **Cover picture** group | T8 (3b) |
| `frontend/src/components/builder/review/printed-card.tsx`, `frontend/src/components/builder/review/review-send-step.test.tsx` | the note and the lines; the bodies (T7) and the card (T9) | T7, T9 (3b) |

**Counts in the PRs:** **PR 3a** 40 paths: 9 created (this plan, `0007_bulletin_images.py`, `bulletin_image.py`, `repos/bulletin_images.py`, `usecases/bulletin_images.py`, `api/routes/bulletin_images.py`, `test_bulletin_image.py`, `test_api_bulletin_images.py`, `picture_helpers.py`), 31 modified (the backend, API, type and docs paths above, the spec, and `docs/ops-runbook.md`, the 2b-2 record, which rides along). **PR 3b** 22 paths: 2 created (`bulletin-images.ts` and its test), 20 modified (19 frontend and docs paths and `docs/ops-runbook.md`, the 3a record). **Untouched:** `service_output.py`, `worship_service.py`, `api/routes/documents.py`, `api/routes/services.py`, `bulletin_settings.py`, the Bulletin settings page and its API, `migrations/env.py`, `service_archive.py`, `documents-card.tsx`, `use-bulletin-carry.ts`, the summary panel, the workflows, the packages, `app.py`, Streamlit.

**Task order and review batches:** PR 3a: T1 → T4, each one commit and a backup push; one review of the batch with its fixes as `Fix: …` commits (T4 Step 4); T5 verifies and opens the draft PR on the owner's yes; T6 takes the owner through the backup, the counts and the SQL, merges on the owner's yes, checks production and the builder, and commits the 3a record. PR 3b, only then: T7 → T10, the same way (review in T10 Step 4); T11 checks that 3a is live, verifies and opens the draft PR on the owner's yes; T12 merges on the owner's yes, runs the phone check and the print test, and writes the record (its own records PR).

---

## PR 3a: the server (T1-T6)

T1-T4 are PR 3a's commits: the migration, the picture's module and the printed cover, the API, the docs. The builder does not change: the old pages send no `cover_image_id` and keep working (clarification 18). T5 verifies and opens the draft PR; T6 takes the owner through the backup, the counts and the SQL, merges on the owner's yes, checks production and writes the 3a record, which rides along in PR 3b. Nothing of PR 3b is started before T6 Step 7.

### Task 1: Migration `0007_bulletin_images` and the owner's steps (planning answers 9, 10; S "Data model"; F §3.2, §3.4, §3.5, §3.6; clarifications 11, 14)

**Files:**
- Create: `backend/migrations/versions/0007_bulletin_images.py`
- Modify: `backend/tests/test_api_app.py`, `backend/tests/test_schema_check.py`, `backend/tests/test_migrations.py`, `backend/tests/test_services_postgres.py`, `backend/db/models.py`, `backend/migrations/README.md`

The head moves to `0007_bulletin_images` (`test_api_app.py`, `test_schema_check.py`, the 0005 and 0006 owner-query tests on Postgres, which expect the head's version). The slice-1a test of `alembic upgrade 0001_baseline:head --sql` asserted no CREATE TABLE at all; it now expects exactly one, 0007's (the baseline's tables are still never created again).

- [ ] **Step 1 (agent): Write the failing tests**

**In `backend/tests/test_api_app.py`, replace:**

````python
SCHEMA_HEAD = "0006_services_bulletin"
````

**with:**

````python
SCHEMA_HEAD = "0007_bulletin_images"
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
EXPECTED_HEAD = "0006_services_bulletin"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
# 0004's invites changes, then 0005's and 0006's services changes (slice 5a-2,
# printed bulletin PR 2b).
````

**with:**

````python
EXPECTED_HEAD = "0007_bulletin_images"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
# 0004's invites changes, then 0005's and 0006's services changes (slice 5a-2,
# printed bulletin PR 2b), then 0007's table (printed bulletin PR 3a).
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
    "add_index ix_services_church_date",
````

**with:**

````python
    "add_index ix_bulletin_images_church_created",
    "add_index ix_services_church_date",
    "add_table bulletin_images",
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_head_is_0006_services_bulletin():
````

**with:**

````python
def test_head_is_0007_bulletin_images():
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_0005_and_0006_changes(tmp_path):
````

**with:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_to_0007_changes(tmp_path):
````

**In `backend/tests/test_migrations.py`, replace:**

````python
import logging.config
````

**with:**

````python
import logging.config
import re
````

**In `backend/tests/test_migrations.py`, replace:**

````python
def test_offline_sql_from_baseline_renders_guarded_adds_and_no_create_table():
````

**with:**

````python
def test_offline_sql_from_baseline_renders_guarded_adds_and_only_0007_s_create_table():
````

**In `backend/tests/test_migrations.py`, replace:**

````python

    assert "CREATE TABLE" not in sql
    assert "CREATE INDEX IF NOT EXISTS ix_hymns_church_hymnal ON hymns (church_id, hymnal);" in sql
````

**with:**

````python

    # No table of the baseline is created again; the one CREATE TABLE is 0007's new table (printed bulletin PR 3a).
    assert sql.count("CREATE TABLE") == 1 and "CREATE TABLE bulletin_images (" in sql
    assert "CREATE INDEX IF NOT EXISTS ix_hymns_church_hymnal ON hymns (church_id, hymnal);" in sql
````

**In `backend/tests/test_migrations.py`, replace:**

````python
    assert block.splitlines() == PREVIEW_0006
````

**with:**

````python
    assert block.splitlines() == PREVIEW_0006


# --- Printed bulletin PR 3a: 0007_bulletin_images (F §3.4, §3.5; printed bulletin spec "Data model") ---

# What `alembic upgrade 0006_services_bulletin:0007_bulletin_images --sql` prints on
# Postgres, comments, blank lines and trailing spaces left out: the preview the owner
# reads before the merge (PR 3 planning answer 10; backend/migrations/README.md).
PREVIEW_0007 = [
    "BEGIN;",
    "SET LOCAL lock_timeout = '5s';",
    "SET LOCAL statement_timeout = '60s';",
    "CREATE TABLE bulletin_images (",
    "    id UUID NOT NULL,",
    "    church_id UUID NOT NULL,",
    "    content_type VARCHAR NOT NULL,",
    "    bytes BYTEA NOT NULL,",
    "    width INTEGER NOT NULL,",
    "    height INTEGER NOT NULL,",
    "    created_by UUID,",
    "    created_at TIMESTAMP WITH TIME ZONE NOT NULL,",
    "    PRIMARY KEY (id),",
    "    FOREIGN KEY(church_id) REFERENCES churches (id) ON DELETE CASCADE,",
    "    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL",
    ");",
    "CREATE INDEX ix_bulletin_images_church_created ON bulletin_images (church_id, created_at);",
    "ALTER TABLE bulletin_images ENABLE ROW LEVEL SECURITY;",
    "DO $$",
    "BEGIN",
    "  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')",
    "     AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN",
    "    REVOKE ALL ON bulletin_images FROM anon, authenticated;",
    "  END IF;",
    "END $$;",
    "UPDATE alembic_version SET version_num='0007_bulletin_images' "
    "WHERE alembic_version.version_num = '0006_services_bulletin';",
    "COMMIT;",
]


def _bulletin_images_shape(conn) -> dict:
    insp = sa.inspect(conn)
    return {
        "columns": [(c["name"], str(c["type"]), c["nullable"]) for c in insp.get_columns("bulletin_images")],
        "pk": insp.get_pk_constraint("bulletin_images")["constrained_columns"],
        "fks": sorted((tuple(fk["constrained_columns"]), fk["referred_table"], fk["options"].get("ondelete"))
                      for fk in insp.get_foreign_keys("bulletin_images")),
        "indexes": sorted((i["name"], tuple(i["column_names"]), bool(i["unique"]))
                          for i in insp.get_indexes("bulletin_images")),
    }


def test_0007_creates_the_bulletin_images_table_and_changes_nothing_else(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0006_services_bulletin")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            kept = _insert_legacy_service(conn, church_id, user_id)
            services_before = _services_shape(conn)
            tables_before = set(sa.inspect(conn).get_table_names())
        _alembic(sqlite_url, "upgrade", "0007_bulletin_images")
        with engine.begin() as conn:
            tables = set(sa.inspect(conn).get_table_names())
            shape = _bulletin_images_shape(conn)
            services_after = _services_shape(conn)
            conn.execute(sa.text(
                "INSERT INTO bulletin_images (id, church_id, content_type, bytes, width, height, created_by, "
                "created_at) VALUES (:id, :church, 'image/jpeg', :data, 1600, 1200, :user, :at)"),
                {"id": uuid.uuid4().hex, "church": church_id.hex, "data": b"\xff\xd8", "user": user_id.hex,
                 "at": T9_NOW.isoformat()})
            services = conn.execute(sa.text("SELECT id FROM services")).scalars().all()
    finally:
        engine.dispose()
    assert tables == tables_before | {"bulletin_images"}
    assert shape == {
        "columns": [("id", "CHAR(32)", False), ("church_id", "CHAR(32)", False), ("content_type", "VARCHAR", False),
                    ("bytes", "BLOB", False), ("width", "INTEGER", False), ("height", "INTEGER", False),
                    ("created_by", "CHAR(32)", True), ("created_at", "DATETIME", False)],
        "pk": ["id"],
        "fks": [(("church_id",), "churches", "CASCADE"), (("created_by",), "users", "SET NULL")],
        "indexes": [("ix_bulletin_images_church_created", ("church_id", "created_at"), False)],
    }
    assert services_after == services_before
    assert [uuid.UUID(str(s)) for s in services] == [kept]


def test_0007_downgrade_drops_only_the_table(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0006_services_bulletin")
    before = _tables_snapshot(sqlite_url)
    _alembic(sqlite_url, "upgrade", "head")
    assert set(_tables_snapshot(sqlite_url)) == set(before) | {"bulletin_images"}
    _alembic(sqlite_url, "downgrade", "0006_services_bulletin")
    assert _tables_snapshot(sqlite_url) == before
    with _connection(sqlite_url) as conn:
        assert conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one() == "0006_services_bulletin"


def test_offline_sql_for_0007_is_one_table_one_index_row_level_security_and_the_revoke_under_the_timeouts():
    cfg = alembic_config(url="postgresql://preview@localhost:1/preview", configure_logger=False)
    cfg.output_buffer = buffer = io.StringIO()
    command.upgrade(cfg, "0006_services_bulletin:0007_bulletin_images", sql=True)
    lines = [line.rstrip() for line in buffer.getvalue().splitlines() if line.strip() and not line.startswith("--")]
    assert lines == PREVIEW_0007


def test_the_readme_shows_the_0007_preview_exactly():
    """The owner reads backend/migrations/README.md → "Before 0007_bulletin_images",
    step 3, against the agent's rendering; both must be PREVIEW_0007."""
    readme = (Path(__file__).resolve().parents[1] / "migrations" / "README.md").read_text(encoding="utf-8")
    section = readme.split("\n## Before 0007_bulletin_images (printed bulletin PR 3a)\n", 1)[1]
    step = section.split("\n### Step 3: Read the SQL the upgrade will run\n", 1)[1].split("\n### ", 1)[0]
    block = "BEGIN;" + step.split("\n```\nBEGIN;", 1)[1].split("\n```", 1)[0]   # the bare fence
    assert block.splitlines() == PREVIEW_0007


@pytest.mark.postgres
def test_0007_turns_on_row_level_security_and_grants_supabase_s_roles_nothing(pg_admin_url):
    """The pictures are served only through the API: with RLS on and no policy, anon and authenticated
    (Supabase's REST roles) read no row, and 0003's default privileges leave them no grant either."""
    with supabase_roles(pg_admin_url), throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        _alembic(sandbox.role_url, "upgrade", "head")
        admin = _pg_engine(sandbox.admin_db_url)
        try:
            assert _rls_flags(admin)["bulletin_images"] is True
            with admin.connect() as conn:
                for grantee in ("anon", "authenticated"):
                    assert conn.execute(text(
                        "SELECT has_table_privilege(:grantee, 'public.bulletin_images', 'SELECT')"),
                        {"grantee": grantee}).scalar_one() is False
        finally:
            admin.dispose()


@pytest.mark.postgres
def test_0007_revokes_supabase_s_roles_even_when_default_privileges_would_grant(pg_admin_url):
    """Plan review M10: 0003's ALTER DEFAULT PRIVILEGES holds only for the role that ran it; 0007's own
    REVOKE leaves anon and authenticated nothing on the new table even when defaults would grant it."""
    with supabase_roles(pg_admin_url), throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        _alembic(sandbox.role_url, "upgrade", "0006_services_bulletin")
        owner = _pg_engine(sandbox.role_url)
        admin = _pg_engine(sandbox.admin_db_url)
        try:
            with owner.begin() as conn:
                conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO anon, authenticated"))
            _alembic(sandbox.role_url, "upgrade", "head")
            with admin.connect() as conn:
                for grantee in ("anon", "authenticated"):
                    assert conn.execute(text(
                        "SELECT has_table_privilege(:grantee, 'public.bulletin_images', 'SELECT')"),
                        {"grantee": grantee}).scalar_one() is False
        finally:
            owner.dispose()
            admin.dispose()


@pytest.mark.postgres
def test_the_after_deploy_check_runs_before_0007_too(pg_admin_url):
    """Plan review M9: README step 4 run before the deploy applied 0007 answers (it does not fail):
    0006_services_bulletin and two empty values."""
    readme = (Path(__file__).resolve().parents[1] / "migrations" / "README.md").read_text(encoding="utf-8")
    section = readme.split("\n## Before 0007_bulletin_images (printed bulletin PR 3a)\n", 1)[1]
    check = re.findall(r"```sql\n(.*?)```", section, re.S)[1]
    with throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        _alembic(sandbox.role_url, "upgrade", "0006_services_bulletin")
        engine = _pg_engine(sandbox.role_url)
        try:
            with engine.connect() as conn:
                row = dict(conn.execute(text(check)).mappings().one())
        finally:
            engine.dispose()
    assert row == {"version": "0006_services_bulletin", "row_security": None, "open_grants": 0, "pictures": None}
````

**In `backend/tests/test_services_postgres.py`, replace:**

````python
    # test database is at head (0006_services_bulletin since printed bulletin PR 2b).
    assert counts == {"version": "0006_services_bulletin", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0006_services_bulletin", "new_columns": 2, "new_index": 1}
````

**with:**

````python
    # test database is at head (0007_bulletin_images since printed bulletin PR 3a).
    assert counts == {"version": "0007_bulletin_images", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0007_bulletin_images", "new_columns": 2, "new_index": 1}
````

**In `backend/tests/test_services_postgres.py`, replace:**

````python
    assert counts == {"version": "0006_services_bulletin", "services": 3, "churches": 2}
    assert applied == {"version": "0006_services_bulletin", "new_column": 1, "with_bulletin": 1}
````

**with:**

````python
    assert counts == {"version": "0007_bulletin_images", "services": 3, "churches": 2}
    assert applied == {"version": "0007_bulletin_images", "new_column": 1, "with_bulletin": 1}


def readme_0007_sql(n: int) -> str:
    """The n-th ```sql block of README "Before 0007_bulletin_images": 0 is step 2's counts, 1 step 4's check,
    2 the pictures' storage."""
    section = README.read_text(encoding="utf-8").split(
        "\n## Before 0007_bulletin_images (printed bulletin PR 3a)\n", 1)[1]
    return re.findall(r"```sql\n(.*?)```", section, re.S)[n]


@pytest.mark.postgres
def test_the_owner_s_read_only_queries_around_0007(world):
    from db.models import BulletinImage

    user, church = world
    with session_scope() as s:
        for bulletin in (None, {"announcements": {"coffee_hour": "Sam Sample"}}):
            s.add(Service(church_id=church, service_date_iso="2026-09-27", occasion="", hymns=[], liturgy={},
                          scriptures=[], bulletin=bulletin))
        s.add(BulletinImage(church_id=church, content_type="image/jpeg", bytes=b"\xff\xd8", width=1, height=1,
                            created_by=user))
    with session_scope() as s:
        counts = dict(s.execute(text(readme_0007_sql(0))).mappings().one())
        applied = dict(s.execute(text(readme_0007_sql(1))).mappings().one())
        storage = dict(s.execute(text(readme_0007_sql(2))).mappings().one())
    assert re.fullmatch(r"\d+ (bytes|kB|MB|GB)", counts.pop("database_size"))
    assert counts == {"version": "0007_bulletin_images", "services": 2, "with_bulletin": 1}
    assert applied == {"version": "0007_bulletin_images", "row_security": True, "open_grants": 0, "pictures": 1}
    assert re.fullmatch(r"\d+ (bytes|kB|MB|GB)", storage.pop("database_size"))
    assert storage == {"pictures": 1, "churches": 1, "pictures_size": "2 bytes", "most_in_one_church": 1}
````

- [ ] **Step 2 (agent): Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py 2>&1 | tail -1`
**Expected:** `16 failed, 59 passed, 7 skipped in <t>s`: the head constants, the baseline drift, the 0007 tests (no such revision), the README pin and the baseline's one CREATE TABLE. With a local, throwaway Postgres also `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres backend/tests/test_migrations.py backend/tests/test_services_postgres.py 2>&1 | tail -1` → `6 failed, 7 passed, 33 deselected in <t>s` (row-level security, the REVOKE, step 4's query before 0007, the 0007 queries, and the 0005 and 0006 queries' head version).

- [ ] **Step 3 (agent): The revision, the model, the README**

**Create `backend/migrations/versions/0007_bulletin_images.py`:**

````python
"""Bulletin images: the printed bulletin's cover pictures (printed bulletin spec, "Data model"; PR 3a)

Expand-only (F §3.4): one new table, no change to any other, no backfill.
- bulletin_images: one uploaded cover picture, turned upright, scaled to at
  most 1600 px on its long side and stored as JPEG (bulletin_image.py):
  id, church_id (the church's content cascades with it), content_type,
  bytes (the picture), width and height in pixels, created_by (SET NULL
  when the member's account goes), created_at. A service's bulletin points
  at a picture by id (services.bulletin's "cover_image_id": a JSON key, no
  foreign key); a picture no saved service points at is removed 60 days
  after its upload (usecases.bulletin_images).
- ix_bulletin_images_church_created (church_id, created_at): one church's
  pictures by age, for that removal.
- Row-level security on, as 0003_lockdown left every other public table:
  with no policy, Supabase's anon and authenticated roles see no row, so a
  picture is only ever served through the API, church-scoped. Postgres only
  (SQLite has no row-level security).
- REVOKE ALL on the table from anon and authenticated when both roles exist
  (Supabase; CI's Postgres has neither), as 0003_lockdown does: 0003's
  ALTER DEFAULT PRIVILEGES already leaves them no grant on a new table, but
  only for the role that ran 0003, so this does not depend on it (plan
  review M10).

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and statement_timeout
'60s') first. Creating a table takes no lock on any existing table except a
short one on churches and users for the two foreign keys.

Revision ID: 0007_bulletin_images
Revises: 0006_services_bulletin
Create Date: 2026-10-03
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_bulletin_images"
down_revision = "0006_services_bulletin"
branch_labels = None
depends_on = None

# 0003_lockdown's REVOKE, for this table only, under the same guard (both Supabase roles exist).
REVOKE_SQL = """\
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
     AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON bulletin_images FROM anon, authenticated;
  END IF;
END $$"""


def upgrade() -> None:
    op.create_table(
        "bulletin_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("church_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("bytes", sa.LargeBinary(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["church_id"], ["churches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bulletin_images_church_created", "bulletin_images", ["church_id", "created_at"])
    if op.get_context().dialect.name == "postgresql":
        op.execute("ALTER TABLE bulletin_images ENABLE ROW LEVEL SECURITY")
        op.execute(REVOKE_SQL)


def downgrade() -> None:
    op.drop_index("ix_bulletin_images_church_created", table_name="bulletin_images")
    op.drop_table("bulletin_images")
````

**In `backend/db/models.py`, replace:**

````python
    Integer,
````

**with:**

````python
    Integer,
    LargeBinary,
````

**In `backend/db/models.py`, replace:**

````python

class HymnUsage(Base):
````

**with:**

````python

class BulletinImage(Base):
    """A cover picture for the printed bulletin (revision 0007_bulletin_images;
    printed bulletin PR 3a): the upload turned upright, scaled to at most
    1600 px on its long side and stored as JPEG (bulletin_image.py). A
    service's bulletin points at it by id (services.bulletin's
    "cover_image_id", no foreign key); one no saved service points at is
    removed 60 days after its upload (usecases.bulletin_images)."""
    __tablename__ = "bulletin_images"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    church_id = Column(
        Uuid, ForeignKey("churches.id", ondelete="CASCADE"), nullable=False
    )
    content_type = Column(String, nullable=False)    # always "image/jpeg" (what is stored)
    bytes = Column(LargeBinary, nullable=False)      # the picture itself
    width = Column(Integer, nullable=False)          # in pixels, as stored
    height = Column(Integer, nullable=False)
    created_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        # One church's pictures by age: the 60-day removal (usecases.bulletin_images).
        Index("ix_bulletin_images_church_created", "church_id", "created_at"),
    )


class HymnUsage(Base):
````

**In `backend/migrations/README.md`, replace:**

````markdown
  `NNNN_short_slug.py`. Head is `0006_services_bulletin`.
````

**with:**

````markdown
  `NNNN_short_slug.py`. Head is `0007_bulletin_images`.
````

**In `backend/migrations/README.md`, replace:**

````markdown
| `0006_services_bulletin` | Printed bulletin PR 2b: `services.bulletin` (JSON), nullable with no default and no backfill: the printed bulletin's weekly fields. Before it reaches production: "Before 0006_services_bulletin" below. |
````

**with:**

````markdown
| `0006_services_bulletin` | Printed bulletin PR 2b: `services.bulletin` (JSON), nullable with no default and no backfill: the printed bulletin's weekly fields. Before it reaches production: "Before 0006_services_bulletin" below. |
| `0007_bulletin_images` | Printed bulletin PR 3a: the table `bulletin_images` (the cover pictures, stored as JPEG in `bytes`) with the index `ix_bulletin_images_church_created`, and on Postgres row-level security on it and, when Supabase's `anon` and `authenticated` roles exist, `REVOKE ALL` on it from both. No other table changes. Before it reaches production: "Before 0007_bulletin_images" below. |
````

**In `backend/migrations/README.md`, replace:**

````markdown
back when 2b-1 does.
````

**with:**

````markdown
back when 2b-1 does.

## Before 0007_bulletin_images (printed bulletin PR 3a)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0007_bulletin_images` when printed bulletin PR 3a (the server's half of
PR 3, the cover picture; the upload on the Bulletin step, PR 3b, merges
after it is live) merges. First, as the owner decided on 2026-10-03 (PR 3
planning answer 10, the same routine as 0006): a backup, read-only counts,
and a look at the SQL; after the deploy, one read-only check. One step at a
time. Nothing here changes data. The agent guides the owner and records the
results in `docs/ops-runbook.md` → "Printed bulletin PR 3a record", never
with an email address, a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL and the artifact's size.

### Step 2: Count the saved services and the database's size (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run:

```sql
-- Read-only: the database before 0007. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM services) AS services,
       (SELECT count(*) FROM services WHERE bulletin IS NOT NULL) AS with_bulletin,
       pg_size_pretty(pg_database_size(current_database())) AS database_size;
```

One row. Expected before the merge: `version` is `0006_services_bulletin`
(anything else: stop); `services` the saved services in all churches,
`with_bulletin` those saved with the Bulletin step's fields, and
`database_size` the whole database today (the free plan holds 500 MB; a
stored picture takes at most 0.6 MB, a phone photo usually 0.2-0.5 MB, and
the app stops taking pictures when all churches' together reach 150 MB:
"Checking the cover pictures' storage" below).

### Step 3: Read the SQL the upgrade will run

The agent renders it from the PR's code without connecting to any database
(from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0006_services_bulletin:0007_bulletin_images --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//'
```

Expected, exactly (`backend/tests/test_migrations.py` pins it):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
CREATE TABLE bulletin_images (
    id UUID NOT NULL,
    church_id UUID NOT NULL,
    content_type VARCHAR NOT NULL,
    bytes BYTEA NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY(church_id) REFERENCES churches (id) ON DELETE CASCADE,
    FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE SET NULL
);
CREATE INDEX ix_bulletin_images_church_created ON bulletin_images (church_id, created_at);
ALTER TABLE bulletin_images ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon')
     AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    REVOKE ALL ON bulletin_images FROM anon, authenticated;
  END IF;
END $$;
UPDATE alembic_version SET version_num='0007_bulletin_images' WHERE alembic_version.version_num = '0006_services_bulletin';
COMMIT;
```

One new, empty table for the cover pictures, its index, row-level security
and no grant to Supabase's `anon` and `authenticated` roles (so Supabase's
own web API shows none of its rows; the `DO` block does that only where both
roles exist, as `0003_lockdown` does), in one transaction: no existing row
is copied, changed or deleted. If another
connection holds a lock on `churches` or `users` for more than 5 s, the
deploy fails and the previous release keeps serving; run the deploy again.

### Step 4: After the deploy (read-only)

SQL Editor:

```sql
-- Read-only: is 0007 applied, and closed to Supabase's web API? Changes nothing.
-- Before 0007 is applied it still runs: 0006_services_bulletin, NULL, 0, NULL.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass('public.bulletin_images')) AS row_security,
       (SELECT count(*) FROM information_schema.role_table_grants
         WHERE table_schema = 'public' AND table_name = 'bulletin_images'
           AND grantee IN ('anon', 'authenticated')) AS open_grants,
       (SELECT (xpath('/row/n/text()', query_to_xml('SELECT count(*) AS n FROM public.bulletin_images',
                                                     false, true, '')))[1]::text::int
         WHERE to_regclass('public.bulletin_images') IS NOT NULL) AS pictures;
```

Expected: `0007_bulletin_images`, `true`, `0` and `0` (no page uploads a
picture until PR 3b). `0006_services_bulletin` with two empty (NULL) values
means the deploy has not applied 0007 yet: wait a minute and run it again. Then step 2's query again: the same `services` and
`with_bulletin` (or more, by the services saved since the deploy; never
fewer) and about the same `database_size`.

### Checking the cover pictures' storage (any time, read-only)

Any Google account can create a church, so the app limits what pictures can
take (plan review of 2026-10-03): a stored picture is at most 0.6 MB; a
church keeps at most 160 (past that its oldest picture no saved service uses
makes room, and when all 160 are in saved services the upload says so); and
when all churches' pictures together reach 150 MB, every upload is refused
with "The app has no room for more pictures right now. Please tell the
app's administrator." and Railway's log has a
`bulletin_images.storage_full` warning. A picture no saved service uses
goes 60 days after its upload, on any church's next upload. To see where
things stand (SQL Editor):

```sql
-- Read-only: the cover pictures' storage. Changes nothing.
SELECT count(*) AS pictures,
       count(DISTINCT church_id) AS churches,
       pg_size_pretty(coalesce(sum(octet_length(bytes)), 0)) AS pictures_size,
       coalesce((SELECT max(n) FROM (SELECT count(*) AS n FROM bulletin_images GROUP BY church_id) AS c), 0)
         AS most_in_one_church,
       pg_size_pretty(pg_database_size(current_database())) AS database_size
  FROM bulletin_images;
```

`pictures_size` near 150 MB (or `most_in_one_church` at 160 for a church
that is not yours) is the time to look closer: the oldest unused pictures go
on their own after 60 days; a church made only to fill the storage can be
removed with the agent's help (its pictures go with it).

### Reverting PR 3b or PR 3a

PR 3b (the upload on the Bulletin step) changes no schema: revert it first,
as the plan's Step R says. Revert PR 3a only after PR 3b is reverted and
live (PR 3b's pages send `cover_image_id` and upload pictures, which the API
before 3a refuses). For PR 3a the schema stays at `0007_bulletin_images`:
the table is new and the code before 3a ignores it. Revert the merge
commit, then restore `backend/migrations/versions/0007_bulletin_images.py`
and the `BulletinImage` model in `backend/db/models.py` from the merge
commit in the same PR, so Railway's `alembic upgrade head` still finds the
database at head and `alembic check` stays clean. Never `alembic downgrade`
production for this: the pictures uploaded since the merge stay in the
table, unread, and come back when 3a does.
````

- [ ] **Step 4 (agent): Run the files, the offline SQL and the suite (and Postgres if at hand)**

Run: `.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_models.py 2>&1 | tail -1` then `(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0006_services_bulletin:0007_bulletin_images --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//')` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:** `79 passed, 7 skipped in <t>s`; the 27 lines of README step 3 exactly (`BEGIN;` … `COMMIT;`, the `DO` block of the REVOKE before the version update); `1436 passed, 21 skipped in <t>s`. With a local Postgres also `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `21 passed, 1436 deselected, 1 warning in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/migrations/versions/0007_bulletin_images.py backend/db/models.py backend/migrations/README.md backend/tests/test_api_app.py backend/tests/test_schema_check.py backend/tests/test_migrations.py backend/tests/test_services_postgres.py
git commit -q -m "Migration 0007_bulletin_images: the cover pictures' table and the owner's steps" -m "Printed bulletin PR 3a (planning answers 9, 10): bulletin_images (id,
church_id cascading with the church, content_type, bytes, width, height,
created_by set null, created_at), the index ix_bulletin_images_church_created
for the 60-day removal, and on Postgres row-level security, as 0003 left
every other public table, and 0003's guarded REVOKE for this table
(Supabase's anon and authenticated roles read no row and hold no grant).
Expand-only: no other table changes. backend/migrations/README.md gains
\"Before 0007_bulletin_images\": the backup, the read-only counts with the
database's size, the SQL preview (pinned by a test, trailing spaces
stripped), the after-deploy check (it also answers before 0007 is applied),
the pictures' storage check, and how to revert." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1436 passed, 21 skipped`; frontend `704 passed` in 87 files.

### Task 2: The picture's module and the printed cover (planning answers 2-6; S "Data model", "What prints where"; clarifications 2-5)

**Files:**
- Create: `backend/tests/picture_helpers.py`, `backend/tests/test_bulletin_image.py`, `backend/bulletin_image.py`
- Modify: `backend/tests/test_service_bulletin.py`, `backend/tests/test_printed_bulletin.py`, `backend/tests/test_printed_render.py`, `backend/service_bulletin.py`, `backend/printed_bulletin.py`, `backend/printed_pdf.py`, `backend/printed_docx.py`

Pure modules only; the API (and "cover" among the boxes to check, which changes the API's `unchecked`) is T3's. `WEEK` in the tests does not say `cover_image_id`, so every earlier test still prints PR 1's box. The plan review's cases (clarifications 2 and 20) are tests here: a phone's multi-picture JPEG, a 16-bit grey PNG, a color profile with and without transparency (`picture_helpers.swapped_profile`, an invented profile with red and blue swapped, so the conversion shows), a busy picture stored in at most 600 KB, an upload that cannot start in time, four 24 MP PNGs at once in a subprocess (the peak memory of one; the test takes about 2 s), and the two lines shrinking together.

- [ ] **Step 1: Write the failing tests**

**Create `backend/tests/picture_helpers.py`:**

````python
"""Invented test pictures for the cover picture tests (printed bulletin PR 3): made here with Pillow,
never a real photo."""
import struct
from io import BytesIO

from PIL import Image, ImageCms

RED, GREEN, BLUE = (220, 30, 30), (30, 160, 60), (30, 60, 220)


def picture(size=(400, 300), fmt="JPEG", color=GREEN, mode="RGB", **save) -> bytes:
    """A plain picture of one color."""
    out = BytesIO()
    Image.new(mode, size, color).save(out, fmt, **save)
    return out.getvalue()


def stripes(size, colors, *, horizontal=True, fmt="JPEG", **save) -> bytes:
    """Equal stripes of `colors`, top to bottom (or left to right when not horizontal)."""
    img = Image.new("RGB", size)
    n = len(colors)
    for i, color in enumerate(colors):
        if horizontal:
            img.paste(color, (0, size[1] * i // n, size[0], size[1] * (i + 1) // n))
        else:
            img.paste(color, (size[0] * i // n, 0, size[0] * (i + 1) // n, size[1]))
    out = BytesIO()
    img.save(out, fmt, **save)
    return out.getvalue()


def opened(data: bytes) -> Image.Image:
    img = Image.open(BytesIO(data))
    img.load()
    return img


def near(pixel, color, tolerance=40) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(pixel, color))


def swapped_profile() -> bytes:
    """An invented color profile: sRGB with its red and blue primaries swapped, so a conversion to sRGB
    shows (a green of (30, 160, 60) becomes about (60, 160, 30))."""
    data = bytearray(ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes())
    count = struct.unpack(">I", data[128:132])[0]
    at = {bytes(data[132 + 12 * i:136 + 12 * i]): 132 + 12 * i for i in range(count)}
    red, blue = at[b"rXYZ"], at[b"bXYZ"]
    data[red + 4:red + 12], data[blue + 4:blue + 12] = data[blue + 4:blue + 12], data[red + 4:red + 12]
    return bytes(data)
````

**Create `backend/tests/test_bulletin_image.py`:**

````python
"""The cover picture (printed bulletin spec, "Data model"; PR 3 planning
answers 2-5; bulletin_image.py): an upload checked, turned upright, scaled
and stored as JPEG; the cover's box made from it. Invented pictures only
(tests/picture_helpers.py)."""
import random
import subprocess
import sys
import threading
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageCms, ImageDraw

import bulletin_image as bi
from domain_errors import InvalidInput, RateLimited
from tests.picture_helpers import BLUE, GREEN, RED, near, opened, picture, stripes, swapped_profile


def test_a_large_photo_is_stored_as_a_jpeg_at_most_1600_px_on_its_long_side():
    stored = bi.prepare(stripes((4000, 3000), [RED, GREEN, BLUE]))
    img = opened(stored.content)
    assert (img.format, img.size, (stored.width, stored.height)) == ("JPEG", (1600, 1200), (1600, 1200))
    assert near(img.getpixel((800, 100)), RED) and near(img.getpixel((800, 1100)), BLUE)
    assert bi.CONTENT_TYPE == "image/jpeg"


def test_a_photo_is_turned_upright():
    """A phone stores a portrait photo sideways with an EXIF orientation (6: turn it a quarter clockwise)."""
    exif = Image.Exif()
    exif[0x0112] = 6
    stored = bi.prepare(stripes((400, 200), [RED, BLUE], horizontal=False, exif=exif.tobytes()))
    img = opened(stored.content)
    assert img.size == (200, 400)                                   # now a portrait
    assert near(img.getpixel((100, 50)), RED) and near(img.getpixel((100, 350)), BLUE)


def test_a_small_png_keeps_its_size_and_a_transparent_part_turns_white():
    png = BytesIO()
    img = Image.new("RGBA", (300, 200), (0, 0, 0, 0))
    img.paste((30, 160, 60, 255), (0, 0, 150, 200))
    img.save(png, "PNG")
    stored = bi.prepare(png.getvalue())
    out = opened(stored.content)
    assert (out.format, out.mode, out.size) == ("JPEG", "RGB", (300, 200))   # never enlarged
    assert near(out.getpixel((50, 100)), GREEN) and near(out.getpixel((250, 100)), (255, 255, 255))


def test_the_stored_picture_keeps_no_camera_data():
    """No EXIF (a phone's location and time) and no color profile: the colors are converted to sRGB."""
    exif = Image.Exif()
    exif[0x0110] = "Example Phone"
    exif[0x8825] = {1: "N", 2: (40.0, 0.0, 0.0)}
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    stored = bi.prepare(picture((800, 600), exif=exif.tobytes(), icc_profile=icc))
    img = opened(stored.content)
    assert "exif" not in img.info and "icc_profile" not in img.info
    assert near(img.getpixel((400, 300)), GREEN)


@pytest.mark.parametrize("data, message", [
    (picture(fmt="GIF", mode="P", color=1), bi.NOT_A_PICTURE_MESSAGE),
    (picture(fmt="BMP"), bi.NOT_A_PICTURE_MESSAGE),
    (b"%PDF-1.4 not a picture", bi.NOT_A_PICTURE_MESSAGE),
    (picture()[:600], bi.NOT_A_PICTURE_MESSAGE),                              # cut short
    (b"", bi.NOT_A_PICTURE_MESSAGE),
    (picture((8000, 7000), fmt="JPEG", mode="L", color=128), bi.TOO_MANY_PIXELS_MESSAGE),               # 56 MP
    (picture((5000, 5000), fmt="PNG", mode="1", color=1), bi.TOO_MANY_PIXELS_MESSAGE),        # a 25 MP PNG
    (picture((11000, 10000), fmt="PNG", mode="1", color=1), bi.TOO_MANY_PIXELS_MESSAGE),      # Pillow's own guard
    (b"\xff" * (10 * 1024 * 1024 + 1), bi.TOO_LARGE_MESSAGE),
])
def test_only_a_jpeg_or_png_of_at_most_10_mb_and_50_million_pixels_is_taken(data, message):
    with pytest.raises(InvalidInput) as raised:
        bi.prepare(data)
    assert (raised.value.message, raised.value.field, raised.value.status) == (message, "image", 422)


def test_the_cover_fills_the_box_with_a_centered_crop_and_a_dark_band():
    """Planning answers 2-4: a tall picture in a wide box keeps its middle (the top and bottom are trimmed
    evenly); the reading and the date are white on a dark see-through band across the bottom; color stays."""
    tall = bi.prepare(stripes((600, 1200), [RED, GREEN, GREEN, GREEN, BLUE])).content
    box = opened(bi.cover(tall, [("Matthew 21:23-32", 75), ("October 11, 2026", 58)], (1550, 1250)))
    assert (box.format, box.mode, box.size) == ("JPEG", "RGB", (1550, 1250))
    assert near(box.getpixel((5, 5)), GREEN) and near(box.getpixel((775, 600)), GREEN)   # no red: trimmed
    band = [box.getpixel((x, 1240)) for x in (5, 1545)]
    assert all(near(pixel, tuple(round(c * (1 - bi.BAND_OPACITY)) for c in GREEN), 25) for pixel in band)
    row = [box.getpixel((x, y)) for y in range(1050, 1250, 4) for x in range(300, 1250, 4)]
    assert any(min(pixel) > 230 for pixel in row)                                           # white letters
    plain = opened(bi.cover(tall, [("", 75)], (1550, 1250)))
    assert near(plain.getpixel((5, 1240)), GREEN)                                           # nothing to say: no band


def test_a_long_reading_is_shrunk_to_fit_the_band():
    long = "1 Corinthians 15:1-11, 12-20, 35-38, 42-50 or Psalm 23 or Psalm 100"
    box = opened(bi.cover(picture((1600, 1200)), [(long, 75), ("October 11, 2026", 58)], (1550, 1250)))
    edges = [box.getpixel((x, y)) for y in range(1000, 1250, 2) for x in (2, 1547)]
    assert not any(min(pixel) > 230 for pixel in edges)                                     # no letter at the edge


# --- plan review fixes (2026-10-03): phone JPEGs, memory, stored size, odd PNGs, the band ---

def test_a_phone_s_multi_picture_jpeg_is_taken_as_a_jpeg():
    """An iPhone HDR or a Samsung portrait photo carries a second picture (Pillow reads it as "MPO")."""
    exif = Image.Exif()
    exif[0x0112] = 6
    out = BytesIO()
    Image.new("RGB", (4032, 3024), GREEN).save(out, "MPO", save_all=True, exif=exif.tobytes(),
                                               append_images=[Image.new("RGB", (1008, 756), RED)])
    assert Image.open(BytesIO(out.getvalue())).format == "MPO"
    stored = bi.prepare(out.getvalue())
    img = opened(stored.content)
    assert (img.format, img.size) == ("JPEG", (1200, 1600))                           # upright, the first picture
    assert near(img.getpixel((600, 800)), GREEN)


def test_a_16_bit_grey_png_keeps_its_tones():
    out = BytesIO()
    Image.new("I;16", (300, 200), 32768).save(out, "PNG")                              # mid-grey, 16 bits
    assert near(opened(bi.prepare(out.getvalue()).content).getpixel((150, 100)), (128, 128, 128), 3)


@pytest.mark.parametrize("mode", ["RGB", "RGBA"])
def test_a_color_profile_is_converted_to_srgb_with_or_without_transparency(mode):
    out = BytesIO()
    Image.new(mode, (300, 200), GREEN + (255,) * (mode == "RGBA")).save(out, "PNG", icc_profile=swapped_profile())
    assert near(opened(bi.prepare(out.getvalue()).content).getpixel((150, 100)), (60, 160, 30), 6)


def test_a_busy_picture_is_stored_in_at_most_600_kb():
    """Noise is the worst case for JPEG: a lower quality, then a smaller size, until it fits."""
    noise = Image.frombytes("RGB", (1600, 1600), random.Random(7).randbytes(1600 * 1600 * 3))
    png = BytesIO()
    noise.save(png, "PNG")
    stored = bi.prepare(png.getvalue())
    img = opened(stored.content)
    assert len(stored.content) <= bi.MAX_STORED_BYTES == 600_000
    assert img.format == "JPEG" and img.size == (stored.width, stored.height) and 800 <= stored.width < 1600
    assert len(bi.prepare(stripes((4000, 3000), [RED, GREEN, BLUE])).content) < 100_000      # a plain one: as is


def test_an_upload_waits_its_turn_then_is_told_to_try_again():
    """One picture is prepared at a time; one that cannot start within the wait is a 429."""
    release = threading.Event()
    busy = bi._WORKER.submit(release.wait, 10)
    try:
        with pytest.raises(RateLimited) as raised:
            bi.prepare(picture(), wait=0.05)
        assert (raised.value.message, raised.value.retry_after_seconds) == (bi.BUSY_MESSAGE, 5)
    finally:
        release.set()
        busy.result()
    assert bi.prepare(picture()).width == 400


MEMORY_PROBE = """
import resource, sys
from concurrent.futures import ThreadPoolExecutor
import bulletin_image as bi
data = open(sys.argv[1], "rb").read()
bi.prepare(open(sys.argv[2], "rb").read())                                  # warm up
before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
with ThreadPoolExecutor(4) as pool:
    sizes = [p.width for p in pool.map(lambda _: bi.prepare(data), range(4))]
print(sizes, (resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - before) // 1024)
"""


def test_four_large_pngs_at_once_take_the_memory_of_one(tmp_path):
    """The worst PNG taken (24 million pixels, a palette with transparency, a 3 KB file) needs about 220 MB
    to prepare; four arriving together are prepared one after another on one thread, so they need no more
    (a subprocess, so the peak is this upload's own)."""
    big = tmp_path / "big.png"
    Image.new("P", (4898, 4898), 0).save(big, transparency=0)
    small = tmp_path / "small.jpg"
    small.write_bytes(picture())
    backend = Path(bi.__file__).resolve().parent
    run = subprocess.run([sys.executable, "-c", MEMORY_PROBE, str(big), str(small)], cwd=backend,
                         capture_output=True, text=True, check=True)
    sizes, megabytes = run.stdout.rsplit(" ", 1)
    assert sizes == "[1600, 1600, 1600, 1600]"
    assert int(megabytes) < 300, run.stdout


def test_a_long_reading_and_the_date_shrink_together():
    """A reading too long for the band is made smaller, and the date with it, so it never prints smaller
    than the date under it."""
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    long = "1 Corinthians 15:1-11, 12-20, 35-38, 42-50 or Psalm 23 or Psalm 100"
    reading, date = bi.fitted_sizes(draw, [(long, 75), ("October 11, 2026", 58)], 1395)
    assert reading < 75 and reading >= date and abs(reading / date - 75 / 58) < 0.1
    assert draw.textlength(long, font=bi._font(reading)) <= 1395
    assert bi.fitted_sizes(draw, [("Matthew 22:1-14", 75), ("October 11, 2026", 58)], 1395) == [75, 58]
````

**Append to `backend/tests/test_service_bulletin.py`:**

````python


def test_the_cover_picture_is_read_stored_and_carried():
    """PR 3a: cover_image_id is a picture's id or None (no picture this week); a bulletin that does not say
    (a page from before PR 3b) is cover_given False and stores no key. It carries forward with the music."""
    picture_id = "0B4C2B0E-1111-4222-8333-444455556666"
    week = sb.read({"cover_image_id": picture_id, "prelude": {"title": "Morning Voluntary"},
                    "people": {"organist": "Sam Sample"}})
    assert (week.cover_image_id, week.cover_given) == (picture_id.lower(), True)
    assert week.to_json()["cover_image_id"] == picture_id.lower()
    assert sb.read(week.to_json()) == week
    assert week.carried() == sb.ServiceBulletin(prelude=sb.Music("Morning Voluntary", ""),
                                                cover_image_id=picture_id.lower(), cover_given=True)
    assert week.map_texts(str.upper).cover_image_id == picture_id.lower()
    none = sb.read({"cover_image_id": None})
    assert (none.cover_image_id, none.cover_given, none.to_json()["cover_image_id"]) == (None, True, None)
    for unsaid in ({}, {"prelude": {"title": "x"}}):
        assert (sb.read(unsaid).cover_given, "cover_image_id" in sb.read(unsaid).to_json()) == (False, False)
    for bad in ("later", 7, "", ["x"]):
        assert (sb.read({"cover_image_id": bad}).cover_image_id, sb.read({"cover_image_id": bad}).cover_given) == (
            None, True)
````

**Append to `backend/tests/test_printed_bulletin.py`:**

````python


def test_the_cover_holds_the_picture_the_reading_alone_or_pr_1_s_box():
    """PR 3a (printed_bulletin.cover_kind): the week's picture; no picture this week, or one no longer there:
    the reading and the date alone (PR 3 planning answer 6); no bulletin, or one that did not say (a page
    from before PR 3b): PR 1's [Cover picture] box, as before."""
    picture_id = "0b4c2b0e-1111-4222-8333-444455556666"
    chosen = dataclasses.replace(WEEK, cover_image_id=picture_id, cover_given=True)
    cases = [
        (service(bulletin=None), "placeholder"),
        (service(), "placeholder"),                                        # WEEK does not say
        (service(bulletin=chosen, cover_picture=b"\xff\xd8"), "picture"),
        (service(bulletin=chosen), "none"),                                # the picture is no longer there
        (service(bulletin=dataclasses.replace(WEEK, cover_given=True)), "none"),
    ]
    for ps, kind in cases:
        assert pb.cover_kind(ps) == kind
        label = "[Cover picture]" if kind == "placeholder" else ""
        assert texts(pb.cover(ps))[:4] == ["Example Church", label, "Matthew 21:33-46", "October 4, 2026"]
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
from docx.shared import Inches
from pypdf import PdfReader

````

**with:**

````python
from docx.shared import Inches, Pt
from pypdf import PdfReader

import bulletin_image
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
import service_bulletin as sb
````

**with:**

````python
import service_bulletin as sb
from tests import picture_helpers
````

**In `backend/tests/test_printed_render.py`, replace:**

````python
    assert doc.paragraphs[-1].text == "*Congregation stands if able"
````

**with:**

````python
    assert doc.paragraphs[-1].text == "*Congregation stands if able"


def chosen(picture: bytes | None = None, **cover) -> pb.PrintedService:
    week = dataclasses.replace(WEEK, cover_given=True, **cover)
    return dataclasses.replace(service(), bulletin=week, cover_picture=picture)


def test_the_cover_picture_fills_the_box_in_both_files():
    """PR 3 planning answers 2-4: the same picture in the PDF and the Word version, 372 x 300 pt under the
    church's name, the reading and the date on its band (inside the picture, so not text)."""
    ps = chosen(bulletin_image.prepare(picture_helpers.stripes((1600, 1200), [picture_helpers.GREEN])).content,
                cover_image_id="0b4c2b0e-1111-4222-8333-444455556666")
    content = printed_pdf.render_pdf(ps)
    (image,) = PdfReader(BytesIO(content)).pages[0].images
    assert image.image.size == (1550, 1250)
    assert halves(content)[0].startswith("Example Church 100 Example Street")
    doc = Document(BytesIO(printed_docx.render_docx(ps)))
    (shape,) = doc.inline_shapes
    assert (shape.width, shape.height) == (Pt(372), Pt(300))
    assert doc.tables == [] and "[Cover picture]" not in [p.text for p in doc.paragraphs]
    word_picture = doc.part.related_parts[shape._inline.graphic.graphicData.pic.blipFill.blip.embed].blob
    assert word_picture == printed_pdf.cover_picture(ps)                   # the PDF's picture, byte for byte


def test_no_picture_prints_the_reading_and_the_date_where_it_would_be():
    """PR 3 planning answer 6: no box at all; the reading and the date centered in its place."""
    ps = chosen()
    content = printed_pdf.render_pdf(ps)
    assert len(PdfReader(BytesIO(content)).pages[0].images) == 0
    assert halves(content)[0].startswith("Example Church Matthew 21:23-32 September 27, 2026 100 Example Street")
    doc = Document(BytesIO(printed_docx.render_docx(ps)))
    assert doc.tables == [] and len(doc.inline_shapes) == 0
    reading, date = doc.paragraphs[1:3]
    assert (reading.text, date.text) == ("Matthew 21:23-32", "September 27, 2026")
    assert reading.runs[0].bold and reading.runs[0].font.size == Pt(18) and date.runs[0].font.size == Pt(14)
    assert reading.paragraph_format.space_before == date.paragraph_format.space_after > Pt(100)
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_bulletin_image.py backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py 2>&1 | tail -3` then `.venv/bin/python -m pytest -q backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py 2>&1 | tail -1`
**Expected** (`bulletin_image` does not exist yet: `ModuleNotFoundError` above these lines):
```
ERROR backend/tests/test_printed_render.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!
2 errors in <t>s
```
then `2 failed, 26 passed in <t>s` (`cover_image_id` and `cover_kind` do not exist yet).

- [ ] **Step 3: `bulletin_image`, the week's picture and the three covers**

**Create `backend/bulletin_image.py`:**

````python
"""The printed bulletin's cover picture (printed bulletin spec, "Data model";
PR 3 planning answers 2-6), with Pillow (installed with reportlab).

- prepare(data): an upload made ready to store (POST /bulletin-images). It
  must be at most 10 MB, a JPEG or a PNG (planning answer 5: no HEIC; an
  iPhone's Safari sends a JPEG; a phone's multi-picture JPEG, which Pillow
  calls "MPO", is a JPEG) and at most 50 million pixels (24 million for a
  PNG, which is decoded whole). It is turned upright (its EXIF
  orientation), its colors converted to sRGB when it carries a color
  profile (an iPhone's Display P3), a transparent part laid on white,
  scaled down to at most 1600 px on its long side (never up), and stored as
  a JPEG with no camera data (no EXIF, so no location or time) of at most
  MAX_STORED_BYTES (a lower quality, then a smaller size, until it fits).
  A JPEG is decoded at a reduced scale when it is much larger (draft mode),
  and a large PNG is reduced before anything else is done to it, so the
  memory one upload takes stays bounded; one upload is prepared at a time in
  the process (one worker thread), and another waits its turn up to
  BUSY_WAIT_SECONDS, then is a 429 (BUSY_MESSAGE). Anything else is a 422 naming the field "image".
- cover(picture, lines, size): the cover's box as both printed files show it
  (planning answers 2-4): the picture scaled to fill `size` and trimmed
  evenly at the edges (a centered crop), in color, with a dark see-through
  band across its bottom holding `lines` (the reading and the date) in
  white, centered, shrunk together to fit the width. A JPEG; the PDF and the
  Word version place the same picture, so they look the same.
Pure: no database, FastAPI or rendering library (the band's font is the
Times Bold outline that reportlab ships).
"""
from __future__ import annotations

import os
import warnings
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as Waited
from collections.abc import Sequence
from dataclasses import dataclass
from io import BytesIO

import reportlab
from PIL import Image, ImageCms, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from domain_errors import InvalidInput, RateLimited

MAX_UPLOAD_BYTES = 10 * 1024 * 1024          # planning answer: at most 10 MB in
MAX_PIXELS = 50_000_000                      # a JPEG: more than any phone camera's 48 MP
MAX_PNG_PIXELS = 24_000_000                  # a PNG (a screenshot or a graphic), decoded whole
MAX_SIDE = 1600                              # the stored picture's long side, at most
MAX_STORED_BYTES = 600_000                   # the stored JPEG, at most (plan review C3)
CONTENT_TYPE = "image/jpeg"                  # what is stored and served
FORMATS = ("JPEG", "MPO", "PNG")             # planning answer 5; MPO: a phone's multi-picture JPEG
OPENERS = ("JPEG", "PNG")                    # the only parsers tried (Pillow opens an MPO with JPEG's)
# The stored JPEG's long side and quality, tried in turn until it is at most MAX_STORED_BYTES.
ENCODINGS = ((1600, 85), (1600, 75), (1400, 70), (1200, 65), (1000, 60), (800, 60))
BUSY_WAIT_SECONDS = 10.0                     # how long an upload waits for the one before it
BUSY_RETRY_SECONDS = 5

TOO_LARGE_MESSAGE = "The picture is larger than 10 MB. Choose a smaller one."
NOT_A_PICTURE_MESSAGE = "Choose a JPEG or PNG picture."
TOO_MANY_PIXELS_MESSAGE = "The picture has too many pixels. Choose a smaller one."
BUSY_MESSAGE = "Another picture is being prepared. Try again in a few seconds."

# The band: black at this opacity, its text white (planning answer 2).
BAND_OPACITY = 0.55
# Times Bold's outline, as reportlab ships it (the PDF's standard Times-Bold has no file of its own).
FONT_FILE = os.path.join(os.path.dirname(reportlab.__file__), "fonts", "_eb_____.pfb")

# EXIF orientation (a phone stores a portrait photo sideways): the turn that makes it upright.
ORIENTATION = 0x0112
TURNS = {2: Image.Transpose.FLIP_LEFT_RIGHT, 3: Image.Transpose.ROTATE_180, 4: Image.Transpose.FLIP_TOP_BOTTOM,
         5: Image.Transpose.TRANSPOSE, 6: Image.Transpose.ROTATE_270, 7: Image.Transpose.TRANSVERSE,
         8: Image.Transpose.ROTATE_90}

# Pillow's own guard against a picture that claims more pixels than its file holds: it refuses one
# past twice this as it opens it (a 422 here). The process opens no other large picture.
Image.MAX_IMAGE_PIXELS = MAX_PIXELS
# One upload is decoded and prepared at a time in the process (plan review C2), always on this one thread:
# uploads arriving together queue here instead of adding up, and the memory a picture took is reused by
# the next (the C allocator keeps freed memory per thread, so twenty threads taking turns would each keep
# their own).
_WORKER = ThreadPoolExecutor(max_workers=1, thread_name_prefix="bulletin-image")


@dataclass(frozen=True)
class Prepared:
    content: bytes          # the JPEG to store
    width: int
    height: int


def _invalid(message: str) -> InvalidInput:
    return InvalidInput(message, field="image")


def _target(width: int, height: int) -> tuple[int, int]:
    """The size `thumbnail` gives: the long side at most MAX_SIDE, the ratio kept."""
    scale = min(1.0, MAX_SIDE / max(width, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


def _smaller(img: Image.Image) -> Image.Image:
    """The decoded picture at most MAX_SIDE on its long side, in a mode Pillow scales well. A large one is
    first reduced by a whole factor (box averaging into a new, small picture: no second copy at full size)."""
    if img.mode.startswith("I;16") or img.mode == "I":
        img = img.point(lambda v: v * (1 / 256)).convert("L")       # 16-bit grey: keep its tones (not clipped)
    elif img.mode == "P":
        img = img.convert("RGBA" if "transparency" in img.info else "RGB")
    elif img.mode not in ("RGB", "RGBA", "L", "LA", "CMYK"):
        bands = img.getbands()
        img = img.convert("RGBA" if "A" in bands else "L" if len(bands) == 1 else "RGB")
    factor = max(img.size) // MAX_SIDE
    if factor >= 2:
        img = img.reduce(factor)
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    return img


def _rgb(img: Image.Image, icc: bytes | None) -> Image.Image:
    """RGB in sRGB: a transparent part laid on white; a color profile converted (kept as is if unreadable)."""
    if "A" in img.getbands():
        flat = Image.new("RGB", img.size, "white")
        flat.paste(img.convert("RGB"), mask=img.getchannel("A"))
        img = flat
    if icc and img.mode in ("RGB", "CMYK"):
        try:
            return ImageCms.profileToProfile(img, ImageCms.ImageCmsProfile(BytesIO(icc)),
                                             ImageCms.createProfile("sRGB"), outputMode="RGB")
        except (ImageCms.PyCMSError, OSError, ValueError):
            pass
    return img if img.mode == "RGB" else img.convert("RGB")


def _encoded(picture: Image.Image) -> tuple[bytes, int, int]:
    """The JPEG to store: the first of ENCODINGS of at most MAX_STORED_BYTES (the last one otherwise)."""
    for side, quality in ENCODINGS:
        img = picture
        if max(picture.size) > side:
            img = picture.copy()
            img.thumbnail((side, side), Image.Resampling.LANCZOS)
        out = BytesIO()
        img.save(out, "JPEG", quality=quality, optimize=True)
        if out.tell() <= MAX_STORED_BYTES:
            break
    return out.getvalue(), img.width, img.height


def _prepared(data: bytes) -> Prepared:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)     # the check below says it
            img = Image.open(BytesIO(data), formats=OPENERS)
        if img.format not in FORMATS:
            raise _invalid(NOT_A_PICTURE_MESSAGE)
        limit = MAX_PNG_PIXELS if img.format == "PNG" else MAX_PIXELS
        if img.width * img.height > limit:
            raise _invalid(TOO_MANY_PIXELS_MESSAGE)
        icc = img.info.get("icc_profile")                           # read before anything drops `info`
        orientation = img.getexif().get(ORIENTATION, 1)
        if img.format != "PNG":
            img.draft("RGB", _target(img.width, img.height))       # decode at 1/2, 1/4 or 1/8 when it can
        img.load()
        img = _smaller(img)                                         # the decoded original is let go here
        img = img.transpose(TURNS[orientation]) if orientation in TURNS else img     # upright
        picture = _rgb(img, icc)
    except Image.DecompressionBombError:
        raise _invalid(TOO_MANY_PIXELS_MESSAGE) from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise _invalid(NOT_A_PICTURE_MESSAGE) from None
    content, width, height = _encoded(picture)
    return Prepared(content, width, height)


def prepare(data: bytes, *, wait: float = BUSY_WAIT_SECONDS) -> Prepared:
    """The upload checked and made ready to store (see the module docstring)."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise _invalid(TOO_LARGE_MESSAGE)
    if not data:
        raise _invalid(NOT_A_PICTURE_MESSAGE)
    job = _WORKER.submit(_prepared, data)
    try:
        return job.result(timeout=wait)
    except Waited:
        if job.cancel():                                            # still waiting its turn: not started
            raise RateLimited(BUSY_MESSAGE, retry_after_seconds=BUSY_RETRY_SECONDS) from None
        return job.result()                                         # started: it finishes in about a second


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_FILE, size)


def fitted_sizes(draw: ImageDraw.ImageDraw, lines: Sequence[tuple[str, int]], width: int) -> list[int]:
    """The lines' pixel sizes, all shrunk by the same factor until every line fits `width` (so a long
    reading is never smaller than the date under it), at least 8 px."""
    scale = 1.0
    for text, px in lines:
        length = draw.textlength(text, font=_font(px))
        if length > width:
            scale = min(scale, width / length)
    sizes = [max(8, int(px * scale)) for _text, px in lines]
    while any(draw.textlength(text, font=_font(size)) > width for (text, _px), size in zip(lines, sizes)) \
            and max(sizes) > 8:
        sizes = [max(8, size - 1) for size in sizes]
    return sizes


def cover(picture: bytes, lines: Sequence[tuple[str, int]], size: tuple[int, int]) -> bytes:
    """The cover's box (see the module docstring). `lines` are (text, pixel size), top to bottom; blank ones
    are left out, and with none there is no band."""
    width, height = size
    with Image.open(BytesIO(picture)) as img:
        box = ImageOps.fit(img.convert("RGB"), size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    lines = [(text, px) for text, px in lines if text.strip()]
    if lines:
        draw = ImageDraw.Draw(box)
        margin = round(width * 0.05)
        fonts = [_font(px) for px in fitted_sizes(draw, lines, width - 2 * margin)]
        gap = round(min(px for _text, px in lines) * 0.45)
        heights = [font.getbbox(text)[3] - font.getbbox(text)[1] for (text, _px), font in zip(lines, fonts)]
        pad = round(min(px for _text, px in lines) * 0.6)
        band_top = height - (sum(heights) + gap * (len(lines) - 1) + 2 * pad)
        band = Image.new("RGBA", (width, height - band_top), (0, 0, 0, round(255 * BAND_OPACITY)))
        box = Image.alpha_composite(box.convert("RGBA"), Image.new("RGBA", size, (0, 0, 0, 0)))
        box.alpha_composite(band, (0, band_top))
        draw = ImageDraw.Draw(box)
        y = band_top + pad
        for (text, _px), font, h in zip(lines, fonts, heights):
            top = font.getbbox(text)[1]
            draw.text(((width - draw.textlength(text, font=font)) / 2, y - top), text, font=font,
                      fill=(255, 255, 255, 255))
            y += h + gap
        box = box.convert("RGB")
    out = BytesIO()
    box.save(out, "JPEG", quality=90, optimize=True)
    return out.getvalue()
````

**In `backend/service_bulletin.py`, replace:**

````python
  the service is opened again; plan review fix I3).
- read(raw): a stored or posted value read tolerantly: anything that is not
  an object, a missing key or a value of the wrong type is blank (a person
  None); an unknown element key and a blank part leader are dropped; every
````

**with:**

````python
  the service is opened again; plan review fix I3). PR 3a adds the week's
  cover picture: `cover_image_id` (a bulletin_images id, or None for no
  picture this week) and `cover_given` (False when the bulletin did not say,
  as a page from before PR 3b sends it: a PUT then keeps the saved picture
  and the printed bulletin keeps PR 1's [Cover picture] box). The picture
  carries forward with the music.
- read(raw): a stored or posted value read tolerantly: anything that is not
  an object, a missing key or a value of the wrong type is blank (a person
  None; a cover_image_id that is not an id, None); an unknown element key
  and a blank part leader are dropped; every
````

**In `backend/service_bulletin.py`, replace:**

````python
- to_json: the stored shape (what GET /services/{id} answers as `bulletin`).
- carried(): what a new week starts from (PR 2 planning answer 5): the music
  and the announcements; the people, the part leaders, the pasted texts and
  `unchecked` start empty.
````

**with:**

````python
- to_json: the stored shape (what GET /services/{id} answers as `bulletin`);
  "cover_image_id" only when the bulletin said (cover_given).
- carried(): what a new week starts from (PR 2 planning answer 5; PR 3
  planning answer 7): the music, the announcements and the cover picture;
  the people, the part leaders, the pasted texts and `unchecked` start empty.
````

**In `backend/service_bulletin.py`, replace:**

````python
import re
````

**with:**

````python
import re
import uuid
````

**In `backend/service_bulletin.py`, replace:**

````python
    unchecked: tuple[str, ...] = ()
````

**with:**

````python
    unchecked: tuple[str, ...] = ()
    # The week's cover picture (PR 3): a bulletin_images id, None for no picture this week.
    cover_image_id: Optional[str] = None
    # False: the bulletin did not say (a page from before PR 3b; cover_image_id is then None).
    cover_given: bool = False
````

**In `backend/service_bulletin.py`, replace:**

````python
        """What the next week starts from: the music and the announcements."""
        return ServiceBulletin(prelude=self.prelude, postlude=self.postlude, announcements=self.announcements)
````

**with:**

````python
        """What the next week starts from: the music, the announcements and the cover picture."""
        return ServiceBulletin(prelude=self.prelude, postlude=self.postlude, announcements=self.announcements,
                               cover_image_id=self.cover_image_id, cover_given=self.cover_given)
````

**In `backend/service_bulletin.py`, replace:**

````python
            ot_text=fn(self.ot_text), nt_text=fn(self.nt_text), unchecked=self.unchecked)
````

**with:**

````python
            ot_text=fn(self.ot_text), nt_text=fn(self.nt_text), unchecked=self.unchecked,
            cover_image_id=self.cover_image_id, cover_given=self.cover_given)
````

**In `backend/service_bulletin.py`, replace:**

````python
            "unchecked": list(self.unchecked),
````

**with:**

````python
            "unchecked": list(self.unchecked),
            **({"cover_image_id": self.cover_image_id} if self.cover_given else {}),
````

**In `backend/service_bulletin.py`, replace:**

````python
    return tuple(key for key in CARRY_KEYS if key in keys)
````

**with:**

````python
    return tuple(key for key in CARRY_KEYS if key in keys)


def _image_id(value: object) -> Optional[str]:
    """A bulletin_images id as stored (lower-case, with hyphens), or None."""
    if isinstance(value, uuid.UUID):
        return str(value)
    try:
        return str(uuid.UUID(value)) if isinstance(value, str) else None
    except ValueError:
        return None
````

**In `backend/service_bulletin.py`, replace:**

````python
        unchecked=_unchecked(stored.get("unchecked")),
````

**with:**

````python
        unchecked=_unchecked(stored.get("unchecked")),
        cover_image_id=_image_id(stored.get("cover_image_id")),
        cover_given="cover_image_id" in stored,
````

**In `backend/printed_bulletin.py`, replace:**

````python
  The cover picture prints as a [bracketed placeholder] until PR 3.
````

**with:**

````python
- The cover picture (PR 3a; cover_kind): the week's picture with the reading
  and the date over it; with no picture this week, the reading and the date
  alone where the picture would be (PR 3 planning answer 6); and PR 1's
  [Cover picture] box when no bulletin was posted or it did not say (a page
  from before PR 3b), so those pages print as before.
````

**In `backend/printed_bulletin.py`, replace:**

````python
# The cover picture's place, until PR 3 prints the picture.
COVER_PICTURE = "[Cover picture]"
````

**with:**

````python
# The cover picture's place on a page from before PR 3b (cover_kind "placeholder").
COVER_PICTURE = "[Cover picture]"
# The cover's box: the picture's place, 372 x 300 pt (5.17 x 4.17 in), centered under the church's name.
COVER_BOX = (372.0, 300.0)
# The reading's and the date's size on the cover (points), on the picture's band or alone in the box.
COVER_TEXT_POINTS = (18.0, 14.0)
CoverKind = Literal["placeholder", "picture", "none"]
````

**In `backend/printed_bulletin.py`, replace:**

````python
    bulletin: Optional[ServiceBulletin] = None           # the week's own fields (PR 2b); None: none posted
````

**with:**

````python
    bulletin: Optional[ServiceBulletin] = None           # the week's own fields (PR 2b); None: none posted
    cover_picture: Optional[bytes] = None                # the week's cover picture as stored (PR 3a), if any
````

**In `backend/printed_bulletin.py`, replace:**

````python
def cover(ps: PrintedService) -> list[Line]:
    """The front page: the church's name, the picture's place with the
    sermon reading and the date over it, and the church's contact lines."""
````

**with:**

````python
def cover_kind(ps: PrintedService) -> CoverKind:
    """What the cover's box holds: "picture" (the week's picture, with the
    reading and the date on a band over it), "none" (no picture this week, or
    one no longer there: the reading and the date alone), or "placeholder"
    (no bulletin posted, or one that did not say: PR 1's box)."""
    if ps.bulletin is None or not ps.bulletin.cover_given:
        return "placeholder"
    return "picture" if ps.bulletin.cover_image_id and ps.cover_picture else "none"


def cover(ps: PrintedService) -> list[Line]:
    """The front page: the church's name, the picture's place (its label
    only for the placeholder) with the sermon reading and the date over it,
    and the church's contact lines."""
````

**In `backend/printed_bulletin.py`, replace:**

````python
        Line("box", (Span(COVER_PICTURE),)),
````

**with:**

````python
        Line("box", (Span(COVER_PICTURE if cover_kind(ps) == "placeholder" else ""),)),
````

**In `backend/printed_pdf.py`, replace:**

````python
page count leaves the last side's right half blank.
````

**with:**

````python
page count leaves the last side's right half blank.

The cover's box (PR 3a; printed_bulletin.cover_kind) is centered under the
church's name: the week's picture as cover_picture makes it (the same JPEG
the Word version places), or the reading and the date alone, or PR 1's
[Cover picture] box for a page from before PR 3b.
````

**In `backend/printed_pdf.py`, replace:**

````python
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, FrameBreak, KeepInFrame, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

````

**with:**

````python
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, FrameBreak, Image, KeepInFrame,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)

import bulletin_image
````

**In `backend/printed_pdf.py`, replace:**

````python
_GRAY = Color(0.45, 0.45, 0.45)
````

**with:**

````python
_GRAY = Color(0.45, 0.45, 0.45)
# The cover picture's resolution: print quality.
DPI = 300
````

**In `backend/printed_pdf.py`, replace:**

````python

def _contact(lines: list[pb.Line], width: float, height: float) -> Flowable:
````

**with:**

````python

class _CoverText(Flowable):
    """No picture this week (PR 3 planning answer 6): no box, the reading and
    the date centered where the picture would be."""

    def __init__(self, width: float, height: float, reference: str, date: str):
        super().__init__()
        self.width, self.height = width, height
        self.reference, self.date = reference, date

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        (big, small), middle = pb.COVER_TEXT_POINTS, self.height / 2
        for text, size, y in ((self.reference, big, middle + 3), (self.date, small, middle - small - 3)):
            if text:
                c.setFont("Times-Bold", size)
                c.drawCentredString(self.width / 2, y, to_pdf_text(text))


def _pixels(points: float) -> int:
    return round(points / 72 * DPI)


def cover_picture(ps: pb.PrintedService) -> bytes:
    """The cover's box as one JPEG (cover_kind "picture"): the week's picture
    filling COVER_BOX, its edges trimmed evenly, with the reading and the date
    in white on a dark see-through band (bulletin_image.cover; PR 3 planning
    answers 2-4). printed_docx places the same picture."""
    _title, _label, reference, date, *_contact = pb.cover(ps)
    lines = [(to_pdf_text(line.text), _pixels(size)) for line, size in zip((reference, date), pb.COVER_TEXT_POINTS)]
    return bulletin_image.cover(ps.cover_picture, lines, (_pixels(pb.COVER_BOX[0]), _pixels(pb.COVER_BOX[1])))


def _cover_box(ps: pb.PrintedService, label: str, reference: str, date: str) -> Flowable:
    """The cover's box for its kind (printed_bulletin.cover_kind), centered under the church's name."""
    width, height = pb.COVER_BOX
    kind = pb.cover_kind(ps)
    if kind == "picture":
        box: Flowable = Image(BytesIO(cover_picture(ps)), width=width, height=height)
    elif kind == "none":
        box = _CoverText(width, height, reference, date)
    else:
        box = _CoverPicture(width, height, label, reference, date)
    box.hAlign = "CENTER"
    return box


def _contact(lines: list[pb.Line], width: float, height: float) -> Flowable:
````

**In `backend/printed_pdf.py`, replace:**

````python
    picture = 300 + 30                                     # the picture's box and the space under it
    room = pb.PAGE_HEIGHT - 2 * MARGIN - heading.wrap(width, pb.PAGE_HEIGHT)[1] - STYLES["title"].spaceAfter - picture
    story: list[Flowable] = [heading, _CoverPicture(width - 60, 300, label.text, reference.text, date.text)]
````

**with:**

````python
    picture = pb.COVER_BOX[1] + 30                         # the picture's box and the space under it
    room = pb.PAGE_HEIGHT - 2 * MARGIN - heading.wrap(width, pb.PAGE_HEIGHT)[1] - STYLES["title"].spaceAfter - picture
    story: list[Flowable] = [heading, _cover_box(ps, label.text, reference.text, date.text)]
````

**In `backend/printed_docx.py`, replace:**

````python
one). An element's leader sits at a right tab stop. To print
````

**with:**

````python
one). The cover's box (PR 3a) is the PDF's: the same picture
(printed_pdf.cover_picture), the reading and the date alone, or PR 1's
[Cover picture] box. An element's leader sits at a right tab stop. To print
````

**In `backend/printed_docx.py`, replace:**

````python
import printed_bulletin as pb
````

**with:**

````python
import printed_bulletin as pb
import printed_pdf
````

**In `backend/printed_docx.py`, replace:**

````python
def render_docx(ps: pb.PrintedService) -> bytes:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(0)
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(7), Inches(8.5)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(0.5))
    section.footer_distance = Inches(0.25)
    _page_number_footer(section)

    title, label, reference, date, *contact = pb.cover(ps)
    _add_line(doc, title)
````

**with:**

````python
def _cover_box(doc, ps: pb.PrintedService, label: pb.Line, reference: pb.Line, date: pb.Line) -> None:
    """The cover's box for its kind (printed_bulletin.cover_kind), as the PDF's."""
    kind = pb.cover_kind(ps)
    width, height = pb.COVER_BOX
    if kind == "picture":
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(BytesIO(printed_pdf.cover_picture(ps)), width=Pt(width), height=Pt(height))
        return
    if kind == "none":                     # no box: the reading and the date centered where the picture would be
        lines = [(line.text, size) for line, size in zip((reference, date), pb.COVER_TEXT_POINTS) if line.text]
        paragraphs = []
        for text, size in lines:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(text)
            run.bold, run.font.size = True, Pt(size)
            paragraphs.append(p)
        room = Pt((height - sum(size * 1.2 for _text, size in lines)) / 2)
        paragraphs[0].paragraph_format.space_before = paragraphs[-1].paragraph_format.space_after = room
        return
````

**In `backend/printed_docx.py`, replace:**

````python
    cell.add_paragraph()
````

**with:**

````python
    cell.add_paragraph()


def render_docx(ps: pb.PrintedService) -> bytes:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(0)
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(7), Inches(8.5)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(0.5))
    section.footer_distance = Inches(0.25)
    _page_number_footer(section)

    title, label, reference, date, *contact = pb.cover(ps)
    _add_line(doc, title)
    _cover_box(doc, ps, label, reference, date)
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_bulletin_image.py backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py backend/tests/test_api_printed.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:** `78 passed in <t>s`; `1463 passed, 21 skipped in <t>s`. With a local Postgres: `21 passed, 1463 deselected, 1 warning in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/bulletin_image.py backend/service_bulletin.py backend/printed_bulletin.py backend/printed_pdf.py backend/printed_docx.py backend/tests/picture_helpers.py backend/tests/test_bulletin_image.py backend/tests/test_service_bulletin.py backend/tests/test_printed_bulletin.py backend/tests/test_printed_render.py
git commit -q -m "Printed bulletin PR 3a: the cover picture's module and the printed cover" -m "bulletin_image (Pillow): prepare checks an upload (a JPEG, a phone's
multi-picture JPEG included, or a PNG; at most 10 MB and 50 million pixels,
24 million for a PNG), prepares one at a time on one thread (a 429 after
10 s of waiting), turns it upright, converts it to sRGB, lays a transparent
part on white, scales it to at most 1600 px and stores it as a JPEG of at
most 600 KB with no camera data; cover makes the cover's box: the picture
filling it with a centered crop, in color, with the reading and the date in
white on a dark see-through band, shrunk together when long (planning
answers 2-4; the plan review's memory and size limits). service_bulletin gains
cover_image_id and cover_given (False when a page from before PR 3b did not
say). printed_bulletin.cover_kind: the picture, the reading and the date
alone (planning answer 6), or PR 1's box for a page from before 3b; the PDF
and the Word version place the same picture, and the PDF's box is now
centered under the church's name." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1463 passed, 21 skipped`; frontend `704 passed` in 87 files.

### Task 3: The API: upload, show, save and print a cover picture (S API, "Data model"; F §1.2, §1.3, §1.8, §2.2, §2.5; clarifications 5-7, 10, 13, 18)

**Files:**
- Create: `backend/tests/test_api_bulletin_images.py`, `backend/repos/bulletin_images.py`, `backend/usecases/bulletin_images.py`, `backend/api/routes/bulletin_images.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`, `backend/tests/test_middleware.py`, `backend/tests/test_ratelimit.py`, `backend/tests/test_service_bulletin.py`, `backend/tests/test_api_services.py`, `backend/tests/test_api_printed.py`, `backend/service_bulletin.py`, `backend/repos/services.py`, `backend/usecases/archive.py`, `backend/usecases/documents.py`, `backend/api/schemas.py`, `backend/api/ratelimit.py`, `backend/api/middleware.py`, `backend/api/main.py`, `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/openapi.json` and `frontend/src/lib/api/schema.d.ts` (regenerated)

`test_api_services.py`'s `BLANK_BULLETIN` gains `"cover_image_id": None` (what a 3b page sends, and what every answer now holds); its 422 case for an unknown box moves from "cover" (now a box) to "picture". `test_route_guards.py` needs no change: both routes depend on `require_church`. The plan review's cases: the GET's headers and its 304, the removal across churches in batches, a church's 160, the 150 MB budget, the removal reading the saved services after it locks (on SQLite, a save slipped in between), and on Postgres the two locks timing each other out (clarifications 6, 7, 20).

- [ ] **Step 1: Write the failing tests**

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "printed_bulletin, printed_pdf, printed_docx, bulletin_settings, usecases.church_bulletin, service_bulletin; "
````

**with:**

````python
            "printed_bulletin, printed_pdf, printed_docx, bulletin_settings, usecases.church_bulletin, service_bulletin, "
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images; "
````

**In `backend/tests/test_middleware.py`, replace:**

````python
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
````

**with:**

````python
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware, UploadSizeMiddleware
````

**In `backend/tests/test_middleware.py`, replace:**

````python
def test_middleware_order_is_cors_then_request_id_then_unhandled_error_then_gzip():
    # Starlette makes the last middleware added the outermost; user_middleware
    # lists them outermost first (F §2.5; slice 3 added GZip innermost).
    app = create_app()
    assert [m.cls for m in app.user_middleware] == [
        CORSMiddleware, RequestIdMiddleware, UnhandledErrorMiddleware, GZipMiddleware,
````

**with:**

````python
def test_middleware_order_is_cors_then_request_id_then_unhandled_error_then_upload_size_then_gzip():
    # Starlette makes the last middleware added the outermost; user_middleware
    # lists them outermost first (F §2.5; slice 3 added GZip innermost; printed
    # bulletin PR 3a UploadSize inside UnhandledError, so its 422 has CORS headers).
    app = create_app()
    assert [m.cls for m in app.user_middleware] == [
        CORSMiddleware, RequestIdMiddleware, UnhandledErrorMiddleware, UploadSizeMiddleware, GZipMiddleware,
````

**In `backend/tests/test_ratelimit.py`, replace:**

````python
        "email": (Rule("user", 10, 3_600),),
````

**with:**

````python
        "email": (Rule("user", 10, 3_600),),
        "picture": (Rule("user", 20, 3_600), Rule("church", 60, 86_400)),     # printed bulletin PR 3a
````

**Append to `backend/tests/test_service_bulletin.py`:**

````python


def test_the_cover_picture_is_the_first_box_to_check():
    """PR 3a: "cover" is one of the boxes still holding last week's choice, first in the step's order."""
    assert sb.CARRY_KEYS[0] == "cover"
    assert sb.read({"unchecked": ["prelude", "cover", "cover"]}).unchecked == ("cover", "prelude")
````

**Create `backend/tests/test_api_bulletin_images.py`:**

````python
"""/bulletin-images (printed bulletin spec, API; PR 3 planning answers 5, 8,
9; PR 3a): upload a cover picture, see it, church-scoped, the removal of
unused pictures after 60 days, a church's 160 pictures, the storage budget,
and a save and a removal waiting for each other (plan review C3, I4, I5).
Invented pictures only."""
import datetime
import logging
import uuid

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.exc import OperationalError

import bulletin_image
from api import ratelimit
from db import SessionLocal, session_scope
from db.models import BulletinImage, Service
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)
from tests.picture_helpers import BLUE, GREEN, RED, opened, picture, stripes

EMAIL = "pastor@example.com"
GONE = "That picture is no longer available."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def pastor(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(pastor, make_church):
    return make_church(name="Grace", owner_user_id=pastor)


def upload(client, church_id, data, *, email=EMAIL, content_type="image/jpeg"):
    return client.post("/bulletin-images", content=data,
                       headers={**church_headers(email, church_id), "Content-Type": content_type})


def stored_ids() -> set[str]:
    with session_scope() as s:
        return {str(i) for i in s.execute(select(BulletinImage.id)).scalars()}


def test_any_member_uploads_a_picture_and_sees_it(client, church, make_user, caplog):
    member = make_user(email="member@example.com")
    add_membership(member, church, "member")
    caplog.set_level(logging.INFO, logger="usecases.bulletin_images")
    r = upload(client, church, stripes((4000, 3000), [RED, GREEN, BLUE]), email="member@example.com")
    assert r.status_code == 201, r.text
    made = r.json()
    assert set(made) == {"id", "width", "height"} and (made["width"], made["height"]) == (1600, 1200)
    got = client.get(f"/bulletin-images/{made['id']}", headers=church_headers(EMAIL, church))
    assert got.status_code == 200, got.text
    assert got.headers["content-type"] == "image/jpeg"
    assert (got.headers["cache-control"], got.headers["x-content-type-options"], got.headers["etag"]) == (
        "private, no-cache", "nosniff", f'"{made["id"]}"')
    assert got.headers["vary"].startswith("Authorization, X-Church-Id")              # CORS adds Origin
    assert opened(got.content).size == (1600, 1200)
    again = client.get(f"/bulletin-images/{made['id']}",
                       headers={**church_headers(EMAIL, church), "If-None-Match": got.headers["etag"]})
    assert (again.status_code, again.content, again.headers["etag"]) == (304, b"", got.headers["etag"])
    with session_scope() as s:
        row = s.get(BulletinImage, uuid.UUID(made["id"]))
        assert (row.content_type, row.width, row.height, row.created_by) == ("image/jpeg", 1600, 1200, member)
        assert bytes(row.bytes) == got.content
    (record,) = [r for r in caplog.records if r.getMessage().startswith("bulletin_images.upload")]
    assert f"image={made['id']}" in record.getMessage() and "size=1600x1200 removed=0" in record.getMessage()
    png = upload(client, church, picture((300, 200), fmt="PNG"), content_type="image/png")
    assert (png.status_code, png.json()["width"]) == (201, 300)


@pytest.mark.parametrize("data, content_type, message", [
    (picture(fmt="GIF", mode="P", color=1), "image/gif", bulletin_image.NOT_A_PICTURE_MESSAGE),
    (b"not a picture", "image/jpeg", bulletin_image.NOT_A_PICTURE_MESSAGE),
    (b"\xff" * (10 * 1024 * 1024 + 1), "image/jpeg", bulletin_image.TOO_LARGE_MESSAGE),
])
def test_only_a_jpeg_or_png_of_at_most_10_mb_is_taken(client, church, data, content_type, message):
    r = upload(client, church, data, content_type=content_type)
    assert r.status_code == 422, r.text
    assert (r.json()["error"]["code"], r.json()["error"]["fields"]) == ("invalid_request", {"image": message})
    assert stored_ids() == set()


def test_a_body_without_its_size_is_refused_before_it_is_read(client, church):
    """UploadSizeMiddleware: a chunked body (no Content-Length) could be any size."""
    def chunks():
        yield picture()

    r = client.post("/bulletin-images", content=chunks(), headers={**church_headers(EMAIL, church),
                                                                   "Content-Type": "image/jpeg"})
    assert r.status_code == 422, r.text
    assert r.json()["error"]["fields"] == {"image": "Send the picture with its size (Content-Length)."}
    empty = upload(client, church, b"")                     # an iCloud photo not downloaded yet
    assert (empty.status_code, empty.json()["error"]["fields"]) == (422, {"image": bulletin_image.NOT_A_PICTURE_MESSAGE})
    assert stored_ids() == set()


def test_every_route_is_church_isolated(client, isolation_world):
    w = isolation_world
    mine = upload(client, w.church_a, picture(), email=w.a).json()["id"]
    theirs = upload(client, w.church_b, picture(), email=w.b).json()["id"]
    assert_church_isolated(client, "POST", "/bulletin-images", world=w)
    assert_church_isolated(client, "GET", f"/bulletin-images/{mine}", world=w,
                           resource_path_b=f"/bulletin-images/{theirs}")
    r = client.get(f"/bulletin-images/{uuid.uuid4()}", headers=church_headers(w.a, w.church_a))
    assert (r.status_code, r.json()["error"]["message"]) == (404, GONE)
    r = client.get(f"/bulletin-images/{theirs}", headers={**church_headers(w.a, w.church_a),
                                                           "If-None-Match": f'"{theirs}"'})
    assert (r.status_code, r.json()["error"]["message"]) == (404, GONE)
    r = client.get("/bulletin-images/not-an-id", headers=church_headers(w.a, w.church_a))
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")


def test_the_picture_bucket_takes_20_an_hour_a_member(client, church, pastor):
    ratelimit.consume("picture", user_id=pastor, church_id=church, cost=20)
    r = upload(client, church, picture())
    assert (r.status_code, r.json()["error"]["code"]) == (429, "rate_limited")
    assert int(r.headers["retry-after"]) > 0
    assert stored_ids() == set()


def add_picture(church_id, user_id, *, age_days=0, data=None) -> str:
    with session_scope() as s:
        row = BulletinImage(church_id=church_id, content_type="image/jpeg", bytes=data or picture(), width=400,
                            height=300, created_by=user_id, created_at=datetime.datetime.now(datetime.timezone.utc)
                            - datetime.timedelta(days=age_days))
        s.add(row)
        s.flush()
        return str(row.id)


def add_service(church_id, image_id, day="2026-01-04"):
    with session_scope() as s:
        s.add(Service(church_id=church_id, service_date_iso=day, occasion="", hymns=[], liturgy={}, scriptures=[],
                      bulletin={"cover_image_id": image_id}))


def test_an_upload_removes_any_church_s_pictures_unused_for_60_days(client, church, pastor, make_church, caplog,
                                                                    monkeypatch):
    """Planning answer 9: a picture no saved service of its church points at goes 60 days after its upload,
    on any church's next upload (a church that stops uploading loses its own too), at most REMOVE_BATCH at a
    time. Kept: one a saved service points at (any age), one uploaded within 60 days (a draft may point at
    it), one another church's service points at in that church."""
    from usecases import bulletin_images

    other = make_church(name="Other", owner_user_id=pastor)
    ids = {"old": add_picture(church, pastor, age_days=61), "used": add_picture(church, pastor, age_days=400),
           "recent": add_picture(church, pastor, age_days=59), "elsewhere": add_picture(other, pastor, age_days=70),
           "elsewhere_too": add_picture(other, pastor, age_days=65),
           "used_elsewhere": add_picture(other, pastor, age_days=90)}
    add_service(church, ids["used"])
    add_service(other, ids["used_elsewhere"])
    add_service(other, ids["old"], day="2026-01-11")          # another church's service: not a use of this one
    monkeypatch.setattr(bulletin_images, "REMOVE_BATCH", 2)
    caplog.set_level(logging.INFO, logger="usecases.bulletin_images")
    first = upload(client, church, picture())
    assert first.status_code == 201, first.text
    # The church with the oldest picture first ("used", 400 days): its "old"; then the other's oldest unused,
    # "elsewhere", and the batch of 2 is full.
    assert stored_ids() == {ids["used"], ids["recent"], ids["elsewhere_too"], ids["used_elsewhere"],
                            first.json()["id"]}
    assert "removed=2" in caplog.records[-1].getMessage()
    second = upload(client, church, picture())
    assert stored_ids() == {ids["used"], ids["recent"], ids["used_elsewhere"], first.json()["id"],
                            second.json()["id"]}
    assert "removed=1" in caplog.records[-1].getMessage()


def test_a_church_keeps_at_most_its_quota_of_pictures(client, church, pastor, monkeypatch):
    """Plan review C3: past MAX_PICTURES, the church's oldest pictures no saved service points at make room,
    whatever their age; when every one is in a saved service, the upload is refused and nothing changes."""
    from usecases import bulletin_images

    monkeypatch.setattr(bulletin_images, "MAX_PICTURES", 3)
    first, second, third = (add_picture(church, pastor, age_days=days) for days in (3, 2, 1))
    add_service(church, first)
    made = upload(client, church, picture())
    assert made.status_code == 201, made.text
    assert stored_ids() == {first, third, made.json()["id"]}                  # the oldest unused one went
    add_service(church, third, day="2026-01-11")
    add_service(church, made.json()["id"], day="2026-01-18")
    full = upload(client, church, picture())
    assert (full.status_code, full.json()["error"]["fields"]) == (422, {"image": bulletin_images.CHURCH_FULL_MESSAGE})
    assert stored_ids() == {first, third, made.json()["id"]}
    assert bulletin_images.CHURCH_FULL_MESSAGE.startswith("Your church keeps 160 pictures, all in saved services.")


def test_uploads_stop_when_every_church_s_pictures_reach_the_storage_budget(client, church, pastor, make_church,
                                                                            monkeypatch, caplog):
    """Plan review C3: any Google account can make a church, so a budget for all churches together keeps the
    database's free plan from filling; past it the upload is refused and the log says so."""
    from usecases import bulletin_images

    other = make_church(name="Other", owner_user_id=pastor)
    add_picture(other, pastor, data=b"\xff" * 5000)
    monkeypatch.setattr(bulletin_images, "STORAGE_BUDGET", 5000 + len(bulletin_image.prepare(picture()).content))
    assert upload(client, church, picture()).status_code == 201
    caplog.set_level(logging.WARNING, logger="usecases.bulletin_images")
    r = upload(client, church, picture())
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"image": bulletin_images.STORAGE_FULL_MESSAGE})
    assert len(stored_ids()) == 2
    assert caplog.records[-1].getMessage().startswith(f"bulletin_images.storage_full church={church} total=")


def test_the_removal_reads_the_saved_services_after_it_locks_its_candidates(client, church, pastor, monkeypatch):
    """Plan review I5: a save that points at an old picture while the removal runs keeps it. The removal
    locks its candidates first (FOR UPDATE on Postgres) and only then reads which pictures the saved services
    point at, so a save that got there first is seen (the Postgres test below checks the locks themselves)."""
    from repos import bulletin_images as images_repo

    old = add_picture(church, pastor, age_days=61)
    add_service(church, None)
    original = images_repo.ids_created_before

    def a_save_in_between(church_id, cutoff=None, *, session, lock=False):
        found = original(church_id, cutoff, session=session, lock=lock)
        session.execute(update(Service).where(Service.church_id == church_id).values(bulletin={"cover_image_id": old}))
        return found

    monkeypatch.setattr(images_repo, "ids_created_before", a_save_in_between)
    assert upload(client, church, picture()).status_code == 201
    assert old in stored_ids()


@pytest.mark.postgres
def test_a_save_and_the_removal_wait_for_each_other(pg_db):
    """Plan review I5, on Postgres: the removal's FOR UPDATE on a picture and a save's FOR SHARE on it
    exclude each other, whichever comes first (the other waits; here it gives up after 200 ms)."""
    from repos import bulletin_images as images_repo
    from repos.churches import create_church
    from repos.users import ensure_user

    user = ensure_user("pastor@example.com", "Pastor").id
    church_id = create_church(name="Grace", timezone="America/New_York", owner_user_id=user)
    image = add_picture(church_id, user, age_days=61)
    for first, second in (("remove", "save"), ("save", "remove")):
        holder, waiter = SessionLocal(), SessionLocal()
        try:
            take = {"remove": lambda s: images_repo.ids_created_before(church_id, None, session=s, lock=True),
                    "save": lambda s: images_repo.has_image(church_id, image, session=s, lock=True)}
            assert take[first](holder)
            waiter.execute(text("SET LOCAL lock_timeout = '200ms'"))
            with pytest.raises(OperationalError, match="lock timeout"):
                take[second](waiter)
        finally:
            waiter.rollback()
            holder.rollback()
            waiter.close()
            holder.close()
````

**In `backend/tests/test_api_services.py`, replace:**

````python
    "reading_text": {"ot": "", "nt": ""}, "unchecked": [],
````

**with:**

````python
    "reading_text": {"ot": "", "nt": ""}, "unchecked": [], "cover_image_id": None,
````

**In `backend/tests/test_api_services.py`, replace:**

````python
    ({"bulletin": {**BULLETIN, "unchecked": ["cover"]}}, "bulletin.unchecked.0"),
````

**with:**

````python
    ({"bulletin": {**BULLETIN, "unchecked": ["picture"]}}, "bulletin.unchecked.0"),
````

**In `backend/tests/test_api_services.py`, replace:**

````python
        assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request"), query
````

**with:**

````python
        assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request"), query



def upload_picture(client, church_id, email=EMAIL) -> str:
    from tests.picture_helpers import picture
    r = client.post("/bulletin-images", content=picture(),
                    headers={**church_headers(email, church_id), "Content-Type": "image/jpeg"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_the_cover_picture_is_saved_kept_by_an_older_page_and_carried(client, church, pastor, make_church):
    """PR 3a: the bulletin's cover_image_id is saved and opened; a bulletin without it (a page from before
    PR 3b) keeps the saved picture on a PUT; null clears it; an id the church does not have saves as none;
    the picture carries forward with the music."""
    mine = upload_picture(client, church)
    theirs = upload_picture(client, make_church(name="Other", owner_user_id=pastor))
    made = create(client, church, {**SERVICE, "service_date_iso": "2026-09-27",
                                   "bulletin": {**BULLETIN, "cover_image_id": mine, "unchecked": ["cover"]}})
    assert (made["bulletin"]["cover_image_id"], made["bulletin"]["unchecked"]) == (mine, ["cover"])
    path = f"/services/{made['id']}"
    older = {key: value for key, value in BULLETIN.items() if key != "cover_image_id"}   # a page from before 3b
    r = call(client, "PUT", path, church, json={**SERVICE, "service_date_iso": "2026-09-27", "bulletin": older},
             **{"If-Match": made["saved_at"]})
    assert (r.status_code, r.json()["bulletin"]["cover_image_id"]) == (200, mine)
    carried = call(client, "GET", "/services/previous-bulletin?before=2026-10-04", church).json()
    assert carried["bulletin"]["cover_image_id"] == mine
    for sent, saved in ((None, None), (theirs, None), (str(uuid.uuid4()), None), (mine, mine)):
        r = call(client, "PUT", path, church, json={**SERVICE, "bulletin": {**BULLETIN, "cover_image_id": sent}},
                 **{"If-Match": r.json()["saved_at"]})
        assert (r.status_code, r.json()["bulletin"]["cover_image_id"]) == (200, saved), sent
        assert call(client, "GET", path, church).json()["bulletin"]["cover_image_id"] == saved
    assert create(client, church, {**SERVICE, "bulletin": older})["bulletin"]["cover_image_id"] is None
````

**Append to `backend/tests/test_api_printed.py`:**

````python



def test_the_cover_picture_prints_and_a_page_from_before_3b_keeps_pr_1_s_box(client, church, owner, make_church,
                                                                             calls):
    """PR 3a: the church's picture fills the cover's box (the reading and the date on its band); null (no
    picture this week) or a picture the church does not have prints the reading and the date alone; a
    bulletin that does not say (a page from before PR 3b) keeps PR 1's [Cover picture] box."""
    from tests.picture_helpers import picture

    def picture_id(church_id):
        r = client.post("/bulletin-images", content=picture((1600, 1200)),
                        headers={**church_headers(EMAIL, church_id), "Content-Type": "image/jpeg"})
        assert r.status_code == 201, r.text
        return r.json()["id"]

    mine, theirs = picture_id(church), picture_id(make_church(name="Other", owner_user_id=owner))
    blank = {"prelude": {"title": "", "composer": ""}, "postlude": {"title": "", "composer": ""},
             "people": {"worship_leader": None, "liturgist": None, "organist": None}, "leaders": {},
             "announcements": {key: "" for key in ("ushers", "deacon", "coffee_hour", "activities",
                                                   "prayer_concerns", "collection", "other")},
             "reading_text": {"ot": "", "nt": ""}, "unchecked": []}
    for cover, images, starts in ((mine, 1, "Example Church 1 THE SERVICE"),
                                  (None, 0, "Example Church Philippians 3:4b-14 October 4, 2026 1 THE SERVICE"),
                                  (theirs, 0, "Example Church Philippians 3:4b-14 October 4, 2026 1 THE SERVICE"),
                                  ("left out", 0, "Example Church [Cover picture] Philippians 3:4b-14")):
        bulletin = blank if cover == "left out" else {**blank, "cover_image_id": cover}
        r = post(client, church, {"format": "pdf", "service": {**SERVICE, "bulletin": bulletin}})
        assert r.status_code == 200, r.text
        first = PdfReader(BytesIO(r.content)).pages[0]
        assert len(first.images) == images, cover
        assert pdf_text(r.content).startswith(starts), cover
    r = post(client, church, {"format": "docx", "service": {**SERVICE, "bulletin": {**blank, "cover_image_id": mine}}})
    assert r.status_code == 200, r.text
    assert len(Document(BytesIO(r.content)).inline_shapes) == 1
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_bulletin_images.py backend/tests/test_api_services.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_service_bulletin.py backend/tests/test_middleware.py backend/tests/test_ratelimit.py 2>&1 | tail -3` then the same without `test_middleware.py`, `| tail -1`
**Expected:** `test_middleware.py` cannot load (`UploadSizeMiddleware` does not exist yet; the new test file imports `usecases.bulletin_images` and `repos.bulletin_images` inside the tests that need them, so it loads):
```
ERROR backend/tests/test_middleware.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```
then `20 failed, 68 passed, 1 skipped in <t>s`: the upload and preview tests (no route: 404 and 405), the removal, the quota, the budget and the lock-order tests (no route), the saved and printed picture (`cover_image_id` is an extra field, a 422), "cover" as a box, the bucket list, and the layering test (no `usecases.bulletin_images`).

- [ ] **Step 3: The repo, the usecase, the routes, the middleware, the archive and the download, the types**

**In `backend/service_bulletin.py`, replace:**

````python
  carries forward with the music.
````

**with:**

````python
  carries forward with the music and is one of the boxes to check ("cover",
  the first: the cover comes first on the Bulletin step).
````

**In `backend/service_bulletin.py`, replace:**

````python
# The boxes that carry forward to the next week (PR 2 planning answer 5), in the Bulletin step's order.
CARRY_KEYS = ("prelude", "postlude", *ANNOUNCEMENT_KEYS)
````

**with:**

````python
# The boxes that carry forward to the next week (PR 2 planning answer 5; the cover picture, PR 3 planning
# answer 7), in the Bulletin step's order.
CARRY_KEYS = ("cover", "prelude", "postlude", *ANNOUNCEMENT_KEYS)
````

**Create `backend/repos/bulletin_images.py`:**

````python
"""The cover pictures, church-scoped (printed bulletin spec, "Data model";
PR 3a; table bulletin_images, migration 0007_bulletin_images).

Every query of one church's pictures filters on church_id, so another
church's picture is simply absent (the usecase's 404, or no picture
printed); the two that look at every church's (churches_with_pictures_before
and total_bytes, for the removal and the storage budget) return no picture.
Each function runs in the caller's session (F §2.2 rule 3);
usecases.bulletin_images, usecases.archive and usecases.documents own the
transactions. The picture's bytes are read only by get_picture (a projection
elsewhere, so a list never loads them).

Locks (plan review I5): the removal takes its candidates `FOR UPDATE` before
it reads which pictures the saved services point at, and a save takes the
picture it points at `FOR SHARE` (has_image with lock=True), so a save never
points at a picture being removed: one waits for the other. SQLite ignores
both (one writer at a time).
"""
import datetime
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from db.ids import as_uuid
from db.models import BulletinImage


@dataclass(frozen=True)
class StoredPicture:
    content_type: str
    content: bytes


def insert_image(church_id, created_by, *, content_type: str, content: bytes, width: int, height: int,
                 session: Session) -> BulletinImage:
    """Add a picture; flushed, so it has its id and created_at."""
    row = BulletinImage(church_id=as_uuid(church_id), created_by=None if created_by is None else as_uuid(created_by),
                        content_type=content_type, bytes=content, width=width, height=height)
    session.add(row)
    session.flush()
    return row


def get_picture(church_id, image_id, *, session: Session) -> Optional[StoredPicture]:
    """The church's picture with this id (its type and bytes), or None."""
    row = session.execute(select(BulletinImage.content_type, BulletinImage.bytes).where(
        BulletinImage.id == as_uuid(image_id), BulletinImage.church_id == as_uuid(church_id))).first()
    return None if row is None else StoredPicture(row.content_type, bytes(row.bytes))


def has_image(church_id, image_id, *, session: Session, lock: bool = False) -> bool:
    """Whether the church has this picture; with lock, it is held (FOR SHARE) until the transaction ends."""
    query = select(BulletinImage.id).where(
        BulletinImage.id == as_uuid(image_id), BulletinImage.church_id == as_uuid(church_id))
    return session.execute(query.with_for_update(read=True) if lock else query).first() is not None


def ids_created_before(church_id, cutoff: Optional[datetime.datetime] = None, *, session: Session,
                       lock: bool = False) -> list[uuid.UUID]:
    """The church's pictures, oldest first, those uploaded before `cutoff` only when given
    (ix_bulletin_images_church_created); with lock, held FOR UPDATE until the transaction ends."""
    query = select(BulletinImage.id).where(BulletinImage.church_id == as_uuid(church_id))
    if cutoff is not None:
        query = query.where(BulletinImage.created_at < cutoff)
    query = query.order_by(BulletinImage.created_at, BulletinImage.id)
    return list(session.execute(query.with_for_update() if lock else query).scalars())


def churches_with_pictures_before(cutoff: datetime.datetime, *, session: Session) -> list[uuid.UUID]:
    """Every church with a picture uploaded before `cutoff`, the one with the oldest first."""
    oldest = func.min(BulletinImage.created_at)
    return list(session.execute(select(BulletinImage.church_id).where(BulletinImage.created_at < cutoff)
                                .group_by(BulletinImage.church_id).order_by(oldest)).scalars())


def count_images(church_id, *, session: Session) -> int:
    return int(session.execute(select(func.count()).select_from(BulletinImage).where(
        BulletinImage.church_id == as_uuid(church_id))).scalar_one())


def total_bytes(*, session: Session) -> int:
    """Every church's pictures together, in bytes (Postgres reads each size without the picture)."""
    return int(session.execute(select(func.coalesce(func.sum(func.length(BulletinImage.bytes)), 0))).scalar_one())


def delete_images(church_id, image_ids: Iterable[uuid.UUID], *, session: Session) -> int:
    """Remove these pictures of the church; how many went."""
    ids = [as_uuid(i) for i in image_ids]
    if not ids:
        return 0
    result = session.execute(delete(BulletinImage).where(
        BulletinImage.church_id == as_uuid(church_id), BulletinImage.id.in_(ids)))
    return int(result.rowcount or 0)
````

**In `backend/repos/services.py`, replace:**

````python

def previous_service(church_id, before_iso: str, *, session: Session) -> Optional[Service]:
````

**with:**

````python

def stored_bulletins(church_id, *, session: Session) -> list[object]:
    """Every stored bulletin of the church's services (NULL left out), as read from the JSON column: for the
    cover pictures still in use (usecases.bulletin_images; printed bulletin PR 3a)."""
    return list(session.execute(select(Service.bulletin).where(
        Service.church_id == as_uuid(church_id), Service.bulletin.is_not(None))).scalars())


def previous_service(church_id, before_iso: str, *, session: Session) -> Optional[Service]:
````

**Create `backend/usecases/bulletin_images.py`:**

````python
"""The cover pictures (printed bulletin spec, "Data model"; PR 3 planning
answers 5, 8, 9; PR 3a).

- upload(church_id, user_id, data): POST /bulletin-images. The upload is
  checked and made ready to store first (bulletin_image.prepare: a 422 naming
  "image" touches no table; a 429 when another picture is being prepared).
  Then the old unused pictures of every church are removed, at most
  REMOVE_BATCH (planning answer 9; remove_unused), in a transaction of its
  own. Then, in one transaction: when the church already keeps MAX_PICTURES,
  its oldest pictures no saved service points at make room (make_room;
  every one in use: a 422, CHURCH_FULL_MESSAGE); when every church's
  pictures together would pass STORAGE_BUDGET, a 422 (STORAGE_FULL_MESSAGE,
  and a warning in the log); else the new one is stored.
- picture(church_id, image_id, if_none_match): GET /bulletin-images/{id}:
  the church's picture with its ETag, without its bytes when the browser
  already has them (If-None-Match), or a 404 (another church's id included,
  F §1.2 rule 2).
- remove_unused(session, now): the removal. A picture younger than
  RETENTION is never removed, so a draft's picture not saved yet (a draft
  lives in one browser) has 60 days; one a saved service of its church
  points at is never removed, whatever its age. It runs on every upload, of
  any church, so nothing has to run on a schedule and a church that stops
  uploading still loses its unused pictures; each upload removes at most
  REMOVE_BATCH, so one call stays short. It reads the stored bulletins of
  every church that has a picture older than RETENTION (a few hundred small
  rows at this size).
- in_use(session, church_id): the ids the church's saved services point at.
Each removal locks its candidates before it reads in_use, and a save locks
the picture it points at (repos.bulletin_images, plan review I5).
Logs carry ids, counts and sizes, never a picture (F §2.5).
"""
from __future__ import annotations

import datetime
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Optional

import bulletin_image
from db import session_scope
from db.ids import as_uuid
from domain_errors import InvalidInput, NotFound
from repos import bulletin_images as images_repo
from repos import services as services_repo
from service_bulletin import read as read_bulletin

logger = logging.getLogger(__name__)

RETENTION = datetime.timedelta(days=60)
REMOVE_BATCH = 20                     # old unused pictures removed on one upload, at most (every church)
MAX_PICTURES = 160                    # one church's stored pictures, at most
STORAGE_BUDGET = 150_000_000          # every church's pictures together, at most (bytes; plan review C3)

GONE_MESSAGE = "That picture is no longer available."
CHURCH_FULL_MESSAGE = (f"Your church keeps {MAX_PICTURES} pictures, all in saved services. Remove the picture "
                       "from an older service, then try again.")
STORAGE_FULL_MESSAGE = "The app has no room for more pictures right now. Please tell the app's administrator."


@dataclass(frozen=True)
class UploadedImage:
    id: uuid.UUID
    width: int
    height: int


@dataclass(frozen=True)
class Picture:
    etag: str                         # the id, quoted: a picture's id never names other bytes
    content_type: str
    content: Optional[bytes]          # None: the browser's copy is current (a 304)


def in_use(session, church_id: uuid.UUID) -> set[str]:
    """The picture ids the church's saved services point at (a stored bulletin's cover_image_id)."""
    ids = (read_bulletin(raw).cover_image_id for raw in services_repo.stored_bulletins(church_id, session=session))
    return {image_id for image_id in ids if image_id}


def _unused(session, church_id: uuid.UUID, cutoff: Optional[datetime.datetime]) -> list[uuid.UUID]:
    """The church's pictures (uploaded before `cutoff`, when given) no saved service points at, oldest first:
    locked first, then checked against the saved services, so a save in between is seen."""
    candidates = images_repo.ids_created_before(church_id, cutoff, session=session, lock=True)
    if not candidates:
        return []
    used = in_use(session, church_id)
    return [i for i in candidates if str(i) not in used]


def remove_unused(session, now: datetime.datetime, *, limit: Optional[int] = None) -> int:
    """Remove up to `limit` (REMOVE_BATCH) pictures, of any church, uploaded more than RETENTION before `now`
    that no saved service of their church points at; the church with the oldest such picture first."""
    limit = REMOVE_BATCH if limit is None else limit
    cutoff = now - RETENTION
    removed = 0
    for church_id in images_repo.churches_with_pictures_before(cutoff, session=session):
        if removed >= limit:
            break
        gone = _unused(session, church_id, cutoff)[:limit - removed]
        removed += images_repo.delete_images(church_id, gone, session=session)
    return removed


def make_room(session, church_id: uuid.UUID) -> int:
    """Below MAX_PICTURES after this: the church's oldest unused pictures removed, whatever their age."""
    over = images_repo.count_images(church_id, session=session) - MAX_PICTURES + 1
    if over <= 0:
        return 0
    unused = _unused(session, church_id, None)
    if len(unused) < over:
        raise InvalidInput(CHURCH_FULL_MESSAGE, field="image")
    return images_repo.delete_images(church_id, unused[:over], session=session)


def upload(church_id: uuid.UUID, user_id: uuid.UUID, data: bytes) -> UploadedImage:
    started = time.monotonic()
    cid = as_uuid(church_id)
    prepared = bulletin_image.prepare(data)
    with session_scope() as s:
        removed = remove_unused(s, datetime.datetime.now(datetime.timezone.utc))
    with session_scope() as s:
        removed += make_room(s, cid)
        total = images_repo.total_bytes(session=s)
        if total + len(prepared.content) > STORAGE_BUDGET:
            logger.warning("bulletin_images.storage_full church=%s total=%d budget=%d", cid, total,
                           STORAGE_BUDGET)
            raise InvalidInput(STORAGE_FULL_MESSAGE, field="image")
        row = images_repo.insert_image(cid, user_id, content_type=bulletin_image.CONTENT_TYPE,
                                       content=prepared.content, width=prepared.width, height=prepared.height,
                                       session=s)
        result = UploadedImage(row.id, row.width, row.height)
    logger.info("bulletin_images.upload church=%s image=%s bytes_in=%d bytes=%d size=%dx%d removed=%d ms=%d", cid,
                result.id, len(data), len(prepared.content), result.width, result.height, removed,
                round((time.monotonic() - started) * 1000))
    return result


def _matches(if_none_match: Optional[str], etag: str) -> bool:
    tags = [tag.strip().removeprefix("W/") for tag in (if_none_match or "").split(",")]
    return etag in tags or "*" in tags


def picture(church_id: uuid.UUID, image_id: uuid.UUID, if_none_match: Optional[str] = None) -> Picture:
    etag = f'"{image_id}"'
    with session_scope() as s:
        if _matches(if_none_match, etag):
            found = images_repo.has_image(church_id, image_id, session=s)
            answer = Picture(etag, bulletin_image.CONTENT_TYPE, None) if found else None
        else:
            stored = images_repo.get_picture(church_id, image_id, session=s)
            answer = None if stored is None else Picture(etag, stored.content_type, stored.content)
    if answer is None:
        raise NotFound(GONE_MESSAGE)
    return answer
````

**In `backend/usecases/archive.py`, replace:**

````python

No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
````

**with:**

````python

Printed bulletin PR 3a adds the week's cover picture (cover_image_id): a
save stores it when it is one of the church's pictures and no picture
otherwise (an id of another church, or one no longer there: never a 404,
never a picture from elsewhere); a PUT whose bulletin does not say (a page
from before PR 3b) keeps the saved picture. The picture is held (FOR SHARE)
until the save commits, so the 60-day removal cannot take it meanwhile
(repos.bulletin_images, plan review I5).

No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
````

**In `backend/usecases/archive.py`, replace:**

````python
from liturgy_config import SECTION_ORDER, normalize_placement
````

**with:**

````python
from liturgy_config import SECTION_ORDER, normalize_placement
from repos import bulletin_images as images_repo
````

**In `backend/usecases/archive.py`, replace:**

````python

def create_service(church_id: uuid.UUID, user_id: uuid.UUID, data: ServiceInput) -> ServiceRecord:
````

**with:**

````python

def _with_known_cover(session, church_id: uuid.UUID, clean: ServiceInput) -> ServiceInput:
    """The input with a cover picture the church does not have read as no picture (PR 3a)."""
    week = clean.bulletin
    if week is None or not week.cover_image_id or images_repo.has_image(church_id, week.cover_image_id,
                                                                        session=session, lock=True):
        return clean
    return replace(clean, bulletin=replace(week, cover_image_id=None))


def create_service(church_id: uuid.UUID, user_id: uuid.UUID, data: ServiceInput) -> ServiceRecord:
````

**In `backend/usecases/archive.py`, replace:**

````python
    with session_scope() as s:
        hymns = resolve_hymn_refs(s, cid, clean.hymns)
````

**with:**

````python
    with session_scope() as s:
        clean = _with_known_cover(s, cid, clean)
        hymns = resolve_hymn_refs(s, cid, clean.hymns)
````

**In `backend/usecases/archive.py`, replace:**

````python
            clean = replace(clean, bulletin=_kept_bulletin(row, clean))
````

**with:**

````python
            clean = replace(clean, bulletin=_kept_bulletin(row, clean))
        elif clean.bulletin is not None and not clean.bulletin.cover_given:     # a page from before PR 3b
            saved = read_bulletin(row.bulletin)
            clean = replace(clean, bulletin=replace(clean.bulletin, cover_image_id=saved.cover_image_id,
                                                    cover_given=saved.cover_given))
        clean = _with_known_cover(s, cid, clean)
````

**In `backend/usecases/documents.py`, replace:**

````python
prints PR 1's placeholders. The log line never carries a bulletin's text.
````

**with:**

````python
prints PR 1's placeholders. The log line never carries a bulletin's text.
PR 3a adds the week's cover picture: the church's picture the bulletin
points at, read with the name (none when it is not the church's or no
longer there: the reading and the date print alone).
````

**In `backend/usecases/documents.py`, replace:**

````python
from domain_errors import Forbidden
````

**with:**

````python
from domain_errors import Forbidden
from repos import bulletin_images as images_repo
````

**In `backend/usecases/documents.py`, replace:**

````python
            raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
        hymns = archive.resolve_hymn_refs(s, church_id, clean.hymns)
    resolved = service_output.ResolvedService(
````

**with:**

````python
            raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
        hymns = archive.resolve_hymn_refs(s, church_id, clean.hymns)
        cover_id = clean.bulletin.cover_image_id if clean.bulletin is not None else None
        stored = images_repo.get_picture(church_id, cover_id, session=s) if cover_id else None
    resolved = service_output.ResolvedService(
````

**In `backend/usecases/documents.py`, replace:**

````python
        bulletin=clean.bulletin)                        # None (a page from before PR 2b-2): PR 1's placeholders
````

**with:**

````python
        bulletin=clean.bulletin,                        # None (a page from before PR 2b-2): PR 1's placeholders
        cover_picture=None if stored is None else stored.content)
````

**In `backend/api/schemas.py`, replace:**

````python
    unchecked: list[Literal[service_bulletin.CARRY_KEYS]] = Field(max_length=len(service_bulletin.CARRY_KEYS))
````

**with:**

````python
    unchecked: list[Literal[service_bulletin.CARRY_KEYS]] = Field(max_length=len(service_bulletin.CARRY_KEYS))
    # The week's cover picture (PR 3a; POST /bulletin-images): null, no picture this week. Left out (a page
    # from before PR 3b): a PUT keeps the saved picture and the printed bulletin keeps PR 1's box.
    cover_image_id: Optional[uuid.UUID] = None
````

**In `backend/api/schemas.py`, replace:**

````python
            bulletin=None if self.bulletin is None else service_bulletin.read(self.bulletin.model_dump()))
````

**with:**

````python
            bulletin=None if self.bulletin is None else service_bulletin.read(self.bulletin.model_dump(
                exclude=None if "cover_image_id" in self.bulletin.model_fields_set else {"cover_image_id"})))
````

**In `backend/api/schemas.py`, replace:**

````python
    service_date_iso: Optional[str]
    bulletin: ServiceBulletin
````

**with:**

````python
    service_date_iso: Optional[str]
    bulletin: ServiceBulletin


# --- printed bulletin PR 3a: the cover pictures (POST /bulletin-images) ---

class BulletinImageOut(BaseModel):
    """An uploaded cover picture as stored (a JPEG at most 1600 px on its long
    side): put its id in the bulletin's cover_image_id."""

    id: uuid.UUID
    width: int
    height: int
````

**In `backend/api/ratelimit.py`, replace:**

````python
# church_create. ai: slices 3 and 4, PR #7, PR #8. email: slice 5b.
````

**with:**

````python
# church_create. ai: slices 3 and 4, PR #7, PR #8. email: slice 5b. picture:
# printed bulletin PR 3a (POST /bulletin-images).
````

**In `backend/api/ratelimit.py`, replace:**

````python
    "email": (Rule("user", 10, 3_600),),
````

**with:**

````python
    "email": (Rule("user", 10, 3_600),),
    "picture": (Rule("user", 20, 3_600), Rule("church", 60, 86_400)),
````

**In `backend/api/middleware.py`, replace:**

````python
readable 500 with CORS headers and X-Request-Id instead of a network error.
````

**with:**

````python
readable 500 with CORS headers and X-Request-Id instead of a network error.

UploadSizeMiddleware (printed bulletin PR 3a) refuses a cover picture over
10 MB from its Content-Length, before the body is read into memory (the
route would read it all first), and one sent without a length.
````

**In `backend/api/middleware.py`, replace:**

````python
            await response(scope, receive, send)
````

**with:**

````python
            await response(scope, receive, send)


class UploadSizeMiddleware:
    """POST /bulletin-images: a 422 naming "image" when the body's
    Content-Length is over bulletin_image.MAX_UPLOAD_BYTES or missing (a
    chunked body), before any of it is read. Every other request passes."""

    PATH = "/bulletin-images"
    NO_LENGTH_MESSAGE = "Send the picture with its size (Content-Length)."

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != self.PATH:
            await self.app(scope, receive, send)
            return
        from api.errors import error_body           # deferred, as UnhandledErrorMiddleware
        from bulletin_image import MAX_UPLOAD_BYTES, TOO_LARGE_MESSAGE

        lengths = [value for name, value in scope.get("headers", []) if name == b"content-length"]
        message = None
        if len(lengths) != 1 or not lengths[0].isdigit():
            message = self.NO_LENGTH_MESSAGE
        elif int(lengths[0]) > MAX_UPLOAD_BYTES:
            message = TOO_LARGE_MESSAGE
        if message is None:
            await self.app(scope, receive, send)
            return
        response = JSONResponse(error_body("invalid_request", message, fields={"image": message}), status_code=422)
        await response(scope, receive, send)
````

**Create `backend/api/routes/bulletin_images.py`:**

````python
"""The cover pictures: /bulletin-images (printed bulletin spec, API; PR 3
planning answers 5, 8, 9; PR 3a).

Church-scoped; any member may upload and see one (planning answer 8: every
member can edit a service). Plain `def` routes that each make one usecase
call (F §2.2 rule 1), with no SQL and no try/except.
- POST /bulletin-images: the picture itself is the request body (a JPEG or
  a PNG of at most 10 MB, any Content-Type but JSON; no multipart, so no
  python-multipart: it is installed here only through Streamlit). 201
  {id, width, height}. 422 naming "image" for anything else
  (api.middleware.UploadSizeMiddleware refuses a body over 10 MB before it
  is read; with no Content-Type the body is taken too, with
  application/json it is a 400). The `picture` bucket (F §1.8): 20 an hour
  a member, 60 a day a church; a 429 also when another picture is being
  prepared (bulletin_image). A church keeps at most 160 pictures, and all
  churches' pictures together at most 150 MB (a 422 past either;
  usecases.bulletin_images). No Idempotency-Key: a retried upload stores a
  second copy, which the 60-day removal takes.
- GET /bulletin-images/{id}: the church's picture (image/jpeg). The browser
  keeps it only privately and asks again each time (`private, no-cache`,
  `Vary: Authorization, X-Church-Id`), with its ETag, the id: a 304 without
  the bytes when it has them (plan review I4). `nosniff`. 404 for an id
  the church does not have.
"""
import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, Header
from fastapi.responses import Response

from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.schemas import BulletinImageOut
from usecases import bulletin_images

router = APIRouter()

PICTURE_RESPONSE = {200: {"description": "The picture (a JPEG).",
                          "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}}},
                    304: {"description": "Not modified: the browser's copy (If-None-Match) is current."}}
# Kept by the browser only, for this sign-in and church, and checked again on each use (a 304 is cheap).
PICTURE_HEADERS = {"Cache-Control": "private, no-cache", "Vary": "Authorization, X-Church-Id",
                   "X-Content-Type-Options": "nosniff"}


@router.post("/bulletin-images", status_code=201, response_model=BulletinImageOut,
             responses=error_responses(401, 403, 422, 429, 503))
def upload_image(
    # An empty body is not refused by the framework, so the sign-in and the church are checked first and
    # bulletin_image says "Choose a JPEG or PNG picture." (an iCloud photo not downloaded yet is 0 bytes).
    image: Annotated[bytes, Body(media_type="application/octet-stream")] = b"",
    user: CurrentUser = Depends(get_current_user),
    church: ActiveChurch = Depends(require_church),
    _limit: None = Depends(ratelimit.rate_limit("picture")),
) -> BulletinImageOut:
    uploaded = bulletin_images.upload(church.id, user.id, image)
    return BulletinImageOut(id=uploaded.id, width=uploaded.width, height=uploaded.height)


@router.get("/bulletin-images/{image_id}", response_class=Response,
            responses={**PICTURE_RESPONSE, **error_responses(401, 403, 404, 422, 503)})
def get_image(image_id: uuid.UUID, church: ActiveChurch = Depends(require_church),
              if_none_match: Annotated[Optional[str], Header()] = None) -> Response:
    found = bulletin_images.picture(church.id, image_id, if_none_match)
    headers = {**PICTURE_HEADERS, "ETag": found.etag}
    if found.content is None:
        return Response(status_code=304, headers=headers)
    return Response(content=found.content, media_type=found.content_type, headers=headers)
````

**In `backend/api/main.py`, replace:**

````python
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
from api.routes import (bulletin_settings, churches, documents, health, hymnals, hymns, invites, lectionary,
                        liturgy, liturgy_review, me, reference, rubric, scripture, services)
````

**with:**

````python
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware, UploadSizeMiddleware
from api.routes import (bulletin_images, bulletin_settings, churches, documents, health, hymnals, hymns, invites,
                        lectionary, liturgy, liturgy_review, me, reference, rubric, scripture, services)
````

**In `backend/api/main.py`, replace:**

````python
    # → GZip (F §2.5), so CORS decorates the 500s that UnhandledError produces, and
    # GZip (slice 3; GET /hymns?limit=2000 is ~200 KB of JSON) is innermost.
    app.add_middleware(GZipMiddleware, minimum_size=1024)
````

**with:**

````python
    # → UploadSize → GZip (F §2.5), so CORS decorates the 500s that UnhandledError
    # produces and UploadSize's 422 (printed bulletin PR 3a), and GZip (slice 3;
    # GET /hymns?limit=2000 is ~200 KB of JSON) is innermost.
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(UploadSizeMiddleware)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(services.router)
````

**with:**

````python
    app.include_router(services.router)
    app.include_router(bulletin_images.router)
````

**In `frontend/src/lib/api/types.ts`, replace:**

````ts
export type PreviousBulletin = components["schemas"]["PreviousBulletinOut"];
````

**with:**

````ts
export type PreviousBulletin = components["schemas"]["PreviousBulletinOut"];
/** `POST /bulletin-images` (printed bulletin PR 3a): an uploaded cover picture as stored; its id goes in `cover_image_id`. */
export type BulletinImage = components["schemas"]["BulletinImageOut"];
````

- [ ] **Step 4: Regenerate the API files; see them pass, the suite, types and lint**

Run: `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api >/dev/null) && git diff --stat -- frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts | tail -1` then `.venv/bin/python -m pytest -q backend/tests/test_api_bulletin_images.py backend/tests/test_api_services.py backend/tests/test_api_printed.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_service_bulletin.py backend/tests/test_middleware.py backend/tests/test_ratelimit.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`, the frontend suite, types and lint
**Expected:** ` 2 files changed, 488 insertions(+), 2 deletions(-)` (the two routes, the GET's `If-None-Match` header and 304, `BulletinImageOut`, `ServiceBulletin.cover_image_id` optional and "cover" in `unchecked`; no `-Input`/`-Output` schema); `121 passed, 1 skipped in <t>s`; `1477 passed, 22 skipped in <t>s`; ` Test Files  87 passed (87)` and `      Tests  704 passed (704)` with no `×` or `FAIL` line (the pages are unchanged; `cover_image_id` is optional in the types); `typecheck 0`, `lint 0`. With a local Postgres: `22 passed, 1477 deselected, 1 warning in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/repos/bulletin_images.py backend/usecases/bulletin_images.py backend/api/routes/bulletin_images.py backend/service_bulletin.py backend/repos/services.py backend/usecases/archive.py backend/usecases/documents.py backend/api/schemas.py backend/api/ratelimit.py backend/api/middleware.py backend/api/main.py backend/tests/test_api_bulletin_images.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_middleware.py backend/tests/test_ratelimit.py backend/tests/test_service_bulletin.py backend/tests/test_api_services.py backend/tests/test_api_printed.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts frontend/src/lib/api/types.ts
git commit -q -m "Printed bulletin PR 3a: upload and show a cover picture, save and print it" -m "POST /bulletin-images takes the picture as the request body (no multipart,
so no new package), any member of the church, the picture bucket (20 an
hour a member, 60 a day a church); UploadSizeMiddleware refuses a body over
10 MB, or without its size, before it is read. Each upload first removes up
to 20 pictures of any church that no saved service of that church points
at, uploaded more than 60 days ago (planning answer 9); a church keeps at
most 160 pictures and all churches together 150 MB (the plan review: any
Google account can create a church). The removal and a save lock the
picture, so a save never points at one being removed. GET
/bulletin-images/{id} serves the church's picture, private and checked
again on each use (an ETag and a 304). ServiceBulletin.cover_image_id is optional: left
out (a page from before PR 3b) a PUT keeps the saved picture and the printed
bulletin keeps PR 1's box; null is no picture; an id the church does not
have saves and prints as none. The picture carries forward and is one of
the boxes to check (\"cover\"). OpenAPI and types regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1477 passed, 22 skipped`; frontend `704 passed` in 87 files.

### Task 4: Docs: the owner's checks for PR 3a and the spec's data model (planning answers 1, 5, 7, 9, 10; clarifications 16, 18)

**Files:**
- Modify: `docs/manual-verification.md`, `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`

- [ ] **Step 1: Append the PR 3 heading and items 28-31; amend the spec's "Data model", "The Bulletin step" and "Scope by PR"**

**Append to `docs/manual-verification.md`:**

````markdown

### Printed bulletin PR 3: the cover picture

PR 3 ships as two PRs, backend first, as PR 2b did: **PR 3a** (migration
`0007_bulletin_images`; the server takes, shows and prints a cover picture;
the builder itself does not change) and, once 3a is live and checked,
**PR 3b** (the picture on the Bulletin step). Before the PR 3a merge the
owner runs the steps of `backend/migrations/README.md` → "Before
0007_bulletin_images" (items 28 and 29); after each merge, the owner's
guided check (one step at a time on the phone) covers the items marked
"(owner, after PR 3a)" or "(owner, after PR 3b)", and the print test item
36. The results go into `docs/ops-runbook.md` → "Printed bulletin PR 3a
record" and "Printed bulletin PR 3b record". Use a picture with no one in
it for the checks (a building, flowers); record what the page and the files
show, never a picture, a name, an email address, a phone number, a street
address or a church id.

- [ ] (owner, before the PR 3a merge) **28.** A green `db-backup` run; the read-only counts (version `0006_services_bulletin`, saved services, those with bulletin fields, the database's size); the SQL preview read: one new table `bulletin_images`, its index, row-level security and no grant to Supabase's `anon` and `authenticated` roles, between `BEGIN;` and `COMMIT;`, under the 5 s lock timeout.
- [ ] (owner, after PR 3a) **29.** The after-deploy query shows `0007_bulletin_images`, `true`, `0` and `0` (`0006_services_bulletin` with two empty values: the deploy has not applied 0007 yet, run it again in a minute), and the counts are unchanged (or grew by the services saved since), the database about the same size.
- [ ] (owner, after PR 3a) **30.** The builder works as before: open a saved service from **Services**, tap **Save changes**, and download the printed bulletin from **5 Review & send**: the save works, and the PDF's cover still shows the "[Cover picture]" box (now centered under the church's name, as the Word version's already was) with the reading and the date in it.
- [ ] (agent, after PR 3a) **31.** `/openapi.json` in production lists `/bulletin-images` and `/bulletin-images/{image_id}`; signed out, `POST /bulletin-images` answers 401 for a 1-byte body and for a 9.5 MB one (Railway's proxy passes a phone-sized picture with its size), and 422 naming `image` for an 11 MB one (refused before it is read).
````

**In `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`, replace:**

````markdown
  The upload is checked (JPEG, PNG or HEIC from a phone; at most 10 MB in), decoded with Pillow
  (already installed with reportlab), turned upright, scaled to at most 1600 px on the long side
  and stored as JPEG (about 150-400 KB). The service's `bulletin.cover_image_id` points at it;
  "Keep last week's" carries the id forward. Images no service points at are removed when they are
  more than 60 days old.
````

**with:**

````markdown
  The upload is checked (JPEG, a phone's multi-picture JPEG included, or PNG; at most 10 MB in;
  PR 3 planning answer 5: no HEIC, an iPhone's Safari sends a JPEG), decoded with Pillow (already
  installed with reportlab), one at a time, turned upright, its colors converted to sRGB, scaled to
  at most 1600 px on the long side and stored as JPEG with no camera data, at most 0.6 MB (a lower
  quality, then a smaller size, until it fits; a phone photo is usually 0.2-0.5 MB). The picture is the request body of
  `POST /bulletin-images` (no multipart form, so no new package). The service's
  `bulletin.cover_image_id` points at it (a JSON key, no foreign key; an id the church does not
  have is saved and printed as no picture); it carries forward with the music, marked to check
  (planning answer 7). A bulletin that does not say (a page from before PR 3b) keeps the saved
  picture on a save and prints PR 1's box. Images no saved service points at are removed when they
  are more than 60 days old, on any church's next upload (planning answer 9). Since any Google
  account can create a church, a church keeps at most 160 pictures (its oldest unused ones make
  room) and all churches' pictures together at most 150 MB; past either an upload is refused with
  a message (PR 3 plan review, `docs/superpowers/plans/2026-10-03-printed-bulletin-3.md`).
````

**In `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`, replace:**

````markdown
and the service time. PR 3 adds the cover picture to the step: "Upload a picture", "Keep last
week's picture", and a preview.
````

**with:**

````markdown
and the service time. PR 3 adds the cover picture to the step: "Choose a picture", a preview
with the band the reading and the date print on, **Remove**, and last week's picture carried forward with "From last week. Check before printing."
and **Keep as is** (PR 3 planning answer 7).
````

**In `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md`, replace:**

````markdown
  reference and date over it). Then a guided phone check and a second short print test (the picture).
````

**with:**

````markdown
  reference and date over it). Then a guided phone check and a second short print test (the picture).
  As PR 2b, two PRs, backend first (PR 3 planning answer 1): 3a (the migration, the upload and
  preview routes, `cover_image_id`, the printing; a page from before 3b keeps working and prints
  PR 1's box) is merged and live before 3b (the picture on the Bulletin step).
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '^## ' docs/manual-verification.md | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md docs/superpowers/specs/2026-10-02-printed-bulletin-design.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected:** `89 passed in <t>s` (`test_slice1_docs.py` pins the last eight `##` headings, ending `## Printed bulletin`: the new heading is a `###`, so the pin holds); `282:## Printed bulletin`; `4`; `0`; ` 2 files changed, 41 insertions(+), 7 deletions(-)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md docs/superpowers/specs/2026-10-02-printed-bulletin-design.md
git commit -q -m "Docs: printed bulletin PR 3a manual checks and the spec's data model" -m "docs/manual-verification.md gains \"### Printed bulletin PR 3: the cover
picture\" under \"## Printed bulletin\": PR 3 ships backend first in two
PRs; the owner's steps around migration 0007, the check that the builder
works as before after PR 3a and the agent's check of the live routes (items
28-31; the after-deploy check sends a 9.5 MB and an 11 MB body). The
spec's \"Data model\" says JPEG or PNG only (planning answer 5), the raw
body, no camera data, at most 0.6 MB, the carry with its mark, the removal
on any church's next upload and the limits; \"The Bulletin step\" and
\"Scope by PR\" follow planning answers 7 and 1." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1477 passed, 22 skipped`; frontend `704 passed` in 87 files.

- [ ] **Step 4 (controller): Review the batch (T1-T4) and backup push**

One review of PR 3a: the revision is expand-only, turns on row-level security, revokes Supabase's roles and its `--sql` is exactly clarification 14's 27 lines; the README's queries are read-only and match the Postgres tests; `ServiceBulletin.cover_image_id` is optional and a bulletin without it keeps the saved picture on a `PUT` and prints PR 1's box; an id the church does not have is never served or printed; the upload is checked before any table is touched, a body over 10 MB is refused before it is read, one picture is prepared at a time, the stored picture has no EXIF and is at most 600 KB; the removal decides "unused" per church, takes only pictures older than 60 days, at most 20 an upload, and never one a saved service points at, and it and a save lock the picture; a church's 160 and the 150 MB budget refuse with their messages; the GET is `private, no-cache` with an ETag; no log line carries a picture; the PDF and the Word version place the same picture; the regenerated types change no page. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

### Task 5: Verification and the draft PR 3a (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N1>` PR 3a's number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
git merge-base --is-ancestor 9b90d21 origin/main; echo "PR 2b-2 record on main: $?"
ls backend/migrations/versions | grep -c '^0'
git ls-tree --name-only origin/main backend/migrations/versions/ | grep -c '/0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `PR 2b-2 record on main: 1` (it rides along: Step 3's list has `M docs/ops-runbook.md`; `0` if a records PR merged it meanwhile, and then that line is absent); `7`; `6`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 5)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner. **If `main` gained a migration** (the last count is not 6), stop: `0007` must be renumbered onto the new head (F §3.5 chain rule) before anything else, and the owner told.

- [ ] **Step 2 (agent): Both suites, Postgres, the frontend, types, lint, the build, the alembic cycle, a sample booklet**

```bash
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/builder/")
(cd backend && ../.venv/bin/python -c "
import datetime, bulletin_image as bi, bulletin_settings as bs, printed_bulletin as pb, printed_pdf, printed_docx, service_bulletin as sb
from io import BytesIO
from PIL import Image, ImageDraw
from service_output import ResolvedService, ResolvedHymn
img = Image.new('RGB', (2400, 1600), (70, 130, 190)); draw = ImageDraw.Draw(img); draw.ellipse((900, 300, 1500, 900), fill=(240, 200, 60)); draw.rectangle((0, 1200, 2400, 1600), fill=(40, 110, 50))
raw = BytesIO(); img.save(raw, 'JPEG'); picture = bi.prepare(raw.getvalue()).content
r = ResolvedService(service_date=datetime.date(2026, 10, 18), hymns={'opening': ResolvedHymn('God Is Here!', 409), 'response': None, 'closing': None}, liturgy={'call_to_worship': 'Leader: Lift up your hearts. People: We lift them up.'}, sermon_title='Who Said?')
s = bs.read({'bulletin': {'address_lines': ['100 Example Street', 'Springfield, ST 00000'], 'phone': '(555) 010-0100', 'service_time': '10:30 a.m.', 'worship_leader': 'Rev. Alex Example', 'liturgist': 'Sam Sample', 'organist': 'Jordan Doe'}})
week = sb.read({'cover_image_id': '0b4c2b0e-1111-4222-8333-444455556666', 'prelude': {'title': 'Morning Voluntary', 'composer': 'Pat Example'}, 'announcements': {'coffee_hour': 'The Example family'}})
ot, nt = pb.Reading('Isaiah 25:1-9', 'O Lord, you are my God. ' * 20), pb.Reading('Matthew 22:1-14', 'Once more Jesus spoke to them in parables. ' * 20)
for name, ps in (('printed3a-sample', pb.PrintedService('Example Church', r, ot, nt, 'World English Bible (WEB)', s, week, picture)), ('printed3a-nopicture', pb.PrintedService('Example Church', r, ot, nt, 'World English Bible (WEB)', s, sb.read({'cover_image_id': None})))):
    open(f'<scratch>/{name}.pdf', 'wb').write(printed_pdf.render_pdf(ps)); open(f'<scratch>/{name}.docx', 'wb').write(printed_docx.render_docx(ps))
print('samples written')
")
```

**Expected:** `1477 passed, 22 skipped in <t>s`; ` Test Files  87 passed (87)` and `      Tests  704 passed (704)` with no `×` or `FAIL` line; `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s`, the five builder routes and no `Error` (a font `Failed to fetch` only: say so and rely on CI); `samples written`. With a local, throwaway Postgres also `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `22 passed, 1477 deselected`, and CI's alembic cycle on an empty throwaway database (`DATABASE_URL=<that url>` in `backend/`: `alembic upgrade head`, `alembic check`, `alembic downgrade base`, `alembic upgrade head`, `alembic check`): `No new upgrade operations detected.` twice. Open both sample PDFs and look at them: in `printed3a-sample.pdf` side 1's left half is "Example Church", then the picture filling the box under it, centered, in color, with "Matthew 22:1-14" and "October 18, 2026" in white on the dark band, then the contact lines; in `printed3a-nopicture.pdf` no box and no frame: "Matthew 22:1-14" and "October 18, 2026" in bold, centered in its place. The `.docx` files: the same picture (one inline picture 372 x 300 pt) and the same two centered lines (read back with python-docx). Attach the samples to the owner's message in Step 4 if the channel allows files, else describe them.

- [ ] **Step 3 (agent): The API files match, the preview, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0006_services_bulletin:0007_bulletin_images --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//')
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/bulletin_image.py backend/service_bulletin.py backend/printed_bulletin.py backend/printed_pdf.py backend/printed_docx.py backend/usecases/bulletin_images.py backend/usecases/archive.py backend/usecases/documents.py backend/repos/bulletin_images.py backend/repos/services.py; echo "imports grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations/env.py backend/service_archive.py backend/service_output.py backend/bulletin_settings.py backend/api/routes/documents.py backend/api/routes/services.py .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt app.py streamlit_views streamlit_tests frontend/src/components frontend/src/app frontend/src/lib/draft frontend/src/lib/queries frontend/src/lib/documents.ts | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); the 27 preview lines of README step 3 exactly; `imports grep exit 1`; exactly these paths (without `M docs/ops-runbook.md` when Step 1 printed `0`):
```
M	backend/api/main.py
M	backend/api/middleware.py
M	backend/api/ratelimit.py
A	backend/api/routes/bulletin_images.py
M	backend/api/schemas.py
A	backend/bulletin_image.py
M	backend/db/models.py
M	backend/migrations/README.md
A	backend/migrations/versions/0007_bulletin_images.py
M	backend/printed_bulletin.py
M	backend/printed_docx.py
M	backend/printed_pdf.py
A	backend/repos/bulletin_images.py
M	backend/repos/services.py
M	backend/service_bulletin.py
A	backend/tests/picture_helpers.py
M	backend/tests/test_api_app.py
A	backend/tests/test_api_bulletin_images.py
M	backend/tests/test_api_printed.py
M	backend/tests/test_api_services.py
A	backend/tests/test_bulletin_image.py
M	backend/tests/test_middleware.py
M	backend/tests/test_migrations.py
M	backend/tests/test_no_streamlit_in_core.py
M	backend/tests/test_printed_bulletin.py
M	backend/tests/test_printed_render.py
M	backend/tests/test_ratelimit.py
M	backend/tests/test_schema_check.py
M	backend/tests/test_service_bulletin.py
M	backend/tests/test_services_postgres.py
M	backend/usecases/archive.py
A	backend/usecases/bulletin_images.py
M	backend/usecases/documents.py
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-03-printed-bulletin-3.md
M	docs/superpowers/specs/2026-10-02-printed-bulletin-design.md
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/types.ts
```
`0` (no page, component, draft, query or body code: the builder is unchanged); the subjects oldest first: `Runbook: printed bulletin PR 2b-2 record (owner's phone check)` (when it rides along), `Spec: printed bulletin PR 3 planning answers (owner, 2026-10-03)`, the plan commits (`WIP plan: printed bulletin PR 3 …`, `Plan: printed bulletin PR 3 (the cover picture)` and any later plan commit), then T1-T4's four subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR 3a**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> The first half of the cover picture (printed bulletin PR 3a, the server's part) is verified on this machine: backend 1477 passed, 22 skipped (1432 and 17 before; the five new skipped ones are database checks that CI runs on Postgres); frontend unchanged at 704 tests in 87 files; typecheck, lint and the production build are clean. It adds one database change, migration 0007 (one new table for the pictures, closed to Supabase's own web API), and teaches the server to take a picture, keep it (upright, at most 1600 pixels and 0.6 MB, without the phone's location data; with limits so that no one account can fill the database or the server's memory), and print it on the cover with the reading and the date on a dark band; with no picture, the reading and the date print alone. Nothing you see changes yet, except that the PDF's "[Cover picture]" box now sits centered under the church's name, as the Word version's does. The picture upload itself comes in the second PR (3b), which I will open only after this one is live and checked. Before it merges I will ask you for the backup, the counts and a look at the SQL, one at a time. May I open the pull request as a **draft** titled "Printed bulletin PR 3a: the server takes and prints the cover picture", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/printed3a-pr-body.md" <<'BODY'
Printed bulletin PR 3a: the server's half of the cover picture (PR 3 planning answers of 2026-10-03; PR 3 ships backend first in two PRs, as 2b). Spec: docs/superpowers/specs/2026-10-02-printed-bulletin-design.md. Plan: docs/superpowers/plans/2026-10-03-printed-bulletin-3.md (Tasks 1-6). One migration (0007_bulletin_images); no new package or variable. The builder does not change: today's pages send no cover_image_id and keep working.

- Migration 0007_bulletin_images (expand-only): the bulletin_images table, its index, row-level security on Postgres. Before the merge: a backup, read-only counts with the database's size and the SQL preview (backend/migrations/README.md, "Before 0007_bulletin_images").
- bulletin_image (Pillow, already installed with reportlab): an upload checked (JPEG, a phone's multi-picture JPEG included, or PNG, at most 10 MB and 50 MP, 24 MP for a PNG), prepared one at a time, turned upright, sRGB, at most 1600 px, stored as JPEG of at most 600 KB without EXIF; the cover's box with a centered crop and a dark see-through band with the reading and the date in white.
- The printed bulletin: the picture (the same one in the PDF and the Word version), no box with the reading and the date centered when there is none, PR 1's box (now centered) for a page from before PR 3b.
- API: POST /bulletin-images (the picture as the body; the picture bucket; a body over 10 MB refused before it is read; each upload removes up to 20 pictures of any church unused for 60 days; a church keeps at most 160 pictures, all churches 150 MB), GET /bulletin-images/{id} (private, no-cache, an ETag), ServiceBulletin.cover_image_id (optional: left out, a PUT keeps the saved picture; a save and the removal lock the picture). OpenAPI and types regenerated.
- docs/manual-verification.md: "### Printed bulletin PR 3: the cover picture", items 28-31; the spec's data model. docs/ops-runbook.md: the PR 2b-2 record (rides along).

Next: PR 3b (the picture on the Bulletin step), opened after this one is live and checked.

Tests: backend 1432 → 1477 passed, 17 → 22 skipped; frontend 704 in 87 files (unchanged)

After merge (Task 6): the owner's after-deploy check (one read-only query) and a short phone check that the builder works as before, then a "Printed bulletin PR 3a record" in docs/ops-runbook.md (it rides along in PR 3b).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Printed bulletin PR 3a: the server takes and prints the cover picture" \
  --body-file "<scratch>/printed3a-pr-body.md"
gh pr checks <N1> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1477 passed, 22 skipped`, backend-postgres `22 passed, 1477 deselected` (after its `alembic upgrade head`, `alembic check`, `downgrade base`, `upgrade head` steps, now through `0007`), frontend `704 passed` in 87 files. Then send: "PR #<N1> is green: backend 1477 passed, 22 skipped; the Postgres job ran the migration up, down and up again and passed its 19 tests; 704 frontend tests in 87 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you, after the backup, the counts and the SQL check." On the yes: `gh pr ready <N1> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_migrations.py` (the 0007 tests, the README pin, the baseline's CREATE TABLE), `test_schema_check.py`, `test_api_app.py`, `test_services_postgres.py`, CI's alembic cycle | T1 |
| `test_bulletin_image.py`, `test_printed_bulletin.py`, `test_printed_render.py`, `test_service_bulletin.py` (but its "first box" test: T3) | T2 |
| `test_api_bulletin_images.py`, `test_api_services.py`, `test_api_printed.py`, `test_middleware.py`, `test_ratelimit.py`, `test_no_streamlit_in_core.py`, `test_openapi_contract.py`, `test_route_guards.py`, typecheck | T3 |
| `test_slice1_docs.py`, `test_docs.py` | T4 |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, printed bulletin PR 3a final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1477 passed, 22 skipped`; frontend `704 passed` in 87 files.

### Task 6: PR 3a: before the merge (backup, counts, SQL), the merge, the after-deploy check, the owner's check, the record (OWNER + agent)

The owner's steps go **one at a time** (send one, wait for the report or "next"). The agent writes each result into `<scratch>/printed3a-t6-results.md` (not committed). Record numbers and what the screens and files showed, never a token, an email address, a phone number, a street address, a church id, a database URL or a picture. The queries are the ones in `backend/migrations/README.md` → "Before 0007_bulletin_images" (pinned by T1's tests); copy them from there.

**Files:** Modify (Step 7): `docs/ops-runbook.md`: insert `### Printed bulletin PR 3a record` right before `## Backups` (after the last `###` record above it; today "Printed bulletin PR 2b-2 record"). A `###` heading, because `test_ops_workflows.py` pins the `##` list. The record is committed on the branch and rides along in PR 3b.

- [ ] **Step 1 (agent → OWNER, then agent): The backup**

Check first (not replayed): `gh pr view <N1> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send:

> PR #<N1> (printed bulletin PR 3a, the server's half of the cover picture) is ready and green. Before it merges you asked for three checks, as for migration 0006; here is the first. May I start a fresh database backup now (the db-backup workflow on main, about a minute)? Nothing else happens yet.

On a clear yes (not replayed):

```bash
gh workflow run db-backup --ref main -R bbrown62450/church
RUN=$(gh run list -R bbrown62450/church --workflow backup.yml --branch main --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId'); echo "$RUN"
gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 15 >/dev/null; echo "backup exit $?"
gh run view "$RUN" -R bbrown62450/church --json url,conclusion --jq '"\(.conclusion) \(.url)"'
gh api "repos/bbrown62450/church/actions/runs/$RUN/artifacts" --jq '.artifacts[] | "\(.name) \(.size_in_bytes)"'
```

**Expected:** a run id (started a few seconds ago; if `gh run list` shows an older run, wait and list again); `backup exit 0`; `success <run URL>`; `db-backup <bytes>`. Record the URL and the size (the next records show how the backups grow with the pictures). A failure: stop and tell the owner; nothing merges without a green backup.

- [ ] **Step 2 (OWNER, then agent): The counts and the database's size (read-only)**

Send, with the query from README step 2 pasted in full inside a code block:

> Second check: one read-only query; it only counts. Open Supabase → your project → SQL Editor → New query, paste the query below, and press Run. You should see one row with four values. Please tell me what each column shows: version, services, with_bulletin, database_size.

**Expected:** `version` `0006_services_bulletin`; `services` the saved services in all churches; `with_bulletin` those saved with the Bulletin step's fields; `database_size` the whole database (for example "14 MB"; the free plan holds 500 MB). Record the four values. If `version` is not `0006_services_bulletin`, stop and tell the owner what it means before going on.

- [ ] **Step 3 (agent → OWNER): The SQL the migration will run**

(not replayed)
```bash
git fetch origin && git status -sb | head -1
(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0006_services_bulletin:0007_bulletin_images --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//')
```

**Expected:** the branch even with `origin/claude/slice-2-plan-4q33le` (the PR's code); the 27 lines of README step 3 exactly. Send them in a code block with:

> Third check: these are the lines of SQL the migration will run on the database when the PR merges, rendered from the PR's code without touching the database. In plain words: start one transaction; give up after 5 seconds if the churches or users tables are busy (the old version then keeps running and we retry); create one new, empty table to hold the cover pictures (each picture belongs to a church and goes with it; the member who uploaded it is remembered, or forgotten if their account goes); add an index to find a church's pictures by age; turn on row-level security for the table and take away any access Supabase's two web roles might have to it, so Supabase's own web API cannot read it (only the app can); note the new version; finish. No existing row is copied, changed or deleted. Does that look right to you?

Record the owner's answer.

- [ ] **Step 4 (agent → OWNER): Ask to merge, then merge**

Send: "The backup is green, the counts are recorded and you have read the SQL. May I merge PR #<N1> with a merge commit? Railway then runs the migration before the new server starts. The website does not change with this PR (only the PDF's empty picture box moves to the center), so you can keep using the builder while it deploys; I will tell you when it is live, then ask for one more read-only query and a short phone check." On a clear yes (not replayed):

```bash
gh pr merge <N1> --merge -R bbrown62450/church
gh pr view <N1> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N1> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both.

- [ ] **Step 5 (agent, then OWNER): The deploy and the after-deploy check (manual-verification items 29 and 31)**

About three minutes after the merge (not replayed):

```bash
curl -s https://church-production-74ca.up.railway.app/health/ready; echo
curl -s https://church-production-74ca.up.railway.app/openapi.json | grep -o '"/bulletin-images[^"]*"' | sort -u
curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: image/jpeg' --data-binary 'x' https://church-production-74ca.up.railway.app/bulletin-images
head -c 9500000 /dev/urandom | curl -s -o /dev/null -w '%{http_code}\n' -X POST -H 'Content-Type: image/jpeg' --data-binary @- https://church-production-74ca.up.railway.app/bulletin-images
head -c 11000000 /dev/urandom | curl -s -w '\n%{http_code}\n' -X POST -H 'Content-Type: image/jpeg' --data-binary @- https://church-production-74ca.up.railway.app/bulletin-images
```

**Expected:** `{"ok":true,"db":"ok"}` (in production this answers 503 `schema_behind` while the database is behind the release, so `ok` means `0007` is applied and the new release is live); `"/bulletin-images"` and `"/bulletin-images/{image_id}"`; `401` (the route exists and wants a sign-in; a body is sent so the size check passes first); `401` again for the 9.5 MB body (it went through Railway's proxy with its length, as a phone photo will); for the 11 MB body the 422 body naming `image` with "The picture is larger than 10 MB. Choose a smaller one." and then `422` (refused from its Content-Length before it is read). A `413` (or a 502) for either large body, or "Send the picture with its size (Content-Length)." for the 9.5 MB one, means Railway's proxy limits or re-chunks bodies: stop and tell the owner before PR 3b (uploads from phones would fail); record what was seen. If `/openapi.json` still lacks the routes, wait a minute and retry; after ten minutes, ask the owner to open Railway → the API service → Deployments and read the newest deployment's status (a failed pre-deploy on the 5 s lock timeout: the old server keeps serving and nothing is broken, since the website does not need the new server yet; redeploy on the owner's yes). Then send, with README step 4's query in a code block, and step 2's query again:

> The new server is live. One more read-only check: in the SQL Editor, run the first query below; it should show 0007_bulletin_images, true, 0 and 0 (the table exists, closed to Supabase's web API, with no pictures yet: nothing can upload one until the second PR). Then run the counting query from before again; the numbers should be the same as last time (or a little higher if a service was saved meanwhile), the database about the same size. Also, if you have Railway open: the newest deployment's logs should include a line "Running upgrade 0006_services_bulletin -> 0007_bulletin_images". What do you see?

Record the values. A version other than `0007_bulletin_images`, `row_security` not `true`, `open_grants` or `pictures` other than `0`, or fewer services than before: stop and look before anything else.

- [ ] **Step 6 (OWNER, then agent): Phone: the builder works as before (item 30)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. Open a saved service from **Services**, then on **5 Review & send** tap **Save changes**, then **Download printed bulletin**. Does the save work, and does the PDF's cover still show the "[Cover picture]" box with the reading and the date in it, now centered under the church's name? (Nothing else is meant to change yet.)

Record the answers. Anything else than "works as before": stop; it is a PR 3a problem to fix (or revert, README "Reverting PR 3b or PR 3a") before PR 3b.

- [ ] **Step 7 (agent): Write the PR 3a record (it rides along in PR 3b)**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it (today `### Printed bulletin PR 2b-2 record`). Insert, right before `## Backups` (one blank line on each side):

```markdown
### Printed bulletin PR 3a record

Printed bulletin PR 3a (the server's half of PR 3, the cover picture:
migration `0007_bulletin_images`, the upload and preview routes, the
picture printed in the PDF and the Word version; the builder unchanged)
merged as PR #<N1>, the first of the two PRs of printed bulletin PR 3
(backend first; PR 3 planning answers of 2026-10-03). Production moved
from `0006_services_bulletin` to `0007_bulletin_images` (one new table,
with row-level security). The steps follow `backend/migrations/README.md`
→ "Before 0007_bulletin_images", and the owner's check covered the
"(owner, before the PR 3a merge)" and "(owner, after PR 3a)" items of
`docs/manual-verification.md` → "Printed bulletin". No token, email
address, phone number, street address, church id, database URL or picture
is recorded here.

| Step | Result | Date |
|---|---|---|
| 1. Backup | `db-backup` run <run URL>: success, artifact `db-backup` (<bytes> bytes, encrypted) | <date> |
| 2. Counts before (SQL Editor, read-only) | version `0006_services_bulletin`; <n> saved services, <n> with bulletin fields; database <size> | <date> |
| 3. SQL preview | Rendered from the PR's code without a database: the 27 lines of the README (one `CREATE TABLE bulletin_images`, its index, row-level security, the guarded REVOKE, under the 5 s lock timeout); read by the owner: <answer> | <date> |
| Merge and deploy | PR #<N1> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`; `/openapi.json` lists `/bulletin-images` and `/bulletin-images/{image_id}`; signed out: 401 (1 byte), 401 (9.5 MB), 422 (11 MB). <Railway log line "Running upgrade 0006_services_bulletin -> 0007_bulletin_images" seen by the owner. / Not checked.> | <date> |
| 4. After the deploy (read-only) | `0007_bulletin_images`, row_security `true`, open_grants `0`, pictures `0`; counts again: <unchanged / …>; database <size> | <date> |
| 5. The builder as before (phone: <phone and browser>) | <A saved service saved again; the printed bulletin's cover shows the [Cover picture] box, centered. / …> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: PR 3b (the picture on the Bulletin step), then the print test of a cover with a picture | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye: the second grep below catches an email address and a "(555)"-style phone, not a street address, a phone number written another way or a name, so check that none is in it. Then (not replayed):

```bash
sed -n '/^### Printed bulletin PR 3a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Printed bulletin PR 3a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|\([0-9]{3}\)'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: printed bulletin PR 3a record (backup, counts, SQL preview, merge, migration 0007)" -m "Records printed bulletin PR 3a (PR #<N1>): the backup, the read-only
counts and the database's size, the SQL preview before the merge, the merge
and the deploy of 0007_bulletin_images, the after-deploy check and the
owner's check that the builder works as before. No token, email, phone
number, address, church id, database URL or picture is recorded. Rides
along in PR 3b." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit; the push (a backup push of the branch, no PR). Then tell the owner: "PR 3a is live and recorded. Next I build PR 3b, the picture on the Bulletin step, and come back to you before opening it." PR 3b's tasks start now, on the same branch (now even with `main` plus this record).

Expected counts after this task: backend `1477 passed, 22 skipped` on `main`; frontend `704 passed` in 87 files.

## PR 3b: the cover picture on the Bulletin step (T7-T12)

Started only after T6 (PR 3a is merged, live and checked, its record committed on the branch). T7-T10 are PR 3b's commits: the draft v4 and the client library, the step's group, the card, the docs. T11 verifies and opens the draft PR; T12 merges it on the owner's yes, checks the phone, runs the print test and writes the record (its own records PR).

### Task 7: The draft v4 and the cover picture on the client (F §4.4, §4.5, §4.6; clarifications 5, 10, 12)

**Files:**
- Create: `frontend/src/lib/queries/bulletin-images.test.ts`, `frontend/src/lib/queries/bulletin-images.ts`
- Modify: `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/draft/schema.test.ts`, `frontend/src/lib/draft/migrate.test.ts`, `frontend/src/lib/draft/store.test.ts`, `frontend/src/lib/draft/mapping.test.ts`, `frontend/src/lib/draft/bulletin.test.ts`, `frontend/src/lib/documents.test.ts`, `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/lib/draft/schema.ts`, `frontend/src/lib/draft/migrate.ts`, `frontend/src/lib/draft/bulletin.ts`, `frontend/src/lib/documents.ts`, `frontend/src/lib/queries/services.ts`, `frontend/src/lib/queries/keys.ts`, `frontend/src/lib/api/timeouts.ts`

The tests that pin the version change with it (3 → 4; a "future" version 4 → 5). `serviceBulletin()` gains `cover_image_id: null`, as the API answers since PR 3a, so the bodies the tests compare say "no picture". The step's group is T8's and the card's lines T9's; here the step and the card show nothing new, but a carried picture already counts among the boxes to check. `useUploadBulletinImage(onStored)` takes the caller's callback into the mutation's own options (plan review I1), and `checkPicture` refuses an empty file.

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
/** A service's bulletin fields (printed bulletin PR 2b) with nothing filled in, unless overridden. */
````

**with:**

````ts
/** A service's bulletin fields (printed bulletin PR 2b) with nothing filled in (no picture, as the API answers since PR 3a), unless overridden. */
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
    unchecked: [],
````

**with:**

````ts
    unchecked: [],
    cover_image_id: null,
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
    expect(DRAFT_VERSION).toBe(3);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 3,
````

**with:**

````ts
    expect(DRAFT_VERSION).toBe(4);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 4,
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
      bulletin: {
````

**with:**

````ts
      bulletin: {
        cover_image_id: null,
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
      { ...d, version: 4 },
      { ...d, bulletin: undefined }, // version 3 needs the bulletin (PR 2b)
````

**with:**

````ts
      { ...d, version: 5 },
      { ...d, bulletin: undefined }, // version 3 needs the bulletin (PR 2b)
      { ...d, bulletin: { ...d.bulletin, cover_image_id: undefined } }, // version 4 needs the picture's id or null (PR 3b)
      { ...d, bulletin: { ...d.bulletin, carried: ["picture"] } },
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts

import { DraftRestoreError, migrate, migrations, parseStoredDraft, type Migration } from "./migrate";
````

**with:**

````ts

import { setAnnouncement } from "./bulletin";
import { DraftRestoreError, migrate, migrations, parseStoredDraft, type Migration } from "./migrate";
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
    expect(Object.keys(migrations)).toEqual(["1", "2"]);
````

**with:**

````ts
    expect(Object.keys(migrations)).toEqual(["1", "2", "3"]);
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
    expect(parseStoredDraft(JSON.stringify({ ...v1, editing }), OWNER)).toMatchObject({
      version: 3,
````

**with:**

````ts
    expect(parseStoredDraft(JSON.stringify({ ...v1, editing }), OWNER)).toMatchObject({
      version: 4,
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
    expect(migrated).toEqual({ ...testDraft(), ...saved, version: 3, bulletin: freshBulletin() });
````

**with:**

````ts
    expect(migrated).toEqual({ ...testDraft(), ...saved, version: 4, bulletin: freshBulletin() });
    expect(reviewStatus(migrated)).toBe("saved");
  });

  it("migrates a version 3 draft: no cover picture, nothing else changed, and a saved draft with bulletin fields stays Saved (PR 3b)", () => {
    const filled = setAnnouncement(testDraft(), "coffee_hour", "The Example family");
    const { cover_image_id, ...bulletin } = { ...filled.bulletin, carried: ["coffee_hour" as const] };
    expect(cover_image_id).toBeNull();
    // 2b-2's payload had no cover_image_id; today's leaves out a null one, so the fingerprint is the same.
    const payload = draftToServicePayload({ ...filled, bulletin: { ...bulletin, cover_image_id: null } });
    expect(payload.bulletin).not.toHaveProperty("cover_image_id");
    const editing = { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-10-04" };
    const v3 = { ...filled, version: 3, bulletin, editing, saved_fingerprint: fingerprint(payload), last_step: "review" };
    const migrated = parseStoredDraft(JSON.stringify(v3), OWNER);
    expect(migrated).toEqual({ ...v3, version: 4, bulletin: { ...bulletin, cover_image_id: null } });
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
      ["a future version", JSON.stringify({ ...d, version: 4 })],
````

**with:**

````ts
      ["a future version", JSON.stringify({ ...d, version: 5 })],
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 4 }), JSON.stringify({ version: 1 })]) {
````

**with:**

````ts
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 5 }), JSON.stringify({ version: 1 })]) {
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    const raw = JSON.stringify({ ...testDraft(), version: 4 });
````

**with:**

````ts
    const raw = JSON.stringify({ ...testDraft(), version: 5 });
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    store.flush();
    expect(stored(data)).toMatchObject({ version: 3, readings: { occasion: "Mine" } });
````

**with:**

````ts
    store.flush();
    expect(stored(data)).toMatchObject({ version: 4, readings: { occasion: "Mine" } });
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    expect(stored(data)).toMatchObject({ version: 3, readings: { occasion: "Mine" } });
````

**with:**

````ts
    expect(stored(data)).toMatchObject({ version: 4, readings: { occasion: "Mine" } });
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````ts
      version: 3,
````

**with:**

````ts
      version: 4,
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````ts
    expect(draftToServicePayload(d).bulletin).toEqual(bulletin);
````

**with:**

````ts
    const { cover_image_id: noPicture, ...payload } = bulletin;
    expect(noPicture).toBeNull();
    expect(draftToServicePayload(d).bulletin).toEqual(payload); // no picture: left out of the payload (PR 3b)
````

**In `frontend/src/lib/draft/bulletin.test.ts`, replace:**

````ts
  followSaveMode,
````

**with:**

````ts
  emptyServiceBulletin,
  followSaveMode,
  isBlankBulletin,
````

**In `frontend/src/lib/draft/bulletin.test.ts`, replace:**

````ts
  setAnnouncement,
````

**with:**

````ts
  setAnnouncement,
  setCover,
````

**In `frontend/src/lib/draft/bulletin.test.ts`, replace:**

````ts
  shouldCarry,
````

**with:**

````ts
  shouldCarry,
  withoutNoPicture,
````

**In `frontend/src/lib/draft/bulletin.test.ts`, replace:**

````ts
    expect(shouldCarry(all)).toBe(false);
````

**with:**

````ts
    expect(shouldCarry(all)).toBe(true); // the cover picture still carries (PR 3b)
    expect(shouldCarry(setCover(all, null))).toBe(false);
````

**In `frontend/src/lib/draft/bulletin.test.ts`, replace:**

````ts
    expect(printedNotFilledIn(undefined, d)).toEqual(["postlude"]); // settings still loading
  });
});
````

**with:**

````ts
    expect(printedNotFilledIn(undefined, d)).toEqual(["postlude"]); // settings still loading
  });
});


describe("the cover picture (printed bulletin PR 3b; PR 3 planning answers 6, 7)", () => {
  const PICTURE = "0b4c2b0e-1111-4222-8333-444455556666";

  it("is chosen or removed on the step, which checks its box for good", () => {
    const d = setCover(testDraft(), PICTURE);
    expect(d.bulletin).toMatchObject({ cover_image_id: PICTURE, edited: ["cover"], carried: [] });
    expect(setCover(d, null).bulletin).toMatchObject({ cover_image_id: null, edited: ["cover"] });
    expect(bulletinPayload(d).cover_image_id).toBe(PICTURE);
  });

  it("carries last week's picture, marked to check first; Keep as is or a choice checks it; a touched box never carries", () => {
    const week = lastWeek({ bulletin: { ...lastWeek().bulletin, cover_image_id: PICTURE } });
    const c = applyCarry(testDraft(), week, "2026-10-04");
    expect(c.bulletin).toMatchObject({ cover_image_id: PICTURE, carried: ["cover", "prelude", "ushers", "coffee_hour", "prayer_concerns"] });
    expect(notChecked(c)[0]).toBe("cover picture");
    expect(bulletinPayload(c).unchecked[0]).toBe("cover");
    expect(keepCarried(c, "cover").bulletin).toMatchObject({ cover_image_id: PICTURE, edited: ["cover"] });
    const removed = setCover(c, null);
    expect(removed.bulletin.carried).not.toContain("cover");
    const later = applyCarry(setDate(removed, "2026-10-11", "user"), week, "2026-10-11");
    expect(later.bulletin.cover_image_id).toBeNull(); // removed: last week's never comes back into it
    expect(applyCarry(testDraft(), lastWeek(), "2026-10-04").bulletin.cover_image_id).toBeNull(); // none last week
  });

  it("is marked to check on Save as new service, and opens with its saved mark", () => {
    const saved = serviceBulletin({ cover_image_id: PICTURE, unchecked: ["cover"] });
    const opened: DraftV1 = {
      ...testDraft(),
      editing: { service_id: "s-last", saved_at: "2026-09-27T12:00:00+00:00", date_iso: "2026-10-04" },
      bulletin: bulletinFromService(saved, savedService()),
    };
    expect(opened.bulletin).toMatchObject({ cover_image_id: PICTURE, carried: ["cover"] });
    const kept = keepCarried(opened, "cover");
    const copy = followSaveMode(setDate(kept, "2026-10-11", "user"));
    expect(copy.bulletin).toMatchObject({ cover_image_id: PICTURE, carried: ["cover"] });
    expect(bulletinFromService(serviceBulletin(), savedService()).cover_image_id).toBeNull();
  });

  it("is left out of the payload when there is none, so a draft saved before PR 3b stays Saved; a POST leaves no picture out", () => {
    expect(bulletinPayload(testDraft())).not.toHaveProperty("cover_image_id");
    expect(isBlankBulletin({ ...emptyServiceBulletin(), cover_image_id: null })).toBe(true);
    expect(isBlankBulletin({ ...emptyServiceBulletin(), cover_image_id: PICTURE })).toBe(false);
    expect(withoutNoPicture({ ...emptyServiceBulletin(), cover_image_id: null })).toEqual(emptyServiceBulletin());
    expect(withoutNoPicture({ ...emptyServiceBulletin(), cover_image_id: PICTURE })).toHaveProperty("cover_image_id", PICTURE);
    expect("bulletin" in draftToServicePayload(testDraft())).toBe(false);
  });
});
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````ts
import { setAnnouncement, setPerson } from "@/lib/draft/bulletin";
````

**with:**

````ts
import { setAnnouncement, setCover, setPerson } from "@/lib/draft/bulletin";
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````ts
    );
  });
});
````

**with:**

````ts
    );
  });
});


describe("the cover picture in the body (printed bulletin PR 3b)", () => {
  const PICTURE = "0b4c2b0e-1111-4222-8333-444455556666";

  it("always says which picture, or none, and the 409 check compares it", () => {
    expect(documentRequest(testDraft(), "bulletin").service.bulletin?.cover_image_id).toBeNull();
    const d = setCover(testDraft(), PICTURE);
    expect(printedRequest(d, "pdf").service.bulletin?.cover_image_id).toBe(PICTURE);
    const theirs = savedService({ bulletin: serviceBulletin({ cover_image_id: PICTURE }) });
    expect(savedCopyFingerprint({ ...theirs, bulletin: serviceBulletin({ cover_image_id: "another" }) })).not.toBe(
      savedCopyFingerprint(theirs),
    );
    const { cover_image_id: noPicture, ...older } = serviceBulletin(); // a copy read before PR 3a: no key
    expect(noPicture).toBeNull();
    expect(savedCopyFingerprint({ ...theirs, bulletin: older })).toBe(savedCopyFingerprint({ ...theirs, bulletin: serviceBulletin() }));
  });
});
````

**Create `frontend/src/lib/queries/bulletin-images.test.ts`:**

````ts
import { describe, expect, it } from "vitest";

import { checkPicture, MAX_PICTURE_BYTES, NOT_A_PICTURE, PICTURE_TOO_LARGE } from "./bulletin-images";
import { keys } from "./keys";

function file(type: string, size: number): File {
  return new File([new Uint8Array(size)], "picture", { type });
}

describe("the cover picture before it is uploaded (printed bulletin PR 3b)", () => {
  it("takes a JPEG or PNG of at most 10 MB and says the server's words otherwise", () => {
    expect(checkPicture(file("image/jpeg", 1000))).toBeNull();
    expect(checkPicture(file("image/jpeg", 0))).toBe(NOT_A_PICTURE); // an iCloud photo not downloaded yet
    expect(checkPicture(file("image/png", MAX_PICTURE_BYTES))).toBeNull();
    expect(checkPicture(file("image/heic", 1000))).toBe(NOT_A_PICTURE);
    expect(checkPicture(file("", 1000))).toBe(NOT_A_PICTURE);
    expect(checkPicture(file("image/jpeg", MAX_PICTURE_BYTES + 1))).toBe(PICTURE_TOO_LARGE);
  });

  it("keeps a picture's bytes under the church's key", () => {
    expect(keys.bulletinImage("c1", "p1")).toEqual(["church", "c1", "bulletin-image", "p1"]);
    expect(keys.bulletinImage("c1", "p1").slice(0, 2)).toEqual(keys.church("c1"));
  });
});
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(put.body).toHaveProperty("bulletin", emptyServiceBulletin()); // clearing every field clears the saved ones
````

**with:**

````tsx
    // Clearing every field clears the saved ones, the picture included (PR 3b: null says "no picture").
    expect(put.body).toHaveProperty("bulletin", { ...emptyServiceBulletin(), cover_image_id: null });
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(post.body).toMatchObject({ bulletin: { announcements: { coffee_hour: "The Sample family" } } });
````

**with:**

````tsx
    expect(post.body).toMatchObject({ bulletin: { announcements: { coffee_hour: "The Sample family" } } });
    expect((post.body as { bulletin: object }).bulletin).not.toHaveProperty("cover_image_id"); // no picture (PR 3b)
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/draft/bulletin.test.ts src/lib/draft/schema.test.ts src/lib/draft/migrate.test.ts src/lib/draft/store.test.ts src/lib/draft/mapping.test.ts src/lib/documents.test.ts src/lib/queries/bulletin-images.test.ts src/components/builder/review/review-send-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`bulletin-images.ts` does not exist yet, so its test file cannot load; the other new names import as undefined):
```
   × DraftStore changes (S store.ts) > never adopts a draft an older version of the app wrote, however new, and writes over it (slice 5a-3: an old tab) <t>ms
   × DraftStore changes (S store.ts) > puts its draft back over an old tab's with nothing to write, and a store loaded from the old tab's takes it (build review M3) <t>ms
   × documentRequest (slice 5a) > sends the service as the Word file prints it: slot hymns, enabled cards with text, picks, communion, custom elements <t>ms
   × the cover picture in the body (printed bulletin PR 3b) > always says which picture, or none, and the 409 check compares it <t>ms
   × carry forward (PR 2 planning answer 5) > carries again for a new date into every box not edited or kept, a box at a time (plan review fix M1) <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 6, 7) > is chosen or removed on the step, which checks its box for good <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 6, 7) > carries last week's picture, marked to check first; Keep as is or a choice checks it; a touched box never carries <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 6, 7) > is marked to check on Save as new service, and opens with its saved mark <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 6, 7) > is left out of the payload when there is none, so a draft saved before PR 3b stays Saved; a POST leaves no picture out <t>ms
   × draft migrate and parseStoredDraft (F §4.6 Versioning) > round-trips a stored draft <t>ms
   × draft migrate and parseStoredDraft (F §4.6 Versioning) > migrates a version 1 draft: editing gains the draft's date, and save_key_fingerprint starts null (slice 5a-3) <t>ms
   × draft migrate and parseStoredDraft (F §4.6 Versioning) > migrates a version 2 draft: an empty bulletin, nothing else changed, and a saved draft stays Saved (PR 2b) <t>ms
   × draft migrate and parseStoredDraft (F §4.6 Versioning) > migrates a version 3 draft: no cover picture, nothing else changed, and a saved draft with bulletin fields stays Saved (PR 3b) <t>ms
   × draft schema and freshDraft (F §4.6) > a fresh draft is dated next Sunday with every field empty and the F §4.6 defaults <t>ms
   × draft schema and freshDraft (F §4.6) > accepts an empty date and generous strings, and rejects impossible values <t>ms
   × serviceToDraft and markSaved (slice 5a-3; F §4.6 Loading an archived service) > opens a saved service as a new draft that is already Saved, on Review, for that date <t>ms
   × Review & send: saving (slice 5a-3) > leaves a blank bulletin out of a POST and always sends it in a PUT (2b-2 build review M1) <t>ms
 FAIL  |unit| src/lib/queries/bulletin-images.test.ts [ src/lib/queries/bulletin-images.test.ts ]
⎯⎯⎯⎯⎯⎯ Failed Tests 17 ⎯⎯⎯⎯⎯⎯⎯
      Tests  17 failed | 72 passed (89)
```

- [ ] **Step 3: The draft v4, the picture in the draft and the bodies, the upload and the preview**

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
 * The per-church unsaved draft, version 3 (F §4.6; S "Draft store").
````

**with:**

````ts
 * The per-church unsaved draft, version 4 (F §4.6; S "Draft store").
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
 * step id "bulletin". The names `DraftV1` and
````

**with:**

````ts
 * step id "bulletin". Version 4 (printed bulletin PR 3b) adds the week's
 * cover picture, `bulletin.cover_image_id`, and its box to check ("cover",
 * first in `CARRY_KEYS`). The names `DraftV1` and
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
export const DRAFT_VERSION = 3;
````

**with:**

````ts
export const DRAFT_VERSION = 4;
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
/** The boxes that carry forward from last week (PR 2 planning answer 5): the music and each announcement. */
export const CARRY_KEYS = ["prelude", "postlude", ...ANNOUNCEMENT_KEYS] as const;
````

**with:**

````ts
/**
 * The boxes that carry forward from last week (PR 2 planning answer 5; PR 3
 * planning answer 7): the cover picture, the music and each announcement.
 */
export const CARRY_KEYS = ["cover", "prelude", "postlude", ...ANNOUNCEMENT_KEYS] as const;
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
const bulletin = z.object({
````

**with:**

````ts
const bulletin = z.object({
  /** The week's cover picture (`POST /bulletin-images`), or null for none (printed bulletin PR 3b). */
  cover_image_id: text.nullable(),
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
  return {
    prelude: { title: "", composer: "" },
````

**with:**

````ts
  return {
    cover_image_id: null,
    prelude: { title: "", composer: "" },
````

**In `frontend/src/lib/draft/migrate.ts`, replace:**

````ts
 * in later like a new draft's, unless the draft is a saved service.
````

**with:**

````ts
 * in later like a new draft's, unless the draft is a saved service.
 *
 * 3 → 4 (printed bulletin PR 3b): the bulletin gains `cover_image_id`, null
 * (no picture); nothing else changes, so a saved draft stays "Saved" (the
 * payload leaves out a null picture).
````

**In `frontend/src/lib/draft/migrate.ts`, replace:**

````ts
  2: (draft) => ({ ...draft, bulletin: freshBulletin() }),
````

**with:**

````ts
  2: (draft) => ({ ...draft, bulletin: freshBulletin() }),
  3: (draft) => ({ ...draft, bulletin: isRecord(draft.bulletin) ? { ...draft.bulletin, cover_image_id: null } : draft.bulletin }),
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
 * text. Pure.
````

**with:**

````ts
 * text; and the cover picture (PR 3b: `setCover`; it carries forward, is
 * marked and kept like the music, and counts in "Save as new service"). Pure.
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
 *   service, plan review fix I3).
````

**with:**

````ts
 *   service, plan review fix I3). The cover picture's id only when there is
 *   one, so a draft saved before PR 3b keeps its fingerprint; the bodies
 *   sent say "no picture" (null) themselves (`serviceBody`).
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts

export function setAnnouncement(d: DraftV1, key: AnnouncementKey, value: string): DraftV1 {
````

**with:**

````ts

/** The week's cover picture (an uploaded picture's id), or null for none ("Remove"). */
export function setCover(d: DraftV1, id: string | null): DraftV1 {
  const b = d.bulletin;
  if (b.cover_image_id === id) return withBulletin(d, { ...b, ...touched(b, "cover") });
  return withBulletin(d, { ...b, cover_image_id: id, ...touched(b, "cover") });
}

export function setAnnouncement(d: DraftV1, key: AnnouncementKey, value: string): DraftV1 {
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
function filled(b: Pick<DraftBulletin, Piece | "announcements">, key: CarryKey): boolean {
````

**with:**

````ts
function filled(b: Pick<DraftBulletin, Piece | "announcements"> & { cover_image_id?: string | null }, key: CarryKey): boolean {
  if (key === "cover") return (b.cover_image_id ?? null) !== null;
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
 * Last week's music and announcements in every box not yet edited or kept,
````

**with:**

````ts
 * Last week's cover picture, music and announcements in every box not yet edited or kept,
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
    ...b,
    prelude: open("prelude") ? { ...p.prelude } : b.prelude,
````

**with:**

````ts
    ...b,
    cover_image_id: open("cover") ? (p.cover_image_id ?? null) : b.cover_image_id,
    prelude: open("prelude") ? { ...p.prelude } : b.prelude,
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
 * filled music and announcement box is marked "From last week. Check before
 * printing.". Back on the saved date, what was set aside returns: a name or
````

**with:**

````ts
 * filled box (the cover picture, the music and the announcements) is marked
 * "From last week. Check before printing.". Back on the saved date, what was set aside returns: a name or
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
/** `ServiceDraft.bulletin` with nothing filled in. */
````

**with:**

````ts
/** `ServiceDraft.bulletin` with nothing filled in (no picture: no `cover_image_id`, as `bulletinPayload` leaves it out). */
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
    unchecked: CARRY_KEYS.filter((key) => b.carried.includes(key)),
````

**with:**

````ts
    unchecked: CARRY_KEYS.filter((key) => b.carried.includes(key)),
    ...(b.cover_image_id === null ? {} : { cover_image_id: b.cover_image_id }),
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
/** Nothing filled in: what a service saved without a bulletin reads as. */
export function isBlankBulletin(p: ServiceBulletin): boolean {
  return JSON.stringify(p) === JSON.stringify(emptyServiceBulletin());
````

**with:**

````ts
/** The bulletin without a null `cover_image_id` ("no picture" said out loud): what a POST sends. */
export function withoutNoPicture(p: ServiceBulletin): ServiceBulletin {
  const { cover_image_id = null, ...rest } = p;
  return cover_image_id === null ? rest : p;
}

/** Nothing filled in (no picture either): what a service saved without a bulletin reads as. */
export function isBlankBulletin(p: ServiceBulletin): boolean {
  return JSON.stringify(withoutNoPicture(p)) === JSON.stringify(emptyServiceBulletin());
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
  return {
    prelude: { ...saved.prelude },
````

**with:**

````ts
  return {
    cover_image_id: saved.cover_image_id ?? null,
    prelude: { ...saved.prelude },
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
const CARRY_LABELS: Record<CarryKey, string> = {
````

**with:**

````ts
const CARRY_LABELS: Record<CarryKey, string> = {
  cover: "cover picture",
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
 * fields (printed bulletin PR 2b) always, each text cut to its limit.
````

**with:**

````ts
 * fields (printed bulletin PR 2b) always, each text cut to its limit, with
 * the cover picture's id or null (PR 3b: a body that says nothing would keep
 * the saved picture and print PR 1's box).
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
    unchecked: [...b.unchecked],
````

**with:**

````ts
    unchecked: [...b.unchecked],
    cover_image_id: b.cover_image_id ?? null,
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
    unchecked: CARRY_KEYS.filter((key) => (b.unchecked ?? []).includes(key)),
````

**with:**

````ts
    unchecked: CARRY_KEYS.filter((key) => (b.unchecked ?? []).includes(key)),
    cover_image_id: b.cover_image_id ?? null,
````

**In `frontend/src/lib/queries/services.ts`, replace:**

````ts
import { isBlankBulletin } from "@/lib/draft/bulletin";
````

**with:**

````ts
import { isBlankBulletin, withoutNoPicture } from "@/lib/draft/bulletin";
````

**In `frontend/src/lib/queries/services.ts`, replace:**

````ts
      // the saved ones.
      const { bulletin, ...withoutBulletin } = body;
      const postBody = bulletin == null || isBlankBulletin(bulletin) ? withoutBulletin : body;
````

**with:**

````ts
      // the saved ones. A POST leaves "no picture" (a null cover_image_id)
      // out for the same reason (a POST sent before PR 3b; the server stores
      // no picture either way); a PUT always says it, so Remove is saved.
      const { bulletin, ...withoutBulletin } = body;
      const postBody =
        bulletin == null || isBlankBulletin(bulletin) ? withoutBulletin : { ...body, bulletin: withoutNoPicture(bulletin) };
````

**In `frontend/src/lib/queries/keys.ts`, replace:**

````ts
  bulletinSettings: (id: string) => ["church", id, "bulletin-settings"] as const,
````

**with:**

````ts
  bulletinSettings: (id: string) => ["church", id, "bulletin-settings"] as const,
  /** A cover picture's bytes (printed bulletin PR 3b): an id never names other bytes, so it is never stale. */
  bulletinImage: (id: string, imageId: string) => ["church", id, "bulletin-image", imageId] as const,
````

**In `frontend/src/lib/api/timeouts.ts`, replace:**

````ts
  "POST /documents/printed": 30_000,
````

**with:**

````ts
  "POST /documents/printed": 30_000,
  // The cover picture (printed bulletin PR 3b): up to 10 MB up from a phone, then a second or two on the server.
  "POST /bulletin-images": 60_000,
````

**Create `frontend/src/lib/queries/bulletin-images.ts`:**

````ts
"use client";

/**
 * The cover pictures (printed bulletin PR 3b; `POST /bulletin-images`, `GET
 * /bulletin-images/{id}`, PR 3a).
 *
 * - `checkPicture(file)`: what the server would refuse, said before the
 *   upload starts (a JPEG or PNG, not empty, at most 10 MB), with the
 *   server's own words; null when it may go.
 * - `useUploadBulletinImage(onStored)`: the picture itself as the request
 *   body; `onStored` gets the answer (its id goes in the draft, `setCover`).
 *   It is the mutation's own callback, not `mutate`'s, so it runs even when
 *   the step is left while the picture uploads (TanStack Query drops
 *   `mutate`'s callbacks once the component unmounts; plan review I1).
 *   Errors are the caller's to show (on the step, next to the button).
 * - `useBulletinImage(id)`: the stored picture's bytes for the preview,
 *   fetched with the church's headers (an `<img>` cannot send them), kept
 *   for the session (an id never names other bytes).
 */
import { useQuery } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { BulletinImage } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

/** `bulletin_image.MAX_UPLOAD_BYTES`. */
export const MAX_PICTURE_BYTES = 10 * 1024 * 1024;
/** `bulletin_image.TOO_LARGE_MESSAGE` and `NOT_A_PICTURE_MESSAGE`: the server's words. */
export const PICTURE_TOO_LARGE = "The picture is larger than 10 MB. Choose a smaller one.";
export const NOT_A_PICTURE = "Choose a JPEG or PNG picture.";
const TYPES = new Set(["image/jpeg", "image/png"]);

export function checkPicture(file: File): string | null {
  if (!TYPES.has(file.type) || file.size === 0) return NOT_A_PICTURE; // 0 bytes: an iCloud photo not downloaded yet
  if (file.size > MAX_PICTURE_BYTES) return PICTURE_TOO_LARGE;
  return null;
}

export function useUploadBulletinImage(onStored: (stored: BulletinImage) => void) {
  const api = useApi();
  return useChurchMutation<BulletinImage, ApiError, File>({
    mutationFn: (file) =>
      api.church<BulletinImage>("/bulletin-images", {
        method: "POST",
        init: { body: file, headers: { "Content-Type": file.type } },
      }),
    onSuccess: (stored) => onStored(stored),
  });
}

export function useBulletinImage(imageId: string | null) {
  const api = useApi();
  const church = useChurch();
  return useQuery<Blob, ApiError>({
    queryKey: keys.bulletinImage(church.id, imageId ?? ""),
    queryFn: async ({ signal }) => (await api.churchBlob(`/bulletin-images/${imageId}`, { signal })).blob,
    enabled: imageId !== null,
    staleTime: Infinity,
  });
}
````

- [ ] **Step 4: See them pass, the suite, types and lint**

Run: the Step 2 command, then the frontend suite, then types and lint.
**Expected:** `      Tests  91 passed (91)` with no `×` line (89 and the two tests of the file that could not load); ` Test Files  88 passed (88)` and `      Tests  712 passed (712)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/queries/bulletin-images.ts frontend/src/lib/queries/bulletin-images.test.ts frontend/src/lib/draft/schema.ts frontend/src/lib/draft/migrate.ts frontend/src/lib/draft/bulletin.ts frontend/src/lib/documents.ts frontend/src/lib/queries/services.ts frontend/src/lib/queries/keys.ts frontend/src/lib/api/timeouts.ts frontend/src/test/fixtures/index.ts frontend/src/lib/draft/schema.test.ts frontend/src/lib/draft/migrate.test.ts frontend/src/lib/draft/store.test.ts frontend/src/lib/draft/mapping.test.ts frontend/src/lib/draft/bulletin.test.ts frontend/src/lib/documents.test.ts frontend/src/components/builder/review/review-send-step.test.tsx
git commit -q -m "Printed bulletin PR 3b: the draft v4 and the cover picture on the client" -m "The draft goes to version 4: bulletin.cover_image_id (null: none) and
\"cover\" first among the boxes that carry forward; a version 3 draft
migrates with no picture and stays Saved. setCover; last week's picture
carries into a new draft marked to check, Keep as is keeps it, Save as new
service marks it (PR 3 planning answer 7). The payload leaves a null picture
out (the fingerprint is unchanged), every body sent says it, a POST leaves
\"no picture\" out, and the 409 check compares it. lib/queries/
bulletin-images: checkPicture (the server's limits and words before an
upload, an empty file included), the upload as the request body (60 s)
with its own callback, which runs even after the step is left, the
preview's bytes." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1477 passed, 22 skipped`; frontend `712 passed` in 88 files.

### Task 8: The Cover picture on the Bulletin step (S "The Bulletin step"; planning answers 5-8; F §4.8; clarifications 8, 15)

**Files:**
- Modify: `frontend/src/test/fixtures/index.ts`, `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, `frontend/src/components/builder/bulletin/bulletin-step.tsx`

The step's first test lists the groups; "Cover picture" comes first. jsdom has no `URL.createObjectURL`: the new tests stub it as the Review tests do. A file the `accept` list would hide is sent with `fireEvent.change` (user-event applies `accept`). The plan review's cases (clarification 8): the step left while the picture uploads (the layout stays, the step's page is swapped out, then the upload answers), the preview under `<StrictMode>` (the URL shown is never one released, and only it is held), a small picture (jsdom loads no image: the test sets `naturalWidth` and fires `load`), and the band over the preview (the reading the files print and the date).

- [ ] **Step 1: Write the failing tests (and the fixture)**

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
import type {
  BulletinSettings,
````

**with:**

````ts
import type {
  BulletinImage,
  BulletinSettings,
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts

/** One row of `GET /services` (`ServiceSummary`): `savedService()`'s, unless overridden. */
````

**with:**

````ts

/** An uploaded cover picture (`POST /bulletin-images`, printed bulletin PR 3a), unless overridden. */
export function bulletinImage(overrides: Partial<BulletinImage> = {}): BulletinImage {
  return { id: "0b4c2b0e-1111-4222-8333-444455556666", width: 1600, height: 1200, ...overrides };
}

/** One row of `GET /services` (`ServiceSummary`): `savedService()`'s, unless overridden. */
````

**In `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, replace:**

````tsx
import { screen, waitFor, within } from "@testing-library/react";
````

**with:**

````tsx
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { StrictMode } from "react";
````

**In `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, replace:**

````tsx
import BulletinStepPage from "@/app/(signed-in)/(church)/builder/bulletin/page";
````

**with:**

````tsx
import BulletinStepPage from "@/app/(signed-in)/(church)/builder/bulletin/page";
import { formatServiceDate } from "@/lib/dates";
import { setCover } from "@/lib/draft/bulletin";
````

**In `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, replace:**

````tsx
import {
  church,
````

**with:**

````tsx
import {
  bulletinImage,
  church,
````

**In `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, replace:**

````tsx
import { FROM_LAST_WEEK } from "./bulletin-step";
````

**with:**

````tsx
import { FROM_LAST_WEEK, PICTURE_ALT, PICTURE_SMALL } from "./bulletin-step";
````

**In `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, replace:**

````tsx
    expect(within(step).getAllByRole("group").map((g) => g.querySelector("legend")?.textContent)).toEqual([
````

**with:**

````tsx
    expect(within(step).getAllByRole("group").map((g) => g.querySelector("legend")?.textContent)).toEqual([
      "Cover picture",
````

**In `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, replace:**

````tsx
  });
});
````

**with:**

````tsx
  });
});


describe("the cover picture (printed bulletin PR 3b; PR 3 planning answers 5-8)", () => {
  const PICTURE = bulletinImage().id;
  const jpeg = () => new File([new Uint8Array([0xff, 0xd8, 0xff])], "church.jpg", { type: "image/jpeg" });
  const pictureRoute = () => new Response(new Blob([new Uint8Array([0xff, 0xd8])], { type: "image/jpeg" }), { headers: { "Content-Type": "image/jpeg" } });

  beforeEach(() => {
    let n = 0;
    Object.assign(URL, { createObjectURL: vi.fn(() => `blob:test/${(n += 1)}`), revokeObjectURL: vi.fn() }); // jsdom has neither
  });

  it("uploads a chosen picture, shows it trimmed as the front page prints it, and Remove takes it off", async () => {
    const readings = editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46");
    const { user, api } = renderStep(readings, {
      "POST /bulletin-images": () => ({ status: 201, body: bulletinImage() }),
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
    });
    const group = await screen.findByRole("group", { name: "Cover picture" });
    expect(within(group).getByText(/^A JPEG or PNG picture for the front page/)).toBeInTheDocument();
    const choose = within(group).getByRole("button", { name: "Choose a picture" });
    expect(choose).toHaveClass("h-11"); // 44 px on a phone
    expect(within(group).queryByRole("button", { name: "Remove the cover picture" })).toBeNull();
    const file = jpeg();
    await user.upload(document.getElementById("bulletin-cover-file") as HTMLInputElement, file);
    const shown = await within(group).findByRole("img", { name: PICTURE_ALT });
    expect(shown).toHaveAttribute("src", "blob:test/1");
    expect(shown).toHaveClass("object-cover", "aspect-[372/300]");
    // The band as it prints over the picture: the New Testament reading the files print (here the epistle) and the date.
    expect(screen.getByTestId("cover-band")).toHaveTextContent(`Philippians 3:4b-14${formatServiceDate(readings.readings.date_iso)}`);
    const [post] = api.requests.filter((r) => r.method === "POST");
    expect(post).toMatchObject({ path: "/bulletin-images", body: file });
    expect(post.headers["content-type"]).toBe("image/jpeg");
    await waitFor(() => expect(stored().bulletin).toMatchObject({ cover_image_id: PICTURE, edited: ["cover"] }));
    expect(within(group).getByRole("button", { name: "Choose another picture" })).toBeInTheDocument();

    await user.click(within(group).getByRole("button", { name: "Remove the cover picture" }));
    await waitFor(() => expect(stored().bulletin.cover_image_id).toBeNull());
    expect(within(group).queryByRole("img")).toBeNull();
    expect(within(group).getByRole("button", { name: "Choose a picture" })).toHaveFocus();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:test/1");
  });

  it("says a file the server would refuse before uploading it, and the server's own refusal after", async () => {
    const { api } = renderStep(testDraft(), {
      "POST /bulletin-images": () =>
        fakeError(422, "invalid_request", "The picture has too many pixels. Choose a smaller one.", {
          fields: { image: "The picture has too many pixels. Choose a smaller one." },
        }),
    });
    const group = await screen.findByRole("group", { name: "Cover picture" });
    const input = document.getElementById("bulletin-cover-file") as HTMLInputElement;
    expect(input).toHaveAttribute("accept", "image/jpeg,image/png");
    fireEvent.change(input, { target: { files: [new File(["x"], "photo.heic", { type: "image/heic" })] } });
    expect(await within(group).findByRole("alert")).toHaveTextContent("Choose a JPEG or PNG picture.");
    expect(api.requests.filter((r) => r.method === "POST")).toEqual([]);
    fireEvent.change(input, { target: { files: [jpeg()] } });
    await waitFor(() =>
      expect(within(group).getByRole("alert")).toHaveTextContent("The picture has too many pixels. Choose a smaller one."),
    );
    expect(stored().bulletin.cover_image_id).toBeNull();
  });

  it("carries last week's picture with its note until it is kept, and says when a picture cannot be loaded", async () => {
    const lastWeek = previousBulletin({ service_id: "s-last", service_date_iso: "2026-09-27", bulletin: serviceBulletin({ cover_image_id: PICTURE }) });
    const { user } = renderStep(testDraft(), {
      "GET /services/previous-bulletin": lastWeek,
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
    });
    const group = await screen.findByRole("group", { name: "Cover picture" });
    expect(await within(group).findByRole("img", { name: PICTURE_ALT })).toBeInTheDocument();
    expect(within(group).getByText(FROM_LAST_WEEK)).toBeInTheDocument();
    expect(within(group).getByRole("button", { name: "Choose another picture" })).toHaveAccessibleDescription(FROM_LAST_WEEK);
    await user.click(within(group).getByRole("button", { name: "Keep as is: cover picture" }));
    expect(within(group).queryByText(FROM_LAST_WEEK)).toBeNull();
    expect(within(group).getByRole("button", { name: "Choose another picture" })).toHaveFocus();
    await waitFor(() => expect(stored().bulletin).toMatchObject({ cover_image_id: PICTURE, carried: [], edited: ["cover"] }));
  });

  it("says when the picture can no longer be loaded, and Remove still works", async () => {
    const gone = setCover(testDraft(), PICTURE); // chosen on an earlier visit
    const { user } = renderStep(gone, {
      [`GET /bulletin-images/${PICTURE}`]: () => fakeError(404, "not_found", "That picture is no longer available."),
    });
    const group = await screen.findByRole("group", { name: "Cover picture" });
    expect(await within(group).findByText("The picture could not be loaded.")).toBeInTheDocument();
    await user.click(within(group).getByRole("button", { name: "Remove the cover picture" }));
    await waitFor(() => expect(stored().bulletin.cover_image_id).toBeNull());
  });
  it("keeps the picture when the step is left while it uploads (plan review I1)", async () => {
    let answer: (value: unknown) => void = () => {};
    const view = renderStep(testDraft(), {
      "POST /bulletin-images": () => new Promise((resolve) => (answer = resolve)),
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
    });
    await screen.findByRole("group", { name: "Cover picture" });
    fireEvent.change(document.getElementById("bulletin-cover-file") as HTMLInputElement, { target: { files: [jpeg()] } });
    expect(await screen.findByRole("button", { name: "Uploading…" })).toBeInTheDocument();
    view.rerender(
      <BuilderLayout>
        <p>Another step</p>
      </BuilderLayout>,
    );
    expect(screen.queryByRole("group", { name: "Cover picture" })).toBeNull();
    await act(async () => answer({ status: 201, body: bulletinImage() }));
    await waitFor(() => expect(stored().bulletin).toMatchObject({ cover_image_id: PICTURE, edited: ["cover"] }));
  });

  it("never shows a preview whose URL was released, under StrictMode (plan review I2)", async () => {
    window.localStorage.setItem(KEY, JSON.stringify(setCover(testDraft(), PICTURE)));
    installFakeApi({
      "GET /church": churchProfile(),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /church/bulletin-settings": filledBulletinSettings(),
      "GET /services/previous-bulletin": previousBulletin(),
      [`GET /bulletin-images/${PICTURE}`]: pictureRoute,
    });
    renderWithProviders(
      <StrictMode>
        <BuilderLayout>
          <BulletinStepPage />
        </BuilderLayout>
      </StrictMode>,
      { me: me(), church: church(), path: "/builder/bulletin" },
    );
    const shown = await screen.findByRole("img", { name: PICTURE_ALT });
    const released = vi.mocked(URL.revokeObjectURL).mock.calls.map(([url]) => url);
    expect(released).not.toContain(shown.getAttribute("src"));
    expect(vi.mocked(URL.createObjectURL).mock.calls.length - released.length).toBe(1); // only the one shown is held
  });

  it("says a small picture may print blurry", async () => {
    renderStep(setCover(testDraft(), PICTURE), { [`GET /bulletin-images/${PICTURE}`]: pictureRoute });
    const shown = await screen.findByRole("img", { name: PICTURE_ALT });
    expect(screen.queryByText(PICTURE_SMALL)).toBeNull();
    Object.defineProperties(shown, { naturalWidth: { value: 640, configurable: true }, naturalHeight: { value: 480, configurable: true } });
    fireEvent.load(shown);
    expect(await screen.findByText(PICTURE_SMALL)).toBeInTheDocument();
    Object.defineProperties(shown, { naturalWidth: { value: 1600, configurable: true }, naturalHeight: { value: 1200, configurable: true } });
    fireEvent.load(shown);
    await waitFor(() => expect(screen.queryByText(PICTURE_SMALL)).toBeNull());
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/builder/bulletin 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (no Cover picture group yet):
```
   × the Bulletin step (printed bulletin PR 2b) > shows the music, who leads, the announcements and the reading text, all optional, and stores what is typed <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 5-8) > uploads a chosen picture, shows it trimmed as the front page prints it, and Remove takes it off <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 5-8) > says a file the server would refuse before uploading it, and the server's own refusal after <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 5-8) > carries last week's picture with its note until it is kept, and says when a picture cannot be loaded <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 5-8) > says when the picture can no longer be loaded, and Remove still works <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 5-8) > keeps the picture when the step is left while it uploads (plan review I1) <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 5-8) > never shows a preview whose URL was released, under StrictMode (plan review I2) <t>ms
   × the cover picture (printed bulletin PR 3b; PR 3 planning answers 5-8) > says a small picture may print blurry <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 8 ⎯⎯⎯⎯⎯⎯⎯
      Tests  8 failed | 7 passed (15)
```

- [ ] **Step 3: The group**

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````tsx
import { useState, type ReactNode } from "react";

````

**with:**

````tsx
import { useEffect, useRef, useState, type ChangeEvent, type ReactNode } from "react";

import { PendingButton } from "@/components/app/pending-button";
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````tsx
import type { BulletinSettings } from "@/lib/api/types";
import { ELEMENTS, ROLES } from "@/lib/bulletin-settings";
````

**with:**

````tsx
import { errorToastMessage } from "@/lib/api/errors";
import type { BulletinSettings } from "@/lib/api/types";
import { ELEMENTS, ROLES } from "@/lib/bulletin-settings";
import { formatServiceDate } from "@/lib/dates";
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````tsx
  setAnnouncement,
````

**with:**

````tsx
  setAnnouncement,
  setCover,
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````tsx
import type { AnnouncementKey, CarryKey, DraftV1, Person } from "@/lib/draft/schema";
````

**with:**

````tsx
import type { AnnouncementKey, CarryKey, DraftV1, Person } from "@/lib/draft/schema";
import { checkPicture, useBulletinImage, useUploadBulletinImage } from "@/lib/queries/bulletin-images";
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````tsx
export const NO_READINGS = "Choose the readings on step 1 to paste their text.";
````

**with:**

````tsx
export const NO_READINGS = "Choose the readings on step 1 to paste their text.";
export const COVER_HELP =
  "A JPEG or PNG picture for the front page, with the reading and the date printed over it. Without a picture, the reading and the date print alone.";
export const PICTURE_ALT = "This week's cover picture, as the front page trims it";
export const PICTURE_MISSING = "The picture could not be loaded.";
export const PICTURE_SMALL = "This picture is small and may print blurry.";
/** A stored picture shorter than this on its long side fills the 5.2 in cover box at under about 150 dpi. */
export const SMALL_PICTURE_SIDE = 800;
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````tsx
      {long ? <Textarea {...shared} rows={3} /> : <Input {...shared} className="h-11" />}
    </div>
  );
````

**with:**

````tsx
      {long ? <Textarea {...shared} rows={3} /> : <Input {...shared} className="h-11" />}
    </div>
  );
}

/**
 * The picture's bytes as a URL the `<img>` can show. Made and released in
 * one effect keyed by the bytes, so StrictMode's second run (or any
 * remount) makes a new URL instead of showing one already released (plan
 * review I2).
 */
function useObjectUrl(blob: Blob | undefined): string | null {
  const [url, setUrl] = useState<{ blob: Blob; url: string } | null>(null);
  useEffect(() => {
    if (blob === undefined) return;
    const made = URL.createObjectURL(blob);
    setUrl({ blob, url: made }); // eslint-disable-line react-hooks/set-state-in-effect -- the URL is an external resource made here and released below
    return () => URL.revokeObjectURL(made);
  }, [blob]);
  return url !== null && url.blob === blob ? url.url : null;
}

/**
 * The cover picture (printed bulletin PR 3b; PR 3 planning answers 2-8): the
 * week's picture, trimmed to the cover's shape as the front page prints it
 * (a centered crop), with a dark band across its bottom holding the reading
 * and the date as they print over it, and **Choose a picture** (or **Choose
 * another picture**) and **Remove**. A file the server would refuse (not a
 * JPEG or PNG, empty, over 10 MB) is said at once; the upload's own refusal
 * or failure is said under the buttons; a small picture is said to print
 * blurry. The picture uploaded goes in the draft even when the step was
 * left meanwhile (the upload's own callback, written at once), unless the
 * draft is another one by then. Last week's picture carries in like the
 * music, with "From last week. Check before printing." and **Keep as is**.
 */
function CoverPicture() {
  const { draft, update, flush } = useDraft();
  const picture = draft.bulletin.cover_image_id;
  const target = useRef<{ created: string; date: string } | null>(null);
  const upload = useUploadBulletinImage((stored) => {
    const chosenFor = target.current;
    update((d) =>
      chosenFor !== null && d.created_at === chosenFor.created && d.readings.date_iso === chosenFor.date
        ? setCover(d, stored.id)
        : d,
    );
    flush(); // the step may be gone by now (plan review I1)
  });
  const preview = useBulletinImage(picture);
  const url = useObjectUrl(preview.data);
  const [smallUrl, setSmallUrl] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const note = "bulletin-cover-carried";
  const { ot, nt } = effectivePicks(draft);
  const band = [nt ?? ot ?? "", formatServiceDate(draft.readings.date_iso)].filter((line) => line !== "");

  function choose(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // the same file can be chosen again
    if (!file) return;
    const refused = checkPicture(file);
    setProblem(refused);
    if (refused) return;
    target.current = { created: draft.created_at, date: draft.readings.date_iso };
    upload.mutate(file, { onError: (e) => setProblem(errorToastMessage(e)) });
  }

  return (
    <Group id="bulletin-cover" title="Cover picture" help={COVER_HELP}>
      {picture === null ? null : preview.isError ? (
        <p className="text-sm">{PICTURE_MISSING}</p>
      ) : url === null ? (
        <Skeleton role="status" aria-label="Loading the cover picture" className="aspect-[372/300] w-full max-w-sm" />
      ) : (
        <div className="grid gap-2">
          <div className="relative w-full max-w-sm overflow-hidden rounded-md border">
            {/* A blob URL of the church's own picture: next/image could not fetch it, and nothing here needs optimizing. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={url}
              alt={PICTURE_ALT}
              className="aspect-[372/300] w-full object-cover"
              onLoad={(e) => {
                const shown = e.currentTarget;
                setSmallUrl(Math.max(shown.naturalWidth, shown.naturalHeight) < SMALL_PICTURE_SIDE ? url : null);
              }}
            />
            {band.length > 0 ? (
              // The printed band, roughly: what it covers, and the words on it (plan review M8).
              <div
                aria-hidden="true"
                data-testid="cover-band"
                className="absolute inset-x-0 bottom-0 grid justify-items-center bg-black/55 px-2 py-1.5 text-center font-serif font-bold leading-tight text-white"
              >
                {band.map((line, i) => (
                  <span key={i} className={i === 0 ? "text-sm" : "text-xs"}>
                    {line}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
          {smallUrl === url ? <p className="text-sm">{PICTURE_SMALL}</p> : null}
        </div>
      )}
      <input
        ref={input}
        id="bulletin-cover-file"
        type="file"
        accept="image/jpeg,image/png"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={choose}
      />
      <div className="flex flex-wrap gap-3">
        <PendingButton
          id="bulletin-cover-choose"
          type="button"
          variant="outline"
          size="touch"
          pending={upload.isPending}
          pendingLabel="Uploading…"
          aria-describedby={draft.bulletin.carried.includes("cover") ? note : undefined}
          onClick={() => input.current?.click()}
        >
          {picture === null ? "Choose a picture" : "Choose another picture"}
        </PendingButton>
        {picture === null ? null : (
          <Button
            type="button"
            variant="outline"
            size="touch"
            aria-label="Remove the cover picture"
            disabled={upload.isPending}
            onClick={() => {
              setProblem(null);
              update((d) => setCover(d, null));
              document.getElementById("bulletin-cover-choose")?.focus();
            }}
          >
            Remove
          </Button>
        )}
      </div>
      <p role="status" className="sr-only">
        {upload.isPending ? "Uploading the picture…" : ""}
      </p>
      {problem ? (
        <p role="alert" className="text-sm">
          {problem}
        </p>
      ) : null}
      <CarriedNote id={note} carryKey="cover" name="cover picture" fieldId="bulletin-cover-choose" />
    </Group>
  );
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````tsx
 * printed bulletin). The prelude and postlude; who leads (the bulletin
 * settings' three people, changeable for this week, and each part's leader
 * behind "Change who leads a part"); the announcements; and per reading a
 * box for its pasted text. Last week's music and announcements carry in
````

**with:**

````tsx
 * printed bulletin). The cover picture (PR 3b); the prelude and postlude; who leads (the bulletin
 * settings' three people, changeable for this week, and each part's leader
 * behind "Change who leads a part"); the announcements; and per reading a
 * box for its pasted text. Last week's picture, music and announcements carry in
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````tsx
      ) : null}
      <Group id="bulletin-music" title="Music">
````

**with:**

````tsx
      ) : null}
      <CoverPicture />
      <Group id="bulletin-music" title="Music">
````

- [ ] **Step 4: See them pass (three runs), the suite, types and lint**

Run: the Step 2 command three times, then the frontend suite, then types and lint.
**Expected:** `      Tests  15 passed (15)` three times; ` Test Files  88 passed (88)` and `      Tests  719 passed (719)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/builder/bulletin/bulletin-step.tsx frontend/src/components/builder/bulletin/bulletin-step.test.tsx frontend/src/test/fixtures/index.ts
git commit -q -m "Printed bulletin PR 3b: the cover picture on the Bulletin step" -m "The Bulletin step starts with Cover picture: Choose a picture (the phone's
photos or camera; JPEG or PNG), the upload with Uploading..., a preview
trimmed as the front page prints it with the band the reading and the date
print on, Choose another picture and Remove. The picture goes in the draft
even when the step is left while it uploads; the preview's URL is made and
released in one effect (StrictMode-safe); a small picture is said to print
blurry. A file the server would refuse is said at once in its words, the
server's refusal under the buttons; a picture that can no longer be loaded
says so, and Remove still works. Last week's picture shows From last week. Check
before printing. with Keep as is (PR 3 planning answers 5-8)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1477 passed, 22 skipped`; frontend `719 passed` in 88 files.

### Task 9: The Printed bulletin card names the cover picture (PR 2 planning answer 3; planning answers 6, 7; clarifications 9, 15)

**Files:**
- Modify: `frontend/src/lib/draft/bulletin.test.ts`, `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/lib/draft/bulletin.ts`, `frontend/src/components/builder/review/printed-card.tsx`

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/lib/draft/bulletin.test.ts`, replace:**

````ts
  it("lists the blank standing fields, this week's people as changed, then the prelude, postlude and announcements", () => {
    const settings = filledBulletinSettings({ phone: "", organist: "" });
    expect(printedNotFilledIn(settings, testDraft())).toEqual(["phone", "organist", "prelude", "postlude", "announcements"]);
    let d = setPerson(setPerson(testDraft(), "organist", "Jordan Doe"), "liturgist", "");
    d = setMusic(setAnnouncement(d, "deacon", "Alex Example"), "prelude", "title", "Morning Voluntary");
    expect(printedNotFilledIn(settings, d)).toEqual(["phone", "liturgist", "postlude"]);
````

**with:**

````ts
  it("lists the blank standing fields, this week's people as changed, then the cover picture, prelude, postlude and announcements", () => {
    const settings = filledBulletinSettings({ phone: "", organist: "" });
    expect(printedNotFilledIn(settings, testDraft())).toEqual(["phone", "organist", "cover picture", "prelude", "postlude", "announcements"]);
    let d = setPerson(setPerson(testDraft(), "organist", "Jordan Doe"), "liturgist", "");
    d = setMusic(setAnnouncement(d, "deacon", "Alex Example"), "prelude", "title", "Morning Voluntary");
    expect(printedNotFilledIn(settings, d)).toEqual(["phone", "liturgist", "cover picture", "postlude"]);
    d = setCover(d, "0b4c2b0e-1111-4222-8333-444455556666");
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
        "Not filled in: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist, prelude, postlude, announcements.",
````

**with:**

````tsx
        "Not filled in: address, phone, email, website, Facebook name, service time, worship leader, liturgist, organist, cover picture, prelude, postlude, announcements.",
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(await within(card).findByText("Not filled in: organist, prelude, postlude, announcements.")).toBeInTheDocument();
````

**with:**

````tsx
    expect(await within(card).findByText("Not filled in: organist, cover picture, prelude, postlude, announcements.")).toBeInTheDocument();
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(within(card).getByText("Not filled in: postlude.")).toBeInTheDocument();
````

**with:**

````tsx
    expect(within(card).getByText("Not filled in: cover picture, postlude.")).toBeInTheDocument();
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Bulletin 3 to check");
````

**with:**

````tsx
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Bulletin 3 to check");
  });

  it("carries last week's cover picture in, lists it to check, and prints it (printed bulletin PR 3b)", async () => {
    const picture = "0b4c2b0e-1111-4222-8333-444455556666";
    const lastWeek = previousBulletin({ service_id: "s-last", service_date_iso: "2026-09-27", bulletin: serviceBulletin({ cover_image_id: picture }) });
    const { api, user } = renderReview(testDraft(), {
      "GET /church/bulletin-settings": filledBulletinSettings(),
      "GET /services/previous-bulletin": lastWeek,
      "POST /documents/printed": pdf(),
    });
    const card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(within(card).getByText(WEEKLY_NOTE)).toHaveTextContent(/^The cover picture, the music/);
    expect(await within(card).findByText("From last week, not checked yet: cover picture.")).toBeInTheDocument();
    expect(within(card).getByText("Not filled in: prelude, postlude, announcements.")).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Download printed bulletin" }));
    await waitFor(() => expect(printedRequests(api)).toHaveLength(1));
    expect(printedRequests(api)[0].body).toMatchObject({ service: { bulletin: { cover_image_id: picture, unchecked: ["cover"] } } });
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/builder/review/review-send-step.test.tsx src/components/builder/builder-shell.test.tsx src/components/builder/liturgy/liturgy-step.test.tsx src/lib/draft/bulletin.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected:**
```
   × printedNotFilledIn (PR 2 planning answer 3) > lists the blank standing fields, this week's people as changed, then the cover picture, prelude, postlude and announcements <t>ms
   × Review & send: the printed bulletin (printed bulletin PR 1) > lists the bulletin settings still blank and links to them (printed bulletin PR 2a) <t>ms
   × Review & send: the printed bulletin (printed bulletin PR 1) > carries last week's music and announcements in, lists what to check, and prints them (printed bulletin PR 2b) <t>ms
   × Review & send: the printed bulletin (printed bulletin PR 1) > carries last week's cover picture in, lists it to check, and prints it (printed bulletin PR 3b) <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 4 ⎯⎯⎯⎯⎯⎯⎯
      Tests  4 failed | 93 passed (97)
```

- [ ] **Step 3: The card's note and "cover picture" in its lines**

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
 * the prelude, the postlude and the announcements (all of them blank).
````

**with:**

````ts
 * the cover picture (PR 3b: none this week prints the reading and the date
 * alone), the prelude, the postlude and the announcements (all of them blank).
````

**In `frontend/src/lib/draft/bulletin.ts`, replace:**

````ts
  const weekly = [
````

**with:**

````ts
  const weekly = [
    ...(filled(p, "cover") ? [] : ["cover picture"]),
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
export const WEEKLY_NOTE = "The music, the announcements and this week's changes to who leads come from the Bulletin step.";
````

**with:**

````tsx
export const WEEKLY_NOTE =
  "The cover picture, the music, the announcements and this week's changes to who leads come from the Bulletin step.";
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
 * people), then the prelude, the postlude and the announcements (PR 2b). The
````

**with:**

````tsx
 * people), then the cover picture (PR 3b), the prelude, the postlude and the
 * announcements (PR 2b). The
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
 * Bulletin step and replace PR 1's last [placeholders] (the cover picture's
 * stays until PR 3); the card lists the blank ones and the boxes from last
````

**with:**

````tsx
 * Bulletin step and replace PR 1's last [placeholders]; PR 3b adds the cover
 * picture (none prints the reading and the date alone); the card lists the blank ones and the boxes from last
````

- [ ] **Step 4: See them pass (three runs), the suite, types and lint**

Run: the Step 2 command three times, then the frontend suite, then types and lint.
**Expected:** `      Tests  97 passed (97)` three times; ` Test Files  88 passed (88)` and `      Tests  720 passed (720)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/draft/bulletin.ts frontend/src/components/builder/review/printed-card.tsx frontend/src/lib/draft/bulletin.test.ts frontend/src/components/builder/review/review-send-step.test.tsx
git commit -q -m "Printed bulletin PR 3b: the Printed bulletin card names the cover picture" -m "The card says the cover picture comes from the Bulletin step, lists
\"cover picture\" under Not filled in when there is none (no picture prints
the reading and the date alone), and first under From last week, not
checked yet when last week's is still to check." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1477 passed, 22 skipped`; frontend `720 passed` in 88 files.

### Task 10: Docs: the manual check items for PR 3b (planning answers 5-7, 10; clarification 16)

**Files:**
- Modify: `docs/manual-verification.md`

- [ ] **Step 1: Append items 32-37**

**Append to `docs/manual-verification.md`:**

````markdown
- [ ] (owner, after PR 3b) **32.** On **4 Bulletin**, **Cover picture** comes first. Tap **Choose a picture**: the phone offers its photos (and the camera). Choose a photo taken on the phone: it uploads ("Uploading…"), and the preview shows it upright, trimmed to the cover's shape, with a dark band across its bottom holding the reading and the date as they print (an iPhone photo shows that Safari sent it as a JPEG, PR 3 planning answer 5). Choose another picture and, while it says "Uploading…", go to **5 Review & send** and back: the new picture is there. Download the printed bulletin from **5 Review & send**: the picture fills the cover's box under the church's name, in color, with the reading and the date in white on a dark see-through band across its bottom. The Word version shows the same picture.
- [ ] (owner, after PR 3b) **33.** Tap **Remove** and download again: the cover has no box, and the reading and the date sit centered where the picture was; the Printed bulletin card lists "cover picture" under "Not filled in".
- [ ] (owner, after PR 3b) **34.** Choose a picture, save the service, start a **New service** for the Sunday after and open **4 Bulletin**: last week's picture is there with "From last week. Check before printing."; **Keep as is** keeps it and the note goes. Open a saved service and change its date ("Save as new service"): its picture is marked the same way.
- [ ] **35.** A file that is not a JPEG or PNG (a PDF, a HEIC picture from a computer) or is over 10 MB says so under the buttons ("Choose a JPEG or PNG picture." or "The picture is larger than 10 MB. Choose a smaller one.") and uploads nothing; the picture already chosen stays.
- [ ] (owner, after PR 3b) **36.** Print test (PR 3 planning answer 10): print side 1 of a bulletin with a picture on the church's color printer, on legal paper: the picture is in color, sharp, inside the margins, and the reading and the date on the band are easy to read.
- [ ] (agent, after PR 3b) **37.** In a test church: another church's picture id answers 404; the picture's preview is fetched once in a visit, and after a reload the browser asks again and gets 304 (`Cache-Control: private, no-cache` with the ETag); a draft from before PR 3b opens with everything it had and no picture.
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '^## ' docs/manual-verification.md | tail -1` then `git diff -U0 docs/manual-verification.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected:** `89 passed in <t>s`; `282:## Printed bulletin`; `0`; ` 1 file changed, 6 insertions(+)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md
git commit -q -m "Docs: printed bulletin PR 3b manual checks" -m "docs/manual-verification.md gains items 32-37: the owner's phone check of
the cover picture (an iPhone photo, planning answer 5), Remove, carry
forward with Keep as is, a refused file, the print test of a cover with a
picture on the church's color printer (planning answer 10) and the agent's
checks." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1477 passed, 22 skipped`; frontend `720 passed` in 88 files.

- [ ] **Step 4 (controller): Review the batch (T7-T10) and backup push**

One review of PR 3b: the draft's 3 → 4 migration keeps everything and a "Saved" draft stays Saved, its bulletin filled in or not; the picture carries only like the music (never into a saved service, a box chosen, removed or kept, or while a save's outcome is unknown), runs only through `autoUpdate`, and Save as new service marks it; every body says the picture (a PUT saves a Remove), a POST leaves "no picture" out, and the 409 check compares it; the upload sends the file as it is with its type, says the server's refusal, and puts the picture in the draft from the mutation's own callback (and only in the same draft); the preview's object URL is made and released in one effect; the group's buttons are 44 px and labelled, the hidden file input is not a tab stop, and focus goes back to **Choose a picture** after **Remove**; the copy is clarification 15's. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

### Task 11: Verification and the draft PR 3b (owner's yes before the PR is opened and before it is marked ready)

`<N2>` is PR 3b's number, `<N1>` PR 3a's. As T5: every `gh` command uses `-R bbrown62450/church`; never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): PR 3a is live, and the branch is up to date with `origin/main`**

```bash
git status --short
git fetch origin
curl -s https://church-production-74ca.up.railway.app/openapi.json | grep -o '"/bulletin-images[^"]*"' | sort -u | wc -l
git ls-tree --name-only origin/main backend/migrations/versions/ | grep -c '/0'
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
git log --format=%s -1 origin/main -- docs/ops-runbook.md
```

**Expected:** nothing (or `?? .claude/`); `2` (the live API has PR 3a's routes: without them, stop, PR 3b must not merge); `7` (`0007` on `main`); `0`; `0`; the subject of the commit that last changed the runbook on `main` (not the 3a record, which rides along here). If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 11)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, Postgres, the frontend three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/builder/bulletin")
```

**Expected:** `1477 passed, 22 skipped in <t>s`; three times ` Test Files  88 passed (88)` and `      Tests  720 passed (720)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s`, a route line `○ /builder/bulletin`, and no `Error` (a font `Failed to fetch` only: say so and rely on CI). With a local, throwaway Postgres also `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `22 passed, 1477 deselected`.

- [ ] **Step 3 (agent): The gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts frontend/src/lib/api/types.ts .github frontend/package.json frontend/package-lock.json requirements-dev.txt app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status`; `raw html grep exit 1`; exactly these paths (and `M docs/superpowers/plans/2026-10-03-printed-bulletin-3.md` if a plan commit came after the 3a merge):
```
M	docs/manual-verification.md
M	docs/ops-runbook.md
M	frontend/src/components/builder/bulletin/bulletin-step.test.tsx
M	frontend/src/components/builder/bulletin/bulletin-step.tsx
M	frontend/src/components/builder/review/printed-card.tsx
M	frontend/src/components/builder/review/review-send-step.test.tsx
M	frontend/src/lib/api/timeouts.ts
M	frontend/src/lib/documents.test.ts
M	frontend/src/lib/documents.ts
M	frontend/src/lib/draft/bulletin.test.ts
M	frontend/src/lib/draft/bulletin.ts
M	frontend/src/lib/draft/mapping.test.ts
M	frontend/src/lib/draft/migrate.test.ts
M	frontend/src/lib/draft/migrate.ts
M	frontend/src/lib/draft/schema.test.ts
M	frontend/src/lib/draft/schema.ts
M	frontend/src/lib/draft/store.test.ts
A	frontend/src/lib/queries/bulletin-images.test.ts
A	frontend/src/lib/queries/bulletin-images.ts
M	frontend/src/lib/queries/keys.ts
M	frontend/src/lib/queries/services.ts
M	frontend/src/test/fixtures/index.ts
```
`0` (no server, API, type, workflow or package change: PR 3b is the frontend and the docs); the subjects oldest first: `Runbook: printed bulletin PR 3a record (backup, counts, SQL preview, merge, migration 0007)`, any later plan commit, then T7-T10's four subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR 3b**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> The cover picture on the Bulletin step (printed bulletin PR 3b) is verified on this machine: frontend 720 tests in 88 files (704 in 87 before), three runs in a row; backend unchanged at 1477 passed, 22 skipped; typecheck, lint and the production build are clean. It needs no database change (PR 3a made it, and it is live). The Bulletin step starts with **Cover picture**: choose a picture from your phone's photos (or take one), see it as the front page will trim it, choose another or remove it; last week's picture comes in with "From last week. Check before printing." and **Keep as is**; the Printed bulletin card lists "cover picture" when there is none. May I open the pull request as a **draft** titled "Printed bulletin PR 3b: the cover picture on the Bulletin step", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/printed3b-pr-body.md" <<'BODY'
Printed bulletin PR 3b: the cover picture on the Bulletin step (PR 3 planning answers of 2026-10-03), on the server of PR 3a (#<N1>, live since <date>). Spec: docs/superpowers/specs/2026-10-02-printed-bulletin-design.md. Plan: docs/superpowers/plans/2026-10-03-printed-bulletin-3.md (Tasks 7-12). No migration, no server change, no new package or variable.

- The draft v4: bulletin.cover_image_id and "cover" first among the boxes that carry; a v3 draft migrates with no picture and stays Saved.
- The Bulletin step's Cover picture: Choose a picture (JPEG or PNG, phone photos or camera), a preview trimmed as the front page prints it, Choose another picture, Remove; the server's limits said before an upload, its refusal after.
- Carry forward of last week's picture with "From last week. Check before printing." and Keep as is; Save as new service marks it; the mark is saved with the service.
- Every body says the picture (a PUT saves a Remove); a POST leaves "no picture" out; the 409 check compares it.
- The Printed bulletin card: the cover picture in its note, in "Not filled in" and in "From last week, not checked yet".
- docs/manual-verification.md: items 32-37 (the phone check, the print test). docs/ops-runbook.md: the PR 3a record (rides along).

Tests: frontend 704 → 720 in 87 → 88 files; backend 1477 passed, 22 skipped (unchanged)

After merge (Task 12): a guided phone check and the print test of a cover with a picture, then a "Printed bulletin PR 3b record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Printed bulletin PR 3b: the cover picture on the Bulletin step" \
  --body-file "<scratch>/printed3b-pr-body.md"
gh pr checks <N2> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass`; CI's numbers: backend `1477 passed, 22 skipped`, backend-postgres `22 passed, 1477 deselected`, frontend `720 passed` in 88 files. Then send: "PR #<N2> is green: 717 frontend tests in 88 files; the backend and its Postgres job unchanged and passing; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N2> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `bulletin-images.test.ts`, `schema.test.ts`, `migrate.test.ts`, `store.test.ts`, `mapping.test.ts`, `documents.test.ts`, `bulletin.test.ts` (but its "Not filled in" test: T9) | T7 |
| `bulletin-step.test.tsx` | T8 |
| `review-send-step.test.tsx` (its saving tests: T7), `builder-shell.test.tsx`, `liturgy-step.test.tsx` | T9 |
| `test_slice1_docs.py`, `test_docs.py` | T10 |
| a backend test | PR 3a's task (T1-T3): stop and tell the owner first, since that code is live |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, printed bulletin PR 3b final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1477 passed, 22 skipped`; frontend `720 passed` in 88 files.

### Task 12: PR 3b: the merge, the phone check, the print test, the record (OWNER + agent)

The owner's steps go **one at a time**. The agent writes each result into `<scratch>/printed3b-t12-results.md` (not committed), never a token, an email address, a phone number, a street address, a church id, a database URL, a name from the prayers and concerns, or a picture.

**Files:** Modify (the records PR, Step 9): `docs/ops-runbook.md`: insert `### Printed bulletin PR 3b record` right before `## Backups` (after `### Printed bulletin PR 3a record`).

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N2> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N2> (the cover picture on the Bulletin step) is ready and green, and the server it needs has been live since PR 3a. May I merge it with a merge commit? Only the website changes (no database step); I will tell you when it is live, then ask for a short phone check, one step at a time, and a print test." On a clear yes (not replayed):

```bash
gh pr merge <N2> --merge -R bbrown62450/church
gh pr view <N2> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N2> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both.

- [ ] **Step 2 (agent): The deploy**

About three minutes after the merge (not replayed): `curl -s https://church-production-74ca.up.railway.app/health/ready; echo` → `{"ok":true,"db":"ok"}` (Railway redeploys the same server code; no migration runs). Wait for Vercel's production deploy of the merge commit before the phone check.

- [ ] **Step 3 (OWNER, then agent): Phone, step 1 of 5: choose a picture (item 32)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. In the Service Builder, open **4 Bulletin**: is **Cover picture** the first group? Tap **Choose a picture** and pick a photo you took with the phone (one with no people in it is best for this test). Does it upload ("Uploading…") and then show the photo upright, trimmed to the cover's shape, with a dark band at the bottom holding the reading and the date? Then tap **Choose another picture**, pick another photo, and while it says "Uploading…" tap **5 Review & send** and come back: is the new photo there? Then on **5 Review & send** tap **Download printed bulletin**: does the cover show the picture filling the box under the church's name, in color, with the reading and the date in white on a dark band at the bottom? Tap **Download Word version**: the same picture?

(An iPhone photo that uploads answers planning answer 5: Safari sent it as a JPEG. If the page says "Choose a JPEG or PNG picture.", record it: the phone sent HEIC, and HEIC support is a follow-up for the owner to decide.)

- [ ] **Step 4 (OWNER, then agent): Phone, step 2 of 5: no picture (item 33)**

> Back on **4 Bulletin**, tap **Remove**, then download the printed bulletin again. Is the box gone, with the reading and the date centered where the picture was? Does the Printed bulletin card list "cover picture" under "Not filled in"? (Choose the picture again afterwards if you want it for this Sunday.)

- [ ] **Step 5 (OWNER, then agent): Phone, step 3 of 5: last week's picture (item 34)**

> With a picture chosen, tap **Save to archive** (or **Save changes**) on **5 Review & send**. Then open the menu (⋮) → **New service** and, on step 1, choose the Sunday one week after the service you just saved. On **4 Bulletin**: is the picture there, with "From last week. Check before printing."? Tap **Keep as is**: does the note go? You can delete this test service from **Services** afterwards.

- [ ] **Step 6 (OWNER, then agent): Phone, step 4 of 5: a file it refuses (item 35)**

> On **Cover picture**, tap **Choose another picture** and pick something that is not a photo, for example a PDF from Files (or skip this step if your phone offers only photos). Does the page say "Choose a JPEG or PNG picture." without uploading, and keep the picture you had?

- [ ] **Step 7 (OWNER, then agent): Step 5 of 5: the print test (item 36; planning answer 10)**

> At the church, print side 1 of this week's printed bulletin (the cover and page 1) on legal paper on the color printer. Is the picture in color and sharp, inside the margins, and are the reading and the date on the dark band easy to read? If the band looks too dark or too light, tell me; it is one number to change.

- [ ] **Step 8 (agent): The agent's own checks (item 37), the results**

On the production URL, in a test church the agent may change (one of the two slice 1 test churches the owner kept, never the owner's own church), signed in as its owner if the session has a test account, else skipped and recorded as "not run": item 37 (another church's picture id answers 404; the preview is fetched once; a draft from before PR 3b opens with everything and no picture). Then write each step's result, with the date, into `<scratch>/printed3b-t12-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 9 (agent): Write the record, and the records PR on the owner's yes**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it: `### Printed bulletin PR 3a record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Printed bulletin PR 3b record

Printed bulletin PR 3b (the cover picture on the Bulletin step: choose,
preview, remove, last week's carried forward with a check, printed in the
PDF and the Word version with the reading and the date on a dark band, or
alone with no picture) merged as PR #<N2>, the second of the two PRs of
printed bulletin PR 3, on the server of PR 3a (#<N1>). No database change.
The owner's check covered the "(owner, after PR 3b)" items of
`docs/manual-verification.md` → "Printed bulletin", the print test
included. No token, email address, phone number, street address, church
id, database URL, name or picture is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N2> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`. | <date> |
| 1. Choose a picture (phone: <phone and browser>) | <A phone photo uploaded (<JPEG from Safari / …>), shown upright and trimmed; the PDF and the Word version showed it with the reading and the date on the band. / …> | <date> |
| 2. No picture | <Remove: no box, the reading and the date centered; the card listed "cover picture". / …> | <date> |
| 3. Last week's picture | <On the Sunday after, the picture came in marked; Keep as is cleared the note. / …> | <date> |
| 4. A refused file | <"Choose a JPEG or PNG picture.", nothing uploaded. / Skipped: …> | <date> |
| 5. Print test (legal, color) | <The picture in color and sharp, inside the margins; the band readable. / Changes asked: …> | <date> |
| Agent checks | <Item 37 in a test church: <results>. / Not run: <why>.> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: 6a (Settings) | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye (no address, phone number, name or picture). Then (not replayed):

```bash
sed -n '/^### Printed bulletin PR 3b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Printed bulletin PR 3b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|\([0-9]{3}\)'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: printed bulletin PR 3b record (merge, phone check, print test)" -m "Records printed bulletin PR 3b (PR #<N2>): the merge and the deploy of the
cover picture on the Bulletin step, the owner's phone check, the print test
of a cover with a picture and the agent's checks. No token, email, phone
number, address, church id, database URL, name or picture is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit. Then ask: "The printed bulletin PR 3b record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: printed bulletin PR 3b record" \
  --body "Records printed bulletin PR 3b (PR #<N2>) in docs/ops-runbook.md → Printed bulletin PR 3b record: the merge, the deploy, the owner's phone check and the print test. No token, email, phone number, address, church id, database URL, name or picture is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Printed bulletin PR 3 is live and recorded; <n> follow-ups."

- [ ] **Step R (only if a release must come out): Prefer a fix forward; if PR 3b must come out, revert only the step's picture group; PR 3a only after it**

On the owner's yes for each outward command (README "Reverting PR 3b or PR 3a"; clarification 19). **PR 3b** (the step): a branch `claude/revert-printed-3b` from `origin/main`; revert T10's commit and T8's commit (their subjects "Docs: printed bulletin PR 3b manual checks" and "Printed bulletin PR 3b: the cover picture on the Bulletin step"; with any `Fix: …` commit of T8 first) one by one, newest first: `git revert --no-edit <T10 sha> <T8 sha>` (each with the trailer added by `git commit --amend` before the next); the frontend suite (`713 passed` in 88: 720 less T8's seven tests), typecheck and lint; a PR, CI, and the merge on the owner's yes; record it in the record. The draft v4, the carry, the bodies and the card stay, so every member's draft opens as it was; a picture already chosen or carried keeps printing and cannot be changed on the step until 3b returns (tell the owner so). Checked while planning: this revert, run on the planning worktree, typechecks, lints and passes `713` tests in 88 files. Reverting all of 3b is not offered: the 2b-2 reader refuses a version 4 draft (a restore error, the draft only backed up). **PR 3a**, only after the 3b revert is live and only if needed: `git revert -m 1 --no-commit <3a merge sha>`, then `git checkout <3a merge sha> -- backend/migrations/versions/0007_bulletin_images.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py`; both suites (`1436 passed, 21 skipped`: the baseline plus T1's four and its four Postgres ones; the frontend as it then is). The 3b frontend still standing then sends `cover_image_id`, which the API before 3a refuses (422): revert the rest of 3b first in that case, accepting the drafts' restore. Never `alembic downgrade` production for this: the database stays at `0007_bulletin_images`, which the older code ignores, and the pictures stay in the table, unread, until 3a returns.

Expected counts after this task: backend `1477 passed, 22 skipped` on `main`; frontend `720 passed` in 88 files. The records PR adds no test.

---
## Build notes

**How this plan was written (2026-10-03).** Each task's code was built and run in a throwaway worktree of the branch head (`fbc9598`), with the repo's `.venv` (a symlink), a hard-linked copy of `frontend/node_modules` (`cp -al`; Turbopack's production build refuses a `node_modules` symlink that points outside the project) and a local, throwaway Postgres 16 (`initdb` under `/var/lib/postgresql`, port 5433, a database of its own for the build and another for the replay; CI uses 17), one commit for each task's tests and one for its code. The directives were generated from those commits by a script (a new file as **Create**, an addition at the end of a file as **Append**, every other change as **In … replace** with the context grown until the block occurs once in the file as it stands at that point), so the plan's blocks are the built code. While building:
- **Row-level security on the new table.** 0003_lockdown enabled it on every table that existed then and nothing since created a table; `test_0003_is_idempotent_after_the_manual_lockdown` expects it on every model table at head, so 0007 turns it on itself (Postgres only), and T1 adds a Postgres test that `anon` and `authenticated` cannot read the table.
- **No multipart.** FastAPI needs `python-multipart` for `UploadFile`; it is in `.venv` only because Streamlit requires it, and `backend/requirements.txt` (what Railway installs) has none. A raw body (`Annotated[bytes, Body(media_type="application/octet-stream")]`) needs nothing new: FastAPI passes the bytes through for any Content-Type but JSON. A route reads its whole body before any dependency runs, so the 10 MB limit is checked from Content-Length by `UploadSizeMiddleware` before the body is read.
- **One picture for both files.** python-docx cannot lay text over a picture without hand-written drawing XML (a floating text box), so the band and its two lines are drawn into the picture by Pillow, with the Times Bold outline reportlab ships (`reportlab/fonts/_eb_____.pfb`, a Type 1 font FreeType reads), and the PDF places the same JPEG, so the two files match. At 300 dpi in a 372 x 300 pt box (1550 x 1250 px) the letters are print-sharp.
- **The PDF's box was not centered.** A reportlab `Flowable` aligns left unless told; PR 1's box sat at the left margin, 60 pt off center (seen on the 2b-2 sample). The cover's box now sets `hAlign = "CENTER"`, the placeholder included (the one change a 2b-2 page shows after 3a).
- **A picture left out is not a picture removed.** A 2b-2 page sends a bulletin without `cover_image_id`; read as "no picture" it would have dropped the saved picture on every `PUT` from an old tab and printed no box. `service_bulletin` keeps `cover_given` (False when the key is missing; `to_json` writes the key only when given), so a `PUT` keeps the saved picture and a download prints PR 1's box; `ServiceDraft.to_input` leaves the key out of what it reads when the client did not send it (`model_fields_set`).
- **"cover" among the boxes changes the API.** Adding it to `CARRY_KEYS` changes `ServiceBulletin.unchecked` and so `openapi.json`; it moved from T2 to T3 (the API's task), so every commit's `test_openapi_contract.py` holds.
- **No `-Input`/`-Output` split.** `ServiceBulletin` is both a request and a response model; a field with a default would split its schema in two (renaming it in `schema.d.ts`) if Pydantic marked defaults required when serializing; it does not by default, and the regenerated `ServiceBulletin` keeps its name with `cover_image_id?: string | null`.
- **The fingerprint of a draft saved before 3b.** With `cover_image_id: null` always in the payload, every draft saved under 2b-2 with bulletin fields would have turned "Unsaved changes" after the v4 migration; `bulletinPayload` leaves a null picture out and `serviceBody` adds it, and T7's migration test pins "Saved".
- **A large PNG's memory.** The first `prepare` kept three copies of a decoded picture (`exif_transpose`, `convert`, the original): a 49 MP PNG peaked at 640 MB more. The plan review then measured 767 MB for a transparent one; the review fixes below replace this. A 3.9 MB, 4032 x 3024 photo-like JPEG takes 0.15 s (draft decoding) and stores as 460 KB; its cover picture is 550 KB.
- **The Bulletin step's carry replaces an untouched box.** A test draft with a picture set by hand but not marked chosen had it replaced by last week's (none): the step's test uses `setCover`, which marks the box chosen, as the step does.
- **Every directive's file ends with a newline.** Three test files had their last block appended without one; the build commits were rewritten so the generated **Append** and **In … replace** blocks apply.
- **Sample booklets** (T5 Step 2's snippet, with a picture drawn by Pillow; no photo) rendered to images with PyMuPDF (in a separate throwaway virtualenv, not the repo's): side 1's left half shows the church's name, the picture centered and in color with "Matthew 22:1-14" and "October 18, 2026" in white on the band, then the contact lines; without a picture, the two lines in bold centered in the box's place and no frame; PR 1's box (a 2b-2 page) centered. The Word files were read back with python-docx (one inline picture of 372 x 300 pt, the same bytes as the PDF's; or the two centered lines); LibreOffice is not in the planning container, so the owner's phone check is their first visual check.
- **CI's alembic cycle by hand** on a fresh local Postgres database: `upgrade head`, `check` (`No new upgrade operations detected.`), `downgrade base`, `upgrade head`, `check`: clean; `relrowsecurity` true on `bulletin_images`.
- **The production build** at T10's commit compiles with the five builder routes.

**Plan review fixes (2026-10-03).** The adversarial review of this plan (3 Critical, 6 Important, 12 Minor) was answered by the owner's decisions, all applied to the build commits and replayed:
- **C1, phone JPEGs.** Pillow reads a JPEG with a multi-picture segment (iPhone HDR, Samsung portrait) as "MPO"; it is now taken as a JPEG (its first picture; T2 builds a two-picture MPO with an EXIF turn). `Image.open(formats=...)` gets `("JPEG", "PNG")`, not `"MPO"`: MPO has no opener of its own in Pillow 12.3 (`KeyError: 'MPO'`), the JPEG opener returns it, and `prepare` then checks `JPEG`, `MPO` or `PNG`. Only those two parsers are tried (M1).
- **C2, memory.** One picture at a time, on one worker thread (`bulletin_image._WORKER`, a 429 after 10 s of waiting); a PNG at most 24 MP; `Image.MAX_IMAGE_PIXELS` set to 50 M (Pillow refuses past twice that as it opens; a 422, with its warning silenced since the check says it); a large PNG reduced by a whole factor into a new small picture before anything else; transparency flattened, and the EXIF turn made, on the small picture. Measured (`ru_maxrss`, the review's files and 24 MP ones): the worst picture taken, a 24 MP palette PNG with transparency, about 216 MB more (RGBA 193, LA 193, 16-bit grey 114, RGB 121; a 49 MP progressive JPEG 152, baseline 32); the review's 49 MP PNGs are refused from their header (0 MB); twenty at once: 252 MB for the process (palette PNGs), 229 MB (RGBA), 173 MB (49 MP JPEGs). A lock alone was not enough: twenty threads taking turns under a lock grew to 2.2 GB, because glibc keeps freed memory in each thread's own arena; one worker thread (or `malloc_trim` after each, 239 MB) fixes that, and the thread needs no `ctypes`. T2 pins it: four 24 MP palette PNGs at once in a subprocess stay under 300 MB more (212 MB measured).
- **C3, storage.** The stored JPEG is at most 600 KB (quality 85, then 75, then 70 at 1400 px, 65 at 1200, 60 at 1000, 60 at 800; random noise, the worst case, stores as 545 KB at 1200 x 1200; a busy photo-like 12 MP picture stays at 1600 px, 460 KB). A church keeps at most 160 pictures (its oldest unused ones make room, any age; all in saved services: a 422). All churches' pictures together at most 150 MB (a 422 and a `storage_full` warning; `sum(length(bytes))`, which Postgres reads without the pictures). The 60-day removal runs on any church's upload, at most 20 a time, in its own transaction before the new picture's. The README gains "Checking the cover pictures' storage". Question 9 no longer claims the bucket protects the database.
- **I1.** The upload's callback is the mutation's own (`useUploadBulletinImage(onStored)`), so it runs after the step unmounts; it checks the draft is the same one (its `created_at` and date) and flushes the draft to storage. T8 swaps the step out of the layout mid-upload.
- **I2.** `useObjectUrl` makes and releases the URL in one effect keyed by the bytes (the `react-hooks/set-state-in-effect` rule is turned off on that line, with the reason); T8 renders under `<StrictMode>`: the URL shown is never one released, and only one is held.
- **I3.** T6 Step 5 sends a 9.5 MB body (401) and an 11 MB one (422) to production, signed out, before PR 3b.
- **I4.** `GET /bulletin-images/{id}`: `Cache-Control: private, no-cache`, `ETag` (the id), 304 on `If-None-Match` (after checking the church), `Vary: Authorization, X-Church-Id` (CORS adds `Origin`), `X-Content-Type-Options: nosniff`. No cookie is used, so `Vary` does not name it.
- **I5.** The removal takes its candidates `FOR UPDATE` and then reads the saved services; a save takes its picture `FOR SHARE` (`has_image(..., lock=True)` in `_with_known_cover`). On SQLite (which ignores both) T3 slips a save in between the lock and the read and the picture stays; on Postgres a test holds each lock and sees the other time out after 200 ms, both ways.
- **I6.** Every owner-facing size (Goal, clarifications 2 and 20, Risks, questions 5, 9, 13, 18, the README's step 2, the spec) is restated from these measurements.
- **Minor.** M2: a 16-bit grey PNG keeps its tones (mid-grey stores as 128, not 255). M3: the color profile is read before anything else and converted with or without transparency. M4: an empty file is refused by `checkPicture`, and an empty body reaches the usecase (the body has a default, so the sign-in is checked first) and gets the picture message. M6: `fitted_sizes` shrinks both lines by one factor. M7: under 800 px on the long side the step says "This picture is small and may print blurry.". M8: the preview has a CSS band with the reading and the date (question 16). M9: README step 4 uses `to_regclass` and counts through `query_to_xml`, and runs before 0007 (a Postgres test at 0006). M10: 0007 has 0003's guarded REVOKE for its table (a Postgres test re-opens default privileges first). M11: the 2b-2 tab after 3b, accepted (Risks, question 17). M5 and M12 are noted (clarification 10, Risks), not changed.

**The rollback was run, not only written.** In a third worktree at the built head, T12 Step R's revert of the step's picture group (T10's and T8's commits) typechecked, linted and passed `713` frontend tests in 88 files. Reverting the whole of 3b would leave the 2b-2 reader, which refuses a version 4 draft.

**Replay of the finished plan (2026-10-03, after the plan review fixes).** The directives of T1-T4 and T7-T10 were applied in order (by a script that parses the plan's **Create**, **Append** and **In … replace** blocks step by step) onto a fresh detached worktree of the branch head (`380cf29`: `fbc9598`, the plan's earlier commits and "WIP plan: printed bulletin PR 3 plan review fixes (before the replay)"), with the repo's `.venv`, a hard-linked copy of `frontend/node_modules` and a fresh database on the local Postgres 16 (`TEST_DATABASE_URL`). Each step's commands were run as written and each task committed with its own commit block (T5, T6, T11 and T12 are verification and owner steps; their local commands were run as described below):
- Baselines before T1: backend `1432 passed, 17 skipped`; Postgres-marked `17 passed, 1432 deselected`; frontend `704 passed` in 87 files.
- All 169 directives applied (T1 11 + 6, T2 7 + 24, T3 10 + 26, T4 4, T7 26 + 28, T8 8 + 8, T9 5 + 5, T10 1); every Replace anchor occurred exactly once. After T10, `backend`, `frontend/src` and `docs` (but the plans) equaled the build worktree's (`git diff`: empty), and `git status` was clean after every commit.
- Every "see it fail" output is quoted from this replay (times as `<t>`): T1 `16 failed, 59 passed, 7 skipped` (Postgres `6 failed, 7 passed, 33 deselected`); T2 the two collection errors, then `2 failed, 26 passed`; T3 the collection error, then `20 failed, 68 passed, 1 skipped`; T7 seventeen failures and one file that cannot load (`17 failed | 72 passed (89)`); T8 `8 failed | 7 passed (15)`; T9 `4 failed | 93 passed (97)`.
- Every count matched the table: backend 1436, 1463, 1477 (21 skipped from T1, 22 from T3); Postgres-marked `21 passed, 1436 deselected`, `21 passed, 1463 deselected`, `22 passed, 1477 deselected` (each with the onboarding timing test's `1 warning`, as on `main`); T1's files `79 passed, 7 skipped` and the 27 preview lines; T2's `78 passed`; T3's `121 passed, 1 skipped`, the OpenAPI export and `gen:api` `2 files changed, 488 insertions(+), 2 deletions(-)`, frontend still `704` in 87, typecheck 0, lint 0; T4 `89 passed`, `282:## Printed bulletin`, `4`, `0`, `2 files changed, 41 insertions(+), 7 deletions(-)`; frontend 712, 719, 720 in 88; T7's files `91 passed`, T8's `15 passed` and T9's `97 passed` three times each, no flaky run; typecheck 0 and lint 0 after every frontend task; T10 `89 passed`, `282:## Printed bulletin`, `0`, `1 file changed, 6 insertions(+)`.
- T5 Steps 2-3 at T4's commit (PR 3a as it would be opened, with `e4f3695`, today's `origin/main`, as the base): `1477 passed, 22 skipped`; Postgres `22 passed, 1477 deselected`; frontend `704` in 87; typecheck 0, lint 0; the production build `✓ Compiled successfully` with the five builder routes; `samples written` (looked at, rendered with PyMuPDF: the picture filling the box under the church's name, centered, in color, with "Matthew 22:1-14" and "October 18, 2026" in white on the band; without one, the two lines in bold centered and no box; the Word files read back with python-docx: one inline picture of 372 x 300 pt, or the two centered lines; a cover with a long reading, rendered separately, keeps the reading larger than the date); CI's alembic cycle on a fresh database clean (`No new upgrade operations detected.` twice); regenerating `openapi.json` and `schema.d.ts` changed nothing; the 27 preview lines; `imports grep exit 1`; the 40 paths exactly (with `M docs/ops-runbook.md`); `0` paths among the untouched server files and the frontend's pages, components, draft, queries and bodies; every commit has the trailer.
- T11 Steps 2-3 at T10's commit, with T4's commit standing in for `main` after the 3a merge: `1477 passed, 22 skipped`; Postgres `22 passed, 1477 deselected`; frontend three times `720` in 88; typecheck 0, lint 0; the build with `○ /builder/bulletin`; the API files unchanged; `raw html grep exit 1`; the 21 paths of the list but the 3a record (not written in a replay); `0` server, API, type, workflow or package paths; T7-T10's four subjects. No em dash in any added line outside the plans; two new log lines (`bulletin_images.upload`, `bulletin_images.storage_full`).
- T12 Step R's revert of the step's picture group (T10's and T8's commits), run on the replay worktree: typecheck 0, lint 0, `713 passed` in 88 files.
- Not run while planning: the pushes, the PRs and CI, the backup, the owner's queries on production, the merges, Railway's and Vercel's deploys (and so T6 Step 5's 9.5 MB and 11 MB checks against Railway's proxy), the phone checks, the print test and the records (T6, T11 Step 1's production check, T12).

## Spec coverage

| Owner answer or S item | Task(s) and tests |
|---|---|
| Planning answer 1: two PRs, server first | T1-T4 (PR 3a), T7-T10 (PR 3b); T5 Step 3 and T11 Step 3 (the paths: nothing of the pages in 3a, nothing of the server in 3b); T3 `test_the_cover_picture_is_saved_kept_by_an_older_page_and_carried` and `test_the_cover_picture_prints_and_a_page_from_before_3b_keeps_pr_1_s_box` (a 2b-2 page keeps working) |
| Planning answer 2: the reading and the date in white on a dark see-through band | T2 `test_the_cover_fills_the_box_with_a_centered_crop_and_a_dark_band`, `test_a_long_reading_is_shrunk_to_fit_the_band`, `test_a_long_reading_and_the_date_shrink_together`, `test_the_cover_picture_fills_the_box_in_both_files`; T8 the band over the preview |
| Planning answer 3: the picture fills the box, centered crop | T2 `test_the_cover_fills_the_box_with_a_centered_crop_and_a_dark_band`; T8 "uploads a chosen picture, shows it trimmed as the front page prints it…" (`object-cover`) |
| Planning answer 4: color | T2 (the band's test checks the picture's colors); T12 Step 7 (the print test) |
| Planning answer 5: JPEG and PNG only, an iPhone photo as JPEG | T2 `test_only_a_jpeg_or_png_of_at_most_10_mb_and_50_million_pixels_is_taken`, `test_a_photo_is_turned_upright`, `test_a_phone_s_multi_picture_jpeg_is_taken_as_a_jpeg`; T3 `test_only_a_jpeg_or_png_of_at_most_10_mb_is_taken`, `test_a_body_without_its_size_is_refused_before_it_is_read`; T7 "takes a JPEG or PNG of at most 10 MB…"; T8 "says a file the server would refuse…"; T12 Step 3 (the owner's iPhone) |
| Planning answer 6: no picture, no box, the reading and the date centered | T2 `test_no_picture_prints_the_reading_and_the_date_where_it_would_be`, `test_the_cover_holds_the_picture_the_reading_alone_or_pr_1_s_box`; T3 the printed test (null and another church's id); T9 "Not filled in: … cover picture"; T12 Step 4 |
| Planning answer 7: last week's picture carries with the mark and Keep as is | T3 `test_the_cover_picture_is_the_first_box_to_check`, the services test (`previous-bulletin` carries it); T7 "carries last week's picture, marked to check first…", "is marked to check on Save as new service…"; T8 "carries last week's picture with its note until it is kept…"; T9 "carries last week's cover picture in, lists it to check, and prints it"; T12 Step 5 |
| Planning answer 8: any member uploads | T3 `test_any_member_uploads_a_picture_and_sees_it`, `test_every_route_is_church_isolated` |
| Planning answer 9: unused pictures removed after 60 days | T3 `test_an_upload_removes_any_church_s_pictures_unused_for_60_days`, `test_the_removal_reads_the_saved_services_after_it_locks_its_candidates`, `test_a_save_and_the_removal_wait_for_each_other` (Postgres) |
| Plan review limits (clarification 20): memory, size, a church's 160, the budget | T2 `test_four_large_pngs_at_once_take_the_memory_of_one`, `test_an_upload_waits_its_turn_then_is_told_to_try_again`, `test_a_busy_picture_is_stored_in_at_most_600_kb`; T3 `test_a_church_keeps_at_most_its_quota_of_pictures`, `test_uploads_stop_when_every_church_s_pictures_reach_the_storage_budget`; T1 `test_the_owner_s_read_only_queries_around_0007` (the storage query) |
| Planning answer 10: the 0006 routine, a phone check after each PR, the print test | T1 `test_offline_sql_for_0007_is_one_table_one_index_and_row_level_security_under_the_timeouts`, `test_the_readme_shows_the_0007_preview_exactly`, `test_the_owner_s_read_only_queries_around_0007`; T6 Steps 1-6; T12 Steps 3-7 |
| S "Data model": `bulletin_images`, 0007, upright, 1600 px, JPEG, `cover_image_id`, the removal | T1 `test_0007_creates_the_bulletin_images_table_and_changes_nothing_else`, `test_0007_downgrade_drops_only_the_table`, `test_0007_turns_on_row_level_security_and_grants_supabase_s_roles_nothing`, `test_0007_revokes_supabase_s_roles_even_when_default_privileges_would_grant`, `test_the_after_deploy_check_runs_before_0007_too`; T2 `test_a_16_bit_grey_png_keeps_its_tones`, `test_a_color_profile_is_converted_to_srgb_with_or_without_transparency`; T2 `test_a_large_photo_is_stored_as_a_jpeg_at_most_1600_px_on_its_long_side`, `test_the_stored_picture_keeps_no_camera_data`, `test_the_cover_picture_is_read_stored_and_carried`; T3 the API tests |
| S "API": `POST /bulletin-images`, `GET /bulletin-images/{id}` | T3 `test_api_bulletin_images.py` (8 tests and cases), `test_route_guards.py` (both church-scoped), `test_openapi_contract.py` |
| S "The Bulletin step": the picture on the step | T8 (the seven tests: the upload, the band and Remove, a refused file, the carry, a picture gone, the step left mid-upload, StrictMode, a small picture; 44 px buttons) |
| F §4.6 (versioning; never destroy typed input) | T7 the v3 → v4 migration test ("stays Saved"); the carry never over a box chosen, removed or kept; T12 Step R (the rollback keeps the drafts) |
| F §2.5 (logs without content) | T3 `test_any_member_uploads_a_picture_and_sees_it` (the log line: ids and sizes) |
| Layering (no FastAPI or Streamlit below the API) | T3 `test_no_streamlit_in_core.py` (three modules added); T5 imports grep |
| OpenAPI and types regenerated | T3 Step 4; T5 Step 3, T11 Step 3; `test_openapi_contract.py` |

S items **not** in PR 3: a route to delete one picture, HEIC (planning answer 5), shrinking in the browser (question 6), the picture on the Word working copies, the Bulletin settings' move into Settings (6a).

## Follow-ups (not in 3)

- `DELETE /bulletin-images/{id}` for a picture uploaded by mistake (today Remove takes it off the bulletin and the 60-day removal takes it from the database; question 8).
- Shrinking the picture in the browser before the upload, if the owner's phone check finds uploads slow (question 6).
- HEIC, if the owner's iPhone sends one (T12 Step 3): a `pillow-heif` package on the server, or a conversion in the browser.
- A lower pixel cap for PNG (`MAX_PNG_PIXELS`) if Railway's memory is small (Risks).
- A higher `MAX_PICTURES` when a church nears 160 pictures in saved services (about three years of a new picture every week; question 18), or a smaller `STORAGE_BUDGET` if the database grows for other reasons.
- Refusing a `POST /bulletin-images` without an `Authorization` header in `UploadSizeMiddleware`, before its body is read, and a light bucket on the GET (the review's M12; not changed now).
- The band's opacity and sizes, if the print test asks (`bulletin_image.BAND_OPACITY`, `printed_bulletin.COVER_TEXT_POINTS`).
- `printed_bulletin.PLACEHOLDERS` and the "[Cover picture]" box can go once no page from before PR 3b can be open (the 2b plan's follow-up, now with the cover too).
- The database's size in each later record (question 13).

## Questions for the owner

**Owner's answer (Beau, 2026-10-04): "all recommended, 160, yes start building".** Questions 1-18 below are accepted as written, with one change: a church keeps at most **160** pictures, not 60 (`MAX_PICTURES = 160`; about three years of a new picture every week; at most 96 MB, inside the 150 MB budget). Binding for the build.

Your answers of 2026-10-02 (the ten answers, layout B, the PR 1 plan's twelve, the eight PR 2 planning answers) and of 2026-10-03 (the PR 2a plan's fourteen, the PR 2b plan's seventeen, the ten PR 3 planning answers) are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **What PR 3a changes for you** (clarifications 4, 18): nothing on the website; the printed bulletin from today's pages keeps its "[Cover picture]" box, which now sits centered under the church's name in the PDF (it was at the left margin; the Word version's was centered on 2026-10-03). Recommended: accept (center it now).
2. **One picture for the PDF and the Word version** (clarification 3): the server draws the band and the two lines into the picture itself, so both files show exactly the same cover; the PDF is the print copy. The other choice is printing the reading and the date as text over the picture in the PDF only (sharper letters, but Word could not match it). In the Word version the band's words are part of the picture, so to change them you change the service and download again. Recommended: one picture for both.
3. **The band's look** (clarification 3): black at 55 % across the bottom, the reading 18 pt and the date 14 pt in white bold Times, centered, a long reading made smaller to fit, and the date with it, so the reading is never smaller than the date; the band about a fifth of the picture's height. Recommended: accept, and adjust after the print test if needed (one number each).
4. **No picture** (clarification 4): no box, no frame; the reading (18 pt) and the date (14 pt), bold and black, centered in the box's place, so the address lines stay where they are. Recommended: accept.
5. **What a picture becomes** (clarification 2): a JPEG or PNG up to 10 MB (a phone photo with a second picture inside, as iPhone HDR and Samsung portrait photos have, counts as a JPEG); it is turned upright, its colors made right for printing, made at most 1600 pixels on its long side (sharp at the cover's size) and at most 0.6 MB (a very busy picture is saved a little softer or smaller to fit; a phone photo usually stays at full size, 0.2-0.5 MB), and kept without the phone's hidden data (location, time, phone model). Recommended: accept.
6. **No shrinking on the phone before the upload** (Risks): a phone photo of 2-5 MB uploads as it is, in a few seconds on Wi-Fi and up to about 20 s on a slow connection; the page waits a minute, and you can go on to another step meanwhile (the picture still lands in this week's service). The other choice is to shrink it on the phone first (faster on a slow connection, more code in the page that the tests cannot fully check). A photo over 10 MB (a phone set to 48 MP) is refused with a message. Recommended: no shrinking now; add it if your phone check finds uploads slow.
7. **Who sees the pictures** (clarifications 6, 13): any member of your church who opens the service sees its picture, as with the rest of a saved service; Supabase's own web access cannot read them; another church never can. The browser keeps a picture only for itself and asks the app again each time it shows it, so after someone signs out of a shared computer the picture is not shown from the browser's memory. Pictures of people, children especially, are for the church's own photo policy. Recommended: accept.
8. **When old pictures go** (clarification 7): a picture uploaded more than 60 days ago that no saved service of its church uses is removed the next time anyone, in any church, uploads a picture (a few at a time; no timer to run), so a church that stops uploading still loses its unused pictures. A picture you remove from a bulletin, or whose service you delete, stays in the database until then; a picture chosen on a phone but not yet saved is kept at least 60 days. Recommended: accept.
9. **A limit on uploads** (clarification 10): at most 20 pictures an hour for one person and 60 a day for a church; past it the page says "Too many requests. Try again in … seconds.". This stops a stuck button or a runaway page, but on its own it does not protect the database: anyone with a Google account can create a church of their own and upload there. The protections for that are question 18. Recommended: accept.
10. **Last week's picture is the first box to check** (clarification 5): it carries like the music, its note and **Keep as is** under the preview, and "cover picture" comes first in "From last week, not checked yet". "Save as new service" marks it too. Recommended: accept.
11. **The card lists a missing picture** (clarification 9): with no picture, "Not filled in: …" names "cover picture" (as it names the prelude), so a week without one is a choice, not a surprise; nothing stops a download. Recommended: list it.
12. **The checks** (clarification 14; Tasks 6 and 12): around PR 3a, as for migration 0006, one at a time: I start the backup on your yes; you run one read-only query (now also showing the database's size); I show you the SQL (one new table, closed to Supabase's web access) and explain it; after the deploy, one more read-only query (it also works if run too early, and then says so), my own check that a phone-sized picture gets through Railway to the app, and a short phone check that the builder works as before. After PR 3b, four short phone steps (a photo from your phone, which also checks that Safari sends an iPhone photo as a JPEG; Remove; last week's picture; a file it refuses) and the print test of a cover with a picture on the color printer. Recommended: accept.
13. **The database's size** (Risks; clarification 20): a stored picture is at most 0.6 MB (a phone photo usually 0.2-0.5 MB), so a new picture every week is at most about 25 MB a year for a church; a church keeps at most 160 pictures (96 MB at most), and the app takes no more pictures once all churches' pictures together reach 150 MB of the free plan's 500 MB. The counting query records the size before PR 3a, later records note it, and a query in `backend/migrations/README.md` shows the pictures' share at any time. Recommended: accept, and look again when the pictures pass about 100 MB.
14. **Undoing PR 3b** (clarification 19): if something goes wrong on the step, I fix it forward. If it must come out, only the picture part of the step goes, so everyone's unsaved work is kept; until it returns, a picture already chosen (or carried from last week) keeps printing and cannot be changed. Recommended: accept.
15. **Two pull requests, the server first** (clarification 18; planning answer 1 as written): as for the Bulletin step, no page ever talks to a server that does not understand it, and you can keep using the app during both deploys. Recommended: as you decided.
16. **The preview shows the band** (clarification 8): on the step, the preview has a dark strip across its bottom with the reading and the date, roughly as they print, so you can see what the band will cover (a face or a steeple at the bottom of a photo) before you print; it is close to the printed band, not an exact copy. A picture smaller than 800 pixels on its long side still uploads, with "This picture is small and may print blurry." under it. Recommended: accept.
17. **An old tab after PR 3b** (clarification 19; Risks): a page opened before PR 3b went live and not reloaded keeps working; saving from it keeps the picture but drops its "From last week" note, and downloading from it prints the empty "[Cover picture]" box instead of the picture. Reloading the page fixes both. Recommended: accept (no extra code for a short overlap).
18. **Limits that protect every church** (clarification 20; Risks): because anyone with a Google account can create a church, the server (a) prepares one picture at a time (another waits a few seconds; after 10 s the page says "Another picture is being prepared. Try again in a few seconds."), so its memory stays near a quarter of a gigabyte even when many pictures arrive at once; (b) lets a church keep at most 160 pictures: past that its oldest picture no saved service uses makes room, and when all 160 are in saved services the page says "Your church keeps 160 pictures, all in saved services. Remove the picture from an older service, then try again." (a church with a new picture every week reaches that after about three years; the number is easy to raise); (c) takes no more pictures from anyone once all churches' pictures reach 150 MB, saying "The app has no room for more pictures right now. Please tell the app's administrator." and noting it in Railway's log, so saving services keeps working. Someone determined could reach the 150 MB in about half a day; uploads would then stop for every church until old unused pictures go or the church made for it is removed. Recommended: accept these numbers, and raise the 60 when your church gets close.

Owner steps still to come: the plan's approval; for PR 3a, the draft PR on your yes and ready on your yes (T5), the backup on your yes, the counts and the SQL check, the merge on your yes, the after-deploy query and the short phone check (T6); for PR 3b, the draft PR on your yes and ready on your yes (T11), the merge on your yes, the phone steps and the print test, and the records PR (T12).
