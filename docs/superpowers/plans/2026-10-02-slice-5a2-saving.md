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

### Task 1: Migration `0005_services_extras` (owner answer 8; S "Data and migrations"; F §3.1, §3.4, §3.5; clarification 13)

**Files:**
- Create: `backend/migrations/versions/0005_services_extras.py`
- Modify: `backend/db/models.py`, `backend/migrations/README.md`, `backend/tests/test_migrations.py`, `backend/tests/test_schema_check.py`, `backend/tests/test_api_app.py`

- [ ] **Step 1 (agent): Write the failing tests**

**Append to `backend/tests/test_migrations.py`:**

````python


# --- Slice 5a-2: 0005_services_extras (F §3.4, §3.5; 5a spec "Data and migrations") ---

# The services columns before 0005, i.e. everything a pre-5a-2 insert names
# (frozen Streamlit's ORM, migrate_to_db.py): never custom_elements or hymnal.
_legacy_services = sa.table(
    "services",
    sa.column("id", sa.Uuid()),
    sa.column("church_id", sa.Uuid()),
    sa.column("created_by", sa.Uuid()),
    sa.column("service_date_iso", sa.String()),
    sa.column("service_date_display", sa.String()),
    sa.column("occasion", sa.String()),
    sa.column("scriptures", sa.JSON()),
    sa.column("hymns", sa.JSON()),
    sa.column("liturgy", sa.JSON()),
    sa.column("sermon_title", sa.String()),
    sa.column("selected_ot_ref", sa.String()),
    sa.column("selected_nt_ref", sa.String()),
    sa.column("include_communion", sa.Boolean()),
    sa.column("saved_at", sa.DateTime(timezone=True)),
)

# What `alembic upgrade 0004_invites_reusable:0005_services_extras --sql` prints
# on Postgres, comments and blank lines left out: the preview the owner reads
# before the merge (5a-2 plan, owner answer 8; backend/migrations/README.md).
PREVIEW_0005 = [
    "BEGIN;",
    "SET LOCAL lock_timeout = '5s';",
    "SET LOCAL statement_timeout = '60s';",
    "ALTER TABLE services ADD COLUMN custom_elements JSON;",
    "ALTER TABLE services ADD COLUMN hymnal VARCHAR;",
    "CREATE INDEX ix_services_church_date ON services (church_id, service_date_iso);",
    "UPDATE alembic_version SET version_num='0005_services_extras' "
    "WHERE alembic_version.version_num = '0004_invites_reusable';",
    "COMMIT;",
]


def _insert_legacy_service(conn, church_id, user_id, *, date_iso="2026-09-27") -> uuid.UUID:
    service_id = uuid.uuid4()
    conn.execute(_legacy_services.insert().values(
        id=service_id, church_id=church_id, created_by=user_id, service_date_iso=date_iso,
        service_date_display="September 27, 2026", occasion="Pentecost 17", scriptures=["Psalm 25"],
        hymns=[{"title": "Holy, Holy, Holy", "number": 138}], liturgy={"call_to_worship": "Come."},
        sermon_title="", selected_ot_ref="", selected_nt_ref="", include_communion=False, saved_at=T9_NOW))
    return service_id


def _services_shape(conn) -> dict:
    insp = sa.inspect(conn)
    return {
        "columns": [(c["name"], str(c["type"]), c["nullable"]) for c in insp.get_columns("services")],
        "pk": insp.get_pk_constraint("services")["constrained_columns"],
        "fks": sorted((fk["name"] or "", tuple(fk["constrained_columns"]), fk["referred_table"],
                       fk["options"].get("ondelete")) for fk in insp.get_foreign_keys("services")),
        "indexes": sorted((i["name"], tuple(i["column_names"]), bool(i["unique"]))
                          for i in insp.get_indexes("services")),
    }


