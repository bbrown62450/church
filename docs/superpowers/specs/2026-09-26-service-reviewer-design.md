# Service Reviewer: Design

Date: 2026-09-26
Status: approved in conversation; awaiting written-spec review
Builds on:
- `2026-09-25-service-rubric-design.md`
- `2026-09-26-prayer-library-design.md`
- `2026-09-25-migration-foundations-design.md` (F)
- `2026-09-25-slice-4-liturgy-design.md` (slice 4)

## Why

This is the third of Beau's cohort ideas, after the rubric and the prayer library. A second AI acts as
a tough, fair liturgical editor: it reads the whole service and leaves short notes where a prayer
misses the church's rubric, breaks a standing rule, drifts from the pastor's voice, or repeats
itself across prayers. The pastor decides what to do with the notes.

## Decisions (Beau, 2026-09-26)

| # | Decision |
|---|---|
| 1 | **Notes for you.** The reviewer leaves notes; it never rewrites anything on its own. |
| 2 | **One "Review service" button** reviews every card at once, so it can catch repetition across prayers. |
| 3 | **Review everything**, including text the pastor typed. |
| 4 | **"Revise with these notes"** appears only on AI-written cards. It **edits the draft** to fix the noted problems and keeps the rest. Typed text is never changed by the AI. |
| 5 | **Checks:** the church's rubric checklist, the standing rules, the voice profile, how it reads aloud, theology, and repetition across the service. |
| 6 | **Season language is judged by feel, not by count.** Seasonal themes may come up naturally, and naming "Easter" or "Christmas" more than once is fine. Canned or repetitive seasonal language is flagged: stock phrases like "in this season of…" or "as we journey through…", naming Ordinary Time, or the same seasonal line echoed across prayers. The writer follows the same guidance. |
| 7 | **New app only**, built right after slice 4's liturgy screen, like the prayer library. |

## Scope

In scope:
- the Review service button and its notes;
- the "Across the service" box;
- "Revise with these notes";
- the code checks;
- the AI review;
- the writer's new season guidance.

Out of scope:
- saving notes;
- reviewing custom elements, hymns or readings;
- automatic revision;
- anything in Streamlit.

This document is the source for a small add-on to slice 4. The add-on builds after slice 4's liturgy
step exists, and slice 4's own spec gets a short amendment pointing here.

## User experience (liturgy step)

**Review service.** The button sits in the liturgy step's header. It is enabled when at least one
switched-on card has text. It sends every switched-on card that has text and shows:
- a spinner;
- "Still working" after 8 s;
- **Cancel** (F §1.8; server deadline 75 s, client timeout 90 000 ms).

**Notes.**
- They appear below each card's text: a small tag chip (Checklist, Rules, Voice, Read aloud,
  Theology or Repetition), one sentence, and a dismiss **×**.
- A card has **at most 3 notes**, most important first.
- A reviewed card with no notes shows **"Looks good."**
- Notes about more than one prayer go in an **"Across the service"** box at the top of the step,
  at most 3 of them.

**Revise with these notes.**
- The button shows only on cards whose origin is `ai` and that have at least one note left.
- It sends the card's text and its remaining (undismissed) notes. The revised text replaces the card
  and the origin stays `ai`.
- The previous `{text, origin}` is kept for **Undo**, as with slice 4's Regenerate.
- Cards with origin `typed`, `archive` or `default` get notes but no Revise button.

**Notes go away when the text changes:**
- Typing in a card clears its notes, and so do Regenerate, Revise, Clear text and "Use church default".
- A review result is dropped for any card whose text changed while the review was running. This
  follows slice 4's stale-results rule (it compares the text and origin captured at request start).

**Other rules:**
- Notes are kept in client memory only. They are never saved to the draft or the archive.
- When the AI is not configured or fails, the code-check notes still appear, with a quiet line:
  "Only quick checks ran. The full review isn't available right now."

## The checks

### Layer 1: code checks (`backend/review_checks.py`, pure, no AI)

These are deterministic, free, and they run even without an OpenAI key. Each returns `Note(tag, text, source="code")`.

| Check | Tag | Note text |
|---|---|---|
| Stock seasonal phrases, case-insensitive: "in this season of", "as we journey", "on this … Sunday", "in this ordinary time" | Rules | `Stock phrase "{match}". Say it more naturally.` |
| Naming Ordinary Time ("ordinary time"), wherever it appears | Rules | `Names Ordinary Time. Leave the season unnamed.` |
| A scripture reference: a Bible book name or common abbreviation followed by a chapter number ("Mark 4", "1 Sam 3:10") | Rules | `Cites {match}. Draw on the reading's themes without naming it.` |
| The same opening words on two or more cards: the first two words after any leading "Leader:" or "People:" label, case-insensitive, punctuation dropped (for example "Gracious God") | Repetition | This goes in the "Across the service" box: `Several prayers open with "{words}".` |

