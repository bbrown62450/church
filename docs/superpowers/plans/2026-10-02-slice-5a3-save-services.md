# Slice 5a-3: The Save Card and the Services Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the third and last of the three 5a PRs (owner answer 1, 2026-10-01): **saving from the app, and the Services page.** After it merges, step 4 of the Service Builder (`/builder/review`) shows, top to bottom, a banner while the draft is a saved service, "Still to do" (4b's "Still needed", renamed, with "Everything's ready." when nothing is missing), an **Archive** card (where the draft stands, **Save to archive** / **Save changes** / **Save as new service**, **Start a new service**, and a dialog when someone else saved first), and the **Word documents** card from 5a-1. Saving records the service's hymns as used for its date (5a-2's server rule), so the Hymns step's "Used …" marks and the 12-week exclusion see services built in the app from then on. A new **Services** item in the menu lists the church's saved services, 20 at a time, newest service date first; a member opens one into the builder (after "Replace your unsaved draft?" when there is something to lose) or deletes one after confirming. The step bar's Review item and the summary's status line show "Saved" or "Unsaved changes". **Frontend only**: no backend change (5a-2's `/services` routes already do everything this needs), no migration (production stays at `0005_services_extras`), no new variable; production Streamlit (branch `streamlit-frozen`) is untouched.