def test_0005_adds_two_nullable_columns_and_the_date_index_and_keeps_rows(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0004_invites_reusable")
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
            rows = conn.execute(sa.text(
                "SELECT id, occasion, custom_elements, hymnal FROM services ORDER BY service_date_iso")).all()
    finally:
        engine.dispose()
    assert at_head["columns"] == before["columns"] + [
        ("custom_elements", "JSON", True), ("hymnal", "VARCHAR", True)]
    assert at_head["indexes"] == sorted(before["indexes"] + [
        ("ix_services_church_date", ("church_id", "service_date_iso"), False)])
    assert (at_head["pk"], at_head["fks"]) == (before["pk"], before["fks"])
    # The row from before keeps its data; an insert that names neither column gets NULLs.
    assert [(uuid.UUID(str(r.id)), r.occasion, r.custom_elements, r.hymnal) for r in rows] == [
        (kept, "Pentecost 17", None, None), (inserted, "Pentecost 17", None, None)]


def test_0005_downgrade_gives_back_the_0004_services_table(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0004_invites_reusable")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            before = _services_shape(conn)
        _alembic(sqlite_url, "upgrade", "head")
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            _insert_legacy_service(conn, church_id, user_id)
            conn.execute(sa.text("UPDATE services SET custom_elements = '[]', hymnal = 'GG2013'"))
        _alembic(sqlite_url, "downgrade", "0004_invites_reusable")
        with engine.connect() as conn:
            after = _services_shape(conn)
            occasions = conn.execute(sa.text("SELECT occasion FROM services")).scalars().all()
            version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()
    assert after == before          # the table copy kept every other column, key and index
    assert occasions == ["Pentecost 17"]
    assert version == "0004_invites_reusable"


def test_offline_sql_for_0005_is_two_column_adds_and_one_index_under_the_timeouts():
    cfg = alembic_config(url="postgresql://preview@localhost:1/preview", configure_logger=False)
    cfg.output_buffer = buffer = io.StringIO()
    command.upgrade(cfg, "0004_invites_reusable:0005_services_extras", sql=True)
    lines = [line for line in buffer.getvalue().splitlines() if line.strip() and not line.startswith("--")]
    assert lines == PREVIEW_0005
````

The head moves to `0005_services_extras`, and a database stamped at the baseline now also lacks `0005`'s three changes:

**In `backend/tests/test_schema_check.py`, replace:**

````python
EXPECTED_HEAD = "0004_invites_reusable"
# What a stamped production at 0001_baseline lacks (runbook step 6, sorted).
BASELINE_DRIFT = [
    "add_column invites.accepted_by",
    "add_column invites.reusable",
    "add_fk fk_invites_accepted_by_users",
]
````

**with:**

````python
EXPECTED_HEAD = "0005_services_extras"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
# 0004's invites changes, then 0005's services changes (slice 5a-2).
BASELINE_DRIFT = [
    "add_column invites.accepted_by",
    "add_column invites.reusable",
    "add_column services.custom_elements",
    "add_column services.hymnal",
    "add_fk fk_invites_accepted_by_users",
    "add_index ix_services_church_date",
]
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_head_is_0004_invites_reusable():
````

**with:**

````python
def test_head_is_0005_services_extras():
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_changes(tmp_path):
````

**with:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_and_0005_changes(tmp_path):
````

**In `backend/tests/test_api_app.py`, replace:**

````python
SCHEMA_HEAD = "0004_invites_reusable"
````

**with:**

````python
SCHEMA_HEAD = "0005_services_extras"
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py 2>&1 | tail -1
```

**Expected:** `14 failed, 52 passed, 4 skipped in <t>s`: the three `0005` tests (the head is still `0004`, so the columns never appear, `UPDATE services SET custom_elements` has no column, and `0004_invites_reusable:0005_services_extras` names an unknown revision), nine head and drift tests in `test_schema_check.py`, two startup tests in `test_api_app.py`.

- [ ] **Step 3 (agent): The revision, the model, the README**

**Create `backend/migrations/versions/0005_services_extras.py`:**

````python
"""Services: custom elements, hymnal and the date index (F §3.5; slice 5a spec, "Data and migrations"; slice 5a-2)

Expand-only (F §3.4): two nullable columns and one index. No backfill, no
server default, no NOT NULL; existing rows keep NULL, which the API reads as
no custom elements ([]) and no hymnal (null).
- services.custom_elements JSON NULL: the custom elements a saved service
  prints, [{label, text, insert_after}].
- services.hymnal VARCHAR NULL: the hymnal the service's hymns came from.
- ix_services_church_date on services (church_id, service_date_iso): the
  archive list's order (newest service date first) and the hymn-use rebuild
  for one date.

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and statement_timeout
'60s') first, so a lock held elsewhere fails the deploy after 5 s instead of
queueing every query behind it; the previous release keeps serving. Adding a
nullable column without a default changes only the catalog; the plain
CREATE INDEX blocks writes to services (not reads) while it builds, a moment
on a table this size. Both directions use op.batch_alter_table, as 0004 does:
plain ALTER TABLE on Postgres and in --sql, a table copy on SQLite when a
column is dropped.

Revision ID: 0005_services_extras
Revises: 0004_invites_reusable
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_services_extras"
down_revision = "0004_invites_reusable"
branch_labels = None
depends_on = None

INDEX = "ix_services_church_date"


def upgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.add_column(sa.Column("custom_elements", sa.JSON(), nullable=True))
        batch.add_column(sa.Column("hymnal", sa.String(), nullable=True))
    op.create_index(INDEX, "services", ["church_id", "service_date_iso"])


def downgrade() -> None:
    op.drop_index(INDEX, table_name="services")
    with op.batch_alter_table("services") as batch:
        batch.drop_column("hymnal")
        batch.drop_column("custom_elements")
````

**In `backend/db/models.py`, replace:**

````python
    include_communion = Column(Boolean, nullable=False, default=False)
    saved_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_services_church_saved_at", "church_id", "saved_at"),
    )

````

**with:**

````python
    include_communion = Column(Boolean, nullable=False, default=False)
    saved_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    # Revision 0005_services_extras (slice 5a-2). NULL means "not recorded": a
    # service saved before 5a-2 (by Streamlit) has neither, and the API reads
    # them as no custom elements ([]) and no hymnal (null).
    custom_elements = Column(JSON, nullable=True)   # [{label, text, insert_after}]
    hymnal = Column(String, nullable=True)          # the hymnal the hymns came from

    __table_args__ = (
        Index("ix_services_church_saved_at", "church_id", "saved_at"),
        # The archive list's order and the hymn-use rebuild for one date (5a-2).
        Index("ix_services_church_date", "church_id", "service_date_iso"),
    )

````

**In `backend/migrations/README.md`, replace:**

````markdown
  `NNNN_short_slug.py`. Head is `0004_invites_reusable`.
````

**with:**

````markdown
  `NNNN_short_slug.py`. Head is `0005_services_extras`.
````

**In `backend/migrations/README.md`, replace:**

````markdown
| `0004_invites_reusable` | `invites.reusable` (NOT NULL, default false; existing code-only invites become reusable) and `invites.accepted_by` with the FK `fk_invites_accepted_by_users` (`ON DELETE SET NULL`). |

````

**with:**

````markdown
| `0004_invites_reusable` | `invites.reusable` (NOT NULL, default false; existing code-only invites become reusable) and `invites.accepted_by` with the FK `fk_invites_accepted_by_users` (`ON DELETE SET NULL`). |
| `0005_services_extras` | Slice 5a-2: `services.custom_elements` (JSON) and `services.hymnal` (VARCHAR), both nullable with no default and no backfill, and the index `ix_services_church_date` on `services (church_id, service_date_iso)`. Before it reaches production: "Before 0005_services_extras" below. |

````

- [ ] **Step 4 (agent): Run the files, the offline SQL and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_models.py 2>&1 | tail -1
(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0004_invites_reusable:0005_services_extras --sql 2>/dev/null | grep -v -e '^--' -e '^$' | wc -l)
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `70 passed, 4 skipped in <t>s`; `8` (the eight preview lines of clarification 14); `1266 passed, 11 skipped in <t>s`. With a local Postgres, also: `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `11 passed, 1266 deselected` (the alembic cycle on Postgres is CI's).

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/migrations/versions/0005_services_extras.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py
git commit -q -m "Migration 0005_services_extras: services.custom_elements, services.hymnal and ix_services_church_date (5a-2)" -m "Expand-only (F 3.4): two nullable columns with no default and no
backfill, and the index (church_id, service_date_iso) for the archive
list and the hymn-use rebuild. Batch mode both ways, as 0004; env.py's
SET LOCAL lock_timeout = '5s' runs first on Postgres. Tests: up from 0004
keeping rows, an insert without the columns, down to the 0004 table, the
exact offline SQL the owner will read (owner answer 8); the head and the
baseline drift in test_schema_check and test_api_app." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 1: backend **1266 passed, 11 skipped**; frontend **618 in 81**.

### Task 2: The idempotency key is scoped to the church (F §1.6 church-scope amendment 2026-09-28; clarification 4)

**Files:**
- Modify: `backend/api/idempotency.py`, `backend/tests/test_idempotency.py`

- [ ] **Step 1 (agent): Write the failing test**

**In `backend/tests/test_idempotency.py`, replace:**

````python
def test_concurrent_same_key_requests_run_the_call_once():
````

**with:**

````python
def test_keys_are_scoped_per_church():
    """F §1.6 church-scope amendment (2026-09-28): a church-scoped route passes its
    church, so the same user and key in another church runs the call again."""
    church_a, church_b = uuid.UUID(int=10), uuid.UUID(int=11)
    store, calls = IdempotencyStore(), []
    first = _direct(store, calls, church_id=church_a)
    other_church = _direct(store, calls, church_id=church_b)
    user_scoped = _direct(store, calls)                                # church_id None: POST /churches
    replay = _direct(store, calls, church_id=church_a)
    assert len(calls) == 3
    assert REPLAYED_HEADER.lower() not in first.headers
    assert REPLAYED_HEADER.lower() not in other_church.headers
    assert REPLAYED_HEADER.lower() not in user_scoped.headers
    assert replay.headers[REPLAYED_HEADER] == "true"
    assert len(store) == 3


def test_concurrent_same_key_requests_run_the_call_once():
````

- [ ] **Step 2 (agent): Run it and see it fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_idempotency.py 2>&1 | tail -1
```

**Expected:** `1 failed, 15 passed in <t>s` (`run_idempotent() got an unexpected keyword argument 'church_id'`).

- [ ] **Step 3 (agent): `church_id` joins the store key**

**In `backend/api/idempotency.py`, replace:**

````python
The store is in memory, keyed by (user_id, method, route template, key), with a
15-minute TTL and at most 10 000 entries. That is enough for one uvicorn
worker; if --workers ever exceeds 1, move it to a Postgres table first (F §1.6).
````

**with:**

````python
The store is in memory, keyed by (user_id, church_id, method, route template,
key), with a 15-minute TTL and at most 10 000 entries. church_id is None for a
user-scoped route (POST /churches); a church-scoped route passes the resolved
church (5a-2's POST /services), so a key sent in two churches never replays
one church's answer in the other (F §1.6, church-scope amendment 2026-09-28).
That is enough for one uvicorn worker; if --workers ever exceeds 1, move it to
a Postgres table first (F §1.6).
````

**In `backend/api/idempotency.py`, replace:**

````python
_Key = tuple[uuid.UUID, str, str, uuid.UUID]
````

**with:**

````python
_Key = tuple[uuid.UUID, Optional[uuid.UUID], str, str, uuid.UUID]
````

**In `backend/api/idempotency.py`, replace:**

````python
    method: str = "POST",
    store: Optional[IdempotencyStore] = None,
) -> Response:
    """Run `call` once per (user, method, route, key) and replay its response.

````

**with:**

````python
    method: str = "POST",
    church_id: Optional[uuid.UUID] = None,
    store: Optional[IdempotencyStore] = None,
) -> Response:
    """Run `call` once per (user, church, method, route, key) and replay its response.

````

**In `backend/api/idempotency.py`, replace:**

````python
    `status_code` the success status. Blocks
````

**with:**

````python
    `status_code` the success status, `church_id` the resolved church of a
    church-scoped route (None: user-scoped). Blocks
````

**In `backend/api/idempotency.py`, replace:**

````python
    scope = (user_id, method.upper(), route, key)
````

**with:**

````python
    scope = (user_id, church_id, method.upper(), route, key)
````

- [ ] **Step 4 (agent): Run the files and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_idempotency.py backend/tests/test_api_churches.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `34 passed in <t>s`; `1267 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/api/idempotency.py backend/tests/test_idempotency.py
git commit -q -m "Idempotency: scope stored keys by church (F 1.6 amendment 2026-09-28; 5a-2)" -m "run_idempotent takes church_id and keys its store by (user, church,
method, route, key), so a key sent in two churches never replays one
church's answer in the other. POST /churches passes none (user-scoped);
5a-2's POST /services passes the active church." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 2: backend **1267 passed, 11 skipped**; frontend **618 in 81**.

### Task 3: Stored dates and hymns, and the hymn-use rebuild (owner answer 6; S `service_output.py`, `hymn_usage.py`; F §6.2, §7.4; clarifications 6, 8, 9)

**Files:**
- Create: `backend/tests/test_usage_rebuild.py`
- Modify: `backend/service_output.py`, `backend/tests/test_service_output.py`, `backend/hymn_usage.py`

- [ ] **Step 1 (agent): Write the failing tests**

**Append to `backend/tests/test_service_output.py`:**

````python


# --- slice 5a-2: stored dates and hymns (5a spec, "Normalizing stored data") ---

def test_normalize_date_iso_keeps_a_real_date_and_recovers_a_time_part():
    assert so.normalize_date_iso("2026-10-04") == "2026-10-04"
    assert so.normalize_date_iso("2026-10-04T00:00:00.000Z") == "2026-10-04"     # Notion-era
    for raw in ("", None, "October 4", "2026-02-30", "2026-13-01", "26-10-04", "２０２６-10-04", 20261004, " 2026-10-04"):
        assert so.normalize_date_iso(raw) is None, raw


def test_coerce_number():
    assert [so.coerce_number(v) for v in (138, "138", " 12 ", 7.0, 0)] == [138, 138, 12, 7, 0]
    assert [so.coerce_number(v) for v in (None, True, "12a", "", 7.5, "²", [1])] == [None] * 7


def test_stored_hymn_entries_never_raise_and_keep_every_entry():
    assert so.stored_hymn_entries("Holy") == [] and so.stored_hymn_entries({"title": "x"}) == []
    assert so.stored_hymn_entries(None) == []
    entries = so.stored_hymn_entries([
        None, 42, {"title": 7}, {"title": "  "},
        {"title": " Holy, Holy, Holy ", "number": "138", "slot": "closing", "hymn_id": "abc", "hymnal": "GG2013"},
        {"title": "Fourth", "number": None, "slot": "bogus", "hymn_id": 5, "hymnal": " "},
    ])
    assert entries[:4] == [None, None, None, None]
    assert entries[4] == so.StoredHymn("closing", "Holy, Holy, Holy", 138, "abc", "GG2013")
    assert entries[5] == so.StoredHymn(None, "Fourth", None, None, None)


def test_slot_map_by_slot_or_by_position():
    react = so.stored_hymns({"opening": None, "response": so.ResolvedHymn("B", 2), "closing": so.ResolvedHymn("C", None)})
    by_slot = so.slot_map(react)
    assert by_slot["opening"] is None
    assert (by_slot["response"].title, by_slot["closing"].title) == ("B", "C")
    # Streamlit's compacted list: by position, a 4th entry ignored.
    legacy = so.slot_map([{"title": "A", "number": 1}, {"title": "B"}, {"title": "C"}, {"title": "D"}])
    assert [legacy[s].title for s in so.SLOTS] == ["A", "B", "C"]
    # One entry without a slot makes the whole list positional.
    mixed = so.slot_map([{"slot": "closing", "title": "C"}, {"title": "A"}])
    assert (mixed["opening"].title, mixed["response"].title, mixed["closing"]) == ("C", "A", None)
    assert so.slot_map([]) == so.slot_map("x") == {"opening": None, "response": None, "closing": None}


def test_stored_hymns_writes_three_slot_entries_never_null_titles():
    import uuid

    hymn_id = "3f0c1b9e-0000-4000-8000-000000000001"
    assert so.stored_hymns({"opening": so.ResolvedHymn("Holy, Holy, Holy", 138, uuid.UUID(hymn_id), "GG2013"),
                            "closing": so.ResolvedHymn("Old Favorite", 12, None, "PH1990")}) == [
        {"slot": "opening", "title": "Holy, Holy, Holy", "number": 138, "hymn_id": hymn_id, "hymnal": "GG2013"},
        {"slot": "response", "title": "", "number": None, "hymn_id": None, "hymnal": None},
        {"slot": "closing", "title": "Old Favorite", "number": 12, "hymn_id": None, "hymnal": "PH1990"},
    ]
````

**Create `backend/tests/test_usage_rebuild.py`:**

````python
"""hymn_usage.rebuild_usage_for_date: a date's hymn use is the union of the
services saved for it (slice 5a spec, hymn_usage.py; owner answer 6,
2026-10-01; F §7.4). SQLite here; the concurrent case is in
test_services_postgres.py."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from db import session_scope
from db.models import HymnUsage, Service
from hymn_usage import rebuild_usage_for_date, record_usage

D = "2026-10-04"
T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def church(make_church):
    return make_church(name="Grace")


def add_service(church_id, hymns, *, date_iso=D, minutes=0) -> uuid.UUID:
    """A services row as any writer left it (5a-2's 3 slots, Streamlit's compacted list, or junk)."""
    with session_scope() as s:
        row = Service(church_id=church_id, service_date_iso=date_iso, service_date_display="October 04, 2026",
                      occasion="", scriptures=[], hymns=hymns, liturgy={},
                      saved_at=T0 + timedelta(minutes=minutes))
        s.add(row)
        s.flush()
        return row.id


def usage(church_id, date_iso=D) -> list[tuple]:
    with session_scope() as s:
        return sorted(s.execute(select(HymnUsage.hymn_number, HymnUsage.hymn_title)
                                .where(HymnUsage.church_id == church_id, HymnUsage.date_iso == date_iso)).all(),
                      key=lambda r: (r[1], r[0] or 0))


def rebuild(church_id, date_iso=D) -> int:
    with session_scope() as s:
        return rebuild_usage_for_date(church_id, date_iso, session=s)


def slots(opening=None, response=None, closing=None) -> list[dict]:
    def entry(slot, hymn):
        title, number = hymn if hymn else ("", None)
        return {"slot": slot, "title": title, "number": number, "hymn_id": None, "hymnal": None}
    return [entry("opening", opening), entry("response", response), entry("closing", closing)]


def test_a_date_s_rows_are_the_union_of_its_saved_services(church):
    add_service(church, slots(("Holy, Holy, Holy", 138), None, ("Be Thou My Vision", 450)))
    add_service(church, slots(("Amazing Grace", 649)), minutes=5)      # an early service, same date
    assert rebuild(church) == 3
    assert usage(church) == [(649, "Amazing Grace"), (450, "Be Thou My Vision"), (138, "Holy, Holy, Holy")]


def test_rows_nothing_saved_backs_are_replaced(church):
    # Frozen Streamlit's Prepare (record_usage) and imported history wrote rows no saved service backs.
    assert record_usage(church, D, [{"title": "Prepared Only", "number": 1}])
    add_service(church, slots(("Holy, Holy, Holy", 138)))
    rebuild(church)
    assert usage(church) == [(138, "Holy, Holy, Holy")]


def test_a_date_with_no_service_left_has_no_rows(church):
    record_usage(church, D, [{"title": "Holy, Holy, Holy", "number": 138}])
    assert rebuild(church) == 0
    assert usage(church) == []


def test_titles_dedupe_by_the_usage_key_and_keep_the_first_saved(church):
    # usage_key is the title alone, punctuation, case and spacing ignored (3a amendment):
    # the same hymn from two hymnals, or typed twice, is one row.
    add_service(church, slots(("Holy, Holy, Holy", 138), ("Be Thou My Vision", None)))
    add_service(church, slots(("holy holy  holy", 4), ("Be Thou My Vision", None), ("Be Thou my vision!", 82)),
                minutes=5)
    assert rebuild(church) == 2
    assert usage(church) == [(None, "Be Thou My Vision"), (138, "Holy, Holy, Holy")]


def test_malformed_legacy_rows_are_skipped_not_raised(church):
    for junk in ("Holy", {"title": "x"}, [None, 42, {"title": 7}, {"title": "  "}], None):
        add_service(church, junk)
    # Streamlit's compacted list, a 4th entry included, and a Notion-era date with a time part.
    add_service(church, [{"title": "A", "number": 1}, {"title": "B"}, {"title": "C"}, {"title": "D", "number": "4"}],
                date_iso="2026-10-04T00:00:00.000Z")
    assert rebuild(church) == 4
    assert usage(church) == [(1, "A"), (None, "B"), (None, "C"), (4, "D")]


def test_only_that_date_and_that_church(church, make_church):
    other = make_church(name="Hope")
    add_service(church, slots(("Holy, Holy, Holy", 138)))
    add_service(church, slots(("Next Week", 2)), date_iso="2026-10-11")
    add_service(other, slots(("Their Hymn", 3)))
    record_usage(church, "2026-10-11", [{"title": "Kept", "number": 9}])
    record_usage(other, D, [{"title": "Their Prepared", "number": 8}])
    rebuild(church)
    assert usage(church) == [(138, "Holy, Holy, Holy")]
    assert usage(church, "2026-10-11") == [(9, "Kept")]                 # not rebuilt
    assert usage(other) == [(8, "Their Prepared")]                      # another church


@pytest.mark.parametrize("bad", [None, "", "2026-13-01", "2026-10-04T00:00:00", "October 04, 2026"])
def test_only_a_yyyy_mm_dd_date_is_accepted(church, bad):
    record_usage(church, D, [{"title": "Holy, Holy, Holy", "number": 138}])
    with pytest.raises(ValueError):
        rebuild(church, bad)
    assert usage(church) == [(138, "Holy, Holy, Holy")]
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_service_output.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_usage_rebuild.py 2>&1 | grep -E "^E +ImportError|error"
```

**Expected:** `5 failed, 6 passed in <t>s` (`AttributeError`: `service_output` has no `normalize_date_iso`, `coerce_number`, `StoredHymn`, `slot_map`, `stored_hymns`); then `E   ImportError: cannot import name 'rebuild_usage_for_date' from 'hymn_usage' (…)`, `!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!` and `1 error in <t>s`.

- [ ] **Step 3 (agent): The readers, the writer and the rebuild**

**In `backend/service_output.py`, replace:**

````python
import datetime
from collections.abc import Mapping
````

**with:**

````python
import datetime
import re
from collections.abc import Mapping
````

**In `backend/service_output.py`, replace:**

````python
- ResolvedHymn, CustomElement, ResolvedService and render_docx (Task 2): a
  service whose hymns are resolved, rendered by worship_service.build_docx.
"""
````

**with:**

````python
- ResolvedHymn, CustomElement, ResolvedService and render_docx (Task 2): a
  service whose hymns are resolved, rendered by worship_service.build_docx.
- normalize_date_iso, coerce_number, StoredHymn, stored_hymn_entries,
  slot_map and stored_hymns (slice 5a-2): reading a saved service's stored
  date and hymns tolerantly, and the 3-slot list a save writes (F §6.2).
"""
````

**Append to `backend/service_output.py`:**

````python


# --- slice 5a-2: saved services (5a spec, "service_output.py" and "Normalizing stored data") ---

_ISO_PREFIX = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def normalize_date_iso(raw: object) -> Optional[str]:
    """A stored services.service_date_iso as YYYY-MM-DD, or None: the first 10
    characters when they are a real calendar date ("2026-10-04" and the
    Notion-era "2026-10-04T00:00:00.000Z" both give "2026-10-04"); None for
    NULL, "", "October 4", "2026-02-30" and anything else. GET /services,
    GET /services/{id} and the hymn-use rebuild all read dates through it."""
    if not isinstance(raw, str) or not _ISO_PREFIX.fullmatch(raw[:10]):
        return None
    try:
        datetime.date.fromisoformat(raw[:10])
    except ValueError:
        return None
    return raw[:10]


def coerce_number(value: object) -> Optional[int]:
    """A stored hymn number as an int, or None: an int (not a bool), a string of
    ASCII digits, or a whole float; anything else is None. Never raises."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isascii() and value.strip().isdigit():
        return int(value.strip())
    return None


@dataclass(frozen=True)
class StoredHymn:
    """One entry of a stored services.hymns list, read tolerantly."""
    slot: Optional[str]                        # one of SLOTS, else None
    title: str                                 # stripped, never blank
    number: Optional[int]
    hymn_id: Optional[str]                     # as stored (a string), else None
    hymnal: Optional[str]


def _stored_hymn(entry: object) -> Optional[StoredHymn]:
    if not isinstance(entry, dict):
        return None
    title = entry.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    slot = entry.get("slot")
    hymn_id = entry.get("hymn_id")
    hymnal = entry.get("hymnal")
    return StoredHymn(slot=slot if slot in SLOTS else None, title=title.strip(),
                      number=coerce_number(entry.get("number")),
                      hymn_id=hymn_id if isinstance(hymn_id, str) and hymn_id.strip() else None,
                      hymnal=hymnal.strip() if isinstance(hymnal, str) and hymnal.strip() else None)


def stored_hymn_entries(raw: object) -> list[Optional[StoredHymn]]:
    """Every entry of a stored services.hymns value, in order, a 4th and later
    entry included (the hymn-use rebuild counts them). A value that is not a
    list gives []; a non-dict entry, a title that is not a string and a blank
    title give None. Never raises: one malformed legacy row cannot fail a save."""
    if not isinstance(raw, list):
        return []
    return [_stored_hymn(entry) for entry in raw]


def slot_map(raw: object) -> dict[str, Optional[StoredHymn]]:
    """The stored hymns by slot (F §4.6 step 3). When the value is a non-empty
    list whose every entry is a dict with a valid "slot" (what 5a-2 writes),
    each entry goes to its slot (the first one wins); otherwise (Streamlit's
    compacted [{title, number}] lists) entries 0-2 map to opening, response
    and closing, and a 4th entry is ignored."""
    entries = stored_hymn_entries(raw)
    slotted = bool(entries) and all(isinstance(e, dict) and e.get("slot") in SLOTS for e in raw)
    if slotted:
        result: dict[str, Optional[StoredHymn]] = {slot: None for slot in SLOTS}
        for entry, parsed in zip(raw, entries):
            if parsed is not None and result[entry["slot"]] is None:
                result[entry["slot"]] = parsed
        return result
    return {slot: entries[i] if i < len(entries) else None for i, slot in enumerate(SLOTS)}


def stored_hymns(hymns: Mapping[str, Optional[ResolvedHymn]]) -> list[dict]:
    """What 5a-2 writes to services.hymns: exactly 3 entries in slot order,
    {slot, title, number, hymn_id, hymnal}; an empty slot has title "" and
    nulls; hymn_id is the id as a string, or JSON null (F §6.2)."""
    out = []
    for slot in SLOTS:
        hymn = hymns.get(slot)
        if hymn is None:
            out.append({"slot": slot, "title": "", "number": None, "hymn_id": None, "hymnal": None})
        else:
            out.append({"slot": slot, "title": hymn.title, "number": hymn.number,
                        "hymn_id": None if hymn.hymn_id is None else str(hymn.hymn_id), "hymnal": hymn.hymnal})
    return out
````

**In `backend/hymn_usage.py`, replace:**

````python
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import HymnUsage
from hymn_search import usage_key

````

**with:**

````python
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import HymnUsage, Service
from db.upsert import insert_ignore
from hymn_search import usage_key
from service_output import normalize_date_iso, stored_hymn_entries

````

**In `backend/hymn_usage.py`, replace:**

````python
Drives the "exclude hymns used in the last 12 weeks" filter. All reads and
writes are scoped to a validated `church_id`; writes are idempotent per
(church_id, date_iso, hymn_number, hymn_title) so re-preparing a bulletin
never inflates the exclusion set.
"""
````

**with:**

````python
Drives the "exclude hymns used in the last 12 weeks" filter. All reads and
writes are scoped to a validated `church_id`; writes are idempotent per
(church_id, date_iso, hymn_number, hymn_title) so re-preparing a bulletin
never inflates the exclusion set.

Slice 5a-2: rebuild_usage_for_date replaces one date's rows with the hymns
of every service saved for that date; saving, re-dating and deleting a
service call it in their own transaction (owner answers 6, 2026-10-01).
record_usage stays for the frozen Streamlit branch's tests (slice 7).
"""
````

**Append to `backend/hymn_usage.py`:**

````python


# --- slice 5a-2: hymn use follows the saved services (owner answer 6, 2026-10-01) ---------

def rebuild_usage_for_date(church_id, date_iso: str, *, session: Session) -> int:
    """Replace the church's hymn_usage rows for `date_iso` with the hymns of
    every service saved for that date (their union), in the caller's
    transaction; return the number of rows written.

    Saving a service rebuilds its date, and deleting one (or moving it to
    another date) rebuilds the date it leaves, so a date's rows always equal
    what the archive holds for it: a second service on the same date keeps
    its hymns, and rows nothing saved backs (frozen Streamlit's Prepare,
    imported history) go when that date is rebuilt (owner answer 6: Streamlit
    is retired). Hymns are deduped by hymn_search.usage_key (the title alone,
    as the 12-week window reads them); the first saved service's number and
    title are kept. Stored rows are read with service_output's tolerant
    parser, so a malformed legacy row is skipped, never raised on.

    `date_iso` must be a YYYY-MM-DD date (ValueError otherwise: a caller's
    bug), so the select can never gather undated services. On Postgres a
    transaction-level advisory lock per (church, date) makes a second save on
    the same date wait for the first to commit; its select then sees the
    first service, so the union is complete, and the rows go in sorted order,
    so two rebuilds never deadlock.
    """
    if not isinstance(date_iso, str) or normalize_date_iso(date_iso) != date_iso:
        raise ValueError(f"rebuild_usage_for_date needs a YYYY-MM-DD date, not {date_iso!r}")
    cid = as_uuid(church_id)
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                        {"lock_key": f"hymn_usage:{cid}:{date_iso}"})
    rows = session.execute(
        select(Service.service_date_iso, Service.hymns)
        .where(Service.church_id == cid, Service.service_date_iso.like(f"{date_iso}%"))
        .order_by(Service.saved_at, Service.id)
    ).all()
    first_seen: Dict[str, Tuple[Optional[int], str]] = {}
    for stored_date, hymns in rows:
        if normalize_date_iso(stored_date) != date_iso:
            continue
        for entry in stored_hymn_entries(hymns):
            key = usage_key(entry.title) if entry is not None else ""
            if key and key not in first_seen:
                first_seen[key] = (entry.number, entry.title)
    session.execute(delete(HymnUsage).where(HymnUsage.church_id == cid, HymnUsage.date_iso == date_iso))
    values = [{"church_id": cid, "date_iso": date_iso, "hymn_number": number, "hymn_title": title}
              for _key, (number, title) in sorted(first_seen.items())]
    if values:
        session.execute(insert_ignore(HymnUsage.__table__).on_conflict_do_nothing(), values)
    return len(values)
````

- [ ] **Step 4 (agent): Run the files and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_service_output.py backend/tests/test_usage_rebuild.py backend/tests/test_hymn_usage.py backend/tests/test_hymn_usage_window.py backend/tests/test_usecase_documents.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `40 passed, 1 skipped in <t>s`; `1283 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/service_output.py backend/tests/test_service_output.py backend/hymn_usage.py backend/tests/test_usage_rebuild.py
git commit -q -m "Hymn use: rebuild a date from its saved services; read stored dates and hymns tolerantly (5a-2; owner answer 6)" -m "hymn_usage.rebuild_usage_for_date replaces a church's rows for one date
with the union of the hymns of every service saved for it, deduped by
the title-only usage_key (first saved number and title kept), in the
caller's transaction, under a per-(church, date) advisory lock on
Postgres, rows in sorted order. Only a real YYYY-MM-DD is accepted.
service_output gains normalize_date_iso, coerce_number, StoredHymn,
stored_hymn_entries, slot_map and stored_hymns (F 6.2's 3 slots); a
malformed legacy row is skipped, never raised on." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 3: backend **1283 passed, 11 skipped**; frontend **618 in 81**.

### Task 4: Saving, opening, listing and deleting (owner answers 4, 6; S `usecases/archive.py`, "Normalizing stored data", "Data access and tenancy"; F §1.7, §2.2; clarifications 5-11, 15, 17)

**Files:**
- Create: `backend/repos/services.py`, `backend/tests/test_usecase_archive.py`
- Modify: `backend/repos/hymns.py`, `backend/usecases/archive.py`, `backend/tests/test_no_streamlit_in_core.py`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_usecase_archive.py`:**

````python
"""usecases.archive's saving, opening, listing and deleting (slice 5a spec,
Backend "usecases/archive.py", Testing `test_archive_usecase.py`; owner
answers 4 and 6, 2026-10-01). SQLite (`tmp_db`); the row lock and the
concurrent saves are in test_services_postgres.py."""
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Church, Hymn, HymnUsage, Service
from domain_errors import Conflict, InvalidInput, NotFound
from hymn_usage import record_usage
from service_output import CustomElement
from usecases import archive
from usecases.liturgy import HymnRefData

GONE = "That service is no longer in the archive."
HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."
D = date(2026, 10, 4)


@pytest.fixture
def pastor(make_user):
    return make_user(email="pastor@example.com", name="Pastor Ann")


@pytest.fixture
def church(pastor, make_church):
    return make_church(name="Grace", owner_user_id=pastor)


def add_hymn(church_id, title="Holy, Holy, Holy", number=138, hymnal="GG2013"):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number)
        s.add(row)
        s.flush()
        return row.id


