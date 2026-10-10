# Slice 6b-2b: Settings → Danger Zone (Leave, Transfer Ownership, Delete) and the Quiet Exit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the second of slice 6b-2's two PRs (owner's 6b-2 planning answers of 2026-10-10, "all recommended"; binding): **Settings → Danger zone**. After it merges, every member of a church opens **Settings → Danger zone** (`/settings/danger`, the last entry of the Settings nav) and can **Leave** the church after a confirmation: the app says "You left {church}.", drops that church's unsaved draft on this device, and opens another of their churches (or the welcome page) without the "You no longer have access to {church}." message that a removal shows. Admins and members also read "Only the owner can transfer ownership or delete the church." The owner sees Leave turned off with why (transfer first, or, alone, delete), **Transfer ownership** (choose anyone else, admins first; confirm; the page then turns to its admin form) and **Delete church** (a confirmation that also needs the church's name typed exactly; then the same quiet exit as Leave). No API change, no migration, no new package or variable; the frozen Streamlit app's files are untouched. Tests never reach the network.

**Architecture:** Frontend only, bottom up. T1: the pure rules (`markChurchExited`/`wasChurchExited` in `lib/church.ts`, a 60 s mark per church; `leaveBlock`, `deleteNameMatches`, `transferCandidates`, `transferChoiceLabel` in `lib/settings/people.ts`). T2: the exit (`useMembershipChanged` now resolves to whether `/me` came back; `lib/church-exit.ts` with the pure, ordered `runChurchExit` and the `useExitChurch` hook; the `(church)` layout's two lost-access toasts skip a church marked as just left). T3: the page (the transfer, leave and delete hooks in `lib/queries/church.ts`, `ConfirmDialog`'s `confirmDisabled`, the Danger zone components and route, its DOM tests inside the real layouts). T4: the nav entry. T5: the manual check items. T6: verification. T7: the pre-merge note (no migration, so no owner routine). T8: the draft PR, the merge on the owner's yes, the after-deploy check, the phone check on a throwaway church with the owner's second Google account, the record.

**Tech Stack:** Next.js 16 (App Router, client components), React 19, TanStack Query 5, Base UI (shadcn components in `components/ui`), Tailwind 4, sonner, Vitest 3 with Testing Library and jsdom, ESLint, `tsc`. The backend (Python 3.11, FastAPI, pytest) is only run, never changed.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md`, read with its two amendments, which are binding and win where the older text differs. **2026-10-09:** two PRs; Streamlit treated as unused; visibility as designed (only the owner transfers or deletes); leave, remove, transfer and delete confirm; delete needs the exact church name; the final Settings order Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, People, Account, Danger zone; no em dashes in user-facing copy. **2026-10-10:** 6b-2 is two PRs; this is **6b-2b**: the Danger zone page (`/settings/danger`: leave, transfer, delete; the Danger zone nav entry), `useExitChurch`/`runChurchExit`, `markChurchExited`/`wasChurchExited` and the `(church)` layout's exited-church check; its phone check tests Delete on a throwaway church made from the switcher (for example "Delete me"), the test churches are kept, and Leave and Transfer use the second account where possible, else open the dialog and cancel. From S: UX §2 (2a Leave, 2b Transfer, 2c Delete), "Losing a role mid-session", "Frontend changes" (the danger components, `leaveBlock`, `deleteNameMatches`, `src/lib/church-exit.ts`, the `(church)` layout change, the transfer, leave and delete hooks), "Draft store", Testing (Frontend unit and DOM for the Danger zone; manual checks 6, 8 and 9), Risks, acceptance 15 and 22's Danger zone half.
- The model plan: `docs/superpowers/plans/2026-10-10-slice-6b2a-people-page.md` (merged as PR #60): its structure, Owner decisions, clarification 6 (what S assumed and what exists: no `forbiddenIsRole` meta, role 403s handled in each hook; native checkboxes; `ConfirmDialog`'s `children`, `pendingLabel` and `wrapAnywhere`; no `PageHeader` on Settings pages; `useMeContext`), its Build notes and its build review fixes (long text wraps at 375 px with `[overflow-wrap:anywhere]`, user text as React text, each running write's state its own). This plan reuses what 6b-2a built: `lib/settings/people.ts` (`displayName`), the `Member`/`MemberList` aliases and the `member`/`memberList`/`PEOPLE` fixtures, `keys.members`, `useMembers`, and the People hooks' role-refusal handling (`onRoleRefused` and `onWriteError` in `lib/queries/people.ts`, now exported).
- `docs/ops-runbook.md` "Slice 6b-1 record" and "Slice 6b-2a record": twice, migration SQL shown in chat as a block was pasted and run. 6b-2b has **no migration** and changes nothing in the database's shape; nothing in this plan puts SQL in front of the owner. If anything here turns out to change the database, stop and tell the owner before going on.
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `6fe88d6` = `origin/main` `518a729` (6b-2a merged as PR #60) plus the 6b-2a record, then this plan's commits; 2026-10-10): backend `2236 passed, 49 skipped`; frontend `1010 passed` in 113 files; typecheck and lint clean; Alembic head `0009_memberships_one_owner` (9 revision files). What exists from 6b-1 and 6b-2a on `main`: `POST /church/transfer-ownership` (`TransferOwnershipIn {user_id}`, `require_owner`; answers `MemberListOut` afterwards; 403 "Only the owner can do that.", 404 "Member not found.", 422 `fields.user_id`), `POST /church/leave` (`require_church`; `LeftOut`; 409 `owner_must_transfer`, 409 `last_admin`), `DELETE /church` (`DeleteChurchIn {confirm_name}` as a JSON body, `require_owner`; `DeletedOut`; 422 `fields.confirm_name` "Church name did not match."; the server compares both names trimmed, exactly; a soft delete that revokes the church's invites), and their generated types in `schema.d.ts` (no aliases yet but `DeletedOut`); `useMembershipChanged` (slice 1), `useMeContext`, `removeLocal` (`lib/storage.ts`), `draftKey`/`corruptDraftKey` (`lib/draft/schema.ts`), `keys.church`, `useChurchMutation`, `ConfirmDialog` (with `children`, `pendingLabel`, `wrapAnywhere`, `finalFocus`), `PendingButton`, `ErrorState`, `Skeleton`, `components/ui` `select` (Base UI, with `items` and a `placeholder` on `SelectValue`), `input`, `label`, `button`. Missing or different: see clarification 2.
- Every code task was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan. `<repo>` is the GitHub repository of this checkout's `origin` (owner/name), `<api>` the production API's address (Railway → the API service → Settings → Networking), `<app>` the production app's address, `<scratch>` the session's scratchpad path and `<N>` the PR number; write each out literally when running a command, and never into a committed file.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: the suite `.venv/bin/python -m pytest -q 2>&1 | tail -1`; the docs tests `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1`. Frontend: one file `(cd frontend && npx vitest run <path> 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` (one file per command, so the order of the lines never depends on which file finishes first), the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`, and `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`. A time in an expected output is written `<t>`.
- The API does not change: `backend/` (the API, the usecases, the migrations, the tests) and the generated `openapi.json` and `schema.d.ts` stay as they are (T6 checks that regenerating them changes nothing). **No migration**; no new package, no new variable; no new `components/ui` file (clarification 2c).
- Branch `claude/slice-2-plan-4q33le`, at `6fe88d6` plus this plan's commits (`WIP plan: …` and `Plan: slice 6b-2b (Danger zone)`, and any later plan commit), then T1-T5. Stage files by name (`git add <paths>`); never `git add -A`; nothing under `.claude/` is staged.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R <repo>` (or the session's GitHub tools, with the same effect), only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 2236 → 2236 passed, 49 → 49 skipped (unchanged); frontend 1010 → 1041 in 113 → 115 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 9 and has no em dashes.
- No church id, email address, invite code or link, token, database URL, street address or real person's name in any doc, commit, test or record. Tests use `@example.com` addresses, the fixtures' "Grace" and "Hope" and made-up names.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.
- **Tests never reach the network**: the frontend tests stub `fetch` with `installFakeApi` (an unhandled request fails the test).
- The frozen Streamlit files (`app.py`, `streamlit_views/`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`, `streamlit_tests/`) are not edited.

### How the file directives below read
As in the 6b-1 and 6b-2a plans: **Create `path`:** the block is the whole new file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file, as whole lines, and is replaced by the block after **with:** (a leading or trailing empty line in a block is part of it). Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted or moved.

### Baselines and counts
- Starting baselines: backend **2236 passed, 49 skipped**; frontend **1010 passed in 113 files**, typecheck and lint clean; Alembic head **`0009_memberships_one_owner`** (9 revision files). If any differs, stop and ask.
- Planned cumulative counts (observed in the replay). A frontend delta counts tests (an `it.each` counts each case) and files. The backend never changes: `2236 passed, 49 skipped` after every task (CI's `backend-postgres` stays `49 passed, 2236 deselected`).

  | After | Frontend (delta) | Frontend |
  |---|---|---|
  | T1 | +5 (`church.test.ts` 1, `people.test.ts` 4) | 1015 in 113 files |
  | T2 | +6 (`church-exit.test.ts` 2, a new file; `membership.test.tsx` 1; `church-layout.test.tsx` 3) | 1021 in 114 files |
  | T3 | +19 (`confirm-dialog.test.tsx` 1; `danger-zone-page.test.tsx` 18, a new file) | 1040 in 115 files |
  | T4 | +1 (`settings-layout.test.tsx`: the Danger zone case) | 1041 in 115 files |
  | T5 | 0 (`docs/manual-verification.md` only) | 1041 in 115 files |

### Layering and code rules (carried)
- Pages and components never call `apiFetch`: the hooks in `src/lib/queries/church.ts` use `useApi().church`, and every write goes through `useChurchMutation`, so a `no_church_access` 403 reaches the `(church)` layout's fallback.
- **A role refusal is the hook's** (6a's way, 6b-2a clarification 6a): a 403 without `details.reason` on a transfer or a delete (ownership moved in another tab or by someone else) is toasted with the server's words and refetches the church profile (the role) and the member list, so the page re-renders as the admin form and the user stays in the church. A 401 and a lost church are the app's and are not toasted again. `handleAuthErrors` does not change.
- `src/lib/settings/people.ts` and the exit's `runChurchExit` are pure (no React, no fetch); the rules decide only what the page shows. The server enforces every rule (6b-1).
- **The exit's order is fixed** (S "`src/lib/church-exit.ts`"): mark the church as exited, cancel its requests, remove its draft keys, `useMembershipChanged({selectChurchId: null})`, remove its cached queries. The exit adds no `storeChurchId` and no `router.replace` of its own.
- Writes are not optimistic (F §4.4): the transfer puts the server's member list in the cache, then refetches. Leave and Delete keep their dialog pending ("Leaving…", "Deleting…") until the exit is done, and one confirmation sends one request, however fast it is tapped.
- User-supplied text (church and member names, emails) renders as React text only, and a long one wraps (`[overflow-wrap:anywhere]`) instead of widening the page at 375 px. Every control is at least 44 px tall on phones (F §4.8), inputs are `text-base md:text-sm` (the `Input` component's own classes) so iOS does not zoom.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** is retired (branch `streamlit-frozen`, untouched); merges never reach it. The frozen files on `main` are not edited.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge; Railway's pre-deploy runs `alembic upgrade head` (it finds nothing to do here: no migration).
4. **The 6b-2 planning answers of 2026-10-10** ("all recommended"; binding; S's second amendment): (1) two PRs; this is **6b-2b**: the Danger zone page and its nav entry, `useExitChurch`/`runChurchExit`, `markChurchExited`/`wasChurchExited` and the `(church)` layout's exited-church check; (3) the phone check deletes a throwaway church made from the switcher (for example "Delete me"); the test churches are kept; Leave and Transfer use the second Google account where possible, else open the dialog and cancel.
5. **The answers for this plan (2026-10-10)**: `/settings/danger` with Leave church (everyone; the owner blocked with the two explanations), Transfer ownership (the owner; a select of the other members, admins first; confirm), Delete church (the owner; the exact name typed; confirm), the non-owner banner, the pending labels, the toasts, the 409 and 422 handling, and the **Danger zone** nav entry last. After a transfer the profile, `/me` and the members refetch and the page re-renders in its non-owner form; alone, "Invite another member first…" links to `/settings/people`.
6. **The 6b planning answers of 2026-10-09** and the earlier ones (binding, carried): decision 5 (roles: only the owner transfers or deletes; anyone but the owner may leave), leave, transfer and delete confirm, delete needs the exact name, the final Settings order, no em dashes; 6a's "a role refusal turns the page read-only without leaving the church"; 6b-2a's "proper plurals" (its question 2).
7. **No migration, no owner routine before the merge** (T7): nothing here changes the database's shape or runs SQL; the daily backup stands.

**Later, out of scope:** slice 7 (retiring the frozen app's files); restoring or purging soft-deleted churches (not scheduled; S "Out of scope").

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items change what someone sees compared with S; each follows an earlier answer, so none is a new question.

1. **What 6b-2b ships** (answer 4 (1), answer 5). `/settings/danger` with `DangerZonePage`, `LeaveChurchCard`, `TransferOwnershipCard` and `DeleteChurchCard` (S's `DeleteChurchDialog` is the card's `ConfirmDialog` with the typed-name box as its body, not a file of its own); `lib/church-exit.ts` (`runChurchExit`, `useExitChurch`); `markChurchExited`/`wasChurchExited` in `lib/church.ts`; `leaveBlock`, `deleteNameMatches`, `transferCandidates`, `transferChoiceLabel` in `lib/settings/people.ts`; `useTransferOwnership`, `useLeaveChurch`, `useDeleteChurch` and `deleteNameError` in `lib/queries/church.ts`; the Danger zone nav entry (the nav is then in its final order); the manual check items.
2. **What S assumed and what exists** (S "Assumed interfaces", "Frontend changes"). Where they differ:
   - a. **`useMembershipChanged({selectChurchId: null})` stores nothing** (S: it "calls `storeChurchId(null)`"). Slice 1 shipped `if (selectChurchId) storeChurchId(selectChurchId)`, with a test, "selectChurchId: null stores nothing and keeps the stored church". The exit does not need it: once the new `/me` no longer lists the church, `pickActiveChurch` falls back to the first remaining church by name and the layout stores that pick. Left as it is; the exit adds no `storeChurchId` (S).
   - b. **`useMembershipChanged` never throws and said nothing about `/me`** (it catches a failed `/me`, resets it and still navigates), so S's "If step 4's `/me` fetch fails, `useExitChurch` toasts …" had nothing to read. T2 makes it resolve to `true` when `/me` came back and `false` when it did not (its two other callers, the create and join forms, ignore the value; a test pins both answers). `runChurchExit` also treats a rejection as `false`, so the draft keys and the cache are dropped either way.
   - c. **No `forbiddenIsRole` meta** (6b-2a clarification 6a): S's "meta `forbiddenIsRole`" on the transfer and delete hooks is 6b-2a's per-hook handling instead: `onWriteError` (now exported from `lib/queries/people.ts`) toasts a role 403 and refetches the profile and the members; a 404 on the transfer (the person left meanwhile) is toasted and refetches the members. The leave hook has no role refusal to handle (S: "a 403 here means the church is gone").
   - d. **The layout has two lost-access toasts, not one** (S: "the one-line `(church)` layout change"). Since slice 1's build, besides the `churchAccessLost` subscriber, a `/me` refetch that no longer lists the shown church toasts "You no longer have access to {name}." too (slice 1's "Step 5, second path", for a refocus that answers before the 403). The exit's own `/me` fetch is exactly that refetch, so a guard on the subscriber alone would still toast after every Leave and Delete (T3's leave test fails that way with only the subscriber guarded; see "Build notes"). T2 adds `wasChurchExited` to both: two lines, the second the one that matters for a normal exit.
   - e. **Slice 2's draft prune is not once per load**: the `(signed-in)` layout prunes "on `/me`'s first load and whenever its data changes" (slice 2b), so the exit's `/me` refetch also prunes the left church's draft. The exit still removes both keys itself, first, as S says, so they are gone even when `/me` does not come back.
   - f. **`ConfirmDialog` has no way to keep its confirm button off** while the dialog's own condition fails (the typed name). T3 adds an optional `confirmDisabled` prop (passed to the `PendingButton`'s `disabled`); every existing caller is unchanged.
   - g. **No `PageHeader` on Settings pages** (6b-2a clarification 6d): an h2 "Danger zone", then h3 cards. S's "info banner" is a `role="note"` paragraph (an `Alert` would be `role="alert"`, which announces itself as an error on every visit).
   - h. S's `useMe().user.id` is `useMeContext().user.id`; the draft key names come from `draftKey`/`corruptDraftKey` (`lib/draft/schema.ts`), not written out again. The type aliases are `TransferOwnershipBody`, `ChurchLeft` and `DeleteChurchBody` (`DeletedOut` exists).
3. **The 60 s mark** (S "Change to slice 1's `(church)` layout"). `markChurchExited(id, at = Date.now())` stores the time in a module-level `Map` (one tab, never stored); `wasChurchExited(id, now = Date.now())` is true while `now - at < 60 000` and forgets the mark after, so a user who rejoins and is later removed sees the toast again. The two time arguments are for the tests (no fake timers). `resetExitedChurchesForTests()` runs after every DOM test (`setup-dom.ts`), as the stored church id's reset does. A marked church is still excluded and `/me` still refetched: only the toast is skipped.
4. **The delete name** (S UX 2c: "`typed.trim() === church.name`"). `deleteNameMatches(typed, name)` trims both, as the server compares them (`confirm_name.strip() != name.strip()`), so a name stored with a stray space can still be confirmed; capitals count. The request sends what was typed (S: `{"confirm_name":" Grace "}`).
5. **Leave for the owner** (S UX 2a). `leaveBlock(role, memberCount)` is `"owner_with_others"`, `"owner_alone"` or `null`; the owner's button is off with the matching sentence. The count is the member list's, so the owner's cards wait for `GET /members` (skeletons, then the cards, or ErrorState with Retry). Admins and members never ask for the member list here. The last admin of a church with no owner is not blocked on the page (only a hand-made church can be in that state); the server's 409 is toasted.
6. **The New owner list** (S UX 2b: "`items` map `user_id → "{display name} ({email})"`"). `transferCandidates` is everyone else but the owner, admins first, each in the server's order (by name). A person with no name is listed by the email alone (`transferChoiceLabel`), not "sam@example.com (sam@example.com)". Someone chosen who has left meanwhile (gone from the refetched list) is no longer chosen, and the button turns off again.
7. **After a transfer** (answer 5). The answer (the member list afterwards) goes in the cache; the members, `["church", id, "profile"]` (the role) and `["me"]` (the switcher's role) refetch; the toast "Ownership transferred. You are now an admin."; once the profile says admin, the page shows the note and Leave only, and the Settings heading says "You're an admin of {church}." Focus goes to the page's heading, since the Transfer card is gone.
8. **The dialogs while they run** (F §4.8; 6b-2a's lessons). Each confirmation stays open while its request runs, ignores Escape and Cancel then, and sends one request per confirmation (a ref guard besides `PendingButton`'s, since a fast double tap can land before the button turns to "Leaving…"). Leave and Delete stay pending through the exit, until the page is gone. A Leave that fails (409, network) closes its dialog with the toast. A Delete that fails on the name keeps the dialog open with "Church name did not match." under the box (focused, `aria-invalid`, described by the message); any other failure closes it with the toast (a role refusal also turns the page to the admin form).
9. **[owner-visible] Every new user-facing string** (S's words, no em dashes): page and nav "Danger zone"; the note "Only the owner can transfer ownership or delete the church."; "Loading" (the skeletons' name for screen readers, as on every Settings page). Leave: "Leave {church}", "You'll lose access to {church}'s services, hymns and settings. To come back you'll need a new invite.", "You're the owner. Transfer ownership below before you leave.", "You're the only person in {church}. To stop using it, delete the church below.", "Leave church…", "Leave {church}?", "You'll lose access right away. Your unsaved draft for {church} on this device will be discarded.", "Leave church" ("Leaving…"), "You left {church}.". Transfer: "Transfer ownership", "The new owner can transfer ownership and delete the church. You'll become an admin.", "New owner", "Choose a person", "{name} ({email})" or "{email}", "Transfer ownership…", "Make {name} the owner?", "{name} will become the owner of {church} and you'll become an admin. Only the new owner can transfer ownership back.", "Transfer ownership" ("Transferring…"), "Ownership transferred. You are now an admin.", "Invite another member first to transfer ownership." with the link "Invite someone". Delete: "Delete {church}", "Deleting {church} removes it for everyone. Pending invite links stop working.", "Delete church…", "Delete {church}?", "This removes {church} for all {n} people in it. They'll lose access to its services, hymns, contacts and settings. Your unsaved draft for {church} on this device will be discarded. This can't be undone." (for the owner alone, the proper singular of 6b-2a's answer: "This removes {church}. You're the only person in it, and you'll lose access to its services, hymns, contacts and settings. Your unsaved draft …"), "Type {church} to confirm", "Delete church" ("Deleting…"), "Church deleted.". The exit: "Can't reach the server. Check your connection and try again." (S's words, when `/me` does not come back). From the server (6b-1's, shown as they come): "Transfer ownership before you leave. If you're the only person in the church, delete it instead.", "You're the last admin. Make someone else an admin before you leave.", "Only the owner can do that.", "Member not found.", "Choose someone else to be the new owner.", "Church name did not match.".
10. **Cards** (S UX 2: "Destructive cards have a `border-destructive/40` outline"): Leave and Delete are outlined that way; Transfer has the plain border. The buttons: **Leave church…** outline, **Transfer ownership…** primary, **Delete church…** destructive; each `size="touch"` (44 px on phones).
11. **Deviations from S** (each the lean or the safer choice): the role refusal per hook, not a meta (2c); the layout's two guarded toasts (2d); `useMembershipChanged`'s boolean (2b); `ConfirmDialog`'s `confirmDisabled` (2f); a note instead of an alert (2g); both names trimmed (4); the email alone for a person with no name (6); the singular Delete body (9); no separate `DeleteChurchDialog` file (1).

### Risks
- **A leave or delete in another tab.** That tab keeps the church until its next request, which answers 403 `no_church_access`; its layout then says "You no longer have access to {church}." (the mark is per tab) and moves on. A builder open there may write its draft back; the next full load's prune removes it (S "Draft store").
- **A late 403 after the 60 s mark** (a very slow request for the church just left) would show the toast; the exit cancels every request for the church first, so none is in flight.
- **The phone check deletes a real (throwaway) church in production.** Deletion is 6b-1's soft delete: the church's rows stay and its invites are revoked; nothing else is touched. The check uses a church made for it ("Delete me"), never the real church or the test churches, and the agent names the church in every step.
- **The second Google account ends with no church** after it deletes "Delete me" (it lands on the welcome page); that is expected and harmless.
- **A Vercel preview** behaves the same; the phone check uses production.

### Lessons carried (the 6b-1 and 6b-2a plans and their reviews and records)
- **No SQL in chat as a pasteable block** (the 6b-1 and 6b-2a records): this slice has none; T7 says so, and T8's after-deploy check is the health check and the page's redirect only.
- A role 403 is toasted and refetches the role without leaving the church; a lost church is the app's; both are tested on the page (6a-1, 6b-2a).
- Long user text wraps at 375 px (6b-2a build review 1): the cards' titles and texts, both dialogs and the typed-name label carry `[overflow-wrap:anywhere]`; a test checks it with a long name.
- Confirmations keep their subject while they close and ignore Cancel while the write runs; focus never drops to the page when the card is gone (5b-1, 6a-3b, 6b-2a).
- Each important rule has a test that fails when the rule breaks, proved by planting the violation (6b-2a's mutation checks; see "Build notes").
- The phone check goes one short step at a time, and the record holds what the screens showed, never an id, an email or a link.

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `frontend/src/lib/church-exit.ts` (+ `church-exit.test.ts`) | `runChurchExit`, `useExitChurch`, `EXIT_ME_FAILED` | T2 |
| `frontend/src/app/(signed-in)/(church)/settings/danger/page.tsx` | the route | T3 |
| `frontend/src/components/settings/danger/danger-zone-page.tsx`, `leave-church-card.tsx`, `transfer-ownership-card.tsx`, `delete-church-card.tsx` (+ `danger-zone-page.test.tsx`) | the page and its three cards | T3 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `frontend/src/lib/church.ts` (+ `church.test.ts`) | `markChurchExited`, `wasChurchExited`, `EXITED_MARK_MS`, `resetExitedChurchesForTests` | T1 |
| `frontend/src/lib/settings/people.ts` (+ `people.test.ts`) | `leaveBlock`, `deleteNameMatches`, `transferCandidates`, `transferChoiceLabel` | T1 |
| `frontend/src/test/setup-dom.ts` | the marks' reset after each DOM test | T1 |
| `frontend/src/lib/queries/membership.ts` (+ `membership.test.tsx`) | resolves to whether `/me` came back | T2 |
| `frontend/src/app/(signed-in)/(church)/layout.tsx` (+ `church-layout.test.tsx`) | no lost-access toast for a church just left or deleted here | T2 |
| `frontend/src/lib/api/types.ts` | `TransferOwnershipBody`, `ChurchLeft`, `DeleteChurchBody` | T3 |
| `frontend/src/lib/queries/people.ts` | `onRoleRefused` and `onWriteError` exported | T3 |
| `frontend/src/lib/queries/church.ts` | `useTransferOwnership`, `useLeaveChurch`, `useDeleteChurch`, `deleteNameError` and the toasts | T3 |
| `frontend/src/components/app/confirm-dialog.tsx` (+ `confirm-dialog.test.tsx`) | `confirmDisabled` | T3 |
| `frontend/src/components/settings/sections.ts`, `settings-layout.test.tsx` | Danger zone last | T4 |
| `docs/manual-verification.md` | "## Slice 6b": items 18-25 | T5 |
| `docs/ops-runbook.md` | "### Slice 6b-2a record" rides along (already on the branch); "### Slice 6b-2b record" is T8's records PR | T8 |

**Counts in the PR:** 27 paths: 9 added (this plan and the eight new code and test files above) and 18 modified (the seventeen code, test and doc paths above, and `docs/ops-runbook.md`, which rides along with the 6b-2a record until merged; the runbook's own T8 change goes in the records PR); none deleted. **Untouched:** everything under `backend/`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`, `frontend/src/lib/queries/client.ts`, `frontend/src/components/ui`, `requirements*.txt`, `frontend/package*.json`, `.github`, `pytest.ini`, `app.py`, `streamlit_views`, `streamlit_tests`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`.

**Task order and review batch:** T1 → T5, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T6 verifies; T7 is the pre-merge note; T8 opens the draft PR on the owner's yes, merges on the owner's yes, checks production, runs the phone check and writes the record.

---
## The rules and the exit (T1-T2)

### Task 1: The exit mark and the Danger zone rules (S "Pure helpers", "Change to slice 1's `(church)` layout"; Testing → Frontend unit; clarifications 3-6)

**Files:**
- Modify: `frontend/src/lib/church.ts`, `frontend/src/lib/church.test.ts`, `frontend/src/lib/settings/people.ts`, `frontend/src/lib/settings/people.test.ts`, `frontend/src/test/setup-dom.ts`

The mark lasts 60 s for one church and is then forgotten. The owner, and only the owner, is kept from leaving, with or without others, which is exactly the shared role-policy fixture's `owner_must_transfer` leave rows. The typed name matches only exactly, capitals included, spaces around it ignored. The New owner list is everyone else, admins first, named with their email, or the email alone.

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/lib/church.test.ts`, replace:**

````ts
import { describe, expect, it } from "vitest";

import { type Church, isAdmin, pickActiveChurch, roleLabel } from "./church";
````

**with:**

````ts
import { afterEach, describe, expect, it } from "vitest";

import {
  type Church,
  isAdmin,
  markChurchExited,
  pickActiveChurch,
  resetExitedChurchesForTests,
  roleLabel,
  wasChurchExited,
} from "./church";
````

**In `frontend/src/lib/church.test.ts`, replace:**

````ts
    expect((["owner", "admin", "member"] as const).map(isAdmin)).toEqual([true, true, false]);
  });
});
````

