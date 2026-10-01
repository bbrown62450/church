# Reviewer Follow-up 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise from "Across the service" (runbook follow-up 5; owner answers 1-6 of 2026-10-01, "all recommended"; the plan's Questions 1-7, "all recommended", owner decision A, the same day, and owner answer A on when the note goes, the same day), in one PR built in one batch (about half a day). After it merges, the code note "Several prayers open with "…"." has a **Revise the other prayers** button: the first of those prayers keeps its text, and the others are revised one at a time, in service order, so each opens differently from the first and from the new openings before it; each shows "Revising…" with its own Cancel from the start, then "Revised with these notes. Undo"; when any of them is the member's own or saved text, one "Replace your text?" asks first. No route, schema, migration or variable changes; production Streamlit (https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`) is untouched.

**Architecture:** Frontend only, plus one backend test. The review's answer carries no sections for a note across the service (`NoteOut` is tag, text and source), so the frontend finds the prayers again from the draft by the backend's own rule (`review_checks.opening_words`: the first two words after any "Leader:"/"People:" label, any case). T1 ports that rule to `lib/liturgy/notes.ts` (`openingWords`, `sharedOpening`, `acrossTargets`, `acrossNote`, `listLabels`) and pins both sides to one new shared fixture, `backend/tests/fixtures/shared/opening_words.json`. T2 adds `reviseAcross(noteId)` to the review provider (`lib/liturgy/review.tsx`), which runs the other prayers one at a time through the existing per-card revision path, each with one note instead of the card's own, naming the new openings produced so far. T3 puts the button and its confirm in the "Across the service" box (`card-notes.tsx`), and lets a card with no notes of its own show its revision's failure. T4 is the docs. T5 verifies and opens the draft PR; T6 is the merge, the owner's three-step phone check and the record.

**Tech Stack:** as the service reviewer plan: Python 3.11 (`.venv`), pytest; Next 16, React 19, TypeScript 5, Base UI, Vitest 3 with Testing Library.

**Source documents:**
- Reviewer spec ("R"): `docs/superpowers/specs/2026-09-26-service-reviewer-design.md` ("Notes", "Revise with these notes", "Layer 1: code checks") and its amendment for follow-up 1.
- Follow-up 1 plan ("F1"): `docs/superpowers/plans/2026-10-01-reviewer-followup-1.md` (Revise on typed text, its confirm and focus rules; faded notes) and its record, `docs/ops-runbook.md` → "Reviewer follow-up 1 record" (its Follow-ups row names this plan).
- Facts checked for this plan (tree `b1ab12c` = `origin/main`, follow-up 1 merged and recorded, 2026-10-01): backend `1222 passed, 11 skipped`; frontend `581 passed` in 78 files; typecheck and lint clean; Alembic head `0004_invites_reusable`; 4 runbook owner markers; the docs tests `89 passed`. `check_openings` (`backend/review_checks.py`) runs on the cards the review was sent (every switched-on card with text, `reviewTargets`), keys each card by `opening_words` lowered and joined by a space, and writes one note per key that two or more cards share, `OPENING_NOTE` = `Several prayers open with "{words}".`, quoting the first card's words; the note's `match` stays in the backend. `ReviseIn` takes 1 to 3 notes of at most 240 characters and no origin. `revise(key)` in the provider already guards a card being written, a card already revising and a 429's wait, applies slice 4's stale rule twice, sets the Undo line ("revised") and drops the card's notes on success.
- Every task's code was written and run by the planner in a throwaway worktree of `b1ab12c`, and the directives were then replayed onto a fresh worktree of `b1ab12c` (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one file `.venv/bin/python -m pytest -q <file> 2>&1 | tail -2`; the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one file `(cd frontend && npx vitest run <path> 2>&1 | grep -E "Tests ")`; the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` (a failure is named); then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- No route or schema changes, so the OpenAPI snapshot and `schema.d.ts` are not regenerated (T5 checks they are unchanged).
- Branch `claude/slice-2-plan-4q33le`, at `origin/main` `b1ab12c` plus this plan's commits (`WIP plan: reviewer follow-up 2`, then `Plan: reviewer follow-up 2, Revise from Across the service (owner answers 2026-10-01)`), then T1-T4. Stage files by name; `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted. T1's backend test pins behavior that already exists, so it passes at once (said where it runs).
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`). A fix asked for by the review is a new commit, `Fix: <what> (Task <n> review)`.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1222 → 1223 passed, 11 → 11 skipped; frontend 581 → 597 in 78 → 78 files`.
- New prose for the owner has no em dashes and no flattery. The owner's copy is exact: "Revise the other prayers", "Replace your text?", "Revise replaces the text in {A} and {B}. You can undo each right after." (with "{A}", "{A} and {B}", "{A}, {B} and {C}"), "Revise text", "Keep my text", "Revising…", "Revised with these notes. Undo".
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.

### How the file directives below read
As in F1: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end; **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop.

