# Slice 2 — Service Builder shell + Date & readings step — Design

**Status:** Draft  **Depends on:** ops, slice 1 (1a platform, 1b onboarding)  **Size:** L. Ship as three PRs, in this order:
- **2a** backend: outbound HTTP client, TTL cache, rate limiter, `scripture_refs.py`, lectionary and passage refactors, the four API changes.
- **2b** frontend foundation: `lib/dates.ts`, `lib/scripture-refs.ts`, the draft store, the builder shell with all four step routes, `/` → `/builder`.
- **2c** the Date & readings step UI.

2a deploys first; every change is additive (foundations §1.11).

**Inputs**
- Inventory (cited as "inv."): §1 C1–C10; A7 (the readings and translation part); the §2.2 rows for `/lectionary/readings`, `/translations`, `/scripture/passages` and `/church`; §3 rows app.py:69-102, 371-377, 428-464, 481-489, 556-597 and vanderbilt_lectionary.py:22; §4 "Time and date" and "External APIs"; §5 row 2; §7 questions 1, 6 and 14.
- Foundations (cited as "F"): §1.2, §1.5, §1.8, §2.2, §2.3, §2.7, §4.4–§4.10, §5, §7.2 row 2, acceptance criteria 10–13.
- Owner decisions 1, 8 and 9 (readings fixes).

---

## Goal

A member opens `/builder` and lands on step 1. The next Sunday, in the church's timezone, is already filled in with its occasion and lectionary readings. The member can:
- pick **any** date: weekday feasts such as Ash Wednesday, Christmas Eve, Good Friday and Thanksgiving are found, and any other date falls back to typing the readings;
- choose between several reading sets for one day;
- edit the occasion and readings without the app ever overwriting what they typed;
- read the passage text in a translation they choose;
- pick the bulletin's Old and New Testament readings, where a Psalm is never picked automatically.

The draft survives a refresh and is kept separately for each church. The four-step shell (progress, sticky mobile footer, desktop summary) is ready for slices 3–5 to fill. The backend gains the shared outbound HTTP client, the TTL cache and the rate limiter that later slices reuse.

---

## Scope / Out of scope

### In scope

| Area | Items |
|---|---|
| Builder shell (F §4.7) | Routes `/builder`, `/builder/readings`, `/builder/hymns`, `/builder/liturgy`, `/builder/review`. `StepHeader`, `StepProgress`, `StepFooter`, `SummaryPanel` plus a bottom sheet below `lg`. An "Available soon" card for steps 2–4 (3, 4 and 5a each replace theirs; see Hand-offs). A "New service" action. `/` redirects to `/builder`. `last_step` written on entry. `AppNav` (F §4.2), created here, with a "Builder" item. |
| Draft store (F §4.6) | The complete `DraftV1`, including the hymns and liturgy sections that later slices fill. Load, migrate, validate, persist, sync between tabs, prune. Readings transitions. Date side effects (the communion default). `draftToServicePayload` and `fingerprint`. |
| Step 1 (inv. C1–C10) | Date (any date; default next Sunday in the church timezone). Lectionary lookup with loading, error and retry states. Reading-set switcher. Occasion. Scripture list. Readings list with lazily loaded passage text. Translation picker. Bulletin OT/NT pickers with automatic defaults. |
| Readings fixes (decision 9) | Psalm-as-NT: the classifier plus the automatic default, shown in slice 2 and applied to the docx in 5a. Stale lectionary on load: the step behaviour for `fields_origin: "archive"`; 5a supplies the mapping. Also the lectionary bugs in inv. C1–C4, C9 and C10 that are listed under Behavior changes. |
| Backend | `GET /lectionary/readings`, `GET /translations`, `POST /scripture/passages`, additive fields on `GET /church`. Refactors of `vanderbilt_lectionary.py` and `scripture_fetcher.py`. New `scripture_refs.py`, `usecases/lectionary.py`, `usecases/passages.py`, `usecases/church_profile.py`. |
| Platform (F §7.2 row 2) | `integrations/http.py`, `cache.py`, `api/ratelimit.py` (per-user buckets plus process-wide upstream budgets for bible-api and ESV). Every bucket from F §1.8 is defined; `lectionary`, `scripture` (charged per upstream part) and `church_create` (a 3-per-minute burst guard that cannot pre-empt slice 1's durable 5-per-24 h cap) are wired. Every limiter 429 is slice 1's `domain_errors.RateLimited`. `respx` in `requirements-dev.txt`. Shared Python/TS fixtures. `lib/dates.ts` and its guard test. |

### Out of scope, and which slice owns it

| Item | Slice |
|---|---|
| Hymns step content; hymnal and hymn queries | 3 |
| Tighter scripture-to-hymn matching ("Psalm 1" matching "Psalm 119", "Isaiah" matching "is 9:6", "John" matching "1 John", inv. §0 item 5). It builds on `scripture_refs.split_book` (below). | 3 |
| Replacing the substring NT heuristic in `suggest_hymns_for_service` (worship_service.py:436-445) with `default_nt_ref`, and removing the `[Could not load text]` check (worship_service.py:433) | 3 |
| Liturgy step, sermon title, communion toggle UI, default benediction text | 4 |
| Review actions (save, download, email); the docx OT/NT fallback (worship_service.py:874-886); `serviceToDraft`; what happens to `editing` when the date changes (inv. F7); the `/services` archive | 5a / 5b |
| Writing the church default translation; "Timezone not recognized." in Settings | 6a |
| Lectio alternative citations (inv. C2 edge case) stay dropped, as today | — (not requested) |
| Any change to Streamlit | frozen (F §6.1) |

### Hand-offs: interfaces this slice provides or assumes

| Other slice | Interface | Direction |
|---|---|---|
| 1 | `useMeContext()` (`me.user.id` for the draft key, `me.churches` for pruning), `ChurchProvider` / `useChurch()` (`{id, name, role}`), `useChurchProfile()` with key `["church", id, "profile"]`, `useApi()` with `api.user` and `api.church`, the `(church)` layout's keyed remount, the UI kit (`ConfirmDialog`, `ErrorState`, `EmptyState`, `PendingButton`, `PageHeader`, `touch` button size), `timezones.is_valid_timezone`, the `DomainError` hierarchy (including `RateLimited(message, *, retry_after_seconds)`: 429 `rate_limited` with a `Retry-After` header and always `details.retry_after_seconds`; `run_idempotent` never stores it), `usecases/`, `test_route_guards.py` allowlists, `assert_church_isolated`, the OpenAPI contract test, `renderWithProviders`, `installFakeApi`, the no-network pytest guard. (`Skeleton` is the shadcn `src/components/ui/skeleton.tsx` that slice 0 already generated; it is not part of slice 1's kit.) | 2 assumes |
| 1 | Slice 1 creates no nav (nav items arrive with their slices). **Slice 2 creates `AppNav`** (`src/components/app/app-nav.tsx`, F §4.2): a header link row at `md` and wider, and a segmented row under the header below `md`, rendered by `AppHeader`. Its only item in slice 2 is "Builder". | 2 changes 1's header |
| 1 | `POST /churches` exists, so 2 adds `Depends(rate_limit("church_create"))` to it: a **burst guard of 3 per minute per user** that cannot pre-empt slice 1's durable cap (5 creates per user per rolling 24 h, in `usecases.onboarding.create_church`). Slice 1's 6th-create test must still see the cap message "You've created 5 churches in the last 24 hours. Try again later."; slice 2 keeps it passing (see Rate-limit buckets and Testing). | 2 changes 1's route |
| 3 | `useDraft()` and the `DraftV1.hymns` section; add hymn transitions in `lib/draft/hymns.ts`; add a date side effect in `lib/draft/date-effects.ts` (for example, drop `alternatives` whose `for_date_iso` differs) | 2 provides |
| 3 | **Builder shell, Hymns:** add `"hymns"` to `SHIPPED_STEPS` (`lib/draft/steps.ts`), so `StepProgress` shows the hymns status of F §4.7 instead of "Soon" and `stillNeeded` lists missing hymns; replace `SummaryPanel`'s Hymns block ("Available soon") with the three slots, each "#{number} {title}" or "No Opening hymn" / "No Response hymn" / "No Closing hymn"; replace the hymns placeholder page. Slice 3's file list names `steps.ts` and `summary-panel.tsx`, and it adds a DOM test that the Hymns step shows its status and the summary no longer says "Available soon". | 3 changes 2's shell |
| 3 | **`scripture_refs`:** `classify(ref) -> "ot" \| "psalm" \| "nt" \| "unknown"` (slice 3 tests `== "nt"`), `split_alternatives(ref)`, `default_nt_ref(scriptures) -> str \| None`, `split_book(ref)` and `BOOKS`. Slice 3 extends `BOOKS` with its single-chapter flag and adds `parse_refs`; the shared fixture must still pass. | 2 provides |
| 3 | **Passages:** `usecases.passages.get_passage_text(ref, translation) -> str \| None`, a re-export of `scripture_fetcher.get_passage_text` that never returns a sentinel. Query key `["passage", translation, ref]`; its cached data is `PassageOut` (`{reference, status, sections: [{reference, status, text}]}`), so slice 3 reads its `nt_text` through `passageText(p: PassageOut) -> string \| null` (the text of sections whose `status` is `ok`, joined with blank lines, or null when there are none; exported from `lib/queries/passages.ts`). | 2 provides |
| 3 | **Platform:** `rate_limit("ai")` with both the user and church rules; `integrations/http.py`; `cache.TTLCache` | 2 provides |
| 3 / 4 | `GET /church` is extended additively through `ChurchProfileOut` (3 adds `default_hymnal` and `effective_hymnal`, 4 adds `default_benediction`). The usecase is `usecases/church_profile.get_church_profile`. | 2 creates the model |
| 4 / 5b | **Rate limiter:** `ratelimit.consume(bucket, *, user_id, church_id=None, cost=1)`, which `rate_limit(bucket)` calls with `cost=1`, plus `ratelimit.reset_for_tests()`. An exhausted bucket raises slice 1's `domain_errors.RateLimited` (no `ApiError`), which `run_idempotent` never stores, so a limiter 429 on 5b's `POST /bulletin-emails` is not replayed. | 2 provides |
| 4 | **Draft:** `DraftV1.liturgy`. The fresh draft's `benediction` card is `{enabled: true, text: "", origin: "default"}`; slice 4 fills the text while the origin is `default`. `isPristine` ignores the text of `default`-origin cards, so a fresh draft with the church's benediction filled in is still pristine. `include_communion` is kept equal to `isFirstSundayOfMonth(date_iso)` while `communion_origin` is `default`. Slice 2 implements this in `date-effects.ts`; slice 4 may move it into its `applyLiturgyDefaults`, so the rule lives in one place. Slice 4 renders the toggle. `update(recipe)` is a no-op (no `updated_at` bump, no write) when the recipe returns the same object, which `applyLiturgyDefaults` relies on. | 2 provides |
| 4 | **Builder shell, Liturgy:** add `"liturgy"` to `SHIPPED_STEPS`, so `StepProgress` shows the liturgy status of F §4.7 instead of "Soon" and `stillNeeded` lists missing sections; replace `SummaryPanel`'s Liturgy block ("Available soon") with F §4.7's contents: "n of m liturgy sections ready", communion yes or no, and the number of custom elements (slice 4's "Writing n sections…" is appended to that line); replace the liturgy placeholder page. Slice 4's file list names `steps.ts` and `summary-panel.tsx`, and it adds a DOM test that the Liturgy step shows its status and the summary no longer says "Available soon". | 4 changes 2's shell |
| 5a | **Draft and dates:** `useDraft() → {draft, update, replace, setLastStep, persistence}`, `freshDraft({church, user, now?})`, `DRAFT_VERSION` plus the `migrations` table, `fingerprint(payload)`, `isDirty(draft)`, `isPristine(draft)`, `status.ts`, and `lib/dates.ts` (`formatServiceDate`, `isValidDateIso`, `nextSunday`, `todayIn`). Slice 2 ships a provisional `mapping.ts` (`draftToServicePayload(draft)`, one argument, as in 5a), which 5a owns and replaces. | 2 provides |
| 5a | **Readings:** the readings step handles `fields_origin: "archive"` with `reading_set: null`: it fetches that date's lectionary and never overwrites the fields. The "Readings available" banner shows for archived fields only once the date has changed since the load (`date_origin !== "archive"`). Slice 2 never changes `editing`. | 2 provides |
| 5a | **Bulletin readings, one rule:** `scripture_refs.resolve_readings(scriptures, ot_pick, nt_pick) -> ReadingPair(ot, nt, ot_auto, nt_auto)` and its TS port `resolveReadings`. It implements 5a's `resolve_doc_readings` rule **including picks** (OT = the pick, else the first line; NT = the pick, else the first line other than the *effective* OT whose first alternative is NT) and additionally ignores a pick that is not among the current `picker_options` for its side. The screen (`effectivePicks`), 5a's `resolve_doc_readings` and 5a's `docReadings` **must all delegate to it**, so the screen and the Word file cannot disagree, whether or not a pick is stale. 5a's `doc_readings.json` cases must also pass through `resolve_readings`; slice 2's `scripture_refs.json` carries the mixed cases (one explicit pick, one automatic) and the stale-pick cases. Also provided: `is_nt_ref`, `expand_ref_options`, `picker_options`, and `default_reading_pair(s) = resolve_readings(s, "", "")`, with TS ports. The provisional `draftToServicePayload` emits only picks that are still options (`resolveReadings`' explicit values); **5a's replacement must keep that rule.** | 2 provides |
| 5a | **Builder shell, Review:** add `"review"` to `SHIPPED_STEPS`, so Review's status reads "Saved" or "Unsaved changes" (derived from `isDirty(draft)` and `editing`) instead of "Not in archive"; wire `SummaryPanel`'s status line to the archive state ("In archive (saved 10:42) · Unsaved changes", F §4.7); replace the review placeholder page and **delete `StepPlaceholder`** (no step uses it any more). Slice 5a's file list names `steps.ts`, `summary-panel.tsx` and the deleted `step-placeholder.tsx`, and it adds a DOM test that the Review step shows its status and the summary no longer says "Available soon" (5a's own email-slot placeholder is 5b's to replace). | 5a changes 2's shell |
| 5a / 5b / 6a | `AppNav` (created here): 5a adds "Services", 5b or 6a adds "Settings". | 2 provides |
| 6a | Invalidates `["church", id, "profile"]` after `PATCH /church`, so a new default translation reaches an open builder. Reads `timezone_valid`, which is computed with slice 1's `timezones.is_valid_timezone`, the same check 6a's `PATCH /church` uses. | 2 provides |

---

## User experience

### Builder shell (every step)