**with:**

````ts
    expect((["owner", "admin", "member"] as const).map(isAdmin)).toEqual([true, true, false]);
  });
});

describe("markChurchExited / wasChurchExited (slice 6b-2b)", () => {
  afterEach(() => resetExitedChurchesForTests());

  it("marks one church for 60 seconds, then forgets it", () => {
    markChurchExited("c1", 1_000);
    expect(wasChurchExited("c1", 1_000)).toBe(true);
    expect(wasChurchExited("c1", 60_999)).toBe(true);
    expect(wasChurchExited("c2", 1_000)).toBe(false);
    expect(wasChurchExited("c1", 61_000)).toBe(false);
    expect(wasChurchExited("c1", 1_000)).toBe(false); // the expired mark is gone
  });
});
````

**In `frontend/src/lib/settings/people.test.ts`, replace:**

````ts
import {
  displayName,
````

**with:**

````ts
import {
  deleteNameMatches,
  displayName,
````

**In `frontend/src/lib/settings/people.test.ts`, replace:**

````ts
  memberActions,
  otherReusableInvites,
````

**with:**

````ts
  leaveBlock,
  memberActions,
  otherReusableInvites,
  transferCandidates,
  transferChoiceLabel,
````

**In `frontend/src/lib/settings/people.test.ts`, replace:**

````ts
  new_role?: "member" | "admin";
  expected: string;
````

**with:**

````ts
  new_role?: "member" | "admin";
  admin_count?: number;
  expected: string;
````

**In `frontend/src/lib/settings/people.test.ts`, replace:**

````ts
    expect(invitesCreatedBy([], PEOPLE.ann)).toBe(0);
  });
});
````

**with:**

````ts
    expect(invitesCreatedBy([], PEOPLE.ann)).toBe(0);
  });
});