**Architecture:** Bottom up, all in `frontend/src`. The draft becomes version 2 (`editing.date_iso`, `save_key_fingerprint`) with a tested migration; `lib/draft/save-key.ts` holds the save key rule; the store writes a replaced draft at once. `lib/draft/mapping.ts` gets its final form: `draftToServicePayload` (trimmed as the server trims), `serviceToDraft` and `markSaved`; `status.ts` gains `isDirty` (moved from `fingerprint.ts`), `reviewStatus`, `saveMode` and the "not in your hymnal" row, and `"review"` joins `SHIPPED_STEPS`. `lib/queries/services.ts` has `useServices`, `useSaveService` (PUT with `If-Match`, POST with the draft's key, the deleted-copy fallback, one retry after `idempotency_mismatch`), `useOpenService` and `useDeleteService`; the save sends the Word downloads' body (`serviceBody`), which stays within the server's limits. Review gains `EditingBanner`, `SaveCard` and `ConflictDialog`; `/services` renders `ServicesPage` with its own draft provider and `ServiceRow`; `AppNav` gains "Services".

**Tech Stack:** Next 16, React 19, TypeScript 5, Base UI, TanStack Query 5, zod, sonner, Vitest 3 with Testing Library. The backend (Python 3.11, FastAPI, pytest) is only run as a check.

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`: UX "Review step" (items 1-3), "Step status and summary panel", "Services page", "Mobile specifics"; Frontend "Routes and pages", "Components", "Library code" (`mapping.ts`, "Draft schema change", `status.ts`, `lib/queries/services.ts` with the save key rule and `useSaveService`, "State rules", "Handing readings to slice 2"); Behavior changes 9-15; Testing (`mapping.test.ts`, `migrate.test.ts`, `status.test.ts`, `save-key.test.ts`, `review-step.test.tsx`, `services-archive.test.tsx`), manual checks 5-9, 12, 13; acceptance criteria 9, 13, 14; and the amendments of 2026-10-01 (three PRs; owner answers 1-9) and 2026-10-02 (5a-2 as planned).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.6 (the frontend key rule; the save key in the draft), §1.7 (`If-Match`, the 409 message), §4.2 (nav items appear when their slice ships), §4.4 (the keys; service save and delete invalidate `services` and `hymns`), §4.5 (`ifMatch`, `idempotencyKey`), §4.6 (the draft shape with 5a's fields, "Versioning", "When the draft is cleared or replaced", "Loading an archived service"), §4.7 (the Review item's statuses, the summary's status line), §4.8, §4.9, and the Amendments rows naming 5a.
- The 5a-1 and 5a-2 plans: `docs/superpowers/plans/2026-10-01-slice-5a1-documents.md` (`documentRequest` within the limits, the Word documents card) and `docs/superpowers/plans/2026-10-02-slice-5a2-saving.md` (the routes and messages in its clarification 3, the church-scoped key in clarification 4 and its stale-replay note, `PUT`'s check order in clarification 5, "what is sent is stored" in clarification 7, `ServiceOut` with `ArchivedHymns` and `CustomElementOut` in clarification 12 and its build notes).
- Format model: the 5a-1 plan.
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `a789fb8` = `origin/main` `c9c8c6b` plus the runbook commit "Runbook: slice 5a-2 record", 2026-10-02): backend `1335 passed, 16 skipped`; frontend `618 passed` in 81 files; typecheck and lint clean; Alembic head `0005_services_extras` (production too: runbook "Slice 5a-2 record"; 26 saved services, 0 undated); 4 runbook owner markers. `DRAFT_VERSION` is 1 and `migrations` is empty; `editing` is `{service_id, saved_at}`; nothing sets it. `mapping.ts` is the provisional mapping (untrimmed text); `isDirty` is in `fingerprint.ts`, which imports `status.ts`. `SHIPPED_STEPS` is readings, hymns, liturgy; `stepStatus` returns "Not in archive" for Review. Review renders `StillNeeded` ("Still needed", nothing when empty), the Word documents card and a dashed "Saving services to the archive is coming soon." box. `showAvailableBanner` shows for archive fields whose `date_origin` is not "archive". `DraftStore.replace` writes 400 ms later. `NAV_ITEMS` holds Builder only. `lib/queries/keys.ts` already has `services` and `service`; `client.ts` already sends `ifMatch` and `idempotencyKey`; `schema.d.ts` already has `ServiceOut`, `ServiceSummary`, `Page_ServiceSummary_`, `ArchivedHymn(s)`, `CustomElementOut`, `DeletedOut` (5a-2). `CustomElementOut` keeps a stored element over today's limits, which a re-save would send back and the server would refuse with 422 (5a-2 record, Follow-ups). The reviewer's notes are dropped when `created_at` changes. sonner replays a toast still showing to the next `Toaster` (`liturgy-step.test.tsx` dismisses them).
- While this plan was written, two docs commits from the owner's session landed on the branch (`8ef6251` and `71d50e1`, the "Hear it from the pews" idea, `docs/superpowers/specs/2026-10-02-pew-voices-idea.md`); they ride along in this PR with the 5a-2 record and touch nothing the tasks change.
- Every task's code was written and run by the planner in a throwaway worktree of `a789fb8`, and the plan's directives were then replayed onto a fresh worktree of `a789fb8` (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted, since Vitest reports files as they finish); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` (a failure is named); then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`. Backend, as a check only: `.venv/bin/python -m pytest -q | tail -1`.
- The API does not change: never run `export_openapi.py` or `gen:api` to change anything (T7 runs them to show nothing changes).
- Branch `claude/slice-2-plan-4q33le`, at `a789fb8` plus this plan's commits (`WIP plan: slice 5a-3` …, then `Plan: slice 5a-3, Save and the Services page (owner answers 2026-10-01/02)` and its follow-up) and the two idea-doc commits, then T1-T6. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1335 → 1335 passed, 16 → 16 skipped; frontend 618 → 645 in 81 → 83 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 18 and has no em dashes; existing copy keeps its own punctuation (the checklist's rows read "{message} — {link}", as 4b shipped them).
- No church id, email address, token or database URL in any doc, commit or record.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.

### How the file directives below read
As in the 5a-1 plan: **Create `path`:** the block is the whole file (for `frontend/src/lib/draft/mapping.ts`, which T2 rewrites, it replaces the existing file whole, as T2's Files list says); **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted.

### Baselines and counts
- Starting baselines: backend **1335 passed, 16 skipped**; frontend **618 passed in 81 files**, typecheck and lint clean; Alembic head **`0005_services_extras`** (5 revision files; no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A frontend delta is the number of new `it(`; the backend never moves.

  | After | Frontend (delta) | Frontend | Backend |
  |---|---|---|---|
  | T1 | +4 (`save-key.test.ts` 2, `migrate.test.ts` 1, `store.test.ts` 1; `schema.test.ts`, `status.test.ts` edited) | 622 in 82 | 1335 passed, 16 skipped |
  | T2 | +6 (`mapping.test.ts` 4, `status.test.ts` 2; `fingerprint.test.ts` edited) | 628 in 82 | 1335 passed, 16 skipped |
  | T3 | +1 (`dates.test.ts`) | 629 in 82 | 1335 passed, 16 skipped |
  | T4 | +8 (`review-send-step.test.tsx`; its other cases and `builder-shell.test.tsx` edited) | 637 in 82 | 1335 passed, 16 skipped |
  | T5 | +8 (`services-page.test.tsx`; `app-header.test.tsx` edited) | 645 in 83 | 1335 passed, 16 skipped |
  | T6 | 0 (docs) | 645 in 83 | 1335 passed, 16 skipped |

- CI `backend-postgres` stays `16 passed, 1335 deselected`.

### Layering and code rules (carried)
- Pages and components never call `apiFetch`: `lib/queries/services.ts` uses `useApi().church` (F §4.5); mutations are `useChurchMutation`, never optimistic, and invalidate on success (F §4.4).
- The draft is changed only through `useDraft()` (`update`, `replace`, `peek`); pure transitions in `lib/draft/*` return the same object when nothing changes.
- Touch targets 44 px below `md`; text wraps at 375 px; no raw HTML (F §4.8); dialogs are Base UI AlertDialogs (F §4.9).
- Nothing about the reviewer's notes is saved or sent (owner answer 9; `ServiceDraft` refuses unknown fields, 5a-2 clarification 17).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** (branch `streamlit-frozen`) is frozen and retired for real use (owner answer 6); merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge (this PR changes only what Vercel serves, plus docs).
4. **The 5a spec's decisions** stand, except where the owner's answers and its amendments change them (S gains an amendment, T6).

### Owner answers (Beau, 2026-10-01 and 2026-10-02, binding)
1. **Three PRs.** 5a-1 (Word downloads, PR #40) and 5a-2 (saving on the server, `0005_services_extras`, PR #43) are merged. **This is the third: the Save card and the Services page.**
2. **No order-of-worship preview on Review** (the Liturgy step shows the order).
4. **A save locks a default-following Benediction and the communion setting to what was saved**, as opening a saved service does (their origin becomes "archive"; clarification 6).
5. **No "Readings for … are available" while the date is still the saved date** (clarification 8).
6. **Streamlit is retired; deleting a service recalculates that date's hymn use** (the server does it since 5a-2; this PR refreshes the hymns after a delete).
8. **A guided phone check after the PR** (T8).
9. **Reviewer notes stay in memory only:** opening a saved service clears them; saving keeps them (clarification 7).

Answers 3 and 7 concern 5a-1's Word file and are not repeated here.

**Already decided in S, cited, not asked again:** confirm before opening over unsaved work ("Replace your unsaved draft?", S "Services page" Open flow; F §4.6 "Loading" step 1; behavior change 10); changing the date means Save as new service (S UX "Save card"; behavior change 14; parity with app.py:1029-1035); 20 a page and no search (S "Services page"; Scope "Archive search … Not planned"); any member can delete, with S's confirm text (S "Delete flow"; owner decision 5); hymn use is recorded on save only (S behavior change 3; owner decision 9).

### Owner answers to this plan's questions
Pending: "Questions for the owner" (end of this plan) lists the twelve choices made here, each written as recommended.

**Later, out of scope:** 5b (email: the Review step's email card, Gmail, contacts), 6a (Settings), the printed bulletin, Voices of the Church.
## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended).

1. **[owner-visible] What 5a-3 ships** (owner answer 1). Saving from Review & send, the conflict dialog, the editing banner, "Start a new service", the Services page (list, open, delete), the "Services" menu item, the Review statuses in the step bar and the summary, `serviceToDraft`, the save key in the draft and the draft version bump. **No backend change:** 5a-2's routes already give everything the screens need (`GET /services` pages 20 with `total`; `ServiceOut` with `hymns.<slot>.in_hymnal`, `custom_elements` as `CustomElementOut`, `created_by` and `saved_at`; `PUT` with `If-Match` and the 409 message; `POST` with the church-scoped `Idempotency-Key`; `DELETE` recalculating hymn use), so the API snapshot and `schema.d.ts` do not change (T7 checks it). No migration; production stays at `0005_services_extras`. Not here: the email card (5b) and the order-of-worship card (owner answer 2).
2. **[owner-visible] Review & send, top to bottom** (S UX "Review step"; owner answer 2): the editing banner (only while the draft is a saved service, clarification 4); "Still to do" (clarification 3); the **Archive** card (clarification 5); the **Word documents** card (5a-1's, plus the save tip, clarification 17). The Archive card moves above the Word documents, where S puts it (people come back to Review to save or download), and 5a-1's dashed "Saving services to the archive is coming soon." box goes. No order-of-worship card, no email card.
3. **[owner-visible] "Still to do"** (S UX "Review step" item 2; the 5a-1 plan's clarification 3 deferred it here). 4b's "Still needed" list is renamed "Still to do", keeps every row it had, and gains one row per hymn that is not in the hymnal (a saved hymn the church no longer has, or one never in it): "{Title} isn't in your hymnal", linking "Choose a replacement" to Hymns, in slot order where that slot's "No … hymn" row would be. With nothing missing it says "Everything's ready." Nothing it lists blocks Save or the downloads but the date (F D9). The rows keep 4b's form "{message} — {link}". S's names `ReviewChecklist` and `missingItems` are not used: the component stays `StillNeeded` (`still-needed.tsx`) and the function `stillNeeded`, so 4b's tests only change their copy.
4. **[owner-visible] The editing banner** (S UX "Review step" item 1): while `editing` is set, "You're editing the saved service for {October 4, 2026}. Changes stay on this device until you save." A saved service with no date (a legacy row; production had none on 2026-10-02, 5a-2 record) says instead "This saved service has no date. It's set to {Sunday, October 11, 2026} for now." with the link "Check the date" (step 1); a save gives it a date, so that line goes. S's second line, "{n} hymn(s) from this service aren't in your hymnal. [Choose replacements]", is left out: "Still to do", just below, lists each such hymn with its own link, so the banner would say it twice. The banner is advice only and never blocks anything.
5. **[owner-visible] The Archive card** (S UX "Save card"; F D9):
   - The status line: "Not in the archive yet."; "Saved to the archive · {Oct 1, 10:42 AM}"; "Unsaved changes · last saved {Oct 1, 10:42 AM}" (`saved_at` in the viewer's time zone, clarification 17).
   - The button (`size="touch"`, full width on a phone): **"Save to archive"** when the draft is not a saved service; **"Save changes"** when it is and the date is the saved date; **"Save as new service"** when the date differs (S, parity), with below it "The date changed from {October 4, 2026} to {October 11, 2026}, so this will be saved as a new service. The {October 4} service stays in the archive." or, for a saved service with no date, "The saved service has no date, so this will be saved as a new service on {October 11, 2026}. The undated service stays in the archive." The sentence describes the button (`aria-describedby`).
   - "Saving…" while it runs (the `PendingButton` keeps focus); success is the toast "Service saved" and the status line moves to "Saved to the archive · …".
   - The button is off only without a service date ("Choose a service date on step 1 to save.") or while a Date & readings field shows its message ("Fix the readings on step 1 to save."), the same two conditions as the downloads (5a-1 build review fix 6). It stays on when nothing changed: a save then stores the same service again with a new time (S: Save is available whenever the date is valid).
   - **"Start a new service"** (outline button): clarification 13.
6. **[owner-visible] What a save does to the draft** (owner answer 4; S `useSaveService` onSuccess; F §4.6 "Save keeps it as the working copy"). The draft stays on screen as the working copy. `editing` becomes the saved service (`service_id`, `saved_at`, `date_iso` from the answer), `saved_fingerprint` the fingerprint of the payload that was sent, so the draft reads "Saved" (or "Unsaved changes" if it was edited while the save ran). Then what followed a default becomes the saved service's own, as when a saved service is opened: a Benediction that followed the church default keeps its text with origin "archive" ("empty" when that text was blank), and communion that followed the first-Sunday rule keeps its setting with origin "archive". So a later change of the church's default Benediction does not change this service, and a later date change does not flip its communion; the Liturgy step's communion card then says "Set from the saved service." with "Use default", as it does for an opened service, and the Benediction card offers "Use church default" as for any text not following the default. One consequence, the same as for an opened service: "Review service" (the reviewer) now reviews that Benediction too, since it is the service's own text. Communion the user set stays "user". Neither change touches the payload, so the draft stays "Saved".
7. **Reviewer notes** (owner answer 9). They live in memory and are keyed by the draft's `created_at` (`notes.ts`). Saving keeps `created_at`, so the notes stay; opening a saved service (from Services, or "Reload their version" in the conflict dialog) builds a new draft with a new `created_at`, so they go, and any AI run on the old draft is cancelled, as New service does. Nothing about them is sent with a save.
8. **[owner-visible] "Readings for … are available"** (owner answer 5). `showAvailableBanner` returns false while the draft is a saved service and its date is still the saved date (`editing.date_iso === readings.date_iso`): after opening a saved service, and also after saving a draft whose readings were typed or edited, the saved readings are the service's own for that date. On another date the banner shows as before (the lectionary then has sets for a date the saved readings were not chosen for); back on the saved date it goes again. A saved service with no date has no saved date, so the banner behaves as for any draft.
9. **[owner-visible] The conflict dialog** (S UX "Save card" Conflict; F §1.7). A `PUT` answered 409 opens an AlertDialog titled "Someone else changed this service" whose text is the server's message, "This service was changed by someone else. Reload it to see their changes." Three buttons: **"Reload their version"** (`GET /services/{id}`, then the draft becomes their saved copy; the dialog is the confirmation; toast "Loaded the latest version."; "Loading…" while it runs); **"Save mine as a new service"** (a POST with the save key; theirs stays in the archive; toast "Service saved"; "Saving…" while it runs); **"Cancel"** (nothing changes; the draft keeps "Unsaved changes" or "Saved" as it was). While one action runs the other is off. If their copy was deleted meanwhile, "Reload their version" toasts "That service is no longer in the archive." and closes the dialog; the next "Save changes" then saves a new service (clarification 10).
10. **[owner-visible] The other outcomes of a save** (S UX "Save card"; S "Save key rule"; F §1.6):
    - **The saved copy was deleted** (a `PUT` answered 404 with no `details.field`): the client POSTs at once and toasts "The archived copy was deleted, so this was saved as a new service." (S).
    - **A hymn the church no longer has** (404 with `details.field = "hymns.<slot>.hymn_id"`): a toast with the server's message, "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.", and the action **"Go to Hymns"**. After the hymn is replaced, Save works at once: the rejected try's key is never used again.
    - **The save key** (`lib/draft/save-key.ts`, S's rule): every POST uses `draft.save_key`; `keyForPost` replaces it first when the pending fingerprint (`save_key_fingerprint`) belongs to another body; after any 2xx or 4xx but a 429 (`settleOutcome`, `lib/idempotency.ts`, F §1.6 2a amendment) `settlePost` replaces it and clears the fingerprint; after a network error, a timeout, a cancel, a 5xx or a 429 it keeps both, so an identical retry replays the server's stored answer instead of saving twice, and an edited retry gets a new key. It lives in the draft, so it survives a refresh. **`idempotency_mismatch`** is retried once, automatically, with the new key, and the member sees nothing; a second one shows its message. A `PUT` never sends the key.
    - **Anything else**: a toast with `errorToastMessage` ("Can't reach the server. Check your connection and try again.", "This is taking too long. Try again.", "Something went wrong. (Ref: …)", or the server's sentence); none after a 401 or a lost church (the app's own handling says it, as the downloads do). The draft is never cleared by a failure, and the member can edit and save again at once.
11. **A replayed `POST` answer may be stale** (5a-2 plan, clarification 4). Within 15 minutes, an identical retry of a `POST` whose first try had an unknown outcome gets the first answer back, even if that service was changed (`saved_at` moved) or deleted since. Nothing special is done: the draft records that answer like any other, and if it is stale the next "Save changes" meets the 409 (the conflict dialog) or the deleted-copy 404 (saved as a new service, with its toast), which already handle it. A replay with a later edit is impossible: an edit changes the fingerprint, and the key with it.
12. **[owner-visible] The body a save sends** (5a-2 record, Follow-ups: "a re-save of a stored custom element over today's limits is a 422 on that field, which 5a-3 must handle"). Save sends exactly what the downloads send (`serviceBody`, the service part of 5a-1's `documentRequest`): the draft's payload kept within `ServiceDraft`'s limits. Pydantic's 422 would say only "The request was not valid.", and a member could not tell which element to fix, so the client never sends what the server refuses: a stored custom element longer than today's limits (200 for a label, 10 000 for text; possible only if a limit is lowered after it was saved, since 5a-2 stores only what passed them) is saved cut to the limit, exactly as the Word file already prints it; an element whose label is blank as the server reads it is left out, as before. The occasion and readings never need cutting here, since Save is off while their messages show (clarification 5). The draft keeps its own text; the payload it is compared with is the uncut one (`draftToServicePayload`), so "Saved" means "as the draft holds it".
13. **[owner-visible] "Start a new service"** (S UX "Save card"; F §4.6 item 1). It runs New service's existing flow (`useNewService`, the header menu's "New service" since 2b): a draft with nothing to lose resets at once; otherwise the existing question "Start a new service?", "This clears the current draft on this device.", "Start new service". S's own copy for this question ("Your current draft has changes that aren't saved to the archive. Starting a new service discards them." / "Discard and start new") is not used, so both doors ask the same thing in the words the owner already knows. A saved draft with no unsaved changes counts as nothing to lose (it is in the archive). The fresh draft keeps the Bible translation, as New service does; the builder opens Date & readings.
14. **[owner-visible] The Services page** (S "Services page"; F §4.1, §4.2, §4.8). `/services`, a client page in the `(church)` layout:
    - Header: "Services", "Saved services for {church name}.", and **"New service"** (the same flow as clarification 13).
    - The list: 20 rows a page, newest service date first, undated last (the server's order). Each row is one button (at least 44 px tall) that opens the service, with three lines: the date ("October 4, 2026"; a legacy row's stored date text when it has no readable date; else "No date"), the occasion (else "No occasion"), and "Created by {name} · last saved {Oct 1, 10:42 AM}" ("Last saved {…}" when the author is gone; the author never changes on a later save, so the line does not claim the author made the last save). A badge "Editing" marks the service the draft holds. Beside each row a 44 px menu button ("More actions for {date}") holds **"Delete…"**.
    - Below the list: "Showing {n} of {total}" and, while there are more, **"Show more"** ("Loading…" while it loads).
    - Loading: five skeleton rows. An error shows the error state with **Retry**, never an empty list. Empty: "No saved services yet", "Services you save from the builder appear here." and **"Build a service"** (to `/builder`).
    - No search, no sorting choice, no filters (S).
15. **[owner-visible] Opening a service** (S "Open flow"; F §4.6 "Loading an archived service"). A tap on a row: when the draft has something to lose (`isDirty`: unsaved changes to a saved service, or a never-saved draft that is not pristine, a translation choice included, since opening resets it), "Replace your unsaved draft?" with "Your current draft for {October 4, 2026} has changes that aren't saved to the archive. Opening this service replaces it." and **"Replace draft"**; otherwise at once. The row then says "Opening…" (the other rows are off), the client fetches `GET /services/{id}` (always fresh), `serviceToDraft` builds the draft (S's rules: readings with `fields_origin` "archive", the saved date or, for an undated service, the next Sunday; slot hymns, one no longer in the hymnal kept with its title and no id; saved sections on with origin "archive", the others off and empty, no church Benediction added; communion "archive"; custom elements with new ids; "Saved"; on Review; a new `created_at` and save key), the draft is written at once, and the builder opens on **Review & send**. A 404 toasts "That service is no longer in the archive." and refreshes the list; any other failure toasts its message, and the draft is unchanged. S's lectionary prefetch is left out: the builder's lectionary lookup (`LectionarySync`) runs on every step, Review included, as soon as the builder opens.
16. **[owner-visible] Deleting a service** (S "Delete flow"; owner decision 5; owner answer 6). "Delete…" opens "Delete this service?" with "“{occasion, or "Untitled service"}” on {date} will be removed from the archive for everyone in {church}. This can't be undone." ("“{…}” (no date) will be removed …" for a row with no date), plus "You're editing this service. Your current draft will be cleared too." when it is the service the draft holds, and **"Delete service"** (destructive; "Saving…" while it runs, the `ConfirmDialog` default). Any member may. On success the list is refreshed before the dialog closes, so the row is gone with it, with no toast; if it was the service being edited the draft resets to a fresh one (keeping the translation, as New service does); the hymns are refreshed too, since the server recalculated that date's hymn use (owner answer 6). A 404 toasts "That service is no longer in the archive." and refreshes the list. **A service deleted elsewhere while it is open here** stays in the draft as it is (nothing polls); its row is gone from Services; the next "Save changes" saves it as a new service and says so (clarification 10).
17. **[owner-visible] Where the archive status shows** (S "Step status and summary panel"; F §4.7):
    - The step bar's Review item: "Not in archive" (muted, as before) until the draft is saved or opened, then "Saved" (with the ✓ of a complete step) or "Unsaved changes" (`reviewStatus`; `"review"` joins `SHIPPED_STEPS`).
    - The summary's status line: "Draft saved on this device · Not in archive", "… · In archive (saved {Oct 1, 10:42 AM})", "… · In archive (saved {…}) · Unsaved changes" (the device half is 2b's, unchanged); the whole line links to Review & send (44 px tall below `lg`).
    - The saved time: `formatSavedAt` in `lib/dates.ts`, the viewer's own time zone, "Oct 1, 10:42 AM", with the year when it is not the current year ("Dec 31, 2025, 6:30 PM").
    - **The save tip** (S UX item 4, deferred by 5a-1): after a download in this visit to Review, while the draft is not "Saved", the Word documents card adds "Tip: save this service so its hymns count as recently used." (hymn use is recorded on save only).
    - **The menu**: "Services" after "Builder", in the header row from `md` and the segmented row below it (F §4.2); current under `/services`.
18. **[owner-visible] Every new user-facing string** (no em dashes):
    - Review: "You're editing the saved service for {October 4, 2026}. Changes stay on this device until you save."; "This saved service has no date. It's set to {Sunday, October 11, 2026} for now."; "Check the date"; "Still to do" (was "Still needed"); "Everything's ready."; "{Title} isn't in your hymnal" with "Choose a replacement"; "Not in the archive yet."; "Saved to the archive · {time}"; "Unsaved changes · last saved {time}"; "Save to archive"; "Save changes"; "Save as new service"; "The date changed from {date} to {date}, so this will be saved as a new service. The {October 4} service stays in the archive."; "The saved service has no date, so this will be saved as a new service on {date}. The undated service stays in the archive."; "Choose a service date on step 1 to save."; "Fix the readings on step 1 to save."; "Start a new service"; "Tip: save this service so its hymns count as recently used."
    - Toasts: "Service saved"; "The archived copy was deleted, so this was saved as a new service."; "Loaded the latest version."; the action "Go to Hymns".
    - The conflict dialog: "Someone else changed this service"; "Reload their version"; "Save mine as a new service"; "Loading…" (its pending label); the body is the server's message.
    - Status: "Saved", "Unsaved changes" (step bar); "In archive (saved {time})" and "In archive (saved {time}) · Unsaved changes" (summary).
    - Services: "Services" (menu and heading); "Saved services for {church}."; "New service" (the header menu's existing words); "No date"; "No occasion"; "Created by {name} · last saved {time}"; "Last saved {time}"; "Editing"; "Opening…"; "More actions for {date}" (screen readers); "Delete…"; "Showing {n} of {total}"; "Show more"; "Loading…"; "No saved services yet"; "Services you save from the builder appear here."; "Build a service"; "Replace your unsaved draft?"; "Your current draft for {date} has changes that aren't saved to the archive. Opening this service replaces it."; "Replace draft"; "Delete this service?"; "“{occasion}” on {date} will be removed from the archive for everyone in {church}. This can't be undone."; "“{occasion}” (no date) will be removed …"; "Untitled service"; "You're editing this service. Your current draft will be cleared too."; "Delete service".
    - From the API, unchanged: "This service was changed by someone else. Reload it to see their changes."; "That service is no longer in the archive."; "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."; "This request was already sent with different details." Reused unchanged: "Start a new service?", "This clears the current draft on this device.", "Start new service", "Saving…", "Cancel", "Retry", "Loading" (screen readers).
19. **The draft, version 2** (S "Draft schema change"; F §4.6 "Versioning"). `DRAFT_VERSION` 1 → 2: `editing` is `{service_id, saved_at, date_iso: YYYY-MM-DD | null}`, and `save_key_fingerprint: string | null` is new (null in a fresh draft). `migrations[1]`: `editing` stays null when null, otherwise gains `date_iso` from `readings.date_iso` (null when that is not a real date); `save_key_fingerprint` starts null. No version 1 draft has `editing` set (nothing could save), so the migration only adds the field; it has its unit test, and a stored version 3 is "a future version" (restore fails, the raw value is backed up, as F says). The names `DraftV1` and `draftV1Schema` stay, so no importer changes. Two more store changes: **`replace` writes the draft at once** (New service, an opened service, the reset after a delete), since the Services page has its own provider and the builder it opens reads the stored draft when it mounts, before that page unmounts and flushes; and `isDirty` moves from `fingerprint.ts` to `status.ts`, beside `reviewStatus` and `saveMode`, so `status.ts` can use it without an import cycle (`fingerprint.ts` imported `status.ts`). `draftToServicePayload` takes its final form (S "mapping.ts"): occasion, card texts, sermon title and custom elements trimmed as the server trims them, so a trailing space never reads as "Unsaved changes" against what the server stored; before 5a-3 no draft has a `saved_fingerprint`, so the change of fingerprint affects nothing stored (S says so).
20. **Query keys and invalidations** (F §4.4). The list: `["church", id, "services", {limit: 20}]`, an infinite query, the next offset `offset + items.length` while below `total`. A save: `setQueryData(["church", id, "service", sid])`, then `services` and `hymns` invalidated (a save rebuilds that date's hymn use, so `recently_used` changes). A delete: `removeQueries` for that service, then `services` and `hymns` (owner answer 6), awaited, so the row is gone when the dialog closes. Opening: `GET /services/{id}` every time (S `staleTime: 0`), the answer cached under `service`. A 404 on open or delete invalidates `services`.
21. **Screen readers and the phone** (F §4.8, §4.9). The Archive card is a region named by its heading; the save sentence describes the button; the `PendingButton`s keep focus while pending ("Saving…", "Loading…"); success and failure are announced by the toasts. The conflict dialog and both confirmations are AlertDialogs (focus trapped; Escape cancels; 44 px buttons below `md`). On Services, each row is one button whose name reads the date, the "Editing" badge, the occasion and the saved line; "Opening…" replaces the saved line and the button is `aria-busy`; each menu button is named "More actions for {date}"; the delete dialog returns focus to "New service" (the row it came from is gone). Five skeleton rows sit in a `status` named "Loading". All text renders as React text.
22. **Docs** (T6). S gains "Amendment 2026-10-02: 5a-3 as planned"; F's Amendments index gains a row (§4.2, §4.6, §4.7); `docs/manual-verification.md` → "Slice 5a" gains items 12-17, items 12-16 marked "(owner, after 5a-3)". The runbook record is T8's. The 5a-2 record commit (`a789fb8`, `docs/ops-runbook.md`) is not on `main` yet and rides along in this PR.

### Risks
- **An open tab still running the old app** (version 1 code) that enters the builder after a new tab wrote a version 2 draft cannot read it: it says "We couldn't restore your unsaved draft.", keeps the raw value in its backup slot and starts fresh. T8 Step 2 has the owner reload the app before the check; saved services are in the archive either way.
- **Reverting 5a-3** has the same effect once in each browser: the version 1 code finds a version 2 draft (T8 Step R). Saved services and hymn use stay.
- **A timed-out save that in fact succeeded, then an edit, then Save** creates a second service (S Risks, accepted): the edit gives a new key. Services lists both, and either can be deleted.
- **The draft held by Services is read when that page mounts**, before the builder's last edit (at most 400 ms old) is written; the builder writes it when it unmounts, and a later save or open reads storage again. Only a "Replace your unsaved draft?" asked within that 400 ms could miss an edit made in it.
- **No polling:** a service changed or deleted elsewhere is found out at the next save (clarifications 9, 10, 16) or when the list refreshes (on focus, after a save or delete).

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `frontend/src/lib/draft/save-key.ts` (+ `.test.ts`) | `keyForPost`, `settlePost` | T1 |
| `frontend/src/lib/queries/services.ts` | `useServices`, `useSaveService`, `useOpenService`, `useDeleteService`, `isConflict`, the toasts | T3 |
| `frontend/src/components/builder/review/conflict-dialog.tsx` | the 409 dialog | T4 |
| `frontend/src/components/builder/review/editing-banner.tsx` | the banner | T4 |
| `frontend/src/components/builder/review/save-card.tsx` | the Archive card | T4 |
| `frontend/src/app/(signed-in)/(church)/services/page.tsx` | the route | T5 |
| `frontend/src/components/services/services-page.tsx` (+ `.test.tsx`) | `ServicesPage`, `deleteDescription` | T5 |
| `frontend/src/components/services/service-row.tsx` | `ServiceRow`, `serviceDateLabel`, `savedByLine` | T5 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `frontend/src/lib/draft/schema.ts`, `migrate.ts`, `store.ts` (+ `schema.test.ts`, `migrate.test.ts`, `store.test.ts`, `status.test.ts`) | version 2 and its migration; `replace` writes at once; a test draft's `editing` gains `date_iso` | T1 |
| `frontend/src/lib/draft/mapping.ts` (whole file), `status.ts`, `steps.ts`, `fingerprint.ts`, `readings.ts` (+ `mapping.test.ts`, `status.test.ts`, `fingerprint.test.ts`) | the final payload, `serviceToDraft`, `markSaved`; `isDirty`, `reviewStatus`, `saveMode`, the hymnal row; `"review"` shipped; owner answer 5 | T2 |
| `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts` | the `/services` aliases; `savedService`, `serviceSummary`, `servicePage` | T2 |
| `frontend/src/components/builder/step-progress.tsx`, `new-service-menu-item.tsx` | "Saved", "Unsaved changes"; `isDirty`'s new home | T2 |
| `frontend/src/lib/dates.ts` (+ `dates.test.ts`), `frontend/src/lib/documents.ts` | `formatSavedAt`; `serviceBody` | T3 |
| `frontend/src/components/builder/review/review-send-step.tsx` (+ `.test.tsx`), `documents-card.tsx`, `frontend/src/components/builder/still-needed.tsx`, `summary-panel.tsx`, `builder-shell.test.tsx`, `frontend/src/app/(signed-in)/(church)/builder/review/page.tsx` | the step's layout; the save tip; "Still to do"; the summary's archive half; the comment | T4 |
| `frontend/src/components/app/app-nav.tsx` (+ `app-header.test.tsx`) | "Services" | T5 |
| `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, `docs/manual-verification.md` | the amendment; the Amendments row; items 12-17 | T6 |
| `docs/ops-runbook.md` | "### Slice 5a-2 record" (commit `a789fb8`, riding along); "### Slice 5a-3 record" (the records PR, after the merge) | T8 |

**Counts in the PR:** 12 created (this plan, the 10 files above, and the ride-along `docs/superpowers/specs/2026-10-02-pew-voices-idea.md`), 34 modified (the 33 code and docs files above, and `docs/ops-runbook.md` through the 5a-2 record commit; the 5a-3 record comes in the records PR after the merge): 46 paths. **Untouched:** every backend file, migrations, `openapi.json`, `schema.d.ts`, `lib/api/client.ts`, `lib/queries/keys.ts`, `lib/draft/context.tsx`, `liturgy/*`, `hymns/*`, `readings/*`, `app.py`, Streamlit.

**Task order and review batch:** T1 → T6, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T7 verifies and opens the draft PR on the owner's yes; T8 merges on the owner's yes, takes the owner through the phone check and writes the record.

---
### Task 1: The draft, version 2: the saved service's date and the save key (S "Draft schema change", "Save key rule"; F §1.6, §4.6; clarifications 10, 19)

**Files:**
- Create: `frontend/src/lib/draft/save-key.ts`, `frontend/src/lib/draft/save-key.test.ts`
- Modify: `frontend/src/lib/draft/schema.ts`, `frontend/src/lib/draft/migrate.ts`, `frontend/src/lib/draft/store.ts`, `frontend/src/lib/draft/schema.test.ts`, `frontend/src/lib/draft/migrate.test.ts`, `frontend/src/lib/draft/store.test.ts`, `frontend/src/lib/draft/status.test.ts`

- [ ] **Step 1 (agent): Write the failing tests**

`status.test.ts` only gains `date_iso` in a draft's `editing` (the version 2 shape); `store.test.ts`'s "future version" becomes 3.

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
    expect(migrations).toEqual({});
    expect(parseStoredDraft(JSON.stringify(d), OWNER)).toEqual(d);
````

**with:**

````ts
    expect(Object.keys(migrations)).toEqual(["1"]);
    expect(parseStoredDraft(JSON.stringify(d), OWNER)).toEqual(d);
  });

  it("migrates a version 1 draft: editing gains the draft's date, and save_key_fingerprint starts null (slice 5a-3)", () => {
    const { save_key_fingerprint, ...v1 } = { ...testDraft(), version: 1 };
    expect(save_key_fingerprint).toBeNull();
    const editing = { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00" };
    expect(parseStoredDraft(JSON.stringify(v1), OWNER)).toEqual({ ...testDraft(), save_key: v1.save_key, version: 2 });
    expect(parseStoredDraft(JSON.stringify({ ...v1, editing }), OWNER)).toMatchObject({
      version: 2,
      save_key_fingerprint: null,
      editing: { ...editing, date_iso: "2026-10-04" },
    });
    const undated = { ...v1, editing, readings: { ...v1.readings, date_iso: "" } };
    expect(parseStoredDraft(JSON.stringify(undated), OWNER).editing).toEqual({ ...editing, date_iso: null });
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````ts
      ["a future version", JSON.stringify({ ...d, version: 2 })],
````

**with:**

````ts
      ["a future version", JSON.stringify({ ...d, version: 3 })],
````

**Create `frontend/src/lib/draft/save-key.test.ts`:**

````ts
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { settleOutcome } from "@/lib/idempotency";
import { testDraft } from "@/test/fixtures";

import { keyForPost, settlePost } from "./save-key";

describe("the save key (slice 5a spec, Save key rule; F §1.6)", () => {
  it("keyForPost keeps the key for the first try and an identical retry, and replaces it when the body changed", () => {
    const d = testDraft();
    const first = keyForPost(d, "aaaa0001");
    expect(first).toMatchObject({ save_key: d.save_key, save_key_fingerprint: "aaaa0001" });
    expect(keyForPost(first, "aaaa0001")).toBe(first); // the same body after an unknown outcome: the same key
    const edited = keyForPost(first, "bbbb0002");
    expect(edited.save_key).not.toBe(d.save_key);
    expect(edited.save_key_fingerprint).toBe("bbbb0002");
  });

  it("settlePost replaces the key after any answer, and keeps it while the outcome is unknown", () => {
    const sent = keyForPost(testDraft(), "aaaa0001");
    const answered = (outcome: Parameters<typeof settlePost>[1]) => settlePost(sent, outcome);
    for (const outcome of ["success", "client_error"] as const) {
      expect(answered(outcome).save_key).not.toBe(sent.save_key);
      expect(answered(outcome).save_key_fingerprint).toBeNull();
    }
    expect(answered("uncertain")).toBe(sent);
    // What each failure counts as: every 4xx but a 429 is an answer; the rest are unknown.
    for (const [status, code] of [[400, "bad_request"], [404, "not_found"], [422, "invalid_request"], [422, "idempotency_mismatch"]] as const) {
      expect(settleOutcome(new ApiError(status, code, "x")), code).toBe("client_error");
    }
    for (const e of [new ApiError(0, "network_error", "x"), new ApiError(0, "timeout", "x"), new ApiError(0, "aborted", "x"),
      new ApiError(500, "internal_error", "x"), new ApiError(503, "db_unavailable", "x"), new ApiError(429, "rate_limited", "x")]) {
      expect(settleOutcome(e), e.code).toBe("uncertain");
    }
  });
});
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
    expect(DRAFT_VERSION).toBe(1);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 1,
````

**with:**

````ts
    expect(DRAFT_VERSION).toBe(2);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 2,
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
      editing: null,
````

**with:**

````ts
      save_key_fingerprint: null,
      editing: null,
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````ts
      { ...d, version: 2 },
````

**with:**

````ts
      { ...d, version: 3 },
      { ...d, editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00" } }, // version 2 needs editing.date_iso
      { ...d, editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-02-30" } },
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
      ["editing", testDraft((d) => ({ ...d, editing: { service_id: "s1", saved_at: "2026-09-29T16:00:00Z" } }))],
````

**with:**

````ts
      ["editing", testDraft((d) => ({ ...d, editing: { service_id: "s1", saved_at: "2026-09-29T16:00:00Z", date_iso: "2026-10-04" } }))],
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 2 }), JSON.stringify({ version: 1 })]) {
````

**with:**

````ts
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 3 }), JSON.stringify({ version: 1 })]) {
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
    const raw = JSON.stringify({ ...testDraft(), version: 2 });
````

**with:**

````ts
    const raw = JSON.stringify({ ...testDraft(), version: 3 });
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````ts
  it("switches to memory-only when a write fails, and reports it once", () => {
````

**with:**

````ts
  it("replace writes at once, so a page that mounts next reads it (slice 5a-3: Services opens the builder)", () => {
    const { storage, data } = memoryStorage();
    const { store } = makeStore(storage);
    const next = { ...testDraft(), editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-10-04" } };
    store.replace(next);
    expect(stored(data)).toMatchObject({ editing: next.editing, save_key: next.save_key }); // no timer run
    expect(makeStore(storage).store.getSnapshot().draft.editing).toEqual(next.editing);
  });

  it("switches to memory-only when a write fails, and reports it once", () => {
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft/save-key.test.ts src/lib/draft/migrate.test.ts src/lib/draft/schema.test.ts src/lib/draft/store.test.ts src/lib/draft/status.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")
```

**Expected:** five failures and `save-key.test.ts` cannot load (`./save-key` does not exist yet):
```
   × draft migrate and parseStoredDraft (F §4.6 Versioning) > round-trips a stored draft <t>ms
   × draft migrate and parseStoredDraft (F §4.6 Versioning) > migrates a version 1 draft: editing gains the draft's date, and save_key_fingerprint starts null (slice 5a-3) <t>ms
   × DraftStore changes (S store.ts) > replace writes at once, so a page that mounts next reads it (slice 5a-3: Services opens the builder) <t>ms
   × draft schema and freshDraft (F §4.6) > a fresh draft is dated next Sunday with every field empty and the F §4.6 defaults <t>ms
   × draft schema and freshDraft (F §4.6) > accepts an empty date and generous strings, and rejects impossible values <t>ms
 FAIL  |unit| src/lib/draft/save-key.test.ts [ src/lib/draft/save-key.test.ts ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 5 ⎯⎯⎯⎯⎯⎯⎯
      Tests  5 failed | 33 passed (38)
```

- [ ] **Step 3 (agent): Version 2, its migration, the save key, `replace` writes at once**

**In `frontend/src/lib/draft/migrate.ts`, replace:**

````ts
import { DRAFT_VERSION, draftV1Schema, type DraftV1 } from "./schema";
````

**with:**

````ts
import { isValidDateIso } from "@/lib/dates";

import { DRAFT_VERSION, draftV1Schema, type DraftV1 } from "./schema";
````

**In `frontend/src/lib/draft/migrate.ts`, replace:**

````ts
/** `migrations[v]` upgrades version v to v + 1. Empty at version 1; slice 5a adds `1`. */
export const migrations: Readonly<Record<number, Migration>> = {};
````

**with:**

````ts
/**
 * `migrations[v]` upgrades version v to v + 1.
 *
 * 1 → 2 (slice 5a-3; F §4.6): `editing`, when set, gains `date_iso`, the
 * draft's own date (null when that is not a real date); `save_key_fingerprint`
 * starts null. No version 1 draft has `editing` set: nothing could save before
 * 5a-3.
 */
export const migrations: Readonly<Record<number, Migration>> = {
  1: (draft) => {
    const readings = isRecord(draft.readings) ? draft.readings : {};
    const date = typeof readings.date_iso === "string" && isValidDateIso(readings.date_iso) ? readings.date_iso : null;
    const editing = isRecord(draft.editing) ? { ...draft.editing, date_iso: date } : null;
    return { ...draft, editing, save_key_fingerprint: null };
  },
};
````

**Create `frontend/src/lib/draft/save-key.ts`:**

````ts
/**
 * The `Idempotency-Key` of a `POST /services` (slice 5a spec, "Save key rule";
 * F §1.6 "Frontend key rule"). Pure. The key lives in the draft, so it
 * survives a refresh: `save_key`, plus `save_key_fingerprint`, the
 * fingerprint of the payload last posted with it whose outcome is unknown.
 *
 * - `keyForPost(d, fp)` before each POST: a pending fingerprint that differs
 *   from `fp` means the uncertain attempt carried another body, so the key is
 *   replaced; then the fingerprint is recorded. An identical retry keeps the
 *   key, and the server replays its stored answer.
 * - `settlePost(d, outcome)` after it: a 2xx or a 4xx (other than a 429) is a
 *   definitive answer the server may have stored under the key, so the key is
 *   replaced and the fingerprint cleared; an unknown outcome (network error,
 *   timeout, cancel, 5xx, 429; `settleOutcome` in `lib/idempotency.ts`) keeps
 *   both. A PUT never uses the key.
 */
import type { SettleOutcome } from "@/lib/idempotency";

import type { DraftV1 } from "./schema";

export function keyForPost(d: DraftV1, fp: string): DraftV1 {
  if (d.save_key_fingerprint === fp) return d;
  const rotate = d.save_key_fingerprint !== null;
  return { ...d, save_key: rotate ? crypto.randomUUID() : d.save_key, save_key_fingerprint: fp };
}

export function settlePost(d: DraftV1, outcome: SettleOutcome): DraftV1 {
  if (outcome === "uncertain") return d;
  return { ...d, save_key: crypto.randomUUID(), save_key_fingerprint: null };
}
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
 * The per-church unsaved draft, version 1 (F §4.6; S "Draft store").
 *
 * This is F §4.6's `DraftV1` without the two fields slice 5a adds with its own
 * version bump (`save_key_fingerprint`, `editing.date_iso`). Strings are
````

**with:**

````ts
 * The per-church unsaved draft, version 2 (F §4.6; S "Draft store").
 *
 * This is F §4.6's draft shape. Version 2 (slice 5a-3) added the two fields
 * slice 5a brings with its own version bump: `editing.date_iso` (the saved
 * service's date; null for an undated saved service) and
 * `save_key_fingerprint` (`save-key.ts`). The names `DraftV1` and
 * `draftV1Schema` stay, so no importer changes. Strings are
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
export const DRAFT_VERSION = 1;
````

**with:**

````ts
export const DRAFT_VERSION = 2;
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
  editing: z.object({ service_id: text, saved_at: text }).nullable(),
````

**with:**

````ts
  save_key_fingerprint: text.nullable(),
  editing: z.object({ service_id: text, saved_at: text, date_iso: dateIso.nullable() }).nullable(),
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
 * first Sunday, a new save key, on step 1.
````

**with:**

````ts
 * first Sunday, a new save key with no pending fingerprint, on step 1.
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````ts
    editing: null,
````

**with:**

````ts
    save_key_fingerprint: null,
    editing: null,
````

**In `frontend/src/lib/draft/store.ts`, replace:**

````ts
 *   never bumps `updated_at`. `replace(next)` stores `normalizePicks(next)`.
````

**with:**

````ts
 *   never bumps `updated_at`. `replace(next)` stores `normalizePicks(next)`
 *   and writes it at once (slice 5a-3).
````

**In `frontend/src/lib/draft/store.ts`, replace:**

````ts
  replace = (next: DraftV1): void => {
    this.set(this.withDefaults(normalizePicks({ ...next, updated_at: this.now().toISOString() })));
    this.schedule();
````

**with:**

````ts
  /**
   * New service, an opened saved service, a reset after a delete: written at
   * once, not 400 ms later (slice 5a-3). The Services page has its own
   * provider, and the builder it opens reads the stored draft when it mounts,
   * before that page unmounts and flushes.
   */
  replace = (next: DraftV1): void => {
    this.set(this.withDefaults(normalizePicks({ ...next, updated_at: this.now().toISOString() })));
    this.schedule();
    this.flush();
````

- [ ] **Step 4 (agent): Run the files, the suite, the types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft/save-key.test.ts src/lib/draft/migrate.test.ts src/lib/draft/schema.test.ts src/lib/draft/store.test.ts src/lib/draft/status.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `      Tests  40 passed (40)`; ` Test Files  82 passed (82)` and `      Tests  622 passed (622)` with no `×` or `FAIL` line; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/lib/draft/save-key.ts frontend/src/lib/draft/save-key.test.ts frontend/src/lib/draft/schema.ts frontend/src/lib/draft/migrate.ts frontend/src/lib/draft/store.ts frontend/src/lib/draft/schema.test.ts frontend/src/lib/draft/migrate.test.ts frontend/src/lib/draft/store.test.ts frontend/src/lib/draft/status.test.ts
git commit -q -m "Draft version 2: the saved service's date and the save key (5a-3; F 4.6, 1.6)" -m "The draft gains editing.date_iso and save_key_fingerprint (DRAFT_VERSION
2, with a tested migration from 1: editing gains the draft's date, the
fingerprint starts null). lib/draft/save-key.ts keeps the POST /services
key for an identical retry after an unknown outcome and replaces it after
any answer or a changed body. The store writes a replaced draft at once,
so the Services page can open the builder on it." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 1: frontend **622 in 82**; backend **1335 passed, 16 skipped** (unchanged).

### Task 2: The final mapping, `serviceToDraft`, `markSaved`, and the Review statuses (owner answers 4, 5, 9; S "mapping.ts", `status.ts`, "Step status and summary panel"; F §4.6, §4.7; clarifications 3, 6, 7, 8, 17, 19)

**Files:**
- Modify: `frontend/src/lib/draft/mapping.ts` (**Create**: T2 rewrites it whole), `frontend/src/lib/draft/status.ts`, `frontend/src/lib/draft/steps.ts`, `frontend/src/lib/draft/fingerprint.ts`, `frontend/src/lib/draft/readings.ts`, `frontend/src/lib/api/types.ts`, `frontend/src/components/builder/step-progress.tsx`, `frontend/src/components/builder/new-service-menu-item.tsx`, `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/draft/mapping.test.ts`, `frontend/src/lib/draft/status.test.ts`, `frontend/src/lib/draft/fingerprint.test.ts`

- [ ] **Step 1 (agent): Write the failing tests and the fixtures**

The fixtures gain a saved service as `GET /services/{id}` returns it (`savedService`: October 4, GG2013 #1 as the Opening hymn, an empty Response slot, a Closing hymn no longer in the hymnal, two sections, communion, an Anthem), one list row (`serviceSummary`) and a page (`servicePage`); `fingerprint.test.ts` imports `isDirty` from its new home.

**In `frontend/src/lib/draft/fingerprint.test.ts`, replace:**

````ts
import { fingerprint, fnv1a32, isDirty, stableStringify } from "./fingerprint";
import { draftToServicePayload } from "./mapping";
import { editOccasion } from "./readings";
import type { DraftV1 } from "./schema";
````

**with:**

````ts
import { fingerprint, fnv1a32, stableStringify } from "./fingerprint";
import { draftToServicePayload } from "./mapping";
import { editOccasion } from "./readings";
import type { DraftV1 } from "./schema";
import { isDirty } from "./status";
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````ts
import { lectionary, testDraft } from "@/test/fixtures";

import { draftToServicePayload } from "./mapping";
import { applyReadingSet, editScriptureLines, setPick } from "./readings";
import type { DraftV1 } from "./schema";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

describe("draftToServicePayload (provisional; 5a replaces it)", () => {
````

**with:**

````ts
import { churchProfile, hymnId, lectionary, savedService, SERVICE_ID, testDraft, USER_ID } from "@/test/fixtures";

import { fingerprint } from "./fingerprint";
import { draftToServicePayload, markSaved, serviceToDraft } from "./mapping";
import { applyReadingSet, editScriptureLines, setPick, showAvailableBanner } from "./readings";
import type { DraftV1 } from "./schema";
import { isDirty, reviewStatus, saveMode, stillNeeded } from "./status";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";
import { editCardText, setCommunion } from "@/lib/liturgy/cards";

const OPEN_AT = new Date(Date.UTC(2026, 9, 2, 13, 0)); // Friday, October 2, 2026
const opened = (service = savedService()) =>
  serviceToDraft(service, { church: churchProfile(), user: { id: USER_ID }, now: OPEN_AT });

describe("draftToServicePayload (slice 5a-3)", () => {
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````ts
  });
});

````

**with:**

````ts
  });

  it("trims every text as the server does and leaves out a custom element without a label", () => {
    let d = { ...testDraft(), readings: { ...testDraft().readings, occasion: "  Harvest " } };
    d = editCardText(d, "call_to_worship", "  Come, let us worship.\n");
    d = { ...d, liturgy: { ...d.liturgy, sermon_title: " Living Water ", custom_elements: [
      { id: "a", label: " Anthem ", text: " Choir\n", insert_after: "sermon" },
      { id: "b", label: "   ", text: "No label", insert_after: "end" },
    ] } };
    expect(draftToServicePayload(d)).toMatchObject({
      occasion: "Harvest",
      liturgy: { call_to_worship: "Come, let us worship." },
      sermon_title: "Living Water",
      custom_elements: [{ label: "Anthem", text: "Choir", insert_after: "sermon" }],
    });
  });
});

describe("serviceToDraft and markSaved (slice 5a-3; F §4.6 Loading an archived service)", () => {
  it("opens a saved service as a new draft that is already Saved, on Review, for that date", () => {
    const d = opened();
    expect(d).toMatchObject({
      version: 2,
      user_id: USER_ID,
      church_id: churchProfile().id,
      created_at: OPEN_AT.toISOString(),
      last_step: "review",
      save_key_fingerprint: null,
      editing: { service_id: SERVICE_ID, saved_at: "2026-10-01T14:42:00.123456+00:00", date_iso: "2026-10-04" },
      readings: {
        date_iso: "2026-10-04",
        date_origin: "archive",
        reading_set: null,
        fields_origin: "archive",
        occasion: "World Communion Sunday",
        scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
        selected_ot_ref: "",
        selected_nt_ref: "Matthew 21:33-46",
        translation: null,
      },
      hymns: {
        hymnal: "GG2013",
        exclude_recent: true,
        alternatives: null,
        slots: {
          opening: { hymn_id: hymnId(1), title: "Holy, Holy, Holy! Lord God Almighty", number: 1, hymnal: "GG2013" },
          response: null,
          closing: { hymn_id: null, title: "Old Favorite", number: 12, hymnal: "PH1990" }, // not in the hymnal
        },
      },
      liturgy: { sermon_title: "Living Water", include_communion: true, communion_origin: "archive" },
    });
    expect(d.save_key).not.toBe(opened().save_key);
    expect(d.liturgy.cards.call_to_worship).toEqual({ enabled: true, text: "Leader: Come. People: We come.", origin: "archive" });
    expect(d.liturgy.cards.benediction).toEqual({ enabled: true, text: "Go in peace.", origin: "archive" });
    expect(d.liturgy.cards.opening_prayer).toEqual({ enabled: false, text: "", origin: "empty" });
    expect(d.liturgy.custom_elements).toEqual([{ id: expect.any(String), label: "Anthem", text: "Choir", insert_after: "sermon" }]);
    expect(isDirty(d)).toBe(false);
    expect(reviewStatus(d)).toBe("saved");
    expect(saveMode(d)).toBe("update");
    expect(d.saved_fingerprint).toBe(fingerprint(draftToServicePayload(d)));
    expect(stillNeeded(d).filter((item) => item.step === "hymns")).toEqual([
      { step: "hymns", message: "No Response hymn", action: "Choose one" },
      { step: "hymns", message: "Old Favorite isn't in your hymnal", action: "Choose a replacement" },
    ]);
    // Owner answer 5: no "Readings for … are available" while the date is the saved date; it shows on another date.
    const sets = lectionary("2026-10-04", { reading_sets: [{ name: "Other", source: "merged", scriptures: ["Genesis 1:1"] }] });
    expect(showAvailableBanner(d, sets)).toBe(false);
    const moved = { ...d, readings: { ...d.readings, date_iso: "2026-10-11", date_origin: "user" as const } };
    expect(showAvailableBanner(moved, { ...sets, date: "2026-10-11" })).toBe(true);
    expect(showAvailableBanner({ ...moved, readings: { ...moved.readings, date_iso: "2026-10-04" } }, sets)).toBe(false); // back on the saved date
  });

  it("opens an undated service on the next Sunday, keeps every element, and adds no Benediction it lacks", () => {
    const d = opened(
      savedService({
        service_date_iso: null,
        service_date: "",
        liturgy: {},
        custom_elements: [{ label: "Old place", text: "", insert_after: "bogus" as "end" }],
      }),
    );
    expect(d.readings).toMatchObject({ date_iso: "2026-10-04", date_origin: "default", fields_origin: "archive" });
    expect(d.editing?.date_iso).toBeNull();
    expect(saveMode(d)).toBe("copy");
    expect(d.liturgy.cards.benediction).toEqual({ enabled: false, text: "", origin: "empty" }); // no church default added
    expect(d.liturgy.custom_elements[0]).toMatchObject({ label: "Old place", insert_after: "end" });
    expect(isDirty(d)).toBe(false);
  });

  it("markSaved records the save and keeps a default Benediction and communion as saved (owner answer 4)", () => {
    const d = testDraft((base) => ({ ...base, readings: { ...base.readings, occasion: "Harvest" } }));
    expect(d.liturgy.cards.benediction.origin).toBe("default");
    const fp = fingerprint(draftToServicePayload(d));
    const saved = markSaved(d, savedService({ saved_at: "2026-10-02T13:00:00+00:00" }), fp);
    expect(saved.editing).toEqual({ service_id: SERVICE_ID, saved_at: "2026-10-02T13:00:00+00:00", date_iso: "2026-10-04" });
    expect(saved.saved_fingerprint).toBe(fp);
    expect(saved.liturgy.cards.benediction).toEqual({ enabled: true, text: DEFAULT_BENEDICTION_FALLBACK, origin: "archive" });
    expect(saved.liturgy.communion_origin).toBe("archive");
    expect(reviewStatus(saved)).toBe("saved");
    // A blank default Benediction becomes an empty card; communion the user set stays the user's.
    const blank = testDraft((base) => setCommunion({
      ...base,
      liturgy: { ...base.liturgy, cards: { ...base.liturgy.cards, benediction: { enabled: true, text: "", origin: "default" } } },
    }, false));
    const after = markSaved(blank, savedService(), fingerprint(draftToServicePayload(blank)));
    expect(after.liturgy.cards.benediction.origin).toBe("empty");
    expect(after.liturgy.communion_origin).toBe("user");
  });
});

````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts

import {
  applyReadingSet,
````

**with:**

````ts

import { fingerprint } from "./fingerprint";
import { draftToServicePayload } from "./mapping";
import {
  applyReadingSet,
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
import { isPristine, stepStatus, stillNeeded, withoutTranslation } from "./status";
````

**with:**

````ts
import { isDirty, isPristine, reviewStatus, saveMode, stepStatus, stillNeeded, withoutTranslation } from "./status";
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
  it("lists the four steps in order, ships Date & readings (2c), Hymns (3b) and Liturgy (4b), and reads a step from its path", () => {
````

**with:**

````ts
  it("lists the four steps in order, ships all four (2c, 3b, 4b and Review in 5a-3), and reads a step from its path", () => {
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
    expect([...SHIPPED_STEPS]).toEqual(["readings", "hymns", "liturgy"]);
````

**with:**

````ts
    expect([...SHIPPED_STEPS]).toEqual(["readings", "hymns", "liturgy", "review"]);
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
  it("counts the hymns step n of 3 and lists each empty slot once it ships (slice 3b)", () => {
````

**with:**

````ts
  it("counts the hymns step n of 3 and lists each empty slot (slice 3b) and a hymn not in the hymnal (5a-3)", () => {
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
    expect(stillNeeded(all, hymnsShipped)).toEqual([]);
````

**with:**

````ts
    expect(stillNeeded(all, hymnsShipped)).toEqual([
      { step: "hymns", message: "Amazing Grace isn't in your hymnal", action: "Choose a replacement" },
    ]);
    expect(stillNeeded(withSlots({ opening: HYMN, response: HYMN, closing: HYMN }), hymnsShipped)).toEqual([]);
````

**In `frontend/src/lib/draft/status.test.ts`, replace:**

````ts
    expect(stillNeeded(titled).some((item) => item.message === "No sermon title")).toBe(false);
  });
});

````

**with:**

````ts
    expect(stillNeeded(titled).some((item) => item.message === "No sermon title")).toBe(false);
  });
});

describe("the archive status and what Save does (slice 5a-3; S status.ts)", () => {
  const saved = (d: DraftV1, dateIso: string | null = d.readings.date_iso): DraftV1 => ({
    ...d,
    editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: dateIso },
    saved_fingerprint: fingerprint(draftToServicePayload(d)),
  });

  it("reviewStatus is not in the archive, saved, or changed since; the step bar shows it once Review ships", () => {
    const fresh = testDraft();
    expect(reviewStatus(fresh)).toBe("not_in_archive");
    expect(reviewStatus(editOccasion(fresh, "Harvest"))).toBe("not_in_archive"); // never saved
    const clean = saved(editOccasion(fresh, "Harvest"));
    expect(reviewStatus(clean)).toBe("saved");
    expect(isDirty(clean)).toBe(false);
    expect(reviewStatus(editOccasion(clean, "Harvest Home"))).toBe("unsaved_changes");
    expect(reviewStatus(editOccasion(clean, "Harvest  "))).toBe("saved"); // trimmed as the server trims it
    expect(stepStatus(clean, "review")).toEqual({ kind: "saved" });
    expect(stepStatus(editOccasion(clean, "Harvest Home"), "review")).toEqual({ kind: "unsaved_changes" });
    expect(stepStatus(fresh, "review")).toEqual({ kind: "not_in_archive" });
    expect(stepStatus(clean, "review", READINGS)).toEqual({ kind: "not_in_archive" }); // before 5a-3
  });

  it("saveMode saves new, saves changes on the saved date, and saves a copy on another date or for an undated service", () => {
    const d = testDraft();
    expect(saveMode(d)).toBe("new");
    expect(saveMode(saved(d))).toBe("update");
    expect(saveMode(setDate(saved(d), "2026-10-11"))).toBe("copy");
    expect(saveMode(saved(d, null))).toBe("copy"); // a saved service with no date
  });
});

````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  SuggestedHymn,
````

**with:**

````ts
  ServiceOut,
  ServicePage,
  ServiceSummary,
  SuggestedHymn,
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  return async (req: { body: unknown }) => answer(req.body as ReviseBody);
}

````

**with:**

````ts
  return async (req: { body: unknown }) => answer(req.body as ReviseBody);
}

