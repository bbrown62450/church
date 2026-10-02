# Slice 5a-1: Word Downloads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first of the three 5a PRs (owner answer 1, 2026-10-01): **Word downloads end to end.** After it merges, a member on step 4 of the Service Builder (`/builder/review`) sees what is still missing (the "Still needed" list from 4b, unchanged), a **Word documents** card with **Download bulletin copy** and **Download pastor's copy**, and a short note that saving to the archive is coming. Each tap builds the file on the server from the draft as it is at that moment (`POST /documents`) and hands it to the browser (on an iPhone, the share or preview sheet). The file keeps Streamlit's layout exactly (Times New Roman 11 pt, Word's Heading 2, "October 04, 2026", `worship_October_04_2026.docx`), with the decided fixes: "First Reading", hymn headings by slot, no "#None", the readings the Bulletin readings selects show. No database change (Alembic head stays `0004_invites_reusable`), no new variable, no migration; production Streamlit (branch `streamlit-frozen`) is untouched. Saving (5a-2, with `0005_services_extras`) and the Save card and Services page (5a-3) are later PRs with their own plans.

**Architecture:** Backend first. `backend/service_output.py` (new, pure) holds the date line, the filenames and headers, the variants, `hymn_line`, `resolve_doc_readings` (slice 2's `resolve_readings`, nothing more) and `render_docx`. `worship_service.build_docx` gets the spec's keyword signature (slot hymns, resolved readings, bytes back) and is pinned against a verbatim copy of the old function, compared as document XML in the same run. `usecases/archive.py` starts with the parts a document needs (`ServiceInput`, `clean_input`, `resolve_hymn_refs`); `usecases/documents.build_document` cleans, resolves the hymns in a short read, renders and names the file; `POST /documents` (church-scoped, plain `def`) returns the bytes with the F §1.9 headers. `ServiceDraft` lands in `api/schemas.py` now, as the body's `service` (5a-2 and 5b reuse it). Frontend: `apiFetchBlob` shares one `send()` with `apiFetch`; `lib/documents.ts` builds the body from the draft within the server's limits; `lib/download.ts` names and saves the file; `useDownloadDocument` (one mutation per button) ties them together; `components/builder/review/` holds the new step (`ReviewSendStep`, `DocumentsCard`), named apart from the service reviewer's `components/builder/liturgy/review-step.test.tsx`.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, python-docx 1.2.0 (`python-docx>=1.0.0` in `backend/requirements.txt`), pytest; Next 16, React 19, TypeScript 5, Base UI, TanStack Query 5, sonner, Vitest 3 with Testing Library.

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`: "Scope", "Hand-offs to 5b", UX "Review step" items 2 and 4 and "Mobile specifics", API (the `/documents` row, "Timeouts", "OpenAPI", "Schemas"), Backend "New modules" (`service_output.py`, `usecases/documents.py`, the `ServiceInput` / `clean_input` / `resolve_hymn_refs` rows of `usecases/archive.py`), "Changed modules" (`worship_service.build_docx`), Frontend "Library code" (`apiFetchBlob`, `timeouts.ts`, `download.ts`, `useDownloadDocument`), "Behavior changes" 1, 2, 5, 6, 7, 19, 20, Testing (`test_service_output.py`, the characterization test, `test_api_documents.py`, `download.test.ts`, `client.test.ts`, the "Downloads" and "Invalid date" DOM cases), manual checks 1-4, 11, 13, Risks (iOS Safari).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.3 (`HymnRef`, `SlotHymns`, `SectionKey`, frozen), §1.6 (idempotency is for writes), §1.8 (`POST /documents`: local, < 3 s, client 30 000 ms), §1.9 (file downloads), §1.10 (CORS exposes `Content-Disposition`), §4.5 (the blob variant), §4.6 ("Draft → API payload"), §4.8, §4.9, and the Amendments rows naming 5a.
- Format models: `docs/superpowers/plans/2026-09-30-slice-4b-liturgy-step.md` and `docs/superpowers/plans/2026-10-01-reviewer-followup-1.md`.
- Facts checked for this plan (tree `934ffb9` = `origin/main`, 2026-10-01): backend `1223 passed, 11 skipped`; frontend `597 passed` in 78 files; typecheck and lint clean; Alembic head `0004_invites_reusable`; 4 runbook owner markers. `build_docx` (`backend/worship_service.py:106`) takes positional hymn lists and prints "Old Testament Reading", `#None` and `scriptures[1]` as the NT fallback, and returns a `BytesIO`; `test_liturgy_config.py:143-146` maps `ot_reading` to "Old Testament Reading" (`DOCX_HEADINGS_UNTIL_5A`) and its outline test and `test_communion_docx.py` call the old signature; `OUTLINE` already says "First Reading". `app.py` on `main` cannot import `worship_service` since slice 4a (its `generate_liturgy` import is gone), and production Streamlit runs from `streamlit-frozen`, so no shim. `hymn_search.usage_key` is title-only (3a amendment), which matters to 5a-2, not here. `client.ts` has `ifMatch` but no blob call; `installFakeApi` turns every handler result into JSON. The Review route renders `StepPlaceholder` ("Available soon") and `StillNeeded`; `StepPlaceholder` has no other user. `CORSMiddleware` already exposes `Content-Disposition`.
- Every task's code was written and run by the planner in a throwaway worktree of `934ffb9`, and the plan's directives were then replayed onto a fresh worktree of `934ffb9` (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one file `.venv/bin/python -m pytest -q <file> 2>&1 | tail -3`; the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one file `(cd frontend && npx vitest run <path> 2>&1 | grep -E "^ +× |Tests ")`; the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` (a failure is named); then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes (T3), so T3 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand.
- Branch `claude/slice-2-plan-4q33le`, at `origin/main` `934ffb9` plus this plan's commits (`WIP plan: slice 5a-1`, then `Plan: slice 5a-1, Word downloads (owner answers 2026-10-01)`, then `Plan: slice 5a-1 review fixes (owner answers 2026-10-01)`), then T1-T7. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1223 → 1256 passed, 11 → 11 skipped; frontend 597 → 611 in 78 → 81 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 16 and has no em dashes; existing copy keeps its own punctuation ("No service date — Choose one", the hymn line "Holy, Holy, Holy — #138" printed in the file, as Streamlit printed it).
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.

### How the file directives below read
As in the 4b plan: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. One file is deleted with `git rm` (T6 Step 3).

### Baselines and counts
- Starting baselines: backend **1223 passed, 11 skipped**; frontend **597 passed in 78 files**, typecheck and lint clean; Alembic head **`0004_invites_reusable`** (no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new `it(`.

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +6 (`test_service_output.py`) | 1229 passed, 11 skipped | 0 | 597 in 78 |
  | T2 | +8 (`test_build_docx_characterization.py`, one test in two cases; two files edited) | 1237 passed, 11 skipped | 0 | 597 in 78 |
  | T3 | +19 (`test_usecase_documents.py` 5, `test_api_documents.py` 14 with one test in six cases; one file edited) | 1256 passed, 11 skipped | 0 | 597 in 78 |
  | T4 | 0 | 1256 passed, 11 skipped | +4 (`client.test.ts`) | 601 in 78 |
  | T5 | 0 | 1256 passed, 11 skipped | +4 (`download.test.ts` 2, `documents.test.ts` 2) | 605 in 80 |
  | T6 | 0 | 1256 passed, 11 skipped | +6 (`review-send-step.test.tsx`; `builder-shell.test.tsx` edited) | 611 in 81 |
  | T7-T9 | 0 (`test_slice1_docs.py` edited) | 1256 passed, 11 skipped | 0 | 611 in 81 |

- CI `backend-postgres` goes from `11 passed, 1223 deselected` to `11 passed, 1256 deselected` (no new Postgres test: nothing here writes).

### Layering and code rules (carried)
- `service_output`, `usecases/archive.py` and `usecases/documents.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains them, T3); the route is a plain `def` with no SQL and no try/except (F §2.2 rule 1); `build_document` reads in one short `session_scope` that closes before rendering (S "Data access").
- Logs carry ids, the variant, the size and the duration, never a service's text (F §2.5).
- Pages and components never call `apiFetch` or `apiFetchBlob`: `lib/queries/documents.ts` uses `useApi()` (F §4.5).
- Touch targets 44 px below `md`; text wraps at 375 px; no raw HTML (F §4.8); nothing about a document is cached or stored (owner decision 4).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** (branch `streamlit-frozen`) is frozen and, since 2026-10-01, retired for real use (owner answer 6 below); merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **The 5a spec's decisions** stand, except where the owner answers below change them (S gains an amendment, T7).

### Owner answers (Beau, 2026-10-01, binding)
1. **Three PRs.** (1) Word downloads end to end: this plan; `/documents` needs no database change. (2) Saving: the backend and migration `0005_services_extras` on its own. (3) The Save card and the Services page. PR 2 and PR 3 get their own plans.
2. **No "Order of worship" preview on the Review step** (the Liturgy step already shows the order). Review keeps the checklist of what is missing and the downloads; Save comes in PR 3.
3. **The Word file: exact parity with Streamlit's layout** (Times New Roman 11 pt, Word's default Heading 2 style, the date as "October 04, 2026", filenames like `worship_October_04_2026.docx` per S), plus the decided fixes: the "First Reading" heading (`DOCX_HEADINGS_UNTIL_5A` deleted), headings by slot, no "#None". The bulletin copy and the pastor's copy as S defines them.
4. (PR 2 and 3) A saved service fixes a default-following Benediction and the communion setting to what was saved.
5. (PR 3) "Readings for … are available" does not show while the date is still the saved date.
6. (PR 2) **Streamlit is retired for real use** (the owner has stopped using it): deleting a service recalculates that date's hymn use from the services still saved. This supersedes S's open question 1 (recorded in S's amendment, T7). The `streamlit-frozen` branch and the frozen app are not touched.
7. **Phone download:** iOS's share or preview sheet is accepted; if the owner's phone check shows the download does not start, the fallback is a "Save {filename}" second-tap link (documented here as the fallback; built only if judged cheap and safe, otherwise a documented follow-up: clarification 11).
8. **Checks:** a guided phone check after each PR (T9 here). For PR 2, not this one: a backup, read-only counts and the migration's `--sql` preview. No Streamlit compatibility check (Streamlit retired).
9. **Reviewer notes stay in memory:** opening a saved service clears them; saving keeps them (accepted as is; PR 3).

### Owner answers to this plan's questions (Beau, 2026-10-01, binding)
The owner answered "all recommended" to "Questions for the owner" (1-7, at the end of this plan) on 2026-10-01. Each choice stands as written there and in its clarification (2, 3, 5 and 16, 4, 14, 11, 9). The plan review's fixes that followed (clarification 19) use owner decision 1 and add no copy.

**Later, out of scope:** PR 2 (5a-2: `/services`, hymn use recorded on save and recalculated on delete, `0005_services_extras`, a backup and the `--sql` preview first), PR 3 (5a-3: the Save card, the Services page, `serviceToDraft`, the draft version bump, `"review"` in `SHIPPED_STEPS`), 5b (email).
## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended).

1. **[owner-visible] What 5a-1 ships** (owner answer 1). The Review route's real content (clarification 2), `POST /documents` and everything under it. Not here: saving, the Services page, the "Saved" and "Unsaved changes" statuses, `serviceToDraft`, the draft version bump, the migration. `"review"` stays out of `SHIPPED_STEPS` until 5a-3, so the step bar still reads "4 Review & send Not in archive" and the summary's status line is unchanged ("Draft saved on this device · Not in archive"); `steps.ts`'s comment says so (T6).
2. **[owner-visible] The Review step's layout** (owner answers 1, 2), top to bottom in one column: "Still needed" (clarification 3), the **Word documents** card (clarifications 4, 5), then a dashed **Archive** card: "Saving services to the archive is coming soon." (the place 5a-3's Save card takes). No order-of-worship card (owner answer 2), no editing banner (5a-3), no email card: S's "keep using the current app for this part" is no longer true (owner answer 6), and 5b brings email. The "Available soon" card goes, and `StepPlaceholder`, which nothing else uses, is deleted (`StillNeeded` stays until 5a-3 replaces it).
3. **[owner-visible] The checklist stays as 4b shipped it:** the heading "Still needed", one row per gap with its link ("No service date — Choose one", "No Opening hymn — Choose one", "Call to Worship is empty — Write or generate it", "No sermon title — Add one", …), and nothing when nothing is missing. S's rename to "Still to do", its "Everything's ready." line and its "{Title} isn't in your hymnal" row wait for 5a-3: only an opened saved service can hold a hymn that is not in the hymnal, and renaming now would change copy the owner has already checked twice.
4. **[owner-visible] Only the service date gates a download** (S UX, F decision D9). Both buttons need a valid date in the supported range (`hasServiceDate`, as the lectionary lookup); without one both are off and the card says "Choose a service date on step 1 to download." (the "No service date — Choose one" row above links there). Anything else missing does not block: the file prints what there is, "[Sermon title]" for a blank title (parity), and leaves out an empty hymn slot or reading.
5. **[owner-visible] The Word documents card** (S UX item 4, without the save hint): "Bulletin copy" with "The order of worship with hymns, readings and the sermon title. Leaves out Prayers of the People." and **Download bulletin copy** (primary); "Pastor's copy" with "Everything in the bulletin copy, plus Prayers of the People." and **Download pastor's copy** (outline); under the pastor's copy, while Prayers of the People is off or blank, "Same as the bulletin copy for this service. Prayers of the People is empty or turned off.". Each button has its own pending label, "Preparing…", then "Still working…" after 8 s (F §1.8; `useStillWorking`), and the other button stays usable. Success opens the browser's download (an iPhone's share or preview sheet) with no toast; a failure is a toast with the message (`errorToastMessage`: the server's sentence, such as "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."; "Can't reach the server. Check your connection and try again."; "This is taking too long. Try again."; "Something went wrong. (Ref: …)"), and no file. A 401 or a lost church shows no toast of its own: the app's handling (sign-in, the church's own message) already says it, as Suggest hymns does (clarification 19). S's "Tip: save this service so its hymns count as recently used." comes with Save in 5a-3.
6. **The route** (S API, F §1.9). `POST /documents`, church-scoped (`require_church`; any member, owner decision 5), body `DocumentIn = {variant: "bulletin" | "pastor", service: ServiceDraft}` (`extra="forbid"`), answer 200 with the bytes and exactly `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `Content-Disposition: attachment; filename="worship_October_04_2026.docx"; filename*=UTF-8''worship_October_04_2026.docx` (pastor: `worship_pastor_…`) and `Cache-Control: no-store`. **No `Idempotency-Key`**: it is a pure render that writes nothing, so a retry is harmless (F §1.6 is for writes). **No rate-limit bucket** (S "Timeouts"): local work, well under 3 s, nothing paid. Errors stay JSON: 404 `not_found` with `details.field = "hymns.<slot>.hymn_id"` for a hymn id the church does not have (slice 4's message), 422 `invalid_request` with `fields` (Pydantic, or "Give each custom element a label."), a logged 500 `internal_error` without python-docx. OpenAPI declares `response_class=Response` and a binary 200 under the docx type.
7. **What the documents read** (S `ServiceDraft`, `build_docx`). The date (the date line and the filename), the occasion (the title), the scripture **references** (never passage texts: S removes `scripture_full_texts`, and Streamlit printed references only), the two bulletin picks (re-resolved on the server by `resolve_readings`, so a stale pick prints the automatic reading), the three hymns by slot (an id is looked up in the church and its current title and number print, F §1.3; a null id prints the snapshot sent), the liturgy (the switched-on cards with text, the Benediction included while it follows the church default, as the Liturgy step shows it), the sermon title, communion on or off (the fixed text from `liturgy_config.COMMUNION_BLOCKS`), and the custom elements (label, text, place). `hymnal` is accepted, for 5a-2, and ignored by the documents.
8. **Cleaning on the server** (S `clean_input`): every string trimmed, blank scripture lines and blank liturgy dropped, Streamlit's stored error texts (`[Error generating …]`, `[Configure OPENAI_API_KEY to generate …]`, `[Your OPENAI_API_KEY contains invalid …]`) dropped, a blank custom label a 422 on `custom_elements.<i>.label`. A hymn whose title is blank prints nothing in its slot. Before any of that, characters a Word file cannot hold are taken out of every string (clarification 19).
9. **[owner-visible] The body stays within the server's limits** (`lib/documents.ts`). It is `draftToServicePayload(draft)` (the provisional mapping, F §4.6) with the occasion and readings exactly as every liturgy request sends them (trimmed; the first 20 readings, each cut to 200; `request.ts`'s `readingsContext`), the two bulletin picks trimmed and cut to 200 (`MAX_REF_LENGTH`, as the readings), the hymns as `HymnRef`s (`hymnRef`: a non-UUID id goes as null), each text cut to its `liturgy_config.LIMITS` length, custom elements without a label left out (`build_docx` never printed them, and the server would refuse them) and each place read through `normalizePlacement`, as the Liturgy step places it. So a draft never meets a 422; an occasion over 300 characters, which step 1 already flags, prints cut at 300.
10. **The download on the client** (F §1.9, §4.5). `apiFetchBlob` shares one `send()` with `apiFetch` (headers, the timeout and the caller's signal combined by hand, the error mapping, so `ApiError` codes and messages are the same); a 2xx returns `{blob, filename}`, the filename from `Content-Disposition` (`filename*` decoded first, then `filename`, else null). `POST /documents` gets 30 000 ms in `timeouts.ts`. `useDownloadDocument(variant)` is a `useChurchMutation` (so a 401 or a lost church goes through `handleAuthErrors`), one per button; at the tap it reads the latest draft (`peek`), posts, and calls `downloadBlob(blob, filename ?? docxFilename(variant, date))`: an object URL clicked through a hidden `<a download>`, revoked after 5 minutes (at once breaks Safari, and an iPhone's "Download?" sheet can wait for the member's answer; clarification 19). Nothing is cached or kept. `docxFilename` and `service_output.docx_filename` run the same shared fixture (`docx_filenames.json`).
11. **[owner-visible] The iPhone fallback is documented, not built** (owner answer 7). Built now it would add a third state to each button, keep an object URL alive until the second tap, and add copy ("Save {filename}"), all for a failure no test here can reproduce. If T9's phone step 1 finds the download does not start, the follow-up is one small PR: after the file arrives, the button becomes a real `<a download>` link reading "Save {filename}"; `downloadBlob` stays the one place to change.
12. **`build_docx`'s parity is pinned** (owner answer 3; S "Changed modules"; F §2.3.1). `test_build_docx_characterization.py` carries a verbatim copy of the old function (`legacy_build_docx`) and of the three helpers it calls whose output the parity rests on (`_add_leader_people_paragraph`, `_add_assurance_paragraph`, `_add_custom_elements_after`, copied from `934ffb9`, so a later change to the module's helpers cannot move both sides at once; `_add_communion_liturgy` stays imported, as `test_communion_docx.py` pins it) and compares the document XML in the same run: a full service in both variants must equal the old output with "Old Testament Reading" read as "First Reading", and the styles part must be identical; a sparse service must be identical. The new keyword signature is S's (`occasion, date_display, hymns_by_slot, liturgy, ot_ref, nt_ref, sermon_title, include_sermon, include_prayers_of_the_people, include_communion, custom_elements`), it returns bytes, and `include_placeholders` and `scripture_full_texts` are gone. `test_liturgy_config.py` loses `DOCX_HEADINGS_UNTIL_5A`, so OUTLINE's labels are the docx headings, "First Reading" included; `test_communion_docx.py`'s helper moves to the new signature (its comparison is unchanged). No shim for `app.py` on `main` (it already cannot import `worship_service`; production Streamlit runs from `streamlit-frozen`).
13. **Names kept from S's hand-offs to 5b:** `usecases.documents.build_document(church_id, data, variant) -> DocumentResult(content, filename)`, `service_output.service_date_display`, `service_output.DOCX_MIME`, `ServiceDraft` (with `to_input()`) and `CustomElementIn` in `api/schemas.py`, `usecases.archive.ServiceInput`. `ServiceDraft.service_date_iso` uses 2a's strict `IsoDate` (only a whole `YYYY-MM-DD`; "2026-10-04T00:00:00" is a 422, as on `GET /lectionary/readings`). `ServiceInput`'s custom elements are `service_output.CustomElement` (a plain dataclass, so `service_output` stays below the usecases); its hymns are slice 4's `HymnRefData`. 5a-2 extends `usecases/archive.py` with saving, listing, opening and deleting.
14. **[owner-visible] Downloads record no hymn use** (S behavior change 3; owner decision 9). Hymn use is recorded on Save from 5a-2. With Streamlit retired (owner answer 6), nothing records it between this merge and 5a-2's, so the hymns step's "Used …" marks and the 12-week exclusion do not see services built in the meantime.
15. **Screen readers and the phone** (F §4.9). The step is a region named "Review & send"; the card is a region named by its "Word documents" heading, each copy an item with its own heading. Each button is described by its copy's sentence (and the "Same as the bulletin copy …" helper when shown, `aria-describedby`). While a file is prepared, a polite status in that row reads "Bulletin copy: Preparing…" (or "… Still working…"), so the change of the button's name is announced with its context; an error is announced by the toast. The buttons are `size="touch"` (44 px) and full width below `sm`. The `PendingButton` pattern (disabled while pending, F §4.8) is the app's own.
16. **[owner-visible] Every new user-facing string** (no em dashes): "Word documents"; "Bulletin copy"; "The order of worship with hymns, readings and the sermon title. Leaves out Prayers of the People."; "Download bulletin copy"; "Pastor's copy"; "Everything in the bulletin copy, plus Prayers of the People."; "Download pastor's copy"; "Same as the bulletin copy for this service. Prayers of the People is empty or turned off."; "Preparing…"; "Still working…"; for screen readers only "Bulletin copy: Preparing…", "Bulletin copy: Still working…", "Pastor's copy: Preparing…", "Pastor's copy: Still working…"; "Choose a service date on step 1 to download."; "Archive"; "Saving services to the archive is coming soon."; from the API only (the UI never sends a blank label) "Give each custom element a label."; in the file, "First Reading" in place of "Old Testament Reading". The filenames are Streamlit's. Error toasts reuse existing messages (clarification 5).
17. **Logging** (F §2.5): one INFO line per file, `documents.build church=<id> variant=<v> bytes=<n> ms=<n>`; never the occasion, a reading, a hymn or any text.
18. **Docs** (owner answers 1-9). T7 appends S's amendment (the three PRs; owner answers 1-9; answer 6 supersedes open question 1 and behavior change 4; manual check 10 and the Streamlit smoke dropped), and `docs/manual-verification.md` gains "## Slice 5a" with items marked "(owner, after 5a-1)" (the `##` pin in `test_slice1_docs.py` grows to seven). The runbook record is T9's.
19. **The plan review's fixes** (owner decision 1, 2026-10-01; no new copy). (a) **Characters a Word file cannot hold.** python-docx refuses XML-invalid characters (a NUL, a vertical tab pasted from Word as a soft line break, a form feed, a lone surrogate) with a `ValueError` (a lone surrogate: `UnicodeEncodeError`), so such a string made `POST /documents` a 500 "Something went wrong.". `usecases.archive.clean_input` now runs every string through `_xml_safe` before trimming and the blank checks (the occasion, the scriptures, the liturgy texts, the sermon title, both bulletin picks, each hymn's title and hymnal, each custom element's label and text), and `resolve_hymn_refs` does the same for the database's hymn title: a vertical tab or form feed becomes a line break (python-docx prints `"\n"` as `<w:br/>`, checked), the other control characters, U+FFFE, U+FFFF and lone surrogates are dropped. A label of only such characters is the blank-label 422. This fixes the NUL 500 for `/documents` only; the app-wide item stays open for the other routes (T9's record). (b) **No second message after a 401 or a lost church** (clarification 5): `CopyRow`'s `onError` returns early for `e.status === 401 || isNoChurchAccess(e)`, as `suggest-hymns-button.tsx` does. (c) **The object URL lives 5 minutes, not 60 s** (clarification 10): an iPhone's "Download?" sheet waits for the member, and a URL revoked under it fails the save; T9's phone step 1 waits about a minute on the sheet. (d) **The bulletin picks stay within the server's 200** (clarification 9): only a picked line over 200 characters could reach the 422. (e) **The parity test copies its helpers** (clarification 12).

### Risks
- **iOS Safari and a download after an `await`.** Safari may not treat the delayed click as the member's tap. T9 step 1 checks it on the owner's phone (waiting a minute on the sheet, so the 5-minute object URL is exercised); the fallback is clarification 11.
- **The XML comparison depends on python-docx writing the same XML for the same calls.** Both documents are built in the same run with the same library, so a python-docx upgrade cannot make it flaky; it only fails when `build_docx` really prints something else.
- **No hymn use is recorded until 5a-2** (clarification 14). 5a-2 is next; its delete-recalculates rule (owner answer 6) and a save rebuild the date's rows.

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/service_output.py` (+ `backend/tests/test_service_output.py`) | the date line, filenames, headers, variants, `hymn_line`, `resolve_doc_readings`, `is_legacy_error_placeholder` (T1); `ResolvedHymn`, `CustomElement`, `ResolvedService`, `render_docx` (T2) | T1, T2 |
| `backend/tests/fixtures/shared/docx_filenames.json` | 8 dates and both variants, shared with `download.test.ts` | T1 |
| `backend/tests/test_build_docx_characterization.py` | `legacy_build_docx` and the parity and change tests | T2 |
| `backend/usecases/archive.py` | `ServiceInput`, `clean_input`, `resolve_hymn_refs` | T3 |
| `backend/usecases/documents.py` (+ `backend/tests/test_usecase_documents.py`) | `DocumentResult`, `build_document` | T3 |
| `backend/api/routes/documents.py` (+ `backend/tests/test_api_documents.py`) | `DocumentIn`, `POST /documents` | T3 |
| `frontend/src/lib/download.ts` (+ `.test.ts`) | `docxFilename`, `downloadBlob` | T5 |
| `frontend/src/lib/documents.ts` (+ `.test.ts`) | `documentRequest` | T5 |
| `frontend/src/lib/queries/documents.ts` | `useDownloadDocument` | T5 |
| `frontend/src/components/builder/review/documents-card.tsx` | the Word documents card | T6 |
| `frontend/src/components/builder/review/review-send-step.tsx` (+ `.test.tsx`) | the step | T6 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/worship_service.py` | `build_docx`'s signature, `_add_hymn`, "First Reading", bytes | T2 |
| `backend/tests/test_liturgy_config.py`, `backend/tests/test_communion_docx.py` | the new signature; `DOCX_HEADINGS_UNTIL_5A` deleted | T2 |
| `backend/api/schemas.py`, `backend/api/main.py` | `Placement`, `CustomElementIn`, `ServiceDraft`; the router | T3 |
| `backend/tests/test_no_streamlit_in_core.py` | the four modules | T3 |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated | T3 |
| `frontend/src/lib/api/client.ts` (+ `client.test.ts`), `frontend/src/lib/api/timeouts.ts`, `frontend/src/test/fake-api.ts` | `send`, `apiFetchBlob`, `parseContentDispositionFilename`; 30 s; a `Response` passes through | T4 |
| `frontend/src/lib/liturgy/request.ts`, `frontend/src/lib/queries/client.ts` | export `hymnRef`, `readingsContext`; `useApi().churchBlob` | T5 |
| `frontend/src/app/(signed-in)/(church)/builder/review/page.tsx`, `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/lib/draft/steps.ts` | the step; the shell test's Review case; the comment | T6 |
| `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`, `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py` | the amendment; "## Slice 5a"; the pin | T7 |
| `docs/ops-runbook.md` | "### Slice 5a-1 record" (the records PR, after the merge) | T9 |

**Deleted:** `frontend/src/components/builder/step-placeholder.tsx` (T6).

**Counts in the PR:** 18 created (this plan and the 17 above), 20 modified (all but the runbook above), 1 deleted: 39 paths. **Untouched:** migrations, `db/models.py`, `service_archive.py`, `hymn_usage.py`, `liturgy_config.py`, `mapping.ts`, `status.ts`, `still-needed.tsx`, `summary-panel.tsx`, `step-progress.tsx`, `app.py`, Streamlit.

**Task order and review batch:** T1 → T7, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T8 verifies and opens the draft PR on the owner's yes; T9 merges on the owner's yes, runs the phone check and writes the record.

---

### Task 1: The file's date line, names and headers: `service_output` (owner answer 3; S `service_output.py`; F §1.9; clarifications 7, 8, 13)

**Files:**
- Create: `backend/tests/fixtures/shared/docx_filenames.json`, `backend/tests/test_service_output.py`, `backend/service_output.py`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/fixtures/shared/docx_filenames.json`:**

````json
{
  "_about": "The Word files' date line and filenames (slice 5a spec, service_output; F §1.9): the date as Streamlit printed it ('%B %d, %Y', day zero-padded, English months whatever the locale) and worship_{date}.docx or worship_pastor_{date}.docx with ', ' and ' ' turned into '_'. backend/service_output runs every case (test_service_output.py); frontend/src/lib/download.ts does too (download.test.ts).",
  "cases": [
    {"date": "2026-10-04", "variant": "bulletin", "display": "October 04, 2026", "filename": "worship_October_04_2026.docx"},
    {"date": "2026-10-04", "variant": "pastor", "display": "October 04, 2026", "filename": "worship_pastor_October_04_2026.docx"},
    {"date": "2026-10-11", "variant": "bulletin", "display": "October 11, 2026", "filename": "worship_October_11_2026.docx"},
    {"date": "2026-12-25", "variant": "pastor", "display": "December 25, 2026", "filename": "worship_pastor_December_25_2026.docx"},
    {"date": "2027-01-03", "variant": "bulletin", "display": "January 03, 2027", "filename": "worship_January_03_2027.docx"},
    {"date": "2027-02-28", "variant": "bulletin", "display": "February 28, 2027", "filename": "worship_February_28_2027.docx"},
    {"date": "2027-05-09", "variant": "pastor", "display": "May 09, 2027", "filename": "worship_pastor_May_09_2027.docx"},
    {"date": "2028-09-03", "variant": "bulletin", "display": "September 03, 2028", "filename": "worship_September_03_2028.docx"}
  ]
}
````

**Create `backend/tests/test_service_output.py`:**

````python
"""service_output: the Word files' date line, names, headers and helpers
(slice 5a spec, Testing `test_service_output.py`; F §1.9)."""
import json
from datetime import date
from pathlib import Path

import service_output as so

SHARED = Path(__file__).resolve().parent / "fixtures" / "shared"


def test_dates_and_filenames_follow_the_shared_fixture():
    cases = json.loads((SHARED / "docx_filenames.json").read_text(encoding="utf-8"))["cases"]
    assert len(cases) == 8
    for case in cases:
        d = date.fromisoformat(case["date"])
        assert so.service_date_display(d) == case["display"], case
        assert so.docx_filename(case["variant"], d) == case["filename"], case
    assert so.safe_date("October 04, 2026") == "October_04_2026"


def test_the_date_line_never_reads_the_locale():
    class NoStrftime(date):
        def strftime(self, fmt):            # '%B' follows LC_TIME; the file must not
            raise AssertionError("service_date_display read the locale")

    assert so.service_date_display(NoStrftime(2026, 10, 4)) == "October 04, 2026"
    assert so.MONTHS[0] == "January" and so.MONTHS[11] == "December" and len(so.MONTHS) == 12


def test_headers_and_variants():
    assert so.DOCX_MIME == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert so.content_disposition("worship_October_04_2026.docx") == (
        "attachment; filename=\"worship_October_04_2026.docx\"; "
        "filename*=UTF-8''worship_October_04_2026.docx")
    assert so.VARIANTS == {
        "bulletin": {"include_sermon": True, "include_prayers_of_the_people": False},
        "pastor": {"include_sermon": True, "include_prayers_of_the_people": True},
    }


def test_hymn_lines_never_print_none():
    assert so.hymn_line("Holy, Holy, Holy", 138) == "Holy, Holy, Holy — #138"
    assert so.hymn_line("Old Favorite", None) == "Old Favorite"
    assert so.hymn_line("Hymn Zero", 0) == "Hymn Zero — #0"


def test_doc_readings_are_resolve_readings():
    rcl = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"]
    assert so.resolve_doc_readings(rcl) == ("Isaiah 5:1-7", "Philippians 3:4b-14")
    # A pick no longer among the lines is ignored: the automatic reading prints.
    assert so.resolve_doc_readings(rcl, "", "Matthew 21:33-40") == ("Isaiah 5:1-7", "Philippians 3:4b-14")
    assert so.resolve_doc_readings(rcl, "", "Matthew 21:33-46") == ("Isaiah 5:1-7", "Matthew 21:33-46")
    assert so.resolve_doc_readings(["Isaiah 5:1-7", "Psalm 80:7-15"]) == ("Isaiah 5:1-7", None)
    assert so.resolve_doc_readings([]) == (None, None)
    cases = json.loads((SHARED / "scripture_refs.json").read_text(encoding="utf-8"))["resolve_readings"]
    assert cases
    for case in cases:
        expected = (case["expected"]["ot"], case["expected"]["nt"])
        assert so.resolve_doc_readings(case["scriptures"], case["ot_pick"], case["nt_pick"]) == expected, case["name"]


def test_legacy_error_placeholders():
    for text in ("[Error generating call_to_worship: timeout]",
                 "  [Configure OPENAI_API_KEY to generate opening_prayer.]  ",
                 "[Your OPENAI_API_KEY contains invalid characters.]"):
        assert so.is_legacy_error_placeholder(text), text
    for text in ("[Sermon title]", "Error generating", "[Error generating call_to_worship", ""):
        assert not so.is_legacy_error_placeholder(text), text
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_service_output.py 2>&1 | tail -3
```

**Expected:** `ERROR backend/tests/test_service_output.py` (`ModuleNotFoundError: No module named 'service_output'`), `!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!`, `1 error in <t>s`.

- [ ] **Step 3 (agent): The module**

**Create `backend/service_output.py`:**

````python
"""What the Word files print and how they are named (slice 5a spec, Backend
"service_output.py"; F §1.9, §2.3). Pure: no database, FastAPI or Streamlit.

- service_date_display: the date line, '%B %d, %Y' with English months
  ("October 04, 2026"), exactly as Streamlit printed it (app.py:430); the only
  date-display function (5b uses it too).
- docx_filename, content_disposition, DOCX_MIME: the download's name and
  headers (app.py:1072-1088; F §1.9).
- VARIANTS: both copies print the sermon title; only the pastor's copy prints
  Prayers of the People (owner decision 4).
- hymn_line: "Title — #138", or just the title when there is no number (no
  "#None").
- resolve_doc_readings: slice 2's resolve_readings, so the file prints the
  readings the Bulletin readings selects show.
- is_legacy_error_placeholder: Streamlit's stored "[Error generating ...]"
  texts, never printed.
- ResolvedHymn, CustomElement, ResolvedService and render_docx (Task 2): a
  service whose hymns are resolved, rendered by worship_service.build_docx.
"""
from __future__ import annotations

import datetime
from typing import Literal, Optional
from urllib.parse import quote

import scripture_refs

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December")
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

Variant = Literal["bulletin", "pastor"]
VARIANTS: dict[str, dict[str, bool]] = {
    "bulletin": {"include_sermon": True, "include_prayers_of_the_people": False},
    "pastor": {"include_sermon": True, "include_prayers_of_the_people": True},
}

LEGACY_ERROR_PREFIXES = ("[Error generating ", "[Configure OPENAI_API_KEY to generate ",
                         "[Your OPENAI_API_KEY contains invalid")


def service_date_display(d: datetime.date) -> str:
    """'%B %d, %Y' without the locale: date(2026, 10, 4) is "October 04, 2026"."""
    return f"{MONTHS[d.month - 1]} {d.day:02d}, {d.year}"


def safe_date(display: str) -> str:
    """"October 04, 2026" -> "October_04_2026" (app.py:1072)."""
    return display.replace(", ", "_").replace(" ", "_")


def docx_filename(variant: Variant, d: datetime.date) -> str:
    """worship_October_04_2026.docx, or worship_pastor_October_04_2026.docx (app.py:1079, 1088)."""
    prefix = "worship_pastor_" if variant == "pastor" else "worship_"
    return f"{prefix}{safe_date(service_date_display(d))}.docx"


def content_disposition(filename: str) -> str:
    """The download header of F §1.9: a plain name and the RFC 5987 form."""
    return f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"


def hymn_line(title: str, number: Optional[int]) -> str:
    """"Holy, Holy, Holy — #138"; just the title when the number is unknown."""
    return title if number is None else f"{title} — #{number}"


def resolve_doc_readings(scriptures: list[str], selected_ot_ref: str = "",
                         selected_nt_ref: str = "") -> tuple[Optional[str], Optional[str]]:
    """The first and NT readings the files print: scripture_refs.resolve_readings,
    nothing more (a stale pick is ignored; a None reading leaves its section out)."""
    pair = scripture_refs.resolve_readings(list(scriptures), selected_ot_ref, selected_nt_ref)
    return pair.ot, pair.nt


def is_legacy_error_placeholder(text: str) -> bool:
    """Streamlit's stored generation errors (worship_service.py:713, 722, 764 before slice 4)."""
    stripped = text.strip()
    return stripped.endswith("]") and stripped.startswith(LEGACY_ERROR_PREFIXES)
````

- [ ] **Step 4 (agent): Run the file and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_service_output.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `6 passed in <t>s`; `1229 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/service_output.py backend/tests/test_service_output.py backend/tests/fixtures/shared/docx_filenames.json
git commit -q -m "Backend: service_output, the Word files' date line, names and headers (5a-1; owner answer 3)" -m "New pure module (slice 5a spec, service_output.py): the date as Streamlit
printed it ('October 04, 2026', English months whatever the locale), the
filenames worship_{date}.docx and worship_pastor_{date}.docx, the F 1.9
headers, the two variants (both print the sermon title), hymn_line without
'#None', resolve_doc_readings (slice 2's resolve_readings) and Streamlit's
stored error texts. The shared fixture docx_filenames.json pins the names
for the TypeScript side too." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 1: backend **1229 passed, 11 skipped**; frontend **597 in 78**.

### Task 2: `build_docx` keeps Streamlit's layout, with headings by slot and "First Reading" (owner answer 3; S "Changed modules", behavior changes 5, 6, 7, 20; F §2.3.1; clarification 12)

**Files:**
- Create: `backend/tests/test_build_docx_characterization.py`
- Modify: `backend/worship_service.py`, `backend/service_output.py`, `backend/tests/test_liturgy_config.py`, `backend/tests/test_communion_docx.py`

- [ ] **Step 1 (agent): Write the failing tests: the old function, copied verbatim, and the parity and change tests**

`legacy_build_docx` is `build_docx` exactly as it is at `934ffb9`, statement for statement (its docstring, its python-docx check and its numbered comments left out). The three helpers whose output the parity rests on (`_add_leader_people_paragraph`, `_add_assurance_paragraph`, `_add_custom_elements_after`) are copied verbatim from `934ffb9` into the test too, so a later change to `worship_service`'s helpers cannot move both sides at once; `_add_communion_liturgy` (the text of `liturgy_config.COMMUNION_BLOCKS`, pinned by `test_communion_docx.py`) stays imported (clarification 12).

**Create `backend/tests/test_build_docx_characterization.py`:**

````python
"""The Word file keeps Streamlit's layout (slice 5a spec, Testing
"Characterization comes first"; F §2.3.1; owner answer 3, 2026-10-01: exact
parity). legacy_build_docx is a verbatim copy of worship_service.build_docx as
it was before slice 5a (main at 934ffb9), with verbatim copies of the three
helpers it calls whose output the parity rests on (so a later change to them in
worship_service cannot move both sides at once; the communion helper, pinned by
test_communion_docx.py, is imported); each case renders both and compares the
document XML in the same run, so the python-docx version cannot matter. The only differences allowed are the
documented ones: the first reading's heading reads "First Reading", hymn
headings follow slots, a hymn without a number prints no "#None", and the
readings come from resolve_readings (render_docx)."""
import re
from datetime import date
from io import BytesIO
from typing import Any, Dict, List, Optional

import pytest
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

import liturgy_config as lc
import service_output as so
import worship_service
from liturgy_config import ASSURANCE_RESPONSE
from worship_service import _add_communion_liturgy

# --- worship_service's helpers as they were at 934ffb9, verbatim ---


def _add_leader_people_paragraph(doc, text: str) -> None:
    """Add paragraph(s): each Leader: (normal), each People: (bold). Supports multiple Leader/People pairs."""
    if not text or not text.strip():
        return
    # Find all "Leader:" and "People:" in order (case-insensitive)
    pattern = re.compile(r"\b(Leader|People):\s*", re.IGNORECASE)
    pos = 0
    parts = []
    for m in pattern.finditer(text):
        if m.start() > pos:
            parts.append(("", text[pos : m.start()].strip()))  # preamble if any
        role = "Leader" if m.group(1).lower() == "leader" else "People"
        end = pattern.search(text, m.end())
        content_end = end.start() if end else len(text)
        content = text[m.end() : content_end].strip()
        parts.append((role, content))
        pos = content_end
    if not parts:
        doc.add_paragraph(text)
        return
    for role, content in parts:
        if not content and role == "":
            continue
        if role == "People":
            p = doc.add_paragraph()
            p.add_run("People: ")
            r = p.add_run(content)
            r.bold = True
        else:
            line = ("Leader: " + content) if role == "Leader" else content
            if line:
                doc.add_paragraph(line)


def _add_assurance_paragraph(doc, leader_text: str) -> None:
    """Add Assurance: Leader line then liturgy_config.ASSURANCE_RESPONSE in bold
    (the one copy the 4b card shows too)."""
    leader_clean = (leader_text or "").strip()
    if leader_clean.startswith("Leader:"):
        leader_clean = leader_clean[7:].strip()
    if leader_clean:
        doc.add_paragraph("Leader: " + leader_clean)
    # Always add the congregational response
    p = doc.add_paragraph()
    r = p.add_run(ASSURANCE_RESPONSE)
    r.bold = True


def _add_custom_elements_after(
    doc,
    anchor: str,
    custom_elements: List[Dict[str, Any]],
) -> None:
    """Add any custom elements that are inserted after this anchor."""
    for ce in custom_elements:
        if ce.get("insert_after") == anchor and ce.get("label"):
            doc.add_paragraph(ce["label"], style="Heading 2")
            if ce.get("text"):
                doc.add_paragraph(ce["text"])
            doc.add_paragraph()


# --- worship_service.build_docx as it was at 934ffb9, verbatim ---


def legacy_build_docx(
    *,
    occasion: str,
    date: str,
    scriptures: List[str],
    hymns: List[Dict[str, str]],
    liturgy: Dict[str, str],
    include_placeholders: bool = True,
    sermon_title: Optional[str] = None,
    selected_ot_ref: Optional[str] = None,
    selected_nt_ref: Optional[str] = None,
    scripture_full_texts: Optional[Dict[str, str]] = None,
    include_sermon: bool = True,
    include_prayers_of_the_people: bool = True,
    include_communion: bool = False,
    custom_elements: Optional[List[Dict[str, Any]]] = None,
) -> BytesIO:
    custom = custom_elements or []
    doc = Document()
    style = doc.styles["Normal"]
    style.font.size = Pt(11)
    style.font.name = "Times New Roman"

    # Title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(f"Worship Service\n{occasion}")
    run.bold = True
    run.font.size = Pt(16)
    run.font.name = "Times New Roman"
    if date:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(date).font.size = Pt(12)
    doc.add_paragraph()

    if liturgy.get("call_to_worship"):
        doc.add_paragraph("Call to Worship", style="Heading 2")
        _add_leader_people_paragraph(doc, liturgy["call_to_worship"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "call_to_worship", custom)

    if liturgy.get("opening_prayer"):
        doc.add_paragraph("Opening Prayer", style="Heading 2")
        doc.add_paragraph(liturgy["opening_prayer"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "opening_prayer", custom)

    if hymns:
        doc.add_paragraph("First Hymn", style="Heading 2")
        h = hymns[0]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()
    _add_custom_elements_after(doc, "first_hymn", custom)

    if liturgy.get("prayer_of_confession"):
        doc.add_paragraph("Prayer of Confession", style="Heading 2")
        p = doc.add_paragraph()
        p.add_run(liturgy["prayer_of_confession"]).bold = True
        doc.add_paragraph()
    _add_custom_elements_after(doc, "prayer_of_confession", custom)

    if liturgy.get("assurance"):
        doc.add_paragraph("Assurance of Pardon", style="Heading 2")
        _add_assurance_paragraph(doc, liturgy["assurance"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "assurance", custom)

    if liturgy.get("prayer_for_illumination"):
        doc.add_paragraph("Prayer for Illumination", style="Heading 2")
        doc.add_paragraph(liturgy["prayer_for_illumination"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "prayer_for_illumination", custom)

    ot_ref = selected_ot_ref or (scriptures[0] if scriptures else None)
    if ot_ref:
        doc.add_paragraph("Old Testament Reading", style="Heading 2")
        doc.add_paragraph(ot_ref)
        doc.add_paragraph()
    _add_custom_elements_after(doc, "ot_reading", custom)

    nt_ref = selected_nt_ref or (scriptures[1] if len(scriptures) > 1 else None)
    if nt_ref:
        doc.add_paragraph("New Testament Reading", style="Heading 2")
        doc.add_paragraph(nt_ref)
        doc.add_paragraph()
    _add_custom_elements_after(doc, "nt_reading", custom)

    if include_sermon:
        doc.add_paragraph("Sermon Title", style="Heading 2")
        doc.add_paragraph(sermon_title.strip() if sermon_title and sermon_title.strip() else "[Sermon title]")
        doc.add_paragraph()
    _add_custom_elements_after(doc, "sermon", custom)

    doc.add_paragraph("Affirmation of Faith", style="Heading 2")
    doc.add_paragraph("Apostles' Creed")
    doc.add_paragraph()
    _add_custom_elements_after(doc, "affirmation_of_faith", custom)

    if len(hymns) > 1:
        doc.add_paragraph("Second Hymn", style="Heading 2")
        h = hymns[1]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()
    _add_custom_elements_after(doc, "second_hymn", custom)

    if include_communion:
        _add_communion_liturgy(doc)
    _add_custom_elements_after(doc, "communion", custom)

    if include_prayers_of_the_people and liturgy.get("prayers_of_the_people"):
        doc.add_paragraph("Prayers of the People", style="Heading 2")
        doc.add_paragraph(liturgy["prayers_of_the_people"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "prayers_of_the_people", custom)

    if liturgy.get("offertory_prayer"):
        doc.add_paragraph("Offertory Prayer", style="Heading 2")
        doc.add_paragraph(liturgy["offertory_prayer"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "offertory_prayer", custom)

    if len(hymns) > 2:
        doc.add_paragraph("Third Hymn", style="Heading 2")
        h = hymns[2]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()
    _add_custom_elements_after(doc, "third_hymn", custom)
    _add_custom_elements_after(doc, "benediction", custom)

    if liturgy.get("benediction"):
        doc.add_paragraph("Benediction", style="Heading 2")
        doc.add_paragraph(liturgy["benediction"])

    _add_custom_elements_after(doc, "end", custom)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


LITURGY = {
    "call_to_worship": "Leader: The Lord be with you. People: And also with you. Leader: Let us worship God.",
    "opening_prayer": "Gracious God, we gather in your name.",
    "prayer_of_confession": "Merciful God, we confess that we have not loved you.",
    "assurance": "Leader: In Jesus Christ we are forgiven.",
    "prayer_for_illumination": "Open our hearts by your Spirit.",
    "prayers_of_the_people": "We pray for the church and the world.",
    "offertory_prayer": "Receive these gifts.",
    "benediction": "Go in peace.",
}
HYMNS = [{"title": "Holy, Holy, Holy", "number": 138}, {"title": "Be Thou My Vision", "number": 450},
         {"title": "Amazing Grace", "number": 649}]
CUSTOM = [{"label": f"CE {key}", "text": f"Text after {key}.", "insert_after": key}
          for key, _label in lc.CUSTOM_PLACEMENTS]


def outline(content: bytes) -> list[tuple[str, str, bool]]:
    """(style, text, any run bold) for every paragraph."""
    return [(p.style.name, p.text, any(r.bold for r in p.runs)) for p in Document(BytesIO(content)).paragraphs]


def body_xml(content: bytes) -> str:
    return Document(BytesIO(content)).element.body.xml


def new_kwargs(*, hymns=HYMNS, ot="Isaiah 5:1-7", nt="Philippians 3:4b-14", **kw):
    slots = dict(zip(("opening", "response", "closing"), [*hymns, None, None, None]))
    return dict(occasion="World Communion Sunday", date_display="October 04, 2026",
                hymns_by_slot=slots, liturgy=dict(LITURGY), ot_ref=ot, nt_ref=nt,
                sermon_title="Living Water", include_communion=True, custom_elements=CUSTOM, **kw)


def legacy_kwargs(*, hymns=HYMNS, ot="Isaiah 5:1-7", nt="Philippians 3:4b-14", **kw):
    return dict(occasion="World Communion Sunday", date="October 04, 2026",
                scriptures=[s for s in (ot, nt) if s], hymns=list(hymns), liturgy=dict(LITURGY),
                selected_ot_ref=ot, selected_nt_ref=nt, sermon_title="Living Water",
                include_communion=True, custom_elements=CUSTOM, **kw)


@pytest.mark.parametrize("prayers", [False, True], ids=["bulletin", "pastor"])
def test_a_full_service_prints_exactly_as_streamlit_did_but_for_the_first_reading_heading(prayers):
    new = worship_service.build_docx(**new_kwargs(include_sermon=True, include_prayers_of_the_people=prayers))
    old = legacy_build_docx(**legacy_kwargs(include_sermon=True, include_prayers_of_the_people=prayers)).getvalue()
    assert isinstance(new, bytes)
    assert body_xml(new) == body_xml(old).replace("Old Testament Reading", "First Reading")
    assert Document(BytesIO(new)).styles.element.xml == Document(BytesIO(old)).styles.element.xml
    texts = [text for _style, text, _bold in outline(new)]
    assert "First Reading" in texts and "Old Testament Reading" not in texts
    assert ("Prayers of the People" in texts) is prayers


def test_a_sparse_service_prints_as_before_with_every_anchor():
    """No hymns, no readings, no communion, one section, an unknown liturgy key:
    every custom element still prints at its place (inv E5)."""
    liturgy = {"benediction": "Go in peace.", "notion_extra": "Never printed."}
    new = worship_service.build_docx(
        occasion="Ordinary Sunday", date_display="", hymns_by_slot={}, liturgy=liturgy, ot_ref=None, nt_ref=None,
        sermon_title="", include_sermon=True, include_prayers_of_the_people=True, include_communion=False,
        custom_elements=CUSTOM)
    old = legacy_build_docx(occasion="Ordinary Sunday", date="", scriptures=[], hymns=[], liturgy=liturgy,
                            sermon_title="", custom_elements=CUSTOM).getvalue()
    assert body_xml(new) == body_xml(old)
    texts = [text for _style, text, _bold in outline(new)]
    assert [t for t in texts if t.startswith("CE ")] == [f"CE {key}" for key, _ in lc.CUSTOM_PLACEMENTS]
    assert "[Sermon title]" in texts and "Never printed." not in texts


def test_the_title_date_fonts_and_bold_text_are_unchanged():
    doc = Document(BytesIO(worship_service.build_docx(**new_kwargs(include_sermon=True,
                                                                   include_prayers_of_the_people=True))))
    normal = doc.styles["Normal"].font
    assert (normal.name, normal.size) == ("Times New Roman", Pt(11))
    title, when = doc.paragraphs[0], doc.paragraphs[1]
    assert title.text == "Worship Service\nWorld Communion Sunday" and title.alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert (title.runs[0].bold, title.runs[0].font.size) == (True, Pt(16))
    assert when.text == "October 04, 2026" and when.runs[0].font.size == Pt(12)
    rows = [(p.style.name, p.text, any(r.bold for r in p.runs)) for p in doc.paragraphs]
    assert ("Normal", "People: And also with you.", True) in rows
    assert ("Normal", LITURGY["prayer_of_confession"], True) in rows
    assert ("Normal", lc.ASSURANCE_RESPONSE, True) in rows
    assert ("Heading 2", "Call to Worship", False) in rows


def test_hymn_headings_follow_slots_and_never_print_none():
    content = worship_service.build_docx(**new_kwargs(
        hymns=[None, {"title": "Be Thou My Vision", "number": 450}, {"title": "Old Favorite", "number": None}],
        include_sermon=True, include_prayers_of_the_people=False))
    texts = [text for _style, text, _bold in outline(content)]
    assert "First Hymn" not in texts                       # Streamlit printed the Response hymn here (inv D6)
    assert texts[texts.index("Second Hymn") + 1] == "Be Thou My Vision — #450"
    assert texts[texts.index("Third Hymn") + 1] == "Old Favorite"
    assert not any("#None" in t for t in texts)
    assert texts.index("CE first_hymn") < texts.index("Prayer of Confession")      # the anchor still prints


def _resolved(**kw):
    base = dict(service_date=date(2026, 10, 4), occasion="Nineteenth Sunday after Pentecost",
                scriptures=("Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"),
                hymns={"opening": so.ResolvedHymn("Holy, Holy, Holy", 138), "response": None, "closing": None},
                liturgy={"prayers_of_the_people": "We pray.", "benediction": "Go in peace."},
                sermon_title="", selected_ot_ref="", selected_nt_ref="", include_communion=False,
                custom_elements=(so.CustomElement("Anthem", "Choir", "sermon"),))
    return so.ResolvedService(**{**base, **kw})


def _after(texts: list[str], heading: str) -> str:
    return texts[texts.index(heading) + 1]


def test_render_docx_prints_the_readings_the_screen_shows():
    texts = [t for _s, t, _b in outline(so.render_docx(_resolved(selected_nt_ref="Matthew 21:33-40"), "pastor"))]
    assert _after(texts, "First Reading") == "Isaiah 5:1-7"
    assert _after(texts, "New Testament Reading") == "Philippians 3:4b-14"      # the stale pick is ignored
    easter = _resolved(scriptures=("Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"))
    for variant in ("bulletin", "pastor"):
        texts = [t for _s, t, _b in outline(so.render_docx(easter, variant))]
        assert _after(texts, "First Reading") == "Acts 10:34-43"
        assert _after(texts, "New Testament Reading") == "Colossians 3:1-4"
        assert "Old Testament Reading" not in texts


def test_render_docx_variants():
    bulletin = [t for _s, t, _b in outline(so.render_docx(_resolved(), "bulletin"))]
    pastor = [t for _s, t, _b in outline(so.render_docx(_resolved(), "pastor"))]
    assert "Sermon Title" in bulletin and "[Sermon title]" in bulletin and "Prayers of the People" not in bulletin
    assert "Sermon Title" in pastor and _after(pastor, "Prayers of the People") == "We pray."
    assert _after(bulletin, "First Hymn") == "Holy, Holy, Holy — #138" and "Second Hymn" not in bulletin
    assert _after(bulletin, "Anthem") == "Choir"
    assert bulletin.index("Anthem") > bulletin.index("Sermon Title")
    communion = [t for _s, t, _b in outline(so.render_docx(_resolved(include_communion=True), "bulletin"))]
    assert communion.index(lc.COMMUNION_TITLE) > communion.index("Affirmation of Faith")


def test_without_python_docx_it_raises(monkeypatch):
    monkeypatch.setattr(worship_service, "Document", None)
    with pytest.raises(RuntimeError, match="python-docx is required"):
        so.render_docx(_resolved(), "bulletin")
````

- [ ] **Step 2 (agent): Run it and see it fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_build_docx_characterization.py 2>&1 | tail -10
```

**Expected:** eight `FAILED` lines (the `build_docx` tests with `TypeError: build_docx() got an unexpected keyword argument 'date_display'`, the `render_docx` ones with `AttributeError: module 'service_output' has no attribute 'ResolvedHymn'`), then `8 failed in <t>s`:
```
FAILED backend/tests/test_build_docx_characterization.py::test_a_full_service_prints_exactly_as_streamlit_did_but_for_the_first_reading_heading[bulletin]
FAILED backend/tests/test_build_docx_characterization.py::test_a_full_service_prints_exactly_as_streamlit_did_but_for_the_first_reading_heading[pastor]
FAILED backend/tests/test_build_docx_characterization.py::test_a_sparse_service_prints_as_before_with_every_anchor
FAILED backend/tests/test_build_docx_characterization.py::test_the_title_date_fonts_and_bold_text_are_unchanged
FAILED backend/tests/test_build_docx_characterization.py::test_hymn_headings_follow_slots_and_never_print_none
FAILED backend/tests/test_build_docx_characterization.py::test_render_docx_prints_the_readings_the_screen_shows
FAILED backend/tests/test_build_docx_characterization.py::test_render_docx_variants
FAILED backend/tests/test_build_docx_characterization.py::test_without_python_docx_it_raises
```

- [ ] **Step 3 (agent): The two older tests that call `build_docx` move to the new signature; `DOCX_HEADINGS_UNTIL_5A` goes**

**In `backend/tests/test_liturgy_config.py`, replace:**

````python
# The docx still prints "Old Testament Reading" until 5a renames it to OUTLINE's
# "First Reading" (owner decision B; slice 4a plan, clarification 4). 5a deletes
# this map when it changes build_docx.
DOCX_HEADINGS_UNTIL_5A = {"ot_reading": "Old Testament Reading"}


def test_the_outline_is_build_docx_s_heading_order():
    from docx import Document

    import worship_service

    buf = worship_service.build_docx(
        occasion="World Communion Sunday", date="October 4, 2026",
        scriptures=["Isaiah 5:1-7", "Matthew 21:33-46"],
        hymns=[{"title": f"Hymn {n}", "number": n} for n in (1, 2, 3)],
        liturgy={key: f"Text of {key}." for key in lc.SECTION_ORDER},
        sermon_title="Living Water", selected_ot_ref="Isaiah 5:1-7", selected_nt_ref="Matthew 21:33-46",
        include_sermon=True, include_prayers_of_the_people=True, include_communion=True,
        custom_elements=[{"label": f"CE:{key}", "text": "", "insert_after": key}
                         for key, _label in lc.CUSTOM_PLACEMENTS])
    communion_inside = {b.text for b in lc.COMMUNION_BLOCKS if b.style == "heading2"}
    printed = [p.text for p in Document(buf).paragraphs
               if p.style.name in ("Heading 1", "Heading 2") and p.text not in communion_inside]
    expected = []
    for item in lc.OUTLINE:
        expected.append(DOCX_HEADINGS_UNTIL_5A.get(item.key, item.label))
        expected.extend(f"CE:{anchor}" for anchor in item.anchors_after)
````

**with:**

````python
def test_the_outline_is_build_docx_s_heading_order():
    from io import BytesIO

    from docx import Document

    import worship_service

    content = worship_service.build_docx(
        occasion="World Communion Sunday", date_display="October 04, 2026",
        hymns_by_slot={slot: {"title": f"Hymn {n}", "number": n}
                       for n, slot in enumerate(("opening", "response", "closing"), start=1)},
        liturgy={key: f"Text of {key}." for key in lc.SECTION_ORDER},
        ot_ref="Isaiah 5:1-7", nt_ref="Matthew 21:33-46", sermon_title="Living Water",
        include_sermon=True, include_prayers_of_the_people=True, include_communion=True,
        custom_elements=[{"label": f"CE:{key}", "text": "", "insert_after": key}
                         for key, _label in lc.CUSTOM_PLACEMENTS])
    communion_inside = {b.text for b in lc.COMMUNION_BLOCKS if b.style == "heading2"}
    printed = [p.text for p in Document(BytesIO(content)).paragraphs
               if p.style.name in ("Heading 1", "Heading 2") and p.text not in communion_inside]
    expected = []
    for item in lc.OUTLINE:              # the docx prints OUTLINE's labels, "First Reading" included (5a)
        expected.append(item.label)
        expected.extend(f"CE:{anchor}" for anchor in item.anchors_after)
````

**In `backend/tests/test_communion_docx.py`, replace:**

````python
def _service(**overrides):
    kwargs = dict(
        occasion="World Communion Sunday", date="October 4, 2026",
        scriptures=["Isaiah 5:1-7", "Matthew 21:33-46"],
        hymns=[{"title": "Be Thou My Vision", "number": 450}, {"title": "Come, Thou Fount", "number": 475}],
        liturgy={"prayers_of_the_people": "We pray.", "benediction": "Go in peace."},
        include_communion=True)
    return worship_service.build_docx(**{**kwargs, **overrides})
````

**with:**

````python
def _service(**overrides):
    kwargs = dict(
        occasion="World Communion Sunday", date_display="October 04, 2026",
        hymns_by_slot={"opening": {"title": "Be Thou My Vision", "number": 450},
                       "response": {"title": "Come, Thou Fount", "number": 475}, "closing": None},
        liturgy={"prayers_of_the_people": "We pray.", "benediction": "Go in peace."},
        ot_ref="Isaiah 5:1-7", nt_ref="Matthew 21:33-46", include_communion=True)
    return BytesIO(worship_service.build_docx(**{**kwargs, **overrides}))      # bytes since slice 5a
````

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_config.py backend/tests/test_communion_docx.py 2>&1 | tail -4
```

**Expected:** (the old `build_docx` refuses `date_display`)
```
FAILED backend/tests/test_liturgy_config.py::test_the_outline_is_build_docx_s_heading_order
FAILED backend/tests/test_communion_docx.py::test_the_word_file_with_communion_is_unchanged
FAILED backend/tests/test_communion_docx.py::test_the_word_file_s_assurance_line_is_liturgy_config_s
3 failed, 11 passed in <t>s
```

- [ ] **Step 4 (agent): The new signature, `_add_hymn`, "First Reading", bytes; `render_docx`**

**In `backend/worship_service.py`, replace:**

````python
moved to liturgy_prompts and usecases.liturgy in slice 4.
"""
````

**with:**

````python
moved to liturgy_prompts and usecases.liturgy in slice 4. Slice 5a renders
the files through service_output.render_docx (POST /documents).
"""
````

**In `backend/worship_service.py`, replace:**

````python
import re
from typing import Dict, Any, List, Optional
from io import BytesIO

from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS

````

**with:**

````python
import re
from collections.abc import Mapping, Sequence
from typing import Dict, Any, List, Optional
from io import BytesIO

from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS
from service_output import hymn_line

````

**In `backend/worship_service.py`, replace:**

````python
def build_docx(
    *,
    occasion: str,
    date: str,
    scriptures: List[str],
    hymns: List[Dict[str, str]],
    liturgy: Dict[str, str],
    include_placeholders: bool = True,
    sermon_title: Optional[str] = None,
    selected_ot_ref: Optional[str] = None,
    selected_nt_ref: Optional[str] = None,
    scripture_full_texts: Optional[Dict[str, str]] = None,
    include_sermon: bool = True,
    include_prayers_of_the_people: bool = True,
    include_communion: bool = False,
    custom_elements: Optional[List[Dict[str, Any]]] = None,
) -> BytesIO:
    """
    Build a Word document with the worship service order and generated liturgy.
    include_sermon: include Sermon Title section (for pastor copy; omit for secretary).
    include_prayers_of_the_people: include Prayers of the People (for pastor copy; omit for secretary).
    include_communion: include The Sacrament of the Lord's Supper liturgy (e.g. first Sunday of month).
    Returns a BytesIO buffer containing the .docx.
    """
    if not Document:
        raise RuntimeError("python-docx is required. pip install python-docx")

    custom = custom_elements or []

````

**with:**

````python
def _add_hymn(doc, heading: str, hymn: Optional[Mapping[str, Any]]) -> None:
    """A filled slot's heading and line; an empty slot prints nothing (5a: headings by slot)."""
    if hymn is None:
        return
    doc.add_paragraph(heading, style="Heading 2")
    doc.add_paragraph(hymn_line(hymn.get("title") or "", hymn.get("number")))
    doc.add_paragraph()


def build_docx(
    *,
    occasion: str,
    date_display: str,
    hymns_by_slot: Mapping[str, Optional[Mapping[str, Any]]],
    liturgy: Mapping[str, str],
    ot_ref: Optional[str],
    nt_ref: Optional[str],
    sermon_title: str = "",
    include_sermon: bool = True,
    include_prayers_of_the_people: bool = True,
    include_communion: bool = False,
    custom_elements: Sequence[Mapping[str, Any]] = (),
) -> bytes:
    """
    The Word file of a service: Streamlit's layout, paragraph for paragraph
    (Times New Roman 11 pt, Word's Heading 2, the bold People lines and
    confession), with slice 5a's changes: hymn headings follow slots
    (opening "First Hymn", response "Second Hymn", closing "Third Hymn"; an
    empty slot prints nothing), a hymn without a number prints no "#None", and
    the first reading's heading is "First Reading". ot_ref and nt_ref arrive
    resolved (service_output.resolve_doc_readings); None leaves a reading out.
    Both variants include the sermon title; only the pastor's copy includes
    Prayers of the People (service_output.VARIANTS). Custom elements print
    after their anchor, which is emitted even when its item is absent.
    Returns the .docx bytes.
    """
    if not Document:
        raise RuntimeError("python-docx is required. pip install python-docx")

    custom = list(custom_elements)

````

**In `backend/worship_service.py`, replace:**

````python
    if date:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(date).font.size = Pt(12)

````

**with:**

````python
    if date_display:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(date_display).font.size = Pt(12)

````

**In `backend/worship_service.py`, replace:**

````python
    # 3. First Hymn
    if hymns:
        doc.add_paragraph("First Hymn", style="Heading 2")
        h = hymns[0]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()

````

**with:**

````python
    # 3. First Hymn (the opening slot)
    _add_hymn(doc, "First Hymn", hymns_by_slot.get("opening"))

````

**In `backend/worship_service.py`, replace:**

````python
    # 7. Old Testament Reading (reference only)
    ot_ref = selected_ot_ref or (scriptures[0] if scriptures else None)
    if ot_ref:
        doc.add_paragraph("Old Testament Reading", style="Heading 2")

````

**with:**

````python
    # 7. First Reading (reference only; owner decision B renamed "Old Testament Reading")
    if ot_ref:
        doc.add_paragraph("First Reading", style="Heading 2")

````

**In `backend/worship_service.py`, replace:**

````python
    # 8. New Testament Reading (reference only)
    nt_ref = selected_nt_ref or (scriptures[1] if len(scriptures) > 1 else None)
    if nt_ref:

````

**with:**

````python
    # 8. New Testament Reading (reference only)
    if nt_ref:

````

**In `backend/worship_service.py`, replace:**

````python
    # 9. Sermon Title (optional; for pastor copy only)

````

**with:**

````python
    # 9. Sermon Title (both copies)

````

**In `backend/worship_service.py`, replace:**

````python
    # 11. Second Hymn
    if len(hymns) > 1:
        doc.add_paragraph("Second Hymn", style="Heading 2")
        h = hymns[1]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()
    _add_custom_elements_after(doc, "second_hymn", custom)

    # 11b. Communion liturgy (after second hymn when communion is included)

````

**with:**

````python
    # 11. Second Hymn (the response slot)
    _add_hymn(doc, "Second Hymn", hymns_by_slot.get("response"))
    _add_custom_elements_after(doc, "second_hymn", custom)

    # 11b. Communion liturgy (after the second hymn when communion is included)

````

**In `backend/worship_service.py`, replace:**

````python
    # 12. Prayers of the People (optional; for pastor copy only)

````

**with:**

````python
    # 12. Prayers of the People (the pastor's copy only)

````

**In `backend/worship_service.py`, replace:**

````python
    # 14. Third Hymn
    if len(hymns) > 2:
        doc.add_paragraph("Third Hymn", style="Heading 2")
        h = hymns[2]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()

````

**with:**

````python
    # 14. Third Hymn (the closing slot)
    _add_hymn(doc, "Third Hymn", hymns_by_slot.get("closing"))

````

**In `backend/worship_service.py`, replace:**

````python
    doc.save(buf)
    buf.seek(0)
    return buf
````

**with:**

````python
    doc.save(buf)
    return buf.getvalue()
````

**In `backend/service_output.py`, replace:**

````python
import datetime
from typing import Literal, Optional
from urllib.parse import quote

````

**with:**

````python
import datetime
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Optional
from urllib.parse import quote

````

**Append to `backend/service_output.py`:**

````python


SLOTS = ("opening", "response", "closing")


@dataclass(frozen=True)
class ResolvedHymn:
    """A slot's hymn as it prints: the database's title and number for a hymn id, else the snapshot sent."""
    title: str
    number: Optional[int]
    hymn_id: Optional[object] = None          # uuid.UUID when the hymn is in the church's hymnal
    hymnal: Optional[str] = None


@dataclass(frozen=True)
class CustomElement:
    label: str
    text: str
    insert_after: str                          # a liturgy_config placement key


@dataclass(frozen=True)
class ResolvedService:
    """A service ready to print: cleaned input with its hymns resolved (usecases.documents)."""
    service_date: datetime.date
    occasion: str = ""
    scriptures: tuple[str, ...] = ()
    hymns: Mapping[str, Optional[ResolvedHymn]] = field(default_factory=dict)
    liturgy: Mapping[str, str] = field(default_factory=dict)
    sermon_title: str = ""
    selected_ot_ref: str = ""
    selected_nt_ref: str = ""
    include_communion: bool = False
    custom_elements: tuple[CustomElement, ...] = ()


def render_docx(resolved: ResolvedService, variant: Variant) -> bytes:
    """The Word file of one variant: worship_service.build_docx with the resolved
    readings, the slot hymns and the variant's flags."""
    import worship_service          # here, not at the top: worship_service imports hymn_line from this module

    ot, nt = resolve_doc_readings(list(resolved.scriptures), resolved.selected_ot_ref, resolved.selected_nt_ref)
    hymns = {slot: None if (h := resolved.hymns.get(slot)) is None else {"title": h.title, "number": h.number}
             for slot in SLOTS}
    return worship_service.build_docx(
        occasion=resolved.occasion,
        date_display=service_date_display(resolved.service_date),
        hymns_by_slot=hymns,
        liturgy=dict(resolved.liturgy),
        ot_ref=ot,
        nt_ref=nt,
        sermon_title=resolved.sermon_title,
        include_communion=resolved.include_communion,
        custom_elements=[{"label": e.label, "text": e.text, "insert_after": e.insert_after}
                         for e in resolved.custom_elements],
        **VARIANTS[variant],
    )
````

- [ ] **Step 5 (agent): Run the four files and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_build_docx_characterization.py backend/tests/test_service_output.py backend/tests/test_liturgy_config.py backend/tests/test_communion_docx.py 2>&1 | tail -1
grep -n 'DOCX_HEADINGS_UNTIL_5A\|paragraph("Old Testament Reading"' backend/worship_service.py backend/tests/test_liturgy_config.py; echo "old heading grep exit $?"
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `28 passed in <t>s`; `old heading grep exit 1`; `1237 passed, 11 skipped in <t>s`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/worship_service.py backend/service_output.py backend/tests/test_build_docx_characterization.py backend/tests/test_liturgy_config.py backend/tests/test_communion_docx.py
git commit -q -m "Backend: build_docx keeps Streamlit's layout, with hymn headings by slot and First Reading (5a-1; owner answer 3)" -m "build_docx takes the slice 5a spec's keyword signature (slot hymns,
resolved readings, the date line) and returns bytes; an empty hymn slot
prints nothing, a hymn without a number prints no '#None', and the first
reading's heading is 'First Reading'. A verbatim copy of the old function
pins everything else: the document XML is compared in the same run.
service_output.render_docx renders a resolved service in either variant.
test_liturgy_config loses DOCX_HEADINGS_UNTIL_5A: OUTLINE's labels are the
docx headings." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 2: backend **1237 passed, 11 skipped**; frontend **597 in 78**.

### Task 3: `POST /documents` (S API, "Schemas", `usecases/documents.py`, `usecases/archive.py`'s input rows; F §1.9; owner decision 5; clarifications 6, 7, 8, 13, 17)

**Files:**
- Create: `backend/usecases/archive.py`, `backend/usecases/documents.py`, `backend/api/routes/documents.py`, `backend/tests/test_usecase_documents.py`, `backend/tests/test_api_documents.py`
- Modify: `backend/api/schemas.py`, `backend/api/main.py`, `backend/tests/test_no_streamlit_in_core.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (regenerated)

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_usecase_documents.py`:**

````python
"""usecases.documents.build_document and the parts of usecases.archive it uses
(slice 5a spec, Backend "usecases/documents.py", "usecases/archive.py"; Testing
`test_archive_usecase.py`'s input and hymn cases, and "build_document writes no
usage")."""
import logging
import uuid
from datetime import date
from io import BytesIO

import pytest
from docx import Document
from sqlalchemy import func, select

from db import session_scope
from db.models import Hymn, HymnUsage, Service
from domain_errors import InvalidInput, NotFound
from service_output import CustomElement, ResolvedHymn
from usecases import archive, documents
from usecases.liturgy import HymnRefData

HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."


@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email="pastor@example.com"))


def add_hymn(church_id, title="Holy, Holy, Holy", number=138, hymnal="GG2013"):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number)
        s.add(row)
        s.flush()
        return row.id


def service(**kw):
    base = dict(service_date=date(2026, 10, 4), occasion="  World Communion Sunday ",
                scriptures=(" Isaiah 5:1-7", "", "Psalm 80:7-15", "Philippians 3:4b-14 ", "Matthew 21:33-46"),
                liturgy={"call_to_worship": " Leader: Come. People: We come. ", "opening_prayer": "   ",
                         "prayers_of_the_people": "We pray for the world.",
                         "offertory_prayer": "[Error generating offertory_prayer: timeout]"},
                sermon_title=" Living Water ")
    return archive.ServiceInput(**{**base, **kw})


def texts(content: bytes) -> list[str]:
    return [p.text for p in Document(BytesIO(content)).paragraphs]


def test_clean_input_trims_and_drops_blanks_and_streamlit_errors():
    clean = archive.clean_input(service(
        hymns={"opening": HymnRefData(None, "  Old Favorite ", 12, " PH1990 "), "response": None},
        hymnal="  ", selected_nt_ref=" Matthew 21:33-46 ",
        custom_elements=(CustomElement(" Anthem ", " Choir ", "sermon"),)))
    assert clean.occasion == "World Communion Sunday" and clean.sermon_title == "Living Water"
    assert clean.scriptures == ("Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46")
    assert clean.liturgy == {"call_to_worship": "Leader: Come. People: We come.",
                             "prayers_of_the_people": "We pray for the world."}
    assert clean.hymns == {"opening": HymnRefData(None, "Old Favorite", 12, "PH1990"), "response": None,
                           "closing": None}
    assert clean.hymnal is None and clean.selected_nt_ref == "Matthew 21:33-46"
    assert clean.custom_elements == (CustomElement("Anthem", "Choir", "sermon"),)


def test_a_blank_custom_label_is_a_422_on_its_field():
    with pytest.raises(InvalidInput) as caught:
        archive.clean_input(service(custom_elements=(CustomElement("Anthem", "", "sermon"),
                                                     CustomElement("  ", "Words", "end"))))
    assert (caught.value.message, caught.value.field) == ("Give each custom element a label.",
                                                          "custom_elements.1.label")


def test_hymn_ids_resolve_in_the_church_and_snapshots_are_kept(church, make_user, make_church):
    hymn = add_hymn(church)
    with session_scope() as s:
        resolved = archive.resolve_hymn_refs(s, church, {
            "opening": HymnRefData(hymn, "What the client says", 999, "XX"),
            "response": HymnRefData(None, "Old Favorite", None, "PH1990"),
            "closing": HymnRefData(None, "   ", 5, None)})
    assert resolved == {"opening": ResolvedHymn("Holy, Holy, Holy", 138, hymn, "GG2013"),
                        "response": ResolvedHymn("Old Favorite", None, None, "PH1990"), "closing": None}
    other = make_church(name="Other", owner_user_id=make_user(email="other@example.com"))
    for gone in (add_hymn(other), uuid.uuid4()):
        with session_scope() as s, pytest.raises(NotFound) as caught:
            archive.resolve_hymn_refs(s, church, {"opening": HymnRefData(hymn, "", None),
                                                  "response": HymnRefData(gone, "Their hymn", 1)})
        assert (caught.value.message, caught.value.details) == (HYMN_GONE, {"field": "hymns.response.hymn_id"})


def test_build_document_prints_the_cleaned_service_with_its_hymns(church, caplog):
    hymn = add_hymn(church)
    data = service(hymns={"opening": HymnRefData(hymn, "Stale title", 1), "response": None,
                          "closing": HymnRefData(None, "Old Favorite", None)})
    with caplog.at_level(logging.INFO, logger="usecases.documents"):
        bulletin = documents.build_document(church, data, "bulletin")
    pastor = documents.build_document(church, data, "pastor")
    assert bulletin.filename == "worship_October_04_2026.docx"
    assert pastor.filename == "worship_pastor_October_04_2026.docx"
    assert bulletin.content[:2] == b"PK"
    lines = texts(bulletin.content)
    assert lines[:2] == ["Worship Service\nWorld Communion Sunday", "October 04, 2026"]
    assert lines[lines.index("First Hymn") + 1] == "Holy, Holy, Holy — #138"
    assert "Second Hymn" not in lines and lines[lines.index("Third Hymn") + 1] == "Old Favorite"
    assert lines[lines.index("First Reading") + 1] == "Isaiah 5:1-7"
    assert lines[lines.index("New Testament Reading") + 1] == "Philippians 3:4b-14"
    assert lines[lines.index("Sermon Title") + 1] == "Living Water"
    assert "Opening Prayer" not in lines and "Offertory Prayer" not in lines
    assert "Prayers of the People" not in lines and "Prayers of the People" in texts(pastor.content)
    [record] = [r for r in caplog.records if r.name == "usecases.documents"]
    assert record.getMessage().startswith(f"documents.build church={church} variant=bulletin bytes=")
    assert "Living Water" not in record.getMessage() and "Communion" not in record.getMessage()


def test_build_document_writes_nothing(church):
    documents.build_document(church, service(hymns={"opening": HymnRefData(add_hymn(church), "", None)}), "pastor")
    with session_scope() as s:
        assert s.scalar(select(func.count()).select_from(HymnUsage)) == 0
        assert s.scalar(select(func.count()).select_from(Service)) == 0
````

**Create `backend/tests/test_api_documents.py`:**

````python
"""POST /documents (slice 5a spec, API; Testing `test_api_documents.py`;
acceptance criteria 1, 2, 10; F §1.9)."""
import uuid
from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient

import worship_service
from api import settings as settings_mod
from db import session_scope
from db.models import Hymn
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
ALLOWED_ORIGIN = "https://church.example.app"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."
SERVICE = {
    "service_date_iso": "2026-10-04",
    "occasion": "World Communion Sunday",
    "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
    "hymns": {"opening": {"hymn_id": None, "title": "Old Favorite", "number": 12, "hymnal": "PH1990"},
              "response": None, "closing": None},
    "hymnal": None,
    "liturgy": {"call_to_worship": "Leader: Come. People: We come.", "prayers_of_the_people": "We pray."},
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
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email=EMAIL))


def post(client, church_id, body, email=EMAIL, **headers):
    return client.post("/documents", json=body, headers={**church_headers(email, church_id), **headers})


def lines(content: bytes) -> list[str]:
    return [p.text for p in Document(BytesIO(content)).paragraphs]


def test_both_copies_download_with_the_file_headers(client, church):
    for variant, name in (("bulletin", "worship_October_04_2026.docx"),
                          ("pastor", "worship_pastor_October_04_2026.docx")):
        r = post(client, church, {"variant": variant, "service": SERVICE})
        assert r.status_code == 200, r.text
        assert r.content[:2] == b"PK"
        assert r.headers["content-type"] == DOCX
        assert r.headers["content-disposition"] == f"attachment; filename=\"{name}\"; filename*=UTF-8''{name}"
        assert r.headers["cache-control"] == "no-store"
        text = lines(r.content)
        assert "Sermon Title" in text and "Living Water" in text
        assert ("Prayers of the People" in text) is (variant == "pastor")
        assert "First Reading" in text and "Old Testament Reading" not in text
        assert text[text.index("First Hymn") + 1] == "Old Favorite — #12"


def test_the_filename_header_is_readable_cross_origin(tmp_db, church, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED_ORIGIN)
    settings_mod.get_settings.cache_clear()
    try:
        r = post(make_api_client(), church, {"variant": "bulletin", "service": SERVICE}, Origin=ALLOWED_ORIGIN)
    finally:
        settings_mod.get_settings.cache_clear()
    assert r.status_code == 200, r.text
    assert r.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "content-disposition" in {h.strip().lower() for h in r.headers["access-control-expose-headers"].split(",")}


def test_any_member_may_download(client, church, make_user):
    member = make_user(email="member@example.com")
    add_membership(member, church, "member")
    r = post(client, church, {"variant": "pastor", "service": SERVICE}, email="member@example.com")
    assert r.status_code == 200, r.text


def test_only_members_and_only_the_church_s_hymns(client, isolation_world):
    world = isolation_world
    assert_church_isolated(client, "POST", "/documents", world=world, json={"variant": "bulletin", "service": SERVICE})
    with session_scope() as s:
        theirs = Hymn(church_id=world.church_b, hymnal="GG2013", title="Their Hymn", number=1)
        s.add(theirs)
        s.flush()
        theirs_id = str(theirs.id)
    for hymn_id in (theirs_id, str(uuid.uuid4())):
        body = {"variant": "bulletin", "service": {**SERVICE, "hymns": {
            "opening": None, "response": {"hymn_id": hymn_id, "title": "Their Hymn", "number": 1, "hymnal": None}}}}
        r = post(client, world.church_a, body, email=world.a)
        assert r.status_code == 404, r.text
        error = r.json()["error"]
        assert (error["code"], error["message"], error["details"]) == (
            "not_found", HYMN_GONE, {"field": "hymns.response.hymn_id"})


@pytest.mark.parametrize("change, field", [
    ({"variant": "secretary"}, "variant"),
    ({"service": {**SERVICE, "service_date_iso": "2026-02-30"}}, "service.service_date_iso"),
    ({"service": {**SERVICE, "service_date_iso": "2026-10-04T00:00:00"}}, "service.service_date_iso"),
    ({"service": {**SERVICE, "extra": 1}}, "service.extra"),
    ({"service": {**SERVICE, "custom_elements": [{"label": "A", "text": "", "insert_after": "bogus"}]}},
     "service.custom_elements.0.insert_after"),
    ({"service": {**SERVICE, "occasion": "x" * 301}}, "service.occasion"),
])
def test_a_bad_body_is_a_422_naming_the_field(client, church, change, field):
    r = post(client, church, {"variant": "bulletin", "service": SERVICE, **change})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"], r.text


def test_a_blank_custom_label_is_the_usecase_s_422(client, church):
    body = {"variant": "bulletin", "service": {**SERVICE, "custom_elements": [
        {"label": "  ", "text": "Words", "insert_after": "end"}]}}
    r = post(client, church, body)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["fields"] == {"custom_elements.0.label": "Give each custom element a label."}


def test_characters_a_word_file_cannot_hold_are_cleaned_not_a_500(client, church):
    """A vertical tab (Word's soft line break, pasted) or a form feed becomes a
    line break; a NUL or another control character is dropped (clarification 19)."""
    service = {**SERVICE, "liturgy": {"opening_prayer": "a\x0bb\x00c"}, "sermon_title": "Living\x0cWater\x1f"}
    r = post(client, church, {"variant": "bulletin", "service": service})
    assert r.status_code == 200, r.text
    text = lines(r.content)
    assert text[text.index("Opening Prayer") + 1] == "a\nbc"
    assert text[text.index("Sermon Title") + 1] == "Living\nWater"


def test_a_label_of_only_a_nul_is_the_blank_label_422(client, church):
    body = {"variant": "bulletin", "service": {**SERVICE, "custom_elements": [
        {"label": "\x00", "text": "Words", "insert_after": "end"}]}}
    r = post(client, church, body)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["fields"] == {"custom_elements.0.label": "Give each custom element a label."}


def test_without_python_docx_it_is_a_logged_500(tmp_db, church, monkeypatch):
    monkeypatch.setattr(worship_service, "Document", None)
    client = make_api_client()
    client = TestClient(client.app, raise_server_exceptions=False)
    r = post(client, church, {"variant": "bulletin", "service": SERVICE})
    assert r.status_code == 500
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("internal_error", "Something went wrong.")
    assert error["request_id"]
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks, usecases.liturgy_review; "
````

**with:**

````python
            "liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks, usecases.liturgy_review, "
            "service_output, worship_service, usecases.archive, usecases.documents; "
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_documents.py backend/tests/test_api_documents.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -4
```

**Expected:** `ERROR backend/tests/test_usecase_documents.py` (`ImportError: cannot import name 'archive' from 'usecases'`), `!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!`, `1 error in <t>s`.

- [ ] **Step 3 (agent): The usecases, the schema, the route**

**Create `backend/usecases/archive.py`:**

````python
"""The service a member builds, as the domain sees it (slice 5a spec, Backend
"usecases/archive.py"). Slice 5a-1 (Word downloads) adds the parts a document
needs; 5a-2 adds saving, listing, opening and deleting services here.

- ServiceInput: the domain copy of api.schemas.ServiceDraft, built by its
  to_input() in the route (usecases never import api/*). 5b's email takes it too.
- clean_input: takes out of every string the characters a Word file cannot
  hold (_xml_safe: python-docx refuses them), then strips every string, drops
  blank scriptures, and drops liturgy that is blank or one of Streamlit's
  stored error texts; a custom element whose label is blank after that is a
  422 on that field.
- resolve_hymn_refs: each slot's hymn, its id resolved within the church in
  one query (the database's title and number win over the client's copy, F
  §1.3); an id the church does not have is a 404 naming the slot; a null id
  keeps the snapshot sent; a blank title is an empty slot (the database's
  title goes through _xml_safe too). The same hymn in two slots is allowed
  (parity).

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

CUSTOM_LABEL_MESSAGE = "Give each custom element a label."

# What XML 1.0 cannot hold, after a vertical tab or form feed becomes a line
# break: the other C0 controls (tab, newline and carriage return are allowed),
# U+FFFE, U+FFFF and lone surrogates. python-docx raises on them (a 500).
_XML_BAD = re.compile("[\x00-\x08\x0e-\x1f\ufffe\uffff\ud800-\udfff]")


def _xml_safe(s: str) -> str:
    """s as a Word file can hold it: a vertical tab (Word's soft line break,
    pasted) or a form feed becomes a line break, the rest of _XML_BAD goes."""
    return _XML_BAD.sub("", s.replace("\x0b", "\n").replace("\x0c", "\n"))


@dataclass(frozen=True)
class ServiceInput:
    service_date: datetime.date
    occasion: str = ""
    scriptures: tuple[str, ...] = ()
    hymns: Mapping[str, Optional[HymnRefData]] = field(default_factory=dict)
    hymnal: Optional[str] = None               # None: the church's effective hymnal (stored by 5a-2)
    liturgy: Mapping[str, str] = field(default_factory=dict)
    sermon_title: str = ""
    selected_ot_ref: str = ""
    selected_nt_ref: str = ""
    include_communion: bool = False
    custom_elements: tuple[CustomElement, ...] = ()


def clean_input(data: ServiceInput) -> ServiceInput:
    """The input with every string made Word-safe and trimmed, and nothing blank kept (see the module docstring)."""
    def clean(text: str) -> str:
        return _xml_safe(text).strip()

    for i, element in enumerate(data.custom_elements):
        if not clean(element.label):
            raise InvalidInput(CUSTOM_LABEL_MESSAGE, field=f"custom_elements.{i}.label")
    liturgy = {key: text for key, raw in data.liturgy.items()
               if (text := clean(raw)) and not is_legacy_error_placeholder(text)}
    hymns = {slot: None if (ref := data.hymns.get(slot)) is None else replace(
        ref, title=clean(ref.title), hymnal=clean(ref.hymnal) if ref.hymnal else ref.hymnal) for slot in SLOTS}
    return replace(
        data,
        occasion=clean(data.occasion),
        scriptures=tuple(text for line in data.scriptures if (text := clean(line))),
        hymns=hymns,
        hymnal=clean(data.hymnal or "") or None,
        liturgy=liturgy,
        sermon_title=clean(data.sermon_title),
        selected_ot_ref=clean(data.selected_ot_ref),
        selected_nt_ref=clean(data.selected_nt_ref),
        custom_elements=tuple(CustomElement(clean(e.label), clean(e.text), e.insert_after)
                              for e in data.custom_elements),
    )


def resolve_hymn_refs(session, church_id: uuid.UUID,
                      hymns: Mapping[str, Optional[HymnRefData]]) -> dict[str, Optional[ResolvedHymn]]:
    """Each slot's hymn as it prints, in one SELECT for the ids (see the module docstring)."""
    ids = [ref.hymn_id for ref in hymns.values() if ref is not None and ref.hymn_id is not None]
    found = hymn_repo.get_hymns_by_ids(church_id, ids, session=session) if ids else {}
    resolved: dict[str, Optional[ResolvedHymn]] = {}
    for slot in SLOTS:
        ref = hymns.get(slot)
        if ref is None:
            resolved[slot] = None
        elif ref.hymn_id is not None:
            record = found.get(ref.hymn_id)
            if record is None:
                raise NotFound(HYMN_GONE_MESSAGE, details={"field": f"hymns.{slot}.hymn_id"})
            title = _xml_safe(record.title or "").strip()
            resolved[slot] = ResolvedHymn(title, record.number, record.id, record.hymnal) if title else None
        else:
            title = ref.title.strip()
            resolved[slot] = ResolvedHymn(title, ref.number, None, ref.hymnal) if title else None
    return resolved
````

**Create `backend/usecases/documents.py`:**

````python
"""The Word files, built on demand from the posted service (slice 5a spec,
Backend "usecases/documents.py"; owner decision 4: never stored, never cached).

build_document(church_id, data, variant) is the only way to build a file
(POST /documents now; 5b's bulletin email later): clean the input, resolve
the hymns in a short read that closes before rendering, render, and name the
file after the posted date. It writes nothing: hymn use is recorded when a
service is saved (5a-2), never on a download. It logs the variant, the church
id, the size and the duration, never the content (F §2.5). clean_input's
InvalidInput and resolve_hymn_refs' NotFound propagate; a missing python-docx
is a RuntimeError, which the API turns into a logged 500.
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

import service_output
from db import session_scope
from usecases import archive

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentResult:
    content: bytes
    filename: str


def build_document(church_id: uuid.UUID, data: archive.ServiceInput,
                   variant: service_output.Variant) -> DocumentResult:
    started = time.monotonic()
    clean = archive.clean_input(data)
    with session_scope() as s:                                  # read, then close before rendering
        hymns = archive.resolve_hymn_refs(s, church_id, clean.hymns)
    resolved = service_output.ResolvedService(
        service_date=clean.service_date, occasion=clean.occasion, scriptures=clean.scriptures, hymns=hymns,
        liturgy=clean.liturgy, sermon_title=clean.sermon_title, selected_ot_ref=clean.selected_ot_ref,
        selected_nt_ref=clean.selected_nt_ref, include_communion=clean.include_communion,
        custom_elements=clean.custom_elements)
    content = service_output.render_docx(resolved, variant)
    logger.info("documents.build church=%s variant=%s bytes=%d ms=%d", church_id, variant, len(content),
                round((time.monotonic() - started) * 1000))
    return DocumentResult(content, service_output.docx_filename(variant, clean.service_date))
````

**In `backend/api/schemas.py`, replace:**

````python
from api.errors import ErrorBody  # noqa: F401  (re-exported: every error response's body, F §1.5)

````

**with:**

````python
import liturgy_config
from api.errors import ErrorBody  # noqa: F401  (re-exported: every error response's body, F §1.5)

````

**Append to `backend/api/schemas.py`:**

````python


# --- slice 5a: the service a member builds (5a spec, "Schemas"; shared with 5b's
# POST /bulletin-emails). 5a-1 uses it for POST /documents; 5a-2 for /services. ---

# The 17 placement keys, liturgy_config.CUSTOM_PLACEMENTS' order (= PLACEMENT_KEYS).
Placement = Literal[tuple(key for key, _label in liturgy_config.CUSTOM_PLACEMENTS)]


class CustomElementIn(BaseModel):
    """A custom element as the builder sends it. A label that is blank after
    trimming is the usecase's 422 ("Give each custom element a label.")."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(max_length=liturgy_config.LIMITS.max_custom_label)
    text: str = Field(default="", max_length=liturgy_config.LIMITS.max_custom_text)
    insert_after: Placement


class ServiceDraft(BaseModel):
    """One service (inventory §2.1 plus hymnal, F §1.3). The limits are slice
    4's (GenerateLiturgyIn, liturgy_config.LIMITS); HymnRef, SlotHymns and
    SectionKey are imported unchanged. Usecases take `to_input()`."""

    model_config = ConfigDict(extra="forbid")

    service_date_iso: IsoDate
    occasion: str = Field(default="", max_length=300)
    scriptures: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=20)
    hymns: SlotHymns = Field(default_factory=SlotHymns)
    # null = the church's effective hymnal (5a-2 stores it); documents ignore it.
    hymnal: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]] = None
    liturgy: dict[SectionKey, Annotated[str, Field(max_length=liturgy_config.LIMITS.max_section_text)]] = Field(
        default_factory=dict)
    sermon_title: str = Field(default="", max_length=liturgy_config.LIMITS.max_sermon_title)
    selected_ot_ref: str = Field(default="", max_length=200)
    selected_nt_ref: str = Field(default="", max_length=200)
    include_communion: bool = False
    custom_elements: list[CustomElementIn] = Field(default_factory=list,
                                                   max_length=liturgy_config.LIMITS.max_custom_elements)

    def to_input(self):
        """The usecases' copy (usecases.archive.ServiceInput); usecases never import api/*."""
        from service_output import CustomElement
        from usecases.archive import ServiceInput
        from usecases.liturgy import HymnRefData

        def hymn(ref: Optional[HymnRef]) -> Optional[HymnRefData]:
            return None if ref is None else HymnRefData(ref.hymn_id, ref.title, ref.number, ref.hymnal)

        return ServiceInput(
            service_date=self.service_date_iso, occasion=self.occasion, scriptures=tuple(self.scriptures),
            hymns={slot: hymn(getattr(self.hymns, slot)) for slot in ("opening", "response", "closing")},
            hymnal=self.hymnal, liturgy=dict(self.liturgy), sermon_title=self.sermon_title,
            selected_ot_ref=self.selected_ot_ref, selected_nt_ref=self.selected_nt_ref,
            include_communion=self.include_communion,
            custom_elements=tuple(CustomElement(e.label, e.text, e.insert_after) for e in self.custom_elements))
