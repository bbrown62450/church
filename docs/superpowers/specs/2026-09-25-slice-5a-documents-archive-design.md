# Slice 5a: Review step, Word documents and service archive — Design

**Date:** 2026-09-25
**Status:** Draft
**Depends on:** ops, 1, 2, 3, 4 (exact interfaces in "Interfaces assumed" below). Consumed by 5b.
**Size:** L. Ship as two PRs: **5a-1** backend (additive API plus migration `0005`), then **5a-2** frontend.

**Inputs:**
- Foundations: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, cited as "F§n". This spec follows it and does not restate its conventions.
- Inventory: `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md`, cited as "inv". Covers F1-F7, §2.2 (`/services`, `/documents`), §3 (the app.py rows for 978-1092, 1029-1067, 379-405 and 520-543), §4 ("Concurrency", "File downloads", "Schema, migrations, coexistence", "Content hazards"), and §5 row 5a.
- Owner decisions 4, 5 and 9, restated where they shape the design.

---

## Goal

Complete step 4 of the builder, "Review & send", except for email. The user can:
1. check what is still missing;
2. save the service to the church's archive, or save changes to an archived service;
3. download the **bulletin copy** and the **pastor's copy** as Word files, built on demand from the current draft.

Add the **Services** page, where members browse the archive, open a saved service into the builder, and delete a service after confirming.

With 5a in place, the archive keeps everything a service needs to rebuild its documents: custom elements and the hymnal are now saved, and hymns are stored by slot. Hymn usage is now recorded when a service is saved, instead of by the "Prepare" button. Deleting a service leaves usage alone (open question 1).

## Scope / Out of scope

**In scope**

| Inventory item | What 5a does with it |
|---|---|
| F1 Prepare bulletin / pastor's copy (app.py:978-1028) | Replaced by two Download buttons that build the file on demand (`POST /documents`). There is no "Prepare" step. |
| F2 Word layout (`build_docx`, worship_service.py:783-948) | Kept section for section. Hymns map by slot, `#None` is fixed, the NT fallback is fixed, and the unused parameters are removed. |
| F3 Download (app.py:1069-1092) | Filenames stay the same. There are no stale bytes. The caption is corrected. |
| F4 Hymn usage recording | Moves from Prepare to **Save**. Saving replaces the saved date's usage rows (owner decision 9). Nothing else removes usage: deleting a service, or moving it to another date, leaves the old date's rows as they are (open question 1). |
| F5 Archive list (app.py:520-543) | Becomes the `/services` page, with paging and delete. |
| F6 Load an archived service (app.py:379-405) | `serviceToDraft` replaces the whole draft, and the readings step then reloads the lectionary for the loaded date. |
| F7 Save / Save changes (app.py:1029-1067) | `POST` / `PUT /services`, with `If-Match` and usage recorded in the same transaction. |
| E7 read-only preview | Becomes an "Order of worship" outline on the Review step, matching the Word file. Card editing belongs to slice 4. |
| inv §4 "Concurrency": `record_usage` race, last-write-wins `update_service`, non-atomic save-then-usage | Fixed (F§7.4). |
| inv §4 "File downloads" | Blob fetch, exposed `Content-Disposition`, python-docx failure becomes a logged 500 (F§1.9). |
| Migration `0005_services_extras`, including the index `ix_services_church_date` | F§3.5. The file number follows merge order (see "Data and migrations"). |
| Frontend foundations F§7.2 row 5a | `apiFetchBlob`, download helper, `docxFilename`, `If-Match`, `serviceToDraft` / `draftToServicePayload`, `/services` |
| Builder shell, step 4 (F§4.7) | Adds `"review"` to `SHIPPED_STEPS`, so the Review item in `StepProgress` shows "Not in archive", "Saved" or "Unsaved changes" (from `editing` and `isDirty`). Wires the archive half of the `SummaryPanel` status line. Deletes `StepPlaceholder` and `StillNeeded`, which no step uses once 5a lands. |

**Out of scope, with the slice that owns it**

| Item | Owner |
|---|---|
| Emailing the bulletin (F10), the Gmail connection (F8, F9), `GET /contacts`, the Settings layout | **5b**. 5a leaves a mount point on the Review step (see Frontend changes). |
| Reading the 12-week exclusion window, and the `recently_used` flag on `GET /hymns` | **3** reads the usage table; 5a writes it. |
| Editing liturgy cards, custom elements, the communion toggle, and the default benediction | **4** |
| The readings step's handling of `fields_origin: "archive"` (showing the loaded date's reading sets without overwriting fields) | **2**. The interface is stated below. |
| Setting a church's default hymnal | **6a** (5a only reads it) |
| Deleting `hymn_usage.record_usage`, `service_archive.list_saved_services` and `app.py` | **7** (the frozen Streamlit branch still uses them) |
| Removing usage when a service is deleted or re-dated | **7** may revisit it once Streamlit no longer writes usage (open question 1) |
| Archive search, "duplicate as template", restoring deleted services | Not planned. Loading a service and changing its date already saves a copy (parity). |

### Interfaces assumed from earlier slices

If an earlier slice shipped a name that differs, use that slice's name. The behavior stated here must still hold.

| Slice | Interface 5a uses |
|---|---|
| ops | `db/upsert.py::insert_ignore(table)`. CORS `allow_headers` includes `If-Match` and `Idempotency-Key`, and `expose_headers` includes `Content-Disposition` (F§1.10). `UnhandledErrorMiddleware`. `redirect_slashes=False`. |
| 1 | `domain_errors`: `InvalidInput(message, field=)`, `NotFound(message, details=)` and `Conflict(message, details=)`. `db.ids.as_uuid`. The `usecases/` package. The idempotency dependency from `api/idempotency.py` (F§1.6), including 422 `idempotency_mismatch` "This request was already sent with different details." and stored 4xx responses. `Page` in `api/schemas.py`. The Alembic head at merge time (`0004` expected; see "Data and migrations"). `test_migrations.py` with its single-head assertion (5a adds the assertion if it is missing). `assert_church_isolated`, `test_route_guards.py`, `test_openapi_contract.py`. On the frontend: `useApi()` (`api.church`), `apiFetch` options `method/json/idempotencyKey/ifMatch/timeoutMs`, `ApiError.status/code/details`, the query keys in F§4.4, the UI kit (F§4.8: `ConfirmDialog`, `PendingButton`, `EmptyState`, `ErrorState`, `Skeleton`, `PageHeader`), `renderWithProviders`, `installFakeApi` (5a-2 extends it for binary responses; see Testing). |
| 2 | Draft store `useDraft() → {draft, update(recipe), replace(next)}`. `freshDraft({church, user})`. `fingerprint(payload)`, `isDirty(draft)`. `status.ts` step statuses and `stillNeeded(draft, SHIPPED_STEPS)`. `steps.ts` with `SHIPPED_STEPS` (slice 2 ships `{"readings"}`). `DRAFT_VERSION` plus the `migrations` table. `lib/dates.ts` (`formatServiceDate`, `isValidDateIso`, `nextSunday`, `todayIn`). `BuilderShell`, `StepProgress`, `StepFooter` and `SummaryPanel`, which read `draft.editing`, plus the `StepPlaceholder` and `StillNeeded` components that 5a deletes. The Review route shell. **The one bulletin-reading rule:** `backend/scripture_refs.py` with `resolve_readings(scriptures, ot_pick="", nt_pick="") -> ReadingPair(ot, nt, ot_auto, nt_auto)` (it ignores a pick that is no longer among `picker_options` for its side), plus `is_nt_ref`, `expand_ref_options` and `picker_options`, and the TypeScript port `src/lib/scripture-refs.ts` (`resolveReadings`, `isNtRef`, `expandRefOptions`, `pickerOptions`) with the shared fixture `scripture_refs.json`. The selector `effectivePicks(draft)`, which calls `resolveReadings`. The provisional `draftToServicePayload`'s rule that picks are sent as `resolveReadings`' explicit values. The `["lectionary", dateIso]` query. |
| 3 | `GET /church` returns `default_hymnal` and `effective_hymnal` (`str \| null`). `usecases.hymns.resolve_default_hymnal(church_id, *, session=None) -> DefaultHymnal(default_hymnal, effective_hymnal)`. `hymn_search.normalize_title(title)` (collapse whitespace, strip, casefold) and `hymn_search.usage_key(number, title)`. The hymns step shows a pick with `hymn_id: null` as "Not in your hymnal. Choose a replacement.". The `["church", id, "hymns", …]` keys. Slice 3's exclusion window reads `hymn_usage` rows by `usage_key`, which 5a now writes on save with the same key. **`api/schemas.py`: `HymnRef`, created by slice 3 with the shape frozen in F§1.3**, and `SlotHymns` and `SectionKey`, frozen there alongside it (see "Shared `HymnRef`"). `"hymns"` in `SHIPPED_STEPS`, and `SummaryPanel`'s hymns block (the three slots). |
| 4 | `backend/liturgy_config.py`: `SECTION_ORDER` (8 keys), `CUSTOM_PLACEMENTS` (the 17 `(key, label)` pairs in the order of app.py:148-166), `PLACEMENT_KEYS`, `normalize_placement(key)` (unknown → `"end"`), **`OUTLINE`**, `ASSURANCE_RESPONSE` and `LIMITS` (`max_sermon_title=300`, `max_section_text=20_000`, `max_custom_elements=30`, `max_custom_label=200`, `max_custom_text=10_000`). **`GET /liturgy/config`**, whose `outline` (`OutlineItemOut[]`: `kind`, `key`, `label`, `value_source`, `fixed_text`, `anchors_after`) and `assurance_response` 5a's order-of-worship card reads through `useLiturgyConfig()` (key `["ref", "liturgy-config"]`, `staleTime: Infinity`). The shared fixture `backend/tests/fixtures/shared/liturgy_outline.json`, which slice 4 keeps equal to the serialized `OUTLINE`. The client helper `normalizePlacement`. The plain dataclass `HymnRefData` that slice 4's usecase takes. The unresolved-hymn message **"A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."**, which 5a uses unchanged. Draft fields `liturgy.cards` and `liturgy.custom_elements` (F§4.6). `"liturgy"` in `SHIPPED_STEPS`, and `SummaryPanel`'s liturgy block (F§4.7). The communion text is either still in `worship_service._add_communion_liturgy` or moved to `liturgy_config` by slice 4; 5a renders whichever exists, and the characterization test below pins the output. |

**Shared `HymnRef`.** The shape is frozen in F§1.3 and created by slice 3, which lands first: `{hymn_id: UUID | null, title: str (≤300), number: int (0-100 000) | null, hymnal: str (≤20) | null}`, `extra="forbid"`, with **no pattern** on `hymnal` (CLI-imported hymnal codes were never pattern-checked; `HymnalCode` is kept only for the query and path parameters that need it). `SlotHymns` and `SectionKey` are frozen alongside it, and whichever of slices 3 and 4 lands first creates them with that shape. Slice 4's `POST /liturgy/generate` is the first route that accepts them. 5a imports `HymnRef`, `SlotHymns` and `SectionKey` from `api/schemas.py` and adds no constraints to them, so the `/liturgy/generate` contract does not change. If 5a ever needs a different limit, it may only loosen one (F§1.11), and it must amend F§1.3, regenerate OpenAPI and add a `/liturgy/generate` test for the new limit.

### Hand-offs to 5b

These are the exact names and signatures, and the 5b spec must use them. This list replaces the earlier 5a names `display_date(date_iso)`, `service_output.bulletin_email_subject(date_iso)` owned by 5a, `draftToServicePayload(draft, church)` and the message "This hymn is no longer in your hymnal. Choose a replacement.". Wherever 5b still uses one of those, it changes to the name below.
- `ServiceDraft`, defined in `backend/api/schemas.py` by 5a. It is the `service` field of `POST /bulletin-emails`. **Usecases never import `api/*`**, so the 5b route calls `body.service.to_input()` and passes the resulting `usecases.archive.ServiceInput` down. `send_bulletin_email` takes `data: ServiceInput`, not `draft: ServiceDraft`.
- `usecases.documents.build_document(church_id: uuid.UUID, data: usecases.archive.ServiceInput, variant: Literal["bulletin", "pastor"]) -> DocumentResult(content: bytes, filename: str)`. This is the only way to build the attachment. 5b calls `build_document(church_id, data, "bulletin")`. It lets `clean_input`'s `InvalidInput` and `resolve_hymn_refs`'s `NotFound("A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.", details={"field": "hymns.<slot>.hymn_id"})` propagate.
- `service_output.service_date_display(d: datetime.date) -> str`, for example "October 04, 2026". This is the **only** date-display function. 5b's `bulletin_email_subject` and `default_bulletin_message` call it.
- `service_output.DOCX_MIME`, defined by 5a (the `/documents` route uses it). 5b imports it and does not define it again.
- 5a does **not** define `bulletin_email_subject`. **5b owns it**, with the signature `(d: datetime.date)` from the 5b spec, and it keeps the subject from app.py:1124. 5b also owns recipients, BCC and the default message.
- Frontend: `draftToServicePayload(draft) → ServiceDraft` (one argument; see "Library code"), `docxFilename(variant, dateIso)`, and the mount point `src/components/builder/review/email-slot.tsx`, which 5b replaces.

---

## User experience

The layout is mobile-first at 375 px, following the builder shell (F§4.7). The Review step sits inside `BuilderShell`: it has progress at the top and a sticky footer with **Back** only. On desktop, `SummaryPanel` stays on the right.

### Review step (`/builder/review`)

Cards appear top to bottom in this order. The actions come first, because people usually come back to Review to download or save.