// --- slice 5a-3: saved services ---------------------------------------------------

export const SERVICE_ID = "55555555-5555-4555-8555-555555555555";

/**
 * `GET /services/{id}` (`ServiceOut`, slice 5a-2): Grace's October 4, 2026
 * service as Pat saved it on October 1 at 14:42 UTC: the Isaiah readings with
 * the Gospel picked, GG2013 #1 as the Opening hymn, an empty Response slot, a
 * Closing hymn no longer in the hymnal, two sections, communion, a sermon
 * title and an Anthem after the sermon.
 */
export function savedService(overrides: Partial<ServiceOut> = {}): ServiceOut {
  return {
    id: SERVICE_ID,
    service_date_iso: "2026-10-04",
    service_date: "October 04, 2026",
    occasion: "World Communion Sunday",
    scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
    hymns: {
      opening: { hymn_id: hymnId(1), title: "Holy, Holy, Holy! Lord God Almighty", number: 1, hymnal: "GG2013", in_hymnal: true },
      response: null,
      closing: { hymn_id: null, title: "Old Favorite", number: 12, hymnal: "PH1990", in_hymnal: false },
    },
    hymnal: "GG2013",
    liturgy: { call_to_worship: "Leader: Come. People: We come.", benediction: "Go in peace." },
    sermon_title: "Living Water",
    selected_ot_ref: "",
    selected_nt_ref: "Matthew 21:33-46",
    include_communion: true,
    custom_elements: [{ label: "Anthem", text: "Choir", insert_after: "sermon" }],
    created_by: { id: USER_ID, name: "Pat Pastor" },
    saved_at: "2026-10-01T14:42:00.123456+00:00",
    ...overrides,
  };
}

/** One row of `GET /services` (`ServiceSummary`): `savedService()`'s, unless overridden. */
export function serviceSummary(overrides: Partial<ServiceSummary> = {}): ServiceSummary {
  const s = savedService();
  return {
    id: s.id,
    service_date_iso: s.service_date_iso,
    service_date: s.service_date,
    occasion: s.occasion,
    sermon_title: s.sermon_title,
    saved_at: s.saved_at,
    created_by: s.created_by,
    ...overrides,
  };
}

/** A page of `GET /services`. */
export function servicePage(items: ServiceSummary[], overrides: Partial<ServicePage> = {}): ServicePage {
  return { items, total: items.length, limit: 20, offset: 0, ...overrides };
}

````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft/mapping.test.ts src/lib/draft/status.test.ts src/lib/draft/fingerprint.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")
```

**Expected:** eleven failures (`isDirty`, `serviceToDraft`, `markSaved`, `reviewStatus` and `saveMode` are not where the tests import them yet; Review is not shipped; no hymnal row; the payload is not trimmed):
```
   × fingerprint and isDirty (F §4.6 Unsaved changes) > isDirty: never saved means not pristine; saved means the payload changed <t>ms
   × fingerprint and isDirty (F §4.6 Unsaved changes) > after a save, a slot or hymnal change is unsaved; the Exclude switch and other ideas are not (owner answer 1) <t>ms
   × fingerprint and isDirty (F §4.6 Unsaved changes) > after a save, liturgy that prints is unsaved; a switch on an empty card is not (owner answer 1, 2026-09-30) <t>ms
   × draftToServicePayload (slice 5a-3) > trims every text as the server does and leaves out a custom element without a label <t>ms
   × serviceToDraft and markSaved (slice 5a-3; F §4.6 Loading an archived service) > opens a saved service as a new draft that is already Saved, on Review, for that date <t>ms
   × serviceToDraft and markSaved (slice 5a-3; F §4.6 Loading an archived service) > opens an undated service on the next Sunday, keeps every element, and adds no Benediction it lacks <t>ms
   × serviceToDraft and markSaved (slice 5a-3; F §4.6 Loading an archived service) > markSaved records the save and keeps a default Benediction and communion as saved (owner answer 4) <t>ms
   × steps (S steps.ts) > lists the four steps in order, ships all four (2c, 3b, 4b and Review in 5a-3), and reads a step from its path <t>ms
   × stillNeeded (S Review "Still needed") > counts the hymns step n of 3 and lists each empty slot (slice 3b) and a hymn not in the hymnal (5a-3) <t>ms
   × the archive status and what Save does (slice 5a-3; S status.ts) > reviewStatus is not in the archive, saved, or changed since; the step bar shows it once Review ships <t>ms
   × the archive status and what Save does (slice 5a-3; S status.ts) > saveMode saves new, saves changes on the saved date, and saves a copy on another date or for an undated service <t>ms
⎯⎯⎯⎯⎯⎯ Failed Tests 11 ⎯⎯⎯⎯⎯⎯⎯
      Tests  11 failed | 14 passed (25)