### Baselines and counts
- Starting baselines: backend **1222 passed, 11 skipped**; frontend **581 passed in 78 files**, typecheck and lint clean; Alembic head **`0004_invites_reusable`** (no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new `def test_`; a frontend delta the number of new `it(`.

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +1 (`test_review_checks.py`) | 1223 passed, 11 skipped | +2 (`notes.test.ts`) | 583 in 78 |
  | T2 | 0 | 1223 passed, 11 skipped | +2 (`review.test.tsx`) | 585 in 78 |
  | T3 | 0 | 1223 passed, 11 skipped | +3 (`review-step.test.tsx`) | 588 in 78 |
  | T4-T6 | 0 | 1223 passed, 11 skipped | 0 | 588 in 78 |

- CI `backend-postgres` stays at `11 passed, 1223 deselected` (1222 before).

### Layering and code rules (carried)
- No backend code changes: routes stay plain `def` and unchanged; `review_checks.py` and `usecases/liturgy_review.py` are untouched; the `ai` bucket and its charging are unchanged (one token per revision, so revising two prayers costs two).
- Notes stay in memory only (never the draft, the archive or `localStorage`); `DraftV1` is unchanged.
- Touch targets 44 px below `md`; text wraps at 375 px; focus never drops to the page; no raw HTML.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** is https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`), frozen; merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **Reviewer decisions** (R, 2026-09-26, as amended by F1) stand.

### Owner answers (Beau, 2026-10-01, "all recommended", binding)
1. **Which notes get the button.** Only notes across the service where the app knows which prayers are involved: today, the code note "Several prayers open with "…"". AI notes across the service get no button (T1, T3).
2. **What is revised.** The first involved prayer in service order is kept unchanged; the others are revised so they open differently, each through the existing `POST /liturgy/revise` with a clear instruction as its note, e.g. `Opens with "Gracious God" like the Call to Worship; open differently.` (T1, T2).
3. **One confirm for your text.** If any prayer to be revised is typed or saved text (`needsRegenerateConfirm`), one confirm for the batch: title "Replace your text?", description "Revise replaces the text in {A} and {B}. You can undo each right after." ("A", "A and B", "A, B and C"), confirm "Revise text", other button "Keep my text". All-AI batches start at once (T3).
4. **Undo per card.** Each revised prayer gets its own "Revised with these notes. Undo" line (the existing per-card revise and Undo), independent of the others (T2).
5. **Label and progress.** The button reads "Revise the other prayers"; each card shows "Revising…" with its own Cancel while it runs (T3).
6. **Process:** this short plan, reviewed, the owner's approval, one build batch, a draft PR, a three-step phone check after the merge (the button revises the others, not the first; the confirm when your text is involved, and Undo per card; what happens to the note after the revisions land), then "### Reviewer follow-up 2 record" in `docs/ops-runbook.md` after "### Reviewer follow-up 1 record", before "## Backups" (T4, T6).

### Owner answers to the plan's questions (Beau, 2026-10-01, binding)
- **Questions 1-7** (below, "Questions for the owner"): "all recommended", as written, except that Question 5's wording is superseded by the answer below.
- **When the note goes, answer A (Beau, 2026-10-01).** After a "Revise the other prayers" batch, the note stays whenever two or more switched-on prayers still share the opening, including when every revision succeeded but the AI kept the opening; the button then offers them again. This replaces the earlier wording of Question 5 ("even if the AI happened to keep the opening") and matches the code (clarification 10).
- **Question 8, decision A: one at a time.** The other prayers are revised **one at a time**, in service order, not in parallel. Each request's note tells the AI to avoid the original shared opening and every new opening the batch has produced so far, e.g. `Opens with "Gracious God" like the Call to Worship; open differently, not with "Holy God" or "Loving God".` (clarification 4). While the batch runs, every prayer it will revise shows "Revising…" with its own Cancel from the start (no new copy); a Cancel on one not sent yet skips it; a Cancel on the running one moves on to the next; one edited meanwhile, gone stale or failed is skipped and the batch goes on; a 429 stops the batch (the rest are not sent, and the wait shows) and the note stays. The note goes only when every one was revised and fewer than two switched-on prayers still share the opening (owner answer A; clarifications 7-10; T2, T3).

## Spec clarifications

The owner's answers win over R and F1; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended).

1. **[owner-visible] Which notes, and when the button shows** (owner answer 1). A note gets the button when it is a code note (`source` "code"), tagged repetition, whose text is exactly `Several prayers open with "<words>".` (`sharedOpening`), and, as the draft is now, at least two switched-on prayers with text open with those words and at least one of the others can be revised (`acrossTargets` is not null). Otherwise there is no button and the note stays as it is (for example, after the member retyped one of two prayers so they no longer share the opening, or switched one off). Every AI note across the service has none.
2. **How the app knows the prayers: no API change** (owner decision 1). The note carries no sections, and `Note.match` is not sent. Rather than add a field to `NoteOut`, the frontend recomputes them at click time and at every render from the draft, with the same rule as `check_openings`: among the switched-on cards with text (`reviewTargets`, the cards a review sends), those whose first two words after any leading "Leader:" or "People:" label (any case, `\s*:\s*`, once), punctuation dropped, a word being a run of letters or digits with apostrophe-joined parts (`'` or `’`) and at most 30 characters, equal the note's words, any case. The TypeScript port uses `[\p{L}\p{N}]` for Python's `[^\W_]` (the same characters: Python's `\w` is letters, digits and `_`). The spaces around the label are Python's `\s`, spelled out as a class in TypeScript (`PY_SPACE`: `[\t\n\v\f\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]`), since JavaScript's `\s` also matches U+FEFF and misses U+001C-U+001F and U+0085. Both suites read `backend/tests/fixtures/shared/opening_words.json` (16 cases: labels, a label after U+0085 and one after a byte-order mark, which is no space to Python, apostrophes, an underscore, accents, a combining mark, a 31-character word) and `OPENING_NOTE`, so a change to either side fails a test. Its `groups` (added by the build review) pin which openings count as the same, any case: `check_openings` gives the note for them and `acrossTargets` finds every one from its words, Greek final sigma included (Python's `str.lower` and JavaScript's `toLowerCase` both apply it, checked on both sides first). Accepted difference: lowercasing differs only on letters added in Unicode versions newer than Python 3.11's; such an opening simply gets no button. Recomputing also means the button always matches what the member sees, not the draft as it was reviewed.
3. **[owner-visible] Which prayer is kept, and the Benediction** (owner answer 2). The prayers are taken in service order (the section order, Call to Worship first, Benediction last; custom elements are never reviewed). The first is kept. A Benediction that follows the church default (origin "default") still counts towards "several prayers" (the review counted it) but is never revised (as Revise never touches it, F1 owner answer 3); once edited it is typed text and is revised like any other. So when the only prayers sharing the opening are the first and a default Benediction, there is no button. The first prayer is never the default Benediction, since it comes last.
4. **[owner-visible] The note sent** (owner answer 2; decision A). Each other prayer is sent alone (the existing body: section, its current text, the readings and sermon text), with exactly one note (`acrossNote`): for the first one sent, `Opens with "{words}" like the {first prayer's label}; open differently.`, `{words}` as the code note quotes them; for each later one, the same instruction with the new openings the batch has produced so far added before the final period: `, not with "X"`, `, not with "X" or "Y"`, `, not with "X", "Y" or "Z"`, oldest first. A new opening is the revised text's first two words after any label, by the same opening rule, as the AI wrote them; one equal (any case) to the shared opening or to one already listed is not added again. The note stays within `ReviseIn`'s 240 characters: when it would pass them, the oldest extra openings are dropped (the instruction alone is at most 2 × 30 characters of words and a label). The card's own notes are not sent, so the revision does one thing (the owner's recommendation in answer 2). The owner sees this only through the result.
5. **[owner-visible] After a prayer is revised.** As after any revision (F1 clarification 5): its text is the AI's (chip "AI draft"), the line "Revised with these notes. Undo" shows (the existing copy, owner answer 4), and its own notes go, since the text they were about was replaced; Undo brings the text back without them. Each card's Undo is independent.
6. **[owner-visible] The confirm** (owner answer 3). It shows when any prayer the button would revise passes `needsRegenerateConfirm` (typed or saved text). It names every prayer it will revise, AI ones included, in service order, joined as "A", "A and B", "A, B and C" (`listLabels`). "Keep my text" (or Escape) sends nothing and returns focus to the button. "Revise text" starts them all and focus stays on the button (now off while they run). The dialog closes, sending nothing, when the prayers it would revise change: which ones (a card switched off or on, another tab's new opening), or any one's text or origin, even an edit that keeps the opening (the confirm keeps `${key}\u0000${origin}\u0000${text}` for each, joined with `\u0001`, when it opens, and compares it at every render); the note or its button goes (fewer than two still share the opening; a new review without that note), or the button goes off (one of them starts being written, a 429's wait begins); focus then goes to the button, or to **Review service** when the button has gone. A new review with the same note and the same prayers leaves it open (it would revise the same prayers).
7. **[owner-visible] One at a time** (decision A). The others are sent one at a time, in service order: the next is sent when the one before has ended. Each goes through the provider's per-card revision (`startRevise`, which `revise(key)` also uses), so each keeps every existing guard and rule: one request per card, the sermon text read through the passage cache (`useSermonLoader`; the review already cached it), the pre-send check after the sermon text loads, the verdict when the answer comes, the 429 handling, the toasts. Every prayer of the batch shows as revising (`revising`) from the start, with its own Cancel. Before each is sent it is checked against its text and origin when the button was pressed; one changed meanwhile is skipped with the existing toast "Kept your edits, so the revised draft for {Label} was not used.", and the batch goes on. A failure other than a 429 shows on that card and the batch goes on; a 429 shows on that card, starts the one shared wait and stops the batch: the rest are not sent and stop showing as revising. Nothing is sent when any of the prayers (the kept one included) is being written (Generate, Regenerate, Try again, queued), revised or waiting in a batch, or while a 429's wait is not over (owner decision 1). There is no batch-level retry. Each revision takes about 10 s, so a batch of seven takes over a minute.
8. **[owner-visible] The button while busy** (owner answer 5). It stays in place but is off (`aria-disabled`, still focusable) while any of those prayers is being written or revised, and during a 429's wait, with the wait shown beside it as beside a card's Revise ("Too many requests — try again in 30 s.", the existing copy). Each card of the batch shows its own "Revising…" and Cancel from the start (no new copy): a Cancel on one not sent yet takes it out of the batch, so it is never sent; a Cancel on the running one stops it, and the next is sent.
9. **Edits while it runs.** The existing per-card rules (F1, slice 4): typing in a revising card, the running one or one waiting its turn, is not possible (it is read-only); another tab's edit, or an edit while the sermon text loads, keeps the member's text with the toast "Kept your edits, so the revised draft for {Label} was not used." (for one waiting its turn, when its turn comes, and it is not sent); switching a card off cancels its revision silently (one waiting its turn leaves the batch); New service cancels all and ends the batch. Each of these counts as "not revised" for the note (clarification 10).
10. **[owner-visible] What happens to the note** (owner answer 6, as recommended; decision A). It goes once every prayer of the batch was revised (its new text put in the card) and, at the batch's end, fewer than two switched-on prayers still share the opening. If any failed, was cancelled, was kept for an edit or was not sent after a 429, the note stays, and the button then offers only the prayers that still share the opening (the revised ones usually no longer do). It also stays when, at the batch's end, two or more switched-on prayers still share the opening, even though every revision succeeded: the AI kept the opening, or an Undo of one already revised brought it back; the button then offers them again (owner answer A, 2026-10-01, replacing the earlier wording of Question 5). The batch also stops, and the note stays, when the kept first prayer no longer opens with the words before the next is sent, or when the next cannot be sent (a 429's wait began meanwhile: that wait shows on it, with the existing "Too many requests" alert; or the AI is writing it: silently). A new review replaces the box as before, and a batch finishing after it never removes a note of the new review, even one with the same id and text: the provider numbers each review it shows (`ServiceReview.generation`, counted in `start()`), the batch keeps the number of the review its note came from, and the note goes only while that review is still the one shown.
11. **Focus and screen readers.** The button is `aria-describedby` the note's sentence (each note's sentence gets an id), so it is read as "Revise the other prayers, Several prayers open with "Gracious God"."; it is a 44 px touch button and wraps under the note at 375 px. Focus stays on it while the prayers revise. When every one was revised the note and its button go together, and focus moves as after a dismiss: to the next note's × in the box (else the one before), or to **Review service** (`REVIEW_BUTTON_ID`) when no note is left. It moves before the cards' own rule (a card whose revision ended takes focus back when focus fell to the page, `SectionCard`), so it does not go to the last card's Undo, and never drops to the page. The wait beside the button is plain text, as beside a card's Revise.
12. **[owner-visible] A failure on a prayer with no notes of its own.** A card revised from "Across the service" may have no notes (it said "Looks good." or had none left). Its revision's failure now shows on the card where the notes go (the same alert as under notes); before, a failure showed only under notes. "Looks good." stays above it. After a failure, that card's own "Revise with these notes" (when it has notes) retries with its own notes, not the opening; only **Revise the other prayers** retries the opening.
13. **Docs** (owner answer 6). T4 adds `docs/manual-verification.md` "Service reviewer" item 10, marked "(owner, after follow-up 2)", and a sentence on that mark; no `##` heading changes, so `test_slice1_docs.py`'s pin is unchanged. R gains a short amendment. The runbook record is T6's records step.

### Risks
- **The AI may keep the opening** despite the note. The note and its button then stay (clarification 10, owner answer A), so the member can try again; the phone check looks at real revisions.
- **Two rules in two languages.** The fixture pins them; a later change to `opening_words` must update the fixture and `notes.ts` together.
- **Cost:** a button press is one AI call per prayer revised (at most 7), each charged to the church's `ai` bucket.
- **One at a time is slower** (decision A): about 10 s per prayer, so two prayers take about 20 s and seven over a minute, all showing "Revising…" meanwhile. In return each prayer is told the new openings before it, so they should differ from each other as well as from the first; the AI may still repeat one. The phone check records whether the new openings differ from each other and the time taken.

## File Structure

**Created**

| Path | Task |
|---|---|
| `backend/tests/fixtures/shared/opening_words.json` (the shared opening rule's cases and `OPENING_NOTE`) | T1 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/tests/test_review_checks.py` | the fixture test | T1 |
| `frontend/src/lib/liturgy/notes.ts` (+ `.test.ts`) | `revisable`, `sharedOpening`, `openingWords`, `acrossTargets`, `acrossNote`, `listLabels`; `ServiceReview.generation` | T1 |
| `frontend/src/lib/liturgy/review.tsx` (+ `review.test.tsx`) | `startRevise` (from `revise`), `reviseAcross` (one at a time), `cancelRevise` for a waiting card, the review's `generation` | T2 |
| `frontend/src/components/builder/liturgy/card-notes.tsx` (+ `review-step.test.tsx`) | the button, its confirm (closing on any listed prayer's change) and wait; focus when the note goes; `NoteList`'s `action` and sentence ids; a noteless card's failure | T3 |
| `docs/manual-verification.md`, `docs/superpowers/specs/2026-09-26-service-reviewer-design.md` | item 10; R's amendment | T4 |
| `docs/ops-runbook.md` | "Reviewer follow-up 2 record" (the records PR, after the merge) | T6 |

**Counts:** 2 created (this plan and the fixture) and 9 modified in the PR, 11 paths. **Untouched:** every backend module, routes, `api/schemas.py`, the OpenAPI files, migrations, `section-card.tsx`, `cards.ts`, `generation.tsx`, `request.ts`, Streamlit.

**Task order and review batch:** T1 → T4, each one commit and a backup push; then one review of the whole batch (the rule's port and fixture; the provider's batch, one at a time; the button, confirm and focus; the docs) with its fixes as `Fix: …` commits; T5 verifies and opens the draft PR on the owner's yes; T6 merges on the owner's yes, runs the phone check and writes the record.

---

### Task 1: The shared opening rule in the frontend (owner answers 1, 2; clarifications 1-4)

**Files:**
- Create: `backend/tests/fixtures/shared/opening_words.json`
- Modify: `backend/tests/test_review_checks.py`, `frontend/src/lib/liturgy/notes.ts`, `frontend/src/lib/liturgy/notes.test.ts`

**Interfaces:**
- Produces: `revisable(card)`, `sharedOpening(note) -> string | null`, `openingWords(text) -> string[]`, `AcrossTargets = { words; first; others }`, `acrossTargets(draft, words) -> AcrossTargets | null`, `acrossNote(words, firstLabel, avoid = [])`, `listLabels(labels)`, `ServiceReview.generation?` (set by T2's provider); `canRevise` now uses `revisable` (same result).

- [ ] **Step 1 (agent): The fixture and the backend pin**

**Create `backend/tests/fixtures/shared/opening_words.json`:**

````json
{
  "_about": "The rule backend review_checks.opening_words and check_openings use, and frontend lib/liturgy/notes.ts (openingWords, sharedOpening) mirrors for Revise the other prayers (reviewer follow-up 2). Both test suites read this file.",
  "opening_note": "Several prayers open with \"{words}\".",
  "cases": [
    {"text": "Gracious God, we gather.", "words": ["Gracious", "God"]},
    {"text": "Leader: gracious god! Hear us.", "words": ["gracious", "god"]},
    {"text": "  PEOPLE :  Holy One, come.", "words": ["Holy", "One"]},
    {"text": "Leader: People: Come now.", "words": ["People", "Come"]},
    {"text": "Leader:Gracious God", "words": ["Gracious", "God"]},
    {"text": " Leader:\u0085Gracious God", "words": ["Gracious", "God"]},
    {"text": "﻿Leader: Holy One", "words": ["Leader", "Holy"]},
    {"text": "We\u2019re here, O God.", "words": ["We\u2019re", "here"]},
    {"text": "O'er all the earth", "words": ["O'er", "all"]},
    {"text": "snake_case words", "words": ["snake", "case"]},
    {"text": "Se\u00f1or Dios, \u00f3yenos.", "words": ["Se\u00f1or", "Dios"]},
    {"text": "Cafe\u0301 God", "words": ["Cafe", "God"]},
    {"text": "1 Lord, 2 God", "words": ["1", "Lord"]},
    {"text": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb Gracious God, hear.", "words": ["Gracious", "God"]},
    {"text": "God", "words": ["God"]},
    {"text": "  ", "words": []}
  ]
}
````

**Append to `backend/tests/test_review_checks.py`:**

````python

def test_opening_words_and_the_opening_note_match_the_shared_fixture():
    """The frontend finds the prayers a "Several prayers open with" note is about by the same rule, and reads the
    note's words back from its text (reviewer follow-up 2); both suites read this fixture."""
    import json
    from pathlib import Path

    import review_checks

    fixture = json.loads((Path(__file__).resolve().parent / "fixtures" / "shared" / "opening_words.json")
                         .read_text(encoding="utf-8"))
    assert review_checks.OPENING_NOTE == fixture["opening_note"]
    for case in fixture["cases"]:
        assert review_checks.opening_words(case["text"]) == case["words"], case["text"]
````


```bash
.venv/bin/python -m pytest -q backend/tests/test_review_checks.py 2>&1 | tail -1
```

**Expected:** `8 passed in <t>s` at once: the test pins the backend's existing rule and note, which the frontend copies next.

- [ ] **Step 2 (agent): Write the failing frontend tests**

**In `frontend/src/lib/liturgy/notes.test.ts`, replace:**

````ts
 */
import { describe, expect, it } from "vitest";
````

**with:**

````ts
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";
````

**In `frontend/src/lib/liturgy/notes.test.ts`, replace:**

````ts
import { applyGenerated, clearCard, editCardText, restoreChurchDefault } from "./cards";
import { applyReview, canRevise, captureReview, dismissNote, forgetCard, noteCount, pruneReview } from "./notes";
````

**with:**

````ts
import { applyGenerated, clearCard, editCardText, restoreChurchDefault } from "./cards";
import {
  acrossNote,
  acrossTargets,
  applyReview,
  canRevise,
  captureReview,
  dismissNote,
  forgetCard,
  listLabels,
  noteCount,
  openingWords,
  pruneReview,
  sharedOpening,
} from "./notes";
````

**Append to `frontend/src/lib/liturgy/notes.test.ts`:**

````ts

describe("Revise the other prayers (reviewer follow-up 2)", () => {
  type Fixture = { opening_note: string; cases: { text: string; words: string[] }[] };
  const fixture = JSON.parse(
    readFileSync(new URL("../../../../backend/tests/fixtures/shared/opening_words.json", import.meta.url), "utf-8"),
  ) as Fixture;

  it("reads openings and the shared-opening note as the backend does (the shared fixture)", () => {
    for (const { text, words } of fixture.cases) expect(openingWords(text), text).toEqual(words);
    const text = fixture.opening_note.replace("{words}", "Gracious God");
    expect(sharedOpening(reviewNote("repetition", text, "code"))).toBe("Gracious God");
    expect(sharedOpening(reviewNote("repetition", text))).toBeNull(); // an AI note: no button
    expect(sharedOpening(reviewNote("rules", text, "code"))).toBeNull();
    expect(sharedOpening(reviewNote("repetition", "Two prayers say journey.", "code"))).toBeNull();
    expect(acrossNote("Gracious God", "Call to Worship")).toBe('Opens with "Gracious God" like the Call to Worship; open differently.');
    // One at a time (owner decision A): each later note also names the openings the batch has produced so far.
    expect(acrossNote("Gracious God", "Call to Worship", ["Holy One"])).toBe(
      'Opens with "Gracious God" like the Call to Worship; open differently, not with "Holy One".',
    );
    expect(acrossNote("Gracious God", "Call to Worship", ["Holy One", "Loving God"])).toBe(
      'Opens with "Gracious God" like the Call to Worship; open differently, not with "Holy One" or "Loving God".',
    );
    expect(acrossNote("Gracious God", "Call to Worship", ["Holy One", "Loving God", "Merciful God"])).toBe(
      'Opens with "Gracious God" like the Call to Worship; open differently, not with "Holy One", "Loving God" or "Merciful God".',
    );
    // At most 240 characters (ReviseIn): the oldest extra openings go first.
    const long = ["a", "b", "c", "d", "e", "f"].map((c) => `${c.repeat(30)} ${c.repeat(30)}`);
    const capped = acrossNote("Gracious God", "Call to Worship", long);
    expect([...capped].length).toBeLessThanOrEqual(240);
    expect(capped).toBe(
      `Opens with "Gracious God" like the Call to Worship; open differently, not with "${long[4]}" or "${long[5]}".`,
    );
    expect([[], ["A"], ["A", "B"], ["A", "B", "C"]].map(listLabels)).toEqual(["", "A", "A and B", "A, B and C"]);
  });

  it("finds the prayers as the draft is now: the first kept, a default Benediction kept, switched-off cards left out", () => {
    let d = withText(testDraft(), "call_to_worship", "Leader: Gracious God, we gather.", "typed");
    d = withText(d, "opening_prayer", "gracious god! Hear us.", "ai");
    d = withText(d, "prayer_of_confession", "Gracious God, we confess.", "archive");
    d = { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, prayer_of_confession: { ...d.liturgy.cards.prayer_of_confession, enabled: false } } } };
    d = withText(d, "assurance", "People: Gracious   God, you forgive.", "archive");
    d = withText(d, "benediction", "Gracious God, go with us.", "default");
    expect(acrossTargets(d, "Gracious God")).toEqual({ words: "Gracious God", first: "call_to_worship", others: ["opening_prayer", "assurance"] });
    expect(acrossTargets(d, "Holy One")).toBeNull();
    // Only the first and a Benediction following the default still share it: nothing to revise.
    const left = withText(withText(d, "opening_prayer", "Holy One, hear us.", "ai"), "assurance", "", "empty");
    expect(acrossTargets(left, "Gracious God")).toBeNull();
    // Once edited, the Benediction is typed text and is revised; a lone opening is no shared one.
    expect(acrossTargets(withText(left, "benediction", "Gracious God, go with us. Amen.", "typed"), "gracious god")?.others).toEqual(["benediction"]);
    expect(acrossTargets(withText(left, "benediction", "Go in peace.", "typed"), "Gracious God")).toBeNull();
  });
});
````


- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/notes.test.ts 2>&1 | grep -E "^ +× |Tests ")
```

**Expected:** two failures, `   × Revise the other prayers (reviewer follow-up 2) > reads openings and the shared-opening note as the backend does (the shared fixture)` and `   × Revise the other prayers (reviewer follow-up 2) > finds the prayers as the draft is now: the first kept, a default Benediction kept, switched-off cards left out` (the functions are not there yet), then `      Tests  2 failed | 5 passed (7)`.

- [ ] **Step 4 (agent): The rule, the targets and the note**

**In `frontend/src/lib/liturgy/notes.ts`, replace:**

````ts
 *   (`CardNotes`).
 */
import type { AiStatus, ReviewNote, ReviewResult } from "@/lib/api/types";
import type { DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";
````

**with:**

````ts
 *   (`CardNotes`).
 * - "Revise the other prayers" (reviewer follow-up 2, owner answers of
 *   2026-10-01) shows only on the code note "Several prayers open with
 *   "…"." (`sharedOpening`). The prayers it is about are found again from the
 *   draft by the backend's rule (`openingWords`, the shared fixture
 *   `opening_words.json`): every switched-on card with text that opens with
 *   those words, any case. The first in service order is kept, and so is a
 *   Benediction following the church default; the others are revised
 *   (`acrossTargets`), each with one note (`acrossNote`).
 */
import type { AiStatus, ReviewNote, ReviewResult } from "@/lib/api/types";
import type { DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";

import { reviewTargets } from "./request";
````

**In `frontend/src/lib/liturgy/notes.ts`, replace:**

````ts
  service: Note[];
  aiStatus: AiStatus;
};
````

**with:**

````ts
  service: Note[];
  aiStatus: AiStatus;
  /** Which review this is: the provider numbers each one it shows, so a late revision never touches a newer one's notes. */
  generation?: number;
};
````

**In `frontend/src/lib/liturgy/notes.ts`, replace:**

````ts

/** "Revise with these notes": a card with text and a note left, written by the AI, typed or from a saved service. */
export function canRevise(card: LiturgyCard, review: CardReview | undefined): boolean {
  const origin = card.origin === "ai" || card.origin === "typed" || card.origin === "archive";
  return origin && card.text.trim() !== "" && review !== undefined && review.notes.length > 0;
}
````

**with:**

````ts

/** A card Revise may rewrite: text written by the AI, typed or from a saved service; never the church default. */
export function revisable(card: LiturgyCard): boolean {
  const origin = card.origin === "ai" || card.origin === "typed" || card.origin === "archive";
  return origin && card.text.trim() !== "";
}

/** "Revise with these notes": a card with text and a note left, written by the AI, typed or from a saved service. */
export function canRevise(card: LiturgyCard, review: CardReview | undefined): boolean {
  return revisable(card) && review !== undefined && review.notes.length > 0;
}

/** The code note across the service that names a shared opening (backend `review_checks.OPENING_NOTE`). */
const OPENING_NOTE = /^Several prayers open with "(.+)"\.$/;

/** The words a "Several prayers open with "…"." code note names; null for any other note (an AI note included). */
export function sharedOpening(note: ReviewNote): string | null {
  if (note.source !== "code" || note.tag !== "repetition") return null;
  return OPENING_NOTE.exec(note.text)?.[1] ?? null;
}

// Python's `\s` (str patterns): JavaScript's `\s` adds U+FEFF and lacks U+001C-U+001F and U+0085, so it is spelled out.
const PY_SPACE = "[\\t\\n\\v\\f\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]";
const LABEL = new RegExp(`^${PY_SPACE}*(?:leader|people)${PY_SPACE}*:${PY_SPACE}*`, "i");
// Backend `review_checks._WORD`: a run of letters and digits, apostrophe-joined parts included.
const WORD = /(?<![\p{L}\p{N}])[\p{L}\p{N}]+(?:['’][\p{L}\p{N}]+)*(?![\p{L}\p{N}])/gu;
const MAX_WORD_CHARS = 30;

/** Backend `review_checks.opening_words`: the first two words after any leading "Leader:" or "People:" label. */
export function openingWords(text: string): string[] {
  const words = text.replace(LABEL, "").match(WORD) ?? [];
  return words.filter((w) => [...w].length <= MAX_WORD_CHARS).slice(0, 2);
}

export type AcrossTargets = { words: string; first: SectionKey; others: SectionKey[] };

/**
 * The prayers a shared-opening note is about, as the draft is now: the
 * switched-on cards with text (the review's own rule) whose first two words
 * are `words`, any case, in service order. `first` is kept; `others` are the
 * rest Revise may rewrite (a Benediction following the church default is
 * kept too). Null when fewer than two still share the opening or none can be
 * revised.
 */
export function acrossTargets(d: DraftV1, words: string): AcrossTargets | null {
  const key = words.toLowerCase();
  const sharing = reviewTargets(d).filter((k) => {
    const opening = openingWords(d.liturgy.cards[k].text);
    return opening.length === 2 && opening.join(" ").toLowerCase() === key;
  });
  if (sharing.length < 2) return null;
  const [first, ...rest] = sharing;
  const others = rest.filter((k) => revisable(d.liturgy.cards[k]));
  return others.length === 0 ? null : { words, first, others };
}

/** `ReviseIn`'s limit on one note, in characters. */
const MAX_NOTE_CHARS = 240;

/**
 * The one note each other prayer is revised with (owner answer 2 of
 * 2026-10-01). The prayers go one at a time (owner decision A), so each
 * later note also names `avoid`, the new openings the batch has produced so
 * far, oldest first: `…; open differently, not with "X" or "Y".` The oldest go
 * first when the note would pass 240 characters.
 */
export function acrossNote(words: string, firstLabel: string, avoid: readonly string[] = []): string {
  const base = `Opens with "${words}" like the ${firstLabel}; open differently`;
  for (let drop = 0; drop < avoid.length; drop += 1) {
    const note = `${base}, not with ${joined(avoid.slice(drop).map((w) => `"${w}"`), "or")}.`;
    if ([...note].length <= MAX_NOTE_CHARS) return note;
  }
  return `${base}.`;
}

function joined(items: readonly string[], last: "and" | "or"): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} ${last} ${items[items.length - 1]}`;
}

/** "A", "A and B", "A, B and C". */
export function listLabels(labels: string[]): string {
  return joined(labels, "and");
}
````


- [ ] **Step 5 (agent): Run the file three times, the suites, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/lib/liturgy/notes.test.ts 2>&1 | grep -E "^ +× |Tests "); done
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `      Tests  7 passed (7)` three times; ` Test Files  78 passed (78)` and `      Tests  583 passed (583)`; `typecheck 0`, `lint 0`; `1223 passed, 11 skipped in <t>s`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/tests/fixtures/shared/opening_words.json backend/tests/test_review_checks.py frontend/src/lib/liturgy/notes.ts frontend/src/lib/liturgy/notes.test.ts
git commit -q -m "Liturgy step: find the prayers a shared-opening note is about (follow-up 2; owner answers 1, 2)" -m "notes.ts ports the backend's opening rule (the first two words after any
Leader:/People: label, any case) and reads the words back from the code
note Several prayers open with. acrossTargets finds, as the draft is now,
the switched-on prayers that share them: the first is kept, and so is a
Benediction following the church default; the others can be revised.
A shared fixture pins both languages to the same cases." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 1: backend **1223 passed, 11 skipped**; frontend **583 in 78**.