````

**Create `backend/api/routes/documents.py`:**

````python
"""POST /documents: the bulletin copy or the pastor's copy of the posted
service as a Word file (slice 5a spec, API; F §1.9).

Church-scoped; any member may download (owner decision 5). A pure render of
the body, so no Idempotency-Key and no rate-limit bucket (F §1.8: local work,
well under 3 s); the client waits up to 30 s. Errors are the usual JSON: 404
with details.field for a hymn id the church does not have, 422 for the body,
a logged 500 when python-docx is missing. Plain `def` (F §1.8), no SQL and no
try/except (F §2.2 rule 1).
"""
from typing import Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

import service_output
from api.deps import ActiveChurch, require_church
from api.errors import error_responses
from api.schemas import ServiceDraft
from usecases import documents

router = APIRouter()


class DocumentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variant: Literal["bulletin", "pastor"]
    service: ServiceDraft


DOCX_RESPONSE = {200: {"description": "The Word file (Content-Disposition names it).",
                       "content": {service_output.DOCX_MIME: {"schema": {"type": "string", "format": "binary"}}}}}


@router.post("/documents", response_class=Response,
             responses={**DOCX_RESPONSE, **error_responses(401, 403, 404, 422, 503)})
def create_document(payload: DocumentIn, church: ActiveChurch = Depends(require_church)) -> Response:
    """Built from the body every time; nothing is stored or cached (owner decision 4)."""
    result = documents.build_document(church.id, payload.service.to_input(), payload.variant)
    return Response(content=result.content, media_type=service_output.DOCX_MIME, headers={
        "Content-Disposition": service_output.content_disposition(result.filename),
        "Cache-Control": "no-store",
    })