```

- [ ] **Step 3 (agent): The mapping, the statuses, Review shipped, the readings banner**

**In `frontend/src/components/builder/new-service-menu-item.tsx`, replace:**

````tsx
import { isDirty } from "@/lib/draft/fingerprint";
import { freshDraft, type DraftChurch } from "@/lib/draft/schema";
import { withoutTranslation } from "@/lib/draft/status";
````

**with:**

````tsx
import { freshDraft, type DraftChurch } from "@/lib/draft/schema";
import { isDirty, withoutTranslation } from "@/lib/draft/status";
````

**In `frontend/src/components/builder/step-progress.tsx`, replace:**

````tsx
      return "Not in archive";
  }
````

**with:**

````tsx
      return "Not in archive";
    case "saved":
      return "Saved";
    case "unsaved_changes":
      return "Unsaved changes";
  }
````

**In `frontend/src/components/builder/step-progress.tsx`, replace:**

````tsx
                    status.kind === "complete" && "bg-primary/60",
````

**with:**

````tsx
                    (status.kind === "complete" || status.kind === "saved") && "bg-primary/60",
````

**In `frontend/src/components/builder/step-progress.tsx`, replace:**

````tsx
                  {status.kind === "complete" ? <CheckIcon aria-hidden="true" className="size-3" /> : null}
````

**with:**

````tsx
                  {status.kind === "complete" || status.kind === "saved" ? <CheckIcon aria-hidden="true" className="size-3" /> : null}
````

**In `frontend/src/lib/api/types.ts`, replace:**

````ts
/** `POST /liturgy/review` (the service reviewer): every switched-on card with text, and the notes back. */
````

**with:**

````ts
/**
 * `/services` (slice 5a-2): a saved service as the builder opens it (`GET`,
 * `POST`, `PUT`), one saved slot's hymn, one row of the list, a page of rows,
 * and the answer to a delete.
 */
export type ServiceOut = components["schemas"]["ServiceOut"];
export type ArchivedHymn = components["schemas"]["ArchivedHymn"];
export type ServiceSummary = components["schemas"]["ServiceSummary"];
export type ServicePage = components["schemas"]["Page_ServiceSummary_"];
export type DeletedOut = components["schemas"]["DeletedOut"];

/** `POST /liturgy/review` (the service reviewer): every switched-on card with text, and the notes back. */
````

**In `frontend/src/lib/draft/fingerprint.ts`, replace:**

````ts
 * Unsaved-changes detection (F §4.6 "Unsaved changes"; S "fingerprint.ts").
 * `fingerprint` is 32-bit FNV-1a over the UTF-8 bytes of a stable JSON
 * string (object keys sorted at every level), as 8 hex digits.
 */
import { draftToServicePayload } from "./mapping";
import type { DraftV1 } from "./schema";
import { isPristine } from "./status";
````

**with:**

````ts
 * The fingerprint behind unsaved-changes detection (F §4.6 "Unsaved changes";
 * S "fingerprint.ts"): 32-bit FNV-1a over the UTF-8 bytes of a stable JSON
 * string (object keys sorted at every level), as 8 hex digits. `isDirty`,
 * which compares it, is in `status.ts` (slice 5a-3), beside the Review
 * statuses that read it.
 */
````

**In `frontend/src/lib/draft/fingerprint.ts`, replace:**

````ts

/** Never saved: dirty means not pristine. Saved or loaded: the payload differs from what was saved. */
export function isDirty(draft: DraftV1): boolean {
  if (draft.saved_fingerprint === null) return !isPristine(draft);
  return fingerprint(draftToServicePayload(draft)) !== draft.saved_fingerprint;
}

````

**with:**

````ts

````

**Create `frontend/src/lib/draft/mapping.ts`:**

````ts
/**
 * Draft ↔ saved service (slice 5a spec, Frontend "mapping.ts"; F §4.6 "Draft
 * → API payload" and "Loading an archived service").
 *
 * - `draftToServicePayload(draft)`: the service as the draft holds it, in the
 *   `ServiceDraft` shape, from the draft alone (so a church setting never
 *   makes a draft look unsaved). The fingerprint behind "Unsaved changes"
 *   hashes it. Text is trimmed as the server trims it; the picks are
 *   `resolveReadings`' explicit values, so a pick that is no longer an option
 *   goes as "". The bodies sent to the server (`serviceBody`, `documents.ts`)
 *   start from it and keep it within the server's limits.
 * - `serviceToDraft(service, …)`: a saved service as a new draft, already
 *   "Saved" (its fingerprint stored), on Review, with a new `created_at`.
 * - `markSaved(draft, service, fp)`: the draft after a save (owner answer 4).
 */
import type { ArchivedHymn, ServiceOut } from "@/lib/api/types";
import { isValidDateIso } from "@/lib/dates";
import { normalizePlacement } from "@/lib/liturgy/cards";
import { cleanLines } from "@/lib/scripture-refs";

import { fingerprint } from "./fingerprint";
import { effectivePicks } from "./readings";
import {
  freshDraft,
  SECTION_KEYS,
  SLOTS,
  type DraftChurch,
  type DraftV1,
  type HymnPick,
  type LiturgyCard,
  type SectionKey,
  type Slot,
} from "./schema";

/** Inventory §2.1's `HymnRef`. */
export type HymnRefPayload = { hymn_id: string | null; title: string; number: number | null; hymnal: string | null };

/** The API's `ServiceDraft` (inventory §2.1 plus `hymnal`, F §1.3), every field present. */
export type ServiceDraftPayload = {
  service_date_iso: string;
  occasion: string;
  scriptures: string[];
  hymns: Record<Slot, HymnRefPayload | null>;
  liturgy: Partial<Record<SectionKey, string>>;
  sermon_title: string;
  selected_ot_ref: string;
  selected_nt_ref: string;
  include_communion: boolean;
  custom_elements: { label: string; text: string; insert_after: string }[];
  hymnal: string | null;
};

function hymnRef(pick: HymnPick | null): HymnRefPayload | null {
  return pick ? { hymn_id: pick.hymn_id, title: pick.title, number: pick.number, hymnal: pick.hymnal } : null;
}

/**
 * The draft as a `ServiceDraft` (S "mapping.ts"): the date; the occasion
 * trimmed; the scripture lines trimmed with blanks dropped; the explicit
 * picks; the slot hymns; `hymnal` as the draft holds it (null = the church's
 * effective hymnal, filled in by the server); the switched-on cards with
 * text, trimmed; the sermon title trimmed; communion; the custom elements
 * with a label, trimmed, without their ids.
 */
export function draftToServicePayload(draft: DraftV1): ServiceDraftPayload {
  const picks = effectivePicks(draft);
  const liturgy: Partial<Record<SectionKey, string>> = {};
  for (const key of SECTION_KEYS) {
    const card = draft.liturgy.cards[key];
    const text = card.text.trim();
    if (card.enabled && text !== "") liturgy[key] = text;
  }
  return {
    service_date_iso: draft.readings.date_iso,
    occasion: draft.readings.occasion.trim(),
    scriptures: cleanLines(draft.readings.scriptures),
    hymns: Object.fromEntries(SLOTS.map((slot) => [slot, hymnRef(draft.hymns.slots[slot])])) as Record<
      Slot,
      HymnRefPayload | null
    >,
    liturgy,
    sermon_title: draft.liturgy.sermon_title.trim(),
    selected_ot_ref: picks.otAuto ? "" : (picks.ot ?? ""),
    selected_nt_ref: picks.ntAuto ? "" : (picks.nt ?? ""),
    include_communion: draft.liturgy.include_communion,
    custom_elements: draft.liturgy.custom_elements
      .filter((element) => element.label.trim() !== "")
      .map(({ label, text, insert_after }) => ({ label: label.trim(), text: text.trim(), insert_after })),
    hymnal: draft.hymns.hymnal,
  };
}

/** A saved slot as a pick: a hymn that is no longer in the hymnal keeps its title with no id ("Not in your hymnal"). */
function pickFromArchived(hymn: ArchivedHymn | null): HymnPick | null {
  if (hymn === null) return null;
  return { hymn_id: hymn.in_hymnal ? hymn.hymn_id : null, title: hymn.title, number: hymn.number, hymnal: hymn.hymnal };
}

/**
 * A saved service as the new draft (S `serviceToDraft`; F §4.6 "Loading an
 * archived service"): the readings from the service (`fields_origin`
 * "archive", so the lectionary never fills over them; no reading set; the
 * church's translation), dated as saved (`date_origin` "archive"), or, for an
 * undated service, the next Sunday (`date_origin` "default"); the slot hymns
 * and the hymnal as saved; each saved section switched on with its text
 * (origin "archive") and the others off and empty (no church Benediction
 * added); the sermon title; communion as saved (origin "archive"); the custom
 * elements with new ids and their places read as the Liturgy step reads
 * them. `editing` names the service, its `saved_at` and its date; the
 * fingerprint of this draft is stored, so it opens "Saved"; a new save key;
 * a new `created_at` (the reviewer's notes and any AI run belong to the
 * draft it replaces); on Review.
 */
export function serviceToDraft(
  service: ServiceOut,
  { church, user, now = new Date() }: { church: DraftChurch; user: { id: string }; now?: Date },
): DraftV1 {
  const fresh = freshDraft({ church, user, now });
  const date = service.service_date_iso !== null && isValidDateIso(service.service_date_iso) ? service.service_date_iso : null;
  const cards = Object.fromEntries(
    SECTION_KEYS.map((key): [SectionKey, LiturgyCard] => {
      const text = service.liturgy[key] ?? "";
      return [key, text.trim() === "" ? { enabled: false, text: "", origin: "empty" } : { enabled: true, text, origin: "archive" }];
    }),
  ) as Record<SectionKey, LiturgyCard>;
  const draft: DraftV1 = {
    ...fresh,
    last_step: "review",
    editing: { service_id: service.id, saved_at: service.saved_at, date_iso: date },
    readings: {
      date_iso: date ?? fresh.readings.date_iso,
      date_origin: date === null ? "default" : "archive",
      reading_set: null,
      fields_origin: "archive",
      occasion: service.occasion,
      scriptures: [...service.scriptures],
      selected_ot_ref: service.selected_ot_ref,
      selected_nt_ref: service.selected_nt_ref,
      translation: null,
    },
    hymns: {
      hymnal: service.hymnal ?? null,
      exclude_recent: true,
      slots: {
        opening: pickFromArchived(service.hymns.opening),
        response: pickFromArchived(service.hymns.response),
        closing: pickFromArchived(service.hymns.closing),
      },
      alternatives: null,
    },
    liturgy: {
      sermon_title: service.sermon_title,
      include_communion: service.include_communion,
      communion_origin: "archive",
      cards,
      custom_elements: service.custom_elements.map((element) => ({
        id: crypto.randomUUID(),
        label: element.label,
        text: element.text,
        insert_after: normalizePlacement(element.insert_after),
      })),
    },
  };
  return { ...draft, saved_fingerprint: fingerprint(draftToServicePayload(draft)) };
}

/**
 * The draft after a save: `editing` names the saved service (its id,
 * `saved_at` and date), `saved_fingerprint` is the payload that was sent, and
 * what followed a default is now the service's own, as when a saved service
 * is opened (owner answer 4): a Benediction following the church default
 * keeps its text with origin "archive" ("empty" when it is blank), and
 * communion following the first-Sunday rule keeps its setting with origin
 * "archive". Neither changes the payload, so the draft is "Saved".
 */
export function markSaved(d: DraftV1, service: ServiceOut, fp: string): DraftV1 {
  const benediction = d.liturgy.cards.benediction;
  const cards =
    benediction.origin === "default"
      ? { ...d.liturgy.cards, benediction: { ...benediction, origin: benediction.text.trim() === "" ? ("empty" as const) : ("archive" as const) } }
      : d.liturgy.cards;
  const communion_origin = d.liturgy.communion_origin === "default" ? "archive" : d.liturgy.communion_origin;
  return {
    ...d,
    editing: { service_id: service.id, saved_at: service.saved_at, date_iso: service.service_date_iso },
    saved_fingerprint: fp,
    liturgy: { ...d.liturgy, cards, communion_origin },
  };
}
````

**In `frontend/src/lib/draft/readings.ts`, replace:**

````ts
 * this date's lectionary, or archived fields whose date has changed.
 */
export function showAvailableBanner(d: DraftV1, lect: Lectionary | undefined): boolean {
  if (!lect || lect.date !== d.readings.date_iso || lect.reading_sets.length === 0) return false;
````

**with:**

````ts
 * this date's lectionary, or archived fields whose date has changed. Never
 * while the date is still the saved service's date (owner answer 5,
 * 2026-10-01): the service's readings are what was saved for that date.
 */
export function showAvailableBanner(d: DraftV1, lect: Lectionary | undefined): boolean {
  if (!lect || lect.date !== d.readings.date_iso || lect.reading_sets.length === 0) return false;
  if (d.editing !== null && d.editing.date_iso === d.readings.date_iso) return false;
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
 * Step status, "nothing to lose" and "Still needed" (F §4.7; S "status.ts").
 * Pure functions of the draft; the shell decides what an unshipped step shows.
````

**with:**

````ts
 * Step status, "nothing to lose", unsaved changes, the archive status and
 * "Still to do" (F §4.7; S "status.ts"). Pure functions of the draft; the
 * shell decides what an unshipped step shows.
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
import { SECTION_KEYS, SLOTS, type DraftV1, type Slot, type StepId } from "./schema";
import { SHIPPED_STEPS } from "./steps";
````

**with:**

````ts
import { fingerprint } from "./fingerprint";
import { draftToServicePayload } from "./mapping";
import { SECTION_KEYS, SLOTS, type DraftV1, type Slot, type StepId } from "./schema";
import { SHIPPED_STEPS } from "./steps";

/** Review's status (S `reviewStatus`): never saved, saved as it is now, or changed since the last save or open. */
export type ReviewStatus = "not_in_archive" | "saved" | "unsaved_changes";
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
  /** Review before slice 5a (and a draft that was never saved). */
  | { kind: "not_in_archive" };
````

**with:**

````ts
  /** Review: "Not in archive", "Saved" (with the ✓ of a complete step) or "Unsaved changes". */
  | { kind: ReviewStatus };
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
 * have text. Review reads "Not in archive" until 5a adds "Saved" and
 * "Unsaved changes". An unshipped step (other than Review) is "Soon".
````

**with:**

````ts
 * have text. Review is `reviewStatus` once it ships (slice 5a-3), and "Not
 * in archive" before. An unshipped step (other than Review) is "Soon".
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
  if (step === "review") return { kind: "not_in_archive" };
````

**with:**

````ts
  if (step === "review") return { kind: shipped.has("review") ? reviewStatus(draft) : "not_in_archive" };
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts

/**
 * A copy of the draft with the translation override cleared, for the checks
````

**with:**

````ts

/** Never saved: dirty means not pristine. Saved or opened: the payload differs from what was saved (moved here from `fingerprint.ts`, slice 5a-3). */
export function isDirty(draft: DraftV1): boolean {
  if (draft.saved_fingerprint === null) return !isPristine(draft);
  return fingerprint(draftToServicePayload(draft)) !== draft.saved_fingerprint;
}

/**
 * Review's archive status (S `reviewStatus`), shown by the step bar, the
 * summary and the Save card: "not_in_archive" until the draft is saved or
 * opened from the archive, then "saved" or "unsaved_changes".
 */
export function reviewStatus(draft: DraftV1): ReviewStatus {
  if (draft.editing === null) return "not_in_archive";
  return isDirty(draft) ? "unsaved_changes" : "saved";
}

/**
 * What Save does (S `saveMode`): "new" for a draft not in the archive,
 * "update" for a saved service whose date is unchanged, "copy" (Save as new
 * service) when the date differs from the saved one, an undated saved
 * service included (parity: app.py:1029-1035).
 */
export function saveMode(draft: DraftV1): "new" | "update" | "copy" {
  if (draft.editing === null) return "new";
  return draft.readings.date_iso === draft.editing.date_iso ? "update" : "copy";
}

/**
 * A copy of the draft with the translation override cleared, for the checks
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
 * What Review lists under "Still needed", from shipped steps only: the
 * readings' gaps (2c), then one row per empty hymn slot in slot order (3b,
 * F §4.7's wording), then one row per switched-on liturgy card with no text,
 * linking to that card, and "No sermon title" (4b, the wording 5a's Review
 * checklist reuses).
````

**with:**

````ts
 * What Review lists under "Still to do", from shipped steps only: the
 * readings' gaps (2c), then per hymn slot in slot order an empty slot (3b,
 * F §4.7's wording) or a hymn that is not in the hymnal, as an opened saved
 * service can hold (5a-3, S "Review checklist"), then one row per
 * switched-on liturgy card with no text, linking to that card, and "No
 * sermon title" (4b).
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````ts
      if (draft.hymns.slots[slot] !== null) continue;
      items.push({ step: "hymns", message: `No ${SLOT_NAMES[slot]} hymn`, action: "Choose one" });
````

**with:**

````ts
      const pick = draft.hymns.slots[slot];
      if (pick === null) items.push({ step: "hymns", message: `No ${SLOT_NAMES[slot]} hymn`, action: "Choose one" });
      else if (pick.hymn_id === null) {
        items.push({ step: "hymns", message: `${pick.title} isn't in your hymnal`, action: "Choose a replacement" });
      }
````

**In `frontend/src/lib/draft/steps.ts`, replace:**

````ts
 * "liturgy". Review's route has its real content from 5a-1 (Still needed and
 * the Word files); "review" joins the set in 5a-3, when saving gives it the
 * statuses "Saved" and "Unsaved changes".
````

**with:**

````ts
 * "liturgy". Review's route has its real content from 5a-1 (the checklist and
 * the Word files); "review" joins the set in 5a-3, when saving gives it the
 * statuses "Saved" and "Unsaved changes" (`reviewStatus`).
````

**In `frontend/src/lib/draft/steps.ts`, replace:**

````ts
export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns", "liturgy"]);
````

**with:**

````ts
export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns", "liturgy", "review"]);
````

- [ ] **Step 4 (agent): Run the files, the suite, the types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft/mapping.test.ts src/lib/draft/status.test.ts src/lib/draft/fingerprint.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `      Tests  25 passed (25)`; ` Test Files  82 passed (82)` and `      Tests  628 passed (628)` with no `×` or `FAIL` line (the builder shell's Review item still reads "Not in archive" for a fresh draft); `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/lib/draft/mapping.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/steps.ts frontend/src/lib/draft/fingerprint.ts frontend/src/lib/draft/readings.ts frontend/src/lib/api/types.ts frontend/src/components/builder/step-progress.tsx frontend/src/components/builder/new-service-menu-item.tsx frontend/src/test/fixtures/index.ts frontend/src/lib/draft/mapping.test.ts frontend/src/lib/draft/status.test.ts frontend/src/lib/draft/fingerprint.test.ts
git commit -q -m "Draft mapping and statuses: serviceToDraft, markSaved, Saved and Unsaved changes (5a-3; owner answers 4, 5)" -m "draftToServicePayload takes its final form (text trimmed as the server
trims it). serviceToDraft opens a saved service as a new draft that is
already Saved; markSaved records a save and keeps a default Benediction
and communion as saved (owner answer 4). status.ts gains isDirty (moved
from fingerprint.ts), reviewStatus, saveMode and the 'isn't in your
hymnal' row; Review ships, so the step bar shows Saved or Unsaved
changes. No 'Readings for ... are available' while the date is the saved
date (owner answer 5)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 2: frontend **628 in 82**; backend **1335 passed, 16 skipped**.

### Task 3: The archive's queries and the save time (S `lib/queries/services.ts`, `useSaveService`, `useDeleteService`; F §1.6, §1.7, §4.4; clarifications 9-12, 15, 16, 17, 20)

**Files:**
- Create: `frontend/src/lib/queries/services.ts`
- Modify: `frontend/src/lib/dates.ts`, `frontend/src/lib/documents.ts`, `frontend/src/lib/dates.test.ts`

The hooks are exercised end to end by T4's and T5's DOM tests (every outcome in clarifications 9-12, 15 and 16), through the fake API, as the 5a-1 download hook was; this task adds only the pure `formatSavedAt` test.

- [ ] **Step 1 (agent): Write the failing test**

**In `frontend/src/lib/dates.test.ts`, replace:**

````ts
  formatServiceDate,
````

**with:**

````ts
  formatSavedAt,
  formatServiceDate,
````

**In `frontend/src/lib/dates.test.ts`, replace:**

