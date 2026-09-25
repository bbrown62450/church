# Slice 5b — Review step: Gmail connection + bulletin email — Design

**Status:** Draft  **Depends on:** ops (Streamlit freeze, catch-all error middleware), 1 (platform: errors, idempotency, guards, query client, UI kit, `/join`-style sign-in continuity), 2 (draft store, builder shell, `ratelimit.py`, `integrations/http.py`), 5a (`ServiceDraft`, document usecase, Review step page, `service_output.py`)  **Size:** M

**Inputs:** foundations spec `2026-09-25-migration-foundations-design.md` (cited as "F§n"), migration inventory `2026-09-25-streamlit-migration-inventory.md` (cited as "inv §n"), owner decisions 1-9.

---

## Goal

Let any church member connect their own Gmail account in the new app and email the bulletin copy of the service they are building, from their own mailbox, with:
- the Gmail OAuth return moved from the Streamlit root to the frontend page `/gmail/callback` (F§4.1, F§4.3), while Streamlit keeps working against the same `gmail_tokens` rows during the overlap;
- the attachment always rebuilt on the server from the posted draft (owner decision 4);
- multiple recipients in BCC with the sender in To, and an editable prefilled message (owner decision 9);
- no double sends (including after an uncertain outcome: a retry replays "check your Sent folder" instead of sending again), no raw Google error text, and a clear reconnect path when Google drops the grant.

5b also ships the Settings layout with `/settings/account` (F§7.2), and it ends with the **parity gate**, after which the tester moves to the new app (F§6.3, owner decision 7).

---

## Scope / Out of scope

### In scope

| Area | Items |
|---|---|
| Inventory | F8 (Gmail status, connect, disconnect), F9 (OAuth callback), F10 (email the bulletin copy), the Gmail parts of A3 (OAuth query cleanup, new-tab redirect) and A7 (email form not reset on church switch), §0 item 1 (Gmail code lost on a signed-out landing), the §3 coupling rows for `app.py:176-218, 334-336` and `google_oauth.py:190-201, 17-24, 129-136`, the §4 "OAuth flows that change shape" and "Gmail sending limits" risks, and row 5b of §5. |
| API | `GET /gmail-connection`, `POST /gmail-connection/auth-url`, `POST /gmail-connection`, `DELETE /gmail-connection`, `GET /contacts` (read only; moved here from 6 by inv §5), `POST /bulletin-emails`. |
| Owner decisions | 4 (email the bulletin, always regenerated), 5 (members may email), 9 (BCC with sender in To, editable prefilled message). |
| Foundations pieces (F§7.2) | Settings layout and `/settings/account`; `/gmail/callback`; required `Idempotency-Key` on `/bulletin-emails`; the `email` rate-limit bucket; the parity gate. |
| Ops | Register the new redirect URIs on the Google OAuth client; set Railway's `GOOGLE_*` variables; the Streamlit switchover banner after the gate. |

### Out of scope (and where it goes)

| Item | Slice |
|---|---|
| Contacts create/edit/delete (inv G4) and the Settings → Contacts page | 6a (validates with `email_addresses.normalize_address` from this slice, the only address validator; see hand-offs) |
| Settings sections Church, Hymns, Liturgy, Contacts; narrowing the "still in the current app" note | 6a (added to the layout built here) |
| Settings sections People, Danger zone; removing the "still in the current app" note | 6b |
| Word document content and variants, `POST /documents`, hymn usage recording | 5a (usage is recorded on Save, never on email — owner decision 9) |
| Gmail refresh-token encryption at rest | 7 (F§6.4; the frozen Streamlit reads plaintext) |
| Removing the Streamlit redirect URI from Google; rotating the Google OAuth client secret; deleting Streamlit docstring references; README Streamlit sections | 7 |
| Deleting `email_contacts.get_contacts_for_display` (dead, still covered by a test) | 7 (dead-code sweep, with its test assertion; 5b and 6a leave it alone) |
| Emailing the pastor's copy, CC, HTML email, per-church email templates | Not planned (Streamlit emails only the bulletin; not requested) |

### Traceability: every current behavior in scope

C = carried over, Ch = intentionally changed (see Behavior changes), M = moved to another slice, R = removed.

| # | Current behavior (source) | Disposition |
|---|---|---|
| 1 | Gmail controls render only for users with a church (app.py:345, inv F8) | C: Settings → Account and the Review step, both inside the church layout |
| 2 | Sidebar pops and shows `oauth_error` (app.py:203-204) | Ch: errors show on `/gmail/callback` |
| 3 | Not configured → "Per-user Gmail sending isn't configured on this deployment." (app.py:205-207) | C (same copy); Ch: the Review step no longer tells the user to connect |
| 4 | Connected → "Connected: {email}" + Disconnect deletes the row (app.py:208-212) | C; Ch: shows the Google address, disconnect also revokes the grant |
| 5 | Not connected → caption + "Connect your Gmail" link button; new tab; a state row per render (app.py:213-218) | Ch: same tab, one state per click |
| 6 | Scopes `openid`, `userinfo.email`, `gmail.send`; `access_type=offline`; `prompt=consent` (google_oauth.py:47-51, 137-146) | C; Ch: adds `login_hint` |
| 7 | State `token_urlsafe(32)`, 10-minute TTL, single use, deleted even when expired (google_oauth.py:149-187) | C; Ch: expired rows purged on each new state |
| 8 | Tokens are user-scoped, one row per user (models.py:202-211) | C |
| 9 | Callback detected at the app root by `should_handle_gmail_callback` (google_oauth.py:190-201, app.py:334-336) | Ch: dedicated `/gmail/callback` page; function deleted |
| 10 | Missing, expired or other user's state → error (app.py:183-188) | C (400 `gmail_state_invalid`); Ch: copy |
| 11 | "Sign in before connecting a Gmail account." (google_oauth.py:214-215) | R: unreachable; every API call has a verified user |
| 12 | Token endpoint failure → raw "Google API error {status}: {msg}" (google_oauth.py:228-229, 372-383) | Ch: typed errors, no Google text |
| 13 | "Google did not return an access token." | Ch: 502 `upstream_error` with new copy |
| 14 | "Could not read your email address from Google." | C |
| 15 | Account mismatch message; nothing stored (google_oauth.py:240-244) | C (+ the signed-in address in the message) |
| 16 | No refresh token and not connected → "Google did not return a refresh token…" (google_oauth.py:246-252) | C |
| 17 | Any other exception text → `oauth_error` (app.py:192-193) | Ch: generic 500 with a reference id |
| 18 | OAuth keys cleared from the URL, then rerun (app.py:194-195, ui_helpers.py:21-25) | Ch: `history.replaceState` on the callback page |
| 19 | 30 s timeout per Google call (google_oauth.py:58) | Ch: 15 s per call (F§1.8) |
| 20 | `?error=access_denied` ignored; orphan state row (inv F9) | Ch: handled; purged later |
| 21 | Email UI shown only after "Prepare bulletin copy" (app.py:1094-1096) | Ch: available whenever the date is valid; server rebuilds the file |
| 22 | Caption "Send the bulletin .docx and a friendly message via Gmail." (app.py:1097) | C (card copy) |
| 23 | "Sending as **{email}** (your connected Gmail)." / warning "Connect your Gmail in the sidebar…" (app.py:1098-1103) | Ch: "From: {google_email}", connect button in place |
| 24 | Recipients multiselect "Name <email>" (app.py:1104-1109) | Ch: checkbox list keyed by id; nameless contacts show the address only |
| 25 | "Additional emails (comma-separated)" (app.py:1110-1112) | C (commas; also semicolons and new lines) |
| 26 | Message textarea, empty (app.py:1113) | Ch: prefilled, editable |
| 27 | No recipients → "Please select at least one recipient or enter an email address." (app.py:1119-1120) | C (422) |
| 28 | Not connected → "Connect your Gmail in the sidebar first, then try again." (app.py:1121-1122) | C (409); Ch: copy without "sidebar" |
| 29 | Subject "Worship service — {date}" with `'%B %d, %Y'` (app.py:1124) | C exactly |
| 30 | Body = message or "Hi! Here’s the worship bulletin for this Sunday.", stripped (app.py:1125) | C; Ch: prefilled, and non-Sunday wording |
| 31 | Attachment `worship_{safe_date}.docx` (app.py:1126) | C name; Ch: docx MIME type instead of octet-stream |
| 32 | From only from the stored `google_email` (google_oauth.py:317-332) | C |
| 33 | All recipients in one To header (google_oauth.py:343) | Ch: BCC rule (decision 9) |
| 34 | Plain-text body (google_oauth.py:345) | C |
| 35 | "Email failed: {err}" / "Email sent to {n} recipient(s)." (app.py:1132-1135) | Ch: typed messages; "Email sent to N people" |
| 36 | Any 400/401 on token refresh deletes the connection (google_oauth.py:288-294) | Ch: only on `invalid_grant` (and a missing send scope) |
| 37 | Stale attachment, church-switch leakage, `KeyError` on stale labels, no validation or dedupe (inv F10, A7) | Ch: fixed |
| 38 | Only the bulletin copy can be emailed (inv F1) | C |
| 39 | Hymn usage recorded on Prepare, which preceded emailing (app.py:1002-1003) | M: 5a records usage on Save; emailing records nothing |
| 40 | `list_contacts` ordered by `created_at, name` (email_contacts.py:24-37) | C + id tie-break; blank (`""`, which Streamlit stores for a nameless contact, settings.py:82) and NULL names are returned as `null` and sort last (F§1.4) |
| 41 | Contacts add/delete in Settings (inv G4) | M: 6a |
| 42 | Settings caption "{church} — you are **{role}**." (inv G1) | C: Settings layout header (built here) |
| 43 | Code/state lost when the callback lands signed out (inv §0 item 1) | Ch: "Gmail connection didn't finish. Try connecting again." |

### Dependencies and hand-offs (exact interfaces assumed)