describe("the Danger zone rules (slice 6b-2b)", () => {
  it("keeps the owner from leaving, with or without others, and nobody else", () => {
    expect(leaveBlock("owner", 2)).toBe("owner_with_others");
    expect(leaveBlock("owner", 1)).toBe("owner_alone");
    expect(leaveBlock("admin", 1)).toBeNull();
    expect(leaveBlock("admin", 5)).toBeNull();
    expect(leaveBlock("member", 1)).toBeNull();
  });

  it("blocks exactly the shared fixture's leave rows the server refuses for the owner", () => {
    const leaves = POLICY.rows.filter((r) => r.action === "leave");
    expect(leaves).toHaveLength(7);
    for (const row of leaves) {
      const blocked = leaveBlock(row.actor_role, Math.max(row.admin_count ?? 1, 1)) !== null;
      expect([row.actor_role, row.admin_count, blocked]).toEqual([
        row.actor_role,
        row.admin_count,
        row.expected === "owner_must_transfer",
      ]);
    }
  });

  it("matches the typed name only exactly, capitals included, spaces around it ignored", () => {
    expect(deleteNameMatches("Grace", "Grace")).toBe(true);
    expect(deleteNameMatches("  Grace ", "Grace")).toBe(true);
    expect(deleteNameMatches("grace", "Grace")).toBe(false);
    expect(deleteNameMatches("GRACE", "Grace")).toBe(false);
    expect(deleteNameMatches("Grac", "Grace")).toBe(false);
    expect(deleteNameMatches("Gr ace", "Grace")).toBe(false);
    expect(deleteNameMatches("", "Grace")).toBe(false);
    expect(deleteNameMatches("St. Mark's", "St. Mark's")).toBe(true);
  });

  it("offers everyone else as the new owner, admins first, and names them with their email", () => {
    const people = [
      member({ user_id: PEOPLE.olive, email: "olive@example.com", name: "Olive Owner", role: "owner", is_me: true }),
      member({ user_id: PEOPLE.ann, email: "ann@example.com", name: "Ann Admin", role: "admin" }),
      member(),
      member({ user_id: PEOPLE.sam, email: "sam@example.com", name: null, role: "member" }),
      member({ user_id: PEOPLE.mo + "-2", email: "zed@example.com", name: "Zed Admin", role: "admin" }),
    ];
    expect(transferCandidates(people).map(transferChoiceLabel)).toEqual([
      "Ann Admin (ann@example.com)",
      "Zed Admin (zed@example.com)",
      "Mo Member (mo@example.com)",
      "sam@example.com",
    ]);
    expect(transferCandidates([people[0]])).toEqual([]);
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/church.test.ts 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx vitest run src/lib/settings/people.test.ts 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`
**Expected:**
```
   × markChurchExited / wasChurchExited (slice 6b-2b) > marks one church for 60 seconds, then forgets it
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/church.test.ts > markChurchExited / wasChurchExited (slice 6b-2b) > marks one church for 60 seconds, then forgets it
 FAIL  |unit| src/lib/church.test.ts > markChurchExited / wasChurchExited (slice 6b-2b) > marks one church for 60 seconds, then forgets it
      Tests  1 failed | 7 passed (8)
```
```
   × the Danger zone rules (slice 6b-2b) > keeps the owner from leaving, with or without others, and nobody else
   × the Danger zone rules (slice 6b-2b) > blocks exactly the shared fixture's leave rows the server refuses for the owner
   × the Danger zone rules (slice 6b-2b) > matches the typed name only exactly, capitals included, spaces around it ignored
   × the Danger zone rules (slice 6b-2b) > offers everyone else as the new owner, admins first, and names them with their email
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 4 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/settings/people.test.ts > the Danger zone rules (slice 6b-2b) > keeps the owner from leaving, with or without others, and nobody else
 FAIL  |unit| src/lib/settings/people.test.ts > the Danger zone rules (slice 6b-2b) > blocks exactly the shared fixture's leave rows the server refuses for the owner
 FAIL  |unit| src/lib/settings/people.test.ts > the Danger zone rules (slice 6b-2b) > matches the typed name only exactly, capitals included, spaces around it ignored
 FAIL  |unit| src/lib/settings/people.test.ts > the Danger zone rules (slice 6b-2b) > offers everyone else as the new owner, admins first, and names them with their email
      Tests  4 failed | 19 passed (23)
```

- [ ] **Step 3: The mark, the rules and the reset**

**Append to `frontend/src/lib/church.ts`:**

````ts

// --- Slice 6b-2b: a church the user just left or deleted ------------------------------------------------------

/** How long `markChurchExited` lasts (6b spec "Change to slice 1's (church) layout"). */
export const EXITED_MARK_MS = 60_000;

// When each church was marked, by id. Module state: one tab, never stored.
const exitedAt = new Map<string, number>();

/**
 * Marks `id` as a church the user has just left or deleted here
 * (`runChurchExit`'s first step), so the `(church)` layout re-picks quietly
 * instead of saying "You no longer have access to {name}." for it.
 */
export function markChurchExited(id: string, at: number = Date.now()): void {
  exitedAt.set(id, at);
}

/**
 * True for 60 s after `markChurchExited(id)`. A later loss of the same church
 * (rejoined, then removed) shows the toast again.
 */
export function wasChurchExited(id: string, now: number = Date.now()): boolean {
  const at = exitedAt.get(id);
  if (at === undefined) return false;
  if (now - at < EXITED_MARK_MS) return true;
  exitedAt.delete(id);
  return false;
}

/** Forget every mark (test isolation). */
export function resetExitedChurchesForTests(): void {
  exitedAt.clear();
}
````

**Append to `frontend/src/lib/settings/people.ts`:**

````ts

// --- Slice 6b-2b: the Danger zone ---------------------------------------------------------------------------

/**
 * Why Leave church is off (6b spec UX 2a): the owner must transfer first
 * ("owner_with_others") or, alone, delete the church ("owner_alone"); null
 * for an admin or a member, who may leave (the server still refuses the last
 * admin of a church with no owner, and that answer is toasted).
 */
export function leaveBlock(role: Church["role"], memberCount: number): "owner_with_others" | "owner_alone" | null {
  if (role !== "owner") return null;
  return memberCount > 1 ? "owner_with_others" : "owner_alone";
}

/**
 * Delete church's typed name (6b spec UX 2c): equal to the church's name once
 * both are trimmed, exactly, capitals included, as the server compares them.
 */
export function deleteNameMatches(typed: string, name: string): boolean {
  return typed.trim() === name.trim();
}

/** Who can become the owner (6b spec UX 2b): everyone else in the church, admins first, each in the list's order. */
export function transferCandidates(members: readonly Member[]): Member[] {
  const others = members.filter((m) => !m.is_me && m.role !== "owner");
  return [...others.filter((m) => m.role === "admin"), ...others.filter((m) => m.role !== "admin")];
}

/** A person in the New owner list: "{name} ({email})", or the email alone when there is no name. */
export function transferChoiceLabel(member: Member): string {
  const name = displayName(member);
  return name === member.email ? member.email : `${name} (${member.email})`;
}
````

**In `frontend/src/test/setup-dom.ts`, replace:**

````ts
import { resetStoredChurchIdForTests } from "@/lib/church";
````

**with:**

````ts
import { resetExitedChurchesForTests, resetStoredChurchIdForTests } from "@/lib/church";
````

**In `frontend/src/test/setup-dom.ts`, replace:**

````ts
  resetStoredChurchIdForTests();
  // Task 18: the signing-out flag is module state; clear it after the tree is unmounted.
````

**with:**

````ts
  resetStoredChurchIdForTests();
  resetExitedChurchesForTests();
  // Task 18: the signing-out flag is module state; clear it after the tree is unmounted.
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/lib/church.test.ts 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx vitest run src/lib/settings/people.test.ts 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  8 passed (8)
```
```
      Tests  23 passed (23)
```
```
typecheck 0
lint 0
```
```
 Test Files  113 passed (113)
      Tests  1015 passed (1015)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/church.ts frontend/src/lib/church.test.ts frontend/src/lib/settings/people.ts frontend/src/lib/settings/people.test.ts frontend/src/test/setup-dom.ts
git commit -q -m "Slice 6b-2b: the exit mark and the Danger zone rules" -m "lib/church.ts: markChurchExited / wasChurchExited, a 60 s mark per church
(reset after every DOM test). lib/settings/people.ts: leaveBlock (the
owner must transfer first, or alone delete; checked against the shared
role-policy fixture's leave rows), deleteNameMatches (both trimmed, exact,
capitals included), transferCandidates (everyone else, admins first) and
transferChoiceLabel." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2236 passed, 49 skipped` (unchanged); frontend `1015 passed` in 113 files.

### Task 2: The quiet exit: `runChurchExit`, `useExitChurch` and the layout (S "`src/lib/church-exit.ts`", "Change to slice 1's `(church)` layout"; Testing → Frontend unit `runChurchExit`, DOM "`(church)` layout, exited church"; acceptance 15; clarifications 2a, 2b, 2d, 2e, 3)

**Files:**
- Create: `frontend/src/lib/church-exit.ts`, `frontend/src/lib/church-exit.test.ts`
- Modify: `frontend/src/lib/queries/membership.ts`, `frontend/src/lib/queries/membership.test.tsx`, `frontend/src/app/(signed-in)/(church)/layout.tsx`, `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx`

`runChurchExit` is pinned step by step with spies: the church is already marked when its requests are cancelled, then both draft keys go, then `membershipChanged({selectChurchId: null})`, then the cache; the draft keys and the cache go even when `/me` does not come back or the call throws, and the answer says so. `useMembershipChanged` resolves `true` or `false`. The layout, inside the real `(signed-in)` layout: a 403 for a marked church re-picks the next church and refetches `/me` with no toast; a `/me` that stops listing a marked church does the same; a mark 60 s old no longer hides the toast (slice 1's own tests keep the toast for an unmarked church).

- [ ] **Step 1: Write the failing tests**

**Create `frontend/src/lib/church-exit.test.ts`:**

````ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { resetExitedChurchesForTests, wasChurchExited } from "@/lib/church";
import type { MembershipChange } from "@/lib/queries/membership";

import { runChurchExit } from "./church-exit";

afterEach(() => resetExitedChurchesForTests());

/** A QueryClient, `membershipChanged` and `removeLocal` that write what they are asked into `log`. */
function spies(membershipChanged: (change: MembershipChange) => Promise<boolean> = async () => true) {
  const log: string[] = [];
  const queryClient = {
    cancelQueries: vi.fn(async (filters: { queryKey: readonly unknown[] }) => {
      log.push(`cancel ${JSON.stringify(filters.queryKey)} exited=${wasChurchExited("c1")}`);
    }),
    removeQueries: vi.fn((filters: { queryKey: readonly unknown[] }) => {
      log.push(`remove ${JSON.stringify(filters.queryKey)}`);
    }),
  };
  const changed = vi.fn(async (change: MembershipChange) => {
    log.push(`membershipChanged ${JSON.stringify(change)}`);
    return membershipChanged(change);
  });
  const removeLocal = vi.fn((key: string) => {
    log.push(`removeLocal ${key}`);
  });
  return { log, queryClient, changed, removeLocal };
}

describe("runChurchExit (slice 6b-2b)", () => {
  it("marks the church, cancels its requests, drops its draft keys, then /me, then its cache, in that order", async () => {
    const { log, queryClient, changed, removeLocal } = spies();
    const meLoaded = await runChurchExit({ churchId: "c1", userId: "u1", queryClient, membershipChanged: changed, removeLocal });
    expect(meLoaded).toBe(true);
    expect(log).toEqual([
      'cancel ["church","c1"] exited=true',
      "removeLocal wsb:draft:u1:c1",
      "removeLocal wsb:draft-corrupt:u1:c1",
      'membershipChanged {"selectChurchId":null}',
      'remove ["church","c1"]',
    ]);
    expect(wasChurchExited("c1")).toBe(true);
    expect(wasChurchExited("c2")).toBe(false);
  });

  it("still drops the draft keys and the cache when /me does not come back, and says so", async () => {
    const failed = spies(async () => false);
    expect(
      await runChurchExit({ churchId: "c1", userId: "u1", queryClient: failed.queryClient, membershipChanged: failed.changed, removeLocal: failed.removeLocal }),
    ).toBe(false);
    expect(failed.removeLocal.mock.calls.map(([key]) => key)).toEqual(["wsb:draft:u1:c1", "wsb:draft-corrupt:u1:c1"]);
    expect(failed.queryClient.removeQueries).toHaveBeenCalledWith({ queryKey: ["church", "c1"] });

    const threw = spies(async () => {
      throw new Error("offline");
    });
    expect(
      await runChurchExit({ churchId: "c1", userId: "u1", queryClient: threw.queryClient, membershipChanged: threw.changed, removeLocal: threw.removeLocal }),
    ).toBe(false);
    expect(threw.log.at(-1)).toBe('remove ["church","c1"]');
  });
});
````

**In `frontend/src/lib/queries/membership.test.tsx`, replace:**

````tsx
  });
});
````

**with:**

````tsx
  });

  it("resolves to whether /me came back (slice 6b-2b)", async () => {
    const api = installFakeApi({ "GET /me": me() });
    const { changed } = renderMembershipChanged();
    let loaded: boolean | undefined;
    await act(async () => {
      loaded = await changed({ selectChurchId: null });
    });
    expect(loaded).toBe(true);

    api.set("GET /me", fakeError(503, "db_unavailable", "The database is unavailable."));
    await act(async () => {
      loaded = await changed({ selectChurchId: null });
    });
    expect(loaded).toBe(false);
    expect(testRouter.replace).toHaveBeenCalledTimes(2);
  });
});
````

**In `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx`, replace:**

````tsx
import type { Church } from "@/lib/church";
````

**with:**

````tsx
import { type Church, markChurchExited } from "@/lib/church";
````

**In `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx`, replace:**

````tsx
  });
});
````

**with:**

