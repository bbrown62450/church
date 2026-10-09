# Slice 6b-1: People on the Server (Members, Invites, Ownership, Leave, Delete) and the Invites-Integrity Migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first of slice 6b's two PRs (owner's 6b planning answers of 2026-10-09, "all recommended"; binding): **the server side of People and the Danger zone, with the invites-integrity migration.** After it merges, the API serves `GET /members` (every member sees every member, with emails), `PATCH /members/{user_id}` (owners and admins make a member an admin or an admin a member, never the owner, never themselves), `DELETE /members/{user_id}` (owners and admins remove someone other than the owner or themselves; every invite link the removed person made stops working, and with `?revoke_reusable=true` every live reusable link of the church too), `GET`, `POST` and `DELETE /invites` (owners and admins list the live invite links, make a single-use link (or one "Reusable for 7 days"), optionally for one email address, and revoke one), `POST /church/transfer-ownership` and `DELETE /church` (the owner only; the delete needs the church's exact name), and `POST /church/leave` (anyone but the owner). Every write runs in one transaction under the church-row lock with the caller's role re-read under it, and the role rules are one pure, table-tested module. Migration **`0008_invites_integrity`** makes the database refuse an invite for any role but member or admin (a stored one is first made an admin invite and revoked) and allows one pending invite per church and email in any capitalization (replacing the old "one invite per church and email, ever" constraint, so an email can be invited again after a revoke or an acceptance); it refuses to run over duplicate pending invites, naming the churches, never an email. `backend/scripts/check_integrity.py` and the README's "Church integrity" runbook find churches without exactly one owner or without an admin, bad invite roles and duplicate pending invites. **No page changes**: People and Danger zone are 6b-2's (with the one-owner revision `0009_…`); the app looks and works as before, and only the generated API types are refreshed. Production moves from `0007_bulletin_images` to `0008_invites_integrity` through the owner's routine (backup, read-only counts and checks, the SQL preview, the after-deploy check). No new package or variable; the frozen Streamlit files are untouched. Tests never reach the network.

**Architecture:** Backend only, bottom up. T1: the revision, the `Invite` model's table arguments, `pytest.ini`'s two targeted warning filters (SQLite cannot reflect an expression index), and the README's "Before 0008_invites_integrity" and "Church integrity (slice 6b)" sections, every query and the SQL preview pinned by tests on SQLite and Postgres. T2: `repos/integrity.py` (`find_violations`, ids and counts only) and `scripts/check_integrity.py` (read-only, an exported `DATABASE_URL` only, like `schema_drift.py`). T3: `usecases/role_policy.py` (four pure checks with the spec's exact messages) and the shared fixture `tests/fixtures/shared/role_policy.json` (the 51 reachable states, for 6b-2's page too). T4: the repos (`memberships`: `set_role`/`remove_membership` in the caller's session, `list_member_rows`, `get_member`, `count_owner_admins`, `is_member_email`, `transfer_ownership` as two Core UPDATEs, demote then promote; `invites`: `insert_invite`, `list_active_invites`, the pending-email lookups, the two revocations, `revoke_invite` returning whether the church has it; `churches.soft_delete_church` in the caller's session, revoking every unrevoked invite), every frozen-Streamlit caller unchanged. T5: `usecases/members.py`'s member and invite functions after 6a-1's `lock_and_read_actor`. T6: `usecases/church_admin.py`'s `transfer_ownership`, `leave_church`, `delete_church`. T7: `api/deps.require_owner`, `api/routes/members.py` (new), the admin invite routes in `routes/invites.py`, the lifecycle routes in `routes/churches.py`, `ADMIN_ONLY` and a new `OWNER_ONLY` in `test_route_guards.py`, the regenerated `openapi.json` and `schema.d.ts`. T8: Postgres tests that each write waits for the other and sees its result. T9: the manual check items.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy 2.1, Alembic 1.20, psycopg2, pytest; the frontend only regenerates `schema.d.ts` (openapi-typescript 7) and is checked with Vitest 3, `tsc` and ESLint.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md`, read with its **"Amendment 2026-10-09: owner's 6b planning answers"**, which is binding and wins where the older text differs: (1) two PRs, this is **6b-1**, the server side with the invites-integrity revision at the next free number (`0008_…`); 6b-2 has the pages and the one-owner revision (`0009_…`); each migration follows the owner routine (backup, before and after counts, a SQL preview, an after-deploy check); (2) Streamlit is treated as unused: no Streamlit compatibility work, no `streamlit_tests` port or ledger, no `LegacySettingsNote` (never built); `check_integrity.py` and its runbook stay; the frozen Streamlit files are untouched; (3) visibility as designed; (4) invites as designed (single-use by default, "Reusable for 7 days", optional email binding); (5) removal revokes the removed person's links, "Also revoke the reusable links" checked by default (the page's default; the API's flag defaults to false); (6) an admin can't change their own role; leave, remove, transfer and delete confirm (6b-2), delete needs the exact church name (here: on the server); (7) the final Settings order (6b-2). No em dashes in user-facing copy. From S: "API" (routes, notes, models), "Role policy" (the table and the evaluation order), "Invite semantics", "Backend changes" (modules, repo changes, transactions and locking, tenancy and logging), "Data and migrations" (its `0006_invites_integrity` is this `0008`), "Church integrity runbook", Testing (the backend parts: pure policy, usecases, integrity, migrations, API, Postgres) and acceptance 1-13 and 21 (the server's half).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.2 (guards; rule 2, another church's id is a 404), §1.5 (errors), §1.6 (Idempotency-Key), §1.7 (the church-row lock), §2.2 (layers), §2.5 (logs), §3.4 and §3.5 (migrations: assert before a constraint, expand-only), §5.1 (the Postgres job).
- The model plans: `docs/superpowers/plans/2026-10-08-slice-6a3b-prayers.md` and `docs/superpowers/plans/2026-10-08-slice-6a3a-prompts-rubric-bulletin.md` (structure, directives, the Postgres lock tests, `ADMIN_ONLY`, their plan review and build review fixes), and for the migration and the owner routine `docs/superpowers/plans/2026-10-03-printed-bulletin-3.md` (PR 3a: migration `0007` with the backup, the counts, the SQL preview pinned by a test and the README, the after-deploy check that also answers before the migration) and `backend/migrations/README.md` ("Before 0006_services_bulletin", "Before 0007_bulletin_images"). "Lessons carried" below maps their findings to this plan.
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `072c374` = `origin/main` `3550645` (6a-3b merged as PR #58) plus the 6a-3b record `e0dfd2a` and the 6b amendment `072c374`, then this plan's commits; 2026-10-09): backend `1983 passed, 35 skipped`; frontend `952 passed` in 109 files; typecheck and lint clean; Alembic head `0007_bulletin_images` (7 revision files); 4 runbook owner markers. What exists: `api/deps.py` (`require_church`, whose 403 carries `details.reason` `no_church_access`; `require_admin`, "Only church admins can do this."); `usecases/members.py` with only `lock_and_read_actor(s, church_id, actor_id)` (6a-1: `repos.churches.lock_church`, then the role re-read; a deleted church or a missing membership is the `no_church_access` 403); `usecases/church_admin.require_admin_role` (`church_admin` imports `members`); `email_addresses.normalize_address` and the shared fixture `email_addresses.json`; `api/schemas.DeletedOut`; `api/idempotency.run_idempotent(..., church_id=)` (church-scoped keys); `domain_errors.ERROR_CODES` with `conflict`, `last_admin`, `owner_must_transfer`, `invite_exists` and `idempotency_mismatch` already registered; `tests/api_helpers.assert_church_isolated`; `test_migrations.test_there_is_a_single_head`; `test_route_guards.ADMIN_ONLY` (13 routes); `routes/invites.py` (slice 1: `POST /invites/preview`, `POST /invites/accept`, whose docstring reserves the module for 6b), `routes/churches.py` (`POST /churches`), `GET`/`PATCH /church` in `routes/me.py`; `repos/memberships.py` (`set_role`, `remove_membership` with `LastAdminError` under the admin-row lock, `list_members` ordered by email), `repos/invites.py` (`create_invite` returning the code, `list_invites` filtering in Python, `revoke_invite` returning nothing and silently ignoring a string id), `repos/churches.soft_delete_church` (revokes only unaccepted invites). The frozen `streamlit_views/settings.py` imports `set_role`, `remove_membership`, `list_members`, `soft_delete_church`, `create_invite`, `list_invites` and `revoke_invite`, and `streamlit_tests` run in the suite. `usecases/onboarding.accept_invite` already claims (stamps `accepted_at` and `accepted_by` on) every non-reusable invite a new member accepts, code-only ones included (`test_single_use_code_only_lifecycle`). The models' `Invite` has `UniqueConstraint("church_id", "email", name="uq_invites_church_email")` with a misleading comment, and no role CHECK.
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch, the migration on SQLite and on a throwaway local Postgres (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan. `<repo>` is the GitHub repository of this checkout's `origin` (owner/name), `<api>` the production API's address (Railway → the API service → Settings → Networking), `<app>` the production app's address, `<scratch>` the session's scratchpad path, `<N>` the PR number and `<local url>` a local, throwaway Postgres URL (host `localhost`); write each out literally when running a command, and never into a committed file.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -1`; the suite `.venv/bin/python -m pytest -q | tail -1`; the Postgres-only tests `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres <paths> 2>&1 | tail -1` (only where a local, throwaway Postgres is at hand; CI's `backend-postgres` job runs them on every push). Frontend (T7 and T10 only): `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` and the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`. A time in an expected output is written `<t>`.
- The API changes (T7), so T7 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand. No other frontend file changes.
- One migration (T1, `0008_invites_integrity`, down from `0007_bulletin_images`); no new package, no new variable.
- Branch `claude/slice-2-plan-4q33le`, at `072c374` plus this plan's commits (the `WIP plan: …` commits and `Plan: slice 6b-1 (people on the server and the invites-integrity migration)`, and any later plan commit), then T1-T9. Stage files by name; nothing under `.claude/` is staged.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R <repo>`, only on the owner's explicit yes, and only after T11's backup, counts and SQL preview.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1983 → 2216 passed, 35 → 45 skipped; frontend 952 in 109 files (unchanged)`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy (the server's messages) is exactly the list in clarification 17 and has no em dashes.
- No church id, email address, invite code or link, token, database URL or real person's name in any doc, commit, test or record. Tests use `@example.com` addresses, the fixtures' "Grace" and made-up names.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.
- **Tests never reach the network**: the suite's `_no_network` fixture refuses any socket except the local Postgres the `postgres` tests are given; the Postgres tests skip without `TEST_DATABASE_URL`, which must be a local, throwaway Postgres (`tests.pg_helpers.require_local_test_url`).

### How the file directives below read
As in the 6a-3a and 6a-3b plans: **Create `path`:** the block is the whole new file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file, as whole lines, and is replaced by the block after **with:** (a leading or trailing empty line in a block is part of it). Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. No file is moved or deleted.

### Baselines and counts
- Starting baselines: backend **1983 passed, 35 skipped**; frontend **952 passed in 109 files**, typecheck and lint clean; Alembic head **`0007_bulletin_images`** (7 revision files; T1 adds the 8th); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case). The frontend gains no test.

  | After | Backend (delta) | Backend | Postgres job (local: skipped) |
  |---|---|---|---|
  | T1 | +5 passed, +2 skipped (`test_migrations.py`: five SQLite tests, two Postgres; four test files edited) | 1988 passed, 37 skipped | 37 passed |
  | T2 | +8 passed, +1 skipped (`test_integrity.py`) | 1996 passed, 38 skipped | 38 passed |
  | T3 | +52 (`test_role_policy.py`: one test and one test in 51 cases; `test_no_streamlit_in_core.py` edited) | 2048 passed, 38 skipped | 38 passed |
  | T4 | +10 (`test_memberships_repo.py` 4, `test_invites_repo.py` 5, `test_churches_repo.py` 1; one onboarding test edited) | 2058 passed, 38 skipped | 38 passed |
  | T5 | +82 (`test_members_usecase.py`: 28 tests, eight of them parametrized, among them the 29 invalid and 8 valid rows of `email_addresses.json`) | 2140 passed, 38 skipped | 38 passed |
  | T6 | +23 (`test_church_lifecycle.py`) | 2163 passed, 38 skipped | 38 passed |
  | T7 | +53 (`test_api_members.py` 30, `test_api_invites_admin.py` 14, `test_api_church_lifecycle.py` 8, `test_route_guards.py` 1) | 2216 passed, 38 skipped | 38 passed |
  | T8 | +7 skipped (`test_people_postgres.py`) | 2216 passed, 45 skipped | 45 passed |
  | T9 | 0 (`test_slice1_docs.py` edited) | 2216 passed, 45 skipped | 45 passed |

- CI `backend-postgres` goes from `35 passed, 1983 deselected` to `45 passed, 2216 deselected`. The frontend stays `952 passed` in 109 files; T7 regenerates `schema.d.ts`, so CI's "API types match the OpenAPI snapshot" step and the typecheck run on it.