````

**In `backend/api/main.py`, replace:**

````python
from api.routes import (churches, health, hymnals, hymns, invites, lectionary, liturgy, liturgy_review, me,
                        reference, rubric, scripture)
````

**with:**

````python
from api.routes import (churches, documents, health, hymnals, hymns, invites, lectionary, liturgy,
                        liturgy_review, me, reference, rubric, scripture)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(liturgy_review.router)
    return app
````

**with:**

````python
    app.include_router(liturgy_review.router)
    app.include_router(documents.router)
    return app
````

- [ ] **Step 4 (agent): Regenerate the OpenAPI snapshot and the types**

```bash
.venv/bin/python backend/scripts/export_openapi.py
(cd frontend && npm run gen:api 2>&1 | tail -1)
git diff --stat -- frontend/src/lib/api | tail -1
grep -c '"/documents"\|"DocumentIn"\|"ServiceDraft"\|"CustomElementIn"' frontend/src/lib/api/openapi.json
```

**Expected:** `Wrote …/frontend/src/lib/api/openapi.json`; a `🚀 src/lib/api/openapi.json → src/lib/api/schema.d.ts` line; `2 files changed, 448 insertions(+)`; `7` (the path, the three schemas and their `$ref`s).

- [ ] **Step 5 (agent): Run the files, the suite, the types**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_documents.py backend/tests/test_api_documents.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_route_guards.py backend/tests/test_openapi_contract.py 2>&1 | tail -1
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/service_output.py backend/usecases/archive.py backend/usecases/documents.py; echo "imports grep exit $?"
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `30 passed in <t>s`; `imports grep exit 1`; `1256 passed, 11 skipped in <t>s`; `typecheck 0`, `lint 0`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/usecases/archive.py backend/usecases/documents.py backend/api/routes/documents.py backend/api/schemas.py backend/api/main.py backend/tests/test_usecase_documents.py backend/tests/test_api_documents.py backend/tests/test_no_streamlit_in_core.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "API: POST /documents builds the bulletin or pastor's copy from the posted service (5a-1; owner answers 1, 3)" -m "Church-scoped, any member; the body is {variant, service: ServiceDraft}
(api/schemas.py, shared with 5a-2 and 5b) and the answer is the Word file
with the F 1.9 Content-Type, Content-Disposition and Cache-Control headers.
usecases.documents.build_document cleans the input, resolves the hymns in
a short read (a hymn id the church lacks is a 404 naming the slot), renders
and names the file; it writes nothing. usecases/archive.py starts with
ServiceInput, clean_input and resolve_hymn_refs. No idempotency key and no
rate-limit bucket: a pure render. OpenAPI snapshot and types regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 3: backend **1256 passed, 11 skipped**; frontend **597 in 78**.

