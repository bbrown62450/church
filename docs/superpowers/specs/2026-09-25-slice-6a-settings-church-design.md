# Slice 6a: Settings for church profile, contacts, hymns, hymnals, liturgy prompts, translation and benediction — Design

**Status:** Draft  **Depends on:** 1, 2, 3, 4, 5b (and coordinates with 6b)  **Size:** M

**Date:** 2026-09-25
**Inputs:**
- Foundations: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, cited as "F §n". This spec follows it and does not restate its conventions.
- Inventory: `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md`, cited as "inv §n". It is the source of truth for current behavior.
- Owner decisions 5 and 9, plus decisions 1 and 7 where the builder or the switchover is affected.
- **Amendment 2026-09-26: the service rubric (PR #4, merged).** `docs/superpowers/specs/2026-09-25-service-rubric-design.md` shipped the rubric's storage, defaults, validation and the `GET`/`PATCH /rubric` API (inv §1 G11), and left "the rubric editor" to this slice. 6a adds the **Rubric** page over the existing routes (UX §6, API, Testing). It also moves the PATCH write under this slice's locking rule, with no change to the route's request or response shape beyond one additive field.
- **Amendment 2026-09-26: the prayer library (PR #7, merged).** `docs/superpowers/specs/2026-09-26-prayer-library-design.md` is the source for the **Prayers** page, its three routes and the voice-profile draft. It is new-app only. This spec adds short pointers (UX §5, API, Backend, Testing, Acceptance) and does not repeat that spec.
- **Amendment 2026-09-26: hymn year and familiarity (owner decision, index §6 question 23).** A hymn's `text_year` and `hymnal_count` can be edited by hand in the hymn dialog (In scope, UX §2, API, Testing, acceptance 25; Open question 4 is answered). The owner approved this for admins, so the two fields are admin-only inside the hymn routes, which stay open to members for every other field (decision 5): a member sees them read-only, and a member's request that sets either one gets the role 403 (Semantics → POST /hymns).

---

## Goal

Move the church-level Settings tabs out of Streamlit and into the new app, so that after 6b ships the tester never has to open Streamlit (F §6.3, phase D). This slice covers the Streamlit tabs **Church profile**, **Contacts**, **Hymns** and **Liturgy prompts** (inv §1 G1–G6) and the per-church settings the new builder already reads:
- default Bible translation (written here; read since slice 2);
- default hymnal (written here; read since slice 3);
- default benediction (written here; read since slice 4).

It also puts hymnal import in the app (inv §1 H3) so admins can add bundled hymnals (owner decision 9). Every edit is enforced on the server by role, church-scoped, and visible to the builder without a reload.

*Amendment 2026-09-26:* it also adds the **service rubric editor** (PR #4, read since slices 3 and 4) and the **prayer library** page (PR #7, read since slice 4). Neither has a Streamlit tab: the rubric has had no editor anywhere, and the prayer library is new-app only.

---

## Scope / Out of scope

### In scope

| Inventory item | What 6a does |
|---|---|
| G1 Settings shell and permission helpers (settings.py:33-55) | Role checks become route guards (`require_church` / `require_admin`). Validation moves to `usecases/church_admin.py` and `usecases/hymn_library.py`. The settings layout itself comes from 5b. |
| G2 Church profile (settings.py:61-74, 192-216) | `/settings/church`: name and timezone with an IANA check, in one transaction with the other profile fields. |
| G3 Default Bible translation (settings.py:162-168, 198-208) | The same form and the same transaction. Only changed fields are written. |
| Decision 9: default benediction (inv §1 E3; app.py:67) | A new profile field stored in `churches.settings.default_benediction`. |
| Decision 9: default hymnal (inv §1 D2) | A new profile field stored in `churches.settings.default_hymnal`. |
| G4 Contacts (settings.py:77-87, 261-284) | Add, edit (new) and delete (with confirmation), for admins. Every member can read the list. |
| G5 Hymn library (settings.py:90-107, 286-312) | Full list with search, a hymnal filter and paging; add and edit (new) for **members** (decision 5). Delete (with confirmation) also stays open to members as **Streamlit parity** (settings.py:303-306), pending the owner's answer to Open question 2. |
| H3 Hymnal import / decision 9: bundled hymnals | `GET /hymnal-sources`, `POST /hymnals` and `DELETE /hymnals/{code}` for admins. The CSV moves to `backend/seed/hymnals/PH1990.csv`. The CLI is kept. |
| G6 Liturgy prompts (settings.py:141-159, 218-259) | `/settings/liturgy`: read for members; save, per-prompt reset and reset-all for admins. Templates are validated on save. |
| F §7.2 row 6a | `usecases/church_admin.py`, the locked settings merge (F §1.7), `backend/seed/hymnals/` + `hymnal_sources.py`, and a fully populated settings section nav (the 6a entries). |
| F §7.4: `_merge_settings` race, Settings→builder hymn invalidation, timezone IANA check on edit, the "Halverson" literal (edit side), church default translation invalidation | Resolved as described below. |
| Hand-offs from 5b (5b spec, "Dependencies and hand-offs") | Contacts validate with 5b's `email_addresses.normalize_address`; the four entries are prepended to `SETTINGS_SECTIONS` in `sections.ts`; the `LegacySettingsNote` is narrowed to people and invites; the admin-only **Manage contacts** link goes into the email dialog's empty state; `MALFORMED_CONTACT_HINT` in `usecases/email.py` changes from "An admin can remove it and add it again in the current app's Settings." to **"An admin can fix it in Settings → Contacts."** (contacts can now be edited here). |
| Hand-off from 2 (slice 2, "Configuration exception") | `ESV_API_KEY` moves into `api/settings.py` and is passed to `scripture_fetcher` (F §2.3.5). The one `streamlit_tests` assertion this breaks is ported, and its file deleted in the same PR (Testing). |
| Hand-off from 3 | `SETTINGS_HYMNS_READY` in `src/lib/features.ts` is set to `true`, so the builder's empty-hymnal state links to `/settings/hymns`. |
| Hand-off from 4 | In the Benediction card's origin-`default` hint ("Your church's default benediction. Admins can change it in Settings."), the word "Settings" becomes a link to `/settings/church`. |
| streamlit_tests assertions for these tabs (inv §6) | Ported to backend tests (see Testing). |
| G11 service rubric (PR #4; amendment 2026-09-26) | `/settings/rubric`: read for members, edit for admins, over the existing `GET`/`PATCH /rubric`. The PATCH write moves into `usecases/church_admin.update_rubric` under `lock_and_read_actor`, and `GET` gains an additive `defaults` field. |
| Prayer library (PR #7; amendment 2026-09-26; new app only) | `/settings/prayers` and `GET`/`PUT /church/prayer-library` plus `POST /church/prayer-library/voice-profile-draft`, exactly as PR #7 specifies. |
| Hymn year and familiarity (PR #4's `text_year` and `hymnal_count`; amendment 2026-09-26, owner decision: index §6 question 23) | Admins edit both facts by hand in the hymn dialog: two optional fields, "Year the words were written" and "Number of hymnals (familiarity)" (read-only for members). `HymnIn` and `HymnPatchIn` accept them, and clearing a field sets null. The ops backfill CLI still fills blanks only, so hand-entered values survive it. |

### Out of scope (and where it goes)

| Item | Slice |
|---|---|
| Members, roles, invites, transfer ownership, delete church, leave church (G7–G10); deleting `LegacySettingsNote` | 6b |
| Deleting `email_contacts.get_contacts_for_display` (dead, still covered by `backend/tests/test_email_contacts.py`) | 7 (as 5b schedules it; inv §6 dead-code sweep) |
| Settings layout, `/settings/account`, Gmail connection, `GET /contacts` | 5b (6a consumes them) |
| `GET /hymns`, `GET /hymnals`, the hymn picker, recently-used exclusion, AI suggestions | 3 (6a consumes and slightly extends them) |
| `GET /church` profile fields (`timezone`, `timezone_valid`, `bible_translation`, `effective_translation`, `default_hymnal`, `effective_hymnal`, `default_benediction`) | 2, 3, 4 (6a writes the stored ones through `PATCH /church`) |
| Prompt test-render validator | 4 (6a reuses it) |
| Uploading a custom hymnal CSV | Not scheduled. The owner approved bundled hymnals only (inv §7 Q16). The CLI stays available for ops. |
| Exporting `hymn_catalog` to `backend/seed/` plus a seed CLI; normalizing `{A,"B"}` theme literals | 7 (F §6.4) |
| Free-text hymns in the builder | Stays removed (decision 9) |
| Filling `text_year` and `hymnal_count` in bulk, and editing them in `hymn_catalog` (amendment 2026-09-26) | The ops backfill CLI (`backfill_hymn_facts.py`, inv H14), which stays an ops tool and fills blanks only. Per-hymn editing in the hymn dialog is **in scope** (owner, 2026-09-26; In scope above). A hymn added here with no facts stays unknown until someone enters them or the CLI runs again. |
| Document import or seeding the prayer library from saved services; the service reviewer (amendment 2026-09-26) | Out of scope (PR #7 §Scope). The reviewer is a slice-4 add-on (`2026-09-26-service-reviewer-design.md`). |

### Assumed interfaces from other slices

6a is written against these interfaces. If a slice ships something different, the "If it differs" column says what 6a does.

| From | Interface assumed | If it differs |
|---|---|---|
| 1 | `domain_errors` (`InvalidInput`, `NotFound`, `Conflict`, `Forbidden`), `db.ids.as_uuid`, `usecases/` package, `assert_church_isolated`, `test_route_guards.py`, `test_openapi_contract.py`; frontend `useApi()`, key factory, `renderWithProviders`, `installFakeApi`, UI kit (`PageHeader`, `EmptyState`, `ErrorState`, `ConfirmDialog`, `PendingButton`, `touch` button size). The IANA check `backend/timezones.py::is_valid_timezone(name: str) -> bool` that `POST /churches` uses (exact, case-sensitive membership in `zoneinfo.available_timezones()`), with the message **"Unknown timezone."** | If the check lives inside `usecases/onboarding.py`, 6a moves it to `backend/timezones.py` and both usecases import it. |
| 1 | Frontend time zones: `src/lib/timezones.ts` (`listTimezones(): string[] \| null`, which is null when `Intl.supportedValuesOf` is missing; `browserTimezone()`) and `TimezoneCombobox {value, onChange, error}` in `src/components/app/timezone-combobox.tsx`, which becomes a plain text input when the list is null. Helper text: **"Sets the default service date (the next Sunday in this time zone)."** | 6a reuses both and adds one optional prop (see Frontend changes). If slice 1 shipped no combobox, 6a builds this one to slice 1's spec. |
| 1 | The global `handleAuthErrors` (F §4.4) falls back to another church only on a 403 with `details.reason = "no_church_access"` (what `require_church` raises). A role 403 from `require_admin` carries no `reason` and never falls back. The `(church)` layout switches churches through `onSelectChurch(id)`. | 6a's admin mutations pass `meta: { forbiddenIsRole: true }`: on a 403 **without** `no_church_access`, `handleAuthErrors` toasts the message and invalidates `profile`. A `no_church_access` 403 always takes the church fallback, with or without the meta. If slice 1 falls back on every 403, 6a narrows it to this rule. |
| 2 | `GET /church` → `ChurchProfileOut {id, name, role, timezone, timezone_valid, bible_translation (str or null; stored), effective_translation}`. `GET /translations` → `{default, esv_available, items: [{id, label}]}`. A draft with `readings.translation: null` uses the church default. `scripture_fetcher` keeps the public names `esv_configured()`, `available_translations()`, `fetch_passage()` and `get_passage_text()`, still reading `ESV_API_KEY` from the environment (slice 2's recorded deviation, which 6a closes). | — |
| 3 | `GET /hymns?hymnal=&q=&limit=&offset=` → `Page[HymnOut]` (`{items, total, limit, offset}`). `HymnOut` includes at least `id, hymnal, title, number, scripture_refs, themes: list[str], link` (no raw `theme` string; the edit dialog starts Themes at `themes.join(", ")` and sends it only when changed). Order is `hymnal, number NULLS LAST, lower(title), id`. `q` is trimmed (empty = no filter): **1 to 6 digits** → `number = int(q)` OR title substring; anything else, including longer digit strings, → case-insensitive substring on `title` (`.contains(…, autoescape=True)`). | If `q` is missing, 6a adds it (additive) with exactly that rule. |
| 3 | `GET /hymnals` → `HymnalListOut {items: [{code, hymn_count, scripture_ref_count}], default_hymnal, effective_hymnal}`. `GET /church` returns the same `default_hymnal` (the stored value: a non-empty string, or null) and `effective_hymnal`; both come from `usecases.hymns.resolve_default_hymnal`, so they never disagree. **Effective default rule:** the stored `default_hymnal` if the church has at least one hymn in it; else the alphabetically first hymnal; else null. `repos.hymns.hymnal_summaries(church_id, *, session=None)` gives the per-hymnal counts. | 6a adds the optional field `label` to each hymnal item (additive). If slice 3 ships other field names, 6a's client maps them; the rules above are what 6a relies on. |
| 3 | Builder: a draft with `hymns.hymnal: null` shows the effective default. A draft whose `hymns.hymnal` is no longer one of the church's hymnals falls back to the effective default. Slot picks resolve by `hymn_id` whatever the hymnal filter. A pick whose `hymn_id` no longer exists shows "Not in your hymnal. Choose a replacement." `repos.hymns.get_hymn(hymn_id, church_id)` exists. | If `get_hymn` is missing, 6a adds it. |
| 4 | `GET /church.default_benediction: str` is the stored value **when the key is present, even if it is `""`**, else `"Halverson"`. A draft's benediction card with `origin: "default"` shows the current profile value, with the hint "Your church's default benediction. Admins can change it in Settings." (`SectionCard.tsx`). `POST /liturgy/generate` reads the church's prompts from the database on every request. The validator is `liturgy_prompts.template_error(template: str) -> str or None`, which returns a short user-facing reason or None and never raises; its reasons are slice 4's pinned strings (for example "It has a { or } without a partner. Use {{ or }} to print a brace."). Prompt cleaning is `liturgy_prompts.clean_prompt_overrides(prompts, defaults=None) -> dict`, whose only implementation is in `liturgy_prompts` (slice 4): it normalizes `\r\n` → `\n`, trims, and keeps only `PROMPT_KEYS` whose value is non-blank and differs from the trimmed default. | If slice 4 wrote `settings.get("default_benediction") or "Halverson"`, 6a changes it to a key-presence check, with a test. If the validator has another shape, 6a wraps it; the 422 contract below is fixed. If `clean_prompt_overrides` lacks the `\r\n` normalization, 6a adds it there (with slice 4's test), never in a second copy. |
| 5b | `src/app/(signed-in)/(church)/settings/layout.tsx` renders the "Settings" header, the caption "{church name} — you’re {a member \| an admin \| the owner}.", the section nav (`settings-nav.tsx`) from `SETTINGS_SECTIONS` in `src/components/settings/sections.ts`, and `LegacySettingsNote` (`legacy-settings-note.tsx`). `/settings` redirects to `SETTINGS_SECTIONS[0].href`. `GET /contacts` → `{items: [ContactOut {id, name (str or null), email}]}`, served from `routes/contacts.py`, ordered by `list_contacts` (creation time, name NULLs last, id). There is a `useContacts()` hook. `backend/email_addresses.py::normalize_address(raw) -> str` (raises `InvalidAddress`; ASCII-only labels; returns the trimmed address with its case kept), which `POST /bulletin-emails` re-applies to every selected contact; a saved contact that fails it gets the 422 "The saved contact “{name, or the address}” has an invalid email address. " followed by `MALFORMED_CONTACT_HINT` (a module constant in `backend/usecases/email.py`). `EmailBulletinDialog`'s empty contacts state is "No saved contacts yet — type addresses below." | If `/settings` is hard-wired to `/settings/account`, 6a points it at `/settings/church` (F §4.1). If `normalize_address` is missing, 6a adds it exactly as 5b specifies, never a second rule. |
| 6b | May land first and create `usecases/church_admin.py`, `repos.churches.lock_church(session, church_id) -> Church \| None` (`SELECT … FOR UPDATE` on a non-deleted church) and `lock_and_read_actor(s, church_id, actor_id) -> str` (in `usecases/members.py`). `lock_and_read_actor` calls `lock_church` (None → the `no_church_access` 403 below), then re-reads the actor's membership **under that lock**: membership gone → the same `no_church_access` 403; otherwise it returns the actor's current role. 6a adds functions to `church_admin.py` and starts **every write below** with `lock_and_read_actor`, so 6a and 6b give the same guarantee. No route is shared. Neither slice adds `email-validator`: 6b validates invite emails with the same `email_addresses.normalize_address` (5b). | If 6a lands first, it creates `lock_church` and `lock_and_read_actor` with those signatures and semantics, at the path 6b names. There is one helper, never two: if it ends up in `church_admin.py` instead, both slices import it from there. |
| PR #4 (on `main`; amendment 2026-09-26) | `backend/api/routes/rubric.py` (`GET /rubric` with `require_church`, `PATCH /rubric` with `require_admin`), `RubricOut`/`RubricModel` in `api/schemas.py`, and `service_rubric` (`DEFAULT_RUBRIC`, `default_rubric`, `validate_patch`, `apply_patch`, `merge_rubric`, `customized_keys`, `HYMN_SLOTS`, `HYMN_SLOT_LABELS`, `MAX_ITEMS = 12`, `MAX_ITEM_CHARS = 300`, `MIN_YEAR = 1500`). `repos.churches._lock_live_church(session, church_id)` already does `SELECT … FOR UPDATE` on a non-deleted church; `_merge_settings` and `update_church_rubric` use it. | `_lock_live_church` **becomes** `lock_church` (renamed, same semantics), so there is one lock helper, not two. `_merge_settings` becomes `merge_settings` (Changed modules). |
| 4 (amendment 2026-09-26) | The pure `backend/prayer_library.py` (`read_library`, `PRAYER_TYPES`, the limits) that slice 4's writer hook reads. `usecases/liturgy` reads `prayer_library` and `rubric` fresh on every generation. | If 4 did not ship it, 6a adds it with the slice 4 shape, and 4's reader imports it. |
| 3 (amendment 2026-09-26) | `HymnOut.newer_than_preferred` depends on the rubric's `prefer_before_year`. | The rubric mutation invalidates `["church", id, "hymns"]` (Queries). |

---

## User experience

All four pages render inside 5b's settings layout. On mobile (375 px) they are a single column with 16 px gutters. From `md` up the content column is `max-w-3xl` beside the settings nav. Primary buttons use `size="touch"`. Inputs use `text-base md:text-sm`.

**Every page:**
- The first load shows `Skeleton` rows shaped like the content.
- A failed query shows `ErrorState` with **Retry**.
- A mutation shows `PendingButton` ("Saving…", "Adding…", "Deleting…", "Removing…").
- The server message appears as a toast, and 422 `fields` appear inline (F §4.8).
- Forms keep a *baseline* (the form values built from the last server value) and the *current* edits. A save sends only the fields where current differs from baseline.
  - A background refetch (for example `refetchOnWindowFocus`, F §4.4) **rebases** the form: each field the user hasn't touched (current equals the old baseline) takes the new server value; each field the user edited keeps the edit. Then the baseline becomes the new server value. So an untouched field is never sent, and another admin's concurrent change to it is not reverted (`rebaseForm`, used by both forms; Frontend changes).
  - A successful save resets the baseline and the form to the response.
  - The church-switch remount (F §4.2) discards everything, after the leave guard below.
- **Leave guard** for the profile and prompts forms while they have unsaved edits (`useLeaveGuard(dirty)`, Frontend changes):
  - Closing or reloading the tab: the browser's `beforeunload` warning.
  - In-app navigation (settings section nav, header links, the switcher's "Join or create a church…") and switching church: a `ConfirmDialog` titled **"Discard unsaved changes?"**, body "Your changes on this page haven't been saved.", confirm **"Discard changes"**, cancel "Keep editing". Confirming continues the navigation or switch; cancelling stays with the edits intact.
  - Not covered: the browser Back/Forward buttons and Log out. That loss is accepted.

### Settings nav (6a entries)

6a **prepends** to `SETTINGS_SECTIONS` (`src/components/settings/sections.ts`), in this order: **Church** (`/settings/church`), **Hymns** (`/settings/hymns`), **Liturgy** (`/settings/liturgy`), **Contacts** (`/settings/contacts`). After 6a the list is Church, Hymns, Liturgy, Contacts, Account (5b). 6b then adds People and Danger zone; 6a doesn't depend on where. Because 5b's `/settings` redirects to `SETTINGS_SECTIONS[0].href`, `/settings` now lands on `/settings/church`.

*Amendment 2026-09-26:* 6a also inserts **Prayers** (`/settings/prayers`, PR #7) right after **Liturgy**, then **Rubric** (`/settings/rubric`, PR #4) right after Prayers. Both are visible to every role (members read). After 6a the list is **Church, Hymns, Liturgy, Prayers, Rubric, Contacts, Account**. After 6b it is **Church, Hymns, Liturgy, Prayers, Rubric, Contacts, People, Account, Danger zone**. This supersedes the final order written in the 5b and 6b specs, and 6b's `SETTINGS_SECTIONS` DOM assertion (6b acceptance 22) uses this list.

**Legacy note (5b):** 6a changes the `LegacySettingsNote` text to **"People and invites are still managed in the current app for now."** The words "the current app" keep 5b's optional link. Without this change, the note would send the tester back to Streamlit for the pages 6a just moved, where settings writes don't take the row lock. 6b deletes the note.

**Email dialog (5b):** in `EmailBulletinDialog`'s empty contacts state ("No saved contacts yet — type addresses below."), 6a adds a **Manage contacts** link to `/settings/contacts`, shown only to owners and admins. The draft survives the navigation (F §4.6).

### 1. Church profile: `/settings/church`

`PageHeader` "Church profile". For members, an info banner shows first: **"Only admins can edit the church profile."** The fields are then disabled (read-only), and Save is hidden.

| Field | Control | Help text / states |
|---|---|---|
| Church name | Input, required | 422 inline: "Church name is required." |
| Time zone | Slice 1's `TimezoneCombobox` (Base UI Combobox; at most 50 filtered matches; "Type to search"; a plain text input when the browser has no zone list) | Help (slice 1's string): "Sets the default service date (the next Sunday in this time zone)." Below the field, a text button: "Use this device's time zone ({browserTimezone()})". If the stored value isn't recognized (`timezone_valid: false`), the field shows it with the warning **"Timezone not recognized. Choose one from the list."** 422 inline: "Timezone is required." / "Unknown timezone." |
| Default Bible translation | Select (`items` from `GET /translations`) | Help: "Used for passage text in the builder. Anyone can switch it for a single service." A stored value that isn't available on this server (for example `esv` without a key) appears as an extra item "{ID} (not available on this server)" and stays selected. It is never silently replaced. |
| Default hymnal | Select (`items` from `GET /hymnals`) | Help: "The hymnal the builder opens with. You can switch hymnals for a single service." A stored value the church no longer has (its hymns were deleted one by one) appears as an extra item **"{code} (no longer in your hymnals)"** and stays selected, like the translation case; the builder already uses `effective_hymnal`. With exactly one item it renders as text: "{code} (your only hymnal)". With **no hymnals** the field is hidden and replaced by the line "Add a hymnal in Hymns to choose a default." (a link to `/settings/hymns`). |
| Default benediction | Textarea (4 rows, auto-grow, 4000 characters max) | Help: "Pre-fills the Benediction card in each new service. Leave it blank to let the AI write the benediction." When the trimmed value is exactly `Halverson`, a note appears: **"The bulletin will print the word “Halverson”. Paste the full benediction text if you want it printed."** |

**Initial values** (`profileFormFrom(profile)`; the baseline is built the same way, so an untouched control never produces a patch key):

| Field | Starts at |
|---|---|
| name, timezone | the stored value, as returned (an unrecognized timezone included) |
| translation | `bible_translation` when non-null (the stored value, even if unavailable), else `effective_translation` |
| default hymnal | `default_hymnal` when non-null (the stored value, even if stale), else `effective_hymnal`, else `""` (no hymnals: field hidden) |
| benediction | `default_benediction` |

A null stored translation or hymnal therefore shows the effective value but is not written by a name-only save; the church keeps following the fallback rule. The value is stored only when the admin picks a **different** item.

**Save profile:**
- Primary button, `PendingButton`, disabled until something changes.
- It sends `PATCH /church` with **only the changed fields** (`diffProfile(baseline, current)`).
- Success toast: **"Profile saved."**
- On a 422, the message appears under the named field, and that field gets focus.

**Time zone options** come from slice 1's `listTimezones()`, with its single fallback: no zone list → a plain text input validated by the server. 6a adds one optional prop to `TimezoneCombobox`, `warning?: string`. When `value` is non-empty and not in the list, the combobox adds `value` as an extra item so Base UI can show it selected (F §4.9.3), and renders `warning` below the field when given. The profile passes the warning only when `timezone_valid` is false.

### 2. Hymns: `/settings/hymns`

Two stacked sections.

**2a. Hymnals card**
- Title "Hymnals".
- One row per church hymnal: code, label (if known), "{hymn_count} hymns", and a **Default** badge on the effective default.
- Footer line: "{total} hymns in {n} hymnals."
- **Admins:**
  - **Add a hymnal** button.
  - A **Remove…** action on every row except the effective default.
  - On the default row, a hint in place of Remove: "Default. Change it in Church profile." (links to `/settings/church`).
- **Members** see no actions. They see the line "Admins can add bundled hymnals."

**Add a hymnal** (Dialog; full screen below `sm`):
- Lists `GET /hymnal-sources`. Each source row: "{code} · {label} · {hymn_count} hymns".
- If `has_scripture_refs` is false, the row adds the note **"This hymnal has no scripture references, so “Find hymns” and AI suggestions work less well with it."**
- Sources the church already has show **Added** (disabled). The others have an **Add** button.
- On success the dialog stays open, the row turns to **Added**, and a toast says **"Added {code} ({inserted} hymns)."**
- The client timeout is 30 s (F §1.8). While the request runs, the button reads "Adding…", and after 8 s the dialog shows "Still working — this can take up to a minute."
- Empty list: "No bundled hymnals are available on this server."

**Remove a hymnal** (`ConfirmDialog`; the confirm button reads **"Remove {code}"**):
- Title: "Remove {code}?"
- Body: "This deletes all {hymn_count} hymns in {code} from your church's hymnal, including hymns your church added to it. Saved services keep their hymns. Services in progress will ask you to choose replacements."
- A second sentence depends on the source:
  - for a bundled code: "You can add {code} again later, but edits you made to its hymns will be lost."
  - otherwise: "It can't be added back from the bundled list."
- Success toast: "Removed {code}."

**2b. Hymn library**
- Title "Hymn library". Caption: **"Anyone in your church can add and edit hymns."**
- Controls, top to bottom on mobile:
  - **Add hymn** (primary, `touch`).
  - A search input "Search by title or number". It is debounced 300 ms, has a clear button, and resets paging.
  - Hymnal filter chips "All · GG2013 · PH1990", shown only with more than one hymnal. They are toggle buttons with `aria-pressed`, not a Select, so no sentinel item is needed (F §4.9.3).
- Count line: "{total} hymns", or with a search or filter "{total} matching hymns".
- **Rows:**
  - "#{number} {title}", with "—" in place of a missing number. With several hymnals, a hymnal badge.
  - The whole row is a button that opens **Edit hymn**.
  - Rows come in pages of 50 in slice 3's server order (hymnal, then number with NULLs last, then title). A **Show more** button loads the next page. NULL-number hymns are therefore reachable at the end of their hymnal, and through search.
  - Search follows slice 3's `q` rule: 1 to 6 digits also match the hymn number (so "23" finds #23 and titles containing "23"); anything else matches titles only.

**Add hymn / Edit hymn** (Dialog; full screen below `sm`):

| Field | Notes |
|---|---|
| Title | Required. "Hymn title is required." |
| Number | Text input with `inputMode="numeric"`. Empty = no number. The client rejects anything that isn't a whole number from 1 to 99999 with "Hymn number must be a whole number."; the server returns the same message for an out-of-range number. |
| Hymnal | Select of the church's hymnals, defaulting to the effective default. Hidden with only one hymnal. |
| Scripture references | Placeholder "e.g. Psalm 23; John 10:11-18". Help: "Used by “Find hymns” and AI suggestions." |
| Themes | Placeholder "e.g. Advent, hope" |
| Link | Placeholder "https://hymnary.org/…". "Links must start with https://." |
| Year the words were written (*amendment 2026-09-26*) | Optional; admins only (members see it read-only, and their saves never send it). Text input with `inputMode="numeric"`. Empty = unknown (null). The client rejects anything that isn't a whole number from 1 to the current year with "Year must be a whole number from 1 to {current year}."; the server returns the same message. |
| Number of hymnals (familiarity) (*amendment 2026-09-26*) | Optional; admins only, as for the year. Text input with `inputMode="numeric"`. Empty = unknown (null). The client rejects anything that isn't a whole number from 0 to 100000 with "Number of hymnals must be a whole number from 0 to 100000."; the server returns the same message. |

- Add submits **Add hymn**. On success the dialog closes and a toast says **"Hymn added."** (the new row may be on another page).
- Edit submits **Save changes** and sends only the changed fields. Toast: **"Hymn updated."** In edit mode a muted note sits above the buttons: **"Changes also appear in saved services that use this hymn."** (5a resolves an archived hymn by `hymn_id` to the row's current title, number and hymnal, so its regenerated documents print the edit.)
- Edit also shows a destructive **Delete hymn** button, which opens a `ConfirmDialog`:
  - Title: "Delete “{title}”?"
  - Body: "Saved services keep this hymn. Services in progress that use it will ask you to choose a replacement."
  - Confirm: **"Delete hymn"**. Toast: **"Hymn deleted."**
- 409 conflict: the dialog stays open and shows the server message above the buttons ("{hymnal} already has #{number} {title}.").
- 404 (someone else deleted it): toast "This hymn was already deleted.", then close the dialog and refetch.

**Empty states:**
- The church has no hymns: `EmptyState` "No hymns yet". Text: "Add hymns one at a time, or ask an admin to add a bundled hymnal." Action: **Add hymn**. For admins the text is "Add hymns one at a time, or add a bundled hymnal above."
- No search results: "No hymns match “{q}”." with **Clear search**.

### 3. Liturgy prompts: `/settings/liturgy`

- `PageHeader` "Liturgy prompts".
- Intro: "These are the instructions the AI follows when it writes your liturgy. Edit any of them to shape the voice; leave a box on its default to use the shared wording."
- Members see the banner **"Only admins can edit the prompts. You can read them below."** Their textareas are read-only and the footer is hidden.

**Nine prompt cards** in server order:
- "Overall voice (system prompt)" first. Under its textarea: **"Placeholders aren't filled in here; this text is sent as written."** (It is sent to the model verbatim, worship_service.py:731, 756.)
- Then a small heading **"Section prompts"**, followed by the server's `placeholder_help` and the sentence "Use {{ or }} to print a brace." (slice 4's wording). This help applies only to the cards below it, never to the system prompt.
- Then Call to Worship, Opening Prayer, Prayer of Confession, Assurance of Pardon, Prayer for Illumination, Prayers of the People, Offertory Prayer, Benediction.
- Each card is a collapsible section (Base UI Collapsible):
  - The header shows the label and a **Customized** badge when the *current text* differs from the default.
  - The body is an auto-grow textarea: minimum 8 rows for the system prompt and Prayers of the People, 4 rows otherwise; 8000 characters maximum.
  - Below the textarea is a **Reset to default** text button, enabled only when the text differs from the default. It puts the default text back into the textarea (unsaved).
- On mobile all cards start collapsed except those with an error. On desktop all start expanded.

**Sticky footer (admins):**
- **Save prompts** (primary; disabled until something changes). It sends `PUT /church/liturgy-prompts` with every card whose trimmed text differs from the default. Toast: **"Prompts saved."**
- **Reset all to defaults** (secondary). It opens a `ConfirmDialog`:
  - Title: "Reset all prompts?"
  - Body: "Your church's custom wording will be removed and the shared defaults used."
  - Confirm: **"Reset all"**. It sends `PUT` with `{"prompts": {}}`. Toast: **"Prompts reset to defaults."**
- The footer is `sticky bottom-0` with `pb-[env(safe-area-inset-bottom)]`.
- The form re-initializes from the server response after a save or reset, so there is no stale text (fixes inv §1 G6).

**Errors:** a 422 `prompt_invalid` expands the named card, shows the message under its textarea (for example **"Benediction prompt: It has a { or } without a partner. Use {{ or }} to print a brace."**, slice 4's `template_error` reason after the label prefix) and focuses it. Nothing is saved.

### 4. Contacts: `/settings/contacts`

- `PageHeader` "Contacts". Caption: "People you can email the bulletin to from the Review step."
- Members see the banner **"Only admins can add or change contacts."**
- **List** (every member): the name in bold with the email below; the email alone when there is no name (`name: null`). Order: 5b's `list_contacts` order (creation time, then name, then id; parity).
- **Admin row actions** (icon buttons, 44 px targets):
  - **Edit** opens a Dialog with Name and Email and **Save changes**.
  - **Delete** opens a `ConfirmDialog`: "Delete {name or email}?" / "They won't be offered as a bulletin recipient anymore." / confirm **"Delete contact"**.
- **Admin add form** below the list: "Name (optional)", "Email", and **Add contact**.
  - On success the fields clear and focus returns to Name. There is no toast; the new row appears (F §4.8).
  - Errors appear inline: **"Email is required."**, **"Enter a valid email address."**, **"That email is already in your contacts."**
- **Empty state:**
  - admin: "No contacts yet" / "Add the people who receive the bulletin, like your church secretary."
  - member: "No contacts yet" / "Ask an admin to add bulletin recipients."

### 5. Prayers: `/settings/prayers` (amendment 2026-09-26, PR #7; new app only)

The page is specified in `docs/superpowers/specs/2026-09-26-prayer-library-design.md` §"Prayers page (slice 6a)". Its copy, states and rules are used verbatim and not repeated here. In summary:
- a voice-profile card with **"Update from my prayers"**. It is disabled with "Save your prayers first." while the list has unsaved changes. The draft appears beside the current profile, stacked at 375 px, with **"Use this draft"** and **"Keep mine"**. While it waits: a spinner, "Still working" after 8 s, and Cancel;
- the prayers list: a type select (the 8 section labels plus "Other"), the prayer's first line, Edit, and Remove with a `ConfirmDialog`. **Add a prayer** appends an open row;
- one sticky **Save** that sends the prayers and the profile together (`PUT`);
- the empty state "No prayers yet. Paste in a few of your own prayers so the writer can learn your voice.";
- for members, the banner "Only admins can edit the prayer library. You can read it below." and a read-only page.

This page follows this slice's "Every page" rules: skeleton, ErrorState with Retry, PendingButton, toasts, inline 422 `fields` (keyed `prayers.<i>.text`, `prayers.<i>.type`, `voice_profile`), and the baseline/rebase rule. The leave guard (`useLeaveGuard(dirty)`) protects unsaved prayers and profile edits. All pastor text is rendered as React text.

### 6. Service rubric: `/settings/rubric` (amendment 2026-09-26, PR #4)

`PageHeader` **"Service rubric"**. Intro: **"What makes a good hymn or prayer at your church. The AI follows these checklists when it suggests hymns and writes liturgy. How each prayer is laid out (Leader and People lines, length, “Amen”) stays in Liturgy prompts."** Members see the banner **"Only admins can edit the rubric. You can read it below."**. Their fields are read-only, and the footer and every add, remove and reset control are hidden.

**Hymn preferences card:**
- **"Prefer hymns written before"**: a year input (`inputMode="numeric"`, 4 digits). Help: **"Hymns with older words are suggested first. This is a preference, not a filter: a newer hymn can still be suggested when it fits clearly better, and the builder shows its year."**
- **"Prefer familiar hymns"**: a `Switch`. Help: **"Hymns found in many hymnals are suggested first."**
- A **Customized** badge and a **Reset to default** text button on each setting that differs from its default.

**Checklist cards**, in two groups. Each card is a collapsible section: all collapsed on mobile except a card with an error, all expanded on desktop.
- The **"Hymns"** group has three cards titled with `HYMN_SLOT_LABELS`: "Opening (Gathering) Hymn", "Response Hymn (after the sermon)", "Closing (Sending) Hymn".
- The **"Prayers"** group has eight cards titled with `SECTION_LABELS`, in `SECTION_ORDER`.
- Each card shows "A good {Label}:" and its points in order. Each point is an auto-growing text box with `maxLength` 300. Line breaks are not allowed there: Enter adds a new point below, and a pasted line break becomes a space, matching the server's whitespace rule.
- Each point has a remove ✕ (aria-label "Remove point {n} from {Label}").
- **Add a point** is disabled at 12, with the helper "A checklist can have at most 12 points."
- A **Customized** badge shows when the card's cleaned points differ from the default. **Reset to default** puts the default points back into the card; the change is unsaved until Save.
- Under the Opening and Closing cards: **"The builder first gathers opening and closing hymns by theme (gathering, praise, sending and similar). This checklist then guides which of them the AI suggests."** This is the known limit in the rubric spec and slice 3 §3.8; see Open question 3.

**Sticky footer (admins):**
- **Save rubric** (primary; disabled until something changes). It sends **one** sparse `PATCH /rubric` with only the changed items. Each point is trimmed, whitespace runs are collapsed and blank points are dropped. An item whose cleaned value **equals its default is sent as `null`**, so the church keeps following future improvements to the defaults (the rubric spec's intent). Toast: **"Rubric saved."**
- **Reset all to defaults** (secondary; shown when `customized` is non-empty). It opens a `ConfirmDialog`: title "Reset the rubric?", body "Your church's checklists and preferences go back to the shared defaults.", confirm **"Reset all"**. It sends `null` for every customized key. Toast: **"Rubric reset to defaults."**
- The footer is `sticky bottom-0` with the safe-area inset, as on the prompts page.

**Validation copy.** The client checks run first, and their messages equal the server's `service_rubric` messages (inv §1 G11), so there is one wording:
- A card whose points are all blank or removed: **"Keep at least one point, or use Reset to default."**, shown inline on the card; Save is disabled. The server's "A checklist must be a non-empty list of points." is the backstop.
- The year: **"The preferred year must be between 1500 and {current year}."**, shown inline under the field.
- Points over 300 characters and more than 12 points can't be entered.
- A 422 `invalid_rubric` from the server, for example a control character pasted in, shows the server message in an inline `Alert` above the footer. The PATCH is validated as a whole, so nothing was saved, and the edits stay.

The form follows "Every page": the baseline and rebase-on-refetch rule (`rebaseForm` over one value per preference and per checklist), the leave guard while dirty, and re-initialization from the PATCH response.

### Losing a role mid-session

If an admin is demoted in another tab or by another admin (6b), their next admin mutation gets 403 "Only church admins can do this.". This holds even when the demotion lands between the route guard and the write, because every write re-reads the role under the church-row lock (Semantics → Locking). The app toasts that message and invalidates `profile`. `role` then updates, and the page switches to its read-only form without leaving the church. An admin or member **removed** from the church gets the `no_church_access` 403 instead, and the client takes slice 1's church fallback.

---

## API

Conventions: F §1. Every route below is church-scoped (`X-Church-Id` plus `require_church`, directly or through `require_admin`). Request models use `extra="forbid"`.

Notation:
- `field?` means the field may be omitted.
- `T?` means the value may be `null`.
- `str(n)` means a string of at most n characters.

Pydantic length errors → 422 `invalid_request` "Too long (max N characters)." (F §1.5).

| Method | Path | Guard | Request | Response | Errors |
|---|---|---|---|---|---|
| PATCH | `/church` | admin | `ChurchPatchIn` (below) | 200 `ChurchProfileOut` (the GET /church model) | 403 `forbidden` "Only church admins can do this."; 422 `invalid_request` with `fields`: `name` "Church name is required.", `timezone` "Timezone is required." or "Unknown timezone.", `bible_translation` "Unknown or unavailable translation.", `default_hymnal` "Choose one of your church's hymnals." |
| GET | `/church/liturgy-prompts` | church | – | 200 `LiturgyPromptsOut` | 403 |
| PUT | `/church/liturgy-prompts` | admin | `{prompts: {PromptKey: str(8000)}}`, keys limited to `system` + the 8 section keys | 200 `LiturgyPromptsOut` | 403; 422 `prompt_invalid`, `fields["prompts.<key>"]`, message "<Label> prompt: <reason>"; 422 `invalid_request` (unknown key → "Not a valid value.") |
| POST | `/contacts` | admin | `ContactIn` (below) | 201 `ContactOut` | 403; 422 `email` "Email is required." (omitted, `""` or blank) / "Enter a valid email address."; 409 `conflict` "That email is already in your contacts." |
| PATCH | `/contacts/{contact_id}` | admin | `ContactPatchIn` (below) | 200 `ContactOut` | 403; 404 `not_found` "Contact not found."; 422 and 409 as for POST |
| DELETE | `/contacts/{contact_id}` | admin | – | 200 `{deleted: true}` | 403; 404 "Contact not found." |
| POST | `/hymns` | church | `HymnIn` (below) | 201 `HymnDetailOut` | 403 (*amendment 2026-09-26:* also the role 403 "Only church admins can do this." when a member sets `text_year` or `hymnal_count`); 422 `title` "Hymn title is required." (omitted or blank), `number` "Hymn number must be a whole number." (outside 1–99999; a non-integer JSON value is Pydantic's generic "Not a valid value."), `hymnal` "Choose one of your church's hymnals.", `link` "Links must start with https://.", *amendment 2026-09-26:* `text_year` "Year must be a whole number from 1 to {current year}." (outside 1 to the current year), `hymnal_count` "Number of hymnals must be a whole number from 0 to 100000." (outside 0–100000; a non-integer JSON value for either is Pydantic's generic "Not a valid value."); 409 `conflict` "{hymnal} already has #{number} {title}." (no number: "{hymnal} already has {title}.") |
| PATCH | `/hymns/{hymn_id}` | church | `HymnPatchIn` (below) | 200 `HymnDetailOut` | 403 (including the role 403 for the facts, as for POST); 404 "Hymn not found."; 422 and 409 as for POST |
| DELETE | `/hymns/{hymn_id}` | church | – | 200 `{deleted: true}` | 403; 404 "Hymn not found." |
| GET | `/hymnals` (3) | church | – | 6a adds `label: str?` to each item (additive) | – |
| GET | `/hymnal-sources` | admin | – | 200 `{items: [HymnalSourceOut]}` | 403 |
| POST | `/hymnals` | admin | `{code: str(20)}` | 200 `{code, label?, inserted, updated}` | 403; 422 `code` "That hymnal isn't available to add." |
| DELETE | `/hymnals/{code}` | admin | path `code` matches `^[A-Za-z0-9_-]{2,20}$` (else 422) | 200 `{deleted: true, hymns_deleted: n}` | 403; 404 "Your church doesn't have that hymnal."; 409 `conflict` "You can't remove your only hymnal." / "{code} is your default hymnal. Choose a different default in Church profile first." |
| GET | `/rubric` (**exists**, PR #4; amendment 2026-09-26) | church | – | 200 `RubricOut {rubric, customized}`, plus the additive `defaults: RubricModel` (the full default rubric), so the editor can show "Reset to default" and send `null` for values equal to the default | 403 |
| PATCH | `/rubric` (**exists**, PR #4; amendment 2026-09-26) | admin | sparse plain JSON object, validated by `service_rubric.validate_patch` (unchanged; declared exception to the `extra="forbid"` model rule, F §1.3) | 200 `RubricOut` (with `defaults`) | 403 "Only church admins can do this."; 422 `invalid_rubric` with the `service_rubric` message and no `fields` (unchanged from PR #4; F §1.5 registry as amended); 422 `invalid_request` for a non-object body |
| GET | `/church/prayer-library` (amendment 2026-09-26, PR #7) | church | – | 200 `{prayers: [PrayerOut], voice_profile, can_edit}` | 403 |
| PUT | `/church/prayer-library` (PR #7) | admin | `{prayers: [{id?, type, text}], voice_profile}` (full replace) | 200, same shape as GET | 403; 422 `invalid_request` with `fields` `prayers.<i>.text` / `prayers.<i>.type` / `voice_profile` and PR #7's five messages |
| POST | `/church/prayer-library/voice-profile-draft` (PR #7) | admin + `rate_limit("ai")` (cost 1) | – | 200 `{draft: str}` (not stored) | 403; 422 `invalid_request` "Add at least one prayer and save it first."; 429 `rate_limited`; 503 `ai_not_configured` / `ai_busy`; 504 `ai_timeout`; 502 `ai_upstream_error`. Never 422 for length: a long library is cut to fit (notes below). |

*Amendment 2026-09-26 notes on the new rows.*
- **`/rubric` keeps its path.** It predates F §1.1's "church sub-resources sit under `/church`" rule and already ships on `main`. It is recorded as the one exception in F §1.1 and is not renamed, because a rename would break any client of PR #4's API for no gain. `PATCH /rubric` is admin-guarded through `require_admin`, so the route-guard test needs no allowlist change.
- **`PATCH /rubric` now takes the locking rule.** It starts with `lock_and_read_actor` and then `require_admin_role`, like every other write in this slice (Semantics → Locking), so a demoted admin gets the role 403 and a removed member gets `no_church_access`.
- **Prayer-library routes:** everything in PR #7 §API applies (module `backend/api/routes/prayer_library.py` calling `backend/usecases/prayer_library.py`; models at the top with `extra="forbid"`; `PUT` semantics; the draft's 75 s deadline, `max_completion_tokens=800` and 2 000-character cap). `PUT` starts with `lock_and_read_actor` and `require_admin_role` and writes through `merge_settings`, never replacing `settings`. The draft route reads the saved prayers in one session, closes it, and then calls `openai_client.complete(…, deadline=…)`; it takes no lock, because it writes nothing. **Draft input budget (PR #7 §Draft semantics, added 2026-09-26):** the draft never returns 422 for length. Every saved prayer is sent, in saved order, with its type label. If the prompt would exceed slice 4's `liturgy_prompts.MAX_PROMPT_CHARS` (24 000, F §2.8), each prayer longer than an equal share of the space left after the fixed instructions and the type labels is cut to that share, at the last sentence end (`.`, `!` or `?`) within its share when there is one, and otherwise at the share itself. The `ai` bucket is charged by the dependency, as on `/hymns/suggestions`, so a 422 for an empty library also costs one token (F §1.8).
- **Client timeouts** (F §1.8): the draft is 90 000 ms (75 s server deadline, like `/hymns/suggestions`); every other new route uses the 20 s default.

**Church, membership or role gone mid-request.** Every write in this slice starts with `lock_and_read_actor` (6b's helper; Semantics → Locking), which takes the church-row lock and re-reads the caller's membership under it.
- If the church was soft-deleted after `require_church` ran (the lock returns None), or the caller's membership is gone (removed, or left in another tab), the usecase raises `Forbidden("You don't have access to this church.", details={"reason": "no_church_access"})` → 403, the same body `require_church` returns. The client then takes slice 1's church fallback. (Streamlit raised "Church not found.", inv §1 G2.)
- On an **admin** route, if the re-read role is no longer owner or admin (demoted after the guard ran), the usecase raises `Forbidden("Only church admins can do this.")` with no `reason` → the role 403, the same body `require_admin` returns. `require_admin`'s earlier snapshot is never trusted for the write.

This applies to `PATCH /church`, `PUT /church/liturgy-prompts`, the contact and hymn writes, and `POST`/`DELETE /hymnals`. The hymn writes are open to members, so they apply only the membership check.

No route in this slice is user-scoped, so the `test_route_guards.py` allowlists don't change. None takes `Idempotency-Key`: adding a hymnal is idempotent by design, and hymn and contact creation run their duplicate check under the church-row lock, so a double tap or a retry after a lost response gets 409 rather than a second row. Client timeouts are the 20 s default, except `POST /hymnals` at 30 s (F §1.8).

### Models

```python
class ChurchPatchIn(BaseModel):            # all optional; omitted or null = unchanged
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, max_length=200)
    timezone: str | None = Field(None, max_length=64)
    bible_translation: str | None = Field(None, max_length=20)
    default_hymnal: str | None = Field(None, max_length=20)
    default_benediction: str | None = Field(None, max_length=4000)   # "" = no default benediction

PromptKey = Literal["system", "call_to_worship", "opening_prayer", "prayer_of_confession",
                    "assurance", "prayer_for_illumination", "prayers_of_the_people",
                    "offertory_prayer", "benediction"]

class LiturgyPromptsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompts: dict[PromptKey, Annotated[str, Field(max_length=8000)]]

class PromptFieldOut(BaseModel):
    key: PromptKey; label: str; default: str
    override: str | None                  # stored override, or null
    customized: bool                      # override is not None

class LiturgyPromptsOut(BaseModel):
    placeholder_help: str                 # liturgy_prompts.PLACEHOLDER_HELP
    can_edit: bool                        # caller is owner or admin
    fields: list[PromptFieldOut]          # "system" first, then SECTION_ORDER

class ContactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, max_length=200)
    email: str = Field("", max_length=320)    # "" default: the usecase says "Email is required." (F §1.3)

class ContactPatchIn(BaseModel):          # omitted = unchanged (model_fields_set)
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, max_length=200)    # null or blank clears the name
    email: str | None = Field(None, max_length=320)   # null or blank -> "Email is required."

class HymnIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field("", max_length=300)    # "" default: the usecase says "Hymn title is required."
    number: int | None = None                 # range 1-99999 checked in the usecase (friendly message)
    hymnal: str | None = Field(None, max_length=20)   # null/omitted = effective default hymnal
    scripture_refs: str | None = Field(None, max_length=2000)
    theme: str | None = Field(None, max_length=2000)
    link: str | None = Field(None, max_length=500)
    # Amendment 2026-09-26 (index §6 question 23): optional hymn facts; null/omitted = unknown.
    text_year: int | None = None              # range 1..current year checked in the usecase
    hymnal_count: int | None = None           # range 0..100000 checked in the usecase

class HymnPatchIn(BaseModel):              # omitted = unchanged (model_fields_set)
    model_config = ConfigDict(extra="forbid")
    title: str | None = Field(None, max_length=300)      # null or blank -> "Hymn title is required."
    number: int | None = None                            # null clears; range checked in the usecase
    hymnal: str | None = Field(None, max_length=20)      # null -> "Choose one of your church's hymnals."
    scripture_refs: str | None = Field(None, max_length=2000)  # null or "" clears
    theme: str | None = Field(None, max_length=2000)            # null or "" clears
    link: str | None = Field(None, max_length=500)              # null or "" clears
    text_year: int | None = None                         # amendment 2026-09-26: null clears; range in the usecase
    hymnal_count: int | None = None                      # amendment 2026-09-26: null clears; range in the usecase

class HymnDetailOut(BaseModel):
    id: uuid.UUID; hymnal: str; title: str; number: int | None
    scripture_refs: str | None; theme: str | None; link: str | None
    text_year: int | None; hymnal_count: int | None     # amendment 2026-09-26 (additive)

class HymnalSourceOut(BaseModel):
    code: str; label: str | None; hymn_count: int
    has_scripture_refs: bool
    present: bool                         # the church has at least one hymn in this hymnal
```

- `ContactOut` is 5b's model: `{id, name: str?, email}`. 6a adds a `field_validator("name", mode="before")` to it that turns `""` (and whitespace-only) into `null`, so every client sees one "no name" value; old Streamlit rows store `""`. See Semantics → Contacts for why 6a still stores `""`.
- Field names in `HymnIn` mirror slice 3's `HymnOut`. If slice 3 named the link field `hymnary_link`, the request uses that name.
- `{deleted: true}` uses the shared `DeletedOut` in `api/schemas.py`, which 5a defines for `DELETE /services/{id}`; 6a and 6b reuse it (6a adds it only if 5a hasn't landed).

### Semantics

- **PATCH /church:**
  - An empty body, or all-null, returns the current profile and writes nothing.
  - Fields are validated in the order name, timezone, bible_translation, default_hymnal; the first failure is returned.
  - Nothing is written unless every provided field is valid.
  - Only provided fields are written, all in **one transaction** under `SELECT … FOR UPDATE` on the church row.
  - Settings keys are merged; unknown keys are preserved.
  - Trimming: `name` and `timezone` are trimmed. `default_benediction` has `\r\n` normalized to `\n` and is trimmed; `""` is stored as `""` (explicit "no default").
  - `default_hymnal` must be a hymnal the church currently has.
  - `bible_translation` must be in `available_translations()` at write time.
- **PUT /church/liturgy-prompts:**
  - Full replace of `settings.liturgy_prompts`: omitted keys go back to the default.
  - Cleaning is slice 4's `liturgy_prompts.clean_prompt_overrides(prompts)`, the **only** implementation (6a imports it and neither copies nor pre-processes it). That one rule normalizes `\r\n` → `\n`, trims, and drops a value that is blank or equals the trimmed default (parity with settings.py:141-153), so `PUT` and generation always agree on what counts as "default".
  - Every kept **section** template, in `PROMPT_KEYS` order, must pass `liturgy_prompts.template_error(...)`. The **system** prompt is sent to the model verbatim, not rendered (worship_service.py:731, 755-757), so only its length is checked. If slice 4 starts rendering it, validate it too.
  - The first failure raises `InvalidInput(code="prompt_invalid", field="prompts.<key>", message="<Label> prompt: <reason>")`. Label comes from `SECTION_LABELS`, or "Overall voice" for `system`.
  - Same locked merge as PATCH /church.
  - Reset all is `PUT {"prompts": {}}`. There is no DELETE route (inv §2.2 proposed one; a PUT with `{}` covers it without a second write path).
- **Locking and role re-read (all writes; 6b's evaluation order):** every write usecase takes `actor_id` (the caller's user id), opens one `session_scope`, and calls `lock_and_read_actor(s, church_id, actor_id)`. That takes `lock_church(s, church_id)` (`SELECT … FOR UPDATE` on the non-deleted church row; None → the `no_church_access` 403 above) and re-reads the caller's membership under the lock (gone → the same 403), returning the current role.
  - The **admin** writes (profile, prompts, contacts, `POST`/`DELETE /hymnals`) then call `church_admin.require_admin_role(role)`, which raises `Forbidden("Only church admins can do this.")` (no `details`) unless the re-read role is owner or admin. A caller demoted after `require_admin` ran therefore gets the role 403 and nothing is written.
  - The **hymn** writes (open to members) use the returned role for nothing more than proof of membership, except that a hymn write that sets `text_year` or `hymnal_count` also calls `require_admin_role` (*amendment 2026-09-26*; POST /hymns below).
  - Then the usecase reads, validates and writes in that transaction. For contacts and hymns this puts the duplicate check and the INSERT/UPDATE under the lock, so two concurrent submits can't both pass it. The lock is held for milliseconds and no external call happens inside it.
- **Contacts:**
  - `email` goes through `normalize_email`, a thin wrapper over 5b's `email_addresses.normalize_address`: blank after trimming → `InvalidInput(field="email", "Email is required.")`; `InvalidAddress` → `InvalidInput(field="email", "Enter a valid email address.")`. The rule is exactly the one `POST /bulletin-emails` re-applies when sending (ASCII-only labels; no IDN or non-ASCII local parts), so an address Settings accepts can never fail a send. No new dependency.
  - The stored email is the trimmed address with its case kept, as 5b stores and displays it.
  - Duplicates compare `lower(email)` within the church (5b's `dedupe_addresses` rule). PATCH excludes the contact itself.
  - `name` is trimmed; blank is stored as `""` (parity with settings.py:82; the frozen Streamlit prints a NULL name as "None", settings.py:265 and app.py:1105). `ContactOut` returns it as `null`.
- **POST /hymns:**
  - `title` is trimmed and required (an omitted title arrives as `""`).
  - `number`, when not null, must be 1–99999, else `InvalidInput(field="number", "Hymn number must be a whole number.")`.
  - `hymnal` defaults to the effective default. It must be one of the church's hymnals, unless the church has none, in which case any code matching `^[A-Za-z0-9_-]{2,20}$` is accepted and the default is `GG2013` (parity with repos/hymns.py:64).
  - `link`, when non-blank, must start with `https://`.
  - Blank `scripture_refs`, `theme` and `link` are stored as NULL.
  - *Amendment 2026-09-26 (index §6 question 23):* `text_year`, when not null, must be 1 to the current year, else `InvalidInput(field="text_year", "Year must be a whole number from 1 to {current year}.")`; `hymnal_count`, when not null, must be 0–100000, else `InvalidInput(field="hymnal_count", "Number of hymnals must be a whole number from 0 to 100000.")`. Null or omitted stores NULL (unknown). The facts are **admin-only** (owner decision): a request that sets either one (on POST a non-null value; on PATCH either key present, `null` included) calls `church_admin.require_admin_role(role)` on the re-read role before anything is validated or written, so a member gets the role 403 "Only church admins can do this." and nothing is written. Every other hymn field stays open to members (decision 5). The ops backfill CLI fills blanks only, so a hand-entered value survives its next run.
  - Duplicate rule: the same `(hymnal, number, lower(trim(title)))` as an existing hymn of the church → 409. This is the same key `import_hymns` uses (repos/hymns.py:95).
- **PATCH /hymns:** merges the provided fields into the row. Everything not provided, including `audio_url`, is kept. This avoids the full-replace hazard in `update_hymn` (repos/hymns.py:130-156). The same validation and duplicate rule apply, excluding the row itself. Changing `hymnal` is allowed, to any of the church's hymnals. *Amendment 2026-09-26:* `text_year` and `hymnal_count` are admin-only and validated as for POST, and `null` clears either one (back to unknown).
- **POST /hymnals:**
  - Looks `code` up in the source registry and imports that source's rows with `import_hymns` semantics: idempotent per `(hymnal, number, lower title)`; it fills missing enrichment only and never deletes (inv §1 H3).
  - Runs under the church-row lock, so two concurrent imports cannot both insert.
  - Re-adding a present source is allowed and typically returns `inserted: 0`.
- **DELETE /hymnals/{code}:**
  - Deletes every hymn of the church with that `hymnal`, under the church-row lock.
  - Refused if it is the church's only hymnal, or the effective default.
  - Services, `hymn_usage` and drafts are not touched. `hymn_usage` is a title/number snapshot. An archived service resolves each stored `hymn_id` to the row's **current** title, number and hymnal while the row exists (5a); once the row is gone it falls back to the snapshot saved with the service (`in_hymnal: false`). Drafts re-resolve by `hymn_id` (slice 3). So deleting keeps saved services' hymns as saved, while **editing** a hymn (PATCH /hymns) changes what past services show and print; the edit dialog says so.
- **PATCH /rubric (amendment 2026-09-26):** `church_admin.update_rubric(church_id, actor_id, patch)` runs in one session:
  1. `lock_and_read_actor`, then `require_admin_role`;
  2. `service_rubric.validate_patch(patch)`. A `ValueError` → `InvalidInput(code="invalid_rubric", message=str(exc))` with no field, so the body is PR #4's: 422, the same code and message, no `fields`. Nothing is written.
  3. Read the stored overrides from the locked row (a non-dict is treated as `{}`), then `service_rubric.apply_patch` (a `null` removes that override; an empty group is dropped);
  4. `merge_settings(church_id, {"rubric": overrides}, session=s)`;
  5. Return `{rubric: merge_rubric(overrides), customized: customized_keys(overrides), defaults: default_rubric()}`.

  The request and response are otherwise PR #4's. `repos.churches.update_church_rubric` is deleted, and its tests in `test_church_settings.py` are retargeted to the usecase, so there is one write path. `get_church_rubric_overrides` and `get_church_rubric` stay; frozen Streamlit and slices 3 and 4 read through them. `GET /rubric` is unchanged apart from `defaults`.
- **PUT /church/prayer-library (amendment 2026-09-26):** PR #7 §API "PUT semantics", through `usecases/prayer_library.py`, which imports slice 4's pure `prayer_library` reader and limits. It runs under the same lock and role re-read and writes the `prayer_library` key through `merge_settings`.

---

## Backend changes

### New modules

| Module | Contents |
|---|---|
| `backend/usecases/church_admin.py` (created here, or extended if 6b created it) | `update_profile(church_id, actor_id, patch: ProfilePatch, *, esv_key: str \| None) -> dict`; `get_prompts(church_id, *, can_edit: bool) -> dict`; `save_prompts(church_id, actor_id, prompts: dict[str, str]) -> dict`; `add_contact(church_id, actor_id, *, name: str \| None, email: str) -> dict`; `update_contact(church_id, actor_id, contact_id, *, changes: dict) -> dict`; `delete_contact(church_id, actor_id, contact_id) -> None`. Every write starts with `lock_and_read_actor` and then `require_admin_role(role: str) -> None` (raises `Forbidden("Only church admins can do this.")`, no `details`; also used by `hymn_library`'s hymnal writes). `save_prompts` cleans with `liturgy_prompts.clean_prompt_overrides` (slice 4; imported, **not** re-implemented here), then validates. Pure validators, table-tested: `clean_profile_patch` (below), `normalize_email(value: str) -> str` (wraps `email_addresses.normalize_address`; raises `InvalidInput`). No FastAPI or Streamlit imports. |
| `backend/usecases/hymn_library.py` | `create_hymn(church_id, actor_id, data) -> dict`; `update_hymn(church_id, actor_id, hymn_id, changes: dict) -> dict`; `delete_hymn(church_id, actor_id, hymn_id) -> None`; `list_sources(church_id) -> list[dict]`; `add_hymnal(church_id, actor_id, code) -> dict`; `remove_hymnal(church_id, actor_id, code) -> int`. Each opens one `session_scope` and passes it down; the writes start with `lock_and_read_actor`, and `add_hymnal` / `remove_hymnal` also call `church_admin.require_admin_role`, as do `create_hymn` and `update_hymn` when the request sets `text_year` or `hymnal_count` (*amendment 2026-09-26*). This is a separate module from slice 3's `usecases/hymns.py` (picker, matching, suggestions), so parallel work doesn't collide. |
| `backend/hymnal_sources.py` | The bundled-hymnal registry and CSV loading. `SEED_DIR = Path(__file__).parent / "seed" / "hymnals"`. `HYMNAL_LABELS = {"GG2013": "Glory to God (2013)", "PH1990": "The Presbyterian Hymnal (1990)"}`. `load_rows(source: Path or text stream, hymnal: str) -> list[dict]` (moved from import_hymnal.py:18-33; opens files as **`utf-8-sig`**, so a BOM no longer breaks the `number` header). File and catalog loading are split: `file_sources() -> dict[str, FileSource]` (no session; one per `SEED_DIR/*.csv`, code from the file stem, rows through `load_rows`, cached with `functools.lru_cache`, `has_scripture_refs` = any row has refs) and the session-taking `list_bundled(*, session: Session) -> list[BundledSource(code, label, hymn_count, has_scripture_refs)]`, which adds catalog sources (each distinct `hymn_catalog.hymnal`, for example GG2013 in production; counts by SQL) to the file sources. A file source wins when both define a code. `rows_for(code: str, *, session: Session) -> list[dict]` returns the file rows or the catalog rows mapped from `HymnCatalog`, and raises `KeyError` for unknown codes. `add_hymnal` calls `lock_and_read_actor` (then `require_admin_role`), `rows_for` and `import_hymns` in the same locked session. |
| `backend/seed/hymnals/PH1990.csv` | Moved with `git mv` from `data/hymnals/PH1990_hymns.csv` (605 rows; `number,title,tune`). Railway deploys only `backend/` (F §2.1). |
| `backend/timezones.py` (only if slice 1 didn't make it shareable) | Slice 1's definition, moved as is: `_zones() -> frozenset[str]` (`frozenset(zoneinfo.available_timezones())`, computed once) and `is_valid_timezone(name) -> bool` = `name in _zones()`, exact and case-sensitive. It is **not** a `zoneinfo.ZoneInfo(name)` lookup, which accepts values such as `america/new_york` or `posixrules` on some filesystems and not others (slice 2 rejects that approach for `timezone_valid`, so the two would disagree). `tzdata` in `backend/requirements.txt` so slim images have the database. |
| `backend/api/routes/church_prompts.py` | GET and PUT `/church/liturgy-prompts` (F §2.1 names this module). |
| `backend/api/routes/prayer_library.py`, `backend/usecases/prayer_library.py` (amendment 2026-09-26, PR #7) | The three prayer-library routes and their usecase (PR #7 §API): `get_library(church_id, *, can_edit)`, `save_library(church_id, actor_id, body)` (locked, role re-read, normalized, validated, merged into `settings`), `draft_voice_profile(church_id, *, ai=openai_client, clock=time.monotonic)` (read, close the session, fit the prayers to `MAX_PROMPT_CHARS` by the equal-share cut in API → "Draft input budget", then one `complete` call inside a 75 s deadline, capped at 2 000 characters). The cut is a pure helper, `fit_prayers(prayers, budget) -> list[str]`, in the same module. New error messages go through the registry (F §1.5). |

The profile patch types in `usecases/church_admin.py`:

```python
@dataclass(frozen=True)
class ProfilePatch:                 # mirrors ChurchPatchIn; None = not provided (unchanged)
    name: str | None = None
    timezone: str | None = None
    bible_translation: str | None = None
    default_hymnal: str | None = None
    default_benediction: str | None = None

@dataclass(frozen=True)
class CleanProfile:
    name: str | None                # trimmed, or None = leave unchanged
    timezone: str | None            # trimmed, or None
    settings_patch: dict[str, str]  # only the provided keys among bible_translation,
                                    # default_hymnal, default_benediction (normalized)

def clean_profile_patch(patch: ProfilePatch, *,
                        translations: Collection[str],      # available_translations() ids
                        church_hymnals: Collection[str]     # the church's codes, read under the lock
                        ) -> CleanProfile: ...
```

`clean_profile_patch` is pure: it trims and normalizes, checks the fields in the order name, timezone, bible_translation, default_hymnal, and raises the first `InvalidInput` with the API table's message. `update_profile` opens the session, calls `lock_and_read_actor` and `require_admin_role`, reads the church's hymnal codes, calls `clean_profile_patch` with `translations` = the ids from `available_translations(esv_key=esv_key)`, and then `repos.churches.update_profile(..., session=s)`. The route builds `ProfilePatch` from `ChurchPatchIn` (null and omitted both mean "not provided") and passes `actor_id=user.id` and `esv_key=settings.esv_api_key`.

### Changed modules

| Module | Change |
|---|---|
| The route module serving `GET /church` (`routes/me.py` in slice 0; `routes/churches.py` if slice 1 moved it) | Add `PATCH /church`. It builds the response with the same profile builder `GET /church` uses (slices 2–4), so the two can't drift. |
| `routes/contacts.py` (5b) | Add POST, PATCH and DELETE, and `ContactIn` / `ContactPatchIn`. Add to 5b's `ContactOut` the `name` validator that maps `""` to `null`. |
| `routes/hymns.py` (3) | Add POST, PATCH and DELETE. Add `q` to GET if slice 3 didn't. |
| `routes/hymnals.py` (3) | Add `label` to the GET items; add `GET /hymnal-sources`, `POST /hymnals` and `DELETE /hymnals/{code}`. |
| `repos/churches.py` | Add `lock_church(session, church_id) -> Church \| None` if 6b didn't: `select(Church).where(Church.id == cid, Church.deleted_at.is_(None)).with_for_update()`. `_merge_settings` (87-96) becomes `merge_settings(church_id, patch, *, session=None)`. It locks through `lock_church` and assigns a **new** dict (so SQLAlchemy sees the change). New `update_profile(church_id, *, name=None, timezone=None, settings_patch=None, session=None) -> dict or None`: one locked read-modify-write; None when the church is missing or soft-deleted, which the usecases turn into the `no_church_access` 403 (API). `set_church_prompts` and `set_church_translation` gain `session=None` and go through `merge_settings`. `update_church(settings=…)` (74-84) gets a docstring warning that it **replaces** settings; the API never calls it. |
| `repos/hymns.py` | `add_hymn` gains `session=None`. New `patch_hymn(hymn_id, church_id, changes, *, session=None) -> dict or None`, which sets only the keys provided (allowed: title, number, hymnal, scripture_refs, theme, hymnary_link, and, *amendment 2026-09-26*, text_year and hymnal_count; `add_hymn` accepts the two facts too). New `find_duplicate(church_id, hymnal, number, title, *, exclude_id=None, session=None) -> bool`. New `delete_hymnal(church_id, hymnal, *, session=None) -> int`. Counts come from slice 3's `hymnal_summaries(church_id, *, session=None)`; 6a adds a count helper only if slice 3 didn't ship one. `import_hymns` gains `session=None` and **drops the per-row `session.flush()`** (line 115). The objects are tracked in `by_key`, and SQLAlchemy 2.x batches the INSERTs at flush ("insertmanyvalues"), which keeps a 605-row import well inside the 10 s budget over the Supabase pooler. `get_hymn` is added if slices 3/4 didn't. Malformed ids go through `db.ids.as_uuid` (F §2.2.5). `update_hymn` and `list_hymns` stay for existing callers. |
| `email_contacts.py` | `add_contact` and `delete_contact` gain `session=None`. New `update_contact(contact_id, church_id, changes: dict, *, session=None) -> dict or None` (sets only the keys given, `name` and/or `email`; already cleaned by the usecase) and `email_exists(church_id, email, *, exclude_id=None, session=None) -> bool` (compares `lower(email)`). `_as_uuid` is replaced by `db.ids.as_uuid`. `get_contacts_for_display` stays (dead, inv §1 I; still asserted by `backend/tests/test_email_contacts.py`); slice 7 deletes it with that assertion, as 5b schedules. |
| `email_addresses.py` (5b) | Unchanged; reused through `church_admin.normalize_email`. 6a adds no `email-validator` to `backend/requirements.txt`. |
| `usecases/email.py` (5b) | `MALFORMED_CONTACT_HINT` changes from "An admin can remove it and add it again in the current app's Settings." to **"An admin can fix it in Settings → Contacts."** Contacts are now editable in the new app, and after slice 7 there is no "current app" to send admins to. The full 422 becomes "The saved contact “{name, or the address}” has an invalid email address. An admin can fix it in Settings → Contacts." Nothing else in the send path changes. |
| `usecases/members.py` (6b) | Holds `lock_and_read_actor`. 6a creates the module with only that function if 6b hasn't landed (Assumed interfaces). |
| `api/settings.py` | Adds `esv_api_key: str \| None`, read from `ESV_API_KEY` (stripped; blank → None). This closes slice 2's recorded deviation from F §2.3.5; the Railway variable name is unchanged, so deploys need no change. |
| `scripture_fetcher.py` (2) | `_esv_key()` and its `os.getenv` are deleted. `esv_configured`, `available_translations`, `fetch_passage` and `get_passage_text` gain a **required** keyword-only `esv_key: str \| None`, and the ESV request uses the key it is given. A call without it is a `TypeError`, never a silent "no ESV". Names and return shapes are otherwise unchanged. |
| Callers of those functions: slice 2's `usecases/passages.py` (`translation_options`, `plan_passages` / `load_passages`, the `get_passage_text` re-export) and `usecases/church_profile.get_church_profile`; slice 3's NT-text lookup for suggestions; 6a's `update_profile` | Each takes `esv_key` keyword-only and passes it down. Routes read it once with `settings: Settings = Depends(get_settings)` and pass `settings.esv_api_key`. No domain module reads the environment for it. Behavior is unchanged: the same translations, gating and ESV requests. |
| `liturgy_prompts.py` | `PLACEHOLDER_HELP` (40-43) is unchanged. The page adds the literal-brace sentence on the client, so the frozen Streamlit caption isn't affected either way. Uses `PROMPT_KEYS`, `SECTION_LABELS`, `default_prompts()`, and slice 4's `template_error` and `clean_prompt_overrides` (whose `\r\n` → `\n` normalization and its test are slice 4's). 6a adds nothing to this module. |
| `import_hymnal.py` (CLI, kept per inv §1 H3) | `load_rows` delegates to `hymnal_sources.load_rows`. `load_dotenv()` moves from import time (13-15) into `main()` (F §2.3.5). `--csv` becomes optional when `--hymnal` names a bundled source. The docstring path becomes `backend/seed/hymnals/PH1990.csv`. It remains an ops tool with no role check, run only by the owner with the production `DATABASE_URL`. |
| `api/schemas.py` | Reuses 5a's `DeletedOut` (defined for `DELETE /services/{id}`); 6a adds it only if 5a hasn't landed. The request models above live in their route modules; only models used by two or more modules go here (F §1.3). |
| `frontend/src/lib/api/openapi.json`, `schema.d.ts` | Regenerated (F §1.11). |
| `backend/usecases/church_admin.py` (amendment 2026-09-26) | Adds `update_rubric(church_id, actor_id, patch) -> dict` (Semantics). |
| `backend/api/routes/rubric.py` (PR #4; amendment 2026-09-26) | `PATCH` calls `church_admin.update_rubric(church.id, actor_id=user.id, patch=…)` instead of the repo function. The route keeps its path, guards and body. |
| `backend/api/schemas.py` (amendment 2026-09-26) | `RubricOut` gains `defaults: RubricModel` (additive). |
| `repos/churches.py` (amendment 2026-09-26) | PR #4's `_lock_live_church` is renamed `lock_church` (the row above adds it only if neither PR #4 nor 6b did). `_merge_settings` already locks since PR #4; it becomes `merge_settings(…, session=None)` as described above. `update_church_rubric` is deleted (Semantics → PATCH /rubric). |

### Domain functions reused

- `scripture_fetcher.available_translations` (48-55) and `translation_label`: translation validation.
- `liturgy_prompts.default_prompts` (134-138), `PROMPT_KEYS` (122), `SECTION_ORDER` and `SECTION_LABELS` (18-38), `PLACEHOLDER_HELP` (40-43), and slice 4's `template_error` and `clean_prompt_overrides`.
- `usecases.members.lock_and_read_actor` (6b): the locked membership and role re-read for every write.
- `repos.hymns.import_hymns` (84-127): hymnal import semantics.
- `repos.hymns.list_church_hymnals` (45-52): the church's hymnals, for default and hymnal validation.
- `email_contacts.list_contacts` (24-37): used by 5b's GET, unchanged.
- `tenancy.is_admin`: computes `can_edit` for prompts.

### Streamlit coupling removed

| Streamlit location | Replacement |
|---|---|
| `NotAuthorizedError` and `_require_admin/_member/_owner` (settings.py:33-55), which re-read the role with `get_role` (and don't exclude soft-deleted churches) | Route guards: `require_church` for hymns and prompt reads, `require_admin` for profile, prompts, contacts and hymnals. The role comes from `validate_active_church` on every request (F §1.2). Because that snapshot is read in an earlier transaction, every write usecase also re-reads the membership and role under the church-row lock (`lock_and_read_actor`, 6b's rule) and the admin writes apply `require_admin_role` to that re-read role. Nothing in 6a is finer than the role. |
| `ValueError` messages (settings.py:66-68, 81, 94, 167) | `InvalidInput(field=…, message=…)` with the same wording → 422 plus `fields`. |
| Direct ORM in the helper and view (settings.py:69-74, 180-182) | `repos.churches.update_profile` inside `usecases.church_admin.update_profile`. |
| Two transactions for profile plus translation (settings.py:211-212) | One `session_scope` in `update_profile`. |
| Streamlit-keyed prompt widgets that go stale (settings.py:229-237) | The client form re-initializes from the server response (see UX). |
| `submit_prompts` cleaning (settings.py:141-153) | Slice 4's `liturgy_prompts.clean_prompt_overrides` (the only implementation; imported by `church_admin.save_prompts`), plus validation. |
| `submit_translation` validating against the zero-argument `available_translations()` (settings.py:165), with the ESV key read from the environment | `clean_profile_patch` against `available_translations(esv_key=…)`, the key coming from `api/settings.py`. |
| The `int(hnum) if hnum.isdigit() else None` coercion (settings.py:298) | A typed `number: int?` plus client validation. |

Per F §2.3.2 nothing is re-exported from `streamlit_views/settings.py`. That module is frozen on `main` (F §6.1).

### Tenancy and data access

- Every usecase takes `church_id` from `ActiveChurch.id` only. The request models forbid extra fields, so a smuggled `church_id` is a 422.
- Hymn and contact ids from the path are looked up `WHERE id = :id AND church_id = :church`. Another church's id → 404 (F §1.2.2).
- Hymnal codes are not ids. Every hymnal query filters by `church_id`, so `DELETE /hymnals/GG2013` only ever touches the caller's church.
- Every write holds the church row lock only for its own read-validate-write. No external call happens inside a transaction. A church soft-deleted, or a membership removed, after the guard ran yields the `no_church_access` 403, and an admin demoted after the guard ran yields the role 403; neither writes anything.
- `GET /hymnal-sources` reads `hymn_catalog`, which is global and read-only. Only codes, labels and counts are exposed, never other churches' data.

---

## Data and migrations

**No DDL and no Alembic revision in 6a.**
- `churches.settings` gains two JSON keys, already planned in F §3.5:
  - `default_benediction: str`: absent means the fallback `"Halverson"`; `""` means no default.
  - `default_hymnal: str`: absent or null means the effective default rule applies.
- `bible_translation` and `liturgy_prompts` keep their current shapes (repos/churches.py:99-129).
- No backfill. "Seeded with the current value" (decision 9) is satisfied by the read-side fallback: churches without the key behave exactly as before until an admin saves the profile.
- *Amendment 2026-09-26:* two more JSON keys are written here, still with no DDL (F §3.5):
  - `rubric`: PR #4's sparse overrides, already written by `PATCH /rubric` since PR #4 and read by frozen Streamlit, slice 3 and slice 4 through `merge_rubric`, which ignores invalid values. Its shape is unchanged.
  - `prayer_library`: PR #7's `{prayers: [{id, type, text, added_at}], voice_profile}`, read by slice 4. It is absent until an admin saves the Prayers page, and frozen Streamlit ignores it.

**File move:** `data/hymnals/PH1990_hymns.csv` → `backend/seed/hymnals/PH1990.csv` (`git mv`; content unchanged). `data/hymnals/` is removed. A test asserts that the file exists under `backend/` and loads 605 rows.

**Compatibility with the frozen Streamlit app** (F §6.2):
- **Reads:** Streamlit reads `settings.liturgy_prompts` and `settings.bible_translation`, whose shapes are unchanged. It ignores `default_benediction` and `default_hymnal`, so it keeps printing its constant "Halverson" and its alphabetical hymnal default. That is accepted: the tester builds services in the new app after the parity gate.
- **Writes:** Streamlit's `_merge_settings` copies the dict and updates only its own key, so it preserves the new keys. Its writes don't take the row lock, so a concurrent Streamlit settings save can still overwrite an API write made in the same instant. This is accepted (F §1.7). *Amendment 2026-09-26:* this is no longer true of a `streamlit-frozen` cut after PR #4, which the ops freeze is. Since PR #4, Streamlit's `_merge_settings` locks the church row (`SELECT … FOR UPDATE` in the same transaction), so on Postgres its settings saves and the API's locked merges wait for each other and neither loses a key. Streamlit's other writes (hymns, contacts, profile name and timezone) are still unlocked. Once 6a ships, the settings `LegacySettingsNote` points the tester to Streamlit only for people and invites, which don't write `churches.settings`, so the tester has no reason to use Streamlit's profile or prompt tabs; after 6b the note is gone.
- **Profile saves:** Streamlit's "Save profile" always re-writes `bible_translation` with its own selectbox value (settings.py:212). Documented; accepted.
- **Hymnals:** hymns added through 6a use one of the church's existing hymnal codes. Adding PH1990 makes Streamlit show its hymnal switcher, which already works (inv §1 D2).
- **Hymn and contact edits:** plain row updates. Streamlit lists at most 50 hymns and reads all contacts, both unaffected.
- **Timezones:** free-text timezones Streamlit wrote are tolerated. `GET /church.timezone_valid` is false, and the profile shows the warning without forcing a change.

**Postgres specifics:** `with_for_update()` is a no-op on SQLite. The concurrency test is `@pytest.mark.postgres` (F §5.1).

---

## Frontend changes

### Routes (all client components under `src/app/(signed-in)/(church)/settings/`)

| Path | Page component |
|---|---|
| `church/page.tsx` | `<ChurchProfilePage>` |
| `hymns/page.tsx` | `<HymnsSettingsPage>` (HymnalsCard + HymnLibrary) |
| `liturgy/page.tsx` | `<LiturgyPromptsPage>` |
| `contacts/page.tsx` | `<ContactsSettingsPage>` |
| `prayers/page.tsx` (amendment 2026-09-26, PR #7) | `<PrayersSettingsPage>` |
| `rubric/page.tsx` (amendment 2026-09-26, PR #4) | `<RubricSettingsPage>` |
| `page.tsx` (5b) | redirect target → `/settings/church` |

### Components (`src/components/settings/`)

- **Church profile:**
  - `ChurchProfileForm`.
  - Slice 1's `TimezoneCombobox` (`src/components/app/timezone-combobox.tsx`), extended with the optional `warning` prop and the out-of-list value item described under the profile page. Slice 1's create-church form passes no warning and is unaffected.
  - `TranslationSelect`, `DefaultHymnalSelect` (stale-value item; hidden with no hymnals), `BenedictionField` (with the Halverson note).
- **Hymns:**
  - `HymnalsCard`, `AddHymnalDialog`, `RemoveHymnalDialog`.
  - `HymnLibrary` (search, chips, list, Show more).
  - `HymnDialog` (mode `"add" | "edit"`) with its delete confirmation.
- **Liturgy:** `LiturgyPromptsForm`, `PromptCard`.
- **Contacts:** `ContactsList`, `ContactAddForm`, `ContactEditDialog`.
- **Prayers (amendment 2026-09-26, PR #7):** `VoiceProfileCard` (textarea, "Update from my prayers", side-by-side draft with "Use this draft" / "Keep mine"), `PrayerList`, `PrayerRow` (type `Select` with an `items` map, F §4.9.3), with the remove `ConfirmDialog`.
- **Rubric (amendment 2026-09-26, PR #4):** `RubricForm`, `HymnPreferencesCard`, `ChecklistCard` (points, add, remove, reset, Customized badge), `RubricFooter`.
- **Shared:** `ReadOnlyBanner(text)`.
- **5b files:**
  - `sections.ts`: prepend the four entries to `SETTINGS_SECTIONS`.
  - `legacy-settings-note.tsx`: the new text "People and invites are still managed in the current app for now." (link behavior unchanged).
  - `src/components/builder/review/` `EmailBulletinDialog`: the admin-only **Manage contacts** link (`<Link href="/settings/contacts">`) in the empty contacts state; `isAdmin` from `useChurch().role`.
  - (5b's one backend hand-off, the `MALFORMED_CONTACT_HINT` text in `usecases/email.py`, is under Backend changes → Changed modules. The text is part of the server's 422 message, so no frontend change goes with it.)
- **Slice 3 file:** `src/lib/features.ts`: `SETTINGS_HYMNS_READY = true`.
- **Slice 4 file:** `src/components/builder/liturgy/SectionCard.tsx`: in the Benediction card's origin-`default` hint, "Your church's default benediction. Admins can change it in Settings.", the word "Settings" becomes `<Link href="/settings/church">Settings</Link>` (shown to every role; members land on the read-only profile). The rest of the hint text is unchanged. If slice 4 serves this hint from the config rather than the client, the client still renders only the trailing "Settings" as the link.
- **Leave guard** (`src/components/app/leave-guard.tsx`, with the registry in `src/lib/leave-guard.ts`): `useLeaveGuard(dirty: boolean)`. While `dirty` it:
  - registers `beforeunload`;
  - adds a capture-phase `click` listener on `document` for same-origin `<a>` elements (no modifier keys, no `target`, no `download`, a different path): `preventDefault()` + `stopPropagation()` (so Next's `Link` handler doesn't run), opens the "Discard unsaved changes?" `ConfirmDialog`, and on confirm `router.push(href)`;
  - registers itself so `confirmLeave(): Promise<boolean>` (resolves true at once when no guard is active) opens the same dialog. 6a adds `if (!(await confirmLeave())) return;` at the top of slice 1's `onSelectChurch(id)` in the `(church)` layout.
  - `ChurchProfileForm` and `LiturgyPromptsForm` call it with their dirty flag. A successful save clears the flag before any navigation.

Base UI components needed: input, textarea, label, dialog, alert-dialog, combobox, collapsible, badge, select. Generate any that are missing with `npx shadcn@latest add` (F §4.9.1). No Radix snippets. `Select` gets `items` (F §4.9.3).

### Pure helpers (unit-tested, `src/lib/settings/`)

- `profile.ts`:
  - `profileFormFrom(profile: ChurchProfile) -> ProfileForm`: the initial-values rule under the profile page (stored translation or hymnal when non-null, else the effective one). Used for both the form and the baseline.
  - `diffProfile(baseline: ProfileForm, current: ProfileForm) -> ChurchPatch`: only changed fields, with values trimmed the way the server trims them.
  - `rebaseForm<T extends Record<string, string>>(oldBaseline: T, current: T, next: T) -> T`: for each key, `current[k] === oldBaseline[k] ? next[k] : current[k]`. Used on a background refetch while dirty (UX, "Every page").
  - `hymnalItems(hymnals, stored: string | null) -> {value, label}[]`: the church's hymnals plus the "{code} (no longer in your hymnals)" item when `stored` is non-null and missing.
  - `benedictionIsShorthand(text) -> boolean`: true when the trimmed text is exactly "Halverson".
- `prompts.ts`:
  - `initialPromptValues(out) -> Record<PromptKey, string>`: override, else default.
  - `promptsPayload(values, fields) -> Record<PromptKey, string>`: only keys whose trimmed value differs from the trimmed default.
  - `isCustomized(value, field)`.
  - Rebasing on refetch reuses `rebaseForm` over `initialPromptValues`.
- `hymns.ts`:
  - `parseHymnNumber(text) -> number | null | "invalid"`.
  - *Amendment 2026-09-26:* `parseTextYear(text, thisYear)` and `parseHymnalCount(text)`, each `-> number | null | "invalid"` (`""` → null; the ranges 1–`thisYear` and 0–100000).
  - `hymnPatch(baseline, form) -> HymnPatch`: changed fields only; `""` → null for the clearable fields (*amendment 2026-09-26:* including `text_year` and `hymnal_count`, which are included only when `isAdmin`). Because a request with the facts can get the role 403, the hymn add and edit mutations also set `meta: { forbiddenIsRole: true }`.
- `email.ts`: `looksLikeEmail(text)`, a lenient client pre-check. The server is authoritative.
- `rubric.ts` (amendment 2026-09-26): `cleanPoints(points) -> string[]` (trim, collapse whitespace runs, drop blanks: the server's rule); `rubricFormFrom(out)`; `rubricPatch(baseline, current, defaults) -> object` (changed items only; an item equal to its default → `null`; never an empty list); `checklistError(points)` ("Keep at least one point, or use Reset to default."); `yearError(value, thisYear)` ("The preferred year must be between 1500 and {thisYear}.").
- `prayers.ts` (amendment 2026-09-26, PR #7): `prayersPayload(rows, profile)` (keeps each row's `id`; new rows have none), `firstLine(text)`, `isDirty(baseline, current)`.
- Time zones: none here. 6a uses slice 1's `src/lib/timezones.ts` as is.

### Queries and mutations (`src/lib/queries/`)

| File | Hooks | Key / invalidation |
|---|---|---|
| `church.ts` | `useUpdateChurch()` → `PATCH /church` | On success: `setQueryData(["church", id, "profile"], response)`, then invalidate `["me"]`, and invalidate `["church", id, "hymnals"]` when `default_hymnal` was sent. (This hymnals entry is 6a's addition to the F §4.4 map, recorded in F's amendments from slice specs.) |
| `prompts.ts` | `useLiturgyPrompts()`, `useSaveLiturgyPrompts()` | `["church", id, "liturgy-prompts"]`; set from the PUT response |
| `contacts.ts` (5b) | add `useCreateContact`, `useUpdateContact`, `useDeleteContact` | invalidate `["church", id, "contacts"]` |
| `hymns.ts` (3) | add `useHymnLibrary({hymnal, q})` (`useInfiniteQuery`, `limit: 50`, `getNextPageParam` from `offset + items.length < total`), `useCreateHymn`, `useUpdateHymn`, `useDeleteHymn` | key `["church", id, "hymns", {view: "library", hymnal, q}]`; mutations invalidate the prefixes `["church", id, "hymns"]` and `["church", id, "hymnals"]` (F §4.4), plus `["church", id, "profile"]` because deleting or moving a hymn can change `effective_hymnal` (the profile entry is in F §4.4 as amended from slices 3 and 6a). Because the builder's `useHymns` shares the prefix, the picker refetches without a reload (F acceptance 18). |
| `hymnals.ts` (3) | add `useHymnalSources()`, `useAddHymnal()`, `useRemoveHymnal()` | new key `["church", id, "hymnal-sources"]` (added to `keys.ts`); add and remove invalidate `hymns`, `hymnals`, `hymnal-sources` and `profile` |
| `rubric.ts` (amendment 2026-09-26) | `useRubric()`, `useSaveRubric()` → `PATCH /rubric` | key `["church", id, "rubric"]` (added to `keys.ts`); set from the PATCH response; also invalidates `["church", id, "hymns"]` when `prefer_before_year` was sent, because `HymnOut.newer_than_preferred` depends on it (slice 3). Liturgy generation reads the rubric on the server, so nothing else is invalidated. |
| `prayer-library.ts` (amendment 2026-09-26, PR #7) | `usePrayerLibrary()`, `useSavePrayerLibrary()` → `PUT`, `useDraftVoiceProfile()` → `POST …/voice-profile-draft` (`timeoutMs: 90_000`, `signal` for Cancel) | key `["church", id, "prayer-library"]` (added to `keys.ts`); set from the PUT response; the draft mutation touches no cache (the draft is not stored) |

- All hooks use `api.church` (F §4.5).
- Mutations are not optimistic (F §4.4).
- The 6a mutations that hit admin routes set `meta: { forbiddenIsRole: true }` (see Assumed interfaces).
- Role comes from `useChurch().role`; `isAdmin = role === "owner" || role === "admin"`. It only decides what is shown; the server enforces.

### Draft store

6a does **not** read or write the draft (F §4.6). What it relies on:
- **Changing the default translation:** drafts with `readings.translation: null` follow it through the invalidated profile (slice 2).
- **Changing the default hymnal:** drafts with `hymns.hymnal: null` show the new default hymnal. Existing picks stay valid because they resolve by `hymn_id` (slice 3).
- **Changing the default benediction:** only benediction cards with `origin: "default"` update (slice 4). Typed, AI, archived and empty cards don't.
- **Deleting a hymn or removing a hymnal:** picks with a missing `hymn_id` show slice 3's replacement notice.

---

## Behavior changes vs Streamlit

| # | Area | Streamlit today | New app | Why |
|---|---|---|---|---|
| 1 | Timezone | Free text, not validated (settings.py:63-68) | IANA-only combobox; server 422 "Unknown timezone."; a stored invalid value is shown with a warning and kept until edited; "use this device's timezone" shortcut | F §7.4; inv §1 G2 |
| 2 | Timezone help | Onboarding said it "drives first-Sunday and the 12-week window" | "Sets the default service date (the next Sunday in this time zone)." (slice 1's string) | It was wrong (inv §1 B2); F §4.10 and §7.4 |
| 3 | Profile save | Two transactions: profile, then translation (settings.py:211-212) | One transaction under a row lock; nothing written if any field is invalid | inv §1 G2, F §1.7 |
| 4 | Translation | An unavailable stored default (for example `esv` without a key) was overwritten with `web` on the next profile save | Only changed fields are sent; an unavailable stored value is shown and kept | inv §1 G3 edge case |
| 5 | Default benediction | Fixed app constant "Halverson" (app.py:67) | Per-church setting, fallback "Halverson"; blank = no default (the AI writes it); a note when the value is the bare word | Decision 9 |
| 6 | Default hymnal | Alphabetical default only (inv §1 D2) | Per-church setting, validated against the church's hymnals | Decision 9 |
| 7 | Settings JSON writes | Unlocked read-modify-write (repos/churches.py:87-96) | `SELECT … FOR UPDATE` merge; concurrent profile and prompt saves keep both | F §1.7, §7.4 |
| 8 | Contacts | No format check, no dedupe, no edit, delete without confirmation, a failed cross-church delete silently ignored | Email format check with 5b's `normalize_address` (the same rule the send applies), case-insensitive dedupe (409), edit, delete confirmation, 404 for unknown or other-church ids | inv §1 G4 |
| 9 | Contact display | "**{name}** — {email}" even with a blank name | The name only when present | Polish |
| 10 | Hymn list | Only the first 50 of all hymns; NULL-number hymns could fall outside them on Postgres (inv §1 G5) | Search, hymnal filter, "Show more" paging, NULLs last; every hymn reachable | inv §1 G5 |
| 11 | Hymn edit | `submit_update_hymn` had no UI; `update_hymn` replaced every field | Edit dialog; PATCH merges and keeps untouched fields, including `audio_url` | inv §1 G5, §1 I |
| 12 | Hymn add | Title, number and refs only; always GG2013 (repos/hymns.py:64); a non-numeric number silently became None | Asks for the hymnal (default = church default); adds themes and link; number must be a whole number; link must be https; exact duplicates refused (409) | inv §1 D2 edge, §1 D8, §7 Q16 |
| 13 | Hymn delete | Any member, no confirmation; a cross-church id silently ignored | Still any member (Streamlit parity, pending Open question 2), now **with confirmation**; 404 for unknown or other-church ids | Parity (settings.py:303-306; decision 5 covers only add/edit), F §4.8 |
| 14 | Builder refresh after hymn edits | Manual "Refresh hymn list" (app.py:723-725) | Automatic through query invalidation | inv §4 caching |
| 15 | Hymnals | CLI only (`import_hymnal.py`), no role check | Admins add bundled hymnals (PH1990 from the seed file, catalog hymnals such as GG2013) and can remove a non-default hymnal; PH1990's missing scripture data is explained | Decision 9, inv §1 H3, §7 Q16 |
| 16 | Hymnal CSV loader | UTF-8 without BOM handling | `utf-8-sig` | inv §1 H3 |
| 17 | Prompt validation | Malformed braces accepted on save, crashing generation later (inv §0 item 4) | Rejected on save: 422 `prompt_invalid` naming the section, with the field focused; length limit 8000 per prompt | inv §1 G6, F §2.8 |
| 18 | Prompt reset | "Reset all" without confirmation; no per-prompt reset | Per-prompt "Reset to default" (unsaved until Save); "Reset all" asks for confirmation | F §4.8 lossy actions |
| 19 | Prompt form state | Keyed widgets could show stale text after save, reset or church switch | Re-initialized from the server response; remounted on church switch | inv §1 G6 |
| 20 | Success messages | "Profile updated.", "Prompts saved.", "Contact added.", "Hymn added." were wiped by `st.rerun()` (inv §0 item 3) | Visible toasts ("Profile saved.", "Prompts saved.", "Hymn added.", …); contact add shows the new row instead | inv §0 item 3 |
| 21 | Role-denied message | "You must be an admin to do that." | "Only church admins can do this." (slice 0's `require_admin` message, deps.py:89-92) | One message across the API |
| 22 | Read-only notices | "Only admins can edit the prompts (you can read them below)."; "Only admins can add or remove contacts." | "Only admins can edit the prompts. You can read them below."; "Only admins can add or change contacts." (contacts can now be edited). The profile notice, "Only admins can edit the church profile." (settings.py:194), is unchanged. | Copy polish; contact edit is new |
| 23 | Service rubric (amendment 2026-09-26) | No editor anywhere. `PATCH /rubric` existed for API clients only (inv G11) | `/settings/rubric` for admins, read-only for members. An item saved equal to its default is stored as "not customized". `PATCH /rubric` now re-reads the role under the church-row lock, and `GET /rubric` gains `defaults` | PR #4 left the editor to slice 6; F §1.7 |
| 24 | Prayer library (amendment 2026-09-26) | Does not exist | `/settings/prayers` and its three routes, new app only | PR #7 |
| 25 | Hymn year and familiarity (amendment 2026-09-26) | Set only by the ops backfill CLI (PR #4, inv H14); no screen | Admins edit "Year the words were written" and "Number of hymnals (familiarity)" in the hymn dialog (read-only for members); clearing a field sets it back to unknown; the backfill still fills blanks only | Owner decision (index §6 question 23) |

Carried over unchanged:
- Members may add and edit hymns, and admins manage the profile, translation, prompts and contacts (decision 5). Members may also delete hymns (Streamlit parity, pending Open question 2).
- Members can read the contacts and the prompts.
- The prompt-override semantics (blank or default = not stored; `{}` = all defaults).
- `import_hymns` idempotency.
- Contact ordering.
- The translation list and ESV gating.

---

## Testing

### Backend (pytest, repo root; SQLite unless marked)

**Usecase and unit tests**
- `backend/tests/test_church_admin.py`:
  - `update_profile`:
    - Trims name and timezone.
    - Messages: "Church name is required." (`"  "`), "Timezone is required." (`""`), "Unknown timezone." (`"Mars/Olympus"`, `"America/New York"`, `"../etc"`, and the wrong-case `"america/new_york"`, which slice 2's `timezone_valid` also rejects), "Unknown or unavailable translation." (`"xyz"`, and `"esv"` with `esv_key=None`), "Choose one of your church's hymnals." (a code the church lacks). `"esv"` is accepted with `esv_key="k"`.
    - An invalid field writes nothing: the name is unchanged when the translation is invalid.
    - Omitted fields are untouched: a stored `esv` survives a name-only update with ESV unconfigured.
    - Unknown settings keys (`{"foo": 1}`) and `liturgy_prompts` survive a profile update.
    - `default_benediction`: `"  Go in peace.\r\n"` is stored as `"Go in peace."`; `""` is stored as `""`, and the profile then returns `""`, not `"Halverson"`; an absent key returns `"Halverson"`.
    - Church gone: soft-delete the church after building the request, then `update_profile`, `save_prompts`, `add_contact` and `create_hymn` each raise `Forbidden` with `details == {"reason": "no_church_access"}` and write nothing.
  - **Role re-read under the lock** (6b's rule; the membership row is changed directly in the database after the actor's admin role was "checked", i.e. just before the usecase call):
    - An admin demoted to member → `update_profile`, `save_prompts`, `add_contact`, `update_contact`, `delete_contact`, `add_hymnal` and `remove_hymnal` each raise `Forbidden("Only church admins can do this.")` with **no** `reason` in `details`, and write nothing (the church name, prompts, contacts and hymn count are unchanged).
    - The same demoted user can still `create_hymn` (members may add hymns).
    - An admin removed from the church → `update_profile` raises `Forbidden` with `details == {"reason": "no_church_access"}`; a member removed from the church → `create_hymn` raises the same.
  - `clean_profile_patch` table test (pure, no database): an all-None `ProfilePatch` → empty `CleanProfile`; field order of the first error; `default_hymnal` checked against the passed `church_hymnals`; `bible_translation` against the passed `translations`.
  - No `clean_prompt_overrides` unit test here: the function is slice 4's, and its table test (including `\r\n` → `\n`) lives in `test_liturgy_prompts.py`. 6a covers the wiring at the API level (below).
  - `save_prompts` validation table:
    - `{curly`, `{0}`, a lone `}`, `{"a": 1}`, `{foo.bar}` → `prompt_invalid` naming the section, with `field == "prompts.<key>"` and the message "<Label> prompt: " + slice 4's pinned reason (for example `{curly` in `benediction` → "Benediction prompt: It has a { or } without a partner. Use {{ or }} to print a brace.").
    - `{{literal}}` and `{unknown_name}` are accepted.
    - Braces in `system` are accepted (not rendered).
    - With two bad keys, the first in `PROMPT_KEYS` order is reported.
  - `normalize_email` table (5b's rules): `" Mary@Example.org "` → `"Mary@Example.org"` (trimmed, case kept); missing `@`, two `@`, a space inside, `a@b` (one label), `josé@x.org` (non-ASCII local part) and `a@bücher.de` (IDN domain) → "Enter a valid email address."; `""` and `"   "` → "Email is required.". Every address it accepts also passes `normalize_address` unchanged (the send-time check).
  - Contacts: dedupe compares lower-cased addresses on add and on update (excluding self): `mary@x.org` then `MARY@X.ORG` → 409; update keeps unchanged fields; a blank name is stored as `""`, and `ContactOut` returns it (and an old Streamlit `""` row) as `null`.
- `backend/tests/test_hymn_library.py`:
  - `create_hymn`:
    - title required; number 0 and 100000 → "Hymn number must be a whole number." (`field == "number"`); default hymnal = effective default (stored default honored; alphabetical fallback);
    - hymnal must exist; any valid code when the church has none, with `GG2013` as the default;
    - https-only link; blanks become NULL;
    - *amendment 2026-09-26:* `text_year` 1826 and `hymnal_count` 1322 are stored; `text_year` 0 and next year → "Year must be a whole number from 1 to {current year}." (`field == "text_year"`); `hymnal_count` -1 and 100001 → "Number of hymnals must be a whole number from 0 to 100000." (`field == "hymnal_count"`); omitted → NULL; a member who sets either fact gets `Forbidden("Only church admins can do this.")` and nothing is written, while a member's hymn with both omitted or null is created;
    - duplicate `(hymnal, number, lower title)` → 409 with the exact message, including the no-number variant.
  - `update_hymn`:
    - merges (omitted keeps; null clears number, refs, theme and link, and, *amendment 2026-09-26*, `text_year` and `hymnal_count`);
    - *amendment 2026-09-26:* a member's patch with `text_year` (a value or `null`) or `hymnal_count` gets `Forbidden("Only church admins can do this.")` and changes nothing; the same patch without them succeeds;
    - *amendment 2026-09-26:* a hand-entered `text_year` survives the backfill: with `hymnal_count` still NULL, run `backfill_hymn_facts` against a faked Hymnary response that gives another year; the count is filled and the hand-entered year is unchanged;
    - `audio_url` preserved;
    - title null or blank → "Hymn title is required.";
    - hymnal change validated;
    - duplicate excluding self.
  - `delete_hymn` 404.
  - `add_hymnal("PH1990")` inserts 605 on a fresh church, and a second call inserts 0.
  - Catalog source, with the setup order explicit (`repos.churches.create_church` seeds a new church from the catalog; the `make_church` fixture does not):
    - create church A with `make_church`, then seed `hymn_catalog` with 3 GG2013 rows → `list_sources(A)` shows GG2013 with `hymn_count` 3 and `present: false`;
    - then create church B with `repos.churches.create_church` → `list_sources(B)` shows GG2013 with `present: true`;
    - `add_hymnal(A, "GG2013")` inserts 3, and `present` becomes true for A.
  - `remove_hymnal`: deletes only this church's hymns in that code (another church with the same code is untouched); only hymnal → 409 "You can't remove your only hymnal."; effective default → 409 with its message; an unknown code → 404.
- `backend/tests/test_hymnal_sources.py`:
  - The seed file exists at `backend/seed/hymnals/PH1990.csv` and loads 605 rows.
  - `load_rows` of a BOM-prefixed CSV reads `number`.
  - Hymnary links are built as `https://hymnary.org/hymn/PH1990/{n}`.
  - `has_scripture_refs` is false for PH1990.
  - An unknown code raises `KeyError` from `rows_for(code, session=s)`.
  - `file_sources()` needs no database; `list_bundled(session=s)` merges file and catalog sources, and a file source wins over a catalog source with the same code.
- `backend/tests/test_email_contacts.py` is unchanged: `get_contacts_for_display` stays until slice 7.
- `backend/tests/test_hymns_repo.py` (extended): `import_hymns` idempotency is kept after the flush removal (`test_hymnals.py::test_import_hymns_is_idempotent_and_enriches` keeps passing); `patch_hymn` is cross-church safe (returns None).
- `backend/tests/test_import_hymnal_cli.py`: `main(["--church-id", id, "--hymnal", "PH1990"])` without `--csv` imports the bundled file; importing the module doesn't call `load_dotenv`.
- **ESV key move:**
  - `backend/tests/test_api_settings.py` (new, or the settings file an earlier slice created): `ESV_API_KEY="  k  "` → `esv_api_key == "k"`; unset or blank → `None` (with `get_settings.cache_clear()` around each case).
  - Slice 2's `test_scripture_fetcher.py`: the ESV gating and routing cases pass `esv_key=` instead of `monkeypatch.setenv("ESV_API_KEY", …)`, with the same expectations; with the variable **set** in the environment but `esv_key=None`, `available_translations` has no `esv` (proving the module no longer reads the environment); calling `available_translations()` with no argument raises `TypeError`.
  - Slice 2's `test_api_translations.py` and `test_api_church_profile.py` set the key through the settings dependency (`app.dependency_overrides[get_settings]`) instead of the environment; their expectations are unchanged.
  - An AST check in the same file (a narrow early copy of slice 7's `test_env_access.py`): `scripture_fetcher.py` contains no `os.getenv` or `os.environ`.
- **Malformed-contact hint:** 5b's `test_usecase_email.py` (extended): `MALFORMED_CONTACT_HINT == "An admin can fix it in Settings → Contacts."`, and a send whose selected contact has a stored address that fails `normalize_address` raises the `contact_ids` error whose message ends with "An admin can fix it in Settings → Contacts." and does not contain "current app".

**API tests** (`TestClient` + `jwt_helpers`; one file per area: `test_api_church_profile.py`, `test_api_liturgy_prompts.py`, `test_api_contacts_admin.py`, `test_api_hymns_admin.py`, `test_api_hymnals_admin.py`)
- **Happy paths:**
  - For every route: status, response model, and `X-Church-Id` required.
  - `PATCH /church` returns the full `ChurchProfileOut` with the new values, and a follow-up `GET /church` matches.
- **Role denials:**
  - A member gets 403 "Only church admins can do this." on `PATCH /church`, `PUT /church/liturgy-prompts`, `POST`/`PATCH`/`DELETE /contacts…`, `GET /hymnal-sources`, `POST /hymnals` and `DELETE /hymnals/{code}`.
  - A member gets **2xx** on `GET /church/liturgy-prompts` (`can_edit: false`) and on `POST`/`PATCH`/`DELETE /hymns…` without the hymn facts, and 403 "Only church admins can do this." on `POST`/`PATCH /hymns…` that set `text_year` or `hymnal_count` (*amendment 2026-09-26*). (If the owner answers Open question 2 with "admins only", `DELETE /hymns/{id}` moves to `require_admin` and this test moves to the 403 list above, together with the DOM test that members see no **Delete hymn**.)
- **Cross-church isolation** with `assert_church_isolated` for every route. A non-member gets 403. A member of A gets 404 when acting on church B's:
  - hymn id (PATCH, DELETE);
  - contact id (PATCH, DELETE).
  For `DELETE /hymnals/{code}`, assert that B's hymns with the same code are untouched. `PATCH /church` with `"church_id": "<B>"` in the body → 422 `invalid_request`, and B is unchanged.
- **Error contract:** code and exact message for every message in the API table, plus `fields` keys (`name`, `timezone`, `bible_translation`, `default_hymnal`, `email`, `title`, `number`, `hymnal`, `link`, `code`, `prompts.benediction`, and, *amendment 2026-09-26*, `text_year` and `hymnal_count`). **Omitted required fields** get the friendly message, not Pydantic's "Required.": `POST /hymns {}` → "Hymn title is required." (`fields.title`); `POST /contacts {"name": "Mary"}` → "Email is required." (`fields.email`); `POST /hymns {"title": "X", "number": 0}` → "Hymn number must be a whole number." (`fields.number`). Malformed path ids → 422. An unknown prompt key → 422 `invalid_request`. A soft-deleted church or a removed membership between guard and write → 403 with `details.reason == "no_church_access"`, and a demotion between guard and write → 403 "Only church admins can do this." with no `reason` (covered by the usecase tests above plus the `DomainError` → HTTP mapping from slice 1).
- **Prompt cleaning through the API** (`test_api_liturgy_prompts.py`; this replaces a 6a unit test, because `clean_prompt_overrides` is slice 4's): `PUT` with the Benediction default re-sent with `\r\n` line endings and surrounding spaces → that field comes back `override: null`, `customized: false`; a blank value → not stored; a changed value with `\r\n` → stored trimmed with `\n`; a following `GET` matches. This pins that `PUT` uses the same rule generation uses.
- **Ported `streamlit_tests` assertions** (F §5.1; inv §6):

  | Streamlit test | New test |
  |---|---|
  | `test_settings_profile_contacts.py::test_member_cannot_update_profile` | member `PATCH /church` → 403 |
  | `::test_member_cannot_add_or_delete_contacts` | member `POST /contacts`, `DELETE /contacts/{id}` → 403 |
  | `::test_admin_can_update_profile_and_add_contact` | owner `PATCH /church {name, timezone}` + `POST /contacts` → persisted |
  | `::test_member_can_add_hymn` | member `POST /hymns` → 201 and listed by `GET /hymns` |
  | `test_settings_prompts_translation.py::test_member_cannot_edit_prompts_or_translation` | member `PUT` prompts, `PUT {}` and `PATCH {bible_translation}` → 403 |
  | `::test_admin_prompt_save_drops_defaults_and_reset_clears` | `PUT` with the default system prompt + a changed benediction stores only the benediction; `PUT {}` → `{}` |
  | `::test_admin_translation_validated` | `PATCH {bible_translation: "kjv"}` → stored; `"not-a-translation"` → 422 |

  The ESV key move makes `available_translations()` require `esv_key`, so the frozen `submit_translation` (settings.py:165) raises `TypeError` on `main` and `::test_admin_translation_validated` breaks. Per F §2.3.7, `streamlit_tests/test_settings_prompts_translation.py` is **deleted in the same PR**; all three of its tests are ported above. The frozen Streamlit code is not edited (production runs from `streamlit-frozen`). `test_settings_profile_contacts.py` doesn't reach `available_translations` and stays until it breaks or slice 7 removes the folder.
- **Contract:** `test_openapi_contract.py` passes with the regenerated snapshot. `test_route_guards.py` passes with no allowlist change. `test_no_streamlit_in_core.py` covers the new modules through `api.main`.
- **Postgres (`@pytest.mark.postgres`):**
  - Two threads with a barrier: one runs `PATCH /church {bible_translation: "kjv"}`, the other `PUT /church/liturgy-prompts {benediction: "Go."}`. Both keys are present afterwards; repeat 20 times.
  - Concurrent `POST /hymnals {PH1990}` × 2 → exactly 605 PH1990 rows.
  - Two threads with a barrier each run `POST /contacts {email: "mary@x.org"}` (the second as `MARY@x.org`) → exactly one 201 and one 409, and one row; repeat 20 times. The same for two identical `POST /hymns`.
  - `POST /hymnals` for 605 rows finishes in under 10 s against the CI Postgres. This is a guard, not a benchmark.
  - *Amendment 2026-09-26:* four threads with a barrier run `PATCH /church {bible_translation}`, `PUT /church/liturgy-prompts`, `PATCH /rubric {prefer_before_year: 1900}` and `PUT /church/prayer-library` (one prayer). All four keys are present afterwards; repeat 20 times. Two concurrent `PATCH /rubric` calls on different checklists keep both overrides.

**Rubric (amendment 2026-09-26, PR #4)**
- PR #4's `backend/tests/test_api_rubric.py` keeps passing unchanged: a member reads the defaults; a non-member gets 403; a member's `PATCH` gets 403; owner and admin can `PATCH`; reset with `null`; a readable 422; a non-object body is rejected; edits stay in their church.
- `test_church_admin.py` additions for `update_rubric`:
  - each `service_rubric` message comes back as 422 `invalid_rubric` with that exact message and no `fields`, and nothing is written;
  - `customized` and `defaults` are accurate after a change and after a reset;
  - an admin demoted under the lock → `Forbidden("Only church admins can do this.")` and nothing is written;
  - a soft-deleted church or a removed member → `no_church_access`;
  - unknown settings keys (`liturgy_prompts`, `prayer_library`, `{"foo": 1}`) survive;
  - a stored non-dict `rubric` is treated as `{}`.
- PR #4's `test_church_settings.py` rubric cases are retargeted to `update_rubric` when `update_church_rubric` is deleted.
- `assert_church_isolated` on `GET` and `PATCH /rubric` (the 403 half; no path ids).
- `GET /rubric` includes `defaults` equal to `service_rubric.default_rubric()`.
- The OpenAPI snapshot shows the additive `defaults` field.

**Prayer library (amendment 2026-09-26, PR #7)** — every case in PR #7 §Testing, in `test_api_prayer_library.py` and `test_usecase_prayer_library.py`:
- guards: `assert_church_isolated` on all three routes (non-member 403, other church 404 where an id applies), and a member's `PUT` gets the role 403;
- every validation message with its exact `fields` key;
- `added_at` kept for known ids and new ids assigned;
- a missing or junk key reads as empty;
- the draft uses `FakeAI` (checking the prayers, their type labels and the no-quoting instruction), returns 422 with no prayers, maps each AI error to its status, and charges the `ai` bucket once;
- **draft input budget** (added 2026-09-26): 30 prayers of 6 000 characters give a prompt of at most 24 000 characters that includes every prayer's type label, in saved order, and returns 200, not 422; a library under the cap is sent uncut; `fit_prayers` cuts a prayer at its last sentence end inside its share, or at the share when the share holds no sentence end;
- the concurrent-save case in the Postgres block above.
- The writer-hook cases belong to slice 4.
- The role re-read under the lock (demoted admin → role 403, nothing written) is added, as for every 6a write.

### Frontend (Vitest 3)

- **Unit (`*.test.ts`):**
  - `profileFormFrom` + `diffProfile`:
    - no change → `{}`; trims; the benediction `""` is sent;
    - `bible_translation: null`, `effective_translation: "web"` → the form shows `web`; changing only the name → `{name}` (no `bible_translation`);
    - `default_hymnal: null`, `effective_hymnal: "GG2013"` → the form shows `GG2013`; a name-only change sends no `default_hymnal`;
    - stored `default_hymnal: "PH1990"` that the church no longer has → the form keeps `PH1990`; a name-only change doesn't send it; picking `GG2013` sends `{default_hymnal: "GG2013"}`;
    - no hymnals (`effective_hymnal: null`, stored null) → the hymnal value is `""` and is never sent.
  - `rebaseForm`: baseline name "X", a refetch brings "Y", the user edited only the benediction → the rebased form has name "Y", and `diffProfile(newBaseline, rebased)` contains `default_benediction` but not `name`. A field the user edited keeps the edit.
  - `hymnalItems`: adds "{code} (no longer in your hymnals)" only for a stored code that is missing.
  - `promptsPayload`: default-equal and blank dropped; whitespace-only difference dropped.
  - `parseHymnNumber`: `""` → null, `"12"` → 12, `"12a"`, `"0"`, `"100000"` → "invalid".
  - *Amendment 2026-09-26:* `parseTextYear`: `""` → null, `"1826"` → 1826, `"0"`, next year and `"18a"` → "invalid". `parseHymnalCount`: `""` → null, `"0"` → 0, `"1322"` → 1322, `"-1"` and `"100001"` → "invalid".
  - `hymnPatch`: `""` → null for the clearable fields (including a cleared year or count); unchanged fields omitted.
  - `looksLikeEmail`.
  - `benedictionIsShorthand`.
  - `leave-guard.ts`: `confirmLeave()` resolves true at once with no active guard.
  - `keys.ts` includes `hymnal-sources`.
- **DOM (`*.test.tsx`, `renderWithProviders` + `installFakeApi`):**
  - **ChurchProfilePage:**
    - A member sees the banner and disabled fields, with no Save.
    - An admin edits only the name → the request is `PATCH /church` with body `{name}` and header `X-Church-Id`; toast "Profile saved.". The fake profile has `bible_translation: null` and `default_hymnal: null`, so the test also proves untouched Selects send nothing.
    - A 422 with `fields.timezone` renders under Time zone and focuses it.
    - `timezone_valid: false` with `timezone: "Eastern"` shows "Eastern" in the field and "Timezone not recognized. Choose one from the list.".
    - A stored `default_hymnal` the church lacks shows "{code} (no longer in your hymnals)"; zero hymnals hide the field and show "Add a hymnal in Hymns to choose a default.".
    - A refetch while dirty (another admin renamed the church) updates the untouched name field and keeps the edited benediction.
    - A stored `esv` not in `/translations` shows "ESV (not available on this server)" and is not sent on save.
    - Typing "Halverson" shows the note.
    - An ErrorState with Retry appears on a 500.
  - **HymnsSettingsPage:**
    - Renders the count and rows (`—` for a null number).
    - Search sends `q` after the debounce and resets the offset; "Show more" requests `offset=50`.
    - Chips appear only with more than one hymnal.
    - Add → POST body, the dialog closes, and `invalidateQueries` is called with `["church", id, "hymns"]` and `["church", id, "hymnals"]` (spy).
    - Edit → PATCH with changed fields only; the edit dialog shows "Changes also appear in saved services that use this hymn.", the add dialog doesn't.
    - *Amendment 2026-09-26:* the dialog shows "Year the words were written" and "Number of hymnals (familiarity)" filled from the hymn; entering 1826 sends `{text_year: 1826}` only; clearing the count sends `{hymnal_count: null}`; a year after the current year shows the inline message and sends nothing; a member sees both fields read-only, and a member's edit never sends them.
    - Delete asks for confirmation, then DELETE.
    - A 409 message stays in the dialog.
    - Members don't see "Add a hymnal"; admins do.
    - AddHymnalDialog shows the PH1990 note and "Added" for present sources.
    - The Remove action is absent on the default row.
  - **LiturgyPromptsPage:**
    - The "Customized" badge appears when the text differs.
    - Reset to default restores the default text.
    - Save sends only customized keys.
    - A 422 `prompt_invalid` with `fields["prompts.benediction"]` expands and focuses that card.
    - Reset all confirms, then `PUT {prompts:{}}`.
    - A member sees read-only textareas with no footer.
    - The placeholder help and the brace sentence appear under "Section prompts", not in the system card; the system card shows "Placeholders aren't filled in here; this text is sent as written.".
    - **Leave guard:** with an edited card, clicking the settings nav's "Contacts" link opens "Discard unsaved changes?" and doesn't navigate; "Keep editing" keeps the text; "Discard changes" navigates (router spy). Calling `onSelectChurch` while dirty opens the same dialog. With no edits, the link navigates with no dialog.
  - **ContactsSettingsPage:**
    - A member sees the list without controls, plus the banner "Only admins can add or change contacts.". A contact with `name: null` shows only its email.
    - An admin adds a contact → the row appears and the fields clear.
    - A 409 shows inline.
    - Edit → PATCH.
    - Delete confirms.
    - Both empty-state variants.
  - **Role loss:** a 403 on `PATCH /church` from an admin form toasts, invalidates the profile, and does **not** call the church-fallback path. A 403 with `details.reason: "no_church_access"` on the same mutation **does** take the fallback.
  - **TimezoneCombobox** (slice 1's test file, extended): an out-of-list `value` renders selected; `warning` renders below; without `warning` slice 1's behavior is unchanged.
  - **EmailBulletinDialog** (5b's test file, extended): with no contacts, an admin sees **Manage contacts** linking to `/settings/contacts`; a member doesn't.
  - **SectionCard** (slice 4's test file, extended): a Benediction card with origin `default` renders the hint with "Settings" as a link to `/settings/church`, for an admin and for a member; other origins show no such link.
  - **Settings layout** (5b's test, updated): `/settings` now redirects to `/settings/church`; the nav starts Church, Hymns, Liturgy, Contacts, Account; the legacy note reads "People and invites are still managed in the current app for now.". *Amendment 2026-09-26:* the nav is Church, Hymns, Liturgy, **Prayers, Rubric**, Contacts, Account.
  - **RubricSettingsPage** (amendment 2026-09-26):
    - A member sees the banner and read-only points, with no footer, add, remove or reset controls.
    - An admin edits one point of the Benediction card → exactly one `PATCH /rubric` with body `{prayers: {benediction: [...]}}`; toast "Rubric saved.".
    - Editing a card back to its default text sends `{prayers: {benediction: null}}`.
    - Reset to default restores the default points unsaved, and the Customized badge follows the text.
    - Changing the year sends only `{prefer_before_year: 1900}` and invalidates `["church", id, "hymns"]` (spy). A year of 1499 or next year shows the inline message and disables Save.
    - Add a point is disabled at 12; Enter in a point adds a new point below; removing every point shows "Keep at least one point, or use Reset to default." and disables Save.
    - A 422 `invalid_rubric` shows the server message above the footer and keeps the edits.
    - Reset all confirms, then sends `null` for exactly the `customized` keys.
    - The Opening and Closing cards show the theme note.
    - The leave guard fires on navigation while dirty.
  - **PrayersSettingsPage** (amendment 2026-09-26): PR #7 §Testing's DOM cases: the happy path and the error state; a member's read-only view; "Use this draft" and "Keep mine"; the "Save your prayers first" rule; remove with confirm; a 422 field error. Plus the leave guard while dirty, and Cancel on the draft aborting its request.
  - `rubric.test.ts` / `prayers.test.ts` (unit, amendment 2026-09-26): `cleanPoints`, `rubricPatch` (unchanged → `{}`, equal to default → `null`, never `[]`), `yearError`, `checklistError`, and `prayersPayload` (keeps ids, new rows without an id).

### Manual checks (appended to `docs/manual-verification.md`; production Vercel URL; 375 px and desktop)

1. **As the owner:**
   - Change the time zone with "Use this device's time zone", then save.
   - Rename the church; the header switcher shows the new name.
   - Set translation KJV, then open `/builder/readings`: the passage caption shows KJV with no reload.
2. Set the default benediction to a full text. Start a new service: the Benediction card shows it. A card you typed earlier is unchanged.
3. Add PH1990:
   - the toast shows 605;
   - the builder hymn step shows the hymnal switcher;
   - make PH1990 the default and confirm the builder opens on it;
   - try removing it: blocked with the default message;
   - switch the default back and remove PH1990: the hymns are gone and saved services still show their hymns.
4. Edit a hymn title in Settings, then open the builder's hymn picker in the same tab: the new title shows with no reload.
5. Delete a hymn that is picked in the current draft: the builder shows "Not in your hymnal. Choose a replacement."
6. Prompts:
   - save a Benediction prompt with a stray `{`: the error is inline, nothing saved;
   - fix it and save; generate liturgy: the custom prompt is used;
   - Reset all.
7. Contacts: add, add a duplicate with different case (refused), edit, and delete (confirmed).
8. As a member (second Google account): the profile, prompts and contacts pages are read-only with the exact notices; adding and deleting a hymn works.
9. At 375 px: no horizontal scroll on all four pages; dialogs are full screen; the prompts footer clears the iOS home indicator.
10. **Streamlit smoke check** (F §6.3):
    - load the church in Streamlit;
    - its Settings shows the translation and prompts saved by the new app;
    - Streamlit's "Save prompts" leaves `default_benediction` and `default_hymnal` in place (verify with `GET /church`).
11. **Rubric** (amendment 2026-09-26):
    - As the owner, edit the Prayer of Confession checklist and save;
    - generate the Confession in the builder: the new point is followed (the prompt is DEBUG-only, so judge the text);
    - set "Prefer hymns written before" to 1900: the hymn picker labels hymns written in or after 1900 without a reload;
    - Reset all;
    - Streamlit (frozen) suggestions and liturgy follow the saved rubric too, because both apps read the same key;
    - as a member, the page is read-only.
12. **Prayers** (amendment 2026-09-26): PR #7's manual check at 375 px, plus: save three prayers of mixed types and a profile, then generate a Prayer of Confession in the builder with no reload.

---

## Acceptance criteria

1. `PATCH /church` updates any subset of name, timezone, default translation, default hymnal and default benediction in one transaction. An invalid field returns 422 with the exact message in `fields[<name>]` and writes nothing. *(test)*
2. A non-IANA timezone is rejected with "Unknown timezone."; a stored invalid timezone is shown with "Timezone not recognized. Choose one from the list." and survives saves that don't touch it. *(test)*
3. A stored translation that is unavailable on the server survives a profile save that doesn't change it. *(test)*
4. `default_benediction` is stored as typed (trimmed). `""` means no default and is returned as `""`; a church without the key still gets `"Halverson"` from `GET /church`. *(test)*
5. `default_hymnal` accepts only the church's hymnals. `effective_hymnal` (in `GET /hymnals` and `GET /church`) and the builder follow it. A null or stale stored default is never written by a save that doesn't change the hymnal field. *(test + manual 3)*
6. Concurrent `PATCH /church` and `PUT /church/liturgy-prompts` never lose a settings key, and unknown settings keys are preserved. *(Postgres test; F acceptance 18)*
7. Members can read prompts (`can_edit: false`) and contacts but get 403 "Only church admins can do this." on every admin route in the API table. *(test)*
8. Members can add and edit hymns (decision 5) and, pending Open question 2, delete them (Streamlit parity). Deletion requires a confirmation in the UI. *(test)*
9. Every church-scoped route in this slice passes `assert_church_isolated`: a non-member gets 403, and another church's hymn or contact id gets 404. `DELETE /hymnals/{code}` never touches another church. *(test)*
10. `PUT /church/liturgy-prompts` stores only non-blank values that differ from the defaults, using slice 4's `liturgy_prompts.clean_prompt_overrides` (no second implementation exists), rejects each malformed section template with 422 `prompt_invalid` naming the section and giving slice 4's reason, and `{prompts: {}}` resets to defaults. *(test)*
11. Contacts reject a missing or invalid email (5b's `normalize_address` rule, so every saved contact passes the send-time check) and case-insensitive duplicates with the exact messages, even under concurrent submits, and can be edited. *(test + Postgres test)*
12. Hymn create and edit validate the title, number, hymnal and https link, with the friendly messages even when a required field is omitted; PATCH preserves fields not sent (including `audio_url`); exact duplicates return 409. *(test)*
13. Every hymn is reachable in Settings through search and "Show more", including hymns without a number. *(DOM test + manual)*
14. Editing, adding or deleting a hymn, or adding or removing a hymnal, refreshes the builder's hymn picker without a page reload. *(DOM test + manual 4; F acceptance 18)*
15. Admins can list bundled hymnals (PH1990 from `backend/seed/hymnals/PH1990.csv`, plus catalog hymnals), add one idempotently (605 PH1990 hymns, then 0 on repeat), and remove a hymnal that isn't the only or the default one. *(test + manual 3)*
16. `data/hymnals/` no longer exists. The CSV ships under `backend/` and loads with or without a BOM. `import_hymnal.py` still works as a CLI. *(test)*
17. All four pages meet F §4.8: skeleton on first load, ErrorState with Retry, the exact empty states and read-only notices above, and no horizontal scroll at 375 px. Unsaved profile or prompt edits are protected by the leave guard, and a background refetch never turns an untouched field into a patch key. *(DOM test + manual 9)*
18. The OpenAPI snapshot and generated types are updated. The route-guard, contract and no-Streamlit tests pass. Every assertion from `test_settings_profile_contacts.py` and `test_settings_prompts_translation.py` has an API or usecase equivalent, and `test_settings_prompts_translation.py` is deleted in the same PR as the ESV key move. *(CI)*
19. After this slice ships, the frozen Streamlit app still loads the church, and its prompts and translation reflect saves made in the new app. *(manual 10)*
20. The hand-offs are done. From 5b: Settings opens on Church, the legacy note mentions only people and invites, an admin with no contacts sees **Manage contacts** in the email dialog, and a bulletin send with a malformed saved contact says "An admin can fix it in Settings → Contacts." From 4: the Benediction card's "Settings" hint links to `/settings/church`. *(DOM test + test)*
21. A write to a church soft-deleted after the guard ran, or by a caller whose membership was removed after the guard ran, returns 403 `no_church_access` and writes nothing. An admin demoted after the guard ran gets 403 "Only church admins can do this." (no `reason`) on every admin write and nothing is written; the role is always the one re-read under the church-row lock (6b's `lock_and_read_actor`). *(test)*
22. `ESV_API_KEY` is read only in `api/settings.py` and passed to `scripture_fetcher`; ESV gating, `GET /translations`, passages and the profile's `effective_translation` behave exactly as before. *(test)*
23. *(Amendment 2026-09-26, PR #4.)* `/settings/rubric` lets admins edit every hymn and prayer checklist and both preferences over the existing `GET`/`PATCH /rubric`. Members read it. It saves one sparse `PATCH`, and an item equal to its default is stored as not customized. Validation copy equals the `service_rubric` messages, and a server 422 `invalid_rubric` saves nothing. `PATCH /rubric` re-reads the role under the church-row lock, keeps PR #4's request, response and error shape (plus the additive `defaults`), and its tests from PR #4 still pass. A year change relabels the builder's hymns without a reload. *(test + DOM test + manual 11)*
24. *(Amendment 2026-09-26, PR #7.)* `/settings/prayers` sits right after Liturgy in `SETTINGS_SECTIONS`, followed by Rubric. `GET /church/prayer-library` (`require_church`), `PUT` (`require_admin`, full replace, `lock_and_read_actor`) and `POST …/voice-profile-draft` (`require_admin`, `ai` bucket cost 1, 75 s deadline, draft not stored) behave as PR #7 specifies. The library lives in `churches.settings["prayer_library"]` with no DDL, and concurrent settings writes never lose it. The voice-profile draft never returns 422 for length: 30 prayers of 6 000 characters are cut to fit 24 000 characters and every type label is sent. *(test + DOM test + manual 12)*
25. *(Amendment 2026-09-26; owner decision, index §6 question 23.)* Admins edit a hymn's "Year the words were written" and "Number of hymnals (familiarity)" in the hymn dialog; members see them read-only, and a member's request that sets either one gets the role 403. `POST`/`PATCH /hymns` accept `text_year` (1 to the current year, or null) and `hymnal_count` (0 to 100000, or null) with the exact messages, `HymnDetailOut` returns both, clearing a field stores NULL, and a hand-entered value survives the ops backfill. *(test + DOM test)*

---

## Risks and open questions

**Open questions (for the owner)**
1. **Removing a hymnal is new.** `DELETE /hymnals/{code}` is admin-only, refused for the only or default hymnal, and confirmed in the UI. It exists so a mistaken "Add a hymnal" (605 rows) can be undone. The owner approved *adding* bundled hymnals, not removing them. If the owner doesn't want removal, drop the route and the dialog; nothing else depends on them.
2. **May members delete hymns?** Decision 5 grants members "add/edit hymns" and says nothing about deleting them; inv §7 Q8 asked it explicitly. Streamlit lets any member delete any hymn (settings.py:303-306), so 6a keeps that as **parity**, now with a confirmation. The gap: admins can't remove the only or the default hymnal, but a member can empty a hymnal, or the whole library, one hymn at a time through `DELETE /hymns/{id}`. The builder then falls back to the next hymnal, or shows the empty-hymnal state. If the owner answers "admins only", change the `DELETE /hymns/{hymn_id}` guard to `require_admin`, hide **Delete hymn** for members, and flip the role tests (Testing → Role denials). Nothing else changes.
3. **Opening and closing theme keywords (amendment 2026-09-26; the rubric spec's known limit).** Slice 3 still gathers opening and closing candidates with the fixed theme keywords before the AI reads the church's checklist. If a church rewrites those checklists, the keywords may not match them. Default until answered: keep the keywords and show the note on the two cards (UX §6). The alternative, dropping the keyword pre-filter when a slot checklist is customized, is a slice 3 change that 6a doesn't need to know about.
4. ~~**Editing a hymn's year and familiarity (amendment 2026-09-26).**~~ **Answered: Yes (owner, 2026-09-26).** The rubric spec calls this "a slice 6 hymn-settings concern", and it is now in 6a, for admins: optional `text_year` and `hymnal_count` on `HymnIn`/`HymnPatchIn` (a member who sets either gets the role 403) and two optional fields in the hymn dialog, "Year the words were written" and "Number of hymnals (familiarity)", read-only for members (In scope, UX §2, API, Testing, acceptance 25). Clearing a field sets null. The ops backfill CLI still fills blanks only, so hand-entered values survive it.

**Risks**
1. **Cross-slice assumptions.** The benediction fallback must be key-presence, not truthiness (slice 4). `effective_hymnal` must follow the effective default rule and must match 6a's deletion guard (slice 3). Contacts must use exactly 5b's `normalize_address`, or a saved contact can fail every send (5b). Prompt cleaning must be slice 4's single `clean_prompt_overrides`, including its `\r\n` normalization, or `PUT` and generation can disagree on which overrides equal the default (slice 4). Every write must take the role from 6b's single `lock_and_read_actor`, not from the guard's snapshot (6b). The timezone check must be slice 1's exact `available_timezones()` membership, or `PATCH /church` and `timezone_valid` disagree (slices 1 and 2). Role 403s must not trigger the church fallback (slice 1). Each has a stated remedy under Assumed interfaces. The implementer checks them first and adjusts before writing 6a code.
2. **Hymn renames and recent-use exclusion.** `hymn_usage` stores `(number, title)` with no hymn id or hymnal (inv §1 D5). Renaming a hymn or changing its number means past usage no longer matches, so it may be suggested again inside the 12-week window. Accepted for now. A later fix would key usage by hymn id (a schema change after slice 7).
3. **Hymn edits change saved services.** 5a resolves an archived service's `hymn_id` to the hymn row's current title, number and hymnal, so renaming, renumbering or moving a hymn in Settings changes what past services show and what their regenerated Word documents print. The edit dialog says so ("Changes also appear in saved services that use this hymn."). Deleting a hymn does not have this effect: the service falls back to the snapshot saved with it. Accepted; it is usually what the user wants (a typo fix).
4. **Browser and server timezone lists can differ.** A zone the browser lists but Python's tzdata lacks returns 422 "Unknown timezone.". Mitigations: the `tzdata` package pinned in requirements, and canonical `Intl` ids.
5. **Import speed on the Supabase pooler.** Removing the per-row flush should make PH1990 a batched insert. If production still exceeds about 10 s, switch `import_hymns` to a single `insert(Hymn).values([...])` for new rows. Verify in manual check 3.
6. **Last write wins within one resource.** `PUT /church/liturgy-prompts` replaces all prompts, so two admins saving prompts at the same moment keep the later set. PATCH sends only changed fields, and a background refetch rebases untouched fields before the next save, so disjoint profile edits merge; for prompts the same rebase means a save after a refetch keeps the other admin's untouched cards. Two edits of the same field keep the later one. Accepted for a single-tester deployment. If it matters later, add `If-Match` on a settings version.
7. **Frozen Streamlit writes are unlocked** and can race an API settings, hymn or contact write (including creating a duplicate contact or hymn the API's locked check would refuse). Accepted per F §1.7 and §6.2. After 6a the legacy note sends the tester to Streamlit only for people and invites, and after 6b not at all. *Amendment 2026-09-26:* Streamlit's **settings** writes are locked since PR #4 (Data and migrations), so only its hymn, contact and profile-name writes remain unlocked.
8. **Rubric and prayers affect prompts in both apps (amendment 2026-09-26).** Frozen Streamlit reads the same `rubric` key, so an edit here changes its hymn suggestions and liturgy too. That is intended, and harmless because `merge_rubric` ignores bad values. It ignores `prayer_library`. Longer prompts from both features are measured in slice 4 (Risk 2 there; index open item 18).