### Task 2: Revise the others, one at a time, through the existing per-card path (owner answers 2, 4; decision A; clarifications 4, 5, 7-10)

**Files:**
- Modify: `frontend/src/lib/liturgy/review.tsx`, `frontend/src/lib/liturgy/review.test.tsx`

**Interfaces:**
- Consumes: T1's `revisable`, `sharedOpening`, `openingWords`, `acrossTargets`, `acrossNote`, `ServiceReview.generation`.
- Produces: `LiturgyReview.reviseAcross(noteId: string) => boolean` (true when the first revision of the batch started; every prayer of the batch is in `revising` from the start). `cancelRevise(key)` also takes a card waiting in a batch out of it. Each review the provider shows carries `generation`. `revise(key)` is unchanged for its callers; inside, it is `startRevise(key)`.

- [ ] **Step 1 (agent): Write the failing test**

**Append to `frontend/src/lib/liturgy/review.test.tsx`:**

````tsx

describe("Revise the other prayers (reviewer follow-up 2)", () => {
  const OPENING = 'Several prayers open with "Gracious God".';
  const ACROSS = 'Opens with "Gracious God" like the Call to Worship; open differently.';

  /** Each prayer's revision waits for its own release; `sent` lists the sections in the order they were sent. */
  function gated(answers: Partial<Record<SectionKey, string>>) {
    const gates = new Map<string, () => void>();
    const route = reviseRoute(async (body) => {
      await new Promise<void>((resolve) => gates.set(body.section, resolve));
      return { text: answers[body.section as SectionKey] ?? "" };
    });
    return { route, release: (key: SectionKey) => gates.get(key)?.() };
  }

  function threeShare(): DraftV1 {
    let d = card(seeded(), "call_to_worship", "Leader: Gracious God, come.", "typed");
    d = card(d, "prayer_of_confession", "Gracious God, we confess.", "archive");
    return card(d, "assurance", "Gracious God, you forgive.", "ai");
  }

  const ANSWER_ACROSS = reviewResult({
    cards: [{ section: "opening_prayer", notes: [reviewNote("read_aloud", "The prayer runs long.")] }],
    service_notes: [reviewNote("repetition", OPENING, "code"), reviewNote("repetition", "Two prayers say journey.")],
  });

  function sentNotes(api: ReturnType<typeof renderProvider>) {
    return api.requests.filter((r) => r.path === "/liturgy/revise").map((r) => r.body as ReviseBody).map((b) => [b.section, b.text, b.notes]);
  }

  it("revises every prayer but the first one at a time, each told the openings so far; the note goes once all were revised", async () => {
    const { route, release } = gated({
      opening_prayer: "Holy One, hear us.",
      prayer_of_confession: "Merciful God, we confess.",
      assurance: "Leader: Loving God, you forgive.",
    });
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER_ACROSS), "POST /liturgy/revise": route }, churchProfile(), threeShare());
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 3 notes.")).toBeInTheDocument();
    const started: (boolean | undefined)[] = [];
    act(() => {
      started.push(handle.current?.reviseAcross("service-1")); // an AI note: the app does not know the prayers
      started.push(handle.current?.reviseAcross("service-0"));
      started.push(handle.current?.reviseAcross("service-0")); // already running
    });
    expect(started).toEqual([false, true, false]);
    // One at a time, in service order; every one shows as revising from the start.
    await waitFor(() => expect(sentNotes(api)).toHaveLength(1));
    expect(handle.current?.revising).toEqual({ opening_prayer: true, prayer_of_confession: true, assurance: true });
    expect(screen.getByText(`status: ok; service: ${OPENING} | Two prayers say journey.`)).toBeInTheDocument();
    act(() => release("opening_prayer"));
    expect(await screen.findByText("opening_prayer: Holy One, hear us. [ai] notes none; revising no; error none; undo revised")).toBeInTheDocument();
    await waitFor(() => expect(sentNotes(api)).toHaveLength(2));
    act(() => release("prayer_of_confession"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(3));
    expect(sentNotes(api)).toEqual([
      ["opening_prayer", "Gracious God, as we journey, hear us.", [ACROSS]],
      ["prayer_of_confession", "Gracious God, we confess.", [`${ACROSS.slice(0, -1)}, not with "Holy One".`]],
      ["assurance", "Gracious God, you forgive.", [`${ACROSS.slice(0, -1)}, not with "Holy One" or "Merciful God".`]],
    ]);
    expect(screen.getByText(`status: ok; service: ${OPENING} | Two prayers say journey.`)).toBeInTheDocument();
    act(() => release("assurance"));
    expect(await screen.findByText("status: ok; service: Two prayers say journey.")).toBeInTheDocument();
    expect(handle.current?.revising).toEqual({});
    expect(screen.getByText(/^call_to_worship: Leader: Gracious God, come\. \[typed\] notes none; revising no; error none; undo none$/)).toBeInTheDocument();
    expect(draftHandle.current?.peek().liturgy.cards.prayer_of_confession).toEqual({ enabled: true, text: "Merciful God, we confess.", origin: "ai" });
    expect(draftHandle.current?.peek().liturgy.cards.assurance).toEqual({ enabled: true, text: "Leader: Loving God, you forgive.", origin: "ai" });
  });

  it("never removes the note of a newer review, even one with the same note", async () => {
    const { route, release } = gated({ opening_prayer: "Holy One, hear us.", prayer_of_confession: "Merciful God, we confess.", assurance: "Loving God, you forgive." });
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER_ACROSS), "POST /liturgy/revise": route }, churchProfile(), threeShare());
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 3 notes.")).toBeInTheDocument();
    act(() => void handle.current?.reviseAcross("service-0"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(1));
    act(() => release("opening_prayer"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(2));
    act(() => release("prayer_of_confession"));
    await waitFor(() => expect(sentNotes(api)).toHaveLength(3));
    // A new review while the last one runs: it brings the same note (same id, same words).
    act(() => handle.current?.start());
    await waitFor(() => expect(api.requests.filter((r) => r.path === "/liturgy/review")).toHaveLength(2));
    expect(await screen.findByText("running: no")).toBeInTheDocument();
    act(() => release("assurance"));
    expect(await screen.findByText(/^opening_prayer: Holy One, hear us\. \[ai\]/)).toBeInTheDocument();
    await waitFor(() => expect(handle.current?.revising).toEqual({}));
    expect(draftHandle.current?.peek().liturgy.cards.assurance.text).toBe("Loving God, you forgive.");
    expect(screen.getByText(`status: ok; service: ${OPENING} | Two prayers say journey.`)).toBeInTheDocument();
  });
});
````


