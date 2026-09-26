# Prayer Library and Voice Profile: Design

Date: 2026-09-26
Status: approved in conversation; awaiting written-spec review
Builds on: `2026-09-25-service-rubric-design.md`, `2026-09-25-migration-foundations-design.md` (F),
`2026-09-25-slice-4-liturgy-design.md` (slice 4), `2026-09-25-slice-6a-settings-church-design.md` (slice 6a)

## Why

This is the second of three ideas from Beau's cohort: the rubric, then a prayer library, then an
adversarial reviewer. The liturgy writer should sound like the church's pastor. Each church keeps a
small library of the pastor's own prayers. The AI reads them to draft a short **voice profile**, which
an admin can edit. Every AI-written section then gets the profile, plus one of the pastor's prayers of
the same kind as an example.

## Decisions (Beau, 2026-09-26)

| # | Decision |
|---|---|
| 1 | The prayers are scattered or in the pastor's head, so they are **pasted or typed in**. There is no document import. |
| 2 | The library starts with **a handful** of prayers (5–15), of **mixed types**. |
| 3 | The library belongs to **the church**, not to a person. |
| 4 | The writer learns from it in **two ways**: the voice profile, plus **one example of the same type**, with a rule against reusing its lines. |
| 5 | The voice profile is redrafted **only when an admin clicks "Update from my prayers"**. The admin reviews the draft before it replaces anything. |
| 6 | **New app only.** Nothing goes into the Streamlit app, which gets data-safety fixes only. |
| 7 | It is built **as part of the migration plan**, not ahead of it. The writer hook lands in slice 4 and the page in slice 6a. |
| 8 | When several prayers share a type, the example is **a different one each time** (chosen at random). |

## Scope

- **Slice 4 (liturgy):** the generation path reads the library and adds the profile and an example
  to each AI section's prompt. An empty or missing library changes nothing.
- **Slice 6a (settings):** the Prayers page, its API, and the AI draft of the voice profile.

Out of scope: document or bulletin import; seeding the library from saved services (their liturgy
mixes AI and typed text with no record of which is which); the adversarial reviewer; anything in
Streamlit.

This document is the source for both slices. Each slice's own spec gets a short amendment that points
here. This document does not edit those specs.

## Data

The library is a JSON key in `churches.settings`, following the `default_benediction` and `rubric`
precedent (F §3.5). No DDL or Alembic revision is needed.

```json
"prayer_library": {
  "prayers": [
    {"id": "<uuid4>", "type": "prayer_of_confession", "text": "...", "added_at": "2026-09-26T15:00:00Z"}
  ],
  "voice_profile": "..."
}
```

- `type` is a SectionKey (F §1.3: the 8 liturgy keys) or `"other"`. An `"other"` prayer shapes the
  voice profile only and is never used as an example. `"other"` is a value of this field alone; it is
  not added to SectionKey.
- Limits:
  - at most **30** prayers;
  - each `text` at most **6,000** characters after trimming;
  - `voice_profile` at most **2,000** characters.
- A missing key, or a stored value of the wrong shape, reads as an empty library: `{"prayers": [], "voice_profile": ""}`.
  There is no backfill.
- Every write goes through the locked settings merge (F §1.7, slice 6a `lock_and_read_actor` and
  `merge_settings`). A write never replaces the whole `settings` object.
- Frozen Streamlit ignores the new key.

## API (slice 6a)

All three routes live in a new module, `backend/api/routes/prayer_library.py`, and call
`backend/usecases/prayer_library.py`.

| Route | Guard | Purpose |
|---|---|---|
| `GET /church/prayer-library` | `require_church` | Returns `{prayers: [PrayerOut], voice_profile: str, can_edit: bool}`. Prayers are in the order they were added. |
| `PUT /church/prayer-library` | `require_admin` | Full replace. Body: `{prayers: [{id?: uuid, type, text}], voice_profile: str}`. Returns the same shape as `GET`. |
| `POST /church/prayer-library/voice-profile-draft` | `require_admin` + `ai` bucket, cost 1 | Drafts a profile from the **saved** prayers. Returns `{draft: str}`. The draft is **not** stored. |