### Task 4: `apiFetchBlob` (S "Library code"; F §1.8, §1.9, §4.5; clarification 10)

**Files:**
- Modify: `frontend/src/lib/api/client.ts`, `frontend/src/lib/api/client.test.ts`, `frontend/src/lib/api/timeouts.ts`

- [ ] **Step 1 (agent): Write the failing tests**

**In `frontend/src/lib/api/client.test.ts`, replace:**

````ts
import { apiFetch } from "./client";
````

**with:**

````ts
import { apiFetch, apiFetchBlob, parseContentDispositionFilename } from "./client";
import { timeoutFor } from "./timeouts";
````

**Append to `frontend/src/lib/api/client.test.ts`:**

````ts

describe("apiFetchBlob (slice 5a; F §1.9, §4.5)", () => {
  const NAME = "worship_October_04_2026.docx";
  const DISPOSITION = `attachment; filename="${NAME}"; filename*=UTF-8''${NAME}`;

  function fileFetch(headers: Record<string, string> = { "Content-Disposition": DISPOSITION }) {
    return vi.fn<typeof fetch>(async () => new Response(new Uint8Array([0x50, 0x4b, 3, 4]), { status: 200, headers }));
  }

  it("returns the bytes and the server's filename, sending the token, church and JSON body", async () => {
    const f = fileFetch();
    const out = await apiFetchBlob("/documents", {
      token: "t0k",
      churchId: "c-1",
      method: "POST",
      json: { variant: "bulletin" },
      baseUrl: "https://api.test",
      fetchImpl: f,
    });
    expect(out.filename).toBe(NAME);
    expect(new Uint8Array(await out.blob.arrayBuffer())).toEqual(new Uint8Array([0x50, 0x4b, 3, 4]));
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("https://api.test/documents");
    const headers = new Headers(init?.headers);
    expect([headers.get("Authorization"), headers.get("X-Church-Id"), headers.get("Content-Type")]).toEqual([
      "Bearer t0k",
      "c-1",
      "application/json",
    ]);
    expect(init?.body).toBe(JSON.stringify({ variant: "bulletin" }));
    // No header: the caller names the file (docxFilename).
    await expect(apiFetchBlob("/documents", { token: "t", baseUrl: "", fetchImpl: fileFetch({}) })).resolves.toMatchObject({
      filename: null,
    });
  });

  it("turns a JSON error body into an ApiError, and keeps the client codes", async () => {
    const body = {
      error: {
        code: "not_found",
        message: "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
        request_id: "req-404",
        details: { field: "hymns.response.hymn_id" },
      },
    };
    await expect(apiFetchBlob("/documents", { token: "t", baseUrl: "", fetchImpl: jsonFetch(404, body) })).rejects.toMatchObject({
      status: 404,
      code: "not_found",
      message: body.error.message,
      requestId: "req-404",
      details: { field: "hymns.response.hymn_id" },
    });
    const down = vi.fn<typeof fetch>(async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(apiFetchBlob("/documents", { token: "t", baseUrl: "", fetchImpl: down })).rejects.toMatchObject({
      status: 0,
      code: "network_error",
    });
    const controller = new AbortController();
    const pending = apiFetchBlob("/documents", { token: "t", baseUrl: "", fetchImpl: hangingFetch(), signal: controller.signal });
    controller.abort();
    await expect(pending).rejects.toMatchObject({ code: "aborted" });
  });

  it("times out after 30 s on POST /documents", async () => {
    expect(timeoutFor("POST", "/documents")).toBe(30_000);
    vi.useFakeTimers();
    const pending = apiFetchBlob("/documents", { token: "t", baseUrl: "", method: "POST", fetchImpl: hangingFetch() });
    const caught = pending.catch((e: unknown) => e);
    await vi.advanceTimersByTimeAsync(29_999);
    let settled = false;
    void caught.then(() => (settled = true));
    await Promise.resolve();
    expect(settled).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await expect(caught).resolves.toMatchObject({ code: "timeout", message: "This is taking too long. Try again." });
  });

  it("reads filename* first, then a quoted or plain filename", () => {
    expect(parseContentDispositionFilename(`attachment; filename="a.docx"; filename*=UTF-8''b%20c.docx`)).toBe("b c.docx");
    expect(parseContentDispositionFilename(`attachment; filename="worship_pastor_May_09_2027.docx"`)).toBe(
      "worship_pastor_May_09_2027.docx",
    );
    expect(parseContentDispositionFilename("attachment; filename=plain.docx")).toBe("plain.docx");
    expect(parseContentDispositionFilename(`attachment; filename*=UTF-8''%E0%A4%A; filename="safe.docx"`)).toBe("safe.docx");
    expect(parseContentDispositionFilename("attachment")).toBeNull();
    expect(parseContentDispositionFilename(null)).toBeNull();
  });
});
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/api/client.test.ts 2>&1 | grep -E "^ +× |Tests ")
```

**Expected:** four failures (`apiFetchBlob` and `parseContentDispositionFilename` are not exported yet):
```
   × apiFetchBlob (slice 5a; F §1.9, §4.5) > returns the bytes and the server's filename, sending the token, church and JSON body <t>ms
   × apiFetchBlob (slice 5a; F §1.9, §4.5) > turns a JSON error body into an ApiError, and keeps the client codes <t>ms
   × apiFetchBlob (slice 5a; F §1.9, §4.5) > times out after 30 s on POST /documents <t>ms
   × apiFetchBlob (slice 5a; F §1.9, §4.5) > reads filename* first, then a quoted or plain filename <t>ms
      Tests  4 failed | 18 passed (22)
