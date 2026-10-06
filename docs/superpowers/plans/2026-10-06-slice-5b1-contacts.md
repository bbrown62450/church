# Slice 5b-1: the Contacts Page

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first of slice 5b's two PRs (owner's 5b planning answers of 2026-10-06, answer 2): **the Contacts page in Settings.** After it merges, the Settings sections are **Church**, **Bulletin** and **Contacts**. `/settings/contacts` lists the church's saved contacts for every member (the name in bold with the address under it, the address alone when there is no name). Owners and admins add a contact below the list (**Add contact**), change one in a small dialog (**Edit contact**, **Save changes**) and delete one after a confirmation (**Delete contact**); a member sees the list with "Only admins can add or change contacts.". Every address goes through one new rule, `email_addresses.normalize_address`, the rule 5b-2 will send with, so an address saved here can always be emailed; an address already in the church's contacts (in any capitalization) is refused with "That email is already in your contacts.", even when two admins add it at the same moment. Contacts saved in the Streamlit days are kept as they are, and any whose address the new rule would refuse shows "This address doesn't look valid. Edit it." under it: that note is the owner's one-time check of the existing contacts (answer 6), done on the phone in the last task. No Google setup, no emailing yet (5b-2), no migration (Alembic head stays `0007_bulletin_images`), no new package or variable.

