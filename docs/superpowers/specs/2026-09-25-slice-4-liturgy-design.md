# Slice 4 — Liturgy step — Design

**Status:** Draft  **Depends on:** ops; 1 (platform: errors, guards, UI kit, TanStack Query, test harness); 2 (draft store, builder shell, `SHIPPED_STEPS`, rate limiter, `GET /church` profile); 3 (`integrations/openai_client.py`, `FakeAI`, hymn picks in the draft, `HymnRef` / `SlotHymns` / `SectionKey` in `api/schemas.py` with the shape frozen in F §1.3)  **Size:** M

**Date:** 2026-09-25
**Inputs:**
- Migration inventory (cited "inv §n"): §1 E (E1-E8), §2.2 rows `/liturgy/config` and `/liturgy/generate`, §3 coupling rows for app.py and worship_service.py, §4 "content hazards", §5 row 4, §7 questions 2, 11 and 12.
- Foundations spec (cited "F §n"). This spec follows it and does not restate its conventions.
- Owner decisions 1, 2, 5 and 9.
- F's "Amendments from slice specs" section, which records up front every foundation rule this slice changes (API §"Deviation from F"), so 4a does not edit F.
- **Amendment 2026-09-26: the service rubric (PR #4, merged to `main`).** `docs/superpowers/specs/2026-09-25-service-rubric-design.md` changed `worship_service.generate_liturgy`, which this slice ports and then deletes. Each AI section's prompt now also carries that section's rubric checklist and the sermon (NT) text for themes, and the Prayer for Illumination and Offertory Prayer defaults say "no more than 3 sentences" (inv §1 E9). This is current behavior and is **carried over**, reusing PR #4's backend functions: backend §2 and §3, API semantics 9, and the Testing and Acceptance additions.
- **Amendment 2026-09-26: the prayer library (PR #7).** `docs/superpowers/specs/2026-09-26-prayer-library-design.md` is the source for the writer hook; it is new-app only. This slice ships the **read path**: `build_messages` gains `voice`, and the usecase reads `churches.settings["prayer_library"]`. It is harmless until 6a lets admins fill the library. The rules are summarized in backend §2 and §3 and API semantics 10, and not repeated from that spec.
- **Amendment 2026-09-26: the service reviewer (PR #8).** `docs/superpowers/specs/2026-09-26-service-reviewer-design.md` is a new-app-only add-on built right after this slice's liturgy step (4b). Its hooks into this slice are in the closing section, "Amendment 2026-09-26: service reviewer".

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
| Sending the sermon title or existing card text to the AI ("rewrite this") | Not in 4a/4b. The sermon title is never sent. The reviewer add-on (amendment 2026-09-26, PR #8) sends card text for review and revises AI-origin drafts. |
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
| E9 (amendment 2026-09-26, PR #4) | Each AI section's prompt gets its rubric checklist ("A good {Label}:" + points) and, when a sermon text is known, "Sermon text ({ref}), for themes only; do not quote, cite, or name it:" + the text cut to 2 000 characters, both appended after `render()`, so edited prompts get them too; the rubric is read fresh per click; the sermon text is the selected NT reading's passage from the session cache, fetched in the session translation when missing; the Illumination and Offertory defaults say "no more than 3 sentences" | **Carried:** the checklist and the sermon block, verbatim and in that order, through `liturgy_prompts` (backend §2) using `service_rubric.format_checklist` and the moved `sermon_text_block`; the rubric read fresh per request; the two defaults (already in `liturgy_prompts.DEFAULT_SECTION_PROMPTS`). **Changed:** BC-24 (where the sermon text comes from). |

### Interfaces this slice assumes

| From | Interface |
|---|---|
| 1 | `domain_errors.py` (`InvalidInput`, `NotFound`, `NotConfigured`, `Busy`, `UpstreamError`, `UpstreamTimeout`, each with `.code` and `.message`); `db.ids.as_uuid`; `assert_church_isolated`; `test_route_guards.py` with its `USER_SCOPED` allowlist; `useApi()` (`api.user`, `api.church`); `handleAuthErrors`; `ConfirmDialog`, `PendingButton`, `ErrorState`, `Skeleton`, `size="touch"`; `renderWithProviders`, `installFakeApi` |
| 2 | `DraftProvider` / `useDraft()` returning `{draft, update(fn: (d: DraftV1) => DraftV1)}`; `DraftV1.liturgy` exactly as in F §4.6; `lib/draft/status.ts` (liturgy is complete when every enabled card has text; `stillNeeded(draft, SHIPPED_STEPS)`); `lib/draft/steps.ts` `SHIPPED_STEPS` (slice 2's hand-off table: this slice adds `"liturgy"`); `BuilderShell`, `StepFooter`, `SummaryPanel` (its Liturgy block reads "Available soon" until this slice replaces it); `lib/dates.ts` (`parseIsoDate`, `formatServiceDate`); `api/ratelimit.py` with an `ai` bucket (40 / 10 min / user and 400 / day / church); the `GET /church` profile response model (called `ChurchProfileOut` below) and query key `["church", id, "profile"]`; `lib/api/timeouts.ts` |
| 3 | `integrations/openai_client.py`: `ai_available()`, `complete(messages, *, max_completion_tokens, json_mode=False) -> str`, the error mapping in F §2.8, and `set_ai_for_tests()` / `FakeAI`. `draft.hymns.slots: Record<Slot, HymnPick \| null>`. `api/schemas.py`: `HymnRef`, `SlotHymns` and `SectionKey`, created in 3 with the shape frozen in F §1.3. |
| PR #4 (on `main`; amendment 2026-09-26) | `backend/service_rubric.py`: `merge_rubric`, `format_checklist`, the `prayers` checklists keyed by `SECTION_ORDER`. `repos.churches.get_church_rubric_overrides(church_id)`; slice 3 gives it `session=` (slice 3 amendment), or this slice adds it if 3 did not. `worship_service._sermon_text_block` and `SERMON_TEXT_LIMIT = 2000`, which this slice **moves** into `liturgy_prompts` (backend §2) before `generate_liturgy` is deleted. The default Illumination and Offertory prompts already say "no more than 3 sentences". |
| PR #7 spec (amendment 2026-09-26) | The `prayer_library` settings shape, limits and writer-hook rules in `2026-09-26-prayer-library-design.md` §Data and §Writer hook. Nothing from 6a is needed: this slice reads the key and treats a missing or malformed value as an empty library. |
| 2 (amendment 2026-09-26) | Frontend passage query options for `["passage", translation, ref]` (`POST /scripture/passages` with one reference), so the generation provider can `queryClient.fetchQuery` the sermon text (Frontend changes, "Sermon text"); `effectivePicks(draft)` for the effective NT reading. |

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
| 6a (amendment 2026-09-26) | **Prayer library read path (PR #7).** The pure module `backend/prayer_library.py`: `PRAYER_TYPES` (the 8 `SectionKey`s plus `"other"`), the limits (`MAX_PRAYERS = 30`, `MAX_PRAYER_CHARS = 6_000`, `MAX_PROFILE_CHARS = 2_000`), `read_library(settings) -> PrayerLibrary(prayers, voice_profile)` (a missing key or a stored value of the wrong shape reads as `{"prayers": [], "voice_profile": ""}`, PR #7 §Data; it never raises) and `choose_example(library, section, *, choose=random.choice) -> str \| None`. 6a's `usecases/prayer_library.py` imports the reader and limits for `GET`/`PUT /church/prayer-library` and adds its own validation; there is one reader. `liturgy_prompts.VoiceContext` and `build_messages(..., voice=)` are what the writer uses; 6a's draft route does not use them. |
| 6a (amendment 2026-09-26) | **Rubric (PR #4).** Liturgy generation reads `churches.settings["rubric"]` fresh on every request, so 6a's rubric editor changes the next generation without any cache invalidation. |

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
─ First Reading · Isaiah 40:1-11
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
    # Amendment 2026-09-26 (PR #4; semantics 9). Optional, so the change is additive:
    sermon_text: SermonText | None = None    # the effective NT reading and its passage text, never ESV

# api/schemas.py (amendment 2026-09-26; shared with the reviewer's /liturgy/review and /liturgy/revise, F §1.3)
class SermonText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ref: str = Field(max_length=200)
    text: str = Field(max_length=20_000)

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
   | System + rendered user prompt + rubric checklist > 24 000 chars (F §2.8; checklist and wording amended 2026-09-26, backend §2) | `prompt_invalid` | Same template, with {reason} = "It is too long once the readings, hymns and rubric checklist are added." |

   **One rule for every `prompt_invalid`:** the message is always "The {Label} prompt in Settings has a problem: {reason} An admin can fix it under Settings → Liturgy prompts.", where {Label} is the section's `SECTION_LABELS` value and {reason} is `PromptInvalid.reason`. `test_usecase_liturgy.py` pins both cases verbatim.

   Upstream, SDK and database text is logged, never returned (F §1.5).
8. **Rate limit.** The `ai` bucket is charged only for sections that will actually call the AI. The usecase calls a `charge(n)` callback supplied by the route once, **after** hymn resolution and after `build_messages` has run for every section needing AI. `n` is the number of sections about to call `ai.complete`. `charge` is not called when `n` is 0, which covers: overrides only, AI not configured, a 404 hymn id (raised before), and every section needing AI failing `prompt_invalid`. If `charge` raises 429, no AI call is made. With at most 4 sections per request, one request costs at most 4 tokens.
9. **Rubric checklist and sermon text (amendment 2026-09-26, PR #4; inv E9).** For every section that needs AI, the user message is the rendered template, then that section's checklist from the church's merged rubric, then the sermon-text block, exactly as `generate_liturgy` builds them today (backend §2):
   - The rubric is read on the server in the same session as the prompts, fresh on every request. It is never accepted from the client. A church with no overrides gets the default checklists; invalid stored values fall back to the defaults.
   - The sermon block uses the request's `sermon_text.ref` and `sermon_text.text`, the text cut to 2 000 characters. It is left out when `sermon_text` is absent, when either field is blank after trimming, or when the text is the legacy `"[Could not load text]"` sentinel. The server never fetches passage text for this route, so the F §1.8 worst case is unchanged; the client supplies it (Frontend changes, "Sermon text").
   - Override sections are never sent, so neither block touches typed text.
   - The checklist counts toward the prompt-length check that raises `prompt_invalid`, because it is the church's own text, like its prompts. The sermon block does not: when the prompt is too long it is dropped instead, after the library blocks (semantics 10).
10. **Prayer library (amendment 2026-09-26; PR #7 §Writer hook, which is authoritative).** The usecase reads `churches.settings["prayer_library"]` in the same `session_scope` as `get_church_prompts`, fresh on every call, and builds one `VoiceContext(profile, example)` per section that needs AI:
    - `profile` is the stored voice profile, trimmed and capped at 2 000 characters;
    - `example` is a uniformly random prayer whose `type` equals the section key (the chooser is injectable), cut to 3 000 characters, or `None` when no prayer has that type. An `"other"` prayer is never an example.

    `build_messages` appends the profile to the system message and the example to the user message, after `render()`. It applies the trim and both caps itself (backend §2 step 5), so a pre-cut in the usecase is a harmless duplicate. When the prompt is over `MAX_PROMPT_CHARS`, the example is dropped first, then the profile, then the sermon block. The library never causes `prompt_invalid`, and an empty or missing library gives messages byte-identical to the messages without it. Nothing is added to the request or the response.

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
| 7 | landmark | ot_reading | First Reading | reading_ot | ot_reading |
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
- **Reading heading (owner decision B; resolves index open question 7).** Row 7's label is **"First Reading"** (was "Old Testament Reading"); the key `ot_reading`, the value source `reading_ot` and the anchor `ot_reading` are unchanged — only the printed heading text changes, both here (the liturgy step's landmark row and 5a's order-of-worship card) and in the Word documents (5a). Row 8's label stays "New Testament Reading"; which reading fills each slot is unchanged; the owner may rename row 8 to "Second Reading" later.
- If 5a renames the docx hymn headings (`SLOT_HEADINGS`) when it makes them slot-keyed, it updates these `OUTLINE` labels and regenerates `shared/liturgy_outline.json` in the same PR. The outline/docx test (Testing) enforces this.
- `OUTLINE` is the only encoding of the order of worship. The frontend (5a's `orderOfWorship`) receives it as a parameter from `GET /liturgy/config`; any other fixture, such as 5a's `shared/order_of_worship.json`, is expected output generated from it.

### 2. `backend/liturgy_prompts.py` (changed)

- `SECTION_ORDER` and `SECTION_LABELS` are now imported from `liturgy_config`. The names stay, so the existing tests and 6a are unaffected.
- **New constants:**
  - `KNOWN_PLACEHOLDERS = ("occasion", "scriptures", "opening_hymn", "hymns")`;
  - `MAX_TEMPLATE_CHARS = 8000`;
  - `MAX_PROMPT_CHARS = 24_000`.

  Per-template sizes are bounded so that 8 000 (system) + 8 000 (template) + about 5 000 (scriptures and hymns) stays under 24 000. *Amendment 2026-09-26:* the rubric checklist also counts (`build_messages` step 4). At its limits (12 points of 300 characters plus the heading) it adds up to about 3 700 characters, so a church at every maximum can exceed the cap. The sermon block is dropped before any error is raised, under the existing rule: like the voice blocks, it never counts toward the check, and step 5 drops it (after the example and the profile) when the total is over. If the church's own text, the readings, the hymns and the checklist are still too long, the section returns `prompt_invalid` with the reason "It is too long once the readings, hymns and rubric checklist are added."
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
      #   PromptInvalid(reason="It is too long once the readings, hymns and rubric checklist are added.")
      #   (reason amended 2026-09-26: the rubric checklist counts; see the amendment below)
  ```

  The usecase turns every `PromptInvalid` into the one `prompt_invalid` message in API §semantics 7.

- **Amendment 2026-09-26: rubric, sermon text and voice** (API semantics 9 and 10). The prompt builder carries PR #4's two blocks and PR #7's voice hook. It reuses PR #4's functions rather than re-implementing them:

  ```python
  # Moved from worship_service.py (PR #4) before generate_liturgy is deleted; same text, same tests:
  SERMON_TEXT_LIMIT = 2000
  def sermon_text_block(ref: str | None, text: str | None) -> str
      # "Sermon text ({ref}), for themes only; do not quote, cite, or name it:\n" + text[:2000],
      # or "" when ref or text is blank after strip() or text contains "[Could not load text]"

  @dataclass(frozen=True)
  class PromptContext:
      occasion: str; scriptures: str; opening_hymn: str; hymns: str
      checklists: Mapping[str, tuple[str, ...]]   # the merged rubric's "prayers", keyed by section
      sermon: str                                 # sermon_text_block(...) or ""

  def build_context(*, occasion, scriptures, hymns_by_slot,
                    rubric: Mapping | None = None,             # service_rubric.merge_rubric(overrides)
                    sermon_ref: str | None = None, sermon_text: str | None = None) -> PromptContext

  @dataclass(frozen=True)
  class VoiceContext:                              # PR #7
      profile: str
      example: str | None

  def build_messages(section: str, prompts: Mapping[str, str], ctx: PromptContext,
                     *, voice: VoiceContext | None = None) -> list[dict]
  ```

  `build_messages` builds the messages in this order:
  1. `check_template` as before; a failure raises `PromptInvalid`.
  2. `system = prompts["system"]` and `user = render(template, ctx)`.
  3. If `ctx.checklists.get(section)` is non-empty, `user += "\n\n" + service_rubric.format_checklist(SECTION_LABELS[section], checklist)` (PR #4 wording: "A good {Label}:" plus "- point" lines).
  4. If `len(system) + len(user) > MAX_PROMPT_CHARS`, raise `PromptInvalid(reason="It is too long once the readings, hymns and rubric checklist are added.")`. The checklist counts because it is the church's own text, and the reason names it because a maximum-size checklist can push a church whose prompts are near their limits over the cap (New constants). The sermon and voice blocks are not yet appended, so they never cause this error.
  5. Optional blocks, each appended **after** `render()` so braces in them are never read as placeholders:
     - `ctx.sermon` → `user += "\n\n" + ctx.sermon` (PR #4);
     - `profile = voice.profile.strip()[:2000]` (`prayer_library.MAX_PROFILE_CHARS`); when non-empty → `system += "\n\nWrite in the voice of this church's pastor, described here:\n" + profile` (PR #7). A whitespace-only profile is empty, so it adds nothing;
     - `example = voice.example[:3000]` (when set) → `user += "\n\nFor voice only, here is a {Section Label} this pastor wrote. Do not reuse its lines or phrases:\n" + example` (PR #7).

     `build_messages` itself strips the profile and applies both caps (the 3 000-character example cut is PR #7 §Writer hook "Budget"; the 2 000-character profile cap is PR #7's §Data limit, which its `PUT` validates; the strip is this slice's rule), so the result does not depend on the caller; the usecase may also pre-cut (§3), and the duplicate cuts are harmless. While the total is over `MAX_PROMPT_CHARS`, drop the example first, then the profile, then the sermon block. None of them ever raises `PromptInvalid`.
  6. Return `[system, user]`. With `voice=None`, or with a profile that is empty after `strip()` and no example, the result is byte-identical to steps 1–5 without the voice blocks; that is the baseline the existing assertions pin.

  The Prayer for Illumination and Offertory Prayer defaults already say "no more than 3 sentences" / "No more than three sentences" (PR #4). They pass `check_template` like every default, and this slice does not change their text.

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

**Amendment 2026-09-26 (PR #4 and PR #7; API semantics 9 and 10).**
- The signature gains `sermon: tuple[str, str] | None = None` (the route passes `(sermon_text.ref, sermon_text.text)`) and `choose: Callable[[list[str]], str] = random.choice` (tests pin it).
- Step 2 also reads, **in the same `session_scope`** and only when a section needs AI: `repos.churches.get_church_rubric_overrides(church_id, session=s)` and the church's `settings["prayer_library"]` through `prayer_library.read_library(settings)`. The usecase takes `use_library: bool = True`. The new app's route always passes the default. Only the Freeze-contingency wrapper passes `False`, which skips the read and gives every section `voice=None`. Every getter takes the session, and the identity map means the church row is loaded once. The session still closes before any AI call.
- Step 5 builds `ctx = build_context(..., rubric=service_rubric.merge_rubric(overrides), sermon_ref=…, sermon_text=…)` and, for each section, `voice = VoiceContext(profile=library.voice_profile, example=prayer_library.choose_example(library, section, choose=choose))`, where `choose_example` returns the chosen text, or `None` when no prayer has that type. Then `build_messages(section, prompts, ctx, voice=voice)`, which strips the profile, treats a whitespace-only one as empty and caps the profile at 2 000 and the example at 3 000 characters (backend §2 step 5). The usecase may also pre-cut (`strip()[:2000]`, and `choose_example` cutting to 3 000); the duplicate cuts are harmless.
- The rubric and the library are read fresh on every call, with no cache, like the prompts.
- **Logging** adds `rubric=default|custom`, `sermon=yes|no`, `voice=profile,example` (which were present) and `dropped=example,profile,sermon` (which the budget dropped). The checklist, sermon text, profile and example are prompt content, logged at DEBUG only (PR #7 §Privacy).

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
- **`repos/churches.get_church_prompts`** gains `session: Session | None = None` (F §2.2 rule 3). *Amendment 2026-09-26:* so does `get_church_rubric_overrides`, if slice 3 has not already added it.
- **`backend/prayer_library.py`** (new, pure; amendment 2026-09-26, PR #7): the reader, limits and example chooser listed under "Interfaces this slice provides". No FastAPI and no database imports.
- **`backend/service_rubric.py`** (PR #4): unchanged, reused (`merge_rubric`, `format_checklist`).
- **`api/ratelimit.py`:** `consume(bucket, *, user_id, church_id=None, cost=1)` charges both of the bucket's limits by `cost` and raises the existing 429. The `rate_limit(bucket)` dependency becomes `consume(cost=1)`. This is a backward-compatible addition if slice 2 lacks it.
- **`api/schemas.py`:** no change. `SectionKey`, `HymnRef` and `SlotHymns` are imported as slice 3 created them (shape frozen in F §1.3). `routes/liturgy.py` uses them in `GenerateLiturgyIn`, which puts them in the OpenAPI snapshot for the first time. *Amendment 2026-09-26:* one addition, `SermonText {ref, text}` (API §Schemas), shared with the reviewer add-on's routes (F §1.3).
- **`worship_service.py`:**
  - `_add_communion_liturgy(doc)` iterates `liturgy_config.COMMUNION_BLOCKS`. The docx output must be identical: characterize first (F §2.3 step 1).
  - `generate_liturgy` (worship_service.py:686-766) is **deleted** after its behavior is pinned in `test_liturgy_generation.py` against the new functions. Its only caller is app.py, which is frozen on its own branch (F D2). *Amendment 2026-09-26:* since PR #4 it lives at worship_service.py:762 and takes `rubric` and `sermon_text`. `_sermon_text_block` and `SERMON_TEXT_LIMIT` move to `liturgy_prompts` (backend §2) with their tests, and PR #4's `backend/tests/test_generate_liturgy.py` is retargeted like the other characterization tests (Testing).
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
- *Amendment 2026-09-26:* the same holds for the rubric and the prayer library. The only new client input is `sermon_text`, which goes into that user's own prompt, bounded by the model limits and by the 2 000-character cut, and is never logged above DEBUG (as slice 3 treats `nt_text`).
- This slice **writes nothing** to the database. Generation is stateless, and results live only in the browser draft until 5a's save.

---

## Data and migrations

- **No schema change and no Alembic revision.**
- `churches.settings.default_benediction` is a JSON key (F §3.5): read here, written in 6a. No row is back-filled. The "seed with the current value" (owner decision 9) is the read fallback, "Halverson".
- *Amendment 2026-09-26:* two more JSON keys are **read** here, with no DDL: `rubric` (PR #4's sparse overrides; written by `PATCH /rubric`, and by 6a's editor) and `prayer_library` (PR #7; written only by 6a, absent until then, so every church reads as an empty library and the messages equal the baseline). Frozen Streamlit reads `rubric` too (it runs PR #4's code) and ignores `prayer_library`.
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
| `request.ts` | `buildGenerateRequest(draft, section)`. Occasion trimmed and cut to 300. Scriptures trimmed, blanks dropped, first 20, each cut to 200 (the ServiceDraft limits). `hymns` = the three `HymnPick`s as `HymnRef`, each `title` cut to 300. `sections: [section]`. **No `overrides`.** *Amendment 2026-09-26:* `sermon_text` from the batch's resolved sermon text ("Sermon text" below), omitted when there is none. |
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

### Sermon text (amendment 2026-09-26, PR #4)

Streamlit sends the sermon (NT) passage with every liturgy request (inv E9). Here the client supplies it, so the server never fetches text on this route (API semantics 9):
- **Reference:** the effective NT reading from slice 2's `effectivePicks(draft).nt` (the explicit pick, else the classifier fallback; never a Psalm), trimmed and cut to 200 characters. No reference → no `sermon_text`.
- **Translation:** the draft's effective translation (`draft.readings.translation ?? church.effective_translation`), except that **ESV is replaced by WEB**, as in slice 3's `nt_text` rule (Crossway terms: ESV text is never sent to the AI).
- **Loading:** before a Generate or a "Generate empty sections" batch sends anything, `generation.tsx` calls `queryClient.fetchQuery` with slice 2's passage query options for `["passage", translation, ref]`. This reuses a passage step 1 already loaded, TanStack deduplicates concurrent calls, and the result is cached for 24 h. The wait is bounded at 10 s. On a timeout, an error or a null text, the batch goes ahead without `sermon_text`, with no toast. The sermon text only adds themes, and Streamlit also skips it when the fetch fails.
- **Request:** `sermon_text = {ref, text}`, with the text cut to 20 000 characters (the server keeps the first 2 000).
- Cancel also aborts this wait. The sermon text is never stored in the draft.

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
| BC-23 | The landmark row and outline heading for the first reading slot read **"First Reading"** (was "Old Testament Reading"). The second slot's heading is unchanged ("New Testament Reading"), and which reading fills each slot is unchanged. | Owner decision B |
| BC-24 | *(Amendment 2026-09-26.)* The rubric checklist and the sermon-text block are carried from PR #4 unchanged in wording and order. The sermon text now comes from the effective NT reading (never a Psalm) in the draft's translation, with **WEB instead of ESV**; before, it came from Streamlit's selected NT reference in the session translation, ESV included. A text that fails to load within 10 s is skipped, as before. If a long prompt must shrink, the sermon block is dropped rather than failing the section. | Crossway ESV terms (as slice 3); F §1.8 |
| BC-25 | *(Amendment 2026-09-26; PR #7, new app only.)* When the church has a prayer library (filled in 6a), AI sections get the pastor's voice profile and one same-type example. With no library, nothing changes. | Owner decision (prayer library) |

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
- `build_messages`: over 24 000 characters raises `PromptInvalid` with reason "It is too long once the readings, hymns and rubric checklist are added."

`test_usecase_liturgy.py` (SQLite `tmp_db`, `FakeAI`):
1. **No key (F acceptance 15).** `sections=[call_to_worship, benediction]` and `overrides={benediction: "  Go in peace.  "}` → benediction `override` with text `"  Go in peace.  "` (verbatim); call_to_worship `error/ai_not_configured`; `FakeAI.calls == 0`.
2. **AI configured.** Generated text is stripped. The church's stored `system` and section overrides reach FakeAI. They are read fresh: change the stored prompt between two calls and assert the second call sees it.
3. **Error mapping.** FakeAI raises `UpstreamTimeout("ai_timeout")`, `Busy("ai_busy")`, `UpstreamError("ai_upstream_error")` with secret text, `NotConfigured`, or `RuntimeError("secret")`; it returns `""`; or it returns 20 001 characters. Each maps to the table in API §semantics 7. The upstream text never appears in any outcome (assert "secret" is absent).
4. **Partial failure.** A church with a malformed stored `call_to_worship` template (`{"a": 1}`) → that section is `prompt_invalid` with exactly "The Call to Worship prompt in Settings has a problem: Placeholders must be a single word such as {occasion}. To print a { or } as text, write {{ or }}. An admin can fix it under Settings → Liturgy prompts."; `opening_prayer` is generated in the same call.
   - **Length cap:** a stored 20 000-character `system` prompt (possible only from unvalidated Streamlit writes), plus the default benediction template and 20 scriptures, pushes the prompt over 24 000 characters → the benediction result is exactly "The Benediction prompt in Settings has a problem: It is too long once the readings, hymns and rubric checklist are added. An admin can fix it under Settings → Liturgy prompts."
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

**Amendment 2026-09-26: rubric, sermon text and prayer library (backend).**
- **Characterization (PR #4).** PR #4's `backend/tests/test_generate_liturgy.py` is retargeted to `build_context`/`build_messages` and the usecase, like `test_liturgy_generation.py`, before `generate_liturgy` is deleted. Each case keeps its assertion: every section gets its default checklist; a church rubric replaces a checklist; a partial rubric falls back to the defaults; edited prompts still get the checklist; the sermon text is appended "for themes only"; it is cut to 2 000 characters; a missing or failed text (`"[Could not load text]"`) is skipped; typed sections are never sent. `sermon_text_block` keeps PR #4's exact wording.
- `test_liturgy_prompts.py` additions:
  - **Order:** rendered template, then "A good {Label}:" with its points, then the sermon block, then the voice example. The profile is only in the system message.
  - **Braces:** braces inside a checklist point, the sermon text, the profile and the example come through literally, and nothing raises (the blocks are appended after `render()`).
  - **Byte-identical baseline:** `build_messages(..., voice=None)`, `voice=VoiceContext("", None)` and `voice=VoiceContext("   ", None)` give equal lists.
  - **Budget:** with a system prompt and template near the limit, the example is dropped first, then the profile, then the sermon block. A voice or sermon block never raises `PromptInvalid`. A checklist that pushes the church's own text over the limit does raise the pinned "It is too long once the readings, hymns and rubric checklist are added." reason: an 8 000-character system prompt, an 8 000-character template that uses `{occasion}`, `{scriptures}` and `{hymns}`, a 300-character occasion, 20 scriptures of 200 characters, three hymns with 300-character titles and a maximum-size checklist (12 points of 300 characters) → `PromptInvalid` with that reason (about 21 260 characters before the checklist, about 24 930 with it). The same church with its default checklist is not over the cap (about 21 700 characters with the largest default, the Prayer of Confession's), and a sermon block of 2 000 characters on top of it is kept (under 23 950 characters). With a six-point checklist of 300-character points instead (about 23 100 characters), the church's own text still fits, and the same sermon block would take the total over 24 000, so it is dropped, not raised.
  - **Truncation:** called directly, `build_messages` sends a 2 500-character profile as 2 000 characters and a 4 000-character example as 3 000, and a profile with surrounding whitespace is sent stripped.
  - **Defaults:** the `prayer_for_illumination` default contains "no more than 3 sentences", `offertory_prayer` contains "No more than three sentences", and both pass `check_template`.
- `test_prayer_library.py` (pure): a missing key and junk values (`[]`, `{"prayers": "x"}`, `{"prayers": [{"type": 5}]}`) read as empty and never raise; `choose_example` with a pinned chooser returns the expected prayer, returns `None` when no prayer has that type, and never returns an `"other"` prayer.
- `test_usecase_liturgy.py` additions:
  1. **Rubric read fresh:** change the stored rubric between two calls; the second call's FakeAI messages show the new checklist. Church B's rubric never appears in church A's messages. An invalid stored rubric gives the default checklist.
  2. **Library read fresh:** add a prayer between two calls; the second call's messages carry the example. An empty library gives messages equal to the no-library baseline.
  3. **One session:** a patched `session_scope` counter shows prompts, rubric and library read in one session, and 0 open sessions during `complete()`.
  4. **Sermon:** `sermon=("Mark 4:35-41", text)` puts the block in every AI section's user message and in no override.
  5. **Worst case (PR #7 §Privacy; index open item 18):** Prayers of the People with a 2 000-character profile, a 3 000-character example, a maximum-size checklist and a 2 000-character sermon text stays within `MAX_PROMPT_CHARS` after the drop rules, and FakeAI receives `max_completion_tokens=4000`.
- `test_api_liturgy.py` additions: `sermon_text` with a 201-character `ref`, a 20 001-character `text`, or an extra field → 422 `invalid_request` with `fields`. A request without `sermon_text` is still accepted (additive).

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
- `request.test.ts`: one section, no `overrides`, trimmed and limited scriptures, slot-keyed `HymnRef`s including `hymn_id: null`, a 301-character hymn title cut to 300. *Amendment 2026-09-26:* `sermon_text` is `{ref, text}` for the effective NT reading, is omitted with no reference or no text, and is never built from an ESV passage (for an ESV church the WEB key is read). This is the port-ledger target for `streamlit_tests/test_app_helpers.py::test_sermon_text_*` (Streamlit's `sermon_text_for`).
- `generation.test.tsx` (amendment 2026-09-26): a "Generate empty sections" batch of 4 makes **one** passage fetch, then sends 4 requests carrying the same `sermon_text`. A passage fetch that fails or passes 10 s still sends the batch, without `sermon_text` and with no toast. Cancel during the wait sends nothing.
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
19. *(Amendment 2026-09-26, PR #4.)* Every AI section's user message is the rendered template, then that section's checklist from the church's rubric (read fresh on each request, defaults when unset or invalid), then the sermon-text block when `sermon_text` is sent, with PR #4's wording, order and 2 000-character cut. Typed sections are never sent. The Illumination and Offertory defaults say "no more than 3 sentences". Every assertion of PR #4's `test_generate_liturgy.py` has an equivalent against the new code before `generate_liturgy` is deleted. *(test)*
20. *(Amendment 2026-09-26.)* The client sends the effective NT reading's passage as `sermon_text`, never ESV text, with one passage fetch per batch, and a failed fetch never blocks generation. The server never fetches passage text on `/liturgy/generate`. *(test)*
21. *(Amendment 2026-09-26, PR #7.)* `build_messages(section, prompts, ctx, *, voice=None)` appends the voice profile (capped at 2 000) to the system message and one random same-type example (capped at 3 000) to the user message, both after `render()`. Over `MAX_PROMPT_CHARS`, the example is dropped first, then the profile, then the sermon block. The library never causes `prompt_invalid`. With an empty or missing library the messages are byte-identical to the baseline. *(Amended 2026-09-26.)* `build_messages` itself strips the profile, treats a whitespace-only profile as empty and applies both caps, whatever the caller passes. `usecases/liturgy` reads `churches.settings["prayer_library"]` in the same `session_scope` as `get_church_prompts`, fresh on every call. *(test)*

---

## Risks and open questions

1. **Prayers of the People vs the 30 s OpenAI timeout (open).**
   - The problem: the prayer is 10-15 paragraphs, and `OPENAI_TIMEOUT_SECONDS=30` per attempt (F §2.8) may be too short on the model slice 3 picks.
   - Measure during 4a with that model.
   - If it times out, add an optional, additive `timeout_seconds` keyword to `openai_client.complete()` and give this section 60 s with no retry. That keeps the worst case (60 + 15 s wait) inside the 90 s client timeout.
2. **Token budgets on a reasoning model (open).** If `OPENAI_MODEL` is a reasoning model, reasoning tokens count toward `max_completion_tokens`, so 1500 or 4000 could produce empty or cut-off text. Empty text is reported as an error, not stored. Verify the budgets with the configured model in 4a and adjust `SectionSpec.max_completion_tokens` (a code constant, no API change). *Amendment 2026-09-26:* the prompt is now longer, with the rubric checklist and the sermon text (PR #4) and, once 6a ships, the voice profile and example (PR #7). Measure the worst case (Prayers of the People with a 2 000-character profile, a 3 000-character example and a full sermon text) against both the budget and the 30 s timeout in item 1.
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

---

## Amendment 2026-09-26: service reviewer (add-on after 4b; PR #8)

**Source:** `docs/superpowers/specs/2026-09-26-service-reviewer-design.md`. That spec is authoritative, and this section does not repeat its checks, prompts or copy. It is **new-app only** (nothing goes into Streamlit). It ships as a small add-on right after 4b, before 5a, and needs this slice's cards, origins, stale-results rule, `usecases/liturgy.py`, `liturgy_prompts` and the OpenAI client. It uses the service rubric (PR #4) and, when a profile exists, the prayer library (PR #7).

**UI hooks on this step:**
- The liturgy step header gets a **"Review service"** button. It is enabled when at least one switched-on card has text, and it sends every such card. While it runs: a spinner, "Still working" after 8 s, and Cancel (F §1.8).
- Each card shows **at most 3 notes** under its text (tag chip, one sentence, dismiss ×), or "Looks good." when it was reviewed with no notes. Notes about several prayers go in an **"Across the service"** box at the top of the step, also at most 3.
- **What clears a card's notes:** typing in the card, Regenerate, Revise, Clear text and "Use church default". A review result is dropped for any card whose text or origin changed while the review ran. This is this slice's stale-results rule (UX "Generate and Regenerate" step 6: compare the text and origin captured at request start).
- **"Revise with these notes"** appears only on cards with origin `ai` that still have at least one undismissed note. The revised text replaces the card, and the origin stays `ai`. Like Regenerate, it keeps the previous `{text, origin}` in memory for **Undo**. Cards with origin `typed`, `archive` or `default` get notes but never a Revise button, so typed text is never changed by the AI (owner decision 2).
- Notes live in client memory only (for example in `LiturgyGenerationProvider` or a sibling provider). They are never written to the draft, the archive or `localStorage`, so `DraftV1` is unchanged, with no version bump.
- When the AI part is missing (`ai_status` other than `ok`), the code-check notes still show, with the reviewer spec's quiet "Only quick checks ran…" line.

**Routes** (in `backend/api/routes/liturgy_review.py`; request models at the top of that module with `extra="forbid"`, plus the shared `SermonText` from `api/schemas.py`, the same `{ref, text}` shape as `GenerateLiturgyIn.sermon_text`):

| Route | Guard and rate limit | Errors |
|---|---|---|
| `POST /liturgy/review` | `require_church`. The `ai` bucket is charged **cost 1, and only when the AI call is made**, through a `charge` callback like `/liturgy/generate`'s (semantics 8). When the bucket is empty, the usecase skips the AI call instead of raising. | Always **200** once the request is valid: code notes plus `ai_status: "ok" \| "not_configured" \| "busy" \| "timeout" \| "rate_limited" \| "error"`. Request-level problems stay HTTP errors (401, 403, 422 `invalid_request`, 500). |
| `POST /liturgy/revise` | `require_church` plus `rate_limit("ai")` (cost 1), as on `/hymns/suggestions` | AI failures as HTTP statuses: 503 `ai_not_configured` / `ai_busy`, 504 `ai_timeout`, 502 `ai_upstream_error`; 429 `rate_limited` with `Retry-After`; 422 `invalid_request`; 422 `prompt_invalid` "This prayer is too long to revise." (budget below). |

- **Consistency with F.** `ai_status` is a response field, not an error code, so nothing is added to F §1.5's `ERROR_CODES` or the frontend `ApiErrorCode` union. Like this slice's per-section results, review's "AI failure inside a 200" and its "empty bucket → `ai_status: rate_limited` instead of 429" are declared deviations from F §1.5 and §1.8, recorded in F's "Amendments from slice specs". Revise follows F exactly; its F §2.8 prompt-size 422 carries its own message, "This prayer is too long to revise."
- **Revise input budget** (reviewer spec §Revise, added 2026-09-26). The revise prompt must stay within `MAX_PROMPT_CHARS` (24 000). If it would exceed it, the usecase drops the voice profile first, then the sermon text, then the rubric checklist. If the draft plus the fixed instructions (the church's system prompt, the section label, the occasion and readings, the notes and the revise instruction) still exceed the cap, it returns 422 `prompt_invalid` "This prayer is too long to revise." before any AI call. The `rate_limit("ai")` dependency has already charged the token, as for any Revise request.
- **Sermon text** (added 2026-09-26). Review and revise requests send the same resolved `sermon_text` as generation (Frontend changes, "Sermon text"): the effective NT reading, in the draft's translation with **WEB instead of ESV** under the Crossway rule, from one bounded 10 s passage fetch through the same `fetchQuery` (a passage already cached is reused), and omitted when the fetch fails, times out or returns no text. The server never fetches passage text on these routes.
- **Timeouts** (F §1.8): review has a 75 s server deadline passed to `complete(deadline=…)` and a 90 000 ms client timeout. Revise uses the section's slice 4 token budget (1 500, or 4 000 for Prayers of the People) and the 90 000 ms client timeout.
- **Tenancy.** The rubric, the merged system prompt and the voice profile are read on the server in one `session_scope`, closed before the AI call (F §1.8), and never taken from the client. Both routes get `assert_church_isolated` tests.
- Neither route is user-scoped, so the `test_route_guards.py` allowlists don't change. The OpenAPI snapshot is regenerated.

**New modules:** `backend/review_checks.py` (pure code checks: stock seasonal phrases, naming Ordinary Time, scripture references, repeated openings) and `backend/usecases/liturgy_review.py` (review with its tolerant parsing, merge and budget, and `revise`). *Consistency (resolved 2026-09-26, PR #9):* `review_checks.py` uses the one book table, slice 3's `scripture_refs.BOOKS` (which absorbs `worship_service._BOOK_ABBREVS`): its prose pattern is built from the `BOOKS` aliases (longest first, whole words, followed by a chapter number) and each candidate is confirmed with `scripture_refs.parse_refs`; only a match that parses into a span becomes a note. There is no second book list.

**Baseline change to this slice: the season guidance.** The add-on replaces the "do not name the season…" sentences in `liturgy_prompts.DEFAULT_SYSTEM_PROMPT` with the new season guidance. The exact old and new text is in the reviewer spec, §"Writer: new season guidance".
- It lands **with the add-on, after the Streamlit freeze**, so `streamlit-frozen` keeps the old wording. A church whose admin saved its own system prompt keeps it, because overrides are stored whole. 6a's prompts page shows whichever default is in code.
- **Freeze contingency** (added 2026-09-26). If F §6.1 item 6 is in force, Streamlit keeps running from `main` through the `generate_liturgy` wrapper (Backend §6, `worship_service.py`), so editing `DEFAULT_SYSTEM_PROMPT` would reach it. The owner decided Streamlit gets no new features (reviewer decision 7; owner decision 7), so the add-on keeps a frozen copy of the old constant, `liturgy_prompts.LEGACY_SYSTEM_PROMPT`, with the old season sentences. The wrapper passes it as the `system` default: a church with no saved system prompt gets `LEGACY_SYSTEM_PROMPT` in Streamlit and the new `DEFAULT_SYSTEM_PROMPT` in the new app, and a saved system prompt is used as is in both. Streamlit's Settings page also runs from `main` and reads `liturgy_prompts.default_prompts()` (streamlit_views/settings.py:145 in `submit_prompts`, :227 in the prompts tab), so it would show the new text as the "Overall voice" default, compare saves with it and store it as an override when an admin edits the system prompt. The add-on therefore adds `liturgy_prompts.legacy_default_prompts()` (`default_prompts()` with `"system"` set to `LEGACY_SYSTEM_PROMPT`) and switches those two calls to it, so Streamlit shows, compares with and saves against the old wording. The new season guidance applies only to the new app. The wrapper's smoke test asserts that the old season sentences reach the fake model, and a `streamlit_tests` case asserts that saving the prompts tab with its system default unchanged stores no `system` override. `LEGACY_SYSTEM_PROMPT` and `legacy_default_prompts()` are deleted with the wrapper. For the same reason, the wrapper calls the usecase with the prayer library switched off (`use_library=False`: no `VoiceContext`, so `build_messages` gets `voice=None`). A voice profile saved in the new app never reaches Streamlit, and the smoke test asserts that no voice or example block reaches the fake model even when the church has a library. The rubric checklist and sermon text stay, because Streamlit already had them before the freeze (PR #4).
- **Tests before and after.** This slice's tests must not pin the old season sentences as a literal. They compare with `liturgy_prompts.default_prompts()["system"]` or `DEFAULT_SYSTEM_PROMPT` (for example "the system message equals the merged system prompt"), so they pass unchanged before the add-on lands and after it. Any slice 4 test that does quote the default system text is updated to the new text **in the add-on's PR**, never earlier. The add-on adds the test that the constant contains the new season sentences and none of the old ones.
- Writer behavior otherwise stays as specified here. The reviewer never rewrites a card on its own.

**Testing and acceptance** for the add-on are the reviewer spec's §Testing (backend `FakeAI` and route tests, frontend DOM tests, a 375 px manual check). These cases are this slice's contract and are added to its test files when the add-on lands:
- `generation`/card tests: typing, Regenerate, Revise, Clear text and "Use church default" each clear that card's notes. A review result for a card edited mid-review is dropped.
- `cards.test.ts`: Revise is offered only for origin `ai`, and its Undo restores the previous text and origin, like Regenerate.
- *(Added 2026-09-26.)* Request builders for review and revise: `sermon_text` is the same resolved `{ref, text}` that `buildGenerateRequest` sends, it is omitted when the passage fetch fails or times out, and for an ESV church no ESV text is sent (the WEB passage is read).
- *(Added 2026-09-26.)* Revise budget, with `FakeAI`: while the prompt is over the cap, the voice profile is dropped first, then the sermon text, then the checklist, and each only when still needed; a draft that is still over `MAX_PROMPT_CHARS` with only the fixed instructions (for example an 8 000-character system prompt and a 20 000-character draft) returns 422 `prompt_invalid` "This prayer is too long to revise." and `FakeAI.calls == 0`.
