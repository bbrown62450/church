# Slice 6b: Settings for members, invites, ownership and the danger zone — Design

**Status:** Draft  **Depends on:** 1 (6b-1 backend and `/join`); 5b (settings layout, for the 6b-2 UI PR); coordinates with 6a  **Size:** M

**Delivery:** two PRs.
- **6b-1 (backend)** may merge any time after slice 1 (F §7.1): `require_owner`, the members, invites, transfer, leave and delete routes, `role_policy`, `0006_invites_integrity`, `check_integrity.py`, and the `streamlit_tests` port and ledger.
- **6b-2 (UI)** merges after 5b: the two pages, the nav entries, the `LegacySettingsNote` removal, and the one-owner revision `memberships_one_owner` (its file number follows merge order; see Data and migrations). The index ships with the UI so that there is never a stretch in which ownership can be transferred in neither app.

**Date:** 2026-09-25
**Inputs:**
- Foundations: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, cited as "F §n". This spec follows it and does not restate its conventions.
- Inventory: `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md`, cited as "inv §n". It is the source of truth for current behavior.
- Sibling spec: `docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md`, cited as "6a".
- Owner decisions 5 (roles), 6 (invites), 7 (switchover) and 9 (join or create more churches from the switcher).

---

## Goal

Move the last three Streamlit Settings tabs, **Members**, **Invites** and **Danger zone** (inv §1 G7–G10), into the new app. With 6a this finishes Settings, so the tester never needs Streamlit again (F §6.3, phase D) and slice 7 can retire it.

The slice also makes church membership safe. Today an admin can grant or revoke "owner", transfer can leave a church with no owner, and invites accept any role (inv §4, "Ownership integrity"). After 6b:
- decision 5's role policy is enforced on the server, as pure table-tested rules;
- the database holds at most one owner per church and refuses a second one; the API enforces exactly one, because no API path demotes or removes the owner except a transfer. (The frozen Streamlit app can still leave a church ownerless until slice 7 retires it; `check_integrity.py` finds such churches and the runbook repairs them. See "Compatibility".)
- ownership transfer is atomic;
- invite links are single-use by default, with a "Reusable for 7 days" option and a Copy button (decision 6);
- removing someone revokes the invite links they created, and optionally every live reusable link, so an old link can't undo the removal;
- anyone except the owner can leave a church (and, in an ownerless legacy church, except its last admin).

It also closes F acceptance 19: the role-policy truth table is fully tested, and every `streamlit_tests/` assertion has a new-stack equivalent.

---

## Scope / Out of scope

### In scope

| Inventory item | What 6b does |
|---|---|
| G7 Members (settings.py:314-336; repos/memberships.py:59-108) | `/settings/people`, Members section. Every member sees the list with emails. Admins change roles (member ↔ admin) and remove people, under owner protection. Removal revokes the removed person's invite links, and optionally every live reusable link. |
| G8 Invites (settings.py:338-361; repos/invites.py:40-146) | `/settings/people`, Invites section (admins). Single-use links by default; "Reusable for 7 days"; optional email binding; Copy link; Share on phones; list of pending invites with expiry and creator; revoke with confirmation. |
| G9 Transfer ownership (settings.py:130-133, 367-380) | `/settings/danger`: atomic `POST /church/transfer-ownership`, owner only. |
| G10 Delete church (settings.py:136-138, 382-394; repos/churches.py:55-71) | `/settings/danger`: `DELETE /church` with the typed-name check on the server, owner only. The client leaves the church cleanly. |
| New: leave church (decision 5; F §1.1) | `POST /church/leave` for anyone except the owner. The last admin of an ownerless legacy church can't leave either. |
| F §1.2: `require_owner` | Added to `backend/api/deps.py`. |
| F §3.5: `0006_invites_integrity` (6b-1) | CHECK on invite roles; partial unique index for pending email invites, after a duplicate pre-check. |
| F §3.5: `memberships_one_owner` (6b-2; next free file number at merge) | A one-owner-per-church partial unique index, in its own revision that ships with the UI PR (explained under Data and migrations). |
| 5b hand-off (5b "Hand-offs", 6b row) | Adds People and Danger zone to `SETTINGS_SECTIONS` in `src/components/settings/sections.ts`, and **deletes `LegacySettingsNote`** (`legacy-settings-note.tsx` and its use in the settings layout), since nothing is managed in the old app any more. |
| F §6.2: one-owner data check and repair runbook | `repos/integrity.py`, `backend/scripts/check_integrity.py`, Postgres concurrency tests, and a runbook in `backend/migrations/README.md`. |
| F §5.1, §7.2: the rest of the `streamlit_tests` port | A ledger test that maps every Streamlit test to its new equivalent (see Testing). |
| F §7.4 rows: ownership integrity, invite codes as bearer secrets (single-use default), permission parity (member emails), non-atomic writes | Resolved as described below. |
| inv §1 B3: church deletion vs invites | Deletion now revokes every unrevoked invite of the church, including used reusable links. |

### Out of scope (and where it goes)

| Item | Slice |
|---|---|
| `/join` page, `POST /invites/preview`, `POST /invites/accept`, honoring `reusable`, the `0004_invites_reusable` columns | 1 |
| Join or create another church from the switcher (`/welcome`) | 1 |
| Church 403 fallback, `queryClient.clear()` on sign-out, keyed remount on switch | 1 |
| Draft pruning for churches the user no longer belongs to (F §4.6, rule 4) | 2. Its prune runs only once per full load, so 6b's exit also deletes the exited church's draft keys itself (see Frontend, `useExitChurch`). |
| Settings layout, section nav, `/settings/account` | 5b |
| Church profile, contacts, hymns, hymnals, prompts; `forbiddenIsRole` mutation meta | 6a |
| Restoring or hard-purging soft-deleted churches | Not scheduled. Slice 7's checklist decides on a purge (inv §6, "Data"). |
| Deleting `streamlit_tests/` and `streamlit_views/` | 7. The one exception is `streamlit_tests/test_settings_members_invites.py`, which 6b deletes after porting it (F §2.3.7; see Data and migrations). |
| Gmail refresh-token encryption | 7 (F §6.4) |

### Assumed interfaces from other slices

6b is written against these interfaces. If a slice ships something different, the "If it differs" column says what 6b does.

| From | Interface assumed | If it differs |
|---|---|---|
| 1 | `domain_errors` (`InvalidInput`, `NotFound`, `Forbidden`, `Conflict` with `code=`), `db.ids.as_uuid`, the `usecases/` package, `session_scope`, the idempotency store (`Idempotency-Key` accepted on `POST /invites`, F §1.6), `assert_church_isolated`, `test_route_guards.py`, `test_openapi_contract.py`, `test_migrations.py` (it asserts a single Alembic head). Frontend: `useApi()`, the key factory with `["church", id, "members" \| "invites"]`, `renderWithProviders`, `installFakeApi`, and the UI kit (`PageHeader`, `EmptyState`, `ErrorState`, `ConfirmDialog`, `PendingButton`, `touch` button size). | 6b adds any missing key to `keys.ts`. If `test_migrations.py` lacks the single-head assertion, 6b adds it. |
| 1 | `0004_invites_reusable` has shipped: `invites.reusable BOOLEAN NOT NULL DEFAULT false`, `invites.accepted_by UUID NULL`, and existing code-only invites are backfilled `reusable = true`. `Invite` in `db/models.py` maps both columns. | — (hard dependency) |
| 1 | `accept_invite` stamps `accepted_at` (and `accepted_by`) on **every non-reusable** invite it accepts, not only email-bound ones, and rejects a used non-reusable invite with "This invite has already been used." Reusable invites stay usable until they expire or are revoked. Whether it also stamps `accepted_at` on a reusable invite doesn't matter to 6b. | 6b's list filter (`accepted_at IS NULL OR reusable`) works either way. If slice 1 didn't make code-only invites single-use, 6b fixes `accept_invite` and adds the test. |
| 1 | `/join?code=<code>` is the public invite route (F §4.3, D14). Invite codes stay `secrets.token_urlsafe(32)`. | — |
| 1 | `queries/membership.ts`: `useMembershipChanged()` → `async ({selectChurchId}) => void`. Slice 1 ships it for 6b's leave and delete: with `selectChurchId: null` it calls `storeChurchId(null)`, then `await queryClient.fetchQuery({queryKey: keys.me(), staleTime: 0})`, then `router.replace(me.churches.length ? "/" : "/welcome")`. That order stops the `(church)` layout's re-pick from racing the stored id. | If it's missing, 6b adds it to slice 1's module exactly as slice 1 specifies; 6b never writes its own `storeChurchId` or `router.replace` exit steps. |
| 1 | The `(church)` layout re-picks the active church from `["me"]`, excluding the ids in its `excluded` set, and goes to `/welcome` when none are left (F §4.2). `handleAuthErrors` only **emits** `authEvents.churchAccessLost(id)` on a `no_church_access` 403. The layout's subscriber to that event shows the "You no longer have access to {name}." toast, adds the id to `excluded` and invalidates `/me`. | 6b's one change to slice 1 code is in that subscriber (see Frontend, `useExitChurch`). |
| 1 | `api/deps.py`: `require_church` 403s carry `details.reason = "no_church_access"`, the one signal the client uses to detect lost church access. `DomainError` accepts `details=`, and the `DomainError` handler copies it into the body. | — |
| 1 | `src/lib/urls.ts`: `buildInviteUrl(code, origin = window.location.origin)` → `${origin}/join?code=${encodeURIComponent(code)}`, tested as a round trip with `extractInviteCode`. `src/lib/storage.ts`: `removeLocal(key)` (try/catch, a no-op on the server). | 6b uses both as they are and defines neither again. |
| 2 | The draft key is `wsb:draft:{userId}:{churchId}`, with the backup `wsb:draft-corrupt:{userId}:{churchId}`. `DraftProvider` lives inside `BuilderShell`. `prune.ts` runs **once**, when the `(signed-in)` layout first has `/me`, so a later `/me` refetch doesn't prune. | 6b relies only on the two key names: `useExitChurch` deletes both keys itself. |
| 5b | `src/app/(signed-in)/(church)/settings/layout.tsx` renders the Settings header, the role caption, `SettingsNav` (`settings-nav.tsx`) from `SETTINGS_SECTIONS` in `src/components/settings/sections.ts`, and `LegacySettingsNote` (`legacy-settings-note.tsx`, whose text 6a narrows to people and invites). `backend/email_addresses.py::normalize_address(raw) -> str` raises `InvalidAddress` and returns the trimmed address with its case kept. It is the only address validator, with the shared fixture `backend/tests/fixtures/shared/email_addresses.json`. | If 6b-1 lands before 5b, 6b adds `normalize_address` and its fixture exactly as 5b specifies, and 5b reuses them. There is never a second rule. |
| 6a | Admin mutations pass `meta: { forbiddenIsRole: true }`, and `handleAuthErrors` skips the church fallback for them: it toasts the message and invalidates `["church", id, "profile"]`. A `no_church_access` 403 always takes the fallback, with or without the meta. | If 6a hasn't merged, 6b implements the meta exactly as 6a specifies. 6b also needs it on **queries** (`GET /invites` is admin-only), so 6b extends the `QueryCache` handler the same way if 6a changed only the `MutationCache`. |
| 6a | `usecases/church_admin.py` exists with 6a's profile, prompt and contact functions and `require_admin_role(role) -> None` (raises `Forbidden("Only church admins can do this.")`, no `details`, unless the role is owner or admin). `repos.churches.lock_church(session, church_id)` locks the church row. **Every** 6a write (profile, prompts, contacts, `POST`/`DELETE /hymnals`, hymn writes) starts with 6b's `lock_and_read_actor`, and the admin writes then apply `require_admin_role` to the **re-read** role, so a caller demoted or removed after `require_admin` ran gets 403 at write time and nothing is written (6a tests this). A write whose church was soft-deleted after the guard raises `Forbidden("You don't have access to this church.", details={"reason": "no_church_access"})`. 6a adds **no** `email-validator` dependency. | If 6b's backend lands first (allowed after 1, F §7.1), 6b creates `church_admin.py` (with `require_admin_role`), `lock_church` and `lock_and_read_actor`, and 6a extends and imports them. If 6a lands first, 6a creates `lock_church` and `lock_and_read_actor` with the signatures and semantics given here, at `usecases/members.py`, and 6b adds its functions to that module. There is one helper, never two: if it ends up in `church_admin.py` instead, both slices import it from there. |

---

## User experience

Both pages render inside 5b's settings layout. At 375 px they are one column with 16 px gutters; from `md` up the content column is `max-w-3xl` beside the settings nav. Primary actions use `size="touch"`, inputs use `text-base md:text-sm`, and icon buttons have 44 px targets (F §4.8).