**PUT semantics:**
- Texts are normalized (`\r\n` to `\n`, then trimmed).
- A prayer with a known `id` keeps its `added_at`. A new prayer gets a fresh `id` and `added_at`, and so
  does an `id` that matches no stored prayer, or one that repeats an earlier row's `id`.
- Validation raises `InvalidInput`, with `fields` keyed `prayers.<i>.text`, `prayers.<i>.type` or `voice_profile`:
  - "Prayer text is required." (blank)
  - "This prayer is too long (6,000 characters at most)."
  - "Choose a prayer type."
  - "You can keep up to 30 prayers."
  - "The voice profile is too long (2,000 characters at most)."
- The write starts with `lock_and_read_actor`, then `require_admin_role`, as every 6a admin write does.

**Draft semantics:**
- With no saved prayers: 422, "Add at least one prayer and save it first."
- Otherwise the draft calls `integrations/openai_client.complete` (F §2.8) with:
  - `max_completion_tokens=800`;
  - a 75 s deadline, matching `/hymns/suggestions`;
  - the prayers, in order, each labeled with its type.
- The instruction asks for a description of about 250 words covering:
  - how the pastor addresses God;
  - sentence length and rhythm;
  - recurring imagery;
  - theological emphases;
  - words the pastor favors or avoids;
  - structural habits.
- The instruction also asks the AI to describe the style without quoting whole lines. The result is capped at 2,000 characters.
- AI failures map to HTTP statuses, as they do for suggestions (F §1.5): 503 `ai_not_configured` or `ai_busy`, 504 `ai_timeout`, 502 `ai_upstream_error`. With no AI configured, the admin can still write the profile by hand.

Models live at the top of the route module, with `extra="forbid"`. New error messages go through the error registry (F §1.5).

## Writer hook (slice 4)

The usecase already reads `get_church_prompts` inside one `session_scope` when a section needs the
AI. It reads the library in the same step and closes the session before any AI call (F §1.8). The
library is read fresh on every call, with no cache.

`liturgy_prompts.build_messages` gains an optional argument:
`build_messages(section, prompts, ctx, *, voice: VoiceContext | None = None)`.
`VoiceContext(profile: str, example: str | None)`.

- **System message:**
  - The church's merged system prompt as today.
  - If `profile` is non-empty, it is followed by: `\n\nWrite in the voice of this church's pastor, described here:\n{profile}`.
- **User message:**
  - The rendered template (plus the rubric checklist and sermon text, where slice 4 carries them).
  - If `example` is set, it is followed by: `\n\nFor voice only, here is a {Section Label} this pastor wrote. Do not reuse its lines or phrases:\n{example}`.
- Both blocks are appended **after** `render()`, so braces in the pastor's text are never read as
  placeholders.
- **Example choice:** a uniformly random pick among the prayers whose `type` equals the section's key.
  The chooser is injectable (`choose: Callable[[list], item]`, default `random.choice`), so tests pin it.
  When no prayer has that type, there is no example.
- **Budget:** the example is truncated to 3,000 characters.
  - If system plus user still exceeds `MAX_PROMPT_CHARS` (24,000), the example is dropped first, then the profile.
  - The library never causes `prompt_invalid`. That error still applies only when the church's own prompts are too long.
- **Unchanged:**
  - Sections the user typed are never sent to the AI, so the library does not touch them.
  - An empty library gives messages byte-identical to slice 4's baseline, so the existing assertions hold.

## Prayers page (slice 6a)

- **Route:** `/settings/prayers`, added to `SETTINGS_SECTIONS` as **Prayers**, right after **Liturgy**.
  It is a client component under `src/app/(signed-in)/(church)/settings/prayers/`, and its components go in `src/components/settings/`.
- **Hooks:** in `src/lib/queries/prayer-library.ts`, with the query key `["church", id, "prayer-library"]`. Admin mutations pass
  `meta: { forbiddenIsRole: true }`.