- **Mobile (375 px):** one column, `max-w-2xl`, 16 px gutters. From top to bottom:
  - `AppHeader`;
  - `StepHeader`: the title "Service Builder", a "Summary" button, and an overflow menu with "New service";
  - `StepProgress`: the line "Step 1 of 4 · Date & readings" above four segments;
  - the step content;
  - `StepFooter`, sticky at the bottom with `pb-[env(safe-area-inset-bottom)]`: "Back" on the left and "Next: Hymns" on the right. Below `md`, while a text input or textarea has focus, the footer hides, so the iOS keyboard doesn't stack on it (`useKeyboardOpen()`, focus-based; slice 4 reuses it).
- **Desktop (≥ 1024 px):** `grid-cols-[minmax(0,1fr)_20rem] gap-6 max-w-6xl`. `SummaryPanel` is sticky in the right column and the "Summary" button is hidden. `StepProgress` shows four labelled steps: "1 Date & readings · 2 Hymns · 3 Liturgy · 4 Review & send".
- **Step status** comes from `lib/draft/status.ts` (F §4.7):
  - Readings: `complete` (✓), or `incomplete` with "n of 3", counting a valid date, a non-empty occasion and at least one scripture.
  - Hymns and Liturgy: the muted label "Soon" until their slice adds them to `SHIPPED_STEPS` (slice 3 adds `"hymns"`, slice 4 adds `"liturgy"`; see Hand-offs).
  - Review: "Not in archive" until 5a adds `"review"` and shows "Saved" or "Unsaved changes".
  - Every step is tappable (F D9).
- **Footer labels:** readings → "Next: Hymns"; hymns → "Back" / "Next: Liturgy"; liturgy → "Back" / "Next: Review"; review → "Back" only.
- **Steps 2–4 (placeholders):** an `EmptyState` card with the title **"Available soon"** and the body **"Keep using the current app for this part."** Slice 3 replaces the Hymns card, slice 4 the Liturgy card, and 5a the Review card, deleting `StepPlaceholder`. Review also shows **"Still needed"**, a list built only from shipped steps, with each row linking to its step:
  - "No service date — Choose one"
  - "No occasion — Add one"
  - "No scripture readings — Add one"
- **SummaryPanel** (desktop column; mobile bottom sheet from "Summary"). Each block links to its step.
  - **Date:** "Sunday, October 4, 2026", then the occasion or "No occasion yet".
  - **Readings:** each reading on its own line, with "OT" and "NT" chips on the bulletin readings. An automatic choice shows "OT (auto)".
  - **Hymns** and **Liturgy:** "Available soon". Slice 3 replaces the Hymns block with the three slots ("#{number} {title}" or "No Opening hymn"); slice 4 replaces the Liturgy block with "n of m liturgy sections ready", communion yes or no, and the number of custom elements (F §4.7).
  - **Status line:** "Draft saved on this device · Not in archive"; in memory-only mode, "Draft not saved on this device". 5a wires the archive half ("In archive (saved 10:42) · Unsaved changes").
- **New service** (overflow menu):
  - If the draft is pristine (see `isPristine` below), it resets immediately.
  - Otherwise a `ConfirmDialog` opens: title **"Start a new service?"**, body **"This clears the current draft on this device."**, confirm **"Start new service"**, cancel "Cancel".
  - Afterwards it goes to `/builder/readings`.

### Step 1 — Date & readings (mobile order)

1. **Service date** card
   - A native `<input type="date">` labelled **"Service date"**, with the help text "Readings and the occasion load automatically for this date." Every date is allowed.
   - Below the input, the long date, for example **"Sunday, October 4, 2026"** (`formatLongDate`).
   - When the date is not a Sunday, an info line: **"Not a Sunday. We'll look for this day's own readings, such as Ash Wednesday, Christmas Eve or Good Friday."**
   - When the date is not the next Sunday, a text button: **"Use next Sunday (October 4)"**.
   - An empty or invalid input shows the inline message **"Choose a service date."** No lookup runs, and the draft keeps `date_iso: ""`.
   - A date before today (church timezone) shows the muted note **"This date has passed."** It is not blocking.
   - A year outside 1900–2199 shows **"Enter a date between 1900 and 2199."** No lookup runs.
2. **Lectionary status.** Exactly one of these shows, directly under the date. The lookup runs for the date **400 ms after it last changed** (typing a date segment by segment passes through intermediate dates; only the settled one is looked up).
   - **Loading** (also shown during that 400 ms wait): two skeleton lines plus "Looking up the lectionary…". After 8 s, "Still working — this can take up to a minute."
   - **Several sets** (`reading_sets.length > 1`):
     - A radio group with the legend **"This date has more than one set of readings"**. Each option is a card showing the set name and its references joined with " · ". Options are keyed by index, so two sets with the same name stay distinct.
     - The selected option is the set whose references equal the draft's cleaned scriptures; otherwise `reading_set.index` for this date; otherwise none.
     - Choosing a set when `fields_origin` is `empty` or `lectionary` applies it immediately.
     - When `fields_origin` is `user` or `archive`, it opens the **Replace** confirmation (see 3).
   - **No readings** (`status: "no_readings"`): an info callout, **"No lectionary readings for Tuesday, September 29, 2026. Enter the occasion and readings below."**, with an **"Enter readings"** link button that moves focus to the Occasion field. Focus never moves on its own, so a keystroke meant for the date input can't land in Occasion.
   - **Unavailable** (502/504/network/timeout): `ErrorState` with **"The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes."** and a **"Try again"** button, which refetches.
   - **Rate limited** (429): `ErrorState` with the F §4.8 copy **"Too many requests — try again in N s."**; its **"Try again"** button is disabled until `retryAfterSeconds` have passed, then refetches. The fields are untouched and manual entry keeps working.
   - **Partial** (`partial: true`, shown together with the set UI): the muted note "One lectionary source didn't respond, so other reading options for this date may be missing."
   - **Stale fields.** Shown together with "No readings" or "Unavailable" when `fields_origin == "lectionary"` and `reading_set.date_iso != date_iso`: **"These readings are from {set name} ({Month D, YYYY}), not {Month D, YYYY}."** with a **"Clear readings"** button. The fields stay as they are until the user clears them (F §4.6: a lookup failure or empty result leaves the fields untouched).
3. **Readings available banner** (`showAvailableBanner`). F §4.6 limits it to new readings for a *changed* date, so ordinary edits never raise it. It shows when the lookup for the current date returned sets, no set's references equal the draft's cleaned scriptures, and:
   - `fields_origin` is `user` and `reading_set?.date_iso !== date_iso`: the typed fields were not filled from this date's lectionary (the date changed after filling, or the user typed before or instead of a lookup). Deleting the Psalm line or one track of a set filled for this same date therefore never shows it; the set switcher still offers the other sets;
   - or `fields_origin` is `archive` and `date_origin !== "archive"`: the date was changed after the archived service was loaded, or the service had no date. An archived service on its own date never shows it.
   - It never shows for `empty` or `lectionary` fields, which auto-fill instead.
   - Text: **"Readings for {Month D, YYYY} are available."** with a **"Use them"** button.
   - "Use them" opens a `ConfirmDialog`: title **"Replace your readings?"**, body **"Your occasion and scripture list will be replaced with “{set name}” from the lectionary."**, confirm **"Replace readings"**, cancel **"Keep mine"**.
   - Confirming applies the default set, or the set chosen in the switcher. "Keep mine" also hides the banner for this date until the date changes (component state keyed by `date_iso`; not stored).
4. **Occasion**
   - Text input labelled **"Occasion"**, help "Printed as the bulletin's title. Filled from the lectionary; edit if needed.", placeholder "e.g. Third Sunday of Easter". Maximum 300 characters: "Too long (max 300 characters)."
   - An origin caption under the field:

     | Draft state | Caption |
     |---|---|
     | `lectionary` | "From the Revised Common Lectionary: {set name}" |
     | `user`, with a reading set for this date | "Edited from the lectionary ({set name})" |
     | `user`, no reading set | "Entered by you" |
     | `archive` | "From the saved service" |
     | `empty` | none |
5. **Scripture readings**
   - Textarea labelled **"Scripture readings"**, help "One reference per line, for example Matthew 17:1-9. Filled from the lectionary; edit if needed.", placeholder "Matthew 17:1-9". It is 5 rows tall and grows with its content.
   - Validation:
     - "Up to 20 readings." (more than 20 non-blank lines)
     - "Line {n} is too long (max 200 characters)."
   - Blank lines are allowed while typing and are dropped from everything derived.
   - The lectionary never produces a line that breaks these limits (the backend guarantees ≤ 20 lines of ≤ 200 characters per set; see "Vanderbilt parsing"), so these messages only ever describe what the user typed.
