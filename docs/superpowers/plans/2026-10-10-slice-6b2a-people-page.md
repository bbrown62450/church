# Slice 6b-2a: Settings → People (Invite Links, Members, Pending Invites) and the One-Owner Migration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first of slice 6b-2's two PRs (owner's 6b-2 planning answers of 2026-10-10, "all recommended"; binding): **Settings → People** and the one-owner migration. After it merges, every member of a church opens **Settings → People** (`/settings/people`, between Contacts and Account in the Settings nav) and sees everyone in the church with their email, their own row marked **You**, and each person's role. Owners and admins also see **Invite someone** above the list (a single-use link by default, or one "Reusable for 7 days", optionally for one email address; the new link with **Copy link** and, on phones, **Share…**), a menu on each row they may act on (**Make admin** or **Make member** at once; **Remove from church** after a confirmation that says which invite links stop working, with "Also revoke the reusable invite links" checked), and **Pending invites** below it (each live link with its role, type, expiry and maker, **Copy link** and **Revoke**). An admin demoted elsewhere is told so and the page turns read-only; someone removed elsewhere falls back to another church, as everywhere in the app. Migration **`0009_memberships_one_owner`** makes the database refuse a second owner in any church (a partial unique index); it refuses to run, naming the churches, if one already has two. Production moves from `0008_invites_integrity` to `0009_memberships_one_owner` through the owner's routine (backup, read-only counts, the SQL shown in full and marked read-only, the after-deploy check). No API change, no new package or variable; the frozen Streamlit app's files are untouched (one of its tests goes, see clarification 5). Tests never reach the network.