````ts
  it("inSupportedRange accepts years 1900-2199 only", () => {
````

**with:**

````ts
  it("formatSavedAt shows a save time in the viewer's zone, with the year only when it is not this year (slice 5a-3)", () => {
    const now = new Date(Date.UTC(2026, 9, 2, 13, 0));
    expect(formatSavedAt("2026-10-01T14:42:00.123456+00:00", { timeZone: "America/New_York", now })).toBe("Oct 1, 10:42 AM");
    expect(formatSavedAt("2026-10-01T14:42:00+00:00", { timeZone: "UTC", now })).toBe("Oct 1, 2:42 PM");
    expect(formatSavedAt("2025-12-31T23:30:00Z", { timeZone: "America/New_York", now })).toBe("Dec 31, 2025, 6:30 PM");
    expect(formatSavedAt("not a time")).toBe("");
  });

  it("inSupportedRange accepts years 1900-2199 only", () => {
````

- [ ] **Step 2 (agent): Run it and see it fail**

```bash
(cd frontend && npx vitest run src/lib/dates.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")
```

**Expected:**
```
   × lib/dates > formatSavedAt shows a save time in the viewer's zone, with the year only when it is not this year (slice 5a-3) <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
      Tests  1 failed | 8 passed (9)
```

- [ ] **Step 3 (agent): `formatSavedAt`, `serviceBody`, the hooks**

**In `frontend/src/lib/dates.ts`, replace:**

````ts
/** Years 1900–2199: the range the lectionary lookup accepts. */
````

**with:**

````ts
/**
 * When a service was saved (an ISO timestamp from the API, slice 5a-3), in
 * the viewer's time zone: "Oct 1, 10:42 AM", with the year when it is not
 * this year ("Dec 31, 2025, 6:30 PM"); "" for an unreadable value.
 * `timeZone` and `now` are for tests.
 */
export function formatSavedAt(iso: string, { timeZone, now = new Date() }: { timeZone?: string; now?: Date } = {}): string {
  const at = Date.parse(iso);
  if (!Number.isFinite(at)) return "";
  const zone = timeZone === undefined ? {} : { timeZone };
  const year = (t: number) => new Intl.DateTimeFormat("en-US", { year: "numeric", ...zone }).format(t);
  const withYear = year(at) === year(now.getTime()) ? {} : { year: "numeric" as const };
  const options: Intl.DateTimeFormatOptions = { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", ...withYear, ...zone };
  // Newer ICU puts a narrow no-break space before AM/PM; a plain space reads the same everywhere.
  return new Intl.DateTimeFormat("en-US", options).format(at).replace(/\u202f/g, " ");
}

/** Years 1900–2199: the range the lectionary lookup accepts. */
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
 * The service is `draftToServicePayload(draft)` (the provisional mapping the
 * save will share, 5a-3), kept within the `ServiceDraft` limits so a draft
````

**with:**

````ts
 * The service is `draftToServicePayload(draft)` (the mapping the save shares,
 * `serviceBody`, 5a-3), kept within the `ServiceDraft` limits so a draft
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
export function documentRequest(draft: DraftV1, variant: DocumentVariant): DocumentBody {
  const payload = draftToServicePayload(draft);
  const slots = draft.hymns.slots;
  return {
    variant,
    service: {
      ...payload,
      ...readingsContext(draft),
      selected_ot_ref: clipChars(payload.selected_ot_ref.trim(), MAX_REF_LENGTH),
      selected_nt_ref: clipChars(payload.selected_nt_ref.trim(), MAX_REF_LENGTH),
      hymns: { opening: hymnRef(slots.opening), response: hymnRef(slots.response), closing: hymnRef(slots.closing) },
      hymnal: payload.hymnal === null ? null : clipChars(payload.hymnal, MAX_HYMNAL),
      liturgy: Object.fromEntries(Object.entries(payload.liturgy).map(([key, text]) => [key, clipChars(text, MAX_CARD_TEXT)])),
      sermon_title: clipChars(payload.sermon_title.trim(), MAX_SERMON_TITLE),
      custom_elements: payload.custom_elements
        .filter((element) => !isBlankLabel(element.label))
        .slice(0, MAX_CUSTOM_ELEMENTS)
        .map((element) => ({
          label: clipChars(element.label.trim(), MAX_CUSTOM_LABEL),
          text: clipChars(element.text, MAX_CUSTOM_TEXT),
          insert_after: normalizePlacement(element.insert_after) as Placement,
        })),
    },
  };
}

````

**with:**

````ts
/**
 * The service as `POST /documents` and `POST`/`PUT /services` send it (slice
 * 5a-3: the Save card sends the same body as the downloads, so a save never
 * meets a 422 for a length either, a stored custom element longer than
 * today's limits included).
 */
export function serviceBody(draft: DraftV1): DocumentBody["service"] {
  const payload = draftToServicePayload(draft);
  const slots = draft.hymns.slots;
  return {
    ...payload,
    ...readingsContext(draft),
    selected_ot_ref: clipChars(payload.selected_ot_ref.trim(), MAX_REF_LENGTH),
    selected_nt_ref: clipChars(payload.selected_nt_ref.trim(), MAX_REF_LENGTH),
    hymns: { opening: hymnRef(slots.opening), response: hymnRef(slots.response), closing: hymnRef(slots.closing) },
    hymnal: payload.hymnal === null ? null : clipChars(payload.hymnal, MAX_HYMNAL),
    liturgy: Object.fromEntries(Object.entries(payload.liturgy).map(([key, text]) => [key, clipChars(text, MAX_CARD_TEXT)])),
    sermon_title: clipChars(payload.sermon_title.trim(), MAX_SERMON_TITLE),
    custom_elements: payload.custom_elements
      .filter((element) => !isBlankLabel(element.label))
      .slice(0, MAX_CUSTOM_ELEMENTS)
      .map((element) => ({
        label: clipChars(element.label.trim(), MAX_CUSTOM_LABEL),
        text: clipChars(element.text, MAX_CUSTOM_TEXT),
        insert_after: normalizePlacement(element.insert_after) as Placement,
      })),
  };
}

export function documentRequest(draft: DraftV1, variant: DocumentVariant): DocumentBody {
  return { variant, service: serviceBody(draft) };
}

````

**Create `frontend/src/lib/queries/services.ts`:**

````ts
/**
 * The archive (slice 5a spec, Frontend `lib/queries/services.ts`; F §4.4
 * keys and invalidations, §1.6 key rule, §1.7 `If-Match`). Every call is
 * church-scoped (`api.church`); a 401 or a lost church goes through the
 * caches' `handleAuthErrors` (`useChurchMutation`) and shows nothing more.
 *
 * - `useServices()`: the list, 20 a page, newest service date first (the
 *   server's order), "Show more" reading the next offset.
 * - `useSaveService()`: Save. "Save changes" PUTs with `If-Match` (the
 *   `saved_at` the draft holds); a 404 without `details.field` (the service
 *   was deleted) POSTs instead and says so; a 409 is left to the Save card
 *   (the conflict dialog). "Save to archive", "Save as new service" and the
 *   dialog's "Save mine as a new service" POST with the draft's save key
 *   (`save-key.ts`): replaced after any answer, kept for an identical retry
 *   after an unknown outcome, and one automatic retry with a new key after
 *   `idempotency_mismatch`. Success records the save in the draft
 *   (`markSaved`), caches the service, and refreshes the list and the hymns
 *   (a save rebuilds that date's hymn use, so `recently_used` changes).
 *   A replayed POST answer (the same key and body within 15 minutes) is the
 *   first answer; if that service was changed or deleted since, the next
 *   "Save changes" meets the 409 or the 404 above, which already handle it.
 * - `useOpenService(church)`: `GET /services/{id}` (always fetched), then the
 *   draft becomes `serviceToDraft(service)`. A 404 refreshes the list.
 * - `useDeleteService(church)`: `DELETE`, then the list and the hymns (a
 *   delete rebuilds that date's hymn use) are refreshed before it settles,
 *   so the row is gone when the dialog closes; deleting the service being
 *   edited resets the draft (F §4.6 rule 2), keeping the translation as New
 *   service does. A 404 refreshes the list.
 */
import { useInfiniteQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { DeletedOut, ServiceOut, ServicePage } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { serviceBody } from "@/lib/documents";
import { useDraft } from "@/lib/draft/context";
import { fingerprint } from "@/lib/draft/fingerprint";
import { draftToServicePayload, markSaved, serviceToDraft } from "@/lib/draft/mapping";
import { keyForPost, settlePost } from "@/lib/draft/save-key";
import { freshDraft, type DraftChurch } from "@/lib/draft/schema";
import { saveMode } from "@/lib/draft/status";
import { settleOutcome } from "@/lib/idempotency";
import { useMeContext } from "@/lib/me-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const SERVICES_PAGE_SIZE = 20;
export const SAVED_MESSAGE = "Service saved";
export const SAVED_AFTER_DELETE_MESSAGE = "The archived copy was deleted, so this was saved as a new service.";

/** A 401 or a lost church: the app's own handling already says it. */
function handledElsewhere(e: ApiError): boolean {
  return e.status === 401 || isNoChurchAccess(e);
}

/** `PUT /services/{id}`'s 409: someone else saved this service since it was saved or opened here. */
export function isConflict(e: unknown): boolean {
  return e instanceof ApiError && e.status === 409 && e.code === "conflict";
}

/** A hymn id the church no longer has: 404 with `details.field` "hymns.<slot>.hymn_id". */
function isHymnGone(e: ApiError): boolean {
  return e.status === 404 && typeof e.details?.field === "string";
}

function servicesKey(churchId: string) {
  return [...keys.church(churchId), "services"] as const;
}

function hymnsKey(churchId: string) {
  return [...keys.church(churchId), "hymns"] as const;
}

export function useServices() {
  const api = useApi();
  const church = useChurch();
  return useInfiniteQuery<ServicePage, ApiError>({
    queryKey: keys.services(church.id, { limit: SERVICES_PAGE_SIZE }),
    queryFn: ({ pageParam, signal }) =>
      api.church<ServicePage>(`/services?limit=${SERVICES_PAGE_SIZE}&offset=${pageParam as number}`, { signal }),
    initialPageParam: 0,
    getNextPageParam: (last) => {
      const next = last.offset + last.items.length;
      return last.items.length > 0 && next < last.total ? next : undefined;
    },
  });
}

export type SaveVariables = { asNew?: boolean };
type Saved = { service: ServiceOut; fp: string; fellBack: boolean };

export function useSaveService() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const router = useRouter();
  const { peek, update } = useDraft();
  return useChurchMutation<Saved, ApiError, SaveVariables>({
    mutationFn: async ({ asNew = false }) => {
      const draft = peek();
      const fp = fingerprint(draftToServicePayload(draft));
      const body = serviceBody(draft);

      async function post(retried: boolean): Promise<ServiceOut> {
        update((d) => keyForPost(d, fp));
        try {
          const out = await api.church<ServiceOut>("/services", { method: "POST", json: body, idempotencyKey: peek().save_key });
          update((d) => settlePost(d, "success"));
          return out;
        } catch (e) {
          update((d) => settlePost(d, settleOutcome(e)));
          if (!retried && e instanceof ApiError && e.code === "idempotency_mismatch") return post(true);
          throw e;
        }
      }

      const editing = draft.editing;
      if (!asNew && editing !== null && saveMode(draft) === "update") {
        try {
          const service = await api.church<ServiceOut>(`/services/${editing.service_id}`, {
            method: "PUT",
            json: body,
            ifMatch: editing.saved_at,
          });
          return { service, fp, fellBack: false };
        } catch (e) {
          // The saved copy was deleted (a 404 with no field): save this one as a new service.
          if (!(e instanceof ApiError) || e.status !== 404 || e.details?.field !== undefined) throw e;
          return { service: await post(false), fp, fellBack: true };
        }
      }
      return { service: await post(false), fp, fellBack: false };
    },
    onSuccess: ({ service, fp, fellBack }) => {
      update((d) => markSaved(d, service, fp));
      queryClient.setQueryData(keys.service(church.id, service.id), service);
      void queryClient.invalidateQueries({ queryKey: servicesKey(church.id) });
      void queryClient.invalidateQueries({ queryKey: hymnsKey(church.id) });
      toast.success(fellBack ? SAVED_AFTER_DELETE_MESSAGE : SAVED_MESSAGE);
    },
    onError: (e) => {
      if (handledElsewhere(e) || isConflict(e)) return;
      if (isHymnGone(e)) {
        toast.error(e.message, { action: { label: "Go to Hymns", onClick: () => router.push("/builder/hymns") } });
        return;
      }
      toast.error(errorToastMessage(e));
    },
  });
}

export function useOpenService(church: DraftChurch) {
  const api = useApi();
  const queryClient = useQueryClient();
  const me = useMeContext();
  const { replace } = useDraft();
  return useChurchMutation<ServiceOut, ApiError, string>({
    mutationFn: (serviceId) => api.church<ServiceOut>(`/services/${serviceId}`),
    onSuccess: (service) => {
      queryClient.setQueryData(keys.service(church.id, service.id), service);
      replace(serviceToDraft(service, { church, user: me.user }));
    },
    onError: (e) => {
      if (handledElsewhere(e)) return;
      toast.error(errorToastMessage(e));
      if (e.status === 404) void queryClient.invalidateQueries({ queryKey: servicesKey(church.id) });
    },
  });
}

export function useDeleteService(church: DraftChurch) {
  const api = useApi();
  const queryClient = useQueryClient();
  const me = useMeContext();
  const { peek, replace } = useDraft();
  return useChurchMutation<DeletedOut, ApiError, string>({
    mutationFn: (serviceId) => api.church<DeletedOut>(`/services/${serviceId}`, { method: "DELETE" }),
    onSuccess: async (_out, serviceId) => {
      queryClient.removeQueries({ queryKey: keys.service(church.id, serviceId) });
      const draft = peek();
      if (draft.editing?.service_id === serviceId) {
        const fresh = freshDraft({ church, user: me.user });
        replace({ ...fresh, readings: { ...fresh.readings, translation: draft.readings.translation } });
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: servicesKey(church.id) }),
        queryClient.invalidateQueries({ queryKey: hymnsKey(church.id) }),
      ]);
    },
    onError: (e) => {
      if (handledElsewhere(e)) return;
      toast.error(errorToastMessage(e));
      if (e.status === 404) void queryClient.invalidateQueries({ queryKey: servicesKey(church.id) });
    },
  });
}
````

- [ ] **Step 4 (agent): Run the file, the suite, the types and lint**

```bash
(cd frontend && npx vitest run src/lib/dates.test.ts src/lib/documents.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `      Tests  13 passed (13)` (`documents.test.ts`'s four cases unchanged: `documentRequest` is `serviceBody` with the variant); ` Test Files  82 passed (82)` and `      Tests  629 passed (629)` with no `×` or `FAIL` line; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/lib/queries/services.ts frontend/src/lib/dates.ts frontend/src/lib/documents.ts frontend/src/lib/dates.test.ts
git commit -q -m "Archive queries: save, open, delete and the list; the save time (5a-3; F 1.6, 1.7, 4.4)" -m "lib/queries/services.ts: useServices (20 a page), useSaveService (PUT
with If-Match; POST with the draft's key; the deleted-copy fallback; one
retry after idempotency_mismatch; a 409 left to the Save card),
useOpenService and useDeleteService, each refreshing the list and the
hymns as F 4.4 says. A save sends the downloads' body (serviceBody), so it
never meets a 422 for a length. formatSavedAt shows a save time in the
viewer's zone." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 3: frontend **629 in 82**; backend **1335 passed, 16 skipped**.

### Task 4: Review & send: the Archive card, the conflict dialog, the banner, "Still to do" (owner answers 2, 4, 9; S UX "Review step" items 1-4, "Step status and summary panel", "Mobile specifics"; F §4.7, §4.8, §4.9; clarifications 2-6, 9, 10, 13, 17, 18, 21)

**Files:**
- Create: `frontend/src/components/builder/review/save-card.tsx`, `frontend/src/components/builder/review/conflict-dialog.tsx`, `frontend/src/components/builder/review/editing-banner.tsx`
- Modify: `frontend/src/components/builder/review/review-send-step.tsx`, `frontend/src/components/builder/review/documents-card.tsx`, `frontend/src/components/builder/still-needed.tsx`, `frontend/src/components/builder/summary-panel.tsx`, `frontend/src/app/(signed-in)/(church)/builder/review/page.tsx`, `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/components/builder/builder-shell.test.tsx`

- [ ] **Step 1 (agent): Write the failing tests**

`review-send-step.test.tsx` gains "Review & send: saving" (eight cases: a new save then Save changes with every status; the banner, the hymn row and the two copy cases; the conflict dialog both ways; the deleted copy; Go to Hymns and a new key; the key kept, replaced and the mismatch retried; Start a new service; the save tip), a `Probe` button that changes the draft as another step would, and `toast.dismiss()` after each test (sonner replays a toast still showing to the next `Toaster`); its first case now checks the new order and its two "off" cases check Save too. `builder-shell.test.tsx` reads "Still to do" and "Everything's ready.".

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
        // Review & send is the real step from slice 5a-1: Still needed, the Word documents, the archive note.
        expect(within(card).getByRole("heading", { name: "Word documents" })).toBeInTheDocument();
````

**with:**

````tsx
        // Review & send is the real step from slice 5a-1: Still to do, the Archive card (5a-3), the Word documents.
        expect(within(card).getByRole("heading", { name: "Word documents" })).toBeInTheDocument();
        expect(within(card).getByRole("button", { name: "Save to archive" })).toBeEnabled();
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
        const needed = screen.getByRole("region", { name: "Still needed" });
````

**with:**

````tsx
        const needed = screen.getByRole("region", { name: "Still to do" });
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
        expect(screen.queryByRole("heading", { name: "Still needed" })).toBeNull();
````

**with:**

````tsx
        expect(screen.queryByRole("heading", { name: "Still to do" })).toBeNull();
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
  it("shows the readings status, Still needed rows, the occasion and the bulletin chips", async () => {
````

**with:**

````tsx
  it("shows the readings status, Still to do, the occasion and the bulletin chips", async () => {
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
    expect(screen.queryByRole("heading", { name: "Still needed" })).toBeNull(); // nothing missing
````

**with:**

````tsx
    // Nothing missing (slice 5a-3: the checklist says so).
    expect(screen.getByRole("region", { name: "Still to do" })).toHaveTextContent("Still to doEverything's ready.");
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
    const section = await screen.findByRole("region", { name: "Still needed" });
````

**with:**

````tsx
    const section = await screen.findByRole("region", { name: "Still to do" });
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
    const needed = screen.getByRole("region", { name: "Still needed" });
````

**with:**

````tsx
    const needed = screen.getByRole("region", { name: "Still to do" });
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
  it("counts the liturgy, lists it in the summary with the sections being written, and in Still needed", async () => {
````

**with:**

````tsx
  it("counts the liturgy, lists it in the summary with the sections being written, and in Still to do", async () => {
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
    const needed = await screen.findByRole("region", { name: "Still needed" });
````

**with:**

````tsx
    const needed = await screen.findByRole("region", { name: "Still to do" });
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
 * Review & send in slice 5a-1 (slice 5a spec, UX "Word documents card",
 * Testing `review-step.test.tsx` "Downloads" and "Invalid date"; owner answers
 * 2 and 3, 2026-10-01). The step renders inside the builder layout with a
 * Toaster; `URL.createObjectURL` and the link's click are stubbed, so a
 * download is recorded instead of navigating. The clock is fixed at Tuesday,
 * September 29, 2026, so a fresh draft is dated Sunday, October 4, 2026.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
````

**with:**

````tsx
 * Review & send (slice 5a spec, UX "Review step", Testing
 * `review-step.test.tsx`; owner answers 2-5 and 9, 2026-10-01): the Word
 * documents (5a-1) and saving (5a-3). The step renders inside the builder
 * layout with a Toaster; `URL.createObjectURL` and the link's click are
 * stubbed, so a download is recorded instead of navigating. The clock is
 * fixed at Tuesday, September 29, 2026, so a fresh draft is dated Sunday,
 * October 4, 2026. A test that needs an edit made elsewhere in the builder
 * renders a probe button that applies it.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { editScriptureLines } from "@/lib/draft/readings";
````

**with:**

````tsx
import { formatSavedAt } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { serviceToDraft } from "@/lib/draft/mapping";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { editOccasion, editScriptureLines, setDate } from "@/lib/draft/readings";
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
  testDraft,
````

**with:**

````tsx
  savedService,
  SERVICE_ID,
  testDraft,
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
import { renderWithProviders } from "@/test/render";

import { FIX_READINGS, NEEDS_DATE, SAME_AS_BULLETIN } from "./documents-card";
````

**with:**

````tsx
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { CONFLICT_TITLE } from "./conflict-dialog";
import { FIX_READINGS, NEEDS_DATE, SAME_AS_BULLETIN, SAVE_HINT } from "./documents-card";
import { CONFLICT_MESSAGE, LOADED_LATEST, SAVE_FIX_READINGS, SAVE_NEEDS_DATE } from "./save-card";
import { SAVED_AFTER_DELETE_MESSAGE, SAVED_MESSAGE } from "@/lib/queries/services";
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
function renderReview(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}) {
````

**with:**

````tsx
function renderReview(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}, probe: ReactNode = null) {
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
      </BuilderLayout>
````

**with:**

````tsx
        {probe}
      </BuilderLayout>
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
afterEach(() => {
  vi.useRealTimers();
````

**with:**

````tsx
afterEach(() => {
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
  vi.useRealTimers();
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
  it("shows Still needed, both copies with what they hold, and the archive note, with no placeholder", async () => {
````

**with:**

````tsx
  it("shows Still to do, the Archive card and both copies with what they hold, in that order, with no placeholder", async () => {
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(screen.getByRole("region", { name: "Still needed" })).toBeInTheDocument();
    const archive = screen.getByRole("region", { name: "Archive" });
    expect(archive).toHaveTextContent("Saving services to the archive is coming soon.");
````

**with:**

````tsx
    const step = screen.getByRole("region", { name: "Review & send" });
    expect(within(step).getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual(["Still to do", "Archive", "Word documents"]);
    const archive = screen.getByRole("region", { name: "Archive" });
    expect(within(archive).getByText("Not in the archive yet.")).toBeInTheDocument();
    expect(within(archive).getByRole("button", { name: "Save to archive" })).toHaveClass("h-11");
    expect(within(archive).getByRole("button", { name: "Start a new service" })).toHaveClass("h-11");
    expect(screen.queryByText(/coming soon/i)).toBeNull();
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
  it("turns both buttons off without a service date, and says why", async () => {
````

**with:**

````tsx
  it("turns both buttons and Save off without a service date, and says why", async () => {
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(within(screen.getByRole("region", { name: "Still needed" })).getByText(/No service date/)).toBeInTheDocument();
````

**with:**

````tsx
    const archive = screen.getByRole("region", { name: "Archive" });
    expect(within(archive).getByText(SAVE_NEEDS_DATE)).toBeInTheDocument();
    expect(within(archive).getByRole("button", { name: "Save to archive" })).toBeDisabled();
    expect(within(screen.getByRole("region", { name: "Still to do" })).getByText(/No service date/)).toBeInTheDocument();
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
  it("turns both buttons off while a Date & readings field shows its message, and says why (build review fix 6)", async () => {
````

**with:**

````tsx
  it("turns both buttons and Save off while a Date & readings field shows its message, and says why (build review fix 6)", async () => {
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
      expect(documentRequests(api)).toEqual([]);
````

**with:**

````tsx
      const archive = screen.getByRole("region", { name: "Archive" });
      expect(within(archive).getByText(SAVE_FIX_READINGS)).toBeInTheDocument();
      expect(within(archive).getByRole("button", { name: "Save to archive" })).toBeDisabled();
      expect(documentRequests(api)).toEqual([]);
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    }
  });
});

````

**with:**

````tsx
    }
  });
});

// --- slice 5a-3: saving ------------------------------------------------------------

const FIRST_SAVE = "2026-10-01T14:42:00.123456+00:00";
const SECOND_SAVE = "2026-10-02T15:05:00+00:00";
const OTHER_ID = "66666666-6666-4666-8666-666666666666";

/** A button the test presses to change the draft as another step would. */
function Probe({ edit }: { edit: (d: DraftV1) => DraftV1 }) {
  const { update } = useDraft();
  return (
    <button type="button" onClick={() => update(edit)}>
      Probe edit
    </button>
  );
}

/** The draft as `serviceToDraft` opens `savedService(overrides)`. */
function opened(overrides: Parameters<typeof savedService>[0] = {}): DraftV1 {
  return serviceToDraft(savedService(overrides), { church: churchProfile(), user: { id: USER_ID } });
}

function archiveCard() {
  return screen.findByRole("region", { name: "Archive" });
}

function serviceRequests(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/services"));
}

/** The draft as last written to localStorage. */
function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

describe("Review & send: saving (slice 5a-3)", () => {
  it("saves a new service with the draft's key, saves changes with If-Match, and every status follows", async () => {
    const d = editOccasion(testDraft(), "Harvest");
    const { api, user } = renderReview(
      d,
      {
        "POST /services": () => ({ status: 201, body: savedService({ occasion: "Harvest", saved_at: FIRST_SAVE }) }),
        [`PUT /services/${SERVICE_ID}`]: () => savedService({ occasion: "Harvest Home", saved_at: SECOND_SAVE }),
      },
      <Probe edit={(draft) => editOccasion(draft, "Harvest Home")} />,
    );
    const card = await archiveCard();
    const progress = screen.getByRole("navigation", { name: "Steps" });
    const aside = screen.getByRole("complementary", { name: "Summary" });
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Review & send Not in archive");
    expect(within(aside).getByText("Draft saved on this device · Not in archive")).toBeInTheDocument();

    await user.click(within(card).getByRole("button", { name: "Save to archive" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    const [post] = serviceRequests(api, "POST");
    expect(post.headers["idempotency-key"]).toBe(d.save_key);
    expect(post.headers["x-church-id"]).toBe(church().id);
    expect(post.body).toMatchObject({ service_date_iso: "2026-10-04", occasion: "Harvest", include_communion: true });
    expect(within(card).getByText(`Saved to the archive · ${formatSavedAt(FIRST_SAVE)}`)).toBeInTheDocument();
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Review & send Saved");
    expect(within(aside).getByText(`Draft saved on this device · In archive (saved ${formatSavedAt(FIRST_SAVE)})`)).toBeInTheDocument();
    await waitFor(() => expect(stored().editing).toEqual({ service_id: SERVICE_ID, saved_at: FIRST_SAVE, date_iso: "2026-10-04" }));
    expect(stored().save_key).not.toBe(d.save_key); // a definitive answer: the next POST gets a new key
    expect(stored().save_key_fingerprint).toBeNull();
    expect(stored().created_at).toBe(d.created_at); // the same draft, so the reviewer's notes stay (owner answer 9)
    // Owner answer 4: what followed a default is now the saved service's own.
    expect(stored().liturgy.cards.benediction.origin).toBe("archive");
    expect(stored().liturgy.communion_origin).toBe("archive");

    await user.click(screen.getByRole("button", { name: "Probe edit" }));
    expect(within(card).getByText(`Unsaved changes · last saved ${formatSavedAt(FIRST_SAVE)}`)).toBeInTheDocument();
    expect(within(progress).getAllByRole("link")[3]).toHaveTextContent("4 Review & send Unsaved changes");
    expect(
      within(aside).getByText(`Draft saved on this device · In archive (saved ${formatSavedAt(FIRST_SAVE)}) · Unsaved changes`),
    ).toBeInTheDocument();

    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(within(card).getByText(`Saved to the archive · ${formatSavedAt(SECOND_SAVE)}`)).toBeInTheDocument());
    const [put] = serviceRequests(api, "PUT");
    expect(put.path).toBe(`/services/${SERVICE_ID}`);
    expect(put.headers["if-match"]).toBe(FIRST_SAVE);
    expect(put.headers["idempotency-key"]).toBeUndefined();
    expect(put.body).toMatchObject({ occasion: "Harvest Home" });
    expect(serviceRequests(api, "POST")).toHaveLength(1);
  });

  it("opens with the banner and the hymn to replace, and saves a copy when the date changed or the service had none", async () => {
    const moved = setDate(opened(), "2026-10-11");
    const first = renderReview(moved, {
      "POST /services": () => ({ status: 201, body: savedService({ id: OTHER_ID, service_date_iso: "2026-10-11", saved_at: SECOND_SAVE }) }),
    });
    const card = await archiveCard();
    expect(screen.getByText("You're editing the saved service for October 4, 2026. Changes stay on this device until you save.")).toBeInTheDocument();
    const todo = screen.getByRole("region", { name: "Still to do" });
    expect(within(todo).getByText(/Old Favorite isn't in your hymnal/)).toBeInTheDocument();
    expect(within(todo).getByRole("link", { name: "Choose a replacement" })).toHaveAttribute("href", "/builder/hymns");
    const button = within(card).getByRole("button", { name: "Save as new service" });
    expect(button).toHaveAccessibleDescription(
      "The date changed from October 4, 2026 to October 11, 2026, so this will be saved as a new service. The October 4 service stays in the archive.",
    );
    await first.user.click(button);
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    expect(serviceRequests(first.api, "PUT")).toEqual([]);
    expect(serviceRequests(first.api, "POST")).toHaveLength(1);
    await waitFor(() => expect(stored().editing?.service_id).toBe(OTHER_ID));
    expect(within(card).getByRole("button", { name: "Save changes" })).toBeInTheDocument();
    first.unmount();
    window.localStorage.clear();

    const second = renderReview(opened({ service_date_iso: null, service_date: "" }), {
      "POST /services": () => ({ status: 201, body: savedService({ id: OTHER_ID, saved_at: SECOND_SAVE }) }),
    });
    const undated = await archiveCard();
    expect(screen.getByText(/This saved service has no date\. It's set to Sunday, October 4, 2026 for now\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Check the date" })).toHaveAttribute("href", "/builder/readings");
    expect(within(undated).getByRole("button", { name: "Save as new service" })).toHaveAccessibleDescription(
      "The saved service has no date, so this will be saved as a new service on October 4, 2026. The undated service stays in the archive.",
    );
    await second.user.click(within(undated).getByRole("button", { name: "Save as new service" }));
    expect(await screen.findByText("You're editing the saved service for October 4, 2026. Changes stay on this device until you save.")).toBeInTheDocument();
    expect(screen.queryByText(/has no date/)).toBeNull();
  });

  it("on a conflict, reloads their version or saves mine as a new service", async () => {
    const { api, user } = renderReview(opened({ saved_at: FIRST_SAVE }), {
      [`PUT /services/${SERVICE_ID}`]: fakeError(409, "conflict", CONFLICT_MESSAGE, { details: { current_saved_at: SECOND_SAVE } }),
      [`GET /services/${SERVICE_ID}`]: savedService({ occasion: "Their occasion", saved_at: SECOND_SAVE }),
      "POST /services": () => ({ status: 201, body: savedService({ id: OTHER_ID, saved_at: "2026-10-02T15:10:00+00:00" }) }),
    });
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    const dialog = await screen.findByRole("alertdialog", { name: CONFLICT_TITLE });
    expect(dialog).toHaveTextContent(CONFLICT_MESSAGE);
    await user.click(within(dialog).getByRole("button", { name: "Reload their version" }));
    expect(await screen.findByText(LOADED_LATEST)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(stored()).toMatchObject({ readings: { occasion: "Their occasion" }, editing: { saved_at: SECOND_SAVE } });
    expect(within(card).getByText(`Saved to the archive · ${formatSavedAt(SECOND_SAVE)}`)).toBeInTheDocument();

    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    const again = await screen.findByRole("alertdialog", { name: CONFLICT_TITLE });
    await user.click(within(again).getByRole("button", { name: "Save mine as a new service" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(serviceRequests(api, "POST")).toHaveLength(1);
    await waitFor(() => expect(stored().editing?.service_id).toBe(OTHER_ID));
  });

  it("saves as a new service, and says so, when the saved copy was deleted", async () => {
    const { api, user } = renderReview(opened(), {
      [`PUT /services/${SERVICE_ID}`]: fakeError(404, "not_found", "That service is no longer in the archive."),
      "POST /services": () => ({ status: 201, body: savedService({ id: OTHER_ID, saved_at: SECOND_SAVE }) }),
    });
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText(SAVED_AFTER_DELETE_MESSAGE)).toBeInTheDocument();
    const [post] = serviceRequests(api, "POST");
    expect(post.headers["idempotency-key"]).toBeTruthy();
    await waitFor(() => expect(stored().editing?.service_id).toBe(OTHER_ID));
  });

  it("offers Go to Hymns for a hymn the church no longer has, and the corrected save uses a new key", async () => {
    const [holy, praise] = gg2013();
    const failure = fakeError(404, "not_found", HYMN_GONE, { details: { field: "hymns.opening.hymn_id" } });
    let posts = 0;
    const { api, user } = renderReview(
      setSlot(testDraft(), "opening", pickFromHymn(holy)),
      {
        "POST /services": () => {
          posts += 1;
          return posts === 1 ? failure : { status: 201, body: savedService({ saved_at: FIRST_SAVE }) };
        },
      },
      <Probe edit={(draft) => setSlot(draft, "opening", pickFromHymn(praise))} />,
    );
    const card = await archiveCard();
    await user.click(within(card).getByRole("button", { name: "Save to archive" }));
    expect(await screen.findByText(HYMN_GONE)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Go to Hymns" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder/hymns");
    await user.click(screen.getByRole("button", { name: "Probe edit" }));
    await user.click(within(card).getByRole("button", { name: "Save to archive" }));
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    const [first, second] = serviceRequests(api, "POST");
    expect(second.headers["idempotency-key"]).not.toBe(first.headers["idempotency-key"]);
  });

  it("keeps the key for an identical retry after an unknown outcome, replaces it after an edit, and retries a mismatch once", async () => {
    const errorToast = vi.spyOn(toast, "error");
    let posts = 0;
    const { api, user } = renderReview(
      editOccasion(testDraft(), "Harvest"),
      {
        "POST /services": () => {
          posts += 1;
          if (posts <= 2) throw new TypeError("Failed to fetch");
          if (posts === 3) return fakeError(422, "idempotency_mismatch", "This request was already sent with different details.");
          return { status: 201, body: savedService({ saved_at: FIRST_SAVE }) };
        },
      },
      <Probe edit={(draft) => editOccasion(draft, "Harvest Home")} />,
    );
    const card = await archiveCard();
    const save = () => user.click(within(card).getByRole("button", { name: "Save to archive" }));
    await save();
    await waitFor(() => expect(errorToast).toHaveBeenCalledTimes(1));
    await save(); // unchanged: the same key, so a stored first answer would be replayed
    await waitFor(() => expect(errorToast).toHaveBeenCalledTimes(2));
    await user.click(screen.getByRole("button", { name: "Probe edit" }));
    await save(); // changed: a new key; the mismatch is retried once with another
    expect(await screen.findByText(SAVED_MESSAGE)).toBeInTheDocument();
    const keys = serviceRequests(api, "POST").map((r) => r.headers["idempotency-key"]);
    expect(keys).toHaveLength(4);
    expect(keys[1]).toBe(keys[0]);
    expect(new Set(keys.slice(1)).size).toBe(3);
    expect(errorToast).toHaveBeenCalledTimes(2); // no message for the mismatch
  });

  it("Start a new service asks first when the draft has unsaved work, and not when it is saved", async () => {
    const first = renderReview(editOccasion(testDraft(), "Harvest"));
    const card = await archiveCard();
    await first.user.click(within(card).getByRole("button", { name: "Start a new service" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Start a new service?" });
    await first.user.click(within(dialog).getByRole("button", { name: "Start new service" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
    expect(stored().readings.occasion).toBe("");
    first.unmount();
    window.localStorage.clear();
    testRouter.push.mockClear();

    const second = renderReview(opened());
    const savedCard = await archiveCard();
    await second.user.click(within(savedCard).getByRole("button", { name: "Start a new service" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(stored().editing).toBeNull();
  });

  it("after a download, says that saving records the hymns, until the service is saved", async () => {
    const { user } = renderReview(testDraft(), {
      "POST /documents": () => docx(),
      "POST /services": () => ({ status: 201, body: savedService({ saved_at: FIRST_SAVE }) }),
    });
    const documents = await documentsCard();
    expect(within(documents).queryByText(SAVE_HINT)).toBeNull();
    await user.click(within(documents).getByRole("button", { name: "Download bulletin copy" }));
    expect(await within(documents).findByText(SAVE_HINT)).toBeInTheDocument();
    await user.click(within(await archiveCard()).getByRole("button", { name: "Save to archive" }));
    await waitFor(() => expect(within(documents).queryByText(SAVE_HINT)).toBeNull());
  });
});

````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/review/review-send-step.test.tsx src/components/builder/builder-shell.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")
```

**Expected:** five failures and `review-send-step.test.tsx` cannot load (`./conflict-dialog` does not exist yet):
```
   × builder shell (F §4.7) > renders each step route inside the shell: progress, the step, and the footer links <t>ms
   × the shell with Date & readings shipped (slice 2c) > shows the readings status, Still to do, the occasion and the bulletin chips <t>ms
   × the shell with Date & readings shipped (slice 2c) > lists what is missing, each linking to its step <t>ms
   × the shell with Hymns shipped (slice 3b) > counts Hymns n of 3, then Complete, and the summary lists the three slots in the column and the sheet <t>ms
   × the shell with Liturgy shipped (slice 4b) > counts the liturgy, lists it in the summary with the sections being written, and in Still to do <t>ms
 FAIL  |dom| src/components/builder/review/review-send-step.test.tsx [ src/components/builder/review/review-send-step.test.tsx ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 5 ⎯⎯⎯⎯⎯⎯⎯
      Tests  5 failed | 6 passed (11)
```

- [ ] **Step 3 (agent): The step, the card, the dialog, the banner, the checklist, the summary**

**In `frontend/src/app/(signed-in)/(church)/builder/review/page.tsx`, replace:**

````tsx
/** Step: Review & send (slice 5a-1: Still needed and the Word files; 5a-3 adds saving). */
````

**with:**

````tsx
/** Step: Review & send (slice 5a-1: the checklist and the Word files; 5a-3: saving). */
````

**Create `frontend/src/components/builder/review/conflict-dialog.tsx`:**

````tsx
"use client";

import { PendingButton } from "@/components/app/pending-button";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export const CONFLICT_TITLE = "Someone else changed this service";

/**
 * The 409 dialog (slice 5a spec, UX "Save card" Conflict; F §1.7): the
 * server's message, then "Reload their version" (the dialog is the
 * confirmation: the draft becomes their saved copy), "Save mine as a new
 * service" (a POST; theirs stays) and "Cancel" (nothing changes). Each action
 * button shows its own pending label; the dialog stays open until it ends.
 */
export function ConflictDialog({
  open,
  onOpenChange,
  message,
  onReload,
  reloading,
  onSaveAsNew,
  saving,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  message: string;
  onReload: () => void;
  reloading: boolean;
  onSaveAsNew: () => void;
  saving: boolean;
}) {
  const busy = reloading || saving;
  return (
    <AlertDialog open={open} onOpenChange={(next) => onOpenChange(next)}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{CONFLICT_TITLE}</AlertDialogTitle>
          <AlertDialogDescription>{message}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel size="touch" className="md:h-8">
            Cancel
          </AlertDialogCancel>
          <PendingButton
            variant="outline"
            size="touch"
            className="md:h-8"
            pending={saving}
            disabled={busy}
            onClick={() => onSaveAsNew()}
          >
            Save mine as a new service
          </PendingButton>
          <PendingButton
            size="touch"
            className="md:h-8"
            pending={reloading}
            pendingLabel="Loading…"
            disabled={busy}
            onClick={() => onReload()}
          >
            Reload their version
          </PendingButton>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
````

**In `frontend/src/components/builder/review/documents-card.tsx`, replace:**

````tsx
import { DownloadIcon } from "lucide-react";

````

**with:**

````tsx
import { DownloadIcon } from "lucide-react";
import { useState } from "react";

````

**In `frontend/src/components/builder/review/documents-card.tsx`, replace:**

````tsx
import { hasReadingsError, hasServiceDate } from "@/lib/draft/status";
````

**with:**

````tsx
import { hasReadingsError, hasServiceDate, reviewStatus } from "@/lib/draft/status";
````

**In `frontend/src/components/builder/review/documents-card.tsx`, replace:**

````tsx
export const FIX_READINGS = "Fix the readings on step 1 to download.";

````

**with:**

````tsx
export const FIX_READINGS = "Fix the readings on step 1 to download.";
export const SAVE_HINT = "Tip: save this service so its hymns count as recently used.";

````

**In `frontend/src/components/builder/review/documents-card.tsx`, replace:**

````tsx
function CopyRow({ copy, disabled, helper }: { copy: Copy; disabled: boolean; helper: string | null }) {
````

**with:**

````tsx
function CopyRow({
  copy,
  disabled,
  helper,
  onDownloaded,
}: {
  copy: Copy;
  disabled: boolean;
  helper: string | null;
  onDownloaded: () => void;
}) {
````

**In `frontend/src/components/builder/review/documents-card.tsx`, replace:**

````tsx
        onClick={() => download.mutate()}
````

**with:**

````tsx
        onClick={() => download.mutate(undefined, { onSuccess: onDownloaded })}
````

**In `frontend/src/components/builder/review/documents-card.tsx`, replace:**

````tsx
 * title]" for a blank title).
 */
export function DocumentsCard() {
  const { draft } = useDraft();
````

**with:**

````tsx
 * title]" for a blank title). After a download while the draft is not saved
 * as it is (slice 5a-3), a tip says that saving is what records the hymns as
 * recently used.
 */
export function DocumentsCard() {
  const { draft } = useDraft();
  const [downloaded, setDownloaded] = useState(false);
````

**In `frontend/src/components/builder/review/documents-card.tsx`, replace:**

````tsx
          />
        ))}
      </ul>
````

**with:**

````tsx
            onDownloaded={() => setDownloaded(true)}
          />
        ))}
      </ul>
      {downloaded && reviewStatus(draft) !== "saved" ? <p className="text-sm text-muted-foreground">{SAVE_HINT}</p> : null}