def snapshot(title, number=None, hymnal=None):
    return HymnRefData(None, title, number, hymnal)


def service(**kw):
    base = dict(service_date=D, occasion=" World Communion Sunday ", scriptures=("Isaiah 5:1-7", " "),
                hymns={"opening": snapshot("Old Favorite", 12, "PH1990"), "response": None, "closing": None},
                liturgy={"call_to_worship": " Come. ", "opening_prayer": "  ",
                         "offertory_prayer": "[Error generating offertory_prayer: timeout]",
                         "benediction": "Go in peace."},
                sermon_title="Living Water", include_communion=True,
                custom_elements=(CustomElement("Anthem", "Choir", "sermon"),))
    return archive.ServiceInput(**{**base, **kw})


def stored(service_id):
    with session_scope() as s:
        row = s.get(Service, service_id)
        return None if row is None else {c: getattr(row, c) for c in (
            "service_date_iso", "service_date_display", "occasion", "scriptures", "hymns", "liturgy", "hymnal",
            "custom_elements", "include_communion", "created_by", "saved_at")}


def usage(church_id, date_iso="2026-10-04"):
    with session_scope() as s:
        return sorted(s.execute(select(HymnUsage.hymn_number, HymnUsage.hymn_title).where(
            HymnUsage.church_id == church_id, HymnUsage.date_iso == date_iso)).all(), key=lambda r: r[1])


def set_default_hymnal(church_id, code):
    with session_scope() as s:
        s.get(Church, church_id).settings = {"default_hymnal": code}


# --- create ---------------------------------------------------------------------

def test_create_writes_three_slots_the_display_date_and_the_8_sections(church, pastor):
    hymn_id = add_hymn(church)
    record = archive.create_service(church, pastor, service(hymns={
        "opening": HymnRefData(hymn_id, "Client's Copy", 1, None), "response": None,
        "closing": snapshot("Old Favorite", 12, "PH1990")}))
    row = stored(record.id)
    assert row["hymns"] == [
        {"slot": "opening", "title": "Holy, Holy, Holy", "number": 138, "hymn_id": str(hymn_id), "hymnal": "GG2013"},
        {"slot": "response", "title": "", "number": None, "hymn_id": None, "hymnal": None},
        {"slot": "closing", "title": "Old Favorite", "number": 12, "hymn_id": None, "hymnal": "PH1990"},
    ]
    assert (row["service_date_iso"], row["service_date_display"]) == ("2026-10-04", "October 04, 2026")
    assert row["occasion"] == "World Communion Sunday" and row["scriptures"] == ["Isaiah 5:1-7"]
    # Only non-blank sections, no error text; the Benediction and communion as sent (owner answer 4).
    assert row["liturgy"] == {"call_to_worship": "Come.", "benediction": "Go in peace."}
    assert row["include_communion"] is True
    assert row["custom_elements"] == [{"label": "Anthem", "text": "Choir", "insert_after": "sermon"}]
    assert row["created_by"] == pastor
    assert record.created_by == archive.Author(pastor, "Pastor Ann")
    assert record.hymns["opening"] == archive.ArchivedHymnData(hymn_id, "Holy, Holy, Holy", 138, "GG2013", True)
    assert record.hymns["closing"] == archive.ArchivedHymnData(None, "Old Favorite", 12, "PH1990", False)
    assert record.saved_at.endswith("+00:00")


def test_a_null_hymnal_is_stored_as_the_church_s_effective_hymnal(church, pastor, make_church):
    add_hymn(church, hymnal="GG2013")
    add_hymn(church, title="Be Thou My Vision", number=339, hymnal="PH1990")
    assert stored(archive.create_service(church, pastor, service()).id)["hymnal"] == "GG2013"   # first code
    set_default_hymnal(church, "PH1990")
    assert stored(archive.create_service(church, pastor, service()).id)["hymnal"] == "PH1990"   # the default
    assert stored(archive.create_service(church, pastor, service(hymnal="  Mine ")).id)["hymnal"] == "Mine"
    empty = make_church(name="No Hymns", owner_user_id=pastor)
    assert stored(archive.create_service(empty, pastor, service()).id)["hymnal"] is None


def test_a_hymn_the_church_lacks_or_a_blank_label_writes_nothing(church, pastor, make_church):
    theirs = add_hymn(make_church(name="Hope"))
    for bad, error in (
        (service(hymns={"response": HymnRefData(theirs, "Theirs", 1, None)}), NotFound),
        (service(hymns={"response": HymnRefData(uuid.uuid4(), "Gone", 1, None)}), NotFound),
        (service(custom_elements=(CustomElement("A", "", "end"), CustomElement("  ", "x", "end"))), InvalidInput),
    ):
        with pytest.raises(error) as info:
            archive.create_service(church, pastor, bad)
        if error is NotFound:
            assert (info.value.message, info.value.details) == (HYMN_GONE, {"field": "hymns.response.hymn_id"})
        else:
            assert info.value.field == "custom_elements.1.label"
    with session_scope() as s:
        assert s.execute(select(func.count()).select_from(Service)).scalar_one() == 0


def test_a_failed_usage_rebuild_rolls_the_save_back(church, pastor, monkeypatch):
    record_usage(church, "2026-10-04", [{"title": "Prepared", "number": 1}])

    def broken(*_a, **_k):
        raise RuntimeError("rebuild failed")

    monkeypatch.setattr(archive, "rebuild_usage_for_date", broken)
    with pytest.raises(RuntimeError):
        archive.create_service(church, pastor, service())
    with session_scope() as s:
        assert s.execute(select(func.count()).select_from(Service)).scalar_one() == 0
    assert usage(church) == [(1, "Prepared")]


# --- hymn use (owner answer 6) ---------------------------------------------------

def test_saving_records_the_date_s_union_and_replaces_prepared_rows(church, pastor):
    record_usage(church, "2026-10-04", [{"title": "Prepared Only", "number": 1}])
    archive.create_service(church, pastor, service())
    assert usage(church) == [(12, "Old Favorite")]
    archive.create_service(church, pastor, service(hymns={"opening": snapshot("Early Hymn", 5)}))
    assert usage(church) == [(5, "Early Hymn"), (12, "Old Favorite")]


def test_deleting_recalculates_the_date_from_the_services_left(church, pastor):
    keep = archive.create_service(church, pastor, service())
    gone = archive.create_service(church, pastor, service(hymns={"opening": snapshot("Early Hymn", 5)}))
    archive.delete_service(church, gone.id)
    assert stored(gone.id) is None and stored(keep.id) is not None
    assert usage(church) == [(12, "Old Favorite")]
    archive.delete_service(church, keep.id)
    assert usage(church) == []


def test_deleting_an_undated_service_changes_no_hymn_use(church, pastor):
    record_usage(church, "2026-10-04", [{"title": "Kept", "number": 1}])
    with session_scope() as s:
        row = Service(church_id=church, service_date_iso="", service_date_display="", occasion="Old",
                      scriptures=[], hymns=[{"title": "Kept", "number": 1}], liturgy={})
        s.add(row)
        s.flush()
        undated = row.id
    archive.delete_service(church, undated)
    assert stored(undated) is None
    assert usage(church) == [(1, "Kept")]


def test_moving_a_service_to_another_date_rebuilds_both_dates(church, pastor):
    record = archive.create_service(church, pastor, service())
    moved = archive.replace_service(church, record.id, service(service_date=date(2026, 10, 11)),
                                    if_match=record.saved_at)
    assert moved.service_date_iso == "2026-10-11"
    assert usage(church) == []
    assert usage(church, "2026-10-11") == [(12, "Old Favorite")]


# --- replace (If-Match) ------------------------------------------------------------

def test_replace_is_a_full_replace_that_keeps_the_author_and_moves_saved_at(church, pastor):
    record = archive.create_service(church, pastor, service())
    again = archive.replace_service(church, record.id, service(
        occasion="Changed", liturgy={}, custom_elements=(), include_communion=False,
        hymns={"closing": snapshot("Closing Hymn", 3)}), if_match=record.saved_at)
    row = stored(record.id)
    assert (row["occasion"], row["liturgy"], row["custom_elements"], row["include_communion"]) == (
        "Changed", {}, [], False)
    assert [h["title"] for h in row["hymns"]] == ["", "", "Closing Hymn"]
    assert row["created_by"] == pastor and again.created_by == record.created_by
    assert again.saved_at > record.saved_at
    assert usage(church) == [(3, "Closing Hymn")]


@pytest.mark.parametrize("header", [
    lambda saved: saved,
    lambda saved: f'"{saved}"',
    lambda saved: f'W/"{saved}"',
    lambda saved: saved.replace("+00:00", "Z"),
    lambda saved: datetime.fromisoformat(saved).astimezone(timezone(timedelta(hours=-4))).isoformat(),
])
def test_if_match_accepts_the_saved_at_in_any_spelling(church, pastor, header):
    record = archive.create_service(church, pastor, service())
    assert archive.replace_service(church, record.id, service(), if_match=header(record.saved_at)).id == record.id


def test_the_check_order_is_404_then_422_then_409_then_the_input(church, pastor):
    record = archive.create_service(church, pastor, service())
    blank_label = service(custom_elements=(CustomElement(" ", "", "end"),))
    with pytest.raises(NotFound) as gone:
        archive.replace_service(church, uuid.uuid4(), blank_label, if_match=None)
    assert (gone.value.message, gone.value.details) == (GONE, None)
    for value, message in ((None, "If-Match is required."), ("  ", "If-Match is required."),
                           ("yesterday", "If-Match must be the service's saved_at timestamp.")):
        with pytest.raises(InvalidInput) as missing:
            archive.replace_service(church, record.id, blank_label, if_match=value)
        assert (missing.value.code, missing.value.message) == ("invalid_request", message)
    stale = (datetime.fromisoformat(record.saved_at) - timedelta(microseconds=1)).isoformat()
    with pytest.raises(Conflict) as conflict:
        archive.replace_service(church, record.id, blank_label, if_match=stale)
    assert conflict.value.message == "This service was changed by someone else. Reload it to see their changes."
    assert conflict.value.details == {"current_saved_at": record.saved_at}
    with pytest.raises(InvalidInput) as label:
        archive.replace_service(church, record.id, blank_label, if_match=record.saved_at)
    assert label.value.field == "custom_elements.0.label"
    assert stored(record.id)["occasion"] == "World Communion Sunday"        # nothing was written


def test_another_church_s_service_is_not_found(church, pastor, make_church):
    record = archive.create_service(church, pastor, service())
    other = make_church(name="Hope")
    for call in (lambda: archive.get_service(other, record.id),
                 lambda: archive.replace_service(other, record.id, service(), if_match=record.saved_at),
                 lambda: archive.delete_service(other, record.id)):
        with pytest.raises(NotFound) as info:
            call()
        assert info.value.message == GONE
    assert stored(record.id) is not None
    assert archive.list_services(other, limit=20, offset=0).total == 0


# --- get: stored data normalized (5a spec, "Normalizing stored data") -------------

def legacy_row(church_id, **kw):
    base = dict(church_id=church_id, service_date_iso="2026-09-27", service_date_display="September 27, 2026",
                occasion="Pentecost 17", scriptures=["Psalm 25", 7], hymns=[], liturgy={}, sermon_title=None,
                selected_ot_ref=None, selected_nt_ref=None)
    with session_scope() as s:
        row = Service(**{**base, **kw})
        s.add(row)
        s.flush()
        return row.id


def test_a_compacted_streamlit_list_maps_by_position_and_resolves_by_title_and_number(church):
    gg = add_hymn(church, "Holy, Holy, Holy", 138, "GG2013")
    ph = add_hymn(church, "Holy, Holy, Holy", 138, "PH1990")
    add_hymn(church, "Be Thou My Vision", 450, "GG2013")
    sid = legacy_row(church, hymns=[{"title": "holy,  HOLY, holy", "number": 138}, {"title": "Unknown Hymn"},
                                    {"title": "Be Thou My Vision", "number": 999}, {"title": "Fourth"}])
    got = archive.get_service(church, sid)
    assert got.hymns["opening"] == archive.ArchivedHymnData(gg, "Holy, Holy, Holy", 138, "GG2013", True)
    assert got.hymns["response"] == archive.ArchivedHymnData(None, "Unknown Hymn", None, None, False)
    # The number must match when the entry has one.
    assert got.hymns["closing"] == archive.ArchivedHymnData(None, "Be Thou My Vision", 999, None, False)
    assert ph != gg                                  # GG2013 wins: the first code (no other preference)


def test_title_matches_prefer_the_entry_s_hymnal_then_the_service_s_then_the_church_s(church):
    gg = add_hymn(church, "Amazing Grace", 649, "GG2013")
    ph = add_hymn(church, "Amazing Grace", 280, "PH1990")
    el = add_hymn(church, "Amazing Grace", 779, "ELW")
    sid = legacy_row(church, hymnal="PH1990", hymns=[{"title": "Amazing Grace", "hymnal": "ELW"},
                                                     {"title": "Amazing Grace"}])
    got = archive.get_service(church, sid)
    assert (got.hymns["opening"].hymn_id, got.hymns["response"].hymn_id) == (el, ph)
    no_pref = archive.get_service(church, legacy_row(church, hymns=[{"title": "Amazing Grace"}]))
    assert no_pref.hymns["opening"].hymn_id == el                     # effective hymnal: the first code, "ELW"
    set_default_hymnal(church, "GG2013")
    assert archive.get_service(church, legacy_row(church, hymns=[{"title": "Amazing Grace"}])
                               ).hymns["opening"].hymn_id == gg


def test_duplicate_titles_resolve_the_same_way_every_time(church):
    ids = [add_hymn(church, "Doxology", n, "PH1990") for n in (593, 592, None)]
    sid = legacy_row(church, hymns=[{"title": "Doxology"}])
    picks = {archive.get_service(church, sid).hymns["opening"].hymn_id for _ in range(3)}
    assert picks == {ids[1]}                                           # the lowest number


def test_a_stored_id_resolves_to_the_hymn_s_current_title(church, pastor):
    hymn_id = add_hymn(church, "Old Title", 1)
    record = archive.create_service(church, pastor, service(hymns={"opening": HymnRefData(hymn_id, "x", None, None)}))
    with session_scope() as s:
        s.get(Hymn, hymn_id).title = "New Title"
    assert archive.get_service(church, record.id).hymns["opening"].title == "New Title"
    with session_scope() as s:
        s.delete(s.get(Hymn, hymn_id))
    assert archive.get_service(church, record.id).hymns["opening"] == archive.ArchivedHymnData(
        None, "Old Title", 1, "GG2013", False)


def test_liturgy_custom_elements_and_dates_are_normalized(church):
    sid = legacy_row(church, service_date_iso="2026-10-04T00:00:00.000Z", liturgy={
        "call_to_worship": " Come. ", "opening_prayer": "", "notion_era_key": "x", "benediction": 5,
        "offertory_prayer": "[Configure OPENAI_API_KEY to generate offertory_prayer.]"},
        custom_elements=[{"label": "Anthem", "text": "Choir", "insert_after": "sermon"},
                         {"label": "Bogus", "text": "x", "insert_after": "bogus"}, {"label": 3}, "junk"])
    got = archive.get_service(church, sid)
    assert got.service_date_iso == "2026-10-04"
    assert got.liturgy == {"call_to_worship": "Come."}
    assert got.custom_elements == [CustomElement("Anthem", "Choir", "sermon"), CustomElement("Bogus", "x", "end"),
                                   CustomElement("", "", "end")]
    assert got.scriptures == ["Psalm 25"]
    assert (got.sermon_title, got.selected_ot_ref, got.created_by, got.hymnal) == ("", "", None, None)
    assert got.hymns == {"opening": None, "response": None, "closing": None}
    assert archive.get_service(church, legacy_row(church, service_date_iso="Oct 4", custom_elements=None)
                               ).service_date_iso is None


def test_an_element_with_an_unknown_place_survives_open_then_save(church, pastor):
    sid = legacy_row(church, custom_elements=[{"label": "Bogus", "text": "x", "insert_after": "bogus"}])
    opened = archive.get_service(church, sid)
    archive.replace_service(church, sid, service(custom_elements=tuple(opened.custom_elements)),
                            if_match=opened.saved_at)
    assert stored(sid)["custom_elements"] == [{"label": "Bogus", "text": "x", "insert_after": "end"}]


