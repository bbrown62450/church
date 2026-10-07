# Slice 5b-2: the Gmail Connection and Emailing the Bulletin

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the second half of slice 5b (owner's 5b planning answers of 2026-10-06, answer 2): **each member connects their own Gmail and emails the bulletin from the Review step.** Settings gains a fourth section, **Account** (after Church, Bulletin and Contacts): who is signed in, **Log out**, and a **Gmail** card to connect (Google's consent screen in the same tab, back through the new page `/gmail/callback`), see "Connected as …" and disconnect. Review & send gains an **Email the bulletin** card after the printed bulletin: "Sends from {address}." and **Email bulletin…**, which opens a dialog with the church's contacts (a contact whose saved address the send-time rule refuses is shown but cannot be chosen), other addresses, the subject "Worship service for October 4, 2026", two attachment boxes, **Bulletin copy (Word)** (ticked at first) and **Printed bulletin (PDF)** (at least one; the choice is remembered on the device), and an editable prefilled message. One recipient goes in To; two or more go in Bcc with the sender in To; at most 50. The server builds both files from the posted draft, as the downloads do, and sends through the Gmail API. A double tap or a retry never sends twice; when Gmail may have sent without confirming (or the connection was lost), the dialog says to check the Sent folder, turns plain **Send** off (still off after leaving Review or a reload in that tab) and offers only **Send again anyway**. The Contacts page's caption becomes "People you can email the bulletin to from the Review step." The owner sets up Google and Railway before the merge (the last task). No migration, no new package.

**Architecture:** Backend first. `integrations/http.py` gains `post()` (no redirects). `google_oauth.py` is rewritten for the API: `GoogleOAuthConfig` (from Railway's `GOOGLE_*` through `api/settings.py`), the consent URL with a login hint, the single-use states (expired ones purged), the token store (`get_connection`, `save_user_token`, `delete_connection(only_if_token=…)`) and the Google calls (`exchange_code`, which stores nothing, `refresh_access_token`, `send_raw_message`, `revoke_token`), each failure one `GoogleErrorKind`; the Streamlit-only functions go. `usecases/email.py` holds the connection (status, start, finish, disconnect) and `send_bulletin_email`; `api/routes/gmail.py` the four user-scoped `/gmail-connection` routes; `api/routes/bulletin_emails.py` `POST /bulletin-emails`, idempotent with a required key and the new `store_error` hook that keeps an uncertain send's answer. `bulletin_email.py` (pure) writes the subject, the default message, the To/Bcc plan and the MIME message; `email_addresses.dedupe_addresses` joins `normalize_address`; `email_contacts.get_contacts_by_ids` reads the chosen contacts. Frontend: `lib/gmail.ts` and `lib/queries/gmail.ts` (the trip to Google), the callback page, Settings → Account, `lib/email.ts` (the dialog's pure rules and remembered choices), `lib/queries/email.ts`, and `components/builder/review/email-card.tsx` with `email-dialog.tsx`. The Supabase browser client stops reading sign-ins from the address bar.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy, httpx, pytest; Next 16, React 19, TypeScript 5, Base UI (Dialog), TanStack Query 5, sonner, lucide-react, Vitest 3 with Testing Library.

**Source documents:**
- 5b spec ("B"): `docs/superpowers/specs/2026-09-25-slice-5b-gmail-email-design.md`, read with its **"Amendment 2026-10-06: owner's 5b planning answers"** (binding; it wins where the older text differs): the two attachments (answer 1), two PRs (answer 2: this is 5b-2), Streamlit's Google client reused (answer 3), Streamlit treated as unused (answer 4), the wording (answer 5). The rest of B (API, errors, idempotency and uncertain sends, flows A-D, the callback page, timeouts, rate limit, testing, acceptance) applies unless it conflicts with the amendment or with the code as it is now (clarifications).
- 6a spec ("S"): `docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md` (the Settings shell and its final order: Church, Hymns, Liturgy, Prayers, Rubric, Contacts, People, Account, Danger zone).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.2 (guards), §1.5 (errors), §1.6 (idempotency), §1.8 (timeouts, rate limits), §2.2 (layers), §2.5 (logs), §4.3 (storage and URLs), §4.4 (queries), §4.8 and §4.9 (forms, 44 px).
- The model plan `docs/superpowers/plans/2026-10-06-slice-5b1-contacts.md` (format, directives, replay; its `normalize_address`, contacts usecases, Contacts page and Settings shell are reused here unchanged).
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `eb5b2da` = `origin/main` plus the 5b-1 record, then this plan's commits; 2026-10-06): backend `1669 passed, 26 skipped`; frontend `780 passed` in 94 files; typecheck and lint clean; Alembic head `0007_bulletin_images` (7 revision files); 4 runbook owner markers. What exists: `gmail_tokens` (`user_id` primary key, `refresh_token` not null, `google_email` nullable) and `oauth_states` (`state`, `user_id`, `created_at`, `expires_at`), both since `0001_baseline`; the Streamlit-era `backend/google_oauth.py` (`requests`, `os.getenv`, `should_handle_gmail_callback`, `send_email` with every recipient in To, `exchange_code` that stores the token itself) imported only by the frozen `app.py` and three test files (`test_oauth_state.py`, `test_gmail_exchange.py`, `test_gmail_token_store.py`, 21 tests); `integrations/http.py` with `get()` only; `api/idempotency.py` with `idempotency_key(required=True)` and `run_idempotent` but **no** `store_error`; `api/ratelimit.py` with the `email` bucket (10 an hour per user) already; `domain_errors.ERROR_CODES` with `gmail_state_invalid`, `gmail_connect_failed`, `gmail_not_connected`, `gmail_send_failed`, `gmail_not_configured` already (and the frontend's `ServerErrorCode` with them); `email_addresses.normalize_address` and the shared `email_addresses.json` (5b-1); `usecases.documents.build_document` and `build_printed` (`POST /documents`, `POST /documents/printed`); `printed_bulletin.printed_date` ("October 4, 2026"); `keys.gmailConnection()` = `["gmail-connection"]` and `keys.contacts(id)` in `lib/queries/keys.ts`; `createKeyTracker` and `settleOutcome` in `lib/idempotency.ts` (a 5xx or a lost connection keeps the key); `SETTINGS_SECTIONS` = Church, Bulletin, Contacts; the header's **Settings** link (6a-1). **No** `/settings/account`, `/gmail/callback`, Gmail route, email card, `email-slot.tsx` placeholder or `useSendBulletinEmail`; the Supabase browser client reads sign-ins from the URL (the default).
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -3`; the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes in T6 and T14, so each regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand.
- No new package (respx, httpx and pytest are already installed; the fake Google is an `httpx.MockTransport`), no migration. The `GOOGLE_*` variables are not new: `backend/.env.example` and the runbook's Railway table already list them ("carried over for a later slice"); this slice starts reading them.
- Branch `claude/slice-2-plan-4q33le`, at `eb5b2da` plus this plan's commits (`WIP plan: slice 5b-2 …` and `Plan: slice 5b-2 (…)`, and any later plan commit), then T1-T17. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1669 → 1825 passed, 27 skipped; frontend 780 → 835 in 94 → 100 files` (two PRs: the lines of T18's table).
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 21 and has no em dashes (B's lines are taken without theirs); existing copy keeps its own punctuation.
- No church id, real email address, token, key, street address, phone number, database URL or real person's name in any doc, commit, test or record. Tests use the fixtures' "Grace", "Pat Pastor" and `@example.org` / `@example.com` addresses only. **The agent never asks for, reads, prints or handles the Google client secret or id** (T19's owner steps copy them inside Google Cloud Console and Railway only).
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.

### One PR or two (owner question 1)
The tasks are grouped so either answer works. **Group A, the Gmail connection (T1-T10):** `post()`, `google_oauth`, the config and startup lines, the connection usecases and routes, the callback page, Settings → Account, and their manual checks. **Group B, emailing the bulletin (T11-T17):** the message, `store_error` and the contacts lookup, `send_bulletin_email`, `POST /bulletin-emails`, the dialog's rules, the card and dialog (with the Contacts caption), and their manual checks. Group B depends on group A; group A stands alone (after it, Settings → Account connects Gmail and Review has no email card yet).
- **One PR (5b-2):** T1-T17, then T18 (verification, draft PR) and T19 (the owner's setup before the merge, the merge, the phone check, the record).
- **Two PRs (recommended):** T1-T10, then T18 and T19 for "Slice 5b-2a: the Gmail connection" (T19's setup steps happen before this merge; its phone check runs the steps marked A); then T11-T17 on the same branch after the merge commit is pulled, then T18 and T19 again for "Slice 5b-2b: emailing the bulletin" (no setup; the steps marked B). The record (`### Slice 5b-2 record`) is written once, after the last merge, with a row per merge. T18 and T19 say which commands and counts belong to which PR.

### How the file directives below read
As in the 5b-1 plan: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. New here: **Replace the whole of `path` with:** the block is the whole new file (an existing file rewritten, T2's `google_oauth.py`), and **Delete `path`:** `git rm -q '<path>'` (T2's three old Gmail test files, whose tests are ported). Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything.

### Baselines and counts
- Starting baselines: backend **1669 passed, 26 skipped**; frontend **780 passed in 94 files**, typecheck and lint clean; Alembic head **`0007_bulletin_images`** (7 revision files; no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests less the removed ones (a parametrized test counts each case); a frontend delta the number of new `it(` (an `it.each` row counts once).

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +2 (`test_http_client.py`, 7 → 9) | 1671 passed, 26 skipped | 0 | 780 in 94 |
  | T2 | −8 (`test_google_oauth.py` 13 new; the three old files' 21 deleted) | 1663 passed, 26 skipped | 0 | 780 in 94 |
  | T3 | +37 (`test_google_oauth.py`, 13 → 50: 11 + 4 + 15 parametrized cases and 7 tests) | 1700 passed, 26 skipped | 0 | 780 in 94 |
  | T4 | +10 (`test_startup.py`: 7 + 2 parametrized cases and 1 test) | 1710 passed, 26 skipped | 0 | 780 in 94 |
  | T5 | +17 (`test_usecase_email.py`: 8 parametrized cases and 9 tests) | 1727 passed, 26 skipped | 0 | 780 in 94 |
  | T6 | +12 (`test_api_gmail.py`: 5 parametrized cases and 7 tests) | 1739 passed, 26 skipped | 0 | 780 in 94 |
  | T7 | 0 | 1739 passed, 26 skipped | +7 (`gmail.test.ts` 5, `client.test.ts` 1, `urls.test.ts` 1 `it.each` row) | 787 in 96 |
  | T8 | 0 | 1739 passed, 26 skipped | +6 (`gmail-callback.test.tsx`) | 793 in 97 |
  | T9 | 0 | 1739 passed, 26 skipped | +7 (`account-settings-page.test.tsx` 6; `settings-layout.test.tsx` one test became two `it.each` rows) | 800 in 98 |
  | T10 | 0 | 1739 passed, 26 skipped | 0 | 800 in 98 |
  | T11 | +13 (`test_bulletin_email.py` 12: 6 + 4 parametrized cases and 2 tests; `test_email_addresses.py` 1) | 1765 passed, 27 skipped | 0 | 801 in 98 |
  | T12 | +4 (`test_idempotency.py` 3, `test_email_contacts.py` 1) | 1769 passed, 27 skipped | 0 | 801 in 98 |
  | T13 | +30 (`test_usecase_email.py`, 20 → 50: 5 + 11 parametrized cases and 14 tests) | 1799 passed, 27 skipped | 0 | 801 in 98 |
  | T14 | +19 (`test_api_bulletin_emails.py`: 2 + 4 parametrized cases and 13 tests) | 1818 passed, 27 skipped | 0 | 801 in 98 |
  | T15 | 0 | 1818 passed, 27 skipped | +10 (`email.test.ts` 8, `idempotency.test.ts` 1, `prune.test.ts` 1) | 811 in 99 |
  | T16 | 0 | 1818 passed, 27 skipped | +18 (`email-card.test.tsx`) | 829 in 100 |
  | T17 | 0 | 1818 passed, 27 skipped | 0 | 829 in 100 |

  After T10 the 5b-2a build review fixes (see "Build notes") added backend +13 (+1 skipped: a Postgres test) and frontend +1, so the rows from T11 on are the planned deltas on top of them.

  After T17 the 5b-2b build review fixes (see "Build notes") added backend +7 and frontend +6: backend `1825 passed, 27 skipped`, frontend `835 passed` in 100 files.

  Two PRs: 5b-2a (after T10 and its build review fixes) is backend `1752 passed, 27 skipped` and frontend `801 passed` in 98 files; 5b-2b (after T17 and its build review fixes) is backend `1825 passed, 27 skipped` and frontend `835 passed` in 100 files.

- CI `backend-postgres`: `27 passed` (26 before; the 5b-2a build review's I1 added `test_gmail_state_postgres.py`, two consumes of one CSRF state on real Postgres). 5b-2b adds no Postgres test: the Gmail rows are per user and the send takes no lock.

### Layering and code rules (carried)
- `google_oauth.py`, `bulletin_email.py`, `usecases/email.py` and `integrations/http.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains the first three); routes are plain `def`s with no SQL and no try/except (F §2.2 rule 1), each one usecase call; the usecase reaches the database only through `google_oauth`'s store and the repos.
- No database connection is held during a Google call (F §1.8); T13 checks the pool.
- Logs carry ids, counts and outcomes, never a code, a state, a token, an address, a subject or a message (F §2.5); T5 and T13 check.
- Pages and components never call `apiFetch`: the queries use `useApi()` (F §4.5).
- Touch targets 44 px below `md`; text wraps at 375 px (an address breaks anywhere, `break-all`); no raw HTML (F §4.8); inputs `text-base md:text-sm` (the kit's `Input` and `Textarea` already are).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit is retired** for this work (owner answer 4, 2026-10-06): the `streamlit-frozen` branch and its app are untouched and nothing in this slice keeps them working; merges never reach them.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **The 5b planning answers of 2026-10-06** ("all recommended"; binding; B's amendment): (1) the two attachment boxes, at least one, remembered per user and church in the browser; (2) two PRs for 5b, of which this is the second (5b-1, the Contacts page, merged as recorded in the runbook); (3) Railway reuses Streamlit's Google OAuth client (same id and secret), and the owner adds the redirect URI and checks the consent screen's publishing status; (4) Streamlit is treated as unused: no `google_oauth_legacy.py`, no Streamlit smoke test, no switchover banner, no parity gate, no `LegacySettingsNote`, no "current app" wording, `MALFORMED_CONTACT_HINT` reads "An admin can fix it in Settings → Contacts.", revoking on disconnect is fine, tokens stay as stored (encryption is slice 7's); (5) the subject "Worship service for October 4, 2026" and no em dash in any of B's copy; BCC with the sender in To, the editable prefilled message, at most 50 people, the last send's contacts preselected, any member may send, all kept.
5. **5b-1's answers** (binding, carried): `normalize_address` is the one address rule; a saved contact whose address it refuses is flagged on the Contacts page, and 5b-2's send refuses it with the hint.

**Later, out of scope:** 6a-2 (Hymns), 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings moved in), 6b (People, Danger zone), slice 7 (token encryption, deleting `app.py`'s Gmail code and `email_contacts.get_contacts_for_display`, rotating the Google client secret).

## Spec clarifications

The owner's answers win over B, S and F; the code wins over all of them where they disagree. **[owner-visible]** items are put to the owner in "Owner questions" (each written as recommended).

1. **[owner-visible] What 5b-2 ships, in one PR or two** (answer 2; owner question 1). Everything B lists for 5b after 5b-1 took the Contacts page: the Gmail connection (Settings → Account, `/gmail/callback`, the four `/gmail-connection` routes) and emailing (the card, the dialog, `POST /bulletin-emails`). B's parity gate, Streamlit smoke test, switchover banner and `scripts/check_contact_addresses.py` are not built (answer 4; 5b-1 clarification 13). The plan is long (17 build tasks against 5b-1's 9), so it can ship as two PRs: group A (the connection) and group B (emailing) ("One PR or two" above).
2. **Streamlit's Gmail code goes** (answer 4; B "Modules" `google_oauth.py`, normal case). `google_oauth.py` loses `should_handle_gmail_callback`, `send_email`, `disconnect`, `is_configured`, `is_connected`, `_fetch_email`, `_access_token_for`, `_user_email`, `_client_id`/`_client_secret`/`_redirect_uri` (`os.getenv`), `_TIMEOUT`, `_google_error` and the `requests` import; `build_auth_url` and `exchange_code` take B's new signatures. Who used them: only the frozen `app.py` (never imported by a test; it runs only from `streamlit-frozen`, which is untouched) and the three old test files, which T2 deletes after porting every assertion about kept code into `test_google_oauth.py` (scopes, the states' single use and expiry, one row per user). On `main`, `app.py` would now fail if someone ran it; nothing does, and slice 7 deletes it. B's `is_connected` (listed as kept) is dropped too: its only caller was `app.py`; `get_connection(...) is not None` is the new test. No `google_oauth_legacy.py`. `test_no_streamlit_in_core.py` gains `google_oauth` (T2), `usecases.email` (T5) and `bulletin_email` (T11).
3. **The Google client's settings** (B "Configuration and startup checks"; answer 3). `api/settings.py` reads `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and `GOOGLE_OAUTH_REDIRECT_URI` (trimmed) into `Settings` and its `google_oauth` property; the secret is left out of both dataclasses' `repr`, so it can never reach a log or an error by printing a settings object. `api.deps.get_google_config()` gives the routes the config (tests override it). The lifespan logs one line: `Gmail: configured` or `Gmail: not configured` (INFO), or a WARNING for each problem: some but not all three set ("Gmail sending is disabled until … set."), a redirect URI whose path is not `/gmail/callback` (a copied Streamlit root), whose site is not in `CORS_ORIGINS`, or that is not https in production. B asked for warnings only; the INFO line is added so the owner's check (T19) has a line to look for, as `AI: configured` does. It never refuses to start and never logs a value. `backend/.env.example` describes the three and gives the local redirect.
4. **HTTP for Google** (B "Rules"; F §2.7). `integrations/http.py` has only `get()`; it gains `post()` with a required per-call timeout that never follows a redirect (a token exchange or an email send is answered where it was sent or not at all). B's functions take an injected `http` client; here, as for every other upstream since slice 2, the tests swap the module's client with `set_http_for_tests` (the autouse fixture restores it), so the functions take none. The fake Google (`backend/tests/fake_google.py`) is an `httpx.MockTransport` that answers the token, userinfo, send and revoke endpoints and records each request; no test reaches the network (conftest's guard). respx is installed but not needed; no new dev dependency.
5. **`google_oauth` after the refactor** (B's signatures, with these readings). `exchange_code(config, code, *, expected_email)` exchanges the code (15 s), checks the granted scopes (no `scope` or a blank one means as requested, RFC 6749 §5.1; a non-string is `INCOMPLETE_RESPONSE`; one without `gmail.send` is `SCOPE_MISSING`), reads the Google address (15 s; a 4xx or no address is `NO_EMAIL`, a 5xx `UPSTREAM`), compares it ignoring case and returns a `GmailGrant` with Google's spelling; it stores nothing and opens no session. `get_connection` is None for no row or a NULL or blank address. `delete_connection(user_id, *, only_if_token=None)` deletes only a row still holding that token and returns the removed token. `create_state` purges every expired state first (another user's live state stays). `send_raw_message(access_token, raw)` posts the base64url message to Gmail's JSON endpoint (30 s): a failure before the request was written (`ConnectError`, `ConnectTimeout`, `PoolTimeout`) is `UPSTREAM`; a Gmail 5xx, or no answer after it was written, is `SEND_UNCONFIRMED` (with or without the status); a 403 naming the scope is `INSUFFICIENT_SCOPE`; a 429 or a 403 rate or daily limit is `SEND_LIMIT`; a 401 (one not about the scope) or a 400 `failedPrecondition` (an account Gmail will not send from, such as a Google account without Gmail or one whose Workspace admin turned Gmail off) is `ACCOUNT_REFUSED`; any other 4xx `SEND_REJECTED`. Each error keeps Google's reason name (for example `failedPrecondition`, never its text) for the caller's log. `revoke_token` (5 s) returns True or False and never raises (B: None), so the usecase can log a failed revoke. **Timeouts** are httpx's and apply per phase, not to the whole call: 5 s to connect, then 15 s (token, userinfo, refresh), 30 s (send) or 5 s (revoke) for each wait on a write, a read or the pool. A slow but steady answer can therefore take longer than the number; the browser's 75 s (40 s as first built; 5b-2a build review M3) and 90 s (clarifications 8 and 17) are the overall limits, and a send the browser stops waiting for is shown as possibly sent. Message size: the Word copy is tens of KB and the printed PDF about a megabyte at most (a cover picture is stored at 600 KB at most), so B's JSON endpoint is kept; `send_bulletin_email` refuses a message over 3.5 MB (`MAX_RAW_BYTES`; about 4.7 MB once base64url-encoded, under the 5 MB that Google's upload guide gives a simple request: https://developers.google.com/workspace/gmail/api/guides/uploads) before the email limit is charged (clarification 15). The media upload endpoint (`https://gmail.googleapis.com/upload/gmail/v1/users/me/messages/send?uploadType=media`, `Content-Type: message/rfc822`) would take more and is a follow-up if bulletins ever grow. Nothing in the module logs.
6. **The connection usecases** (B "usecases/email.py"; T5). `gmail_status`, `start_gmail_connect` (503 when not configured; a new state; the signed-in address as `login_hint`), `finish_gmail_connect` (B's order: not configured, then the state is used up in its own transaction and must be the caller's, then a blank code, then the exchange with no session open, then the store: a refresh token is saved; none, with a connection already stored, keeps it; none and no connection is the refresh-token message) and `disconnect_gmail` (delete, then revoke outside the transaction; a failed revoke is a WARNING and still a success). The messages are B's with no em dash; Google's error code (never its text) is logged at ERROR for our own misconfiguration (`invalid_client`, `unauthorized_client`, `redirect_uri_mismatch`).
7. **`/gmail-connection`** (B API, Schemas). `GET`, `POST /auth-url`, `POST`, `DELETE`, each `get_current_user` plus `get_google_config`, never `require_church` (`X-Church-Id` is ignored); all four join `USER_SCOPED` in `test_route_guards.py`. `POST /auth-url` stores a new state on every call, so it is rate-limited: a new per-user bucket `gmail_connect` (10 in 10 minutes; `api/ratelimit.py` and its pin in `test_ratelimit.py`), not the `email` bucket, so connecting never spends sends; the 11th is the usual 429 "Too many requests. Try again in {n} seconds." and stores no state. `GmailConnectionOut {configured, connected, google_email}`, `GmailAuthUrlOut {auth_url}`, `GmailConnectIn {code ≤ 2048, state ≤ 256}` (`extra="forbid"`). Every route documents 401, 422 and 503 (and `POST` 400, 502, 504; `POST /auth-url` 429): a route without 422 in its responses would put FastAPI's `HTTPValidationError` in the snapshot, which `test_openapi_contract.py` forbids.
8. **The browser's side of connecting** (B flows A-C, "Pure modules" `lib/gmail.ts`). `lib/gmail.ts`: `startGmailRedirect` (refuses any URL but `https://accounts.google.com/…`, stores `wsb:gmailReturnTo` and, from Review, `wsb:reopenEmailDialog` in sessionStorage, then leaves in the same tab through `browser.assign`, an object the tests replace since jsdom cannot navigate), `readReturnTo` (through `safeInternalPath`, else `/settings/account`), `parseCallbackParams`, `connectGmailOnce` (one POST per state) and `gmailErrorMessage`, which keeps the server's sentence for a Gmail or Google 502, 503 or 504 (`describeError` turns every 5xx into "Something went wrong.", which would hide "Couldn't reach Google…"). `lib/queries/gmail.ts`: `useGmailConnection`, `useStartGmailConnect` (a non-Google URL toasts "Something went wrong."), `useDisconnectGmail` (puts its answer in the cache, so no refetch and no toast). `POST /gmail-connection` gets a 75 s client timeout (40 s as first built, raised by 5b-2a build review M3: two slow but steady Google calls can take longer), the overall limit (Google's timeouts are per phase, clarification 5); a connect it stops waiting for shows an error and connecting again starts afresh. `src/lib/supabase/client.ts` passes `auth: { detectSessionInUrl: false }`, so the browser client never mistakes `/gmail/callback?code=…` or `?error=…` for a Supabase sign-in (sign-in itself is exchanged on the server in `/auth/callback`). `safeInternalPath` accepts exactly `/gmail/callback` as well as its five roots. Why: `proxy.ts` (unchanged) sends a signed-out request to `/login?next=<path>` and keeps only the path, dropping Google's `?code=…&state=…`, so after sign-in the page cannot finish the connect; returning to `/gmail/callback` shows "Gmail connection didn't finish. Try connecting again." with **Try again**, where without the entry the login would land on the Builder with no word about Gmail. Nothing is connected on that path either way.
9. **[owner-visible] `/gmail/callback`** (B flow C). In `(signed-in)`, outside the church shell. It reads Google's answer once (a ref, so StrictMode's second effect reuses it), removes it from the address bar and history, and shows "Connecting your Gmail…" (with "Still working. This can take up to a minute." after 8 s) while `POST /gmail-connection` runs, once per state; then the toast "Gmail connected", the status put in the cache and back to where the connect started. `?error=access_denied`: the toast "Gmail connection was cancelled." and back. Another `?error=`: "Google couldn't connect your Gmail." (the value is never shown). Nothing in the address bar (a lost query, a reload after success): "Gmail connection didn't finish. Try connecting again.". A failed POST: the server's message. Each failure has **Try again** (a new consent URL, the same way back) and **Go back**; Gmail not set up here has only **Go back**. It starts in the connecting view, so the "didn't finish" card never flashes during a connect (B's "reading" state is the same card).
10. **[owner-visible] Settings → Account** (B "/settings/account"; S's final order). `SETTINGS_SECTIONS` becomes Church, Bulletin, Contacts, **Account**: S puts Account after Contacts and People, so appending keeps it where it will stay when 6b adds People between them. `/settings` still opens Church. The page: "Account" (an `h2`), a box with the avatar (only an https picture; else the initial), the name, the email, "Signed in with Google." and **Log out** (the shared sign-out; the account menu keeps its own), and the **Gmail** box: two skeleton lines while loading; "Couldn't check your Gmail connection." with **Retry**; "Per-user Gmail sending isn't configured on this deployment." (no button); "Connect the Gmail account you sign in with. The app gets permission only to send email for you; it can't read your mail." with **Connect Gmail** ("Opening Google…") in 5b-2a, which T16 (5b-2b) changes to "Connect your Gmail to email bulletins from your own account. The app can only send email for you; it can't read your mail." (clarification 20, so the page never promises emailing before Review has it); "Connected as **{address}**." and "Works in all your churches." with **Disconnect** ("Disconnecting…"; no confirmation, no toast). Everyone sees the same page. No `LegacySettingsNote` (answer 4). The header's **Settings** link exists since 6a-1, so `AppNav` and the account menu do not change. The section nav stays a wrapping row on a phone: four short labels fit one row at 375 px (T19 checks).
11. **The message itself** (B "service_output.py additions", amended). A new pure module `backend/bulletin_email.py`, not `service_output.py`: the subject uses the printed bulletin's date form (`printed_bulletin.printed_date`, "October 4, 2026", answer 5), and `printed_bulletin` already imports `service_output`, so `service_output` cannot import it back. `bulletin_email_subject`, `default_bulletin_message` ("Hi! Here's the worship bulletin for this Sunday."; another day: "Hi! Here's the worship bulletin for Wednesday, February 10."), `plan_bulletin_addressing` and `compose_bulletin_email` (one plain-text body, then each attachment with its MIME type). The apostrophe is straight, like the app's other copy (B had a curly one, Streamlit's; owner question 2). The shared fixture `backend/tests/fixtures/shared/bulletin_email.json` (six dates: three Sundays, a Thursday, a Wednesday, a Friday) pins the subject and the message for the backend and `lib/email.ts`. `email_addresses.dedupe_addresses` keeps the first spelling of each address, ignoring case.
12. **[owner-visible] The two attachments** (answer 1). `BulletinEmailIn.attachments`: a required list of `"docx"` (the bulletin copy, `build_document(…, "bulletin")`, `worship_October_04_2026.docx`) and/or `"pdf"` (the printed bulletin, `build_printed(…, "pdf", translation)`, `printed_bulletin_October_04_2026.pdf`); an empty list is a 422 "Choose at least one attachment." on `attachments`. `BulletinEmailIn.translation` is the draft's, as `POST /documents/printed` takes it; the PDF's readings are fetched as for the download and charge the `scripture` bucket the same way (one token per upstream part). The dialog shows both boxes with the file names under them; **Bulletin copy (Word)** is ticked the first time; the boxes are remembered on the device for this user and church (`wsb:emailPrefs:{userId}:{churchId}`, `{version: 1, contact_ids, attachments}`) as soon as one is ticked or unticked (owner question 4); the contacts are remembered after a successful send (B). The (signed-in) layout's draft pruning also removes this key for churches the user has left.
13. **Idempotency keeps an uncertain send** (B §Errors "Stored"; F §1.6). B assumed slice 1 would add `run_idempotent(..., store_error=...)`; it did not. T12 adds it: a 5xx `DomainError` for which `store_error` returns True is stored and replayed like a 4xx; `RateLimited` is never stored; the default is unchanged for every other route. The route passes `store_error` that keeps an answer with `details.send_uncertain`.
14. **The contacts a send names** (B "Modules" `email_contacts.py`). `email_contacts.get_contacts_by_ids(church_id, ids, *, session=None)`: the church's contacts among the ids, in the order asked, each once (5b-1 already added the session, the order and `as_uuid`). The send runs every stored address through `normalize_address` again (a Streamlit-era " Office@Example.ORG " is sent as "Office@example.org"); one it refuses is a 422 on `contact_ids`: "The saved contact “{name, or the address when there is none}” has an invalid email address. An admin can fix it in Settings → Contacts." (`MALFORMED_CONTACT_HINT`, answer 4). In the dialog such a contact (`email_valid: false`, 5b-1) is listed, cannot be ticked, and says "This address doesn't look valid. An admin can fix it in Settings → Contacts." (5b-1's follow-up).
15. **`send_bulletin_email`** (B "usecases/email.py", §Errors; T13). The order is B's: (5) one read session for the recipients (a contact the church does not have is a 404 with `details.field = "contact_ids"`; a refused saved address or other address is a 422 naming it, the other address cut to 60 characters; none or more than 50 after de-duplication is a 422 on `recipients`) and then the attachments (new: none is a 422 on `attachments`) and the connection read; (6) not configured is a 503, no connection (or a NULL address) the 409; (7) the files (5a's `InvalidInput` and `NotFound` pass through; no hymn use is recorded), then the message, which must be 3.5 MB at most (`MAX_RAW_BYTES`, clarification 5; else a 422 on `attachments`, "The attachments are too large to email. Try sending only the bulletin copy.", with nothing charged or sent); (8) `charge()`, the `email` bucket, the only 429 here, right before Google; (9-10) the refresh and the send with no session open. A refused grant (`invalid_grant` on refresh, a missing scope on send) deletes the connection only if it still holds the token that failed; a connection made again meanwhile is kept ("Your Gmail connection changed while sending. Nothing was sent. Try again."). The send's uncertain outcomes carry `details.send_uncertain: true` (502 for a Gmail 5xx, 504 for no answer); every other `gmail_send_failed` carries `{disconnected, send_uncertain: false}`. Gmail refusing the account itself (`ACCOUNT_REFUSED`) is its own 502, "Gmail won't send from this Google account. Nothing was sent. Check that you can send email in Gmail with it, then try again.", not "Check the email addresses"; the connection is kept, and the failure's log line names Google's reason (`bulletin_email.send … outcome=account_refused status=400 google_error=failedPrecondition`). The log line after a send: `bulletin_email.sent church_id=… user_id=… recipients=n bcc=… attachments=docx,pdf bytes=… ms=…`.
16. **`POST /bulletin-emails`** (B API, Routes). `require_church` (any member, owner decision 5), then the user, then `idempotency_key(required=True)`, then the config; FastAPI checks the body after them, so a request with no key and a bad body is the key's 422 (T14 checks the order). `run_idempotent` gets `church_id` (F §1.6's church-scope amendment) and `store_error`. `BulletinEmailIn {service, contact_ids ≤ 200, additional_emails ≤ 200 × 320, message ≤ 5000 | null, attachments ≤ 2, translation ≤ 20 | null}` (`extra="forbid"`); `BulletinEmailOut {sent: true, recipient_count}`. The `email` bucket's 429 is never stored, so the same key works after `Retry-After`.
17. **The dialog's rules** (B "Pure modules" `lib/email.ts`, `lib/idempotency.ts`). `lib/email.ts`: `bulletinEmailSubject`, `defaultBulletinMessage` (the shared fixture), `parseAddressList` (commas, semicolons, new lines; `Name <a@b.org>` read as the address), `countRecipients` (each address once, ignoring case and spaces), `fieldTarget` (`additional_emails*` under Other addresses, `message` under Message, `attachments` under Attachments, `recipients` and `contact_ids*` under To, anything else at the top), the remembered choices, `bulletinEmailBody` (the downloads' `serviceBody(draft)` and the draft's translation, as `printedRequest`) and the reopen request (`parseReopen`, only for the active church). B's `createSendKeyTracker` is the existing `createKeyTracker` plus a new `rotate()`: a 2xx or a 4xx drops the key; a 5xx, a 429 or a lost connection keeps it; only **Send again anyway** rotates it. `POST /bulletin-emails` gets a 90 s client timeout (B: 60 s): the PDF's readings have a 20 s deadline, but Google's 15 s and 30 s are per phase (clarification 5), so the server has no overall deadline and 90 s is the overall limit; a send still unanswered then is the lost-connection case of clarification 18 (possibly sent, plain Send off). The uncertain send is remembered in sessionStorage (`wsb:emailUncertain:{userId}:{churchId}`, `{version: 1, message}`; `readUncertainSend`, `writeUncertainSend`, `clearUncertainSend`).
18. **[owner-visible] The card and the dialog** (B "Review step", "Email dialog", "Send outcomes", flows B and D). There is no `email-slot.tsx` placeholder in the code (5a never built one); the card is the last on Review, after the printed bulletin. Card: "Email the bulletin", "Send the bulletin and a short message from your own Gmail."; while loading a skeleton line and a disabled **Email bulletin…**; "Couldn't check your Gmail connection." with **Retry**; "Emailing isn't set up on this deployment."; "Connect your Gmail to email the bulletin from your own account." with **Connect Gmail** (back to Review, and the dialog then opens); connected: "Sends from {address}." and **Email bulletin…**, turned off with "Choose a service date on step 1 to email the bulletin." or "Fix the readings on step 1 to email the bulletin." as the downloads are (B: the date only; a readings error would break the PDF's readings too; owner question 3); nothing else turns it off. Dialog (below `md` a bottom sheet, the same pattern as 5b-1's approved contact editor: `max-md:bottom-0 … max-md:max-h-[85dvh] max-md:overflow-y-auto`, so the whole sheet scrolls with **Cancel** and **Send** inside it and the iPhone keyboard never leaves Send out of reach; centred from `md`, the fields scrolling above the buttons): "Email the bulletin"; From; To (one row per contact, 44 px, the name and the address under it, the address alone when there is none; three skeleton rows; "Couldn't load your contacts." with **Retry**, other addresses still work; "No saved contacts yet. Type addresses below." with **Manage contacts** for owners and admins); Other addresses ("name@example.com", "Separate addresses with commas."); "Recipients won't see each other's addresses (sent as BCC)." from two people; Subject; Attachments (while **Printed bulletin (PDF)** is ticked, the printed card's own notes under them: "Not filled in: …" and "From last week, not checked yet: …"); Message (4 rows, at most 5000 characters); "Not finished yet: {n} item(s) under Still to do." and "Not saved to the archive yet. The attachments use the service as it is on screen now." when they apply (B had "Still missing: …", which would repeat Still to do's sentences); **Cancel** and **Send to {n} person/people** ("Send" turned off with "Choose at least one recipient."; "You can email at most 50 people at once."; "Choose at least one attachment."; "Sending…", then "Still working…" after 8 s, as the downloads say). A send closes it with the toast "Email sent to {n} person/people.", remembers the contacts, and resets Other addresses and the message. Failures show in the dialog, never as a toast, where B's table puts them: under the field and focused for a 422; under To for a contact gone (the contacts are refetched); at the top with **Go to Hymns** for a hymn gone, **Connect Gmail** for "Connect your Gmail first, then try again." and **Reconnect Gmail** for a dropped grant (both keep the form for the way back; the status is refetched), **Send again anyway** for an uncertain send, Send turned off for Gmail not set up; a lost connection says "We lost the connection before Gmail confirmed, so the email may already have been sent. Check your Gmail Sent folder before sending again."; a 429 and anything else the server's sentence. After an uncertain send or a lost connection, plain **Send** stays off and the message stays at the top with **Send again anyway** as the only way to send (with a new key), also after closing the dialog, leaving Review or a reload in that tab (sessionStorage, per user and church); a definite answer to **Send again anyway** clears it. While a send runs the dialog cannot be closed. Back from Google (flow B), the card reads `wsb:reopenEmailDialog` when it mounts, decides once the status has settled (reopening the dialog with what was in it only when connected and for this church, and then only once the printed card's `useBulletinCarry` has carried last week's bulletin in or its lookup failed, so a PDF sent at once has it) and forgets it either way.
19. **The contacts load when the dialog opens** (B: prefetched when Review mounts). Review then makes no contacts request unless the dialog is opened, and the existing Review tests need only the status route.
20. **[owner-visible] The Contacts caption** returns to S's "People you can email the bulletin to from the Review step." in T16, with the dialog (5b-1 clarification 3 and its follow-up), so it is never true before emailing is. For the same reason the Account page's Gmail sentence is "Connect the Gmail account you sign in with. …" in 5b-2a and becomes "Connect your Gmail to email bulletins from your own account. …" in T16 (clarification 10).
21. **[owner-visible] Every new user-facing string** (no em dashes). Settings: "Account"; "Signed in with Google."; "Log out"; "Gmail"; "Couldn't check your Gmail connection."; "Per-user Gmail sending isn't configured on this deployment."; "Connect the Gmail account you sign in with. The app gets permission only to send email for you; it can't read your mail." (5b-2a); "Connect your Gmail to email bulletins from your own account. The app can only send email for you; it can't read your mail." (5b-2b); "Connect Gmail"; "Opening Google…"; "Connected as {address}."; "Works in all your churches."; "Disconnect"; "Disconnecting…". Callback: "Gmail"; "Connecting your Gmail…"; "Still working. This can take up to a minute."; "Gmail connected"; "Gmail connection was cancelled."; "Google couldn't connect your Gmail."; "Gmail connection didn't finish. Try connecting again."; "Try again"; "Go back"; "Something went wrong.". Card: "Email the bulletin"; "Send the bulletin and a short message from your own Gmail."; "Emailing isn't set up on this deployment."; "Connect your Gmail to email the bulletin from your own account."; "Sends from {address}."; "Email bulletin…"; "Choose a service date on step 1 to email the bulletin."; "Fix the readings on step 1 to email the bulletin.". Dialog: "From"; "To"; "This address doesn't look valid. An admin can fix it in Settings → Contacts."; "No saved contacts yet. Type addresses below."; "Manage contacts"; "Couldn't load your contacts."; "Other addresses"; "name@example.com"; "Separate addresses with commas."; "Recipients won't see each other's addresses (sent as BCC)."; "Subject"; "Attachments"; "Bulletin copy (Word)"; "Printed bulletin (PDF)"; "Message"; "Not finished yet: {n} item(s) under Still to do."; "Not saved to the archive yet. The attachments use the service as it is on screen now."; "Send"; "Send to {n} person/people"; "Sending…"; "Still working…"; "Choose at least one recipient."; "You can email at most 50 people at once."; "Choose at least one attachment."; "Go to Hymns"; "Reconnect Gmail"; "Send again anyway"; "We lost the connection before Gmail confirmed, so the email may already have been sent. Check your Gmail Sent folder before sending again."; "Email sent to {n} person/people.". The email: "Worship service for {Month D, YYYY}"; "Hi! Here's the worship bulletin for this Sunday."; "Hi! Here's the worship bulletin for {Weekday}, {Month D}.". From the server (B's, without dashes; five new): "Per-user Gmail sending isn't configured on this deployment."; "Gmail sending isn't set up correctly on this deployment."; "This Gmail connection request expired or was already used. Try connecting again."; "That Google approval has expired or was already used. Try connecting again."; "Google returned an incomplete response. Try connecting again."; "Google didn't give permission to send email. Try again and allow “Send email on your behalf”."; "Could not read your email address from Google."; "That Google account doesn't match your signed-in email ({email}). Connect the Gmail account you're logged in with."; "Google did not return a refresh token. Remove this app's access at https://myaccount.google.com/permissions and connect again."; "Couldn't reach Google. Try connecting again in a minute."; "Google took too long to respond. Try connecting again."; "One of the selected contacts no longer exists. Refresh the list and try again."; "The saved contact “{name}” has an invalid email address. An admin can fix it in Settings → Contacts."; "“{value}” isn't a valid email address."; "Please select at least one recipient or enter an email address."; "You can email at most 50 people at once."; "Choose at least one attachment." (new); "Connect your Gmail first, then try again."; "Your Gmail connection has expired or was removed. Reconnect Gmail and try again."; "Your Gmail connection no longer allows sending. Reconnect Gmail and try again."; "Your Gmail connection changed while sending. Nothing was sent. Try again."; "Couldn't reach Gmail. Nothing was sent. Try again in a minute."; "Google took too long to respond. Nothing was sent. Try again."; "Gmail's sending limit has been reached. Nothing was sent. Try again later."; "Gmail couldn't send this message. Nothing was sent. Check the email addresses and try again."; "Gmail won't send from this Google account. Nothing was sent. Check that you can send email in Gmail with it, then try again." (new); "The attachments are too large to email. Try sending only the bulletin copy." (new); "Gmail reported a problem, so the email may already have been sent. Check your Gmail Sent folder before sending again."; "Gmail didn't confirm the email, so it may already have been sent. Check your Gmail Sent folder before sending again.". Reused: "Retry", "Cancel", "Loading", "Too many requests. Try again in {n} seconds.", the printed card's "Not filled in: …" and "From last week, not checked yet: …", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.", "Give each custom element a label.", the Contacts caption of clarification 20.
22. **No database change.** `gmail_tokens` and `oauth_states` exist since `0001_baseline` with the columns B assumes; nothing is added. Alembic head stays `0007_bulletin_images`.
23. **Docs.** T10 and T17 append items 7-10 and 11-16 to `docs/manual-verification.md` → "## Slice 5b" (no new `##` heading, so `test_slice1_docs.py`'s pin does not move). T19 inserts `### Slice 5b-2 record` before `## Backups`, after `### Slice 5b-1 record`, and in the same commit brings the runbook's Railway variables row for `GOOGLE_*` and its "Google OAuth client" paragraph up to date (the new redirect URIs, what reads the variables now).
24. **Deviations from B** (each the lean choice; none changes an owner answer):
    - `bulletin_email.py` instead of additions to `service_output.py` (clarification 11); a straight apostrophe in the message.
    - `revoke_token` returns a bool; the Google functions take no `http` argument (the module client is swapped in tests); `is_connected` is dropped (clarifications 2, 4, 5).
    - The startup check also logs one INFO line (clarification 3).
    - `attachments` and `translation` join `BulletinEmailIn`; "Choose at least one attachment." is new (clarification 12).
    - `store_error` is added here, not in slice 1 (clarification 13).
    - `POST /gmail-connection/auth-url` is rate-limited (`gmail_connect`); Gmail refusing the account has its own message; a message over 3.5 MB is refused before Google (clarifications 5, 7, 15).
    - After an uncertain send only **Send again anyway** sends, remembered in the tab; B let a plain Send replay the key (clarification 18).
    - The card's button also waits for readings without errors; the dialog's "not finished" note counts the Still to do items; the contacts load when the dialog opens; the client timeout is 90 s (clarifications 17-19).
    - No parity gate, Streamlit smoke test, banner, legacy note, `check_contact_addresses.py` or `google_oauth_legacy.py` (answer 4).

### Risks
- **Google may refuse the new redirect URI** until `worship-service-builder.vercel.app` is an authorized domain on the consent screen, and `vercel.app` is a public suffix, so Google may ask to verify ownership of the subdomain (Search Console: a file or meta tag served by the Next app). Found in T19's first owner step, before the merge; the fallback is a custom domain the owner controls (a new plan). With two PRs, nothing of group B is built on top until it works.
- **The consent screen's publishing status** (owner question 5; T19 Step 2). `gmail.send` is a Sensitive scope (https://developers.google.com/workspace/gmail/api/auth/scopes). Confirmed: in **Testing** only the accounts listed as test users (at most 100) can connect, anyone else gets Google's "Access blocked" page, and every refresh token expires 7 days after consent (https://support.google.com/cloud/answer/15549945), so each sender reconnects weekly (the first send after expiry says "Your Gmail connection has expired or was removed. Reconnect Gmail and try again." and **Reconnect Gmail** keeps the dialog's form); **In production** without verification the app works but shows the "Google hasn't verified this app" warning and is capped at 100 new users in total (https://support.google.com/cloud/answer/7454865). Not confirmed: that the warning shows only once (with `prompt=consent` it probably shows on every connect and reconnect); that tokens issued in Testing stop expiring after the switch (so each sender reconnects once after it); and how Google treats an unverified app whose policy expects verification before a user-facing launch. A Google Workspace admin may also block unverified apps for that organization's accounts.
- **Gmail honours Bcc in a raw message** and strips it from delivered copies (documented); T19's phone check verifies it with the owner's own addresses only.
- **An uncertain send** is replayed for 15 minutes in this process only (F §1.6's in-memory store): a Railway restart between a send and its retry, or **Send again anyway** without checking the Sent folder, can send a second copy.
- **The `scripture` bucket is charged for the PDF's readings before the `email` bucket is checked**, so an 11th email in the hour still spends a few scripture tokens (out of 60 per 5 minutes).
- **The callback URL in Vercel's request logs** carries a single-use code that expires in minutes and is useless without the client secret on Railway (B's risk 7; accepted).
- **The frozen Streamlit app still runs** (`liturgy-frozen`) with the same client and the same `gmail_tokens` rows; it deletes a row on any refresh 400/401 and puts every recipient in To. Nothing here changes it; nobody uses it (answer 4).

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/tests/test_google_oauth.py`, `backend/tests/fake_google.py` | the module's tests (ported and new); the fake Google | T2, T3 |
| `backend/usecases/email.py` (+ `backend/tests/test_usecase_email.py`) | the connection usecases; `send_bulletin_email` | T5, T13 |
| `backend/api/routes/gmail.py` (+ `backend/tests/test_api_gmail.py`) | `/gmail-connection` | T6 |
| `frontend/src/lib/gmail.ts` (+ `.test.ts`), `frontend/src/lib/queries/gmail.ts`, `frontend/src/lib/supabase/client.test.ts` | the trip to Google; the Gmail queries; the Supabase option's test | T7 |
| `frontend/src/components/gmail/gmail-callback.tsx` (+ `.test.tsx`), `frontend/src/app/(signed-in)/gmail/callback/page.tsx` | `/gmail/callback` | T8 |
| `frontend/src/components/settings/account-settings-page.tsx` (+ `.test.tsx`), `frontend/src/app/(signed-in)/(church)/settings/account/page.tsx` | Settings → Account | T9 |
| `backend/bulletin_email.py` (+ `backend/tests/test_bulletin_email.py`, `backend/tests/fixtures/shared/bulletin_email.json`) | the subject, the message, To and Bcc, the MIME message | T11 |
| `backend/api/routes/bulletin_emails.py` (+ `backend/tests/test_api_bulletin_emails.py`) | `POST /bulletin-emails` | T14 |
| `frontend/src/lib/email.ts` (+ `.test.ts`) | the dialog's rules and remembered choices | T15 |
| `frontend/src/lib/queries/email.ts`, `frontend/src/components/builder/review/email-card.tsx` (+ `.test.tsx`), `frontend/src/components/builder/review/email-dialog.tsx` | the send; the card and the dialog | T16 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/integrations/http.py`, `backend/tests/test_http_client.py` | `post()` | T1 |
| `backend/google_oauth.py` | rewritten (T2), the Google calls (T3), the secret out of `repr` (T4) | T2-T4 |
| `backend/tests/test_no_streamlit_in_core.py` | `google_oauth`, `usecases.email`, `bulletin_email` | T2, T5, T11 |
| `backend/api/settings.py`, `backend/api/startup.py`, `backend/api/main.py`, `backend/.env.example`, `backend/tests/test_startup.py` | the `GOOGLE_*` settings and the startup lines | T4 |
| `backend/api/deps.py`, `backend/api/main.py`, `backend/tests/test_route_guards.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | `get_google_config`; the routers mounted; `USER_SCOPED`; regenerated | T6, T14 |
| `backend/api/ratelimit.py`, `backend/tests/test_ratelimit.py` | the `gmail_connect` bucket and its pin | T6 |
| `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/timeouts.ts`, `frontend/src/lib/supabase/client.ts`, `frontend/src/lib/urls.ts`, `frontend/src/lib/urls.test.ts` | the Gmail types; 40 s (T7; 75 s after 5b-2a build review M3) and 90 s (T15); `detectSessionInUrl: false`; `/gmail/callback` | T7, T15 |
| `frontend/src/components/settings/sections.ts`, `frontend/src/components/settings/settings-layout.test.tsx`, `frontend/src/test/fixtures/index.ts` | **Account** in the nav; `gmailConnection()`, `gmailDisconnected()` | T9 |
| `docs/manual-verification.md` | items 7-10 (T10), 11-16 (T17) | T10, T17 |
| `backend/email_addresses.py`, `backend/tests/test_email_addresses.py` | `dedupe_addresses` | T11 |
| `backend/api/idempotency.py`, `backend/tests/test_idempotency.py`, `backend/email_contacts.py`, `backend/tests/test_email_contacts.py` | `store_error`; `get_contacts_by_ids` | T12 |
| `frontend/src/lib/idempotency.ts` (+ test), `frontend/src/lib/draft/prune.ts` (+ test) | `rotate()`; the remembered choices pruned | T15 |
| `frontend/src/components/builder/review/review-send-step.tsx` (+ test), `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, `frontend/src/components/settings/contacts-settings-page.tsx` (+ test), `frontend/src/components/builder/review/printed-card.tsx`, T9's `account-settings-page.tsx` (+ test) | the card on Review; the status route in the tests that render Review; the Contacts caption; `NotFilledInLines` exported for the dialog; the Account page's Gmail sentence for 5b-2b | T16 |
| `docs/ops-runbook.md` | "### Slice 5b-2 record", the `GOOGLE_*` row and the Google client paragraph (the records PR, after the merge) | T19 |

**Deleted** (T2): `backend/tests/test_oauth_state.py`, `backend/tests/test_gmail_exchange.py`, `backend/tests/test_gmail_token_store.py` (every assertion about kept code ported to `test_google_oauth.py`).

**Counts in the PR:** 76 paths (one PR): 29 created (this plan, the 27 new code, test and fixture files above and the 5b-2a build review's `backend/tests/test_gmail_state_postgres.py`), 44 modified (the code, test, doc and API paths above, plus `docs/ops-runbook.md`, whose 5b-1 record rides along until its records PR is merged, and the build review's `frontend/src/lib/api/client.test.ts` and `docs/superpowers/specs/2026-09-25-slice-5b-gmail-email-design.md`), 3 deleted. **Untouched:** migrations, `db/models.py`, `domain_errors.py` (every Gmail code is registered since slice 1), `api/errors.py`, `usecases/documents.py`, `usecases/contacts.py`, `lib/queries/keys.ts`, `lib/api/errors.ts`, `proxy.ts`, the draft schema, `app.py`, `streamlit_views`, `streamlit_tests`.

**Task order and review batch:** T1 → T17 (two PRs: T1 → T10, then T11 → T17), each one commit and a backup push; then one review of the batch with its fixes as `Fix: …` commits; T18 verifies and opens the draft PR on the owner's yes; T19 runs the owner's Google and Railway setup (before the first merge only), merges on the owner's yes, runs the phone check and writes the record.

---


## Group A: the Gmail connection (T1-T10)

### Task 1: `integrations.http.post` (clarification 4)

**Files:**
- Modify: `backend/tests/test_http_client.py`, `backend/integrations/http.py`

- [ ] **Step 1: Write the failing tests**

Google's token, revoke and Gmail send endpoints take a POST. Like `get()`, `post()` goes through the one shared client (its User-Agent, its https-only hook) with a timeout chosen per call; unlike `get()`, it never follows a redirect, so a code exchange or an email is never replayed at another address.

**Append to `backend/tests/test_http_client.py`:**

````python


# --- slice 5b-2: post(), for Google's token, revoke and Gmail send endpoints ----------------------

def test_post_sends_a_form_or_json_with_its_own_timeout_and_the_user_agent():
    seen = _install(lambda request: httpx.Response(200, json={"ok": True}))
    r = http.post("https://oauth2.example.test/token", data={"grant_type": "refresh_token", "code": "c"},
                  timeout=httpx.Timeout(15.0, connect=5.0))
    assert r.json() == {"ok": True}
    http.post("https://gmail.example.test/send", json={"raw": "abc"}, headers={"Authorization": "Bearer t"},
              timeout=httpx.Timeout(30.0, connect=5.0))
    assert [request.method for request in seen] == ["POST", "POST"]
    assert seen[0].headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert seen[0].content == b"grant_type=refresh_token&code=c"
    assert seen[1].headers["Content-Type"] == "application/json"
    assert seen[1].headers["Authorization"] == "Bearer t"
    assert seen[1].headers["User-Agent"] == "WorshipServiceBuilder/1.0"
    assert [request.extensions["timeout"] for request in seen] == [
        {"connect": 5.0, "read": 15.0, "write": 15.0, "pool": 15.0},
        {"connect": 5.0, "read": 30.0, "write": 30.0, "pool": 30.0},
    ]
    with pytest.raises(TypeError):
        http.post("https://oauth2.example.test/token", data={})          # timeout is required


def test_post_never_follows_a_redirect_and_refuses_plain_http():
    seen = _install(lambda request: httpx.Response(307, headers={"Location": "https://elsewhere.example.test/"}))
    r = http.post("https://oauth2.example.test/token", data={"a": "b"}, timeout=httpx.Timeout(5.0))
    assert r.status_code == 307                                          # returned, not replayed elsewhere
    assert [str(request.url) for request in seen] == ["https://oauth2.example.test/token"]
    with pytest.raises(httpx.UnsupportedProtocol):
        http.post("http://oauth2.example.test/token", data={"a": "b"}, timeout=httpx.Timeout(5.0))
    assert len(seen) == 1
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_http_client.py 2>&1 | tail -3`
**Expected** (`http.post` does not exist yet):
```
FAILED backend/tests/test_http_client.py::test_post_sends_a_form_or_json_with_its_own_timeout_and_the_user_agent
FAILED backend/tests/test_http_client.py::test_post_never_follows_a_redirect_and_refuses_plain_http
2 failed, 7 passed in <t>s
```

- [ ] **Step 3: Add `post()`**

**In `backend/integrations/http.py`, replace:**

````python
Every upstream call the new app makes (Lectio, Vanderbilt, bible-api, ESV)
goes through get(). One module-level httpx.Client carries the settings F §2.7
fixes, so no caller picks its own:
- User-Agent "WorshipServiceBuilder/1.0";
- follow_redirects=True, but only to https: a request event hook refuses any
  non-https URL, and httpx runs that hook for every redirect hop too;
- connect timeout 5 s; the read timeout is chosen per call (S Timeouts).
````

**with:**

````python
Every upstream call the new app makes (Lectio, Vanderbilt, bible-api, ESV,
and from slice 5b-2 Google's OAuth and Gmail endpoints) goes through get() or
post(). One module-level httpx.Client carries the settings F §2.7 fixes, so
no caller picks its own:
- User-Agent "WorshipServiceBuilder/1.0";
- follow_redirects=True, but only to https: a request event hook refuses any
  non-https URL, and httpx runs that hook for every redirect hop too;
- connect timeout 5 s; the read timeout is chosen per call (S Timeouts);
- post() never follows a redirect: a POST (a token exchange, an email send)
  is answered where it was sent or not at all, never replayed elsewhere.
````

**In `backend/integrations/http.py`, replace:**

````python

def set_http_for_tests(client: httpx.Client | None) -> None:
````

**with:**

````python

def post(url: str, *, data: Mapping[str, str] | None = None, json: object = None,
         headers: Mapping[str, str] | None = None, timeout: httpx.Timeout) -> httpx.Response:
    """POST a form (`data`) or a JSON body (`json`) to `url` with the shared
    client and the given `timeout` (slice 5b-2: Google's token, revoke and
    Gmail send endpoints). A redirect is returned as it is, never followed.

    As get(): transport problems raise httpx.HTTPError subclasses, a 4xx or
    5xx is returned for the caller to classify."""
    return _client.post(url, data=data, json=json, headers=headers, timeout=timeout, follow_redirects=False)


def set_http_for_tests(client: httpx.Client | None) -> None:
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_http_client.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`12 passed in <t>s`; `1671 passed, 26 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/integrations/http.py backend/tests/test_http_client.py
git commit -q -m "Slice 5b-2: integrations.http.post for Google's endpoints" -m "post() sends a form or a JSON body through the shared client (its
User-Agent and https-only hook) with a timeout chosen per call, and never
follows a redirect: a token exchange or an email is answered where it was
sent or not at all. Google's token, revoke and Gmail send endpoints use it
(Tasks 3 and 13)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1671 passed, 26 skipped`; frontend `780 passed` in 94 files.

### Task 2: `google_oauth`: the config, the consent URL, the states and the token store (B "Modules", "google_oauth.py after the refactor"; clarifications 2 and 5)

**Files:**
- Create: `backend/tests/test_google_oauth.py`
- Modify (rewrite): `backend/google_oauth.py`; Modify: `backend/tests/test_no_streamlit_in_core.py`
- Delete: `backend/tests/test_oauth_state.py`, `backend/tests/test_gmail_exchange.py`, `backend/tests/test_gmail_token_store.py`

- [ ] **Step 1: Write the failing tests, port the old ones, delete the old files**

`test_google_oauth.py` replaces the three Streamlit-era files (21 tests). Ported: `test_scopes_unchanged`, `test_create_state_persists_row` (now with the 10-minute expiry), `test_consume_state_is_single_use`, `test_consume_unknown_or_empty_state_returns_none`, `test_consume_expired_state_returns_none_and_deletes`, `test_save_and_is_connected` and `test_save_replaces_single_row` (as `get_connection` after `save_user_token`), `test_disconnect` (as `delete_connection`), and the old `build_auth_url` test's "no `gmail_oauth` marker" (now with the config and the login hint). Not ported, because their code goes (clarification 2): the five `should_handle_gmail_callback` cases, `send_email`'s refusal, `_access_token_for`'s three tests, and the old `exchange_code`'s three (Task 3 tests the new one: a mismatch is refused, a case-insensitive match returns Google's spelling). The last test checks the Streamlit functions, `os.getenv` and `requests` are gone.

**Create `backend/tests/test_google_oauth.py`:**

````python
"""google_oauth (slice 5b spec, Testing "test_google_oauth.py"; slice 5b-2):
the config, the consent URL, the single-use states and the token store; Task
3 adds the Google calls. It replaces test_oauth_state.py, test_gmail_exchange.py
and test_gmail_token_store.py: every assertion they made about code that is
kept is ported here; the Streamlit-only functions went with their tests."""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import pytest

import google_oauth
from db import session_scope
from db.models import GmailToken, OAuthState

CONFIG = google_oauth.GoogleOAuthConfig(
    client_id="client-123", client_secret="secret-456", redirect_uri="https://app.example.org/gmail/callback")


def test_scopes_unchanged():
    assert google_oauth.SCOPES == [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/gmail.send",
    ]
    assert google_oauth.GMAIL_SEND_SCOPE in google_oauth.SCOPES


def test_the_config_is_configured_only_with_all_three_values():
    assert CONFIG.configured
    for blank in ("client_id", "client_secret", "redirect_uri"):
        values = {"client_id": "a", "client_secret": "b", "redirect_uri": "https://c.example.org/gmail/callback"}
        values[blank] = ""
        assert not google_oauth.GoogleOAuthConfig(**values).configured, blank


def test_the_consent_url_asks_for_offline_access_with_the_state_and_the_signed_in_account():
    url = google_oauth.build_auth_url(CONFIG, "state-token-123", login_hint="owner@example.com")
    parts = urlsplit(url)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == google_oauth.AUTH_URI
    assert {key: values[0] for key, values in parse_qs(parts.query).items()} == {
        "client_id": "client-123",
        "redirect_uri": "https://app.example.org/gmail/callback",
        "response_type": "code",
        "scope": " ".join(google_oauth.SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": "state-token-123",
        "login_hint": "owner@example.com",
    }
    assert "gmail_oauth" not in url
    assert "login_hint" not in google_oauth.build_auth_url(CONFIG, "s")


def test_create_state_persists_a_row_bound_to_the_user_for_ten_minutes(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    before = datetime.now(timezone.utc)
    state = google_oauth.create_state(uid)
    assert isinstance(state, str) and len(state) >= 20
    with session_scope() as s:
        row = s.get(OAuthState, state)
        assert row.user_id == uid
        expires_at = row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at
    assert before + timedelta(minutes=10) <= expires_at <= datetime.now(timezone.utc) + timedelta(minutes=10)


def test_create_state_purges_only_expired_states(tmp_db, make_user):
    me, other = make_user(email="a@example.com"), make_user(email="b@example.com")
    old = google_oauth.create_state(me)
    live = google_oauth.create_state(other)                 # another user's, still valid
    with session_scope() as s:
        s.get(OAuthState, old).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    google_oauth.create_state(me)
    with session_scope() as s:
        assert s.get(OAuthState, old) is None
        assert s.get(OAuthState, live) is not None


def test_consume_state_is_single_use(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    assert google_oauth.consume_state(state) == uid
    assert google_oauth.consume_state(state) is None        # already consumed
    with session_scope() as s:
        assert s.get(OAuthState, state) is None


def test_consume_unknown_or_empty_state_returns_none(tmp_db):
    assert google_oauth.consume_state("nope") is None
    assert google_oauth.consume_state("") is None


def test_consume_expired_state_returns_none_and_deletes(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    state = google_oauth.create_state(uid)
    with session_scope() as s:
        s.get(OAuthState, state).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    assert google_oauth.consume_state(state) is None
    with session_scope() as s:
        assert s.get(OAuthState, state) is None              # consumed even when expired


def test_save_user_token_keeps_one_row_per_user_and_replaces_it(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    assert google_oauth.get_connection(uid) is None
    google_oauth.save_user_token(uid, "a@example.com", "refresh-1")
    google_oauth.save_user_token(uid, "A@Example.com", "refresh-2")
    with session_scope() as s:
        rows = s.query(GmailToken).filter(GmailToken.user_id == uid).all()
        assert [(r.google_email, r.refresh_token) for r in rows] == [("A@Example.com", "refresh-2")]
    assert google_oauth.get_connection(uid) == google_oauth.GmailConnection("A@Example.com", "refresh-2")


def test_a_row_without_an_address_is_not_a_connection(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    with session_scope() as s:
        s.add(GmailToken(user_id=uid, google_email=None, refresh_token="refresh-1"))
    assert google_oauth.get_connection(uid) is None
    google_oauth.save_user_token(uid, "  ", "refresh-2")
    assert google_oauth.get_connection(uid) is None


def test_delete_connection_returns_the_token_and_only_if_token_keeps_a_newer_one(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    assert google_oauth.delete_connection(uid) is None
    google_oauth.save_user_token(uid, "a@example.com", "refresh-old")
    google_oauth.save_user_token(uid, "a@example.com", "refresh-new")     # connected again meanwhile
    assert google_oauth.delete_connection(uid, only_if_token="refresh-old") is None
    assert google_oauth.get_connection(uid).refresh_token == "refresh-new"
    assert google_oauth.delete_connection(uid, only_if_token="refresh-new") == "refresh-new"
    assert google_oauth.get_connection(uid) is None
    google_oauth.save_user_token(uid, "a@example.com", "refresh-3")
    assert google_oauth.delete_connection(uid) == "refresh-3"


def test_the_store_joins_the_callers_session(tmp_db, make_user):
    uid = make_user(email="a@example.com")
    with session_scope() as s:
        state = google_oauth.create_state(uid, session=s)
        google_oauth.save_user_token(uid, "a@example.com", "refresh-1", session=s)
        assert google_oauth.get_connection(uid, session=s).refresh_token == "refresh-1"
        assert google_oauth.delete_connection(uid, session=s) == "refresh-1"
        assert s.get(OAuthState, state) is not None
    assert google_oauth.get_connection(uid) is None


def test_the_streamlit_functions_are_gone():
    for name in ("should_handle_gmail_callback", "send_email", "disconnect", "is_configured", "is_connected",
                 "_fetch_email", "_access_token_for", "_user_email", "_client_id", "_google_error"):
        assert not hasattr(google_oauth, name), name
    source = open(google_oauth.__file__, encoding="utf-8").read()
    assert "os.getenv" not in source and "import requests" not in source and "os.environ" not in source
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts; "
````

**with:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth; "
````

**Delete `backend/tests/test_oauth_state.py`:** (`git rm -q 'backend/tests/test_oauth_state.py'`; its tests are ported to the new file above)

**Delete `backend/tests/test_gmail_exchange.py`:** (`git rm -q 'backend/tests/test_gmail_exchange.py'`; its tests are ported to the new file above)

**Delete `backend/tests/test_gmail_token_store.py`:** (`git rm -q 'backend/tests/test_gmail_token_store.py'`; its tests are ported to the new file above)

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_google_oauth.py 2>&1 | tail -3`
**Expected** (`GoogleOAuthConfig` does not exist yet: an `AttributeError` at import, above these lines):
```
ERROR backend/tests/test_google_oauth.py - AttributeError: module 'google_oau...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: Rewrite the module's first half**

The Google calls follow in Task 3; nothing calls the old ones any more (clarification 2).

**Replace the whole of `backend/google_oauth.py` with:**

````python
"""Google OAuth 2.0 for per-user Gmail sending (slice 5b spec, "google_oauth.py
after the refactor"; slice 5b-2).

Each user connects their own Google account and grants the `gmail.send` scope,
so the bulletin is emailed from their own mailbox. The refresh token is kept in
`gmail_tokens`, one row per user (user-scoped: one connection works in every
church the user belongs to). Google sends the user back to the frontend page
`/gmail/callback`, which posts the code and the state to `POST
/gmail-connection` (usecases.email).

This module holds:
- GoogleOAuthConfig: the client id, secret and redirect URI (from Railway's
  GOOGLE_* variables, read by api.settings, never by this module);
- the single-use CSRF states (`oauth_states`, 10 minutes) and the token store;
- build_auth_url, and (Task 3) the Google calls: the code exchange, the token
  refresh, the Gmail send and the revoke, each through integrations.http with
  its own timeout, each failure a GoogleOAuthError of one kind.

The Streamlit app's functions (the root-URL callback check, send_email, the
old exchange that stored the token itself, disconnect, is_configured) are
gone: production Streamlit is retired and nothing on `main` runs it (5b
amendment 2026-10-06, answer 4). Nothing here logs a code, a state, a token
or an address. No FastAPI, Starlette or Streamlit.
"""
from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

from sqlalchemy import delete
from sqlalchemy.orm import Session

from db import session_scope
from db.models import GmailToken, OAuthState

# openid and userinfo.email identify the Google account (the callback checks it is
# the signed-in user's); gmail.send lets the app send mail as them, nothing more.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.send",
]
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

AUTH_URI = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URI = "https://www.googleapis.com/oauth2/v2/userinfo"
GMAIL_SEND_URI = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
REVOKE_URI = "https://oauth2.googleapis.com/revoke"

# A single-use CSRF state lives this long.
STATE_TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class GoogleOAuthConfig:
    """The Google OAuth client (the one Streamlit used: same id and secret, so a
    stored refresh token keeps working) and this deployment's redirect URI."""

    client_id: str
    client_secret: str
    redirect_uri: str

    @property
    def configured(self) -> bool:
        """All three are set."""
        return bool(self.client_id and self.client_secret and self.redirect_uri)


@dataclass(frozen=True)
class GmailConnection:
    """A user's stored connection: the Google address mail is sent from, and the refresh token."""

    google_email: str
    refresh_token: str


# --------------------------------------------------------------------------- #
# The consent URL and the CSRF states
# --------------------------------------------------------------------------- #
def build_auth_url(config: GoogleOAuthConfig, state: str, *, login_hint: Optional[str] = None) -> str:
    """Google's consent screen for this app's scopes, returning to the
    configured redirect URI with `state`. Offline access and a consent prompt,
    so Google returns a refresh token; `login_hint` pre-selects the signed-in
    Google account."""
    params = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    if login_hint:
        params["login_hint"] = login_hint
    return f"{AUTH_URI}?{urlencode(params)}"


def purge_expired_states(session: Session) -> int:
    """Delete every expired state (abandoned connects); returns how many."""
    result = session.execute(delete(OAuthState).where(OAuthState.expires_at < datetime.now(timezone.utc)))
    return result.rowcount or 0


def create_state(user_id: uuid.UUID, *, session: Optional[Session] = None) -> str:
    """A new single-use state bound to the user (10 minutes); expired states
    are purged first. Returns the opaque token."""
    if session is None:
        with session_scope() as own:
            return create_state(user_id, session=own)
    purge_expired_states(session)
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    session.add(OAuthState(state=state, user_id=user_id, created_at=now, expires_at=now + STATE_TTL))
    session.flush()
    return state


def consume_state(state: str) -> Optional[uuid.UUID]:
    """The user the state was issued to, or None for a blank, unknown, used or
    expired state. Single use: a found row is deleted, valid or expired. Runs
    in its own committed transaction."""
    if not state:
        return None
    with session_scope() as session:
        row = session.get(OAuthState, state)
        if row is None:
            return None
        user_id = row.user_id
        expires_at = row.expires_at
        session.delete(row)
    if expires_at.tzinfo is None:            # SQLite hands back naive datetimes
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return user_id


# --------------------------------------------------------------------------- #
# The token store (gmail_tokens, one row per user)
# --------------------------------------------------------------------------- #
def get_connection(user_id: uuid.UUID, *, session: Optional[Session] = None) -> Optional[GmailConnection]:
    """The user's connection, or None when there is no row or its address is
    NULL or blank (the column is nullable; without an address nothing can be sent)."""
    if session is None:
        with session_scope() as own:
            return get_connection(user_id, session=own)
    row = session.get(GmailToken, user_id)
    if row is None or not row.refresh_token or not (row.google_email or "").strip():
        return None
    return GmailConnection(google_email=row.google_email, refresh_token=row.refresh_token)


def save_user_token(user_id: uuid.UUID, google_email: str, refresh_token: str, *,
                    session: Optional[Session] = None) -> None:
    """Store (or replace) the user's connection: one row per user."""
    if session is None:
        with session_scope() as own:
            return save_user_token(user_id, google_email, refresh_token, session=own)
    row = session.get(GmailToken, user_id)
    if row is None:
        session.add(GmailToken(user_id=user_id, google_email=google_email, refresh_token=refresh_token))
    else:
        row.google_email = google_email
        row.refresh_token = refresh_token
    session.flush()


def delete_connection(user_id: uuid.UUID, *, only_if_token: Optional[str] = None,
                      session: Optional[Session] = None) -> Optional[str]:
    """Delete the user's connection and return its refresh token, or None when
    no row matched. With `only_if_token`, only a row still holding that token is
    deleted: a connection made again since the token failed is kept."""
    if session is None:
        with session_scope() as own:
            return delete_connection(user_id, only_if_token=only_if_token, session=own)
    row = session.get(GmailToken, user_id)
    if row is None or (only_if_token is not None and row.refresh_token != only_if_token):
        return None
    token = row.refresh_token
    session.delete(row)
    session.flush()
    return token
````

- [ ] **Step 4: See them pass, the Streamlit tests, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_google_oauth.py backend/tests/test_no_streamlit_in_core.py streamlit_tests 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`51 passed in <t>s` (the 13 new tests, the import check's 3 and the 35 `streamlit_tests`, which never touched Gmail); `1663 passed, 26 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/google_oauth.py backend/tests/test_google_oauth.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Slice 5b-2: google_oauth's config, consent URL, states and token store" -m "GoogleOAuthConfig carries the client id, secret and redirect URI;
build_auth_url adds the signed-in account as login_hint;
create_state purges expired states; the store gains get_connection (none
for a row without an address), save_user_token and delete_connection
(only_if_token keeps a connection made again meanwhile), each with an
optional session. Streamlit's functions (the root callback check,
send_email, the exchange that stored the token, disconnect, os.getenv,
requests) are gone, with their three test files; every assertion about
kept code is ported to test_google_oauth.py." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

`git add` stages the three deletions made with `git rm` in Step 1 as well (they are already staged).

Expected counts after this task: backend `1663 passed, 26 skipped`; frontend `780 passed` in 94 files.

### Task 3: `google_oauth`: the Google calls (B "Rules"; clarifications 4 and 5)

**Files:**
- Create: `backend/tests/fake_google.py`
- Modify: `backend/tests/test_google_oauth.py`, `backend/google_oauth.py`

- [ ] **Step 1: Write the fake Google and the failing tests**

`fake_google.py` answers Google's four endpoints through an `httpx.MockTransport` installed with `set_http_for_tests` (the autouse `_fresh_http_client` fixture restores the real client after each test, and conftest's network guard stays on). Each endpoint answers with what its attribute holds; the default is a successful connect and send. Error bodies carry `SECRET-GOOGLE-TEXT`, which no test may ever see in a message or a response.

**Create `backend/tests/fake_google.py`:**

````python
"""A fake Google for the Gmail tests (slice 5b-2): an httpx.MockTransport behind
integrations.http.set_http_for_tests, so no test reaches the network (the
conftest guard stays on) and the autouse _fresh_http_client fixture puts the
real client back afterwards.

Each endpoint answers with what its attribute holds: an httpx.Response, an
exception to raise (an httpx error, as the transport would), or a function of
the request returning either. `requests` records every request in order;
`sent(...)` and friends filter it. The defaults are a successful connect and
send for owner@example.com.
"""
import base64
import json
from email import message_from_bytes, policy
from email.message import EmailMessage
from typing import Callable, Union
from urllib.parse import parse_qs

import httpx

import google_oauth
from integrations import http

Answer = Union[httpx.Response, Exception, Callable[[httpx.Request], Union[httpx.Response, Exception]]]

ACCESS_TOKEN = "access-token-1"
REFRESH_TOKEN = "refresh-token-1"
FRESH_ACCESS_TOKEN = "access-token-2"


def google_error(status: int, error: str) -> httpx.Response:
    """A token endpoint error ({"error": "invalid_grant", ...})."""
    return httpx.Response(status, json={"error": error, "error_description": "SECRET-GOOGLE-TEXT"})


# The Gmail API's error status for each HTTP status the tests use.
GMAIL_STATUS = {400: "INVALID_ARGUMENT", 401: "UNAUTHENTICATED", 403: "PERMISSION_DENIED", 429: "RESOURCE_EXHAUSTED"}


def gmail_error(status: int, reason: str, api_status: str | None = None) -> httpx.Response:
    """A Gmail API error with one reason (and its status name, by default the usual one for `status`)."""
    return httpx.Response(status, json={"error": {"code": status, "message": "SECRET-GOOGLE-TEXT",
                                                  "errors": [{"reason": reason, "message": "SECRET-GOOGLE-TEXT"}],
                                                  "status": api_status or GMAIL_STATUS.get(status, "UNKNOWN")}})


class FakeGoogle:
    def __init__(self, email: str = "owner@example.com"):
        self.exchange: Answer = httpx.Response(200, json={
            "access_token": ACCESS_TOKEN, "refresh_token": REFRESH_TOKEN, "expires_in": 3599,
            "scope": " ".join(google_oauth.SCOPES), "token_type": "Bearer"})
        self.userinfo: Answer = httpx.Response(200, json={"email": email, "verified_email": True})
        self.refresh: Answer = httpx.Response(200, json={"access_token": FRESH_ACCESS_TOKEN, "expires_in": 3599})
        self.send: Answer = httpx.Response(200, json={"id": "msg-1", "threadId": "thread-1", "labelIds": ["SENT"]})
        self.revoke: Answer = httpx.Response(200)
        self.requests: list[httpx.Request] = []

    def install(self) -> "FakeGoogle":
        http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(self._handle)))
        return self

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url).split("?")[0]
        if url == google_oauth.TOKEN_URI:
            form = parse_qs(request.content.decode())
            answer = self.exchange if form.get("grant_type") == ["authorization_code"] else self.refresh
        elif url == google_oauth.USERINFO_URI:
            answer = self.userinfo
        elif url == google_oauth.GMAIL_SEND_URI:
            answer = self.send
        elif url == google_oauth.REVOKE_URI:
            answer = self.revoke
        else:
            raise AssertionError(f"unexpected request to {url}")
        if callable(answer) and not isinstance(answer, (httpx.Response, Exception)):
            answer = answer(request)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def calls(self, url: str, grant_type: str | None = None) -> list[httpx.Request]:
        found = [r for r in self.requests if str(r.url).split("?")[0] == url]
        if grant_type is not None:
            found = [r for r in found if parse_qs(r.content.decode()).get("grant_type") == [grant_type]]
        return found

    def form(self, request: httpx.Request) -> dict[str, str]:
        return {key: values[0] for key, values in parse_qs(request.content.decode()).items()}

    def sent(self) -> list[EmailMessage]:
        """Every message the Gmail send endpoint received, parsed."""
        messages = []
        for request in self.calls(google_oauth.GMAIL_SEND_URI):
            raw = base64.urlsafe_b64decode(json.loads(request.content)["raw"])
            messages.append(message_from_bytes(raw, policy=policy.default))
        return messages

````

**In `backend/tests/test_google_oauth.py`, replace:**

````python
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

````

**with:**

````python
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
````

**In `backend/tests/test_google_oauth.py`, replace:**

````python
from db.models import GmailToken, OAuthState
````

**with:**

````python
from db.models import GmailToken, OAuthState
from tests.fake_google import ACCESS_TOKEN, FRESH_ACCESS_TOKEN, REFRESH_TOKEN, FakeGoogle, gmail_error, google_error
````

**Append to `backend/tests/test_google_oauth.py`:**

````python


# --- Task 3: the Google calls, against tests.fake_google (no network) -----------------------------

Kind = google_oauth.GoogleErrorKind


def _kind(call) -> google_oauth.GoogleErrorKind:
    with pytest.raises(google_oauth.GoogleOAuthError) as failed:
        call()
    return failed.value.kind


def _exchange(email="owner@example.com"):
    return google_oauth.exchange_code(CONFIG, "auth-code", expected_email=email)


def test_exchange_code_returns_the_grant_with_googles_spelling_and_stores_nothing(tmp_db):
    google = FakeGoogle(email="Owner@Example.com").install()
    grant = _exchange("owner@example.com")
    assert grant == google_oauth.GmailGrant("Owner@Example.com", REFRESH_TOKEN, frozenset(google_oauth.SCOPES))
    token_request, userinfo_request = google.requests
    assert google.form(token_request) == {"code": "auth-code", "client_id": "client-123", "client_secret": "secret-456",
                                          "redirect_uri": "https://app.example.org/gmail/callback",
                                          "grant_type": "authorization_code"}
    assert token_request.extensions["timeout"]["read"] == 15.0
    assert userinfo_request.headers["Authorization"] == f"Bearer {ACCESS_TOKEN}"
    assert userinfo_request.extensions["timeout"] == {"connect": 5.0, "read": 15.0, "write": 15.0, "pool": 15.0}
    with session_scope() as s:
        assert s.query(GmailToken).count() == 0


def test_exchange_code_without_a_refresh_token_or_a_scope_field(tmp_db):
    google = FakeGoogle().install()
    google.exchange = httpx.Response(200, json={"access_token": ACCESS_TOKEN})       # no scope: as requested
    assert _exchange() == google_oauth.GmailGrant("owner@example.com", None, frozenset(google_oauth.SCOPES))


@pytest.mark.parametrize("answer, kind", [
    (google_error(400, "invalid_grant"), Kind.INVALID_GRANT),
    (google_error(401, "invalid_client"), Kind.CLIENT_MISCONFIGURED),
    (google_error(400, "redirect_uri_mismatch"), Kind.CLIENT_MISCONFIGURED),
    (google_error(400, "invalid_request"), Kind.UPSTREAM),
    (httpx.Response(500, text="oops"), Kind.UPSTREAM),
    (httpx.ReadTimeout("slow"), Kind.TIMEOUT),
    (httpx.ConnectError("down"), Kind.UPSTREAM),
    (httpx.Response(200, json={"refresh_token": REFRESH_TOKEN}), Kind.INCOMPLETE_RESPONSE),
    (httpx.Response(200, text="not json"), Kind.INCOMPLETE_RESPONSE),
    (httpx.Response(200, json={"access_token": ACCESS_TOKEN, "scope": "openid email"}), Kind.SCOPE_MISSING),
    (httpx.Response(200, json={"access_token": ACCESS_TOKEN, "scope": ["openid"]}), Kind.INCOMPLETE_RESPONSE),
])
def test_exchange_code_failures(tmp_db, answer, kind):
    google = FakeGoogle().install()
    google.exchange = answer
    assert _kind(_exchange) == kind


@pytest.mark.parametrize("answer, kind", [
    (httpx.Response(401, json={"error": {"code": 401}}), Kind.NO_EMAIL),
    (httpx.Response(200, json={"verified_email": False}), Kind.NO_EMAIL),
    (httpx.Response(503, text="later"), Kind.UPSTREAM),
    (httpx.ReadTimeout("slow"), Kind.TIMEOUT),
])
def test_exchange_code_userinfo_failures(tmp_db, answer, kind):
    google = FakeGoogle().install()
    google.userinfo = answer
    assert _kind(_exchange) == kind


def test_exchange_code_refuses_another_google_account(tmp_db):
    FakeGoogle(email="attacker@example.com").install()
    assert _kind(_exchange) == Kind.EMAIL_MISMATCH


def test_exchange_code_opens_no_database_session(tmp_db, monkeypatch):
    FakeGoogle().install()
    monkeypatch.setattr(google_oauth, "session_scope", lambda: pytest.fail("exchange_code opened a session"))
    assert _exchange().google_email == "owner@example.com"


def test_refresh_access_token(tmp_db):
    google = FakeGoogle().install()
    assert google_oauth.refresh_access_token(CONFIG, REFRESH_TOKEN) == FRESH_ACCESS_TOKEN
    assert google.form(google.requests[0]) == {"client_id": "client-123", "client_secret": "secret-456",
                                               "refresh_token": REFRESH_TOKEN, "grant_type": "refresh_token"}
    for answer, kind in ((google_error(400, "invalid_grant"), Kind.INVALID_GRANT),
                         (google_error(401, "unauthorized_client"), Kind.CLIENT_MISCONFIGURED),
                         (httpx.Response(502), Kind.UPSTREAM),
                         (httpx.Response(200, json={}), Kind.INCOMPLETE_RESPONSE),
                         (httpx.ReadTimeout("slow"), Kind.TIMEOUT),
                         (httpx.ConnectTimeout("slow"), Kind.TIMEOUT)):
        google.refresh = answer
        assert _kind(lambda: google_oauth.refresh_access_token(CONFIG, REFRESH_TOKEN)) == kind, answer


def test_send_raw_message_posts_the_message_with_the_access_token():
    google = FakeGoogle().install()
    google_oauth.send_raw_message(FRESH_ACCESS_TOKEN, b"From: a@example.org\r\nTo: b@example.org\r\n\r\nHi\r\n")
    (request,) = google.requests
    assert request.headers["Authorization"] == f"Bearer {FRESH_ACCESS_TOKEN}"
    assert request.extensions["timeout"] == {"connect": 5.0, "read": 30.0, "write": 30.0, "pool": 30.0}
    assert google.sent()[0]["To"] == "b@example.org"


@pytest.mark.parametrize("answer, kind, status", [
    (gmail_error(403, "insufficientPermissions"), Kind.INSUFFICIENT_SCOPE, 403),
    (httpx.Response(403, json={"error": {"code": 403, "status": "PERMISSION_DENIED",
                                         "details": [{"reason": "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}]}}),
     Kind.INSUFFICIENT_SCOPE, 403),
    (gmail_error(429, "rateLimitExceeded"), Kind.SEND_LIMIT, 429),
    (gmail_error(403, "dailyLimitExceeded"), Kind.SEND_LIMIT, 403),
    (gmail_error(400, "invalidArgument"), Kind.SEND_REJECTED, 400),
    (gmail_error(401, "authError"), Kind.ACCOUNT_REFUSED, 401),
    (gmail_error(400, "failedPrecondition", "FAILED_PRECONDITION"), Kind.ACCOUNT_REFUSED, 400),
    (httpx.ConnectError("down"), Kind.UPSTREAM, None),
    (httpx.ConnectTimeout("slow"), Kind.UPSTREAM, None),
    (httpx.PoolTimeout("busy"), Kind.UPSTREAM, None),
    (httpx.Response(503, text="later"), Kind.SEND_UNCONFIRMED, 503),
    (httpx.ReadTimeout("slow"), Kind.SEND_UNCONFIRMED, None),
    (httpx.WriteTimeout("slow"), Kind.SEND_UNCONFIRMED, None),
    (httpx.ReadError("reset"), Kind.SEND_UNCONFIRMED, None),
    (httpx.RemoteProtocolError("closed"), Kind.SEND_UNCONFIRMED, None),
])
def test_send_raw_message_failures(answer, kind, status):
    google = FakeGoogle().install()
    google.send = answer
    with pytest.raises(google_oauth.GoogleOAuthError) as failed:
        google_oauth.send_raw_message(FRESH_ACCESS_TOKEN, b"Subject: x\r\n\r\nx\r\n")
    assert (failed.value.kind, failed.value.status) == (kind, status)
    assert "SECRET-GOOGLE-TEXT" not in str(failed.value)
    if isinstance(answer, httpx.Response) and answer.headers["Content-Type"] == "application/json":
        error = json.loads(answer.content)["error"]
        reasons = [item["reason"] for item in error.get("errors", []) + error.get("details", [])]
        assert failed.value.google_error == reasons[0]                     # logged by the caller: a reason, never text


def test_revoke_token_is_best_effort():
    google = FakeGoogle().install()
    assert google_oauth.revoke_token(REFRESH_TOKEN) is True
    assert google.form(google.requests[0]) == {"token": REFRESH_TOKEN}
    assert google.requests[0].extensions["timeout"]["read"] == 5.0
    for answer in (httpx.Response(400, json={"error": "invalid_token"}), httpx.ReadTimeout("slow"),
                   httpx.ConnectError("down")):
        google.revoke = answer
        assert google_oauth.revoke_token(REFRESH_TOKEN) is False
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_google_oauth.py 2>&1 | tail -3`
**Expected** (`GoogleErrorKind`, `exchange_code` and the rest do not exist yet: the module-level `Kind = google_oauth.GoogleErrorKind` is an `AttributeError` at collection):
```
ERROR backend/tests/test_google_oauth.py - AttributeError: module 'google_oau...
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: Add the calls**

**In `backend/google_oauth.py`, replace:**

````python

import secrets
````

**with:**

````python

import base64
import secrets
````

**In `backend/google_oauth.py`, replace:**

````python
from typing import Optional
from urllib.parse import urlencode

````

**with:**

````python
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
````

**In `backend/google_oauth.py`, replace:**

````python
from db.models import GmailToken, OAuthState
````

**with:**

````python
from db.models import GmailToken, OAuthState
from integrations import http
````

**Append to `backend/google_oauth.py`:**

````python


# --------------------------------------------------------------------------- #
# The Google calls (Task 3)
# --------------------------------------------------------------------------- #
# F §1.8. httpx applies each value per phase, not to the whole call: 5 s to connect, then up to 15 s
# (a token, userinfo or refresh call), 30 s (the send) or 5 s (the revoke) for each wait on a write, a
# read or the pool. A slow but steady answer can therefore take longer than the number; the browser's own
# timeout (lib/api/timeouts.ts) is the overall deadline, and a send it stops waiting for is treated there
# as possibly sent.
TOKEN_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
SEND_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
REVOKE_TIMEOUT = httpx.Timeout(5.0, connect=5.0)

_CLIENT_ERRORS = {"invalid_client", "unauthorized_client", "redirect_uri_mismatch"}
_SCOPE_ERRORS = {"insufficientPermissions", "ACCESS_TOKEN_SCOPE_INSUFFICIENT"}
_LIMIT_ERRORS = {"rateLimitExceeded", "userRateLimitExceeded", "dailyLimitExceeded"}
# Gmail refuses the account itself (a Google account without Gmail, Gmail turned off by a Workspace admin).
_ACCOUNT_ERRORS = {"failedPrecondition", "FAILED_PRECONDITION"}
# A send that failed before its request was written cannot have reached Gmail.
_NOT_SENT = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.UnsupportedProtocol)


class GoogleErrorKind(str, Enum):
    INVALID_GRANT = "invalid_grant"                 # the code or the refresh token is no longer valid
    CLIENT_MISCONFIGURED = "client_misconfigured"   # our client id, secret or redirect URI
    INCOMPLETE_RESPONSE = "incomplete_response"     # no access token, or an unreadable answer
    SCOPE_MISSING = "scope_missing"                 # consent given without "send email on your behalf"
    NO_EMAIL = "no_email"                           # userinfo had no address
    EMAIL_MISMATCH = "email_mismatch"               # a Google account other than the signed-in one
    INSUFFICIENT_SCOPE = "insufficient_scope"       # Gmail: the grant no longer allows sending
    SEND_LIMIT = "send_limit"                       # Gmail: a rate or daily limit
    ACCOUNT_REFUSED = "account_refused"             # Gmail: a 401 not about the scope, or a failed precondition
    SEND_REJECTED = "send_rejected"                 # Gmail: any other 4xx; nothing was sent
    UPSTREAM = "upstream"                           # a 5xx or a network error where nothing changed at Google
    TIMEOUT = "timeout"                             # no answer in time where nothing changed at Google
    SEND_UNCONFIRMED = "send_unconfirmed"           # the send was written but not confirmed: it may have gone out


class GoogleOAuthError(Exception):
    """A Google call failed in a way the caller maps to a message. `status` is
    Google's HTTP status (None for a network error); `google_error` is Google's
    error code (for example "invalid_client"), for the logs only: never shown."""

    def __init__(self, kind: GoogleErrorKind, *, status: Optional[int] = None,
                 google_error: Optional[str] = None):
        super().__init__(kind.value)
        self.kind = kind
        self.status = status
        self.google_error = google_error


@dataclass(frozen=True)
class GmailGrant:
    """What a successful code exchange gives: the Google address (as Google
    spells it), the refresh token (None when Google sent none) and the granted scopes."""

    google_email: str
    refresh_token: Optional[str]
    scopes: frozenset[str]


def _error_names(resp: httpx.Response) -> set[str]:
    """Google's error names in a response body: the OAuth "error" string, or the
    Gmail API's error status and each reason. Empty for a body that is not JSON."""
    try:
        body = resp.json()
    except ValueError:
        return set()
    if not isinstance(body, dict):
        return set()
    error = body.get("error")
    if isinstance(error, str):
        return {error}
    if not isinstance(error, dict):
        return set()
    names = {error["status"]} if isinstance(error.get("status"), str) else set()
    for item in [*(error.get("errors") or []), *(error.get("details") or [])]:
        if isinstance(item, dict) and isinstance(item.get("reason"), str):
            names.add(item["reason"])
    return names


def _failure(resp: httpx.Response, phase: str) -> GoogleOAuthError:
    """The error for a non-2xx answer. `phase` is "token", "userinfo",
    "refresh" or "send" (5b spec, the one classification helper)."""
    names = _error_names(resp)
    named = next(iter(sorted(names, key=lambda name: (name.isupper(), name))), None)   # a reason before a STATUS
    status = resp.status_code
    if phase == "send":
        if status == 403 and names & _SCOPE_ERRORS:
            return GoogleOAuthError(GoogleErrorKind.INSUFFICIENT_SCOPE, status=status, google_error=named)
        if status == 429 or (status == 403 and names & _LIMIT_ERRORS):
            return GoogleOAuthError(GoogleErrorKind.SEND_LIMIT, status=status, google_error=named)
        if status == 401 or (status == 400 and names & _ACCOUNT_ERRORS):
            return GoogleOAuthError(GoogleErrorKind.ACCOUNT_REFUSED, status=status, google_error=named)
        if status >= 500:
            return GoogleOAuthError(GoogleErrorKind.SEND_UNCONFIRMED, status=status, google_error=named)
        return GoogleOAuthError(GoogleErrorKind.SEND_REJECTED, status=status, google_error=named)
    if phase in ("token", "refresh") and status in (400, 401):
        if "invalid_grant" in names:
            return GoogleOAuthError(GoogleErrorKind.INVALID_GRANT, status=status, google_error="invalid_grant")
        client = names & _CLIENT_ERRORS
        if client:
            return GoogleOAuthError(GoogleErrorKind.CLIENT_MISCONFIGURED, status=status,
                                    google_error=sorted(client)[0])
    if phase == "userinfo" and status < 500:
        return GoogleOAuthError(GoogleErrorKind.NO_EMAIL, status=status, google_error=named)
    return GoogleOAuthError(GoogleErrorKind.UPSTREAM, status=status, google_error=named)


def _transport_failure(exc: httpx.HTTPError, phase: str) -> GoogleOAuthError:
    """The error for a request that got no answer. A send that was written may
    have gone out (SEND_UNCONFIRMED); any other call changed nothing at Google."""
    if phase == "send":
        return GoogleOAuthError(GoogleErrorKind.UPSTREAM if isinstance(exc, _NOT_SENT)
                                else GoogleErrorKind.SEND_UNCONFIRMED)
    return GoogleOAuthError(GoogleErrorKind.TIMEOUT if isinstance(exc, httpx.TimeoutException)
                            else GoogleErrorKind.UPSTREAM)


def _json(resp: httpx.Response) -> dict[str, Any]:
    try:
        body = resp.json()
    except ValueError:
        raise GoogleOAuthError(GoogleErrorKind.INCOMPLETE_RESPONSE, status=resp.status_code) from None
    if not isinstance(body, dict):
        raise GoogleOAuthError(GoogleErrorKind.INCOMPLETE_RESPONSE, status=resp.status_code)
    return body


def _token_request(form: dict[str, str], phase: str) -> dict[str, Any]:
    try:
        resp = http.post(TOKEN_URI, data=form, timeout=TOKEN_TIMEOUT)
    except httpx.HTTPError as exc:
        raise _transport_failure(exc, phase) from None
    if not resp.is_success:
        raise _failure(resp, phase)
    return _json(resp)


def _access_token(payload: dict[str, Any]) -> str:
    token = payload.get("access_token")
    if not isinstance(token, str) or not token:
        raise GoogleOAuthError(GoogleErrorKind.INCOMPLETE_RESPONSE)
    return token


def _granted_scopes(payload: dict[str, Any]) -> frozenset[str]:
    """The granted scopes. No `scope` (or a blank one) means exactly the
    requested ones (RFC 6749 §5.1); one without gmail.send is SCOPE_MISSING."""
    scope = payload.get("scope")
    if scope is None or scope == "":
        return frozenset(SCOPES)
    if not isinstance(scope, str):
        raise GoogleOAuthError(GoogleErrorKind.INCOMPLETE_RESPONSE)
    granted = frozenset(scope.split())
    if GMAIL_SEND_SCOPE not in granted:
        raise GoogleOAuthError(GoogleErrorKind.SCOPE_MISSING)
    return granted


def _fetch_userinfo_email(access_token: str) -> str:
    try:
        resp = http.get(USERINFO_URI, headers={"Authorization": f"Bearer {access_token}"},
                        read_timeout=TOKEN_TIMEOUT.read)
    except httpx.HTTPError as exc:
        raise _transport_failure(exc, "userinfo") from None
    if not resp.is_success:
        raise _failure(resp, "userinfo")
    try:
        email = resp.json().get("email")
    except (ValueError, AttributeError):
        email = None
    if not isinstance(email, str) or not email.strip():
        raise GoogleOAuthError(GoogleErrorKind.NO_EMAIL)
    return email.strip()


def exchange_code(config: GoogleOAuthConfig, code: str, *, expected_email: str) -> GmailGrant:
    """Exchange the consent screen's code (15 s), check the granted scopes, read
    the Google address (15 s) and compare it, ignoring case, with the signed-in
    user's. Stores nothing (the caller does, in its own transaction)."""
    payload = _token_request({
        "code": code,
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "redirect_uri": config.redirect_uri,
        "grant_type": "authorization_code",
    }, "token")
    access_token = _access_token(payload)
    scopes = _granted_scopes(payload)
    google_email = _fetch_userinfo_email(access_token)
    if google_email.lower() != expected_email.strip().lower():
        raise GoogleOAuthError(GoogleErrorKind.EMAIL_MISMATCH)
    refresh = payload.get("refresh_token")
    return GmailGrant(google_email=google_email, refresh_token=refresh if isinstance(refresh, str) and refresh else None,
                      scopes=scopes)


def refresh_access_token(config: GoogleOAuthConfig, refresh_token: str) -> str:
    """A fresh access token for the stored refresh token (15 s)."""
    payload = _token_request({
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }, "refresh")
    return _access_token(payload)


def send_raw_message(access_token: str, raw: bytes) -> None:
    """Send one MIME message (its bytes) through the Gmail API's JSON endpoint
    (SEND_TIMEOUT, per phase; the caller keeps the message small enough for it).
    A failure before the request was written is UPSTREAM (nothing was sent); no
    answer after it, or a Gmail 5xx, is SEND_UNCONFIRMED (it may have been sent)."""
    body = {"raw": base64.urlsafe_b64encode(raw).decode("ascii")}
    try:
        resp = http.post(GMAIL_SEND_URI, json=body, headers={"Authorization": f"Bearer {access_token}"},
                         timeout=SEND_TIMEOUT)
    except httpx.HTTPError as exc:
        raise _transport_failure(exc, "send") from None
    if not resp.is_success:
        raise _failure(resp, "send")


def revoke_token(token: str) -> bool:
    """Ask Google to revoke the grant (5 s), best effort: True when Google said
    yes, False on any failure. Never raises."""
    try:
        resp = http.post(REVOKE_URI, data={"token": token}, timeout=REVOKE_TIMEOUT)
    except httpx.HTTPError:
        return False
    return resp.is_success
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_google_oauth.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`50 passed in <t>s`; `1700 passed, 26 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/google_oauth.py backend/tests/fake_google.py backend/tests/test_google_oauth.py
git commit -q -m "Slice 5b-2: google_oauth's code exchange, refresh, Gmail send and revoke" -m "exchange_code checks the granted scopes and the Google address (ignoring
case) and stores nothing; refresh_access_token and send_raw_message go
through integrations.http with 15 s and 30 s; revoke_token is best
effort. Every failure is one GoogleErrorKind: a send that failed before
its request was written is UPSTREAM (nothing sent), a Gmail 5xx or no
answer after it was written is SEND_UNCONFIRMED (it may have gone out);
a 401 or a failedPrecondition is ACCOUNT_REFUSED. The timeouts are per
phase. Google's own text never leaves the module; its reason name is
kept for the caller's log. tests/fake_google.py is the
MockTransport stand-in." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1700 passed, 26 skipped`; frontend `780 passed` in 94 files.

### Task 4: The Google settings and the startup lines (B "Configuration and startup checks"; clarification 3)

**Files:**
- Modify: `backend/tests/test_startup.py`, `backend/google_oauth.py`, `backend/api/settings.py`, `backend/api/startup.py`, `backend/api/main.py`, `backend/.env.example`

- [ ] **Step 1: Write the failing tests**

The `api_env` fixture also clears the developer's `GOOGLE_*`, so these tests read only what they set.

**In `backend/tests/test_startup.py`, replace:**

````python
from api.startup import check_app_env, describe_database
from db.engine import _make_engine
from db.schema_check import RevisionState
````

**with:**

````python
from api.startup import check_app_env, describe_database, gmail_config_problems
from db.engine import _make_engine
from db.schema_check import RevisionState
from google_oauth import GoogleOAuthConfig
````

**In `backend/tests/test_startup.py`, replace:**

````python
    """No APP_ENV / CORS_ORIGINS from the developer's shell; get_settings() re-reads the env."""
    for name in ("APP_ENV", "CORS_ORIGINS"):
````

**with:**

````python
    """No APP_ENV, CORS_ORIGINS or GOOGLE_* from the developer's shell; get_settings() re-reads the env."""
    for name in ("APP_ENV", "CORS_ORIGINS", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_REDIRECT_URI"):
````

**Append to `backend/tests/test_startup.py`:**

````python


# --- slice 5b-2: the Gmail configuration (5b spec, "Configuration and startup checks") ------------

SITE = "https://worship-service-builder.vercel.app"
CALLBACK = f"{SITE}/gmail/callback"


def _gmail(client_id="client-123", secret="secret-456", redirect=CALLBACK, origins=(SITE,), env="production"):
    return settings_mod.Settings(supabase_url="", cors_origins=origins, app_env=env, google_client_id=client_id,
                                 google_client_secret=secret, google_oauth_redirect_uri=redirect)


@pytest.mark.parametrize("settings, problems", [
    (_gmail(), []),
    (_gmail(client_id="", secret="", redirect=""), []),
    (_gmail(secret=""), ["Gmail sending is disabled until GOOGLE_CLIENT_SECRET is set."]),
    (_gmail(client_id="", redirect=""),
     ["Gmail sending is disabled until GOOGLE_CLIENT_ID and GOOGLE_OAUTH_REDIRECT_URI are set."]),
    (_gmail(redirect="https://liturgy.streamlit.app/", origins=(SITE,)),
     ["GOOGLE_OAUTH_REDIRECT_URI should be the site's address followed by /gmail/callback.",
      "GOOGLE_OAUTH_REDIRECT_URI's site is not one of CORS_ORIGINS."]),
    (_gmail(redirect="http://localhost:3000/gmail/callback", origins=("http://localhost:3000",)),
     ["GOOGLE_OAUTH_REDIRECT_URI must start with https:// in production."]),
    (_gmail(redirect="http://localhost:3000/gmail/callback", origins=("http://localhost:3000",), env="development"),
     []),
], ids=["configured", "not-configured", "one-missing", "two-missing", "streamlit-root", "http-in-production",
        "http-in-development"])
def test_gmail_configuration_problems(settings, problems):
    assert gmail_config_problems(settings) == problems


def test_the_google_config_comes_from_the_environment_and_never_shows_the_secret(api_env):
    api_env.setenv("GOOGLE_CLIENT_ID", " client-123 ")
    api_env.setenv("GOOGLE_CLIENT_SECRET", " secret-456\n")
    api_env.setenv("GOOGLE_OAUTH_REDIRECT_URI", f" {CALLBACK} ")
    settings = settings_mod.get_settings()
    assert settings.google_oauth == GoogleOAuthConfig("client-123", "secret-456", CALLBACK)
    assert "secret-456" not in repr(settings) and "secret-456" not in repr(settings.google_oauth)


@pytest.mark.parametrize("secret, lines", [
    ("secret-456", [(logging.INFO, "Gmail: configured")]),
    ("", [(logging.WARNING, "Gmail: Gmail sending is disabled until GOOGLE_CLIENT_SECRET is set.")]),
], ids=["configured", "missing-secret"])
def test_startup_logs_the_gmail_configuration(api_env, tmp_db, caplog, secret, lines):
    api_env.setenv("CORS_ORIGINS", "http://localhost:3000")
    api_env.setenv("GOOGLE_CLIENT_ID", "client-123")
    api_env.setenv("GOOGLE_CLIENT_SECRET", secret)
    api_env.setenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:3000/gmail/callback")
    with caplog.at_level(logging.INFO):
        _start(api.main.create_app())
    assert [(r.levelno, r.getMessage()) for r in caplog.records if r.getMessage().startswith("Gmail: ")] == lines
    assert all("secret-456" not in r.getMessage() and "client-123" not in r.getMessage() for r in caplog.records)
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_startup.py 2>&1 | tail -3`
**Expected** (`gmail_config_problems` does not exist yet: an `ImportError` above these lines):
```
ERROR backend/tests/test_startup.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: Read the variables, check them at startup**

**In `backend/google_oauth.py`, replace:**

````python
from dataclasses import dataclass
````

**with:**

````python
from dataclasses import dataclass, field
````

**In `backend/google_oauth.py`, replace:**

````python
    client_secret: str
````

**with:**

````python
    client_secret: str = field(repr=False)
````

**In `backend/api/settings.py`, replace:**

````python
from dataclasses import dataclass
from functools import lru_cache
````

**with:**

````python
from dataclasses import dataclass, field
from functools import lru_cache

from google_oauth import GoogleOAuthConfig
````

**In `backend/api/settings.py`, replace:**

````python
    log_level: str = "INFO"                # LOG_LEVEL; api.logging_config validates it
````

**with:**

````python
    log_level: str = "INFO"                # LOG_LEVEL; api.logging_config validates it
    # Slice 5b-2: the Google OAuth client Streamlit used (same id and secret) and this
    # deployment's /gmail/callback page; api.startup.log_gmail_state says what is missing.
    google_client_id: str = ""
    google_client_secret: str = field(default="", repr=False)
    google_oauth_redirect_uri: str = ""
````

**In `backend/api/settings.py`, replace:**

````python
        return self.app_env == "production"
````

**with:**

````python
        return self.app_env == "production"

    @property
    def google_oauth(self) -> GoogleOAuthConfig:
        return GoogleOAuthConfig(self.google_client_id, self.google_client_secret, self.google_oauth_redirect_uri)
````

**In `backend/api/settings.py`, replace:**

````python
        log_level=os.environ.get("LOG_LEVEL", "").strip() or "INFO",
````

**with:**

````python
        log_level=os.environ.get("LOG_LEVEL", "").strip() or "INFO",
        google_client_id=os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
        google_client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", "").strip(),
        google_oauth_redirect_uri=os.environ.get("GOOGLE_OAUTH_REDIRECT_URI", "").strip(),
````

**In `backend/api/startup.py`, replace:**

````python
  file on Railway), and log an ERROR when CORS_ORIGINS lists only localhost.
````

**with:**

````python
  file on Railway), and log an ERROR when CORS_ORIGINS lists only localhost.
- gmail_config_problems and log_gmail_state (slice 5b-2; 5b spec,
  "Configuration and startup checks"): one "Gmail: configured" or "Gmail:
  not configured" line, or a WARNING for each problem with the GOOGLE_*
  variables. Never refuses to start, and never logs a value.
````

**In `backend/api/startup.py`, replace:**

````python
APP_ENVS = ("development", "production")
````

**with:**

````python
APP_ENVS = ("development", "production")
GMAIL_VARIABLES = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_OAUTH_REDIRECT_URI")
GMAIL_CALLBACK_PATH = "/gmail/callback"
````

**Append to `backend/api/startup.py`:**

````python


def gmail_config_problems(settings: Settings) -> list[str]:
    """What is wrong with the GOOGLE_* variables, as log lines (none when all
    three are set and right, or none is set: Gmail is then simply off)."""
    values = (settings.google_client_id, settings.google_client_secret, settings.google_oauth_redirect_uri)
    missing = [name for name, value in zip(GMAIL_VARIABLES, values) if not value]
    if len(missing) == len(GMAIL_VARIABLES):
        return []
    problems = []
    if missing:
        names = missing[0] if len(missing) == 1 else f"{', '.join(missing[:-1])} and {missing[-1]}"
        problems.append(f"Gmail sending is disabled until {names} {'is' if len(missing) == 1 else 'are'} set.")
    uri = settings.google_oauth_redirect_uri
    if uri:
        parts = urlsplit(uri)
        if parts.path != GMAIL_CALLBACK_PATH:
            problems.append(f"GOOGLE_OAUTH_REDIRECT_URI should be the site's address followed by {GMAIL_CALLBACK_PATH}.")
        if f"{parts.scheme}://{parts.netloc}" not in settings.cors_origins:
            problems.append("GOOGLE_OAUTH_REDIRECT_URI's site is not one of CORS_ORIGINS.")
        if settings.is_production and parts.scheme != "https":
            problems.append("GOOGLE_OAUTH_REDIRECT_URI must start with https:// in production.")
    return problems


def log_gmail_state(settings: Settings) -> None:
    problems = gmail_config_problems(settings)
    for problem in problems:
        logger.warning("Gmail: %s", problem)
    if not problems:
        logger.info("Gmail: %s", "configured" if settings.google_oauth.configured else "not configured")
````

**In `backend/api/main.py`, replace:**

````python
from api.startup import check_app_env, describe_database, enforce_production_guards
````

**with:**

````python
from api.startup import check_app_env, describe_database, enforce_production_guards, log_gmail_state
````

**In `backend/api/main.py`, replace:**

````python
    openai_client.log_startup_state()                       # one "AI: ..." line, never the key
````

**with:**

````python
    openai_client.log_startup_state()                       # one "AI: ..." line, never the key
    log_gmail_state(settings)                               # "Gmail: ..." lines, never a value (slice 5b-2)
````

**In `backend/.env.example`, replace:**

````bash
# Carried over for a later slice (Gmail sending).
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=
````

**with:**

````bash
# Gmail sending (slice 5b-2): the SAME Google OAuth client id and secret Streamlit used,
# so a Gmail connection made there keeps working. The redirect URI is the frontend's
# /gmail/callback page (production: https://worship-service-builder.vercel.app/gmail/callback),
# and must also be listed on that client in Google Cloud Console. All three empty: Gmail is off.
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:3000/gmail/callback
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_startup.py backend/tests/test_google_oauth.py backend/tests/test_docs.py backend/tests/test_foundation_setup.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`95 passed in <t>s`; `1710 passed, 26 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/google_oauth.py backend/api/settings.py backend/api/startup.py backend/api/main.py backend/.env.example backend/tests/test_startup.py
git commit -q -m "Slice 5b-2: the Google client's settings and the Gmail startup lines" -m "api/settings.py reads GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and
GOOGLE_OAUTH_REDIRECT_URI into Settings.google_oauth, the secret left out
of repr. The startup logs \"Gmail: configured\" or \"Gmail: not
configured\", or a warning for each problem: a missing variable, a
redirect URI that is not the site's /gmail/callback, a site not in
CORS_ORIGINS, plain http in production. It never refuses to start and
never logs a value. .env.example describes the three." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1710 passed, 26 skipped`; frontend `780 passed` in 94 files.

### Task 5: The Gmail connection usecases (B "usecases/email.py", "Errors: POST /gmail-connection"; clarification 6)

**Files:**
- Create: `backend/tests/test_usecase_email.py`, `backend/usecases/email.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

- [ ] **Step 1: Write the failing tests**

Every row of B's table for `POST /gmail-connection` has a case, each storing nothing; the state is used up before Google is called (CSRF first), so it is used up even when the exchange fails; a failed revoke still disconnects; the logs carry no code, state, token or address.

**Create `backend/tests/test_usecase_email.py`:**

````python
"""usecases.email (slice 5b spec, Testing "test_usecase_email.py"; slice 5b-2):
the Gmail connection (status, start, finish, disconnect) against
tests.fake_google; Task 12 adds the bulletin send. No network."""
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import google_oauth
from db import session_scope
from db.models import GmailToken, OAuthState
from domain_errors import NotConfigured, Rejected, UpstreamError, UpstreamTimeout
from tests.fake_google import REFRESH_TOKEN, FakeGoogle, google_error
from usecases import email

CONFIG = google_oauth.GoogleOAuthConfig("client-123", "secret-456", "https://app.example.org/gmail/callback")
UNCONFIGURED = google_oauth.GoogleOAuthConfig("", "", "")
OWNER = "owner@example.com"


@pytest.fixture
def owner(tmp_db, make_user):
    return make_user(email=OWNER)


def _rows() -> list[tuple]:
    with session_scope() as s:
        return [(r.user_id, r.google_email, r.refresh_token) for r in s.query(GmailToken).all()]


def _finish(user, state=None, code="auth-code", config=CONFIG, email_=OWNER):
    state = google_oauth.create_state(user) if state is None else state
    return email.finish_gmail_connect(user, email_, code, state, config)


def _error(call):
    with pytest.raises(Exception) as failed:
        call()
    error = failed.value
    return type(error), error.code, error.message


def test_status_before_and_after_connecting(owner):
    assert email.gmail_status(owner, CONFIG) == email.GmailStatus(True, False, None)
    assert email.gmail_status(owner, UNCONFIGURED) == email.GmailStatus(False, False, None)
    google_oauth.save_user_token(owner, "Owner@Example.com", REFRESH_TOKEN)
    assert email.gmail_status(owner, CONFIG) == email.GmailStatus(True, True, "Owner@Example.com")


def test_start_returns_googles_url_with_a_state_stored_for_the_caller(owner):
    url = email.start_gmail_connect(owner, OWNER, CONFIG)
    query = {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}
    assert url.startswith("https://accounts.google.com/") and query["login_hint"] == OWNER
    assert google_oauth.consume_state(query["state"]) == owner
    assert _error(lambda: email.start_gmail_connect(owner, OWNER, UNCONFIGURED)) == (
        NotConfigured, "gmail_not_configured", "Per-user Gmail sending isn't configured on this deployment.")


def test_finish_stores_the_connection(owner):
    FakeGoogle(email="Owner@Example.com").install()
    assert _finish(owner) == email.GmailStatus(True, True, "Owner@Example.com")
    assert _rows() == [(owner, "Owner@Example.com", REFRESH_TOKEN)]


def test_a_state_that_is_another_users_used_expired_or_unknown_stores_nothing(owner, make_user):
    google = FakeGoogle().install()
    other = make_user(email="other@example.com")
    used = google_oauth.create_state(owner)
    google_oauth.consume_state(used)
    expired = google_oauth.create_state(owner)
    with session_scope() as s:
        s.get(OAuthState, expired).expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    invalid = (Rejected, "gmail_state_invalid",
               "This Gmail connection request expired or was already used. Try connecting again.")
    for state in (google_oauth.create_state(other), used, expired, "unknown", ""):
        assert _error(lambda: _finish(owner, state=state)) == invalid
    assert google.requests == [] and _rows() == []


def test_the_state_is_used_up_even_when_the_exchange_fails(owner):
    google = FakeGoogle().install()
    google.exchange = google_error(400, "invalid_grant")
    state = google_oauth.create_state(owner)
    assert _error(lambda: _finish(owner, state=state))[1] == "gmail_connect_failed"
    assert _error(lambda: _finish(owner, state=state))[1] == "gmail_state_invalid"


@pytest.mark.parametrize("setup, expected", [
    (lambda g: setattr(g, "exchange", google_error(400, "invalid_grant")),
     (Rejected, "gmail_connect_failed", "That Google approval has expired or was already used. Try connecting again.")),
    (lambda g: setattr(g, "exchange", google_error(401, "invalid_client")),
     (NotConfigured, "gmail_not_configured", "Gmail sending isn't set up correctly on this deployment.")),
    (lambda g: setattr(g, "exchange", httpx.Response(200, json={"refresh_token": "r"})),
     (UpstreamError, "upstream_error", "Google returned an incomplete response. Try connecting again.")),
    (lambda g: setattr(g, "exchange", httpx.Response(200, json={"access_token": "a", "refresh_token": "r",
                                                                "scope": "openid email"})),
     (Rejected, "gmail_connect_failed",
      "Google didn't give permission to send email. Try again and allow “Send email on your behalf”.")),
    (lambda g: setattr(g, "userinfo", httpx.Response(200, json={})),
     (Rejected, "gmail_connect_failed", "Could not read your email address from Google.")),
    (lambda g: setattr(g, "userinfo", httpx.Response(200, json={"email": "someone.else@example.com"})),
     (Rejected, "gmail_connect_failed", "That Google account doesn't match your signed-in email "
                                        "(owner@example.com). Connect the Gmail account you're logged in with.")),
    (lambda g: setattr(g, "exchange", httpx.Response(503)),
     (UpstreamError, "upstream_error", "Couldn't reach Google. Try connecting again in a minute.")),
    (lambda g: setattr(g, "exchange", httpx.ReadTimeout("slow")),
     (UpstreamTimeout, "upstream_timeout", "Google took too long to respond. Try connecting again.")),
], ids=["invalid-grant", "client", "no-access-token", "scope", "no-email", "mismatch", "google-5xx", "timeout"])
def test_each_connect_failure_has_its_message_and_stores_nothing(owner, setup, expected):
    setup(FakeGoogle().install())
    assert _error(lambda: _finish(owner)) == expected
    assert _rows() == []


def test_a_blank_code_or_no_config_fails_before_google(owner):
    google = FakeGoogle().install()
    assert _error(lambda: _finish(owner, code="  ")) == (
        Rejected, "gmail_connect_failed", "That Google approval has expired or was already used. Try connecting again.")
    assert _error(lambda: _finish(owner, config=UNCONFIGURED))[1] == "gmail_not_configured"
    assert google.requests == []


def test_no_refresh_token_keeps_an_existing_connection_and_refuses_a_new_one(owner):
    google = FakeGoogle().install()
    google.exchange = httpx.Response(200, json={"access_token": "a"})
    assert _error(lambda: _finish(owner)) == (
        Rejected, "gmail_connect_failed", "Google did not return a refresh token. Remove this app's access at "
                                          "https://myaccount.google.com/permissions and connect again.")
    google_oauth.save_user_token(owner, OWNER, "refresh-kept")
    assert _finish(owner) == email.GmailStatus(True, True, OWNER)
    assert _rows() == [(owner, OWNER, "refresh-kept")]


def test_disconnect_deletes_then_revokes_and_a_failed_revoke_still_disconnects(owner, caplog):
    google = FakeGoogle().install()
    google_oauth.save_user_token(owner, OWNER, REFRESH_TOKEN)
    assert email.disconnect_gmail(owner, CONFIG) == email.GmailStatus(True, False, None)
    assert _rows() == [] and [google.form(r) for r in google.requests] == [{"token": REFRESH_TOKEN}]
    google_oauth.save_user_token(owner, OWNER, "refresh-2")
    google.revoke = httpx.ConnectError("down")
    with caplog.at_level(logging.WARNING):
        assert email.disconnect_gmail(owner, CONFIG).connected is False
    assert _rows() == []
    assert [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING] == [
        f"gmail.disconnect user_id={owner} outcome=revoke_failed"]
    assert email.disconnect_gmail(owner, CONFIG).connected is False         # nothing stored: no revoke
    assert len(google.requests) == 2


def test_the_logs_never_carry_a_code_state_token_or_address(owner, caplog):
    google = FakeGoogle().install()
    state = google_oauth.create_state(owner)
    with caplog.at_level(logging.DEBUG):
        _finish(owner, state=state)
        google.exchange = google_error(401, "invalid_client")
        with pytest.raises(NotConfigured):
            _finish(owner)
        email.disconnect_gmail(owner, CONFIG)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert "google_error=invalid_client" in text
    for secret in ("auth-code", state, REFRESH_TOKEN, OWNER, "secret-456", "SECRET-GOOGLE-TEXT"):
        assert secret not in text
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth; "
````

**with:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth, usecases.email; "
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_usecase_email.py 2>&1 | tail -3`
**Expected** (`usecases.email` does not exist yet):
```
ERROR backend/tests/test_usecase_email.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: Write the usecases**

**Create `backend/usecases/email.py`:**

````python
"""Gmail and the bulletin email (slice 5b spec, "usecases/email.py"; slice 5b-2).

The Gmail connection is the user's own (user-scoped, `gmail_tokens`), so it
works in every church they belong to:
- gmail_status: configured, connected, and the Google address;
- start_gmail_connect: a new single-use state and Google's consent URL, with
  the signed-in address as the login hint;
- finish_gmail_connect: the state is checked (and used up) first, then the
  code is exchanged with no database session open, then the refresh token is
  stored. Every Google failure becomes one of the messages below; Google's
  own text is never shown (F §1.5);
- disconnect_gmail: the row is deleted, then the grant revoked at Google,
  best effort (a failed revoke is logged and ignored).

Task 12 adds send_bulletin_email. Logs carry user ids and outcomes, never a
code, a state, a token or an address (F §2.5). No FastAPI, Starlette or
Streamlit here.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

import google_oauth
from db import session_scope
from domain_errors import DomainError, NotConfigured, Rejected, UpstreamError, UpstreamTimeout
from google_oauth import GoogleErrorKind, GoogleOAuthConfig, GoogleOAuthError

logger = logging.getLogger(__name__)

NOT_CONFIGURED = "Per-user Gmail sending isn't configured on this deployment."
MISCONFIGURED = "Gmail sending isn't set up correctly on this deployment."
STATE_INVALID = "This Gmail connection request expired or was already used. Try connecting again."
CODE_INVALID = "That Google approval has expired or was already used. Try connecting again."
INCOMPLETE = "Google returned an incomplete response. Try connecting again."
SCOPE_MISSING = "Google didn't give permission to send email. Try again and allow “Send email on your behalf”."
NO_EMAIL = "Could not read your email address from Google."
MISMATCH = ("That Google account doesn't match your signed-in email ({email}). "
            "Connect the Gmail account you're logged in with.")
NO_REFRESH_TOKEN = ("Google did not return a refresh token. Remove this app's access at "
                    "https://myaccount.google.com/permissions and connect again.")
GOOGLE_UNREACHABLE = "Couldn't reach Google. Try connecting again in a minute."
GOOGLE_SLOW = "Google took too long to respond. Try connecting again."


@dataclass(frozen=True)
class GmailStatus:
    configured: bool
    connected: bool
    google_email: Optional[str]


def not_configured() -> NotConfigured:
    return NotConfigured(NOT_CONFIGURED, code="gmail_not_configured")


def misconfigured(event: str, error: GoogleOAuthError) -> NotConfigured:
    """Our client id, secret or redirect URI is wrong: an ERROR in the log (Google's error code only)."""
    logger.error("%s outcome=client_misconfigured google_error=%s", event, error.google_error)
    return NotConfigured(MISCONFIGURED, code="gmail_not_configured")


def gmail_status(user_id: uuid.UUID, config: GoogleOAuthConfig) -> GmailStatus:
    """GET /gmail-connection."""
    connection = google_oauth.get_connection(user_id)
    return GmailStatus(configured=config.configured, connected=connection is not None,
                       google_email=connection.google_email if connection else None)


def start_gmail_connect(user_id: uuid.UUID, user_email: str, config: GoogleOAuthConfig) -> str:
    """POST /gmail-connection/auth-url: Google's consent URL with a new state."""
    if not config.configured:
        raise not_configured()
    state = google_oauth.create_state(user_id)
    return google_oauth.build_auth_url(config, state, login_hint=user_email)


def _connect_error(error: GoogleOAuthError, user_email: str) -> DomainError:
    kind = error.kind
    if kind == GoogleErrorKind.CLIENT_MISCONFIGURED:
        return misconfigured("gmail.connect", error)
    if kind == GoogleErrorKind.INVALID_GRANT:
        return Rejected(CODE_INVALID, code="gmail_connect_failed")
    if kind == GoogleErrorKind.SCOPE_MISSING:
        return Rejected(SCOPE_MISSING, code="gmail_connect_failed")
    if kind == GoogleErrorKind.NO_EMAIL:
        return Rejected(NO_EMAIL, code="gmail_connect_failed")
    if kind == GoogleErrorKind.EMAIL_MISMATCH:
        return Rejected(MISMATCH.format(email=user_email), code="gmail_connect_failed")
    if kind == GoogleErrorKind.INCOMPLETE_RESPONSE:
        return UpstreamError(INCOMPLETE, code="upstream_error")
    if kind == GoogleErrorKind.TIMEOUT:
        return UpstreamTimeout(GOOGLE_SLOW, code="upstream_timeout")
    return UpstreamError(GOOGLE_UNREACHABLE, code="upstream_error")


def finish_gmail_connect(user_id: uuid.UUID, user_email: str, code: str, state: str,
                         config: GoogleOAuthConfig) -> GmailStatus:
    """POST /gmail-connection: the order of the 5b spec's error table; nothing
    is stored unless every check passes. `user_email` is the verified address
    of the signed-in user (the token's), never a database lookup."""
    if not config.configured:
        raise not_configured()
    if google_oauth.consume_state(state) != user_id:               # CSRF first, in its own transaction
        logger.info("gmail.connect user_id=%s outcome=state_invalid", user_id)
        raise Rejected(STATE_INVALID, code="gmail_state_invalid")
    if not code.strip():
        raise Rejected(CODE_INVALID, code="gmail_connect_failed")
    try:
        grant = google_oauth.exchange_code(config, code, expected_email=user_email)   # no session open
    except GoogleOAuthError as error:
        logger.info("gmail.connect user_id=%s outcome=%s", user_id, error.kind.value)
        raise _connect_error(error, user_email) from None
    with session_scope() as s:
        if grant.refresh_token:
            google_oauth.save_user_token(user_id, grant.google_email, grant.refresh_token, session=s)
        elif google_oauth.get_connection(user_id, session=s) is None:
            logger.info("gmail.connect user_id=%s outcome=no_refresh_token", user_id)
            raise Rejected(NO_REFRESH_TOKEN, code="gmail_connect_failed")
    logger.info("gmail.connect user_id=%s outcome=connected", user_id)
    return gmail_status(user_id, config)


def disconnect_gmail(user_id: uuid.UUID, config: GoogleOAuthConfig) -> GmailStatus:
    """DELETE /gmail-connection: forget the connection, then revoke it at Google
    (best effort, outside the transaction)."""
    removed = google_oauth.delete_connection(user_id)
    if removed is not None and not google_oauth.revoke_token(removed):
        logger.warning("gmail.disconnect user_id=%s outcome=revoke_failed", user_id)
    logger.info("gmail.disconnect user_id=%s outcome=%s", user_id, "disconnected" if removed else "not_connected")
    return GmailStatus(configured=config.configured, connected=False, google_email=None)
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_usecase_email.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`20 passed in <t>s`; `1727 passed, 26 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/usecases/email.py backend/tests/test_usecase_email.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Slice 5b-2: the Gmail connection usecases" -m "usecases/email.py: the status; the consent URL with a new state and the
signed-in address as login hint; finishing a connect in the 5b spec's
order (not configured, the state used up and checked, a blank code, the
exchange with no session open, then the store, keeping a stored token
when Google sends none); and disconnecting (delete, then revoke at Google,
best effort). Each Google failure has its message; Google's text is never
shown, its error code is logged only for our own misconfiguration." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1727 passed, 26 skipped`; frontend `780 passed` in 94 files.

### Task 6: `/gmail-connection` (B API, Schemas; clarification 7)

**Files:**
- Create: `backend/tests/test_api_gmail.py`, `backend/api/routes/gmail.py`
- Modify: `backend/tests/test_route_guards.py`, `backend/tests/test_ratelimit.py`, `backend/api/deps.py`, `backend/api/main.py`, `backend/api/ratelimit.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (regenerated)

- [ ] **Step 1: Write the failing tests**

The client fixture overrides `get_google_config`, so the routes see a test client id and the not-configured case sets an empty one. The four routes join `USER_SCOPED`. `POST /gmail-connection/auth-url` gets the new `gmail_connect` bucket (10 in 10 minutes per user; plan review M6), pinned in `test_ratelimit.py`; the 11th request is a 429 and stores no state.

**Create `backend/tests/test_api_gmail.py`:**

````python
"""/gmail-connection over HTTP (slice 5b spec, API and Testing "test_api_gmail.py";
slice 5b-2): user-scoped (X-Church-Id ignored), the exact codes and messages,
and Google's own text never in a response. Google is tests.fake_google."""
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import google_oauth
from api.deps import get_google_config
from db import session_scope
from db.models import OAuthState
from tests.api_helpers import auth_headers, make_api_client
from tests.fake_google import REFRESH_TOKEN, FakeGoogle, google_error

OWNER = "owner@example.com"
CONFIG = google_oauth.GoogleOAuthConfig("client-123", "secret-456", "https://app.example.org/gmail/callback")
DISCONNECTED = {"configured": True, "connected": False, "google_email": None}


@pytest.fixture
def config():
    return {"value": CONFIG}


@pytest.fixture
def client(tmp_db, config):
    client = make_api_client()
    client.app.dependency_overrides[get_google_config] = lambda: config["value"]
    return client


def _error(r) -> tuple:
    error = r.json()["error"]
    return r.status_code, error["code"], error["message"]


def _start(client, email=OWNER) -> str:
    r = client.post("/gmail-connection/auth-url", headers=auth_headers(email))
    assert r.status_code == 200, r.text
    return {key: values[0] for key, values in parse_qs(urlsplit(r.json()["auth_url"]).query).items()}["state"]


def test_connect_status_and_disconnect(client):
    google = FakeGoogle(email="Owner@Example.com").install()
    headers = {**auth_headers(OWNER), "X-Church-Id": "not-a-church"}           # ignored: user-scoped
    assert client.get("/gmail-connection", headers=headers).json() == DISCONNECTED
    r = client.post("/gmail-connection/auth-url", headers=headers)
    url = r.json()["auth_url"]
    query = {key: values[0] for key, values in parse_qs(urlsplit(url).query).items()}
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert (query["login_hint"], query["redirect_uri"]) == (OWNER, CONFIG.redirect_uri)
    r = client.post("/gmail-connection", headers=headers, json={"code": "auth-code", "state": query["state"]})
    connected = {"configured": True, "connected": True, "google_email": "Owner@Example.com"}
    assert (r.status_code, r.json()) == (200, connected)
    assert client.get("/gmail-connection", headers=headers).json() == connected
    r = client.delete("/gmail-connection", headers=headers)
    assert (r.status_code, r.json()) == (200, DISCONNECTED)
    assert google.form(google.requests[-1]) == {"token": REFRESH_TOKEN}
    assert client.get("/gmail-connection", headers=headers).json() == DISCONNECTED


def test_a_connection_is_the_users_own(client):
    FakeGoogle().install()
    state = _start(client)
    r = client.post("/gmail-connection", headers=auth_headers("other@example.com"),
                    json={"code": "auth-code", "state": state})
    assert _error(r) == (400, "gmail_state_invalid",
                         "This Gmail connection request expired or was already used. Try connecting again.")
    assert client.get("/gmail-connection", headers=auth_headers(OWNER)).json() == DISCONNECTED


@pytest.mark.parametrize("answer, expected", [
    (google_error(400, "invalid_grant"),
     (400, "gmail_connect_failed", "That Google approval has expired or was already used. Try connecting again.")),
    (google_error(401, "invalid_client"),
     (503, "gmail_not_configured", "Gmail sending isn't set up correctly on this deployment.")),
    (httpx.Response(200, json={"refresh_token": "r"}),
     (502, "upstream_error", "Google returned an incomplete response. Try connecting again.")),
    (httpx.Response(500, json={"error": "SECRET-GOOGLE-TEXT"}),
     (502, "upstream_error", "Couldn't reach Google. Try connecting again in a minute.")),
    (httpx.ReadTimeout("slow"),
     (504, "upstream_timeout", "Google took too long to respond. Try connecting again.")),
], ids=["invalid-grant", "client", "incomplete", "google-5xx", "timeout"])
def test_connect_errors_never_show_googles_text(client, answer, expected):
    google = FakeGoogle().install()
    google.exchange = answer
    r = client.post("/gmail-connection", headers=auth_headers(OWNER), json={"code": "auth-code", "state": _start(client)})
    assert _error(r) == expected
    assert "SECRET-GOOGLE-TEXT" not in r.text


def test_a_mismatched_account_is_named(client):
    FakeGoogle(email="someone.else@example.com").install()
    r = client.post("/gmail-connection", headers=auth_headers(OWNER), json={"code": "auth-code", "state": _start(client)})
    assert _error(r) == (400, "gmail_connect_failed", "That Google account doesn't match your signed-in email "
                                                      "(owner@example.com). Connect the Gmail account you're logged in with.")


def test_not_configured(client, config):
    config["value"] = google_oauth.GoogleOAuthConfig("", "", "")
    not_configured = (503, "gmail_not_configured", "Per-user Gmail sending isn't configured on this deployment.")
    assert client.get("/gmail-connection", headers=auth_headers(OWNER)).json() == {
        "configured": False, "connected": False, "google_email": None}
    assert _error(client.post("/gmail-connection/auth-url", headers=auth_headers(OWNER))) == not_configured
    r = client.post("/gmail-connection", headers=auth_headers(OWNER), json={"code": "c", "state": "s"})
    assert _error(r) == not_configured


def test_consent_urls_are_rate_limited_per_user(client):
    for _ in range(10):
        _start(client)
    r = client.post("/gmail-connection/auth-url", headers=auth_headers(OWNER))
    assert _error(r)[:2] == (429, "rate_limited") and int(r.headers["Retry-After"]) >= 1
    with session_scope() as s:
        assert s.query(OAuthState).count() == 10                      # the refused request stored no state
    assert _start(client, "other@example.com")                        # another user's bucket is their own


def test_the_body_is_checked(client):
    for body in ({"code": "c"}, {"code": "c", "state": "s", "extra": 1}, {"code": "c" * 2049, "state": "s"}):
        r = client.post("/gmail-connection", headers=auth_headers(OWNER), json=body)
        assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request"), body


def test_every_gmail_route_needs_a_signed_in_user(client):
    for method, path in (("GET", "/gmail-connection"), ("POST", "/gmail-connection/auth-url"),
                         ("POST", "/gmail-connection"), ("DELETE", "/gmail-connection")):
        r = client.request(method, path, json={"code": "c", "state": "s"} if path == "/gmail-connection" else None)
        assert (r.status_code, r.json()["error"]["code"]) == (401, "unauthenticated"), (method, path)
````

**In `backend/tests/test_route_guards.py`, replace:**

````python
4a: GET /liturgy/config).
````

**with:**

````python
4a: GET /liturgy/config; 5b-2: the four /gmail-connection routes).
````

**In `backend/tests/test_route_guards.py`, replace:**

````python
    ("GET", "/liturgy/config"),
````

**with:**

````python
    ("GET", "/liturgy/config"),
    ("GET", "/gmail-connection"),
    ("POST", "/gmail-connection/auth-url"),
    ("POST", "/gmail-connection"),
    ("DELETE", "/gmail-connection"),
````

**In `backend/tests/test_ratelimit.py`, replace:**

````python
        "picture": (Rule("user", 20, 3_600), Rule("church", 60, 86_400)),     # printed bulletin PR 3a
````

**with:**

````python
        "picture": (Rule("user", 20, 3_600), Rule("church", 60, 86_400)),     # printed bulletin PR 3a
        "gmail_connect": (Rule("user", 10, 600),),                            # slice 5b-2
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_gmail.py backend/tests/test_route_guards.py 2>&1 | tail -3`
**Expected** (`api.deps.get_google_config` does not exist yet: an `ImportError` above these lines):
```
ERROR backend/tests/test_api_gmail.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: Write the routes, the dependency, and mount them**

**Create `backend/api/routes/gmail.py`:**

````python
"""/gmail-connection: the caller's own Gmail connection (slice 5b spec, API;
slice 5b-2).

User-scoped: every route reads only the signed-in user's connection and
ignores X-Church-Id (test_route_guards USER_SCOPED), since one connection
works in every church. Plain `def` routes, each one usecase call, no SQL and
no try/except (F §2.2 rule 1). The Google client comes from get_google_config
(Railway's GOOGLE_* variables; tests override it).

- GET: configured, connected and the Google address.
- POST /auth-url: Google's consent URL with a new single-use state; the page
  sends the browser there in the same tab. Each request stores a state, so
  the `gmail_connect` bucket allows 10 in 10 minutes per user (429 after).
- POST: the code and the state Google sent back to /gmail/callback; 200 with
  the new status, or the 5b spec's error table.
- DELETE: forgets the connection and revokes it at Google (best effort).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.deps import CurrentUser, get_current_user, get_google_config
from api.ratelimit import rate_limit
from api.errors import error_responses
from google_oauth import GoogleOAuthConfig
from usecases import email

router = APIRouter()


class GmailConnectionOut(BaseModel):
    configured: bool = Field(description="false when this deployment has no Google client: nobody can connect")
    connected: bool
    google_email: str | None = Field(description="the connected Google address; null when not connected")


class GmailAuthUrlOut(BaseModel):
    auth_url: str


class GmailConnectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(max_length=2048)
    state: str = Field(max_length=256)


def _out(status: email.GmailStatus) -> GmailConnectionOut:
    return GmailConnectionOut(configured=status.configured, connected=status.connected,
                              google_email=status.google_email)


@router.get("/gmail-connection", response_model=GmailConnectionOut, responses=error_responses(401, 422, 503))
def get_gmail_connection(user: CurrentUser = Depends(get_current_user),
                         config: GoogleOAuthConfig = Depends(get_google_config)) -> GmailConnectionOut:
    return _out(email.gmail_status(user.id, config))


@router.post("/gmail-connection/auth-url", response_model=GmailAuthUrlOut,
             responses=error_responses(401, 422, 429, 503))
def start_gmail_connect(user: CurrentUser = Depends(get_current_user),
                        config: GoogleOAuthConfig = Depends(get_google_config),
                        _limit: None = Depends(rate_limit("gmail_connect"))) -> GmailAuthUrlOut:
    return GmailAuthUrlOut(auth_url=email.start_gmail_connect(user.id, user.email, config))


@router.post("/gmail-connection", response_model=GmailConnectionOut,
             responses=error_responses(400, 401, 422, 502, 503, 504))
def finish_gmail_connect(payload: GmailConnectIn, user: CurrentUser = Depends(get_current_user),
                         config: GoogleOAuthConfig = Depends(get_google_config)) -> GmailConnectionOut:
    return _out(email.finish_gmail_connect(user.id, user.email, payload.code, payload.state, config))


@router.delete("/gmail-connection", response_model=GmailConnectionOut, responses=error_responses(401, 422, 503))
def disconnect_gmail(user: CurrentUser = Depends(get_current_user),
                     config: GoogleOAuthConfig = Depends(get_google_config)) -> GmailConnectionOut:
    return _out(email.disconnect_gmail(user.id, config))
````

**In `backend/api/deps.py`, replace:**

````python
from api.settings import get_settings
````

**with:**

````python
from api.settings import get_settings
from google_oauth import GoogleOAuthConfig
````

**Append to `backend/api/deps.py`:**

````python


def get_google_config() -> GoogleOAuthConfig:
    """The Google OAuth client for the Gmail routes (slice 5b-2), from the
    GOOGLE_* variables; tests override this dependency."""
    return get_settings().google_oauth
````

**In `backend/api/main.py`, replace:**

````python
from api.routes import (bulletin_images, bulletin_settings, churches, contacts, documents, health, hymnals, hymns,
                        invites, lectionary, liturgy, liturgy_review, me, reference, rubric, scripture, services)
````

**with:**

````python
from api.routes import (bulletin_images, bulletin_settings, churches, contacts, documents, gmail, health, hymnals,
                        hymns, invites, lectionary, liturgy, liturgy_review, me, reference, rubric, scripture,
                        services)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(contacts.router)
````

**with:**

````python
    app.include_router(contacts.router)
    app.include_router(gmail.router)
````

**In `backend/api/ratelimit.py`, replace:**

````python
# printed bulletin PR 3a (POST /bulletin-images).
````

**with:**

````python
# printed bulletin PR 3a (POST /bulletin-images). gmail_connect: slice 5b-2
# (POST /gmail-connection/auth-url; a new consent URL and state per request).
````

**In `backend/api/ratelimit.py`, replace:**

````python
    "picture": (Rule("user", 20, 3_600), Rule("church", 60, 86_400)),
````

**with:**

````python
    "picture": (Rule("user", 20, 3_600), Rule("church", 60, 86_400)),
    "gmail_connect": (Rule("user", 10, 600),),
````

- [ ] **Step 4: Regenerate the API files, see the tests pass, and the suites**

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git diff --stat -- frontend/src/lib/api | tail -1` then `.venv/bin/python -m pytest -q backend/tests/test_api_gmail.py backend/tests/test_usecase_email.py backend/tests/test_openapi_contract.py backend/tests/test_route_guards.py backend/tests/test_ratelimit.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
` 2 files changed, 675 insertions(+)`; `54 passed in <t>s`; `1739 passed, 26 skipped in <t>s`; `typecheck 0`, `lint 0` (the new types are not used until T7).

- [ ] **Step 5: Commit**

```bash
git add backend/api/routes/gmail.py backend/api/deps.py backend/api/main.py backend/api/ratelimit.py backend/tests/test_api_gmail.py backend/tests/test_route_guards.py backend/tests/test_ratelimit.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Slice 5b-2: GET, POST and DELETE /gmail-connection" -m "The caller's own Gmail connection, user-scoped (X-Church-Id ignored; the
four routes join USER_SCOPED): the status, Google's consent URL, the
code and state back from /gmail/callback, and disconnecting. The errors
are the 5b spec's codes and messages, never Google's text (a seeded
marker is checked). A new consent URL is limited to 10 in 10 minutes per
user (the gmail_connect bucket). get_google_config reads the GOOGLE_*
settings; tests override it. OpenAPI and the types regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1739 passed, 26 skipped`; frontend `780 passed` in 94 files.

### Task 7: The trip to Google in the browser: helpers, queries, the Supabase client (B flows A-C, "Pure modules", "Query hooks"; clarification 8)

**Files:**
- Create: `frontend/src/lib/gmail.test.ts`, `frontend/src/lib/supabase/client.test.ts`, `frontend/src/lib/gmail.ts`, `frontend/src/lib/queries/gmail.ts`
- Modify: `frontend/src/lib/urls.test.ts`, `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/timeouts.ts`, `frontend/src/lib/supabase/client.ts`, `frontend/src/lib/urls.ts`

- [ ] **Step 1: Write the failing tests**

The Supabase test mocks `@supabase/ssr` (in the `unit` project; the `dom` project's setup mocks `@/lib/supabase/client` itself). The queries are covered by the page tests (T8, T9).

**Create `frontend/src/lib/gmail.test.ts`:**

````ts
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { ApiCall } from "@/lib/queries/client";

import { connectGmailOnce, DEFAULT_RETURN, gmailErrorMessage, isGoogleAuthUrl, parseCallbackParams, returnToFrom } from "./gmail";

describe("connecting Gmail (slice 5b-2)", () => {
  it("accepts only Google's consent page", () => {
    expect(isGoogleAuthUrl("https://accounts.google.com/o/oauth2/v2/auth?state=s")).toBe(true);
    for (const url of ["http://accounts.google.com/o/oauth2/v2/auth", "https://accounts.google.com.evil.example/",
      "https://evil.example/?https://accounts.google.com/", "javascript:alert(1)", "/o/oauth2/v2/auth", ""]) {
      expect(isGoogleAuthUrl(url), url).toBe(false);
    }
  });

  it("returns only to a page of the app, else Settings → Account", () => {
    expect(returnToFrom("/builder/review")).toBe("/builder/review");
    expect(returnToFrom("/settings/account")).toBe("/settings/account");
    for (const raw of ["//evil.com", "https://evil.com/builder", "/login", "/gmail/callback?x", null, 42]) {
      expect(returnToFrom(raw), String(raw)).toBe(DEFAULT_RETURN);
    }
  });

  it("reads Google's answer from the query string", () => {
    expect(parseCallbackParams("?code=4%2F0Ab&state=s1&scope=email")).toEqual({ code: "4/0Ab", state: "s1", error: null });
    expect(parseCallbackParams("?error=access_denied&state=s1")).toEqual({ code: null, state: "s1", error: "access_denied" });
    expect(parseCallbackParams("")).toEqual({ code: null, state: null, error: null });
    expect(parseCallbackParams("?code=&state=%20")).toEqual({ code: null, state: null, error: null });
  });

  it("posts each state once, however often it is asked", async () => {
    const answer = { configured: true, connected: true, google_email: "owner@example.com" };
    const call = vi.fn(async () => answer) as unknown as ApiCall;
    const first = connectGmailOnce(call, { code: "c", state: "state-once" });
    const second = connectGmailOnce(call, { code: "c", state: "state-once" });
    expect(second).toBe(first);
    await expect(first).resolves.toEqual(answer);
    expect(call).toHaveBeenCalledTimes(1);
    expect(call).toHaveBeenCalledWith("/gmail-connection", { method: "POST", json: { code: "c", state: "state-once" } });
    connectGmailOnce(call, { code: "c", state: "state-other" });
    expect(call).toHaveBeenCalledTimes(2);
  });

  it("says what Google's or Gmail's failure was, and anything else as every toast does", () => {
    const own = "Couldn't reach Google. Try connecting again in a minute.";
    expect(gmailErrorMessage(new ApiError(502, "upstream_error", own))).toBe(own);
    expect(gmailErrorMessage(new ApiError(503, "gmail_not_configured", "Not set up."))).toBe("Not set up.");
    expect(gmailErrorMessage(new ApiError(500, "internal_error", "boom", { requestId: "abcdef123456" }))).toBe(
      "Something went wrong. (Ref: abcdef12)",
    );
    expect(gmailErrorMessage(new ApiError(400, "gmail_state_invalid", "Expired."))).toBe("Expired.");
  });
});
````

**In `frontend/src/lib/urls.test.ts`, replace:**

````ts
  it.each(["/join", "/builder/hymns", "/settings/people"])("accepts %s", (path) => {
````

**with:**

````ts
  it.each(["/join", "/builder/hymns", "/settings/people", "/gmail/callback"])("accepts %s", (path) => {
````

**In `frontend/src/lib/urls.test.ts`, replace:**

````ts
    ["a first segment outside the allow-list", ["/joinx", "/", "/login", "/auth/callback"]],
````

**with:**

````ts
    ["a first segment outside the allow-list", ["/joinx", "/", "/login", "/auth/callback", "/gmail", "/gmail/other"]],
````

**Create `frontend/src/lib/supabase/client.test.ts`:**

````ts
import { beforeEach, describe, expect, it, vi } from "vitest";

const createBrowserClient = vi.fn<(...args: unknown[]) => object>(() => ({}));
vi.mock("@supabase/ssr", () => ({ createBrowserClient: (...args: unknown[]) => createBrowserClient(...args) }));

import { createClient } from "./client";

beforeEach(() => {
  createBrowserClient.mockClear();
});

describe("the browser's Supabase client (slice 5b-2)", () => {
  it("never reads a sign-in from the address bar, so /gmail/callback?code= stays the Gmail page's", () => {
    createClient();
    expect(createBrowserClient).toHaveBeenCalledTimes(1);
    expect(createBrowserClient.mock.calls[0][2]).toEqual({ auth: { detectSessionInUrl: false } });
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/gmail.test.ts src/lib/urls.test.ts src/lib/supabase/client.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`gmail.ts` does not exist yet; `/gmail/callback` is refused; the option is missing):
```
   × safeInternalPath > accepts /gmail/callback <t>ms
   × the browser's Supabase client (slice 5b-2) > never reads a sign-in from the address bar, so /gmail/callback?code= stays the Gmail page's <t>ms
 FAIL  |unit| src/lib/gmail.test.ts [ src/lib/gmail.test.ts ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
      Tests  2 failed | 21 passed (23)
```

- [ ] **Step 3: Write the types, the helpers, the queries and the two changes**

**Append to `frontend/src/lib/api/types.ts`:**

````ts

/**
 * `/gmail-connection` (slice 5b-2): the caller's own Gmail connection
 * (`configured` false: this deployment has no Google client), Google's consent
 * URL, and the code and state `/gmail/callback` posts back.
 */
export type GmailConnection = components["schemas"]["GmailConnectionOut"];
export type GmailAuthUrl = components["schemas"]["GmailAuthUrlOut"];
export type GmailConnectBody = components["schemas"]["GmailConnectIn"];
````

**In `frontend/src/lib/api/timeouts.ts`, replace:**

````ts
  "POST /bulletin-images": 120_000,
````

**with:**

````ts
  "POST /bulletin-images": 120_000,
  // Slice 5b-2 (F §1.8): the code exchange, then the address lookup. Google's timeouts are per phase (5 s
  // to connect, then 15 s for each wait), not a deadline for the call, so this is the overall limit; a
  // connect it stops waiting for shows an error, and connecting again starts afresh.
  "POST /gmail-connection": 40_000,
````

**In `frontend/src/lib/supabase/client.ts`, replace:**

````ts

export function createClient() {
````

**with:**

````ts

/**
 * The browser's Supabase client. It never reads a sign-in from the address
 * bar (`detectSessionInUrl: false`, slice 5b-2): Google sends the Gmail
 * connection back to `/gmail/callback?code=…&state=…` (or `?error=…`), the
 * same names Supabase's own callbacks use, and the client would otherwise
 * post the Gmail code to Supabase. Sign-in does not need it: the server's
 * `/auth/callback` route exchanges Supabase's code.
 */
export function createClient() {
````

**In `frontend/src/lib/supabase/client.ts`, replace:**

````ts
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
````

**with:**

````ts
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { auth: { detectSessionInUrl: false } },
````

**In `frontend/src/lib/urls.ts`, replace:**

````ts
const INTERNAL_PATH_ROOTS = new Set(["join", "builder", "services", "settings", "welcome"]);
````

**with:**

````ts
const INTERNAL_PATH_ROOTS = new Set(["join", "builder", "services", "settings", "welcome"]);
/**
 * Whole paths it may also return to (slice 5b-2): Google's Gmail return page. The proxy keeps only the
 * path in `/login?next=`, so a landing there while signed out comes back after sign-in without Google's
 * answer and shows "Gmail connection didn't finish. Try connecting again." with **Try again**, instead of
 * dropping the user on the Builder with no word about Gmail.
 */
const INTERNAL_PATHS = new Set(["/gmail/callback"]);
````

**In `frontend/src/lib/urls.ts`, replace:**

````ts
 * settings, welcome, matched whole (so `/joinx` is rejected).
````

**with:**

````ts
 * settings, welcome, matched whole (so `/joinx` is rejected), or exactly `/gmail/callback`.
````

**In `frontend/src/lib/urls.ts`, replace:**

````ts
  if (segments.some(isParentSegment)) return null;
````

**with:**

````ts
  if (segments.some(isParentSegment)) return null;
  if (INTERNAL_PATHS.has(raw)) return raw;
````

**Create `frontend/src/lib/gmail.ts`:**

````ts
/**
 * Connecting Gmail (slice 5b spec, flows A-C; slice 5b-2). Pure helpers and
 * the browser's side of the trip to Google:
 *
 * - `startGmailRedirect(authUrl, returnTo, reopen?)`: refuses any URL that is
 *   not Google's consent page; otherwise remembers where to come back to
 *   (`wsb:gmailReturnTo`, and for the email dialog what to reopen,
 *   `wsb:reopenEmailDialog`, both in sessionStorage) and leaves for Google in
 *   the same tab. The draft is already in localStorage.
 * - `readReturnTo()`: the remembered page, through `safeInternalPath`, else
 *   Settings → Account.
 * - `parseCallbackParams(search)`: what Google put on `/gmail/callback`.
 * - `connectGmailOnce(call, {code, state})`: `POST /gmail-connection` once
 *   per state, however often it is asked (React StrictMode runs the callback
 *   page's effect twice; a state is single use at the server).
 * - `gmailErrorMessage(e)`: what a failed Gmail request tells the user.
 */
import { ApiError } from "@/lib/api/client";
import { errorToastMessage } from "@/lib/api/errors";
import type { GmailConnectBody, GmailConnection } from "@/lib/api/types";
import type { ApiCall } from "@/lib/queries/client";
import { readSession, removeSession, writeSession } from "@/lib/storage";
import { safeInternalPath } from "@/lib/urls";

export const GMAIL_RETURN_KEY = "wsb:gmailReturnTo";
export const REOPEN_EMAIL_KEY = "wsb:reopenEmailDialog";
export const DEFAULT_RETURN = "/settings/account";

/** Leaving the app for Google; tests replace `assign` (jsdom cannot navigate). */
export const browser = {
  assign(url: string): void {
    window.location.assign(url);
  },
};

/** True only for Google's consent page over https. */
export function isGoogleAuthUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" && parsed.host === "accounts.google.com";
  } catch {
    return false;
  }
}

/**
 * Leave for Google's consent page, remembering `returnTo` (and `reopen`, the
 * email dialog's state, when given). False, and nothing stored, for a URL that
 * is not Google's.
 */
export function startGmailRedirect(authUrl: string, returnTo: string, reopen?: object): boolean {
  if (!isGoogleAuthUrl(authUrl)) return false;
  writeSession(GMAIL_RETURN_KEY, returnTo);
  if (reopen !== undefined) writeSession(REOPEN_EMAIL_KEY, JSON.stringify(reopen));
  browser.assign(authUrl);
  return true;
}

/** `raw` when it is a page the app may return to, else Settings → Account. */
export function returnToFrom(raw: unknown): string {
  return safeInternalPath(raw) ?? DEFAULT_RETURN;
}

export function readReturnTo(): string {
  return returnToFrom(readSession(GMAIL_RETURN_KEY));
}

export function clearReturnTo(): void {
  removeSession(GMAIL_RETURN_KEY);
}

export type CallbackParams = { code: string | null; state: string | null; error: string | null };

/** `?code=…&state=…` or `?error=…` from `/gmail/callback`'s query string; blank values are null. */
export function parseCallbackParams(search: string): CallbackParams {
  const params = new URLSearchParams(search);
  const value = (name: string) => {
    const found = params.get(name);
    return found === null || found.trim() === "" ? null : found;
  };
  return { code: value("code"), state: value("state"), error: value("error") };
}

const submitted = new Map<string, Promise<GmailConnection>>();

/** `POST /gmail-connection` for this state, or the promise of the one already sent. */
export function connectGmailOnce(call: ApiCall, body: GmailConnectBody): Promise<GmailConnection> {
  let pending = submitted.get(body.state);
  if (pending === undefined) {
    pending = call<GmailConnection>("/gmail-connection", { method: "POST", json: body });
    submitted.set(body.state, pending);
  }
  return pending;
}

/** Gmail's and Google's 5xx answers whose message says what happened and what to do. */
const OWN_MESSAGE_CODES = new Set(["gmail_send_failed", "gmail_not_configured", "upstream_error", "upstream_timeout"]);

/**
 * The sentence for a failed Gmail request: the server's own for a Gmail or
 * Google 502, 503 or 504 ("Couldn't reach Google. Try connecting again in a
 * minute."), which `errorToastMessage` would turn into "Something went
 * wrong."; anything else as every toast says it.
 */
export function gmailErrorMessage(e: unknown): string {
  return e instanceof ApiError && OWN_MESSAGE_CODES.has(e.code) ? e.message : errorToastMessage(e);
}
````

**Create `frontend/src/lib/queries/gmail.ts`:**

````ts
/**
 * The caller's Gmail connection (slice 5b spec, "Query hooks"; slice 5b-2).
 * User-scoped (`api.user`, no church header), under ["gmail-connection"].
 *
 * - `useGmailConnection()`: `GET /gmail-connection`.
 * - `useStartGmailConnect()`: `POST /gmail-connection/auth-url`, then
 *   `startGmailRedirect` to Google in the same tab; a URL that is not Google's
 *   is refused with "Something went wrong.".
 * - `useDisconnectGmail()`: `DELETE /gmail-connection`; its answer (not
 *   connected) goes straight into the cache.
 * A 401 is the app's (`handleAuthErrors`); any other failure is toasted
 * (`gmailErrorMessage`).
 */
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import type { GmailAuthUrl, GmailConnection } from "@/lib/api/types";
import { gmailErrorMessage, startGmailRedirect } from "@/lib/gmail";

import { useApi } from "./client";
import { keys } from "./keys";

export const SOMETHING_WRONG = "Something went wrong.";

export function useGmailConnection(): UseQueryResult<GmailConnection, ApiError> {
  const api = useApi();
  return useQuery<GmailConnection, ApiError>({
    queryKey: keys.gmailConnection(),
    queryFn: ({ signal }) => api.user<GmailConnection>("/gmail-connection", { signal }),
  });
}

/** Where to come back to after Google, and (from the email dialog, 5b-2b) what to reopen. */
export type StartGmailConnect = { returnTo: string; reopen?: object };

export function useStartGmailConnect() {
  const api = useApi();
  return useMutation<GmailAuthUrl, ApiError, StartGmailConnect>({
    mutationFn: () => api.user<GmailAuthUrl>("/gmail-connection/auth-url", { method: "POST" }),
    onSuccess: (data, { returnTo, reopen }) => {
      if (!startGmailRedirect(data.auth_url, returnTo, reopen)) toast.error(SOMETHING_WRONG);
    },
    onError: (e) => {
      if (e.status === 401) return;
      toast.error(gmailErrorMessage(e));
    },
  });
}

export function useDisconnectGmail() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation<GmailConnection, ApiError, void>({
    mutationFn: () => api.user<GmailConnection>("/gmail-connection", { method: "DELETE" }),
    onSuccess: (data) => queryClient.setQueryData(keys.gmailConnection(), data),
    onError: (e) => {
      if (e.status === 401) return;
      toast.error(gmailErrorMessage(e));
    },
  });
}
````

- [ ] **Step 4: See them pass, and the suite**

Run: `(cd frontend && npx vitest run src/lib/gmail.test.ts src/lib/urls.test.ts src/lib/supabase/client.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
`      Tests  28 passed (28)`; ` Test Files  96 passed (96)` and `      Tests  787 passed (787)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/gmail.ts frontend/src/lib/gmail.test.ts frontend/src/lib/queries/gmail.ts frontend/src/lib/api/types.ts frontend/src/lib/api/timeouts.ts frontend/src/lib/supabase/client.ts frontend/src/lib/supabase/client.test.ts frontend/src/lib/urls.ts frontend/src/lib/urls.test.ts
git commit -q -m "Slice 5b-2: connecting Gmail in the browser: helpers, queries, Supabase option" -m "lib/gmail.ts leaves for Google's consent page only (same tab),
remembering the way back and, from Review, what to reopen; reads the way
back through safeInternalPath; reads Google's answer; posts each state
once; and keeps the server's sentence for a Gmail or Google 5xx.
lib/queries/gmail.ts: the status, starting a connect, disconnecting. The
Supabase browser client no longer reads sign-ins from the address bar, so
/gmail/callback?code= is never taken for one; safeInternalPath accepts
/gmail/callback; POST /gmail-connection waits 40 s." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1739 passed, 26 skipped`; frontend `787 passed` in 96 files.

### Task 8: `/gmail/callback` (B flow C; clarification 9)

**Files:**
- Create: `frontend/src/components/gmail/gmail-callback.test.tsx`, `frontend/src/components/gmail/gmail-callback.tsx`, `frontend/src/app/(signed-in)/gmail/callback/page.tsx`

- [ ] **Step 1: Write the failing tests**

The page renders under `<StrictMode>`, as Next runs it in development, so its effect runs twice: one POST is the proof that `connectGmailOnce` holds. The success test holds the POST open and records every text the page shows (a `MutationObserver`), so "didn't finish" can never have flashed. Each test uses its own state, since `connectGmailOnce` remembers a state for the life of the module.

**Create `frontend/src/components/gmail/gmail-callback.test.tsx`:**

````tsx
/**
 * `/gmail/callback` (slice 5b spec, flow C; slice 5b-2): rendered under
 * StrictMode, as Next runs it in development, with a Toaster. The address bar
 * is set with `history.replaceState` before each render.
 */
import { screen, waitFor } from "@testing-library/react";
import { StrictMode } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GmailCallbackPage from "@/app/(signed-in)/gmail/callback/page";
import { Toaster } from "@/components/ui/sonner";
import { browser, GMAIL_RETURN_KEY } from "@/lib/gmail";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import { me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { CANCELLED, CONNECTED, GOOGLE_REFUSED, NOT_FINISHED } from "./gmail-callback";

const CONNECTED_STATUS = { configured: true, connected: true, google_email: "owner@example.com" };
let n = 0;

function renderCallback(search: string, routes: Record<string, FakeHandler> = {}) {
  window.history.replaceState(null, "", `/gmail/callback${search}`);
  const api = installFakeApi(routes);
  const view = renderWithProviders(
    <StrictMode>
      <GmailCallbackPage />
      <Toaster />
    </StrictMode>,
    { me: me(), path: "/gmail/callback" },
  );
  return { ...view, api };
}

/** A unique state per test: connectGmailOnce remembers each state for the life of the module. */
function nextState(): string {
  n += 1;
  return `state-${n}`;
}

beforeEach(() => {
  window.sessionStorage.setItem(GMAIL_RETURN_KEY, "/builder/review");
});

afterEach(() => {
  toast.dismiss();
  window.history.replaceState(null, "", "/");
});

describe("/gmail/callback (slice 5b-2)", () => {
  it("connects once, never shows the didn't-finish card, cleans the address bar and goes back", async () => {
    let release: (value: unknown) => void = () => {};
    const held = new Promise((resolve) => {
      release = resolve;
    });
    const seen: string[] = [];
    const observer = new MutationObserver(() => seen.push(document.body.textContent ?? ""));
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    const state = nextState();
    const { api, queryClient } = renderCallback(`?code=4%2F0Ab&state=${state}&scope=email`, {
      "POST /gmail-connection": async () => {
        await held;
        return CONNECTED_STATUS;
      },
    });
    expect(screen.getByRole("status")).toHaveTextContent("Connecting your Gmail…");
    await waitFor(() => expect(api.requests).toHaveLength(1));
    expect(window.location.pathname + window.location.search).toBe("/gmail/callback");
    release(undefined);
    expect(await screen.findByText(CONNECTED)).toBeInTheDocument();
    expect(testRouter.replace).toHaveBeenCalledWith("/builder/review");
    observer.disconnect();
    expect(api.requests.map((r) => [r.method, r.path, r.body])).toEqual([
      ["POST", "/gmail-connection", { code: "4/0Ab", state }],
    ]);
    expect(queryClient.getQueryData(keys.gmailConnection())).toEqual(CONNECTED_STATUS);
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBeNull();
    expect(seen.some((text) => text.includes(NOT_FINISHED))).toBe(false);
  });

  it("goes back with a note when the user cancelled at Google, without calling the API", async () => {
    const { api } = renderCallback(`?error=access_denied&state=${nextState()}`);
    expect(await screen.findByText(CANCELLED)).toBeInTheDocument();
    expect(testRouter.replace).toHaveBeenCalledWith("/builder/review");
    expect(api.requests).toEqual([]);
    expect(window.location.search).toBe("");
  });

  it("never shows Google's error value", async () => {
    renderCallback("?error=%3Cb%3Eserver_error%3C%2Fb%3E");
    expect(await screen.findByRole("alert")).toHaveTextContent(GOOGLE_REFUSED);
    expect(document.body.textContent).not.toContain("server_error");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go back" })).toBeInTheDocument();
  });

  it("says the connection didn't finish when the address bar has no answer", async () => {
    const { api, user } = renderCallback("");
    expect(await screen.findByRole("alert")).toHaveTextContent(NOT_FINISHED);
    await user.click(screen.getByRole("button", { name: "Go back" }));
    expect(testRouter.replace).toHaveBeenCalledWith("/builder/review");
    expect(api.requests).toEqual([]);
  });

  it("shows the server's message, and Try again leaves for Google again with the same way back", async () => {
    const assign = vi.spyOn(browser, "assign").mockImplementation(() => {});
    const { api, user } = renderCallback(`?code=c&state=${nextState()}`, {
      "POST /gmail-connection": fakeError(400, "gmail_state_invalid",
        "This Gmail connection request expired or was already used. Try connecting again."),
      "POST /gmail-connection/auth-url": { auth_url: "https://accounts.google.com/o/oauth2/v2/auth?state=new" },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This Gmail connection request expired or was already used. Try connecting again.",
    );
    await user.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith("https://accounts.google.com/o/oauth2/v2/auth?state=new"));
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBe("/builder/review");
    expect(api.requests.map((r) => `${r.method} ${r.path}`)).toEqual([
      "POST /gmail-connection",
      "POST /gmail-connection/auth-url",
    ]);
  });

  it("offers only Go back when Gmail is not set up here, with the server's words for a Google failure", async () => {
    renderCallback(`?code=c&state=${nextState()}`, {
      "POST /gmail-connection": fakeError(503, "gmail_not_configured", "Gmail sending isn't set up correctly on this deployment."),
    });
    expect(await screen.findByRole("alert")).toHaveTextContent("Gmail sending isn't set up correctly on this deployment.");
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
    expect(screen.getByRole("button", { name: "Go back" })).toBeInTheDocument();
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/gmail 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the page does not exist yet):
```
 FAIL  |dom| src/components/gmail/gmail-callback.test.tsx [ src/components/gmail/gmail-callback.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: Write the page**

**Create `frontend/src/components/gmail/gmail-callback.tsx`:**

````tsx
"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Loader2Icon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import {
  clearReturnTo,
  connectGmailOnce,
  gmailErrorMessage,
  parseCallbackParams,
  readReturnTo,
  type CallbackParams,
} from "@/lib/gmail";
import { reportAuthErrors, useApi } from "@/lib/queries/client";
import { useStartGmailConnect } from "@/lib/queries/gmail";
import { keys } from "@/lib/queries/keys";

export const CONNECTING = "Connecting your Gmail…";
export const STILL_CONNECTING = "Still working. This can take up to a minute.";
export const CONNECTED = "Gmail connected";
export const CANCELLED = "Gmail connection was cancelled.";
export const GOOGLE_REFUSED = "Google couldn't connect your Gmail.";
export const NOT_FINISHED = "Gmail connection didn't finish. Try connecting again.";
const CALLBACK_PATH = "/gmail/callback";

type View =
  | { kind: "connecting" }
  | { kind: "failed"; message: string; canRetry: boolean };

/**
 * `/gmail/callback` (slice 5b spec, flow C; slice 5b-2): the page Google sends
 * the browser back to. It reads Google's answer from the address bar once (a
 * ref, so React StrictMode's second effect reuses it), removes it from the
 * address bar and history, and then:
 * - `?error=access_denied` (the user cancelled): "Gmail connection was
 *   cancelled." and back where they started;
 * - another `?error=`: "Google couldn't connect your Gmail." (the value is
 *   never shown), with **Try again** and **Go back**;
 * - a code and a state: "Connecting your Gmail…" while `POST
 *   /gmail-connection` runs, once per state; then "Gmail connected", the
 *   status in the cache, and back; or the server's message with **Try again**
 *   (not when Gmail is not set up here) and **Go back**;
 * - nothing (a signed-out landing lost the query, or a reload after success):
 *   "Gmail connection didn't finish. Try connecting again.".
 * "Back" is the page the connect started from (`wsb:gmailReturnTo`), else
 * Settings → Account. It starts in the "connecting" state so the "didn't
 * finish" card never flashes during a successful connect.
 */
export function GmailCallback() {
  const api = useApi();
  const queryClient = useQueryClient();
  const router = useRouter();
  const params = useRef<CallbackParams | null>(null);
  const [view, setView] = useState<View>({ kind: "connecting" });
  const slow = useStillWorking(view.kind === "connecting");
  const start = useStartGmailConnect();

  useEffect(() => {
    if (params.current === null) params.current = parseCallbackParams(window.location.search);
    window.history.replaceState(null, "", CALLBACK_PATH);
    const { code, state, error } = params.current;
    const returnTo = readReturnTo();
    if (error === "access_denied") {
      clearReturnTo();
      toast(CANCELLED, { id: "gmail-callback" });
      router.replace(returnTo);
      return;
    }
    if (error !== null) {
      setView({ kind: "failed", message: GOOGLE_REFUSED, canRetry: true });
      return;
    }
    if (code === null || state === null) {
      setView({ kind: "failed", message: NOT_FINISHED, canRetry: true });
      return;
    }
    let active = true;
    connectGmailOnce(api.user, { code, state }).then(
      (status) => {
        if (!active) return;
        queryClient.setQueryData(keys.gmailConnection(), status);
        clearReturnTo();
        toast.success(CONNECTED, { id: "gmail-callback" });
        router.replace(returnTo);
      },
      (e: unknown) => {
        if (!active) return;
        reportAuthErrors(e, null);
        const notConfigured = e instanceof ApiError && e.code === "gmail_not_configured";
        setView({ kind: "failed", message: gmailErrorMessage(e), canRetry: !notConfigured });
      },
    );
    return () => {
      active = false;
    };
  }, [api, queryClient, router]);

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center p-4">
      <section aria-labelledby="gmail-callback-title" className="grid gap-4 rounded-lg border p-6">
        <h1 id="gmail-callback-title" className="text-lg font-semibold">
          Gmail
        </h1>
        {view.kind === "connecting" ? (
          <div role="status" className="flex items-start gap-2 text-sm">
            <Loader2Icon className="mt-0.5 size-4 shrink-0 animate-spin" aria-hidden="true" />
            <div className="grid gap-1">
              <p>{CONNECTING}</p>
              {slow ? <p className="text-muted-foreground">{STILL_CONNECTING}</p> : null}
            </div>
          </div>
        ) : (
          <>
            <p role="alert" className="text-sm">
              {view.message}
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              {view.canRetry ? (
                <PendingButton
                  size="touch"
                  pending={start.isPending}
                  pendingLabel="Opening Google…"
                  onClick={() => start.mutate({ returnTo: readReturnTo() })}
                >
                  Try again
                </PendingButton>
              ) : null}
              <Button variant="outline" size="touch" onClick={() => router.replace(readReturnTo())}>
                Go back
              </Button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
````

**Create `frontend/src/app/(signed-in)/gmail/callback/page.tsx`:**

````tsx
"use client";

import { GmailCallback } from "@/components/gmail/gmail-callback";

/**
 * `/gmail/callback`: where Google sends the browser back after Gmail's consent
 * screen (slice 5b-2; F §4.1). Signed in, outside the church shell: the Gmail
 * connection is the user's own, for every church.
 */
export default function GmailCallbackPage() {
  return <GmailCallback />;
}
````

- [ ] **Step 4: See them pass three times, and the suite**

Run: `(cd frontend && npx vitest run src/components/gmail 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (three times) then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
three times `      Tests  6 passed (6)`, with no `×`; ` Test Files  97 passed (97)` and `      Tests  793 passed (793)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/gmail/gmail-callback.tsx frontend/src/components/gmail/gmail-callback.test.tsx 'frontend/src/app/(signed-in)/gmail/callback/page.tsx'
git commit -q -m "Slice 5b-2: the /gmail/callback page" -m "Google's answer is read once, cleared from the address bar and history,
and posted once per state, even under StrictMode; the page shows
\"Connecting your Gmail…\" (never \"didn't finish\" during a connect),
then toasts \"Gmail connected\", seeds the status and goes back where the
connect started. A cancel at Google goes back with a note; another Google
error, a lost query or a server refusal shows its message with Try again
and Go back (only Go back when Gmail is not set up here)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1739 passed, 26 skipped`; frontend `793 passed` in 97 files.

### Task 9: Settings → Account (B "/settings/account"; S "Settings nav"; clarification 10)

**Files:**
- Create: `frontend/src/components/settings/account-settings-page.test.tsx`, `frontend/src/components/settings/account-settings-page.tsx`, `frontend/src/app/(signed-in)/(church)/settings/account/page.tsx`
- Modify: `frontend/src/test/fixtures/index.ts`, `frontend/src/components/settings/settings-layout.test.tsx`, `frontend/src/components/settings/sections.ts`

- [ ] **Step 1: Write the failing tests**

The fixtures gain `gmailConnection()` (connected as Pat, `pat@example.com`) and `gmailDisconnected()`, used here and on Review (T16). The page renders inside the Settings layout, as the route is.

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  ContactList,
````

**with:**

````ts
  ContactList,
  GmailConnection,
````

**Append to `frontend/src/test/fixtures/index.ts`:**

````ts

// --- slice 5b-2: the Gmail connection --------------------------------------------------------------

/** `GET /gmail-connection`: set up here and connected as Pat, unless overridden. */
export function gmailConnection(overrides: Partial<GmailConnection> = {}): GmailConnection {
  return { configured: true, connected: true, google_email: "pat@example.com", ...overrides };
}

/** Not connected yet (set up here). */
export function gmailDisconnected(): GmailConnection {
  return gmailConnection({ connected: false, google_email: null });
}
````

**Create `frontend/src/components/settings/account-settings-page.test.tsx`:**

````tsx
/**
 * Settings → Account (slice 5b spec, UX "/settings/account"; slice 5b-2): who
 * is signed in, Log out, and the Gmail card's five states. Rendered inside the
 * Settings layout, as the route is, with a Toaster. Leaving for Google is
 * `browser.assign`, spied (jsdom cannot navigate).
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AccountSettingsRoute from "@/app/(signed-in)/(church)/settings/account/page";
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import { Toaster } from "@/components/ui/sonner";
import { browser, GMAIL_RETURN_KEY } from "@/lib/gmail";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import { church, gmailConnection, gmailDisconnected, me } from "@/test/fixtures";
import { supabaseAuth } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { GMAIL_EVERY_CHURCH, GMAIL_INTRO, GMAIL_NOT_CONFIGURED, GMAIL_STATUS_ERROR, SIGNED_IN_WITH_GOOGLE } from "./account-settings-page";

const GOOGLE_URL = "https://accounts.google.com/o/oauth2/v2/auth?state=s1";
let assign: ReturnType<typeof vi.spyOn>;

function renderPage(routes: Record<string, FakeHandler> = {}) {
  const api = installFakeApi({ "GET /gmail-connection": gmailConnection(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <AccountSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me(), church: church({ role: "member" }), path: "/settings/account" },
  );
  return { ...view, api };
}

async function gmailCard() {
  return screen.findByRole("region", { name: "Gmail" });
}

beforeEach(() => {
  assign = vi.spyOn(browser, "assign").mockImplementation(() => {});
});

afterEach(() => {
  toast.dismiss();
});

describe("Settings → Account (slice 5b-2)", () => {
  it("shows who is signed in, and Log out signs out", async () => {
    const { user } = renderPage();
    const account = screen.getByRole("region", { name: "Account" });
    expect(within(account).getByText("Pat Pastor")).toBeInTheDocument();
    expect(within(account).getByText("pat@example.com")).toBeInTheDocument();
    expect(within(account).getByText(SIGNED_IN_WITH_GOOGLE)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Account" })).toHaveAttribute("aria-current", "page");
    await user.click(within(account).getByRole("button", { name: "Log out" }));
    await waitFor(() => expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1));
  });

  it("shows the connected address, and Disconnect shows the Connect button with no toast", async () => {
    const { api, user } = renderPage({ "DELETE /gmail-connection": gmailDisconnected() });
    const card = await gmailCard();
    expect(await within(card).findByText("pat@example.com")).toBeInTheDocument();
    expect(card).toHaveTextContent("Connected as pat@example.com.");
    expect(within(card).getByText(GMAIL_EVERY_CHURCH)).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Disconnect" }));
    expect(await within(card).findByRole("button", { name: "Connect Gmail" })).toBeInTheDocument();
    expect(within(card).getByText(GMAIL_INTRO)).toBeInTheDocument();
    expect(GMAIL_INTRO).toBe(
      "Connect the Gmail account you sign in with. The app gets permission only to send email for you; it can't read your mail.",
    ); // 5b-2a: true before emailing exists (5b-2b says what it is for)
    expect(api.requests.filter((r) => r.method === "DELETE").map((r) => r.path)).toEqual(["/gmail-connection"]);
    expect(api.requests.find((r) => r.path === "/gmail-connection")?.headers["x-church-id"]).toBeUndefined();
    expect(document.querySelectorAll("[data-sonner-toast]")).toHaveLength(0);
  });

  it("Connect Gmail leaves for Google in this tab, to come back to Account", async () => {
    const { api, user } = renderPage({
      "GET /gmail-connection": gmailDisconnected(),
      "POST /gmail-connection/auth-url": { auth_url: GOOGLE_URL },
    });
    const card = await gmailCard();
    await user.click(await within(card).findByRole("button", { name: "Connect Gmail" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(GOOGLE_URL));
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBe("/settings/account");
    expect(api.requests.filter((r) => r.method === "POST").map((r) => r.path)).toEqual(["/gmail-connection/auth-url"]);
  });

  it("refuses a consent URL that is not Google's", async () => {
    const { user } = renderPage({
      "GET /gmail-connection": gmailDisconnected(),
      "POST /gmail-connection/auth-url": { auth_url: "https://evil.example/consent" },
    });
    const card = await gmailCard();
    await user.click(await within(card).findByRole("button", { name: "Connect Gmail" }));
    expect(await screen.findByText("Something went wrong.")).toBeInTheDocument();
    expect(assign).not.toHaveBeenCalled();
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBeNull();
  });

  it("says when Gmail is not set up here, with no button", async () => {
    renderPage({ "GET /gmail-connection": gmailConnection({ configured: false, connected: false, google_email: null }) });
    const card = await gmailCard();
    expect(await within(card).findByText(GMAIL_NOT_CONFIGURED)).toBeInTheDocument();
    expect(within(card).queryByRole("button")).toBeNull();
  });

  it("shows a failed check with Retry, and a failed disconnect is toasted", async () => {
    let fail = true;
    const { user } = renderPage({
      "GET /gmail-connection": () => (fail ? fakeError(500, "internal_error", "Something went wrong.") : gmailConnection()),
      "DELETE /gmail-connection": fakeError(500, "internal_error", "Something went wrong."),
    });
    const card = await gmailCard();
    expect(await within(card).findByText(GMAIL_STATUS_ERROR)).toBeInTheDocument();
    fail = false;
    await user.click(within(card).getByRole("button", { name: "Retry" }));
    await user.click(await within(card).findByRole("button", { name: "Disconnect" }));
    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
  });
});
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    ]);
    expect(links[0]).toHaveAttribute("aria-current", "page");
    expect(links[1]).not.toHaveAttribute("aria-current");
    expect(links[2]).not.toHaveAttribute("aria-current");
````

**with:**

````tsx
      ["Account", "/settings/account"],
    ]);
    expect(links[0]).toHaveAttribute("aria-current", "page");
    for (const link of links.slice(1)) expect(link).not.toHaveAttribute("aria-current");
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
  it("marks Contacts current on its page (slice 5b-1)", () => {
    renderShell("member", "/settings/contacts");
    const links = within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link");
    expect(links.filter((link) => link.getAttribute("aria-current") === "page").map((link) => link.textContent)).toEqual([
      "Contacts",
````

**with:**

````tsx
  it.each([
    ["/settings/contacts", "Contacts"],
    ["/settings/account", "Account"],
  ])("marks the section current on its page (slices 5b-1, 5b-2): %s", (path, label) => {
    renderShell("member", path);
    const links = within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link");
    expect(links.filter((link) => link.getAttribute("aria-current") === "page").map((link) => link.textContent)).toEqual([
      label,
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(3);
````

**with:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(4);
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/account-settings-page.test.tsx src/components/settings/settings-layout.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the page does not exist yet; the nav has three sections):
```
   × the Settings area (slice 6a-1) > shows the heading, who you are in the church, and the sections with the current one marked <t>ms
   × the Settings area (slice 6a-1) > marks the section current on its page (slices 5b-1, 5b-2): /settings/account <t>ms
   × the Settings area (slice 6a-1) > shows a member the same sections, and /settings opens Church <t>ms
 FAIL  |dom| src/components/settings/account-settings-page.test.tsx [ src/components/settings/account-settings-page.test.tsx ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 3 ⎯⎯⎯⎯⎯⎯⎯
      Tests  3 failed | 1 passed (4)
```

- [ ] **Step 3: Write the page, its route and the nav entry**

**Create `frontend/src/components/settings/account-settings-page.tsx`:**

````tsx
"use client";

import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useSignOut } from "@/lib/auth";
import { useMeContext } from "@/lib/me-context";
import { useDisconnectGmail, useGmailConnection, useStartGmailConnect } from "@/lib/queries/gmail";
import { safeHttpsUrl } from "@/lib/urls";

export const SIGNED_IN_WITH_GOOGLE = "Signed in with Google.";
export const GMAIL_STATUS_ERROR = "Couldn't check your Gmail connection.";
export const GMAIL_NOT_CONFIGURED = "Per-user Gmail sending isn't configured on this deployment.";
export const GMAIL_INTRO =
  "Connect the Gmail account you sign in with. The app gets permission only to send email for you; it can't read your mail.";
export const GMAIL_EVERY_CHURCH = "Works in all your churches.";
const ACCOUNT_PATH = "/settings/account";

/**
 * `/settings/account` (slice 5b spec, UX "/settings/account"; slice 5b-2): who
 * is signed in, with **Log out**, and the user's own Gmail connection, which
 * works in every church they belong to. Everyone sees the same page.
 */
export function AccountSettingsPage() {
  return (
    <section aria-labelledby="account-title" className="grid gap-4">
      <h2 id="account-title" className="text-lg font-semibold">
        Account
      </h2>
      <AccountCard />
      <GmailConnectionCard />
    </section>
  );
}

function AccountCard() {
  const { user } = useMeContext();
  const signOut = useSignOut();
  const name = user.name ?? user.email;
  const picture = safeHttpsUrl(user.picture);
  return (
    <div className="grid gap-4 rounded-lg border p-4">
      <div className="flex min-w-0 items-center gap-3">
        <Avatar className="size-11">
          {picture ? <AvatarImage src={picture} alt="" /> : null}
          <AvatarFallback>{name.slice(0, 1).toUpperCase()}</AvatarFallback>
        </Avatar>
        <div className="grid min-w-0 gap-0.5">
          <p className="font-medium break-words">{name}</p>
          <p className="text-sm text-muted-foreground break-all">{user.email}</p>
        </div>
      </div>
      <p className="text-sm text-muted-foreground">{SIGNED_IN_WITH_GOOGLE}</p>
      <Button variant="outline" size="touch" className="w-full sm:w-fit" onClick={() => void signOut()}>
        Log out
      </Button>
    </div>
  );
}

/**
 * The Gmail card: loading, a failed check (Retry), not set up on this
 * deployment, not connected (**Connect Gmail**, which leaves for Google in
 * this tab and comes back here), connected (the address, **Disconnect**, no
 * confirmation: connecting again is one tap).
 */
function GmailConnectionCard() {
  const status = useGmailConnection();
  const start = useStartGmailConnect();
  const disconnect = useDisconnectGmail();
  let body;
  if (status.data) {
    const { configured, connected, google_email } = status.data;
    if (!configured) {
      body = <p className="text-sm">{GMAIL_NOT_CONFIGURED}</p>;
    } else if (connected) {
      body = (
        <>
          <div className="grid gap-1 text-sm">
            <p className="break-all">
              Connected as <strong>{google_email}</strong>.
            </p>
            <p className="text-muted-foreground">{GMAIL_EVERY_CHURCH}</p>
          </div>
          <PendingButton
            variant="outline"
            size="touch"
            className="w-full sm:w-fit"
            pending={disconnect.isPending}
            pendingLabel="Disconnecting…"
            onClick={() => disconnect.mutate()}
          >
            Disconnect
          </PendingButton>
        </>
      );
    } else {
      body = (
        <>
          <p className="text-sm">{GMAIL_INTRO}</p>
          <PendingButton
            size="touch"
            className="w-full sm:w-fit"
            pending={start.isPending}
            pendingLabel="Opening Google…"
            onClick={() => start.mutate({ returnTo: ACCOUNT_PATH })}
          >
            Connect Gmail
          </PendingButton>
        </>
      );
    }
  } else if (status.isError) {
    body = (
      <ErrorState
        message={GMAIL_STATUS_ERROR}
        error={status.error}
        onRetry={() => void status.refetch()}
        retrying={status.isFetching}
      />
    );
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }
  return (
    <section aria-labelledby="gmail-title" className="grid gap-4 rounded-lg border p-4">
      <h3 id="gmail-title" className="text-base font-medium">
        Gmail
      </h3>
      {body}
    </section>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/account/page.tsx`:**

````tsx
"use client";

import { AccountSettingsPage } from "@/components/settings/account-settings-page";

/** Settings → Account: who is signed in, and their own Gmail connection (slice 5b-2; F §4.1). */
export default function AccountSettingsRoute() {
  return <AccountSettingsPage />;
}
````

**In `frontend/src/components/settings/sections.ts`, replace:**

````ts
 * under /settings); 5b-1 adds Contacts, last for now (the final order puts it
 * after every page about the church's services), and 5b-2 Account after it.
````

**with:**

````ts
 * under /settings); 5b-1 adds Contacts (the final order puts it after every
 * page about the church's services) and 5b-2 Account after it (6b's People
 * will go between them).
````

**In `frontend/src/components/settings/sections.ts`, replace:**

````ts
  { href: "/settings/contacts", label: "Contacts" },
````

**with:**

````ts
  { href: "/settings/contacts", label: "Contacts" },
  { href: "/settings/account", label: "Account" },
````

- [ ] **Step 4: See them pass, and the suite**

Run: `(cd frontend && npx vitest run src/components/settings src/components/app/app-header.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
`      Tests  44 passed (44)`; ` Test Files  98 passed (98)` and `      Tests  800 passed (800)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/account-settings-page.tsx frontend/src/components/settings/account-settings-page.test.tsx 'frontend/src/app/(signed-in)/(church)/settings/account/page.tsx' frontend/src/components/settings/sections.ts frontend/src/components/settings/settings-layout.test.tsx frontend/src/test/fixtures/index.ts
git commit -q -m "Slice 5b-2: Settings → Account, with the Gmail connection" -m "A fourth Settings section, Account, after Contacts (the final order
puts People between them): who is signed in with Log out, and the Gmail
card: loading, a failed check with Retry, not set up here, Connect Gmail
(Google in this tab, then back here) and Connected as {address} with
Disconnect (no confirmation, no toast). Fixtures gmailConnection() and
gmailDisconnected()." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1739 passed, 26 skipped`; frontend `800 passed` in 98 files.

### Task 10: Docs: the connection's manual checks (clarification 23)

**Files:**
- Modify: `docs/manual-verification.md`

- [ ] **Step 1: Append the items**

Items 7-10 under "## Slice 5b" (no new heading, so `test_slice1_docs.py`'s pin of the last ten `##` headings stays).

**Append to `docs/manual-verification.md`:**

````markdown

**5b-2 (the Gmail connection and emailing the bulletin).** The owner's Google
and Railway setup comes before the merge (item 7). After the merge the
owner's guided check covers the items marked "(owner, after 5b-2)", one step
at a time on the phone; the results go into `docs/ops-runbook.md` → "Slice
5b-2 record". Every test email goes only to the owner's own addresses. Record
what the page shows, never an email address, a token, a code from the
address bar or a church id.

- [ ] (owner, before the 5b-2 merge) **7.** Google Cloud Console → the OAuth client "Liturgy" lists `https://worship-service-builder.vercel.app/gmail/callback` and `http://localhost:3000/gmail/callback` under Authorized redirect URIs, and the consent screen's publishing status is noted (Testing or In production). Railway → the API service → Variables has `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` (Streamlit's) and `GOOGLE_OAUTH_REDIRECT_URI` = `https://worship-service-builder.vercel.app/gmail/callback`; after the deploy the log has the line `Gmail: configured` and no other line starting `Gmail:`.
- [ ] (owner, after 5b-2) **8.** **Settings** lists **Church**, **Bulletin**, **Contacts** and **Account**. **Account** shows your name, your email, "Signed in with Google.", **Log out** and the **Gmail** card. If it says "Connected as …", tap **Disconnect** first ("Connect Gmail" shows). Tap **Connect Gmail**: Google opens in the same tab with your account chosen; allow sending; you are back on **Account** with "Gmail connected" and "Connected as" your address. At 375 px the four section links are easy to tap and nothing scrolls sideways.
- [ ] **9.** On **Account**, **Connect Gmail** and then Cancel at Google: "Gmail connection was cancelled." and back on **Account**.
- [ ] **10.** After a successful connect, reload `/gmail/callback`: "Gmail connection didn't finish. Try connecting again."; **Account** still says "Connected as …".
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected:**
`89 passed in <t>s`; `4`; `0`; ` 1 file changed, 13 insertions(+)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md
git commit -q -m "Docs: slice 5b-2 manual checks for the Gmail connection" -m "docs/manual-verification.md → Slice 5b gains items 7-10: the owner's
Google and Railway setup before the merge (the redirect URIs, the consent
screen's status, the three variables, the \"Gmail: configured\" line),
connecting from Settings → Account, a cancel at Google and a reload of
/gmail/callback." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1739 passed, 26 skipped`; frontend `800 passed` in 98 files.


## Group B: emailing the bulletin (T11-T17)

### Task 11: `dedupe_addresses` and the bulletin email message (B "service_output.py additions", "`email_addresses.normalize_address`"; clarification 11)

**Files:**
- Create: `backend/tests/fixtures/shared/bulletin_email.json`, `backend/tests/test_bulletin_email.py`, `backend/bulletin_email.py`
- Modify: `backend/tests/test_email_addresses.py`, `backend/tests/test_no_streamlit_in_core.py`, `backend/email_addresses.py`

- [ ] **Step 1: Write the shared cases and the failing tests**

The composed message is read back as a mail client would (`message_from_bytes` with the default policy): the headers, the stripped body, each attachment's name, type and bytes, and no defect.

**Create `backend/tests/fixtures/shared/bulletin_email.json`:**

````json
{
  "_about": "The bulletin email's subject and default message for a service date (slice 5b-2; 5b spec amended 2026-10-06: no zero padding, no dash). backend/tests/test_bulletin_email.py runs each case through bulletin_email.bulletin_email_subject and default_bulletin_message; frontend/src/lib/email.test.ts through bulletinEmailSubject and defaultBulletinMessage, so the dialog shows exactly what is sent.",
  "cases": [
    {"date_iso": "2026-10-04", "subject": "Worship service for October 4, 2026", "default_message": "Hi! Here's the worship bulletin for this Sunday."},
    {"date_iso": "2026-11-01", "subject": "Worship service for November 1, 2026", "default_message": "Hi! Here's the worship bulletin for this Sunday."},
    {"date_iso": "2026-12-20", "subject": "Worship service for December 20, 2026", "default_message": "Hi! Here's the worship bulletin for this Sunday."},
    {"date_iso": "2026-12-24", "subject": "Worship service for December 24, 2026", "default_message": "Hi! Here's the worship bulletin for Thursday, December 24."},
    {"date_iso": "2027-02-10", "subject": "Worship service for February 10, 2027", "default_message": "Hi! Here's the worship bulletin for Wednesday, February 10."},
    {"date_iso": "2027-04-02", "subject": "Worship service for April 2, 2027", "default_message": "Hi! Here's the worship bulletin for Friday, April 2."}
  ]
}
````

**Create `backend/tests/test_bulletin_email.py`:**

````python
"""bulletin_email (slice 5b spec, "service_output.py additions" and Testing
"test_service_output_email.py"; slice 5b-2): the subject, the default message,
who goes in To and Bcc, and the composed message read back as a mail client
would. The subject and message cases are the shared fixture the frontend's
email.test.ts reads too."""
import datetime
import json
from email import message_from_bytes, policy
from pathlib import Path

import pytest

import bulletin_email
from bulletin_email import Attachment
from printed_bulletin import PDF_MIME
from service_output import DOCX_MIME

CASES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "bulletin_email.json").read_text(encoding="utf-8"))
SENDER = "pastor@example.org"
SUNDAY = datetime.date(2026, 10, 4)
DOCX = Attachment(b"PK\x03\x04docx", "worship_October_04_2026.docx", DOCX_MIME)
PDF = Attachment(b"%PDF-1.7 printed", "printed_bulletin_October_04_2026.pdf", PDF_MIME)


@pytest.mark.parametrize("case", CASES["cases"], ids=lambda case: case["date_iso"])
def test_subject_and_default_message_match_the_shared_fixture(case):
    d = datetime.date.fromisoformat(case["date_iso"])
    assert bulletin_email.bulletin_email_subject(d) == case["subject"]
    assert bulletin_email.default_bulletin_message(d) == case["default_message"]


@pytest.mark.parametrize("recipients, to, bcc", [
    (["mary@example.org"], ("mary@example.org",), ()),
    (["mary@example.org", "office@example.org", "organist@example.org"],
     (SENDER,), ("mary@example.org", "office@example.org", "organist@example.org")),
    (["mary@example.org", "Pastor@Example.org"], (SENDER,), ("mary@example.org",)),
    ([SENDER], (SENDER,), ()),
])
def test_one_recipient_is_in_to_and_several_are_in_bcc_with_the_sender_in_to(recipients, to, bcc):
    assert bulletin_email.plan_bulletin_addressing(SENDER, recipients) == bulletin_email.Addressing(to, bcc)


def _compose(recipients, message=None, attachments=(DOCX,)):
    composed = bulletin_email.compose_bulletin_email(sender=SENDER, recipients=recipients, service_date=SUNDAY,
                                                     message=message, attachments=attachments)
    return message_from_bytes(composed.as_bytes(), policy=policy.default)


def test_the_message_reads_back_with_its_headers_body_and_attachments():
    parsed = _compose(["mary@example.org", "office@example.org"], "  Here it is.\nSee you Sunday.  ", (DOCX, PDF))
    assert (parsed["From"], parsed["To"], parsed["Bcc"]) == (SENDER, SENDER, "mary@example.org, office@example.org")
    assert parsed["Subject"] == "Worship service for October 4, 2026"
    assert parsed.get_body(preferencelist=("plain",)).get_content() == "Here it is.\nSee you Sunday.\n"
    files = [(part.get_filename(), part.get_content_type(), part.get_content()) for part in parsed.iter_attachments()]
    assert files == [("worship_October_04_2026.docx", DOCX_MIME, b"PK\x03\x04docx"),
                     ("printed_bulletin_October_04_2026.pdf", PDF_MIME, b"%PDF-1.7 printed")]
    assert parsed.defects == []


def test_one_recipient_has_no_bcc_and_a_blank_message_gets_the_default():
    for blank in (None, "", "   \n "):
        parsed = _compose(["mary@example.org"], blank, (PDF,))
        assert (parsed["To"], parsed["Bcc"]) == ("mary@example.org", None)
        assert parsed.get_body(preferencelist=("plain",)).get_content() == (
            "Hi! Here's the worship bulletin for this Sunday.\n")
        assert [part.get_filename() for part in parsed.iter_attachments()] == ["printed_bulletin_October_04_2026.pdf"]
````

**In `backend/tests/test_email_addresses.py`, replace:**

````python
from email_addresses import InvalidAddress, normalize_address
````

**with:**

````python
from email_addresses import InvalidAddress, dedupe_addresses, normalize_address
````

**Append to `backend/tests/test_email_addresses.py`:**

````python


# --- slice 5b-2: dedupe_addresses -----------------------------------------------------------------

def test_dedupe_keeps_the_first_of_each_address_ignoring_case():
    assert dedupe_addresses(["Mary@example.org", "office@example.org", "mary@EXAMPLE.org", "office@example.org",
                             "organist@example.org"]) == ["Mary@example.org", "office@example.org", "organist@example.org"]
    assert dedupe_addresses([]) == []
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth, usecases.email; "
````

**with:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth, usecases.email, bulletin_email; "
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_bulletin_email.py 2>&1 | tail -3` then `.venv/bin/python -m pytest -q backend/tests/test_email_addresses.py 2>&1 | tail -3`
**Expected** (`bulletin_email` and `dedupe_addresses` do not exist yet):
```
ERROR backend/tests/test_bulletin_email.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
ERROR backend/tests/test_email_addresses.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: Write the module and the de-duplication**

**In `backend/email_addresses.py`, replace:**

````python
import re
````

**with:**

````python
import re
from collections.abc import Iterable
````

**Append to `backend/email_addresses.py`:**

````python


def dedupe_addresses(addresses: Iterable[str]) -> list[str]:
    """The addresses in order, each once: a later copy (in any capitalization) is
    dropped and the first spelling kept (slice 5b-2: a contact also typed under
    Other addresses is emailed once)."""
    seen: set[str] = set()
    kept: list[str] = []
    for address in addresses:
        key = address.lower()
        if key not in seen:
            seen.add(key)
            kept.append(address)
    return kept
````

**Create `backend/bulletin_email.py`:**

````python
"""The bulletin email itself (slice 5b spec, "service_output.py additions",
amended 2026-10-06; slice 5b-2). Pure: no database, no network, no FastAPI,
Starlette or Streamlit.

- bulletin_email_subject: "Worship service for October 4, 2026" (the printed
  bulletin's date form, no zero padding; owner answer 5).
- default_bulletin_message: "Hi! Here's the worship bulletin for this Sunday.",
  or "... for Wednesday, February 10." for a service on another day. The
  dialog prefills it, and a message left blank is sent as it.
- plan_bulletin_addressing: one recipient is in To; two or more are in Bcc
  with the sender in To (owner decision 9), the sender never twice.
- compose_bulletin_email: the plain-text message with its attachments (the
  bulletin copy's Word file and/or the printed bulletin's PDF).
Every header holds only addresses email_addresses.normalize_address accepted
and strings built here, so there is no header injection.
The shared fixture tests/fixtures/shared/bulletin_email.json pins the subject
and the message for frontend/src/lib/email.ts too.
"""
from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Optional

from printed_bulletin import printed_date
from service_output import MONTHS

WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
BULLETIN_EMAIL_FALLBACK = "Hi! Here's the worship bulletin for this Sunday."


@dataclass(frozen=True)
class Addressing:
    to: tuple[str, ...]
    bcc: tuple[str, ...]


@dataclass(frozen=True)
class Attachment:
    content: bytes
    filename: str
    mime_type: str


def bulletin_email_subject(d: datetime.date) -> str:
    return f"Worship service for {printed_date(d)}"


def default_bulletin_message(d: datetime.date) -> str:
    if d.weekday() == 6:
        return BULLETIN_EMAIL_FALLBACK
    return f"Hi! Here's the worship bulletin for {WEEKDAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}."


def plan_bulletin_addressing(sender: str, recipients: Sequence[str]) -> Addressing:
    """`recipients` already checked and without duplicates."""
    if len(recipients) == 1:
        return Addressing(to=(recipients[0],), bcc=())
    return Addressing(to=(sender,), bcc=tuple(r for r in recipients if r.lower() != sender.lower()))


def compose_bulletin_email(*, sender: str, recipients: Sequence[str], service_date: datetime.date,
                           message: Optional[str], attachments: Sequence[Attachment]) -> EmailMessage:
    plan = plan_bulletin_addressing(sender, recipients)
    composed = EmailMessage()
    composed["From"] = sender
    composed["To"] = ", ".join(plan.to)
    if plan.bcc:
        composed["Bcc"] = ", ".join(plan.bcc)
    composed["Subject"] = bulletin_email_subject(service_date)
    composed.set_content((message or "").strip() or default_bulletin_message(service_date))
    for attachment in attachments:
        maintype, subtype = attachment.mime_type.split("/", 1)
        composed.add_attachment(attachment.content, maintype=maintype, subtype=subtype, filename=attachment.filename)
    return composed
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_bulletin_email.py backend/tests/test_email_addresses.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`118 passed in <t>s`; `1765 passed, 27 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/bulletin_email.py backend/email_addresses.py backend/tests/fixtures/shared/bulletin_email.json backend/tests/test_bulletin_email.py backend/tests/test_email_addresses.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Slice 5b-2: the bulletin email's subject, message, To and Bcc" -m "bulletin_email.py (pure): \"Worship service for October 4, 2026\", the
default message (\"this Sunday\", or the weekday and date for another
day), one recipient in To or several in Bcc with the sender in To, and
the plain-text MIME message with its attachments. The shared fixture
bulletin_email.json pins the subject and the message for the frontend
too. email_addresses.dedupe_addresses keeps the first spelling of each
address, ignoring case." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1765 passed, 27 skipped`; frontend `801 passed` in 98 files.

### Task 12: Idempotency keeps an uncertain send; the contacts a send names (B §Errors "Stored", "Modules" `email_contacts.py`; clarifications 13 and 14)

**Files:**
- Modify: `backend/tests/test_idempotency.py`, `backend/tests/test_email_contacts.py`, `backend/api/idempotency.py`, `backend/email_contacts.py`

- [ ] **Step 1: Write the failing tests**

**In `backend/tests/test_idempotency.py`, replace:**

````python
from domain_errors import Busy, Conflict, DomainError, RateLimited
````

**with:**

````python
from domain_errors import Busy, Conflict, DomainError, RateLimited, UpstreamTimeout
````

**Append to `backend/tests/test_idempotency.py`:**

````python


# --- slice 5b-2: store_error (an uncertain send's 5xx is kept for the retry) ----------------------

def _uncertain(_n):
    raise UpstreamTimeout("Gmail didn't confirm the email.", code="upstream_timeout",
                          details={"send_uncertain": True})


def _kept(error: DomainError) -> bool:
    return bool((error.details or {}).get("send_uncertain"))


def test_store_error_keeps_a_5xx_it_accepts_and_replays_it():
    store, calls = IdempotencyStore(), []
    first = _direct(store, calls, call=lambda: _uncertain(calls.append(1)), store_error=_kept)
    again = _direct(store, calls, call=lambda: _uncertain(calls.append(1)), store_error=_kept)
    assert first.status_code == again.status_code == 504
    assert bytes(again.body) == bytes(first.body) and again.headers[REPLAYED_HEADER] == "true"
    assert len(calls) == 1


def test_store_error_saying_no_or_left_out_keeps_slice_1s_rule():
    for store_error in (None, lambda error: False):
        store, calls = IdempotencyStore(), []
        for _ in range(2):
            r = _direct(store, calls, call=lambda: _uncertain(calls.append(1)), store_error=store_error)
            assert r.status_code == 504 and REPLAYED_HEADER.lower() not in r.headers
        assert len(calls) == 2 and len(store) == 0


def test_store_error_never_keeps_a_rate_limit():
    store, calls = IdempotencyStore(), []

    def limited():
        calls.append(1)
        raise RateLimited("Too many requests. Try again in 5 seconds.", retry_after_seconds=5)

    for _ in range(2):
        assert _direct(store, calls, call=limited, store_error=lambda error: True).status_code == 429
    assert len(calls) == 2 and len(store) == 0
````

**Append to `backend/tests/test_email_contacts.py`:**

````python


# --- slice 5b-2: the contacts a send names --------------------------------------------------------

def test_get_contacts_by_ids_returns_the_churchs_contacts_in_the_order_asked(tmp_db, make_user, make_church):
    u = make_user(email="c9@x.org")
    a = make_church(name="A", owner_user_id=u)
    b = make_church(name="B", owner_user_id=u)
    mary = add_contact(a, name="Mary", email="mary@x.org")["id"]
    office = add_contact(a, name="", email="office@x.org")["id"]
    theirs = add_contact(b, name="Theirs", email="theirs@x.org")["id"]
    found = email_contacts.get_contacts_by_ids(a, [office, theirs, mary, office])
    assert [(c["id"], c["name"], c["email"]) for c in found] == [(office, "", "office@x.org"), (mary, "Mary", "mary@x.org")]
    assert email_contacts.get_contacts_by_ids(a, []) == []
    with session_scope() as s:
        assert [c["id"] for c in email_contacts.get_contacts_by_ids(b, [theirs, mary], session=s)] == [theirs]
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_idempotency.py backend/tests/test_email_contacts.py 2>&1 | tail -3`
**Expected** (`run_idempotent` takes no `store_error` yet; `get_contacts_by_ids` does not exist):
```
FAILED backend/tests/test_idempotency.py::test_store_error_never_keeps_a_rate_limit
FAILED backend/tests/test_email_contacts.py::test_get_contacts_by_ids_returns_the_churchs_contacts_in_the_order_asked
4 failed, 26 passed in <t>s
```

- [ ] **Step 3: Add `store_error` and `get_contacts_by_ids`**

**In `backend/api/idempotency.py`, replace:**

````python
after Retry-After). Never a 5xx: a 5xx DomainError drops the entry, and any
````

**with:**

````python
after Retry-After). A 5xx DomainError drops the entry, unless the route's
`store_error` says to keep it (slice 5b-2: an email that may already have
been sent is answered "check your Sent folder" again, never sent twice); any
````

**In `backend/api/idempotency.py`, replace:**

````python
    store: Optional[IdempotencyStore] = None,
````

**with:**

````python
    store: Optional[IdempotencyStore] = None,
    store_error: Optional[Callable[[DomainError], bool]] = None,
````

**In `backend/api/idempotency.py`, replace:**

````python
    Slice 5b adds a `store_error` keyword (F §1.6).
````

**with:**

````python
    `store_error` (slice 5b-2): a 5xx DomainError for which it returns True is
    stored and replayed like a 4xx; a RateLimited never is.
````

**In `backend/api/idempotency.py`, replace:**

````python
                if 400 <= exc.status < 500 and not isinstance(exc, RateLimited):
````

**with:**

````python
                kept = 400 <= exc.status < 500 or (exc.status >= 500 and store_error is not None and store_error(exc))
                if kept and not isinstance(exc, RateLimited):
````

**In `backend/email_contacts.py`, replace:**

````python

def get_contacts_for_display(church_id) -> List[Dict[str, str]]:
````

**with:**

````python

def get_contacts_by_ids(church_id, ids, *, session: Optional[Session] = None) -> List[Dict[str, Any]]:
    """The church's contacts among `ids`, in the order of `ids`, each once (slice
    5b-2: the contacts a bulletin email names). An id the church has no contact
    for (another church's included) is simply missing from the answer."""
    if session is None:
        with session_scope() as own:
            return get_contacts_by_ids(church_id, ids, session=own)
    wanted = list(dict.fromkeys(as_uuid(i) for i in ids))
    if not wanted:
        return []
    rows = session.execute(
        select(Contact).where(Contact.church_id == as_uuid(church_id), Contact.id.in_(wanted))
    ).scalars().all()
    by_id = {c.id: c for c in rows}
    return [_to_dict(by_id[i]) for i in wanted if i in by_id]


def get_contacts_for_display(church_id) -> List[Dict[str, str]]:
````

- [ ] **Step 4: See them pass, the Streamlit tests, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_idempotency.py backend/tests/test_email_contacts.py streamlit_tests 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`65 passed in <t>s` (the two files' 30 and the 35 `streamlit_tests`); `1769 passed, 27 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/api/idempotency.py backend/email_contacts.py backend/tests/test_idempotency.py backend/tests/test_email_contacts.py
git commit -q -m "Slice 5b-2: run_idempotent's store_error, and the contacts a send names" -m "run_idempotent(store_error=...) stores and replays a 5xx DomainError the
route chooses to keep (an email that may already have been sent), never a
rate limit; every other route is unchanged. email_contacts.
get_contacts_by_ids returns the church's contacts among the ids, in the
order asked, each once; another church's id is simply missing." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1769 passed, 27 skipped`; frontend `801 passed` in 98 files.

### Task 13: `send_bulletin_email` (B "usecases/email.py", §Errors, Testing "test_usecase_email.py"; clarifications 12, 14 and 15)

**Files:**
- Modify: `backend/tests/test_usecase_email.py`, `backend/usecases/email.py`

- [ ] **Step 1: Write the failing tests**

The `world` fixture fixes the files' bytes (python-docx output is not byte-reproducible); two tests undo that and build real ones: a deleted hymn and a blank custom label pass through unchanged and send nothing, and the emailed Word copy has the same `word/document.xml` as the download (with no hymn use recorded). One test watches the database pool while the fake Google answers: no connection is checked out during a Google call. Two cover the plan review's M4 and M2: Gmail refusing the account (a 401, or a 400 `failedPrecondition`) has its own message, keeps the connection and logs Google's reason name; a message over `MAX_RAW_BYTES` (lowered for the test) is a 422 on `attachments` with nothing charged or sent.

**In `backend/tests/test_usecase_email.py`, replace:**

````python
the Gmail connection (status, start, finish, disconnect) against
tests.fake_google; Task 12 adds the bulletin send. No network."""
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

import google_oauth
from db import session_scope
from db.models import GmailToken, OAuthState
from domain_errors import NotConfigured, Rejected, UpstreamError, UpstreamTimeout
from tests.fake_google import REFRESH_TOKEN, FakeGoogle, google_error
from usecases import email
````

**with:**

````python
the Gmail connection (status, start, finish, disconnect) and (Task 12) the
bulletin email, against tests.fake_google. No network."""
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile

import httpx
import pytest
from sqlalchemy import event

import email_contacts
import google_oauth
from db import session_scope
from db.models import GmailToken, HymnUsage, OAuthState
from domain_errors import Conflict, DomainError, InvalidInput, NotConfigured, NotFound, Rejected, UpstreamError, UpstreamTimeout
from repos.memberships import add_membership
from service_output import CustomElement
from tests.fake_google import REFRESH_TOKEN, FakeGoogle, gmail_error, google_error
from usecases import archive, documents, email
from usecases.liturgy import HymnRefData
````

**Append to `backend/tests/test_usecase_email.py`:**

````python


# --- Task 12: emailing the bulletin ----------------------------------------------------------------

SUNDAY = date(2026, 10, 4)
FIXED_DOCX = documents.DocumentResult(b"FIXED-DOCX", "worship_October_04_2026.docx")
FIXED_PDF = documents.DocumentResult(b"%PDF-FIXED", "printed_bulletin_October_04_2026.pdf")
SECRET_MESSAGE = "A private note for the organist."


@pytest.fixture
def world(owner, make_user, make_church, monkeypatch):
    """Grace with a member who sends (connected), two contacts, Google faked and
    the files fixed (python-docx output is not byte-reproducible)."""
    member = make_user(email="member@example.com")
    church = make_church(name="Grace", owner_user_id=owner)
    add_membership(member, church, "member")
    mary = email_contacts.add_contact(church, name="Mary", email="mary@example.org")["id"]
    office = email_contacts.add_contact(church, name="", email=" Office@Example.ORG ")["id"]
    google_oauth.save_user_token(member, "member@example.com", REFRESH_TOKEN)
    built = []
    monkeypatch.setattr(documents, "build_document", lambda *args: built.append(("docx", args)) or FIXED_DOCX)
    monkeypatch.setattr(documents, "build_printed",
                        lambda *args, charge: built.append(("pdf", args)) or charge(2) or FIXED_PDF)
    return {"church": church, "member": member, "mary": mary, "office": office, "built": built,
            "google": FakeGoogle(email="member@example.com").install(), "charged": [], "scripture": []}


def _send(world, contact_ids=(), extra=(), message=None, attachments=("docx",), config=CONFIG,
          data=None, user=None):
    return email.send_bulletin_email(
        world["church"], user or world["member"], data or archive.ServiceInput(service_date=SUNDAY),
        contact_ids=[uuid.UUID(c) if isinstance(c, str) else c for c in contact_ids], additional_emails=list(extra),
        message=message, attachments=list(attachments), translation="nrsvue", config=config,
        charge=lambda: world["charged"].append(1), charge_scripture=lambda parts: world["scripture"].append(parts))


def test_a_member_emails_the_bulletin_with_both_files_in_bcc(world):
    count = _send(world, [world["office"], world["mary"]], [" organist@example.org", "MARY@example.org"],
                  "  See you Sunday.  ", ("pdf", "docx"))
    assert count == 3
    (sent,) = world["google"].sent()
    assert (sent["From"], sent["To"]) == ("member@example.com", "member@example.com")
    assert sent["Bcc"] == "Office@example.org, mary@example.org, organist@example.org"
    assert sent["Subject"] == "Worship service for October 4, 2026"
    assert sent.get_body(preferencelist=("plain",)).get_content() == "See you Sunday.\n"
    assert [(p.get_filename(), p.get_content()) for p in sent.iter_attachments()] == [
        ("worship_October_04_2026.docx", b"FIXED-DOCX"), ("printed_bulletin_October_04_2026.pdf", b"%PDF-FIXED")]
    data = archive.ServiceInput(service_date=SUNDAY)
    assert world["built"] == [("docx", (world["church"], data, "bulletin")),
                              ("pdf", (world["church"], data, "pdf", "nrsvue"))]
    assert (world["charged"], world["scripture"]) == ([1], [2])
    refresh = world["google"].calls(google_oauth.TOKEN_URI, "refresh_token")
    assert world["google"].form(refresh[0])["refresh_token"] == REFRESH_TOKEN


def test_one_recipient_is_in_to_and_the_default_message_fills_a_blank_one(world):
    assert _send(world, [world["mary"]], message="   ") == 1
    (sent,) = world["google"].sent()
    assert (sent["To"], sent["Bcc"]) == ("mary@example.org", None)
    assert sent.get_body(preferencelist=("plain",)).get_content() == "Hi! Here's the worship bulletin for this Sunday.\n"
    assert [p.get_filename() for p in sent.iter_attachments()] == ["worship_October_04_2026.docx"]
    assert world["scripture"] == []                                     # no PDF: no readings fetched


@pytest.mark.parametrize("call, expected", [
    (lambda w: _send(w), (InvalidInput, "invalid_request",
                          "Please select at least one recipient or enter an email address.", "recipients")),
    (lambda w: _send(w, extra=[f"p{i}@example.org" for i in range(51)] + ["P0@example.org"] * 9),
     (InvalidInput, "invalid_request", "You can email at most 50 people at once.", "recipients")),
    (lambda w: _send(w, extra=["mary@example.org", "not an address, really, it is far too long to show"]),
     (InvalidInput, "invalid_request", "“not an address, really, it is far too long to show” isn't a valid email "
                                       "address.", "additional_emails")),
    (lambda w: _send(w, [uuid.uuid4()]),
     (NotFound, "not_found", "One of the selected contacts no longer exists. Refresh the list and try again.", None)),
    (lambda w: _send(w, [w["mary"]], attachments=()),
     (InvalidInput, "invalid_request", "Choose at least one attachment.", "attachments")),
], ids=["none", "51-after-dedupe", "bad-extra", "unknown-contact", "no-attachment"])
def test_recipient_and_attachment_errors_come_first_and_send_nothing(world, call, expected):
    with pytest.raises(DomainError) as failed:
        call(world)
    assert (type(failed.value), failed.value.code, failed.value.message, failed.value.field) == expected
    assert world["google"].requests == [] and world["built"] == [] and world["charged"] == []


def test_an_extra_address_is_shown_cut_to_60_characters(world):
    with pytest.raises(InvalidInput) as failed:
        _send(world, extra=["x" * 70])
    assert failed.value.message == f"“{'x' * 60}” isn't a valid email address."


def test_another_churchs_contact_is_not_found(world, make_church):
    other = make_church(name="Other", owner_user_id=world["member"])
    theirs = email_contacts.add_contact(other, name="Theirs", email="theirs@example.org")["id"]
    with pytest.raises(NotFound) as failed:
        _send(world, [world["mary"], theirs])
    assert failed.value.details == {"field": "contact_ids"}
    assert world["google"].requests == []


def test_a_saved_contact_the_rule_refuses_is_named_with_the_hint(world):
    two = email_contacts.add_contact(world["church"], name="", email="a@example.org, b@example.org")["id"]
    named = email_contacts.add_contact(world["church"], name="Two at once", email="c@example.org; d@example.org")["id"]
    for contact, label in ((two, "a@example.org, b@example.org"), (named, "Two at once")):
        with pytest.raises(InvalidInput) as failed:
            _send(world, [contact])
        assert (failed.value.field, failed.value.message) == (
            "contact_ids", f"The saved contact “{label}” has an invalid email address. "
                           "An admin can fix it in Settings → Contacts.")
    assert email.MALFORMED_CONTACT_HINT == "An admin can fix it in Settings → Contacts."


def test_not_configured_and_not_connected_come_after_the_recipients(world, make_user):
    with pytest.raises(InvalidInput):
        _send(world, config=UNCONFIGURED)                         # no recipients: that is said first
    with pytest.raises(NotConfigured) as failed:
        _send(world, [world["mary"]], config=UNCONFIGURED)
    assert failed.value.code == "gmail_not_configured"
    stranger = make_user(email="nogmail@example.com")
    no_address = make_user(email="noaddress@example.com")
    with session_scope() as s:
        s.add(GmailToken(user_id=no_address, google_email=None, refresh_token="r"))     # counts as not connected
    for user in (stranger, no_address):
        with pytest.raises(Conflict) as failed:
            _send(world, [world["mary"]], user=user)
        assert (failed.value.code, failed.value.message) == ("gmail_not_connected",
                                                             "Connect your Gmail first, then try again.")
    assert world["google"].requests == [] and world["charged"] == []


def test_the_services_own_errors_propagate_and_nothing_is_charged_or_sent(world, monkeypatch):
    monkeypatch.undo()                                             # the real build_document again
    hymn = archive.ServiceInput(service_date=SUNDAY, hymns={"response": HymnRefData(uuid.uuid4(), "Gone", 1, None)})
    with pytest.raises(NotFound) as failed:
        _send(world, [world["mary"]], data=hymn)
    assert (failed.value.message, failed.value.details) == (
        "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
        {"field": "hymns.response.hymn_id"})
    label = archive.ServiceInput(service_date=SUNDAY, custom_elements=(CustomElement("  ", "Text", "sermon"),))
    with pytest.raises(InvalidInput) as failed:
        _send(world, [world["mary"]], data=label)
    assert failed.value.field == "custom_elements.0.label"
    assert world["google"].requests == [] and world["charged"] == []


def test_a_real_bulletin_copy_is_the_same_document_as_the_download(world, monkeypatch):
    monkeypatch.undo()
    data = archive.ServiceInput(service_date=SUNDAY, occasion="World Communion Sunday", sermon_title="Living Water")
    _send(world, [world["mary"]], data=data, attachments=("docx", "pdf"))
    files = {p.get_filename(): p.get_content() for p in world["google"].sent()[0].iter_attachments()}
    direct = documents.build_document(world["church"], data, "bulletin").content
    with ZipFile(BytesIO(files["worship_October_04_2026.docx"])) as sent, ZipFile(BytesIO(direct)) as built:
        assert sent.read("word/document.xml") == built.read("word/document.xml")
    assert files["printed_bulletin_October_04_2026.pdf"].startswith(b"%PDF")
    with session_scope() as s:
        assert s.query(HymnUsage).count() == 0                     # emailing records no hymn use


def _connected(world) -> bool:
    return google_oauth.get_connection(world["member"]) is not None


@pytest.mark.parametrize("where, answer, expected", [
    ("refresh", google_error(400, "invalid_grant"),
     (UpstreamError, "gmail_send_failed", email.EXPIRED, {"disconnected": True, "send_uncertain": False}, False)),
    ("refresh", google_error(401, "unauthorized_client"),
     (NotConfigured, "gmail_not_configured", "Gmail sending isn't set up correctly on this deployment.", None, True)),
    ("refresh", httpx.Response(503),
     (UpstreamError, "gmail_send_failed", email.GMAIL_UNREACHABLE, {"disconnected": False, "send_uncertain": False},
      True)),
    ("refresh", httpx.Response(200, json={}),
     (UpstreamError, "gmail_send_failed", email.GMAIL_UNREACHABLE, {"disconnected": False, "send_uncertain": False},
      True)),
    ("refresh", httpx.ReadTimeout("slow"),
     (UpstreamTimeout, "upstream_timeout", email.GOOGLE_SLOW_NOTHING_SENT, None, True)),
    ("send", gmail_error(403, "insufficientPermissions"),
     (UpstreamError, "gmail_send_failed", email.NO_SEND_PERMISSION, {"disconnected": True, "send_uncertain": False},
      False)),
    ("send", gmail_error(429, "rateLimitExceeded"),
     (UpstreamError, "gmail_send_failed", email.SEND_LIMIT, {"disconnected": False, "send_uncertain": False}, True)),
    ("send", gmail_error(400, "invalidArgument"),
     (UpstreamError, "gmail_send_failed", email.SEND_REJECTED, {"disconnected": False, "send_uncertain": False}, True)),
    ("send", httpx.ConnectError("down"),
     (UpstreamError, "gmail_send_failed", email.GMAIL_UNREACHABLE, {"disconnected": False, "send_uncertain": False},
      True)),
    ("send", httpx.Response(503),
     (UpstreamError, "gmail_send_failed", email.MAYBE_SENT_PROBLEM, {"disconnected": False, "send_uncertain": True},
      True)),
    ("send", httpx.ReadTimeout("slow"),
     (UpstreamTimeout, "upstream_timeout", email.MAYBE_SENT_UNCONFIRMED, {"send_uncertain": True}, True)),
], ids=["refresh-invalid-grant", "refresh-client", "refresh-5xx", "refresh-no-token", "refresh-timeout",
        "send-scope", "send-limit", "send-4xx", "send-connect", "send-5xx", "send-read-timeout"])
def test_google_failures_map_to_their_message_and_keep_or_forget_the_connection(world, where, answer, expected):
    setattr(world["google"], where, answer)
    with pytest.raises(DomainError) as failed:
        _send(world, [world["mary"]])
    error = failed.value
    assert (type(error), error.code, error.message, error.details, _connected(world)) == expected
    assert world["charged"] == [1]


def test_gmail_refusing_the_account_has_its_own_message_and_its_reason_is_logged(world, caplog):
    assert email.ACCOUNT_REFUSED == ("Gmail won't send from this Google account. Nothing was sent. "
                                     "Check that you can send email in Gmail with it, then try again.")
    for answer, status, reason in ((gmail_error(401, "authError"), 401, "authError"),
                                   (gmail_error(400, "failedPrecondition", "FAILED_PRECONDITION"), 400,
                                    "failedPrecondition")):
        world["google"].send = answer
        with caplog.at_level(logging.INFO), pytest.raises(UpstreamError) as failed:
            _send(world, [world["mary"]])
        assert (failed.value.code, failed.value.message, failed.value.details) == (
            "gmail_send_failed", email.ACCOUNT_REFUSED, {"disconnected": False, "send_uncertain": False})
        assert f"outcome=account_refused status={status} google_error={reason}" in caplog.text
    assert _connected(world) and "SECRET-GOOGLE-TEXT" not in caplog.text


def test_a_message_too_large_for_gmail_is_refused_before_the_limit_and_google(world, monkeypatch):
    assert email.MAX_RAW_BYTES == 3_500_000
    monkeypatch.setattr(email, "MAX_RAW_BYTES", 100)
    with pytest.raises(InvalidInput) as failed:
        _send(world, [world["mary"]], attachments=("docx", "pdf"))
    assert (failed.value.field, failed.value.message) == (
        "attachments", "The attachments are too large to email. Try sending only the bulletin copy.")
    assert world["google"].requests == [] and world["charged"] == []


def test_a_connection_made_again_meanwhile_is_kept(world):
    def reconnect_then_refuse(_request):
        google_oauth.save_user_token(world["member"], "member@example.com", "refresh-new")   # in either app
        return google_error(400, "invalid_grant")

    world["google"].refresh = reconnect_then_refuse
    with pytest.raises(UpstreamError) as failed:
        _send(world, [world["mary"]])
    assert (failed.value.message, failed.value.details) == (
        "Your Gmail connection changed while sending. Nothing was sent. Try again.",
        {"disconnected": False, "send_uncertain": False})
    assert google_oauth.get_connection(world["member"]).refresh_token == "refresh-new"


def test_the_rate_limit_is_charged_once_after_the_files_and_before_google(world):
    order = []
    world["google"].refresh = lambda request: order.append("refresh") or httpx.Response(200, json={"access_token": "a"})
    email.send_bulletin_email(world["church"], world["member"], archive.ServiceInput(service_date=SUNDAY),
                              contact_ids=[uuid.UUID(world["mary"])], additional_emails=[], message=None,
                              attachments=["docx"], translation=None, config=CONFIG,
                              charge=lambda: order.append(("charge", len(world["built"]))))
    assert order == [("charge", 1), "refresh"]


def test_no_pooled_connection_is_held_while_google_is_called(world, tmp_db):
    out = []
    event.listen(tmp_db.pool, "checkout", lambda *a: out.append(1))
    event.listen(tmp_db.pool, "checkin", lambda *a: out.pop())

    def check(answer):
        def handler(_request):
            assert out == [], "a database connection was checked out during a Google call"
            return answer
        return handler

    world["google"].refresh = check(httpx.Response(200, json={"access_token": "a"}))
    world["google"].send = check(httpx.Response(200, json={"id": "m"}))
    assert _send(world, [world["mary"]]) == 1


def test_the_logs_carry_no_address_subject_message_or_token(world, caplog):
    with caplog.at_level(logging.DEBUG):
        _send(world, [world["mary"]], ["organist@example.org"], SECRET_MESSAGE)
        world["google"].send = httpx.Response(503)
        with pytest.raises(UpstreamError):
            _send(world, [world["office"]], message=SECRET_MESSAGE)
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert f"bulletin_email.sent church_id={world['church']} user_id={world['member']} recipients=2 bcc=True" in text
    for secret in ("mary@example.org", "organist@example.org", "ffice@example", "member@example.com",
                   "Worship service", SECRET_MESSAGE, REFRESH_TOKEN, "access-token"):
        assert secret not in text, secret
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_usecase_email.py 2>&1 | tail -3`
**Expected** (`email.EXPIRED` and the rest do not exist yet: an `AttributeError` at collection, above these lines):
```
ERROR backend/tests/test_usecase_email.py - AttributeError: module 'usecases....
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

- [ ] **Step 3: Write the send**

**In `backend/usecases/email.py`, replace:**

````python
Task 12 adds send_bulletin_email. Logs carry user ids and outcomes, never a
code, a state, a token or an address (F §2.5). No FastAPI, Starlette or
````

**with:**

````python
send_bulletin_email (Task 12) emails the bulletin from the caller's Gmail,
in the 5b spec's order (§Errors, "POST /bulletin-emails"): the recipients
(the church's contacts by id, the other addresses, each through
email_addresses.normalize_address, then de-duplicated: 1 to 50), the
attachments (at least one), the connection, the files built from the posted
service (5a's bulletin copy, the printed bulletin's PDF) and the message's
size (MAX_RAW_BYTES), the `email` rate limit (`charge`), and only then Google: the token refresh and the send, with
no database session open. A refused grant forgets the connection only if it
still holds the token that failed. A send that may have gone out is a 502 or
504 with details.send_uncertain, which the route keeps for a retry with the
same key. Nothing is recorded (hymn use is recorded on Save).

Logs carry ids, counts, outcomes and Google's error reason (a name such as
failedPrecondition), never a code, a state, a token, an address, the
subject, the message or Google's text (F §2.5). No FastAPI, Starlette or
````

**In `backend/usecases/email.py`, replace:**

````python
import uuid
from dataclasses import dataclass
from typing import Optional

import google_oauth
from db import session_scope
from domain_errors import DomainError, NotConfigured, Rejected, UpstreamError, UpstreamTimeout
from google_oauth import GoogleErrorKind, GoogleOAuthConfig, GoogleOAuthError
````

**with:**

````python
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Optional

import email_contacts
import google_oauth
import printed_bulletin
import service_output
from bulletin_email import Attachment, compose_bulletin_email
from db import session_scope
from domain_errors import (Conflict, DomainError, InvalidInput, NotConfigured, NotFound, Rejected, UpstreamError,
                           UpstreamTimeout)
from email_addresses import InvalidAddress, dedupe_addresses, normalize_address
from google_oauth import GmailConnection, GoogleErrorKind, GoogleOAuthConfig, GoogleOAuthError
from usecases import archive, documents
````

**Append to `backend/usecases/email.py`:**

````python


# --- emailing the bulletin (Task 12) ---------------------------------------------------------------

MAX_RECIPIENTS = 50
MALFORMED_CONTACT_HINT = "An admin can fix it in Settings → Contacts."
CONTACT_GONE = "One of the selected contacts no longer exists. Refresh the list and try again."
MALFORMED_CONTACT = "The saved contact “{label}” has an invalid email address. " + MALFORMED_CONTACT_HINT
BAD_ADDRESS = "“{value}” isn't a valid email address."
NO_RECIPIENTS = "Please select at least one recipient or enter an email address."
TOO_MANY = f"You can email at most {MAX_RECIPIENTS} people at once."
NO_ATTACHMENT = "Choose at least one attachment."
NOT_CONNECTED = "Connect your Gmail first, then try again."
EXPIRED = "Your Gmail connection has expired or was removed. Reconnect Gmail and try again."
NO_SEND_PERMISSION = "Your Gmail connection no longer allows sending. Reconnect Gmail and try again."
CHANGED = "Your Gmail connection changed while sending. Nothing was sent. Try again."
GMAIL_UNREACHABLE = "Couldn't reach Gmail. Nothing was sent. Try again in a minute."
GOOGLE_SLOW_NOTHING_SENT = "Google took too long to respond. Nothing was sent. Try again."
SEND_LIMIT = "Gmail's sending limit has been reached. Nothing was sent. Try again later."
SEND_REJECTED = "Gmail couldn't send this message. Nothing was sent. Check the email addresses and try again."
ACCOUNT_REFUSED = ("Gmail won't send from this Google account. Nothing was sent. "
                   "Check that you can send email in Gmail with it, then try again.")
TOO_LARGE = "The attachments are too large to email. Try sending only the bulletin copy."
# The Gmail API's JSON endpoint takes the message base64url-encoded inside the request (a third larger),
# and Google's upload guide puts simple requests at 5 MB at most
# (https://developers.google.com/workspace/gmail/api/guides/uploads). A message over 3.5 MB (about
# 4.7 MB once encoded) is refused here, before the email limit is charged and before Google is called.
# The bulletin copy is tens of KB and the printed PDF about a megabyte at most.
MAX_RAW_BYTES = 3_500_000
MAYBE_SENT_PROBLEM = ("Gmail reported a problem, so the email may already have been sent. "
                      "Check your Gmail Sent folder before sending again.")
MAYBE_SENT_UNCONFIRMED = ("Gmail didn't confirm the email, so it may already have been sent. "
                          "Check your Gmail Sent folder before sending again.")

AttachmentKind = Literal["docx", "pdf"]


def _send_failed(message: str, *, disconnected: bool = False, uncertain: bool = False) -> UpstreamError:
    return UpstreamError(message, code="gmail_send_failed",
                         details={"disconnected": disconnected, "send_uncertain": uncertain})


def _recipients(church_id: uuid.UUID, contact_ids: Sequence[uuid.UUID],
                additional_emails: Sequence[str], session) -> list[str]:
    """Step 5: the contacts' addresses in the order asked, then the others, each
    checked, without repeats (any case). 404 for a contact the church does not
    have; 422 naming the contact or the address; 422 for none or too many."""
    contacts = email_contacts.get_contacts_by_ids(church_id, contact_ids, session=session)
    if len(contacts) != len(set(contact_ids)):
        raise NotFound(CONTACT_GONE, details={"field": "contact_ids"})
    addresses = []
    for contact in contacts:
        try:
            addresses.append(normalize_address(contact["email"]))
        except InvalidAddress:
            label = (contact["name"] or "").strip() or contact["email"].strip()
            raise InvalidInput(MALFORMED_CONTACT.format(label=label), field="contact_ids") from None
    for value in additional_emails:
        try:
            addresses.append(normalize_address(value))
        except InvalidAddress:
            raise InvalidInput(BAD_ADDRESS.format(value=value.strip()[:60]), field="additional_emails") from None
    recipients = dedupe_addresses(addresses)
    if not recipients:
        raise InvalidInput(NO_RECIPIENTS, field="recipients")
    if len(recipients) > MAX_RECIPIENTS:
        raise InvalidInput(TOO_MANY, field="recipients")
    return recipients


def _attachments(church_id: uuid.UUID, data: archive.ServiceInput, kinds: Sequence[AttachmentKind],
                 translation: Optional[str], charge_scripture: Callable[[int], None]) -> list[Attachment]:
    """Step 7: each file built from the posted service, as the downloads build it."""
    files = []
    if "docx" in kinds:
        doc = documents.build_document(church_id, data, "bulletin")
        files.append(Attachment(doc.content, doc.filename, service_output.DOCX_MIME))
    if "pdf" in kinds:
        pdf = documents.build_printed(church_id, data, "pdf", translation, charge=charge_scripture)
        files.append(Attachment(pdf.content, pdf.filename, printed_bulletin.PDF_MIME))
    return files


def _refused_grant(user_id: uuid.UUID, connection: GmailConnection, message: str) -> UpstreamError:
    """Google says the grant is gone: forget it, unless it was replaced meanwhile."""
    removed = google_oauth.delete_connection(user_id, only_if_token=connection.refresh_token)
    if removed is None:
        return _send_failed(CHANGED)
    return _send_failed(message, disconnected=True)


def _refresh_error(error: GoogleOAuthError, user_id: uuid.UUID, connection: GmailConnection) -> DomainError:
    if error.kind == GoogleErrorKind.INVALID_GRANT:
        return _refused_grant(user_id, connection, EXPIRED)
    if error.kind == GoogleErrorKind.CLIENT_MISCONFIGURED:
        return misconfigured("bulletin_email.refresh", error)
    if error.kind == GoogleErrorKind.TIMEOUT:
        return UpstreamTimeout(GOOGLE_SLOW_NOTHING_SENT, code="upstream_timeout")
    return _send_failed(GMAIL_UNREACHABLE)


def _send_error(error: GoogleOAuthError, user_id: uuid.UUID, connection: GmailConnection) -> DomainError:
    kind = error.kind
    if kind == GoogleErrorKind.INSUFFICIENT_SCOPE:
        return _refused_grant(user_id, connection, NO_SEND_PERMISSION)
    if kind == GoogleErrorKind.SEND_LIMIT:
        return _send_failed(SEND_LIMIT)
    if kind == GoogleErrorKind.ACCOUNT_REFUSED:
        return _send_failed(ACCOUNT_REFUSED)
    if kind == GoogleErrorKind.SEND_REJECTED:
        return _send_failed(SEND_REJECTED)
    if kind == GoogleErrorKind.SEND_UNCONFIRMED and error.status is not None:
        return _send_failed(MAYBE_SENT_PROBLEM, uncertain=True)
    if kind == GoogleErrorKind.SEND_UNCONFIRMED:
        return UpstreamTimeout(MAYBE_SENT_UNCONFIRMED, code="upstream_timeout", details={"send_uncertain": True})
    return _send_failed(GMAIL_UNREACHABLE)


def send_bulletin_email(church_id: uuid.UUID, user_id: uuid.UUID, data: archive.ServiceInput, *,
                        contact_ids: Sequence[uuid.UUID], additional_emails: Sequence[str], message: Optional[str],
                        attachments: Sequence[AttachmentKind], translation: Optional[str],
                        config: GoogleOAuthConfig, charge: Callable[[], None] = lambda: None,
                        charge_scripture: Callable[[int], None] = lambda parts: None) -> int:
    """POST /bulletin-emails: the number of people emailed. `charge` is the
    `email` bucket (called once, right before Google); `charge_scripture` the
    printed bulletin's readings fetch (POST /documents/printed's)."""
    started = time.monotonic()
    kinds = [kind for kind in ("docx", "pdf") if kind in attachments]
    with session_scope() as s:                                  # steps 5-6, closed before step 7
        recipients = _recipients(church_id, contact_ids, additional_emails, s)
        if not kinds:
            raise InvalidInput(NO_ATTACHMENT, field="attachments")
        connection = google_oauth.get_connection(user_id, session=s)
    if not config.configured:
        raise not_configured()
    if connection is None:
        raise Conflict(NOT_CONNECTED, code="gmail_not_connected")
    files = _attachments(church_id, data, kinds, translation, charge_scripture)
    raw = compose_bulletin_email(sender=connection.google_email, recipients=recipients,
                                 service_date=data.service_date, message=message, attachments=files).as_bytes()
    if len(raw) > MAX_RAW_BYTES:
        logger.info("bulletin_email.too_large church_id=%s user_id=%s bytes=%d", church_id, user_id, len(raw))
        raise InvalidInput(TOO_LARGE, field="attachments")
    charge()                                                    # step 8: the only 429 here
    try:
        access_token = google_oauth.refresh_access_token(config, connection.refresh_token)
    except GoogleOAuthError as error:
        logger.info("bulletin_email.refresh church_id=%s user_id=%s outcome=%s", church_id, user_id, error.kind.value)
        raise _refresh_error(error, user_id, connection) from None
    try:
        google_oauth.send_raw_message(access_token, raw)
    except GoogleOAuthError as error:
        logger.info("bulletin_email.send church_id=%s user_id=%s outcome=%s status=%s google_error=%s", church_id,
                    user_id, error.kind.value, error.status, error.google_error)
        raise _send_error(error, user_id, connection) from None
    logger.info("bulletin_email.sent church_id=%s user_id=%s recipients=%d bcc=%s attachments=%s bytes=%d ms=%d",
                church_id, user_id, len(recipients), len(recipients) > 1, ",".join(kinds), len(raw),
                round((time.monotonic() - started) * 1000))
    return len(recipients)
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_usecase_email.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
`53 passed in <t>s`; `1799 passed, 27 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/usecases/email.py backend/tests/test_usecase_email.py
git commit -q -m "Slice 5b-2: send_bulletin_email" -m "In the 5b spec's order: the recipients (the church's contacts, the other
addresses, each through normalize_address, de-duplicated, 1 to 50; a
refused saved contact is named with \"An admin can fix it in Settings →
Contacts.\"), at least one attachment, the connection, the files built
from the posted service (the bulletin copy and/or the printed PDF), the
email rate limit, then Google with no database session open. A refused
grant forgets the connection only if it still holds the failed token. A
send that may have gone out carries details.send_uncertain. Gmail
refusing the account has its own message, and a message over 3.5 MB is
refused before the limit and Google. The log lines hold counts, outcomes
and Google's reason name only." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1799 passed, 27 skipped`; frontend `801 passed` in 98 files.

### Task 14: `POST /bulletin-emails` (B API, Routes, Testing "test_api_bulletin_emails.py"; clarifications 12 and 16)

**Files:**
- Create: `backend/tests/test_api_bulletin_emails.py`, `backend/api/routes/bulletin_emails.py`
- Modify: `backend/api/main.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (regenerated)

- [ ] **Step 1: Write the failing tests**

The files are fixed bytes here (T13 builds real ones). The rate-limit test spends the member's `email` bucket exactly: 15 refused requests (bad address, unknown contact, not connected) and 4 replays cost nothing, the 10 sends that reach Gmail use it up, the 11th is a 429.

**Create `backend/tests/test_api_bulletin_emails.py`:**

````python
"""POST /bulletin-emails over HTTP (slice 5b spec, API, §Errors and Testing
"test_api_bulletin_emails.py"; slice 5b-2): any member sends; the
Idempotency-Key replays successes, refusals and uncertain sends, never a
second email; the checks run in the spec's order; only requests that reach
Gmail use the `email` bucket; church isolation; the shared address fixture.
Google is tests.fake_google; the files are fixed bytes (the usecase tests
build real ones)."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

import email_contacts
import google_oauth
from api.deps import get_google_config
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)
from tests.fake_google import REFRESH_TOKEN, FakeGoogle, gmail_error, google_error
from usecases import documents

OWNER = "owner@example.com"
MEMBER = "member@example.com"
CONFIG = google_oauth.GoogleOAuthConfig("client-123", "secret-456", "https://app.example.org/gmail/callback")
SERVICE = {"service_date_iso": "2026-10-04", "occasion": "World Communion Sunday"}
ADDRESSES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "email_addresses.json").read_text(encoding="utf-8"))
SENT = {"sent": True, "recipient_count": 2}


@pytest.fixture
def config():
    return {"value": CONFIG}


@pytest.fixture
def client(tmp_db, config, monkeypatch):
    monkeypatch.setattr(documents, "build_document",
                        lambda *args: documents.DocumentResult(b"FIXED-DOCX", "worship_October_04_2026.docx"))
    monkeypatch.setattr(documents, "build_printed",
                        lambda *args, charge: documents.DocumentResult(b"%PDF-FIXED", "printed_bulletin_October_04_2026.pdf"))
    client = make_api_client()
    client.app.dependency_overrides[get_google_config] = lambda: config["value"]
    return client


@pytest.fixture
def world(client, make_user, make_church):
    church = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    member = make_user(email=MEMBER)
    add_membership(member, church, "member")
    mary = email_contacts.add_contact(church, name="Mary", email="mary@example.org")["id"]
    office = email_contacts.add_contact(church, name="", email="office@example.org")["id"]
    google_oauth.save_user_token(member, MEMBER, REFRESH_TOKEN)
    return {"church": church, "member": member, "mary": mary, "office": office,
            "google": FakeGoogle(email=MEMBER).install()}


def _body(world, **overrides):
    return {"service": SERVICE, "contact_ids": [world["mary"], world["office"]], "attachments": ["docx"],
            **overrides}


def _post(client, world, body=None, *, key=None, email=MEMBER, church=None):
    headers = church_headers(email, church or world["church"])
    if key is not False:
        headers["Idempotency-Key"] = key or str(uuid.uuid4())
    return client.post("/bulletin-emails", headers=headers, json=_body(world) if body is None else body)


def _error(r) -> tuple:
    error = r.json()["error"]
    return r.status_code, error["code"], error["message"], error.get("fields"), error.get("details")


def _sends(world) -> int:
    return len(world["google"].calls(google_oauth.GMAIL_SEND_URI))


def test_a_member_emails_the_bulletin(client, world):
    r = _post(client, world, _body(world, attachments=["pdf", "docx"], message="See you Sunday.",
                                   translation="nrsvue"))
    assert (r.status_code, r.json()) == (200, SENT)
    (sent,) = world["google"].sent()
    assert (sent["To"], sent["Bcc"]) == (MEMBER, "mary@example.org, office@example.org")
    assert [p.get_filename() for p in sent.iter_attachments()] == [
        "worship_October_04_2026.docx", "printed_bulletin_October_04_2026.pdf"]


def test_the_key_is_required_and_must_be_a_uuid(client, world):
    assert _error(_post(client, world, key=False)) == (422, "invalid_request", "Missing Idempotency-Key header.",
                                                       None, None)
    assert _error(_post(client, world, key="not-a-uuid"))[:3] == (422, "invalid_request",
                                                                 "Idempotency-Key must be a UUID.")
    assert _sends(world) == 0


def test_a_retry_with_the_same_key_replays_and_sends_once(client, world):
    key = str(uuid.uuid4())
    first, again = _post(client, world, key=key), _post(client, world, key=key)
    assert (first.status_code, first.json(), again.status_code, again.json()) == (200, SENT, 200, SENT)
    assert again.headers["Idempotent-Replayed"] == "true"
    r = _post(client, world, _body(world, message="Changed."), key=key)
    assert _error(r)[:2] == (422, "idempotency_mismatch")
    assert _sends(world) == 1


def test_two_requests_with_one_key_at_once_send_once(client, world):
    key = str(uuid.uuid4())
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda _: _post(client, world, key=key), range(2)))
    assert [(r.status_code, r.json()) for r in responses] == [(200, SENT), (200, SENT)]
    assert _sends(world) == 1


@pytest.mark.parametrize("answer, status, code", [
    (httpx.ReadTimeout("slow"), 504, "upstream_timeout"),
    (httpx.Response(503), 502, "gmail_send_failed"),
], ids=["read-timeout", "gmail-5xx"])
def test_an_uncertain_send_is_replayed_never_sent_again(client, world, answer, status, code):
    world["google"].send = answer
    key = str(uuid.uuid4())
    first = _post(client, world, key=key)
    world["google"].send = httpx.Response(200, json={"id": "m"})
    again = _post(client, world, key=key)
    assert (first.status_code, first.json()["error"]["code"]) == (status, code)
    assert first.json()["error"]["details"]["send_uncertain"] is True
    assert (again.status_code, again.json()) == (status, first.json())
    assert again.headers["Idempotent-Replayed"] == "true"
    assert _sends(world) == 1
    assert _post(client, world).status_code == 200                 # a new key ("Send again anyway") sends
    assert _sends(world) == 2


def test_a_send_that_never_left_or_a_slow_refresh_runs_again_with_the_same_key(client, world):
    key = str(uuid.uuid4())
    world["google"].send = httpx.ConnectError("down")
    first = _post(client, world, key=key)
    assert _error(first)[:2] == (502, "gmail_send_failed")
    assert first.json()["error"]["details"] == {"disconnected": False, "send_uncertain": False}
    world["google"].send = httpx.Response(200, json={"id": "m"})
    assert (_post(client, world, key=key).json(), _sends(world)) == (SENT, 2)
    key = str(uuid.uuid4())
    world["google"].refresh = httpx.ReadTimeout("slow")
    assert _error(_post(client, world, key=key))[:4] == (
        504, "upstream_timeout", "Google took too long to respond. Nothing was sent. Try again.", None)
    world["google"].refresh = httpx.Response(200, json={"access_token": "a"})
    assert _post(client, world, key=key).json() == SENT


def test_the_checks_run_in_the_specs_order(client, world):
    r = client.post("/bulletin-emails", json={"nonsense": True})
    assert _error(r)[:2] == (401, "unauthenticated")
    r = _post(client, world, {"service": {}}, key=False)
    assert _error(r)[:3] == (422, "invalid_request", "Missing Idempotency-Key header.")
    r = _post(client, world, _body(world, message="x" * 5001))
    assert _error(r)[3] == {"message": "Too long (max 5000 characters)."}
    r = _post(client, world, _body(world, contact_ids=[str(uuid.uuid4()) for _ in range(201)]))
    assert _error(r)[3] == {"contact_ids": "Not a valid value."}
    many = [email_contacts.add_contact(world["church"], name="", email=f"p{i}@example.org")["id"] for i in range(60)]
    r = _post(client, world, _body(world, contact_ids=many))
    assert _error(r)[:4] == (422, "invalid_request", "You can email at most 50 people at once.",
                             {"recipients": "You can email at most 50 people at once."})
    assert _sends(world) == 0


def test_the_body_and_its_attachments(client, world):
    r = _post(client, world, {**_body(world), "sender": "someone@example.org"})
    assert _error(r)[:2] == (422, "invalid_request")
    body = _body(world)
    del body["attachments"]
    assert _error(_post(client, world, body))[3] == {"attachments": "Required."}
    assert _error(_post(client, world, _body(world, attachments=["zip"])))[3] == {"attachments.0": "Not a valid value."}
    assert _error(_post(client, world, _body(world, attachments=[])))[2:4] == (
        "Choose at least one attachment.", {"attachments": "Choose at least one attachment."})
    assert _sends(world) == 0


def test_only_requests_that_reach_gmail_use_the_hourly_limit(client, world):
    for _ in range(5):
        assert _post(client, world, _body(world, additional_emails=["not an address"])).status_code == 422
        assert _post(client, world, _body(world, contact_ids=[str(uuid.uuid4())])).status_code == 404
    google_oauth.delete_connection(world["member"])
    for _ in range(5):
        assert _post(client, world).status_code == 409                 # not connected
    google_oauth.save_user_token(world["member"], MEMBER, REFRESH_TOKEN)
    key = str(uuid.uuid4())
    for _ in range(5):
        assert _post(client, world, key=key).status_code == 200      # one send, four replays
    for _ in range(9):
        assert _post(client, world).status_code == 200
    r = _post(client, world)
    assert _error(r)[:2] == (429, "rate_limited")
    assert int(r.headers["Retry-After"]) >= 1
    assert _sends(world) == 10


def test_another_churchs_contact_is_not_found_and_nothing_is_sent(client, world, make_church, make_user):
    other = make_church(name="Other", owner_user_id=make_user(email="other@example.com"))
    theirs = email_contacts.add_contact(other, name="Theirs", email="theirs@example.org")["id"]
    r = _post(client, world, _body(world, contact_ids=[world["mary"], theirs]))
    assert _error(r) == (404, "not_found", "One of the selected contacts no longer exists. Refresh the list and try "
                                           "again.", None, {"field": "contact_ids"})
    assert _sends(world) == 0


def test_a_hymn_the_church_no_longer_has_is_not_found(client, world, monkeypatch):
    monkeypatch.undo()                                             # the real build_document
    service = {**SERVICE, "hymns": {"response": {"hymn_id": str(uuid.uuid4()), "title": "Gone", "number": 1}}}
    r = _post(client, world, _body(world, service=service))
    assert _error(r)[:3] + (_error(r)[4],) == (
        404, "not_found", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
        {"field": "hymns.response.hymn_id"})
    assert _sends(world) == 0


def test_the_route_is_church_scoped(client, isolation_world):
    assert_church_isolated(client, "POST", "/bulletin-emails", world=isolation_world,
                           json={"service": SERVICE, "additional_emails": ["a@example.org"], "attachments": ["docx"]})


def test_the_shared_address_cases(client, world):
    for raw in ADDRESSES["invalid"]:
        r = _post(client, world, _body(world, contact_ids=[], additional_emails=[raw]))
        assert r.status_code == 422, raw
        assert list(r.json()["error"]["fields"]) == ["additional_emails"], raw
    r = _post(client, world, _body(world, contact_ids=[], additional_emails=[c["raw"] for c in ADDRESSES["valid"]]))
    assert (r.status_code, r.json()["recipient_count"]) == (200, len(ADDRESSES["valid"]))
    assert world["google"].sent()[0]["Bcc"] == ", ".join(c["normalized"] for c in ADDRESSES["valid"])


@pytest.mark.parametrize("setup, expected", [
    (lambda w, c: google_oauth.delete_connection(w["member"]),
     (409, "gmail_not_connected", "Connect your Gmail first, then try again.", None, None)),
    (lambda w, c: setattr(w["google"], "refresh", google_error(400, "invalid_grant")),
     (502, "gmail_send_failed", "Your Gmail connection has expired or was removed. Reconnect Gmail and try again.",
      None, {"disconnected": True, "send_uncertain": False})),
    (lambda w, c: setattr(w["google"], "send", gmail_error(403, "dailyLimitExceeded")),
     (502, "gmail_send_failed", "Gmail's sending limit has been reached. Nothing was sent. Try again later.",
      None, {"disconnected": False, "send_uncertain": False})),
    (lambda w, c: c.update(value=google_oauth.GoogleOAuthConfig("", "", "")),
     (503, "gmail_not_configured", "Per-user Gmail sending isn't configured on this deployment.", None, None)),
], ids=["not-connected", "expired", "limit", "not-configured"])
def test_gmail_errors_never_carry_googles_text(client, world, config, setup, expected):
    setup(world, config)
    r = _post(client, world)
    assert _error(r) == expected
    assert "SECRET-GOOGLE-TEXT" not in r.text


def test_signed_out_is_401(client):
    r = client.post("/bulletin-emails", headers=auth_headers(MEMBER) | {"Authorization": "Bearer nope"}, json={})
    assert _error(r)[:2] == (401, "unauthenticated")
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_bulletin_emails.py 2>&1 | tail -3`
**Expected** (no route yet: every request is a 404, the signed-out one among them; all 19 fail):
```
FAILED backend/tests/test_api_bulletin_emails.py::test_gmail_errors_never_carry_googles_text[not-configured]
FAILED backend/tests/test_api_bulletin_emails.py::test_signed_out_is_401 - As...
19 failed in <t>s
```

- [ ] **Step 3: Write the route and mount it**

**Create `backend/api/routes/bulletin_emails.py`:**

````python
"""POST /bulletin-emails: email the bulletin from the caller's own Gmail
(slice 5b spec, API; owner's 5b answers of 2026-10-06; slice 5b-2).

Church-scoped; any member may send (owner decision 5). The body is the
service as it is on screen (built into the files on the server, never
uploaded), the chosen contacts by id and any other addresses, the message,
the attachments ("docx": the bulletin copy, "pdf": the printed bulletin; at
least one) and, for the PDF, the draft's translation, as POST
/documents/printed takes it.

An Idempotency-Key is required. FastAPI runs the dependencies in the order
declared (sign-in and church, then the key) and checks the body after them;
run_idempotent comes next, then the usecase's own order. A retry with the
same key and body gets the first answer: the success, any 4xx, and an
answer that says the email may already have been sent (details.send_uncertain,
kept by `store_error`), so a lost connection or a second tap never sends twice.
The `email` bucket (10 an hour) is charged inside the usecase right before
Google, so a typo, a missing contact or a replay costs nothing; the PDF's
readings charge the `scripture` bucket as the printed download does. Plain
`def`, one usecase call, no SQL and no try/except (F §2.2 rule 1).
"""
import uuid
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, get_google_config, require_church
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.schemas import ServiceDraft
from domain_errors import DomainError
from google_oauth import GoogleOAuthConfig
from usecases import email

router = APIRouter()


class BulletinEmailIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: ServiceDraft
    # The list caps only guard the body's size; the usecase applies the 50-recipient rule after de-duplication.
    contact_ids: list[uuid.UUID] = Field(default_factory=list, max_length=200)
    additional_emails: list[Annotated[str, StringConstraints(max_length=320)]] = Field(default_factory=list,
                                                                                       max_length=200)
    message: Optional[str] = Field(default=None, max_length=5000)
    attachments: list[Literal["docx", "pdf"]] = Field(max_length=2, description="docx: the bulletin copy; "
                                                      "pdf: the printed bulletin. At least one.")
    # The printed bulletin's readings print in it when this deployment offers it, else in the church's.
    translation: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]] = None


class BulletinEmailOut(BaseModel):
    sent: Literal[True]
    recipient_count: int


def _maybe_sent(error: DomainError) -> bool:
    """Keep an answer that says the email may already have gone out."""
    return bool((error.details or {}).get("send_uncertain"))


@router.post("/bulletin-emails", response_model=BulletinEmailOut,
             responses=error_responses(401, 403, 404, 409, 422, 429, 502, 503, 504))
def send_bulletin_email(
    payload: BulletinEmailIn,
    church: ActiveChurch = Depends(require_church),
    user: CurrentUser = Depends(get_current_user),
    key: Optional[uuid.UUID] = Depends(idempotency_key(required=True)),
    config: GoogleOAuthConfig = Depends(get_google_config),
) -> Response:
    return run_idempotent(
        user_id=user.id, church_id=church.id, route="/bulletin-emails", key=key, payload=payload, status_code=200,
        store_error=_maybe_sent,
        call=lambda: BulletinEmailOut(sent=True, recipient_count=email.send_bulletin_email(
            church.id, user.id, payload.service.to_input(), contact_ids=payload.contact_ids,
            additional_emails=payload.additional_emails, message=payload.message, attachments=payload.attachments,
            translation=payload.translation, config=config,
            charge=lambda: ratelimit.consume("email", user_id=user.id),
            charge_scripture=lambda parts: ratelimit.consume("scripture", user_id=user.id, cost=parts))))
````

**In `backend/api/main.py`, replace:**

````python
from api.routes import (bulletin_images, bulletin_settings, churches, contacts, documents, gmail, health, hymnals,
                        hymns, invites, lectionary, liturgy, liturgy_review, me, reference, rubric, scripture,
                        services)
````

**with:**

````python
from api.routes import (bulletin_emails, bulletin_images, bulletin_settings, churches, contacts, documents, gmail,
                        health, hymnals, hymns, invites, lectionary, liturgy, liturgy_review, me, reference, rubric,
                        scripture, services)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(gmail.router)
````

**with:**

````python
    app.include_router(gmail.router)
    app.include_router(bulletin_emails.router)
````

- [ ] **Step 4: Regenerate the API files, see the tests pass, and the suites**

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git diff --stat -- frontend/src/lib/api | tail -1` then `.venv/bin/python -m pytest -q backend/tests/test_api_bulletin_emails.py backend/tests/test_usecase_email.py backend/tests/test_openapi_contract.py backend/tests/test_route_guards.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
` 2 files changed, 409 insertions(+)`; `80 passed in <t>s`; `1818 passed, 27 skipped in <t>s`; `typecheck 0`, `lint 0` (the new types are used in T15).

- [ ] **Step 5: Commit**

```bash
git add backend/api/routes/bulletin_emails.py backend/api/main.py backend/tests/test_api_bulletin_emails.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Slice 5b-2: POST /bulletin-emails" -m "Any member emails the bulletin built from the posted service, with the
chosen attachments, from their own Gmail. An Idempotency-Key is
required: a retry with the same key and body replays the first answer,
a success, a refusal or \"may already have been sent\" (store_error), so
a lost connection or a second tap never sends twice. Only requests that
reach Gmail use the hourly email limit. Church isolation, the shared
address fixture and the 5b spec's check order are tested. OpenAPI and
the types regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1818 passed, 27 skipped`; frontend `801 passed` in 98 files.

### Task 15: The email dialog's rules (B "Pure modules" `lib/email.ts`, `lib/idempotency.ts`, "Storage keys"; clarifications 12 and 17)

**Files:**
- Create: `frontend/src/lib/email.test.ts`, `frontend/src/lib/email.ts`
- Modify: `frontend/src/lib/idempotency.test.ts`, `frontend/src/lib/draft/prune.test.ts`, `frontend/src/lib/idempotency.ts`, `frontend/src/lib/draft/prune.ts`, `frontend/src/lib/api/timeouts.ts`

- [ ] **Step 1: Write the failing tests**

`email.test.ts` reads the shared `bulletin_email.json` (T11) as `download.test.ts` reads `docx_filenames.json`, and stubs `window` with a small storage for the remembered choices and the uncertain send (plan review M1: kept per user and church in sessionStorage).

**Create `frontend/src/lib/email.test.ts`:**

````ts
import { readFileSync } from "node:fs";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { testDraft } from "@/test/fixtures";

import {
  bulletinEmailBody,
  bulletinEmailSubject,
  clearUncertainSend,
  countRecipients,
  defaultBulletinMessage,
  emailPrefsKey,
  fieldTarget,
  parseAddressList,
  parseReopen,
  readEmailPrefs,
  readUncertainSend,
  uncertainSendKey,
  writeEmailPrefs,
  writeUncertainSend,
} from "./email";

type Case = { date_iso: string; subject: string; default_message: string };
const { cases } = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/bulletin_email.json", import.meta.url), "utf-8"),
) as { cases: Case[] };

let data: Map<string, string>;

beforeEach(() => {
  data = new Map();
  const storage = {
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
    removeItem: (k: string) => void data.delete(k),
  };
  vi.stubGlobal("window", { localStorage: storage, sessionStorage: storage });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("the bulletin email (slice 5b-2)", () => {
  it("writes the subject and the default message as the server does (shared/bulletin_email.json)", () => {
    expect(cases).toHaveLength(6);
    for (const c of cases) {
      expect(bulletinEmailSubject(c.date_iso), c.date_iso).toBe(c.subject);
      expect(defaultBulletinMessage(c.date_iso), c.date_iso).toBe(c.default_message);
    }
  });

  it("reads Other addresses split on commas, semicolons and new lines", () => {
    expect(parseAddressList(" a@example.org, b@example.org;c@example.org\n\nMary Jones <mary@example.org> ,, ")).toEqual([
      "a@example.org",
      "b@example.org",
      "c@example.org",
      "mary@example.org",
    ]);
    expect(parseAddressList("   ")).toEqual([]);
  });

  it("counts each person once, ignoring capitals and spaces", () => {
    expect(countRecipients(["mary@example.org", "office@example.org"], ["MARY@example.org ", "organist@example.org"])).toBe(3);
    expect(countRecipients([], [])).toBe(0);
  });

  it("puts each field's message where it belongs", () => {
    expect(["additional_emails", "additional_emails.3"].map(fieldTarget)).toEqual(["other", "other"]);
    expect(fieldTarget("message")).toBe("message");
    expect(fieldTarget("attachments")).toBe("attachments");
    expect(["recipients", "contact_ids", "contact_ids.2"].map(fieldTarget)).toEqual(["to", "to", "to"]);
    expect(["custom_elements.0.label", "service.service_date_iso", "translation"].map(fieldTarget)).toEqual(["top", "top", "top"]);
  });

  it("remembers the last send's contacts and the attachments per user and church", () => {
    expect(readEmailPrefs("u1", "c1")).toEqual({ version: 1, contact_ids: [], attachments: ["docx"] });
    writeEmailPrefs("u1", "c1", { attachments: ["pdf", "docx"] });
    writeEmailPrefs("u1", "c1", { contact_ids: ["k1", "k2"] });
    expect(readEmailPrefs("u1", "c1")).toEqual({ version: 1, contact_ids: ["k1", "k2"], attachments: ["docx", "pdf"] });
    expect(readEmailPrefs("u1", "c2").contact_ids).toEqual([]);
    expect(emailPrefsKey("u1", "c1")).toBe("wsb:emailPrefs:u1:c1");
    data.set(emailPrefsKey("u1", "c3"), JSON.stringify({ version: 1, contact_ids: "k1", attachments: [] }));
    expect(readEmailPrefs("u1", "c3")).toEqual({ version: 1, contact_ids: [], attachments: ["docx"] });
    data.set(emailPrefsKey("u1", "c4"), "{broken");
    expect(readEmailPrefs("u1", "c4").attachments).toEqual(["docx"]);
  });

  it("remembers a send that may already have gone out, per user and church, in this tab", () => {
    expect(readUncertainSend("u1", "c1")).toBeNull();
    writeUncertainSend("u1", "c1", "Check your Gmail Sent folder before sending again.");
    expect(readUncertainSend("u1", "c1")).toBe("Check your Gmail Sent folder before sending again.");
    expect(readUncertainSend("u1", "c2")).toBeNull();
    expect(uncertainSendKey("u1", "c1")).toBe("wsb:emailUncertain:u1:c1");
    data.set(uncertainSendKey("u1", "c3"), "{broken");
    expect(readUncertainSend("u1", "c3")).toBeNull();
    clearUncertainSend("u1", "c1");
    expect(readUncertainSend("u1", "c1")).toBeNull();
  });

  it("sends the service as the downloads do, with the choices and the draft's translation", () => {
    const draft = testDraft((d) => ({ ...d, readings: { ...d.readings, translation: "nrsvue" } }));
    const body = bulletinEmailBody(draft, {
      contactIds: ["k1"],
      otherAddresses: "organist@example.org; ",
      message: "See you Sunday.",
      attachments: ["pdf", "docx"],
    });
    expect(body).toMatchObject({
      contact_ids: ["k1"],
      additional_emails: ["organist@example.org"],
      message: "See you Sunday.",
      attachments: ["docx", "pdf"],
      translation: "nrsvue",
    });
    expect(body.service.service_date_iso).toBe(draft.readings.date_iso);
  });

  it("reopens the dialog only for the same church", () => {
    const raw = JSON.stringify({ church_id: "c1", contact_ids: ["k1"], other_addresses: "a@example.org", message: "Hi", attachments: ["pdf"] });
    expect(parseReopen(raw, "c1")).toEqual({ church_id: "c1", contact_ids: ["k1"], other_addresses: "a@example.org", message: "Hi", attachments: ["pdf"] });
    expect(parseReopen(JSON.stringify({ church_id: "c1" }), "c1")).toEqual({ church_id: "c1" });
    expect(parseReopen(raw, "c2")).toBeNull();
    expect(parseReopen("{broken", "c1")).toBeNull();
    expect(parseReopen(null, "c1")).toBeNull();
  });
});
````

**In `frontend/src/lib/idempotency.test.ts`, replace:**

````ts
    expect(tracker.keyFor({ ...BODY, name: "New Life Church" })).toBe(edited);
  });
});
````

**with:**

````ts
    expect(tracker.keyFor({ ...BODY, name: "New Life Church" })).toBe(edited);
  });

  it("rotate drops the kept key, so the same body is sent as a new request (slice 5b-2: Send again anyway)", () => {
    const tracker = createKeyTracker();
    const first = tracker.keyFor(BODY);
    tracker.settle("uncertain");
    tracker.rotate();
    const second = tracker.keyFor(BODY);
    expect(second).toMatch(UUID);
    expect(second).not.toBe(first);
  });
});
````

**In `frontend/src/lib/draft/prune.test.ts`, replace:**

````ts

  it("does nothing when storage is missing or blocked", () => {
````

**with:**

````ts

  it("removes the email dialog's remembered choices for churches the user left (slice 5b-2)", () => {
    data.set("wsb:emailPrefs:u1:c-left", "{}");
    data.set("wsb:emailPrefs:u1:c-member", "{}");
    data.set("wsb:emailPrefs:u2:c-left", "{}");
    expect(pruneDrafts("u1", ["c-member"], NOW)).toEqual(["wsb:emailPrefs:u1:c-left"]);
    expect([...data.keys()].sort()).toEqual(["wsb:emailPrefs:u1:c-member", "wsb:emailPrefs:u2:c-left"]);
  });

  it("does nothing when storage is missing or blocked", () => {
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/email.test.ts src/lib/idempotency.test.ts src/lib/draft/prune.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`email.ts` does not exist yet; no `rotate`; the choices are not pruned):
```
   × pruneDrafts (F §4.6 items 3 and 4) > removes the email dialog's remembered choices for churches the user left (slice 5b-2) <t>ms
   × createKeyTracker > rotate drops the kept key, so the same body is sent as a new request (slice 5b-2: Send again anyway) <t>ms
 FAIL  |unit| src/lib/email.test.ts [ src/lib/email.test.ts ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
      Tests  2 failed | 10 passed (12)
```

- [ ] **Step 3: Write the rules, `rotate`, the pruning and the timeout**

**Create `frontend/src/lib/email.ts`:**

````ts
/**
 * Emailing the bulletin (slice 5b spec, "Pure modules" `lib/email.ts`, amended
 * 2026-10-06; slice 5b-2). Pure, apart from the remembered choices in
 * localStorage (`readEmailPrefs`, `writeEmailPrefs`).
 *
 * - The subject and the default message, as the server writes them
 *   (`bulletin_email.py`; shared/bulletin_email.json keeps the two equal).
 * - `parseAddressList`: "Other addresses" as addresses (commas, semicolons or
 *   new lines; the part inside <…> when a name comes with it).
 * - `countRecipients`: how many people the email goes to (an address chosen
 *   twice, in any capitals, counts once, as the server sends it once).
 * - `fieldTarget`: where a 422's field message goes in the dialog.
 * - The remembered choices (per user and church, on this device): the
 *   contacts of the last successful send and the attachments last chosen.
 * - `bulletinEmailBody`: the `POST /bulletin-emails` body.
 * - The uncertain send (`readUncertainSend`, `writeUncertainSend`,
 *   `clearUncertainSend`): a send that may already have gone out, kept in
 *   sessionStorage per user and church, so neither leaving Review nor a reload
 *   quietly allows a plain Send again; only **Send again anyway** does.
 * - `ReopenEmail`: what the dialog keeps while the user is away at Google.
 */
import type { components } from "@/lib/api/schema";
import { formatServiceDate, formatShortDate, isSunday, isValidDateIso, weekday } from "@/lib/dates";
import { serviceBody } from "@/lib/documents";
import type { DraftV1 } from "@/lib/draft/schema";
import { readLocal, readSession, removeSession, writeLocal, writeSession } from "@/lib/storage";

export type BulletinEmailBody = components["schemas"]["BulletinEmailIn"];
export type AttachmentKind = BulletinEmailBody["attachments"][number];

export const MAX_RECIPIENTS = 50;
export const MESSAGE_MAX_LENGTH = 5000;
export const ATTACHMENT_KINDS: readonly AttachmentKind[] = ["docx", "pdf"];
export const ATTACHMENT_LABELS: Record<AttachmentKind, string> = {
  docx: "Bulletin copy (Word)",
  pdf: "Printed bulletin (PDF)",
};
export const DEFAULT_ATTACHMENTS: AttachmentKind[] = ["docx"];
export const SUNDAY_MESSAGE = "Hi! Here's the worship bulletin for this Sunday.";

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
/** The server's `PrintedDocumentIn.translation` and `BulletinEmailIn.translation` limit. */
const MAX_TRANSLATION = 20;

/** "2026-10-04" → "Worship service for October 4, 2026" (`bulletin_email.bulletin_email_subject`). */
export function bulletinEmailSubject(dateIso: string): string {
  return `Worship service for ${formatServiceDate(dateIso)}`;
}

/** The message the dialog starts with (`bulletin_email.default_bulletin_message`). */
export function defaultBulletinMessage(dateIso: string): string {
  if (!isValidDateIso(dateIso) || isSunday(dateIso)) return SUNDAY_MESSAGE;
  return `Hi! Here's the worship bulletin for ${WEEKDAYS[weekday(dateIso)]}, ${formatShortDate(dateIso)}.`;
}

/** "Other addresses" as a list: split on commas, semicolons and new lines, trimmed, `Name <a@b.org>` read as `a@b.org`. */
export function parseAddressList(text: string): string[] {
  return text
    .split(/[,;\n]/)
    .map((part) => {
      const inside = /<([^<>]*)>/.exec(part);
      return (inside ? inside[1] : part).trim();
    })
    .filter((address) => address !== "");
}

/** How many people get the email: every address once, ignoring capitals and spaces around it. */
export function countRecipients(contactEmails: readonly string[], extras: readonly string[]): number {
  return new Set([...contactEmails, ...extras].map((address) => address.trim().toLowerCase())).size;
}

/** Where a 422's field message shows in the dialog (5b spec, "Send outcomes"). */
export type FieldTarget = "to" | "other" | "message" | "attachments" | "top";

export function fieldTarget(key: string): FieldTarget {
  const head = key.split(".")[0];
  if (head === "additional_emails") return "other";
  if (head === "message") return "message";
  if (head === "attachments") return "attachments";
  if (head === "recipients" || head === "contact_ids") return "to";
  return "top";
}

/** What the dialog remembers for this user in this church, on this device. */
export type EmailPrefs = { version: 1; contact_ids: string[]; attachments: AttachmentKind[] };

export function emailPrefsKey(userId: string, churchId: string): string {
  return `wsb:emailPrefs:${userId}:${churchId}`;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function attachmentList(value: unknown): AttachmentKind[] {
  const chosen = stringList(value);
  return ATTACHMENT_KINDS.filter((kind) => chosen.includes(kind));
}

/** The remembered choices; none (or unreadable): no contacts, the bulletin copy. */
export function readEmailPrefs(userId: string, churchId: string): EmailPrefs {
  const fallback: EmailPrefs = { version: 1, contact_ids: [], attachments: DEFAULT_ATTACHMENTS };
  const raw = readLocal(emailPrefsKey(userId, churchId));
  if (raw === null) return fallback;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (parsed?.version !== 1) return fallback;
    const attachments = attachmentList(parsed.attachments);
    return {
      version: 1,
      contact_ids: stringList(parsed.contact_ids),
      attachments: attachments.length > 0 ? attachments : DEFAULT_ATTACHMENTS,
    };
  } catch {
    return fallback;
  }
}

/** Remember `changes` (the last send's contacts, or the attachments just chosen) on top of what is kept. */
export function writeEmailPrefs(userId: string, churchId: string, changes: Partial<Omit<EmailPrefs, "version">>): void {
  const next = { ...readEmailPrefs(userId, churchId), ...changes, version: 1 };
  writeLocal(emailPrefsKey(userId, churchId), JSON.stringify(next));
}

/** Where this tab keeps a send that may already have gone out, for this user in this church. */
export function uncertainSendKey(userId: string, churchId: string): string {
  return `wsb:emailUncertain:${userId}:${churchId}`;
}

/** The message of a send that may already have gone out, or null (none, or unreadable). */
export function readUncertainSend(userId: string, churchId: string): string | null {
  const raw = readSession(uncertainSendKey(userId, churchId));
  if (raw === null) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return parsed?.version === 1 && typeof parsed.message === "string" && parsed.message !== "" ? parsed.message : null;
  } catch {
    return null;
  }
}

export function writeUncertainSend(userId: string, churchId: string, message: string): void {
  writeSession(uncertainSendKey(userId, churchId), JSON.stringify({ version: 1, message }));
}

export function clearUncertainSend(userId: string, churchId: string): void {
  removeSession(uncertainSendKey(userId, churchId));
}

/** The dialog's form. */
export type EmailForm = { contactIds: string[]; otherAddresses: string; message: string; attachments: AttachmentKind[] };

/** `POST /bulletin-emails`: the service as the downloads send it, the choices, and the draft's translation for the PDF. */
export function bulletinEmailBody(draft: DraftV1, form: EmailForm): BulletinEmailBody {
  const translation = draft.readings.translation;
  return {
    service: serviceBody(draft),
    contact_ids: [...form.contactIds],
    additional_emails: parseAddressList(form.otherAddresses),
    message: form.message,
    attachments: ATTACHMENT_KINDS.filter((kind) => form.attachments.includes(kind)),
    translation: translation && translation.length <= MAX_TRANSLATION ? translation : null,
  };
}

/** What the dialog keeps in `wsb:reopenEmailDialog` while the user connects Gmail at Google. */
export type ReopenEmail = { church_id: string } & Partial<{
  contact_ids: string[];
  other_addresses: string;
  message: string;
  attachments: AttachmentKind[];
}>;

/** The stored reopen request for this church, or null (none, unreadable, or another church's). */
export function parseReopen(raw: string | null, churchId: string): ReopenEmail | null {
  if (raw === null) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (parsed?.church_id !== churchId) return null;
    const reopen: ReopenEmail = { church_id: churchId };
    if (Array.isArray(parsed.contact_ids)) reopen.contact_ids = stringList(parsed.contact_ids);
    if (typeof parsed.other_addresses === "string") reopen.other_addresses = parsed.other_addresses;
    if (typeof parsed.message === "string") reopen.message = parsed.message;
    if (Array.isArray(parsed.attachments)) reopen.attachments = attachmentList(parsed.attachments);
    return reopen;
  } catch {
    return null;
  }
}
````

**In `frontend/src/lib/idempotency.ts`, replace:**

````ts
 * Any 2xx or 4xx, or a changed body, gets a new key. 5b's `createSendKeyTracker` is this
 * tracker with the draft as the fingerprint.
````

**with:**

````ts
 * Any 2xx or 4xx, or a changed body, gets a new key. The bulletin email (slice 5b-2) uses
 * this tracker as the 5b spec's `createSendKeyTracker`: a send that may already have gone out
 * keeps its key, so a plain retry replays "check your Sent folder", and only **Send again
 * anyway** (`rotate`) sends with a new one.
````

**In `frontend/src/lib/idempotency.ts`, replace:**

````ts
  settle(outcome: SettleOutcome): void;
````

**with:**

````ts
  settle(outcome: SettleOutcome): void;
  /** Drop the pending key now: the next request is a new one, even with the same body. */
  rotate(): void;
````

**In `frontend/src/lib/idempotency.ts`, replace:**

````ts
    },
  };
````

**with:**

````ts
    },
    rotate() {
      pending = null;
    },
  };
````

**In `frontend/src/lib/draft/prune.ts`, replace:**

````ts
 * churches the user no longer belongs to, with their corrupt-draft backups.
````

**with:**

````ts
 * churches the user no longer belongs to, with their corrupt-draft backups,
 * and (slice 5b-2) the email dialog's remembered choices for those churches.
````

**In `frontend/src/lib/draft/prune.ts`, replace:**

````ts
  const corruptPrefix = `wsb:draft-corrupt:${userId}:`;
````

**with:**

````ts
  const corruptPrefix = `wsb:draft-corrupt:${userId}:`;
  const emailPrefix = `wsb:emailPrefs:${userId}:`;
````

**In `frontend/src/lib/draft/prune.ts`, replace:**

````ts
      removed.push(key);
    }
````

**with:**

````ts
      removed.push(key);
    } else if (key.startsWith(emailPrefix) && !members.has(key.slice(emailPrefix.length))) {
      removeLocal(key);
      removed.push(key);
    }
````

**In `frontend/src/lib/api/timeouts.ts`, replace:**

````ts
  "POST /gmail-connection": 75_000,
````

**with:**

````ts
  "POST /gmail-connection": 75_000,
  // Slice 5b-2: the printed bulletin's readings (their 20 s deadline), then Google's refresh and the send,
  // whose timeouts are per phase (15 s and 30 s for each wait), not deadlines. This is the overall limit: a
  // send still unanswered then is shown as possibly sent ("We lost the connection…"), never as failed.
  "POST /bulletin-emails": 90_000,
````

- [ ] **Step 4: See them pass, and the suite**

Run: `(cd frontend && npx vitest run src/lib/email.test.ts src/lib/idempotency.test.ts src/lib/draft/prune.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
`      Tests  20 passed (20)`; ` Test Files  99 passed (99)` and `      Tests  811 passed (811)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/email.ts frontend/src/lib/email.test.ts frontend/src/lib/idempotency.ts frontend/src/lib/idempotency.test.ts frontend/src/lib/draft/prune.ts frontend/src/lib/draft/prune.test.ts frontend/src/lib/api/timeouts.ts
git commit -q -m "Slice 5b-2: the email dialog's rules and remembered choices" -m "lib/email.ts: the subject and the default message as the server writes
them (shared fixture), Other addresses as a list, the recipient count
(each address once), where a 422's field goes, the remembered contacts
and attachments per user and church, a send that may already have gone
out (sessionStorage, per user and church), the POST /bulletin-emails
body and the reopen request after Google. createKeyTracker gains rotate() for
\"Send again anyway\"; the draft pruning drops the remembered choices for
churches left; POST /bulletin-emails waits 90 s, the overall limit." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1818 passed, 27 skipped`; frontend `811 passed` in 99 files.

### Task 16: The Email the bulletin card and dialog (B "Review step", "Email dialog", "Send outcomes", flows B and D; clarifications 14 and 17-20)

**Files:**
- Create: `frontend/src/components/builder/review/email-card.test.tsx`, `frontend/src/lib/queries/email.ts`, `frontend/src/components/builder/review/email-dialog.tsx`, `frontend/src/components/builder/review/email-card.tsx`
- Modify: `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, `frontend/src/components/settings/contacts-settings-page.test.tsx`, `frontend/src/components/settings/account-settings-page.test.tsx`, `frontend/src/components/builder/review/review-send-step.tsx`, `frontend/src/components/builder/review/printed-card.tsx`, `frontend/src/components/settings/contacts-settings-page.tsx`, `frontend/src/components/settings/account-settings-page.tsx`

- [ ] **Step 1: Write the failing tests**

The card renders inside the builder layout on Review, as in `review-send-step.test.tsx`, with the clock fixed so a fresh draft is dated Sunday, October 4, 2026. The three test files that render Review (the step itself, the builder shell's step routes, and the liturgy step's walk to Review) gain the status route; the step's heading list gains the card. The Contacts caption test and the Account page's Gmail sentence test pin clarification 20's lines. From the plan review: the dialog is 5b-1's bottom sheet below `md`, and a class-based test checks that nothing between **Send** and the sheet scrolls by itself (I3; jsdom does not lay out, so manual check 12 stays); after an uncertain send or a lost connection plain Send stays off, also after the card is unmounted and rendered again, and only **Send again anyway** sends (M1); back from Google the dialog waits for last week's bulletin and shows the printed card's notes under a ticked PDF (M7).

**Create `frontend/src/components/builder/review/email-card.test.tsx`:**

````tsx
/**
 * Review → Email the bulletin (slice 5b spec, UX "Email the bulletin card",
 * "Email dialog", "Send outcomes", flow B; amended 2026-10-06; slice 5b-2).
 * The step renders inside the builder layout with a Toaster, as in
 * review-send-step.test.tsx. The clock is fixed at Tuesday, September 29,
 * 2026, so a fresh draft is dated Sunday, October 4, 2026. Leaving for
 * Google is `browser.assign`, spied.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church } from "@/lib/api/types";
import { draftKey } from "@/lib/draft/schema";
import { emailPrefsKey, uncertainSendKey } from "@/lib/email";
import { browser, GMAIL_RETURN_KEY, REOPEN_EMAIL_KEY } from "@/lib/gmail";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  bulletinSettings,
  church,
  churchProfile,
  contact,
  contactList,
  DRAFT_NOW,
  gmailConnection,
  gmailDisconnected,
  hymnals,
  hymnListRoute,
  lectionaryRoute,
  liturgyConfig,
  me,
  previousBulletin,
  serviceBulletin,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { BCC_NOTE, CHOOSE_ATTACHMENT, CHOOSE_RECIPIENT, CONNECTION_LOST, CONTACTS_ERROR, INVALID_CONTACT, NO_CONTACTS, TOO_MANY } from "./email-dialog";
import { EMAIL_CONNECT, EMAIL_NEEDS_DATE, EMAIL_NOT_CONFIGURED, EMAIL_STATUS_ERROR } from "./email-card";

const GRACE = church();
const PREFS = emailPrefsKey(USER_ID, GRACE.id);
const MARY = contact();
const OFFICE = contact({ id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e02", name: null, email: "office@example.org" });
const BROKEN = contact({ id: "6c0b5e1a-1d2b-4c3d-8e4f-5a6b7c8d9e03", name: "Two at once", email: "a@example.org, b@example.org", email_valid: false });
const GOOGLE_URL = "https://accounts.google.com/o/oauth2/v2/auth?state=s1";
const SENT = { sent: true, recipient_count: 2 };
let assign: ReturnType<typeof vi.spyOn>;

function renderReview(routes: Record<string, FakeHandler> = {}, { draft = testDraft(), role = "admin" as Church["role"] } = {}) {
  window.localStorage.setItem(draftKey(USER_ID, GRACE.id), JSON.stringify(draft));
  const active = church({ role });
  const api = installFakeApi({
    "GET /church": churchProfile({ role }),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /translations": translations(),
    "GET /hymnals": hymnals(),
    "GET /hymns": hymnListRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(),
    "GET /contacts": contactList([MARY, OFFICE, BROKEN]),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <ReviewStepPage />
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/builder/review" },
  );
  return { ...view, api };
}

async function emailCard() {
  return screen.findByRole("region", { name: "Email the bulletin" });
}

/** Opens the dialog once the card knows the connection (while it loads, its button is disabled). */
async function openDialog(user: ReturnType<typeof renderReview>["user"]) {
  const card = await emailCard();
  await within(card).findByText("Sends from pat@example.com.");
  await user.click(within(card).getByRole("button", { name: "Email bulletin…" }));
  const dialog = await screen.findByRole("dialog", { name: "Email the bulletin" });
  await within(dialog).findByRole("checkbox", { name: /Mary Jones/ });
  return dialog;
}

function sends(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "POST" && r.path === "/bulletin-emails");
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  assign = vi.spyOn(browser, "assign").mockImplementation(() => {});
});

afterEach(() => {
  toast.dismiss();
  vi.useRealTimers();
});

describe("Review → Email the bulletin: the card (slice 5b-2)", () => {
  it("says when emailing is not set up here, with no button", async () => {
    renderReview({ "GET /gmail-connection": gmailConnection({ configured: false, connected: false, google_email: null }) });
    const card = await emailCard();
    expect(await within(card).findByText(EMAIL_NOT_CONFIGURED)).toBeInTheDocument();
    expect(within(card).queryByRole("button")).toBeNull();
  });

  it("connects Gmail from Review, to come back here and reopen the dialog", async () => {
    const { user } = renderReview({
      "GET /gmail-connection": gmailDisconnected(),
      "POST /gmail-connection/auth-url": { auth_url: GOOGLE_URL },
    });
    const card = await emailCard();
    expect(await within(card).findByText(EMAIL_CONNECT)).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Connect Gmail" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(GOOGLE_URL));
    expect(window.sessionStorage.getItem(GMAIL_RETURN_KEY)).toBe("/builder/review");
    expect(JSON.parse(window.sessionStorage.getItem(REOPEN_EMAIL_KEY) ?? "null")).toEqual({ church_id: GRACE.id });
  });

  it("shows a failed check with Retry", async () => {
    let fail = true;
    const { user } = renderReview({
      "GET /gmail-connection": () => (fail ? fakeError(500, "internal_error", "Something went wrong.") : gmailConnection()),
    });
    const card = await emailCard();
    expect(await within(card).findByText(EMAIL_STATUS_ERROR)).toBeInTheDocument();
    fail = false;
    await user.click(within(card).getByRole("button", { name: "Retry" }));
    expect(await within(card).findByText("Sends from pat@example.com.")).toBeInTheDocument();
  });

  it("needs a service date first, and says so", async () => {
    renderReview({}, { draft: testDraft((d) => ({ ...d, readings: { ...d.readings, date_iso: "" } })) });
    const card = await emailCard();
    expect(await within(card).findByText(EMAIL_NEEDS_DATE)).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Email bulletin…" })).toBeDisabled();
  });
});

describe("Review → Email the bulletin: the dialog (slice 5b-2)", () => {
  it("shows the contacts, the subject, the attachments and the prefilled message, and counts each person once", async () => {
    const { user, api } = renderReview();
    const dialog = await openDialog(user);
    expect(within(dialog).getByText("pat@example.com")).toBeInTheDocument();
    const broken = within(dialog).getByRole("checkbox", { name: /Two at once/ });
    expect(broken).toBeDisabled();
    expect(within(dialog).getByText(INVALID_CONTACT)).toBeInTheDocument();
    expect(within(dialog).getByRole("checkbox", { name: "office@example.org" })).not.toBeChecked();
    expect(within(dialog).getByText("Worship service for October 4, 2026")).toBeInTheDocument();
    expect(within(dialog).getByRole("checkbox", { name: /Bulletin copy \(Word\)/ })).toBeChecked();
    expect(within(dialog).getByRole("checkbox", { name: /Printed bulletin \(PDF\)/ })).not.toBeChecked();
    expect(within(dialog).getByText("worship_October_04_2026.docx")).toBeInTheDocument();
    expect(within(dialog).getByText("printed_bulletin_October_04_2026.pdf")).toBeInTheDocument();
    const message = within(dialog).getByRole("textbox", { name: "Message" });
    expect(message).toHaveValue("Hi! Here's the worship bulletin for this Sunday.");
    expect(message).toHaveAttribute("maxLength", "5000");
    expect(within(dialog).getByRole("button", { name: "Send" })).toBeDisabled();
    expect(within(dialog).getByText(CHOOSE_RECIPIENT)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    expect(within(dialog).getByRole("button", { name: "Send to 1 person" })).toBeEnabled();
    expect(within(dialog).queryByText(BCC_NOTE)).toBeNull();
    await user.type(within(dialog).getByRole("textbox", { name: "Other addresses" }), "MARY@example.org, organist@example.org");
    expect(within(dialog).getByRole("button", { name: "Send to 2 people" })).toBeEnabled();
    expect(within(dialog).getByText(BCC_NOTE)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("checkbox", { name: /Bulletin copy \(Word\)/ }));
    expect(within(dialog).getByText(CHOOSE_ATTACHMENT)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Send to 2 people" })).toBeDisabled();
    await user.click(within(dialog).getByRole("checkbox", { name: /Printed bulletin \(PDF\)/ }));
    expect(JSON.parse(window.localStorage.getItem(PREFS) ?? "null").attachments).toEqual(["pdf"]);
    expect(sends(api)).toEqual([]);
  });

  it("is a bottom sheet on a phone whose one scroll area holds Send, so the keyboard never hides it", async () => {
    const { user } = renderReview();
    const dialog = await openDialog(user);
    // Below md the sheet itself scrolls (5b-1's contact editor); from md the fields scroll above the buttons.
    expect(dialog.className).toContain("max-md:overflow-y-auto");
    expect(dialog.className).toContain("max-md:max-h-[85dvh]");
    const send = within(dialog).getByRole("button", { name: "Send" });
    const between: string[] = [];
    for (let el = send.parentElement; el !== null && el !== dialog; el = el.parentElement) between.push(el.className);
    expect(between.length).toBeGreaterThan(0);
    for (const className of between) {
      expect(className.split(/\s+/)).not.toContain("overflow-y-auto"); // nothing between Send and the sheet scrolls on a phone
      expect(className.split(/\s+/)).not.toContain("min-h-0");
    }
    expect(between.some((className) => className.split(/\s+/).includes("md:overflow-y-auto"))).toBe(false);
    const fields = within(dialog).getByRole("textbox", { name: "Message" }).closest("div.content-start");
    expect(fields?.className.split(/\s+/)).toContain("md:overflow-y-auto");
    expect(fields?.contains(send)).toBe(false);
  });

  it("allows at most 50 people", async () => {
    const { user } = renderReview();
    const dialog = await openDialog(user);
    const many = Array.from({ length: 51 }, (_, i) => `p${i}@example.org`).join(", ");
    await user.click(within(dialog).getByRole("textbox", { name: "Other addresses" }));
    await user.paste(many);
    expect(within(dialog).getByText(TOO_MANY)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Send to 51 people" })).toBeDisabled();
  });

  it("sends the service as it is now with a key, toasts, remembers the contacts and resets the message", async () => {
    window.localStorage.setItem(PREFS, JSON.stringify({ version: 1, contact_ids: [MARY.id, "gone"], attachments: ["docx", "pdf"] }));
    const { user, api } = renderReview({ "POST /bulletin-emails": SENT });
    const dialog = await openDialog(user);
    expect(within(dialog).getByRole("checkbox", { name: /Mary Jones/ })).toBeChecked();
    await user.click(within(dialog).getByRole("checkbox", { name: "office@example.org" }));
    const message = within(dialog).getByRole("textbox", { name: "Message" });
    await user.clear(message);
    await user.type(message, "See you Sunday.");
    await user.click(within(dialog).getByRole("button", { name: "Send to 2 people" }));
    expect(await screen.findByText("Email sent to 2 people.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
    const [request] = sends(api);
    expect(request.headers["x-church-id"]).toBe(GRACE.id);
    expect(request.headers["idempotency-key"]).toMatch(/^[0-9a-f-]{36}$/);
    expect(request.body).toMatchObject({
      contact_ids: [MARY.id, OFFICE.id],
      additional_emails: [],
      message: "See you Sunday.",
      attachments: ["docx", "pdf"],
      service: { service_date_iso: "2026-10-04" },
    });
    expect(JSON.parse(window.localStorage.getItem(PREFS) ?? "null")).toEqual({
      version: 1,
      contact_ids: [MARY.id, OFFICE.id],
      attachments: ["docx", "pdf"],
    });
    await user.click(within(await emailCard()).getByRole("button", { name: "Email bulletin…" }));
    expect(within(await screen.findByRole("dialog")).getByRole("textbox", { name: "Message" })).toHaveValue(
      "Hi! Here's the worship bulletin for this Sunday.",
    );
  });

  it("shows each field's refusal where it belongs and focuses the first", async () => {
    let answer = fakeError(422, "invalid_request", "The request was not valid.", {
      fields: { "additional_emails.1": "Not a valid value.", message: "Too long (max 5000 characters)." },
    });
    const { user } = renderReview({ "POST /bulletin-emails": () => answer });
    const dialog = await openDialog(user);
    const other = within(dialog).getByRole("textbox", { name: "Other addresses" });
    await user.type(other, "a@example.org, b@example.org");
    await user.click(within(dialog).getByRole("button", { name: "Send to 2 people" }));
    expect(await within(dialog).findByText("Not a valid value.")).toBeInTheDocument();
    expect(other).toHaveFocus();
    expect(other).toHaveAttribute("aria-invalid", "true");
    expect(within(dialog).getByText("Too long (max 5000 characters).")).toBeInTheDocument();
    answer = fakeError(422, "invalid_request", "Give each custom element a label.", {
      fields: { "custom_elements.0.label": "Give each custom element a label." },
    });
    await user.click(within(dialog).getByRole("button", { name: "Send to 2 people" }));
    expect(await within(dialog).findByText("Give each custom element a label.")).toBeInTheDocument();
    expect(document.querySelectorAll("[data-sonner-toast]")).toHaveLength(0);
  });

  it("refreshes the contacts when one is gone, and links to Hymns for a hymn that is gone", async () => {
    let answer = fakeError(404, "not_found", "One of the selected contacts no longer exists. Refresh the list and try again.", {
      details: { field: "contact_ids" },
    });
    const { user, api } = renderReview({ "POST /bulletin-emails": () => answer });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText("One of the selected contacts no longer exists. Refresh the list and try again.")).toBeInTheDocument();
    await waitFor(() => expect(api.requests.filter((r) => r.path === "/contacts")).toHaveLength(2));
    answer = fakeError(404, "not_found", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.", {
      details: { field: "hymns.response.hymn_id" },
    });
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByRole("link", { name: "Go to Hymns" })).toHaveAttribute("href", "/builder/hymns");
    expect(api.requests.filter((r) => r.path === "/contacts")).toHaveLength(2);
  });

  it("offers Connect Gmail when the connection is gone, keeping the form for the way back", async () => {
    const { user, api } = renderReview({
      "POST /bulletin-emails": fakeError(409, "gmail_not_connected", "Connect your Gmail first, then try again."),
      "POST /gmail-connection/auth-url": { auth_url: GOOGLE_URL },
    });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.type(within(dialog).getByRole("textbox", { name: "Other addresses" }), "organist@example.org");
    await user.click(within(dialog).getByRole("button", { name: "Send to 2 people" }));
    expect(await within(dialog).findByText("Connect your Gmail first, then try again.")).toBeInTheDocument();
    await waitFor(() => expect(api.requests.filter((r) => r.path === "/gmail-connection")).toHaveLength(2));
    await user.click(within(dialog).getByRole("button", { name: "Connect Gmail" }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith(GOOGLE_URL));
    expect(JSON.parse(window.sessionStorage.getItem(REOPEN_EMAIL_KEY) ?? "null")).toEqual({
      church_id: GRACE.id,
      contact_ids: [MARY.id],
      other_addresses: "organist@example.org",
      message: "Hi! Here's the worship bulletin for this Sunday.",
      attachments: ["docx"],
    });
  });

  it("after an uncertain send turns plain Send off, even after a reload, and only Send again anyway sends, with a new key", async () => {
    const UNCERTAIN =
      "Gmail didn't confirm the email, so it may already have been sent. Check your Gmail Sent folder before sending again.";
    const first = renderReview({
      "POST /bulletin-emails": fakeError(504, "upstream_timeout", UNCERTAIN, { details: { send_uncertain: true } }),
    });
    const dialog = await openDialog(first.user);
    await first.user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await first.user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText(UNCERTAIN)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Send to 1 person" })).toBeDisabled();
    expect(sends(first.api)).toHaveLength(1);
    const firstKey = sends(first.api)[0].headers["idempotency-key"];
    first.unmount(); // leaving Review, or a reload: this tab still knows

    const again = renderReview({ "POST /bulletin-emails": SENT });
    const reopened = await openDialog(again.user);
    expect(within(reopened).getByText(UNCERTAIN)).toBeInTheDocument();
    await again.user.click(within(reopened).getByRole("checkbox", { name: /Mary Jones/ }));
    expect(within(reopened).getByRole("button", { name: "Send to 1 person" })).toBeDisabled();
    await again.user.click(within(reopened).getByRole("button", { name: "Send again anyway" }));
    expect(await screen.findByText("Email sent to 2 people.")).toBeInTheDocument();
    expect(sends(again.api).map((r) => r.headers["idempotency-key"])).not.toContain(firstKey);
    expect(window.sessionStorage.getItem(uncertainSendKey(USER_ID, GRACE.id))).toBeNull();
  });

  it("after a lost connection says the email may have gone, and only Send again anyway sends", async () => {
    let first = true;
    const { user, api } = renderReview({
      "POST /bulletin-emails": () => {
        if (first) {
          first = false;
          throw new TypeError("Failed to fetch");
        }
        return SENT;
      },
    });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText(CONNECTION_LOST)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Send to 1 person" })).toBeDisabled();
    await user.click(within(dialog).getByRole("button", { name: "Send again anyway" }));
    expect(await screen.findByText("Email sent to 2 people.")).toBeInTheDocument();
    const [one, two] = sends(api).map((r) => r.headers["idempotency-key"]);
    expect(two).not.toBe(one);
  });

  it("offers Reconnect Gmail when Google dropped the grant", async () => {
    const { user } = renderReview({
      "POST /bulletin-emails": fakeError(502, "gmail_send_failed",
        "Your Gmail connection has expired or was removed. Reconnect Gmail and try again.",
        { details: { disconnected: true, send_uncertain: false } }),
    });
    const dialog = await openDialog(user);
    await user.click(within(dialog).getByRole("checkbox", { name: /Mary Jones/ }));
    await user.click(within(dialog).getByRole("button", { name: "Send to 1 person" }));
    expect(await within(dialog).findByText("Your Gmail connection has expired or was removed. Reconnect Gmail and try again.")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Reconnect Gmail" })).toBeInTheDocument();
  });

  it("with no contacts says so, links admins to Contacts, and still sends to typed addresses", async () => {
    const { user, api, unmount } = renderReview({ "GET /contacts": contactList([]), "POST /bulletin-emails": SENT });
    const card = await emailCard();
    await within(card).findByText("Sends from pat@example.com.");
    await user.click(within(card).getByRole("button", { name: "Email bulletin…" }));
    const opened = await screen.findByRole("dialog", { name: "Email the bulletin" });
    expect(await within(opened).findByText(NO_CONTACTS)).toBeInTheDocument();
    expect(within(opened).getByRole("link", { name: "Manage contacts" })).toHaveAttribute("href", "/settings/contacts");
    await user.type(within(opened).getByRole("textbox", { name: "Other addresses" }), "organist@example.org");
    await user.click(within(opened).getByRole("button", { name: "Send to 1 person" }));
    await waitFor(() => expect(sends(api)).toHaveLength(1));
    unmount();

    const member = renderReview({ "GET /contacts": fakeError(500, "internal_error", "Something went wrong.") }, { role: "member" });
    const memberCard = await emailCard();
    await within(memberCard).findByText("Sends from pat@example.com.");
    await member.user.click(within(memberCard).getByRole("button", { name: "Email bulletin…" }));
    const failing = await screen.findByRole("dialog", { name: "Email the bulletin" });
    expect(await within(failing).findByText(CONTACTS_ERROR)).toBeInTheDocument();
    expect(within(failing).getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(within(failing).queryByRole("link", { name: "Manage contacts" })).toBeNull();
  });
});

describe("Review → Email the bulletin: back from Google (slice 5b-2, flow B)", () => {
  function reopen(value: object) {
    window.sessionStorage.setItem(REOPEN_EMAIL_KEY, JSON.stringify(value));
  }

  it("waits for the status, then reopens the dialog with what was in it", async () => {
    reopen({ church_id: GRACE.id, contact_ids: [OFFICE.id], other_addresses: "organist@example.org", message: "Hello", attachments: ["pdf"] });
    let release: (value: unknown) => void = () => {};
    const held = new Promise((resolve) => {
      release = resolve;
    });
    renderReview({
      "GET /gmail-connection": async () => {
        await held;
        return gmailConnection();
      },
    });
    await emailCard();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).not.toBeNull();
    release(undefined);
    const dialog = await screen.findByRole("dialog", { name: "Email the bulletin" });
    expect(await within(dialog).findByRole("checkbox", { name: "office@example.org" })).toBeChecked();
    expect(within(dialog).getByRole("textbox", { name: "Other addresses" })).toHaveValue("organist@example.org");
    expect(within(dialog).getByRole("textbox", { name: "Message" })).toHaveValue("Hello");
    expect(within(dialog).getByRole("checkbox", { name: /Printed bulletin \(PDF\)/ })).toBeChecked();
    expect(within(dialog).getByRole("checkbox", { name: /Bulletin copy \(Word\)/ })).not.toBeChecked();
    expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).toBeNull();
  });

  it("waits for last week's bulletin to be carried in, then shows the printed bulletin's notes with the PDF", async () => {
    reopen({ church_id: GRACE.id, contact_ids: [MARY.id], attachments: ["pdf"] });
    let release: (value: unknown) => void = () => {};
    const held = new Promise((resolve) => {
      release = resolve;
    });
    const lastWeek = serviceBulletin({ announcements: { ...serviceBulletin().announcements, coffee_hour: "The Smiths" } });
    renderReview({
      "GET /services/previous-bulletin": async () => {
        await held;
        return previousBulletin({ service_date_iso: "2026-09-27", bulletin: lastWeek });
      },
    });
    expect(await within(await emailCard()).findByText("Sends from pat@example.com.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).not.toBeNull();
    release(undefined);
    const dialog = await screen.findByRole("dialog", { name: "Email the bulletin" });
    expect(within(dialog).getByText("From last week, not checked yet: coffee hour.")).toBeInTheDocument();
    expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).toBeNull();
  });

  it("forgets the request without reopening when still not connected (a cancel at Google) or for another church", async () => {
    reopen({ church_id: GRACE.id });
    const { unmount } = renderReview({ "GET /gmail-connection": gmailDisconnected() });
    expect(await within(await emailCard()).findByText(EMAIL_CONNECT)).toBeInTheDocument();
    await waitFor(() => expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).toBeNull());
    expect(screen.queryByRole("dialog")).toBeNull();
    unmount();

    reopen({ church_id: "22222222-2222-4222-8222-222222222222" });
    renderReview();
    expect(await within(await emailCard()).findByText("Sends from pat@example.com.")).toBeInTheDocument();
    await waitFor(() => expect(window.sessionStorage.getItem(REOPEN_EMAIL_KEY)).toBeNull());
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
  gg2013,
````

**with:**

````tsx
  gg2013,
  gmailConnection,
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    "GET /services/previous-bulletin": previousBulletin(),
````

**with:**

````tsx
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(), // slice 5b-2: the email card
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
      "Printed bulletin",
````

**with:**

````tsx
      "Printed bulletin",
      "Email the bulletin",
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
  churchProfile,
````

**with:**

````tsx
  churchProfile,
  gmailConnection,
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````tsx
    "GET /services/previous-bulletin": previousBulletin(),
````

**with:**

````tsx
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(), // slice 5b-2: Review's email card
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````tsx
  churchProfile,
````

**with:**

````tsx
  churchProfile,
  gmailConnection,
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````tsx
    "GET /services/previous-bulletin": previousBulletin(),
````

**with:**

````tsx
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(), // slice 5b-2: Review's email card
````

**In `frontend/src/components/settings/contacts-settings-page.test.tsx`, replace:**

````tsx
    expect(screen.getByText(CONTACTS_INTRO)).toBeInTheDocument();
````

**with:**

````tsx
    expect(screen.getByText(CONTACTS_INTRO)).toBeInTheDocument();
    expect(CONTACTS_INTRO).toBe("People you can email the bulletin to from the Review step."); // slice 5b-2
````

**In `frontend/src/components/settings/account-settings-page.test.tsx`, replace:**

````tsx
      "Connect the Gmail account you sign in with. The app gets permission only to send email for you; it can't read your mail.",
    ); // 5b-2a: true before emailing exists (5b-2b says what it is for)
````

**with:**

````tsx
      "Connect your Gmail to email bulletins from your own account. The app can only send email for you; it can't read your mail.",
    ); // 5b-2b: emailing is on Review now
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/builder/review src/components/settings/contacts-settings-page.test.tsx src/components/settings/account-settings-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the card does not exist yet; the caption and the Account sentence are 5b-2a's):
```
   × Settings → Account (slice 5b-2) > shows the connected address, and Disconnect shows the Connect button with no toast <t>ms
   × Settings → Contacts (slice 5b-1) > shows a member the list as text, with the note, a flag on a bad address, and no controls <t>ms
   × Review & send: the Word documents (slice 5a-1) > shows Still to do, the Archive card and both copies with what they hold, in that order, with no placeholder <t>ms
 FAIL  |dom| src/components/builder/review/email-card.test.tsx [ src/components/builder/review/email-card.test.tsx ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 3 ⎯⎯⎯⎯⎯⎯⎯
      Tests  3 failed | 47 passed (50)
```

- [ ] **Step 3: Write the send, the dialog and the card, put the card on Review, and set the caption**

**Create `frontend/src/lib/queries/email.ts`:**

````ts
/**
 * Emailing the bulletin (slice 5b spec, `useSendBulletinEmail`; slice 5b-2):
 * `POST /bulletin-emails` with the dialog's Idempotency-Key (90 s client
 * timeout, `lib/api/timeouts.ts`). The dialog shows every failure itself, so
 * nothing is toasted here; a 401 or a lost church still goes through the
 * cache's `handleAuthErrors` (`useChurchMutation`).
 */
import type { ApiError } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import type { BulletinEmailBody } from "@/lib/email";

import { useApi, useChurchMutation } from "./client";

export type BulletinEmailSent = components["schemas"]["BulletinEmailOut"];
export type SendBulletinEmail = { body: BulletinEmailBody; key: string };

export function useSendBulletinEmail() {
  const api = useApi();
  return useChurchMutation<BulletinEmailSent, ApiError, SendBulletinEmail>({
    mutationFn: ({ body, key }) =>
      api.church<BulletinEmailSent>("/bulletin-emails", { method: "POST", json: body, idempotencyKey: key }),
  });
}
````

**Create `frontend/src/components/builder/review/email-dialog.tsx`:**

````tsx
"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState, type FormEvent, type ReactNode } from "react";

import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { Button, buttonVariants } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { docxFilename, printedFilename } from "@/lib/download";
import { useDraft } from "@/lib/draft/context";
import { isDirty, stillNeeded } from "@/lib/draft/status";
import {
  ATTACHMENT_KINDS,
  ATTACHMENT_LABELS,
  bulletinEmailBody,
  bulletinEmailSubject,
  countRecipients,
  fieldTarget,
  MAX_RECIPIENTS,
  MESSAGE_MAX_LENGTH,
  parseAddressList,
  type AttachmentKind,
  type EmailForm,
  type FieldTarget,
} from "@/lib/email";
import { gmailErrorMessage } from "@/lib/gmail";
import { settleOutcome, type KeyTracker } from "@/lib/idempotency";
import { useContacts } from "@/lib/queries/contacts";
import { useSendBulletinEmail } from "@/lib/queries/email";
import { useStartGmailConnect } from "@/lib/queries/gmail";
import { keys } from "@/lib/queries/keys";

import { NotFilledInLines } from "./printed-card";

export const BCC_NOTE = "Recipients won't see each other's addresses (sent as BCC).";
export const CHOOSE_RECIPIENT = "Choose at least one recipient.";
export const TOO_MANY = `You can email at most ${MAX_RECIPIENTS} people at once.`;
export const CHOOSE_ATTACHMENT = "Choose at least one attachment.";
export const NO_CONTACTS = "No saved contacts yet. Type addresses below.";
export const CONTACTS_ERROR = "Couldn't load your contacts.";
export const INVALID_CONTACT = "This address doesn't look valid. An admin can fix it in Settings → Contacts.";
export const NOT_SAVED_NOTE = "Not saved to the archive yet. The attachments use the service as it is on screen now.";
export const CONNECTION_LOST =
  "We lost the connection before Gmail confirmed, so the email may already have been sent. Check your Gmail Sent folder before sending again.";
const REVIEW_PATH = "/builder/review";

/** One failed send, shown in the dialog: a message per place, and what the user can do next. */
type Problem = Partial<Record<FieldTarget, string>> & {
  action?: "connect" | "reconnect" | "again" | "hymns";
  sendDisabled?: boolean;
};

/** "1 person", "2 people". */
export function people(n: number): string {
  return `${n} ${n === 1 ? "person" : "people"}`;
}

/** "Not finished yet: 2 items under Still to do." */
function unfinishedNote(count: number): string {
  return `Not finished yet: ${count} ${count === 1 ? "item" : "items"} under Still to do.`;
}

type Props = {
  googleEmail: string;
  form: EmailForm;
  onFormChange(change: Partial<EmailForm>): void;
  tracker: KeyTracker;
  /** A send that may already have gone out (kept by the card in sessionStorage), or null. */
  uncertain: string | null;
  onUncertain(message: string | null): void;
  onClose(): void;
  onSent(count: number, contactIds: string[]): void;
};

/**
 * The email dialog (slice 5b spec, UX "Email dialog", amended 2026-10-06;
 * slice 5b-2): From, To (the church's contacts; one whose saved address the
 * send-time rule refuses is shown but cannot be chosen), Other addresses, the
 * BCC note from two people on, the subject, the two attachments (at least
 * one), the message (prefilled, editable), notes when the service is not
 * finished or not saved, the printed bulletin's notes while its PDF is
 * ticked, and **Send to N people**. Below `md` it is a bottom sheet, as the
 * Contacts page's editor (5b-1): the whole sheet scrolls, its buttons with
 * it, so the iPhone keyboard never leaves Send out of reach; from `md` it is
 * centred, the fields scrolling above the buttons. The form lives in the
 * card, so closing and reopening keeps it. While a send runs the dialog
 * cannot be closed (abandoning the wait would not stop Gmail). Every failure
 * shows here, where it belongs, never as a toast. After a send that may
 * already have gone out (Gmail did not confirm it, or the connection was
 * lost), plain Send stays off, even after a reload, until **Send again
 * anyway** sends with a new key.
 */
export function EmailDialog({ googleEmail, form, onFormChange, tracker, uncertain, onUncertain, onClose, onSent }: Props) {
  const church = useChurch();
  const { draft, peek } = useDraft();
  const queryClient = useQueryClient();
  const contacts = useContacts();
  const send = useSendBulletinEmail();
  const start = useStartGmailConnect();
  const slow = useStillWorking(send.isPending);
  const [problem, setProblem] = useState<Problem | null>(null);
  const toRef = useRef<HTMLFieldSetElement>(null);
  const otherRef = useRef<HTMLInputElement>(null);
  const messageRef = useRef<HTMLTextAreaElement>(null);
  const attachmentsRef = useRef<HTMLFieldSetElement>(null);

  const dateIso = draft.readings.date_iso;
  const items = contacts.data?.items ?? [];
  const chosen = items.filter((c) => c.email_valid && form.contactIds.includes(c.id));
  const extras = parseAddressList(form.otherAddresses);
  const count = countRecipients(
    chosen.map((c) => c.email),
    extras,
  );
  const missing = stillNeeded(draft).length;
  const blocked =
    count === 0 ? CHOOSE_RECIPIENT : count > MAX_RECIPIENTS ? TOO_MANY : form.attachments.length === 0 ? CHOOSE_ATTACHMENT : null;

  const change = (target: FieldTarget, update: Partial<EmailForm>) => {
    onFormChange(update);
    if (problem?.[target]) setProblem((p) => (p ? { ...p, [target]: undefined } : p));
  };

  const focusFirst = (found: Problem) => {
    if (found.to) toRef.current?.querySelector("input")?.focus();
    else if (found.other) otherRef.current?.focus();
    else if (found.attachments) attachmentsRef.current?.querySelector("input")?.focus();
    else if (found.message) messageRef.current?.focus();
  };

  function failed(e: ApiError) {
    if (e.status === 401 || isNoChurchAccess(e) || e.code === "aborted") return;
    const details = e.details ?? {};
    let found: Problem;
    if (e.status === 0) {
      found = { top: CONNECTION_LOST, action: "again" };
      onUncertain(CONNECTION_LOST);
    } else if (e.status === 422 && e.fields && Object.keys(e.fields).length > 0) {
      found = {};
      for (const [key, message] of Object.entries(e.fields)) {
        const target = fieldTarget(key);
        found[target] ??= message;
      }
    } else if (e.status === 404 && details.field === "contact_ids") {
      found = { to: e.message };
      void queryClient.invalidateQueries({ queryKey: keys.contacts(church.id) });
    } else if (e.status === 404 && typeof details.field === "string" && details.field.startsWith("hymns.")) {
      found = { top: e.message, action: "hymns" };
    } else if (e.code === "gmail_not_connected") {
      found = { top: e.message, action: "connect" };
      void queryClient.invalidateQueries({ queryKey: keys.gmailConnection() });
    } else if (e.code === "gmail_send_failed" && details.disconnected === true) {
      found = { top: e.message, action: "reconnect" };
      void queryClient.invalidateQueries({ queryKey: keys.gmailConnection() });
    } else if (details.send_uncertain === true) {
      found = { top: e.message, action: "again" };
      onUncertain(e.message);
    } else if (e.code === "gmail_not_configured") {
      found = { top: e.message, sendDisabled: true };
      void queryClient.invalidateQueries({ queryKey: keys.gmailConnection() });
    } else {
      found = { top: gmailErrorMessage(e) };
    }
    setProblem(found);
    focusFirst(found);
  }

  function submit({ again = false }: { again?: boolean } = {}) {
    if (send.isPending || blocked !== null || (uncertain !== null && !again)) return;
    const body = bulletinEmailBody(peek(), { ...form, contactIds: chosen.map((c) => c.id) });
    if (again) tracker.rotate();
    const key = tracker.keyFor(body);
    setProblem(null);
    send.mutate(
      { body, key },
      {
        onSuccess: (sent) => {
          tracker.settle("success");
          onUncertain(null);
          onSent(sent.recipient_count, body.contact_ids ?? []);
        },
        onError: (e) => {
          tracker.settle(settleOutcome(e));
          if (again) onUncertain(null); // answered: an uncertain answer sets it again in `failed`
          failed(e);
        },
      },
    );
  }

  function connect() {
    start.mutate({
      returnTo: REVIEW_PATH,
      reopen: {
        church_id: church.id,
        contact_ids: form.contactIds,
        other_addresses: form.otherAddresses,
        message: form.message,
        attachments: form.attachments,
      },
    });
  }

  const toggleContact = (id: string, on: boolean) =>
    change("to", { contactIds: on ? [...form.contactIds, id] : form.contactIds.filter((c) => c !== id) });
  const toggleAttachment = (kind: AttachmentKind, on: boolean) =>
    change("attachments", {
      attachments: ATTACHMENT_KINDS.filter((k) => (k === kind ? on : form.attachments.includes(k))),
    });

  // A failure of this visit, else a send that may already have gone out (this visit or an earlier one).
  const shown: Problem | null = problem ?? (uncertain !== null ? { top: uncertain, action: "again" } : null);

  let toBody: ReactNode;
  if (contacts.data) {
    toBody =
      items.length === 0 ? (
        <div className="grid gap-1 text-sm">
          <p>{NO_CONTACTS}</p>
          {isAdmin(church.role) ? (
            <Link href="/settings/contacts" className="w-fit font-medium underline underline-offset-4">
              Manage contacts
            </Link>
          ) : null}
        </div>
      ) : (
        <ul className="grid gap-1">
          {items.map((contact) => (
            <li key={contact.id}>
              <label
                className={`flex min-h-11 items-start gap-3 rounded-md px-1 py-2 ${contact.email_valid ? "cursor-pointer" : "opacity-70"}`}
              >
                <input
                  type="checkbox"
                  className="mt-0.5 size-5 shrink-0 accent-primary"
                  checked={contact.email_valid && form.contactIds.includes(contact.id)}
                  disabled={!contact.email_valid || send.isPending}
                  onChange={(event) => toggleContact(contact.id, event.target.checked)}
                />
                <span className="grid min-w-0 gap-0.5">
                  {contact.name !== null ? <span className="break-words">{contact.name}</span> : null}
                  <span className={contact.name !== null ? "text-sm text-muted-foreground break-all" : "break-all"}>
                    {contact.email}
                  </span>
                  {contact.email_valid ? null : (
                    <span className="text-sm text-amber-700 dark:text-amber-400">{INVALID_CONTACT}</span>
                  )}
                </span>
              </label>
            </li>
          ))}
        </ul>
      );
  } else if (contacts.isError) {
    toBody = (
      <ErrorState error={contacts.error} message={CONTACTS_ERROR} onRetry={() => void contacts.refetch()} retrying={contacts.isFetching} />
    );
  } else {
    toBody = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !send.isPending) onClose();
      }}
    >
      <DialogContent
        showCloseButton={false}
        className="max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto md:max-h-[calc(100dvh-2rem)] md:max-w-lg md:grid-rows-[auto_minmax(0,1fr)]"
      >
        <DialogHeader>
          <DialogTitle>Email the bulletin</DialogTitle>
        </DialogHeader>
        <form
          noValidate
          className="grid gap-4 md:min-h-0 md:grid-rows-[minmax(0,1fr)_auto]"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            submit();
          }}
        >
          <div className="grid content-start gap-5 md:overflow-y-auto">
            <div aria-live="polite" className="empty:hidden">
              {shown?.top ? (
                <div role="alert" className="grid gap-2 rounded-md border border-destructive/40 p-3 text-sm">
                  <p>{shown.top}</p>
                  {shown.action === "hymns" ? (
                    <Link
                      href="/builder/hymns"
                      onClick={onClose}
                      className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}
                    >
                      Go to Hymns
                    </Link>
                  ) : null}
                  {shown.action === "connect" || shown.action === "reconnect" ? (
                    <PendingButton size="touch" className="w-full sm:w-fit" pending={start.isPending} pendingLabel="Opening Google…" onClick={connect}>
                      {shown.action === "connect" ? "Connect Gmail" : "Reconnect Gmail"}
                    </PendingButton>
                  ) : null}
                  {shown.action === "again" ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="touch"
                      className="w-full sm:w-fit"
                      disabled={send.isPending || blocked !== null}
                      onClick={() => submit({ again: true })}
                    >
                      Send again anyway
                    </Button>
                  ) : null}
                </div>
              ) : null}
            </div>
            <p className="text-sm">
              <span className="text-muted-foreground">From </span>
              <span className="break-all">{googleEmail}</span>
            </p>
            <fieldset ref={toRef} className="grid gap-2" aria-describedby={problem?.to ? "email-to-error" : undefined}>
              <legend className="mb-1 text-sm font-medium">To</legend>
              {toBody}
              {problem?.to ? (
                <p id="email-to-error" role="alert" className="text-sm text-destructive">
                  {problem.to}
                </p>
              ) : null}
            </fieldset>
            <div className="grid gap-1.5">
              <Label htmlFor="email-other">Other addresses</Label>
              <Input
                id="email-other"
                ref={otherRef}
                type="text"
                inputMode="email"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                autoComplete="off"
                placeholder="name@example.com"
                className="h-11"
                value={form.otherAddresses}
                aria-invalid={problem?.other ? true : undefined}
                aria-describedby={problem?.other ? "email-other-help email-other-error" : "email-other-help"}
                onChange={(event) => change("other", { otherAddresses: event.target.value })}
              />
              <p id="email-other-help" className="text-sm text-muted-foreground">
                Separate addresses with commas.
              </p>
              {problem?.other ? (
                <p id="email-other-error" role="alert" className="text-sm text-destructive">
                  {problem.other}
                </p>
              ) : null}
            </div>
            {count >= 2 ? <p className="text-sm text-muted-foreground">{BCC_NOTE}</p> : null}
            <p className="text-sm">
              <span className="text-muted-foreground">Subject </span>
              {bulletinEmailSubject(dateIso)}
            </p>
            <fieldset ref={attachmentsRef} className="grid gap-1">
              <legend className="mb-1 text-sm font-medium">Attachments</legend>
              {ATTACHMENT_KINDS.map((kind) => (
                <label key={kind} className="flex min-h-11 cursor-pointer items-start gap-3 rounded-md px-1 py-2">
                  <input
                    type="checkbox"
                    className="mt-0.5 size-5 shrink-0 accent-primary"
                    checked={form.attachments.includes(kind)}
                    disabled={send.isPending}
                    onChange={(event) => toggleAttachment(kind, event.target.checked)}
                  />
                  <span className="grid min-w-0 gap-0.5">
                    <span>{ATTACHMENT_LABELS[kind]}</span>
                    <span className="text-sm text-muted-foreground break-all">
                      {kind === "docx" ? docxFilename("bulletin", dateIso) : printedFilename("pdf", dateIso)}
                    </span>
                  </span>
                </label>
              ))}
              {form.attachments.includes("pdf") ? (
                <div className="grid gap-1 px-1">
                  <NotFilledInLines />
                </div>
              ) : null}
              {problem?.attachments ? (
                <p role="alert" className="text-sm text-destructive">
                  {problem.attachments}
                </p>
              ) : null}
            </fieldset>
            <div className="grid gap-1.5">
              <Label htmlFor="email-message">Message</Label>
              <Textarea
                id="email-message"
                ref={messageRef}
                rows={4}
                maxLength={MESSAGE_MAX_LENGTH}
                value={form.message}
                aria-invalid={problem?.message ? true : undefined}
                aria-describedby={problem?.message ? "email-message-error" : undefined}
                onChange={(event) => change("message", { message: event.target.value })}
              />
              {problem?.message ? (
                <p id="email-message-error" role="alert" className="text-sm text-destructive">
                  {problem.message}
                </p>
              ) : null}
            </div>
            {missing > 0 || isDirty(draft) ? (
              <div className="grid gap-1 text-sm text-muted-foreground">
                {missing > 0 ? <p>{unfinishedNote(missing)}</p> : null}
                {isDirty(draft) ? <p>{NOT_SAVED_NOTE}</p> : null}
              </div>
            ) : null}
          </div>
          <DialogFooter className="max-md:rounded-none max-md:pb-[calc(1rem+env(safe-area-inset-bottom))]">
            {blocked !== null ? <p className="text-sm text-muted-foreground sm:mr-auto sm:self-center">{blocked}</p> : null}
            <DialogClose disabled={send.isPending} render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>
              Cancel
            </DialogClose>
            <PendingButton
              type="submit"
              size="touch"
              className="md:h-8"
              pending={send.isPending}
              pendingLabel={slow ? "Still working…" : "Sending…"}
              disabled={blocked !== null || problem?.sendDisabled === true || uncertain !== null}
            >
              {count === 0 ? "Send" : `Send to ${people(count)}`}
            </PendingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
````

**Create `frontend/src/components/builder/review/email-card.tsx`:**

````tsx
"use client";

import { MailIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { shouldCarry } from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { hasReadingsError, hasServiceDate } from "@/lib/draft/status";
import {
  clearUncertainSend,
  defaultBulletinMessage,
  parseReopen,
  readEmailPrefs,
  readUncertainSend,
  writeEmailPrefs,
  writeUncertainSend,
  type EmailForm,
} from "@/lib/email";
import { REOPEN_EMAIL_KEY } from "@/lib/gmail";
import { createKeyTracker } from "@/lib/idempotency";
import { useMeContext } from "@/lib/me-context";
import { useGmailConnection, useStartGmailConnect } from "@/lib/queries/gmail";
import { usePreviousBulletin } from "@/lib/queries/services";
import { readSession, removeSession } from "@/lib/storage";

import { EmailDialog, people } from "./email-dialog";

export const EMAIL_SUMMARY = "Send the bulletin and a short message from your own Gmail.";
export const EMAIL_STATUS_ERROR = "Couldn't check your Gmail connection.";
export const EMAIL_NOT_CONFIGURED = "Emailing isn't set up on this deployment.";
export const EMAIL_CONNECT = "Connect your Gmail to email the bulletin from your own account.";
export const EMAIL_NEEDS_DATE = "Choose a service date on step 1 to email the bulletin.";
export const EMAIL_FIX_READINGS = "Fix the readings on step 1 to email the bulletin.";
const REVIEW_PATH = "/builder/review";

/**
 * The "Email the bulletin" card on Review (slice 5b spec, UX "Review step:
 * Email the bulletin card"; slice 5b-2), after the printed bulletin. It shows
 * the caller's Gmail connection: loading, a failed check (Retry), not set up
 * here, not connected (**Connect Gmail**, which comes back here), or
 * connected ("Sends from …" and **Email bulletin…**, which needs a service
 * date and readings without errors, as the downloads do; nothing else blocks
 * it). It keeps the dialog's form (closing and reopening keeps it, a sent
 * email resets the message), its Idempotency-Key tracker and a send that may
 * already have gone out (sessionStorage, so a reload keeps plain Send off).
 * After a connect from Review it reopens the dialog with what was in it, once
 * the status says connected, only in the church it was opened in, and only
 * after last week's bulletin has been carried in (the printed card's
 * `useBulletinCarry`), so a PDF sent at once has it.
 */
export function EmailCard() {
  const church = useChurch();
  const { user } = useMeContext();
  const { draft } = useDraft();
  const status = useGmailConnection();
  const start = useStartGmailConnect();
  const [tracker] = useState(() => createKeyTracker());
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<EmailForm | null>(null);
  const [uncertain, setUncertain] = useState(() => readUncertainSend(user.id, church.id));
  // Read only, never fetched here: the printed card's useBulletinCarry fetches and applies it.
  const carry = usePreviousBulletin(draft.readings.date_iso, false);
  const dateIso = draft.readings.date_iso;
  const dated = hasServiceDate(draft);
  const readingsError = hasReadingsError(draft);

  const freshForm = (): EmailForm => {
    const prefs = readEmailPrefs(user.id, church.id);
    return { contactIds: prefs.contact_ids, otherAddresses: "", message: defaultBulletinMessage(dateIso), attachments: prefs.attachments };
  };

  // Back from Google (flow B): the request is read once, when the card mounts, and decided once the
  // status has settled and, when it reopens the dialog, once last week's bulletin is carried in or its
  // lookup failed (during render, so no effect sets state); then it is forgotten either way.
  const [reopenRaw, setReopenRaw] = useState(() => readSession(REOPEN_EMAIL_KEY));
  const settled = !status.isPending;
  const reopen = reopenRaw !== null && settled ? parseReopen(reopenRaw, church.id) : null;
  const carrying = reopen !== null && status.data?.connected === true && shouldCarry(draft) && !carry.isError;
  if (reopenRaw !== null && settled && !carrying) {
    setReopenRaw(null);
    if (reopen !== null && status.data?.connected === true) {
      const prefs = readEmailPrefs(user.id, church.id);
      setForm({
        contactIds: reopen.contact_ids ?? prefs.contact_ids,
        otherAddresses: reopen.other_addresses ?? "",
        message: reopen.message ?? defaultBulletinMessage(dateIso),
        attachments: reopen.attachments && reopen.attachments.length > 0 ? reopen.attachments : prefs.attachments,
      });
      setOpen(true);
    }
  }
  useEffect(() => {
    if (settled && !carrying) removeSession(REOPEN_EMAIL_KEY);
  }, [settled, carrying]);

  let body;
  if (status.data) {
    const { configured, google_email } = status.data;
    if (!configured) {
      body = <p className="text-sm">{EMAIL_NOT_CONFIGURED}</p>;
    } else if (!status.data.connected || google_email === null) {
      body = (
        <>
          <p className="text-sm">{EMAIL_CONNECT}</p>
          <PendingButton
            size="touch"
            className="w-full sm:w-fit"
            pending={start.isPending}
            pendingLabel="Opening Google…"
            onClick={() => start.mutate({ returnTo: REVIEW_PATH, reopen: { church_id: church.id } })}
          >
            Connect Gmail
          </PendingButton>
        </>
      );
    } else {
      const disabled = !dated || readingsError;
      body = (
        <>
          <p className="text-sm break-all">Sends from {google_email}.</p>
          {!dated ? <p className="text-sm text-muted-foreground">{EMAIL_NEEDS_DATE}</p> : null}
          {dated && readingsError ? <p className="text-sm text-muted-foreground">{EMAIL_FIX_READINGS}</p> : null}
          <Button
            size="touch"
            className="w-full sm:w-fit"
            disabled={disabled}
            onClick={() => {
              setForm((current) => current ?? freshForm());
              setOpen(true);
            }}
          >
            <MailIcon data-icon="inline-start" aria-hidden="true" />
            Email bulletin…
          </Button>
          {open && form !== null ? (
            <EmailDialog
              googleEmail={google_email}
              form={form}
              onFormChange={(change) => {
                setForm((current) => (current ? { ...current, ...change } : current));
                if (change.attachments) writeEmailPrefs(user.id, church.id, { attachments: change.attachments });
              }}
              tracker={tracker}
              uncertain={uncertain}
              onUncertain={(message) => {
                setUncertain(message);
                if (message === null) clearUncertainSend(user.id, church.id);
                else writeUncertainSend(user.id, church.id, message);
              }}
              onClose={() => setOpen(false)}
              onSent={(count, contactIds) => {
                writeEmailPrefs(user.id, church.id, { contact_ids: contactIds });
                setForm((current) =>
                  current ? { ...current, otherAddresses: "", message: defaultBulletinMessage(dateIso) } : current,
                );
                setOpen(false);
                toast.success(`Email sent to ${people(count)}.`);
              }}
            />
          ) : null}
        </>
      );
    }
  } else if (status.isError) {
    body = (
      <ErrorState error={status.error} message={EMAIL_STATUS_ERROR} onRetry={() => void status.refetch()} retrying={status.isFetching} />
    );
  } else {
    body = (
      <>
        <Skeleton className="h-4 w-2/3" />
        <Button size="touch" className="w-full sm:w-fit" disabled>
          <MailIcon data-icon="inline-start" aria-hidden="true" />
          Email bulletin…
        </Button>
      </>
    );
  }

  return (
    <section aria-labelledby="email-title" className="grid gap-4 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="email-title" className="text-base font-medium">
          Email the bulletin
        </h2>
        <p className="text-sm text-muted-foreground">{EMAIL_SUMMARY}</p>
      </div>
      {body}
    </section>
  );
}
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````tsx
import { EditingBanner } from "./editing-banner";
````

**with:**

````tsx
import { EditingBanner } from "./editing-banner";
import { EmailCard } from "./email-card";
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````tsx
 * (printed bulletin spec, PR 1). No order-of-worship
 * preview: the Liturgy step already shows the order. Email comes in 5b.
````

**with:**

````tsx
 * (printed bulletin spec, PR 1), and emailing the bulletin (slice 5b-2). No
 * order-of-worship preview: the Liturgy step already shows the order.
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````tsx
      <PrintedCard />
````

**with:**

````tsx
      <PrintedCard />
      <EmailCard />
````

**In `frontend/src/components/settings/contacts-settings-page.tsx`, replace:**

````tsx
export const CONTACTS_INTRO = "People you can email the bulletin to. Emailing it from the Review step comes in a later update.";
````

**with:**

````tsx
export const CONTACTS_INTRO = "People you can email the bulletin to from the Review step.";
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
 * unchecked.
 */
function NotFilledInLines() {
````

**with:**

````tsx
 * unchecked. The email dialog shows the same lines while its PDF is ticked
 * (slice 5b-2).
 */
export function NotFilledInLines() {
````

**In `frontend/src/components/settings/account-settings-page.tsx`, replace:**

````tsx
  "Connect the Gmail account you sign in with. The app gets permission only to send email for you; it can't read your mail.";
````

**with:**

````tsx
  "Connect your Gmail to email bulletins from your own account. The app can only send email for you; it can't read your mail.";
````

- [ ] **Step 4: See them pass three times, and the suite**

Run: `(cd frontend && npx vitest run src/components/builder/review 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (three times) then `(cd frontend && npx vitest run src/components/builder/builder-shell.test.tsx src/components/builder/liturgy/liturgy-step.test.tsx src/components/settings 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
three times `      Tests  46 passed (46)`, with no `×`; `      Tests  93 passed (93)`; ` Test Files  100 passed (100)` and `      Tests  829 passed (829)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/queries/email.ts frontend/src/components/builder/review/email-dialog.tsx frontend/src/components/builder/review/email-card.tsx frontend/src/components/builder/review/email-card.test.tsx frontend/src/components/builder/review/printed-card.tsx frontend/src/components/builder/review/review-send-step.tsx frontend/src/components/builder/review/review-send-step.test.tsx frontend/src/components/builder/builder-shell.test.tsx frontend/src/components/builder/liturgy/liturgy-step.test.tsx frontend/src/components/settings/contacts-settings-page.tsx frontend/src/components/settings/contacts-settings-page.test.tsx frontend/src/components/settings/account-settings-page.tsx frontend/src/components/settings/account-settings-page.test.tsx
git commit -q -m "Slice 5b-2: the Email the bulletin card and dialog on Review" -m "The last card on Review shows the Gmail connection and opens the dialog:
the church's contacts (a flagged one shown but not choosable), other
addresses, the subject, the two attachments (at least one, remembered),
the prefilled message and Send to N people, with the BCC note and the
50-person cap, as a bottom sheet on a phone. Every failure shows in the
dialog where the 5b spec puts it; after an uncertain send plain Send
stays off (kept in the tab) and only Send again anyway sends; Connect or
Reconnect Gmail returns to Review and reopens the dialog with its form
once last week's bulletin is carried in; a ticked PDF shows the printed
card's notes. The Contacts caption and the Account page's Gmail sentence
now say emailing is on the Review step." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1818 passed, 27 skipped`; frontend `829 passed` in 100 files.

### Task 17: Docs: the email's manual checks (clarification 23)

**Files:**
- Modify: `docs/manual-verification.md`

- [ ] **Step 1: Append the items**

Items 11-16, after T10's.

**Append to `docs/manual-verification.md`:**

````markdown
- [ ] (owner, after 5b-2) **11.** **Review & send** → **Email the bulletin** says "Sends from" your address. Tap **Email bulletin…**: the subject reads "Worship service for" the service date with no leading zero, and **Bulletin copy (Word)** is ticked; tick **Printed bulletin (PDF)** too. Type your own address under **Other addresses** (only yours) and tap **Send to 1 person**: "Email sent to 1 person." The email has you in To, the message and both files, and both open on the phone. If you have a second address of your own, send again to both: each copy shows only the sender in To, and Gmail's Sent copy shows both in Bcc.
- [ ] (owner, after 5b-2) **12.** Open **Email bulletin…** again: **Printed bulletin (PDF)** is still ticked (remembered on this phone). With the keyboard open in **Message**, **Send** can still be reached and the box is not covered. At 375 px nothing in the dialog scrolls sideways. Close it with **Cancel**.
- [ ] (owner, after 5b-2) **13.** **Settings** → **Account** → **Disconnect**. On **Review & send** the card says "Connect your Gmail to email the bulletin from your own account."; tap its **Connect Gmail**: after Google you come back to **Review & send** and the email dialog opens by itself. **Cancel**; **Account** says "Connected as" your address.
- [ ] **14.** Double-tap **Send to 1 person**: one email arrives.
- [ ] **15.** A contact flagged on the Contacts page shows in the dialog with "This address doesn't look valid. An admin can fix it in Settings → Contacts." and cannot be ticked.
- [ ] **16.** Switch church with the dialog open: it closes; opening it again lists the other church's contacts.
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected:**
`89 passed in <t>s`; `4`; `0`; ` 1 file changed, 6 insertions(+)`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md
git commit -q -m "Docs: slice 5b-2 manual checks for emailing the bulletin" -m "docs/manual-verification.md → Slice 5b gains items 11-16: emailing the
bulletin to the owner's own address with both attachments, the BCC check,
the remembered attachment and the dialog with the keyboard open, a
reconnect from Review that reopens the dialog, a double tap, a flagged
contact, and a church switch with the dialog open." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1818 passed, 27 skipped`; frontend `829 passed` in 100 files.


## Verification, the PR, the owner's setup, the merge (T18-T19)

### Task 18: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`. **Two PRs:** run this task after T10 for 5b-2a and again after T17 for 5b-2b, with the counts, paths and texts marked A or B below; one PR: after T17, with those marked "one PR".

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
ls backend/migrations/versions | grep -c '^0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `7`. If `main` moved (for 5b-2b it has: the 5b-2a merge and its records PR): `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 18)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the frontend three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/settings|/gmail")
```

**Expected** (one PR, or 5b-2b): `1825 passed, 27 skipped in <t>s`; three times ` Test Files  100 passed (100)` and `      Tests  835 passed (835)` (5b-2a: `1752 passed, 27 skipped in <t>s`; three times ` Test Files  98 passed (98)` and `      Tests  801 passed (801)`) with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s` and the route lines `├ ○ /gmail/callback`, `├ ○ /settings`, `├ ○ /settings/account`, `├ ○ /settings/church` and `├ ○ /settings/contacts` and no `Error` (a font `Failed to fetch` only: say so and rely on CI).

- [ ] **Step 3 (agent): The API files match, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -nE "^(import|from) (fastapi|starlette|streamlit)|os\.getenv|^import requests" backend/google_oauth.py backend/bulletin_email.py backend/usecases/email.py backend/integrations/http.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff origin/main...HEAD -- backend frontend/src | grep '^+' | grep -c '—'
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations backend/db .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); `imports grep exit 1`; `raw html grep exit 1`; `0` (no em dash in an added line of code or tests); exactly these paths (one PR; `docs/ops-runbook.md` is there only while the 5b-1 records PR is not merged):
```
M	backend/.env.example
M	backend/api/deps.py
M	backend/api/idempotency.py
M	backend/api/main.py
M	backend/api/ratelimit.py
A	backend/api/routes/bulletin_emails.py
A	backend/api/routes/gmail.py
M	backend/api/settings.py
M	backend/api/startup.py
A	backend/bulletin_email.py
M	backend/email_addresses.py
M	backend/email_contacts.py
M	backend/google_oauth.py
M	backend/integrations/http.py
A	backend/tests/fake_google.py
A	backend/tests/fixtures/shared/bulletin_email.json
A	backend/tests/test_api_bulletin_emails.py
A	backend/tests/test_api_gmail.py
A	backend/tests/test_bulletin_email.py
M	backend/tests/test_email_addresses.py
M	backend/tests/test_email_contacts.py
D	backend/tests/test_gmail_exchange.py
A	backend/tests/test_gmail_state_postgres.py
D	backend/tests/test_gmail_token_store.py
A	backend/tests/test_google_oauth.py
M	backend/tests/test_http_client.py
M	backend/tests/test_idempotency.py
M	backend/tests/test_no_streamlit_in_core.py
D	backend/tests/test_oauth_state.py
M	backend/tests/test_ratelimit.py
M	backend/tests/test_route_guards.py
M	backend/tests/test_startup.py
A	backend/tests/test_usecase_email.py
A	backend/usecases/email.py
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-06-slice-5b2-gmail-email.md
M	docs/superpowers/specs/2026-09-25-slice-5b-gmail-email-design.md
A	frontend/src/app/(signed-in)/(church)/settings/account/page.tsx
A	frontend/src/app/(signed-in)/gmail/callback/page.tsx
M	frontend/src/components/builder/builder-shell.test.tsx
M	frontend/src/components/builder/liturgy/liturgy-step.test.tsx
A	frontend/src/components/builder/review/email-card.test.tsx
A	frontend/src/components/builder/review/email-card.tsx
A	frontend/src/components/builder/review/email-dialog.tsx
M	frontend/src/components/builder/review/printed-card.tsx
M	frontend/src/components/builder/review/review-send-step.test.tsx
M	frontend/src/components/builder/review/review-send-step.tsx
A	frontend/src/components/gmail/gmail-callback.test.tsx
A	frontend/src/components/gmail/gmail-callback.tsx
A	frontend/src/components/settings/account-settings-page.test.tsx
A	frontend/src/components/settings/account-settings-page.tsx
M	frontend/src/components/settings/contacts-settings-page.test.tsx
M	frontend/src/components/settings/contacts-settings-page.tsx
M	frontend/src/components/settings/sections.ts
M	frontend/src/components/settings/settings-layout.test.tsx
M	frontend/src/lib/api/client.test.ts
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/timeouts.ts
M	frontend/src/lib/api/types.ts
M	frontend/src/lib/draft/prune.test.ts
M	frontend/src/lib/draft/prune.ts
A	frontend/src/lib/email.test.ts
A	frontend/src/lib/email.ts
A	frontend/src/lib/gmail.test.ts
A	frontend/src/lib/gmail.ts
M	frontend/src/lib/idempotency.test.ts
M	frontend/src/lib/idempotency.ts
A	frontend/src/lib/queries/email.ts
A	frontend/src/lib/queries/gmail.ts
A	frontend/src/lib/supabase/client.test.ts
M	frontend/src/lib/supabase/client.ts
M	frontend/src/lib/urls.test.ts
M	frontend/src/lib/urls.ts
M	frontend/src/test/fixtures/index.ts
```
(5b-2a: the lines of T1-T10's files, the plan and the build review fixes' three paths (`test_gmail_state_postgres.py`, `client.test.ts`, the 5b spec); 5b-2b: the lines of T11-T17's files, `api/main.py`, the two API files and the two `account-settings-page` files again (as `M`); T18's Step 3 for 5b-2b also lists any plan commit since 5b-2a.) Then `0`; the subjects oldest first: the plan commits (`WIP plan: …` and `Plan: slice 5b-2 (…)`) and any later plan commit, then the task subjects as written above (T1-T17; or T1-T10, or T11-T17), then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this (one PR), and wait for a clear yes:

> Slice 5b-2 is verified on this machine: backend 1825 passed, 27 skipped (1669 before); frontend 835 tests in 100 files (780 before), three runs in a row; typecheck, lint and the production build are clean. It adds Settings → Account, where each person connects their own Gmail, and an **Email the bulletin** card on Review: you pick contacts or type addresses, choose the Word copy, the printed PDF or both, and it is sent from your own Gmail (several people go in Bcc). There is no database change and no new package. Before it can be merged you will add one address in Google Cloud Console and three settings in Railway; I will walk you through that one step at a time and never need to see the secret. May I open the pull request as a **draft** titled "Slice 5b-2: the Gmail connection and emailing the bulletin", so the checks run? Merging stays with you.

(5b-2a: "Slice 5b-2a is verified … backend 1752 passed, 27 skipped (1669 before); frontend 801 tests in 98 files (780 before) … It adds Settings → Account, where each person connects their own Gmail; emailing comes in 5b-2b. … May I open the pull request as a **draft** titled "Slice 5b-2a: the Gmail connection" …". 5b-2b: "Slice 5b-2b is verified … backend 1825 passed, 27 skipped (1752 before); frontend 835 tests in 100 files (801 before) … It adds the **Email the bulletin** card on Review … No Google or Railway step this time. May I open the pull request as a **draft** titled "Slice 5b-2b: emailing the bulletin" …".)

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/5b2-pr-body.md" <<'BODY'
Slice 5b-2: the Gmail connection and emailing the bulletin (the second of 5b's two PRs; owner's 5b planning answers of 2026-10-06). Spec: docs/superpowers/specs/2026-09-25-slice-5b-gmail-email-design.md (its amendment of 2026-10-06). Plan: docs/superpowers/plans/2026-10-06-slice-5b2-gmail-email.md. No database change, no new package; the GOOGLE_* variables Railway already lists are read now.

- google_oauth.py rewritten for the API (Streamlit's functions removed with their tests, every kept assertion ported): GoogleOAuthConfig, the consent URL with a login hint, single-use states, the token store with only_if_token, and the Google calls through integrations.http.post, each failure one kind.
- GET, POST and DELETE /gmail-connection (user-scoped) and the startup's "Gmail: …" lines; usecases/email.py.
- /gmail/callback (one POST per state under StrictMode; the Supabase browser client no longer reads sign-ins from the URL) and Settings → Account.
- POST /bulletin-emails: any member; the bulletin copy and/or the printed PDF built from the posted service; one recipient in To, several in Bcc with the sender in To, at most 50; a required Idempotency-Key whose replay covers a send that may have gone out (run_idempotent's new store_error), so nothing is sent twice; the hourly email limit charged only when Gmail is reached; no database connection held during a Google call.
- Review: the Email the bulletin card and dialog (remembered contacts and attachments, inline errors, Send again anyway, Connect or Reconnect Gmail that reopens the dialog). The Contacts caption now points to it.
- docs/manual-verification.md → Slice 5b: items 7-16.

Before merge: the owner adds the /gmail/callback redirect URIs in Google Cloud Console and sets the three GOOGLE_* variables in Railway (Task 19). After merge: a short phone check, then a "Slice 5b-2 record" in docs/ops-runbook.md.

Tests: backend 1669 → 1825 passed, 27 skipped; frontend 780 → 835 in 94 → 100 files

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 5b-2: the Gmail connection and emailing the bulletin" \
  --body-file "<scratch>/5b2-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. (Two PRs: the same body cut to its half, the title of Step 4, and the tests line `backend 1669 → 1752 passed …; frontend 780 → 801 in 94 → 98 files` for 5b-2a, `backend 1752 → 1825 …; frontend 801 → 835 in 98 → 100 files` for 5b-2b.) **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers as Step 2's, and backend-postgres `26 passed`. Then send: "PR #<N> is green: backend … passed, 27 skipped; … frontend tests in … files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you, after the Google and Railway steps." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_http_client.py` | T1 |
| `test_google_oauth.py`, `test_no_streamlit_in_core.py` (`google_oauth`) | T2, T3 |
| `test_startup.py` | T4 |
| `test_usecase_email.py` (connection), `test_no_streamlit_in_core.py` (`usecases.email`) | T5 |
| `test_api_gmail.py`, `test_route_guards.py`, `test_openapi_contract.py` (5b-2a) | T6 |
| `gmail.test.ts`, `urls.test.ts`, `client.test.ts` | T7 |
| `gmail-callback.test.tsx` | T8 |
| `account-settings-page.test.tsx`, `settings-layout.test.tsx` | T9 |
| `test_slice1_docs.py`, `test_docs.py` | T10, T17 |
| `test_bulletin_email.py`, `test_email_addresses.py`, `test_no_streamlit_in_core.py` (`bulletin_email`) | T11 |
| `test_idempotency.py`, `test_email_contacts.py` | T12 |
| `test_usecase_email.py` (send) | T13 |
| `test_api_bulletin_emails.py`, `test_openapi_contract.py` (5b-2b) | T14 |
| `email.test.ts`, `idempotency.test.ts`, `prune.test.ts` | T15 |
| `email-card.test.tsx`, `review-send-step.test.tsx`, `builder-shell.test.tsx`, `liturgy-step.test.tsx`, `contacts-settings-page.test.tsx` | T16 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, slice 5b-2 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: as Step 2.

### Task 19: The owner's Google and Railway setup, the merge, the phone check, the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate (production stays at `0007_bulletin_images`). Railway serves the new routes, Vercel the pages. **Steps 1-5 (the setup) come before the merge, and only once** (with two PRs: before the 5b-2a merge). Each owner step is sent **one at a time** (send one, wait for the report or "next"), in plain words. The agent never asks for, reads, prints or stores the client id or secret: the owner copies them inside Google Cloud Console and Railway. The phone check is on the production URL, in the owner's own church, signed in as its owner; every test email goes only to the owner's own addresses. The agent writes each result into `<scratch>/5b2-t19-results.md` (not committed). Record what the pages showed and yes/no answers, never an email address, a name, a token, a code from the address bar or a church id.

**Files:** Modify (the records PR, Step 13): `docs/ops-runbook.md`: insert `### Slice 5b-2 record` right before `## Backups` (after the last record above it, today `### Slice 5b-1 record`, whose table's last row starts `| Follow-ups |`); in the same commit, the Railway table's `GOOGLE_*` row and the "Google OAuth client "Liturgy"" paragraph. `###` headings, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (OWNER): Setup 1 of 5: add the new return address in Google Cloud Console**

> Please open https://console.cloud.google.com on a computer and sign in with the Google account that owns the app's sign-in setup. At the top, make sure the project is the one with the OAuth client named "Liturgy" (the one the old Streamlit app uses). In the menu choose **APIs & Services**, then **Credentials**, and click the client **Liturgy** under "OAuth 2.0 Client IDs". Under **Authorized redirect URIs**, click **Add URI** and paste `https://worship-service-builder.vercel.app/gmail/callback`; click **Add URI** again and paste `http://localhost:3000/gmail/callback`. Do not remove or change any address already listed. Click **Save**. Did it save without an error? If Google shows a message about the domain (for example that it must be an authorized domain), please copy the message's words to me, without any ids or secrets.

If Google refuses the address (B's risk 3: `vercel.app` is a public suffix), stop the setup and tell the owner: "Google wants proof that the app's address is ours before it accepts it. That needs a separate small piece of work (adding Google's verification to the site, or a domain of your own). Nothing is broken; the new code stays unmerged until then." Record it and end the task there (the PR stays open).

- [ ] **Step 2 (OWNER): Setup 2 of 5: the consent screen's publishing status**

> Still in **APIs & Services**, open **OAuth consent screen** (it may be called **Google Auth Platform**, then **Audience**). What does it say under **Publishing status**: **Testing** or **In production**? If it says Testing, look at **Test users** on the same page: is the Google account of everyone who will email bulletins listed there? (In Testing only listed test users can connect; anyone else sees "Access blocked", and each connection ends after 7 days.) Please do not change anything now unless you already decided to.

Record the status and, for Testing, whether every sender is a test user (yes/no, never the addresses). If **Testing**, owner question 5's answer applies (recommended: switch to In production, after which each person sees "Google hasn't verified this app" when they connect, probably on every connect, and reconnects once after the switch; or stay in Testing, add every sender as a test user and reconnect weekly); the owner changes it there, or not, now or later.

- [ ] **Step 3 (OWNER): Setup 3 of 5: the client id and secret in Railway**

> Now open https://railway.app, the project, the **API** service (church-production), and its **Variables** tab. Look for `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. They must hold exactly the same values the Streamlit app uses (in Streamlit Cloud: the app **liturgy-frozen** → **Settings** → **Secrets**, the lines `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`; or in Google Cloud Console → **Credentials** → **Liturgy**, the Client ID, and the secret you saved in your password manager). If either is missing or different, copy the value from there and paste it into Railway yourself. Please do not paste either value into this chat. Tell me only: were both there already with the same values, or did you add or change them?

- [ ] **Step 4 (OWNER): Setup 4 of 5: the return address in Railway**

> In the same **Variables** tab, set `GOOGLE_OAUTH_REDIRECT_URI` to exactly `https://worship-service-builder.vercel.app/gmail/callback` (no space, no slash at the end). If it is already there with another value (for example the old Streamlit address), replace it. Then click **Deploy** (Railway may say "Apply changes") so the new values take effect. Tell me when the deploy has finished.

- [ ] **Step 5 (OWNER, then agent): Setup 5 of 5: the startup log**

> In Railway, open the **API** service → **Deployments** → the newest deployment → **Deploy Logs**. Near the top you will see lines starting `Database:` and `AI:`. Is there a line that says exactly `Gmail: configured`? Is there any other line that starts with `Gmail:` (a warning)? If there is a warning, copy its words to me (they never contain a secret).

Expected: `Gmail: configured` and no other `Gmail:` line. A warning names what to fix (a missing variable, or an address that is not `https://worship-service-builder.vercel.app/gmail/callback`, or one whose site is not in `CORS_ORIGINS`); send the owner the one-line fix and ask again. Before the merge, the deployed code is the old one, which does not read these variables yet: if no `Gmail:` line appears at all, the check moves to right after the merge's deploy (Step 7), and Steps 3-4 are still done now so the merge's deploy starts configured.

- [ ] **Step 6 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (slice 5b-2: the Gmail connection and emailing the bulletin) is ready, green and up to date with main, and the Google and Railway steps are done. There is no database change. May I merge it with a merge commit?" (5b-2a: "… (slice 5b-2a: the Gmail connection) …"; 5b-2b: "… (slice 5b-2b: emailing the bulletin) …, with no Google or Railway step this time.") On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about three minutes for Railway and Vercel before Step 7; a failed deploy keeps the old version running (Step R).

- [ ] **Step 7 (OWNER, then agent): Phone, step 1: Settings → Account and connecting Gmail (A; manual-verification items 7-8)**

If Step 5 found no `Gmail:` line, first: "In Railway's newest deployment's **Deploy Logs**, is there a line `Gmail: configured`, and no other line starting `Gmail:`?" Then:

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload. Tap **Settings**: are the sections **Church**, **Bulletin**, **Contacts** and **Account**, all on screen without sideways scrolling? Tap **Account**: do you see your name, your email, "Signed in with Google." and a **Gmail** box? If the Gmail box says "Connected as …", tap **Disconnect** first. Then tap **Connect Gmail**: Google should open in the same tab with your account already chosen. Allow it to send email for you. Are you back on **Account** with "Gmail connected" and "Connected as" your address?

Record yes/no for each and the phone and browser. If Google showed "Google hasn't verified this app", record that it did (In production, unverified) and that the owner went on with **Advanced** → **Go to …**. If Google showed "Access blocked", the account is not a test user (Testing): record it; the owner adds it under **Test users** (or switches to In production, owner question 5) and connects again.

- [ ] **Step 8 (OWNER, then agent): Phone, step 2: disconnect and reconnect (A)**

> On **Account**, tap **Disconnect**: does the box go back to "Connect Gmail" with no message popping up? Tap **Connect Gmail** again and allow it: are you back with "Connected as" your address?

- [ ] **Step 9 (OWNER, then agent): Phone, step 3: email the bulletin to yourself (B; item 11)**

> Open **Builder**, go to **Review & send** for any service with a date (it does not need to be saved). At the bottom, does the **Email the bulletin** box say "Sends from" your address? Tap **Email bulletin…**. Is the subject "Worship service for" the date, without a zero before a one-digit day? Tick **Printed bulletin (PDF)** so both boxes are ticked. Leave every contact unticked, type only your own email address under **Other addresses**, and tap **Send to 1 person**. Does it say "Email sent to 1 person."? In your inbox, does the email show you in To, the message, and two attachments, and do both open on your phone?

- [ ] **Step 10 (OWNER, then agent): Phone, step 4: two of your own addresses (B; item 11, the Bcc check)**

> Only if you have a second email address of your own (not anyone else's): send again with both of your addresses under **Other addresses**, separated by a comma. When it arrives at each address, does it show only your Gmail address in To and no other address? In Gmail's **Sent** folder, does the copy show both addresses as Bcc? If you have only one address, tell me "skip".

- [ ] **Step 11 (OWNER, then agent): Phone, step 5: the dialog on the phone and the Review card's connect (B; items 12-13)**

> Tap **Email bulletin…** again: is **Printed bulletin (PDF)** still ticked? Tap in **Message** so the keyboard opens: can you still see and tap the Send button, and is the message box visible above the keyboard? Tap **Cancel**. Now go to **Settings** → **Account** → **Disconnect**, then back to **Review & send**: does the box say "Connect your Gmail to email the bulletin from your own account."? Tap its **Connect Gmail**, allow it at Google: are you back on **Review & send** with the email box open by itself? Tap **Cancel** (nothing is sent).

- [ ] **Step 12 (agent): The agent's own checks (items 9-10 and 14-16)**

On the production URL, in a test church the agent may change (one of the two slice 1 test churches the owner kept, never the owner's own church), signed in as its owner if the session has a test account, else skipped and recorded as "not run": item 9 (cancel at Google), item 10 (reload `/gmail/callback`), item 14 (double tap: one email, to the test account's own address), item 15 (a flagged contact cannot be ticked), item 16 (church switch with the dialog open). Without a test account, all are "not run" and the follow-up says so.

- [ ] **Step 13 (agent): Write the record**

Write each step's result, with the date, into `<scratch>/5b2-t19-results.md`; a problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now. Then (not replayed):

```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it, `### Slice 5b-1 record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Slice 5b-2 record

Slice 5b-2 (each member connects their own Gmail in Settings → Account
through `/gmail/callback`; Review's Email the bulletin card sends the
bulletin copy and/or the printed PDF, built from the posted service, from
that Gmail: one recipient in To, several in Bcc with the sender in To, at
most 50; a retry never sends twice) merged as <PR #<N> / PRs #<A> (5b-2a,
the connection) and #<B> (5b-2b, emailing)>, the second of slice 5b's two
parts (owner's 5b planning answers of 2026-10-06). No database change and
no new package; production stays at `0007_bulletin_images`. Railway reads
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` (Streamlit's client, "Liturgy")
and `GOOGLE_OAUTH_REDIRECT_URI` since this merge. The owner's check was on
a phone, covering the "(owner, …)" items 7-13 of
`docs/manual-verification.md` → "Slice 5b"; every test email went to the
owner's own addresses. No address, name, token, code or church id is
recorded here.

| Step | Result | Date |
|---|---|---|
| Google and Railway setup | <Redirect URIs `…/gmail/callback` (production and localhost) added to the client "Liturgy"; consent screen <Testing / In production>; `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` <already Streamlit's / set to Streamlit's>; `GOOGLE_OAUTH_REDIRECT_URI` set; log `Gmail: configured`, no `Gmail:` warning> | <date> |
| Merge and deploy | <PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success> <one row per PR when there were two> | <date> |
| 1. Account and connecting (phone: <phone and browser>) | <Four sections, no sideways scroll; Account showed name, email, "Signed in with Google."; Connect Gmail opened Google in the same tab with the account chosen; back with "Gmail connected" and "Connected as". / …> | <date> |
| 2. Disconnect and reconnect | <Disconnect showed Connect Gmail with no message; reconnect worked. / …> | <date> |
| 3. Email to the owner's address | <"Email sent to 1 person."; the subject without a leading zero; owner in To; both attachments opened on the phone. / …> | <date> |
| 4. Two of the owner's addresses | <Each copy showed only the sender in To; Sent showed both in Bcc. / Skipped: one address.> | <date> |
| 5. The dialog on the phone, connect from Review | <PDF still ticked; Send reachable and the box visible with the keyboard open; Connect Gmail from Review came back with the dialog open. / …> | <date> |
| Agent checks | <Items 9, 10, 14, 15, 16 in a test church: <results>. / Not run: <why>.> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: 6a-2 and 6a-3, in the order the owner picks | <date> |
```

In the same commit, in the Railway table, replace the `GOOGLE_*` row's middle cell "carried over for a later slice (secrets)" with "Streamlit's OAuth client "Liturgy" (id and secret, secrets) and `https://worship-service-builder.vercel.app/gmail/callback`. Read by `api/settings.py` since slice 5b-2: without all three, Gmail is off (`Gmail: not configured` or a `Gmail:` warning in the startup log)." and its last cell with "slice 0; read since slice 5b-2"; and at the end of the "Google OAuth client "Liturgy"" paragraph add: "Since slice 5b-2 (<date>) it also lists `https://worship-service-builder.vercel.app/gmail/callback` and `http://localhost:3000/gmail/callback`, the new app's Gmail return page." Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye. Then (not replayed):

```bash
sed -n '/^### Slice 5b-2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 5b-2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-|apps\.googleusercontent|GOCSPX'
git diff -U0 docs/ops-runbook.md | grep '^+' | grep -c '—'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 5b-2 record (merged; Google setup; owner's phone check)" -m "Records slice 5b-2: the Google and Railway setup, the merge and CI on
main, and the owner's phone check (Settings → Account and connecting,
disconnect and reconnect, emailing the bulletin to the owner's own
address with both files, the Bcc check, the dialog on the phone). The
Railway GOOGLE_* row and the Google client paragraph now say what reads
them. No address, name, token, code or church id is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0` (the client id's `apps.googleusercontent` and a secret's `GOCSPX` prefix never appear); `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 14 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 5b-2 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 5b-2 record" \
  --body "Records slice 5b-2 in docs/ops-runbook.md → Slice 5b-2 record: the Google and Railway setup, the merge and the owner's phone check; the Railway GOOGLE_* row and the Google client paragraph brought up to date. No address, name, token, code or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Slice 5b-2 is live and recorded; <n> follow-ups. Next: 6a-2 and 6a-3, in the order you pick." (Two PRs: after the 5b-2a merge, Steps 7-8 and the agent's items 9-10 run, their results wait in the results file, and the work goes on with T11; the record is written after the 5b-2b merge, Steps 9-12.)

- [ ] **Step R (only if the release must come out): Revert**

Code only (no schema to undo). On the owner's yes for each outward command: a branch `claude/revert-5b2` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert slice 5b-2 (PR #<N>)" with the trailer, both suites (`1669 passed, 26 skipped`; `780 passed` in 94, or 5b-2a's counts when reverting 5b-2b only), a PR, CI, and the merge on the owner's yes; record it in the record. Connections made through the new page stay in `gmail_tokens` and keep working for the frozen app (same client); the Railway variables can stay (nothing reads them after the revert).

Expected counts after this task: backend 1825 passed, 27 skipped on `main`; frontend 835 passed in 100 files. The records PR adds no test.

---


## Build notes

**How this plan was written (2026-10-06).** Each task's code was built and run in a throwaway worktree of `4d4527f` (the branch head `eb5b2da` plus the plan's skeleton commit; the repo's `.venv`; a hard-linked copy of `frontend/node_modules`, since Turbopack refuses a `node_modules` symlink that points outside the project), one commit per task; the directives were then generated from those commits (a new file as **Create**, T2's rewrite as **Replace the whole of**, a removed file as **Delete**, an addition at the end of a file as **Append**, every other change as **In … replace** with just enough context to occur once in the file as it stands at that point). No package, variable name or migration was added. While building:
- **What the spec assumed and what exists.** B was written before 5a, 6a-1, the printed bulletin and 5b-1. Already there: the Settings shell, the header's Settings link, the `email` bucket, every Gmail error code (backend and frontend), `keys.gmailConnection`, `normalize_address`, the contacts API with `email_valid`, the key tracker. Missing although B assumed them: `run_idempotent`'s `store_error`, `integrations/http.post`, `email-slot.tsx` (5a never built a placeholder), `service_output`'s email additions. B's Streamlit coexistence work is dropped (answer 4).
- **Who imports `google_oauth`.** Only the frozen `app.py` (no test imports it; `streamlit_tests` reach `streamlit_views`, not `app.py`) and the three old test files; `test_no_streamlit_in_core.py` and `test_route_guards.py` constrain the new modules and routes, not the old ones. So the Streamlit functions could go (clarification 2).
- **The OpenAPI snapshot** refused FastAPI's `HTTPValidationError`: a Gmail route without 422 in its `responses` (every route has header parameters) failed `test_openapi_contract.py`'s second test until 422 was listed (clarification 7).
- **`describeError` turns every 5xx into "Something went wrong."**, which would have hidden B's Google and Gmail sentences on the callback page and in toasts; `gmailErrorMessage` keeps them for `gmail_send_failed`, `gmail_not_configured`, `upstream_error` and `upstream_timeout`.
- **The card's reopen decision** first lived in an effect that set state, which the React lint (`react-hooks/set-state-in-effect`) refuses; it is now read once in a `useState` initializer and decided during render, and only the removal of the session key is an effect.
- **Opening the dialog in tests** must wait for "Sends from …": while the status loads, the card shows a disabled **Email bulletin…**, and a click on it does nothing.
- **Three existing test files render Review** (`review-send-step`, `builder-shell`'s step routes, `liturgy-step`'s walk to Review) and needed the `GET /gmail-connection` route once the card existed; the first build forgot two of them and the full suite caught it (4 failures).
- **The Contacts caption** first changed in T9 (Account); it moved to T16, so that with two PRs it never says emailing is on Review before it is.
- **Mutation checks** (each change made by hand in the build worktree, the named tests run, the change undone): a send `ReadTimeout` counted as "not sent" → `3 failed, 110 passed` (`test_google_oauth.py`, `test_usecase_email.py`, `test_api_bulletin_emails.py`); the route without `store_error` → `2 failed, 17 passed`; `delete_connection` ignoring `only_if_token` → `2 failed, 92 passed`; `charge()` before the recipients → `22 failed, 42 passed`; a database session held during the refresh → `1 failed, 44 passed` (the pool test); the scope check skipped → `3 failed, 102 passed`; the state not compared with the caller → `2 failed, 54 passed`; the sender left in Bcc → `1 failed, 56 passed`; `connectGmailOnce` not remembering a state → `1 failed, 10 passed` (the StrictMode test); **Send again anyway** without `rotate()` → `1 failed, 15 passed`; `detectSessionInUrl` left out → `1 failed`; the reopen request taken for any church → `2 failed, 21 passed`; a flagged contact tickable → `1 failed, 15 passed`; the recipient count without de-duplication → `2 failed, 21 passed`.
- **The plan review fixes** (see "Plan review fixes") were built the same way: each change made as a fixup of its task's commit in a build worktree of the first replay's commits, the commits re-stacked, and the directives of T3, T6, T7, T9, T13, T15 and T16 generated again from them (those of the other tasks came out identical, a check on the generator). Mutation checks for them: `ACCOUNT_REFUSED` not classified → `3 failed, 125 passed` (`test_google_oauth.py`, `test_usecase_email.py`, `test_api_bulletin_emails.py`, `test_api_gmail.py`); no size guard → `1 failed, 127 passed`; no `gmail_connect` limit → `1 failed, 127 passed`; the flow B reopen not waiting for the carry → `1 failed, 17 passed` (`email-card.test.tsx`); the dialog's fields scrolling by themselves on a phone (the old full-screen layout's classes) → `1 failed, 17 passed`; plain Send left on after an uncertain send → `2 failed, 16 passed`.
- **The production build** compiled with `○ /gmail/callback`, `○ /settings`, `○ /settings/account`, `○ /settings/church` and `○ /settings/contacts`.

**Replay of the finished plan (2026-10-06; run again after the plan review fixes).** The directives of T1-T17 were applied in order (by a replay script that parses each step's **Create**, **Replace the whole of**, **Delete**, **Append** and **In … replace** blocks and runs every command on its "Run:" lines, three times where it says so, then the task's commit block) onto a fresh detached worktree of the branch at `56971b9` and, after the plan review fixes, again onto one at `79c6f69` (the branch with the fixes' plan commits; each outside the repo directory, removed afterwards), with the repo's `.venv` (a symlink) and a hard-linked copy of `frontend/node_modules`:
- All directives applied, every Replace anchor exactly once (in the second replay: T1 1 + 2, T2 5 + 1, T3 4 + 4, T4 3 + 12, T5 2 + 1, T6 4 + 7, T7 4 + 9, T8 1 + 2, T9 6 + 4, T10 1, T11 5 + 3, T12 3 + 5, T13 2 + 3, T14 1 + 3, T15 3 + 8, T16 10 + 9, T17 1).
- Baselines before T1: backend `1669 passed, 26 skipped`; frontend `780 passed` in 94 files.
- Every "see it fail" output is quoted from this replay (times as `<t>`). Every count matched the table; T8's and T16's three runs passed each time, no flaky run; typecheck 0 and lint 0 after T6, T7, T8, T9, T14, T15 and T16; T10 and T17 `89 passed`, `4`, `0`. After T17: T18 Step 3's gates (`imports grep exit 1`, `raw html grep exit 1`, `0` em dashes, the 73 paths quoted, `0` untouched-area paths, `trailer check done`) and the production build as above.
- Not run while planning: the pushes, the PRs and CI, the merges, Railway's and Vercel's deploys, Google Cloud Console, a real Gmail send and the owner's phone check (T19).

**5b-2a build review fixes (2026-10-07).** After T10, the code review of T1-T10 found one Important and four Minor issues. Each was fixed test first (the test seen to fail, then to pass) in its own commit, `Fix: <what> (5b-2a build review <id>)`, pushed after each:
- **I1** (`google_oauth.consume_state`): it read the state, then deleted it through the ORM, so two consumes racing for one state both returned the user (the second delete matched no row, only a warning). It is now one `DELETE ... RETURNING user_id, expires_at`, and only what the delete returned counts (an expired state is still refused, still used up). `test_google_oauth.py` +1 (a second consume slipped into the first's transaction) and a new Postgres test, `test_gmail_state_postgres.py` (the first consume held after its delete while the second runs on its own connection; with the old code `assert 2 == 1`).
- **M1** (`usecases.email.finish_gmail_connect`): with no refresh token, an existing row was kept whatever its address. It is kept only when its address matches the grant's, ignoring case; otherwise the no-refresh-token message (`gmail_connect_failed`) and the row is left as it was. `test_usecase_email.py` +1.
- **M2** (`google_oauth.exchange_code`): on `SCOPE_MISSING` or `EMAIL_MISMATCH` the token Google had just issued is revoked first, best effort (the refresh token when there is one, else the access token; `revoke_token` never raises and logs nothing). `test_google_oauth.py` +7 (4 + 3 parametrized cases).
- **M3** (`lib/api/timeouts.ts`): `POST /gmail-connection` waits 75 s, not 40 s (Google's timeouts are per phase, so the exchange and the lookup can together take longer than 40 s); the "Still working" line still shows after 8 s. Clarifications 5 and 8, the file table, T15's directive and the 5b spec say 75 s. `client.test.ts` +1.
- **M4** (`google_oauth._failure`): a token endpoint 400 or 401 other than `invalid_grant` and the client errors (`invalid_request`, `invalid_scope`, or no readable error) is `INCOMPLETE_RESPONSE` ("Google returned an incomplete response. Try connecting again."), not `UPSTREAM` ("Couldn't reach Google"); the connect's log line carries Google's error code (`google_error=invalid_request`), never its text. `test_google_oauth.py` +2 cases (one more in the refresh test's loop), `test_usecase_email.py` +2.
- Counts after the fixes: backend `1752 passed, 27 skipped` (+13, and the Postgres test skipped without `TEST_DATABASE_URL`); `-m postgres` on a local Postgres 16: `27 passed`; frontend `801 passed` in 98 files; typecheck 0, lint 0; the regenerated API files unchanged; the production build compiled with the same five routes. The expected counts of T11-T18 above are moved by the same deltas (backend +13 and one more skipped, frontend +1; `test_usecase_email.py` is 20 before T13, so T13's and T14's focused runs are `53` and `80`), and T18's path list has the three new paths (76 in all).

**5b-2b build review fixes (2026-10-07).** After T17, the code review of T11-T17 found two Important and seven Minor issues. Each was fixed test first (the test seen to fail, then to pass; the reload-style I1 test already passed and guards the behaviour) in its own commit, `Fix: <what> (5b-2b build review <id>)`, pushed after each:
- **I1** (`email-dialog.tsx`, `email-card.tsx`): the possibly-sent mark was written only in `send.mutate`'s per-call `onError`, which React Query v5 skips after an unmount and a reload kills, and the card's key tracker went with the card, so Back or a reload during "Still working…" allowed a plain Send of a second copy. The card's new `onMaybeSent` writes the mark (the connection-lost message) to sessionStorage before the request leaves, without setting the shown state (no flash); it is cleared only on a definite answer (success, or a 4xx other than 429 that is not `send_uncertain`, excluding 401 and a lost church; an aborted request is status 0 and keeps it). After **Send again anyway** with an answer that is not definite, the warning is hidden (a plain retry replays that key) but the mark stays. This also covers **M1**: leaving Review mid-send and coming back shows the warning with plain Send off. `email-card.test.tsx` +3 (unmount mid-send then back, a reload with the mark, a definite refusal forgets it and a 500 keeps it).
- **I2** (`email-dialog.tsx`): a problem at the top was off-screen after Send on the 375 px bottom sheet. The alert has a ref and `tabIndex={-1}` and is focused after the next frame (`requestAnimationFrame`); a To problem focuses the first enabled contact (a disabled one cannot take focus, and during the send every checkbox was disabled when focus moved, so attachments too are focused after the frame). `email-card.test.tsx` +1 (`document.activeElement`); the 422 focus test now waits for the frame.
- **M2** (`usecases/email.py`, `api/ratelimit.py`): the PDF and its readings were built before the email limit was checked. `ratelimit.check` (a peek: raises as `consume` would, charges nothing) is passed as `check_charge` and called before the files; the charge stays right before Google. `test_ratelimit.py` +1, `test_usecase_email.py` +1, `test_api_bulletin_emails.py` +1 (at the limit no PDF is built and the `scripture` bucket is still full).
- **M3** (`usecases/email.py`, `bulletin_email.py`): the stored `google_email` went into From and To as stored. It now goes through `normalize_address` (a stored address the rule refuses is `gmail_not_connected`, "Connect your Gmail first, then try again."), and the Bcc self-exclusion compares trimmed lower-case addresses. `test_usecase_email.py` +2.
- **M4** (`usecases/email.py` `_refused_grant`): when Google refused the grant and the row was already gone (a Disconnect meanwhile), the send said "connection changed" (no Reconnect). A row that is gone is now the expired-or-removed failure with `disconnected: true`; a replaced row is still "changed". `test_usecase_email.py` +2 (refresh `invalid_grant` and send `insufficientPermissions`).
- **M5** (`email-dialog.tsx`): the `aria-live` wrapper around the `role="alert"` child is gone (it could announce twice). An assertion in the Reconnect test.
- **M6** (`lib/email.ts`): the mark is `{version: 2, message, date_iso}`, and `readUncertainSend(userId, churchId, dateIso)` ignores one for another service date (a version-1 mark is ignored). `email.test.ts` (the existing test extended), `email-card.test.tsx` +1.
- **M7** (`lib/email.ts` `parseAddressList`): a comma or semicolon inside a quoted name split the address; separators inside double quotes no longer split (an unclosed quote falls back to splitting on all of them). `email.test.ts` +1.
- Counts after the fixes: backend `1825 passed, 27 skipped` (+7); frontend `835 passed` in 100 files (+6), three runs in a row; typecheck 0, lint 0; the regenerated API files unchanged (no route schema changed); the production build compiled with the same five routes; no em dash in an added line. T18's counts and PR texts above are moved to these; its 5b-2b path list also has `backend/api/ratelimit.py` and `backend/tests/test_ratelimit.py` (as `M`).

## Spec coverage

| Owner answer or spec item | Task(s) and tests |
|---|---|
| Answer 1: two attachment boxes, at least one, built server-side from the posted draft and the church's settings, remembered per user and church | T13 `test_a_member_emails_the_bulletin_with_both_files_in_bcc`, the `no-attachment` case, `test_a_real_bulletin_copy_is_the_same_document_as_the_download`; T14 `test_the_body_and_its_attachments`; T15 "remembers the last send's contacts and the attachments per user and church"; T16 "shows the contacts, the subject, the attachments …" and "sends the service as it is now …" |
| Answer 2: 5b-2 is the Gmail connection and emailing (two PRs possible) | T1-T17; "One PR or two"; clarification 1 |
| Answer 3: Streamlit's Google client reused; the owner adds the redirect URI and checks the publishing status | T4 (the variables and startup lines); T19 Steps 1-5 |
| Answer 4: Streamlit unused (no legacy module, smoke test, banner, parity gate, legacy note; the hint; revoke on disconnect) | T2 `test_the_streamlit_functions_are_gone`; T13 `test_a_saved_contact_the_rule_refuses_is_named_with_the_hint`; T5 `test_disconnect_deletes_then_revokes_and_a_failed_revoke_still_disconnects` |
| Answer 5: "Worship service for October 4, 2026", no em dashes; BCC with the sender in To; the editable prefilled message; at most 50; last send's contacts preselected; any member sends | T11 (shared fixture, addressing); T13 the `51-after-dedupe` case; T14 `test_a_member_emails_the_bulletin`; T16 the dialog tests; T10 and T17 Step 2 and T18 Step 3 grep the added lines for em dashes |
| B `google_oauth` refactor (signatures, scope check, classification, timeouts, no logging, no `os.getenv`/`requests`) | T2, T3 `test_google_oauth.py` (B Testing's list, ported and new) |
| B `POST /gmail-connection` errors table, state CSRF first, nothing stored on failure, mismatch names the address | T5 `test_each_connect_failure_has_its_message_and_stores_nothing`, `test_a_state_that_is_another_users_used_expired_or_unknown_stores_nothing`, `test_the_state_is_used_up_even_when_the_exchange_fails`; T6 `test_connect_errors_never_show_googles_text`, `test_a_mismatched_account_is_named` (B AC 3, 4) |
| B API: the four Gmail routes user-scoped, `USER_SCOPED` | T6 `test_connect_status_and_disconnect` (`X-Church-Id` ignored), `test_every_gmail_route_needs_a_signed_in_user`; `test_route_guards.py` (B AC 1, 2) |
| B configuration and startup checks | T4 `test_gmail_configuration_problems`, `test_startup_logs_the_gmail_configuration` |
| B `/gmail/callback`: once under StrictMode, never "didn't finish" during a connect, URL cleaned, `access_denied`, other errors not echoed, status seeded, return path | T8 `gmail-callback.test.tsx` (B AC 10) |
| B: `detectSessionInUrl: false`; `/gmail/callback` an allowed post-login path; Google URL check; return path validated | T7 `client.test.ts`, `urls.test.ts`, `gmail.test.ts` (B AC 10) |
| B `/settings/account`: identity, Log out, the Gmail card's five states | T9 `account-settings-page.test.tsx` (B AC 12, with `/settings` opening Church: S) |
| B §Errors `POST /bulletin-emails`: the order, recipients, de-dupe, cap, contacts 404 and 422 with the hint, not configured, not connected, 5a's errors, rate limit, refresh and send failures, conditional delete | T13 (each row), T14 `test_the_checks_run_in_the_specs_order`, `test_gmail_errors_never_carry_googles_text` (B AC 6, 7) |
| B: uncertain sends stored and replayed; Send again anyway | T12 `store_error` tests; T14 `test_an_uncertain_send_is_replayed_never_sent_again`, `test_a_send_that_never_left_or_a_slow_refresh_runs_again_with_the_same_key`; T16 "after an uncertain send …" (B AC 6, 11) |
| B: the key required, replay, mismatch, concurrent one send | T14 `test_the_key_is_required_and_must_be_a_uuid`, `test_a_retry_with_the_same_key_replays_and_sends_once`, `test_two_requests_with_one_key_at_once_send_once` (B AC 6) |
| B: rate limit only for requests that reach Gmail | T14 `test_only_requests_that_reach_gmail_use_the_hourly_limit`; T13 `test_the_rate_limit_is_charged_once_after_the_files_and_before_google` (B AC 6) |
| B: the message (To/Bcc, subject, attachment bytes and types, word/document.xml identity, no hymn usage) | T11; T13 `test_a_member_emails_the_bulletin_with_both_files_in_bcc`, `test_a_real_bulletin_copy_is_the_same_document_as_the_download` (B AC 5, 9) |
| B: no pooled connection during Google calls; logs without addresses or tokens | T13 `test_no_pooled_connection_is_held_while_google_is_called`, `test_the_logs_carry_no_address_subject_message_or_token`; T5's log test (B AC 8) |
| B: `normalize_address` the only validator; the shared fixture through `POST /bulletin-emails` | T14 `test_the_shared_address_cases` (B AC 14a) |
| B: church isolation | T13 `test_another_churchs_contact_is_not_found`; T14 `test_the_route_is_church_scoped`, `test_another_churchs_contact_is_not_found_and_nothing_is_sent`, `test_a_hymn_the_church_no_longer_has_is_not_found` (B AC 2) |
| B: subject and default message identical in Python and TypeScript | T11 and T15 on `bulletin_email.json` (B AC 13) |
| B "Send outcomes": field errors where they belong, contact 404 refetches, hymn 404 "Go to Hymns", 409 Connect, 502 Reconnect, network error keeps the key | T16 dialog tests (B AC 11) |
| B flow B: reopen after connect only when connected, for the active church; cleared otherwise | T16 "back from Google" tests (B AC 10) |
| B: `dedupe_addresses`; `get_contacts_by_ids` | T11, T12 |
| 5b-1 follow-ups: the caption; `email_valid` in the dialog; "Manage contacts" for admins | T16 (caption, flagged contact, empty state) |
| The owner's setup before merge; a guided phone check; the record | T19 |

Spec items **not** in 5b-2: the parity gate, the Streamlit smoke test and switchover banner, `LegacySettingsNote`, `google_oauth_legacy.py`, `scripts/check_contact_addresses.py` (answer 4; 5b-1 clarification 13); `NEXT_PUBLIC_LEGACY_APP_URL`; B's Streamlit coexistence checks (manual checks 3, 13, 16); token encryption and the client secret's rotation (slice 7).

## Follow-ups (not in 5b-2)

- Slice 7: delete `app.py`'s Gmail code with the rest of the Streamlit app; encrypt `gmail_tokens.refresh_token` (only `google_oauth.get_connection`, `save_user_token` and `delete_connection` touch it); rotate the Google client secret after the Streamlit app is deleted (it lives in Streamlit Cloud and Railway), then update Railway's `GOOGLE_CLIENT_SECRET`; remove the Streamlit redirect URIs from the client.
- If the consent screen stays in Testing: every sender listed as a test user and the weekly reconnect (owner question 5). If Google ever requires verification for the `gmail.send` scope at our size, or the 100-new-user cap of an unverified app is reached, that is its own project.
- Gmail's media upload endpoint (`uploadType=media`, `message/rfc822`) if a bulletin ever needs more than the 3.5 MB the JSON endpoint is given here (clarification 5).
- The idempotency store is in memory (F §1.6): a Railway restart between an uncertain send and its retry forgets the stored answer. Move it to Postgres if `--workers` ever exceeds 1.
- The email dialog has no "send a test to myself" shortcut; the owner can type their own address. A later wish, not in B.

## Owner questions

Your 5b planning answers of 2026-10-06 (all as recommended) are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **One pull request or two?** (clarification 1, "One PR or two"). The work is about twice the size of the Contacts page. Recommended: **two**. The first (5b-2a) adds Settings → Account, where each person connects their own Gmail; nothing is emailed yet. The second (5b-2b) adds the **Email the bulletin** card and its dialog on Review. Why two: the Google setup (a new return address in Google Cloud Console, three settings in Railway) is the riskiest part, because Google may ask to verify the site's address; with two, you do that setup and check that connecting works before the emailing code is merged, and each review is half as long. (The other choice: one PR with everything, one setup and one phone check.)
2. **The email's words** (clarifications 11 and 21). Subject "Worship service for October 4, 2026"; the message box starts with "Hi! Here's the worship bulletin for this Sunday." (for a service on another day: "Hi! Here's the worship bulletin for Wednesday, February 10."), and you can change it each time; a message left empty is sent as that sentence. The apostrophe is the plain one the app uses everywhere. Recommended: accept.
3. **When the Email button is available** (clarification 18). It needs a service date and readings without an error on step 1, the same as the download buttons (a reading the app cannot read would also break the printed PDF). Nothing else blocks it: an unfinished or unsaved service can be emailed, and the dialog says so ("Not finished yet: 2 items under Still to do." and "Not saved to the archive yet. The attachments use the service as it is on screen now."). Recommended: accept.
4. **Remembering the attachment boxes** (clarification 12). Your choice of **Bulletin copy (Word)** and **Printed bulletin (PDF)** is remembered on that phone or computer as soon as you tick or untick a box, for you in that church; the people you chose are remembered after a successful send, so they are ticked next time. Recommended: accept.
5. **Google's consent screen: "Testing" or "In production"** (Risks; T19 Step 2). Sending email for someone is a permission Google calls "sensitive" (https://developers.google.com/workspace/gmail/api/auth/scopes). What each status means for your church:
   - **Testing** (https://support.google.com/cloud/answer/15549945): only the Google accounts you list as test users in Google Cloud Console (at most 100) can connect; anyone else sees "Access blocked". Google also ends every connection 7 days after it was made, so each person taps **Reconnect Gmail** about once a week (the email dialog keeps what they typed). Staying in Testing means adding every person who will send as a test user.
   - **In production, without Google's review** (https://support.google.com/cloud/answer/7454865): anyone can connect, but Google shows a "Google hasn't verified this app" warning and they tap **Advanced**, then **Go to …**. Google allows an unreviewed app 100 new users in total, ever (plenty for the people who send bulletins).
   - **Not certain:** we expect the warning on each connect and each reconnect, not just the first time; we do not know whether connections made while in Testing stop expiring after the switch, so plan for each person to reconnect once after switching; Google's policy expects an app to be verified before it is launched to users, so Google could ask for a review later; and if someone connects a church Google Workspace account (not an @gmail.com one), that organization's admin may block unverified apps.

   Recommended: if it says Testing, switch it to In production at T19 Step 2 and have each person reconnect once. (The other choice: stay in Testing, add everyone who will send as a test user, and reconnect weekly.)
6. **A contact whose address the app cannot use** (clarification 14). In the email dialog it is listed but its box cannot be ticked, with "This address doesn't look valid. An admin can fix it in Settings → Contacts." under it, so a send never fails on it. Recommended: accept.
7. **Settings → Account** (clarification 10). The new section goes after Contacts; it shows your name, email, "Signed in with Google.", a **Log out** button (the same as the one in the account menu) and the Gmail box; **Disconnect** asks nothing first (connecting again is one tap). Recommended: accept.
8. **The new wording** (clarifications 10, 20 and 21): the Gmail box, the callback page's messages, the card, the dialog and the server's messages, all without long dashes. The Account page's Gmail box says "Connect the Gmail account you sign in with. The app gets permission only to send email for you; it can't read your mail." in the first PR, before emailing exists, and "Connect your Gmail to email bulletins from your own account. The app can only send email for you; it can't read your mail." once emailing comes (the Contacts caption changes at the same time). Two server messages are new: "Gmail won't send from this Google account. Nothing was sent. Check that you can send email in Gmail with it, then try again." and "The attachments are too large to email. Try sending only the bulletin copy." Recommended: accept.
9. **When Gmail may already have sent the email** (clarification 18). If Gmail does not confirm a send, or the connection drops while sending, the dialog says to check your Gmail Sent folder, the **Send** button stays off, and the only way to send is **Send again anyway**. This holds even if you close the dialog, leave Review & send or reload the page in that tab, so a second copy is only ever sent on purpose. Recommended: accept.
10. **The printed PDF in the email** (clarification 18). When **Printed bulletin (PDF)** is ticked, the dialog shows the same "Not filled in: …" and "From last week, not checked yet: …" lines as the printed bulletin card. After connecting Gmail from Review, the dialog reopens only once last week's music and announcements have been brought in, so an emailed PDF has them. Recommended: accept.

Owner steps still to come: the plan's approval and the answers above; the draft PR on your yes and ready on your yes (T18); the Google Cloud Console and Railway steps, one at a time, before the (first) merge; the merge on your yes; the phone check one step at a time (T19); the records PR.

Owner's answer 2026-10-06: all recommended (binding): two PRs (5b-2a then 5b-2b); if the consent screen says Testing, switch to In production at T19 Step 2.

## Plan review fixes (2026-10-06)

The plan review's findings, each fixed in the plan; every task they touch was replayed again (see "Build notes"), and the counts above are the replay's.

- **I1** (Testing allows only listed test users, at most 100; others get "Access blocked"; https://support.google.com/cloud/answer/15549945): Risks, owner question 5 and T19 Step 2 (which now asks whether everyone who will send is listed under Test users) say so; staying in Testing means adding every sender. T19 Step 7 says what to do on "Access blocked".
- **I2** (owner question 5 overstated): reworded for a non-expert with the confirmed facts and their sources (`gmail.send` is Sensitive, https://developers.google.com/workspace/gmail/api/auth/scopes; Testing tokens expire 7 days after consent; In production unverified works with the warning and a 100-new-user lifetime cap, https://support.google.com/cloud/answer/7454865) and an explicit "Not certain" list: the warning probably shows on each connect and reconnect (not "one-time"), one reconnect after switching, Google's policy expecting verification before a user-facing launch, a Workspace admin blocking unverified apps. Risks and T19 Step 2 match.
- **I3** (the dialog's footer under the iPhone keyboard): T16's dialog is now 5b-1's approved bottom sheet below `md` (`max-md:bottom-0 … max-md:max-h-[85dvh] max-md:overflow-y-auto`; the footer scrolls with the content); from `md` the fields scroll above the footer as before. New DOM test "is a bottom sheet on a phone whose one scroll area holds Send, so the keyboard never hides it" (class-based: no element between **Send** and the sheet scrolls or clips by itself). Manual check 12 and T19 Step 11 stay. Clarification 18.
- **M1** (uncertain send): after `send_uncertain` or a lost connection, plain **Send** is off and **Send again anyway** (a new key) is the only way to send; the message is kept in sessionStorage per user and church (`wsb:emailUncertain:{userId}:{churchId}`, T15's `readUncertainSend`, `writeUncertainSend`, `clearUncertainSend`), so closing the dialog, leaving Review or reloading the tab keeps Send off; a definite answer to **Send again anyway** clears it. The pending key itself is not stored: while the state stands no request reuses it (plain Send is off, and **Send again anyway** rotates by design), so storing it would add nothing. Tests: T15 "remembers a send that may already have gone out, per user and church, in this tab"; T16's two uncertain tests rewritten (the first unmounts and renders Review again). Clarifications 17 and 18, owner question 9.
- **M2** (Gmail raw size): `send_bulletin_email` refuses a message over 3.5 MB (`MAX_RAW_BYTES`, about 4.7 MB once base64url-encoded, under the 5 MB Google's upload guide gives a simple request, https://developers.google.com/workspace/gmail/api/guides/uploads) with a 422 on `attachments`, "The attachments are too large to email. Try sending only the bulletin copy.", before the email limit is charged and before Google. The JSON endpoint is kept; the media upload endpoint is a follow-up. Test: T13 `test_a_message_too_large_for_gmail_is_refused_before_the_limit_and_google`. Clarifications 5, 15 and 21.
- **M3** (timeouts): the comments in `google_oauth.py` and `lib/api/timeouts.ts` and clarifications 5, 8 and 17 now say the httpx timeouts are per phase (5 s to connect, then 15, 30 or 5 s for each write, read or pool wait), not deadlines, and that the browser's 40 s and 90 s are the overall limits (a send still unanswered at 90 s is shown as possibly sent). No server deadline is added.
- **M4** (Gmail refusing the account): a new `GoogleErrorKind.ACCOUNT_REFUSED` for a send's 401 (not about the scope) or 400 `failedPrecondition`, answered "Gmail won't send from this Google account. Nothing was sent. Check that you can send email in Gmail with it, then try again." (the connection kept); the failure's log line names Google's reason (`google_error=failedPrecondition`; a reason is preferred over the status name). `fake_google.gmail_error` now gives each status its usual Gmail status name. Tests: T3's send failures (`authError` now `ACCOUNT_REFUSED`, a new `failedPrecondition` case, and the reason checked) and T13 `test_gmail_refusing_the_account_has_its_own_message_and_its_reason_is_logged`.
- **M5** (clarification 8's reason for `/gmail/callback` in `safeInternalPath`): the change is kept and its reason corrected in clarification 8 and in `urls.ts`'s comment: the proxy keeps only the path in `/login?next=`, so the landing after sign-in has no answer from Google and shows "Gmail connection didn't finish. Try connecting again." with **Try again**, rather than leaving the user on the Builder.
- **M6** (rate limit on `POST /gmail-connection/auth-url`): a new per-user bucket `gmail_connect`, 10 in 10 minutes (not the `email` bucket, so connecting never spends sends), in `api/ratelimit.py` and its pin in `test_ratelimit.py`; the route documents 429. Test: T6 `test_consent_urls_are_rate_limited_per_user` (the 11th is a 429 and stores no state). Clarification 7.
- **M7** (the PDF's notes and the carry): with **Printed bulletin (PDF)** ticked the dialog shows the printed card's "Not filled in: …" and "From last week, not checked yet: …" (`NotFilledInLines`, now exported from `printed-card.tsx`); back from Google (flow B) the card reopens the dialog only once `useBulletinCarry` has carried last week's bulletin in (the draft no longer `shouldCarry`) or the lookup failed, read from the shared query without fetching it again. Test: T16 "waits for last week's bulletin to be carried in, then shows the printed bulletin's notes with the PDF". Clarification 18, owner question 10.
- **M8** (the Account intro in 5b-2a): T9's sentence is "Connect the Gmail account you sign in with. The app gets permission only to send email for you; it can't read your mail.", true before emailing exists; T16 changes it to "Connect your Gmail to email bulletins from your own account. The app can only send email for you; it can't read your mail." with the Contacts caption. Both are pinned in `account-settings-page.test.tsx`. Clarifications 10, 20 and 21, owner question 8.
- **M9** (T2's commit message): it no longer says the secret is out of `repr` (T4 does that).

## Self-review

- **Coverage.** Every binding constraint has a home: the two attachments, at least one, remembered (clarification 12, T13-T16); Streamlit's client reused and the owner's setup before merge, one step at a time, never handling the secret (answer 3; T19 Steps 1-5; Global Constraints); Streamlit unused: the Streamlit-only functions deleted after checking who imports them (only the frozen `app.py`, never imported by a test, and three test files, ported), no legacy module, no smoke test, no banner, no parity gate, no legacy note, the hint's text (clarification 2, T2, T13); the subject without zero padding and no em dash in new copy (clarifications 11 and 21; T10, T17, T18 grep); BCC with the sender in To, the prefilled message, 50 at most, the last send's contacts preselected, any member sends (T11, T13, T14, T16); no migration (clarification 22; T18 Step 3 counts `backend/migrations` as 0); the frozen Streamlit files untouched (T18 Step 3); no network in tests (the fake Google behind conftest's guard; clarification 4) and no new dev dependency; the Account section after Contacts (clarification 10); the Contacts caption changed with emailing (clarification 20); the second-to-last task opens a draft PR only on the owner's yes, the last runs the setup, merges only on a yes, runs the phone check one step at a time (connect, a test email to the owner's own address, the Bcc check with two of the owner's addresses when there are two, both attachments, disconnect and reconnect, the Review card) and inserts "### Slice 5b-2 record" before "## Backups", after "### Slice 5b-1 record".
- **Placeholders.** None in T1-T17's code, tests, commands or expected outputs; every expected output is quoted from the replay. The `<…>` left are T18 and T19's runtime values (`<N>`, `<scratch>`, times, the owner's answers), as in the 5b-1 plan.
- **Consistency.** Names agree across tasks: `post` (T1) is used by `google_oauth` (T3); `GoogleOAuthConfig`, `get_connection`, `delete_connection(only_if_token=…)` (T2) by T5 and T13; `GoogleErrorKind` (T3) by T5 and T13; `get_google_config` (T6) by T14; `dedupe_addresses`, `compose_bulletin_email`, `Attachment` (T11) and `get_contacts_by_ids`, `store_error` (T12) by T13 and T14; `GmailConnection` types, `startGmailRedirect`, `REOPEN_EMAIL_KEY`, `gmailErrorMessage` (T7) by T8, T9 and T16; `gmailConnection()` (T9) by T16; `bulletinEmailBody`, `parseReopen`, `readEmailPrefs`, `rotate` (T15) by T16. The counts in the table, each task's "Expected" and the PR lines agree.
- **Not verified while planning:** the pushes, the PRs and CI, the merges, Railway's and Vercel's deploys, Google's acceptance of the redirect URI (B's risk 3), a real Gmail send and Gmail's handling of Bcc, which reasons Gmail really sends for an account it will not send from (the fake answers `failedPrecondition` and `authError`), the JSON endpoint's real size limit (3.5 MB is kept under the upload guide's 5 MB), how often Google shows the unverified-app warning, the owner's phone check, and the pages at 375 px in a real browser (the classes give 44 px rows, `break-all` addresses and the bottom sheet; jsdom does not lay out).
- **Judgement calls to watch in review:** `bulletin_email.py` as its own module; the INFO startup line; the button's readings rule; the attachments remembered on change; the 90 s client timeout as the overall limit (no server deadline); `revoke_token` returning a bool; the module client swapped in tests instead of an `http` argument; the `gmail_connect` bucket (10 in 10 minutes) rather than the `email` bucket; `MAX_RAW_BYTES` at 3.5 MB; the uncertain send kept as a message in sessionStorage without its key; the flow B reopen waiting for the carry (not the plain **Email bulletin…** button, which like the downloads sends the draft as it is at the tap).