### Layering and code rules (carried)
- `usecases/role_policy.py` is pure (no database); `usecases/members.py` and `usecases/church_admin.py` import no FastAPI, Starlette or Streamlit (T3 adds `role_policy` and `repos.integrity` to `test_no_streamlit_in_core.py`; the other two are already listed); the routes are plain `def`s with no SQL and no try/except (F §2.2 rule 1), each one usecase call; the usecases write through the repos (no SQL in a usecase), called through their modules so a test can patch one function.
- **One church-row lock.** Every write of 6b-1 opens one `session_scope()` and starts with `lock_and_read_actor` (6a-1's), then checks the role read under the lock, then reads the target, then writes (S "Transactions and locking"). A role 403 never carries `details`; a church deleted, or a caller's membership removed, after the guard ran is the `no_church_access` 403.
- **Invite codes are bearer secrets.** They appear only in `GET` and `POST /invites` answers (admins only, `Cache-Control: no-store`) and the accept and preview request bodies; never in a path, a query string or a log line. Log lines carry ids, roles and counts.
- **Migrations are safe on production data** (F §3.4): the duplicate pre-check runs before the unique index, the CHECK is added after the repair that makes every row pass it, everything runs in one transaction under the 5 s lock timeout, and the downgrade works (and refuses, changing nothing, when it would fail).
- The frozen Streamlit files (`app.py`, `streamlit_views/`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`) are not edited; the repo functions they import keep their positional signatures, and `streamlit_tests` keep passing.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** is retired (branch `streamlit-frozen`, untouched); merges never reach it. The frozen files on `main` are not edited, and `streamlit_tests` keep passing.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge; Railway's pre-deploy runs `alembic upgrade head`.
4. **The 6b planning answers of 2026-10-09** ("all recommended"; binding; S's amendment): (1) two PRs, this is **6b-1** with `0008_…`; 6b-2 has the pages and `0009_…` (the one-owner index); each migration follows the owner routine (backup, before and after counts, a SQL preview, an after-deploy check); (2) Streamlit treated as unused: no `streamlit_tests` port or ledger, no `LegacySettingsNote`; keep `check_integrity.py` (one owner per church) and its runbook; (3) every member sees the member list with emails; only owners and admins see pending invites, invite, change roles or remove; only the owner transfers or deletes; (4) single-use invites by default, "Reusable for 7 days", optional email binding; (5) removal revokes the removed person's links, and the page's "Also revoke the reusable links" box is checked by default; (6) an admin can't change their own role; role changes apply without confirmation; delete needs the exact church name; (7) the final Settings order (6b-2). No em dashes in user-facing copy.
5. **Earlier answers** (binding, carried): decision 5 (roles: the owner transfers and deletes, admins manage people, members read), decision 6 (invites), 2026-10-02's migration routine (backup, read-only counts, the SQL preview, one step at a time, results recorded without ids or emails), and 6a's "every church write takes the church-row lock and re-reads the caller's role".

**Later, out of scope:** 6b-2 (the People and Danger zone pages, the Settings nav, `memberships_one_owner` as `0009_…`, the client's `useExitChurch` and role meta), slice 7.

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Owner questions" (each written as recommended) unless an answer already covers them.

1. **[owner-visible] What 6b-1 ships** (answers 1 and 2). The nine routes and `require_owner`; `usecases/role_policy.py` and its shared fixture; the member, invite, transfer, leave and delete usecases and their repos; migration `0008_invites_integrity`; `repos/integrity.py` and `scripts/check_integrity.py` with the README's "Church integrity (slice 6b)" runbook and "Before 0008_invites_integrity" steps; the Postgres tests; the regenerated `openapi.json` and `schema.d.ts`; the manual check items. Not here: the People and Danger zone pages, the Settings nav, the client's type aliases, `useExitChurch` and role meta, the frontend tests (6b-2); the one-owner revision (`0009_…`, 6b-2); the `streamlit_tests` port and ledger and the deletion of `streamlit_tests/test_settings_members_invites.py` (answer 2: dropped; the file keeps passing, see 10); `LegacySettingsNote` (never built). Nothing in the app changes for anyone until 6b-2; the routes are live but no page calls them.
2. **The revision's number and place.** S's `0006_invites_integrity` is `0008_invites_integrity` (answer 1), `down_revision = "0007_bulletin_images"`, the head on `main` today. The head constants move with it: `test_api_app.SCHEMA_HEAD`, `test_schema_check.EXPECTED_HEAD` (and its test's name), and the head version the README's 0005-0007 queries report on the Postgres test database (`test_services_postgres.py`). `test_migrations.test_there_is_a_single_head` already enforces the chain.
3. **What S assumed and what exists** (S "Assumed interfaces"). Slice 1, 5b and 6a shipped every interface 6b-1 needs, and nothing is created twice: `lock_church`, `lock_and_read_actor` (in `usecases/members.py`, where 6b adds its functions), `require_admin_role` (`church_admin`, which imports `members`, so `members` imports it inside `_require_admin` when called: one helper, no import cycle), `normalize_address` and its fixture, `DeletedOut`, church-scoped Idempotency-Keys (`run_idempotent(church_id=)`), every error code, `assert_church_isolated`. `ActiveChurch.role` is never trusted for a write: the role read under the lock is.
4. **Slice 1's accept already makes code-only invites single-use** (S "Assumed interfaces", row 3). `accept_invite` claims every non-reusable invite a new member accepts (`if not inv.reusable and not invites.claim(...)`), so a code-only single-use link refuses a second user with "This invite has already been used." (`test_single_use_code_only_lifecycle`). No fix: T7 adds the end-to-end test through `POST /invites`. Slice 1's exception stays: someone already in the church who opens an unused code-only link does not use it up.
5. **The duplicate pre-check runs inside the migration on both dialects** (S "Data and migrations", step 2). On Postgres it is a `DO` block that raises (so the owner's SQL preview shows it, and it runs in the upgrade's one transaction: a refusal rolls back the role repair too, the pre-deploy step fails and the previous release keeps serving); on SQLite it is the same words as a `RuntimeError`. The words: `0008_invites_integrity: {n} (church, email) pair(s) have more than one pending invite: {church ids}. Follow "Church integrity" in backend/migrations/README.md, then redeploy.` (church ids as UUIDs, never an email; S had `0006:`). On Postgres the error reaches Railway's log as the database's exception rather than a Python `RuntimeError`.
6. **The role repair needs no separate assertion** (S step 1, "then assertion"). The `UPDATE` covers every row (`role` is NOT NULL), and adding a CHECK makes Postgres check every existing row itself (SQLite's batch copy does the same), so a separate assertion could never fire. Online runs log `0008_invites_integrity: <n> invite(s) with another role made admin and revoked`; the offline preview cannot count, so it only shows the `UPDATE`.
7. **The expression index and autogenerate** (S Risk 3). On Postgres Alembic compares `uq_invites_pending_email` with the model (`alembic check` reports nothing, measured on PG 16), so `env.py`'s `include_object` needs no exception. SQLite cannot reflect an expression index: SQLAlchemy and Alembic each warn once per comparison and skip it, so `pytest.ini` filters exactly those two warnings, by the index's name, and the SQLite tests read the index from `sqlite_master`. On SQLite the drift of a database stamped at the baseline gains one line, `remove_constraint uq_invites_church_email` (`test_schema_check.BASELINE_DRIFT`).
8. **Slice 1's clamp tests store a role the database now refuses.** Three tests stored an invite as `owner` or `foo` to check that accept and preview clamp it (`_clamp_role`); `ck_invites_role` refuses that now. They store it through `tests/invite_helpers.store_unchecked_role` (SQLite's `PRAGMA ignore_check_constraints` for that one statement). `_clamp_role` stays as a harmless defense.
9. **[owner-visible] How the integrity check is run** (S "Church integrity runbook"). Step 2 of "Before 0008_invites_integrity" is one read-only query for Supabase's SQL Editor that counts the same four kinds `check_integrity.py` reports (T2 checks on Postgres that both agree), so the owner needs no laptop setup. `scripts/check_integrity.py` stays for a laptop, and reads only an exported `DATABASE_URL`, like `schema_drift.py` (S said `load_dotenv()`: a `backend/.env` pointing at Supabase would then be used without anyone choosing it); without one it exits 2. Streamlit is retired, so S's "run it right before slice 7 retires Streamlit" is dropped: the check runs before and after each 6b PR. Owner question 1.
10. **The frozen Streamlit pages keep working on the changed repos** (answer 2; the frozen files are not edited). `streamlit_views/settings.py` imports seven of the changed repo functions; each keeps its positional signature and gains only a keyword-only `session=None` (`revoke_invite` now returns a bool its callers ignore). `streamlit_tests/test_settings_members_invites.py` keeps passing (its transfer runs before any one-owner index). The transfer lives in the repo as `memberships.transfer_ownership`: two Core `UPDATE`s, demote then promote (S "Transactions and locking"), checked by statement order.
11. **Deleting a church revokes every unrevoked invite** (S "Repo changes", inv §1 B3). `soft_delete_church` drops its `accepted_at IS NULL` filter, so a used reusable link is revoked too. One slice 1 test deleted a church through it to keep a consumed invite live for its check-order case; it now sets `deleted_at` directly, as its neighbour `_rejected_code` already does.
12. **Invite creation in detail** (S "Invite semantics"). The checks run in this order, the first failure answering: the role 403 (under the lock); `role` not member or admin, 422 `fields.role` "Not a valid value." (Pydantic answers first over HTTP with the same words; the usecase checks too, for direct callers); the email (`clean_invite_email`: blank is none, else `normalize_address` then lower-cased; refused, 422 `fields.email`); `reusable` with an email, 422 `fields.reusable`; a member of this church with that email, 409 `conflict` "{email} is already a member of this church."; the email's expired pending invites revoked; a live pending one, 409 `invite_exists`; the insert in a savepoint, its `IntegrityError` (a writer that skipped the lock) the same 409. `{email}` is the stored, lower-cased address. Seven days from `now`. The answer is the invite as `GET /invites` lists it, with its creator.
13. **The evaluation order** (S "Role policy"). Change role and remove: the role 403 (`require_admin_role`), then the target as a membership of this church (404 "Member not found."), then the policy (self, the owner). Transfer: `check_transfer` (owner only; self is a 422 naming `user_id`), then the target (404). Leave: `check_leave` with the owner and admin count read under the admin-row lock. Delete: owner only, then the name (trimmed, exact, case included; 422 naming `confirm_name`). The repo's `LastAdminError` cannot fire behind the policy; if it ever does it is a 409 `last_admin` with the repo's words (not in the OpenAPI document, as S says).
14. **Postgres concurrency tests force each race deterministically** (S Testing → Postgres). Instead of 20 rounds behind a `Barrier`, each test holds the first write inside the lock (a function it calls through its module after taking it), starts the second, checks it is still waiting a second later, then releases: the order is then certain and the loser's answer exact, every run. The six S cases plus one: two transactions that skip the lock (a direct write) still cannot store two pending invites for one email. With `lock_church`'s `FOR UPDATE` taken out, six of the seven fail (measured).
15. **The API in detail** (S API). `DELETE /church` takes a JSON body (`confirm_name`); `revoke_reusable` is a query flag (`true`/`false`; anything else 422). `GET` and `POST /invites` answers carry `Cache-Control: no-store` (a replayed or refused `POST` too). `POST /invites`'s Idempotency-Key is scoped to the user, the church and the route. `GET /members` depends on `get_current_user` as well, for `is_me`. `PATCH` and `DELETE /members` document no 409. Every route is a plain `def`.
16. **`test_route_guards.py` pins the new routes** (S API notes; the 6a-3a lesson). `ADMIN_ONLY` gains `PATCH` and `DELETE /members/{user_id}`, `GET` and `POST /invites` and `DELETE /invites/{invite_id}`; a new `OWNER_ONLY` (S's `OWNER_ROUTES`) holds `POST /church/transfer-ownership` and `DELETE /church`, checked both ways as `ADMIN_ONLY` is. `GET /members` and `POST /church/leave` stay church-scoped. The user-scoped allowlist does not change.
17. **[owner-visible] Every new user-facing string** (S's words; no em dashes): "Only the owner can do that.", "You can't change your own role.", "The owner's role can't be changed.", "To leave this church, use Leave church in Danger zone.", "The owner can't be removed.", "Choose someone else to be the new owner.", "Transfer ownership before you leave. If you're the only person in the church, delete it instead.", "You're the last admin. Make someone else an admin before you leave.", "Member not found.", "Enter a valid email address.", "A link for one email address works once.", "{email} is already a member of this church.", "There's already a pending invite for {email}. Copy its link below or revoke it first.", "Invite not found.", "Church name did not match."; for the migration's and the script's readers: the pre-check's words (5), the downgrade's "Cannot restore uq_invites_church_email: {n} (church, email) pairs have more than one invite. Delete the revoked or accepted duplicates first." and "OK: no integrity violations.". Reused: "Only church admins can do this.", "You don't have access to this church.", "Not a valid value.".
18. **Logs** (S "Tenancy and data access"). `invite_created church_id=… invite_id=… role=… reusable=… email_bound=…`, `invite_revoked …`, `member_role_changed … old_role=… new_role=…`, `member_removed … revoked_invites=…`, `ownership_transferred …`, `church_left …`, `church_deleted …`: ids, roles and counts, never an email, a name or a code (T5 and T7 check).
19. **Docs.** T1 adds the README's "Before 0008_invites_integrity (slice 6b-1)" (backup; one read-only query with the counts and the integrity check; the SQL preview pinned by a test; the after-deploy check, which also answers before 0008 is applied; reverting) and "Church integrity (slice 6b)". T9 adds `docs/manual-verification.md` → "## Slice 6b" (items 1-6 for 6b-1; `test_slice1_docs.py`'s pin of the last `##` headings moves). The runbook record is T11's (`### Slice 6b-1 record` before `## Backups`, after `### Slice 6a-3b record`).
20. **Deviations from S** (each the lean or the safer choice): the deterministic Postgres races (14); the integrity check as one SQL Editor query besides the script, which reads only an exported `DATABASE_URL` (9); no separate role assertion (6); the pre-check as a `DO` block on Postgres (5); `list_invites` and `create_invite` take an optional `now` (tests); `revoke_invite` with a malformed id is a 404 from the usecase and a 422 from the route (its path is a UUID); the usecase also checks the invite role (12).

### Risks
- **Production may hold duplicate pending email invites** (unlikely: the old exact-case constraint and the lower-casing since slice 1). T11's step 2 counts them before the merge; the migration refuses to run over them in any case, safely (the previous release keeps serving), and the runbook's step 2 repairs them with the owner.
- **The old constraint's name in production.** The upgrade drops `uq_invites_church_email` by name; step 2 checks it exists (`old_constraint` `1`). The 1a drift check found production's invites table equal to the models, so it is expected.
- **A church without exactly one owner** (made by the retired Streamlit app's role select or by hand). It does not block 0008, but in it transfer and delete are refused (the owner-only 403) and its only admin cannot leave (409). Step 2 counts such churches; owner question 2 says what then.
- **The routes are live before any page uses them** (6b-1 before 6b-2). Only a signed-in owner or admin calling the API directly reaches the writes, under the same rules the pages will use. Nothing removes an owner except a transfer.
- **The lock timeout.** Creating the index and the CHECK takes a short lock on `invites`; another connection holding one for more than 5 s fails the deploy safely; redeploy.
- **SQLite ignores `FOR UPDATE` and cannot reflect the expression index.** Only CI's `backend-postgres` proves the waiting (T8) and compares the index (`alembic check`); T1's SQLite tests read the index from `sqlite_master`.

### Lessons carried (the 3a, 6a-3a and 6a-3b plans and their reviews)
- The SQL preview the owner reads is pinned twice: the test renders it offline and compares it with a constant, and another test compares the README's block with the same constant (3a); trailing spaces stripped.
- The after-deploy query also answers before the migration is applied, so "not yet" is an answer, not an error (3a plan review M9); T1's Postgres test runs it at both versions.
- The owner's queries are run by tests on Postgres, read from the README itself (3a; `test_services_postgres.py`), so the owner never pastes a query no test ran.
- Admin routes are pinned both ways (6a-3a build review 4), and now owner routes too (16).
- Locking is proved on Postgres, not only asked for (6a-1, 6a-3a, 6a-3b), and each Postgres test fails rather than passing vacuously when the first write never takes the lock (a 10 s limit on every wait).
- Every write re-reads the role under the lock and answers a lost church as `no_church_access`, tested for each write at the usecase and over HTTP (6a-1).
- Logs are checked for what they must not hold (6a-3b build review 1): T5 and T7 capture every record of a create, a list and a revoke and look for the code and the email.
- No real ids, emails or URLs in committed files; placeholders in commands (`<repo>`, `<api>`, `<app>`).

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/migrations/versions/0008_invites_integrity.py` | the revision | T1 |
| `backend/tests/invite_helpers.py` | `store_unchecked_role` for slice 1's clamp tests | T1 |
| `backend/repos/integrity.py`, `backend/scripts/check_integrity.py` (+ `backend/tests/test_integrity.py`) | `find_violations`; the read-only CLI | T2 |
| `backend/usecases/role_policy.py`, `backend/tests/fixtures/shared/role_policy.json` (+ `backend/tests/test_role_policy.py`) | the four pure checks; the 51 reachable states | T3 |
| `backend/tests/test_members_usecase.py` | the member and invite usecases | T5 |
| `backend/tests/test_church_lifecycle.py` | transfer, leave, delete | T6 |
| `backend/api/routes/members.py` (+ `backend/tests/test_api_members.py`, `test_api_invites_admin.py`, `test_api_church_lifecycle.py`) | `/members`; the HTTP tests of all nine routes | T7 |
| `backend/tests/test_people_postgres.py` | the races on Postgres | T8 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/db/models.py` | `Invite`: `ck_invites_role`, `uq_invites_pending_email`, `PENDING_INVITE`; the old constraint and comment go | T1 |
| `backend/migrations/README.md` | the head, the revision's row, "Before 0008_invites_integrity (slice 6b-1)", "Church integrity (slice 6b)" | T1 |
| `pytest.ini` | two warning filters naming the index | T1 |
| `backend/tests/test_migrations.py`, `test_schema_check.py`, `test_api_app.py`, `test_services_postgres.py`, `test_api_invites.py`, `test_usecase_onboarding.py` | the 0008 tests; the head; the clamp tests' rows | T1 (and T4 for one onboarding test) |
| `backend/tests/test_no_streamlit_in_core.py` | `usecases.role_policy`, `repos.integrity` | T3 |
| `backend/repos/memberships.py`, `invites.py`, `churches.py` (+ `test_memberships_repo.py`, `test_invites_repo.py`, `test_churches_repo.py`) | the repo changes | T4 |
| `backend/usecases/members.py` | the member and invite functions | T5 |
| `backend/usecases/church_admin.py` | transfer, leave, delete | T6 |
| `backend/api/deps.py`, `backend/api/main.py`, `backend/api/routes/invites.py`, `backend/api/routes/churches.py`, `backend/tests/test_route_guards.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | `require_owner`; the router; the routes; `ADMIN_ONLY` and `OWNER_ONLY`; regenerated | T7 |
| `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py` | "## Slice 6b" and its pin | T9 |
| `docs/ops-runbook.md` | "### Slice 6b-1 record" (the records PR, after the merge) | T11 |

**Counts in the PR:** 45 paths: 16 added (this plan and the fifteen new code, test and fixture files above) and 29 modified (the twenty-six code, test, config and API paths above, `docs/manual-verification.md`, and two that ride along until merged: `docs/ops-runbook.md` with the 6a-3b record and the 6b spec with its amendment; the runbook's own T11 change goes in the records PR). **Untouched:** `api/idempotency.py`, `api/schemas.py`, `api/errors.py`, `domain_errors.py`, `email_addresses.py`, `usecases/onboarding.py`, `tenancy.py`, `migrations/env.py`, `db/schema_check.py`, every other migration, every frontend file except the two generated ones, `requirements*.txt`, `frontend/package*.json`, `.github`, `app.py`, `streamlit_views`, `streamlit_tests`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`.

**Task order and review batch:** T1 → T9, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T10 verifies and opens the draft PR on the owner's yes; T11 takes the owner through the backup, the counts and checks and the SQL preview, merges on the owner's yes, checks production, runs the short phone check and writes the record.

---

## The server (T1-T8)

### Task 1: Migration `0008_invites_integrity`, the model, and the owner's steps in the README (S "Data and migrations", "Church integrity runbook"; answers 1 and 2; clarifications 2, 5-8, 19)

**Files:**
- Create: `backend/migrations/versions/0008_invites_integrity.py`, `backend/tests/invite_helpers.py`
- Modify: `backend/db/models.py`, `backend/migrations/README.md`, `pytest.ini`, `backend/tests/test_migrations.py`, `backend/tests/test_schema_check.py`, `backend/tests/test_api_app.py`, `backend/tests/test_services_postgres.py`, `backend/tests/test_api_invites.py`, `backend/tests/test_usecase_onboarding.py`

The head moves to `0008_invites_integrity`. On SQLite (every test database): the role repair, the refusal over duplicate pending emails until the runbook's step 2 runs (read from the README itself), the swap of the old constraint for the partial index (read from `sqlite_master`) and the CHECK, the downgrade (refusing over exact duplicates), the offline SQL equal to `PREVIEW_0008` and the README's step 3 equal to it too. On Postgres: the same upgrade and downgrade (the `DO` block's refusal rolls back the repair), the index's definition, and the owner's two read-only queries before and after the upgrade. Slice 1's three clamp tests store their `owner`/`foo` invite through `store_unchecked_role`.

- [ ] **Step 1: Write the failing tests**

**Create `backend/tests/invite_helpers.py`:**

````python
"""An invite row as it could be stored before 0008_invites_integrity.

Since slice 6b-1 the database refuses an invite whose role is neither member
nor admin (ck_invites_role). Slice 1's accept and preview still clamp such a
role (usecases.onboarding._clamp_role), so their tests store one with
SQLite's CHECK enforcement off for that one statement.
"""
from sqlalchemy import text, update

from db import session_scope
from db.models import Invite


def store_unchecked_role(code: str, role: str) -> None:
    """Set the invite's role to `role`, which ck_invites_role would refuse (SQLite tests only)."""
    with session_scope() as s:
        s.execute(text("PRAGMA ignore_check_constraints = ON"))
        try:
            s.execute(update(Invite).where(Invite.code == code).values(role=role))
        finally:
            s.execute(text("PRAGMA ignore_check_constraints = OFF"))
````

**In `backend/tests/test_api_app.py`, replace:**

````python
SCHEMA_HEAD = "0007_bulletin_images"
````

**with:**

````python
SCHEMA_HEAD = "0008_invites_integrity"
````

**In `backend/tests/test_api_invites.py`, replace:**

````python
from tests.api_helpers import auth_headers, church_headers, make_api_client
````

**with:**

````python
from tests.api_helpers import auth_headers, church_headers, make_api_client
from tests.invite_helpers import store_unchecked_role
````

**In `backend/tests/test_api_invites.py`, replace:**

````python
    code = world.invite(role="owner")            # no CHECK on invites.role until 6b
````

**with:**

````python
    code = world.invite()
    store_unchecked_role(code, "owner")          # a row from before 0008's CHECK
````

**Append to `backend/tests/test_migrations.py`:**

````python


# --- Slice 6b-1: 0008_invites_integrity (6b spec, "Data and migrations"; owner's 6b planning answers) ---

# What `alembic upgrade 0007_bulletin_images:0008_invites_integrity --sql` prints on Postgres,
# comments, blank lines and trailing spaces left out: the preview the owner reads before the
# merge (backend/migrations/README.md, "Before 0008_invites_integrity", step 3).
PREVIEW_0008 = [
    "BEGIN;",
    "SET LOCAL lock_timeout = '5s';",
    "SET LOCAL statement_timeout = '60s';",
    "UPDATE invites SET role='admin', revoked=true WHERE (invites.role NOT IN ('member', 'admin'));",
    "DO $$",
    "DECLARE",
    "  pairs integer;",
    "  church_ids text;",
    "BEGIN",
    "  SELECT count(*), string_agg(DISTINCT church_id::text, ', ')",
    "    INTO pairs, church_ids",
    "    FROM (SELECT church_id FROM invites",
    "           WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL",
    "           GROUP BY church_id, lower(email) HAVING count(*) > 1) AS duplicates;",
    "  IF pairs > 0 THEN",
    "    RAISE EXCEPTION '0008_invites_integrity: % (church, email) pair(s) have more than one pending invite: %. "
    "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy.', pairs, church_ids;",
    "  END IF;",
    "END $$;",
    "ALTER TABLE invites DROP CONSTRAINT uq_invites_church_email;",
    "ALTER TABLE invites ADD CONSTRAINT ck_invites_role CHECK (role IN ('member','admin'));",
    "CREATE UNIQUE INDEX uq_invites_pending_email ON invites (church_id, lower(email)) "
    "WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL;",
    "UPDATE alembic_version SET version_num='0008_invites_integrity' "
    "WHERE alembic_version.version_num = '0007_bulletin_images';",
    "COMMIT;",
]

# Church integrity, step 2 (backend/migrations/README.md): keep the newest pending invite per
# church and email, revoke the rest. The tests run it exactly as the README prints it.
RUNBOOK_DEDUPE_PATTERN = re.compile(r"\n2\. \*\*Duplicate pending email invites\*\*.*?```sql\n(.*?)```", re.S)


def _readme() -> str:
    return (Path(__file__).resolve().parents[1] / "migrations" / "README.md").read_text(encoding="utf-8")


def _runbook_dedupe_sql() -> str:
    return RUNBOOK_DEDUPE_PATTERN.search(_readme()).group(1)


def _invite_row(conn, church_id, user_id, *, email=None, role="member", revoked=False, accepted=False,
                created_at=T9_NOW) -> uuid.UUID:
    """An invite inserted with plain SQL, as any client of the table could."""
    invite_id = uuid.uuid4()
    conn.execute(sa.text(
        "INSERT INTO invites (id, church_id, code, email, role, created_by, created_at, expires_at, revoked, "
        "accepted_at, reusable) VALUES (:id, :church, :code, :email, :role, :user, :created, :expires, :revoked, "
        ":accepted, :reusable)"),
        {"id": invite_id.hex if conn.dialect.name == "sqlite" else invite_id,
         "church": church_id.hex if conn.dialect.name == "sqlite" else church_id,
         "code": uuid.uuid4().hex, "email": email, "role": role,
         "user": user_id.hex if conn.dialect.name == "sqlite" else user_id,
         "created": created_at, "expires": created_at + timedelta(days=7), "revoked": revoked,
         "accepted": T9_NOW if accepted else None, "reusable": email is None})
    return invite_id


def _invite_state(conn, invite_id) -> tuple:
    key = invite_id.hex if conn.dialect.name == "sqlite" else invite_id
    row = conn.execute(sa.text("SELECT role, revoked FROM invites WHERE id = :id"), {"id": key}).one()
    return row.role, bool(row.revoked)


def _version(url: str) -> str:
    with _connection(_normalize_url(url)) as conn:
        return conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()


def test_0008_repairs_roles_and_allows_one_pending_invite_per_email(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0007_bulletin_images")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            owner_invite = _invite_row(conn, church_id, user_id, role="owner")
            junk_invite = _invite_row(conn, church_id, user_id, email="junk@example.com", role="pastor")
            kept = _invite_row(conn, church_id, user_id, email="b@example.com", role="admin")
            _invite_row(conn, church_id, user_id, email="a@example.com", revoked=True)   # the old constraint
            _invite_row(conn, church_id, user_id, email="A@example.com")                 # allows these two
        _alembic(sqlite_url, "upgrade", "0008_invites_integrity")
        with engine.begin() as conn:
            states = [_invite_state(conn, i) for i in (owner_invite, junk_invite, kept)]
            shape = _invites_shape(conn)
            index_sql = conn.execute(sa.text(
                "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'uq_invites_pending_email'")).scalar_one()
            checks = sa.inspect(conn).get_check_constraints("invites")
        with engine.begin() as conn:     # a re-invite after a revoke, an accepted one, and code-only links
            _invite_row(conn, church_id, user_id, email="b@example.com", accepted=True)
            _invite_row(conn, church_id, user_id, email="c@example.com", revoked=True)
            _invite_row(conn, church_id, user_id, email="C@example.com")
            _invite_row(conn, church_id, user_id)
            _invite_row(conn, church_id, user_id)
        for email, role in (("a@EXAMPLE.com", "member"), ("x@example.com", "owner")):
            with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
                _invite_row(conn, church_id, user_id, email=email, role=role)
    finally:
        engine.dispose()
    assert states == [("admin", True), ("admin", True), ("admin", False)]
    assert shape["uniques"] == [("", ("code",))]
    assert index_sql == ("CREATE UNIQUE INDEX uq_invites_pending_email ON invites (church_id, lower(email)) "
                         "WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL")
    assert [(c["name"], c["sqltext"]) for c in checks] == [("ck_invites_role", "role IN ('member','admin')")]
    assert _version(sqlite_url) == "0008_invites_integrity"


def test_0008_refuses_duplicate_pending_emails_until_the_runbook_step_runs(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0007_bulletin_images")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            older = _invite_row(conn, church_id, user_id, email="dup@example.com")
            newer = _invite_row(conn, church_id, user_id, email="Dup@example.com",
                                created_at=T9_NOW + timedelta(hours=1))
        with pytest.raises(RuntimeError) as refused:
            _alembic(sqlite_url, "upgrade", "0008_invites_integrity")
        assert _version(sqlite_url) == "0007_bulletin_images"
        with engine.begin() as conn:
            conn.execute(sa.text(_runbook_dedupe_sql()))
        _alembic(sqlite_url, "upgrade", "0008_invites_integrity")
        with engine.begin() as conn:
            states = {i: _invite_state(conn, i)[1] for i in (older, newer)}
    finally:
        engine.dispose()
    assert str(refused.value) == (
        f"0008_invites_integrity: 1 (church, email) pair(s) have more than one pending invite: {church_id}. "
        "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy.")
    assert "dup@" not in str(refused.value).lower()
    assert states == {older: True, newer: False}
    assert _version(sqlite_url) == "0008_invites_integrity"


def test_0008_downgrade_restores_the_old_constraint_or_refuses_over_duplicates(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0007_bulletin_images")
    before = _tables_snapshot(sqlite_url)
    _alembic(sqlite_url, "upgrade", "0008_invites_integrity")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            revoked = _invite_row(conn, church_id, user_id, email="again@example.com", revoked=True)
            _invite_row(conn, church_id, user_id, email="again@example.com")
        with pytest.raises(RuntimeError) as refused:
            _alembic(sqlite_url, "downgrade", "0007_bulletin_images")
        assert _version(sqlite_url) == "0008_invites_integrity"
        with engine.begin() as conn:
            conn.execute(sa.text("DELETE FROM invites WHERE id = :id"), {"id": revoked.hex})
    finally:
        engine.dispose()
    _alembic(sqlite_url, "downgrade", "0007_bulletin_images")
    assert str(refused.value) == (
        "Cannot restore uq_invites_church_email: 1 (church, email) pairs have more than one invite. "
        "Delete the revoked or accepted duplicates first.")
    assert _tables_snapshot(sqlite_url) == before
    assert _version(sqlite_url) == "0007_bulletin_images"


def test_offline_sql_for_0008_repairs_checks_and_swaps_the_constraint_under_the_timeouts():
    cfg = alembic_config(url="postgresql://preview@localhost:1/preview", configure_logger=False)
    cfg.output_buffer = buffer = io.StringIO()
    command.upgrade(cfg, "0007_bulletin_images:0008_invites_integrity", sql=True)
    lines = [line.rstrip() for line in buffer.getvalue().splitlines() if line.strip() and not line.startswith("--")]
    assert lines == PREVIEW_0008


def test_the_readme_shows_the_0008_preview_exactly():
    """The owner reads backend/migrations/README.md → "Before 0008_invites_integrity",
    step 3, against the agent's rendering; both must be PREVIEW_0008."""
    section = _readme().split("\n## Before 0008_invites_integrity (slice 6b-1)\n", 1)[1]
    step = section.split("\n### Step 3: Read the SQL the upgrade will run\n", 1)[1].split("\n### ", 1)[0]
    block = "BEGIN;" + step.split("\n```\nBEGIN;", 1)[1].split("\n```", 1)[0]   # the bare fence
    assert block.splitlines() == PREVIEW_0008


def _readme_0008_sql(n: int) -> str:
    """The n-th ```sql block of README "Before 0008_invites_integrity": 0 is step 2's
    counts and integrity check, 1 step 4's after-deploy check."""
    section = _readme().split("\n## Before 0008_invites_integrity (slice 6b-1)\n", 1)[1]
    return re.findall(r"```sql\n(.*?)```", section, re.S)[n]


@pytest.mark.postgres
def test_0008_on_postgres_refuses_duplicates_then_repairs_swaps_and_downgrades(pg_admin_url):
    """The same upgrade on Postgres: the DO block's refusal rolls back the whole
    run (the role repair too), the runbook's dedupe makes it pass, the partial
    expression index and the CHECK hold, and the downgrade refuses over exact
    duplicates and otherwise restores uq_invites_church_email."""
    with throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        _alembic(sandbox.role_url, "upgrade", "0007_bulletin_images")
        engine = _pg_engine(sandbox.role_url)
        try:
            with engine.begin() as conn:
                user_id, church_id = _seed_owner_and_church(conn)
                owner_invite = _invite_row(conn, church_id, user_id, role="owner")
                older = _invite_row(conn, church_id, user_id, email="dup@example.com")
                newer = _invite_row(conn, church_id, user_id, email="Dup@example.com",
                                    created_at=T9_NOW + timedelta(hours=1))
            with pytest.raises(sa.exc.DBAPIError) as refused:
                _alembic(sandbox.role_url, "upgrade", "0008_invites_integrity")
            with engine.connect() as conn:
                assert _invite_state(conn, owner_invite) == ("owner", False)   # rolled back with the refusal
            assert _version(sandbox.role_url) == "0007_bulletin_images"
            with engine.begin() as conn:
                conn.execute(text(_runbook_dedupe_sql()))
            _alembic(sandbox.role_url, "upgrade", "0008_invites_integrity")
            with engine.begin() as conn:
                states = [_invite_state(conn, i) for i in (owner_invite, older, newer)]
                index = conn.execute(text(
                    "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_invites_pending_email'")).scalar_one()
                old = conn.execute(text(
                    "SELECT count(*) FROM pg_constraint WHERE conname = 'uq_invites_church_email'")).scalar_one()
                _invite_row(conn, church_id, user_id, email="dup@example.com", accepted=True)
            for email, role in (("DUP@example.com", "member"), (None, "owner")):
                with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
                    _invite_row(conn, church_id, user_id, email=email, role=role)
            with pytest.raises(RuntimeError, match="Cannot restore uq_invites_church_email: 1 "):
                _alembic(sandbox.role_url, "downgrade", "0007_bulletin_images")
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM invites WHERE email IS NOT NULL AND id <> :id"), {"id": newer})
            _alembic(sandbox.role_url, "downgrade", "0007_bulletin_images")
            with engine.connect() as conn:
                restored = conn.execute(text(
                    "SELECT count(*) FROM pg_constraint WHERE conname = 'uq_invites_church_email'")).scalar_one()
        finally:
            engine.dispose()
    message = str(refused.value.orig).splitlines()[0]
    assert message == (
        f"0008_invites_integrity: 1 (church, email) pair(s) have more than one pending invite: {church_id}. "
        "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy.")
    assert states == [("admin", True), ("member", True), ("member", False)]
    assert index == ("CREATE UNIQUE INDEX uq_invites_pending_email ON public.invites USING btree "
                     "(church_id, lower((email)::text)) WHERE ((email IS NOT NULL) AND (NOT revoked) "
                     "AND (accepted_at IS NULL))")
    assert (old, restored) == (0, 1)


@pytest.mark.postgres
def test_the_owner_s_read_only_queries_around_0008(pg_admin_url):
    """README "Before 0008_invites_integrity": step 2's counts and integrity check
    before and after the upgrade, and step 4's check (which also answers before
    0008 is applied)."""
    with throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        _alembic(sandbox.role_url, "upgrade", "0007_bulletin_images")
        engine = _pg_engine(sandbox.role_url)
        try:
            with engine.begin() as conn:
                user_id, church_id = _seed_owner_and_church(conn)
                conn.execute(text("INSERT INTO memberships (church_id, user_id, role, created_at) "
                                  "VALUES (:c, :u, 'owner', now())"), {"c": church_id, "u": user_id})
                conn.execute(text("INSERT INTO churches (id, name, timezone, settings, created_at) "
                                  "VALUES (:id, 'Hope', 'UTC', '{}', now())"), {"id": uuid.uuid4()})
                _invite_row(conn, church_id, user_id, role="owner")
                _invite_row(conn, church_id, user_id, email="p@example.com")
                _invite_row(conn, church_id, user_id, email="P@example.com", revoked=True)
                _invite_row(conn, church_id, user_id)
            with engine.connect() as conn:
                before = dict(conn.execute(text(_readme_0008_sql(0))).mappings().one())
                check_before = dict(conn.execute(text(_readme_0008_sql(1))).mappings().one())
            _alembic(sandbox.role_url, "upgrade", "0008_invites_integrity")
            with engine.connect() as conn:
                after = dict(conn.execute(text(_readme_0008_sql(0))).mappings().one())
                check_after = dict(conn.execute(text(_readme_0008_sql(1))).mappings().one())
        finally:
            engine.dispose()
    assert before == {"version": "0007_bulletin_images", "invites": 4, "pending_email_invites": 1,
                      "duplicate_pending_pairs": 0, "other_role_invites": 1, "old_constraint": 1,
                      "churches": 2, "churches_without_one_owner": 1, "churches_without_admin": 1}
    assert check_before == {"version": "0007_bulletin_images", "pending_email_index": 0, "role_check": 0,
                            "old_constraint": 1}
    assert after == {**before, "version": "0008_invites_integrity", "other_role_invites": 0, "old_constraint": 0}
    assert check_after == {"version": "0008_invites_integrity", "pending_email_index": 1, "role_check": 1,
                           "old_constraint": 0}
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
EXPECTED_HEAD = "0007_bulletin_images"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
# 0004's invites changes, then 0005's and 0006's services changes (slice 5a-2,
# printed bulletin PR 2b), then 0007's table (printed bulletin PR 3a).
````

**with:**

````python
EXPECTED_HEAD = "0008_invites_integrity"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
# 0004's invites changes, then 0005's and 0006's services changes (slice 5a-2,
# printed bulletin PR 2b), then 0007's table (printed bulletin PR 3a), then
# 0008's removed constraint (slice 6b-1; SQLite reflects no expression index,
# so its new uq_invites_pending_email is not listed here; Postgres lists it).
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
    "add_table bulletin_images",
````

**with:**

````python
    "add_table bulletin_images",
    "remove_constraint uq_invites_church_email",
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_head_is_0007_bulletin_images():
````

**with:**

````python
def test_head_is_0008_invites_integrity():
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_to_0007_changes(tmp_path):
````

**with:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_to_0008_changes(tmp_path):
````

**In `backend/tests/test_services_postgres.py`, replace:**

````python
    # test database is at head (0007_bulletin_images since printed bulletin PR 3a).
    assert counts == {"version": "0007_bulletin_images", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0007_bulletin_images", "new_columns": 2, "new_index": 1}
````

**with:**

````python
    # test database is at head (0008_invites_integrity since slice 6b-1).
    assert counts == {"version": "0008_invites_integrity", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0008_invites_integrity", "new_columns": 2, "new_index": 1}
````

**In `backend/tests/test_services_postgres.py`, replace:**

````python
    assert counts == {"version": "0007_bulletin_images", "services": 3, "churches": 2}
    assert applied == {"version": "0007_bulletin_images", "new_column": 1, "with_bulletin": 1}
````

**with:**

````python
    assert counts == {"version": "0008_invites_integrity", "services": 3, "churches": 2}
    assert applied == {"version": "0008_invites_integrity", "new_column": 1, "with_bulletin": 1}
````

**In `backend/tests/test_services_postgres.py`, replace:**

````python
    assert counts == {"version": "0007_bulletin_images", "services": 2, "with_bulletin": 1}
    assert applied == {"version": "0007_bulletin_images", "row_security": True, "open_grants": 0, "pictures": 1}
````

**with:**

````python
    assert counts == {"version": "0008_invites_integrity", "services": 2, "with_bulletin": 1}
    assert applied == {"version": "0008_invites_integrity", "row_security": True, "open_grants": 0, "pictures": 1}
````

**In `backend/tests/test_usecase_onboarding.py`, replace:**

````python
from repos.memberships import add_membership, get_role, remove_membership
````

**with:**

````python
from repos.memberships import add_membership, get_role, remove_membership
from tests.invite_helpers import store_unchecked_role
````

**In `backend/tests/test_usecase_onboarding.py`, replace:**

````python
    code = _invite(invite_world["church_id"], invite_world["owner"], role=stored)
````

**with:**

````python
    code = _invite(invite_world["church_id"], invite_world["owner"])
    store_unchecked_role(code, stored)                    # a row from before 0008's CHECK
````

**In `backend/tests/test_usecase_onboarding.py`, replace:**

````python
    owner_code = create_invite(church_id=cid, created_by=owner, role="owner")
````

**with:**

````python
    owner_code = create_invite(church_id=cid, created_by=owner)
    store_unchecked_role(owner_code, "owner")             # a row from before 0008's CHECK
````

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_api_invites.py backend/tests/test_usecase_onboarding.py 2>&1 | tail -1` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres backend/tests/test_migrations.py backend/tests/test_services_postgres.py 2>&1 | tail -1`
**Expected:** on SQLite, the head constants (`test_api_app.py`, `test_schema_check.py`), the baseline drift without 0008's removed constraint, the five 0008 tests (no such revision; the README has no 0008 section) and the revision-state tests that compare with the head; the clamp tests already pass through `store_unchecked_role` (the CHECK does not exist yet). On a local Postgres, the two 0008 tests and the three README-query tests of `test_services_postgres.py` (they expect the head's version):
```
16 failed, 139 passed, 9 skipped in <t>s
```
```
5 failed, 10 passed, 38 deselected in <t>s
```

- [ ] **Step 3: The revision, the model, the warning filters, the README**

The revision repairs roles, then refuses over duplicate pending emails (a `DO` block on Postgres, a `RuntimeError` on SQLite, the same words), then swaps the constraint for the index and adds the CHECK (batch mode on SQLite). The model gains the same index (with `PENDING_INVITE`, its predicate) and CHECK, so `alembic check` stays clean on Postgres. `pytest.ini` filters the two warnings SQLite's missing expression-index reflection gives, by the index's name. The README gains the owner's steps and the integrity runbook, whose queries T1's and T2's tests run.

**In `backend/db/models.py`, replace:**

````python
class Invite(Base):
````

**with:**

````python
# An invite still waiting to be used: email-bound, not revoked, not accepted
# (uq_invites_pending_email's predicate; revision 0008_invites_integrity).
PENDING_INVITE = "email IS NOT NULL AND NOT revoked AND accepted_at IS NULL"


class Invite(Base):
````

**In `backend/db/models.py`, replace:**

````python
    email = Column(String)  # nullable; when set, one pending per (church, email)
````

**with:**

````python
    email = Column(String)  # nullable (anyone with the link); stored lower-cased
````

**In `backend/db/models.py`, replace:**

````python
        # NULL emails are distinct on both SQLite and Postgres, so many
        # code-only invites coexist while an email-bound one is single-pending.
        UniqueConstraint("church_id", "email", name="uq_invites_church_email"),
````

**with:**

````python
        # Revision 0008_invites_integrity (slice 6b-1): an invite grants member
        # or admin, never owner; and one pending invite per church and email,
        # in any capitalization (a revoked, accepted or code-only one never
        # counts, so re-inviting after a revoke or an acceptance works).
        CheckConstraint("role IN ('member','admin')", name="ck_invites_role"),
        Index(
            "uq_invites_pending_email", "church_id", sa.func.lower(email), unique=True,
            postgresql_where=sa.text(PENDING_INVITE), sqlite_where=sa.text(PENDING_INVITE),
        ),
````

**In `backend/migrations/README.md`, replace:**

````markdown
  `NNNN_short_slug.py`. Head is `0007_bulletin_images`.
````

**with:**

````markdown
  `NNNN_short_slug.py`. Head is `0008_invites_integrity`.
````

**In `backend/migrations/README.md`, replace:**

````markdown
| `0007_bulletin_images` | Printed bulletin PR 3a: the table `bulletin_images` (the cover pictures, stored as JPEG in `bytes`) with the index `ix_bulletin_images_church_created`, and on Postgres row-level security on it and, when Supabase's `anon` and `authenticated` roles exist, `REVOKE ALL` on it from both. No other table changes. Before it reaches production: "Before 0007_bulletin_images" below. |
````

**with:**

````markdown
| `0007_bulletin_images` | Printed bulletin PR 3a: the table `bulletin_images` (the cover pictures, stored as JPEG in `bytes`) with the index `ix_bulletin_images_church_created`, and on Postgres row-level security on it and, when Supabase's `anon` and `authenticated` roles exist, `REVOKE ALL` on it from both. No other table changes. Before it reaches production: "Before 0007_bulletin_images" below. |
| `0008_invites_integrity` | Slice 6b-1: an invite whose role is neither `member` nor `admin` becomes an `admin` invite and is revoked; then, unless two pending invites of one church share an email in any capitalization (it refuses, naming the churches: "Church integrity" below), the unique constraint `uq_invites_church_email` is replaced by the partial unique index `uq_invites_pending_email` on `(church_id, lower(email))` for pending email invites, and the check `ck_invites_role` (`member` or `admin`) is added. No column changes. Before it reaches production: "Before 0008_invites_integrity" below. |
````

**Append to `backend/migrations/README.md`:**

````markdown

## Before 0008_invites_integrity (slice 6b-1)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0008_invites_integrity` when slice 6b-1 (the server side of People:
members, invites, ownership, leave and delete) merges. First, as the owner
decided on 2026-10-09 (6b planning answer 1, the same routine as 0007): a
backup, one read-only query that counts the invites and checks the
churches' owners, and a look at the SQL; after the deploy, one read-only
check. One step at a time. Nothing here changes data. The agent guides the
owner and records the results in `docs/ops-runbook.md` → "Slice 6b-1
record", never with an email address, a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL and the artifact's size.

### Step 2: Count the invites and check the churches (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run:

```sql
-- Read-only: the invites and the churches' owners before 0008. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM invites) AS invites,
       (SELECT count(*) FROM invites
         WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL) AS pending_email_invites,
       (SELECT count(*) FROM (SELECT 1 FROM invites
                               WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
                               GROUP BY church_id, lower(email) HAVING count(*) > 1) AS d)
         AS duplicate_pending_pairs,
       (SELECT count(*) FROM invites WHERE role NOT IN ('member', 'admin')) AS other_role_invites,
       (SELECT count(*) FROM pg_constraint WHERE conname = 'uq_invites_church_email') AS old_constraint,
       (SELECT count(*) FROM churches WHERE deleted_at IS NULL) AS churches,
       (SELECT count(*) FROM churches c
         WHERE c.deleted_at IS NULL
           AND (SELECT count(*) FROM memberships m
                 WHERE m.church_id = c.id AND m.role = 'owner') <> 1) AS churches_without_one_owner,
       (SELECT count(*) FROM churches c
         WHERE c.deleted_at IS NULL
           AND NOT EXISTS (SELECT 1 FROM memberships m
                            WHERE m.church_id = c.id AND m.role IN ('owner', 'admin')))
         AS churches_without_admin;
```

One row. Expected before the merge:

- `version` is `0007_bulletin_images` (anything else: stop);
- `invites` all invites ever made, `pending_email_invites` those bound to an
  email and still waiting;
- `duplicate_pending_pairs` is `0`. Anything else: stop. The upgrade would
  refuse (safely: the previous release keeps serving); follow "Church
  integrity" step 2 below with the agent first;
- `other_role_invites` is normally `0`; any number is fine (the upgrade
  makes those invites admin invites and revokes them): record it;
- `old_constraint` is `1` (the constraint the upgrade replaces; `0`: stop
  and tell the agent);
- `churches` the churches in use; `churches_without_one_owner` and
  `churches_without_admin` are normally `0`. They do not block this
  upgrade, but a church with no owner cannot transfer ownership or be
  deleted in the new app: tell the agent, who records it, and decide
  together whether to repair it ("Church integrity" steps 3 and 4).

This is the same check as `backend/scripts/check_integrity.py` ("Church
integrity" below), as one query for the SQL Editor.

### Step 3: Read the SQL the upgrade will run

The agent renders it from the PR's code without connecting to any database
(from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0007_bulletin_images:0008_invites_integrity --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//'
```

Expected, exactly (`backend/tests/test_migrations.py` pins it):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
UPDATE invites SET role='admin', revoked=true WHERE (invites.role NOT IN ('member', 'admin'));
DO $$
DECLARE
  pairs integer;
  church_ids text;
BEGIN
  SELECT count(*), string_agg(DISTINCT church_id::text, ', ')
    INTO pairs, church_ids
    FROM (SELECT church_id FROM invites
           WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
           GROUP BY church_id, lower(email) HAVING count(*) > 1) AS duplicates;
  IF pairs > 0 THEN
    RAISE EXCEPTION '0008_invites_integrity: % (church, email) pair(s) have more than one pending invite: %. Follow "Church integrity" in backend/migrations/README.md, then redeploy.', pairs, church_ids;
  END IF;
END $$;
ALTER TABLE invites DROP CONSTRAINT uq_invites_church_email;
ALTER TABLE invites ADD CONSTRAINT ck_invites_role CHECK (role IN ('member','admin'));
CREATE UNIQUE INDEX uq_invites_pending_email ON invites (church_id, lower(email)) WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL;
UPDATE alembic_version SET version_num='0008_invites_integrity' WHERE alembic_version.version_num = '0007_bulletin_images';
COMMIT;
```

In one transaction: invites with a role other than member or admin (only a
direct database write could make one) become admin invites and are revoked;
the check stops everything if two waiting invites of one church share an
email; the old rule (one invite per church and email, ever) is replaced by
one waiting invite per church and email, in any capitalization; and an
invite's role must be member or admin from now on. No row is deleted and
no column changes. If another connection holds a lock on `invites` for
more than 5 s, the deploy fails and the previous release keeps serving;
run the deploy again.

### Step 4: After the deploy (read-only)

SQL Editor:

```sql
-- Read-only: is 0008 applied? Changes nothing.
-- Before 0008 is applied it still runs: 0007_bulletin_images, 0, 0, 1.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM pg_indexes
         WHERE schemaname = 'public' AND indexname = 'uq_invites_pending_email') AS pending_email_index,
       (SELECT count(*) FROM pg_constraint WHERE conname = 'ck_invites_role') AS role_check,
       (SELECT count(*) FROM pg_constraint WHERE conname = 'uq_invites_church_email') AS old_constraint;
```

Expected: `0008_invites_integrity`, `1`, `1`, `0`. `0007_bulletin_images`,
`0`, `0`, `1` means the deploy has not applied 0008 yet: wait a minute and
run it again. Then step 2's query again: the same counts as before (or more
`invites` and `pending_email_invites`, by the invites made since the
deploy), except `other_role_invites` `0` and `old_constraint` `0`.

### Reverting 6b-1

The schema stays at `0008_invites_integrity`: the code before 6b-1 creates
no invites (only `POST /invites/accept` and `/preview` read them), so it
runs on it unchanged. Revert the merge commit, then restore
`backend/migrations/versions/0008_invites_integrity.py` and the `Invite`
table arguments in `backend/db/models.py` from the merge commit in the same
PR, so Railway's `alembic upgrade head` still finds the database at head and
`alembic check` stays clean. Never `alembic downgrade` production for this.

## Church integrity (slice 6b)

Every church should have exactly one owner and at least one owner or
admin, every invite should grant member or admin, and no two waiting
invites of one church should share an email. The new app keeps all of this
(slice 6b), but rows written before it, or by hand, may not.

1. **When to check:** before merging slice 6b-1 and slice 6b-2, and after
   each of their deploys. Either run "Before 0008_invites_integrity" step 2's
   query in the SQL Editor (read-only), or, from a laptop with the
   production `DATABASE_URL` (the laptop setup of "Production runbook"
   above), `../.venv/bin/python scripts/check_integrity.py` from `backend/`
   (read-only). The script prints one line per problem (its kind, the church
   id, a count) and `OK: no integrity violations.` when there is none; it
   exits 1 when it found any. Record the result (never a church id) in the
   PR or the slice's record.
2. **Duplicate pending email invites** (`duplicate_pending_pairs` above,
   `pending_duplicate` in the script; `0008` refuses to run over them): after
   a fresh backup, keep the newest pending invite per church and email, and
   revoke the rest. In the SQL Editor:
   ```sql
   UPDATE invites SET revoked = true
   WHERE id IN (
     SELECT id FROM (
       SELECT id, row_number() OVER (
         PARTITION BY church_id, lower(email) ORDER BY created_at DESC, id DESC) AS rn
       FROM invites
       WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
     ) ranked WHERE rn > 1
   );
   ```
   The people those invites were for can still use the newest one.
3. **More than one owner** in a church (`owner_count` with a count above 1):
   agree with the church who keeps ownership, then, with the agent, make the
   others admins:
   `UPDATE memberships SET role = 'admin' WHERE church_id = :c AND role = 'owner' AND user_id <> :keep;`
4. **No owner** (`owner_count` 0): pick an existing admin with the church,
   then:
   `UPDATE memberships SET role = 'owner' WHERE church_id = :c AND user_id = :new_owner;`
   If the church has no admin either (`no_admin`), pick any member.
5. **Invites with another role** (`invite_role`): `0008` repairs them; after
   it, the database refuses new ones.
6. Check again until it shows none of these, then merge. Railway's
   pre-deploy runs `alembic upgrade head`.
7. After the deploy, check once more.
````

**Create `backend/migrations/versions/0008_invites_integrity.py`:**

````python
"""Invites integrity: member/admin roles only, one pending invite per email (slice 6b-1)

6b spec, "Data and migrations" (its 0006_invites_integrity; the owner's 6b
planning answers of 2026-10-09 number it 0008). Expand-only while nothing
else shares the database (F §3.4): no column changes.

Upgrade, in order:
1. Role repair: an invite whose role is neither member nor admin (only a
   direct database write could make one; it would have granted a second
   owner) becomes an admin invite and is revoked. Data only; the downgrade
   does not undo it. Online runs log how many rows it changed.
2. Duplicate pre-check: if two pending invites (email set, not revoked, not
   accepted) of one church share an email in any capitalization, stop with
   the runbook message, naming the church ids and never an email. On
   Postgres it is a DO block (so the owner's SQL preview shows it); on
   SQLite a RuntimeError with the same words.
3. Drop the unique constraint uq_invites_church_email (church_id, email):
   it refused a re-invite after a revoke or an acceptance.
4. Create the unique index uq_invites_pending_email on
   (church_id, lower(email)) WHERE email IS NOT NULL AND NOT revoked AND
   accepted_at IS NULL: one pending invite per church and email.
5. Add the check constraint ck_invites_role: role IN ('member','admin').
   Every existing row passes it after step 1 (role is NOT NULL).

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and
statement_timeout '60s') first, and everything runs in one transaction, so
a refusal in step 2 rolls back step 1 too and the previous release keeps
serving. On SQLite steps 3 and 5 recreate the table (batch mode) and copy
its rows.

Downgrade: drop ck_invites_role and uq_invites_pending_email, then restore
uq_invites_church_email, unless two invites of one church share an exact
non-null email (re-inviting after a revoke makes such pairs legitimately):
then it refuses with a RuntimeError, and nothing changes.

Revision ID: 0008_invites_integrity
Revises: 0007_bulletin_images
Create Date: 2026-10-09
"""
import logging
import uuid

from alembic import context, op
import sqlalchemy as sa

revision = "0008_invites_integrity"
down_revision = "0007_bulletin_images"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

PENDING = "email IS NOT NULL AND NOT revoked AND accepted_at IS NULL"
ROLES = "role IN ('member','admin')"
DUPLICATES_MESSAGE = (
    "0008_invites_integrity: {pairs} (church, email) pair(s) have more than one pending invite: {churches}. "
    "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy."
)

# A lightweight table for the data step: never the ORM model, which keeps changing.
invites = sa.table(
    "invites",
    sa.column("role", sa.String()),
    sa.column("revoked", sa.Boolean()),
)

# The pending duplicates: one row per (church, lower(email)) with more than one pending invite.
DUPLICATES_SQL = """\
SELECT church_id FROM invites
           WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
           GROUP BY church_id, lower(email) HAVING count(*) > 1"""

# Step 2 on Postgres: the same refusal inside the migration's transaction.
DUPLICATES_CHECK_PG = """\
DO $$
DECLARE
  pairs integer;
  church_ids text;
BEGIN
  SELECT count(*), string_agg(DISTINCT church_id::text, ', ')
    INTO pairs, church_ids
    FROM (""" + DUPLICATES_SQL + """) AS duplicates;
  IF pairs > 0 THEN
    RAISE EXCEPTION '0008_invites_integrity: % (church, email) pair(s) have more than one pending invite: %. Follow "Church integrity" in backend/migrations/README.md, then redeploy.', pairs, church_ids;
  END IF;
END $$"""


def upgrade() -> None:
    dialect = op.get_context().dialect.name
    repair = invites.update().where(invites.c.role.not_in(["member", "admin"])).values(
        role="admin", revoked=sa.true())
    if context.is_offline_mode():
        op.execute(repair)
    else:
        repaired = op.get_bind().execute(repair).rowcount
        logger.info("0008_invites_integrity: %d invite(s) with another role made admin and revoked", repaired)
    if dialect == "postgresql":
        op.execute(DUPLICATES_CHECK_PG)
    else:
        rows = op.get_bind().execute(sa.text(DUPLICATES_SQL)).all()
        if rows:
            churches = ", ".join(sorted({str(uuid.UUID(str(row[0]))) for row in rows}))   # SQLite keeps hex
            raise RuntimeError(DUPLICATES_MESSAGE.format(pairs=len(rows), churches=churches))
    with op.batch_alter_table("invites") as batch:
        batch.drop_constraint("uq_invites_church_email", type_="unique")
        batch.create_check_constraint("ck_invites_role", ROLES)
    op.create_index(
        "uq_invites_pending_email", "invites", ["church_id", sa.text("lower(email)")], unique=True,
        postgresql_where=sa.text(PENDING), sqlite_where=sa.text(PENDING))


def downgrade() -> None:
    pairs = op.get_bind().execute(sa.text(
        "SELECT church_id, email FROM invites WHERE email IS NOT NULL "
        "GROUP BY church_id, email HAVING count(*) > 1")).all()
    if pairs:   # checked before any change: SQLite runs DDL outside a transaction
        raise RuntimeError(
            f"Cannot restore uq_invites_church_email: {len(pairs)} (church, email) pairs have more than one "
            "invite. Delete the revoked or accepted duplicates first.")
    op.drop_index("uq_invites_pending_email", table_name="invites")
    with op.batch_alter_table("invites") as batch:
        batch.drop_constraint("ck_invites_role", type_="check")
        batch.create_unique_constraint("uq_invites_church_email", ["church_id", "email"])
````

**Append to `pytest.ini`:**

````ini
filterwarnings =
    # SQLite reflects no expression index; Postgres compares uq_invites_pending_email (slice 6b-1).
    ignore:Skipped unsupported reflection of expression-based index uq_invites_pending_email:sqlalchemy.exc.SAWarning
    ignore:autogenerate skipping metadata-specified expression-based index .uq_invites_pending_email.:UserWarning
````

- [ ] **Step 4: Run the files, the offline SQL and the suite (and Postgres)**

Run: `.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_api_invites.py backend/tests/test_usecase_onboarding.py backend/tests/test_models.py 2>&1 | tail -1` then `(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0007_bulletin_images:0008_invites_integrity --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//' | wc -l)` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:** the files pass; the preview is the 23 lines of README step 3 (`BEGIN;` … `COMMIT;`); every Postgres test passes (the warning is the existing one, not 0008's); the suite as the table says:
```
159 passed, 9 skipped in <t>s
```
```
23
```
```
37 passed, 1988 deselected, 1 warning in <t>s
```
```
1988 passed, 37 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/versions/0008_invites_integrity.py backend/db/models.py backend/migrations/README.md pytest.ini backend/tests/invite_helpers.py backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py backend/tests/test_api_invites.py backend/tests/test_usecase_onboarding.py
git commit -q -m "Migration 0008_invites_integrity: member/admin invites, one pending invite per email" -m "Slice 6b-1 (6b spec \"Data and migrations\"; the owner's 6b planning
answers number it 0008): an invite with another role becomes an admin
invite and is revoked; the upgrade refuses, naming the churches and never an
email, while two pending invites of one church share an email in any
capitalization (a DO block on Postgres, shown in the SQL preview; a
RuntimeError on SQLite); then uq_invites_church_email gives way to the
partial unique index uq_invites_pending_email on (church_id, lower(email))
and the check ck_invites_role. The downgrade refuses over exact duplicates.
The Invite model matches; pytest.ini filters SQLite's two expression-index
warnings by name. backend/migrations/README.md gains \"Before
0008_invites_integrity\" (backup, one read-only query with the counts and
the integrity check, the SQL preview pinned by a test, the after-deploy
check, reverting) and \"Church integrity (slice 6b)\". Slice 1's clamp tests
store their bad role through tests/invite_helpers.py." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1988 passed, 37 skipped`; frontend `952 passed` in 109 files.

### Task 2: The integrity check: `repos/integrity.py` and `scripts/check_integrity.py` (S "Backend changes" rows for both, Testing → Integrity; clarification 9)

**Files:**
- Create: `backend/tests/test_integrity.py`, `backend/repos/integrity.py`, `backend/scripts/check_integrity.py`

`find_violations` reports the four kinds (owner count not one, no admin, another role, duplicate pending emails) for churches in use, ids and counts only; the runbook's dedupe step (read from the README) keeps the newest pending invite; the script prints one line per problem with no email, name or code and exits 1, prints "OK: no integrity violations." and exits 0, or exits 2 without `DATABASE_URL`. On Postgres, the README's step 2 query (the SQL Editor's way) counts what `find_violations` finds.

- [ ] **Step 1: Write the failing tests**

**Create `backend/tests/test_integrity.py`:**

````python
"""repos.integrity.find_violations and scripts/check_integrity.py (6b spec,
"Church integrity runbook" and Testing → Integrity; slice 6b-1): each kind is
found, soft-deleted churches are skipped, the output holds ids and counts
only, and the runbook's dedupe step leaves the newest pending invite."""
import importlib.util
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import select, text, update

from db import session_scope
from db.models import Church, Invite, Membership
from repos.integrity import find_violations
from repos.invites import create_invite
from repos.memberships import add_membership
from tests.invite_helpers import store_unchecked_role

BACKEND = Path(__file__).resolve().parents[1]
SCRIPT = BACKEND / "scripts" / "check_integrity.py"
README = BACKEND / "migrations" / "README.md"
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def _load_check_integrity():
    """backend/scripts is not a package: load the script by path, as `python scripts/…` does."""
    spec = importlib.util.spec_from_file_location("check_integrity_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def grace(make_user, make_church):
    owner = make_user(email="owner@example.com", name="Olive Owner")
    church = make_church(name="Grace", owner_user_id=owner)
    add_membership(make_user(email="admin@example.com"), church, "admin")
    return church, owner


def _set_roles(church, role, *, where_role):
    with session_scope() as s:
        s.execute(update(Membership).where(Membership.church_id == church, Membership.role == where_role)
                  .values(role=role))


def _pending(church, owner, email, *, created_at=NOW) -> uuid.UUID:
    invite_id = uuid.uuid4()
    with session_scope() as s:
        s.add(Invite(id=invite_id, church_id=church, code=uuid.uuid4().hex, email=email, role="member",
                     created_by=owner, created_at=created_at, expires_at=created_at + timedelta(days=7)))
    return invite_id


def test_a_clean_church_has_no_violations(grace):
    church, owner = grace
    create_invite(church_id=church, created_by=owner, email="new@example.com")
    assert find_violations() == []


def test_an_ownerless_church_and_one_with_no_admin_are_reported(grace, make_church, make_user):
    church, _ = grace
    _set_roles(church, "admin", where_role="owner")            # demoted directly in SQL: no owner
    lonely = make_church(name="Hope", owner_user_id=make_user(email="hope@example.com"))
    _set_roles(lonely, "member", where_role="owner")           # no owner and no admin
    gone = make_church(name="Gone", owner_user_id=make_user(email="gone@example.com"))
    _set_roles(gone, "member", where_role="owner")
    with session_scope() as s:                                  # soft-deleted: not checked
        s.execute(update(Church).where(Church.id == gone).values(deleted_at=NOW))
    found = find_violations()
    assert sorted((v["kind"], v["church_id"], v.get("owners")) for v in found) == sorted([
        ("owner_count", church, 0), ("owner_count", lonely, 0), ("no_admin", lonely, None)])


def test_two_owners_are_reported(grace):
    church, _ = grace
    _set_roles(church, "owner", where_role="admin")
    assert find_violations() == [{"kind": "owner_count", "church_id": church, "owners": 2}]


def test_an_invite_with_another_role_is_reported(grace):
    church, owner = grace
    code = create_invite(church_id=church, created_by=owner)
    store_unchecked_role(code, "owner")
    with session_scope() as s:
        invite_id = s.execute(select(Invite.id).where(Invite.code == code)).scalar_one()
    assert find_violations() == [{"kind": "invite_role", "church_id": church, "invite_id": invite_id}]


def test_duplicate_pending_invites_are_reported_and_the_runbook_step_keeps_the_newest(grace):
    church, owner = grace
    with session_scope() as s:                  # as a database from before 0008 could hold them
        s.execute(text("DROP INDEX uq_invites_pending_email"))
    older = _pending(church, owner, "dup@example.com")
    newer = _pending(church, owner, "DUP@example.com", created_at=NOW + timedelta(hours=1))
    _pending(church, owner, "other@example.com")
    assert find_violations() == [{"kind": "pending_duplicate", "church_id": church, "invites": 2}]
    step = re.search(r"\n2\. \*\*Duplicate pending email invites\*\*.*?```sql\n(.*?)```",
                     README.read_text(encoding="utf-8"), re.S).group(1)
    with session_scope() as s:
        s.execute(text(step))
    with session_scope() as s:
        revoked = dict(s.execute(select(Invite.id, Invite.revoked).where(Invite.id.in_([older, newer]))).all())
    assert revoked == {older: True, newer: False}
    assert find_violations() == []


def test_the_script_prints_ids_and_counts_only_and_exits_1(grace, tmp_db, monkeypatch, capsys):
    church, owner = grace
    _set_roles(church, "admin", where_role="owner")
    code = create_invite(church_id=church, created_by=owner, email="secret@example.com")
    store_unchecked_role(code, "owner")
    monkeypatch.setenv("DATABASE_URL", str(tmp_db.url))
    assert _load_check_integrity().main([]) == 1
    out, err = capsys.readouterr()
    with session_scope() as s:
        invite_id = s.execute(select(Invite.id).where(Invite.code == code)).scalar_one()
    assert out.splitlines() == [f"owner_count church={church} owners=0", f"invite_role church={church} invite={invite_id}"]
    assert err.startswith("Database: dialect=sqlite")
    for secret in ("secret@example.com", "owner@example.com", "Olive", "Grace", code):
        assert secret not in out + err


def test_the_script_says_ok_and_exits_0_when_clean(grace, tmp_db, monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", str(tmp_db.url))
    assert _load_check_integrity().main([]) == 0
    assert capsys.readouterr().out == "OK: no integrity violations.\n"


def test_the_script_refuses_without_database_url(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert _load_check_integrity().main([]) == 2
    assert capsys.readouterr().err == "DATABASE_URL is not set.\n"


@pytest.mark.postgres
def test_the_readme_query_counts_what_the_script_finds_on_postgres():
    """README "Before 0008_invites_integrity" step 2 (the SQL Editor's way) and
    find_violations (check_integrity.py's way) agree, on a database at 0007
    holding one problem of each kind (plus a second ownerless church)."""
    import os

    from alembic import command
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import NullPool

    from db.engine import _normalize_url
    from db.schema_check import alembic_config
    from tests.pg_helpers import require_local_test_url, throwaway_database

    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set (the backend-postgres CI job sets it)")
    readme = README.read_text(encoding="utf-8").split("\n## Before 0008_invites_integrity (slice 6b-1)\n", 1)[1]
    counts_sql = re.findall(r"```sql\n(.*?)```", readme, re.S)[0]
    with throwaway_database(require_local_test_url(url), role_bypassrls=True) as sandbox:
        command.upgrade(alembic_config(url=sandbox.role_url, configure_logger=False), "0007_bulletin_images")
        engine = create_engine(_normalize_url(sandbox.role_url), poolclass=NullPool)
        try:
            with Session(engine) as s, s.begin():
                user, grace, hope, joy = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
                s.execute(text("INSERT INTO users (id, email, created_at) VALUES (:u, 'p@example.com', now())"),
                          {"u": user})
                for church in (grace, hope, joy):
                    s.execute(text("INSERT INTO churches (id, name, timezone, settings, created_at) "
                                   "VALUES (:c, 'C', 'UTC', '{}', now())"), {"c": church})
                s.execute(text("INSERT INTO memberships (church_id, user_id, role, created_at) VALUES "
                               "(:g, :u, 'owner', now()), (:h, :u, 'admin', now()), (:j, :u, 'member', now())"),
                          {"g": grace, "h": hope, "j": joy, "u": user})
                for email, role in (("dup@example.com", "member"), ("Dup@example.com", "member"),
                                    (None, "owner")):
                    s.execute(text(
                        "INSERT INTO invites (id, church_id, code, email, role, created_by, created_at, expires_at, "
                        "revoked, reusable) VALUES (:id, :c, :code, :email, :role, :u, now(), now() + interval '7 days', "
                        "false, false)"),
                        {"id": uuid.uuid4(), "c": grace, "code": uuid.uuid4().hex, "email": email, "role": role,
                         "u": user})
            with Session(engine) as s:
                kinds = [v["kind"] for v in find_violations(session=s)]
                counts = dict(s.execute(text(counts_sql)).mappings().one())
        finally:
            engine.dispose()
    assert kinds == ["owner_count", "owner_count", "no_admin", "invite_role", "pending_duplicate"]
    assert (counts["churches_without_one_owner"], counts["churches_without_admin"], counts["other_role_invites"],
            counts["duplicate_pending_pairs"]) == (2, 1, 1, 1)
````

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_integrity.py 2>&1 | tail -1`
**Expected** (the module does not exist yet):
```
1 error in <t>s
```

- [ ] **Step 3: The repo and the script**

**Create `backend/repos/integrity.py`:**

````python
"""Church integrity checks (6b spec, "Church integrity runbook"; slice 6b-1).

find_violations reads, never writes, and returns ids and counts only: no
email, name or invite code. The kinds, in this order:
- owner_count: a church in use whose owner count is not exactly one
  {"kind", "church_id", "owners"};
- no_admin: a church in use with no owner or admin {"kind", "church_id"};
- invite_role: an invite whose role is neither member nor admin
  {"kind", "church_id", "invite_id"} (0008_invites_integrity repairs these,
  and the database refuses new ones);
- pending_duplicate: more than one pending invite (email set, not revoked,
  not accepted) for one church and email in any capitalization
  {"kind", "church_id", "invites"} (0008 refuses to run over these).
Within a kind, rows are ordered by church id (then invite id). A church in
use is one not soft-deleted; invites are checked in every church.
backend/scripts/check_integrity.py prints them; the README's "Before
0008_invites_integrity" step 2 query counts the same things.
"""
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from db import session_scope
from db.models import Church, Invite, Membership

ROLES = ("member", "admin")


def find_violations(*, session: Optional[Session] = None) -> list[dict]:
    if session is not None:
        return _find_violations(session)
    with session_scope() as own:
        return _find_violations(own)


def _find_violations(s: Session) -> list[dict]:
    owners = (
        select(func.count()).select_from(Membership)
        .where(Membership.church_id == Church.id, Membership.role == "owner")
        .scalar_subquery()
    )
    admins = (
        select(func.count()).select_from(Membership)
        .where(Membership.church_id == Church.id, Membership.role.in_(("owner", "admin")))
        .scalar_subquery()
    )
    in_use = Church.deleted_at.is_(None)
    found = [
        {"kind": "owner_count", "church_id": church_id, "owners": count}
        for church_id, count in s.execute(
            select(Church.id, owners).where(in_use, owners != 1).order_by(Church.id))
    ]
    found += [
        {"kind": "no_admin", "church_id": church_id}
        for church_id in s.execute(select(Church.id).where(in_use, admins == 0).order_by(Church.id)).scalars()
    ]
    found += [
        {"kind": "invite_role", "church_id": church_id, "invite_id": invite_id}
        for church_id, invite_id in s.execute(
            select(Invite.church_id, Invite.id).where(Invite.role.not_in(ROLES))
            .order_by(Invite.church_id, Invite.id))
    ]
    pending = and_(Invite.email.is_not(None), Invite.revoked.is_(False), Invite.accepted_at.is_(None))
    found += [
        {"kind": "pending_duplicate", "church_id": church_id, "invites": count}
        for church_id, count in s.execute(
            select(Invite.church_id, func.count()).where(pending)
            .group_by(Invite.church_id, func.lower(Invite.email))
            .having(func.count() > 1)
            .order_by(Invite.church_id, func.lower(Invite.email)))
    ]
    return found
````

**Create `backend/scripts/check_integrity.py`:**

````python
"""Check every church for the problems slice 6b's rules forbid (read-only).

Run from backend/ with DATABASE_URL exported in the same shell (the laptop
setup of backend/migrations/README.md, "Production runbook"):

    ../.venv/bin/python scripts/check_integrity.py

Prints one line per problem found by repos.integrity.find_violations: its
kind, the church id and a count (or the invite id), never an email, a name or
an invite code; or "OK: no integrity violations." Exit status: 0 when there
is none, 1 when there is one, 2 when DATABASE_URL is not set. It only reads.
The `Database:` line goes to stderr and never shows the username or
password. backend/migrations/README.md, "Church integrity", says what to do
with each kind.
"""
import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))   # run as a file, sys.path[0] is backend/scripts

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from api.startup import describe_database  # noqa: E402
from db.engine import _normalize_url  # noqa: E402
from repos.integrity import find_violations  # noqa: E402

OK = "OK: no integrity violations."


def format_violation(v: dict) -> str:
    """One line: the kind, then church=<id> and the kind's count or invite id."""
    extra = {"owner_count": lambda: f" owners={v['owners']}",
             "no_admin": lambda: "",
             "invite_role": lambda: f" invite={v['invite_id']}",
             "pending_duplicate": lambda: f" invites={v['invites']}"}[v["kind"]]()
    return f"{v['kind']} church={v['church_id']}{extra}"


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(argv)
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        return 2
    engine = create_engine(_normalize_url(url), poolclass=NullPool)
    print(f"Database: {describe_database(engine.url)}", file=sys.stderr)
    try:
        with Session(engine) as session:
            violations = find_violations(session=session)
    finally:
        engine.dispose()
    for v in violations:
        print(format_violation(v))
    if not violations:
        print(OK)
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
````

- [ ] **Step 4: Run the file (and Postgres) and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_integrity.py 2>&1 | tail -1` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q backend/tests/test_integrity.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
8 passed, 1 skipped in <t>s
```
```
9 passed in <t>s
```
```
1996 passed, 38 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/repos/integrity.py backend/scripts/check_integrity.py backend/tests/test_integrity.py
git commit -q -m "Slice 6b-1: the church integrity check (repos.integrity, check_integrity.py)" -m "find_violations reports, for churches in use, an owner count other than
one, no owner or admin, an invite role other than member or admin, and
more than one pending invite for one church and email; ids and counts
only. scripts/check_integrity.py prints them (or \"OK: no integrity
violations.\") and exits 1 (or 0); it reads only an exported DATABASE_URL,
like schema_drift.py, and exits 2 without one. A Postgres test checks that
the README's SQL Editor query counts the same things." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1996 passed, 38 skipped`; frontend `952 passed` in 109 files.

### Task 3: The role policy and its shared fixture (S "Role policy", Testing → "Pure policy"; acceptance 2)

**Files:**
- Create: `backend/tests/fixtures/shared/role_policy.json`, `backend/tests/test_role_policy.py`, `backend/usecases/role_policy.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

The fixture holds exactly the 51 reachable states of the four checks (S "State rules": the test builds every state and drops the two unreachable kinds, then compares), and each row's outcome, error type, code, message and field holds. The checks are pure: no database. The fixture is shared because 6b-2's People page mirrors its change-role and remove rows.

- [ ] **Step 1: Write the failing tests**

**Create `backend/tests/fixtures/shared/role_policy.json`:**

````json
{
  "_about": "Role policy (6b spec, \"Role policy\"; owner decision 5): every reachable state of the four pure checks in backend/usecases/role_policy.py (change_role, remove, leave, transfer), 51 rows. actor_role is the role re-read under the church-row lock; target is self or another member's role; admin_count (leave) counts owner and admin memberships, the leaver's included. expected: allow, noop, forbidden (403), owner_must_transfer or last_admin (409), invalid (422, naming field). backend/tests/test_role_policy.py runs every row; slice 6b-2's People page mirrors the change_role and remove rows.",
  "rows": [
    {"action": "change_role", "actor_role": "owner", "target": "self", "new_role": "member", "expected": "forbidden", "message": "You can't change your own role."},
    {"action": "change_role", "actor_role": "owner", "target": "self", "new_role": "admin", "expected": "forbidden", "message": "You can't change your own role."},
    {"action": "change_role", "actor_role": "owner", "target": "admin", "new_role": "member", "expected": "allow"},
    {"action": "change_role", "actor_role": "owner", "target": "admin", "new_role": "admin", "expected": "noop"},
    {"action": "change_role", "actor_role": "owner", "target": "member", "new_role": "member", "expected": "noop"},
    {"action": "change_role", "actor_role": "owner", "target": "member", "new_role": "admin", "expected": "allow"},
    {"action": "change_role", "actor_role": "admin", "target": "self", "new_role": "member", "expected": "forbidden", "message": "You can't change your own role."},
    {"action": "change_role", "actor_role": "admin", "target": "self", "new_role": "admin", "expected": "forbidden", "message": "You can't change your own role."},
    {"action": "change_role", "actor_role": "admin", "target": "owner", "new_role": "member", "expected": "forbidden", "message": "The owner's role can't be changed."},
    {"action": "change_role", "actor_role": "admin", "target": "owner", "new_role": "admin", "expected": "forbidden", "message": "The owner's role can't be changed."},
    {"action": "change_role", "actor_role": "admin", "target": "admin", "new_role": "member", "expected": "allow"},
    {"action": "change_role", "actor_role": "admin", "target": "admin", "new_role": "admin", "expected": "noop"},
    {"action": "change_role", "actor_role": "admin", "target": "member", "new_role": "member", "expected": "noop"},
    {"action": "change_role", "actor_role": "admin", "target": "member", "new_role": "admin", "expected": "allow"},
    {"action": "change_role", "actor_role": "member", "target": "self", "new_role": "member", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "change_role", "actor_role": "member", "target": "self", "new_role": "admin", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "change_role", "actor_role": "member", "target": "owner", "new_role": "member", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "change_role", "actor_role": "member", "target": "owner", "new_role": "admin", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "change_role", "actor_role": "member", "target": "admin", "new_role": "member", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "change_role", "actor_role": "member", "target": "admin", "new_role": "admin", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "change_role", "actor_role": "member", "target": "member", "new_role": "member", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "change_role", "actor_role": "member", "target": "member", "new_role": "admin", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "remove", "actor_role": "owner", "target": "self", "expected": "forbidden", "message": "To leave this church, use Leave church in Danger zone."},
    {"action": "remove", "actor_role": "owner", "target": "admin", "expected": "allow"},
    {"action": "remove", "actor_role": "owner", "target": "member", "expected": "allow"},
    {"action": "remove", "actor_role": "admin", "target": "self", "expected": "forbidden", "message": "To leave this church, use Leave church in Danger zone."},
    {"action": "remove", "actor_role": "admin", "target": "owner", "expected": "forbidden", "message": "The owner can't be removed."},
    {"action": "remove", "actor_role": "admin", "target": "admin", "expected": "allow"},
    {"action": "remove", "actor_role": "admin", "target": "member", "expected": "allow"},
    {"action": "remove", "actor_role": "member", "target": "self", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "remove", "actor_role": "member", "target": "owner", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "remove", "actor_role": "member", "target": "admin", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "remove", "actor_role": "member", "target": "member", "expected": "forbidden", "message": "Only church admins can do this."},
    {"action": "leave", "actor_role": "owner", "admin_count": 1, "expected": "owner_must_transfer", "message": "Transfer ownership before you leave. If you're the only person in the church, delete it instead."},
    {"action": "leave", "actor_role": "owner", "admin_count": 2, "expected": "owner_must_transfer", "message": "Transfer ownership before you leave. If you're the only person in the church, delete it instead."},
    {"action": "leave", "actor_role": "admin", "admin_count": 1, "expected": "last_admin", "message": "You're the last admin. Make someone else an admin before you leave."},
    {"action": "leave", "actor_role": "admin", "admin_count": 2, "expected": "allow"},
    {"action": "leave", "actor_role": "member", "admin_count": 0, "expected": "allow"},
    {"action": "leave", "actor_role": "member", "admin_count": 1, "expected": "allow"},
    {"action": "leave", "actor_role": "member", "admin_count": 2, "expected": "allow"},
    {"action": "transfer", "actor_role": "owner", "target": "self", "expected": "invalid", "message": "Choose someone else to be the new owner.", "field": "user_id"},
    {"action": "transfer", "actor_role": "owner", "target": "admin", "expected": "allow"},
    {"action": "transfer", "actor_role": "owner", "target": "member", "expected": "allow"},
    {"action": "transfer", "actor_role": "admin", "target": "self", "expected": "forbidden", "message": "Only the owner can do that."},
    {"action": "transfer", "actor_role": "admin", "target": "owner", "expected": "forbidden", "message": "Only the owner can do that."},
    {"action": "transfer", "actor_role": "admin", "target": "admin", "expected": "forbidden", "message": "Only the owner can do that."},
    {"action": "transfer", "actor_role": "admin", "target": "member", "expected": "forbidden", "message": "Only the owner can do that."},
    {"action": "transfer", "actor_role": "member", "target": "self", "expected": "forbidden", "message": "Only the owner can do that."},
    {"action": "transfer", "actor_role": "member", "target": "owner", "expected": "forbidden", "message": "Only the owner can do that."},
    {"action": "transfer", "actor_role": "member", "target": "admin", "expected": "forbidden", "message": "Only the owner can do that."},
    {"action": "transfer", "actor_role": "member", "target": "member", "expected": "forbidden", "message": "Only the owner can do that."}
  ]
}
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth, usecases.email, bulletin_email, hymnal_sources, usecases.hymn_library, usecases.prayer_library; "
````

**with:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth, usecases.email, bulletin_email, hymnal_sources, usecases.hymn_library, usecases.prayer_library, usecases.role_policy, repos.integrity; "
````

**Create `backend/tests/test_role_policy.py`:**

````python
"""usecases.role_policy against tests/fixtures/shared/role_policy.json (6b spec,
Testing → "Pure policy"; F acceptance 19; slice 6b-1): the fixture holds
exactly the reachable states of the four checks, and every row's outcome,
code, message and field holds."""
import itertools
import json
import uuid
from pathlib import Path

import pytest

from domain_errors import Conflict, Forbidden, InvalidInput
from usecases import role_policy

FIXTURE = Path(__file__).parent / "fixtures" / "shared" / "role_policy.json"
ROWS = json.loads(FIXTURE.read_text(encoding="utf-8"))["rows"]
ROLES = ("owner", "admin", "member")
TARGETS = ("self", "owner", "admin", "member")
ACTOR, OTHER = uuid.UUID(int=1), uuid.UUID(int=2)


def _key(row: dict) -> tuple:
    return (row["action"], row["actor_role"], row.get("target"), row.get("new_role"), row.get("admin_count"))


def _reachable() -> set[tuple]:
    """Every state the database can hold: the owner acting on "owner" is self
    (one owner per church), and an owner or admin leaving counts themselves."""
    states = set()
    for actor, target in itertools.product(ROLES, TARGETS):
        if actor == "owner" and target == "owner":
            continue
        states |= {("change_role", actor, target, new_role, None) for new_role in ("member", "admin")}
        states |= {("remove", actor, target, None, None), ("transfer", actor, target, None, None)}
    for actor, count in itertools.product(ROLES, (0, 1, 2)):
        if not (count == 0 and actor in ("owner", "admin")):
            states.add(("leave", actor, None, None, count))
    return states


def test_the_fixture_holds_exactly_the_51_reachable_states():
    keys = [_key(row) for row in ROWS]
    assert len(keys) == len(set(keys)) == 51
    assert set(keys) == _reachable()


def _call(row: dict):
    target_id = ACTOR if row.get("target") == "self" else OTHER
    target_role = row["actor_role"] if row.get("target") == "self" else row.get("target")
    action = row["action"]
    if action == "change_role":
        return role_policy.check_role_change(actor_id=ACTOR, actor_role=row["actor_role"], target_id=target_id,
                                             target_role=target_role, new_role=row["new_role"])
    if action == "remove":
        return role_policy.check_remove(actor_id=ACTOR, actor_role=row["actor_role"], target_id=target_id,
                                        target_role=target_role)
    if action == "leave":
        return role_policy.check_leave(role=row["actor_role"], admin_count=row["admin_count"])
    return role_policy.check_transfer(actor_id=ACTOR, actor_role=row["actor_role"], target_id=target_id)


ERRORS = {"forbidden": (Forbidden, "forbidden"), "invalid": (InvalidInput, "invalid_request"),
          "owner_must_transfer": (Conflict, "owner_must_transfer"), "last_admin": (Conflict, "last_admin")}


@pytest.mark.parametrize("row", ROWS, ids=lambda row: "-".join(str(v) for v in _key(row) if v is not None))
def test_every_row_has_its_outcome(row):
    if row["expected"] in ("allow", "noop"):
        result = _call(row)
        expected = {"allow": "change" if row["action"] == "change_role" else None, "noop": "noop"}[row["expected"]]
        assert result == expected
        return
    kind, code = ERRORS[row["expected"]]
    with pytest.raises(kind) as raised:
        _call(row)
    assert (type(raised.value), raised.value.code, raised.value.message, raised.value.field, raised.value.details) == (
        kind, code, row["message"], row.get("field"), None)
````

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_role_policy.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1`
**Expected** (`usecases.role_policy` does not exist yet, so the policy file cannot load and the import check fails):
```
1 error in <t>s
```

- [ ] **Step 3: The policy**

**Create `backend/usecases/role_policy.py`:**

````python
"""Who may change roles, remove people, leave and transfer ownership (6b spec,
"Role policy"; owner decision 5; slice 6b-1).

Pure functions over a state the database can hold: no database, no FastAPI,
Starlette or Streamlit (usecases/__init__.py). The usecases call them with
the caller's role re-read under the church-row lock
(usecases.members.lock_and_read_actor), after looking up the target: a
missing target is the usecase's 404, never a policy outcome, so nothing here
raises NotFound. Each check stops at the first rule that refuses, in the
spec's evaluation order, so every case has one message. The rows of
tests/fixtures/shared/role_policy.json (every reachable state, 51 rows) pin
each outcome; slice 6b-2's People page mirrors the change-role and remove
rows to decide which actions it shows.
"""
import uuid
from typing import Literal

from domain_errors import Conflict, Forbidden, InvalidInput

ADMIN_ROLES = ("owner", "admin")

NOT_ADMIN = "Only church admins can do this."
OWN_ROLE = "You can't change your own role."
OWNERS_ROLE = "The owner's role can't be changed."
REMOVE_SELF = "To leave this church, use Leave church in Danger zone."
REMOVE_OWNER = "The owner can't be removed."
OWNER_ONLY = "Only the owner can do that."
TRANSFER_TO_SELF = "Choose someone else to be the new owner."
OWNER_MUST_TRANSFER = ("Transfer ownership before you leave. If you're the only person in the church, "
                       "delete it instead.")
LAST_ADMIN = "You're the last admin. Make someone else an admin before you leave."


def check_role_change(*, actor_id: uuid.UUID, actor_role: str, target_id: uuid.UUID, target_role: str,
                      new_role: str) -> Literal["change", "noop"]:
    """PATCH /members/{user_id}: "change", or "noop" when the target already
    has `new_role` (member or admin; Pydantic refuses owner before this).
    Refuses a non-admin, a change to one's own role and a change to the
    owner's role."""
    if actor_role not in ADMIN_ROLES:
        raise Forbidden(NOT_ADMIN)
    if target_id == actor_id:
        raise Forbidden(OWN_ROLE)
    if target_role == "owner":
        raise Forbidden(OWNERS_ROLE)
    return "noop" if new_role == target_role else "change"


def check_remove(*, actor_id: uuid.UUID, actor_role: str, target_id: uuid.UUID, target_role: str) -> None:
    """DELETE /members/{user_id}: refuses a non-admin, removing oneself (that
    is Leave church) and removing the owner."""
    if actor_role not in ADMIN_ROLES:
        raise Forbidden(NOT_ADMIN)
    if target_id == actor_id:
        raise Forbidden(REMOVE_SELF)
    if target_role == "owner":
        raise Forbidden(REMOVE_OWNER)


def check_leave(*, role: str, admin_count: int) -> None:
    """POST /church/leave: the owner must transfer first (409
    owner_must_transfer); the only owner or admin of a church (one with no
    owner, made before slice 6b) may not leave it with nobody to run it (409
    last_admin). `admin_count` counts owner and admin memberships, the
    leaver's included."""
    if role == "owner":
        raise Conflict(OWNER_MUST_TRANSFER, code="owner_must_transfer")
    if role in ADMIN_ROLES and admin_count <= 1:
        raise Conflict(LAST_ADMIN, code="last_admin")


def check_transfer(*, actor_id: uuid.UUID, actor_role: str, target_id: uuid.UUID) -> None:
    """POST /church/transfer-ownership: only the owner, and to someone else
    (422 naming user_id)."""
    if actor_role != "owner":
        raise Forbidden(OWNER_ONLY)
    if target_id == actor_id:
        raise InvalidInput(TRANSFER_TO_SELF, field="user_id")
````

- [ ] **Step 4: Run the files and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_role_policy.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
55 passed in <t>s
```
```
2048 passed, 38 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/usecases/role_policy.py backend/tests/fixtures/shared/role_policy.json backend/tests/test_role_policy.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Slice 6b-1: the role policy and its 51-row shared fixture" -m "usecases/role_policy.py: check_role_change, check_remove, check_leave and
check_transfer, pure, each stopping at the first rule that refuses with the
6b spec's exact message (403, the 409s owner_must_transfer and last_admin,
or the 422 naming user_id). tests/fixtures/shared/role_policy.json holds
exactly the 51 reachable states, which test_role_policy.py checks before
running every row; 6b-2's People page will mirror its change-role and
remove rows. test_no_streamlit_in_core.py covers role_policy and
repos.integrity." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2048 passed, 38 skipped`; frontend `952 passed` in 109 files.

### Task 4: The repos: members, invites and the church's delete (S "Repo changes"; clarifications 10, 11)

**Files:**
- Modify: `backend/tests/test_memberships_repo.py`, `backend/tests/test_invites_repo.py`, `backend/tests/test_churches_repo.py`, `backend/tests/test_usecase_onboarding.py`, `backend/repos/memberships.py`, `backend/repos/invites.py`, `backend/repos/churches.py`

The new reads and writes take the caller's session, so a usecase runs them under its church-row lock. The members' order (the owner, admins, members, each by name or else email, then id); the lookups scoped to the church; `set_role` and `remove_membership` in a caller's session (rolled back with it); the transfer's two UPDATEs in order (demote, then promote); `insert_invite` returning the whole row; the live-invite list (not revoked, not expired, unused unless reusable, newest first, the creator or `None`); the pending-email lookups ignoring case; the two revocations counted and scoped; `revoke_invite` saying whether the church has the invite (a string id works, a malformed one is `NotFound`); the delete revoking a used reusable link too and saying whether it deleted. Every old caller (the frozen Streamlit pages among them) keeps its positional call. One slice 1 test that deleted a church through `soft_delete_church` to keep a consumed invite live now sets `deleted_at` directly (clarification 11).

- [ ] **Step 1: Write the failing tests**

**Append to `backend/tests/test_churches_repo.py`:**

````python


def test_soft_delete_revokes_every_unrevoked_invite_and_says_whether_it_deleted(tmp_db, make_user):
    """Slice 6b: a used reusable link is revoked too (inv §1 B3), in the caller's session."""
    owner = make_user(email="o4@x.com")
    cid = create_church(name="Joy", timezone="UTC", owner_user_id=owner)
    later = datetime.now(timezone.utc) + timedelta(days=7)
    with session_scope() as s:
        s.add(Invite(church_id=cid, code="used-reusable", role="member", created_by=owner, expires_at=later,
                     reusable=True, accepted_at=datetime.now(timezone.utc)))
        s.add(Invite(church_id=cid, code="pending-single", role="member", created_by=owner, expires_at=later))
    with session_scope() as s:
        assert soft_delete_church(str(cid), session=s) is True
    assert soft_delete_church(cid) is False
    with session_scope() as s:
        assert s.execute(select(Invite.code, Invite.revoked).order_by(Invite.code)).all() == [
            ("pending-single", True), ("used-reusable", True)]
````

**In `backend/tests/test_invites_repo.py`, replace:**

````python
from sqlalchemy import select

from db import session_scope
from db.models import Invite
from repos.churches import create_church
from repos.invites import (
    create_invite, get_invite_by_code, list_invites, revoke_invite,
````

**with:**

````python
from sqlalchemy import delete, select, update

from db import session_scope
from db.models import Invite, User
from domain_errors import NotFound
from repos.churches import create_church
from repos.invites import (
    create_invite, get_invite_by_code, list_invites, revoke_invite,
    find_pending_email_invite, insert_invite, list_active_invites, revoke_expired_email_invites,
    revoke_invites_created_by, revoke_reusable_invites,
````

**Append to `backend/tests/test_invites_repo.py`:**

````python


# --- Slice 6b-1: the People routes' reads and revocations ---

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def _set(code, **values):
    with session_scope() as s:
        s.execute(update(Invite).where(Invite.code == code).values(**values))


def _revoked(code) -> bool:
    return get_invite_by_code(code)["revoked"]


def test_insert_invite_returns_the_whole_row(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    with session_scope() as s:
        row = insert_invite(church_id=cid, created_by=owner, role="admin", email="  Mary@X.com ",
                            reusable=False, now=NOW, session=s)
    assert len(row["code"]) >= 22
    assert {k: row[k] for k in ("church_id", "email", "role", "created_by", "reusable", "revoked", "accepted_at")} == {
        "church_id": cid, "email": "mary@x.com", "role": "admin", "created_by": owner, "reusable": False,
        "revoked": False, "accepted_at": None}
    assert (row["created_at"], row["expires_at"]) == (NOW, NOW + timedelta(days=7))
    assert get_invite_by_code(row["code"])["id"] == row["id"]


def test_list_active_invites_shows_live_ones_newest_first_with_their_creator(tmp_db, make_user):
    owner = make_user(email="o@x.com", name="Olive")
    gone = make_user(email="gone@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    codes = {}
    for hours, key, creator, kwargs in ((1, "old", owner, {}), (2, "reusable_used", owner, {"reusable": True}),
                                        (3, "single_used", owner, {}), (4, "revoked", owner, {}),
                                        (5, "expired", owner, {}), (6, "by_gone", gone, {"email": "p@x.com"})):
        codes[key] = create_invite(church_id=cid, created_by=creator, **kwargs)
        _set(codes[key], created_at=NOW + timedelta(hours=hours), expires_at=NOW + timedelta(days=7))
    for key in ("reusable_used", "single_used"):
        _set(codes[key], accepted_at=NOW)
    _set(codes["revoked"], revoked=True)
    _set(codes["expired"], expires_at=NOW)
    with session_scope() as s:
        s.execute(delete(User).where(User.id == gone))
    rows = list_active_invites(cid, now=NOW)
    assert [r["code"] for r in rows] == [codes["by_gone"], codes["reusable_used"], codes["old"]]
    assert rows[0]["created_by"] is None and rows[0]["email"] == "p@x.com"
    assert rows[2]["created_by"] == {"user_id": owner, "name": "Olive", "email": "o@x.com"}
    assert (rows[2]["created_at"], rows[2]["expires_at"]) == (NOW + timedelta(hours=1), NOW + timedelta(days=7))
    assert set(rows[2]) == {"id", "code", "email", "role", "reusable", "created_at", "expires_at", "created_by"}


def test_pending_email_lookups_ignore_case_and_revoke_only_the_expired(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    live = create_invite(church_id=cid, created_by=owner, email="mary@x.com")
    with session_scope() as s:
        assert find_pending_email_invite(cid, "MARY@x.com", now=NOW, session=s)["code"] == live
        assert revoke_expired_email_invites(cid, "Mary@X.com", now=NOW, session=s) == 0
    _set(live, expires_at=NOW)
    with session_scope() as s:
        assert find_pending_email_invite(cid, "mary@x.com", now=NOW, session=s) is None
        assert revoke_expired_email_invites(cid, "mary@x.com", now=NOW, session=s) == 1
    assert _revoked(live) is True


def test_revoke_created_by_and_revoke_reusable_count_their_rows_in_one_church(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    admin = make_user(email="a@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other = create_church(name="D", timezone="UTC", owner_user_id=admin)
    by_admin = [create_invite(church_id=cid, created_by=admin, **kw)
                for kw in ({}, {"reusable": True}, {"email": "e@x.com", "role": "admin"})]
    elsewhere = create_invite(church_id=other, created_by=admin, reusable=True)
    owners_reusable = create_invite(church_id=cid, created_by=owner, reusable=True)
    owners_single = create_invite(church_id=cid, created_by=owner)
    with session_scope() as s:
        assert revoke_invites_created_by(cid, admin, session=s) == 3
        assert revoke_invites_created_by(cid, admin, session=s) == 0
        assert revoke_reusable_invites(cid, session=s) == 1
    assert [_revoked(c) for c in by_admin] == [True, True, True]
    assert (_revoked(owners_reusable), _revoked(owners_single), _revoked(elsewhere)) == (True, False, False)


def test_revoke_invite_says_whether_the_church_has_it(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other = create_church(name="D", timezone="UTC", owner_user_id=owner)
    code = create_invite(church_id=cid, created_by=owner)
    invite_id = str(get_invite_by_code(code)["id"])
    assert revoke_invite(invite_id, other) is False and _revoked(code) is False
    assert revoke_invite(invite_id, str(cid)) is True and _revoked(code) is True
    assert revoke_invite(invite_id, cid) is True                    # already revoked: still the church's
    with pytest.raises(NotFound):
        revoke_invite("not-a-uuid", cid)
````

**In `backend/tests/test_memberships_repo.py`, replace:**

````python
from sqlalchemy import select
````

**with:**

````python
from sqlalchemy import event, select
````

**In `backend/tests/test_memberships_repo.py`, replace:**

````python
    remove_membership, list_members, count_admins, ensure_membership,
````

**with:**

````python
    remove_membership, list_members, count_admins, ensure_membership,
    count_owner_admins, get_member, is_member_email, list_member_rows, transfer_ownership,
````

**Append to `backend/tests/test_memberships_repo.py`:**

````python


# --- Slice 6b-1: the People routes' reads, the session variants and the transfer ---


def test_list_member_rows_orders_the_owner_then_admins_then_members_by_name(tmp_db, make_user):
    owner = make_user(email="zed@x.com", name="Zed")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    people = {key: make_user(email=email, name=name) for key, email, name in (
        ("bea", "bea@x.com", "bea"), ("amy", "amy@x.com", ""), ("cal", "cal@x.com", "Cal"),
        ("al", "al@x.com", None), ("dot", "dot@x.com", "Dot"))}
    for key, role in (("bea", "admin"), ("amy", "admin"), ("cal", "member"), ("al", "member"), ("dot", "member")):
        add_membership(people[key], cid, role)
    rows = list_member_rows(cid)
    assert [(r["email"], r["role"]) for r in rows] == [
        ("zed@x.com", "owner"), ("amy@x.com", "admin"), ("bea@x.com", "admin"),
        ("al@x.com", "member"), ("cal@x.com", "member"), ("dot@x.com", "member")]
    assert rows[1] == {"user_id": people["amy"], "email": "amy@x.com", "name": "", "role": "admin"}


def test_member_lookups_are_scoped_to_the_church(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    other_owner = make_user(email="other@x.com")
    admin = make_user(email="Admin@X.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    other = create_church(name="D", timezone="UTC", owner_user_id=other_owner)
    add_membership(admin, cid, "admin")
    with session_scope() as s:
        assert get_member(cid, str(admin), session=s) == {
            "user_id": admin, "email": "admin@x.com", "name": "Person", "role": "admin"}
        assert get_member(cid, other_owner, session=s) is None
        assert (count_owner_admins(cid, session=s), count_owner_admins(other, session=s)) == (2, 1)
        assert is_member_email(cid, " ADMIN@x.com ", session=s) is True
        assert is_member_email(other, "admin@x.com", session=s) is False


def test_set_role_and_remove_membership_write_in_the_callers_session(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    member = make_user(email="m@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(member, cid, "member")
    with pytest.raises(RuntimeError), session_scope() as s:
        set_role(str(member), str(cid), "admin", session=s)
        assert get_role(member, cid, session=s) == "admin"
        raise RuntimeError("roll back")
    assert get_role(member, cid) == "member"
    with session_scope() as s:
        remove_membership(member, cid, session=s)
    assert get_role(member, cid) is None


def test_transfer_ownership_demotes_then_promotes(tmp_db, make_user):
    owner = make_user(email="owner@x.com")
    heir = make_user(email="heir@x.com")
    cid = create_church(name="C", timezone="UTC", owner_user_id=owner)
    add_membership(heir, cid, "member")
    roles = []

    @event.listens_for(tmp_db, "before_cursor_execute")
    def _record(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE memberships"):
            roles.append(parameters[0])

    with session_scope() as s:
        transfer_ownership(cid, owner, heir, session=s)
    event.remove(tmp_db, "before_cursor_execute", _record)
    assert roles == ["admin", "owner"]
    assert (get_role(owner, cid), get_role(heir, cid)) == ("admin", "owner")
````

**In `backend/tests/test_usecase_onboarding.py`, replace:**

````python
    soft_delete_church(cid)   # revokes only pending invites; this one was consumed
````

**with:**

````python
    with session_scope() as s:   # soft-deleted directly: since slice 6b, soft_delete_church revokes used invites too
        s.execute(update(Church).where(Church.id == cid).values(deleted_at=INVITE_NOW))
````

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_memberships_repo.py backend/tests/test_invites_repo.py backend/tests/test_churches_repo.py backend/tests/test_usecase_onboarding.py 2>&1 | tail -1`
**Expected:** `test_memberships_repo.py` and `test_invites_repo.py` cannot import the new repo functions, so collection stops with two errors:
```
2 errors in <t>s
```

- [ ] **Step 3: The repos**

**In `backend/repos/churches.py`, replace:**

````python
def soft_delete_church(church_id) -> None:
    """Soft-delete the church (excluded from every query afterward) and revoke
    all still-pending invites for it."""
    with session_scope() as session:
        church = session.get(Church, church_id)
        if church is None or church.deleted_at is not None:
            return
        church.deleted_at = _dt.datetime.now(_dt.timezone.utc)
        session.execute(
            update(Invite)
            .where(
                Invite.church_id == church_id,
                Invite.revoked.is_(False),
                Invite.accepted_at.is_(None),
            )
            .values(revoked=True)
        )
````

**with:**

````python
def soft_delete_church(church_id, *, session: Optional[Session] = None) -> bool:
    """Soft-delete the church (excluded from every query afterward) and revoke
    every unrevoked invite of it, a used reusable link included (slice 6b;
    inv §1 B3). True when this call deleted it; False when it was missing or
    already deleted. Runs in the caller's `session` (DELETE /church, under
    the church-row lock) or in its own scope."""
    cid = as_uuid(church_id)
    if session is not None:
        return _soft_delete_church(session, cid)
    with session_scope() as own:
        return _soft_delete_church(own, cid)


def _soft_delete_church(session, church_id) -> bool:
    church = session.get(Church, church_id)
    if church is None or church.deleted_at is not None:
        return False
    church.deleted_at = _dt.datetime.now(_dt.timezone.utc)
    session.execute(
        update(Invite)
        .where(Invite.church_id == church_id, Invite.revoked.is_(False))
        .values(revoked=True)
        .execution_options(synchronize_session=False)
    )
    return True
````

**In `backend/repos/invites.py`, replace:**

````python
from sqlalchemy import select, update
````

**with:**

````python
from sqlalchemy import func, or_, select, update
````

**In `backend/repos/invites.py`, replace:**

````python
from db.models import Invite
````

**with:**

````python
from db.models import Invite, User
````

**In `backend/repos/invites.py`, replace:**

````python
    """Create an invite and return its code. Code is >=128 bits of url-safe
    entropy (secrets.token_urlsafe(32) == 256 bits).
````

**with:**

````python
    """Create an invite and return its code (insert_invite(...)["code"]).
````

**In `backend/repos/invites.py`, replace:**

````python
    code = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    invite = Invite(
        church_id=church_id,
        code=code,
        email=_normalize_email(email),
        role=role,
        created_by=created_by,
````

**with:**

````python
    fields = dict(church_id=church_id, created_by=created_by, role=role, email=email,
                  reusable=reusable, ttl_days=ttl_days)
    if session is not None:
        return insert_invite(**fields, session=session)["code"]
    with session_scope() as own:
        return insert_invite(**fields, session=own)["code"]


def insert_invite(*, church_id, created_by, role, email, reusable: bool, ttl_days=7,
                  now: Optional[datetime] = None, session: Session) -> dict:
    """Insert an invite in `session` (flushed, not committed) and return its
    row as a dict, created_at included. The code is >=128 bits of url-safe
    entropy (secrets.token_urlsafe(32) == 256 bits); the email is stored
    trimmed and lower-cased (None when blank); it expires `ttl_days` after
    `now`."""
    now = now if now is not None else datetime.now(timezone.utc)
    invite = Invite(
        church_id=as_uuid(church_id),
        code=secrets.token_urlsafe(32),
        email=_normalize_email(email),
        role=role,
        created_by=as_uuid(created_by) if created_by is not None else None,
        created_at=now,
````

**In `backend/repos/invites.py`, replace:**

````python
    if session is not None:
        session.add(invite)
        session.flush()
        return code
    with session_scope() as own:
        own.add(invite)
    return code
````

**with:**

````python
    session.add(invite)
    session.flush()
    return {**_to_dict(invite), "created_at": invite.created_at}
````

**In `backend/repos/invites.py`, replace:**

````python
def revoke_invite(invite_id, church_id) -> None:
    """Revoke an invite, scoped to church_id so a caller can never revoke
    another church's invite by id (IDOR-safe)."""
    with session_scope() as session:
        inv = session.get(Invite, invite_id)
        if inv is None or inv.church_id != church_id:
            return
        inv.revoked = True
````

**with:**

````python
def revoke_invite(invite_id, church_id, *, session: Optional[Session] = None) -> bool:
    """Revoke an invite, scoped to church_id so a caller can never revoke
    another church's invite by id (IDOR-safe). True when the church has the
    invite (revoked now or already); False for an unknown id or another
    church's. Ids go through as_uuid (a malformed id is NotFound). Runs in the
    caller's `session` or in its own scope."""
    iid, cid = as_uuid(invite_id), as_uuid(church_id)
    if session is not None:
        return _revoke_invite(session, iid, cid)
    with session_scope() as own:
        return _revoke_invite(own, iid, cid)


def _revoke_invite(session, invite_id, church_id) -> bool:
    inv = session.get(Invite, invite_id)
    if inv is None or inv.church_id != church_id:
        return False
    inv.revoked = True
    return True


# --- Slice 6b-1: the People routes' reads and revocations (6b spec, "Repo changes") ---

def _pending_email(church_id, email: str):
    """Pending invites of the church for `email` (lower-cased): email-bound,
    not revoked, not accepted (uq_invites_pending_email's rows)."""
    return (
        Invite.church_id == church_id,
        func.lower(Invite.email) == email.strip().lower(),
        Invite.revoked.is_(False),
        Invite.accepted_at.is_(None),
    )


def list_active_invites(church_id, *, now: datetime, session: Optional[Session] = None) -> list[dict]:
    """The church's live invites, newest first (created_at DESC, then id):
    not revoked, not expired at `now`, and not used unless reusable. Each is
    {id, code, email, role, reusable, created_at, expires_at, created_by},
    created_by being {user_id, name, email} of its creator, or None when the
    creator's account is gone."""
    cid = as_uuid(church_id)
    query = (
        select(Invite, User.id.label("creator_id"), User.name.label("creator_name"),
               User.email.label("creator_email"))
        .outerjoin(User, User.id == Invite.created_by)
        .where(
            Invite.church_id == cid,
            Invite.revoked.is_(False),
            Invite.expires_at > as_utc(now),
            or_(Invite.accepted_at.is_(None), Invite.reusable.is_(True)),
        )
        .order_by(Invite.created_at.desc(), Invite.id)
    )
    if session is not None:
        return _active_rows(session, query)
    with session_scope() as own:
        return _active_rows(own, query)


def _active_rows(session, query) -> list[dict]:
    return [
        {
            "id": row.Invite.id,
            "code": row.Invite.code,
            "email": row.Invite.email,
            "role": row.Invite.role,
            "reusable": row.Invite.reusable,
            "created_at": as_utc(row.Invite.created_at),
            "expires_at": as_utc(row.Invite.expires_at),
            "created_by": ({"user_id": row.creator_id, "name": row.creator_name, "email": row.creator_email}
                           if row.creator_id is not None else None),
        }
        for row in session.execute(query)
    ]


def find_pending_email_invite(church_id, email: str, *, now: datetime, session: Session) -> Optional[dict]:
    """The church's unexpired pending invite for `email`, or None."""
    inv = session.execute(
        select(Invite).where(*_pending_email(as_uuid(church_id), email), Invite.expires_at > as_utc(now))
    ).scalars().first()
    return _to_dict(inv) if inv is not None else None


def revoke_expired_email_invites(church_id, email: str, *, now: datetime, session: Session) -> int:
    """Revoke the church's pending invites for `email` that expired at or
    before `now` (expiry cannot sit in the unique index's predicate); returns
    how many."""
    return session.execute(
        update(Invite)
        .where(*_pending_email(as_uuid(church_id), email), Invite.expires_at <= as_utc(now))
        .values(revoked=True)
        .execution_options(synchronize_session=False)
    ).rowcount


def revoke_invites_created_by(church_id, user_id, *, session: Session) -> int:
    """Revoke every unrevoked invite of the church that `user_id` created
    (single-use or reusable, email-bound or not, any role); returns how many."""
    return session.execute(
        update(Invite)
        .where(Invite.church_id == as_uuid(church_id), Invite.created_by == as_uuid(user_id),
               Invite.revoked.is_(False))
        .values(revoked=True)
        .execution_options(synchronize_session=False)
    ).rowcount


def revoke_reusable_invites(church_id, *, session: Session) -> int:
    """Revoke every unrevoked reusable invite of the church; returns how many."""
    return session.execute(
        update(Invite)
        .where(Invite.church_id == as_uuid(church_id), Invite.reusable.is_(True), Invite.revoked.is_(False))
        .values(revoked=True)
        .execution_options(synchronize_session=False)
    ).rowcount
````

**In `backend/repos/memberships.py`, replace:**

````python
from sqlalchemy import select, func, update
````

**with:**

````python
from sqlalchemy import case, select, func, update
````

**In `backend/repos/memberships.py`, replace:**

````python
def set_role(user_id, church_id, role) -> None:
    """Change a member's role. Demoting the last owner/admin to member is
    rejected under a row lock."""
    with session_scope() as session:
        m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
        if m is None:
            return
        if m.role in _ADMIN_ROLES and role not in _ADMIN_ROLES:
            admins = _lock_admin_user_ids(session, church_id)
            if len(admins) <= 1:
                raise LastAdminError(
                    "Cannot demote the last owner/admin of this church."
                )
        m.role = role


def remove_membership(user_id, church_id) -> None:
    """Remove a member. Removing the last owner/admin is rejected under a row
    lock. The member's authored services are preserved but their
    services.created_by is nulled (history survives the author leaving)."""
    with session_scope() as session:
        m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
        if m is None:
            return
        if m.role in _ADMIN_ROLES:
            admins = _lock_admin_user_ids(session, church_id)
            if len(admins) <= 1:
                raise LastAdminError(
                    "Cannot remove the last owner/admin of this church."
                )
        session.execute(
            update(Service)
            .where(Service.church_id == church_id, Service.created_by == user_id)
            .values(created_by=None)
        )
        session.delete(m)
````

**with:**

````python
def set_role(user_id, church_id, role, *, session: Optional[Session] = None) -> None:
    """Change a member's role. Demoting the last owner/admin to member is
    rejected under a row lock. Runs in the caller's `session` (slice 6b's
    usecases, under the church-row lock) or in its own scope; ids go through
    as_uuid."""
    uid, cid = as_uuid(user_id), as_uuid(church_id)
    if session is not None:
        _set_role(session, uid, cid, role)
        return
    with session_scope() as own:
        _set_role(own, uid, cid, role)


def _set_role(session, user_id, church_id, role) -> None:
    m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
    if m is None:
        return
    if m.role in _ADMIN_ROLES and role not in _ADMIN_ROLES:
        admins = _lock_admin_user_ids(session, church_id)
        if len(admins) <= 1:
            raise LastAdminError(
                "Cannot demote the last owner/admin of this church."
            )
    m.role = role


def remove_membership(user_id, church_id, *, session: Optional[Session] = None) -> None:
    """Remove a member. Removing the last owner/admin is rejected under a row
    lock. The member's authored services are preserved but their
    services.created_by is nulled (history survives the author leaving).
    Runs in the caller's `session` or in its own scope; ids go through
    as_uuid."""
    uid, cid = as_uuid(user_id), as_uuid(church_id)
    if session is not None:
        _remove_membership(session, uid, cid)
        return
    with session_scope() as own:
        _remove_membership(own, uid, cid)


def _remove_membership(session, user_id, church_id) -> None:
    m = session.get(Membership, {"church_id": church_id, "user_id": user_id})
    if m is None:
        return
    if m.role in _ADMIN_ROLES:
        admins = _lock_admin_user_ids(session, church_id)
        if len(admins) <= 1:
            raise LastAdminError(
                "Cannot remove the last owner/admin of this church."
            )
    session.execute(
        update(Service)
        .where(Service.church_id == church_id, Service.created_by == user_id)
        .values(created_by=None)
    )
    session.delete(m)


def transfer_ownership(church_id, owner_id, new_owner_id, *, session: Session) -> None:
    """Make `new_owner_id` the owner and `owner_id` an admin, as two Core
    UPDATEs in this order: demote, then promote. (The ORM's unit of work
    orders same-table UPDATEs by primary key, not by assignment, and a promote
    first would hold two owners for one statement, which slice 6b-2's
    one-owner index refuses.) The caller holds the church-row lock and has
    checked both memberships."""
    cid = as_uuid(church_id)
    for user_id, role in ((as_uuid(owner_id), "admin"), (as_uuid(new_owner_id), "owner")):
        session.execute(
            update(Membership)
            .where(Membership.church_id == cid, Membership.user_id == user_id)
            .values(role=role)
            .execution_options(synchronize_session=False)
        )


def _member_query(church_id):
    return (
        select(User.id, User.email, User.name, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.church_id == church_id)
    )


def _member_dict(row) -> dict:
    return {"user_id": row.id, "email": row.email, "name": row.name, "role": row.role}


def list_member_rows(church_id, *, session: Optional[Session] = None) -> list[dict]:
    """The church's members {user_id, email, name, role} in the order
    GET /members shows them (slice 6b): the owner, then admins, then members,
    each by lower(name, or the email when the name is blank), then user_id."""
    cid = as_uuid(church_id)
    order = (
        case((Membership.role == "owner", 0), (Membership.role == "admin", 1), else_=2),
        func.lower(func.coalesce(func.nullif(User.name, ""), User.email)),
        User.id,
    )
    if session is not None:
        return [_member_dict(r) for r in session.execute(_member_query(cid).order_by(*order))]
    with session_scope() as own:
        return [_member_dict(r) for r in own.execute(_member_query(cid).order_by(*order))]


def get_member(church_id, user_id, *, session: Session) -> Optional[dict]:
    """One membership of this church {user_id, email, name, role}, or None
    (a user who belongs only to another church is None too)."""
    row = session.execute(_member_query(as_uuid(church_id)).where(Membership.user_id == as_uuid(user_id))).first()
    return _member_dict(row) if row is not None else None


def count_owner_admins(church_id, *, session: Session) -> int:
    """How many owner and admin memberships the church has, read under the
    same admin-row lock set_role and remove_membership take."""
    return len(_lock_admin_user_ids(session, as_uuid(church_id)))


def is_member_email(church_id, email: str, *, session: Session) -> bool:
    """True when a member of this church has `email` (compared lower-cased)."""
    return session.execute(
        select(func.count()).select_from(Membership)
        .join(User, User.id == Membership.user_id)
        .where(Membership.church_id == as_uuid(church_id), func.lower(User.email) == email.strip().lower())
    ).scalar_one() > 0
````

- [ ] **Step 4: Run the files, the frozen pages' tests and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_memberships_repo.py backend/tests/test_invites_repo.py backend/tests/test_churches_repo.py backend/tests/test_usecase_onboarding.py streamlit_tests 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
122 passed in <t>s
```
```
2058 passed, 38 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/repos/memberships.py backend/repos/invites.py backend/repos/churches.py backend/tests/test_memberships_repo.py backend/tests/test_invites_repo.py backend/tests/test_churches_repo.py backend/tests/test_usecase_onboarding.py
git commit -q -m "Slice 6b-1: the repos for members, invites and the church's delete" -m "memberships: set_role and remove_membership run in a caller's session
(ids through as_uuid; LastAdminError unchanged); list_member_rows (the
owner, admins, members, each by name, else email, then id), get_member,
count_owner_admins (under the admin-row lock), is_member_email, and
transfer_ownership as two Core UPDATEs, demote then promote. invites:
insert_invite returns the whole row (create_invite wraps it);
list_active_invites filters in SQL and names the creator;
find_pending_email_invite and revoke_expired_email_invites ignore case;
revoke_invites_created_by and revoke_reusable_invites count their rows;
revoke_invite says whether the church has the invite. churches:
soft_delete_church runs in a caller's session, revokes every unrevoked
invite (a used reusable link too) and says whether it deleted. The frozen
Streamlit callers keep their positional calls." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2058 passed, 38 skipped`; frontend `952 passed` in 109 files.

### Task 5: The member and invite usecases (S "Backend changes" `usecases/members.py`, "Invite semantics", "Transactions and locking"; clarifications 3, 12, 13, 18)

**Files:**
- Create: `backend/tests/test_members_usecase.py`
- Modify: `backend/usecases/members.py`

The list (order, `is_me`, a blank name as `None`); role changes (both ways; the policy's four refusals change nothing; a stranger, another church's member or a malformed id is not found; the same role writes nothing; in a church with no owner one admin demotes another; the repo's `LastAdminError` is a 409, not a 500; an admin demoted after the guard gets the role 403 without a reason); for each of the four writes, a church deleted or a caller removed after the guard is `no_church_access` with nothing written; each write reads the church row locked, in its own session; removal (services kept, every invite the removed person made in this church revoked and counted, `revoke_reusable` counting each row once, the policy's refusals, another church's member not found, two admins of an ownerless church); invites (`clean_invite_email` with every row of `email_addresses.json`; the defaults; the three 422s; the two 409s with their words; re-inviting after a revoke, an acceptance or expiry, the expired row then revoked; a unique-index race; the log line; the list's filters and creators; idempotent, church-scoped revoking; members refused).

- [ ] **Step 1: Write the failing tests**

**Create `backend/tests/test_members_usecase.py`:**

````python
"""usecases.members: the member and invite functions of slice 6b-1 (6b spec,
"Backend changes", "Role policy", "Invite semantics", "Transactions and
locking"; Testing → test_members_usecase.py). Every write takes the
church-row lock and re-reads the caller's role under it; the policy's own
truth table is test_role_policy.py's."""
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import delete, select, update

from db import session_scope
from db.models import Church, Invite, Service, User
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound
from repos import invites, memberships
from repos.memberships import LastAdminError, add_membership, get_role, remove_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import members

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
NO_ACCESS = ("You don't have access to this church.", {"reason": "no_church_access"})
ADDRESSES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "email_addresses.json")
                       .read_text(encoding="utf-8"))


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com", name="Olive Owner")
    admin = make_user(email="admin@example.com", name="Adam Admin")
    member = make_user(email="member@example.com", name="Mia Member")
    cid = make_church(name="Grace", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    other_owner = make_user(email="elsewhere@example.com")
    other = make_church(name="Hope", owner_user_id=other_owner)
    return {"church": cid, "owner": owner, "admin": admin, "member": member, "other": other,
            "other_owner": other_owner}


def _invite(world, who="owner", **kwargs) -> dict:
    return members.create_invite(world["church"], world[who], now=NOW, **kwargs)


def _invite_row(invite_id) -> Invite:
    with session_scope() as s:
        row = s.get(Invite, invite_id)
        s.expunge(row)
        return row


def _codes(world) -> list[str]:
    return [i["code"] for i in members.list_invites(world["church"], now=NOW)]


# --- list_members ---


def test_members_are_listed_owner_admins_members_by_name_with_is_me(world, make_user):
    blank = make_user(email="aaron@example.com", name="  ")
    add_membership(blank, world["church"], "member")
    rows = members.list_members(world["church"], world["member"])
    assert [(r["email"], r["role"], r["name"], r["is_me"]) for r in rows] == [
        ("owner@example.com", "owner", "Olive Owner", False),
        ("admin@example.com", "admin", "Adam Admin", False),
        ("aaron@example.com", "member", None, False),
        ("member@example.com", "member", "Mia Member", True),
    ]
    assert set(rows[0]) == {"user_id", "email", "name", "role", "is_me"}


# --- change_role ---


def test_an_admin_makes_a_member_an_admin_and_back(world):
    up = members.change_role(world["church"], world["admin"], world["member"], "admin")
    assert up == {"user_id": world["member"], "email": "member@example.com", "name": "Mia Member", "role": "admin",
                  "is_me": False}
    assert members.change_role(world["church"], world["owner"], str(world["member"]), "member")["role"] == "member"
    assert get_role(world["member"], world["church"]) == "member"


@pytest.mark.parametrize("who, target, message", [
    ("member", "admin", "Only church admins can do this."),
    ("admin", "admin", "You can't change your own role."),
    ("owner", "owner", "You can't change your own role."),
    ("admin", "owner", "The owner's role can't be changed."),
])
def test_a_role_change_the_policy_refuses_changes_nothing(world, who, target, message):
    with pytest.raises(Forbidden) as refused:
        members.change_role(world["church"], world[who], world[target], "member")
    assert (refused.value.message, refused.value.details) == (message, None)
    assert [get_role(world[w], world["church"]) for w in ("owner", "admin", "member")] == ["owner", "admin", "member"]


def test_a_role_change_for_a_non_member_is_not_found(world, make_user):
    for target in (world["other_owner"], make_user(email="nobody@example.com"), uuid.uuid4(), "not-a-uuid"):
        with pytest.raises(NotFound) as missing:
            members.change_role(world["church"], world["owner"], target, "admin")
        assert missing.value.message in ("Member not found.", "Not found.")
    assert get_role(world["other_owner"], world["other"]) == "owner"


def test_the_same_role_writes_nothing(world, monkeypatch):
    monkeypatch.setattr(memberships, "set_role", lambda *a, **k: pytest.fail("set_role called"))
    assert members.change_role(world["church"], world["owner"], world["admin"], "admin")["role"] == "admin"


def test_in_an_ownerless_church_one_admin_demotes_another(world, make_user):
    second = make_user(email="second@example.com")
    add_membership(second, world["church"], "admin")
    set_role(world["owner"], world["church"], "admin")             # made ownerless outside the app
    assert members.change_role(world["church"], world["admin"], second, "member")["role"] == "member"


def test_a_last_admin_error_from_the_repo_is_a_409_not_a_500(world, monkeypatch):
    def refuse(*_args, **_kwargs):
        raise LastAdminError("Cannot demote the last owner/admin of this church.")

    monkeypatch.setattr(memberships, "set_role", refuse)
    with pytest.raises(Conflict) as refused:
        members.change_role(world["church"], world["owner"], world["admin"], "member")
    assert (refused.value.code, refused.value.message) == (
        "last_admin", "Cannot demote the last owner/admin of this church.")


def test_a_demoted_admin_gets_the_role_403_without_a_reason(world):
    set_role(world["admin"], world["church"], "member")          # after require_admin read "admin"
    with pytest.raises(Forbidden) as refused:
        members.change_role(world["church"], world["admin"], world["member"], "admin")
    assert (refused.value.message, refused.value.details) == ("Only church admins can do this.", None)
    assert get_role(world["member"], world["church"]) == "member"


WRITES = {
    "change_role": lambda w: members.change_role(w["church"], w["admin"], w["member"], "admin"),
    "remove_member": lambda w: members.remove_member(w["church"], w["admin"], w["member"]),
    "create_invite": lambda w: members.create_invite(w["church"], w["admin"], email="new@example.com", now=NOW),
    "revoke_invite": lambda w: members.revoke_invite(w["church"], w["admin"], w["invite"]),
}


@pytest.mark.parametrize("gone", ["church deleted", "actor removed"])
@pytest.mark.parametrize("write", sorted(WRITES))
def test_a_write_after_the_church_or_the_callers_membership_went_is_no_church_access(world, write, gone):
    world["invite"] = _invite(world)["id"]
    if gone == "church deleted":
        with session_scope() as s:                 # as a DELETE /church racing this write would leave it
            s.execute(update(Church).where(Church.id == world["church"])
                      .values(deleted_at=NOW))
    else:
        remove_membership(world["admin"], world["church"])
    with pytest.raises(Forbidden) as refused:
        WRITES[write](world)
    assert (refused.value.message, refused.value.details) == NO_ACCESS
    assert get_role(world["member"], world["church"]) == "member"
    with session_scope() as s:
        assert s.execute(select(Invite.email, Invite.revoked)).all() == [(None, False)]


def test_every_write_reads_the_church_row_locked_in_its_own_session(world):
    invite_id = _invite(world)["id"]
    calls = [lambda: members.change_role(world["church"], world["owner"], world["member"], "admin"),
             lambda: members.remove_member(world["church"], world["owner"], world["member"]),
             lambda: members.create_invite(world["church"], world["owner"], now=NOW),
             lambda: members.revoke_invite(world["church"], world["owner"], invite_id)]
    for call in calls:
        with _record_church_row_access() as (reads, _writes):
            call()
        assert reads and reads[0][1] is True and len({id(session) for session, _ in reads}) == 1


# --- remove_member ---


def test_removing_a_member_keeps_their_services_and_revokes_every_invite_they_made(world):
    with session_scope() as s:
        s.add(Service(church_id=world["church"], service_date_iso="2026-10-04", occasion="", hymns=[], liturgy={},
                      scriptures=[], created_by=world["admin"]))
    made = [members.create_invite(world["church"], world["admin"], now=NOW, **kw)["id"]
            for kw in ({}, {"reusable": True}, {"email": "e@example.com", "role": "admin"})]
    owners = _invite(world, reusable=True)["id"]
    add_membership(world["admin"], world["other"], "admin")
    elsewhere = members.create_invite(world["other"], world["admin"], now=NOW)["id"]
    assert members.remove_member(world["church"], world["owner"], world["admin"]) == 3
    assert get_role(world["admin"], world["church"]) is None
    assert [_invite_row(i).revoked for i in made] == [True, True, True]
    assert (_invite_row(owners).revoked, _invite_row(elsewhere).revoked) == (False, False)
    with session_scope() as s:
        assert s.execute(select(Service.created_by)).scalars().all() == [None]


def test_revoke_reusable_also_revokes_every_live_reusable_link_counting_each_once(world):
    theirs = members.create_invite(world["church"], world["admin"], now=NOW, reusable=True)["id"]
    owners_reusable = _invite(world, reusable=True)["id"]
    owners_single = _invite(world)["id"]
    assert members.remove_member(world["church"], world["owner"], world["admin"], revoke_reusable=True) == 2
    assert [_invite_row(i).revoked for i in (theirs, owners_reusable, owners_single)] == [True, True, False]


@pytest.mark.parametrize("who, target, message", [
    ("member", "admin", "Only church admins can do this."),
    ("admin", "admin", "To leave this church, use Leave church in Danger zone."),
    ("owner", "owner", "To leave this church, use Leave church in Danger zone."),
    ("admin", "owner", "The owner can't be removed."),
])
def test_a_removal_the_policy_refuses_changes_nothing(world, who, target, message):
    with pytest.raises(Forbidden) as refused:
        members.remove_member(world["church"], world[who], world[target])
    assert refused.value.message == message
    assert get_role(world[target], world["church"]) == target


def test_removing_another_churchs_member_is_not_found(world):
    with pytest.raises(NotFound) as missing:
        members.remove_member(world["church"], world["owner"], world["other_owner"])
    assert missing.value.message == "Member not found."
    assert get_role(world["other_owner"], world["other"]) == "owner"


def test_in_an_ownerless_church_with_two_admins_one_removes_the_other(world, make_user):
    second = make_user(email="second@example.com")
    add_membership(second, world["church"], "admin")
    remove_membership(world["owner"], world["church"])             # made ownerless outside the app
    assert members.remove_member(world["church"], second, world["admin"]) == 0
    assert get_role(world["admin"], world["church"]) is None


# --- invites ---


@pytest.mark.parametrize("raw, stored", [("  Right@X.com ", "right@x.com"), ("", None), ("   ", None), (None, None)])
def test_clean_invite_email(raw, stored):
    assert members.clean_invite_email(raw) == stored


@pytest.mark.parametrize("raw", ["no-at"] + [raw for raw in ADDRESSES["invalid"] if raw.strip()])
def test_an_address_the_app_cannot_use_is_refused(raw):
    with pytest.raises(InvalidInput) as refused:
        members.clean_invite_email(raw)
    assert (refused.value.message, refused.value.field) == ("Enter a valid email address.", "email")


@pytest.mark.parametrize("case", ADDRESSES["valid"], ids=lambda case: case["raw"])
def test_a_valid_address_is_stored_lower_cased(case):
    assert members.clean_invite_email(case["raw"]) == case["normalized"].lower()


def test_an_invite_is_single_use_member_by_default_for_seven_days(world):
    out = _invite(world, who="admin")
    assert len(out["code"]) >= 22
    assert {k: out[k] for k in ("email", "role", "reusable", "created_at", "expires_at")} == {
        "email": None, "role": "member", "reusable": False, "created_at": NOW, "expires_at": NOW + timedelta(days=7)}
    assert out["created_by"] == {"user_id": world["admin"], "name": "Adam Admin", "email": "admin@example.com"}
    second = members.create_invite(world["church"], world["owner"], reusable=True, role="admin",
                                   now=NOW + timedelta(minutes=1))
    assert (second["reusable"], second["role"]) == (True, "admin")
    assert _codes(world) == [second["code"], out["code"]]


@pytest.mark.parametrize("kwargs, field, message", [
    ({"email": "x@example.com", "reusable": True}, "reusable", "A link for one email address works once."),
    ({"email": "not an address"}, "email", "Enter a valid email address."),
    ({"role": "owner"}, "role", "Not a valid value."),
])
def test_a_bad_invite_is_refused_and_nothing_is_stored(world, kwargs, field, message):
    with pytest.raises(InvalidInput) as refused:
        _invite(world, **kwargs)
    assert (refused.value.field, refused.value.message) == (field, message)
    assert _codes(world) == []


def test_inviting_a_members_email_in_any_case_is_a_conflict(world):
    with pytest.raises(Conflict) as refused:
        _invite(world, email=" Member@Example.COM ")
    assert (refused.value.code, refused.value.message) == ("conflict",
                                                           "member@example.com is already a member of this church.")


def test_a_second_pending_invite_for_an_email_is_invite_exists(world):
    _invite(world, email="new@example.com")
    with pytest.raises(Conflict) as refused:
        _invite(world, email="NEW@example.com", role="admin")
    assert (refused.value.code, refused.value.message) == (
        "invite_exists", "There's already a pending invite for new@example.com. Copy its link below or revoke it first.")


def test_an_email_can_be_invited_again_after_a_revoke_an_acceptance_or_expiry(world):
    first = _invite(world, email="new@example.com")
    members.revoke_invite(world["church"], world["owner"], first["id"])
    second = _invite(world, email="new@example.com")
    invites.claim(second["id"], world["member"], NOW)                # accepted
    third = _invite(world, email="new@example.com")
    later = NOW + timedelta(days=8)                                  # third has expired by then
    fourth = members.create_invite(world["church"], world["owner"], email="new@example.com", now=later)
    assert _invite_row(third["id"]).revoked is True
    assert _invite_row(fourth["id"]).revoked is False


def test_a_unique_index_race_is_invite_exists_too(world, monkeypatch):
    _invite(world, email="new@example.com")
    monkeypatch.setattr(invites, "find_pending_email_invite", lambda *a, **k: None)   # as if the other was not seen
    with pytest.raises(Conflict) as refused:
        _invite(world, email="new@example.com")
    assert refused.value.code == "invite_exists"
    with session_scope() as s:
        assert s.execute(select(Invite.email)).scalars().all() == ["new@example.com"]


def test_creating_an_invite_logs_ids_never_the_code_or_the_email(world, caplog):
    caplog.set_level(logging.INFO, logger="usecases.members")
    out = _invite(world, email="secret@example.com", role="admin")
    [record] = [r for r in caplog.records if r.name == "usecases.members"]
    assert record.getMessage() == (f"invite_created church_id={world['church']} invite_id={out['id']} role=admin "
                                   "reusable=False email_bound=True")


def test_the_invite_list_hides_used_single_use_revoked_and_expired_and_keeps_used_reusable(world):
    single = _invite(world)
    reusable = _invite(world, reusable=True)
    revoked = _invite(world)
    expiring = members.create_invite(world["church"], world["owner"], now=NOW - timedelta(days=7))
    by_admin = members.create_invite(world["church"], world["admin"], now=NOW + timedelta(minutes=1))
    for invite in (single, reusable):
        invites.claim(invite["id"], world["member"], NOW)
    members.revoke_invite(world["church"], world["owner"], revoked["id"])
    with session_scope() as s:
        s.execute(update(User).where(User.id == world["admin"]).values(name=""))
    listed = members.list_invites(world["church"], now=NOW)
    assert [i["id"] for i in listed] == [by_admin["id"], reusable["id"]]
    assert listed[0]["created_by"] == {"user_id": world["admin"], "name": None, "email": "admin@example.com"}
    remove_membership(world["admin"], world["church"])
    with session_scope() as s:
        s.execute(delete(User).where(User.id == world["admin"]))
    assert members.list_invites(world["church"], now=NOW)[0]["created_by"] is None
    assert expiring["id"] not in [i["id"] for i in listed]


def test_revoking_an_invite_is_idempotent_and_church_scoped(world):
    mine = _invite(world)
    theirs = members.create_invite(world["other"], world["other_owner"], now=NOW)
    members.revoke_invite(world["church"], world["admin"], mine["id"])
    members.revoke_invite(world["church"], world["admin"], str(mine["id"]))       # again: still fine
    assert _invite_row(mine["id"]).revoked is True
    for invite_id in (theirs["id"], uuid.uuid4(), "not-a-uuid"):
        with pytest.raises(NotFound):
            members.revoke_invite(world["church"], world["admin"], invite_id)
    assert _invite_row(theirs["id"]).revoked is False


def test_a_member_may_not_create_or_revoke_invites(world):
    invite_id = _invite(world)["id"]
    for call in (lambda: _invite(world, who="member"),
                 lambda: members.revoke_invite(world["church"], world["member"], invite_id)):
        with pytest.raises(Forbidden) as refused:
            call()
        assert (refused.value.message, refused.value.details) == ("Only church admins can do this.", None)
    assert _invite_row(invite_id).revoked is False
````

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_members_usecase.py 2>&1 | tail -1`
**Expected:** every test fails: `usecases.members` has only `lock_and_read_actor` (no `list_members`, `change_role`, `remove_member`, `clean_invite_email`, `create_invite`, `list_invites` or `revoke_invite`):
```
82 failed in <t>s
```

- [ ] **Step 3: The usecases**

**In `backend/usecases/members.py`, replace:**

````python
"""The church's members (6b spec, `usecases/members.py`). Slice 6a-1 creates
the module with only the helper every church write shares (6a and 6b specs,
"Assumed interfaces"); 6b adds its member and invite functions here.
````

**with:**

````python
"""The church's members and invites (6b spec, `usecases/members.py`). Slice
6a-1 created the module with the helper every church write shares (6a and 6b
specs, "Assumed interfaces"); slice 6b-1 adds the member and invite
functions of GET /members, PATCH and DELETE /members/{user_id}, and GET,
POST and DELETE /invites.
````

**In `backend/usecases/members.py`, replace:**

````python
earlier transaction. No FastAPI, Starlette or Streamlit here
(usecases/__init__.py).
"""
import uuid

from sqlalchemy.orm import Session

from domain_errors import Forbidden
from repos import churches, memberships
````

**with:**

````python
earlier transaction. Every write here opens one session, starts with it,
then checks the role (church_admin.require_admin_role, or usecases.role_policy
after the target is looked up: a missing target is a 404), then writes.
Repos are called through their modules, so tests can patch one function.
Log lines carry ids, roles and counts only: never an email, a name or an
invite code. No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound
from email_addresses import InvalidAddress, normalize_address
from repos import churches, invites, memberships
from repos.memberships import LastAdminError
from usecases import role_policy

logger = logging.getLogger(__name__)
````

**Append to `backend/usecases/members.py`:**

````python


# --- Slice 6b-1: members (GET /members, PATCH and DELETE /members/{user_id}) ---

MEMBER_NOT_FOUND = "Member not found."


def member_out(row: dict, actor_id: uuid.UUID) -> dict:
    """A member as the API returns it: a blank name is None, and is_me."""
    name = row["name"] if row["name"] is not None and row["name"].strip() else None
    return {"user_id": row["user_id"], "email": row["email"], "name": name, "role": row["role"],
            "is_me": row["user_id"] == actor_id}


def list_members(church_id: uuid.UUID, actor_id: uuid.UUID) -> list[dict]:
    """GET /members (every member, with emails; decision 5): the owner, then
    admins, then members, each by name (the email when the name is blank)."""
    actor_id = as_uuid(actor_id)
    return [member_out(row, actor_id) for row in memberships.list_member_rows(church_id)]


def _require_admin(role: str) -> None:
    # church_admin imports this module (lock_and_read_actor), so it is imported here, when called.
    from usecases.church_admin import require_admin_role
    require_admin_role(role)


def _target(s: Session, church_id: uuid.UUID, target_id) -> dict:
    target = memberships.get_member(church_id, target_id, session=s)
    if target is None:
        raise NotFound(MEMBER_NOT_FOUND)
    return target


def change_role(church_id: uuid.UUID, actor_id: uuid.UUID, target_id, new_role: str) -> dict:
    """PATCH /members/{user_id}: under the church-row lock with the caller's
    role re-read, the role 403, then the target (404 when not a member of this
    church), then role_policy.check_role_change (self, the owner); a role the
    target already has writes nothing. Returns the target as GET /members
    shows it. repos.memberships' LastAdminError cannot fire here (the actor and
    an admin target are two owners or admins); if it does, it is a 409
    last_admin with the repo's words, never a 500."""
    actor_id, target_id = as_uuid(actor_id), as_uuid(target_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin(role)
        target = _target(s, church_id, target_id)
        outcome = role_policy.check_role_change(actor_id=actor_id, actor_role=role, target_id=target_id,
                                                target_role=target["role"], new_role=new_role)
        if outcome == "change":
            try:
                memberships.set_role(target_id, church_id, new_role, session=s)
            except LastAdminError as exc:
                raise Conflict(str(exc), code="last_admin") from None
            logger.info("member_role_changed church_id=%s actor_id=%s target_id=%s old_role=%s new_role=%s",
                        church_id, actor_id, target_id, target["role"], new_role)
            target = {**target, "role": new_role}
    return member_out(target, actor_id)


def remove_member(church_id: uuid.UUID, actor_id: uuid.UUID, target_id, *, revoke_reusable: bool = False) -> int:
    """DELETE /members/{user_id}: under the church-row lock with the caller's
    role re-read, the role 403, the target (404), role_policy.check_remove
    (self, the owner), then in the same transaction: the membership goes (its
    services.created_by is nulled), every unrevoked invite of this church the
    removed person created is revoked, and with `revoke_reusable` every
    unrevoked reusable invite of the church too. Returns how many invites were
    revoked (each once)."""
    actor_id, target_id = as_uuid(actor_id), as_uuid(target_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin(role)
        target = _target(s, church_id, target_id)
        role_policy.check_remove(actor_id=actor_id, actor_role=role, target_id=target_id,
                                 target_role=target["role"])
        try:
            memberships.remove_membership(target_id, church_id, session=s)
        except LastAdminError as exc:
            raise Conflict(str(exc), code="last_admin") from None
        revoked = invites.revoke_invites_created_by(church_id, target_id, session=s)
        if revoke_reusable:
            revoked += invites.revoke_reusable_invites(church_id, session=s)
    logger.info("member_removed church_id=%s actor_id=%s target_id=%s revoked_invites=%d",
                church_id, actor_id, target_id, revoked)
    return revoked


# --- Slice 6b-1: invites (GET, POST and DELETE /invites) ---

EMAIL_INVALID = "Enter a valid email address."
REUSABLE_WITH_EMAIL = "A link for one email address works once."
ROLE_INVALID = "Not a valid value."
ALREADY_MEMBER = "{email} is already a member of this church."
INVITE_EXISTS = "There's already a pending invite for {email}. Copy its link below or revoke it first."
INVITE_NOT_FOUND = "Invite not found."
ASSIGNABLE_ROLES = ("member", "admin")
INVITE_TTL_DAYS = 7


def clean_invite_email(value: Optional[str]) -> Optional[str]:
    """An invite's email as stored: None when missing or blank, else
    email_addresses.normalize_address (the app's one address rule) and fully
    lower-cased (accept compares it with the caller's lower-cased email).
    An address the rule refuses is a 422 naming `email`."""
    if value is None or not value.strip():
        return None
    try:
        return normalize_address(value).lower()
    except InvalidAddress:
        raise InvalidInput(EMAIL_INVALID, field="email") from None


def _creator(row: Optional[dict]) -> Optional[dict]:
    if row is None:
        return None
    name = row["name"] if row["name"] is not None and row["name"].strip() else None
    return {"user_id": row["user_id"], "name": name, "email": row["email"]}


def _invite_out(row: dict, creator: Optional[dict]) -> dict:
    return {"id": row["id"], "code": row["code"], "email": row["email"], "role": row["role"],
            "reusable": row["reusable"], "created_at": invites.as_utc(row["created_at"]),
            "expires_at": invites.as_utc(row["expires_at"]), "created_by": _creator(creator)}


def list_invites(church_id: uuid.UUID, *, now: Optional[datetime] = None) -> list[dict]:
    """GET /invites (owners and admins): the live invites, newest first (not
    revoked, not expired, and unused unless reusable), each with its creator
    (None when the creator's account is gone)."""
    now = now if now is not None else datetime.now(timezone.utc)
    return [_invite_out(row, row["created_by"]) for row in invites.list_active_invites(church_id, now=now)]


def create_invite(church_id: uuid.UUID, actor_id: uuid.UUID, *, role: str = "member", email: Optional[str] = None,
                  reusable: bool = False, now: Optional[datetime] = None) -> dict:
    """POST /invites: under the church-row lock with the caller's role
    re-read, the role 403, then the body's checks in order (the role; the
    email, clean_invite_email; reusable with an email is a 422 naming
    `reusable`: an email-bound link works once), then for an email: a member
    of this church with it is a 409 conflict; its pending invites that have
    expired are revoked; a live pending one is a 409 invite_exists; and a
    unique-index race (uq_invites_pending_email) is the same 409. Expires 7
    days from `now`. Returns the invite as GET /invites lists it. Logs the
    ids, the role and whether it is reusable or email-bound; never the code
    or the email."""
    actor_id = as_uuid(actor_id)
    now = now if now is not None else datetime.now(timezone.utc)
    with session_scope() as s:
        actor_role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin(actor_role)
        if role not in ASSIGNABLE_ROLES:
            raise InvalidInput(ROLE_INVALID, field="role")
        email = clean_invite_email(email)
        if email is not None and reusable:
            raise InvalidInput(REUSABLE_WITH_EMAIL, field="reusable")
        if email is not None:
            if memberships.is_member_email(church_id, email, session=s):
                raise Conflict(ALREADY_MEMBER.format(email=email))
            invites.revoke_expired_email_invites(church_id, email, now=now, session=s)
            if invites.find_pending_email_invite(church_id, email, now=now, session=s) is not None:
                raise Conflict(INVITE_EXISTS.format(email=email), code="invite_exists")
        try:
            with s.begin_nested():
                row = invites.insert_invite(church_id=church_id, created_by=actor_id, role=role, email=email,
                                            reusable=reusable, ttl_days=INVITE_TTL_DAYS, now=now, session=s)
        except IntegrityError:
            raise Conflict(INVITE_EXISTS.format(email=email), code="invite_exists") from None
        creator = memberships.get_member(church_id, actor_id, session=s)
    logger.info("invite_created church_id=%s invite_id=%s role=%s reusable=%s email_bound=%s",
                church_id, row["id"], role, reusable, email is not None)
    return _invite_out(row, creator)


def revoke_invite(church_id: uuid.UUID, actor_id: uuid.UUID, invite_id) -> None:
    """DELETE /invites/{invite_id}: under the church-row lock with the
    caller's role re-read, the role 403, then the invite is revoked when this
    church has it (already revoked, used or expired: still 200); another
    church's id, or an unknown or malformed one, is a 404."""
    actor_id = as_uuid(actor_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin(role)
        if not invites.revoke_invite(invite_id, church_id, session=s):
            raise NotFound(INVITE_NOT_FOUND)
    logger.info("invite_revoked church_id=%s invite_id=%s actor_id=%s", church_id, invite_id, actor_id)
````

- [ ] **Step 4: Run the file, the other lock users and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_members_usecase.py backend/tests/test_church_admin.py backend/tests/test_usecase_contacts.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
156 passed in <t>s
```
```
2140 passed, 38 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/usecases/members.py backend/tests/test_members_usecase.py
git commit -q -m "Slice 6b-1: the member and invite usecases under the church-row lock" -m "usecases/members.py: list_members (is_me, a blank name as None);
change_role and remove_member (lock_and_read_actor, the role 403, the
target as a membership of this church or 404, then role_policy; removal
revokes every invite the removed person made, and with revoke_reusable
every live reusable link, counting each once); list_invites, create_invite
(the role, clean_invite_email with normalize_address, reusable only without
an email, the conflict and invite_exists 409s, expired pending invites
revoked, a unique-index race as invite_exists) and revoke_invite (church
scoped, idempotent). Logs carry ids, roles and counts only." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2140 passed, 38 skipped`; frontend `952 passed` in 109 files.

### Task 6: Transfer ownership, leave and delete (S "Backend changes" `usecases/church_admin.py`, "Transactions and locking"; clarifications 11, 13)

**Files:**
- Create: `backend/tests/test_church_lifecycle.py`
- Modify: `backend/usecases/church_admin.py`

Transfer (to a member or an admin; the answer lists the members afterwards; exactly one owner, `find_violations() == []`; oneself is a 422 naming `user_id`; a stranger or another church's member is a 404 with roles unchanged; only the owner, and an owner who already transferred in another tab is refused); leave (a member or an admin, their services kept and the church gone from their list; an admin's invites keep working; the owner must transfer, even alone; the only admin of an ownerless church cannot, with the exact words, while a member still can); delete (the exact name after trimming, case included; the church soft-deleted and every invite revoked, a used reusable one too, so accepting any says "This invite has been revoked."; only the owner); for each, a church deleted or a caller removed after the guard is `no_church_access`; each reads the church row locked in its own session.

- [ ] **Step 1: Write the failing tests**

**Create `backend/tests/test_church_lifecycle.py`:**

````python
"""usecases.church_admin's transfer, leave and delete (6b spec, "Transactions
and locking", "Role policy"; Testing → test_church_lifecycle.py; slice 6b-1):
each runs in one transaction under the church-row lock with the caller's
role re-read, and leaves every church with exactly one owner."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select, update

from db import session_scope
from db.models import Church, Invite, Service
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound, Rejected
from repos import invites
from repos.churches import get_church, list_user_churches
from repos.integrity import find_violations
from repos.memberships import add_membership, get_role, remove_membership
from tests.test_church_settings import _record_church_row_access
from usecases import church_admin, members, onboarding

NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
NO_ACCESS = ("You don't have access to this church.", {"reason": "no_church_access"})


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com", name="Olive Owner")
    admin = make_user(email="admin@example.com", name="Adam Admin")
    member = make_user(email="member@example.com", name="Mia Member")
    cid = make_church(name="Grace", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    other_owner = make_user(email="elsewhere@example.com")
    other = make_church(name="Hope", owner_user_id=other_owner)
    return {"church": cid, "owner": owner, "admin": admin, "member": member, "other": other,
            "other_owner": other_owner}


def _roles(world) -> list:
    return [get_role(world[w], world["church"]) for w in ("owner", "admin", "member")]


# --- transfer_ownership ---


def test_transfer_swaps_roles_atomically(world):
    out = church_admin.transfer_ownership(world["church"], world["owner"], world["member"])
    assert _roles(world) == ["admin", "admin", "owner"]
    assert [(m["email"], m["role"], m["is_me"]) for m in out] == [
        ("member@example.com", "owner", False), ("admin@example.com", "admin", False),
        ("owner@example.com", "admin", True)]
    assert find_violations() == []


def test_transfer_to_an_admin(world):
    church_admin.transfer_ownership(world["church"], world["owner"], str(world["admin"]))
    assert _roles(world) == ["admin", "owner", "member"]
    assert find_violations() == []


def test_transfer_to_oneself_is_a_422_naming_user_id(world):
    with pytest.raises(InvalidInput) as refused:
        church_admin.transfer_ownership(world["church"], world["owner"], world["owner"])
    assert (refused.value.message, refused.value.field) == ("Choose someone else to be the new owner.", "user_id")
    assert _roles(world) == ["owner", "admin", "member"]


def test_transfer_to_someone_not_in_this_church_is_not_found(world, make_user):
    for target in (world["other_owner"], make_user(email="nobody@example.com"), uuid.uuid4()):
        with pytest.raises(NotFound) as missing:
            church_admin.transfer_ownership(world["church"], world["owner"], target)
        assert missing.value.message == "Member not found."
    assert _roles(world) == ["owner", "admin", "member"]
    assert get_role(world["other_owner"], world["other"]) == "owner"


@pytest.mark.parametrize("who", ["admin", "member"])
def test_only_the_owner_transfers(world, who):
    with pytest.raises(Forbidden) as refused:
        church_admin.transfer_ownership(world["church"], world[who], world["member"])
    assert (refused.value.message, refused.value.details) == ("Only the owner can do that.", None)
    assert _roles(world) == ["owner", "admin", "member"]


def test_an_owner_who_already_transferred_elsewhere_is_refused(world):
    church_admin.transfer_ownership(world["church"], world["owner"], world["admin"])   # another tab, first
    with pytest.raises(Forbidden) as refused:
        church_admin.transfer_ownership(world["church"], world["owner"], world["member"])
    assert refused.value.message == "Only the owner can do that."
    assert _roles(world) == ["admin", "owner", "member"]


# --- leave_church ---


@pytest.mark.parametrize("who", ["member", "admin"])
def test_a_member_or_an_admin_leaves_and_their_services_stay(world, who):
    with session_scope() as s:
        s.add(Service(church_id=world["church"], service_date_iso="2026-10-04", occasion="", hymns=[], liturgy={},
                      scriptures=[], created_by=world[who]))
    church_admin.leave_church(world["church"], world[who])
    assert get_role(world[who], world["church"]) is None
    assert list_user_churches(world[who]) == []
    with session_scope() as s:
        assert s.execute(select(Service.created_by)).scalars().all() == [None]


def test_an_admin_who_leaves_keeps_their_invites_working(world):
    made = members.create_invite(world["church"], world["admin"], now=NOW)
    church_admin.leave_church(world["church"], world["admin"])
    with session_scope() as s:
        assert s.get(Invite, made["id"]).revoked is False


def test_the_owner_must_transfer_before_leaving_even_alone(world, make_user, make_church):
    with pytest.raises(Conflict) as refused:
        church_admin.leave_church(world["church"], world["owner"])
    alone = make_user(email="alone@example.com")
    solo = make_church(name="Solo", owner_user_id=alone)
    with pytest.raises(Conflict) as alone_refused:
        church_admin.leave_church(solo, alone)
    for exc in (refused.value, alone_refused.value):
        assert (exc.code, exc.message) == ("owner_must_transfer", "Transfer ownership before you leave. If you're the "
                                                                   "only person in the church, delete it instead.")
    assert (get_role(world["owner"], world["church"]), get_role(alone, solo)) == ("owner", "owner")


def test_ownerless_sole_admin_cannot_leave(world):
    remove_membership(world["owner"], world["church"])              # made ownerless outside the app
    with pytest.raises(Conflict) as refused:
        church_admin.leave_church(world["church"], world["admin"])
    assert (refused.value.code, refused.value.message) == (
        "last_admin", "You're the last admin. Make someone else an admin before you leave.")
    assert get_role(world["admin"], world["church"]) == "admin"
    church_admin.leave_church(world["church"], world["member"])      # a member still may


# --- delete_church ---


def test_delete_needs_the_exact_name_after_trimming(world):
    for typed in ("grace", "Grace Church", ""):
        with pytest.raises(InvalidInput) as refused:
            church_admin.delete_church(world["church"], world["owner"], typed)
        assert (refused.value.message, refused.value.field) == ("Church name did not match.", "confirm_name")
    assert get_church(world["church"]) is not None
    church_admin.delete_church(world["church"], world["owner"], "  Grace  ")
    assert get_church(world["church"]) is None


def test_delete_soft_deletes_and_revokes_every_invite_even_a_used_reusable_one(world):
    reusable = members.create_invite(world["church"], world["owner"], reusable=True, now=NOW)
    invites.claim(reusable["id"], world["member"], NOW)
    single = members.create_invite(world["church"], world["owner"], now=NOW)
    church_admin.delete_church(world["church"], world["owner"], "Grace")
    with session_scope() as s:
        assert s.get(Church, world["church"]).deleted_at is not None
        assert [s.get(Invite, i["id"]).revoked for i in (reusable, single)] == [True, True]
    for invite in (reusable, single):
        with pytest.raises(Rejected) as rejected:
            onboarding.accept_invite(user_id=world["other_owner"], user_email="elsewhere@example.com",
                                     code=invite["code"], now=NOW)
        assert rejected.value.message == "This invite has been revoked."


@pytest.mark.parametrize("who", ["admin", "member"])
def test_only_the_owner_deletes(world, who):
    with pytest.raises(Forbidden) as refused:
        church_admin.delete_church(world["church"], world[who], "Grace")
    assert (refused.value.message, refused.value.details) == ("Only the owner can do that.", None)
    assert get_church(world["church"]) is not None


# --- lost access under the lock, and the lock itself ---

WRITES = {
    "transfer_ownership": lambda w: church_admin.transfer_ownership(w["church"], w["owner"], w["member"]),
    "leave_church": lambda w: church_admin.leave_church(w["church"], w["owner"]),
    "delete_church": lambda w: church_admin.delete_church(w["church"], w["owner"], "Grace"),
}


@pytest.mark.parametrize("gone", ["church deleted", "actor removed"])
@pytest.mark.parametrize("write", sorted(WRITES))
def test_a_write_after_the_church_or_the_callers_membership_went_is_no_church_access(world, write, gone):
    if gone == "church deleted":
        with session_scope() as s:
            s.execute(update(Church).where(Church.id == world["church"]).values(deleted_at=NOW))
    else:
        remove_membership(world["owner"], world["church"])
    with pytest.raises(Forbidden) as refused:
        WRITES[write](world)
    assert (refused.value.message, refused.value.details) == NO_ACCESS
    assert [get_role(world[w], world["church"]) for w in ("admin", "member")] == ["admin", "member"]


def test_each_write_reads_the_church_row_locked_in_its_own_session(world):
    calls = [lambda: church_admin.transfer_ownership(world["church"], world["owner"], world["admin"]),
             lambda: church_admin.leave_church(world["church"], world["owner"]),       # now an admin
             lambda: church_admin.delete_church(world["church"], world["admin"], "Grace")]
    for call in calls:
        with _record_church_row_access() as (reads, _writes):
            call()
        assert reads and reads[0][1] is True and len({id(session) for session, _ in reads}) == 1
````

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_lifecycle.py 2>&1 | tail -1`
**Expected:** every test fails: `church_admin` has no `transfer_ownership`, `leave_church` or `delete_church` (the fixture's `members.create_invite` exists since T5):
```
23 failed in <t>s
```

- [ ] **Step 3: The usecases**

**In `backend/usecases/church_admin.py`, replace:**

````python
reads); 6a-3b and 6b add their writes here.
````

**with:**

````python
reads); 6a-3b and 6b add their writes here (6b-1: transfer ownership,
leave and delete, which check usecases.role_policy instead of
require_admin_role).
````

**In `backend/usecases/church_admin.py`, replace:**

````python
"""
````

**with:**

````python
"""
import logging
````

**In `backend/usecases/church_admin.py`, replace:**

````python
from bulletin_settings import NOT_ONE_LINE
from domain_errors import Forbidden, InvalidInput
from liturgy_config import SECTION_LABELS
from repos import churches
from repos import hymns as hymn_repo
from tenancy import is_admin
from timezones import is_valid_timezone
from usecases import archive
from usecases.members import lock_and_read_actor
````

**with:**

````python
from db.ids import as_uuid
from bulletin_settings import NOT_ONE_LINE
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound
from liturgy_config import SECTION_LABELS
from repos import churches, memberships
from repos import hymns as hymn_repo
from repos.memberships import LastAdminError
from tenancy import is_admin
from timezones import is_valid_timezone
from usecases import archive, role_policy
from usecases.members import MEMBER_NOT_FOUND, lock_and_read_actor, member_out

logger = logging.getLogger(__name__)
````

**Append to `backend/usecases/church_admin.py`:**

````python


# --- Ownership, leaving and deleting (slice 6b-1; 6b spec, "Transactions and locking") ---------------------

NAME_MISMATCH = "Church name did not match."


def transfer_ownership(church_id: uuid.UUID, actor_id: uuid.UUID, target_id) -> list[dict]:
    """POST /church/transfer-ownership: in one transaction under the
    church-row lock, with the caller's role re-read under it,
    role_policy.check_transfer (only the owner; not to oneself, a 422 naming
    user_id), then the target must be a member of this church (404), then
    repos.memberships.transfer_ownership demotes the caller to admin and then
    promotes the target to owner. Two transfers at once serialize on the lock:
    the second re-reads its role as admin and gets the owner-only 403.
    Returns the members as GET /members lists them, afterwards."""
    actor_id, target_id = as_uuid(actor_id), as_uuid(target_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        role_policy.check_transfer(actor_id=actor_id, actor_role=role, target_id=target_id)
        if memberships.get_member(church_id, target_id, session=s) is None:
            raise NotFound(MEMBER_NOT_FOUND)
        memberships.transfer_ownership(church_id, actor_id, target_id, session=s)
        rows = memberships.list_member_rows(church_id, session=s)
    logger.info("ownership_transferred church_id=%s from_user_id=%s to_user_id=%s", church_id, actor_id, target_id)
    return [member_out(row, actor_id) for row in rows]


def leave_church(church_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    """POST /church/leave: under the church-row lock with the caller's role
    re-read, role_policy.check_leave with the church's owner and admin count
    (the owner must transfer first; the only admin of a church with no owner
    may not leave), then the membership goes, its services.created_by nulled.
    The invites the leaver made stay: they were sent to other people."""
    actor_id = as_uuid(actor_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        role_policy.check_leave(role=role, admin_count=memberships.count_owner_admins(church_id, session=s))
        try:
            memberships.remove_membership(actor_id, church_id, session=s)
        except LastAdminError as exc:   # check_leave refuses first; a backstop, never a 500
            raise Conflict(str(exc), code="last_admin") from None
    logger.info("church_left church_id=%s user_id=%s role=%s", church_id, actor_id, role)


def delete_church(church_id: uuid.UUID, actor_id: uuid.UUID, confirm_name: str) -> None:
    """DELETE /church: under the church-row lock with the caller's role
    re-read, only the owner (403), and `confirm_name`, trimmed, must equal the
    church's name exactly, case included (a 422 naming confirm_name), then
    repos.churches.soft_delete_church in the same transaction: the church is
    soft-deleted and every unrevoked invite of it revoked. Nothing is
    hard-deleted."""
    actor_id = as_uuid(actor_id)
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        if role != "owner":
            raise Forbidden(role_policy.OWNER_ONLY)
        if (confirm_name or "").strip() != churches.get_church(church_id, session=s)["name"]:
            raise InvalidInput(NAME_MISMATCH, field="confirm_name")
        churches.soft_delete_church(church_id, session=s)
    logger.info("church_deleted church_id=%s user_id=%s", church_id, actor_id)
````

- [ ] **Step 4: Run the files and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_lifecycle.py backend/tests/test_church_admin.py backend/tests/test_members_usecase.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
161 passed in <t>s
```
```
2163 passed, 38 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/usecases/church_admin.py backend/tests/test_church_lifecycle.py
git commit -q -m "Slice 6b-1: transfer ownership, leave and delete under the church-row lock" -m "usecases/church_admin.py: transfer_ownership (check_transfer, the target as
a member of this church or 404, then the demote and the promote; answers
the members afterwards), leave_church (check_leave with the owner and
admin count; the leaver's invites stay) and delete_church (the owner only,
the exact name after trimming or a 422 naming confirm_name, then the soft
delete revoking every invite), each in one transaction starting with
lock_and_read_actor." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2163 passed, 38 skipped`; frontend `952 passed` in 109 files.

### Task 7: `require_owner` and the routes (S API, Models, "Role denials", "Lost access under the lock", "Removal sticks", "Cross-church isolation", "Invites", "Guards and contract"; acceptance 1, 3-11, 21; clarifications 15, 16)

**Files:**
- Create: `backend/tests/test_api_members.py`, `backend/tests/test_api_invites_admin.py`, `backend/tests/test_api_church_lifecycle.py`, `backend/api/routes/members.py`
- Modify: `backend/tests/test_route_guards.py`, `backend/api/deps.py`, `backend/api/main.py`, `backend/api/routes/invites.py`, `backend/api/routes/churches.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (regenerated)

Over HTTP: every member reads the list with emails; the policy's words, codes and `fields`; a role that cannot be assigned, a malformed id or flag (422) and a stranger (404); no 409 documented for `PATCH`/`DELETE /members`; removal sticks, end to end with slice 1's accept (a reusable link revoked on removal refuses the removed member; without the flag it still works, as the page will warn; a removed admin cannot redeem any invite they made; a used single-use link stays used); each of the seven writes answers `no_church_access` when the church was deleted after the guard ran, and two when the caller was removed (a test override runs the real `require_church`, then changes the database); a role 403 has no reason; isolation for every route (`assert_church_isolated`, another church's ids are 404s, a smuggled `church_id` is a 422, B's name sent to A deletes nothing). Invites: members refused (403 before any 404); single-use by default, with `Cache-Control: no-store` on the answer and the list; the 422s and both 409s; an Idempotency-Key replay gives the same invite once, a different body with it is 422 `idempotency_mismatch`; no code or email in any log record; revoking is idempotent and church-scoped; a single-use link works once, a reusable one for everyone and stays listed. Lifecycle: only the owner transfers and deletes; transfer answers the members and the old owner reads as an admin; leave refuses the owner (409) and the last admin of an ownerless church (409), and a second leave is `no_church_access`; delete needs the exact name, removes the church from everyone's `/me` and revokes its invites. `test_route_guards.py` pins `ADMIN_ONLY` and the new `OWNER_ONLY` both ways.

- [ ] **Step 1: Write the failing tests**

**Create `backend/tests/test_api_church_lifecycle.py`:**

````python
"""POST /church/transfer-ownership, POST /church/leave and DELETE /church over
HTTP (6b spec, API and Testing → API; slice 6b-1): only the owner transfers
and deletes; transfer answers the members afterwards; leave refuses the owner
and the last admin of an ownerless church; delete needs the church's exact
name and revokes its invites; and church isolation."""
import uuid

import pytest

from repos.churches import get_church
from repos.memberships import add_membership, get_role, remove_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER, ADMIN, MEMBER = "owner@example.com", "admin@example.com", "member@example.com"
OWNER_ONLY = {"code": "forbidden", "message": "Only the owner can do that."}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def people(make_user, make_church):
    ids = {email: make_user(email=email) for email in (OWNER, ADMIN, MEMBER)}
    cid = make_church(name="Grace", owner_user_id=ids[OWNER])
    add_membership(ids[ADMIN], cid, "admin")
    add_membership(ids[MEMBER], cid, "member")
    return cid, ids


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _transfer(client, church, to, *, by=OWNER):
    return client.post("/church/transfer-ownership", headers=church_headers(by, church), json={"user_id": str(to)})


def _delete(client, church, name, *, by=OWNER):
    return client.request("DELETE", "/church", headers=church_headers(by, church), json={"confirm_name": name})


def _my_churches(client, email) -> list:
    return [c["name"] for c in client.get("/me", headers=auth_headers(email)).json()["churches"]]


def test_admin_cannot_transfer_or_delete(client, people):
    church, ids = people
    for r in (_transfer(client, church, ids[MEMBER], by=ADMIN), _delete(client, church, "Grace", by=ADMIN)):
        assert (r.status_code, _error(r)) == (403, OWNER_ONLY)
    assert get_church(church) is not None and get_role(ids[OWNER], church) == "owner"


def test_the_owner_transfers_and_becomes_an_admin(client, people):
    church, ids = people
    r = _transfer(client, church, ids[MEMBER])
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert items[0]["email"] == MEMBER and items[0]["role"] == "owner"
    assert sorted((m["email"], m["role"], m["is_me"]) for m in items[1:]) == [(ADMIN, "admin", False),
                                                                              (OWNER, "admin", True)]
    assert client.get("/church", headers=church_headers(OWNER, church)).json()["role"] == "admin"
    r = _transfer(client, church, ids[ADMIN])                           # no longer the owner
    assert (r.status_code, _error(r)) == (403, OWNER_ONLY)


def test_a_transfer_to_oneself_a_stranger_or_a_bad_body_is_refused(client, people, make_user):
    church, ids = people
    r = _transfer(client, church, ids[OWNER])
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"user_id": "Choose someone else to be the new owner."})
    for stranger in (make_user(email="stranger@example.com"), uuid.uuid4()):
        r = _transfer(client, church, stranger)
        assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Member not found."})
    for body in ({}, {"user_id": "not-a-uuid"}, {"user_id": str(ids[MEMBER]), "role": "owner"}):
        r = client.post("/church/transfer-ownership", headers=church_headers(OWNER, church), json=body)
        assert r.status_code == 422
    assert get_role(ids[OWNER], church) == "owner"


@pytest.mark.parametrize("who", [ADMIN, MEMBER])
def test_a_member_or_an_admin_leaves(client, people, who):
    church, _ids = people
    r = client.post("/church/leave", headers=church_headers(who, church))
    assert (r.status_code, r.json()) == (200, {"left": True})
    assert _my_churches(client, who) == []
    r = client.post("/church/leave", headers=church_headers(who, church))     # again: no longer a member
    assert (r.status_code, r.json()["error"]["details"]) == (403, {"reason": "no_church_access"})


def test_the_owner_and_the_last_admin_of_an_ownerless_church_cannot_leave(client, people):
    church, ids = people
    r = client.post("/church/leave", headers=church_headers(OWNER, church))
    assert (r.status_code, _error(r)) == (409, {
        "code": "owner_must_transfer",
        "message": "Transfer ownership before you leave. If you're the only person in the church, delete it instead."})
    remove_membership(ids[OWNER], church)                               # made ownerless outside the app
    r = client.post("/church/leave", headers=church_headers(ADMIN, church))
    assert (r.status_code, _error(r)) == (409, {
        "code": "last_admin", "message": "You're the last admin. Make someone else an admin before you leave."})
    assert get_role(ids[ADMIN], church) == "admin"


def test_delete_needs_the_exact_name_and_leaves_everyone_without_the_church(client, people, make_user):
    church, ids = people
    make_user(email="x@example.com")
    code = client.post("/invites", headers=church_headers(OWNER, church), json={}).json()["code"]
    r = _delete(client, church, "grace")
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"confirm_name": "Church name did not match."})
    assert client.request("DELETE", "/church", headers=church_headers(OWNER, church)).status_code == 422  # no body
    r = _delete(client, church, "  Grace ")
    assert (r.status_code, r.json()) == (200, {"deleted": True})
    assert get_church(church) is None
    assert [_my_churches(client, email) for email in (OWNER, ADMIN, MEMBER)] == [[], [], []]
    r = client.post("/invites/accept", headers=auth_headers("x@example.com"), json={"code": code})
    assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has been revoked.")


def test_every_lifecycle_route_is_church_isolated(client, isolation_world, make_user):
    w = isolation_world
    a_member = make_user(email="am@example.com")
    add_membership(a_member, w.church_a, "member")
    assert_church_isolated(client, "POST", "/church/leave", world=w)             # a@ owns A: the control is a 409
    r = client.request("DELETE", "/church", headers=church_headers(w.a, w.church_a),
                       json={"confirm_name": "Church B"})                        # B's name, acting in A
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"confirm_name": "Church name did not match."})
    assert_church_isolated(client, "DELETE", "/church", world=w, json={"confirm_name": "Church B"})
    assert get_church(w.church_a) is not None and get_church(w.church_b) is not None
    assert_church_isolated(client, "POST", "/church/transfer-ownership", world=w, json={"user_id": str(a_member)})
    assert get_role(a_member, w.church_a) == "owner"                             # the control, last
````

**Create `backend/tests/test_api_invites_admin.py`:**

````python
"""GET, POST and DELETE /invites over HTTP (6b spec, API, "Invite semantics"
and Testing → API; slice 6b-1): owners and admins only; single-use by
default, reusable on request, email-bound ones single-use; the exact 409s
and 422s; no-store answers; Idempotency-Key replays; codes never logged;
revocation scoped to the church; and the invites working end to end with
slice 1's POST /invites/accept."""
import logging
import uuid

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Invite
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER, ADMIN, MEMBER = "owner@example.com", "admin@example.com", "member@example.com"
ADMINS_ONLY = {"code": "forbidden", "message": "Only church admins can do this."}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=ADMIN), cid, "admin")
    add_membership(make_user(email=MEMBER), cid, "member")
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _create(client, church, body=None, *, by=ADMIN, key=None):
    headers = church_headers(by, church)
    if key is not None:
        headers["Idempotency-Key"] = key
    return client.post("/invites", headers=headers, json=body if body is not None else {})


def _list(client, church, by=ADMIN):
    return client.get("/invites", headers=church_headers(by, church))


def _rows() -> int:
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(Invite)).scalar_one()


def test_member_cannot_create_list_or_revoke_invites(client, church):
    for r in (_create(client, church, by=MEMBER), _list(client, church, by=MEMBER),
              client.delete(f"/invites/{uuid.uuid4()}", headers=church_headers(MEMBER, church))):
        assert (r.status_code, _error(r)) == (403, ADMINS_ONLY)
    assert _rows() == 0


def test_admin_creates_single_use_invite(client, church):
    r = _create(client, church)
    assert r.status_code == 201, r.text
    assert r.headers["cache-control"] == "no-store"
    out = r.json()
    assert set(out) == {"id", "code", "email", "role", "reusable", "created_at", "expires_at", "created_by"}
    assert len(out["code"]) >= 22
    assert (out["email"], out["role"], out["reusable"], out["created_by"]["email"]) == (None, "member", False, ADMIN)
    assert out["created_at"].endswith("Z") or "+00:00" in out["created_at"]
    listed = _list(client, church)
    assert listed.headers["cache-control"] == "no-store"
    assert listed.json() == {"items": [out]}


def test_an_owner_creates_a_reusable_admin_link(client, church):
    out = _create(client, church, {"role": "admin", "reusable": True}, by=OWNER).json()
    assert (out["role"], out["reusable"]) == ("admin", True)


@pytest.mark.parametrize("body, fields", [
    ({"email": "x@example.com", "reusable": True}, {"reusable": "A link for one email address works once."}),
    ({"email": "not an address"}, {"email": "Enter a valid email address."}),
    ({"role": "owner"}, {"role": "Not a valid value."}),
    ({"email": "x" * 321}, {"email": "Too long (max 320 characters)."}),
])
def test_a_bad_invite_is_a_422_naming_its_field(client, church, body, fields):
    r = _create(client, church, body)
    assert (r.status_code, r.json()["error"]["code"], r.json()["error"]["fields"]) == (422, "invalid_request", fields)
    assert _rows() == 0


def test_a_church_id_in_the_body_is_refused_and_nothing_is_created(client, church, make_church, make_user):
    other = make_church(name="Hope", owner_user_id=make_user(email="h@example.com"))
    r = _create(client, church, {"church_id": str(other)})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    assert _rows() == 0


def test_the_two_conflicts_have_their_codes_and_words(client, church):
    _create(client, church, {"email": "new@example.com"})
    r = _create(client, church, {"email": " NEW@example.com "})
    assert (r.status_code, _error(r)) == (409, {
        "code": "invite_exists",
        "message": "There's already a pending invite for new@example.com. Copy its link below or revoke it first."})
    r = _create(client, church, {"email": "Member@Example.com"})
    assert (r.status_code, _error(r)) == (409, {"code": "conflict",
                                                "message": "member@example.com is already a member of this church."})


def test_an_idempotency_key_replays_the_same_invite_once(client, church):
    key = str(uuid.uuid4())
    first = _create(client, church, {"role": "admin"}, key=key)
    again = _create(client, church, {"role": "admin"}, key=key)
    assert (first.status_code, again.status_code) == (201, 201)
    assert (again.json()["id"], again.json()["code"]) == (first.json()["id"], first.json()["code"])
    assert again.headers["idempotent-replayed"] == "true" and again.headers["cache-control"] == "no-store"
    assert _rows() == 1
    r = _create(client, church, {"role": "member"}, key=key)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "idempotency_mismatch")


def test_codes_and_emails_never_reach_the_logs(client, church, caplog):
    caplog.set_level(logging.DEBUG)
    out = _create(client, church, {"email": "secret@example.com"}).json()
    _list(client, church)
    client.delete(f"/invites/{out['id']}", headers=church_headers(ADMIN, church))
    text = "\n".join(f"{r.getMessage()} {r.args}" for r in caplog.records)
    assert out["code"] not in text and "secret@example.com" not in text
    assert f"invite_id={out['id']}" in text


def test_revoking_is_idempotent_and_scoped_to_the_church(client, church, make_church, make_user):
    out = _create(client, church).json()
    for _ in range(2):
        r = client.delete(f"/invites/{out['id']}", headers=church_headers(ADMIN, church))
        assert (r.status_code, r.json()) == (200, {"revoked": True})
    assert _list(client, church).json() == {"items": []}
    other = make_church(name="Hope", owner_user_id=make_user(email="h@example.com"))
    theirs = _create(client, other, by="h@example.com").json()
    r = client.delete(f"/invites/{theirs['id']}", headers=church_headers(ADMIN, church))
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Invite not found."})
    assert _list(client, other, by="h@example.com").json()["items"] == [theirs]
    assert client.delete("/invites/not-a-uuid", headers=church_headers(ADMIN, church)).status_code == 422


def test_a_single_use_link_works_once_and_a_reusable_one_for_everyone(client, church, make_user):
    for email in ("x@example.com", "y@example.com"):
        make_user(email=email)
    single = _create(client, church).json()
    assert client.post("/invites/accept", headers=auth_headers("x@example.com"),
                       json={"code": single["code"]}).status_code == 200
    r = client.post("/invites/accept", headers=auth_headers("y@example.com"), json={"code": single["code"]})
    assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has already been used.")
    reusable = _create(client, church, {"reusable": True}).json()
    for email in ("x@example.com", "y@example.com"):
        r = client.post("/invites/accept", headers=auth_headers(email), json={"code": reusable["code"]})
        assert r.status_code == 200, r.text
    assert [i["id"] for i in _list(client, church).json()["items"]] == [reusable["id"]]


def test_every_invites_route_is_church_isolated(client, isolation_world):
    w = isolation_world
    theirs = _create(client, w.church_b, by=w.b).json()
    mine = _create(client, w.church_a, by=w.a).json()
    assert_church_isolated(client, "GET", "/invites", world=w)
    assert_church_isolated(client, "POST", "/invites", world=w, json={})
    assert_church_isolated(client, "DELETE", f"/invites/{mine['id']}", world=w,
                           resource_path_b=f"/invites/{theirs['id']}")
    assert _list(client, w.church_b, by=w.b).json()["items"] == [theirs]
````

**Create `backend/tests/test_api_members.py`:**

````python
"""/members over HTTP (6b spec, API and Testing → API; slice 6b-1): every
member reads the list with emails; owners and admins change roles and remove
people under the policy's exact messages; a removal revokes the removed
person's invites (and, when asked, every reusable link), end to end with
slice 1's accept; a write whose church or caller went after the guard ran is
the no_church_access 403; and church isolation."""
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import pytest
from fastapi import Depends, Header

from api.deps import CurrentUser, get_current_user, require_church
from db import session_scope
from db.models import Church
from repos.memberships import add_membership, get_role, remove_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER, ADMIN, MEMBER = "owner@example.com", "admin@example.com", "member@example.com"
NO_ACCESS = {"code": "forbidden", "message": "You don't have access to this church.",
             "details": {"reason": "no_church_access"}}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=ADMIN), cid, "admin")
    add_membership(make_user(email=MEMBER), cid, "member")
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _id(client, church, email) -> str:
    r = client.get("/members", headers=church_headers(OWNER, church))
    return next(m["user_id"] for m in r.json()["items"] if m["email"] == email)


def _role(client, church, email, role, *, by=OWNER):
    return client.patch(f"/members/{_id(client, church, email)}", headers=church_headers(by, church),
                        json={"role": role})


def _remove(client, church, email, *, by=OWNER, query=""):
    return client.delete(f"/members/{_id(client, church, email)}{query}", headers=church_headers(by, church))


def test_a_member_reads_every_member_with_emails(client, church):
    r = client.get("/members", headers=church_headers(MEMBER, church))
    assert r.status_code == 200, r.text
    assert [(m["email"], m["role"], m["is_me"]) for m in r.json()["items"]] == [
        (OWNER, "owner", False), (ADMIN, "admin", False), (MEMBER, "member", True)]
    assert set(r.json()["items"][0]) == {"user_id", "email", "name", "role", "is_me"}
    assert client.get("/members", headers=auth_headers(MEMBER)).status_code == 403   # no X-Church-Id


def test_an_admin_makes_a_member_an_admin_and_back(client, church):
    r = _role(client, church, MEMBER, "admin", by=ADMIN)
    assert (r.status_code, r.json()["email"], r.json()["role"], r.json()["is_me"]) == (200, MEMBER, "admin", False)
    assert _role(client, church, MEMBER, "member", by=ADMIN).json()["role"] == "member"


def test_member_cannot_change_role_or_remove(client, church):
    for r in (_role(client, church, ADMIN, "member", by=MEMBER), _remove(client, church, ADMIN, by=MEMBER)):
        assert (r.status_code, _error(r)) == (403, {"code": "forbidden", "message": "Only church admins can do this."})


@pytest.mark.parametrize("by, target, verb, message", [
    (ADMIN, OWNER, "patch", "The owner's role can't be changed."),
    (ADMIN, OWNER, "delete", "The owner can't be removed."),
    (ADMIN, ADMIN, "patch", "You can't change your own role."),
    (ADMIN, ADMIN, "delete", "To leave this church, use Leave church in Danger zone."),
    (OWNER, OWNER, "patch", "You can't change your own role."),
])
def test_the_policy_messages_over_http(client, church, by, target, verb, message):
    r = (_role(client, church, target, "member", by=by) if verb == "patch"
         else _remove(client, church, target, by=by))
    assert (r.status_code, _error(r)) == (403, {"code": "forbidden", "message": message})


def test_owner_cannot_be_removed_even_by_self(client, church):
    """The Streamlit scenario of the last admin removing themselves: now a 403, and the owner stays."""
    r = _remove(client, church, OWNER, by=OWNER)
    assert (r.status_code, _error(r)["message"]) == (403, "To leave this church, use Leave church in Danger zone.")
    assert _id(client, church, OWNER)


@pytest.mark.parametrize("body", [{"role": "owner"}, {"role": "pastor"}, {}, {"role": "admin", "church_id": "x"}])
def test_a_role_that_cannot_be_assigned_is_a_422(client, church, body):
    r = client.patch(f"/members/{_id(client, church, MEMBER)}", headers=church_headers(OWNER, church), json=body)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    if body.get("role") == "owner":
        assert r.json()["error"]["fields"] == {"role": "Not a valid value."}


def test_a_malformed_id_or_flag_is_a_422_and_a_stranger_is_a_404(client, church, make_user):
    headers = church_headers(OWNER, church)
    assert client.patch("/members/not-a-uuid", headers=headers, json={"role": "admin"}).status_code == 422
    assert client.delete(f"/members/{_id(client, church, MEMBER)}?revoke_reusable=maybe",
                         headers=headers).status_code == 422
    stranger = make_user(email="stranger@example.com")
    for r in (client.patch(f"/members/{stranger}", headers=headers, json={"role": "admin"}),
              client.delete(f"/members/{uuid.uuid4()}", headers=headers)):
        assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Member not found."})


def test_no_409_is_documented_for_a_role_change_or_a_removal(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert sorted(paths["/members/{user_id}"]["patch"]["responses"]) == ["200", "401", "403", "404", "422", "503"]
    assert sorted(paths["/members/{user_id}"]["delete"]["responses"]) == ["200", "401", "403", "404", "422", "503"]


# --- removal sticks (end to end with slice 1's POST /invites/accept) ---


def _create(client, church, *, by=OWNER, **body) -> dict:
    r = client.post("/invites", headers=church_headers(by, church), json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _accept(client, email, code):
    return client.post("/invites/accept", headers=auth_headers(email), json={"code": code})


def test_a_removed_member_cannot_rejoin_with_a_reusable_link_revoked_on_removal(client, church, make_user):
    make_user(email="x@example.com")
    link = _create(client, church, reusable=True)
    assert _accept(client, "x@example.com", link["code"]).status_code == 200
    r = _remove(client, church, "x@example.com", query="?revoke_reusable=true")
    assert (r.status_code, r.json()["removed"]) == (200, True) and r.json()["revoked_invites"] >= 1
    r = _accept(client, "x@example.com", link["code"])
    assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has been revoked.")


def test_without_the_flag_a_reusable_link_still_lets_them_rejoin(client, church, make_user):
    make_user(email="x@example.com")
    link = _create(client, church, reusable=True)
    _accept(client, "x@example.com", link["code"])
    assert _remove(client, church, "x@example.com").json() == {"removed": True, "revoked_invites": 0}
    assert _accept(client, "x@example.com", link["code"]).status_code == 200


def test_a_removed_admin_cannot_redeem_the_invites_they_made(client, church, make_user):
    make_user(email="y@example.com")
    single = _create(client, church, by=ADMIN)
    promoting = _create(client, church, by=ADMIN, role="admin", email="y@example.com")
    assert _remove(client, church, ADMIN).json() == {"removed": True, "revoked_invites": 2}
    for email, invite in ((ADMIN, single), ("y@example.com", promoting)):
        r = _accept(client, email, invite["code"])
        assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has been revoked.")


def test_a_used_single_use_link_stays_used_after_a_removal(client, church, make_user):
    make_user(email="x@example.com")
    single = _create(client, church)
    assert _accept(client, "x@example.com", single["code"]).status_code == 200
    _remove(client, church, "x@example.com")
    r = _accept(client, "x@example.com", single["code"])
    assert (r.status_code, r.json()["error"]["message"]) == (400, "This invite has already been used.")


# --- the church or the caller gone after the guard ran ---


def _late(client, change):
    """Wrap require_church: run the real guard, then change the database before the route body."""
    def late_guard(user: CurrentUser = Depends(get_current_user),
                   x_church_id: Optional[str] = Header(default=None)):
        active = require_church(user, x_church_id)
        change(active, user)
        return active

    client.app.dependency_overrides[require_church] = late_guard


def _soft_delete(active, _user):
    with session_scope() as s:
        s.get(Church, active.id).deleted_at = datetime.now(timezone.utc)


def _drop_caller(active, user):
    remove_membership(user.id, active.id)


WRITES = [
    ("PATCH", "/members/{member}", {"role": "admin"}),
    ("DELETE", "/members/{member}", None),
    ("POST", "/invites", {"email": "late@example.com"}),
    ("DELETE", "/invites/{invite}", None),
    ("POST", "/church/transfer-ownership", {"user_id": "{member}"}),
    ("POST", "/church/leave", None),
    ("DELETE", "/church", {"confirm_name": "Grace"}),
]


@pytest.mark.parametrize("method, path, body", WRITES, ids=[f"{m} {p}" for m, p, _ in WRITES])
def test_a_write_whose_church_was_deleted_after_the_guard_is_no_church_access(client, church, method, path, body):
    names = {"member": _id(client, church, MEMBER), "invite": _create(client, church)["id"]}
    _late(client, _soft_delete)
    r = client.request(method, path.format(**names), headers=church_headers(OWNER, church),
                       json=json.loads(json.dumps(body).replace("{member}", names["member"])) if body else None)
    assert (r.status_code, _error(r)) == (403, NO_ACCESS)
    client.app.dependency_overrides.clear()
    assert get_role(uuid.UUID(names["member"]), church) == "member"


@pytest.mark.parametrize("method, path, body", [WRITES[0], WRITES[2]], ids=["PATCH /members", "POST /invites"])
def test_a_write_whose_caller_was_removed_after_the_guard_is_no_church_access(client, church, method, path, body):
    member = _id(client, church, MEMBER)
    _late(client, _drop_caller)
    r = client.request(method, path.format(member=member), headers=church_headers(ADMIN, church), json=body)
    assert (r.status_code, _error(r)) == (403, NO_ACCESS)


def test_a_role_403_carries_no_reason(client, church):
    r = _role(client, church, ADMIN, "member", by=MEMBER)
    assert "details" not in r.json()["error"]


# --- church isolation ---


def test_every_members_route_is_church_isolated(client, isolation_world, make_user):
    w = isolation_world
    a_member = make_user(email="am@example.com")
    add_membership(a_member, w.church_a, "member")
    b_member = make_user(email="bm@example.com")
    add_membership(b_member, w.church_b, "member")
    assert_church_isolated(client, "GET", "/members", world=w)
    assert_church_isolated(client, "PATCH", f"/members/{a_member}", world=w, json={"role": "admin"},
                           resource_path_b=f"/members/{b_member}")
    assert_church_isolated(client, "DELETE", f"/members/{a_member}", world=w,
                           resource_path_b=f"/members/{b_member}")
    assert get_role(b_member, w.church_b) == "member"
````

**In `backend/tests/test_route_guards.py`, replace:**

````python
/church/prayer-library and its voice-profile draft).
````

**with:**

````python
/church/prayer-library and its voice-profile draft; 6b-1: the member and
invite writes and GET /invites).

OWNER_ONLY pins the routes only the church's owner may call (slice 6b-1:
transfer ownership and delete the church): each must have require_owner in
its tree, and every route that has it must be listed.
````

**In `backend/tests/test_route_guards.py`, replace:**

````python
from api.deps import get_current_user, require_admin, require_church
````

**with:**

````python
from api.deps import get_current_user, require_admin, require_church, require_owner
````

**In `backend/tests/test_route_guards.py`, replace:**

````python
    ("DELETE", "/hymns/{hymn_id}"),
````

**with:**

````python
    ("DELETE", "/hymns/{hymn_id}"),
    ("PATCH", "/members/{user_id}"),
    ("DELETE", "/members/{user_id}"),
    ("GET", "/invites"),
    ("POST", "/invites"),
    ("DELETE", "/invites/{invite_id}"),
}
OWNER_ONLY = {
    ("POST", "/church/transfer-ownership"),
    ("DELETE", "/church"),
````

**In `backend/tests/test_route_guards.py`, replace:**

````python
def test_allowlists_name_real_routes():
````

**with:**

````python
def test_owner_routes_require_the_owner():
    routes = route_dependencies(create_app())
    for route in sorted(OWNER_ONLY):
        assert require_owner in routes[route], f"{route} is owner-only but does not depend on require_owner"
    assert {route for route, calls in routes.items() if require_owner in calls} == OWNER_ONLY


def test_allowlists_name_real_routes():
````

**In `backend/tests/test_route_guards.py`, replace:**

````python
    assert PUBLIC.isdisjoint(USER_SCOPED)
    assert ADMIN_ONLY.isdisjoint(PUBLIC | USER_SCOPED)
````

**with:**

````python
    assert OWNER_ONLY - served == set()
    assert PUBLIC.isdisjoint(USER_SCOPED)
    assert ADMIN_ONLY.isdisjoint(PUBLIC | USER_SCOPED)
    assert OWNER_ONLY.isdisjoint(PUBLIC | USER_SCOPED | ADMIN_ONLY)
````

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_members.py backend/tests/test_api_invites_admin.py backend/tests/test_api_church_lifecycle.py backend/tests/test_route_guards.py 2>&1 | tail -1`
**Expected:** `test_route_guards.py` cannot import `require_owner`, so collection stops with one error before any test runs:
```
1 error in <t>s
```

- [ ] **Step 3: The guard, the routes, the router, the API files**

**In `backend/api/deps.py`, replace:**

````python
def get_google_config() -> GoogleOAuthConfig:
````

**with:**

````python
def require_owner(church: ActiveChurch = Depends(require_church)) -> ActiveChurch:
    """The church's owner only (slice 6b-1: transfer ownership, delete the
    church). The usecase re-reads the role under the church-row lock."""
    if church.role != "owner":
        raise forbidden("Only the owner can do that.")
    return church


def get_google_config() -> GoogleOAuthConfig:
````

**In `backend/api/main.py`, replace:**

````python
                        prayer_library, reference, rubric, scripture, services)
````

**with:**

````python
                        members, prayer_library, reference, rubric, scripture, services)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(invites.router)
````

**with:**

````python
    app.include_router(invites.router)
    app.include_router(members.router)
````

**In `backend/api/routes/churches.py`, replace:**

````python
"""POST /churches: create a church; the caller becomes its owner (S API, Idempotency).
````

**with:**

````python
"""POST /churches: create a church; the caller becomes its owner (S API,
Idempotency). Slice 6b-1 adds the church's own lifecycle below it:
POST /church/transfer-ownership and DELETE /church (the owner only,
`require_owner`) and POST /church/leave (any member, `require_church`, so its
403 means "no longer a member"); usecases.church_admin re-reads the caller's
role under the church-row lock. GET and PATCH /church stay in routes/me.py;
FastAPI serves both modules' methods on the same path.

POST /churches:
````

**In `backend/api/routes/churches.py`, replace:**

````python

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.ratelimit import rate_limit
from api.schemas import ChurchOut, CreateChurchIn
from usecases import onboarding
````

**with:**

````python
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church, require_owner
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.ratelimit import rate_limit
from api.routes.members import MemberListOut, MemberOut
from api.schemas import ChurchOut, CreateChurchIn, DeletedOut
from usecases import church_admin, onboarding
````

**Append to `backend/api/routes/churches.py`:**

````python


# --- Slice 6b-1: transfer ownership, leave, delete ---


class TransferOwnershipIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: uuid.UUID


class DeleteChurchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm_name: str = Field(max_length=200)   # the church's name, typed; compared trimmed, case included


class LeftOut(BaseModel):
    left: Literal[True] = True


@router.post("/church/transfer-ownership", response_model=MemberListOut,
             responses=error_responses(401, 403, 404, 422, 503))
def transfer_ownership(payload: TransferOwnershipIn, church: ActiveChurch = Depends(require_owner),
                       user: CurrentUser = Depends(get_current_user)) -> MemberListOut:
    """The new owner must be another member of this church; the caller becomes an admin."""
    return MemberListOut(items=[MemberOut(**m) for m in church_admin.transfer_ownership(church.id, user.id,
                                                                                         payload.user_id)])


@router.post("/church/leave", response_model=LeftOut, responses=error_responses(401, 403, 409, 422, 503))
def leave_church(church: ActiveChurch = Depends(require_church),
                 user: CurrentUser = Depends(get_current_user)) -> LeftOut:
    church_admin.leave_church(church.id, user.id)
    return LeftOut()


@router.delete("/church", response_model=DeletedOut, responses=error_responses(401, 403, 422, 503))
def delete_church(payload: DeleteChurchIn, church: ActiveChurch = Depends(require_owner),
                  user: CurrentUser = Depends(get_current_user)) -> DeletedOut:
    church_admin.delete_church(church.id, user.id, payload.confirm_name)
    return DeletedOut()
````

**In `backend/api/routes/invites.py`, replace:**

````python
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
````

**with:**

````python
"""Invites: joining a church with an invite code (S API; F §4.3, §7.4; AC7,
AC9), and an admin's invites (6b spec, API; slice 6b-1).

POST /invites/preview and /invites/accept are user-scoped: the caller comes
from the token and X-Church-Id is ignored. GET and POST /invites and
DELETE /invites/{invite_id} are for the church's owners and admins
(`require_admin`, then usecases.members re-reads the caller's role under the
church-row lock). An invite code is a bearer secret: it travels only in a
JSON body (the accept and preview requests, and the admin-only GET and POST
answers, which are `Cache-Control: no-store`), never in a path or a query
string, and no log line carries it (the usecases log ids and reasons only).
POST /invites takes an optional Idempotency-Key (api/idempotency.py), so a
retried create never makes a second link. Plain `def` routes: each parses,
calls one usecase and maps its answer. The fixed paths /invites/preview and
/invites/accept are declared before /invites/{invite_id}.
"""
import uuid
from dataclasses import asdict
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.schemas import ChurchOut, InviteAcceptOut, InviteCodeIn, InvitePreviewOut
from usecases import members, onboarding
````

**Append to `backend/api/routes/invites.py`:**

````python


# --- Slice 6b-1: an admin's invites ---

AssignableRole = Literal["member", "admin"]
NO_STORE = "no-store"


class InviteCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: AssignableRole = "member"
    email: str | None = Field(None, max_length=320)   # blank or null: anyone with the link
    reusable: bool = False


class InviteCreatorOut(BaseModel):
    user_id: uuid.UUID
    name: str | None
    email: str


class InviteOut(BaseModel):
    id: uuid.UUID
    code: str                 # a bearer secret, for admins only; the client builds /join?code=
    email: str | None
    role: AssignableRole
    reusable: bool
    created_at: datetime
    expires_at: datetime
    created_by: InviteCreatorOut | None   # null when the creator's account is gone


class InviteListOut(BaseModel):
    items: list[InviteOut]    # newest first


class RevokedOut(BaseModel):
    revoked: Literal[True] = True


@router.get("/invites", response_model=InviteListOut, responses=error_responses(401, 403, 422, 503))
def list_invites(response: Response, church: ActiveChurch = Depends(require_admin)) -> InviteListOut:
    response.headers["Cache-Control"] = NO_STORE
    return InviteListOut(items=[InviteOut(**i) for i in members.list_invites(church.id)])


@router.post("/invites", status_code=201, response_model=InviteOut,
             responses=error_responses(401, 403, 409, 422, 503))
def create_invite(
    payload: InviteCreateIn,
    church: ActiveChurch = Depends(require_admin),
    user: CurrentUser = Depends(get_current_user),
    key: uuid.UUID | None = Depends(idempotency_key()),
) -> Response:
    response = run_idempotent(
        user_id=user.id,
        route="/invites",
        key=key,
        payload=payload,
        status_code=201,
        church_id=church.id,
        call=lambda: InviteOut(**members.create_invite(church.id, user.id, role=payload.role, email=payload.email,
                                                       reusable=payload.reusable)),
    )
    response.headers["Cache-Control"] = NO_STORE
    return response


@router.delete("/invites/{invite_id}", response_model=RevokedOut, responses=error_responses(401, 403, 404, 422, 503))
def revoke_invite(invite_id: uuid.UUID, church: ActiveChurch = Depends(require_admin),
                  user: CurrentUser = Depends(get_current_user)) -> RevokedOut:
    members.revoke_invite(church.id, user.id, invite_id)
    return RevokedOut()
````

**Create `backend/api/routes/members.py`:**

````python
"""/members: the church's people (6b spec, API; slice 6b-1).

Every member reads the list, with emails (decision 5; `require_church`);
owners and admins change a member's role and remove people (`require_admin`,
then usecases.members re-reads the caller's role under the church-row lock
and applies usecases.role_policy). Plain `def` routes, one usecase call each,
no SQL and no try/except (F §2.2 rule 1). A `user_id` is looked up as a
membership of this church: anyone else is a 404.
"""
import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from usecases import members

router = APIRouter()

Role = Literal["owner", "admin", "member"]
AssignableRole = Literal["member", "admin"]


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str | None          # a blank stored name is null
    role: Role
    is_me: bool


class MemberListOut(BaseModel):
    items: list[MemberOut]    # the owner, admins, members; each by name (else email), then user_id


class RoleChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: AssignableRole      # "owner" is never assigned: ownership moves only by a transfer


class RemovedOut(BaseModel):
    removed: Literal[True] = True
    revoked_invites: int      # the invites the removal revoked, each once


@router.get("/members", response_model=MemberListOut, responses=error_responses(401, 403, 422, 503))
def list_members(church: ActiveChurch = Depends(require_church),
                 user: CurrentUser = Depends(get_current_user)) -> MemberListOut:
    return MemberListOut(items=[MemberOut(**m) for m in members.list_members(church.id, user.id)])


@router.patch("/members/{user_id}", response_model=MemberOut, responses=error_responses(401, 403, 404, 422, 503))
def change_role(user_id: uuid.UUID, payload: RoleChangeIn, church: ActiveChurch = Depends(require_admin),
                user: CurrentUser = Depends(get_current_user)) -> MemberOut:
    return MemberOut(**members.change_role(church.id, user.id, user_id, payload.role))


@router.delete("/members/{user_id}", response_model=RemovedOut, responses=error_responses(401, 403, 404, 422, 503))
def remove_member(user_id: uuid.UUID, revoke_reusable: bool = False, church: ActiveChurch = Depends(require_admin),
                  user: CurrentUser = Depends(get_current_user)) -> RemovedOut:
    """Also revokes every invite the removed person created, and with
    `revoke_reusable=true` every live reusable invite of the church."""
    return RemovedOut(revoked_invites=members.remove_member(church.id, user.id, user_id,
                                                            revoke_reusable=revoke_reusable))
````

Then regenerate the snapshot and the types (never by hand):

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null 2>&1) && git status --short -- frontend`
**Expected:**
```
 M frontend/src/lib/api/openapi.json
 M frontend/src/lib/api/schema.d.ts
```

- [ ] **Step 4: Run the files, the contract, the frontend checks and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_members.py backend/tests/test_api_invites_admin.py backend/tests/test_api_church_lifecycle.py backend/tests/test_route_guards.py backend/tests/test_openapi_contract.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_api_invites.py 2>&1 | tail -1` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
89 passed in <t>s
```
```
typecheck 0
lint 0
```
```
2216 passed, 38 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/api/deps.py backend/api/main.py backend/api/routes/members.py backend/api/routes/invites.py backend/api/routes/churches.py backend/tests/test_api_members.py backend/tests/test_api_invites_admin.py backend/tests/test_api_church_lifecycle.py backend/tests/test_route_guards.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Slice 6b-1: require_owner and the People routes (members, invites, transfer, leave, delete)" -m "api/deps.require_owner (\"Only the owner can do that.\"). GET /members (every
member, with emails), PATCH and DELETE /members/{user_id} (admins; DELETE
takes ?revoke_reusable=); GET, POST (Idempotency-Key, church-scoped) and
DELETE /invites (admins; the GET and POST answers no-store);
POST /church/transfer-ownership and DELETE /church (the owner; the delete
takes {confirm_name}); POST /church/leave (any member). Plain def routes,
one usecase call each. test_route_guards pins the five new admin routes in
ADMIN_ONLY and the two owner routes in a new OWNER_ONLY, both ways. The
OpenAPI snapshot and schema.d.ts are regenerated; no page uses the routes
until 6b-2." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2216 passed, 38 skipped`; frontend `952 passed` in 109 files.

### Task 8: The writes serialize on real Postgres (S Testing → Postgres; acceptance 6, 9, 21; clarification 14)

**Files:**
- Create: `backend/tests/test_people_postgres.py`

Seven races, each forced the same way (the first write held inside the lock, the second started and still waiting a second later, then both finished): two transfers at once leave one owner and the second gets "Only the owner can do that."; a transfer to someone leaving, in both orders (the leave then the transfer's 404, or the transfer then the leave's 409), never leaves the church ownerless; two admins of an ownerless church removing each other leave one, the loser `no_church_access`; two invites for one email make one, the other `invite_exists`; two inserts that skip the lock still cannot both be pending (the index's `IntegrityError`); a profile save and a role change both happen; a delete and an invite, in both orders, leave no live invite of the deleted church.

- [ ] **Step 1: Write the tests**

**Create `backend/tests/test_people_postgres.py`:**

````python
"""Slice 6b-1's writes on real Postgres (6b spec, Testing → Postgres;
"Transactions and locking"): every membership, invite, transfer, leave and
delete write takes the church-row lock and re-reads the caller's role under
it, so two writes to one church serialize, and the loser sees the winner's
result. The partial unique index refuses a second pending invite for an email
even without the lock.

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs it. SQLite
ignores FOR UPDATE, so only these tests prove the waiting. Each forces the
race the same way: a function the first write calls through its module after
taking the lock waits until the test lets it go; the second write is started
meanwhile and must still be waiting a second later. A write that never gets
there fails the test after 10 s instead of passing vacuously.
"""
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from db import session_scope
from db.models import Invite
from domain_errors import Conflict, Forbidden, NotFound
from repos import churches, invites
from repos.churches import create_church
from repos.integrity import find_violations
from repos.memberships import add_membership, get_role, remove_membership
from repos.users import ensure_user
from usecases import church_admin, members, role_policy

pytestmark = pytest.mark.postgres
NOW = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def world(pg_db):
    ids = {who: ensure_user(f"{who}@example.com", who.title()).id for who in ("owner", "b", "c")}
    church = create_church(name="Grace", timezone="America/New_York", owner_user_id=ids["owner"])
    add_membership(ids["b"], church, "admin")
    add_membership(ids["c"], church, "member")
    return church, ids


def _hold(monkeypatch, module, name):
    """Make module.name wait inside the first call until released; returns (inside, release)."""
    inside, release = threading.Event(), threading.Event()
    real = getattr(module, name)
    calls = []

    def held(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            inside.set()               # the first write holds the church-row lock here
            assert release.wait(10), f"the test never released {name}"
        return real(*args, **kwargs)

    monkeypatch.setattr(module, name, held)
    return inside, release


def _race(first, second, inside, release):
    """Run `first`, wait until it holds the lock, start `second`, check it waits, release.
    Returns both outcomes (a value or the exception)."""
    def outcome(future):
        try:
            return future.result(10)
        except Exception as exc:       # noqa: BLE001 - the loser's refusal is the result
            return exc

    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(first)
        assert inside.wait(10), "the first write never took the lock"
        b = pool.submit(second)
        threading.Event().wait(1)      # time for the second to finish if nothing held it
        assert not b.done(), "the second write did not wait for the church-row lock"
        release.set()
        return outcome(a), outcome(b)


def test_two_transfers_at_once_leave_one_owner(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, role_policy, "check_transfer")
    first, second = _race(lambda: church_admin.transfer_ownership(church, ids["owner"], ids["b"]),
                          lambda: church_admin.transfer_ownership(church, ids["owner"], ids["c"]),
                          inside, release)
    assert [m["role"] for m in first if m["user_id"] == ids["b"]] == ["owner"]
    assert isinstance(second, Forbidden) and second.message == "Only the owner can do that."
    assert [get_role(ids[w], church) for w in ("owner", "b", "c")] == ["admin", "owner", "member"]
    assert find_violations() == []


def test_a_transfer_to_someone_leaving_never_leaves_the_church_ownerless(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, role_policy, "check_transfer")
    _transfer, leave = _race(lambda: church_admin.transfer_ownership(church, ids["owner"], ids["c"]),
                             lambda: church_admin.leave_church(church, ids["c"]), inside, release)
    assert isinstance(leave, Conflict) and leave.code == "owner_must_transfer"
    assert get_role(ids["c"], church) == "owner"
    monkeypatch.undo()
    other = create_church(name="Hope", timezone="UTC", owner_user_id=ids["owner"])
    add_membership(ids["c"], other, "member")
    inside, release = _hold(monkeypatch, role_policy, "check_leave")
    _left, transfer = _race(lambda: church_admin.leave_church(other, ids["c"]),
                            lambda: church_admin.transfer_ownership(other, ids["owner"], ids["c"]), inside, release)
    assert isinstance(transfer, NotFound) and transfer.message == "Member not found."
    assert get_role(ids["owner"], other) == "owner"
    assert find_violations() == []


def test_two_admins_of_an_ownerless_church_removing_each_other_leave_one(world, monkeypatch):
    church, ids = world
    remove_membership(ids["owner"], church)
    add_membership(ids["owner"], church, "admin")          # now an ownerless church with two admins
    inside, release = _hold(monkeypatch, role_policy, "check_remove")
    first, second = _race(lambda: members.remove_member(church, ids["owner"], ids["b"]),
                          lambda: members.remove_member(church, ids["b"], ids["owner"]), inside, release)
    assert first == 0
    assert isinstance(second, Forbidden) and second.details == {"reason": "no_church_access"}
    assert (get_role(ids["owner"], church), get_role(ids["b"], church)) == ("admin", None)
    assert [v["kind"] for v in find_violations()] == ["owner_count"]   # the seeded ownerless church only


def test_two_invites_for_one_email_at_once_make_one(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, members, "clean_invite_email")
    first, second = _race(lambda: members.create_invite(church, ids["owner"], email="new@example.com"),
                          lambda: members.create_invite(church, ids["b"], email="NEW@example.com"), inside, release)
    assert first["email"] == "new@example.com"
    assert isinstance(second, Conflict) and second.code == "invite_exists"
    with session_scope() as s:
        assert s.execute(select(Invite.email)).scalars().all() == ["new@example.com"]


def test_the_pending_email_index_refuses_a_second_insert_even_without_the_lock(world):
    """Two transactions that never take the church-row lock (a direct write):
    the second insert waits on the first's index entry and fails once it commits."""
    church, ids = world
    inserted, release = threading.Event(), threading.Event()

    def first():
        with session_scope() as s:
            invites.insert_invite(church_id=church, created_by=ids["owner"], role="member", email="a@example.com",
                                  reusable=False, session=s)
            inserted.set()
            assert release.wait(10)

    def second():
        with session_scope() as s:
            invites.insert_invite(church_id=church, created_by=ids["b"], role="admin", email="A@example.com",
                                  reusable=False, session=s)

    with ThreadPoolExecutor(2) as pool:
        a = pool.submit(first)
        assert inserted.wait(10)
        b = pool.submit(second)
        threading.Event().wait(1)
        assert not b.done(), "the second insert did not wait for the first's index entry"
        release.set()
        a.result(10)
        with pytest.raises(IntegrityError, match="uq_invites_pending_email"):
            b.result(10)


def test_a_profile_save_and_a_role_change_at_once_both_happen(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, church_admin, "clean_profile_patch")
    profile, role = _race(lambda: church_admin.update_profile(church, ids["owner"], {"default_benediction": "Go."}),
                          lambda: members.change_role(church, ids["b"], ids["c"], "admin"), inside, release)
    assert profile["name"] == "Grace" and role["role"] == "admin"
    assert churches.get_church(church)["settings"]["default_benediction"] == "Go."


def test_a_delete_and_an_invite_at_once_leave_no_live_invite(world, monkeypatch):
    church, ids = world
    inside, release = _hold(monkeypatch, members, "clean_invite_email")
    _invite, _deleted = _race(lambda: members.create_invite(church, ids["b"], email="late@example.com"),
                              lambda: church_admin.delete_church(church, ids["owner"], "Grace"), inside, release)
    with session_scope() as s:
        assert s.execute(select(Invite.revoked)).scalars().all() == [True]     # made, then revoked by the delete
    monkeypatch.undo()
    other = create_church(name="Hope", timezone="UTC", owner_user_id=ids["owner"])
    add_membership(ids["b"], other, "admin")
    inside, release = _hold(monkeypatch, churches, "soft_delete_church")
    _deleted, invite = _race(lambda: church_admin.delete_church(other, ids["owner"], "Hope"),
                             lambda: members.create_invite(other, ids["b"], email="later@example.com"),
                             inside, release)
    assert isinstance(invite, Forbidden) and invite.details == {"reason": "no_church_access"}
    with session_scope() as s:
        assert s.execute(select(Invite.id).where(Invite.church_id == other)).all() == []
````

- [ ] **Step 2: See them skip here, and pass on a local Postgres**

Run: `.venv/bin/python -m pytest -q backend/tests/test_people_postgres.py 2>&1 | tail -1` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q backend/tests/test_people_postgres.py 2>&1 | tail -1` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected** (without `TEST_DATABASE_URL` they skip; CI's `backend-postgres` job runs them):
```
7 skipped in <t>s
```
```
7 passed in <t>s
```
```
45 passed, 2216 deselected, 1 warning in <t>s
```
```
2216 passed, 45 skipped in <t>s
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_people_postgres.py
git commit -q -m "Slice 6b-1: the People writes serialize on Postgres" -m "test_people_postgres: with the first write held inside the church-row lock,
the second waits and then sees its result: two transfers leave one owner;
a transfer and the target's leave, in both orders, never leave the church
ownerless; two admins of an ownerless church removing each other leave
one; two invites for one email make one; a profile save and a role change
both happen; a delete and an invite, in both orders, leave no live invite.
And two inserts that skip the lock cannot both be pending (the partial
unique index). Skipped without TEST_DATABASE_URL." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2216 passed, 45 skipped`; frontend `952 passed` in 109 files. CI's `backend-postgres`: `45 passed, 2216 deselected`.

## Docs, verification, the PR, the owner's routine and the merge (T9-T11)

### Task 9: Docs: the manual check items (clarification 19)

**Files:**
- Modify: `backend/tests/test_slice1_docs.py`, `docs/manual-verification.md`

`docs/manual-verification.md` gains "## Slice 6b" with the 6b-1 items: the owner's three before the merge (the backup, the counts and checks, the SQL preview), two after (the after-deploy check; the app as before on the phone) and the agent's one (the routes are served and want a sign-in). `test_slice1_docs.py`'s pin of the last `##` headings takes the new one.

- [ ] **Step 1: The pin**

**In `backend/tests/test_slice1_docs.py`, replace:**

````python
    # PR 1 "## Printed bulletin", slice 6a-1 "## Slice 6a" and slice 5b-1 "## Slice 5b".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-10:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4", "## Service reviewer",
                        "## Slice 5a", "## Printed bulletin", "## Slice 6a", "## Slice 5b"]
````

**with:**

````python
    # PR 1 "## Printed bulletin", slice 6a-1 "## Slice 6a", slice 5b-1 "## Slice 5b" and slice 6b-1 "## Slice 6b".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-11:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4", "## Service reviewer",
                        "## Slice 5a", "## Printed bulletin", "## Slice 6a", "## Slice 5b", "## Slice 6b"]
````

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py 2>&1 | tail -1`
**Expected:**
```
1 failed, 5 passed in <t>s
```

- [ ] **Step 2: The items**

**Append to `docs/manual-verification.md`:**

````markdown

## Slice 6b

Slice 6b moves People (members and invites) and the Danger zone (transfer
ownership, leave, delete the church) into Settings, in two PRs (owner's 6b
planning answers of 2026-10-09). **6b-1** is the server side only:
`GET /members`, `PATCH` and `DELETE /members/{user_id}`, `GET`, `POST` and
`DELETE /invites`, `POST /church/transfer-ownership`, `POST /church/leave`
and `DELETE /church`, and migration `0008_invites_integrity`. No page uses
them until 6b-2, so the app looks and works as before. The owner's steps
around the 6b-1 merge follow `backend/migrations/README.md` → "Before
0008_invites_integrity", one step at a time; the results go into
`docs/ops-runbook.md` → "Slice 6b-1 record". Record counts and what the
screens show, never an email address, an invite code or link, a church id
or a database URL. 6b-2 (the People and Danger zone pages) adds its items
here.

- [ ] (owner, before the 6b-1 merge) **1.** A fresh backup: the db-backup workflow on `main` finishes green with an artifact `db-backup`.
- [ ] (owner, before the 6b-1 merge) **2.** "Before 0008_invites_integrity" step 2's read-only query in Supabase's SQL Editor shows `version` `0007_bulletin_images`, `duplicate_pending_pairs` `0` and `old_constraint` `1`; the other counts are recorded (`churches_without_one_owner` and `churches_without_admin` are normally `0`).
- [ ] (owner, before the 6b-1 merge) **3.** The SQL preview the agent renders from the PR's code matches step 3 of that section, and the owner has read it.
- [ ] (owner, after 6b-1) **4.** Step 4's read-only query shows `0008_invites_integrity`, `1`, `1`, `0`; step 2's query again shows the same counts (or more invites), with `other_role_invites` `0` and `old_constraint` `0`.
- [ ] (owner, after 6b-1) **5.** On the phone, the app loads as before (pull down to reload): the builder opens and **Settings** lists the same sections as before 6b-1 (no People or Danger zone yet). If you still have an invite link (`…/join?code=…`) to your church that nobody has used yet, open it on the phone while signed in: it says "You're already a member of {church}." with **Open {church}**, which opens the church and changes nothing (the link stays unused); without such a link, that half is skipped.
- [ ] (agent, after 6b-1) **6.** `/health/ready` answers `{"ok":true,"db":"ok"}`; `/openapi.json` lists `/members`, `/members/{user_id}`, `/invites`, `/invites/{invite_id}`, `/church/transfer-ownership` and `/church/leave`, and `/church` with `delete`; each of the new routes answers 401 when called signed out.
````

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `git diff -- docs/manual-verification.md | grep '^+' | grep -c '—'`
**Expected:**
```
89 passed in <t>s
```
```
0
```

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -q -m "Docs: slice 6b-1's manual check items" -m "docs/manual-verification.md gains \"## Slice 6b\" with the 6b-1 items: the
owner's backup, read-only counts and checks, and SQL preview before the
merge; the after-deploy check and a short phone check (the app as before)
after it; and the agent's check that the new routes are served and want a
sign-in. test_slice1_docs pins the new heading." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2216 passed, 45 skipped`; frontend `952 passed` in 109 files.

### Task 10: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Every `gh` command uses `-R <repo>` (or the session's GitHub tools, with the same effect). Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

Run: `git status --short | grep -v '^?? .claude/' | wc -l` then `git fetch -q origin && git rev-list --count HEAD..origin/main` then `ls backend/migrations/versions | grep -c '^0'`
**Expected:** `0` (nothing uncommitted); `0`; `8` (with T1's revision). If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 10)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner. If `main` gained a revision after `0007_bulletin_images`, stop: `0008`'s `down_revision` and number must follow it (clarification 2), and the owner's SQL preview changes.
```
0
```
```
0
```
```
8
```

- [ ] **Step 2 (agent): Both suites, Postgres, types, lint, the build**

Run: `.venv/bin/python -m pytest -q | tail -1` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres 2>&1 | tail -1` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -cE "Compiled successfully")`
**Expected** (the Postgres line only where a local, throwaway Postgres is at hand; otherwise CI's job is the check; a font `Failed to fetch` in the build: say so and rely on CI):
```
2216 passed, 45 skipped in <t>s
```
```
45 passed, 2216 deselected, 1 warning in <t>s
```
```
 Test Files  109 passed (109)
      Tests  952 passed (952)
```
```
typecheck 0
lint 0
```
```
1
```

- [ ] **Step 3 (agent): The API files match, the gates, the paths, the commits**

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null 2>&1) && git status --short -- frontend backend | wc -l` then `grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/usecases/members.py backend/usecases/church_admin.py backend/usecases/role_policy.py backend/repos/integrity.py; echo "imports grep exit $?"` then `git diff origin/main...HEAD -- backend frontend/src pytest.ini docs/manual-verification.md | grep '^+' | grep -c '—'` then `python3 -c "import pathlib; t=pathlib.Path('docs/superpowers/plans/2026-10-09-slice-6b1-people-backend.md').read_text(); print(sum(t.count(c) for c in ('\u2028','\u2029','\ufffe','\uffff')))"` then `git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2` then `git diff --name-only origin/main...HEAD -- .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt requirements.txt app.py streamlit_views streamlit_tests streamlit_auth.py streamlit_tenancy.py ui_helpers.py backend/api/idempotency.py backend/api/schemas.py backend/api/errors.py backend/domain_errors.py backend/email_addresses.py backend/usecases/onboarding.py backend/migrations/env.py backend/db/schema_check.py | wc -l` then `git log --reverse --no-merges --format=%s origin/main..HEAD | grep -v -e '^WIP plan: ' -e '^Plan: '` then `for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"`
**Expected:** `0` (the committed snapshot and types are current); `imports grep exit 1`; `0` (no em dash in an added line of code, tests or the checklist); `0` (no U+2028, U+2029, U+FFFE or U+FFFF in this plan); exactly these 45 paths (the 6a-3b record and the 6b amendment ride along until merged); `0` (nothing that must stay untouched changed); the subjects oldest first, then any `Fix: …` lines (the plan's own commits are left out by the `grep`); only `trailer check done`:
```
0
```
```
imports grep exit 1
```
```
0
```
```
0
```
```
M	backend/api/deps.py
M	backend/api/main.py
M	backend/api/routes/churches.py
M	backend/api/routes/invites.py
A	backend/api/routes/members.py
M	backend/db/models.py
M	backend/migrations/README.md
A	backend/migrations/versions/0008_invites_integrity.py
M	backend/repos/churches.py
A	backend/repos/integrity.py
M	backend/repos/invites.py
M	backend/repos/memberships.py
A	backend/scripts/check_integrity.py
A	backend/tests/fixtures/shared/role_policy.json
A	backend/tests/invite_helpers.py
M	backend/tests/test_api_app.py
A	backend/tests/test_api_church_lifecycle.py
M	backend/tests/test_api_invites.py
A	backend/tests/test_api_invites_admin.py
A	backend/tests/test_api_members.py
A	backend/tests/test_church_lifecycle.py
M	backend/tests/test_churches_repo.py
A	backend/tests/test_integrity.py
M	backend/tests/test_invites_repo.py
A	backend/tests/test_members_usecase.py
M	backend/tests/test_memberships_repo.py
M	backend/tests/test_migrations.py
M	backend/tests/test_no_streamlit_in_core.py
A	backend/tests/test_people_postgres.py
A	backend/tests/test_role_policy.py
M	backend/tests/test_route_guards.py
M	backend/tests/test_schema_check.py
M	backend/tests/test_services_postgres.py
M	backend/tests/test_slice1_docs.py
M	backend/tests/test_usecase_onboarding.py
M	backend/usecases/church_admin.py
M	backend/usecases/members.py
A	backend/usecases/role_policy.py
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-09-slice-6b1-people-backend.md
M	docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	pytest.ini
```
```
0
```
```
Runbook: slice 6a-3b record (merged; owner's phone check)
Spec: slice 6b planning answers (owner, 2026-10-09)
Migration 0008_invites_integrity: member/admin invites, one pending invite per email
Slice 6b-1: the church integrity check (repos.integrity, check_integrity.py)
Slice 6b-1: the role policy and its 51-row shared fixture
Slice 6b-1: the repos for members, invites and the church's delete
Slice 6b-1: the member and invite usecases under the church-row lock
Slice 6b-1: transfer ownership, leave and delete under the church-row lock
Slice 6b-1: require_owner and the People routes (members, invites, transfer, leave, delete)
Slice 6b-1: the People writes serialize on Postgres
Docs: slice 6b-1's manual check items
```
```
trailer check done
```

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

(not replayed) `gh pr list -R <repo> --head claude/slice-2-plan-4q33le --state open --json number,url` → `[]`. Send the owner exactly this, and wait for a clear yes:

> The server side of People (slice 6b-1) is verified on this machine: backend 2216 passed, 45 skipped (1983 and 35 before), and the 45 Postgres tests pass on a throwaway local database; frontend 952 tests in 109 files, typecheck, lint and the production build unchanged and clean. It adds the routes the People and Danger zone pages will use (6b-2): see the members, change roles, remove someone, invite links (single-use by default, or reusable for 7 days, optionally for one email), transfer ownership, leave, delete the church. Nothing in the app changes until 6b-2. It includes one database change, migration 0008: invites can only grant member or admin, and an email can have only one waiting invite at a time (so it can be invited again after a revoke). Before merging I will take you through the same routine as last time: a backup, one read-only query in Supabase, and the SQL to read. May I open the pull request as a **draft** titled "Slice 6b-1: People on the server (members, invites, ownership, leave, delete) and migration 0008", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/6b1-pr-body.md" <<'BODY'
Slice 6b-1: the server side of People and the Danger zone, with migration 0008_invites_integrity (the first of slice 6b's two PRs; owner's 6b planning answers of 2026-10-09). Spec: docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md and its amendment of 2026-10-09. Plan: docs/superpowers/plans/2026-10-09-slice-6b1-people-backend.md. No page changes (6b-2), no new package or variable.

- Routes: GET /members (every member, with emails); PATCH and DELETE /members/{user_id} (owners and admins; never the owner or oneself; a removal revokes the removed person's invites, and with ?revoke_reusable=true every live reusable link); GET, POST (Idempotency-Key) and DELETE /invites (owners and admins; single-use by default, reusable for 7 days, optionally email-bound; no-store answers; codes never logged); POST /church/transfer-ownership and DELETE /church (the owner; the delete needs the exact name); POST /church/leave (anyone but the owner). api/deps.require_owner; ADMIN_ONLY and a new OWNER_ONLY in test_route_guards.
- usecases/role_policy.py with the 51-row shared fixture; usecases/members.py and church_admin.py: every write in one transaction under the church-row lock with the caller's role re-read (a church or membership gone after the guard is no_church_access).
- Migration 0008_invites_integrity: other invite roles made admin and revoked; refuses over duplicate pending email invites (naming churches, never emails); uq_invites_church_email replaced by the partial unique index uq_invites_pending_email on (church_id, lower(email)) and the check ck_invites_role. backend/migrations/README.md: "Before 0008_invites_integrity" and "Church integrity (slice 6b)"; repos/integrity.py and scripts/check_integrity.py.
- Postgres tests: two transfers, transfer against leave, mutual removal, two invites for one email, the index without the lock, profile against role change, delete against invite.
- docs/manual-verification.md: "Slice 6b" (6b-1 items). Rides along: the 6a-3b record and the 6b spec amendment.

Before the merge (Task 11): the backup, the read-only counts and integrity check, and the SQL preview with the owner. After: the after-deploy check, a short phone check, a "Slice 6b-1 record" in docs/ops-runbook.md.

Tests: backend 1983 → 2216 passed, 35 → 45 skipped; frontend 952 in 109 files (unchanged)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R <repo> --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 6b-1: People on the server (members, invites, ownership, leave, delete) and migration 0008" \
  --body-file "<scratch>/6b1-pr-body.md"
gh pr checks <N> -R <repo> --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `2216 passed, 45 skipped`, backend-postgres `45 passed, 2216 deselected` (after its `alembic upgrade head`, `alembic check`, `alembic downgrade base` and `alembic upgrade head` steps, which now include 0008 on Postgres 17), frontend `952 passed` in 109 files. Then send: "PR #<N> is green: backend 2216 passed, 45 skipped (the ten new Postgres tests passed in their own job, and the migration went up, down and up again on Postgres); 952 frontend tests in 109 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you, after the backup, the query and the SQL." On the yes: `gh pr ready <N> -R <repo>`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_migrations.py` (0008), `test_schema_check.py`, `test_api_app.py`, `test_services_postgres.py`, `test_models.py`, CI's `alembic check` | T1 |
| `test_api_invites.py`, `test_usecase_onboarding.py` (the clamp tests) | T1 (the soft-delete case: T4) |
| `test_integrity.py` | T2 |
| `test_role_policy.py`, `test_no_streamlit_in_core.py` | T3 |
| `test_memberships_repo.py`, `test_invites_repo.py`, `test_churches_repo.py`, `streamlit_tests` | T4 |
| `test_members_usecase.py`, `test_church_admin.py`, `test_usecase_contacts.py` | T5 |
| `test_church_lifecycle.py` | T6 |
| `test_api_members.py`, `test_api_invites_admin.py`, `test_api_church_lifecycle.py`, `test_route_guards.py`, `test_openapi_contract.py`, `typecheck`, CI's "API types match" step | T7 |
| `test_people_postgres.py` (CI `backend-postgres`) | T8 (the lock itself: T5, T6) |
| `test_slice1_docs.py`, `test_docs.py` | T9 |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, slice 6b-1 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `2216 passed, 45 skipped`; frontend `952 passed` in 109 files.

### Task 11: Before the merge (backup, counts and checks, SQL), the merge, the after-deploy check, the phone check, the record (OWNER + agent)

The owner's steps go **one at a time** (send one, wait for the report or "next"), in plain words. The queries are the ones in `backend/migrations/README.md` → "Before 0008_invites_integrity" (pinned by T1's tests); copy them from there, in full, into a code block. The agent writes each result into `<scratch>/6b1-t11-results.md` (not committed). Record numbers and what the screens showed, never a church id, an email address, an invite code or link, a token or a database URL. 6b-1 changes no page, so the phone check is short: the app loads and works as before.

**Files:** Modify (Step 8, the records PR): `docs/ops-runbook.md`: insert `### Slice 6b-1 record` right before `## Backups` (after the last record above it, today `### Slice 6a-3b record`, whose table's last row starts `| Follow-ups |`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER, then agent): The backup**

Check first (not replayed): `gh pr view <N> -R <repo> --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send:

> PR #<N> (slice 6b-1, the server side of People) is ready and green. It changes the database (migration 0008), so before it merges we do the same three checks as for the cover pictures. Here is the first: may I start a fresh database backup now (the db-backup workflow on main, about a minute)? Nothing else happens yet.

On a clear yes (not replayed):

```bash
gh workflow run db-backup --ref main -R <repo>
RUN=$(gh run list -R <repo> --workflow backup.yml --branch main --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId'); echo "$RUN"
gh run watch "$RUN" -R <repo> --exit-status --interval 15 >/dev/null; echo "backup exit $?"
gh run view "$RUN" -R <repo> --json url,conclusion --jq '"\(.conclusion) \(.url)"'
gh api "repos/<repo>/actions/runs/$RUN/artifacts" --jq '.artifacts[] | "\(.name) \(.size_in_bytes)"'
```

**Expected:** a run id (started a few seconds ago; if `gh run list` shows an older run, wait and list again); `backup exit 0`; `success <run URL>`; `db-backup <bytes>`. Record the URL and the size. A failure: stop and tell the owner; nothing merges without a green backup.

- [ ] **Step 2 (OWNER, then agent): The counts and the integrity check (read-only)**

Send, with README step 2's query pasted in full inside a code block:

> Second check: one read-only query; it only counts. Open Supabase → your project → SQL Editor → New query, paste the query below, and press Run. You should see one row with nine values. Please tell me what each column shows: version, invites, pending_email_invites, duplicate_pending_pairs, other_role_invites, old_constraint, churches, churches_without_one_owner, churches_without_admin.

**Expected:** `version` `0007_bulletin_images`; `duplicate_pending_pairs` `0`; `old_constraint` `1`; `other_role_invites` normally `0`; `churches_without_one_owner` and `churches_without_admin` normally `0`; the rest are counts to record. Then:
- `version` not `0007_bulletin_images`, or `old_constraint` not `1`: stop and tell the owner what it means before going on (another release ran, or the constraint has another name; the migration would refuse, safely).
- `duplicate_pending_pairs` above `0`: stop. Explain: "Some person was invited twice and both invites are still waiting; the update refuses to run over that. The fix keeps the newest invite for each person and cancels the older copies (the person can still use the newest link)." On the owner's yes, guide them through "Church integrity" step 2's `UPDATE` in the SQL Editor (the backup of Step 1 is fresh), then run this step's query again: `0`.
- `other_role_invites` above `0`: not a stop; record it (the update turns those invites into admin invites and cancels them).
- `churches_without_one_owner` or `churches_without_admin` above `0`: not a stop for this PR; record the counts, and, as owner question 2 says, send a second read-only query that names the church (`SELECT c.name, (SELECT count(*) FROM memberships m WHERE m.church_id = c.id AND m.role = 'owner') AS owners, (SELECT count(*) FROM memberships m WHERE m.church_id = c.id AND m.role IN ('owner', 'admin')) AS owners_and_admins FROM churches c WHERE c.deleted_at IS NULL AND ((SELECT count(*) FROM memberships m WHERE m.church_id = c.id AND m.role = 'owner') <> 1 OR NOT EXISTS (SELECT 1 FROM memberships m WHERE m.church_id = c.id AND m.role IN ('owner', 'admin')));`); the repair waits for the owner's choice ("Church integrity" steps 3 and 4, after a fresh backup) and is recorded without the name.

- [ ] **Step 3 (agent → OWNER): The SQL the migration will run**

Run (not replayed here; T1 Step 4 and T10 check the same): `git fetch origin && git status -sb | head -1` then `(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0007_bulletin_images:0008_invites_integrity --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//')`
**Expected:** the branch even with `origin/claude/slice-2-plan-4q33le` (the PR's code); exactly the lines of README step 3. Send them in a code block with:

> Third check: these are the lines of SQL the migration will run on the database when the PR merges, rendered from the PR's code without touching the database. In plain words: start one transaction; give up after 5 seconds if the invites table is busy (the old version then keeps running and we retry); any invite that would make someone an owner becomes an admin invite and is cancelled (normally there are none); then a check that stops everything if one email has two waiting invites in one church (your count was 0); then the old rule "one invite per church and email, ever" is replaced by "one waiting invite per church and email", so a person can be invited again after a cancelled or used invite; and from now on an invite can only make someone a member or an admin; note the new version; finish. No row is deleted and no column changes. Does that look right to you?

Record the owner's answer.

- [ ] **Step 4 (agent → OWNER): Ask to merge, then merge**

Send: "The backup is green, the counts are recorded and you have read the SQL. May I merge PR #<N> with a merge commit? Railway then runs the migration before the new server starts. Nothing in the app changes with this PR, so you can keep using it while it deploys; I will tell you when it is live, then ask for one more read-only query and a two-minute phone check." On a clear yes (not replayed):

```bash
gh pr merge <N> --merge -R <repo>
gh pr view <N> -R <repo> --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R <repo> --workflow ci.yml --branch main --commit "$(gh pr view <N> -R <repo> --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R <repo> --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both.

- [ ] **Step 5 (agent, then OWNER): The deploy and the after-deploy check (manual-verification items 4 and 6)**

About three minutes after the merge (not replayed):

```bash
curl -s <api>/health/ready; echo
curl -s <api>/openapi.json | python3 -c "import json,sys; p=json.load(sys.stdin)['paths']; print(sorted(k for k in p if k.startswith(('/members','/invites','/church/'))), sorted(p['/church']))"
for r in "GET /members" "PATCH /members/00000000-0000-0000-0000-000000000000" "DELETE /members/00000000-0000-0000-0000-000000000000" "GET /invites" "POST /invites" "DELETE /invites/00000000-0000-0000-0000-000000000000" "POST /church/transfer-ownership" "POST /church/leave" "DELETE /church"; do set -- $r; printf '%s %s ' "$1" "$2"; curl -s -o /dev/null -w '%{http_code}\n' -X "$1" -H 'Content-Type: application/json' -d '{}' "<api>$2"; done
```

**Expected:** `{"ok":true,"db":"ok"}` (in production this answers 503 `schema_behind` while the database is behind the release, so `ok` means `0008` is applied and the new release is live); `['/church/bulletin-settings', '/church/leave', '/church/liturgy-prompts', '/church/prayer-library', '/church/prayer-library/voice-profile-draft', '/church/transfer-ownership', '/invites', '/invites/accept', '/invites/preview', '/invites/{invite_id}', '/members', '/members/{user_id}'] ['delete', 'get', 'patch']`; `401` for each of the nine (the route exists and wants a sign-in). If `/openapi.json` still lacks the routes, wait a minute and retry; after ten minutes, ask the owner to open Railway → the API service → Deployments and read the newest deployment's status (a failed pre-deploy on the 5 s lock timeout or on 0008's refusal: the old server keeps serving and nothing is broken; read the log line with the owner, then Step R or a redeploy on the owner's yes). Then send, with README step 4's query in a code block, and step 2's query again:

> The new server is live. One more read-only check: in the SQL Editor, run the first query below; it should show 0008_invites_integrity, 1, 1 and 0 (the new rule is in place and the old one is gone). Then run the counting query from before again; the numbers should be the same as last time (or a few more invites if someone was invited meanwhile), except other_role_invites and old_constraint, which should now be 0. Also, if you have Railway open: the newest deployment's logs should include the lines "Running upgrade 0007_bulletin_images -> 0008_invites_integrity" and "0008_invites_integrity: 0 invite(s) with another role made admin and revoked" (or the number you saw before). What do you see?

Record the values. A version other than `0008_invites_integrity`, `pending_email_index` or `role_check` not `1`, `old_constraint` not `0`, or fewer invites than before: stop and look before anything else.

- [ ] **Step 6 (OWNER, then agent): Phone: the app as before (manual-verification item 5)**

> Last, a two-minute check on your phone: open the app as you usually do and pull down to reload it. Does it load, and does the builder open as before? Tap **Settings**: are the sections the same as before (Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, Account; People and Danger zone come with the next PR)? If you still have an invite link to your church that you sent someone and nobody has used yet, open it on the phone: does it say "You're already a member of {your church}." with an **Open** button? Tapping **Open** just opens your church and does not use up the link. If you have no such link, skip that part.

Record the answers (never the link). Anything other than "works as before": stop; it is a 6b-1 problem to fix (or revert, Step R) before 6b-2.

- [ ] **Step 7 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/6b1-t11-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 8 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it, `### Slice 6a-3b record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Slice 6b-1 record

Slice 6b-1 (the server side of People and the Danger zone: `GET /members`,
`PATCH` and `DELETE /members/{user_id}`, `GET`, `POST` and `DELETE /invites`,
`POST /church/transfer-ownership`, `POST /church/leave` and `DELETE /church`,
every write under the church-row lock with the caller's role re-read, and
the role rules in `usecases/role_policy.py`; no page uses them until 6b-2)
merged as PR #<N>, the first of slice 6b's two PRs (owner's 6b planning
answers of 2026-10-09). Production moved from `0007_bulletin_images` to
`0008_invites_integrity` (invites grant member or admin only; one waiting
invite per church and email). The steps follow `backend/migrations/README.md`
→ "Before 0008_invites_integrity", and the owner's check covered the
"(owner, before the 6b-1 merge)" and "(owner, after 6b-1)" items of
`docs/manual-verification.md` → "Slice 6b". No church id, email address,
invite code or link, token or database URL is recorded here.

| Step | Result | Date |
|---|---|---|
| 1. Backup | `db-backup` run <run URL>: success, artifact `db-backup` (<bytes> bytes, encrypted) | <date> |
| 2. Counts and integrity (SQL Editor, read-only) | version `0007_bulletin_images`; <n> invites, <n> pending email invites, 0 duplicate pending pairs, <n> with another role, old constraint 1; <n> churches, <n> without exactly one owner, <n> without an admin<; repairs: none / …> | <date> |
| 3. SQL preview | Rendered from the PR's code without a database: the README's lines (the role repair, the duplicate check, the constraint swapped for `uq_invites_pending_email`, `ck_invites_role`, under the 5 s lock timeout); read by the owner: <answer> | <date> |
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`; `/openapi.json` lists the new routes; signed out: 401 from each of the nine. <Railway log lines "Running upgrade 0007_bulletin_images -> 0008_invites_integrity" and "0008_invites_integrity: <n> invite(s) …" seen by the owner. / Not checked.> | <date> |
| 4. After the deploy (read-only) | `0008_invites_integrity`, index 1, check 1, old constraint 0; counts again: <unchanged / …> | <date> |
| 5. The app as before (phone: <phone and browser>) | <Loads; the builder opens; Settings unchanged; <an unused invite link opened as "already a member" / no unused link at hand>. / …> | <date> |
| Agent checks | Item 6: the routes served and 401 signed out (above). | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: 6b-2 (the People and Danger zone pages, migration `0009_memberships_one_owner`) | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye. Then (not replayed):

```bash
sed -n '/^### Slice 6b-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 6b-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|code='
sed -n '/^### Slice 6b-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '—'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 6b-1 record (backup, counts, SQL preview, merge, migration 0008)" -m "Records slice 6b-1 (PR #<N>): the backup, the read-only counts and
integrity check, the SQL preview before the merge, the merge and the deploy
of 0008_invites_integrity, the after-deploy check, and the owner's short
phone check that the app works as before. No church id, email address,
invite code or link, token or database URL is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 9 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 6b-1 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R <repo> --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 6b-1 record" \
  --body "Records slice 6b-1 (PR #<N>) in docs/ops-runbook.md → Slice 6b-1 record: the backup, the read-only counts and integrity check, the SQL preview, the merge and deploy of migration 0008_invites_integrity, and the owner's short phone check. No church id, email address or invite link is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R <repo> --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R <repo>`. Report: "Slice 6b-1 is live and recorded; <n> follow-ups. Next: 6b-2, the People and Danger zone pages."

- [ ] **Step R (only if the release must come out): Revert**

Code only; the schema stays at `0008_invites_integrity` (README "Reverting 6b-1": the code before 6b-1 creates no invite, so it runs on it unchanged). On the owner's yes for each outward command: a branch `claude/revert-6b1` from `origin/main`; `git revert -m 1 --no-commit <merge sha>`; then restore `backend/migrations/versions/0008_invites_integrity.py`, the `Invite` table arguments in `backend/db/models.py` and `pytest.ini`'s two filters from the merge commit (`git checkout <merge sha> -- backend/migrations/versions/0008_invites_integrity.py pytest.ini`, and the model's lines by hand), so Railway's `alembic upgrade head` still finds the database at head and `alembic check` stays clean; a commit "Revert slice 6b-1 (PR #<N>), keeping migration 0008" with the trailer; the backend suite; a PR, CI, and the merge on the owner's yes; record it in the record. Never `alembic downgrade` production for this.

Expected counts after this task: backend `2216 passed, 45 skipped` on `main`; frontend `952 passed` in 109 files. The records PR adds no test.

---

## Build notes

**How this plan was written (2026-10-09).** Each task's code was built and run in a throwaway worktree of `a75ebc6` (the branch head `072c374` plus the plan's skeleton commit; outside the repo directory; the repo's `.venv` as a symlink; a hard-linked copy of `frontend/node_modules`, since Turbopack's production build refuses a `node_modules` symlink that points outside the project), one commit per task; the directives were then generated from those commits by a script (a new file as **Create**, an addition at the end of a file as **Append**, every other change as **In … replace** with just enough whole-line context to occur once in the file as it stands at that point, changes three or fewer lines apart in one block), which also checked that applying each file's directives to the file before the commit gives the file after it. The Postgres runs used a throwaway local PostgreSQL 16 cluster (initialised under `/var/lib/postgresql`, never a real database, on a local port, `TEST_DATABASE_URL` a local throwaway URL), stopped and deleted afterwards. No package or variable was added. While building:
- **What S assumed and what exists.** Slices 1, 5b and 6a shipped every interface S lists (clarification 3), so 6b-1 creates no helper twice. Slice 1's accept already makes code-only invites single-use (clarification 4); nothing to fix.
- **The migration on both dialects.** The first version raised a Python `RuntimeError` on both; on Postgres the check could not appear in the owner's offline preview, so it became a `DO` block there (clarification 5). On SQLite the refusal named the churches in SQLite's stored hex form; it now prints them as UUIDs, as Postgres does. SQLite runs DDL outside a transaction, so the downgrade checks for duplicates before it changes anything.
- **The expression index.** On Postgres `alembic upgrade head`, `alembic check` ("No new upgrade operations detected."), `alembic downgrade base` and `alembic upgrade head` again all passed, CI's own sequence; on SQLite autogenerate skips the index with two warnings, now filtered by name (clarification 7).
- **What the new CHECK and the wider delete broke.** The full suite after T1's model found slice 1's three clamp tests storing `owner`/`foo` invites (clarification 8); after T4's repos, one onboarding test that deleted a church to keep a consumed invite live (clarification 11). `streamlit_tests` passed throughout.
- **An import cycle.** `church_admin` imports `members` at load, so `members` imports `require_admin_role` when it is called (clarification 3).
- **Flaky orderings caught while building.** Two invites made at the same instant tie on `created_at` (the order then falls to the random id), so the test that reads the list's order gives them different times; the members' order by name depends on the token's name, which `get_current_user` writes back to the user row, so the lifecycle API test compares the two admins as a set.
- **Mutation checks** (each change made by hand in the build worktree with every task applied, the named tests run, the change undone): no revocation of the removed person's invites → `2 failed, 110 passed` (`test_members_usecase.py`, `test_api_members.py`); no revocation of expired pending invites → `1 failed, 95 passed` (`test_members_usecase.py`, `test_api_invites_admin.py`); `DELETE /church` guarded by `require_church` → `1 failed, 14 passed` (`test_route_guards.py`, `test_api_church_lifecycle.py`); the delete revoking only unaccepted invites (the old filter) → `2 failed, 33 passed` (`test_churches_repo.py`, `test_church_lifecycle.py`); `check_leave` without its last-admin rule → `3 failed, 80 passed` (`test_role_policy.py`, `test_church_lifecycle.py`, `test_api_church_lifecycle.py`); `revoke_invite` without the lock and role re-read → `4 failed, 78 passed` (`test_members_usecase.py`); `GET /invites` without `no-store` → `1 failed, 13 passed` (`test_api_invites_admin.py`); `lock_church` without `FOR UPDATE` → `6 failed, 1 passed` (`test_people_postgres.py`, on Postgres).

**Replay of the finished plan (2026-10-09).** The directives of T1-T9 were applied in order by a replay script that parses each step's **Create**, **Append** and **In … replace** blocks and its `bash` blocks (each commit), runs every command on its "Run:" lines (T1-T9 and T10 Steps 1-3; `<local url>` a fresh database on the throwaway local PostgreSQL 16 cluster) and compares the output with the quoted **Expected** blocks, onto a fresh detached worktree of the branch (outside the repo directory and removed afterwards), with the repo's `.venv` (a symlink) and a hard-linked copy of `frontend/node_modules`:
- Baselines before T1, on the replay worktree: backend `1983 passed, 35 skipped`; Postgres `35 passed, 1983 deselected, 1 warning`; frontend `952 passed` in 109 files; typecheck 0, lint 0.
- All 75 directives applied (15 **Create**, 11 **Append**, 49 **In … replace**); every **In … replace** block occurred exactly once; all nine commit blocks ran, each commit with the trailer; afterwards the replayed `backend`, `frontend/src`, `docs/manual-verification.md` and `pytest.ini` were identical to the build worktree's.
- Every "see it fail" output, every count and every T10 Step 1-3 output above is quoted from the first replay (times as `<t>`); the plan as committed was then replayed once more onto another fresh worktree and fresh database and matched every quoted block but one: T10 Step 3's check of this plan for U+2028, U+2029, U+FFFE and U+FFFF found 4, because the command itself had been written with those characters instead of their `\u` escapes; the command now uses the escapes, and run again on the replayed tree with the committed plan it prints `0`. The migration ran up, down (refusing, then restoring) and up again on SQLite in T1's tests and on Postgres in T1's Postgres tests, and CI's own Alembic sequence (upgrade, check, downgrade base, upgrade) was run by hand on the throwaway cluster.
- Not run while planning: the pushes, the PR and CI, the merge, Railway's pre-deploy migration on production data, Vercel's deploy, and the owner's steps (T11).

## Spec coverage

| Owner answer or spec item | Task(s) and tests |
|---|---|
| Answer 1: 6b-1 is the server side with `0008_…`; the owner routine | T1-T9; T11 Steps 1-5 |
| Answer 2: no Streamlit work, no port or ledger, no `LegacySettingsNote`; `check_integrity.py` and its runbook kept | clarifications 1, 9, 10; T2; T1's README section |
| Answer 3: visibility (members see members with emails; admins invite, change roles, remove; the owner transfers and deletes) | T7 `test_a_member_reads_every_member_with_emails`, `test_member_cannot_change_role_or_remove`, `test_member_cannot_create_list_or_revoke_invites`, `test_admin_cannot_transfer_or_delete`; T3 every row |
| Answer 4: single-use by default, reusable for 7 days, optional email binding | T5 `test_an_invite_is_single_use_member_by_default_for_seven_days`, `test_a_bad_invite_is_refused_and_nothing_is_stored`; T7 `test_a_single_use_link_works_once_and_a_reusable_one_for_everyone` |
| Answer 5: removal revokes the removed person's links; the reusable flag | T5 `test_removing_a_member_keeps_their_services_and_revokes_every_invite_they_made`, `test_revoke_reusable_also_revokes_every_live_reusable_link_counting_each_once`; T7 the three "removal sticks" tests |
| Answer 6: no own role change; delete needs the exact name | T3; T6 `test_delete_needs_the_exact_name_after_trimming`; T7 `test_delete_needs_the_exact_name_and_leaves_everyone_without_the_church` |
| S API (routes, guards, errors, `no-store`, Idempotency-Key, the JSON body of `DELETE /church`, no 409 on members) | T7 every test; `test_route_guards.py` |
| S "Role policy" and its evaluation order; acceptance 2 | T3 `test_the_fixture_holds_exactly_the_51_reachable_states`, `test_every_row_has_its_outcome`; T5 and T6 the 404-before-policy cases |
| S "Invite semantics" (TTL, email rule, reusable with email, member conflict, pending duplicate, expired revoked, race, list filter, revoke, removal) | T4 the invites repo tests; T5 the invite tests; T7 `test_the_two_conflicts_have_their_codes_and_words`; T8 `test_two_invites_for_one_email_at_once_make_one`, `test_the_pending_email_index_refuses_a_second_insert_even_without_the_lock` |
| S "Transactions and locking" (one session, the lock, the role re-read, lost access as `no_church_access`, the transfer's order) | T5 and T6 the "lost access" and "row locked" tests; T4 `test_transfer_ownership_demotes_then_promotes`; T7 the late-guard tests; T8 every test |
| S "Repo changes" | T4 |
| S "Data and migrations" (`0006` = `0008`: repair, pre-check, index, CHECK, downgrade; models; compare) | T1 every 0008 test; CI's `alembic check` on Postgres |
| S "Church integrity runbook" | T1 README; T2 every test |
| S "Tenancy and data access" (ids looked up in this church; logs) | T5 `test_creating_an_invite_logs_ids_never_the_code_or_the_email`; T7 `test_codes_and_emails_never_reach_the_logs` and the isolation tests |
| S Testing → Postgres (the six races) | T8 (clarification 14) |
| S acceptance 1, 3-13, 21 (the server's half) | T1-T8; T11 for "production is at 0008" |
| The binding rules (no em dashes in server messages; no real ids, emails or URLs; migrations safe on production data; frozen Streamlit untouched; no network in tests; every write under the lock with the role re-read; Postgres tests for transfer, remove and the index) | Global Constraints; clarifications 5-7, 10, 14, 17; T10 Step 3; T11's record checks |

S items **not** in 6b-1: everything of the UX, the frontend and the manual checks 2-10 (6b-2); `memberships_one_owner` (6b-2, `0009_…`); the `streamlit_tests` port and ledger (dropped by answer 2).

## Follow-ups (not in 6b-1)

- 6b-2 builds on these routes: the pages, the Settings nav, the client's role meta and `useExitChurch`, and `0009_memberships_one_owner` (run the integrity check before it, README "Church integrity").
- `usecases.onboarding._clamp_role` can never fire once 0008 is applied; it stays as a harmless defense (clarification 8) and could go in a later clean-up.
- If an admin ever needs to see why an invite stopped working (revoked by a removal or a delete), a "revoked reason" column would say; not asked for.

## Owner questions

Your 6b planning answers of 2026-10-09 (all as recommended) and the earlier answers on roles, invites and the migration routine are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **How to run the integrity check before and after the merge** (clarification 9). The spec's check is a script run from a laptop with the database's address. This plan gives you the same check as one read-only query to paste into Supabase's SQL Editor (Task 11, step 2), which you already use for the counts; the script stays for anyone with the laptop setup. Recommended: the SQL Editor query.
2. **What to do if a church turns out to have no owner (or two, or no admin)** (Risks). It does not block this update, but in such a church nobody can transfer ownership or delete it, and its only admin cannot leave. If a count in step 2 is not 0, I will give you a second read-only query that names the church (in our chat only, never recorded), and recommend we fix it before the People page arrives (6b-2), choosing the owner with you, with the runbook's one-line repair after a fresh backup. Recommended: fix it before 6b-2, with your choice of owner.
3. **The phone check after the merge** (Task 11, step 6). This PR changes nothing you can see, so the check is two minutes: the app loads, the builder opens, Settings is unchanged, and (only if you happen to have one) an unused invite link still opens. Recommended: this short check, with the full People checks coming with 6b-2.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T10); the backup, one read-only query and the SQL to read, the merge on your yes, one more read-only query, a two-minute phone check, and the records PR (T11).

## Self-review

- **Coverage.** Every binding constraint has a home: 6b-1 as the server side with `0008_…`, the one-owner revision left to 6b-2 (clarifications 1, 2; T1-T9); Streamlit treated as unused with `check_integrity.py` kept (clarifications 1, 9, 10; T2); no em dashes in server messages (clarification 17; T10 Step 3 greps the added lines); no real ids, emails or URLs (tests use `@example.com`; commands use `<repo>`, `<api>`, `<app>`; the record's own grep, T11 Step 8); migrations safe on production data (the duplicate pre-check before the unique index, the CHECK after the repair, one transaction under the 5 s lock timeout, a working downgrade that refuses rather than half-runs; clarifications 5-7; T1's SQLite and Postgres tests); frozen Streamlit untouched (T10 Step 3's untouched check; clarification 10); no network in tests (Global Constraints); every write under the church-row lock with the role re-read (Layering rules; T5, T6, T7's lost-access tests); Postgres concurrency tests for transfer, remove and the invite unique index (T8). The second-to-last task opens a draft PR only on the owner's yes; the last runs the owner's routine one step at a time (backup, read-only counts and the duplicate pre-check in the SQL Editor, the SQL preview), merges only on a yes, checks production, runs a minimal phone check (6b-1 is server-only: the app loads, Settings unchanged, an unused invite link still opens if one exists) and inserts "### Slice 6b-1 record" before "## Backups", after "### Slice 6a-3b record".
- **Placeholders.** None in T1-T9's code, tests, commands or expected outputs; every expected output is quoted from the replay. The `<…>` left are T10 and T11's runtime values (`<N>`, `<repo>`, `<api>`, `<scratch>`, `<local url>`, times, the owner's answers), as in the earlier plans.
- **Consistency.** Names agree across tasks: `find_violations` (T2) is used by T6's and T8's tests; `role_policy.check_role_change`, `check_remove`, `check_leave`, `check_transfer`, `NOT_ADMIN`, `OWNER_ONLY` (T3) by T5, T6 and T8; `list_member_rows`, `get_member`, `count_owner_admins`, `is_member_email`, `transfer_ownership`, `insert_invite`, `list_active_invites`, `find_pending_email_invite`, `revoke_expired_email_invites`, `revoke_invites_created_by`, `revoke_reusable_invites`, `revoke_invite`, `soft_delete_church` (T4) by T5 and T6; `member_out`, `MEMBER_NOT_FOUND`, `clean_invite_email`, `create_invite`, `list_invites` (T5) by T6, T7 and T8; `MemberOut`, `MemberListOut` (T7 `routes/members.py`) by `routes/churches.py`. The counts in the table, each task's "Expected" and the PR line agree: `1983 → 2216`, `35 → 45`, frontend `952` in 109 unchanged.
- **Not verified while planning:** the pushes, the PR and CI (the Postgres tests and CI's Alembic sequence were run on a throwaway local PostgreSQL 16 instead of CI's 17), the merge, Railway's pre-deploy migration on production data, Vercel's deploy, and the owner's checks.
- **Judgement calls to watch in review:** the deterministic races instead of 20 barrier rounds (clarification 14); the pre-check as a `DO` block on Postgres (5); no separate role assertion (6); the SQL Editor query as the integrity check (9); the script reading only an exported `DATABASE_URL` (9); `pytest.ini`'s two warning filters (7); the lazy import of `require_admin_role` (3); `revoke_reusable` defaulting to false on the API while the page will check it by default (answer 5).