**1. Banner, shown only while editing an archived service**
- "You're editing the saved service for {October 4, 2026}. Changes stay on this device until you save."
- If any pick has `hymn_id: null`, add a second line: "{n} hymn(s) from this service aren't in your hymnal. [Choose replacements]", which links to `/builder/hymns`.
- If the saved service has no date (`editing.date_iso === null`, a legacy row), show this instead of the first line: "This saved service has no date. It's set to {Sunday, October 11, 2026} for now. [Check the date]" (a link to `/builder/readings`). The banner is advice only and never blocks Save. It disappears after the next save, because a save always sets `editing.date_iso`.

**2. "Still to do" checklist**
- Uses `missingItems(draft)`, built on slice 2's `status.ts`. Each row links to its step:

  | Row | Links to |
  |---|---|
  | "No service date — Choose one" | Readings |
  | "No occasion — Add one" | Readings |
  | "No readings — Add them" | Readings |
  | "No {Opening\|Response\|Closing} hymn — Choose one" | Hymns |
  | "{Title} isn't in your hymnal — Choose a replacement" | Hymns |
  | "{Card label} is empty — Write or generate it" (only enabled cards) | Liturgy |
  | "No sermon title — Add one" (the documents would print "[Sermon title]") | Liturgy |

- With nothing missing: "Everything's ready."
- Only a missing or invalid date blocks anything (F decision D9).