- [ ] **Step 2 (agent): Run it and see it fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/review.test.tsx 2>&1 | grep -E "^ +× |Tests ")
```

**Expected:** two failures, `   × Revise the other prayers (reviewer follow-up 2) > revises every prayer but the first one at a time, each told the openings so far; the note goes once all were revised` and `   × Revise the other prayers (reviewer follow-up 2) > never removes the note of a newer review, even one with the same note` (`reviseAcross` is not there yet), then `      Tests  2 failed | 6 passed (8)`.

- [ ] **Step 3 (agent): `startRevise` and `reviseAcross`**

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
 *   changes and a toast says why. A failure shows on the card's notes.
 * - `announcement`: the polite line read out when a review ends.
````

**with:**

````tsx
 *   changes and a toast says why. A failure shows on the card's notes.
 * - `reviseAcross(noteId)` (reviewer follow-up 2): "Revise the other
 *   prayers" on a "Several prayers open with "…"." note. The prayers are
 *   found again from the draft (`acrossTargets`); nothing is sent while any
 *   of them is being written, revised or waiting in a batch, or while a
 *   429's wait is not over. The others are revised one at a time, in service
 *   order (owner decision A), each through the same path as `revise` (its
 *   own stale rule, failure and Undo), with the one note `acrossNote`
 *   instead of its own notes; each later note also names the new openings
 *   the batch has produced so far. Every one of them shows as revising from
 *   the start, with its own Cancel: a Cancel on one not sent yet skips it,
 *   on the running one moves to the next. One edited meanwhile (its text or
 *   origin no longer what it was when the button was pressed), or whose
 *   revision failed, is skipped and the batch goes on; a 429 stops it (the
 *   rest are not sent). Each success drops that card's own notes, as any
 *   revision does. The note goes once every one of them was revised, and
 *   only while the review it came from is still the one shown
 *   (`generation`); otherwise it stays.
 * - `announcement`: the polite line read out when a review ends.
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
import {
  applyReview,
````

**with:**

````tsx
import {
  acrossNote,
  acrossTargets,
  applyReview,
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
  noteCount,
  pruneReview,
  type ServiceReview,
````

**with:**

````tsx
  noteCount,
  openingWords,
  pruneReview,
  revisable,
  sharedOpening,
  type ServiceReview,
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
  revise: (key: SectionKey) => boolean;
  cancelRevise: (key: SectionKey) => void;
````

**with:**

````tsx
  revise: (key: SectionKey) => boolean;
  /** "Revise the other prayers" on a shared-opening note, one at a time; true when the first revision started. */
  reviseAcross: (noteId: string) => boolean;
  /** Stops a card's revision, or takes it out of a "Revise the other prayers" batch before it is sent. */
  cancelRevise: (key: SectionKey) => void;
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
type ReviseVerdict = "apply" | "service_changed" | "edited";
````

**with:**

````tsx
type ReviseVerdict = "apply" | "service_changed" | "edited";
/** How one revision ended: the text put in the card (null when none was), and whether it was a 429. */
type ReviseEnd = { text: string | null; limited: boolean };
type StartRevise = (key: SectionKey, instead?: string[], onDone?: (end: ReviseEnd) => void) => boolean;

/** "Revise the other prayers" while it runs (owner decision A): one prayer at a time, in service order. */
type AcrossBatch = {
  noteId: string;
  /** The review the note came from (`ServiceReview.generation`). */
  generation: number | undefined;
  words: string;
  firstLabel: string;
  /** The prayers not sent yet, each as it was when the button was pressed. */
  queue: { key: SectionKey; sent: Sent }[];
  /** The new openings so far, oldest first. */
  openings: string[];
  started: number;
  /** Every one so far was revised. */
  all: boolean;
};

function inBatch(batches: Set<AcrossBatch>, key: SectionKey): boolean {
  for (const batch of batches) if (batch.queue.some((q) => q.key === key)) return true;
  return false;
}

/** A Cancel on a prayer not sent yet: it leaves its batch, which then keeps the note. */
function leaveBatch(batches: Set<AcrossBatch>, key: SectionKey): void {
  for (const batch of batches) {
    const at = batch.queue.findIndex((q) => q.key === key);
    if (at < 0) continue;
    batch.queue.splice(at, 1);
    batch.all = false;
  }
}
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
  const service = useRef(draft.created_at);
````

**with:**

````tsx
  const service = useRef(draft.created_at);
  const batches = useRef(new Set<AcrossBatch>());
  const startReviseRef = useRef<StartRevise | null>(null);
  /** Numbers each review shown (`ServiceReview.generation`). */
  const generation = useRef(0);
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
    const waits = revisions.current;
    return () => {
````

**with:**

````tsx
    const waits = revisions.current;
    const queued = batches.current;
    return () => {
      queued.clear();
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
    active.current = null;
    for (const controller of revisions.current.values()) controller.abort();
````

**with:**

````tsx
    active.current = null;
    batches.current.clear();
    for (const controller of revisions.current.values()) controller.abort();
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
        setReview(next);
````

**with:**

````tsx
        generation.current += 1;
        setReview(next === null ? null : { ...next, generation: generation.current });
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx

  const revise = useCallback(
    (key: SectionKey) => {
      if (revisions.current.has(key)) return false;
      const asked = peek();
      const card = asked.liturgy.cards[key];
      const notes = reviewRef.current?.cards[key];
      if (!canRevise(card, notes) || notes === undefined) return false;
      // The AI is writing this card (Generate, Regenerate, Try again): one request at a time per card.
````

**with:**

````tsx

  // One card's revision: with its remaining notes (`revise`), or with `instead` (`reviseAcross`). `onDone` hears
  // how it ended. A card waiting in a "Revise the other prayers" batch is left to the batch.
  const startRevise = useCallback<StartRevise>(
    (key, instead, onDone) => {
      if (revisions.current.has(key) || inBatch(batches.current, key)) return false;
      const asked = peek();
      const card = asked.liturgy.cards[key];
      const own = reviewRef.current?.cards[key];
      const notes = instead ?? (canRevise(card, own) && own !== undefined ? own.notes.map((n) => n.text) : []);
      if (!revisable(card) || notes.length === 0) return false;
      // The AI is writing this card (Generate, Regenerate, Try again): one request at a time per card.
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
      setReviseErrors((current) => without(current, key));
      void (async () => {
````

**with:**

````tsx
      setReviseErrors((current) => without(current, key));
      const end: ReviseEnd = { text: null, limited: false };
      void (async () => {
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
          }
          const body = buildReviseRequest(asked, key, notes.notes.map((n) => n.text), sermon);
          const text = await reviseSection(api.church, body, controller.signal);
````

**with:**

````tsx
          }
          const body = buildReviseRequest(asked, key, notes, sermon);
          const text = await reviseSection(api.church, body, controller.signal);
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
            setReview((current) => forgetCard(current, key)); // the notes were addressed
          }
````

**with:**

````tsx
            setReview((current) => forgetCard(current, key)); // the notes were addressed
            end.text = text;
          }
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
          if (retryAt !== undefined) noteRateLimit(retryAt);
````

**with:**

````tsx
          if (retryAt !== undefined) {
            noteRateLimit(retryAt);
            end.limited = true;
          }
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
          }
        }
      })();
      return true;
    },
    [api, handleFailure, loadSermon, noteRateLimit, peek, rateLimitedUntil, runs, setUndo, update],
  );
````

**with:**

````tsx
          }
          if (mounted.current) onDone?.(end);
        }
      })();
      return true;
    },
    [api, handleFailure, loadSermon, noteRateLimit, peek, rateLimitedUntil, runs, setUndo, update],
  );

  // A batch moves on from a revision's end, after this render: it starts the next one with the latest guards.
  useEffect(() => {
    startReviseRef.current = startRevise;
  }, [startRevise]);

  const revise = useCallback((key: SectionKey) => startRevise(key), [startRevise]);

  // Sends a batch's next prayer, skipping one edited meanwhile or not revisable now; when none is left, the note goes
  // if every one was revised and its review is still the one shown.
  const runAcross = useCallback(
    (batch: AcrossBatch) => {
      const step = (): void => {
        if (!batches.current.has(batch)) return; // a new service, or the provider went
        for (let next = batch.queue.shift(); next !== undefined; next = batch.queue.shift()) {
          const { key, sent } = next;
          const verdict = reviseVerdict(peek(), key, sent);
          if (verdict === "apply") {
            const ask = acrossNote(batch.words, batch.firstLabel, batch.openings);
            const started = startReviseRef.current?.(key, [ask], (end) => {
              if (!batches.current.has(batch)) return;
              if (end.text === null) batch.all = false;
              else {
                const opening = openingWords(end.text).join(" ");
                const seen = [batch.words, ...batch.openings].some((w) => w.toLowerCase() === opening.toLowerCase());
                if (opening !== "" && !seen) batch.openings.push(opening);
              }
              if (end.limited) {
                // A 429: the rest are not sent (the wait shows on that card and beside the button).
                const left = batch.queue.map((q) => q.key);
                batch.queue = [];
                batch.all = false;
                setRevising((current) => left.reduce((acc, k) => without(acc, k), current));
              }
              step();
            });
            if (started === true) {
              batch.started += 1;
              return;
            }
          } else reviseToast(key, verdict);
          batch.all = false;
          setRevising((current) => without(current, key));
        }
        batches.current.delete(batch);
        if (!batch.all) return;
        // Every one was revised: the note goes, unless a newer review has replaced it meanwhile.
        setReview((current) =>
          current !== null && current.generation === batch.generation && current.service.some((n) => n.id === batch.noteId)
            ? dismissNote(current, "service", batch.noteId)
            : current,
        );
      };
      step();
    },
    [peek],
  );

  const reviseAcross = useCallback(
    (noteId: string) => {
      const current = reviewRef.current;
      const note = current?.service.find((n) => n.id === noteId);
      const words = note === undefined ? null : sharedOpening(note);
      if (current === null || note === undefined || words === null) return false;
      const asked = peek();
      const targets = acrossTargets(asked, words);
      if (targets === null) return false;
      // Any of these prayers being written, revised or waiting in a batch: nothing is sent (the button is off).
      const busy = (key: SectionKey) => runs[key] !== undefined || revisions.current.has(key) || inBatch(batches.current, key);
      if ([targets.first, ...targets.others].some(busy)) return false;
      if (rateLimitedUntil !== null && Date.now() < rateLimitedUntil) return false;
      const batch: AcrossBatch = {
        noteId: note.id,
        generation: current.generation,
        words,
        firstLabel: SECTION_LABELS[targets.first],
        queue: targets.others.map((key) => {
          const card = asked.liturgy.cards[key];
          return { key, sent: { createdAt: asked.created_at, text: card.text, origin: card.origin } };
        }),
        openings: [],
        started: 0,
        all: true,
      };
      batches.current.add(batch);
      // Every one shows as revising, with its own Cancel, from the start.
      setRevising((now) => {
        const next = { ...now };
        for (const key of targets.others) next[key] = true;
        return next;
      });
      runAcross(batch);
      return batch.started > 0;
    },
    [peek, rateLimitedUntil, runAcross, runs],
  );
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
  const cancelRevise = useCallback((key: SectionKey) => {
    revisions.current.get(key)?.abort();
````

**with:**

````tsx
  const cancelRevise = useCallback((key: SectionKey) => {
    // Not sent yet: it leaves its batch. Running: its batch moves on to the next.
    leaveBatch(batches.current, key);
    revisions.current.get(key)?.abort();
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
  const value = useMemo<LiturgyReview>(
    () => ({ review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, cancelRevise }),
    [review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, cancelRevise],
  );
````

**with:**

````tsx
  const value = useMemo<LiturgyReview>(
    () => ({ review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, reviseAcross, cancelRevise }),
    [review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, reviseAcross, cancelRevise],
  );
````


- [ ] **Step 4 (agent): Run the file three times, the suite, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/lib/liturgy/review.test.tsx 2>&1 | grep -E "^ +× |Tests "); done
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `      Tests  8 passed (8)` three times; ` Test Files  78 passed (78)` and `      Tests  585 passed (585)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/review.tsx frontend/src/lib/liturgy/review.test.tsx
git commit -q -m "Liturgy step: revise the other prayers that share an opening, one at a time (follow-up 2; owner answers 2, 4, decision A)" -m "reviseAcross(noteId) sends each prayer after the first that shares the
note's opening, one at a time in service order, through the same per-card
revision as Revise with these notes (its guards, stale rule, failure and
Undo), with the one note Opens with ... like the {first}; open
differently, naming the new openings so far. All show as revising from
the start; Cancel skips a waiting one or moves on; an edited or failed one
is skipped; a 429 stops the rest. The note goes once every one was
revised, and only while its review is still the one shown." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 2: backend **1223 passed, 11 skipped**; frontend **585 in 78**.

