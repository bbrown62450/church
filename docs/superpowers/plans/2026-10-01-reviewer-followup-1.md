# Reviewer Follow-up 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Four small changes to the service reviewer, from the owner's phone check after it merged (owner answers 1-6 of 2026-10-01, "all recommended"), in one PR built in one batch (about a day). After it merges: the AI review leaves notes only for something to change, never praise; **Revise with these notes** is offered on typed and saved text too, after "Replace your text?", with Undo; after an edit a card's notes stay, dimmed, under "From before your last edit." until the next review; and an AI note that only restates a code note (a citation, a repeated opening) is dropped. No route, schema, migration or variable changes; production Streamlit (https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`) is untouched.

**Architecture:** Backend first. T1 firms up two strings in `usecases/liturgy_review.py` (`CONTRACT`, and `CODE_NOTES_INTRO`, now finished by `code_notes_intro` from the code notes present). T2 adds `drop_restated` there and runs it on each card's AI notes before `merge_notes`, and drops an AI note across the service on prayers that open alike when the code note names the opening. Frontend: T3 makes `pruneReview` (`lib/liturgy/notes.ts`) mark a changed card's notes `stale` instead of dropping them, adds `forgetCard` for a successful Regenerate (through a new `onWritten` listener on the generation provider) or Revise, and shows the faded notes and the line in `CardNotes`. T4 widens `canRevise` to typed and saved text and puts the existing `ConfirmDialog` in front of Revise on those cards. T5 is the docs. T6 verifies and opens the draft PR; T7 is the merge, the owner's four-step phone check and the record.

**Tech Stack:** as the service reviewer plan: Python 3.11 (`.venv`), FastAPI, pytest with `FakeAI`; Next 16, React 19, TypeScript 5, Base UI, Vitest 3 with Testing Library.