# --- list --------------------------------------------------------------------------

def test_the_list_is_newest_service_date_first_with_undated_last(church, pastor, make_user):
    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    gone_author = make_user(email="gone@example.com", name="  ")
    ids = {}
    for name, date_iso, minutes, author in (("old", "2026-09-27", 0, pastor), ("blank", "", 1, None),
                                            ("new", "2026-10-11", 2, gone_author), ("none", None, 3, None),
                                            ("same-day-later", "2026-10-11", 5, pastor)):
        ids[name] = legacy_row(church, service_date_iso=date_iso, occasion=name, created_by=author,
                               saved_at=base + timedelta(minutes=minutes))
    page = archive.list_services(church, limit=20, offset=0)
    assert [i.occasion for i in page.items] == ["same-day-later", "new", "old", "none", "blank"]
    assert (page.total, page.limit, page.offset) == (5, 20, 0)
    new = page.items[1]
    assert new.created_by == archive.Author(gone_author, "gone@example.com")     # a blank name: the email
    assert (new.service_date_iso, new.saved_at) == ("2026-10-11", "2026-09-01T00:02:00+00:00")
    assert page.items[3].service_date_iso is None and page.items[3].created_by is None
    window = archive.list_services(church, limit=2, offset=2)
    assert [i.occasion for i in window.items] == ["old", "none"] and window.total == 5


def test_saving_logs_ids_and_counts_never_text(church, pastor, caplog):
    with caplog.at_level(logging.INFO, logger="usecases.archive"):
        record = archive.create_service(church, pastor, service())
        archive.delete_service(church, record.id)
    lines = [r.getMessage() for r in caplog.records if r.name == "usecases.archive"]
    assert lines[0].startswith(f"archive.create church={church} service={record.id} usage_rows=1 ms=")
    assert lines[1].startswith(f"archive.delete church={church} service={record.id} usage_rows=0 ms=")
    assert not any("Communion" in line or "Old Favorite" in line for line in lines)
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "service_output, worship_service, usecases.archive, usecases.documents; "
````

**with:**

````python
            "service_output, worship_service, usecases.archive, usecases.documents, repos.services, hymn_usage; "
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_archive.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
```

**Expected:** `25 failed, 2 passed in <t>s`: every `test_usecase_archive.py` case (`AttributeError`: `usecases.archive` has no `create_service`, `Author`, …) and `test_usecases_package_imports_no_fastapi_or_streamlit` (`No module named 'repos.services'`).

- [ ] **Step 3 (agent): The repo, the title lookup, the usecases**

**Create `backend/repos/services.py`:**

````python
"""Saved services, church-scoped (slice 5a-2; 5a spec "Data access and tenancy").

Every query filters on church_id, so another church's service is simply
absent (the usecase's 404). Each function runs in the caller's session, or
its own when none is given (F §2.2 rule 3); usecases.archive owns the
transactions. service_archive.py stays as the frozen Streamlit branch left it
(slice 7 deletes it).
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Service, User


@dataclass(frozen=True)
class SummaryRow:
    """One row of the archive list: no JSON columns (a projection)."""
    id: uuid.UUID
    service_date_iso: Optional[str]
    service_date_display: Optional[str]
    occasion: Optional[str]
    sermon_title: Optional[str]
    saved_at: datetime
    created_by: Optional[uuid.UUID]
    author_name: Optional[str]
    author_email: Optional[str]


# Newest service date first, with NULL and a legacy "" last; then the latest
# save, then the id (F §1.4: nulls_last spelled out, an id tie-breaker).
LIST_ORDER = (func.nullif(Service.service_date_iso, "").desc().nulls_last(),
              Service.saved_at.desc(), Service.id.desc())


def _in(session: Optional[Session], work):
    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)


def get_service(church_id, service_id, *, session: Session, for_update: bool = False) -> Optional[Service]:
    """The church's service with this id, or None. `for_update` locks the row
    (SELECT ... FOR UPDATE; nothing on SQLite) until the transaction ends."""
    stmt = select(Service).where(Service.id == as_uuid(service_id), Service.church_id == as_uuid(church_id))
    if for_update:
        stmt = stmt.with_for_update()
    return session.execute(stmt).scalar_one_or_none()


def list_page(church_id, *, limit: int, offset: int,
              session: Optional[Session] = None) -> tuple[list[SummaryRow], int]:
    """One page of the church's services in LIST_ORDER, and the church's total."""
    cid = as_uuid(church_id)

    def work(s: Session) -> tuple[list[SummaryRow], int]:
        total = s.execute(select(func.count()).select_from(Service).where(Service.church_id == cid)).scalar_one()
        rows = s.execute(
            select(Service.id, Service.service_date_iso, Service.service_date_display, Service.occasion,
                   Service.sermon_title, Service.saved_at, Service.created_by, User.name, User.email)
            .outerjoin(User, User.id == Service.created_by)
            .where(Service.church_id == cid)
            .order_by(*LIST_ORDER).limit(limit).offset(offset)
        ).all()
        return [SummaryRow(*row) for row in rows], int(total)

    return _in(session, work)


def author(user_id, *, session: Session) -> Optional[tuple[uuid.UUID, Optional[str], str]]:
    """(id, name, email) of the user who created a service, or None (removed)."""
    if user_id is None:
        return None
    row = session.execute(select(User.id, User.name, User.email).where(User.id == as_uuid(user_id))).first()
    return None if row is None else (row.id, row.name, row.email)


def insert_service(church_id, created_by, fields: dict, *, session: Session) -> Service:
    """Add a service with these column values (usecases.archive builds them); flushed, so it has its id."""
    row = Service(church_id=as_uuid(church_id), created_by=None if created_by is None else as_uuid(created_by),
                  **fields)
    session.add(row)
    session.flush()
    return row


def update_service(row: Service, fields: dict, *, session: Session) -> Service:
    """Replace these columns of a service already read (and locked) in `session`; created_by never changes."""
    for name, value in fields.items():
        setattr(row, name, value)
    session.flush()
    return row


def delete_service(row: Service, *, session: Session) -> None:
    session.delete(row)
    session.flush()
````

**In `backend/repos/hymns.py`, replace:**

````python
from domain_errors import NotFound

````

**with:**

````python
from domain_errors import NotFound
from hymn_search import normalize_title

````

**Append to `backend/repos/hymns.py`:**

````python


def find_hymns_by_titles(church_id, title_keys, *, session: Optional[Session] = None) -> list[HymnRecord]:
    """The church's hymns whose hymn_search.normalize_title(title) is in
    `title_keys`, ordered by hymnal, number (nulls last), id (slice 5a-2:
    opening a saved service whose hymn has no id that still resolves). The
    filter runs in Python, because SQL cannot collapse whitespace the same way
    on SQLite and Postgres; a church has a few thousand hymns at most, and the
    caller asks only when some slot needs it."""
    wanted = {key for key in title_keys if key}
    if not wanted:
        return []
    cid = as_uuid(church_id)

    def work(s: Session) -> list[HymnRecord]:
        rows = s.execute(select(*_RECORD_COLUMNS).where(Hymn.church_id == cid)
                         .order_by(Hymn.hymnal.asc(), Hymn.number.asc().nulls_last(), Hymn.id.asc())).all()
        return [_record(row) for row in rows if normalize_title(row.title) in wanted]

    return _in(session, work)
````

**In `backend/usecases/archive.py`, replace:**

````python
No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import datetime
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Optional

from domain_errors import InvalidInput, NotFound
from repos import hymns as hymn_repo
from service_output import SLOTS, CustomElement, ResolvedHymn, is_legacy_error_placeholder
from usecases.liturgy import HYMN_GONE_MESSAGE, HymnRefData

````

**with:**

````python
Slice 5a-2 adds the archive (owner answers 4 and 6, 2026-10-01), each in one
transaction:
- create_service and replace_service: clean the input, resolve the hymns,
  write the row (3 slot entries, the display date, only the 8 sections, the
  custom elements, the hymnal: the church's effective hymnal when none is
  sent), then rebuild the date's hymn use. replace_service first locks the
  row and checks If-Match against saved_at (404, then 422, then 409, then
  the input's own errors); a PUT that moves a service to another date
  rebuilds both dates. What is sent is what is stored: a Benediction that
  followed the church default and the communion setting are kept as saved.
- get_service: the stored row normalized for the builder (hymns by slot,
  resolved by id, else by title and number; only the 8 sections without
  Streamlit's error texts; custom elements kept with an unknown place read
  as "end"; the date through normalize_date_iso).
- list_services: one page, newest service date first, undated last.
- delete_service: removes the row and rebuilds that date's hymn use from the
  services still saved for it (owner answer 6); an undated service changes
  no hymn use.

No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import datetime
import logging
import re
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Optional

from db import session_scope
from db.ids import as_uuid
from domain_errors import Conflict, InvalidInput, NotFound
from hymn_search import normalize_title
from hymn_usage import rebuild_usage_for_date
from liturgy_config import SECTION_ORDER, normalize_placement
from repos import hymns as hymn_repo
from repos import services as services_repo
from service_output import (SLOTS, CustomElement, ResolvedHymn, is_legacy_error_placeholder, normalize_date_iso,
                            service_date_display, slot_map, stored_hymns)
from usecases.hymns import resolve_default_hymnal
from usecases.liturgy import HYMN_GONE_MESSAGE, HymnRefData

logger = logging.getLogger(__name__)

````

**Append to `backend/usecases/archive.py`:**

````python


# --- slice 5a-2: saving, listing, opening and deleting services (5a spec, Backend "usecases/archive.py") ---

SERVICE_GONE_MESSAGE = "That service is no longer in the archive."
CONFLICT_MESSAGE = "This service was changed by someone else. Reload it to see their changes."
IF_MATCH_REQUIRED_MESSAGE = "If-Match is required."
IF_MATCH_INVALID_MESSAGE = "If-Match must be the service's saved_at timestamp."


@dataclass(frozen=True)
class Author:
    id: uuid.UUID
    name: str                                   # the member's name, else their email (owner decision 5)


@dataclass(frozen=True)
class ArchivedHymnData:
    hymn_id: Optional[uuid.UUID]
    title: str
    number: Optional[int]
    hymnal: Optional[str]
    in_hymnal: bool                             # the hymn is in the church's hymnal now


@dataclass(frozen=True)
class ServiceRecord:
    id: uuid.UUID
    service_date_iso: Optional[str]             # normalize_date_iso; None for an undated legacy row
    service_date: str                           # the stored display date ("October 04, 2026")
    occasion: str
    scriptures: list[str]
    hymns: dict[str, Optional[ArchivedHymnData]]
    hymnal: Optional[str]
    liturgy: dict[str, str]
    sermon_title: str
    selected_ot_ref: str
    selected_nt_ref: str
    include_communion: bool
    custom_elements: list[CustomElement]
    created_by: Optional[Author]
    saved_at: str                               # ISO 8601 in UTC, "+00:00"


@dataclass(frozen=True)
class ServiceSummaryData:
    id: uuid.UUID
    service_date_iso: Optional[str]
    service_date: str
    occasion: str
    sermon_title: str
    saved_at: str
    created_by: Optional[Author]


@dataclass(frozen=True)
class ServicePageData:
    items: list[ServiceSummaryData]
    total: int
    limit: int
    offset: int


def _utc(value: datetime.datetime) -> datetime.datetime:
    """A naive value (SQLite) is UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)


def saved_at_text(value: datetime.datetime) -> str:
    return _utc(value).isoformat()


def parse_if_match(value: Optional[str]) -> datetime.datetime:
    """The saved_at an If-Match header carries, in UTC: surrounding quotes and a
    W/ prefix are ignored; missing or blank is 422 "If-Match is required.",
    anything else that is not an ISO 8601 timestamp is 422 "If-Match must be
    the service's saved_at timestamp."."""
    if value is None or not value.strip():
        raise InvalidInput(IF_MATCH_REQUIRED_MESSAGE)
    text = value.strip()
    if text.startswith("W/"):
        text = text[2:].strip()
    text = text.strip('"').strip()
    try:
        return _utc(datetime.datetime.fromisoformat(text))
    except ValueError:
        raise InvalidInput(IF_MATCH_INVALID_MESSAGE) from None


def _author(user_id, name: Optional[str], email: Optional[str]) -> Optional[Author]:
    if user_id is None:
        return None
    return Author(user_id, (name or "").strip() or (email or ""))


def _fields(church_id: uuid.UUID, clean: ServiceInput, hymns: Mapping[str, Optional[ResolvedHymn]],
            session) -> dict:
    """The columns a save writes (F §6.2), saved_at included (it moves on every save)."""
    day = clean.service_date
    return {
        "service_date_iso": day.isoformat(),
        "service_date_display": service_date_display(day),
        "occasion": clean.occasion,
        "scriptures": list(clean.scriptures),
        "hymns": stored_hymns(hymns),
        # null = the hymnal the hymns step showed: the church's effective hymnal now.
        "hymnal": clean.hymnal or resolve_default_hymnal(church_id, session=session).effective_hymnal,
        "liturgy": {key: clean.liturgy[key] for key in SECTION_ORDER if key in clean.liturgy},
        "sermon_title": clean.sermon_title,
        "selected_ot_ref": clean.selected_ot_ref,
        "selected_nt_ref": clean.selected_nt_ref,
        "include_communion": clean.include_communion,
        "custom_elements": [{"label": e.label, "text": e.text, "insert_after": e.insert_after}
                            for e in clean.custom_elements],
        "saved_at": datetime.datetime.now(datetime.timezone.utc),
    }


def _hymn_from_record(record) -> ArchivedHymnData:
    return ArchivedHymnData(record.id, (record.title or "").strip(), record.number, record.hymnal, True)


def _best_match(entry, candidates, preferred: list[str]):
    """The church's hymn for a stored entry without a usable id: the same
    normalized title (and number, when the entry has one), from the first
    preferred hymnal that has it, else from the first other hymnal in code
    order; within a hymnal the lowest number (nulls last), then the lowest id,
    so the answer is the same on every run (PH1990 has 34 duplicate titles)."""
    key = normalize_title(entry.title)
    pool = [c for c in candidates
            if normalize_title(c.title) == key and (entry.number is None or c.number == entry.number)]
    if not pool:
        return None

    def rank(c):
        place = preferred.index(c.hymnal) if c.hymnal in preferred else len(preferred)
        return (place, c.hymnal, c.number is None, c.number or 0, c.id)

    return min(pool, key=rank)


def _archived_hymns(session, church_id: uuid.UUID, row) -> dict[str, Optional[ArchivedHymnData]]:
    by_slot = slot_map(row.hymns)
    ids: dict[str, uuid.UUID] = {}
    for slot, entry in by_slot.items():
        if entry is not None and entry.hymn_id is not None:
            try:
                ids[slot] = uuid.UUID(entry.hymn_id)
            except ValueError:
                pass
    found = hymn_repo.get_hymns_by_ids(church_id, list(ids.values()), session=session) if ids else {}
    result: dict[str, Optional[ArchivedHymnData]] = {}
    unmatched = {}
    for slot, entry in by_slot.items():
        record = found.get(ids.get(slot)) if entry is not None else None
        if entry is None:
            result[slot] = None
        elif record is not None and (record.title or "").strip():
            result[slot] = _hymn_from_record(record)
        else:
            unmatched[slot] = entry
    if unmatched:
        candidates = hymn_repo.find_hymns_by_titles(
            church_id, {normalize_title(e.title) for e in unmatched.values()}, session=session)
        effective = resolve_default_hymnal(church_id, session=session).effective_hymnal
        for slot, entry in unmatched.items():
            preferred = [h for h in (entry.hymnal, row.hymnal, effective) if h]
            match = _best_match(entry, candidates, preferred)
            result[slot] = (_hymn_from_record(match) if match is not None else
                            ArchivedHymnData(None, entry.title, entry.number, entry.hymnal, False))
    return {slot: result[slot] for slot in SLOTS}


def _archived_liturgy(raw) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {key: text.strip() for key in SECTION_ORDER
            if isinstance(text := raw.get(key), str) and text.strip() and not is_legacy_error_placeholder(text)}


def _archived_custom_elements(raw) -> list[CustomElement]:
    """Every stored element, in order; never dropped for its place (unknown or missing reads as "end")."""
    if not isinstance(raw, list):
        return []
    return [CustomElement(label if isinstance(label := e.get("label"), str) else "",
                          text if isinstance(text := e.get("text"), str) else "",
                          normalize_placement(e.get("insert_after")))
            for e in raw if isinstance(e, dict)]


def _record(session, church_id: uuid.UUID, row) -> ServiceRecord:
    found = services_repo.author(row.created_by, session=session)
    return ServiceRecord(
        id=row.id,
        service_date_iso=normalize_date_iso(row.service_date_iso),
        service_date=row.service_date_display or "",
        occasion=row.occasion or "",
        scriptures=[line for line in row.scriptures if isinstance(line, str)] if isinstance(row.scriptures, list) else [],
        hymns=_archived_hymns(session, church_id, row),
        hymnal=row.hymnal,
        liturgy=_archived_liturgy(row.liturgy),
        sermon_title=row.sermon_title or "",
        selected_ot_ref=row.selected_ot_ref or "",
        selected_nt_ref=row.selected_nt_ref or "",
        include_communion=bool(row.include_communion),
        custom_elements=_archived_custom_elements(row.custom_elements),
        created_by=None if found is None else _author(*found),
        saved_at=saved_at_text(row.saved_at),
    )


def _log(action: str, church_id: uuid.UUID, service_id: uuid.UUID, usage_rows: int, started: float) -> None:
    """Ids and counts only, never a service's text (F §2.5)."""
    logger.info("archive.%s church=%s service=%s usage_rows=%d ms=%d", action, church_id, service_id, usage_rows,
                round((time.monotonic() - started) * 1000))


def create_service(church_id: uuid.UUID, user_id: uuid.UUID, data: ServiceInput) -> ServiceRecord:
    """POST /services: save a new service and rebuild its date's hymn use, in one transaction."""
    started = time.monotonic()
    cid, uid = as_uuid(church_id), as_uuid(user_id)
    clean = clean_input(data)
    with session_scope() as s:
        hymns = resolve_hymn_refs(s, cid, clean.hymns)
        row = services_repo.insert_service(cid, uid, _fields(cid, clean, hymns, s), session=s)
        usage_rows = rebuild_usage_for_date(cid, row.service_date_iso, session=s)
        record = _record(s, cid, row)
    _log("create", cid, record.id, usage_rows, started)
    return record


def replace_service(church_id: uuid.UUID, service_id: uuid.UUID, data: ServiceInput, *,
                    if_match: Optional[str]) -> ServiceRecord:
    """PUT /services/{id}: the 5a spec's check order (the row, If-Match present
    and readable, If-Match equal to saved_at, the input), then a full replace
    (created_by kept, saved_at moved) and the hymn-use rebuild of the saved
    date and, when the date changed, of the date it left, in date order."""
    started = time.monotonic()
    cid = as_uuid(church_id)
    with session_scope() as s:
        row = services_repo.get_service(cid, service_id, session=s, for_update=True)
        if row is None:
            raise NotFound(SERVICE_GONE_MESSAGE)
        expected = parse_if_match(if_match)
        current = _utc(row.saved_at)
        if expected != current:
            raise Conflict(CONFLICT_MESSAGE, details={"current_saved_at": current.isoformat()})
        clean = clean_input(data)
        hymns = resolve_hymn_refs(s, cid, clean.hymns)
        old_date = normalize_date_iso(row.service_date_iso)
        services_repo.update_service(row, _fields(cid, clean, hymns, s), session=s)
        usage_rows = 0
        for date_iso in sorted({old_date, row.service_date_iso} - {None}):
            usage_rows += rebuild_usage_for_date(cid, date_iso, session=s)
        record = _record(s, cid, row)
    _log("replace", cid, record.id, usage_rows, started)
    return record


def get_service(church_id: uuid.UUID, service_id: uuid.UUID) -> ServiceRecord:
    """GET /services/{id}: the church's service, normalized (see the module docstring)."""
    cid = as_uuid(church_id)
    with session_scope() as s:
        row = services_repo.get_service(cid, service_id, session=s)
        if row is None:
            raise NotFound(SERVICE_GONE_MESSAGE)
        return _record(s, cid, row)


def list_services(church_id: uuid.UUID, *, limit: int, offset: int) -> ServicePageData:
    """GET /services: one page, newest service date first (undated last), then the latest save, then id."""
    rows, total = services_repo.list_page(as_uuid(church_id), limit=limit, offset=offset)
    items = [ServiceSummaryData(id=r.id, service_date_iso=normalize_date_iso(r.service_date_iso),
                                service_date=r.service_date_display or "", occasion=r.occasion or "",
                                sermon_title=r.sermon_title or "", saved_at=saved_at_text(r.saved_at),
                                created_by=_author(r.created_by, r.author_name, r.author_email))
             for r in rows]
    return ServicePageData(items=items, total=total, limit=limit, offset=offset)


def delete_service(church_id: uuid.UUID, service_id: uuid.UUID) -> None:
    """DELETE /services/{id}: remove the service and rebuild its date's hymn use
    from the services still saved for that date (owner answer 6), in one
    transaction. An undated service changes no hymn use."""
    started = time.monotonic()
    cid = as_uuid(church_id)
    with session_scope() as s:
        row = services_repo.get_service(cid, service_id, session=s, for_update=True)
        if row is None:
            raise NotFound(SERVICE_GONE_MESSAGE)
        deleted_id, date_iso = row.id, normalize_date_iso(row.service_date_iso)
        services_repo.delete_service(row, session=s)
        usage_rows = rebuild_usage_for_date(cid, date_iso, session=s) if date_iso else 0
    _log("delete", cid, deleted_id, usage_rows, started)
````

- [ ] **Step 4 (agent): Run the files and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_archive.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_usecase_documents.py backend/tests/test_hymns_repo.py 2>&1 | tail -1
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/usecases/archive.py backend/repos/services.py backend/hymn_usage.py backend/service_output.py; echo "imports grep exit $?"
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `48 passed in <t>s`; `imports grep exit 1`; `1307 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/repos/services.py backend/repos/hymns.py backend/usecases/archive.py backend/tests/test_usecase_archive.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Archive usecases: save, save changes with If-Match, open, list and delete services, each with its hymn-use rebuild (5a-2; owner answers 4, 6)" -m "usecases.archive gains create_service, replace_service (row lock, then
404, If-Match 422s, 409 with current_saved_at, the input), get_service
(hymns by slot or position, resolved by id, else by title and number
with the hymnal preference and a fixed tie-break; only the 8 sections;
custom elements kept, unknown places as end), list_services (newest
date first, undated last) and delete_service (rebuilds the date it
leaves; an undated service changes no hymn use). Each save writes 3 slot
entries, the display date and the effective hymnal for a null one, and
stores the Benediction and communion as sent. repos/services.py holds
the queries; repos/hymns gains find_hymns_by_titles. Logs carry ids and
counts only." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 4: backend **1307 passed, 11 skipped**; frontend **618 in 81**.