### Task 3: The button, its confirm and the wait (owner answers 1, 3, 5; decision A; clarifications 1, 6, 8, 11, 12)

**Files:**
- Modify: `frontend/src/components/builder/liturgy/card-notes.tsx`, `frontend/src/components/builder/liturgy/review-step.test.tsx`

**Interfaces:**
- Consumes: T1's `sharedOpening`, `acrossTargets`, `listLabels`; T2's `reviseAcross`.
- Produces: `NoteList`'s optional `action(note)` row and each note's sentence id `note-{id}-text`; the button's id `{noteId}-revise-others`.

- [ ] **Step 1 (agent): Write the failing tests**

**Append to `frontend/src/components/builder/liturgy/review-step.test.tsx`:**

````tsx

describe("Revise the other prayers (reviewer follow-up 2)", () => {
  const OPENING = 'Several prayers open with "Gracious God".';
  const ACROSS = 'Opens with "Gracious God" like the Call to Worship; open differently.';

  function across() {
    return screen.getByRole("region", { name: "Across the service" });
  }

  function revisions(api: ReturnType<typeof renderStep>["api"]) {
    return api.requests.filter((r) => r.path === "/liturgy/revise").map((r) => r.body as ReviseBody);
  }

  /** Each prayer's revision waits for its own release. */
  function gated(answers: Partial<Record<SectionKey, string>>) {
    const gates = new Map<string, () => void>();
    const route = reviseRoute(async (body) => {
      await new Promise<void>((resolve) => gates.set(body.section, resolve));
      return { text: answers[body.section as SectionKey] ?? "" };
    });
    return { route, release: (key: SectionKey) => gates.get(key)?.() };
  }

  function otherTab(d: DraftV1, at: string) {
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...d, updated_at: at }) }));
    });
  }

  it("shows only on the code note about a shared opening and revises every prayer but the first one at a time, each with its own Revising…, Cancel and Undo", async () => {
    const { route, release } = gated({ opening_prayer: "Holy One, hear us.", assurance: "Leader: Through Christ you are forgiven." });
    let d = withCard(seeded(), "call_to_worship", "Leader: Gracious God, we gather.", "typed");
    d = withCard(d, "assurance", "gracious god, in Christ we are forgiven.", "ai");
    const answer = reviewResult({ cards: ANSWER.cards, service_notes: [...ANSWER.service_notes, reviewNote("repetition", "Two prayers say journey.")] });
    const { user, api } = renderStep(d, { "POST /liturgy/review": reviewRoute(() => answer), "POST /liturgy/revise": route });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await screen.findByText("Review finished. 7 notes.");
    const button = within(across()).getByRole("button", { name: "Revise the other prayers" }); // one: not on the AI note
    expect(button).toHaveAccessibleDescription(OPENING);
    await user.click(button);
    expect(screen.queryByRole("alertdialog")).toBeNull(); // only AI text is revised: no confirm
    expect(button).toHaveAttribute("aria-disabled", "true");
    expect(button).toHaveFocus();
    // One at a time: the Opening Prayer is sent; both show Revising… with their own Cancel from the start.
    await waitFor(() => expect(revisions(api)).toHaveLength(1));
    expect(within(card("Opening Prayer")).getByRole("button", { name: "Cancel revising Opening Prayer" })).toBeInTheDocument();
    expect(within(card("Assurance of Pardon")).getByRole("button", { name: "Cancel revising Assurance of Pardon" })).toBeInTheDocument();
    act(() => release("opening_prayer"));
    expect(await within(card("Opening Prayer")).findByText("Revised with these notes.")).toBeInTheDocument();
    await waitFor(() => expect(revisions(api)).toHaveLength(2));
    expect(revisions(api).map((b) => [b.section, b.notes])).toEqual([
      ["opening_prayer", [ACROSS]],
      ["assurance", [`${ACROSS.slice(0, -1)}, not with "Holy One".`]],
    ]);
    act(() => release("assurance"));
    expect(await within(card("Assurance of Pardon")).findByText("Revised with these notes.")).toBeInTheDocument();
    await waitFor(() => expect(within(across()).queryByText(OPENING)).toBeNull()); // every one revised: the note goes
    expect(within(across()).getByText("Two prayers say journey.")).toBeInTheDocument();
    // Focus moves as a dismiss would: the next note's ×, not the last card's Undo.
    await waitFor(() => expect(within(across()).getByRole("button", { name: "Dismiss note: Two prayers say journey." })).toHaveFocus());
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("Leader: Gracious God, we gather."); // the first is kept
    await user.click(within(card("Opening Prayer")).getByRole("button", { name: "Undo" }));
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, as we journey, hear us.");
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveValue("Leader: Through Christ you are forgiven.");
  });

  it("asks once when your text is involved, closing when one of them changes; Keep my text sends nothing; a 429 stops the rest and keeps the note", async () => {
    let d = withCard(seeded(), "call_to_worship", "Gracious God, we gather.", "ai");
    d = withCard(d, "opening_prayer", "Gracious God, hear us.", "typed");
    d = withCard(d, "prayer_of_confession", "Gracious God, we confess.", "archive");
    d = withCard(d, "assurance", "Gracious God, you forgive us.", "ai");
    const answer = reviewResult({
      cards: [
        { section: "call_to_worship", notes: [] },
        { section: "opening_prayer", notes: [reviewNote("read_aloud", "The second clause is hard to say aloud.")] },
        { section: "prayer_of_confession", notes: [] },
        { section: "assurance", notes: [] },
      ],
      service_notes: [reviewNote("repetition", OPENING, "code")],
    });
    const { user, api } = renderStep(d, {
      "POST /liturgy/review": reviewRoute(() => answer),
      "POST /liturgy/revise": reviseRoute((body) =>
        body.section === "opening_prayer"
          ? { text: "Holy One, hear us." }
          : body.section === "assurance"
            ? { text: "Loving God, you forgive us." }
            : fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", { details: { retry_after_seconds: 30 } }),
      ),
    });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await screen.findByText("Review finished. 2 notes.");
    const button = within(across()).getByRole("button", { name: "Revise the other prayers" });
    await user.click(button);
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your text?" });
    expect(dialog).toHaveTextContent(
      "Revise replaces the text in Opening Prayer, Prayer of Confession and Assurance of Pardon. You can undo each right after.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Keep my text" }));
    await waitFor(() => expect(button).toHaveFocus());
    expect(revisions(api)).toHaveLength(0);
    // Another tab changes the Confession's text, keeping its opening: the confirm closes, sending nothing.
    await user.click(button);
    await screen.findByRole("alertdialog");
    otherTab(withCard(stored(), "prayer_of_confession", "Gracious God, we confess our sins.", "archive"), "2026-09-29T16:59:00.000Z");
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(button).toHaveFocus());
    expect(revisions(api)).toHaveLength(0);
    await user.click(button);
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Revise text" }));
    await waitFor(() => expect(button).toHaveFocus());
    expect(await within(card("Opening Prayer")).findByText("Revised with these notes.")).toBeInTheDocument();
    expect(await within(card("Prayer of Confession")).findByRole("alert")).toHaveTextContent("Too many requests — try again in 30 s.");
    // The 429 stopped the batch: the Assurance was never sent and is no longer revising.
    expect(revisions(api).map((b) => [b.section, b.text])).toEqual([
      ["opening_prayer", "Gracious God, hear us."],
      ["prayer_of_confession", "Gracious God, we confess our sins."],
    ]);
    expect(within(card("Assurance of Pardon")).queryByRole("button", { name: "Cancel revising Assurance of Pardon" })).toBeNull();
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveValue("Gracious God, you forgive us.");
    // Not every one was revised: the note stays, and the button now offers the ones left, off until the wait ends.
    expect(within(across()).getByText(OPENING)).toBeInTheDocument();
    const again = within(across()).getByRole("button", { name: "Revise the other prayers" });
    expect(again).toHaveAttribute("aria-disabled", "true");
    expect(within(across()).getByText("Too many requests — try again in 30 s.")).toBeInTheDocument();
    await user.click(again);
    expect(again).toHaveFocus();
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(revisions(api)).toHaveLength(2);
  });

  it("goes when fewer than two switched-on prayers share the opening, closing its confirm; Cancel skips a prayer not sent yet, moves on from the running one, and keeps the note", async () => {
    let d = withCard(seeded(), "call_to_worship", "Leader: Gracious God, we gather.", "typed");
    d = withCard(d, "opening_prayer", "Gracious God, hear us.", "typed");
    d = withCard(d, "prayer_of_confession", "Gracious God, we confess.", "archive", false);
    const answer = reviewResult({
      cards: [
        { section: "call_to_worship", notes: [reviewNote("rules", STOCK, "code")] },
        { section: "opening_prayer", notes: [] },
      ],
      service_notes: [reviewNote("repetition", OPENING, "code")],
    });
    const { user, api } = renderStep(d, {
      "POST /liturgy/review": reviewRoute(() => answer),
      "POST /liturgy/revise": reviseRoute(() => new Promise<never>(() => {})),
    });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await screen.findByText("Review finished. 2 notes.");
    await user.click(within(across()).getByRole("button", { name: "Revise the other prayers" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your text?" });
    expect(dialog).toHaveTextContent("Revise replaces the text in Opening Prayer. You can undo each right after.");
    // Another tab gives the Opening Prayer a new opening: the switched-off Confession does not count, so none is shared.
    otherTab(withCard(stored(), "opening_prayer", "Holy One, hear us.", "typed"), "2026-09-29T16:59:00.000Z");
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(within(across()).queryByRole("button", { name: "Revise the other prayers" })).toBeNull();
    expect(within(across()).getByText(OPENING)).toBeInTheDocument(); // the note stays until the next review
    await waitFor(() => expect(reviewButton()).toHaveFocus());
    // Back to "Gracious God" there and in the Assurance, and the Confession switched on: three to revise.
    otherTab(
      withCard(withCard(stored(), "opening_prayer", "Gracious God, hear us now.", "typed"), "assurance", "Gracious God, you forgive.", "ai"),
      "2026-09-29T16:59:30.000Z",
    );
    await user.click(screen.getByRole("switch", { name: "Include Prayer of Confession" }));
    await user.click(within(across()).getByRole("button", { name: "Revise the other prayers" }));
    const three = await screen.findByRole("alertdialog");
    expect(three).toHaveTextContent("Revise replaces the text in Opening Prayer, Prayer of Confession and Assurance of Pardon.");
    await user.click(within(three).getByRole("button", { name: "Revise text" }));
    await waitFor(() => expect(revisions(api)).toHaveLength(1));
    // Cancel on the Confession, not sent yet: it is skipped. Cancel on the running Opening Prayer: on to the Assurance.
    await user.click(within(card("Prayer of Confession")).getByRole("button", { name: "Cancel revising Prayer of Confession" }));
    await user.click(within(card("Opening Prayer")).getByRole("button", { name: "Cancel revising Opening Prayer" }));
    await waitFor(() => expect(revisions(api)).toHaveLength(2));
    expect(revisions(api).map((b) => b.section)).toEqual(["opening_prayer", "assurance"]);
    await user.click(within(card("Assurance of Pardon")).getByRole("button", { name: "Cancel revising Assurance of Pardon" }));
    expect(revisions(api)).toHaveLength(2);
    expect(within(across()).getByText(OPENING)).toBeInTheDocument();
    expect(within(across()).getByRole("button", { name: "Revise the other prayers" })).not.toHaveAttribute("aria-disabled", "true");
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, hear us now.");
    expect(screen.getByRole("textbox", { name: "Prayer of Confession" })).toHaveValue("Gracious God, we confess.");
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveValue("Gracious God, you forgive.");
  });
});
````


- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/liturgy/review-step.test.tsx 2>&1 | grep -E "^ +× |Tests ")
```

**Expected:** three failures, `   × Revise the other prayers (reviewer follow-up 2) > shows only on the code note about a shared opening and revises every prayer but the first one at a time, each with its own Revising…, Cancel and Undo`, `   × Revise the other prayers (reviewer follow-up 2) > asks once when your text is involved, closing when one of them changes; Keep my text sends nothing; a 429 stops the rest and keeps the note` and `   × Revise the other prayers (reviewer follow-up 2) > goes when fewer than two switched-on prayers share the opening, closing its confirm; Cancel skips a prayer not sent yet, moves on from the running one, and keeps the note` (no button yet), then `      Tests  3 failed | 26 passed (29)`.

- [ ] **Step 3 (agent): The button, the confirm, and a noteless card's failure**

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
import { CheckIcon, CircleAlertIcon, XIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
````

**with:**

````tsx
import { CheckIcon, CircleAlertIcon, XIcon } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { canRevise, LOOKS_GOOD, STALE_LINE, TAG_LABELS, type CardReview, type Note } from "@/lib/liturgy/notes";
import { useLiturgyReview } from "@/lib/liturgy/review";
import { cn } from "@/lib/utils";
````

**with:**

````tsx
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import {
  acrossTargets,
  canRevise,
  listLabels,
  LOOKS_GOOD,
  sharedOpening,
  STALE_LINE,
  TAG_LABELS,
  type CardReview,
  type Note,
} from "@/lib/liturgy/notes";
import { useLiturgyReview } from "@/lib/liturgy/review";
import { SECTION_LABELS } from "@/lib/liturgy/sections";
import { cn } from "@/lib/utils";
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
import type { SectionKey } from "@/lib/draft/schema";
````

**with:**

````tsx
import type { DraftV1, SectionKey } from "@/lib/draft/schema";
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx

/** One list of notes: a tag chip, the sentence and a dismiss ×, wrapping at 375 px. */
export function NoteList({
````

**with:**

````tsx

/** The id of a note's sentence (it describes the note's own button, when it has one). */
function noteTextId(id: string): string {
  return `note-${id}-text`;
}

/** One list of notes: a tag chip, the sentence and a dismiss ×, wrapping at 375 px; `action` may add a row under one. */
export function NoteList({
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
  describedBy,
}: {
````

**with:**

````tsx
  describedBy,
  action,
}: {
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
  describedBy?: string;
}) {
  return (
    <ul aria-label={label} aria-describedby={describedBy} className="grid gap-2">
      {notes.map((note) => (
        <li key={note.id} className="flex min-w-0 items-start gap-2">
          <Badge variant="outline" className={cn("mt-0.5 shrink-0", faded && "text-muted-foreground")}>
            {TAG_LABELS[note.tag]}
          </Badge>
          <p className={cn("min-w-0 flex-1 text-sm wrap-anywhere", faded && "text-muted-foreground")}>{note.text}</p>
          <Button
            id={`note-${note.id}-dismiss`}
            variant="ghost"
            size="icon-lg"
            className="-my-2 size-11 shrink-0 md:my-0 md:size-8"
            aria-label={`Dismiss note: ${note.text}`}
            disabled={disabled}
            onClick={() => onDismiss(note.id)}
          >
            <XIcon aria-hidden="true" />
          </Button>
        </li>
      ))}
    </ul>
````

**with:**

````tsx
  describedBy?: string;
  /** A row under a note (its own button), or null. */
  action?: (note: Note) => ReactNode;
}) {
  return (
    <ul aria-label={label} aria-describedby={describedBy} className="grid gap-2">
      {notes.map((note) => {
        const row = (
          <>
            <Badge variant="outline" className={cn("mt-0.5 shrink-0", faded && "text-muted-foreground")}>
              {TAG_LABELS[note.tag]}
            </Badge>
            <p id={noteTextId(note.id)} className={cn("min-w-0 flex-1 text-sm wrap-anywhere", faded && "text-muted-foreground")}>
              {note.text}
            </p>
            <Button
              id={`note-${note.id}-dismiss`}
              variant="ghost"
              size="icon-lg"
              className="-my-2 size-11 shrink-0 md:my-0 md:size-8"
              aria-label={`Dismiss note: ${note.text}`}
              disabled={disabled}
              onClick={() => onDismiss(note.id)}
            >
              <XIcon aria-hidden="true" />
            </Button>
          </>
        );
        const extra = action?.(note) ?? null;
        return extra === null ? (
          <li key={note.id} className="flex min-w-0 items-start gap-2">
            {row}
          </li>
        ) : (
          <li key={note.id} className="grid gap-2">
            <div className="flex min-w-0 items-start gap-2">{row}</div>
            {extra}
          </li>
        );
      })}
    </ul>
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
  );
  if (notes === undefined || notes.notes.length === 0) {
    // The notes went while the card revises (another tab edited it): Cancel stays.
    const rest =
````

**with:**

````tsx
  );
  // A 429's alert shows until its wait ends.
  const failureShown = failure !== undefined && !revising && (failure.retryAt === undefined || failureWaiting);
  const failureAlert = failureShown ? (
    <Alert variant="destructive" role="alert">
      <CircleAlertIcon aria-hidden="true" />
      <AlertTitle className="whitespace-normal">{failure.message}</AlertTitle>
    </Alert>
  ) : null;
  if (notes === undefined || notes.notes.length === 0) {
    // The notes went while the card revises (another tab edited it): Cancel stays. A card revised from "Across the
    // service" may have no notes of its own: its failure shows here.
    const rest =
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
        {rest}
        {dialog}
      </>
    );
  }
  // A 429's alert shows until its wait ends.
  const failureShown = failure !== undefined && !revising && (failure.retryAt === undefined || failureWaiting);
  // The wait, beside the disabled Revise, unless its own alert already says it.
````

**with:**

````tsx
        {rest}
        {failureAlert}
        {dialog}
      </>
    );
  }
  // The wait, beside the disabled Revise, unless its own alert already says it.
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
        ) : null)}
      {failureShown ? (
        <Alert variant="destructive" role="alert">
          <CircleAlertIcon aria-hidden="true" />
          <AlertTitle className="whitespace-normal">{failure.message}</AlertTitle>
        </Alert>
      ) : null}
    </div>
````

**with:**

````tsx
        ) : null)}
      {failureAlert}
    </div>
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx

/** The "Across the service" box at the top of the step (R "Notes"): notes about more than one prayer, at most 3. */
export function ServiceNotes() {
  const review = useLiturgyReview();
  const notes = review.review?.service ?? [];
  const remember = useDismissFocus(() => document.getElementById(REVIEW_BUTTON_ID));
  if (notes.length === 0) return null;
  return (
````

**with:**

````tsx

/** The id of a shared-opening note's "Revise the other prayers" button. */
function acrossId(noteId: string): string {
  return `${noteId}-revise-others`;
}

/** The prayers a confirm names, each with its origin and text, so any change to one of them closes it. */
function snapshot(d: DraftV1, keys: readonly SectionKey[]): string {
  return keys.map((k) => `${k}\u0000${d.liturgy.cards[k].origin}\u0000${d.liturgy.cards[k].text}`).join("\u0001");
}

/**
 * The "Across the service" box at the top of the step (R "Notes"): notes
 * about more than one prayer, at most 3.
 *
 * "Revise the other prayers" (reviewer follow-up 2) shows under a code note
 * "Several prayers open with "…"." while at least two switched-on prayers
 * still open with those words and one of the others can be revised
 * (`acrossTargets`); the note's sentence describes it. It is off (still
 * focusable) while any of those prayers is being written or revised, and
 * during a 429's wait, which shows beside it. When any prayer it would
 * revise is typed or saved text it asks first, once for all of them ("Replace
 * your text?"); the dialog closes, sending nothing, when the prayers it names
 * change (which ones, or any one's text or origin) or the button goes off.
 * Focus stays on the button (or, when it has gone, the Review button); the
 * prayers are revised one at a time, and each shows its own Revising… and
 * Cancel from the start. When the note goes with its button (every one was
 * revised), focus moves as a dismiss would: the next note's ×, else the
 * Review button.
 */
export function ServiceNotes() {
  const review = useLiturgyReview();
  const { draft } = useDraft();
  const { runs, rateLimitedUntil } = useLiturgyGeneration();
  const limitedUntil = rateLimitedUntil ?? undefined;
  const waiting = useRetryWait(limitedUntil);
  const notes = review.review?.service ?? [];
  const remember = useDismissFocus(() => document.getElementById(REVIEW_BUTTON_ID));
  /** The note whose confirm is open, and the prayers it names (`snapshot`). */
  const [asking, setAsking] = useState<{ id: string; others: string } | null>(null);
  /** The last button pressed and the prayers its confirm lists (kept while the dialog closes). */
  const [pressed, setPressed] = useState<{ id: string; labels: string } | null>(null);
  // The pressed button's note went (every prayer was revised) and focus fell to the page: the next note's ×, else
  // the Review button, as a dismiss. Before the cards' own effects, which would send it to the last card's Undo.
  const shownBefore = useRef<Note[]>(notes);
  useLayoutEffect(() => {
    const before = shownBefore.current;
    shownBefore.current = notes;
    if (pressed === null || notes.some((n) => n.id === pressed.id)) return;
    const at = before.findIndex((n) => n.id === pressed.id);
    if (at < 0) return;
    const active = document.activeElement;
    if (active !== null && active !== document.body) return; // focus already went somewhere on purpose
    const left = (n: Note) => notes.some((m) => m.id === n.id);
    const next = before.slice(at + 1).find(left) ?? before.slice(0, at).reverse().find(left);
    const element = next === undefined ? null : document.getElementById(`note-${next.id}-dismiss`);
    (element ?? document.getElementById(REVIEW_BUTTON_ID))?.focus();
  });
  const offer = (note: Note) => {
    const words = sharedOpening(note);
    const targets = words === null ? null : acrossTargets(draft, words);
    if (targets === null) return null;
    const busy = [targets.first, ...targets.others].some((key) => runs[key] !== undefined || review.revising[key] === true);
    return { targets, off: busy || waiting };
  };
  const asked = asking === null ? undefined : notes.find((n) => n.id === asking.id);
  const askedOffer = asked === undefined ? null : offer(asked);
  // The confirm closes when the prayers it names change, or the button goes off or away.
  if (asking !== null && (askedOffer === null || askedOffer.off || snapshot(draft, askedOffer.targets.others) !== asking.others)) {
    setAsking(null);
  }
  const dialog = (
    <ConfirmDialog
      open={asking !== null}
      onOpenChange={(open) => {
        if (!open) setAsking(null);
      }}
      title="Replace your text?"
      description={`Revise replaces the text in ${pressed?.labels ?? ""}. You can undo each right after.`}
      confirmLabel="Revise text"
      cancelLabel="Keep my text"
      onConfirm={() => {
        const id = asking?.id;
        setAsking(null);
        if (id !== undefined) review.reviseAcross(id);
      }}
      // Keep my text, Revise text, or the confirm closing on its own: the button (off while the prayers revise), else
      // the Review button when the note went.
      finalFocus={() =>
        (pressed === null ? null : document.getElementById(acrossId(pressed.id))) ?? document.getElementById(REVIEW_BUTTON_ID)
      }
    />
  );
  if (notes.length === 0) return dialog;
  return (
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
        }}
      />
    </section>
````

**with:**

````tsx
        }}
        action={(note) => {
          const offered = offer(note);
          if (offered === null) return null;
          const { targets, off } = offered;
          return (
            <div className="flex flex-wrap items-center justify-end gap-2">
              {waiting && limitedUntil !== undefined ? <WaitLine key={limitedUntil} until={limitedUntil} /> : null}
              <Button
                id={acrossId(note.id)}
                variant="outline"
                size="touch"
                aria-describedby={noteTextId(note.id)}
                focusableWhenDisabled
                disabled={off}
                className="data-disabled:pointer-events-none data-disabled:opacity-50"
                onClick={() => {
                  setPressed({ id: note.id, labels: listLabels(targets.others.map((key) => SECTION_LABELS[key])) });
                  if (targets.others.some((key) => needsRegenerateConfirm(draft.liturgy.cards[key]))) {
                    setAsking({ id: note.id, others: snapshot(draft, targets.others) });
                    return;
                  }
                  review.reviseAcross(note.id);
                }}
              >
                Revise the other prayers
              </Button>
            </div>
          );
        }}
      />
      {dialog}
    </section>
````


- [ ] **Step 4 (agent): The three files three times, the suite, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/lib/liturgy/notes.test.ts src/lib/liturgy/review.test.tsx src/components/builder/liturgy/review-step.test.tsx 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** ` Test Files  3 passed (3)` and `      Tests  44 passed (44)` three times, with no `×` or `FAIL` line; ` Test Files  78 passed (78)` and `      Tests  588 passed (588)`; `typecheck 0`, `lint 0`; `1223 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/components/builder/liturgy/card-notes.tsx frontend/src/components/builder/liturgy/review-step.test.tsx
git commit -q -m "Liturgy step: Revise the other prayers in Across the service (follow-up 2; owner answers 1, 3, 5)" -m "The code note Several prayers open with gets Revise the other prayers,
described by the note, while two switched-on prayers still share the
opening and one can be revised. Your text or a saved service's asks once,
Replace your text?, naming them all; it closes if any of them changes.
The button is off while any of them is busy and during a 429's wait,
shown beside it; focus stays on it, and when the note goes it moves as a
dismiss would. A card with no notes of its own shows its revision's
failure." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 3: backend **1223 passed, 11 skipped**; frontend **588 in 78**.