Book names come from `scripture_refs.BOOKS`, the single book table from slices 2 and 3; there is no second list. `review_checks.py` builds its prose pattern from every alias in `BOOKS` (longest alias first, whole words, followed by a chapter number), then confirms each candidate with `scripture_refs.parse_refs`. That parser matches slice 3's, so "Psalm 1" never reads as "Psalm 119". Only matches that `parse_refs` turns into a span become notes. Slice 3 lands before this add-on, so the table and the parser already exist.

### Layer 2: AI review (`backend/usecases/liturgy_review.py`)

The AI gets one `complete` call with `json_mode=True`, `max_completion_tokens=2000` and the 75 s
deadline. Its messages contain:
- **Role:** "a tough, fair liturgical editor for a moderate Reformed (PC(USA)) congregation."
  The reviewer points out problems and never rewrites the prayers.
- **Standing rules:** the church's merged system prompt, the same text the writer received.
- **Season guidance:** decision 6, worded as the writer's new rule below.
- **The rubric:** for each section present, that section's checklist from the church's rubric.
- **The voice profile:** the church's `prayer_library.voice_profile`, when it is non-empty.
  With no profile, the Voice check is skipped and the instructions say so.
- **Context:** the occasion, the scripture references and the sermon text. The sermon text is
  truncated to 2,000 characters, as in the rubric spec.
- **The cards,** in section order, each labeled with its section label and origin.
- **Notes already found by code,** with the instruction not to repeat them.
- **The output contract:**
  - a JSON object `{"cards": [{"section": key, "notes": [{"tag": t, "text": s}]}], "service_notes": [{"tag": t, "text": s}]}`;
  - at most 3 notes per card and 3 service notes;
  - each note one sentence of 240 characters or fewer, naming the specific phrase at issue;
  - an empty list when a card is fine;
  - flag canned or repetitive seasonal language, not seasonal themes.

**Parsing is tolerant:**
- Invalid JSON counts as an AI failure.
- Unknown sections and tags are dropped.
- Notes are trimmed to 240 characters, and anything past the note limits is cut.

**Merge:**
- Code notes come first, because they are certain. AI notes follow in the AI's order, and the
  total is capped at 3 per card.
- An AI note that repeats a code note is dropped. A repeat is a note whose text contains the code
  note's quoted match, case-insensitive.

**Budget:**
- The prompt must stay within `MAX_PROMPT_CHARS` (24,000).
- Each card's text is truncated to 4,000 characters for review (the card itself is untouched).
- If the prompt is still too long, the voice profile is dropped first, then the sermon text.
  Only after that is the longest card truncated further.
- The review never returns `prompt_invalid` for its own additions.

### Revise (`usecases/liturgy_review.revise`)

One `complete` call. Its messages:
- **System:** the church's merged system prompt, with the voice profile appended as in the prayer-library spec.
- **User:** the section label, the rubric checklist for the section, the occasion and readings (with the
  sermon text when it is sent, truncated to 2,000 characters as in the review), the current draft, and
  the notes, followed by the instruction: "Revise this draft to address these notes
  only. Keep everything that works. Keep the same form (Leader/People lines where present) and about
  the same length. Output only the revised text."

`max_completion_tokens` is the section's slice 4 budget: 1,500, or 4,000 for Prayers of the People.

**Budget** (added 2026-09-26 after the plan check):
- The prompt must stay within `MAX_PROMPT_CHARS` (24,000).
- If it would exceed it, the voice profile is dropped first, then the sermon text, then the rubric checklist.
- If the draft plus the fixed instructions (the system prompt, the section label, the occasion and
  readings, the notes and the instruction) still exceed the cap, Revise returns 422 `prompt_invalid`
  with the message "This prayer is too long to revise." No AI call is made.

## API

Both routes live in `backend/api/routes/liturgy_review.py`, with request models at the top of the module and `extra="forbid"`.

| Route | Guard | Body | Response |
|---|---|---|---|
| `POST /liturgy/review` | `require_church` | `{occasion ≤300, scriptures ≤20×≤200, sermon_text?: {ref ≤200, text ≤20000}, cards: [{section: SectionKey, origin: "ai"\|"typed"\|"archive"\|"default", text ≤20000}] (1..8, unique sections)}` | `{cards: [{section, notes: [Note]}], service_notes: [Note], ai_status: "ok"\|"not_configured"\|"busy"\|"timeout"\|"rate_limited"\|"error"}` |
| `POST /liturgy/revise` | `require_church` | `{section: SectionKey, text ≤20000, notes: [str ≤240] (1..3), occasion, scriptures, sermon_text?}` | `{text}` |

- `Note = {tag: "checklist"|"rules"|"voice"|"read_aloud"|"theology"|"repetition", text: str, source: "code"|"ai"}`.
- The rubric, the system prompt and the voice profile are read on the server from the active church's settings,
  never from the client (slice 4 tenancy rule). They are read in one `session_scope`, which is closed
  before the AI call (F §1.8).