6. **Readings list** (heading **"Readings"**). It is derived from the cleaned scriptures, debounced 400 ms.
   - Header row (always shown, including when the list is empty):
     - **"Bible translation"** select (`items` map), help "For the passage text shown here. The bulletin lists the references, not the verse text."
     - The caption "Passage text shown in {label}."
     - A **"Show all text"** button. It expands every row; at most **3 passage requests are in flight** at once (a client-side limiter in `lib/queries/passages.ts`; each request's 30 s timeout starts when it leaves the queue).
   - One row per reference:
     - the reference (wrapping, `break-words`);
     - a testament badge: **OT**, **Psalm** or **NT**, or **?** with the tooltip "Book not recognized". A line with " or " alternatives shows one badge per alternative;
     - a **"Show text" / "Hide text"** toggle. Expanded state is keyed by the reference text, so editing a line collapses its row and nothing is fetched until the row is opened again. A line longer than 200 characters has the toggle disabled (the textarea already shows its error) and is never sent.
   - Expanded passage states. Each section (one per " or " alternative) has a `status` and the text of the parts that loaded (see "Status rules"). The row picks the first matching line:

     | Response | Row shows |
     |---|---|
     | loading | "Loading text…" |
     | every section `ok` | the text, as React text with `whitespace-pre-wrap`; with " or " alternatives, one section per alternative, each with its reference as a small heading |
     | some text, not every section `ok` | the sections that have text; under a section with none, its own line "Couldn't load {reference}."; then the note **"Part of this passage couldn't be loaded."**, plus **"Try again"** (`refetch`) when the passage status is `unavailable` |
     | no text, status `not_found` | **"Couldn't find this passage. Check the reference, for example “Matthew 17:1-9”."** |
     | no text, status `unavailable`; or the request failed (network, timeout, 5xx) | **"Passage text isn't available right now."** plus **"Try again"** (`refetch`) |
     | 429 | "Too many requests — try again in N s." (F §4.8), with "Try again" enabled after N s |
     | 422 (from the UI only for a line with more than 20 parts) | the server message, "Too many passages in one request." |
   - Empty list: **"Add a reading above to see its text and choose the bulletin readings."**
7. **Bulletin readings** card (heading **"Bulletin readings"**, help "The bulletin prints one Old Testament and one New Testament reading.")
   - Select **"Old Testament reading"** (options: expanded alternatives classified `ot`, `psalm` or `unknown`) and select **"New Testament reading"** (options: `nt`). This is parity with app.py:598-631.
   - The value `""` means automatic. The placeholder shows **"Automatic: {ref}"**, using `resolve_readings(scriptures, ot_pick, nt_pick)` with the line as written, or **"None — choose one"** when there is no default. The automatic side depends on the other side's pick: with Easter's lines (Acts, Psalm 118, Colossians, John) and the OT pick "Psalm 118:1-2, 14-24", the NT placeholder reads "Automatic: Acts 10:34-43". This is exactly what the docx prints from 5a on, because 5a's resolver delegates to the same function.
   - When a pick is set, a **"Use automatic"** text button clears it. There is no sentinel item (F §4.9.3).
   - **Stale picks.** A stored pick that is no longer among the current options for its side is ignored by `resolve_readings`, so the screen, the provisional payload and (from 5a) the docx all treat it as automatic, whatever state the stored draft is in. The store also removes such picks from the draft (`normalizePicks`) when the textarea loses focus, when a set is applied, on load and migration, on `replace` (New service, 5a's archive load) and when another tab's draft is adopted. While the user is typing, the stored pick is kept, so retyping the line restores it.
8. **Footer:** "Next: Hymns".

### Other states and messages

| Situation | Behaviour and copy |
|---|---|
| Builder first render | `Skeleton` shaped like the step while the draft loads (synchronous from localStorage; the church profile is already loaded by the `(church)` layout) |
| Draft could not be restored | Start fresh, back up the raw value, toast "We couldn't restore your unsaved draft." (F §4.6) |
| Storage unavailable | A one-time toast plus the summary status: "This browser isn't saving your draft. Don't refresh until you save." (F §4.6) |
| Another tab changed this draft | Adopt the newer `updated_at`, toast "Updated from another tab." |
| Translations list failed | The translation select is disabled and shows the profile's `effective_translation_label`. Passage text uses `church.effective_translation` until the list loads: `effectiveTranslation` only honours a stored override it can see in the list. The override stays in the draft. |
| 401 / church 403 / 500 | Global handling (F §4.4, §4.8) |

---

## API

All routes follow F §1. JSON is snake_case. User-scoped routes ignore `X-Church-Id` and go into the `USER_SCOPED` allowlist in `test_route_guards.py`.

One assumption about slice 1: its Pydantic-422 mapping strips the `query.` location prefix the same way it strips `body.`, so a bad `?date=` reports `fields.date`. If it doesn't, slice 2 adds that. (No client-side error code is added: an upstream passage failure is data, not an error; see Queries.)

| Method | Path | Guard | Request | Response | Errors |
|---|---|---|---|---|---|
| GET | `/lectionary/readings` | user + `rate_limit("lectionary")` | `?date=YYYY-MM-DD` | 200 `LectionaryOut` | 401 `unauthenticated`; 422 `invalid_request` (`fields.date`: "Not a valid value." for a bad format, or "Enter a date between 1900 and 2199."); 429 `rate_limited`; 502 `upstream_error` / 504 `upstream_timeout` "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes." |
| GET | `/translations` | user | – | 200 `TranslationsOut` | 401 |
| POST | `/scripture/passages` | user; the route charges the `scripture` bucket **one token per upstream part** after validation (see Rate-limit buckets) | `PassagesIn` | 200 `PassagesOut` (per-passage and per-section status; upstream failures never become 5xx) | 401; 422 `invalid_request` (`fields.refs` "Enter a scripture reference." for an empty list or a blank ref, `fields.refs` "Too many passages in one request." for more than 20 parts in total, `fields.translation` "Unknown or unavailable translation.", or a Pydantic size error for more than 4 refs or a ref over 200 characters); 429 |
| GET | `/church` | church | `X-Church-Id` | 200 `ChurchProfileOut` (**additive** over slice 0/1 `ChurchOut`) | 401; 403 `forbidden` |
| POST | `/churches` | user (slice 1 route) | unchanged | unchanged | **adds** 429 `rate_limited` "Too many requests. Try again in {n} seconds." (`church_create` burst guard, 3 per minute per user). Slice 1's durable cap (5 per user per 24 h, "You've created 5 churches in the last 24 hours. Try again later.") is unchanged and still answers the 6th create in 24 h. |

### Schemas

These live in `backend/api/schemas.py` when shared; otherwise at the top of the route module.

```python
class ReadingSetOut(BaseModel):
    name: str                                   # "Liturgy of the Passion", "Proper 22 (27)", "Ash Wednesday"
    scriptures: list[str]                       # display order: first, psalm, second, gospel; compound cells split
                                                # guaranteed: 1–20 items, each 1–200 chars (fits_draft_limits)
    source: Literal["lectio", "vanderbilt", "merged"]

class LectionaryOut(BaseModel):
    date: datetime.date                         # echo of the requested date; never normalized
    status: Literal["ok", "no_readings"]
    partial: bool                               # sets found, but one source failed
    reading_sets: list[ReadingSetOut]           # [] when status == "no_readings"
    default_index: int | None                   # None iff reading_sets == []

class TranslationOut(BaseModel):  id: str; label: str
class TranslationsOut(BaseModel): default: str; esv_available: bool; items: list[TranslationOut]
    # default = "web"; items in scripture_fetcher.TRANSLATIONS order, esv only when configured

class PassagesIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refs: list[Annotated[str, StringConstraints(max_length=200)]] = Field(max_length=4)  # the UI sends 1
    translation: str = Field(max_length=20)
    # empty list, blank ref and > 20 parts are rejected by the usecase with the exact messages above

PartStatus = Literal["ok", "not_found", "unavailable"]

class PassageSectionOut(BaseModel):
    reference: str                              # one " or " alternative, e.g. "Matthew 27:11-54"
    status: PartStatus                          # derived from its parts (Status rules)
    text: str | None                            # the parts that loaded, joined; None when none loaded

class PassageOut(BaseModel):
    reference: str                              # as sent (trimmed)
    status: PartStatus                          # derived from its sections (Status rules)
    sections: list[PassageSectionOut]           # one per alternative, always all of them

class PassagesOut(BaseModel):
    translation: str; translation_label: str; passages: list[PassageOut]   # same order as refs

class ChurchProfileOut(ChurchOut):              # ChurchOut = {id, name, role}; /me keeps ChurchOut
    timezone: str
    timezone_valid: bool                        # timezones.is_valid_timezone(timezone) (slice 1; exact, case-sensitive)
    bible_translation: str | None               # stored settings value, or None
    effective_translation: str                  # stored value if currently available, else "web"
    effective_translation_label: str            # translation_label(effective_translation), for when /translations fails
```

**Example** (`GET /lectionary/readings?date=2026-03-29`):

```json
{"date": "2026-03-29", "status": "ok", "partial": false, "default_index": 1,
 "reading_sets": [
   {"name": "Liturgy of the Palms", "source": "vanderbilt",
    "scriptures": ["Psalm 118:1-2, 19-29", "Matthew 21:1-11"]},
   {"name": "Liturgy of the Passion", "source": "merged",
    "scriptures": ["Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11", "Matthew 26:14-27:66"]}]}
```

### Status rules

- **`GET /lectionary/readings`:**
  - Status is `ok` when at least one set was found.
  - With no sets, if at least one source *failed*, the route returns 502 `upstream_error`, or 504 `upstream_timeout` when every failure was a timeout.
  - With no sets and no failure, status is `no_readings`.
  - A source *fails* on a network error, a timeout, 403, 5xx, 429, a wrong content type, or a CSV with no header. A source reports *none* on a Lectio 404 or empty `data`, a Vanderbilt 404 for the year file, or a file with no row on that date.
- **`POST /scripture/passages`** (the same derivation at every level):
  - **Part** (one upstream call; see `fetch_passage`): `ok` with text; `not_found` (bible-api 404, or ESV returning no passages); or `unavailable` (network, timeout, 5xx, 429, the process-wide upstream budget exhausted, or the request deadline reached before the part ran).
  - **Section** (one " or " alternative): `ok` when every part is `ok`; otherwise `unavailable` if any part is `unavailable`; otherwise `not_found`. Its `text` is the texts of its `ok` parts in order, joined with blank lines, or `None` when no part is `ok`. A section with some parts missing therefore keeps the parts that loaded and carries a non-`ok` status.
  - **Passage**: the same rule over its sections. Every section is always returned, with whatever text it has.
- **Rate-limit body:** `{"error": {"code": "rate_limited", "message": "Too many requests. Try again in {n} seconds.", "request_id": …, "details": {"retry_after_seconds": n}}}`, plus the header `Retry-After: n`. It is slice 1's `domain_errors.RateLimited` rendered by slice 1's `DomainError` handler, which always adds `details.retry_after_seconds` and `Retry-After`; slice 1's durable church cap produces the same shape with its own message.

### Rate-limit buckets

`backend/api/ratelimit.py` defines every bucket in F §1.8 plus one addition:

| Bucket | Limit | Wired in |
|---|---|---|
| `lectionary` (**new; addition to F §1.8**) | 120 / 5 min / user | 2: `/lectionary/readings` (uncached dates call third parties) |
| `scripture` | 60 **parts** / 5 min / user | 2: `/scripture/passages`. The route calls `consume("scripture", user_id=…, cost=len(plan.parts))` after validation, where `plan.parts` is every upstream part of every alternative of every ref (cached or not, so the cost is known before any work). One request is capped at 20 parts, below the bucket size, so any valid request can eventually succeed. A typical one-reference request costs 1–3. |
| `church_create` | 3 / minute / user (burst guard; F §1.8) | 2: `POST /churches`. See below. |
| `ai` | 40 / 10 min / user **and** 400 / day / church | defined in 2, wired in 3 and 4 |
| `email` | 10 / hour / user | defined in 2, wired in 5b |

**`church_create` is only a burst guard.** The real limit on `POST /churches` is slice 1's durable, database-backed cap: 5 creates per user per rolling 24 h, answered with "You've created 5 churches in the last 24 hours. Try again later." The bucket runs as a dependency, before validation and before an idempotency replay, so a 422 or a replay also costs a token. At 3 per minute that costs at most about a minute's wait, and it answers in place of the cap only when a 4th request arrives within one minute; it never pre-empts the cap for creates spread over more than a minute. Slice 1's 6th-create test must still see the cap message: slice 2 updates it to advance the limiter's fake clock (`set_clock_for_tests`) 60 s between creates, so the cap, not the bucket, answers the 6th.

**Upstream budgets (process-wide, not per user).** Any Google account can call the user-scoped passage route, and every user shares the Railway IP and the one ESV key (inv. §4; F §7.4), so per-user buckets alone don't protect the upstreams. `integrations/budget.py` keeps a token bucket per upstream, shared by all requests in the process (one uvicorn worker):

| Upstream | Budget | Source |
|---|---|---|
| `bible_api` | 15 / 30 s | bible-api.com's documented per-IP limit (checked 2026-09-25) |
| `esv` | 60 / min **and** 1 000 / hour **and** 5 000 / day | Crossway's published ESV API limits (checked 2026-09-25) |

`try_acquire(upstream) -> bool` never waits. A part that finds no token is not sent; it becomes `unavailable` (not cached, logged as `budget`), so the user sees "Try again". Cache hits take no token.

### Client timeouts

Set in `lib/api/timeouts.ts`: lectionary 25 000 ms, passages 30 000 ms, translations and church use the default (F §1.8). The passages route has a **20 s server deadline per request** (see Passages), so a request whose parts are queued behind other requests on the shared pool still answers before the client gives up.

---

## Backend changes

### Upstream facts that shape the design (checked against the live sources on 2026-09-25)

These are recorded as fixtures (§Testing). They are why the merge rule below changes.

1. **Lectio (`lectio-api.org/api/v1/readings?date=…&tradition=rcl`) answers for exact dates, including weekdays.**
   - It returns data for Ash Wednesday (2026-02-18), Christmas Eve and Day (2025-12-24/25), Epiphany (2026-01-06) and Ascension (2026-05-14).
   - It returns **HTTP 404 with a JSON error** for Good Friday (2026-04-03), Maundy Thursday (2026-04-02), New Year's Day (2026-01-01), Holy Cross (2026-09-14), US Thanksgiving (2026-11-26) and an ordinary Tuesday (2026-09-29).
   - Today's code turns that 404 into a failure, and it only ever asks for the previous Sunday (vanderbilt_lectionary.py:357-362).
2. **Lectio's `dayName` is null** in every response checked, so today's names come from `_liturgical_sunday_name` or "{season} — Year {year}". An ordinary Sunday is labelled "Ordinary Time — Year A".
3. **Lectio data errors.**
   - Ascension 2026 gives gospel Matthew 28:16-20 (RCL: Luke 24:44-53).
   - Trinity Sunday 2026-05-31 returns **two sets interleaved**: Proper 4 (Matthew 7:21-29 …) then Trinity (Matthew 28:16-20 …). "First non-alternative per type" (vanderbilt_lectionary.py:298-304) therefore picks the Proper 4 readings.
4. **Vanderbilt's year CSV lists every observance with its own date**, including weekday feasts:
   - Nativity Propers I–III, Holy Name and New Year's Day, Epiphany, Ash Wednesday, Maundy Thursday, Good Friday, Ascension, Holy Cross, Thanksgiving;
   - several rows on one date: Palms + Passion; Easter Vigil + Resurrection + Easter Evening; Visitation + Trinity; All Saints + Proper 26.

   Its rows are **not in date order**: the Nativity rows come after January rows, so the "nearest previous row" fallback (vanderbilt_lectionary.py:247-254) is unreliable. Ordinary-time rows pack two tracks into cells, for example First reading `"Genesis 12:1-9 Psalm 33:1-12"` and Psalm `"Hosea 5:15-6:6 Psalm 50:7-15"`. Easter-season cells start with `"* "`.
5. Vanderbilt answers **404 HTML** for a year file it doesn't have (`1999-00`) and **200 HTML** for some far-future years (`2045-46`). The default `WorshipServiceBuilder/1.0` user agent gets 200.
   - The **Easter Vigil** row (2025-26, 2026-27 and 2027-28 checked) packs the whole vigil into its First-reading cell: one 513–517-character string of `" - "`-separated segments, with headings ("Old Testament Readings and Psalms", "New Testament Reading and Psalm", "Gospel") and nine reading-plus-psalm pairs joined by " and ", for example `"Genesis 1:1-2:4a and Psalm 136:1-9, 23-26"`. Its other reading cells are empty. It is the only such cell in those three files.
6. **bible-api.com returns 404 for verse-part suffixes and en dashes**: "Isaiah 50:4-9a" and "Isaiah 50:4–9" both fail. It accepts "Isaiah 50:4-9", comma lists ("Luke 2:1-14, 15-20"), "Psalm"/"Psalms", abbreviations ("Matt 5:1-3") and the deuterocanon (Sirach, Wisdom of Solomon). Many RCL citations carry a/b suffixes, so passage text for them fails silently today.

### New and changed modules

| Module | Change |
|---|---|
| `backend/integrations/__init__.py`, `integrations/http.py` | **New** (F §2.7). A module-level `httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0), follow_redirects=True, headers={"User-Agent": "WorshipServiceBuilder/1.0"})`. A request event hook rejects any non-`https` URL, which also covers redirects. `get(url, *, params=None, headers=None, read_timeout: float) -> httpx.Response`. `set_http_for_tests(client)`. |
| `backend/cache.py` | **New.** `TTLCache(maxsize, ttl_ok, ttl_fail, clock=time.monotonic)`, thread-safe with LRU eviction. `get_or_load(key, loader)`: <ul><li>An ok hit returns the value; a failure hit re-raises the cached `CacheableFailure`.</li><li>A miss is **single-flight per key** (per-key lock): the loader runs; its return value is cached for `ttl_ok`; a `CacheableFailure` it raises is cached for `ttl_fail` and re-raised; any other exception is not cached.</li><li>`clear()`.</li></ul>An error is never stored as an empty success (F §2.7). |
| `backend/api/ratelimit.py` | **New.** A token-bucket `RateLimiter(clock)` keyed by `(bucket, scope_id)`, with a lock and pruning of idle entries. <ul><li>`consume(bucket, *, user_id, church_id=None, cost=1)` charges every rule of the bucket (user rule; church rule when the bucket has one) all-or-nothing by `cost`. When a rule lacks tokens, nothing is charged and it raises slice 1's `domain_errors.RateLimited("Too many requests. Try again in {n} seconds.", retry_after_seconds=n)`, where n is the ceiling of the seconds until `cost` tokens are available. Slice 1's `DomainError` handler turns it into 429 `rate_limited` with `Retry-After: n` and `details.retry_after_seconds`, and `run_idempotent` never stores it, so a limiter 429 is never replayed.</li><li>`rate_limit(name)` returns a FastAPI dependency that calls `consume(name, cost=1)`. It depends on `get_current_user`, plus `require_church` for buckets with a church rule. The church id comes from the resolved `ActiveChurch`, never the raw header. Routes whose cost depends on the request (`/scripture/passages`) call `consume` themselves after validation.</li><li>`reset_for_tests()` and `set_clock_for_tests(clock)`.</li></ul>The bucket arithmetic lives in a pure `backend/token_bucket.py` (`TokenBucket(capacity, per_seconds, clock)`, `try_take(n) -> float` returning 0 or the seconds to wait) shared with the upstream budgets. There is one 429 mechanism (F §1.5, §2.2): `ApiError` is not extended and gains no `headers`. |
| `backend/integrations/budget.py` | **New.** Process-wide upstream budgets (see "Upstream budgets"): `try_acquire(upstream: Literal["bible_api", "esv"]) -> bool`, non-blocking, all of an upstream's rules all-or-nothing, thread-safe, built on `token_bucket.py`. No FastAPI, so `scripture_fetcher.py` can call it. `reset_for_tests()` and `set_clock_for_tests(clock)`. |
| `backend/scripture_refs.py` | **New** (from app.py:69-102). See below. |
| `backend/vanderbilt_lectionary.py` | **Refactor.** See "Lectionary domain". It keeps its module name (F §2.1). |
| `backend/scripture_fetcher.py` | **Refactor.** See "Passages". Public names used by frozen code and tests stay: `TRANSLATIONS`, `DEFAULT_TRANSLATION`, `esv_configured()`, `available_translations()`, `translation_label()`, `get_passage_text()`. |
| `backend/usecases/lectionary.py` | **New.** `readings_for_date(d) -> LectionaryResult`. |
| `backend/usecases/passages.py` | **New.** `plan_passages(refs, translation) -> PassagePlan`, `load_passages(plan) -> PassagesResult`, `translation_options() -> TranslationOptions`. The route runs `plan_passages`, then `ratelimit.consume("scripture", user_id=user.id, cost=len(plan.parts))`, then `load_passages`. |
| `backend/usecases/church_profile.py` | **New.** `get_church_profile(church_id) -> ChurchProfile`. Slices 3 and 4 add fields. |
| `backend/api/routes/lectionary.py`, `routes/reference.py` (`/translations`), `routes/scripture.py` | **New** thin routes (F §2.2). Blocking I/O means plain `def`. |
| GET `/church` (in `routes/me.py` today, or wherever slice 1 placed it) | Returns `ChurchProfileOut` from `get_church_profile(active.id)`. |
| `POST /churches` (slice 1) | Adds `Depends(rate_limit("church_create"))`, the 3-per-minute burst guard; slice 1's durable cap in `create_church` is unchanged. |
| `backend/requirements.txt` | Add `tzdata` if slice 1 hasn't, so `zoneinfo` works on slim Railway images. |
| `requirements-dev.txt` | Add `respx`. |
| `backend/scripts/record_fixtures.py` | **New** (manual; never in CI). Records the Lectio, Vanderbilt and bible-api fixtures listed under Testing. |

### `scripture_refs.py` (pure; ported to TypeScript with shared fixtures)

- **`BOOKS`**: the 66 books plus the deuterocanon (Tobit, Judith, Additions to Esther, Wisdom of Solomon, Sirach, Baruch, Letter of Jeremiah, Prayer of Azariah / Song of the Three, Susanna, Bel and the Dragon, 1–4 Maccabees, 1–2 Esdras, Prayer of Manasseh, Psalm 151).
  - Each entry is `Book(name, testament, aliases)`, where `testament` is `"ot"`, `"psalm"` or `"nt"`. The deuterocanon counts as `"ot"`; Psalms (and Psalm 151) are `"psalm"`.
  - Aliases cover common abbreviations with or without a period: Gen, Ex/Exod, Lev, Num, Deut, Josh, Judg, 1 Sam, 1 Kgs, 1 Chr, Neh, Esth, Ps/Pss/Psa/Psalms, Prov, Eccl, Song/Song of Songs/Canticles, Isa, Jer, Lam, Ezek, Dan, Hos, Obad, Mic, Nah, Hab, Zeph, Hag, Zech, Mal, Sir/Ecclus, Wis, Bar, 1 Macc, Matt/Mt, Mk, Lk, Jn, Rom, 1 Cor, Gal, Eph, Phil, Col, 1 Thess, 1 Tim, Titus/Tit, Philem/Phlm, Heb, Jas, 1 Pet, 1 Jn, Rev. **The fixture is authoritative.**
- **`normalize_book_text(s)`:** lower-case; drop a leading `*` and whitespace; remove `.`; roman or ordinal prefixes `i|ii|iii|first|second|third` → `1|2|3`; `1john` → `1 john`; collapse spaces.
- **`split_alternatives(ref) -> list[str]`:** split on `\s+or\s+`, case-insensitively, and trim. This fixes the case-sensitive split (inv. C9).
- **`split_book(ref) -> tuple[Book, str] | None`:** the longest alias at the start, followed by end, a space or a digit; returns the canonical book and the rest ("17:1-9").
- **`classify(ref) -> "ot" | "psalm" | "nt" | "unknown"`:** for one alternative.
- **`is_nt_ref(ref) -> bool`:** `classify(ref) == "nt"`. This keeps the name of app.py:90-97, which 5a uses.
- **`expand_ref_options(refs) -> list[str]`:** clean the lines (trim, drop blanks), expand every alternative with `split_alternatives`, and de-duplicate in first-seen order. This is the parity name for app.py:79-87.
- **`picker_options(scriptures) -> {ot: [...], nt: [...]}`:** over `expand_ref_options(scriptures)`. `ot` holds `ot`, `psalm` and `unknown` (parity: anything not NT, app.py:100-102); `nt` holds `nt`.
- **`resolve_readings(scriptures, ot_pick="", nt_pick="") -> ReadingPair(ot, nt, ot_auto, nt_auto)`** (**fixes Psalm-as-NT**). This is the **only** implementation of the bulletin-reading rule. The screen, the provisional payload, and 5a's `resolve_doc_readings` / `docReadings` all call it (or its TS port), so what the screen shows is what the docx prints. It is 5a's `resolve_doc_readings` rule plus a validity check on picks:
  1. `entries` = the cleaned lines; `opts = picker_options(entries)`.
  2. `ot_pick = ot_pick.strip()`, and it is treated as `""` unless it is in `opts.ot`; the same for `nt_pick` with `opts.nt`. A stale pick is therefore automatic, whatever the stored draft or payload says.
  3. `ot` = `ot_pick`, else `entries[0]`, else `None`; `ot_auto = not ot_pick`. The automatic OT rule is unchanged (parity, worship_service.py:875); 5a holds the open question about it.
  4. `nt` = `nt_pick`, else the first entry `e != ot` (the **effective** OT, which may be an explicit pick) whose **first** alternative `is_nt_ref`, else `None`; `nt_auto = not nt_pick`. In RCL order with no picks that is the second reading, or the Gospel when there is no second reading. A Psalm is never the automatic NT.
  5. Entries are returned **as written**, so an " or " line prints whole, as the docx does today.

  Examples (all in `scripture_refs.json`):
  - `["Isaiah 5:1-7","Psalm 80:7-15","Philippians 3:4b-14","Matthew 21:33-46"]`, no picks → (Isaiah, Philippians)
  - `["Acts 10:34-43","Psalm 118:1-2, 14-24","Colossians 3:1-4","John 20:1-18"]`, no picks → (Acts, Colossians)
  - the same Easter lines, OT pick `"Psalm 118:1-2, 14-24"` → (Psalm 118, **Acts 10:34-43**, auto NT)
  - `["Romans 8:1-11","Psalm 23","John 10:1-10"]`, OT pick `"Psalm 23"` → (Psalm 23, Romans, auto NT)
  - the Isaiah lines, NT pick `"Matthew 21:33-46"` → (Isaiah auto, Matthew)
  - the Isaiah lines, OT pick `"Isaiah 5:1-8"` (no longer a line) → (Isaiah, Philippians), both auto
  - the Isaiah lines, NT pick `"Psalm 80:7-15"` (not an NT option) → (Isaiah, Philippians), both auto
  - `["Isaiah 9:2-7","Psalm 96"]` → (Isaiah, None)
- **`default_reading_pair(scriptures) -> ReadingPair`:** `resolve_readings(scriptures, "", "")`. Kept for callers that have no picks.
- **`default_nt_ref(scriptures) -> str | None`:** `default_reading_pair(scriptures).nt`, for slice 3.
- **`normalize_for_fetch(ref) -> str`** (fetch only; the displayed text never changes):
  - drop a leading `*`;
  - en and em dashes → `-`;
  - remove verse-part letters after digits (`9a`, `4b`, `35b` → `9`, `4`, `35`);
  - remove parentheses;
  - insert a comma between two verse groups separated only by whitespace (`1-14 15-20` → `1-14, 15-20`);
  - collapse doubled commas and spaces.

  Examples: "Luke 2:1-14, (15-20)" → "Luke 2:1-14, 15-20"; "Isaiah 50:4-9a" → "Isaiah 50:4-9".
- **`split_parts(ref) -> list[str]`:** split on `;` and carry the book into parts shaped like `3:1-7`. This moves from scripture_fetcher.py:124-140 unchanged.
- **`split_joined(ref) -> list[str]`** (fetch only): split on `\s+and\s+` only where the text after it starts with a recognized book (`split_book`), and trim. `"Genesis 1:1-2:4a and Psalm 136:1-9, 23-26"` → two; `"Psalm 42 and 43"` stays whole (and its fetch reports `not_found`). Used for the Easter Vigil's paired lines (below).
- **`scripture_key(ref) -> str`:** for comparisons. `normalize_for_fetch`, then lower-case, then remove whitespace, commas, periods and parentheses.

### Lectionary domain (`vanderbilt_lectionary.py`)

**Kept:**
- `_easter_date` becomes public as `easter_date`.
- `ReadingSet(name, first, psalm, second, gospel, scriptures, source)` is a frozen dataclass. The internal fields feed matching; the API exposes `name`, `scriptures` and `source`.

**Year file (fixes the boundary bug, inv. C2):**
- `advent_sunday(year)` = the Sunday from Nov 27 to Dec 3.
- `liturgical_year_for(d)` = `f"{y}-{(y+1)%100:02d}"` where `y = d.year if d >= advent_sunday(d.year) else d.year - 1`.
- Cases: 2027-11-27 → `2026-27`; 2027-11-28 → `2027-28`; 2026-11-28 → `2025-26`; 2026-11-29 → `2026-27`; 2025-12-24 → `2025-26`.

**Vanderbilt parsing (pure):**
- `parse_vanderbilt_csv(text) -> list[VRow]`:
  - finds the line containing "Calendar Date" and "Liturgical Date";
  - uses the fixed field names (vanderbilt_lectionary.py:179-182);
  - keeps rows whose calendar date parses;
  - raises `LectionaryFormatError` when there is no header (for example an HTML page).
- `vanderbilt_sets_on(rows, d)` returns **only rows whose calendar date equals `d`**, in file order. The nearest-previous fallback is removed.
- Cell cleanup, `clean_cell(cell) -> list[str]`:
  - strip quotes and whitespace; drop cells that start with `http` (parity);
  - drop a leading `* `;
  - **split a multi-reading cell** (one containing `" - "`, which today is only the Easter Vigil): split on `" - "`, trim, and drop every segment that does not start with a recognized book (`split_book`), which removes the headings "Old Testament Readings and Psalms", "New Testament Reading and Psalm" and "Gospel". Each remaining segment is one line, kept whole, so each vigil reading stays next to its psalm: the Vigil gives **11 lines**, the longest 69 characters (`"Baruch 3:9-15, 3:32-4:4 or Proverbs 8:1-8, 19-21; 9:4b-6 and Psalm 19"`). Splitting the pairs as well would give 21 lines, over the draft's 20. Passage text still loads per reading because `fetch_passage` applies `split_joined`;
  - otherwise, **split a compound cell** `"<reading> Psalm(s) <n>…"` into `[reading, "Psalm <n>…"]` at the first `\sPsalms?\s+\d`, but only when the part before it starts with a recognized book (`split_book`).

  `scriptures` is the flattened cleaned cells in column order (First reading, Psalm, Second reading, Gospel). `gospel` is the cleaned Gospel cell (empty for the Vigil, so the Vigil never matches a Lectio group). Example: Thanksgiving Day `"Deuteronomy 8:7-18 Psalm 65"` becomes `["Deuteronomy 8:7-18", "Psalm 65", "2 Corinthians 9:6-15", "Luke 17:11-19"]`.
- **Draft-limit guard, `fits_draft_limits(set) -> bool`:** 1–20 lines, each 1–200 characters (the draft's and 5a's `ServiceDraft` limits, inv. §2.1). It runs on every Vanderbilt set and every Lectio group **before** `merge`, so indices and the default are computed on what is returned. A set that fails is dropped and logged at warning level with its name and line lengths; it is never truncated. If that leaves no sets and no source failed, the status is `no_readings`. With today's data nothing is dropped; the guard makes `ReadingSetOut`'s limits a guarantee rather than an accident of the data.

**Lectio parsing (pure):**
- `parse_lectio_payload(payload) -> LectioDay | None` returns `None` when `data` is missing or `readings` is empty.
- It walks `readings` in order, skipping `isAlternative` (parity), and **starts a new group when a non-alternative type repeats**. This handles Trinity 2026.
- Each group becomes `first`, `psalm`, `second` and `gospel`, with `scriptures = [first, psalm, second, gospel]` minus blanks (parity, vanderbilt_lectionary.py:311). It also keeps `season`, `year` and `dayName`.

**Names for Lectio-only sets** (`lectio_set_name(day, d)`):
1. `dayName` when present;
2. for a Sunday, `sunday_name(d)`;
3. for another day, `weekday_feast_name(d)`;
4. `"{season} — Year {year}"`;
5. `"Sunday"`, or the weekday name for a weekday.

When several groups end up with the same name, the second and later get " (2)", " (3)".

- `sunday_name(d)` is date-only (it no longer depends on the season string) and returns `None` for any non-Sunday. **This fixes a weekday such as Ascension Thursday being labelled "Sixth Sunday of Easter".** It covers: Advent 1–4; Baptism of the Lord; 2nd–9th after Epiphany; Transfiguration; Lent 1–5; Palm Sunday; Easter Sunday; Easter 2–7; **Day of Pentecost**; **Trinity Sunday**; **Reign of Christ** (the Sunday before Advent 1). The existing wording stays ("… Sunday in Lent", "… Sunday of Advent").
- `weekday_feast_name(d)`: Ash Wednesday (Easter −46), Maundy Thursday (−3), Good Friday (−2), Holy Saturday (−1), Ascension of the Lord (+39), Christmas Eve (Dec 24), Nativity of the Lord (Dec 25), New Year's Day (Jan 1), Epiphany of the Lord (Jan 6), All Saints Day (Nov 1); otherwise `None`.

**Merge** — `merge(lectio: LectioDay | None, v_sets: list[ReadingSet], d) -> (sets, default_index)`. It replaces the merge at vanderbilt_lectionary.py:368-396.

```
if not v_sets and not lectio: return [], None
if not v_sets:  sets = lectio groups named by lectio_set_name, source "lectio"; default = last
if not lectio:  sets = v_sets (source "vanderbilt");                       default = last   # parity
else:
    sets = copy(v_sets); matched = set()
    for g in lectio.groups:                       # each group replaces at most one Vanderbilt set
        k = scripture_key(g.gospel)
        if not k: continue
        for i, v in enumerate(sets):
            if i not in matched and k in {scripture_key(a) for a in split_alternatives(v.gospel)}:
                sets[i] = g with name=v.name, source "merged"; matched.add(i); break
    # unmatched Lectio groups are dropped: when Vanderbilt has rows, it decides which sets exist
    default = max(matched) if matched else len(sets) - 1
```

Expected outcomes, recorded as fixtures (★ = default):

| Date | Vanderbilt rows on that date | Lectio | Result |
|---|---|---|---|
| 2026-10-04 (Sun) | Proper 22 (27), two-track cells | Matthew 21:33-46 | [**Proper 22 (27)** ← Lectio readings ★]. Today: "Ordinary Time — Year A". |
| 2026-03-29 (Palm Sun) | Palms; Passion | Matthew 26:14-27:66 | [Palms, **Passion** ← Lectio ★]. Parity. |
| 2026-04-05 (Easter) | Vigil; Resurrection; Evening | John 20:1-18 | [Vigil (11 lines, headings dropped), **Resurrection** ← Lectio ★, Evening]. Today: a 4th duplicate set, which is the default, and the Vigil is one 517-character line. |
| 2026-05-31 (Trinity) | Visitation; Trinity Sunday | 2 groups (Proper 4; Trinity) | [Visitation, **Trinity Sunday** ← group 2 ★]. Today: the default is the Proper 4 readings. |
| 2026-05-14 (Thu) | Ascension (Luke 24:44-53) | Matthew 28:16-20, no match | [**Ascension of the Lord** ★], Vanderbilt readings |
| 2026-02-18 (Wed) | Ash Wednesday | Matthew 6:1-6, 16-21 | [**Ash Wednesday** ← Lectio ★] |
| 2025-12-24 (Wed) | Nativity of the Lord - Proper I | Luke 2:1-14 (15-20) | [**Nativity of the Lord - Proper I** ← Lectio ★] |
| 2025-12-25 (Thu) | Proper II; Proper III | John 1:1-14 | [Proper II, **Proper III** ← Lectio ★] |
| 2026-04-03 (Fri) | Good Friday | 404 | [**Good Friday** ★] |
| 2026-01-01 (Thu) | Holy Name; New Year's Day | 404 | [Holy Name, **New Year's Day** ★] (last, parity) |
| 2026-11-26 (Thu) | Thanksgiving Day | 404 | [**Thanksgiving Day** ★], with the compound cell split |
| 2026-11-01 (Sun) | All Saints Day; Proper 26 (31) | Matthew 23:1-12 | [All Saints Day, **Proper 26 (31)** ← Lectio ★] |
| 2026-09-29 (Tue) | none | 404 | `status: "no_readings"` |
| Any date, Vanderbilt down | — | 1 group | [Lectio group, named by `lectio_set_name`], `partial: true` |

**Fetchers** (use `integrations/http.py`). `SourceFailed(timeout: bool)` subclasses `CacheableFailure`. Every `httpx.HTTPError` is caught and becomes `SourceFailed(timeout=isinstance(e, httpx.TimeoutException))`.
- `fetch_lectio(d) -> dict | None`:
  - `GET LECTIO_API_URL?date=<d.isoformat()>&tradition=rcl`, read timeout 10 s;
  - 404 → `None` (definitive none);
  - 200 with a JSON content type and a body that decodes → the payload;
  - anything else, including a JSON decode error → `SourceFailed`.
- `fetch_vanderbilt_year(year) -> str | None`:
  - read timeout 15 s;
  - 404 → `None`;
  - 200 `text/plain` or `text/csv` → the text;
  - anything else → `SourceFailed`.

**Loaders** (what the caches store). Each converts every *expected* failure into `SourceFailed` **inside** the loader, so it is cached for the 5-minute failure TTL; an exception that escapes a loader is a bug, is not cached, and surfaces as a 500.

```python
def load_vanderbilt_year(year: str) -> list[VRow]:           # cached ok for 24 h, SourceFailed for 5 min
    text = fetch_vanderbilt_year(year)                        # raises SourceFailed
    if text is None:                                          # 404: definitive none
        return []
    try:
        return parse_vanderbilt_csv(text)
    except LectionaryFormatError as e:                        # e.g. HTML served as 200
        raise SourceFailed(timeout=False) from e

def load_lectio(d: date) -> LectioDay | None:
    payload = fetch_lectio(d)                                 # raises SourceFailed
    if payload is None:                                       # 404: definitive none
        return None
    try:
        return parse_lectio_payload(payload)                  # None when data/readings are empty
    except (KeyError, TypeError, ValueError) as e:            # unexpected JSON shape
        raise SourceFailed(timeout=False) from e
```

**Deleted:** `_cache`, `fetch_lectionary_year`, `get_readings_for_date` (the nearest-previous logic), `_normalize_date_for_match`, `_liturgical_year_for_date`, `_liturgical_sunday_name`, `get_readings_for_date_string`. The only caller of the last one is the frozen app.py:437, which needs no shim when Streamlit runs from `streamlit-frozen` (F §2.3, §6.1).

**Contingency shim** (only if the F §6.1 item 6 contingency is in force, i.e. Streamlit still runs from `main`). app.py:437-485 passes a display string such as "March 01, 2026" (its default date is `date.today()`, usually a weekday), expects `[]` rather than an exception, reads `rd["liturgical_date"]` and `rd["calendar_date"]`, and defaults to the **last** set. So the shim keeps the old contract exactly:

```python
def get_readings_for_date_string(date_str: str) -> list[dict]:
    d = _parse_legacy_date(date_str.strip())   # "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%d %B %Y"
    if d is None:
        return []
    sunday = d - timedelta(days=(d.weekday() + 1) % 7)       # the Sunday on or before (old normalization)
    from usecases.lectionary import readings_for_date         # local import: avoids an import cycle
    try:
        result = readings_for_date(sunday)
    except Exception:                                        # UpstreamError, InvalidInput, anything
        logger.exception("legacy lectionary shim failed")
        return []
    sets = list(result.reading_sets)
    if result.default_index is not None:                     # app.py picks readings_list[-1]
        sets.append(sets.pop(result.default_index))
    return [{"liturgical_date": s.name, "calendar_date": _legacy_calendar_date(sunday),  # "Mar 01, 2026"
             "first_reading": s.first, "psalm": s.psalm, "second_reading": s.second,
             "gospel": s.gospel, "scriptures": list(s.scriptures)} for s in sets]
```

`_legacy_calendar_date` uses a fixed English month table (not locale `strftime`). The shim ships with `test_legacy_lectionary_shim.py`, a characterization test added in the same PR and deleted with the shim: a display string and an ISO string give the Sunday's sets with exactly the old keys; a weekday string ("October 1, 2026", a Thursday) is looked up as the Sunday before; the default set is last (Easter: Resurrection last); an upstream failure and an unparseable string both give `[]`; plus the F §6.1 `AppTest` smoke test. If the contingency is not in force, none of this is written.

### `usecases/lectionary.py`

```python
@dataclass(frozen=True)
class LectionaryResult:
    date: date; status: Literal["ok", "no_readings"]; partial: bool
    reading_sets: list[ReadingSet]; default_index: int | None

def readings_for_date(d: date) -> LectionaryResult
```

1. If `d.year` is outside 1900–2199, raise `InvalidInput(field="date", message="Enter a date between 1900 and 2199.")`.
2. In parallel, on a module-level `ThreadPoolExecutor(max_workers=4)`:
   - `_LECTIO.get_or_load(d, lambda: load_lectio(d))`, with `TTLCache(maxsize=512, ttl_ok=24 h, ttl_fail=5 min)`;
   - `y = liturgical_year_for(d)`; `_VANDERBILT.get_or_load(y, lambda: load_vanderbilt_year(y))`, with `TTLCache(maxsize=8, 24 h, 5 min)`.

   Each source's outcome is `ok` (a value), `none` (`None` / `[]`, a definitive none cached as an ok value for 24 h) or `failed` (a `SourceFailed`, from the loader or re-raised from the cache). The worst case is ~15 s, down from ~35 s sequential (inv. C1).
3. Compute `v_sets = [s for s in vanderbilt_sets_on(rows, d) if fits_draft_limits(s)]`, filter the Lectio groups the same way, and `sets, default = merge(...)`.
4. Apply the status rules in §API.
   - 502: `UpstreamError("upstream_error", "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.")`
   - 504: `UpstreamTimeout("upstream_timeout", <same message>)`
5. Log one line: date, each source outcome (`ok`/`none`/`failed`/`cached`), set count, duration. Never log payloads.

No database access. The route is user-guarded because the lectionary is global data (inv. C1 "Role").

### Passages (`scripture_fetcher.py`, `usecases/passages.py`)

- **Planning (pure), `plan_parts(reference) -> list[list[str]]`:** `split_alternatives(reference)` gives one section per alternative; each alternative becomes `[normalize_for_fetch(p) for j in split_joined(alt) for p in split_parts(j)]`. The same plan drives fetching, part counting (rate-limit cost) and reassembly.
- `fetch_passage(reference, translation) -> Passage(reference, status, sections)` replaces the dict-returning version (scripture_fetcher.py:143-182): it fetches every part of the plan and derives part, section and passage statuses and texts by the Status rules. The "--- alt ---" text format (line 163) is replaced by structured sections.
- **bible-api part:**
  - cache hit → the cached result, no budget token;
  - otherwise `budget.try_acquire("bible_api")`; no token → `unavailable` (not sent, not cached);
  - `GET https://bible-api.com/{quote(part.lower(), safe=":,-")}?translation=…`, read timeout 10 s;
  - 404 → `not_found`; other failures → `unavailable`.
  - This replaces the minimal `%20` encoding (lines 65-69).
- **ESV part:** `budget.try_acquire("esv")` first (no token → `unavailable`); the parameters are unchanged (lines 91-98), with `q=` the normalized part and a 10 s timeout. `passages: []` → `not_found`.
- **Cache:**
  - bible-api parts: `TTLCache(maxsize=2000, ttl_ok=7 days)`, keyed by `(translation, normalized part)`. A not-found result is cached as ok (24 h is enough; use the same cache with value `NOT_FOUND`). Transient failures are **not** cached, so "Try again" works.
  - **ESV: never cached** (Crossway terms, F §2.7).
- **`plan_passages(refs, translation) -> PassagePlan`** (validation; called by the route before it charges the bucket):
  - `refs == []` or any ref blank after trimming → `InvalidInput(field="refs", "Enter a scripture reference.")`;
  - `translation` not in `available_translations()` → `InvalidInput(field="translation", "Unknown or unavailable translation.")`;
  - more than 20 parts in total → `InvalidInput(field="refs", "Too many passages in one request.")`;
  - returns the trimmed refs, their plans and the flat `parts` list (its length is the rate-limit cost).
- **`load_passages(plan) -> PassagesResult`:**
  - It **flattens every part of every ref into one task list** and submits it to a module-level `ThreadPoolExecutor(max_workers=4)`. Flattening avoids nested submission to the same pool (deadlock). The pool is **shared by all concurrent requests**, so a request can wait behind another's parts.
  - **Per-request deadline:** it waits with `concurrent.futures.wait(futures, timeout=deadline)` where `deadline = 20 s` from the start of the request (injectable for tests). Parts not finished by then are `unavailable`; futures that have not started are cancelled. A request therefore returns within ~20 s however busy the pool is, inside the 30 s client timeout (F §1.8's 20 s worst case now holds per request, not just for an idle pool).
  - The results are then reassembled in order.
- **`get_passage_text(reference, translation) -> str | None`** stays for slice 3: the text of `ok` sections joined, or `None`. It never returns a sentinel (fixes inv. C9: the sentinel leaking into domain code). `usecases/passages.py` re-exports it under the same name, which is the import path slice 3 assumes. It is not rate-limited per user (slice 3 charges its own `ai` bucket) but does draw on the upstream budgets.
- **`translation_options()`** → `default="web"`, `esv_available=esv_configured()`, and `items` from `available_translations()`.

### `usecases/church_profile.py`

`get_church_profile(church_id)` reads `repos.churches.get_church` and returns:
- `timezone`;
- `timezone_valid`: `timezones.is_valid_timezone(tz)` (slice 1), exact and case-sensitive membership in `zoneinfo.available_timezones()`. It is **not** "`ZoneInfo(tz)` succeeds": that accepts values such as `america/new_york` or `posixrules` on some filesystems (macOS) and not others, and 6a's `PATCH /church` would reject them as "Unknown timezone.";
- `bible_translation`: `settings.get("bible_translation")` if it is a non-empty string, else `None`;
- `effective_translation`: that value if it is in `available_translations()`, else `"web"`;
- `effective_translation_label`: `translation_label(effective_translation)`.

This matches the seeding at app.py:371-377. The route passes only `ActiveChurch.id` (F §1.2 rule 1).

### Streamlit coupling removed (inv. §3)

| From | To |
|---|---|
| app.py:69-102 (`_NT_BOOKS`, `_expand_ref_options`, `_is_nt_ref`, `_is_ot_ref`) | `scripture_refs.py` + `src/lib/scripture-refs.ts` |
| app.py:428-464, 481-489 (lectionary load and set switching as session mutations; error lost to rerun) | `usecases/lectionary.readings_for_date` + client draft transitions |
| app.py:371-377, 556-577 (translation default resolved in render) | `usecases/church_profile` + draft `readings.translation` |
| app.py:579-597 (session passage cache; sentinel) | `usecases/passages` + query key `["passage", translation, ref]` |
| vanderbilt_lectionary.py:22, 163-166, 176-178 (process `_cache` that stores failures forever) | `cache.TTLCache` |
| `httpx.get` in both domain modules | `integrations/http.get` |

Nothing under `backend/` imports streamlit.

**Configuration exception (recorded deviation from F §2.3.5).** `scripture_fetcher._esv_key()` keeps reading `ESV_API_KEY` from the environment. The reason: the frozen Settings code (streamlit_views/settings.py:28, 165) and `streamlit_tests/test_settings_prompts_translation.py` call the zero-argument `available_translations()`, and both stay until Streamlit is retired. **Slice 7 owns the move** of the key into `api/settings.py` (its `api/settings.py` row), because slice 7 deletes those frozen callers and their tests; 6a does not take it. The key still never leaves the backend.

### Tenancy notes

- The three new routes are user-scoped. They read no church data, and `X-Church-Id` is ignored.
- `GET /church` stays church-guarded. It adds a read of the validated church row and nothing else.
- No repo signature changes.

---

## Data and migrations

- **No schema change and no Alembic revision.** Slice 2 writes nothing to the database.
- It reads `churches.timezone` (free text; can be invalid, see `timezone_valid`) and `churches.settings["bible_translation"]`. The frozen Streamlit Settings keeps writing both, and the builder picks up changes on the next profile refetch (default staleTime 30 s, and refetch on focus). This fixes "the church default is read once per session" (inv. C8).
- The draft lives only in the browser: `localStorage["wsb:draft:{userId}:{churchId}"]` (F §4.6). The translation override is never archived.
- Shared-data rules (F §6.2) are unaffected. There is no rollback concern beyond reverting code.

---

## Frontend changes

### Routes and files

```
src/app/(signed-in)/(church)/page.tsx            → router.replace("/builder") after slice 1's postLoginPath handling
src/app/(signed-in)/(church)/builder/layout.tsx  → <BuilderShell>{children}</BuilderShell>
src/app/(signed-in)/(church)/builder/page.tsx    → router.replace(`/builder/${draft.last_step}`)
.../builder/readings/page.tsx                    → <ReadingsStep/>
.../builder/{hymns,liturgy,review}/page.tsx      → <StepPlaceholder step=…/> (review adds <StillNeeded/>); replaced by 3, 4 and 5a,
                                                    and 5a deletes StepPlaceholder
src/components/app/app-nav.tsx                   → NEW (F §4.2): links at md+, segmented row below md; "Builder" only
src/components/app/app-header.tsx                → renders <AppNav/> (slice 1's file)
src/components/builder/  BuilderShell, StepHeader, StepProgress, StepFooter, SummaryPanel, SummarySheet,
                         StepPlaceholder, StillNeeded, NewServiceMenuItem
src/components/builder/readings/  ReadingsStep, ServiceDateField, LectionaryStatus, ReadingSetPicker,
                         ReplaceReadingsDialog, OccasionField, ScriptureLinesField, ReadingsList,
                         ReadingRow, PassageText, TranslationSelect, BulletinReadingsPicker
src/lib/dates.ts (+ dates.test.ts, dates.guard.test.ts)
src/lib/scripture-refs.ts (+ scripture-refs.test.ts)
src/lib/use-debounced-value.ts (+ test)
src/lib/draft/  schema.ts store.ts context.tsx migrate.ts mapping.ts status.ts fingerprint.ts
                steps.ts readings.ts date-effects.ts prune.ts (+ tests)
src/lib/queries/  lectionary.ts reference.ts passages.ts (+ ChurchProfile type update in church.ts/types.ts)
```

- Component names are listed above; **file names are kebab-case** like slice 1's (`builder-shell.tsx`, `readings-step.tsx`, `bulletin-readings-picker.tsx`).
- Add `zod` (F §4.11).
- Generate these Base UI components if slice 1 hasn't: `radio-group`, `textarea`, `badge`, `sheet`, `collapsible`, `tooltip`. (`input`, `label` and `alert` come from slice 1; `select`, `dropdown-menu` and `skeleton` already exist from slice 0.)
- Every page is a client component (F §4.1).

### `lib/dates.ts` (F §4.10)

- `parseIsoDate(s) -> {y, m, d} | null`, validated.
- `isValidDateIso(s)`, `addDays(iso, n)`, `weekday(iso)` (0 = Sunday), `isSunday(iso)`.
- `formatServiceDate(iso)` → "October 4, 2026"; `formatLongDate(iso)` → "Sunday, October 4, 2026"; `formatShortDate(iso)` → "October 4".
- `todayIn(tz)`: `Intl.DateTimeFormat("en-CA", {timeZone: tz, year, month, day})`. An invalid or empty `tz`, or `timezone_valid === false`, falls back to the browser zone.
- `nextSunday(iso)`: strictly after the given day.
- `isFirstSundayOfMonth(iso)`: Sunday and day ≤ 7.
- `inSupportedRange(iso)`: year 1900–2199.
- Everything works on calendar fields; nothing calls `new Date("YYYY-MM-DD")`. `dates.guard.test.ts` scans `src/` for it (F acceptance 12).

### `lib/scripture-refs.ts`

A line-for-line port, with the same `BOOKS` data. TypeScript names:

| Python | TypeScript |
|---|---|
| `split_alternatives` | `splitAlternatives` |
| `split_book` | `splitBook` |
| `classify` | `classify` |
| `is_nt_ref` | `isNtRef` |
| `expand_ref_options` | `expandRefOptions` |
| `picker_options` | `pickerOptions` |
| `resolve_readings` | `resolveReadings` |
| `default_reading_pair` | `defaultReadingPair` |
| `default_nt_ref` | `defaultNtRef` |
| `clean_lines` (trim, drop blanks) | `cleanLines` |
| `scripture_key` | `scriptureKey` |

Both suites run `backend/tests/fixtures/shared/scripture_refs.json` (F §5.3). The fetch-only helpers (`normalize_for_fetch`, `split_parts`, `split_joined`) stay in Python.

### Draft store (`lib/draft/`, F §4.6)

- **`schema.ts`:** the zod schema for `DraftV1` exactly as in F §4.6, with `DRAFT_VERSION = 1`.
  - Strings are bounded generously (≤ 20 000) so a stored draft is never rejected for length. UI limits live in the components.
  - `readings.date_iso` accepts `""` or a valid ISO date.
  - `readings.scriptures` holds **raw lines** (blanks allowed while typing). `cleanLines()` derives everything else.
- **`store.ts` / `context.tsx`:** `DraftProvider` lives inside `BuilderShell`. The `(church)` layout's key remount already scopes it per church.

  ```ts
  type DraftApi = {
    draft: DraftV1;
    update: (recipe: (d: DraftV1) => DraftV1) => void; // applies the recipe to the LATEST draft; sets updated_at
                                                         // and schedules the write, unless the recipe returns
                                                         // the same object (then nothing happens)
    replace: (next: DraftV1) => void;                    // New service; 5a's archive load
    setLastStep: (step: StepId) => void;                 // navigation only; see below
    persistence: "ok" | "memory-only";
  };
  export function useDraft(): DraftApi;
  ```

  - Load: parse → `migrate` → validate → `normalizePicks`. On failure, back up to `wsb:draft-corrupt:{userId}:{churchId}`, start fresh, and toast.
  - Write-through with a 400 ms debounce, flushed on `visibilitychange` (hidden), `pagehide` and unmount (church switch).
  - `storage` events for the same key adopt a strictly newer `updated_at` (after `normalizePicks`) and toast.
  - `replace(next)` stores `normalizePicks(next)`.
  - Storage exceptions switch to `memory-only` and show a one-time toast.
  - Every read and write goes through `lib/storage.ts` (slice 1).
  - **`setLastStep(step)`** sets `last_step` when it differs and schedules the normal debounced write, but does **not** bump `updated_at`. So navigating never resets the 30-day prune clock, and because other tabs adopt only a strictly newer `updated_at`, it never triggers "Updated from another tab." (Another tab keeps its own `last_step` in memory and may overwrite it on its next write; the last-visited step is a convenience, not data.) `BuilderShell` calls it in an effect on every step route entry, with the step taken from the pathname. `/builder` then `router.replace`s to `/builder/${draft.last_step}`.
- **`normalizePicks(d)`** (`readings.ts`): sets `selected_ot_ref` / `selected_nt_ref` to `""` when they are not in `pickerOptions(cleanLines(scriptures))` for their side, and returns `d` itself when nothing changes. Called on load, adoption and `replace`, by `commitScriptureLines`, and implied by `applyReadingSet` / `clearReadings` (which clear picks).
- **`freshDraft({church, user, now?})`**, where `church` is the profile (`id`, `timezone`, `timezone_valid`) and `user` is `useMeContext().user`:
  - `date_iso = nextSunday(todayIn(church.timezone))`, `date_origin: "default"`, `fields_origin: "empty"`, `reading_set: null`, empty occasion, scriptures and picks, `translation: null`;
  - hymns `{hymnal: null, exclude_recent: true, slots: all null, alternatives: null}`;
  - liturgy: `sermon_title: ""`, `include_communion = isFirstSundayOfMonth(date_iso)`, `communion_origin: "default"`, the 8 cards `{enabled: key !== "prayers_of_the_people", text: "", origin: "empty"}` except `benediction`, which is `origin: "default"`, and `custom_elements: []`;
  - `last_step: "readings"`, `save_key: crypto.randomUUID()`, `editing: null`, `saved_fingerprint: null`.
- **Mount-time roll-forward:** if `date_origin === "default"`, `date_iso < todayIn(tz)` and `isPristine(draft)`, then `setDate(nextSunday(today), "default")`. A non-pristine draft keeps its date and shows "This date has passed."
- **`prune.ts`** (called once by the `(signed-in)` layout after `/me` loads):
  - removes `wsb:draft:{userId}:*` entries whose `updated_at` is more than 30 days old;
  - removes entries for churches not in `me.churches`;
  - removes the matching `wsb:draft-corrupt:*` keys.
- **`readings.ts`** (pure transitions, each unit-tested):

  | Function | Effect |
  |---|---|
  | `setDate(d, iso, origin = "user")` | Sets `date_iso` and `date_origin`, then runs `onDateChanged(d, prevIso)` from `date-effects.ts`. Slice 2's effect: while `communion_origin === "default"`, `include_communion = isFirstSundayOfMonth(iso)` (false for a weekday). It does not touch the readings fields, `editing` or hymns. |
  | `applyReadingSet(d, lect, i)` | Requires `lect.date === d.readings.date_iso`. Sets `occasion = set.name`, `scriptures = [...set.scriptures]`, `fields_origin: "lectionary"`, `reading_set: {date_iso: lect.date, index: i}`, and clears both picks. |
  | `shouldAutoApply(d, lect)` | True when `lect.date === date_iso`, the status is `ok`, there are sets, and either `fields_origin === "empty"` or (`fields_origin === "lectionary"` and `reading_set?.date_iso !== date_iso`). |
  | `editOccasion(d, s)` / `editScriptureLines(d, raw)` | Stores the value and sets `fields_origin: "user"`. The textarea keeps its raw text, split on `\n`. Picks are not touched while the user types. |
  | `commitScriptureLines(d)` | Runs when the textarea loses focus: `normalizePicks(d)`. (A refresh or tab close while the textarea has focus skips it; the next load normalizes instead, and every consumer resolves through `resolveReadings` meanwhile.) |
  | `clearReadings(d)` | Empty occasion and scriptures, `fields_origin: "empty"`, `reading_set: null`, picks `""`. |
  | `setPick(d, "ot" \| "nt", ref \| "")` | Explicit pick, or `""` for automatic. |
  | `setTranslation(d, id, churchEffective)` | Stores `null` when `id === churchEffective`, so later default changes flow through. |
  | Selectors | `cleanScriptures`; `readingsStale` (`lectionary` origin and `reading_set.date_iso !== date_iso`); `showAvailableBanner(d, lect)` (the rule in UX item 3: sets for this date, none equal to the cleaned scriptures, and `user` with `reading_set?.date_iso !== date_iso` or `archive` with `date_origin !== "archive"`); `selectedSetIndex(d, lect)`; `effectivePicks(d)` = `resolveReadings(d.readings.scriptures, d.readings.selected_ot_ref, d.readings.selected_nt_ref)` (`{ot, nt, otAuto, ntAuto}`; 5a's `docReadings` delegates to the same function, so they cannot differ); `effectiveTranslation(d, church, translations)` (the draft value if it is in the loaded list, else `church.effective_translation`). |

- **`useLectionarySync()`**, mounted in `BuilderShell` so it runs whichever step is showing:
  - it watches `useDebouncedValue(draft.readings.date_iso, 400)`, which starts at the current value (no delay on mount) and then trails every date change by 400 ms (a `replace` included; harmless, and 5a prefetches the loaded date anyway), so intermediate dates typed segment by segment are never looked up or charged to the rate limit;
  - it runs `useLectionary(debouncedDate)`; while `debouncedDate !== date_iso` the status area shows Loading;
  - when data arrives it calls `update(d => shouldAutoApply(d, data) ? applyReadingSet(d, data, data.default_index!) : d)`. The check runs inside the recipe, against the **latest** draft, so a keystroke in the same tick is never overwritten; returning `d` unchanged is a no-op.

  The query key is per date and `applyReadingSet` requires `lect.date === date_iso`, so a late response for an old date never applies to a new one.
- **`status.ts`:**
  - `stepStatus(draft)` per F §4.7;
  - `isPristine(draft)` means "nothing the user would lose", defined by **origins, not text**, so defaults filled by later slices never make a fresh draft look edited (F §4.6: dirty means content *beyond its defaults*):
    - readings: `fields_origin` is `empty` or `lectionary`; both picks `""`;
    - hymns: every slot `null`;
    - liturgy: every card's `origin` is `empty` or `default` (the text of a `default` card, such as slice 4's church benediction, is ignored; an `empty` card has empty text); `communion_origin === "default"`; empty `sermon_title`; no `custom_elements`;
    - `editing === null`.
  - `stillNeeded(draft, SHIPPED_STEPS)`.
- **`steps.ts`:** `STEPS` (id, label, href, next and previous) and `SHIPPED_STEPS = new Set(["readings"])`. Slice 3 adds `"hymns"`, slice 4 `"liturgy"` and 5a `"review"` (Hand-offs); an unshipped step shows "Soon" (Review: "Not in archive") and `stillNeeded` ignores it.
- **`mapping.ts`** (provisional; **5a owns and replaces it**): `draftToServicePayload(draft)` per F §4.6. It takes only the draft, matching 5a's signature.
  - Trimmed, non-blank scriptures.
  - **Picks:** `selected_ot_ref` / `selected_nt_ref` are the explicit values of `resolveReadings(...)`, i.e. `otAuto ? "" : ot`. A pick that is no longer an option is sent as `""`, whatever the stored draft says. 5a's replacement must keep this.
  - Enabled non-empty cards → `liturgy`; slot-keyed hymns; `hymnal`; `custom_elements` without `id`.
  - Typed as a hand-written `ServiceDraftPayload` matching inv. §2.1 plus `hymnal` (F §1.3).
  - Slice 2 uses it only for `fingerprint`.
- **`fingerprint.ts`:**
  - `fingerprint(payload)`: FNV-1a over stable JSON.
  - `isDirty(draft)`: `saved_fingerprint === null ? !isPristine(draft) : fingerprint(draftToServicePayload(draft)) !== saved_fingerprint`. In slice 2 nothing is saved yet, so dirty means not pristine.

### Queries (TanStack Query, F §4.4)

| Hook | Key | Client | Options |
|---|---|---|---|
| `useLectionary(dateIso)` | `["lectionary", dateIso]` | `api.user` | `enabled: isValidDateIso && inSupportedRange`; `staleTime: q => q.state.data?.partial ? 5 * 60_000 : 24 * 3_600_000`; `retry: 0`; timeout 25 s |
| `useTranslations()` | `["ref", "translations"]` | `api.user` | `staleTime: Infinity` |
| `usePassage(ref, translation, enabled)` | `["passage", translation, ref]` | `api.user` | POST `{refs: [ref], translation}` through `passageLimiter` (3 in flight; the 30 s timeout starts when the request is sent). The `queryFn` **never throws for an upstream miss**: every 200 is returned as data, including `not_found` and `unavailable` passages and partial sections, and the row renders it by the precedence table in UX item 6. `staleTime: q => q.state.data?.status === "unavailable" ? 0 : 24 * 3_600_000`, so a transient miss is refetched on the next expand or focus, while "Try again" calls `refetch()`. Real request errors (network, timeout, 5xx, 429) keep the default handling and `retry`. The module also exports `passageText(p)` for slice 3. |
| `useChurchProfile()` (slice 1) | `["church", id, "profile"]` | `api.church` | Type widened to `ChurchProfileOut` |

"Show all text" sets every row's expanded state. Only expanded rows fetch, TanStack dedupes, and `passageLimiter` (a module-level promise queue, `createLimiter(3)`, unit-tested) keeps at most 3 passage requests in flight, so "Show all text" on 20 rows never queues 20 requests on the server's shared pool at once. API types come from the regenerated `schema.d.ts` (F §1.11), for example `type Lectionary = components["schemas"]["LectionaryOut"]`.

---

## Behavior changes vs Streamlit

1. **Step-by-step builder.**
   - Each step has its own URL and a progress indicator, and there is a desktop summary panel (decision 1).
   - The unsaved draft is kept per user and church in the browser across refresh, church switch and logout.
   - Streamlit kept one page and session state that leaked between churches (inv. A7). The switcher reset list also missed `occasion`, `scriptures_text` and the lectionary keys.
2. **Default date** is the next Sunday, strictly after today, in the church's timezone. Streamlit used today on the server, which is UTC on Railway (inv. C1).
3. **Any date is looked up as itself.** There is no normalization to the previous Sunday (vanderbilt_lectionary.py:357) and no "nearest previous row" fallback (247-254). Weekday feasts return their own readings. A date with no readings shows the manual-entry prompt (decision 8).
4. **Lectionary failures are visible and retryable.** Streamlit's error disappeared on rerun, and a failure looked like "no readings" (inv. C1). Failures are cached for 5 minutes instead of forever (inv. C2).
5. **Typed input is never destroyed.**
   - A date change no longer blanks occasion and scriptures (app.py:456-460). Lectionary-filled fields are replaced automatically; typed or archived fields get a "Readings for … are available" banner with a confirmation, but only when the fields did not come from this date's lectionary or archived service; editing this date's readings never raises it.
   - When there are no readings or the lookup fails, stale lectionary fields stay and a "Clear readings" button is offered.
   - Switching reading sets over edited readings asks first (inv. C4).
6. **The reading-set switcher is keyed by index**, so sets with duplicate names no longer collapse (inv. C4). It reflects the *current* date's sets, including after 5a loads an archived service (the stale-lectionary fix, inv. F6).
7. **Merge rule.**
   - Vanderbilt decides which sets exist when it has rows; Lectio supplies the readings for the set whose Gospel it matches.
   - The default is the matched set, else the last set (parity).
   - Effects: Easter no longer gets a duplicate 4th set; Trinity Sunday no longer defaults to the Proper 4 readings; Ascension no longer shows Lectio's wrong Gospel.
8. **Occasion names.**
   - Ordinary Sundays show the Vanderbilt name ("Proper 22 (27)") instead of "Ordinary Time — Year A".
   - Weekday feasts get real names ("Ash Wednesday", "Good Friday").
   - Computed fallback names gain Pentecost, Trinity and Reign of Christ, and never give a Sunday name to a weekday.
9. **Liturgical-year boundary** is computed from Advent 1, which fixes 2027-11-28 (inv. C2).
10. **Vanderbilt cells:** a compound "reading + Psalm" cell becomes two lines, and the leading "* " is removed. The Easter Vigil's single 517-character cell becomes 11 reading lines without its headings; every lectionary line now fits the 200-character limit.
11. **Lectionary sources are fetched in parallel** (worst case ~15 s instead of ~35 s).
12. **Passage text.**
    - It loads per reading on demand, plus a "Show all text" button. There is no page-wide sequential fetch.
    - Alternatives show as separate sections instead of "--- alt ---" text.
    - References are normalized before fetching (a/b verse parts, en dashes, parentheses, "*"), which fixes silent failures for many RCL citations.
    - The " or " split is case-insensitive.
    - "Not found" and "unavailable" have different messages; the `[Could not load text]` sentinel is gone. Parts that loaded are shown even when another part failed.
    - Public-domain text is cached on the server for 7 days; ESV is never cached.
    - Upstream calls are budgeted per user (per part) and per process (bible-api's and Crossway's published limits), so one user can't exhaust the shared IP or ESV key.
13. **Translation.**
    - The override persists in the draft instead of the session.
    - The church default is re-read from the profile query instead of once per session (inv. C8).
    - The picker shows even when the scripture list is empty.
14. **OT/NT classification.**
    - Recognizes abbreviations and the deuterocanon.
    - Separates Psalms.
    - Splits " or " case-insensitively.
15. **Bulletin readings.**
    - An empty pick shows "Automatic: {ref}". The automatic NT reading is the first NT line other than the OT reading (the pick, if one is set), never the Psalm. The automatic OT reading stays the first line (parity; 5a holds the open question).
    - The docx uses the same function (`resolve_readings`) from 5a on, so the screen and the document always agree. Today an empty NT pick prints `scriptures[1]`, which in RCL order is the Psalm (worship_service.py:881).
    - A pick that no longer matches a line is treated as automatic everywhere, including in the payload and the docx, and is removed from the draft when the field loses focus, on load and on archive load. Streamlit reset it on the next rerun but could save a stale value (app.py:598-631; inv. C10).
16. **Copy.**
    - The stale "Edit the Scripture list in the sidebar" captions are dropped (inv. C7).
    - The scripture help example uses a hyphen, not an en dash (inv. C6).
    - The on-screen date reads "October 4, 2026" instead of the zero-padded form. The stored display string is unchanged (5a).
17. **Limits.** At most 20 readings of 200 characters each and a 300-character occasion, with inline messages. Streamlit had no limits.
18. **Unchanged on purpose.**
    - Lectio alternative citations are still dropped (inv. C2).
    - Duplicate scripture lines are allowed.
    - Unknown books still appear in the OT picker.

---

## Testing

### Backend (pytest from the repo root; no network, F §5.1)

Fixtures in `backend/tests/fixtures/`, recorded by `scripts/record_fixtures.py`:
- **`lectio/`:** the dates in the merge table; the 404 bodies for 2026-04-03, 2026-01-01, 2026-11-26 and 2026-09-29; an HTML 200; a 500.
- **`vanderbilt/`:** trimmed `2025-26.csv` containing the rows those dates use, **including the full Easter Vigil row** (verbatim); `2026-27.csv` and `2027-28.csv` stubs with the Advent 1 rows (Nov 29, 2026 and Nov 28, 2027); a 404 HTML body; an HTML 200.
- **`bible_api/`:** a success, a 404, a comma-list reference, and `esv/` success and empty.
- **`shared/`:**
  - `scripture_refs.json`: `classify`, `is_nt_ref`, `expand_ref_options`, `picker_options`, `default_reading_pair` and **`resolve_readings`** cases, including every example in this document, abbreviations, roman numerals, deuterocanon, `unknown`, case-insensitive " or ", an " or " line printed whole, **mixed cases** (an explicit OT pick with an automatic NT, including Easter with OT = Psalm 118 → NT Acts and a list starting with an epistle; an explicit NT pick with an automatic OT), **stale picks** (a pick that is no longer a line; a pick on the wrong side) → automatic, and every case in 5a's `doc_readings.json` (5a's resolver delegates to `resolve_readings`, so they must agree);
  - `next_sunday.json` (TypeScript only): 2026-09-25 → 2026-09-27; 2026-09-27 → 2026-10-04; 2026-12-31 → 2027-01-03; 2026-09-26 → 2026-09-27.

| File | Cases |
|---|---|
| `test_scripture_refs.py` | The shared fixture; `split_book` (longest alias, "1 John" vs "John", "1john", "I Cor.", "Song of Songs"); `normalize_for_fetch` (9a, 4b, 35b, en dash, "(15-20)", ", (15-20)", "John 1:(1-9), 10-18", leading "*"); `split_parts` (book carry); `split_joined` ("Genesis 1:1-2:4a and Psalm 136:1-9, 23-26" → 2; "Psalm 42 and 43" → 1); `scripture_key` equality ("Luke 2:1-14 (15-20)" == "Luke 2:1-14, (15-20)") |
| `test_lectionary_domain.py` | `liturgical_year_for` boundaries; `advent_sunday` 2025–2028; `parse_vanderbilt_csv` (header found, HTML raises, unparseable dates skipped); `clean_cell` (compound split, "* ", http dropped, "Psalm 105:1-11, 45b or Psalm 128" kept whole as the psalm part, **the verbatim Vigil cell → exactly the 11 reading lines, headings dropped, "Ezekiel 36:24-28 and Psalm 42 and 43" kept whole**); `fits_draft_limits` (21 lines, a 201-character line and an empty set are rejected; a rejected set is dropped before `merge` and the default index is computed without it); **invariant: every set returned for every fixture date has 1–20 lines of 1–200 characters**; `vanderbilt_sets_on` (exact only; no row → []); `parse_lectio_payload` (alternatives skipped; Trinity gives 2 groups; empty → None); `sunday_name` (every case listed, Pentecost 2026-05-24, Trinity 2026-05-31, Reign of Christ 2026-11-22, a weekday → None, Ascension Thursday → None); `weekday_feast_name`; `lectio_set_name` precedence and de-duplicated names; **`merge` for every row of the merge table** |
| `test_usecase_lectionary.py` | Uses `respx` against the fixtures. Both ok → merged; Lectio 404 + Vanderbilt row → ok; both none → `no_readings`; one failed + sets → `partial`; both failed → `UpstreamError`; all failures timeouts → `UpstreamTimeout`; Lectio HTML 200 → failed; Lectio 200 JSON that doesn't decode → failed; Vanderbilt HTML 200 → failed; Vanderbilt 404 → none. Cache (fake clock): a second call within 24 h makes no request; **a Vanderbilt 404 is cached as none for 24 h** (no second request; `status: "no_readings"` when Lectio also has none); **a Vanderbilt HTML 200 is cached as a failure for 5 min** (no second request inside 5 min, one after); a Lectio 500 is cached 5 min then retried; a Lectio 404 is cached 24 h; an unexpected exception from a loader is not cached (the next call runs the loader again). Single-flight: two threads cause one upstream call. The sources are requested concurrently. Year out of range → `InvalidInput(field="date")`. |
| `test_legacy_lectionary_shim.py` | **Only if the F §6.1 item 6 contingency is in force** (see "Contingency shim"): old keys; display and ISO strings; weekday → Sunday before; default set last; failure and unparseable → `[]`. |
| `test_scripture_fetcher.py` | Ported from `test_scripture_translations.py`, which is replaced: its assertions move to `respx` because `sf.httpx.get` is no longer the call site. ESV gating and labels; routing (ESV header `Token …`; bible-api `translation=`); URL quoting of a normalized part; alternatives → sections; `;` parts joined; `split_joined` parts fetched separately; **part, section and passage statuses** (all ok; one of two `;` parts 404 → section `not_found` with the other part's text; one part 500 → section `unavailable` with the other part's text; one alternative ok and one unavailable → passage `unavailable`, the ok section's text returned; all 404 → `not_found`, text `None`); budget exhausted → `unavailable`, not sent, not cached, a cache hit still served; bible-api text cached (fake clock, 7 days); a not-found result cached; transient failures not cached; ESV never cached (two calls → two requests); `get_passage_text` returns None, never a sentinel, and ignores non-`ok` sections. |
| `test_usecase_passages.py` | `refs == []` and a blank ref → `InvalidInput(field="refs", "Enter a scripture reference.")`; 21 parts → `InvalidInput(field="refs", "Too many passages in one request.")`; unknown or unavailable translation (ESV without a key) → `InvalidInput(field="translation")`; `plan.parts` counts alternatives × joined × `;` parts; order preserved; **two concurrent requests** of 4 refs × 3 parts never exceed 4 in-flight upstream calls in total (a counting transport); with a slow transport and a 0.2 s injected deadline, both requests return by their deadline with the unfinished parts `unavailable` and not-started futures cancelled. |
| `test_cache.py`, `test_ratelimit.py`, `test_budget.py`, `test_http_client.py` | TTL expiry, LRU eviction, uncached exceptions. Bucket refill; per-user isolation; the church rule for `ai`; an exhausted bucket raises `domain_errors.RateLimited` (not `ApiError`) with `retry_after_seconds` = the ceiling of the wait, and the response carries `Retry-After` and `details.retry_after_seconds`; `cost=3` charges 3 and a failed charge takes nothing. Upstream budgets: 15 bible-api acquisitions in 30 s succeed and the 16th fails, then refills (fake clock); ESV's minute, hour and day rules are all enforced; shared across users. User-Agent; non-https refused (also after a redirect); per-call read timeout. |
| `test_api_lectionary.py` | 401 without a token; 200 shape (the Palm Sunday example); `X-Church-Id` ignored, and a user with zero churches gets 200; 422 bad date with `fields.date`; 422 out of range with the exact message; 502 and 504 with the exact message; 429 after 120 calls in the window, with `Retry-After`, `details.retry_after_seconds` and `access-control-allow-origin` for an allowed origin |
| `test_api_scripture.py` | 200 per-passage and per-section statuses; 422 for 5 refs, a 201-character ref (Pydantic), `refs: []`, a blank ref, 21 parts and an unknown translation (exact messages, `fields`); rate limit charged per part: 60 one-part calls then the 61st → 429, and after 20 three-part calls the 21st → 429; a 422 charges nothing; an extra field → 422 (`extra="forbid"`) |
| `test_api_translations.py` | Without `ESV_API_KEY`: no esv and `esv_available: false`; with it: esv last |
| `test_api_church_profile.py` | New fields, including `effective_translation_label`; `timezone_valid` false for "Eastern" and for the wrong-case "america/new_york", true for "America/New_York"; stored "esv" without a key → effective "web"; unset → `bible_translation: null`, effective "web"; `assert_church_isolated` for `GET /church` (non-member → 403; a member of A sending B's id → 403, since the church comes only from the header); every role (owner, admin, member) → 200 |
| `test_api_churches.py` (slice 1 file) | Burst guard (fake limiter clock): the 4th `POST /churches` within one minute → 429 `rate_limited` "Too many requests. Try again in {n} seconds." with `Retry-After` and `details.retry_after_seconds`; after the clock advances 60 s the next create succeeds. **Slice 1's 6th-create test is kept passing:** it advances the limiter clock 60 s between creates, and the 6th create in 24 h still returns slice 1's cap message "You've created 5 churches in the last 24 hours. Try again later." |
| `test_route_guards.py` | `/lectionary/readings`, `/translations` and `/scripture/passages` in `USER_SCOPED`; `/church` church-guarded |
| `test_openapi_contract.py` | Snapshot regenerated |

### Frontend (Vitest 3; `unit` and `dom` projects, F §5.2)

| File | Cases |
|---|---|
| `lib/dates.test.ts` | `next_sunday.json`; `todayIn` at `2026-09-27T02:30Z` → LA "2026-09-26", UTC "2026-09-27", and an invalid tz falls back; formats; `isFirstSundayOfMonth` (2026-10-04 true, 2026-10-11 false, 2026-10-01 Thursday false); invalid ISO strings |
| `lib/dates.guard.test.ts` | F acceptance 12 |
| `lib/scripture-refs.test.ts` | `scripture_refs.json` read with `fs` from `../backend/tests/fixtures/shared/` (includes the `resolve_readings` mixed and stale-pick cases) |
| `lib/use-debounced-value.test.ts` | Initial value immediate; trails changes by 400 ms; only the last of several quick changes is emitted (fake timers) |
| `lib/queries/passages.test.ts` | `createLimiter(3)`: a 4th task waits until one settles; a rejection frees its slot. `passageText` joins only `ok` sections and returns null when there are none. |
| `lib/draft/schema.test.ts`, `migrate.test.ts` | Round-trip; corrupt JSON, schema-invalid data and a future version → backup key written, fresh draft, toast |
| `lib/draft/readings.test.ts` | Every transition and selector. `shouldAutoApply` for each origin. Stale detection. Auto-apply replaces the lectionary fields of an old date but never `user` or `archive` fields. Picks reset on apply. The communion effect only while its origin is `default`. `setTranslation` stores null when the value equals the default. `effectivePicks` never returns a Psalm as NT, and with the Easter lines and OT pick Psalm 118 gives NT Acts (as `resolveReadings` does). `normalizePicks` / `commitScriptureLines` clear only picks that are no longer options and return the same object otherwise; `editScriptureLines` never clears picks. **`showAvailableBanner`:** `user` after a date change → shown; `user` after editing a line of this date's set (same `reading_set.date_iso`) → **not** shown; `user` typed with `reading_set: null` and sets for this date → shown; `archive` on its archived date (`date_origin: "archive"`) → not shown; `archive` after a date change → shown; `empty` / `lectionary` → never. |
| `lib/draft/store.test.ts` | Debounced write; flush on `pagehide`; the key includes the user and church; a `storage` event with a newer `updated_at` is adopted (and its stale picks normalized) and one with an equal `updated_at` is not; quota exception → `memory-only`; roll-forward of a pristine past default date (**including one whose benediction card holds default text**) and not of a non-pristine one; `update` with a recipe that returns the same object neither bumps `updated_at` nor writes; the auto-apply recipe sees the latest draft (an occasion edit dispatched in the same tick survives); `setLastStep` changes `last_step`, writes, and leaves `updated_at` unchanged; **a stored draft with a stale `selected_ot_ref` (as left by a refresh while the textarea had focus) loads with `selected_ot_ref === ""`, and `draftToServicePayload` of the un-normalized draft also sends `""`**; `replace` normalizes picks. |
| `lib/draft/prune.test.ts` | Drafts older than 30 days removed; drafts for churches left removed; another user's keys untouched |
| `lib/draft/status.test.ts`, `mapping.test.ts`, `fingerprint.test.ts` | "2 of 3"; `stillNeeded` limited to shipped steps; `isPristine`: a fresh draft → true; **a fresh draft with the benediction card `{text: "Halverson", origin: "default"}` → true**; a card with origin `typed`, `ai` or `archive` → false; `communion_origin: "user"` → false; a pick, a hymn slot, a sermon title, a custom element, `editing`, or `user` fields → false. The provisional payload trims and drops blanks and sends a stale pick as `""`; fingerprint is stable under key order; `isDirty` with and without `saved_fingerprint`; a fresh draft with the default benediction text is not dirty. |
| `builder/builder-shell.test.tsx` | The four routes render inside the shell; StepProgress status and "Soon" for steps not in `SHIPPED_STEPS`; the summary's Hymns and Liturgy blocks say "Available soon" (slices 3, 4 and 5a change these assertions when they turn their steps on); footer links; the Summary sheet opens below `lg` (the `matchMedia` shim); New service confirms only when not pristine; **visiting `/builder/hymns` then `/builder` redirects to `/builder/hymns`**, and that navigation leaves `updated_at` unchanged; `AppNav` shows "Builder" as a link row at `md` and a segmented row below it |
| `builder/readings/readings-step.test.tsx` (`installFakeApi`) | Fresh draft → `GET /lectionary/readings?date=<next Sunday>` with no `X-Church-Id`, and the fields fill. Two sets → radio cards, and choosing one applies it. After typing in Occasion, changing the date shows the "available" banner instead of replacing, and "Use them" → confirm → replaced. **Deleting the Psalm line of the auto-filled set on the same date shows no banner.** Changing the date twice within 400 ms (fake timers) → one request, for the last date. `no_readings` → prompt with "Enter readings", focus stays on the date input, and clicking "Enter readings" focuses Occasion. 502 → ErrorState, and "Try again" refetches. 429 → the rate-limit ErrorState with "Try again" disabled until `Retry-After` elapses. The stale note plus "Clear readings". Out-of-range year → no request. Expanding a row POSTs `{refs: [ref], translation}`; `not_found`, `unavailable` and a partial response (one section with text, one `unavailable`) show their copy, the partial one with its text, "Part of this passage couldn't be loaded." and "Try again", which refetches. A line over 200 characters has "Show text" disabled and sends nothing. "Show all text" on 5 rows keeps at most 3 requests in flight. Changing the translation refetches expanded rows. `/translations` failing → the select is disabled and shows `effective_translation_label`. Bulletin selects show "Automatic: Philippians 3:4b-14" and never a Psalm; picking OT "Psalm 118:1-2, 14-24" on the Easter lines changes the NT placeholder to "Automatic: Acts 10:34-43". |
| `builder/readings/church-switch.test.tsx` | Edit under church A; remount under church B → B's fresh draft; back to A → A's edits restored |

### Manual checks (append to `docs/manual-verification.md`; at 375 px and on desktop, on the production URL)

1. A new church with no draft opens `/` → `/builder/readings`, dated next Sunday in the church's timezone, with the occasion and readings filled.
2. Change the date to Ash Wednesday 2027 (2027-02-10): "Ash Wednesday". Good Friday 2027 (2027-03-26): readings found. Thanksgiving (2026-11-26): four lines. A plain Tuesday: the manual-entry prompt, plus the stale note with "Clear readings".
3. Palm Sunday 2027 (2027-03-21): two set cards, with the Passion set selected.
4. Type an occasion, change the date: the banner appears; "Use them" asks first. On a date whose readings auto-filled, delete the Psalm line: no banner.
5. Easter Day 2026 (2026-04-05): choose the Easter Vigil set: 11 lines, no heading lines, no "too long" message; "Show text" on "Romans 6:3-11 and Psalm 114" loads both passages.
6. Type a date on desktop digit by digit: one lookup (network tab), and focus never jumps to Occasion.
7. Refresh on every step: the draft is kept. A second tab edits: the first tab shows "Updated from another tab." Switch church and back: the drafts are separate.
8. Open "Isaiah 50:4-9a": text loads. Switch the translation: the text changes. ESV appears only if configured.
9. Bulletin readings: automatic NT is the epistle, never the Psalm. Easter-season dates: OT automatic is the first line (Acts), NT automatic is the epistle; pick the Psalm as OT and the NT placeholder becomes Acts. Edit a picked line and leave the field: the pick returns to automatic. Edit a picked line and refresh without leaving the field: after reload the pick is automatic.
10. Navigate to Hymns, then open `/builder`: it lands on Hymns. With a second tab open, navigating steps in one tab shows no "Updated from another tab." in the other.
11. With the network off (devtools offline) on a new date: the error card; "Try again" recovers.
12. At 375 px: no horizontal scroll; the footer is sticky above the home indicator; inputs don't zoom on iOS. On desktop: the summary is sticky on the right.
13. Regression: sign in, switch church, open the Builder nav item; Streamlit smoke check (F §6.3).

---

## Acceptance criteria

1. `GET /lectionary/readings` returns the merge-table results for every recorded date, including weekday feasts and `no_readings` for 2026-09-29. It never normalizes the date, and the response `date` equals the request. Every returned set has 1–20 lines of 1–200 characters; the Easter Vigil gives 11 lines without headings. *(test)*
2. When both sources fail, it returns 502 `upstream_error`, or 504 `upstream_timeout` when every failure was a timeout, with the exact message. One failed source with sets present returns 200 with `partial: true`. *(test)*
3. Lectionary successes (including definitive 404s) are cached 24 h and failures (including an HTML 200) 5 min, per source, single-flight; the loaders convert every expected failure to `SourceFailed`. No module-level dict cache remains in `vanderbilt_lectionary.py`. *(test + grep)*
4. `liturgical_year_for(2027-11-28) == "2027-28"` and `liturgical_year_for(2026-11-28) == "2025-26"`. `sunday_name` returns None for every non-Sunday. *(test)*
5. `POST /scripture/passages` returns per-passage and per-section `ok` / `not_found` / `unavailable`, with the text of every part that loaded. "Isaiah 50:4-9a" is requested as `isaiah 50:4-9`. ESV text is never cached, and public-domain text is cached for 7 days. Each request answers within its 20 s deadline however many requests share the pool, and upstream calls stay within the process-wide bible-api and ESV budgets. *(test)*
6. `GET /translations` hides ESV without a key. `GET /church` returns `timezone`, `timezone_valid` (slice 1's `is_valid_timezone`, so "america/new_york" is invalid), `bible_translation`, `effective_translation` and `effective_translation_label`, and `/me`'s church items are unchanged. *(test + OpenAPI snapshot)*
7. Rate limits: the 121st lectionary call, the passages call that would exceed 60 upstream parts, or the 4th church creation within one minute returns 429 `rate_limited` with `Retry-After`, `details.retry_after_seconds` and CORS headers, raised as `domain_errors.RateLimited` (no `ApiError.headers`). Creates spaced more than a minute apart are never stopped by the bucket, so the 6th within 24 h still gets slice 1's cap message. *(test)*
8. `scripture_refs` in Python and TypeScript pass the same shared fixture. `resolve_readings` never returns a Psalm as the automatic NT reading, handles one explicit pick plus one automatic side, and treats a stale pick as automatic; `effectivePicks` and the provisional payload use it, and 5a's resolvers are specified to delegate to it. The payload never carries a pick outside the current options, whatever the stored draft holds (including after a refresh while the textarea had focus). *(test)*
9. The three new routes are in `USER_SCOPED`, and `test_route_guards.py`, `test_openapi_contract.py` and the `gen:api` diff check pass. *(CI)*
10. F acceptance 10: the draft persists per user and church, survives refresh, migrates or discards bad data (with a backup key and a toast), is kept across church switch and logout, and is pruned after 30 days and for churches the user left. *(test)*
11. F acceptance 11: all four builder routes render inside the shell with progress, the sticky mobile footer and the desktop summary panel. There is no horizontal scroll at 375 px. *(test + deployed)*
12. F acceptance 12: a fresh draft defaults to the next Sunday in the church's timezone, and `dates.guard.test.ts` passes. *(test)*
13. F acceptance 13: `ratelimit.py`, `integrations/budget.py`, `cache.TTLCache` and `integrations/http.py` exist, and the no-network guard is active. *(test)*
14. Auto-fill replaces only `empty` or `lectionary` fields, checked against the latest draft. `user` and `archive` fields are replaced only through a confirmed "Use them" or a set choice. The "Readings available" banner never appears after an edit to readings that came from this date's lectionary or archived service. A failed or empty lookup never changes the fields. Date lookups are debounced 400 ms and never move focus. *(test)*
15. The set switcher is keyed by index and shows the current date's sets. With a draft of `fields_origin: "archive"` and `reading_set: null`, the step fetches that date's sets and does not overwrite the fields. *(test)*
16. Passage text loads only for expanded rows, with at most 3 requests in flight. Changing the translation changes the fetched text. "Not found", "unavailable" and the partial state show their exact copy, and "Try again" refetches. *(test)*
17. `/` redirects to `/builder`; each step writes `last_step` on entry without bumping `updated_at`, and `/builder` redirects to it; `AppNav` exists and shows "Builder". `isPristine` stays true for a fresh draft whose default benediction text is filled. *(test + deployed)*
18. The manual checklist passes on the production URL, and Streamlit still loads the tester's church. *(deployed)*

---

## Risks and open questions

**Risks**
- **Upstream data quality.** Lectio has wrong or interleaved data on some days; Vanderbilt has two-track cells and unordered rows. Mitigations:
  - Vanderbilt decides the set list; Lectio supplies readings only where the Gospels match; everything is fixture-tested.
  - If Vanderbilt is down on such a day, Lectio's set shows with `partial: true`. The fields are editable.
  - When Lectio is down on an ordinary Sunday, the two-track Vanderbilt cells give about six lines instead of four. The user deletes the lines they don't use; this does not raise the "Readings available" banner.
  - A future Vanderbilt cell in a shape nobody has seen could still break the draft limits. `fits_draft_limits` drops such a set (logged) rather than returning lines the draft can't hold.
- **Vanderbilt from Railway.** The source comment says it "often returns 403 or HTML". With per-year caching, one successful fetch serves the whole year for 24 h. Lectio still covers Sundays and several feasts. A 200 HTML page for a far-future year makes that date report "couldn't be reached"; this is accepted.
- **Failure TTL.** A cached failure makes "Try again" return the same error for up to 5 minutes. The copy says "in a few minutes", and manual entry is always available.
- **Reading-set indices can shift** when a partial result later becomes complete. The selection is derived from matching scriptures first, so the UI stays correct. `reading_set.index` is used only when the fields were edited.
- **Python/TypeScript classifier drift.** Mitigated by the shared fixture, which both CI jobs run.
- **Shared upstream budgets.** With bible-api at 15 calls per 30 s for the whole app, "Show all text" on a long set (the Easter Vigil, ~25 parts) can leave some rows "unavailable" until "Try again"; the 7-day cache makes repeats free. Acceptable at the current user count; revisit if many churches use the app at once.
- **5a must delegate.** The screen/docx agreement depends on 5a's `resolve_doc_readings` and `docReadings` calling `resolve_readings` / `resolveReadings`, and on 5a's `draftToServicePayload` keeping the valid-picks rule. Both are stated in the hand-offs; the shared fixture catches a divergent reimplementation only for the cases it lists.
- **Configuration deviation** (`ESV_API_KEY` read from the environment) until slice 7 moves it, as recorded above.
- **Turning on steps 2–4 has named owners.** Slice 3 adds `"hymns"`, slice 4 `"liturgy"` and 5a `"review"` to `SHIPPED_STEPS`, each replacing its `SummaryPanel` block or status line and adding a DOM test that the summary no longer says "Available soon"; 5a deletes `StepPlaceholder` (Hand-offs). Slice 7's `Available soon` source guard is only the backstop.

**Open questions for the owner** (not covered by decisions 1–9)
1. **Occasion names for ordinary-time Sundays.** This design prints the RCL designation "Proper 22 (27)". Today the app shows "Ordinary Time — Year A". Many bulletins say "Nineteenth Sunday after Pentecost". Is "Proper 22 (27)" acceptable as the auto-filled default? The field is always editable. The alternative is to compute "Nth Sunday after Pentecost" for Propers, which is small but adds a naming table.
2. **Saturday vigil and Sunday-eve services.** Vanderbilt lists the Easter Vigil on the Sunday date, so a Saturday service date finds nothing and falls back to manual entry (decision 8). Should a Saturday offer a one-tap "Use Sunday {Month D}'s readings"? The default is no; it can be added later without changing the draft shape.