### Task 4: Docs: the manual check and R's amendment (owner answer 6; clarification 13)

**Files:**
- Modify: `docs/manual-verification.md`, `docs/superpowers/specs/2026-09-26-service-reviewer-design.md`

- [ ] **Step 1 (agent): Write the docs**

**In `docs/manual-verification.md`, replace:**

````markdown
(`docs/superpowers/plans/2026-10-01-reviewer-followup-1.md`); that result
goes into "Reviewer follow-up 1 record".
````

**with:**

````markdown
(`docs/superpowers/plans/2026-10-01-reviewer-followup-1.md`); that result
goes into "Reviewer follow-up 1 record". Items marked "(owner, after
follow-up 2)" are the owner's phone check after reviewer follow-up 2
(`docs/superpowers/plans/2026-10-01-reviewer-followup-2.md`); that result
goes into "Reviewer follow-up 2 record".
````

**Append to `docs/manual-verification.md`:**

````markdown
- [ ] (owner, after follow-up 2) **10.** With two or three prayers opening with the same words, **Review service**: under "Several prayers open with "…"." in "Across the service" there is **Revise the other prayers** (an AI note there has none). Tap it: the first of those prayers keeps its text; each of the others shows "Revising…" with its own Cancel from the start, and they are revised one at a time (about 10 s each), each with a new opening, different from the first and from each other, and "Revised with these notes. Undo"; the note goes once all were revised with new openings (if the AI kept the opening, the note and its button stay). When one of them is your own or saved text, "Replace your text?" asks first, once, naming them; **Keep my text** changes nothing. **Undo** on one card brings back only that card's text.
````