| From | Interface this slice uses |
|---|---|
| ops | Streamlit production runs from `streamlit-frozen` (F§6.1), so `google_oauth.py` can change on `main` without shims. If the F§6.1 contingency is in force instead, 5b adds `google_oauth_legacy.py` (see Streamlit coupling removed). `UnhandledErrorMiddleware` inside CORS (F§2.5). |
| 1 | `domain_errors.py` (`InvalidInput`, `NotFound`, `Conflict`, `Rejected`, `NotConfigured`, `UpstreamError`, `UpstreamTimeout`, each with `code`, `field`, `details`; and `RateLimited(message, *, retry_after_seconds)`, 429 `rate_limited`, whose handler always sets the `Retry-After` header and `details.retry_after_seconds`); error body with `fields`/`details`/`request_id` (F§1.5). `api/idempotency.py`: `idempotency_key(required=True)` → 422 `invalid_request` "Missing Idempotency-Key header." (slice 1 builds it for 5b), and `run_idempotent(...)`, which stores 2xx and `DomainError` 4xx responses **except `RateLimited`, which it never stores**, stores no 5xx, and drops the entry and re-raises on any other exception. **5b adds** an optional `store_error: Callable[[DomainError], bool] \| None = None` argument: a 5xx `DomainError` for which it returns True is stored too (used for uncertain sends, §Errors). `test_route_guards.py` `USER_SCOPED` allowlist and `api_helpers.assert_church_isolated`. Frontend: `useApi()` (`api.user`, `api.church`), `useMe()`, `useChurch()` → `{id, name, role}`, `lib/storage.ts` session/local accessors, `lib/urls.ts` `safeInternalPath` and `safeHttpsUrl`, UI kit (`PendingButton`, `ErrorState`, `EmptyState`, `ConfirmDialog`, `PageHeader`, `touch` button size), `renderWithProviders`, `installFakeApi`, shared sign-out. |
| 2 | `ratelimit.consume(bucket, *, user_id, church_id=None, cost=1)` (raises slice 1's `domain_errors.RateLimited`: 429 `rate_limited` with `Retry-After` and `details.retry_after_seconds`; there is no second 429 mechanism and `ApiError` gains no `headers`) and bucket config in `ratelimit.py`; `integrations/http.py` shared `httpx.Client` with a per-call `timeout`; `respx` in dev requirements. Frontend: `useDraft()` → `{draft}`; `lib/draft/status.ts` (per-step status, used for the "still missing" line); `lib/draft/fingerprint.ts` `fingerprint(value)` and the dirty rule (F§4.6); `lib/dates.ts` (`parseIsoDate`, `formatServiceDate`). |
| 5a | The names in 5a's "Hand-offs to 5b" list, exactly. `api.schemas.ServiceDraft` and `ServiceDraft.to_input() -> usecases.archive.ServiceInput` (with `service_date: datetime.date`); usecases never import `api/*`, so the route converts and `send_bulletin_email` takes `data: ServiceInput`. `usecases.documents.build_document(church_id: UUID, data: ServiceInput, variant: Literal["bulletin","pastor"]) -> DocumentResult(content: bytes, filename: str)` (bulletin includes the sermon title, decision 4). It runs `clean_input` (raises `InvalidInput("Give each custom element a label.", field="custom_elements.<i>.label")`) and `resolve_hymn_refs` (raises `NotFound("A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.", details={"field": "hymns.<slot>.hymn_id"})`, slice 4's wording); 5b lets both propagate. `service_output.service_date_display(d: datetime.date) -> str` (`'%B %d, %Y'`, zero-padded day, locale-independent), the **only** date-display function; `display_date(date_iso)` does not exist. `service_output.DOCX_MIME`, which 5b imports and does not define again. 5a does **not** define `bulletin_email_subject`; 5b owns it (§`service_output.py` additions). Frontend: `draftToServicePayload(draft)` (one argument) in `lib/draft/mapping.ts`, `docxFilename(variant, dateIso)` in `lib/download.ts`, and the Review page's card 5, `src/components/builder/review/email-slot.tsx`, whose placeholder contents 5b replaces with `<EmailBulletinCard />`. The contract is "bytes + filename for the bulletin variant built from the posted draft, reading only the active church's data". |
| 6a (hand-off) | **One address validator.** `POST`/`PATCH /contacts` validate with `email_addresses.normalize_address` (mapping `InvalidAddress` to 6a's own message "Enter a valid email address.") and store what it returns; 6a does **not** add `email-validator`. 6a's contacts API tests assert against the shared fixture `backend/tests/fixtures/shared/email_addresses.json`, like 5b's. Also: contact mutations invalidate `["church", id, "contacts"]`; inserts Church, Hymns, Liturgy, Contacts **before** Account in `SETTINGS_SECTIONS` (so `/settings` then redirects to `/settings/church`, as the F§4.1 route map says); changes the `LegacySettingsNote` text to "People and invites are still managed in the current app for now."; swaps the malformed-contact hint `MALFORMED_CONTACT_HINT` in `usecases/email.py` from "An admin can remove it and add it again in the current app's Settings." to "An admin can fix it in Settings → Contacts.", with a test asserting the new text; adds the admin-only "Manage contacts" link in the email dialog's empty state. 6a leaves `get_contacts_for_display` alone (slice 7 deletes it). |
| 6b (hand-off) | Inserts People before Account and appends Danger zone. Final `SETTINGS_SECTIONS` order: **Church, Hymns, Liturgy, Contacts, People, Account, Danger zone** (as the 6a and 6b specs list it). Removes the `LegacySettingsNote`. |
| 7 (hand-off) | Token encryption touches only `google_oauth.get_connection` / `save_user_token` / `delete_connection` (the only token readers and writers after this slice). Remove the Streamlit redirect URI from Google. **Rotate the Google OAuth client secret** after the Streamlit app is deleted (it lived in Streamlit Cloud's secrets and, since this slice, in Railway), then update Railway's `GOOGLE_CLIENT_SECRET`; rotating the secret keeps existing refresh tokens valid, so the tester stays connected. Delete `google_oauth_legacy.py` if the F§6.1 contingency created it. Delete the dead `email_contacts.get_contacts_for_display` and its assertion in `test_email_contacts.py`. Its backend copy check fails on "current app" in user-facing strings under `backend/**/*.py` (or its 7-B copy sweep lists `MALFORMED_CONTACT_HINT`), so the hint can never point admins to the retired Streamlit app even if 6a's swap were missed. |

---

## User experience

### Where things live

| Place | What 5b adds |
|---|---|
| Builder step 4 "Review & send" (`/builder/review`) | The **Email the bulletin** card (5a's card 5, `email-slot.tsx`, between the Word documents card and the Order of worship card), and the email dialog |
| Header nav | The **Settings** item (Builder · Services · Settings) and the account menu's "Settings" link, both to `/settings` |
| `/settings/account` | Account card (identity, Log out) and Gmail card (connect, status, disconnect) |
| `/gmail/callback` | The page Google returns to; a minimal centered card, outside the church shell |

### Settings layout (5b builds it; 6a/6b fill it)

- `PageHeader` "Settings" with the caption "{church name} — you’re {a member | an admin | the owner}." (inv G1).
- Section navigation from `SETTINGS_SECTIONS` in `src/components/settings/sections.ts`, each `{id, href, label}`:
  - below `md`: a horizontally scrollable row of links inside the header (`overflow-x-auto`, no page-level horizontal scroll), current item underlined;
  - `md` and wider: a left column (`grid-cols-[12rem_minmax(0,1fr)] gap-8`).
- 5b ships one section: `{id: "account", href: "/settings/account", label: "Account"}`. `/settings` redirects (`router.replace`) to `SETTINGS_SECTIONS[0].href`. The final order after 6a and 6b is Church, Hymns, Liturgy, Contacts, People, Account, Danger zone.
- Under the nav, `LegacySettingsNote` (muted text): "Church details, hymns, liturgy prompts, contacts and people are still managed in the current app for now." If `NEXT_PUBLIC_LEGACY_APP_URL` passes `safeHttpsUrl`, the words "the current app" link to it (new tab). 6a narrows the text to people and invites; 6b deletes the note.

### `/settings/account` (mobile first; single column, `max-w-2xl`)

**Account card**
- Avatar (only when `me.user.picture` passes `safeHttpsUrl`; otherwise initials), name, email.
- "Signed in with Google."
- `Log out` (touch size, outline) → the shared sign-out (F§4.2).

**Gmail card** (title "Gmail"), states from `GET /gmail-connection`:

| State | Content |
|---|---|
| Loading | Two skeleton lines |
| Query error | `ErrorState` "Couldn't check your Gmail connection." + Retry |
| `configured: false` | "Per-user Gmail sending isn't configured on this deployment." No button. |
| Not connected | "Connect your Gmail to email bulletins from your own account. The app can only send email for you; it can't read your mail." Primary `Connect Gmail` (touch size). |
| Connected | "Connected as **{google_email}**." / "Works in all your churches." Outline `Disconnect`. |

- **Connect** (see flow A). While the auth-url request runs, the button shows "Opening Google…".
- **Disconnect**: no confirmation (reconnecting is one click). `PendingButton` "Disconnecting…"; on success the card shows the Not connected state; no toast (the result is visible). A failure toasts the server message.

### Review step: "Email the bulletin" card

This is 5a's card 5 (`email-slot.tsx`, between the Word documents card and the Order of worship card); 5b replaces its placeholder. Full width on mobile.

| State | Content |
|---|---|
| Loading | Skeleton line + disabled button |
| Status query error | Inline `ErrorState` "Couldn't check your Gmail connection." + Retry |
| `configured: false` | "Emailing isn't set up on this deployment." No button. |
| Not connected | "Connect your Gmail to email the bulletin copy from your own account." `Connect Gmail` (flow B). |
| Connected, date invalid | "Sends the bulletin copy (.docx) from {google_email}." `Email bulletin…` disabled, helper "Choose a valid service date first." (F D9) |
| Connected, date valid | "Sends the bulletin copy (.docx) from {google_email}." `Email bulletin…` → opens the dialog |

The button is never disabled because the service is incomplete or unsaved (F D9); the dialog says so instead.

### Email dialog

Base UI `Dialog`, controlled. Below `md` it fills the screen (`h-dvh`, no radius) with a scrolling body and a sticky footer (`pb-[env(safe-area-inset-bottom)]`); at `md`+ it is centered, `max-w-lg`. The (church) layout's keyed remount closes it on church switch.

```
┌───────────────────────────────────────┐
│ Email the bulletin                  ✕ │
├───────────────────────────────────────┤
│ From  bob@gmail.com                   │
│                                       │
│ To                                    │
│ [✓] Mary Jones                        │
│     mary@firstpres.org                │
│ [ ] office@firstpres.org              │
│                                       │
│ Other addresses                       │
│ [ organist@example.com              ] │
│ Separate addresses with commas.       │
│                                       │
│ Recipients won’t see each other’s     │
│ addresses (sent as BCC).              │
│                                       │
│ Subject  Worship service — October    │
│          04, 2026                     │
│ Attachment  worship_October_04_2026   │
│             .docx (bulletin copy)     │
│                                       │
│ Message                               │
│ [ Hi! Here’s the worship bulletin   ] │
│ [ for this Sunday.                  ] │
│                                       │
│ Still missing: Response hymn.         │
│ Not saved to the archive yet. The     │
│ attachment uses the service as it is  │
│ on screen now.                        │
├───────────────────────────────────────┤
│ [ Cancel ]        [ Send to 2 people ]│
└───────────────────────────────────────┘
```

Contents, top to bottom:
1. **From**: `google_email`.
2. **To**: one checkbox row per contact (≥ 44 px tall). Name in normal weight and the address muted below; a contact with no name (`name: null`; the API already maps blank names to null) shows only the address. Contacts load with `useContacts()` (prefetched when the Review page mounts).
   - Loading: three skeleton rows.
   - Error: inline `ErrorState` "Couldn't load your contacts." + Retry; "Other addresses" still works.
   - Empty: "No saved contacts yet — type addresses below." (6a adds an admin-only "Manage contacts" link here.)
   - Preselection: contacts selected in this user's last successful send in this church (`wsb:emailPrefs:{userId}:{churchId}`), if they still exist.
3. **Other addresses**: `<input type="text" inputMode="email" autoCapitalize="none" autoCorrect="off" spellCheck={false}>`, class `text-base md:text-sm`, placeholder "name@example.com", helper "Separate addresses with commas." Parsed with `parseAddressList` (split on `,` `;` and new lines, trim, take the part inside `<…>` when present, drop empties). Server field errors show under this input.
4. **BCC note**, only when the de-duplicated recipient count is ≥ 2: "Recipients won’t see each other’s addresses (sent as BCC)."
5. **Subject** (read only): `bulletinEmailSubject(date_iso)`, for example "Worship service — October 04, 2026".
6. **Attachment** (read only): "{docxFilename('bulletin', date_iso)} (bulletin copy)".
7. **Message**: textarea, 4 rows, label "Message", `maxLength={5000}` (the server limit), prefilled with `defaultBulletinMessage(date_iso)`:
   - Sunday: "Hi! Here’s the worship bulletin for this Sunday."
   - any other day: "Hi! Here’s the worship bulletin for {Weekday}, {Month} {D}." (for example "…for Wednesday, February 10." for Ash Wednesday 2027-02-10)
   - The user can edit or clear it; if it is blank at send time the server uses the same default (parity with app.py:1125).
8. **Notes** (muted, non-blocking):
   - "Still missing: {items}." from the step status functions, when any step is incomplete (for example "Response hymn, 2 liturgy sections").
   - "Not saved to the archive yet. The attachment uses the service as it is on screen now." when the draft is dirty.
9. **Footer**: `Cancel` and the primary `PendingButton`:
   - label "Send to {n} {person|people}", where n = de-duplicated (case-insensitive) count of selected contact addresses plus parsed other addresses;
   - n = 0 → label "Send", disabled, helper "Choose at least one recipient.";
   - n > 50 → disabled, helper "You can email at most 50 people at once." (the server's message for the same rule);
   - pending label "Sending…"; after 8 s the line "Still working — this can take up to a minute." (F§1.8). There is **no Cancel during sending**: abandoning the wait would not stop Gmail.

Form state (checked ids, other-addresses text, message) lives in the Review page, not the dialog, so closing and reopening keeps it until a successful send or leaving the page.

### Send outcomes (dialog)

The dialog handles these errors inline (an `aria-live` region at the top of the body or under the field) and does not also toast.

| Outcome | What the user sees | Client action |
|---|---|---|
| 200 | Dialog closes; toast "Email sent to {n} {person\|people}." | Save the selected contact ids to `wsb:emailPrefs`; reset the message to the prefill |
| 422 with `fields` | Each field message goes where `fieldTarget(key)` (`lib/email.ts`) puts it, and the first such control is focused: `additional_emails` and `additional_emails.<i>` → under **Other addresses**; `message` → under **Message**; `recipients`, `contact_ids`, `contact_ids.<i>` → under the **To** group; any other key (for example `custom_elements.<i>.label` or `service.*`) → the `aria-live` message at the top of the dialog | — |
| 404 `not_found`, `details.field == "contact_ids"` | "One of the selected contacts no longer exists. Refresh the list and try again." (under **To**) | Invalidate contacts; drop unknown ids from the selection |
| 404 `not_found`, `details.field` starts with `hymns.` | "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step." (the server message) at the top, with the link **Go to Hymns** (closes the dialog, navigates to `/builder/hymns`), as 5a's save card does | — |
| 404 `not_found`, any other or no `details.field` | Server message at the top | — |
| 409 `gmail_not_connected` | "Connect your Gmail first, then try again." + `Connect Gmail` | Invalidate `["gmail-connection"]` |
| 502 `gmail_send_failed`, `details.disconnected: true` | Server message + `Reconnect Gmail` | Invalidate `["gmail-connection"]` |
| 502 or 504 with `details.send_uncertain: true` | Server message ("…may already have been sent. Check your Gmail Sent folder before sending again.") + outline button **Send again anyway** | Keep the key, so Send with nothing changed replays this same answer; **Send again anyway** calls `tracker.rotate()` and sends with a new key (the user's deliberate choice after checking) |
| Other 502 `gmail_send_failed` | Server message (it says nothing was sent) | — |
| 503 `gmail_not_configured` | Server message; Send disabled | Invalidate `["gmail-connection"]` |
| 504 `upstream_timeout` without `send_uncertain` | Server message ("…Nothing was sent — try again.") | — |
| Client `network_error` / `timeout` | "We lost the connection before Gmail confirmed, so the email may already have been sent. Check your Gmail Sent folder before sending again." | Keep the same Idempotency-Key: Send with nothing changed gets the first attempt's stored answer (sent, or "check your Sent folder") instead of sending again; only an attempt that stored nothing (so sent nothing) runs again (§Frontend) |
| 429 `rate_limited` | "Too many requests — try again in {N} s." (F§1.8 copy) | — |
| 500 | "Something went wrong. (Ref: {8 chars})" | — |

`Connect Gmail` / `Reconnect Gmail` inside the dialog store the dialog's form state in `sessionStorage["wsb:reopenEmailDialog"]` as `{church_id, contact_ids, other_addresses, message}` before leaving (flow B).

### Flow A — connect from Settings

1. Tap `Connect Gmail` → `POST /gmail-connection/auth-url`.
2. The client checks the URL starts with `https://accounts.google.com/` (else toasts "Something went wrong." and stops), stores `sessionStorage["wsb:gmailReturnTo"] = "/settings/account"`, and calls `window.location.assign(auth_url)` in the **same tab**. The draft is already in localStorage and flushes on `pagehide` (F§4.6).
3. Google shows its account chooser, pre-selecting the signed-in address (`login_hint`), then the consent screen.
4. Google redirects to `/gmail/callback` (flow C). On success the user is back on `/settings/account` with the toast "Gmail connected".

### Flow B — connect from the Review step

Same as A, with `wsb:gmailReturnTo = "/builder/review"` and `wsb:reopenEmailDialog` set (from the card: `{church_id}` only; from inside the dialog: the full form state). On return, the Review page reads `wsb:reopenEmailDialog` on mount but decides only once `useGmailConnection()` has **settled**: on success with `connected: true` and `church_id` equal to the active church, it reopens the dialog with that state; in every case it then clears the key (an error or "not connected", for example after a cancel, clears it without reopening). The callback page seeds the status with `setQueryData` (flow C) and returns with a client-side `router.replace`, so the status is normally already there.

### Flow C — `/gmail/callback`

A client component in `(signed-in)`, outside `(church)` (Gmail is user-scoped). The page state starts as `reading` (renders the neutral "Connecting your Gmail…" card, never "didn't finish"). In an effect (not `useSearchParams`, which re-renders after the URL is cleaned, and not during render, which would break SSR/hydration):
1. If `paramsRef.current` is null, parse `window.location.search` into it (`{code, state, error}`) — **before** touching the URL. Under React StrictMode the effect runs twice but the ref survives, so the second run reuses the first parse instead of reading the already-cleaned URL.
2. Call `history.replaceState(null, "", "/gmail/callback")` so the code and state leave the address bar and history (a no-op the second time).
3. Derive the page state from `paramsRef.current` only.

`returnTo` = `safeInternalPath(sessionStorage["wsb:gmailReturnTo"]) ?? "/settings/account"`.

| URL had | Page shows | Buttons / navigation |
|---|---|---|
| `error=access_denied` | Toast "Gmail connection was cancelled." | `router.replace(returnTo)` immediately |
| another `error=` value | "Google couldn't connect your Gmail." (the error value is never echoed) | `Try again` (restarts flow A/B with the same `returnTo`), `Go back` |
| `code` and `state` | "Connecting your Gmail…" spinner; after 8 s "Still working — this can take up to a minute." Then `POST /gmail-connection` (client timeout 40 s). | — |
| → 200 | Toast "Gmail connected" | `queryClient.setQueryData(["gmail-connection"], response)` (the POST returns `GmailConnectionOut`), clear `wsb:gmailReturnTo`, `router.replace(returnTo)` |
| → error | The server message (from the table in §API) | `Try again`, `Go back`; for `gmail_not_configured` only `Go back` |
| neither (for example a signed-out landing lost the query, inv §0 item 1) | "Gmail connection didn't finish. Try connecting again." | `Try again`, `Go back` |

The POST runs **exactly once per state**, including under React StrictMode's double effect: `connectGmailOnce(api, {code, state})` in `lib/gmail.ts` keeps a module-level `Map<state, Promise<GmailConnectionOut>>` and returns the existing promise for a state already submitted. Each effect run awaits that shared promise and ignores the result only if its own cleanup has run, so the surviving run always receives the outcome (a per-run "cancelled" flag alone would drop it). A browser reload after success finds no query (it was replaced) and shows the "didn't finish" card; the connection itself stays connected.

**Supabase must not read these parameters.** Google's `code`, `state` and `error` use the same names as Supabase's own callbacks, and the browser Supabase client (`createBrowserClient`, `detectSessionInUrl` defaulting to true) would treat `?error=` as an implicit-grant callback, and `?code=` plus a leftover code verifier from an abandoned sign-in as a PKCE callback, POSTing the Gmail code to Supabase. 5b sets `auth: { detectSessionInUrl: false }` in `src/lib/supabase/client.ts` (or wherever slice 1 moved the browser client). Nothing relies on browser-side detection: the Supabase code exchange already happens on the server in `/auth/callback/route.ts`.

For a signed-out landing: `proxy.ts` sends the user to `/login?next=/gmail/callback` (path only, F§4.2). 5b adds `/gmail/callback` to `safeInternalPath`'s allowed prefixes so the user returns here and sees "didn't finish" instead of silently landing on the builder.

### Flow D — Google revoked the grant (for example weekly expiry, or removal at myaccount.google.com)

The next send returns 502 `gmail_send_failed` with `details.disconnected: true` and the message "Your Gmail connection has expired or was removed. Reconnect Gmail and try again." The server has already deleted the stored token (only if it is still the token that failed, so a reconnect made meanwhile in either app survives), so the Gmail card and Settings show "Not connected". `Reconnect Gmail` runs flow B and reopens the dialog with the form intact.

---

## API

Conventions follow F§1: snake_case JSON, `extra="forbid"` request models, `{"items": [...]}` for lists, uniform error body with `request_id`, typed ids. All routes are plain `def` (blocking I/O).

| Method | Path | Guard | Request | Response | Errors (status `code`) |
|---|---|---|---|---|---|
| GET | `/gmail-connection` | user | – | 200 `GmailConnectionOut` | 401 `unauthenticated` |
| POST | `/gmail-connection/auth-url` | user | no body | 200 `{auth_url: str}` | 401; 503 `gmail_not_configured` |
| POST | `/gmail-connection` | user | `GmailConnectIn` `{code, state}` | 200 `GmailConnectionOut` (`connected: true`) | 401; 422 `invalid_request`; 400 `gmail_state_invalid`; 400 `gmail_connect_failed`; 502 `upstream_error`; 503 `gmail_not_configured`; 504 `upstream_timeout` |
| DELETE | `/gmail-connection` | user | – | 200 `GmailConnectionOut` (`connected: false`, `google_email: null`) | 401 |
| GET | `/contacts` | church | `X-Church-Id` | 200 `{items: ContactOut[]}` | 401; 403 `forbidden` |
| POST | `/bulletin-emails` | church | `X-Church-Id`; **`Idempotency-Key` (required)**; body `BulletinEmailIn` | 200 `{sent: true, recipient_count: int}` | 401; 403; 404 `not_found` (`details.field`: `contact_ids` or `hymns.<slot>.hymn_id`); 409 `gmail_not_connected`; 422 `invalid_request` (with `fields`, including 5a's `custom_elements.<i>.label`), `idempotency_mismatch`; 429 `rate_limited`; 502 `gmail_send_failed` (`details.disconnected`, `details.send_uncertain`); 503 `gmail_not_configured`; 504 `upstream_timeout` (`details.send_uncertain` when the send may have gone out) |

`X-Church-Id` is ignored on the four `/gmail-connection` routes, which go on the `USER_SCOPED` allowlist in `test_route_guards.py`. Members may send (owner decision 5), so `/bulletin-emails` uses `require_church`, not `require_admin`.

### Schemas

```python
# backend/api/routes/gmail.py
class GmailConnectionOut(BaseModel):
    configured: bool
    connected: bool
    google_email: str | None          # the connected Google address; null when not connected

class GmailAuthUrlOut(BaseModel):
    auth_url: str

class GmailConnectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(max_length=2048)
    state: str = Field(max_length=256)

# backend/api/routes/contacts.py  (6a adds POST/DELETE to this module)
class ContactOut(BaseModel):
    id: uuid.UUID
    name: str | None                  # null when the stored name is NULL or blank after trim
    email: str                        # (Streamlit stores "" for a nameless contact, settings.py:82)

class ContactList(BaseModel):
    items: list[ContactOut]

# backend/api/routes/bulletin_emails.py
class BulletinEmailIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: ServiceDraft                                   # api.schemas (5a)
    # List caps are a size guard only (200). The 50-recipient rule is checked after
    # de-duplication in the usecase, so it produces the friendly `recipients` message.
    contact_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    additional_emails: list[Annotated[str, StringConstraints(max_length=320)]] = Field(
        default_factory=list, max_length=200)
    message: str | None = Field(default=None, max_length=5000)

class BulletinEmailOut(BaseModel):
    sent: Literal[True]
    recipient_count: int
```

`GET /contacts` order: `created_at ASC, nullif(trim(name), '') ASC NULLS LAST, id ASC` (F§1.4), so blank names sort with NULL ones. A NULL or blank name is returned as `null`. No paging (small bounded list).

### Errors: `POST /gmail-connection`

Checks run in this order; nothing is stored unless every check passes.

| Condition | Status `code` | Message |
|---|---|---|
| Not configured | 503 `gmail_not_configured` | "Per-user Gmail sending isn't configured on this deployment." |
| State blank, unknown, expired, already used, or issued to another user | 400 `gmail_state_invalid` | "This Gmail connection request expired or was already used. Try connecting again." |
| Code blank, or Google `invalid_grant` on the code exchange (reused or expired code) | 400 `gmail_connect_failed` | "That Google approval has expired or was already used. Try connecting again." |
| Google `invalid_client`, `unauthorized_client` or `redirect_uri_mismatch` (our configuration) | 503 `gmail_not_configured` | "Gmail sending isn't set up correctly on this deployment." (logged at ERROR with Google's error code) |
| Token response without `access_token` | 502 `upstream_error` | "Google returned an incomplete response. Try connecting again." |
| The token response has a `scope` field and `gmail.send` is not in it (granular consent unticked). A missing `scope` means the requested scopes were granted (RFC 6749 §5.1), so it passes; the send-time `insufficientPermissions` path still catches a missing grant. | 400 `gmail_connect_failed` | "Google didn't give permission to send email. Try again and allow “Send email on your behalf”." |
| userinfo failed or returned no email | 400 `gmail_connect_failed` | "Could not read your email address from Google." |
| Google address ≠ signed-in address (case-insensitive) | 400 `gmail_connect_failed` | "That Google account doesn't match your signed-in email ({email}). Connect the Gmail account you're logged in with." |
| No refresh token and no existing connection | 400 `gmail_connect_failed` | "Google did not return a refresh token. Remove this app's access at https://myaccount.google.com/permissions and connect again." |
| Google 5xx or network error | 502 `upstream_error` | "Couldn't reach Google. Try connecting again in a minute." |
| Google timeout (15 s per call) | 504 `upstream_timeout` | "Google took too long to respond. Try connecting again." |

No refresh token **with** an existing connection keeps the stored token and returns 200 (parity with google_oauth.py:246-248).

### Errors: `POST /bulletin-emails`

Checks run in the order below, which is the order FastAPI and the code actually execute them: FastAPI resolves the route's dependencies in declaration order and raises body-validation errors only after all of them (a body that isn't JSON at all is a 422 before everything, a FastAPI detail); `run_idempotent` runs next; the usecase checks recipients before the connection (parity with app.py:1119-1122). Nothing is sent unless every check before "Send" passes. **Stored** says whether `run_idempotent` keeps the response for a retry with the same key (2xx and `DomainError` 4xx per slice 1, except `RateLimited`, which slice 1 never stores; plus the uncertain-send 5xx rows via `store_error`).

| # | Condition | Status `code` | Message (`fields` key or `details`) | Stored |
|---|---|---|---|---|
| 1 | Not signed in / not a member of the church | 401 `unauthenticated` / 403 `forbidden` | (slice 0/1 messages) | — (before the store) |
| 2 | `Idempotency-Key` header missing or not a UUID | 422 `invalid_request` | "Missing Idempotency-Key header." / "Idempotency-Key must be a UUID." | — |
| 3 | Body fails Pydantic (`ServiceDraft` rules such as the date, unknown field, over-long entry, `message` over 5000, more than 200 list entries) | 422 `invalid_request` | "The request was not valid." with `fields` (for example `additional_emails.3`, `message`, `service.service_date_iso`) | — |
| 4 | Same key, different body | 422 `idempotency_mismatch` | (slice 1 message) | — |
| 4 | Same key, a request still running | waits on the key's lock, then gets that request's stored answer | — | — |
| 4 | Same key and body, answer stored | the stored status and body, `Idempotent-Replayed: true`; nothing re-runs, nothing is charged | — | — |
| 5 | A `contact_ids` entry not in the active church | 404 `not_found` | "One of the selected contacts no longer exists. Refresh the list and try again." (`details.field = "contact_ids"`) | yes |
| 5 | A selected contact's stored address fails `normalize_address` | 422 `invalid_request` | "The saved contact “{name, or the address when the name is blank}” has an invalid email address. An admin can remove it and add it again in the current app's Settings." (`contact_ids`; the hint text is `MALFORMED_CONTACT_HINT`, which 6a swaps) | yes |
| 5 | An `additional_emails` entry fails `normalize_address` | 422 `invalid_request` | "“{value, truncated to 60 chars}” isn't a valid email address." (`additional_emails`) | yes |
| 5 | Zero recipients after de-duplication | 422 `invalid_request` | "Please select at least one recipient or enter an email address." (`recipients`) | yes |
| 5 | More than 50 recipients after de-duplication | 422 `invalid_request` | "You can email at most 50 people at once." (`recipients`) | yes |
| 6 | Gmail not configured | 503 `gmail_not_configured` | "Per-user Gmail sending isn't configured on this deployment." | no |
| 6 | Caller has no stored connection (or its `google_email` is NULL) | 409 `gmail_not_connected` | "Connect your Gmail first, then try again." | yes |
| 7 | 5a `clean_input`: a custom element label blank after trim | 422 `invalid_request` | "Give each custom element a label." (`custom_elements.<i>.label`) | yes |
| 7 | 5a `resolve_hymn_refs`: a `hymn_id` no longer in the church's hymnal (for example deleted in Settings) | 404 `not_found` | "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step." (`details.field = "hymns.<slot>.hymn_id"`; slice 4's wording, as 5a uses it) | yes |
| 7 | Document build failure | 500 `internal_error` | generic, logged (5a behavior) | no |
| 8 | Rate limit (`email` bucket), charged here | 429 `rate_limited` + `Retry-After` | (slice 2 message; `details.retry_after_seconds`) | no (`RateLimited` is never stored, so the entry is dropped) |
| 9 | Token refresh: `invalid_grant`, and the stored token is still the one that failed → row **deleted** | 502 `gmail_send_failed`, `details: {disconnected: true, send_uncertain: false}` | "Your Gmail connection has expired or was removed. Reconnect Gmail and try again." | no |
| 9 | Token refresh: `invalid_grant`, but the row was replaced meanwhile (a reconnect in either app) → row **kept** | 502 `gmail_send_failed`, `disconnected: false` | "Your Gmail connection changed while sending. Nothing was sent — try again." | no |
| 9 | Token refresh: `invalid_client` / `unauthorized_client` → row **kept**, ERROR logged | 503 `gmail_not_configured` | "Gmail sending isn't set up correctly on this deployment." | no |
| 9 | Token refresh: 5xx / network / no `access_token` | 502 `gmail_send_failed`, `disconnected: false` | "Couldn't reach Gmail. Nothing was sent — try again in a minute." | no |
| 9 | Token refresh timeout (15 s) | 504 `upstream_timeout` | "Google took too long to respond. Nothing was sent — try again." | no |
| 10 | Send: could not connect (`ConnectError`, `ConnectTimeout`, `PoolTimeout`), so nothing reached Gmail | 502 `gmail_send_failed`, `disconnected: false` | "Couldn't reach Gmail. Nothing was sent — try again in a minute." | no |
| 10 | Send: 403 with reason `insufficientPermissions` → token row **deleted** (same conditional delete as row 9) | 502 `gmail_send_failed`, `disconnected: true` | "Your Gmail connection no longer allows sending. Reconnect Gmail and try again." | no |
| 10 | Send: 429, or 403 with a rate/daily-limit reason | 502 `gmail_send_failed`, `disconnected: false` | "Gmail's sending limit has been reached. Nothing was sent — try again later." | no |
| 10 | Send: other 4xx | 502 `gmail_send_failed`, `disconnected: false` | "Gmail couldn't send this message. Nothing was sent — check the email addresses and try again." | no |
| 10 | **Send, uncertain:** Gmail answered 5xx after receiving the request | 502 `gmail_send_failed`, `details: {disconnected: false, send_uncertain: true}` | "Gmail reported a problem, so the email may already have been sent. Check your Gmail Sent folder before sending again." | **yes** |
| 10 | **Send, uncertain:** no answer after the request was written — read/write timeout (30 s) or a read/write/protocol error | 504 `upstream_timeout`, `details: {send_uncertain: true}` | "Gmail didn't confirm the email, so it may already have been sent. Check your Gmail Sent folder before sending again." | **yes** |

The route passes `store_error=lambda e: bool((e.details or {}).get("send_uncertain"))` to `run_idempotent`, so a retry with the same key after an uncertain outcome (a client timeout, a lost connection, a reflex second tap) replays the Sent-folder message and never calls Gmail again. Every other 5xx means nothing was sent, is not stored, and a retry runs again. Nothing after a successful Gmail send can fail the request (only the log line remains), so a sent email never ends as an unstored 500.

Google and database error text is never returned (F§1.5); it is logged with the request id.

### Timeouts (F§1.8, unchanged)

| Endpoint | Server upstream limits | Client `timeoutMs` |
|---|---|---|
| `POST /gmail-connection` | token 15 s + userinfo 15 s (connect 5 s each) | 40 000 |
| `POST /bulletin-emails` | refresh 15 s + send 30 s, docx < 3 s | 60 000 |
| `DELETE /gmail-connection` | revoke 5 s, best effort | default 20 000 |
| others | database only | default 20 000 |

### Rate limit

`ratelimit.py` gains the bucket `email`: 10 per hour per user (F§1.8). It is **not** a route dependency. The route passes `charge=lambda: ratelimit.consume("email", user_id=user.id)` to the usecase, which calls it once, right before the first Google call (row 8 above). So only requests that reach Gmail are charged: a typo in an address, a missing contact, a deleted hymn, "not connected" and idempotent replays cost nothing. The 429 is slice 1's `RateLimited`, which `run_idempotent` never stores, so the same key can be retried after `Retry-After`. A request refused by the limit has already rendered the docx (row 7); `/documents` renders without any limit already, so this adds no new exposure.

---

## Backend changes

### Modules

| Module | Change |
|---|---|
| `backend/google_oauth.py` | **Refactor** (characterize first, F§2.3). Keeps: `SCOPES`, `AUTH_URI`, `TOKEN_URI`, `USERINFO_URI`, `GMAIL_SEND_URI`, `STATE_TTL`, `consume_state`, `is_connected`, `save_user_token`, `create_state` (gains keyword-only `session`). Replaced with new signatures (below): `build_auth_url(state)` → `build_auth_url(config, state, *, login_hint)`; `exchange_code(code, expected_user_id)` → `exchange_code(config, code, *, expected_email, http)` (no longer stores anything). Deletes: `should_handle_gmail_callback`, `send_email`, `disconnect` (→ `delete_connection` + the usecase's revoke), `is_configured` (→ `GoogleOAuthConfig.configured`), `_fetch_email` (→ private `_fetch_userinfo_email(access_token, http)` inside `exchange_code`), `_access_token_for`, `_user_email` (a global lookup, inv §I), `_client_id/_client_secret/_redirect_uri` (`os.getenv` at call time), `_TIMEOUT`, `_google_error`, the `requests` import. Module docstring rewritten for the new redirect (Streamlit mention kept as "the frozen Streamlit app uses its own root redirect until slice 7"). |
| `backend/email_addresses.py` | **New.** `normalize_address(raw: str) -> str` (raises `InvalidAddress`) and `dedupe_addresses(addrs: Iterable[str]) -> list[str]`. The **only** address validator in the backend: 6a's contacts routes use it too (hand-off). |
| `backend/tests/fixtures/shared/email_addresses.json` | **New.** `{"valid": [{"raw", "normalized"}], "invalid": [...]}`, asserted by `test_email_addresses.py`, `test_api_bulletin_emails.py` and (6a) `test_api_contacts.py`, so contacts and recipients can never accept different addresses. |
| `backend/service_output.py` (created in 5a) | Reuses 5a's `service_date_display(d: date)` and `DOCX_MIME` unchanged (imports, never redefines). **Adds** `BULLETIN_EMAIL_FALLBACK`, `bulletin_email_subject(d: date)`, `default_bulletin_message(d: date)`, `plan_bulletin_addressing(sender, recipients)` and `compose_bulletin_email(...)`; 5a defines none of these. |
| `backend/email_contacts.py` | `list_contacts(church_id, *, session=None)`: order becomes `created_at, nullif(trim(name), '') NULLS LAST, id`; a NULL or blank-after-trim name is returned as `None`; ids through `db.ids.as_uuid`. New `get_contacts_by_ids(church_id, ids, *, session=None) -> list[dict]` (`WHERE church_id = :church AND id IN (:ids)`, same name mapping). Signatures stay compatible with `streamlit_views/settings.py` and `streamlit_tests`. `get_contacts_for_display` is left for slice 7 to delete. |
| `backend/usecases/email.py` | **New** (F§2.1 names it). Gmail connection and bulletin-send orchestration. |
| `backend/api/idempotency.py` (slice 1) | `run_idempotent` gains `store_error: Callable[[DomainError], bool] \| None = None`. Default behavior unchanged for every other route. |
| `backend/api/settings.py` | Adds `google_client_id`, `google_client_secret`, `google_oauth_redirect_uri` (all stripped) and property `google_oauth -> GoogleOAuthConfig`. |
| `backend/api/deps.py` | `get_google_config() -> GoogleOAuthConfig` (from settings; overridable in tests). |
| `backend/api/routes/gmail.py`, `contacts.py`, `bulletin_emails.py` | **New** route modules; mounted in `create_app()`. |
| `backend/api/ratelimit.py` | Adds the `email` bucket. |
| `backend/api/main.py` lifespan | Gmail configuration warnings (below). |
| `backend/.env.example` | `GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/gmail/callback` with a comment: "Frontend /gmail/callback page. Streamlit keeps its own value (its app root) until slice 7. Use the SAME client id/secret as Streamlit." |
| `backend/scripts/check_contact_addresses.py` | **New**, for manual check 14. `--church <id>` reads that church's contacts through `email_contacts.list_contacts` (run on Railway); `--stdin` reads a saved `GET /contacts` JSON body instead. Prints each contact id whose address fails `normalize_address`; never prints tokens. |

### `google_oauth.py` after the refactor

```python
@dataclass(frozen=True)
class GoogleOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    @property
    def configured(self) -> bool: ...      # all three non-empty (parity with is_configured)

class GoogleErrorKind(str, Enum):
    INVALID_GRANT = "invalid_grant"; CLIENT_MISCONFIGURED = "client_misconfigured"
    INCOMPLETE_RESPONSE = "incomplete_response"; SCOPE_MISSING = "scope_missing"
    NO_EMAIL = "no_email"; EMAIL_MISMATCH = "email_mismatch"
    INSUFFICIENT_SCOPE = "insufficient_scope"; SEND_LIMIT = "send_limit"
    SEND_REJECTED = "send_rejected"; UPSTREAM = "upstream"; TIMEOUT = "timeout"
    SEND_UNCONFIRMED = "send_unconfirmed"   # send only: the request was written, no definite answer

class GoogleOAuthError(Exception):
    def __init__(self, kind: GoogleErrorKind, *, status: int | None = None,
                 google_error: str | None = None): ...   # google_error is for logs only

@dataclass(frozen=True)
class GmailGrant:
    google_email: str
    refresh_token: str | None
    scopes: frozenset[str]

@dataclass(frozen=True)
class GmailConnection:
    google_email: str
    refresh_token: str

def build_auth_url(config, state: str, *, login_hint: str | None = None) -> str
def create_state(user_id, *, session: Session | None = None) -> str   # purges expired rows first
def purge_expired_states(session: Session) -> int                     # DELETE ... WHERE expires_at < now()
def consume_state(state: str) -> uuid.UUID | None                     # unchanged semantics
def exchange_code(config, code: str, *, expected_email: str,
                  http: httpx.Client | None = None) -> GmailGrant
def get_connection(user_id, *, session: Session | None = None) -> GmailConnection | None
    # None when there is no row, or the row's google_email is NULL/blank (the column is
    # nullable; the old send_email treated a missing sender as "not connected")
def save_user_token(user_id, google_email, refresh_token, *, session=None) -> None
def delete_connection(user_id, *, only_if_token: str | None = None,
                      session=None) -> str | None
    # DELETE ... WHERE user_id = :u [AND refresh_token = :only_if_token];
    # returns the removed refresh token, or None when no row matched
def refresh_access_token(config, refresh_token: str, *, http=None) -> str
def send_raw_message(access_token: str, raw: bytes, *, http=None) -> None
def revoke_token(token: str, *, http=None) -> None                   # best effort; never raises
```

Rules:
- `exchange_code` does not touch the database. It POSTs the code (15 s), checks `access_token`, checks the granted scopes, GETs userinfo (15 s), and compares the address case-insensitively with `expected_email`. Each failure raises `GoogleOAuthError(kind)`. Scope check: `scope = payload.get("scope")`; a missing or blank value means the requested `SCOPES` were granted (RFC 6749 §5.1: `scope` is omitted when identical to the request); a non-string value → `INCOMPLETE_RESPONSE`; otherwise `GMAIL_SEND_SCOPE not in scope.split()` → `SCOPE_MISSING`. There is no `KeyError` path.
- Google error classification (one helper, `_classify(resp_or_exc, *, phase)` with `phase` in `token | userinfo | refresh | send`): token endpoint 400 `invalid_grant` → `INVALID_GRANT`; 400/401 `invalid_client`, `unauthorized_client`, `redirect_uri_mismatch` → `CLIENT_MISCONFIGURED`; Gmail 403 `insufficientPermissions` (or `ACCESS_TOKEN_SCOPE_INSUFFICIENT`) → `INSUFFICIENT_SCOPE`; 429, or 403 `rateLimitExceeded`/`userRateLimitExceeded`/`dailyLimitExceeded` → `SEND_LIMIT`; other 4xx → `SEND_REJECTED` (send) or `UPSTREAM` (others).
  - `token`, `userinfo`, `refresh` (no side effect at Google): 5xx and `httpx.TransportError` → `UPSTREAM`; `httpx.TimeoutException` → `TIMEOUT`.
  - `send`, request **not** written (`httpx.ConnectError`, `ConnectTimeout`, `PoolTimeout`) → `UPSTREAM` (nothing was sent).
  - `send`, request written with no definite answer (`ReadTimeout`, `WriteTimeout`, `ReadError`, `WriteError`, `RemoteProtocolError`, any other `TransportError`) → `SEND_UNCONFIRMED` with `status=None`; a 5xx response → `SEND_UNCONFIRMED` with that `status`. These may have sent the email.
- `build_auth_url` keeps every current parameter and adds `login_hint` when given.
- All HTTP goes through `integrations/http.py` (injected `http`, default the shared client) with `httpx.Timeout(15, connect=5)` for token/userinfo/refresh, `httpx.Timeout(30, connect=5)` for send, `httpx.Timeout(5, connect=5)` for revoke.
- Nothing in this module logs a code, state, token or address.

### `service_output.py` additions (pure, no I/O)

```python
# Defined by 5a in this module and reused unchanged (never redefined here):
#   DOCX_MIME, MONTHS, service_date_display(d: datetime.date) -> str   # "October 04, 2026"

BULLETIN_EMAIL_FALLBACK = "Hi! Here’s the worship bulletin for this Sunday."   # U+2019, parity app.py:1125

def bulletin_email_subject(d: datetime.date) -> str     # f"Worship service — {service_date_display(d)}" (app.py:1124)
def default_bulletin_message(d: datetime.date) -> str   # Sunday → fallback text; else "…for {Weekday}, {Month} {D}."
                                                        # (English tables, locale-independent, like service_date_display)
def plan_bulletin_addressing(sender: str, recipients: list[str]) -> Addressing  # (to, bcc)
def compose_bulletin_email(*, sender: str, recipients: list[str], service_date: datetime.date,
                           message: str | None, attachment: bytes,
                           attachment_filename: str) -> EmailMessage
```

The date arguments are `datetime.date`, never ISO strings: the usecase passes `data.service_date` (5a's `ServiceInput`), which Pydantic has already validated.

`plan_bulletin_addressing` (decision 9):
- exactly one recipient → `To: [recipient]`, no Bcc;
- two or more → `To: [sender]`, `Bcc: recipients` minus any address equal to the sender (case-insensitive).

`compose_bulletin_email` uses `email.message.EmailMessage` (default policy): `From` = sender, `To`/`Bcc` from the plan, `Subject` from `bulletin_email_subject(service_date)`, body `message.strip()` or `default_bulletin_message(service_date)` when blank, one attachment with 5a's `DOCX_MIME` and the given filename. Header values contain only validated addresses and server-built strings, so there is no header-injection path.

### `email_addresses.normalize_address`

Accepts `raw.strip()` when all hold, else raises `InvalidAddress`:
- length ≤ 254; no whitespace, control characters (including CR/LF), or any of `, ; < > " ( ) [ ] \`;
- exactly one `@`; local part 1-64 characters;
- domain: at least two dot-separated labels, each 1-63 of `[A-Za-z0-9-]` not starting or ending with `-`; the last label ≥ 2 letters. ASCII only: internationalized domains (`anna@bücher.de`) are rejected on purpose (their punycode form, `anna@xn--bcher-kva.de`, is accepted).

Returns the trimmed address with the domain lower-cased (domains are case-insensitive); the local part's case is preserved. `dedupe_addresses` keeps the first occurrence, comparing lower-cased. No new dependency (`email-validator` is not installed and `EmailStr` needs it). Because this is the only validator (6a's contacts use it too), an address that can be saved as a contact can always be emailed; the shared fixture `email_addresses.json` pins that.

### `usecases/email.py`

```python
MALFORMED_CONTACT_HINT = "An admin can remove it and add it again in the current app's Settings."
    # 6a changes it to "An admin can fix it in Settings → Contacts." (with a test);
    # slice 7's backend copy check fails if "current app" is still here

def gmail_status(user_id: UUID, config: GoogleOAuthConfig) -> GmailStatus
def start_gmail_connect(user_id: UUID, user_email: str, config) -> str            # auth URL
def finish_gmail_connect(user_id: UUID, user_email: str, code: str, state: str,
                         config, http=None) -> GmailStatus
def disconnect_gmail(user_id: UUID, config, http=None) -> GmailStatus
def send_bulletin_email(church_id: UUID, user_id: UUID, data: ServiceInput,
                        contact_ids: list[UUID], additional_emails: list[str],
                        message: str | None, config, *,
                        charge: Callable[[], None] = lambda: None,
                        http=None) -> int                                         # recipient count
```

`ServiceInput` is 5a's domain type; the route converts with `body.service.to_input()` (usecases never import `api/*`), and the usecase uses `data.service_date` (a `datetime.date`) for the subject and message. `charge` is the rate-limit hook (§Rate limit); the usecase does not import `ratelimit`.

All map `GoogleOAuthError` kinds to `DomainError`s with the messages in the §API tables, and log `event outcome=<kind>` lines.

`finish_gmail_connect`:
1. `NotConfigured("gmail_not_configured")` if not configured.
2. `consume_state(state)` in its own committed transaction. `None` or `!= user_id` → `Rejected("gmail_state_invalid")`. The state is consumed before any Google call (CSRF check first).
3. Blank code → `Rejected("gmail_connect_failed")`.
4. `exchange_code(..., expected_email=user_email)` with **no session open**. `user_email` is the verified top-level email claim from `CurrentUser` (slice 0), not a database lookup.
5. New transaction: refresh token present → `save_user_token`; absent and `get_connection` is None → `Rejected("gmail_connect_failed", <refresh-token message>)`; absent and connected → keep.
6. Return the status.

`disconnect_gmail`: `delete_connection(user_id)` (unconditional; commit), then `revoke_token(removed_token)` outside the transaction; revoke failures are logged at WARNING and ignored. Returns `{configured, connected: false, google_email: null}`.

`send_bulletin_email` (step numbers match the # column of the §Errors table):
- **5. Recipients.** The `NotConfigured` check waits for step 6 so recipient errors surface first (parity order). One read session, closed before step 7: `get_contacts_by_ids(church_id, contact_ids)`; any requested id missing → `NotFound(<contacts message>, details={"field": "contact_ids"})`. Validate each contact address with `normalize_address` (→ `InvalidInput(field="contact_ids")`, naming the contact by name, or by address when the name is blank, plus `MALFORMED_CONTACT_HINT`), then each `additional_emails` entry (→ `InvalidInput(field="additional_emails")`). Recipients = `dedupe_addresses(contact addresses in request order + additional)`. Zero → `InvalidInput(field="recipients")`; more than 50 → `InvalidInput(field="recipients")`.
- **6. Connection.** Same session: `connection = get_connection(user_id)` (None also when `google_email` is NULL). Not configured → `NotConfigured`; no connection → `Conflict("gmail_not_connected")`.
- **7. Document.** `doc = build_document(church_id, data, "bulletin")` (5a) → `DocumentResult(content, filename)`. Its `InvalidInput` (custom element label) and `NotFound` (hymn, with `details.field`) propagate unchanged. It opens its own read session for hymn resolution; no hymn usage is written.
- `compose_bulletin_email(sender=connection.google_email, recipients=recipients, service_date=data.service_date, message=message, attachment=doc.content, attachment_filename=doc.filename)`; `raw = msg.as_bytes()`.
- **8. `charge()`** — the only call that can return 429; everything before it is free.
- **9-10. No session open:** `refresh_access_token` → `send_raw_message`.
- On `INVALID_GRANT` (refresh) or `INSUFFICIENT_SCOPE` (send): new transaction `delete_connection(user_id, only_if_token=connection.refresh_token)`. A row was removed → `UpstreamError("gmail_send_failed", details={"disconnected": True, "send_uncertain": False})`. No row matched (the user reconnected in either app meanwhile) → `UpstreamError("gmail_send_failed", "Your Gmail connection changed while sending. Nothing was sent — try again.", details={"disconnected": False, "send_uncertain": False})`.
- On `SEND_UNCONFIRMED`: `status` set (Gmail 5xx) → `UpstreamError("gmail_send_failed", details={"disconnected": False, "send_uncertain": True})`; `status` None → `UpstreamTimeout("upstream_timeout", details={"send_uncertain": True})`; messages from the table. The route's `store_error` keeps both for replay.
- Every other failure maps per the table, with `details={"disconnected": False, "send_uncertain": False}` where the code is `gmail_send_failed`.
- After `send_raw_message` returns, only the log line remains: `bulletin_email.sent church_id user_id recipients=n bcc=bool attachment_bytes duration_ms`. Never addresses, subject, message or tokens. Logging errors are handled by the logging module and cannot fail the request.
- Return `len(recipients)`.

### Routes

```python
# gmail.py
@router.get("/gmail-connection", response_model=GmailConnectionOut)
def get_status(user=Depends(get_current_user), cfg=Depends(get_google_config)): ...
@router.post("/gmail-connection/auth-url", response_model=GmailAuthUrlOut)
@router.post("/gmail-connection", response_model=GmailConnectionOut)
@router.delete("/gmail-connection", response_model=GmailConnectionOut)

# contacts.py
@router.get("/contacts", response_model=ContactList)
def list_(church=Depends(require_church)): ...

# bulletin_emails.py — no rate_limit dependency (see §Rate limit)
@router.post("/bulletin-emails", response_model=BulletinEmailOut)
def send(body: BulletinEmailIn,
         church=Depends(require_church),                     # 401/403 first
         user=Depends(get_current_user),
         key=Depends(idempotency_key(required=True)),        # then the key
         cfg=Depends(get_google_config)):                    # body errors after all dependencies
    return run_idempotent(
        user_id=user.id, route="POST /bulletin-emails", key=key, payload=body, status_code=200,
        store_error=lambda e: bool((e.details or {}).get("send_uncertain")),
        call=lambda: BulletinEmailOut(sent=True, recipient_count=email.send_bulletin_email(
            church.id, user.id, body.service.to_input(), body.contact_ids,
            body.additional_emails, body.message, cfg,
            charge=lambda: ratelimit.consume("email", user_id=user.id))))
```

Each route calls one usecase function and contains no `try/except` for domain errors (F§2.2).

### Configuration and startup checks

In the lifespan (log only; never refuse to start):
- some but not all of `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` set → WARNING naming the missing ones ("Gmail sending is disabled until …");
- redirect URI set but its path is not `/gmail/callback` → WARNING "GOOGLE_OAUTH_REDIRECT_URI should be <frontend origin>/gmail/callback" (catches a copied Streamlit root value);
- redirect URI origin not in `CORS_ORIGINS` → WARNING;
- `APP_ENV=production` and the redirect URI is not `https` → WARNING.

### Streamlit coupling removed

- The root-URL callback detection (`should_handle_gmail_callback`, app.py:334-336) and `oauth_error` session plumbing are replaced by `/gmail/callback` + `POST /gmail-connection`.
- `create_state` on every render (app.py:217) is replaced by a click-time `POST /gmail-connection/auth-url`.
- Email composition and recipient merge move from app.py:1115-1131 into `service_output` and `usecases/email.py`.
- `send_email`'s error-string return is replaced by typed exceptions.
- `google_oauth` reads configuration from `GoogleOAuthConfig` instead of `os.getenv`.
- **Normal case** (production Streamlit runs from `streamlit-frozen`, F D2): no shims are kept for `app.py` on `main`. `disconnect`, `is_configured`, `_fetch_email`, `should_handle_gmail_callback` and `send_email` are deleted, and `exchange_code`/`build_auth_url` change signature, as the Modules table says.
- **F§6.1 contingency** (Streamlit production still runs `app.py` from `main`): every function `app.py` calls must keep its old signature. The old names `exchange_code` and `build_auth_url` are taken by the new signatures, so the wrappers live in a separate module, **`backend/google_oauth_legacy.py`**, and the one `app.py` edit is `import google_oauth_legacy as google_oauth` (app.py:42). The module reads configuration with `os.getenv` (Streamlit's own `GOOGLE_*` values) through `_env_config() -> GoogleOAuthConfig` and delegates to `google_oauth`:
  - `is_configured()` → `_env_config().configured`;
  - `build_auth_url(state)` → `google_oauth.build_auth_url(_env_config(), state)` (no `login_hint`, parity);
  - `exchange_code(code, expected_user_id)` → looks up the user's email (the old `_user_email` query, moved here), calls the new `exchange_code`, applies the old store/keep refresh-token rule, returns the old `{user_id, email, refresh_token}` dict, and raises `RuntimeError(<our message>)` on failure (app.py:191-193 shows `str(e)`);
  - `disconnect(user_id)` → `google_oauth.delete_connection(user_id)` (no revoke, parity);
  - `send_email(user_id, to_email, subject, body_plain, *, attachment_bytes=None, attachment_filename=None) -> str | None` → the old behavior (all recipients in To, octet-stream attachment, error string or None) over `refresh_access_token` + `send_raw_message`;
  - `should_handle_gmail_callback(query_params, is_logged_in)` → the old body, moved;
  - re-exports `consume_state`, `create_state`, `is_connected`.
  
  AC 14 applies to `google_oauth.py` only; `google_oauth_legacy.py` is exempt and deleted in slice 7. Add the F§6.1 smoke test `streamlit_tests/test_app_gmail_smoke.py` (`streamlit.testing.v1.AppTest`, no network, env set): the app loads for a signed-in user with a church; the sidebar shows "Connect your Gmail" when not connected, "Connected: …" + Disconnect when a token row exists, and the not-configured caption when env is empty; a `?code=&state=` callback with a stubbed `exchange_code` stores nothing on a mismatch and clears the query.

### Data access and tenancy

- Gmail routes are user-scoped: every read and write is keyed by `CurrentUser.id`. There is no way to address another user's token or state; a state issued to another user is consumed and rejected.
- `/contacts` and `/bulletin-emails` use only `ActiveChurch.id`. Contact ids are resolved with `church_id` in the `WHERE` clause; another church's id is indistinguishable from a missing one (404, F§1.2 rule 2).
- The attachment is built by 5a's usecase from the posted draft plus the active church's hymnal; the client cannot point it at another church's data.
- The sender is always the caller's stored `google_email`; the request has no sender field.
- No database connection is held during any Google call (F§1.8).

---

## Data and migrations

**No schema change and no Alembic revision.** Tables used: `gmail_tokens`, `oauth_states`, `contacts` (read), `users` (none: the expected email comes from the token).

### Coexistence with the frozen Streamlit app (until slice 7)

| Shared thing | Rule |
|---|---|
| `gmail_tokens` (one row per user) | Both apps read and replace the same row. A connection made in either app works in both, so the tester is already "connected" in the new app on first visit. Disconnecting in either app disconnects both. The new app's automatic delete after `invalid_grant` is conditional on the refresh token that failed (`only_if_token`), so a reconnect made in either app in the meantime is never wiped. A row with a NULL `google_email` counts as not connected in the new app (as in the old `send_email`). |
| **Google OAuth client** | Railway **must use the same `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` as Streamlit Cloud.** A refresh token can only be refreshed by the client that issued it; with different clients, a refresh from the other app fails with `unauthorized_client`, and the frozen Streamlit code deletes the row on any 400/401 (google_oauth.py:288-291). Only `GOOGLE_OAUTH_REDIRECT_URI` differs between the two deployments. |
| Redirect URIs | Add `https://worship-service-builder.vercel.app/gmail/callback` and `http://localhost:3000/gmail/callback` to that client. **Keep** Streamlit's app-root URI and every other existing URI (Streamlit login `/oauth2callback`, and Supabase's `…/auth/v1/callback` if it shares the client). Each deployment's `exchange_code` sends its own redirect URI, matching the one in its own auth URL, so the flows never cross. |
| `oauth_states` | The new app deletes only **expired** rows when it creates a state. Streamlit's live states are untouched, and its accumulated orphans get cleaned up. |
| `contacts` | Read only here. Streamlit (until 6a) remains the place to add or delete contacts; it cannot edit one, so a malformed contact is fixed by deleting and re-adding it. Streamlit stores a nameless contact's name as `""`; the new app returns it as `null`. |
| Revoke on disconnect | Revoking the grant at Google also ends Streamlit's use of it. That matches the shared-row semantics above. |

Known gap, accepted until slice 7: the frozen Streamlit still disconnects on any 400/401 refresh error and still puts every recipient in To.

### Ops steps (in the PR description; owner performs)

1. Google Cloud Console → the OAuth client that Streamlit Cloud's `GOOGLE_CLIENT_ID` names → add the two redirect URIs above. Leave the rest.
2. Railway: set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to Streamlit's values, and `GOOGLE_OAUTH_REDIRECT_URI=https://worship-service-builder.vercel.app/gmail/callback`. Confirm the startup log has no Gmail warnings. The client secret now lives in two places until slice 7, which rotates it after the Streamlit app is deleted (hand-off).
3. Vercel (optional): `NEXT_PUBLIC_LEGACY_APP_URL=https://liturgy.streamlit.app` (Production + Preview).
4. Local: `backend/.env` redirect `http://localhost:3000/gmail/callback`.

---

## Frontend changes

### Routes

| Path | File | Notes |
|---|---|---|
| `/gmail/callback` | `src/app/(signed-in)/gmail/callback/page.tsx` | Client component; flow C |
| `/settings` | `src/app/(signed-in)/(church)/settings/page.tsx` | Redirects to `SETTINGS_SECTIONS[0].href` |
| settings layout | `src/app/(signed-in)/(church)/settings/layout.tsx` | `PageHeader`, role caption, `SettingsNav`, `LegacySettingsNote` |
| `/settings/account` | `src/app/(signed-in)/(church)/settings/account/page.tsx` | `AccountCard`, `GmailConnectionCard` |
| `/builder/review` | 5a's page | Card 5 (`email-slot.tsx`) renders `<EmailBulletinCard />`; the page reads `wsb:reopenEmailDialog` on mount and acts on it once the Gmail status query settles (flow B) |

### Components

| Component | File |
|---|---|
| `SettingsNav`, `LegacySettingsNote`, `SETTINGS_SECTIONS` | `src/components/settings/` (`sections.ts`, `settings-nav.tsx`, `legacy-settings-note.tsx`) |
| `AccountCard`, `GmailConnectionCard` | `src/components/settings/account-card.tsx`, `gmail-connection-card.tsx` |
| `EmailBulletinCard`, `EmailBulletinDialog`, `RecipientPicker` | `src/components/builder/review/`; 5a's `email-slot.tsx` placeholder is replaced so it renders `EmailBulletinCard` |
| `GmailCallback` (page body) | colocated with the page |
| `AppNav` | adds the Settings item; account menu adds "Settings" |

### Query hooks (`src/lib/queries/`)

| Hook | Client | Key / invalidation |
|---|---|---|
| `useGmailConnection()` | `api.user` GET `/gmail-connection` | `["gmail-connection"]` |
| `useStartGmailConnect()` | `api.user` POST `/gmail-connection/auth-url` | mutation; on success runs `startGmailRedirect(auth_url, returnTo)` |
| `connectGmailOnce(api, {code, state})` (`lib/gmail.ts`, not a hook) | `api.user` POST `/gmail-connection`, `timeoutMs: 40_000` | one shared promise per state (flow C); the page then calls `setQueryData(["gmail-connection"], response)` |
| `useDisconnectGmail()` | `api.user` DELETE `/gmail-connection` | invalidates `["gmail-connection"]` |
| `useContacts()` | `api.church` GET `/contacts` | `["church", id, "contacts"]` (6a invalidates it) |
| `useSendBulletinEmail()` | `api.church` POST `/bulletin-emails`, `timeoutMs: 60_000`, `idempotencyKey` | no invalidation on success; see error table |

`lib/api/timeouts.ts` gains the two entries above (values from F§1.8). Mutations in the dialog and callback page mark their errors as handled locally so they don't also toast; 401 and church-403 still go through the global handler (F§4.4).

**Supabase browser client** (`src/lib/supabase/client.ts`): `createBrowserClient(url, key, { auth: { detectSessionInUrl: false } })`, so the client never treats `/gmail/callback?code=…` or `?error=…` as a Supabase callback (flow C). Sign-in is unaffected: `/auth/callback/route.ts` exchanges the Supabase code on the server.

### Pure modules

| Module | Contents |
|---|---|
| `src/lib/email.ts` | `MAX_RECIPIENTS = 50`, `MESSAGE_MAX_LENGTH = 5000`; `parseAddressList(text): string[]`; `countRecipients(contactEmails, extras): number` (case-insensitive de-dupe); `bulletinEmailSubject(dateIso)` and `defaultBulletinMessage(dateIso)` (built on `serviceDateDisplay(dateIso)`, the TypeScript twin of `service_output.service_date_display`, which uses the English month table 5a's `lib/download.ts` already has for `docxFilename`; 5b exports it from there if 5a didn't); `fieldTarget(key): "to" \| "other" \| "message" \| "top"` (the 422 mapping in §Send outcomes) |
| `src/lib/gmail.ts` | `GMAIL_RETURN_KEY = "wsb:gmailReturnTo"`, `REOPEN_EMAIL_KEY = "wsb:reopenEmailDialog"`; `isGoogleAuthUrl(url)`; `startGmailRedirect(authUrl, returnTo, reopen?)`; `readReturnTo()` (through `safeInternalPath`); `parseCallbackParams(search)`; `connectGmailOnce(api, {code, state})` (module-level `Map<state, Promise>`) |
| `src/lib/idempotency.ts` | `createSendKeyTracker()` (below) |
| `src/lib/urls.ts` | `safeInternalPath` allowed prefixes gain `/gmail/callback` |

**Idempotency key rule** (`createSendKeyTracker`), which refines F§1.6 "one key per dialog open, reused on retry, replaced after success" so that a corrected retry never hits `idempotency_mismatch` or a stored 4xx:
- `keyFor(body)`: fingerprint the request body with `fingerprint()` from `lib/draft/fingerprint.ts`; reuse the current key only if the fingerprint matches, else create a new UUID v4.
- `settle(result)`: after a 2xx or any 4xx response, drop the key (the answer is final and the user sees it). After a client-side `network_error`/`timeout` or any 5xx, keep it. Keeping is protective, because the server stores the uncertain-send answers (`details.send_uncertain`, §Errors) and a successful send, so an identical retry replays them instead of sending again. It is also harmless, because every other 5xx is not stored and means nothing was sent, so the retry simply runs again.
- `rotate()`: drop the key now; used only by **Send again anyway** after an uncertain outcome, when the user has chosen to send a new copy.
- The tracker lives in the Review page with the form state; it is discarded when the page unmounts (including church switch).

### Storage keys (all through `lib/storage.ts`, `wsb:` prefix)

| Key | Store | Shape | Lifetime |
|---|---|---|---|
| `wsb:gmailReturnTo` | session | internal path | set before redirect, cleared on callback success |
| `wsb:reopenEmailDialog` | session | `{church_id, contact_ids?, other_addresses?, message?}` | set before redirect from the Review step; read on Review mount and cleared once the Gmail status query settles |
| `wsb:emailPrefs:{userId}:{churchId}` | local | `{version: 1, contact_ids: string[]}` | written after a successful send; removed by slice 2's pruning when the user leaves the church (5b extends the prune to this prefix) |

The draft (`DraftV1`) is unchanged; no draft version bump. The dialog reads `draft.readings.date_iso`, the step status, the dirty flag, and `draftToServicePayload(draft)` (5a; one argument) at send time, so the attachment always reflects the latest on-screen state (decision 4).

### Accessibility

Dialog title labels the dialog; each checkbox row is a `<label>`; the recipients group has a `fieldset`/`legend` "To"; errors render in an `aria-live="polite"` region and the first invalid control is focused; the callback page's status text is `role="status"`.

---

## Behavior changes vs Streamlit

1. **Gmail OAuth returns to the new app** at `/gmail/callback` (frontend) instead of the Streamlit root; the frontend POSTs `{code, state}` with the bearer token. Streamlit keeps its own redirect until slice 7.
2. **Same-tab consent** instead of a new tab (which started a new Streamlit session, inv A3); the draft survives in localStorage and the user returns to where they started, with the email dialog reopened when they came from it.
3. **State created per click** (not per render) and **expired states purged** on each create (inv F8/F9 orphans).
4. **`login_hint`** pre-selects the signed-in Google account, reducing account-mismatch errors.
5. **`?error=` handled**: cancel shows "Gmail connection was cancelled."; other errors show a generic message (Streamlit ignored them).
6. **Granted-scope check**: a connection without `gmail.send` (granular consent unticked) is refused with an explanation instead of failing later at send time.
7. **No raw Google or exception text** reaches the user; every message is defined in our code (F§1.5). The unreachable "Sign in before connecting a Gmail account." is removed.
8. **State error copy** changes from "Sign-in expired or was invalid. Please try again." to "This Gmail connection request expired or was already used. Try connecting again." The mismatch message now names the signed-in address.
9. **Disconnect only when Google says the grant is gone** (`invalid_grant` on refresh, or a missing send scope on send). Streamlit also disconnected on `invalid_client`/`unauthorized_client` (our misconfiguration), silently dropping a valid token.
10. **Disconnect revokes the grant at Google** (best effort), not just deletes the row.
11. **Status shows the connected Google address** (Streamlit showed the login address; they are equal by construction).
12. **Gmail controls move** from the sidebar to Settings → Account and the Review step card; "in the sidebar" disappears from all copy.
13. **The attachment is always rebuilt** from the posted draft on the server (decision 4): no stale file, no church-switch leakage (inv A7, F3), and no "Prepare" step before emailing.
14. **Email is available whenever the date is valid**, even with an incomplete or unsaved service; the dialog notes what's missing and that it isn't archived.
15. **Multiple recipients go in BCC with the sender in To**; a single recipient stays in To (decision 9). The dialog says so.
16. **Recipient validation, de-duplication and a 50-recipient cap**; a malformed saved contact is reported instead of being passed to Gmail (Streamlit sent whatever text a contact held).
17. **Message prefilled and editable** (decision 9); blank still falls back to the default. On non-Sunday dates (decision 8) the prefill and fallback say "for {Weekday}, {Month} {D}" instead of "this Sunday".
18. **Attachment MIME type** is the docx type instead of `application/octet-stream` (better previews on phones).
19. **Contact labels**: nameless contacts (NULL or `""` name) show the address, not "None <address>" or " <address>"; the picker is keyed by id (no stale-label `KeyError`).
20. **"Not configured" is explained** instead of asking the user to connect (which was impossible).
21. **No double sends**: a required `Idempotency-Key` makes double taps and network retries safe; the send button is disabled while pending. When Gmail's answer is uncertain (timeout, dropped connection or 5xx after the request was sent), the user is told to check the Sent folder, a plain retry replays that answer, and only an explicit **Send again anyway** sends a new copy.
22. **Rate limit**: 10 bulletin emails per hour per user, counting only requests that reach Gmail (typos and other rejected requests don't count).
23. **Success copy**: "Email sent to N people" (was "Email sent to N recipient(s).").
24. **Emailing records no hymn usage.** Streamlit's Prepare did; usage is now recorded on Save (decision 9, slice 5a).
25. **Remembered recipients**: the contacts chosen in the last successful send are pre-selected next time (per user, per church, on this device).
26. **Timeouts** are 15 s per Google call and 30 s for the send (was 30 s each, F§1.8).
27. **Contacts order** gains a deterministic tie-break with nameless contacts last.
28. **Deleted hymns are reported in the email dialog** with the same message and "Go to Hymns" link as 5a's Save card, instead of a generic error.

---

## Testing

TDD throughout; characterization tests for `google_oauth` first (F§2.3.1), except where a decided change applies (BCC, disconnect rule, scope check, `login_hint`), where the new test is written first and fails.

### Backend (pytest, no network; `respx` for httpx)

**`backend/tests/test_google_oauth.py`** (replaces `test_oauth_state.py`, `test_gmail_exchange.py`, `test_gmail_token_store.py`; every existing assertion is ported except `should_handle_gmail_callback`, which is deleted with the function):
- `SCOPES` unchanged (ported `test_scopes_unchanged`).
- `build_auth_url`: contains the config redirect URI, `response_type=code`, `access_type=offline`, `prompt=consent`, the state, and `login_hint` when given; no `gmail_oauth` marker.
- `create_state` persists a user-bound row with a 10-minute expiry and deletes only expired rows (another user's valid state survives).
- `consume_state`: single use; unknown/empty → None; expired → None and deleted (ported).
- `save_user_token` single row per user and replace; `delete_connection` returns the old token; `delete_connection(only_if_token=old)` after the row was replaced with a new token deletes nothing and returns None; `get_connection` (ported store tests), and None for a row whose `google_email` is NULL.
- `exchange_code`: success (case-insensitive match returns Google's casing); mismatch → `EMAIL_MISMATCH`; `scope` present without `gmail.send` → `SCOPE_MISSING`; token response **without** a `scope` field → success (no `KeyError`); non-string `scope` → `INCOMPLETE_RESPONSE`; token 400 `invalid_grant` → `INVALID_GRANT`; 401 `invalid_client` → `CLIENT_MISCONFIGURED`; 500 → `UPSTREAM`; timeout → `TIMEOUT`; no access token → `INCOMPLETE_RESPONSE`; userinfo 401 → `NO_EMAIL`; asserts it opens no DB session.
- `refresh_access_token`: success; `invalid_grant`; `unauthorized_client`; timeout.
- `send_raw_message`: 200; 403 `insufficientPermissions` → `INSUFFICIENT_SCOPE`; 429 and 403 `dailyLimitExceeded` → `SEND_LIMIT`; 400 → `SEND_REJECTED`; `ConnectError` and `ConnectTimeout` → `UPSTREAM`; 503 → `SEND_UNCONFIRMED` with `status == 503`; `ReadTimeout`, `ReadError` and `RemoteProtocolError` → `SEND_UNCONFIRMED` with `status is None`.
- `revoke_token` swallows errors and timeouts.

**`test_email_addresses.py`**: driven by the shared fixture `backend/tests/fixtures/shared/email_addresses.json` — valid addresses (plus-tags, subdomains, local-part case preserved, domain lower-cased, punycode domain) and invalid ones (no `@`, two `@`, spaces, trailing dot, `a@b`, 255 chars, `"a@b.com, c@d.com"`, `"a@b.com\r\nBcc: x@y.com"`, `<a@b.com>`, `anna@bücher.de`); `dedupe_addresses` keeps first occurrence case-insensitively. The same fixture is asserted through `POST /bulletin-emails` (below) and, in 6a, through `POST /contacts`.

**`test_service_output_email.py`**:
- addressing: 1 recipient → To=[r], no Bcc; 3 → To=[sender], Bcc=all 3; sender among ≥2 recipients → excluded from Bcc (case-insensitive); sender as the only recipient → To=[sender].
- the composed message parses back: `Subject` decodes to "Worship service — October 04, 2026"; `From` is the sender; body is the stripped message, or the default when blank or whitespace; one attachment with `DOCX_MIME` and filename `worship_October_04_2026.docx`; `Bcc` header present only in the multi-recipient case.
- `bulletin_email_subject(d)`: `date(2026, 10, 4)` → "Worship service — October 04, 2026" (built on 5a's `service_date_display`).
- `default_bulletin_message(d)`: Sunday → the exact fallback (U+2019); `date(2027, 2, 10)` → "Hi! Here’s the worship bulletin for Wednesday, February 10."; locale-independent (same `LC_TIME` check as 5a's `service_date_display` test).
- shared fixture `backend/tests/fixtures/shared/bulletin_email.json` (`[{date_iso, subject, default_message}]`, including a Sunday, a weekday, a first-of-month and a single-digit day) drives both this test and the TypeScript test; the Python test converts each `date_iso` with `datetime.date.fromisoformat` before calling `bulletin_email_subject` and `default_bulletin_message`.

**`test_usecase_email.py`** (SQLite `tmp_db`, `FakeGoogle` injected as `http` via respx routes):
- connect: happy path stores the token; state for another user → `gmail_state_invalid` and nothing stored; reused state; expired state; mismatch stores nothing; scope missing stores nothing; no refresh token with an existing connection keeps the old token; without one → the refresh-token message.
- disconnect deletes the row and calls revoke; revoke failure still succeeds.
- send: recipient order and de-dupe across contacts and extras; zero → `recipients` message; 51 after de-dupe (from 60 entries with duplicates) → cap message; unknown contact id → `NotFound` with `details.field == "contact_ids"`; another church's contact id → `NotFound` and nothing sent; malformed saved contact → `contact_ids` message naming it (by address when its name is `""`) with `MALFORMED_CONTACT_HINT`; recipient errors come before `gmail_not_connected`; not configured → 503 kind; a token row with NULL `google_email` → `gmail_not_connected`; `invalid_grant` → row deleted + `details.disconnected is True`; `invalid_grant` when the row was replaced with a new token between the read and the delete (the fake refresh handler replaces it) → row kept, `disconnected is False`, the "changed while sending" message; `unauthorized_client` → row kept + `gmail_not_configured`; `insufficientPermissions` → row deleted (same conditional delete); send limit / 4xx / connect errors / refresh 5xx and timeouts map as the table says with `send_uncertain is False`; send `ReadTimeout` → `UpstreamTimeout` and send 503 → `gmail_send_failed`, both with `details.send_uncertain is True`.
- 5a errors propagate: a draft whose `hymns.response.hymn_id` was deleted → `NotFound` with `details.field == "hymns.response.hymn_id"`; a blank custom-element label → `InvalidInput` with `field == "custom_elements.0.label"`; in both cases nothing is sent and `charge` is not called.
- **attachment identity** (python-docx output is not byte-reproducible: every zip entry carries the build time): `usecases.email.build_document` is monkeypatched to return `DocumentResult(b"FIXED-DOCX", "worship_October_04_2026.docx")`; assert the decoded attachment equals `b"FIXED-DOCX"` and the fake was called once with `(church_id, service_input, "bulletin")`. One unpatched test compares the attachment's unzipped `word/document.xml` with that of a direct `build_document` call on the same input. `hymn_usage` has no rows after a send.
- `charge` is called exactly once, after the document build and before the fake refresh handler runs; it is not called for any 4xx/409/503 path above.
- **no pooled connection during Google calls**: a pool `checkout`/`checkin` event counter must be 0 when the fake refresh and send handlers run.
- logs contain no recipient address, subject, message, code or token (capture with `caplog`).

**API tests** (`TestClient`, JWKS helper, F§5.1):
- `test_api_gmail.py`: status configured/unconfigured/connected; `X-Church-Id` ignored; auth-url 503 when unconfigured, returns a Google URL whose state is stored for the caller with `login_hint` = caller email; POST success and each error row in the §API table with exact code and message; a Google error body containing `SECRET-GOOGLE-TEXT` never appears in any response; DELETE returns `connected: false`; unauthenticated → 401 on all four.
- `test_api_contacts.py`: a member lists contacts in order, with a NULL-name row and a `""`-name row both returned as `name: null` and sorted after named contacts created at the same time; `assert_church_isolated` (non-member 403; church A's list never includes church B's contacts).
- `test_api_bulletin_emails.py`: a **member** (not admin) sends → 200 with `recipient_count`; missing `Idempotency-Key` → 422; replay with the same key and body → the stored 200 and exactly one Gmail send; same key, different body → 422 `idempotency_mismatch`; two concurrent requests with one key (threads) → one send.
  - **Uncertain sends are replayed**: the fake Gmail send route raises `httpx.ReadTimeout` → 504 `upstream_timeout` with `details.send_uncertain: true`; a retry with the same key and body → the identical stored 504 with `Idempotent-Replayed: true`, and the Gmail send route was called **exactly once**. Same for a send 503 (stored 502). A send `ConnectError` → 502 not stored: the retry with the same key runs again and succeeds (send route called twice, one email). A refresh timeout → 504 without `send_uncertain`, not stored.
  - **Check order** (the §Errors table): unauthenticated with no key → 401; a member with no key and an invalid body → the key 422; a valid key and an over-long `message` → Pydantic 422 with `fields.message`; a valid key and 201 `contact_ids` → 422 `fields.contact_ids`, while 60 unique contact ids → the friendly `recipients` cap message.
  - **Rate limit charges only requests that reach Gmail**: 10 successful sends, then an 11th → 429 with `Retry-After` and no Gmail call; before that, 15 requests failing with 422 (bad address), 404 (unknown contact) or 409 (not connected), and 5 replays, did not use up the bucket; a 429 is not stored.
  - `assert_church_isolated` with a church-B contact id → 404 and no send; a church-B hymn id in `service.hymns` → 404 with `details.field` and no send; non-member → 403; every `invalid` entry of `email_addresses.json` in `additional_emails` → 422 `fields.additional_emails` and every `valid` one → accepted; an unknown body field → 422; 409, 502 (with `details.disconnected`), 503 and 504 mappings.
- `test_route_guards.py`: the four Gmail routes added to `USER_SCOPED`; `/contacts` and `/bulletin-emails` detected as church-guarded.
- `test_openapi_contract.py`: snapshot regenerated.
- Lifespan warnings: partial Google config; redirect URI not ending in `/gmail/callback`; origin not in `CORS_ORIGINS`.
- `test_email_contacts.py` updated for the ordering (NULL and `""` names last, id tie-break) and the `""` → `None` mapping; existing assertions kept.
- `test_idempotency.py` (slice 1 file): `store_error` returning True stores a 5xx `DomainError` and replays it; returning False (and the default) keeps slice 1's behavior; a `RateLimited` raised inside `call` is not stored, also when `store_error` is given.
- F§6.1 contingency only: `streamlit_tests/test_app_gmail_smoke.py` (see Streamlit coupling removed).

### Frontend (Vitest 3; `unit` and `dom` projects, F§5.2)

Unit (`*.test.ts`):
- `email.test.ts`: `parseAddressList` (commas, semicolons, new lines, `Name <a@b.com>`, blanks, whitespace); `countRecipients` de-dupes case-insensitively across contacts and extras; `bulletinEmailSubject` and `defaultBulletinMessage` against the shared fixture (read with `fs`); `fieldTarget`: `additional_emails` and `additional_emails.3` → other, `message` → message, `recipients`/`contact_ids`/`contact_ids.2` → to, `custom_elements.0.label` and `service.service_date_iso` → top.
- `idempotency.test.ts`: same body after `network_error` → same key; after 5xx (with or without `send_uncertain`) → same key; after 4xx → new key; after 2xx → new key; changed body → new key; `rotate()` → new key.
- `supabase-client.test.ts`: with `@supabase/ssr` mocked, `createClient()` passes `auth.detectSessionInUrl === false`.
- `gmail.test.ts`: `isGoogleAuthUrl` accepts only `https://accounts.google.com/…`; `readReturnTo` rejects `//evil.com`, `https://…`, and unknown prefixes and falls back to `/settings/account`.
- `urls.test.ts`: `/gmail/callback` is now allowed.

DOM (`*.test.tsx`, `installFakeApi`, `renderWithProviders`):
- **Gmail callback page**: success posts `{code, state}` **once** under `<StrictMode>` (the fake API holds the POST open while the test checks the page), cleans the URL with `replaceState`, and the "didn't finish" card is **never** rendered at any point (a `MutationObserver` records every rendered text), then toasts "Gmail connected", seeds `["gmail-connection"]` with the response (`getQueryData`), and navigates to the stored path; `error=access_denied` toasts "Gmail connection was cancelled." and navigates back without calling the API; another `error` value shows the generic message and does not echo it; no params → "didn't finish"; a 400 shows the server message with Try again and Go back; `gmail_not_configured` shows only Go back.
- **GmailConnectionCard**: loading, error + Retry, not configured, not connected, connected; Connect calls auth-url, stores `wsb:gmailReturnTo`, and assigns `window.location` (spied); a non-Google URL is refused; Disconnect calls DELETE and shows Not connected.
- **EmailBulletinCard**: not configured, not connected (Connect stores the reopen flag), invalid date disables with the helper, valid date opens the dialog.
- **EmailBulletinDialog**: contacts render (nameless shows the address), last-send preselection, the button label counts de-duplicated recipients, the BCC note appears at 2+, the prefilled message, the textarea has `maxLength` 5000, 51 recipients disable Send with the cap helper, the request carries `X-Church-Id`, `Idempotency-Key` and `draftToServicePayload(draft)`; success closes, toasts "Email sent to 2 people" and writes `wsb:emailPrefs`; a 422 on `additional_emails.1` shows under "Other addresses" and focuses it; a 422 on `message` shows under Message; a 422 on `custom_elements.0.label` shows at the top; 404 with `details.field: "contact_ids"` invalidates contacts and shows the contacts message; 404 with `details.field: "hymns.response.hymn_id"` shows the hymn message "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step." and a "Go to Hymns" link to `/builder/hymns` and does **not** invalidate contacts; 409 and 502-disconnected show the connect/reconnect button and invalidate `["gmail-connection"]`; 504 with `send_uncertain` shows the Sent-folder message and **Send again anyway**: Send again with nothing changed reuses the key, Send again anyway uses a new one; a network error shows the "may already have been sent" copy and a retry reuses the same key; empty contacts show the empty state; contacts error shows Retry while extras still work.
- **Review page**: `wsb:reopenEmailDialog` for the active church, with the status query still loading, keeps the key and does not open; when the status resolves `connected: true` the dialog opens with the saved state and the key is cleared; resolving `connected: false` (after a cancel) or an error clears the key without opening; a value for another church is ignored and cleared.
- **Settings layout**: `/settings` redirects to `/settings/account`; the role caption; the nav shows Account; the legacy note links only when the env URL is https.

### Manual checks (appended to `docs/manual-verification.md`; production Vercel URL, 375 px and desktop)

1. Startup log on Railway shows no Gmail warnings.
2. Settings → Account shows the tester **already connected** (row from Streamlit).
3. Disconnect → Streamlit's sidebar also shows not connected. Connect in the new app → Google pre-selects the signed-in account → back on Account with "Gmail connected" → Streamlit shows connected too.
4. Connect from the Review step, cancel at Google → "Gmail connection was cancelled." back on Review, draft intact.
5. Connect choosing a different Google account → mismatch message; nothing stored.
6. At consent, untick "Send email on your behalf" (if Google shows granular choices) → the scope message.
7. After a successful connect, reload `/gmail/callback` → "didn't finish" card; status still connected.
8. Email to one contact → the recipient sees themselves in To. Email to two contacts + one typed address → each sees only the sender in To and no other addresses; the sender's Sent copy shows the Bcc list; the sender also receives a copy.
9. The attachment opens in Word and in iOS Mail preview, includes the sermon title, and reflects an edit made just before sending (no Prepare step).
10. Double-tap Send → one email.
11. Remove the app's access at myaccount.google.com/permissions → Send → "Your Gmail connection has expired or was removed…" → Reconnect → the dialog reopens with recipients and message kept → send works.
12. Switch church with the dialog open → dialog closes; reopening shows the other church's contacts.
13. Streamlit still connects through its own root redirect, and still sends with a token the new app stored (same client).
14. A contact-data check before the gate: confirm each of the tester's contacts passes `normalize_address` without the production `DATABASE_URL` leaving Railway — either `railway ssh` into the backend service and run `python -m scripts.check_contact_addresses --church <id>` there, or save the Review page's `GET /contacts` response from the browser's Network tab and pipe it to `python -m scripts.check_contact_addresses --stdin` locally. Fix failures by deleting and re-adding the contact in Streamlit's Settings (it cannot edit contacts).
15. Regression pass: sign in, switch church, open Builder, Services, Settings.
16. Streamlit smoke check (F§6.3 phase B): load the church, load an archived service, open Settings.

---

## Acceptance criteria

1. `GET /gmail-connection`, `POST /gmail-connection/auth-url`, `POST /gmail-connection`, `DELETE /gmail-connection`, `GET /contacts` and `POST /bulletin-emails` exist with the guards, schemas, status codes and exact messages in §API, and appear in the committed OpenAPI snapshot and generated TypeScript types. *(CI)*
2. The four Gmail routes are on the `USER_SCOPED` allowlist; `/contacts` and `/bulletin-emails` pass `assert_church_isolated`; a contact id from another church returns 404 and sends nothing. *(test)*
3. A state issued to another user, a reused state, or an expired state returns 400 `gmail_state_invalid` and stores nothing; an account mismatch or a missing `gmail.send` scope returns 400 `gmail_connect_failed` and stores nothing. *(test)*
4. No response body from any route in this slice contains Google's error text (seeded marker test). *(test)*
5. With two or more recipients the sent MIME message has `To: <sender>` and every recipient in `Bcc`; with one recipient it has `To: <recipient>` and no `Bcc`; the subject decodes to "Worship service — {'%B %d, %Y' date}"; the attachment is named `worship_{Month}_{DD}_{YYYY}.docx` with the docx MIME type, is exactly the bytes `build_document(church_id, service_input, "bulletin")` returned for that request (asserted with a stubbed build), and a real build's attachment has the same `word/document.xml` as a direct bulletin build of the posted draft. *(test)*
6. `POST /bulletin-emails` without `Idempotency-Key` returns 422; an identical replay returns the first response with exactly one Gmail send; a send that ends uncertain (send timeout, or Gmail 5xx) followed by a retry with the same key returns the stored 504/502 with `details.send_uncertain: true` and calls Gmail's send exactly once; the 11th request that reaches Gmail in an hour returns 429 with `Retry-After`, and requests rejected earlier (422/404/409) or replayed are not counted; the checks run in the order of the §Errors table. *(test)*
7. `invalid_grant` on refresh (or a missing send scope on send) deletes the caller's `gmail_tokens` row only if it still holds the token that failed, and returns 502 `gmail_send_failed` with `details.disconnected: true`; a row replaced meanwhile is kept; `unauthorized_client` keeps the row; a row with NULL `google_email` reads as not connected. *(test)*
8. No pooled database connection is checked out while Google is being called. *(test)*
9. Emailing writes no `hymn_usage` rows. *(test)*
10. The `/gmail/callback` page posts exactly once under StrictMode and never shows "didn't finish" during a successful connect, removes `code` and `state` from the address bar, handles `?error=access_denied`, seeds the Gmail status query, and returns to the stored path; `/gmail/callback` is an allowed post-login path; the Supabase browser client has `detectSessionInUrl: false`; after connecting from the Review step the dialog reopens with its form state once the status query reports connected. *(test)*
11. The email dialog sends `draftToServicePayload(draft)` with `X-Church-Id` and an `Idempotency-Key` that is dropped after a 2xx or 4xx, kept after a network error, timeout or 5xx while the body is unchanged (so a retry after an uncertain outcome replays the stored answer), and replaced only by **Send again anyway**; field errors, the contact 404 and the hymn 404 (with "Go to Hymns") appear where §Send outcomes says. *(test)*
12. `/settings` redirects to `/settings/account`, which shows identity, Log out, and the Gmail card in all five states; the Settings nav item appears in the header. *(test + deployed)*
13. The subject and default message are identical in Python and TypeScript for every case in `backend/tests/fixtures/shared/bulletin_email.json`. *(test)*
14. `google_oauth.py` no longer calls `os.getenv`, `requests`, or defines `should_handle_gmail_callback`/`send_email`/`disconnect`/`is_configured`/`_fetch_email`; all its HTTP goes through `integrations/http.py`. *(test/CI grep)* Only under the F§6.1 contingency, `google_oauth_legacy.py` (exempt from this check) keeps every function `app.py` calls with its old signature, and `test_app_gmail_smoke.py` passes. *(test)*
14a. `normalize_address` is the only address validator: `email_addresses.json` passes through `normalize_address` and `POST /bulletin-emails` (and, from 6a, `POST /contacts`) with identical accept/reject results; no `email-validator` dependency. `GET /contacts` returns blank names as `null`, sorted last. *(test)*
15. On production: the Railway log shows no Gmail configuration warnings; manual checks 1-16 pass at 375 px and on desktop, including the coexistence checks (3, 13). *(deployed)*
16. **Parity gate** (F§6.3): on the new app the tester completes a real service end to end — any-date readings, hymns with AI picks and exclusion, liturgy cards, both Word downloads, bulletin email from their own Gmail, save, reload from the archive, edit, delete — and a service saved in React opens correctly in Streamlit. Then the switchover banner PR into `streamlit-frozen` is merged ("Services are now built at https://worship-service-builder.vercel.app — use Streamlit only for Settings until they move.") and the tester has the link. *(deployed)*

---

## Risks and open questions

**Open questions (owner to check; not product decisions)**

1. **Google consent-screen publishing status.** If the OAuth consent screen is External and in **Testing**, Google expires refresh tokens after 7 days for any scope beyond basic profile, so the tester would need to reconnect about weekly (the flow-D reconnect path handles it, but it is friction). Options: move the app to "In production" (unverified-app warning screen; `gmail.send` is a sensitive scope and full verification is a separate process), or accept weekly reconnects. Owner to look up the current status in Google Cloud Console → OAuth consent screen before the parity gate.
2. **Which Google client Streamlit uses.** Railway must reuse it (see Data and migrations). If Streamlit's client is shared with Supabase login, that is fine; just add the redirect URIs to it. Confirm the client id from Streamlit Cloud's secrets before setting Railway.

**Risks**

3. **Authorized domains.** Google may refuse the new redirect URI until `worship-service-builder.vercel.app` is listed under the consent screen's authorized domains; because `vercel.app` is a public suffix, that may need Search Console ownership verification of the subdomain (a verification file or meta tag served by the Next app). Fallback: a custom domain the owner controls. Discover this in ops step 1, before merging.
4. **Tester's existing contacts may fail the new validation** (for example a row holding "a@x.org, b@x.org", which Streamlit's single To header happened to accept). Manual check 14 runs before the gate; until 6a, a bad contact is fixed by deleting and re-adding it in Streamlit Settings (Streamlit cannot edit contacts), which is what the error message says.
5. **BCC through the Gmail API** relies on Gmail honoring the `Bcc` header in a raw message and stripping it from delivered copies (documented behavior). Manual check 8 verifies it on the tester's account before the gate.
6. **Uncertain sends.** When Gmail may have sent the email but didn't confirm it (send read timeout, a dropped connection after the request was written, or a Gmail 5xx), the answer is stored under the request's Idempotency-Key, so retries with the same key (client timeout, lost connection, a second tap) replay "check your Gmail Sent folder" instead of sending again; only the explicit **Send again anyway** sends a new copy. What remains: a Railway restart or redeploy between a send and its retry loses the in-memory store (F§1.6), and a user who taps **Send again anyway** without checking can get a duplicate. Acceptable for one tester; revisit with the Postgres-backed store if `--workers` ever exceeds 1.
7. **Callback URL in Vercel request logs.** `/gmail/callback?code=…&state=…` appears in Vercel's request logs. The code is single-use, expires in minutes, and is useless without the client secret held on Railway; the state is single-use. Accepted.
8. **Frozen Streamlit behavior** (disconnect on any 400/401, all recipients in To, plaintext tokens) persists until slice 7 (F§6.2, F§6.4).
9. **Railway request timeout** must exceed the 45 s worst case of `/bulletin-emails`; the ops slice confirms it exceeds 120 s (F§1.8).
10. **Cross-spec updates this spec depends on.** 6a must swap `MALFORMED_CONTACT_HINT` (with a test asserting the new text) and narrow the `LegacySettingsNote` text; 6b removes the note; slice 7 deletes `get_contacts_for_display` and its backend copy check catches any "current app" text left in backend strings (hand-off rows). Otherwise, after Streamlit is retired, a send with a malformed contact would point admins to an app that no longer exists.
11. **Google OAuth client secret in two places** (Streamlit Cloud and Railway) until slice 7 rotates it (hand-off).
