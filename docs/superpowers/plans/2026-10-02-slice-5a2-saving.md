# Slice 5a-2: Saving Backend and Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the second of the three 5a PRs (owner answer 1, 2026-10-01): **saving on the server, and migration `0005_services_extras` on its own.** After it merges, the API can save a service (`POST /services`), list the church's saved services (`GET /services`, 20 a page, newest service date first), open one (`GET /services/{id}`), save changes to it (`PUT /services/{id}` with `If-Match`, 409 when someone else saved first) and delete it (`DELETE /services/{id}`, any member). Every save rebuilds that date's hymn use from all the services saved for it, and a delete recalculates the date it leaves (owner answer 6: Streamlit is retired). Production gets two nullable columns on `services` (`custom_elements`, `hymnal`) and the index `ix_services_church_date`, after a backup, read-only counts and a look at the migration's SQL (owner answer 8). **Nothing changes on screen**: the frontend gets only the regenerated API types; the Save card and the Services page are 5a-3. So hymn use stays unrecorded until 5a-3's Save (as since Streamlit's retirement). Production Streamlit (branch `streamlit-frozen`) is untouched.

**Architecture:** Backend only, bottom up. `0005_services_extras` (expand-only, batch mode as `0004`, under `env.py`'s 5 s lock timeout) and the two `Service` columns plus the index. `api/idempotency.run_idempotent` gains `church_id` (F §1.6 church-scope amendment). `service_output` gains the tolerant readers of stored dates and hymns (`normalize_date_iso`, `stored_hymn_entries`, `slot_map`) and the 3-slot writer (`stored_hymns`); `hymn_usage.rebuild_usage_for_date` replaces one date's rows with the union of its saved services, deduped by slice 3a's title-only `usage_key`, under a Postgres advisory lock. A new `repos/services.py` holds the archive's queries (Streamlit's `service_archive.py` stays as it is); `usecases/archive.py` gains `create_service`, `replace_service` (row lock, If-Match), `get_service` (stored data normalized), `list_services` and `delete_service`, each one transaction with its usage rebuild. `api/routes/services.py` has five plain `def` routes; `api/schemas.py` gains `DeletedOut`, `AuthorOut`, `ArchivedHymn`, `ArchivedHymns`, `ServiceOut`, `ServiceSummary`. The owner's production steps (backup, counts, preview, after-deploy check) live in `backend/migrations/README.md`, with their SQL run by the Postgres tests and the preview pinned by a test.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, SQLAlchemy 2, Alembic, pytest (SQLite; Postgres for `@pytest.mark.postgres`); the frontend only regenerates `openapi.json` and `schema.d.ts` (openapi-typescript), then Vitest 3, `tsc`, ESLint as checks.

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`: Scope (F4, F5, F7), API (the four `/services` rows, "Check order for `PUT`", "Schemas", "Normalizing stored data"), Backend (`service_output.py`'s stored-data rows, `usecases/archive.py`'s save, list, get and delete rows, `hymn_usage.py`, `repos/hymns.py`, `db/models.py`), "Data access and tenancy", "Data and migrations", Testing (`test_archive_usecase.py`, `test_api_services.py`, Migrations, Postgres), acceptance criteria 6-12, Risks (concurrent saves, Alembic), and the **Amendment 2026-10-01** (three PRs; owner answers 1-9).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.2 (scoping, isolation tests), §1.4 (paging), §1.6 (idempotency, with the **2026-09-28 church-scope amendment**: "5a `POST /services` … must add the resolved church id to the scope"), §1.7 (`If-Match` → 409 message), §2.2 (layer rules), §3.1 (`env.py`'s `lock_timeout`), §3.4 (expand-only), §3.5 (the revision chain; the `0005_services_extras` row), §5.1, §6.2 (the data shape a save writes), §7.4 (the `record_usage` race), the Amendments rows naming 5a, and the §4.4 row of 2026-09-29 (recent use matched on the title alone).
- Format model: `docs/superpowers/plans/2026-10-01-slice-5a1-documents.md`.
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `2cd4b79` = `origin/main` `bdfd422` plus one runbook commit, 2026-10-02): backend `1263 passed, 11 skipped`; Postgres-marked run `11 passed, 1263 deselected` (local Postgres 16); frontend `618 passed` in 81 files; typecheck and lint clean; Alembic head `0004_invites_reusable` (production too: runbook "Slice 5a-1 record"); 4 runbook owner markers. `api/idempotency.py` keys its store by `(user_id, method, route template, key)`, no church. `usecases/archive.py` has `ServiceInput`, `clean_input`, `resolve_hymn_refs` (5a-1). `ServiceDraft` (`api/schemas.py`) has `hymnal` and `custom_elements` and `extra="forbid"`. `hymn_search.usage_key(title)` takes the title alone. `hymn_usage.record_usage` (Streamlit's) checks then inserts. `services` has no `custom_elements`, `hymnal` or date index; `test_migrations.py` already asserts a single head; `test_schema_check.py`, `test_api_app.py` pin the head `0004_invites_reusable`. `CORSMiddleware` already allows `If-Match` and `Idempotency-Key`. No frontend code calls `/services`; `lib/queries/keys.ts` already has the `services` keys.
- Every task's code was written and run by the planner in a throwaway worktree of `2cd4b79`, and the plan's directives were then replayed onto a fresh worktree of `2cd4b79` (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one file `.venv/bin/python -m pytest -q <file> 2>&1 | tail -3`; the suite `.venv/bin/python -m pytest -q | tail -1`. Postgres-marked tests run only with `TEST_DATABASE_URL` set to a local, throwaway Postgres (`tests/pg_helpers.require_local_test_url`); without it they skip, and CI's `backend-postgres` job runs them. Frontend: the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`, then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes (T5), so T5 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand.
- Branch `claude/slice-2-plan-4q33le`, at `2cd4b79` plus this plan's commits (`WIP plan: slice 5a-2` …, then `Plan: slice 5a-2, saving backend and migration (owner answers 2026-10-01/02)`), then T1-T7. Stage files by name; `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1263 → 1330 passed, 11 → 16 skipped; frontend 618 → 618 in 81 → 81 files`.
- New prose for the owner has no em dashes and no flattery. No new user-facing copy in the app (clarification 1); the API's messages are the spec's, listed in clarification 3.
- No church id, email address, token or database URL in any doc, commit or record.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action (the backup run included). Owner steps go one at a time, in plain words.

### How the file directives below read
As in the 5a-1 plan: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything.

### Baselines and counts
- Starting baselines: backend **1263 passed, 11 skipped**; frontend **618 passed in 81 files**, typecheck and lint clean; Alembic head **`0004_invites_reusable`**; runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case). The frontend count never moves.

  | After | Backend (delta) | Backend | Frontend |
  |---|---|---|---|
  | T1 | +3 (`test_migrations.py`; `test_schema_check.py`, `test_api_app.py` edited) | 1266 passed, 11 skipped | 618 in 81 |
  | T2 | +1 (`test_idempotency.py`) | 1267 passed, 11 skipped | 618 in 81 |
  | T3 | +16 (`test_service_output.py` 5, `test_usage_rebuild.py` 11 with one test in five cases) | 1283 passed, 11 skipped | 618 in 81 |
  | T4 | +24 (`test_usecase_archive.py`, one test in five cases; `test_no_streamlit_in_core.py` edited) | 1307 passed, 11 skipped | 618 in 81 |
  | T5 | +22 (`test_api_services.py`, three tests in 2, 6 and 4 cases) | 1329 passed, 11 skipped | 618 in 81 |
  | T6 | +1 run, +5 skipped (`test_migrations.py` 1; `test_services_postgres.py` 5, Postgres only) | 1330 passed, 16 skipped | 618 in 81 |
  | T7 | 0 (docs) | 1330 passed, 16 skipped | 618 in 81 |

- CI `backend-postgres` goes from `11 passed, 1263 deselected` to `16 passed, 1330 deselected`. With a local Postgres (`TEST_DATABASE_URL`), the same numbers locally.

### Layering and code rules (carried)
- `usecases/archive.py`, `repos/services.py`, `hymn_usage.py` and `service_output.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains `repos.services` and `hymn_usage`, T4). The routes are plain `def`, one usecase call each, no SQL and no try/except (F §2.2 rule 1). Usecases own the transactions (`with session_scope() as s:`) and pass `session=s` down (F §2.2 rule 3).
- Ids through `db.ids.as_uuid`; every query filters on `church_id` (F §1.2); every route depends on `require_church` (`test_route_guards.py` unchanged).
- Logs carry ids, counts and durations, never a service's text (F §2.5): `archive.<create|replace|delete> church=<id> service=<id> usage_rows=<n> ms=<n>`.
- Expand-only migration (F §3.4); every new index named in the model and the revision (F §3.1).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** (branch `streamlit-frozen`) is frozen and retired for real use (owner answer 6); merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge; Railway's Pre-deploy Command `alembic upgrade head` applies migrations (runbook "Alembic stamping record").
4. **The 5a spec's decisions** stand, except where the owner answers below change them (S gains an amendment, T7).

### Owner answers (Beau, 2026-10-01 and 2026-10-02, binding)
1. **Three PRs.** (1) Word downloads (5a-1, merged as PR #40). (2) **Saving: the backend and migration `0005_services_extras` on its own: this plan.** (3) The Save card and the Services page (5a-3, its own plan).
4. **A saved service fixes a default-following Benediction and the communion setting to what was saved.** The frontend part is 5a-3 (its Save sends the Benediction as text); the backend stores exactly what it is given (clarification 7).
6. **Streamlit is retired.** Deleting a service recalculates that date's hymn use from the services still saved (this supersedes S's open question 1 and behavior change 4). Hymn use is recorded on save: each save replaces that date's rows with the union of every saved service on that date, deduped by the title-only usage key (clarification 8).
8. **Before `0005` runs on production:** a backup, read-only counts of the saved services (total, undated, old-style hymn lists), and a look at the migration's `--sql` preview. No Streamlit compatibility check (clarification 14; T9).
9. **Reviewer notes stay in memory** only: nothing about them is saved (clarification 17).

Answers 2, 3, 5 and 7 concern 5a-1 and 5a-3 and are not repeated here.

### Owner answers to this plan's questions
None yet: "Questions for the owner" (end of this plan) lists the choices, each written as recommended. The plan is built as recommended; an answer that differs is a change before T1.

**Later, out of scope:** 5a-3 (the Save card, the conflict dialog, the Services page, `serviceToDraft`, `draftToServicePayload`'s final form, the save key in the draft, the draft version bump, `"review"` in `SHIPPED_STEPS`, the query hooks `useServices`, `useSaveService`, `useDeleteService`), 5b (email).

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended).

1. **[owner-visible] Nothing changes on screen in 5a-2.** The PR adds API routes, a migration and the regenerated types (`openapi.json`, `schema.d.ts`). It adds **no** frontend client function or hook: 5a-3 writes `useSaveService`, `useServices`, `useDeleteService` with their DOM tests, and a function with no caller and no test would only be dead code until then (the generated types are enough for 5a-3 to start). The Review step keeps "Saving services to the archive is coming soon."; the step bar and the summary still read "Not in archive". Frontend tests stay at 618 in 81.
2. **[owner-visible] Hymn use stays unrecorded until 5a-3.** Since Streamlit's retirement nothing records hymn use (5a-1 record, "Hymn use is not recorded until 5a-3's Save"). 5a-2 makes saving record it, but nothing in the app saves until 5a-3's Save card, so the Hymns step's "Used …" marks and the 12-week exclusion still miss services built until then.
3. **The routes** (S API; F §1.2, §1.4, §1.6, §1.7). All church-scoped (`require_church`), any member (owner decision 5), plain `def`, in `api/routes/services.py`:

   | Route | Answer | Errors (code, exact message) |
   |---|---|---|
   | `GET /services?limit=&offset=` | 200 `Page[ServiceSummary]`; `limit` 1-200, **default 20** (the UI's page; S had 50), `offset` 0-1 000 000 | 422 `invalid_request` (paging) |
   | `GET /services/{service_id}` | 200 `ServiceOut` | 404 `not_found` "That service is no longer in the archive." (unknown id or another church's); 422 (malformed UUID) |
   | `POST /services` | 201 `ServiceOut`; optional `Idempotency-Key` (clarification 4) | 404 `not_found` "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step." with `details.field = "hymns.<slot>.hymn_id"`; 422 (Pydantic, with `fields`) or "Give each custom element a label." on `custom_elements.<i>.label`; 422 `idempotency_mismatch` "This request was already sent with different details." |
   | `PUT /services/{service_id}` | 200 `ServiceOut` with a new `saved_at`; `If-Match` required | as clarification 5 |
   | `DELETE /services/{service_id}` | 200 `DeletedOut` `{"deleted": true}` | 404 "That service is no longer in the archive." |

4. **The idempotency key is scoped to the church** (F §1.6, amendment 2026-09-28). `run_idempotent` gains `church_id: Optional[uuid.UUID] = None` and keys its store by `(user_id, church_id, method, route, key)`. `POST /services` passes `church.id`; `POST /churches` passes nothing (user-scoped, unchanged). So a key sent in two churches saves in each and never replays one church's answer to the other. Everything else is slice 1's: a replay returns the stored 201 with `Idempotent-Replayed: true`, a stored 4xx (the hymn 404) holds the key, a different body is `idempotency_mismatch`, no 5xx is stored.
5. **`PUT`'s check order** (S "Check order for `PUT`"; F §1.7). A body that fails Pydantic is a 422 first (FastAPI validates before the route runs). Then, in `usecases.archive.replace_service`, inside one transaction: (1) the row `WHERE id AND church_id`, locked `FOR UPDATE` (nothing on SQLite), else 404 with no `details` (the 5a-3 client POSTs then); (2) `If-Match` present, else 422 "If-Match is required.", and readable (`datetime.fromisoformat` after a `W/` prefix and quotes are removed; a naive value is UTC), else 422 "If-Match must be the service's saved_at timestamp."; (3) equal to the stored `saved_at` (to the microsecond), else 409 `conflict` "This service was changed by someone else. Reload it to see their changes." with `details.current_saved_at`; (4) the input (`clean_input`'s label 422, `resolve_hymn_refs`' hymn 404); (5) the write. Two PUTs with the same `If-Match` give one 200 and one 409 (the row lock; Postgres test, T6).
6. **What a save writes** (F §6.2; S acceptance criterion 6): `hymns` as exactly 3 entries in slot order `{slot, title, number, hymn_id, hymnal}` (an empty slot `title: ""` and nulls; `hymn_id` the id as a string or JSON null); `service_date_iso` `YYYY-MM-DD` and `service_date_display` "October 04, 2026"; `liturgy` with only the 8 sections, in `SECTION_ORDER`, non-blank, without Streamlit's error texts (`clean_input`); the cleaned occasion, scriptures, sermon title and picks; `custom_elements` as `[{label, text, insert_after}]`; `hymnal` as sent, or, when null, the church's `effective_hymnal` (`usecases.hymns.resolve_default_hymnal`; null for a church with no hymns); `saved_at` now (it moves on every save); `created_by` the saver on POST and never changed by PUT. A hymn id resolves within the church and the database's title, number and hymnal are stored (F §1.3).
7. **[owner-visible] What is sent is what is stored** (owner answer 4). The server stores the Benediction text and `include_communion` it receives, and injects no church default. In 5a-3 the Save card sends a default-following Benediction as its text, so a saved service keeps the Benediction it had even if the church default changes later; the communion setting likewise.
8. **[owner-visible] Hymn use follows the saved services** (owner answer 6; S `hymn_usage.py`, amended). `hymn_usage.rebuild_usage_for_date(church_id, date_iso, *, session)` deletes the church's rows for that date and inserts the union of the hymns of every service saved for it (stored dates read through `normalize_date_iso`, so a Notion-era date with a time part counts), deduped by `hymn_search.usage_key(title)` (the title alone, slice 3a; the first saved service's number and title are kept). **Saving** rebuilds the saved date; a **PUT that moves a service to another date** rebuilds both dates; **deleting** rebuilds the date the service leaves, from the services still saved. Consequences: a second service on the same date never erases the first one's hymns; rows that no saved service backs (Streamlit's Prepare, imported history) go when their date is rebuilt; **deleting an undated service changes no hymn use** (it has no date to rebuild). A malformed legacy row (hymns not a list, entries that are not objects, a title that is not text) is skipped, never raised on.
9. **One transaction, no lost union, no deadlock** (S Risks; F §7.4). The service write and the rebuild share one `session_scope`; a failure in either rolls back both (SQLite test). On Postgres the rebuild first takes `pg_advisory_xact_lock(hashtextextended('hymn_usage:<church>:<date>', 0))`, so a second save on the same date waits for the first to commit and then sees it; rows go in sorted order with `insert_ignore` (`ON CONFLICT DO NOTHING`); a re-dating PUT rebuilds its two dates in date order. `rebuild_usage_for_date` refuses anything but a real `YYYY-MM-DD` with `ValueError` (a caller's bug), so it can never gather undated services.
10. **Opening a saved service** (`get_service`; S "Normalizing stored data"). Hymns: `slot_map` reads a list whose every entry has a valid `slot` by slot (what 5a-2 writes), else by position 0-2 (Streamlit's compacted lists; a 4th entry ignored). Each filled slot: a stored `hymn_id` that still resolves in the church gives the hymn's current title, number and hymnal with `in_hymnal: true`; otherwise the church's hymns with the same `normalize_title` (and the same number, when the entry has one) are ranked by hymnal (the entry's, then the service's, then the church's effective hymnal, then any other in code order), then the lowest number (nulls last), then the lowest id; no match keeps the snapshot with `hymn_id: null`, `in_hymnal: false`. Liturgy: only the 8 sections, non-blank, trimmed, without Streamlit's error texts. Custom elements: every stored object kept in order, a non-text label or text read as `""`, an unknown or missing `insert_after` read as `"end"` (never dropped, so it survives open then save). `service_date_iso`: `normalize_date_iso` (the first 10 characters when they are a real date, else null). `saved_at`: UTC, `+00:00`.
11. **The list** (`list_services`; S API; F §1.4): a projection with no JSON columns, ordered `NULLIF(service_date_iso, '') DESC NULLS LAST, saved_at DESC, id DESC` (so undated rows come last on SQLite and Postgres alike; Postgres test, T6), `total` the church's count, `created_by` `{id, name}` with the name falling back to the email, null when the author was removed.
12. **Response shapes** (`api/schemas.py`): `DeletedOut {deleted: true}` (6a and 6b reuse it); `AuthorOut {id, name}`; `ArchivedHymn {hymn_id, title, number, hymnal, in_hymnal}`; **`ArchivedHymns {opening, response, closing}`**, each an `ArchivedHymn` or null and always present (an object, not S's dict, so the generated type has three required keys); `ServiceOut` (S's fields, `custom_elements` as `CustomElementIn`, `liturgy` keyed by `SectionKey`, `saved_at` a string); `ServiceSummary` (id, dates, occasion, sermon title, `saved_at`, `created_by`). `ServiceDraft`, `HymnRef`, `SlotHymns`, `SectionKey` are unchanged (F §1.3).
13. **Migration `0005_services_extras`** (S "Data and migrations"; F §3.4, §3.5). `down_revision = "0004_invites_reusable"` (the head on `main`; no other revision is in flight). `services.custom_elements JSON NULL`, `services.hymnal VARCHAR NULL` (no default, no backfill: old rows read as `[]` and null), `CREATE INDEX ix_services_church_date ON services (church_id, service_date_iso)`. Both directions in `op.batch_alter_table`, as `0004` (plain ALTERs on Postgres and in `--sql`; a table copy on SQLite to drop columns). **Lock timeout:** `env.py` already runs `SET LOCAL lock_timeout = '5s'` and `statement_timeout = '60s'` first in the one transaction (F §3.1), so a lock held elsewhere fails the deploy after 5 s and the previous release keeps serving; the revision adds nothing of its own. The plain `CREATE INDEX` blocks writes to `services` (not reads) while it builds, a moment on this table. Tests: up from `0004` with a row kept and a later insert that names neither column (NULLs), down giving back the `0004` table exactly, the exact offline SQL, the drift at the baseline, the head constants (`test_schema_check.py`, `test_api_app.py`). CI's `backend-postgres` job runs `upgrade head`, `alembic check`, `downgrade base`, `upgrade head` on it.
14. **[owner-visible] The owner's production steps** (owner answer 8). `backend/migrations/README.md` gains "Before 0005_services_extras (slice 5a-2)": (1) a `db-backup` run, (2) one read-only query in the Supabase SQL Editor giving `version`, `services`, `undated`, `old_style_hymn_lists`, (3) the `--sql` preview, rendered by the agent without a database and shown to the owner (8 lines: `BEGIN;`, the two timeouts, two `ADD COLUMN`, one `CREATE INDEX`, the version update, `COMMIT;`), (4) after the deploy, a read-only query giving `0005_services_extras`, `2`, `1`, and step 2 again (unchanged). Both queries run in the Postgres tests on seeded rows (T6), and the README's preview must equal the rendered SQL (T6 test). T9 walks the owner through them one at a time. No Streamlit check.
15. **Layout** (F §2.1, §2.2). The archive's queries go in a new `repos/services.py` (session-taking functions; `get_service(…, for_update=)`, `list_page`, `author`, `insert_service`, `update_service`, `delete_service`); Streamlit's `service_archive.py` and `test_service_archive.py` stay as they are (slice 7 deletes them), and so do `record_usage` and its tests. No `test_services_streamlit_compat.py`: Streamlit is retired (owner answers 6, 8), and the data shape it relied on is still written (clarification 6).
16. **Frontend: the generated files only** (clarification 1). T5 regenerates `openapi.json` and `schema.d.ts`; typecheck and lint stay clean, and the suite stays at 618 in 81.
17. **Reviewer notes are not saved** (owner answer 9): `ServiceDraft` has no field for them and refuses unknown fields (422), so 5a-3 cannot send them by mistake.
18. **Reverting 5a-2** keeps the schema: the revert PR restores the revision file and the model's columns and index from the merge commit, so Railway's `alembic upgrade head` still finds the database at head (code without `0005` would fail its pre-deploy on a database at `0005`). Production is never downgraded for it (README "Reverting 5a-2"; T9 Step R).
19. **Docs** (T7): S gains "Amendment 2026-10-02: 5a-2 as planned"; `docs/manual-verification.md` → "Slice 5a" gains items 9-11 for 5a-2. The runbook record is T9's.

### Risks
- **A lock on `services` at deploy time.** A long-running query holding a conflicting lock would make `ALTER TABLE` wait; `lock_timeout` turns that into a failed deploy after 5 s with the previous release still serving. T9 Step 5 has the owner check the deploy and `/health/ready` (which answers 503 `schema_behind` in production if the schema were behind).
- **Hymn-use rows that no saved service backs** are replaced when their date is rebuilt (clarification 8). With Streamlit retired, nothing writes such rows any more; existing ones (Prepare, imported history) stay until a service on their date is saved or deleted.
- **Concurrency on SQLite** (local dev) is not covered: no row lock, no advisory lock. The Postgres tests cover production's behavior (T6).
- **No UI exercises the routes until 5a-3.** The API tests are the check; the owner's phone check after the merge is a regression check only (T9).

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/migrations/versions/0005_services_extras.py` | the two columns and the index | T1 |
| `backend/tests/test_usage_rebuild.py` | `rebuild_usage_for_date` on SQLite | T3 |
| `backend/repos/services.py` | the archive's queries | T4 |
| `backend/tests/test_usecase_archive.py` | create, replace, get, list, delete, hymn use | T4 |
| `backend/api/routes/services.py` (+ `backend/tests/test_api_services.py`) | the five routes | T5 |
| `backend/tests/test_services_postgres.py` | concurrency, row lock, order, the owner's queries | T6 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/db/models.py` | `Service.custom_elements`, `Service.hymnal`, `ix_services_church_date` | T1 |
| `backend/migrations/README.md` | head, the `0005` row (T1); "Before 0005_services_extras" (T6) | T1, T6 |
| `backend/tests/test_migrations.py` | the `0005` tests (T1); the README preview pin (T6) | T1, T6 |
| `backend/tests/test_schema_check.py`, `backend/tests/test_api_app.py` | head `0005_services_extras`; the baseline drift | T1 |
| `backend/api/idempotency.py` (+ `backend/tests/test_idempotency.py`) | `church_id` in the store key | T2 |
| `backend/service_output.py` (+ `backend/tests/test_service_output.py`) | stored dates and hymns | T3 |
| `backend/hymn_usage.py` | `rebuild_usage_for_date` | T3 |
| `backend/repos/hymns.py` | `find_hymns_by_titles` | T4 |
| `backend/usecases/archive.py` | saving, opening, listing, deleting | T4 |
| `backend/tests/test_no_streamlit_in_core.py` | `repos.services`, `hymn_usage` | T4 |
| `backend/api/schemas.py`, `backend/api/main.py` | the response models; the router | T5 |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated | T5 |
| `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`, `docs/manual-verification.md` | the amendment; items 9-11 | T7 |
| `docs/ops-runbook.md` | "### Slice 5a-2 record" (the records PR, after the merge) | T9 |

**Counts in the PR:** 8 created (this plan and the 7 above), 19 modified (all but the runbook above): 27 paths, plus `docs/ops-runbook.md` if the runbook commit `2cd4b79` is not on `main` yet when the PR opens (T8 Step 3). **Untouched:** `service_archive.py`, `worship_service.py`, `usecases/documents.py`, `api/routes/documents.py`, `liturgy_config.py`, `migrations/env.py`, every frontend source file, `app.py`, Streamlit.

**Task order and review batch:** T1 → T7, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T8 verifies and opens the draft PR on the owner's yes; T9 takes the owner through the backup, the counts and the preview, merges on the owner's yes, checks production, and writes the record.

---