**Append to `docs/superpowers/specs/2026-09-26-service-reviewer-design.md`:**

````markdown

## Amendment 2026-10-01: reviewer follow-up 2 (Revise from "Across the service")

`docs/superpowers/plans/2026-10-01-reviewer-followup-2.md`, on the owner's answers of 2026-10-01 ("all recommended"):

- **Revise the other prayers** shows under the code note "Several prayers open with "…"." in "Across the service", and on no other note (an AI note there does not say which prayers it means). The frontend finds the prayers again from the draft by the backend's rule (the first two words after any "Leader:" or "People:" label, any case; a shared fixture keeps the two in step), among the switched-on cards with text. No API change.
- The first of them in service order keeps its text, and so does a Benediction following the church default; the others (AI, typed or saved text) are revised one at a time, in service order (owner decision A), through the existing `POST /liturgy/revise`, each with one note: `Opens with "{words}" like the {first prayer's label}; open differently.` (not its own notes), to which each later one adds the new openings so far (`, not with "X" or "Y"`; at most 240 characters, the oldest dropped first). Each shows "Revising…" with its own Cancel from the start, then its failure message or "Revised with these notes. Undo"; a success drops that card's own notes, as any revision does.
- When any of them is typed or saved text, one confirm asks first: "Replace your text?", "Revise replaces the text in {A}, {B} and {C}. You can undo each right after.", "Revise text", "Keep my text".
- The button is off while any of those prayers is being written or revised and during a 429's wait (shown beside it), and goes when fewer than two switched-on prayers still share the opening or none can be revised. A Cancel on one not sent yet skips it, on the running one moves on; one edited meanwhile or failed is skipped; a 429 stops the rest. The note goes once every one was revised and fewer than two switched-on prayers still share the opening (never a newer review's note); otherwise it stays, even when the AI kept the opening (owner answer A, 2026-10-01), and the button then offers the ones that still share it.
````


- [ ] **Step 2 (agent): Check the docs tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
grep -c "—" <(git diff -U0 -- docs | grep '^+' | grep -v '^+++')
.venv/bin/python -m pytest -q | tail -1
git diff --stat | tail -1
```

**Expected:** `89 passed in <t>s`; `4`; `0` (no em dash added); `1223 passed, 11 skipped in <t>s`; `2 files changed, 14 insertions(+), 1 deletion(-)`.

- [ ] **Step 3 (agent): Commit**

```bash
git add docs/manual-verification.md docs/superpowers/specs/2026-09-26-service-reviewer-design.md
git commit -q -m "Docs: reviewer follow-up 2 in the reviewer spec and the manual check (owner answers 2026-10-01)" -m "The reviewer spec gains an amendment for Revise the other prayers (which
note, which prayers, the one note sent, the confirm, the button while busy,
when the note goes). docs/manual-verification.md: item 10, marked for the
owner's phone check after the merge." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 4 (controller): Review the batch (T1-T4) and backup push**

One review of the whole batch: the port matches `opening_words`, the label's spaces included, and the fixture covers its edges (clarification 2); only the code opening note gets the button, and it hides as clarification 1 says; the first and a default Benediction are kept (clarification 3); the note sent is exactly clarification 4's, its list of new openings and its 240-character cap; one at a time, each through `startRevise` with every existing guard, every card revising from the start, Cancel on a waiting or running one, an edited or failed one skipped, a 429 stopping the rest (clarifications 7-9); the note goes only when all were revised and never removes a newer review's note (`generation`, clarification 10); the confirm's copy verbatim, its list, its closing on any listed prayer's change and focus (clarification 6); the button off while busy or waiting, with the wait beside it (clarification 8); focus after the note goes, as a dismiss, never to the page (clarification 11); a noteless card's failure shows (clarification 12); 44 px targets and wrapping at 375 px; the docs match. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

Counts after Task 4: backend **1223 passed, 11 skipped**; frontend **588 in 78**.

### Task 5: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline --grep '^Plan: reviewer follow-up 2' -1
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
```

**Expected:** nothing (or `?? .claude/`); `0`; `<sha> Plan: reviewer follow-up 2, Revise from Across the service (owner answers 2026-10-01)`; `0`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 5)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the frontend three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error")
```

**Expected:** `1223 passed, 11 skipped in <t>s`; three times ` Test Files  78 passed (78)` and `      Tests  597 passed (597)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s` and no `Error` (the build runs in the real checkout; a font `Failed to fetch` only: say so and rely on CI).

- [ ] **Step 3 (agent): The API files are unchanged, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff --name-only origin/main...HEAD | LC_ALL=C sort
git diff --name-only origin/main...HEAD -- backend/api backend/usecases backend/review_checks.py backend/migrations backend/db .github frontend/package.json frontend/package-lock.json frontend/src/lib/api docs/ops-runbook.md app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status`; `raw html grep exit 1`; exactly these 11 paths:
```
backend/tests/fixtures/shared/opening_words.json
backend/tests/test_review_checks.py
docs/manual-verification.md
docs/superpowers/plans/2026-10-01-reviewer-followup-2.md
docs/superpowers/specs/2026-09-26-service-reviewer-design.md
frontend/src/components/builder/liturgy/card-notes.tsx
frontend/src/components/builder/liturgy/review-step.test.tsx
frontend/src/lib/liturgy/notes.test.ts
frontend/src/lib/liturgy/notes.ts
frontend/src/lib/liturgy/review.test.tsx
frontend/src/lib/liturgy/review.tsx
```
`0`; the subjects oldest first: `WIP plan: reviewer follow-up 2`, `Plan: reviewer follow-up 2, Revise from Across the service (owner answers 2026-10-01)` (and any later plan commits), then T1-T4's four subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** one `✓ Logged in` line; `[]`. Send the owner exactly this, and wait for a clear yes:

> Reviewer follow-up 2 is verified on this machine: backend 1223 passed, 11 skipped (1222 before); frontend 597 tests in 78 files (581 before), three runs in a row; typecheck, lint and the production build are clean; the API is unchanged. It adds **Revise the other prayers** under "Several prayers open with …": the first prayer keeps its text, the others are revised one at a time to open differently, each with its own Undo, and "Replace your text?" asks first when your own text is involved. May I open the pull request as a **draft** titled "Reviewer follow-up 2: Revise the other prayers", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/followup2-pr-body.md" <<'EOF'
Reviewer follow-up 2 (owner answers of 2026-10-01): Revise from "Across the service". Plan: docs/superpowers/plans/2026-10-01-reviewer-followup-2.md. No route, schema, migration or variable change.

- The code note "Several prayers open with "…"." gets **Revise the other prayers** while two switched-on prayers still share the opening; AI notes across the service get none.
- The first of those prayers keeps its text (and a Benediction following the church default is never changed); the others are revised one at a time, in service order, through the existing per-card Revise, each with the one note `Opens with "…" like the {first}; open differently.` (later ones also naming the new openings so far), its own Revising… and Cancel from the start, and "Revised with these notes. Undo".
- "Replace your text?" asks once when any of them is typed or saved text, naming them all.
- The note goes once every one was revised and no two switched-on prayers still share the opening (never a newer review's); a failure, Cancel, edit or an opening the AI kept keeps it (owner answer A, 2026-10-01), and a 429 stops the rest.
- The frontend finds the prayers with the backend's opening rule; a shared fixture (backend/tests/fixtures/shared/opening_words.json) pins both.

Tests: backend 1222 → 1223 passed, 11 → 11 skipped; frontend 581 → 597 in 78 → 78 files

After merge (Task 6): a three-step check on the owner's phone, then a short "Reviewer follow-up 2 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
EOF
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Reviewer follow-up 2: Revise the other prayers" \
  --body-file "<scratch>/followup2-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1223 passed, 11 skipped`, backend-postgres `11 passed, 1223 deselected`, frontend `597 passed` in 78 files. Then send: "PR #<N> is green: backend 1223 passed, 11 skipped; 597 frontend tests in 78 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_review_checks.py`'s fixture test, `notes.test.ts` | T1 |
| `review.test.tsx` | T2 |
| `review-step.test.tsx` (the follow-up 2 cases, or an older case the new button or alert disturbed) | T3 |
| `test_docs.py`, `test_slice1_docs.py` | T4 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, follow-up 2 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1223 passed, 11 skipped`; frontend `597 passed` in 78 files.

### Task 6: Merge, the owner's phone check (three steps), the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate; the Vercel deploy is the one members see. The owner's check is **one step at a time** (send one, wait for the report or "next"). The agent writes each result into `<scratch>/followup2-t6-results.md` (not committed). The AI's words differ every time: record what the page showed, never a token, an email address or a church id.

**Files:** Modify (the records PR, Step 6): `docs/ops-runbook.md`: insert `### Reviewer follow-up 2 record` right after the "Reviewer follow-up 1 record" table (its last row starts `| Follow-ups | Accepted, not fixed: notes on a Benediction`) and before `## Backups`. A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (reviewer follow-up 2) is ready, green and up to date with main. There is no database change, and liturgy-frozen is not affected. Then I will ask you for three short checks on your phone, one at a time. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about two minutes for Vercel before Step 2.

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 3: the button revises the others, not the first**

> On your phone, open https://worship-service-builder.vercel.app (signed in, in your church). Tap **⋮** next to Summary, choose **New service** (tap **Start new service** if it asks), then tap **3 Liturgy**. Type these three, each as the whole text of its card: **Call to Worship** `Leader: Gracious God, we gather.`; **Opening Prayer** `Gracious God, hear our prayer.`; **Prayer of Confession** `Gracious God, we confess our sins.` Tap **Review service**. At the top, **Across the service** should say `Several prayers open with "Gracious God".` with **Revise the other prayers** under it (any other note there has no such button). Tap it: a box asks "Replace your text?" and names Opening Prayer and Prayer of Confession. Tap **Keep my text**: nothing changes. Tap **Revise the other prayers** again, then **Revise text**: Opening Prayer and Prayer of Confession both show "Revising…" with their own × straight away; the Opening Prayer gets its new text first, then the Prayer of Confession (about 10 seconds each). Do the two new texts open differently from "Gracious God" and from each other? About how long did it take until both were done? Does the Call to Worship keep your words exactly?

Record whether the button showed (and only there), the confirm's wording, the time from **Revise text** until both were revised (expect about 10 s per prayer, so about 20 s), the two new openings and whether they differ from each other (and from "Gracious God"), and that the Call to Worship was unchanged.

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 3: Undo on each card**

> Each of the two revised cards should now say "Revised with these notes. Undo" and show "AI draft". Tap **Undo** on the **Opening Prayer** only: your words come back there, and the Prayer of Confession keeps its revised text. Is that what you see?

Record both cards' lines and what Undo changed.

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 3: the note after the revisions**

> Look at **Across the service**: once both revisions came back, the `Several prayers open with "Gracious God".` note should have gone (the box goes too if it had nothing else); if either new text still opens with "Gracious God", the note and its button stay instead (owner answer A): say so. Now tap **Review service** again: since Undo brought back "Gracious God" in the Opening Prayer, the note should come back, and **Revise the other prayers** should now name only the Opening Prayer when it asks. Tap **Keep my text**. Is that what you see?

Record whether the note went after the revisions, came back on the new review, and what the confirm named.

- [ ] **Step 5 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/followup2-t6-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 6 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^### Reviewer follow-up 1 record$\|^| Follow-ups | Accepted, not fixed: notes on a Benediction\|^## Backups$' docs/ops-runbook.md
```

**Expected:** `Fast-forward` (or `Already up to date.`); three lines in that order. Insert, between that last row and `## Backups` (one blank line on each side):