### Task 5: The `/services` routes (S API, "Schemas"; F §1.2, §1.4, §1.6, §1.7; owner decision 5; clarifications 3, 4, 5, 12, 16)

**Files:**
- Create: `backend/api/routes/services.py`, `backend/tests/test_api_services.py`
- Modify: `backend/api/schemas.py`, `backend/api/main.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_api_services.py`:**

````python
"""/services (slice 5a spec, API; Testing `test_api_services.py`; acceptance
criteria 6-10; F §1.6 church-scope amendment; owner answers 4 and 6, 2026-10-01)."""
import uuid

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Hymn, HymnUsage, Service
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
GONE = "That service is no longer in the archive."
HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."
CONFLICT = "This service was changed by someone else. Reload it to see their changes."
SERVICE = {
    "service_date_iso": "2026-10-04",
    "occasion": "World Communion Sunday",
    "scriptures": ["Isaiah 5:1-7", "Philippians 3:4b-14"],
    "hymns": {"opening": {"hymn_id": None, "title": "Old Favorite", "number": 12, "hymnal": "PH1990"},
              "response": None, "closing": None},
    "hymnal": None,
    "liturgy": {"call_to_worship": "Come.", "benediction": "Go in peace."},
    "sermon_title": "Living Water",
    "selected_ot_ref": "",
    "selected_nt_ref": "",
    "include_communion": True,
    "custom_elements": [{"label": "Anthem", "text": "Choir", "insert_after": "sermon"}],
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def pastor(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(pastor, make_church):
    return make_church(name="Grace", owner_user_id=pastor)


def call(client, method, path, church_id, *, email=EMAIL, json=None, **headers):
    return client.request(method, path, json=json, headers={**church_headers(email, church_id), **headers})


def create(client, church_id, body=SERVICE, **headers):
    r = call(client, "POST", "/services", church_id, json=body, **headers)
    assert r.status_code == 201, r.text
    return r.json()


def error(r):
    body = r.json()["error"]
    return body["code"], body["message"]


def service_count():
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(Service)).scalar_one()


def test_create_open_list_replace_delete(client, church, pastor):
    made = create(client, church)
    assert made["hymns"] == {
        "opening": {"hymn_id": None, "title": "Old Favorite", "number": 12, "hymnal": "PH1990", "in_hymnal": False},
        "response": None, "closing": None}
    assert (made["service_date_iso"], made["service_date"]) == ("2026-10-04", "October 04, 2026")
    assert made["liturgy"] == {"call_to_worship": "Come.", "benediction": "Go in peace."}
    assert made["include_communion"] is True
    assert made["custom_elements"] == SERVICE["custom_elements"]
    # The author's name as the sign-in token last gave it (tests.jwt_helpers), else the email.
    assert made["created_by"] == {"id": str(pastor), "name": "Pat Tor"} and made["saved_at"].endswith("+00:00")
    sid = made["id"]
    opened = call(client, "GET", f"/services/{sid}", church)
    assert (opened.status_code, opened.json()) == (200, made)
    listed = call(client, "GET", "/services", church).json()
    assert (listed["total"], listed["limit"], listed["offset"]) == (1, 20, 0)
    assert listed["items"] == [{key: made[key] for key in (
        "id", "service_date_iso", "service_date", "occasion", "sermon_title", "saved_at", "created_by")}]
    r = call(client, "PUT", f"/services/{sid}", church, json={**SERVICE, "occasion": "Changed"},
             **{"If-Match": made["saved_at"]})
    assert r.status_code == 200, r.text
    assert r.json()["occasion"] == "Changed" and r.json()["saved_at"] > made["saved_at"]
    r = call(client, "DELETE", f"/services/{sid}", church)
    assert (r.status_code, r.json()) == (200, {"deleted": True})
    assert call(client, "GET", f"/services/{sid}", church).status_code == 404


def test_hymn_use_follows_save_and_delete(client, church):
    first = create(client, church)
    create(client, church, {**SERVICE, "hymns": {"closing": {"title": "Early Hymn", "number": 5}}})

    def used():
        with session_scope() as s:
            return sorted(s.execute(select(HymnUsage.hymn_title).where(
                HymnUsage.church_id == church, HymnUsage.date_iso == "2026-10-04")).scalars().all())

    assert used() == ["Early Hymn", "Old Favorite"]
    call(client, "DELETE", f"/services/{first['id']}", church)
    assert used() == ["Early Hymn"]


@pytest.mark.parametrize("role", ["member", "admin"])
def test_any_member_may_save_replace_and_delete(client, church, make_user, role):
    other = f"{role}@example.com"
    add_membership(make_user(email=other), church, role)
    made = create(client, church)
    r = call(client, "POST", "/services", church, email=other, json=SERVICE)
    assert r.status_code == 201, r.text
    r = call(client, "PUT", f"/services/{made['id']}", church, email=other, json=SERVICE,
             **{"If-Match": made["saved_at"]})
    assert r.status_code == 200, r.text
    assert r.json()["created_by"] == made["created_by"]          # the author stays the first saver
    assert call(client, "DELETE", f"/services/{made['id']}", church, email=other).status_code == 200


def test_every_route_is_church_isolated(client, isolation_world):
    world = isolation_world
    r = call(client, "POST", "/services", world.church_b, email=world.b, json=SERVICE)
    theirs_id = r.json()["id"]
    theirs_saved = r.json()["saved_at"]
    mine = call(client, "POST", "/services", world.church_a, email=world.a, json=SERVICE).json()
    assert_church_isolated(client, "GET", "/services", world=world)
    assert_church_isolated(client, "GET", f"/services/{mine['id']}", world=world,
                           resource_path_b=f"/services/{theirs_id}")
    assert_church_isolated(client, "POST", "/services", world=world, json=SERVICE)
    # PUT: church B's id is a 404 even with its real saved_at; a@'s own service then saves.
    r = client.put(f"/services/{theirs_id}", json=SERVICE,
                   headers={**church_headers(world.a, world.church_a), "If-Match": theirs_saved})
    assert (r.status_code, error(r)) == (404, ("not_found", GONE))
    assert_church_isolated(client, "DELETE", f"/services/{mine['id']}", world=world,
                           resource_path_b=f"/services/{theirs_id}")
    assert call(client, "GET", f"/services/{theirs_id}", world.church_b, email=world.b).status_code == 200


def test_another_church_s_hymn_id_is_a_404_naming_the_slot_and_writes_nothing(client, isolation_world):
    world = isolation_world
    with session_scope() as s:
        hymn = Hymn(church_id=world.church_b, hymnal="GG2013", title="Their Hymn", number=1)
        s.add(hymn)
        s.flush()
        theirs = str(hymn.id)
    for hymn_id in (theirs, str(uuid.uuid4())):
        body = {**SERVICE, "hymns": {"response": {"hymn_id": hymn_id, "title": "x", "number": 1, "hymnal": None}}}
        r = call(client, "POST", "/services", world.church_a, email=world.a, json=body)
        assert r.status_code == 404, r.text
        assert r.json()["error"]["details"] == {"field": "hymns.response.hymn_id"}
        assert error(r) == ("not_found", HYMN_GONE)
    assert service_count() == 0


def test_put_check_order_and_messages(client, church):
    made = create(client, church)
    path = f"/services/{made['id']}"
    r = call(client, "PUT", f"/services/{uuid.uuid4()}", church, json=SERVICE)
    assert (r.status_code, error(r)) == (404, ("not_found", GONE))
    assert "details" not in r.json()["error"]                       # not a hymn 404: the client POSTs instead
    r = call(client, "PUT", path, church, json=SERVICE)
    assert (r.status_code, error(r)) == (422, ("invalid_request", "If-Match is required."))
    r = call(client, "PUT", path, church, json=SERVICE, **{"If-Match": "yesterday"})
    assert (r.status_code, error(r)) == (422, ("invalid_request", "If-Match must be the service's saved_at timestamp."))
    r = call(client, "PUT", path, church, json=SERVICE, **{"If-Match": "2026-01-01T00:00:00+00:00"})
    assert (r.status_code, error(r)) == (409, ("conflict", CONFLICT))
    assert r.json()["error"]["details"] == {"current_saved_at": made["saved_at"]}
    ok = call(client, "PUT", path, church, json=SERVICE, **{"If-Match": made["saved_at"]})
    assert ok.status_code == 200
    stale = call(client, "PUT", path, church, json=SERVICE, **{"If-Match": made["saved_at"]})
    assert (stale.status_code, stale.json()["error"]["details"]) == (409, {"current_saved_at": ok.json()["saved_at"]})


@pytest.mark.parametrize("method, path", [("GET", "/services/not-a-uuid"), ("PUT", "/services/not-a-uuid"),
                                          ("DELETE", "/services/not-a-uuid"), ("GET", "/services?limit=0"),
                                          ("GET", "/services?limit=201"), ("GET", "/services?offset=-1")])
def test_malformed_ids_and_paging_are_422(client, church, method, path):
    r = call(client, method, path, church, json=SERVICE if method == "PUT" else None)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")


@pytest.mark.parametrize("change, field", [
    ({"extra": 1}, "extra"),
    ({"custom_elements": [{"label": "A", "text": "", "insert_after": "bogus"}]}, "custom_elements.0.insert_after"),
    ({"service_date_iso": "2026-10-04T00:00:00"}, "service_date_iso"),
    ({"custom_elements": [{"label": " ", "text": "", "insert_after": "end"}]}, "custom_elements.0.label"),
])
def test_a_bad_body_is_a_422_naming_the_field(client, church, change, field):
    r = call(client, "POST", "/services", church, json={**SERVICE, **change})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"]
    assert service_count() == 0


def test_deleting_twice_is_a_404(client, church):
    made = create(client, church)
    assert call(client, "DELETE", f"/services/{made['id']}", church).status_code == 200
    r = call(client, "DELETE", f"/services/{made['id']}", church)
    assert (r.status_code, error(r)) == (404, ("not_found", GONE))


def test_a_stored_unknown_place_comes_back_as_end_and_survives_a_put(client, church):
    made = create(client, church)
    with session_scope() as s:
        s.get(Service, uuid.UUID(made["id"])).custom_elements = [{"label": "Old", "text": "x", "insert_after": "bogus"}]
    opened = call(client, "GET", f"/services/{made['id']}", church).json()
    assert opened["custom_elements"] == [{"label": "Old", "text": "x", "insert_after": "end"}]
    r = call(client, "PUT", f"/services/{made['id']}", church,
             json={**SERVICE, "custom_elements": opened["custom_elements"]}, **{"If-Match": opened["saved_at"]})
    assert r.status_code == 200 and r.json()["custom_elements"] == opened["custom_elements"]


# --- Idempotency-Key (F §1.6 and its church-scope amendment) ------------------------------

KEY = "6f1c2a52-3a8e-4c3e-9d57-2f0b1f6f1a11"


def test_a_replayed_key_returns_the_first_answer_and_saves_once(client, church):
    first = create(client, church, **{"Idempotency-Key": KEY})
    again = call(client, "POST", "/services", church, json=SERVICE, **{"Idempotency-Key": KEY})
    assert (again.status_code, again.json()) == (201, first)
    assert again.headers["idempotent-replayed"] == "true"
    assert service_count() == 1
    r = call(client, "POST", "/services", church, json={**SERVICE, "occasion": "Other"}, **{"Idempotency-Key": KEY})
    assert (r.status_code, error(r)) == (422, ("idempotency_mismatch",
                                               "This request was already sent with different details."))


def test_a_corrected_retry_needs_a_new_key(client, church):
    gone = {**SERVICE, "hymns": {"opening": {"hymn_id": str(uuid.uuid4()), "title": "x"}}}
    assert call(client, "POST", "/services", church, json=gone, **{"Idempotency-Key": KEY}).status_code == 404
    r = call(client, "POST", "/services", church, json=SERVICE, **{"Idempotency-Key": KEY})
    assert error(r)[0] == "idempotency_mismatch"           # the stored 404 holds the key
    create(client, church, **{"Idempotency-Key": str(uuid.uuid4())})
    assert service_count() == 1


def test_the_same_key_in_two_churches_saves_in_each(client, church, pastor, make_church):
    # The key store is scoped by church (F §1.6 amendment 2026-09-28): the same
    # member, key and body in another church saves there instead of replaying
    # the first church's answer.
    second = make_church(name="Hope", owner_user_id=pastor)
    first = create(client, church, **{"Idempotency-Key": KEY})
    other = call(client, "POST", "/services", second, json=SERVICE, **{"Idempotency-Key": KEY})
    assert other.status_code == 201, other.text
    assert "idempotent-replayed" not in other.headers
    assert other.json()["id"] != first["id"]
    assert call(client, "GET", "/services", second).json()["total"] == 1
    assert call(client, "GET", f"/services/{first['id']}", second).status_code == 404
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_services.py 2>&1 | tail -1
```

**Expected:** `22 failed in <t>s` (no `/services` routes yet, so every request misses).

- [ ] **Step 3 (agent): The response models, the routes, the router**

**Append to `backend/api/schemas.py`:**

````python


# --- slice 5a-2: the archive (5a spec, "Schemas"; GET/POST/PUT/DELETE /services) ---

class DeletedOut(BaseModel):
    """DELETE /services/{id}; 6a and 6b reuse it for their deletes."""

    deleted: Literal[True] = True


class AuthorOut(BaseModel):
    """Who first saved a service: the member's name, else their email (owner decision 5)."""

    id: uuid.UUID
    name: str


class ArchivedHymn(BaseModel):
    """A saved slot's hymn. in_hymnal: the hymn is in the church's hymnal now
    (by its id, else by title and number), with its current title, number and
    hymnal; otherwise the stored snapshot, hymn_id null."""

    hymn_id: Optional[uuid.UUID]
    title: str
    number: Optional[int]
    hymnal: Optional[str]
    in_hymnal: bool


class ArchivedHymns(BaseModel):
    """The three slots of a saved service, each always present (null = empty)."""

    opening: Optional[ArchivedHymn]
    response: Optional[ArchivedHymn]
    closing: Optional[ArchivedHymn]


class ServiceOut(BaseModel):
    """A saved service as the builder opens it (GET, POST and PUT /services)."""

    id: uuid.UUID
    service_date_iso: Optional[str]     # YYYY-MM-DD; null for an undated legacy row
    service_date: str                   # the stored display date ("October 04, 2026")
    occasion: str
    scriptures: list[str]
    hymns: ArchivedHymns
    hymnal: Optional[str]
    liturgy: dict[SectionKey, str]
    sermon_title: str
    selected_ot_ref: str
    selected_nt_ref: str
    include_communion: bool
    custom_elements: list[CustomElementIn]
    created_by: Optional[AuthorOut]     # null when the author's account was removed
    saved_at: str                       # ISO 8601 with "+00:00"; send it back as If-Match


class ServiceSummary(BaseModel):
    """One row of GET /services."""

    id: uuid.UUID
    service_date_iso: Optional[str]
    service_date: str
    occasion: str
    sermon_title: str
    saved_at: str
    created_by: Optional[AuthorOut]
````

**Create `backend/api/routes/services.py`:**

````python
"""The archive: /services (slice 5a spec, API; owner answers 4 and 6, 2026-10-01).

Church-scoped; any member may save, open and delete (owner decision 5). Plain
`def` routes that each make one usecase call (F §2.2 rule 1), with no SQL and
no try/except.
- POST /services: 201 ServiceOut. An Idempotency-Key replays the first answer
  for the same user in the same church (F §1.6 and its church-scope
  amendment): run_idempotent gets church.id.
- PUT /services/{id}: If-Match carries the saved_at last received; 404, then
  422 (If-Match missing or unreadable), then 409, then the body's own errors.
- DELETE /services/{id}: {"deleted": true}; the date's hymn use is then
  recalculated from the services still saved for it (owner answer 6).
- GET /services: 20 a page by default, newest service date first, undated last.
"""
import uuid
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import Response

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.schemas import DeletedOut, Page, ServiceDraft, ServiceOut, ServiceSummary
from usecases import archive

router = APIRouter()


def service_out(record: archive.ServiceRecord) -> ServiceOut:
    return ServiceOut(**asdict(record))


@router.get("/services", response_model=Page[ServiceSummary], responses=error_responses(401, 403, 422, 503))
def list_services(
    church: ActiveChurch = Depends(require_church),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0, le=1_000_000),
) -> Page[ServiceSummary]:
    page = archive.list_services(church.id, limit=limit, offset=offset)
    return Page[ServiceSummary](items=[ServiceSummary(**asdict(item)) for item in page.items], total=page.total,
                                limit=page.limit, offset=page.offset)


@router.get("/services/{service_id}", response_model=ServiceOut, responses=error_responses(401, 403, 404, 422, 503))
def get_service(service_id: uuid.UUID, church: ActiveChurch = Depends(require_church)) -> ServiceOut:
    return service_out(archive.get_service(church.id, service_id))


@router.post("/services", status_code=201, response_model=ServiceOut,
             responses=error_responses(401, 403, 404, 422, 503))
def create_service(
    payload: ServiceDraft,
    user: CurrentUser = Depends(get_current_user),
    church: ActiveChurch = Depends(require_church),
    key: Optional[uuid.UUID] = Depends(idempotency_key()),
) -> Response:
    return run_idempotent(
        user_id=user.id,
        church_id=church.id,
        route="/services",
        key=key,
        payload=payload,
        status_code=201,
        call=lambda: service_out(archive.create_service(church.id, user.id, payload.to_input())),
    )


@router.put("/services/{service_id}", response_model=ServiceOut,
            responses=error_responses(401, 403, 404, 409, 422, 503))
def replace_service(
    service_id: uuid.UUID,
    payload: ServiceDraft,
    church: ActiveChurch = Depends(require_church),
    if_match: Optional[str] = Header(default=None, alias="If-Match"),
) -> ServiceOut:
    return service_out(archive.replace_service(church.id, service_id, payload.to_input(), if_match=if_match))


@router.delete("/services/{service_id}", response_model=DeletedOut,
               responses=error_responses(401, 403, 404, 422, 503))
def delete_service(service_id: uuid.UUID, church: ActiveChurch = Depends(require_church)) -> DeletedOut:
    archive.delete_service(church.id, service_id)
    return DeletedOut()
````

**In `backend/api/main.py`, replace:**

````python
from api.routes import (churches, documents, health, hymnals, hymns, invites, lectionary, liturgy,
                        liturgy_review, me, reference, rubric, scripture)
````

**with:**

````python
from api.routes import (churches, documents, health, hymnals, hymns, invites, lectionary, liturgy,
                        liturgy_review, me, reference, rubric, scripture, services)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(documents.router)

````

**with:**

````python
    app.include_router(documents.router)
    app.include_router(services.router)

````

- [ ] **Step 4 (agent): Regenerate the OpenAPI snapshot and the types**

```bash
.venv/bin/python backend/scripts/export_openapi.py
(cd frontend && npm run gen:api 2>&1 | tail -1)
git diff --stat -- frontend/src/lib/api | tail -1
grep -c '"/services"\|"/services/{service_id}"\|"ServiceOut"\|"ServiceSummary"\|"ArchivedHymn"\|"ArchivedHymns"\|"AuthorOut"\|"DeletedOut"\|"Page_ServiceSummary_"' frontend/src/lib/api/openapi.json
```

**Expected:** `Wrote …/frontend/src/lib/api/openapi.json`; a `🚀 src/lib/api/openapi.json → src/lib/api/schema.d.ts` line; ` 2 files changed, 1499 insertions(+), 24 deletions(-)` (the deletions are git aligning moved neighbors; no schema is removed); `15` (the two paths, the seven schemas and their `$ref`s).

- [ ] **Step 5 (agent): Run the files, the suite, the types**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_services.py backend/tests/test_route_guards.py backend/tests/test_openapi_contract.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_idempotency.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `49 passed in <t>s`; `1329 passed, 11 skipped in <t>s`; ` Test Files  81 passed (81)` and `      Tests  618 passed (618)`; `typecheck 0`, `lint 0`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/api/routes/services.py backend/api/schemas.py backend/api/main.py backend/tests/test_api_services.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "API: /services lists, opens, saves, saves changes to and deletes services (5a-2)" -m "Church-scoped, any member, plain def routes, one usecase call each.
GET /services pages 20 by default, newest service date first. POST is
201 with an optional Idempotency-Key scoped to the church. PUT needs
If-Match (422 when missing or unreadable, 409 conflict with
current_saved_at when stale). DELETE answers {deleted: true}. New
models: DeletedOut, AuthorOut, ArchivedHymn, ArchivedHymns, ServiceOut,
ServiceSummary. OpenAPI snapshot and types regenerated; no frontend code
uses them until 5a-3." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 5: backend **1329 passed, 11 skipped**; frontend **618 in 81**.

### Task 6: Postgres tests, and the owner's steps before `0005` (owner answer 8; S Testing "Postgres", acceptance criteria 7, 8, 11; clarifications 9, 11, 14, 18)

**Files:**
- Create: `backend/tests/test_services_postgres.py`
- Modify: `backend/tests/test_migrations.py`, `backend/migrations/README.md`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_services_postgres.py`:**

````python
"""The archive on real Postgres (slice 5a spec, Testing "Postgres"; acceptance
criteria 7 and 8): concurrent saves on one date record the full union of
their hymns, two PUTs with the same If-Match give one 200 and one 409, the
list's NULLS LAST order, and the owner's read-only counts before 0005
(backend/migrations/README.md).

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs them. The
SQLite fixtures cannot be used here: users and churches come from the repos
on pg_db's engine. Forcing the race: a barrier inside the function the
usecase calls through a module attribute holds each save until both have
written their row (or both are about to lock it), so the advisory lock and
the row lock are what decide the outcome. A save that never reaches the
barrier breaks it after 10 s, and the test errors instead of passing vacuously.
"""
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

import repos.services
from db import SessionLocal, session_scope
from db.models import HymnUsage, Service
from domain_errors import Conflict
from hymn_usage import rebuild_usage_for_date
from repos.churches import create_church
from repos.users import ensure_user
from usecases import archive
from usecases.liturgy import HymnRefData

README = Path(__file__).resolve().parents[1] / "migrations" / "README.md"


@pytest.fixture
def world(pg_db):
    user = ensure_user("pastor@example.com", "Pastor").id
    return user, create_church(name="Grace", timezone="America/New_York", owner_user_id=user)


def hymn(title, number):
    return HymnRefData(None, title, number, None)


def service(day, opening, response, closing):
    return archive.ServiceInput(service_date=day, occasion="", hymns={
        "opening": opening, "response": response, "closing": closing})


def used(church_id, day) -> set[str]:
    with session_scope() as s:
        return set(s.execute(select(HymnUsage.hymn_title).where(
            HymnUsage.church_id == church_id, HymnUsage.date_iso == day.isoformat())).scalars().all())


def together(monkeypatch, module, name):
    """Patch module.name so two callers wait for each other before the real call."""
    real = getattr(module, name)
    barrier = threading.Barrier(2)

    def wrapped(*args, **kwargs):
        barrier.wait(timeout=10)
        return real(*args, **kwargs)

    monkeypatch.setattr(module, name, wrapped)


@pytest.mark.postgres
def test_concurrent_saves_on_one_date_record_the_full_union(world, monkeypatch):
    user, church = world
    together(monkeypatch, archive, "rebuild_usage_for_date")
    for round_ in range(20):
        day = date(2026, 1, 4) + timedelta(weeks=round_)
        early = service(day, hymn("Holy, Holy, Holy", 138), hymn("Be Thou My Vision", 450), hymn("Early", 1))
        late = service(day, hymn("Be Thou My Vision", 450), hymn("Holy, Holy, Holy", 138), hymn("Late", 2))
        with ThreadPoolExecutor(max_workers=2) as pool:
            records = list(pool.map(lambda data: archive.create_service(church, user, data), (early, late)))
        assert len({r.id for r in records}) == 2
        assert used(church, day) == {"Holy, Holy, Holy", "Be Thou My Vision", "Early", "Late"}, round_


@pytest.mark.postgres
def test_a_rebuild_waits_for_another_on_the_same_date_only(world):
    """The advisory lock, deterministically: while one transaction has rebuilt
    a date, a second one's rebuild of that date waits (here it gives up after
    200 ms), and a rebuild of another date does not."""
    _user, church = world
    first = SessionLocal()
    try:
        rebuild_usage_for_date(church, "2026-10-04", session=first)       # holds the lock until it ends
        for date_iso, waits in (("2026-10-04", True), ("2026-10-11", False)):
            second = SessionLocal()
            try:
                second.execute(text("SET LOCAL lock_timeout = '200ms'"))
                if waits:
                    with pytest.raises(OperationalError, match="lock timeout"):
                        rebuild_usage_for_date(church, date_iso, session=second)
                else:
                    assert rebuild_usage_for_date(church, date_iso, session=second) == 0
            finally:
                second.rollback()
                second.close()
    finally:
        first.rollback()
        first.close()


@pytest.mark.postgres
def test_two_puts_with_the_same_if_match_give_one_save_and_one_conflict(world, monkeypatch):
    user, church = world
    record = archive.create_service(church, user, service(date(2026, 10, 4), hymn("Holy, Holy, Holy", 138),
                                                          None, None))
    together(monkeypatch, repos.services, "get_service")

    def put(occasion):
        data = archive.ServiceInput(service_date=date(2026, 10, 4), occasion=occasion)
        try:
            return archive.replace_service(church, record.id, data, if_match=record.saved_at)
        except Conflict as exc:
            return exc

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(put, ("Mine", "Theirs")))
    saved = [r for r in results if isinstance(r, archive.ServiceRecord)]
    conflicts = [r for r in results if isinstance(r, Conflict)]
    assert (len(saved), len(conflicts)) == (1, 1)
    assert conflicts[0].details == {"current_saved_at": saved[0].saved_at}
    monkeypatch.undo()                                   # one more read, without the barrier
    assert archive.get_service(church, record.id).occasion == saved[0].occasion