**3. Save card, titled "Archive"**
- **Status line:**
  - "Not in the archive yet."
  - "Saved to the archive · {Oct 1, 10:42 AM}" (`saved_at` in the viewer's local time)
  - "Unsaved changes · last saved {Oct 1, 10:42 AM}"
- **Primary button** (`size="touch"`):
  - **"Save to archive"** when `editing` is null.
  - **"Save changes"** when editing and the date is unchanged.
  - **"Save as new service"** when editing and `readings.date_iso !== editing.date_iso`. This is parity with app.py:1029-1035. Below the button: "The date changed from {October 4, 2026} to {October 11, 2026}, so this will be saved as a new service. The {October 4} service stays in the archive."
  - When the saved service has no date (`editing.date_iso === null`), the rule is the same (parity: Streamlit also compares against a null date). The text below the button reads instead: "The saved service has no date, so this will be saved as a new service on {October 11, 2026}. The undated service stays in the archive."
- **Pending:** "Saving…". **Success:** toast "Service saved".
- **Invalid date:** the button is disabled, with the note "Choose a service date on step 1 to save or download." and a link.
- **Secondary button "Start a new service":**
  - If the draft is dirty, it first opens a `ConfirmDialog`: title "Start a new service?", body "Your current draft has changes that aren't saved to the archive. Starting a new service discards them.", confirm button "Discard and start new".
  - It then replaces the draft with `freshDraft(...)` and navigates to `/builder/readings`.
- **Conflict (409):** a dialog titled "Someone else changed this service", with the body "This service was changed by someone else. Reload it to see their changes." (the exact server message). Buttons:
  - **"Reload their version"**: `GET /services/{id}`, then `serviceToDraft`, then replace the draft. The dialog is the confirmation. Toast "Loaded the latest version."
  - **"Save mine as a new service"**: `POST`.
  - **"Cancel"**.
- **The archived copy was deleted (PUT returns 404 with no `details.field`):** the client POSTs automatically and toasts "The archived copy was deleted, so this was saved as a new service."
- **Hymn no longer in the hymnal (404 with `details.field = "hymns.<slot>.hymn_id"`):** toast with the server message, "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step." (slice 4's wording, used for this case everywhere), and the action "Go to Hymns". After the user replaces the hymn, **Save** works straight away: the rejected attempt's `Idempotency-Key` is never reused (see `useSaveService`).
- **Retrying after a failure:** the user can edit the draft and save again after any error. The client picks the `Idempotency-Key` itself (see `useSaveService`), so the user normally never sees `idempotency_mismatch`. If the one automatic retry gets it again, the global pattern shows the server message.
- **Other errors:** the global patterns (F§4.8), for example "Something went wrong. (Ref: 9f2c1a4b)".

**4. Word documents card**
- **Bulletin copy**
  - Description: "The order of worship with hymns, readings and the sermon title. Leaves out Prayers of the People." This fixes the misleading "Liturgy only" / "no sermon" copy (inv §0 item 2; owner decision 4).
  - Button: **"Download bulletin copy"**.
- **Pastor's copy**
  - Description: "Everything in the bulletin copy, plus Prayers of the People."
  - Button: **"Download pastor's copy"**.
  - When the Prayers of the People card is disabled or empty, add the helper "Same as the bulletin copy for this service. Prayers of the People is empty or turned off." (inv F1 notes that the two copies are identical by default.)
- **Pending:** each button has its own state, "Preparing…", with "Still working…" after 8 s (F§1.8).
- **Success:** the browser's download or share sheet opens with the server's filename. No toast.
- **Hint:** after a download while the draft is unsaved or dirty, show inline "Tip: save this service so its hymns count as recently used." Usage is recorded only on save.
- **Invalid date:** both buttons are disabled, with the same note as the Save card.
- **Errors:** a toast with the server message. The frontend never shows a file for a failed request.

**5. Email card.** This is `email-slot.tsx`. In 5a it is a plain muted card with the text "Emailing the bulletin is available soon — keep using the current app for this part." It no longer uses `StepPlaceholder`, which 5a deletes. 5b replaces it.

**6. "Order of worship" card**
- A two-segment control, **Bulletin copy | Pastor's copy**. The default is Bulletin.
- **Title block:** "Worship Service", the occasion (or "No occasion"), and the date exactly as the document prints it ("October 04, 2026").
- One row per item, in the order of slice 4's `OUTLINE` as served by `GET /liturgy/config` (see `orderOfWorship`, Frontend changes). Slice 4's outline/docx test ties that order to the Word document, so the card and the file cannot disagree:
  - a small heading (the outline item's `label`, or a custom element's own label), then the content as plain text with `whitespace-pre-wrap`, clamped to 3 lines with "Show more";
  - hymns as "Holy, Holy, Holy — #138", or with "· not in your hymnal" appended;
  - readings with "· chosen automatically" when the fallback picked them;
  - the sermon title, or "[Sermon title]";
  - "Affirmation of Faith — Apostles' Creed" (the item's `fixed_text`);
  - communion as the single row "The Sacrament of the Lord's Supper" (the outline item's label);
  - custom elements under their own label.
- Assurance shows the appended `assurance_response` from the config ("People: Thanks be to God! Amen.") exactly as the document does.
- Rows present only in the pastor's copy carry the tag "Pastor's copy only".
- **Loading:** skeleton rows while `useLiturgyConfig()` is pending. **Error:** `ErrorState` with **Retry**. Saving and downloading don't depend on the config, so they stay available.
- All text renders as React text. Nothing is rendered as HTML (F§4.8).

### Step status and summary panel (builder shell)

Slices 3 and 4 have turned on the Hymns and Liturgy steps. 5a turns on the last one.
- **`StepProgress`, Review item** (F§4.7: review shows "Saved" or "Unsaved changes"). It is computed from `editing` and `isDirty(draft)`:
  - `editing === null` → "Not in archive" (slice 2's label, unchanged);
  - `editing` set and not dirty → "Saved", with the ✓ of a complete step;
  - `editing` set and dirty → "Unsaved changes".
- **`SummaryPanel` status line.** Slice 2's device half stays: "Draft saved on this device", or "Draft not saved on this device" in memory-only mode. 5a supplies the archive half after " · ", with the same three states:
  - "Not in archive";
  - "In archive (saved {Oct 1, 10:42 AM})";
  - "In archive (saved {Oct 1, 10:42 AM}) · Unsaved changes".

  The status line links to `/builder/review`, like the other blocks link to their steps.
- With all four steps shipped, no builder route renders `StepPlaceholder`, and nothing in `SummaryPanel` reads "Available soon". The only "available soon" text left in the builder is the email card, which 5b replaces.

### Services page (`/services`)

The "Services" nav item appears in the header and the mobile segmented nav (F§4.2).

- **Header:** "Services", with the subtitle "Saved services for {church name}." and the button **"New service"**, which follows the same flow as "Start a new service".
- **List:**
  - 20 rows per page, newest service date first. Rows with no date go last.
  - Each row:
    - line 1: `formatServiceDate(service_date_iso)` (already normalized by the server; see "Normalizing stored data"), or the stored display string, or "No date";
    - line 2: the occasion, or "No occasion";
    - line 3 (small): "Created by {name} · last saved {Oct 1, 10:42 AM}", or "Last saved {Oct 1, 10:42 AM}" when `created_by` is null. `created_by` is the original author and never changes on a later save, so the line does not claim that the author made the last save;
    - the badge "Editing" when `draft.editing.service_id` matches.
  - Tapping the row opens the service. A trailing menu button (aria-label "More actions for {date}") holds **"Delete…"**.
  - At the bottom: "Showing {n} of {total}" and the button **"Show more"**, which reads "Loading…" while pending.
- **Loading:** five skeleton rows.
- **Error:** `ErrorState` with the message and **Retry**. An error is never shown as an empty list.
- **Empty:** `EmptyState` with the title "No saved services yet", the text "Services you save from the builder appear here." and the action **"Build a service"**, which goes to `/builder`.
- **Open flow:**
  1. If the draft is dirty, open a `ConfirmDialog`: title "Replace your unsaved draft?", body "Your current draft for {date} has changes that aren't saved to the archive. Opening this service replaces it.", confirm button "Replace draft".
  2. The row shows "Opening…". The client fetches `GET /services/{id}` with `staleTime: 0`.
  3. It runs `serviceToDraft`, replaces the draft and navigates to `/builder/review`.
  4. It also prefetches `["lectionary", date_iso]` in the background, so step 1 is ready.
  5. On 404: toast "That service is no longer in the archive." and refetch the list.
- **Delete flow:**
  - A `ConfirmDialog` titled "Delete this service?" with the body: "“{occasion or 'Untitled service'}” on {date} will be removed from the archive for everyone in {church}. This can't be undone." `{date}` is the row's line 1; for a row with no date the body reads "“{occasion}” (no date) will be removed…".
  - When this row is the service being edited, add: "You're editing this service. Your current draft will be cleared too."
  - The confirm button is "Delete service", and any member can use it (owner decision 5).
  - On success the row disappears (no toast). If it was the service being edited, the draft resets to a fresh one (F§4.6, rule 2).
  - On 404: toast "That service is no longer in the archive." and refetch.

### Mobile specifics

- Every primary action uses `size="touch"`.
- Row tap targets are at least 44 px tall.
- The Review cards stack in one column, with no horizontal scroll at 375 px.
- Dialogs use Base UI AlertDialog. Downloads use the object-URL flow (F§1.9). On iOS this opens the share or preview sheet, which is acceptable.

---

## API

All routes use the conventions of F§1: snake_case JSON, the uniform error body with `request_id`, typed UUID path ids, `extra="forbid"` request models, and DELETE returning 200 with JSON. Every route below is **church**-guarded. Owner decision 5 lets **members** use all of them, so there are no admin or owner routes in 5a. Every route can also return `401 unauthenticated` and `403 forbidden` ("You don't have access to this church.") from the guard. These are omitted from the table.

| Method | Path | Guard | Request | Response | Errors (status `code` "message") |
|---|---|---|---|---|---|
| GET | `/services` | church | `?limit` (1-200, default 50; the UI sends 20), `?offset` (≥0, default 0) | 200 `ServicePage` = `{items: ServiceSummary[], total, limit, offset}`, ordered by `NULLIF(service_date_iso, '') DESC NULLS LAST, saved_at DESC, id DESC` (an empty legacy date sorts with the undated rows) | 422 `invalid_request` (limit or offset out of range) |
| GET | `/services/{service_id}` | church | – | 200 `ServiceOut` (hymns normalized; see below) | 404 `not_found` "That service is no longer in the archive." (unknown id or another church's id); 422 `invalid_request` (malformed UUID) |
| POST | `/services` | church | `ServiceDraft`; optional `Idempotency-Key` (the client sends `draft.save_key`) | 201 `ServiceOut` | 404 `not_found` "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step." (slice 4's message) + `details.field` = `hymns.<slot>.hymn_id`; 422 `invalid_request` (Pydantic, with `fields`), or "Give each custom element a label." with `fields["custom_elements.<i>.label"]`; 422 `idempotency_mismatch` "This request was already sent with different details." (slice 1's message; the client's key rule avoids it, see `useSaveService`) |
| PUT | `/services/{service_id}` | church | `ServiceDraft`; **required** `If-Match: <saved_at from the last response>` | 200 `ServiceOut` (with a new `saved_at`) | 404 `not_found` "That service is no longer in the archive." (no `details`); 409 `conflict` "This service was changed by someone else. Reload it to see their changes." + `details.current_saved_at`; 422 `invalid_request` "If-Match is required." or "If-Match must be the service's saved_at timestamp."; plus the hymn-404 and 422 cases from POST |
| DELETE | `/services/{service_id}` | church | – | 200 `DeletedOut` = `{"deleted": true}` (defined here in `api/schemas.py`; 6a and 6b reuse it) | 404 `not_found` "That service is no longer in the archive." |
| POST | `/documents` | church | `{variant: "bulletin" \| "pastor", service: ServiceDraft}` | 200 bytes. `Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `Content-Disposition: attachment; filename="worship_October_04_2026.docx"; filename*=UTF-8''worship_October_04_2026.docx` (pastor: `worship_pastor_…`), `Cache-Control: no-store` | Hymn 404 and 422 as for POST `/services`; 500 `internal_error` if python-docx cannot be imported (logged) |

**Check order for `PUT`** (so the client can tell the cases apart):
1. The service exists in the church. Otherwise 404, with no `details`.
2. `If-Match` is present and parses. Otherwise 422.
3. `If-Match` equals the stored `saved_at`. Otherwise 409.
4. Input rules, then hymn resolution (404 with `details.field`).
5. Write.

POST `/services` and `/documents` run steps 4-5 only.

**Why a hymn id in the body gives 404, not 422:** F§1.2 rule 2 says an id from the path or body that is unknown, or belongs to another church, is a 404. The same message for both cases means the response never reveals whether a hymn exists in another church.

**Timeouts** (F§1.8): `/documents` has a client `timeoutMs` of 30 000. The other routes use the default 20 000. There is no rate-limit bucket: `/documents` does only local work, in under 3 s.

**OpenAPI:** `/documents` declares `response_class=Response` and `responses={200: {"content": {DOCX_MIME: {"schema": {"type": "string", "format": "binary"}}}}}` in place of a `response_model`. Every other route declares `response_model`. The contract snapshot is regenerated in 5a-1.

### Schemas (`backend/api/schemas.py`, shared with 5b)

```python
# Already in api/schemas.py (shapes frozen in F§1.3; HymnRef created by slice 3), imported and reused
# unchanged (see "Shared HymnRef"):
#   SectionKey  - Literal of the 8 section keys
#   HymnRef     - {hymn_id: UUID | None, title: str (<=300), number: int (0..100_000) | None,
#                  hymnal: str (<=20, no pattern) | None}, extra="forbid"
#   SlotHymns   - {opening, response, closing: HymnRef | None}, extra="forbid"
# 5a adds no constraints to these three, so POST /liturgy/generate is unaffected.

class DeletedOut(BaseModel):       # response of DELETE /services/{id}; 6a and 6b reuse it for their deletes
    deleted: Literal[True] = True

Placement = Literal[*(k for k, _ in liturgy_config.CUSTOM_PLACEMENTS)]  # the 17 keys (= PLACEMENT_KEYS)
L = liturgy_config.LIMITS

class CustomElementIn(BaseModel):  # extra="forbid"
    label: str = Field(max_length=L.max_custom_label)    # "required after trim" is a usecase rule
    text: str = Field(default="", max_length=L.max_custom_text)
    insert_after: Placement

class ServiceDraft(BaseModel):     # extra="forbid"; inventory §2.1 plus hymnal (F§1.3)
    service_date_iso: datetime.date
    occasion: str = Field(default="", max_length=300)    # same limits as slice 4's GenerateLiturgyIn
    scriptures: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=20)
    hymns: SlotHymns = Field(default_factory=SlotHymns)
    hymnal: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] | None = None
        # null = the church's effective hymnal at save time (slice 3's convention for `hymnal: null`)
    liturgy: dict[SectionKey, Annotated[str, Field(max_length=L.max_section_text)]] = Field(default_factory=dict)
    sermon_title: str = Field(default="", max_length=L.max_sermon_title)
    selected_ot_ref: str = Field(default="", max_length=200)
    selected_nt_ref: str = Field(default="", max_length=200)
    include_communion: bool = False
    custom_elements: list[CustomElementIn] = Field(default_factory=list, max_length=L.max_custom_elements)

    def to_input(self) -> "archive.ServiceInput": ...    # usecases never import api/*; routes call this

class ArchivedHymn(BaseModel):
    hymn_id: uuid.UUID | None
    title: str
    number: int | None
    hymnal: str | None
    in_hymnal: bool                                      # true when hymn_id resolves in this church now

class ServiceOut(BaseModel):
    id: uuid.UUID
    service_date_iso: str | None                         # normalize_date_iso(stored); null for undated legacy rows
    service_date: str                                    # stored display string ('%B %d, %Y')
    occasion: str
    scriptures: list[str]
    hymns: dict[Literal["opening", "response", "closing"], ArchivedHymn | None]
    hymnal: str | None
    liturgy: dict[SectionKey, str]
    sermon_title: str
    selected_ot_ref: str
    selected_nt_ref: str
    include_communion: bool
    custom_elements: list[CustomElementIn]
    created_by: AuthorOut | None                         # {id, name}; name falls back to the email
    saved_at: str                                        # ISO 8601, always with an offset

class ServiceSummary(BaseModel):
    id: uuid.UUID
    service_date_iso: str | None                         # same normalize_date_iso as ServiceOut
    service_date: str
    occasion: str
    sermon_title: str
    saved_at: str
    created_by: AuthorOut | None
```

`AuthorOut.name` shows a member's name or email to other members. Owner decision 5 allows this: members already see the member list with emails.

**Normalizing stored data into `ServiceOut`** (in `usecases/archive.get_service`)

*Hymns.* Stored `hymns` becomes the slot map using F§4.6 step 3, **run on the server**, so `serviceToDraft` needs no hymnal list. Parsing uses `service_output.stored_hymn_entries` and `service_output.slot_map`, the same tolerant parser that the usage rebuild uses. For each slot:
1. **Mapping.** A stored value that is not a list counts as `[]`. If every stored entry is a dict with a valid `slot` key, map by slot. Otherwise map entries positionally: index 0 is opening, 1 is response, 2 is closing. Legacy Streamlit lists are compacted, so this can misplace hymns (accepted in F§4.6). Non-dict entries, and a `title` that is not a string, count as empty.
2. **A blank title** (after stripping) makes the slot `null`.
3. **Stored `hymn_id` still in this church:** use the hymnal row's current title, number and hymnal, with `in_hymnal: true`.
4. **Otherwise, match on `hymn_search.normalize_title(title)`, plus `number` when it is not null,** among the church's hymns. Rank the candidates by hymnal: first the entry's `hymnal`, then `service.hymnal`, then `effective_hymnal` from `usecases.hymns.resolve_default_hymnal` (slice 3; no separate default-hymnal logic here), then any other hymnal in code order. Within one hymnal, take the lowest `number` (nulls last), then the lowest `id`. PH1990 alone has 34 duplicate titles, so this tie-break keeps the result deterministic. The chosen match gets `in_hymnal: true`.
5. **Otherwise** keep the snapshot: `hymn_id: null`, the stored title, `_coerce_number(number)` and the stored hymnal, with `in_hymnal: false`.

*Liturgy.* Only the 8 `SECTION_ORDER` keys are kept, with string values that are non-blank after stripping. Text that `service_output.is_legacy_error_placeholder` recognizes is dropped. That covers Streamlit's stored `[Error generating …]`, `[Configure OPENAI_API_KEY to generate …]` and `[Your OPENAI_API_KEY contains invalid …]` (worship_service.py:713, 722, 764).

*Other fields.*
- `custom_elements`: NULL, or a stored value that is not a list, becomes `[]`. Every dict entry is kept, in stored order: a `label` or `text` that is not a string becomes `""`, and `insert_after` goes through `liturgy_config.normalize_placement`, so an unknown or missing placement becomes `"end"`. **An element is never dropped for its placement** (slice 4; F§4.6: typed input is never destroyed), so it survives a load followed by a save. Non-dict entries are skipped. `ServiceDraft` still rejects an unknown `insert_after` with 422; the client never sends one, because it only sends placements it received from here or chose from `CUSTOM_PLACEMENTS`.
- `service_date_iso`: `service_output.normalize_date_iso(raw)`, which **both `get_service` and `list_services` use**. A string that is a valid ISO date (`YYYY-MM-DD`, and a real calendar date) is returned as it is. Otherwise, if its first 10 characters are a valid ISO date, those are returned; this recovers Notion-era values with a time part, such as `2026-10-04T00:00:00.000Z` (migrate_to_db.py keeps the raw value). Anything else (`''`, `NULL`, a non-date) becomes `null`.
- `saved_at`: a naive value (SQLite) is treated as UTC. It is always serialized with `+00:00`.

---

## Backend changes

### New modules

**`backend/service_output.py`**: pure functions with no database, no FastAPI and no Streamlit (F§2.3 destination table). It moves:
- the filename and date logic out of app.py:1072;
- the variant flags out of app.py:996-997 and 1019-1020;
- the slot mapping out of app.py:847-851.

| Name | Behavior |
|---|---|
| `MONTHS` | A fixed English month table. `strftime("%B")` is not used, because it depends on the locale. |
| `DOCX_MIME` | `"application/vnd.openxmlformats-officedocument.wordprocessingml.document"`. 5b imports it. |
| `service_date_display(d: datetime.date) -> str` | `'%B %d, %Y'` with the day zero-padded: `date(2026, 10, 4)` becomes "October 04, 2026". This is identical to `service_date_str` (app.py:425) and to existing rows (F§6.2). It is the only date-display function (5b uses it too). |
| `normalize_date_iso(raw) -> str \| None` | The stored-date rule in "Normalizing stored data" (full ISO date, else a valid first 10 characters, else `None`) |
| `safe_date(display) -> str` | `display.replace(", ", "_").replace(" ", "_")`, which gives "October_04_2026" (app.py:1072) |
| `docx_filename(variant, d: datetime.date) -> str` | `worship_{safe}.docx` for the bulletin, `worship_pastor_{safe}.docx` for the pastor's copy (app.py:1079, 1088) |
| `stored_hymn_entries(raw) -> list[StoredHymn \| None]` | A tolerant parser for a stored `services.hymns` value. A non-list gives `[]`. Each entry becomes `StoredHymn(slot, title, number, hymn_id, hymnal)`, where `title` is stripped, `number` goes through `_coerce_number`, and `slot` is kept only when it is one of the 3 slots. Otherwise the entry becomes `None`: that covers a non-dict, a non-string title and a blank title. It never raises. |
| `slot_map(entries) -> dict[slot, StoredHymn \| None]` | Maps by `slot` when every entry has one, else by position 0-2 (step 1 of "Normalizing stored data") |
| `VARIANTS` | `{"bulletin": {"include_sermon": True, "include_prayers_of_the_people": False}, "pastor": {"include_sermon": True, "include_prayers_of_the_people": True}}`. Both copies include the sermon title (owner decision 4; inv §0 item 2). |
| `SLOT_HEADINGS` | `{"opening": "First Hymn", "response": "Second Hymn", "closing": "Third Hymn"}`. The heading text is unchanged, so the documents look the same and the placement labels "After First Hymn" etc. stay true. **Renaming a heading here requires updating the matching `liturgy_config.OUTLINE` label (and regenerating `liturgy_outline.json` and `order_of_worship.json`) in the same PR**, as slice 4 states; slice 4's outline/docx test fails otherwise. |
| `hymn_line(title, number) -> str` | `"{title} — #{number}"`, or just `"{title}"` when `number is None`. Fixes `#None` (worship_service.py:847, 906, 933). |
| `resolve_doc_readings(scriptures, selected_ot_ref, selected_nt_ref) -> (ot \| None, nt \| None)` | Returns `scripture_refs.resolve_readings(scriptures, selected_ot_ref, selected_nt_ref)` projected to `(ot, nt)`. It has no rule of its own; see below the table. |
| `is_legacy_error_placeholder(text) -> bool` | Stripped text that starts with `[Error generating `, `[Configure OPENAI_API_KEY to generate ` or `[Your OPENAI_API_KEY contains invalid` and ends with `]`. |
| `ResolvedService` (frozen dataclass) | The service date (`datetime.date`), occasion, scriptures, `hymns: dict[slot, ResolvedHymn \| None]`, hymnal, liturgy, sermon title, selected refs, communion, custom elements |
| `stored_hymns(resolved) -> list[dict]` | Exactly 3 entries in slot order, `{slot, title, number, hymn_id, hymnal}`. An empty slot is `{"slot": s, "title": "", "number": None, "hymn_id": None, "hymnal": None}`. Titles and entries are never null (F§6.2). |
| `render_docx(resolved, variant) -> bytes` | Calls `worship_service.build_docx` with the resolved readings, slot hymns and variant flags |
| `content_disposition(filename) -> str` | `attachment; filename="{f}"; filename*=UTF-8''{quote(f)}` (F§1.9) |

5b adds `bulletin_email_subject(d: datetime.date)` and the other email helpers to this module. 5a does not define them.

**Rule for `resolve_doc_readings`.** This is the NT fallback from owner decision 9 and inv §7 question 14, implemented **once**, in slice 2's `scripture_refs.resolve_readings`. The screen (`effectivePicks`), `draftToServicePayload`, `docReadings` and this function all delegate to it (or to its TypeScript port `resolveReadings`), so what the Bulletin readings selects show is what the Word file prints, whether or not a pick is stale:

```
def resolve_doc_readings(scriptures, selected_ot_ref, selected_nt_ref):
    pair = scripture_refs.resolve_readings(scriptures, selected_ot_ref, selected_nt_ref)
    return pair.ot, pair.nt             # a None reading omits that section
```

What `resolve_readings` does (slice 2 owns the definition; restated for reading this spec):
- A pick that is not among `picker_options(scriptures)` for its side (a line that was edited or removed, or a Psalm picked as NT) is ignored, so that side is automatic.
- OT = the valid OT pick, else the first cleaned line (the OT rule is unchanged; see open question 2).
- NT = the valid NT pick, else the first line other than the effective OT whose first alternative is NT.

With RCL order `[first, psalm, second, gospel]` and no picks, the NT reading is now the second reading, or the gospel. The Psalm is never printed as the NT reading. A day with only OT and Psalm entries prints no NT reading. An `' or '` entry is classified by its first alternative and printed as written. The server applies the rule again to every posted `ServiceDraft`, so a direct API call (or 5b's email) with a stale pick prints the automatic reading too.

**`backend/usecases/archive.py`**. Every function takes `church_id: uuid.UUID`, and uses `user_id` only where noted.

| Function | Behavior |
|---|---|
| `ServiceInput` (frozen dataclass) | The domain copy of `ServiceDraft`, built by `ServiceDraft.to_input()` in the route. `service_date: datetime.date`; `hymns: Mapping[slot, HymnRefData \| None]` (slice 4's plain dataclass); `hymnal: str \| None`; the other fields as in `ServiceDraft`. `build_document` and 5b's `send_bulletin_email` take it too. |
| `resolve_hymn_refs(session, church_id, hymns) -> dict[slot, ResolvedHymn \| None]` | Detailed after this table. |
| `clean_input(data) -> ServiceInput` | Strips every string. Drops blank scriptures. Drops liturgy values that are blank or that `is_legacy_error_placeholder` recognizes. Raises `InvalidInput("Give each custom element a label.", field=f"custom_elements.{i}.label")` for a label that is blank after trim. |
| `list_services(church_id, *, limit, offset) -> Page[ServiceSummary]` | A projection query (no JSON columns) with an outer join to `users` for `created_by`. Uses the order from the API table with explicit `nulls_last()`. `total` comes from `count(*)`. Each row's `service_date_iso` goes through `service_output.normalize_date_iso`, exactly as in `get_service`. |
| `get_service(church_id, service_id) -> ServiceRecord` | Raises `NotFound("That service is no longer in the archive.")`. Normalizes as described in the API section. |
| `create_service(church_id, user_id, data) -> ServiceRecord` | One `session_scope`: `clean_input`, resolve hymns, insert (`created_by = user_id`, `service_date_iso = d.isoformat()`, `service_date_display = service_date_display(d)`, `hymns = stored_hymns(...)`, plus `custom_elements` and `hymnal`), then `hymn_usage.rebuild_usage_for_date(church_id, d.isoformat(), session=s)`. A null `data.hymnal` is stored as `resolve_default_hymnal(church_id, session=s).effective_hymnal`, the hymnal the hymns step showed. This server-side fill is **the** archived-hymnal rule, which slice 3 adopts: the payload sends `draft.hymns.hymnal` as is. There is no further fallback to a pick's hymnal: `effective_hymnal` is null only when the church has no hymns at all, and then every pick is a snapshot that keeps its own `hymnal` in its slot entry. |
| `replace_service(church_id, service_id, data, *, if_match: str \| None) -> ServiceRecord` | One `session_scope`. Lock the row with `SELECT … FOR UPDATE WHERE id AND church_id` (a no-op on SQLite), then run the PUT check order. Parse `If-Match` with `datetime.fromisoformat` after removing surrounding quotes and a `W/` prefix, treat a naive value as UTC, and compare to the stored `saved_at` (also normalized) at microsecond precision. Full replace. `saved_at = now(UTC)` (parity: it bumps on every save). `created_by` is unchanged. A null `hymnal` is filled as in `create_service`. Then rebuild usage for the saved date only. If the date changed, the old date's usage rows are left as they are, as on delete (open question 1). The builder never sends a date-changing PUT (it POSTs a copy), so this only affects direct API calls. |
| `delete_service(church_id, service_id) -> None` | One `session_scope`: delete `WHERE id AND church_id`. A rowcount of 0 raises `NotFound`. **`hymn_usage` is not touched** (open question 1). During the overlap, that date's rows may have been written by frozen Streamlit's Prepare for a real service, or imported from history, and no archived row backs them. |

`resolve_hymn_refs` resolves all non-null `hymn_id`s in one query, `repos.hymns.get_hymns_by_ids(church_id, ids, session=s)`, which is `WHERE church_id = :cid AND id IN (...)`.
- **An id that is found:** the title, number and hymnal come from the database, and the client's copy is ignored (F§1.3).
- **An id that is missing:** `NotFound("A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.", details={"field": f"hymns.{slot}.hymn_id"})`. This is slice 4's message; 5a adds only `details.field`.
- **`hymn_id: null`:** the client's `{title, number, hymnal}` snapshot is kept (F§1.3). A blank title makes the slot empty.
- **Duplicates:** the same hymn in two slots is allowed (parity).

**`backend/usecases/documents.py`**
- `DocumentResult(content: bytes, filename: str)`.
- `build_document(church_id: uuid.UUID, data: ServiceInput, variant: Literal["bulletin", "pastor"]) -> DocumentResult`. The `/documents` route and 5b's usecase both pass `ServiceDraft.to_input()`:
  1. Run `clean_input`, then `resolve_hymn_refs` inside a short read-only `session_scope`.
  2. **Close the session.**
  3. Run `service_output.render_docx(resolved, variant)`.
  4. Return it with `docx_filename(variant, data.service_date)`.

  It writes nothing: usage recording moves to save (owner decision 9). It logs `variant`, the church id, the byte size and the duration, never the content.

**`backend/api/routes/services.py`** and **`backend/api/routes/documents.py`**
- These are thin routes (F§2.2): parse the request, depend on `require_church` (and the idempotency dependency on `POST /services`), call one usecase and return the model.
- `documents.py` builds a `Response(content, media_type=DOCX_MIME, headers={Content-Disposition, Cache-Control: no-store})`. `Content-Disposition` is built by `service_output.content_disposition(filename)` in the exact form from F§1.9.
- Both routers are included in `create_app()`.

### Changed modules

`worship_service.build_docx`. First write characterization tests that pin the current headings, order, anchors, formatting and variants (F§2.3.1). Then change it:
- **New keyword signature:** `build_docx(*, occasion, date_display, hymns_by_slot, liturgy, ot_ref, nt_ref, sermon_title, include_sermon, include_prayers_of_the_people, include_communion, custom_elements) -> bytes`.
- `hymns_by_slot` maps each slot to `{title, number}` or `None`. Each hymn heading renders only when its slot is filled. The custom-element anchors `first_hymn`, `second_hymn` and `third_hymn` are still always emitted, as today (inv E5: anchors are emitted even when the section is absent).
- **Removed:** `include_placeholders` and `scripture_full_texts` (inv §3 row worship_service.py:790, 794). OT and NT arrive already resolved. Hymn lines use `hymn_line`.
- **Docstring fixed:** "Both variants include the sermon title; only the pastor's copy includes Prayers of the People."
- **Unchanged:** Times New Roman 11 pt, the centered bold 16 pt title "Worship Service\n{occasion}", the 12 pt date line, the Leader/People bolding, bold confession, the Assurance response, "Affirmation of Faith / Apostles' Creed", the communion block after the Second Hymn, the "benediction" and "end" anchors, and ignoring keys outside the 8 sections.
- **python-docx missing:** still raises `RuntimeError`. It reaches `UnhandledErrorMiddleware` as a logged 500 `internal_error` (F§7.4).
- Production Streamlit runs from `streamlit-frozen` (F§6.1), so app.py's call sites on `main` get no shim. **If the F§6.1.6 contingency is in force**, add `build_docx_legacy(**old_kwargs)`, which adapts the old list-based call.

`service_archive.py`. Per F§2.2 rule 3, every changed function gains `session: Session | None = None`, and ids use `db.ids.as_uuid`.
- `_hymn_snapshot` keeps only the whitelisted keys that are present: `slot`, `title`, `number`, `hymn_id` and `hymnal`. `hymn_id` is stored as `str(hymn_id)` when it is not `None`, and as JSON `null` when it is `None`, never as the string `"None"`. Unknown keys are dropped, as today; the existing test that input `{title, number, extra}` gives `{title, number}` still passes.
- `save_service(..., custom_elements=None, hymnal=None, session=None)`.
- `update_service(..., custom_elements=_UNSET, hymnal=_UNSET, session=None)`. A column is written only when its argument is passed (F§3.5).
- `_to_dict` adds `custom_elements` and `hymnal`.
- New:
  - `list_services_page(church_id, *, limit, offset, session=None) -> (rows, total)`;
  - `get_service_for_update(service_id, church_id, *, session)`, which uses `with_for_update()`;
  - the existing `delete_service(service_id, church_id)` gains `session=None`. It still returns a bool (whether a row was deleted).
- `list_saved_services` and `record_usage` stay for the frozen branch's tests. Slice 7 deletes them.

`hymn_usage.py`: new `rebuild_usage_for_date(church_id, date_iso, *, session) -> int`. Only `create_service` and `replace_service` call it, always with the date being saved.
0. **Guard.** `date_iso` must be a valid `YYYY-MM-DD` date, else `ValueError` (a programming error, so a 500). It is never called with `None` or `''`, so the SQL can never become `IS NULL` and gather every undated service.
1. **Serialize per church and date.** On Postgres, `SELECT pg_advisory_xact_lock(hashtextextended('hymn_usage:' || :church_id || ':' || :date_iso, 0))`. This is skipped on SQLite. The lock is released at commit or rollback.
2. Select `Service.hymns` for `church_id` whose stored date normalizes to `date_iso`. The query uses `service_date_iso LIKE :d || '%'` and then `normalize_date_iso` in Python, so a legacy value with a time part still counts.
3. Parse each value with `service_output.stored_hymn_entries`, the same tolerant parser `get_service` uses. A value that is not a list, a non-dict entry, a non-string title and a blank title are all skipped, never raised. One malformed legacy row therefore cannot make every save on that date fail. Unlike `slot_map`, this step keeps every entry, including a 4th or later one in an imported row.
4. Collect `(number, title)` for each entry and **dedupe on `hymn_search.usage_key(number, title)`**, slice 3's key (`normalize_title` collapses whitespace and casefolds). The first-seen display title is kept. Deduping in Python also removes NULL-number duplicates, which the unique constraint does not catch (inv F4).
5. **Sort** the pairs by `(number is None, number, usage_key title)`, so every transaction inserts in the same order.
6. `DELETE FROM hymn_usage WHERE church_id = :c AND date_iso = :d`.
7. `insert_ignore(HymnUsage.__table__)` for each pair (ON CONFLICT DO NOTHING; F§7.4).
8. Return the row count.

This replaces the saved date's rows, including rows the frozen Streamlit wrote on Prepare (owner decision 9; F§6.2). It uses the **union of all archived services on that date**, so a second service on the same date (an early service, say) never erases the first one's usage. Because of the advisory lock, a second transaction saving on the same date waits for the first to commit. Its select, a new statement under READ COMMITTED, then sees the first service, so the union is complete and the two rebuilds cannot deadlock. The frozen Streamlit's `record_usage` does not take the lock. Its insert can still collide with the unique constraint, which is the same as today.

`repos/hymns.py`:
- `get_hymns_by_ids(church_id, ids, *, session=None) -> dict[uuid, Hymn]`;
- `find_hymns_by_titles(church_id, title_keys: set[str], *, session) -> list[(id, hymnal, number, title)]`, used by legacy normalization. SQL cannot reproduce `normalize_title` portably (whitespace collapsing), so it reads the church's `(id, hymnal, number, title)` projection and filters in Python on `normalize_title(title) in title_keys`. A church has a few thousand hymns at most, and this runs only when some slot needs title matching. The rows come back ordered by `hymnal, number NULLS LAST, id`, and the usecase applies the ranking from "Normalizing stored data" step 4.

`db/models.py`:
- `Service.custom_elements = Column(JSON, nullable=True)`;
- `Service.hymnal = Column(String, nullable=True)`;
- `Index("ix_services_church_date", "church_id", "service_date_iso")`, which serves the list ordering and the usage rebuild;
- the docstring notes that NULL means "not recorded" (rows written by Streamlit).

`backend/tests/test_no_streamlit_in_core.py` also imports `service_output`, `usecases.archive` and `usecases.documents`.

### Streamlit coupling removed

These are replaced, not re-exported (F§2.3.2):
- app.py:978-1028 (Prepare buttons and `record_usage` on Prepare);
- app.py:1029-1067 (the editing-id lifecycle, with `get_service` called on every rerun, and the update-then-insert fallback);
- app.py:1069-1092 (downloads and the wrong caption);
- app.py:379-405 (load into session keys);
- app.py:520-543 (the archive sidebar and `_cached_saved_services`);
- app.py:847-851 (`hymns_ordered` positional flattening).

The editing lifecycle now lives in the draft (`editing`). Refresh buttons become query refetches.

### Data access and tenancy

- Every query filters on `church_id = ActiveChurch.id`. Path ids are looked up as `WHERE id AND church_id`. Body hymn ids are resolved inside the church. The usage rebuild and the list's user join are both church-filtered.
- A save is **one transaction**: the service write plus the usage rebuild. A failure in either rolls back both. This fixes the non-atomic save-then-usage (inv §4).
- There are no external calls in 5a. `/documents` closes its session before rendering.
- `If-Match` together with the row lock replaces last-write-wins (inv F7). On SQLite, `FOR UPDATE` does nothing; that known gap is covered by the Postgres test.
- Logs record only ids, counts, variant, `usage_rows` and duration. They never include a service body, liturgy text or custom-element text (F§2.5).

---

## Data and migrations

**`backend/migrations/versions/0005_services_extras.py`** (F§3.5), expand-only (F§3.4).

**Revision chain** (F§3.5). The chain after slice 1's `0001`-`0004` is: `services_extras` (5a-1, this revision, with the index), `invites_integrity` (6b-1), `memberships_one_owner` (6b-2), then slice 7's `normalize_legacy_data`, `contract_after_cutover` and `encrypt_gmail_tokens`. **File numbers follow merge order**, and the single-head test enforces the chain:
- `down_revision` is **the Alembic head on `main` when 5a-1 merges**, not a hard-coded `0004`. F§7.1 lets 6b-1, with `invites_integrity`, land any time after slice 1, so it may already be on `main`. (6b-2's `memberships_one_owner` merges after 5b, so it always comes after this revision.)
- If the head is `0004`, keep `0005_services_extras` with `down_revision = "0004_…"`.
- If 6b-1's `0006_invites_integrity` is already the head, name this file with the next free number (`0007_services_extras`, with `down_revision = "0006_invites_integrity"`). Renaming happens in the rebase, like `DRAFT_VERSION`.
- Add a merge revision only if both branches have already merged with the same parent.
- `test_migrations.py`'s single-head assertion fails CI on a wrong or duplicate `down_revision`. 5a relies on it and adds it if slice 1 or 6b has not. This spec keeps calling the revision "0005" for readability.

| Operation | Upgrade | Downgrade |
|---|---|---|
| `services.custom_elements` | `op.add_column("services", sa.Column("custom_elements", sa.JSON(), nullable=True))` | `drop_column` (batch mode on SQLite) |
| `services.hymnal` | `op.add_column("services", sa.Column("hymnal", sa.String(), nullable=True))` | `drop_column` |
| Index | `op.create_index("ix_services_church_date", "services", ["church_id", "service_date_iso"])` | `drop_index` |

- There is no backfill. Existing rows keep NULL, which the API reads as `[]` and `null`.
- There are no server defaults and no NOT NULL. The JSON type matches the existing `services` JSON columns.
- `env.py`'s `lock_timeout 5s` keeps a Streamlit connection from blocking the deploy. A failed pre-deploy migration leaves the previous release serving.
- `test_migrations.py` covers up, down and up again, plus `compare_metadata`. The CI Postgres job runs `alembic check` after it.

**Data shape written by the new app** (F§6.2):
- `services.hymns` has exactly 3 slot-ordered entries `{slot, title, number, hymn_id, hymnal}`, with `title: ""` for an empty slot.
- `service_date_display = service_date_display(d)`, and `service_date_iso` is `YYYY-MM-DD`.
- `liturgy` has only the 8 section keys, with non-blank strings and no error text.
- Example:

```json
[{"slot":"opening","title":"Holy, Holy, Holy","number":138,"hymn_id":"3f0c…","hymnal":"GG2013"},
 {"slot":"response","title":"","number":null,"hymn_id":null,"hymnal":null},
 {"slot":"closing","title":"Old Favorite","number":12,"hymn_id":null,"hymnal":"PH1990"}]
```

**Compatibility with frozen Streamlit during the overlap (until slice 7):**

| Direction | What happens | Result |
|---|---|---|
| Streamlit loads a service saved by React | The loader reads `hymns[i].get("title")` for i = 0..2 (app.py:401-404). The empty slot's `""` leaves that selectbox empty. It reads `liturgy` through the 8 keys and `service_date_iso` for the date. It ignores `custom_elements` and `hymnal`. | Correct slots. Custom elements are not shown in Streamlit (known, accepted). |
| Streamlit saves a new service | The frozen ORM omits the new columns, so they are NULL. It writes compacted `[{title, number}]`. | React reads it positionally (legacy path). |
| Streamlit re-saves a service saved by React | The frozen `update_service` rewrites `hymns` compacted, without `slot` or ids, and leaves `custom_elements` and `hymnal` untouched (possibly stale relative to the Streamlit edit). | Accepted: the tester moves after 5b. React resolves the hymns again by title and number. |
| Streamlit Prepare writes usage | Rows are added for that date. | The next React save of that date replaces them with the archive union (F§6.2). A React **delete**, or a re-dating PUT, never removes them (open question 1). |
| Usage reads | Streamlit's `get_recently_used_identifiers` reads the same rows. | Unaffected. |

Legacy `liturgy` keys outside the 8 sections (Notion era, inv E7) are not returned. They are dropped on the next save from the new app, as F§6.2 requires. Nothing is lost that the Word file ever printed.

---

## Frontend changes

### Routes and pages

- `src/app/(signed-in)/(church)/builder/review/page.tsx` renders `<ReviewStep />`, replacing slice 2's `<StepPlaceholder step="review"/>` and `<StillNeeded/>`.
- `src/app/(signed-in)/(church)/services/page.tsx` renders `<ServicesArchive />`. It is a client component.
- `AppNav` gains **Services** (F§4.2: nav items appear when their slice ships).
- **Builder shell (changed files, slice 2's):**
  - `src/lib/draft/steps.ts`: `SHIPPED_STEPS` gains `"review"`, so it holds all four steps.
  - `src/lib/draft/status.ts`: the review status (`reviewStatus(draft)`, below) and `missingItems(draft)`.
  - `src/components/builder/step-progress.tsx`: the Review item renders `reviewStatus`.
  - `src/components/builder/summary-panel.tsx`: the archive half of the status line (UX "Step status and summary panel").
  - **Deleted:** `src/components/builder/step-placeholder.tsx` and `still-needed.tsx`, with their tests. `ReviewChecklist` replaces `StillNeeded`.

### Components

| File | Purpose |
|---|---|
| `components/builder/review/review-step.tsx` | Orders the cards and reads `useDraft()`, `useChurch()` and `useMe()` |
| `…/editing-banner.tsx` | The editing, not-in-hymnal and no-date banners |
| `…/review-checklist.tsx` | `missingItems(draft)` rendered as links |
| `…/save-card.tsx` | Status line, the save button with its three labels, and "Start a new service" |
| `…/conflict-dialog.tsx` | The 409 dialog (Reload their version / Save mine as a new service / Cancel) |
| `…/documents-card.tsx` | Two download buttons, the helper when the copies are identical, the save hint |
| `…/email-slot.tsx` | A plain muted card ("Emailing the bulletin is available soon…") in 5a, not `StepPlaceholder`; **5b replaces the contents** |
| `…/order-of-worship.tsx` | The variant toggle and outline rows. Reads `useLiturgyConfig()` (slice 4) and passes `config.outline` to `orderOfWorship`; appends `config.assurance_response` under the Assurance row; skeleton and error states for the config |
| `components/services/services-archive.tsx` | Page header, infinite list, empty, error and loading states |
| `components/services/service-row.tsx` | Row with the open action, the "Editing" badge and the overflow menu (Base UI DropdownMenu) |
| `components/services/delete-service-dialog.tsx` | `ConfirmDialog` with the copy above |
| `lib/queries/use-open-service.ts` | `useOpenService()`: confirm if dirty, `fetchQuery` with `staleTime: 0`, `serviceToDraft`, `replace`, prefetch the lectionary, `router.push("/builder/review")`. Reused by the conflict dialog's "Reload". |

### Library code

**`src/lib/api/client.ts`**: `apiFetchBlob(path, opts) → {blob, filename}` (F§4.5).
- It uses the same headers, timeout, abort and error mapping as `apiFetch`. A non-2xx response parses the JSON error body into `ApiError`.
- On 2xx it returns `res.blob()` and `parseContentDispositionFilename(header)`. That parser prefers `filename*=UTF-8''…` (decoded), falls back to `filename="…"`, and returns `null` when both are missing.

**`src/lib/api/timeouts.ts`**: `documents: 30_000`.

**`src/lib/download.ts`**:
- `docxFilename(variant, dateIso)` uses the same English month table and zero-padding as `service_output`, checked against a shared fixture.
- `downloadBlob(blob, filename)` creates an object URL, clicks an `<a download rel="noopener">` attached to the body, removes it, and revokes the URL after 60 s. Revoking immediately breaks Safari.

**`src/lib/service/doc-readings.ts`**: `docReadings(payload) → {ot, nt, otAuto, ntAuto}` returns `resolveReadings(payload.scriptures, payload.selected_ot_ref, payload.selected_nt_ref)` from slice 2's `scripture-refs.ts`, unchanged. It is the TypeScript side of `resolve_doc_readings` and has no rule of its own, so it always agrees with `effectivePicks` on screen and with the Word file.

**`src/lib/service/order.ts`**: `orderOfWorship(payload, variant, outline) → OrderItem[]`, where `outline` is `config.outline` from slice 4's `useLiturgyConfig()` (`GET /liturgy/config`, the served `liturgy_config.OUTLINE`).
- It keeps **no order, anchor or heading constants**. It walks `outline` in order; each item's heading is the item's `label`, and after each item it emits the custom elements whose `insert_after` is in that item's `anchors_after`, in payload order. The anchors are emitted even when the item itself is omitted (inv E5), exactly as `build_docx` does.
- Per item, by `kind` and `value_source`:
  - `section`: emitted when `payload.liturgy[key]` has text;
  - `landmark` with `hymn_opening | hymn_response | hymn_closing`: emitted only when that slot is filled, with `line = hymnLine(title, number)` and an `inHymnal` flag;
  - `landmark` with `reading_ot | reading_nt`: from `docReadings(payload)`, omitted when null, with the `auto` flag;
  - `landmark` with `sermon_title`: always emitted, with the title (the component shows "[Sermon title]" when it is blank);
  - `landmark` with `fixed`: emitted with `fixed_text`;
  - `communion`: emitted when `payload.include_communion`, as one row.
- **Variant rules**, the only logic that is not in the outline (they mirror `service_output.VARIANTS` and `build_docx`): an empty hymn slot omits its heading, and the `prayers_of_the_people` section is pastor-only (omitted from the bulletin, tagged `pastorOnly` in the pastor's copy).
- `OrderItem.kind` is one of `section | hymn | reading | sermon | creed | communion | custom`. Each item has a `heading` plus `text` or `line`, and a `pastorOnly` flag.
- Placement labels are not needed, because custom items use their own label as the heading.
- A reorder or a renamed heading is therefore one change to `build_docx` plus `OUTLINE` (slice 4), and the frontend follows without a code change.

**`src/lib/draft/mapping.ts`**: built by 5a (F§7.2). If slice 2 shipped a provisional `draftToServicePayload`, 5a replaces it. That is safe: before 5a no draft can have `saved_fingerprint` set, because nothing could save.

`draftToServicePayload(draft) → ServiceDraft` (F§4.6). It takes **only the draft**, so the payload, and so the dirty fingerprint, never depends on church settings. A 6a change to the default hymnal therefore never makes an open or saved draft look dirty.
- `service_date_iso = readings.date_iso`.
- The occasion is trimmed. Scriptures are trimmed, with blanks dropped.
- **Picks:** `selected_ot_ref` / `selected_nt_ref` are `resolveReadings(scriptures, readings.selected_ot_ref, readings.selected_nt_ref)`'s explicit values, `otAuto ? "" : ot` and `ntAuto ? "" : nt`. A pick that is no longer one of the current picker options is sent as `""`, whatever the stored draft says. This keeps slice 2's provisional rule.
- `hymns` is keyed by slot, with `{hymn_id, title, number, hymnal}` or `null`.
- `hymnal = draft.hymns.hymnal` (null passes through). Null means "the church's effective hymnal", as in F§4.6 and slice 3. The **server** turns it into `effective_hymnal` when it stores the service (`create_service`). Slice 3's `draft.hymns.hymnal ?? effective_hymnal` is therefore still what gets archived. The fallback just moves to the server, so it is not part of the fingerprint.
- `liturgy` includes only enabled cards with non-blank text, trimmed.
- The sermon title is trimmed. Communion comes across as is.
- `custom_elements` are `{label, text, insert_after}` without `id`. Elements with a blank label are dropped; slice 4's UI doesn't allow them, so this only guards stale data.

`serviceToDraft(service, {church, user, now}) → Draft` follows F§4.6 "Loading an archived service" steps 2-5, with these details:
1. **Readings:**
   - **Always** `fields_origin: "archive"`, `reading_set: null` and `translation: null`, whether or not the service has a date. The readings step therefore never auto-fills a lectionary set over the archived occasion and scriptures.
   - `date_iso = service.service_date_iso` with `date_origin: "archive"`. If that is null, use `nextSunday(todayIn(church.timezone))` with `date_origin: "default"`, and the no-date banner shows. Slice 2's mount-time roll-forward does not touch this date, because it needs a pristine draft and `editing` is set.
2. **Hymns:**
   - Each slot comes from `service.hymns[slot]`, already normalized by the server, as `{hymn_id, title, number, hymnal}`. `in_hymnal: false` arrives as `hymn_id: null`.
   - `hymns.hymnal = service.hymnal ?? null`, `alternatives: null`, `exclude_recent: true`.
3. **Liturgy:**
   - Present sections become `{enabled: true, text, origin: "archive"}`. Absent sections become `{enabled: false, text: "", origin: "empty"}`, with no default benediction injected.
   - The sermon title comes across. Communion comes across with `communion_origin: "archive"`.
   - `custom_elements` get new ids, and each `insert_after` passes through slice 4's `normalizePlacement` (a no-op for data the server already normalized; it keeps the client safe against an older server).
4. **Bookkeeping:**
   - `editing = {service_id, saved_at, date_iso: service.service_date_iso ?? null}` (see the draft change below).
   - `saved_fingerprint = fingerprint(draftToServicePayload(result))`, so a freshly opened service is not dirty.
   - `last_step: "review"`, a new `save_key`, `save_key_fingerprint: null`, and new `created_at` and `updated_at`.

**Draft schema change (F§4.6 versioning).**
- `editing` becomes `{service_id: string; saved_at: string; date_iso: string | null} | null`.
- New `save_key_fingerprint: string | null`: the fingerprint of the payload last POSTed with `save_key` whose outcome is unknown (a network error, a timeout or a 5xx). It is null otherwise. See "Save key rule" below.
- `DRAFT_VERSION` goes from N to N+1, where N is the version current when 5a lands (1 if no earlier slice bumped it).
- Migration: `editing: null` stays null; otherwise `date_iso = readings.date_iso`. Before 5a every stored draft has `editing: null`, because nothing could set it. `save_key_fingerprint` is set to `null`.
- The migration has a unit test.

**`src/lib/draft/status.ts`**: adds `missingItems(draft)` if slice 2 did not. It covers all four steps (it replaces `stillNeeded`'s use on the Review step; with every step in `SHIPPED_STEPS`, no row is filtered out). It also adds:
- `saveMode(draft) → "new" | "update" | "copy"`:
  - `"update"` when `editing` is set and `readings.date_iso === editing.date_iso`;
  - `"copy"` when `editing` is set and the dates differ;
  - `"new"` otherwise.
- `reviewStatus(draft) → "not_in_archive" | "saved" | "unsaved_changes"`, which `stepStatus` returns for the Review step now that it is in `SHIPPED_STEPS`, and which `SummaryPanel`'s status line also reads:
  - `"not_in_archive"` when `editing === null`;
  - `"saved"` when `editing` is set and `!isDirty(draft)`;
  - `"unsaved_changes"` when `editing` is set and `isDirty(draft)`.

**`src/lib/queries/services.ts`**. Every hook uses `api.church`. Keys come from F§4.4.

- **`useServices()`:** `useInfiniteQuery` on `["church", id, "services", {limit: 20}]`. The next offset is `offset + items.length` while that is less than `total`.
- **`fetchService(id)`:** `queryClient.fetchQuery(["church", id, "service", sid], {staleTime: 0})`.
- **Save key rule** (`src/lib/draft/save-key.ts`, pure). It refines F§1.6's "replaced after the first successful POST". The idempotency store keeps 4xx responses and rejects a reused key with a different body, so a key must never outlive a definitive answer. The rule is the same as 5b's `createSendKeyTracker`, but it is persisted in the draft, so it survives a refresh.
  - `keyForPost(draft, fp) → draft'`: if `save_key_fingerprint` is set and differs from `fp`, replace `save_key` with a new UUID v4, because the uncertain attempt carried a different body. Then set `save_key_fingerprint = fp`. The request uses the resulting `save_key`.
  - `settlePost(draft, outcome) → draft'`:
    - after a **2xx** or **any 4xx** (404 hymn gone, 422 validation, 422 `idempotency_mismatch`, 401, 403): new `save_key`, `save_key_fingerprint: null`. The server has either stored a final answer under the old key or rejected it, so a corrected retry must not replay it;
    - after `network_error`, `timeout`, `aborted` or a **5xx** (the outcome is unknown): keep both. An identical retry then replays the stored 201 (or re-executes if nothing was stored), and an edited retry gets a new key from `keyForPost`.
  - Trade-off, accepted: if a POST timed out but in fact succeeded, and the user then edits before retrying, the retry creates a second service. The Services list shows both, and either can be deleted. The alternative, a stuck save for 15 minutes, is worse.

- **`useSaveService()`:** a mutation over `(draft)`.

  ```
  payload = draftToServicePayload(draft); fp = fingerprint(payload)
  mode = saveMode(draft)

  post(retried = false):
      update(d => keyForPost(d, fp)); key = latest draft's save_key
      try:
          out = POST /services (json: payload, idempotencyKey: key)
          update(d => settlePost(d, "2xx")); return out
      catch e:
          update(d => settlePost(d, outcomeOf(e)))       // 4xx → rotate; network/timeout/5xx → keep
          if e.code == "idempotency_mismatch" and not retried:
              return post(true)                         // one automatic retry, with the new key
          throw e

  if mode == "update":
      PUT /services/{editing.service_id}  (json: payload, ifMatch: editing.saved_at)
        → 404 without details.field: post() + fallback toast
        → 409: surface ConflictError (the Save card opens the dialog)
  else: post()                                          // "new" and "copy"
  onSuccess(out):
      update(d => ({ ...d,
          editing: {service_id: out.id, saved_at: out.saved_at, date_iso: out.service_date_iso},
          saved_fingerprint: fp }))                     // the payload that was sent
      setQueryData(["church", id, "service", out.id], out)
      invalidate ["church", id, "services"] and ["church", id, "hymns"]
  ```

  The conflict dialog's "Save mine as a new service" also calls `post()`. A PUT never uses `save_key`: it is naturally idempotent. Invalidating `hymns` amends the F§4.4 map: saving now writes usage, which changes `recently_used`. If the user edits while the save is in flight, the draft stays correctly dirty afterwards.
- **`useDeleteService()`:** `DELETE`, then invalidate `services` and `hymns`, and `removeQueries` for that service. If `draft.editing?.service_id === id`, run `replace(freshDraft(...))`.
- **`useDownloadDocument()`:** a mutation (never cached, per owner decision 4) that builds `payload = draftToServicePayload(draft)` at click time, calls `apiFetchBlob("/documents", {method: "POST", json: {variant, service: payload}, timeoutMs: TIMEOUTS.documents})`, then `downloadBlob(blob, filename ?? docxFilename(variant, payload.service_date_iso))`. Each variant has its own mutation instance, so each button has its own pending state.

`src/lib/api/types.ts` gains the aliases `ServiceDraft`, `ServiceOut`, `ServiceSummary`, `ArchivedHymn`, `ServicePage` and `DeletedOut`, generated from OpenAPI (F§1.11).

**State rules** (F§4.6):
- Save, download and email never clear the draft.
- Church switch remounts through the layout key, and the draft is per church, so a document or save always uses the active church's draft and header. This fixes inv A7's cross-church stale-bytes problem.
- No document bytes are ever stored.

**Handing readings to slice 2.** After `serviceToDraft`, slice 2's readings step, seeing `fields_origin: "archive"` and `reading_set: null`, must:
- fetch `["lectionary", date_iso]` for the loaded date, so the set switcher and caption belong to that date (the stale-lectionary fix);
- never overwrite occasion or scriptures automatically;
- let the user apply a set explicitly.

5a only supplies the draft fields and the prefetch.

---

## Behavior changes vs Streamlit

| # | Streamlit today | New app | Why |
|---|---|---|---|
| 1 | "Prepare" builds bytes kept in the session. They can go stale across edits, date changes, loads and church switches (inv F3, A7). | Each Download builds the file from the current draft on the server. Nothing is cached. | Owner decision 4 |
| 2 | The bulletin help and caption say "Liturgy only" / "no sermon", but the bulletin does include the sermon title (inv §0 item 2) | The content is unchanged; both copies include the sermon title. The copy is corrected, and the docstring is fixed. | Owner decision 4 |
| 3 | Usage is recorded on Prepare and only ever added, so changed picks stay counted (inv F4) | Usage is recorded on **Save**. The saved date's rows are replaced by the union of hymns from every archived service on the date, including rows Streamlit added on Prepare. Downloads and email record nothing. | Owner decision 9. The union keeps two services on one date from erasing each other. |
| 4 | — (Streamlit cannot delete services) | Deleting a service leaves `hymn_usage` unchanged, so its hymns keep counting as recently used for that date | Frozen Streamlit and history write usage that no archived service backs, and delete must not erase it (open question 1) |
| 5 | Hymn headings follow position. With no Opening hymn, the Response hymn prints as "First Hymn" (inv D6). | Headings follow slots: Opening is "First Hymn", Response is "Second Hymn", Closing is "Third Hymn". An empty slot omits its heading. | Slot-keyed storage (F§6.2) |
| 6 | A hymn without a number prints `Title — #None` | Prints `Title` | inv §4 "Content hazards" |
| 7 | With no NT pick, `scriptures[1]` prints as the NT reading, which is usually the Psalm. A pick left over from an edited scripture line could still print. | The NT reading is the first NT-classified entry other than the OT reading. It is omitted when there is none. A pick that is no longer one of the lines is ignored, so the file prints what the Bulletin readings select shows ("Automatic: …"). Both come from slice 2's `resolve_readings`. | Owner decision 9 |
| 8 | The archive does not keep custom elements, the hymnal, hymn ids or slots | It keeps `custom_elements`, `hymnal`, and 3 slot entries with `hymn_id` | Owner decision 9, F§6.2 |
| 9 | Loading keeps custom elements, translation and stale lectionary sets from the previous service. Hymns map by position from lower-cased titles and are silently dropped if renamed. The exclusion filter drops the service's own hymns (inv F6). | Loading replaces the whole draft. Custom elements and hymnal come from the service, and translation resets to the church default. The readings step reloads that date's sets. Hymns resolve by id, then by (number, title); a hymn that can't be matched is kept with a "Not in your hymnal" notice. (The own-date exclusion fix is slice 3's.) | Owner decision 9, F§4.6 |
| 10 | Loading overwrites unsaved work without asking | "Replace your unsaved draft?" confirmation | F§4.6 |
| 11 | Save and Prepare appear only after liturgy is generated | Save and both downloads are available whenever the date is valid. Missing items are listed but don't block. | F decision D9 |
| 12 | Last write wins, and any member can overwrite silently (inv F7) | `If-Match` returns 409 on a stale copy, offering "Reload their version" or "Save mine as a new service" | F§1.7 |
| 13 | Updating a deleted service silently saves a new one | Same fallback, now with a toast saying so | Clarity |
| 14 | Changing the date of a loaded service silently turns the next save into a new service | The same rule, but the button reads "Save as new service" with an explanation. An undated legacy service is also saved as a new, dated service, with its own explanation. | Parity, made visible |
| 15 | Archive: the first 20 by `saved_at`, no delete, manual "Refresh archive" (inv F5) | A paged list of all services, newest **service date** first, showing who created each and when it was last saved. Members can delete after confirming. Data refetches automatically. | Owner decision 5; findability |
| 16 | Streamlit error placeholders (`[Error generating …]`, etc.) were stored as liturgy and printed | They are dropped when a service is loaded, and never written | inv §4 "Content hazards" |
| 17 | Legacy liturgy keys outside the 8 sections sit in stored rows | Not returned, and dropped on the next save | F§6.2 |
| 18 | Raw exception text: "Archive save failed: {e}", tracebacks on Prepare | Typed messages only. Unexpected failures show "Something went wrong. (Ref: …)". | F§1.5 |
| 19 | The download filename uses the *current* date, even for stale bytes | The filename comes from the date in the posted draft, through `Content-Disposition` | F§1.9 |

Unchanged on purpose:
- the document layout, fonts, section order, communion text, "Apostles' Creed", and the Assurance response;
- `saved_at` bumping on every save;
- multiple services on the same date being allowed;
- only the bulletin copy being emailable (5b);
- the OT fallback `selected_ot_ref or scriptures[0]`, where a stale pick counts as no pick (open question 2).

---

## Testing

### Backend (pytest, from the repo root; F§5.1)

Characterization comes first (F§2.3.1). `backend/tests/test_build_docx_characterization.py` is written **before** `build_docx` changes and runs against the current signature. It uses a helper, `docx_outline(bytes)`, that reads the paragraphs with python-docx and returns `(style, text, bold)` tuples. It pins:
- the title and date lines;
- the heading sequence for the bulletin and the pastor's copy, with all 8 sections, 3 hymns, both readings, the sermon, communion on, and one custom element at every placement;
- Leader/People bolding in the Call to Worship, bold Confession, and the Assurance response line;
- "[Sermon title]" for a blank sermon title;
- anchors emitted when their section is absent;
- keys outside the 8 sections being ignored.

When the refactor lands, this file is updated **only** where a behavior change above requires it: slot mapping, `#None` and the NT fallback.

`test_service_output.py`:
- `service_date_display` zero-pads and is locale-independent (the test sets `LC_TIME` to a non-English locale when one is available, else skips that case);
- `normalize_date_iso`: `"2026-10-04"` stays; `"2026-10-04T00:00:00.000Z"` becomes `"2026-10-04"`; `""`, `None`, `"October 4"` and `"2026-02-30"` become `None`;
- `stored_hymn_entries` and `slot_map`: a non-list value gives `[]`; non-dict entries, non-string titles and blank titles become `None`, and parsing never raises; `number` is coerced; a 4th entry is kept by `stored_hymn_entries` but ignored by `slot_map`; slot-keyed and positional mapping;
- `docx_filename` against the shared fixture `backend/tests/fixtures/shared/docx_filenames.json`;
- `hymn_line` with and without a number;
- `resolve_doc_readings` **and** `scripture_refs.resolve_readings` (projected to `(ot, nt)`) both run every case of `shared/doc_readings.json` and must give its expected pair. The fixture covers:
  - RCL order with no picks, where the NT reading is the second reading and not the Psalm;
  - only OT and Psalm, where the NT reading is None;
  - a gospel-only NT;
  - an `' or '` entry;
  - selected refs winning;
  - Easter order, where Acts comes first;
  - blank entries;
  - **stale picks**: an NT pick that is no longer a line, and a Psalm sent as the NT pick, each giving the automatic reading;

  Slice 2's `scripture_refs.json` carries the same cases; `resolve_doc_readings` also runs every `resolve_readings` case of that file and must equal its `(ot, nt)`, which pins the delegation;
- **stale pick in the document:** `render_docx` (through `build_document`) with the lines Isaiah 5:1-7 / Psalm 80:7-15 / Philippians 3:4b-14 / Matthew 21:33-46 and `selected_nt_ref = "Matthew 21:33-40"` (no longer a line) prints "Philippians 3:4b-14" under "New Testament Reading", the same reading `resolve_readings` reports as automatic;
- `stored_hymns` shape, with 3 entries and `""` for an empty slot;
- `is_legacy_error_placeholder`, including the three real strings and the negative case "[Sermon title]";
- `content_disposition` matching F§1.9 exactly.

`test_order_of_worship_fixture.py`. The order comes from slice 4's `OUTLINE`; 5a adds no order of its own.
- **Fixture source.** `shared/order_of_worship.json` holds only cases (variant × which slots are filled × communion × custom elements × whether Prayers of the People is present) and their `expected_headings`. The expected headings are **generated** from `shared/liturgy_outline.json` (slice 4's serialized `OUTLINE`) plus the two variant rules, by the helper `expected_order(outline, payload, variant)` in this test module: walk the outline, emit each item's label unless the item is omitted (an empty hymn slot, an absent section or reading, communion off, `prayers_of_the_people` in the bulletin), then `CE:{label}` for the custom elements anchored after it. A test regenerates the file and fails with "regenerate order_of_worship.json" if the committed copy differs, so a change to `OUTLINE` shows up as a fixture diff.
- **Docx check.** For each case, `render_docx` then `docx_outline`. The six fixed communion H2s after the H1 collapse into one "The Sacrament of the Lord's Supper" item, and the result must equal `expected_headings`.
- Slice 4's `test_liturgy_config.py` keeps `liturgy_outline.json` equal to `OUTLINE`, so the chain `OUTLINE` → `liturgy_outline.json` → `order_of_worship.json` → docx is closed.

`test_archive_usecase.py` (SQLite `tmp_db`):
- create writes 3 slot entries exactly, the display date, only non-blank liturgy keys from the 8, `custom_elements` and `hymnal`;
- an empty slot is stored with `"hymn_id": null` (JSON null, not the string `"None"`), and a filled slot with the id as a string (`_hymn_snapshot`);
- `hymnal: null` in the input is stored as `effective_hymnal`: the church default when it is valid, else the alphabetically first hymnal, and `null` for a church with no hymns (a snapshot pick's own `hymnal` stays in its slot entry; there is no first-pick fallback);
- a hymn id resolves from the database and the client's title is ignored;
- a hymn id from another church, or a deleted one, gives `NotFound` with `details.field == "hymns.response.hymn_id"`;
- a null-id snapshot is kept, and a null id with a blank title gives an empty slot;
- a blank custom label gives `InvalidInput` on field `custom_elements.1.label`;
- **usage:**
  - after a save, the date's rows equal that service's hymns;
  - a second service on the same date gives the union;
  - rows added earlier by `record_usage` for that date are replaced;
  - NULL-number duplicates collapse into one row, and titles that differ only in case or inner whitespace collapse by `usage_key`;
  - **a malformed legacy row on the same date** (`hymns` set to a string, a dict, and a list holding `None`, `42` and `{"title": 7}`) is skipped: the save succeeds, and the usage equals the valid services' union;
  - a legacy row whose `service_date_iso` has a time part is included in its date's union;
  - a PUT that changes the date rebuilds the new date and **leaves the old date's rows unchanged**;
  - **delete leaves `hymn_usage` unchanged**, including rows written by `record_usage` (the Streamlit Prepare path) for that date;
  - `rebuild_usage_for_date` with `None`, `""` or `"2026-13-01"` raises `ValueError` and writes nothing;
  - `build_document` writes no usage;
- **atomicity:** monkeypatch `rebuild_usage_for_date` to raise, then assert no service row and no usage change;
- **`If-Match`:** equal passes; a mismatch raises `Conflict` with `details.current_saved_at`; missing or malformed raises `InvalidInput`; a naive SQLite value compares equal to its `+00:00` form;
- **`get_service` normalization:**
  - a legacy compacted `[{title, number}]` maps by position;
  - a matching `(number, normalize_title)` resolves the id, preferring the entry's hymnal, then the service's hymnal, then `effective_hymnal`;
  - a title that appears twice in the preferred hymnal, with `number` null, resolves to the lowest number, then the lowest id, on every run;
  - an unmatched hymn is kept with `in_hymnal: false`;
  - non-dict entries become empty;
  - unknown liturgy keys and placeholders are filtered;
  - NULL `custom_elements` becomes `[]`;
  - **a stored custom element with `insert_after: "bogus"` (or no `insert_after`) is returned with `"end"`, not dropped**, alongside a valid one that keeps its placement and order;
  - **that element survives load then save:** `replace_service` with the input built from the normalized `get_service` output stores it with `insert_after: "end"` and its label and text unchanged;
  - an invalid `service_date_iso` becomes null, and one with a time part becomes its first 10 characters;
- **list:** order by date desc with NULL and `''` dates last, `total`, the `offset` window, `service_date_iso` normalized exactly as in `get_service`, `created_by` name falling back to the email, and a removed author (`created_by` NULL) giving `null`.

`test_services_streamlit_compat.py`:
- a React-saved row with an empty Opening slot, read with the frozen loader expression copied from app.py:401-404 (`[(h[i].get("title") or "").strip().lower() for i in range(3)]`), gives `["", "b", "c"]`;
- `save_service` without the new keyword arguments leaves NULLs;
- `update_service` without them leaves existing `custom_elements` and `hymnal` untouched.

The existing tests `test_service_archive.py` and `test_hymn_usage.py` pass unchanged.

`test_api_services.py` and `test_api_documents.py` (TestClient + `jwt_helpers`):
- **Happy paths:**
  - list, get, create (201), update, delete (`DeletedOut`, `{"deleted": true}`);
  - a service stored with a custom element whose `insert_after` is `"bogus"`: GET returns it with `"end"`, and a PUT of the returned `custom_elements` succeeds and keeps the element;
  - documents for both variants: the body starts with `PK`, and the exact `Content-Type`, `Content-Disposition` and `Cache-Control: no-store` headers are present;
  - with an allowed `Origin`, `access-control-expose-headers` includes `Content-Disposition`;
  - the bulletin outline contains "Sermon Title" and not "Prayers of the People", while the pastor's copy contains both.
- **Roles:** a **member**, an admin and the owner each succeed on POST, PUT, DELETE and `/documents` (owner decision 5).
- **Isolation:**
  - `assert_church_isolated` on `GET`, `PUT` and `DELETE /services/{id}`, and on `GET /services` (a non-member gets 403, and church A's member using church B's service id gets 404);
  - POST `/services` and `/documents` with church B's hymn id give 404 with `details.field`, and nothing is written.
- **Errors, asserting code and exact message:**
  - a malformed UUID gives 422;
  - `limit=0` and `limit=201` give 422;
  - an unknown field in the body gives 422 with `fields`;
  - a bad `insert_after` in a request body still gives 422 with `fields["custom_elements.0.insert_after"]` (only stored data is normalized);
  - a missing `If-Match` gives 422;
  - a stale `If-Match` gives 409 with the exact message;
  - PUT on an unknown id gives 404 without `details`.
- **Idempotency:** replaying POST `/services` with the same `Idempotency-Key` returns the same body and creates one row. The same key with a different body gives 422 `idempotency_mismatch`. A POST that got the hymn 404 under key K, retried with K and a corrected body, also gives `idempotency_mismatch`, and the same corrected body with a new key gives 201. This pins the server behavior that the client's key rule depends on.
- **python-docx missing:** monkeypatch `worship_service.Document = None`. The response is 500 `internal_error` with the uniform body and `request_id`, and nothing is written.

Guard and contract:
- `test_route_guards.py` passes with no allowlist change, because every new route depends on `require_church`;
- `test_openapi_contract.py` passes after running `export_openapi.py`;
- `test_no_streamlit_in_core.py` covers the new modules.

Migrations: `test_migrations.py`, with 0005 up, down and up again, and a single Alembic head. A focused test inserts a `services` row through Core without the new columns and succeeds.

Postgres (`@pytest.mark.postgres`):
- two threads saving **different** services for the same date concurrently, sharing hymns in opposite slot orders, repeated 20 times: no `IntegrityError`, no `DeadlockDetected`, and afterwards the date's usage rows equal the **full** union (the advisory lock makes this exact);
- two concurrent PUTs with the same `If-Match`: exactly one 200 and one 409, thanks to the row lock;
- `nulls_last` ordering matches SQLite.

### Frontend (Vitest 3; F§5.2)

Unit tests (`*.test.ts`):
- **`download.test.ts`:** `docxFilename` against `docx_filenames.json` (read with `fs`); `parseContentDispositionFilename` handles `filename*` first, a plain quoted `filename`, and a missing header.
- **`client.test.ts` (`apiFetchBlob`):**
  - a 2xx response returns a blob and the filename;
  - a JSON error becomes `ApiError` with `code`, `details` and `requestId`;
  - network failure → `network_error`, timeout → `timeout`, abort → `aborted`;
  - it sends `X-Church-Id` and `Authorization`.
- **`doc-readings.test.ts`:** every case of `doc_readings.json` (including the stale-pick cases) through both `resolveReadings` and `docReadings`, which must agree with each other and with the expected pair; `docReadings(payload)` equals `effectivePicks` for a draft with the same lines and picks.
- **`order.test.ts`:** for every case of `order_of_worship.json`, `orderOfWorship(case.payload, case.variant, outline)`, with `outline` read with `fs` from `liturgy_outline.json`, gives headings equal to `expected_headings`. A second check passes a reordered copy of the outline and asserts the items follow it, which proves the function holds no order of its own.
- **`mapping.test.ts`:**
  - `draftToServicePayload`: disabled cards dropped, blank card text dropped, scripture trimming, slot-keyed hymns with nulls, `hymnal` passed through (null stays null), custom-element `id` stripped and blank labels dropped. It takes only the draft, so its output is the same whatever the church's default hymnal is;
  - **stale pick:** a draft whose `selected_nt_ref` is no longer one of its lines (as left by a refresh while the textarea had focus) produces `selected_nt_ref: ""`, and a valid pick is sent trimmed;
  - `serviceToDraft`: each rule in the Frontend changes section, including null date → default plus `date_origin: "default"` **and `fields_origin: "archive"`**; `in_hymnal: false` → `hymn_id: null`; absent benediction → disabled with no default; new custom-element ids; a custom element with an unknown `insert_after` is kept with `"end"`; `editing.date_iso`; `save_key_fingerprint: null`;
  - **round trip:** `isDirty(serviceToDraft(x))` is false.
- **`migrate.test.ts`:** N → N+1 with `editing` null and non-null; `save_key_fingerprint` becomes null.
- **`status.test.ts`:** `saveMode` new, update and copy, and copy when `editing.date_iso` is null; `missingItems` each row, for all four steps; `reviewStatus` gives `not_in_archive` with `editing` null, `saved` when editing and clean, and `unsaved_changes` when editing and dirty; `stepStatus` for Review returns `reviewStatus` (not the unshipped label), and `SHIPPED_STEPS` has all four steps.
- **`save-key.test.ts`:** `keyForPost` keeps the key with no pending fingerprint or the same one, and rotates it when the pending fingerprint differs; `settlePost` rotates and clears after 2xx and after 400, 404 and 422 (including `idempotency_mismatch`), and keeps both after `network_error`, `timeout`, `aborted` and 500/502/503.
- **`fake-api.test.ts`:** the extended `installFakeApi` (below) passes a handler's `Response` through unchanged, turns `{status, body: Blob, headers}` into a `Response` with those headers, and still returns JSON for a plain object.

**Test harness extension (5a-2).** F§5.2's `installFakeApi` returns only JSON responses. 5a-2 extends `src/test/fake-api.ts` so that a handler may return:
- a `Response`, which is returned as it is; or
- `{status?: number, body: Blob | string, headers?: Record<string, string>}`, which is wrapped in a `Response` with exactly those headers.

A plain object keeps today's JSON behavior, so existing tests are unaffected. The download tests use it for a docx `Blob` with `Content-Disposition`, and for a response without that header.

DOM tests (`*.test.tsx`), using `renderWithProviders` and `installFakeApi`. `URL.createObjectURL` and `revokeObjectURL` are stubbed.

`review-step.test.tsx`:
- **New save:** POST carries `Idempotency-Key === draft.save_key` and `X-Church-Id`; the status becomes "Saved to the archive · …"; `save_key` rotates.
- **Editing save:** PUT carries `If-Match` equal to `editing.saved_at`.
- **Date changed:** the button reads "Save as new service", and the request is a POST.
- **409:** the dialog shows the server message. "Reload their version" GETs and replaces the draft. "Save mine as a new service" POSTs.
- **PUT 404 without details:** it falls back to POST and shows the fallback toast.
- **Hymn 404:** a toast with slice 4's message and "Go to Hymns".
- **Hymn 404 → replace → save succeeds:** the first POST gets a 404 with `details.field`. The test replaces the hymn in the draft and saves again. The second POST carries a **different** `Idempotency-Key` and gets a 201.
- **Timeout → edit → save:** the first POST times out. The test edits the occasion and saves again. The second POST carries a different key.
- **Timeout → unchanged retry:** the first POST times out. Saving again without edits reuses the same key.
- **`idempotency_mismatch`:** the fake returns 422 `idempotency_mismatch` once. The client retries exactly once with a new key, the retry succeeds, and no error is shown.
- **No-date service:** after opening a service with `service_date_iso: null`, the advice banner and the "has no date" explanation show, and Save is enabled. After a successful save, the banner is gone.
- **Invalid date:** Save and both downloads are disabled, and the note is shown.
- **Downloads:**
  - the bulletin download POSTs `/documents` with `variant: "bulletin"` and the payload, and `downloadBlob` receives the header filename;
  - a missing header falls back to `docxFilename`;
  - an error toasts the server message;
  - the identical-copies helper appears when Prayers of the People is disabled;
  - the save hint appears after a download while the draft is unsaved.
- **Order of worship:** the fake serves `GET /liturgy/config` with the outline from `liturgy_outline.json`; the rows follow it, and the toggle shows "Pastor's copy only" on Prayers of the People. While the config is pending, skeleton rows show; when it fails, `ErrorState` shows and Save and both downloads stay enabled.
- **Start a new service:** a dirty draft asks first; a clean one doesn't.
- **Step status and summary** (rendered inside `BuilderShell`): `StepProgress`'s Review item reads "Not in archive" for a fresh draft, "Saved" after a successful save, and "Unsaved changes" after the occasion is then edited. `SummaryPanel`'s status line reads "Draft saved on this device · Not in archive", then "… · In archive (saved …)", then "… · Unsaved changes". `SummaryPanel` contains no "available soon" text (case-insensitive), the Review step contains it only inside the email card (until 5b), and no `StepPlaceholder` renders.

`services-archive.test.tsx`:
- skeleton while loading;
- an empty state with "Build a service";
- an error state whose Retry refetches;
- rows and "Showing 20 of 45" then "Show more" requests `offset=20`;
- line 3 reads "Created by {name} · last saved …", or "Last saved …" when `created_by` is null;
- **Open:** a clean draft opens without a dialog and navigates to `/builder/review` with the draft replaced; a dirty draft shows "Replace your unsaved draft?"; a 404 shows the toast;
- **Delete:** the confirmation copy; a DELETE request on confirm; the row disappears; deleting the service being edited adds the extra line and resets the draft;
- the "Editing" badge.

### Manual checks (appended to `docs/manual-verification.md` as "Slice 5a"; production Vercel URL, at 375 px on an iPhone with Safari and on desktop Chrome)

1. Build a service. **Download bulletin copy.**
   - iOS shows the share or preview sheet with `worship_October_04_2026.docx` (for that date).
   - The file opens in Word or Files.
   - The sermon title is present and Prayers of the People is absent.
2. Enable Prayers of the People with text. The **pastor's copy** includes it and the bulletin copy does not. With it disabled, the helper "Same as the bulletin copy…" appears.
3. Leave Opening empty and pick Response.
   - The document shows "Second Hymn" and no "First Hymn".
   - A hymn without a number shows no "#None".
4. Use RCL readings with no NT pick. The NT reading is the epistle, not the Psalm. Then pick the Gospel as the NT reading and edit that scripture line: the Bulletin readings select shows "Automatic: {epistle}", and a fresh download prints that same epistle.
5. **Save to archive.**
   - Services shows the service at its date position.
   - The summary panel reads "In archive", and the Review step in the progress bar reads "Saved". After an edit, both say "Unsaved changes".
   - Within 12 weeks, the hymns step for another date marks these hymns as recently used.
6. Edit and **Save changes**. In a second browser holding the old copy, save: the conflict dialog appears, and both "Reload" and "Save as new" work.
7. Change the date while editing. The button reads "Save as new service", and both services exist afterwards.
8. With a dirty draft, open an archived service from Services.
   - The confirmation appears.
   - Step 1 shows that date's reading sets without changing the occasion or readings.
   - Custom elements and the hymnal are restored.
9. Delete a service with confirmation. Deleting the service being edited resets the draft. Its hymns are still marked as recently used on the hymns step for a nearby date.
10. Open a React-saved service, including one with an empty Opening slot, in **frozen Streamlit**. The hymns are in the right slots.
11. On desktop Chrome, the download has the server filename.
12. Switch church. Services lists only that church's services, and downloads use that church's draft.
13. No horizontal scroll at 375 px on `/builder/review` and `/services`. Every tap target is at least 44 px.
14. Regression pass: sign in, switch church, open every nav item. Run the Streamlit smoke check (F§6.3).

---

## Acceptance criteria

1. `POST /documents` returns a valid `.docx` for `bulletin` and `pastor`, with exactly the F§1.9 `Content-Type`, `Content-Disposition` and `Cache-Control: no-store`. `Content-Disposition` is readable cross-origin. *(test)*
2. Both variants include "Sermon Title". Only `pastor` includes "Prayers of the People", and only when it has text. No user-facing copy calls the bulletin "no sermon" or "Liturgy only". *(test + grep)*
3. Hymn headings follow slots. An empty Opening slot never moves another hymn into "First Hymn". No document contains `#None`. *(test)*
4. The shared fixtures `docx_filenames.json`, `doc_readings.json` and `order_of_worship.json` pass in both pytest and Vitest. `resolve_doc_readings` and `docReadings` delegate to slice 2's `resolve_readings` / `resolveReadings`, so a stale pick prints the automatic reading the screen shows, and `draftToServicePayload` never sends a pick that is not a current option. `orderOfWorship` takes slice 4's `outline` and holds no order, anchor or heading constants; `order_of_worship.json` is generated from `OUTLINE` and matches the docx. *(CI)*
5. The build_docx characterization test passes. It differs from pre-5a output only in the documented changes (behavior changes 5-7). *(test)*
6. `POST /services` and `PUT /services/{id}` store `hymns` as exactly 3 slot-ordered entries with non-null titles. They store `service_date_display` in `'%B %d, %Y'`, `liturgy` with only the 8 keys (non-blank, no placeholders), and `custom_elements` and `hymnal`. *(test)*
7. After any save, the saved date's `hymn_usage` rows equal the union of hymns from the church's archived services on that date, deduplicated by slice 3's `usage_key`. A malformed legacy row on that date is skipped and does not fail the save. **A delete leaves `hymn_usage` unchanged**, and so does the old date of a date-changing PUT. `/documents` writes no usage. A failure during the usage rebuild rolls back the service write. On Postgres, concurrent saves for one date produce the full union with no deadlock. *(test, including the Postgres job)*
8. `PUT` without `If-Match` returns 422. With a stale `If-Match` it returns 409 `conflict` with the exact F§1.7 message. On Postgres, two concurrent PUTs with the same `If-Match` give exactly one 200. *(test, including the Postgres job)*
9. Replaying `POST /services` with the same `Idempotency-Key` returns the first response and creates one row. The client rotates `save_key` after any 2xx or 4xx from `POST /services`, and reuses it only after a network error, timeout or 5xx with an unchanged payload. After a hymn 404, a corrected save succeeds at once, and an `idempotency_mismatch` is retried once with a new key. *(test)*
10. Every new route:
    - allows a member;
    - returns 403 to a non-member;
    - returns 404 when church A's member acts on church B's service;
    - returns 404 with `details.field` for church B's hymn id.

    `DELETE /services/{id}` returns `DeletedOut` from `api/schemas.py`, which 6a and 6b reuse. `test_route_guards.py`, `test_openapi_contract.py` and `test_no_streamlit_in_core.py` pass. *(CI)*
11. The `services_extras` revision (`0005`, or the next free number at merge), including `ix_services_church_date`, upgrades and downgrades on SQLite and Postgres, sits on the single Alembic head, and leaves `alembic check` clean. A `services` insert without the new columns succeeds. `update_service` without the new arguments leaves them unchanged. *(CI)*
12. `GET /services/{id}`:
    - maps legacy compacted hymn lists positionally;
    - resolves hymns by id, then by (number, normalized title), with the documented hymnal preference and a deterministic tie-break;
    - otherwise returns the snapshot with `in_hymnal: false`;
    - filters placeholders and unknown liturgy keys;
    - maps each stored custom element through `normalize_placement`, so an unknown placement becomes `"end"` and the element survives a load followed by a save;
    - normalizes `service_date_iso` with the same helper that `GET /services` uses.

    *(test)*
13. `serviceToDraft` and `draftToServicePayload` follow F§4.6 as refined here, and a freshly opened service is not dirty. `serviceToDraft` always sets `fields_origin: "archive"`. `draftToServicePayload` takes only the draft, so changing the church's default hymnal never makes a draft dirty. The draft migration N → N+1 is tested. *(test)*
14. The Review step saves (POST, then PUT), handles 409 (Reload, Save as new), falls back from PUT 404 to POST, and disables Save and Download only for an invalid date. The Services page pages, opens (with confirmation when dirty) and deletes (with confirmation; resets the draft when it deletes the service being edited). `SHIPPED_STEPS` holds all four steps; the Review item shows "Not in archive", "Saved" or "Unsaved changes"; the `SummaryPanel` status line shows the archive state; nothing in the builder reads "Available soon" except the email card until 5b; `StepPlaceholder` and `StillNeeded` are deleted. *(DOM tests)*
15. On the deployed app:
    - both downloads work on iOS Safari and desktop Chrome with the server filename;
    - a React-saved service opens in frozen Streamlit with the hymns in the right slots;
    - `/builder/review` and `/services` have no horizontal scroll at 375 px.

    *(manual; F acceptance 16)*

---

## Risks and open questions

**Open questions** (not covered by the owner's decisions)

1. **Should deleting a service change hymn usage?** **Default: no. A delete, and the old date of a re-dating PUT, leave `hymn_usage` untouched, at least until Streamlit is retired in slice 7.** Owner decision 9 covers replacing a date's usage on **save** only. Rebuilding on delete would go further and erase rows that no archived service backs:
   - **The coexistence case.** During phase B (F§6.3), the tester builds real services in frozen Streamlit, and Prepare records usage whether or not the service is archived (inv F4; app.py:1002-1003, 1025-1026). Take this sequence: (1) the tester tries the new app and saves a trial service for Sunday D; (2) in Streamlit, they build the real service for D and Prepare it, which adds usage rows; (3) back in the new app, they delete the trial. A rebuild on delete would recompute D from the archive alone. That erases the real Prepare rows for D, and the 12-week exclusion silently stops working for those hymns. F§6.2 accepts replacing Prepare rows on a React **save** only (owner decision 9), not on a delete.
   - **Imported history.** `migrate_to_db.py` imported usage rows that no archived service backs. A rebuild on delete would erase them too.
   - **Last Sunday.** Deleting last Sunday's service would stop its hymns counting as recently used.

   The cost of the default: deleting an abandoned planned service keeps its hymns counted as recently used near that date, until another save on that date rebuilds it. The user can also turn off "Exclude" on the hymns step. Slice 7 may revisit this, once Streamlit no longer writes usage, by adding the rebuild to `delete_service`, which is a one-line change. If the owner wants the rebuild before then, they must sign off with the coexistence case above spelled out.
2. **The OT fallback when the first reading isn't from the Old Testament.** The OT rule is unchanged: `selected_ot_ref or scriptures[0]`. In Easter season the first RCL reading is from Acts, so with no OT pick the document prints Acts under "Old Testament Reading", as it does today. Options: (a) keep parity (**default**); (b) use the first OT-classified reading and omit the section when there is none, which in Easter would print only the Psalm under that heading. The decision covered the NT fallback only.

**Risks**

- **iOS Safari and programmatic downloads after an `await`.** Safari may treat the delayed `a.click()` as unrelated to the user's tap. **Fallback, if manual check 1 fails:** after the blob arrives, the button changes to "Save {filename}", a real `<a download>` link, and a second tap downloads the file. `downloadBlob` stays the single place to change.
- **Concurrent saves for the same date.** Without a lock, under READ COMMITTED, two transactions could each rebuild the union without seeing the other's uncommitted row. They could also deadlock when they insert shared hymns in different orders. `rebuild_usage_for_date` therefore takes `pg_advisory_xact_lock` per (church, date) and inserts in sorted order, and the Postgres test asserts the full union and no deadlock. The lock is held only for the rest of the save transaction, which takes milliseconds. Frozen Streamlit's `record_usage` does not take it, which is no worse than today.
- **A timed-out save that actually succeeded, followed by an edit.** The save key rule then sends a new key, and a second service is created. This is accepted: the alternative is a save that stays stuck on `idempotency_mismatch` for up to 15 minutes. Both services appear in the list, and either can be deleted.
- **Frozen Streamlit re-saving a React service during the overlap.** It compacts `hymns` (no slots or ids) and leaves `custom_elements` stale. React reads it back positionally. This lasts only until the tester moves after 5b (F§6.3).
- **Renamed hymns.** An archived service shows the hymn's *current* title and number when its id still resolves (F§1.3). Documents regenerated from an old service therefore reflect hymnal edits. This is intended ("latest state", owner decision 4), but it differs from a frozen snapshot.
- **Parallel slices and `DRAFT_VERSION`.** Slices 3 and 4 may also bump the draft version. 5a takes the next number at merge time and chains its migration after theirs. A rebase must renumber.
- **Parallel slices and Alembic.** 6b-1's `invites_integrity` may merge before 5a-1; 6b-2's `memberships_one_owner` and slice 7's `normalize_legacy_data`, `contract_after_cutover` and `encrypt_gmail_tokens` come later. 5a-1's `down_revision` is the head at merge time, and its file number follows merge order (see "Data and migrations"; F§3.5). `test_migrations.py`'s single-head assertion catches a mistake in CI.
- **`liturgy_config` and the shared schemas.** The build order puts slices 3 and 4 before 5a. If slice 4 has somehow not created `liturgy_config.py`, 5a-1 creates it with only `CUSTOM_PLACEMENTS` (moved verbatim from app.py:148-166), `PLACEMENT_KEYS`, `normalize_placement`, `OUTLINE` and `LIMITS`, exactly as slice 4's spec defines them, and slice 4 then extends it. 5a-2's order-of-worship card needs slice 4's `GET /liturgy/config` and `liturgy_outline.json`, so 5a-2 does not merge before slice 4. If `SectionKey`, `HymnRef` or `SlotHymns` is somehow missing from `api/schemas.py`, 5a-1 adds it with the exact shape frozen in F§1.3.
- **Order-of-worship drift.** `orderOfWorship` has no order of its own and `order_of_worship.json` is generated from `OUTLINE`, so the only way the Review card and the Word file can disagree is a `build_docx` change without the matching `OUTLINE` change. Slice 4's outline/docx test and 5a's docx fixture test both fail in that case.
