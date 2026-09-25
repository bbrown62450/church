# Slice 4 — Liturgy step — Design

**Status:** Draft  **Depends on:** ops; 1 (platform: errors, guards, UI kit, TanStack Query, test harness); 2 (draft store, builder shell, `SHIPPED_STEPS`, rate limiter, `GET /church` profile); 3 (`integrations/openai_client.py`, `FakeAI`, hymn picks in the draft, `HymnRef` / `SlotHymns` / `SectionKey` in `api/schemas.py` with the shape frozen in F §1.3)  **Size:** M

**Date:** 2026-09-25
**Inputs:**
- Migration inventory (cited "inv §n"): §1 E (E1-E8), §2.2 rows `/liturgy/config` and `/liturgy/generate`, §3 coupling rows for app.py and worship_service.py, §4 "content hazards", §5 row 4, §7 questions 2, 11 and 12.
- Foundations spec (cited "F §n"). This spec follows it and does not restate its conventions.
- Owner decisions 1, 2, 5 and 9.
- F's "Amendments from slice specs" section, which records up front every foundation rule this slice changes (API §"Deviation from F"), so 4a does not edit F.

Ship as two PRs, both additive (F §1.11): **4a** backend (config, validator, generation, `GET /church` field), then **4b** frontend (the step). The tester keeps building real services in Streamlit until the parity gate after 5b, so a short deploy skew between them is harmless. 4b starts only after the owner has answered Risks and open questions item 7 (recorded in F's decisions table).

---

## Goal

Replace the Streamlit liturgy area (app.py:852-976) with step 3 of the builder, `/builder/liturgy`. The Streamlit area has these parts: sermon title, the "Your text" overrides expander, the section ticks, custom elements, the Generate button, a read-only preview and the communion checkbox.

The new step is an **order of worship made of editable cards**:
- one card per liturgy section, each with its own **Generate / Regenerate**;
- a bulk **Generate empty sections** button;
- a communion card;
- custom-element cards, shown in their printed positions;
- the sermon title.

Rules:
- Text the user typed is never changed by the AI.
- Errors are shown on the card and never stored.
- Generation works without an OpenAI key. Typed cards are unaffected, and only empty cards say "AI not configured".

On the backend, this slice adds:
- `GET /liturgy/config`;
- `POST /liturgy/generate`, which returns a result for each section;
- `default_benediction` on `GET /church`;
- `liturgy_config.py`;
- the prompt test-render validator that slice 6a reuses.

---

## Scope / Out of scope

### In scope

- **Backend**
  - `backend/liturgy_config.py`:
    - the constants moved out of app.py: sections, custom placements, order-of-worship outline, assurance response, communion text, first-Sunday rule, limits;
    - the default-benediction resolver.
  - `liturgy_prompts` gains the template validator (`check_template`, `template_error`, `validate_prompts`, `clean_prompt_overrides`) and the prompt builder (`build_context`, `build_messages`).
  - `backend/usecases/liturgy.py`: per-section generation. Overrides are applied first, sections run concurrently, errors are typed and returned per section.
  - `backend/api/routes/liturgy.py`: `GET /liturgy/config` and `POST /liturgy/generate`.
  - `GET /church` gains `default_benediction`.
  - `api/ratelimit.py` gains a `cost` parameter, if slice 2 did not ship one.
  - `worship_service._add_communion_liturgy` renders the moved communion blocks. The output is identical.
  - `worship_service.generate_liturgy` is deleted, after its behavior is characterized and ported.
- **Frontend**
  - `/builder/liturgy` fills in slice 2's placeholder.
  - Components: sermon title field, AI bar, section cards, landmark rows, communion card, custom-element cards and the "Add custom element" dialog.
  - `LiturgyGenerationProvider`, mounted in the builder shell, so generation continues while the user moves between steps.
  - `applyLiturgyDefaults`, wired into the draft store, for the default benediction and the communion default.
  - **Turning the step on in the shell:** `"liturgy"` is added to slice 2's `SHIPPED_STEPS`, so `StepProgress` shows the liturgy status instead of "Soon", and `SummaryPanel`'s Liturgy block replaces slice 2's "Available soon" with the F §4.7 contents (Frontend changes §Builder shell).

### Out of scope, with owner

| Item | Owner |
|---|---|
| Printing sections, sermon title, communion, custom elements and Prayers of the People (pastor copy only) in the Word files; slot-keyed hymn labels; `#None` fix | 5a (`service_output.py`, `build_docx`) |
| Persisting `custom_elements` and `hymnal` (`0005_services_extras`); loading an archived service into cards (`serviceToDraft`); what `draftToServicePayload` sends | 5a |
| Full order-of-worship preview including readings, creed and hymns | 5a (Review step) |
| Editing the default benediction and the liturgy prompts in Settings | 6a (uses this slice's resolver and validator) |
| Per-church communion text | Not planned. The static text moves unchanged. |
| Reordering custom elements that share a position | Not planned. List order is print order, as today. |
| Sending the sermon title or existing card text to the AI ("rewrite this") | Not planned (parity: E1) |
| Streaming progress (SSE) | Dropped (F D4) |

### Inventory coverage (E1-E8)

Every current behavior is either carried over, changed (the BC-n references point to "Behavior changes vs Streamlit"), or handed to a named slice.

| Ref | Current behavior (inventory) | Disposition |
|---|---|---|
| E1 | "Sermon title (for bulletin)" input, placeholder "[Sermon title]". Not sent to the AI. The docx prints "[Sermon title]" when blank. Archived and restored. Not reset on church switch. | **Carried:** a field on this step (`draft.liturgy.sermon_title`), not sent to the AI. **Changed:** label and help (BC-15). Printing → 5a; archive → 5a. The per-church draft (slice 2) fixes the church-switch leak. |
| E2 | Eight override text areas in an expander. Used verbatim, only when the section is ticked. Never written back. Filled when an archived service loads. The only way to edit liturgy. | **Changed:** editable cards (BC-1, BC-2). Verbatim rule carried. Loading archived text → 5a's `serviceToDraft` (`origin: "archive"`). |
| E2 edge | Text in an unticked section is silently ignored | **Changed** (BC-3) |
| E2 edge | With no usable client, every section gets placeholder text and overrides are discarded | **Changed** (BC-5) |
| E2 edge | Generate is blocked without `OPENAI_API_KEY`, even when every section has text | **Changed** (BC-5) |
| E3 | `DEFAULT_BENEDICTION = "Halverson"` seeded into the box, and re-seeded after a church switch. The literal word prints. AI writes the benediction only if the box is cleared. Loading a service with no benediction blanks the box. | **Changed:** per-church default with fallback "Halverson" (BC-9). The literal still prints by default; that is the owner-approved seed. The per-church draft replaces the re-seed on switch. Loading a service with no benediction → 5a mapping (card off and empty), which matches "blanks the box". |
| E4 | Eight keyless ticks, all on except Prayers of the People. Not saved. Generation replaces the liturgy wholesale. All unticked → `{}` with a success message, and Preview, Prepare and Save hidden. | **Carried:** the default switch states. **Changed:** switches persist in the draft; nothing is replaced wholesale (BC-4); nothing is hidden (F D9), and an all-off notice is shown. |
| E5 | Custom elements: label (a blank label is a silent no-op), text, "Place after" over 17 placements, Remove. Inputs not cleared. Not archived. Carried over when a service loads. Anchors are emitted even when the anchoring section is absent. An unknown `insert_after` raises `StopIteration`. | **Carried:** the 17 placement keys and labels, and the rule that a position is kept when its section is absent (the element prints in that position; docx → 5a). **Changed:** BC-12. Archiving → 5a (`0005`). The carry-over fix → 5a mapping. Unknown placements are impossible through the UI and are normalized to `end`. |
| E6 | Church prompts read fresh on each click; `- {title} (#{number})` hymn lines; `- {ref}` or "None specified." scripture lines; `opening_hymn` = `hymns[0]` or "N/A"; sequential calls with `max_tokens=1024` and no timeout; errors stored as text; `render` outside `try`; `gpt-3.5-turbo` default; raw provider errors; "Settings → Secrets" wording | **Carried:** prompts read fresh per request, the system + user message shape, the scripture line format, "N/A" when there is no opening hymn. **Changed:** BC-6, 7, 8, 13, 14, 16, 19. The model default was removed in 3 (F §2.8). |
| E7 | Read-only preview: 8 sections as monospace text, with "People: Thanks be to God! Amen." appended to Assurance. Omits hymns, readings, sermon, creed, communion and custom elements. | **Changed:** the cards are the preview (BC-1). The assurance response is shown under its card (BC-18). The docx formatting rules appear as card hints. Landmark rows show where hymns, readings, sermon and creed fall. The full preview → 5a Review. Legacy Notion-era liturgy keys → 5a mapping (Risk 6). |
| E8 | Communion default = first Sunday of the month, set once when the key is absent. Checkbox label and help text. The docx inserts static text after the Second Hymn. Archived and restored. Ignores the church timezone. Not per church. Not previewed. | **Carried:** the rule, the label, the static text (moved verbatim) and the position. **Changed:** BC-10, BC-11. Docx → 5a. Archive → 5a. |
| inv §3 | app.py:67, 148-166, the four section-list copies and 969-971; app.py:926-945 (env-var gate, no `try`); worship_service.py:705-724 and 763-764 (UI-shaped errors) | Moved to `liturgy_config.py`, `usecases/liturgy.py` and typed errors (Backend changes §6) |
| inv §4 | "Error placeholders stored as liturgy"; "Halverson literal"; malformed-prompt crash (inv §0 item 4) | Fixed: BC-6, BC-9, BC-7 |

### Interfaces this slice assumes

| From | Interface |
|---|---|
| 1 | `domain_errors.py` (`InvalidInput`, `NotFound`, `NotConfigured`, `Busy`, `UpstreamError`, `UpstreamTimeout`, each with `.code` and `.message`); `db.ids.as_uuid`; `assert_church_isolated`; `test_route_guards.py` with its `USER_SCOPED` allowlist; `useApi()` (`api.user`, `api.church`); `handleAuthErrors`; `ConfirmDialog`, `PendingButton`, `ErrorState`, `Skeleton`, `size="touch"`; `renderWithProviders`, `installFakeApi` |
| 2 | `DraftProvider` / `useDraft()` returning `{draft, update(fn: (d: DraftV1) => DraftV1)}`; `DraftV1.liturgy` exactly as in F §4.6; `lib/draft/status.ts` (liturgy is complete when every enabled card has text; `stillNeeded(draft, SHIPPED_STEPS)`); `lib/draft/steps.ts` `SHIPPED_STEPS` (slice 2's hand-off table: this slice adds `"liturgy"`); `BuilderShell`, `StepFooter`, `SummaryPanel` (its Liturgy block reads "Available soon" until this slice replaces it); `lib/dates.ts` (`parseIsoDate`, `formatServiceDate`); `api/ratelimit.py` with an `ai` bucket (40 / 10 min / user and 400 / day / church); the `GET /church` profile response model (called `ChurchProfileOut` below) and query key `["church", id, "profile"]`; `lib/api/timeouts.ts` |
| 3 | `integrations/openai_client.py`: `ai_available()`, `complete(messages, *, max_completion_tokens, json_mode=False) -> str`, the error mapping in F §2.8, and `set_ai_for_tests()` / `FakeAI`. `draft.hymns.slots: Record<Slot, HymnPick \| null>`. `api/schemas.py`: `HymnRef`, `SlotHymns` and `SectionKey`, created in 3 with the shape frozen in F §1.3. |

If 2 did not ship `ratelimit.consume(..., cost=)`, or 3 did not ship a by-id hymn lookup, this slice adds them. Both additions are listed under Backend changes.

**`HymnRef`, `SlotHymns` and `SectionKey`: shape frozen in F §1.3; created in 3.** The one definition is `HymnRef{hymn_id: UUID | null, title: str ≤300, number: int 0..100 000 | null, hymnal: str ≤20 | null}` with **no pattern on `hymnal`**, plus `SlotHymns{opening, response, closing: HymnRef | null}` and the 8-key `SectionKey` literal, all `extra="forbid"` (restated in API §Schemas for reference). Slice 3 lands first and creates them with exactly this shape; its `HymnalCode` pattern applies only to the query and path parameters that need it, never to `HymnRef`. `POST /liturgy/generate` is the first route that accepts them. 4a imports them and neither redefines nor changes them, and 5a does the same. This slice keeps its own request-validation tests for them (Testing, `test_api_liturgy.py`).

### Interfaces this slice provides

| To | Interface |
|---|---|
| 5a | `liturgy_config`: `SECTION_ORDER`, `SECTION_LABELS`, `CUSTOM_PLACEMENTS`, `PLACEMENT_KEYS`, `normalize_placement`, `OUTLINE`, `ASSURANCE_RESPONSE`, `COMMUNION_BLOCKS`, and `LIMITS` (5a's `ServiceDraft` uses these limits: sermon title ≤300, section text ≤20 000, ≤30 custom elements, label ≤200, text ≤10 000, `insert_after` ∈ `PLACEMENT_KEYS`). `api/schemas.py`: `SectionKey`, `HymnRef`, `SlotHymns` are not provided by this slice (shape frozen in F §1.3; created in 3); 4 adds the first route that accepts them, and 5a imports them unchanged. |
| 5a | **One source for the order of worship: `liturgy_config.OUTLINE`.** It is served as `GET /liturgy/config` `outline` (cached with `staleTime: Infinity`), and a test ties it to `build_docx` (Testing). 5a's `orderOfWorship` takes that outline as a parameter, `orderOfWorship(payload, variant, outline)`, with `config.outline` from `useLiturgyConfig()`, and keeps no order, anchor or heading constants of its own. 5a's `test_order_of_worship_fixture.py` and `order.test.ts` are built from `shared/liturgy_outline.json` (which this slice adds and a pytest keeps equal to the serialized `OUTLINE`) plus the variant rules: an empty hymn slot omits its heading, and Prayers of the People is pastor-only. 5a keeps `shared/order_of_worship.json` only as expected output generated from `OUTLINE`, never as a second encoding of the order. A reorder is then one change to `build_docx` plus `OUTLINE`, with the fixtures regenerated. Renaming `SLOT_HEADINGS` (5a) requires updating the `OUTLINE` labels in the same PR (Backend §1). 5a's spec states the same rule. |
| 5a | Draft invariants: card `text` never contains error text; card origins as in F §4.6; custom elements whose label is blank after trimming must be **left out** of `draftToServicePayload`. Cards carry DOM ids `card-{section_key}` and `custom-{id}`, so the Review step can link to `/builder/liturgy#card-call_to_worship`. |
| 5a | **Unknown custom-element placements are normalized to `"end"`, never dropped** (F §4.6: never destroy typed input). The client applies `normalizePlacement` when it loads a draft or maps a service. 5a's server-side mapping of stored `custom_elements` into `ServiceOut` applies `liturgy_config.normalize_placement` to each entry instead of dropping entries with an unknown `insert_after`. `ServiceDraft` still rejects an unknown placement with 422, which is safe because the client never sends one. 5a's spec states the same rule in "Normalizing stored data → Other fields", and its archive-usecase tests include a stored bogus placement that survives load and then save (as `"end"`). |
| 6a | `liturgy_prompts`: `template_error(template) -> str \| None` (the section-template check 6a calls), `check_template`, `validate_prompts`, `MAX_TEMPLATE_CHARS`, the reason strings in Backend §2, and **`clean_prompt_overrides(prompts, defaults=None)`, whose only home is `liturgy_prompts`** because it is pure. It includes the `\r\n` → `\n` normalization (Backend §2), so there is one rule for which overrides equal the default. 6a's `usecases/church_admin.py` imports it and implements neither a second copy nor its own normalization; 6a tests it through the API. **6a owns the shape of `PUT /church/liturgy-prompts`** (status, `fields` keys, message prefix, first-failure rule). This slice defines only the reason strings, and 6a's copy and examples use them verbatim (for example "It has a { or } without a partner. Use {{ or }} to print a brace."). |
| 6a | Settings key `churches.settings.default_benediction` (string), read through `liturgy_config.resolve_default_benediction(settings)`. A missing or non-string value means "Halverson". An empty string is a valid stored value meaning "no default" (the card starts empty). 6a's `PATCH /church` writes it and invalidates `["church", id, "profile"]`; the builder then follows the new default for untouched cards. |

---

## User experience

### Layout (375 px first)

The page renders inside slice 2's `BuilderShell`. It is a single column: `max-w-2xl`, 16 px gutters. At `lg`, the `SummaryPanel` sits to the right (F §4.7).

```
Step 3 of 4 · Liturgy                       [Summary]   ← shell
Sermon title  [ Living Water                       ]
              Printed in the bulletin and the pastor's copy. …
┌────────────────────────────────────────────────────┐
│ [ Generate empty sections (5) ]                    │ ← AI bar
│ Only switched-on sections with no text are written.│
│ Text you typed is never changed.                   │
└────────────────────────────────────────────────────┘
Order of worship
[● Call to Worship              Your text   ⋯]       ← section card
  ( textarea )                        [Regenerate]
[● Opening Prayer               Empty       ⋯]
  ( textarea )                        [Generate]
  ┆ Children's Moment   Custom  ⋯                    ← custom element (anchor: opening_prayer)
─ First Hymn · Be Thou My Vision                      ← landmark row
[● Prayer of Confession …]
[● Assurance of Pardon …]  People: Thanks be to God! Amen.
[● Prayer for Illumination …]
─ Old Testament Reading · Isaiah 40:1-11
─ New Testament Reading
─ Sermon Title · Living Water
─ Affirmation of Faith · Apostles' Creed
─ Second Hymn · …
[● Include communion liturgy …]                      ← communion card
[○ Prayers of the People   Pastor's copy only]       ← off: collapsed
[● Offertory Prayer …]
─ Third Hymn · …
[● Benediction                  Church default  ⋯]
[ + Add custom element ]
                        (StepFooter: Back · Next: Review)
```

- The order is `OUTLINE` from `GET /liturgy/config`. It is the same order `build_docx` prints (worship_service.py:829-943); a test enforces this.
- Custom elements appear right after the outline item that owns their placement.
- **Landmark rows** are single muted lines, not cards:
  - Hymn rows show the slot's title. Tapping one opens `/builder/hymns`.
  - Reading rows show what the Word file will print: the value from slice 2's `effectivePicks(draft)` (`{ot, nt, otAuto, ntAuto}`, `lib/draft/readings.ts`), which is the chosen reference or the automatic fallback `build_docx` uses. A fallback value carries a muted **"auto"** marker. When there are no readings at all, the row shows only its label. Tapping one opens `/builder/readings`.
  - The Sermon row shows the title, or a muted **"[Sermon title]"** when it is blank (what the docx prints). Tapping it focuses the sermon field.
  - The Affirmation row shows "Apostles' Creed".
- Inputs use `text-base md:text-sm`; primary buttons use `size="touch"` (F §4.8).
- Textareas grow with their content up to 60 vh, then scroll (`useAutosize`). Their minimum rows come from the config: 4, or 8 for Prayers of the People.
- Below `md`, while a textarea has focus, the sticky `StepFooter` hides, so the iOS keyboard does not stack on it. If slice 2's footer doesn't already do this, this slice adds it through a `useKeyboardOpen()` hook based on `visualViewport`.

### Sermon title

- Label **"Sermon title"**, placeholder "e.g. Living Water", `maxLength` 300.
- Help: **"Printed in the bulletin and the pastor's copy. If blank, both show “[Sermon title]”."**
- Writes `draft.liturgy.sermon_title`. It is not sent to the AI.

### AI bar

- Button **"Generate empty sections (n)"**. `n` counts the cards that are enabled, empty after trimming, and not already running.
- Caption: **"Only switched-on sections with no text are written. Text you typed is never changed."**
- When `n = 0`: the button is disabled, and the caption becomes **"Every switched-on section has text. Use Regenerate on a card for a new AI draft."**
- While a bulk run is active:
  - the button becomes **"Cancel"** (outline style);
  - the line reads **"Writing k of n…"**;
  - after 8 s it adds **"Still working — this can take up to a minute."**
- When the bulk run finishes, one toast (the cards may be off screen):
  - all succeeded: **"Wrote n sections."**
  - some failed: **"Wrote k of n sections. The rest show what went wrong."**
- **No-AI banner** (info), shown when `config.ai_available` is false: **"AI writing isn't set up for this app. Type each section yourself — everything else works as usual."** In that state the client sends **no** generation request (see BC-5):
  - **Generate** on an empty card, and **Generate empty sections**, mark each targeted enabled, empty card with the `ai_not_configured` message ("AI not configured. Type this section yourself.") locally. There is no request and no toast; the banner is already next to the button.
  - **Regenerate** on a card with text is disabled, with the caption **"AI isn't set up"** beside it. No confirmation dialog can open, so typed text is never offered for replacement.
  - The server still answers `ai_not_configured` per section (API §semantics 5), which covers a config fetched before the key was removed. A key added later takes effect on the next page load, when the config is fetched again.
- **Context notice** (muted), shown when the occasion is empty and there are no scriptures: **"No occasion or readings yet, so AI text will be general. Add them in Date & readings."** "Date & readings" links to `/builder/readings`.
- **All-off notice**, shown when all 8 cards are off: **"All liturgy sections are switched off. The Word files will list only hymns, readings, the sermon title and any custom elements."**

### Section card

Header row:
- a `Switch` labelled with the section name (aria-label "Include {Label}");
- the label (`h3`);
- a status chip;
- a `⋯` menu.

Body (when on):
- the textarea, placeholder **"Type your own text, or tap Generate."**;
- the section hint from the config;
- the action button.

| Origin (`card.origin`) | Chip |
|---|---|
| `empty` | Empty |
| `typed` | Your text |
| `ai` | AI draft |
| `default` | Church default |
| `archive` | From saved service |

| State | What the card shows |
|---|---|
| Off | Header only, plus the caption **"Off — not in the service. Any text is kept."** The textarea is hidden. |
| On, empty | Textarea and a **Generate** button |
| On, with text | Textarea and a **Regenerate** button (disabled with **"AI isn't set up"** when `config.ai_available` is false) |
| Queued (bulk) | Button disabled, **"Waiting…"**, and a Cancel icon button. The `⋯` menu is disabled. Typing in the textarea cancels this card's queued request, which was never sent, and the typed text stays. |
| Writing | Button spinner **"Writing…"**. The textarea is read-only and the `⋯` menu is disabled. After 8 s: **"Still working — this can take up to a minute."** A Cancel icon button. |
| Error | An inline `Alert` (`role="alert"`) with the server message and a **"Try again"** button. The text is unchanged. The alert clears on edit, retry or switch toggle. |
| Just replaced | **"Replaced with a new AI draft. Undo"** (after Regenerate) or **"Cleared. Undo"** (after Clear). It disappears on the next edit of that card or when the step unmounts. |

Section hints come from config and mirror the docx formatting (worship_service.py:44-75, 148-158):

| Section | Hint |
|---|---|
| Call to Worship | "Start lines with “Leader:” or “People:”. People lines print in bold." |
| Prayer of Confession | "Printed in bold for everyone to read together." |
| Assurance of Pardon | A fixed read-only line under the textarea, **"People: Thanks be to God! Amen."**, with "Added automatically after your text." |
| Prayers of the People | A chip, **"Pastor's copy only"** |
| Benediction, origin `default` | "Your church's default benediction. Admins can change it in Settings." (6a turns "Settings" into a link to `/settings/church`, listed in 6a's hand-offs and DOM tests) |

`⋯` menu (disabled while the card is queued or writing):
- **Clear text** (when the card has text): sets the text to "" and the origin to `empty`, and shows the Undo line.
- **Use church default** (Benediction only, when the origin is not `default`): sets the text to the church default and the origin to `default`.

Other card rules:
- Typing sets the origin to `typed`, or to `empty` if the text is now blank after trimming.
- Switching a card **off** while it is queued or writing cancels its run silently, as Cancel does. The text is unchanged. Switching it back on does not restart the run.
- The textarea has `maxLength` 20 000. A counter "n / 20,000" appears past 18 000.

### Generate and Regenerate

0. **No AI configured** (`config.ai_available` false): steps 1-3 send nothing. Generate and Generate empty sections mark the targeted cards with the local `ai_not_configured` error, and Regenerate is disabled (AI bar §No-AI banner).
1. **Generate** (empty card) sends one request for that section. On success, the text is written and the origin becomes `ai`. No toast, because the result is visible.
2. **Regenerate** (card with text):
   - **Origin `typed` or `archive`** → `ConfirmDialog`:
     - title **"Replace your text?"**;
     - body **"Regenerate replaces the text in {Label} with a new AI draft. You can undo right after."**;
     - confirm **"Replace text"**, cancel **"Keep my text"**.
   - **Origin `ai` or `default`** → runs without confirmation. The `default` text can be restored with "Use church default", and every Regenerate offers Undo.
   - On success, the previous `{text, origin}` is kept in memory for Undo.
3. **Generate empty sections**:
   - At click time, takes the cards that are enabled, empty and not running, in `SECTION_ORDER`.
   - Queues one request per section, with **at most 3 in flight**. That leaves one of the server's 4 AI slots free, so queued sections never wait out the server's 15 s `ai_busy` limit.
   - Cards with text, and cards that are off, are never sent.
4. **Cancel** (a card's own, or the AI bar's for the whole bulk run) aborts the client wait. The server finishes and discards the result (F §1.8). The card returns silently to its previous state.
5. **Navigation.** Runs live in `LiturgyGenerationProvider`, inside the builder layout:
   - Moving between builder steps does not stop them, and results land in the cards. The `SummaryPanel` Liturgy block (defined by this slice; Frontend changes §Builder shell) adds **"Writing n sections…"** to its first line.
   - Leaving `/builder/*`, switching church (keyed remount, F §4.2) or signing out aborts them.
6. **Stale results.** Each run captures `draft.created_at` and the card's `text` and `origin` when its request starts. When the result arrives, the first matching rule wins:
   - `draft.created_at` has changed (the draft was replaced by "New service" or an archive load) → dropped with the toast **"The service changed, so the AI draft for {Label} was discarded."**
   - The card was `default` at start and is still `default`, but its text changed → the church default changed mid-run (a profile refetch ran `applyLiturgyDefaults`). The user asked to replace the default, so the result is **applied**. Undo restores the new default.
   - The card's text differs from the captured text → dropped with the toast **"Kept your edits — the new AI draft for {Label} was not used."** While a request is in flight nothing on this page can change the card's text: the textarea is read-only, the `⋯` menu is disabled, and switching the card off cancels the run. So this case arises only from an edit in another tab (slice 2's cross-tab sync).
   - Otherwise the result is applied.
7. **429.** The whole queue stops. That card, and every queued card, shows **"Too many requests — try again in N s."**

### Per-card error messages

The server supplies the message. The one exception is the local `ai_not_configured` error used when the config says AI is off, whose text equals the server's. The client chooses behavior by `code` only (F §1.5).

| Code | Message shown on the card | Extra |
|---|---|---|
| `ai_not_configured` | "AI not configured. Type this section yourself." | No "Try again" |
| `ai_busy` | "The AI service is busy. Try again in a minute." | Try again |
| `ai_timeout` | "The AI took too long to answer. Try again." | Try again |
| `ai_upstream_error` | "The AI service had a problem. Try again." | Try again |
| `prompt_invalid` | "The {Label} prompt in Settings has a problem: {reason} An admin can fix it under Settings → Liturgy prompts." (every `prompt_invalid`, including the length cap; API §semantics 7) | No retry |
| `not_found` (HTTP 404) | "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step." | A link to `/builder/hymns` |
| `rate_limited` (HTTP 429) | "Too many requests — try again in N s." | Try again becomes enabled after N s |
| `timeout` (client, 90 s) | "This is taking too long. Try again." | Try again |
| `network_error` | "Can't reach the server. Check your connection and try again." | Try again |
| `internal_error` (500) | "Something went wrong. (Ref: {first 8 chars of request_id})" | Try again |
| `aborted` | none; the card returns to its previous state | — |

401 and church 403 are also passed to `handleAuthErrors`, which signs out or falls back to another church (F §4.4).

### Benediction and the church default

- A fresh draft's Benediction card is `{enabled: true, text: <church default>, origin: "default"}` (F §4.6). The church default comes from `GET /church` `default_benediction`. If that field is missing (an older backend), the client uses "Halverson".
- While the origin is `default`, the card follows the church default. If an admin changes the default in 6a, untouched drafts pick it up on the next profile refetch.
- If the church default is `""`, the card is simply empty. It counts as empty, so it is generated when switched on.
- Once the user edits the card, generates it or clears it, it no longer follows the default. **Use church default** restores it.

### Communion card

The communion card sits in the outline after the Second Hymn.

- Switch label: **"Include communion liturgy (The Sacrament of the Lord's Supper)"**.
- Helper text by origin:
  - `default`, first Sunday: **"On by default — {October 4, 2026} is the first Sunday of the month."**
  - `default`, other dates: **"Off by default — it's on by default only on the first Sunday of the month."**
  - `user`: **"You changed this."** plus a link button **"Use default"**, which sets the origin to `default` and recomputes.
  - `archive`: **"Set from the saved service."** plus **"Use default"**.
- A disclosure, **"Show communion text"**, reveals the fixed text read-only, rendered from `config.communion.blocks` (headings, paragraphs, bold responses). The caption under it: **"Printed after the Second Hymn. The same text is used for every service."**

### Custom elements

- **"+ Add custom element"** (at the end of the outline) opens a `Dialog`, which is a bottom sheet below `md`:
  - title **"Add custom element"**;
  - description **"A heading and text printed in the Word files at the place you choose."**;
  - fields:
    - **"Label"** (required, `maxLength` 200, placeholder "e.g. Children's Moment");
    - **"Text (optional)"** (`maxLength` 10 000, placeholder "Words for the bulletin or order of service");
    - **"Place"**: a `Select` over `config.custom_placements`, defaulting to "After Call to Worship" (parity: the first option);
  - buttons **Cancel** and **Add**.
  - A blank label shows **"Label is required."** under the field and focuses it.
  - On Add:
    - the label and text are trimmed and the element is appended to `draft.liturgy.custom_elements` with a new `crypto.randomUUID()` id;
    - the dialog closes;
    - the page scrolls to the new card (`#custom-{id}`).
    - The dialog's fields are empty the next time it opens.
- Each custom element renders as a card (dashed border, chip **"Custom"**) right after its placement's outline item. It has inline, editable **Label**, **Text** and **Place** fields.
  - Clearing the label shows **"Add a label, or remove this element — it won't be printed without one."**
  - `⋯` → **Remove** deletes the element and toasts **"Removed “{label}”."** with an **Undo** action, which restores it at the same index.
- At 30 elements, Add is disabled with **"You can add up to 30 custom elements."**
- Custom elements have no Generate. AI prompts exist only for the 8 sections. Owner decision 2 lists custom elements among the cards with Generate/Regenerate, so this reading is put to the owner **before 4b starts** (Risks and open questions item 7), and the answer is recorded in F's decisions table. Until answered, the design assumes "no". If the answer is yes, this slice adds the `custom` request kind and 6a adds the prompt template and validator entry (item 7).

### Loading, error and empty states

- `GET /liturgy/config` is loading → `Skeleton` blocks: the sermon field plus three card shapes. The church profile is already loaded by the church layout.
- Config failed → `ErrorState` **"Couldn't load the liturgy sections."** with the server message and **Retry** (`refetch`).
- There is no empty state: the step always shows the 8 cards.

---

## API

Conventions follow F §1:
- snake_case;
- `extra="forbid"`;
- Pydantic enforces types, enums and sizes only;
- `response_model` on every route;
- the uniform error body.

| Method | Path | Guard | Request | Response | Errors |
|---|---|---|---|---|---|
| GET | `/liturgy/config` | user | – | 200 `LiturgyConfigOut` | 401 `unauthenticated`; 503 `auth_unavailable` |
| POST | `/liturgy/generate` | church, plus the `ai` rate-limit bucket charged at **cost = number of sections that reach the AI call** (0 when AI is not configured, the request 404s, or every section needing AI fails its prompt check; semantics 8) | `GenerateLiturgyIn` | 200 `GenerateLiturgyOut`. **Section-level failures are inside the body** (below; a declared deviation from F). | 401 `unauthenticated`; 403 `forbidden` (not a member or bad `X-Church-Id`); 404 `not_found` "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step." (a non-null `hymn_id` that is not in the active church, including another church's hymn); 422 `invalid_request` with `fields`; 429 `rate_limited` + `Retry-After`; 500 `internal_error`; 503 `auth_unavailable` |
| GET | `/church` (changed) | church | – | `ChurchProfileOut` gains `default_benediction: str` | unchanged |

Other route rules:
- Client timeouts: `/liturgy/config` uses the default 20 s. `/liturgy/generate` uses 90 s (F §1.8), so `TIMEOUTS.liturgyGenerate = 90_000`.
- No idempotency key: the route writes nothing.
- Both routes are plain `def`, so they run in the threadpool (F §1.8).

### Schemas

```python
# api/schemas.py (shared; shape frozen in F §1.3, created in slice 3; restated here for reference.
# 4a and 5a import these unchanged and never redefine or tighten them.)
SectionKey = Literal["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                     "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction"]

class HymnRef(BaseModel):                      # a slot's pick; reused by 5a's ServiceDraft
    model_config = ConfigDict(extra="forbid")
    hymn_id: uuid.UUID | None = None           # null = archived snapshot, used as sent
    title: str = Field(default="", max_length=300)
    number: int | None = Field(default=None, ge=0, le=100_000)
    hymnal: str | None = Field(default=None, max_length=20)
    # No pattern on `hymnal` (F §1.3): the value echoes hymns.hymnal from the database, which CLI
    # imports never pattern-checked. Slice 3's HymnalCode pattern is used only on query and path
    # parameters, never on HymnRef. For a resolved hymn_id the server replaces title, number and hymnal
    # with the database row, so these limits only bound the request size.

class SlotHymns(BaseModel):                    # reused by 5a's ServiceDraft.hymns
    model_config = ConfigDict(extra="forbid")
    opening: HymnRef | None = None
    response: HymnRef | None = None
    closing: HymnRef | None = None

# api/routes/liturgy.py
class GenerateLiturgyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    occasion: str = Field("", max_length=300)
    scriptures: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=20)
    hymns: SlotHymns = Field(default_factory=SlotHymns)
    sections: list[SectionKey] = Field(min_length=1, max_length=4)    # UI sends exactly 1
    overrides: dict[SectionKey, Annotated[str, Field(max_length=20_000)]] = Field(default_factory=dict)

class SectionError(BaseModel):
    code: Literal["ai_not_configured", "ai_busy", "ai_timeout", "ai_upstream_error", "prompt_invalid"]
    message: str

class SectionResult(BaseModel):
    section: SectionKey
    status: Literal["override", "generated", "error"]
    text: str | None          # None only when status == "error"
    error: SectionError | None

class GenerateLiturgyOut(BaseModel):
    results: list[SectionResult]   # one per requested section, request order, duplicates removed

class SectionSpecOut(BaseModel):
    key: SectionKey; label: str; default_enabled: bool; rows: int
    pastor_copy_only: bool; hint: str | None

class PlacementOut(BaseModel):
    key: str; label: str

class OutlineItemOut(BaseModel):
    kind: Literal["section", "landmark", "communion"]
    key: str                               # section key, or landmark key (first_hymn, ot_reading, …)
    label: str                             # identical to the docx heading text
    value_source: Literal["none", "hymn_opening", "hymn_response", "hymn_closing",
                          "reading_ot", "reading_nt", "sermon_title", "fixed"]
    fixed_text: str | None                 # "Apostles' Creed" for affirmation_of_faith
    anchors_after: list[str]               # placement keys whose custom elements follow this item

class CommunionBlockOut(BaseModel):
    style: Literal["heading1", "heading2", "text", "response", "blank"]
    text: str

class CommunionOut(BaseModel):
    title: str; toggle_label: str
    default_rule: Literal["first_sunday_of_month"]
    blocks: list[CommunionBlockOut]

class LiturgyLimitsOut(BaseModel):
    max_section_text: int; max_sermon_title: int; max_custom_elements: int
    max_custom_label: int; max_custom_text: int; max_sections_per_request: int

class LiturgyConfigOut(BaseModel):
    sections: list[SectionSpecOut]         # SECTION_ORDER
    custom_placements: list[PlacementOut]  # the 17, in app.py:148-166 order
    outline: list[OutlineItemOut]
    assurance_response: str                # "People: Thanks be to God! Amen."
    default_benediction_fallback: str      # "Halverson"
    communion: CommunionOut
    limits: LiturgyLimitsOut
    ai_available: bool                     # openai_client.ai_available(); no detail about why
```

### `POST /liturgy/generate` semantics

1. **Sections.** `sections` is deduplicated, keeping the first occurrence. `overrides` entries for sections that were not requested are ignored; this matches E2's "unticked override ignored" at the API level.
2. **Needs AI.** A requested section *needs AI* when its override is missing or blank after `strip()`.
3. **Overrides.** A section with a non-blank override gets `status: "override"` and `text` = the override **exactly as sent** (owner decision 2: verbatim). No AI call is made for it.
4. **Hymns.** Non-null `hymn_id`s are resolved **within the active church** (F §1.2 rule 2), and the database title and number replace the client copy. Any id that doesn't resolve → **404 for the whole request**. A `HymnRef` with `hymn_id: null` (an archived snapshot) is used with its own title and number. Resolution runs whenever any `hymn_id` is present, even when no section needs AI, so the isolation behavior doesn't depend on configuration.
5. **AI not configured.** Every section that needs AI gets `error: ai_not_configured`. Nothing is charged to the rate limit. (The UI does not send these requests when its config says AI is off; this path serves API parity and a stale config.)
6. **Section-level failures never change the HTTP status.** One request can mix overrides, successes and failures, and a single-section request uses the same shape. HTTP errors are reserved for request-level problems (auth, church, hymn id, validation, rate limit, crash). This departs from F's registry on purpose; see "Deviation from F" below.
7. **Section error codes and messages** are the only strings returned:

   | Cause | `code` | `message` |
   |---|---|---|
   | AI not configured (including a non-ASCII key; F §2.8) | `ai_not_configured` | "AI not configured. Type this section yourself." |
   | `Busy` from the client (semaphore wait > 15 s, or OpenAI 429) | `ai_busy` | "The AI service is busy. Try again in a minute." |
   | `UpstreamTimeout` | `ai_timeout` | "The AI took too long to answer. Try again." |
   | `UpstreamError`; an empty answer; an answer > 20 000 chars; any unexpected exception (logged at ERROR with the stack trace) | `ai_upstream_error` | "The AI service had a problem. Try again." |
   | The stored template fails `check_template` | `prompt_invalid` | "The {Label} prompt in Settings has a problem: {reason} An admin can fix it under Settings → Liturgy prompts." ({reason} is the Backend §2 table message) |
   | System + rendered user prompt > 24 000 chars (F §2.8) | `prompt_invalid` | Same template, with {reason} = "It is too long once the readings and hymns are added." |

   **One rule for every `prompt_invalid`:** the message is always "The {Label} prompt in Settings has a problem: {reason} An admin can fix it under Settings → Liturgy prompts.", where {Label} is the section's `SECTION_LABELS` value and {reason} is `PromptInvalid.reason`. `test_usecase_liturgy.py` pins both cases verbatim.

   Upstream, SDK and database text is logged, never returned (F §1.5).
8. **Rate limit.** The `ai` bucket is charged only for sections that will actually call the AI. The usecase calls a `charge(n)` callback supplied by the route once, **after** hymn resolution and after `build_messages` has run for every section needing AI. `n` is the number of sections about to call `ai.complete`. `charge` is not called when `n` is 0, which covers: overrides only, AI not configured, a 404 hymn id (raised before), and every section needing AI failing `prompt_invalid`. If `charge` raises 429, no AI call is made. With at most 4 sections per request, one request costs at most 4 tokens.

**Deviation from F (declared; recorded in F's "Amendments from slice specs", citing this slice).** On this route only, AI and prompt failures are per-section results inside a 200 body, not HTTP errors. This overrides:
- F §1.5 status registry rows 422 `prompt_invalid`, 503 `ai_not_configured` / `ai_busy`, 502 `ai_upstream_error` and 504 `ai_timeout`. On `/liturgy/generate` these codes arrive as `SectionError`, with the same codes and messages. `/hymns/suggestions` (slice 3) still returns them as HTTP statuses, so the frontend `ApiErrorCode` union keeps them.
- F §1.8 "An upstream timeout on the server → 504 … `ai_timeout`".
- F §2.8 cost guard "422 `prompt_invalid` 'This prompt is too long.'". Here it is a section-level `prompt_invalid` with the unified message above. Slice 3's HTTP 422 is unchanged.
- The inventory's §2.2 row and §5 row 4, which list HTTP `503 ai_unavailable` and `422 prompt_invalid` next to the per-section `errors`. The per-section form replaces both HTTP forms, and `ai_unavailable` is spelled `ai_not_configured` (F registry).

Why:
1. F acceptance 15 and E2 parity need one request to return override text and `ai_not_configured` side by side. Only a per-section body can carry both.
2. Inventory §5 row 4 asks for "per-section structured errors".
3. The response shape stays the same for every section count. The rejected alternative, an HTTP error only when exactly one section is requested, would make the shape depend on the request.
4. The client already funnels both forms through one `cardErrorFrom(ApiError | SectionError)`, so the body form adds no screen logic.

The F amendment is made up front, before implementation, in F's "Amendments from slice specs" pass rather than in 4a's PR, so merge order cannot make F and this slice drift. It is one note under the §1.5 registry ("On `POST /liturgy/generate`, AI and prompt codes are returned per section inside a 200 body; see slice 4") plus matching qualifiers on the §1.8 timeout line and the §2.8 prompt-cap line. 4a does not edit F; if 4a's review changes this rule, the same PR updates that amendment.

---

## Backend changes

### 1. `backend/liturgy_config.py` (new; pure, standard library only)

The single home of the liturgy constants that app.py held (inv §3; F §2.3 step 2). Nothing is re-exported from Streamlit modules. app.py on `main` keeps its own frozen copies.

```python
@dataclass(frozen=True)
class SectionSpec:
    key: str; label: str; default_enabled: bool; rows: int
    pastor_copy_only: bool; hint: str | None; max_completion_tokens: int

SECTIONS: tuple[SectionSpec, ...]     # SECTION_ORDER order; labels = liturgy_prompts.py:29-38
SECTION_ORDER: list[str]; SECTION_LABELS: dict[str, str]   # derived from SECTIONS
CUSTOM_PLACEMENTS: tuple[tuple[str, str], ...]   # the 17 (key, label) pairs of app.py:148-166, same order and text
PLACEMENT_KEYS: frozenset[str]
OUTLINE: tuple[OutlineItem, ...]      # see below
ASSURANCE_RESPONSE = "People: Thanks be to God! Amen."    # worship_service.py:157
COMMUNION_TITLE = "The Sacrament of the Lord's Supper"
COMMUNION_TOGGLE_LABEL = "Include communion liturgy (The Sacrament of the Lord's Supper)"
COMMUNION_BLOCKS: tuple[CommunionBlock, ...]   # worship_service.py:78-145 as data, verbatim
DEFAULT_BENEDICTION_FALLBACK = "Halverson"      # app.py:67
LIMITS = Limits(max_section_text=20_000, max_sermon_title=300, max_custom_elements=30,
                max_custom_label=200, max_custom_text=10_000, max_sections_per_request=4)

def is_first_sunday_of_month(d: date) -> bool: ...   # d.day <= 7 and d.weekday() == 6 (app.py:969)
def resolve_default_benediction(settings: Mapping | None) -> str: ...
    # value = (settings or {}).get("default_benediction")
    # str → returned unchanged (including ""); anything else → DEFAULT_BENEDICTION_FALLBACK
def normalize_placement(key: str) -> str: ...   # unknown → "end"
```

`SECTIONS` values:

| Key | `default_enabled` | `rows` | `max_completion_tokens` |
|---|---|---|---|
| `prayers_of_the_people` | false (app.py:890) | 8 | 4000 |
| every other section | true | 4 | 1500 |

`prayers_of_the_people` also has `pastor_copy_only` = true. The token budgets are tuned in Risk 2.

`OUTLINE` mirrors `build_docx`'s emission order (worship_service.py:829-943):

| # | kind | key | label | value_source | anchors_after |
|---|---|---|---|---|---|
| 1 | section | call_to_worship | Call to Worship | none | call_to_worship |
| 2 | section | opening_prayer | Opening Prayer | none | opening_prayer |
| 3 | landmark | first_hymn | First Hymn | hymn_opening | first_hymn |
| 4 | section | prayer_of_confession | Prayer of Confession | none | prayer_of_confession |
| 5 | section | assurance | Assurance of Pardon | none | assurance |
| 6 | section | prayer_for_illumination | Prayer for Illumination | none | prayer_for_illumination |
| 7 | landmark | ot_reading | Old Testament Reading | reading_ot | ot_reading |
| 8 | landmark | nt_reading | New Testament Reading | reading_nt | nt_reading |
| 9 | landmark | sermon | Sermon Title | sermon_title | sermon |
| 10 | landmark | affirmation_of_faith | Affirmation of Faith | fixed ("Apostles' Creed") | affirmation_of_faith |
| 11 | landmark | second_hymn | Second Hymn | hymn_response | second_hymn |
| 12 | communion | communion | The Sacrament of the Lord's Supper | none | communion |
| 13 | section | prayers_of_the_people | Prayers of the People | none | prayers_of_the_people |
| 14 | section | offertory_prayer | Offertory Prayer | none | offertory_prayer |
| 15 | landmark | third_hymn | Third Hymn | hymn_closing | third_hymn, **benediction** ("Before Benediction") |
| 16 | section | benediction | Benediction | none | end |

- Every placement key appears exactly once across `anchors_after`.
- If 5a renames the docx hymn headings (`SLOT_HEADINGS`) when it makes them slot-keyed, it updates these `OUTLINE` labels and regenerates `shared/liturgy_outline.json` in the same PR. The outline/docx test (Testing) enforces this.
- `OUTLINE` is the only encoding of the order of worship. The frontend (5a's `orderOfWorship`) receives it as a parameter from `GET /liturgy/config`; any other fixture, such as 5a's `shared/order_of_worship.json`, is expected output generated from it.

### 2. `backend/liturgy_prompts.py` (changed)

- `SECTION_ORDER` and `SECTION_LABELS` are now imported from `liturgy_config`. The names stay, so the existing tests and 6a are unaffected.
- **New constants:**
  - `KNOWN_PLACEHOLDERS = ("occasion", "scriptures", "opening_hymn", "hymns")`;
  - `MAX_TEMPLATE_CHARS = 8000`;
  - `MAX_PROMPT_CHARS = 24_000`.

  Per-template sizes are bounded so that 8 000 (system) + 8 000 (template) + about 5 000 (scriptures and hymns) stays under 24 000.
- **Validator** (the "prompt test-render validator", reused by 6a):

  ```python
  @dataclass(frozen=True)
  class TemplateCheck:
      ok: bool
      message: str | None                         # user-facing reason when not ok
      unknown_placeholders: tuple[str, ...]       # render as blank; 6a may show them as warnings

  def check_template(key: str, template: str) -> TemplateCheck
  def template_error(template: str) -> str | None
      # the section-template check 6a calls: check_template("call_to_worship", template).message
      # (any section key gives the same result; only "system" is special). Never raises.
  def validate_prompts(prompts: Mapping[str, str]) -> dict[str, str]
      # key -> reason, failures only; keys outside PROMPT_KEYS are skipped (merge_prompts ignores
      # them, and 6a's PUT rejects them earlier with 422 invalid_request). Used by Risk 3's check.
  def clean_prompt_overrides(prompts: Mapping[str, str],
                             defaults: Mapping[str, str] | None = None) -> dict[str, str]
      # the only implementation (6a imports it); defaults=None means default_prompts().
      # Port of streamlit_views/settings.py:141-153, plus one normalization:
      #   1. each value and each default has "\r\n" replaced by "\n" (browser textareas submit CRLF);
      #   2. keep PROMPT_KEYS whose stripped normalized value is non-blank and differs from the
      #      stripped normalized default;
      #   3. values are stored normalized and stripped.
      # This is the single rule for "equal to default"; 6a's PUT uses it and has no second copy.
  ```

  `check_template(key, t)` runs these checks in order and returns the first failure:

  | Check | Message |
  |---|---|
  | `len(t) > MAX_TEMPLATE_CHARS` | "This prompt is too long (max 8,000 characters)." |
  | `key == "system"` → **stop here, ok**. The system prompt is sent as written, never formatted (worship_service.py:731), so braces in it are literal. | — |
  | `string.Formatter().parse(t)` raises `ValueError` (`{`, `}`, `{a!}`, `{a[}`) | "It has a { or } without a partner. Use {{ or }} to print a brace." |
  | A field name is empty or all digits (`{}`, `{0}`) | "Placeholders need a name, such as {occasion}." |
  | A field name contains `.` or `[` (`{a.b}`, `{a[0]}`, `{a[x]}`, `{occasion.upper}`) | "Placeholders must be a plain name such as {occasion}, with no dots or brackets." |
  | A field name is not a Python identifier (`str.isidentifier()` is false): `{"a": 1}` (parses as field `"a"` with spec ` 1`), `{"title"}`, `{ occasion }`, `{a b}`. This check comes **before** the `!`/`:` row, so JSON-like braces, the likeliest real mistake, get the brace advice. | "Placeholders must be a single word such as {occasion}. To print a { or } as text, write {{ or }}." |
  | A conversion or format spec is present (`{a!r}`, `{a:d}`, `{occasion:>10}`) | "Placeholders can't include ! or :. Write just {occasion}." |
  | Test render with a probe context (every known placeholder set to a sample string) raises **any** `Exception` (inv §0 item 4: `ValueError`, `AttributeError`, `IndexError`, `TypeError`) | "It can't be filled in. Check the { } placeholders." |
  | otherwise | ok. `unknown_placeholders` = field names not in `KNOWN_PLACEHOLDERS`, which render blank as today (liturgy_prompts.py:125-131). |

  (Verified with `string.Formatter().parse`: `{"a": 1}`, `{"title"}` and `{ occasion }` do not raise, while `{`, `}`, `{a!}` and `{a[}` do.)
- **Prompt building** (pure):

  ```python
  @dataclass(frozen=True)
  class PromptContext:
      occasion: str; scriptures: str; opening_hymn: str; hymns: str

  def build_context(*, occasion: str, scriptures: Sequence[str],
                    hymns_by_slot: Mapping[str, ResolvedHymn | None]) -> PromptContext
      # scriptures: "\n".join(f"- {s}") or "None specified."          (parity: worship_service.py:729)
      # hymns: filled slots in slot order, "- {title} (#{number})", or "- {title}" when number is None;
      #        "None chosen." when no slot is filled                       (BC-8)
      # opening_hymn: the OPENING slot's title, else "N/A"                (BC-8)

  class PromptInvalid(Exception): section: str; reason: str

  def build_messages(section: str, prompts: Mapping[str, str], ctx: PromptContext) -> list[dict]
      # check_template(section, prompts[section]) must pass, else PromptInvalid;
      # [{"role":"system","content":prompts["system"]}, {"role":"user","content":render(...)}];
      # len(system) + len(user) > MAX_PROMPT_CHARS →
      #   PromptInvalid(reason="It is too long once the readings and hymns are added.")
  ```

  The usecase turns every `PromptInvalid` into the one `prompt_invalid` message in API §semantics 7.

- `render` and `merge_prompts` are unchanged. `render` is lenient; it is called only after `check_template` passes.

### 3. `backend/usecases/liturgy.py` (new)

```python
@dataclass(frozen=True)
class SectionOutcome:
    section: str; status: Literal["override", "generated", "error"]
    text: str | None; error_code: str | None; error_message: str | None

def sections_needing_ai(sections: Sequence[str], overrides: Mapping[str, str]) -> list[str]

def generate_liturgy(*, church_id: uuid.UUID, user_id: uuid.UUID,
                     occasion: str, scriptures: Sequence[str],
                     hymns: Mapping[str, HymnRefData | None],     # slot -> ref (plain dataclass, no Pydantic)
                     sections: Sequence[str], overrides: Mapping[str, str],
                     charge: Callable[[int], None] = lambda n: None,   # the route's rate-limit charge
                     ai=openai_client) -> list[SectionOutcome]
```

Flow. No database connection is held during AI calls (F §1.8):
1. Deduplicate `sections`. Split them into override and needs-AI.
2. `with session_scope() as s:`
   - resolve non-null hymn ids with `repos.hymns.get_hymns_by_ids(church_id, ids, session=s)`. A missing id raises `NotFound("A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.")`;
   - if any section needs AI, read `repos.churches.get_church_prompts(church_id, session=s)`.

   The session closes here.
3. Override sections → `override` outcomes.
4. If sections need AI and `not ai.ai_available()` → an `ai_not_configured` outcome for each.
5. Otherwise:
   - `ctx = build_context(...)` and `prompts = merge_prompts(stored)`;
   - for each section, `build_messages`. `PromptInvalid` → a `prompt_invalid` outcome with the unified message (API §semantics 7);
   - `n` = the sections left. If `n > 0`, call `charge(n)` once. A 429 it raises propagates, and no AI call is made;
   - run those `n` sections in a `ThreadPoolExecutor(max_workers=min(4, n))`, calling `ai.complete(messages, max_completion_tokens=SECTIONS[k].max_completion_tokens)`;
   - map `NotConfigured`, `Busy`, `UpstreamTimeout` and `UpstreamError` per the table in API §semantics 7;
   - `text.strip()`. An empty result, or one over 20 000 chars, → `ai_upstream_error`;
   - any other exception is logged with `logger.exception` and becomes `ai_upstream_error`.
6. Return the outcomes in request order.

Other properties:
- **Church prompts are read on every call** (parity with E6 "read fresh on each click"; no cache).
- **Logging** (F §2.5): `liturgy.generate church=… sections=n ai=k outcomes=generated:x,override:y,error:z codes=… duration_ms=…`. Prompts and outputs are logged at DEBUG only, never at INFO.

### 4. `backend/api/routes/liturgy.py` (new) and `create_app`

- `GET /liturgy/config` (`def`, `Depends(get_current_user)`) builds `LiturgyConfigOut` from `liturgy_config` plus `openai_client.ai_available()`.
- `POST /liturgy/generate` (`def`, `Depends(require_church)`, `Depends(get_current_user)`):
  1. call the usecase once, passing `charge=lambda n: ratelimit.consume("ai", user_id=…, church_id=…, cost=n)`;
  2. map `SectionOutcome` → `SectionResult`.

  The usecase decides when and how much to charge (API §semantics 8), so a request that fails before any AI call costs nothing. The usecase stays free of `api/*` imports: `charge` is a plain callable. The route contains no SQL and no `try`.
- `create_app` includes the router.
- `/liturgy/config` is added to `USER_SCOPED` in `test_route_guards.py`.
- `frontend/src/lib/api/openapi.json` is regenerated (F §1.11).

### 5. `GET /church` (changed)

`ChurchProfileOut` gains `default_benediction: str = resolve_default_benediction(church["settings"])`. It reuses the church row slice 2 already loads for timezone and translation. Additive (F §1.11).

### 6. Other module changes

- **`repos/hymns.py`:** `get_hymns_by_ids(church_id, ids, *, session=None) -> dict[uuid.UUID, dict]`, one `SELECT … WHERE church_id = :c AND id IN (…)`, using `db.ids.as_uuid`. If slice 3 already added an equivalent by-id lookup, use that instead.
- **`repos/churches.get_church_prompts`** gains `session: Session | None = None` (F §2.2 rule 3).
- **`api/ratelimit.py`:** `consume(bucket, *, user_id, church_id=None, cost=1)` charges both of the bucket's limits by `cost` and raises the existing 429. The `rate_limit(bucket)` dependency becomes `consume(cost=1)`. This is a backward-compatible addition if slice 2 lacks it.
- **`api/schemas.py`:** no change. `SectionKey`, `HymnRef` and `SlotHymns` are imported as slice 3 created them (shape frozen in F §1.3). `routes/liturgy.py` uses them in `GenerateLiturgyIn`, which puts them in the OpenAPI snapshot for the first time.
- **`worship_service.py`:**
  - `_add_communion_liturgy(doc)` iterates `liturgy_config.COMMUNION_BLOCKS`. The docx output must be identical: characterize first (F §2.3 step 1).
  - `generate_liturgy` (worship_service.py:686-766) is **deleted** after its behavior is pinned in `test_liturgy_generation.py` against the new functions. Its only caller is app.py, which is frozen on its own branch (F D2).
  - If the freeze contingency (F §6.1 item 6) is in effect, keep `generate_liturgy` instead, as a wrapper over the new usecase with the old signature.
  - The "Settings → Secrets" and `[Configure OPENAI_API_KEY…]` strings go with it.

### Streamlit coupling removed (inv §3)

| Coupling | Now |
|---|---|
| `DEFAULT_BENEDICTION` (app.py:67, 136-137) | `liturgy_config.DEFAULT_BENEDICTION_FALLBACK` + `resolve_default_benediction` + per-church draft default |
| `CUSTOM_PLACEMENTS` (app.py:148-166) | `liturgy_config.CUSTOM_PLACEMENTS` |
| Four copies of the section list (app.py:398-399, 857-866, 880-895, 950-959) | `liturgy_config.SECTIONS` (+ shared fixture for TS) |
| First-Sunday rule (app.py:969-971) | `liturgy_config.is_first_sunday_of_month` + TS port (shared fixture) |
| Generate reads overrides from session, env-var gate, no `try` (app.py:926-945) | `usecases.liturgy.generate_liturgy` behind `POST /liturgy/generate`; the client keeps card text |
| UI-shaped errors and "Settings → Secrets" (worship_service.py:705-724, 763-764) | Typed errors → per-section `SectionOutcome` |
| Malformed template crashes generation (`render` outside `try`, inv §0 item 4) | `check_template` before `render`; failure is per section |
| Prompt cleaning in a streamlit-importing module (settings.py:141-153; inv §3 "prompt-validation part in 4") | `liturgy_prompts.clean_prompt_overrides`, the only implementation, including `\r\n` → `\n` (6a imports it for `PUT`) |
| Communion text inside a docx helper (worship_service.py:78-145) | `liturgy_config.COMMUNION_BLOCKS` |

### Tenancy and data access

- The church id comes only from `require_church`. `GenerateLiturgyIn` has no church field (`extra="forbid"`).
- Hymn ids are resolved with `church_id` in the `WHERE` clause. Another church's id → 404 (F §1.2 rule 2).
- Prompt templates are read only from the active church's settings, never from the client (inv §4 "load prompt overrides on the server").
- This slice **writes nothing** to the database. Generation is stateless, and results live only in the browser draft until 5a's save.

---

## Data and migrations

- **No schema change and no Alembic revision.**
- `churches.settings.default_benediction` is a JSON key (F §3.5): read here, written in 6a. No row is back-filled. The "seed with the current value" (owner decision 9) is the read fallback, "Halverson".
- **Frozen Streamlit compatibility:**
  - Streamlit never reads `default_benediction`. Its settings merge preserves unknown keys (F §6.2), so a 6a write survives Streamlit prompt or translation saves.
  - Streamlit keeps its own "Halverson" constant.
- **Prompt overrides written by frozen Streamlit** are not validated there. A stored template that fails `check_template` makes only that section return `prompt_invalid` in the new app. Before 6a, it is fixed in Streamlit Settings → Liturgy prompts. Risk 3 has the pre-deploy check.
- **Liturgy text persisted later (5a)** must follow F §6.2: only the 8 keys, string values, no error text. This slice guarantees that the draft never holds error text.
- **Browser draft:** no change to `DraftV1` and no version bump. Drafts created before this slice ships work unchanged. A Benediction card with `origin: "default"` picks up the church default on first load.

---

## Frontend changes

Read `frontend/node_modules/next/dist/docs/` for any App Router API used (frontend/AGENTS.md). All components are client components.

### Routes

- `src/app/(signed-in)/(church)/builder/liturgy/page.tsx` renders `<LiturgyStep />`, replacing slice 2's `<StepPlaceholder step="liturgy"/>` ("Available soon" card). `StepPlaceholder` itself stays for Review; 5a deletes it.
- On mount it scrolls to `location.hash` (`#card-…` / `#custom-…`) when present.

### Builder shell: turning the step on (slice 2's hand-off)

| File | Change |
|---|---|
| `src/lib/draft/steps.ts` (slice 2) | `SHIPPED_STEPS` gains `"liturgy"` (after slice 3's `"hymns"`). From then on `StepProgress` shows the liturgy status, never "Soon", and `stillNeeded` considers the liturgy step. |
| `src/lib/liturgy/summary.ts` (new, pure) | `liturgyCounts(draft) → {ready, enabled, communion, customCount}`: `enabled` = cards switched on; `ready` = enabled cards whose text is non-blank after trimming; `communion` = `include_communion`; `customCount` = `custom_elements.length`. The one count used by both the step status and the summary, so they cannot disagree. |
| `src/lib/draft/status.ts` (slice 2) | Liturgy step status per F §4.7, from `liturgyCounts`: `complete` (✓) when `ready === enabled` (including all cards off), else `incomplete` with **"{ready} of {enabled}"**. If slice 2's `stepStatus` already computes this, it switches to `liturgyCounts` with no behavior change. `stillNeeded` gains the liturgy rows, worded exactly as 5a's Review checklist: **"{Card label} is empty — Write or generate it"** (enabled cards only) and **"No sermon title — Add one"**, each linking to `/builder/liturgy` (to `#card-{key}` for the first). 5a's `missingItems` reuses them. |
| `src/components/builder/SummaryPanel.tsx` (slice 2) | The Liturgy block's "Available soon" is replaced by `<LiturgySummaryBlock />`. |
| `src/components/builder/liturgy/LiturgySummaryBlock.tsx` (new) | F §4.7 liturgy contents, linking to `/builder/liturgy`: <br>• **"{ready} of {enabled} liturgy sections ready"**, or **"All liturgy sections switched off"** when `enabled` is 0; while `runs` has active entries it appends **" · Writing n sections…"**; <br>• **"Communion: Yes"** or **"Communion: No"**; <br>• **"1 custom element"**, **"{k} custom elements"**, or **"No custom elements"**. |

### Components (`src/components/builder/liturgy/`)

| File | Responsibility |
|---|---|
| `LiturgyStep.tsx` | Loads config (`useLiturgyConfig`); lays out the sermon field, AI bar, notices, the outline (cards, landmarks and custom elements placed by `anchors_after`) and the Add button; skeleton and error states |
| `SermonTitleField.tsx` | Controlled input over `draft.liturgy.sermon_title` |
| `AiBar.tsx` | Bulk button, progress line, Cancel, no-AI banner, context notice, all-off notice |
| `SectionCard.tsx` | Switch, chip, `⋯` menu, textarea (`useAutosize`), hint, action button, run states, error alert, undo line, Regenerate confirmation (`ConfirmDialog`) |
| `OutlineLandmark.tsx` | One-line landmark with its value from the draft (`value_source`) and navigation on tap. Readings resolve through slice 2's `effectivePicks(draft)`, with a muted "auto" marker when `otAuto`/`ntAuto`; a blank sermon title shows a muted "[Sermon title]". |
| `CommunionCard.tsx` | Switch, origin helper, "Use default", collapsible read-only communion text |
| `CustomElementCard.tsx` | Inline label, text and place (`Select` with an `items` map, F §4.9), label-required message, remove with Undo toast |
| `AddCustomElementDialog.tsx` | `Dialog` / bottom sheet form (native `<form onSubmit>`, F §4.8) |

shadcn (base-nova) components added if missing: `switch`, `textarea`, `badge`, `dialog`, `alert`, `collapsible`.

### Library (`src/lib/liturgy/`, pure except `generation.tsx`)

| File | Contents |
|---|---|
| `cards.ts` | Draft reducers: `editCardText`, `setCardEnabled`, `applyGenerated`, `clearCard`, `useChurchDefault`, `restoreCard`, `addCustomElement`, `updateCustomElement`, `removeCustomElement` (returns `{element, index}`), `restoreCustomElement`, `normalizePlacement` (unknown → `"end"`, mirroring `liturgy_config.normalize_placement`). Selectors: `sectionsNeedingAi(draft)`, `needsRegenerateConfirm(card)` (origin `typed` or `archive` with non-blank text). |
| `defaults.ts` | `firstSundayOfMonth(dateIso)`, which uses `parseIsoDate` and never `new Date("YYYY-MM-DD")` (F §4.10). `applyLiturgyDefaults(draft, {defaultBenediction})` returns the same object when nothing changes. |
| `request.ts` | `buildGenerateRequest(draft, section)`. Occasion trimmed and cut to 300. Scriptures trimmed, blanks dropped, first 20, each cut to 200 (the ServiceDraft limits). `hymns` = the three `HymnPick`s as `HymnRef`, each `title` cut to 300. `sections: [section]`. **No `overrides`.** |
| `errors.ts` | `cardErrorFrom(ApiError \| SectionError)` → `{code, message, retryable, retryAfterSeconds?, link?}`. `localAiNotConfigured()` returns the `ai_not_configured` card error used when `config.ai_available` is false; its message equals the server's text, which `errors.test.ts` pins. |
| `queue.ts` | `createTaskQueue({concurrency: 3})` with `push(key, run)`, `cancel(key)`, `cancelAll()` and per-task `AbortController`s |
| `generation.tsx` | `LiturgyGenerationProvider` and `useLiturgyGeneration()` → `{runs, undo, generate(keys), cancel(keys?), applyUndo(key), dismissError(key)}` |

**`generation.tsx` behavior:**
- Runs are held in memory, never in the draft.
- When `config.ai_available` is false, `generate(keys)` sends nothing and sets `localAiNotConfigured()` on each key (UX §Generate step 0).
- It captures `{created_at, text, origin}` per run when the request starts and applies the stale guard (UX §Generate step 6), with its two distinct toasts.
- A card switched off, or typed into while queued, cancels that card's run.
- On 429 it cancels the queue.
- It passes 401 and church-403 `ApiError`s to `handleAuthErrors`.
- On unmount it calls `cancelAll()`.

### Card origin transitions (enforced in `cards.ts`)

| Event | `text` | `origin` |
|---|---|---|
| User edits | the new text | `typed` if it is non-blank after trimming, else `empty` |
| AI result applied | the result | `ai` |
| Clear | `""` | `empty` |
| Use church default (Benediction) | church default | `default` |
| Church default changes while `default` | new default | `default` |
| Undo | previous | previous |
| Switch toggled | unchanged | unchanged |
| Archive load (5a) | the saved text, or `""` | `archive`, or `empty` (card off) |

Communion: a toggle sets `communion_origin: "user"`. "Use default" sets it to `"default"`. While it is `default`, `applyLiturgyDefaults` keeps `include_communion = firstSundayOfMonth(readings.date_iso)`.

### Draft store integration

- **`DraftProvider` (slice 2):** runs `applyLiturgyDefaults(draft, {defaultBenediction: profile.default_benediction ?? "Halverson"})` after every `update` and whenever the `["church", id, "profile"]` data changes.
  - If slice 2 already applies the communion rule, that code moves into `applyLiturgyDefaults`, so there is one place for it.
  - The function returns the same object when nothing changes, so a no-op triggers no write.
- **`BuilderShell`:** mounts `LiturgyGenerationProvider` inside `DraftProvider`.
- **`SummaryPanel`:** its Liturgy block is `LiturgySummaryBlock` (Builder shell above); when `runs` has active entries, its first line appends "Writing n sections…".

### API client usage

- `src/lib/queries/liturgy.ts`:
  - `useLiturgyConfig()`: `api.user`, key `["ref", "liturgy-config"]`, `staleTime: Infinity` (F §4.4).
  - `generateSection(api.church, draft, section, signal)`: `POST /liturgy/generate`, `timeoutMs: TIMEOUTS.liturgyGenerate` (90 000), returns `results[0]`.
  - This is a plain async function used by the provider, because per-section queueing and abort don't fit `useMutation`. It still lives in `lib/queries`, so pages never call `apiFetch` (F §4.4).
- Types come from the generated schema (`src/lib/api/types.ts`): `LiturgyConfig`, `GenerateLiturgyIn`, `GenerateLiturgyOut`, `SectionResult`, and `ChurchProfile["default_benediction"]`. The last one is treated as optional.

---

## Behavior changes vs Streamlit

| # | Change | Why |
|---|---|---|
| BC-1 | The "Your text" expander and the read-only preview become one editable card per section. AI output lands in the card and can be edited. It was never written back before (E2, E7). | Owner decision 2 |
| BC-2 | Generate and Regenerate on each card, plus "Generate empty sections" (enabled, empty cards only). Regenerating text of origin `typed` or `archive` asks for confirmation. Undo after Regenerate or Clear. | Owner decision 2; F §4.6 |
| BC-3 | Text in a switched-off card is **kept** in the draft and shown when the card is switched back on. Before, it was silently ignored at generation (E2 edge). An off card is still not printed. | Never destroy typed input (F §4.6) |
| BC-4 | Generation no longer replaces the liturgy wholesale (E4). Unrequested sections keep their text. With every card off, nothing is hidden; a notice explains. | F D9 |
| BC-5 | **Without an OpenAI key:** typed cards work as usual; Generate marks only enabled empty cards "AI not configured. Type this section yourself." without sending a request; Regenerate is disabled on cards with text ("AI isn't set up"), so typed text is never offered for replacement; a banner explains. Before: Generate was blocked, or placeholder text replaced every section and discarded overrides (E2, E6). | Owner decision 9 |
| BC-6 | Errors appear on the card and are **never** stored, saved or printed. Before, `[Error generating …]` became liturgy text (E6, inv §4). Raw provider text is no longer shown. | F §1.5, §4.6 |
| BC-7 | A malformed admin prompt fails only its own section, with `prompt_invalid` naming the section and the reason. Before, it crashed the whole generation (inv §0 item 4). Placeholders with `.`, `[ ]`, `!` or `:` are now rejected. | Robustness; blocks attribute access in templates |
| BC-8 | `{opening_hymn}` is the **Opening slot's** hymn (before: the first filled slot, E6/D6 positional bug). `{hymns}` lists hymns without a number as `- Title`, not `(#None)`. No hymns renders "None chosen." instead of an empty string. | Correctness |
| BC-9 | The default benediction is a **per-church setting**, read with fallback "Halverson". The card shows "Church default" and follows the setting until edited. "Use church default" restores it. Before: a hard-coded literal, re-seeded per session (E3). | Owner decision 9 |
| BC-10 | The communion default **recomputes when the date changes** until the user toggles it. Before, it was set once per session (E8). It uses the draft's calendar date, whose default is timezone-aware (slice 2). "Use default" restores it. | inv §5 row 4, F §7.4 |
| BC-11 | The communion text can be viewed read-only on the step. Before, it was not previewed (E8). | Transparency |
| BC-12 | Custom elements: <br>• a blank label shows "Label is required." (before: a silent no-op); <br>• the dialog clears after Add; <br>• label, text and place can be edited after adding; <br>• Remove has Undo; <br>• elements show inline at their printed position; <br>• at most 30; <br>• an unknown placement is normalized to "end" (before: `StopIteration`, E5). <br>Archive persistence and the load carry-over fix are 5a. | Owner decision 2; inv §2.1 limits |
| BC-13 | Sections are generated in **parallel** (client: 3 in flight; server: up to 4 per request), with a spinner, "Still working…" and Cancel. Before: sequential, no timeout (E6). | F §1.8 |
| BC-14 | `max_tokens=1024` becomes `max_completion_tokens` per section (1500, or 4000 for Prayers of the People), so long prayers are less likely to be cut off (E6). | F §2.8 |
| BC-15 | Sermon title label "Sermon title (for bulletin)" becomes **"Sermon title"**, with help "Printed in the bulletin and the pastor's copy. If blank, both show “[Sermon title]”." | Owner decision 4 (the bulletin includes the sermon) |
| BC-16 | No message mentions `.env`, `OPENAI_API_KEY` or "Settings → Secrets". A non-ASCII key reads as "AI not configured" to members (E6). | F §2.8 |
| BC-17 | The section switches **persist per church in the browser draft**. Before, they reset each session (E4). They are not archived; loading a service derives them from its content (5a). | Owner decision 1 |
| BC-18 | The Assurance card shows the fixed "People: Thanks be to God! Amen." line that the docx appends. Before, it appeared only in the preview. | Parity of what prints |
| BC-19 | An empty AI answer is an error on the card, not a blank section. | Clarity |
| BC-20 | The success message "Liturgy generated. Review below and download Word." is gone. Results are visible in the cards. A bulk run ends with one toast. | F §4.8 toast rule |
| BC-21 | Generation continues while the user moves between builder steps. | Step-by-step UX (owner decision 1) |
| BC-22 | AI generation is rate-limited: the shared `ai` bucket, 40 sections / 10 min / user and 400 / day / church. Only sections that reach the AI call are charged. | F §1.8 cost exposure |

---

## Testing

### Backend (pytest, no network, `FakeAI`)

**Characterization first** (F §2.3). These are written against current code before refactoring:
- `test_communion_docx.py`: `build_docx(include_communion=True)` paragraph texts, styles and bold runs are identical before and after `COMMUNION_BLOCKS`.
- `test_liturgy_generation.py`: pins `generate_liturgy`'s prompt construction, using a fake OpenAI client that records messages:
  - the system message equals the merged system prompt;
  - `- {ref}` lines, or "None specified.";
  - an override is used verbatim with no call;
  - church overrides are applied.

  These assertions are then retargeted to `build_context`/`build_messages` and the usecase, and the old function is deleted. The two intentional changes, `{opening_hymn}` by slot and `(#None)`, get new tests that fail first.

`test_liturgy_config.py`:
- Sections, labels and default switch states equal the shared fixture `backend/tests/fixtures/shared/liturgy_sections.json` (also read by Vitest).
- `CUSTOM_PLACEMENTS` equals the 17 pairs of app.py:148-166, verbatim and in order.
- Every placement key appears exactly once in `OUTLINE.anchors_after`.
- **Outline matches the docx:**
  1. Build a docx with all 8 sections, 3 hymns, OT/NT refs, `include_sermon`, `include_prayers_of_the_people`, `include_communion`, and one custom element per placement labelled `CE:{key}`.
  2. Collect the Heading 1 and Heading 2 texts, dropping communion's internal headings (the `heading2` blocks).
  3. Assert they equal the sequence implied by `OUTLINE`: each item's label, then `CE:{anchor}` for each anchor.
- **Outline fixture:** `backend/tests/fixtures/shared/liturgy_outline.json` equals the serialized `OUTLINE` (the same shape as `OutlineItemOut`). 5a's `test_order_of_worship_fixture.py` and `order.test.ts` are built from this file plus the variant rules (an empty hymn slot omits its heading; Prayers of the People is pastor-only), and 5a's `order_of_worship.json` is expected output generated from `OUTLINE`, so the TypeScript order cannot drift from `OUTLINE`. A failure message says to regenerate the fixtures.
- `is_first_sunday_of_month` passes `shared/first_sunday.json`. Cases include:

  | Date | Expected |
  |---|---|
  | 2026-10-04 | true |
  | 2026-10-11 | false |
  | 2026-11-01 | true |
  | 2026-11-07 (Saturday) | false |
  | 2026-12-06 | true |
  | 2026-12-24 (Thursday, Christmas Eve) | false |
  | 2026-02-01 | true |
  | 2026-03-08 (day 8) | false |

- `resolve_default_benediction`:

  | Stored value | Result |
  |---|---|
  | `None` settings | "Halverson" |
  | `{}` | "Halverson" |
  | `{"default_benediction": 5}` | "Halverson" |
  | `""` | `""` |
  | `"May the Lord bless you…"` | returned verbatim |

- `normalize_placement("bogus") == "end"`.

`test_liturgy_prompts.py` (additions):
- `check_template` table, each case pinned to its exact message (parametrized `(template, expected_message)`):

  | Templates | Expected message |
  |---|---|
  | `{`, `}`, `{a!}`, `{a[}` | "It has a { or } without a partner. Use {{ or }} to print a brace." |
  | `{}`, `{0}` | "Placeholders need a name, such as {occasion}." |
  | `{a.b}`, `{a[0]}`, `{a[x]}`, `{occasion.upper}` | "Placeholders must be a plain name such as {occasion}, with no dots or brackets." |
  | `{"a": 1}`, `{"title"}`, `{ occasion }`, `{a b}` | "Placeholders must be a single word such as {occasion}. To print a { or } as text, write {{ or }}." |
  | `{a!r}`, `{a:d}`, `{occasion:>10}` | "Placeholders can't include ! or :. Write just {occasion}." |
  | 8 001 characters | "This prompt is too long (max 8,000 characters)." |

  - every default template passes;
  - `"Hi {ocassion}"` passes with `unknown_placeholders == ("ocassion",)`;
  - `{{literal}}` passes;
  - `system` containing `{` passes.
- `template_error`: `None` for every default section template, and the same message as `check_template` for each failing case above.
- `validate_prompts({"bogus": "x", "benediction": "{", "system": "{"})` returns only `{"benediction": <brace message>}`: unknown keys are skipped and `system` is not formatted.
- `clean_prompt_overrides`: ports streamlit_tests/test_settings_prompts_translation.py `test_admin_prompt_save_drops_defaults_and_reset_clears`. A value equal to the default is dropped, a blank value is dropped, a changed value is kept stripped, and unknown keys are dropped. Called both with and without an explicit `defaults` mapping.
  - **Line endings (the one rule 6a relies on):** a value equal to the default except for `\r\n` line endings is dropped; a changed value submitted with `\r\n` is stored with `\n` only; a default containing `\r\n` (explicit `defaults`) compares equal to the same text with `\n`.
- `build_context`:
  - an opening slot empty and response filled gives `opening_hymn == "N/A"`;
  - a number of `None` gives `- Title`;
  - no hymns gives "None chosen.";
  - no scriptures gives "None specified.".
- `build_messages`: over 24 000 characters raises `PromptInvalid` with reason "It is too long once the readings and hymns are added."

`test_usecase_liturgy.py` (SQLite `tmp_db`, `FakeAI`):
1. **No key (F acceptance 15).** `sections=[call_to_worship, benediction]` and `overrides={benediction: "  Go in peace.  "}` → benediction `override` with text `"  Go in peace.  "` (verbatim); call_to_worship `error/ai_not_configured`; `FakeAI.calls == 0`.
2. **AI configured.** Generated text is stripped. The church's stored `system` and section overrides reach FakeAI. They are read fresh: change the stored prompt between two calls and assert the second call sees it.
3. **Error mapping.** FakeAI raises `UpstreamTimeout("ai_timeout")`, `Busy("ai_busy")`, `UpstreamError("ai_upstream_error")` with secret text, `NotConfigured`, or `RuntimeError("secret")`; it returns `""`; or it returns 20 001 characters. Each maps to the table in API §semantics 7. The upstream text never appears in any outcome (assert "secret" is absent).
4. **Partial failure.** A church with a malformed stored `call_to_worship` template (`{"a": 1}`) → that section is `prompt_invalid` with exactly "The Call to Worship prompt in Settings has a problem: Placeholders must be a single word such as {occasion}. To print a { or } as text, write {{ or }}. An admin can fix it under Settings → Liturgy prompts."; `opening_prayer` is generated in the same call.
   - **Length cap:** a stored 20 000-character `system` prompt (possible only from unvalidated Streamlit writes), plus the default benediction template and 20 scriptures, pushes the prompt over 24 000 characters → the benediction result is exactly "The Benediction prompt in Settings has a problem: It is too long once the readings and hymns are added. An admin can fix it under Settings → Liturgy prompts."
5. **Hymns.** A hymn of the same church resolves to database values even when the client title differs. Another church's hymn id → `NotFound`. A malformed id → `NotFound`. A `hymn_id: None` snapshot uses its own title.
6. **Charging** (a recording `charge` callback):
   - two sections needing AI, both generated → `charge` called once with 2, before the first `complete()`;
   - one `prompt_invalid` section plus one good section → `charge(1)`;
   - only a `prompt_invalid` section → `charge` never called;
   - an unresolved hymn id → `NotFound`, `charge` never called;
   - overrides only, or AI not configured → `charge` never called;
   - `charge` raising → the exception propagates and `FakeAI.calls == 0`.
7. **Order and limits.** Results come back in request order after dedupe, with 4 sections run concurrently. FakeAI sleeps with a barrier to prove concurrency ≤ 4.
8. **No session during AI.** FakeAI asserts that a `session_scope` counter (patched) is 0 while `complete()` runs.

`test_api_liturgy.py` (TestClient + JWKS helper):
- `GET /liturgy/config`:
  - 401 without a token;
  - 200 without `X-Church-Id`;
  - it has 8 sections, 17 placements, 16 outline items, the communion blocks, the limits and `ai_available`.
- `POST /liturgy/generate`:
  - 401;
  - 403 for a non-member;
  - `assert_church_isolated`: a non-member gets 403, and a member of A sending church B's hymn id gets 404 with the exact message;
  - `member`, `admin` and `owner` all get 200;
  - 422 `invalid_request` with `fields` for: an unknown section, 5 sections, an empty `sections`, an extra top-level field, `church_id` in the body, a 301-character occasion, 21 scriptures, a 20 001-character override, a 301-character hymn title, a hymn number of -1, and an extra field inside a `HymnRef`;
  - a 300-character hymn title with `hymn_id: null` is accepted (the F §1.3 `HymnRef` limit 5a shares);
  - a `hymnal` value outside slice 3's `HymnalCode` pattern but within 20 characters (`"H"`, `"old code"`) with `hymn_id: null` is accepted, since `HymnRef` has no pattern (F §1.3); a 21-character `hymnal` → 422;
  - response shape per `GenerateLiturgyOut`.
- **Rate limit** (bucket remaining is read before and after each request):
  - after 40 AI sections within 10 minutes, the next request returns 429 `rate_limited` with `Retry-After`;
  - an override-only request charges 0;
  - with AI not configured, 0 is charged;
  - a request with another church's hymn id (404) charges 0;
  - a request whose only section fails `prompt_invalid` returns 200 and charges 0.

  Uses slice 2's reset helper.
- **Logs:** at INFO, `caplog` contains no prompt or output text.
- `GET /church`: `default_benediction` is "Halverson" when unset, the stored text when set, and `""` when stored as `""`.
- **Guard and contract:**
  - `test_route_guards.py` passes with `/liturgy/config` in `USER_SCOPED`, and `/liturgy/generate` has `require_church` in its dependency tree;
  - the OpenAPI snapshot test passes after regeneration;
  - `test_no_streamlit_in_core.py` still passes.

### Frontend (Vitest 3)

**unit** (`*.test.ts`):
- `cards.test.ts`: every row of the origin-transition table; `sectionsNeedingAi` (off cards and cards with text excluded; whitespace counts as empty); `needsRegenerateConfirm`; custom-element add, update, remove and restore at index; `normalizePlacement`.
- `defaults.test.ts`:
  - `firstSundayOfMonth` against `shared/first_sunday.json`;
  - `applyLiturgyDefaults`:
    - Benediction follows the default only while its origin is `default`, including `""`;
    - communion recomputes on a date change only while its origin is `default`;
    - it returns the same reference when nothing changes;
  - fresh-draft card switches equal `shared/liturgy_sections.json`.
- `request.test.ts`: one section, no `overrides`, trimmed and limited scriptures, slot-keyed `HymnRef`s including `hymn_id: null`, a 301-character hymn title cut to 300.
- `queue.test.ts`: never more than 3 running; FIFO order; `cancel(key)` and `cancelAll()` abort the signals; a cancelled task's result is never delivered.
- `errors.test.ts`: every code in the UX table.
- `summary.test.ts`: `liturgyCounts` on a fresh draft (7 enabled, the Benediction default counts as ready when non-blank), with whitespace-only text (not ready), with all cards off (`enabled` 0), and with custom elements and communion.
- `status.test.ts` (slice 2's file, additions): `SHIPPED_STEPS` contains `"liturgy"`; liturgy step status is ✓ when every enabled card has text (and when all are off), else "{ready} of {enabled}"; `stillNeeded` lists "{Card label} is empty — Write or generate it" for enabled empty cards only, and "No sermon title — Add one" when the title is blank.

**dom** (`*.test.tsx`, `renderWithProviders` + `installFakeApi`):
1. Skeleton while config loads; `ErrorState` plus Retry when it fails.
2. Cards render in outline order, with landmark values taken from the draft:
   - with no explicit reading picks, the OT and NT rows show `effectivePicks`' fallback references with the "auto" marker, and never a Psalm as the NT reading;
   - with explicit picks, they show those references without "auto";
   - a blank sermon title shows a muted "[Sermon title]", and a set title shows the title.
3. Typing sets the chip to "Your text" and persists: re-render from `localStorage` and the text is still there.
4. Generate on an empty card:
   - exactly one `POST /liturgy/generate` with `X-Church-Id` and `sections: [key]`, and no `overrides`;
   - the text is filled and the chip reads "AI draft".
5. "Generate empty sections":
   - the requests cover only the enabled, empty cards;
   - never more than 3 are open at once (a deferred fake);
   - the toast text is correct.
6. Regenerate on a typed card:
   - the confirm dialog appears;
   - "Keep my text" sends no request;
   - "Replace text" replaces it;
   - Undo restores the text and origin.
7. Error result:
   - the card shows the message and the text is unchanged;
   - the serialized draft in `localStorage` doesn't contain the message.
8. No AI (`ai_available: false`):
   - the banner shows;
   - Generate on an empty card, and "Generate empty sections", send **no** request (the fake API records zero `POST /liturgy/generate`), show no toast, and mark exactly the enabled empty cards "AI not configured. Type this section yourself." (F acceptance 15, frontend half);
   - on a typed card, Regenerate is disabled with "AI isn't set up", and no "Replace your text?" dialog can open; the text and "Your text" chip are unchanged;
   - variant with `ai_available: true` but the server answering `ai_not_configured` (stale config): the empty card shows the same message.
9. Cancel aborts, and the card returns to its previous state with no error. Switching a writing card off also cancels it silently; the `⋯` menu is disabled while queued or writing; typing in a queued card cancels its request before it is sent.
10. The stale guard:
    - replace the draft (a new `created_at`) during a run → the result is discarded with "The service changed, so the AI draft for {Label} was discarded.";
    - an edit to the card from another tab (a `storage` event) during a run → the result is discarded with "Kept your edits — the new AI draft for {Label} was not used.";
    - Regenerate on a Benediction with origin `default`; while it is writing, the profile default changes → the card shows the new default during the run, then the AI text is applied with "AI draft", and Undo restores the new default with "Church default".
11. Moving to `/builder/review` during a run and back → the result was applied (the provider lives in the shell).
12. A 429 stops the queue and every queued card shows the retry message.
13. Benediction: a fresh draft shows the church default and "Church default"; changing the profile default updates it; after editing, it doesn't follow; "Use church default" restores it.
14. Communion: a first-Sunday date is on by default; changing the date recomputes it; toggling keeps it; "Use default" restores it; the "Show communion text" blocks render.
15. Custom elements:
    - a blank label → "Label is required." with focus;
    - Add places the card after its anchor and clears the dialog;
    - editing the place moves the card;
    - Remove, then Undo, restores it at the same index;
    - Add is disabled at 30;
    - after a church switch, the other church's draft shows its own elements (ports streamlit_tests/test_streamlit_tenancy.py "custom elements are church-scoped").
16. AI and user text render as text. A card containing `<b>x</b>` shows literally (`react/no-danger` lint also enforces this).
17. **Shell turned on** (`builder-shell.test.tsx` additions):
    - `StepProgress`'s Liturgy item shows its status ("{ready} of {enabled}", or ✓ once every enabled card has text) and never "Soon";
    - the `SummaryPanel` Liturgy block shows "n of m liturgy sections ready", "Communion: Yes/No" and the custom-element count, and **no longer says "Available soon"**; it links to `/builder/liturgy`;
    - during a run it shows "Writing n sections…", which disappears when the run ends;
    - `/builder/liturgy` no longer renders the "Available soon" placeholder.

### Manual checklist

Append to `docs/manual-verification.md`. Run on the production Vercel URL at 375 px and on desktop (F §5.5).

- [ ] Open Liturgy on a fresh draft:
  - 8 cards in order; Prayers of the People off;
  - Benediction "Halverson" with "Church default";
  - landmark rows show the chosen hymns.
- [ ] Type a Call to Worship. Tap "Generate empty sections":
  - 6 sections fill within about a minute;
  - the Call to Worship is unchanged, character for character;
  - Benediction untouched.
- [ ] Regenerate the typed card: confirmation appears; Replace, then Undo.
- [ ] Start a bulk run, go to Hymns and back: the results are there. Cancel a run: the card is unchanged.
- [ ] Refresh mid-edit: text kept. Switch church and back: each church keeps its own liturgy.
- [ ] Communion is on for a first-Sunday date, off after changing the date, and stays as set after a toggle. Its text is viewable.
- [ ] Add, edit, move and remove (then Undo) a custom element. It shows after its anchor.
- [ ] At 375 px:
  - no horizontal scroll;
  - the keyboard doesn't cover the focused textarea;
  - the footer hides while typing;
  - touch targets ≥ 44 px.
- [ ] Regression pass: sign in, switch church, open every shipped nav item. Streamlit smoke check (F §6.3).

---

## Acceptance criteria

1. `GET /liturgy/config` (user guard, no church header) returns:
   - the 8 sections in `SECTION_ORDER`, with labels and default switch states equal to the shared fixture;
   - the 17 placements, verbatim from app.py:148-166;
   - an outline in which each placement is anchored exactly once;
   - the communion blocks, the limits and `ai_available`.

   *(test)*
2. The outline order equals `build_docx`'s heading order, `shared/liturgy_outline.json` equals the serialized `OUTLINE`, and the communion docx output is byte-for-byte the same paragraphs, styles and bold runs as before the move. *(test)*
3. `POST /liturgy/generate` with FakeAI:
   - returns 200 with one `generated` result per requested section, in request order;
   - uses the church's stored prompts, read on each request;
   - sets `{opening_hymn}` to the Opening slot's title;
   - never emits `(#None)`.

   *(test)*
4. With AI not configured, a request mixing an override and an empty section returns the override verbatim (`override`) and `ai_not_configured` for the other, makes no AI call and charges no rate-limit tokens. *(test; F acceptance 15)*
5. Timeout, busy, upstream error, an empty answer and unexpected exceptions become per-section errors with the exact messages in API §semantics 7. The HTTP status stays 200 (the declared deviation from F), and no upstream text appears in any response. *(test)*
6. A malformed stored template fails only its section, with `prompt_invalid` and the one message format of API §semantics 7, including the length cap. `check_template` rejects every malformed case in the table with its pinned message and accepts every default template. `template_error`, `validate_prompts` and `clean_prompt_overrides` (including its `\r\n` → `\n` normalization) behave as specified for 6a. *(test)*
7. Guards:
   - no token → 401;
   - non-member → 403;
   - member, admin and owner → 200;
   - another church's hymn id → 404 with the exact message;
   - invalid bodies → 422 with `fields`;
   - the route guard and OpenAPI contract tests pass.

   *(test + CI)*
8. The 41st AI section within 10 minutes for one user returns 429 `rate_limited` with `Retry-After`. Only sections that reach the AI call are charged: override-only, AI-not-configured, 404 hymn-id and all-`prompt_invalid` requests cost nothing. *(test)*
9. `GET /church` returns `default_benediction`: "Halverson" when unset, the stored string otherwise (including `""`). *(test)*
10. No database session is open during any AI call. *(test)*
11. In the step:
    - typing persists across refresh;
    - "Generate empty sections" sends one request per enabled empty card and never for a card with text or a card that is off;
    - at most 3 requests are in flight.

    *(test)*
12. Regenerating a `typed` or `archive` card requires confirmation, and Undo restores the previous text and origin. With `ai_available` false, no generation request is sent, empty enabled cards show "AI not configured", and Regenerate is disabled on cards with text. *(test)*
13. Errors appear only on the card. The card text and the stored draft never contain error text. *(test)*
14. The benediction and communion defaults follow the church default and the service date while untouched, stop following once changed, and can be restored. *(test)*
15. Custom elements:
    - require a label;
    - render after their anchor;
    - can be edited, moved and removed with Undo;
    - are capped at 30;
    - are separate per church.

    *(test)*
16. The liturgy step is turned on in the shell: `"liturgy"` is in `SHIPPED_STEPS`; `StepProgress` shows its status instead of "Soon"; the `SummaryPanel` Liturgy block shows the F §4.7 contents (sections ready, communion, custom-element count) and no longer says "Available soon"; Review's "Still needed" list includes the liturgy rows. *(test)*
17. A generation started on the Liturgy step completes and applies after moving to another builder step. A result for a replaced draft is discarded with the "service changed" toast. A result for a card edited in another tab is discarded with the "Kept your edits" toast. A Benediction still following the church default takes the result even if the default changed mid-run. *(test)*
18. On production at 375 px:
    - no horizontal scroll;
    - the focused textarea stays visible above the keyboard;
    - a real service's default 6 empty sections generate in under about a minute, leaving typed text untouched.

    *(deployed)*

---

## Risks and open questions

1. **Prayers of the People vs the 30 s OpenAI timeout (open).**
   - The problem: the prayer is 10-15 paragraphs, and `OPENAI_TIMEOUT_SECONDS=30` per attempt (F §2.8) may be too short on the model slice 3 picks.
   - Measure during 4a with that model.
   - If it times out, add an optional, additive `timeout_seconds` keyword to `openai_client.complete()` and give this section 60 s with no retry. That keeps the worst case (60 + 15 s wait) inside the 90 s client timeout.
2. **Token budgets on a reasoning model (open).** If `OPENAI_MODEL` is a reasoning model, reasoning tokens count toward `max_completion_tokens`, so 1500 or 4000 could produce empty or cut-off text. Empty text is reported as an error, not stored. Verify the budgets with the configured model in 4a and adjust `SectionSpec.max_completion_tokens` (a code constant, no API change).
3. **Stored prompt overrides that fail the stricter validator.**
   - Before deploying 4a, list production overrides read-only:

     ```sql
     select id, settings->'liturgy_prompts' from churches where settings->'liturgy_prompts' is not null
     ```

     `churches.settings` is `json`, not `jsonb` (models.py:51, created by `create_all`), so the jsonb `?` operator does not exist on it.
   - Run `validate_prompts` on each locally.
   - Any failure is fixed in Streamlit Settings → Liturgy prompts by the tester before the switch.
4. **The default benediction changes a saved draft.** A saved service whose Benediction card is still `origin: "default"` shows "Unsaved changes" after an admin changes the church default, because the card follows the default until edited. This is intended. 5a's archive load sets `archive` origins, so reopened services are unaffected.
5. **Cost with Regenerate.** A full liturgy is about 6 AI calls. The `ai` bucket (40 per 10 min per user) allows about 6 full passes in 10 minutes. A user who regenerates heavily can hit it and sees the retry-in-N-seconds message. Acceptable for one tester; revisit the limit if a second church onboards.
6. **Legacy liturgy keys (hand-off to 5a).** Notion-era services may store liturgy under keys outside the 8 (E7 edge). The cards cannot show them, and a full-replace `PUT` would drop them. 5a's `serviceToDraft` must detect unknown keys and warn before saving ("This older service has liturgy the new app can't show; saving will remove it."), or leave them untouched.
7. **AI Generate for custom elements (open; owner answers before 4b).** Owner decision 2 lists "custom elements" among the editable cards and says "tap Generate/Regenerate per card". This spec reads that as "custom elements are editable cards", and gives Generate only to the 8 sections, which have church prompts (UX §Custom elements). Question for the owner: *"Should custom elements such as Children's Moment get AI Generate, using a generic prompt built from their label?"*
   - **When:** put to the owner before 4b starts, together with slice 3's "overwrite every slot?" question (asked before 3b). The answer is recorded in F's decisions table.
   - **Until answered:** the design assumes no. 4a is unaffected either way.
   - **If yes:** this slice adds a `custom` request kind to `POST /liturgy/generate` (carrying the element's label, ≤200), its handling in `usecases/liturgy.py`, and Generate/Regenerate on `CustomElementCard` with the same run states and Undo as section cards (Regenerate on an element with text always confirms, since custom elements carry no origin); 6a adds the prompt template and its validator entry. No draft or schema change is needed.
   - **If no:** nothing changes; the spec stands as written.