**Architecture:** Backend first. `backend/email_addresses.py` (new) holds `normalize_address` and `InvalidAddress`, pinned by the shared fixture `backend/tests/fixtures/shared/email_addresses.json` (run through `normalize_address` here and through `POST /contacts`; 5b-2 adds `POST /bulletin-emails`). `backend/email_contacts.py` (the Streamlit-era repo, kept) gains a `session` parameter on every function, the 5b spec's order (`created_at`, then the name with blank names last, then `id`), a blank name returned as `None`, `get_contact`, `update_contact` and `email_exists` (case-insensitive), and `db.ids.as_uuid`; `get_contacts_for_display` is left alone. `backend/usecases/contacts.py` (new) holds the read (`list_contacts`, each contact with `email_valid`) and the three writes, each in one session that starts with 6a-1's `lock_and_read_actor` and `require_admin_role`, so the duplicate check and the write run under the church-row lock with the caller's role re-read. `backend/api/routes/contacts.py` (new): `GET /contacts` (`require_church`), `POST`, `PATCH /contacts/{contact_id}` and `DELETE` (`require_admin`), with `ContactOut` (5b's model plus `email_valid`), `ContactIn` and `ContactPatchIn`. A Postgres test proves the lock. Frontend: the generated types, `lib/settings/contacts.ts` (the forms' pure rules), `lib/queries/contacts.ts` (`useContacts` and the three mutations on `["church", id, "contacts"]`), `components/settings/contacts-settings-page.tsx` with its route, 6a-1's `LeaveGuard` on the add form, and one more entry in `SETTINGS_SECTIONS`.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy, pytest; Next 16, React 19, TypeScript 5, Base UI (Dialog, AlertDialog), TanStack Query 5, sonner, lucide-react, Vitest 3 with Testing Library.

**Source documents:**
- 5b spec ("B"): `docs/superpowers/specs/2026-09-25-slice-5b-gmail-email-design.md`, read with its **"Amendment 2026-10-06: owner's 5b planning answers"** (binding; it wins where the older text differs). This plan is 5b-1 only: B's `email_addresses.normalize_address`, the shared address fixture, `GET /contacts` and `ContactOut`, the list order, and "Data access and tenancy" for `/contacts`.
- 6a spec ("S"): `docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md`, read with its amendments of 2026-10-05 (Contacts returns with 5b; 5b adds Contacts to 6a-1's Settings shell). From it: UX §4 "Contacts: /settings/contacts", the `POST`/`PATCH`/`DELETE /contacts` API rows, `ContactIn`/`ContactPatchIn`, "Semantics" → Locking and Contacts, and its contacts tests (the Postgres race among them).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.2 (guards), §1.4 (list order), §1.5 (errors), §2.2 (layers), §4.4 (keys and invalidation), §4.8 and §4.9 (forms, 44 px).
- The model plan `docs/superpowers/plans/2026-10-05-slice-6a1-settings-church.md` (format; its `lock_church`, `lock_and_read_actor`, `require_admin_role`, `LeaveGuard` and Settings shell are reused here unchanged).
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `c97d341` = `origin/main` `0018d1c` plus the 6a-1 record `91b0d7b` and the 5b amendment `c97d341`, then this plan's commits; 2026-10-06): backend `1529 passed, 24 skipped`; frontend `759 passed` in 92 files; typecheck and lint clean; Alembic head `0007_bulletin_images` (7 revision files); 4 runbook owner markers. What exists: the `contacts` table (`db/models.py` `Contact`: `id`, `church_id` (cascade), `name` nullable, `email` not null, `created_at`; index `ix_contacts_church_id`; **no** unique constraint); `backend/email_contacts.py` with `list_contacts`, `add_contact`, `delete_contact` and `get_contacts_for_display` (no `session` parameter, its own `_as_uuid`, ordered by `created_at, name`), called by `streamlit_views/settings.py` and `app.py` (frozen) and by `streamlit_tests/test_settings_profile_contacts.py` and `backend/tests/test_email_contacts.py`, both of which pytest still collects; `repos.churches.lock_church`, `usecases.members.lock_and_read_actor`, `usecases.church_admin.require_admin_role` (6a-1); `api.schemas.DeletedOut`; `keys.contacts(id)` = `["church", id, "contacts"]` already in `lib/queries/keys.ts`; `components/app/leave-guard.tsx` (`LeaveGuard`, `DISCARD_TITLE`), `ConfirmDialog`, `EmptyState`, `ErrorState`, `PendingButton`; `SETTINGS_SECTIONS` = Church, Bulletin. **No** `email_addresses.py`, contacts route, contacts usecase, `useContacts` or Contacts page; nothing in the code validates an address today.
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -3`; the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes (T4), so T4 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand.
- No new package, no new variable, no migration.
- Branch `claude/slice-2-plan-4q33le`, at `c97d341` plus this plan's commits (`WIP plan: slice 5b-1 …` and `Plan: slice 5b-1 (the Contacts page)`, and any later plan commit), then T1-T9. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1529 → 1598 passed, 24 → 26 skipped; frontend 759 → 775 in 92 → 94 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 15 and has no em dashes (the specs' lines are taken without theirs); existing copy keeps its own punctuation.
- No church id, real email address, token, key, street address, phone number, database URL or real person's name in any doc, commit, test or record. Tests use the fixtures' "Grace" and `@example.org` / `@example.com` addresses only.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.

### How the file directives below read
As in the 6a-1 plan: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted.

### Baselines and counts
- Starting baselines: backend **1529 passed, 24 skipped**; frontend **759 passed in 92 files**, typecheck and lint clean; Alembic head **`0007_bulletin_images`** (7 revision files; no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new `it(`.

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +33 (`test_email_addresses.py`: 8 valid, 22 invalid and 3 blank cases; `test_no_streamlit_in_core.py` edited) | 1562 passed, 24 skipped | 0 | 759 in 92 |
  | T2 | +5 (`test_email_contacts.py`, 3 → 8) | 1567 passed, 24 skipped | 0 | 759 in 92 |
  | T3 | +18 (`test_usecase_contacts.py`: 2 + 9 parametrized cases and 7 tests) | 1585 passed, 24 skipped | 0 | 759 in 92 |
  | T4 | +13 (`test_api_contacts.py`: 6 parametrized cases and 7 tests) | 1598 passed, 24 skipped | 0 | 759 in 92 |
  | T5 | +2 skipped (`test_contacts_postgres.py`, skipped without `TEST_DATABASE_URL`) | 1598 passed, 26 skipped | 0 | 759 in 92 |
  | T6 | 0 | 1598 passed, 26 skipped | +4 (`contacts.test.ts`) | 763 in 93 |
  | T7 | 0 | 1598 passed, 26 skipped | +11 (`contacts-settings-page.test.tsx`) | 774 in 94 |
  | T8 | 0 | 1598 passed, 26 skipped | +1 (`settings-layout.test.tsx`, two tests edited) | 775 in 94 |
  | T9 | 0 (`test_slice1_docs.py` edited) | 1598 passed, 26 skipped | 0 | 775 in 94 |

- CI `backend-postgres` goes from `24 passed, 1529 deselected` to `26 passed, 1598 deselected` (T5). Locally, without `TEST_DATABASE_URL`, those two tests are among the 26 skipped.

### Layering and code rules (carried)
- `email_addresses.py` and `usecases/contacts.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains both, T1 and T3); the routes are plain `def`s with no SQL and no try/except (F §2.2 rule 1), each one usecase call; the usecase writes through `email_contacts` (no SQL in the usecase).
- Logs carry ids, never an address or a name (F §2.5). This PR adds no log line.
- Pages and components never call `apiFetch`: the queries use `useApi()` (F §4.5).
- Touch targets 44 px below `md`; text wraps at 375 px (an address breaks anywhere, `break-all`); no raw HTML (F §4.8); inputs `text-base md:text-sm` (the kit's `Input` already is).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** is retired (branch `streamlit-frozen`, untouched); merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **The 5b planning answers of 2026-10-06** ("all recommended"; binding; B's amendment): (1) the email dialog's two attachments (5b-2); (2) **two PRs: 5b-1 the Contacts page in Settings with `GET /contacts` and `email_addresses.normalize_address`, no Google setup; 5b-2 the Gmail connection and emailing**; (3) Railway reuses Streamlit's Google client (5b-2); (4) Streamlit is treated as unused: no coexistence work, and `MALFORMED_CONTACT_HINT` reads "An admin can fix it in Settings → Contacts." from the start (5b-2); (5) the wording (5b-2's subject; every em dash in B's copy replaced); (6) **existing contacts are kept, and 5b-1 includes a read-only check the owner runs once to find saved contacts whose address would fail `normalize_address`, so they can be fixed on the new Contacts page** (clarification 13).
5. **The 6a answers of 2026-10-05** (binding, carried): admins change the church, everyone reads (so: everyone reads contacts, admins add, edit and delete, as S says); Contacts returned with 5b, into 6a-1's Settings shell.

**Later, out of scope:** 5b-2 (`/settings/account`, `/gmail/callback`, the `/gmail-connection` routes, the "Email the bulletin" card and dialog, `POST /bulletin-emails`, `dedupe_addresses`, the email dialog's admin-only "Manage contacts" link), 6a-2 (Hymns), 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings moved in), 6b (People, Danger zone), slice 7 (deleting `get_contacts_for_display`).

## Spec clarifications

The owner's answers win over B, S and F; the code wins over all of them where they disagree. **[owner-visible]** items are put to the owner in "Owner questions" (each written as recommended).

1. **[owner-visible] What 5b-1 ships** (answer 2). `email_addresses.normalize_address` and its shared fixture; `GET`, `POST`, `PATCH` and `DELETE /contacts` with the locked, role-re-read writes; the Contacts page and its place in the Settings nav; the check of existing contacts (clarification 13). Not here: anything Gmail or email (5b-2), `dedupe_addresses` (5b-2 adds it with its first caller, the send), the "Manage contacts" link in the email dialog (5b-2 builds the dialog).
2. **[owner-visible] Where Contacts sits** (S "Settings nav"). `SETTINGS_SECTIONS` becomes **Church**, **Bulletin**, **Contacts**: Contacts is appended. The final order (S amendment 2026-09-26) puts Contacts after every page about the church's services (Church, Hymns, Liturgy, Prayers, Rubric) and before People and Account; Bulletin settings is one of those service pages and 6a-3 moves it in among them, so appending keeps Contacts where it will end up and no item moves when 6a-2, 6a-3 and 5b-2 add theirs. Owner question 1.
3. **[owner-visible] The Contacts page, for everyone** (S UX §4). Inside the Settings layout (its `h1` "Settings" and the nav): the heading "Contacts" (an `h2`, as Church's "Church profile") and under it "People you can email the bulletin to. Emailing it from the Review step comes in a later update." (S's caption said "…to from the Review step.", which is not true until 5b-2; 5b-2 sets S's line back; owner question 4). A member also sees "Only admins can add or change contacts." (S's banner). The list (`aria-label="Contacts"`, one row per contact, in the server's order): the name in bold with the address under it in muted text, or the address alone (normal text) when there is no name; addresses break anywhere on a phone. Under an address the send-time rule refuses (`email_valid: false`), in amber text: "This address doesn't look valid. Edit it." for owners and admins, "This address doesn't look valid. An admin can fix it." for members. With no contacts, S's empty states: "No contacts yet" with "Add the people who receive the bulletin, like your church secretary." (admins) or "Ask an admin to add bulletin recipients." (members). The first load shows two skeleton rows; a failed read the usual `ErrorState` with **Retry**.
4. **[owner-visible] Owners and admins** (S UX §4). Each row has two icon buttons, 44 px below `md` (32 px from `md`): a pencil, "Edit {name or address}" to screen readers, and a bin, "Delete {name or address}".
   - **Edit** opens a dialog (a bottom sheet below `md`, as "Add custom element" is): title "Edit contact", the contact's name or address under it, "Name (optional)" and "Email" filled in, **Cancel** and **Save changes** ("Saving…" while pending). Only the fields that changed (trimmed) are sent; nothing changed closes it with no request. Success closes it and the row shows the answer; a 422 or 409 shows under its field in the dialog. Cancel, Escape or a tap outside closes it and discards the edits (clarification 6).
   - **Delete** opens S's `ConfirmDialog`: "Delete {name or address}?", "They won't be offered as a bulletin recipient anymore.", **Delete contact** (red) and **Cancel**. On success the row goes. When the confirmation closes, focus moves to the add form's Name field (after a delete the row and its button are gone).
   - **Add a contact** (an `h3`) below the list, in a bordered box: "Name (optional)", "Email" (`inputMode="email"`, no auto-capitalize, no autocorrect, no spellcheck, `autocomplete="off"`), **Add contact** (full width on a phone, 44 px, "Saving…" while pending). A blank Email says "Email is required." under it at once, with no request. On success the new row appears at the end, the fields clear and focus returns to Name; no toast (S; F §4.8). Owner question 7.
5. **Errors.** A 422 that names `name` or `email`, and a 409 (the address is taken; the body has no `fields`, so the page puts it under Email), show under the field in the error colour (`role="alert"`), mark it `aria-invalid` and focus it; they are not toasted. Editing a field clears its error. A role 403 (an admin demoted meanwhile) toasts "Only church admins can do this." and refetches the church profile, which carries the role, so the page turns into the member's view; a 404 (a contact deleted in another tab) toasts "Contact not found." and refetches the list; a 401 or a lost church toasts nothing more (the app handles them); anything else toasts the server's message.
6. **[owner-visible] The leave guard.** 6a-1's `LeaveGuard` protects the add form while either field holds something (trimmed): a reload or close shows the browser's warning, any in-app link (the Settings sections, the top menu) and "Join or create a church…" ask "Discard unsaved changes?" first. The edit dialog is modal (no link can be reached behind it) and its Cancel discards, so it has no guard of its own. Owner question 8.
7. **`email_addresses.normalize_address`** (B, exactly). `normalize_address(raw: str) -> str` accepts `raw.strip()` when it is at most 254 characters, ASCII only, holds no whitespace, control character or any of `, ; < > " ( ) [ ] \`, has exactly one `@`, a local part of 1-64 characters, and a domain of at least two dot-separated labels, each 1-63 ASCII letters, digits or hyphens not starting or ending with a hyphen, the last at least two letters; it returns the trimmed address with the domain lower-cased (the local part as typed), and raises `InvalidAddress` (a `ValueError`) otherwise. No dependency. The shared fixture `backend/tests/fixtures/shared/email_addresses.json` (`_about`, `valid: [{raw, normalized}]`, `invalid: [...]`) holds 8 valid cases (plain, trimmed with a mixed-case domain, a plus tag, subdomains, an apostrophe, a punycode domain, the shortest, exactly 254 characters) and 22 invalid ones (B's list: no `@`, two `@`, a space, a trailing dot, `a@b`, 255 characters, two addresses with a comma or a semicolon, a header injection with CR LF, `<a@b.com>`, a display name, a quoted local part, `anna@bücher.de`, `josé@…`; and an empty local part, a 65-character local part, an empty label, a label starting with a hyphen, an underscore, a one-letter and an all-digit last label). `test_email_addresses.py` runs every case through `normalize_address` (and each normalized value again: unchanged), `test_api_contacts.py` through `POST /contacts`. The fixtures README is generated by `record_fixtures.py` and lists only the recorded fixtures and `scripture_refs.json`, so it is not edited; the JSON's `_about` documents the file, as `docx_filenames.json`'s does.
8. **The contacts repo** (B "Modules" `email_contacts.py`; S "Changed modules"). `backend/email_contacts.py` stays where it is (the frozen `streamlit_views/settings.py` and `app.py` import it; `streamlit_tests/test_settings_profile_contacts.py`, which pytest still collects, calls it through them). Every function gains a keyword-only `session=None` (a given session is used, else its own `session_scope`), and ids go through `db.ids.as_uuid` (a malformed id is a 404, never a 500; its private `_as_uuid` goes). `list_contacts` orders by `created_at`, then `nullif(trim(name), '') ASC NULLS LAST`, then `id` (B; F §1.4), and every function returns a NULL or blank-after-trim name as `None`. New: `get_contact(contact_id, church_id)`, `update_contact(contact_id, church_id, changes)` (sets only `name` and/or `email`, already cleaned; `None` when the church has no such contact) and `email_exists(church_id, email, *, exclude_id=None)` (`lower(email)` within the church). `add_contact` and `delete_contact` keep their signatures (plus `session`). `get_contacts_for_display` is untouched (slice 7 deletes it); `test_email_contacts.py`'s three tests are kept.
9. **The contacts usecases** (S "Semantics" → Contacts and Locking). In a new `backend/usecases/contacts.py`:
   - `list_contacts(church_id)`: `email_contacts.list_contacts` with `email_valid` added to each (`normalize_address` does not raise).
   - `normalize_email(value)`: S's thin wrapper: `None` or blank → `InvalidInput("Email is required.", field="email")`; `InvalidAddress` → `InvalidInput("Enter a valid email address.", field="email")`; else **what `normalize_address` returns is stored** (B's hand-off: "store what it returns"): trimmed, the domain lower-cased, the local part as typed. S's "case kept" holds for the local part; owner question 5.
   - `clean_name(value)`: trimmed, `""` for none (S: blank is stored as `""`, parity with Streamlit; the list returns it as `None`), and one line: a control character (NUL among them, which Postgres refuses in text), U+2028/U+2029 or U+FFFE/U+FFFF is `InvalidInput("Name can't contain line breaks or control characters.", field="name")` (new; the church name's rule from 6a-1; owner question 6).
   - `add_contact(church_id, actor_id, *, name, email)`, `update_contact(church_id, actor_id, contact_id, changes)`, `delete_contact(church_id, actor_id, contact_id)`: one `session_scope` each; `lock_and_read_actor` then `require_admin_role` (so a demoted admin gets the role 403 and a removed member or a deleted church `no_church_access`, and nothing is written); then, for an edit or a delete, the contact (404 "Contact not found." for an unknown id or another church's, before any field is checked); then the name, then the email; then the duplicate check (`email_exists`, excluding the contact itself on an edit, only when an email is sent) → `Conflict("That email is already in your contacts.")` (409); then the write. An edit's `changes` holds only the fields sent: a `None` or blank name clears it, a `None` or blank email is "Email is required.".
   - Placed in its own module rather than in `usecases/church_admin.py` (S): contacts are their own table with a read every member makes, 5b-2's send reads them, and `church_admin.py` keeps the church row's writes (deviation, clarification 17).
10. **`/contacts`** (B API; S API, Models). `backend/api/routes/contacts.py`, mounted in `create_app()`:
    - `GET /contacts` (`require_church`, every member) → 200 `ContactList {items: ContactOut[]}`. No paging (a small list).
    - `POST /contacts` (`require_admin`) with `ContactIn` → **201** `ContactOut`.
    - `PATCH /contacts/{contact_id}` (`require_admin`) with `ContactPatchIn` → 200 `ContactOut`; only the fields present in the body are passed on (`model_fields_set`).
    - `DELETE /contacts/{contact_id}` (`require_admin`) → 200 `DeletedOut {deleted: true}`.
    - `ContactOut {id, name: str | null, email, email_valid: bool}`: B's model plus `email_valid` (additive; clarification 13). The repo already maps a blank name to `None`, so S's `field_validator` on `name` is not needed.
    - `ContactIn {name?: str(200) | null, email: str(320) = ""}` (`extra="forbid"`; an omitted email reaches the usecase as `""`: "Email is required.", F §1.3); `ContactPatchIn {name?: str(200) | null, email?: str(320) | null}` (`extra="forbid"`).
    - Errors: 401; 403 `forbidden` (a member on a write: "Only church admins can do this."; a non-member: `no_church_access`); 404 `not_found` "Contact not found."; 409 `conflict` "That email is already in your contacts."; 422 `invalid_request` with `fields.email` ("Email is required." / "Enter a valid email address."), `fields.name` (the one-line message), Pydantic's "Too long (max N characters)." and a malformed path id or an unknown body field. No `Idempotency-Key` and no rate-limit bucket (S: the duplicate check under the lock turns a double tap or a retry into a 409). The route-guard allowlists do not change (`require_admin` depends on `require_church`).
11. **Concurrency** (S "Semantics" → Locking; Testing → Postgres). The duplicate check and the insert or update run in the transaction that holds `SELECT … FOR UPDATE` on the church row, so two admins adding one address at once (in any capitalization) get one 201 and one 409. SQLite ignores `FOR UPDATE`; T3's `test_each_write_reads_the_church_row_under_its_lock` checks (compiled for Postgres) that each write asks for it, and T5's `test_contacts_postgres.py` proves it on real Postgres in CI's `backend-postgres`: one test holds the first add inside the lock and checks the second waits and gets the 409; the other is S's (two threads with a barrier, 20 rounds, a new address each round). With the lock turned off both fail (Build notes).
12. **[owner-visible] No database change** (no migration). The table has no unique constraint on the address, and none is added: the locked check above is S's design and is enough now that Streamlit, which wrote without the lock, is retired. A unique index on `(church_id, lower(email))` would be a second guard, but its migration fails on deploy if any church already has the same address twice (Streamlit never checked), so it would first need those duplicates found and removed by hand. Owner question 3.
13. **[owner-visible] The check of existing contacts** (answer 6). SQL cannot run `normalize_address`, so a database query would only approximate the rule. Instead `GET /contacts` says for each contact whether its stored address passes the rule (`email_valid`), and the page flags each one that does not (clarification 3). The owner's phone check (T11 Step 2) opens Contacts once and fixes any flagged contact with **Edit**; the flag stays useful afterwards (5b-2's send refuses such a contact with "An admin can fix it in Settings → Contacts."). B's `backend/scripts/check_contact_addresses.py` (run over `railway ssh`, or on a saved `GET /contacts` body) is not built: the owner would need a terminal, Railway access and the church's id. Owner question 2.
14. **Queries** (B "Query hooks"; S "Queries"). `lib/queries/contacts.ts`: `useContacts()` (`api.church` `GET /contacts`, key `keys.contacts(church.id)`, which exists); `useCreateContact()`, `useUpdateContact()` (`{ id, patch }`) and `useDeleteContact()` (the id), each `useChurchMutation`: on success it cancels a list read in flight, puts the answer in the cached list at once (the new row last, as the server orders it; an edited row in its place; a deleted row gone) and then invalidates the list; on failure the policy of clarification 5. Not optimistic (F §4.4). `lib/settings/contacts.ts` (pure): `contactLabel`, `contactFormFrom`, `newContactBody` (trimmed; no name is `null`), `contactPatch` (only the fields whose trimmed value differs; a cleared name is `null`), `hasTyped`, `EMPTY_CONTACT`. The generated types are named in `lib/api/types.ts`: `Contact`, `ContactList`, `ContactBody`, `ContactPatch`.
15. **[owner-visible] Every new user-facing string** (no em dashes). Settings nav: "Contacts". Contacts page: "Contacts"; "People you can email the bulletin to. Emailing it from the Review step comes in a later update."; "Only admins can add or change contacts."; "This address doesn't look valid. Edit it."; "This address doesn't look valid. An admin can fix it."; "No contacts yet"; "Add the people who receive the bulletin, like your church secretary."; "Ask an admin to add bulletin recipients."; "Add a contact"; "Name (optional)"; "Email"; "Add contact"; "Edit contact"; "Save changes"; "Delete {name or address}?"; "They won't be offered as a bulletin recipient anymore."; "Delete contact"; screen readers: "Edit {name or address}", "Delete {name or address}", the list's "Contacts". From the server (S's, and one new): "Email is required.", "Enter a valid email address.", "That email is already in your contacts.", "Contact not found.", "Name can't contain line breaks or control characters." (new), "Only church admins can do this.", "Too long (max {n} characters).". Reused: "Cancel", "Saving…", "Retry", the skeleton's "Loading", the leave guard's "Discard unsaved changes?", "Your changes on this page haven't been saved.", "Discard changes", "Keep editing".
16. **Docs.** T9 appends "## Slice 5b" to `docs/manual-verification.md` with items 1-6 (owner items 1-3 after the merge) and moves `test_slice1_docs.py`'s pin from the last nine `##` headings to the last ten (the new heading last). The runbook record is T11's (`### Slice 5b-1 record` before `## Backups`, after `### Slice 6a-1 record`).
17. **Deviations from B and S** (each the lean choice for 5b-1; none changes 5b-2's contract):
    - `ContactOut` gains `email_valid` (clarification 13); B's `check_contact_addresses.py` is not built.
    - The contact usecases are in `usecases/contacts.py`, not `usecases/church_admin.py` (clarification 9); `normalize_email` and `clean_name` live there too.
    - S's `field_validator` on `ContactOut.name` is not added: `email_contacts` already returns a blank name as `None` (B).
    - `dedupe_addresses` waits for 5b-2, its first caller.
    - A contact's name refuses control characters and line separators (new; clarification 9).
    - The page's caption says emailing comes later (clarification 3); the add form has an "Add a contact" heading (S had none) so its box is named.
    - The leave guard covers the add form only (S named the profile and prompts forms; the Contacts page had none; clarification 6).
    - S's Postgres race (barrier, 20 rounds) is kept and a deterministic held-lock test is added beside it (clarification 11).

### Risks
- **Addresses already saved twice** (Streamlit never checked) stay; each can be edited or deleted, and an edit that does not change the address never runs the duplicate check. The owner's check counts them (T11 Step 2); deleting one is the fix.
- **A Streamlit-era address with spaces or capitals** (" Office@Example.ORG ") passes the rule (it is trimmed and lower-cased when used), so it is not flagged; it is shown as stored. 5b-2 sends with the normalized form.
- **Every member sees every contact's address** (S: everyone reads). Nothing new: in Streamlit every member could see them too.
- **The edit dialog discards without asking** on Cancel, Escape or a tap outside (clarification 6): at most two fields are lost.
- **SQLite ignores `FOR UPDATE`.** Only CI's `backend-postgres` proves the lock; T3 checks each write asks for it.
- **The Settings nav on a phone** is a wrapping row: three sections fit in one row at 375 px; 5b-2's fourth (Account) may wrap to a second row (Follow-ups).

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/email_addresses.py` (+ `backend/tests/test_email_addresses.py`, `backend/tests/fixtures/shared/email_addresses.json`) | `normalize_address`, `InvalidAddress`; the shared address cases | T1 |
| `backend/usecases/contacts.py` (+ `backend/tests/test_usecase_contacts.py`) | `list_contacts` (with `email_valid`), `normalize_email`, `clean_name`, `add_contact`, `update_contact`, `delete_contact` | T3 |
| `backend/api/routes/contacts.py` (+ `backend/tests/test_api_contacts.py`) | `GET`, `POST`, `PATCH`, `DELETE /contacts`; `ContactOut`, `ContactList`, `ContactIn`, `ContactPatchIn` | T4 |
| `backend/tests/test_contacts_postgres.py` | the lock on real Postgres | T5 |
| `frontend/src/lib/settings/contacts.ts` (+ `.test.ts`), `frontend/src/lib/queries/contacts.ts` | the forms' rules; `useContacts` and the three mutations | T6 |
| `frontend/src/components/settings/contacts-settings-page.tsx` (+ `.test.tsx`), `frontend/src/app/(signed-in)/(church)/settings/contacts/page.tsx` | the Contacts page and its route | T7 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/tests/test_no_streamlit_in_core.py` | `email_addresses` (T1), `usecases.contacts` (T3) | T1, T3 |
| `backend/email_contacts.py`, `backend/tests/test_email_contacts.py` | `session`, the order, blank names as `None`, `get_contact`, `update_contact`, `email_exists`, `as_uuid`; five tests | T2 |
| `backend/api/main.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | the router mounted; regenerated | T4 |
| `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts` | `Contact`, `ContactList`, `ContactBody`, `ContactPatch`; `contact()`, `contactList()` | T6 |
| `frontend/src/components/settings/sections.ts`, `frontend/src/components/settings/settings-layout.test.tsx` | **Contacts** in the nav | T8 |
| `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py` | "## Slice 5b"; the pin of the last ten headings | T9 |
| `docs/ops-runbook.md` | "### Slice 5b-1 record" (the records PR, after the merge) | T11 |

**Counts in the PR:** 29 paths: 15 created (this plan and the fourteen new code, test and fixture files above), 14 modified (the twelve code, test and API paths above, `docs/manual-verification.md` among them, plus the 5b spec (its amendment of 2026-10-06) and `docs/ops-runbook.md` (the 6a-1 record), which ride along until merged). **Untouched:** migrations, `db/models.py`, `api/deps.py`, `api/schemas.py`, `usecases/church_admin.py`, `usecases/members.py`, `repos/churches.py`, `components/app/leave-guard.tsx`, `lib/queries/keys.ts`, the draft schema, `app.py`, `streamlit_views`, `streamlit_tests`.

**Task order and review batch:** T1 → T9, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T10 verifies and opens the draft PR on the owner's yes; T11 merges on the owner's yes, runs the phone check and writes the record.

---


## The server (T1-T5)

### Task 1: `email_addresses.normalize_address` and the shared address cases (B "`email_addresses.normalize_address`"; clarification 7)

**Files:**
- Create: `backend/tests/fixtures/shared/email_addresses.json`, `backend/tests/test_email_addresses.py`, `backend/email_addresses.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

- [ ] **Step 1: Write the failing tests**

The fixture is the authority for the rule: each `valid` case is accepted and returns its `normalized` value, each `invalid` one raises. The exactly-254-character valid case and the 255-character invalid one are the same shape (a 64-character local part and three labels) one letter apart.

**Create `backend/tests/fixtures/shared/email_addresses.json`:**

````json
{
  "_about": "Email addresses (slice 5b spec, email_addresses.normalize_address: the only address validator). Each valid raw value is accepted and saved as normalized (trimmed, the domain lower-cased, the local part as typed); each invalid one is refused. backend/tests/test_email_addresses.py runs every case through normalize_address and test_api_contacts.py through POST /contacts (slice 5b-1); 5b-2 runs them through POST /bulletin-emails, so a saved contact can always be emailed.",
  "valid": [
    {"raw": "mary@example.org", "normalized": "mary@example.org"},
    {"raw": "  Mary.Jones@Example.ORG  ", "normalized": "Mary.Jones@example.org"},
    {"raw": "pastor+bulletin@example.org", "normalized": "pastor+bulletin@example.org"},
    {"raw": "office@mail.example.co.uk", "normalized": "office@mail.example.co.uk"},
    {"raw": "o'brien@example.org", "normalized": "o'brien@example.org"},
    {"raw": "anna@xn--bcher-kva.de", "normalized": "anna@xn--bcher-kva.de"},
    {"raw": "a@b.co", "normalized": "a@b.co"},
    {"raw": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc.ddddddddddddddddddddddddddddddddddddddddddddddddddddddddd.org", "normalized": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc.ddddddddddddddddddddddddddddddddddddddddddddddddddddddddd.org"}
  ],
  "invalid": [
    "maryexample.org",
    "mary@@example.org",
    "mary@jones@example.org",
    "mary jones@example.org",
    "mary@example.org.",
    "mary@example..org",
    "a@b",
    "@example.org",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@example.org",
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.ccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc.dddddddddddddddddddddddddddddddddddddddddddddddddddddddddd.org",
    "mary@-example.org",
    "mary@exa_mple.org",
    "mary@example.c",
    "mary@example.123",
    "a@b.com, c@d.com",
    "a@b.com; c@d.com",
    "a@b.com\r\nBcc: x@y.com",
    "<a@b.com>",
    "Mary <mary@example.org>",
    "\"mary\"@example.org",
    "anna@bücher.de",
    "josé@example.org"
  ]
}
````

**Create `backend/tests/test_email_addresses.py`:**

````python
"""email_addresses.normalize_address, the one address rule (slice 5b spec;
slice 5b-1), driven by the shared fixture every caller is tested against."""
import json
from pathlib import Path

import pytest

from email_addresses import InvalidAddress, normalize_address

CASES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "email_addresses.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES["valid"], ids=lambda case: case["raw"].strip()[:40])
def test_a_valid_address_is_trimmed_with_its_domain_lower_cased(case):
    assert normalize_address(case["raw"]) == case["normalized"]
    assert normalize_address(case["normalized"]) == case["normalized"]     # saving it again changes nothing


@pytest.mark.parametrize("raw", CASES["invalid"], ids=lambda raw: raw[:40])
def test_an_invalid_address_is_refused(raw):
    with pytest.raises(InvalidAddress):
        normalize_address(raw)


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_a_blank_address_is_refused(raw):
    with pytest.raises(InvalidAddress):
        normalize_address(raw)
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin; "
````

**with:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses; "
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_email_addresses.py 2>&1 | tail -3` then `.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1`
**Expected** (`email_addresses` does not exist yet: `ModuleNotFoundError` above these lines; then the import check names the missing module):
```
ERROR backend/tests/test_email_addresses.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```
```
1 failed, 2 passed in <t>s
```

- [ ] **Step 3: Write the rule**

**Create `backend/email_addresses.py`:**

````python
"""The one email address rule (slice 5b spec, `email_addresses.normalize_address`).

Every address the app keeps or sends goes through normalize_address: a saved
contact (slice 5b-1, POST and PATCH /contacts) and, from 5b-2, every
recipient of a bulletin email. So an address Settings accepts can always be
emailed, and the shared fixture tests/fixtures/shared/email_addresses.json
pins the rule for both. No dependency (email-validator is not installed);
no FastAPI, Starlette or Streamlit here.
"""
import re

# Characters that never belong in one plain address: they separate lists (", ;"),
# wrap display names or quoted parts ("< > \" ( ) [ ]") or escape ("\\").
_FORBIDDEN = frozenset(',;<>"()[]\\')
# One domain label: 1-63 ASCII letters, digits or hyphens, not starting or ending with a hyphen.
_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")


class InvalidAddress(ValueError):
    """`raw` is not one plain email address the app can send to."""


def normalize_address(raw: str) -> str:
    """`raw` trimmed, with its domain lower-cased (domains ignore case; the
    local part keeps the case typed), or InvalidAddress unless all hold:
    at most 254 characters, ASCII only (an internationalized domain is refused;
    its punycode form is accepted), no whitespace, control character or any of
    , ; < > " ( ) [ ] \\, exactly one @, a local part of 1-64 characters, and a
    domain of at least two labels (each 1-63 letters, digits or hyphens, not
    starting or ending with a hyphen) whose last label is at least two letters.
    """
    address = raw.strip()
    if not address or len(address) > 254 or not address.isascii():
        raise InvalidAddress(raw)
    if any(ch.isspace() or ord(ch) < 32 or ord(ch) == 127 or ch in _FORBIDDEN for ch in address):
        raise InvalidAddress(raw)
    if address.count("@") != 1:
        raise InvalidAddress(raw)
    local, _, domain = address.partition("@")
    if not 1 <= len(local) <= 64:
        raise InvalidAddress(raw)
    labels = domain.split(".")
    if len(labels) < 2 or not all(_LABEL.fullmatch(label) for label in labels):
        raise InvalidAddress(raw)
    if len(labels[-1]) < 2 or not labels[-1].isalpha():
        raise InvalidAddress(raw)
    return f"{local}@{domain.lower()}"
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_email_addresses.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`36 passed in <t>s`; `1562 passed, 24 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/email_addresses.py backend/tests/test_email_addresses.py backend/tests/fixtures/shared/email_addresses.json backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Slice 5b-1: email_addresses.normalize_address, the one address rule" -m "An address is accepted when it is one plain ASCII address: at most 254
characters, no whitespace, control character or list or quoting
character, one @, a local part of 1-64 characters and a domain of two or
more labels ending in letters. It comes back trimmed with the domain
lower-cased. The shared fixture email_addresses.json holds the cases
(5b spec's list and a few more); POST /contacts runs them too (T4), and
5b-2's send will." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1562 passed, 24 skipped`; frontend `759 passed` in 92 files.

### Task 2: The contacts repo: sessions, the order, edits and the duplicate check (B "Modules" `email_contacts.py`; S "Changed modules"; clarification 8)

**Files:**
- Modify: `backend/tests/test_email_contacts.py`, `backend/email_contacts.py`

- [ ] **Step 1: Write the failing tests**

The three existing tests stay as they are (the church isolation of a list and of a delete, and no `DEFAULT_CONTACTS`). The order test seeds rows with the same `created_at`, so only the name and the id decide; the nameless ones (`""`, `None`, spaces) come last and among themselves by id.

**In `backend/tests/test_email_contacts.py`, replace:**

````python
import email_contacts
from email_contacts import (
    add_contact,
    delete_contact,
    get_contacts_for_display,
    list_contacts,
````

**with:**

````python
from datetime import datetime, timezone

import pytest

import email_contacts
from db import session_scope
from db.models import Contact
from domain_errors import NotFound
from email_contacts import (
    add_contact,
    delete_contact,
    email_exists,
    get_contact,
    get_contacts_for_display,
    list_contacts,
    update_contact,
````

**Append to `backend/tests/test_email_contacts.py`:**

````python


# --- slice 5b-1: the order, blank names, edits, the duplicate check, a session -------------------

def _seed(church_id, rows):
    """Contacts with the given (name, email, created_at), straight into the table."""
    with session_scope() as s:
        for name, email, created_at in rows:
            s.add(Contact(church_id=church_id, name=name, email=email, created_at=created_at))


def test_contacts_are_listed_by_creation_then_name_with_blank_names_last(tmp_db, make_user, make_church):
    church = make_church(name="A", owner_user_id=make_user(email="c3@x.org"))
    first, later = datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 2, 1, tzinfo=timezone.utc)
    _seed(church, [("Zoe", "zoe@x.org", first), ("", "blank@x.org", first), (None, "null@x.org", first),
                   ("  ", "spaces@x.org", first), ("Amy", "amy@x.org", first), ("Bob", "bob@x.org", later)])
    listed = list_contacts(church)
    assert [c["email"] for c in listed[:2]] == ["amy@x.org", "zoe@x.org"]
    assert sorted(c["email"] for c in listed[2:5]) == ["blank@x.org", "null@x.org", "spaces@x.org"]
    assert [c["id"] for c in listed[2:5]] == sorted(c["id"] for c in listed[2:5])     # nameless: by id
    assert listed[5]["email"] == "bob@x.org"
    assert [c["name"] for c in listed] == ["Amy", "Zoe", None, None, None, "Bob"]


def test_update_contact_sets_only_the_keys_given_and_never_another_church(tmp_db, make_user, make_church):
    u = make_user(email="c4@x.org")
    a = make_church(name="A", owner_user_id=u)
    b = make_church(name="B", owner_user_id=u)
    cid = add_contact(a, name="Mary", email="mary@x.org")["id"]
    assert update_contact(cid, a, {"name": ""}) == {"id": cid, "name": None, "email": "mary@x.org"}
    assert update_contact(cid, a, {"email": "mary.jones@x.org"})["email"] == "mary.jones@x.org"
    assert update_contact(cid, b, {"name": "Taken"}) is None
    assert get_contact(cid, b) is None
    assert get_contact(cid, a) == {"id": cid, "name": None, "email": "mary.jones@x.org"}


def test_email_exists_ignores_case_and_can_leave_one_contact_out(tmp_db, make_user, make_church):
    u = make_user(email="c5@x.org")
    a = make_church(name="A", owner_user_id=u)
    b = make_church(name="B", owner_user_id=u)
    cid = add_contact(a, name="Mary", email="Mary@X.org")["id"]
    assert email_exists(a, "mary@x.org") and email_exists(a, "MARY@X.ORG")
    assert not email_exists(a, "mary@x.org", exclude_id=cid)
    assert not email_exists(b, "mary@x.org")


def test_a_malformed_id_is_not_found(tmp_db, make_user, make_church):
    a = make_church(name="A", owner_user_id=make_user(email="c6@x.org"))
    for call in (lambda: update_contact("not-a-uuid", a, {"name": "X"}), lambda: delete_contact("not-a-uuid", a),
                 lambda: get_contact("not-a-uuid", a)):
        with pytest.raises(NotFound):
            call()


def test_the_writes_join_the_callers_session(tmp_db, make_user, make_church):
    a = make_church(name="A", owner_user_id=make_user(email="c7@x.org"))
    with session_scope() as s:
        cid = add_contact(a, name="Mary", email="mary@x.org", session=s)["id"]
        assert email_exists(a, "mary@x.org", session=s)
        update_contact(cid, a, {"name": "Mary J."}, session=s)
        assert [c["name"] for c in list_contacts(a, session=s)] == ["Mary J."]
        assert delete_contact(cid, a, session=s) is True
    assert list_contacts(a) == []
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_email_contacts.py 2>&1 | tail -3`
**Expected** (`email_exists`, `get_contact` and `update_contact` do not exist yet: an `ImportError` above these lines):
```
ERROR backend/tests/test_email_contacts.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: Rewrite the repo's functions**

`add_contact` and `delete_contact` keep their names and arguments (the frozen `streamlit_views/settings.py` calls them); `get_contacts_for_display` is unchanged.

**In `backend/email_contacts.py`, replace:**

````python
"""
import uuid
from typing import Any, Dict, List

from sqlalchemy import delete, select

from db import session_scope
from db.models import Contact


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _to_dict(c: Contact) -> Dict[str, str]:
    return {"id": str(c.id), "name": c.name, "email": c.email}


def list_contacts(church_id) -> List[Dict[str, str]]:
    """All contacts for a church, ordered by creation then name."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        rows = (
            session.execute(
                select(Contact)
                .where(Contact.church_id == cid)
                .order_by(Contact.created_at, Contact.name)
            )
            .scalars()
            .all()
        )
        return [_to_dict(c) for c in rows]


def add_contact(church_id, *, name: str, email: str) -> Dict[str, str]:
    """Insert a contact for a church. Returns {id, name, email}."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        c = Contact(church_id=cid, name=name, email=email)
        session.add(c)
        session.flush()
        return _to_dict(c)


def delete_contact(contact_id, church_id) -> bool:
    """Delete a contact only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        result = session.execute(
            delete(Contact).where(
                Contact.id == _as_uuid(contact_id), Contact.church_id == cid
            )
        )
        return result.rowcount > 0
````

**with:**

````python

Every function is scoped to one church (a contact of another church is never
read, changed or deleted) and takes an optional `session`, so a usecase can
run it inside the transaction that holds the church-row lock (slice 5b-1;
6a spec, "Semantics" → Contacts). Ids go through db.ids.as_uuid, so a
malformed id is a 404, never a 500. A name that is NULL or blank (Streamlit
stored "" for a contact without one) is returned as None.
"""
import uuid
from typing import Any, Dict, List, Mapping, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Contact


def _to_dict(c: Contact) -> Dict[str, Any]:
    name = c.name if c.name is not None and c.name.strip() else None
    return {"id": str(c.id), "name": name, "email": c.email}


def list_contacts(church_id, *, session: Optional[Session] = None) -> List[Dict[str, Any]]:
    """All contacts for a church: by creation time, then name (a NULL or blank
    name after every named one), then id, so the order never depends on the
    database (5b spec, GET /contacts)."""
    if session is not None:
        return _list_contacts(session, church_id)
    with session_scope() as own:
        return _list_contacts(own, church_id)


def _list_contacts(session, church_id) -> List[Dict[str, Any]]:
    name = func.nullif(func.trim(Contact.name), "")
    rows = session.execute(
        select(Contact)
        .where(Contact.church_id == as_uuid(church_id))
        .order_by(Contact.created_at, name.asc().nulls_last(), Contact.id)
    ).scalars().all()
    return [_to_dict(c) for c in rows]


def add_contact(church_id, *, name: str, email: str, session: Optional[Session] = None) -> Dict[str, Any]:
    """Insert a contact for a church, as given (the caller cleans it). Returns {id, name, email}."""
    if session is not None:
        return _add_contact(session, church_id, name, email)
    with session_scope() as own:
        return _add_contact(own, church_id, name, email)


def _add_contact(session, church_id, name, email) -> Dict[str, Any]:
    c = Contact(church_id=as_uuid(church_id), name=name, email=email)
    session.add(c)
    session.flush()
    return _to_dict(c)


def update_contact(contact_id, church_id, changes: Mapping[str, str], *,
                   session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """Set the keys given ("name" and/or "email", already cleaned) on the
    church's contact. Returns it, or None when the church has no such contact."""
    if session is not None:
        return _update_contact(session, contact_id, church_id, changes)
    with session_scope() as own:
        return _update_contact(own, contact_id, church_id, changes)


def _update_contact(session, contact_id, church_id, changes) -> Optional[Dict[str, Any]]:
    c = _get(session, contact_id, church_id)
    if c is None:
        return None
    if "name" in changes:
        c.name = changes["name"]
    if "email" in changes:
        c.email = changes["email"]
    session.flush()
    return _to_dict(c)


def get_contact(contact_id, church_id, *, session: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """The church's contact, or None."""
    if session is not None:
        c = _get(session, contact_id, church_id)
        return _to_dict(c) if c is not None else None
    with session_scope() as own:
        return get_contact(contact_id, church_id, session=own)


def _get(session, contact_id, church_id) -> Optional[Contact]:
    return session.execute(
        select(Contact).where(Contact.id == as_uuid(contact_id), Contact.church_id == as_uuid(church_id))
    ).scalar_one_or_none()


def email_exists(church_id, email: str, *, exclude_id: Optional[uuid.UUID] = None,
                 session: Optional[Session] = None) -> bool:
    """True when another of the church's contacts has this address, compared
    lower-cased (5b's rule: addresses that differ only in case are one)."""
    if session is not None:
        return _email_exists(session, church_id, email, exclude_id)
    with session_scope() as own:
        return _email_exists(own, church_id, email, exclude_id)


def _email_exists(session, church_id, email, exclude_id) -> bool:
    query = select(Contact.id).where(
        Contact.church_id == as_uuid(church_id), func.lower(Contact.email) == email.lower()
    )
    if exclude_id is not None:
        query = query.where(Contact.id != as_uuid(exclude_id))
    return session.execute(query.limit(1)).first() is not None


def delete_contact(contact_id, church_id, *, session: Optional[Session] = None) -> bool:
    """Delete a contact only if it belongs to `church_id`. Cross-church -> False."""
    if session is not None:
        return _delete_contact(session, contact_id, church_id)
    with session_scope() as own:
        return _delete_contact(own, contact_id, church_id)


def _delete_contact(session, contact_id, church_id) -> bool:
    result = session.execute(
        delete(Contact).where(Contact.id == as_uuid(contact_id), Contact.church_id == as_uuid(church_id))
    )
    return result.rowcount > 0
````

- [ ] **Step 4: See them pass, the Streamlit tests that call this module, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_email_contacts.py streamlit_tests 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`43 passed in <t>s` (the repo's 8 and the 35 `streamlit_tests`); `1567 passed, 24 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/email_contacts.py backend/tests/test_email_contacts.py
git commit -q -m "Slice 5b-1: the contacts repo takes a session, orders nameless contacts last, edits and finds duplicates" -m "Every email_contacts function takes an optional session, so a usecase
can run it under the church-row lock, and ids go through db.ids.as_uuid
(a malformed id is a 404). The list orders by creation, then name with
blank names last, then id (5b spec), and a NULL or blank name comes back
as None. New: get_contact, update_contact (only the keys given) and
email_exists (case-insensitive, optionally leaving one contact out).
get_contacts_for_display and the Streamlit callers' signatures stay." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1567 passed, 24 skipped`; frontend `759 passed` in 92 files.

### Task 3: The contacts usecases: the list's check, the rules, the locked writes (S "Semantics" → Contacts and Locking; clarifications 9, 11, 13)

**Files:**
- Create: `backend/tests/test_usecase_contacts.py`, `backend/usecases/contacts.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

- [ ] **Step 1: Write the failing tests**

`test_usecase_contacts.py` imports `_record_church_row_access` from `test_church_settings.py` (the 2a lock check, as `test_church_admin.py` does). The flagged-address test stores addresses straight through the repo, as Streamlit did, with no check.

**Create `backend/tests/test_usecase_contacts.py`:**

````python
"""usecases.contacts (slice 5b-1; 6a spec "Semantics" → Contacts): the list
with each address's check, the address and name rules, the duplicate check,
and every write under the church-row lock with the role re-read under it."""
import pytest

import email_contacts
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound
from email_addresses import normalize_address
from repos import churches
from repos.memberships import add_membership, remove_membership, set_role
from tests.test_church_settings import _record_church_row_access
from usecases import contacts

NO_ACCESS = {"reason": "no_church_access"}


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com")
    admin = make_user(email="admin@example.com")
    member = make_user(email="member@example.com")
    cid = make_church(name="Example Church", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    return {"church": cid, "owner": owner, "admin": admin, "member": member}


def _emails(world) -> list[str]:
    return [c["email"] for c in email_contacts.list_contacts(world["church"])]


@pytest.mark.parametrize("raw, stored", [
    (" Mary@Example.ORG ", "Mary@example.org"),
    ("pastor+bulletin@example.org", "pastor+bulletin@example.org"),
])
def test_an_address_is_stored_as_the_send_time_rule_returns_it(raw, stored):
    assert contacts.normalize_email(raw) == stored
    assert normalize_address(stored) == stored


@pytest.mark.parametrize("raw, message", [
    ("", "Email is required."),
    ("   ", "Email is required."),
    (None, "Email is required."),
    ("maryexample.org", "Enter a valid email address."),
    ("mary@@example.org", "Enter a valid email address."),
    ("mary jones@example.org", "Enter a valid email address."),
    ("a@b", "Enter a valid email address."),
    ("josé@example.org", "Enter a valid email address."),
    ("a@bücher.de", "Enter a valid email address."),
])
def test_a_missing_or_invalid_address_is_named(raw, message):
    with pytest.raises(InvalidInput) as bad:
        contacts.normalize_email(raw)
    assert (bad.value.field, bad.value.message) == ("email", message)


def test_a_name_is_trimmed_blank_is_stored_as_empty_and_it_stays_on_one_line():
    assert contacts.clean_name("  Mary Jones ") == "Mary Jones"
    assert contacts.clean_name("   ") == ""
    assert contacts.clean_name(None) == ""
    for bad in ("Mary\nJones", "Mary\x00", "Mary Jones"):
        with pytest.raises(InvalidInput) as refused:
            contacts.clean_name(bad)
        assert (refused.value.field, refused.value.message) == (
            "name", "Name can't contain line breaks or control characters.")


def test_an_admin_adds_a_contact_and_a_duplicate_in_any_case_is_refused(world):
    added = contacts.add_contact(world["church"], world["admin"], name=" Mary ", email=" Mary@Example.ORG ")
    assert {k: added[k] for k in ("name", "email", "email_valid")} == {
        "name": "Mary", "email": "Mary@example.org", "email_valid": True}
    with pytest.raises(Conflict) as taken:
        contacts.add_contact(world["church"], world["owner"], name="Other", email="MARY@example.org")
    assert taken.value.message == "That email is already in your contacts."
    nameless = contacts.add_contact(world["church"], world["owner"], name="  ", email="office@example.org")
    assert nameless["name"] is None
    assert _emails(world) == ["Mary@example.org", "office@example.org"]


def test_an_edit_changes_only_what_is_sent_and_checks_duplicates_but_not_itself(world):
    mary = contacts.add_contact(world["church"], world["owner"], name="Mary", email="mary@example.org")
    contacts.add_contact(world["church"], world["owner"], name="Office", email="office@example.org")
    edited = contacts.update_contact(world["church"], world["admin"], mary["id"], {"name": "Mary Jones"})
    assert (edited["name"], edited["email"]) == ("Mary Jones", "mary@example.org")
    edited = contacts.update_contact(world["church"], world["admin"], mary["id"], {"email": "MARY@example.org"})
    assert (edited["name"], edited["email"]) == ("Mary Jones", "MARY@example.org")       # itself: no conflict
    assert contacts.update_contact(world["church"], world["admin"], mary["id"], {"name": None})["name"] is None
    with pytest.raises(Conflict):
        contacts.update_contact(world["church"], world["admin"], mary["id"], {"email": "Office@Example.org"})
    with pytest.raises(InvalidInput) as blank:
        contacts.update_contact(world["church"], world["admin"], mary["id"], {"email": None})
    assert (blank.value.field, blank.value.message) == ("email", "Email is required.")
    assert _emails(world) == ["MARY@example.org", "office@example.org"]


def test_an_unknown_contact_or_another_churchs_is_not_found(world, make_church):
    other = make_church(name="Other Church", owner_user_id=world["owner"])
    theirs = contacts.add_contact(other, world["owner"], name="Theirs", email="theirs@example.org")
    for call in (lambda: contacts.update_contact(world["church"], world["owner"], theirs["id"], {"email": "bad"}),
                 lambda: contacts.delete_contact(world["church"], world["owner"], theirs["id"])):
        with pytest.raises(NotFound) as missing:
            call()
        assert missing.value.message == "Contact not found."
    assert [c["email"] for c in email_contacts.list_contacts(other)] == ["theirs@example.org"]
    contacts.delete_contact(other, world["owner"], theirs["id"])
    assert email_contacts.list_contacts(other) == []


def test_the_list_flags_each_saved_address_the_send_time_rule_refuses(world):
    for name, email in (("Mary", "mary@example.org"), ("Two", "a@example.org, b@example.org"),
                        ("", "office@example"), (None, " Office@Example.ORG ")):
        email_contacts.add_contact(world["church"], name=name, email=email)     # as Streamlit saved them
    listed = contacts.list_contacts(world["church"])
    assert [(c["name"], c["email"], c["email_valid"]) for c in listed] == [
        ("Mary", "mary@example.org", True),
        ("Two", "a@example.org, b@example.org", False),
        (None, "office@example", False),
        (None, " Office@Example.ORG ", True),
    ]


def test_a_member_a_demoted_admin_or_a_removed_member_writes_nothing(world):
    mary = contacts.add_contact(world["church"], world["owner"], name="Mary", email="mary@example.org")
    writes = (lambda who: contacts.add_contact(world["church"], world[who], name="X", email="x@example.org"),
              lambda who: contacts.update_contact(world["church"], world[who], mary["id"], {"name": "Renamed"}),
              lambda who: contacts.delete_contact(world["church"], world[who], mary["id"]))
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    for who in ("member", "admin"):
        for write in writes:
            with pytest.raises(Forbidden) as denied:
                write(who)
            assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        writes[0]("member")
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        writes[0]("owner")
    assert deleted.value.details == NO_ACCESS
    assert [(c["name"], c["email"]) for c in email_contacts.list_contacts(world["church"])] == [
        ("Mary", "mary@example.org")]


def test_each_write_reads_the_church_row_under_its_lock(world):
    for write in (lambda: contacts.add_contact(world["church"], world["owner"], name="Mary", email="mary@example.org"),
                  lambda: contacts.update_contact(world["church"], world["owner"],
                                                  email_contacts.list_contacts(world["church"])[0]["id"],
                                                  {"email": "mary.jones@example.org"}),
                  lambda: contacts.delete_contact(world["church"], world["owner"],
                                                  email_contacts.list_contacts(world["church"])[0]["id"])):
        with _record_church_row_access() as (reads, _writes):
            write()
        assert [locked for _session, locked in reads] == [True]
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses; "
````

**with:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts; "
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_usecase_contacts.py 2>&1 | tail -3` then `.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1`
**Expected** (`usecases.contacts` does not exist yet):
```
ERROR backend/tests/test_usecase_contacts.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```
```
1 failed, 2 passed in <t>s
```

- [ ] **Step 3: Write the usecases**

**Create `backend/usecases/contacts.py`:**

````python
"""The church's contacts, the people the bulletin is emailed to (slice 5b-1;
5b spec GET /contacts; 6a spec "Contacts" and "Semantics" → Contacts).

Every member reads the list; owners and admins add, edit and delete. Each
write opens one session and starts with usecases.members.lock_and_read_actor
(the church-row lock and the caller's role re-read under it), then
church_admin.require_admin_role, so a caller demoted after require_admin ran
gets the role 403, and the duplicate check and the write run under the lock:
two admins adding the same address at once get one contact and one 409.

An address goes through email_addresses.normalize_address, the rule 5b-2
applies again when it sends, so an address saved here can always be emailed.
The list says, for each contact, whether its stored address passes that rule
(`email_valid`): contacts saved before the rule (in Streamlit) are shown, and
flagged when they would fail, so an admin can fix them on the Contacts page.
No FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import re
import uuid
from collections.abc import Mapping
from typing import Optional

import email_contacts
from bulletin_settings import NOT_ONE_LINE
from db import session_scope
from domain_errors import Conflict, InvalidInput, NotFound
from email_addresses import InvalidAddress, normalize_address
from usecases.church_admin import require_admin_role
from usecases.members import lock_and_read_actor

EMAIL_REQUIRED = "Email is required."
EMAIL_INVALID = "Enter a valid email address."
EMAIL_TAKEN = "That email is already in your contacts."
NAME_NOT_ONE_LINE = "Name can't contain line breaks or control characters."
CONTACT_NOT_FOUND = "Contact not found."

# A contact's name is one line in the list and, from 5b-2, in the email dialog: no control character (NUL,
# which Postgres refuses in text, among them), no U+2028/U+2029, no U+FFFE/U+FFFF (the church name's rule).
_NOT_ONE_LINE = re.compile(f"[{NOT_ONE_LINE}￾￿]")


def email_is_valid(email: str) -> bool:
    """True when `email` passes normalize_address (5b-2 can send to it)."""
    try:
        normalize_address(email)
    except InvalidAddress:
        return False
    return True


def _out(contact: dict) -> dict:
    return {**contact, "email_valid": email_is_valid(contact["email"])}


def list_contacts(church_id: uuid.UUID) -> list[dict]:
    """GET /contacts: every contact of the church, in email_contacts.list_contacts'
    order, each {id, name (None when blank), email, email_valid}."""
    return [_out(c) for c in email_contacts.list_contacts(church_id)]


def normalize_email(value: Optional[str]) -> str:
    """A contact's address as stored: normalize_address's answer (trimmed, the
    domain lower-cased). Blank or None: InvalidInput "Email is required.";
    refused by the rule: InvalidInput "Enter a valid email address."."""
    if value is None or not value.strip():
        raise InvalidInput(EMAIL_REQUIRED, field="email")
    try:
        return normalize_address(value)
    except InvalidAddress:
        raise InvalidInput(EMAIL_INVALID, field="email") from None


def clean_name(value: Optional[str]) -> str:
    """A contact's name as stored: trimmed, "" for none (Streamlit's value for
    a nameless contact, which the list returns as None). One line only."""
    name = (value or "").strip()
    if _NOT_ONE_LINE.search(name):
        raise InvalidInput(NAME_NOT_ONE_LINE, field="name")
    return name


def add_contact(church_id: uuid.UUID, actor_id: uuid.UUID, *, name: Optional[str], email: Optional[str]) -> dict:
    """POST /contacts: the new contact. The name is checked before the email;
    an address already in the church's contacts (any case) is a 409."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        clean = clean_name(name)
        address = normalize_email(email)
        if email_contacts.email_exists(church_id, address, session=s):
            raise Conflict(EMAIL_TAKEN)
        return _out(email_contacts.add_contact(church_id, name=clean, email=address, session=s))


def update_contact(church_id: uuid.UUID, actor_id: uuid.UUID, contact_id: uuid.UUID,
                   changes: Mapping[str, Optional[str]]) -> dict:
    """PATCH /contacts/{id}: only the keys sent ("name": None or blank clears
    it; "email": None or blank is "Email is required."). An unknown id, or
    another church's, is a 404 before any field is checked; an address another
    of the church's contacts has (any case) is a 409."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        if email_contacts.get_contact(contact_id, church_id, session=s) is None:
            raise NotFound(CONTACT_NOT_FOUND)
        clean: dict[str, str] = {}
        if "name" in changes:
            clean["name"] = clean_name(changes["name"])
        if "email" in changes:
            clean["email"] = normalize_email(changes["email"])
            if email_contacts.email_exists(church_id, clean["email"], exclude_id=contact_id, session=s):
                raise Conflict(EMAIL_TAKEN)
        return _out(email_contacts.update_contact(contact_id, church_id, clean, session=s))


def delete_contact(church_id: uuid.UUID, actor_id: uuid.UUID, contact_id: uuid.UUID) -> None:
    """DELETE /contacts/{id}; an unknown id, or another church's, is a 404."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        if not email_contacts.delete_contact(contact_id, church_id, session=s):
            raise NotFound(CONTACT_NOT_FOUND)
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_usecase_contacts.py backend/tests/test_email_contacts.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`29 passed in <t>s`; `1585 passed, 24 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/usecases/contacts.py backend/tests/test_usecase_contacts.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Slice 5b-1: the contacts usecases, each write under the church-row lock" -m "usecases/contacts.py: the list, with email_valid for each saved
address (false when normalize_address refuses it, so the page can flag
contacts saved before the rule); the address rule's wrapper (\"Email is
required.\", \"Enter a valid email address.\"; what normalize_address
returns is stored); the name, trimmed and on one line; and add, edit and
delete, each in one session that locks the church row and re-reads the
caller's role, then 404, the fields, and the case-insensitive duplicate
check (\"That email is already in your contacts.\") under the lock." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1585 passed, 24 skipped`; frontend `759 passed` in 92 files.

### Task 4: `/contacts` (B API, Schemas; S API, Models; clarifications 10, 12)

**Files:**
- Create: `backend/tests/test_api_contacts.py`, `backend/api/routes/contacts.py`
- Modify: `backend/api/main.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (regenerated)

- [ ] **Step 1: Write the failing tests**

`test_every_shared_address_case_is_accepted_or_refused_as_normalize_address_says` runs the whole shared fixture through `POST /contacts` (B acceptance 14a). The isolation test uses `assert_church_isolated` for all four routes, with church B's contact as `resource_path_b` for `PATCH` and `DELETE` (404, never 403).

**Create `backend/tests/test_api_contacts.py`:**

````python
"""/contacts over HTTP (slice 5b-1; 5b spec GET /contacts, 6a spec POST, PATCH
and DELETE /contacts): who may read and write, the order and the null names,
each address's check, the exact errors, and church isolation. The shared
address fixture runs through POST /contacts, as it runs through
normalize_address, so a contact can be saved exactly when it can be emailed."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from db import session_scope
from db.models import Contact
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER = "owner@example.com"
MEMBER = "member@example.com"
ADDRESSES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "email_addresses.json").read_text(encoding="utf-8"))
ADMINS_ONLY = {"code": "forbidden", "message": "Only church admins can do this."}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=MEMBER), cid, "member")
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _list(client, church, email=OWNER) -> list[dict]:
    r = client.get("/contacts", headers=church_headers(email, church))
    assert r.status_code == 200, r.text
    return r.json()["items"]


def _add(client, church, body, email=OWNER):
    return client.post("/contacts", headers=church_headers(email, church), json=body)


def test_a_member_reads_the_list_in_order_with_blank_names_null_and_bad_addresses_flagged(client, church):
    at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with session_scope() as s:
        for name, email in (("Zoe", "zoe@example.org"), ("", "blank@example.org"), (None, "null@example.org"),
                            ("Amy", "a@example.org, b@example.org")):
            s.add(Contact(church_id=church, name=name, email=email, created_at=at))
    items = _list(client, church, email=MEMBER)
    assert [(c["name"], c["email"], c["email_valid"]) for c in items[:2]] == [
        ("Amy", "a@example.org, b@example.org", False), ("Zoe", "zoe@example.org", True)]
    assert sorted((c["name"], c["email"], c["email_valid"]) for c in items[2:]) == [
        (None, "blank@example.org", True), (None, "null@example.org", True)]
    assert set(items[0]) == {"id", "name", "email", "email_valid"}


def test_an_admin_adds_edits_and_deletes_a_contact(client, church, make_user):
    add_membership(make_user(email="admin@example.com"), church, "admin")
    r = _add(client, church, {"name": " Mary ", "email": " Mary@Example.ORG "}, email="admin@example.com")
    assert r.status_code == 201, r.text
    mary = r.json()
    assert {k: mary[k] for k in ("name", "email", "email_valid")} == {
        "name": "Mary", "email": "Mary@example.org", "email_valid": True}
    assert _list(client, church) == [mary]

    path = f"/contacts/{mary['id']}"
    r = client.patch(path, headers=church_headers(OWNER, church), json={"name": "Mary Jones"})
    assert (r.status_code, r.json()["name"], r.json()["email"]) == (200, "Mary Jones", "Mary@example.org")
    r = client.patch(path, headers=church_headers(OWNER, church), json={"name": None, "email": "mary@example.org"})
    assert (r.status_code, r.json()["name"], r.json()["email"]) == (200, None, "mary@example.org")

    r = client.delete(path, headers=church_headers(OWNER, church))
    assert (r.status_code, r.json()) == (200, {"deleted": True})
    assert _list(client, church) == []
    r = client.delete(path, headers=church_headers(OWNER, church))
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Contact not found."})


def test_a_member_cannot_add_edit_or_delete(client, church):
    mary = _add(client, church, {"name": "Mary", "email": "mary@example.org"}).json()
    for method, path, body in (("POST", "/contacts", {"email": "x@example.org"}),
                               ("PATCH", f"/contacts/{mary['id']}", {"name": "Renamed"}),
                               ("DELETE", f"/contacts/{mary['id']}", None)):
        r = client.request(method, path, headers=church_headers(MEMBER, church), json=body)
        assert (r.status_code, _error(r)) == (403, ADMINS_ONLY), f"{method} {path}"
    assert [(c["name"], c["email"]) for c in _list(client, church)] == [("Mary", "mary@example.org")]


@pytest.mark.parametrize("body, field, message", [
    ({"name": "Mary"}, "email", "Email is required."),
    ({"email": "   "}, "email", "Email is required."),
    ({"email": "mary@example"}, "email", "Enter a valid email address."),
    ({"name": "Mary\nJones", "email": "mary@example.org"}, "name",
     "Name can't contain line breaks or control characters."),
    ({"name": "x" * 201, "email": "mary@example.org"}, "name", "Too long (max 200 characters)."),
    ({"email": "m" * 321}, "email", "Too long (max 320 characters)."),
])
def test_a_bad_field_is_a_422_naming_it(client, church, body, field, message):
    r = _add(client, church, body)
    assert r.status_code == 422, r.text
    assert (r.json()["error"]["code"], r.json()["error"]["fields"]) == ("invalid_request", {field: message})
    assert _list(client, church) == []


def test_an_address_already_saved_in_any_case_is_a_409(client, church):
    mary = _add(client, church, {"name": "Mary", "email": "mary@example.org"}).json()
    office = _add(client, church, {"email": "office@example.org"}).json()
    taken = {"code": "conflict", "message": "That email is already in your contacts."}
    r = _add(client, church, {"name": "Again", "email": "MARY@example.org"})
    assert (r.status_code, _error(r)) == (409, taken)
    r = client.patch(f"/contacts/{office['id']}", headers=church_headers(OWNER, church),
                     json={"email": "Mary@Example.org"})
    assert (r.status_code, _error(r)) == (409, taken)
    r = client.patch(f"/contacts/{mary['id']}", headers=church_headers(OWNER, church),
                     json={"email": "MARY@example.org"})                       # its own address, new case
    assert (r.status_code, r.json()["email"]) == (200, "MARY@example.org")


def test_every_shared_address_case_is_accepted_or_refused_as_normalize_address_says(client, church):
    for case in ADDRESSES["valid"]:
        r = _add(client, church, {"email": case["raw"]})
        assert (r.status_code, r.json().get("email")) == (201, case["normalized"]), case["raw"]
    for raw in ADDRESSES["invalid"]:
        r = _add(client, church, {"email": raw})
        assert r.status_code == 422, raw
        assert r.json()["error"]["fields"] == {"email": "Enter a valid email address."}, raw
    assert [c["email"] for c in _list(client, church)] == [case["normalized"] for case in ADDRESSES["valid"]]


def test_unknown_fields_and_malformed_ids_are_422(client, church):
    r = _add(client, church, {"email": "mary@example.org", "church_id": str(church)})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.patch("/contacts/not-a-uuid", headers=church_headers(OWNER, church), json={"name": "X"})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")


def test_contacts_are_isolated_between_churches(client, isolation_world):
    world = isolation_world
    theirs = _add(client, world.church_b, {"name": "Theirs", "email": "theirs@example.org"}, email=world.b).json()
    assert_church_isolated(client, "GET", "/contacts", world=world)
    assert_church_isolated(client, "POST", "/contacts", world=world, json={"email": "ours@example.org"})
    second = _add(client, world.church_a, {"email": "second@example.org"}, email=world.a).json()
    assert_church_isolated(client, "PATCH", f"/contacts/{second['id']}", world=world, json={"name": "Ours"},
                           resource_path_b=f"/contacts/{theirs['id']}")
    assert_church_isolated(client, "DELETE", f"/contacts/{second['id']}", world=world,
                           resource_path_b=f"/contacts/{theirs['id']}")
    assert [(c["name"], c["email"]) for c in _list(client, world.church_b, email=world.b)] == [
        ("Theirs", "theirs@example.org")]
    assert [c["email"] for c in _list(client, world.church_a, email=world.a)] == ["ours@example.org"]
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_contacts.py 2>&1 | tail -3`
**Expected** (no `/contacts` route yet: every request is a 404):
```
FAILED backend/tests/test_api_contacts.py::test_unknown_fields_and_malformed_ids_are_422
FAILED backend/tests/test_api_contacts.py::test_contacts_are_isolated_between_churches
13 failed in <t>s
```

- [ ] **Step 3: Write the routes and mount them**

**Create `backend/api/routes/contacts.py`:**

````python
"""/contacts: the church's contacts (slice 5b-1; 5b spec GET /contacts, 6a
spec POST, PATCH and DELETE /contacts).

Every member reads the list (`require_church`); owners and admins add, edit
and delete (`require_admin`, then the role re-read under the church-row lock
in usecases.contacts). Plain `def` routes that each make one usecase call
(F §2.2 rule 1), with no SQL and no try/except. No Idempotency-Key: the
duplicate check runs under the lock, so a double tap or a retry gets a 409,
never a second contact (6a spec, API).
"""
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from api.schemas import DeletedOut
from usecases import contacts

router = APIRouter()


class ContactOut(BaseModel):
    id: uuid.UUID
    name: str | None = Field(description="null when the stored name is NULL or blank")
    email: str
    email_valid: bool = Field(description="false when the stored address fails the send-time check "
                                          "(email_addresses.normalize_address): an admin should fix it")


class ContactList(BaseModel):
    items: list[ContactOut]


class ContactIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=200)
    email: str = Field("", max_length=320)        # "" default: the usecase says "Email is required." (F §1.3)


class ContactPatchIn(BaseModel):
    """Omitted = unchanged (model_fields_set); a null or blank name clears it;
    a null or blank email is "Email is required."."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, max_length=200)
    email: str | None = Field(None, max_length=320)


@router.get("/contacts", response_model=ContactList, responses=error_responses(401, 403, 422, 503))
def list_contacts(church: ActiveChurch = Depends(require_church)) -> ContactList:
    return ContactList(items=[ContactOut(**c) for c in contacts.list_contacts(church.id)])


@router.post("/contacts", status_code=201, response_model=ContactOut,
             responses=error_responses(401, 403, 409, 422, 503))
def add_contact(payload: ContactIn, church: ActiveChurch = Depends(require_admin),
                user: CurrentUser = Depends(get_current_user)) -> ContactOut:
    return ContactOut(**contacts.add_contact(church.id, user.id, name=payload.name, email=payload.email))


@router.patch("/contacts/{contact_id}", response_model=ContactOut,
              responses=error_responses(401, 403, 404, 409, 422, 503))
def update_contact(contact_id: uuid.UUID, payload: ContactPatchIn, church: ActiveChurch = Depends(require_admin),
                   user: CurrentUser = Depends(get_current_user)) -> ContactOut:
    return ContactOut(**contacts.update_contact(church.id, user.id, contact_id,
                                                payload.model_dump(include=payload.model_fields_set)))


@router.delete("/contacts/{contact_id}", response_model=DeletedOut,
               responses=error_responses(401, 403, 404, 422, 503))
def delete_contact(contact_id: uuid.UUID, church: ActiveChurch = Depends(require_admin),
                   user: CurrentUser = Depends(get_current_user)) -> DeletedOut:
    contacts.delete_contact(church.id, user.id, contact_id)
    return DeletedOut()
````

**In `backend/api/main.py`, replace:**

````python
from api.routes import (bulletin_images, bulletin_settings, churches, documents, health, hymnals, hymns, invites,
                        lectionary, liturgy, liturgy_review, me, reference, rubric, scripture, services)
````

**with:**

````python
from api.routes import (bulletin_images, bulletin_settings, churches, contacts, documents, health, hymnals, hymns,
                        invites, lectionary, liturgy, liturgy_review, me, reference, rubric, scripture, services)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(bulletin_images.router)
````

**with:**

````python
    app.include_router(bulletin_images.router)
    app.include_router(contacts.router)
````

- [ ] **Step 4: Regenerate the API files, see the tests pass, and the suites**

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git diff --stat -- frontend/src/lib/api | tail -1` then `.venv/bin/python -m pytest -q backend/tests/test_api_contacts.py backend/tests/test_usecase_contacts.py backend/tests/test_openapi_contract.py backend/tests/test_route_guards.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
` 2 files changed, 921 insertions(+)`; `42 passed in <t>s`; `1598 passed, 24 skipped in <t>s`; `typecheck 0`, `lint 0` (the new types are not used until T6).

- [ ] **Step 5: Commit**

```bash
git add backend/api/routes/contacts.py backend/api/main.py backend/tests/test_api_contacts.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Slice 5b-1: GET, POST, PATCH and DELETE /contacts" -m "Every member reads the church's contacts (5b spec's ContactOut, plus
email_valid); owners and admins add (201), edit (only the fields sent)
and delete them, through the locked usecases. The errors are the 6a
spec's: \"Email is required.\", \"Enter a valid email address.\", 409
\"That email is already in your contacts.\", 404 \"Contact not found.\";
a member's write is the role 403. The shared address fixture runs
through POST /contacts; each route passes assert_church_isolated.
OpenAPI and the types regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1598 passed, 24 skipped`; frontend `759 passed` in 92 files.

### Task 5: The duplicate check under the lock, on real Postgres (S Testing → Postgres; clarification 11)

**Files:**
- Create: `backend/tests/test_contacts_postgres.py`

- [ ] **Step 1: Write the tests**

T3 already takes the lock, so these pass at once on Postgres; what proves them is that they fail without it (Build notes: with `lock_church`'s `with_for_update=True` removed, "the second add did not wait for the church-row lock" and, in round 0, `[201, 201]`). Both are skipped without `TEST_DATABASE_URL`, like `test_church_admin_postgres.py`.

**Create `backend/tests/test_contacts_postgres.py`:**

````python
"""POST /contacts on real Postgres (slice 5b-1; 6a spec, Testing → Postgres):
two admins adding the same address at the same moment get one contact and
one 409, because the duplicate check and the insert run under the church-row
lock (usecases.contacts, through lock_and_read_actor).

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs them. The
SQLite fixtures cannot be used here: the owner signs in through GET /me and
the church is made through repos.churches.create_church on pg_db's engine.

- The held lock: the first request's duplicate check (email_contacts.
  email_exists, which usecases.contacts calls through the module attribute
  after taking the lock) waits until the test lets it go; the second request
  must still be waiting a second later. Without the lock it would finish.
- The barrier (the 6a spec's test): both requests wait for each other just
  before the lock, 20 times over, each round with a new address in two cases.
A request that never reaches the wrapper makes the test fail after 10 s
instead of passing vacuously.
"""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

import email_contacts
from db import session_scope
from db.models import Contact
from repos.churches import create_church
from tests.api_helpers import auth_headers, church_headers
from usecases import contacts

pytestmark = pytest.mark.postgres

OWNER = "owner@example.com"


@pytest.fixture
def pg_client(pg_db):
    from tests.api_helpers import make_api_client

    return make_api_client()


@pytest.fixture
def church(pg_client) -> uuid.UUID:
    r = pg_client.get("/me", headers=auth_headers(OWNER))
    assert r.status_code == 200, r.text
    return create_church(name="Grace", timezone="America/New_York", owner_user_id=uuid.UUID(r.json()["user"]["id"]))


def _post(client, church, email):
    return client.post("/contacts", headers=church_headers(OWNER, church), json={"email": email})


def _rows(church, address) -> int:
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(Contact).where(
            Contact.church_id == church, func.lower(Contact.email) == address)).scalar_one()


def test_a_second_add_waits_for_the_first_and_gets_a_409(pg_client, church, monkeypatch):
    inside, release = threading.Event(), threading.Event()
    real = email_contacts.email_exists
    calls = []

    def held(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            inside.set()                   # the first add holds the church-row lock here
            assert release.wait(10), "the test never released the first add"
        return real(*args, **kwargs)

    monkeypatch.setattr(email_contacts, "email_exists", held)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(_post, pg_client, church, "mary@example.org")
        assert inside.wait(10), "the first add never took the lock"
        second = pool.submit(_post, pg_client, church, "MARY@example.org")
        threading.Event().wait(1)          # time for the second add to finish if nothing held it
        assert not second.done(), "the second add did not wait for the church-row lock"
        release.set()
        responses = [first.result(10), second.result(10)]
    assert [r.status_code for r in responses] == [201, 409]
    assert responses[1].json()["error"]["message"] == "That email is already in your contacts."
    assert _rows(church, "mary@example.org") == 1


def test_two_adds_of_one_address_at_once_make_one_contact_twenty_times(pg_client, church, monkeypatch):
    barrier = threading.Barrier(2)
    real = contacts.lock_and_read_actor

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        return real(*args, **kwargs)

    monkeypatch.setattr(contacts, "lock_and_read_actor", together)
    for round_ in range(20):
        address = f"mary{round_}@example.org"
        with ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(lambda email: _post(pg_client, church, email), [address, address.upper()]))
        assert sorted(r.status_code for r in responses) == [201, 409], f"round {round_}"
        assert _rows(church, address) == 1, f"round {round_}"
````

- [ ] **Step 2: Run them**

Run: `.venv/bin/python -m pytest -q backend/tests/test_contacts_postgres.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`2 skipped in <t>s`; `1598 passed, 26 skipped in <t>s`.

With a local throwaway Postgres (never a real database), `TEST_DATABASE_URL=postgresql://postgres@localhost:<port>/postgres .venv/bin/python -m pytest -q -m postgres 2>&1 | tail -1` gives `26 passed, 1598 deselected, 1 warning in <t>s`; without one, CI's `backend-postgres` runs them.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_contacts_postgres.py
git commit -q -m "Slice 5b-1: two adds of one address at once make one contact (Postgres)" -m "On real Postgres: while one add holds the church-row lock, a second add
of the same address in other capitals waits and then gets the 409; and
the 6a spec's race, two threads past a barrier, 20 rounds, always ends
with one 201, one 409 and one row. Both fail with the lock turned off.
Skipped without TEST_DATABASE_URL; CI's backend-postgres runs them." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1598 passed, 26 skipped`; frontend `759 passed` in 92 files.


## The app (T6-T8)

### Task 6: The contact forms' rules, the types and the queries (B "Query hooks"; S "Queries"; clarification 14)

**Files:**
- Create: `frontend/src/lib/settings/contacts.test.ts`, `frontend/src/lib/settings/contacts.ts`, `frontend/src/lib/queries/contacts.ts`
- Modify: `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/api/types.ts`

- [ ] **Step 1: Write the failing test**

The fixtures gain `contact()` (Mary Jones, `mary@example.org`) and `contactList()` (Mary Jones, then a nameless `office@example.org`), used here and by the page's tests (T7).

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  ChurchProfile,
````

**with:**

````ts
  ChurchProfile,
  Contact,
  ContactList,
````

**Append to `frontend/src/test/fixtures/index.ts`:**

````ts

// --- slice 5b-1: contacts -------------------------------------------------------------------------

/** One of Grace's contacts (`ContactOut`): Mary Jones at an example address, which passes the check. */
export function contact(overrides: Partial<Contact> = {}): Contact {
  return {
    id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e01",
    name: "Mary Jones",
    email: "mary@example.org",
    email_valid: true,
    ...overrides,
  };
}

/** `GET /contacts`: Mary Jones, then the church office, which has no name. */
export function contactList(items: Contact[] = [
  contact(),
  contact({ id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e02", name: null, email: "office@example.org" }),
]): ContactList {
  return { items };
}
````

**Create `frontend/src/lib/settings/contacts.test.ts`:**

````ts
import { describe, expect, it } from "vitest";

import { contact } from "@/test/fixtures";

import { contactFormFrom, contactLabel, contactPatch, EMPTY_CONTACT, hasTyped, newContactBody } from "./contacts";

describe("the Contacts page's forms (slice 5b-1)", () => {
  it("names a contact by its name, or by its address when it has none", () => {
    expect(contactLabel(contact())).toBe("Mary Jones");
    expect(contactLabel(contact({ name: null, email: "office@example.org" }))).toBe("office@example.org");
  });

  it("sends a new contact trimmed, with no name as null", () => {
    expect(newContactBody({ name: " Mary Jones ", email: " mary@example.org " })).toEqual({
      name: "Mary Jones",
      email: "mary@example.org",
    });
    expect(newContactBody({ name: "   ", email: "office@example.org" })).toEqual({ name: null, email: "office@example.org" });
  });

  it("sends an edit's changed fields only, trimmed, and a cleared name as null", () => {
    const base = contactFormFrom(contact());
    expect(base).toEqual({ name: "Mary Jones", email: "mary@example.org" });
    expect(contactPatch(base, { ...base, name: " Mary Jones " })).toEqual({});
    expect(contactPatch(base, { ...base, name: "Mary Smith" })).toEqual({ name: "Mary Smith" });
    expect(contactPatch(base, { ...base, name: "" })).toEqual({ name: null });
    expect(contactPatch(base, { name: "Mary", email: "Mary@example.org" })).toEqual({ name: "Mary", email: "Mary@example.org" });
    expect(contactFormFrom(contact({ name: null }))).toEqual({ name: "", email: "mary@example.org" });
  });

  it("knows when the add form holds something", () => {
    expect(hasTyped(EMPTY_CONTACT)).toBe(false);
    expect(hasTyped({ name: "  ", email: " " })).toBe(false);
    expect(hasTyped({ name: "", email: "m" })).toBe(true);
  });
});
````

- [ ] **Step 2: See it fail**

Run: `(cd frontend && npx vitest run src/lib/settings/contacts.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`contacts.ts` does not exist yet):
```
 FAIL  |unit| src/lib/settings/contacts.test.ts [ src/lib/settings/contacts.test.ts ]
      Tests  no tests
```

- [ ] **Step 3: Write the types, the rules and the queries**

The queries are used by the page (T7), whose tests cover their cache work and their errors.

**Append to `frontend/src/lib/api/types.ts`:**

````ts

/**
 * `/contacts` (slice 5b-1): one contact (`name` null when it has none;
 * `email_valid` false for a saved address the send-time check refuses), the
 * list, the body of `POST /contacts` and of `PATCH /contacts/{id}` (only the
 * fields that change).
 */
export type Contact = components["schemas"]["ContactOut"];
export type ContactList = components["schemas"]["ContactList"];
export type ContactBody = components["schemas"]["ContactIn"];
export type ContactPatch = components["schemas"]["ContactPatchIn"];
````

**Create `frontend/src/lib/settings/contacts.ts`:**

````ts
/**
 * The Contacts page's forms (slice 5b-1; 6a spec "Contacts"). The server
 * checks and cleans every address (the one rule 5b-2 sends with); the page
 * trims what it sends, as the server would, so an edit that only adds spaces
 * sends nothing.
 */
import type { Contact, ContactBody, ContactPatch } from "@/lib/api/types";

export type ContactForm = { name: string; email: string };

export const EMPTY_CONTACT: ContactForm = { name: "", email: "" };

/** How a contact is named on the page: its name, or its address when it has none. */
export function contactLabel(contact: Pick<Contact, "name" | "email">): string {
  return contact.name ?? contact.email;
}

/** The edit form a contact starts at, and its baseline. */
export function contactFormFrom(contact: Contact): ContactForm {
  return { name: contact.name ?? "", email: contact.email };
}

/** `POST /contacts`'s body: both fields trimmed; no name is null. */
export function newContactBody(form: ContactForm): ContactBody {
  const name = form.name.trim();
  return { name: name === "" ? null : name, email: form.email.trim() };
}

/** `PATCH /contacts/{id}`'s body: each field whose trimmed value differs from the baseline's; a cleared name is null. */
export function contactPatch(baseline: ContactForm, form: ContactForm): ContactPatch {
  const patch: ContactPatch = {};
  const name = form.name.trim();
  if (name !== baseline.name.trim()) patch.name = name === "" ? null : name;
  const email = form.email.trim();
  if (email !== baseline.email.trim()) patch.email = email;
  return patch;
}

/** True while the add form holds something a reload would lose. */
export function hasTyped(form: ContactForm): boolean {
  return form.name.trim() !== "" || form.email.trim() !== "";
}
````

**Create `frontend/src/lib/queries/contacts.ts`:**

````ts
/**
 * The church's contacts (slice 5b-1; 5b spec `useContacts`, 6a spec contact
 * mutations): `GET /contacts` under ["church", id, "contacts"], and the add,
 * edit and delete an admin makes on the Contacts page.
 *
 * Each write puts its answer in the cached list at once (the new row last, as
 * the server orders it; an edited row in its place; a deleted row gone) and
 * then refetches the list. A 422 or 409 is the form's to show under its
 * field, so it is not toasted; a 401 or a lost church the app already reports;
 * a role 403 (an admin demoted meanwhile) is toasted and refetches the church
 * profile, which carries the role, so the page turns read-only; anything
 * else, a 404 for a contact deleted elsewhere among them, is toasted.
 */
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { Contact, ContactBody, ContactList, ContactPatch, DeletedOut } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

/** `GET /contacts` for the active church. */
export function useContacts(): UseQueryResult<ContactList, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<ContactList, ApiError>({
    queryKey: keys.contacts(church.id),
    queryFn: ({ signal }) => api.church<ContactList>("/contacts", { signal }),
  });
}

/** The cache work and the error handling every contact write shares. */
function useContactWrite<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  apply: (items: Contact[], data: TData, variables: TVariables) => Contact[],
) {
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.contacts(church.id);
  return useChurchMutation<TData, ApiError, TVariables>({
    mutationFn,
    onSuccess: async (data, variables) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<ContactList>(key, (list) => (list ? { items: apply(list.items, data, variables) } : list));
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e) || e.status === 409 || e.status === 422) return;
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
      if (e.status === 404) void queryClient.invalidateQueries({ queryKey: key });
    },
  });
}

/** `POST /contacts` (admins). */
export function useCreateContact() {
  const api = useApi();
  return useContactWrite<Contact, ContactBody>(
    (body) => api.church<Contact>("/contacts", { method: "POST", json: body }),
    (items, added) => [...items, added],
  );
}

/** `PATCH /contacts/{id}` (admins): only the fields that change. */
export function useUpdateContact() {
  const api = useApi();
  return useContactWrite<Contact, { id: string; patch: ContactPatch }>(
    ({ id, patch }) => api.church<Contact>(`/contacts/${encodeURIComponent(id)}`, { method: "PATCH", json: patch }),
    (items, saved) => items.map((c) => (c.id === saved.id ? saved : c)),
  );
}

/** `DELETE /contacts/{id}` (admins). */
export function useDeleteContact() {
  const api = useApi();
  return useContactWrite<DeletedOut, string>(
    (id) => api.church<DeletedOut>(`/contacts/${encodeURIComponent(id)}`, { method: "DELETE" }),
    (items, _deleted, id) => items.filter((c) => c.id !== id),
  );
}
````

- [ ] **Step 4: See it pass, and the suite**

Run: `(cd frontend && npx vitest run src/lib/settings/contacts.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
`      Tests  4 passed (4)`; ` Test Files  93 passed (93)` and `      Tests  763 passed (763)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/test/fixtures/index.ts frontend/src/lib/settings/contacts.ts frontend/src/lib/settings/contacts.test.ts frontend/src/lib/queries/contacts.ts
git commit -q -m "Slice 5b-1: the contact forms' rules and the contacts queries" -m "lib/settings/contacts.ts: a contact's label (its name, or its address),
the add body (trimmed, no name as null) and the edit's patch (only what
changed, a cleared name as null). lib/queries/contacts.ts: useContacts
and the add, edit and delete mutations, which put the answer in the
cached list at once and refetch it; a 422 or 409 is left to the form, a
role 403 refetches the profile, a 404 the list." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1598 passed, 26 skipped`; frontend `763 passed` in 93 files.

### Task 7: The Contacts page (S UX §4; clarifications 3-6, 13, 15)

**Files:**
- Create: `frontend/src/components/settings/contacts-settings-page.test.tsx`, `frontend/src/components/settings/contacts-settings-page.tsx`, `frontend/src/app/(signed-in)/(church)/settings/contacts/page.tsx`

- [ ] **Step 1: Write the failing tests**

The page's tests render it inside the Settings layout, as the route is. `contactsServer` is a small fake `/contacts` whose `GET` answers with what the writes left, so the refetch after each write shows what a real server would (a fixed `GET` answer would put a deleted row back). The leave-guard test clicks the Settings nav's **Church**, which exists since 6a-1 (T8 adds **Contacts** to the nav).

**Create `frontend/src/components/settings/contacts-settings-page.test.tsx`:**

````tsx
/**
 * Settings → Contacts (slice 5b-1; 6a spec "Contacts"): every member reads
 * the list, admins add, edit and delete. Rendered inside the Settings layout,
 * as the route is, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import ContactsSettingsRoute from "@/app/(signed-in)/(church)/settings/contacts/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Contact } from "@/lib/api/types";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, contact, contactList, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { ADMINS_ONLY, CONTACTS_INTRO, INVALID_ADDRESS_ADMIN, INVALID_ADDRESS_MEMBER } from "./contacts-settings-page";

afterEach(() => {
  toast.dismiss();
});

const BROKEN = contact({ id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e03", name: "Two at once", email: "a@example.org, b@example.org", email_valid: false });

/** A fake `/contacts`: `GET` answers with what the writes left, as the server would after a refetch. */
function contactsServer(initial: Contact[] = contactList().items) {
  let items = [...initial];
  return {
    list: () => contactList(items),
    add: (added: Contact) => {
      items = [...items, added];
      return { status: 201, body: added };
    },
    save: (saved: Contact) => {
      items = items.map((c) => (c.id === saved.id ? saved : c));
      return saved;
    },
    remove: (id: string) => {
      items = items.filter((c) => c.id !== id);
      return { deleted: true };
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({ "GET /contacts": contactList(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <ContactsSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/contacts" },
  );
  return { ...view, api };
}

function writes(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/contacts"));
}

function rows() {
  return within(screen.getByRole("list", { name: "Contacts" })).getAllByRole("listitem");
}

describe("Settings → Contacts (slice 5b-1)", () => {
  it("shows a member the list as text, with the note, a flag on a bad address, and no controls", async () => {
    renderPage("member", { "GET /contacts": contactList([contact(), contact({ id: "c-2", name: null, email: "office@example.org" }), BROKEN]) });
    expect(await screen.findByText("Mary Jones")).toBeInTheDocument();
    expect(screen.getByText(CONTACTS_INTRO)).toBeInTheDocument();
    expect(screen.getByText(ADMINS_ONLY)).toBeInTheDocument();
    expect(rows().map((row) => row.textContent)).toEqual([
      "Mary Jonesmary@example.org",
      "office@example.org",
      `Two at oncea@example.org, b@example.org${INVALID_ADDRESS_MEMBER}`,
    ]);
    expect(screen.queryByRole("button", { name: /^(Edit|Delete) / })).toBeNull();
    expect(screen.queryByRole("button", { name: "Add contact" })).toBeNull();
    expect(screen.queryAllByRole("textbox")).toEqual([]);
  });

  it("lets an admin add a contact: the row appears, the fields clear and Name has focus", async () => {
    const added = contact({ id: "c-new", name: "Sam Sample", email: "sam@example.org" });
    const server = contactsServer();
    const { api, user } = renderPage("admin", { "GET /contacts": server.list, "POST /contacts": () => server.add(added) });
    await screen.findByText("Mary Jones");
    const name = screen.getByLabelText("Name (optional)");
    const email = screen.getByLabelText("Email");
    await user.type(name, " Sam Sample ");
    await user.type(email, " sam@example.org ");
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(await screen.findByText("Sam Sample")).toBeInTheDocument();
    expect(writes(api, "POST")[0].body).toEqual({ name: "Sam Sample", email: "sam@example.org" });
    expect(writes(api, "POST")[0].headers["x-church-id"]).toBe(church().id);
    expect(rows()).toHaveLength(3);
    expect(name).toHaveValue("");
    expect(email).toHaveValue("");
    await waitFor(() => expect(name).toHaveFocus());
  });

  it("says what is wrong with an address under Email and focuses it", async () => {
    const { api, user } = renderPage("admin", {
      "POST /contacts": fakeError(409, "conflict", "That email is already in your contacts."),
    });
    await screen.findByText("Mary Jones");
    const email = screen.getByLabelText("Email");
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Email is required.");
    expect(writes(api, "POST")).toHaveLength(0);
    await user.type(email, "MARY@example.org");
    expect(screen.queryByRole("alert")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(await screen.findByText("That email is already in your contacts.")).toBeInTheDocument();
    expect(email).toHaveAttribute("aria-invalid", "true");
    await waitFor(() => expect(email).toHaveFocus());
    expect(email).toHaveValue("MARY@example.org");

    api.set("POST /contacts", fakeError(422, "invalid_request", "Enter a valid email address.", { fields: { email: "Enter a valid email address." } }));
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
  });

  it("lets an admin edit a contact: only the changed field is sent and the row shows the answer", async () => {
    const server = contactsServer();
    const { api, user } = renderPage("admin", {
      "GET /contacts": server.list,
      [`PATCH /contacts/${contact().id}`]: (r: RecordedRequest) => server.save({ ...contact(), ...(r.body as Partial<Contact>) }),
    });
    await user.click(await screen.findByRole("button", { name: "Edit Mary Jones" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit contact" });
    const name = within(dialog).getByLabelText("Name (optional)");
    await user.clear(name);
    await user.type(name, "Mary Smith");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(writes(api, "PATCH")[0].body).toEqual({ name: "Mary Smith" });
    expect(rows()[0]).toHaveTextContent("Mary Smithmary@example.org");
  });

  it("shows an edit's 409 in the dialog, and Cancel leaves the contact as it was", async () => {
    const { api, user } = renderPage("admin", {
      [`PATCH /contacts/${contact().id}`]: fakeError(409, "conflict", "That email is already in your contacts."),
    });
    await user.click(await screen.findByRole("button", { name: "Edit Mary Jones" }));
    const dialog = await screen.findByRole("dialog", { name: "Edit contact" });
    const email = within(dialog).getByLabelText("Email");
    await user.clear(email);
    await user.type(email, "office@example.org");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await within(dialog).findByText("That email is already in your contacts.")).toBeInTheDocument();
    expect(writes(api, "PATCH")[0].body).toEqual({ email: "office@example.org" });
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(rows()[0]).toHaveTextContent("Mary Jonesmary@example.org");
  });

  it("asks before deleting, then removes the row", async () => {
    const server = contactsServer();
    const office = server.list().items[1];
    const { api, user } = renderPage("admin", {
      "GET /contacts": server.list,
      [`DELETE /contacts/${office.id}`]: () => server.remove(office.id),
    });
    await user.click(await screen.findByRole("button", { name: "Delete office@example.org" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Delete office@example.org?" });
    expect(confirm).toHaveTextContent("They won't be offered as a bulletin recipient anymore.");
    await user.click(within(confirm).getByRole("button", { name: "Delete contact" }));
    await waitFor(() => expect(screen.queryByText("office@example.org")).toBeNull());
    expect(writes(api, "DELETE")).toHaveLength(1);
    expect(rows()).toHaveLength(1);
  });

  it("flags a saved address the send-time check refuses, and the admin fixes it", async () => {
    const fixed = { ...BROKEN, email: "a@example.org", email_valid: true };
    const server = contactsServer([BROKEN]);
    const { user } = renderPage("admin", { "GET /contacts": server.list, [`PATCH /contacts/${BROKEN.id}`]: () => server.save(fixed) });
    expect(await screen.findByText(INVALID_ADDRESS_ADMIN)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Edit Two at once" }));
    const email = within(await screen.findByRole("dialog")).getByLabelText("Email");
    await user.clear(email);
    await user.type(email, "a@example.org{Enter}");
    await waitFor(() => expect(screen.queryByText(INVALID_ADDRESS_ADMIN)).toBeNull());
  });

  it("shows each role its empty state", async () => {
    const { unmount } = renderPage("admin", { "GET /contacts": contactList([]) });
    expect(await screen.findByText("Add the people who receive the bulletin, like your church secretary.")).toBeInTheDocument();
    expect(screen.getByText("No contacts yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add contact" })).toBeInTheDocument();
    unmount();
    renderPage("member", { "GET /contacts": contactList([]) });
    expect(await screen.findByText("Ask an admin to add bulletin recipients.")).toBeInTheDocument();
  });

  it("asks before leaving with something typed in the add form", async () => {
    const { user } = renderPage("admin");
    await user.type(await screen.findByLabelText("Email"), "sam@example.org");
    await user.click(screen.getByRole("link", { name: "Church" }));
    const dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/settings/church");
  });

  it("toasts a role 403 and refetches the church profile, so the page turns read-only", async () => {
    const { user, queryClient } = renderPage("admin", {
      "POST /contacts": fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.type(await screen.findByLabelText("Email"), "sam@example.org");
    await user.click(screen.getByRole("button", { name: "Add contact" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
  });

  it("shows the error state with Retry when the list cannot be read", async () => {
    renderPage("admin", { "GET /contacts": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/contacts-settings-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the route and the page do not exist yet):
```
 FAIL  |dom| src/components/settings/contacts-settings-page.test.tsx [ src/components/settings/contacts-settings-page.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: Write the page and its route**

**Create `frontend/src/components/settings/contacts-settings-page.tsx`:**

````tsx
"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import type { Contact } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useContacts, useCreateContact, useDeleteContact, useUpdateContact } from "@/lib/queries/contacts";
import {
  contactFormFrom,
  contactLabel,
  contactPatch,
  EMPTY_CONTACT,
  hasTyped,
  newContactBody,
  type ContactForm,
} from "@/lib/settings/contacts";

export const CONTACTS_INTRO = "People you can email the bulletin to. Emailing it from the Review step comes in a later update.";
export const ADMINS_ONLY = "Only admins can add or change contacts.";
export const INVALID_ADDRESS_ADMIN = "This address doesn't look valid. Edit it.";
export const INVALID_ADDRESS_MEMBER = "This address doesn't look valid. An admin can fix it.";
export const EMAIL_REQUIRED = "Email is required.";
const EMPTY_TITLE = "No contacts yet";
const EMPTY_ADMIN = "Add the people who receive the bulletin, like your church secretary.";
const EMPTY_MEMBER = "Ask an admin to add bulletin recipients.";
const DELETE_BODY = "They won't be offered as a bulletin recipient anymore.";

type Field = keyof ContactForm;
type FieldErrors = Partial<Record<Field, string>>;

/**
 * A failed add or edit's message for its field: a 422's `fields` (name or
 * email), a 409 (the address is taken) under the email. Null for any other
 * failure, which the mutation toasts.
 */
function fieldErrors(e: unknown): FieldErrors | null {
  if (!(e instanceof ApiError)) return null;
  if (e.status === 409) return { email: e.message };
  if (e.status !== 422 || !e.fields) return null;
  const found: FieldErrors = {};
  for (const field of ["name", "email"] as const) {
    if (e.fields[field]) found[field] = e.fields[field];
  }
  return Object.keys(found).length > 0 ? found : null;
}

/**
 * `/settings/contacts` (slice 5b-1; 6a spec "Contacts"): the people the
 * bulletin is emailed to. Every member reads the list (the name in bold with
 * the address under it, the address alone when there is no name, a note under
 * an address the send-time check refuses); owners and admins also edit and
 * delete each one and add new ones below the list. Leaving with something
 * typed in the add form asks first (`LeaveGuard`); the edit dialog's Cancel
 * discards its edits.
 */
export function ContactsSettingsPage() {
  const church = useChurch();
  const admin = isAdmin(church.role);
  const list = useContacts();
  const nameRef = useRef<HTMLInputElement>(null);
  const [editing, setEditing] = useState<Contact | null>(null);
  const [deleting, setDeleting] = useState<Contact | null>(null);
  const remove = useDeleteContact();

  let body: ReactNode;
  if (list.data) {
    body =
      list.data.items.length === 0 ? (
        <EmptyState title={EMPTY_TITLE} description={admin ? EMPTY_ADMIN : EMPTY_MEMBER} />
      ) : (
        <ul className="divide-y rounded-lg border" aria-label="Contacts">
          {list.data.items.map((contact) => (
            <ContactRow
              key={contact.id}
              contact={contact}
              admin={admin}
              onEdit={() => setEditing(contact)}
              onDelete={() => setDeleting(contact)}
            />
          ))}
        </ul>
      );
  } else if (list.isError) {
    body = <ErrorState error={list.error} onRetry={() => void list.refetch()} retrying={list.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="contacts-title" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="contacts-title" className="text-lg font-semibold">
          Contacts
        </h2>
        <p className="text-sm text-muted-foreground">{CONTACTS_INTRO}</p>
      </div>
      {admin ? null : (
        <Alert role="status">
          <AlertDescription>{ADMINS_ONLY}</AlertDescription>
        </Alert>
      )}
      {body}
      {admin ? <ContactAddForm nameRef={nameRef} /> : null}
      {editing ? <ContactEditDialog contact={editing} onClose={() => setEditing(null)} /> : null}
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title={deleting ? `Delete ${contactLabel(deleting)}?` : ""}
        description={DELETE_BODY}
        confirmLabel="Delete contact"
        destructive
        pending={remove.isPending}
        finalFocus={nameRef}
        onConfirm={() => {
          if (deleting === null) return;
          remove.mutate(deleting.id, { onSettled: () => setDeleting(null) });
        }}
      />
    </section>
  );
}

function ContactRow({
  contact,
  admin,
  onEdit,
  onDelete,
}: {
  contact: Contact;
  admin: boolean;
  onEdit(): void;
  onDelete(): void;
}) {
  const label = contactLabel(contact);
  return (
    <li className="flex items-start gap-2 px-4 py-3">
      <div className="grid min-w-0 flex-1 gap-0.5">
        {contact.name !== null ? <p className="font-semibold break-words">{contact.name}</p> : null}
        <p className={contact.name !== null ? "text-sm text-muted-foreground break-all" : "text-sm break-all"}>
          {contact.email}
        </p>
        {contact.email_valid ? null : (
          <p className="text-sm text-amber-700 dark:text-amber-400">
            {admin ? INVALID_ADDRESS_ADMIN : INVALID_ADDRESS_MEMBER}
          </p>
        )}
      </div>
      {admin ? (
        <div className="flex shrink-0 gap-1">
          <Button type="button" variant="ghost" size="icon" className="size-11 md:size-8" aria-label={`Edit ${label}`} onClick={onEdit}>
            <Pencil aria-hidden="true" />
          </Button>
          <Button type="button" variant="ghost" size="icon" className="size-11 md:size-8" aria-label={`Delete ${label}`} onClick={onDelete}>
            <Trash2 aria-hidden="true" />
          </Button>
        </div>
      ) : null}
    </li>
  );
}

/** One field of a contact form, with its error under it (`role="alert"`). */
function ContactField({
  id,
  label,
  field,
  value,
  error,
  inputRef,
  onChange,
}: {
  id: string;
  label: string;
  field: Field;
  value: string;
  error: string | undefined;
  inputRef?: RefObject<HTMLInputElement | null>;
  onChange(value: string): void;
}) {
  const email = field === "email";
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        ref={inputRef}
        value={value}
        maxLength={email ? 320 : 200}
        className="h-11"
        {...(email ? { inputMode: "email" as const, autoCapitalize: "none", autoCorrect: "off", spellCheck: false } : {})}
        autoComplete="off"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

/** Below the list, for admins: Name (optional), Email, **Add contact**. */
function ContactAddForm({ nameRef }: { nameRef: RefObject<HTMLInputElement | null> }) {
  const create = useCreateContact();
  const emailRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<ContactForm>(EMPTY_CONTACT);
  const [errors, setErrors] = useState<FieldErrors>({});

  const update = (field: Field, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
  };

  const focusFirst = (found: FieldErrors) => (found.name ? nameRef : emailRef).current?.focus();

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (create.isPending) return;
    if (form.email.trim() === "") {
      setErrors({ email: EMAIL_REQUIRED });
      emailRef.current?.focus();
      return;
    }
    create.mutate(newContactBody(form), {
      onSuccess: () => {
        setForm(EMPTY_CONTACT);
        setErrors({});
        nameRef.current?.focus();
      },
      onError: (e) => {
        const found = fieldErrors(e);
        if (found === null) return;
        setErrors(found);
        focusFirst(found);
      },
    });
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-labelledby="contact-add-title" className="grid gap-4 rounded-lg border p-4">
      <h3 id="contact-add-title" className="text-base font-medium">
        Add a contact
      </h3>
      <ContactField id="contact-add-name" label="Name (optional)" field="name" value={form.name} error={errors.name} inputRef={nameRef} onChange={(v) => update("name", v)} />
      <ContactField id="contact-add-email" label="Email" field="email" value={form.email} error={errors.email} inputRef={emailRef} onChange={(v) => update("email", v)} />
      <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={create.isPending}>
        Add contact
      </PendingButton>
      <LeaveGuard when={hasTyped(form)} />
    </form>
  );
}

/** **Edit** on a row: Name and Email, **Save changes**; only the fields that change are sent. */
function ContactEditDialog({ contact, onClose }: { contact: Contact; onClose(): void }) {
  const save = useUpdateContact();
  const [baseline] = useState(() => contactFormFrom(contact));
  const [form, setForm] = useState<ContactForm>(baseline);
  const [errors, setErrors] = useState<FieldErrors>({});
  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);

  const update = (field: Field, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (save.isPending) return;
    if (form.email.trim() === "") {
      setErrors({ email: EMAIL_REQUIRED });
      emailRef.current?.focus();
      return;
    }
    const patch = contactPatch(baseline, form);
    if (Object.keys(patch).length === 0) {
      onClose();
      return;
    }
    save.mutate(
      { id: contact.id, patch },
      {
        onSuccess: onClose,
        onError: (e) => {
          const found = fieldErrors(e);
          if (found === null) return;
          setErrors(found);
          (found.name ? nameRef : emailRef).current?.focus();
        },
      },
    );
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent
        showCloseButton={false}
        className="max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto md:max-w-lg"
      >
        <DialogHeader>
          <DialogTitle>Edit contact</DialogTitle>
          <DialogDescription>{contactLabel(contact)}</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} noValidate className="grid gap-4">
          <ContactField id="contact-edit-name" label="Name (optional)" field="name" value={form.name} error={errors.name} inputRef={nameRef} onChange={(v) => update("name", v)} />
          <ContactField id="contact-edit-email" label="Email" field="email" value={form.email} error={errors.email} inputRef={emailRef} onChange={(v) => update("email", v)} />
          <DialogFooter className="max-md:rounded-b-none max-md:pb-[calc(1rem+env(safe-area-inset-bottom))]">
            <DialogClose render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>Cancel</DialogClose>
            <PendingButton type="submit" size="touch" className="md:h-8" pending={save.isPending}>
              Save changes
            </PendingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/contacts/page.tsx`:**

````tsx
"use client";

import { ContactsSettingsPage } from "@/components/settings/contacts-settings-page";

/** Settings → Contacts: the people the bulletin is emailed to (slice 5b-1; F §4.1). */
export default function ContactsSettingsRoute() {
  return <ContactsSettingsPage />;
}
````

- [ ] **Step 4: See them pass (three times), and the suite**

Run: `(cd frontend && npx vitest run src/components/settings 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (three times) then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
three times `      Tests  25 passed (25)` (the Contacts page's 11, the Church page's 12 and the Settings layout's 2); ` Test Files  94 passed (94)` and `      Tests  774 passed (774)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/contacts-settings-page.tsx frontend/src/components/settings/contacts-settings-page.test.tsx 'frontend/src/app/(signed-in)/(church)/settings/contacts/page.tsx'
git commit -q -m "Slice 5b-1: the Contacts page" -m "Settings → Contacts: every member reads the church's contacts (the name
in bold over the address, the address alone when there is none, and
\"This address doesn't look valid.\" under an address the send-time
check refuses). Owners and admins add one below the list, edit one in a
dialog (only what changed is sent) and delete one after a confirmation;
a refused address or a duplicate shows under Email, and leaving with
something typed in the add form asks first." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1598 passed, 26 skipped`; frontend `774 passed` in 94 files.

### Task 8: Contacts in the Settings nav (S "Settings nav"; clarification 2)

**Files:**
- Modify: `frontend/src/components/settings/settings-layout.test.tsx`, `frontend/src/components/settings/sections.ts`

- [ ] **Step 1: Write the failing test**

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    ]);
    expect(links[0]).toHaveAttribute("aria-current", "page");
    expect(links[1]).not.toHaveAttribute("aria-current");
````

**with:**

````tsx
      ["Contacts", "/settings/contacts"],
    ]);
    expect(links[0]).toHaveAttribute("aria-current", "page");
    expect(links[1]).not.toHaveAttribute("aria-current");
    expect(links[2]).not.toHaveAttribute("aria-current");
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
  it("shows a member the same sections, and /settings opens Church", () => {
    renderShell("member", "/settings");
    expect(screen.getByText("You're a member of Grace.")).toBeInTheDocument();
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(2);
````

**with:**

````tsx
  it("marks Contacts current on its page (slice 5b-1)", () => {
    renderShell("member", "/settings/contacts");
    const links = within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link");
    expect(links.filter((link) => link.getAttribute("aria-current") === "page").map((link) => link.textContent)).toEqual([
      "Contacts",
    ]);
  });

  it("shows a member the same sections, and /settings opens Church", () => {
    renderShell("member", "/settings");
    expect(screen.getByText("You're a member of Grace.")).toBeInTheDocument();
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(3);
````

- [ ] **Step 2: See it fail**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected:**
```
   × the Settings area (slice 6a-1) > shows the heading, who you are in the church, and the sections with the current one marked <t>ms
   × the Settings area (slice 6a-1) > marks Contacts current on its page (slice 5b-1) <t>ms
   × the Settings area (slice 6a-1) > shows a member the same sections, and /settings opens Church <t>ms
      Tests  3 failed (3)
```

- [ ] **Step 3: Add the entry**

**In `frontend/src/components/settings/sections.ts`, replace:**

````ts
 * under /settings); 5b adds Account and Contacts.
````

**with:**

````ts
 * under /settings); 5b-1 adds Contacts, last for now (the final order puts it
 * after every page about the church's services), and 5b-2 Account after it.
````

**In `frontend/src/components/settings/sections.ts`, replace:**

````ts
  { href: "/bulletin-settings", label: "Bulletin" },
````

**with:**

````ts
  { href: "/bulletin-settings", label: "Bulletin" },
  { href: "/settings/contacts", label: "Contacts" },
````

- [ ] **Step 4: See it pass, and the suite**

Run: `(cd frontend && npx vitest run src/components/settings src/components/app/app-header.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
`      Tests  32 passed (32)`; ` Test Files  94 passed (94)` and `      Tests  775 passed (775)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/sections.ts frontend/src/components/settings/settings-layout.test.tsx
git commit -q -m "Slice 5b-1: Contacts in the Settings nav" -m "SETTINGS_SECTIONS gains Contacts after Church and Bulletin: the final
order puts Contacts after every page about the church's services, so no
entry moves when 6a-2, 6a-3 and 5b-2 add theirs. It is marked current on
its page." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1598 passed, 26 skipped`; frontend `775 passed` in 94 files.

## Docs, verification, the PR, the merge (T9-T11)

### Task 9: Docs: the manual check items (clarification 16)

**Files:**
- Modify: `backend/tests/test_slice1_docs.py`, `docs/manual-verification.md`

- [ ] **Step 1: Append the items and move the headings pin**

**In `backend/tests/test_slice1_docs.py`, replace:**

````python
    # PR 1 "## Printed bulletin" and slice 6a-1 "## Slice 6a".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-9:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4", "## Service reviewer",
                        "## Slice 5a", "## Printed bulletin", "## Slice 6a"]
````

**with:**

````python
    # PR 1 "## Printed bulletin", slice 6a-1 "## Slice 6a" and slice 5b-1 "## Slice 5b".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-10:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4", "## Service reviewer",
                        "## Slice 5a", "## Printed bulletin", "## Slice 6a", "## Slice 5b"]
````

**Append to `docs/manual-verification.md`:**

````markdown

## Slice 5b

Run on the production URL https://worship-service-builder.vercel.app, on an
iPhone with Safari at 375 px and on desktop Chrome. These are the checks for
5b-1 (the Contacts page in Settings), as the owner's 5b planning answers of
2026-10-06 split 5b into two PRs; 5b-2 (the Gmail connection and emailing the
bulletin) adds its own items here. After the 5b-1 merge the owner's guided
check (one step at a time on the phone) covers the items marked "(owner,
after 5b-1)"; the results go into `docs/ops-runbook.md` → "Slice 5b-1
record". Record what the page shows (how many contacts, how many flagged),
never an email address, a person's name or a church id.

- [ ] (owner, after 5b-1) **1.** **Settings** lists **Church**, **Bulletin** and **Contacts**. Tap **Contacts**: the church's saved contacts are listed (a name in bold with its address under it, an address alone when there is no name). Under any address the app could not email, "This address doesn't look valid. Edit it." shows. Note how many contacts there are, how many are flagged, and whether any address is listed twice.
- [ ] (owner, after 5b-1) **2.** Fix each flagged contact with its pencil button (**Edit contact**, **Save changes**): the note goes away. With nothing flagged, add a contact named "Test" with the address test@example.com instead, edit its name, try adding TEST@example.com again ("That email is already in your contacts."), then delete it with its bin button ("Delete Test?", **Delete contact**).
- [ ] (owner, after 5b-1) **3.** Type a name in the add form without adding it and tap **Church** in the Settings sections: "Discard unsaved changes?" asks first. At 375 px: no sideways scroll; the section links, the pencil and bin buttons and **Add contact** are easy to tap.
- [ ] **4.** Signed in as a plain member of the same church: **Settings** → **Contacts** shows "Only admins can add or change contacts." and the list with no buttons and no add form.
- [ ] **5.** Two tabs as an admin: delete a contact in one, then edit it in the other: "Contact not found." and the row goes away.
- [ ] **6.** Add a contact as `Someone@Example.ORG`: it is saved and listed as `Someone@example.org` (the domain lower-cased, the rest as typed).
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected:**
`89 passed in <t>s`; `4`; `0`; ` 2 files changed, 22 insertions(+), 3 deletions(-)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -q -m "Docs: slice 5b-1 manual checks" -m "docs/manual-verification.md gains \"## Slice 5b\": the owner's phone
check after 5b-1 (Contacts in Settings and the flagged addresses, fixing
one or adding, editing, refusing a duplicate and deleting a test
contact, the leave guard and the page at 375 px) and the agent's checks
(a member, a contact deleted in another tab, the domain lower-cased).
test_slice1_docs.py pins the last ten ## headings, the new one last." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1598 passed, 26 skipped`; frontend `775 passed` in 94 files.


### Task 10: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
ls backend/migrations/versions | grep -c '^0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `7`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 10)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the frontend three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/settings")
```

**Expected:** `1598 passed, 26 skipped in <t>s`; three times ` Test Files  94 passed (94)` and `      Tests  775 passed (775)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s` and the route lines `├ ○ /settings`, `├ ○ /settings/church` and `├ ○ /settings/contacts` and no `Error` (a font `Failed to fetch` only: say so and rely on CI).

- [ ] **Step 3 (agent): The API files match, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/email_addresses.py backend/usecases/contacts.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff origin/main...HEAD -- backend frontend/src | grep '^+' | grep -c '—'
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations backend/db .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); `imports grep exit 1`; `raw html grep exit 1`; `0` (no em dash in an added line of code or tests); exactly these 29 paths (the 6a-1 record in the runbook and the 5b spec's amendment ride along until merged):
```
M	backend/api/main.py
A	backend/api/routes/contacts.py
A	backend/email_addresses.py
M	backend/email_contacts.py
A	backend/tests/fixtures/shared/email_addresses.json
A	backend/tests/test_api_contacts.py
A	backend/tests/test_contacts_postgres.py
A	backend/tests/test_email_addresses.py
M	backend/tests/test_email_contacts.py
M	backend/tests/test_no_streamlit_in_core.py
M	backend/tests/test_slice1_docs.py
A	backend/tests/test_usecase_contacts.py
A	backend/usecases/contacts.py
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-06-slice-5b1-contacts.md
M	docs/superpowers/specs/2026-09-25-slice-5b-gmail-email-design.md
A	frontend/src/app/(signed-in)/(church)/settings/contacts/page.tsx
A	frontend/src/components/settings/contacts-settings-page.test.tsx
A	frontend/src/components/settings/contacts-settings-page.tsx
M	frontend/src/components/settings/sections.ts
M	frontend/src/components/settings/settings-layout.test.tsx
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/types.ts
A	frontend/src/lib/queries/contacts.ts
A	frontend/src/lib/settings/contacts.test.ts
A	frontend/src/lib/settings/contacts.ts
M	frontend/src/test/fixtures/index.ts
```
`0`; the subjects oldest first: `Runbook: slice 6a-1 record (merged; owner's phone check)`, `Spec: slice 5b planning answers (owner, 2026-10-06)`, the plan commits (`WIP plan: …` and `Plan: slice 5b-1 (the Contacts page)`) and any later plan commit, then T1-T9's nine subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> The Contacts page (slice 5b-1) is verified on this machine: backend 1598 passed, 26 skipped (1529 and 24 before); frontend 775 tests in 94 files (759 before), three runs in a row; typecheck, lint and the production build are clean. It adds the `/contacts` routes, no database change and no new package. Settings gets a third section, **Contacts**: everyone in the church sees the saved contacts, and you (and any admin) add, edit and delete them. Every address is checked by the same rule the email feature will use, a second copy of an address is refused, and a contact saved in the old app whose address would not work shows "This address doesn't look valid. Edit it.", so you can fix it there. Nothing is emailed yet (that is 5b-2). The pull request also carries the 6a-1 record and today's 5b planning notes. May I open the pull request as a **draft** titled "Slice 5b-1: the Contacts page", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/5b1-pr-body.md" <<'BODY'
Slice 5b-1: the Contacts page (the first of 5b's two PRs; owner's 5b planning answers of 2026-10-06). Specs: docs/superpowers/specs/2026-09-25-slice-5b-gmail-email-design.md (its amendment of 2026-10-06) and docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md ("Contacts"). Plan: docs/superpowers/plans/2026-10-06-slice-5b1-contacts.md. No database change, no new package or variable, no Google setup.

- email_addresses.normalize_address: the one address rule (5b spec), pinned by the shared fixture backend/tests/fixtures/shared/email_addresses.json, which runs through POST /contacts too (5b-2's send will use the same rule).
- GET /contacts (every member; ContactOut plus email_valid), POST, PATCH and DELETE /contacts (owners and admins), each write in one transaction that locks the church row and re-reads the caller's role, so the case-insensitive duplicate check holds under concurrent adds (Postgres tests).
- email_contacts: a session on every function, the 5b spec's order (blank names last), blank names as null, edit and duplicate lookups; get_contacts_for_display and the frozen Streamlit callers unchanged.
- Settings → Contacts: the list for everyone, flags on saved addresses the rule refuses, add, edit (dialog) and delete (confirmed) for admins, inline errors, the leave guard on the add form. The Settings nav: Church, Bulletin, Contacts.
- docs/manual-verification.md: "## Slice 5b".
- Rides along: the 6a-1 record in docs/ops-runbook.md and the 5b spec's amendment of 2026-10-06.

Later: 5b-2 (the Gmail connection, Settings → Account, emailing the bulletin), 6a-2 (Hymns), 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings moved in), 6b (People).

Tests: backend 1529 → 1598 passed, 24 → 26 skipped; frontend 759 → 775 in 92 → 94 files

After merge (Task 11): a short check on the owner's phone (which also finds any saved contact the new rule refuses), then a "Slice 5b-1 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 5b-1: the Contacts page" \
  --body-file "<scratch>/5b1-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1598 passed, 26 skipped`, backend-postgres `26 passed, 1598 deselected`, frontend `775 passed` in 94 files. Then send: "PR #<N> is green: backend 1598 passed, 26 skipped (the two new Postgres tests passed in their own job); 775 frontend tests in 94 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_email_addresses.py`, `test_no_streamlit_in_core.py` (`email_addresses`) | T1 |
| `test_email_contacts.py`, `streamlit_tests/test_settings_profile_contacts.py` | T2 |
| `test_usecase_contacts.py`, `test_no_streamlit_in_core.py` (`usecases.contacts`) | T3 |
| `test_api_contacts.py`, `test_openapi_contract.py`, `test_route_guards.py` | T4 |
| `test_contacts_postgres.py` (CI `backend-postgres`) | T5 (the lock itself: T3) |
| `contacts.test.ts`, `typecheck` in `lib/queries/contacts.ts` | T6 |
| `contacts-settings-page.test.tsx` | T7 |
| `settings-layout.test.tsx`, `church-settings-page.test.tsx` (its nav links) | T8 |
| `test_slice1_docs.py`, `test_docs.py` | T9 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, slice 5b-1 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1598 passed, 26 skipped`; frontend `775 passed` in 94 files.

### Task 11: Merge, the owner's phone check (three steps), the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate (production stays at `0007_bulletin_images`); Railway serves `/contacts`, Vercel the page. The owner's check is **one step at a time** (send one, wait for the report or "next"), on the phone, on the production URL, in the owner's own church, signed in as its owner. Any test contact the check adds is deleted in the same step. The agent writes each result into `<scratch>/5b1-t11-results.md` (not committed). Record counts and what the page showed, never an email address, a contact's or person's name, a token or a church id.

**Files:** Modify (the records PR, Step 7): `docs/ops-runbook.md`: insert `### Slice 5b-1 record` right before `## Backups` (after the last record above it, today `### Slice 6a-1 record`, whose table's last row starts `| Follow-ups |`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (slice 5b-1: the Contacts page) is ready, green and up to date with main. There is no database change; your saved contacts stay exactly as they are until someone edits them. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about three minutes for Railway and Vercel before Step 2; a failed deploy keeps the old version running (Step R).

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 3: your saved contacts (manual-verification item 1; answer 6's check)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. Tap **Settings** at the top: are the sections **Church**, **Bulletin** and **Contacts**? Tap **Contacts**: do you see your church's saved contacts, each name in bold with its email address under it? Please tell me three numbers, without any names or addresses: how many contacts are listed, how many show "This address doesn't look valid. Edit it." under them, and whether any address appears twice.

This step is the one-time check of existing contacts (owner answer 6): the page runs every saved address through the same rule the email feature will use. Record the three numbers only.

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 3: fix, or try it out (item 2)**

If Step 2 found flagged contacts or an address listed twice:

> For each contact with "This address doesn't look valid. Edit it.": tap its pencil button, correct the email address (one address only, like name@example.org), and tap **Save changes**. Does the note go away? If an address is listed twice, tap the bin button on one of them and then **Delete contact**. Is the list now as you want it?

Otherwise:

> Under the list, in **Add a contact**, type the name **Test** and the email **test@example.com**, and tap **Add contact**: does "Test" appear at the end of the list, with the boxes emptied? Tap its pencil button, change the name to **Test 2** and tap **Save changes**: does the list show "Test 2"? Now add **TEST@example.com** again: does it say "That email is already in your contacts." under Email? Clear the Email box, then tap the bin button next to "Test 2" and **Delete contact**: is it gone?

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 3: unsaved changes and the phone screen (item 3)**

> In **Add a contact**, type any name but do not add it, then tap **Church** in the Settings sections: does "Discard unsaved changes?" ask first? Tap **Discard changes**: does the Church page open? Back on **Contacts**: is the page easy to use on the phone, with no sideways scrolling, and are the section links, the pencil and bin buttons and **Add contact** easy to tap?

- [ ] **Step 5 (agent): The agent's own checks (items 4-6)**

On the production URL, in a test church the agent may change (one of the two slice 1 test churches the owner kept, never the owner's own church), signed in as its owner if the session has a test account, else skipped and recorded as "not run": item 5 (a contact deleted in one tab and edited in another), item 6 (`Someone@Example.ORG` saved as `Someone@example.org`, then deleted). Item 4 needs a plain member's sign-in; record "not run" unless the owner offers one.

- [ ] **Step 6 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/5b1-t11-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 7 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it, `### Slice 6a-1 record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Slice 5b-1 record

Slice 5b-1 (the Contacts page: Contacts in the Settings sections after
Church and Bulletin; every member reads the church's contacts, owners and
admins add, edit and delete them; `GET`, `POST`, `PATCH` and `DELETE
/contacts`, each write under the church-row lock with the caller's role
re-read; `email_addresses.normalize_address`, the one address rule, which
5b-2's send will use) merged as PR #<N>, the first of slice 5b's two PRs
(owner's 5b planning answers of 2026-10-06). No database change and no new
package; production stays at `0007_bulletin_images`. The owner's check was
three steps on a phone, covering the "(owner, after 5b-1)" items of
`docs/manual-verification.md` → "Slice 5b"; its first step is the one-time
check of the contacts saved before the rule (answer 6). Any test contact
was deleted. No address, name, token or church id is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success | <date> |
| 1. Saved contacts (phone: <phone and browser>) | <Church, Bulletin and Contacts listed; <n> contacts, <n> flagged, <n> addresses listed twice. / …> | <date> |
| 2. Fix or try it out | <Each flagged contact fixed (the note went away); <n> duplicates deleted. / A test contact added, renamed, its address refused a second time, deleted. / …> | <date> |
| 3. Unsaved changes and the phone | <"Discard unsaved changes?" asked; Discard changes opened Church; no sideways scroll, easy to tap. / …> | <date> |
| Agent checks | <Items 5 and 6 in a test church: <results>. / Not run: <why>.> Item 4 (a member): <result / not run> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: 5b-2 (the Gmail connection and emailing the bulletin; the owner adds the redirect URI in Google Cloud Console), 6a-2 and 6a-3, in the order the owner picks | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye. Then (not replayed):

```bash
sed -n '/^### Slice 5b-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 5b-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
sed -n '/^### Slice 5b-1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '—'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 5b-1 record (merged; owner's phone check)" -m "Records slice 5b-1 (PR #<N>): the merge and CI on main and the owner's
three-step phone check (the saved contacts counted and any flagged one
fixed, adding, editing and deleting, the leave guard and the phone
screen). No address, name, token or church id is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 8 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 5b-1 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 5b-1 record" \
  --body "Records slice 5b-1 (PR #<N>) in docs/ops-runbook.md → Slice 5b-1 record: the merge and the owner's three-step phone check. No address, name, token or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Slice 5b-1 is live and recorded; <n> follow-ups. Next: 5b-2's build, or 6a-2 and 6a-3, in the order you pick."

- [ ] **Step R (only if the release must come out): Revert**

Code only (no schema to undo). On the owner's yes for each outward command: a branch `claude/revert-5b1` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert slice 5b-1 (PR #<N>)" with the trailer, both suites (`1529 passed, 24 skipped`; `759 passed` in 92), a PR, CI, and the merge on the owner's yes; record it in the record. Contacts added or edited through the page stay in the `contacts` table (a name, an address, as the old app stored them), so nothing needs undoing in the data.

Expected counts after this task: backend `1598 passed, 26 skipped` on `main`; frontend `775 passed` in 94 files. The records PR adds no test.

---

## Build notes

**How this plan was written (2026-10-06).** Each task's code was built and run in a throwaway worktree of `62c9cc5` (the branch head `c97d341` plus the plan's skeleton commit; the repo's `.venv`; a hard-linked copy of `frontend/node_modules`, since Turbopack's production build refuses a `node_modules` symlink that points outside the project), one commit per task; the directives were then generated from those commits (a new file as **Create**, an addition at the end of a file as **Append**, every other change as **In … replace** with just enough context to occur once in the file as it stands at that point, changes three or fewer lines apart in one block). No package, variable or migration was added. While building:
- **What the specs assumed and what exists.** B's `email_addresses.py`, `GET /contacts` and `ContactOut` were never built (5b was set aside for 6a-1), and S assumed them; 6a-1 built the lock helpers and the Settings shell S and B describe, so this plan reuses them unchanged. `keys.contacts` was already in `keys.ts`. The `contacts` table has no unique constraint and the old repo no session parameter.
- **The Streamlit callers.** `streamlit_tests/test_settings_profile_contacts.py` still runs (pytest collects `streamlit_tests`) and reaches `email_contacts.add_contact` and `list_contacts` through the frozen `streamlit_views/settings.py`; with the new keyword-only `session` and the same positional arguments, its 35-test folder passes unchanged (T2 Step 4).
- **A fixed `GET /contacts` answer in the page tests** put a deleted row back (and dropped an added one) when the mutation's refetch landed; the tests use `contactsServer`, a fake whose `GET` answers with what the writes left, as the server does.
- **The 409 has no `fields`** (the error handler adds them only to a 422), so the page puts a 409 under Email itself.
- **Mutation checks** (each change made by hand in the build worktree, the named tests run, the change undone): the role check dropped from `update_contact` → `1 failed, 38 passed` (usecase, API and repo tests); `email_valid` always true → `2 failed, 37 passed`; the old `created_at, name` order → `2 failed, 37 passed`; the edit's duplicate check not leaving the contact itself out → `3 failed, 36 passed`; the address stored as typed instead of normalized → `4 failed, 35 passed`; the add form's `LeaveGuard` removed → `1 failed, 34 passed` (the settings and rules tests); the row buttons shown to members → `1 failed, 34 passed`; `contactPatch` always sending the email → `2 failed, 33 passed`.
- **The lock on Postgres.** On a throwaway PG 16 cluster (initialised under `/var/lib/postgresql`, port 5437, never a real database): `test_contacts_postgres.py` `2 passed`; all Postgres-marked tests `26 passed, 1598 deselected, 1 warning`. With `lock_church`'s `with_for_update=True` removed, both fail: "the second add did not wait for the church-row lock" and `round 0: assert [201, 201] == [201, 409]`.
- **The production build** compiled with `○ /settings`, `○ /settings/church` and `○ /settings/contacts`.

**Replay of the finished plan (2026-10-06).** The directives of T1-T9 were applied in order (by `replay.py`, which parses each step's **Create**, **Append** and **In … replace** blocks and runs every command on its "Run:" lines, three times where it says so, then the task's commit block) onto a fresh detached worktree of `62c9cc5`, with the repo's `.venv` (a symlink) and a hard-linked copy of `frontend/node_modules`:
- All 30 directives applied (T1 3 + 1, T2 2 + 1, T3 2 + 1, T4 1 + 3, T5 1, T6 3 + 3, T7 1 + 2, T8 2 + 2, T9 2); every Replace anchor occurred exactly once. After T9, `backend`, `frontend/src` and `docs/manual-verification.md` equaled the build worktree's (`diff -r`).
- Baselines before T1: backend `1529 passed, 24 skipped`; frontend `759 passed` in 92 files.
- Every "see it fail" output is quoted from this replay (times as `<t>`): T1 and T3 the collection error and the import check's `1 failed, 2 passed`; T2 the collection error; T4 `13 failed`; T6 and T7 the new file not loading; T8 three `×`.
- Every count matched the table: backend 1562, 1567, 1585, 1598 passed with 24 skipped, then 26 skipped from T5; frontend 763 in 93, 774 in 94, 775 in 94; T7's three runs `25 passed` each time, no flaky run; T4 Step 4 ` 2 files changed, 921 insertions(+)` and `42 passed`; T8 Step 4 `32 passed`; typecheck 0 and lint 0 after T4, T6, T7 and T8; T9 `89 passed`, `4`, `0`, ` 2 files changed, 22 insertions(+), 3 deletions(-)`.
- Not run while planning: the pushes, the PR and CI, the merge, Railway's and Vercel's deploys and the owner's phone check (T11).

## Spec coverage

| Owner answer or spec item | Task(s) and tests |
|---|---|
| Answer 2: 5b-1 is the Contacts page, `GET /contacts` and `normalize_address`, no Google setup | T1, T4, T7, T8; clarification 1 |
| Answer 6: a one-time check of saved contacts the rule would refuse | T3 `test_the_list_flags_each_saved_address_the_send_time_rule_refuses`; T4 `test_a_member_reads_the_list_in_order_with_blank_names_null_and_bad_addresses_flagged`; T7 "flags a saved address the send-time check refuses, and the admin fixes it", the member's note in "shows a member the list as text…"; T11 Step 2; clarification 13 |
| B `normalize_address` (the rule, no dependency) and the shared fixture | T1 `test_email_addresses.py` (33 cases); T4 `test_every_shared_address_case_is_accepted_or_refused_as_normalize_address_says` (B acceptance 14a) |
| B `GET /contacts`: `ContactOut`, the order, blank names as null, `assert_church_isolated` | T2 `test_contacts_are_listed_by_creation_then_name_with_blank_names_last`; T4 the list test and `test_contacts_are_isolated_between_churches` |
| S UX §4: the list, the member banner, nameless rows, the empty states | T7 "shows a member the list as text…", "shows each role its empty state" |
| S UX §4: add (fields clear, focus to Name, no toast), edit (dialog, PATCH), delete (confirmed) | T7 "lets an admin add a contact…", "lets an admin edit a contact…", "asks before deleting, then removes the row"; T6 `contacts.test.ts` |
| S errors inline: "Email is required.", "Enter a valid email address.", "That email is already in your contacts." | T7 "says what is wrong with an address under Email and focuses it", "shows an edit's 409 in the dialog…"; T4 `test_a_bad_field_is_a_422_naming_it`, `test_an_address_already_saved_in_any_case_is_a_409` |
| S API rows and models (`POST` 201, `PATCH` only what is sent, `DELETE` `{deleted: true}`, 404 "Contact not found.", `extra="forbid"`, an omitted email is "Email is required.") | T4 `test_an_admin_adds_edits_and_deletes_a_contact`, `test_a_bad_field_is_a_422_naming_it`, `test_unknown_fields_and_malformed_ids_are_422`; T3 `test_an_unknown_contact_or_another_churchs_is_not_found` |
| S roles: everyone reads, admins write | T4 `test_a_member_cannot_add_edit_or_delete`; T3 `test_a_member_a_demoted_admin_or_a_removed_member_writes_nothing`; T7 the member's view |
| S Semantics → Contacts: `normalize_email`, the stored address, `lower()` duplicates excluding self, a blank name stored as `""` and returned as null | T3 `test_an_address_is_stored_as_the_send_time_rule_returns_it`, `test_a_missing_or_invalid_address_is_named`, `test_a_name_is_trimmed_blank_is_stored_as_empty_and_it_stays_on_one_line`, `test_an_admin_adds_a_contact_and_a_duplicate_in_any_case_is_refused`, `test_an_edit_changes_only_what_is_sent_and_checks_duplicates_but_not_itself` |
| S Semantics → Locking (the lock, the role re-read, `no_church_access`) | T3 `test_each_write_reads_the_church_row_under_its_lock`, `test_a_member_a_demoted_admin_or_a_removed_member_writes_nothing` |
| S Postgres: two concurrent adds of one address in two cases → one 201, one 409, one row, 20 rounds | T5 `test_two_adds_of_one_address_at_once_make_one_contact_twenty_times` and `test_a_second_add_waits_for_the_first_and_gets_a_409` (CI `backend-postgres`) |
| S: a role 403 does not take the church fallback; `["church", id, "contacts"]` invalidated by the writes | T7 "toasts a role 403 and refetches the church profile…"; T6 `lib/queries/contacts.ts` |
| S "Settings nav": Contacts in `SETTINGS_SECTIONS` | T8 `settings-layout.test.tsx` |
| Leave guard on a settings form with unsaved input | T7 "asks before leaving with something typed in the add form" |
| B/S: `get_contacts_for_display` left for slice 7; the Streamlit callers keep working | T2 (unchanged function; `test_email_contacts.py`'s three tests and `streamlit_tests` pass) |
| Layering; OpenAPI and types regenerated | T1, T3 `test_no_streamlit_in_core.py`; T4 Step 4; T10 Step 3; `test_openapi_contract.py`, `test_route_guards.py` |
| A guided phone check after the PR | T11 Steps 2-4; `docs/manual-verification.md` "## Slice 5b" (T9) |

Spec items **not** in 5b-1: everything Gmail and email (5b-2: `/settings/account`, `/gmail/callback`, the `/gmail-connection` routes, `POST /bulletin-emails`, `dedupe_addresses`, `MALFORMED_CONTACT_HINT` with "An admin can fix it in Settings → Contacts.", the email dialog and its admin-only "Manage contacts" link, the `useContacts` prefetch on the Review page); B's `check_contact_addresses.py` (replaced by the page's flag, clarification 13); S's `ContactOut.name` validator (not needed, clarification 17).

## Follow-ups (not in 5b-1)

- 5b-2: set the Contacts caption back to S's "People you can email the bulletin to from the Review step." once the Review step can send; add `dedupe_addresses` beside `normalize_address`; run `email_addresses.json` through `POST /bulletin-emails`; use `email_valid` in the email dialog (a flagged contact can be shown but not chosen, or chosen with the hint); the "Manage contacts" link to `/settings/contacts` for admins.
- 5b-2 (it adds Account, a fourth section): on a phone the Settings nav is a wrapping row of 44 px links; three fit in one row at 375 px, four may wrap. Switch the phone row to a horizontal scroller then, as the 6a-1 follow-up says.
- If the owner wants a second guard against duplicates: a unique index on `(church_id, lower(email))` in its own migration, after any church's duplicate addresses are removed (owner question 3).
- Choosing another church in the church menu still does not ask before discarding unsaved settings edits (6a-1 follow-up, carried; it now covers the add form too).
- Slice 7: delete `email_contacts.get_contacts_for_display` and its assertion in `test_email_contacts.py` (B, S).

## Owner questions

Your 5b planning answers of 2026-10-06 (the six, all as recommended) are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **Where Contacts sits in Settings** (clarification 2). The sections become **Church**, **Bulletin**, **Contacts**: Contacts goes at the end. In the full plan for Settings, Contacts comes after every page about your services (Church, Hymns, Liturgy, Prayers, Rubric, and Bulletin settings, which moves in among them later) and before People and Account. Putting it last now means it is already where it will stay, and no section moves when Hymns, Liturgy, Prayers, Rubric and Account arrive. (The other choice: Church, Contacts, Bulletin, which would move Bulletin to the end now and back up later.) Recommended: accept.
2. **How to find saved contacts the new address check would refuse** (your answer 6; clarification 13). Recommended: **(b) the page shows it.** The Contacts page runs every saved address through the same rule the email feature will use, and puts "This address doesn't look valid. Edit it." under any that fails; the first step of your phone check after the merge is to open Contacts once, count them and fix them with **Edit**. Why: a database query cannot run the rule itself, so it could only guess; a small script (the 5b spec's plan) would need a terminal, access to Railway and your church's id, which you would not normally use; the page needs nothing from you but your phone, cannot change anything by itself, and keeps flagging any bad address later (the email feature will refuse such a contact with "An admin can fix it in Settings → Contacts."). (The other choice: **(a)** a script the agent runs on Railway with your permission, listing the ids of contacts that fail, with no flag on the page.)
3. **No database change for duplicates** (clarification 12). Recommended: keep the check the 6a spec designed, with no database change: when an address is added or changed, the app looks for the same address (in any capitals) in your church's contacts while it holds the lock every church change takes, so two admins adding the same person at the same moment still end up with one contact (tested on Postgres). The alternative is a database rule (a unique index) as a second guard; it needs a migration, and that migration would fail on deploy if your church already has an address saved twice (the old app never checked), so any duplicates would have to be found and deleted first. With the old app retired, nothing else writes contacts, so the check is enough.
4. **The Contacts page's caption until emailing exists** (clarification 3). "People you can email the bulletin to. Emailing it from the Review step comes in a later update." The spec's line, "People you can email the bulletin to from the Review step.", is not true until 5b-2 ships; 5b-2 puts the spec's line back. (The other choice: the spec's line now.) Recommended: accept.
5. **How an address is saved** (clarification 9). Spaces around it are removed and the part after the @ is saved in lower case (it never matters for delivery); the part before the @ is kept as typed. So "Mary@Example.ORG" is saved as "Mary@example.org". Contacts saved in the old app are left as they were until edited. Recommended: accept.
6. **Contact names stay on one line** (clarification 9). A name with a line break or an invisible control character (only an odd paste can make one) is refused with "Name can't contain line breaks or control characters.", the same rule as the church name. (The other choice: quietly turn such characters into a space.) Recommended: accept.
7. **No "saved" messages on this page** (clarification 4). Adding, editing or deleting a contact shows its result in the list (the new row, the changed row, the row gone) with no pop-up message, as the 6a spec says for contacts. Recommended: accept.
8. **The unsaved-changes warning** (clarification 6). While something is typed in **Add a contact**, leaving the page asks "Discard unsaved changes?" first, as on the Church page. The **Edit contact** box has no such question: **Cancel** (or tapping outside it) simply closes it and drops the change, which is at most a name and an address. Recommended: accept.
9. **The page's wording** (clarifications 3, 4 and 15): "Contacts"; "Only admins can add or change contacts."; "This address doesn't look valid. Edit it." (admins) and "This address doesn't look valid. An admin can fix it." (members); "No contacts yet" with "Add the people who receive the bulletin, like your church secretary." or "Ask an admin to add bulletin recipients."; "Add a contact", "Name (optional)", "Email", **Add contact**; "Edit contact", **Save changes**; "Delete {name}?", "They won't be offered as a bulletin recipient anymore.", **Delete contact**; and the server's "Email is required.", "Enter a valid email address.", "That email is already in your contacts.", "Contact not found.". Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T10); the merge on your yes, then three phone checks one at a time (the first one is your check of the saved contacts), and the records PR (T11).

## Self-review

- **Coverage.** Every binding constraint has a home: the nav order and its reason (clarification 2, owner question 1); no migration, with the unique-index trade-off (clarification 12, owner question 3); no em dash in new copy (clarification 15; T9 Step 2 and T10 Step 3 grep the added lines; S's caption is not used as written, and the 5b spec's dialog lines with their dashes belong to 5b-2); no ids, real addresses, keys or phone numbers in the docs (only `@example.org` / `@example.com` addresses; the record's own grep, T11 Step 7); the frozen Streamlit files untouched and `get_contacts_for_display` kept (T2; T10 Step 3's path check counts `app.py`, `streamlit_views` and `streamlit_tests` as 0); the read-only check of existing contacts as option (b), with (a) offered (clarification 13, owner question 2); 6a-1's patterns reused as they are (`lock_and_read_actor`, `require_admin_role`, `LeaveGuard`, `ConfirmDialog`, the generated types, the Settings shell); the second-to-last task opens a draft PR only on the owner's yes, the last merges only on a yes, runs a three-step phone check one step at a time and inserts "### Slice 5b-1 record" before "## Backups", after "### Slice 6a-1 record".
- **Placeholders.** None in T1-T9's code, tests, commands or expected outputs; every expected output is quoted from the replay. The `<…>` left are T10 and T11's runtime values (`<N>`, `<scratch>`, times, the owner's answers), as in the 6a-1 plan.
- **Consistency.** Names agree across tasks: `normalize_address`/`InvalidAddress` (T1) are used by `usecases.contacts` (T3); `get_contact`, `update_contact`, `email_exists` (T2) by T3; `list_contacts`, `add_contact`, `update_contact`, `delete_contact` (T3) by the routes (T4); `ContactOut.email_valid` (T4) by `Contact` (T6) and the page (T7); `keys.contacts` (existing) by the queries (T6). The counts in the table, each task's "Expected" and the PR line (`1529 → 1598`, `24 → 26`, `759 → 775`, `92 → 94`) agree.
- **Not verified while planning:** the pushes, the PR and CI, the merge, Railway's and Vercel's deploys, the owner's phone check, and the page at 375 px in a real browser (the classes give 44 px targets and `break-all` addresses; jsdom does not lay out). What the owner's contacts look like is unknown until T11 Step 2.
- **Judgement calls to watch in review:** the usecases in their own module rather than `church_admin.py`; `email_valid` added to B's `ContactOut`; the held-lock Postgres test beside S's barrier test; the name's one-line rule.