````

**Create `frontend/src/components/builder/review/editing-banner.tsx`:**

````tsx
"use client";

import Link from "next/link";

import { formatLongDate, formatServiceDate } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";

/**
 * The banner at the top of Review while the draft is a saved service (slice
 * 5a spec, UX "Review step" item 1): which saved service this is, and that
 * changes stay on this device until saved. A saved service with no date (a
 * legacy row; production had none on 2026-10-02) says so instead, with the
 * date it was given for now and a link to step 1. It is advice only. A hymn
 * that is not in the hymnal is listed in "Still to do" just below, so the
 * banner does not repeat it.
 */
export function EditingBanner() {
  const { draft } = useDraft();
  const editing = draft.editing;
  if (editing === null) return null;
  if (editing.date_iso === null) {
    const now = formatLongDate(draft.readings.date_iso);
    return (
      <div className="rounded-lg border bg-muted/40 p-4 text-sm">
        <p>
          This saved service has no date.{now ? ` It's set to ${now} for now.` : ""}{" "}
          <Link href="/builder/readings" className="font-medium underline underline-offset-4">
            Check the date
          </Link>
        </p>
      </div>
    );
  }
  return (
    <div className="rounded-lg border bg-muted/40 p-4 text-sm">
      <p>
        You&apos;re editing the saved service for {formatServiceDate(editing.date_iso)}. Changes stay on this device until you
        save.
      </p>
    </div>
  );
}
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````tsx

import { DocumentsCard } from "./documents-card";

/**
 * Step 4, Review & send, as slice 5a-1 ships it (owner answers 1 and 2,
 * 2026-10-01): "Still needed" (the shipped steps' gaps, each a link to fix
 * it), the Word documents, and a note that saving to the archive comes later
 * (5a-3 puts the Save card here). No order-of-worship preview: the Liturgy
 * step already shows the order.
 */