**Architecture:** Bottom up, backend first. T1: the revision, the `Membership` model's index, the README's "Before 0009_memberships_one_owner (slice 6b-2a)" (every query and the SQL preview pinned by tests on SQLite and Postgres), the head constants, the integrity test's two-owner case, and the deletion of the frozen app's members test whose transfer the index refuses. T2: the People rules (`lib/settings/people.ts`: names, initials, `memberActions` checked against 6b-1's 51-row shared role-policy fixture, the link's sentences, the expiry), `lib/clipboard.ts`, the type aliases and the test fixtures. T3: the People queries (`lib/queries/people.ts`: each hook handles a role refusal itself, as 6a's do), `ConfirmDialog` with a body and a pending label, `CopyLinkButton`, `InitialsAvatar`. T4: the page with Members (rows, the actions menu, the Remove dialog). T5: Invite someone (the form and the link panel) and Pending invites (rows, Copy link, Revoke). T6: People in the Settings nav. T7: the manual check items. T8: verification. T9: the owner's pre-merge routine for 0009, one step at a time. T10: the draft PR, the merge on the owner's yes, the after-deploy check, the phone check in a test church with a second Google account, the record.

**Tech Stack:** Python 3.11 (`.venv`), SQLAlchemy 2.1, Alembic 1.20, psycopg2, pytest; Next.js 16 (App Router, client components), React 19, TanStack Query 5, Base UI (shadcn components in `components/ui`), Tailwind 4, sonner, Vitest 3 with Testing Library and jsdom, ESLint, `tsc`.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md`, read with its two amendments, which are binding and win where the older text differs. **2026-10-09:** two PRs; Streamlit treated as unused (no compatibility work, no `streamlit_tests` port or ledger, no `LegacySettingsNote`), `check_integrity.py` and its runbook kept and run before the one-owner revision; visibility as designed (every member sees the list with emails; only owners and admins see pending invites, invite, change roles or remove; only the owner transfers or deletes); invites as designed (single-use by default, "Reusable for 7 days", optional email binding, Copy link, Share on phones); removal revokes the removed person's links, with "Also revoke the reusable links" checked by default; an admin can't change their own role, role changes apply without confirmation, leave, remove, transfer and delete confirm; the final Settings order Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, People, Account, Danger zone; no em dashes in user-facing copy ("Copied ✓" stays). **2026-10-10:** 6b-1 merged as PR #59 and production is at `0008_invites_integrity` with exactly one owner and at least one admin in every church; 6b-2 is two PRs, this is **6b-2a** (the People page, the People nav entry, `0009_memberships_one_owner` with its owner routine, the SQL shown in full and marked read-only); **6b-2b** has the Danger zone page, `useExitChurch`/`runChurchExit`, `markChurchExited`/`wasChurchExited` and the layout's exited-church check; 6b-2a's phone check is a real join in a test church with a second Google account the owner controls, then its removal. From S: "User experience" (Every page, §1 People, "Losing a role mid-session"), "Alembic revision `memberships_one_owner`", "Church integrity runbook", "Frontend changes" (the People parts: routes, components, pure helpers, queries), Testing (Frontend; the one-owner migration tests; Integrity's two-owner case), "Manual checks", "Risks", acceptance 2 (the client half), 12 (the one-owner half), 14, 16, 18 and 22 (the People half).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §3.4 and §3.5 (migrations: assert before a constraint, expand-only), §4.4 (queries), §4.8 (every page: skeletons, ErrorState with Retry, 44 px targets, confirm dialogs), §4.9 (Base UI).
- The model plans: `docs/superpowers/plans/2026-10-09-slice-6b1-people-backend.md` (its structure, the owner routine for 0008, its build notes and the "Slice 6b-1 record" lesson below), `docs/superpowers/plans/2026-10-08-slice-6a3b-prayers.md` and `docs/superpowers/plans/2026-10-08-slice-6a3a-prompts-rubric-bulletin.md` (a Settings page plan: Vitest with `renderWithProviders` and `installFakeApi` inside the Settings layout with a Toaster, the nav task, the phone check one step at a time). "Lessons carried" below maps their findings to this plan.
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `dd2e7f0` = `origin/main` `24828b1` (6b-1 merged as PR #59) plus the 6b-1 record `698c324` and the 6b-2 amendment `dd2e7f0`, then this plan's commits; 2026-10-10): backend `2235 passed, 46 skipped`; Postgres `46 passed, 2235 deselected`; frontend `952 passed` in 109 files; typecheck and lint clean; Alembic head `0008_invites_integrity` (8 revision files); 4 runbook owner markers. What exists from 6b-1 on `main`: `GET /members` (`MemberListOut`: `user_id`, `email`, `name` null when blank, `role`, `is_me`), `PATCH /members/{user_id}` (`RoleChangeIn`), `DELETE /members/{user_id}?revoke_reusable=` (`RemovedOut`: `revoked_invites`), `GET`/`POST /invites` (`InviteOut` with `code` and `created_by`, `Cache-Control: no-store`; `POST` takes an `Idempotency-Key`; 409 `invite_exists` and `conflict` with the spec's words), `DELETE /invites/{invite_id}` (`RevokedOut`), and their generated types in `frontend/src/lib/api/schema.d.ts` (no aliases yet in `types.ts`); `backend/tests/fixtures/shared/role_policy.json` (51 rows: `change_role` 22, `remove` 11, `leave` 7, `transfer` 11); `repos/integrity.py`, `scripts/check_integrity.py` and the README's "Church integrity (slice 6b)" with its step 3 for two owners; `repos.memberships.transfer_ownership` (demote, then promote). Frontend: `keys.members(id)` and `keys.invites(id)`, `useChurchMutation` (sets `meta.churchId`, so a `no_church_access` 403 reaches the `(church)` layout's fallback), `ConfirmDialog` (title, `description` string only, `pending` shows "Saving…"), `PendingButton`, `EmptyState`, `ErrorState`, `Skeleton`, `buildInviteUrl(code, origin = window.location.origin)` (slice 1, with its round-trip test), `isAdmin`, `roleLabel`, `useMeContext()`, `components/ui` `alert-dialog`, `avatar`, `badge`, `dropdown-menu`, `input`, `label`, `radio-group` (Base UI), and the Bulletin email dialog's native checkboxes (slice 5b-2). Missing or different: see clarification 6.
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch, the migration on SQLite and on a throwaway local Postgres 16 (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan. `<repo>` is the GitHub repository of this checkout's `origin` (owner/name), `<api>` the production API's address (Railway → the API service → Settings → Networking), `<app>` the production app's address, `<scratch>` the session's scratchpad path, `<N>` the PR number and `<local url>` a local, throwaway Postgres URL (host `localhost`); write each out literally when running a command, and never into a committed file.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -1`; the suite `.venv/bin/python -m pytest -q 2>&1 | tail -1`; the Postgres-only tests `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres <paths> 2>&1 | tail -1` (only where a local, throwaway Postgres is at hand; CI's `backend-postgres` job runs them on every push). Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`, the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`, and `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`. A time in an expected output is written `<t>`.
- The API does not change: `backend/api` and the generated `openapi.json` and `schema.d.ts` stay as they are (T8 checks that regenerating them changes nothing).
- One migration (T1, `0009_memberships_one_owner`, down from `0008_invites_integrity`); no new package, no new variable; no new `components/ui` file (clarification 6).
- Branch `claude/slice-2-plan-4q33le`, at `dd2e7f0` plus this plan's commits (the `WIP plan: …` commits and `Plan: slice 6b-2a (People page and migration 0009)`, and any later plan commit), then T1-T7. Stage files by name (`git add <paths>`, `git rm` for the one deletion); never `git add -A`; nothing under `.claude/` is staged.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R <repo>`, only on the owner's explicit yes, and only after T9's backup, counts and SQL preview.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 2235 → 2235 passed, 46 → 48 skipped; frontend 952 → 1007 in 109 → 113 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 11 and has no em dashes ("Copied ✓" keeps its check mark).
- No church id, email address, invite code or link, token, database URL or real person's name in any doc, commit, test or record. Tests use `@example.com` addresses, the fixtures' "Grace" and made-up names. Invite codes are never logged, by the server (6b-1) or by the app (nothing here logs; every People page test fails if any `console` call carries a fixture's invite code or `code=`).
- **SQL the owner must not run is shown in full and marked.** The SQL preview (T9 Step 3, README step 3) is shown whole, never shortened with "...", inside a code block, and the message says "Read only. Do not run this." before it (the "Slice 6b-1 record" lesson: a shortened preview was pasted and run, and Postgres refused it). The read-only queries the owner does run say "Read-only … Changes nothing." in their first line.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.
- **Tests never reach the network**: the backend suite's `_no_network` fixture refuses any socket except the local Postgres the `postgres` tests are given; the frontend tests stub `fetch` with `installFakeApi` (an unhandled request fails the test).
- The frozen Streamlit files (`app.py`, `streamlit_views/`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`) are not edited.

### How the file directives below read
As in the 6b-1, 6a-3a and 6a-3b plans: **Create `path`:** the block is the whole new file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file, as whole lines, and is replaced by the block after **with:** (a leading or trailing empty line in a block is part of it). Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. One file is deleted, with `git rm` on a "Run:" line (T1 Step 4); no file is moved.

### Baselines and counts
- Starting baselines: backend **2235 passed, 46 skipped**; Postgres **46 passed, 2235 deselected**; frontend **952 passed in 109 files**, typecheck and lint clean; Alembic head **`0008_invites_integrity`** (8 revision files; T1 adds the 9th); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed in the replay). A backend delta is the number of collected tests; a frontend delta counts tests (an `it.each` counts each case) and files.

  | After | Backend (delta) | Backend | Postgres job (local) | Frontend (delta) | Frontend |
  |---|---|---|---|---|---|
  | T1 | +4 passed, +2 skipped (`test_migrations.py`: four SQLite tests, two Postgres), -4 passed (`streamlit_tests/test_settings_members_invites.py` deleted); four test files edited | 2235 passed, 48 skipped | 48 passed, 2235 deselected | 0 | 952 in 109 files |
  | T2 | 0 | 2235 passed, 48 skipped | 48 passed | +23 (`people.test.ts` 19, `clipboard.test.tsx` 3, `urls.test.ts` 1), +2 files | 975 in 111 files |
  | T3 | 0 | 2235 passed, 48 skipped | 48 passed | +5 (`confirm-dialog.test.tsx` 2, `copy-link-button.test.tsx` 3), +1 file | 980 in 112 files |
  | T4 | 0 | 2235 passed, 48 skipped | 48 passed | +14 (`people-settings-page.test.tsx`), +1 file | 994 in 113 files |
  | T5 | 0 | 2235 passed, 48 skipped | 48 passed | +12 (`people-settings-page.test.tsx`) | 1006 in 113 files |
  | T6 | 0 | 2235 passed, 48 skipped | 48 passed | +1 (`settings-layout.test.tsx`: the People case) | 1007 in 113 files |
  | T7 | 0 (`docs/manual-verification.md` only) | 2235 passed, 48 skipped | 48 passed | 0 | 1007 in 113 files |

- CI `backend-postgres` goes from `46 passed, 2235 deselected` to `48 passed, 2235 deselected`.

### Layering and code rules (carried)
- Pages and components never call `apiFetch`: the hooks in `src/lib/queries/people.ts` use `useApi().church`, and every write goes through `useChurchMutation`, so a `no_church_access` 403 reaches the `(church)` layout's fallback (another church, "You no longer have access to {name}.").
- **A role refusal is the hook's** (6a's way, clarification 6a): a 403 without `details.reason` is toasted with the server's words and refetches the church profile (the role) and the member list, so the page re-renders for the role the user has now and they stay in the church. A 401 and a lost church are the app's and are not toasted again.
- `src/lib/settings/people.ts` is pure (no React, no fetch); it decides only what the page shows. The server enforces every rule (6b-1).
- User-supplied text (names, emails) renders as React text only. No other person's picture is loaded: avatars are initials.
- Writes are not optimistic: each puts the server's answer in the cache, then refetches (F §4.4). `GET /invites` is never cached as fresh (`staleTime: 0`): its codes are secrets and a revoked link must not linger. Once the role no longer allows it, the cached list is removed, and the Invite link ready panel closes when its invite leaves the list.
- **Migrations are safe on production data** (F §3.4): the owner pre-check runs before the unique index, in the same transaction, under the 5 s lock timeout, and refuses (changing nothing) rather than repairing: which owner stays is a person's choice. The downgrade works.
- Every control is at least 44 px tall on phones (F §4.8), inputs are `text-base md:text-sm` (the `Input` component's own classes) so iOS does not zoom, and nothing scrolls sideways at 375 px.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** is retired (branch `streamlit-frozen`, untouched); merges never reach it. The frozen files on `main` are not edited.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge; Railway's pre-deploy runs `alembic upgrade head`.
4. **The 6b-2 planning answers of 2026-10-10** ("all recommended"; binding; S's second amendment): (1) two PRs, this is **6b-2a**: the People page, the People nav entry, `0009_memberships_one_owner` with the owner routine (backup, before and after counts, the SQL shown in full and marked read-only, an after-deploy check); 6b-2b has the Danger zone; (2) the phone check is a real join in a test church: a single-use invite opened in a private window, a second Google account the owner controls signs in and joins, then the owner removes it; (3) 6b-2b's Delete check uses a throwaway church (not here).
5. **The 6b planning answers of 2026-10-09** (binding, carried): visibility, invites, removal revoking the removed person's links with the reusable box checked, no own role change, role changes without confirmation, remove and revoke confirm, the final Settings order, no em dashes.
6. **Earlier answers** (binding, carried): decision 5 (roles), decision 6 (invites), 2026-10-02's migration routine (backup, read-only counts, the SQL preview, one step at a time, results recorded without ids or emails), and 6a's "a role refusal turns the page read-only without leaving the church".
7. **The plan's two questions, answered 2026-10-10** ("all recommended"): delete `streamlit_tests/test_settings_members_invites.py` in T1 (clarification 5), and proper plurals and "as a member" / "as an admin" in the copy (clarification 11).

**Later, out of scope:** 6b-2b (the Danger zone page and its nav entry, `useExitChurch`/`runChurchExit`, `markChurchExited`/`wasChurchExited`, the `(church)` layout's exited-church check, `leaveBlock`, `deleteNameMatches`, the transfer, leave and delete hooks), slice 7.
## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items were put to the owner in "Questions for the owner"; both were answered on 2026-10-10 as recommended (clarifications 5 and 11).

1. **[owner-visible] What 6b-2a ships** (answer 1). `/settings/people` with Invite someone, Members and Pending invites; `CreateInviteForm`, `InviteLinkPanel`, `MembersList` (with `MemberRow`, the actions menu and `RemoveMemberDialog`), `PendingInvitesList` (with `InviteRow` and the revoke confirmation); `CopyLinkButton`, `InitialsAvatar`; `lib/clipboard.ts`; `lib/settings/people.ts` (`displayName`, `initials`, `memberActions`, `inviteSummary`, `formatDateTime`, `formatExpiry`, and two counts for the Remove dialog); the People hooks `useMembers`, `useChangeRole`, `useRemoveMember`, `useInvites`, `useCreateInvite`, `useRevokeInvite`; the People nav entry (nav after 6b-2a: Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, People, Account); migration `0009_memberships_one_owner` and its README routine; the manual check items. Not here (6b-2b): the Danger zone, its nav entry, `useExitChurch`, `markChurchExited`, the layout change, `leaveBlock`, `deleteNameMatches`, the transfer, leave and delete hooks. S's ledger and port are dropped (2026-10-09 answer 2).
2. **The revision's number and place.** S's `memberships_one_owner` is `0009_memberships_one_owner`, `down_revision = "0008_invites_integrity"` (the head on `main`). The head constants move with it: `test_api_app.SCHEMA_HEAD`, `test_schema_check.EXPECTED_HEAD` (and its test's name), the README's "Head is", and the version the README's 0005-0007 queries report on the Postgres test database (`test_services_postgres.py`). On SQLite a database stamped at the baseline now also lacks the index (`test_schema_check.BASELINE_DRIFT` gains `add_index uq_memberships_one_owner`). Postgres stores the predicate as `((role)::text = 'owner'::text)` (the test pins `pg_indexes`' text); `alembic check` compares it with the model cleanly (measured on Postgres 16 in the replay), so `env.py` needs no exception.
3. **The owner pre-check runs inside the migration on both dialects** (S "Upgrade" step 1), as `0008`'s duplicate check does: on Postgres a `DO` block that raises (so the owner's SQL preview shows it, and it runs in the upgrade's one transaction: a refusal changes nothing, the pre-deploy step fails and the previous release keeps serving); on SQLite the same words as a `RuntimeError`. The words: `0009_memberships_one_owner: {n} church(es) have more than one owner: {church ids}. Follow "Church integrity" in backend/migrations/README.md, then redeploy.` (church ids, sorted, as UUIDs; never an email; S had `one_owner:`). The check counts **every** church, soft-deleted ones too, because the index covers every row; README step 2's `churches_with_two_owners` counts the same. There is no automatic repair ("Church integrity" step 3 with the church, after a fresh backup). No data step, so the upgrade logs nothing of its own.
4. **The integrity check's two-owner test** (S Testing → Integrity: "with `uq_memberships_one_owner` dropped inside the test DB"). `test_integrity.test_two_owners_are_reported` drops the index in its own SQLite database before it makes a second owner; `find_violations` is unchanged (it still reports `owner_count` 0 and 2, for rows written by hand).
5. **[owner-visible] The frozen app's members test goes** (S "Compatibility → Streamlit tests"). `streamlit_tests/test_settings_members_invites.py::test_owner_only_transfer_and_delete` runs the frozen app's transfer, which promotes the new owner before it demotes the old one; with the index that first statement is refused, so the test fails (measured: `1 failed, 3 passed` once the model has the index). S says 6b deletes this file once its four checks have new-stack equivalents; 6b-1 shipped them (`test_api_members.py::test_member_cannot_change_role_or_remove` and `::test_owner_cannot_be_removed_even_by_self`, `test_api_invites_admin.py::test_member_cannot_create_list_or_revoke_invites` and `::test_admin_creates_single_use_invite`, `test_church_lifecycle.py::test_ownerless_sole_admin_cannot_leave` and `::test_transfer_swaps_roles_atomically`, `test_api_church_lifecycle.py::test_admin_cannot_transfer_or_delete`, `test_memberships_repo.py::test_remove_last_admin_is_rejected`) but kept the file, since its transfer still worked without the index. T1 deletes the file (four tests); the frozen app's own files are not touched, and the retired app's transfer, if anyone ran it, fails without changing data (S Risk 1). "Questions for the owner" 1, answered yes on 2026-10-10.
6. **What S assumed and what exists** (S "Assumed interfaces", "Frontend changes"). Slice 1, 5b, 6a and 6b-1 shipped most of it (see "Facts checked"). Where it differs:
   - a. **No `forbiddenIsRole` meta.** 6a-1 decided against it ("`handleAuthErrors` already leaves a role 403 alone; `useUpdateChurch`'s own `onError` toasts it and refetches the profile"), and 6a-2, 6a-3a, 6a-3b and 5b followed. 6b-2a does the same, so the app keeps one way: each People write's `onError` toasts a role 403 and invalidates `["church", id, "profile"]` **and** `["church", id, "members"]` (S "When a role 403 arrives … 6b adds `members`"); `useInvites` does the same inside its `queryFn` (S needed the meta on this query too). A `no_church_access` 403 is never toasted by the hooks: `useChurchMutation` and the query key already report it to the `(church)` layout. `handleAuthErrors` does not change.
   - b. **No checkbox component.** `components/ui` has no `checkbox.tsx`. `npx shadcn@latest view checkbox` reached the registry from this session on 2026-10-10, but generating one is not needed: the two checkboxes here are native `<input type="checkbox">` with `accent-primary` and a 44 px label, as the Bulletin email dialog's are (slice 5b-2). No new `components/ui` file and no registry dependency. Radio group, badge, avatar, alert dialog and dropdown menu exist (Base UI).
   - c. **`ConfirmDialog` takes only a description string**, and its pending button always says "Saving…". The Remove dialog needs a sentence that depends on data and a checkbox, and S's pending words are "Removing…" and "Revoking…". T3 adds two optional props: `children` (rendered under the description, above the buttons) and `pendingLabel`. Every existing caller is unchanged.
   - d. **Settings pages have no `PageHeader` of their own.** The Settings layout's `PageHeader` is "Settings" (h1); each page starts with an h2 (Contacts, Prayers). People does the same: an h2 "People" with S's caption, then h3 sections.
   - e. S's `useMe().user.id` is `useMeContext().user.id`; S's `src/lib/queries/people.ts` and the aliases in `types.ts` are as S says (`Member`, `MemberList`, `RoleChangeBody`, `MemberRemoved`, `Invite`, `InviteList`, `InviteCreator`, `InviteBody`, `InviteRevoked`).
   - f. `copyText`'s tests need `document`, so they run in the jsdom project (`clipboard.test.tsx`), like `use-keyboard-open.test.tsx`.
   - g. `buildInviteUrl` exists with S's signature and its round-trip test; T2 adds S's one case pinning `(code, origin)`.
7. **The People hooks in detail** (S "Queries and mutations"). `useMembers` (`GET /members`); `useInvites({enabled})` (`GET /invites`, `enabled` only for owners and admins, `staleTime: 0`; when `enabled` turns false, as after a role refusal once the profile says member, the cached list and its codes are removed; not at the refusal itself, since the page's still-enabled queries would fetch and be refused again until the new role arrives); `useChangeRole` (`PATCH`, the answer replaces the row in the cache, then the list refetches); `useRemoveMember` (`DELETE …?revoke_reusable=true|false`, the row leaves the cache, then members and invites refetch); `useCreateInvite` (`POST /invites` with a new `crypto.randomUUID()` `Idempotency-Key` per click, as S says; the new invite goes first in the cached list, then it refetches); `useRevokeInvite` (`DELETE /invites/{id}`, the row leaves the cache, then the list refetches). A 404 (the person or the link went elsewhere) is toasted with the server's words and refetches that list. A 409 or a 422 naming `email` or `reusable` on create is the form's, shown under the field, never toasted; any other failure is toasted.
8. **The Remove dialog** (S UX 1b). The body is S's: "{name} will lose access to {church}. Services they saved stay in the archive." Then, when the invites have loaded, "The {k} invite link(s) {name} created will stop working." (left out when k is 0), else "Any invite links {name} created will stop working."; then, when the invites have not loaded or someone else made a live reusable link, the box **checked**: "Also revoke the {r} reusable invite link(s)" ("Also revoke every reusable invite link" when unknown) with S's help line. The request sends `revoke_reusable=true` only when the box is shown and checked. Since 6b-1's build, the server also revokes any pending invite for the removed person's own email (plan review M1 there); those are invites to that person, so the dialog does not count them.
9. **Focus** (F §4.8). The link panel's **Copy link** takes focus when it opens (S), and **Done** returns focus to **Create invite link**. The panel also closes when its invite leaves the loaded list (revoked in Pending invites or by a removal); focus then follows the revoke or the removal to that section's heading. After a removal or a revoke the row is gone, so focus goes to its section's heading (`tabIndex={-1}`); a Cancel returns it to where it was. An inline error focuses its field (S).
10. **Copy link in a row** (S UX 1c: "same behavior as the panel"). Its screen reader name is "Copy link for {who}" and becomes "Copied ✓" while that label shows. A row has no visible link, so when copying is refused the row shows its link in a read-only box under it, focused and selected, and the toast says "Couldn't copy. The link is selected; copy it from there."
11. **[owner-visible] Every new user-facing string** (S's words, no em dashes; the two wording changes are "Questions for the owner" 2, answered yes on 2026-10-10). Page: "People", "Everyone in {church} can see this list.". Invite someone: "Invite someone", "Role", "Member" with "Can build, save and email services, and edit hymns.", "Admin" with "Can also change church settings, invite people and manage members.", "Email (optional)" with "Only the Google account with this email will be able to use the link.", "Reusable for 7 days" with "Let several people join with the same link. Otherwise the link works once." (while an email is typed: "A link for one email address works once."), "Create invite link" ("Creating…"), "Invite link created." (screen readers). The panel: "Invite link ready", "Invite link", "Copy link", "Copied ✓", "Link copied", "Couldn't copy. The link is selected; copy it from there.", "Share…" (sharing "Join {church}" and "You're invited to plan worship with {church}."), "Done", and one of "Anyone who opens this link can join {church} as a member. It works once and expires {date, time}." / "Only {email} can use this link to join {church} as an admin. It works once and expires {date, time}." / "Anyone with this link can join {church} as a member until {date, time}. Share it only with people you trust." ("a member" or "an admin"; S wrote "a {member|admin}"). Members: "Members ({n})", "You", "Owner", "Admin", "Member", "Only admins can change roles or remove people. To add someone, ask an admin for an invite link.", "Actions for {name}" (screen readers), "Make admin", "Make member", "Remove from church", "Remove {name}?", "{name} will lose access to {church}. Services they saved stay in the archive.", "The 1 invite link {name} created will stop working." / "The {k} invite links {name} created will stop working." / "Any invite links {name} created will stop working.", "Also revoke the 1 reusable invite link" / "Also revoke the {r} reusable invite links" / "Also revoke every reusable invite link", "Anyone with a reusable link, including {name}, can use it to rejoin until it expires. You can create a new link for everyone else.", "Remove member" ("Removing…"). Pending invites: "Pending invites ({n})", "Anyone with the link", "Single use", "Reusable", "Expires in 7 days" / "in 1 day" / "in 5 hours" / "in less than an hour" (the full date and time as the tooltip), " · Created by {name or email}", " · Created by a former member", "Copy link for {who}" and "Revoke the invite for {who}" (screen readers), "Revoke", "Revoke this invite?", "The link will stop working. People who already joined stay in the church.", "Revoke invite" ("Revoking…"), "No pending invites", "Create an invite link above to add someone to {church}.". Nav: "People". Dates read "Oct 17, 2026, 3:00 PM" in the device's time zone. From the server (6b-1's, shown as they come): "There's already a pending invite for {email}. Copy its link below or revoke it first.", "{email} is already a member of this church.", "Enter a valid email address.", "A link for one email address works once.", "Only church admins can do this.", "The owner can't be removed.", "Member not found.", "Invite not found.". For the migration's reader: clarification 3's words.
12. **Share** (S UX 1a). **Share…** shows only where `navigator.share` exists; it shares S's title, text and link; a cancelled share (`AbortError`) does nothing, as S says, and so does any other failure: the link stays on screen with **Copy link** beside it, so a second message would add nothing.
13. **Docs.** T1 adds the README's "Before 0009_memberships_one_owner (slice 6b-2a)" (backup; one read-only query with the owner counts; the SQL preview in full, marked "Read only. Do not run this.", pinned by a test that also refuses "..." in that step; the after-deploy check, which also answers before 0009 is applied; reverting) right before "Church integrity (slice 6b)", whose step 3 now says 0009 refuses over two owners. T7 adds items 7-17 to `docs/manual-verification.md` → "## Slice 6b" (no new `##` heading, so `test_slice1_docs.py`'s pin is unchanged). The runbook record is T10's (`### Slice 6b-2a record` before `## Backups`, after `### Slice 6b-1 record`).
14. **The final tasks' order** (the planning request): T9 is the owner's pre-merge routine for 0009 (backup, counts, the SQL preview), run on the branch's code before the PR is opened; T10 opens the draft PR, waits for CI, merges on the owner's yes, then the after-deploy check, the phone check and the record. If more than a day passes between T9's backup and the merge, or anything merges to `main` meanwhile, T10 takes a fresh backup and runs T9's counts again first.
15. **Deviations from S** (each the lean or the safer choice): the role refusal handled per hook, not by a cache-wide meta (6a); native checkboxes, no generated component (6b); `ConfirmDialog`'s two optional props (6c); an h2 instead of a `PageHeader` (6d); proper plurals and "an admin" in the copy (11); a row's link shown in a box when copying is refused (10); the pre-check's prefix `0009_memberships_one_owner:` (3); the frozen app's members test deleted here rather than in 6b-1 (5).

### Risks
- **A church with two owners in production** (only a hand-written row could make one: the app's transfer demotes first, and the retired Streamlit app is not running). T9's step 2 counts them; the migration refuses to run over them in any case, safely (the previous release keeps serving), and "Church integrity" step 3 repairs them with the owner. The slice 6b-1 record found every church with exactly one owner on 2026-10-10.
- **A church with no owner** does not block 0009 (the index only refuses a second owner) but would leave nobody to transfer or delete it in 6b-2b. T9 Step 2 counts it as a stop (the 6b-1 gate), repaired with "Church integrity" step 4 before the merge.
- **The lock timeout.** Creating the index takes a short lock on `memberships`; another connection holding one for more than 5 s fails the deploy safely; redeploy.
- **Invite links in Vercel's request logs** (S Risk 6): the phone check opens a real link; it is single-use and is used at once, and the record never holds it.
- **The phone check changes a test church only.** Every People action that changes something runs in one of the owner's test churches, never the real one; the real church is only read (item 11).
- **A Vercel preview builds links from its own address** (S Risk 7): previews are build checks only; the phone check uses production.

### Lessons carried (the 6b-1, 6a-3a and 6a-3b plans and their reviews and records)
- **Show SQL that is only for reading in full, and say not to run it** (the "Slice 6b-1 record": a chat copy of the preview shortened with "..." was pasted into the SQL Editor). The README's step 3 says "Read only. Do not run this." before the block; a test refuses "..." and "…" in that step and pins the block; T9 Step 3 sends the whole block with those words.
- The SQL preview is pinned twice: the test renders it offline and compares it with a constant, and another test compares the README's block with the same constant (3a, 6b-1).
- The after-deploy query also answers before the migration is applied, so "not yet" is an answer, not an error (3a plan review M9); the Postgres test runs it at both versions.
- The owner's queries are run by tests on Postgres, read from the README itself (3a, 6b-1), so the owner never pastes a query no test ran.
- The revert restores T1's whole commit, not only the revision and the model (6b-1 plan review I1); T10 Step R lists the paths and the README says the same.
- A role 403 is toasted and refetches the role without leaving the church; a lost church is the app's (6a-1, 6a-3b); both are tested on the page.
- Confirmations keep their subject while they close and ignore Cancel while the write runs; focus never drops to the page when the row is gone (5b-1, 6a-3b).
- No real ids, emails or URLs in committed files; placeholders in commands (`<repo>`, `<api>`, `<app>`).

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/migrations/versions/0009_memberships_one_owner.py` | the revision | T1 |
| `frontend/src/lib/settings/people.ts` (+ `people.test.ts`) | names, initials, `memberActions`, the link's sentences, the expiry, the Remove dialog's counts | T2 |
| `frontend/src/lib/clipboard.ts` (+ `clipboard.test.tsx`) | `copyText` | T2 |
| `frontend/src/lib/queries/people.ts` | the six People hooks and `inviteFieldError` | T3 |
| `frontend/src/components/app/copy-link-button.tsx` (+ `copy-link-button.test.tsx`), `frontend/src/components/app/initials-avatar.tsx` | Copy link; the initials avatar | T3 |
| `frontend/src/app/(signed-in)/(church)/settings/people/page.tsx`, `frontend/src/components/settings/people/people-settings-page.tsx`, `members-list.tsx` (+ `people-settings-page.test.tsx`) | the route, the page, Members | T4 |
| `frontend/src/components/settings/people/create-invite-form.tsx`, `invite-link-panel.tsx`, `pending-invites-list.tsx` | Invite someone, the link panel, Pending invites | T5 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/db/models.py` | `Membership`: `uq_memberships_one_owner` | T1 |
| `backend/migrations/README.md` | the head, the revision's row, "Before 0009_memberships_one_owner (slice 6b-2a)", "Church integrity" step 3 | T1 |
| `backend/tests/test_migrations.py`, `test_schema_check.py`, `test_api_app.py`, `test_services_postgres.py`, `test_integrity.py` | the 0009 tests; the head; the baseline drift; the two-owner case | T1 |
| `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/urls.test.ts` | the People aliases; `member`, `memberList`, `invite`, `inviteList`, `PEOPLE`; one `buildInviteUrl` case | T2 |
| `frontend/src/components/app/confirm-dialog.tsx` (+ `confirm-dialog.test.tsx`) | `children` and `pendingLabel` | T3 |
| `frontend/src/components/settings/people/people-settings-page.tsx`, `people-settings-page.test.tsx` | the invite sections for owners and admins | T5 |
| `frontend/src/components/settings/sections.ts`, `settings-layout.test.tsx` | People between Contacts and Account | T6 |
| `docs/manual-verification.md` | "## Slice 6b": items 7-17 | T7 |
| `docs/ops-runbook.md` | "### Slice 6b-2a record" (the records PR, after the merge) | T10 |

**Deleted:** `streamlit_tests/test_settings_members_invites.py` (T1, clarification 5).

**Counts in the PR:** 35 paths: 17 added (this plan and the sixteen new code and test files above), 17 modified (the fifteen code, test and doc paths above, and two that ride along until merged: `docs/ops-runbook.md` with the 6b-1 record and the 6b spec with its 6b-2 amendment; the runbook's own T10 change goes in the records PR) and 1 deleted. **Untouched:** everything under `backend/api`, `backend/usecases`, `backend/repos`, `backend/scripts`, `backend/migrations/env.py`, every other migration, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`, `frontend/src/lib/queries/client.ts`, `frontend/src/components/ui`, `frontend/src/app/(signed-in)/(church)/layout.tsx`, `requirements*.txt`, `frontend/package*.json`, `.github`, `pytest.ini`, `app.py`, `streamlit_views`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`.

**Task order and review batch:** T1 → T7, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T8 verifies; T9 takes the owner through the backup, the counts and the SQL preview; T10 opens the draft PR on the owner's yes, merges on the owner's yes, checks production, runs the phone check and writes the record.

---
## The migration (T1)

### Task 1: Migration `0009_memberships_one_owner`, the model, and the owner's steps in the README (S "Alembic revision `memberships_one_owner`", "Church integrity runbook", Testing → Migrations and Integrity; answer 1; clarifications 2-5, 13)

**Files:**
- Create: `backend/migrations/versions/0009_memberships_one_owner.py`
- Modify: `backend/db/models.py`, `backend/migrations/README.md`, `backend/tests/test_migrations.py`, `backend/tests/test_schema_check.py`, `backend/tests/test_api_app.py`, `backend/tests/test_services_postgres.py`, `backend/tests/test_integrity.py`
- Delete: `streamlit_tests/test_settings_members_invites.py`

The head moves to `0009_memberships_one_owner`. On SQLite (every test database): the refusal over two owners (naming the church, changing nothing) until the extra owner is made an admin, the index (read from `sqlite_master`) refusing a second owner in a church while another church keeps its own, the downgrade dropping only the index, the offline SQL equal to `PREVIEW_0009`, and the README's step 3 equal to it too, marked read-only and never shortened. On Postgres: the same upgrade (a soft-deleted church with two owners refuses it too), the index's definition, the downgrade and the upgrade again, and the owner's two read-only queries before and after the upgrade. The integrity check's two-owner test drops the index first; the frozen app's members test, whose transfer the index refuses, is deleted.

- [ ] **Step 1: Write the failing tests**

**Append to `backend/tests/test_migrations.py`:**

````python


# --- Slice 6b-2a: 0009_memberships_one_owner (6b spec, "Data and migrations"; owner's 6b-2 planning answers) ---

# What `alembic upgrade 0008_invites_integrity:0009_memberships_one_owner --sql` prints on Postgres,
# comments, blank lines and trailing spaces left out: the preview the owner reads before the
# merge (backend/migrations/README.md, "Before 0009_memberships_one_owner", step 3).
PREVIEW_0009 = [
    "BEGIN;",
    "SET LOCAL lock_timeout = '5s';",
    "SET LOCAL statement_timeout = '60s';",
    "DO $$",
    "DECLARE",
    "  hits integer;",
    "  church_ids text;",
    "BEGIN",
    "  SELECT count(*), string_agg(church_id::text, ', ' ORDER BY church_id::text)",
    "    INTO hits, church_ids",
    "    FROM (SELECT church_id FROM memberships",
    "           WHERE role = 'owner'",
    "           GROUP BY church_id HAVING count(*) > 1) AS owners;",
    "  IF hits > 0 THEN",
    "    RAISE EXCEPTION '0009_memberships_one_owner: % church(es) have more than one owner: %. "
    "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy.', hits, church_ids;",
    "  END IF;",
    "END $$;",
    "CREATE UNIQUE INDEX uq_memberships_one_owner ON memberships (church_id) WHERE role = 'owner';",
    "UPDATE alembic_version SET version_num='0009_memberships_one_owner' "
    "WHERE alembic_version.version_num = '0008_invites_integrity';",
    "COMMIT;",
]


def _membership_row(conn, church_id, user_id, role) -> None:
    """A membership inserted with plain SQL, as any client of the table could."""
    hexed = conn.dialect.name == "sqlite"
    conn.execute(sa.text("INSERT INTO memberships (church_id, user_id, role, created_at) "
                         "VALUES (:church, :user, :role, :created)"),
                 {"church": church_id.hex if hexed else church_id, "user": user_id.hex if hexed else user_id,
                  "role": role, "created": T9_NOW})


def _user_row(conn, email: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    conn.execute(_t9_users.insert().values(id=user_id, email=email, created_at=T9_NOW))
    return user_id


def _demote_extra_owners(conn, church_id, keep) -> None:
    """Church integrity step 3, with the ids filled in (the agent does this in the chat only)."""
    hexed = conn.dialect.name == "sqlite"
    conn.execute(sa.text("UPDATE memberships SET role = 'admin' "
                         "WHERE church_id = :church AND role = 'owner' AND user_id <> :keep"),
                 {"church": church_id.hex if hexed else church_id, "keep": keep.hex if hexed else keep})


def test_0009_refuses_two_owners_then_allows_one_owner_per_church(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0008_invites_integrity")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            owner, church_id = _seed_owner_and_church(conn)
            second = _user_row(conn, "second@example.com")
            _membership_row(conn, church_id, owner, "owner")
            _membership_row(conn, church_id, second, "owner")                  # 0008 still allows it
            _membership_row(conn, church_id, _user_row(conn, "m@example.com"), "member")
        with pytest.raises(RuntimeError) as refused:
            _alembic(sqlite_url, "upgrade", "0009_memberships_one_owner")
        assert _version(sqlite_url) == "0008_invites_integrity"
        with engine.begin() as conn:
            _demote_extra_owners(conn, church_id, keep=owner)
        _alembic(sqlite_url, "upgrade", "0009_memberships_one_owner")
        with engine.begin() as conn:
            index_sql = conn.execute(sa.text(
                "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'uq_memberships_one_owner'")).scalar_one()
            other_church = uuid.uuid4()
            conn.execute(_t9_churches.insert().values(
                id=other_church, name="Hope", timezone="America/New_York", settings={}, created_at=T9_NOW))
            _membership_row(conn, other_church, owner, "owner")                # one owner in another church
            _membership_row(conn, other_church, second, "admin")
        with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
            _membership_row(conn, church_id, _user_row(conn, "third@example.com"), "owner")
        with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
            conn.execute(sa.text("UPDATE memberships SET role = 'owner' WHERE church_id = :c AND user_id = :u"),
                         {"c": other_church.hex, "u": second.hex})
    finally:
        engine.dispose()
    assert str(refused.value) == (
        f"0009_memberships_one_owner: 1 church(es) have more than one owner: {church_id}. "
        "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy.")
    assert index_sql == "CREATE UNIQUE INDEX uq_memberships_one_owner ON memberships (church_id) WHERE role = 'owner'"
    assert _version(sqlite_url) == "0009_memberships_one_owner"


def test_0009_downgrade_drops_only_the_index(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0008_invites_integrity")
    before = _tables_snapshot(sqlite_url)
    _alembic(sqlite_url, "upgrade", "0009_memberships_one_owner")
    _alembic(sqlite_url, "downgrade", "0008_invites_integrity")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            gone = conn.execute(sa.text(
                "SELECT count(*) FROM sqlite_master WHERE name = 'uq_memberships_one_owner'")).scalar_one()
    finally:
        engine.dispose()
    assert gone == 0
    assert _tables_snapshot(sqlite_url) == before
    assert _version(sqlite_url) == "0008_invites_integrity"


def test_offline_sql_for_0009_is_the_owner_check_and_one_index_under_the_timeouts():
    cfg = alembic_config(url="postgresql://preview@localhost:1/preview", configure_logger=False)
    cfg.output_buffer = buffer = io.StringIO()
    command.upgrade(cfg, "0008_invites_integrity:0009_memberships_one_owner", sql=True)
    lines = [line.rstrip() for line in buffer.getvalue().splitlines() if line.strip() and not line.startswith("--")]
    assert lines == PREVIEW_0009


def test_the_readme_shows_the_0009_preview_exactly_and_in_full():
    """The owner reads backend/migrations/README.md → "Before 0009_memberships_one_owner",
    step 3, against the agent's rendering: both must be PREVIEW_0009, nothing shortened,
    and the step says it is for reading only (the slice 6b-1 record's lesson)."""
    section = _readme().split("\n## Before 0009_memberships_one_owner (slice 6b-2a)\n", 1)[1]
    step = section.split("\n### Step 3: Read the SQL the upgrade will run\n", 1)[1].split("\n### ", 1)[0]
    block = "BEGIN;" + step.split("\n```\nBEGIN;", 1)[1].split("\n```", 1)[0]   # the bare fence
    assert block.splitlines() == PREVIEW_0009
    assert "**Read only. Do not run this.**" in step
    assert "..." not in step and "…" not in step


def _readme_0009_sql(n: int) -> str:
    """The n-th ```sql block of README "Before 0009_memberships_one_owner": 0 is step 2's
    counts, 1 step 4's after-deploy check."""
    section = _readme().split("\n## Before 0009_memberships_one_owner (slice 6b-2a)\n", 1)[1]
    return re.findall(r"```sql\n(.*?)```", section, re.S)[n]


@pytest.mark.postgres
def test_0009_on_postgres_refuses_two_owners_then_creates_the_index_and_downgrades(pg_admin_url):
    """The same upgrade on Postgres: the DO block refuses a church with two
    owners (a soft-deleted one too) and changes nothing; after the runbook's
    step 3 the partial unique index exists and refuses a second owner; the
    downgrade drops it; the upgrade runs again."""
    with throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        _alembic(sandbox.role_url, "upgrade", "0008_invites_integrity")
        engine = _pg_engine(sandbox.role_url)
        try:
            with engine.begin() as conn:
                owner, church_id = _seed_owner_and_church(conn)
                second = _user_row(conn, "second@example.com")
                _membership_row(conn, church_id, owner, "owner")
                _membership_row(conn, church_id, second, "owner")
                conn.execute(text("UPDATE churches SET deleted_at = now() WHERE id = :c"), {"c": church_id})
            with pytest.raises(sa.exc.DBAPIError) as refused:
                _alembic(sandbox.role_url, "upgrade", "0009_memberships_one_owner")
            assert _version(sandbox.role_url) == "0008_invites_integrity"
            with engine.begin() as conn:
                _demote_extra_owners(conn, church_id, keep=owner)
            _alembic(sandbox.role_url, "upgrade", "0009_memberships_one_owner")
            with engine.begin() as conn:
                index = conn.execute(text(
                    "SELECT indexdef FROM pg_indexes WHERE indexname = 'uq_memberships_one_owner'")).scalar_one()
            with pytest.raises(sa.exc.IntegrityError), engine.begin() as conn:
                conn.execute(text("UPDATE memberships SET role = 'owner' WHERE church_id = :c AND user_id = :u"),
                             {"c": church_id, "u": second})
            _alembic(sandbox.role_url, "downgrade", "0008_invites_integrity")
            with engine.begin() as conn:
                dropped = conn.execute(text(
                    "SELECT count(*) FROM pg_indexes WHERE indexname = 'uq_memberships_one_owner'")).scalar_one()
            _alembic(sandbox.role_url, "upgrade", "0009_memberships_one_owner")
            again = _version(sandbox.role_url)
        finally:
            engine.dispose()
    message = str(refused.value.orig).splitlines()[0]
    assert message == (
        f"0009_memberships_one_owner: 1 church(es) have more than one owner: {church_id}. "
        "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy.")
    assert index == ("CREATE UNIQUE INDEX uq_memberships_one_owner ON public.memberships USING btree (church_id) "
                     "WHERE ((role)::text = 'owner'::text)")
    assert (dropped, again) == (0, "0009_memberships_one_owner")


@pytest.mark.postgres
def test_the_owner_s_read_only_queries_around_0009(pg_admin_url):
    """README "Before 0009_memberships_one_owner": step 2's counts before and
    after the upgrade, and step 4's check (which also answers before 0009 is
    applied)."""
    with throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        _alembic(sandbox.role_url, "upgrade", "0008_invites_integrity")
        engine = _pg_engine(sandbox.role_url)
        try:
            with engine.begin() as conn:
                owner, church_id = _seed_owner_and_church(conn)
                _membership_row(conn, church_id, owner, "owner")
                _membership_row(conn, church_id, _user_row(conn, "a@example.com"), "admin")
                _membership_row(conn, church_id, _user_row(conn, "m@example.com"), "member")
                hope = uuid.uuid4()
                conn.execute(text("INSERT INTO churches (id, name, timezone, settings, created_at, deleted_at) "
                                  "VALUES (:id, 'Hope', 'UTC', '{}', now(), now())"), {"id": hope})
                _membership_row(conn, hope, owner, "owner")
            with engine.connect() as conn:
                before = dict(conn.execute(text(_readme_0009_sql(0))).mappings().one())
                check_before = dict(conn.execute(text(_readme_0009_sql(1))).mappings().one())
            _alembic(sandbox.role_url, "upgrade", "0009_memberships_one_owner")
            with engine.connect() as conn:
                after = dict(conn.execute(text(_readme_0009_sql(0))).mappings().one())
                check_after = dict(conn.execute(text(_readme_0009_sql(1))).mappings().one())
        finally:
            engine.dispose()
    assert before == {"version": "0008_invites_integrity", "churches": 1, "deleted_churches": 1, "memberships": 4,
                      "owners": 2, "churches_with_two_owners": 0, "churches_without_one_owner": 0,
                      "churches_without_admin": 0, "one_owner_index": 0}
    assert check_before == {"version": "0008_invites_integrity", "one_owner_index": 0}
    assert after == {**before, "version": "0009_memberships_one_owner", "one_owner_index": 1}
    assert check_after == {"version": "0009_memberships_one_owner", "one_owner_index": 1}
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
EXPECTED_HEAD = "0008_invites_integrity"
````

**with:**

````python
EXPECTED_HEAD = "0009_memberships_one_owner"
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
# so its new uq_invites_pending_email is not listed here; Postgres lists it).
````

**with:**

````python
# so its new uq_invites_pending_email is not listed here; Postgres lists it),
# then 0009's index (slice 6b-2a).
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
    "add_index ix_services_church_date",
````

**with:**

````python
    "add_index ix_services_church_date",
    "add_index uq_memberships_one_owner",
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_head_is_0008_invites_integrity():
````

**with:**

````python
def test_head_is_0009_memberships_one_owner():
````

**In `backend/tests/test_schema_check.py`, replace:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_to_0008_changes(tmp_path):
````

**with:**

````python
def test_schema_diff_at_baseline_lists_exactly_the_0004_to_0009_changes(tmp_path):
````

**In `backend/tests/test_api_app.py`, replace:**

````python
SCHEMA_HEAD = "0008_invites_integrity"
````

**with:**

````python
SCHEMA_HEAD = "0009_memberships_one_owner"
````

**In `backend/tests/test_services_postgres.py`, replace:**

````python
    # test database is at head (0008_invites_integrity since slice 6b-1).
    assert counts == {"version": "0008_invites_integrity", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0008_invites_integrity", "new_columns": 2, "new_index": 1}
````

**with:**

````python
    # test database is at head (0009_memberships_one_owner since slice 6b-2a).
    assert counts == {"version": "0009_memberships_one_owner", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0009_memberships_one_owner", "new_columns": 2, "new_index": 1}
````

**In `backend/tests/test_services_postgres.py`, replace:**

````python
    assert counts == {"version": "0008_invites_integrity", "services": 3, "churches": 2}
    assert applied == {"version": "0008_invites_integrity", "new_column": 1, "with_bulletin": 1}
````

**with:**

````python
    assert counts == {"version": "0009_memberships_one_owner", "services": 3, "churches": 2}
    assert applied == {"version": "0009_memberships_one_owner", "new_column": 1, "with_bulletin": 1}
````

**In `backend/tests/test_services_postgres.py`, replace:**

````python
    assert counts == {"version": "0008_invites_integrity", "services": 2, "with_bulletin": 1}
    assert applied == {"version": "0008_invites_integrity", "row_security": True, "open_grants": 0, "pictures": 1}
````

**with:**

````python
    assert counts == {"version": "0009_memberships_one_owner", "services": 2, "with_bulletin": 1}
    assert applied == {"version": "0009_memberships_one_owner", "row_security": True, "open_grants": 0, "pictures": 1}
````

**In `backend/tests/test_integrity.py`, replace:**

````python
    church, _ = grace
    _set_roles(church, "owner", where_role="admin")
````

**with:**

````python
    church, _ = grace
    with session_scope() as s:   # a row from before 0009 (or written by hand with the index gone)
        s.execute(text("DROP INDEX uq_memberships_one_owner"))
    _set_roles(church, "owner", where_role="admin")
````

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_integrity.py 2>&1 | tail -1` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres backend/tests/test_migrations.py backend/tests/test_services_postgres.py 2>&1 | tail -1`
**Expected:** on SQLite, the head constants (`test_api_app.py`, `test_schema_check.py`), the baseline drift without the index, the four 0009 tests (no such revision; the README has no 0009 section) and the integrity test (no index to drop yet); on a local Postgres, the two 0009 tests and the three README-query tests of `test_services_postgres.py` (they expect the head's version):
```
16 failed, 78 passed, 12 skipped in <t>s
```
```
5 failed, 12 passed, 43 deselected in <t>s
```

- [ ] **Step 3: The revision, the model, the README**

The revision refuses over two owners (a `DO` block on Postgres, a `RuntimeError` on SQLite, the same words), then creates the partial unique index. The model gains the same index, so `alembic check` stays clean. The README gains the owner's steps before "Church integrity", whose step 3 now names 0009.

**Create `backend/migrations/versions/0009_memberships_one_owner.py`:**

````python
"""One owner per church: the partial unique index uq_memberships_one_owner (slice 6b-2a)

6b spec, "Data and migrations" (its memberships_one_owner; the owner's 6b-2
planning answers of 2026-10-10 number it 0009 and ship it with the People
page). Expand-only (F §3.4): no column changes, no data changes.

Upgrade, in order:
1. Owner pre-check: if any church (soft-deleted ones too: the index covers
   every row) has more than one owner, stop with the runbook message, naming
   the church ids. Which owner stays is a person's decision, so there is no
   automatic repair. On Postgres it is a DO block (so the owner's SQL preview
   shows it and it runs in the upgrade's one transaction); on SQLite a
   RuntimeError with the same words.
2. Create the unique index uq_memberships_one_owner on
   memberships (church_id) WHERE role = 'owner': the database refuses a
   second owner. The API keeps exactly one (only a transfer moves ownership,
   demote first, then promote; usecases/church_admin.py).

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and
statement_timeout '60s') first, and everything runs in one transaction, so
a refusal changes nothing and the previous release keeps serving.

Downgrade: drop uq_memberships_one_owner. Nothing else changes.

Revision ID: 0009_memberships_one_owner
Revises: 0008_invites_integrity
Create Date: 2026-10-10
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0009_memberships_one_owner"
down_revision = "0008_invites_integrity"
branch_labels = None
depends_on = None

ONE_OWNER = "role = 'owner'"
OWNERS_MESSAGE = (
    "0009_memberships_one_owner: {churches} church(es) have more than one owner: {ids}. "
    "Follow \"Church integrity\" in backend/migrations/README.md, then redeploy."
)

# The churches with more than one owner, one row each.
EXTRA_OWNERS_SQL = """\
SELECT church_id FROM memberships
           WHERE role = 'owner'
           GROUP BY church_id HAVING count(*) > 1"""

# Step 1 on Postgres: the same refusal inside the migration's transaction.
EXTRA_OWNERS_CHECK_PG = """\
DO $$
DECLARE
  hits integer;
  church_ids text;
BEGIN
  SELECT count(*), string_agg(church_id::text, ', ' ORDER BY church_id::text)
    INTO hits, church_ids
    FROM (""" + EXTRA_OWNERS_SQL + """) AS owners;
  IF hits > 0 THEN
    RAISE EXCEPTION '0009_memberships_one_owner: % church(es) have more than one owner: %. Follow "Church integrity" in backend/migrations/README.md, then redeploy.', hits, church_ids;
  END IF;
END $$"""


def upgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute(EXTRA_OWNERS_CHECK_PG)
    else:
        rows = op.get_bind().execute(sa.text(EXTRA_OWNERS_SQL)).all()
        if rows:
            ids = ", ".join(sorted(str(uuid.UUID(str(row[0]))) for row in rows))   # SQLite keeps hex
            raise RuntimeError(OWNERS_MESSAGE.format(churches=len(rows), ids=ids))
    op.create_index(
        "uq_memberships_one_owner", "memberships", ["church_id"], unique=True,
        postgresql_where=sa.text(ONE_OWNER), sqlite_where=sa.text(ONE_OWNER))


def downgrade() -> None:
    op.drop_index("uq_memberships_one_owner", table_name="memberships")
````

**In `backend/db/models.py`, replace:**

````python
        Index("ix_memberships_user_id", "user_id"),
````

**with:**

````python
        Index("ix_memberships_user_id", "user_id"),
        # Revision 0009_memberships_one_owner (slice 6b-2a): at most one owner
        # per church. Ownership moves only by a transfer, which demotes the
        # owner before it promotes the new one (repos.memberships.transfer_ownership).
        Index(
            "uq_memberships_one_owner", "church_id", unique=True,
            postgresql_where=sa.text("role = 'owner'"), sqlite_where=sa.text("role = 'owner'"),
        ),
````

**In `backend/migrations/README.md`, replace:**

````markdown
  `NNNN_short_slug.py`. Head is `0008_invites_integrity`.
````

**with:**

````markdown
  `NNNN_short_slug.py`. Head is `0009_memberships_one_owner`.
````

**In `backend/migrations/README.md`, replace:**

````markdown
| `0008_invites_integrity` | Slice 6b-1: an invite whose role is neither `member` nor `admin` becomes an `admin` invite and is revoked; then, unless two pending invites of one church share an email in any capitalization (it refuses, naming the churches: "Church integrity" below), the unique constraint `uq_invites_church_email` is replaced by the partial unique index `uq_invites_pending_email` on `(church_id, lower(email))` for pending email invites, and the check `ck_invites_role` (`member` or `admin`) is added. No column changes. Before it reaches production: "Before 0008_invites_integrity" below. |
````

**with:**

````markdown
| `0008_invites_integrity` | Slice 6b-1: an invite whose role is neither `member` nor `admin` becomes an `admin` invite and is revoked; then, unless two pending invites of one church share an email in any capitalization (it refuses, naming the churches: "Church integrity" below), the unique constraint `uq_invites_church_email` is replaced by the partial unique index `uq_invites_pending_email` on `(church_id, lower(email))` for pending email invites, and the check `ck_invites_role` (`member` or `admin`) is added. No column changes. Before it reaches production: "Before 0008_invites_integrity" below. |
| `0009_memberships_one_owner` | Slice 6b-2a: unless a church has more than one owner (it refuses, naming the churches: "Church integrity" below), the partial unique index `uq_memberships_one_owner` on `memberships (church_id)` `WHERE role = 'owner'`: the database refuses a second owner. No column or data changes. Before it reaches production: "Before 0009_memberships_one_owner" below. |
````

**In `backend/migrations/README.md`, replace:**

````markdown

## Church integrity (slice 6b)
````

**with:**

````markdown

## Before 0009_memberships_one_owner (slice 6b-2a)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0009_memberships_one_owner` when slice 6b-2a (Settings → People: invite
links, the member list, roles and removal) merges. First, as the owner
decided on 2026-10-10 (6b-2 planning answer 1, the same routine as 0008): a
backup, one read-only query that counts the churches' owners, and a look at
the SQL; after the deploy, one read-only check. One step at a time. Nothing
here changes data. The agent guides the owner and records the results in
`docs/ops-runbook.md` → "Slice 6b-2a record", never with an email address,
a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL and the artifact's size.

### Step 2: Count the churches' owners (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run (it
only reads):

```sql
-- Read-only: the churches' owners before 0009. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM churches WHERE deleted_at IS NULL) AS churches,
       (SELECT count(*) FROM churches WHERE deleted_at IS NOT NULL) AS deleted_churches,
       (SELECT count(*) FROM memberships) AS memberships,
       (SELECT count(*) FROM memberships WHERE role = 'owner') AS owners,
       (SELECT count(*) FROM (SELECT 1 FROM memberships WHERE role = 'owner'
                               GROUP BY church_id HAVING count(*) > 1) AS d)
         AS churches_with_two_owners,
       (SELECT count(*) FROM churches c
         WHERE c.deleted_at IS NULL
           AND (SELECT count(*) FROM memberships m
                 WHERE m.church_id = c.id AND m.role = 'owner') <> 1) AS churches_without_one_owner,
       (SELECT count(*) FROM churches c
         WHERE c.deleted_at IS NULL
           AND NOT EXISTS (SELECT 1 FROM memberships m
                            WHERE m.church_id = c.id AND m.role IN ('owner', 'admin')))
         AS churches_without_admin,
       (SELECT count(*) FROM pg_indexes
         WHERE schemaname = 'public' AND indexname = 'uq_memberships_one_owner') AS one_owner_index;
```

One row. Expected before the merge:

- `version` is `0008_invites_integrity` (anything else: stop);
- `churches` the churches in use and `deleted_churches` the deleted ones;
  `memberships` every person in every church; `owners` the owner rows
  (normally one per church, deleted churches included);
- `churches_with_two_owners` is `0`. It counts deleted churches too,
  because the new index covers every row. Anything else: stop. The
  upgrade would refuse (safely: the previous release keeps serving);
  agree with the church who keeps ownership and follow "Church integrity"
  step 3 below with the agent first;
- `churches_without_one_owner` and `churches_without_admin` are `0` (the
  gate from slice 6b-1: the index only refuses a second owner, so it
  would not notice a church with none). Anything else: stop and repair
  it with the agent ("Church integrity" step 4) before the merge;
- `one_owner_index` is `0` (the index does not exist yet).

### Step 3: Read the SQL the upgrade will run

**Read only. Do not run this.** It is the SQL Railway runs when the PR
merges, shown here so the owner can read it; pasting it into the SQL
Editor would change the database. The agent renders it from the PR's code
without connecting to any database (from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0008_invites_integrity:0009_memberships_one_owner --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//'
```

Expected, exactly and in full (`backend/tests/test_migrations.py` pins it;
when the agent shows it in the chat it is the whole block, never shortened):

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
DO $$
DECLARE
  hits integer;
  church_ids text;
BEGIN
  SELECT count(*), string_agg(church_id::text, ', ' ORDER BY church_id::text)
    INTO hits, church_ids
    FROM (SELECT church_id FROM memberships
           WHERE role = 'owner'
           GROUP BY church_id HAVING count(*) > 1) AS owners;
  IF hits > 0 THEN
    RAISE EXCEPTION '0009_memberships_one_owner: % church(es) have more than one owner: %. Follow "Church integrity" in backend/migrations/README.md, then redeploy.', hits, church_ids;
  END IF;
END $$;
CREATE UNIQUE INDEX uq_memberships_one_owner ON memberships (church_id) WHERE role = 'owner';
UPDATE alembic_version SET version_num='0009_memberships_one_owner' WHERE alembic_version.version_num = '0008_invites_integrity';
COMMIT;
```

In one transaction: a check that stops everything if any church has more
than one owner (your count was 0); then the new rule that a church can have
at most one owner; note the new version; finish. No row is changed or
deleted and no column changes. If another connection holds a lock on
`memberships` for more than 5 s, the deploy fails and the previous release
keeps serving; run the deploy again.

### Step 4: After the deploy (read-only)

SQL Editor (it only reads):

```sql
-- Read-only: is 0009 applied? Changes nothing.
-- Before 0009 is applied it still runs: 0008_invites_integrity, 0.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM pg_indexes
         WHERE schemaname = 'public' AND indexname = 'uq_memberships_one_owner') AS one_owner_index;
```

Expected: `0009_memberships_one_owner`, `1`. `0008_invites_integrity`, `0`
means the deploy has not applied 0009 yet: wait a minute and run it again.
Then step 2's query again: the same counts as before, except `version`
`0009_memberships_one_owner` and `one_owner_index` `1` (or more
`memberships` and `churches`, by the people and churches added since).

### Reverting 6b-2a

The schema stays at `0009_memberships_one_owner`: the code before 6b-2a
never makes a second owner (slice 6b-1's transfer demotes the owner before
it promotes the new one), so it runs on it unchanged. Revert the merge
commit, then, in the same PR, restore from the merge commit every file of
6b-2a's first commit ("Migration 0009_memberships_one_owner: …"), not only
the revision: the `Membership` model, this README and the tests that know
the head or the index, and keep the frozen app's transfer test deleted
(it promotes before it demotes, which the index refuses). Then Railway's
`alembic upgrade head` still finds the database at head, `alembic check`
stays clean, and the backend suite passes. From the repo root:

```bash
git checkout <merge sha> -- backend/migrations/versions/0009_memberships_one_owner.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py backend/tests/test_integrity.py
git rm -q -f streamlit_tests/test_settings_members_invites.py
```

Run the backend suite before the revert's PR opens; it must pass. Never
`alembic downgrade` production for this.

## Church integrity (slice 6b)
````

**In `backend/migrations/README.md`, replace:**

````markdown
3. **More than one owner** in a church (`owner_count` with a count above 1):
````

**with:**

````markdown
3. **More than one owner** in a church (`owner_count` with a count above 1;
   `0009_memberships_one_owner` refuses to run over it):
````

- [ ] **Step 4: The frozen app's members test, then delete it (clarification 5)**

With the index in the model, the frozen app's transfer (promote first, then demote) is refused, so its test fails; its four checks have had new-stack equivalents since 6b-1.

Run: `.venv/bin/python -m pytest -q streamlit_tests/test_settings_members_invites.py 2>&1 | tail -1` then `git rm -q streamlit_tests/test_settings_members_invites.py && git status --short streamlit_tests`
**Expected:**
```
1 failed, 3 passed in <t>s
```
```
D  streamlit_tests/test_settings_members_invites.py
```

- [ ] **Step 5: See them pass, the suite, Postgres, and the SQL preview**

Run: `.venv/bin/python -m pytest -q backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_integrity.py 2>&1 | tail -1` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres backend/tests/test_migrations.py backend/tests/test_services_postgres.py backend/tests/test_integrity.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q 2>&1 | tail -1` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres 2>&1 | tail -1` then `(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0008_invites_integrity:0009_memberships_one_owner --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//')`
**Expected:** all pass; the suite: four 0009 tests in, the frozen app's four out; Postgres: two more; the preview is exactly README step 3's block:
```
94 passed, 12 skipped in <t>s
```
```
18 passed, 52 deselected in <t>s
```
```
2235 passed, 48 skipped in <t>s
```
```
48 passed, 2235 deselected, 1 warning in <t>s
```
```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
DO $$
DECLARE
  hits integer;
  church_ids text;
BEGIN
  SELECT count(*), string_agg(church_id::text, ', ' ORDER BY church_id::text)
    INTO hits, church_ids
    FROM (SELECT church_id FROM memberships
           WHERE role = 'owner'
           GROUP BY church_id HAVING count(*) > 1) AS owners;
  IF hits > 0 THEN
    RAISE EXCEPTION '0009_memberships_one_owner: % church(es) have more than one owner: %. Follow "Church integrity" in backend/migrations/README.md, then redeploy.', hits, church_ids;
  END IF;
END $$;
CREATE UNIQUE INDEX uq_memberships_one_owner ON memberships (church_id) WHERE role = 'owner';
UPDATE alembic_version SET version_num='0009_memberships_one_owner' WHERE alembic_version.version_num = '0008_invites_integrity';
COMMIT;
```

- [ ] **Step 6: Commit**

```bash
git add backend/migrations/versions/0009_memberships_one_owner.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py backend/tests/test_integrity.py
git commit -q -m "Migration 0009_memberships_one_owner: at most one owner per church" -m "The partial unique index uq_memberships_one_owner on memberships (church_id)
WHERE role = 'owner', after a check that refuses (naming the churches,
changing nothing) when a church already has two owners: a DO block on
Postgres, a RuntimeError on SQLite. The Membership model gains the index.
backend/migrations/README.md gains \"Before 0009_memberships_one_owner\":
the backup, one read-only query, the SQL in full marked read-only, the
after-deploy check and the revert. The head constants and the baseline
drift move; the integrity check's two-owner test drops the index first;
the frozen app's members test, whose transfer the index refuses, is
deleted (its checks have had new-stack equivalents since slice 6b-1)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2235 passed, 48 skipped`; Postgres `48 passed`; frontend `952 passed` in 109 files.

## The People page (T2-T6)

### Task 2: The People rules, `copyText`, the types and the fixtures (S "Pure helpers", Testing → Frontend unit; acceptance 2's client half; clarifications 6e-6g, 8, 11)

**Files:**
- Create: `frontend/src/lib/settings/people.ts`, `frontend/src/lib/settings/people.test.ts`, `frontend/src/lib/clipboard.ts`, `frontend/src/lib/clipboard.test.tsx`
- Modify: `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/urls.test.ts`

`memberActions` is run against every change_role and remove row of `backend/tests/fixtures/shared/role_policy.json`, grouped by (actor role, target) into S's 11 pairs, with S's mapping: an `allow` row offers its role (the `noop` one never), two `forbidden` rows offer none, the remove row decides `canRemove`. The names, initials, the three link sentences, the date and the expiry in days, hours or less than an hour (the unit chosen after rounding, so 23.5 hours reads "in 1 day"), and the Remove dialog's two counts are pinned. `copyText` is pinned in jsdom: the Clipboard API, the textarea fallback when it is refused (the textarea removed again), and `false` without throwing when both fail. One `buildInviteUrl` case pins `(code, origin)`.

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  InviteAccepted,
````

**with:**

````ts
  Invite,
  InviteAccepted,
  InviteList,
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  LiturgySection,
````

**with:**

````ts
  LiturgySection,
  Member,
  MemberList,
````

**Append to `frontend/src/test/fixtures/index.ts`:**

````ts

// --- slice 6b-2a: Settings → People -------------------------------------------------------------------------

/** The people of Grace in the People tests: Pat Pastor is `USER_ID` (the viewer of `me()`). */
export const PEOPLE = {
  olive: "a0000000-0000-4000-8000-000000000001",
  ann: "a0000000-0000-4000-8000-000000000002",
  mo: "a0000000-0000-4000-8000-000000000003",
  sam: "a0000000-0000-4000-8000-000000000004",
} as const;

/** One member of Grace: Mo Member unless overridden. */
export function member(overrides: Partial<Member> = {}): Member {
  return { user_id: PEOPLE.mo, email: "mo@example.com", name: "Mo Member", role: "member", is_me: false, ...overrides };
}

const ROLE_ORDER: Record<Member["role"], number> = { owner: 0, admin: 1, member: 2 };

/**
 * `GET /members` as Pat (`USER_ID`) sees it with `myRole`: Olive Owner (unless
 * Pat is the owner), Ann Admin, Mo Member, sam@example.com (no name) and Pat,
 * in the server's order (owner, admins, members; each by name, else email).
 */
export function memberList(myRole: Member["role"] = "admin"): MemberList {
  const people: Member[] = [
    member({ user_id: PEOPLE.ann, email: "ann@example.com", name: "Ann Admin", role: "admin" }),
    member(),
    member({ user_id: PEOPLE.sam, email: "sam@example.com", name: null }),
    member({ user_id: USER_ID, email: "pat@example.com", name: "Pat Pastor", role: myRole, is_me: true }),
  ];
  if (myRole !== "owner") {
    people.push(member({ user_id: PEOPLE.olive, email: "olive@example.com", name: "Olive Owner", role: "owner" }));
  }
  const key = (m: Member) => (m.name?.trim() || m.email).toLowerCase();
  return { items: people.sort((a, b) => ROLE_ORDER[a.role] - ROLE_ORDER[b.role] || key(a).localeCompare(key(b))) };
}

/**
 * One live invite: a single-use member link for anyone, made by Olive a
 * minute ago, expiring in seven days less that minute (times are relative to
 * now, so its row reads "Expires in 7 days"), unless overridden.
 */
export function invite(overrides: Partial<Invite> = {}): Invite {
  const created = Date.now() - 60_000;
  return {
    id: "b0000000-0000-4000-8000-000000000001",
    code: "abc",
    email: null,
    role: "member",
    reusable: false,
    created_at: new Date(created).toISOString(),
    expires_at: new Date(created + 7 * 24 * 60 * 60 * 1000).toISOString(),
    created_by: { user_id: PEOPLE.olive, name: "Olive Owner", email: "olive@example.com" },
    ...overrides,
  };
}

/** `GET /invites`: these invites (none by default). */
export function inviteList(items: Invite[] = []): InviteList {
  return { items };
}
````

**Create `frontend/src/lib/settings/people.test.ts`:**

````ts
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import type { Church, Member } from "@/lib/api/types";
import { invite, member, PEOPLE } from "@/test/fixtures";

import {
  displayName,
  formatDateTime,
  formatExpiry,
  initials,
  inviteSummary,
  invitesCreatedBy,
  memberActions,
  otherReusableInvites,
} from "./people";

type PolicyRow = {
  action: "change_role" | "remove" | "leave" | "transfer";
  actor_role: Church["role"];
  target?: "self" | Member["role"];
  new_role?: "member" | "admin";
  expected: string;
};

const POLICY: { rows: PolicyRow[] } = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/role_policy.json", import.meta.url), "utf-8"),
);

/** The fixture's change_role and remove rows, grouped by (actor role, target): 11 pairs. */
function pairs(): Map<string, PolicyRow[]> {
  const grouped = new Map<string, PolicyRow[]>();
  for (const row of POLICY.rows.filter((r) => r.action === "change_role" || r.action === "remove")) {
    const key = `${row.actor_role}/${row.target}`;
    grouped.set(key, [...(grouped.get(key) ?? []), row]);
  }
  return grouped;
}

describe("memberActions mirrors the server's role policy (6b spec Testing → Frontend; slice 6b-2a)", () => {
  it("covers the 11 (actor, target) pairs of the shared fixture's change_role and remove rows", () => {
    expect([...pairs().keys()].sort()).toEqual([
      "admin/admin", "admin/member", "admin/owner", "admin/self",
      "member/admin", "member/member", "member/owner", "member/self",
      "owner/admin", "owner/member", "owner/self",
    ]);
  });

  it.each([...pairs().entries()])("offers what the server allows: %s", (_key, rows) => {
    const actorRole = rows[0].actor_role;
    const target = rows[0].target!;
    const actor = { id: "a", role: actorRole };
    const targetRow = member(target === "self" ? { user_id: "a", role: actorRole } : { user_id: "t", role: target });
    const changes = rows.filter((r) => r.action === "change_role");
    const removal = rows.filter((r) => r.action === "remove");
    expect(changes).toHaveLength(2);
    expect(removal).toHaveLength(1);

    const allowed = changes.filter((r) => r.expected === "allow");
    const got = memberActions(actor, targetRow);
    if (allowed.length === 1) {
      expect(changes.filter((r) => r.expected === "noop")).toHaveLength(1);
      expect(got.changeRoleTo).toBe(allowed[0].new_role);
    } else {
      expect(changes.map((r) => r.expected)).toEqual(["forbidden", "forbidden"]);
      expect(got.changeRoleTo).toBeNull();
    }
    expect(got.canRemove).toBe(removal[0].expected === "allow");
    expect(["allow", "forbidden"]).toContain(removal[0].expected);
  });
});

describe("the People page's names and sentences (slice 6b-2a)", () => {
  it("names a person by their name, trimmed, else their email", () => {
    expect(displayName(member())).toBe("Mo Member");
    expect(displayName(member({ name: "  Mo  " }))).toBe("Mo");
    expect(displayName(member({ name: null }))).toBe("mo@example.com");
    expect(displayName(member({ name: "   " }))).toBe("mo@example.com");
  });

  it("gives up to two initials: first and last word, else the email's first letter", () => {
    expect(initials(member())).toBe("MM");
    expect(initials(member({ name: "mary ann  jones " }))).toBe("MJ");
    expect(initials(member({ name: "Cher" }))).toBe("C");
    expect(initials(member({ name: null, email: "sam@example.com" }))).toBe("S");
    expect(initials(member({ name: "Émile Zola" }))).toBe("ÉZ");
  });

  it("says who can use a link, for what role and until when, in three ways", () => {
    const at = (iso: string) => `[${iso}]`;
    const expires_at = "2026-10-17T15:00:00Z";
    expect(inviteSummary({ email: null, role: "member", reusable: false, expires_at }, "Grace", at)).toBe(
      "Anyone who opens this link can join Grace as a member. It works once and expires [2026-10-17T15:00:00Z].",
    );
    expect(inviteSummary({ email: "b@example.com", role: "admin", reusable: false, expires_at }, "Grace", at)).toBe(
      "Only b@example.com can use this link to join Grace as an admin. It works once and expires [2026-10-17T15:00:00Z].",
    );
    expect(inviteSummary({ email: null, role: "admin", reusable: true, expires_at }, "Grace", at)).toBe(
      "Anyone with this link can join Grace as an admin until [2026-10-17T15:00:00Z]. Share it only with people you trust.",
    );
  });

  it("writes a date and time plainly, and nothing for an unreadable value", () => {
    expect(formatDateTime("2026-10-17T15:00:00Z", { timeZone: "America/New_York" })).toBe("Oct 17, 2026, 11:00 AM");
    expect(formatDateTime("not a time")).toBe("");
  });

  it("says when an invite expires in days, hours or less than an hour", () => {
    const now = new Date("2026-10-10T12:00:00Z");
    const zone = { timeZone: "UTC" };
    expect(formatExpiry("2026-10-17T11:59:00Z", now, zone)).toEqual({ relative: "in 7 days", full: "Oct 17, 2026, 11:59 AM" });
    expect(formatExpiry("2026-10-11T13:00:00Z", now, zone).relative).toBe("in 1 day");
    expect(formatExpiry("2026-10-10T17:10:00Z", now, zone).relative).toBe("in 5 hours");
    expect(formatExpiry("2026-10-10T13:00:00Z", now, zone).relative).toBe("in 1 hour");
    expect(formatExpiry("2026-10-10T12:59:00Z", now, zone).relative).toBe("in less than an hour");
    expect(formatExpiry("2026-10-10T11:00:00Z", now, zone).relative).toBe("in less than an hour");
  });

  it("chooses the unit after rounding, so 23.5 hours or more reads in 1 day", () => {
    const now = new Date("2026-10-10T12:00:00Z");
    expect(formatExpiry("2026-10-11T11:30:00Z", now).relative).toBe("in 1 day");
    expect(formatExpiry("2026-10-11T11:59:00Z", now).relative).toBe("in 1 day");
    expect(formatExpiry("2026-10-11T11:20:00Z", now).relative).toBe("in 23 hours");
  });

  it("counts the invites a person made, and the reusable links others made", () => {
    const mine = { user_id: PEOPLE.ann, name: "Ann Admin", email: "ann@example.com" };
    const invites = [
      invite({ id: "1", created_by: mine }),
      invite({ id: "2", created_by: mine, reusable: true }),
      invite({ id: "3", reusable: true }),
      invite({ id: "4", reusable: true, created_by: null }),
      invite({ id: "5" }),
    ];
    expect(invitesCreatedBy(invites, PEOPLE.ann)).toBe(2);
    expect(otherReusableInvites(invites, PEOPLE.ann)).toBe(2);
    expect(invitesCreatedBy([], PEOPLE.ann)).toBe(0);
  });
});
````

**Create `frontend/src/lib/clipboard.test.tsx`:**

````tsx
/** `copyText` (slice 6b-2a): the Clipboard API, the textarea fallback, and false when both fail. */
import { afterEach, describe, expect, it, vi } from "vitest";

import { copyText } from "./clipboard";

const realExecCommand = document.execCommand;

afterEach(() => {
  vi.unstubAllGlobals();
  document.execCommand = realExecCommand;
});

function stubClipboard(writeText: (text: string) => Promise<void>) {
  vi.stubGlobal("navigator", { ...navigator, clipboard: { writeText: vi.fn(writeText) } });
  return navigator.clipboard.writeText as ReturnType<typeof vi.fn>;
}

describe("copyText (slice 6b-2a)", () => {
  it("copies with the Clipboard API", async () => {
    const writeText = stubClipboard(async () => {});
    document.execCommand = vi.fn(() => true);
    expect(await copyText("https://app.example/join?code=abc")).toBe(true);
    expect(writeText).toHaveBeenCalledWith("https://app.example/join?code=abc");
    expect(document.execCommand).not.toHaveBeenCalled();
  });

  it("falls back to a hidden textarea when the Clipboard API refuses, and removes it again", async () => {
    stubClipboard(async () => {
      throw new DOMException("Not allowed", "NotAllowedError");
    });
    let copied = "";
    document.execCommand = vi.fn((command: string) => {
      copied = document.querySelector("textarea")?.value ?? "";
      return command === "copy";
    });
    expect(await copyText("the link")).toBe(true);
    expect(document.execCommand).toHaveBeenCalledWith("copy");
    expect(copied).toBe("the link");
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("says false, without throwing, when both ways fail", async () => {
    vi.stubGlobal("navigator", { ...navigator, clipboard: undefined });
    document.execCommand = vi.fn(() => false);
    expect(await copyText("the link")).toBe(false);
    document.execCommand = vi.fn(() => {
      throw new Error("unsupported");
    });
    expect(await copyText("the link")).toBe(false);
    expect(document.querySelector("textarea")).toBeNull();
  });
});
````

**In `frontend/src/lib/urls.test.ts`, replace:**

````ts
    expect(buildInviteUrl("Abc123")).toBe("https://app.example/join?code=Abc123");
  });
});
````

**with:**

````ts
    expect(buildInviteUrl("Abc123")).toBe("https://app.example/join?code=Abc123");
  });

  it("takes the code first and the origin second, as the People page calls it (slice 6b-2a)", () => {
    expect(buildInviteUrl("abc", "http://localhost:3000")).toBe("http://localhost:3000/join?code=abc");
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/settings/people.test.ts src/lib/clipboard.test.tsx src/lib/urls.test.ts 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`
**Expected:** the two new files cannot load their modules; the new `buildInviteUrl` case passes already:
```
 FAIL  |unit| src/lib/settings/people.test.ts [ src/lib/settings/people.test.ts ]
 FAIL  |dom| src/lib/clipboard.test.tsx [ src/lib/clipboard.test.tsx ]
      Tests  23 passed (23)
```

- [ ] **Step 3: The rules, `copyText` and the types**

**Append to `frontend/src/lib/api/types.ts`:**

````ts

/**
 * Settings → People (slice 6b-2a; the routes are slice 6b-1's): `GET /members`
 * (every member, with emails: the owner, admins, members, each by name) and one
 * member (`name` null when blank, `is_me` on the caller's own row); `PATCH
 * /members/{user_id}`'s body (member or admin, never owner) and `DELETE`'s
 * answer (how many invites the removal revoked); `GET /invites` (owners and
 * admins: the live links, newest first), one invite (its `code` is a bearer
 * secret: never logged, never in a URL but the link the admin shares) and its
 * creator (null once their account is gone); `POST /invites`'s body; and
 * `DELETE /invites/{invite_id}`'s answer.
 */
export type MemberList = components["schemas"]["MemberListOut"];
export type Member = components["schemas"]["MemberOut"];
export type RoleChangeBody = components["schemas"]["RoleChangeIn"];
export type MemberRemoved = components["schemas"]["RemovedOut"];
export type InviteList = components["schemas"]["InviteListOut"];
export type Invite = components["schemas"]["InviteOut"];
export type InviteCreator = components["schemas"]["InviteCreatorOut"];
export type InviteBody = components["schemas"]["InviteCreateIn"];
export type InviteRevoked = components["schemas"]["RevokedOut"];
````

**Create `frontend/src/lib/settings/people.ts`:**

````ts
/**
 * Settings → People's rules (slice 6b-2a; 6b spec "Pure helpers"): how a
 * person is named and shown, what an admin may do to a row (a mirror of the
 * server's role policy, tested against its shared fixture), and the invite
 * link's sentences. They decide only what the page shows; the server enforces.
 */
import type { Church, Invite, Member } from "@/lib/api/types";

/** A name or an email, as `MemberOut` and `InviteCreatorOut` carry them. */
type Person = Pick<Member, "name" | "email">;

/** The name, trimmed, else the email. */
export function displayName(person: Person): string {
  return person.name?.trim() || person.email;
}

/**
 * Up to two letters for the avatar: the first letters of the name's first and
 * last words, else the email's first letter, upper-cased.
 */
export function initials(person: Person): string {
  const words = (person.name ?? "").trim().split(/\s+/).filter(Boolean);
  const first = (word: string) => Array.from(word)[0] ?? "";
  if (words.length === 0) return first(person.email.trim()).toUpperCase();
  const letters = words.length === 1 ? first(words[0]) : first(words[0]) + first(words[words.length - 1]);
  return letters.toUpperCase();
}

export type MemberActions = {
  /** The role the menu offers ("Make admin" or "Make member"), or null: no role change. */
  changeRoleTo: "admin" | "member" | null;
  canRemove: boolean;
};

/**
 * What `actor` may do to `target`, mirroring the server's
 * `role_policy.check_role_change` and `check_remove` (`people.test.ts` runs
 * their shared fixture's change_role and remove rows): owners and admins make
 * a member an admin or an admin a member, and remove either; nobody acts on
 * their own row or on the owner's.
 */
export function memberActions(actor: { id: string; role: Church["role"] }, target: Member): MemberActions {
  const none: MemberActions = { changeRoleTo: null, canRemove: false };
  if (actor.role === "member") return none;
  if (target.user_id === actor.id || target.role === "owner") return none;
  return { changeRoleTo: target.role === "member" ? "admin" : "member", canRemove: true };
}

/** "a member" or "an admin". */
function asRole(role: Invite["role"]): string {
  return role === "admin" ? "an admin" : "a member";
}

/** The Invite link ready panel's sentence (UX 1a), with `formatDateTime` for the expiry. */
export function inviteSummary(
  invite: Pick<Invite, "email" | "role" | "reusable" | "expires_at">,
  churchName: string,
  formatDateTime: (iso: string) => string,
): string {
  const until = formatDateTime(invite.expires_at);
  if (invite.reusable) {
    return `Anyone with this link can join ${churchName} as ${asRole(invite.role)} until ${until}. Share it only with people you trust.`;
  }
  if (invite.email) {
    return `Only ${invite.email} can use this link to join ${churchName} as ${asRole(invite.role)}. It works once and expires ${until}.`;
  }
  return `Anyone who opens this link can join ${churchName} as ${asRole(invite.role)}. It works once and expires ${until}.`;
}

/** A timestamp as "Oct 17, 2026, 3:00 PM" (`timeZone` for tests; the device's zone otherwise). */
export function formatDateTime(iso: string, { timeZone }: { timeZone?: string } = {}): string {
  const at = Date.parse(iso);
  if (!Number.isFinite(at)) return "";
  const options: Intl.DateTimeFormatOptions = {
    month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit",
    ...(timeZone === undefined ? {} : { timeZone }),
  };
  // Newer ICU puts a narrow no-break space before AM/PM; a plain space reads the same everywhere.
  return new Intl.DateTimeFormat("en-US", options).format(at).replace(/\u202f/g, " ");
}

const HOUR = 60 * 60 * 1000;
const DAY = 24 * HOUR;

/**
 * When an invite expires, for its row: `relative` ("in 7 days", "in 5 hours",
 * "in less than an hour") and `full` (the date and time, for `title` and
 * `aria-label`). Days and hours are rounded to the nearest whole one.
 */
export function formatExpiry(
  expiresAtIso: string,
  now: Date = new Date(),
  { timeZone }: { timeZone?: string } = {},
): { relative: string; full: string } {
  const left = Date.parse(expiresAtIso) - now.getTime();
  const words = new Intl.RelativeTimeFormat("en-US", { numeric: "always" });
  let relative: string;
  const hours = Math.round(left / HOUR);
  // The unit is chosen after rounding, so 23.5 hours reads "in 1 day", never "in 24 hours".
  if (!(left >= HOUR)) relative = "in less than an hour";
  else if (hours < 24) relative = words.format(hours, "hour");
  else relative = words.format(Math.round(left / DAY), "day");
  return { relative, full: formatDateTime(expiresAtIso, { timeZone }) };
}

/** Invites `creatorId` made: the removal revokes them (the Remove dialog's count). */
export function invitesCreatedBy(invites: readonly Invite[], creatorId: string): number {
  return invites.filter((invite) => invite.created_by?.user_id === creatorId).length;
}

/** Live reusable links someone other than `creatorId` made: what "Also revoke …" would revoke too. */
export function otherReusableInvites(invites: readonly Invite[], creatorId: string): number {
  return invites.filter((invite) => invite.reusable && invite.created_by?.user_id !== creatorId).length;
}
````

**Create `frontend/src/lib/clipboard.ts`:**

````ts
/**
 * Copying text (slice 6b-2a; 6b spec "Pure helpers"): the Clipboard API when
 * the browser allows it, else a hidden textarea and `document.execCommand`,
 * which older phones still need. Never throws: false means the text was not
 * copied, so the caller can select it for the user instead.
 */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Refused (no permission, not a secure page): try the old way.
  }
  return copyWithTextarea(text);
}

function copyWithTextarea(text: string): boolean {
  if (typeof document === "undefined" || typeof document.execCommand !== "function") return false;
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.top = "0";
  area.style.left = "0";
  area.style.opacity = "0";
  document.body.appendChild(area);
  try {
    area.select();
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    area.remove();
  }
}
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/lib/settings/people.test.ts src/lib/clipboard.test.tsx src/lib/urls.test.ts 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  45 passed (45)
```
```
typecheck 0
lint 0
```
```
 Test Files  111 passed (111)
      Tests  975 passed (975)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/settings/people.ts frontend/src/lib/settings/people.test.ts frontend/src/lib/clipboard.ts frontend/src/lib/clipboard.test.tsx frontend/src/lib/api/types.ts frontend/src/test/fixtures/index.ts frontend/src/lib/urls.test.ts
git commit -q -m "Slice 6b-2a: the People rules, copyText and the types" -m "lib/settings/people.ts: displayName, initials, memberActions (checked
against the 51-row shared role-policy fixture's change_role and remove
rows), the invite link's three sentences, the date and the expiry, and the
Remove dialog's two counts. lib/clipboard.ts: copyText (the Clipboard API,
else a hidden textarea; false, never a throw). The People type aliases and
test fixtures, and one buildInviteUrl case pinning (code, origin)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2235 passed, 48 skipped`; frontend `975 passed` in 111 files.

### Task 3: The People queries, Copy link, the initials avatar, and a confirm dialog with a body (S "Queries and mutations", "Components" `CopyLinkButton` and `InitialsAvatar`; clarifications 6a-6c, 7, 10)

**Files:**
- Create: `frontend/src/lib/queries/people.ts`, `frontend/src/components/app/copy-link-button.tsx`, `frontend/src/components/app/copy-link-button.test.tsx`, `frontend/src/components/app/initials-avatar.tsx`
- Modify: `frontend/src/components/app/confirm-dialog.tsx`, `frontend/src/components/app/confirm-dialog.test.tsx`

`ConfirmDialog` shows `children` under the description and above the buttons, and says `pendingLabel` while pending. **Copy link** copies, reads "Copied ✓" for two seconds (a `label` given for screen readers is dropped meanwhile, so the name follows what shows) and toasts "Link copied"; when copying is refused it calls `onCopyFailed` (the caller selects the link) and toasts S's words. The avatar shows initials only, hidden from screen readers, with no picture. The six hooks are typed here and tested through the page (T4, T5): their role refusal, lost-church and field-error handling is clarification 7's, and `useInvites` removes the cached list once it is disabled.

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/components/app/confirm-dialog.test.tsx`, replace:**

````tsx
  });
});
````

**with:**

````tsx
  });

  it("shows more of the body under the description, above the buttons (slice 6b-2a)", async () => {
    render(
      <ConfirmDialog
        open
        onOpenChange={() => {}}
        title="Remove Ann Admin?"
        description="Ann Admin will lose access to Grace."
        confirmLabel="Remove member"
        onConfirm={() => {}}
        destructive
      >
        <label>
          <input type="checkbox" defaultChecked /> Also revoke the 1 reusable invite link
        </label>
      </ConfirmDialog>,
    );
    const dialog = await screen.findByRole("alertdialog", { name: "Remove Ann Admin?" });
    const box = within(dialog).getByRole("checkbox", { name: "Also revoke the 1 reusable invite link" });
    expect(box).toBeChecked();
    expect(box.compareDocumentPosition(within(dialog).getByRole("button", { name: "Remove member" })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(dialog).toHaveAccessibleDescription("Ann Admin will lose access to Grace.");
  });

  it("names the pending action when asked (slice 6b-2a)", async () => {
    render(
      <ConfirmDialog open onOpenChange={() => {}} title="Revoke this invite?" confirmLabel="Revoke invite"
        onConfirm={() => {}} destructive pending pendingLabel="Revoking…" />,
    );
    const dialog = await screen.findByRole("alertdialog", { name: "Revoke this invite?" });
    expect(within(dialog).getByRole("button", { name: "Revoking…" })).toHaveAttribute("aria-disabled", "true");
  });
});
````

**Create `frontend/src/components/app/copy-link-button.test.tsx`:**

````tsx
/** Copy link (slice 6b-2a; 6b spec UX 1a) and the initials avatar. */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";

import { COPY_FAILED, CopyLinkButton, LINK_COPIED } from "./copy-link-button";
import { InitialsAvatar } from "./initials-avatar";

const realExecCommand = document.execCommand;

afterEach(() => {
  toast.dismiss();
  document.execCommand = realExecCommand;
});

describe("CopyLinkButton (slice 6b-2a)", () => {
  it("copies the link, says Copied ✓ for two seconds and toasts Link copied", async () => {
    const user = userEvent.setup(); // installs a clipboard the test can read back
    const onCopyFailed = vi.fn();
    render(
      <>
        <CopyLinkButton text="http://localhost:3000/join?code=abc" onCopyFailed={onCopyFailed} size="touch" />
        <Toaster />
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Copy link" }));
    expect(await screen.findByText(LINK_COPIED)).toBeInTheDocument();
    expect(LINK_COPIED).toBe("Link copied");
    expect(screen.getByRole("button", { name: "Copied ✓" })).toHaveClass("h-11");
    expect(await navigator.clipboard.readText()).toBe("http://localhost:3000/join?code=abc");
    expect(onCopyFailed).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByRole("button", { name: "Copy link" })).toBeInTheDocument(), { timeout: 3000 });
  });

  it("selects the link through onCopyFailed and says so when copying is refused", async () => {
    const user = userEvent.setup();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new DOMException("Not allowed", "NotAllowedError"));
    document.execCommand = vi.fn(() => false);
    const onCopyFailed = vi.fn();
    render(
      <>
        <CopyLinkButton text="the link" onCopyFailed={onCopyFailed} label="Copy link for anyone with the link" />
        <Toaster />
      </>,
    );
    await user.click(screen.getByRole("button", { name: "Copy link for anyone with the link" }));
    expect(await screen.findByText(COPY_FAILED)).toBeInTheDocument();
    expect(COPY_FAILED).toBe("Couldn't copy. The link is selected; copy it from there.");
    expect(onCopyFailed).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Copy link for anyone with the link" })).toHaveTextContent("Copy link");
  });
});

describe("InitialsAvatar (slice 6b-2a)", () => {
  it("shows initials only, hidden from screen readers, and loads no picture", () => {
    const { container } = render(<InitialsAvatar name="Ann Admin" email="ann@example.com" />);
    const avatar = container.querySelector("[data-slot=avatar]");
    expect(avatar).toHaveTextContent("AA");
    expect(avatar).toHaveAttribute("aria-hidden", "true");
    expect(container.querySelector("img")).toBeNull();
    render(<InitialsAvatar name={null} email="sam@example.com" />);
    expect(screen.getByText("S", { exact: true })).toBeInTheDocument();
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/app/confirm-dialog.test.tsx src/components/app/copy-link-button.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`
**Expected:** the body is not shown and the pending label is "Saving…"; the new file cannot load its modules:
```
   × ConfirmDialog > shows more of the body under the description, above the buttons (slice 6b-2a)
   × ConfirmDialog > names the pending action when asked (slice 6b-2a)
 FAIL  |dom| src/components/app/copy-link-button.test.tsx [ src/components/app/copy-link-button.test.tsx ]
  7  |  import { COPY_FAILED, CopyLinkButton, LINK_COPIED } from "./copy-link-button";
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |dom| src/components/app/confirm-dialog.test.tsx > ConfirmDialog > shows more of the body under the description, above the buttons (slice 6b-2a)
 FAIL  |dom| src/components/app/confirm-dialog.test.tsx > ConfirmDialog > names the pending action when asked (slice 6b-2a)
      Tests  2 failed | 4 passed (6)
```

- [ ] **Step 3: The dialog's two props, Copy link, the avatar and the queries**

**In `frontend/src/components/app/confirm-dialog.tsx`, replace:**

````tsx
import type { AlertDialog as AlertDialogPrimitive } from "@base-ui/react/alert-dialog";
````

**with:**

````tsx
import type { AlertDialog as AlertDialogPrimitive } from "@base-ui/react/alert-dialog";
import type { ReactNode } from "react";
````

**In `frontend/src/components/app/confirm-dialog.tsx`, replace:**

````tsx
  pending?: boolean;
````

**with:**

````tsx
  pending?: boolean;
  /** The confirm button's words while `pending` ("Removing…"; slice 6b-2a): "Saving…" unless given. */
  pendingLabel?: string;
````

**In `frontend/src/components/app/confirm-dialog.tsx`, replace:**

````tsx
  finalFocus?: AlertDialogPrimitive.Popup.Props["finalFocus"];
````

**with:**

````tsx
  finalFocus?: AlertDialogPrimitive.Popup.Props["finalFocus"];
  /** More of the dialog's body under the description (a sentence that depends on data, a checkbox; slice 6b-2a). */
  children?: ReactNode;
````

**In `frontend/src/components/app/confirm-dialog.tsx`, replace:**

````tsx
  destructive = false,
  onCancel,
  finalFocus,
````

**with:**

````tsx
  pendingLabel,
  destructive = false,
  onCancel,
  finalFocus,
  children,
````

**In `frontend/src/components/app/confirm-dialog.tsx`, replace:**

````tsx
        </AlertDialogHeader>
````

**with:**

````tsx
        </AlertDialogHeader>
        {children}
````

**In `frontend/src/components/app/confirm-dialog.tsx`, replace:**

````tsx
            pending={pending}
````

**with:**

````tsx
            pending={pending}
            {...(pendingLabel === undefined ? {} : { pendingLabel })}
````

**Create `frontend/src/components/app/copy-link-button.tsx`:**

````tsx
"use client";

import { CopyIcon } from "lucide-react";
import { useEffect, useRef, useState, type ComponentProps } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { copyText } from "@/lib/clipboard";

export const LINK_COPIED = "Link copied";
export const COPY_FAILED = "Couldn't copy. The link is selected; copy it from there.";
const COPIED_FOR_MS = 2000;

export type CopyLinkButtonProps = Omit<ComponentProps<typeof Button>, "onClick" | "children"> & {
  /** The link to copy. */
  text: string;
  /** When copying fails: show and select the link so the user can copy it themselves. */
  onCopyFailed(): void;
  /**
   * Screen readers' name when the visible label alone is not enough ("Copy link
   * for …"); dropped while "Copied ✓" shows, so the name follows the label.
   */
  label?: string;
};

/**
 * **Copy link** (6b spec UX 1a): copies `text`; on success the label reads
 * "Copied ✓" for 2 s and a toast says "Link copied"; when the browser refuses,
 * `onCopyFailed` selects the link and a toast says so.
 */
export function CopyLinkButton({ text, onCopyFailed, label, ...props }: CopyLinkButtonProps) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  async function onClick() {
    if (await copyText(text)) {
      setCopied(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), COPIED_FOR_MS);
      toast.success(LINK_COPIED);
    } else {
      onCopyFailed();
      toast.error(COPY_FAILED);
    }
  }

  return (
    <Button type="button" aria-label={copied ? undefined : label} {...props} onClick={() => void onClick()}>
      {copied ? null : <CopyIcon data-icon="inline-start" aria-hidden="true" />}
      {copied ? "Copied ✓" : "Copy link"}
    </Button>
  );
}
````

**Create `frontend/src/components/app/initials-avatar.tsx`:**

````tsx
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { initials } from "@/lib/settings/people";

/**
 * A person's initials in a circle (6b spec "Every page"): never a picture,
 * since another person's picture address is theirs to edit. Hidden from
 * screen readers: the name is written beside it.
 */
export function InitialsAvatar({ name, email }: { name: string | null; email: string }) {
  return (
    <Avatar size="lg" aria-hidden="true">
      <AvatarFallback className="font-medium">{initials({ name, email })}</AvatarFallback>
    </Avatar>
  );
}
````

**Create `frontend/src/lib/queries/people.ts`:**

````ts
/**
 * Settings → People's queries (slice 6b-2a; 6b spec "Queries and mutations"):
 * `GET /members` under ["church", id, "members"], `GET /invites` under
 * ["church", id, "invites"] (owners and admins only; never cached as fresh,
 * since its codes are secrets and a revoked link must not linger), and the
 * role change, removal, invite and revoke an owner or admin makes.
 *
 * A role 403 (an admin demoted elsewhere; no `details.reason`) is toasted and
 * refetches the church profile, which carries the role, and the member list,
 * so the page turns read-only and the user stays in the church (6a's way:
 * each hook handles it, not a cache-wide `forbiddenIsRole` meta). A 401 or a
 * lost church (`no_church_access`) is the app's: it signs out or falls back
 * to another church. Writes are not optimistic: each puts the answer in the
 * cache, then refetches.
 */
import { useQuery, useQueryClient, type QueryClient, type UseQueryResult } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type {
  Invite,
  InviteBody,
  InviteList,
  InviteRevoked,
  Member,
  MemberList,
  MemberRemoved,
} from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

/** A 403 that is about the role, not the church: the server's role refusal. */
export function isRoleRefusal(e: unknown): boolean {
  return e instanceof ApiError && e.status === 403 && !isNoChurchAccess(e);
}

/** A role refusal's toast and refetches: the page re-renders for the role the user has now. */
function onRoleRefused(queryClient: QueryClient, churchId: string, e: ApiError): void {
  toast.error(errorToastMessage(e));
  void queryClient.invalidateQueries({ queryKey: keys.churchProfile(churchId) });
  void queryClient.invalidateQueries({ queryKey: keys.members(churchId) });
}

/**
 * A failed write's handling: nothing for a 401 or a lost church (the app's),
 * nothing for a failure `isForm` says the form shows under a field, a role
 * refusal as above, and any other message toasted (a 404 also refetches
 * `refetchKey`, the list the missing row came from).
 */
function onWriteError(queryClient: QueryClient, churchId: string, refetchKey: readonly unknown[],
                      isForm: (e: ApiError) => boolean = () => false) {
  return (e: ApiError) => {
    if (e.status === 401 || isNoChurchAccess(e) || isForm(e)) return;
    if (isRoleRefusal(e)) {
      onRoleRefused(queryClient, churchId, e);
      return;
    }
    toast.error(errorToastMessage(e));
    if (e.status === 404) void queryClient.invalidateQueries({ queryKey: refetchKey });
  };
}

/** `GET /members`: everyone in the church, with emails (every role). */
export function useMembers(): UseQueryResult<MemberList, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<MemberList, ApiError>({
    queryKey: keys.members(church.id),
    queryFn: ({ signal }) => api.church<MemberList>("/members", { signal }),
  });
}

/**
 * `GET /invites` (owners and admins; no request otherwise): the live links,
 * newest first. A role refusal is handled as for a write, here in the query,
 * so a demoted admin's page turns read-only. Once the role no longer allows
 * it (`enabled` false), the cached list and its codes are removed. Not at the
 * refusal itself: the page's queries are still enabled then, so they would
 * fetch the list again and be refused again until the new role arrives.
 */
export function useInvites({ enabled }: { enabled: boolean }): UseQueryResult<InviteList, ApiError> {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!enabled) queryClient.removeQueries({ queryKey: keys.invites(church.id) });
  }, [enabled, church.id, queryClient]);
  return useQuery<InviteList, ApiError>({
    queryKey: keys.invites(church.id),
    queryFn: async ({ signal }) => {
      try {
        return await api.church<InviteList>("/invites", { signal });
      } catch (e) {
        if (e instanceof ApiError && isRoleRefusal(e)) onRoleRefused(queryClient, church.id, e);
        throw e;
      }
    },
    enabled,
    staleTime: 0,
  });
}

/** `PATCH /members/{user_id}` (owners and admins): make a member an admin or an admin a member. */
export function useChangeRole() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.members(church.id);
  return useChurchMutation<Member, ApiError, { userId: string; role: "member" | "admin" }>({
    mutationFn: ({ userId, role }) =>
      api.church<Member>(`/members/${encodeURIComponent(userId)}`, { method: "PATCH", json: { role } }),
    onSuccess: async (saved) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<MemberList>(key, (list) =>
        list ? { items: list.items.map((m) => (m.user_id === saved.user_id ? saved : m)) } : list,
      );
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: onWriteError(queryClient, church.id, key),
  });
}

/**
 * `DELETE /members/{user_id}?revoke_reusable=` (owners and admins): the
 * removal also revokes the invites the person made, and with
 * `revokeReusable` every live reusable link, so both lists refetch.
 */
export function useRemoveMember() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.members(church.id);
  return useChurchMutation<MemberRemoved, ApiError, { userId: string; revokeReusable: boolean }>({
    mutationFn: ({ userId, revokeReusable }) =>
      api.church<MemberRemoved>(`/members/${encodeURIComponent(userId)}?revoke_reusable=${revokeReusable}`, {
        method: "DELETE",
      }),
    onSuccess: async (_removed, { userId }) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<MemberList>(key, (list) =>
        list ? { items: list.items.filter((m) => m.user_id !== userId) } : list,
      );
      void queryClient.invalidateQueries({ queryKey: key });
      void queryClient.invalidateQueries({ queryKey: keys.invites(church.id) });
    },
    onError: onWriteError(queryClient, church.id, key),
  });
}

/**
 * A failed invite's message for the form (409 `invite_exists` or `conflict`,
 * or a 422 naming the email or the reusable box): `{field, message}`, or null
 * for anything else, which the mutation toasts.
 */
export function inviteFieldError(e: unknown): { field: "email" | "reusable"; message: string } | null {
  if (!(e instanceof ApiError)) return null;
  if (e.status === 409) return { field: "email", message: e.message };
  if (e.status !== 422) return null;
  if (e.fields?.email) return { field: "email", message: e.fields.email };
  if (e.fields?.reusable) return { field: "reusable", message: e.fields.reusable };
  return null;
}

/**
 * `POST /invites` (owners and admins), with a new `Idempotency-Key` for every
 * click (6b spec), so a repeat of the same request is never a second link.
 * The new invite goes first in the cached list, then the list refetches.
 */
export function useCreateInvite() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.invites(church.id);
  return useChurchMutation<Invite, ApiError, InviteBody>({
    mutationFn: (body) =>
      api.church<Invite>("/invites", { method: "POST", json: body, idempotencyKey: crypto.randomUUID() }),
    onSuccess: async (created) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<InviteList>(key, (list) =>
        list ? { items: [created, ...list.items.filter((i) => i.id !== created.id)] } : list,
      );
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: onWriteError(queryClient, church.id, key, (e) => inviteFieldError(e) !== null),
  });
}

/** `DELETE /invites/{invite_id}` (owners and admins): the link stops working. */
export function useRevokeInvite() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.invites(church.id);
  return useChurchMutation<InviteRevoked, ApiError, string>({
    mutationFn: (inviteId) => api.church<InviteRevoked>(`/invites/${encodeURIComponent(inviteId)}`, { method: "DELETE" }),
    onSuccess: async (_revoked, inviteId) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<InviteList>(key, (list) =>
        list ? { items: list.items.filter((i) => i.id !== inviteId) } : list,
      );
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: onWriteError(queryClient, church.id, key),
  });
}
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/components/app/confirm-dialog.test.tsx src/components/app/copy-link-button.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  9 passed (9)
```
```
typecheck 0
lint 0
```
```
 Test Files  112 passed (112)
      Tests  980 passed (980)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/queries/people.ts frontend/src/components/app/copy-link-button.tsx frontend/src/components/app/copy-link-button.test.tsx frontend/src/components/app/initials-avatar.tsx frontend/src/components/app/confirm-dialog.tsx frontend/src/components/app/confirm-dialog.test.tsx
git commit -q -m "Slice 6b-2a: the People queries, Copy link, initials, and a confirm dialog with a body" -m "lib/queries/people.ts: useMembers, useInvites (owners and admins, never
cached as fresh), useChangeRole, useRemoveMember, useCreateInvite (a new
Idempotency-Key per click) and useRevokeInvite; a role refusal is toasted
and refetches the role and the member list, as 6a's hooks do; a lost
church is the app's. CopyLinkButton (Copied, Link copied, or the link
selected when copying is refused) and InitialsAvatar (initials only).
ConfirmDialog gains children under the description and a pendingLabel." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2235 passed, 48 skipped`; frontend `980 passed` in 112 files.

### Task 4: Settings → People: the page and Members (S UX "Every page", 1b, "Losing a role mid-session"; Testing → Frontend DOM; acceptance 14, 16, 18; clarifications 6a, 6d, 7-9)

**Files:**
- Create: `frontend/src/app/(signed-in)/(church)/settings/people/page.tsx`, `frontend/src/components/settings/people/people-settings-page.tsx`, `frontend/src/components/settings/people/members-list.tsx`, `frontend/src/components/settings/people/people-settings-page.test.tsx`

Rendered inside the Settings layout with a Toaster, over a fake `/members` that answers with what the writes left. A member sees everyone with emails, their row marked **You**, the note, no menu, and no `GET /invites` is sent. An admin gets a 44 px menu on members' and other admins' rows only; the owner turns an admin into a member at once (`PATCH` with `{"role":"member"}` and `X-Church-Id`; the badge follows), and an admin's menu is busy while the change runs. Remove asks first: the dialog counts the links the person made ("The 2 invite links Ann Admin created will stop working.") and offers "Also revoke the 1 reusable invite link", checked; confirming sends `revoke_reusable=true`, the row goes, the invites refetch and focus moves to the heading; unchecked it sends `false`; with no other reusable link there is no box; with the invites unreadable it speaks generally with the box checked; Cancel sends nothing. A role refusal (of a write or of `GET /invites`) is toasted and refetches the profile and the members without reporting a lost church; a `no_church_access` 403 is reported to the app and not toasted here; a failed list shows Retry. The Remove box is checked again each time the dialog opens, even after it was unchecked and cancelled. The invite list's query has `staleTime` 0. Around every test of the file, every `console` method is spied on, and a call whose arguments carry a fixture's invite code or `code=` fails the test.

- [ ] **Step 1: Write the failing tests**

**Create `frontend/src/components/settings/people/people-settings-page.test.tsx`:**

````tsx
/**
 * Settings → People (slice 6b-2a; 6b spec UX §1 and Testing → Frontend DOM):
 * every member reads the list; owners and admins change roles and remove
 * people. Rendered inside the Settings layout, as the route is, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import PeopleSettingsRoute from "@/app/(signed-in)/(church)/settings/people/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Invite, Member, MemberList } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, invite, inviteList, me, memberList, PEOPLE } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { MEMBERS_NOTE } from "./members-list";

/** The invite codes in these tests' fixtures: none may reach the console (codes are never logged). */
const FIXTURE_CODES = ["abc", "r-123", "r-1"];
const CONSOLE_METHODS = ["debug", "error", "info", "log", "trace", "warn"] as const;
let consoleSpies: MockInstance[] = [];

function printable(value: unknown): string {
  if (typeof value === "string") return value;
  if (value instanceof Error) return `${value.message} ${value.stack ?? ""}`;
  try {
    return JSON.stringify(value) ?? String(value);
  } catch {
    return String(value);
  }
}

beforeEach(() => {
  consoleSpies = CONSOLE_METHODS.map((method) => vi.spyOn(console, method));
});

afterEach(() => {
  toast.dismiss();
  const printed = consoleSpies.flatMap((spy) => spy.mock.calls.map((args) => args.map(printable).join(" ")));
  consoleSpies.forEach((spy) => spy.mockRestore());
  for (const line of printed) {
    expect(line).not.toMatch(/code=/);
    for (const code of FIXTURE_CODES) expect(line).not.toMatch(new RegExp(`\\b${code}\\b`));
  }
});

const ANN = { user_id: PEOPLE.ann, name: "Ann Admin", email: "ann@example.com" };

/** A fake `/members` whose `GET` answers with what the writes left, as the server would. */
function membersServer(initial: MemberList) {
  let items = [...initial.items];
  return {
    list: () => ({ items }),
    patch: (userId: string) => (r: RecordedRequest) => {
      items = items.map((m) => (m.user_id === userId ? { ...m, ...(r.body as Partial<Member>) } : m));
      return items.find((m) => m.user_id === userId);
    },
    remove: (userId: string) => () => {
      items = items.filter((m) => m.user_id !== userId);
      return { removed: true, revoked_invites: 2 };
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({ "GET /members": memberList(role), "GET /invites": inviteList(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <PeopleSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/people" },
  );
  return { ...view, api };
}

function rows() {
  return within(screen.getByRole("list", { name: "Members" })).getAllByRole("listitem");
}

function row(name: string) {
  return rows().find((r) => within(r).queryByText(name, { exact: true }) !== null)!;
}

function sent(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/members"));
}

async function openRemove(user: { click(e: Element): Promise<void> }, name: string) {
  await user.click(await screen.findByRole("button", { name: `Actions for ${name}` }));
  await user.click(await screen.findByRole("menuitem", { name: "Remove from church" }));
  return screen.findByRole("alertdialog", { name: `Remove ${name}?` });
}

describe("Settings → People: Members (slice 6b-2a)", () => {
  it("shows a member everyone with emails, their own row marked, and no actions", async () => {
    const { api } = renderPage("member");
    expect(await screen.findByRole("heading", { name: "Members (5)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "People" })).toBeInTheDocument();
    expect(screen.getByText("Everyone in Grace can see this list.")).toBeInTheDocument();
    expect(screen.getByText(MEMBERS_NOTE)).toBeInTheDocument();
    expect(MEMBERS_NOTE).toBe("Only admins can change roles or remove people. To add someone, ask an admin for an invite link.");
    expect(rows().map((r) => r.textContent)).toEqual([
      "OOOlive Ownerolive@example.comOwner",
      "AAAnn Adminann@example.comAdmin",
      "MMMo Membermo@example.comMember",
      "PPPat PastorYoupat@example.comMember",
      "Ssam@example.comMember",
    ]);
    expect(screen.queryByRole("button", { name: /^Actions for / })).toBeNull();
    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual(["GET /members"]);
  });

  it("gives an admin a menu on members' and other admins' rows, never on the owner's or their own", async () => {
    renderPage("admin");
    await screen.findByRole("heading", { name: "Members (5)" });
    expect(screen.getAllByRole("button", { name: /^Actions for / }).map((b) => b.getAttribute("aria-label"))).toEqual([
      "Actions for Ann Admin",
      "Actions for Mo Member",
      "Actions for sam@example.com",
    ]);
    expect(screen.getByRole("button", { name: "Actions for Mo Member" })).toHaveClass("size-11");
    expect(screen.queryByText(MEMBERS_NOTE)).toBeNull();
  });

  it("lets the owner make an admin a member at once, and the badge follows", async () => {
    const server = membersServer(memberList("owner"));
    const { api, user } = renderPage("owner", {
      "GET /members": server.list,
      [`PATCH /members/${PEOPLE.ann}`]: server.patch(PEOPLE.ann),
    });
    await user.click(await screen.findByRole("button", { name: "Actions for Ann Admin" }));
    expect((await screen.findAllByRole("menuitem")).map((i) => i.textContent)).toEqual(["Make member", "Remove from church"]);
    await user.click(screen.getByRole("menuitem", { name: "Make member" }));
    await waitFor(() => expect(within(row("Ann Admin")).getByText("Member")).toBeInTheDocument());
    expect(sent(api, "PATCH")).toHaveLength(1);
    expect(sent(api, "PATCH")[0].body).toEqual({ role: "member" });
    expect(sent(api, "PATCH")[0].headers["x-church-id"]).toBe(church().id);
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("lets an admin make a member an admin, with the menu busy while it runs", async () => {
    let release: () => void = () => {};
    const server = membersServer(memberList("admin"));
    const { user } = renderPage("admin", {
      "GET /members": server.list,
      [`PATCH /members/${PEOPLE.mo}`]: async (r: RecordedRequest) => {
        await new Promise<void>((resolve) => (release = resolve));
        return server.patch(PEOPLE.mo)(r);
      },
    });
    await user.click(await screen.findByRole("button", { name: "Actions for Mo Member" }));
    await user.click(await screen.findByRole("menuitem", { name: "Make admin" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Actions for Mo Member" })).toBeDisabled());
    release();
    await waitFor(() => expect(within(row("Mo Member")).getByText("Admin")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Actions for Mo Member" })).toBeEnabled();
  });

  it("asks before removing, says which links stop working, and revokes the reusable ones when left checked", async () => {
    const server = membersServer(memberList("admin"));
    const invites: Invite[] = [
      invite({ id: "c0000000-0000-4000-8000-000000000001", created_by: ANN }),
      invite({ id: "c0000000-0000-4000-8000-000000000002", created_by: ANN, email: "x@example.com" }),
      invite({ id: "c0000000-0000-4000-8000-000000000003", reusable: true }),
    ];
    const { api, user } = renderPage("admin", {
      "GET /members": server.list,
      "GET /invites": inviteList(invites),
      [`DELETE /members/${PEOPLE.ann}`]: server.remove(PEOPLE.ann),
    });
    const dialog = await openRemove(user, "Ann Admin");
    expect(dialog).toHaveAccessibleDescription("Ann Admin will lose access to Grace. Services they saved stay in the archive.");
    await waitFor(() => expect(within(dialog).getByText("The 2 invite links Ann Admin created will stop working.")).toBeInTheDocument());
    const box = within(dialog).getByRole("checkbox", { name: "Also revoke the 1 reusable invite link" });
    expect(box).toBeChecked();
    expect(within(dialog).getByText(/Anyone with a reusable link, including Ann Admin, can use it to rejoin until it expires\./)).toBeInTheDocument();
    const invitesReads = api.requests.filter((r) => r.path === "/invites").length;
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(sent(api, "DELETE").map((r) => r.path)).toEqual([`/members/${PEOPLE.ann}?revoke_reusable=true`]);
    await waitFor(() => expect(rows()).toHaveLength(4));
    expect(screen.queryByText("Ann Admin")).toBeNull();
    await waitFor(() => expect(api.requests.filter((r) => r.path === "/invites").length).toBeGreaterThan(invitesReads));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Members (4)" })).toHaveFocus());
  });

  it("sends revoke_reusable=false when the box is unchecked, and shows no box when no other reusable link exists", async () => {
    const server = membersServer(memberList("admin"));
    const { api, user } = renderPage("admin", {
      "GET /members": server.list,
      "GET /invites": inviteList([invite({ reusable: true })]),
      [`DELETE /members/${PEOPLE.mo}`]: server.remove(PEOPLE.mo),
      [`DELETE /members/${PEOPLE.sam}`]: server.remove(PEOPLE.sam),
    });
    let dialog = await openRemove(user, "Mo Member");
    await user.click(await within(dialog).findByRole("checkbox", { name: "Also revoke the 1 reusable invite link" }));
    // what the list holds once Mo is removed (the removal refetches it): only a link sam made
    api.set("GET /invites", inviteList([invite({ created_by: { user_id: PEOPLE.sam, name: null, email: "sam@example.com" }, reusable: true })]));
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(rows()).toHaveLength(4));
    dialog = await openRemove(user, "sam@example.com");
    await waitFor(() => expect(within(dialog).getByText("The 1 invite link sam@example.com created will stop working.")).toBeInTheDocument());
    expect(within(dialog).queryByRole("checkbox")).toBeNull();
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(sent(api, "DELETE").map((r) => r.path)).toEqual([
      `/members/${PEOPLE.mo}?revoke_reusable=false`,
      `/members/${PEOPLE.sam}?revoke_reusable=false`,
    ]);
  });

  it("speaks generally, with the box checked, when the invites could not be read", async () => {
    const { api, user } = renderPage("admin", {
      "GET /invites": fakeError(500, "internal_error", "Something went wrong."),
      [`DELETE /members/${PEOPLE.mo}`]: { removed: true, revoked_invites: 0 },
    });
    const dialog = await openRemove(user, "Mo Member");
    expect(within(dialog).getByText("Any invite links Mo Member created will stop working.")).toBeInTheDocument();
    expect(within(dialog).getByRole("checkbox", { name: "Also revoke every reusable invite link" })).toBeChecked();
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    await waitFor(() => expect(sent(api, "DELETE").map((r) => r.path)).toEqual([`/members/${PEOPLE.mo}?revoke_reusable=true`]));
  });

  it("checks Also revoke again each time the dialog opens, even after it was unchecked and cancelled", async () => {
    const { api, user } = renderPage("admin", { "GET /invites": inviteList([invite({ reusable: true })]) });
    let dialog = await openRemove(user, "Mo Member");
    const box = await within(dialog).findByRole("checkbox", { name: "Also revoke the 1 reusable invite link" });
    await user.click(box);
    expect(box).not.toBeChecked();
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    dialog = await openRemove(user, "Mo Member");
    expect(await within(dialog).findByRole("checkbox", { name: "Also revoke the 1 reusable invite link" })).toBeChecked();
    expect(sent(api, "DELETE")).toEqual([]);
  });

  it("Cancel keeps the person and sends nothing", async () => {
    const { api, user } = renderPage("admin");
    const dialog = await openRemove(user, "Mo Member");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(sent(api, "DELETE")).toEqual([]);
    expect(rows()).toHaveLength(5);
  });

  it("toasts the server's refusal and refetches the role and the list, staying in the church", async () => {
    const lost = vi.fn();
    const unsubscribe = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("admin", {
      [`DELETE /members/${PEOPLE.mo}`]: fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const dialog = await openRemove(user, "Mo Member");
    await user.click(within(dialog).getByRole("button", { name: "Remove member" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
    expect(lost).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("toasts a role refusal of the invite list, refetches the role and the list, and stays in the church", async () => {
    const lost = vi.fn();
    const unsubscribe = authEvents.onChurchAccessLost(lost);
    const { queryClient } = renderPage("admin", {
      "GET /invites": fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
    expect(lost).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("leaves a lost church to the app: a no_church_access 403 on a role change reports the church", async () => {
    const lost = vi.fn();
    const unsubscribe = authEvents.onChurchAccessLost(lost);
    const { user } = renderPage("admin", {
      [`PATCH /members/${PEOPLE.mo}`]: fakeError(403, "forbidden", "You don't have access to this church.", {
        details: { reason: "no_church_access" },
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Actions for Mo Member" }));
    await user.click(await screen.findByRole("menuitem", { name: "Make admin" }));
    await waitFor(() => expect(lost).toHaveBeenCalledWith(church().id));
    expect(screen.queryByText("You don't have access to this church.")).toBeNull();
    unsubscribe();
  });

  it("never keeps the invite list as fresh, since its codes are secrets (staleTime 0)", async () => {
    const { queryClient } = renderPage("admin");
    await screen.findByRole("heading", { name: "Members (5)" });
    await waitFor(() => expect(queryClient.getQueryCache().find({ queryKey: keys.invites(church().id) })?.state.status).toBe("success"));
    const query = queryClient.getQueryCache().find({ queryKey: keys.invites(church().id) })!;
    expect(new Set(query.observers.map((observer) => observer.options.staleTime))).toEqual(new Set([0]));
  });

  it("shows the error state with Retry when the list cannot be read", async () => {
    const { api, user } = renderPage("member", { "GET /members": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "Members" })).toBeNull();
    api.set("GET /members", memberList("member"));
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: "Members (5)" })).toBeInTheDocument();
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/people/people-settings-page.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`
**Expected:** the route and the list do not exist yet:
```
 FAIL  |dom| src/components/settings/people/people-settings-page.test.tsx [ src/components/settings/people/people-settings-page.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: The route, the page and Members**

**Create `frontend/src/components/settings/people/members-list.tsx`:**

````tsx
"use client";

import { EllipsisVerticalIcon, Loader2Icon } from "lucide-react";
import { useRef, useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { InitialsAvatar } from "@/components/app/initials-avatar";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import type { Church, InviteList, Member } from "@/lib/api/types";
import { isAdmin, roleLabel } from "@/lib/church";
import { useChangeRole, useInvites, useMembers, useRemoveMember } from "@/lib/queries/people";
import { displayName, invitesCreatedBy, memberActions, otherReusableInvites } from "@/lib/settings/people";
import { cn } from "@/lib/utils";

export const MEMBERS_NOTE = "Only admins can change roles or remove people. To add someone, ask an admin for an invite link.";

const ROLE_BADGE: Record<Member["role"], "default" | "secondary" | "outline"> = {
  owner: "default",
  admin: "secondary",
  member: "outline",
};

/** "1 invite link" or "2 invite links". */
function links(n: number, kind: string): string {
  return `${n} ${kind} link${n === 1 ? "" : "s"}`;
}

/**
 * Members ({n}) (6b spec UX 1b): every member in the server's order, with an
 * initials avatar, the name (a **You** badge on your own row), the email under
 * it and a role badge. For owners and admins, rows they may act on end in a
 * menu: **Make admin** or **Make member** (at once, no confirmation) and
 * **Remove from church** (after a confirmation that says which invite links
 * stop working).
 */
export function MembersList({ actor, churchName }: { actor: { id: string; role: Church["role"] }; churchName: string }) {
  const admin = isAdmin(actor.role);
  const list = useMembers();
  const invites = useInvites({ enabled: admin });
  const changeRole = useChangeRole();
  const remove = useRemoveMember();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [removing, setRemoving] = useState<Member | null>(null);
  // The confirmation keeps its person while it closes (removing is null by then).
  const [shown, setShown] = useState<Member | null>(null);
  const [revokeReusable, setRevokeReusable] = useState(true);
  // After a removal the row and its menu are gone, so focus goes to the heading.
  const removed = useRef(false);

  const changingId = changeRole.isPending ? changeRole.variables?.userId : undefined;

  let body: ReactNode;
  if (list.data) {
    body = (
      <ul className="divide-y rounded-lg border" aria-label="Members">
        {list.data.items.map((m) => (
          <MemberRow
            key={m.user_id}
            member={m}
            actor={actor}
            busy={changingId === m.user_id}
            onChangeRole={(role) => changeRole.mutate({ userId: m.user_id, role })}
            onRemove={() => {
              removed.current = false;
              setRevokeReusable(true);
              setShown(m);
              setRemoving(m);
            }}
          />
        ))}
      </ul>
    );
  } else if (list.isError) {
    body = <ErrorState error={list.error} onRetry={() => void list.refetch()} retrying={list.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="members-title" className="grid gap-3">
      <div className="grid gap-1">
        <h3 id="members-title" ref={headingRef} tabIndex={-1} className="text-base font-medium outline-none">
          {list.data ? `Members (${list.data.items.length})` : "Members"}
        </h3>
        {admin ? null : <p className="text-sm text-muted-foreground">{MEMBERS_NOTE}</p>}
      </div>
      {body}
      {admin ? (
        <RemoveMemberDialog
          member={removing}
          shown={shown}
          churchName={churchName}
          invites={invites.data}
          revokeReusable={revokeReusable}
          onRevokeReusableChange={setRevokeReusable}
          pending={remove.isPending}
          finalFocus={() => (removed.current ? headingRef.current : true)}
          onOpenChange={(open) => {
            // while the removal runs the confirmation stays open
            if (!open && !remove.isPending) setRemoving(null);
          }}
          onConfirm={(revoke) => {
            if (removing === null) return;
            const userId = removing.user_id;
            remove.mutate(
              { userId, revokeReusable: revoke },
              {
                onSuccess: () => {
                  removed.current = true;
                },
                onError: (e) => {
                  if (e.status === 404) removed.current = true; // removed elsewhere: gone all the same
                },
                onSettled: () => setRemoving((current) => (current?.user_id === userId ? null : current)),
              },
            );
          }}
        />
      ) : null}
    </section>
  );
}

function MemberRow({
  member,
  actor,
  busy,
  onChangeRole,
  onRemove,
}: {
  member: Member;
  actor: { id: string; role: Church["role"] };
  busy: boolean;
  onChangeRole(role: "admin" | "member"): void;
  onRemove(): void;
}) {
  const name = displayName(member);
  const actions = memberActions(actor, member);
  const hasName = name !== member.email;
  return (
    <li className="flex items-center gap-3 px-3 py-3 sm:px-4">
      <InitialsAvatar name={member.name} email={member.email} />
      <div className="grid min-w-0 flex-1 gap-0.5">
        <p className="flex flex-wrap items-center gap-2 font-medium [overflow-wrap:anywhere]">
          <span className="min-w-0">{name}</span>
          {member.is_me ? <Badge variant="secondary">You</Badge> : null}
        </p>
        {hasName ? <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{member.email}</p> : null}
      </div>
      <Badge variant={ROLE_BADGE[member.role]} className="shrink-0">
        {roleLabel(member.role)}
      </Badge>
      {actions.changeRoleTo !== null || actions.canRemove ? (
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label={`Actions for ${name}`}
            disabled={busy}
            aria-busy={busy || undefined}
            className={cn(buttonVariants({ variant: "ghost", size: "icon-lg" }), "size-11 shrink-0")}
          >
            {busy ? (
              <Loader2Icon className="animate-spin" aria-hidden="true" />
            ) : (
              <EllipsisVerticalIcon aria-hidden="true" />
            )}
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-auto min-w-44">
            {actions.changeRoleTo !== null ? (
              <DropdownMenuItem className="min-h-11 md:min-h-0" onClick={() => onChangeRole(actions.changeRoleTo!)}>
                {actions.changeRoleTo === "admin" ? "Make admin" : "Make member"}
              </DropdownMenuItem>
            ) : null}
            {actions.changeRoleTo !== null && actions.canRemove ? <DropdownMenuSeparator /> : null}
            {actions.canRemove ? (
              <DropdownMenuItem variant="destructive" className="min-h-11 md:min-h-0" onClick={() => onRemove()}>
                Remove from church
              </DropdownMenuItem>
            ) : null}
          </DropdownMenuContent>
        </DropdownMenu>
      ) : null}
    </li>
  );
}

/**
 * **Remove from church** (6b spec UX 1b): says what the removal does to the
 * person's access and to the invite links, and offers (checked) to revoke the
 * church's other reusable links too, since a reusable link would let the
 * removed person rejoin. The counts come from Pending invites when it has
 * loaded; otherwise the sentences speak generally.
 */
function RemoveMemberDialog({
  member,
  shown,
  churchName,
  invites,
  revokeReusable,
  onRevokeReusableChange,
  pending,
  finalFocus,
  onOpenChange,
  onConfirm,
}: {
  member: Member | null;
  shown: Member | null;
  churchName: string;
  invites: InviteList | undefined;
  revokeReusable: boolean;
  onRevokeReusableChange(value: boolean): void;
  pending: boolean;
  finalFocus(): HTMLElement | null | true;
  onOpenChange(open: boolean): void;
  onConfirm(revokeReusable: boolean): void;
}) {
  const name = shown ? displayName(shown) : "";
  const made = shown && invites ? invitesCreatedBy(invites.items, shown.user_id) : null;
  const others = shown && invites ? otherReusableInvites(invites.items, shown.user_id) : null;
  const showBox = others === null || others > 0;
  let sentence: string | null;
  if (made === null) sentence = `Any invite links ${name} created will stop working.`;
  else if (made === 0) sentence = null;
  else sentence = `The ${links(made, "invite")} ${name} created will stop working.`;
  return (
    <ConfirmDialog
      open={member !== null}
      onOpenChange={onOpenChange}
      title={`Remove ${name}?`}
      description={`${name} will lose access to ${churchName}. Services they saved stay in the archive.`}
      confirmLabel="Remove member"
      pendingLabel="Removing…"
      destructive
      pending={pending}
      finalFocus={finalFocus}
      onConfirm={() => onConfirm(showBox && revokeReusable)}
    >
      {sentence !== null || showBox ? (
        <div className="grid gap-3 text-sm">
          {sentence !== null ? <p className="text-muted-foreground">{sentence}</p> : null}
          {showBox ? (
            <div className="grid gap-1">
              <label className="flex min-h-11 cursor-pointer items-start gap-3 py-1">
                <input
                  type="checkbox"
                  className="mt-0.5 size-5 shrink-0 accent-primary"
                  checked={revokeReusable}
                  disabled={pending}
                  aria-describedby="remove-revoke-help"
                  onChange={(event) => onRevokeReusableChange(event.target.checked)}
                />
                <span className="font-medium">
                  {others === null ? "Also revoke every reusable invite link" : `Also revoke the ${links(others, "reusable invite")}`}
                </span>
              </label>
              <p id="remove-revoke-help" className="text-muted-foreground">
                Anyone with a reusable link, including {name}, can use it to rejoin until it expires. You can create a
                new link for everyone else.
              </p>
            </div>
          ) : null}
        </div>
      ) : null}
    </ConfirmDialog>
  );
}
````

**Create `frontend/src/components/settings/people/people-settings-page.tsx`:**

````tsx
"use client";

import { useChurch } from "@/lib/church-context";
import { useMeContext } from "@/lib/me-context";

import { MembersList } from "./members-list";

/**
 * `/settings/people` (slice 6b-2a; 6b spec UX §1): everyone in the church,
 * with emails, for every role; owners and admins also change roles and
 * remove people.
 */
export function PeopleSettingsPage() {
  const church = useChurch();
  const me = useMeContext();
  return (
    <section aria-labelledby="people-title" className="grid gap-6">
      <div className="grid gap-1">
        <h2 id="people-title" className="text-lg font-semibold">
          People
        </h2>
        <p className="text-sm text-muted-foreground">Everyone in {church.name} can see this list.</p>
      </div>
      <MembersList actor={{ id: me.user.id, role: church.role }} churchName={church.name} />
    </section>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/people/page.tsx`:**

````tsx
"use client";

import { PeopleSettingsPage } from "@/components/settings/people/people-settings-page";

/** Settings → People: the church's members and invite links (slice 6b-2a). */
export default function PeopleSettingsRoute() {
  return <PeopleSettingsPage />;
}
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/components/settings/people/people-settings-page.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  14 passed (14)
```
```
typecheck 0
lint 0
```
```
 Test Files  113 passed (113)
      Tests  994 passed (994)
```

- [ ] **Step 5: Commit**

```bash
git add "frontend/src/app/(signed-in)/(church)/settings/people/page.tsx" frontend/src/components/settings/people/people-settings-page.tsx frontend/src/components/settings/people/members-list.tsx frontend/src/components/settings/people/people-settings-page.test.tsx
git commit -q -m "Slice 6b-2a: Settings > People, the members, roles and removal" -m "/settings/people: everyone in the church with emails, for every role,
with initials, a You badge and role badges. Owners and admins get a menu
on the rows they may act on: Make admin or Make member at once, and
Remove from church after a confirmation that says which invite links stop
working and offers, checked, to revoke the other reusable links. A role
refusal is toasted and turns the page read-only; a lost church is the
app's; a failed list shows Retry." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2235 passed, 48 skipped`; frontend `994 passed` in 113 files.

### Task 5: Invite someone, the link panel and Pending invites (S UX 1a, 1c; Testing → Frontend DOM "Create invite", "Pending invites"; acceptance 14; clarifications 7, 9-12)

**Files:**
- Create: `frontend/src/components/settings/people/create-invite-form.tsx`, `frontend/src/components/settings/people/invite-link-panel.tsx`, `frontend/src/components/settings/people/pending-invites-list.tsx`
- Modify: `frontend/src/components/settings/people/people-settings-page.tsx`, `frontend/src/components/settings/people/people-settings-page.test.tsx`

A member sees neither section; an admin sees Invite someone, Members and Pending invites in that order, the empty state first. **Create invite link** sends `{"role":"member","email":null,"reusable":false}` with an `Idempotency-Key` (a new one for each click) and `X-Church-Id`; the panel shows `http://localhost:3000/join?code=abc` (jsdom's origin) with **Copy link** focused, "Invite link created." for screen readers, the single-use sentence, and no **Share…** without `navigator.share`; Copy link puts the link on the clipboard and toasts "Link copied"; **Done** hides the panel and returns focus to the button, and the invite stays listed. An admin, reusable link gets its sentence and the form resets. Typing an email turns Reusable off and disabled, with "A link for one email address works once.", and sends the email trimmed. A 409 `invite_exists` or `conflict`, and a 422 naming the email, show under Email (focused), not as a toast, and clear when the email changes. **Share…** appears where the device shares, with S's words. Pending invites shows each row's email or "Anyone with the link", role, type, "Expires in 7 days" (the full date and time as its tooltip), and its maker or "a former member"; a row's Copy link copies its own link, and shows it selected when copying is refused; Revoke asks first, sends `DELETE /invites/{id}`, and the list empties with focus on its heading. "Invite link created." sits in an `aria-live="polite"` region; a row's Copy link is named "Copied ✓" while that shows; the panel closes when its invite is revoked. Inside the real `(church)` layout, a refused revoke whose profile refetch says member turns the page read-only (no Invite someone, no menus, no Pending invites) and leaves no invite list in the cache. The tests whose fake `GET /invites` must list a new invite use `invitesServer`, since the panel now follows the list.

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/components/settings/people/people-settings-page.test.tsx`, replace:**

````tsx

import { MEMBERS_NOTE } from "./members-list";
````

**with:**

````tsx

import { EMAIL_HELP, INVITE_CREATED, ONE_EMAIL_ONCE, REUSABLE_HELP, ROLE_HELP } from "./create-invite-form";
import { MEMBERS_NOTE } from "./members-list";
````

**In `frontend/src/components/settings/people/people-settings-page.test.tsx`, replace:**

````tsx
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
````

**with:**

````tsx
import ChurchLayout from "@/app/(signed-in)/(church)/layout";
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
````

**In `frontend/src/components/settings/people/people-settings-page.test.tsx`, replace:**

````tsx
import { keys } from "@/lib/queries/keys";
````

**with:**

````tsx
import { keys } from "@/lib/queries/keys";
import { ACTIVE_CHURCH_KEY } from "@/lib/storage";
````

**In `frontend/src/components/settings/people/people-settings-page.test.tsx`, replace:**

````tsx
import { church, invite, inviteList, me, memberList, PEOPLE } from "@/test/fixtures";
````

**with:**

````tsx
import { church, churchProfile, invite, inviteList, me, memberList, PEOPLE } from "@/test/fixtures";
````

**Append to `frontend/src/components/settings/people/people-settings-page.test.tsx`:**

````tsx

const CODE_FREE = invite();
const NEW_LINK = "http://localhost:3000/join?code=abc";

function invitesSent(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/invites"));
}

function inviteRows() {
  return within(screen.getByRole("list", { name: "Pending invites" })).getAllByRole("listitem");
}

/** A fake `/invites`: `POST` adds the answer first, `DELETE` revokes, `GET` lists what is left. */
function invitesServer(initial: Invite[] = []) {
  let items = [...initial];
  return {
    list: () => inviteList(items),
    add: (made: Invite) => () => {
      items = [made, ...items.filter((i) => i.id !== made.id)];
      return { status: 201, body: made };
    },
    revoke: (id: string) => () => {
      items = items.filter((i) => i.id !== id);
      return { revoked: true };
    },
  };
}

describe("Settings → People: Invite someone and Pending invites (slice 6b-2a)", () => {
  it("shows a member neither the invite form nor the pending invites", async () => {
    renderPage("member");
    await screen.findByRole("heading", { name: "Members (5)" });
    expect(screen.queryByRole("heading", { name: "Invite someone" })).toBeNull();
    expect(screen.queryByRole("heading", { name: /^Pending invites/ })).toBeNull();
    expect(screen.queryByRole("button", { name: "Create invite link" })).toBeNull();
  });

  it("puts Invite someone, Members and Pending invites in that order for an admin", async () => {
    renderPage("admin");
    await screen.findByRole("heading", { name: "Pending invites (0)" });
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Invite someone",
      "Members (5)",
      "Pending invites (0)",
    ]);
    expect(screen.getByText("No pending invites")).toBeInTheDocument();
    expect(screen.getByText("Create an invite link above to add someone to Grace.")).toBeInTheDocument();
  });

  it("creates a single-use member link, shows it with Copy link focused, and copies it", async () => {
    const server = invitesServer();
    const { api, user } = renderPage("admin", { "GET /invites": server.list, "POST /invites": server.add(CODE_FREE) });
    const form = within((await screen.findByRole("heading", { name: "Invite someone" })).closest("section")!);
    expect(form.getByRole("radio", { name: /^Member/ })).toBeChecked();
    expect(form.getByRole("radio", { name: /^Member/ })).toHaveAccessibleDescription(ROLE_HELP.member);
    expect(form.getByRole("radio", { name: /^Admin/ })).toHaveAccessibleDescription(ROLE_HELP.admin);
    expect(form.getByLabelText("Email (optional)")).toHaveAccessibleDescription(EMAIL_HELP);
    expect(form.getByRole("checkbox", { name: "Reusable for 7 days" })).toHaveAccessibleDescription(REUSABLE_HELP);
    await user.click(form.getByRole("button", { name: "Create invite link" }));

    const panel = await screen.findByRole("group", { name: "Invite link ready" });
    expect(within(panel).getByLabelText("Invite link")).toHaveValue(NEW_LINK);
    await waitFor(() => expect(within(panel).getByRole("button", { name: "Copy link" })).toHaveFocus());
    expect(screen.getByText(INVITE_CREATED).closest('[aria-live="polite"]')).not.toBeNull();
    expect(within(panel).getByText(/^Anyone who opens this link can join Grace as a member\. It works once and expires .+\.$/)).toBeInTheDocument();
    const post = invitesSent(api, "POST")[0];
    expect(post.body).toEqual({ role: "member", email: null, reusable: false });
    expect(post.headers["idempotency-key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(post.headers["x-church-id"]).toBe(church().id);

    await user.click(within(panel).getByRole("button", { name: "Copy link" }));
    expect(await screen.findByText("Link copied")).toBeInTheDocument();
    expect(await navigator.clipboard.readText()).toBe(NEW_LINK);
    expect(within(panel).getByRole("button", { name: "Copied ✓" })).toBeInTheDocument();
    expect(within(panel).queryByRole("button", { name: "Share…" })).toBeNull();

    await waitFor(() => expect(inviteRows()).toHaveLength(1));
    await user.click(within(panel).getByRole("button", { name: "Done" }));
    expect(screen.queryByRole("group", { name: "Invite link ready" })).toBeNull();
    expect(form.getByRole("button", { name: "Create invite link" })).toHaveFocus();
    expect(inviteRows()).toHaveLength(1);
  });

  it("sends an admin, reusable link with a new key each time, and says who can use it", async () => {
    const reusable = invite({ id: "c0000000-0000-4000-8000-000000000009", code: "r-123", role: "admin", reusable: true });
    const server = invitesServer();
    const { api, user } = renderPage("admin", { "GET /invites": server.list, "POST /invites": server.add(reusable) });
    const form = within((await screen.findByRole("heading", { name: "Invite someone" })).closest("section")!);
    await user.click(form.getByRole("radio", { name: /^Admin/ }));
    await user.click(form.getByRole("checkbox", { name: "Reusable for 7 days" }));
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    const panel = await screen.findByRole("group", { name: "Invite link ready" });
    expect(within(panel).getByText(/^Anyone with this link can join Grace as an admin until .+\. Share it only with people you trust\.$/)).toBeInTheDocument();
    expect(form.getByRole("radio", { name: /^Member/ })).toBeChecked();
    expect(form.getByRole("checkbox", { name: "Reusable for 7 days" })).not.toBeChecked();
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    await waitFor(() => expect(invitesSent(api, "POST")).toHaveLength(2));
    const [first, second] = invitesSent(api, "POST");
    expect(first.body).toEqual({ role: "admin", email: null, reusable: true });
    expect(second.body).toEqual({ role: "member", email: null, reusable: false });
    expect(first.headers["idempotency-key"]).not.toBe(second.headers["idempotency-key"]);
  });

  it("turns Reusable off while an email is typed, and sends the email trimmed", async () => {
    const bound = invite({ email: "b@example.com" });
    const server = invitesServer();
    const { api, user } = renderPage("admin", { "GET /invites": server.list, "POST /invites": server.add(bound) });
    const form = within((await screen.findByRole("heading", { name: "Invite someone" })).closest("section")!);
    const box = form.getByRole("checkbox", { name: "Reusable for 7 days" });
    await user.click(box);
    expect(box).toBeChecked();
    await user.type(form.getByLabelText("Email (optional)"), " b@example.com ");
    expect(box).toBeDisabled();
    expect(box).not.toBeChecked();
    expect(box).toHaveAccessibleDescription(ONE_EMAIL_ONCE);
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    const panel = await screen.findByRole("group", { name: "Invite link ready" });
    expect(invitesSent(api, "POST")[0].body).toEqual({ role: "member", email: "b@example.com", reusable: false });
    expect(within(panel).getByText(/^Only b@example\.com can use this link to join Grace as a member\. It works once and expires .+\.$/)).toBeInTheDocument();
    expect(form.getByLabelText("Email (optional)")).toHaveValue("");
  });

  it("says under Email when the address has a pending invite or is a member, and focuses it", async () => {
    const pending = "There's already a pending invite for b@example.com. Copy its link below or revoke it first.";
    const { api, user } = renderPage("admin", { "POST /invites": fakeError(409, "invite_exists", pending) });
    const form = within((await screen.findByRole("heading", { name: "Invite someone" })).closest("section")!);
    const email = form.getByLabelText("Email (optional)");
    await user.type(email, "b@example.com");
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    expect(await form.findByRole("alert")).toHaveTextContent(pending);
    await waitFor(() => expect(email).toHaveFocus());
    expect(email).toHaveAttribute("aria-invalid", "true");
    expect(email).toHaveValue("b@example.com");
    expect(screen.queryByText(pending, { selector: "[data-sonner-toast] *" })).toBeNull();

    api.set("POST /invites", fakeError(409, "conflict", "b@example.com is already a member of this church."));
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    expect(await form.findByText("b@example.com is already a member of this church.")).toBeInTheDocument();

    api.set("POST /invites", fakeError(422, "invalid_request", "Enter a valid email address.", { fields: { email: "Enter a valid email address." } }));
    await user.click(form.getByRole("button", { name: "Create invite link" }));
    expect(await form.findByText("Enter a valid email address.")).toBeInTheDocument();
    await user.type(email, "x");
    expect(form.queryByRole("alert")).toBeNull();
  });

  it("offers Share on a device that can share, with the church's words and the link", async () => {
    const share = vi.fn(async () => {});
    Object.defineProperty(navigator, "share", { value: share, configurable: true });
    try {
      const server = invitesServer();
      const { user } = renderPage("admin", { "GET /invites": server.list, "POST /invites": server.add(CODE_FREE) });
      await user.click(await screen.findByRole("button", { name: "Create invite link" }));
      const panel = await screen.findByRole("group", { name: "Invite link ready" });
      await user.click(within(panel).getByRole("button", { name: "Share…" }));
      expect(share).toHaveBeenCalledWith({
        title: "Join Grace",
        text: "You're invited to plan worship with Grace.",
        url: NEW_LINK,
      });
    } finally {
      delete (navigator as { share?: unknown }).share;
    }
  });

  it("lists pending invites with their role, type, expiry and maker, and copies a row's link", async () => {
    const items = [
      invite({ id: "c0000000-0000-4000-8000-000000000001", email: "b@example.com", role: "admin", created_by: ANN }),
      invite({ id: "c0000000-0000-4000-8000-000000000002", code: "r-1", reusable: true, created_by: null }),
    ];
    const { user } = renderPage("admin", { "GET /invites": inviteList(items) });
    await screen.findByRole("heading", { name: "Pending invites (2)" });
    expect(inviteRows().map((r) => r.textContent)).toEqual([
      "b@example.comAdminSingle useExpires in 7 days · Created by Ann AdminCopy linkRevoke",
      "Anyone with the linkMemberReusableExpires in 7 days · Created by a former memberCopy linkRevoke",
    ]);
    const expiry = within(inviteRows()[0]).getByText("Expires in 7 days");
    expect(expiry).toHaveAttribute("title", expect.stringMatching(/^[A-Z][a-z]{2} \d{1,2}, \d{4}, \d{1,2}:\d{2} [AP]M$/));
    expect(expiry).toHaveAttribute("aria-label", `Expires ${expiry.getAttribute("title")}`);
    await user.click(screen.getByRole("button", { name: "Copy link for Anyone with the link" }));
    expect(await navigator.clipboard.readText()).toBe("http://localhost:3000/join?code=r-1");
    expect(within(inviteRows()[1]).getByRole("button", { name: "Copied ✓" })).toBeInTheDocument();
  });

  it("shows a row's link, selected, when copying is refused", async () => {
    const { user } = renderPage("admin", { "GET /invites": inviteList([CODE_FREE]) });
    const copy = await screen.findByRole("button", { name: "Copy link for Anyone with the link" });
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValue(new DOMException("Not allowed", "NotAllowedError"));
    const realExecCommand = document.execCommand;
    document.execCommand = vi.fn(() => false);
    try {
      await user.click(copy);
      const link = await screen.findByRole("textbox", { name: "Invite link for Anyone with the link" });
      expect(link).toHaveValue(NEW_LINK);
      await waitFor(() => expect(link).toHaveFocus());
      expect(await screen.findByText("Couldn't copy. The link is selected; copy it from there.")).toBeInTheDocument();
    } finally {
      document.execCommand = realExecCommand;
    }
  });

  it("revokes an invite after asking, and the list empties", async () => {
    const server = invitesServer([CODE_FREE]);
    const { api, user } = renderPage("admin", {
      "GET /invites": server.list,
      [`DELETE /invites/${CODE_FREE.id}`]: server.revoke(CODE_FREE.id),
    });
    await user.click(await screen.findByRole("button", { name: "Revoke the invite for Anyone with the link" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Revoke this invite?" });
    expect(dialog).toHaveAccessibleDescription("The link will stop working. People who already joined stay in the church.");
    await user.click(within(dialog).getByRole("button", { name: "Revoke invite" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(invitesSent(api, "DELETE").map((r) => r.path)).toEqual([`/invites/${CODE_FREE.id}`]);
    expect(await screen.findByText("No pending invites")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Pending invites (0)" })).toHaveFocus());
  });

  it("clears the link panel when its invite is revoked", async () => {
    const server = invitesServer();
    const { user } = renderPage("admin", {
      "GET /invites": server.list,
      "POST /invites": server.add(CODE_FREE),
      [`DELETE /invites/${CODE_FREE.id}`]: server.revoke(CODE_FREE.id),
    });
    await user.click(await screen.findByRole("button", { name: "Create invite link" }));
    await screen.findByRole("group", { name: "Invite link ready" });
    await user.click(await screen.findByRole("button", { name: "Revoke the invite for Anyone with the link" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Revoke this invite?" });
    await user.click(within(dialog).getByRole("button", { name: "Revoke invite" }));
    await waitFor(() => expect(screen.queryByRole("group", { name: "Invite link ready" })).toBeNull());
    expect(screen.queryByDisplayValue(NEW_LINK)).toBeNull();
    expect(screen.queryByText(INVITE_CREATED)).toBeNull();
  });

  it("turns read-only inside the church layout once GET /church says member after a refusal, and drops the codes", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, church().id);
    let role: Church["role"] = "admin";
    const api = installFakeApi({
      "GET /church": () => churchProfile({ role }),
      "GET /members": () => memberList(role),
      "GET /invites": inviteList([CODE_FREE]),
      [`DELETE /invites/${CODE_FREE.id}`]: () => {
        role = "member"; // demoted elsewhere just before
        return fakeError(403, "forbidden", "Only church admins can do this.");
      },
    });
    const { user, queryClient } = renderWithProviders(
      <>
        <ChurchLayout>
          <SettingsLayout>
            <PeopleSettingsRoute />
          </SettingsLayout>
        </ChurchLayout>
        <Toaster />
      </>,
      { me: me(), path: "/settings/people" },
    );
    await user.click(await screen.findByRole("button", { name: "Revoke the invite for Anyone with the link" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Revoke this invite?" });
    await user.click(within(dialog).getByRole("button", { name: "Revoke invite" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(MEMBERS_NOTE)).toBeInTheDocument());
    expect(screen.getByRole("heading", { level: 2, name: "People" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Invite someone" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Actions for / })).toBeNull();
    expect(screen.queryByRole("heading", { name: /^Pending invites/ })).toBeNull();
    expect(api.requests.filter((r) => r.path === "/church")).toHaveLength(2);
    expect(queryClient.getQueryData(keys.invites(church().id))).toBeUndefined();
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/people/people-settings-page.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`
**Expected:** the form's constants do not exist yet, so the file cannot load:
```
 FAIL  |dom| src/components/settings/people/people-settings-page.test.tsx [ src/components/settings/people/people-settings-page.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: The form, the panel, the list, and the page shows them to owners and admins**

**Create `frontend/src/components/settings/people/invite-link-panel.tsx`:**

````tsx
"use client";

import { useEffect, useRef } from "react";

import { CopyLinkButton } from "@/components/app/copy-link-button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Invite } from "@/lib/api/types";
import { formatDateTime, inviteSummary } from "@/lib/settings/people";
import { buildInviteUrl } from "@/lib/urls";

/**
 * **Invite link ready** (6b spec UX 1a): the new link in a read-only box (it
 * scrolls inside the box, never the page), **Copy link** (focused when the
 * panel opens), **Share…** where the device can share (phones), who can use
 * the link and until when, and **Done**. The invite stays in Pending invites.
 */
export function InviteLinkPanel({ invite, churchName, onDone }: { invite: Invite; churchName: string; onDone(): void }) {
  const url = buildInviteUrl(invite.code);
  const inputRef = useRef<HTMLInputElement>(null);
  const copyRef = useRef<HTMLButtonElement>(null);
  const canShare = typeof navigator !== "undefined" && typeof navigator.share === "function";

  useEffect(() => {
    copyRef.current?.focus();
  }, [invite.id]);

  function selectLink() {
    inputRef.current?.focus();
    inputRef.current?.select();
  }

  return (
    <div role="group" aria-labelledby="invite-ready-title" className="grid gap-3 rounded-lg border bg-muted/40 p-3">
      <h4 id="invite-ready-title" className="text-sm font-medium">
        Invite link ready
      </h4>
      <div className="grid gap-1.5">
        <Label htmlFor="invite-link">Invite link</Label>
        <Input
          id="invite-link"
          ref={inputRef}
          readOnly
          value={url}
          className="h-11 font-mono"
          onFocus={(event) => event.currentTarget.select()}
        />
      </div>
      <p className="text-sm text-muted-foreground">{inviteSummary(invite, churchName, (iso) => formatDateTime(iso))}</p>
      <div className="flex flex-col gap-2 sm:flex-row">
        <CopyLinkButton ref={copyRef} text={url} onCopyFailed={selectLink} size="touch" className="w-full sm:w-fit" />
        {canShare ? (
          <Button
            type="button"
            variant="outline"
            size="touch"
            className="w-full sm:w-fit"
            onClick={() => {
              navigator
                .share({ title: `Join ${churchName}`, text: `You're invited to plan worship with ${churchName}.`, url })
                .catch(() => {}); // a cancelled share does nothing
            }}
          >
            Share…
          </Button>
        ) : null}
        <Button type="button" variant="ghost" size="touch" className="w-full sm:w-fit" onClick={() => onDone()}>
          Done
        </Button>
      </div>
    </div>
  );
}
````

**Create `frontend/src/components/settings/people/create-invite-form.tsx`:**

````tsx
"use client";

import { useRef, useState, type FormEvent } from "react";

import { PendingButton } from "@/components/app/pending-button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { Invite, InviteBody } from "@/lib/api/types";
import { inviteFieldError, useCreateInvite, useInvites } from "@/lib/queries/people";

import { InviteLinkPanel } from "./invite-link-panel";

export const ROLE_HELP = {
  member: "Can build, save and email services, and edit hymns.",
  admin: "Can also change church settings, invite people and manage members.",
} as const;
export const EMAIL_HELP = "Only the Google account with this email will be able to use the link.";
export const REUSABLE_HELP = "Let several people join with the same link. Otherwise the link works once.";
export const ONE_EMAIL_ONCE = "A link for one email address works once.";
export const INVITE_CREATED = "Invite link created.";

type Role = InviteBody["role"];
type FieldErrors = Partial<Record<"email" | "reusable", string>>;

/**
 * Invite someone (owners and admins; 6b spec UX 1a): the role (Member by
 * default), an optional email (only that Google account can use the link)
 * and "Reusable for 7 days" (off, and off while an email is typed). **Create
 * invite link** sends a new request each time; the link then shows below.
 */
export function CreateInviteForm({ churchName }: { churchName: string }) {
  const create = useCreateInvite();
  const invites = useInvites({ enabled: true });
  const emailRef = useRef<HTMLInputElement>(null);
  const reusableRef = useRef<HTMLInputElement>(null);
  const submitRef = useRef<HTMLButtonElement>(null);
  const [role, setRole] = useState<Role>("member");
  const [email, setEmail] = useState("");
  const [reusable, setReusable] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [created, setCreated] = useState<Invite | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const emailBound = email.trim() !== "";
  // A link revoked since (in Pending invites, or by a removal) leaves the panel too.
  const shown =
    created !== null && (invites.data === undefined || invites.data.items.some((i) => i.id === created.id))
      ? created
      : null;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (create.isPending) return;
    setAnnouncement("");
    const body: InviteBody = { role, email: emailBound ? email.trim() : null, reusable: emailBound ? false : reusable };
    create.mutate(body, {
      onSuccess: (invite) => {
        setRole("member");
        setEmail("");
        setReusable(false);
        setErrors({});
        setCreated(invite);
        setAnnouncement(INVITE_CREATED);
      },
      onError: (e) => {
        const found = inviteFieldError(e);
        if (found === null) return;
        setErrors({ [found.field]: found.message });
        (found.field === "email" ? emailRef : reusableRef).current?.focus();
      },
    });
  }

  return (
    <section aria-labelledby="invite-title" className="grid gap-4 rounded-lg border p-4">
      <h3 id="invite-title" className="text-base font-medium">
        Invite someone
      </h3>
      <form onSubmit={onSubmit} noValidate className="grid gap-4">
        <div className="grid gap-1.5">
          <span id="invite-role-label" className="text-sm font-medium">
            Role
          </span>
          <RadioGroup
            aria-labelledby="invite-role-label"
            value={role}
            onValueChange={(value) => setRole(value as Role)}
            className="grid gap-2 sm:grid-cols-2"
          >
            {(["member", "admin"] as const).map((value) => (
              <label
                key={value}
                className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border p-3 has-data-checked:border-primary"
              >
                <RadioGroupItem value={value} aria-describedby={`invite-role-${value}-help`} className="mt-0.5" />
                <span className="grid min-w-0 gap-0.5">
                  <span className="text-sm font-medium">{value === "member" ? "Member" : "Admin"}</span>
                  <span id={`invite-role-${value}-help`} className="text-sm text-muted-foreground">
                    {ROLE_HELP[value]}
                  </span>
                </span>
              </label>
            ))}
          </RadioGroup>
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="invite-email">Email (optional)</Label>
          <Input
            id="invite-email"
            ref={emailRef}
            type="email"
            inputMode="email"
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            maxLength={320}
            value={email}
            className="h-11"
            aria-invalid={errors.email ? true : undefined}
            aria-describedby={errors.email ? "invite-email-error invite-email-help" : "invite-email-help"}
            onChange={(event) => {
              setEmail(event.target.value);
              if (errors.email || errors.reusable) setErrors({});
            }}
          />
          {errors.email ? (
            <p id="invite-email-error" role="alert" className="text-sm text-destructive">
              {errors.email}
            </p>
          ) : null}
          <p id="invite-email-help" className="text-sm text-muted-foreground">
            {EMAIL_HELP}
          </p>
        </div>
        <div className="grid gap-1">
          <label className={`flex min-h-11 items-center gap-3 ${emailBound ? "opacity-70" : "cursor-pointer"}`}>
            <input
              ref={reusableRef}
              type="checkbox"
              className="size-5 shrink-0 accent-primary"
              checked={!emailBound && reusable}
              disabled={emailBound}
              aria-describedby="invite-reusable-help"
              aria-invalid={errors.reusable ? true : undefined}
              onChange={(event) => {
                setReusable(event.target.checked);
                if (errors.reusable) setErrors({});
              }}
            />
            <span className="text-sm font-medium">Reusable for 7 days</span>
          </label>
          {errors.reusable ? (
            <p role="alert" className="text-sm text-destructive">
              {errors.reusable}
            </p>
          ) : null}
          <p id="invite-reusable-help" className="text-sm text-muted-foreground">
            {emailBound ? ONE_EMAIL_ONCE : REUSABLE_HELP}
          </p>
        </div>
        <PendingButton
          ref={submitRef}
          type="submit"
          size="touch"
          className="w-full sm:w-fit"
          pending={create.isPending}
          pendingLabel="Creating…"
        >
          Create invite link
        </PendingButton>
      </form>
      <p className="sr-only" aria-live="polite">
        {shown ? announcement : ""}
      </p>
      {shown ? (
        <InviteLinkPanel
          invite={shown}
          churchName={churchName}
          onDone={() => {
            setCreated(null);
            setAnnouncement("");
            submitRef.current?.focus();
          }}
        />
      ) : null}
    </section>
  );
}
````

**Create `frontend/src/components/settings/people/pending-invites-list.tsx`:**

````tsx
"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { CopyLinkButton } from "@/components/app/copy-link-button";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { Invite } from "@/lib/api/types";
import { roleLabel } from "@/lib/church";
import { useInvites, useRevokeInvite } from "@/lib/queries/people";
import { displayName, formatExpiry } from "@/lib/settings/people";
import { buildInviteUrl } from "@/lib/urls";

const ANYONE = "Anyone with the link";

/**
 * Pending invites ({n}) (owners and admins; 6b spec UX 1c): the live links,
 * newest first, each with who can use it, its role and type, when it
 * expires and who made it, **Copy link** and **Revoke** (after a
 * confirmation). Used single-use links, expired and revoked ones are not listed.
 */
export function PendingInvitesList({ churchName }: { churchName: string }) {
  const list = useInvites({ enabled: true });
  const revoke = useRevokeInvite();
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [revoking, setRevoking] = useState<Invite | null>(null);
  // After a revoke the row and its button are gone, so focus goes to the heading.
  const revoked = useRef(false);

  let body: ReactNode;
  if (list.data) {
    body =
      list.data.items.length === 0 ? (
        <EmptyState title="No pending invites" description={`Create an invite link above to add someone to ${churchName}.`} />
      ) : (
        <ul className="divide-y rounded-lg border" aria-label="Pending invites">
          {list.data.items.map((invite) => (
            <InviteRow
              key={invite.id}
              invite={invite}
              onRevoke={() => {
                revoked.current = false;
                setRevoking(invite);
              }}
            />
          ))}
        </ul>
      );
  } else if (list.isError) {
    body = <ErrorState error={list.error} onRetry={() => void list.refetch()} retrying={list.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="invites-title" className="grid gap-3">
      <h3 id="invites-title" ref={headingRef} tabIndex={-1} className="text-base font-medium outline-none">
        {list.data ? `Pending invites (${list.data.items.length})` : "Pending invites"}
      </h3>
      {body}
      <ConfirmDialog
        open={revoking !== null}
        onOpenChange={(open) => {
          // while the revoke runs the confirmation stays open
          if (!open && !revoke.isPending) setRevoking(null);
        }}
        title="Revoke this invite?"
        description="The link will stop working. People who already joined stay in the church."
        confirmLabel="Revoke invite"
        pendingLabel="Revoking…"
        destructive
        pending={revoke.isPending}
        finalFocus={() => (revoked.current ? headingRef.current : true)}
        onConfirm={() => {
          if (revoking === null) return;
          const id = revoking.id;
          revoke.mutate(id, {
            onSuccess: () => {
              revoked.current = true;
            },
            onError: (e) => {
              if (e.status === 404) revoked.current = true; // gone elsewhere: gone all the same
            },
            onSettled: () => setRevoking((current) => (current?.id === id ? null : current)),
          });
        }}
      />
    </section>
  );
}

function InviteRow({ invite, onRevoke }: { invite: Invite; onRevoke(): void }) {
  const who = invite.email ?? ANYONE;
  const url = buildInviteUrl(invite.code);
  const expiry = formatExpiry(invite.expires_at);
  const creator = invite.created_by ? displayName(invite.created_by) : null;
  const [showLink, setShowLink] = useState(false);
  const linkRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!showLink) return;
    linkRef.current?.focus();
    linkRef.current?.select();
  }, [showLink]);

  return (
    <li className="grid gap-2 px-3 py-3 sm:px-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="min-w-0 font-medium [overflow-wrap:anywhere]">{who}</span>
        <Badge variant="outline">{roleLabel(invite.role)}</Badge>
        <Badge variant="secondary">{invite.reusable ? "Reusable" : "Single use"}</Badge>
      </div>
      <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">
        <time dateTime={invite.expires_at} title={expiry.full} aria-label={`Expires ${expiry.full}`}>
          Expires {expiry.relative}
        </time>
        {creator !== null ? ` · Created by ${creator}` : " · Created by a former member"}
      </p>
      {showLink ? (
        <Input ref={linkRef} readOnly value={url} aria-label={`Invite link for ${who}`} className="h-11 font-mono" />
      ) : null}
      <div className="flex flex-wrap gap-2">
        <CopyLinkButton
          text={url}
          label={`Copy link for ${who}`}
          onCopyFailed={() => {
            if (showLink) linkRef.current?.select();
            else setShowLink(true);
          }}
          variant="outline"
          size="touch"
          className="md:h-8"
        />
        <Button
          type="button"
          variant="destructive"
          size="touch"
          className="md:h-8"
          aria-label={`Revoke the invite for ${who}`}
          onClick={() => onRevoke()}
        >
          Revoke
        </Button>
      </div>
    </li>
  );
}
````

**In `frontend/src/components/settings/people/people-settings-page.tsx`, replace:**

````tsx
import { useChurch } from "@/lib/church-context";
import { useMeContext } from "@/lib/me-context";

import { MembersList } from "./members-list";

/**
 * `/settings/people` (slice 6b-2a; 6b spec UX §1): everyone in the church,
 * with emails, for every role; owners and admins also change roles and
 * remove people.
````

**with:**

````tsx
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useMeContext } from "@/lib/me-context";

import { CreateInviteForm } from "./create-invite-form";
import { MembersList } from "./members-list";
import { PendingInvitesList } from "./pending-invites-list";

/**
 * `/settings/people` (slice 6b-2a; 6b spec UX §1): everyone in the church,
 * with emails, for every role. Owners and admins also see Invite someone
 * above the list and Pending invites below it, change roles and remove
 * people.
````

**In `frontend/src/components/settings/people/people-settings-page.tsx`, replace:**

````tsx
  const me = useMeContext();
````

**with:**

````tsx
  const me = useMeContext();
  const admin = isAdmin(church.role);
````

**In `frontend/src/components/settings/people/people-settings-page.tsx`, replace:**

````tsx
      <MembersList actor={{ id: me.user.id, role: church.role }} churchName={church.name} />
````

**with:**

````tsx
      {admin ? <CreateInviteForm churchName={church.name} /> : null}
      <MembersList actor={{ id: me.user.id, role: church.role }} churchName={church.name} />
      {admin ? <PendingInvitesList churchName={church.name} /> : null}
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/components/settings/people/people-settings-page.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  26 passed (26)
```
```
typecheck 0
lint 0
```
```
 Test Files  113 passed (113)
      Tests  1006 passed (1006)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/people/create-invite-form.tsx frontend/src/components/settings/people/invite-link-panel.tsx frontend/src/components/settings/people/pending-invites-list.tsx frontend/src/components/settings/people/people-settings-page.tsx frontend/src/components/settings/people/people-settings-page.test.tsx
git commit -q -m "Slice 6b-2a: Settings > People, invite links and pending invites" -m "Owners and admins see Invite someone (Member or Admin, an optional email,
Reusable for 7 days) above the members: Create invite link shows the new
link with Copy link (focused), Share on phones, who can use it and until
when, and Done; a pending or member email is said under Email. Pending
invites below the members lists each live link with its role, type,
expiry and maker, Copy link and Revoke (after a confirmation)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2235 passed, 48 skipped`; frontend `1006 passed` in 113 files.

### Task 6: People in the Settings nav (answer 7 of 2026-10-09; S "Settings nav"; acceptance 22's People half)

**Files:**
- Modify: `frontend/src/components/settings/settings-layout.test.tsx`, `frontend/src/components/settings/sections.ts`

- [ ] **Step 1: Update the tests**

The nav lists nine sections, People between Contacts and Account, marks **People** current on its page, and a member sees nine links.

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
      ["Contacts", "/settings/contacts"],
````

**with:**

````tsx
      ["Contacts", "/settings/contacts"],
      ["People", "/settings/people"],
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    ["/settings/account", "Account"],
  ])("marks the section current on its page (slices 6a-2, 6a-3a, 6a-3b, 5b-1, 5b-2): %s", (path, label) => {
````

**with:**

````tsx
    ["/settings/people", "People"],
    ["/settings/account", "Account"],
  ])("marks the section current on its page (slices 6a-2, 6a-3a, 6a-3b, 5b-1, 5b-2, 6b-2a): %s", (path, label) => {
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(8);
````

**with:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(9);
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`
**Expected:**
```
   × the Settings area (slice 6a-1) > shows the heading, who you are in the church, and the sections with the current one marked
   × the Settings area (slice 6a-1) > marks the section current on its page (slices 6a-2, 6a-3a, 6a-3b, 5b-1, 5b-2, 6b-2a): /settings/people
   × the Settings area (slice 6a-1) > shows a member the same sections, and /settings opens Church
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 3 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |dom| src/components/settings/settings-layout.test.tsx > the Settings area (slice 6a-1) > shows the heading, who you are in the church, and the sections with the current one marked
 FAIL  |dom| src/components/settings/settings-layout.test.tsx > the Settings area (slice 6a-1) > marks the section current on its page (slices 6a-2, 6a-3a, 6a-3b, 5b-1, 5b-2, 6b-2a): /settings/people
 FAIL  |dom| src/components/settings/settings-layout.test.tsx > the Settings area (slice 6a-1) > shows a member the same sections, and /settings opens Church
      Tests  3 failed | 8 passed (11)
```

- [ ] **Step 3: Put People between Contacts and Account**

**In `frontend/src/components/settings/sections.ts`, replace:**

````ts
 * and 5b-2 Account after it (6b's People will go between them).
````

**with:**

````ts
 * and 5b-2 Account after it; 6b-2a puts People between them (the owner's 6b
 * answers of 2026-10-09: Church, Hymns, Liturgy, Prayers, Rubric, Bulletin,
 * Contacts, People, Account, then 6b-2b's Danger zone).
````

**In `frontend/src/components/settings/sections.ts`, replace:**

````ts
  { href: "/settings/contacts", label: "Contacts" },
````

**with:**

````ts
  { href: "/settings/contacts", label: "Contacts" },
  { href: "/settings/people", label: "People" },
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  11 passed (11)
```
```
typecheck 0
lint 0
```
```
 Test Files  113 passed (113)
      Tests  1007 passed (1007)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/settings-layout.test.tsx frontend/src/components/settings/sections.ts
git commit -q -m "Slice 6b-2a: People in the Settings nav" -m "SETTINGS_SECTIONS gains People (/settings/people) between Contacts and
Account: Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts,
People, Account (6b-2b adds Danger zone last)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2235 passed, 48 skipped`; frontend `1007 passed` in 113 files.

## Docs, verification, the owner's routine, the PR and the merge (T7-T10)

### Task 7: Docs: the manual check items (clarification 13; answer 2)

**Files:**
- Modify: `docs/manual-verification.md`

"## Slice 6b" gains the 6b-2a items 7-17: the owner's three before the merge (the backup, the counts, the SQL read and not run), the after-deploy check, the phone check in the real church (read only) and in a test church with a second Google account (a single-use link joined in a private window, a role change, a revoke, the removal), the phone screen, and the agent's check. No new `##` heading, so `test_slice1_docs.py`'s pin is unchanged.

- [ ] **Step 1: The items**

**Append to `docs/manual-verification.md`:**

````markdown

**6b-2a** (owner's 6b-2 planning answers of 2026-10-10) brings Settings →
**People** (`/settings/people`: Invite someone, Members, Pending invites;
the People entry between Contacts and Account) and migration
`0009_memberships_one_owner` (at most one owner per church). The owner's
steps around the merge follow `backend/migrations/README.md` → "Before
0009_memberships_one_owner", one step at a time; the results go into
`docs/ops-runbook.md` → "Slice 6b-2a record". The People checks that
change anything run in one of the owner's **test churches**, never the
real one, with a **second Google account the owner controls** (in a
private window). Record counts and what the screens show, never an email
address, an invite code or link, a church id or a database URL.

- [ ] (owner, before the 6b-2a merge) **7.** A fresh backup: the db-backup workflow on `main` finishes green with an artifact `db-backup`.
- [ ] (owner, before the 6b-2a merge) **8.** "Before 0009_memberships_one_owner" step 2's read-only query shows `version` `0008_invites_integrity`, `churches_with_two_owners` `0`, `churches_without_one_owner` `0`, `churches_without_admin` `0` and `one_owner_index` `0`; the other counts are recorded.
- [ ] (owner, before the 6b-2a merge) **9.** The SQL preview the agent shows in full (marked "Read only. Do not run this.") matches step 3 of that section, and the owner has read it without running it.
- [ ] (owner, after 6b-2a) **10.** Step 4's read-only query shows `0009_memberships_one_owner`, `1`; step 2's query again shows the same counts, with `one_owner_index` `1`.
- [ ] (owner, after 6b-2a) **11.** On the phone, in the real church: **Settings** lists Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, **People**, Account. **People** shows "Everyone in {church} can see this list.", **Invite someone**, **Members ({n})** with everyone's email, your row marked **You** and **Owner**, and **Pending invites ({n})**. Nothing is changed here.
- [ ] (owner, after 6b-2a) **12.** In a test church: **Create invite link** (Member, no email, not reusable) shows **Invite link ready** with the link, **Copy link** ("Copied ✓", "Link copied") and, on the phone, **Share…** (the share sheet opens; cancel it). The invite is listed under Pending invites as **Single use**. Open the copied link in a private window, sign in there with the second Google account, and join: the test church opens for it, and its People page shows the members note and no invite form or menus. Back on the owner's People page (pull to reload), the second account is listed as **Member** and the link is gone from Pending invites.
- [ ] (owner, after 6b-2a) **13.** In the test church: the second account's ⋮ menu → **Make admin**: the badge says **Admin** at once, with no question; ⋮ → **Make member**: **Member** again. Your own row and the owner's have no menu.
- [ ] (owner, after 6b-2a) **14.** In the test church: create another link, then **Revoke** it: "Revoke this invite?" → **Revoke invite**, and it leaves Pending invites. Opening it in the private window says "This invite has been revoked."
- [ ] (owner, after 6b-2a) **15.** In the test church: the second account's ⋮ → **Remove from church**: "Remove {name}?" says they lose access and that services they saved stay; **Remove member** removes the row. In the private window, the second account's next tap in the test church says "You no longer have access to {church}." and moves it to another church or the welcome page.
- [ ] (owner, after 6b-2a) **16.** At 375 px (the phone): no sideways scroll on People, even with a long email or the link in its box (the link scrolls inside the box); the keyboard does not cover the Email field while typing; the dialogs fit the screen; every button and menu is easy to tap.
- [ ] (agent, after 6b-2a) **17.** `/health/ready` answers `{"ok":true,"db":"ok"}`; the app's `/settings/people` is served (signed out, it sends you to sign in).
````

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `git diff -- docs/manual-verification.md | grep '^+' | grep -c '—'`
**Expected:**
```
89 passed in <t>s
```
```
0
```

- [ ] **Step 2: Commit**

```bash
git add docs/manual-verification.md
git commit -q -m "Docs: slice 6b-2a's manual check items" -m "docs/manual-verification.md \"Slice 6b\" gains the 6b-2a items: the
owner's backup, read-only counts and the SQL (read, not run) before the
merge; the after-deploy check; People on the phone in the real church
(read only) and in a test church with a second Google account (a
single-use link joined in a private window, a role change, a revoke, the
removal); the phone screen; and the agent's check." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2235 passed, 48 skipped`; frontend `1007 passed` in 113 files.

### Task 8: Verification (agent)

Every `gh` command uses `-R <repo>` (or the session's GitHub tools, with the same effect). Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 4).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

Run: `git status --short | grep -v '^?? .claude/' | wc -l` then `git fetch -q origin && git rev-list --count HEAD..origin/main` then `ls backend/migrations/versions | grep -c '^0'`
**Expected:** `0` (nothing uncommitted); `0`; `9` (with T1's revision). If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 8)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner. If `main` gained a revision after `0008_invites_integrity`, stop: `0009`'s `down_revision` and number must follow it (clarification 2), and the owner's SQL preview changes.
```
0
```
```
0
```
```
9
```

- [ ] **Step 2 (agent): Both suites, Postgres, types, lint, the build**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -1` then `TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres 2>&1 | tail -1` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -cE "Compiled successfully")`
**Expected** (the Postgres line only where a local, throwaway Postgres is at hand; otherwise CI's job is the check; a font `Failed to fetch` in the build: say so and rely on CI):
```
2235 passed, 48 skipped in <t>s
```
```
48 passed, 2235 deselected, 1 warning in <t>s
```
```
 Test Files  113 passed (113)
      Tests  1007 passed (1007)
```
```
typecheck 0
lint 0
```
```
1
```

- [ ] **Step 3 (agent): The API files unchanged, the gates, the paths, the commits**

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null 2>&1) && git status --short -- frontend backend | wc -l` then `git diff origin/main...HEAD -- backend frontend/src docs/manual-verification.md | grep '^+' | grep -c '—'` then `python3 -c "import pathlib; t=pathlib.Path('docs/superpowers/plans/2026-10-10-slice-6b2a-people-page.md').read_text(); print(sum(t.count(c) for c in ('\u2028','\u2029','\ufffe','\uffff')))"` then `git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2` then `git diff --name-only origin/main...HEAD -- .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt requirements.txt pytest.ini app.py streamlit_views streamlit_auth.py streamlit_tenancy.py ui_helpers.py backend/api backend/usecases backend/repos backend/scripts backend/migrations/env.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts frontend/src/lib/queries/client.ts frontend/src/components/ui | wc -l` then `git log --reverse --no-merges --format=%s origin/main..HEAD | grep -v -e '^WIP plan: ' -e '^Plan: '` then `for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"`
**Expected:** `0` (the committed snapshot and types are current: no API change); `0` (no em dash in an added line of code, tests or the checklist); `0` (no U+2028, U+2029, U+FFFE or U+FFFF in this plan); exactly these 35 paths (the 6b-1 record and the 6b-2 amendment ride along until merged); `0` (nothing that must stay untouched changed); the subjects oldest first, then any `Fix: …` lines (the plan's own commits are left out by the `grep`); only `trailer check done`:
```
0
```
```
0
```
```
0
```
```
M	backend/db/models.py
M	backend/migrations/README.md
A	backend/migrations/versions/0009_memberships_one_owner.py
M	backend/tests/test_api_app.py
M	backend/tests/test_integrity.py
M	backend/tests/test_migrations.py
M	backend/tests/test_schema_check.py
M	backend/tests/test_services_postgres.py
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-10-slice-6b2a-people-page.md
M	docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md
A	frontend/src/app/(signed-in)/(church)/settings/people/page.tsx
M	frontend/src/components/app/confirm-dialog.test.tsx
M	frontend/src/components/app/confirm-dialog.tsx
A	frontend/src/components/app/copy-link-button.test.tsx
A	frontend/src/components/app/copy-link-button.tsx
A	frontend/src/components/app/initials-avatar.tsx
A	frontend/src/components/settings/people/create-invite-form.tsx
A	frontend/src/components/settings/people/invite-link-panel.tsx
A	frontend/src/components/settings/people/members-list.tsx
A	frontend/src/components/settings/people/pending-invites-list.tsx
A	frontend/src/components/settings/people/people-settings-page.test.tsx
A	frontend/src/components/settings/people/people-settings-page.tsx
M	frontend/src/components/settings/sections.ts
M	frontend/src/components/settings/settings-layout.test.tsx
M	frontend/src/lib/api/types.ts
A	frontend/src/lib/clipboard.test.tsx
A	frontend/src/lib/clipboard.ts
A	frontend/src/lib/queries/people.ts
A	frontend/src/lib/settings/people.test.ts
A	frontend/src/lib/settings/people.ts
M	frontend/src/lib/urls.test.ts
M	frontend/src/test/fixtures/index.ts
D	streamlit_tests/test_settings_members_invites.py
```
```
0
```
```
Docs: slice 6b-1 record in the ops runbook
Docs: slice 6b spec amendment with the owner's 6b-2 planning answers
Migration 0009_memberships_one_owner: at most one owner per church
Slice 6b-2a: the People rules, copyText and the types
Slice 6b-2a: the People queries, Copy link, initials, and a confirm dialog with a body
Slice 6b-2a: Settings > People, the members, roles and removal
Slice 6b-2a: Settings > People, invite links and pending invites
Slice 6b-2a: People in the Settings nav
Docs: slice 6b-2a's manual check items
```
```
trailer check done
```

- [ ] **Step 4: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_migrations.py` (0009), `test_schema_check.py`, `test_api_app.py`, `test_services_postgres.py`, `test_integrity.py`, `test_models.py`, `streamlit_tests`, CI's `alembic check` | T1 |
| `people.test.ts`, `clipboard.test.tsx`, `urls.test.ts`, the fixtures | T2 |
| `confirm-dialog.test.tsx`, `copy-link-button.test.tsx`, any existing `ConfirmDialog` caller's test | T3 |
| `people-settings-page.test.tsx` (Members) | T4 (the hooks: T3) |
| `people-settings-page.test.tsx` (Invite someone, Pending invites) | T5 (the hooks: T3) |
| `settings-layout.test.tsx` | T6 |
| `test_slice1_docs.py`, `test_docs.py` | T7 |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, slice 6b-2a final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `2235 passed, 48 skipped`; frontend `1007 passed` in 113 files.

### Task 9: Before the PR: the owner's pre-merge routine for 0009 (backup, counts, the SQL) (OWNER + agent; clarification 14)

The owner's steps go **one at a time** (send one, wait for the report or "next"), in plain words. The queries are the ones in `backend/migrations/README.md` → "Before 0009_memberships_one_owner" (pinned by T1's tests); copy them from there, **in full**, into a code block. The agent writes each result into `<scratch>/6b2a-t9-results.md` (not committed). Record numbers and what the screens showed, never a church id, an email address, an invite code or link, a token or a database URL. Nothing here changes data.

**Files:** none.

- [ ] **Step 1 (agent → OWNER, then agent): The backup**

Send:

> The next update (slice 6b-2a) adds the People page and one database change, migration 0009: a church can have at most one owner. Before I open its pull request we do the same three checks as for the last one. Here is the first: may I start a fresh database backup now (the db-backup workflow on main, about a minute)? Nothing else happens yet.

On a clear yes (not replayed):

```bash
gh workflow run db-backup --ref main -R <repo>
RUN=$(gh run list -R <repo> --workflow backup.yml --branch main --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId'); echo "$RUN"
gh run watch "$RUN" -R <repo> --exit-status --interval 15 >/dev/null; echo "backup exit $?"
gh run view "$RUN" -R <repo> --json url,conclusion,createdAt --jq '"\(.conclusion) \(.url) \(.createdAt)"'
gh api "repos/<repo>/actions/runs/$RUN/artifacts" --jq '.artifacts[] | "\(.name) \(.size_in_bytes)"'
```

**Expected:** a run id (started a few seconds ago; if `gh run list` shows an older run, wait and list again); `backup exit 0`; `success <run URL> <UTC time>`; `db-backup <bytes>`. Record the URL, the time and the size. A failure: stop and tell the owner; nothing merges without a green backup.

- [ ] **Step 2 (OWNER, then agent): The owner counts (read-only)**

Send, with README step 2's query pasted **in full** inside a code block:

> Second check: one read-only query; it only counts and changes nothing. Open Supabase → your project → SQL Editor → New query, paste the query below, and press Run. You should see one row with nine values. Please tell me what each column shows: version, churches, deleted_churches, memberships, owners, churches_with_two_owners, churches_without_one_owner, churches_without_admin, one_owner_index.

**Expected:** `version` `0008_invites_integrity`; `churches_with_two_owners` `0`; `churches_without_one_owner` `0`; `churches_without_admin` `0`; `one_owner_index` `0`; the rest are counts to record (`owners` is normally `churches` plus `deleted_churches`). Then:
- `version` not `0008_invites_integrity`, or `one_owner_index` not `0`: stop and tell the owner what it means before going on (another release ran; the migration would refuse or find the index there).
- `churches_with_two_owners` above `0`: stop. Explain: "A church has two owners (only a change made by hand could do that). The update refuses to run over that, safely. The fix is to agree with that church who stays the owner and make the other an admin." Then a second read-only query that names it, for the chat only: `SELECT c.name, c.deleted_at IS NOT NULL AS deleted, count(*) AS owners FROM memberships m JOIN churches c ON c.id = m.church_id WHERE m.role = 'owner' GROUP BY c.id, c.name, c.deleted_at HAVING count(*) > 1;`. On the owner's choice, after a fresh backup, "Church integrity" step 3's `UPDATE` with the ids filled in **in the chat only**, then this step's query again: `0`.
- `churches_without_one_owner` or `churches_without_admin` above `0`: stop (the 6b-1 gate: 0009 only refuses a second owner, so it would not notice a church with none, and 6b-2b's transfer and delete need an owner). Send a second read-only query that names the church, for the chat only: `SELECT c.name, (SELECT count(*) FROM memberships m WHERE m.church_id = c.id AND m.role = 'owner') AS owners, (SELECT count(*) FROM memberships m WHERE m.church_id = c.id AND m.role IN ('owner', 'admin')) AS owners_and_admins FROM churches c WHERE c.deleted_at IS NULL AND ((SELECT count(*) FROM memberships m WHERE m.church_id = c.id AND m.role = 'owner') <> 1 OR NOT EXISTS (SELECT 1 FROM memberships m WHERE m.church_id = c.id AND m.role IN ('owner', 'admin')));`. On the owner's choice of owner, after a fresh backup, "Church integrity" step 4 with the ids filled in **in the chat only**, then this step's query again: `0`.

- [ ] **Step 3 (agent → OWNER): The SQL the migration will run (read only)**

Run (not replayed here; T1 Step 5 runs the same command and T1's tests pin it): `git fetch origin && git status -sb | head -1` then `(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0008_invites_integrity:0009_memberships_one_owner --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//')`
**Expected:** the branch even with `origin/claude/slice-2-plan-4q33le`; exactly the lines of README step 3 (T1 Step 5 quotes them). Send them **all, in one code block, never shortened**, with:

> Third check, and this one is **read only. Do not run this.** These are the lines of SQL Railway will run on the database when the pull request merges, rendered from the branch's code without touching the database; please read them, and do not paste them into the SQL Editor (run there, they would change the database). In plain words: start one transaction; give up after 5 seconds if the memberships table is busy (the old version then keeps running and we retry); a check that stops everything if any church has more than one owner (your count was 0); then the new rule: at most one owner per church; note the new version; finish. No row is changed or deleted and no column changes. Does that look right to you?

Record the owner's answer.

- [ ] **Step 4 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/6b2a-t9-results.md`. A problem the owner reports is a follow-up (and the owner's to decide), not a change made now.

Expected counts after this task: unchanged.

### Task 10: The draft PR, the merge, the after-deploy check, the phone check, the record (OWNER + agent)

**Files:** Modify (Step 12, the records PR): `docs/ops-runbook.md`: insert `### Slice 6b-2a record` right before `## Backups` (after the last record above it, today `### Slice 6b-1 record`, whose table's last row starts `| Follow-ups |`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to open the draft PR**

(not replayed) `gh pr list -R <repo> --head claude/slice-2-plan-4q33le --state open --json number,url` → `[]`. Send the owner exactly this, and wait for a clear yes:

> The People page (slice 6b-2a) is verified on this machine: backend 2235 passed, 48 skipped (2235 and 46 before), and the 48 Postgres tests pass on a throwaway local database; frontend 1007 tests in 113 files (952 in 109 before), typecheck, lint and the production build clean. It adds Settings → People: everyone sees the members with emails; owners and admins invite (single-use links by default, or reusable for 7 days, optionally for one email), copy or share the link, make someone an admin or a member, remove someone, and see and revoke the pending links. With it comes migration 0009 (at most one owner per church), whose checks you have just done. May I open the pull request as a **draft** titled "Slice 6b-2a: Settings > People (invite links, members, pending invites) and migration 0009", so the checks run? Merging stays with you.

- [ ] **Step 2 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/6b2a-pr-body.md" <<'BODY'
Slice 6b-2a: Settings > People and migration 0009_memberships_one_owner (the first of slice 6b-2's two PRs; owner's 6b-2 planning answers of 2026-10-10). Spec: docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md and its amendments of 2026-10-09 and 2026-10-10. Plan: docs/superpowers/plans/2026-10-10-slice-6b2a-people-page.md. No API change, no new package or variable.

- /settings/people, for every role: everyone in the church with emails (initials, You, role badges). Owners and admins: Invite someone (Member or Admin, optional email, Reusable for 7 days; a new Idempotency-Key per click) with the link panel (Copy link, Share on phones, who can use it and until when, Done); Make admin / Make member at once; Remove from church after a confirmation that counts the person's invite links and offers, checked, to revoke the other reusable links (revoke_reusable); Pending invites with role, type, expiry and maker, Copy link and Revoke. The People nav entry between Contacts and Account.
- A role refusal is toasted and refetches the role and the members (each hook, as 6a's do; no forbiddenIsRole meta); a lost church is the app's fallback. lib/settings/people.ts (memberActions checked against the 51-row shared role-policy fixture), lib/clipboard.ts, CopyLinkButton, InitialsAvatar; ConfirmDialog gains children and pendingLabel.
- Migration 0009_memberships_one_owner: refuses over a church with two owners (naming churches; a DO block on Postgres), then the partial unique index uq_memberships_one_owner on memberships (church_id) WHERE role = 'owner'. backend/migrations/README.md: "Before 0009_memberships_one_owner" (the SQL shown in full, marked read-only). streamlit_tests/test_settings_members_invites.py deleted: the frozen app's transfer promotes first, which the index refuses; its checks have had new-stack equivalents since 6b-1.
- docs/manual-verification.md: "Slice 6b" items 7-17. Rides along: the 6b-1 record and the 6b-2 spec amendment.

Before the PR (Task 9): the backup, the read-only owner counts and the SQL preview with the owner. After the merge: the after-deploy check, the phone check in a test church with a second Google account (join, role change, revoke, removal), a "Slice 6b-2a record" in docs/ops-runbook.md.

Tests: backend 2235 → 2235 passed, 46 → 48 skipped; frontend 952 → 1007 in 109 → 113 files

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R <repo> --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 6b-2a: Settings > People (invite links, members, pending invites) and migration 0009" \
  --body-file "<scratch>/6b2a-pr-body.md"
gh pr checks <N> -R <repo> --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `2235 passed, 48 skipped`, backend-postgres `48 passed, 2235 deselected` (after its `alembic upgrade head`, `alembic check`, `alembic downgrade base` and `alembic upgrade head` steps, which now include 0009 on Postgres 17), frontend `1007 passed` in 113 files. Then send: "PR #<N> is green: backend 2235 passed, 48 skipped (the two new Postgres tests passed in their own job, and the migration went up, down and up again on Postgres); 1007 frontend tests in 113 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R <repo>`.

- [ ] **Step 3 (agent, only if needed): A fresh backup and the counts again**

If more than a day has passed since T9's backup, or anything has merged to `main` since (`git fetch -q origin && git log --oneline <T9's main sha>..origin/main`), repeat T9 Steps 1 and 2 before Step 4 (clarification 14), and T8 Step 1 if `main` moved. Otherwise say so in the results and go on.

- [ ] **Step 4 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R <repo> --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "The backup is green, the counts are recorded and you have read the SQL. May I merge PR #<N> with a merge commit? Railway then runs the migration before the new server starts, and Vercel publishes the People page. You can keep using the app while it deploys; I will tell you when it is live, then ask for one more read-only query and the phone check, one step at a time." On a clear yes (not replayed):

```bash
gh pr merge <N> --merge -R <repo>
gh pr view <N> -R <repo> --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R <repo> --workflow ci.yml --branch main --commit "$(gh pr view <N> -R <repo> --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R <repo> --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both.

- [ ] **Step 5 (agent, then OWNER): The deploy and the after-deploy check (manual-verification items 10 and 17)**

About three minutes after the merge (not replayed):

```bash
curl -s <api>/health/ready; echo
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' <app>/settings/people
```

**Expected:** `{"ok":true,"db":"ok"}` (in production this answers 503 `schema_behind` while the database is behind the release, so `ok` means `0009` is applied and the new release is live); `307 <app>/login?next=%2Fsettings%2Fpeople` (signed out, the page sends you to sign in). If `/health/ready` still says `schema_behind` after ten minutes, ask the owner to open Railway → the API service → Deployments and read the newest deployment's status (a failed pre-deploy on the 5 s lock timeout or on 0009's refusal: the old server keeps serving and nothing is broken; read the log line with the owner, then Step R or a redeploy on the owner's yes). Then send, with README step 4's query in a code block, and step 2's query again:

> The new version is live. One more read-only check (it only reads): in the SQL Editor, run the first query below; it should show 0009_memberships_one_owner and 1 (the one-owner rule is in place). Then run the counting query from before again; the numbers should be the same as last time, except version and one_owner_index, which should now be 0009_memberships_one_owner and 1. If you have Railway open, the newest deployment's logs should include "Running upgrade 0008_invites_integrity -> 0009_memberships_one_owner". What do you see?

Record the values. A version other than `0009_memberships_one_owner`, `one_owner_index` not `1`, or fewer `memberships` or `owners` than before: stop and look before anything else.

- [ ] **Step 6 (OWNER, then agent): Phone, step 1 of 5: People in your church, read only (manual-verification item 11)**

> On your phone, open the app as you usually do and pull down to reload it. Tap **Settings**: are the sections Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, **People**, Account? Tap **People**: does it say "Everyone in {your church} can see this list.", then **Invite someone**, then **Members** with a number, then **Pending invites**? Is your own row marked **You** and **Owner**, with your email under your name? Please do not change anything in your own church; the next steps use a test church.

Record the answers (never a name or an email).

- [ ] **Step 7 (OWNER, then agent): Phone, step 2 of 5: an invite link, joined with your second account (item 12)**

> Switch to one of your test churches (the church menu at the top), then **Settings → People**. Under **Invite someone** leave **Member** chosen, leave Email empty and Reusable off, and tap **Create invite link**. Does **Invite link ready** appear with the link, "Anyone who opens this link can join {test church} as a member. It works once and expires …", and **Copy link**, **Share…** and **Done**? Tap **Share…**: does the share sheet open? Close it without sharing. Tap **Copy link**: does it say "Copied ✓" and "Link copied"? Is the link listed under **Pending invites** as **Single use**, "Expires in 7 days", created by you? Now open a **private window** (on the phone or on a computer) and paste the link. Does it say "You're invited" with **Sign in with Google**? Sign in there with your **second Google account**. Does it then offer **Join {test church}**? Tap it: does the test church open? In that private window, tap **Settings → People**: does it show the note "Only admins can change roles or remove people. …", with no **Invite someone** and no menus? Back in your own window, pull down to reload People: is the second account listed as **Member**, and is the link gone from Pending invites?

Record the answers (never the link or the second account's email).

- [ ] **Step 8 (OWNER, then agent): Phone, step 3 of 5: a role change and a revoke (items 13 and 14)**

> In the test church's People page: tap the **⋮** on the second account's row. Do you see **Make admin** and **Remove from church**? Tap **Make admin**: does the badge say **Admin** at once, with no question asked? Tap **⋮** again and **Make member**: **Member** again? Do your own row and the owner's row (yours) have no **⋮**? Now create one more invite link (Member, no email) and, under **Pending invites**, tap **Revoke** on it: does it ask "Revoke this invite?"; tap **Revoke invite**: does it leave the list? If you like, open that revoked link in the private window: does it say "This invite has been revoked."?

- [ ] **Step 9 (OWNER, then agent): Phone, step 4 of 5: removing the second account (item 15)**

> In the test church's People page, tap **⋮** on the second account's row, then **Remove from church**. Does it ask "Remove {name}?" and say they will lose access and that services they saved stay in the archive? (If you have a reusable link in that church there is also a checked box "Also revoke …"; leave it checked.) Tap **Remove member**: is the row gone? Then, in the private window, tap anything in the test church: does it say "You no longer have access to {test church}." and move to another church or the welcome page? You can close the private window afterwards.

- [ ] **Step 10 (OWNER, then agent): Phone, step 5 of 5: the phone screen (item 16)**

> On the People page: is there any sideways scrolling, even on a row with a long email? Tap **Create invite link** once more in the test church: does the link sit in its box (it scrolls inside the box) without widening the page? Tap **Done**, then tap in the **Email** box so the keyboard opens: can you still see the box and what you type, above the keyboard? Close the keyboard. Do the confirmations (open **Revoke** on a link and cancel) fit the screen? Are the buttons and the **⋮** easy to tap? Last, revoke that link so the test church has no links left: **Revoke**, **Revoke invite**.

- [ ] **Step 11 (agent): The agent's own check and the results (item 17)**

Item 17 is Step 5's two lines. Write each step's result, with the date, into `<scratch>/6b2a-t10-results.md` (not committed). A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 12 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it, `### Slice 6b-1 record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Slice 6b-2a record

Slice 6b-2a (Settings → People: every member sees the members with emails;
owners and admins invite with single-use or reusable links, change roles,
remove people and revoke links) merged as PR #<N>, the first of slice 6b-2's
two PRs (owner's 6b-2 planning answers of 2026-10-10), with migration
`0009_memberships_one_owner` (at most one owner per church). The owner
followed "Before 0009_memberships_one_owner" in `backend/migrations/README.md`
before the PR was opened: a backup, the read-only counts and the SQL (read,
not run); after the deploy, the read-only check and the counts again. Then
the phone check, its changes in a test church with a second Google account.
No church id, email address, invite code or link, token or database URL is
recorded here.

| Step | Result | Date |
|---|---|---|
| 1. Backup | `db-backup` run <run URL>: success, artifact `db-backup` (<bytes> bytes) <; a second one before the merge: …> | <date> |
| 2. Counts before (SQL Editor, read-only) | `0008_invites_integrity`; <n> churches, <n> deleted, <n> memberships, <n> owners, 0 churches with two owners, 0 without one owner, 0 without an admin, one-owner index 0 | <date> |
| 3. The SQL (read only, not run) | Rendered from the branch's code without a database and sent in full, marked "Read only. Do not run this.": the owner check and the index under the 5 s lock timeout; read by the owner: <answer> | <date> |
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`; `/settings/people` signed out: 307 to sign in. <Railway log line "Running upgrade 0008_invites_integrity -> 0009_memberships_one_owner" seen by the owner. / Not checked.> | <date> |
| 4. After the deploy (read-only) | `0009_memberships_one_owner`, index 1; counts again: <unchanged / …> | <date> |
| Phone 1. People in the real church (read only) | <Nine sections with People; the caption, Invite someone, Members (<n>), Pending invites; own row You and Owner. / …> | <date> |
| Phone 2. A link joined with the second account (test church) | <The panel's sentence, Share sheet, Copied and Link copied; listed as Single use; joined in a private window; the member's view had the note and no controls; listed as Member, the link gone. / …> | <date> |
| Phone 3. Role change and revoke | <Admin, then Member, at once; no menu on own row; the revoke asked and the link left the list <; the revoked link said "This invite has been revoked.">. / …> | <date> |
| Phone 4. Removal | <The dialog's words; the row gone; the second account's next tap said it no longer has access and moved on. / …> | <date> |
| Phone 5. The screen (<phone and browser>) | <No sideways scroll; the link scrolls in its box; the keyboard left the Email box visible; the dialogs fit; easy to tap. / …> | <date> |
| Agent checks | Item 17: Step 5's two lines. | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: 6b-2b (the Danger zone: leave, transfer, delete) | <date> |
```

Replace every `<…>` from the results files, keeping one alternative where a cell offers two. Read the record once by eye. Then (not replayed):

```bash
sed -n '/^### Slice 6b-2a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 6b-2a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|code='
sed -n '/^### Slice 6b-2a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '—'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 6b-2a record (backup, counts, SQL, merge, migration 0009, phone check)" -m "Records slice 6b-2a (PR #<N>): the backup, the read-only owner counts
and the SQL (read, not run) before the PR, the merge and the deploy of
0009_memberships_one_owner, the after-deploy check, and the owner's phone
check of Settings > People (read only in the real church; a join, a role
change, a revoke and a removal in a test church with a second account).
No church id, email address, invite code or link, token or database URL
is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 13 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 6b-2a record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R <repo> --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 6b-2a record" \
  --body "Records slice 6b-2a (PR #<N>) in docs/ops-runbook.md → Slice 6b-2a record: the backup, the read-only owner counts, the SQL (read, not run), the merge and deploy of migration 0009_memberships_one_owner, and the owner's phone check of Settings > People. No church id, email address or invite link is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R <repo> --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R <repo>`. Report: "Slice 6b-2a is live and recorded; <n> follow-ups. Next: 6b-2b, the Danger zone."

- [ ] **Step R (only if the release must come out): Revert**

Code only; the schema stays at `0009_memberships_one_owner` (README "Reverting 6b-2a": the code before 6b-2a never makes a second owner, so it runs on it unchanged). Reverting the merge and restoring only the revision and the model is not enough: the head constants, the baseline drift and the integrity test would fail, and the frozen app's members test would come back and fail on the index. So the revert keeps T1's whole commit (and its deletion), and the docs that rode along (the 6b-1 record, the 6b spec's amendment and this plan). On the owner's yes for each outward command, on a branch `claude/revert-6b2a` from `origin/main`:

```bash
git revert -m 1 --no-commit <merge sha>
git show --name-only --format= "$(git log -1 --format=%H --grep='^Migration 0009_memberships_one_owner: ' <merge sha>)" | LC_ALL=C sort
git checkout <merge sha> -- backend/migrations/versions/0009_memberships_one_owner.py backend/db/models.py backend/migrations/README.md backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py backend/tests/test_integrity.py
git rm -q -f streamlit_tests/test_settings_members_invites.py
git checkout <merge sha> -- docs/ops-runbook.md docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md docs/superpowers/plans/2026-10-10-slice-6b2a-people-page.md
.venv/bin/python -m pytest -q | tail -1
TEST_DATABASE_URL=<local url> .venv/bin/python -m pytest -q -m postgres 2>&1 | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
```

**Expected** (simulated in the replay, see "Build notes": a `--no-ff` merge of the replayed branch into `origin/main`, then these commands): the second line prints exactly the nine paths of T1's commit (the eight of the `git checkout` after it and the deleted test; if T1's commit lists any other path, add it before going on); the suites pass with T1's changes and nothing of T2-T7:
```
backend/db/models.py
backend/migrations/README.md
backend/migrations/versions/0009_memberships_one_owner.py
backend/tests/test_api_app.py
backend/tests/test_integrity.py
backend/tests/test_migrations.py
backend/tests/test_schema_check.py
backend/tests/test_services_postgres.py
streamlit_tests/test_settings_members_invites.py
```
```
2235 passed, 48 skipped in <t>s
```
```
48 passed, 2235 deselected, 1 warning in <t>s
```
```
 Test Files  109 passed (109)
      Tests  952 passed (952)
```

Then a commit "Revert slice 6b-2a (PR #<N>), keeping migration 0009" with the trailer; a PR, CI (whose `alembic check` then compares the restored model with the database at `0009`), and the merge on the owner's yes; record it in the record. Never `alembic downgrade` production for this.

Expected counts after this task: backend `2235 passed, 48 skipped` on `main`; frontend `1007 passed` in 113 files. The records PR adds no test.

---

## Build notes

**How this plan was written (2026-10-10).** Each task's code was built and run in a throwaway worktree of `dd2e7f0` (outside the repo directory; the repo's `.venv` as a symlink; a hard-linked copy of `frontend/node_modules`), one commit per task; the directives were then generated from those commits by a script (a new file as **Create**, an addition at the end of a file as **Append**, every other change as **In … replace** with just enough whole-line context to occur once in the file as it stands at that point, changes three or fewer lines apart in one block), which also checked that applying each file's directives to the file before the commit gives the file after it. The deletion in T1 is a `git rm` on a "Run:" line. The Postgres runs used a throwaway local PostgreSQL 16 cluster (initialised under `/var/lib/postgresql`, never a real database, on a local port), stopped and deleted afterwards. No package or variable was added. While building:
- **What S assumed and what exists.** Clarification 6: no `forbiddenIsRole` meta (6a decided against it; the People hooks follow 6a), no checkbox component (native checkboxes, as the email dialog's), `ConfirmDialog` without a body or a pending label (two optional props), no per-page `PageHeader` in Settings, `useMeContext` for the user's id. `buildInviteUrl`, the keys, the UI kit and the Base UI components S lists exist. `npx shadcn@latest view checkbox` reached the shadcn registry from this session (2026-10-10), so generating components is possible here; none was needed.
- **The index and the frozen app's test.** With the index in the model, `streamlit_tests/test_settings_members_invites.py::test_owner_only_transfer_and_delete` fails (`1 failed, 3 passed`), because the frozen app's transfer promotes first (clarification 5); `test_integrity.test_two_owners_are_reported` needed the index dropped first (clarification 4); the SQLite baseline drift gained `add_index uq_memberships_one_owner` (clarification 2). Nothing else in the backend suite or `streamlit_tests` touched a second owner.
- **The migration on Postgres.** Postgres prints the index's predicate as `((role)::text = 'owner'::text)` (the test pins it). CI's Alembic sequence by hand on a fresh database of the throwaway cluster: `upgrade head` (it logged "Running upgrade 0008_invites_integrity -> 0009_memberships_one_owner"), `check` ("No new upgrade operations detected."), `downgrade 0008_invites_integrity`, `downgrade base`, `upgrade head`, `check` again, clean.
- **Two test fixes while building.** The first 0009 SQLite test seeded a second church with the same owner email (the users table's unique email refused it); it now inserts the second church directly. In the People page tests the dropdown's items appear a tick after the trigger is clicked, so they are found with `findByRole`, and the second removal's invite list is set before the first removal refetches it.
- **Mutation checks** (each change made by hand in the build worktree with every task applied, the named tests run, the change undone): `memberActions` letting an admin act on their own row → `2 failed, 38 passed` (`people.test.ts`, `people-settings-page.test.tsx`); a role refusal not refetching the members → `2 failed, 38 passed`; the Remove dialog always sending `revoke_reusable=false` → `2 failed, 38 passed`; `useInvites` without its role-refusal handling → `1 failed, 39 passed`; Reusable left on and enabled while an email is typed → `1 failed, 39 passed`; the migration's SQLite pre-check removed → `1 failed, 42 passed, 10 skipped` (`test_migrations.py`); the model without the index → `9 failed, 63 passed, 11 skipped` (`test_migrations.py`, `test_models.py`, `test_integrity.py`, `test_schema_check.py`).

**Replay of the finished plan (2026-10-10).** The directives of T1-T7 were applied in order by a replay script that parses each step's **Create**, **Append** and **In … replace** blocks and its `bash` blocks (each commit), runs every command on its "Run:" lines (T1-T7 and T8 Steps 1-3; `<local url>` a fresh database on the throwaway local PostgreSQL 16 cluster) and compares the output with the quoted **Expected** blocks, onto a fresh detached worktree of the branch at the plan's commit (outside the repo directory and removed afterwards), with the repo's `.venv` (a symlink) and a hard-linked copy of `frontend/node_modules`:
- Baselines before T1 (on a worktree of `dd2e7f0`): backend `2235 passed, 46 skipped`; Postgres `46 passed, 2235 deselected, 1 warning`; frontend `952 passed` in 109 files; typecheck 0, lint 0.
- All 55 directives applied (16 **Create**, 5 **Append**, 34 **In … replace**); every **In … replace** block occurred exactly once; all seven commit blocks ran, each commit with the trailer; 46 commands run. Every "see it fail" output, every count and every T8 Step 1-3 output above is quoted from that replay (times as `<t>`), with one exception, fixed and run again: T8 Step 3's check of this plan for U+2028, U+2029, U+FFFE and U+FFFF found 4, because the command itself had been written with those characters instead of their `\u` escapes (6b-1's lesson, repeated); the command now uses the escapes and prints `0`. The production build compiled (`1`).
- **The revert (T10 Step R), simulated** on that worktree: a `--no-ff` merge of the replayed branch into `origin/main`, then Step R's commands. The first run showed that after `git revert -m 1 --no-commit` the deleted test is back **and staged**, so a plain `git rm -q` refuses it; Step R and the README's "Reverting 6b-2a" now say `git rm -q -f`. With that: `git show --name-only` of T1's commit listed exactly the nine paths, and the suites gave backend `2235 passed, 48 skipped`, Postgres `48 passed, 2235 deselected, 1 warning`, frontend `952 passed` in 109 files (T1's changes only).
- **The plan as committed** (`2b61519`) was then replayed once more by the same script with `--check` onto another fresh worktree and a fresh database: all 55 directives applied, all seven commits made with the trailer, 46 commands run, and every quoted output above matched (0 mismatches). The worktrees, their branches and the cluster were removed afterwards. The plan review fixes below changed T2-T5; their frontend outputs and counts were replayed again (see there).
- Not run while planning (each marked "(not replayed)" where it appears): T9 and T10 (the owner's backup, counts and SQL; the pushes, the PR and CI, the merge, Railway's pre-deploy migration on production data, Vercel's deploy, the after-deploy check, the phone check, the record and its PR). T9 Step 3's render is the same command T1 Step 5 runs.

**Plan review fixes (2026-10-10).** An independent review of the plan at `2b61519` found eight things. Each is fixed in the task that owns the code, and the owner's answers to the plan's two questions ("all recommended", 2026-10-10) are recorded in "Owner decisions" 7 and "Questions for the owner" (the tasks already followed them).
1. **(Major) Four must-rules had no failing test.** T4's test file now spies on every `console` method (`debug`, `error`, `info`, `log`, `trace`, `warn`) around each People page test and fails a test whose console output carries a fixture's invite code (`abc`, `r-123`, `r-1`) or `code=`. T4 "never keeps the invite list as fresh…" checks `staleTime` 0 on every observer of the invite query. T5's create test checks that "Invite link created." sits inside the `aria-live="polite"` region. T4 "checks Also revoke again each time…" unchecks the box, cancels, reopens the dialog and finds it checked.
2. **(Minor) The role 403 tests showed the refetch, not the page turning read-only.** T5 "turns read-only inside the church layout…" renders the real `(church)` layout (so `useChurch` comes from `GET /church`) around Settings → People: a revoke is refused, `GET /church` then says member, and Invite someone, the action menus and Pending invites are gone, with the members note shown and `GET /church` asked twice.
3. **(Minor) The link panel outlived its invite.** `CreateInviteForm` reads the invite list and shows the panel only while its invite is in it (or while the list has not loaded); the live region empties with it (clarification 9). T5 "clears the link panel when its invite is revoked" covers a revoke; a removal reaches the panel the same way, through the refetched list. Three T5 tests whose fake `GET /invites` stayed empty after a create now use `invitesServer` (it also no longer lists an id twice).
4. **(Nit) The codes stayed in memory after a role refusal.** `useInvites` removes `keys.invites(churchId)` when `enabled` turns false, which happens once the refetched profile says the role no longer allows the list. Not in the refusal handler itself: there the page's queries are still enabled, so a removed list is fetched again and refused again, a loop until the new role arrives (and without end in a test whose role never changes). The layout test of item 2 checks that the cache holds no invite list afterwards.
5. **(Nit) Copy link's name in a row stayed "Copy link for …" while "Copied ✓" showed.** `CopyLinkButton` drops its `aria-label` while "Copied ✓" shows; T5's row copy test finds the row's button by the name "Copied ✓" (clarification 10).
6. **(Nit) `formatExpiry` could say "in 24 hours".** It rounds the hours first and switches to days from 24 rounded hours: 23.5 hours reads "in 1 day", 23 hours 20 minutes "in 23 hours". T2 "chooses the unit after rounding…".
7. **(Nit) The date regex held a literal U+202F.** It is written `/\u202f/g`.
8. **(Nit, optional) Share failures.** Kept as written: every failure of `navigator.share` is silent, a cancel (`AbortError`) included, which is all the spec asks; the link and Copy link stay on screen, so a message for other failures would add nothing (clarification 12).

Mutation checks for these (each violation planted in a build worktree with T1-T7 applied, the named file run, the change undone; `people-settings-page.test.tsx` unless named): `staleTime` 60 s → `1 failed, 25 passed`; a `console.info` of the codes in `useInvites` → `15 failed, 11 passed`; `console.log(url)` in `InviteRow` → `15 failed, 11 passed`; no `aria-live` → `1 failed, 25 passed`; the Remove box not reset to checked → `1 failed, 25 passed`; the panel kept after its revoke → `1 failed, 25 passed`; the invite list kept in the cache once read-only → `1 failed, 25 passed`; a role refusal not refetching the profile → `3 failed, 23 passed`; the unit chosen before rounding → `1 failed, 18 passed` (`people.test.ts`); Copy link keeping its `aria-label` while copied → `1 failed, 25 passed`. With the real code each file passes.

Counts: frontend 1002 → 1007 (T2 +1 in `people.test.ts`, T4 +2 and T5 +2 in `people-settings-page.test.tsx`); still 113 files and 35 paths; the backend, the API and the docs tasks are unchanged.

**Replay of the fixed plan (2026-10-10).** The same replay script, limited to the frontend, applied the fixed plan's T1-T7 directives in order onto a fresh detached worktree of `2b61519` (outside the repo directory, removed afterwards; the repo's `.venv` as a symlink, a hard-linked copy of `frontend/node_modules`): all 58 directives applied (16 **Create**, 5 **Append**, 37 **In … replace**), every **In … replace** block occurred exactly once, all seven commit blocks ran with the trailer, and every frontend command of T2-T6 and T8 Step 2 (23 commands: the focused files, the suites, typecheck and lint, the production build) was compared with its quoted **Expected** block: 0 mismatches. Not replayed this time, since the fixes do not touch them and the replay above stands for them: T1's backend and Postgres commands (T1's `git rm` did run), T7's docs tests and em dash count, T8 Step 1, T8 Step 2's backend and Postgres lines, and T8 Step 3.

**6b-2a build (2026-10-10).** T1-T8 built on the branch from `3c70ac0` by applying each task's directives in order (all 58 applied: 16 **Create**, 5 **Append**, 37 **In … replace**; every **In … replace** block occurred exactly once), running every "Run:" line and comparing with its **Expected** block, then committing and pushing after each task:
- Baselines before T1: backend `2235 passed, 46 skipped`; Postgres `46 passed, 2235 deselected, 1 warning`; frontend `952 passed` in 109 files; typecheck 0, lint 0.
- Every "see it fail" and "see it pass" output of T1-T7 matched as quoted (T1: `16 failed, 78 passed, 12 skipped`, `5 failed, 12 passed, 43 deselected`, the frozen test `1 failed, 3 passed`, then `94 passed, 12 skipped`, `18 passed, 52 deselected`, the suite `2235 passed, 48 skipped`, Postgres `48 passed, 2235 deselected, 1 warning`, and the SQL preview identical to step 3's block; T2 975 in 111 files; T3 980 in 112; T4 994 in 113; T5 1006 in 113; T6 1007 in 113; T7 `89 passed` and `0` em dashes).
- T8: Step 1 `0`, `0`, `9`; Step 2 backend `2235 passed, 48 skipped`, Postgres `48 passed, 2235 deselected, 1 warning`, frontend `1007 passed` in 113 files, typecheck 0, lint 0, the production build compiled (`1`); Step 3 `0` (API files regenerate unchanged), `0` em dashes in added lines, `0` stray code points, exactly the 35 paths, `0` untouched paths changed, the nine subjects in order, `trailer check done`. CI's Alembic sequence by hand on a fresh database (`upgrade head`, `check`, `downgrade base`, `upgrade head`, `check`): "No new upgrade operations detected." both times; `pg_smoke.py` OK. Runbook owner markers still `4`. The PR line's counts (`backend 2235 → 2235 passed, 46 → 48 skipped; frontend 952 → 1007 in 109 → 113 files`) match.
- One difference, in the environment only: the throwaway PostgreSQL 16 cluster could not live in the session scratchpad (its parent directory is private to root, and Postgres does not run as root), so it was initialised under `/var/lib/postgresql` on a local port, as when planning, and stopped and deleted at the end. No code or test differs from the plan.
- Not run here: T9 and T10 (the owner's routine, the PR, CI, the merge, production).

## Spec coverage

| Owner answer or spec item | Task(s) and tests |
|---|---|
| 2026-10-10 answer 1: 6b-2a is the People page, its nav entry and `0009_…` with the owner routine (the SQL in full, marked read-only) | T1-T7; T9 Steps 1-3; T10 Steps 4-5; T1 `test_the_readme_shows_the_0009_preview_exactly_and_in_full` |
| 2026-10-10 answer 2: the phone check is a real join in a test church with a second Google account, then its removal | T7 items 12-15; T10 Steps 7-9 |
| 2026-10-09 answers: visibility; invites; removal revoking links with the reusable box checked; no own role change; role changes without confirmation; the Settings order; no em dashes | T4 "shows a member everyone…", "gives an admin a menu…", "lets the owner make an admin a member at once…", "asks before removing…"; T5 the invite tests; T6; T8 Step 3's em dash gate |
| S UX "Every page" (skeletons, ErrorState with Retry, the pending words, toasts, inline errors with focus, React text, initials only) | T4 "shows the error state with Retry…"; T5 "says under Email…"; T3 "names the pending action when asked", "shows initials only…" |
| S UX 1a (Invite someone and the panel) | T5 "creates a single-use member link…", "sends an admin, reusable link…", "turns Reusable off while an email is typed…", "says under Email…", "offers Share on a device that can share…"; T3 the Copy link tests |
| S UX 1b (Members, the menu, the Remove dialog) | T4 every test (the box checked again on reopen: "checks Also revoke again each time…") |
| S UX 1c (Pending invites) | T5 "puts Invite someone, Members and Pending invites in that order…", "lists pending invites…", "shows a row's link, selected…", "revokes an invite after asking…", "clears the link panel when its invite is revoked"; T4 "never keeps the invite list as fresh…" |
| S "Losing a role mid-session" | T4 "toasts the server's refusal…", "toasts a role refusal of the invite list…", "leaves a lost church to the app…" (clarification 6a); T5 "turns read-only inside the church layout…" (the page goes read-only and the codes leave the cache) |
| S "Alembic revision `memberships_one_owner`" (the pre-check, the index, the downgrade, the model) | T1 every 0009 test; CI's `alembic check` on Postgres |
| S "Church integrity runbook" (step 3 for two owners; the check before the revision) | T1 README; T1 `test_integrity.test_two_owners_are_reported`; T9 Step 2 |
| S "Frontend changes" (routes, components, pure helpers, queries; the People parts) | T2-T5 |
| S Testing → Frontend unit (`memberActions` against the fixture with S's mapping, `copyText`, `buildInviteUrl`'s argument order, `inviteSummary`, `formatExpiry`) | T2 every test |
| S Testing → Frontend DOM (People as a member and as an admin, create invite, pending invites, role loss, lost access, ErrorState, the Settings nav) | T4, T5, T6 |
| S "Manual checks" (the People items, rewritten for a test church and a second account) | T7 items 7-17; T10 Steps 6-10 |
| S acceptance 2 (client half), 12 (one-owner half), 14, 16, 18, 22 (People half) | T2; T1 and T10 Step 5; T4, T5; T4; T4, T5 and T7 item 16; T6 |
| The binding rules (no em dashes; no real ids, emails or links in docs; SQL for reading shown in full and marked; migrations safe on production data; frozen Streamlit files untouched; no network in tests; never log invite codes) | Global Constraints; T4's console check around every People page test; clarifications 3, 5, 11, 13; T8 Step 3; T9 Step 3; T10 Step 12's record checks |

S items **not** in 6b-2a: the Danger zone (UX §2), `useExitChurch`, `markChurchExited`, the `(church)` layout's exited-church check, `leaveBlock`, `deleteNameMatches`, the transfer, leave and delete hooks and their DOM tests (6b-2b); `LegacySettingsNote` (never built); the `streamlit_tests` port and ledger (dropped by the 2026-10-09 answer 2); S's `handleAuthErrors` meta test (no meta, clarification 6a; the page tests cover the behavior).

## Follow-ups (not in 6b-2a)

- 6b-2b builds on this: the Danger zone page and its nav entry, `useExitChurch` with `markChurchExited`, the layout's exited-church check, and its phone check on a throwaway church. Its Transfer card can link to **Invite someone** on this page ("Invite another member first to transfer ownership.").
- If the owner ever wants the Remove dialog to also count the pending invites for the removed person's own email (which 6b-1's removal revokes too; clarification 8), it is one more count in `lib/settings/people.ts`.
- `components/ui` still has no `checkbox.tsx`; if a later page wants Base UI's styled checkbox, `npx shadcn@latest add checkbox` works from this environment.

## Questions for the owner

Your 6b-2 planning answers of 2026-10-10 and your 6b answers of 2026-10-09 (all as recommended) are binding and already in the plan. The two choices below were put to you and **answered on 2026-10-10: "all recommended"**; the tasks and the copy follow them.

1. **The retired Streamlit app's members test** (clarification 5). **Answered: yes, delete `streamlit_tests/test_settings_members_invites.py` in T1** (four tests; T1 Step 4's `git rm`). One of its tests runs the old app's "Transfer ownership", which makes the new owner before it demotes the old one; the new one-owner rule refuses that (safely, nothing changes), so the test would fail. Everything it checked has had a new test since 6b-1, and the old app's own files stay untouched.
2. **Two small wording changes** (clarification 11). **Answered: yes, plain English**: "The 1 invite link Ann created …" / "The 2 invite links Ann created …", "Also revoke the 1 reusable invite link" / "… the 2 reusable invite links", and "as a member" / "as an admin" (the design wrote "link(s)" and "a {member|admin}"). T2's `inviteSummary`, T4's Remove dialog and their tests use these words.

Owner steps still to come: the backup, one read-only query and the SQL to read (T9); the draft PR on your yes and ready on your yes, the merge on your yes, one more read-only query, a phone check in five short steps (the last four in a test church with your second Google account), and the records PR (T10).

## Self-review

- **Coverage.** Every binding constraint has a home: 6b-2a as the People page with `0009_…` and the owner routine (clarifications 1, 2; T1-T7, T9, T10); the phone check as a real join and removal in a test church with a second account (answer 2; T7 items 12-15; T10 Steps 7-9); the SQL for reading shown in full and marked "Read only. Do not run this." (T1's README and its test refusing "..."; T9 Step 3); no em dashes in user-facing copy (clarification 11; T8 Step 3 greps the added lines); no real ids, emails, codes or links in committed docs (tests use `@example.com` and made-up names; commands use `<repo>`, `<api>`, `<app>`; the record's own grep, T10 Step 12); invite codes never logged (nothing in the app logs; the server's are 6b-1's); migrations safe on production data (the pre-check before the index in one transaction under the 5 s lock timeout, a refusal rather than a repair, a working downgrade; clarification 3; T1's SQLite and Postgres tests); the frozen Streamlit files untouched (T8 Step 3's untouched check; one of its tests deleted, clarification 5); no network in tests (Global Constraints). The second-to-last task (T9) runs the owner's pre-merge routine for 0009 one step at a time; the last (T10) opens the draft PR only on the owner's yes, merges only on a yes, checks production, runs the phone check and inserts "### Slice 6b-2a record" before "## Backups", after "### Slice 6b-1 record".
- **Placeholders.** None in T1-T8's code, tests, commands or expected outputs; every expected output is quoted from the replay. The `<…>` left are T9 and T10's runtime values (`<N>`, `<repo>`, `<api>`, `<app>`, `<scratch>`, `<local url>`, times, the owner's answers), as in the earlier plans.
- **Consistency.** Names agree across tasks: `displayName`, `initials`, `memberActions`, `inviteSummary`, `formatDateTime`, `formatExpiry`, `invitesCreatedBy`, `otherReusableInvites` (T2) are used by T3 (`InitialsAvatar`), T4 and T5; `copyText` (T2) by `CopyLinkButton` (T3); `useMembers`, `useInvites`, `useChangeRole`, `useRemoveMember`, `useCreateInvite`, `useRevokeInvite`, `inviteFieldError`, `isRoleRefusal` (T3) by T4 and T5; `ConfirmDialog`'s `children` and `pendingLabel` (T3) by T4 and T5; `member`, `memberList`, `invite`, `inviteList`, `PEOPLE` (T2) by T2, T4 and T5; `PREVIEW_0009` (T1) by two T1 tests. The counts in the table, each task's "Expected" and the PR line agree.
- **Not verified while planning:** the pushes, the PR and CI (the Postgres tests and CI's Alembic sequence were run on a throwaway local PostgreSQL 16 instead of CI's 17), Railway's pre-deploy migration on production data, Vercel's deploy, the production build's font fetch if it fails here, the owner's checks, and the page on a real phone (Share, the keyboard, 375 px): those are T10's phone steps.
- **Judgement calls to watch in review:** the role refusal per hook instead of S's meta (6a); native checkboxes (6b); `ConfirmDialog`'s two new props (6c); an h2 instead of a `PageHeader` (6d); the frozen app's test deleted here (5, owner question 1, answered yes); the wording (11, owner question 2, answered yes); a row's link revealed when copying fails (10); the pre-merge routine before the PR is opened, with a fresh backup if a day passes (14).
