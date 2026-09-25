# Slice 3: Hymns step — Design

**Status:** Draft  **Depends on:** ops, 1, 2 (interfaces listed in "Interfaces with other slices")  **Size:** L, shipped as two PRs: **3a** backend (additive API, no UI change) and then **3b** frontend.

**Inputs:**
- Migration inventory `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md`, cited as "inv". The sections used here are §1 D1–D9, §2.2, §3 and §5 row 3.
- Foundations `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, cited as "F". This spec follows F. It declares the refinements below. They are not left to be folded back at merge time: F's **"Amendments from slice specs"** section records them now, before implementation, each citing slice 3, so merge order cannot make F and this spec drift. Where F's body text and that section disagree, the amendment wins.
  - **F §1.2 rules 2 and 5:** `current_picks` ids in `POST /hymns/suggestions` are exclusion hints. They are never resolved or echoed, so an id from another church is ignored rather than returned as 404 (§API notes).
  - **F §2.5:** `GZipMiddleware` joins the middleware stack as the innermost layer (§Backend 1).
  - **F §2.8:** the OpenAI client does its own capped retry, accepts an optional `deadline`, and maps `insufficient_quota` separately (§Backend 3.7).
  - **F §4.4:** hymn and hymnal mutations (6a) also invalidate `["church", id, "profile"]`, because they can change `effective_hymnal` (row 6a in "Interfaces with other slices").
- The shared `HymnRef`, `SlotHymns` and `SectionKey` shapes are **frozen in F §1.3**. This slice lands first and creates them with exactly that shape (§API Models).
- Owner decisions 3 and 9.

---

## Goal

Replace the Streamlit hymn section (app.py:634-851) with step 2 of the React builder, `/builder/hymns`. The step lets a member:
- fill the Opening, Response and Closing slots from the church's own hymnal, searching by number or title;
- hide hymns used within 12 weeks of this service without losing a pick;
- see hymns that match the day's readings, with a scripture matcher tightened so it stops over-matching;
- ask AI for suggestions. AI fills each empty slot with its top pick and shows 2–4 one-tap alternatives per slot. Filling only *empty* slots is this spec's reading of decision 3. It is put to the owner before 3b starts, and the answer is recorded in F's decisions table (Open question 2).

The step writes only to the per-church draft (F §4.6). It also turns the Hymns step on in slice 2's builder shell: `"hymns"` joins `SHIPPED_STEPS`, so `StepProgress` shows the hymns status instead of "Soon", and `SummaryPanel`'s Hymns block shows the three slots instead of "Available soon" (§Frontend "Builder shell"). Behind it, the backend gains four church-scoped read or action endpoints and the shared OpenAI client (F §2.8). The dead Notion and audio code goes away.

---

## Scope / Out of scope

### In scope

Each current behavior is carried over, changed (listed again under "Behavior changes") or moved.

| Inventory item | Disposition in slice 3 |
|---|---|
| D1 hymnal load, cache, refresh, empty warning | `GET /hymns` + TanStack Query. The empty-hymnal message is kept. The Refresh button is removed; the list refetches and is invalidated instead. A load error is never cached as an empty list. |
| D2 hymnal switcher | `GET /hymnals` + a draft-held `hymns.hymnal`. The default comes from the church's `default_hymnal` setting (read only here). Picks keep their own hymnal. |
| D3 "Find hymns matching any of the scriptures" | `POST /hymns/scripture-matches`. It runs automatically from the draft's readings, accepts an extra reference, and results can be added to a slot. |
| D4 scripture-matching engine | Rewritten as a parsed book/chapter/verse matcher (owner decision 9). |
| D5 exclude recently used | Window around the service date, excluding that date. Default on. Never clears a pick. Applied to AI candidates. Match results are marked or hidden. |
| D6 three slot pickers | Slot-keyed pickers that hold hymn ids. A searchable Combobox shows numbers. Duplicate titles can be told apart. |
| D7 AI suggestions | `POST /hymns/suggestions`. Top pick plus 2–4 alternatives per slot (owner decision 3). The server guarantees the minimum by topping up from the slot's candidate list (§3.6 step 9). Typed errors, timeouts, and resolution by candidate id. |
| D8 hymn display, links, dead audio | One backend read model (`HymnOut`). Links are rendered only through `safeHttpsUrl`. The audio resolver and its cache are deleted. |
| D9 free-text hymns | Stay removed (owner decision 9). A slot always references a hymnal hymn. |

Foundation pieces this slice builds (F §7.2 row 3):
- `backend/integrations/openai_client.py` (F §2.8) and `OPENAI_MODEL` on Railway;
- the `ai` rate-limit bucket;
- `SearchCombobox`, the generic long-list component for the hymn picker (F §4.9.5). The Combobox pattern itself first appears in slice 1's `TimezoneCombobox` (F §7.2), which 6a reuses for the timezone picker. If slice 1 built `TimezoneCombobox` on a generic `SearchCombobox`, this slice reuses that component instead of creating one;
- `GET /church` gains `default_hymnal` and `effective_hymnal` (read only);
- the shared `HymnRef`, `SlotHymns`, `SectionKey` and `Page[T]` models in `backend/api/schemas.py`, with the shapes frozen in F §1.3 and F §1.4. No slice-3 route uses the first three; they are created here because this slice lands first and slices 4 and 5a import them unchanged (§API Models);
- in the builder shell: `"hymns"` in `SHIPPED_STEPS` and the Hymns block of `SummaryPanel` (F §4.7).

### Out of scope (moved to named slices)

| Item | Slice | Interface this slice leaves for it |
|---|---|---|
| Hymn usage recording ("replace that date's usage on Save") | 5a | The exclusion reads `hymn_usage` with the `(number, normalized title)` key in §Backend 3.4, and 5a writes rows with the same key. |
| `services.hymns` slot storage, the `services.hymnal` column, the docx "First/Second/Third Hymn" labels, `#None` | 5a | `draft.hymns.slots` and `draft.hymns.hymnal` (F §4.6). The payload hymnal rule is in "Interfaces with other slices", row 5a. |
| Mapping legacy archived picks to hymn ids (`serviceToDraft`) | 5a | `GET /hymns?hymnal=…&limit=2000` supplies `(hymnal, number, title)` for resolution. This step shows "Not in your hymnal" for any `hymn_id: null` pick. |
| `{opening_hymn}` / `{hymns}` in liturgy prompts | 4 | The opening slot is the opening hymn. There is no positional compaction. |
| Hymn create, edit and delete; the hymn library list; "Add hymn" asks which hymnal | 6a | `HymnOut` and `GET /hymns` `q`/`limit`/`offset` are defined here for 6a to reuse. |
| Hymnal import (bundled PH1990) and writing `default_hymnal` | 6a | See "Interfaces with other slices". |
| Theme data cleanup (`{A,"B"}` literals) | 7 | This slice only normalizes themes for display and matching. |

### Interfaces with other slices