export function ReviewSendStep() {
  return (
    <section aria-label="Review & send" className="grid gap-6">
      <StillNeeded />
      <DocumentsCard />
      <section aria-labelledby="archive-title" className="grid gap-1 rounded-lg border border-dashed p-4">
        <h2 id="archive-title" className="text-base font-medium">
          Archive
        </h2>
        <p className="text-sm text-muted-foreground">Saving services to the archive is coming soon.</p>
      </section>
````

**with:**

````tsx
import { useChurch } from "@/lib/church-context";
import { useChurchProfile } from "@/lib/queries/church";

import { DocumentsCard } from "./documents-card";
import { EditingBanner } from "./editing-banner";
import { SaveCard } from "./save-card";

/**
 * Step 4, Review & send (slice 5a spec, UX "Review step"; owner answers 1 and
 * 2, 2026-10-01), top to bottom: the banner while the draft is a saved
 * service, "Still to do" (each gap a link to fix it), the Archive card (save,
 * start a new service; 5a-3), and the Word documents. No order-of-worship
 * preview: the Liturgy step already shows the order. Email comes in 5b.
 */
export function ReviewSendStep() {
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  return (
    <section aria-label="Review & send" className="grid gap-6">
      <EditingBanner />
      <StillNeeded />
      {/* The builder shows a step only once the profile has loaded (BuilderShell). */}
      {profile.data ? <SaveCard church={profile.data} /> : null}
      <DocumentsCard />
````

**Create `frontend/src/components/builder/review/save-card.tsx`:**

````tsx
"use client";

import { useState } from "react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { useNewService } from "@/components/builder/new-service-menu-item";
import { Button } from "@/components/ui/button";
import { formatSavedAt, formatServiceDate, formatShortDate } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import type { DraftChurch, DraftV1 } from "@/lib/draft/schema";
import { hasReadingsError, hasServiceDate, reviewStatus, saveMode } from "@/lib/draft/status";
import { isConflict, useOpenService, useSaveService } from "@/lib/queries/services";

import { ConflictDialog } from "./conflict-dialog";

export const SAVE_NEEDS_DATE = "Choose a service date on step 1 to save.";
export const SAVE_FIX_READINGS = "Fix the readings on step 1 to save.";
export const CONFLICT_MESSAGE = "This service was changed by someone else. Reload it to see their changes.";
export const LOADED_LATEST = "Loaded the latest version.";

/** The line under the heading (S UX "Save card" status line). */
export function archiveStatusLine(draft: DraftV1): string {
  const editing = draft.editing;
  if (editing === null) return "Not in the archive yet.";
  const at = formatSavedAt(editing.saved_at);
  return reviewStatus(draft) === "saved" ? `Saved to the archive · ${at}` : `Unsaved changes · last saved ${at}`;
}

/** Why the button says "Save as new service" (S UX "Save card"); null in the other modes or without a date. */
function copyNote(draft: DraftV1): string | null {
  const editing = draft.editing;
  if (editing === null || saveMode(draft) !== "copy" || !hasServiceDate(draft)) return null;
  const now = formatServiceDate(draft.readings.date_iso);
  if (editing.date_iso === null) {
    return `The saved service has no date, so this will be saved as a new service on ${now}. The undated service stays in the archive.`;
  }
  return `The date changed from ${formatServiceDate(editing.date_iso)} to ${now}, so this will be saved as a new service. The ${formatShortDate(editing.date_iso)} service stays in the archive.`;
}

const LABELS = { new: "Save to archive", update: "Save changes", copy: "Save as new service" } as const;

/**
 * The Archive card (slice 5a spec, UX "Save card"; owner answer 4): where the
 * draft stands in the archive, the save button ("Save to archive", "Save
 * changes" or "Save as new service", with why when the date changed),
 * "Saving…" while it runs, and "Start a new service" (New service's own
 * question when there is something to lose). The button is off only without
 * a service date or while a Date & readings field shows its message, as the
 * downloads are. A 409 opens the conflict dialog; every other outcome is a
 * toast from `useSaveService`.
 */
export function SaveCard({ church }: { church: DraftChurch }) {
  const { draft } = useDraft();
  const save = useSaveService();
  const reload = useOpenService(church);
  const newService = useNewService(church);
  const [conflict, setConflict] = useState<string | null>(null);
  const mode = saveMode(draft);
  const dated = hasServiceDate(draft);
  const readingsError = hasReadingsError(draft);
  const note = copyNote(draft);

  function run(asNew: boolean) {
    save.mutate(
      { asNew },
      {
        onSuccess: () => setConflict(null),
        onError: (e) => {
          if (isConflict(e)) setConflict(e.message || CONFLICT_MESSAGE);
        },
      },
    );
  }

  function reloadTheirs() {
    const id = draft.editing?.service_id;
    if (!id) return;
    reload.mutate(id, {
      onSuccess: () => {
        setConflict(null);
        toast.success(LOADED_LATEST);
      },
      onError: () => setConflict(null),
    });
  }

  return (
    <section aria-labelledby="archive-title" className="grid gap-3 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="archive-title" className="text-base font-medium">
          Archive
        </h2>
        <p className="text-sm text-muted-foreground">{archiveStatusLine(draft)}</p>
        {dated ? null : <p className="text-sm text-muted-foreground">{SAVE_NEEDS_DATE}</p>}
        {readingsError ? <p className="text-sm text-muted-foreground">{SAVE_FIX_READINGS}</p> : null}
      </div>
      {note ? (
        <p id="save-note" className="text-sm text-muted-foreground">
          {note}
        </p>
      ) : null}
      <div className="flex flex-col gap-2 sm:flex-row">
        <PendingButton
          size="touch"
          className="w-full sm:w-fit"
          pending={save.isPending}
          disabled={!dated || readingsError}
          aria-describedby={note ? "save-note" : undefined}
          onClick={() => run(false)}
        >
          {LABELS[mode]}
        </PendingButton>
        <Button variant="outline" size="touch" className="w-full sm:w-fit" onClick={() => newService.start()}>
          Start a new service
        </Button>
      </div>
      <ConflictDialog
        open={conflict !== null}
        onOpenChange={(open) => {
          if (!open && !save.isPending && !reload.isPending) setConflict(null);
        }}
        message={conflict ?? CONFLICT_MESSAGE}
        onReload={reloadTheirs}
        reloading={reload.isPending}
        onSaveAsNew={() => run(true)}
        saving={save.isPending}
      />
      {newService.dialog}
    </section>
  );
}
````

**In `frontend/src/components/builder/still-needed.tsx`, replace:**

````tsx
 * Review's "Still needed" list (S "Steps 2–4"; F §4.7 "Review has no Next"):
 * one row per gap in a shipped step, each linking to that step. Nothing
 * renders while no step has shipped (slice 2b) or nothing is missing.
````

**with:**

````tsx
 * Review's checklist, "Still to do" (slice 5a spec, UX "Review step" item 2;
 * F §4.7 "Review has no Next"; renamed from 4b's "Still needed" in 5a-3): one
 * row per gap in a shipped step, each linking to where it is fixed, or
 * "Everything's ready." when nothing is missing. Nothing it lists blocks
 * Save or the downloads but the date (F D9).
````

**In `frontend/src/components/builder/still-needed.tsx`, replace:**

````tsx
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="still-needed-heading" className="grid gap-2">
      <h2 id="still-needed-heading" className="text-base font-medium">
        Still needed
      </h2>
      <ul className="grid gap-1 text-sm">
````

**with:**

````tsx
  return (
    <section aria-labelledby="still-needed-heading" className="grid gap-2">
      <h2 id="still-needed-heading" className="text-base font-medium">
        Still to do
      </h2>
      {items.length === 0 ? <p className="text-sm">Everything&apos;s ready.</p> : null}
      <ul className="grid gap-1 text-sm empty:hidden">
````

**In `frontend/src/components/builder/summary-panel.tsx`, replace:**

````tsx
import { formatLongDate } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { cleanScriptures, effectivePicks } from "@/lib/draft/readings";
````

**with:**

````tsx
import { formatLongDate, formatSavedAt } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { cleanScriptures, effectivePicks } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { reviewStatus } from "@/lib/draft/status";
````

**In `frontend/src/components/builder/summary-panel.tsx`, replace:**

````tsx

/**
 * The draft at a glance (S "SummaryPanel"; F §4.7): a sticky column from
````

**with:**

````tsx

/** The archive half of the status line (S "Step status and summary panel"; slice 5a-3). */
export function archiveSummary(draft: DraftV1): string {
  if (draft.editing === null) return "Not in archive";
  const saved = `In archive (saved ${formatSavedAt(draft.editing.saved_at)})`;
  return reviewStatus(draft) === "saved" ? saved : `${saved} · Unsaved changes`;
}

/**
 * The draft at a glance (S "SummaryPanel"; F §4.7): a sticky column from
````

**In `frontend/src/components/builder/summary-panel.tsx`, replace:**

````tsx
 * (slice 4b); 5a wires the archive half of the status line.
````

**with:**

````tsx
 * (slice 4b); 5a-3 wires the archive half of the status line, which links to Review.
````

**In `frontend/src/components/builder/summary-panel.tsx`, replace:**

````tsx
      <p className="border-t pt-3 text-xs text-muted-foreground">{saved} · Not in archive</p>
````

**with:**

````tsx
      <p className="border-t pt-3 text-xs text-muted-foreground">
        <Link
          href={stepById("review").href}
          onClick={onNavigate}
          className="inline-flex min-h-11 items-center underline-offset-4 hover:underline lg:min-h-0"
        >
          {saved} · {archiveSummary(draft)}
        </Link>
      </p>
````

- [ ] **Step 4 (agent): Run the files three times, the suite, the types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/components/builder/review/review-send-step.test.tsx src/components/builder/builder-shell.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests "); done
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
grep -rn "Saving services to the archive" frontend/src; echo "note grep exit $?"
```

**Expected:** three times `      Tests  27 passed (27)`; ` Test Files  82 passed (82)` and `      Tests  637 passed (637)` with no `×` or `FAIL` line; `typecheck 0`, `lint 0`; `note grep exit 1` (5a-1's note is gone).

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/components/builder/review/save-card.tsx frontend/src/components/builder/review/conflict-dialog.tsx frontend/src/components/builder/review/editing-banner.tsx frontend/src/components/builder/review/review-send-step.tsx frontend/src/components/builder/review/documents-card.tsx frontend/src/components/builder/still-needed.tsx frontend/src/components/builder/summary-panel.tsx 'frontend/src/app/(signed-in)/(church)/builder/review/page.tsx' frontend/src/components/builder/review/review-send-step.test.tsx frontend/src/components/builder/builder-shell.test.tsx
git commit -q -m "Review & send: the Archive card, the conflict dialog, the banner and Still to do (5a-3; owner answers 2, 4, 9)" -m "Step 4 now shows the banner while the draft is a saved service, Still
to do (4b's list renamed, Everything's ready. when nothing is missing, a
row per hymn not in the hymnal), the Archive card (Save to archive, Save
changes or Save as new service with why, Start a new service) and the
Word documents with the save tip. A 409 opens Someone else changed this
service (Reload their version, Save mine as a new service, Cancel). The
summary's status line shows the archive half and links to Review." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 4: frontend **637 in 82**; backend **1335 passed, 16 skipped**.

### Task 5: The Services page and the menu item (owner answer 6; S "Services page", "Mobile specifics"; F §4.1, §4.2, §4.8, §4.9; clarifications 14-16, 18, 21)

**Files:**
- Create: `frontend/src/app/(signed-in)/(church)/services/page.tsx`, `frontend/src/components/services/services-page.tsx`, `frontend/src/components/services/service-row.tsx`, `frontend/src/components/services/services-page.test.tsx`
- Modify: `frontend/src/components/app/app-nav.tsx`, `frontend/src/components/app/app-header.test.tsx`

- [ ] **Step 1 (agent): Write the failing tests**

**In `frontend/src/components/app/app-header.test.tsx`, replace:**

````tsx
  it("shows the Builder nav item on church pages, current under /builder, and no nav without churches (F §4.2)", () => {
````

**with:**

````tsx
  it("shows the Builder and Services nav items on church pages, current under /builder, and no nav without churches (F §4.2)", () => {
````

**In `frontend/src/components/app/app-header.test.tsx`, replace:**

````tsx
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([["Builder", "/builder"]]);
````

**with:**

````tsx
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([
      ["Builder", "/builder"],
      ["Services", "/services"],
    ]);
    expect(links[1]).not.toHaveAttribute("aria-current");
````

**Create `frontend/src/components/services/services-page.test.tsx`:**

````tsx
/**
 * The Services page (slice 5a spec, "Services page", Testing
 * `services-archive.test.tsx`; F §4.8). The page renders as the route does,
 * with a Toaster; the draft is seeded in localStorage. The clock is fixed at
 * Tuesday, September 29, 2026, so a fresh draft is dated Sunday, October 4.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ServicesRoute from "@/app/(signed-in)/(church)/services/page";
import { Toaster } from "@/components/ui/sonner";
import type { ServiceSummary } from "@/lib/api/types";
import { formatSavedAt } from "@/lib/dates";
import { serviceToDraft } from "@/lib/draft/mapping";
import { editOccasion } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  me,
  savedService,
  SERVICE_ID,
  servicePage,
  serviceSummary,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

const KEY = draftKey(USER_ID, church().id);
const GONE = "That service is no longer in the archive.";

function renderServices(draft: DraftV1 | null, routes: Record<string, FakeHandler>) {
  if (draft) window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({ "GET /church": churchProfile(), ...routes });
  const view = renderWithProviders(
    <>
      <ServicesRoute />
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/services" },
  );
  return { ...view, api };
}

function listRequests(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "GET" && r.path.startsWith("/services?"));
}

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

/** `n` rows with distinct ids and dates, newest first. */
function rows(n: number, from = 0): ServiceSummary[] {
  return Array.from({ length: n }, (_, i) =>
    serviceSummary({ id: `00000000-0000-4000-8000-${String(from + i + 1).padStart(12, "0")}`, occasion: `Service ${from + i + 1}` }),
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Services (slice 5a-3)", () => {
  it("shows five rows while it loads, then each service with its date, occasion and who saved it", async () => {
    let release!: () => void;
    const held = new Promise<void>((resolve) => (release = resolve));
    const undated = serviceSummary({
      id: "77777777-7777-4777-8777-777777777777",
      service_date_iso: null,
      service_date: "",
      occasion: "",
      created_by: null,
      saved_at: "2026-09-20T12:00:00+00:00",
    });
    renderServices(testDraft(), {
      "GET /services": async () => {
        await held;
        return servicePage([serviceSummary(), undated]);
      },
    });
    expect(await screen.findByRole("heading", { level: 1, name: "Services" })).toBeInTheDocument();
    expect(screen.getByText("Saved services for Grace.")).toBeInTheDocument();
    const loading = screen.getByRole("status", { name: "Loading" });
    expect(loading.querySelectorAll('[data-slot="skeleton"]')).toHaveLength(5);
    release();
    const list = await screen.findByRole("list");
    const buttons = within(list)
      .getAllByRole("listitem")
      .map((li) => within(li).getAllByRole("button")[0]);
    expect(buttons.map((b) => b.textContent)).toEqual([
      `October 4, 2026World Communion SundayCreated by Pat Pastor · last saved ${formatSavedAt(serviceSummary().saved_at)}`,
      `No dateNo occasionLast saved ${formatSavedAt("2026-09-20T12:00:00+00:00")}`,
    ]);
    expect(buttons[0]).toHaveClass("min-h-11");
    expect(within(list).getByRole("button", { name: "More actions for October 4, 2026" })).toHaveClass("size-11");
    expect(screen.getByText("Showing 2 of 2")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
    expect(screen.queryByText("Editing")).toBeNull();
  });

  it("with nothing saved, offers to build a service; New service opens the builder", async () => {
    const { user } = renderServices(testDraft(), { "GET /services": servicePage([]) });
    expect(await screen.findByText("No saved services yet")).toBeInTheDocument();
    expect(screen.getByText("Services you save from the builder appear here.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Build a service" })).toHaveAttribute("href", "/builder");
    await user.click(screen.getByRole("button", { name: "New service" }));
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
  });

  it("shows an error with Retry, never an empty list, and Retry asks again", async () => {
    let calls = 0;
    const { user, api } = renderServices(testDraft(), {
      "GET /services": () => {
        calls += 1;
        return calls === 1 ? fakeError(500, "internal_error", "Something went wrong.") : servicePage(rows(1));
      },
    });
    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.queryByText("No saved services yet")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Service 1")).toBeInTheDocument();
    expect(listRequests(api)).toHaveLength(2);
  });

  it("Show more reads the next 20", async () => {
    const { user, api } = renderServices(testDraft(), {
      "GET /services?limit=20&offset=0": servicePage(rows(20), { total: 45 }),
      "GET /services?limit=20&offset=20": servicePage(rows(20, 20), { total: 45, offset: 20 }),
    });
    expect(await screen.findByText("Showing 20 of 45")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show more" }));
    expect(await screen.findByText("Showing 40 of 45")).toBeInTheDocument();
    expect(listRequests(api).map((r) => r.path)).toEqual(["/services?limit=20&offset=0", "/services?limit=20&offset=20"]);
    expect(screen.getByText("Service 40")).toBeInTheDocument();
  });

  it("opens a service into the builder at once when the draft has nothing unsaved", async () => {
    const { user, api } = renderServices(testDraft(), {
      "GET /services": servicePage([serviceSummary()]),
      [`GET /services/${SERVICE_ID}`]: savedService(),
    });
    await user.click(await screen.findByRole("button", { name: /World Communion Sunday/ }));
    await waitFor(() => expect(testRouter.push).toHaveBeenCalledWith("/builder/review"));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(api.requests.filter((r) => r.path === `/services/${SERVICE_ID}`)).toHaveLength(1);
    expect(stored()).toMatchObject({
      last_step: "review",
      editing: { service_id: SERVICE_ID, date_iso: "2026-10-04" },
      readings: { occasion: "World Communion Sunday", fields_origin: "archive" },
    });
  });

  it("asks before replacing unsaved work, and a service gone from the archive says so and refreshes the list", async () => {
    const { user, api } = renderServices(editOccasion(testDraft(), "Harvest"), {
      "GET /services": servicePage([serviceSummary()]),
      [`GET /services/${SERVICE_ID}`]: fakeError(404, "not_found", GONE),
    });
    await user.click(await screen.findByRole("button", { name: /World Communion Sunday/ }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your unsaved draft?" });
    expect(dialog).toHaveTextContent(
      "Your current draft for October 4, 2026 has changes that aren't saved to the archive. Opening this service replaces it.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Replace draft" }));
    expect(await screen.findByText(GONE)).toBeInTheDocument();
    await waitFor(() => expect(listRequests(api)).toHaveLength(2));
    expect(testRouter.push).not.toHaveBeenCalled();
    expect(stored().readings.occasion).toBe("Harvest");
  });

  it("deletes after asking, for everyone in the church; deleting the service being edited clears the draft", async () => {
    let deleted = false;
    const { user, api } = renderServices(serviceToDraft(savedService(), { church: churchProfile(), user: { id: USER_ID } }), {
      "GET /services": () => servicePage(deleted ? [] : [serviceSummary()]),
      [`DELETE /services/${SERVICE_ID}`]: () => {
        deleted = true;
        return { deleted: true };
      },
    });
    const row = (await screen.findByRole("button", { name: /World Communion Sunday/ })).closest("li") as HTMLElement;
    expect(within(row).getByText("Editing")).toBeInTheDocument();
    await user.click(within(row).getByRole("button", { name: "More actions for October 4, 2026" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete this service?" });
    expect(dialog).toHaveTextContent(
      "“World Communion Sunday” on October 4, 2026 will be removed from the archive for everyone in Grace. This can't be undone. " +
        "You're editing this service. Your current draft will be cleared too.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Delete service" }));
    expect(await screen.findByText("No saved services yet")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(api.requests.filter((r) => r.method === "DELETE")).toHaveLength(1);
    expect(stored().editing).toBeNull();
    expect(stored().readings.occasion).toBe("");
  });

  it("names an untitled, undated service, and a delete that finds it gone says so", async () => {
    const undated = serviceSummary({ service_date_iso: null, service_date: "", occasion: "" });
    const { user, api } = renderServices(testDraft(), {
      "GET /services": servicePage([undated]),
      [`DELETE /services/${SERVICE_ID}`]: fakeError(404, "not_found", GONE),
    });
    await user.click(await screen.findByRole("button", { name: "More actions for No date" }));
    await user.click(await screen.findByRole("menuitem", { name: "Delete…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete this service?" });
    expect(dialog).toHaveTextContent(
      "“Untitled service” (no date) will be removed from the archive for everyone in Grace. This can't be undone.",
    );
    expect(dialog).not.toHaveTextContent("You're editing");
    await user.click(within(dialog).getByRole("button", { name: "Delete service" }));
    expect(await screen.findByText(GONE)).toBeInTheDocument();
    await waitFor(() => expect(listRequests(api)).toHaveLength(2));
  });
});
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/services/services-page.test.tsx src/components/app/app-header.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")
```

**Expected:** one failure and `services-page.test.tsx` cannot load (the route does not exist yet):
```
   × AppHeader > shows the Builder and Services nav items on church pages, current under /builder, and no nav without churches (F §4.2) <t>ms
 FAIL  |dom| src/components/services/services-page.test.tsx [ src/components/services/services-page.test.tsx ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
      Tests  1 failed | 5 passed (6)
```

- [ ] **Step 3 (agent): The route, the page, the row, the menu item**

**Create `frontend/src/app/(signed-in)/(church)/services/page.tsx`:**

````tsx
"use client";

import { ServicesPage } from "@/components/services/services-page";

/** Services: the church's saved services (slice 5a spec, "Services page"; F §4.1). */
export default function ServicesRoute() {
  return <ServicesPage />;
}
````

**In `frontend/src/components/app/app-nav.tsx`, replace:**

````tsx
/** Nav items in order; each appears once its slice ships (F §4.2). 5a adds "Services", 5b or 6a "Settings". */
export const NAV_ITEMS = [{ href: "/builder", label: "Builder" }] as const;
````

**with:**

````tsx
/** Nav items in order; each appears once its slice ships (F §4.2): "Services" from 5a-3; 5b or 6a adds "Settings". */
export const NAV_ITEMS = [
  { href: "/builder", label: "Builder" },
  { href: "/services", label: "Services" },
] as const;
````

**Create `frontend/src/components/services/service-row.tsx`:**

````tsx
"use client";

import { EllipsisVerticalIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import type { ServiceSummary } from "@/lib/api/types";
import { formatSavedAt, formatServiceDate } from "@/lib/dates";
import { cn } from "@/lib/utils";

/** A row's first line: the service date ("October 4, 2026"), else the stored date text, else "No date". */
export function serviceDateLabel(s: ServiceSummary): string {
  if (s.service_date_iso) return formatServiceDate(s.service_date_iso) || s.service_date_iso;
  return s.service_date.trim() || "No date";
}

/** A row's third line: who first saved it (it never changes) and when it was last saved. */
export function savedByLine(s: ServiceSummary): string {
  const at = formatSavedAt(s.saved_at);
  return s.created_by ? `Created by ${s.created_by.name} · last saved ${at}` : `Last saved ${at}`;
}

/**
 * One saved service (slice 5a spec, "Services page" List): the date, the
 * occasion, who created it and when it was last saved, "Editing" when the
 * draft is this service. The row opens it ("Opening…" while it loads); the
 * menu beside it holds "Delete…". Both are 44 px tall.
 */
export function ServiceRow({
  service,
  editing,
  opening,
  disabled,
  onOpen,
  onDelete,
}: {
  service: ServiceSummary;
  editing: boolean;
  opening: boolean;
  disabled: boolean;
  onOpen: () => void;
  onDelete: () => void;
}) {
  const date = serviceDateLabel(service);
  return (
    <li className="flex items-start gap-1 rounded-lg border">
      <button
        type="button"
        onClick={() => onOpen()}
        disabled={disabled}
        aria-busy={opening || undefined}
        className="grid min-h-11 min-w-0 flex-1 gap-0.5 rounded-lg p-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
      >
        <span className="flex flex-wrap items-center gap-2 font-medium">
          {date}
          {editing ? <Badge variant="secondary">Editing</Badge> : null}
        </span>
        <span className="wrap-anywhere text-sm">{service.occasion.trim() || "No occasion"}</span>
        <span className="text-xs text-muted-foreground">{opening ? "Opening…" : savedByLine(service)}</span>
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={`More actions for ${date}`}
          disabled={disabled}
          className={cn(buttonVariants({ variant: "ghost", size: "icon-lg" }), "m-1 size-11 shrink-0")}
        >
          <EllipsisVerticalIcon aria-hidden="true" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-auto min-w-36">
          <DropdownMenuItem variant="destructive" className="min-h-11 md:min-h-0" onClick={() => onDelete()}>
            Delete…
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
}
````

**Create `frontend/src/components/services/services-page.tsx`:**

````tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { PageHeader } from "@/components/app/page-header";
import { PendingButton } from "@/components/app/pending-button";
import { useNewService } from "@/components/builder/new-service-menu-item";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ChurchProfile, ServiceSummary } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { formatServiceDate } from "@/lib/dates";
import { DraftProvider, useDraft } from "@/lib/draft/context";
import { isDirty } from "@/lib/draft/status";
import { useMeContext } from "@/lib/me-context";
import { useChurchProfile } from "@/lib/queries/church";
import { useDeleteService, useOpenService, useServices } from "@/lib/queries/services";

import { serviceDateLabel, ServiceRow } from "./service-row";

/** The delete question's text (slice 5a spec, "Delete flow"). */
export function deleteDescription(s: ServiceSummary, churchName: string, editing: boolean): string {
  const name = `“${s.occasion.trim() || "Untitled service"}”`;
  const when = serviceDateLabel(s) === "No date" ? " (no date)" : ` on ${serviceDateLabel(s)}`;
  const text = `${name}${when} will be removed from the archive for everyone in ${churchName}. This can't be undone.`;
  return editing ? `${text} You're editing this service. Your current draft will be cleared too.` : text;
}

function ListSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="grid gap-2">
      {[0, 1, 2, 3, 4].map((i) => (
        <Skeleton key={i} className="h-20 w-full" />
      ))}
    </div>
  );
}

/**
 * `/services` (slice 5a spec, "Services page"; F §4.1, §4.8): the church's
 * saved services, 20 at a time, newest service date first, and "New
 * service". The page has its own `DraftProvider` (the builder's is not
 * mounted here), so a row shows "Editing" for the service the draft holds,
 * opening a service replaces the draft (after "Replace your unsaved draft?"
 * when there is something to lose) and the builder then opens on Review, and
 * deleting the service being edited clears the draft. Every delete asks
 * first and is open to any member (owner decision 5).
 */
export function ServicesPage() {
  const me = useMeContext();
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  return (
    <main className="mx-auto grid w-full max-w-2xl content-start gap-4 px-4 py-4">
      {profile.data ? (
        <DraftProvider key={`${me.user.id}:${church.id}`} userId={me.user.id} church={profile.data}>
          <ServicesArchive church={profile.data} />
        </DraftProvider>
      ) : (
        <ListSkeleton />
      )}
    </main>
  );
}

function ServicesArchive({ church }: { church: ChurchProfile }) {
  const { draft } = useDraft();
  const router = useRouter();
  const list = useServices();
  const open = useOpenService(church);
  const remove = useDeleteService(church);
  const newService = useNewService(church);
  const newButton = useRef<HTMLButtonElement>(null);
  const [replacing, setReplacing] = useState<ServiceSummary | null>(null);
  const [deleting, setDeleting] = useState<ServiceSummary | null>(null);
  const [opening, setOpening] = useState<string | null>(null);
  const editingId = draft.editing?.service_id ?? null;
  const draftDate = formatServiceDate(draft.readings.date_iso);

  function openNow(s: ServiceSummary) {
    setReplacing(null);
    setOpening(s.id);
    open.mutate(s.id, {
      onSuccess: () => router.push("/builder/review"),
      onSettled: () => setOpening(null),
    });
  }

  const items = list.data?.pages.flatMap((page) => page.items) ?? [];
  const total = list.data?.pages.at(-1)?.total ?? 0;

  let body;
  if (list.isPending) body = <ListSkeleton />;
  else if (list.isError && !list.data) body = <ErrorState error={list.error} onRetry={() => void list.refetch()} retrying={list.isRefetching} />;
  else if (items.length === 0) {
    body = (
      <EmptyState
        title="No saved services yet"
        description="Services you save from the builder appear here."
        action={
          <Link href="/builder" className={buttonVariants({ size: "touch" })}>
            Build a service
          </Link>
        }
      />
    );
  } else {
    body = (
      <>
        <ul className="grid gap-2">
          {items.map((s) => (
            <ServiceRow
              key={s.id}
              service={s}
              editing={s.id === editingId}
              opening={opening === s.id}
              disabled={opening !== null}
              onOpen={() => (isDirty(draft) ? setReplacing(s) : openNow(s))}
              onDelete={() => setDeleting(s)}
            />
          ))}
        </ul>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">
            Showing {items.length} of {total}
          </p>
          {list.hasNextPage ? (
            <PendingButton
              variant="outline"
              size="touch"
              pending={list.isFetchingNextPage}
              pendingLabel="Loading…"
              onClick={() => void list.fetchNextPage()}
            >
              Show more
            </PendingButton>
          ) : null}
        </div>
        {list.isFetchNextPageError ? <ErrorState error={list.error} onRetry={() => void list.fetchNextPage()} /> : null}
      </>
    );
  }

  return (
    <>
      <PageHeader
        title="Services"
        description={`Saved services for ${church.name}.`}
        actions={
          <Button ref={newButton} size="touch" onClick={() => newService.start()}>
            New service
          </Button>
        }
      />
      {body}
      <ConfirmDialog
        open={replacing !== null}
        onOpenChange={(next) => {
          if (!next) setReplacing(null);
        }}
        title="Replace your unsaved draft?"
        description={`Your current draft${draftDate ? ` for ${draftDate}` : ""} has changes that aren't saved to the archive. Opening this service replaces it.`}
        confirmLabel="Replace draft"
        onConfirm={() => {
          if (replacing) openNow(replacing);
        }}
        destructive
      />
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(next) => {
          if (!next && !remove.isPending) setDeleting(null);
        }}
        title="Delete this service?"
        description={deleting ? deleteDescription(deleting, church.name, deleting.id === editingId) : undefined}
        confirmLabel="Delete service"
        pending={remove.isPending}
        onConfirm={() => {
          if (deleting) remove.mutate(deleting.id, { onSettled: () => setDeleting(null) });
        }}
        finalFocus={newButton}
        destructive
      />
      {newService.dialog}
    </>
  );
}
````

- [ ] **Step 4 (agent): Run the files three times, the suite, the types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/components/services/services-page.test.tsx src/components/app/app-header.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests "); done
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** three times `      Tests  14 passed (14)`; ` Test Files  83 passed (83)` and `      Tests  645 passed (645)` with no `×` or `FAIL` line; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add 'frontend/src/app/(signed-in)/(church)/services/page.tsx' frontend/src/components/services/services-page.tsx frontend/src/components/services/service-row.tsx frontend/src/components/services/services-page.test.tsx frontend/src/components/app/app-nav.tsx frontend/src/components/app/app-header.test.tsx
git commit -q -m "Services page: the saved services, open and delete; Services in the menu (5a-3; owner answer 6)" -m "/services lists the church's saved services, 20 at a time, newest
service date first, with who created each and when it was last saved,
Editing on the one the draft holds, Show more, and the empty, loading and
error states. A tap opens a service into the builder on Review (after
Replace your unsaved draft? when there is something to lose); Delete...
asks first, refreshes the list and the hymns, and clears the draft when
it held that service. The menu gains Services." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 5: frontend **645 in 83**; backend **1335 passed, 16 skipped**.

### Task 6: Docs: S's amendment, F's index row, the manual check items (owner answers 2026-10-01/02; clarification 22)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, `docs/manual-verification.md`

- [ ] **Step 1 (agent): Write the docs**

**Append to `docs/manual-verification.md`:**

````markdown

Slice 5a-3 adds the Save card on **4 Review & send** and the **Services**
page. The owner's guided check after the merge (five steps on the phone)
covers the items marked "(owner, after 5a-3)"; its result goes into
`docs/ops-runbook.md` → "Slice 5a-3 record".

- [ ] (owner, after 5a-3) **12.** On **4 Review & send**, tap **Save to archive**: "Service saved", and the card says "Saved to the archive · {date and time}". **Services** in the menu lists the service at its date, with "Editing". After an edit the card says "Unsaved changes · last saved …" and the button "Save changes"; saving again says "Saved to the archive" with the new time.
- [ ] (owner, after 5a-3) **13.** **Start a new service**, date it a week after the saved service (a service's own date is never marked), then on **2 Hymns**: the saved service's hymns are marked as recently used.
- [ ] (owner, after 5a-3) **14.** On **Services**, open the saved service (after "Replace your unsaved draft?" if the draft has changes): Review shows "You're editing the saved service for {date}. …"; step 1 shows the saved occasion and readings, with no "Readings for … are available". Change the date: the button reads "Save as new service" and says why.
- [ ] (owner, after 5a-3) **15.** Save that copy, then delete it from **Services** ("Delete this service?", "Delete service"): it leaves the list, and if it was the one being edited the draft starts fresh.
- [ ] (owner, after 5a-3) **16.** At 375 px: no sideways scroll on **Review & send** or **Services**; the buttons and rows are easy to tap.
- [ ] **17.** In a second browser with the same service open, save it in one, then "Save changes" in the other: "Someone else changed this service"; "Reload their version" and "Save mine as a new service" both work.
````

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

````markdown
| §1.8, §2.8 | *(2026-10-01, service reviewer plan, owner answer 3)* The client timeouts for `POST /liturgy/review` and `POST /liturgy/revise` are 100 000 ms (`ENDPOINT_TIMEOUTS`), as the 4b row said. Review passes a 75 s deadline from the start of its usecase and a 70 s attempt timeout to its one `complete()` call, so it answers within 75 s plus the last 5 s connect, about 80 s; revise reuses generation's 80 s deadline and the section's attempt timeout (60 s for Prayers of the People), so it answers within 85 s. Revise's prompt-size 422 has no `fields`; a review whose church text is too long even with every card cut to 200 characters skips the AI and answers `ai_status: "error"`, never `prompt_invalid`; it logs `dropped=too_long`, and for that church it persists until its saved system prompt or checklists are shortened. | reviewer |

````

**with:**

````markdown
| §1.8, §2.8 | *(2026-10-01, service reviewer plan, owner answer 3)* The client timeouts for `POST /liturgy/review` and `POST /liturgy/revise` are 100 000 ms (`ENDPOINT_TIMEOUTS`), as the 4b row said. Review passes a 75 s deadline from the start of its usecase and a 70 s attempt timeout to its one `complete()` call, so it answers within 75 s plus the last 5 s connect, about 80 s; revise reuses generation's 80 s deadline and the section's attempt timeout (60 s for Prayers of the People), so it answers within 85 s. Revise's prompt-size 422 has no `fields`; a review whose church text is too long even with every card cut to 200 characters skips the AI and answers `ai_status: "error"`, never `prompt_invalid`; it logs `dropped=too_long`, and for that church it persists until its saved system prompt or checklists are shortened. | reviewer |
| §4.2, §4.6, §4.7 | *(2026-10-02, slice 5a-3 plan)* The draft is version 2 (`editing.date_iso`, `save_key_fingerprint`, with its migration); `replace` writes the draft at once, so a page outside the builder (Services) can replace it and open the builder; `isDirty` lives in `status.ts` with `reviewStatus` and `saveMode`. Review ships (`SHIPPED_STEPS` holds all four steps): the step bar shows "Not in archive", "Saved" or "Unsaved changes", and the summary's status line links to Review with the archive half. After a save, a Benediction or communion that followed its default is the saved service's own (origin "archive", owner answer 4). The nav gains "Services". | 5a |

````

**Append to `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`:**

````markdown

## Amendment 2026-10-02: 5a-3 as planned (the Save card and the Services page)

Plan: `docs/superpowers/plans/2026-10-02-slice-5a3-save-services.md`. The owner's answers of 2026-10-01/02 stand: 4 (a save keeps a Benediction that followed the church default, and the communion setting, as saved), 5 (no "Readings for … are available" while the date is still the saved service's date), 9 (reviewer notes stay in memory: opening a saved service clears them, saving keeps them), 2 (no order-of-worship card), 8 (a guided phone check after the PR). No backend change and no migration. Where this spec says otherwise, 5a-3 does this:

1. **Review & send, top to bottom:** the editing banner (only while the draft is a saved service), "Still to do", the Archive card, the Word documents. No order-of-worship card and no email card (5b). The banner does not repeat the hymns that are not in the hymnal: "Still to do" lists each one ("{Title} isn't in your hymnal", linking "Choose a replacement" to Hymns). "Still to do" shows "Everything's ready." when nothing is missing. The component keeps 4b's name (`StillNeeded`, `still-needed.tsx`) and `status.ts` keeps `stillNeeded` (S's `ReviewChecklist`, `missingItems`).
2. **Save sends the downloads' body** (`serviceBody` in `lib/documents.ts`), kept within the server's limits, so a save never meets a 422 for a length; a stored custom element longer than today's limits is saved cut to the limit, as the Word file already prints it. Save is off only without a service date or while a Date & readings field shows its message ("Choose a service date on step 1 to save.", "Fix the readings on step 1 to save."), as the downloads are; it is on when nothing changed (F D9).
3. **After a save** a Benediction that followed the church default and communion that followed the first-Sunday rule become the saved service's own (origin "archive"), as when a saved service is opened (owner answer 4). The Liturgy step then shows "Set from the saved service." with "Use default" for communion.
4. **"Start a new service"** runs New service's flow and question ("Start a new service?", "This clears the current draft on this device.", "Start new service"), not this spec's own copy, so both doors ask the same thing.
5. **Opening a saved service** always fetches it (`GET /services/{id}`) and prefetches nothing: the builder's lectionary lookup runs on every step. A service deleted elsewhere while it is open stays in the draft; "Save changes" then saves it as a new service and says so.
6. **The Services page** renders its own draft provider (the builder's is not mounted there), and the draft store now writes a replaced draft at once (New service, opening, the reset after a delete), so the builder it opens reads it. Rows open on a tap; "Delete…" is in the row's menu.
7. **The draft is version 2** (`editing.date_iso`, `save_key_fingerprint`); the names `DraftV1` and `draftV1Schema` stay. `isDirty` moved from `fingerprint.ts` to `status.ts`, beside `reviewStatus` and `saveMode`.
8. **A replayed `POST /services` answer may be stale** (5a-2 plan, clarification 4); there is no special handling: a later "Save changes" meets the 409 or the deleted-copy 404, which already handle it.
````

- [ ] **Step 2 (agent): Check the docs tests and the suites**

```bash
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
grep -c "—" <(git diff -U0 -- docs | grep '^+' | grep -v '^+++')
git diff --stat | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `89 passed in <t>s`; `4`; `0` (no em dash added); `3 files changed, 26 insertions(+)`; `1335 passed, 16 skipped in <t>s`.

- [ ] **Step 3 (agent): Commit**

```bash
git add docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md docs/superpowers/specs/2026-09-25-migration-foundations-design.md docs/manual-verification.md
git commit -q -m "Docs: slice 5a-3 as planned, and its manual check items (owner answers 2026-10-01/02)" -m "The 5a spec gains 'Amendment 2026-10-02: 5a-3 as planned' (the Review
order, Still to do, Save sends the downloads' body, a save keeps a
default Benediction and communion, Start a new service is New service's
flow, the Services page's own draft provider, draft version 2). The
foundations index gains its row. docs/manual-verification.md gains items
12-17 for 5a-3." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 4 (controller): Review the batch (T1-T6) and backup push**

One review of the whole batch: the draft migration and the save key exactly as clarifications 10 and 19; `serviceToDraft` and `markSaved` as clarification 6 and S; "Saved" means the payload equals the last one saved or opened; the save's request order and every outcome in clarifications 9-12 (PUT with `If-Match` and no key; POST with the draft's key; the fallback; one mismatch retry; no toast after a 401 or a lost church, none of its own for a 409); the invalidations of clarification 20; the Services page opens and deletes as clarifications 15-16; the copy exactly clarification 18, no em dash; 44 px targets, wrapping at 375 px, the names and descriptions of clarification 21; no backend, API or migration file touched. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

Counts after Task 6: frontend **645 in 83**; backend **1335 passed, 16 skipped**.

### Task 7: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
git merge-base --is-ancestor a789fb8 origin/main; echo "5a-2 record on main: $?"
ls backend/migrations/versions | grep -c '^0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `5a-2 record on main: 1` (it rides along: Step 3's list has `M docs/ops-runbook.md`; `0` if a records PR merged it meanwhile, and then that line is absent); `5`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 7)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the frontend three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/services")
```

**Expected:** `1335 passed, 16 skipped in <t>s`; three times ` Test Files  83 passed (83)` and `      Tests  645 passed (645)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s`, a route line for `/services` and no `Error` (a font `Failed to fetch` only: say so and rely on CI).

- [ ] **Step 3 (agent): The API files unchanged, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend .github frontend/package.json frontend/package-lock.json frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the API did not change); `raw html grep exit 1`; exactly these 46 paths (without `M docs/ops-runbook.md` when Step 1 printed `0`, and without the idea doc if it reached `main` another way):
```
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-02-slice-5a3-save-services.md
M	docs/superpowers/specs/2026-09-25-migration-foundations-design.md
M	docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md
A	docs/superpowers/specs/2026-10-02-pew-voices-idea.md
M	frontend/src/app/(signed-in)/(church)/builder/review/page.tsx
A	frontend/src/app/(signed-in)/(church)/services/page.tsx
M	frontend/src/components/app/app-header.test.tsx
M	frontend/src/components/app/app-nav.tsx
M	frontend/src/components/builder/builder-shell.test.tsx
M	frontend/src/components/builder/new-service-menu-item.tsx
A	frontend/src/components/builder/review/conflict-dialog.tsx
M	frontend/src/components/builder/review/documents-card.tsx
A	frontend/src/components/builder/review/editing-banner.tsx
M	frontend/src/components/builder/review/review-send-step.test.tsx
M	frontend/src/components/builder/review/review-send-step.tsx
A	frontend/src/components/builder/review/save-card.tsx
M	frontend/src/components/builder/step-progress.tsx
M	frontend/src/components/builder/still-needed.tsx
M	frontend/src/components/builder/summary-panel.tsx
A	frontend/src/components/services/service-row.tsx
A	frontend/src/components/services/services-page.test.tsx
A	frontend/src/components/services/services-page.tsx
M	frontend/src/lib/api/types.ts
M	frontend/src/lib/dates.test.ts
M	frontend/src/lib/dates.ts
M	frontend/src/lib/documents.ts
M	frontend/src/lib/draft/fingerprint.test.ts
M	frontend/src/lib/draft/fingerprint.ts
M	frontend/src/lib/draft/mapping.test.ts
M	frontend/src/lib/draft/mapping.ts
M	frontend/src/lib/draft/migrate.test.ts
M	frontend/src/lib/draft/migrate.ts
M	frontend/src/lib/draft/readings.ts
A	frontend/src/lib/draft/save-key.test.ts
A	frontend/src/lib/draft/save-key.ts
M	frontend/src/lib/draft/schema.test.ts
M	frontend/src/lib/draft/schema.ts
M	frontend/src/lib/draft/status.test.ts
M	frontend/src/lib/draft/status.ts
M	frontend/src/lib/draft/steps.ts
M	frontend/src/lib/draft/store.test.ts
M	frontend/src/lib/draft/store.ts
A	frontend/src/lib/queries/services.ts
M	frontend/src/test/fixtures/index.ts
```
`0` (no backend, workflow, package, API snapshot or Streamlit path); the subjects oldest first: `Runbook: slice 5a-2 record (merged; 0005 on production; owner's checks)` (unless on `main`), then in branch order `WIP plan: slice 5a-3`, `Docs: Hear it from the pews idea (owner, 2026-10-02)`, `Docs: Hear it from the pews goes after 6a (owner, 2026-10-02)`, `WIP plan: slice 5a-3`, `Plan: slice 5a-3, Save and the Services page (owner answers 2026-10-01/02)` and its follow-up, then T1-T6's six subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** one `✓ Logged in` line; `[]`. Send the owner exactly this, and wait for a clear yes:

> Slice 5a-3 (the Save card and the Services page) is verified on this machine: frontend 645 tests in 83 files (618 in 81 before), three runs in a row; backend 1335 passed, 16 skipped, unchanged (no backend change in this PR); typecheck, lint and the production build are clean. On step 4 you get Save to archive, Save changes or Save as new service, Start a new service, and a dialog when someone else saved first; the menu gains Services, where you open or delete saved services. Saving records the hymns as used. No database change. May I open the pull request as a **draft** titled "Slice 5a-3: the Save card and the Services page", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/slice5a3-pr-body.md" <<'BODY'
Slice 5a-3: the Save card and the Services page (the last of three 5a PRs; owner answers of 2026-10-01/02). Plan: docs/superpowers/plans/2026-10-02-slice-5a3-save-services.md. Frontend only: no backend change, no migration, no new variable. The 5a-2 runbook record and the "Hear it from the pews" idea doc ride along.

- Review & send: a banner while the draft is a saved service; Still to do (renamed from Still needed, with Everything's ready. and a row per hymn not in the hymnal); the Archive card (Save to archive / Save changes / Save as new service with why; Start a new service); the Word documents with a save tip. A 409 opens "Someone else changed this service" (Reload their version, Save mine as a new service, Cancel); a deleted saved copy is saved as new, with a toast; a hymn the church no longer has offers Go to Hymns.
- A save keeps a default-following Benediction and communion as saved (owner answer 4); no "Readings for ... are available" while the date is the saved date (owner answer 5); reviewer notes stay on save and go on open (owner answer 9).
- Services (new menu item): 20 a page, newest service date first; open into the builder (with "Replace your unsaved draft?" when needed); delete after confirming (hymn use recalculated by the server).
- Draft version 2 (editing.date_iso, save_key_fingerprint) with a tested migration; the save key rule (F 1.6) in lib/draft/save-key.ts; serviceToDraft and the final draftToServicePayload; the step bar and summary show Saved or Unsaved changes.
- The 5a spec gains its 5a-3 amendment; manual-verification items 12-17.

Tests: backend 1335 → 1335 passed, 16 → 16 skipped; frontend 618 → 645 in 81 → 83 files

After merge (Task 8): a guided five-step check on the owner's phone, then a "Slice 5a-3 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 5a-3: the Save card and the Services page" \
  --body-file "<scratch>/slice5a3-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1335 passed, 16 skipped`, backend-postgres `16 passed, 1335 deselected`, frontend `645 passed` in 83 files. Then send: "PR #<N> is green: 645 frontend tests in 83 files; the backend is unchanged at 1335 passed; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `save-key.test.ts`, `migrate.test.ts`, `schema.test.ts`, `store.test.ts` | T1 |
| `mapping.test.ts`, `status.test.ts`, `fingerprint.test.ts`, `readings.test.ts`, `documents.test.ts` (the payload) | T2 |
| `dates.test.ts`, `dates.guard.test.ts` | T3 |
| `review-send-step.test.tsx`, `builder-shell.test.tsx`, `church-switch.test.tsx`, `liturgy-step.test.tsx` | T4 |
| `services-page.test.tsx`, `app-header.test.tsx` | T5 |
| `test_slice1_docs.py`, `test_docs.py` | T6 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, 5a-3 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: frontend `645 passed` in 83 files; backend `1335 passed, 16 skipped`.

### Task 8: Merge, the owner's guided phone check (five steps), the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate (production stays at `0005_services_extras`); Vercel serves the new screens. The owner's check is **one step at a time** (send one, wait for the report or "next"), on the phone, on the production URL, in the owner's own church. It saves one copy of a real service and deletes it again (steps 4-5), so nothing is left behind but the owner's own saves. The agent writes each result into `<scratch>/slice5a3-t8-results.md` (not committed). Record what the screens showed, never a token, an email address or a church id.

**Files:** Modify (the records PR, Step 8): `docs/ops-runbook.md`: insert `### Slice 5a-3 record` right after the "Slice 5a-2 record" table (its last row starts `| Follow-ups | Next: 5a-3 (Save card and Services page;`) and before `## Backups`. A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (slice 5a-3, the Save card and the Services page) is ready, green and up to date with main. There is no database change. Then I will ask you for five short checks on your phone, one at a time. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about two minutes for Vercel before Step 2.

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 5: save a service (manual-verification item 12)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it (or close and reopen the tab), so the phone runs the new version; if you have the app open on another device, reload it there too. Build a service as you normally would, or keep the one you have: a date, readings, hymns, liturgy and a sermon title. Tap **4 Review & send**. Under **Archive** it should say "Not in the archive yet." Tap **Save to archive**: you should see "Service saved", and the card should say "Saved to the archive · " with today's date and time. Then tap **Services** in the menu at the top: is your service listed at its date, with "Created by" your name and an "Editing" badge?

Record the messages and what Services showed. A "We couldn't restore your unsaved draft." message after the reload is the old-tab case (Risks): record it; the draft is backed up and the check can go on.

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 5: save changes (item 12)**

> From **Services**, tap **Builder**, go to **3 Liturgy** and change something small, for example the sermon title. Back on **4 Review & send**, the card should say "Unsaved changes · last saved …" and the button "Save changes". Tap it: "Service saved", and the time moves on. Does it?

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 5: the hymns now count as used (item 13)**

> On **4 Review & send**, tap **Start a new service** (it starts at once, since everything is saved). On **1 Date & readings**, set the date to one week after the service you saved (the marks never count a service's own date). Then go to **2 Hymns**: are the hymns of the service you just saved marked as recently used ("Used …" with its date)?

Record what the marks showed. This is the first time the app itself records hymn use.

- [ ] **Step 5 (OWNER, then agent): Phone, step 4 of 5: open the saved service and save a copy (item 14)**

> Tap **Services**, then tap your saved service. If the app asks "Replace your unsaved draft?", tap **Replace draft**. It should open on **4 Review & send** with "You're editing the saved service for {its date}. Changes stay on this device until you save." Go to **1 Date & readings**: are the occasion and readings the ones you saved, with no "Readings for … are available" box? Now change the date to the following Sunday and come back to **4 Review & send**: the button should read **Save as new service**, with a sentence saying why. Tap it. On **Services**, are both services listed now, the copy on the new date?

- [ ] **Step 6 (OWNER, then agent): Phone, step 5 of 5: delete the copy, and the layout (items 15, 16)**

> On **Services**, tap the **⋮** button on the copy's row (the one on the following Sunday), then **Delete…**. The question "Delete this service?" names it and your church and says it can't be undone; since you are editing it, it also says your current draft will be cleared. Tap **Delete service**: the row should go, and the original stays. Last: on **Services** and on **4 Review & send**, does everything fit the screen with no sideways scrolling, and are the rows and buttons easy to tap?

- [ ] **Step 7 (agent): Fill the results, then write the record**

Write each step's result, with the date, into `<scratch>/slice5a3-t8-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now. Then (not replayed):

```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^### Slice 5a-2 record$\|^| Follow-ups | Next: 5a-3 (Save card and Services page;\|^## Backups$' docs/ops-runbook.md
```

**Expected:** `Fast-forward` (or `Already up to date.`); three lines in that order. Insert, between that last row and `## Backups` (one blank line on each side):

```markdown
### Slice 5a-3 record

Slice 5a-3 (saving from the app: the Archive card on Review & send with
Save to archive, Save changes and Save as new service, the conflict dialog
and the editing banner; the Services page to open and delete saved
services; the draft's version 2) merged as PR #<N>, the last of the three
5a PRs (owner answers of 2026-10-01/02). Frontend only: no backend change
and no migration (production stays at `0005_services_extras`). From this
merge, saving a service records its hymns as used for its date. The
owner's check was five steps on a phone, covering the "(owner, after
5a-3)" items of `docs/manual-verification.md` → "Slice 5a". No token,
email address or church id is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success | <date> |
| 1. Save (phone: <phone and browser>) | <"Not in the archive yet.", then "Service saved" and "Saved to the archive · <time>"; Services listed it at its date with "Created by" and "Editing". / …> | <date> |
| 2. Save changes | <"Unsaved changes · last saved …", then "Save changes" saved with a new time. / …> | <date> |
| 3. Hymn use | <After Start a new service, dated a week later, the Hymns step marked the saved hymns as recently used. / …> | <date> |
| 4. Open and save a copy | <Opened on Review with the editing banner; step 1 showed the saved readings and no "Readings for … are available"; on the next Sunday the button read "Save as new service" with why; both services listed. / …> | <date> |
| 5. Delete and layout | <The copy was deleted after "Delete this service?" (with the draft line); the original stayed; no sideways scroll; easy to tap. / …> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: 5b (email), the printed bulletin (`docs/superpowers/specs/2026-10-02-printed-bulletin-idea.md`), Voices of the Church, 6a. Still open: the screen-reader copy for "Revise the other prayers", first-line matching research (Hymnary.org), the NUL-character 500 outside `/documents`, and the two slice 1 test churches (kept for now, owner) | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Then (not replayed):

```bash
sed -n '/^### Slice 5a-3 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 5a-3 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 5a-3 record (merged; owner's phone check)" -m "Records slice 5a-3 (PR #<N>): the merge and CI on main, and the owner's
five-step phone check (save, save changes, hymn use, open and save a
copy, delete and the layout). No token, email or church id is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 8 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 5a-3 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 5a-3 record" \
  --body "Records slice 5a-3 (PR #<N>) in docs/ops-runbook.md → Slice 5a-3 record: the merge and the owner's five-step phone check. No token, email or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Slice 5a-3 is live and recorded; <n> follow-ups. 5a is complete. Next: 5b (email)."

- [ ] **Step R (only if the release must come out): Revert**

Code only (no data or schema to undo: the services saved and the hymn use recorded meanwhile stay in the archive, where 5a-2's routes keep them). On the owner's yes for each outward command: a branch `claude/revert-slice-5a3` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert slice 5a-3 (PR #<N>)" with the trailer, both suites (`1335 passed, 16 skipped`; `618 passed` in 81), a PR, CI, and the merge on the owner's yes; record it in the 5a-3 record. Tell the owner first: the reverted app reads drafts as version 1, so each browser's current draft (version 2) is not restored once ("We couldn't restore your unsaved draft."; the raw value stays in `wsb:draft-corrupt:…`); saved services are unaffected. Review then shows the "Saving services to the archive is coming soon." note again.

Expected counts after this task: frontend `645 passed` in 83 files on `main`; backend `1335 passed, 16 skipped`. The records PR adds no test.

---
## Build notes

**How this plan was written (2026-10-02).** Each task's code was built and run in a throwaway worktree of `a789fb8` (the repo's `.venv`, a hard-linked copy of `frontend/node_modules`), one commit per task; the directives were then generated from those commits (a new file as **Create**, `mapping.ts` whole, the docs' additions as **Append**, every other change as **In … replace** with just enough context to occur once in the file as it stands at that point) and replayed onto a fresh worktree of the branch head by a script that applies each task's Step 1 and Step 3 directives by their line ranges and runs that task's commands. While building:
- **`isDirty` moved to `status.ts`.** `reviewStatus` belongs in `status.ts` beside `stepStatus`, and needs `isDirty`, but `fingerprint.ts` (where `isDirty` was) imports `status.ts` for `isPristine`; moving it leaves `fingerprint.ts` with no imports and no cycle.
- **`replace` writes at once.** With the Services page's own provider, the builder it opens built its store from storage while the Services page's store still held the opened service in its 400 ms write delay (React renders the new route before the old one unmounts and flushes), so the builder showed the old draft. Writing on `replace` fixes it for New service and the delete reset too (T1 "replace writes at once, …").
- **The summary's status line is one link.** Splitting it into text and a link broke `getByText("Draft saved on this device · Not in archive")` in 2b's and 3b's tests (Testing Library matches one element's own text); the whole line links to Review instead, which also gives a bigger target.
- **Toasts between tests.** sonner replays a toast still showing to the next `Toaster`, so a second test found "Service saved" twice; `review-send-step.test.tsx` and `services-page.test.tsx` call `toast.dismiss()` after each test, as `liturgy-step.test.tsx` does before each.
- **`isConflict` returns a boolean, not a type guard:** as `e is ApiError` it narrowed `onError`'s already-typed error to `never` in the other branch (typecheck).
- **The row test reads each row's first button:** the menu button's name ("More actions for October 4, 2026") also matched a pattern on the year.
- **Hymn use skips a service's own date** (`hymn_usage.usage_near`: "D itself excluded"), so T8's phone step 3 dates the new service a week after the saved one; manual-verification item 13 says so.
- **The production build** ran in the build worktree: `✓ Compiled successfully`, with `/services` among the routes.
- Vitest reports failures as files finish, so the `×` lines of a "see it fail" step may come in another order than quoted (T1's did in the replay); the set and the `Tests` line are what count.

**Replay of the finished plan (2026-10-02).** The directives of T1-T6 were applied in order onto a fresh detached worktree of the branch head (`a789fb8` plus the plan commits and the two idea-doc commits), running each step's commands:
- All 108 directives applied (T1 10 + 10, T2 12 + 19, T3 2 + 4, T4 23 + 18, T5 3 + 4, T6 3); every Replace anchor occurred exactly once, and every Append landed on the file as the task before left it. After T6, `frontend/src` and the three docs equaled the build worktree's (`diff -r`: empty).
- Every "see it fail" output matched as quoted (T1's `×` lines in another order), and every count matched the table: frontend 622, 628, 629, 637 in 82, then 645 in 83; the task's files `40`, `25`, `13`, `27` (three times) and `14` (three times) passed; typecheck 0 and lint 0 after each of T1-T5; `note grep exit 1` after T4; T6 `89 passed`, `4`, `0`, `3 files changed, 26 insertions(+)`, backend `1335 passed, 16 skipped`. At the end the whole frontend suite three times, `645 passed` in 83 each, no `×` or `FAIL`; `export_openapi.py` and `gen:api` changed nothing; no raw HTML. No flaky run.
- Not run while planning: the pushes, the PR and CI, the merge, and the owner's phone check.

## Spec coverage

| Owner answer or S item | Task(s) and tests |
|---|---|
| 1. Three PRs; this one is the Save card and the Services page; no backend change | the plan's scope; T7 Step 3 (46 paths; `0` backend, API snapshot or migration paths; regenerating the API changes nothing); clarification 1 |
| 2. No order-of-worship preview | T4 "shows Still to do, the Archive card and both copies … in that order" (the step's three h2s) |
| 4. A save keeps a default Benediction and communion as saved | T2 "markSaved records the save and keeps a default Benediction and communion as saved (owner answer 4)"; T4 "saves a new service with the draft's key, …" (the stored draft's origins after the save) |
| 5. No "Readings for … are available" while the date is the saved date | T2 "opens a saved service as a new draft that is already Saved, …" (hidden on the saved date, shown on another, hidden again back on it) |
| 6. Deleting recalculates hymn use (server); the client refreshes the hymns | T3 `useDeleteService` (`hymns` invalidated, clarification 20); T5 "deletes after asking, …"; T8 Step 6 |
| 8. A guided phone check | T8 Steps 2-6; `docs/manual-verification.md` items 12-16 (T6) |
| 9. Reviewer notes: cleared on open, kept on save | clarification 7 (`created_at` new on open, unchanged on save): T2 "opens a saved service …" (`created_at` is the open time); T4's saves keep `created_at` (the stored draft keeps `testDraft`'s) |
| S "Draft schema change" (version 2, the migration and its test) | T1 "migrates a version 1 draft: …", the schema cases (`editing.date_iso` required and validated; version 3 is a future version) |
| S "Save key rule" (F §1.6; acceptance criterion 9, client side) | T1 `save-key.test.ts` (two cases); T4 "saves a new service with the draft's key …" (key = `save_key`, replaced after the 201), "offers Go to Hymns … uses a new key", "keeps the key for an identical retry … retries a mismatch once" |
| S `serviceToDraft` / `draftToServicePayload` (acceptance criterion 13) | T2 the three `serviceToDraft and markSaved` cases (round trip not dirty; undated; unknown place kept as "end"; no default Benediction added; `in_hymnal: false` → no id), "trims every text as the server does …", the existing payload cases |
| S `status.ts` (`saveMode`, `reviewStatus`, `stepStatus` for Review, all four steps shipped, the hymnal row) | T2 the two "archive status" cases, "lists the four steps …", "counts the hymns step n of 3 and lists … a hymn not in the hymnal" |
| S UX "Save card": labels, the copy note, Saving…, success, invalid date | T4 "saves a new service …", "opens with the banner … saves a copy when the date changed or the service had none", "turns both buttons and Save off without a service date …", "… while a Date & readings field shows its message …" |
| S UX Conflict (409; F §1.7) | T4 "on a conflict, reloads their version or saves mine as a new service" |
| S UX "The archived copy was deleted" (PUT 404 → POST) | T4 "saves as a new service, and says so, when the saved copy was deleted" |
| S UX hymn 404 → "Go to Hymns", corrected save works | T4 "offers Go to Hymns …" |
| S UX "Start a new service" | T4 "Start a new service asks first when the draft has unsaved work, and not when it is saved" |
| S UX editing banner (and the no-date case) | T4 "opens with the banner and the hymn to replace, …" |
| S UX "Still to do" and "Everything's ready." | T4 the first case; `builder-shell.test.tsx` (rows, "Everything's ready."); T2 the hymnal row |
| S UX save hint after a download | T4 "after a download, says that saving records the hymns, until the service is saved" |
| S "Step status and summary panel" (Review item; summary status line) | T4 "saves a new service …" (step bar "Not in archive" → "Saved" → "Unsaved changes"; the summary line's three states) |
| S "Services page": loading, rows, paging, empty, error | T5 "shows five rows while it loads, …", "Show more reads the next 20", "with nothing saved, offers to build a service; …", "shows an error with Retry, …" |
| S "Open flow" (confirm when dirty; Opening…; 404) | T5 "opens a service into the builder at once …", "asks before replacing unsaved work, and a service gone …" |
| S "Delete flow" (copy; editing line; reset; 404) | T5 "deletes after asking, …", "names an untitled, undated service, and a delete that finds it gone says so" |
| F §4.2 nav item | T5 `app-header.test.tsx` (Builder, Services) |
| F §4.4 invalidations | T3 `lib/queries/services.ts` (clarification 20); T5's refetch counts after a 404 |
| F §4.6 `replace` writes at once (the Services page opens the builder) | T1 "replace writes at once, …"; T5 "opens a service into the builder at once …" (the stored draft after the tap) |
| `formatSavedAt` | T3 `dates.test.ts` |
| 5a-2 record follow-up: a stored element over today's limits | clarification 12 (`serviceBody`); 5a-1's `documents.test.ts` "stays within the ServiceDraft limits …" covers the cutting |
| S acceptance criterion 14 (frontend) | T4 and T5 as above; `SHIPPED_STEPS` (T2) |

S items **not** in 5a-3 (owner answers 1, 2): the order-of-worship card and its fixtures; the email card (5b). Changed by this plan (clarifications 3, 4, 13, 15): the names `ReviewChecklist`/`missingItems` (kept as `StillNeeded`/`stillNeeded`); the banner's hymn line (the checklist lists them); "Start a new service"'s own copy (New service's is used); the lectionary prefetch on open (the builder looks it up itself).

## Questions for the owner

Your answers of 2026-10-01 and 2026-10-02 are binding and already in the plan, and so are the choices the spec already made (asking before opening over unsaved work, Save as new service on a new date, 20 a page with no search, any member may delete with the spec's question, hymn use recorded on save only). These are the choices this plan makes where you did not say; each is written as recommended.

1. **Review & send, top to bottom** (clarification 2): the banner (only while you are editing a saved service), "Still to do", the **Archive** card, then **Word documents**. The Archive card moves above the downloads, and "Saving services to the archive is coming soon." goes. Recommended: accept.
2. **"Still to do"** (clarification 3): "Still needed" is renamed "Still to do", keeps every row, adds "{Title} isn't in your hymnal" with the link "Choose a replacement", and says "Everything's ready." when nothing is missing. Recommended: accept.
3. **The banner** (clarification 4): "You're editing the saved service for October 4, 2026. Changes stay on this device until you save." For a saved service without a date (you have none today): "This saved service has no date. It's set to Sunday, October 11, 2026 for now." with "Check the date". It does not repeat the hymns that are not in your hymnal, since "Still to do" right below lists them. Recommended: accept.
4. **The Archive card** (clarification 5): "Not in the archive yet." / "Saved to the archive · Oct 1, 10:42 AM" / "Unsaved changes · last saved Oct 1, 10:42 AM"; the button "Save to archive", "Save changes" or "Save as new service" (with "The date changed from October 4, 2026 to October 11, 2026, so this will be saved as a new service. The October 4 service stays in the archive."); "Saving…", then "Service saved". It is off only without a date ("Choose a service date on step 1 to save.") or while step 1 shows a message ("Fix the readings on step 1 to save."); it stays on when nothing changed. Recommended: accept.
5. **After a save** (clarification 6, your answer 4): a Benediction or communion that followed the default becomes the service's own, so the Liturgy step says "Set from the saved service." with "Use default" for communion, as for an opened service, and "Review service" then reviews that Benediction like the other prayers. Recommended: accept.
6. **When someone else saved first** (clarification 9): "Someone else changed this service" with "This service was changed by someone else. Reload it to see their changes." and three choices: "Reload their version" (your unsaved changes go; "Loaded the latest version."), "Save mine as a new service" (theirs stays), "Cancel". Recommended: accept.
7. **Other save problems** (clarification 10): if the saved copy was deleted, yours is saved as a new service with "The archived copy was deleted, so this was saved as a new service."; a hymn no longer in your hymnal shows the existing message with a "Go to Hymns" button; a connection problem shows the usual message, and saving again is safe (it never saves twice). Recommended: accept.
8. **"Start a new service"** (clarification 13) asks the same question as the menu's "New service" ("Start a new service?" / "This clears the current draft on this device." / "Start new service"), and only when something is unsaved, instead of new wording. Recommended: accept.
9. **The Services page** (clarification 14): "Services", "Saved services for {your church}.", a "New service" button; each row shows the date, the occasion and "Created by {name} · last saved {time}", with "Editing" on the one you have open; tap a row to open it; "Delete…" is behind the ⋮ button; "Showing 20 of 45" and "Show more" at the bottom; "No saved services yet" / "Services you save from the builder appear here." / "Build a service" when empty. Recommended: accept.
10. **Opening and deleting** (clarifications 15, 16): opening asks "Replace your unsaved draft?" only when something is unsaved (choosing another Bible translation counts, since opening resets it), says "Opening…", and lands on Review & send. Deleting asks with the spec's words ("“World Communion Sunday” on October 4, 2026 will be removed from the archive for everyone in {church}. This can't be undone.", plus "You're editing this service. Your current draft will be cleared too." when it is the open one), and the row simply goes, with no message. A service someone deletes while you have it open stays on your screen; "Save changes" then saves it as a new one and says so. Recommended: accept.
11. **Where the status shows** (clarification 17): the step bar's "4 Review & send" reads "Not in archive", "Saved" (with a ✓) or "Unsaved changes"; the summary's last line reads "Draft saved on this device · In archive (saved Oct 1, 10:42 AM)" (plus "· Unsaved changes") and takes you to Review; times are in your phone's time zone, with the year only when it is not this year; after a download of an unsaved service the card adds "Tip: save this service so its hymns count as recently used."; the menu gains "Services" after "Builder". Recommended: accept.
12. **A save sends what the downloads send** (clarification 12): anything over the app's length limits is saved cut to the limit, exactly as the Word file prints it (only possible for an old saved custom element, never for anything typed in the app today), so a save never fails with an unexplained "not valid". Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T7); the merge on your yes, then five phone checks one at a time and the records PR (T8).