**Settings nav:** 6b adds **People** (`/settings/people`) and **Danger zone** (`/settings/danger`) to `SETTINGS_SECTIONS` (5b's `src/components/settings/sections.ts`), in the positions 5b and 6a list: Church, Hymns, Liturgy, Prayers, Rubric, Contacts, **People**, Account, **Danger zone**. Both entries are visible to every role.

**Legacy note:** 6b deletes 5b's `LegacySettingsNote` ("People and invites are still managed in the current app for now." after 6a), because after 6b nothing is managed in the old app.

**Every page:**
- The first load shows `Skeleton` rows shaped like the content.
- A failed query shows `ErrorState` with **Retry**. An error is never shown as an empty list.
- Mutations use `PendingButton`: "Creating…", "Removing…", "Revoking…", "Transferring…", "Leaving…", "Deleting…".
- Server messages appear as toasts. 422 `fields` appear inline under the named input, which gets focus (F §4.8).
- User-supplied text (member names, emails) renders as React text only. Names come from editable Google profile data (inv §1 A2).
- Members show an **initials avatar**. No profile picture URL is loaded for other people, since that URL is user-editable.

### 1. People: `/settings/people`

`PageHeader` "People". Caption: "Everyone in {church} can see this list."

Section order: **Invite someone** (admins only), **Members**, **Pending invites** (admins only).

#### 1a. Invite someone (owner and admins)

A card titled "Invite someone" containing a native form:

| Field | Control | Copy |
|---|---|---|
| Role | Two-option radio group (segmented), default **Member** | Member: "Can build, save and email services, and edit hymns." Admin: "Can also change church settings, invite people and manage members." |
| Email (optional) | `type="email"`, `inputMode="email"`, `autoComplete="off"` | Help: "Only the Google account with this email will be able to use the link." Inline 422: **"Enter a valid email address."** |
| Reusable for 7 days | Checkbox, unchecked | Help: "Let several people join with the same link. Otherwise the link works once." While Email is non-blank, the checkbox is unchecked and disabled, and the help reads **"A link for one email address works once."** |

- **Create invite link** is the primary button, full width on mobile. Each click sends `POST /invites` with a fresh `Idempotency-Key` (F §1.6).
- **On success:**
  - The form resets (Member, blank email, unchecked).
  - An **Invite link ready** panel appears under the button, and focus moves to its **Copy link** button. An `aria-live="polite"` region announces "Invite link created."
- **Errors:**
  - 409 `invite_exists` shows under Email: **"There's already a pending invite for {email}. Copy its link below or revoke it first."**
  - 409 `conflict` shows under Email: **"{email} is already a member of this church."**

**Invite link ready panel:**
- The link, built on the client with slice 1's `buildInviteUrl(code)`, which gives `{window.location.origin}/join?code={code}` (D14), in a read-only monospace input. It shows the full text on focus and scrolls horizontally inside the input only; the page never scrolls sideways.
- **Copy link** (primary):
  - Success: the label shows "Copied ✓" for 2 s and a toast says **"Link copied"**.
  - Failure (clipboard API unavailable or refused): the input text is selected and a toast says **"Couldn't copy. The link is selected; copy it from there."**
- **Share…** (secondary) appears only when `navigator.share` exists (phones). It shares `{title: "Join {church}", text: "You're invited to plan worship with {church}.", url}`. A cancelled share does nothing.
- A summary sentence:
  - single use, no email: **"Anyone who opens this link can join {church} as a {member|admin}. It works once and expires {date, time}."**
  - single use, with email: **"Only {email} can use this link to join {church} as a {member|admin}. It works once and expires {date, time}."**
  - reusable: **"Anyone with this link can join {church} as a {member|admin} until {date, time}. Share it only with people you trust."**
- **Done** hides the panel. The invite stays in Pending invites, where its link can be copied again.

#### 1b. Members (everyone)

- Header "Members ({n})".
- For non-admins, one line under the header: **"Only admins can change roles or remove people. To add someone, ask an admin for an invite link."**
- **Rows**, in server order: owner, then admins, then members, each alphabetical by display name.
  - An initials avatar.
  - The display name (the name, else the email) in medium weight, with a **You** badge on your own row.
  - The email under the name, when a name exists. Long emails wrap (`[overflow-wrap:anywhere]`).
  - A role badge: **Owner**, **Admin** or **Member**.
- **Admin actions:**
  - Rows other than your own and other than the owner's end in a 44 px "More" icon button (`aria-label="Actions for {display name}"`). It opens a `DropdownMenu`:
    - **Make admin** (on a member) or **Make member** (on an admin). It applies immediately with no confirmation, since it is reversible. The badge updates in place with no toast. While it runs, the row's button shows a spinner and is disabled.
    - A separator, then **Remove from church** (destructive). It opens a `ConfirmDialog`:
      - Title: "Remove {display name}?"
      - Body: "{display name} will lose access to {church}. Services they saved stay in the archive."
      - Then the invite sentence. When the Pending invites data has loaded: **"The {k} invite link(s) {display name} created will stop working."**, omitted when k is 0. When it hasn't loaded: **"Any invite links {display name} created will stop working."**
      - Then, when the church has live reusable links that someone other than {display name} created (or when the invites haven't loaded), a checkbox, **checked** by default: **"Also revoke the {r} reusable invite link(s)"** ("Also revoke every reusable invite link" when the count is unknown). Help text: "Anyone with a reusable link, including {display name}, can use it to rejoin until it expires. You can create a new link for everyone else."
      - Confirm: **"Remove member"**. It sends `DELETE /members/{user_id}?revoke_reusable={true|false}`.
      - On success the row disappears, and the revoked invites leave Pending invites; no toast.
  - The owner's row and your own row have no menu. The policy explains why only if someone calls the API directly (see API).
- Server rejections are toasted with the server message, for example **"The owner can't be removed."**
- **Empty state:** none. The list always contains at least the viewer.

#### 1c. Pending invites (owner and admins)

- Header "Pending invites ({n})".
- **Rows**, newest first:
  - Line 1: **"Anyone with the link"** or the bound email; a role badge (Member or Admin); a type badge (**Single use** or **Reusable**).
  - Line 2: "Expires in {relative}" (the full date and time are in `title` and `aria-label`), then " · Created by {name or email}", or " · Created by a former member" when the creator is gone.
  - Actions: **Copy link** (same behavior as the panel) and **Revoke** (destructive). Revoke opens a `ConfirmDialog`:
    - Title: "Revoke this invite?"
    - Body: "The link will stop working. People who already joined stay in the church."
    - Confirm: **"Revoke invite"**.
    - On success the row disappears; no toast.
- **Empty state:** `EmptyState` "No pending invites" / "Create an invite link above to add someone to {church}."
- Used single-use invites, expired invites and revoked invites are not listed.

### 2. Danger zone: `/settings/danger`

`PageHeader` "Danger zone". Non-owners see the info banner **"Only the owner can transfer ownership or delete the church."** (parity, settings.py:365) above a single card, Leave church. The owner sees three cards: Leave church, Transfer ownership, Delete church. Destructive cards have a `border-destructive/40` outline.

#### 2a. Leave church (everyone)

- Title "Leave {church}".
- **Member or admin:**
  - Text: "You'll lose access to {church}'s services, hymns and settings. To come back you'll need a new invite."
  - The button **Leave church…** opens a `ConfirmDialog`:
    - Title: "Leave {church}?"
    - Body: "You'll lose access right away. Your unsaved draft for {church} on this device will be discarded."
    - Confirm: **"Leave church"**.
  - Success:
    - toast **"You left {church}."**;
    - the app switches to another of the user's churches, or to `/welcome` if none remain (see Frontend, `useExitChurch`).
  - Invite links a leaving admin created stay active, since they were sent to other people. Admins see them under Pending invites ("Created by {name}") and can revoke them. Only a **removal** revokes the removed person's links.
- **Owner:** the button is disabled, with an explanation instead:
  - other people exist: **"You're the owner. Transfer ownership below before you leave."**
  - you are the only person: **"You're the only person in {church}. To stop using it, delete the church below."**
- A 409 from the server is toasted with its message (see API).

#### 2b. Transfer ownership (owner)

- Title "Transfer ownership". Text: "The new owner can transfer ownership and delete the church. You'll become an admin."
- **Select "New owner"** (Base UI Select with an `items` map `user_id → "{display name} ({email})"`, placeholder "Choose a person"). It lists every other member, admins first.
- **Transfer ownership…** is disabled until someone is chosen. It opens a `ConfirmDialog`:
  - Title: "Make {display name} the owner?"
  - Body: "{display name} will become the owner of {church} and you'll become an admin. Only the new owner can transfer ownership back."
  - Confirm: **"Transfer ownership"**.
- Success:
  - toast **"Ownership transferred. You are now an admin."** (parity text, settings.py:375);
  - the profile, `/me` and the member list refetch, and the page re-renders in its non-owner form.
- **Nobody else in the church:** the text is **"Invite another member first to transfer ownership."** (parity, settings.py:380) with a link **"Invite someone"** → `/settings/people`.

#### 2c. Delete church (owner)

- Title "Delete {church}". Text: "Deleting {church} removes it for everyone. Pending invite links stop working."
- **Delete church…** (destructive) opens a `ConfirmDialog` that also needs the typed name (F §4.8):
  - Title: "Delete {church}?"
  - Body: "This removes {church} for all {n} people in it. They'll lose access to its services, hymns, contacts and settings. Your unsaved draft for {church} on this device will be discarded. This can't be undone."
  - An input labelled **"Type {church} to confirm"**, with `autoComplete="off"` and `autoCapitalize="off"`.
  - Confirm: **"Delete church"** (destructive). It is enabled only when `typed.trim() === church.name`, an exact, case-sensitive comparison (parity with settings.py:385).
- Success:
  - toast **"Church deleted."**;
  - the same exit as Leave.
- A 422 from the server (for example, the church was renamed in another tab) shows **"Church name did not match."** under the input.

### Losing a role mid-session

If a demotion or transfer happens elsewhere, the next admin or owner action returns 403 ("Only church admins can do this." or "Only the owner can do that."). Those requests carry `meta: { forbiddenIsRole: true }`, so the app toasts the message and invalidates the profile and the member list. The page re-renders for the new role, and the user stays in the church.

If the user was **removed** or the church was **deleted**, their next church request returns 403 with `details.reason = "no_church_access"`, and slice 1's fallback runs: "You no longer have access to {name}.", then another church. This holds whether `require_church` refuses the request or a 6b write finds, under the church lock, that the church or the caller's membership is gone (see Transactions and locking), and whether or not the request carries `forbiddenIsRole`.

---

## API

Conventions: F §1. Every route below is church-scoped: `X-Church-Id` plus `require_church`, either directly or through `require_admin` or `require_owner`. Request models use `extra="forbid"`. Notation follows 6a: `field?` may be omitted, `T?` may be null, `str(n)` is a string of at most n characters.

### Routes

| Method | Path | Guard | Request | Response | Errors (status `code` "message") |
|---|---|---|---|---|---|
| GET | `/members` | church | – | 200 `MemberListOut` | 403 `forbidden` (not a member) |
| PATCH | `/members/{user_id}` | admin + policy | `RoleChangeIn` | 200 `MemberOut` | 403 `forbidden` "Only church admins can do this." / "You can't change your own role." / "The owner's role can't be changed."; 404 `not_found` "Member not found."; 422 `invalid_request` (`role` not `member`/`admin` → `fields.role` "Not a valid value."; malformed `user_id`) |
| DELETE | `/members/{user_id}` | admin + policy | query `revoke_reusable: bool = false` | 200 `{removed: true, revoked_invites: int}` | 403 `forbidden` "Only church admins can do this." / "To leave this church, use Leave church in Danger zone." / "The owner can't be removed."; 404 "Member not found."; 422 malformed id or a non-boolean `revoke_reusable` |
| GET | `/invites` | admin | – | 200 `InviteListOut`; header `Cache-Control: no-store` | 403 "Only church admins can do this." |
| POST | `/invites` | admin | `InviteCreateIn`; optional `Idempotency-Key` | 201 `InviteOut`; header `Cache-Control: no-store` | 403; 409 `invite_exists` "There's already a pending invite for {email}. Copy its link below or revoke it first."; 409 `conflict` "{email} is already a member of this church."; 422 `invalid_request` `fields.email` "Enter a valid email address." / `fields.reusable` "A link for one email address works once." / `fields.role` "Not a valid value."; 422 `idempotency_mismatch` |
| DELETE | `/invites/{invite_id}` | admin | – | 200 `{revoked: true}` | 403; 404 "Invite not found."; 422 malformed id |
| POST | `/church/transfer-ownership` | owner | `TransferOwnershipIn` | 200 `MemberListOut` (after the change) | 403 "Only the owner can do that."; 404 "Member not found."; 422 `fields.user_id` "Choose someone else to be the new owner." |
| POST | `/church/leave` | church | none | 200 `{left: true}` | 403 (not a member); 409 `owner_must_transfer` "Transfer ownership before you leave. If you're the only person in the church, delete it instead."; 409 `last_admin` "You're the last admin. Make someone else an admin before you leave." |
| DELETE | `/church` | owner | `DeleteChurchIn` (JSON body) | 200 `{deleted: true}` | 403 "Only the owner can do that."; 422 `fields.confirm_name` "Church name did not match." |

Notes:
- All codes are already in F §1.5's registry. `last_admin` and `owner_must_transfer` are raised as `Conflict(..., code=...)`. Only `POST /church/leave` can return either.
- **No `last_admin` on `PATCH`/`DELETE /members`.** The actor is an owner or admin (checked again under the lock), self and owner targets are refused first, and only an admin target can be demoted or removed. So at that point the church always has at least two owners/admins: the actor and the target. The repo's `LastAdminError` stays in `set_role` and `remove_membership` as a backstop. If it ever fires, the usecase re-raises it as `Conflict(..., code="last_admin")` with the repo's text, but it is not part of this contract (see Transactions and locking).
- **Every write route** (all of the above except the two GETs) can also return 403 `forbidden` "You don't have access to this church." with `details: {"reason": "no_church_access"}`. That happens when the church was soft-deleted after the guard ran, or when the caller's own membership is gone when it is re-read under the church lock. It is the same body `require_church` returns, so the client takes slice 1's church fallback, with or without `forbiddenIsRole` (6a does the same). Role 403s never carry a `reason`.
- `GET /members` is church-scoped because every member may see the list with emails (decision 5).
- `POST /church/leave` is church-scoped, not admin-scoped, so its 403 means "no longer a member", and the church fallback is correct for it.
- None of these routes is user-scoped, so the `test_route_guards.py` allowlists don't change. 6b adds an `OWNER_ROUTES` assertion there: `DELETE /church` and `POST /church/transfer-ownership` must have `require_owner` in their dependency tree.
- Client timeouts are the 20 s default (F §1.8). Only `POST /invites` takes an `Idempotency-Key`. Remove, leave, transfer and delete are naturally idempotent: a repeat either finds the state already changed or is refused by a guard.
- `revoke_reusable` is a boolean flag in the query string. It carries no personal data or secret, and `DELETE /members` keeps no body.
- `DELETE /church` carries a JSON body, as inv §2.2 proposed. Fetch, Starlette and openapi-typescript all support it. See Risks.
- Invite codes appear only in `GET /invites` and `POST /invites` responses, which are admin-only and `no-store`. They are never in a path, a query string or a log line (F §1.1, §2.5).

### Models (`backend/api/routes/members.py`, `routes/invites.py`, `routes/churches.py`)

```python
Role = Literal["owner", "admin", "member"]
AssignableRole = Literal["member", "admin"]

class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str | None          # a blank stored name is returned as null
    role: Role
    is_me: bool

class MemberListOut(BaseModel):
    items: list[MemberOut]    # owner, admins, members; each by lower(coalesce(nullif(name,''), email)), then user_id

class RoleChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: AssignableRole      # "owner" is not assignable; ownership moves only by transfer

class InviteCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: AssignableRole = "member"
    email: str | None = Field(None, max_length=320)   # blank or null = anyone with the link
    reusable: bool = False

class InviteCreatorOut(BaseModel):
    user_id: uuid.UUID
    name: str | None
    email: str

class InviteOut(BaseModel):
    id: uuid.UUID
    code: str                 # bearer secret; admins only; the client builds /join?code=
    email: str | None
    role: AssignableRole
    reusable: bool
    created_at: datetime      # ISO 8601 with offset
    expires_at: datetime
    created_by: InviteCreatorOut | None   # null when the creator's account is gone

class InviteListOut(BaseModel):
    items: list[InviteOut]    # created_at DESC, id

class TransferOwnershipIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: uuid.UUID

class DeleteChurchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm_name: str = Field(max_length=200)
```

- `RemovedOut {removed: true, revoked_invites: int}` (the number of invites the removal revoked), `{revoked: true}` and `{left: true}` are small models in their route modules. `{deleted: true}` reuses `DeletedOut` from `api/schemas.py`, which 5a defines for `DELETE /services/{id}` (6a reuses it too). 6b adds it there, with the same shape, only if 5a hasn't landed.
- As in inv §2.2, `GET /invites` and `POST /invites` return no `url` (F §1.1).

### Role policy (decision 5)

The rules live in `backend/usecases/role_policy.py` as pure functions. They are the single source for the server and are mirrored on the client from a shared fixture (see Testing).

| Action | Owner | Admin | Member |
|---|---|---|---|
| See members with emails | ✓ | ✓ | ✓ |
| Make a member an admin | ✓ | ✓ | 403 not admin |
| Make an admin a member (someone else) | ✓ | ✓ | 403 not admin |
| Change own role | 403 self | 403 self | 403 not admin |
| Change the owner's role | (is self) 403 self | 403 owner | 403 not admin |
| Assign `owner` through PATCH | 422 | 422 | 403 not admin, or 422 (whichever FastAPI resolves first; not asserted) |
| Remove a member or an admin (also revokes their invites; optionally every live reusable link) | ✓ | ✓ | 403 not admin |
| Remove the owner | (is self) 403 self | 403 owner | 403 not admin |
| Remove self through `/members` | 403 self | 403 self | 403 not admin |
| Leave the church | 409 `owner_must_transfer` | ✓, or 409 `last_admin` if they are the only owner/admin (ownerless legacy church only) | ✓ |
| Transfer ownership to another member | ✓ | 403 owner only | 403 owner only |
| Delete the church | ✓ (name must match) | 403 owner only | 403 owner only |
| List, create or revoke invites (member or admin role) | ✓ | ✓ | 403 not admin |

**Evaluation order** (so each case has one deterministic message). Every write first runs step 0 inside its transaction:
0. lock the church row; the church is gone → 403 `no_church_access`. Re-read the caller's membership; it is gone → 403 `no_church_access`. The re-read role is the `actor_role` for the steps below.
- **Change role:**
  1. guard: the actor is not an owner or admin → 403;
  2. target membership exists, else 404;
  3. target is self → 403;
  4. target is the owner → 403;
  5. new role equals the current role → 200 with no write;
  6. otherwise write.
- **Remove:** guard → 404 → self → owner → write (with the invite revocations).
- **Leave:** owner → 409 `owner_must_transfer`; the only owner/admin → 409 `last_admin`.
- **Transfer:** guard → self → 422; target membership → 404.
- **Delete:** guard → name check → 422.

**The last-admin rule applies only to Leave.** Change role and Remove can't reach it (see the API notes). Leave reaches it only when the leaver is the sole admin of an **ownerless legacy church**, which Streamlit's bug could have produced and can still produce until slice 7 (inv §1 G7; see Compatibility). `check_integrity.py` reports those churches. The repo-level `LastAdminError` stays as a backstop behind the policy.

### Invite semantics

- **TTL:** 7 days for every invite (`create_invite`'s `ttl_days=7`, repos/invites.py:40).
  - Single-use: works once, until it expires.
  - Reusable: many uses until it expires.
- **Email:**
  - Trimmed. Blank → `null`.
  - Validated with 5b's `email_addresses.normalize_address`, the app's only address validator (5b, 6a). `InvalidAddress` → 422 `fields.email` "Enter a valid email address.". No `email-validator` dependency is added.
  - Stored as `normalize_address(value).lower()`, fully lower-cased, because `accept_invite` compares `user.email.strip().lower()` with the stored value (repos/invites.py:97).
- **`reusable` with an email** → 422 `fields.reusable`. An email-bound invite always works once, which matches the `0004` backfill (`reusable = true WHERE email IS NULL`).
- **Already a member:** if an email is given and a user with that lower-cased email is a member of this church → 409 `conflict`. This reveals nothing new: admins already see member emails.
- **Pending duplicate:** a non-revoked, unaccepted, **unexpired** invite for the same church and email → 409 `invite_exists`.
  - Expired invites for that email that are still pending are revoked in the same transaction before the insert. Expiry can't sit in the partial-index predicate (F §3.5).
  - An `IntegrityError` from the partial unique index (a race between two creates) also maps to 409 `invite_exists`.
- **List:** `church_id = :church AND NOT revoked AND expires_at > now() AND (accepted_at IS NULL OR reusable)`, ordered `created_at DESC, id`.
- **Revoke:** looked up by `(id, church_id)`; another church's id → 404. Revoking an invite of this church that is already revoked, used or expired returns 200 (idempotent) and sets `revoked = true`.
- **Removal:** removing a person sets `revoked = true` on every unrevoked invite of this church whose `created_by` is that person: single-use or reusable, email-bound or not, any role. With `revoke_reusable=true` it also revokes every unrevoked reusable invite of the church. Both happen in the removal's transaction. This closes two ways to undo a removal: a reusable link is never stamped (slice 1), so it would let the removed person rejoin until it expires; and a removed admin could redeem an unused invite they created, including an admin-role one. A consumed single-use link is already refused by slice 1's check 4. Leaving doesn't revoke anything (see UX 2a).

---

## Backend changes

### New and changed modules

| Module | Change |
|---|---|
| `backend/api/deps.py` | Add `require_owner(church = Depends(require_church))`: raise `forbidden("Only the owner can do that.")` unless `church.role == "owner"`. The message is parity with settings.py:54. |
| `backend/usecases/role_policy.py` (new) | Pure, DB-free functions over a reachable state (see Testing, "State rules"). They raise `Forbidden` or `InvalidInput`, or `Conflict(code="last_admin" \| "owner_must_transfer")` from `check_leave` only: `check_role_change(*, actor_id, actor_role, target_id, target_role, new_role) -> Literal["change", "noop"]`; `check_remove(*, actor_id, actor_role, target_id, target_role) -> None`; `check_leave(*, role, admin_count) -> None`, where `admin_count` counts owner + admin memberships including the leaver; `check_transfer(*, actor_id, actor_role, target_id) -> None`. They never raise `NotFound`: a missing target is the usecase's 404. All messages are module constants that the tests import. |
| `backend/usecases/members.py` (new; F §2.1) | `list_members(church_id, actor_id) -> list[dict]`; `change_role(church_id, actor_id, target_id, new_role) -> dict`; `remove_member(church_id, actor_id, target_id, *, revoke_reusable=False) -> int` (invites revoked); `list_invites(church_id) -> list[dict]`; `create_invite(church_id, actor_id, *, role, email, reusable) -> dict`; `revoke_invite(church_id, actor_id, invite_id) -> None`; `clean_invite_email(value) -> str \| None`. It also holds `lock_and_read_actor(s, church_id, actor_id) -> str`, which runs step 0 of the evaluation order (steps 1 and 2 under Transactions and locking) and returns the actor's current role. It is the **one shared helper** for every church write in 6a and 6b: 6b's member and invite writes, `church_admin`'s transfer, leave and delete, and 6a's profile, prompts, contacts, hymn and hymnal writes. (6a creates this module with only that function if it lands first; see Assumed interfaces.) Every write takes `actor_id` for that re-read; the invite writes pass the re-read role to `church_admin.require_admin_role` ("Only church admins can do this."). No FastAPI or Streamlit imports. |
| `backend/usecases/church_admin.py` (6a creates it, or 6b creates it if first) | 6b adds `transfer_ownership(church_id, actor_id, target_id) -> list[dict]`, `leave_church(church_id, actor_id) -> None` and `delete_church(church_id, actor_id, confirm_name) -> None`, each starting with `lock_and_read_actor`. If 6b lands first it also creates `require_admin_role(role) -> None` exactly as 6a specifies, and 6a's admin writes reuse it. |
| `backend/api/routes/members.py` (new) | `GET /members`, `PATCH` and `DELETE /members/{user_id}`. |
| `backend/api/routes/invites.py` (created in 1 for accept and preview) | Add `GET /invites`, `POST /invites` and `DELETE /invites/{invite_id}`. Set `Cache-Control: no-store` on the GET and POST responses. |
| `backend/api/routes/churches.py` (created in 1 for `POST /churches`) | Add `DELETE /church`, `POST /church/transfer-ownership` and `POST /church/leave`. FastAPI merges these with `GET`/`PATCH /church` even if those stay in `routes/me.py`. |
| `backend/api/main.py` | Mount `members.router` (the other modules are already mounted). |
| `backend/repos/memberships.py` | See "Repo changes" below. |
| `backend/repos/invites.py` | See "Repo changes" below. |
| `backend/repos/churches.py` | `soft_delete_church(church_id, *, session=None) -> bool` (True if it deleted). Its invite revocation drops the `accepted_at IS NULL` filter, so **every** unrevoked invite of the church is revoked, including used reusable links (inv §1 B3). Add `lock_church(session, church_id) -> Church \| None` if 6a didn't: `select(Church).where(Church.id == cid, Church.deleted_at.is_(None)).with_for_update()`. |
| `backend/repos/integrity.py` (new) | `find_violations(*, session=None) -> list[dict]`. Read-only queries: non-deleted churches whose owner count ≠ 1 (`kind: "owner_count"`, with `church_id`, `owners`); non-deleted churches with no owner or admin (`"no_admin"`); invites whose role is not `member`/`admin` (`"invite_role"`, with `invite_id`); pending email invites duplicated on `(church_id, lower(email))` (`"pending_duplicate"`). It returns ids and counts only: no emails, codes or names. |
| `backend/scripts/check_integrity.py` (new) | CLI. `load_dotenv()` runs in `main()`. It prints one line per violation (kind, church id, count) and "OK: no integrity violations." when there are none. Exit code 1 on any violation. The owner runs it from a laptop against production (see runbook). |
| `backend/db/models.py` | `Invite` table args (6b-1) and `Membership` table args (6b-2), per Data and migrations. |
| `backend/migrations/versions/0006_invites_integrity.py` (new, 6b-1) and `<next free number>_memberships_one_owner.py` (new, 6b-2) | See Data and migrations. |
| `backend/email_addresses.py` | Reused from 5b. Created by 6b-1, exactly as 5b specifies, only if 6b-1 lands first. |
| `backend/migrations/README.md` | Add the "Church integrity (slice 6b)" runbook. |

### Repo changes

**`repos/memberships.py`:**
- `set_role` and `remove_membership` gain `session=None` (F §2.2.3) and coerce ids with `db.ids.as_uuid`. Their `LastAdminError` lock logic stays.
- New `list_member_rows(church_id, *, session=None)` returns `user_id, email, name, role`, ordered as `MemberListOut` documents. The ordering is `CASE role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END`, then `lower(coalesce(nullif(name,''), email))`, then `user_id`. `list_members` stays unchanged for its existing test and callers.
- New `get_member(church_id, user_id, *, session) -> dict | None`.
- New `count_owner_admins(church_id, *, session) -> int`, which reads under the existing admin-row lock.
- New `is_member_email(church_id, email, *, session) -> bool`.

**`repos/invites.py`:**
- New `insert_invite(*, church_id, created_by, role, email, reusable, ttl_days=7, session) -> dict`. It returns the full row, including `created_at`.
- `create_invite` becomes a thin wrapper that returns `insert_invite(...)["code"]`, keeping its callers and tests.
- New `list_active_invites(church_id, *, now, session=None) -> list[dict]`. It filters in SQL (see Invite semantics) and outer-joins `users` for `created_by`. `list_invites` stays for the frozen Streamlit caller and its tests.
- New `find_pending_email_invite(church_id, email, *, now, session)`.
- New `revoke_expired_email_invites(church_id, email, *, now, session) -> int`.
- New `revoke_invites_created_by(church_id, user_id, *, session) -> int`: `UPDATE invites SET revoked = true WHERE church_id = :c AND created_by = :u AND NOT revoked`.
- New `revoke_reusable_invites(church_id, *, session) -> int`: `UPDATE invites SET revoked = true WHERE church_id = :c AND reusable AND NOT revoked`.
- `revoke_invite(invite_id, church_id, *, session=None) -> bool` returns whether it found the invite; the old `None` return was ignored by every caller. It uses `as_uuid`, which fixes the silent no-op for string ids (inv §1 I).

### Transactions and locking

Every write usecase in 6b runs in **one** `session_scope()` in this order (steps 1 and 2 are `lock_and_read_actor`). 6a's writes use the same helper and the same order, with `require_admin_role` as their step-3 policy for the admin writes, so both slices give the same guarantee:
1. `lock_church(s, church_id)`. It returns `None` if the church was soft-deleted since the guard ran. That raises `Forbidden("You don't have access to this church.", details={"reason": "no_church_access"})`, the body `require_church` returns (slice 1) and the one 6a raises in the same case.
2. Re-read the actor's membership **inside** the transaction and apply the policy to that role, not to `ActiveChurch.role`. `require_church` read the role in an earlier transaction. Re-reading it under the lock closes the gap in which, for example, two tabs transfer ownership to different people at once.
   - **Membership gone** (the actor was removed, or left in another tab, after the guard ran): raise the same `no_church_access` `Forbidden`. The caller has lost the church, not a role, so the client must fall back to another church.
   - **Role too low** (for example, demoted to member): the policy's role 403, with no `reason`.
3. Read the target, check the policy, write.

Because every membership, invite, transfer, leave and delete write for a church takes the same church-row lock, they serialize with each other and with 6a's settings merge. On SQLite `with_for_update()` does nothing; the Postgres job covers concurrency (F §5.1).

**Last admin.** `set_role` and `remove_membership` keep their `LastAdminError` under the admin-row lock. Under the policy, `change_role` and `remove_member` can't reach it: the actor is an owner or admin, self and owner targets are refused, and the target is another admin, so there are always at least two. If it fires anyway, the usecase re-raises it as `Conflict(str(e), code="last_admin")` rather than a 500. `leave_church` runs `check_leave` with `count_owner_admins` under the lock before calling `remove_membership`, so its 409 uses its own message.

**Transfer** runs two Core `UPDATE`s **in this order**: demote the actor to `admin`, then promote the target to `owner`. It doesn't rely on ORM attribute changes, because the unit of work orders same-table UPDATEs by primary key, not by assignment order. Promoting first would violate `uq_memberships_one_owner` (from 6b-2 on) for one statement.

**Remove and leave** reuse `remove_membership`'s semantics: `services.created_by` of the departing user is set to NULL in the same transaction, so the history survives the author leaving (repos/memberships.py:75-94). **Remove** also calls `revoke_invites_created_by(church_id, target_id)` and, when `revoke_reusable` is set, `revoke_reusable_invites(church_id)`, in the same transaction, and returns the number of rows revoked (an invite matched by both is counted once). Leave revokes nothing.

**Delete** calls `soft_delete_church(church_id, session=s)`, which sets `deleted_at` and revokes invites. Nothing is hard-deleted.

### Domain functions reused

- `repos.memberships.set_role`, `remove_membership` and `_lock_admin_user_ids` (15-26, 59-94): last-admin enforcement under a row lock.
- `repos.invites._normalize_email`, `_as_utc` and `secrets.token_urlsafe(32)`: codes of at least 128 bits (40-55).
- `repos.churches.soft_delete_church` (55-71).
- `tenancy.is_admin` (18-19) and `validate_active_church`, through the guards.

### Streamlit coupling removed

| Streamlit location | Replacement |
|---|---|
| `NotAuthorizedError`, `_require_admin` / `_require_owner` (settings.py:33-55). `get_role` doesn't exclude soft-deleted churches (inv §1 G1). | Route guards (`require_admin`, `require_owner`), plus a role re-read under the church lock that excludes deleted churches. |
| `apply_role_change`, `apply_remove_member` (110-117): any admin could set any role, including owner, on anyone, including the owner | `usecases.members.change_role` / `remove_member` with `role_policy` |
| `do_create_invite`, `do_revoke_invite` (120-127): no role validation; silent no-op for another church | `usecases.members.create_invite` / `revoke_invite`: `AssignableRole`, email validation, 409 mapping, 404 for other churches |
| `transfer_ownership` (130-133): two non-atomic `set_role` calls; target not checked | `usecases.church_admin.transfer_ownership`: one transaction, target must be a current member other than the caller |
| `delete_this_church` plus the render-only name check (136-138, 383-394) | `usecases.church_admin.delete_church`: the name check is on the server |
| `LastAdminError` shown with `st.error(str(e))` | The policy refuses self and owner targets first, so change role and remove no longer reach it; it stays a repo backstop, re-raised as `Conflict(str(e), code="last_admin")` if it ever fires (inv §3: `LastAdminError` → 409). The reachable last-admin case is now leave's `check_leave` 409. |
| `st.session_state.pop("active_church_id")` after delete (388), leaving the old church's cached state | Client `useExitChurch` on top of slice 1's `useMembershipChanged` (see Frontend) |

Per F §2.3.2 nothing is re-exported from `streamlit_views/settings.py`, and the frozen file is not edited on `main` (F §6.1).

### Tenancy and data access

- Every usecase takes `church_id` from `ActiveChurch.id` only. The models forbid extra fields, so a smuggled `church_id` in a body is a 422.
- `user_id` in `/members/{user_id}` and the transfer body is looked up as a **membership of this church** (`WHERE church_id = :church AND user_id = :id`). A user who exists only in another church → 404 "Member not found." (F §1.2, rule 2). `repos.users.get_user` / `get_user_by_email` are never used, so no global user lookup is exposed (inv §1 I).
- `invite_id` is looked up with the church. Another church's id → 404.
- `is_member_email` is scoped to this church's memberships.
- Logging:
  - Invite creation logs `invite_id`, `role`, `reusable` and `email_bound` only; never the code or the email.
  - Role changes log actor id, target id, old role and new role.
  - Remove logs actor id, target id and the revoked-invite count.
  - Transfer, leave and delete log the ids.

---

## Data and migrations

### Alembic revision `0006_invites_integrity` (6b-1)

**Revision chain** (F §3.5): `0001`–`0004` (slice 1), `0005_services_extras` with `ix_services_church_date` (5a), `0006_invites_integrity` (6b-1, this revision), `memberships_one_owner` (6b-2, below), then slice 7's `normalize_legacy_data`, `contract_after_cutover` and `encrypt_gmail_tokens`. Revision names are fixed; **file numbers follow merge order**. `down_revision` is the Alembic head on `main` when 6b-1 merges, never a hard-coded predecessor: `0005_services_extras` if 5a merged first (the expected order), otherwise `0004_invites_reusable`. In the second case this file keeps `0006` and 5a becomes `0007_services_extras` on top of it during its rebase. `test_migrations.py`'s single-head assertion enforces the chain: a wrong or duplicate `down_revision` fails CI.

**Upgrade**, in order. On SQLite the DDL runs through batch mode, since `env.py` sets `render_as_batch=True`.

1. **Invite-role repair, then assertion** (F §6.2 "fixes such rows to `admin` first"; F §3.4 "assert before CHECK"):
   - `UPDATE invites SET role = 'admin', revoked = true WHERE role NOT IN ('member','admin')`. The migration logs the count. Such an invite could only have been created by a direct call, and it would have granted a second owner, so it is also revoked.
   - Then it asserts that no row violates the rule and raises `RuntimeError` naming the count if one does.
   - The frozen Streamlit form offers only member/admin (settings.py:344), so no new violating row can appear.
2. **Pending-duplicate assertion** (before the index in step 4, so a duplicate fails with the runbook message rather than a raw database error):
   ```sql
   SELECT church_id, lower(email), count(*) FROM invites
   WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
   GROUP BY church_id, lower(email) HAVING count(*) > 1
   ```
   If this returns any rows, raise `RuntimeError("0006: {n} (church, email) pair(s) have more than one pending invite: {church ids}. Follow 'Church integrity' in backend/migrations/README.md, then redeploy.")`. The message names church ids only, never emails. Today's exact-case `uq_invites_church_email` and the lower-casing in `create_invite` make a hit unlikely, but a row written by a direct call could still exist.
3. Drop the unique constraint `uq_invites_church_email`.
4. Create the unique index `uq_invites_pending_email` on `invites (church_id, lower(email))` `WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL`. It uses the same predicate for Postgres (`postgresql_where`) and SQLite (`sqlite_where`).
5. Create the check constraint `ck_invites_role`: `role IN ('member','admin')`.

**Downgrade**, in order:
1. Drop `ck_invites_role` and `uq_invites_pending_email`.
2. Check for duplicate `(church_id, email)` pairs with a non-null email. Re-inviting after a revoke creates such pairs legitimately. If any exist, raise `RuntimeError("Cannot restore uq_invites_church_email: {n} (church, email) pairs have more than one invite. Delete the revoked or accepted duplicates first.")`. Otherwise recreate `uq_invites_church_email`.
3. The step-1 role repair is not reversed. It is data-only and safe, and this is documented in the revision docstring.

### Alembic revision `memberships_one_owner` (6b-2; F §3.5)

It ships **with the UI PR, not with 6b-1**. The index breaks Streamlit's transfer and grant-owner (see Compatibility). 6b-1 may deploy long before the People and Danger zone pages exist (after slice 1, while 5b is not yet merged), and during that gap transfer would work in neither app. The file takes the next free number when 6b-2 merges (for example `0007_memberships_one_owner.py` after `0005` and `0006`), and its `down_revision` is the Alembic head on `main` then. Specs and tests refer to it by name only. 6b-2 merges after 5b, so it always comes after 5a's and 6b-1's revisions, and it is the head when slice 7 starts. Slice 7's revisions, `normalize_legacy_data`, `contract_after_cutover` and `encrypt_gmail_tokens`, follow it, each numbered after the head at its merge; the single-head assertion enforces the chain.

**Upgrade:**
1. **Owner assertion:**
   ```sql
   SELECT church_id, count(*) FROM memberships WHERE role = 'owner'
   GROUP BY church_id HAVING count(*) > 1
   ```
   If this returns any rows, raise `RuntimeError("one_owner: {n} church(es) have more than one owner: {ids}. Follow 'Church integrity' in backend/migrations/README.md, then redeploy.")`. There is no automatic repair: which owner to keep is a human decision.
2. Create the unique index `uq_memberships_one_owner` on `memberships (church_id)` `WHERE role = 'owner'`. It enforces "at most one owner" in the database. The policy never demotes or removes the owner except through a transfer, so the **API** keeps exactly one. It can't stop the frozen app from leaving a church with none (see Compatibility). F §3.4 allows adding an index before slice 7.

**Downgrade:** drop `uq_memberships_one_owner`.

**Models** (`db/models.py`) must match the migrations so that `compare_metadata` stays empty:
- `Invite.__table_args__` (6b-1):
  - drop `UniqueConstraint("church_id","email")`;
  - add `CheckConstraint("role IN ('member','admin')", name="ck_invites_role")`;
  - add `Index("uq_invites_pending_email", "church_id", func.lower(column("email")), unique=True, postgresql_where=…, sqlite_where=…)`;
  - fix the misleading comment at line 84.
- `Membership.__table_args__` (6b-2): add `Index("uq_memberships_one_owner", "church_id", unique=True, postgresql_where=text("role = 'owner'"), sqlite_where=text("role = 'owner'"))`.
- Test fixtures keep `create_all`, so SQLite tests get each index once its PR has merged.
- If Alembic's autogenerate warns about, or can't compare, the expression index, `env.py`'s `include_object` skips `uq_invites_pending_email` by name. `test_migrations.py` then asserts the index exists through the inspector (see Risks).

### Compatibility with the frozen Streamlit app (F §6.2)

**Reads:** no column changes. Streamlit's `Invite` model doesn't map `reusable` or `accepted_by`, which is fine (F §6.2).

**Invite inserts from Streamlit:**
- still pass the CHECK, because its form offers only member/admin;
- an email with a live pending invite still raises `IntegrityError`, as today;
- re-inviting after a revoke or an acceptance now **succeeds** where it used to fail.

**Streamlit "Transfer ownership"** calls `set_role(new, "owner")` before demoting the caller (settings.py:132-133). From 6b-2 on, `uq_memberships_one_owner` makes the first statement fail with an `IntegrityError`; its transaction rolls back and **nothing changes**. Streamlit shows a traceback. Between 6b-1 and 6b-2 (no index yet) it keeps working as it does today.

**Streamlit's owner role option** (settings.py:317): from 6b-2 on, granting "owner" to a second person fails the same safe way. This closes the known gap "Streamlit still lets an admin grant owner" (F §6.2) at the database level.

Both failures are accepted:
- they start only when 6b-2 ships the People and Danger zone pages, and from then on the tester manages people only in the new app (F §6.3, phase D); slice 7 follows;
- the failures change no data, which is what the freeze policy (data-safety only) asks for.

**Streamlit can still leave a church ownerless** (inv §1 G7, verified). Its role select offers member/admin/owner on every row except the caller's own (settings.py:317-336). `set_role` and `remove_membership` check only for the last owner/admin (repos/memberships.py:59-94). So an admin can demote or remove the owner while another admin remains. The one-owner index stops a second owner, not a missing one. The new app can't repair an ownerless church: `owner` isn't assignable, and transfer and delete need the owner. In such a church the new app still works for admins; Transfer and Delete are unavailable, and the sole admin can't leave (409 `last_admin`). Mitigations:
- after 6b-2 the tester uses only the new app for people (manual check 10 says not to touch Streamlit's role select);
- `check_integrity.py` runs after each 6b deploy and **again right before slice 7 retires Streamlit**. Any `owner_count` 0 hit is fixed with runbook step 4 (see below).

**Streamlit delete church** still works: `soft_delete_church` is Streamlit's own frozen copy. Its narrower invite revocation is harmless, because an invite of a deleted church is rejected with "This church is no longer available."

**Streamlit remove member** doesn't revoke the removed person's invites (it runs the frozen `remove_membership`). This is accepted for the overlap: after 6b-2 people are managed only in the new app.

**Streamlit tests:** `streamlit_tests/test_settings_members_invites.py::test_owner_only_transfer_and_delete` breaks under the one-owner index, because it runs Streamlit's two-step transfer. Per F §2.3.7, 6b-1 ports all four of that file's tests (see Testing) and **deletes the file**, so it is gone before 6b-2 adds the index. No other Streamlit test touches owners.

### Church integrity runbook (added to `backend/migrations/README.md`)

1. **When to run it:** before merging 6b-1, before merging 6b-2, after each of their deploys, and **right before slice 7 retires Streamlit** (the frozen app can make a church ownerless until then; see Compatibility). Run `python backend/scripts/check_integrity.py` from a laptop with the production `DATABASE_URL`. It is read-only. Record the output in the PR, or in slice 7's checklist for the last run.
2. **Duplicate pending email invites** (`pending_duplicate`; `0006` refuses to run over them): keep the newest pending invite per church and email, and revoke the rest:
   ```sql
   UPDATE invites SET revoked = true
   WHERE id IN (
     SELECT id FROM (
       SELECT id, row_number() OVER (
         PARTITION BY church_id, lower(email) ORDER BY created_at DESC, id DESC) AS rn
       FROM invites
       WHERE email IS NOT NULL AND NOT revoked AND accepted_at IS NULL
     ) ranked WHERE rn > 1
   );
   ```
3. **More than one owner** in a church (the one-owner revision refuses to run over it): agree with the tester who keeps ownership, then
   ```sql
   UPDATE memberships SET role = 'admin'
   WHERE church_id = :c AND role = 'owner' AND user_id <> :keep;
   ```
4. **No owner** (`owner_count` 0): pick an existing admin with the tester, then
   ```sql
   UPDATE memberships SET role = 'owner'
   WHERE church_id = :c AND user_id = :new_owner;
   ```
   If the church has no admin either (`no_admin`), pick any member.
5. **Invalid invite roles** need nothing: `0006` repairs them.
6. Re-run the check until it prints "OK: no integrity violations.", then merge. Railway's pre-deploy runs `alembic upgrade head` (F §3.3).
7. After the deploy, run the check once more.
8. **Rollback:** `alembic downgrade -1` (once per revision to undo). If `0006`'s downgrade refuses because of duplicate email invites, delete the revoked or accepted duplicates it names, then retry.

### Other data notes

- No change to `memberships.role`, whose CHECK already exists; no backfill; no JSON shape change.
- `services.created_by` is nulled on remove and leave, as today.
- Remove sets `invites.revoked = true` on the removed person's invites (and, if asked, on every reusable one). Nothing is deleted.
- Soft-deleted churches keep all their rows. There is no restore or purge in this slice.

---

## Frontend changes

### Routes (client components under `src/app/(signed-in)/(church)/settings/`)

| Path | Page component |
|---|---|
| `people/page.tsx` | `<PeopleSettingsPage>` |
| `danger/page.tsx` | `<DangerZonePage>` |

### Components

**`src/components/settings/people/`:**
- `PeopleSettingsPage`.
- `CreateInviteForm`, `InviteLinkPanel`.
- `MembersList`, `MemberRow`, `MemberActionsMenu`, `RemoveMemberDialog` (the invite-revocation sentence and the "Also revoke … reusable invite link(s)" checkbox; counts come from `useInvites()` data when it is loaded; see UX 1b).
- `PendingInvitesList`, `InviteRow`, `RevokeInviteDialog`.

**`src/components/settings/danger/`:**
- `DangerZonePage`.
- `LeaveChurchCard`, `TransferOwnershipCard`, `DeleteChurchCard`, `DeleteChurchDialog` (a `ConfirmDialog` with the typed-name input).

**`src/components/app/`:** `CopyLinkButton` (label state, toast, fallback selection); `InitialsAvatar`, which reuses `ui/avatar` with no image.

**`src/components/settings/sections.ts` (5b):** add People and Danger zone to `SETTINGS_SECTIONS` (`settings-nav.tsx` renders them unchanged).

**`src/components/settings/legacy-settings-note.tsx` (5b):** deleted, along with its import and render in `settings/layout.tsx`.

**Base UI components needed:** dropdown-menu, select and avatar (these exist); alert-dialog, badge, checkbox, input, label, radio-group. Generate the missing ones with `npx shadcn@latest add` (F §4.9.1). `Select` gets `items` (F §4.9.3). `DropdownMenuLabel`, if used, goes inside `DropdownMenuGroup` (F §4.9.4).

### Pure helpers (unit-tested)

**`src/lib/urls.ts` (slice 1):** 6b calls slice 1's `buildInviteUrl(code, origin = window.location.origin)` and defines no second version. `window.location.origin` never ends with a slash, so no stripping is needed.

**`src/lib/clipboard.ts`:** `copyText(text) -> Promise<boolean>`. It tries `navigator.clipboard.writeText`, then falls back to a hidden textarea plus `document.execCommand("copy")`. It returns false when both fail and never throws.

**`src/lib/settings/people.ts`:**
- `displayName(member)`: the name trimmed, else the email.
- `initials(member)`.
- `memberActions(actor: {id, role}, target: MemberOut) -> {changeRoleTo: "admin" | "member" | null; canRemove: boolean}`. It mirrors `role_policy`'s change-role and remove checks and is tested against the shared fixture (mapping under Testing, Frontend). It takes no admin count, because those two checks don't use one. It only decides what the UI shows; the server enforces.
- `leaveBlock(role, memberCount) -> "owner_with_others" | "owner_alone" | null`.
- `deleteNameMatches(typed, name) -> boolean`: trimmed, exact, case-sensitive.
- `inviteSummary(invite, churchName, formatDateTime) -> string`: the three sentences in UX 1a.
- `formatExpiry(expiresAtIso, now) -> {relative: string, full: string}`. It uses `Intl.RelativeTimeFormat` and `Intl.DateTimeFormat`. These are full timestamps, so `new Date(iso)` is allowed (F §4.10 bans it only for date-only strings).

**`src/lib/church-exit.ts`:** `useExitChurch() -> (churchId: string) => Promise<void>`, used after a successful leave or delete. It is built on slice 1's `useMembershipChanged` and wraps a pure, unit-tested `runChurchExit({churchId, userId, queryClient, membershipChanged, removeLocal})`. `userId` comes from `useMeContext()`, and `removeLocal` comes from `lib/storage.ts`. It runs, in order:
1. `markChurchExited(churchId)` (`lib/church.ts`; see the layout change below).
2. `await queryClient.cancelQueries({queryKey: ["church", churchId]})`, so no in-flight request for the church completes into a 403.
3. `removeLocal("wsb:draft:{userId}:{churchId}")` and `removeLocal("wsb:draft-corrupt:{userId}:{churchId}")`. This always runs: slice 2's prune runs once per full load, so a `/me` refetch doesn't trigger it. Leave and Delete run from `/settings/danger`, where `BuilderShell` and its `DraftProvider` aren't mounted, so no pending flush can write the key back. A builder open in **another tab** still can; that tab's next church request falls back, and the prune removes the key on the next full load.
4. `await membershipChanged({selectChurchId: null})`. Slice 1's order applies: `storeChurchId(null)`, then fetch `/me` with `staleTime: 0` (the server has already removed the church, so `/me` no longer lists it), then `router.replace("/")`, or `router.replace("/welcome")` when no church remains. The `(church)` layout re-picks from the new `/me` (F §4.2). 6b adds no `storeChurchId` or `router.replace` steps of its own.
5. `queryClient.removeQueries({queryKey: ["church", churchId]})`, after the layout has moved to another church. Slice 1's switch cleanup may already have removed them; removing twice is harmless.

If step 4's `/me` fetch fails, `useExitChurch` toasts "Can't reach the server. Check your connection and try again.", and the layout's normal fallback takes over on the next church request.

**Change to slice 1's `(church)` layout (one line):** its `authEvents.churchAccessLost(id)` subscriber, which is where slice 1 shows the "You no longer have access to {name}." toast, skips the toast when `wasChurchExited(id)`. It still adds the id to `excluded` and invalidates `/me`. So a late `no_church_access` 403 for a church the user just left or deleted re-picks silently instead of showing a confusing toast. `handleAuthErrors` only emits the event and is not changed for this. `markChurchExited(id)` / `wasChurchExited(id)` use a module-level `Map<id, timestamp>` in `lib/church.ts`. A mark lasts 60 s, so a user who later rejoins the church and loses access again still sees the toast.

### Queries and mutations (`src/lib/queries/people.ts`; `church.ts`)

| Hook | Request | Key and invalidation |
|---|---|---|
| `useMembers()` | `GET /members` | `["church", id, "members"]` |
| `useChangeRole()` | `PATCH /members/{user_id}` | meta `forbiddenIsRole`; on success `setQueryData` of the row into `members`, then invalidate `members` |
| `useRemoveMember()` | `DELETE /members/{user_id}?revoke_reusable={bool}` | meta `forbiddenIsRole`; invalidate `members` and `invites` |
| `useInvites()` | `GET /invites` | `["church", id, "invites"]`; `enabled: isAdmin`; meta `forbiddenIsRole`; `staleTime: 0`, because codes are secrets and freshness matters more than caching |
| `useCreateInvite()` | `POST /invites`, with `idempotencyKey: crypto.randomUUID()` per click | meta `forbiddenIsRole`; invalidate `invites` |
| `useRevokeInvite()` | `DELETE /invites/{id}` | meta `forbiddenIsRole`; invalidate `invites` |
| `useTransferOwnership()` (`church.ts`) | `POST /church/transfer-ownership` | meta `forbiddenIsRole`; `setQueryData(members)` from the response; invalidate `["church", id, "profile"]` and `["me"]` |
| `useLeaveChurch()` (`church.ts`) | `POST /church/leave` | no meta, since a 403 here means the church is gone; on success `useExitChurch()(id)` |
| `useDeleteChurch()` (`church.ts`) | `DELETE /church` with `json: {confirm_name}` | meta `forbiddenIsRole` (a `no_church_access` 403 still takes the fallback); on success `useExitChurch()(id)` |

- All hooks use `api.church` (F §4.5). Mutations are not optimistic (F §4.4).
- When a role 403 arrives, the handler invalidates `profile` (6a) and 6b adds `members`.
- Roles come from `useChurch().role`; `isAdmin = role === "owner" || role === "admin"`; the actor id comes from `useMe().user.id`.
- Types are aliases in `src/lib/api/types.ts` (`MemberOut`, `InviteOut`, …) over the generated schema (F §1.11). They are not hand-written.

### Draft store

6b never reads the draft. Leaving or deleting a church deletes that church's draft keys directly (`useExitChurch`, step 3), so the confirm dialogs' "Your unsaved draft … will be discarded" is true at once, without waiting for slice 2's prune. Removing *another* person affects only their browser, where slice 2's prune removes the draft on their next full load.

---

## Behavior changes vs Streamlit

| # | Area | Streamlit today | New app | Why |
|---|---|---|---|---|
| 1 | Granting owner | The role select offered member/admin/owner to any admin (settings.py:317); two owners possible | Role select offers Member/Admin only; `owner` → 422; ownership moves only by transfer; the database refuses a second owner | Decision 5; inv §1 G7, §4 |
| 2 | Owner protection | Admins could demote or remove the owner while another admin remained | 403 "The owner's role can't be changed." / "The owner can't be removed." | Decision 5 |
| 3 | Self changes | UI hid controls on your own row (settings.py:321) but the helpers allowed self changes | Also enforced on the server: 403 for your own role or removal; leaving has its own action | inv §4; F §1.2, rule 3 |
| 4 | Leave church | No way to leave | `POST /church/leave` for everyone except the owner (must transfer) and the last owner/admin | Decision 5 |
| 5 | Transfer | Two non-atomic steps; any user id, even a non-member, left the church ownerless | One transaction, demote then promote; target must be another current member (404 / 422); confirmation | inv §1 G9 |
| 6 | Delete confirmation | Name compared only in the render code | Compared on the server too (422 "Church name did not match."); typed inside a confirm dialog | inv §1 G10, F §4.8 |
| 7 | After delete (and leave) | Popped the active church and kept the old church's cached state | `useExitChurch`: cancel the church's requests, delete its draft keys, then slice 1's `useMembershipChanged` (clear the stored id, refetch `/me`, re-pick or `/welcome`), then drop the church's cache; no "no longer have access" toast | inv §1 G10, A7 |
| 8 | Delete vs invites | Revoked only unaccepted invites | Revokes every unrevoked invite, including used reusable links | inv §1 B3 |
| 9 | Invite roles | Not validated; an owner invite was possible | `member`/`admin` only (Pydantic + DB CHECK); existing bad rows revoked by `0006` | inv §1 G8 |
| 10 | Single use | Code-only invites worked for anyone, any number of times, for 7 days | Single-use by default; "Reusable for 7 days" opt-in; email-bound stays single-use | Decision 6 |
| 11 | Invite link | Raw code "Invite code: `{code}`" (settings.py:350); no link anywhere | `https://<frontend>/join?code=…` with Copy link and, on phones, Share | Decision 6, D14 |
| 12 | Re-inviting an email | Any earlier invite for that email (even revoked or used) caused an `IntegrityError` → error page | Allowed once the earlier one is revoked, used or expired; a live pending one → 409 with guidance | inv §1 G8; F §3.5 |
| 13 | Inviting a member | Allowed, silently consumed on accept | 409 "{email} is already a member of this church." | Clarity |
| 14 | Invite email | No format check | Validated; stored lower-cased | Data quality |
| 15 | Invite list | Code, email or "any", role; used code-only invites stayed listed; no expiry or creator | Type, role, expiry (relative plus full), creator; used single-use, expired and revoked invites hidden | inv §1 G8 |
| 16 | Revoke | No confirmation; another church's id silently ignored | Confirmation; 404 for unknown or other-church ids; idempotent within the church | F §4.8, §1.2 |
| 17 | Role change / remove on a non-member | Silent no-op | 404 "Member not found." | F §1.2 |
| 18 | Remove confirmation | None | `ConfirmDialog` "Remove member", which says which invite links will stop working and offers to revoke reusable links | F §4.8 |
| 19 | Member list order | By email | Owner, admins, members, each by name | Readability |
| 20 | Member list for members | "Only admins can manage members." | "Only admins can change roles or remove people. To add someone, ask an admin for an invite link." | Copy |
| 21 | Invites for members | Tab showed "Only admins can manage invites." | Section hidden; the members note says to ask an admin | Copy |
| 22 | Role-denied message | "You must be an admin to do that." | "Only church admins can do this." (slice 0's `require_admin`); the owner message is unchanged | One message across the API (6a #21) |
| 23 | Success messages | "Ownership transferred…" and "Church deleted." wiped by `st.rerun()` (inv §0, item 3) | Visible toasts | inv §0 |
| 24 | Last admin | Reachable by demoting or removing the owner, or by removing yourself as the sole admin: "Cannot demote/remove the last owner/admin of this church." | Change role and remove can't reach it (self and owner targets are refused first), so the API never returns it there; the repo check stays as a backstop. The only reachable case is the sole admin of an ownerless legacy church trying to leave: 409 "You're the last admin. Make someone else an admin before you leave." | Owner protection |
| 25 | Avatars | None for others | Initials only; no other people's picture URLs are loaded | Privacy |
| 26 | Removal vs invites | A removed person could rejoin with any live code-only invite, and a removed admin with any invite they had created | Removal revokes every invite the removed person created; the dialog offers (checked by default) to revoke every live reusable link too | Decision 5 ("remove members" must stick) |
| 27 | Settings note | 5b's `LegacySettingsNote` pointed to the old app for people and invites | Deleted | Nothing is managed in the old app any more |

Carried over unchanged:
- every member sees every member's name, email and role (decision 5);
- only admins manage invites and members; only the owner transfers or deletes;
- the 7-day invite TTL and 256-bit codes;
- the soft delete;
- the repo's last-admin messages and their row lock (now a backstop behind the policy);
- authorship nulling on removal;
- "Invite another member first to transfer ownership." and "Only the owner can transfer ownership or delete the church."

---

## Testing

### Backend (pytest from the repo root; SQLite unless marked)

**Pure policy: `backend/tests/test_role_policy.py`**

It reads `backend/tests/fixtures/shared/role_policy.json` (F §5.3), which covers the four pure checks. The table's other rows (seeing members, invites, assigning `owner`, delete, and every 404) belong to the usecase and API tests below.

**Row shape:** `{action, actor_role, target?, new_role?, admin_count?, expected, message?, field?}`:
- `action` ∈ `change_role`, `remove`, `leave`, `transfer`.
- `actor_role` ∈ `owner`, `admin`, `member`: the role re-read under the lock.
- `target` (change_role, remove, transfer): `self`, or the role of **another** member: `owner`, `admin` or `member`. There is no `none`: a missing target is a usecase 404, not a policy outcome.
- `new_role` (change_role only): `member` or `admin`. `owner` never reaches the policy; Pydantic refuses it (API test).
- `admin_count` (leave only): owner + admin memberships, including the leaver.
- `expected` and the checks that may return it:
  - `allow` (all four);
  - `noop` (change_role only);
  - `forbidden` (all but leave);
  - `last_admin` and `owner_must_transfer` (leave only);
  - `invalid` (transfer only).
- `message` is present on every `forbidden`, `last_admin`, `owner_must_transfer` and `invalid` row. `field` is `user_id` on the `invalid` row.

**State rules.** The test builds the full product of the values above and drops the unreachable states. It then asserts that the fixture's `(action, actor_role, target, new_role, admin_count)` keys are **exactly** the reachable ones, with none missing and none extra. Unreachable:
- `target: "owner"` when `actor_role` is `owner`: a church has one owner, and the owner acting on the owner is `self`.
- For leave, `admin_count` is drawn from {0, 1, 2}, and 0 is unreachable when the leaver is an owner or admin (they count themselves).

That gives 51 rows:

| Action | Rows | Outcomes |
|---|---|---|
| `change_role` (22) | member actor × 4 targets × 2 roles; admin actor × 4 × 2; owner actor × {self, admin, member} × 2 | member actor → `forbidden` "Only church admins can do this."; `self` → `forbidden` "You can't change your own role."; admin actor on `owner` → `forbidden` "The owner's role can't be changed."; a target already in `new_role` → `noop`; otherwise `allow` |
| `remove` (11) | member × 4; admin × 4; owner × {self, admin, member} | member actor → `forbidden` "Only church admins can do this."; `self` → `forbidden` "To leave this church, use Leave church in Danger zone."; admin on `owner` → `forbidden` "The owner can't be removed."; otherwise `allow` |
| `leave` (7) | owner × {1, 2}; admin × {1, 2}; member × {0, 1, 2} | owner → `owner_must_transfer`; admin with 1 (ownerless legacy church) → `last_admin` "You're the last admin. Make someone else an admin before you leave."; otherwise `allow` |
| `transfer` (11) | member × 4; admin × 4; owner × {self, admin, member} | member or admin actor → `forbidden` "Only the owner can do that."; owner on `self` → `invalid` "Choose someone else to be the new owner." (`field: user_id`); otherwise `allow` |

**Assertions.** For each row the test builds ids (`self` → `target_id == actor_id` and `target_role == actor_role`; otherwise a distinct id) and calls the check. It asserts `"change"` or `None` for `allow`, `"noop"` for `noop`, and otherwise the exception type, `code`, exact message and `field`.

**Usecases: `backend/tests/test_members_usecase.py`**
- `list_members`:
  - ordering: owner, admins, members, then name; a blank name sorts by email; `user_id` breaks ties;
  - `is_me`;
  - a blank name is returned as `None`.
- `change_role`:
  - member → admin and back;
  - self → 403;
  - owner target → 403;
  - an unknown user or another church's member → `NotFound`;
  - same role → no write (row unchanged);
  - in an ownerless church, one admin demotes another → OK. There is no last-admin case here, because the actor remains.
- `change_role` re-reads the actor role in the transaction: an actor demoted to member after the guard ran gets `Forbidden` "Only church admins can do this." with **no** `details`. Simulated by changing the membership between building `ActiveChurch` and calling the usecase.
- **Lost access under the lock** (`test_members_usecase.py` and `test_church_lifecycle.py`, for every write usecase: `change_role`, `remove_member`, `create_invite`, `revoke_invite`, `transfer_ownership`, `leave_church`, `delete_church`):
  - **church deleted after the guard** (a delete racing this write): soft-delete the church after building `ActiveChurch` → `Forbidden` "You don't have access to this church." with `details == {"reason": "no_church_access"}`, and nothing is written;
  - **actor removed after the guard:** delete the actor's membership after building `ActiveChurch` → the same `Forbidden` with the same `details`, and nothing is written.
- `lock_and_read_actor` itself (the helper 6a shares): it returns the role read under the lock, not the guard's (an actor changed from admin to member after building `ActiveChurch` → `"member"`); a soft-deleted church or a missing membership → the `no_church_access` `Forbidden`. 6a's `test_church_admin.py` adds the demoted-admin 403 for its own admin writes.
- `remove_member`:
  - removes, and nulls `services.created_by` (extends `test_remove_member_preserves_content_and_nulls_authorship`);
  - revokes every unrevoked invite the removed user created in this church: single-use, reusable, email-bound and admin-role. It leaves other creators' invites alone, and the removed user's invites in another church. It returns the count;
  - `revoke_reusable=True` also revokes every live reusable invite of the church, whoever created it; the count covers each row once;
  - self → 403 with the Leave message;
  - owner → 403;
  - other church → `NotFound`;
  - in an ownerless church with two admins, one removes the other → OK.
- The repo backstop keeps its own tests: `test_memberships_repo.py::test_remove_last_admin_is_rejected` and `::test_set_role_demote_last_admin_rejected` (unchanged, with `session=None`). A monkeypatched `set_role` raising `LastAdminError` → `change_role` raises `Conflict` `last_admin` with the repo's text, not a 500.
- `clean_invite_email`:
  - `"  Right@X.com "` → `"right@x.com"`;
  - `""` and `None` → `None`;
  - `"no-at"` → "Enter a valid email address.";
  - every row of 5b's `email_addresses.json` fixture: a valid address comes back lower-cased, and an invalid one raises `InvalidInput(field="email")` with that message.
- `create_invite`:
  - default single-use member invite, code ≥ 22 characters, expiry about 7 days;
  - `reusable=True` stored;
  - reusable with an email → `InvalidInput(field="reusable")`;
  - an existing member's email (any case) → `Conflict`;
  - pending duplicate → `invite_exists` with the exact message;
  - re-invite after revoke → OK;
  - re-invite after an email-bound acceptance → OK;
  - re-invite after expiry → OK, and the expired row is now `revoked`.
- `list_invites`:
  - hides revoked, expired and used single-use invites;
  - shows a used reusable invite;
  - newest first;
  - `created_by` becomes `None` after the creator's user row is deleted.
- `revoke_invite`:
  - found → revoked;
  - repeat → OK;
  - other church → `NotFound`;
  - malformed id → `NotFound` via `as_uuid`.
- `repos.invites.create_invite` still returns a code string (the existing tests keep passing).

**Usecases: `backend/tests/test_church_lifecycle.py`**
- `transfer_ownership`:
  - target member → owner, actor → admin, exactly one owner (`find_violations() == []`);
  - target admin → owner;
  - self → `InvalidInput(field="user_id")`;
  - non-member or other church's member → `NotFound` with roles unchanged;
  - actor no longer owner at execution time → `Forbidden("Only the owner can do that.")`.
- `leave_church`:
  - member and admin leave, `services.created_by` is nulled, and the church disappears from `list_user_churches`;
  - an admin who leaves keeps their created invites unrevoked;
  - owner → `owner_must_transfer`, even as the only person;
  - `test_ownerless_sole_admin_cannot_leave`: the sole admin of an ownerless church → `Conflict` `last_admin` with the exact message, and the membership stays (the port of Streamlit's last-admin assertion).
- `delete_church`:
  - `"  Grace  "` matches `"Grace"`;
  - `"grace"` doesn't ("Church name did not match.", `field="confirm_name"`);
  - on success `deleted_at` is set and **every** unrevoked invite is revoked, including a used reusable one;
  - accepting any of those invites then returns "This invite has been revoked."

**Integrity: `backend/tests/test_integrity.py`**
- A clean church → `[]`.
- Zero owners (owner demoted directly in SQL) → `owner_count` and, with no admins, `no_admin`.
- Two owners (inserted directly; once 6b-2 has merged, with `uq_memberships_one_owner` dropped inside the test DB) → `owner_count` 2.
- Duplicate pending email invites (with the index dropped) → `pending_duplicate`, and runbook step 2's SQL (run in the test) leaves only the newest one pending.
- The output contains no email, name or code.
- `check_integrity.main()` exits 1 with violations and 0 with none, printing "OK: no integrity violations.".

**Migrations: `backend/tests/test_migrations.py` (extended)**
- `0006_invites_integrity` (6b-1):
  - after upgrading, the inspector shows `uq_invites_pending_email` and `ck_invites_role`, and no `uq_invites_church_email`;
  - `role='owner'` on an invite fails;
  - two pending invites for `a@x.com` / `A@x.com` in one church fail; a revoked plus a pending one succeed;
  - upgrading from the previous head with an `owner` invite present → that row becomes `admin` and `revoked`;
  - upgrading with two pending invites whose emails differ only in case (inserted with the old constraint) → `RuntimeError` naming the runbook and no email; after runbook step 2's SQL the upgrade succeeds;
  - downgrade with duplicate email invites → `RuntimeError`; without them it restores `uq_invites_church_email`.
- `memberships_one_owner` (6b-2; addressed by name, since its file number follows merge order):
  - after upgrading, the inspector shows `uq_memberships_one_owner`, and a second `role='owner'` membership fails;
  - upgrading with two owners in a church → `RuntimeError` naming the runbook;
  - downgrade drops the index.
- The generic round trip (F §3.3) still passes, and the single-head assertion passes (one head, whatever the merge order of 5a and 6b-1).

**API** (`TestClient` + `jwt_helpers`; `test_api_members.py`, `test_api_invites_admin.py`, `test_api_church_lifecycle.py`)
- **Happy paths:** status, response model, required `X-Church-Id`. `GET /members` for a plain member returns every member with emails.
- **Role denials:**
  - A member gets 403 "Only church admins can do this." on `PATCH`/`DELETE /members/{id}`, `GET`/`POST /invites` and `DELETE /invites/{id}`. The revoke case uses a random uuid, so the 403 comes from the guard before any 404.
  - An admin gets 403 "Only the owner can do that." on `POST /church/transfer-ownership` and `DELETE /church`.
- **Policy messages over HTTP:**
  - an admin PATCHes the owner → 403 "The owner's role can't be changed.";
  - an admin DELETEs the owner → 403 "The owner can't be removed.";
  - PATCH/DELETE on self → 403 with the exact messages;
  - an admin PATCHes `{role: "owner"}` → 422 with `fields.role`;
  - the owner calls `POST /church/leave` → 409 `owner_must_transfer`;
  - the sole admin of an ownerless church calls `POST /church/leave` → 409 `last_admin`;
  - no `PATCH`/`DELETE /members` response is ever 409: the OpenAPI snapshot lists no 409 for those two routes.
- **Lost access under the lock:** a dependency override wraps `require_church`: it runs the real guard, then changes the database before the route body runs.
  - **Church soft-deleted** (a delete racing the write): `PATCH /members/{id}`, `DELETE /members/{id}`, `POST /invites`, `DELETE /invites/{id}`, `POST /church/transfer-ownership`, `POST /church/leave` and `DELETE /church` each return 403 with `details.reason == "no_church_access"` and write nothing.
  - **Actor's membership deleted** (the actor was removed in another request): `PATCH /members/{id}` and `POST /invites` return the same body.
  - A role 403 ("Only church admins can do this.") has no `details.reason`.
- **Removal sticks** (`test_api_members.py`, end to end with slice 1's `POST /invites/accept`):
  - X joins through reusable link L, created by A; A removes X with `?revoke_reusable=true` → `revoked_invites >= 1`; X accepting L → 400 "This invite has been revoked.";
  - the same without the flag → L still works and X can rejoin. This is the documented behavior the dialog warns about;
  - admin Y creates an unused single-use invite and an admin-role invite; A removes Y; Y accepting either → 400 "This invite has been revoked.";
  - a consumed single-use link X used → 400 "This invite has already been used." (slice 1's check 4, unchanged).
- **Cross-church isolation** with `assert_church_isolated` for every route. A non-member gets 403. A member of church A gets 404 for:
  - `PATCH`/`DELETE /members/{id}` with a user who belongs only to church B;
  - `DELETE /invites/{id}` with B's invite (and B's invite stays unrevoked);
  - `POST /church/transfer-ownership` with a B-only user.

  Also:
  - `POST /invites` with `"church_id": "<B>"` in the body → 422, and no invite is created.
  - `DELETE /church` is sent with `X-Church-Id: A` and B's name as `confirm_name`. It returns 422 "Church name did not match.", and B is not deleted.
- **Invites:**
  - `Cache-Control: no-store` on `GET` and `POST /invites`;
  - an `Idempotency-Key` replay of `POST /invites` returns the same `id` and `code`, and exactly one row exists;
  - the same key with a different body → 422 `idempotency_mismatch`;
  - the codes never appear in captured log records (`caplog`).
- **Error contract:** code and exact message for every row of the API table, plus the `fields` keys (`role`, `email`, `reusable`, `user_id`, `confirm_name`). Malformed path ids → 422.
- **End to end with slice 1:**
  - `POST /invites` (single use) → `POST /invites/accept` by user X → 200; by user Y → 400 "This invite has already been used.".
  - A reusable invite accepted by X and Y → both 200, and it is still listed.
  - After `DELETE /church`, the invite is rejected with "This invite has been revoked.", and `GET /me` for the other members no longer lists the church.
- **Guards and contract:**
  - `test_route_guards.py` gains the `OWNER_ROUTES` assertion and passes with no allowlist change;
  - `test_openapi_contract.py` passes with the regenerated snapshot;
  - `test_no_streamlit_in_core.py` covers the new modules through `api.main`.

**Postgres (`@pytest.mark.postgres`, CI Postgres job)**
- Each test runs 20 rounds with a `threading.Barrier` and ends with `find_violations() == []`, except test 3, whose only violation is its own seeded `owner_count` 0 row:
  1. The owner transfers to B and to C at once: exactly one 200, one 403 "Only the owner can do that." (the loser re-reads its role under the lock and is now an admin), one owner.
  2. The owner transfers to B while B leaves: either the transfer then B's 409 `owner_must_transfer`, or B's leave then the transfer's 404. Never zero owners.
  3. In an ownerless church with two admins, each removes the other at once. The church-row lock serializes them: one 200, and one 403 with `details.reason == "no_church_access"` (the loser's own membership is gone when it re-reads it under the lock). Exactly one admin remains.
  4. Two concurrent `POST /invites` for the same email (different idempotency keys): one 201 and one 409 `invite_exists`.
  5. `PATCH /church` (6a) and `PATCH /members/{id}` at once both succeed.
  6. `DELETE /church` and `POST /invites` at once: either the invite is created and then revoked by the delete, or the create gets 403 `no_church_access`. No unrevoked invite of the deleted church remains.
- The `0006` and one-owner upgrade and downgrade behavior above, repeated on Postgres (partial and expression indexes).

**Ported `streamlit_tests` assertions and the ledger**

`test_settings_members_invites.py` (deleted in 6b-1 after porting):

| Streamlit test | New test(s) |
|---|---|
| `test_member_rejected_by_action_helpers` | `test_api_members.py::test_member_cannot_change_role_or_remove`; `test_api_invites_admin.py::test_member_cannot_create_list_or_revoke_invites` |
| `test_remove_last_admin_surfaces_lastadmin_error` | `test_church_lifecycle.py::test_ownerless_sole_admin_cannot_leave` (the reachable last-admin case, 409 `last_admin`); `test_memberships_repo.py::test_remove_last_admin_is_rejected` (the repo backstop, existing); `test_api_members.py::test_owner_cannot_be_removed_even_by_self` (the Streamlit scenario, the owner removing themselves, is now a 403) |
| `test_owner_only_transfer_and_delete` | `test_api_church_lifecycle.py::test_admin_cannot_transfer_or_delete`; `test_church_lifecycle.py::test_transfer_swaps_roles_atomically` |
| `test_admin_can_create_invite` | `test_api_invites_admin.py::test_admin_creates_single_use_invite` (code ≥ 22 characters) |

`backend/tests/test_streamlit_port_ledger.py` (new; deleted in slice 7 with `streamlit_tests/`):
- It holds a dict from every Streamlit test node id to its replacements. A replacement is one of:
  - `"backend/tests/<file>.py::<function>"`;
  - `"frontend/<path>.test.ts(x)::<test title substring>"`;
  - `"DROPPED: <reason>"`.
- It asserts:
  1. Every `def test_*` found by AST in `streamlit_tests/*.py` (plus the four tests of the file deleted here) is a key.
  2. Every backend target function exists (AST).
  3. Every frontend target file exists and contains the title substring.
- Planned mapping. Exact names are filled in at implementation time from what each slice shipped; for any destination that doesn't exist, **6b writes the test**:

| Streamlit tests | Destination | Owner slice |
|---|---|---|
| `test_app_helpers.py::test_capture_query_params_copies_invite_and_church` | `/join` page test: stores the code in `wsb:pendingInviteCode` and removes it from the URL. The `?church=` half is DROPPED (param capture removed, inv §1 A3). | 1 |
| `::test_capture_query_params_ignores_missing_and_keeps_prior` | `/join` test: no code in the URL keeps an earlier stored code | 1 |
| `::test_clear_oauth_query_params_is_targeted_not_blanket` | DROPPED: OAuth params arrive only at `/gmail/callback` and never share a URL with an invite; 5b's callback test covers cleanup | 5b |
| `::test_hymn_display_from_flat_*` (e.g. `::test_hymn_display_from_flat_maps_notion_keys_and_trims`) | slice 3's `HymnOut` mapping test in `test_api_hymns.py`, plus `lib/hymns/filter.test.ts` ("blank titles never listed", "same title stays distinct by id"). Slice 3 **replaces** the helper with `HymnOut`; it doesn't move it (slice 3 Testing, port-ledger table). | 3 |
| `::test_build_title_to_info_lowercases_skips_blank_and_handles_empty` | `filter.test.ts` "blank titles never listed" and the `hymns-step.test.tsx` empty-hymnal case. The title-keyed map is DROPPED (picks by id). | 3 |
| the ops D5 tests added to `test_app_helpers.py` in ops-1 (the `hymn_options_excluding_recent` tests and the D5-flow regression test; exact names from ops-1) | `DROPPED: Streamlit-only fix; intent covered by slice 3 test that exclusion never clears a pick (hymns-step DOM test, AC 12)` | ops (tests), 3 (intent) |
| `test_selectbox_safety.py` (4) | a stale pick shows "Not in your hymnal. Choose a replacement." (3); the draft is per church, so a switch never carries picks (2). `coerce_selectbox_value` is DROPPED. | 2, 3 |
| `test_onboarding.py::test_pick_invite_code_*` (3) | `/welcome` join tab: a typed code wins; the stored code is used when blank; both blank → "Enter an invite code, or open your invite link again." | 1 |
| `::test_create_church_makes_owner_and_seeds_hymnal`, `::test_accept_captured_invite_joins_as_member` | API tests for `POST /churches` and `POST /invites/accept` | 1 |
| `test_streamlit_tenancy.py::test_require_active_church_ignores_forged_session_value` | `test_api_me.py` forged `X-Church-Id` → 403, plus `church.test.ts` fallback | 0/1 |
| `::test_require_active_church_zero_church_returns_none_and_clears` | `(church)` layout test: no churches → `/welcome`, no church-scoped queries left | 1 |
| `::test_set_active_church_writes_selector_keys` | DROPPED: no session keys; `ChurchProvider` tests cover it | 1 |
| `::test_clear_all_church_state_pops_scoped_and_prefixed_keys` | church-switch test: `removeQueries(["church", oldId])` and keyed remount | 1 |
| `::test_church_scoped_keys_cover_known_state` | draft-store test: custom elements and communion live under the per-church key | 2 |
| `test_settings_profile_contacts.py` (4), `test_settings_prompts_translation.py` (3) | 6a's port table | 6a |
| `test_settings_members_invites.py` (4) | the table above | 6b |

### Frontend (Vitest 3)

**Unit (`*.test.ts`):**
- `buildInviteUrl` is slice 1's, with slice 1's tests. 6b adds one case: `buildInviteUrl("abc", "http://localhost:3000")` → `"http://localhost:3000/join?code=abc"`, pinning the `(code, origin)` argument order that 6b's callers use.
- `copyText`: the clipboard path; the fallback path when `writeText` rejects; false when both fail.
- `memberActions`, against `backend/tests/fixtures/shared/role_policy.json`. The test groups the `change_role` and `remove` rows by `(actor_role, target)`, which gives 11 pairs. For each pair it builds `actor = {id: "a", role: actor_role}` and a target `MemberOut` (`self` → the same id and role; otherwise id `"t"` with `role = target`), then asserts:

  | Fixture rows for the pair | `memberActions` output |
  |---|---|
  | one `change_role` row is `allow` (the other is then `noop`) | `changeRoleTo` = the `allow` row's `new_role`; the `noop` role is never offered, since the target already has it |
  | both `change_role` rows are `forbidden` | `changeRoleTo: null` (the action is hidden) |
  | the `remove` row is `allow` | `canRemove: true` |
  | the `remove` row is `forbidden` | `canRemove: false` (hidden) |

  `leave` and `transfer` rows aren't mapped to `memberActions`; the server tests cover them, and `leaveBlock` covers the owner's disabled Leave.
- `leaveBlock`, `deleteNameMatches` (trim, case-sensitive), `inviteSummary` (three variants), `formatExpiry` (days, hours, "less than an hour").
- `runChurchExit`, with a spy QueryClient, a stub `membershipChanged` and a spy `removeLocal`:
  - call order: `markChurchExited` → `cancelQueries(["church", id])` → `removeLocal("wsb:draft:u1:c1")` and `removeLocal("wsb:draft-corrupt:u1:c1")` → `membershipChanged({selectChurchId: null})` → `removeQueries(["church", id])`;
  - it never calls `storeChurchId` or a router itself;
  - the draft keys are removed even when `membershipChanged` rejects, and the rejection is reported (toast).
- `markChurchExited` / `wasChurchExited`: true right after marking, false for another id, false after 60 s (fake timers).
- `handleAuthErrors`: a `forbiddenIsRole` query or mutation 403 without `no_church_access` toasts, invalidates `profile` and `members`, and emits no `churchAccessLost`; a `no_church_access` 403 with the meta still emits it.
- `keys.ts` includes `members` and `invites`.

**DOM (`*.test.tsx`, `renderWithProviders` + `installFakeApi`):**
- **PeopleSettingsPage as a member:**
  - lists members with emails, a You badge and role badges;
  - no action menus, no Invite section, no Pending invites;
  - shows the members note;
  - makes no `GET /invites` request.
- **PeopleSettingsPage as an admin:**
  - menus appear on member and admin rows only, not on the owner's or your own;
  - Make admin sends `PATCH /members/{id}` with body `{"role":"admin"}` and header `X-Church-Id`, and the badge updates;
  - Remove: the dialog says "The 2 invite link(s) {name} created will stop working." when the fake invites include two by that person, and shows "Also revoke the 1 reusable invite link(s)" checked when another creator's reusable link exists. Confirm sends `DELETE /members/{id}?revoke_reusable=true` (or `false` after unchecking), then the row disappears and `invites` refetches. With no other reusable links, the checkbox is absent and the request sends `revoke_reusable=false`;
  - a 403 policy rejection (for example "The owner can't be removed.", with no `reason`) is toasted and invalidates `members`, with no church fallback.
- **Create invite:**
  - sends `POST /invites` with an `Idempotency-Key` header and body `{"role":"member","email":null,"reusable":false}`;
  - the panel shows `http://localhost:3000/join?code=abc` (jsdom origin);
  - Copy link calls the clipboard stub and toasts "Link copied";
  - typing an email disables and unchecks "Reusable for 7 days";
  - a 409 `invite_exists` renders under Email and focuses it;
  - Share appears only when `navigator.share` is stubbed.
- **Pending invites:**
  - badges Single use and Reusable;
  - "Created by a former member" when `created_by` is null;
  - Revoke confirms, then sends DELETE;
  - the empty state.
- **Role loss:** a 403 on `GET /invites` toasts, invalidates the profile and members, and does **not** call the church fallback.
- **Lost access:** a 403 with `details.reason: "no_church_access"` on `PATCH /members/{id}` (which carries `forbiddenIsRole`) **does** emit `churchAccessLost`.
- **ErrorState** with Retry on a 500 from `GET /members`.
- **Settings layout (after 6b):** the nav lists Church, Hymns, Liturgy, Prayers, Rubric, Contacts, People, Account, Danger zone in that order, and no "still managed in the current app" text renders (`LegacySettingsNote` is gone).
- **`(church)` layout, exited church** (slice 1's layout test file): a `churchAccessLost` for an id marked exited adds it to `excluded` and refetches `/me` with **no** toast; an unmarked id still toasts "You no longer have access to {name}.".
- **DangerZonePage as a member:** the owner-only banner plus Leave. Leave confirms and sends `POST /church/leave`. It then toasts "You left {church}.", removes `wsb:draft:{userId}:{churchId}` from the fake storage, calls `useMembershipChanged` with `{selectChurchId: null}` (so `router.replace("/")` runs), and shows no "no longer have access" toast.
- **DangerZonePage as the owner:**
  - Leave is disabled with the correct explanation for "has others" and for "alone";
  - Transfer lists only the other members, stays disabled until one is chosen, confirms, sends a POST with `{"user_id"}`, then toasts "Ownership transferred. You are now an admin." and invalidates `profile` and `["me"]`;
  - the owner alone sees "Invite another member first to transfer ownership." with a link;
  - Delete is disabled for `grace` when the name is `Grace` and enabled for ` Grace `; it sends DELETE with `{"confirm_name":" Grace "}`, then toasts "Church deleted." and runs `useExitChurch`;
  - a 422 renders "Church name did not match." under the input.

### Manual checks (appended to `docs/manual-verification.md`; production Vercel URL; 375 px and desktop)

Use four Google accounts, each in its own browser profile or incognito window: **A** (owner), **B**, **C** and **D**. Checks 2–10 run after 6b-2 is deployed. First, A creates a throwaway church, "6b Check", from the switcher ("Join or create a church…"). Every step below runs in it, never in the tester's real church.

1. **Integrity:**
   - before merging each 6b PR, run `check_integrity.py` against production and record "OK";
   - after each deploy, `alembic current` shows `0006_invites_integrity` (6b-1) or `memberships_one_owner` (6b-2), and the check still prints OK.
2. **Email-bound invite** (B isn't in the church yet):
   - A invites B's email as Admin; C opens that link, signs in, and sees "This invite was issued for a different email address.";
   - A invites B's email again while it is pending → the inline 409;
   - A revokes it, the old link now shows "This invite has been revoked.", and A invites B's email as Admin again → OK;
   - B opens the new link signed out, signs in via `/join`, and joins as an admin; the invite is gone from Pending invites.
3. **Single-use invite:**
   - A creates a Member link, copies it, and pastes it into C's signed-out browser;
   - C signs in via `/join`, joins, and lands in the church;
   - D opens the same link and sees "This invite has already been used.";
   - the invite is gone from Pending invites.
4. **Members as B (admin):**
   - B sees no menu on A's row or their own;
   - B makes C an admin and then a member;
   - B removes C after the confirmation (no reusable links exist yet, so there is no checkbox);
   - C's open app shows "You no longer have access to {church}." on its next action;
   - C reopens the step-3 link and sees "This invite has already been used.".
5. **Reusable invite and removal:**
   - A creates a reusable link; C and D both join with it, and it stays listed with the Reusable badge;
   - A removes D; the dialog shows "Also revoke the 1 reusable invite link(s)", checked; after **Remove member** the link is gone from Pending invites;
   - D reopens the link and sees "This invite has been revoked."
6. **Leave:** C (a member again after step 5) opens the builder and types a sermon title, so a draft exists. C then leaves from Danger zone → the toast "You left 6b Check.", then the app switches to C's other church or `/welcome`, with no "no longer have access" toast. In DevTools → Local Storage, `wsb:draft:{C's user id}:{church id}` is gone.
7. **Streamlit smoke check** (F §6.3), as A in the frozen app, before the transfer below:
   - "6b Check" loads, and the Members tab lists A and B;
   - Streamlit's Transfer ownership to B fails with an error and **changes nothing**: the new app's People page still shows A as Owner and B as Admin;
   - **don't** use Streamlit's role select on A's row: it can still demote the owner (see Compatibility);
   - run `check_integrity.py` once more → OK.
8. **Transfer:** A transfers to B (still an admin) → A's Danger zone shows the non-owner form and the header role says admin; B sees the owner cards.
9. **Delete:** B (now owner) deletes, typing the name with the wrong case (blocked), then the right case → "Church deleted.". B lands on another church or `/welcome` with no "no longer have access" toast. A's app falls back on its next request with "You no longer have access to 6b Check.".
10. **Phone (375 px, iOS Safari):**
    - Share… opens the share sheet;
    - Copy link works;
    - no horizontal scroll on either page;
    - dialogs fit the screen;
    - long emails wrap.

---

## Acceptance criteria

1. `require_owner` exists. `DELETE /church` and `POST /church/transfer-ownership` depend on it, and `test_route_guards.py` asserts that. An admin gets 403 "Only the owner can do that." *(test)*
2. `role_policy.json` holds exactly the 51 reachable states of the four pure checks (change role, remove, leave, transfer), with no unreachable state, and `test_role_policy.py` asserts every row's outcome, code, message and field. The frontend `memberActions` test passes on every change-role and remove pair under the stated mapping. The policy table's other rows (seeing members, invites, assigning `owner`, delete, 404s) are covered by the API tests. *(test; F acceptance 19)*
3. `PATCH /members/{user_id}` assigns only `member` or `admin`. It refuses self and owner targets with the exact 403 messages and returns 404 for non-members and other churches' users. It never returns 409; the repo's `LastAdminError` remains only as a backstop with its own repo tests. *(test)*
4. `DELETE /members/{user_id}` refuses self and the owner with the exact 403 messages and nulls the removed user's `services.created_by`. In the same transaction it revokes every invite the removed user created, and with `revoke_reusable=true` every live reusable invite. A removed member can't rejoin with a reusable link revoked that way, and a removed admin can't redeem any invite they created. *(test)*
5. `POST /church/leave` removes a member or admin, refuses the owner with 409 `owner_must_transfer`, and refuses the sole admin of an ownerless church with 409 `last_admin`. After leaving, the church is gone from `/me`. *(test)*
6. Ownership transfer is one transaction, demote then promote. After any sequence of transfers, including concurrent ones on Postgres, every non-deleted church has exactly one owner (`find_violations() == []`). *(test + Postgres test)*
7. `DELETE /church` requires `confirm_name` equal to the church name after trimming, case-sensitive (422 otherwise). It soft-deletes the church and revokes every unrevoked invite of it. *(test)*
8. `POST /invites` creates single-use invites by default. `reusable: true` makes a link that several users can accept until it expires. Email-bound invites can't be reusable. The role is limited to member/admin at the API and in the database. *(test)*
9. Re-inviting an email works after its earlier invite is revoked, used or expired. A live pending duplicate returns 409 `invite_exists`, and a current member's email returns 409 `conflict`. *(test + Postgres race test)*
10. `GET /invites` lists only live invites (not revoked, not expired, and unused or reusable), newest first, with creator and expiry, and `Cache-Control: no-store`. Invite codes never appear in logs, paths or query strings. *(test)*
11. Every route in this slice passes `assert_church_isolated`: a non-member gets 403, and another church's user or invite id gets 404 with no change to that church. *(test)*
12. `0006_invites_integrity` (6b-1) and `memberships_one_owner` (6b-2) upgrade and downgrade on SQLite and Postgres and leave `alembic check` clean. `0006` repairs invalid invite roles and refuses to run over duplicate pending email invites with the runbook message. The one-owner revision refuses to run over duplicate owners with the runbook message. Production is at `memberships_one_owner` after 6b-2 deploys, and `test_migrations.py` shows a single head. *(CI + deployed)*
13. `check_integrity.py` reports ownerless, multi-owner and adminless churches, bad invite roles and duplicate pending email invites without printing personal data. The runbook has a repair step for each kind. Its production run is recorded before and after each 6b deploy, and slice 7's checklist records one more run right before Streamlit is retired. *(test + manual 1, 7)*
14. The People page shows every member with email to every role, with admin actions only on eligible rows. An admin can create an invite and copy a working `/join?code=` link in at most two taps after creating it. *(DOM test + manual 3)*
15. The Danger zone shows Leave to everyone and Transfer and Delete to the owner only, with the exact copy above. Leave and Delete go through slice 1's `useMembershipChanged({selectChurchId: null})` and end on another church or `/welcome` with no "no longer have access" toast, and the church's `wsb:draft:` and `wsb:draft-corrupt:` keys are removed right away. *(unit + DOM test + manual 6, 9)*
16. A role 403 on an admin or owner action updates the page to the new role without switching churches. *(DOM test)*
17. `streamlit_tests/test_settings_members_invites.py` is deleted, and its four tests have the listed replacements. `test_streamlit_port_ledger.py` passes, mapping every remaining Streamlit test to an existing new test or an explicit DROPPED reason. *(CI; F acceptance 19)*
18. Both pages meet F §4.8: skeletons, ErrorState with Retry, the exact empty states and notices, 44 px targets, and no horizontal scroll at 375 px. *(DOM test + manual 10)*
19. The OpenAPI snapshot and generated types are updated, and CI (backend, backend-postgres, frontend) is green. *(CI)*
20. After 6b-2 deploys, the frozen Streamlit app still loads the church and lists members. Its transfer and grant-owner actions fail without changing data. *(manual 7)*
21. A 6b write whose church was deleted, or whose caller's membership was removed, after the guard ran returns 403 with `details.reason = "no_church_access"` and writes nothing, so the client takes slice 1's church fallback. *(usecase + API + Postgres test)*
22. `SETTINGS_SECTIONS` (`sections.ts`) lists Church, Hymns, Liturgy, Prayers, Rubric, Contacts, People, Account, Danger zone, and `LegacySettingsNote` is deleted. Invite emails are validated only by `email_addresses.normalize_address` and stored lower-cased; `email-validator` is not a dependency. *(DOM test + test)*

---

## Risks and open questions

**Open questions (for the owner)**

None. Decisions 5 and 6 settle the product behavior. Two points follow inv §7 Q8's approved recommendation and are listed only so the owner can object:
- an admin can't change their own role (they can leave, or ask another admin);
- role changes apply without a confirmation, because they are reversible.

**Risks**

1. **The one-owner index breaks Streamlit's transfer and grant-owner.** Both fail closed with no data change. The index ships in its own revision with 6b-2, the PR that brings the People and Danger zone pages, so from that moment the tester manages people only in the new app, and slice 7 follows. Between 6b-1 and 6b-2 Streamlit's transfer keeps working, so there is no stretch in which ownership can be transferred in neither app. If the owner wants the Streamlit actions to keep working until 7, drop the one-owner revision from 6b-2 and rely on `check_integrity.py` plus the policy. Nothing else depends on the index.
2. **Production data may already violate the owner rule, and the frozen app can still break it until slice 7** through Streamlit's G7 bug: two owners before the index, or no owner at any time (see Compatibility). The pre-merge integrity runs and the one-owner revision's refusal to proceed stop a bad deploy. Railway keeps the previous release serving (F §3.3) until the runbook repair is done. The last integrity run, right before slice 7 retires Streamlit, catches an ownerless church created during the overlap.
3. **Expression-index comparison in Alembic.** Some Alembic versions skip, or warn about, expression-based indexes in autogenerate. Mitigation: `include_object` excludes `uq_invites_pending_email` from comparison by name, a targeted `filterwarnings` entry in `test_migrations.py` covers the warning, and an inspector assertion proves the index exists on both dialects.
4. **DELETE with a JSON body.** Fetch, Starlette and the generated types support it, and the browser calls Railway directly. If a proxy is ever found to strip DELETE bodies, add `POST /church/delete` with the same model (additive, F §1.11) and switch the client.
5. **Cross-slice assumptions.** Slice 1 must stamp `accepted_at` on non-reusable invites and ship `useMembershipChanged`. Its `(church)` layout's `churchAccessLost` subscriber needs the one-line exited-church check, and `handleAuthErrors` needs 6a's role meta on queries. 5b must ship `normalize_address`. Each has a stated remedy under Assumed interfaces; the implementer checks them before writing 6b code.
6. **Invite links in logs.** Vercel request logs record `/join?code=…` (F §7.4). Single-use by default and revocation limit the exposure. Reusable links carry the 7-day risk the admin opted into, and the panel says "Share it only with people you trust."
7. **Links built from `window.location.origin`.** An admin who creates an invite from a Vercel preview URL gets a preview link that can't sign in (F §6.4). Accepted: previews are build checks only.
8. **Reusable links outlive a removal unless revoked.** Slice 1 never stamps reusable invites, so a removed person who has one can rejoin until it expires. The Remove dialog offers to revoke them, checked by default. An admin who unchecks it accepts that risk, and the help text says so.