- **Review** returns 200 even when the AI fails: the code notes are still returned, and `ai_status` says why
  the AI part is missing. This follows slice 4's per-section error pattern. It charges the `ai` bucket 1
  only when an AI call is made (F §1.8). When the bucket is empty, the AI call is skipped and
  `ai_status` is `rate_limited`, so the code notes still come back.
- **Revise** returns AI failures as HTTP statuses (503 `ai_not_configured` or `ai_busy`, 504 `ai_timeout`, 502
  `ai_upstream_error`), as `/hymns/suggestions` does, and charges the `ai` bucket 1. A draft too long to revise
  returns 422 `prompt_invalid` "This prayer is too long to revise." (Revise §Budget).
- The client sends review and revise the same resolved `sermon_text` as generation (slice 4 "Sermon text": the
  effective NT reading, WEB text instead of ESV under the Crossway rule, one bounded fetch, omitted when the fetch
  fails). (Added 2026-09-26.)
- Prayer text is logged at DEBUG only (F §2.5). No OpenAI text is returned to users.

## Writer: new season guidance

The default system prompt in `liturgy_prompts.DEFAULT_SYSTEM_PROMPT` changes. These sentences go:

> The occasion is given only to guide tone and theme — do not name or refer to the liturgical season or calendar in the text itself: no 'in this ordinary time,' 'in this season of...,' 'as we journey through...,' 'on this Nth Sunday...,' or similar. Exception: on a major festival (Christmas Eve/Day, Easter, Pentecost) you may name the day itself, at most once across the piece.

They are replaced with:

> Let the season's themes come through when the time calls for it, and name the season or festival where it is natural; saying 'Easter' or 'Christmas' more than once is fine. Avoid canned or repetitive seasonal language: no stock phrases like 'in this season of…,' 'as we journey through…,' or 'on this Nth Sunday…,' and never name Ordinary Time.

This lands with the reviewer add-on in the new app, after the Streamlit freeze. `streamlit-frozen`
keeps the old wording. A church whose admin saved its own system prompt keeps it.

If the migration's freeze contingency is in force instead (F §6.1 item 6: Streamlit keeps running from
`main` through a `generate_liturgy` wrapper), the wrapper keeps the old season sentences by using a frozen
copy of the old constant (for example `LEGACY_SYSTEM_PROMPT` in `liturgy_prompts`), because Streamlit gets
no new features. The new season guidance applies only to the new app (decision 7). (Added 2026-09-26.)

## Testing

Backend, per F §5:
- `review_checks`, table-tested:
  - each stock phrase, "Ordinary Time", book-and-chapter references and common abbreviations, drawn from `scripture_refs.BOOKS` aliases;
  - no false hit on "Mark" as a verb or on "the book of life";
  - repeated openings across cards.
- Review usecase with `FakeAI`:
  - The prompt carries the church's system prompt, the checklists for the present sections only, the voice profile (and says Voice is skipped when there is none), and the code notes.
  - Parsing drops unknown tags and sections, trims notes, and cuts past the note limits.
  - The merge puts code notes first and drops duplicates.
  - The budget drops the profile, then the sermon text, then truncates.
  - AI not configured, busy, timeout, rate limited or invalid JSON gives code notes plus the right `ai_status`.
  - The `ai` bucket is charged only when the AI is called.
- Revise with `FakeAI`:
  - The messages include the draft, the notes and the section checklist.
  - The token budget for each section is correct.
  - Each AI error maps to its HTTP status.
  - The budget drops the profile, then the sermon text, then the checklist; a draft still over the cap with
    only the fixed instructions returns 422 `prompt_invalid` "This prayer is too long to revise." and makes
    no AI call.
- Routes: guards, `assert_church_isolated` (another church's rubric and profile never appear), and validation.
- `DEFAULT_SYSTEM_PROMPT`: contains the new season sentences and none of the old ones.

Frontend, per F §5.5. DOM tests for:
- review happy path;
- "Looks good";
- the "Across the service" box;
- dismissing a note;
- Revise with Undo;
- Revise hidden on typed, archive and default cards;
- notes cleared on typing;
- stale results dropped;
- quick-checks-only mode;
- cancel.

Append a manual check at 375 px to `docs/manual-verification.md`.

## Dependencies

- **Slice 4:** the liturgy cards and origins, the stale-results rule, `usecases/liturgy.py`, `liturgy_prompts`
  and `integrations/openai_client`.
- **Slice 2:** the `ai` bucket.
- **The service rubric** in the new app. The rubric storage is already on main, and the ops session is folding
  the rubric into the slice 3, 4 and 6a specs.
- **The prayer library** (slice 6a) is optional: the Voice check simply skips until a profile exists.