@pytest.mark.postgres
def test_the_list_puts_blank_and_missing_dates_last_as_on_sqlite(world):
    user, church = world
    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    with session_scope() as s:
        for minutes, (name, date_iso) in enumerate((("old", "2026-09-27"), ("blank", ""), ("new", "2026-10-11"),
                                                    ("none", None), ("same-day-later", "2026-10-11"))):
            s.add(Service(church_id=church, created_by=user, service_date_iso=date_iso, occasion=name,
                          hymns=[], liturgy={}, scriptures=[], saved_at=base + timedelta(minutes=minutes)))
    page = archive.list_services(church, limit=20, offset=0)
    assert [i.occasion for i in page.items] == ["same-day-later", "new", "old", "none", "blank"]


def readme_sql(n: int) -> str:
    """The n-th ```sql block of README "Before 0005_services_extras": 0 is step 2's counts, 1 step 4's check."""
    section = README.read_text(encoding="utf-8").split("\n## Before 0005_services_extras (slice 5a-2)\n", 1)[1]
    return re.findall(r"```sql\n(.*?)```", section, re.S)[n]


@pytest.mark.postgres
def test_the_owner_s_read_only_queries_count_as_the_api_reads(world):
    user, church = world
    archive.create_service(church, user, service(date(2026, 10, 4), hymn("Holy, Holy, Holy", 138), None, None))
    with session_scope() as s:
        for date_iso, hymns in (("2026-09-27", [{"title": "A", "number": 1}]),     # Streamlit's list
                                ("", [{"title": "B"}]), (None, None),                   # undated
                                ("2026-09-20T00:00:00.000Z", []), ("Sept 13", "junk")):
            s.add(Service(church_id=church, service_date_iso=date_iso, occasion="", hymns=hymns, liturgy={},
                          scriptures=[]))
    with session_scope() as s:
        counts = dict(s.execute(text(readme_sql(0))).mappings().one())
        applied = dict(s.execute(text(readme_sql(1))).mappings().one())
    # The 5a-2 save has 3 slots; the other five are old-style; "", NULL and "Sept 13" are undated.
    assert counts == {"version": "0005_services_extras", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0005_services_extras", "new_columns": 2, "new_index": 1}
````

**Append to `backend/tests/test_migrations.py`:**

````python


def test_the_readme_shows_the_0005_preview_exactly():
    """The owner reads backend/migrations/README.md → "Before 0005_services_extras",
    step 3, against the agent's rendering; both must be PREVIEW_0005."""
    readme = (Path(__file__).resolve().parents[1] / "migrations" / "README.md").read_text(encoding="utf-8")
    section = readme.split("\n## Before 0005_services_extras (slice 5a-2)\n", 1)[1]
    step = section.split("\n### Step 3: Read the SQL the upgrade will run\n", 1)[1].split("\n### ", 1)[0]
    block = "BEGIN;" + step.split("\n```\nBEGIN;", 1)[1].split("\n```", 1)[0]   # the bare fence
    assert block.splitlines() == PREVIEW_0005
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_services_postgres.py 2>&1 | tail -1
```

**Expected:** `1 failed, 24 passed, 8 skipped in <t>s`: `test_the_readme_shows_the_0005_preview_exactly` (the README has no "Before 0005_services_extras" section yet); the five Postgres tests and three in `test_migrations.py` skip without `TEST_DATABASE_URL` (with a local Postgres, `test_the_owner_s_read_only_queries_count_as_the_api_reads` fails too, for the same reason).

- [ ] **Step 3 (agent): The owner's steps in the migrations README**

**Append to `backend/migrations/README.md`:**

````markdown

## Before 0005_services_extras (slice 5a-2)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0005_services_extras` when the slice 5a-2 PR merges. First, as the owner
decided on 2026-10-01: a backup, read-only counts of the saved services, and
a look at the SQL. No Streamlit check (Streamlit is retired). Nothing here
changes data. The agent guides the owner one step at a time and records the
results in `docs/ops-runbook.md` → "Slice 5a-2 record", never with an email
address, a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL.

### Step 2: Count the saved services (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run:

```sql
-- Read-only: what the archive holds before 0005. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       count(*) AS services,
       count(*) FILTER (WHERE coalesce(substr(service_date_iso, 1, 10), '')
                              !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$') AS undated,
       count(*) FILTER (WHERE CASE WHEN json_typeof(hymns) = 'array'
                                   THEN json_array_length(hymns) = 0
                                        OR EXISTS (SELECT 1 FROM json_array_elements(hymns) AS e
                                                   WHERE json_typeof(e) <> 'object' OR e ->> 'slot' IS NULL)
                                   ELSE true END) AS old_style_hymn_lists
FROM services;
```

One row. Expected before the merge: `version` is `0004_invites_reusable`
(anything else: stop); `services` is the number of saved services in all
churches; `undated` is how many have no readable date (the list shows them
last); `old_style_hymn_lists` equals `services`, because every service so
far was saved by Streamlit, whose hymn lists have no slots (they are read
by position).

### Step 3: Read the SQL the upgrade will run

The agent renders it from the PR's code without connecting to any database
(from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0004_invites_reusable:0005_services_extras --sql 2>/dev/null | grep -v -e '^--' -e '^$'
```

Expected, exactly (`backend/tests/test_migrations.py` pins it):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE services ADD COLUMN custom_elements JSON;
ALTER TABLE services ADD COLUMN hymnal VARCHAR;
CREATE INDEX ix_services_church_date ON services (church_id, service_date_iso);
UPDATE alembic_version SET version_num='0005_services_extras' WHERE alembic_version.version_num = '0004_invites_reusable';
COMMIT;
```

Two new empty columns and one index, in one transaction: no row is copied,
changed or deleted. If another connection holds a lock on `services` for
more than 5 s, the deploy fails and the previous release keeps serving; run
the deploy again.

### Step 4: After the deploy (read-only)

SQL Editor:

```sql
-- Read-only: is 0005 applied? Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'services'
           AND column_name IN ('custom_elements', 'hymnal')) AS new_columns,
       (SELECT count(*) FROM pg_indexes
         WHERE schemaname = 'public' AND indexname = 'ix_services_church_date') AS new_index;
```

Expected: `0005_services_extras`, `2`, `1`. Then step 2's query again: the
same `services`, `undated` and `old_style_hymn_lists` (no row changed; the
app cannot save a service until 5a-3).

### Reverting 5a-2

The schema stays at `0005_services_extras`: its columns are nullable and the
code before 5a-2 ignores them. Revert the merge commit, then restore
`backend/migrations/versions/0005_services_extras.py` and the two `Service`
columns and the index in `backend/db/models.py` from the merge commit in the
same PR, so Railway's `alembic upgrade head` still finds the database at
head and `alembic check` stays clean. Never `alembic downgrade` production
for this.
````

- [ ] **Step 4 (agent): Run the files, the Postgres tests if a local Postgres is at hand, the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_services_postgres.py backend/tests/test_slice1_docs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `31 passed, 8 skipped in <t>s`; `1330 passed, 16 skipped in <t>s`. With a local, throwaway Postgres: `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `16 passed, 1330 deselected`; without one, say so (CI's `backend-postgres` job runs them).

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/tests/test_services_postgres.py backend/tests/test_migrations.py backend/migrations/README.md
git commit -q -m "Postgres tests for the archive, and the owner's steps before 0005 (5a-2; owner answer 8)" -m "On Postgres: concurrent saves on one date record the full union (20
rounds, shared hymns in opposite slots), the advisory lock makes a
second rebuild of a date wait and leaves other dates alone, two PUTs with
the same If-Match give one save and one 409, and the list puts blank and
missing dates last. migrations/README.md gains 'Before
0005_services_extras': the backup, the read-only counts, the SQL preview
and the after-deploy check; both queries run in the Postgres tests and
the preview is pinned to the rendered SQL. Reverting 5a-2 keeps 0005." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 6: backend **1330 passed, 16 skipped**; frontend **618 in 81**.

### Task 7: Docs: S's amendment and the manual-verification items (owner answers 2026-10-01/02; clarification 19)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`, `docs/manual-verification.md`

- [ ] **Step 1 (agent): Write the docs**

**Append to `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`:**

````markdown

## Amendment 2026-10-02: 5a-2 as planned (saving on the server, `0005_services_extras`)

Plan: `docs/superpowers/plans/2026-10-02-slice-5a2-saving.md`. The owner's answers of 2026-10-01 stand (answer 6: deleting a service recalculates that date's hymn use; answer 8: a backup, read-only counts and the `--sql` preview before `0005` runs; no Streamlit check). Where this spec says otherwise, 5a-2 does this:

1. **Hymn use follows the archive.** `hymn_usage.rebuild_usage_for_date` replaces a date's rows with the union of the services saved for it, deduped by `hymn_search.usage_key(title)` (the title alone, slice 3a's key; the first saved number and title are kept). Saving rebuilds the saved date; a PUT that moves a service rebuilds both dates (in date order, so two rebuilds never deadlock); deleting rebuilds the date the service leaves. An undated service changes no hymn use when deleted. A rebuild also removes rows nothing saved backs (Streamlit's Prepare, imported history) for that date. Behavior change 4, open question 1 and acceptance criterion 7's "a delete leaves `hymn_usage` unchanged" are superseded.
2. **The idempotency store is scoped by church.** `run_idempotent` takes `church_id` and keys entries by (user, church, method, route, key) (F §1.6 amendment 2026-09-28); `POST /services` passes the active church, `POST /churches` passes none.
3. **Code layout.** The archive's queries are in a new `backend/repos/services.py`; `service_archive.py` (Streamlit's) is unchanged and slice 7 deletes it. `service_output` gains `normalize_date_iso`, `coerce_number`, `StoredHymn`, `stored_hymn_entries`, `slot_map(raw)` (it reads the stored value, so it can tell a slotted list from a compacted one) and `stored_hymns`; `repos/hymns.py` gains `find_hymns_by_titles`. No `test_services_streamlit_compat.py` (Streamlit retired).
4. **API shapes.** `GET /services` pages 20 by default (`limit` 1-200, `offset` 0-1 000 000). `ServiceOut.hymns` is an object `ArchivedHymns {opening, response, closing}` (each `ArchivedHymn` or null, always present), not a dict. `ServiceOut.saved_at` and `ServiceSummary.saved_at` are ISO 8601 strings in UTC ending `+00:00`; `If-Match` accepts that value quoted, with `W/`, with `Z` or in another offset. A request body that fails validation is a 422 before the PUT check order starts; the order applies to the usecase's checks.
5. **What is saved is what was sent** (owner answer 4): the server stores the Benediction text and the communion setting it receives; 5a-3's Save card sends a default-following Benediction as text, so a saved service keeps it.
6. **Hymn use is not recorded until 5a-3.** Nothing in the app saves a service before 5a-3's Save card; until then the archive and the hymn-use rows change only through direct API calls.
7. **Reverting 5a-2** keeps the schema at `0005_services_extras` (the revert PR restores the revision file and the model columns), so Railway's `alembic upgrade head` still succeeds; production is never downgraded for it.
````