```

- [ ] **Step 3 (agent): One `send()` for both calls, the blob call, the filename, 30 s**

**In `frontend/src/lib/api/client.ts`, replace:**

````ts
/** Call the FastAPI backend. The server re-checks the church on every request. */
export async function apiFetch<T>(path: string, opts: ApiOptions): Promise<T> {
````

**with:**

````ts
/**
 * Sends one request with the shared headers, timeout and abort (F §4.5) and
 * reads the body with `read` before the timer stops, so a stalled body also
 * times out. A failure to send or read is `timeout`, `aborted` or
 * `network_error` (status 0).
 */
async function send<B>(path: string, opts: ApiOptions, read: (res: Response) => Promise<B>): Promise<{ res: Response; body: B }> {
````

**In `frontend/src/lib/api/client.ts`, replace:**

````ts
  let res: Response;
  let text: string;
  try {
    res = await fetchImpl(`${normalizedBaseUrl}${path}`, {
      ...init,
      method,
      headers,
      body,
      signal: controller.signal,
    });
    // Read the body before the timer stops: a stalled body also times out.
    text = res.status === 204 ? "" : await res.text();
  } catch {
    if (timedOut) throw new ApiError(0, "timeout", TIMEOUT_MESSAGE);
    if (controller.signal.aborted) throw new ApiError(0, "aborted", ABORTED_MESSAGE);
    throw new ApiError(0, "network_error", NETWORK_MESSAGE);
  } finally {
    clearTimeout(timer);
    callerSignal?.removeEventListener("abort", onCallerAbort);
  }

  if (res.ok) {
    if (!text) return undefined as T;
    try {
      return JSON.parse(text) as T;
    } catch {
      // A proxy or captive portal answering 200 with HTML: still an ApiError.
      throw new ApiError(res.status, "internal_error", GENERIC_MESSAGE, {
        requestId: res.headers.get("X-Request-Id") ?? undefined,
      });
    }
  }
  throw errorFromResponse(res, text);
}
````

**with:**

````ts
  try {
    const res = await fetchImpl(`${normalizedBaseUrl}${path}`, {
      ...init,
      method,
      headers,
      body,
      signal: controller.signal,
    });
    return { res, body: await read(res) };
  } catch {
    if (timedOut) throw new ApiError(0, "timeout", TIMEOUT_MESSAGE);
    if (controller.signal.aborted) throw new ApiError(0, "aborted", ABORTED_MESSAGE);
    throw new ApiError(0, "network_error", NETWORK_MESSAGE);
  } finally {
    clearTimeout(timer);
    callerSignal?.removeEventListener("abort", onCallerAbort);
  }
}

/** Call the FastAPI backend. The server re-checks the church on every request. */
export async function apiFetch<T>(path: string, opts: ApiOptions): Promise<T> {
  const { res, body: text } = await send(path, opts, (r) => (r.status === 204 ? Promise.resolve("") : r.text()));
  if (res.ok) {
    if (!text) return undefined as T;
    try {
      return JSON.parse(text) as T;
    } catch {
      // A proxy or captive portal answering 200 with HTML: still an ApiError.
      throw new ApiError(res.status, "internal_error", GENERIC_MESSAGE, {
        requestId: res.headers.get("X-Request-Id") ?? undefined,
      });
    }
  }
  throw errorFromResponse(res, text);
}

/** A file from the API (`POST /documents`, slice 5a) and the name its `Content-Disposition` gives, if any. */
export type BlobResult = { blob: Blob; filename: string | null };

/**
 * `apiFetch` for a route that answers with a file (F §1.9, §4.5): the same
 * headers, timeout, abort and error mapping; a 2xx returns the bytes and the
 * server's filename; an error body is read as JSON into an `ApiError`.
 */
export async function apiFetchBlob(path: string, opts: ApiOptions): Promise<BlobResult> {
  const { res, body } = await send<Blob | string>(path, opts, (r) => (r.ok ? r.blob() : r.text()));
  if (!res.ok) throw errorFromResponse(res, typeof body === "string" ? body : "");
  return { blob: body as Blob, filename: parseContentDispositionFilename(res.headers.get("Content-Disposition")) };
}

/**
 * The filename in a `Content-Disposition` header: `filename*=UTF-8''…` decoded
 * first, else `filename="…"` (or unquoted), else null.
 */
export function parseContentDispositionFilename(header: string | null): string | null {
  if (!header) return null;
  const encoded = /filename\*\s*=\s*UTF-8''([^;\s]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1]);
    } catch {
      // A malformed escape: fall back to the plain name.
    }
  }
  const plain = /filename\s*=\s*(?:"([^"]*)"|([^;\s]+))/i.exec(header);
  const name = (plain?.[1] ?? plain?.[2] ?? "").trim();
  return name === "" ? null : name;
}
````

**In `frontend/src/lib/api/timeouts.ts`, replace:**

````ts
  "POST /liturgy/review": 100_000,
  "POST /liturgy/revise": 100_000,
};
````

**with:**

````ts
  "POST /liturgy/review": 100_000,
  "POST /liturgy/revise": 100_000,
  // Slice 5a (F §1.8): a Word file is local work on the server, well under 3 s; 30 s covers a slow phone network.
  "POST /documents": 30_000,
};
````

- [ ] **Step 4 (agent): Run the file, the suite, the types and lint**

```bash
(cd frontend && npx vitest run src/lib/api 2>&1 | grep -E "^ +× |Tests ")
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `Tests  30 passed (30)` (`client.test.ts` 22, `errors.test.ts` 8); ` Test Files  78 passed (78)` and `      Tests  601 passed (601)` with no `×` or `FAIL` line; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/lib/api/client.ts frontend/src/lib/api/client.test.ts frontend/src/lib/api/timeouts.ts
git commit -q -m "Client: apiFetchBlob returns a file and its server filename (5a-1; F 1.9, 4.5)" -m "apiFetch and the new apiFetchBlob share one send(): the same headers,
timeout, abort and error mapping. A 2xx file comes back as {blob,
filename}, the filename read from Content-Disposition (filename* first);
an error body is the usual ApiError. POST /documents waits up to 30 s." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 4: backend **1256 passed, 11 skipped**; frontend **601 in 78**.

### Task 5: The body, the filename and the download (S `download.ts`, `useDownloadDocument`; F §1.9, §4.6; clarifications 9, 10)

**Files:**
- Create: `frontend/src/lib/download.ts`, `frontend/src/lib/download.test.ts`, `frontend/src/lib/documents.ts`, `frontend/src/lib/documents.test.ts`, `frontend/src/lib/queries/documents.ts`
- Modify: `frontend/src/lib/liturgy/request.ts`, `frontend/src/lib/queries/client.ts`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `frontend/src/lib/download.test.ts`:**

````ts
import { readFileSync } from "node:fs";

import { afterEach, describe, expect, it, vi } from "vitest";

import { docxFilename, downloadBlob, REVOKE_AFTER_MS, type DocumentVariant } from "./download";

type Case = { date: string; variant: DocumentVariant; display: string; filename: string };
const { cases } = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/docx_filenames.json", import.meta.url), "utf-8"),
) as { cases: Case[] };

describe("docxFilename (slice 5a; F §1.9)", () => {
  it("names each file as the server does (shared/docx_filenames.json)", () => {
    expect(cases).toHaveLength(8);
    for (const c of cases) expect(docxFilename(c.variant, c.date), c.date).toBe(c.filename);
  });
});

describe("downloadBlob (slice 5a; F §1.9)", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("clicks a hidden download link and keeps the file's URL 5 minutes, so an iPhone's Download? sheet can wait", () => {
    vi.useFakeTimers();
    const link = { click: vi.fn(), remove: vi.fn() } as unknown as HTMLAnchorElement;
    const appendChild = vi.fn();
    vi.stubGlobal("document", { createElement: vi.fn(() => link), body: { appendChild } });
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:test/1");
    const revoke = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

    downloadBlob(new Blob(["PK"]), "worship_October_04_2026.docx");
    expect(link).toMatchObject({ href: "blob:test/1", download: "worship_October_04_2026.docx", hidden: true });
    expect(appendChild).toHaveBeenCalledWith(link);
    expect(link.click).toHaveBeenCalledOnce();
    expect(link.remove).toHaveBeenCalledOnce();
    expect(REVOKE_AFTER_MS).toBe(5 * 60_000);
    vi.advanceTimersByTime(REVOKE_AFTER_MS - 1);
    expect(revoke).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(revoke).toHaveBeenCalledWith("blob:test/1");
  });
});
````