```markdown
### Reviewer follow-up 2 record

Reviewer follow-up 2 (Revise from "Across the service": **Revise the other
prayers** on the code note "Several prayers open with …", the first prayer
kept and the others revised one at a time, one "Replace your text?" for your
own or saved text, Undo on each card; owner answers of 2026-10-01) merged as
PR #<N>. No database change and no new variable; production stays at
`0004_invites_reusable`; the API is unchanged. The owner's check was three
steps on a phone, covering the "(owner, after follow-up 2)" item of
`docs/manual-verification.md` → "Service reviewer". No token, email address
or church id is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success | <date> |
| 1. Revise the other prayers (phone: <phone and browser>) | <The button showed only under the opening note; "Replace your text?" named Opening Prayer and Prayer of Confession; Keep my text changed nothing; both revised one at a time in <n> s, with new openings "<opening 1>" and "<opening 2>", <different from each other / the same>; the Call to Worship unchanged. / …> | <date> |
| 2. Undo on each card | <Both showed "Revised with these notes. Undo"; Undo on the Opening Prayer brought its text back and left the Confession revised. / …> | <date> |
| 3. The note after the revisions | <The note went once both were revised; a new review brought it back, and the button named only the Opening Prayer. / …> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: 5a (saving and archiving services and the Word files), Voices of the Church, 6a. | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Then:

(not replayed)
```bash
sed -n '/^### Reviewer follow-up 2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Reviewer follow-up 2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: reviewer follow-up 2 record (merged; owner's phone check)" -m "Records reviewer follow-up 2 (PR #<N>): the merge and CI on main, and the
owner's three-step phone check (Revise the other prayers keeps the first
and revises the others; Undo on each card; the note after the revisions).
No token, email or church id is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 7 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The reviewer follow-up 2 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes:

(not replayed)
```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: reviewer follow-up 2 record" \
  --body "Records reviewer follow-up 2 (PR #<N>) in docs/ops-runbook.md → Reviewer follow-up 2 record: the merge and the owner's three-step phone check. No token, email or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Reviewer follow-up 2 is live and recorded; <n> follow-ups."

- [ ] **Step R (only if the release must come out): Revert**

Code only (notes were never saved; no draft shape changed). On the owner's yes for each outward command: a branch `claude/revert-reviewer-followup-2` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert reviewer follow-up 2 (PR #<N>)" with the trailer, both suites (`1222 passed, 11 skipped`; `581 passed` in 78), a PR, CI, and the merge on the owner's yes; record it in the follow-up record.

Expected counts after this task: backend `1223 passed, 11 skipped` on `main`; frontend `597 passed` in 78 files. The records PR adds no test.

---

## Build notes

**How this plan was written (2026-10-01).** Each task's code was built and run in a throwaway worktree of `b1ab12c` (the repo's `.venv`, the checkout's `node_modules`), then the directives were generated from that worktree's changes and replayed onto a fresh detached worktree of `b1ab12c` by the script that applies every Create, Append and Replace directive in order, running each task's commands.
- **Revised the same day** for the plan review's fixes (the confirm closes on any listed prayer's text or origin change; the review's `generation`, so a late batch never removes a newer review's note; Python's `\s` around the label, with two new fixture cases checked against Python first; the case note; focus when the note goes; the retry wording in clarification 12; T3's last press) and owner decision A (one at a time). The whole plan was replayed again onto a fresh detached worktree of this branch's `3f19384` (the code there is `b1ab12c`'s), with the commands below; the figures here are that replay's.
- All 41 directives applied (T1 8, T2 18, T3 12, T4 3); every Replace anchor occurred exactly once.
- Every "see it fail" output matched as quoted (T1 `2 failed | 5 passed (7)`; T2 `2 failed | 6 passed (8)`; T3 `3 failed | 26 passed (29)`); T1's backend pin passed at once (`8 passed`), as said. Every count matched the table: backend 1223 (11 skipped) from T1; frontend 583, 585, then 588 in 78 files; the three changed test files three times after T3 (`44 passed`), the whole frontend suite three times at the end, with no `×` or `FAIL` line; typecheck 0 and lint 0 after every task; the docs tests `89 passed`, owner markers `4`, no em dash added; the OpenAPI export and `gen:api` left the API files unchanged; no raw HTML; exactly the 10 paths T5 Step 3 lists besides this plan.
- **Choices made while building:** the button sits inside the note's list item (`NoteList`'s `action`), so it is next to the note it acts on; the confirm's text is kept in state when the button is pressed, so it does not change while the dialog closes; `revise(key)` became `startRevise(key)` with two optional arguments, so the batch reuses every guard rather than copying them; the batch keeps its waiting prayers in a ref (`AcrossBatch`), marks them all as revising at once, and starts the next from the last one's end through a ref to the latest `startRevise`; the focus move when the note goes runs in a layout effect, so it comes before the cards' own effects. Checked by breaking each fix on purpose: without the text-and-origin snapshot, the focus move or the `generation` check, the test written for it fails.
- **Build review fixes (owner decision 1).** The build's review (no Critical) found: an Undo of an already-revised prayer mid-batch let the note go while the shared opening was back, so the batch now also needs `acrossTargets` to be null at its end (I1); `startRevise` reached the batch through a passive effect, now a layout effect, with the 429's `rateLimitedUntil` kept beside it (I2); a prayer `startRevise` refused at its turn was dropped silently, so the batch now stops as after a 429, the rest no longer revising and the note kept, and a refusal for a 429's wait shows that wait on the prayer with the existing `rateLimitMessage` alert (other refusals stop silently; `startRevise` returns `"limited"` for the wait, and `revise` still a boolean) (M1); the batch stops, the note kept, when the kept first prayer no longer opens with the words before the next is sent (M2); "Across the service" followed its pressed button for good, so a later removal of a note with that id could move focus, so it now follows it in a ref only until its batch ends with the note kept or the note goes, and the confirm's labels and closing focus are kept apart from it (M3); seven tests in `review.test.tsx` (the Undo, the 429's wait between turns, the first prayer edited, New service, unmount, a non-429 failure, another tab's edit) (M4); the shared fixture's `groups`, with both sides' tests reading them; both agree on case, Greek final sigma included, so no gap is left to accept (M5). No new user-facing copy; the API is unchanged. Each of the I1, M1 and M2 tests fails against the code before these fixes. Counts: backend **1223 passed, 11 skipped** (the fixture's groups are checked inside the existing test); frontend **596 in 78** (589 + 7), three runs in a row with no `×` or `FAIL` line; typecheck 0, lint 0.
- **Owner answer A (Beau, 2026-10-01): when the note goes.** The note stays whenever two or more switched-on prayers still share the opening after a batch, including when every revision succeeded but the AI kept the opening (the I1 check at the batch's end, `acrossTargets` not null, already did this). Question 5's earlier wording ("goes once every revision succeeded, even if the AI kept the opening") is superseded; clarification 10, the Risks, the amendment, the manual check, T6 Step 4 and the PR body now say so. One test in `review.test.tsx` (every revision succeeds, each keeping "Gracious God": the note stays and `reviseAcross` starts again), which fails when the I1 check is removed. Counts: frontend **597 in 78**; backend unchanged.
- **Open question for the owner (M6, not changed: it needs owner copy).** Screen readers are not told why "Revise the other prayers" is off while one of its prayers is busy (the 429 wait has its line; busy does not), and nothing is announced when a batch ends or is cut short; only focus moves. Relatedly, a batch that stops for a reason other than a 429 (the kept first prayer no longer opens with the words, or the AI started writing the next prayer) says nothing about why. Each would need new copy; until the owner gives it, they stay silent.
- Not run while planning: the production build (Turbopack refuses the replay's symlinked `node_modules`; T5 runs it in the real checkout), the pushes, the PR and CI, the merge and the owner's checks, and any call to OpenAI.

## Spec coverage

| Owner answer or R item | Task(s) and tests |
|---|---|
| 1. Only the code opening note gets the button; AI notes none; hidden when fewer than two still share | T1 `notes.test.ts` "reads openings and the shared-opening note …", "finds the prayers as the draft is now …"; T2 `review.test.tsx` (the AI note starts nothing); T3 review-step "shows only on the code note …" (one button, not on the AI note), "goes when fewer than two switched-on prayers share the opening …"; T6 Step 2 |
| 1. The same rule as the backend, no API change | T1 `test_opening_words_and_the_opening_note_match_the_shared_fixture` and the same fixture in `notes.test.ts`; T5 Step 3 (API files unchanged) |
| 2. The first kept; the others revised with one note; a default Benediction kept; switched-off cards left out | T1 "finds the prayers as the draft is now …"; T2 "revises every prayer but the first one at a time …" (the bodies); T3 "shows only on the code note …" (the Call to Worship unchanged), "goes when fewer than two …" (the switched-off Confession); T6 Steps 2, 4 |
| 3. One confirm when your text is involved, its copy and list; all-AI starts at once; it closes when a listed prayer changes | T1 (`listLabels`); T3 "asks once when your text is involved …" (three names; Keep my text sends nothing; focus back; another tab's edit to the Confession that keeps the opening closes it), "goes when fewer than two …" (one name; the dialog closes when the prayers change, focus to Review service), "shows only on the code note …" (no confirm); T6 Step 2 |
| 4. Undo per card | T2 (each `undo revised`); T3 "shows only on the code note …" (Undo on one card only); T6 Step 3 |
| 5. The label; Revising… and Cancel per card from the start; a Cancel keeps the note | T2 (all three revising from the start); T3 "shows only on the code note …" (both Cancels before the second is sent), "goes when fewer than two …" (Cancel keeps the note and frees the button); T6 Step 2 |
| 6. The note goes when all were revised, stays otherwise; the button then offers the rest; never a newer review's note | T2 "revises every prayer …" (the note goes), "never removes the note of a newer review …", "keeps the note and offers the button again when every one was revised but the AI kept the opening" (owner answer A); T3 "asks once …" (a 429 keeps it; the button offers the ones left), "goes when fewer than two …" (Cancel keeps it); T6 Step 4 |
| Decision A: one at a time, the openings so far, Cancel, skips and the 429 (clarifications 4, 7-9) | T1 (`acrossNote` with one, two and three openings, and the 240-character cap); T2 "revises every prayer …" (one request at a time in service order; the second and third notes name "Holy One", then "Holy One" or "Merciful God"; a second press starts nothing); T3 "shows only on the code note …" (the second is sent after the first ends, told "Holy One"), "asks once …" (a 429 on the second stops the third: never sent, no longer revising), "goes when fewer than two …" (Cancel on a waiting prayer skips it; Cancel on the running one moves on); T6 Step 2 (the openings differ; the time) |
| Busy and the 429 wait (clarification 8) | T3 "shows only on the code note …" (off and focused while they run), "asks once …" (off with the wait beside it; a press sends nothing, opens no confirm and keeps focus) |
| Focus and screen readers (clarification 11) | T3 (the button described by the note; focus stays on it; when the note goes, the next note's ×, not the last card's Undo; Review service when the button goes) |
| A noteless card's failure (clarification 12) | T3 "asks once …" (the Confession, "Looks good.", shows the 429 alert) |
| 6. Process: one PR, one batch, phone check, records, the manual item | T4 (item 10; R's amendment), T4 Step 4 (the batch review), T5, T6 |

## Questions for the owner

Your answers of 2026-10-01 (1-6, "all recommended") are binding and already in the plan. These are the choices the plan makes where you did not say. **Answered 2026-10-01:** 1-7 "all recommended", and 8 with A; all binding and already in the plan.

1. **The note each prayer is revised with** (clarification 4): only `Opens with "Gracious God" like the Call to Worship; open differently.`, not that prayer's own notes, so the revision does one thing. Recommended: accept.
2. **Its own notes after** (clarification 5): as after any revision, a revised prayer's own notes go (they were about the old text), it shows "AI draft" and "Revised with these notes. Undo"; Undo brings the text back without them. Recommended: accept.
3. **The confirm names every prayer it will revise** (clarification 6), the AI ones too, not only yours, since all are replaced. Recommended: accept.
4. **The Benediction following your church's default** (clarification 3) counts as one of the prayers (the review counted it) but is never changed; if the only other prayer sharing the opening is that Benediction, there is no button. Once you edit it, it is your text and can be revised. Recommended: accept.
5. **When the note goes** (clarification 10): once every prayer the button sent was revised, even if the AI happened to keep the opening (the next review finds it again); if one failed, was cancelled or kept for your edit, the note stays and the button offers the ones left. Recommended: accept. **Superseded by owner answer of 2026-10-01: A.** The note stays whenever two or more switched-on prayers still share the opening, including when every revision succeeded but the AI kept the opening; the button then offers them again.
6. **The button while busy** (clarification 8): it stays but is off while any of those prayers is being written or revised, and during a "Too many requests" wait, shown beside it. Recommended: accept.
7. **A failure on a prayer with no notes of its own** (clarification 12) shows on that card, where notes go. Recommended: accept.
8. **All at once or one at a time** (clarifications 4, 7; from the plan's review). Revised all at once, two prayers could both land on the same new opening. **A:** one at a time, in service order, each told to avoid the shared opening and the new openings before it (`…; open differently, not with "Holy God" or "Loving God".`); every prayer shows "Revising…" with its own Cancel from the start; a Cancel skips one not sent yet or moves on from the running one; an edited or failed one is skipped; a 429 stops the rest and the note stays. About 10 s per prayer, so slower than all at once. **Chosen: A.**

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T5); the merge on your yes, then three phone checks one at a time and the records PR (T6).