**Append to `docs/manual-verification.md`:**

````markdown

Slice 5a-2 (saving on the server and `0005_services_extras`) changes nothing
on screen; saving from the app comes with 5a-3. Its items are the owner's
production steps around the merge (`backend/migrations/README.md` →
"Before 0005_services_extras") and a short phone check that the builder works
as before; the results go into `docs/ops-runbook.md` → "Slice 5a-2 record".

- [ ] (owner, before the 5a-2 merge) **9.** A green `db-backup` run; the read-only counts (version `0004_invites_reusable`, saved services, undated, old-style hymn lists); the SQL preview read: two `ADD COLUMN` lines and one `CREATE INDEX` between `BEGIN;` and `COMMIT;`, under the 5 s lock timeout.
- [ ] (owner, after 5a-2) **10.** The after-deploy query shows `0005_services_extras`, `2`, `1`, and the counts are unchanged.
- [ ] (owner, after 5a-2) **11.** On the phone the builder works as before: **2 Hymns** lists the hymnal, and **4 Review & send** still downloads the bulletin copy. Nothing new shows; "Saving services to the archive is coming soon." is still there.
````

- [ ] **Step 2 (agent): Check the docs tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
grep -c "—" <(git diff -U0 -- docs | grep '^+' | grep -v '^+++')
.venv/bin/python -m pytest -q | tail -1
git diff --stat | tail -1
```

**Expected:** `89 passed in <t>s`; `4`; `0` (no em dash added); `1330 passed, 16 skipped in <t>s`; ` 2 files changed, 22 insertions(+)`.

- [ ] **Step 3 (agent): Commit**

```bash
git add docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md docs/manual-verification.md
git commit -q -m "Docs: slice 5a-2 amendment and manual-verification items (owner answers 2026-10-01/02)" -m "The 5a spec gains 'Amendment 2026-10-02: 5a-2 as planned': hymn use
follows the archive (save, re-date and delete rebuild their dates;
superseding open question 1), the church-scoped idempotency store, the
repo layout, the API shapes, what is sent is what is stored (owner
answer 4), no hymn use until 5a-3, and the revert that keeps 0005.
docs/manual-verification.md gains items 9-11 under 'Slice 5a'." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 4 (controller): Review the batch (T1-T7) and backup push**

One review of the whole batch: the revision is expand-only and its `--sql` is exactly clarification 14's eight lines; the store key has the church and `POST /churches` behaves as before; a save writes F §6.2's shape and the Benediction and communion as sent; the rebuild's union, dedupe, lock and sorted inserts, and its three callers (save, re-dating PUT both dates, delete; none for an undated delete); the PUT check order and messages exactly clarification 5; `get_service`'s normalization as clarification 10, never raising on stored data; every query church-filtered and every route behind `require_church`; no FastAPI below the API; logs without text; the README's queries are read-only and match the tests; no frontend source changed. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

Counts after Task 7: backend **1330 passed, 16 skipped**; frontend **618 in 81**.

### Task 8: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
git merge-base --is-ancestor 2cd4b79 origin/main; echo "runbook commit on main: $?"
ls backend/migrations/versions | grep -c '^0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `runbook commit on main: 0` or `1` (note which: Step 3's path list depends on it); `5`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 8)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner. **If `main` gained a migration** (the count of revisions on `origin/main` is not 4: `git ls-tree --name-only origin/main backend/migrations/versions/ | grep -c '/0'`), stop: `0005` must be renumbered onto the new head (F §3.5 chain rule) before anything else, and the owner told.