- **Voice profile card:**
  - A textarea with the current profile, and an **"Update from my prayers"** button.
  - While the prayer list has unsaved changes, the button is disabled with the hint "Save your prayers first."
  - The draft appears **next to** the current profile, stacked at 375 px, with two actions: **"Use this draft"**, which replaces the textarea text so the admin can still edit it before saving, and **"Keep mine"**, which dismisses the draft.
  - Waiting shows a spinner, "Still working" after 8 s, and **Cancel** (F §1.8).
- **Prayers list:**
  - Each row shows a type select (the 8 section labels plus "Other"), the first line of the prayer, and **Edit** and **Remove**. Remove asks first in a ConfirmDialog.
  - **Add a prayer** appends an open row.
  - One sticky **Save** saves the prayers and the profile together (PUT). `useLeaveGuard` protects unsaved work.
- **Other states:**
  - Empty library: "No prayers yet. Paste in a few of your own prayers so the writer can learn your voice."
  - Members see the page read-only, with the banner "Only admins can edit the prayer library. You can read it below."
  - Skeleton, ErrorState with Retry, PendingButton, toasts and inline 422 fields follow 6a's "Every page" rules. All text is rendered as React text only.

## How it fits with the rubric and the reviewer

- The **rubric** says what makes a good prayer. The **voice profile** says how the pastor sounds. The
  writer gets both.
- The future **adversarial reviewer** checks each draft against the rubric's checklist and the voice
  profile.
- The profile sits after the church's "Overall voice" system prompt, so an admin who edits both gets
  both. The system prompt comes first.

## Privacy and limits

- The pastor's prayers and the profile count as AI prompts and outputs. They are logged at DEBUG only, never at INFO (F §2.5).
  OpenAI error text is never returned to users.
- Drafting a profile costs one `ai` token (F §1.8).
- Open measurement (full-migration §6 item 18): with reasoning models, the extra prompt length must still fit the per-section
  `max_completion_tokens` budget and the 30 s timeout. Slice 4's budget test covers the worst case: a 2,000-character profile
  and a 3,000-character example on Prayers of the People.

## Testing

Backend, per F §5:
- Route guards. `assert_church_isolated` on all three routes: a non-member gets 403, and a request for another church gets 404.
- A member PUT gets the role 403.
- Every validation message, with its exact `fields` key.
- PUT keeps `added_at` for known ids and assigns new ids.
- A missing or junk stored key reads as empty.
- A concurrent PUT and liturgy-prompts save keep both keys (Postgres test, as in 6a acceptance 6).
- Draft:
  - uses `FakeAI` and asserts the message content (the prayers, their type labels, and the no-quoting instruction);
  - returns 422 with no prayers;
  - maps each AI error;
  - charges the `ai` bucket once.
- `build_messages`:
  - An empty library gives byte-identical messages.
  - The profile is appended to the system message.
  - The example is appended to the user message, and braces in the text survive.
  - A pinned chooser picks the expected prayer.
  - An `"other"` prayer is never used as an example.
  - Truncation works, and the budget drops the example first and then the profile.
- The usecase reads the library fresh: change it between two calls and the second call sees it.

Frontend, per F §5.5. DOM tests for:
- the happy path and the error state;
- a member's read-only view;
- the draft's "Use this draft" and "Keep mine";
- the "Save your prayers first" rule;
- remove with confirm;
- a 422 field error.

Append a manual check at 375 px to `docs/manual-verification.md`.

## Dependencies

- **Slice 4:** `build_messages` and `usecases/liturgy.py` (the hook), `integrations/openai_client`, and the `ai` bucket (slice 2).
- **Slice 6a:** the settings layout (5b), `lock_and_read_actor` and `merge_settings` (6a or 6b), and the error registry (F §1.5).
- **Order:** slice 4 ships the read path, which is harmless while no church has a library. Slice 6a ships the page, API and
  draft. The library can only be filled once 6a ships.