**Create `frontend/src/lib/documents.test.ts`:**

````ts
/**
 * The `POST /documents` body (slice 5a spec, `useDownloadDocument`; Testing
 * `mapping.test.ts`'s payload rules as the documents use them).
 */
import { describe, expect, it } from "vitest";

import { editScriptureLines, setPick } from "@/lib/draft/readings";
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { addCustomElement, editCardText, setCardEnabled, setCommunion, setSermonTitle } from "@/lib/liturgy/cards";
import { gg2013, testDraft } from "@/test/fixtures";

import { documentRequest } from "./documents";

const OCT_4 = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];

describe("documentRequest (slice 5a)", () => {
  it("sends the service as the Word file prints it: slot hymns, enabled cards with text, picks, communion, custom elements", () => {
    const [holy] = gg2013();
    let d = editScriptureLines(testDraft(), ["  Isaiah 5:1-7 ", "", ...OCT_4.slice(1)].join("\n"));
    d = { ...d, readings: { ...d.readings, occasion: "  World Communion Sunday " } };
    d = setPick(d, "nt", "Matthew 21:33-46");
    d = setSlot(d, "response", pickFromHymn(holy));
    d = editCardText(d, "call_to_worship", "Leader: Come. People: We come.");
    d = editCardText(setCardEnabled(d, "opening_prayer", false), "opening_prayer", "Switched off, so not sent.");
    d = editCardText(d, "prayer_of_confession", "   ");
    d = setSermonTitle(setCommunion(d, true), "  Living Water ");
    d = addCustomElement(d, { label: " Anthem ", text: "Choir", insert_after: "sermon" }, "a");
    d = addCustomElement(d, { label: "  ", text: "No label, never printed.", insert_after: "end" }, "b");
    d = addCustomElement(d, { label: "Old place", text: "", insert_after: "bogus" }, "c");

    expect(documentRequest(d, "pastor")).toEqual({
      variant: "pastor",
      service: {
        service_date_iso: "2026-10-04",
        occasion: "World Communion Sunday",
        scriptures: OCT_4,
        hymns: {
          opening: null,
          response: { hymn_id: holy.id, title: holy.title, number: holy.number, hymnal: holy.hymnal },
          closing: null,
        },
        hymnal: null,
        liturgy: { call_to_worship: "Leader: Come. People: We come.", benediction: "Halverson" },
        sermon_title: "Living Water",
        selected_ot_ref: "",
        selected_nt_ref: "Matthew 21:33-46",
        include_communion: true,
        custom_elements: [
          { label: "Anthem", text: "Choir", insert_after: "sermon" },
          { label: "Old place", text: "", insert_after: "end" },
        ],
      },
    });
    expect(documentRequest(d, "bulletin").variant).toBe("bulletin");
  });

  it("stays within the ServiceDraft limits, so a draft never meets a 422", () => {
    let d = editScriptureLines(testDraft(), Array.from({ length: 22 }, (_, i) => `Psalm ${i + 1}`).join("\n"));
    d = { ...d, readings: { ...d.readings, occasion: "o".repeat(320), selected_nt_ref: "Mark 1" } };
    d = setSlot(d, "opening", { hymn_id: "not-a-uuid", title: "t".repeat(310), number: 100_001, hymnal: "h".repeat(25) });
    d = { ...d, hymns: { ...d.hymns, hymnal: "x".repeat(30) } };
    d = editCardText(d, "call_to_worship", "c".repeat(20_005));
    d = setSermonTitle(d, "s".repeat(305));
    for (let i = 0; i < 32; i += 1) d = addCustomElement(d, { label: "L".repeat(205), text: "T".repeat(10_005), insert_after: "end" }, `e${i}`);

    const { service } = documentRequest(d, "bulletin");
    expect(service.occasion).toHaveLength(300);
    expect(service.scriptures).toHaveLength(20);
    expect(service.selected_nt_ref).toBe(""); // not one of the lines
    expect(service.hymns?.opening).toEqual({ hymn_id: null, title: "t".repeat(300), number: null, hymnal: "h".repeat(20) });
    expect(service.hymnal).toHaveLength(20);
    expect(service.liturgy?.call_to_worship).toHaveLength(20_000);
    expect(service.sermon_title).toHaveLength(300);
    expect(service.custom_elements).toHaveLength(30);
    expect(service.custom_elements?.[0]).toEqual({ label: "L".repeat(200), text: "T".repeat(10_000), insert_after: "end" });

    // A picked reading over 200 characters goes cut, as its line does, so the pick still names that line.
    const long = `Matthew 21:33-46 ${"x".repeat(190)}`;
    const picked = documentRequest(setPick(editScriptureLines(testDraft(), `Isaiah 5:1-7\n${long}`), "nt", long), "bulletin").service;
    expect(picked.scriptures).toEqual(["Isaiah 5:1-7", long.slice(0, 200)]);
    expect(picked.selected_nt_ref).toBe(long.slice(0, 200));
  });
});
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/download.test.ts src/lib/documents.test.ts 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests |Error:")
```

**Expected:** both files fail to load:
```
 FAIL  |unit| src/lib/documents.test.ts [ src/lib/documents.test.ts ]
Error: Cannot find module './documents' imported from '…/frontend/src/lib/documents.test.ts'
Caused by: Error: Failed to load url ./documents (resolved id: ./documents) in …/frontend/src/lib/documents.test.ts. Does the file exist?
 FAIL  |unit| src/lib/download.test.ts [ src/lib/download.test.ts ]
Error: Cannot find module './download' imported from '…/frontend/src/lib/download.test.ts'
Caused by: Error: Failed to load url ./download (resolved id: ./download) in …/frontend/src/lib/download.test.ts. Does the file exist?
 Test Files  2 failed (2)
      Tests  no tests
```

- [ ] **Step 3 (agent): `docxFilename`, `downloadBlob`, `documentRequest`, `useApi().churchBlob`, `useDownloadDocument`**

**Create `frontend/src/lib/download.ts`:**

````ts
/**
 * Word files on this device (slice 5a spec, Library "download.ts"; F §1.9).
 *
 * - `docxFilename(variant, dateIso)`: the name the server gives
 *   (`service_output.docx_filename`), for a response without
 *   `Content-Disposition`; shared/docx_filenames.json keeps the two equal.
 * - `downloadBlob(blob, filename)`: an object URL clicked through a hidden
 *   `<a download>`; the URL is revoked after 5 minutes, since revoking at once
 *   breaks Safari and an iPhone's "Download?" sheet can wait for the member's
 *   answer. On iPhone this opens the share or preview sheet (accepted, owner
 *   answer 7, 2026-10-01).
 */
export type DocumentVariant = "bulletin" | "pastor";

const MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export const REVOKE_AFTER_MS = 5 * 60_000;

/** "2026-10-04" → "worship_October_04_2026.docx" (pastor: "worship_pastor_October_04_2026.docx"). */
export function docxFilename(variant: DocumentVariant, dateIso: string): string {
  const [year, month, day] = dateIso.split("-");
  const prefix = variant === "pastor" ? "worship_pastor_" : "worship_";
  return `${prefix}${MONTHS[Number(month) - 1]}_${day}_${year}.docx`;
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  link.hidden = true;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), REVOKE_AFTER_MS);
}
````

**In `frontend/src/lib/liturgy/request.ts`, replace:**

````ts
 * The service reviewer's bodies (`buildReviewRequest`, `buildReviseRequest`)
 * carry the same occasion, readings and resolved sermon text.
 */
````

**with:**

````ts
 * The service reviewer's bodies (`buildReviewRequest`, `buildReviseRequest`)
 * carry the same occasion, readings and resolved sermon text, and the Word
 * files' body (`lib/documents.ts`, slice 5a) the same occasion, readings and
 * hymns (`readingsContext`, `hymnRef`).
 */
````

**In `frontend/src/lib/liturgy/request.ts`, replace:**

````ts
function hymnRef(pick: HymnPick | null): HymnRef | null {
````

**with:**

````ts
export function hymnRef(pick: HymnPick | null): HymnRef | null {
````

**In `frontend/src/lib/liturgy/request.ts`, replace:**

````ts
function readingsContext(draft: DraftV1): { occasion: string; scriptures: string[] } {
````

**with:**

````ts
export function readingsContext(draft: DraftV1): { occasion: string; scriptures: string[] } {
````

**Create `frontend/src/lib/documents.ts`:**

````ts
/**
 * The `POST /documents` body (slice 5a spec, `useDownloadDocument`; F §4.6
 * "Draft → API payload"). Pure.
 *
 * The service is `draftToServicePayload(draft)` (the provisional mapping the
 * save will share, 5a-3), kept within the `ServiceDraft` limits so a draft
 * never meets a 422: the occasion and readings as every liturgy request sends
 * them (trimmed; the first 20 readings, each cut to 200; `request.ts`), the
 * two bulletin picks trimmed and cut to 200 as well, the hymns as `HymnRef`s (an id that is not a UUID goes as null, so the pick's own
 * title prints), each text cut to its limit (`liturgy_config.LIMITS`), custom
 * elements without a label left out (the Word file never printed them) and
 * each place read as `normalizePlacement` does on the Liturgy step.
 */
import type { components } from "@/lib/api/schema";
import { draftToServicePayload } from "@/lib/draft/mapping";
import type { DraftV1 } from "@/lib/draft/schema";
import type { DocumentVariant } from "@/lib/download";
import { clipChars, MAX_REF_LENGTH } from "@/lib/hymns/match-request";
import { normalizePlacement } from "@/lib/liturgy/cards";
import { hymnRef, MAX_CARD_TEXT, MAX_HYMNAL, readingsContext } from "@/lib/liturgy/request";

export type DocumentBody = components["schemas"]["DocumentIn"];
type Placement = components["schemas"]["CustomElementIn"]["insert_after"];

/** liturgy_config.LIMITS (slice 4a), the server's ServiceDraft limits. */
export const MAX_SERMON_TITLE = 300;
export const MAX_CUSTOM_ELEMENTS = 30;
export const MAX_CUSTOM_LABEL = 200;
export const MAX_CUSTOM_TEXT = 10_000;

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
        .filter((element) => element.label.trim() !== "")
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

**In `frontend/src/lib/queries/client.ts`, replace:**

````ts
import { ApiError, apiFetch, type ApiOptions } from "@/lib/api/client";
````

**with:**

````ts
import { ApiError, apiFetch, apiFetchBlob, type ApiOptions, type BlobResult } from "@/lib/api/client";
````

**In `frontend/src/lib/queries/client.ts`, replace:**

````ts
export type ApiCall = <T>(path: string, opts?: Omit<ApiOptions, "token" | "churchId">) => Promise<T>;

````

**with:**

````ts
export type ApiCall = <T>(path: string, opts?: Omit<ApiOptions, "token" | "churchId">) => Promise<T>;

/** `apiFetchBlob` with the token and `X-Church-Id` filled in: a church-scoped route that answers with a file. */
export type BlobCall = (path: string, opts?: Omit<ApiOptions, "token" | "churchId">) => Promise<BlobResult>;

````

**In `frontend/src/lib/queries/client.ts`, replace:**

````ts
  /** A church-scoped call for a church that is not (yet) provided: the `(church)` layout's `GET /church`. */
  forChurch(churchId: string): ApiCall;
};
````

**with:**

````ts
  /** A church-scoped call for a church that is not (yet) provided: the `(church)` layout's `GET /church`. */
  forChurch(churchId: string): ApiCall;
  /** A church-scoped file (`POST /documents`, slice 5a). Throws when called outside a `ChurchProvider`. */
  churchBlob: BlobCall;
};
````

**In `frontend/src/lib/queries/client.ts`, replace:**

````ts
const churchOutsideProvider: ApiCall = () => {
  throw new Error("useApi().church needs a ChurchProvider; use useApi().user or forChurch(id).");
};
````

**with:**

````ts
const churchOutsideProvider: ApiCall = () => {
  throw new Error("useApi().church needs a ChurchProvider; use useApi().user or forChurch(id).");
};

function boundBlobCall(churchId: string): BlobCall {
  return async (path, opts = {}) => apiFetchBlob(path, { ...opts, token: await getAccessToken(), churchId });
}

const blobOutsideProvider: BlobCall = () => {
  throw new Error("useApi().churchBlob needs a ChurchProvider.");
};
````

**In `frontend/src/lib/queries/client.ts`, replace:**

````ts
      forChurch: (id: string) => boundCall(id),
    }),
````

**with:**

````ts
      forChurch: (id: string) => boundCall(id),
      churchBlob: churchId ? boundBlobCall(churchId) : blobOutsideProvider,
    }),
````

**Create `frontend/src/lib/queries/documents.ts`:**

````ts
/**
 * The Word files (slice 5a spec, `useDownloadDocument`; F §1.9; owner decision 4).
 *
 * `useDownloadDocument(variant)`: one mutation per button, so each has its own
 * pending state. On click it reads the latest draft (`peek`), builds the body
 * (`documentRequest`), posts it with `useApi().churchBlob` (30 s client
 * timeout, `lib/api/timeouts.ts`) and hands the file to `downloadBlob` under
 * the server's name, or `docxFilename` when the header is missing. Nothing is
 * cached or kept: each tap builds the file from the draft as it is then. A
 * 401 or a lost church goes through the cache's `handleAuthErrors`
 * (`useChurchMutation`); the caller shows any other error.
 */
import type { ApiError } from "@/lib/api/client";
import { documentRequest } from "@/lib/documents";
import { useDraft } from "@/lib/draft/context";
import { docxFilename, downloadBlob, type DocumentVariant } from "@/lib/download";

import { useApi, useChurchMutation } from "./client";

/** The mutation's result: the name the file was saved under. */
export function useDownloadDocument(variant: DocumentVariant) {
  const api = useApi();
  const { peek } = useDraft();
  return useChurchMutation<string, ApiError, void>({
    mutationFn: async () => {
      const body = documentRequest(peek(), variant);
      const { blob, filename } = await api.churchBlob("/documents", { method: "POST", json: body });
      const name = filename ?? docxFilename(variant, body.service.service_date_iso);
      downloadBlob(blob, name);
      return name;
    },
  });
}
````

- [ ] **Step 4 (agent): Run the files, the suite, the types and lint**

```bash
(cd frontend && npx vitest run src/lib/download.test.ts src/lib/documents.test.ts 2>&1 | grep -E "^ +× |Tests ")
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `Tests  4 passed (4)`; ` Test Files  80 passed (80)` and `      Tests  605 passed (605)` with no `×` or `FAIL` line; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/lib/download.ts frontend/src/lib/download.test.ts frontend/src/lib/documents.ts frontend/src/lib/documents.test.ts frontend/src/lib/queries/documents.ts frontend/src/lib/queries/client.ts frontend/src/lib/liturgy/request.ts
git commit -q -m "Client: the documents body, the file's name and the download (5a-1; F 1.9, 4.6)" -m "documentRequest builds POST /documents' body from the draft within the
ServiceDraft limits (the occasion and readings as every liturgy request
sends them, HymnRefs, texts cut to their limits, unlabelled custom elements
left out, places normalized, the bulletin picks cut to 200). docxFilename names a file as the server does
(shared fixture); downloadBlob saves it through an object URL kept 5
minutes.
useDownloadDocument is one mutation per button, reading the draft at the
tap; useApi() gains churchBlob." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 5: backend **1256 passed, 11 skipped**; frontend **605 in 80**.

### Task 6: The Review & send step: Still needed, the Word documents, the archive note (owner answers 1, 2, 3, 7; S UX "Review step" items 2 and 4, "Mobile specifics"; F §4.7, §4.8, §4.9; clarifications 1-5, 11, 15, 16)

**Files:**
- Create: `frontend/src/components/builder/review/documents-card.tsx`, `frontend/src/components/builder/review/review-send-step.tsx`, `frontend/src/components/builder/review/review-send-step.test.tsx`
- Modify: `frontend/src/app/(signed-in)/(church)/builder/review/page.tsx`, `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/lib/draft/steps.ts`, `frontend/src/test/fake-api.ts`
- Delete: `frontend/src/components/builder/step-placeholder.tsx`

- [ ] **Step 1 (agent): Write the failing tests; the fake API passes a real `Response` through**

**Create `frontend/src/components/builder/review/review-send-step.test.tsx`:**

````tsx
/**
 * Review & send in slice 5a-1 (slice 5a spec, UX "Word documents card",
 * Testing `review-step.test.tsx` "Downloads" and "Invalid date"; owner answers
 * 2 and 3, 2026-10-01). The step renders inside the builder layout with a
 * Toaster; `URL.createObjectURL` and the link's click are stubbed, so a
 * download is recorded instead of navigating. The clock is fixed at Tuesday,
 * September 29, 2026, so a fresh draft is dated Sunday, October 4, 2026.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
import { Toaster } from "@/components/ui/sonner";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { editCardText, setCardEnabled } from "@/lib/liturgy/cards";
import { REVOKE_AFTER_MS } from "@/lib/download";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  gg2013,
  hymnals,
  hymnListRoute,
  lectionaryRoute,
  liturgyConfig,
  me,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { NEEDS_DATE, SAME_AS_BULLETIN } from "./documents-card";

const KEY = draftKey(USER_ID, church().id);
const NAME = "worship_October_04_2026.docx";
const HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.";

/** A Word file response, with the server's Content-Disposition unless `headers` says otherwise. */
function docx(headers: Record<string, string> = { "Content-Disposition": `attachment; filename="${NAME}"; filename*=UTF-8''${NAME}` }) {
  return new Response(new Uint8Array([0x50, 0x4b, 3, 4]), {
    status: 200,
    headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", ...headers },
  });
}

let clicks: { download: string; href: string }[];
let revoked: string[];

function renderReview(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /translations": translations(),
    "GET /hymnals": hymnals(),
    "GET /hymns": hymnListRoute(),
    "GET /liturgy/config": liturgyConfig(),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <ReviewStepPage />
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/builder/review" },
  );
  return { ...view, api };
}

async function documentsCard() {
  return screen.findByRole("region", { name: "Word documents" });
}