- [ ] **Step 2 (agent): Both suites, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error")
```

**Expected:** `1330 passed, 16 skipped in <t>s`; ` Test Files  81 passed (81)` and `      Tests  618 passed (618)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s` and no `Error` (a font `Failed to fetch` only: say so and rely on CI). With a local, throwaway Postgres also `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres | tail -1` → `16 passed, 1330 deselected`.

- [ ] **Step 3 (agent): The API files match, the preview, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0004_invites_reusable:0005_services_extras --sql 2>/dev/null | grep -v -e '^--' -e '^$')
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/usecases/archive.py backend/repos/services.py backend/hymn_usage.py backend/service_output.py; echo "imports grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- frontend/src ':!frontend/src/lib/api/openapi.json' ':!frontend/src/lib/api/schema.d.ts' backend/service_archive.py backend/migrations/env.py .github frontend/package.json frontend/package-lock.json app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); the eight preview lines of clarification 14 exactly; `imports grep exit 1`; exactly these 27 paths (plus `M	docs/ops-runbook.md` when Step 1 printed `runbook commit on main: 1`):
```
M	backend/api/idempotency.py
M	backend/api/main.py
A	backend/api/routes/services.py
M	backend/api/schemas.py
M	backend/db/models.py
M	backend/hymn_usage.py
M	backend/migrations/README.md
A	backend/migrations/versions/0005_services_extras.py
M	backend/repos/hymns.py
A	backend/repos/services.py
M	backend/service_output.py
M	backend/tests/test_api_app.py
A	backend/tests/test_api_services.py
M	backend/tests/test_idempotency.py
M	backend/tests/test_migrations.py
M	backend/tests/test_no_streamlit_in_core.py
M	backend/tests/test_schema_check.py
M	backend/tests/test_service_output.py
A	backend/tests/test_services_postgres.py
A	backend/tests/test_usage_rebuild.py
A	backend/tests/test_usecase_archive.py
M	backend/usecases/archive.py
M	docs/manual-verification.md
A	docs/superpowers/plans/2026-10-02-slice-5a2-saving.md
M	docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
```
`0`; the subjects oldest first: the runbook commit (`Runbook: default Benediction skipped by Review service (PR #42, owner's phone check)`) unless it is on `main`, the plan's (`WIP plan: slice 5a-2` …, `Plan: slice 5a-2, saving backend and migration (owner answers 2026-10-01/02)`), then T1-T7's seven subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** one `✓ Logged in` line; `[]`. Send the owner exactly this, and wait for a clear yes:

> Slice 5a-2 (saving, on the server side) is verified on this machine: backend 1330 passed, 16 skipped (1263 and 11 before; the 5 new skipped ones are database-concurrency tests that CI runs on Postgres); frontend 618 tests in 81 files, unchanged; typecheck, lint and the production build are clean. It adds the /services routes (save, list, open, save changes, delete) and one database change, migration 0005: two new empty columns and an index. Nothing changes on screen yet; the Save button and the Services page come in 5a-3. Before it merges I will ask you for the backup, the counts and a look at the SQL, one at a time. May I open the pull request as a **draft** titled "Slice 5a-2: saving backend and migration 0005", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/slice5a2-pr-body.md" <<'BODY'
Slice 5a-2: saving on the server, and migration 0005_services_extras (the second of three 5a PRs; owner answers of 2026-10-01/02). Plan: docs/superpowers/plans/2026-10-02-slice-5a2-saving.md. Nothing changes on screen; 5a-3 adds the Save card and the Services page.

- Migration 0005_services_extras (expand-only): services.custom_elements JSON NULL, services.hymnal VARCHAR NULL, index ix_services_church_date. No backfill. env.py's 5 s lock timeout applies. Before the merge: a backup, read-only counts and the SQL preview (backend/migrations/README.md, "Before 0005_services_extras").
- /services (church-scoped, any member): GET (20 a page, newest service date first, undated last), GET one (stored data normalized: hymns by slot or position, resolved by id or by title and number), POST (201; Idempotency-Key scoped to the church, F 1.6 amendment), PUT (If-Match; 404, 422, 409 conflict in the spec's order; row lock), DELETE ({deleted: true}).
- Hymn use follows the archive (owner answer 6): every save rebuilds that date from all services saved for it (deduped by the title-only usage key); a re-dating save rebuilds both dates; a delete rebuilds the date it leaves. One transaction; a Postgres advisory lock per church and date.
- A save stores what is sent: the Benediction text and communion setting (owner answer 4).
- repos/services.py for the queries; service_archive.py (Streamlit's) untouched.
- OpenAPI snapshot and types regenerated; no frontend code changed.

Tests: backend 1263 → 1330 passed, 11 → 16 skipped; frontend 618 → 618 in 81 → 81 files

After merge (Task 9): the owner's after-deploy check (one read-only query) and a short phone check, then a "Slice 5a-2 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 5a-2: saving backend and migration 0005" \
  --body-file "<scratch>/slice5a2-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1330 passed, 16 skipped`, backend-postgres `16 passed, 1330 deselected` (after its `alembic upgrade head`, `alembic check`, `downgrade base`, `upgrade head` steps, now through `0005`), frontend `618 passed` in 81 files. Then send: "PR #<N> is green: backend 1330 passed, 16 skipped; the Postgres job ran the migration up, down and up again and passed its 16 tests; 618 frontend tests in 81 files. May I mark it ready for review? Merging stays with you, after the backup, the counts and the SQL check." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_migrations.py` (the `0005` tests), `test_schema_check.py`, `test_api_app.py`, CI's alembic cycle | T1 |
| `test_idempotency.py`, `test_api_churches.py` | T2 |
| `test_service_output.py`, `test_usage_rebuild.py`, `test_hymn_usage*.py` | T3 |
| `test_usecase_archive.py`, `test_no_streamlit_in_core.py`, `test_hymns_repo.py` | T4 |
| `test_api_services.py`, `test_route_guards.py`, `test_openapi_contract.py` | T5 |
| `test_services_postgres.py`, `test_migrations.py`'s README pin | T6 |
| `test_slice1_docs.py`, `test_docs.py` | T7 |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, 5a-2 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1330 passed, 16 skipped`; frontend `618 passed` in 81 files.

### Task 9: Before the merge (backup, counts, SQL), the merge, the after-deploy checks, the record (OWNER + agent)

The owner's steps go **one at a time** (send one, wait for the report or "next"). The agent writes each result into `<scratch>/slice5a2-t9-results.md` (not committed). Record numbers and what the screens showed, never a token, an email address, a church id or a database URL. The queries are the ones in `backend/migrations/README.md` → "Before 0005_services_extras" (pinned by T6's tests); copy them from there.

**Files:** Modify (the records PR, Step 9): `docs/ops-runbook.md`: insert `### Slice 5a-2 record` right before `## Backups` (after the last `###` record above it; today "Review service: default Benediction skipped (record)"). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER, then agent): The backup**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send:

> PR #<N> (slice 5a-2) is ready and green. Before it merges you asked for three checks; here is the first. May I start a fresh database backup now (the db-backup workflow on main, about a minute)? Nothing else happens yet.

On a clear yes:

(not replayed)
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

> Second check: one read-only query; it only counts. Open Supabase → your project → SQL Editor → New query, paste the query below, and press Run. You should see one row with four numbers. Please tell me what each column shows: version, services, undated, old_style_hymn_lists.

**Expected:** `version` `0004_invites_reusable`; `services` the number of saved services in all churches; `undated` how many have no readable date; `old_style_hymn_lists` equal to `services`. Record the four values. If `version` is not `0004_invites_reusable`, or `old_style_hymn_lists` differs from `services`, stop and tell the owner what it means before going on.

- [ ] **Step 3 (agent → OWNER): The SQL the migration will run**

(not replayed)
```bash
git fetch origin && git status -sb | head -1
(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0004_invites_reusable:0005_services_extras --sql 2>/dev/null | grep -v -e '^--' -e '^$')
```

**Expected:** the branch even with `origin/claude/slice-2-plan-4q33le` (the PR's code); the eight lines of clarification 14 exactly. Send them in a code block with:

> Third check: these are the eight lines of SQL the migration will run on the database when the PR merges, rendered from the PR's code without touching the database. In plain words: start one transaction; give up after 5 seconds if the services table is busy (the old version then keeps running and we retry); add two empty columns to the saved services (custom elements and hymnal); add an index for listing services by date; note the new version; finish. No row is copied, changed or deleted. Does that look right to you?

Record the owner's answer.

- [ ] **Step 4 (agent → OWNER): Ask to merge, then merge**

Send: "The backup is green, the counts are recorded and you have read the SQL. May I merge PR #<N> with a merge commit? Railway then runs the migration before the new version starts; I will check it and then ask you for one more read-only query and a short phone check." On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both.

- [ ] **Step 5 (agent, then OWNER): The deploy and the after-deploy check**

About three minutes after the merge (not replayed):

```bash
curl -s https://church-production-74ca.up.railway.app/health/ready; echo
curl -s https://church-production-74ca.up.railway.app/openapi.json | grep -c '"/services/{service_id}"'
curl -s -o /dev/null -w '%{http_code}\n' https://church-production-74ca.up.railway.app/services
```

**Expected:** `{"ok":true,"db":"ok"}` (in production this answers 503 `schema_behind` while the database is behind the release, so `ok` means `0005` is applied and the new release is live); `1`; `401` (the route exists and wants a sign-in). If `/openapi.json` still has no `/services/{service_id}`, wait a minute and retry; after ten minutes, ask the owner to open Railway → the API service → Deployments and read the newest deployment's status. Then send, with README step 4's query in a code block, and step 2's query again:

> The new version is live. One more read-only check: in the SQL Editor, run the first query below; it should show 0005_services_extras, 2 and 1. Then run the counting query from before again; the numbers should be the same as last time. Also, if you have Railway open: the newest deployment's logs should include a line "Running upgrade 0004_invites_reusable -> 0005_services_extras". What do you see?

Record the values. Different counts, or a version other than `0005_services_extras`: stop and look before anything else (the release can stay; nothing in the app writes services yet).

- [ ] **Step 6 (OWNER, then agent): The phone check (manual-verification item 11)**

> Last step, on your phone: open https://worship-service-builder.vercel.app (signed in, in your church). Go to **2 Hymns**: does the hymnal list as before? Then **4 Review & send**: tap **Download bulletin copy**; does the file still download and open? The page should still say "Saving services to the archive is coming soon."; saving from the app comes with the next PR.

- [ ] **Step 7 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/slice5a2-t9-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 8 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^### \|^## Backups$' docs/ops-runbook.md | tail -3
```

**Expected:** `Fast-forward` (or `Already up to date.`); the last `###` record headings, then `## Backups`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Slice 5a-2 record

Slice 5a-2 (saving on the server: `/services` to save, list, open, save
changes to and delete services, with hymn use rebuilt for the date on every
save and delete; migration `0005_services_extras`) merged as PR #<N>, the
second of three 5a PRs (owner answers of 2026-10-01/02). Nothing changed on
screen; the Save card and the Services page come in 5a-3, and hymn use is
recorded from then on. Production moved from `0004_invites_reusable` to
`0005_services_extras` (two empty nullable columns on `services` and the
index `ix_services_church_date`). The steps follow
`backend/migrations/README.md` → "Before 0005_services_extras". No token,
email address, church id or database URL is recorded here.

| Step | Result | Date |
|---|---|---|
| 1. Backup | `db-backup` run <run URL>: success, artifact `db-backup` (<bytes> bytes, encrypted) | <date> |
| 2. Counts before (SQL Editor, read-only) | version `0004_invites_reusable`; <n> saved services; <n> undated; <n> old-style hymn lists | <date> |
| 3. SQL preview | Rendered from the PR's code without a database: the eight lines of the README (two `ADD COLUMN`, one `CREATE INDEX`, under the 5 s lock timeout); read by the owner: <answer> | <date> |
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`; `/openapi.json` lists `/services/{service_id}`; `GET /services` signed out: 401. <Railway log line "Running upgrade 0004_invites_reusable -> 0005_services_extras" seen by the owner. / Not checked.> | <date> |
| 4. After the deploy (read-only) | `0005_services_extras`, `2`, `1`; counts again: <unchanged / …> | <date> |
| Phone check | <Hymns listed as before; the bulletin copy downloaded and opened; the archive note still showed. / …> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: 5a-3 (the Save card, the Services page; hymn use recorded from its Save), the printed bulletin (`docs/superpowers/specs/2026-10-02-printed-bulletin-idea.md`), Voices of the Church, 6a. Still open: the screen-reader copy for "Revise the other prayers", first-line matching research (Hymnary.org), the NUL-character 500 outside `/documents`, and the two slice 1 test churches (kept for now, owner) | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Then:

(not replayed)
```bash
sed -n '/^### Slice 5a-2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 5a-2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 5a-2 record (backup, counts, SQL preview, merge, migration 0005)" -m "Records slice 5a-2 (PR #<N>): the backup, the read-only counts and
the SQL preview before the merge, the merge and the deploy of
0005_services_extras, the after-deploy check and the owner's phone check.
No token, email, church id or database URL is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 9 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 5a-2 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes:

(not replayed)
```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 5a-2 record" \
  --body "Records slice 5a-2 (PR #<N>) in docs/ops-runbook.md → Slice 5a-2 record: the backup, the counts and the SQL preview before the merge, the deploy of 0005_services_extras and the owner's checks. No token, email, church id or database URL is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Slice 5a-2 is live and recorded; <n> follow-ups. Next: the 5a-3 plan (the Save card and the Services page)."

- [ ] **Step R (only if the release must come out): Revert, keeping `0005`**

On the owner's yes for each outward command (clarification 18; README "Reverting 5a-2"): a branch `claude/revert-slice-5a2` from `origin/main`; `git revert -m 1 --no-commit <merge sha>`; then put back the schema and its tests from the merge commit, `git checkout <merge sha> -- backend/migrations/versions/0005_services_extras.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py`; a commit "Revert slice 5a-2 (PR #<N>), keeping migration 0005" with the trailer; both suites (`1267 passed, 11 skipped`: the baseline plus T1's three and T6's README test; `618 passed` in 81); a PR, CI, and the merge on the owner's yes; record it in the 5a-2 record. Never `alembic downgrade` production for this: the database stays at `0005_services_extras`, which the older code ignores.

Expected counts after this task: backend `1330 passed, 16 skipped` on `main`; frontend `618 passed` in 81 files. The records PR adds no test.

---
## Build notes

**How this plan was written (2026-10-02).** Each task's code was built and run in a throwaway worktree of `2cd4b79` (the repo's `.venv`, the checkout's `node_modules`, and a local Postgres 16 started for the `postgres` marker; CI uses 17), then the directives were generated from those files and replayed onto a fresh detached worktree of `2cd4b79` by a script that applies every Create, Append and Replace directive of T1-T7 in order and runs each step's commands. While building:
- **The advisory lock needed a deterministic test.** Two saves released together at a barrier recorded the full union even with the lock removed (each `DELETE` ran before the other transaction committed), so the 20-round union test alone could not show the lock's worth. `test_a_rebuild_waits_for_another_on_the_same_date_only` holds the lock in one transaction and gives a second rebuild of the same date a 200 ms `lock_timeout`: it times out with the lock and does not without it (checked by removing the lock). The 20-round test stays as the spec's no-deadlock, no-`IntegrityError` check. The PUT race test fails (two saves, no conflict) with `with_for_update()` removed (checked).
- **The PUT race test's last read undoes its patch** (`monkeypatch.undo()`): a lone call through the two-party barrier in `repos.services.get_service` would wait 10 s and break it.
- **`slot_map` reads the raw stored value.** A 5a-2 row's empty slot (`title: ""`) parses to `None`, so deciding "every entry has a slot" on the parsed entries would have sent 5a-2's own rows down the positional path.
- **The README preview test splits on the 5a-2 section first:** the 1a runbook in the same README has its own "Read the SQL the upgrade will run" step.
- **The author's name in the API test is "Pat Tor":** `get_current_user` refreshes the users row from the sign-in token (`tests.jwt_helpers`).
- **CI's Postgres cycle by hand:** on the local Postgres, `alembic upgrade head`, `check`, `downgrade base`, `upgrade head`, then `downgrade 0004_invites_reusable`, `upgrade head`, `check`: all clean (`No new upgrade operations detected.`).
- **No frontend source changed;** the `openapi.json` diff shows 24 deletions only because git aligns the inserted schemas against moved neighbors.

**Replay of the finished plan (2026-10-02).** The directives of T1-T7 were applied in order onto a fresh detached worktree of `2cd4b79` (symlinked `.venv`, hard-linked `frontend/node_modules`), running each step's commands, with `TEST_DATABASE_URL` pointing at the local Postgres for an extra `-m postgres` run after each suite:
- All 40 directives applied (T1 9, T2 6, T3 8, T4 7, T5 5, T6 3, T7 2); every Replace anchor occurred exactly once, and every Append landed on the file as the task before left it. After T7 the tree equaled the build worktree's (`diff -r` of `backend`, `frontend/src` and `docs` but the plan: empty).
- Every "see it fail" output matched as quoted (T1 `14 failed, 52 passed, 4 skipped`; T2 `1 failed, 15 passed`; T3 `5 failed, 6 passed` and the collection error; T4 `25 failed, 2 passed`; T5 `22 failed`; T6 `1 failed, 24 passed, 8 skipped`), and every count matched the table: backend 1266, 1267, 1283, 1307, 1329 (11 skipped), 1330 (16 skipped); the Postgres-marked runs `11 passed, <n> deselected` through T5 and `16 passed, 1330 deselected` from T6; the offline SQL `8` lines; the OpenAPI change `2 files changed, 1499 insertions(+), 24 deletions(-)` and `15`; frontend `618` in 81, typecheck 0, lint 0 after T5; T7 `89 passed`, `4`, `0`, `2 files changed, 22 insertions(+)`; `imports grep exit 1`.
- **Step R checked:** in the replay worktree, `git revert --no-commit` of T1-T7 and `git checkout` of Step R's six files from the tip gave `1267 passed, 11 skipped` and typecheck 0.
- Not run while planning: the production build (T8 runs it in the real checkout; no frontend source changed), the pushes, the PR and CI, the backup, the owner's queries on production, the merge and the deploy.

## Spec coverage

| Owner answer or S item | Task(s) and tests |
|---|---|
| 1. Three PRs; this one is the saving backend and `0005` alone | the plan's scope; T8 Step 3 (27 paths, no frontend source); clarification 1 |
| 4. A saved service keeps its Benediction and communion as saved | T4 `test_create_writes_three_slots_the_display_date_and_the_8_sections` (the Benediction and `include_communion` stored as sent), `test_replace_is_a_full_replace_that_keeps_the_author_and_moves_saved_at`; T5 `test_create_open_list_replace_delete` |
| 6. Delete recalculates a date's hymn use; save records the date's union, deduped by the title-only key | T3 `test_a_date_s_rows_are_the_union_of_its_saved_services`, `test_rows_nothing_saved_backs_are_replaced`, `test_a_date_with_no_service_left_has_no_rows`, `test_titles_dedupe_by_the_usage_key_and_keep_the_first_saved`, `test_malformed_legacy_rows_are_skipped_not_raised`, `test_only_that_date_and_that_church`, `test_only_a_yyyy_mm_dd_date_is_accepted`; T4 `test_saving_records_the_date_s_union_and_replaces_prepared_rows`, `test_deleting_recalculates_the_date_from_the_services_left`, `test_deleting_an_undated_service_changes_no_hymn_use`, `test_moving_a_service_to_another_date_rebuilds_both_dates`, `test_a_failed_usage_rebuild_rolls_the_save_back`; T5 `test_hymn_use_follows_save_and_delete`; T6 `test_concurrent_saves_on_one_date_record_the_full_union`, `test_a_rebuild_waits_for_another_on_the_same_date_only` |
| 8. Backup, read-only counts, the `--sql` preview first; no Streamlit check | T1 `test_offline_sql_for_0005_is_two_column_adds_and_one_index_under_the_timeouts`; T6 the README section, `test_the_readme_shows_the_0005_preview_exactly`, `test_the_owner_s_read_only_queries_count_as_the_api_reads`; T9 Steps 1-3 and 5 |
| 9. Reviewer notes not saved | clarification 17 (`ServiceDraft` `extra="forbid"`; T5 `test_a_bad_body_is_a_422_naming_the_field` "extra") |
| F §1.6 church-scope amendment | T2 `test_keys_are_scoped_per_church`; T5 `test_the_same_key_in_two_churches_saves_in_each`, `test_a_replayed_key_returns_the_first_answer_and_saves_once`, `test_a_corrected_retry_needs_a_new_key` (S acceptance criterion 9, server side) |
| S API rows, messages, paging; F §1.4 | T5 `test_create_open_list_replace_delete`, `test_malformed_ids_and_paging_are_422` (6 cases), `test_a_bad_body_is_a_422_naming_the_field` (4 cases), `test_deleting_twice_is_a_404`; T4 `test_the_list_is_newest_service_date_first_with_undated_last`; T6 `test_the_list_puts_blank_and_missing_dates_last_as_on_sqlite` |
| S "Check order for `PUT`", F §1.7 (acceptance criterion 8) | T4 `test_the_check_order_is_404_then_422_then_409_then_the_input`, `test_if_match_accepts_the_saved_at_in_any_spelling` (5 cases); T5 `test_put_check_order_and_messages`; T6 `test_two_puts_with_the_same_if_match_give_one_save_and_one_conflict` |
| S acceptance criterion 6 (what a save writes; F §6.2) | T3 `test_stored_hymns_writes_three_slot_entries_never_null_titles`; T4 `test_create_writes_three_slots_the_display_date_and_the_8_sections`, `test_a_null_hymnal_is_stored_as_the_church_s_effective_hymnal` |
| S acceptance criterion 10 (members allowed, isolation, another church's hymn id) | T5 `test_any_member_may_save_replace_and_delete` (member, admin; the owner in the others), `test_every_route_is_church_isolated` (`assert_church_isolated` on GET list, GET one, POST, DELETE; PUT on B's id 404), `test_another_church_s_hymn_id_is_a_404_naming_the_slot_and_writes_nothing`; T4 `test_another_church_s_service_is_not_found`, `test_a_hymn_the_church_lacks_or_a_blank_label_writes_nothing`; `test_route_guards.py` unchanged and passing |
| S acceptance criterion 11 (`0005` up, down, single head, `alembic check`, inserts without the columns) | T1 `test_0005_adds_two_nullable_columns_and_the_date_index_and_keeps_rows`, `test_0005_downgrade_gives_back_the_0004_services_table`, `test_head_is_0005_services_extras`, `test_schema_diff_at_baseline_lists_exactly_the_0004_and_0005_changes`; existing `test_upgrade_head_on_empty_sqlite_matches_the_models`, `test_downgrade_base_then_upgrade_head`, `test_there_is_a_single_head`; CI `backend-postgres` alembic cycle |
| S acceptance criterion 12 (opening: legacy lists, resolution and tie-break, snapshots, filtering, unknown places, dates) | T3 `test_normalize_date_iso_keeps_a_real_date_and_recovers_a_time_part`, `test_stored_hymn_entries_never_raise_and_keep_every_entry`, `test_slot_map_by_slot_or_by_position`, `test_coerce_number`; T4 `test_a_compacted_streamlit_list_maps_by_position_and_resolves_by_title_and_number`, `test_title_matches_prefer_the_entry_s_hymnal_then_the_service_s_then_the_church_s`, `test_duplicate_titles_resolve_the_same_way_every_time`, `test_a_stored_id_resolves_to_the_hymn_s_current_title`, `test_liturgy_custom_elements_and_dates_are_normalized`, `test_an_element_with_an_unknown_place_survives_open_then_save`; T5 `test_a_stored_unknown_place_comes_back_as_end_and_survives_a_put` |
| S "Data access and tenancy" (one transaction; logs without text) | T4 `test_a_failed_usage_rebuild_rolls_the_save_back`, `test_saving_logs_ids_and_counts_never_text` |
| Layering (no FastAPI or Streamlit below the API) | T4 `test_no_streamlit_in_core.py` (`repos.services`, `hymn_usage` added) and the imports grep |
| OpenAPI and types regenerated | T5 Step 4; T8 Step 3; `test_openapi_contract.py` |

S items **not** in 5a-2 (owner answer 1): the Review step's Save card, conflict dialog and editing banner; the Services page; `serviceToDraft`, the final `draftToServicePayload`, `save-key.ts`, the draft version bump, `"review"` in `SHIPPED_STEPS`, the summary's archive half; `useSaveService`, `useServices`, `useDeleteService`, `useOpenService`; `test_services_streamlit_compat.py` (Streamlit retired); `service_archive.py`'s new functions (replaced by `repos/services.py`, clarification 15).

## Questions for the owner

Your answers of 2026-10-01 and 2026-10-02 (1-9) are binding and already in the plan. These are the choices the plan makes where you did not say; each is written as recommended. The plan is built as recommended.

1. **Nothing new on screen in this PR** (clarifications 1, 16): it is the server side of saving and the database change. The Save button, the Services page and their wording come in 5a-3. Recommended: accept.
2. **Hymn use stays unrecorded until 5a-3** (clarification 2): saving will record it, but the app cannot save until 5a-3's Save button, so the Hymns step's "Used …" marks keep missing services built until then. Recommended: accept (5a-3 is next).
3. **Deleting or moving a service** (clarification 8): deleting a service recalculates that date from the services still saved for it; saving a service under a new date recalculates both dates; deleting a service that has no date changes nothing. When a date is recalculated, older hymn-use entries for that date that no saved service backs (from Streamlit's Prepare button or the imported history) go too. Recommended: accept (it follows your answer 6).
4. **A saved service keeps exactly what it was saved with** (clarification 7): the server stores the Benediction text and the communion setting it receives, so a later change to the church's default Benediction does not change a saved service. Recommended: accept (your answer 4).
5. **The checks around the merge** (clarification 14; Task 9): I start the backup on your yes; you paste one read-only query into the Supabase SQL Editor and tell me four numbers; I show you the eight lines of SQL the migration will run and explain them; after the deploy, one more read-only query and a short phone check that the app works as before. Recommended: accept.
6. **If this PR ever has to be undone, the two new columns and the index stay** (clarification 18): they are empty and harmless, and keeping them keeps Railway's deploy working. Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T8); the backup on your yes, the counts and the SQL check, the merge on your yes, the after-deploy query and the phone check, and the records PR (T9).