For everything this slice **provides**, this table and §API are the source of truth, except where F freezes a shape (F §1.3) or another slice owns the rule (row 5a's archived hymnal). Where another slice's spec describes these interfaces differently, this table wins and that slice's plan adapts. The points settled across slices are:
- **`HymnRef`, `SlotHymns`, `SectionKey`:** one definition, frozen in F §1.3 and created here with exactly that shape (§API Models). `HymnRef.hymnal` is a plain string of at most 20 characters with **no pattern**, and `title` allows 300 characters. Slices 4 and 5a import the three models and neither redefine nor tighten them.
- **Archived hymnal (5a):** 5a's server-side rule applies (row 5a). The payload sends `draft.hymns.hymnal` as is, and 5a's `create_service`/`replace_service` store `effective_hymnal` when it is null.
- **Slice 6a**, if any of its text still describes `GET /hymnals` as `{items: [{code, count}], default}`, uses the shape in §API Models: `{items: [{code, hymn_count, scripture_ref_count}], default_hymnal, effective_hymnal}`. 6a's interface row already assumes this shape. 6a's hymn mutations also invalidate `profile` (row 6a). 6a's hymn library uses this slice's `GET /hymns` ordering and `q` rule (§API notes).

| Slice | Direction | Exact interface assumed or provided |
|---|---|---|
| ops | assumed | Middleware order (F §2.5), `redirect_slashes=False`. This slice adds `GZipMiddleware` innermost and updates the ops middleware-order test (§Backend 1). |
| 1 | assumed | `domain_errors.py` (`InvalidInput`, `NotConfigured`, `Busy`, `UpstreamError`, `UpstreamTimeout`); the `usecases/` package; `test_route_guards.py`; `assert_church_isolated`; `test_openapi_contract.py` + `gen:api`; TanStack client and `useApi().church`; UI kit (`EmptyState`, `ErrorState`, `PendingButton`); `renderWithProviders` / `installFakeApi`; migration `0002_reconcile` creating `ix_hymns_church_hymnal` in production. |
| 2 | assumed | **Draft:** `useDraft(): { draft: DraftV1; update(recipe: (d: DraftV1) => DraftV1): void }` from the builder's `DraftProvider` (adapt to slice 2's actual names). The fresh draft has `hymns = {hymnal: null, exclude_recent: true, slots: all null, alternatives: null}`. **Shell:** the `/builder/hymns` route with slice 2's `StepPlaceholder` card; `lib/draft/steps.ts` `SHIPPED_STEPS = new Set(["readings"])`; `lib/draft/status.ts` `stepStatus` (hymns complete when all three slots are filled, F §4.7) and `stillNeeded(draft, SHIPPED_STEPS)`; `SummaryPanel`, whose Hymns and Liturgy blocks read "Available soon". Slice 3 adds `"hymns"` to `SHIPPED_STEPS` and replaces the Hymns block (§Frontend "Builder shell"); slice 2's hand-off table lists this row. **Dates:** `lib/dates.ts` `formatServiceDate` and `parseIsoDate`. **Backend:** `api.ratelimit.rate_limit(bucket)` in `backend/api/ratelimit.py`; `integrations/http.py`; `cache.TTLCache`; `scripture_refs.py` with `BOOKS` (66 books plus the deuterocanon, each `Book(name, testament, aliases)`), `split_book(ref)`, `classify(ref) -> "ot" \| "psalm" \| "nt" \| "unknown"` (slice 3 tests `== "nt"`), `split_alternatives(ref) -> list[str]` and `default_nt_ref(scriptures) -> str \| None` ("NT fallback = second reading or gospel from the classifier", F §7.4); `usecases.passages.get_passage_text(ref: str, translation: str) -> str \| None`, which never raises for upstream failures, caches public-domain text for 7 days, takes no deadline and can take up to 20 s (F §1.8), so slice 3 bounds it itself (§3.6 step 5); `GET /church` served by `ChurchProfileOut` in `api/schemas.py`. **Frontend:** the passage query key `["passage", translation, ref]`, whose cached data is `PassageOut`, read through `passageText(p: PassageOut) -> string \| null` from `lib/queries/passages.ts`. If slice 2 does not ship `default_nt_ref` or `split_alternatives`, slice 3 adds them to `scripture_refs.py` with exactly those signatures. |
| 4 | provided | `integrations/openai_client` (`ai_available()`, `complete(messages, *, max_completion_tokens, json_mode=False, deadline=None) -> str`, `FakeAI`, `set_ai_for_tests()`; `deadline` is optional, so 4's calls without it keep the F §2.8 behavior), the `ai` bucket, the `repos.hymns.HymnRecord` type, **`HymnRef`, `SlotHymns` and `SectionKey` in `api/schemas.py`** (shape frozen in F §1.3; created here, §API Models; 4 imports them unchanged and keeps its own schema tests), and the rule that slots are never compacted. **Shell hand-off:** `SummaryPanel`'s Liturgy block still reads "Available soon" and `StepProgress` still shows "Soon" for Liturgy after this slice; slice 4 adds `"liturgy"` to `SHIPPED_STEPS` and the liturgy block per F §4.7. |
| 5a | provided / assumed | **Provided:** `Page[T]`, `HymnRef`, `SlotHymns` and `SectionKey` in `api/schemas.py` (shapes frozen in F §1.3; 5a reuses them and does not define its own copy); the usage key in §3.4; `GET /hymns?hymnal=&limit=2000`; `usecases.hymns.resolve_default_hymnal`. **Assumed — archived hymnal, 5a's server-side rule:** the payload sends `draft.hymns.hymnal` as is (null passes through), so church data stays out of the payload and its fingerprint. 5a's `create_service`/`replace_service` store `resolve_default_hymnal(...).effective_hymnal` when it is null, which is the hymnal this step showed as selected (`selectHymnal` also falls back to `effective_hymnal`). There is no client-side fallback and no first-pick fallback here; if a first-pick fallback is wanted for a church with no hymnals, 5a adds it to `create_service`/`replace_service` with a test. A draft code that has since vanished is sent and archived as stored (the step never rewrites it, §User experience "Toolbar"). **Shell hand-off:** 5a adds `"review"` to `SHIPPED_STEPS` (Saved / Unsaved via `isDirty` and `editing`), wires the `SummaryPanel` status line and deletes `StepPlaceholder`. |
| 6a | provided / handed off | 6a writes `churches.settings.default_hymnal` through `PATCH /church` and must validate it against `GET /hymnals` codes. The `GET /hymnals` shape in §API Models is authoritative. **Hymn create, edit and delete invalidate `["church", id, "hymns"]`, `["church", id, "hymnals"]` and `["church", id, "profile"]`**: a hymn change can alter `hymn_count` and `scripture_ref_count`, add or remove a hymnal code, and change `effective_hymnal` (for example the first hymn in an alphabetically earlier code). F's "Amendments from slice specs" adds `profile` to the §4.4 map, and 6a's hymn-mutation row carries it. 6a's hymn library reuses `GET /hymns` with the ordering and `q` rule in §API notes (hymnal, then number with nulls last, then title, then id; `q` of 1–6 digits also matches `number`). The `hymns` prefix also covers the scripture-match queries (key nested under it, §Frontend). Hymnal import and removal invalidate the same three keys. 6a may add an optional `label` to `GET /hymnals` items, which is additive. When 6a ships, it sets `SETTINGS_HYMNS_READY = true` so the empty-hymnal state links to `/settings/hymns`. |

---

## User experience

Mobile first (375 px). The step renders inside slice 2's `BuilderShell`: progress "Step 2 of 4 · Hymns", a sticky Back/Next footer, and the summary panel (right column at `lg`, bottom sheet below `lg`). Everything is a single column at every width. The three slot cards stack, because the main column at `lg` is too narrow for three side-by-side cards with chips.

### Layout (375 px)

```
Step 2 of 4 · Hymns  ▮▮▯▯                        [Summary]
Hymns
Choose an opening, response and closing hymn.

Hymnal  [ GG2013 · 853 hymns            ▾ ]    ← only with 2+ hymnals
[■] Exclude hymns used within 12 weeks
    Hides hymns sung in the 12 weeks before this service or planned
    in the 12 weeks after it.  4 hymns are hidden.
[ ✦ Suggest hymns                               ]   (touch size, full width)
    Fills empty slots and shows other ideas under each hymn.

┌ Opening hymn ─────────────────────────────────┐
│ Gathering / call to worship                   │
│ #403  Come, Thou Almighty King   GG2013  ▶ ✕ │
│ [Change]                                      │
│ Other ideas                                   │
│ [#1 Holy, Holy, Holy…] [#35 Praise, My Soul…] │
└───────────────────────────────────────────────┘
┌ Response hymn ────────────────────────────────┐
│ After the sermon — responds to the scripture  │
│ [ Search by title or number              ▾ ]  │  ← empty slot shows the picker
└───────────────────────────────────────────────┘
┌ Closing hymn … ┐
▸ Hymns for the readings (7)                          ← collapsible; open at md+
Hymn information and links courtesy of Hymnary.org. Individual hymns may
carry their own copyright — see each hymn's page.
[‹ Back]                                   [Next ›]
```

### Slot cards

- **Titles and captions:**

  | Slot | Title | Caption |
  |---|---|---|
  | Opening | Opening hymn | Gathering / call to worship |
  | Response | Response hymn | After the sermon — responds to the scripture (NT reading) |
  | Closing | Closing hymn | Joyful / sending |

- **Filled slot.** The card shows `HymnLabel`, which renders:
  - "#{number} {title}" ("{title}" alone when the number is null);
  - a hymnal badge when the church has 2+ hymnals;
  - a **▶ Listen** icon link to the Hymnary page (`safeHttpsUrl`; `target="_blank" rel="noopener noreferrer"`; aria-label "Listen to {title} on Hymnary.org"), with no link if the URL is not https;
  - an **✕** button (aria-label "Remove {title}").

  **Change** replaces the row with the focused picker. Escape or blur restores the row.
- **Empty slot.** The card shows the picker.
- **Live data.** When the pick's id is found in its hymnal's loaded list, the card shows the live title, number and link. The draft snapshot is **not** rewritten, so renaming a hymn in Settings does not mark the draft dirty. Until the list loads, the card shows the snapshot.
- **Remove.** ✕ sets the slot to `null` and shows the toast "Removed {title}." with an **Undo** action (sonner). The previous pick is held in component state for Undo.
- **Undo toasts never outlive the step.** Sonner toasts stay mounted outside the `(church)` layout, so a closure over `update` could write church A's pick into church B's draft after a switch. Two guards:
  - the step keeps the ids of the Undo toasts it shows (✕ here, "Add" in the matches) and calls `toast.dismiss(id)` for each in an effect cleanup on unmount;
  - each Undo handler captures the church id when the toast is shown and does nothing if the current church id differs.
- **Notices** appear under the pick in muted text with an icon. None of them changes the pick:
  - recently used (only when the service date is valid):
    - past date: "Used on {September 7, 2026} — within 12 weeks of this service."
    - future date: "Also planned for {October 18, 2026} — within 12 weeks of this service."
  - not in the hymnal (`hymn_id` null, or the id is not in its hymnal's list once loaded): "Not in your hymnal. Choose a replacement."
  - duplicate: "Also chosen as the {Opening|Response|Closing} hymn."
- **Other ideas (AI chips).** Shown only when `draft.hymns.alternatives?.for_date_iso === draft.readings.date_iso`.
  - 2–4 chips (`Button variant="secondary" size="touch"`, title truncated with an ellipsis), labelled "#{n} {title}", with a "Used Sep 7" / "Planned Oct 18" suffix badge when recently used. The server returns enough hymns for at least 2 chips whenever the slot's candidate list has them (§3.6 step 9). Fewer appear only in a hymnal with very few eligible hymns, or when chips are hidden by the rule below.
  - Tapping a chip swaps it into the slot. The previous pick takes the chip's place, so tapping again swaps back.
  - A chip whose hymn is missing from its loaded hymnal list is hidden.
  - Group aria-label: "Other ideas for the {slot} hymn". Chip aria-label: "Use {title} as the {slot} hymn".

### Picker (`HymnPicker` over `SearchCombobox`)

- Label: the slot title. Placeholder: "Search by title or number". Input `text-base md:text-sm` so iOS doesn't zoom.
- Items come from the selected hymnal's list. Hymns with a blank title are never listed.
- **Ranking** (pure `filterHymns`, §Frontend):
  - all digits: exact number first, then numbers that start with the digits, then titles containing the digits;
  - otherwise: accent- and case-insensitive title match, ranked starts-with, then word-start, then contains.
  - Within each group, hymnal order applies.
  - At most 50 rows are rendered.
- **Hints in the list footer:**
  - empty query: "Type to search {n} hymns.";
  - more than 50 matches: "Showing 50 of {n} — keep typing to narrow.";
  - no matches: "No hymns match “{q}”.";
  - when exclusion hides matches: "{k} more used within 12 weeks are hidden."
- Rows show "#{n} {title}" plus a "Used Sep 7" / "Planned Oct 18" badge when the hymn is recently used and exclusion is off.
- Selecting sets the slot to `{hymn_id, title, number, hymnal}` from the row.
- While the list loads, the input is disabled with placeholder "Loading hymnal…".

### Toolbar

- **Hymnal** (Base UI `Select` with an `items` map, F §4.9.3). Shown only when `GET /hymnals` returns 2+ items.
  - Item label: "{code} · {hymn_count} hymns". Helper text: "Which hymnal to choose hymns from for this service."
  - The **selected hymnal** is `selectHymnal(draft.hymns.hymnal, hymnals)` (pure, `src/lib/hymns/hymnal.ts`). It is resolved only after `GET /hymnals` has succeeded; while it loads the toolbar shows skeletons, and on error the `ErrorState` below applies, so nothing is resolved from missing data.
    - Stored code present in the list → that code.
    - Stored code `null` → `effective_hymnal`.
    - Stored code absent from a successfully loaded list → `effective_hymnal`, with `stale: true`. The note "{code} is no longer in your church's hymnals. Showing {effective} instead." appears in the toolbar, even when the Select itself is hidden (one hymnal).
  - The selected hymnal drives the Select value, the list, the matches and the suggestion request.
  - Changing the Select writes `draft.hymns.hymnal = code`. Picks are not touched. **The step never writes the hymnal on its own**, so a vanished code never marks a loaded service dirty or changes its archived hymnal without a user action.
  - When the selected hymnal has `scripture_ref_count == 0`, a note appears under the select: "{code} has no scripture references, so scripture matches and AI response picks will be weaker."
- **Exclude switch** (`Switch`). Label: "Exclude hymns used within 12 weeks". Helper: "Hides hymns sung in the 12 weeks before this service or planned in the 12 weeks after it."
  - When on and `n > 0` hidden hymns in the selected hymnal: "{n} hymns are hidden."
  - Writes `draft.hymns.exclude_recent`. It never changes slots or chips.
  - When the draft date is invalid, the switch is disabled with the helper "Pick a valid date in step 1 to check recent use."
- **Suggest hymns** (full-width touch button with a Sparkles icon).
  - Helper: "Fills empty slots and shows other ideas under each hymn."
  - Disabled while pending, when the selected hymnal has no hymns, or when the date is invalid.
  - When the draft has no scriptures and no occasion, it adds: "Tip: add the readings in step 1 first — suggestions use them."

### AI suggestion flow

1. Tap **Suggest hymns**. The button shows a spinner and "Suggesting…".
   - After 8 s: "Still working — this can take up to a minute."
   - A **Cancel** link aborts the client wait. The server finishes and discards the result (F §1.8).
2. On success the result is applied with a functional draft update (`applySuggestions`, §Frontend), so any pick the user made during the wait counts:
   - **empty slot**: gets the top pick; its chips are the next results (2–4);
   - **filled slot**: keeps its pick; its chips are the results minus the current pick (3–4);
   - `alternatives = {for_date_iso: request date, by_slot}`.
3. What the button area shows afterwards (component state, never stored in the draft):
   - hymns returned for at least one slot: "Suggestions ready. Tap an idea under a hymn to swap it in." When `excluded_recent_count > 0` it adds " {n} recently used hymns were left out.";
   - nothing returned for any slot (possible only when the hymnal has almost no eligible hymns, because an AI answer with no usable hymn is a 502, §3.6 step 9): "The AI didn't pick any hymns from this hymnal. Try again, or choose hymns yourself.";
   - some slots returned nothing (same condition): that slot's card says "No suggestion for this slot."
4. If the draft date changed while the request was pending, the result is discarded and the step shows "The date changed while suggestions were loading. Try again."
5. Errors appear in an inline `Alert` under the button (component state, never stored), keyed on `code` (F §1.5):

   | Code | Copy |
   |---|---|
   | `ai_not_configured` | "AI suggestions aren't set up on this app yet. You can still choose hymns yourself." |
   | `ai_busy` | "The AI service is busy. Try again in a minute." |
   | `ai_timeout` | "The AI took too long to answer. Try again." |
   | `ai_upstream_error` | "The AI service had a problem. Try again in a moment." |
   | `invalid_request` | The server message (for example the empty-hymnal message below) |
   | `rate_limited` | "Too many requests — try again in {n} s." (global pattern) |
   | `timeout` (client) | "This is taking too long. Try again." |
   | `aborted` | Nothing; back to idle |

   Network errors and 500s use the global handling (F §4.8).

### Hymns for the readings (`ScriptureMatches`)

- A collapsible section, closed by default below `md` and open at `md+`. Its title is "Hymns for the readings", with a count badge once loaded.
- **References:** the draft's scriptures plus an **Additional scripture** input (placeholder "e.g. Matthew 17", `maxLength={200}`) with a **Search** button. Enter also submits. The input lives in component state only. The request's `refs` come from the pure `buildMatchRefs(scriptures, extraRef)` (§Frontend), which applies the server's limits (each trimmed, blanks dropped, each cut to 200 characters, at most 20, the extra reference always kept), so a long typed line can never cause a 422 that Retry cannot clear. An over-long reference that is cut shows up at worst as unreadable (below), never as an error.
- The query runs automatically whenever the reference list, the selected hymnal or the date changes.
- **Results** come in two groups, "Matches the readings" (`strength = passage`) and "Same chapter" (`strength = chapter`). Each row shows:
  - `HymnLabel`;
  - the matched reference(s) as small text, "Matches Mark 1:9-15";
  - an **Add** button that opens a `DropdownMenu` with "Opening hymn / Response hymn / Closing hymn". Choosing one sets that slot. If the slot was filled, the toast "{Slot} hymn changed to {title}." offers **Undo**.
- With exclusion on, recently used matches are hidden and the footer reads "{k} recently used matches are hidden. [Show them]", a local toggle. With exclusion off, they show a badge.
- Unreadable references: "Couldn't read “{text}” as a scripture reference."
- **No references:** "Add the readings in step 1, or type a scripture reference here." with a link "Go to readings" → `/builder/readings`.
- **No matches:** "No hymns in {hymnal} match these readings. Try a shorter reference, such as “Matthew 17”."
- **Hymnal without scripture data** (`scripture_ref_count == 0`): the section skips the request and shows "{code} has no scripture references, so it can't be searched by scripture."
- **Loading and errors:** three skeleton rows while loading. On error: `ErrorState` "Couldn't search the hymnal." with Retry.
- The Hymnary credit caption stays under the section (parity, app.py:710-713).

### Whole-step states

- **Loading.** Slot cards render immediately from the draft snapshot. Pickers are disabled with "Loading hymnal…" and the toolbar shows skeletons until `GET /hymnals` and the hymnal list load. There is no full-page spinner.
- **Hymnals or list failed.** An `ErrorState` replaces the pickers and the matches: "Couldn't load this church's hymnal." with **Retry**. Existing picks stay visible from the snapshot.
- **Empty hymnal** (`GET /hymnals` returns no items). An `EmptyState` replaces the toolbar, pickers and matches:
  - title "This church's hymnal is empty";
  - body "Add hymns on the Settings → Hymns page to choose hymns here.";
  - action "Open Settings → Hymns" → `/settings/hymns`, only when `SETTINGS_HYMNS_READY` (6a). Before 6a the body reads "Add hymns in the current app under Settings → Hymns." and there is no action.

  Existing picks still show, each with the "Not in your hymnal" notice.
- **Church switch.** The `(church)` layout remounts (F §4.2): component state resets and the other church's draft loads.

### Builder shell: Hymns status and summary (F §4.7)

This slice turns the Hymns step on in slice 2's shell. The Liturgy and Review parts stay as slice 2 left them until slices 4 and 5a.
- **`StepProgress`:** the Hymns item drops the muted "Soon" label and shows `stepStatus` for hymns: `complete` (✓) when all three slots are filled, otherwise `incomplete` with "n of 3" (filled slots). A pick shown as "Not in your hymnal" still counts as filled, because the slot holds a pick.
- **Review → "Still needed":** now that `"hymns"` is shipped, `stillNeeded` adds one row per empty slot, in slot order, each linking to `/builder/hymns`: "No Opening hymn — Choose one", "No Response hymn — Choose one", "No Closing hymn — Choose one" (F §4.7's wording).
- **`SummaryPanel` Hymns block** (desktop column and mobile bottom sheet), replacing "Available soon". It links to `/builder/hymns` like the other blocks and shows three rows in slot order:
  - filled: "Opening · #403 Come, Thou Almighty King" ("Opening · {title}" when the number is null);
  - empty: "No Opening hymn" (likewise "No Response hymn", "No Closing hymn") in muted text.

  It reads only the draft snapshot (`hymns.slots`), so the shell never loads a hymnal list on other steps. The Liturgy block keeps "Available soon" until slice 4.

---

## API

All four routes are church-scoped (`require_church`). Members of any role may call them. Bodies use `extra="forbid"`. Pydantic enforces only types and maximum sizes; friendly messages come from the usecase (F §1.3). Every error body follows F §1.5.

| Method | Path | Guard | Request | Response | Errors (status · code · message) |
|---|---|---|---|---|---|
| GET | `/hymnals` | church | — | 200 `HymnalListOut` | 401 · 403 |
| GET | `/hymns` | church | query `hymnal?` (≤20), `q?` (≤100; 1–6 digits also match `number`), `limit` 1–2000 (default 50), `offset` ≥0 (default 0), `recent_for_date?` (`YYYY-MM-DD`) | 200 `Page[HymnOut]` | 401 · 403 · 422 `invalid_request` "The request was not valid." (bad limit or date, with `fields`) |
| POST | `/hymns/scripture-matches` | church | `ScriptureMatchIn` | 200 `ScriptureMatchesOut` | 401 · 403 · 422 `invalid_request` "Enter at least one scripture reference." (`fields.refs`) · 422 `invalid_request` "That hymnal isn't in this church's library." (`fields.hymnal`) |
| POST | `/hymns/suggestions` | church + `rate_limit("ai")` | `HymnSuggestionIn` | 200 `HymnSuggestionsOut` | 401 · 403 · 422 `invalid_request` "That hymnal isn't in this church's library." (`fields.hymnal`) · 422 `invalid_request` "This hymnal has no hymns to suggest from." · 422 `invalid_request` "Every hymn in this hymnal was used within 12 weeks of this service. Turn off “Exclude” and try again." · 429 `rate_limited` (+`Retry-After`) · 503 `ai_not_configured` "AI suggestions aren't set up on this app yet." (also for an exhausted OpenAI quota, §3.7) · 503 `ai_busy` "The AI service is busy. Try again in a minute." · 504 `ai_timeout` "The AI took too long to answer. Try again." · 502 `ai_upstream_error` "The AI service had a problem. Try again." or "The AI gave an answer we couldn't use. Try again." |
| GET | `/church` (extended) | church | — | `ChurchProfileOut` + `default_hymnal: str \| null`, `effective_hymnal: str \| null` | unchanged |

No route is user-scoped, so nothing is added to the `USER_SCOPED` allowlist in `test_route_guards.py`. There are no path ids. Client-timeout entries (F §1.8): default 20 000 ms, and `POST /hymns/suggestions` 90 000 ms.

### Models

In `backend/api/routes/hymnals.py`:

```python
class HymnalOut(BaseModel):
    code: str                     # e.g. "GG2013"
    hymn_count: int
    scripture_ref_count: int      # hymns with non-blank scripture_refs

class HymnalListOut(BaseModel):
    items: list[HymnalOut]        # ORDER BY code
    default_hymnal: str | None    # churches.settings["default_hymnal"] verbatim (non-empty string) or null
    effective_hymnal: str | None  # default_hymnal if it is in items; else items[0].code; else null
```

In `backend/api/routes/hymns.py`:

```python
class HymnOut(BaseModel):
    id: uuid.UUID
    hymnal: str
    title: str                    # stripped; "" when NULL
    number: int | None
    link: str | None              # hymnary_link verbatim; the client renders it only via safeHttpsUrl
    scripture_refs: str | None
    themes: list[str]             # hymn_search.parse_themes(theme)
    recent_use_on: date | None    # nearest usage date in the recent window; null when no date given

class ScriptureMatchIn(BaseModel):          # extra="forbid"
    refs: list[Annotated[str, StringConstraints(max_length=200)]] = Field(default_factory=list, max_length=20)
    hymnal: Annotated[str, StringConstraints(max_length=20)] | None = None   # null = effective_hymnal
    recent_for_date: date | None = None
    limit_per_ref: int = Field(50, ge=1, le=100)
    max_results: int = Field(20, ge=1, le=100)

class HymnMatchOut(HymnOut):
    strength: Literal["passage", "chapter"]
    matched_refs: list[str]       # the query references (after the ' or ' split) that matched

class ScriptureMatchesOut(BaseModel):
    hymnal: str | None
    refs_used: list[str]          # trimmed, non-blank, after the ' or ' split, in order
    unparsed_refs: list[str]      # query refs that could not be read as scripture
    total_matched: int            # before max_results truncation
    items: list[HymnMatchOut]     # passage tier first, then chapter tier

class SlotPicks(BaseModel):                 # extra="forbid"
    opening: uuid.UUID | None = None
    response: uuid.UUID | None = None
    closing: uuid.UUID | None = None

class HymnSuggestionIn(BaseModel):          # extra="forbid"
    service_date_iso: date
    occasion: Annotated[str, StringConstraints(max_length=300)] = ""
    scriptures: list[Annotated[str, StringConstraints(max_length=200)]] = Field(default_factory=list, max_length=20)
    selected_nt_ref: Annotated[str, StringConstraints(max_length=200)] | None = None
    nt_text: Annotated[str, StringConstraints(max_length=20_000)] | None = None
    hymnal: Annotated[str, StringConstraints(max_length=20)] | None = None
    exclude_recent: bool = True
    current_picks: SlotPicks = Field(default_factory=SlotPicks)

class SuggestedHymnOut(HymnOut):
    source: Literal["ai", "candidates"]   # "candidates" = added by the minimum top-up (§3.6 step 9); the UI ignores it

class SuggestedSlots(BaseModel):
    opening: list[SuggestedHymnOut]   # ≤5, best first; ≥3 not counting the slot's own current pick, when the candidates allow
    response: list[SuggestedHymnOut]
    closing: list[SuggestedHymnOut]

class HymnSuggestionsOut(BaseModel):
    hymnal: str
    nt_ref: str | None            # NT reference used for context
    nt_text_used: bool
    excluded_recent_count: int
    slots: SuggestedSlots
```

In `backend/api/schemas.py` (shared). The three hymn and liturgy models below are **frozen in F §1.3** and created here with exactly that shape, because this slice lands first:

```python
SectionKey = Literal["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                     "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction"]

class HymnRef(BaseModel):                   # F §1.3 (frozen); used by 4 (liturgy) and 5a (services, documents)
    model_config = ConfigDict(extra="forbid")
    hymn_id: uuid.UUID | None = None                    # null = archived snapshot, used as sent
    title: str = Field(default="", max_length=300)      # ignored when hymn_id is set (F §1.3)
    number: int | None = Field(default=None, ge=0, le=100_000)
    hymnal: str | None = Field(default=None, max_length=20)
    # No pattern on `hymnal`: a pick echoes hymns.hymnal from the database (pickFromHymn), and codes
    # written by CLI imports were never pattern-checked. A pattern here would turn a pick from such a
    # hymnal into a 422 on /liturgy/generate, /services, /documents and /bulletin-emails.

class SlotHymns(BaseModel):                 # F §1.3 (frozen); 4's GenerateLiturgyIn.hymns, 5a's ServiceDraft.hymns
    model_config = ConfigDict(extra="forbid")
    opening: HymnRef | None = None
    response: HymnRef | None = None
    closing: HymnRef | None = None

HymnalCode = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{2,20}$")]
# Only for query and path parameters that name a NEW or admin-managed hymnal code (6a: DELETE /hymnals/{code},
# a new code in hymn create or hymnal import). Never on HymnRef, and never on this slice's read filters
# (GET /hymns `hymnal`, ScriptureMatchIn.hymnal, HymnSuggestionIn.hymnal), which must accept any stored code.
```

Notes on the models:
- `Page[T]` (`items`, `total`, `limit`, `offset`) goes in `api/schemas.py`. If it does not exist yet, this slice creates it, and 5a reuses it.
- `HymnRef`, `SlotHymns` and `SectionKey` are created here and no slice-3 route uses them, so they do not appear in the OpenAPI snapshot until slice 4 adds a route that does. `test_schemas.py` covers them: extra field rejected (on `HymnRef` and on `SlotHymns`); `title` of 300 characters accepted and 301 rejected; `number` of -1 and 100 001 rejected; `hymnal` of 21 characters rejected; **a `hymnal` that breaks the `HymnalCode` pattern (for example `"PH 1990"` or `"X"`) accepted**; `hymn_id: null` accepted; an unknown section key rejected by a model typed with `SectionKey`. 4 and 5a import them, keep their own tests, and neither redefine nor tighten them. No slice-3 field uses `HymnalCode`.
- In suggestion results, `recent_use_on` is always computed against `service_date_iso`, whatever `exclude_recent` is.
- **`GET /hymns` ordering:** `hymnal ASC, number ASC NULLS LAST (nulls_last()), lower(title) ASC, id ASC`.
  - `q` (trimmed; empty means no filter): **1 to 6 digits** → `number = int(q) OR lower(title) LIKE %q%`; otherwise, including longer digit strings, `lower(title) LIKE %lower(q)%`, built with `.contains(…, autoescape=True)`. The digit cap keeps a long all-digit `q` from binding an integer above 2^63, which raises `OverflowError` (a 500) on SQLite.
  - `hymnal` filters exactly. An unknown hymnal returns an empty page, not an error, because this is a list filter.
  - `total` counts every row matching the filter, blank titles included (6a must be able to fix them).
- **Hymnal resolution for matches and suggestions:** `hymnal: null` means `effective_hymnal`. A value not among the church's hymnals raises `InvalidInput(field="hymnal")`. The message is the same whether the code exists in another church or nowhere, so nothing leaks.
- **`current_picks`** are used only as exclusion hints (§3.6 steps 6 and 9). Ids that are not in this church's hymnal are ignored silently, and nothing about them is returned.
  - **Declared exception to F §1.2 rules 2 and 5.** Rule 2 returns 404 for another church's id because the route would otherwise resolve or act on it. These ids are never resolved, loaded, echoed or used to reveal anything; they are only compared against this church's pool. A stale pick of a deleted hymn is also normal draft state, and a 404 would break Suggest for it. So no 404 is raised, and the 404 half of `assert_church_isolated` (`resource_path_b`) is not used for any slice-3 route (none has a resolved path or body id). The isolation tests instead assert that B's id is ignored and never echoed (§Testing).

---

## Backend changes

### 1. Module map

| Module | Change |
|---|---|
| `backend/integrations/openai_client.py` | **New** (F §2.8, with the refinements in §3.7): settings, `ai_available()`, `complete(messages, *, max_completion_tokens, json_mode=False, deadline=None)`, the process-wide semaphore, the capped client-side retry, error mapping, `FakeAI` + `set_ai_for_tests()`. Adds the startup log line in §3.7. |
| `backend/api/settings.py` | Adds the `OPENAI_*` settings from F §2.8. The key is stripped; non-ASCII means not configured. |
| `backend/scripture_refs.py` (from 2) | **Extended:** slice 2's `BOOKS` (66 books plus the deuterocanon) gains a single-chapter flag and any aliases in §2 step 4 that it lacks; `RefSpan`; `parse_refs(text) -> ParsedRefs`; `spans_overlap(a, b)`; `same_chapter(a, b)`. There is one book table: `classify` and `parse_refs` both read `BOOKS`, and slice 2's shared `scripture_refs.json` fixtures must still pass. If slice 2 shipped only the 66 books, slice 3 adds the deuterocanon with testament `"ot"`. |
| `backend/hymn_search.py` | **New, pure:** `normalize_title`, `usage_key`, `parse_themes`, `match_hymns`, `evenly_spaced`. |
| `backend/hymn_suggest.py` | **New, pure:** `build_candidates`, `build_prompt`, `parse_suggestion_json`, `resolve_suggestions`, `finalize_slots`; the theme keyword sets move here from worship_service.py:364-377. |
| `backend/repos/hymns.py` | **Adds** `HymnRecord` (frozen dataclass: `id, hymnal, title, number, link, scripture_refs, theme`), `hymnal_summaries(church_id, *, session=None)`, `query_hymns(church_id, *, hymnal=None, q=None, limit=50, offset=0, session=None) -> tuple[list[HymnRecord], int]`, `list_hymnal_records(church_id, hymnal, *, session=None) -> list[HymnRecord]` (hymnal order). `list_hymns` and `list_church_hymnals` are unchanged (CLI and frozen Streamlit). Ids go through `db.ids.as_uuid()` (F §2.2.5). |
| `backend/hymn_usage.py` | **Adds** `RECENT_WEEKS = 12` and `usage_near(church_id, service_date, *, weeks=RECENT_WEEKS, session=None) -> dict[tuple[int \| None, str], date]` (§3.4), which tolerates `date_iso` values that are not `YYYY-MM-DD`. `get_recently_used_identifiers` and `record_usage` are unchanged (5a replaces recording). |
| `backend/usecases/hymns.py` | **New:** `hymnal_overview`, `list_hymns_page`, `scripture_matches`, `suggest_hymns`, `resolve_default_hymnal`. No FastAPI imports (F §2.2). |
| `backend/api/routes/hymnals.py`, `backend/api/routes/hymns.py` | **New.** Thin routes (F §2.2.1), mounted in `create_app`. |
| GET `/church` usecase (from 2) | Calls `usecases.hymns.resolve_default_hymnal(church_id, session=s)` and adds the two fields. |
| `backend/api/ratelimit.py` (from 2) | Registers `ai`: 40 per 10 min per user **and** 400 per day per church (F §1.8). If slice 2 built only user-keyed buckets, `rate_limit("ai")` gains a church-keyed second bucket. It reads the church from the resolved `require_church` dependency, never from the raw header. |
| `backend/api/main.py` | Adds `GZipMiddleware(minimum_size=1024)` **first**, so it is innermost. The F §2.5 order of UnhandledError, RequestId and CORS is unchanged around it. Reason: `GET /hymns?limit=2000` for one hymnal is about 150–250 KB of JSON uncompressed. The F §2.5 order becomes: add `GZipMiddleware`, then `UnhandledErrorMiddleware`, `RequestIdMiddleware`, `CORSMiddleware`. |
| ops middleware-order test (from ops) | **Updated in the same PR:** the test that walks `app.user_middleware` now expects CORS, RequestId, UnhandledError, GZip (outermost first). Without this change the ops test fails. |
| `backend/worship_service.py` | **Deleted:** `_BOOK_ABBREVS`, `_scripture_search_variants`, `hymns_by_scripture` (with the Notion path), `_OPENING_THEMES`, `_CLOSING_THEMES`, `_hymn_matches_theme`, `suggest_hymns_for_service`, `hymn_display_info`, `_hymnary_audio_url`, `resolve_hymnary_audio_url`, `_hymnary_audio_resolve_cache`, the `NotionHymnsDB` TYPE_CHECKING import, and `load_dotenv()` at import (F §2.3.5). `generate_liturgy` and `build_docx` stay until 4 and 5a. |
| `backend/requirements.txt` | Remove `lxml`: its only runtime user was the audio resolver. `beautifulsoup4` stays until `fill_from_hymnary.py` is deleted in 7. **Raise `openai>=1.0.0` to `openai>=1.45.0`**, the first release whose `chat.completions.create` accepts `max_completion_tokens` (`response_format={"type": "json_object"}` is older). With an older SDK every call would raise `TypeError`, a 500. A test asserts the installed SDK's `create` signature has `max_completion_tokens`. |
| `backend/.env.example` | Replace `OPENAI_MODEL=gpt-3.5-turbo` with the model chosen at deploy, and add `OPENAI_TIMEOUT_SECONDS=30`, `OPENAI_MAX_RETRIES=1`, `OPENAI_MAX_CONCURRENCY=4`, and a commented `# OPENAI_TEMPERATURE=`. |

If the F §6.1 contingency is in force (Streamlit still runs from `main`), keep `hymns_by_scripture`, `suggest_hymns_for_service` and `hymn_display_info` as thin wrappers over the new code, with an `AppTest` smoke test. Otherwise delete them (F §2.3).

### 2. Scripture matcher (owner decision 9: tightened matching)

**Parsing: `scripture_refs.parse_refs(text) -> ParsedRefs(spans: tuple[RefSpan, ...], unparsed: tuple[str, ...])`.** This is pure and `lru_cache(maxsize=4096)` on the raw string. The same parser reads query references and the hymns' `scripture_refs` fields.

1. **Normalize:** NFKC; en and em dashes → `-`; collapse whitespace; strip.
2. **Alternatives:** split on `\s+or\s+`, case-insensitive (`split_alternatives`). Each alternative is parsed on its own. This fixes the case-sensitive split in inv C9/D4.
3. **Segments:** split on `;` and on newlines. Also split on `,` when the text after the comma begins with a known book name. Otherwise the comma continues the current location list (for example "Romans 4:1-5, 13-17").
4. **Book:** an optional ordinal (`1|2|3|4|I|II|III|IV|1st|2nd|3rd|4th|First|Second|Third|Fourth`), then name words, with trailing periods ignored. The result is looked up case-insensitively in `BOOKS`, and the **longest** matching alias wins (so "Song of the Three" is not read as "Song" plus junk). `BOOKS` holds:
   - the 66 canonical names; every `_BOOK_ABBREVS` variant (worship_service.py:162-231) in **both** directions; `Ps`, `Pss`, `Psalm`, `Psalms`; `Song`, `Song of Songs`, `Song of Solomon`, `Canticles`; no-space forms such as `1Cor`; and `Revelations`;
   - the deuterocanon that the RCL and Vanderbilt's rows cite, with testament `"ot"`: `Wisdom` / `Wisdom of Solomon` / `Wis` / `Ws`; `Sirach` / `Sir` / `Ecclesiasticus` / `Ecclus`; `Baruch` / `Bar`; `Tobit` / `Tob` / `Tb`; `Judith` / `Jdt` / `Jth`; `1`–`4 Maccabees` / `Macc` / `Mc`; `Song of the Three` / `Song of the Three Jews` / `Song of the Three Young Men` / `Prayer of Azariah` / `Pr Azar`; `Letter of Jeremiah` / `Ep Jer`; `Susanna` / `Sus`; `Bel and the Dragon` / `Bel`; `1`–`2 Esdras` / `Esd`; `Prayer of Manasseh` / `Pr Man`; `Additions to Esther` / `Add Esth`. The single-chapter ones (Song of the Three, Letter of Jeremiah, Susanna, Bel and the Dragon, Prayer of Manasseh) get the single-chapter flag.

   A segment with no book inherits the previous segment's book. A segment with no book and no previous book is unparsed.
5. **Location list items:** `C`, `C-C`, `C:V`, `C:V-V`, `C:V-C:V`.
   - Verse letter suffixes `a`–`d` are ignored.
   - `ff` or `f` makes the end open (to the end of the chapter).
   - After an item that has verses, a bare number means a verse in the same chapter. Otherwise a bare number is a chapter.
   - Single-chapter books (Obadiah, Philemon, 2 John, 3 John, Jude, and the single-chapter deuterocanonical books in step 4): `N` and `N-M` are verses of chapter 1.
   - A book with no location means the whole book: chapters 1–999.
6. **Span:** each item becomes `RefSpan(book, start=(c1, v1), end=(c2, v2))`. A whole-chapter start is `v1 = 0` and a whole-chapter end is `v2 = 999`.
7. Anything else goes to `unparsed`, as normalized text.

**Matching: `hymn_search.match_hymns(pool, refs, *, limit_per_ref=50, max_results=20) -> MatchResult(items, total_matched, refs_used, unparsed_refs)`.**
- For a query span Q and a hymn span H of the **same canonical book**:
  - **passage**: `Q.start <= H.end and H.start <= Q.end`, compared as tuples;
  - **chapter**: otherwise, if the chapter ranges `[Q.c1, Q.c2]` and `[H.c1, H.c2]` intersect.
- **Unparsed hymn segments** fall back to a boundary-aware text test, which yields **chapter** at most. The pattern is `(?<![0-9A-Za-z])(?<!\d )` + a book alias + `\s*` + the chapter + `(?![0-9])`, tried for each query span's book aliases and first chapter. So "Psalm 1" never hits "Psalm 119", and "John 3" never hits "1 John 3".
- A hymn's strength is its best across all query spans. `matched_refs` lists every query ref that matched it.
- **Ordering:** passage tier before chapter tier. Within a tier, by the index of the first matching query ref, then pool order (hymnal order).
- **Limits:** `limit_per_ref` caps matches attributed to each query ref (a hymn counts once, at its first ref). `max_results` truncates after ordering.
- Hymns with a blank title or blank `scripture_refs` are skipped.

**Required results.** The first four are the verified over-matches in inv §0 item 5:

| Query | Hymn refs | Result |
|---|---|---|
| Isaiah 9:6 | Genesis 9:6 | no match |
| Mark 1:9-15 | Mark 10:45 | no match |
| Psalm 1 | Psalm 119 | no match |
| John 3:1-17 | 1 John 3:16 | no match |
| Matthew 17 | Matt 17:1-8 | passage (reverse abbreviation, inv D4) |
| Psalm 99 | Psalms 99 | passage |
| Genesis 12:1-4a | Genesis 12:1 | passage |
| Mark 1:9-15 | Mark 1:1-8 | chapter |
| Isaiah 9:2-7; 11:1 | Isaiah 11:1-9 | passage (`;` carry-forward, inv D4) |
| Luke 24:13-35 or Mark 16:1-8 | Mark 16:6 | passage (the `or` split) |
| Jude 24-25 | Jude 24 | passage (single-chapter book) |
| Baruch 5:1-9 | Bar 5:5 | passage (deuterocanon, RCL Advent 2 C); not reported as unreadable |
| Wisdom of Solomon 1:13-15; 2:23-24 | Wis 2:23 | passage (deuterocanon plus `;` carry-forward) |
| Sirach 27:4-7 | Ecclesiasticus 27:4 | passage (alias in both directions) |
| Song of Solomon 2:8-13 | Song 2:10 | passage (still Song of Songs, not Song of the Three) |
| Transfiguration | (any) | unparsed; no match |

### 3. Usecases (`backend/usecases/hymns.py`)

#### 3.1 `resolve_default_hymnal(church_id, *, session=None) -> DefaultHymnal(default_hymnal, effective_hymnal)`

- `stored = churches.settings.get("default_hymnal")`. It counts only as a non-empty string after `strip()`; any other value counts as unset.
- `codes = [s.code for s in hymnal_summaries(church_id)]`, in alphabetical order.
- `effective = stored if stored in codes else (codes[0] if codes else None)`. The alphabetical fallback matches Streamlit (app.py:650).
- `GET /hymnals` and `GET /church` both use this function, so the two can never disagree.

#### 3.2 `hymnal_overview(church_id) -> HymnalListOut data`

One session: `hymnal_summaries` plus `resolve_default_hymnal`.

#### 3.3 `list_hymns_page(church_id, *, hymnal, q, limit, offset, recent_for_date) -> page`

One session: `query_hymns`. If `recent_for_date` is given, also `usage_near(church_id, recent_for_date)`, and each record's `recent_use_on = usage.get(usage_key(record))`.

#### 3.4 Recent-use window (`hymn_usage.usage_near`)

- **Window:** usage dates in `[D - 84 days, D + 84 days]`, both bounds inclusive, excluding D itself. D is the **service date**, not today (F §7.4).
- **Not every `date_iso` is `YYYY-MM-DD`.** Rows imported from Notion by `migrate_to_db` store Notion's `start` as is (backend/migrate_to_db.py:344-350), which can be `""` or a datetime such as `2026-08-02T10:00:00.000-05:00`. So the window is applied in two steps:
  1. **SQL (index-friendly, deliberately wide):** `date_iso >= 'D-84' AND date_iso < 'D+85'` as string comparisons. This keeps datetime-shaped values on D+84 (they sort after `'D+84'`), and drops NULL, `""` and most junk.
  2. **Python (exact):** `day = date_iso[:10]`, parsed with `date.fromisoformat`. A value that still fails to parse (for example `2026-8-2`) is skipped and counted, and the count is logged at DEBUG. Then `D-84 <= day <= D+84 and day != D` is applied to the parsed date, so a datetime-shaped value on D itself is excluded too.

  Nothing in this path raises on bad stored data, so a stray row can never turn `GET /hymns?recent_for_date=` or a suggestion call into a 500.
- **Key:** `usage_key(number, title) = (number, normalize_title(title))`. `normalize_title` collapses whitespace, strips and casefolds. The key is the same as `is_hymn_recently_used` today (hymn_usage.py:45-47), just more tolerant of whitespace.
- **Value:** the usage date nearest D; ties go to the earlier date. The UI labels a date before D "Used on …" and a date after D "Also planned for …".
- Uses the index `ix_hymn_usage_church_date`. It reads rows written by either app (frozen Streamlit Prepare, and 5a Save).

#### 3.5 `scripture_matches(church_id, *, refs, hymnal, recent_for_date, limit_per_ref, max_results)`

1. `refs_used`: trim each ref, drop blanks, and apply `split_alternatives`. If nothing is left → `InvalidInput(field="refs", message="Enter at least one scripture reference.")`.
2. Resolve the hymnal (§API notes). If `effective_hymnal` is null (empty church hymnal), return an empty result.
3. One session: `list_hymnal_records(church_id, hymnal)`, plus `usage_near` when a date is given.
4. `match_hymns(...)`. Then map to `HymnMatchOut` with `recent_use_on`.

#### 3.6 `suggest_hymns(church_id, user_id, req, *, ai=openai_client, fetch_text=passages.get_passage_text, clock=time.monotonic) -> HymnSuggestionsOut data`

0. **Deadline.** `deadline = clock() + SUGGEST_BUDGET_S` (75 s, the F §1.8 server worst case) is set on entry. Every later wait is bounded by it (§3.7 has the arithmetic). `SUGGEST_BUDGET_S` and `NT_FETCH_BUDGET_S` are module constants so tests can shrink them.
1. **Read phase** (one session, closed before any external call, F §1.8): resolve the hymnal; `pool = list_hymnal_records(...)` minus blank titles; `usage = usage_near(church_id, req.service_date_iso)`, always read, for `recent_use_on`.
2. `pool` is empty → `InvalidInput(field="hymnal", "This hymnal has no hymns to suggest from.")`.
3. If `req.exclude_recent`: `eligible = [h for h in pool if usage_key(h) not in usage]` and `excluded_recent_count = len(pool) - len(eligible)`. Otherwise `eligible = pool` and the count is 0. `eligible` is empty → `InvalidInput("Every hymn in this hymnal was used within 12 weeks of this service. Turn off “Exclude” and try again.")`.
4. `ai.ai_available()` is false → `NotConfigured("ai_not_configured", "AI suggestions aren't set up on this app yet.")`. The check runs before any network call.
5. **NT context:**
   - `nt_ref = req.selected_nt_ref or scripture_refs.default_nt_ref(req.scriptures)`.
   - If `req.nt_text` is non-blank, use it (`nt_source = "client"`).
   - Otherwise, if `nt_ref` is set, the fetch runs as `future = _NT_EXECUTOR.submit(fetch_text, nt_ref, "web")` on a module-level `ThreadPoolExecutor(max_workers=4, thread_name_prefix="nt-fetch")`, and the usecase waits `future.result(timeout=min(NT_FETCH_BUDGET_S, remaining))` with `NT_FETCH_BUDGET_S = 10`. This enforces the 10 s budget even though slice 2's `get_passage_text` takes no deadline and can take up to 20 s (F §1.8). On timeout the usecase continues without text (`nt_source = "timeout"`). The abandoned fetch finishes in the background, and its result still fills slice 2's 7-day passage cache for the next request. Any other failure, or `None`, also means no text (`nt_source = "none"`); it is logged, not raised.
   - The text is truncated to 1 500 characters for the prompt (parity, worship_service.py:497).
   - The server always fetches WEB, never ESV (see Behavior changes 8).
6. **Candidates** (`hymn_suggest.build_candidates(eligible, refs, *, nt_ref, current_picks)`), one list per slot, each at most `SLOT_CAP = 50`:
   - **response**: `match_hymns(eligible, refs, limit_per_ref=30, max_results=200)`, passage tier then chapter tier (parity limit of 30 per ref, worship_service.py:460-464). `refs` puts the alternatives of `nt_ref` **first**, then the rest of `split_alternatives` over `req.scriptures`, without duplicates. Because `match_hymns` orders each tier by the index of the first matching query ref, the NT reading's matches (which the ROLE REQUIREMENTS say the response hymn should fit) lead each tier, and truncating to `SLOT_CAP` cuts the other readings' chapter-tier matches first.
   - **opening**: hymns whose normalized themes match `_OPENING_THEMES` by word start (`\bkeyword`);
   - **closing**: the same with `_CLOSING_THEMES`.
   - **Other slots' picks removed first.** Before capping, padding and prompt building, each slot's list drops the other two slots' `current_picks` ids. The AI therefore never sees another slot's chosen hymn as a candidate for this slot. A slot's own current pick may stay in its own list.
   - **Capping.** A response list longer than `SLOT_CAP` is truncated in the order above. An opening or closing list longer than `SLOT_CAP` (for example "praise" or "joy" in GG2013) is reduced with `evenly_spaced(list, SLOT_CAP)` rather than truncated, so it is not biased to low hymn numbers.
   - **Padding.** Any list with fewer than 15 focused hymns is padded to 40 with `evenly_spaced(remaining, k)`, which is `remaining[floor(i * len(remaining) / k)]` for `i` in `0..k-1`, over the rest of `eligible` (minus the other slots' current picks) in hymnal order. This replaces "first 80", which for PH1990 meant Advent-only hymns (inv D7).
7. **Prompt** (`build_prompt`), deterministic and at most 24 000 characters (F §2.8):
   - a system message: "You help a church choose hymns for a worship service. Reply with JSON only.";
   - a user message containing:
     - `OCCASION`, `SCRIPTURE READINGS`, `NEW TESTAMENT READING` and `NT PASSAGE TEXT (excerpt)` (parity fields);
     - the ROLE REQUIREMENTS text for the three slots (parity, worship_service.py:508-511);
     - one `HYMNS` catalogue listing every distinct candidate once: `H{k} | {title ≤80} | #{number or –} | themes: {≤60} | scripture: {≤60}`, with tokens `H1…Hn` in first-seen order;
     - `OPENING CANDIDATES: H…, …`, and the same for RESPONSE and CLOSING;
     - `Return {"opening": [ids], "response": [ids], "closing": [ids]}, with exactly 5 ids per slot (all of that slot's ids if it lists fewer than 5), best first, using only ids listed for that slot, and never the same hymn in two slots.`
   - If the result exceeds 24 000 characters, drop the last candidate of the longest slot list (and its catalogue line when no other list uses it), and repeat. `build_prompt` returns `(messages, token_map)`.
8. **Call:** `raw = ai.complete(messages, max_completion_tokens=1200, json_mode=True, deadline=deadline)`. Errors map as in §3.7. `temperature` is sent only when `OPENAI_TEMPERATURE` is set.
9. **Parse and resolve:**
   - `parse_suggestion_json(raw)` strips code fences (parity, worship_service.py:531-535) and runs `json.loads`. It requires a dict whose slot values are lists. Anything else → `UpstreamError("ai_upstream_error", "The AI gave an answer we couldn't use. Try again.")`.
   - `resolve_suggestions(parsed, token_map, eligible)` maps `^H\d+$` tokens (case-insensitive) to records.
     - A non-token string resolves only by **exact** `normalize_title` equality within `eligible`. When titles collide, the one that appears in that slot's candidate list wins, then the lowest number.
     - There is no substring or fuzzy matching (inv D7), and unknown values are dropped.
     - Each slot is deduplicated.
     - If no slot resolves to any hymn, the answer is unusable → the same `UpstreamError` "The AI gave an answer we couldn't use. Try again." (a silent top-up of all three slots from candidates would present a non-AI answer as a suggestion).
   - `finalize_slots(resolved, current_picks, candidates)` guarantees owner decision 3's minimum of a top pick plus 2 alternatives. `MIN_PER_SLOT = 3`, `MAX_PER_SLOT = 5`.
     1. **Top picks.** `reserved` = the non-null current picks. For each slot with no current pick, in the order opening, response, closing: its top pick is the first hymn in its AI list that is not in `reserved`; if there is none, the first such hymn in its candidate list (`source: "candidates"`). The top pick joins `reserved`. So top picks are distinct across slots and never another slot's current pick.
     2. **AI alternatives.** For each slot, `blocked` = `reserved` minus that slot's own current pick and own top pick. The list is the top pick (if any), then the slot's AI hymns that are not in `blocked` and not yet listed, in AI order (`source: "ai"`).
     3. **Minimum top-up.** While the list has fewer than `MIN_PER_SLOT` hymns other than the slot's own current pick, append the next hymn from that slot's candidate list, in candidate order, that is not in `blocked` and not yet listed (`source: "candidates"`). Stop when the candidates run out; only a hymnal with very few eligible hymns ends below the minimum.
     4. Cap the list at `MAX_PER_SLOT`.

     The client then shows an empty slot's top pick plus 2–4 chips, and a filled slot's 3–4 chips (its own pick filtered out).
10. **Logs** (F §2.5): hymnal, pool size, excluded count, candidate count per slot, resolved count per slot, topped-up count per slot, `nt_source` (`client`, `fetched`, `timeout`, `none`), model, duration and outcome code. Never the prompt, `nt_text` or titles, except prompts at DEBUG.

#### 3.7 OpenAI client specifics for this slice

- Build `integrations/openai_client.py` as F §2.8 specifies, with the refinements below. There is no hymn-specific code in it.
- **Retries (refines F §2.8).** The SDK client is built with `max_retries=0`. The SDK's own retry honors `Retry-After` for up to 60 s between attempts, which would break the 90 s client budget while holding a concurrency slot. `complete()` retries itself, up to `OPENAI_MAX_RETRIES` (1) times, on `APIConnectionError` (this includes `APITimeoutError`), on `RateLimitError` other than `insufficient_quota`, and on `APIStatusError` with status ≥ 500. The wait before a retry is `min(Retry-After or 1 s, 2 s)`, through an injectable `sleep`.
- **Deadline (refines F §2.8).** `complete(messages, *, max_completion_tokens, json_mode=False, deadline: float | None = None)`, where `deadline` is a `time.monotonic()` instant.
  - With a deadline: the semaphore wait is `min(15 s, remaining − 5 s)`, and a slot not acquired in that time → `Busy("ai_busy")`. Each attempt's timeout is `min(OPENAI_TIMEOUT_SECONDS, remaining)`, passed per request with `with_options(timeout=httpx.Timeout(t, connect=min(5, t)))`. A retry starts only when at least 5 s remain after the backoff; otherwise the last attempt's error is mapped as usual.
  - Without a deadline (slice 4 as currently specified) the F §2.8 limits apply unchanged: 15 s semaphore wait and `OPENAI_TIMEOUT_SECONDS` per attempt. The only difference is the 2 s backoff cap.
- **Error mapping**, checked in this order, because subclasses come before their base classes (`APITimeoutError` subclasses `APIConnectionError`; `RateLimitError`, `AuthenticationError`, `PermissionDeniedError` and `BadRequestError` subclass `APIStatusError`):
  1. `APITimeoutError` → `UpstreamTimeout("ai_timeout")`;
  2. `RateLimitError` whose `code` is `"insufficient_quota"` → `NotConfigured("ai_not_configured")`, **not retried**, logged at ERROR as `AI: quota exhausted (insufficient_quota)`. This is what the OpenAI monthly budget cap (§Risks) produces. Mapping it to `ai_busy` ("Try again in a minute") would have members retrying for weeks, with the SDK retrying every call;
  3. any other `RateLimitError` → `Busy("ai_busy")`;
  4. `AuthenticationError`, `PermissionDeniedError` → `NotConfigured("ai_not_configured")` (log ERROR);
  5. `BadRequestError` → `UpstreamError("ai_upstream_error")`;
  6. `APIConnectionError` → `UpstreamError("ai_upstream_error")`;
  7. any other `APIStatusError` → `UpstreamError("ai_upstream_error")`.
- **Startup (lifespan)** logs exactly one of:
  - INFO `AI: configured (model=<name>)`;
  - WARNING `AI: not configured (OPENAI_API_KEY missing)`;
  - WARNING `AI: not configured (OPENAI_MODEL missing)`;
  - ERROR `AI: not configured (OPENAI_API_KEY is not ASCII)`.

  The key is never printed.
- **Worst case on the server** for `POST /hymns/suggestions`: everything from the read phase to the last OpenAI attempt runs inside the 75 s deadline set in §3.6 step 0. Inside it, the NT fetch takes ≤ 10 s, the semaphore wait ≤ 15 s, attempt 1 ≤ 30 s, the backoff ≤ 2 s, and attempt 2 gets whatever remains (at least 5 s, or no retry). Mapping the response afterwards is in memory (< 1 s). The total is about 76 s, which matches F §1.8's "~75 s" and leaves about 14 s under the 90 000 ms client timeout. The concurrency slot is held only for the attempts and the backoff, all inside the deadline.

### 4. Routes

In `api/routes/hymnals.py`:

```python
@router.get("/hymnals", response_model=HymnalListOut)
def list_hymnals(church: ActiveChurch = Depends(require_church)): ...
```

In `api/routes/hymns.py`, each route is a plain `def` that makes one usecase call:

```python
@router.get("/hymns", response_model=Page[HymnOut])
@router.post("/hymns/scripture-matches", response_model=ScriptureMatchesOut)
@router.post("/hymns/suggestions", response_model=HymnSuggestionsOut,
             dependencies=[Depends(rate_limit("ai"))])
```

Every route calls its usecase with `church.id` only (F §1.2 rule 1).

### 5. Streamlit coupling removed (inv §3)

| Inventory §3 row | Result |
|---|---|
| app.py:636-646, 723-725 (`_cached_all_hymns`, Refresh) | Replaced by TanStack queries keyed by church; no error is cached as empty. |
| app.py:648-663, 676-695, 735-746 (hymnal filter, search loop, exclusion filter) | Server-side hymnal filter, `match_hymns`, and `recent_use_on` on every hymn. |
| app.py:753-824, 770-772 (first-pick apply, `_find_key`, "Could not" message classification, `st.progress`, closure over the session translation) | Structured `slots` response, typed HTTP errors, and NT text passed explicitly (`nt_text`) or fetched in WEB. |
| app.py:259-266, 401-404, 847-851 (title-keyed, positional picks) | The draft holds slot-keyed `HymnPick` with ids. The positional readers (liturgy and docx) are fixed in 4 and 5a. |
| ui_helpers.py `hymn_display_from_flat`, `build_title_to_info` | Replaced by `HymnOut` from repos. ui_helpers.py itself stays untouched on `main` (frozen Streamlit; deleted in 7) and nothing is re-exported. |
| worship_service.py:20-21, 287-343, 447-450 (Notion fallback) | Deleted. |
| worship_service.py:406-417, 539-541 (UI-shaped suggestion errors, "Settings → Secrets") | Typed `DomainError`s through `openai_client`. |
| worship_service.py:28, 612-683 (audio resolver and its cache) | Deleted. |

### 6. Tenancy and data access

- All reads filter `Hymn.church_id == church.id` and `HymnUsage.church_id == church.id`.
- The AI candidate list is built on the server from the church's hymnal. It is never accepted from the client (F §2.8).
- Hymn titles and themes are editable by members and appear in the prompt. The output is constrained to candidate tokens and to this church's hymns, so a prompt-injected title can at worst skew that church's own suggestions.
- `nt_text` from the client goes only into that user's prompt, truncated to 1 500 characters, and is never logged.
- No write happens anywhere in this slice.

---

## Data and migrations

- **No schema change and no Alembic revision.** This slice only reads:
  - `hymns`, using `ix_hymns_church_hymnal`, which `0002_reconcile` creates in production in slice 1;
  - `hymn_usage`, using `ix_hymn_usage_church_date`;
  - `churches.settings["default_hymnal"]`, a JSON key that 6a writes and that is absent until then (F §3.5).
- **Compatibility with frozen Streamlit:** nothing is written, so there is nothing to break.
  - Usage rows written by Streamlit's Prepare (ISO `date_iso` from `record_usage`) are read correctly.
  - Streamlit ignores `default_hymnal`, and its settings merge preserves unknown keys (F §6.2).
- **Production data assumption to verify before building the parser.** Nobody has checked the actual `scripture_refs` formats in production. Before implementing §2, the owner runs a read-only query against production and commits the output as `backend/tests/fixtures/hymns/scripture_refs_sample.txt`:

  ```sql
  select distinct scripture_refs from hymn_catalog where coalesce(scripture_refs, '') <> '' order by 1 limit 400;
  ```

  The output is public hymn metadata with no personal data. A test asserts that `parse_refs` parses at least 98 % of the segments in that file.
- **Second read-only check, run at the same time:** the shapes of `hymn_usage.date_iso`, whose Notion-imported rows may not be `YYYY-MM-DD` (§3.4). The counts go in the PR description. `usage_near` tolerates every shape either way; the check only tells us whether the cleanup in 7 has rows to fix.

  ```sql
  select length(coalesce(date_iso, '')) as len, count(*) from hymn_usage group by 1 order by 1;
  ```

---

## Frontend changes

Read `frontend/node_modules/next/dist/docs/` and the installed `@base-ui/react` Combobox docs before coding (F §4). Do not paste Radix snippets.

### Files

```
src/app/(signed-in)/(church)/builder/hymns/page.tsx   replaces slice 2's <StepPlaceholder step="hymns"/>; renders <HymnsStep/>
                                                      (StepPlaceholder stays for liturgy and review; 5a deletes it)
src/components/ui/{combobox,switch,badge,alert}.tsx   generated: npx shadcn@latest add combobox switch badge alert
src/components/app/search-combobox.tsx                generic long-list wrapper over Base UI Combobox (F §4.9.5) for the hymn
                                                      picker; reused as is if slice 1 already built it under TimezoneCombobox.
                                                      The timezone picker is slice 1's TimezoneCombobox (6a reuses that), not
                                                      this component
src/lib/draft/steps.ts                                SHIPPED_STEPS gains "hymns" (slice 2's file)
src/lib/draft/status.ts                               stillNeeded: the three "No {Slot} hymn — Choose one" rows (if slice 2 did
                                                      not already implement them behind the SHIPPED_STEPS filter)
src/components/builder/summary-panel.tsx              Hymns block: three slots from the draft snapshot, or "No {Slot} hymn"
                                                      (replaces "Available soon"; slice 2's file)
src/components/builder/summary-hymns.tsx              the Hymns block component used by SummaryPanel
src/components/builder/hymns/
  hymns-step.tsx            loads queries; composes toolbar, slots, matches, credit; empty/error states
  hymns-toolbar.tsx         hymnal Select, exclude Switch, <SuggestHymnsButton/>
  suggest-hymns-button.tsx  mutation, 8 s "Still working…", Cancel (AbortController), inline Alert
  hymn-slot-card.tsx        pick row / picker, notices, Undo toast (dismissed on unmount), <AlternativeChips/>
  hymn-picker.tsx           SearchCombobox + filterHymns
  alternative-chips.tsx
  scripture-matches.tsx     collapsible section, extra-ref input, grouped results, Add menu
  hymn-label.tsx            "#n Title", hymnal badge, recent badge, ▶ Listen via safeHttpsUrl
src/lib/hymns/
  filter.ts                 filterHymns(items, query, {excludeRecent}) -> {shown ≤50, totalMatches, hiddenRecent}
  picks.ts                  pickFromHymn, reconcilePick, applySuggestions, swapAlternative, setSlot, clearSlot, duplicateSlots
  suggest-request.ts        buildSuggestionRequest(draft, selectedHymnal, getCachedPassage)
  match-request.ts          buildMatchRefs(scriptures, extraRef) -> string[]; shared cleanRefs(list, {max, maxLen})
  hymnal.ts                 selectHymnal(stored, hymnals) -> {code, stale}
  labels.ts                 SLOT_META (titles/captions), recentUseLabel(dateIso, serviceDateIso), notice copy
src/lib/queries/hymns.ts    useHymnals, useHymnList, useHymnLists, useScriptureMatches, useSuggestHymns
src/lib/queries/keys.ts     + hymnList, hymnMatches
src/lib/api/timeouts.ts     hymnSuggestions: 90_000 (if not already present)
src/lib/dates.ts            + formatShortDate(iso) -> "Sep 7" (adds the year when it differs from the service year)
src/lib/features.ts         SETTINGS_HYMNS_READY = false (6a flips it)
```

### Queries (TanStack, church client `api.church`, so every request carries `X-Church-Id`)

| Hook | Key | Request |
|---|---|---|
| `useHymnals()` | `["church", id, "hymnals"]` | `GET /hymnals` |
| `useHymnList(hymnal, recentForDate)` | `["church", id, "hymns", {hymnal, limit: 2000, recent_for_date}]` | `GET /hymns?hymnal=…&limit=2000&recent_for_date=…` |
| `useHymnLists(hymnals[])` | as above, via `useQueries` | For each distinct non-null `pick.hymnal` among the slots plus the selected hymnal (at most 4), so picks from another hymnal can be checked |
| `useScriptureMatches(params)` | `["church", id, "hymns", "matches", {refs, hymnal, recent_for_date}]` | `POST /hymns/scripture-matches`, `max_results: 30`. `refs` always come from `buildMatchRefs` (never the raw draft list), and `hymnal` is the selected hymnal. `enabled` only when refs are non-empty and the hymnal has scripture data. |
| `useSuggestHymns()` | mutation | `POST /hymns/suggestions` with `timeoutMs: 90_000` and `signal` |

- Nesting the matches key under `["church", id, "hymns"]` means 6a's prefix invalidation also refreshes the matches.
- Defaults are F §4.4: `staleTime` 30 s, refetch on focus, one retry for retryable errors only.
- `recent_for_date` is omitted when `draft.readings.date_iso` is not a valid date.

### Draft usage (DraftV1, F §4.6; **no schema change, no version bump**)

| Field | Read | Written |
|---|---|---|
| `readings.date_iso`, `occasion`, `scriptures`, `selected_nt_ref`, `translation` | Request building, recent window, chip freshness | never |
| `hymns.hymnal` | Selected hymnal (`selectHymnal`: the stored code if still present, else `effective_hymnal`) | Hymnal Select only. Never written automatically, even when the stored code has disappeared |
| `hymns.exclude_recent` | Picker, matches, request | Switch |
| `hymns.slots[slot]` | Slot cards | Picker select, chip swap, match "Add", ✕, Undo, `applySuggestions` |
| `hymns.alternatives` | Chips (only when `for_date_iso === readings.date_iso`) | `applySuggestions`, chip swap |

- Every write goes through `update(recipe)` as a functional update of the latest draft.
- `exclude_recent` and `alternatives` are not part of `ServiceDraft`, so changing them never marks the draft dirty.
- Changing `slots` or `hymnal` does mark it dirty, which is correct because both are archived in 5a. Only user actions change them.

### Pure-function contracts (`src/lib/hymns/picks.ts`)

- `pickFromHymn(h: HymnOut): HymnPick` → `{hymn_id: h.id, title: h.title, number: h.number, hymnal: h.hymnal}`.
- `reconcilePick(pick, lists: Map<hymnal, HymnOut[] | undefined>)` returns one of:
  - `{status: "ok", live: HymnOut}`;
  - `{status: "loading"}` when that hymnal's list is not loaded yet;
  - `{status: "missing"}` when `hymn_id` is null or not found.
- `applySuggestions(hymns, resp, dateIso)`:
  - an empty slot gets `pickFromHymn(resp.slots[s][0])`, and its chips are `resp.slots[s].slice(1, 5)` (2–4, since the server returns at least 3 when it can);
  - a filled slot keeps its pick, and its chips are `resp.slots[s].filter(h => h.id !== current.hymn_id).slice(0, 4)` (3–4 by the same guarantee);
  - `alternatives = {for_date_iso: dateIso, by_slot}`.
- `swapAlternative(hymns, slot, hymnId)`:
  - the slot takes that chip;
  - the chip's position takes the previous pick, when there was one and it is not already a chip.
  - Swapping twice restores the original state.
- `duplicateSlots(slots)` → a map from each slot to the other slots holding the same `hymn_id`.
- `selectHymnal(stored, hymnals)` (`hymnal.ts`), called only with a successfully loaded `HymnalListOut` → `{code: stored, stale: false}` when `stored` is among `items`; `{code: effective_hymnal, stale: false}` when `stored` is null; `{code: effective_hymnal, stale: true}` otherwise.

### `buildMatchRefs(scriptures, extraRef)` (`match-request.ts`)

- `cleanRefs(list, {max: 20, maxLen: 200})`: trim each item, drop blanks, cut each to 200 characters, keep the first `max`. These are exactly the `ScriptureMatchIn.refs` limits, so the request can never 422 on size.
- The result is the cleaned draft scriptures (at most 19 when an extra reference is present, else 20), then the cleaned extra reference, without an exact duplicate.

### `buildSuggestionRequest(draft, selectedHymnal, getCachedPassage)`

- `scriptures`: `cleanRefs(draft.readings.scriptures, {max: 20, maxLen: 200})`.
- `occasion`: trimmed and cut to 300 characters.
- `selected_nt_ref`: `draft.readings.selected_nt_ref`, trimmed and cut to 200 characters; empty is sent as `null`. Without it the server would always use the classifier fallback and ignore the user's step-1 choice.
- `hymnal`: `selectedHymnal` (the `selectHymnal` result, never a vanished stored code), always sent explicitly.
- `nt_text`: sent only when **all** of these hold:
  1. `selected_nt_ref` is set;
  2. the effective translation (`draft.readings.translation ?? church.effective_translation`) is not `"esv"`;
  3. `passageText(queryClient.getQueryData(["passage", translation, ref]))` is non-null, where `ref` is the draft's `selected_nt_ref` exactly as stored (the string slice 2 keyed the query with).

  It is cut to 20 000 characters. The step never triggers a passage fetch.
- `current_picks`: the slots' `hymn_id`s.
- `exclude_recent`: `draft.hymns.exclude_recent`.
- `service_date_iso`: `draft.readings.date_iso`.

### Stale and cross-church protection

- `useSuggestHymns` records the request's `church_id` and `service_date_iso`.
- `onSuccess` applies the result only if the component is still mounted for the same church (the keyed remount unmounts it) and `draft.readings.date_iso` still equals the request date. Otherwise it shows the "date changed" message and does not touch the draft.
- Undo toasts are dismissed on unmount and check the captured church id (§User experience "Slot cards").
- The client uses `createLatestTracker` (`src/lib/latest.ts`), so an older response never overwrites a newer one.

### Builder shell

Slice 2's hand-off table assigns this to slice 3 (F §4.7); the copy is in §User experience "Builder shell: Hymns status and summary".
- `lib/draft/steps.ts`: `SHIPPED_STEPS = new Set(["readings", "hymns"])`. Slice 4 adds `"liturgy"`, and 5a adds `"review"`.
- `lib/draft/status.ts`: no new rule for hymns status (F §4.7's "complete when all three slots are filled" is slice 2's `stepStatus`); `stillNeeded` gets the three hymn rows if slice 2 left them out.
- `SummaryPanel`: the Hymns block becomes `<SummaryHymns/>`, which reads `draft.hymns.slots` only and renders the three rows. The Liturgy block and the status line are untouched (slices 4 and 5a).
- `StepPlaceholder` is no longer used by `/builder/hymns`; it stays for liturgy and review, and 5a deletes it.

---

## Behavior changes vs Streamlit

1. **Picks are hymn ids per slot.**
   - Before: lower-cased title keys, compacted by position.
   - Now: titles that appear more than once can each be picked (inv D1: 34 PH1990 hymns could not be picked).
   - Switching hymnals no longer silently rebinds a pick to the other hymnal's number (inv D2). Picks keep their hymnal and show a badge.
2. **Picker.** A searchable Combobox by number or title, labelled "#n Title". It was a dropdown of titles with no numbers.
3. **Exclude recent:**
   - default **on** (was off);
   - window from 12 weeks before to 12 weeks after the **service date**, excluding that date (was UTC today minus 12 weeks, with no upper bound, including the draft's own date);
   - never clears or resets a pick, and shows a notice instead (fixes the confirmed Prepare-then-lose-picks bug, inv D5);
   - applies to AI candidates, and match results hide or mark recent hymns (both ignored the flag before);
   - stored in the draft.
4. **AI fills only empty slots** with the top pick and shows 2–4 alternative chips per slot (owner decision 3). "Only empty slots" is this spec's interpretation of "fill each slot". It is put to the owner before 3b starts and the answer is recorded in F's decisions table (Open question 2); an "overwrite every slot" answer changes this item.
   - Before: all three slots were overwritten with the first pick and the other four suggestions were thrown away.
   - Slots the user already chose keep their pick and gain chips.
   - Top picks are distinct across slots and never duplicate another slot's current pick. Other slots' picks are removed from a slot's candidates before the AI sees them.
   - The minimum of a top pick plus 2 alternatives is guaranteed on the server by topping up from the slot's own candidate list when the AI returns too few usable hymns.
5. **AI errors are specific:**
   - Before: every failure (no key, upstream error, bad JSON) showed "AI could not match…".
   - Now: `ai_not_configured` / `ai_busy` / `ai_timeout` / `ai_upstream_error` with fixed copy. An exhausted OpenAI quota reads as "not set up", not "busy".
   - Members never see configuration details (the non-ASCII key text is logged only).
   - OpenAI timeout is 30 s with 1 retry and a backoff capped at 2 s, all inside a 75 s server deadline (was the SDK default of about 600 s with 2 retries).
   - A spinner with Cancel replaces the fake step-by-step progress bar.
   - `temperature` 0.3 is no longer sent unless `OPENAI_TEMPERATURE` is set.
   - The model no longer defaults to `gpt-3.5-turbo`; `OPENAI_MODEL` is required.
6. **AI results resolve by candidate token.** A non-token answer counts only on an exact title match. Before, a fuzzy substring match could pick the wrong hymn (inv D7).
7. **AI candidates:**
   - when themes or scripture data are sparse, lists are padded with an even sample across the hymnal (before: the first 80 hymns, which for PH1990 are all Advent hymns); over-long theme lists are also sampled evenly rather than cut at low numbers;
   - response candidates put the NT reading's matches first;
   - recently used hymns are left out when exclusion is on;
   - one catalogue lists each hymn once, and the prompt is capped at 24 000 characters.
8. **NT context for AI:**
   - the client's already-loaded passage text is used, but never ESV;
   - otherwise the server fetches WEB for the selected NT reading, or for the classifier's NT fallback.
   - Before: the session translation, including ESV, was used, and the fallback only looked at `' or '` references already in the cache.
   - Reason: Crossway's ESV terms, and WEB is cacheable.
9. **Scripture matching is tightened** (owner decision 9):
   - references are parsed by book, chapter and verse;
   - abbreviations work in both directions, `Psalm`/`Psalms` are equivalent, `;` and `,` lists carry the book forward, and the `' or '` split ignores case;
   - RCL deuterocanonical readings (Baruch, Wisdom, Sirach, …) parse and match instead of being reported as unreadable;
   - results are tiered "Matches the readings" / "Same chapter";
   - the four over-matches in inv §0 item 5 no longer match;
   - unreadable references are reported.
10. **Scripture matches:**
    - run automatically from the draft's readings (before: a button, with stale results that stayed on screen);
    - are limited to the selected hymnal and keyed by it, so they reset when the hymnal changes;
    - can be added to a slot (before: read-only);
    - with no references, a link to step 1 replaces the info message.
11. **Hymnal default.** The church's `default_hymnal` setting, falling back to the alphabetically first hymnal (parity). Before: always alphabetical, per session. The draft keeps the chosen hymnal; before, it was not saved.
12. **No "Refresh hymn list" button.**
    - The list refetches on focus and after Settings changes (6a invalidation).
    - A load failure shows Retry and is never cached as an empty hymnal (inv D1).
    - The raw exception text ("Could not load hymns: {e}") is no longer shown.
13. **Rendering is safe.** Titles and links render as React text. Hymnary links render only when https, with one "▶ Listen" link in place of two duplicate links (inv D3, D8).
14. **Dead code removed.** `audio_url` is no longer exposed, and the audio resolver and Notion search path are gone.
15. **The same hymn in two slots** is still allowed, now with an "Also chosen as…" notice.
16. **Blank-title hymns** are excluded from the picker, the matches and AI. Before, matches and AI could show them as "Unknown".
17. **Ordering.** NULL-number hymns sort last on both SQLite and Postgres (before: first on SQLite, last on Postgres).
18. **Themes** stored as Postgres array literals (`{A,"B"}`) are normalized for display and matching. The data itself is cleaned up in 7.
19. **Hymnals without scripture data** get an explicit note (PH1990 has no scripture references).

Unchanged on purpose:
- empty-hymnal message wording (adapted for the link);
- the Hymnary credit caption;
- the slot captions;
- free-text hymns stay removed (owner decision 9);
- the usage key stays `(number, title)`, with no hymnal dimension (see Risks).

---

## Testing

All backend tests are network-free (F §5.1 autouse guard). AI goes through `FakeAI`; the NT fetch is an injected fake.

### Backend (pytest)

**Characterization first (F §2.3.1).** Before deleting `hymns_by_scripture`, add `test_hymn_match_parity.py`. It holds a table of (query, hymn refs) pairs that match today and must still match with `match_hymns`: exact reference, book + chapter, first verse, a/b suffix, and the `or` alternative. Run it against both implementations in the PR that introduces `match_hymns`. The four over-match pairs are asserted **not** to match under `match_hymns`; these tests are written first and fail against the old code. The old function and its half of the parity test are deleted in the same PR.

| File | Cases |
|---|---|
| `test_scripture_refs_parse.py` | Every `BOOKS` alias maps to its canonical book; ordinals `1`/`I`/`First`/`1st` and no-space forms; `Ps`/`Pss`/`Psalms`; ranges, cross-chapter ranges, a–d suffixes, `ff`; `;` carry-forward; `,` as a verse list versus a new book; single-chapter books; en dash; case-insensitive `or`; whole-book references; garbage goes to `unparsed`. Deuterocanon: `Baruch 5:1-9`, `Bar 5:5`, `Wisdom of Solomon 1:13-15; 2:23-24`, `Wis 2:23`, `Sirach 10:12-18`, `Sir 27:4-7`, `Ecclesiasticus 27:4`, `Tobit 8:5-8`, `Judith 9:11`, `1 Macc 2:1`, `2 Maccabees 7:1`, `Song of the Three 35-65` (single chapter, verses) all parse with no `unparsed` entry; the longest alias wins, so `Song 2:8-13` stays Song of Songs; `classify` returns `"ot"` for each (slice 2's `scripture_refs.json` still passes). The production sample file parses ≥ 98 % of segments. |
| `test_hymn_search.py` | The required-results table (§2); tier ordering; `limit_per_ref`; `max_results`; `total_matched`; dedupe across refs; `matched_refs`; the unparsed hymn-text fallback never hits `Psalm 119` for `Psalm 1` or `1 John 3` for `John 3`; blank titles and blank refs skipped; `parse_themes` for None, list, `{A,"B c"}`, comma and semicolon strings; `normalize_title`; `evenly_spaced` is deterministic and in range; `hymn_search` never imports FastAPI. |
| `test_hymn_suggest.py` | `build_candidates`: theme word-start matching (`joy` matches `joyful`, not `enjoy`), padding to 40 when fewer than 15, response from passage tier then chapter tier, cap of 50. **NT first:** with four references (OT, Psalm, Epistle, Gospel = `nt_ref`) and more than 50 OT and Psalm matches, the Gospel's passage matches lead the response list and survive the cap. **Theme sampling:** a theme list of 120 hymns is reduced by `evenly_spaced` to 50 that include hymns from the last third of the hymnal, not the first 50 by number. **Other slots' picks:** the response pick's id is absent from the opening and closing lists (and from their `* CANDIDATES` lines in the prompt) and present in the response list. `build_prompt`: at most 24 000 characters with a 2 000-hymn pool of long titles, trimming is deterministic, every token in a slot list is in the catalogue, the instruction asks for exactly 5 ids per slot. `parse_suggestion_json`: plain JSON, fenced JSON, invalid JSON / non-dict / non-list → `UpstreamError`. `resolve_suggestions`: tokens, lowercase tokens, unknown tokens dropped, exact-title fallback, "Holy" does **not** resolve to "Holy, Holy, Holy", title collisions prefer the slot's candidates, nothing resolved in any slot → `UpstreamError`. `finalize_slots`: distinct top picks, another slot's current pick excluded, another slot's top pick never an alternative, own pick kept, cap of 5. **Minimum count:** the AI returns 1 id per slot → each empty slot ends with 3 hymns (1 `ai` + 2 `candidates`, in candidate order); the AI returns the same 5 ids for all three slots → opening keeps them and response and closing are topped up to 3 from their own candidates with no id repeated across slots; a filled slot ends with at least 3 hymns other than its own pick; a pool of 4 eligible hymns ends below the minimum without error. |
| `test_openai_client.py` | No key, key without model, and non-ASCII key → `ai_available()` false plus the startup log line. **Error mapping for all seven SDK error classes** (constructed fakes): `APITimeoutError` → `ai_timeout` (an ordering test: it must not come back as `ai_upstream_error` through its `APIConnectionError` base), `RateLimitError` → `ai_busy`, `AuthenticationError` and `PermissionDeniedError` → `ai_not_configured`, `BadRequestError`, `APIConnectionError` and a 500 `APIStatusError` → `ai_upstream_error`. `RateLimitError` with `code="insufficient_quota"` → `ai_not_configured`, one attempt only, ERROR log. **Retries:** the SDK client is built with `max_retries=0`; a 500 then success → one retry and success; a 429 with `Retry-After: 60` → the injected `sleep` is called with 2; a `BadRequestError` is not retried. **Deadline** (injected clock): the per-attempt timeout shrinks to the remaining time; with 4 s left after a failed attempt there is no retry; a semaphore that stays full until the deadline minus 5 s → `ai_busy`. `max_completion_tokens` always sent. `json_mode` sets `response_format`. `temperature` sent only when set. The installed SDK's `chat.completions.create` signature has `max_completion_tokens` (guards the `openai>=1.45.0` pin). The semaphore raises `Busy("ai_busy")` after the wait (tiny injected wait). |
| `test_hymn_usage_window.py` | D−84 and D+84 included; D−85 and D+85 excluded; D itself excluded; nearest date chosen, with ties going to the earlier date; NULL numbers match NULL; title whitespace and case tolerated; church-scoped; NULL `date_iso` ignored. **Stored shapes:** `""` ignored; `2026-08-02T10:00:00.000-05:00` inside the window counts as 2026-08-02; the same shape on D+84 is included and on D itself is excluded; a malformed `2026-8-2` is skipped (DEBUG count) and nothing raises; `GET /hymns?recent_for_date=` with such rows returns 200. |
| `test_api_hymnals.py` | Counts and `scripture_ref_count`; `effective_hymnal` when stored is valid, when stored is missing from the hymnals (alphabetical fallback), when stored is not a string or blank, and with no hymns (null). `GET /church` returns the same two values. |
| `test_api_hymns.py` | Ordering (hymnal, number with nulls last, title, id); `hymnal` filter; `q` by number and by title, with `%` and `_` escaped; a 30-digit `q` → 200 via the title-only branch (no `OverflowError` on SQLite); a 6-digit `q` still uses the number branch; `limit=2000` accepted and `2001` → 422 with `fields`; `offset`; `total`; `recent_for_date` sets `recent_use_on` and omitting it gives null; blank titles returned; `themes` normalized; **`HymnOut` mapping** (one named test, the port-ledger target for `hymn_display_from_flat`): title stripped, NULL title → `""`, `link` returned verbatim, NULL number stays null; a stored hymnal code that breaks the `HymnalCode` pattern is listed by `GET /hymns?hymnal=` like any other. |
| `test_api_hymn_matches.py` | Happy path grouped by strength; refs that are blank after trim → 422 with the exact message and `fields.refs`; unknown hymnal → 422 with the exact message; `unparsed_refs`; `recent_use_on`; an empty church hymnal → 200 with empty items. |
| `test_api_hymn_suggestions.py` | Happy path (FakeAI returns tokens) → slots of at most 5, distinct tops. `ai_not_configured` 503, `ai_timeout` 504, `ai_busy` 503, `ai_upstream_error` 502 for SDK errors and for invalid JSON, each asserting code and exact message. With `nt_text` supplied the fetcher is not called. Without it, the fetcher is called with `(selected_nt_ref, "web")`, or with the `default_nt_ref` fallback. Fetcher failure is tolerated (`nt_text_used` false). **NT budget:** a fetcher that blocks on a `threading.Event`, with `NT_FETCH_BUDGET_S` patched to 0.05 → 200 with `nt_text_used: false`, FakeAI still called, and the request finishes in under 1 s. **Deadline:** FakeAI records the `deadline` it receives, and it is no later than entry + `SUGGEST_BUDGET_S`. **Minimum count through the route:** FakeAI returns one token per slot → each empty slot has 3 hymns, the added ones with `source: "candidates"`. **NT first:** with `selected_nt_ref` set, the captured prompt's RESPONSE CANDIDATES start with that reading's matches. `exclude_recent` true: no recent hymn appears in the captured prompt or the response, and `excluded_recent_count` is correct. The service date's own usage does not exclude. `exclude_recent` false: recent hymns may appear, with `recent_use_on` set. Empty pool → 422. All excluded → 422 with the exact message. Extra body field → 422 (`extra="forbid"`). `occasion` longer than 300 → 422. |
| Isolation and roles (all four routes, `assert_church_isolated` with its 403 half only) | A non-member gets 403 on each route. The 404 half (`resource_path_b`) is not used: no slice-3 route resolves a path or body id, and `current_picks` is the declared exception in §API notes. A member of A never sees B's hymns in `GET /hymns`, the matches, the captured suggestion prompt or the response. B's hymnal code in A's request → 422, with the same message as a nonexistent code. B's hymn id in `current_picks` → 200 (not 404); it matches nothing in A's pool and is never echoed. Usage recorded in B does not mark A's hymns. Members, admins and owners all get 200. |
| Rate limit | The 41st suggestion call in 10 min by one user → 429 `rate_limited` with `Retry-After`. The 401st call in a day across users of one church → 429. Another church is unaffected. The clock is injected. |
| Contract and guards | `test_schemas.py` covers `HymnRef`, `SlotHymns` and `SectionKey` against the F §1.3 frozen shape, including a non-pattern `hymnal` code accepted (§API notes). `test_route_guards.py` passes with no allowlist change. `test_openapi_contract.py` passes with the regenerated snapshot. `test_no_streamlit_in_core.py` imports `api.main` with the new routers. |
| GZip | `GET /hymns?limit=2000` with `Accept-Encoding: gzip` and an allowed `Origin` → `content-encoding: gzip`, plus `access-control-allow-origin` and `x-request-id`. The ops middleware-order test is updated to CORS, RequestId, UnhandledError, GZip (outermost first) and passes. |
| `@pytest.mark.postgres` | `GET /hymns` ordering with NULL numbers and the `q` ILIKE escaping on Postgres; `usage_near` string-date range on Postgres, including a datetime-shaped `date_iso`. |

The `streamlit_tests/` assertions on `hymn_display_from_flat`, `build_title_to_info` and `coerce_selectbox_value` test Streamlit-only helpers that this slice does not modify or move: `hymn_display_from_flat` is **replaced** by `HymnOut`, not moved to the backend. Their intent (trimmed titles, blank titles skipped, stale picks never crash) is covered here by the `HymnOut` mapping test in `test_api_hymns.py` (title stripped, NULL title → `""`, link verbatim, themes normalized), the `filterHymns` tests ("blank titles never listed", "same title stays distinct by id") and the `reconcilePick` "missing" status. 6b's port ledger (`test_streamlit_port_ledger.py`) maps them as follows, and the files are deleted in 7:

| Streamlit test | Ledger target in this slice |
|---|---|
| `test_app_helpers.py::test_hymn_display_from_flat_*` | `test_api_hymns.py` `HymnOut` mapping test, plus `lib/hymns/filter.test.ts` ("blank titles never listed", "same title stays distinct by id") |
| `test_app_helpers.py::test_build_title_to_info_*` | `filter.test.ts` "blank titles never listed" and the `hymns-step.test.tsx` empty-hymnal case; the title-keyed map is DROPPED (picks by id) |
| `test_selectbox_safety.py` (stale pick half) | `picks.test.ts` `reconcilePick` "missing" and the `hymns-step.test.tsx` "Not in your hymnal" case |
| the ops D5 tests in `test_app_helpers.py` (`hymn_options_excluding_recent` and its regression test) | `DROPPED: Streamlit-only fix; intent covered by slice 3 test that exclusion never clears a pick (hymns-step DOM test, AC 12)`. The DOM test's title contains "exclusion never clears a pick". |

### Frontend (Vitest)

| Project / file | Cases |
|---|---|
| unit `lib/hymns/filter.test.ts` | An exact number ranks before a prefix, and a prefix before a title containing the digits; starts-with, then word-start, then contains; accent- and case-insensitive; at most 50 shown with the correct `totalMatches`; "blank titles never listed"; "same title stays distinct by id" (two hymns with the same title; these two titles are port-ledger targets); `excludeRecent` hides them and counts `hiddenRecent`. |
| unit `lib/hymns/picks.test.ts` | `applySuggestions` fills only empty slots, gives filled slots chips without their own pick, caps chips at 4, and sets `for_date_iso`. **At least 2 chips:** a 3-hymn server list for an empty slot gives a pick plus 2 chips; a 3-hymn list for a filled slot (own pick not in it) gives 3 chips. `selectHymnal`: present, null and vanished (stale) codes. `swapAlternative` swaps symmetrically and doesn't duplicate chips. `reconcilePick` returns ok, loading and missing (null id, id not found). `duplicateSlots`. |
| unit `lib/hymns/suggest-request.test.ts` | `nt_text` is sent only with a selected NT ref, a non-ESV translation and cached text (read through `passageText`); scriptures are trimmed and capped; **`selected_nt_ref` is sent trimmed, cut to 200, and `""` or whitespace becomes `null`**; the hymnal is the selected one, never a vanished stored code; `current_picks` is mapped. |
| unit `lib/hymns/match-request.test.ts` | `buildMatchRefs`: trims, drops blanks, cuts a 500-character line to 200, keeps at most 20, keeps the extra reference when the draft has 25 scriptures, and drops an exact duplicate of the extra reference. |
| unit `lib/hymns/labels.test.ts`, `lib/dates.test.ts` | "Used on…" versus "Also planned for…"; `formatShortDate` year handling; no `new Date("YYYY-MM-DD")` (the F §4.10 guard test still passes). |
| unit `lib/draft/status.test.ts` (slice 2's file, extended) | `SHIPPED_STEPS` contains `"hymns"`; hymns `stepStatus` is `incomplete` "0 of 3" for a fresh draft, "2 of 3" with two slots filled, and `complete` with all three (a `hymn_id: null` pick counts as filled); `stillNeeded` lists "No Opening hymn — Choose one" (and Response, Closing) for empty slots, linking to `/builder/hymns`, and none when all three are filled; still no liturgy rows (liturgy not shipped). |
| dom `components/app/search-combobox.test.tsx` | Opens on click; renders at most 50 with the hints; shows the empty and hidden footers; keyboard selection. |
| dom `components/builder/summary-panel.test.tsx` (slice 2's file, extended) | **Hymns step shows its status and the summary no longer says "Available soon" for hymns:** with a draft holding an Opening and a Closing pick, `StepProgress` shows "2 of 3" on the Hymns item (not "Soon"), and after filling Response it shows ✓; the `SummaryPanel` Hymns block shows "#403 Come, Thou Almighty King" for Opening and "No Response hymn" for the empty slot, and its text does not contain "Available soon"; the Liturgy block still reads "Available soon" (until slice 4). Rendered at 375 px (bottom sheet) and at `lg` (column). |
| dom `components/builder/hymns/hymns-step.test.tsx` | See the list after this table. |

`hymns-step.test.tsx` runs against `installFakeApi` and `renderWithProviders` and covers:
- picks render from the draft before the list loads;
- choosing a hymn in the picker writes a `HymnPick` to localStorage under `wsb:draft:{user}:{church}`;
- **exclusion never clears a pick** (AC 12; the port ledger's target for the ops D5 tests): the exclude switch hides a recent hymn from the options, shows "{n} hymns are hidden.", and leaves a recent pick in place with its notice, with `draft.hymns.slots` unchanged after toggling on and off;
- a missing pick shows "Not in your hymnal. Choose a replacement.";
- an empty hymnal shows the `EmptyState` copy;
- a list error shows `ErrorState` and Retry refetches;
- the hymnal Select changes the list request and keeps the picks;
- Suggest success fills empty slots and adds chips; a chip tap swaps; chips are hidden after the draft date changes;
- Suggest `ai_not_configured` shows the inline copy;
- Cancel aborts (the recorded request's signal is aborted) and the button returns to idle;
- the matches auto-request uses the draft scriptures; "Add → Response hymn" sets the slot; the Undo toast restores the previous pick;
- after Suggest, each slot card renders at least 2 chips when the fake server returns 3 hymns per slot;
- **date change while pending:** the draft date changes before the suggestion resolves → "The date changed while suggestions were loading. Try again." and the draft's slots and `alternatives` are unchanged;
- **pick during the wait:** the user fills the response slot while the request is pending → on success that pick is kept and the slot gets chips;
- **vanished hymnal:** a draft whose `hymns.hymnal` is not in the loaded `GET /hymnals` list → the stale note shows, the list request uses `effective_hymnal`, and the stored draft is unchanged (no write, not dirty); while `GET /hymnals` is pending or failed, nothing is written either;
- **unreadable reference:** a matches response with `unparsed_refs: ["Transfiguration"]` shows "Couldn't read “Transfiguration” as a scripture reference.";
- **Undo after a church switch:** show the ✕ Undo toast, switch church (remount) → the toast is dismissed, and invoking the captured Undo handler leaves church B's draft unchanged;
- every request carries `X-Church-Id`.

### Manual checks (appended to `docs/manual-verification.md`, F §5.5)

Run on the production Vercel URL, at 375 px (iPhone SE in device mode) and on desktop:
1. Open Hymns with readings for a real Sunday. Matches appear, grouped. "Add → Opening hymn" works.
2. Search by number ("403") and by partial title. Two hymns with the same title are both selectable and show different numbers.
3. Turn exclusion on and off. A recently used pick stays, with its notice. The hidden count changes.
4. Suggest: empty slots fill and every slot shows at least 2 chips. Tap a chip and tap back. Pick a slot manually, suggest again, and the manual pick stays.
5. Tap Cancel during a suggestion. Suggest 41 times quickly (or lower the limit in a local run) and see the 429 copy.
6. In a church with 2 hymnals: switch hymnals, and the picks keep their badges. For PH1990, the no-scripture note shows.
7. Refresh the page mid-step: picks, chips and the switch state survive. Switch church and back: each church keeps its own draft. The progress bar shows "n of 3" (then ✓) for Hymns, and the summary (bottom sheet at 375 px, right column on desktop) lists the three hymns or "No {Slot} hymn", with no "Available soon" in its Hymns block.
8. The 375 px layout has no horizontal scroll, the chips wrap, the Combobox list is usable with the keyboard open, and the sticky footer does not cover the last card.
9. Regression pass: sign in, switch church, and open every shipped nav item. Streamlit smoke check: load the church, load an archived service, open Settings (F §6.3).

---

## Acceptance criteria

1. `GET /hymnals`, `GET /hymns`, `POST /hymns/scripture-matches` and `POST /hymns/suggestions` exist, depend on `require_church`, match the models in §API, and appear in the committed OpenAPI snapshot and the generated `schema.d.ts`. `test_route_guards.py` passes with no allowlist change.
2. `GET /church` returns `default_hymnal` and `effective_hymnal`, and they equal the same fields from `GET /hymnals` for the same church.
3. Every case in the §2 required-results table passes, and `parse_refs` parses at least 98 % of the committed production sample.
4. With `exclude_recent: true`, no hymn whose usage falls in [D−84, D+84] minus {D} appears in the suggestion prompt or response, and usage on D itself excludes nothing. *(test)*
5. Every OpenAI call goes through `openai_client.complete`, with `max_completion_tokens` and `json_mode`, and `FakeAI` tests cover success, timeout, busy, not configured, upstream error and invalid JSON (F acceptance 14). The seven SDK error classes and `insufficient_quota` map as in §3.7, in that order, and `backend/requirements.txt` pins `openai>=1.45.0`. No test opens a network socket.
6. Each AI and validation error returns the exact code and message in §API. No response body contains OpenAI error text or configuration detail. *(test)*
7. The 41st suggestion request by one user within 10 minutes returns 429 with `Retry-After`. *(test)*
8. A member of church A cannot see or influence church B's hymns, usage or hymnals through any of the four routes (isolation tests pass).
9. `grep` finds no `hymns_by_scripture`, `suggest_hymns_for_service`, `hymn_display_info`, `_hymnary_audio`, `resolve_hymnary_audio_url` or `NotionHymnsDB` under `backend/`, and no `load_dotenv` in `worship_service.py`. `lxml` is gone from `backend/requirements.txt`. The contingency wrappers are the only exception, if F §6.1.6 applies.
10. On production, `/builder/hymns` replaces the slice 2 placeholder. `"hymns"` is in `SHIPPED_STEPS`, so `StepProgress` shows "n of 3" for Hymns instead of "Soon". A member can fill all three slots by number or title search at 375 px, and the step then shows complete ("✓") in `StepProgress`. The `SummaryPanel` Hymns block lists the three slots ("#number title" or "No {Slot} hymn") and never reads "Available soon", and Review's "Still needed" lists each empty slot. *(test + deployed)*
11. (As written for "empty slots only"; it changes if the owner's answer to Open question 2, recorded in F's decisions table before 3b, is "overwrite every slot".) Tapping Suggest fills only empty slots with distinct top picks and shows **2–4 chips per slot** whenever the slot's candidate list holds at least 3 eligible hymns, even when the AI returns fewer usable ids (server top-up, §3.6 step 9). A chip tap swaps symmetrically. The chips disappear when the service date changes. *(test + deployed)*
12. Toggling exclusion never changes `draft.hymns.slots`. A recently used pick shows its dated notice. *(test)*
13. A pick whose hymn was deleted, or whose `hymn_id` is null, shows "Not in your hymnal. Choose a replacement." and does not crash or silently disappear. *(test)*
14. Hymn load failure shows Retry, not the empty-hymnal message, and an empty hymnal shows the empty-hymnal state. *(test)*
15. Railway has `OPENAI_API_KEY` (a key separate from the Streamlit one) and `OPENAI_MODEL`, and the startup log shows `AI: configured (model=…)` with no key material. *(deployed)*
16. `GET /hymns?limit=2000` is gzip-encoded for clients that accept it, and still carries the CORS and request-id headers. *(test)*
17. The manual checklist passes on production at 375 px and on desktop, and the post-merge Streamlit smoke check passes. *(deployed)*
18. `POST /hymns/suggestions` finishes within its 75 s server deadline even when the NT fetch hangs or OpenAI asks for a long `Retry-After`, so it always answers before the 90 s client timeout. *(test)*

---

## Risks and open questions

**Risks (with mitigations):**
- **Unknown `scripture_refs` formats in production.** Parser recall could drop silently. Mitigations: sample export plus the 98 % parse test before implementation (§Data), the boundary-aware text fallback for unparsed segments, and logging of the unparsed count per request at DEBUG.
- **Model choice and cost.** `OPENAI_MODEL` must support `response_format: json_object` and `max_completion_tokens`. A reasoning model can spend the 1 200-token budget on reasoning and return empty content, which becomes `ai_upstream_error`. Mitigations: pick a non-reasoning, inexpensive chat model; use a separate Railway key; set a monthly budget cap in the OpenAI dashboard. Together with the `ai` bucket, this bounds cost exposure. When the cap is reached, OpenAI returns 429 `insufficient_quota`, which maps to `ai_not_configured` with an ERROR log (§3.7), so members see "not set up" rather than "busy", and nothing retries.
- **Candidate top-up quality.** When the AI returns fewer than 3 usable hymns for a slot, the extra alternatives come from the server's own candidate order (scripture matches for response, theme matches for opening and closing, then the even sample). These are reasonable but not AI-ranked. They carry `source: "candidates"` and are counted in the logs, so a model that often under-answers is visible.
- **Payload size.** One hymnal of about 850 rows is about 200 KB uncompressed and about 35 KB gzipped, refetched when stale on focus. If mobile data use becomes a complaint, raise `staleTime` for the hymn-list key (hymn edits already invalidate it).
- **Rate limiter dependency.** If slice 2's limiter has no church-keyed buckets, this slice extends it (§1). The `ai` bucket is shared with slice 4, so heavy liturgy use can block suggestions for the rest of the window, as intended.
- **Parallel slice naming.** The slice 2 interfaces (`useDraft`, `default_nt_ref`, `get_passage_text`, `ChurchProfileOut`) are assumed as written. If slice 2 lands with other names, adapt at implementation. The behavior contracts in "Interfaces with other slices" are what matter.

**Open questions:**
1. **Recent use across hymnals.** Usage is matched on `(number, normalized title)`, as today, so a hymn sung from GG2013 is not flagged when the same text is picked from PH1990 under a different number. Should the match use the normalized title alone, with more matches but occasional false positives for different hymns with the same title? This spec keeps the current key until the owner decides. It is a one-line change in `usage_key`.
2. **"Fill each slot" versus "fill each empty slot" (decision 3).** Decision 3 says "fill each slot with the top pick". This spec reads that as "fill each *empty* slot": a hymn the user already chose is never overwritten, and a filled slot gains 3–4 chips instead, so the AI's top pick is one tap away. This is an interpretation, not a confirmed decision.
   - **When it is decided:** the question is put to the owner **before 3b starts** (together with slice 4's question on Generate for custom elements, which must be answered before 4b). The answer is recorded in F's decisions table, and this spec follows that entry.
   - **If the answer is "overwrite every slot",** the change is small and lands in 3b: `applySuggestions` takes `[0]` for every slot and puts the previous pick first among the chips; the server's `finalize_slots` stops treating current picks as reserved for their own slot (a small backend change shipped with 3b, with its `test_hymn_suggest.py` cases updated); and AC 11, Behavior change 4, the toolbar helper "Fills empty slots…" and the `picks.test.ts` / `hymns-step.test.tsx` cases change with it.
   - **If the answer is "empty slots only", or before it arrives,** 3a builds `finalize_slots` as specified here, and nothing changes.