function documentRequests(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "POST" && r.path === "/documents");
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  clicks = [];
  revoked = [];
  let n = 0;
  Object.assign(URL, {
    createObjectURL: vi.fn(() => `blob:test/${(n += 1)}`),
    revokeObjectURL: vi.fn((url: string) => revoked.push(url)),
  });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
    clicks.push({ download: this.download, href: this.getAttribute("href") ?? "" });
  });
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Review & send: the Word documents (slice 5a-1)", () => {
  it("shows Still needed, both copies with what they hold, and the archive note, with no placeholder", async () => {
    renderReview();
    const card = await documentsCard();
    expect(within(card).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Bulletin copy", "Pastor's copy"]);
    const bulletin = within(card).getByRole("button", { name: "Download bulletin copy" });
    const pastor = within(card).getByRole("button", { name: "Download pastor's copy" });
    expect(bulletin).toHaveAccessibleDescription(
      "The order of worship with hymns, readings and the sermon title. Leaves out Prayers of the People.",
    );
    // Prayers of the People is off on a fresh draft, so the two copies are the same.
    expect(pastor).toHaveAccessibleDescription(`Everything in the bulletin copy, plus Prayers of the People. ${SAME_AS_BULLETIN}`);
    for (const button of [bulletin, pastor]) {
      expect(button).toBeEnabled();
      expect(button).toHaveClass("h-11"); // 44 px on a phone
    }
    expect(within(card).queryByText(NEEDS_DATE)).toBeNull();
    expect(screen.getByRole("region", { name: "Still needed" })).toBeInTheDocument();
    const archive = screen.getByRole("region", { name: "Archive" });
    expect(archive).toHaveTextContent("Saving services to the archive is coming soon.");
    expect(screen.queryByText("Available soon")).toBeNull();
  });

  it("downloads the bulletin copy built from the draft, under the server's name", async () => {
    const [holy] = gg2013();
    let d = setSlot(testDraft(), "opening", pickFromHymn(holy));
    d = editCardText(d, "call_to_worship", "Leader: Come. People: We come.");
    const { api, user } = renderReview(d, { "POST /documents": () => docx() });
    const card = await documentsCard();
    await user.click(within(card).getByRole("button", { name: "Download bulletin copy" }));

    await waitFor(() => expect(clicks).toEqual([{ download: NAME, href: "blob:test/1" }]));
    const [request] = documentRequests(api);
    expect(request.headers["x-church-id"]).toBe(church().id);
    expect(request.body).toMatchObject({
      variant: "bulletin",
      service: {
        service_date_iso: "2026-10-04",
        hymns: { opening: { hymn_id: holy.id, title: holy.title, number: holy.number }, response: null, closing: null },
        liturgy: { call_to_worship: "Leader: Come. People: We come.", benediction: "Halverson" },
      },
    });
    expect(revoked).toEqual([]); // kept 5 minutes: revoking at once breaks Safari
    expect(REVOKE_AFTER_MS).toBe(300_000);
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled();
  });

  it("names the pastor's copy itself when the header is missing; each button has its own Preparing…, then Still working… after 8 s", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    let release!: () => void;
    const held = new Promise<void>((resolve) => (release = resolve));
    const { api, user } = renderReview(editCardText(setCardEnabled(testDraft(), "prayers_of_the_people", true), "prayers_of_the_people", "We pray."), {
      "POST /documents": async () => {
        await held;
        return docx({});
      },
    });
    const card = await documentsCard();
    const pastor = within(card).getByRole("button", { name: "Download pastor's copy" });
    expect(pastor).toHaveAccessibleDescription("Everything in the bulletin copy, plus Prayers of the People.");
    await user.click(pastor);
    expect(await within(card).findByRole("button", { name: "Preparing…" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled();
    expect(within(card).getAllByRole("status").map((s) => s.textContent)).toEqual(["", "Pastor's copy: Preparing…"]);
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(within(card).getByRole("button", { name: "Still working…" })).toBeDisabled();
    expect(within(card).getAllByRole("status")[1]).toHaveTextContent("Pastor's copy: Still working…");
    release();
    await waitFor(() => expect(clicks).toEqual([{ download: "worship_pastor_October_04_2026.docx", href: "blob:test/1" }]));
    expect((documentRequests(api)[0].body as { variant: string }).variant).toBe("pastor");
    expect(await within(card).findByRole("button", { name: "Download pastor's copy" })).toBeEnabled();
  });

  it("shows the server's message when a download fails, and saves no file", async () => {
    const [holy] = gg2013();
    const { user } = renderReview(setSlot(testDraft(), "response", pickFromHymn(holy)), {
      "POST /documents": fakeError(404, "not_found", HYMN_GONE, { details: { field: "hymns.response.hymn_id" } }),
    });
    const card = await documentsCard();
    await user.click(within(card).getByRole("button", { name: "Download bulletin copy" }));
    expect(await screen.findByText(HYMN_GONE)).toBeInTheDocument();
    expect(clicks).toEqual([]);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled();
  });

  it("adds no message of its own after a 401 or a lost church, and saves no file", async () => {
    const errorToast = vi.spyOn(toast, "error");
    const responses = [
      fakeError(401, "unauthorized", "Sign in again."),
      fakeError(403, "forbidden", "You no longer have access to this church.", { details: { reason: "no_church_access" } }),
    ];
    for (const response of responses) {
      const { api, user, unmount } = renderReview(testDraft(), { "POST /documents": response });
      const card = await documentsCard();
      await user.click(within(card).getByRole("button", { name: "Download bulletin copy" }));
      await waitFor(() => expect(documentRequests(api)).toHaveLength(1));
      await waitFor(() => expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled());
      unmount();
    }
    expect(errorToast).not.toHaveBeenCalled();
    expect(clicks).toEqual([]);
    expect(URL.createObjectURL).not.toHaveBeenCalled();
  });

  it("turns both buttons off without a service date, and says why", async () => {
    const d = testDraft();
    const { api } = renderReview({ ...d, readings: { ...d.readings, date_iso: "" } });
    const card = await documentsCard();
    expect(within(card).getByText(NEEDS_DATE)).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "Download pastor's copy" })).toBeDisabled();
    expect(within(screen.getByRole("region", { name: "Still needed" })).getByText(/No service date/)).toBeInTheDocument();
    expect(documentRequests(api)).toEqual([]);
  });
});
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
  it("renders each step route inside the shell: progress, the step or its placeholder card, and the footer links", async () => {
````

**with:**

````tsx
  it("renders each step route inside the shell: progress, the step, and the footer links", async () => {
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
      } else {
        expect(within(card).getByRole("heading", { name: "Available soon" })).toBeInTheDocument();
        expect(within(card).getByText("Keep using the current app for this part.")).toBeInTheDocument();
        expect(within(card).queryByRole("link")).toBeNull(); // no link to the old app (owner answer Q2)
      }
````

**with:**

````tsx
      } else {
        // Review & send is the real step from slice 5a-1: Still needed, the Word documents, the archive note.
        expect(within(card).getByRole("heading", { name: "Word documents" })).toBeInTheDocument();
        expect(within(card).getByRole("button", { name: "Download bulletin copy" })).toBeEnabled();
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      }
````

**In `frontend/src/test/fake-api.ts`, replace:**

````ts
 * - A handler is either a response body (sent as 200 JSON) or a function of the
 *   recorded request that returns a body or a `FakeResponse`, possibly after an
 *   `await` (a delayed response). A `FakeResponse` is a plain object with a numeric
 *   `status` and no keys other than `status`, `body` and `headers`; build error
 *   responses with `fakeError`.
````

**with:**

````ts
 * - A handler is either a response body (sent as 200 JSON) or a function of the
 *   recorded request that returns a body or a `FakeResponse`, possibly after an
 *   `await` (a delayed response). A `FakeResponse` is a plain object with a numeric
 *   `status` and no keys other than `status`, `body` and `headers`; build error
 *   responses with `fakeError`. A real `Response` (a file, slice 5a) is returned
 *   as it is.
````

**In `frontend/src/test/fake-api.ts`, replace:**

````ts
function toResponse(result: unknown): Response {

````

**with:**

````ts
function toResponse(result: unknown): Response {
  if (result instanceof Response) return result;

````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/review src/components/builder/builder-shell.test.tsx 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests |Error:")
```

**Expected:** 
```
   × builder shell (F §4.7) > renders each step route inside the shell: progress, the step, and the footer links <t>ms
 FAIL  |dom| src/components/builder/review/review-send-step.test.tsx [ src/components/builder/review/review-send-step.test.tsx ]
Error: Failed to resolve import "./documents-card" from "src/components/builder/review/review-send-step.test.tsx". Does the file exist?
 FAIL  |dom| src/components/builder/builder-shell.test.tsx > builder shell (F §4.7) > renders each step route inside the shell: progress, the step, and the footer links
TestingLibraryElementError: Unable to find an accessible element with the role "heading" and name "Word documents"
 Test Files  2 failed (2)
      Tests  1 failed | 10 passed (11)
```

- [ ] **Step 3 (agent): The card, the step, the route; the placeholder goes**

**Create `frontend/src/components/builder/review/documents-card.tsx`:**

````tsx
"use client";

import { DownloadIcon } from "lucide-react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import { useDraft } from "@/lib/draft/context";
import type { DraftV1 } from "@/lib/draft/schema";
import { hasServiceDate } from "@/lib/draft/status";
import type { DocumentVariant } from "@/lib/download";
import { useDownloadDocument } from "@/lib/queries/documents";

type Copy = { variant: DocumentVariant; title: string; description: string; action: string };

const COPIES: readonly Copy[] = [
  {
    variant: "bulletin",
    title: "Bulletin copy",
    description: "The order of worship with hymns, readings and the sermon title. Leaves out Prayers of the People.",
    action: "Download bulletin copy",
  },
  {
    variant: "pastor",
    title: "Pastor's copy",
    description: "Everything in the bulletin copy, plus Prayers of the People.",
    action: "Download pastor's copy",
  },
];

export const SAME_AS_BULLETIN = "Same as the bulletin copy for this service. Prayers of the People is empty or turned off.";
export const NEEDS_DATE = "Choose a service date on step 1 to download.";

/** The pastor's copy prints nothing more when Prayers of the People is off or blank (inv F1). */
function sameAsBulletin(draft: DraftV1): boolean {
  const card = draft.liturgy.cards.prayers_of_the_people;
  return !card.enabled || card.text.trim() === "";
}

function CopyRow({ copy, disabled, helper }: { copy: Copy; disabled: boolean; helper: string | null }) {
  const download = useDownloadDocument(copy.variant);
  const slow = useStillWorking(download.isPending);
  const pendingLabel = slow ? "Still working…" : "Preparing…";
  const id = `${copy.variant}-copy`;
  return (
    <li className="grid gap-2">
      <h3 id={`${id}-title`} className="text-base font-medium">
        {copy.title}
      </h3>
      <p id={`${id}-description`} className="text-sm text-muted-foreground">
        {copy.description}
      </p>
      {helper ? (
        <p id={`${id}-helper`} className="text-sm text-muted-foreground">
          {helper}
        </p>
      ) : null}
      <PendingButton
        size="touch"
        variant={copy.variant === "bulletin" ? "default" : "outline"}
        className="w-full sm:w-fit"
        pending={download.isPending}
        pendingLabel={pendingLabel}
        disabled={disabled}
        aria-describedby={helper ? `${id}-description ${id}-helper` : `${id}-description`}
        onClick={() =>
          download.mutate(undefined, {
            onError: (e) => {
              // A 401 or a lost church is handled globally (sign-in, the church's own message): no second message.
              if (e.status === 401 || isNoChurchAccess(e)) return;
              toast.error(errorToastMessage(e));
            },
          })
        }
      >
        <DownloadIcon data-icon="inline-start" aria-hidden="true" />
        {copy.action}
      </PendingButton>
      <p role="status" className="sr-only">
        {download.isPending ? `${copy.title}: ${pendingLabel}` : ""}
      </p>
    </li>
  );
}

/**
 * The Word documents card (slice 5a spec, UX "Word documents card"; owner
 * answers 3 and 7, 2026-10-01): the bulletin copy and the pastor's copy, each
 * built on the server from the draft as it is at the tap. Each button has its
 * own "Preparing…" ("Still working…" after 8 s); the file then goes to the
 * browser's download (on iPhone, the share or preview sheet), with no toast;
 * a failure is a toast with the server's message (none after a 401 or a lost
 * church: the app's own handling says it). Both buttons need a valid
 * service date, nothing else: what is missing is listed above, and the file
 * prints what there is ("[Sermon title]" for a blank title).
 */
export function DocumentsCard() {
  const { draft } = useDraft();
  const dated = hasServiceDate(draft);
  const same = sameAsBulletin(draft);
  return (
    <section aria-labelledby="documents-title" className="grid gap-4 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="documents-title" className="text-base font-medium">
          Word documents
        </h2>
        {dated ? null : <p className="text-sm text-muted-foreground">{NEEDS_DATE}</p>}
      </div>
      <ul className="grid gap-6">
        {COPIES.map((copy) => (
          <CopyRow
            key={copy.variant}
            copy={copy}
            disabled={!dated}
            helper={copy.variant === "pastor" && same ? SAME_AS_BULLETIN : null}
          />
        ))}
      </ul>
    </section>
  );
}
````

**Create `frontend/src/components/builder/review/review-send-step.tsx`:**

````tsx
"use client";

import { StillNeeded } from "@/components/builder/still-needed";

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
    </section>
  );
}
````

**In `frontend/src/app/(signed-in)/(church)/builder/review/page.tsx`, replace:**

````tsx
import { StepPlaceholder } from "@/components/builder/step-placeholder";
import { StillNeeded } from "@/components/builder/still-needed";

/** Step: Review & send. Slice 5a replaces the placeholder; "Still needed" lists shipped steps' gaps. */
export default function ReviewStepPage() {
  return (
    <>
      <StepPlaceholder step="review" />
      <StillNeeded />
    </>
  );
}
````

**with:**

````tsx
import { ReviewSendStep } from "@/components/builder/review/review-send-step";

/** Step: Review & send (slice 5a-1: Still needed and the Word files; 5a-3 adds saving). */
export default function ReviewStepPage() {
  return <ReviewSendStep />;
}
````

**In `frontend/src/lib/draft/steps.ts`, replace:**

````ts
 * `SHIPPED_STEPS` holds the steps whose content has shipped. An unshipped
 * step shows the "Available soon" card, the muted status "Soon" (Review: "Not
 * in archive"), and `stillNeeded` ignores it. Slice 2b shipped none (owner
 * answer Q1, 2026-09-28); slice 2c ships "readings", slice 3b "hymns" and
 * slice 4b "liturgy". 5a adds "review".
````

**with:**

````ts
 * `SHIPPED_STEPS` holds the steps whose content has shipped. An unshipped
 * step shows the muted status "Soon" (Review: "Not in archive"), and
 * `stillNeeded` ignores it. Slice 2b shipped none (owner answer Q1,
 * 2026-09-28); slice 2c ships "readings", slice 3b "hymns" and slice 4b
 * "liturgy". Review's route has its real content from 5a-1 (Still needed and
 * the Word files); "review" joins the set in 5a-3, when saving gives it the
 * statuses "Saved" and "Unsaved changes".
````

```bash
git rm -q frontend/src/components/builder/step-placeholder.tsx
grep -rn "step-placeholder\|StepPlaceholder" frontend/src; echo "placeholder grep exit $?"
```

**Expected:** `placeholder grep exit 1`.

- [ ] **Step 4 (agent): Run the files three times, the suite, the types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/components/builder/review src/components/builder/builder-shell.test.tsx 2>&1 | grep -E "^ +× |FAIL|Tests "); done
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
grep -c "—" frontend/src/components/builder/review/documents-card.tsx frontend/src/components/builder/review/review-send-step.tsx
```

**Expected:** three times `      Tests  17 passed (17)` (6 new, 11 in the shell test) with no `×` or `FAIL` line; ` Test Files  81 passed (81)` and `      Tests  611 passed (611)`; `typecheck 0`, `lint 0`; `…/documents-card.tsx:0` and `…/review-send-step.tsx:0` (no em dash in new copy).

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/components/builder/review/documents-card.tsx frontend/src/components/builder/review/review-send-step.tsx frontend/src/components/builder/review/review-send-step.test.tsx 'frontend/src/app/(signed-in)/(church)/builder/review/page.tsx' frontend/src/components/builder/builder-shell.test.tsx frontend/src/lib/draft/steps.ts frontend/src/test/fake-api.ts
git commit -q -m "Review step: Still needed, the Word documents and the archive note (5a-1; owner answers 1, 2, 7)" -m "Step 4 renders its real content: the 4b Still needed list, a Word
documents card (Download bulletin copy, Download pastor's copy, each with
its own Preparing... and Still working... after 8 s, the helper when the
two copies are the same, a toast with the message on failure but none
after a 401 or a lost church, off only without a service date) and a note that saving to the archive is coming.
StepPlaceholder, which nothing else used, is deleted. The fake API passes
a real Response through for files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

`git rm` in Step 3 already staged the deletion. Counts after Task 6: backend **1256 passed, 11 skipped**; frontend **611 in 81**.

### Task 7: Docs: S's amendment, the manual check and its heading pin (owner answers 1-9; clarification 18)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`, `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py`

- [ ] **Step 1 (agent): Write the docs**

**Append to `docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md`:**

````markdown

## Amendment 2026-10-01: three PRs, and the owner's answers before the 5a plans

The owner answered nine questions on 2026-10-01 (binding). Where this spec says otherwise, these win:

1. **Three PRs, not two.** 5a-1: Word downloads end to end (`POST /documents`, `service_output`, `build_docx`'s new signature, the Review step's Word documents card); no database change. 5a-2: saving (`/services`, `usecases/archive.py`'s save, list, open and delete, hymn use on save) with migration `0005_services_extras` on its own. 5a-3: the Save card on the Review step, the Services page, `serviceToDraft`, the draft version bump. Plan: `docs/superpowers/plans/2026-10-01-slice-5a1-documents.md`.
2. **No "Order of worship" card on the Review step:** the Liturgy step already shows the order. `orderOfWorship`, `order-of-worship.tsx` and `order_of_worship.json` are dropped. Review keeps the list of what is missing and the downloads (Save comes in 5a-3).
3. **The Word file keeps Streamlit's layout exactly** (Times New Roman 11 pt, Word's Heading 2, the date as "October 04, 2026", `worship_October_04_2026.docx`), with the decided fixes: "First Reading", hymn headings by slot, no "#None", the readings from `resolve_readings`.
4. (5a-2, 5a-3) A saved service fixes a Benediction that followed the church default, and the communion setting, to what was saved.
5. (5a-3) "Readings for … are available" does not show while the date is still the saved service's date.
6. (5a-2) **Streamlit is retired for real use** (the owner has stopped using it). Deleting a service recalculates that date's hymn use from the services still saved for it. This supersedes open question 1 and behavior change 4 above; a re-dating PUT does the same for the old date. The frozen app and the `streamlit-frozen` branch stay untouched.
7. **On a phone, iOS's share or preview sheet is accepted.** If the owner's phone check finds the download does not start, the fallback is a second tap: the button becomes "Save {filename}", a real `<a download>` link (Risks). 5a-1 documents it and builds it only if the check needs it.
8. **Checks:** a guided phone check after each PR. 5a-2 adds a backup, read-only counts and the migration's `--sql` preview first. No Streamlit compatibility check: manual check 10 and the Streamlit smoke in check 14 are dropped.
9. Reviewer notes stay in memory: opening a saved service clears them; saving keeps them.

**5a-1 as planned.** `ServiceDraft` (with `CustomElementIn`) is in `api/schemas.py` from 5a-1, the body of `POST /documents`; `usecases/archive.py` starts with `ServiceInput`, `clean_input` and `resolve_hymn_refs`, which `usecases/documents.build_document` uses. The Review step shows "Still needed" (unchanged from 4b), the Word documents card and a short "coming soon" note for the archive; `StepPlaceholder` is deleted, `StillNeeded` stays until 5a-3. `"review"` joins `SHIPPED_STEPS` in 5a-3. Until 5a-2, hymn use is not recorded anywhere (Streamlit recorded it on Prepare).
````

**Append to `docs/manual-verification.md`:**

````markdown

## Slice 5a

Run on the production URL https://worship-service-builder.vercel.app, on an
iPhone with Safari at 375 px and on desktop Chrome. These are the slice 5a
spec's manual checks (Testing → Manual checks) for the Word downloads, as
amended on 2026-10-01 (three PRs; no Streamlit check). After the 5a-1 merge
the owner's guided check (owner answer 8, one step at a time on the phone)
covers the items marked "(owner, after 5a-1)"; its result goes into
`docs/ops-runbook.md` → "Slice 5a-1 record". 5a-2 and 5a-3 add their own
items here. Record what the page and the file show, never an email address
or a church id.

- [ ] (owner, after 5a-1) **1.** Build a service and open **4 Review & send**. Tap **Download bulletin copy**: the button says "Preparing…", then the share or preview sheet opens with `worship_October_04_2026.docx` (for that date). The file opens; it has the title, the date as "October 04, 2026", "First Reading", the sermon title, and no Prayers of the People.
- [ ] (owner, after 5a-1) **2.** Switch on Prayers of the People with text: the **pastor's copy** includes it and the bulletin copy does not. With it off, the pastor's copy says "Same as the bulletin copy for this service. Prayers of the People is empty or turned off."
- [ ] (owner, after 5a-1) **3.** Leave the Opening hymn empty and choose a Response hymn: the file has "Second Hymn" and no "First Hymn"; no hymn line ends in "#None".
- [ ] **4.** With RCL readings and no NT pick, the NT reading is the epistle, not the Psalm. Pick the Gospel as the NT reading, then edit that line: the Bulletin readings select shows "Automatic: {epistle}", and a new download prints that epistle.
- [ ] **5.** On desktop Chrome the download has the server's filename, and the file looks like the Streamlit one: Times New Roman 11 pt, Word's Heading 2 headings, People lines and the Prayer of Confession in bold, communion after the Second Hymn.
- [ ] **6.** Clear the service date: both download buttons are off with "Choose a service date on step 1 to download."
- [ ] (owner, after 5a-1) **7.** At 375 px: no sideways scroll on **Review & send**; the download buttons are full width and at least 44 px tall.
- [ ] **8.** Switch church: a download uses that church's draft.
````

**In `backend/tests/test_slice1_docs.py`, replace:**

````python
    # Slices 2c, 3b and 4b append "## Slice 2", "## Slice 3" and "## Slice 4" after this section (their specs, Manual
    # checks), and the service reviewer "## Service reviewer".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-6:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4", "## Service reviewer"]
````

**with:**

````python
    # Slices 2c, 3b and 4b append "## Slice 2", "## Slice 3" and "## Slice 4" after this section (their specs, Manual
    # checks), the service reviewer "## Service reviewer", and slice 5a-1 "## Slice 5a".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-7:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4", "## Service reviewer",
                        "## Slice 5a"]
````

- [ ] **Step 2 (agent): Check the docs tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
grep -c "—" <(git diff -U0 -- docs | grep '^+' | grep -v '^+++')
.venv/bin/python -m pytest -q | tail -1
git diff --stat | tail -1
```

**Expected:** `89 passed in <t>s`; `4`; `0` (no em dash added); `1256 passed, 11 skipped in <t>s`; `3 files changed, 41 insertions(+), 3 deletions(-)`.

- [ ] **Step 3 (agent): Commit**

```bash
git add docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -q -m "Docs: slice 5a split in three PRs, the owner's answers, the 5a-1 manual check (owner answers 2026-10-01)" -m "The 5a spec gains an amendment with the owner's nine answers of
2026-10-01: three PRs, no order-of-worship card, the Word file's exact
parity, Streamlit retired (deleting a service recalculates hymn use,
superseding open question 1), the iPhone share sheet accepted with a
second-tap fallback. docs/manual-verification.md gains '## Slice 5a' with
the owner's phone items for 5a-1; test_slice1_docs pins seven headings." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 4 (controller): Review the batch (T1-T7) and backup push**

One review of the whole batch: `build_docx`'s output equals the old function's but for the four documented changes (the XML tests), and nothing else in `worship_service` moved; the route's headers exactly as F §1.9 and clarification 6, no idempotency and no bucket; `build_document` reads in one short session, writes nothing and logs no text; `ServiceDraft`'s limits are slice 4's and `HymnRef`, `SlotHymns`, `SectionKey` are unchanged (F §1.3); `apiFetch` behaves exactly as before (its tests unchanged) and `apiFetchBlob` maps errors the same way; `documentRequest` never sends what the server refuses; one mutation per button, nothing cached; the card's copy exactly clarification 16, no em dash; 44 px targets, wrapping at 375 px, the status lines and descriptions as clarification 15; the docs match. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

Counts after Task 7: backend **1256 passed, 11 skipped**; frontend **611 in 81**.

### Task 8: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 8)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the frontend three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error")
```

**Expected:** `1256 passed, 11 skipped in <t>s`; three times ` Test Files  81 passed (81)` and `      Tests  611 passed (611)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s` and no `Error` (the build runs in the real checkout; a font `Failed to fetch` only: say so and rely on CI).

- [ ] **Step 3 (agent): The API files match, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/service_output.py backend/usecases/archive.py backend/usecases/documents.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
ls backend/migrations/versions | grep -c '^0'
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations backend/db .github frontend/package.json frontend/package-lock.json docs/ops-runbook.md app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); `imports grep exit 1`; `raw html grep exit 1`; `4` (no new migration); exactly these 39 paths:
```
M	backend/api/main.py
A	backend/api/routes/documents.py
M	backend/api/schemas.py
A	backend/service_output.py
A	backend/tests/fixtures/shared/docx_filenames.json
A	backend/tests/test_api_documents.py
A	backend/tests/test_build_docx_characterization.py
M	backend/tests/test_communion_docx.py
M	backend/tests/test_liturgy_config.py
M	backend/tests/test_no_streamlit_in_core.py
A	backend/tests/test_service_output.py
M	backend/tests/test_slice1_docs.py
A	backend/tests/test_usecase_documents.py
A	backend/usecases/archive.py
A	backend/usecases/documents.py
M	backend/worship_service.py
M	docs/manual-verification.md
A	docs/superpowers/plans/2026-10-01-slice-5a1-documents.md
M	docs/superpowers/specs/2026-09-25-slice-5a-documents-archive-design.md
M	frontend/src/app/(signed-in)/(church)/builder/review/page.tsx
M	frontend/src/components/builder/builder-shell.test.tsx
A	frontend/src/components/builder/review/documents-card.tsx
A	frontend/src/components/builder/review/review-send-step.test.tsx
A	frontend/src/components/builder/review/review-send-step.tsx
D	frontend/src/components/builder/step-placeholder.tsx
M	frontend/src/lib/api/client.test.ts
M	frontend/src/lib/api/client.ts
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/timeouts.ts
A	frontend/src/lib/documents.test.ts
A	frontend/src/lib/documents.ts
A	frontend/src/lib/download.test.ts
A	frontend/src/lib/download.ts
M	frontend/src/lib/draft/steps.ts
M	frontend/src/lib/liturgy/request.ts
M	frontend/src/lib/queries/client.ts
A	frontend/src/lib/queries/documents.ts
M	frontend/src/test/fake-api.ts
```
`0`; the subjects oldest first: the plan's (`WIP plan: slice 5a-1` …, `Plan: slice 5a-1, Word downloads (owner answers 2026-10-01)`), then T1-T7's seven subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** one `✓ Logged in` line; `[]`. Send the owner exactly this, and wait for a clear yes:

> Slice 5a-1 (Word downloads) is verified on this machine: backend 1256 passed, 11 skipped (1223 before); frontend 611 tests in 81 files (597 in 78 before), three runs in a row; typecheck, lint and the production build are clean. It adds one API route, `POST /documents`, and no database change. On step 4 you get "Download bulletin copy" and "Download pastor's copy", built from your draft each time, in Streamlit's layout with "First Reading", hymn headings by slot and no "#None". Saving comes in the next two PRs. May I open the pull request as a **draft** titled "Slice 5a-1: Word downloads", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/slice5a1-pr-body.md" <<'BODY'
Slice 5a-1: Word downloads end to end (the first of three 5a PRs; owner answers of 2026-10-01). Plan: docs/superpowers/plans/2026-10-01-slice-5a1-documents.md. No database change, no new variable; one new route.

- POST /documents (church-scoped, any member): {variant: bulletin | pastor, service: ServiceDraft} in, the Word file out, with Content-Disposition (worship_October_04_2026.docx) and Cache-Control: no-store. A pure render: nothing written, nothing cached, no idempotency key, no rate-limit bucket.
- build_docx keeps Streamlit's layout (pinned against a verbatim copy of the old function, compared as document XML), with "First Reading", hymn headings by slot, no "#None", and the readings resolve_readings picks.
- service_output (pure): the date line, names, headers, variants. usecases/archive.py starts with ServiceInput, clean_input, resolve_hymn_refs; ServiceDraft is in api/schemas.py for 5a-2 and 5b.
- Client: apiFetchBlob (one send() with apiFetch), the body within the server's limits, docxFilename (shared fixture), downloadBlob, one mutation per button.
- Review & send: Still needed (unchanged), the Word documents card, a note that saving is coming. StepPlaceholder deleted.
- The 5a spec gains the owner's nine answers (three PRs; Streamlit retired, so deleting a service will recalculate hymn use in 5a-2).

Later: 5a-2 (saving, 0005_services_extras), 5a-3 (Save card, Services page).

Tests: backend 1223 → 1256 passed, 11 → 11 skipped; frontend 597 → 611 in 78 → 81 files

After merge (Task 9): a short check on the owner's phone, then a "Slice 5a-1 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 5a-1: Word downloads" \
  --body-file "<scratch>/slice5a1-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1256 passed, 11 skipped`, backend-postgres `11 passed, 1256 deselected`, frontend `611 passed` in 81 files. Then send: "PR #<N> is green: backend 1256 passed, 11 skipped; 611 frontend tests in 81 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_service_output.py`, `docx_filenames.json` | T1 |
| `test_build_docx_characterization.py`, `test_liturgy_config.py`, `test_communion_docx.py` | T2 |
| `test_usecase_documents.py`, `test_api_documents.py`, `test_no_streamlit_in_core.py`, `test_route_guards.py`, `test_openapi_contract.py` | T3 |
| `client.test.ts` | T4 |
| `download.test.ts`, `documents.test.ts` | T5 |
| `review-send-step.test.tsx`, `builder-shell.test.tsx` | T6 |
| `test_slice1_docs.py`, `test_docs.py` | T7 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, 5a-1 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1256 passed, 11 skipped`; frontend `611 passed` in 81 files.

### Task 9: Merge, the owner's phone check (four steps), the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate (production stays at `0004_invites_reusable`); Railway serves the new route and Vercel the new step. The owner's check is **one step at a time** (send one, wait for the report or "next"). The agent writes each result into `<scratch>/slice5a1-t9-results.md` (not committed). Record what the page and the file showed, never a token, an email address or a church id.

**Files:** Modify (the records PR, Step 8): `docs/ops-runbook.md`: insert `### Slice 5a-1 record` right after the "Reviewer follow-up 2 record" table (its last row starts `| Follow-ups | Open question for the owner (needs copy)`) and before `## Backups`. A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (slice 5a-1, Word downloads) is ready, green and up to date with main. There is no database change. Then I will ask you for four short checks on your phone, one at a time. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about two minutes for Vercel and Railway before Step 2.

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 4: the bulletin copy downloads and opens**

> On your phone, open https://worship-service-builder.vercel.app (signed in, in your church) and build a service as you normally would, or keep the one you have: a date, readings, at least one hymn, a few liturgy sections and a sermon title. Tap **4 Review & send**. Under **Word documents**, tap **Download bulletin copy**. The button says "Preparing…" for a moment; then your phone should show its share or preview sheet (or a "Download?" question) for a file named like `worship_October_04_2026.docx` (with your date). Wait about a minute on that sheet before you confirm it, then open the file (Word, Files or the preview). Does it start with "Worship Service", the occasion and the date written like "October 04, 2026"? Is the first reading under the heading "First Reading", and is the sermon title there? Is Prayers of the People left out? If nothing happened after "Preparing…", tell me that too.

Record whether the sheet or a download appeared, the filename, how long "Preparing…" showed, whether the file still saved after the minute's wait, and each answer. **If no download started**, record it and stop here: the follow-up is clarification 11's "Save {filename}" link, a small PR for the owner to approve; the remaining steps can wait for it.

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 4: the pastor's copy**

> Go to **3 Liturgy**, switch on **Prayers of the People** and give it some text (type a line, or tap Generate). Come back to **4 Review & send** and tap **Download pastor's copy**. Does that file include Prayers of the People, and does the bulletin copy still leave it out? Then switch Prayers of the People off again: under "Pastor's copy" the card should now say "Same as the bulletin copy for this service. Prayers of the People is empty or turned off." Does it?

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 4: hymn headings by slot**

> On **2 Hymns**, clear the **Opening** hymn (its ✕) and make sure a **Response** hymn is chosen. Back on **4 Review & send**, download the bulletin copy again. In the file, is there a "Second Hymn" with your Response hymn and no "First Hymn"? Does every hymn line read like "Title — #123" (or just the title when it has no number), with no "#None"? Then put your Opening hymn back.

- [ ] **Step 5 (OWNER, then agent): Phone, step 4 of 4: the page on the phone, and the layout**

> On **4 Review & send**: does the page fit the screen with no sideways scrolling, and are the two download buttons full width and easy to tap? Below them, a dashed box says "Saving services to the archive is coming soon." If you still have a Word file the old app made, does the new one look the same apart from "First Reading" (same font, same headings, people's lines and the confession in bold, communion after the Second Hymn)?

- [ ] **Step 6 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/slice5a1-t9-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 7 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^### Reviewer follow-up 2 record$\|^| Follow-ups | Open question for the owner (needs copy)\|^## Backups$' docs/ops-runbook.md
```

**Expected:** `Fast-forward` (or `Already up to date.`); three lines in that order. Insert, between that last row and `## Backups` (one blank line on each side):

```markdown
### Slice 5a-1 record

Slice 5a-1 (Word downloads end to end: `POST /documents`, the bulletin copy
and the pastor's copy built on demand from the draft in Streamlit's layout,
with "First Reading", hymn headings by slot and no "#None"; the Review step's
Word documents card) merged as PR #<N>, the first of three 5a PRs (owner
answers of 2026-10-01). No database change and no new variable; production
stays at `0004_invites_reusable` (head). The owner's check was four steps on
a phone, covering the "(owner, after 5a-1)" items of
`docs/manual-verification.md` → "Slice 5a". No token, email address or church
id is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success | <date> |
| 1. Bulletin copy (phone: <phone and browser>) | <The share sheet opened with worship_<date>.docx after about <n> s and still saved it after a minute's wait; the file had the title, the date line, First Reading and the sermon title, and no Prayers of the People. / No download started: follow-up "Save {filename}" link (clarification 11).> | <date> |
| 2. Pastor's copy | <Included Prayers of the People; the bulletin copy did not; with it off, the card said "Same as the bulletin copy …". / …> | <date> |
| 3. Hymn headings by slot | <"Second Hymn" with the Response hymn and no "First Hymn"; no "#None". / …> | <date> |
| 4. The page and the layout | <No sideways scroll; full-width buttons; the archive note showed; the file matched the old layout but for First Reading. / …> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: 5a-2 (saving: `/services`, hymn use recorded on save and recalculated on delete, `0005_services_extras`, with a backup, read-only counts and the `--sql` preview first), then 5a-3 (the Save card, the Services page). Hymn use is not recorded until 5a-2. Still open: the reviewer's screen-reader copy question (Reviewer follow-up 2 record), first-line matching research (Hymnary.org), the NUL-character 500 on the other routes (app-wide; `/documents` cleans such characters since 5a-1), and the two slice 1 test churches (kept for now, owner) | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Then:

(not replayed)
```bash
sed -n '/^### Slice 5a-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 5a-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 5a-1 record (merged; owner's phone check)" -m "Records slice 5a-1 (PR #<N>): the merge and CI on main, and the owner's
four-step phone check (the bulletin copy downloads and opens, the pastor's
copy, hymn headings by slot, the page and the layout). No token, email or
church id is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 8 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 5a-1 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes:

(not replayed)
```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 5a-1 record" \
  --body "Records slice 5a-1 (PR #<N>) in docs/ops-runbook.md → Slice 5a-1 record: the merge and the owner's four-step phone check. No token, email or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Slice 5a-1 is live and recorded; <n> follow-ups. Next: the 5a-2 plan (saving)."

- [ ] **Step R (only if the release must come out): Revert**

Code only (no data was written; no draft shape changed). On the owner's yes for each outward command: a branch `claude/revert-slice-5a1` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert slice 5a-1 (PR #<N>)" with the trailer, both suites (`1223 passed, 11 skipped`; `597 passed` in 78), a PR, CI, and the merge on the owner's yes; record it in the 5a-1 record. Review then shows the "Available soon" card again.

Expected counts after this task: backend `1256 passed, 11 skipped` on `main`; frontend `611 passed` in 81 files. The records PR adds no test.

---
## Build notes

**How this plan was written (2026-10-01).** Each task's code was built and run in a throwaway worktree of `934ffb9` (the repo's `.venv`, the checkout's `node_modules`), then the directives were generated from those files and replayed onto a fresh worktree of `934ffb9` by a script that applies every Create, Append and Replace directive of T1-T7 in order (plus T6's `git rm`), running each task's commands. While building:
- **The date test reads no locale.** A test that switched `LC_TIME` to German would skip on this machine (no such locale) and change the skipped count; `test_the_date_line_never_reads_the_locale` passes a `date` whose `strftime` raises instead.
- **`render_docx` imports `worship_service` inside the function,** because `worship_service` imports `hymn_line` from `service_output`; the import at the top would be circular.
- **`ServiceDraft.to_input()` imports the usecases inside the method,** so importing `api/schemas.py` (every route module does) does not import the usecases and the database layer with it.
- **Two status lines** (one per copy) made `getByRole("status")` ambiguous; the test reads both.
- **The fake API's change** (a real `Response` passes through) is needed only by T6's DOM tests, so it moved from the build's T4 to T6.

**Replay of the finished plan (2026-10-01).** The directives of T1-T7 were applied in order onto a fresh detached worktree of `934ffb9` (symlinks to the repo's `.venv` and `frontend/node_modules`), with T6's `git rm`, running each task's commands:
- All directives applied (T1 3, T2 17, T3 10, T4 5, T5 13, T6 9, T7 3); every Replace anchor occurred exactly once, and every Append landed on the file as the task before left it. After T7 the tree was identical to the build worktree's (`git diff` between the two: empty).
- Every "see it fail" output matched as quoted (T1 one collection error; T2 `8 failed`, then `3 failed, 11 passed`; T3 one collection error; T4 `4 failed | 18 passed (22)`; T5 two files that cannot load; T6 one file that cannot load and `1 failed | 10 passed (11)`), and every count matched the table: backend 1229, 1237, 1254 (11 skipped); frontend 601 in 78, 604 in 80, 609 in 81; the T6 files three times and the whole suite three times at the end, with no `×` or `FAIL` line; typecheck 0 and lint 0 after T3-T6; the OpenAPI export and `gen:api` gave `2 files changed, 448 insertions(+)` and, run again at the end, no change; the docs tests `89 passed`, owner markers `4`, no em dash added, `3 files changed, 41 insertions(+), 3 deletions(-)`; four revisions; no raw HTML; the 38 code paths of T8 Step 3 exactly. No flaky run.
- One check was corrected by the replay: T2 Step 5's grep first matched "Old Testament Reading" in the new comment that records the rename; it now looks for the old `add_paragraph("Old Testament Reading"` call only. T3 Step 4's count is `7`, not 4 (each schema also appears in a `$ref`).

**Review fixes and their replay (2026-10-01).** After the owner's "all recommended", the plan review's five fixes went in (clarification 19): `_xml_safe` in `clean_input` and for the database's hymn title, with two API tests (T3: `test_api_documents.py` 12 → 14); no toast after a 401 or a lost church, with a DOM test (T6: 5 → 6 cases); the object URL kept 5 minutes, with a `downloadBlob` timing test (T5: `download.test.ts` 1 → 2) and the one-minute wait in T9's phone step 1; the bulletin picks cut to 200 (T5, a case added to the limits test); the three helpers copied into the parity test (T2, its count unchanged). Checked first: python-docx 1.2.0 writes `"a\nbc"` as `a`, `<w:br/>`, `bc` and reads it back as `"a\nbc"`. Then the whole plan was replayed again onto a fresh detached worktree of the branch head (`934ffb9` plus the plan commits, so the same code), the same way:
- All directives applied with the same counts (T1 3, T2 17, T3 10, T4 5, T5 13, T6 9, T7 3), every Replace anchor exactly once.
- Every "see it fail" output matched as quoted (unchanged), and the counts matched the table: backend 1229, 1237, 1256 (11 skipped); T3's files `30 passed`; frontend 601 in 78, 605 in 80 (T5's files `4 passed`), 611 in 81 (T6's files `17 passed` three times); the whole frontend suite three times at the end, 611 each, no `×` or `FAIL`; typecheck 0 and lint 0 after T3-T6; the OpenAPI change still `2 files changed, 448 insertions(+)` and `7` (the schemas did not change), no change when regenerated at the end; T7 `89 passed`, `4`, `0`, `3 files changed, 41 insertions(+), 3 deletions(-)`; four revisions; no raw HTML; the 39 paths of T8 Step 3 exactly. No flaky run.
- Each new test was seen to fail with its fix undone (`_xml_safe` returning its input: both new API tests fail, the first with a 500; the `onError` guard removed: the DOM case fails; `REVOKE_AFTER_MS` at 60 s: the timing test fails; the NT pick unclipped: the limits test fails).
- Not run while planning: the production build (Turbopack refuses the replay's symlinked `node_modules`; T8 runs it in the real checkout), the pushes, the PR and CI, the merge and the owner's checks, and a download on a real phone.

## Spec coverage

| Owner answer or S item | Task(s) and tests |
|---|---|
| 1. Three PRs; this one has no database change | the plan's scope; T8 Step 3 (`4` revisions; no `backend/migrations` or `backend/db` path); T7 S amendment |
| 2. No order-of-worship card; the checklist and the downloads | T6 `review-send-step.test.tsx` "shows Still needed, both copies …", `builder-shell.test.tsx` (the Review case and its Still needed rows) |
| 3. Streamlit's layout exactly; "First Reading"; slots; no "#None"; the date line and filenames | T2 `test_a_full_service_prints_exactly_as_streamlit_did_but_for_the_first_reading_heading` (both variants), `test_a_sparse_service_prints_as_before_with_every_anchor`, `test_the_title_date_fonts_and_bold_text_are_unchanged`, `test_hymn_headings_follow_slots_and_never_print_none`, `test_render_docx_prints_the_readings_the_screen_shows`, `test_the_outline_is_build_docx_s_heading_order`; T1 `test_dates_and_filenames_follow_the_shared_fixture`; T3 `test_both_copies_download_with_the_file_headers`; T9 steps 1, 3, 4 |
| 3. Bulletin and pastor's copies as S defines them | T2 `test_render_docx_variants`; T3 `test_build_document_prints_the_cleaned_service_with_its_hymns`; T6 "names the pastor's copy itself …"; T9 step 2 |
| 4, 5, 9 (PR 2 and 3) | out of scope; recorded in S's amendment (T7) |
| 6. Streamlit retired; delete recalculates hymn use (PR 2) | S's amendment supersedes open question 1 (T7); clarification 14 (nothing recorded until 5a-2) |
| 7. iOS sheet accepted; the "Save {filename}" fallback | clarification 11 (documented, not built); T9 step 1 decides |
| 8. A guided phone check | T9 Steps 2-5; `docs/manual-verification.md` "## Slice 5a" (T7) |
| S API `/documents` row, F §1.9 headers, CORS exposure | T3 `test_both_copies_download_with_the_file_headers`, `test_the_filename_header_is_readable_cross_origin` |
| S API errors: hymn 404 with `details.field`, 422 with `fields`, 500 without python-docx | T3 `test_only_members_and_only_the_church_s_hymns`, `test_a_bad_body_is_a_422_naming_the_field` (6 cases), `test_a_blank_custom_label_is_the_usecase_s_422`, `test_a_label_of_only_a_nul_is_the_blank_label_422`, `test_without_python_docx_it_is_a_logged_500`; T2 `test_without_python_docx_it_raises` |
| S AC10 (member allowed, non-member 403, isolation) | T3 `test_any_member_may_download`, `test_only_members_and_only_the_church_s_hymns` (`assert_church_isolated`); `test_route_guards.py` unchanged and passing |
| S `clean_input`, `resolve_hymn_refs`; `build_document` writes nothing, logs no text | T3 `test_characters_a_word_file_cannot_hold_are_cleaned_not_a_500` (clarification 19), `test_clean_input_trims_and_drops_blanks_and_streamlit_errors`, `test_a_blank_custom_label_is_a_422_on_its_field`, `test_hymn_ids_resolve_in_the_church_and_snapshots_are_kept`, `test_build_document_writes_nothing`, the log assertions |
| S behavior change 7 / AC4 (stale pick prints the automatic reading) | T1 `test_doc_readings_are_resolve_readings` (every `scripture_refs.json` case); T2 `test_render_docx_prints_the_readings_the_screen_shows` |
| S `service_output` helpers (`hymn_line`, `content_disposition`, `VARIANTS`, `is_legacy_error_placeholder`) | T1 `test_headers_and_variants`, `test_hymn_lines_never_print_none`, `test_legacy_error_placeholders`, `test_the_date_line_never_reads_the_locale` |
| F §4.5 `apiFetchBlob`; F §1.8 30 s | T4 `client.test.ts` (four cases) |
| S `docxFilename` with the shared fixture; `downloadBlob` (5-minute revoke) | T5 `download.test.ts` (two cases); T6 "downloads the bulletin copy …" (header name, no early revoke) |
| F §4.6 the payload; within the limits (the picks cut to 200) | T5 `documents.test.ts` (two cases) |
| S UX "Word documents card": pending per button, Still working after 8 s, helper, errors (none of its own after a 401 or a lost church), invalid date | T6 the six DOM cases |
| F §4.9 descriptions, status lines, 44 px | T6 "shows Still needed, both copies …" (descriptions, `h-11`), "names the pastor's copy …" (status lines) |
| `StepPlaceholder` deleted | T6 Step 3 grep; `builder-shell.test.tsx` |
| Layering (no FastAPI or Streamlit below the API) | T3 `test_no_streamlit_in_core.py` (four modules added) and the imports grep |
| OpenAPI and types regenerated | T3 Step 4; T8 Step 3; `test_openapi_contract.py` |

S items **not** in 5a-1 (by owner answer 1 or 2): the editing banner, the Save card and conflict dialog, the email card, the order-of-worship card and its fixtures, `/services`, migration `0005`, `serviceToDraft`, the save key, the draft version bump, `"review"` in `SHIPPED_STEPS`, the summary's archive half, the Services page, and the save hint.

## Questions for the owner

Your answers of 2026-10-01 (1-9) are binding and already in the plan. These are the choices the plan makes where you did not say; each is written as recommended. **Answered 2026-10-01: "all recommended"** (binding; recorded under "Owner decisions").

1. **The Review step's layout** (clarification 2): "Still needed", then the Word documents card, then a dashed "Archive" box saying "Saving services to the archive is coming soon." No email box (5b brings email, and "keep using the current app" is no longer true). Recommended: accept.
2. **"Still needed" stays exactly as you checked it in 4b** (clarification 3): same heading and rows, nothing shown when nothing is missing. The rename to "Still to do" and an "Everything's ready." line wait for 5a-3, with Save. Recommended: accept.
3. **The card's wording** (clarifications 5, 16), from the spec: "Bulletin copy: The order of worship with hymns, readings and the sermon title. Leaves out Prayers of the People."; "Pastor's copy: Everything in the bulletin copy, plus Prayers of the People."; the buttons "Download bulletin copy" (filled) and "Download pastor's copy" (outlined); "Preparing…", then "Still working…" after 8 seconds; "Same as the bulletin copy for this service. Prayers of the People is empty or turned off." when that section is off or blank; no message on success, a short message on failure. Recommended: accept.
4. **Only the date stops a download** (clarification 4): with no service date both buttons are off and the card says "Choose a service date on step 1 to download."; anything else missing still downloads (a blank sermon title prints "[Sermon title]", as before). Recommended: accept.
5. **No hymn use is recorded until 5a-2** (clarification 14): downloads never record it (the spec moves it to Save), and with Streamlit retired nothing records it in between, so "Used …" marks will not include services you build until 5a-2 ships. Recommended: accept (5a-2 is next).
6. **The iPhone fallback is written down, not built** (clarification 11): if your phone check shows the download does not start, a small follow-up PR adds the "Save {filename}" second tap. Recommended: accept.
7. **An occasion longer than 300 characters prints cut at 300** (clarification 9), as the AI already sees it; step 1 already warns about it. Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T8); the merge on your yes, then four phone checks one at a time and the records PR (T9).