````tsx
  });

  it("re-picks without the toast after a 403 for a church just left or deleted here (slice 6b-2b)", async () => {
    markChurchExited(GRACE.id);
    const api = installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(HOPE),
    });

    renderShell();

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    await waitFor(() => expect(meRequests(api)).toHaveLength(2));
    expect(churchRequests(api)).toEqual([GRACE.id, HOPE.id]);
    expect(toastError).not.toHaveBeenCalled();
  });

  it("stays quiet when /me stops listing a church just left or deleted here (slice 6b-2b)", async () => {
    let meCalls = 0;
    installFakeApi({
      "GET /me": () => {
        meCalls += 1;
        return meCalls === 1 ? me({ churches: [GRACE, HOPE] }) : me({ churches: [HOPE] });
      },
      "GET /church": churchById(GRACE, HOPE),
    });
    const { queryClient } = renderShell();
    expect(await screen.findByText("Showing Grace")).toBeInTheDocument();

    markChurchExited(GRACE.id);
    await act(async () => {
      await queryClient.invalidateQueries({ queryKey: keys.me() });
    });

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(toastError).not.toHaveBeenCalled();
  });

  it("says so again once the mark is 60 seconds old (slice 6b-2b)", async () => {
    markChurchExited(GRACE.id, Date.now() - 60_000);
    installFakeApi({
      "GET /me": me({ churches: [GRACE, HOPE] }),
      "GET /church": churchById(HOPE),
    });

    renderShell();

    expect(await screen.findByText("Showing Hope")).toBeInTheDocument();
    expect(toastError).toHaveBeenCalledTimes(1);
    expect(toastError).toHaveBeenCalledWith("You no longer have access to Grace.");
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/church-exit.test.ts 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx vitest run src/lib/queries/membership.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx vitest run "src/app/(signed-in)/(church)/church-layout.test.tsx" 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`
**Expected:**
```
 FAIL  |unit| src/lib/church-exit.test.ts [ src/lib/church-exit.test.ts ]
      Tests  no tests
```
```
   × useMembershipChanged > resolves to whether /me came back (slice 6b-2b)
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |dom| src/lib/queries/membership.test.tsx > useMembershipChanged > resolves to whether /me came back (slice 6b-2b)
      Tests  1 failed | 5 passed (6)
```
```
   × (church) layout > re-picks without the toast after a 403 for a church just left or deleted here (slice 6b-2b)
   × (church) layout > stays quiet when /me stops listing a church just left or deleted here (slice 6b-2b)
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |dom| src/app/(signed-in)/(church)/church-layout.test.tsx > (church) layout > re-picks without the toast after a 403 for a church just left or deleted here (slice 6b-2b)
 FAIL  |dom| src/app/(signed-in)/(church)/church-layout.test.tsx > (church) layout > stays quiet when /me stops listing a church just left or deleted here (slice 6b-2b)
      Tests  2 failed | 16 passed (18)
```

- [ ] **Step 3: The exit and the layout's two quiet paths**

**In `frontend/src/lib/queries/membership.ts`, replace:**

````ts
 * itself succeeded, so the caller still shows its success toast.
````

**with:**

````ts
 * itself succeeded, so the caller still shows its success toast. It resolves
 * to whether `/me` came back (slice 6b-2b: a leave or delete says so when it
 * did not).
````

**In `frontend/src/lib/queries/membership.ts`, replace:**

````ts
export function useMembershipChanged(): (change: MembershipChange) => Promise<void> {
````

**with:**

````ts
export function useMembershipChanged(): (change: MembershipChange) => Promise<boolean> {
````

**In `frontend/src/lib/queries/membership.ts`, replace:**

````ts
      let hasChurch = true;
      try {
````

**with:**

````ts
      let hasChurch = true;
      let meLoaded = false;
      try {
````

**In `frontend/src/lib/queries/membership.ts`, replace:**

````ts
        hasChurch = me.churches.length > 0;
      } catch {
````

**with:**

````ts
        hasChurch = me.churches.length > 0;
        meLoaded = true;
      } catch {
````

**In `frontend/src/lib/queries/membership.ts`, replace:**

````ts
      router.replace(hasChurch ? "/" : "/welcome");
    },
````

**with:**

````ts
      router.replace(hasChurch ? "/" : "/welcome");
      return meLoaded;
    },
````

**Create `frontend/src/lib/church-exit.ts`:**

````ts
/**
 * Leaving a church the user has just left or deleted (slice 6b-2b; 6b spec
 * "Frontend changes", `src/lib/church-exit.ts`). `runChurchExit` is the pure
 * order of steps, unit-tested; `useExitChurch` binds it to the app and is
 * what `useLeaveChurch` and `useDeleteChurch` call after the server said yes:
 *
 * 1. `markChurchExited(id)`: the `(church)` layout then re-picks quietly
 *    instead of saying "You no longer have access to {name}." for it;
 * 2. cancel every request for the church, so none finishes into a 403;
 * 3. remove this user's draft and corrupt-draft keys for it, so the dialogs'
 *    "Your unsaved draft … will be discarded" is true at once;
 * 4. slice 1's `useMembershipChanged({ selectChurchId: null })`: `/me` again
 *    (the server no longer lists the church), then `/` or `/welcome`; the
 *    layout re-picks from the new `/me`;
 * 5. remove the church's cached queries.
 *
 * If step 4's `/me` does not come back, `useExitChurch` says so; the
 * `(signed-in)` layout then shows its error state with Retry.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { toast } from "sonner";

import { markChurchExited } from "@/lib/church";
import { corruptDraftKey, draftKey } from "@/lib/draft/schema";
import { useMeContext } from "@/lib/me-context";
import { keys } from "@/lib/queries/keys";
import { type MembershipChange, useMembershipChanged } from "@/lib/queries/membership";
import { removeLocal } from "@/lib/storage";

/** The toast when `/me` did not come back after a leave or delete. */
export const EXIT_ME_FAILED = "Can't reach the server. Check your connection and try again.";

export type ChurchExit = {
  churchId: string;
  userId: string;
  /** The app's QueryClient, or a test's spies. */
  queryClient: {
    cancelQueries(filters: { queryKey: readonly unknown[] }): Promise<void>;
    removeQueries(filters: { queryKey: readonly unknown[] }): void;
  };
  membershipChanged(change: MembershipChange): Promise<boolean>;
  removeLocal(key: string): void;
};

/** The five steps above, in order. Resolves to whether `/me` came back; never throws. */
export async function runChurchExit({
  churchId,
  userId,
  queryClient,
  membershipChanged,
  removeLocal: remove,
}: ChurchExit): Promise<boolean> {
  markChurchExited(churchId);
  const queryKey = keys.church(churchId);
  await queryClient.cancelQueries({ queryKey });
  remove(draftKey(userId, churchId));
  remove(corruptDraftKey(userId, churchId));
  let meLoaded = false;
  try {
    meLoaded = await membershipChanged({ selectChurchId: null });
  } catch {
    meLoaded = false;
  }
  queryClient.removeQueries({ queryKey });
  return meLoaded;
}

/** `runChurchExit` for the signed-in user, with the toast when `/me` did not come back. */
export function useExitChurch(): (churchId: string) => Promise<void> {
  const queryClient = useQueryClient();
  const membershipChanged = useMembershipChanged();
  const userId = useMeContext().user.id;
  return useCallback(
    async (churchId: string) => {
      const meLoaded = await runChurchExit({ churchId, userId, queryClient, membershipChanged, removeLocal });
      if (!meLoaded) toast.error(EXIT_ME_FAILED);
    },
    [queryClient, membershipChanged, userId],
  );
}
````

**In `frontend/src/app/(signed-in)/(church)/layout.tsx`, replace:**

````tsx
 *    before the 403 on refocus) toasts the same message once.
````

**with:**

````tsx
 *    before the 403 on refocus) toasts the same message once. Neither path
 *    toasts for a church the user has just left or deleted here
 *    (`wasChurchExited`, slice 6b-2b): it is still excluded and `/me`
 *    refetched, so the next church is picked quietly.
````

**In `frontend/src/app/(signed-in)/(church)/layout.tsx`, replace:**

````tsx
import { type Church, pickActiveChurch, storeChurchId, useStoredChurchId } from "@/lib/church";
````

**with:**

````tsx
import { type Church, pickActiveChurch, storeChurchId, useStoredChurchId, wasChurchExited } from "@/lib/church";
````

**In `frontend/src/app/(signed-in)/(church)/layout.tsx`, replace:**

````tsx
      toast.error(`You no longer have access to ${candidateName}.`);
````

**with:**

````tsx
      if (!wasChurchExited(lostId)) toast.error(`You no longer have access to ${candidateName}.`);
````

**In `frontend/src/app/(signed-in)/(church)/layout.tsx`, replace:**

````tsx
    if (!me.churches.some((c) => c.id === shown.id)) {
````

**with:**

````tsx
    if (!me.churches.some((c) => c.id === shown.id) && !wasChurchExited(shown.id)) {
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/lib/church-exit.test.ts 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx vitest run src/lib/queries/membership.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx vitest run "src/app/(signed-in)/(church)/church-layout.test.tsx" 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  2 passed (2)
```
```
      Tests  6 passed (6)
```
```
      Tests  18 passed (18)
```
```
typecheck 0
lint 0
```
```
 Test Files  114 passed (114)
      Tests  1021 passed (1021)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/church-exit.ts frontend/src/lib/church-exit.test.ts frontend/src/lib/queries/membership.ts frontend/src/lib/queries/membership.test.tsx "frontend/src/app/(signed-in)/(church)/layout.tsx" "frontend/src/app/(signed-in)/(church)/church-layout.test.tsx"
git commit -q -m "Slice 6b-2b: the quiet exit after a leave or delete" -m "lib/church-exit.ts: runChurchExit marks the church, cancels its requests,
removes its draft keys, runs useMembershipChanged({selectChurchId: null})
and removes its cache, in that order; useExitChurch toasts when /me did not
come back. useMembershipChanged now resolves to whether /me came back. The
(church) layout's two lost-access toasts (the 403 event and a /me that no
longer lists the shown church) skip a church marked as just left here." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2236 passed, 49 skipped` (unchanged); frontend `1021 passed` in 114 files.

## The page and the nav (T3-T4)

### Task 3: Settings → Danger zone: the hooks, the page and its three cards (S UX §2, "Losing a role mid-session", "Queries and mutations" (the transfer, leave and delete rows); Testing → Frontend DOM "DangerZonePage"; acceptance 15, 16, 18; clarifications 1, 2c, 2f-2h, 4-10)

**Files:**
- Create: `frontend/src/app/(signed-in)/(church)/settings/danger/page.tsx`, `frontend/src/components/settings/danger/danger-zone-page.tsx`, `frontend/src/components/settings/danger/leave-church-card.tsx`, `frontend/src/components/settings/danger/transfer-ownership-card.tsx`, `frontend/src/components/settings/danger/delete-church-card.tsx`, `frontend/src/components/settings/danger/danger-zone-page.test.tsx`
- Modify: `frontend/src/lib/api/types.ts`, `frontend/src/lib/queries/people.ts`, `frontend/src/lib/queries/church.ts`, `frontend/src/components/app/confirm-dialog.tsx`, `frontend/src/components/app/confirm-dialog.test.tsx`

`ConfirmDialog`'s confirm stays off while `confirmDisabled` holds. The page: an admin and a member see the note and Leave only, and the page asks for nothing; Leave, inside the real `(signed-in)` and `(church)` layouts, asks first, sends `POST /church/leave` once with `X-Church-Id`, toasts "You left Grace.", removes both draft keys, goes to `/` and shows the next church (Hope) with no "no longer have access" text and no error toast; a double tap sends one leave; a 409 is toasted and the dialog closes; a `/me` that does not come back is said. The owner: Leave off with each of the two sentences, both destructive cards outlined; Transfer lists the others admins first, stays off until one is chosen, asks, sends `{user_id}`, toasts, refetches the profile, `/me` and the members, and inside the church layout turns to the admin form; a role refusal is toasted and refetches without leaving the church; alone, "Invite another member first…" with the link to People. Delete is off for every wrong spelling and on for " Grace ", sends `{"confirm_name":" Grace "}`, toasts "Church deleted." and exits quietly; the server's 422 shows under the box and focuses it; a double tap sends one delete; the body is singular for the owner alone. A long church name wraps in the cards, both dialogs and the label; nothing the page says, in any state, has an em dash. ErrorState with Retry when the members cannot be read.

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/components/app/confirm-dialog.test.tsx`, replace:**

````tsx
  });
});
````

**with:**

````tsx
  });

  it("keeps the confirm button off while confirmDisabled holds (slice 6b-2b)", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    const { rerender } = render(
      <ConfirmDialog open onOpenChange={() => {}} title="Delete Grace?" confirmLabel="Delete church"
        onConfirm={onConfirm} destructive confirmDisabled />,
    );
    const dialog = await screen.findByRole("alertdialog", { name: "Delete Grace?" });
    const confirm = within(dialog).getByRole("button", { name: "Delete church" });
    expect(confirm).toBeDisabled();
    await user.click(confirm);
    expect(onConfirm).not.toHaveBeenCalled();
    rerender(
      <ConfirmDialog open onOpenChange={() => {}} title="Delete Grace?" confirmLabel="Delete church"
        onConfirm={onConfirm} destructive />,
    );
    expect(within(dialog).getByRole("button", { name: "Delete church" })).toBeEnabled();
    await user.click(within(dialog).getByRole("button", { name: "Delete church" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});
````

**Create `frontend/src/components/settings/danger/danger-zone-page.test.tsx`:**

````tsx
/**
 * Settings → Danger zone (slice 6b-2b; 6b spec UX §2 and Testing → Frontend
 * DOM): everyone may leave; only the owner transfers ownership or deletes the
 * church. Rendered inside the Settings layout, as the route is, with a
 * Toaster; the leave and delete exits also inside the real `(signed-in)` and
 * `(church)` layouts, so the switch to the next church and the absence of the
 * "no longer have access" toast are the app's own.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SignedInLayout from "@/app/(signed-in)/layout";
import ChurchLayout from "@/app/(signed-in)/(church)/layout";
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import DangerZoneRoute from "@/app/(signed-in)/(church)/settings/danger/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Member } from "@/lib/api/types";
import { EXIT_ME_FAILED } from "@/lib/church-exit";
import { authEvents } from "@/lib/queries/auth-events";
import { CHURCH_DELETED, leftChurch, TRANSFERRED } from "@/lib/queries/church";
import { keys } from "@/lib/queries/keys";
import { ACTIVE_CHURCH_KEY } from "@/lib/storage";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { CHURCH_IDS, USER_ID, church, member, memberList, me, PEOPLE } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { OWNER_ONLY_NOTE } from "./danger-zone-page";
import { deleteBody, deleteText } from "./delete-church-card";
import { leaveText, OWNER_MUST_TRANSFER, ownerAloneText } from "./leave-church-card";
import { INVITE_FIRST, TRANSFER_TEXT } from "./transfer-ownership-card";

/** Breaks a long name anywhere, so it wraps at 375 px instead of widening the page. */
const WRAP = "[overflow-wrap:anywhere]";

const GRACE_DRAFT = `wsb:draft:${USER_ID}:${CHURCH_IDS.grace}`;
const GRACE_CORRUPT = `wsb:draft-corrupt:${USER_ID}:${CHURCH_IDS.grace}`;

afterEach(() => {
  toast.dismiss();
});

/** Pat (`USER_ID`) as the only person in the church: the owner alone. */
function alone(): { items: Member[] } {
  return { items: [member({ user_id: USER_ID, email: "pat@example.com", name: "Pat Pastor", role: "owner", is_me: true })] };
}

/** The page inside the Settings layout, for Grace with `role` (a static church; no exit layouts). */
function renderPage(role: Church["role"] = "owner", routes: Record<string, FakeHandler> = {}, name = "Grace") {
  const active = church({ role, name });
  const api = installFakeApi({ "GET /members": memberList(role), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <DangerZoneRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/danger" },
  );
  return { ...view, api };
}

/**
 * The page inside the real `(signed-in)` and `(church)` layouts, Grace shown
 * (Pat is `role` there) and Hope (member) the other church. `POST
 * /church/leave` and `DELETE /church` take Grace out of `/me`, as the server
 * does; `GET /church` then refuses Grace.
 */
function renderShell(role: Church["role"], routes: Record<string, FakeHandler> = {}) {
  const grace = church({ role });
  const hope = church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" });
  let graceGone = false;
  const gone = (answer: unknown) => () => {
    graceGone = true;
    return answer;
  };
  window.localStorage.setItem(ACTIVE_CHURCH_KEY, grace.id);
  window.localStorage.setItem(GRACE_DRAFT, "{}");
  window.localStorage.setItem(GRACE_CORRUPT, "{}");
  const api = installFakeApi({
    "GET /me": () => me({ churches: graceGone ? [hope] : [grace, hope] }),
    "GET /church": (r: RecordedRequest) => {
      if (r.headers["X-Church-Id"] === hope.id) return hope;
      return graceGone
        ? fakeError(403, "forbidden", "You don't have access to this church.", { details: { reason: "no_church_access" } })
        : grace;
    },
    "GET /members": memberList(role),
    "POST /church/leave": gone({ left: true }),
    "DELETE /church": gone({ deleted: true }),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <SignedInLayout>
        <ChurchLayout>
          <SettingsLayout>
            <DangerZoneRoute />
          </SettingsLayout>
        </ChurchLayout>
      </SignedInLayout>
      <Toaster />
    </>,
    { path: "/settings/danger" },
  );
  return { ...view, api };
}

function sent(api: { requests: RecordedRequest[] }, method: string, path: string) {
  return api.requests.filter((r) => r.method === method && r.path === path);
}

/** Everything the page and its open dialogs say. */
function allText(): string {
  return document.body.textContent ?? "";
}

describe("Settings → Danger zone: admins and members (slice 6b-2b)", () => {
  it.each(["member", "admin"] as const)("shows %s the owner-only note and Leave church only", async (role) => {
    const { api } = renderPage(role);
    expect(await screen.findByRole("heading", { level: 2, name: "Danger zone" })).toBeInTheDocument();
    expect(screen.getByRole("note")).toHaveTextContent(OWNER_ONLY_NOTE);
    expect(OWNER_ONLY_NOTE).toBe("Only the owner can transfer ownership or delete the church.");
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Leave Grace"]);
    expect(screen.getByText(leaveText("Grace"))).toBeInTheDocument();
    expect(leaveText("Grace")).toBe(
      "You'll lose access to Grace's services, hymns and settings. To come back you'll need a new invite.",
    );
    expect(screen.getByRole("button", { name: "Leave church…" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Transfer ownership…" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Delete church…" })).toBeNull();
    expect(api.requests).toEqual([]);
  });

  it("leaves after asking, says so, drops the draft and moves to the next church with no access toast", async () => {
    const error = vi.spyOn(toast, "error");
    const { api, user } = renderShell("member");
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Leave Grace?" });
    expect(dialog).toHaveAccessibleDescription(
      "You'll lose access right away. Your unsaved draft for Grace on this device will be discarded.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Leave church" }));
    expect(await screen.findByText(leftChurch("Grace"))).toBeInTheDocument();
    expect(leftChurch("Grace")).toBe("You left Grace.");
    expect(await screen.findByRole("heading", { level: 3, name: "Leave Hope" })).toBeInTheDocument();
    expect(sent(api, "POST", "/church/leave")).toHaveLength(1);
    expect(sent(api, "POST", "/church/leave")[0].headers["x-church-id"]).toBe(CHURCH_IDS.grace);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(window.localStorage.getItem(GRACE_DRAFT)).toBeNull();
    expect(window.localStorage.getItem(GRACE_CORRUPT)).toBeNull();
    await waitFor(() => expect(window.localStorage.getItem(ACTIVE_CHURCH_KEY)).toBe(CHURCH_IDS.hope));
    expect(screen.queryByText(/no longer have access/)).toBeNull();
    expect(error).not.toHaveBeenCalled();
    error.mockRestore();
  });

  it("sends one leave for a double tap", async () => {
    let release: () => void = () => {};
    const { api, user } = renderPage("member", {
      "POST /church/leave": () => new Promise((resolve) => (release = () => resolve({ left: true }))),
      "GET /me": me(),
    });
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Leave Grace?" });
    await user.dblClick(within(dialog).getByRole("button", { name: "Leave church" }));
    expect(sent(api, "POST", "/church/leave")).toHaveLength(1);
    expect(await within(dialog).findByRole("button", { name: "Leaving…" })).toHaveAttribute("aria-disabled", "true");
    await user.click(within(dialog).getByRole("button", { name: "Leaving…" }));
    expect(sent(api, "POST", "/church/leave")).toHaveLength(1);
    release();
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/"));
    expect(sent(api, "POST", "/church/leave")).toHaveLength(1);
  });

  it("toasts the server's refusal, closes the dialog and stays", async () => {
    const message = "You're the last admin. Make someone else an admin before you leave.";
    const { user } = renderPage("admin", { "POST /church/leave": fakeError(409, "last_admin", message) });
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Leave Grace?" });
    await user.click(within(dialog).getByRole("button", { name: "Leave church" }));
    expect(await screen.findByText(message)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(testRouter.replace).not.toHaveBeenCalled();
    expect(screen.getByRole("heading", { level: 3, name: "Leave Grace" })).toBeInTheDocument();
  });

  it("says when /me does not come back after leaving", async () => {
    const { user } = renderPage("member", {
      "POST /church/leave": { left: true },
      "GET /me": fakeError(503, "db_unavailable", "The database is unavailable."),
    });
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Leave church" }));
    expect(await screen.findByText(EXIT_ME_FAILED)).toBeInTheDocument();
    expect(EXIT_ME_FAILED).toBe("Can't reach the server. Check your connection and try again.");
    expect(screen.getByText("You left Grace.")).toBeInTheDocument();
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });
});

describe("Settings → Danger zone: the owner (slice 6b-2b)", () => {
  it("shows Leave off with why, Transfer and Delete, and no owner-only note", async () => {
    renderPage("owner");
    expect(await screen.findByRole("heading", { level: 3, name: "Transfer ownership" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
      "Leave Grace",
      "Transfer ownership",
      "Delete Grace",
    ]);
    expect(screen.queryByRole("note")).toBeNull();
    expect(screen.getByRole("button", { name: "Leave church…" })).toBeDisabled();
    expect(screen.getByText(OWNER_MUST_TRANSFER)).toBeInTheDocument();
    expect(OWNER_MUST_TRANSFER).toBe("You're the owner. Transfer ownership below before you leave.");
    expect(screen.getByText(TRANSFER_TEXT)).toBeInTheDocument();
    expect(screen.getByText(deleteText("Grace"))).toBeInTheDocument();
    expect(deleteText("Grace")).toBe("Deleting Grace removes it for everyone. Pending invite links stop working.");
    for (const id of ["leave-title", "delete-title"]) {
      expect(document.getElementById(id)!.closest("section")).toHaveClass("border-destructive/40");
    }
  });

  it("tells the owner alone to delete instead of leaving, and to invite someone before a transfer", async () => {
    renderPage("owner", { "GET /members": alone() });
    expect(await screen.findByText(ownerAloneText("Grace"))).toBeInTheDocument();
    expect(ownerAloneText("Grace")).toBe("You're the only person in Grace. To stop using it, delete the church below.");
    expect(screen.getByRole("button", { name: "Leave church…" })).toBeDisabled();
    expect(screen.getByText(INVITE_FIRST, { exact: false })).toBeInTheDocument();
    expect(INVITE_FIRST).toBe("Invite another member first to transfer ownership.");
    expect(screen.getByRole("link", { name: "Invite someone" })).toHaveAttribute("href", "/settings/people");
    expect(screen.queryByRole("button", { name: "Transfer ownership…" })).toBeNull();
  });

  it("transfers to the person chosen, admins listed first, after asking", async () => {
    const { api, user, queryClient } = renderPage("owner", { "POST /church/transfer-ownership": memberList("admin") });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const start = await screen.findByRole("button", { name: "Transfer ownership…" });
    expect(start).toBeDisabled();
    await user.click(screen.getByRole("combobox", { name: "New owner" }));
    expect((await screen.findAllByRole("option")).map((o) => o.textContent)).toEqual([
      "Ann Admin (ann@example.com)",
      "Mo Member (mo@example.com)",
      "sam@example.com",
    ]);
    await user.click(screen.getByRole("option", { name: "Mo Member (mo@example.com)" }));
    expect(start).toBeEnabled();
    await user.click(start);
    const dialog = await screen.findByRole("alertdialog", { name: "Make Mo Member the owner?" });
    expect(dialog).toHaveAccessibleDescription(
      "Mo Member will become the owner of Grace and you'll become an admin. Only the new owner can transfer ownership back.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Transfer ownership" }));
    expect(await screen.findByText(TRANSFERRED)).toBeInTheDocument();
    expect(TRANSFERRED).toBe("Ownership transferred. You are now an admin.");
    expect(sent(api, "POST", "/church/transfer-ownership").map((r) => r.body)).toEqual([{ user_id: PEOPLE.mo }]);
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.me() });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
  });

  it("turns to the admin form inside the church layout once the transfer is done", async () => {
    window.localStorage.setItem(ACTIVE_CHURCH_KEY, church().id);
    let role: Church["role"] = "owner";
    installFakeApi({
      "GET /church": () => church({ role }),
      "GET /members": () => memberList(role),
      "POST /church/transfer-ownership": () => {
        role = "admin";
        return memberList("admin");
      },
    });
    const { user } = renderWithProviders(
      <>
        <ChurchLayout>
          <SettingsLayout>
            <DangerZoneRoute />
          </SettingsLayout>
        </ChurchLayout>
        <Toaster />
      </>,
      { me: me(), path: "/settings/danger" },
    );
    await user.click(await screen.findByRole("combobox", { name: "New owner" }));
    await user.click(await screen.findByRole("option", { name: "Ann Admin (ann@example.com)" }));
    await user.click(screen.getByRole("button", { name: "Transfer ownership…" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Transfer ownership" }));
    expect(await screen.findByRole("note")).toHaveTextContent(OWNER_ONLY_NOTE);
    expect(screen.getByText("You're an admin of Grace.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete church…" })).toBeNull();
    expect(screen.getByRole("button", { name: "Leave church…" })).toBeEnabled();
  });

  it("toasts a role refusal of the transfer and refetches the role and the members, staying in the church", async () => {
    const lost = vi.fn();
    const unsubscribe = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("owner", {
      "POST /church/transfer-ownership": fakeError(403, "forbidden", "Only the owner can do that."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.click(await screen.findByRole("combobox", { name: "New owner" }));
    await user.click(await screen.findByRole("option", { name: "Ann Admin (ann@example.com)" }));
    await user.click(screen.getByRole("button", { name: "Transfer ownership…" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Transfer ownership" }));
    expect(await screen.findByText("Only the owner can do that.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.members(church().id) });
    expect(lost).not.toHaveBeenCalled();
    unsubscribe();
  });

  it("deletes only after the exact name is typed, then says so and moves on with no access toast", async () => {
    const error = vi.spyOn(toast, "error");
    const { api, user } = renderShell("owner");
    await user.click(await screen.findByRole("button", { name: "Delete church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete Grace?" });
    expect(dialog).toHaveAccessibleDescription(deleteBody("Grace", 4));
    expect(deleteBody("Grace", 4)).toBe(
      "This removes Grace for all 4 people in it. They'll lose access to its services, hymns, contacts and settings. " +
        "Your unsaved draft for Grace on this device will be discarded. This can't be undone.",
    );
    const box = within(dialog).getByRole("textbox", { name: "Type Grace to confirm" });
    expect(box).toHaveAttribute("autocomplete", "off");
    expect(box).toHaveAttribute("autocapitalize", "off");
    const confirm = within(dialog).getByRole("button", { name: "Delete church" });
    expect(confirm).toBeDisabled();
    for (const wrong of ["grace", "GRACE", "Grac", "Grace."]) {
      await user.clear(box);
      await user.type(box, wrong);
      expect(confirm).toBeDisabled();
    }
    await user.click(confirm);
    expect(sent(api, "DELETE", "/church")).toEqual([]);
    await user.clear(box);
    await user.type(box, " Grace ");
    expect(confirm).toBeEnabled();
    await user.click(confirm);
    expect(await screen.findByText(CHURCH_DELETED)).toBeInTheDocument();
    expect(CHURCH_DELETED).toBe("Church deleted.");
    expect(await screen.findByRole("heading", { level: 3, name: "Leave Hope" })).toBeInTheDocument();
    expect(sent(api, "DELETE", "/church").map((r) => r.body)).toEqual([{ confirm_name: " Grace " }]);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(window.localStorage.getItem(GRACE_DRAFT)).toBeNull();
    expect(screen.queryByText(/no longer have access/)).toBeNull();
    expect(error).not.toHaveBeenCalled();
    error.mockRestore();
  });

  it("says when the server finds the name does not match, under the box, and focuses it", async () => {
    const { user } = renderPage("owner", {
      "DELETE /church": fakeError(422, "invalid_request", "Church name did not match.", {
        fields: { confirm_name: "Church name did not match." },
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Delete church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete Grace?" });
    const box = within(dialog).getByRole("textbox", { name: "Type Grace to confirm" });
    await user.type(box, "Grace");
    await user.click(within(dialog).getByRole("button", { name: "Delete church" }));
    expect(await within(dialog).findByText("Church name did not match.")).toBeInTheDocument();
    expect(box).toHaveFocus();
    expect(box).toHaveAttribute("aria-invalid", "true");
    expect(box).toHaveAccessibleDescription("Church name did not match.");
    expect(testRouter.replace).not.toHaveBeenCalled();
  });

  it("sends one delete for a double tap, and says so for the owner alone in the singular", async () => {
    let release: () => void = () => {};
    const { api, user } = renderPage("owner", {
      "GET /members": alone(),
      "GET /me": me({ churches: [] }),
      "DELETE /church": () => new Promise((resolve) => (release = () => resolve({ deleted: true }))),
    });
    await user.click(await screen.findByRole("button", { name: "Delete church…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete Grace?" });
    expect(dialog).toHaveAccessibleDescription(deleteBody("Grace", 1));
    expect(deleteBody("Grace", 1)).toBe(
      "This removes Grace. You're the only person in it, and you'll lose access to its services, hymns, contacts and settings. " +
        "Your unsaved draft for Grace on this device will be discarded. This can't be undone.",
    );
    await user.type(within(dialog).getByRole("textbox", { name: "Type Grace to confirm" }), "Grace");
    await user.dblClick(within(dialog).getByRole("button", { name: "Delete church" }));
    expect(sent(api, "DELETE", "/church")).toHaveLength(1);
    expect(await within(dialog).findByRole("button", { name: "Deleting…" })).toHaveAttribute("aria-disabled", "true");
    release();
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/welcome"));
    expect(sent(api, "DELETE", "/church")).toHaveLength(1);
  });

  it("shows the error state with Retry when the members cannot be read", async () => {
    const { api, user } = renderPage("owner", { "GET /members": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete church…" })).toBeNull();
    api.set("GET /members", memberList("owner"));
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: "Delete church…" })).toBeInTheDocument();
  });
});

describe("Settings → Danger zone: the copy and the phone screen (slice 6b-2b)", () => {
  it("lets a long church name wrap at 375 px in the cards, the dialogs and the typed-name label", async () => {
    const long = "TheVeryLongChurchNameThatNeverEndsWithoutASingleSpaceAnywhereInItsWholeLengthAtAll";
    const { user } = renderPage("owner", {}, long);
    expect((await screen.findByRole("heading", { level: 3, name: `Leave ${long}` }))).toHaveClass(WRAP);
    expect(screen.getByRole("heading", { level: 3, name: `Delete ${long}` })).toHaveClass(WRAP);
    expect(screen.getByText(deleteText(long))).toHaveClass(WRAP);
    expect(screen.getByText(OWNER_MUST_TRANSFER)).toHaveClass(WRAP);
    expect(screen.getByRole("combobox", { name: "New owner" })).toHaveClass("w-full", "min-w-0", "overflow-hidden");
    await user.click(screen.getByRole("button", { name: "Delete church…" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByRole("heading", { name: `Delete ${long}?` })).toHaveClass(WRAP);
    expect(within(dialog).getByText(deleteBody(long, 4))).toHaveClass(WRAP);
    expect(within(dialog).getByText(`Type ${long} to confirm`)).toHaveClass(WRAP);
  });

  it("lets a long church name wrap in the Leave dialog too", async () => {
    const long = "AnotherVeryLongChurchNameWithoutSpacesSoItMustBreakAnywhereToFitOnAPhone";
    const { user } = renderPage("member", {}, long);
    await user.click(await screen.findByRole("button", { name: "Leave church…" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByRole("heading", { name: `Leave ${long}?` })).toHaveClass(WRAP);
    expect(screen.getByText(leaveText(long))).toHaveClass(WRAP);
  });

  it("has no em dash in anything it says, for any role or dialog", async () => {
    const seen: string[] = [];
    const member = renderPage("member");
    await member.user.click(await screen.findByRole("button", { name: "Leave church…" }));
    await screen.findByRole("alertdialog");
    seen.push(allText());
    member.unmount();

    const owner = renderPage("owner");
    await owner.user.click(await screen.findByRole("combobox", { name: "New owner" }));
    await owner.user.click(await screen.findByRole("option", { name: "Ann Admin (ann@example.com)" }));
    await owner.user.click(screen.getByRole("button", { name: "Transfer ownership…" }));
    await screen.findByRole("alertdialog");
    seen.push(allText());
    owner.unmount();

    const deleting = renderPage("owner", { "GET /members": alone() });
    await deleting.user.click(await screen.findByRole("button", { name: "Delete church…" }));
    await screen.findByRole("alertdialog");
    seen.push(allText());

    const copy = [
      OWNER_ONLY_NOTE, OWNER_MUST_TRANSFER, TRANSFER_TEXT, INVITE_FIRST, TRANSFERRED, CHURCH_DELETED, EXIT_ME_FAILED,
      leaveText("Grace"), ownerAloneText("Grace"), deleteText("Grace"), deleteBody("Grace", 1), deleteBody("Grace", 3),
      leftChurch("Grace"),
    ];
    for (const text of [...seen, ...copy]) expect(text).not.toContain("\u2014");
    expect(seen.join(" ")).toContain("Leave Grace?");
    expect(seen.join(" ")).toContain("Make Ann Admin the owner?");
    expect(seen.join(" ")).toContain("Delete Grace?");
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/app/confirm-dialog.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx vitest run src/components/settings/danger/danger-zone-page.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`
**Expected:**
```
   × ConfirmDialog > keeps the confirm button off while confirmDisabled holds (slice 6b-2b)
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |dom| src/components/app/confirm-dialog.test.tsx > ConfirmDialog > keeps the confirm button off while confirmDisabled holds (slice 6b-2b)
      Tests  1 failed | 6 passed (7)
```
```
 FAIL  |dom| src/components/settings/danger/danger-zone-page.test.tsx [ src/components/settings/danger/danger-zone-page.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: The types, the hooks, `confirmDisabled`, the cards, the page and the route**

**Append to `frontend/src/lib/api/types.ts`:**

````ts

/**
 * Settings → Danger zone (slice 6b-2b; the routes are slice 6b-1's): `POST
 * /church/transfer-ownership`'s body (another member of the church; the
 * answer is the member list afterwards), `POST /church/leave`'s answer, and
 * `DELETE /church`'s body (the church's name, typed; the answer is
 * `DeletedOut`).
 */
export type TransferOwnershipBody = components["schemas"]["TransferOwnershipIn"];
export type ChurchLeft = components["schemas"]["LeftOut"];
export type DeleteChurchBody = components["schemas"]["DeleteChurchIn"];
````

**In `frontend/src/lib/queries/people.ts`, replace:**

````ts
function onRoleRefused(queryClient: QueryClient, churchId: string, e: ApiError): void {
````

**with:**

````ts
export function onRoleRefused(queryClient: QueryClient, churchId: string, e: ApiError): void {
````

**In `frontend/src/lib/queries/people.ts`, replace:**

````ts
 * `refetchKey`, the list the missing row came from).
 */
function onWriteError(queryClient: QueryClient, churchId: string, refetchKey: readonly unknown[],
````

**with:**

````ts
 * `refetchKey`, the list the missing row came from). Slice 6b-2b's transfer
 * and delete use it too.
 */
export function onWriteError(queryClient: QueryClient, churchId: string, refetchKey: readonly unknown[],
````

**In `frontend/src/lib/queries/church.ts`, replace:**

````ts
import type { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { ChurchPatch, ChurchProfile } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";
````

**with:**

````ts
import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { ChurchLeft, ChurchPatch, ChurchProfile, DeletedOut, MemberList } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { useExitChurch } from "@/lib/church-exit";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";
import { onWriteError } from "./people";
````

**In `frontend/src/lib/queries/church.ts`, replace:**

````ts
    },
  });
}
````

**with:**

````ts
    },
  });
}

// --- Slice 6b-2b: transfer ownership, leave, delete (the routes are slice 6b-1's) ---------------------------

export const TRANSFERRED = "Ownership transferred. You are now an admin.";

/** "You left {church}." */
export function leftChurch(name: string): string {
  return `You left ${name}.`;
}

export const CHURCH_DELETED = "Church deleted.";

/**
 * `POST /church/transfer-ownership` (the owner): the answer, the member list
 * afterwards, goes in the cache; the members, the profile (which carries the
 * role, so the Danger zone turns to its admin form) and `/me` (the switcher's
 * role) refetch; "Ownership transferred. You are now an admin.". A role
 * refusal (ownership moved elsewhere) is toasted and refetches the role and
 * the members; a 404 (that person left meanwhile) is toasted and refetches
 * the members; a 401 or a lost church is the app's.
 */
export function useTransferOwnership() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.members(church.id);
  return useChurchMutation<MemberList, ApiError, string>({
    mutationFn: (userId) =>
      api.church<MemberList>("/church/transfer-ownership", { method: "POST", json: { user_id: userId } }),
    onSuccess: async (list) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData(key, list);
      void queryClient.invalidateQueries({ queryKey: key });
      void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
      void queryClient.invalidateQueries({ queryKey: keys.me() });
      toast.success(TRANSFERRED);
    },
    onError: onWriteError(queryClient, church.id, key),
  });
}

/**
 * `POST /church/leave` (an admin or a member): "You left {church}.", then
 * `useExitChurch` (another church or `/welcome`, the draft gone, no "no
 * longer have access" toast). The mutation stays pending until the exit is
 * done, so the dialog keeps "Leaving…" until the page goes. A refusal (409:
 * the owner must transfer first, or the last admin of a church with no owner)
 * is toasted with the server's words; a 401 or a lost church is the app's.
 */
export function useLeaveChurch() {
  const api = useApi();
  const church = useChurch();
  const exit = useExitChurch();
  return useChurchMutation<ChurchLeft, ApiError, void>({
    mutationFn: () => api.church<ChurchLeft>("/church/leave", { method: "POST" }),
    onSuccess: async () => {
      toast.success(leftChurch(church.name));
      await exit(church.id);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      toast.error(errorToastMessage(e));
    },
  });
}

/** A 422 naming `confirm_name` ("Church name did not match."): the Delete dialog shows it under the name. */
export function deleteNameError(e: unknown): string | null {
  return e instanceof ApiError && e.status === 422 && e.fields?.confirm_name ? e.fields.confirm_name : null;
}

/**
 * `DELETE /church` with `{confirm_name}` (the owner; sent as typed, the
 * server trims): "Church deleted.", then the same exit as Leave. A name
 * mismatch is the dialog's (`deleteNameError`); a role refusal (ownership
 * moved elsewhere) is toasted and refetches the role and the members; a 401
 * or a lost church is the app's; anything else is toasted.
 */
export function useDeleteChurch() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const exit = useExitChurch();
  return useChurchMutation<DeletedOut, ApiError, string>({
    mutationFn: (confirmName) =>
      api.church<DeletedOut>("/church", { method: "DELETE", json: { confirm_name: confirmName } }),
    onSuccess: async () => {
      toast.success(CHURCH_DELETED);
      await exit(church.id);
    },
    onError: onWriteError(queryClient, church.id, keys.members(church.id), (e) => deleteNameError(e) !== null),
  });
}
````

**In `frontend/src/components/app/confirm-dialog.tsx`, replace:**

````tsx
  pendingLabel?: string;
  destructive?: boolean;
````

**with:**

````tsx
  pendingLabel?: string;
  /** Keeps the confirm button off until the dialog's own condition holds (a typed name; slice 6b-2b). */
  confirmDisabled?: boolean;
  destructive?: boolean;
````

**In `frontend/src/components/app/confirm-dialog.tsx`, replace:**

````tsx
  pendingLabel,
  destructive = false,
````

**with:**

````tsx
  pendingLabel,
  confirmDisabled = false,
  destructive = false,
````

**In `frontend/src/components/app/confirm-dialog.tsx`, replace:**

````tsx
            {...(pendingLabel === undefined ? {} : { pendingLabel })}
            size="touch"
````

**with:**

````tsx
            {...(pendingLabel === undefined ? {} : { pendingLabel })}
            disabled={confirmDisabled}
            size="touch"
````

**Create `frontend/src/components/settings/danger/leave-church-card.tsx`:**

````tsx
"use client";

import { useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { Button } from "@/components/ui/button";
import { useLeaveChurch } from "@/lib/queries/church";
import type { leaveBlock } from "@/lib/settings/people";

/** A Danger zone card: a bordered box; a destructive one is outlined in red (6b spec UX 2). */
export const CARD = "grid gap-3 rounded-lg border p-4";
export const DESTRUCTIVE_CARD = `${CARD} border-destructive/40`;

export const OWNER_MUST_TRANSFER = "You're the owner. Transfer ownership below before you leave.";

export function leaveText(church: string): string {
  return `You'll lose access to ${church}'s services, hymns and settings. To come back you'll need a new invite.`;
}

export function ownerAloneText(church: string): string {
  return `You're the only person in ${church}. To stop using it, delete the church below.`;
}

/**
 * Leave {church} (6b spec UX 2a), for everyone. A member or an admin leaves
 * after a confirmation; the owner's button is off, with why: transfer first
 * or, alone, delete the church.
 */
export function LeaveChurchCard({
  churchName,
  block,
}: {
  churchName: string;
  block: ReturnType<typeof leaveBlock>;
}) {
  const leave = useLeaveChurch();
  const [open, setOpen] = useState(false);
  // One leave per confirmation, even if the button is tapped twice before it says "Leaving…".
  const sent = useRef(false);
  let text: string;
  if (block === "owner_with_others") text = OWNER_MUST_TRANSFER;
  else if (block === "owner_alone") text = ownerAloneText(churchName);
  else text = leaveText(churchName);
  return (
    <section aria-labelledby="leave-title" className={DESTRUCTIVE_CARD}>
      <h3 id="leave-title" className="text-base font-medium [overflow-wrap:anywhere]">
        Leave {churchName}
      </h3>
      <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{text}</p>
      <div>
        <Button
          type="button"
          variant="outline"
          size="touch"
          className="md:h-8"
          disabled={block !== null}
          onClick={() => {
            sent.current = false;
            setOpen(true);
          }}
        >
          Leave church…
        </Button>
      </div>
      <ConfirmDialog
        open={open}
        onOpenChange={(next) => {
          // while the leave runs the confirmation stays open
          if (!next && leave.isPending) return;
          setOpen(next);
        }}
        title={`Leave ${churchName}?`}
        description={`You'll lose access right away. Your unsaved draft for ${churchName} on this device will be discarded.`}
        confirmLabel="Leave church"
        pending={leave.isPending}
        pendingLabel="Leaving…"
        destructive
        wrapAnywhere
        onConfirm={() => {
          if (sent.current) return;
          sent.current = true;
          leave.mutate(undefined, {
            onError: () => {
              sent.current = false;
              setOpen(false);
            },
          });
        }}
      />
    </section>
  );
}
````

**Create `frontend/src/components/settings/danger/transfer-ownership-card.tsx`:**

````tsx
"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Member } from "@/lib/api/types";
import { useTransferOwnership } from "@/lib/queries/church";
import { displayName, transferCandidates, transferChoiceLabel } from "@/lib/settings/people";

import { CARD } from "./leave-church-card";

export const TRANSFER_TEXT = "The new owner can transfer ownership and delete the church. You'll become an admin.";
export const INVITE_FIRST = "Invite another member first to transfer ownership.";

/**
 * Transfer ownership (6b spec UX 2b), for the owner: choose anyone else in
 * the church (admins first), confirm, and they become the owner while you
 * become an admin; the page then turns to its admin form. Alone, the card
 * says to invite someone first, with a link to People.
 */
export function TransferOwnershipCard({
  churchName,
  members,
  onTransferred,
}: {
  churchName: string;
  members: readonly Member[];
  /** Where focus goes once the transfer is done (the card is about to go). */
  onTransferred(): HTMLElement | null;
}) {
  const transfer = useTransferOwnership();
  const candidates = transferCandidates(members);
  const [chosen, setChosen] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<Member | null>(null);
  // The confirmation keeps its person while it closes (confirming is null by then).
  const [shown, setShown] = useState<Member | null>(null);
  const sent = useRef(false);
  const done = useRef(false);
  // Someone chosen who has left meanwhile is no longer chosen.
  const target = candidates.find((m) => m.user_id === chosen) ?? null;
  const items = Object.fromEntries(candidates.map((m) => [m.user_id, transferChoiceLabel(m)]));
  const name = shown ? displayName(shown) : "";

  return (
    <section aria-labelledby="transfer-title" className={CARD}>
      <h3 id="transfer-title" className="text-base font-medium">
        Transfer ownership
      </h3>
      {candidates.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          {INVITE_FIRST}{" "}
          <Link href="/settings/people" className="inline-flex min-h-11 items-center font-medium text-foreground underline underline-offset-4 md:min-h-0">
            Invite someone
          </Link>
        </p>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">{TRANSFER_TEXT}</p>
          <div className="grid gap-2">
            <Label htmlFor="transfer-new-owner">New owner</Label>
            <Select
              value={target?.user_id ?? null}
              items={items}
              onValueChange={(value) => {
                if (typeof value === "string") setChosen(value);
              }}
            >
              <SelectTrigger
                id="transfer-new-owner"
                className="h-11 w-full min-w-0 overflow-hidden data-[size=default]:h-11 md:h-9 md:data-[size=default]:h-9"
              >
                <SelectValue placeholder="Choose a person" />
              </SelectTrigger>
              <SelectContent>
                {candidates.map((m) => (
                  <SelectItem key={m.user_id} value={m.user_id} className="[overflow-wrap:anywhere]">
                    {items[m.user_id]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Button
              type="button"
              size="touch"
              className="md:h-8"
              disabled={target === null}
              onClick={() => {
                sent.current = false;
                done.current = false;
                setShown(target);
                setConfirming(target);
              }}
            >
              Transfer ownership…
            </Button>
          </div>
          <ConfirmDialog
            open={confirming !== null}
            onOpenChange={(next) => {
              // while the transfer runs the confirmation stays open
              if (!next && !transfer.isPending) setConfirming(null);
            }}
            title={`Make ${name} the owner?`}
            description={`${name} will become the owner of ${churchName} and you'll become an admin. Only the new owner can transfer ownership back.`}
            confirmLabel="Transfer ownership"
            pending={transfer.isPending}
            pendingLabel="Transferring…"
            wrapAnywhere
            finalFocus={() => (done.current ? onTransferred() : true)}
            onConfirm={() => {
              if (confirming === null || sent.current) return;
              sent.current = true;
              transfer.mutate(confirming.user_id, {
                onSuccess: () => {
                  done.current = true;
                  setChosen(null);
                },
                onSettled: () => {
                  sent.current = false;
                  setConfirming(null);
                },
              });
            }}
          />
        </>
      )}
    </section>
  );
}
````

**Create `frontend/src/components/settings/danger/delete-church-card.tsx`:**

````tsx
"use client";

import { useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { deleteNameError, useDeleteChurch } from "@/lib/queries/church";
import { deleteNameMatches } from "@/lib/settings/people";

import { DESTRUCTIVE_CARD } from "./leave-church-card";

export function deleteText(church: string): string {
  return `Deleting ${church} removes it for everyone. Pending invite links stop working.`;
}

/** The Delete dialog's body (6b spec UX 2c; its first two sentences in the singular when the owner is alone). */
export function deleteBody(church: string, people: number): string {
  const who =
    people === 1
      ? `This removes ${church}. You're the only person in it, and you'll lose access to its services, hymns, contacts and settings.`
      : `This removes ${church} for all ${people} people in it. They'll lose access to its services, hymns, contacts and settings.`;
  return `${who} Your unsaved draft for ${church} on this device will be discarded. This can't be undone.`;
}

/**
 * Delete {church} (6b spec UX 2c), for the owner: a confirmation that also
 * needs the church's name typed exactly (capitals included; spaces around it
 * do not count), then the same exit as Leave. The server checks the name too:
 * its "Church name did not match." shows under the box.
 */
export function DeleteChurchCard({ churchName, memberCount }: { churchName: string; memberCount: number }) {
  const remove = useDeleteChurch();
  const [open, setOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const sent = useRef(false);
  const matches = deleteNameMatches(typed, churchName);
  return (
    <section aria-labelledby="delete-title" className={DESTRUCTIVE_CARD}>
      <h3 id="delete-title" className="text-base font-medium [overflow-wrap:anywhere]">
        Delete {churchName}
      </h3>
      <p className="text-sm text-muted-foreground [overflow-wrap:anywhere]">{deleteText(churchName)}</p>
      <div>
        <Button
          type="button"
          variant="destructive"
          size="touch"
          className="md:h-8"
          onClick={() => {
            sent.current = false;
            setTyped("");
            setError(null);
            setOpen(true);
          }}
        >
          Delete church…
        </Button>
      </div>
      <ConfirmDialog
        open={open}
        onOpenChange={(next) => {
          // while the delete runs the confirmation stays open
          if (!next && remove.isPending) return;
          setOpen(next);
        }}
        title={`Delete ${churchName}?`}
        description={deleteBody(churchName, memberCount)}
        confirmLabel="Delete church"
        pending={remove.isPending}
        pendingLabel="Deleting…"
        confirmDisabled={!matches}
        destructive
        wrapAnywhere
        onConfirm={() => {
          if (!matches || sent.current) return;
          sent.current = true;
          setError(null);
          remove.mutate(typed, {
            onError: (e) => {
              sent.current = false;
              const message = deleteNameError(e);
              if (message === null) {
                setOpen(false);
                return;
              }
              setError(message);
              input.current?.focus();
            },
          });
        }}
      >
        <div className="grid gap-2">
          <Label htmlFor="delete-confirm-name" className="block leading-snug [overflow-wrap:anywhere]">
            Type {churchName} to confirm
          </Label>
          <Input
            id="delete-confirm-name"
            ref={input}
            value={typed}
            onChange={(e) => {
              setTyped(e.target.value);
              setError(null);
            }}
            autoComplete="off"
            autoCapitalize="off"
            autoCorrect="off"
            spellCheck={false}
            className="h-11 md:h-9"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? "delete-confirm-name-error" : undefined}
          />
          {error ? (
            <p id="delete-confirm-name-error" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
        </div>
      </ConfirmDialog>
    </section>
  );
}
````

**Create `frontend/src/components/settings/danger/danger-zone-page.tsx`:**

````tsx
"use client";

import { useRef } from "react";

import { ErrorState } from "@/components/app/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { useMembers } from "@/lib/queries/people";
import { leaveBlock } from "@/lib/settings/people";

import { DeleteChurchCard } from "./delete-church-card";
import { LeaveChurchCard } from "./leave-church-card";
import { TransferOwnershipCard } from "./transfer-ownership-card";

export const OWNER_ONLY_NOTE = "Only the owner can transfer ownership or delete the church.";

/**
 * `/settings/danger` (slice 6b-2b; 6b spec UX §2). Admins and members see
 * that only the owner can transfer or delete, and Leave church. The owner
 * sees Leave church (off, with why), Transfer ownership and Delete church,
 * once the member list (who can become the owner; how many people a delete
 * removes) has loaded.
 */
export function DangerZonePage() {
  const church = useChurch();
  const heading = useRef<HTMLHeadingElement>(null);
  return (
    <section aria-labelledby="danger-title" className="grid gap-6">
      <h2 id="danger-title" ref={heading} tabIndex={-1} className="text-lg font-semibold outline-none">
        Danger zone
      </h2>
      {church.role === "owner" ? (
        <OwnerCards churchName={church.name} focusAfterTransfer={() => heading.current} />
      ) : (
        <>
          <p role="note" className="rounded-lg border bg-muted/50 px-3 py-2 text-sm">
            {OWNER_ONLY_NOTE}
          </p>
          <LeaveChurchCard churchName={church.name} block={null} />
        </>
      )}
    </section>
  );
}

function OwnerCards({ churchName, focusAfterTransfer }: { churchName: string; focusAfterTransfer(): HTMLElement | null }) {
  const members = useMembers();
  if (members.data) {
    const people = members.data.items;
    return (
      <>
        <LeaveChurchCard churchName={churchName} block={leaveBlock("owner", people.length)} />
        <TransferOwnershipCard churchName={churchName} members={people} onTransferred={focusAfterTransfer} />
        <DeleteChurchCard churchName={churchName} memberCount={people.length} />
      </>
    );
  }
  if (members.isError) {
    return <ErrorState error={members.error} onRetry={() => void members.refetch()} retrying={members.isFetching} />;
  }
  return (
    <div role="status" aria-label="Loading" className="grid gap-4">
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-36 w-full" />
      <Skeleton className="h-28 w-full" />
    </div>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/danger/page.tsx`:**

````tsx
"use client";

import { DangerZonePage } from "@/components/settings/danger/danger-zone-page";

/** Settings → Danger zone: leave the church; the owner also transfers ownership or deletes it (slice 6b-2b). */
export default function DangerZoneRoute() {
  return <DangerZonePage />;
}
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/components/app/confirm-dialog.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx vitest run src/components/settings/danger/danger-zone-page.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  7 passed (7)
```
```
      Tests  18 passed (18)
```
```
typecheck 0
lint 0
```
```
 Test Files  115 passed (115)
      Tests  1040 passed (1040)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/lib/queries/people.ts frontend/src/lib/queries/church.ts frontend/src/components/app/confirm-dialog.tsx frontend/src/components/app/confirm-dialog.test.tsx frontend/src/components/settings/danger/danger-zone-page.tsx frontend/src/components/settings/danger/leave-church-card.tsx frontend/src/components/settings/danger/transfer-ownership-card.tsx frontend/src/components/settings/danger/delete-church-card.tsx frontend/src/components/settings/danger/danger-zone-page.test.tsx "frontend/src/app/(signed-in)/(church)/settings/danger/page.tsx"
git commit -q -m "Slice 6b-2b: Settings > Danger zone (leave, transfer ownership, delete)" -m "/settings/danger: everyone may leave after a confirmation (then the quiet
exit); admins and members read that only the owner transfers or deletes.
The owner's Leave is off with why; Transfer ownership offers everyone else,
admins first, confirms, and the page turns to its admin form; Delete church
needs the exact name typed, confirms, then the same exit. The transfer,
leave and delete hooks in lib/queries/church.ts (a role refusal toasted and
refetched as on People); ConfirmDialog gains confirmDisabled." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2236 passed, 49 skipped` (unchanged); frontend `1040 passed` in 115 files.

### Task 4: Danger zone in the Settings nav (answer 5; 2026-10-09 answer 7; S "Settings nav"; acceptance 22's Danger zone half)

**Files:**
- Modify: `frontend/src/components/settings/settings-layout.test.tsx`, `frontend/src/components/settings/sections.ts`

- [ ] **Step 1: Update the tests**

The nav lists ten sections, Danger zone last (the final order), marks **Danger zone** current on its page, and a member sees ten links.

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
      ["Account", "/settings/account"],
    ]);
````

**with:**

````tsx
      ["Account", "/settings/account"],
      ["Danger zone", "/settings/danger"],
    ]);
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
  ])("marks the section current on its page (slices 6a-2, 6a-3a, 6a-3b, 5b-1, 5b-2, 6b-2a): %s", (path, label) => {
````

**with:**

````tsx
    ["/settings/danger", "Danger zone"],
  ])("marks the section current on its page (slices 6a-2, 6a-3a, 6a-3b, 5b-1, 5b-2, 6b-2a, 6b-2b): %s", (path, label) => {
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(9);
````

**with:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(10);
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')`
**Expected:**
```
   × the Settings area (slice 6a-1) > shows the heading, who you are in the church, and the sections with the current one marked
   × the Settings area (slice 6a-1) > marks the section current on its page (slices 6a-2, 6a-3a, 6a-3b, 5b-1, 5b-2, 6b-2a, 6b-2b): /settings/danger
   × the Settings area (slice 6a-1) > shows a member the same sections, and /settings opens Church
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 3 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |dom| src/components/settings/settings-layout.test.tsx > the Settings area (slice 6a-1) > shows the heading, who you are in the church, and the sections with the current one marked
 FAIL  |dom| src/components/settings/settings-layout.test.tsx > the Settings area (slice 6a-1) > marks the section current on its page (slices 6a-2, 6a-3a, 6a-3b, 5b-1, 5b-2, 6b-2a, 6b-2b): /settings/danger
 FAIL  |dom| src/components/settings/settings-layout.test.tsx > the Settings area (slice 6a-1) > shows a member the same sections, and /settings opens Church
      Tests  3 failed | 9 passed (12)
```

- [ ] **Step 3: Put Danger zone last**

**In `frontend/src/components/settings/sections.ts`, replace:**

````ts
 * Contacts, People, Account, then 6b-2b's Danger zone).
````

**with:**

````ts
 * Contacts, People, Account, then 6b-2b's Danger zone); 6b-2b adds Danger
 * zone last, so the nav is in its final order.
````

**In `frontend/src/components/settings/sections.ts`, replace:**

````ts
  { href: "/settings/account", label: "Account" },
] as const;
````

**with:**

````ts
  { href: "/settings/account", label: "Account" },
  { href: "/settings/danger", label: "Danger zone" },
] as const;
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests " | sed -E 's/ [0-9]+ms$//')` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  12 passed (12)
```
```
typecheck 0
lint 0
```
```
 Test Files  115 passed (115)
      Tests  1041 passed (1041)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/settings-layout.test.tsx frontend/src/components/settings/sections.ts
git commit -q -m "Slice 6b-2b: Danger zone in the Settings nav" -m "SETTINGS_SECTIONS gains Danger zone (/settings/danger) last: Church, Hymns,
Liturgy, Prayers, Rubric, Bulletin, Contacts, People, Account, Danger zone,
the final order of the owner's 6b answers." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2236 passed, 49 skipped` (unchanged); frontend `1041 passed` in 115 files.

## Docs, verification, the PR and the merge (T5-T8)

### Task 5: Docs: the manual check items (answers 4 (3) and 5)

**Files:**
- Modify: `docs/manual-verification.md`

"## Slice 6b" gains the 6b-2b items 18-25: the page in the real church (read only, with the Delete dialog opened and cancelled), a throwaway church "Delete me" joined by the second account, that account's member view (Leave opened and cancelled), the transfer to it, the owner's own leave, its delete as the new owner alone, the phone screen, and the agent's check. No new `##` heading, so `test_slice1_docs.py`'s pin is unchanged.

- [ ] **Step 1: The items**

**Append to `docs/manual-verification.md`:**

````markdown

**6b-2b** (owner's 6b-2 planning answers of 2026-10-10) brings Settings →
**Danger zone** (`/settings/danger`: Leave church for everyone; Transfer
ownership and Delete church for the owner; the Danger zone entry last in
the Settings nav). No migration. The checks that change anything run in a
**throwaway church made from the church menu for this check** (for example
"Delete me"), with the owner's **second Google account** in a private
window; the real church and the test churches are only read, and are
kept. The results go into `docs/ops-runbook.md` → "Slice 6b-2b record":
what the screens show, never an email address, an invite link, a church id
or a database URL.

- [ ] (owner, after 6b-2b) **18.** On the phone, in the real church: **Settings** lists Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, People, Account, **Danger zone**. **Danger zone** shows **Leave {church}** with its button off and "You're the owner. Transfer ownership below before you leave.", **Transfer ownership** with **New owner**, and **Delete {church}**. **Delete church…** asks "Delete {church}?"; with the name typed in small letters **Delete church** stays off; **Cancel**. Nothing is changed here.
- [ ] (owner, after 6b-2b) **19.** From the church menu, create a church named **Delete me**. In it, **Settings → People → Create invite link** (Member), and join with the second Google account in a private window, as in item 12.
- [ ] (owner, after 6b-2b) **20.** In the private window (the second account, a member of Delete me): **Danger zone** says "Only the owner can transfer ownership or delete the church." and shows **Leave Delete me** only. **Leave church…** asks "Leave Delete me?"; **Cancel**.
- [ ] (owner, after 6b-2b) **21.** In your own window, Delete me's **Danger zone → New owner**: the second account is listed; choose it, **Transfer ownership…** asks "Make {name} the owner?"; **Transfer ownership**: "Ownership transferred. You are now an admin.", and the page turns to the short form (the note and Leave only; the Settings heading says "You're an admin of Delete me.").
- [ ] (owner, after 6b-2b) **22.** Still in your own window: **Leave church…** → **Leave church**: "You left Delete me.", and the app opens another of your churches with **no** "You no longer have access" message; Delete me is gone from the church menu.
- [ ] (owner, after 6b-2b) **23.** In the private window (the second account, now Delete me's owner and only person; pull to reload): **Danger zone** shows Leave off with "You're the only person in Delete me. To stop using it, delete the church below.", and Transfer ownership says "Invite another member first to transfer ownership." with **Invite someone**. **Delete church…**: with "delete me" typed, **Delete church** stays off; with "Delete me", it turns on; tap it: "Church deleted.", then the welcome page (that account has no other church), with no "no longer have access" message.
- [ ] (owner, after 6b-2b) **24.** At 375 px (the phone): no sideways scroll on Danger zone; the dialogs and the New owner list fit the screen; the keyboard does not cover the name box while typing; every button is easy to tap.
- [ ] (agent, after 6b-2b) **25.** `/health/ready` answers `{"ok":true,"db":"ok"}`; the app's `/settings/danger` is served (signed out, it sends you to sign in).
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
git commit -q -m "Docs: slice 6b-2b's manual check items" -m "docs/manual-verification.md \"Slice 6b\" gains the 6b-2b items: Danger zone
in the real church (read only), then in a throwaway church made for the
check with the second Google account: its member view, the transfer to it,
the owner's own leave, and its delete as the new owner alone; the phone
screen; and the agent's check." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `2236 passed, 49 skipped` (unchanged); frontend `1041 passed` in 115 files.

### Task 6: Verification (agent)

Every `gh` command uses `-R <repo>` (or the session's GitHub tools, with the same effect). Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 4).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

Run: `git status --short | grep -v '^?? .claude/' | wc -l` then `git fetch -q origin && git rev-list --count HEAD..origin/main` then `ls backend/migrations/versions | grep -c '^0'`
**Expected:** `0` (nothing uncommitted); `0`; `9` (no new revision). If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 6)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner. If `main` gained a migration, nothing here depends on it, but say so in the PR.
```
0
```
```
0
```
```
9
```

- [ ] **Step 2 (agent): Both suites, types, lint, the build**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -1` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -cE "Compiled successfully|/settings/danger")`
**Expected** (a font `Failed to fetch` in the build: say so and rely on CI): the backend unchanged; the frontend as in the counts table; `2` (compiled, and the `/settings/danger` route listed):
```
2236 passed, 49 skipped in <t>s
```
```
 Test Files  115 passed (115)
      Tests  1041 passed (1041)
```
```
typecheck 0
lint 0
```
```
2
```

- [ ] **Step 3 (agent): The API files unchanged, the gates, the paths, the commits**

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null 2>&1) && git status --short -- frontend backend | wc -l` then `git diff origin/main...HEAD -- frontend/src docs/manual-verification.md | grep '^+' | grep -c '—'` then `python3 -c "import pathlib; t=pathlib.Path('docs/superpowers/plans/2026-10-10-slice-6b2b-danger-zone.md').read_text(); print(sum(t.count(c) for c in ('\u2028','\u2029','\ufffe','\uffff')))"` then `git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2` then `git diff --name-only origin/main...HEAD -- backend .github frontend/package.json frontend/package-lock.json requirements-dev.txt requirements.txt pytest.ini app.py streamlit_views streamlit_tests streamlit_auth.py streamlit_tenancy.py ui_helpers.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts frontend/src/lib/queries/client.ts frontend/src/components/ui | wc -l` then `git log --reverse --no-merges --format=%s origin/main..HEAD | grep -v -e '^WIP plan: ' -e '^Plan: '` then `for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"`
**Expected:** `0` (no API change); `0` (no em dash in an added line of code, tests or the checklist); `0` (no U+2028, U+2029, U+FFFE or U+FFFF in this plan); exactly these paths (the 6b-2a record rides along until merged); `0` (nothing that must stay untouched changed); the subjects oldest first, then any `Fix: …` lines; only `trailer check done`:
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
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-10-slice-6b2b-danger-zone.md
M	frontend/src/app/(signed-in)/(church)/church-layout.test.tsx
M	frontend/src/app/(signed-in)/(church)/layout.tsx
A	frontend/src/app/(signed-in)/(church)/settings/danger/page.tsx
M	frontend/src/components/app/confirm-dialog.test.tsx
M	frontend/src/components/app/confirm-dialog.tsx
A	frontend/src/components/settings/danger/danger-zone-page.test.tsx
A	frontend/src/components/settings/danger/danger-zone-page.tsx
A	frontend/src/components/settings/danger/delete-church-card.tsx
A	frontend/src/components/settings/danger/leave-church-card.tsx
A	frontend/src/components/settings/danger/transfer-ownership-card.tsx
M	frontend/src/components/settings/sections.ts
M	frontend/src/components/settings/settings-layout.test.tsx
M	frontend/src/lib/api/types.ts
A	frontend/src/lib/church-exit.test.ts
A	frontend/src/lib/church-exit.ts
M	frontend/src/lib/church.test.ts
M	frontend/src/lib/church.ts
M	frontend/src/lib/queries/church.ts
M	frontend/src/lib/queries/membership.test.tsx
M	frontend/src/lib/queries/membership.ts
M	frontend/src/lib/queries/people.ts
M	frontend/src/lib/settings/people.test.ts
M	frontend/src/lib/settings/people.ts
M	frontend/src/test/setup-dom.ts
```
```
0
```
```
Docs: slice 6b-2a record in the ops runbook
Slice 6b-2b: the exit mark and the Danger zone rules
Slice 6b-2b: the quiet exit after a leave or delete
Slice 6b-2b: Settings > Danger zone (leave, transfer ownership, delete)
Slice 6b-2b: Danger zone in the Settings nav
Docs: slice 6b-2b's manual check items
```
```
trailer check done
```

- [ ] **Step 4: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `church.test.ts`, `people.test.ts`, `setup-dom.ts` | T1 |
| `church-exit.test.ts`, `membership.test.tsx`, `church-layout.test.tsx` | T2 |
| `confirm-dialog.test.tsx` (or an existing `ConfirmDialog` caller's test), `danger-zone-page.test.tsx`, any People page test (the exported helpers) | T3 |
| `settings-layout.test.tsx` | T4 |
| `test_slice1_docs.py`, `test_docs.py` | T5 |
| anything else, any backend test | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, slice 6b-2b final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `2236 passed, 49 skipped` (unchanged); frontend `1041 passed` in 115 files.

### Task 7: Before the PR: no migration, so no owner routine (agent; answer 7)

**Files:** none.

6b-2b changes no table, column, index or row shape, adds no migration (T6 Step 1 counts 9 revision files, as on `main`) and touches nothing under `backend/` (T6 Step 3). Railway's pre-deploy `alembic upgrade head` finds nothing to do. So there is **no backup, no count query and no SQL to read before this merge**, and nothing of the kind is sent to the owner.

Delete church calls 6b-1's `DELETE /church`, shipped and live since PR #59: a soft delete (it sets `deleted_at` and revokes the church's invites; every row stays), behind `require_owner`, the church-row lock and the server's own name check. The new page adds no new way to change data, only a button for that route. The daily `db-backup` run (08:37 UTC, `.github/workflows/backup.yml`) stands as the safety net, so no extra backup is recommended. If the owner wants one anyway before the phone check deletes "Delete me", it is the same one-line `gh workflow run db-backup --ref main -R <repo>` as before, on the owner's yes only.

- [ ] **Step 1 (agent): Confirm nothing touches the database**

Run: `git diff --name-only origin/main...HEAD -- backend | wc -l` then `ls backend/migrations/versions | grep -c '^0'`
**Expected:** `0` and `9`. Anything else: stop and tell the owner before the PR, since the plan then needs the owner routine of the 6b-1 and 6b-2a plans (without SQL in chat; see "Lessons carried").
```
0
```
```
9
```

### Task 8: The draft PR, the merge, the after-deploy check, the phone check, the record (OWNER + agent)

**Files:** Modify (Step 13, the records PR): `docs/ops-runbook.md`: insert `### Slice 6b-2b record` right before `## Backups` (after the last record above it, today `### Slice 6b-2a record`, whose table's last row starts `| Follow-ups |`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to open the draft PR**

(not replayed) `gh pr list -R <repo> --head claude/slice-2-plan-4q33le --state open --json number,url` → `[]`. Send the owner exactly this, and wait for a clear yes:

> The Danger zone page (slice 6b-2b) is verified on this machine: backend 2236 passed, 49 skipped (unchanged); frontend 1041 tests in 115 files (1010 in 113 before), typecheck, lint and the production build clean. It adds Settings → Danger zone: anyone but the owner can leave a church (it then opens another of their churches, without the "no longer have access" message, and drops that church's unsaved draft on this device); the owner can transfer ownership to someone else in the church, or delete the church after typing its exact name. There is no database change this time, so no backup or SQL check before it. May I open the pull request as a **draft** titled "Slice 6b-2b: Settings > Danger zone (leave, transfer ownership, delete)", so the checks run? Merging stays with you.

- [ ] **Step 2 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/6b2b-pr-body.md" <<'BODY'
Slice 6b-2b: Settings > Danger zone (the second of slice 6b-2's two PRs; owner's 6b-2 planning answers of 2026-10-10). Spec: docs/superpowers/specs/2026-09-25-slice-6b-settings-people-design.md and its amendments of 2026-10-09 and 2026-10-10. Plan: docs/superpowers/plans/2026-10-10-slice-6b2b-danger-zone.md. No API change, no migration, no new package or variable.

- /settings/danger: admins and members read "Only the owner can transfer ownership or delete the church." and can leave after a confirmation. The owner's Leave is off with why (transfer first, or alone delete); Transfer ownership offers everyone else, admins first, confirms, then refetches the profile, /me and the members, and the page turns to its admin form ("Invite another member first…" with a link to People when alone); Delete church needs the exact name typed (both trimmed, capitals included), confirms, and shows the server's 422 under the box. One confirmation sends one request; Leaving…, Transferring…, Deleting…; a role refusal is toasted and refetched as on People; a 409 is toasted. The Danger zone nav entry last (the final Settings order).
- The quiet exit after a leave or delete: lib/church-exit.ts runChurchExit (mark the church as exited, cancel its requests, remove its draft keys, useMembershipChanged({selectChurchId: null}), remove its cache) and useExitChurch (toasts when /me did not come back; useMembershipChanged now resolves to that). The (church) layout's two lost-access toasts skip a church marked in the last 60 s (markChurchExited / wasChurchExited in lib/church.ts).
- lib/settings/people.ts: leaveBlock, deleteNameMatches, transferCandidates, transferChoiceLabel. ConfirmDialog gains confirmDisabled. docs/manual-verification.md: "Slice 6b" items 18-25. Rides along: the 6b-2a record in docs/ops-runbook.md.

Before the PR: nothing (no migration; Task 7). After the merge: the after-deploy check, the phone check on a throwaway church with a second Google account (member view, transfer, leave, delete), a "Slice 6b-2b record" in docs/ops-runbook.md.

Tests: backend 2236 → 2236 passed, 49 → 49 skipped (unchanged); frontend 1010 → 1041 in 113 → 115 files

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R <repo> --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 6b-2b: Settings > Danger zone (leave, transfer ownership, delete)" \
  --body-file "<scratch>/6b2b-pr-body.md"
gh pr checks <N> -R <repo> --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `2236 passed, 49 skipped`, backend-postgres `49 passed, 2236 deselected`, frontend `1041 passed` in 115 files. Then send: "PR #<N> is green: the backend is unchanged (2236 passed, 49 skipped); 1041 frontend tests in 115 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R <repo>`.

- [ ] **Step 3 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R <repo> --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "May I merge PR #<N> with a merge commit? There is no database change; Railway restarts the server with nothing to migrate, and Vercel publishes the Danger zone page. I will tell you when it is live, then ask for a phone check in short steps." On a clear yes (not replayed):

```bash
gh pr merge <N> --merge -R <repo>
gh pr view <N> -R <repo> --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R <repo> --workflow ci.yml --branch main --commit "$(gh pr view <N> -R <repo> --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R <repo> --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both.

- [ ] **Step 4 (agent): The deploy (manual-verification item 25)**

About three minutes after the merge (not replayed):

```bash
curl -s <api>/health/ready; echo
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' <app>/settings/danger
```

**Expected:** `{"ok":true,"db":"ok"}`; `307 <app>/login?next=%2Fsettings%2Fdanger` (signed out, the page sends you to sign in). A `404` means Vercel has not published yet: wait a minute and ask again. Nothing for the owner to run.

- [ ] **Step 5 (OWNER, then agent): Phone, step 1 of 7: the page in your church, read only (item 18)**

> On your phone, open the app and pull down to reload. Tap **Settings**: is **Danger zone** the last section, after Account? Tap it. Do you see **Leave {your church}** with its button greyed out and "You're the owner. Transfer ownership below before you leave.", then **Transfer ownership** with a **New owner** list, then **Delete {your church}**? Tap **Delete church…**, type your church's name in small letters: does **Delete church** stay greyed out? Tap **Cancel**. Please change nothing in this church.

- [ ] **Step 6 (OWNER, then agent): Phone, step 2 of 7: a throwaway church (item 19)**

> Open the church menu at the top and create a new church named **Delete me** (it is only for this check and will be deleted at the end). In Delete me, open **Settings → People** and tap **Create invite link** (Member). Copy the link, open it in a **private window**, and join with your **second Google account**. Did Delete me open there?

- [ ] **Step 7 (OWNER, then agent): Phone, step 3 of 7: the member's view (item 20)**

> In the private window (your second account, in Delete me): tap **Settings → Danger zone**. Does it say "Only the owner can transfer ownership or delete the church." with only **Leave Delete me** below? Tap **Leave church…**: does it ask "Leave Delete me?"? Tap **Cancel** (not Leave).

- [ ] **Step 8 (OWNER, then agent): Phone, step 4 of 7: the transfer (item 21)**

> In your own window, in Delete me: **Settings → Danger zone**. In **New owner**, choose your second account, then tap **Transfer ownership…**. Does it ask "Make {name} the owner?"? Tap **Transfer ownership**. Do you see "Ownership transferred. You are now an admin.", and does the page now show the note and Leave only? Does the Settings heading say "You're an admin of Delete me."?

- [ ] **Step 9 (OWNER, then agent): Phone, step 5 of 7: you leave (item 22)**

> Still in your own window: tap **Leave church…**, then **Leave church**. Do you see "You left Delete me.", and does the app open your other church **without** a message "You no longer have access…"? Is Delete me gone from the church menu?

- [ ] **Step 10 (OWNER, then agent): Phone, step 6 of 7: the new owner deletes it (item 23)**

> In the private window (your second account, now the owner and the only person in Delete me): pull down to reload, then **Settings → Danger zone**. Is Leave greyed out with "You're the only person in Delete me. To stop using it, delete the church below."? Does Transfer ownership say "Invite another member first to transfer ownership."? Tap **Delete church…** and type **delete me** in small letters: is **Delete church** greyed out? Change it to **Delete me**: is it on now? Tap it. Do you see "Church deleted." and then the welcome page, without a "no longer have access" message? You can close the private window afterwards.

- [ ] **Step 11 (OWNER, then agent): Phone, step 7 of 7: the phone screen (item 24)**

> Thinking back over these screens: was there any sideways scrolling on Danger zone? Did the dialogs and the New owner list fit the screen? Did the keyboard leave the name box visible while you typed? Were the buttons easy to tap?

- [ ] **Step 12 (agent): The results**

Write each step's result, with the date, into `<scratch>/6b2b-t8-results.md` (not committed). A step the owner could not do (no second account at hand, for example) is "Not checked" with the reason; Steps 8-10 then become: open the Transfer and Delete dialogs in Delete me as the owner, check them, **Cancel**, and delete Delete me as its only person (Step 10's checks). A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 13 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it, `### Slice 6b-2a record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Slice 6b-2b record

Slice 6b-2b (Settings → Danger zone: anyone but the owner leaves; the owner
transfers ownership or deletes the church after typing its name; a leave or
delete then opens another church quietly and drops that church's draft)
merged as PR #<N>, the second of slice 6b-2's two PRs (owner's 6b-2
planning answers of 2026-10-10). No migration, so no backup routine before
the merge. The phone check deleted a throwaway church made for it, with
the owner's second Google account; the real church and the test churches
were only read. No church id, email address, invite link, token or
database URL is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`; `/settings/danger` signed out: 307 to sign in | <date> |
| Phone 1. The page in the real church (read only) | <Danger zone last in the nav; Leave off with the transfer sentence; Transfer with New owner; Delete's button off for the name in small letters; cancelled. / …> | <date> |
| Phone 2. A throwaway church | <"Delete me" created from the church menu; the second account joined with a single-use link in a private window. / …> | <date> |
| Phone 3. The member's view | <The note and Leave only; the Leave dialog opened and cancelled. / …> | <date> |
| Phone 4. Transfer | <"Make {name} the owner?"; "Ownership transferred. You are now an admin."; the page turned to the note and Leave; the heading said admin. / …> | <date> |
| Phone 5. Leave | <"You left Delete me."; another church opened with no access message; Delete me gone from the menu. / …> | <date> |
| Phone 6. Delete | <Leave off with the only-person sentence; "Invite another member first…"; the button off for small letters, on for the exact name; "Church deleted."; the welcome page with no access message. / …> | <date> |
| Phone 7. The screen (<phone and browser>) | <No sideways scroll; dialogs and the list fit; the keyboard left the box visible; easy to tap. / …> | <date> |
| Agent checks | Item 25: Step 4's two lines | <date> |
| Follow-ups | <None. / One line per follow-up.> Slice 6b is done; next: <what the owner names> | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye. Then (not replayed):

```bash
sed -n '/^### Slice 6b-2b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 6b-2b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|code='
sed -n '/^### Slice 6b-2b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '—'
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 6b-2b record (merge, deploy, Danger zone phone check)" -m "Records slice 6b-2b (PR #<N>): the merge and deploy (no migration), and
the owner's phone check of Settings > Danger zone (read only in the real
church; a transfer, a leave and a delete in a throwaway church with a
second account). No church id, email address, invite link, token or
database URL is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `0`; `89 passed in <t>s`; one commit.

- [ ] **Step 14 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 6b-2b record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R <repo> --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 6b-2b record" \
  --body "Records slice 6b-2b (PR #<N>) in docs/ops-runbook.md → Slice 6b-2b record: the merge and deploy (no migration) and the owner's phone check of Settings > Danger zone. No church id, email address or invite link is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R <repo> --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R <repo>`. Report: "Slice 6b-2b is live and recorded; <n> follow-ups. Slice 6b is done."

- [ ] **Step R (only if the release must come out): Revert**

Code only (there is no migration to undo). On the owner's yes for each outward command, on a branch `claude/revert-6b2b` from `origin/main`: `git revert -m 1 --no-commit <merge sha>`, then keep the docs that rode along (`git checkout <merge sha> -- docs/ops-runbook.md docs/superpowers/plans/2026-10-10-slice-6b2b-danger-zone.md`), then the suites (frontend back to 1010 in 113 files), a commit "Revert slice 6b-2b (PR #<N>)" with the trailer, a PR, CI and the merge on the owner's yes; record it in the record.

Expected counts after this task: backend `2236 passed, 49 skipped` on `main`; frontend `1041 passed` in 115 files. The records PR adds no test.

---

## Build notes

**How this plan was written (2026-10-10).** Each task's code was built and run in a throwaway worktree of `6fe88d6` (in the session scratchpad, outside the repo directory; the repo's `.venv` as a symlink; a hard-linked copy of `frontend/node_modules`). The directives were then generated from that worktree by a script (a new file as **Create**, an addition at the end of a file as **Append**, every other change as **In … replace** with just enough whole-line context to occur once in the file as it stands at that point), and replayed (below). Baselines on `6fe88d6`: backend `2236 passed, 49 skipped`; frontend `1010 passed` in 113 files; typecheck 0, lint 0. While building:
- **What S assumed and what exists** (clarification 2). `useMembershipChanged({selectChurchId: null})` stores nothing (slice 1's own test says so) and never reported a failed `/me`, so it now resolves to a boolean. The `(church)` layout toasts lost access from two places, not one: with only the `churchAccessLost` subscriber guarded, T3's leave test still found "You no longer have access to Grace." (the exit's own `/me` refetch no longer lists the church, which is slice 1's second path), so both are guarded. The draft prune reruns whenever `/me`'s data changes, not once per load. No `forbiddenIsRole` meta (6b-2a). `ConfirmDialog` could not keep its confirm off, hence `confirmDisabled`. Every component S lists exists (`select`, `input`, `label`, `button`, `alert-dialog`); `npx shadcn` was not needed.
- **One test fix while building.** The fixtures' owner list (`memberList("owner")`) has four people (Ann, Mo, sam and Pat; Olive is left out when Pat is the owner), so the Delete body's count is 4, and the transfer test no longer compares the cache with the answer after the refetch replaced it.
- **The escapes lesson, a third time.** The first replay found T6 Step 3's stray-code-point check printing `4` and the em dash gate printing `1`, because the file writer had turned the `\u2028`, `\u2029`, `\ufffe`, `\uffff` escapes of the command, and the `\u2014` of T3's em dash test, into the characters themselves. Both are now written as escapes (the test reads `"\u2014"` in its source), and both checks print `0`.
- **A double tap.** `PendingButton` already turns the confirm into a disabled "Leaving…" before a second tap lands in jsdom, so the ref guard alone is never what the test sees; the mutation check below removes both (the guard and the pending state) and the test then counts two requests.

**Mutation checks** (each violation planted in the build worktree with T1-T5 applied, the named file or files run, the change undone; `danger-zone-page.test.tsx` unless named):

| Planted violation | Result |
|---|---|
| `runChurchExit` calls `membershipChanged` before cancelling and removing the draft keys | `church-exit.test.ts`: 1 failed, 1 passed |
| `runChurchExit` keeps the draft keys | `church-exit.test.ts`: 2 failed |
| `runChurchExit` does not mark the church | `church-exit.test.ts` and this file: 3 failed, 17 passed |
| The layout's `churchAccessLost` toast not guarded | `church-layout.test.tsx`: 1 failed, 17 passed |
| The layout's `/me` toast not guarded | `church-layout.test.tsx` and this file: 3 failed, 33 passed (the leave and delete exits both toast) |
| The mark never expires | `church.test.ts`, `church-layout.test.tsx`: 2 failed, 24 passed |
| `deleteNameMatches` ignores capitals | `people.test.ts` and this file: 2 failed, 39 passed |
| `deleteNameMatches` does not trim | `people.test.ts` and this file: 2 failed, 39 passed |
| Delete's confirm on before the name is typed (`confirmDisabled` dropped) | 1 failed, 17 passed |
| The owner may leave (`leaveBlock` always null) | `people.test.ts` and this file: 5 failed, 36 passed |
| Admins see the owner's cards | 3 failed, 15 passed |
| Leave without the ref guard and never pending | 1 failed, 17 passed (two `POST /church/leave`) |
| Delete without the ref guard and never pending | 1 failed, 17 passed (two `DELETE /church`) |
| Leave's title without `[overflow-wrap:anywhere]` | 1 failed, 17 passed |
| The Delete dialog without `wrapAnywhere` | 1 failed, 17 passed |
| An em dash in "You're the owner…" | 2 failed, 16 passed |
| The transfer does not refetch the profile | 2 failed, 16 passed (the toast-and-refetch test and the admin-form test) |

With the real code every file passes.

**Replay of the plan (2026-10-10).** A replay script parsed the plan's **Create**, **Append** and **In … replace** blocks, its "Run:" lines and its commit blocks, and applied T1-T7 in order onto a fresh detached worktree of the branch at the plan's first commit (`eafcccc`; scratchpad, the repo's `.venv` as a symlink, a hard-linked `frontend/node_modules`): all 45 directives applied (8 **Create**, 4 **Append**, 33 **In … replace**; every **In … replace** block occurred exactly once), all five commit blocks ran with the trailer, and its 42 commands' outputs are the ones quoted above (times as `<t>`), except the two gates fixed as described (escapes). The fixed plan was then replayed once more, with `--check`, onto another fresh worktree: see the last paragraph of these notes. The production build compiled and listed `/settings/danger`. Backend `2236 passed, 49 skipped` before and after (no backend file changes).

**Not run while planning** (each marked "(not replayed)" where it appears): T8 (the pushes, the PR and CI, the merge, Vercel's and Railway's deploys, the after-deploy check, the phone check, the record and its PR) and T8 Step R. No headless browser was available in this session, so the 375 px wrapping is checked by class in jsdom only; the phone check's Step 11 is the real-device check. No local Postgres was needed (no backend change; CI's `backend-postgres` job still runs).

## Spec coverage

| Owner answer or spec item | Task(s) and tests |
|---|---|
| 2026-10-10 answer 1 (6b-2b's scope: the Danger zone, its nav entry, the exit, the mark, the layout check) | T1-T4 |
| 2026-10-10 answer 3 (Delete on a throwaway church; the test churches kept; Leave and Transfer with the second account, else open and cancel) | T5 items 18-24; T8 Steps 5-12 |
| Answer 5: Leave for everyone, the owner blocked with the two explanations | T1 `leaveBlock` tests; T3 "shows member…", "shows admin…", "shows Leave off with why…", "tells the owner alone…" |
| Answer 5: Transfer (others, admins first; confirm; refetch profile, /me, members; the non-owner form; Invite someone when alone) | T1 `transferCandidates`; T3 "transfers to the person chosen…", "turns to the admin form inside the church layout…", "tells the owner alone…" |
| Answer 5: Delete (typed exact name; confirm; 422 under the box) | T1 `deleteNameMatches`; T3 "deletes only after the exact name…", "says when the server finds the name does not match…" |
| Answer 5: the banner, pending labels, toasts, 409 and 422 | T3 every test ("toasts the server's refusal…", "sends one leave for a double tap", "sends one delete for a double tap…") |
| Answer 5 / 2026-10-09 answer 7: Danger zone last in the nav | T4 |
| S `runChurchExit` order and its failure path; `useExitChurch`'s toast | T2 `church-exit.test.ts`, `membership.test.tsx`; T3 "says when /me does not come back after leaving" |
| S `(church)` layout change (no toast for a church just left; still shown otherwise and after 60 s) | T1 `markChurchExited / wasChurchExited`; T2 the three layout tests; T3 the leave and delete exits inside the real layouts; slice 1's own toast tests unchanged |
| S "Losing a role mid-session" (transfer or delete refused for the role) | T3 "toasts a role refusal of the transfer…" |
| S "Draft store" (the exit removes both draft keys at once) | T2 "marks the church, cancels…", "still drops the draft keys…"; T3 the leave and delete tests |
| S UX "Every page" (skeletons, ErrorState with Retry, pending words, toasts, inline errors with focus, React text, 44 px) | T3 "shows the error state with Retry…", "says when the server finds the name…", the long-name tests |
| S acceptance 15, 16, 18, 22 (Danger zone half) | T2, T3; T3; T3 and T5 item 24; T4 |
| The binding rules (no em dashes; no real ids, emails or links in docs; no SQL in chat; frozen Streamlit untouched; no network in tests) | Global Constraints; T3 "has no em dash…"; T6 Step 3; T7; T8 Step 13's checks |

S items **not** in 6b-2b: everything of 6b-1 and 6b-2a (shipped); S's `handleAuthErrors` meta test (no meta, clarification 2c); S manual check 7 (the Streamlit smoke check; Streamlit is retired, 2026-10-09 answer 2).

## Follow-ups (not in 6b-2b)

- The mark is per tab. If the owner ever wants another open tab to move on quietly too, a `storage` or `BroadcastChannel` message could carry it; nothing asks for it now.
- `useMembershipChanged`'s boolean could let the create and join forms say "Can't reach the server…" the same way; they keep their behavior here.

## Questions for the owner

Your 6b-2 planning answers of 2026-10-10 (all as recommended), your answers for this plan (the scope, the order of the exit, the phone check on a throwaway church) and your 6b answers of 2026-10-09 are binding and already in the plan. **There is no open question.** The few places where the plan departs from the design's wording follow an earlier answer or the code as it is (clarifications 2, 4, 6 and 9: the layout's two quiet paths instead of one line, both church names trimmed as the server does, a person without a name listed by email alone, the singular Delete sentence when the owner is alone); none changes what an owner can or cannot do. If you would rather have any of them as the design wrote it, say so and it is a one-line change in T1 or T3.

Owner steps still to come: the draft PR on your yes and ready on your yes, the merge on your yes (no backup or SQL check this time), and a phone check in seven short steps, the last six in a throwaway church "Delete me" with your second Google account; then the records PR (T8).

## Self-review

- **Coverage.** Every binding constraint has a home: 6b-2b's scope (clarification 1; T1-T4); the phone check on a throwaway church with the second account, the test churches kept (answer 4 (3); T5 items 18-24; T8 Steps 5-12); no migration and so no backup routine, said plainly (T7); no SQL in chat (Lessons carried; T7; T8 has none); no em dashes in user-facing copy (clarification 9; T3's test; T6 Step 3's grep); no real ids, emails or links in committed docs (fixtures use `@example.com`; commands use `<repo>`, `<api>`, `<app>`; T8 Step 13's grep); the frozen Streamlit files untouched (T6 Step 3); no network in tests (Global Constraints).
- **Placeholders.** None in T1-T7's code, tests, commands or expected outputs; every expected output is quoted from the replay. The `<…>` left are T8's runtime values, as in the earlier plans.
- **Consistency.** Names agree across tasks: `markChurchExited`, `wasChurchExited`, `resetExitedChurchesForTests` (T1) are used by T2's exit and layout and by `setup-dom.ts`; `leaveBlock`, `deleteNameMatches`, `transferCandidates`, `transferChoiceLabel` (T1) by T3's cards; `runChurchExit`, `useExitChurch`, `EXIT_ME_FAILED` (T2) by T3's hooks and tests; `useTransferOwnership`, `useLeaveChurch`, `useDeleteChurch`, `deleteNameError`, `TRANSFERRED`, `leftChurch`, `CHURCH_DELETED` (T3) by its cards and tests; `confirmDisabled` (T3) by the Delete card.
- **Not verified while planning:** the pushes, the PR and CI, Vercel's deploy, the page on a real phone (375 px in a real browser, the keyboard), the owner's checks: those are T8's steps. The 375 px wrapping is checked by class in jsdom only (no headless browser was at hand in this session; 6b-2a's build review measured the same classes in Chromium).
- **Judgement calls to watch in review:** the two guarded toasts instead of one line (2d); `useMembershipChanged`'s boolean (2b); `confirmDisabled` (2f); a note, not an alert (2g); both names trimmed (4); the email alone in the list (6); the singular Delete body (9); Leave's dialog closing on any failure, Delete's only on a failure other than the name (8).