**Source documents:**
- Reviewer spec ("R"): `docs/superpowers/specs/2026-09-26-service-reviewer-design.md` (decision 4, "Notes", "Notes go away when the text changes", "Revise with these notes", "Layer 2: AI review").
- The reviewer plan ("RP"): `docs/superpowers/plans/2026-10-01-service-reviewer.md` (its clarifications 18-25 are what this plan changes), and its runbook record, `docs/ops-runbook.md` → "Service reviewer record" (follow-ups 1-4 there are this plan; 5 is out of scope).
- The branch also carries one docs-only commit made before this plan, `2607566 Docs: Voices of the Church owner decisions (pre-spec, 2026-10-01)` (one new file under `docs/superpowers/specs/`); it touches nothing this plan changes.
- Facts checked for this plan (tree `faa0ecb` = `origin/main`, the reviewer merged and live, 2026-10-01): backend `1217 passed, 11 skipped`; frontend `570 passed` in 78 files; typecheck and lint clean; Alembic head `0004_invites_reusable`; 4 runbook owner markers. `revise_section` and `ReviseIn` take no origin, so the backend never restricted Revise to AI text; only `canRevise` in `notes.ts` did. `needsRegenerateConfirm` (`cards.ts`) is true for "typed" and "archive" cards with text. `check_openings` builds its key from `opening_words` (the first two words, lowered and joined by a space) and puts the first card's words in `Note.match`.
- Every task's code was written and run by the planner in a throwaway worktree of `faa0ecb`, and the plan's directives were then replayed onto a fresh worktree of `faa0ecb` (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one file `.venv/bin/python -m pytest -q <file> 2>&1 | tail -2`; the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one file `(cd frontend && npx vitest run <path> 2>&1 | grep -E "Tests ")`; the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` (a failure is named); then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- No route or schema changes, so the OpenAPI snapshot and `schema.d.ts` are not regenerated (T6 checks they are unchanged).
- Branch `claude/slice-2-plan-4q33le`, at `origin/main` `faa0ecb` plus this plan's commits (`WIP plan: reviewer follow-up 1`, then `Plan: reviewer follow-up 1 (owner answers 2026-10-01)` (twice), then `Plan: reviewer follow-up 1 review fixes (owner answers 2026-10-01)`), then T1-T5, the review fixes `a0959fb` and `Plan: reviewer follow-up 1 build notes and counts`. Stage files by name; `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`). A fix asked for by the review is a new commit, `Fix: <what> (Task <n> review)`.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1217 → 1222 passed, 11 → 11 skipped; frontend 570 → 581 in 78 → 78 files` (the counts after the review fixes, `a0959fb`; see "Build notes").
- New prose for the owner has no em dashes and no flattery. The owner's copy is exact: "Replace your text?", "Revise replaces the text in {Label} with a version that addresses these notes. You can undo right after.", "Revise text", "From before your last edit.".
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.

### How the file directives below read
As in RP: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end; **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop.

### Baselines and counts
- Starting baselines: backend **1217 passed, 11 skipped**; frontend **570 passed in 78 files**, typecheck and lint clean; Alembic head **`0004_invites_reusable`** (no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new `def test_`; a frontend delta the number of new `it(`.

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +1 (`test_usecase_liturgy_review.py`; one assertion edited) | 1218 passed, 11 skipped | 0 | 570 in 78 |
  | T2 | +2 (`test_usecase_liturgy_review.py`) | 1220 passed, 11 skipped | 0 | 570 in 78 |
  | T3 | 0 | 1220 passed, 11 skipped | +2 (`notes.test.ts` +1, `review-step.test.tsx` +1; others edited) | 572 in 78 |
  | T4 | 0 | 1220 passed, 11 skipped | +2 (`review-step.test.tsx`; others edited) | 574 in 78 |
  | T5 | 0 | 1220 passed, 11 skipped | 0 | 574 in 78 |
  | Review fixes (`a0959fb`) | +2 (`test_usecase_liturgy_review.py`) | 1222 passed, 11 skipped | +7 (`review-step.test.tsx` +6, `generation.test.tsx` +1) | 581 in 78 |
  | T6-T7 | 0 | 1222 passed, 11 skipped | 0 | 581 in 78 |

- CI `backend-postgres` stays at `11 passed, 1222 deselected` (1220 before the review fixes).

### Layering and code rules (carried)
- `usecases/liturgy_review.py` imports no FastAPI, Starlette or Streamlit; routes stay plain `def` and unchanged; tests use `FakeAI`; the `ai` bucket and its charging are unchanged (one token per review that reaches the AI, one per revision).
- No AI text, note or prayer at INFO (F §2.5): T2 adds no log line.
- Notes stay in memory only (never the draft, the archive or `localStorage`); `DraftV1` is unchanged.
- Touch targets 44 px below `md`; text wraps at 375 px; focus never drops to the page; a dimmed note uses `text-muted-foreground` (the app's readable secondary color), not opacity.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** is https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`), frozen; merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **Reviewer decisions** (R, 2026-09-26) stand, except decision 4 (Revise only on AI cards), which owner answer 2 below reverses.

### Owner answers (Beau, 2026-10-01, from the post-merge phone check; "all recommended", binding)
1. **No praise notes.** `gpt-4.1-mini` returned approving notes ("Confession names specific sins …, which fit sermon themes well"), so Revise was offered with nothing to fix. A firmer rule in the output contract, pinned by a test; no code filter guessing at compliments (T1).
2. **Revise on non-AI text.** Typed and archive cards (the set `needsRegenerateConfirm` asks for) get Revise, after the existing `ConfirmDialog`: title "Replace your text?", description "Revise replaces the text in {Label} with a version that addresses these notes. You can undo right after.", confirm "Revise text"; Undo after, as on AI cards. Focus after the dialog mirrors Regenerate's (T4).
3. **The Benediction while it follows the church default** (origin "default") has no Revise; once edited it is typed text and gets Revise with the confirm (T4).
4. **Faded notes after an edit** (replaces "notes go the moment the text changes"): the notes stay, dimmed and readable, under "From before your last edit.", each dismissable, with Revise still offered on the current text and the remaining notes; "Looks good." goes after any edit; a new Review replaces them; memory only (T3).
5. **No restated code notes.** On a card with a code "Cites …" note, AI rules notes about citing or naming scripture are dropped; AI repetition notes on a card whose opening is already in a code "Several prayers open with …" note are dropped; the prompt's "Do not repeat them" is firmer. Table tests (T1, T2).
6. **Process:** this short plan, reviewed, the owner's approval, one build batch with review and fixes, a draft PR, a phone check of about four steps after the merge (praise gone on a real review, Revise on typed text with the confirm and Undo, faded notes after typing, no restated citation or repetition notes), then a records step: "### Reviewer follow-up 1 record" in `docs/ops-runbook.md` after the Service reviewer record, before "## Backups", and the `docs/manual-verification.md` "Service reviewer" items that change (T5, T7).

### Owner answers to this plan's questions (Beau, 2026-10-01; "all recommended", binding)
The owner answered "all recommended" to "Questions for the owner" (1-8) on 2026-10-01: every choice stands as written there and in the clarifications it names. The plan's review of the same day changed no answer. It added two owner-visible notes to clarification 5, which question 4 now states (Undo after a successful Revise or Regenerate brings the text back without the notes; another tab's Regenerate or Revise fades this tab's notes under the same line), and narrowed which opening notes are dropped (clarification 4, question 2), so fewer real points are lost.

**Later, out of scope:** Revise from "Across the service" (runbook follow-up 5), planned separately.

## Spec clarifications

The owner's answers win over R and RP; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended; the owner answered "all recommended" on 2026-10-01).

1. **[owner-visible] The no-praise rule, worded** (owner answer 1). The contract's last sentence "Give a card an empty notes list when it is fine." becomes "A note is only for something to change. Never praise or describe what already works. If a prayer is fine, give it no notes: its notes list is empty." The role already says the editor points out problems. Nothing in code inspects a note for praise.
2. **[owner-visible] The firmer "do not repeat" line** (owner answer 5). `CODE_NOTES_INTRO` becomes "Notes already found by code. The pastor sees them already, so do not repeat them or make the same point in other words", then, in brackets, only the points these code notes invite, after "for example, a note " and joined by ", or ": "on citing or naming scripture on a card that already has a Cites note" when a card has a code "Cites …" note (`CITES_PREFIX`), and "on prayers that open alike" when a code note across the service names an opening; with neither (say, only a stock-phrase note) there are no brackets; then ":" (`code_notes_intro`). So the AI is never told about a citation or an opening the service does not have. It still comes only when there are code notes.
3. **[owner-visible] Which restated citation notes go** (owner answer 5). Only on a card that has a code "Cites …" note, and only AI notes tagged `rules`, matching (any case) `\b(?:cit(?:e|es|ed|ing|ation)s?|nam(?:e|es|ed|ing)\s+(?:the\s+)?(?:reading|passage|scripture|text)s?|scripture\s+references?)\b`: "cite(s/d)", "citing", "citation(s)", "name(s/d)/naming (the) reading/passage/scripture/text(s)", "scripture reference(s)". "Recites", "excited" and "Names God only as Father" do not match; a `theology` note that mentions citing is kept. The whole-word repeat rule of RP clarification 11 still runs after it.
4. **[owner-visible] Which restated opening notes go** (owner answer 5). Only on a card whose opening words are the words of a code "Several prayers open with …" note (the same key as `check_openings`: the first two words after any "Leader:"/"People:" label, any case), and only AI notes tagged `repetition` that either speak of how the prayer opens or quote the opening words. "Speak of how it opens" (`speaks_of_opening`): once the section names (`SECTION_LABELS`, any case, so "the Opening Prayer") are taken out of the note, it matches (any case) `\b(?:opens?|opened|opening|begins?|beginning|began|starts?|started|starting)\s+(?:with|like|alike|the\s+same|as)\b`: "Opens like …", "Begins the same way as …", "both begin alike". A repetition note about something else on that card is kept ("Repeats "mercy" four times.", "Repeats "mercy" from the Opening Prayer.", ""Open our hearts" also appears in the Confession.", "Echoes the Opening Prayer word for word in its last line.", "Starts and ends with the same petition."): narrower than "drop AI repetition notes on that card", so a real repetition point inside one prayer is not lost. Across the service, when a code note names a shared opening, an AI `repetition` note there that speaks of prayers opening alike ("The Call to Worship and Opening Prayer both begin alike.") is dropped the same way, before `merge_notes`; one quoting the opening was already dropped (RP clarification 11).
5. **[owner-visible] What fades and what goes** (owner answer 4). Faded, under "From before your last edit.": typing, Undo, "Use church default", another tab's edit (any change to the text or the origin, as before). Gone: a successful Regenerate or Generate (its new draft replaced the text the notes were about), a successful Revise (it addressed them), Clear text (a blank card shows no notes; Undo of Clear does not bring them back), New service. A card that showed "Looks good.", or whose notes were all dismissed, shows nothing after an edit. Once faded, a card stays faded until the next Review, even when Undo puts back the exact words that were reviewed. A failed or cancelled Regenerate or Revise leaves the text, so the notes stay as they were. Undo after a successful Revise or Regenerate brings the text back without the notes (they went with the revision or the new draft; the next Review brings fresh ones). Another tab's Regenerate or Revise reaches this tab as an edit, so here the card's notes fade under the same line instead of going: accepted (this tab cannot tell another tab's AI draft from its typing); a possible later follow-up.
6. **[owner-visible] "Across the service" is unchanged:** it stays, at full strength, until the next Review, its own dismiss or New service, since its notes are about several prayers.
7. **The in-flight rule stays** (RP clarification 20): a card changed while a review was running gets no notes from that review. The member edited it before seeing any notes, so nothing would fade, and "From before your last edit." would be wrong for notes they never saw; the next Review is one tap.
8. **[owner-visible] Revise on a faded card** sends the card's current text and the notes left (as before: the notes the member has not dismissed). It is offered whenever `canRevise` holds, faded or not.
9. **Screen readers** (F §4.9). "From before your last edit." is plain text inside the card's notes block, before the list, so it is read with the notes and is part of the textarea's description (`aria-describedby`, as the notes already are). It is not a live region: it appears as the member types, and announcing it then would interrupt every edit. The list keeps its name "Notes on {Label}" and, while faded, is described by the line (`aria-describedby` on the list, pointing at the line's id), so a screen reader that moves to the list hears why the notes are dimmed.
10. **How the screen knows a draft was written.** The review provider is inside the generation provider, so the generation provider gains `onWritten(listener)`, called with the card's key whenever an AI draft is applied (Generate, Regenerate, Try again); the review provider subscribes and calls `forgetCard`. Revise calls `forgetCard` itself after its draft lands. Pruning still runs during render, so faded notes never show a frame unfaded; `forgetCard` then removes them in the same update. Owner decision 1.
11. **[owner-visible] Revise's eligibility** (owner answers 2, 3). `canRevise`: the card has text after trimming, at least one note left, and its origin is "ai", "typed" or "archive"; never "default" (a Benediction following the church default) or "empty". The confirm shows exactly when `needsRegenerateConfirm(card)` is true (typed or archive text), so AI text revises at once as before.
12. **[owner-visible] The dialog's other button** is "Keep my text", Regenerate's approved label (the owner gave the title, the description and the confirm). Focus mirrors Regenerate: "Keep my text" (or Escape) returns to **Revise with these notes**; "Revise text" starts the revision and the closing dialog sends focus to its Cancel (the Revise button, or the card's heading, if it did not start). If the notes change while it asks (another tab edits or clears the card, a new review), the dialog closes without revising: it closes whenever Revise is no longer offered or the review it was opened on is replaced, and focus goes to Revise if it is still there, else the card's heading. The dialog is rendered in every branch of `CardNotes`, after the notes, so it stays mounted as the notes go.
13. **[owner-visible] After Revise on your text** the card's chip reads "AI draft" (the text is now the AI's, as after Regenerate) and the line "Revised with these notes. Undo" shows; Undo brings your text back with its "Your text" chip.
14. **The backend needed no change for Revise on typed text:** `ReviseIn` and `revise_section` take the section, text and notes only, with no origin. The `ai` bucket and the 100 s client timeouts are unchanged.
15. **Docs** (owner answer 6). T5 rewrites `docs/manual-verification.md` "Service reviewer" items 4 and 5 and adds item 9, marked "(owner, after follow-up 1)"; no `##` heading changes, so `test_slice1_docs.py`'s pin is unchanged. R gains a short amendment. The runbook record is T7's records step.

### Risks
- **The model may still praise.** The contract rule is the owner's chosen fix; T7's phone check looks at a real review. If praise persists, a follow-up can strengthen the role, never a code filter (owner answer 1).
- **The restated-note patterns are conservative by design:** some restatements will still get through (a note tagged `theology` about citing, or wording the patterns do not catch). They never drop a code note.

## File Structure

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/usecases/liturgy_review.py` (+ `backend/tests/test_usecase_liturgy_review.py`) | `CONTRACT`, `CODE_NOTES_INTRO`, `code_notes_intro` (T1); `drop_restated`, `speaks_of_opening`, their patterns, and their use in `review_service` (T2); the module docstring on `revise_section` (T4) | T1, T2, T4 |
| `frontend/src/lib/liturgy/notes.ts` (+ `.test.ts`) | `STALE_LINE`, `CardReview.stale`, `pruneReview` fades, `forgetCard` (T3); `canRevise` (T4) | T3, T4 |
| `frontend/src/lib/liturgy/generation.tsx` | `onWritten` | T3 |
| `frontend/src/lib/liturgy/review.tsx` (+ `review.test.tsx`) | forget on Regenerate and Revise (T3); docs of `revise` (T4) | T3, T4 |
| `frontend/src/components/builder/liturgy/card-notes.tsx` | the faded notes, the line and the list's description (T3); the confirm (T4) | T3, T4 |
| `frontend/src/components/builder/liturgy/review-step.test.tsx` | DOM cases | T3, T4 |
| `docs/manual-verification.md`, `docs/superpowers/specs/2026-09-26-service-reviewer-design.md` | items 4, 5, 9; R's amendment | T5 |
| `docs/ops-runbook.md` | "Reviewer follow-up 1 record" (the records PR, after the merge) | T7 |

**Created:** this plan only. **Counts:** 1 created and 11 modified in the PR, 12 paths. **Untouched:** routes, `api/schemas.py`, the OpenAPI files, migrations, `review_checks.py`, `section-card.tsx`, `cards.ts`, Streamlit.

**Task order and review batch:** T1 → T5, each one commit and a backup push; then one review of the whole batch (backend prompt and filter; the notes' rules, the provider, the card; the docs) with its fixes as `Fix: …` commits; T6 verifies and opens the draft PR on the owner's yes; T7 merges on the owner's yes, runs the phone check and writes the record.

---

### Task 1: No praise notes, and a firmer "do not repeat" (owner answers 1, 5; clarifications 1, 2)

**Files:**
- Modify: `backend/usecases/liturgy_review.py`, `backend/tests/test_usecase_liturgy_review.py`

- [ ] **Step 1 (agent): Write the failing test**

**In `backend/tests/test_usecase_liturgy_review.py`, replace:**

````python
    assert user.endswith("Notes already found by code. Do not repeat them:\n"
````

**with:**

````python
    assert user.endswith(liturgy_review.CODE_NOTES_INTRO + " (for example, a note on prayers that open alike):\n" +
````

**Append to `backend/tests/test_usecase_liturgy_review.py`:**

````python


# --- reviewer follow-up 1 (owner answers 2026-10-01): no praise notes, no restated code notes ---

NO_PRAISE = ("A note is only for something to change. Never praise or describe what already works. "
             "If a prayer is fine, give it no notes")


def test_the_prompt_asks_for_no_praise_and_no_restated_code_notes(church):
    intro = ("Notes already found by code. The pastor sees them already, so do not repeat them or make the same "
             "point in other words")
    ai = FakeAI(reply=answer())
    run(church, cards=CARDS[:1], ai=ai)                 # only a stock-phrase note: nothing in brackets
    system, user = (m["content"] for m in ai.calls[0]["messages"])
    assert NO_PRAISE in system and "Give a card an empty notes list when it is fine." not in system
    assert user.endswith(f"{intro}:\n- call_to_worship: {STOCK}")
    # A Cites note and a shared opening: the brackets name both.
    ai = FakeAI(reply=answer())
    run(church, cards=[*CARDS, ReviewCard("assurance", "ai", "As John 21:1-19 tells, you are forgiven.")], ai=ai)
    user = ai.calls[0]["messages"][1]["content"]
    assert (f"{intro} (for example, a note on citing or naming scripture on a card that already has a Cites "
            f"note, or on prayers that open alike):\n- call_to_worship: {STOCK}\n- assurance: Cites John 21:1-19.") in user
````

- [ ] **Step 2 (agent): Run it and see it fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy_review.py 2>&1 | tail -3
```

**Expected:** `FAILED backend/tests/test_usecase_liturgy_review.py::test_the_prompt_carries_the_church_s_rules_present_checklists_profile_and_code_notes` (the code-notes line has no brackets yet), `FAILED backend/tests/test_usecase_liturgy_review.py::test_the_prompt_asks_for_no_praise_and_no_restated_code_notes` (the contract has no such rule yet), then `2 failed, 12 passed in <t>s`.

- [ ] **Step 3 (agent): The contract, and the code-notes line built from the code notes present**

**In `backend/usecases/liturgy_review.py`, replace:**

````python
    "Each note is one sentence of 240 characters or fewer that names the specific phrase at issue. "
    "Give a card an empty notes list when it is fine."
)
````

**with:**

````python
    "Each note is one sentence of 240 characters or fewer that names the specific phrase at issue. "
    "A note is only for something to change. Never praise or describe what already works. "
    "If a prayer is fine, give it no notes: its notes list is empty."
)
````

**In `backend/usecases/liturgy_review.py`, replace:**

````python
CODE_NOTES_INTRO = "Notes already found by code. Do not repeat them:\n"
````

**with:**

````python
CODE_NOTES_INTRO = ("Notes already found by code. The pastor sees them already, so do not repeat them or make "
                    "the same point in other words")
CITES_PREFIX = review_checks.CITES_NOTE.split("{match}", 1)[0]          # "Cites "
RESTATED_CITING = "on citing or naming scripture on a card that already has a Cites note"
RESTATED_OPENING = "on prayers that open alike"
````

**In `backend/usecases/liturgy_review.py`, replace:**

````python
def _readings(scriptures: Sequence[str]) -> str:
````

**with:**

````python
def code_notes_intro(code_notes: Mapping[str, Sequence[Note]], service_notes: Sequence[Note]) -> str:
    """CODE_NOTES_INTRO, naming in brackets only the restatements these code notes invite: citing, when a card
    has a "Cites ..." note; openings, when a note across the service names one (reviewer follow-up 1)."""
    cites = any(n.text.startswith(CITES_PREFIX) for notes in code_notes.values() for n in notes)
    points = [point for point, present in ((RESTATED_CITING, cites), (RESTATED_OPENING, bool(service_notes)))
              if present]
    return CODE_NOTES_INTRO + (f" (for example, a note {', or '.join(points)})" if points else "") + ":\n"


def _readings(scriptures: Sequence[str]) -> str:
````

**In `backend/usecases/liturgy_review.py`, replace:**

````python
            CODE_NOTES_INTRO + "\n".join(noted) if noted else "",
````

**with:**

````python
            code_notes_intro(code_notes, service_notes) + "\n".join(noted) if noted else "",
````

- [ ] **Step 4 (agent): Run the file and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy_review.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `14 passed in <t>s` (the budget test still drops what it did: the prompt grew by less than 250 characters); `1218 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/usecases/liturgy_review.py backend/tests/test_usecase_liturgy_review.py
git commit -q -m "Reviewer: notes only for something to change, and code notes not restated (follow-up 1; owner answers 1, 5)" -m "The review's output contract now says a note is only for something to
change, never praise or a description of what works, and a fine prayer
gets no notes. The code-notes line asks the AI not to make the same point
in other words, naming in brackets only what these code notes invite
(citing scripture when a card has a Cites note, prayers that open alike
when a note across the service names an opening)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 1: backend **1218 passed, 11 skipped**; frontend **570 in 78**.

### Task 2: Drop AI notes that restate a code note (owner answer 5; clarifications 3, 4)

**Files:**
- Modify: `backend/usecases/liturgy_review.py`, `backend/tests/test_usecase_liturgy_review.py`

**Interfaces:**
- Consumes: `CITES_PREFIX` (T1).
- Produces: `liturgy_review.drop_restated(code, ai, *, opening="") -> list[Note]`, `speaks_of_opening(text) -> bool`, `RESTATES_CITING`, `RESTATES_OPENING`, `SECTION_NAMES`.

- [ ] **Step 1 (agent): Write the failing tests**

**Append to `backend/tests/test_usecase_liturgy_review.py`:**

````python


def test_ai_notes_that_restate_a_code_note_in_other_words_are_dropped():
    cites = [Note("rules", "Cites John 21:1-19. Draw on the reading's themes without naming it.", match="John 21:1-19")]
    stock = [Note("rules", STOCK, match="as we journey")]
    cases = [
        # (code notes, the card's shared opening, the AI note, kept?)
        (cites, "", ("rules", "Cites the Gospel directly; draw on its themes."), False),
        (cites, "", ("rules", "Names the reading outright."), False),
        (cites, "", ("rules", "Naming the passages breaks the church's rule."), False),
        (cites, "", ("rules", "Drop the scripture reference in the second line."), False),
        (cites, "", ("rules", "The citation of John should go."), False),
        (cites, "", ("theology", "Cites the Gospel to prove a point."), True),       # another tag: kept
        (cites, "", ("rules", "Recites a long list of attributes."), True),         # not "cite"
        (cites, "", ("rules", "Names God only as Father."), True),
        (stock, "", ("rules", "Names the reading outright."), True),                # no Cites note on this card
        ([], "Gracious God", ("repetition", "Opens like the Opening Prayer."), False),
        ([], "Gracious God", ("repetition", "Begins the same way as the Confession."), False),
        ([], "Gracious God", ("repetition", '"gracious god" again, as in the Confession.'), False),
        ([], "Gracious God", ("repetition", 'Repeats "mercy" four times.'), True),   # not about the opening
        ([], "Gracious God", ("repetition", 'Repeats "mercy" from the Opening Prayer.'), True),   # a section's name
        ([], "Gracious God", ("repetition", '"Open our hearts" also appears in the Confession.'), True),
        ([], "Gracious God", ("repetition", "Echoes the Opening Prayer word for word in its last line."), True),
        ([], "Gracious God", ("repetition", "Starts and ends with the same petition."), True),
        ([], "Gracious God", ("theology", "Opens with a request before any praise."), True),
        ([], "", ("repetition", "Opens like the Opening Prayer."), True),          # its opening is not shared
    ]
    for code, opening, (tag, text), kept in cases:
        note = Note(tag, text, "ai")
        assert (liturgy_review.drop_restated(code, [note], opening=opening) == [note]) is kept, text


ALIKE = ("repetition", "The Call to Worship and Opening Prayer both begin alike.")


def test_the_review_drops_restated_citation_and_opening_notes(church):
    cards = [ReviewCard("call_to_worship", "ai", "Gracious God, we gather."),
             ReviewCard("opening_prayer", "ai", "Gracious God, as John 21:1-19 tells, you call us. Amen."),
             ReviewCard("offertory_prayer", "ai", "Holy One, receive these gifts.")]
    reply = answer([
        ("call_to_worship", [("repetition", "Opens the same way as the Opening Prayer.")]),
        ("opening_prayer", [("rules", "Names the reading; let its themes speak instead."),
                            ("repetition", '"Gracious God" again.'), ("read_aloud", "The second clause is long.")]),
        ("offertory_prayer", [("repetition", "Starts like no other prayer, which is fine but abrupt."),
                              ("rules", "Names the reading outright.")]),
    ], service=[ALIKE])
    outcome = run(church, cards=cards, ai=FakeAI(reply=reply))
    assert notes_of(outcome) == {
        "call_to_worship": [],
        "opening_prayer": [("rules", "Cites John 21:1-19. Draw on the reading's themes without naming it.", "code"),
                           ("read_aloud", "The second clause is long.", "ai")],
        "offertory_prayer": [("repetition", "Starts like no other prayer, which is fine but abrupt.", "ai"),
                             ("rules", "Names the reading outright.", "ai")],     # no code note here: kept
    }
    assert [n.text for n in outcome.service_notes] == ['Several prayers open with "Gracious God".']
    # With no shared opening found by code, the AI's note across the service on prayers that open alike stays.
    apart = [ReviewCard("call_to_worship", "ai", "Come, let us worship."), *cards[1:]]
    outcome = run(church, cards=apart, ai=FakeAI(reply=answer(service=[ALIKE])))
    assert [(n.text, n.source) for n in outcome.service_notes] == [(ALIKE[1], "ai")]
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy_review.py 2>&1 | tail -3
```

**Expected:** `FAILED backend/tests/test_usecase_liturgy_review.py::test_ai_notes_that_restate_a_code_note_in_other_words_are_dropped` (no `drop_restated` yet), `FAILED backend/tests/test_usecase_liturgy_review.py::test_the_review_drops_restated_citation_and_opening_notes` (the restated notes are kept), then `2 failed, 14 passed in <t>s`.

- [ ] **Step 3 (agent): `drop_restated`, and run it before the merge**

**In `backend/usecases/liturgy_review.py`, replace:**

````python
   whole words (any whitespace between them) dropped, at most 3 per card and
   3 across the service.
````

**with:**

````python
   whole words (any whitespace between them) dropped, at most 3 per card and
   3 across the service. Before it, `drop_restated` drops an AI note that
   makes a code note's point in other words (owner answer 5 of 2026-10-01):
   a rules note on citing or naming scripture on a card with a "Cites" note,
   and a repetition note on how the prayer opens on a card whose opening a
   code note across the service names (or, across the service, on prayers
   that open alike when that code note is there).
````

**In `backend/usecases/liturgy_review.py`, replace:**

````python
def review_service(*, church_id: uuid.UUID, user_id: uuid.UUID, occasion: str, scriptures: Sequence[str],
````

**with:**

````python
# An AI note that makes a code note's point in other words (owner answer 5 of 2026-10-01). Conservative: only a
# rules note that speaks of citing or naming scripture, on a card with a code "Cites ..." note, and only a
# repetition note that speaks of how the prayer opens ("opens with", "begins like", "starts the same" ...; the
# section names are taken out first, so "the Opening Prayer" is not about opening) or quotes its opening, on a
# card whose opening is in a code "Several prayers open with ..." note; across the service, a repetition note
# about prayers that open alike when that code note is there.
RESTATES_CITING = re.compile(
    r"\b(?:cit(?:e|es|ed|ing|ation)s?|nam(?:e|es|ed|ing)\s+(?:the\s+)?(?:reading|passage|scripture|text)s?"
    r"|scripture\s+references?)\b",
    re.IGNORECASE,
)
RESTATES_OPENING = re.compile(
    r"\b(?:opens?|opened|opening|begins?|beginning|began|starts?|started|starting)"
    r"\s+(?:with|like|alike|the\s+same|as)\b",
    re.IGNORECASE,
)
SECTION_NAMES = re.compile(
    r"\b(?:" + "|".join(re.escape(label) for label in sorted(SECTION_LABELS.values(), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def speaks_of_opening(text: str) -> bool:
    """True when a note speaks of how a prayer opens, once the section names are taken out of it."""
    return RESTATES_OPENING.search(SECTION_NAMES.sub(" ", text)) is not None


def drop_restated(code: Sequence[Note], ai: Sequence[Note], *, opening: str = "") -> list[Note]:
    """The card's AI notes without those that restate its code notes in other words. `opening` is the
    card's opening words when a code note across the service already names them, else ""."""
    cites = any(n.text.startswith(CITES_PREFIX) for n in code)
    words = opening.split()
    quoted = (re.compile(r"(?<!\w)" + r"\s+".join(map(re.escape, words)) + r"(?!\w)", re.IGNORECASE)
              if words else None)

    def restated(note: Note) -> bool:
        if cites and note.tag == "rules" and RESTATES_CITING.search(note.text):
            return True
        return (quoted is not None and note.tag == "repetition"
                and (speaks_of_opening(note.text) or quoted.search(note.text) is not None))

    return [n for n in ai if not restated(n)]


def review_service(*, church_id: uuid.UUID, user_id: uuid.UUID, occasion: str, scriptures: Sequence[str],
````

**In `backend/usecases/liturgy_review.py`, replace:**

````python
    outcome = ReviewOutcome(
        cards=tuple(CardNotes(key, merge_notes(code[key], ai_notes[key], MAX_NOTES_PER_CARD)) for key in sections),
        service_notes=merge_notes(code_service, ai_service, MAX_SERVICE_NOTES),
````

**with:**

````python
    shared = {n.match.lower() for n in code_service}                 # the openings already named across the service
    openings = {c.section: " ".join(review_checks.opening_words(c.text)) for c in cards}
    kept = {key: drop_restated(code[key], ai_notes[key],
                               opening=openings[key] if openings[key].lower() in shared else "") for key in sections}
    # Across the service, a note on prayers that open alike restates the code note that names the opening.
    across = [n for n in ai_service if not (code_service and n.tag == "repetition" and speaks_of_opening(n.text))]
    outcome = ReviewOutcome(
        cards=tuple(CardNotes(key, merge_notes(code[key], kept[key], MAX_NOTES_PER_CARD)) for key in sections),
        service_notes=merge_notes(code_service, across, MAX_SERVICE_NOTES),
````

- [ ] **Step 4 (agent): Run the file three times, the import gate and the suite**

```bash
for i in 1 2 3; do .venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy_review.py 2>&1 | tail -1; done
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/usecases/liturgy_review.py; echo "imports grep exit $?"
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `16 passed in <t>s` three times; `imports grep exit 1`; `1220 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/usecases/liturgy_review.py backend/tests/test_usecase_liturgy_review.py
git commit -q -m "Reviewer: drop AI notes that restate a code note (follow-up 1; owner answer 5)" -m "On a card with a code Cites note, an AI rules note about citing or naming
scripture is dropped; on a card whose opening a code note across the
service names, an AI repetition note about how it opens, or quoting the
opening, is dropped, and so is an AI note across the service on prayers
that open alike. Section names are taken out before matching, so a note
naming the Opening Prayer is kept. Conservative patterns, table-tested;
code notes are never dropped." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 2: backend **1220 passed, 11 skipped**; frontend **570 in 78**.

### Task 3: Faded notes after an edit (owner answer 4; clarifications 5-10)

**Files:**
- Modify: `frontend/src/lib/liturgy/notes.ts`, `frontend/src/lib/liturgy/notes.test.ts`, `frontend/src/lib/liturgy/generation.tsx`, `frontend/src/lib/liturgy/review.tsx`, `frontend/src/lib/liturgy/review.test.tsx`, `frontend/src/components/builder/liturgy/card-notes.tsx`, `frontend/src/components/builder/liturgy/review-step.test.tsx`

**Interfaces:**
- Produces: `notes.STALE_LINE`, `CardReview.stale: boolean`, `pruneReview` (fades), `forgetCard(review, key)`; `LiturgyGeneration.onWritten(listener) => unsubscribe`; `NoteList`'s `faded` and `describedBy` props.

- [ ] **Step 1 (agent): Write the failing tests**

**In `frontend/src/lib/liturgy/notes.test.ts`, replace:**

````ts
 * the text changes"; slice 4 spec, reviewer amendment Testing): stale results
 * dropped by text and origin, notes cleared by any change, dismiss, "Looks
 * good." and when Revise is offered.
````

**with:**

````ts
 * the text changes"; slice 4 spec, reviewer amendment Testing; reviewer
 * follow-up 1): stale results dropped by text and origin, notes faded by any
 * later change and dropped by a new draft, dismiss, "Looks good." and when
 * Revise is offered.
````

**In `frontend/src/lib/liturgy/notes.test.ts`, replace:**

````ts
import { applyReview, canRevise, captureReview, dismissNote, noteCount, pruneReview } from "./notes";
````

**with:**

````ts
import { applyReview, canRevise, captureReview, dismissNote, forgetCard, noteCount, pruneReview } from "./notes";
````

**In `frontend/src/lib/liturgy/notes.test.ts`, replace:**

````ts
    expect(review?.cards.benediction).toEqual({ reviewed: { text: "Go in peace.", origin: "default" }, notes: [], found: 0 });
````

**with:**

````ts
    expect(review?.cards.benediction).toEqual({ reviewed: { text: "Go in peace.", origin: "default" }, notes: [], found: 0, stale: false });
````

**In `frontend/src/lib/liturgy/notes.test.ts`, replace:**

````ts
  it("clears a card's notes when its text or origin changes, and every note when the service changes", () => {
    const d = reviewed();
    const { review } = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER);
    expect(pruneReview(review, d)).toBe(review);                                    // nothing changed: the same object
    const changes: [string, DraftV1][] = [
      ["typing", editCardText(d, "opening_prayer", "Gracious God, hear us!")],
      ["Regenerate or Revise", applyGenerated(d, "opening_prayer", "A new draft.")],
      ["Clear text", clearCard(d, "opening_prayer")],
    ];
    for (const [what, next] of changes) {
      const pruned = pruneReview(review, next);
      expect(Object.keys(pruned?.cards ?? {}), what).toEqual(["call_to_worship", "benediction"]);
      expect(pruned?.service, what).toHaveLength(1);
    }
    // "Use church default" with the same words still changes the origin.
````

**with:**

````ts
  it("fades a card's notes when its text or origin changes, drops a blank or noteless card's, and every note when the service changes", () => {
    const d = reviewed();
    const { review } = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER);
    expect(pruneReview(review, d)).toBe(review);                                    // nothing changed: the same object
    const changes: [string, DraftV1][] = [
      ["typing", editCardText(d, "opening_prayer", "Gracious God, hear us!")],
      ["another tab, or an Undo", withText(d, "opening_prayer", "Gracious God, hear us all.", "ai")],
      ["only the origin", withText(d, "opening_prayer", "Gracious God, hear us.", "typed")],
    ];
    for (const [what, next] of changes) {
      const pruned = pruneReview(review, next);
      expect(pruned?.cards.opening_prayer, what).toEqual({ ...review?.cards.opening_prayer, stale: true });
      expect(pruned?.cards.call_to_worship?.stale, what).toBe(false);
      expect(pruned?.service, what).toHaveLength(1);
      // Faded until the next review, even back at the reviewed words.
      const back = pruneReview(pruned, d);
      expect(back?.cards.opening_prayer?.stale, what).toBe(true);
      expect(pruneReview(back, d), what).toBe(back);
    }
    // Clear text: a blank card shows no notes; "Looks good." and a card with every note dismissed go after any edit.
    expect(Object.keys(pruneReview(review, clearCard(d, "opening_prayer"))?.cards ?? {})).toEqual(["call_to_worship", "benediction"]);
    expect(pruneReview(review, editCardText(d, "benediction", "Go in peace!"))?.cards.benediction).toBeUndefined();
    const dismissed = dismissNote(review!, "call_to_worship", "call_to_worship-0");
    expect(pruneReview(dismissed, editCardText(d, "call_to_worship", "Come."))?.cards.call_to_worship).toEqual({
      ...dismissed.cards.call_to_worship,
      stale: true,
    });
    const none = dismissNote(dismissed, "call_to_worship", "call_to_worship-1");
    expect(pruneReview(none, editCardText(d, "call_to_worship", "Come."))?.cards.call_to_worship).toBeUndefined();
    // "Use church default" with the same words still changes the origin.
````

**In `frontend/src/lib/liturgy/notes.test.ts`, replace:**

````ts
  it("offers Revise only on an AI card with a note left", () => {
````

**with:**

````ts
  it("forgets a card's notes after a new AI draft or a revision lands; a faded AI card can still be revised", () => {
    const d = reviewed();
    const review = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER).review!;
    const written = applyGenerated(d, "opening_prayer", "A new draft.");
    const forgotten = forgetCard(pruneReview(review, written), "opening_prayer");
    expect(Object.keys(forgotten?.cards ?? {})).toEqual(["call_to_worship", "benediction"]);
    expect(forgotten?.service).toHaveLength(1);
    expect(forgetCard(review, "assurance")).toBe(review);
    expect(forgetCard(null, "opening_prayer")).toBeNull();
    const elsewhere = withText(d, "opening_prayer", "Gracious God, hear us all.", "ai");
    const faded = pruneReview(review, elsewhere)!;
    expect(canRevise(elsewhere.liturgy.cards.opening_prayer, faded.cards.opening_prayer)).toBe(true);
  });

  it("offers Revise only on an AI card with a note left", () => {
````

**In `frontend/src/lib/liturgy/review.test.tsx`, replace:**

````tsx
    const shown = notes === undefined ? "none" : notes.notes.map((n) => n.text).join(" | ") || "looks good";
````

**with:**

````tsx
    const shown = notes === undefined ? "none" : `${notes.stale ? "faded " : ""}${notes.notes.map((n) => n.text).join(" | ") || "looks good"}`;
````

**In `frontend/src/lib/liturgy/review.test.tsx`, replace:**

````tsx
    expect(await screen.findByText("Kept your edits, so the revised draft for Opening Prayer was not used.")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: My own words\. \[typed\] notes none; revising no;/)).toBeInTheDocument();

    act(() => draftHandle.current?.update((d) => card(d, "opening_prayer", "Holy One, as we journey.", "ai")));
````

**with:**

````tsx
    expect(await screen.findByText("Kept your edits, so the revised draft for Opening Prayer was not used.")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: My own words\. \[typed\] notes faded Stock phrase .* \| The prayer runs long\.; revising no;/)).toBeInTheDocument();

    act(() => draftHandle.current?.update((d) => card(d, "opening_prayer", "Holy One, as we journey.", "ai")));
````

**In `frontend/src/lib/liturgy/review.test.tsx`, replace:**

````tsx
    act(() => loads[1]());
    expect(await screen.findByText("Kept your edits, so the revised draft for Opening Prayer was not used.")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: My own words\. \[typed\] notes none; revising no;/)).toBeInTheDocument();
````

**with:**

````tsx
    act(() => loads[1]());
    expect(await screen.findByText("Kept your edits, so the revised draft for Opening Prayer was not used.")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: My own words\. \[typed\] notes faded Stock phrase .* \| The prayer runs long\.; revising no;/)).toBeInTheDocument();
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
const QUICK = "Only quick checks ran. The full review isn't available right now.";
````

**with:**

````tsx
const QUICK = "Only quick checks ran. The full review isn't available right now.";
const STALE = "From before your last edit.";
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
  it("clears a card's notes when it is typed in, regenerated, cleared or set to the church default", async () => {
````

**with:**

````tsx
  it("fades a card's notes when it is typed in or set to the church default, and drops them when it is regenerated or cleared", async () => {
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
    // Typing.
    await user.type(screen.getByRole("textbox", { name: "Call to Worship" }), "!");
    expect(within(card("Call to Worship")).queryByText("About call_to_worship.")).toBeNull();
    // Regenerate on an AI card (no confirm), once its new draft lands.
````

**with:**

````tsx
    // Typing: the notes stay, dimmed, under "From before your last edit.".
    await user.type(screen.getByRole("textbox", { name: "Call to Worship" }), "!");
    expect(within(card("Call to Worship")).getByText(STALE)).toBeInTheDocument();
    expect(within(card("Call to Worship")).getByText("About call_to_worship.")).toHaveClass("text-muted-foreground");
    // Regenerate on an AI card (no confirm): its notes go once its new draft lands.
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
    // Clear text.
    await user.click(within(card("Prayer of Confession")).getByRole("button", { name: "More actions for Prayer of Confession" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    expect(within(card("Prayer of Confession")).queryByText("About prayer_of_confession.")).toBeNull();
    // Use church default.
    await user.click(within(card("Benediction")).getByRole("button", { name: "More actions for Benediction" }));
    await user.click(await screen.findByRole("menuitem", { name: "Use church default" }));
    expect(within(card("Benediction")).queryByText("About benediction.")).toBeNull();
    expect(within(card("Opening Prayer")).getByText("About opening_prayer.")).toBeInTheDocument(); // untouched
  });
````

**with:**

````tsx
    // Clear text: a blank card shows no notes.
    await user.click(within(card("Prayer of Confession")).getByRole("button", { name: "More actions for Prayer of Confession" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    expect(within(card("Prayer of Confession")).queryByText("About prayer_of_confession.")).toBeNull();
    // Use church default: the notes fade.
    await user.click(within(card("Benediction")).getByRole("button", { name: "More actions for Benediction" }));
    await user.click(await screen.findByRole("menuitem", { name: "Use church default" }));
    expect(within(card("Benediction")).getByText("About benediction.")).toBeInTheDocument();
    expect(within(card("Benediction")).getByText(STALE)).toBeInTheDocument();
    expect(within(card("Opening Prayer")).getByText("About opening_prayer.")).toBeInTheDocument(); // untouched
    expect(within(card("Opening Prayer")).queryByText(STALE)).toBeNull();
  });

  it("keeps faded notes readable and dismissable, drops Looks good. after an edit, and a new review replaces them", async () => {
    const { user } = renderStep();
    await review(user);
    const opening = card("Opening Prayer");
    await user.type(screen.getByRole("textbox", { name: "Opening Prayer" }), " Amen.");
    expect(within(opening).getByText(STALE)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveAccessibleDescription(expect.stringContaining(STALE));
    expect(within(opening).getByRole("list", { name: "Notes on Opening Prayer" })).toHaveAccessibleDescription(STALE);
    expect(within(opening).getByText(STOCK)).toHaveClass("text-muted-foreground");
    await user.click(within(opening).getByRole("button", { name: `Dismiss note: ${STOCK}` }));
    expect(within(opening).getByRole("button", { name: "Dismiss note: The second clause is hard to say aloud." })).toHaveFocus();
    expect(within(opening).getByText(STALE)).toBeInTheDocument();
    // "Looks good." goes after any edit, and the card shows nothing until the next review.
    await user.type(screen.getByRole("textbox", { name: "Benediction" }), "!");
    expect(within(card("Benediction")).queryByText("Looks good.")).toBeNull();
    expect(within(card("Benediction")).queryByText(STALE)).toBeNull();
    // "Across the service" stays until the next review.
    expect(screen.getByRole("region", { name: "Across the service" })).toBeInTheDocument();
    // The second review announces the same words as the first, so wait for the faded notes to go.
    await user.click(reviewButton());
    await waitFor(() => expect(screen.queryByText(STALE)).toBeNull());
    expect(within(opening).getByText(STOCK)).not.toHaveClass("text-muted-foreground");
    expect(within(card("Benediction")).getByText("Looks good.")).toBeInTheDocument();
  });
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
  it("keeps Cancel while a one-note card revises, with its × off, even when another tab's edit drops the notes", async () => {
````

**with:**

````tsx
  it("keeps Cancel while a one-note card revises, with its × off, even when another tab's edit fades the notes", async () => {
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
    // Another tab edits the card: its notes go, the revision's Cancel stays.
````

**with:**

````tsx
    // Another tab edits the card: its notes fade, the revision's Cancel stays.
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
    await waitFor(() => expect(within(assurance).queryByRole("list", { name: "Notes on Assurance of Pardon" })).toBeNull());
````

**with:**

````tsx
    expect(await within(assurance).findByText(STALE)).toBeInTheDocument();
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/notes.test.ts src/lib/liturgy/review.test.tsx src/components/builder/liturgy/review-step.test.tsx 2>&1 | grep -E "^ +× |Tests ")
```

**Expected:** these eight lines (order may vary; the `stale` field, `forgetCard` and the line do not exist yet), then `⎯⎯⎯⎯⎯⎯⎯ Failed Tests 8 ⎯⎯⎯⎯⎯⎯⎯` and `      Tests  8 failed | 21 passed (29)`:
```
   × the reviewer's notes (R Notes) > keeps the notes of each card that still holds what was reviewed, and drops the rest or the whole review
   × the reviewer's notes (R Notes) > fades a card's notes when its text or origin changes, drops a blank or noteless card's, and every note when the service changes
   × the reviewer's notes (R Notes) > forgets a card's notes after a new AI draft or a revision lands; a faded AI card can still be revised
   × Revise with these notes (R Revise) > keeps a card edited meanwhile, and shows why a revision failed
   × Revise with these notes (R Revise) > checks again once the sermon text has loaded: a card changed meanwhile is left out of the review, and its revision sends nothing
   × Review service (R User experience) > fades a card's notes when it is typed in or set to the church default, and drops them when it is regenerated or cleared
   × Review service (R User experience) > keeps faded notes readable and dismissable, drops Looks good. after an edit, and a new review replaces them
   × Revise with these notes (R Revise) > keeps Cancel while a one-note card revises, with its × off, even when another tab's edit fades the notes
```

- [ ] **Step 3 (agent): The notes' rules**

**In `frontend/src/lib/liturgy/notes.ts`, replace:**

````ts
 * - `pruneReview` runs on every draft change: a card whose text or origin no
 *   longer matches what was reviewed loses its notes (typing, Regenerate,
 *   Revise, Clear text, "Use church default", Undo, another tab's edit), and
 *   a new service loses the whole review.
 * - "Looks good." shows for a card that was reviewed and came back with no
 *   notes; a card whose notes were all dismissed shows nothing.
````

**with:**

````ts
 * - `pruneReview` runs on every draft change (reviewer follow-up 1, owner
 *   answer 4 of 2026-10-01): a card whose text or origin no longer matches
 *   what was reviewed keeps its notes, marked `stale` ("From before your last
 *   edit.") until the next review (typing, Undo, "Use church default",
 *   another tab's edit; an Undo back to the reviewed words keeps them
 *   stale); a card left blank, or one with no notes left ("Looks good." or
 *   all dismissed), loses them; a new service loses the whole review. A
 *   successful Regenerate or Revise drops the card's notes (`forgetCard`,
 *   called by the providers), since the new text replaced or addressed them.
 * - "Looks good." shows for a card that was reviewed, came back with no
 *   notes and is unchanged since; a card whose notes were all dismissed
 *   shows nothing.
````

**In `frontend/src/lib/liturgy/notes.ts`, replace:**

````ts
/** `found`: how many notes the card came back with ("Looks good." only when 0). */
export type CardReview = { reviewed: ReviewedCard; notes: Note[]; found: number };
````

**with:**

````ts
export const STALE_LINE = "From before your last edit.";

/**
 * `found`: how many notes the card came back with ("Looks good." only when 0).
 * `stale`: the card changed since it was reviewed; its notes show faded.
 */
export type CardReview = { reviewed: ReviewedCard; notes: Note[]; found: number; stale: boolean };
````

**In `frontend/src/lib/liturgy/notes.ts`, replace:**

````ts
    cards[section] = { reviewed, notes: notes.map((n, i) => ({ ...n, id: `${section}-${i}` })), found: notes.length };
````

**with:**

````ts
    cards[section] = {
      reviewed,
      notes: notes.map((n, i) => ({ ...n, id: `${section}-${i}` })),
      found: notes.length,
      stale: false,
    };
````

**In `frontend/src/lib/liturgy/notes.ts`, replace:**

````ts
/** The review after a draft change: the same object when nothing changed. */
export function pruneReview(review: ServiceReview | null, d: DraftV1): ServiceReview | null {
  if (review === null) return null;
  if (d.created_at !== review.createdAt) return null;
  const gone = (Object.keys(review.cards) as SectionKey[]).filter((key) => {
    const card = review.cards[key];
    return card !== undefined && !holds(d.liturgy.cards[key], card.reviewed);
  });
  if (gone.length === 0) return review;
  const cards = { ...review.cards };
  for (const key of gone) delete cards[key];
  return { ...review, cards };
}
````

**with:**

````ts
/**
 * The review after a draft change: a changed card's notes fade (`stale`),
 * a blank card's or a noteless card's go; the same object when nothing changed.
 */
export function pruneReview(review: ServiceReview | null, d: DraftV1): ServiceReview | null {
  if (review === null) return null;
  if (d.created_at !== review.createdAt) return null;
  let cards: Partial<Record<SectionKey, CardReview>> | null = null;
  for (const key of Object.keys(review.cards) as SectionKey[]) {
    const card = review.cards[key];
    const now = d.liturgy.cards[key];
    if (card === undefined) continue;
    const blank = now.text.trim() === "";
    if (!blank && (card.stale || holds(now, card.reviewed))) continue;
    cards ??= { ...review.cards };
    if (blank || card.notes.length === 0) delete cards[key];
    else cards[key] = { ...card, stale: true };
  }
  return cards === null ? review : { ...review, cards };
}

/** A successful Regenerate or Revise: the card's notes go (the new text replaced or addressed them). */
export function forgetCard(review: ServiceReview | null, key: SectionKey): ServiceReview | null {
  if (review === null || review.cards[key] === undefined) return review;
  const cards = { ...review.cards };
  delete cards[key];
  return { ...review, cards };
}
````

- [ ] **Step 4 (agent): The generation provider tells who listens when it writes a draft**

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
 *   The service reviewer's Revise sets the same kind of Undo ("revised").
 */
````

**with:**

````tsx
 *   The service reviewer's Revise sets the same kind of Undo ("revised").
 * - `onWritten(listener)`: told the card's key each time an AI draft is
 *   written into it (the service reviewer drops that card's notes; reviewer
 *   follow-up 1). Returns the unsubscribe.
 */
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
  setUndo: (key: SectionKey, entry: UndoEntry | null) => void;
  clearUndo: () => void;
  applyUndo: (key: SectionKey) => void;
};
````

**with:**

````tsx
  setUndo: (key: SectionKey, entry: UndoEntry | null) => void;
  clearUndo: () => void;
  applyUndo: (key: SectionKey) => void;
  /** Calls `listener` with the card's key whenever an AI draft is written into it; returns the unsubscribe. */
  onWritten: (listener: (key: SectionKey) => void) => () => void;
};
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
  const batchSeq = useRef(0);
  const service = useRef(draft.created_at);
````

**with:**

````tsx
  const batchSeq = useRef(0);
  const service = useRef(draft.created_at);
  const writtenListeners = useRef(new Set<(key: SectionKey) => void>());
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
      setUndo(key, replaced && out.previous !== null ? { kind: "replaced", previous: out.previous, after: text } : null);
      return true;
````

**with:**

````tsx
      setUndo(key, replaced && out.previous !== null ? { kind: "replaced", previous: out.previous, after: text } : null);
      for (const listener of writtenListeners.current) listener(key);
      return true;
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
  const value = useMemo<LiturgyGeneration>(
    () => ({ runs, errors, undo, bulk, rateLimitedUntil, noteRateLimit, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo }),
    [runs, errors, undo, bulk, rateLimitedUntil, noteRateLimit, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo],
  );
````

**with:**

````tsx
  const onWritten = useCallback((listener: (key: SectionKey) => void) => {
    const listeners = writtenListeners.current;
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  }, []);

  const value = useMemo<LiturgyGeneration>(
    () => ({ runs, errors, undo, bulk, rateLimitedUntil, noteRateLimit, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo, onWritten }),
    [runs, errors, undo, bulk, rateLimitedUntil, noteRateLimit, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo, onWritten],
  );
````

- [ ] **Step 5 (agent): The review provider forgets a card's notes when a new draft or a revision lands**

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
 * - Every draft change prunes the notes of cards whose text or origin changed
 *   (`pruneReview`); a new service (a new `created_at`) cancels the review and
 *   every revision silently and drops all notes.
````

**with:**

````tsx
 * - Every draft change marks the notes of cards whose text or origin changed
 *   as stale, shown faded until the next review (`pruneReview`; reviewer
 *   follow-up 1); a successful Regenerate (`onWritten`) or Revise drops the
 *   card's notes (`forgetCard`); a new service (a new `created_at`) cancels
 *   the review and every revision silently and drops all notes.
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
import { applyReview, canRevise, captureReview, dismissNote, noteCount, pruneReview, type ServiceReview } from "./notes";
````

**with:**

````tsx
import {
  applyReview,
  canRevise,
  captureReview,
  dismissNote,
  forgetCard,
  noteCount,
  pruneReview,
  type ServiceReview,
} from "./notes";
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
  const { runs, setUndo, rateLimitedUntil, noteRateLimit } = useLiturgyGeneration();
````

**with:**

````tsx
  const { runs, setUndo, rateLimitedUntil, noteRateLimit, onWritten } = useLiturgyGeneration();
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
  // Every draft change, during render: notes whose card changed go (typing, Regenerate, Revise, Clear text, the
  // church default, Undo), so they never show for a single frame, and an Undo never brings them back.
````

**with:**

````tsx
  // Every draft change, during render: notes whose card changed fade (typing, Undo, the church default, another
  // tab), and a blank card's go, so neither shows for a single frame as if nothing had changed.
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
  // A new service (or a saved one loaded): the review and every revision belonged to the old draft.
````

**with:**

````tsx
  // A Regenerate (or Generate) wrote a new AI draft: the card's notes were about the text it replaced.
  useEffect(() => onWritten((key) => setReview((current) => forgetCard(current, key))), [onWritten]);

  // A new service (or a saved one loaded): the review and every revision belonged to the old draft.
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
          if (out.verdict !== "apply") reviseToast(key, out.verdict);
          else if (out.previous !== null) setUndo(key, { kind: "revised", previous: out.previous, after: text });
````

**with:**

````tsx
          if (out.verdict !== "apply") reviseToast(key, out.verdict);
          else if (out.previous !== null) {
            setUndo(key, { kind: "revised", previous: out.previous, after: text });
            setReview((current) => forgetCard(current, key)); // the notes were addressed
          }
````

- [ ] **Step 6 (agent): The card shows faded notes under the line, which describes the list**

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
import { canRevise, LOOKS_GOOD, TAG_LABELS, type Note } from "@/lib/liturgy/notes";
import { useLiturgyReview } from "@/lib/liturgy/review";
````

**with:**

````tsx
import { canRevise, LOOKS_GOOD, STALE_LINE, TAG_LABELS, type Note } from "@/lib/liturgy/notes";
import { useLiturgyReview } from "@/lib/liturgy/review";
import { cn } from "@/lib/utils";
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
  disabled = false,
}: {
  notes: Note[];
  label: string;
  onDismiss: (id: string) => void;
  /** The card is being revised with these notes: none can go meanwhile. */
  disabled?: boolean;
}) {
  return (
    <ul aria-label={label} className="grid gap-2">
      {notes.map((note) => (
        <li key={note.id} className="flex min-w-0 items-start gap-2">
          <Badge variant="outline" className="mt-0.5 shrink-0">
            {TAG_LABELS[note.tag]}
          </Badge>
          <p className="min-w-0 flex-1 text-sm wrap-anywhere">{note.text}</p>
````

**with:**

````tsx
  disabled = false,
  faded = false,
  describedBy,
}: {
  notes: Note[];
  label: string;
  onDismiss: (id: string) => void;
  /** The card is being revised with these notes: none can go meanwhile. */
  disabled?: boolean;
  /** The card changed since its review: the chips and sentences are dimmed, still readable. */
  faded?: boolean;
  /** The id of the line that says why they are dimmed. */
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
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
 * nothing when it was not reviewed, its notes were all dismissed, or its text
 * changed since.
````

**with:**

````tsx
 * nothing when it was not reviewed, its notes were all dismissed, or it was
 * "Looks good." and has changed since. When the card changed after its review
 * (reviewer follow-up 1) the notes stay, dimmed, under "From before your last
 * edit.", which is plain text inside the notes, so it is read with them, is
 * part of the textarea's description and describes the list; it is not
 * announced as it appears (it appears as the member types).
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
/** The id of a card's "Revise with these notes" button. */
````

**with:**

````tsx
/** The id of a card's "From before your last edit." line, which describes its faded notes. */
function staleId(key: SectionKey): string {
  return `card-${key}-stale`;
}

/** The id of a card's "Revise with these notes" button. */
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
    <div id={notesId(sectionKey)} className="grid gap-2 rounded-md bg-muted/40 p-3">
      <NoteList
        notes={notes.notes}
        label={`Notes on ${label}`}
        disabled={revising}
````

**with:**

````tsx
    <div id={notesId(sectionKey)} className="grid gap-2 rounded-md bg-muted/40 p-3">
      {notes.stale ? (
        <p id={staleId(sectionKey)} className="text-sm font-medium text-muted-foreground">
          {STALE_LINE}
        </p>
      ) : null}
      <NoteList
        notes={notes.notes}
        label={`Notes on ${label}`}
        disabled={revising}
        faded={notes.stale}
        describedBy={notes.stale ? staleId(sectionKey) : undefined}
````

- [ ] **Step 7 (agent): Run the three files three times, the suite, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/lib/liturgy/notes.test.ts src/lib/liturgy/review.test.tsx src/components/builder/liturgy/review-step.test.tsx 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** ` Test Files  3 passed (3)` and `      Tests  29 passed (29)` three times, with no `×` or `FAIL` line; ` Test Files  78 passed (78)` and `      Tests  572 passed (572)`; `typecheck 0`, `lint 0`. A `×` or `FAIL` line names the failing test: make it deterministic (Step 6 of T6), never rerun until green.

- [ ] **Step 8 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/notes.ts frontend/src/lib/liturgy/notes.test.ts frontend/src/lib/liturgy/generation.tsx frontend/src/lib/liturgy/review.tsx frontend/src/lib/liturgy/review.test.tsx frontend/src/components/builder/liturgy/card-notes.tsx frontend/src/components/builder/liturgy/review-step.test.tsx
git commit -q -m "Liturgy step: faded notes after an edit (follow-up 1; owner answer 4)" -m "After typing, Undo, Use church default or another tab's edit, a card's
notes stay, dimmed and dismissable, under From before your last edit.,
until the next review. A new AI draft or a successful revision removes
them (the generation provider's onWritten, and Revise itself); a blank
card shows none; Looks good. goes after any edit. Across the service and
the in-flight rule are unchanged." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 3: backend **1220 passed, 11 skipped**; frontend **572 in 78**.

### Task 4: Revise on typed and saved text, with a confirm (owner answers 2, 3; clarifications 8, 11-14)

**Files:**
- Modify: `frontend/src/lib/liturgy/notes.ts`, `frontend/src/lib/liturgy/notes.test.ts`, `frontend/src/lib/liturgy/review.tsx`, `frontend/src/lib/liturgy/review.test.tsx`, `frontend/src/components/builder/liturgy/card-notes.tsx`, `frontend/src/components/builder/liturgy/review-step.test.tsx`, `backend/usecases/liturgy_review.py` (its docstring only)

- [ ] **Step 1 (agent): Write the failing tests**

**In `frontend/src/lib/liturgy/notes.test.ts`, replace:**

````ts
  it("offers Revise only on an AI card with a note left", () => {
    const d = reviewed();
    const review = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER).review!;
    expect(canRevise(d.liturgy.cards.opening_prayer, review.cards.opening_prayer)).toBe(true);
    expect(canRevise(d.liturgy.cards.call_to_worship, review.cards.call_to_worship)).toBe(false);     // typed
    expect(canRevise(d.liturgy.cards.benediction, review.cards.benediction)).toBe(false);             // default
    const archive = { ...d.liturgy.cards.opening_prayer, origin: "archive" as const };
    expect(canRevise(archive, review.cards.opening_prayer)).toBe(false);
````

**with:**

````ts
  it("offers Revise on AI, typed and saved text with a note left, never on the church default or a blank card", () => {
    const d = reviewed();
    const review = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER).review!;
    expect(canRevise(d.liturgy.cards.opening_prayer, review.cards.opening_prayer)).toBe(true);
    expect(canRevise(d.liturgy.cards.call_to_worship, review.cards.call_to_worship)).toBe(true);      // typed
    expect(canRevise(d.liturgy.cards.benediction, review.cards.benediction)).toBe(false);             // default, no notes
    const archive = { ...d.liturgy.cards.opening_prayer, origin: "archive" as const };
    expect(canRevise(archive, review.cards.opening_prayer)).toBe(true);
    const followsDefault = { ...d.liturgy.cards.opening_prayer, origin: "default" as const };
    expect(canRevise(followsDefault, review.cards.opening_prayer)).toBe(false);                       // even with notes
    const blank = { ...d.liturgy.cards.opening_prayer, text: "  ", origin: "typed" as const };
    expect(canRevise(blank, review.cards.opening_prayer)).toBe(false);
````

**In `frontend/src/lib/liturgy/review.test.tsx`, replace:**

````tsx
      started.push(handle.current?.revise("call_to_worship")); // typed: never revised
````

**with:**

````tsx
      started.push(handle.current?.revise("benediction")); // no notes: nothing to revise with
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
  it("is offered only on AI cards with a note left; typed, archived and default cards get notes but no Revise", async () => {
    const { user } = renderStep();
    await review(user);
    expect(within(card("Opening Prayer")).getByRole("button", { name: "Revise with these notes" })).toBeInTheDocument();
    expect(within(card("Assurance of Pardon")).getByRole("button", { name: "Revise with these notes" })).toHaveAccessibleDescription(
      "Assurance of Pardon",
    );
    expect(within(card("Call to Worship")).getByText(STOCK)).toBeInTheDocument();
    expect(within(card("Call to Worship")).queryByRole("button", { name: "Revise with these notes" })).toBeNull();
    expect(within(card("Prayer of Confession")).queryByRole("button", { name: "Revise with these notes" })).toBeNull();
    expect(within(card("Benediction")).queryByRole("button", { name: "Revise with these notes" })).toBeNull();
    // Its last note dismissed, an AI card has nothing to revise with.
````

**with:**

````tsx
  it("is offered on AI, typed and archived cards with a note left; the Benediction only once it no longer follows the default", async () => {
    const answer = reviewResult({
      cards: [
        ...ANSWER.cards.filter((c) => c.section !== "benediction"),
        { section: "benediction", notes: [reviewNote("read_aloud", "The last line is long.")] },
      ],
      service_notes: ANSWER.service_notes,
    });
    const { user } = renderStep(seeded(), { "POST /liturgy/review": reviewRoute(() => answer) });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await screen.findByText("Review finished. 7 notes.");
    for (const label of ["Opening Prayer", "Call to Worship", "Prayer of Confession"]) {
      expect(within(card(label)).getByRole("button", { name: "Revise with these notes" }), label).toBeInTheDocument();
    }
    expect(within(card("Assurance of Pardon")).getByRole("button", { name: "Revise with these notes" })).toHaveAccessibleDescription(
      "Assurance of Pardon",
    );
    const benediction = card("Benediction");
    expect(within(benediction).getByText("The last line is long.")).toBeInTheDocument();
    expect(within(benediction).queryByRole("button", { name: "Revise with these notes" })).toBeNull(); // follows the church default
    await user.type(screen.getByRole("textbox", { name: "Benediction" }), " Amen.");
    expect(within(benediction).getByText(STALE)).toBeInTheDocument();
    expect(within(benediction).getByRole("button", { name: "Revise with these notes" })).toBeInTheDocument(); // now your text
    // Its last note dismissed, a card has nothing to revise with.
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
  it("keeps the card read-only while it revises; Cancel keeps the text and notes and returns focus to Revise", async () => {
````

**with:**

````tsx
  it("asks before revising typed or saved text: Keep my text sends nothing; Revise text revises the current text, with Undo", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": reviseRoute(async () => {
        await gate;
        return { text: "Leader: Come, all.\nPeople: We come." };
      }),
    });
    await review(user);
    const call = card("Call to Worship");
    const box = screen.getByRole("textbox", { name: "Call to Worship" });
    await user.type(box, " Now.");
    const revise = within(call).getByRole("button", { name: "Revise with these notes" }); // faded notes: still offered
    await user.click(revise);
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your text?" });
    expect(dialog).toHaveTextContent(
      "Revise replaces the text in Call to Worship with a version that addresses these notes. You can undo right after.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Keep my text" }));
    await waitFor(() => expect(revise).toHaveFocus());
    expect(api.requests.some((r) => r.path === "/liturgy/revise")).toBe(false);
    await user.click(revise);
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Revise text" }));
    await waitFor(() => expect(within(call).getByRole("button", { name: "Cancel revising Call to Worship" })).toHaveFocus());
    const sent = api.requests.find((r) => r.path === "/liturgy/revise")?.body as ReviseBody;
    expect(sent).toMatchObject({ section: "call_to_worship", text: "Leader: As we journey, come. Now.", notes: [STOCK] });
    release();
    expect(await within(call).findByText("Revised with these notes.")).toBeInTheDocument();
    expect(box).toHaveValue("Leader: Come, all.\nPeople: We come.");
    expect(within(call).getByText("AI draft")).toBeInTheDocument();
    expect(within(call).queryByRole("list", { name: "Notes on Call to Worship" })).toBeNull(); // addressed: they go
    expect(within(call).getByRole("button", { name: "Undo" })).toHaveFocus();
    await user.click(within(call).getByRole("button", { name: "Undo" }));
    expect(box).toHaveValue("Leader: As we journey, come. Now.");
    expect(within(call).getByText("Your text")).toBeInTheDocument();
  });

  it("closes Replace your text? when the notes change meanwhile, sending nothing; focus goes to the heading once Revise is gone", async () => {
    const { user, api } = renderStep();
    await review(user);
    const call = card("Call to Worship");
    await user.click(within(call).getByRole("button", { name: "Revise with these notes" }));
    expect(await screen.findByRole("alertdialog", { name: "Replace your text?" })).toBeInTheDocument();
    // Another tab clears the card: no notes are left to revise with.
    act(() => {
      const theirs = withCard(stored(), "call_to_worship", "", "empty");
      window.dispatchEvent(
        new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...theirs, updated_at: "2026-09-29T17:00:00.000Z" }) }),
      );
    });
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(within(call).queryByRole("list", { name: "Notes on Call to Worship" })).toBeNull();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Call to Worship" })).toHaveFocus());
    // Another tab edits another card: the review changed, so the confirm closes; Revise is still there and takes focus.
    const confession = card("Prayer of Confession");
    await user.click(within(confession).getByRole("button", { name: "Revise with these notes" }));
    expect(await screen.findByRole("alertdialog", { name: "Replace your text?" })).toBeInTheDocument();
    act(() => {
      const theirs = withCard(stored(), "opening_prayer", "Holy One, hear us.", "typed");
      window.dispatchEvent(
        new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...theirs, updated_at: "2026-09-29T17:01:00.000Z" }) }),
      );
    });
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    await waitFor(() => expect(within(confession).getByRole("button", { name: "Revise with these notes" })).toHaveFocus());
    expect(api.requests.some((r) => r.path === "/liturgy/revise")).toBe(false);
  });

  it("keeps the card read-only while it revises; Cancel keeps the text and notes and returns focus to Revise", async () => {
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveValue("From the other tab");
    expect(screen.getByRole("heading", { name: "Assurance of Pardon" })).toHaveFocus();
````

**with:**

````tsx
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveValue("From the other tab");
    expect(within(assurance).getByRole("button", { name: "Revise with these notes" })).toHaveFocus(); // now typed text
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/notes.test.ts src/lib/liturgy/review.test.tsx src/components/builder/liturgy/review-step.test.tsx 2>&1 | grep -E "^ +× |Tests ")
```

**Expected:** these five lines (order may vary; typed and saved text has no Revise yet), then `⎯⎯⎯⎯⎯⎯⎯ Failed Tests 5 ⎯⎯⎯⎯⎯⎯⎯` and `      Tests  5 failed | 26 passed (31)`:
```
   × the reviewer's notes (R Notes) > offers Revise on AI, typed and saved text with a note left, never on the church default or a blank card
   × Revise with these notes (R Revise) > is offered on AI, typed and archived cards with a note left; the Benediction only once it no longer follows the default
   × Revise with these notes (R Revise) > asks before revising typed or saved text: Keep my text sends nothing; Revise text revises the current text, with Undo
   × Revise with these notes (R Revise) > closes Replace your text? when the notes change meanwhile, sending nothing; focus goes to the heading once Revise is gone
   × Revise with these notes (R Revise) > keeps Cancel while a one-note card revises, with its × off, even when another tab's edit fades the notes
```

- [ ] **Step 3 (agent): Who gets Revise**

**In `frontend/src/lib/liturgy/notes.ts`, replace:**

````ts
 * - Revise is offered only on a card whose origin is "ai" with a note left.
 */
````

**with:**

````ts
 * - Revise is offered on a card with text and a note left whose origin is
 *   "ai", "typed" or "archive" (owner answer 2 of 2026-10-01); never on the
 *   church default (owner answer 3). Typed and saved text asks first
 *   (`CardNotes`).
 */
````

**In `frontend/src/lib/liturgy/notes.ts`, replace:**

````ts
/** "Revise with these notes": only an AI card with at least one note left. */
export function canRevise(card: LiturgyCard, review: CardReview | undefined): boolean {
  return card.origin === "ai" && review !== undefined && review.notes.length > 0;
}
````

**with:**

````ts
/** "Revise with these notes": a card with text and a note left, written by the AI, typed or from a saved service. */
export function canRevise(card: LiturgyCard, review: CardReview | undefined): boolean {
  const origin = card.origin === "ai" || card.origin === "typed" || card.origin === "archive";
  return origin && card.text.trim() !== "" && review !== undefined && review.notes.length > 0;
}
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
 * - `revise(key)`: an AI card with notes left; its text and remaining notes,
````

**with:**

````tsx
 * - `revise(key)`: a card with notes left (`canRevise`: AI, typed or saved
 *   text; the card asks first for the last two); its text and remaining notes,
````

**In `frontend/src/lib/liturgy/review.tsx`, replace:**

````tsx
  /** True when the revision started (an AI card with notes left, not already revising, not being written, no 429 wait). */
````

**with:**

````tsx
  /** True when the revision started (`canRevise`, not already revising, not being written, no 429 wait). */
````

**In `backend/usecases/liturgy_review.py`, replace:**

````python
revise_section: one complete() call that edits an AI draft to address the
notes left on it and keeps the rest. The system message
````

**with:**

````python
revise_section: one complete() call that edits a card's text to address the
notes left on it and keeps the rest: an AI draft, typed text or a saved
service's (reviewer follow-up 1; the origin is not sent, and the client asks
before replacing the member's own text). The system message
````

- [ ] **Step 4 (agent): The confirm on the card**

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
import { PendingButton } from "@/components/app/pending-button";
````

**with:**

````tsx
import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { PendingButton } from "@/components/app/pending-button";
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
import type { SectionKey } from "@/lib/draft/schema";
````

**with:**

````tsx
import type { SectionKey } from "@/lib/draft/schema";
import { needsRegenerateConfirm } from "@/lib/liturgy/cards";
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
import { canRevise, LOOKS_GOOD, STALE_LINE, TAG_LABELS, type Note } from "@/lib/liturgy/notes";
````

**with:**

````tsx
import { canRevise, LOOKS_GOOD, STALE_LINE, TAG_LABELS, type Note, type ServiceReview } from "@/lib/liturgy/notes";
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
 * "Revise with these notes" (R "Revise") shows only on an AI card with a note
 * left, and not while the card is being written; the card's heading
 * describes it. While it runs the button
````

**with:**

````tsx
 * "Revise with these notes" (R "Revise") shows on a card with text and a note
 * left, written by the AI, typed or from a saved service (reviewer follow-up
 * 1; never the church default), and not while the card is being written; the
 * card's heading describes it. On typed or saved text it asks first ("Replace
 * your text?", the same rule as Regenerate's): "Keep my text" returns focus to
 * the button, "Revise text" starts it and the closing dialog sends focus to its
 * Cancel. The dialog closes, sending nothing, when the notes change while it
 * asks (Revise no longer offered, or a new review or another tab's edit), and
 * focus goes to Revise, else the heading. While it runs the button
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
  const cancelRef = useRef<HTMLButtonElement>(null);
  const focusCancel = useRef(false);
````

**with:**

````tsx
  const cancelRef = useRef<HTMLButtonElement>(null);
  const focusCancel = useRef(false);
  const [confirming, setConfirming] = useState(false);
  /** The review the confirm was opened on. */
  const [askedOn, setAskedOn] = useState<ServiceReview | null>(null);
  /** "Revise text" was chosen, so the closing dialog sends focus to the revision's Cancel. */
  const confirmed = useRef(false);
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
  if (notes === undefined || notes.notes.length === 0) {
    // The notes went while the card revises (another tab edited it): Cancel stays.
    if (revisingRow !== null) return revisingRow;
    return notes?.found === 0 ? (
      <p id={notesId(sectionKey)} className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <CheckIcon className="size-4" aria-hidden="true" />
        {LOOKS_GOOD}
      </p>
    ) : null;
  }
  const offered = canRevise(draft.liturgy.cards[sectionKey], notes) && !busy;
````

**with:**

````tsx
  const card = draft.liturgy.cards[sectionKey];
  const offered = canRevise(card, notes) && !busy;
  // The confirm closes once Revise is no longer offered or the notes it asked about changed (another tab's edit,
  // a new review), so it never revises with notes the member is not looking at.
  if (confirming && (!offered || review.review !== askedOn)) setConfirming(false);
  // Rendered after the notes in every branch below, so it stays mounted (and sends focus back) as the notes go.
  const dialog = (
    <ConfirmDialog
      open={confirming}
      onOpenChange={setConfirming}
      title="Replace your text?"
      description={`Revise replaces the text in ${label} with a version that addresses these notes. You can undo right after.`}
      confirmLabel="Revise text"
      cancelLabel="Keep my text"
      onConfirm={() => {
        confirmed.current = true;
        setConfirming(false);
        review.revise(sectionKey);
      }}
      // Keep my text: back to Revise. Revise text: Revise is gone, so the revision's Cancel (Revise if it did not
      // start). The heading when neither is there (the notes went while it asked).
      finalFocus={() => {
        const cancel = confirmed.current ? cancelRef.current : null;
        if (cancel !== null && cancel.isConnected) return cancel;
        return document.getElementById(reviseId(sectionKey)) ?? document.getElementById(headingId);
      }}
    />
  );
  if (notes === undefined || notes.notes.length === 0) {
    // The notes went while the card revises (another tab edited it): Cancel stays.
    const rest =
      revisingRow ??
      (notes?.found === 0 ? (
        <p id={notesId(sectionKey)} className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <CheckIcon className="size-4" aria-hidden="true" />
          {LOOKS_GOOD}
        </p>
      ) : null);
    return (
      <>
        {rest}
        {dialog}
      </>
    );
  }
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
  return (
    <div id={notesId(sectionKey)} className="grid gap-2 rounded-md bg-muted/40 p-3">
````

**with:**

````tsx
  const shown = (
    <div id={notesId(sectionKey)} className="grid gap-2 rounded-md bg-muted/40 p-3">
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
              onClick={() => {
                // Focus moves to Cancel only when the revision started.
                if (review.revise(sectionKey)) focusCancel.current = true;
              }}
````

**with:**

````tsx
              onClick={() => {
                if (needsRegenerateConfirm(card)) {
                  confirmed.current = false;
                  setAskedOn(review.review);
                  setConfirming(true);
                  return;
                }
                // Focus moves to Cancel only when the revision started.
                if (review.revise(sectionKey)) focusCancel.current = true;
              }}
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
      ) : null}
    </div>
  );
}

/** The "Across the service" box at the top of the step (R "Notes"): notes about more than one prayer, at most 3. */
````

**with:**

````tsx
      ) : null}
    </div>
  );
  return (
    <>
      {shown}
      {dialog}
    </>
  );
}

/** The "Across the service" box at the top of the step (R "Notes"): notes about more than one prayer, at most 3. */
````

- [ ] **Step 5 (agent): Run the three files three times, the suite, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/lib/liturgy/notes.test.ts src/lib/liturgy/review.test.tsx src/components/builder/liturgy/review-step.test.tsx 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** ` Test Files  3 passed (3)` and `      Tests  31 passed (31)` three times, with no `×` or `FAIL` line; ` Test Files  78 passed (78)` and `      Tests  574 passed (574)`; `typecheck 0`, `lint 0`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/notes.ts frontend/src/lib/liturgy/notes.test.ts frontend/src/lib/liturgy/review.tsx frontend/src/lib/liturgy/review.test.tsx frontend/src/components/builder/liturgy/card-notes.tsx frontend/src/components/builder/liturgy/review-step.test.tsx backend/usecases/liturgy_review.py
git commit -q -m "Liturgy step: Revise on typed and saved text, with a confirm (follow-up 1; owner answers 2, 3)" -m "Revise with these notes is offered on typed and saved text too, after
Replace your text? (Revise text, Keep my text), with Undo after, and
focus as Regenerate's confirm. The confirm closes, sending nothing, if the
notes change while it asks. A Benediction following the church default
has none; once edited it is typed text. The backend never restricted the
origin, so only its docstring changes." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 4: backend **1220 passed, 11 skipped**; frontend **574 in 78**.

### Task 5: Docs: the manual check and R's amendment (owner answer 6; clarification 15)

**Files:**
- Modify: `docs/manual-verification.md`, `docs/superpowers/specs/2026-09-26-service-reviewer-design.md`

- [ ] **Step 1 (agent): Write the docs**

**In `docs/manual-verification.md`, replace:**

````markdown
record". The AI's words differ every time, so record what the page shows,
never an email address or a church id.
````

**with:**

````markdown
record". The AI's words differ every time, so record what the page shows,
never an email address or a church id. Items marked "(owner, after
follow-up 1)" are the owner's phone check after reviewer follow-up 1
(`docs/superpowers/plans/2026-10-01-reviewer-followup-1.md`); that result
goes into "Reviewer follow-up 1 record".
````

**In `docs/manual-verification.md`, replace:**

````markdown
- [ ] (owner, after the reviewer) **4.** The typed card has notes but no **Revise with these notes** button.
- [ ] (owner, after the reviewer) **5.** Type in a card that has notes: its notes go at once; the other cards keep theirs.
````

**with:**

````markdown
- [ ] (owner, after follow-up 1) **4.** On the typed card with a note, tap **Revise with these notes**: "Replace your text?" asks first; **Keep my text** changes nothing; **Revise text** revises it, shows "Revised with these notes. Undo", and **Undo** brings your text back. A Benediction that follows the church default has no Revise. (Before reviewer follow-up 1: typed cards had no Revise.)
- [ ] (owner, after follow-up 1) **5.** Type in a card that has notes: its notes stay, dimmed, under "From before your last edit.", and the other cards keep theirs; a card that said "Looks good." shows nothing after an edit; a new **Review service** replaces the dimmed notes. (Before reviewer follow-up 1: the notes went at once.)
````

**In `docs/manual-verification.md`, replace:**

````markdown
- [ ] **8.** Start a review and tap **Cancel**: the spinner goes and nothing changes. Start one and choose **New service**: no notes remain.
````

**with:**

````markdown
- [ ] **8.** Start a review and tap **Cancel**: the spinner goes and nothing changes. Start one and choose **New service**: no notes remain.
- [ ] (owner, after follow-up 1) **9.** On a real review: no note only praises a prayer ("… fits well", "good focus on …"); a card with a "Cites …" note has no second note about naming the reading; a prayer named in "Several prayers open with …" has no note of its own about its opening, and "Across the service" has no second, AI-worded version of that note.
````

**Append to `docs/superpowers/specs/2026-09-26-service-reviewer-design.md`:**

````markdown

## Amendment 2026-10-01: reviewer follow-up 1 (owner decisions after the phone check)

`docs/superpowers/plans/2026-10-01-reviewer-followup-1.md` changes four things, on the owner's decisions of 2026-10-01 ("all recommended"):

- **No praise notes.** The output contract says a note is only for something to change, never praise or a description of what already works, and a prayer that is fine gets no notes. No code filter guesses at compliments.
- **Revise on typed and saved text** (reverses decision 4). Revise is offered on a card with text and a note left whose origin is AI, typed or from a saved service; typed and saved text asks first ("Replace your text?", "Revise replaces the text in {Label} with a version that addresses these notes. You can undo right after.", "Revise text", "Keep my text"), and Undo follows, as on AI cards. The revised text is an AI draft. A Benediction that follows the church default has no Revise; once edited it is typed text.
- **Faded notes after an edit** (replaces "Notes go away when the text changes"). After typing, Undo, "Use church default" or another tab's edit (another tab's Regenerate or Revise included), a card's notes stay, dimmed, under "From before your last edit.", each still dismissable, with Revise still offered (it sends the current text and the remaining notes) until the next review. A successful Regenerate or Revise removes the card's notes, and Undo after it brings the text back without them; Clear text (a blank card) removes them; "Looks good." goes after any edit. "Across the service" is unchanged: it stays until the next review, its own dismiss or New service. A card changed while the review ran still gets no notes.
- **No restated code notes.** On a card with a code "Cites …" note, an AI note tagged rules that speaks of citing or naming scripture is dropped; on a card whose opening a code "Several prayers open with …" note names, an AI note tagged repetition that speaks of how the prayer opens, or quotes its opening, is dropped, and so is an AI note across the service on prayers that open alike. The prompt also says not to make a code note's point in other words.

Later, planned on its own: Revise from "Across the service".
````

- [ ] **Step 2 (agent): Check the docs tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
grep -c "—" <(git diff -U0 -- docs | grep '^+' | grep -v '^+++')
.venv/bin/python -m pytest -q | tail -1
git diff --stat
```

**Expected:** `89 passed in <t>s`; `4`; `0` (no em dash added); `1220 passed, 11 skipped in <t>s`; `2 files changed, 18 insertions(+), 3 deletions(-)`.

- [ ] **Step 3 (agent): Commit**

```bash
git add docs/manual-verification.md docs/superpowers/specs/2026-09-26-service-reviewer-design.md
git commit -q -m "Docs: reviewer follow-up 1 in the reviewer spec and the manual check (owner answers 2026-10-01)" -m "The reviewer spec gains an amendment for the four owner decisions (no
praise notes, Revise on typed and saved text, faded notes after an edit,
no restated code notes). docs/manual-verification.md: items 4 and 5 follow
the new behavior and item 9 checks a real review, marked for the owner's
phone check after the merge." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 4 (controller): Review the batch (T1-T5) and backup push**

One review of the whole batch: the contract and code-notes strings exactly as clarifications 1-2; `code_notes_intro` names only the points the code notes invite (clarification 2); `drop_restated` and the across-the-service filter drop only what clarifications 3-4 say and never a code note; no INFO line gains text; `pruneReview` fades and drops exactly as clarification 5; Regenerate and Revise forget the card (`onWritten`, `forgetCard`); "Across the service" unchanged; the line is plain text in the notes (clarification 9); `canRevise` and the confirm as clarifications 11-12 (it closes, sending nothing, when the notes change while it asks), with the owner's copy verbatim; focus never drops to the page; 44 px targets and wrapping at 375 px unchanged; the docs match. Fixes are `Fix: <what> (Task <n> review)` commits. Then the backup push.

Counts after Task 5: backend **1220 passed, 11 skipped**; frontend **574 in 78**.

### Task 6: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 7).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline --grep '^Plan: reviewer follow-up 1' -1
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
```

**Expected:** nothing (or `?? .claude/`); `0`; `<sha> Plan: reviewer follow-up 1 build notes and counts`; `0`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 6)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the changed files three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error")
```

**Expected:** `1222 passed, 11 skipped in <t>s`; three times ` Test Files  78 passed (78)` and `      Tests  581 passed (581)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s` and no `Error` (the build runs in the real checkout; a font `Failed to fetch` only: say so and rely on CI).

- [ ] **Step 3 (agent): The API files are unchanged, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/usecases/liturgy_review.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff --name-only origin/main...HEAD | LC_ALL=C sort
git diff --name-only origin/main...HEAD -- backend/api backend/migrations backend/db .github frontend/package.json frontend/package-lock.json frontend/src/lib/api docs/ops-runbook.md app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status`; `imports grep exit 1`; `raw html grep exit 1`; exactly these 13 paths (this plan, the 11 files the tasks change, and `generation.test.tsx`, which the review fixes `a0959fb` added a test to), plus `docs/superpowers/specs/2026-10-01-voices-of-the-church-decisions.md` from the docs-only commit `2607566 Docs: Voices of the Church owner decisions (pre-spec, 2026-10-01)`, which landed on the branch before this plan (name it in Step 4's message; it changes no code):
```
backend/tests/test_usecase_liturgy_review.py
backend/usecases/liturgy_review.py
docs/manual-verification.md
docs/superpowers/plans/2026-10-01-reviewer-followup-1.md
docs/superpowers/specs/2026-09-26-service-reviewer-design.md
frontend/src/components/builder/liturgy/card-notes.tsx
frontend/src/components/builder/liturgy/review-step.test.tsx
frontend/src/lib/liturgy/generation.test.tsx
frontend/src/lib/liturgy/generation.tsx
frontend/src/lib/liturgy/notes.test.ts
frontend/src/lib/liturgy/notes.ts
frontend/src/lib/liturgy/review.test.tsx
frontend/src/lib/liturgy/review.tsx
```
`0`; the subjects oldest first: `Docs: Voices of the Church owner decisions (pre-spec, 2026-10-01)`, the plan's (`WIP plan: reviewer follow-up 1` …, `Plan: reviewer follow-up 1 review fixes (owner answers 2026-10-01)`), then T1-T5's five subjects as written above, then `Reviewer follow-up 1 review fixes (owner decision 1)` and `Plan: reviewer follow-up 1 build notes and counts`, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** one `✓ Logged in` line; `[]`. Send the owner exactly this, and wait for a clear yes:

> Reviewer follow-up 1 is verified on this machine: backend 1222 passed, 11 skipped (1217 before); frontend 581 tests in 78 files (570 before), three runs in a row; typecheck, lint and the production build are clean; the API is unchanged. It makes the four changes you chose: no praise notes, Revise on your own text after "Replace your text?", dimmed notes under "From before your last edit." after an edit, and no AI notes that restate a citation or a repeated opening. May I open the pull request as a **draft** titled "Reviewer follow-up 1: no praise, Revise on your text, faded notes", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/followup1-pr-body.md" <<'EOF'
Reviewer follow-up 1 (owner answers of 2026-10-01 after the reviewer's phone check). Plan: docs/superpowers/plans/2026-10-01-reviewer-followup-1.md. No route, schema, migration or variable change.

- No praise notes: the review's output contract says a note is only for something to change; a fine prayer gets no notes.
- Revise with these notes on typed and saved text, after "Replace your text?" (Revise text / Keep my text), with Undo. A Benediction following the church default has none.
- After an edit a card's notes stay, dimmed, under "From before your last edit." until the next review; a new AI draft or a successful revision removes them.
- AI notes that only restate a code note (citing scripture on a card with a Cites note; how a prayer opens, on the card or across the service, when "Several prayers open with" already says so) are dropped, and the prompt names only the restatements the code notes invite.

Later, planned on its own: Revise from "Across the service".

Tests: backend 1217 → 1222 passed, 11 → 11 skipped; frontend 570 → 581 in 78 → 78 files

After merge (Task 7): a four-step check on the owner's phone, then a short "Reviewer follow-up 1 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
EOF
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Reviewer follow-up 1: no praise, Revise on your text, faded notes" \
  --body-file "<scratch>/followup1-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1222 passed, 11 skipped`, backend-postgres `11 passed, 1222 deselected`, frontend `581 passed` in 78 files. Then send: "PR #<N> is green: backend 1222 passed, 11 skipped; 581 frontend tests in 78 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_usecase_liturgy_review.py` (the prompt tests, the restated-note tests, the INFO test, the budget test) | T1, T2 |
| `notes.test.ts`, `review.test.tsx`, `generation.test.tsx`, review-step's fading cases | T3 |
| review-step's Revise cases (the confirm, and its closing when the notes change) | T4 |
| `test_docs.py`, `test_slice1_docs.py` | T5 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, follow-up 1 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1222 passed, 11 skipped`; frontend `581 passed` in 78 files.

### Task 7: Merge, the owner's phone check (four steps), the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate; the Vercel deploy is the one members see. The owner's check is **one step at a time** (send one, wait for the report or "next"). The agent writes each result into `<scratch>/followup1-t7-results.md` (not committed). The AI's words differ every time: record what the page showed, never a token, an email address or a church id.

**Files:** Modify (the records PR, Step 7): `docs/ops-runbook.md`: insert `### Reviewer follow-up 1 record` right after the "Service reviewer record" table (its last row starts `| Follow-ups | Next, one small PR (owner, 2026-10-01)`) and before `## Backups`. A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (reviewer follow-up 1) is ready, green and up to date with main. There is no database change, and liturgy-frozen is not affected. Then I will ask you for four short checks on your phone, one at a time. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about two minutes for Vercel before Step 2.

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 4: no praise notes**

> On your phone, open https://worship-service-builder.vercel.app (signed in, in your church). Tap **⋮** next to Summary, choose **New service** (tap **Start new service** if it asks), then tap **3 Liturgy**. In **Call to Worship** type: `Leader: Gracious God, as John 21 tells, you call us. People: We come.` Then tap **Generate empty sections** and wait until it says it wrote them ("Wrote … sections."). In **Opening Prayer**, make the very first words `Gracious God,` (type over the start if needed). Now tap **Review service**. Read every note: is any of them only praise, saying something already works ("fits well", "good focus on …") rather than asking for a change? Cards with nothing to fix should say "Looks good.".

Record the number of notes, any that only praised (quote it), and the "Looks good." cards.

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 4: no restated notes**

> Still on that review: your **Call to Worship** should have the note `Cites John 21. Draw on the reading's themes without naming it.` Is there a second note on it that says the same thing in other words (about citing or naming the reading)? At the top, **Across the service** should say `Several prayers open with "Gracious God".` Does the Call to Worship or the Opening Prayer have its own note about how it opens? And does **Across the service** show a second, AI-worded version of that note (saying the prayers begin or open alike)?

Record yes or no for each, quoting any restated note.

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 4: Revise on your own text**

> On your **Call to Worship** (your text, with a note), tap **Revise with these notes**. A box asks "Replace your text?". Tap **Keep my text**: nothing changes. Tap **Revise with these notes** again, then **Revise text**: "Revising…" shows, then your text is replaced, its notes go, and "Revised with these notes. Undo" appears. Did it fix what the note said? Then tap **Undo**: your own text comes back. Did it?

Record whether the confirm showed, how long it took, whether the revision addressed the note and kept the Leader/People form, and that Undo restored the text.

- [ ] **Step 5 (OWNER, then agent): Phone, step 4 of 4: dimmed notes after typing**

> In a card that still has notes (for example Opening Prayer), type one letter at the end. Its notes should stay, a little dimmer, under "From before your last edit.", and you can still tap their **×**. If a card said "Looks good.", type a letter in it too: "Looks good." should go. Then tap **Review service** again: the dimmed notes are replaced by fresh ones. Is that what you see?

- [ ] **Step 6 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/followup1-t7-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 7 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^### Service reviewer record$\|^| Follow-ups | Next, one small PR (owner, 2026-10-01)\|^## Backups$' docs/ops-runbook.md
```

**Expected:** `Fast-forward` (or `Already up to date.`); three lines in that order. Insert, between that last row and `## Backups` (one blank line on each side):

```markdown
### Reviewer follow-up 1 record

Reviewer follow-up 1 (owner answers of 2026-10-01 after the reviewer's phone
check: no praise notes, Revise on typed and saved text with a confirm and
Undo, faded notes after an edit, no AI notes restating a code note) merged as
PR #<N>. No database change and no new variable; production stays at
`0004_invites_reusable`. The owner's check was four steps on a phone,
covering the "(owner, after follow-up 1)" items of
`docs/manual-verification.md` → "Service reviewer". No token, email address
or church id is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success | <date> |
| 1. No praise notes (phone: <phone and browser>) | <n notes, none only praise; Looks good on n cards. / Praise seen: "…"> | <date> |
| 2. No restated notes | <The Call to Worship had only the code Cites note on citing; no card restated the opening; Across the service had no AI-worded second note on it. / Restated: "…"> | <date> |
| 3. Revise on your text | <"Replace your text?" asked first; Keep my text changed nothing; revised in <n> s, addressed the note, kept the form; Undo brought the text back. / …> | <date> |
| 4. Dimmed notes after typing | <The notes stayed, dimmed, under "From before your last edit."; Looks good went; a new review replaced them. / …> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: Revise from "Across the service" (planned on its own); then 5a (saving and archiving services and the Word files). | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Then:

(not replayed)
```bash
sed -n '/^### Reviewer follow-up 1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Reviewer follow-up 1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: reviewer follow-up 1 record (merged; owner's phone check)" -m "Records reviewer follow-up 1 (PR #<N>): the merge and CI on main, and the
owner's four-step phone check (no praise notes, no restated notes, Revise
on typed text with the confirm and Undo, dimmed notes after typing). No
token, email or church id is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 8 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The reviewer follow-up 1 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes:

(not replayed)
```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: reviewer follow-up 1 record" \
  --body "Records reviewer follow-up 1 (PR #<N>) in docs/ops-runbook.md → Reviewer follow-up 1 record: the merge and the owner's four-step phone check. No token, email or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Reviewer follow-up 1 is live and recorded; <n> follow-ups."

- [ ] **Step R (only if the release must come out): Revert**

Code only (notes were never saved; no draft shape changed). On the owner's yes for each outward command: a branch `claude/revert-reviewer-followup-1` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert reviewer follow-up 1 (PR #<N>)" with the trailer, both suites (`1217 passed, 11 skipped`; `570 passed` in 78), a PR, CI, and the merge on the owner's yes; record it in the follow-up record.

Expected counts after this task: backend `1222 passed, 11 skipped` on `main`; frontend `581 passed` in 78 files. The records PR adds no test.

---

## Build notes

**How this plan was written (2026-10-01).** Each task's code was built and run in a throwaway worktree of `faa0ecb` (the repo's `.venv`, the checkout's `node_modules`), then the directives were written from those changes and replayed onto a fresh worktree of `faa0ecb` by a script that applies every Create, Append and Replace directive of T1-T5 in order. While writing it:
- **T3's dismissed-card case** first used the Opening Prayer, which has one note in `notes.test.ts`'s answer, so dismissing it left none; it uses the Call to Worship (two notes).
- **T3 keeps `canRevise` as it is,** so its DOM tests stay on AI cards; T4 widens it and updates the two cases that depended on typed cards having no Revise (the "offered on" test and the other-tab Cancel test, whose focus now goes to Revise on the now-typed card).

**Replay of the finished plan (2026-10-01).** The directives of T1-T5 were applied in order onto a fresh detached worktree of `faa0ecb` (a symlink to the repo's `.venv` and to `frontend/node_modules`), running each task's test commands:
- All 61 directives applied (T1 4, T2 4, T3 34, T4 15, T5 4); every Replace anchor occurred exactly once; after T2, T3, T4 and T5 the tree was identical to the build worktree's. (Superseded by the replay after the review fixes, below.)
- Every "see it fail" output matched as then quoted (T1 `1 failed, 13 passed`; T2 `2 failed, 14 passed`; T3 eight failures, `8 failed | 21 passed (29)`; T4 four failures, `4 failed | 26 passed (30)`), and every count matched the table then: backend 1218, then 1220 (11 skipped); frontend 572, then 573 in 78 files; typecheck 0 and lint 0; the docs tests `89 passed`, owner markers `4`, no em dash added; the OpenAPI export and `gen:api` left the API files unchanged.
- **One flaky run:** during T3's checks the three frontend files once reported `1 failed | 28 passed (29)`; the failing test's name was not captured, and 45 further runs of the same files (T3 and T4 trees) all passed. T6 Step 2 runs the suite three times; a failure there is Step 6's (make the test deterministic, never retry), and the build's review should look at the new DOM tests' waits first.

**Review fixes and replay (2026-10-01, after the owner's "all recommended").** The plan's review asked for ten changes, all applied: (1) `RESTATES_OPENING` matches only an opening verb followed by a comparison, after the section names are taken out (`SECTION_NAMES`, `speaks_of_opening`), with four kept table cases; (2) `code_notes_intro` brackets only the points the code notes invite, tested with and without; (3) the same opening test drops an AI note across the service when the code note names the opening, tested both ways, and T7 Step 3 asks about it; (4) the confirm stays mounted in every branch of `CardNotes`, closes when Revise stops being offered or the review changes, and falls back to the heading, with a new test; (5) the T3, T4 and T6 greps name a failing test, and the faded-notes test waits for the line to go on the second review; (6) the faded list is described by the line (`aria-describedby`), tested; (7, 8) clarification 5 and question 4 state Undo after Revise or Regenerate and another tab's Regenerate or Revise; (9) T4 updates the module docstring on `revise_section`; (10) T7 Step 2 names no count. The directives of T1-T5 were then replayed onto a fresh detached worktree of the branch at `332fe18` (`faa0ecb` plus docs only; symlinks to the repo's `.venv` and `frontend/node_modules`), running each task's commands:
- All 68 directives applied (T1 6, T2 4, T3 35, T4 19, T5 4); every Replace anchor occurred exactly once; the result matched the build worktree's but for two comments.
- Every "see it fail" output matched as quoted (T1 two failures, `2 failed, 12 passed`; T2 `2 failed, 14 passed`; T3 eight failures, `8 failed | 21 passed (29)`; T4 five failures, `5 failed | 26 passed (31)`), and every count matched the table: backend 1218, then 1220 (11 skipped); frontend 572, then 574 in 78 files (three files three times after T3 and T4, the whole suite three times at the end, with no `×` or `FAIL` line); typecheck 0 and lint 0; the docs tests `89 passed`, owner markers `4`, no em dash added, `2 files changed, 18 insertions(+), 3 deletions(-)`; the OpenAPI export and `gen:api` left the API files unchanged; no raw HTML. No flaky run this time.
- Not run while planning: the production build (Turbopack refuses the replay's symlinked `node_modules`; T6 runs it in the real checkout), the pushes, the PR and CI, the merge and the owner's checks, and any call to OpenAI.

**Review fixes (a0959fb).** The build's whole-branch review asked for one important pair and seven minor changes, made in one commit under owner decision 1 (no owner-visible change beyond what the owner chose), so the code now differs from the T1-T4 directives above where it says here; the directives are kept as built. (I1) "Replace your text?" closes, sending nothing, only on this card's changes: Revise no longer offered, this card's review entry replaced (a new review, the card went stale or lost its notes) or its text changed (another tab's edit, even to a card already faded); other cards' changes leave it open (clarification 12's "the review it was opened on is replaced" is now this card's entry and text). (M4) The text that describes these rules (the module docstring, the `drop_restated` comment, `CardNotes`'s docstring) was rewritten to match. (M3) A 429's wait beginning while the dialog asks closes it, and the wait shows beside Revise. (I2) The citing pattern also matches "references", "by name", "names (up to three words) the reading/passage/scripture/text/Gospel/psalm/lesson/epistle" and "refers to (up to two words) the Gospel ..."; a possessive after the scripture word ("Name the reading's central image ...", "the passages' setting") is about the reading's content, so it stays (clarification 3 widened). (M1) Across the service, an AI note on prayers opening alike is kept when it quotes something and none of it is an opening the code note names (`drop_restated_across`; 'both open with "We confess"' stays). (M2) On a card, a restated opening note goes only when it also puts the prayer beside others (`CROSS_PRAYER`: both, also, other(s), another, several, alike, "same as", "like the", "as in" ..., or a section's name), so 'Uses "Gracious God" three times.' and "Begins with 'we' three lines in a row." stay (clarification 4 narrowed). (M5) Tests: backend +2 (`test_a_note_across_the_service_on_another_shared_opening_is_kept`, `test_the_citing_pattern_runs_in_linear_time_on_100_kb`) and new table rows; frontend +7 (`review-step.test.tsx` +6: the confirm closing on staleness, on another tab's edit to a faded card, on a new review and on a 429, Undo after revising saved text, a failed or cancelled Regenerate keeping faded notes; `generation.test.tsx` +1). (M6) Each `onWritten` listener runs on its own: one that throws is logged (`console.error`) and the others and the write still run. (M7) The code-notes brackets read "(for example, a note on ...)" instead of "(another note on ...)" (clarification 2 and the T1 sketch above now quote the code). The T3 build also made two `review.test.tsx` waits deterministic (`findByText`; test only). Counts after the fixes: backend **1222 passed, 11 skipped**; frontend **581 in 78 files**.

## Spec coverage

| Owner answer or R item | Task(s) and tests |
|---|---|
| 1. No praise notes (contract rule, pinned) | T1 `test_the_prompt_asks_for_no_praise_and_no_restated_code_notes`; T7 Step 2 |
| 2. Revise on typed and archive text, the confirm, Undo, focus | T4 `notes.test.ts` "offers Revise on AI, typed and saved text …"; review-step "is offered on AI, typed and archived cards …", "asks before revising typed or saved text …", "closes Replace your text? when the notes change meanwhile …" (nothing sent; focus to the heading or Revise), the other-tab Cancel test (focus to Revise); T7 Step 4 |
| 2. The backend allows any origin | clarification 14 (no change; `ReviseIn` has no origin) |
| 3. The Benediction following the default has no Revise; once edited it has | T4 review-step "is offered on …" (the Benediction part); `notes.test.ts` (`followsDefault`) |
| 4. Faded notes: typing, Undo, other tab, Use church default; dismissable; Revise on current text; Looks good goes; a new review replaces; memory only | T3 `notes.test.ts` "fades a card's notes …"; review-step "fades a card's notes …", "keeps faded notes readable …"; T4 "asks before revising …" (Revise from a faded card sends the current text); T7 Step 5 |
| 4. Regenerate and Revise success clear | T3 `notes.test.ts` "forgets a card's notes …", review-step "fades … drops them when it is regenerated or cleared"; `review.test.tsx` "sends the card's text …" (no notes after a revision); T4 "asks before revising …" (notes go after Revise) |
| 4. "Across the service" unchanged; the in-flight rule kept | T3 "keeps faded notes readable …" (the box stays); RP's "drops the notes of a card edited while the review ran …" unchanged |
| 4. Screen readers | T3 "keeps faded notes readable …" (the textarea's description contains the line; the list "Notes on Opening Prayer" is described by it); clarification 9 |
| 5. No restated citation or opening notes; firmer prompt | T1 `test_the_prompt_asks_for_no_praise_and_no_restated_code_notes` (the line, with brackets only for the code notes present); T2 `test_ai_notes_that_restate_a_code_note_in_other_words_are_dropped` (table, with the kept notes that name a section or use "open" otherwise), `test_the_review_drops_restated_citation_and_opening_notes` (per card and across the service); T7 Step 3 |
| 6. Process: one PR, one batch, phone check, records, manual-verification items | T5 (items 4, 5, 9; R's amendment), T5 Step 4 (the batch review), T6, T7 |
| R decision 4 (Revise only on AI cards) | reversed by owner answer 2: T4, R's amendment (T5) |
| R "Notes go away when the text changes" | replaced by owner answer 4: T3, R's amendment (T5) |

## Questions for the owner

Your answers of 2026-10-01 (1-6, "all recommended") are binding and already in the plan. These are the choices the plan makes where you did not say; each is written as recommended. **Answered 2026-10-01: "all recommended" (binding;** see "Owner answers to this plan's questions"). The plan's review afterwards added the Undo and other-tab notes to question 4 and narrowed question 2; neither changes an answer.

1. **The no-praise wording** (clarification 1): "A note is only for something to change. Never praise or describe what already works. If a prayer is fine, give it no notes: its notes list is empty." Recommended: accept.
2. **Which restated opening notes go** (clarification 4): on a prayer named in "Several prayers open with …", only its AI repetition notes that talk about how it opens ("Opens like …", "Begins the same way as …") or quote the opening go; a repetition note about something else in that prayer stays, even when it names the Opening Prayer ("Repeats "mercy" four times.", "Repeats "mercy" from the Opening Prayer."). In "Across the service", an AI note that the prayers open alike goes too, since the code note already says it. Recommended: accept (narrower than dropping every repetition note on that card, so a real point is not lost).
3. **Which restated citation notes go** (clarification 3): only "Rules" notes about citing or naming scripture, and only on a card that already has the "Cites …" note. Recommended: accept.
4. **What fades and what goes** (clarification 5): typing, Undo, "Use church default" and another tab's edit fade the notes; a successful Regenerate or Revise, Clear text and New service remove them; once dimmed, they stay dimmed until the next review even if Undo puts the old words back. Undo after a successful Revise or Regenerate brings the text back without the notes. Another tab's Regenerate or Revise dims this tab's notes under the same line rather than removing them (accepted; a possible later follow-up). Recommended: accept.
5. **"Across the service"** stays as it is after an edit, not dimmed (clarification 6). Recommended: accept.
6. **The dialog's other button** is "Keep my text", as on Regenerate's dialog (clarification 12). Recommended: accept.
7. **After Revise on your text** the card shows "AI draft"; Undo brings back "Your text" (clarification 13). Recommended: accept.
8. **A card you change while a review is running** still gets no notes from that review, rather than dimmed ones (clarification 7). Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T6); the merge on your yes, then four phone checks one at a time and the records PR (T7).
