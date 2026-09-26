# Slice 7 — Cutover: retire Streamlit — Design

**Date:** 2026-09-25
**Status:** Draft  **Depends on:** 6a and 6b merged and deployed; the parity gate (5b) passed and the tester's settings sign-off (F§6.3 phase D) recorded; the interfaces from ops, 1, 3, 5a, 5b and 6a listed under "Dependencies"  **Size:** M

**Inputs**
- Foundations: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` (cited "F§n").
- Inventory: `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md` (cited "inv §n"). It is the source of truth for current behavior. This slice covers inv §6 (the cutover checklist), §1 H (operations, scripts, legacy code), the §3 coupling rows assigned to 7, and the F§6.4 deferred list.
- Slice specs already written: ops, 1, 2, 3, 4, 5a, 5b, 6a (cited "ops spec", "slice 1 spec", …). Their hand-offs to 7 are listed in the coverage ledger.
- Owner decision 7: freeze Streamlit, move the tester after 2–5 reach parity, **retire Streamlit right after slice 6**. Decision 9 items touched here: hymnals and seeds; archived services keeping custom elements and hymnal (done in 5a; verified here by the quiet-period SQL check under Manual checks); hymn usage recorded on save (5a), which this slice extends to deletes of future-dated services once Streamlit can no longer write usage (7-G; open question 3).

---

## Goal

Retire the Streamlit app completely, without interrupting the tester and without losing data:

1. The old address shows a "moved" page, then the Streamlit Cloud app is deleted.
2. Nothing Streamlit remains in the repo or in any deployment: code, tests, dependencies, workflows, the Streamlit Cloud app, its Google redirect URIs, and the secrets it held, which are rotated.
3. The work that Streamlit's presence blocked gets done:
   - the contract-phase migrations (F§3.4, §3.5);
   - Gmail refresh-token encryption at rest (F§6.4);
   - finishing the Alembic adoption;
   - exporting `hymn_catalog` to a versioned seed file with a seed CLI;
   - cleaning up the `{A,"B"}` theme literals;
   - the last dead-code and configuration sweep (`requests`, `load_dotenv`, `os.getenv`, the engine default).
4. Every irreversible step comes after a **quiet period**. During that period Streamlit can be brought back by reverting one commit.

---

## Scope / Out of scope

### In scope

| # | Item | Source |
|---|---|---|
| C1 | Tombstone ("moved") page on `streamlit-frozen`; a quiet period with a tested revival path | owner decision 7; F§6.3 phase E |
| C2 | Delete the Streamlit code, its tests and its files | inv §6 "Code to delete"; F§5.1 |
| C3 | `pytest.ini`, the requirements files, CI, and workflows (delete `keep-awake.yml`) | inv §6 "Tests, CI, dependencies"; inv H6, H7 |
| C4 | Guards that keep the retirement true: a repo-wide Streamlit reference test, an environment-access test, `.env.example` parity (backend and frontend), and legacy-copy tests for the frontend and the backend (no "current app" wording, including 5b's `MALFORMED_CONTACT_HINT`) | F acceptance 20; F§2.3.5; slice 5b hand-off |
| C5 | Export `hymn_catalog` to a versioned seed file with a seed CLI; then delete the Notion and migration code (`migrate_to_db.py`, `notion_hymns.py`, `fill_from_hymnary.py`) and their dependencies | inv §6 "Data"; inv H1, H9, H10; F§6.4 |
| C6 | Normalize the `{A,"B"}` theme literals and the Notion-imported `hymn_usage.date_iso` shapes (Alembic `normalize_legacy_data`) | inv H1, §4 "Content hazards"; F§6.4; slice 3 hand-offs |
| C7 | Final configuration and dead-code sweep: engine default URL, `create_all` restricted to tests, CLIs refuse to run on an un-migrated database, the remaining `load_dotenv` and `os.getenv` calls, `requests`, dead functions | inv §3 rows for 7; inv §6; F§2.3.5–6 |
| C8 | Documentation: `README.md`, `docs/manual-verification.md` (rewritten), `frontend/README.md`, `backend/migrations/README.md`, `docs/ops-runbook.md`, and complete `.env.example` files | inv §6 "Config and docs"; F§5.5 |
| C9 | The point-of-no-return runbook: delete the Streamlit Cloud app, revoke its GitHub access, remove the Google redirect URIs, rotate secrets, tag and delete the frozen branch, remove the Vercel legacy variable, check the Supabase Auth URL settings, add an uptime monitor, clean up locally | inv §6 "External services"; F§6.3 phase E |
| C10 | Gmail refresh-token encryption at rest (two PRs plus Alembic `encrypt_gmail_tokens`) | F§6.4; slice 5b hand-off |
| C11 | Contract migration `contract_after_cutover`: drop `users.google_sub` and the undeclared production default `'GG2013'` on `hymnal`; turn on `compare_server_default` | F§3.4–3.5; inv H2; F§3.1 |
| C12 | Messages to the tester and the rollback plan | owner decision 7 |
| C13 | Decide on the hard purge of soft-deleted churches (a hand-off from slice 1) | slice 1 spec "Out of scope" |
| C14 | A rollback-safe pre-deploy migration step (`scripts/migrate.py`), so a Railway rollback onto an older release still deploys after a slice-7 migration | R2; slice 1 `railway.toml` |
| C15 | Rebuild hymn usage when a future-dated service is deleted or re-dated, once Streamlit cannot write usage (7-G) | 5a open question 1 hand-off; owner decisions 3 and 9 |

### Out of scope

| Item | Where it goes, or why |
|---|---|
| A staging environment to replace `liturgy-stg` (inv §6) | **Not planned** (F§6.4, F§7.3). Vercel previews stay build-only, because they would hit the production API and data. The README says so. Revisit when a second church onboards. |
| New endpoints or features | None. The API surface and the OpenAPI snapshot are unchanged. |
| Keying hymn usage by hymn id | A future schema change (slice 6a risk 2). |
| CSV upload of hymnals | Deferred (6a; inv §7 question 16). |
| Dropping `hymns.audio_url`, `hymn_catalog.audio_url` or `services.service_date_display`; making `services.custom_elements` NOT NULL | **Not needed** (F§3.5: "contract phase only if needed"). The audio columns hold data a later feature could use and cost nothing. The display date is still written by the API and read by the archive list. For `custom_elements`, NULL means "not recorded" on legacy rows, which 5a already reads as `[]`. |
| Changing the stored `services.hymns` shape (F§6.2) | It stays as it is. After the point of no return the §6.2 rules no longer bind, but there is no reason to change a working format. |
| Keeping backups longer, or off GitHub | Open question 2. |
| An automatic purge of soft-deleted churches | **Decided: none.** See C13 under Backend changes. |

### Coverage ledger (every inventory and hand-off item for slice 7)

Status legend:
- **Here (PR)**: done in this slice, in the named PR (see "Delivery plan").
- **Verify (slice)**: done by an earlier slice; this slice only checks it with a grep or a test.
- **No**: deliberately not done, with the reason.

| Source | Item | Status |
|---|---|---|
| inv §6 code | `app.py`, `streamlit_views/`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`, `streamlit_tests/` | Here (7-B), after the port ledger check |
| inv §6 code | `google_oauth.should_handle_gmail_callback` and its tests; the module and `build_auth_url` docstrings | Verify (5b deleted the function); Here (7-B) for the docstring's "until slice 7" wording |
| inv §6 code | `worship_service.py`: the Notion fallback, the `NotionHymnsDB` TYPE_CHECKING import, the audio resolver and its cache, the unused `build_docx` parameters, the "Settings → Secrets" messages, `load_dotenv()` at import | Verify (3, 4, 5a) with the grep in acceptance criterion 4 |
| inv §6 code | `migrate_to_db.py`, `notion_hymns.py`, `fill_from_hymnary.py`, `test_migrate_hymns.py`, `test_migrate_archive.py` | Here (7-D), after the catalog export |
| inv §6 code | `migrate_add_hymnal.py` | Verify (1) |
| inv §6 code (amendment 2026-09-26, PR #4) | `migrate_add_hymn_facts.py` and `tests/test_migrate_hymn_facts.py` | Verify (1 deleted them with the Alembic baseline) |
| Kept (amendment 2026-09-26, PR #4) | `backfill_hymn_facts.py` and `hymnary_facts.py` | Kept as an ops CLI after cutover; it no longer needs Streamlit. Document it in the post-cutover README's operations section. |
| inv §6 code | Remaining dead modules (H8, H10, H11) | Verify (ops deleted six); Here (7-D) for `fill_from_hymnary.py` |
| inv §6 code | `repos/users.upsert_user`; `streamlit_auth.current_user_id` | Verify (ops); Here (7-B), where it goes with its file. Also `auth.upsert_from_claims`, dead once Streamlit and `migrate_to_db` are gone: Here (7-B) |
| inv §6 tests | `pytest.ini` → `pythonpath = backend`, `testpaths = backend/tests` | Here (7-B) |
| inv §6 tests | `requirements-dev.txt` → `-r backend/requirements.txt`; delete the root `requirements.txt` | Here (7-B) |
| inv §6 tests | `backend/requirements.txt` without `playwright` and `notion-client`; `requests` replaced by httpx | Here (7-D: `playwright`, `notion-client`, `beautifulsoup4`; 7-E: `requests`) |
| inv §6 tests | Rewrite `test_foundation_setup.py:17-28` and `test_docs.py` | Here (7-B interim; 7-E final) |
| inv §6 tests | Extend `test_no_streamlit_in_core.py` | Replaced (7-B) by `test_no_streamlit_references.py` and `test_entry_points_import.py` |
| inv §6 tests | Delete `keep-awake.yml`; update `ci.yml`; `shadcn` to devDependencies | Here (7-B); Verify (ops) for `shadcn` |
| inv §6 config | Delete the root `.env.example`; complete `backend/.env.example` and `frontend/.env.example` | Here (7-B delete; 7-E parity tests) |
| inv §6 config | `db/engine.py` default URL (line 24) and comment (line 30) | Verify (ops fixed the comment); Here (7-E) for the default |
| inv §6 config | Rewrite `README.md`, `docs/manual-verification.md` and `frontend/README.md` | Here (7-E) |
| inv §6 config | The `streamlit` entry in the local `.claude/launch.json` (untracked); stale docstrings (`auth.py`, `tenancy.py:5`, `api/security.py:110-113`, `migrate_to_db.py:570`) | Here (P, local step; 7-B docstrings; `migrate_to_db.py` deleted in 7-D) |
| inv §6 external | Delete the Streamlit Cloud apps `liturgy` and `liturgy-stg` and their secrets | Here (P) for `liturgy`; Verify (ops deleted `liturgy-stg`) |
| inv §6 external | Rotate the database password and the OpenAI key | Here (P), plus the Google client secret, the ESV key if it was stored there, and revoking the Notion integration |
| inv §6 external | Google OAuth client: keep only the `/gmail/callback` URIs | Here (P). Supabase's own callback URI is **kept** if that client is shared. |
| inv §6 external | Supabase Auth redirect allow-list | Here (P, check) |
| inv §6 external | Staging to replace `liturgy-stg` | No (F§6.4) |
| inv §6 external | Keep-alive secret, or an off-GitHub pinger | Verify (ops: `keepalive.yml` needs no secret); Here (P): an external uptime monitor on `/health/ready` (ops risk 7) |
| inv §6 external | Encrypted or private backups | Verify (ops); Here (P): `BACKUP_DATABASE_URL` updated after the password rotation |
| inv §6 data | Export `hymn_catalog` plus a seed CLI | Here (7-C tool, 7-D file) |
| inv §6 data | Normalize `{A,"B"}` themes | Here (7-C, `normalize_legacy_data`) |
| inv §6 data | Purge stale `oauth_states`; decide on a hard purge of soft-deleted churches | Verify (5b purges expired states on each create) plus an optional runbook SQL; C13 decided (no automatic purge) |
| inv §6 data | Production schema equals the Alembic head, including `ix_hymns_church_hymnal` | Verify (1: `0002_reconcile`); Here (7-G): `alembic check` with `compare_server_default=True` |
| inv H1–H12 | Every row | H1, H9, H10: 7-D. H2: verify (1). H3: kept, `import_hymnal.py` refuses an un-migrated database (7-E). H4: verify (ops) plus the uptime monitor (P). H5: verify (ops) plus the secret update (P). H6: 7-B. H7: 7-B. H8, H11: verify (ops). H12: 7-B and 7-E. |
| inv §3 rows for 7 | `app.py:221-256` / `streamlit_tenancy.py`; `streamlit_auth.py`; `ui_helpers.py` rest | Here (7-B) |
| inv §3 rows for 7 | `google_oauth.py:190-201`; `worship_service.py:28, 612-683`; `worship_service.py:16, 23` and the other `load_dotenv` modules; `db/engine.py:24, 30`; `pytest.ini`, requirements, `test_foundation_setup.py`, `test_docs.py` | Verify (5b, 3), then Here (7-B, 7-E) |
| F§6.4 | Gmail token encryption; contract migrations; catalog export; theme normalization; remove `requests` and the remaining `load_dotenv`; the rest of inv §6; no staging | Here (7-C … 7-G); staging: No |
| F§7.3 | Vercel previews can't sign in | No (deliberate); documented in the README |
| ops spec | Delete `keep-awake.yml` and the `liturgy` app; README and manual-verification rewrites; delete the root `.env.example`; rotate secrets; off-GitHub pinger; the engine default URL; token encryption; `migrate_to_db.py`, `notion_hymns.py`, `fill_from_hymnary.py` and their requirements | Here (as above) |
| ops spec Q3 | Is 30 days of backup retention enough? | Open question 2 |
| slice 1 | Deleting the Streamlit onboarding code; the hard-purge decision | Here (7-B); C13 |
| slice 2 | Configuration deviation: `ESV_API_KEY` read by `scripture_fetcher._esv_key()` from the environment instead of `api/settings.py` | Verify (6a) if 6a took the move; otherwise Here (7-E, `api/settings.py` row). `test_env_access.py` enforces it either way. |
| slice 3 | `beautifulsoup4` stays until `fill_from_hymnary.py` goes; the theme data cleanup; the Streamlit-only helper tests | Here (7-D, 7-C, 7-B) |
| slice 3 | The `hymn_usage.date_iso` cleanup (Notion imports stored `""` or full datetimes; slice 3's read-only shape check counts them) | Here (7-C, `normalize_legacy_data` step 2): values whose first 10 characters parse become `YYYY-MM-DD`; the rest are left and counted. This also closes the gap where 5a's `rebuild_usage_for_date` (exact `date_iso` match) could not replace datetime-shaped rows. |
| slice 5a | `service_archive.list_saved_services` and `hymn_usage.record_usage` (kept only for frozen tests) | Here (7-B, dead-code sweep) |
| slice 5a | Open question 1: rebuild usage on delete or re-date once Streamlit no longer writes usage | Here (7-G), for **future-dated** services only; past dates keep their usage (Backend changes → Changed modules; open question 3) |
| slice 5a | `backend/tests/test_services_streamlit_compat.py` | Here (7-B): renamed `test_services_storage_shape.py`. It keeps the stored-shape assertion (exactly 3 entries in slot order, `title: ""` for an empty slot); the two "without the new keyword arguments" cases go, because their only callers were Streamlit's. |
| decision 9 (5a) | Archived services keep custom elements and the hymnal used | Verify (5a): the quiet-period SQL check under Manual checks |
| slice 5b | Token encryption through `google_oauth.get_connection`, `save_user_token` and `delete_connection` (including its `only_if_token` race check); remove the Streamlit redirect URI; `email_contacts.get_contacts_for_display`; `NEXT_PUBLIC_LEGACY_APP_URL` | Here (7-F, P, 7-B, P) |
| slice 5b; 6a | `usecases/email.py`'s `MALFORMED_CONTACT_HINT` must not send admins to the retired app: 6a swaps "An admin can remove it and add it again in the current app's Settings." for "An admin can fix it in Settings → Contacts." (with a test asserting the new text) | Verify (6a) in 7-B's copy sweep; Here (7-B): `backend/tests/test_no_legacy_copy.py` fails on "current app" in any backend string literal, so the hint cannot survive the retirement even if 6a's swap were missed (7-B then makes the swap) |
| slice 6b | Delete `LegacySettingsNote` (`legacy-settings-note.tsx` and its use in the settings layout) | Verify (6b-2; 6b acceptance 22) with the frontend guard test; 7-B deletes it only as a fallback if it somehow still exists |
| slice 5b; F§6.1 item 6 | If the freeze contingency applied (Streamlit deployed from `main`): delete `google_oauth_legacy.py` (5b), `build_docx_legacy` (5a), `generate_liturgy` (4), the `hymns_by_scripture`, `suggest_hymns_for_service` and `hymn_display_info` wrappers (3), `get_readings_for_date_string` and `test_legacy_lectionary_shim.py` (2), the `repos.invites.accept_invite` wrapper (1), and every `AppTest` smoke test (`streamlit_tests/test_app_gmail_smoke.py` and the others) | Here (7-B, which then merges only after P; see "If the F§6.1 contingency applied"). Verify (entry gate item 6) that none exists when the contingency did not apply. |
| slice 6a | `hymn_catalog` export; theme literals | Here (7-C, 7-D) |

### Dependencies (exact interfaces assumed)

| From | Interface this slice assumes | If it differs |
|---|---|---|
| ops | `streamlit-frozen` is protected (PR required, `backend` check, no force-push or delete). `docs/ops-runbook.md` has sections 1–7 (environments; lockdown; backups; keep-alive; Streamlit freeze; platform limits; incident response). `backup.yml` uses the secret `BACKUP_DATABASE_URL`. `keepalive.yml` curls `${vars.API_BASE_URL}/health/ready`. `backend/keepalive.py` is gone. `backend/tests/test_ops_workflows.py` asserts that `keep-awake.yml` pings only `https://liturgy.streamlit.app/`. `GET /health/ready` returns 200 `{"ok": true, "db": "ok"}`. The `APP_ENV` production guard exists. | Adapt the file names; the steps don't change. |
| 1 | `backend/migrations/` with `env.py` (`compare_server_default=False`, `include_object`, SQLite batch mode, Postgres lock and statement timeouts) and revisions `0001`–`0004`. `backend/db/schema_check.py` with `alembic_config()` (absolute path) and `revision_state(conn) -> RevisionState(current, head, state)`, where `state` is `current`, `behind` or `ahead` (current unknown to this release's scripts); the readiness gate returns 200 on `ahead`. `backend/railway.toml`: `preDeployCommand = ["alembic upgrade head"]`, `healthcheckPath = "/health/ready"` (F§3.3 as amended: Railway's deploy health check is `/health/ready`, while `GET /health` stays ops' dependency-free liveness probe). The readiness gate on `/health/ready`: in production, a schema `behind` head returns 503 `db_unavailable` with `details.reason = "schema_behind"` (the F§1.5 registry documents that reason), so a release starting on a behind-head schema fails its deploy health check and the previous release keeps serving. `backend/tests/test_migrations.py` (up, compare, down, up; every revision defines `downgrade`). The `backend-postgres` CI job runs `alembic upgrade head` and `alembic check`. The startup revision check logs a WARNING. `db.init_db()` survives only for test fixtures and CLIs. `repos.hymns.seed_church_from_catalog(church_id, session)` copies every `hymn_catalog` row. `test_route_guards.py`. | 7-C adds `require_head` to `db/schema_check.py` and 7-B's `scripts/migrate.py` uses `revision_state`. If the helper has another name or module, both build on it; a new `db/revision.py` is created only if slice 1 shipped no revision helper at all. |
| 3 | `hymn_search.parse_themes(theme) -> list[str]` handles None, lists, `{A,"B c"}`, and comma or semicolon strings. `lxml` and the audio resolver are gone. `worship_service.py` no longer calls `load_dotenv`. | `normalize_legacy_data` embeds a frozen copy of whatever parser slice 3 ships for the array-literal case. |
| 5a | `0005_services_extras`, including the index `ix_services_church_date` (its file number follows merge order, so it may be `0007_services_extras` if 6b-1 merged first; F§3.5). `list_saved_services` and `record_usage` are kept only for the frozen branch's tests. `hymn_usage.rebuild_usage_for_date(church_id, date_iso, *, session) -> int` exists, with tests (per-church-and-date advisory lock on Postgres; replaces the date's rows with the union of archived services on that date; `ValueError` on a non-`YYYY-MM-DD` date). `usecases.archive.delete_service` and a date-changing `replace_service` leave `hymn_usage` untouched. `backend/tests/test_services_streamlit_compat.py` exists. | If `delete_service` already rebuilds, 7-G only adds the future-date condition. |
| 5b | `google_oauth.save_user_token(user_id, google_email, refresh_token, *, session=None)`, `get_connection(user_id, *, session=None) -> GmailConnection \| None` and `delete_connection(user_id, *, only_if_token: str \| None = None, session=None) -> str \| None` are the only readers and writers of `gmail_tokens.refresh_token`. `delete_connection` runs `DELETE … WHERE user_id = :u [AND refresh_token = :only_if_token]` and returns the removed token. `disconnect_gmail` calls it unconditionally; `send_bulletin_email`'s `INVALID_GRANT` / `INSUFFICIENT_SCOPE` path calls it with `only_if_token=connection.refresh_token` (the plaintext `get_connection` returned) and reports "Your Gmail connection changed while sending…" with `disconnected: false` when no row matched. `GoogleOAuthConfig.configured`. `usecases/email.py` checks configuration. Gmail startup warnings live in the lifespan. `NEXT_PUBLIC_LEGACY_APP_URL` is optional in Vercel. | If more token readers exist, each goes through `TokenCipher` as well. |
| 6a | `backend/seed/hymnals/PH1990.csv` and `hymnal_sources.py`. The catalog source reads the `hymn_catalog` **table**. `import_hymnal.py` calls `load_dotenv()` inside `main()`. `usecases/email.py`'s `MALFORMED_CONTACT_HINT` reads "An admin can fix it in Settings → Contacts." (the 5b hand-off, with 6a's test asserting it). `ESV_API_KEY` is either already read through `api/settings.py` (if 6a took slice 2's configuration hand-off) or still read by `scripture_fetcher._esv_key()` from the environment. | If the hint still says "current app", 7-B swaps it and adds the assertion (`test_no_legacy_copy.py` fails until it does). If the ESV key is still read from the environment, 7-E moves it (Changed modules → `api/settings.py`); `test_env_access.py` fails until it does. |
| 6b | Merged and deployed, with **both** of its revisions applied in production: `0006_invites_integrity` (6b-1: the invite-role CHECK and the pending-email partial unique index) and the one-owner revision `memberships_one_owner` (6b-2: the `uq_memberships_one_owner` partial unique index; its file number follows merge order). With 5a's `0005_services_extras` also merged, `memberships_one_owner` is expected to be the Alembic head when 7-C merges (F§3.5). `streamlit_tests/test_settings_members_invites.py` is already deleted. `backend/tests/test_streamlit_port_ledger.py` maps every remaining Streamlit test to a replacement or an explicit `DROPPED:` reason (F acceptance 19); 6b says slice 7 deletes it. `backend/scripts/check_integrity.py` (read-only; prints "OK: no integrity violations.") and its runbook in `backend/migrations/README.md`. 6b-2 deletes `LegacySettingsNote` (`legacy-settings-note.tsx` and its use in the settings layout; 6b scope table and acceptance 22). | This slice's revisions, `normalize_legacy_data`, `contract_after_cutover` and `encrypt_gmail_tokens`, take the next free file numbers after whatever is the Alembic head when each merges; the first one's `down_revision` is that head, and `test_migrations.py`'s single-head assertion enforces the chain (F§3.5). 7-B only **verifies** that `legacy-settings-note.tsx` is gone (the guard test fails otherwise); deleting it there is a fallback, not planned work. |

### Delivery plan

Commits follow TDD and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. "Owner" means a manual step in a console, recorded in `docs/ops-runbook.md` → "Streamlit retirement record" (dates and outcomes only, **never secret values**).

| Step | Kind | Contents | Gate before the next step |
|---|---|---|---|
| 7-0 | Owner | The entry gate (below). | Every entry item recorded. |
| 7-A | PR into `streamlit-frozen` | The tombstone: `app.py` is replaced by the "moved" page (UX §1). Nothing else on the branch changes. Also open the **revert PR** as a draft and wait for its CI to go green; that is the revival drill. | Merged; the tombstone is live at `https://liturgy.streamlit.app/`; the day-0 message is sent. **The quiet period starts.** |
| 7-B | PR, `main` | "Remove the Streamlit app": the C2 deletions, C3, the C4 guards (with a `PENDING` allowlist), the copy sweep (verify 6a's `MALFORMED_CONTACT_HINT` swap and 6b's `LegacySettingsNote` deletion; `test_no_legacy_copy.py` and `legacy.guard.test.ts` enforce both), dead-code sweep part 1, `auth.upsert_from_claims` removed, the API stops reading and writing `users.google_sub` (the column is **unmapped** with `exclude_properties`, plus a suite-wide statement guard), docstrings, `test_services_streamlit_compat.py` renamed. Also the rollback-safe pre-deploy step (C14: `scripts/migrate.py` and `railway.toml`), which must be live **before** the first slice-7 revision so that every release a rollback can land on has it. | CI green; the merge deploy log shows `scripts.migrate` ran. |
| 7-C | PR, `main` | `normalize_legacy_data` (themes and usage dates); `require_head` in `db/schema_check.py` with its unit tests; `backend/scripts/catalog.py` (`export`, `seed`, `verify`); the startup warning for an empty catalog; tests. | Deployed (Railway runs `normalize_legacy_data`). Then the owner runs `export` against production. |
| 7-D | PR, `main` | Commit `backend/seed/catalog/hymn_catalog.csv` and its README; delete the Notion and migration code and their tests; remove `notion-client`, `playwright` and `beautifulsoup4`. The PR description contains the output of `verify` run against production (exit 0). | CI green; `verify` exit 0. |
| 7-E | PR, `main` | Config and docs: engine default (and a blank `DATABASE_URL` in `backend/.env.example`); `init_db` becomes `create_all_for_tests` (with `test_engine.py` and the startup tests updated); `import_hymnal.py` switches to 7-C's `require_head`; `test_create_all_scope.py`; the environment-access guard and the remaining moves; `requests` removed; `.env.example` parity; README, manual verification and frontend README rewrites; runbook updates (including the rollback order for migrating deploys). `PENDING` shrinks to `backend/migrations/README.md`. | CI green. |
| Quiet period | Owner | At least **7 days** after 7-A, including at least one Sunday service planned end to end in the new app, and no open "I can't do X in the new app" report from the tester. The owner may extend it. | All three conditions met. |
| **P** | Owner | **Point of no return** (runbook below): fresh backup, remove the Google URIs (before the app is deleted), delete the Streamlit Cloud app, revoke its GitHub access, rotate secrets, tag and delete the branch, Vercel and Supabase checks, uptime monitor, local cleanup, final message. | Every P step recorded. |
| 7-F | PR, `main` | Token encryption, part 1: `token_crypto.py`; encrypted writes; reads accept both formats; production refuses to start without a key when Gmail is configured. **Before merging:** the owner sets `GMAIL_TOKEN_ENCRYPTION_KEYS` on Railway and stores it in the password manager. | Deployed; a test bulletin email sends. |
| 7-G | PR, `main` | `contract_after_cutover`; `encrypt_gmail_tokens`; strict token reads; `compare_server_default=True`; post-cutover rules in `migrations/README.md`; the usage rebuild on deleting or re-dating a future-dated service (C15; may ship as its own small PR after P); `PENDING` empty. **Before merging:** run the backup workflow by hand. | Deployed; the post-deploy SQL checks and `alembic check` against production are recorded. Slice done. |

7-B to 7-E may merge during the quiet period. They change only `main`, and production Streamlit runs from `streamlit-frozen` (F D2; entry gate item 6). They also keep every F§3.4 and F§6.2 rule: `normalize_legacy_data` only normalizes theme text and usage dates into shapes the frozen app already writes and reads, and 7-B stops the API's own use of `google_sub` without dropping the column. Each of those PR descriptions carries the checkbox "Keeps F§3.4 and §6.2 (revival still possible)". 7-F and 7-G come **only after P**. From 7-B on, a regression in the new stack is rolled back with R2, during the quiet period too; R1 is only about Streamlit.

**If the F§6.1 contingency applied** (entry gate item 6 finds Streamlit Cloud deploying from `main`, not `streamlit-frozen`):
- 7-A is a PR into **`main`** that replaces `app.py` there, and the revival PR reverts it on `main`.
- 7-B, 7-D and 7-E merge **only after P**, because a revival on `main` needs the Streamlit code, the root `requirements.txt` that Streamlit Cloud installs, `init_db` and the contingency wrappers. 7-C may still merge during the quiet period (it adds files and a compatible data revision only), but C14 (`scripts/migrate.py` and the `railway.toml` change, which touch nothing Streamlit uses) is then split out of 7-B into its own PR and merged **before** 7-C, so rollbacks stay safe.
- 7-B also deletes every contingency wrapper and `AppTest` smoke test listed in the coverage ledger.
- P step 9 tags `main`'s last commit before 7-B as `streamlit-final`; there is no frozen branch to delete.

**Entry gate (7-0)**, recorded in the runbook:
1. 6a and 6b are merged and deployed, and their manual checklists are done.
2. The parity-gate date (5b) and the tester's settings sign-off after 6b (F§6.3 phase D) are recorded.
3. 6b's `test_streamlit_port_ledger.py` passes on `main` (Testing → "Port ledger"), so every remaining `streamlit_tests` test has an existing replacement or an explicit `DROPPED:` reason. If it fails, 7-B is blocked.
4. `git log origin/streamlit-frozen` since the freeze cut shows only data-safety fixes and the 5b banner.
5. A backup run from the last 24 hours exists (`workflow_dispatch` if needed).
6. Streamlit Cloud's `liturgy` app deploys from branch `streamlit-frozen`, `app.py` (checked in the app's settings and matched against the freeze record in `docs/ops-runbook.md` → "Streamlit freeze"). If it deploys from `main`, the F§6.1 contingency applied: follow "If the F§6.1 contingency applied" above. Otherwise, a grep on `main` confirms that none of the contingency wrappers or `AppTest` smoke tests exist.

---

## User experience

Nothing changes in the React app's screens. The people who notice this slice are the tester (at the old address and in two messages) and the owner (the runbook).

### 1. Tombstone page (old address, during the quiet period)

`app.py` on `streamlit-frozen` is **replaced** by this file (7-A). It needs no login, no database and no secrets. `ui_helpers.py`, `streamlit_views/` and the rest stay on the branch, so the branch CI (`streamlit_tests`) stays green; no test imports `app.py`.

```python
"""Moved notice (slice 7). Revert this commit to bring the full app back."""
import streamlit as st

NEW_APP_URL = "https://worship-service-builder.vercel.app"

st.set_page_config(page_title="Worship Service Builder has moved", layout="centered")
st.title("Worship Service Builder has moved")
st.write(
    "Services, hymns, settings and your church's people are all in the new app now. "
    "Sign in there with the same Google account."
)
st.link_button("Open the new app", NEW_APP_URL, type="primary")
st.caption("This old address stops working on {RETIRE_DATE}. Please update your bookmark.")
```

- `{RETIRE_DATE}` is filled in the PR with the planned P date, written like "Sunday, October 18" (it is informational; slipping it by a few days is harmless).
- Layout: Streamlit's centered layout reads fine at 375 px. The button is a full link to the new app; `st.link_button` opens it in a **new tab** (as the old Gmail button did, inv F8), which is acceptable here because the old tab has nothing left to do.
- The only other state: without traffic, Streamlit Cloud puts the app to sleep, because `keep-awake.yml` is deleted in 7-B. A visitor then sees Streamlit's own sleep page with a wake button, and after waking, the tombstone. This is acceptable for a page that exists only to redirect.

This is the **second planned exception** to the freeze policy (the first was the 5b banner). It is a PR into the protected branch, and the `backend` check must pass.

### 2. Messages to the tester (the owner sends them; exact copy)

**Day 0, when 7-A is live:**
> Quick update: everything now lives in the new app at https://worship-service-builder.vercel.app — services, hymns, liturgy prompts, contacts and people. The old address (liturgy.streamlit.app) now only shows a link to the new one, and it will be switched off on {RETIRE_DATE}. Please update your bookmark or home-screen icon. Nothing you've saved is lost. If there's anything you used to do in the old app that you can't do in the new one, tell me before {RETIRE_DATE}.

**At P, after the rotation checks pass:**
> The old app is now switched off for good; https://worship-service-builder.vercel.app is the only address. Please delete any bookmark to liturgy.streamlit.app, because that address no longer belongs to us. I also changed some behind-the-scenes passwords. If the app ever asks you to reconnect Gmail, click Connect Gmail once; nothing else is needed.

**Only if Streamlit is revived during the quiet period (R1):**
> I've switched the old app back on for now at https://liturgy.streamlit.app while I fix {issue}. Anything you save in either app shows up in both. I'll let you know when it's fixed.

### 3. The new app

- **Unchanged screens.** No route, component or copy changes. The only user-visible change is that neither a screen nor a backend message mentions "the current app": 6b already removed the Settings note, and 6a already changed the malformed-contact hint on a bulletin send to "…An admin can fix it in Settings → Contacts." 7-B's two guard tests (`legacy.guard.test.ts` and `test_no_legacy_copy.py`) prove both.
- **Gmail after 7-F and 7-G.** Token encryption is invisible. The one new path is a stored token that cannot be decrypted (for example after a key mistake). The server logs an ERROR and treats the user as **not connected**, so they see 5b's existing states:
  - `/settings/account`: "Connect your Gmail to email bulletins from your own account. The app can only send email for you; it can't read your mail." plus `Connect Gmail`.
  - Email dialog on send: 409 `gmail_not_connected`, "Connect your Gmail first, then try again." plus `Connect Gmail`.

  Reconnecting overwrites the row, so the state heals itself.
- **Deployment without a key (development only):** `GET /gmail-connection` returns `configured: false`, so the UI shows 5b's "Per-user Gmail sending isn't configured on this deployment." Production cannot reach this state, because it refuses to start (Backend changes → Configuration).

### 4. Owner flows

These are covered by the Delivery plan, the "Cutover runbook and rollback" section and the updated `docs/ops-runbook.md`. The runbook gets a new section, "Streamlit retirement record", that is filled in as the steps run.

---

## API

This slice adds, changes and removes **no routes**. The committed OpenAPI snapshot (`frontend/src/lib/api/openapi.json`) does not change, so `test_openapi_contract.py` passes without regeneration. There are no new error codes and no new rate-limit buckets.

| Method | Path | Guard | Request | Response | Errors |
|---|---|---|---|---|---|
| — | — | — | — | — | No endpoint added, changed or removed |

**Internal behavior changes on existing routes** (same schemas, codes and copy as slices 5a and 5b):

| Route | Change | Visible effect |
|---|---|---|
| `GET /gmail-connection` (user) | `configured` is true only when the Google client settings **and** a token cipher are both present. `connected` is false when the stored token cannot be decrypted. | 5b's existing "not configured" or "not connected" copy. |
| `POST /gmail-connection` (user) | The refresh token is stored encrypted (`enc:v1:` + Fernet). | None. |
| `DELETE /gmail-connection` (user) | The removed token is decrypted before best-effort revocation. An undecryptable token skips the revoke (WARNING) and still deletes the row. | None. |
| `POST /bulletin-emails` (church) | The stored token is decrypted before the refresh. Undecryptable → 409 `gmail_not_connected`, "Connect your Gmail first, then try again." On `INVALID_GRANT` / `INSUFFICIENT_SCOPE`, 5b's conditional delete still removes the dead row: it compares the **decrypted** stored token with the one used for the send (see `google_oauth` under Changed modules), so the user gets 5b's `disconnected: true` and is asked to reconnect; a reconnect in between keeps the new row and gives 5b's "changed while sending" message. | 5b's existing 409 and 502 handling. |
| `DELETE /services/{service_id}` (church); a date-changing `PUT /services/{service_id}` | 7-G: when the vacated date is today or later in the church's timezone (UTC if the stored zone is not a valid IANA name), that date's usage is rebuilt from the services still archived on it (C15). Past dates are untouched, as in 5a. | Deleting an abandoned planned service stops its hymns counting as "recently used". |
| `GET /me` and every authenticated route | `ensure_user` no longer reads or writes `users.google_sub` (7-B); the column is dropped in 7-G. | None. |
| `POST /churches` (user) | Unchanged: it seeds from the `hymn_catalog` table. Fresh databases (CI, local) are filled by `scripts.catalog seed`. | None in production. |

Guards: `test_route_guards.py` needs no allowlist change. There is no new church-scoped route, so there is no new isolation test (Testing lists the existing ones that must stay green).

---

## Backend changes

### Deleted

| Path | PR | Notes |
|---|---|---|
| `app.py`, `streamlit_views/` (incl. `settings.py`), `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py` | 7-B | Replaced by slices 1–6b (F§2.3.2: nothing re-exported). Their frozen copies remain at tag `streamlit-final` (P). |
| `streamlit_tests/` (every remaining file, incl. `conftest.py` and `__init__.py`; `test_onboarding.py` and `test_settings_members_invites.py` were already deleted by 1b and 6b) and `backend/tests/test_streamlit_port_ledger.py` (6b) | 7-B | Only after the port ledger passes (Testing). |
| Root `requirements.txt` (Streamlit Cloud installs it) | 7-B | The frozen branch keeps its own copy. |
| Root `.env.example` (documents the Streamlit `[auth]` block and `http://localhost:8501/`) | 7-B | `backend/.env.example` and `frontend/.env.example` are the only examples. |
| `.github/workflows/keep-awake.yml` | 7-B | The tombstone may sleep. |
| `backend/tests/test_no_streamlit_in_core.py`; `test_api_app.py::test_api_does_not_import_streamlit` | 7-B | Replaced by `test_no_streamlit_references.py` and `test_entry_points_import.py`. Streamlit is no longer installed in CI, so any `import streamlit` would fail anyway. |
| `auth.upsert_from_claims` (and `auth.py` if only it and `_normalize_email` remain), `backend/tests/test_auth.py` | 7-B | Its callers were `streamlit_auth.py:28` and `migrate_to_db.py:130`. Its assertions (normalization, idempotency, empty-email rejection) already exist as `ensure_user` tests (ops). The `google_sub` assertion is dropped. |
| `backend/migrate_to_db.py`, `backend/notion_hymns.py`, `backend/fill_from_hymnary.py`, `backend/tests/test_migrate_hymns.py`, `backend/tests/test_migrate_archive.py` | 7-D | Only after the catalog file is committed and `verify` passes against production. `test_import_hymn_catalog_is_idempotent` is re-expressed as the seed CLI's idempotency test. `test_import_usage_dedupes` is covered by 5a's `rebuild_usage_for_date` tests. |
| `backend/hymn_utils.py` and `test_hymn_utils.py` | 7-D | Only if the grep rule below finds no runtime caller after the Notion code goes (its callers today are `worship_service.py:17` and `migrate_to_db.py:27`). |
| `backend/tests/test_services_streamlit_compat.py` (5a) | 7-B | **Renamed** `backend/tests/test_services_storage_shape.py`, not dropped: the stored `services.hymns` shape stays as it is (Out of scope), so the assertion that an empty Opening slot is stored as exactly 3 entries in slot order with `title: ""` stays. The two "without the new keyword arguments" cases are deleted; they protected only Streamlit's call sites. |
| The F§6.1 contingency wrappers and `AppTest` smoke tests (coverage ledger), only if the contingency applied | 7-B (after P in that case) | Nothing to delete otherwise (entry gate item 6). |

### Dead-code sweep (7-B; completed in 7-D and 7-E)

**Rule:** after the Streamlit and Notion deletions, any function with no caller outside `backend/tests/` is deleted together with its tests, unless it is a documented CLI entry point. A test assertion that still describes live behavior is moved to the test of the function that now provides it.

Aid: run `pipx run vulture backend --exclude "backend/tests/*,backend/migrations/*" --min-confidence 80` once (it is not added as a dependency) and triage its output in the PR description.

Expected candidates (the final disposition comes from grep at implementation time):

| Candidate | Why it is expected dead | Test impact |
|---|---|---|
| `service_archive.list_saved_services` | kept by 5a only for frozen tests | `test_service_archive.py::test_list_saved_services_is_church_scoped` deleted; 5a's `list_services_page` isolation test covers the intent |
| `hymn_usage.record_usage` (plus `get_recently_used_identifiers` and `is_hymn_recently_used` if slice 3 replaced them) | kept by 5a for frozen tests | Its tests in `test_hymn_usage.py` deleted; 5a's rebuild tests and slice 3's recency tests cover the intent. Helpers still used by `rebuild_usage_for_date` (`_coerce_number`, date parsing) stay. |
| `email_contacts.get_contacts_for_display` | slice 5b hand-off | its assertion in `test_email_contacts.py` deleted |
| `repos.users.get_user_by_email` | tests only (inv §1 I); a global lookup that must never be exposed | deleted with its test if still unused |
| `repos.memberships.count_admins`, `add_membership`; `repos.invites.get_invite_by_code`; `repos.churches.update_church` | inv §1 I lists them as having no UI caller; slices 1, 6a and 6b may now use them | grep rule |
| `db.init_db` | renamed, not deleted (below) | fixtures updated |

### Changed modules

| Module | Change | PR |
|---|---|---|
| `backend/db/models.py` | 7-B: `User.google_sub` is **unmapped**, not deferred. The declaration `google_sub = Column(String, unique=True)` stays, so the column stays on `users.__table__` and `compare_metadata` stays clean, and `User` gets `__mapper_args__ = {"exclude_properties": ["google_sub"]}`, so the ORM neither selects nor inserts it (checked against SQLAlchemy 2.1: the INSERT and SELECT omit the column). (A `deferred()` column is still mapped, and the unit of work sends an explicit NULL for every mapped column without a default on INSERT, so a deferred mapping would still write it.) The docstring says "on the table only until the contract_after_cutover revision drops it". 7-G: the column is removed from the table too. The module docstring's "never server defaults" rule gets one sentence noting the declared `server_default` columns from `0004` and later. | 7-B, 7-G |
| `backend/repos/users.py` | `ensure_user(email, name=None, picture=None, *, now=None)`: the `google_sub` parameter, its insert value and its SELECT column are removed. `_user_to_dict` drops `"google_sub"`. | 7-B |
| `backend/api/security.py:104-122` | `claims_to_profile` docstring rewritten: the API matches users by email only, and `sub` stays `None`. The `"sub"` key is removed if `ensure_user` no longer takes it. | 7-B |
| `backend/tenancy.py:1-6`, `backend/google_oauth.py` docstrings, `backend/repos/hymns.py:1-5` | Streamlit and Notion mentions removed. The Gmail docstring describes the `/gmail/callback` flow only. | 7-B |
| `backend/tests/conftest.py` | 7-B: `make_user(..., google_sub=None, ...)` loses the parameter (the attribute no longer exists on `User`), and an autouse fixture `forbid_google_sub_sql` listens for `before_cursor_execute` on the `Engine` **class** (so every engine a test creates is covered) and fails the test if any DML statement (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) contains `google_sub`. Ignored: DDL (`CREATE`, `ALTER`, `DROP`, `PRAGMA`, which covers `create_all_for_tests` and every migration's schema changes) and Alembic's batch-mode copy statements (they name an `_alembic_tmp_` table), so the migration tests need no exemption. 7-G removes the fixture with the column. 7-E: `tmp_db` calls `create_all_for_tests()`. | 7-B, 7-E, 7-G |
| `backend/tests/test_api_me.py` | `test_me_matches_existing_streamlit_user_by_email` is renamed `test_me_matches_existing_user_by_email`. The `google_sub` fixture argument and the assertion `user.google_sub is None` are removed (the suite-wide guard now proves the API never writes it). | 7-B |
| `backend/db/engine.py` | `_database_url()`: returns the stripped `DATABASE_URL` if it is non-empty. Otherwise it uses the **absolute** path `<repo>/data/app.db` (`Path(__file__).resolve().parents[2] / "data" / "app.db"`), creates the directory, and logs WARNING once: `DATABASE_URL is not set; using local SQLite at {path}`. This replaces the cwd-relative `sqlite:///data/church.db`. The ops production guard still refuses SQLite in production. `init_db()` is renamed **`create_all_for_tests()`**, and its docstring says it must never run against a real database. | 7-E |
| `backend/db/__init__.py` | Exports `create_all_for_tests` instead of `init_db`. | 7-E |
| `backend/tests/test_engine.py`; `backend/tests/test_startup.py` (ops) | `test_public_imports_are_reexported` imports `create_all_for_tests` instead of `init_db`, and the `sqlite:///data/app.db` normalization case stays (it tests `_normalize_url` only). Any remaining `api.main.init_db` spy or stub in the ops startup tests (if slice 1 did not already remove it with the lifespan call) is deleted; the production-guard test instead asserts that no table is created. Every other `init_db` reference found by `test_create_all_scope.py` is renamed. | 7-E |
| `backend/.env.example` | `DATABASE_URL=` is **blank**, with the comment "Leave blank for the local SQLite file `<repo>/data/app.db`; production uses the Supabase session-pooler URL (see README)." This replaces `sqlite:///../data/app.db`, which depended on the working directory, and removes the "SAME SQLite file the Streamlit app uses" wording. | 7-E |
| `backend/db/schema_check.py` (slice 1) | Gains `require_head(engine) -> None`, built on `revision_state`: `current` returns; otherwise it raises `SystemExit(2)` with `Database schema is at {current or "an empty database"}, expected {head}. Run "alembic upgrade head" from backend/ first.` (`ahead` gets the same message; a CLI must not write to a schema it does not know). No new module. | **7-C** (the catalog CLI needs it) |
| `backend/import_hymnal.py` | `main()` calls `require_head(get_engine())` instead of `init_db()`. | 7-E |
| `backend/railway.toml` (slice 1) | `preDeployCommand = ["python -m scripts.migrate"]` replaces `["alembic upgrade head"]`. `healthcheckPath` stays `"/health/ready"` (slice 1; F§3.3); `/health` stays the dependency-free liveness probe and is not the deploy health check. | 7-B |
| `backend/usecases/archive.py` (5a) | C15, after P: `delete_service` reads the row's normalized date before deleting. If that date is today or later in the church's timezone (UTC when the stored zone is invalid), it calls `hymn_usage.rebuild_usage_for_date(church_id, date, session=s)` in the same transaction after the delete. A date-changing `replace_service` does the same for the **old** date after rebuilding the new one. A past date, a NULL date and an unparseable legacy date leave `hymn_usage` untouched, as today. Reason: a future service that is deleted or moved was never held, so its hymns should not count as recently used; a past service's hymns were sung, and deleting its archive entry does not change that (5a's "Last Sunday" case). | 7-G |
| `backend/api/settings.py` | Adds `gmail_token_encryption_keys` (stripped) and a `token_cipher: TokenCipher \| None` property, parsed once. Any remaining configuration read elsewhere moves here. In particular `ESV_API_KEY`: slice 2 recorded `scripture_fetcher._esv_key()` reading the environment as a deviation from F§2.3.5, because the frozen Settings code and `test_settings_prompts_translation.py` call the zero-argument `available_translations()`. If 6a already moved the key (porting that test), this is a verify; otherwise 7-E moves it, after 7-B has deleted those frozen callers, and passes it to `scripture_fetcher`. Either way `test_env_access.py` (7-E) fails while `scripture_fetcher.py` reads the environment. | 7-E, 7-F |
| `backend/api/main.py` lifespan | Adds the empty-catalog warning (7-C) and the token-key checks (7-F, below). Like slice 1's checks, each catches and logs its own errors, except the production refusal, which is intentional. | 7-C, 7-F |
| `backend/google_oauth.py` | `save_user_token(user_id, google_email, refresh_token, *, cipher, session=None)` always stores `cipher.encrypt(refresh_token)`. `get_connection(user_id, *, cipher, session=None)` decrypts. `delete_connection(user_id, *, cipher, only_if_token: str \| None = None, session=None) -> str \| None` keeps 5b's race check, redefined for ciphertext (Fernet output is randomized, so comparing `refresh_token = :only_if_token` in SQL can never match):<br>• **Unconditional** (`only_if_token=None`, used by `disconnect_gmail`): select the stored value, `DELETE … WHERE user_id = :u`, and return the decrypted token, or None when it cannot decrypt (the row is still deleted).<br>• **Conditional** (the `INVALID_GRANT` / `INSUFFICIENT_SCOPE` path passes the plaintext `connection.refresh_token`): `SELECT refresh_token … WHERE user_id = :u FOR UPDATE` (a no-op on SQLite); decrypt it in Python; if there is no row, it cannot be decrypted, or the plaintext differs from `only_if_token`, delete nothing and return None. Otherwise `DELETE … WHERE user_id = :u AND refresh_token = :stored` (the exact stored value just read) and return the plaintext when a row was removed, else None. The stored-value predicate keeps the check race-safe on SQLite too, where there is no row lock.<br>**7-F (transition):** a value without the prefix is returned as plaintext and logs WARNING `gmail_token_plaintext user_id=…` once per user per process. **7-G (strict):** a value without the prefix, or one that fails to decrypt, logs ERROR `gmail_token_undecryptable user_id=…` and returns None. Nothing logs a token. | 7-F, 7-G |
| `backend/usecases/email.py` | 7-B (copy sweep, verify only): `MALFORMED_CONTACT_HINT` reads "An admin can fix it in Settings → Contacts." (6a's swap of 5b's "…in the current app's Settings.", with 6a's test). If 6a's swap was missed, 7-B makes it, removes 5b's code comment about the check, and adds the test asserting the new text; `test_no_legacy_copy.py` fails until then. 7-F: `gmail_ready = config.configured and cipher is not None` replaces `config.configured` in every check. It passes `cipher` to the token functions. | 7-B, 7-F |
| `backend/requirements.txt` | Remove `notion-client`, `playwright` and `beautifulsoup4` (7-D) and `requests` (7-E, after the grep shows no importer). Add `cryptography>=42` explicitly (7-F; already present through `PyJWT[crypto]`, but now imported directly). The "migration only" comment block goes. | 7-D, 7-E, 7-F |
| `requirements-dev.txt` (root) | The first line becomes `-r backend/requirements.txt`. The dev tools from earlier slices (pytest, respx, …) stay. | 7-B |
| `pytest.ini` | `pythonpath = backend`, `testpaths = backend/tests`. Markers from slice 1 stay. | 7-B |
| `.gitignore` | **Keeps** `.streamlit/secrets.toml`, `data/*.json` and `data/*.db`, because an old local secrets file, the legacy JSON exports (`data/email_contacts.json` holds contact names and addresses; the archive and usage JSON read by the deleted `migrate_to_db.py`) and local databases must never be committed to this public repo. Only the `data/*.json` comment changes, from "optional: remove data/*.json to commit archive/usage" to "legacy JSON exports with personal data; never commit". `test_foundation_setup.py` asserts all three entries. | 7-D |

### New modules

**`backend/token_crypto.py`** (7-F). It is pure and has no settings import.

```python
PREFIX = "enc:v1:"

class TokenKeyError(ValueError): ...      # message names the entry index, never the key
class TokenDecryptError(Exception): ...

@dataclass(frozen=True)
class TokenCipher:
    _fernet: MultiFernet
    @classmethod
    def from_setting(cls, raw: str | None) -> "TokenCipher | None":
        """Comma-separated Fernet keys; first encrypts, all decrypt. Blank → None."""
    def encrypt(self, plaintext: str) -> str: ...     # PREFIX + Fernet token
    def decrypt(self, stored: str) -> str: ...        # TokenDecryptError on no prefix / InvalidToken
    def rotate(self, stored: str) -> str: ...         # re-encrypt under the first key

def is_encrypted(stored: str) -> bool: ...
def generate_key() -> str: ...                        # Fernet.generate_key().decode()
```

- Algorithm: Fernet (AES-128-CBC with HMAC-SHA256), with `MultiFernet` for key rotation. The key comes from `GMAIL_TOKEN_ENCRYPTION_KEYS`, which lives only on Railway and in the owner's password manager.
- Generate a key with `python -c "from token_crypto import generate_key; print(generate_key())"`, run from `backend/`.

**`backend/scripts/migrate.py`** (7-B; C14). Railway's pre-deploy command, `python -m scripts.migrate`, run from `backend/`.
- It reads `revision_state` (slice 1's `db.schema_check`) on the configured engine.
- `ahead` (the database is at a revision this release's scripts do not contain, which is what a rollback onto an older release looks like): log WARNING `Database is at revision {current}, which this release does not know (head {head}); skipping "alembic upgrade head". Expected right after a rollback.` and exit 0. The readiness gate already returns 200 on `ahead` (slice 1).
- Otherwise: `alembic.command.upgrade(alembic_config(), "head")`. An exception exits non-zero, so the deploy fails and the previous release keeps serving (F§3.3), as today.
- Why: with a plain `alembic upgrade head`, Alembic cannot locate the database's revision in an older release's `migrations/versions` and fails, so a Railway redeploy or rollback of an older deployment would itself fail after 7-C or 7-G. Every slice-7 revision works with the previous release's code (rules after the cutover), so skipping the upgrade is safe. It ships in 7-B, before the first slice-7 revision, so the release a 7-C rollback lands on already has it.

**`backend/scripts/catalog.py`** (7-C). Run as `python -m scripts.catalog <command>` from `backend/`; add `scripts/__init__.py` if it is missing. `main()` calls `load_dotenv()` and then `require_head(engine)` (added to `db/schema_check.py` in the same PR).

| Command | Behavior |
|---|---|
| `export [--out PATH]` | Default `seed/catalog/hymn_catalog.csv`. Reads every `hymn_catalog` row and writes a deterministic CSV (format under Data and migrations). If any row has a NULL or blank `title` (the column is nullable), it exits 2 with `hymn_catalog has {n} rows with no title, e.g. {hymnal} #{number}; fix the data before exporting.` If duplicate keys exist, it exits 2 with `hymn_catalog has {n} duplicate (hymnal, number, title) keys, e.g. {hymnal} #{number} "{title}"; fix the data before exporting.` It prints `exported={n} sha256={hex}`. |
| `seed [--file PATH] [--dry-run]` | Validates the whole file first: a row with a blank `hymnal` or `title`, or a duplicate key, exits 2 naming the line, and nothing is written. Then, in one transaction: insert missing rows (new uuid4 ids), update rows whose compared fields differ, **never delete**. It prints `inserted={i} updated={u} unchanged={k} extra_in_db={e}`. It is idempotent; a second run inserts 0. |
| `verify [--file PATH]` | Exit 0 when the database and the file are equal on every key and field. Otherwise exit 1 and print the missing, extra and changed counts plus up to 10 example keys. |

- **Key:** `(hymnal, number, title.strip().lower())`. A NULL number is a distinct key value.
- **Compared fields:** `title` in its **exact** text (so a title that differs only in case or surrounding spaces under the same key counts as changed, and `seed` updates it to the file's text), `scripture_refs`, `theme`, `hymnary_link` and `audio_url`.
- **Equality:** an empty string and NULL compare equal, and `seed` writes NULL for empty fields.
- *Amendment 2026-09-26 (PR #4):* the hymn facts `text_year` and `hymnal_count` (integers) are also exported, compared by `seed` and checked by `verify`. They follow the backfill's fill-blanks rule: an empty cell never nulls a stored fact, so `seed` leaves it and `verify` does not count it. A non-empty cell that differs from the stored value, including a stored NULL, is a changed field under the rules above: `seed` updates it and `verify` reports it.
- Ids are not exported. Nothing references `hymn_catalog.id`: `seed_church_from_catalog` copies field values, and 6a's catalog source maps rows.

**`backend/scripts/rotate_gmail_token_key.py`** (7-F). `python -m scripts.rotate_gmail_token_key [--dry-run]`.
- It reads the cipher through `api.settings`, re-encrypts every `gmail_tokens` row with `TokenCipher.rotate` in one transaction, and prints `rotated={n} undecryptable={m}`.
- It exits 1 if `m > 0` and leaves those rows unchanged.
- Runbook procedure: put the new key **first** → deploy → run the CLI → remove the old key → deploy.

### Configuration and startup (7-F)

| Condition | Environment | Behavior (exact text) |
|---|---|---|
| An entry in `GMAIL_TOKEN_ENCRYPTION_KEYS` is not a valid Fernet key | any | Refuse to start: `GMAIL_TOKEN_ENCRYPTION_KEYS entry {n} is not a valid Fernet key.` |
| All three `GOOGLE_*` settings are set, but there is no key | production | Refuse to start: `GMAIL_TOKEN_ENCRYPTION_KEYS is required in production when Gmail sending is configured.` A failed deploy leaves the previous release serving (F§3.3). |
| No key | development | WARNING, added to 5b's Gmail warnings: `Gmail sending is disabled: GMAIL_TOKEN_ENCRYPTION_KEYS is not set.` `configured` is false. |
| `hymn_catalog` has no rows (7-C) | any | WARNING: `hymn_catalog is empty; new churches will get an empty hymnal. Run "python -m scripts.catalog seed" from backend/.` Never blocks startup. |

### Guards (tests that keep the retirement true)

| Test | Asserts | PR |
|---|---|---|
| `backend/tests/test_no_streamlit_references.py` | `git ls-files` (the test skips if git is unavailable) finds no tracked file whose contents or path contain `streamlit` (case-insensitive), except the **permanent allowlist**:<br>• `.gitignore` (it must keep ignoring `.streamlit/secrets.toml`);<br>• this test file;<br>• `backend/tests/test_foundation_setup.py` (it asserts that `.gitignore` entry);<br>• `frontend/src/lib/legacy.guard.test.ts` (the frontend guard, which names what it forbids);<br>• `docs/ops-runbook.md` (the retirement record);<br>• `docs/superpowers/**` (historical specs);<br>• `backend/migrations/versions/**` (immutable history).<br>Every other test is written so that it does not need the word: `test_ci_workflow.py` drops its `streamlit_tests` assertion (this repo-wide check already covers `ci.yml`), and `test_foundation_setup.py` relies on this check for the Streamlit paths and requirement lines. A module-level `PENDING` set lists files still to be cleaned by later PRs. 7-B **derives** its initial contents from `git grep -il streamlit` on the 7-B branch after the deletions, minus the allowlist (expected to include `README.md`, `docs/manual-verification.md`, `backend/migrate_to_db.py`, `backend/migrations/README.md`, `backend/.env.example` and `backend/tests/test_docs.py`, but the grep is authoritative). Files 7-B already edits (the docstrings under Changed modules, the renamed tests) are cleaned there rather than listed. 7-D, 7-E and 7-G shrink `PENDING`; it is **empty** at the end. A second assertion fails if a `PENDING` entry no longer needs to be there, so the list cannot go stale. | 7-B |
| `backend/tests/test_no_legacy_copy.py` | The backend twin of the frontend legacy-copy guard. Using AST over the tracked `backend/**/*.py` files (excluding `backend/tests/**` and `backend/migrations/versions/**`), no string literal (every `ast.Constant` whose value is a `str`: messages, constants such as `MALFORMED_CONTACT_HINT`, f-string parts and docstrings) contains `current app` (case-insensitive). Comments are not string literals and are not checked. Failures print `file:line` and the offending text. It never names the retired package, so it needs no allowlist entry in `test_no_streamlit_references.py`. | 7-B |
| `backend/tests/test_entry_points_import.py` | In a subprocess from `backend/`: `import api.main, import_hymnal, scripts.export_openapi, scripts.check_integrity, scripts.migrate` succeeds, as do `scripts.catalog` (from 7-C) and `scripts.rotate_gmail_token_key` (from 7-F). It only asserts that the imports succeed, so it never names the retired package. Replaces `test_no_streamlit_in_core.py`. | 7-B |
| `backend/tests/test_env_access.py` | Using AST over `backend/**/*.py` (tests excluded): `os.getenv(...)`, `os.environ.get(...)` and `os.environ[...]` appear only in `api/settings.py`, `db/engine.py`, `integrations/*.py`, `migrations/env.py` and `migrations/versions/*.py`. A `load_dotenv()` call at **module level** appears only in `api/main.py`; everywhere else it must be inside a function. Failures print `file:line`. | 7-E |
| `backend/tests/test_env_example.py` | Every environment-variable name read in the allowlisted modules (from the same AST pass) appears as `NAME=` in `backend/.env.example`, and every `NAME=` there is read somewhere. `DATABASE_URL=` has an empty value, so the documented setup uses the absolute default path. | 7-E |
| `backend/tests/test_foundation_setup.py` (rewritten) | Root `requirements.txt`, root `.env.example`, `app.py`, `ui_helpers.py` and `.github/workflows/keep-awake.yml` do not exist (7-B), nor do `migrate_to_db.py`, `notion_hymns.py` and `fill_from_hymnary.py` (7-D); tracked Streamlit-named paths and a Streamlit requirement line are caught by `test_no_streamlit_references.py`. `backend/requirements.txt` contains none of `lxml` (from 7-B), `notion-client`, `playwright` and `beautifulsoup4` (from 7-D), or `requests` (from 7-E). It contains `alembic`, and `cryptography` from 7-F. `requirements-dev.txt` starts with `-r backend/requirements.txt`. `pytest.ini` has `testpaths = backend/tests`. `backend/railway.toml`'s pre-deploy command is `python -m scripts.migrate` (replacing slice 1's pre-deploy assertion), and its `healthcheckPath` is still `"/health/ready"` (slice 1's assertion kept). The Procfile and Python 3.11 assertions are kept. The gitignore assertions: `data/*.db`, `data/*.json` and `.streamlit/secrets.toml` present. | 7-B … 7-F |
| `backend/tests/test_ci_workflow.py` | `.github/workflows/` contains exactly `backup.yml`, `ci.yml` and `keepalive.yml`. The existing assertions stay. (The "no `streamlit_tests` in `ci.yml`" check is left to the repo-wide guard, so this file never names the retired package.) | 7-B |
| `backend/tests/test_ops_workflows.py` | The ops `keep-awake.yml` assertion becomes "the file does not exist". | 7-B |
| `backend/tests/test_docs.py` (rewritten) | See Testing. | 7-E |
| `backend/tests/test_create_all_scope.py` | `create_all(` appears only in `db/engine.py` (`create_all_for_tests`) and under `backend/tests/`; `init_db` appears nowhere under `backend/` (this test file excepted), which requires the `test_engine.py` and startup-test updates listed under Changed modules. | 7-E |

### C13: soft-deleted churches (decision)

- **No automatic hard purge.** Every route already rejects a soft-deleted church (`validate_active_church`), so the data is invisible. Keeping it lets the owner recover an accidental delete.
- The runbook gains a section "Deleted churches" with two procedures:
  - **Who may ask.** The operator honours a restore or purge only when the request comes from the user recorded as that church's **owner** in `memberships` (`select u.email from memberships m join users u on u.id = m.user_id where m.church_id = :id and m.role = 'owner';`), confirmed from that email address. Owner decision 5 lets only the owner delete a church, so only the owner can undo or finalize it; a request from an admin, a member or a removed member is declined. Each runbook entry records the church id, the requester's user id and email, the date and the action.
  - **Restore on request:** `update churches set deleted_at = null where id = :id;`. Invites stay revoked; the owner creates new invites.
  - **Purge on request:** take a manual backup, then `delete from churches where id = :id and deleted_at is not null;`. Memberships, hymns, services, usage, contacts and invites cascade (`ON DELETE CASCADE`); `created_by` is set to NULL elsewhere.
- Revisit an automatic purge when a second church onboards.

### Streamlit coupling removed (inv §3 rows closed here)

- `app.py:221-256` and `streamlit_tenancy.py:13-88` (hand-maintained reset lists, session tenancy): deleted. Their replacement is the keyed remount (slice 1) and the per-church draft store (slice 2).
- `streamlit_auth.py` (`st.user`, `st.login`, `st.logout`, `st.stop`, the dead `current_user_id`): deleted. Replaced by `get_current_user` and Supabase `signOut`.
- `ui_helpers.py` (query-parameter capture, invite pick, selectbox coercion, title-keyed map): deleted. Replaced by `/join` (1), the `/gmail/callback` cleanup (5b) and `HymnOut` (3).
- `backend/google_oauth.py` docstrings that assume a Streamlit root redirect: rewritten.
- The remaining `load_dotenv()` at import and `os.getenv` at call time (F§2.3.5): moved into entry points and settings, enforced by `test_env_access.py`.
- `backend/db/engine.py:24`: an absolute default path. (The comment at line 30 was fixed in ops.)
- `pytest.ini`, the requirements files, `test_foundation_setup.py` and `test_docs.py`: rewritten.

### Data access and tenancy notes

- There is no new church-scoped data access. `scripts/catalog.py` touches only the global, read-only `hymn_catalog`, which is never exposed beyond 6a's code, label and count listing.
- Token functions stay **user-scoped**, keyed by the caller's `user_id` (5b). Encryption changes the stored value, not who can read it.
- Logs:
  - `catalog`: counts and a sha256 only.
  - Token paths: user ids and outcome codes only; never a token, key or ciphertext.
  - `normalize_legacy_data` and `encrypt_gmail_tokens`: row counts only.
  - `scripts.migrate`: revision ids only.
- `scripts/catalog.py` and `rotate_gmail_token_key.py` are owner-run operations tools with no role check, like `import_hymnal.py` (inv H3). The runbook says so.

---

## Data and migrations

### Revisions

The chain before this slice (F§3.5) is `0001`–`0004` (slice 1), `0005_services_extras` with `ix_services_church_date` (5a), `0006_invites_integrity` (6b-1) and `memberships_one_owner` (6b-2); file numbers follow merge order. This slice adds three revisions, referred to by **name** throughout this spec: `normalize_legacy_data` (7-C), `contract_after_cutover` and `encrypt_gmail_tokens` (both 7-G, in that order). Each file gets the next free number after the Alembic head on `main` when its PR merges (for example `00NN_normalize_legacy_data.py`), and its `down_revision` is that head. `test_migrations.py`'s single-head assertion fails CI on a wrong or duplicate `down_revision`. Every revision has a working `downgrade()` (F§3.1).

**`normalize_legacy_data`** (7-C). A data-only revision that is compatible with the frozen Streamlit app. Two independent steps, each idempotent.

| Step | Upgrade | Downgrade |
|---|---|---|
| 1. Themes. For `hymns` and `hymn_catalog`: `SELECT id, theme WHERE theme LIKE '{%}'` | For each row, `new = _normalize(theme)`. `_normalize` returns `None` for an ambiguous row (below), which is left unchanged and counted. When `new` is not `None` and `new != theme`, `UPDATE … SET theme = :new WHERE id = :id`. Log `normalized {table}={n} skipped_ambiguous={m}`. | **No-op**, documented: the change keeps the meaning; the original literal text is not restored, and the pre-7-C backup holds it. |
| 2. Usage dates. `SELECT id, church_id, date_iso, hymn_number, hymn_title FROM hymn_usage WHERE length(date_iso) > 10` | Slice 3 found that Notion-imported rows can hold full datetimes (`2026-08-02T10:00:00.000-05:00`). For each row, `day = date_iso[:10]`; if `date.fromisoformat(day)` fails, leave the row and count it. Otherwise, if a row with the same `church_id`, `date_iso = day`, `hymn_title` and `hymn_number` (NULL matching NULL, compared in Python) already exists, **delete** this row as a duplicate; else `UPDATE … SET date_iso = :day WHERE id = :id`. Rows are processed one at a time in `id` order, so two datetime rows for the same day and hymn end as one row. `""`, NULL and other short values are not touched (slice 3's `usage_near` already ignores them). Log `usage_dates normalized={n} merged={d} unparseable={u}`. | **No-op**, documented, as step 1. |

`_normalize(raw)` (step 1):
1. If the stripped value is not wrapped in `{…}`, return it unchanged.
2. Otherwise parse it as a Postgres array literal: comma-separated elements; double-quoted elements with `\` escapes; an unquoted `NULL` means null. This is a **frozen copy** of the array branch of slice 3's `hymn_search.parse_themes`, so stored text matches what slice 3 already displays.
3. If any element contains `,` or `;`, return `None` (ambiguous): slice 3's `parse_themes` splits plain strings on commas and semicolons, so joining such an element would turn one theme into two. These rows keep their array literal, which `parse_themes` still reads correctly.
4. Otherwise drop blank and NULL elements, strip each one, and join them with `", "`. An empty result becomes `NULL`.

- Examples: `{Advent,"Hope and Peace"}` → `Advent, Hope and Peace`; `{}` → `NULL`; `{"Faith; Hope",Love}` → unchanged (counted as ambiguous); `Advent, Hope` → unchanged; `NULL` → unchanged.
- The rule that keeps display identical: for every value `x` that step 1 changes, `parse_themes(_normalize(x)) == parse_themes(x)` (tested).
- It runs on SQLite and Postgres (portable Core SQL plus Python parsing; fewer than about 1 500 theme rows and a few thousand usage rows).
- **Streamlit compatibility:** the frozen app only substring-matches theme keywords (inv D7), and the normalized text still contains the same words. For usage it compares `date_iso >= cutoff` as strings, and `YYYY-MM-DD` is exactly what it writes itself. So F§3.4 and §6.2 hold, and 7-C may merge during the quiet period.

**`contract_after_cutover`** (7-G, **only after P**)

| Operation | Upgrade | Downgrade |
|---|---|---|
| `users.google_sub` | `with op.batch_alter_table("users") as b: b.drop_column("google_sub")`. On Postgres the unnamed unique constraint (`users_google_sub_key`) goes with the column. | Also in batch mode, because SQLite cannot `ALTER` constraints (`render_as_batch` only affects autogenerate, not hand-written ops): `with op.batch_alter_table("users") as b: b.add_column(sa.Column("google_sub", sa.String(), nullable=True)); b.create_unique_constraint("uq_users_google_sub", ["google_sub"])`. On Postgres batch mode emits plain `ALTER TABLE` statements. The column comes back **empty**; nothing reads it. |
| Undeclared server default `'GG2013'` on `hymns.hymnal` and `hymn_catalog.hymnal` (created in production by the deleted `migrate_add_hymnal.py`, inv H2) | Postgres only: `ALTER TABLE hymns ALTER COLUMN hymnal DROP DEFAULT`, and the same for `hymn_catalog`. This is idempotent: a fresh database has no default, and the statement is a no-op there. | No-op, documented: the default was never part of the models, so after downgrade the schema equals the models at the previous head. |

- Why these two and only these:
  - `google_sub` was written only by the retired Streamlit login. The API matches users by email and never writes it (slice 0). Keeping an identifier nothing reads is data minimization debt.
  - The `'GG2013'` default is the last production-only drift. Removing it makes production equal to a fresh `upgrade head`, which is what lets `compare_server_default` be turned on.
- Why two deploys are safe: Railway's pre-deploy step runs the upgrade while the previous release still serves (F§3.3). 7-B already stopped every statement that referenced `google_sub`: the column is unmapped (`exclude_properties`), so the ORM neither selects nor inserts it, and `ensure_user` has no insert value or select column for it. The suite-wide `forbid_google_sub_sql` fixture proves this for every flow the backend tests exercise, not a hand-picked list. So the serving release never touches the column that 7-G drops. The API always sets `hymnal` explicitly (Python-side default), so dropping the database default affects no insert.
- In the same PR, `migrations/env.py` sets `compare_server_default=True`. If `alembic check` against CI Postgres or production reports only rendering-equivalent differences (for example `false` versus `'false'::boolean`), `env.py` supplies a `compare_server_default` callable that normalizes case, quotes and `::type` casts before comparing. Any real difference is fixed in `contract_after_cutover`.

**`encrypt_gmail_tokens`** (7-G, only after P and after 7-F is live)

| Step | Upgrade | Downgrade |
|---|---|---|
| Select `user_id, refresh_token FROM gmail_tokens WHERE refresh_token NOT LIKE 'enc:v1:%'` | If there are no rows, do nothing (no key needed). If there are rows and no key: raise `encrypt_gmail_tokens needs GMAIL_TOKEN_ENCRYPTION_KEYS to encrypt {n} Gmail tokens; set it and run the migration again.` Otherwise, `UPDATE … SET refresh_token = 'enc:v1:' || fernet(token)` per row. Log `encrypted={n}`. | Rows **with** the prefix are decrypted back to plaintext. The same key rule applies: no such rows → nothing to do and no key needed; rows and no key → raise `encrypt_gmail_tokens downgrade needs GMAIL_TOKEN_ENCRYPTION_KEYS to decrypt {n} Gmail tokens; set it and run the migration again.` |

- The key parsing is a minimal frozen copy inside the revision (split on commas, first key encrypts, all decrypt), using `cryptography.fernet` directly. Revisions do not import app modules.
- The revision reads the key with `os.environ.get("GMAIL_TOKEN_ENCRYPTION_KEYS", "").strip()`, **after** the select, and requires it only when there are rows to convert. So CI's `alembic upgrade head` and `downgrade base` (no key, no Gmail rows) pass. Railway's pre-deploy command has the key, and the laptop runbook exports it.
- It runs in the migration's transaction (Postgres), so a failure leaves every row as it was.
- Encrypted backups made before 7-G still contain plaintext tokens inside the `age` encryption. They age out after 30 days.

### Seed file format (7-C tool, 7-D file)

`backend/seed/catalog/hymn_catalog.csv`:
- UTF-8 **without** BOM, LF line endings, `csv.QUOTE_MINIMAL`.
- Header exactly `hymnal,number,title,scripture_refs,theme,hymnary_link,audio_url,text_year,hymnal_count` (*amendment 2026-09-26*: the last two are PR #4's hymn facts).
- `number`, `text_year` and `hymnal_count` are integers or empty. Other fields are stored text; NULL is written as empty.
- Rows are sorted by `(hymnal, number IS NULL, number, title.lower(), title)`, so a re-export produces no diff.
- There are no duplicate keys (`export` refuses them).

`backend/seed/catalog/README.md` explains:
- that this file is the source of `hymn_catalog`, which is copied into every new church;
- how to regenerate it (`export`) and apply it (`seed`);
- how it differs from `seed/hymnals/` (6a's hymnals an admin can **add**);
- attribution: numbers and titles from the hymnal, with scripture references, themes and links gathered from Hymnary.org during the original import. See open question 1.
- *amendment 2026-09-26:* the `text_year` and `hymnal_count` columns: the year the words were written and the number of hymnals that include them, filled from Hymnary.org's public API by the ops backfill CLI (`backfill_hymn_facts.py`). An empty cell means unknown, and `seed` never clears a stored value for it.

The file is created by the owner running `export` against production **after `normalize_legacy_data` is applied there**, so the committed themes are already clean.

**Fresh databases (CI, local, disaster recovery):** `cd backend && alembic upgrade head && python -m scripts.catalog seed`. The README documents this, and the empty-catalog startup warning points to it. Production already holds the same rows; `verify` proves it (7-D gate).

### Finishing the Alembic adoption

| Item | Where |
|---|---|
| `create_all` only in test fixtures (`create_all_for_tests`); CLIs refuse a database that is not at head | 7-C (`require_head`, used first by `scripts/catalog.py`); 7-E (`import_hymnal.py`, the rename, `test_create_all_scope.py`) |
| A rollback onto an older release still deploys after a migration (the pre-deploy step skips the upgrade when the database is `ahead`) | 7-B; `test_migrate_cli.py` |
| No production-only drift; `compare_server_default=True`; production `alembic check` clean; `alembic current` = head | 7-G; recorded in the runbook |
| `backend/migrations/README.md`: the section "Rules while Streamlit still runs" is **replaced** by "Rules after the cutover". The production stamping runbook (1) and the integrity check and repair runbook (6b) stay. | 7-G |
| The startup revision check stays a WARNING (never auto-migrates, F§2.6) | unchanged |

**Rules after the cutover** (text for `migrations/README.md`):
1. Railway's pre-deploy step (`python -m scripts.migrate`) upgrades to head while the previous release still serves. Every migration must therefore work with the **previous** release's code. The same rule is what makes a code-only rollback safe: on a database that is ahead of the release, the pre-deploy step skips the upgrade and the older code runs on the newer schema.
2. Additive changes ship in one PR.
3. A drop, rename or type change takes two PRs: first **unmap** the column (keep the `Column` on the table so `compare_metadata` stays clean, and add it to `__mapper_args__ = {"exclude_properties": [...]}` so the ORM neither selects nor inserts it; a `deferred()` column is still inserted as NULL), then drop it.
4. Adding NOT NULL needs a server default or a backfill in an earlier release.
5. Data migrations must be idempotent and log only counts.
6. Every revision has a working `downgrade()`. A documented no-op is allowed only when nothing in the models changes.
7. Take a manual backup (`workflow_dispatch`) before merging any contract or data migration.

### Compatibility with the still-running Streamlit app

| Period | Rule |
|---|---|
| 7-A → P (quiet period) | F§3.4 and §6.2 remain **in force**, so R1 revival works. Only `normalize_legacy_data` (compatible) runs. 7-B stops the API's use of `google_sub` but keeps the column, so frozen Streamlit, if revived, still maps and writes it. Tokens stay plaintext: 7-F waits for P, because an encrypted write would break a revived Streamlit for that user (its refresh would fail, and it deletes the row on 400/401, inv F10). |
| After P | There is no Streamlit to be compatible with. `contract_after_cutover` and `encrypt_gmail_tokens` may run. The §6.2 data shapes stay as they are but no longer bind. |

---

## Frontend changes

- **No routes, components, state or draft-store changes.** The draft store (`wsb:draft:{userId}:{churchId}`, F§4.6) contains no Streamlit data and is untouched.
- **Residual legacy references removed (7-B):**
  - `src/components/settings/legacy-settings-note.tsx` and its use in the settings layout: **verify only**. 6b-2 deletes them (6b scope table and acceptance 22), and the guard test below would fail on its "current app" text and its `LEGACY_APP_URL` read if it were still there. Only in that unexpected case does 7-B delete them and update the layout test so no note renders.
  - Any `NEXT_PUBLIC_LEGACY_APP_URL` read.
  - Any "current app" or "Available soon" copy left from the placeholders in slices 2–6b. If `frontend/.env.example` lists `NEXT_PUBLIC_LEGACY_APP_URL`, delete the line. The owner deletes the Vercel variable at P.
- **New guard test, `src/lib/legacy.guard.test.ts`** (unit project, node environment; the same pattern as slice 2's `dates.guard.test.ts`):
  - no file under `src/` contains `streamlit` (case-insensitive), `LEGACY_APP_URL`, `current app` or `Available soon`. The scan skips the guard file itself (matched by its own path, `src/lib/legacy.guard.test.ts`), because it holds those literals; it is the only exclusion, and it is on the backend guard's permanent allowlist for the same reason;
  - every `process.env.NEXT_PUBLIC_[A-Z0-9_]+` referenced under `src/` appears as `NAME=` in `frontend/.env.example`, and every name in that file is referenced.
- **`frontend/README.md`** (7-E): replaces the create-next-app boilerplate with:
  - what the app is;
  - `npm ci` and `.env.local` from `.env.example`;
  - `npm run dev`, `npm test` (unit and dom projects), `npm run gen:api`;
  - the Base UI notes (F§4.9) and a pointer to `AGENTS.md` for Next 16 specifics;
  - deployment (Vercel, root `frontend/`, variables scoped to Production and Preview);
  - the note that previews cannot sign in, by design.
- API client usage: unchanged.

---

## Cutover runbook and rollback

### P: point of no return (owner, one weekday session, never Saturday or Sunday)

Preconditions:
- the quiet-period conditions are met;
- 7-B to 7-E are merged and deployed (under the F§6.1 contingency: only 7-C; 7-B, 7-D and 7-E follow right after P);
- the R1 revert PR is still unneeded;
- `python backend/scripts/check_integrity.py` against production prints "OK: no integrity violations." (6b), recorded.

1. **Backup.** Run `db-backup` by hand; confirm the `backup-*.dump.age` artifact. Record the run id.
2. **Google Cloud Console, first.** This comes **before** the app is deleted, so the `liturgy.streamlit.app` subdomain is never free while our OAuth client still trusts it (risk 6). The tombstone never signs in, so it needs none of these URIs. For every OAuth client in the project, record its current redirect URIs and JavaScript origins, and which service uses it (Railway Gmail; Supabase Auth's Google provider, if it uses a client in this project).
   - **Remove:** `https://liturgy.streamlit.app/oauth2callback`, `https://liturgy.streamlit.app/`, `http://localhost:8501/oauth2callback`, `http://localhost:8501/`, and any `*.streamlit.app` JavaScript origin.
   - **Keep:** `https://worship-service-builder.vercel.app/gmail/callback`, `http://localhost:3000/gmail/callback`, and `https://<project-ref>.supabase.co/auth/v1/callback` if that client serves Supabase sign-in.
   - On the OAuth consent screen, change any home-page or privacy link that points to `streamlit.app` to the Vercel URL, and remove `streamlit.app` from the authorized domains if nothing else needs it.
   - If a client served **only** the Streamlit login, delete the whole client.
   - Google notes that OAuth client changes can take from a few minutes to a few hours to apply. Leave at least an hour between saving them and step 3; steps 5–8 may be done in that hour (they do not need the app gone).
3. **Delete the Streamlit Cloud app `liturgy`** (Streamlit Cloud → app menu → Delete). Its stored secrets go with it. Confirm `https://liturgy.streamlit.app/` no longer serves our app. (`liturgy-stg` was deleted in ops; confirm it is absent from the workspace.)
4. **Revoke Streamlit's GitHub access**, if the owner has no other Streamlit apps: GitHub → Settings → Applications → Authorized OAuth Apps and Installed GitHub Apps → "Streamlit" → Revoke or Uninstall.
5. **Rotate the Google client secret** of the Gmail client, without downtime. Google keeps several secrets per client.
   1. Add a new secret.
   2. Set Railway `GOOGLE_CLIENT_SECRET` to it. If Supabase Auth uses the same client, update Supabase → Authentication → Providers → Google in the same sitting.
   3. Verify a sign-in on the Vercel app, then a test bulletin email to yourself (this proves existing refresh tokens still refresh).
   4. Disable and then delete the old secret.
6. **Rotate the OpenAI key:** create a new key → Railway `OPENAI_API_KEY` → generate one liturgy card → revoke the old key.
7. **Rotate the Supabase database password** (Settings → Database → Reset password), then immediately:
   1. update Railway `DATABASE_URL`, which redeploys;
   2. update the GitHub secret `BACKUP_DATABASE_URL`;
   3. update any local `backend/.env` that points at production.

   Verify: `/health/ready` is 200, sign-in works, and a manual `db-backup` run is green. The uptime monitor may alert during the few minutes this takes; that is expected.
8. **ESV key:** if `ESV_API_KEY` was in the Streamlit secrets, regenerate it at api.esv.org, update Railway and load one ESV passage. **Notion:** revoke the Notion integration token (no code uses Notion after 7-D). **Gmail app password:** if a Google-account app password was ever created for the legacy SMTP sender (`email_send.py`, `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD`, inv H11; deleted in ops), revoke it in that Google account → Security → App passwords. Deleting the code and local files does not revoke it. Record "revoked" or "none existed".
9. **Tag and delete the frozen branch.**
   ```
   git fetch origin
   git tag -a streamlit-final origin/streamlit-frozen -m "Last Streamlit code (tombstone commit on top)"
   git push origin streamlit-final
   ```
   Then remove the branch protection rule and delete `streamlit-frozen` on GitHub. Record the tag's SHA.
10. **Vercel:** delete `NEXT_PUBLIC_LEGACY_APP_URL` from Production and Preview, if it exists.
11. **Supabase Auth → URL configuration:**
    - Site URL is `https://worship-service-builder.vercel.app`.
    - The redirect allow-list is exactly `https://worship-service-builder.vercel.app/auth/callback` and `http://localhost:3000/auth/callback`. `/join` and `next` need no entries (F§4.3). Remove any wildcard or preview entry: previews must not sign in (F§6.4).
12. **Uptime monitor:** create a free external HTTP monitor (for example UptimeRobot or Better Stack) on `https://<railway-domain>/health/ready`: 5-minute interval, alert by e-mail after 2 failures. It keeps Supabase Free from pausing even if GitHub disables scheduled workflows (ops risk 7). `keepalive.yml` stays as a second pinger.
13. **Local cleanup** (the owner's laptop):
    - delete `.streamlit/secrets.toml` and the root `.env`, after moving anything still needed into `backend/.env`;
    - delete, or move out of the repository into encrypted personal storage, every legacy `data/*.json` export (for example `data/email_contacts.json`, which holds contact names and addresses, and the archive and usage JSON read by the deleted `migrate_to_db.py`). `.gitignore` keeps ignoring them, but this repo is public and a file that is not there cannot be committed by mistake. Also remove `data/church.db` (the old cwd-relative default database) once nothing in it is needed;
    - remove the `streamlit` configuration from `.claude/launch.json` (untracked);
    - delete the password-manager copy of the Streamlit secrets (ops freeze step 4.1) and every superseded credential.
14. **Record** every step, with dates, in "Streamlit retirement record": removed and kept URIs, which secrets were rotated (names only), the tag SHA, the monitor's provider and URL. Then send the P message.

Optional SQL, afterwards: `delete from oauth_states where expires_at < now();` (5b already purges expired states whenever a new state is created).

### Rollback

**R1: before P (revive Streamlit).** Use this when the tester hits a blocking gap during the quiet period that cannot be fixed before they need it.
1. Mark the prepared revert PR (from 7-A) ready and merge it into `streamlit-frozen`. Streamlit Cloud redeploys in a few minutes; press the wake button if the app is asleep.
2. Smoke check: sign in, load the church, load an archived service, open Settings.
3. Send the revival message.
4. Fix the gap in the new app. Then merge the tombstone again (a new PR) and restart the quiet period.

Why this works:
- the secrets are still in Streamlit Cloud;
- the Google URIs are still registered;
- the schema is still expand-compatible (`normalize_legacy_data` only);
- the tokens are plaintext;
- `users.google_sub` still exists;
- the new app still writes the F§6.2 shapes.

Two limits of a revived app:
- Since 6b's `uq_memberships_one_owner` index, Streamlit's ownership transfer and grant-owner fail closed without changing data (6b risk 1). People management stays in the new app.
- It may fall asleep, because `keep-awake.yml` is gone from `main` after 7-B and scheduled workflows run only from the default branch. `keep-awake.yml` is **not** restored: that would break four 7-B guards (`test_ci_workflow.py`'s exact workflow list, `test_ops_workflows.py`, `test_foundation_setup.py` and `test_no_streamlit_references.py`). Instead, the wake button (step 1) is enough for a short revival, and for a revival longer than a few days the owner adds a second HTTP check on `https://liturgy.streamlit.app/` to the uptime monitor (or creates the monitor early for this), and removes it when the tombstone returns. Nothing on `main` changes.

**R2: the new stack (from 7-B on, during the quiet period too; the only path after P).** After P, Streamlit cannot come back: the app, its URIs and its credentials are gone, and the contract migrations have run. Rollback means rolling the new stack back. Railway runs the release's pre-deploy command on every deployment, including a redeploy or rollback of an older one:

| Problem | Action |
|---|---|
| App regression after a deploy (the schema is fine) | Vercel "Instant Rollback", or Railway "Redeploy" / rollback of the previous deployment. From 7-B on, that release's pre-deploy step is `scripts.migrate`, which sees the database `ahead` (for example at `normalize_legacy_data` after 7-C, or `encrypt_gmail_tokens` after 7-G), logs the WARNING and skips the upgrade; the older code runs on the newer schema because every slice-7 revision works with the previous release (rules after the cutover). The readiness gate returns 200 on `ahead` (slice 1). Roll forward with a fix; its upgrade is then a no-op. |
| Rolling back to a release **older than 7-B** (its pre-deploy step is still a plain `alembic upgrade head`, which fails with "Can't locate revision" on a database ahead of it), or wanting the schema back as well | Order matters: **first** from the laptop with the production URL, `alembic downgrade <that release's head>` (`normalize_legacy_data`'s downgrade is a documented no-op; `contract_after_cutover` re-adds an empty `google_sub`; `encrypt_gmail_tokens` needs `GMAIL_TOKEN_ENCRYPTION_KEYS` exported); **then** redeploy the older release. |
| A bad slice-7 migration | From the laptop with the production URL: `alembic downgrade <previous revision>` (`encrypt_gmail_tokens` also needs `GMAIL_TOKEN_ENCRYPTION_KEYS` exported). Then roll back the release. Every downgrade is tested in CI. |
| Data damage | Restore from the manual backup taken before 7-G, using the ops restore drill into a scratch Postgres, then `pg_restore --data-only --table=…` into production for the affected tables. The owner judges the scope. |
| Token key lost or wrong | Users reconnect Gmail (5b flow). Undecryptable rows are harmless (treated as not connected) and are overwritten on reconnect. Fix the key in Railway if the right one is still available. |
| Sunday-morning outage that can't be fixed in time | The tester adapts last week's downloaded Word file. Both copies are on their device. |

---

## Behavior changes vs Streamlit

| # | Before | After | Reason |
|---|---|---|---|
| 1 | `https://liturgy.streamlit.app/` runs the full app | Quiet period: a "moved" page with a link. After P: the app no longer exists. | Owner decision 7 |
| 2 | Two apps share one database; the F§6.2 compatibility rules bind every write | One app. The rules no longer bind (the shapes are unchanged). | Retirement |
| 3 | The frozen-app gaps accepted in F§6.2 and 5b: admins could grant owner; single-use invites were reusable; usage was recorded on Prepare; all recipients went in To; any 400/401 refresh error disconnected Gmail | These paths no longer exist. Only the new app's behavior remains. | Retirement |
| 4 | Gmail refresh tokens stored as plaintext (inv §1 I) | Encrypted at rest (`enc:v1:` + Fernet). An undecryptable token counts as "not connected". | F§6.4 |
| 5 | `users.google_sub` stored for Streamlit sign-ins | Column dropped; identity is email only | Retirement, data minimization |
| 6 | Theme text may hold `{A,"B"}` literals | Stored as `A, B` (display unchanged; slice 3 already normalized it). A literal whose element contains `,` or `;` stays as it is, because joining it would split one theme into two. | inv H1 |
| 7 | A fresh database has an empty `hymn_catalog`, so new churches get an empty hymnal | `scripts.catalog seed` fills it from the committed file; startup warns while it is empty. Production unchanged. | inv §6 "Data" |
| 8 | `import_hymnal.py` ran `create_all` on any database | It refuses to run unless the schema is at the Alembic head | Finishing Alembic |
| 9 | With `DATABASE_URL` unset, the database was the cwd-relative `data/church.db` (the docs said `data/app.db`) | The absolute `<repo>/data/app.db`, with a warning | inv §3 engine row |
| 10 | Production could start without Gmail being fully usable | Production refuses to start when Gmail is configured without a valid token key | Safer failure: the previous release keeps serving |
| 11 | The Streamlit login, the Gmail root redirect URIs and the old credentials were valid | Removed and rotated | Security hygiene |
| 12 | Soft-deleted churches kept forever, with no documented procedure | Still kept (no automatic purge); the runbook documents restore and purge on request | C13 decision |
| 13 | `keep-awake.yml` pinged Streamlit every 6 h | Deleted. An external uptime monitor pings `/health/ready`, plus the daily `keepalive.yml`. | Retirement; ops risk 7 |
| 14 | Deleting a service, or moving it to another date, never changed hymn usage (5a, during coexistence) | After 7-G, deleting or re-dating a service whose date is today or later rebuilds that date's usage from the services still archived on it, so an abandoned plan's hymns stop counting as "recently used". Past dates keep their usage. | 5a open question 1; owner decisions 3 and 9; open question 3 |
| 15 | Notion-imported `hymn_usage.date_iso` values may be full datetimes | Stored as `YYYY-MM-DD` (duplicates merged), so saving a service on that date replaces them like any other row. The 12-week exclusion is unchanged (slice 3 already read the first 10 characters). | slice 3 hand-off |

---

## Testing

### Backend (pytest, from the repo root)

**New or rewritten tests**

- `test_no_streamlit_references.py`, `test_no_legacy_copy.py`, `test_entry_points_import.py`, `test_env_access.py`, `test_env_example.py`, `test_create_all_scope.py` (see Guards).
- Each guard also has a **negative** unit case, in that guard's own test file: a temporary file set containing `import streamlit`, a string literal such as `HINT = "An admin can remove it and add it again in the current app's Settings."`, a module-level `load_dotenv()` or an `os.getenv` in a non-allowlisted module makes the checker report `file:line`; for `test_no_legacy_copy.py`, the same words in a `#` comment are **not** reported. The checker function is tested directly, not by editing repo files. `test_no_streamlit_references.py` also checks that each allowlist pattern and `PENDING` entry matches at least one tracked file, so the allowlist cannot silently cover a deleted path.
- `test_foundation_setup.py`, `test_ci_workflow.py`, `test_ops_workflows.py` (see Guards).
- `test_services_storage_shape.py` (7-B, renamed from 5a's `test_services_streamlit_compat.py`): a saved row with an empty Opening slot stores exactly 3 entries in slot order, with `title: ""` for the empty slot.
- `test_migrate_cli.py` (7-B, `scripts/migrate.py`):
  - an empty SQLite file → upgraded to head, exit 0;
  - at head → no DDL is emitted (statement listener), exit 0;
  - `alembic_version` holding a revision unknown to the scripts (`ahead`) → exit 0, the exact WARNING with both revision ids, and no DDL;
  - a failing upgrade (a monkeypatched `command.upgrade` that raises) → non-zero exit.
- `test_schema_check.py` (extends slice 1's, **7-C**): `require_head` returns at head; on an empty database it raises `SystemExit(2)` with `Database schema is at an empty database, expected {head}. …`; at an older revision and at an unknown (`ahead`) revision it raises with that revision id in the message.
- `test_docs.py` (rewritten, 7-E):
  - `README.md` contains `alembic upgrade head`, `python -m scripts.catalog seed`, `/gmail/callback`, `/join?code=`, `pooler.supabase.com`, `/health/ready`, `docs/ops-runbook.md`, and the sentence explaining that Vercel previews can't sign in;
  - it contains neither `[auth]` nor `oauth2callback`;
  - `docs/manual-verification.md` contains `375`, `invite`, `Gmail`, `Word` and `Release smoke test`.
- `test_catalog_cli.py` (7-C):
  - seed a 6-row fixture CSV (two hymnals, one NULL number, one quoted comma, one non-ASCII title) into an empty `tmp_db` → `inserted=6`;
  - `export` reproduces the fixture byte for byte;
  - a second `seed` → `inserted=0 unchanged=6`;
  - changing one theme in the file → `updated=1`;
  - `verify` → 0 when equal, 1 after a database edit (reports `changed=1`);
  - `export` exits 2 with the duplicate message when two rows share a key (including two titles that differ only in case);
  - `export` exits 2 with the no-title message when a row's `title` is NULL or blank;
  - a title that differs only in case from the database's under the same key → `seed` reports `updated=1` and stores the file's exact text; `verify` then exits 0;
  - `seed` on a file with a blank title or a duplicate key exits 2 naming the line and writes nothing;
  - `seed --dry-run` writes nothing;
  - *amendment 2026-09-26*, hymn facts: the fixture has `text_year`/`hymnal_count` on some rows and empty cells on others, and `export` reproduces them; an empty cell over a stored `1826` leaves it (`unchanged`, and `verify` exits 0); a stored NULL under a file value of `1826` → `updated=1`; a stored `1900` under a file value of `1826` → `verify` reports `changed=1`, then `seed` reports `updated=1` and stores 1826;
  - after `seed`, `usecases.onboarding.create_church` seeds exactly as many hymns as file rows (the tie to slice 1);
  - each command on a database behind head exits 2 with the `require_head` message (`require_head` ships in the same PR).
- `test_catalog_seed_file.py` (7-D, over the committed file):
  - it exists under `backend/`, is UTF-8 without BOM, and has the exact header;
  - every row has a hymnal and a title; `number`, `text_year` and `hymnal_count` are integers or empty;
  - there are no duplicate keys, and the rows are in the sort order (so re-export yields no diff);
  - there is at least one row (the PR records the real count).
- `test_migration_normalize_legacy_data.py`:
  - themes: upgrade on SQLite from the previous head with seeded `hymns` and `hymn_catalog` rows: `{Advent,"Hope and Peace"}` → `Advent, Hope and Peace`; `{}` → NULL; `{"a\"b",NULL}` → `a"b`; `{"Faith; Hope",Love}` and `{"Faith, Hope",Love}` unchanged and counted in `skipped_ambiguous`; plain text and NULL unchanged; both tables handled;
  - running the normalization function twice changes nothing;
  - **display round trip:** for every slice-3 `parse_themes` array-literal fixture and every example above that step 1 changes, `parse_themes(_normalize(x)) == parse_themes(x)`; and for every changed value, `", ".join(parse_themes(x)) == _normalize(x)`;
  - usage dates, over the stored shapes slice 3 lists: `2026-08-02T10:00:00.000-05:00` → `2026-08-02`; a datetime row whose `(church, day, number, title)` already exists as a `YYYY-MM-DD` row is deleted (`merged=1`); two datetime rows for the same day and hymn end as one row; a NULL-number row matches a NULL-number row; `""`, NULL and `2026-08-02` untouched; `2026-8-2T10:00` and `not a dateXXXX` left and counted in `unparseable`; a second run changes nothing; afterwards `rebuild_usage_for_date(church, "2026-08-02")` replaces the formerly datetime-shaped rows;
  - downgrade leaves the data as upgraded (documented no-op).
- `test_token_crypto.py`:
  - round trip; the prefix is present;
  - `decrypt` without the prefix → `TokenDecryptError`; a wrong key → `TokenDecryptError`;
  - `MultiFernet`: with `"new,old"`, an old ciphertext decrypts, and `rotate` produces one that decrypts under `"new"` alone;
  - `from_setting("")` → None; a malformed second entry → `TokenKeyError` whose message contains `entry 2` and not the key text.
- `test_google_oauth_tokens.py` (extends 5b's token tests):
  - `save_user_token` stores `enc:v1:…` (raw row inspected), and `get_connection` returns the plaintext;
  - **7-F mode:** a raw plaintext row is returned with one WARNING;
  - **7-G mode:** a plaintext row or an undecryptable row → None and an ERROR that carries the user id;
  - unconditional `delete_connection` returns the decrypted token, or None for an undecryptable row (still deleted);
  - **conditional delete with encryption on:** `delete_connection(u, only_if_token=<plaintext from get_connection>)` removes the encrypted row and returns the plaintext; with a different plaintext it removes nothing and returns None; after `save_user_token` re-saves the **same** plaintext (a new ciphertext) it still removes the row; in 7-F mode a legacy plaintext row matches too;
  - **race:** read the connection, then `save_user_token` a new token (a reconnect), then `delete_connection(only_if_token=<old plaintext>)` → None, and the row still holds the new token;
  - `caplog` never contains the token, the ciphertext or the key.
- API tests (extend 5b):
  - with a cipher: `GET /gmail-connection` for an undecryptable row → `{configured: true, connected: false}`;
  - `POST /bulletin-emails` → 409 `gmail_not_connected` with the exact message;
  - with a cipher and an encrypted row, the token refresh stubbed (respx) to return `invalid_grant` → 5b's `gmail_send_failed` with `details.disconnected: true`, and the `gmail_tokens` row is gone;
  - the same, but the stub saves a new token for the user before answering `invalid_grant` (a reconnect during the send) → 5b's "Your Gmail connection changed while sending. Nothing was sent — try again." with `disconnected: false`, and the new row is kept;
  - with no cipher (development): `configured: false`, and `POST /gmail-connection/auth-url` → 503 `gmail_not_configured`.
- Startup tests (7-F):
  - production + Google configured + no key → startup raises the exact message;
  - an invalid entry → the exact message with its index;
  - development + no key → the WARNING, and the app starts.
- Empty-catalog warning (7-C): an empty table → the WARNING is logged; a seeded table → no warning; a failing query → logged, and startup continues.
- `test_migration_encrypt_gmail_tokens.py` (SQLite; `monkeypatch` sets the key):
  - plaintext rows → encrypted, and decryptable with `TokenCipher`;
  - rows that already carry the prefix are untouched;
  - no plaintext rows and the variable **unset** (`monkeypatch.delenv`) → no-op, no `KeyError`; the same for downgrade with no prefixed rows;
  - plaintext rows and no key → raises the exact message; prefixed rows, no key, downgrade → raises the downgrade message;
  - downgrade decrypts back to the original values.
- `test_migration_contract_after_cutover.py`:
  - after upgrade, `users` has no `google_sub` (inspector);
  - downgrade on **SQLite** (batch mode) re-adds a nullable column with the unique constraint `uq_users_google_sub`, and upgrade drops it again;
  - SQLite batch mode handles the unnamed unique constraint on the way up.
- The existing `test_migrations.py` (up, compare, down, up, and every revision defines `downgrade`) runs over `normalize_legacy_data`, `contract_after_cutover` and `encrypt_gmail_tokens` with `compare_server_default=True`, with `GMAIL_TOKEN_ENCRYPTION_KEYS` unset, as in CI.
- `test_google_sub_unreferenced.py` (7-B; deleted in 7-G with the column):
  - `"google_sub" not in inspect(User).attrs` and `"google_sub" in User.__table__.c`;
  - an ORM `session.add(User(email=…))` + flush emits an `INSERT` without `google_sub` (the case a `deferred()` mapping would get wrong);
  - the `forbid_google_sub_sql` checker flags a DML string that mentions `google_sub` and ignores a `CREATE TABLE` and an `INSERT INTO _alembic_tmp_users … SELECT` that do.

  Together with the autouse fixture, which runs across the **whole** backend suite, this proves 7-G's drop is safe for the release that is still serving, for every flow the tests exercise, not a hand-picked list.
- Usage rebuild on delete (7-G; extends 5a's archive tests, with an injected "today" and church timezone):
  - delete the only service on a future date → that date's usage rows are gone; delete one of two services on a future date → usage equals the remaining service's hymns;
  - delete a service dated yesterday → usage unchanged; a NULL or unparseable date → unchanged;
  - "today" is computed in the church's timezone: at 20:00 on the 1st in `America/Los_Angeles` (already the 2nd in UTC), a service dated the 1st counts as today and is rebuilt; an invalid stored zone falls back to UTC;
  - a date-changing PUT from a future date → the old date is rebuilt, the new date rebuilt as before; from a past date → the old date unchanged;
  - the delete and the rebuild are one transaction: a rebuild that raises leaves the service and the usage as they were.
- `test_engine_default.py` (7-E):
  - with `DATABASE_URL` unset or blank, `_database_url()` is `sqlite:///<absolute path ending in data/app.db>`, the WARNING is logged once, and the directory exists;
  - a set URL is returned stripped and unchanged;
  - production + unset → the ops guard still refuses to start.
- `test_import_hymnal_cli.py` (extends 6a): `main([...])` on a database at base exits 2 with the `require_head` message; at head it imports.
- `test_rotate_gmail_token_key.py`: with `"new,old"`, rows encrypted under old → rotated (decrypt under `"new"` alone); an undecryptable row → exit 1 and left unchanged; `--dry-run` writes nothing.

**Postgres (`@pytest.mark.postgres`, CI job from slice 1)**
- After `upgrade head`, `information_schema.columns.column_default` is NULL for `hymns.hymnal` and `hymn_catalog.hymnal`, even when the test first creates the tables with `DEFAULT 'GG2013'` to simulate production (stamp the previous head, then upgrade).
- `alembic check` is clean with `compare_server_default=True`.
- `encrypt_gmail_tokens` over 50 rows inside one transaction; a forced failure on row 30 leaves all 50 plaintext.

**Cross-church isolation and role checks.** No church-scoped or role-guarded route is added or changed, so there is no new `assert_church_isolated` case. These must stay green, unchanged:
- every existing isolation and role test from slices 1–6b;
- `test_route_guards.py` with no allowlist change;
- 5b's user-scoping test (user B can never read or delete user A's Gmail connection), now run with encryption on.

**Deleted tests** (and where their intent lives):
- the whole `streamlit_tests/` folder (see the port ledger);
- `test_auth.py` (moved to the `ensure_user` tests, ops);
- `test_migrate_hymns.py`, `test_migrate_archive.py` (catalog idempotency → `test_catalog_cli.py`; usage dedupe → 5a);
- `test_hymn_utils.py`, if `hymn_utils.py` is dead;
- the dead-code sweep's tests, listed in the sweep table.

### Port ledger (entry gate for 7-B)

The authoritative ledger is 6b's `backend/tests/test_streamlit_port_ledger.py`. It maps every Streamlit test node id to an existing backend test function, a frontend test title, or `DROPPED: <reason>`, and it checks that each target exists.

- **7-0 gate:** the ledger passes on `main`.
- **7-B:** copies the ledger's final mapping into the PR description, which is the permanent record once the files are gone. It then deletes the ledger together with `streamlit_tests/`.

Summary of where the intent lives (from 6b's planned mapping):

| Streamlit tests | Replacement (slice) |
|---|---|
| `test_app_helpers.py` | `/join` code capture and keep-prior tests (1); OAuth cleanup is DROPPED, covered by 5b's callback test; hymn display and blank-title handling (3); the `?church=` param and the title-keyed map are DROPPED |
| `test_onboarding.py` | Ported and deleted in 1b |
| `test_selectbox_safety.py` | The stale-pick "Not in your hymnal. Choose a replacement." test (3) and per-church drafts (2); `coerce_selectbox_value` is DROPPED |
| `test_settings_members_invites.py` | Ported and deleted in 6b |
| `test_settings_profile_contacts.py`, `test_settings_prompts_translation.py` | The 6a table plus `clean_prompt_overrides` (4) |
| `test_streamlit_tenancy.py` | Forged `X-Church-Id` → 403 (0 and 1); zero churches → `/welcome` (1); the church-switch reset tests: keyed remount (1), per-church draft (2), church-scoped custom elements (4) |

### Frontend (Vitest)

- `src/lib/legacy.guard.test.ts` (7-B), including negative cases run against in-memory strings: the checker flags `streamlit`, `LEGACY_APP_URL`, `current app`, and an `.env.example` mismatch; the file list it scans excludes exactly one path, its own.
- The whole existing unit and dom suites stay green. No new components.

### Manual checks (one time, recorded in the runbook's retirement record)

- [ ] 7-A: at 375 px and on desktop, `https://liturgy.streamlit.app/` shows the tombstone, and the button opens the new app (in a new tab). The revert PR is a draft with green CI.
- [ ] 7-B deployed: the deploy log shows `python -m scripts.migrate` ran as the pre-deploy step (at head, so nothing to upgrade).
- [ ] Quiet period: one Sunday service planned end to end in the new app (dates recorded). No open gap report.
- [ ] Quiet period, decision 9 check (5a): `select count(*) from services where saved_at > '<7-A date>' and (custom_elements is null or hymnal is null);` → 0. After the tombstone only the new app saves services, and it always writes both (`[]` for no custom elements; the effective hymnal for a null one). A non-zero count is investigated before P; the only accepted case is a church with no hymns at all (null effective hymnal), confirmed by hand.
- [ ] 7-C deployed: `select count(*) from hymns where theme like '{%}'` and the same for `hymn_catalog` equal the `skipped_ambiguous` counts `normalize_legacy_data` logged (expected 0; any rows are listed in the 7-C PR). `select count(*) from hymn_usage where length(date_iso) > 10` equals the logged `unparseable` count (expected 0). The deploy log shows the `normalized`, `merged` and `unparseable` counts, and they are consistent with slice 3's recorded shape check (new rows are always `YYYY-MM-DD`, so the datetime-shaped count cannot have grown).
- [ ] 7-D: `python -m scripts.catalog verify` against production → exit 0 (output in the PR). Local fresh setup: `alembic upgrade head && python -m scripts.catalog seed`, then create a church in the local app → its hymn count equals the file's row count.
- [ ] P: every runbook step recorded. After the rotations, on the production Vercel URL at 375 px:
  - sign in;
  - generate one liturgy card (OpenAI);
  - load an ESV passage, if ESV is configured;
  - send a test bulletin to yourself (Gmail refresh);
  - `/health/ready` 200;
  - a manual `db-backup` run green;
  - the uptime monitor green;
  - `https://liturgy.streamlit.app/` no longer serves our app;
  - the Google client lists no `streamlit.app` or `:8501` URI.
- [ ] 7-F deployed: connect Gmail again, or keep the existing connection → a test bulletin sends. The raw row starts with `enc:v1:` after a reconnect.
- [ ] 7-G deployed:
  - `select count(*) from gmail_tokens where refresh_token not like 'enc:v1:%'` → 0;
  - `select column_name from information_schema.columns where table_name='users' and column_name='google_sub'` → no rows;
  - `hymnal` `column_default` is NULL in both tables;
  - from the laptop: `alembic current` = head and `alembic check` is clean;
  - a test bulletin sends; sign-in works;
  - save a throwaway service with one hymn on a future date that has no other saved service, delete it, and open the hymns step for the Sunday before that date: that hymn is not marked "recently used" (C15).
- [ ] Final regression: the new `docs/manual-verification.md` "Release smoke test" passes at 375 px and on desktop.

`docs/manual-verification.md` is **rewritten** in 7-E (F§5.5). It drops the Streamlit sections 1–3 and the per-slice history (which stays in git) and becomes:
1. **Release smoke test** (about 10 minutes, after any deploy touching sign-in, the builder or email):
   - sign in at 375 px;
   - switch church;
   - build one service through the four steps;
   - download both Word copies;
   - email the bulletin to yourself;
   - save it, then reload it from Services.
2. **Full regression by area:**
   - sign-in and onboarding (single-use link, reusable link, create church, join from the switcher);
   - builder steps 1–4 (any-date readings, manual fallback, AI hymn picks and chips, exclusion, liturgy cards with and without AI);
   - archive (paging, load, edit, delete with confirmation);
   - Gmail connect and disconnect;
   - settings (church, hymns and hymnals, liturgy prompts, contacts, people, danger zone) per role (owner, admin, member);
   - error states (offline, a 500 showing "Ref", 429);
   - layout at 375 px and on desktop.
3. **Operations checks:**
   - `/health/ready`;
   - the latest backup is at most 48 h old;
   - the quarterly restore drill;
   - the uptime monitor;
   - `alembic current` equals head.

---

## Acceptance criteria

1. **Entry gate.** The runbook records: 6a and 6b deployed; the parity-gate and settings sign-off dates; a backup from the last 24 h; the branch Streamlit Cloud deploys from (and, if it was `main`, that the contingency plan was followed). 6b's `test_streamlit_port_ledger.py` passed on `main` before 7-B, and its final mapping is copied into the 7-B description. *(review + CI)*
2. **Tombstone and revival path.** During the quiet period, `https://liturgy.streamlit.app/` shows exactly the UX §1 copy with a working link, and the revert PR is a draft with green CI. The day-0 message was sent. *(deployed)*
3. **Streamlit code gone.** `app.py`, `streamlit_views/`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`, `streamlit_tests/`, the root `requirements.txt`, the root `.env.example` and `keep-awake.yml` do not exist. `test_no_streamlit_references.py` passes with `PENDING` **empty**. Its only allowlist entries are `.gitignore`, the test itself, `backend/tests/test_foundation_setup.py`, `frontend/src/lib/legacy.guard.test.ts`, `docs/ops-runbook.md`, `docs/superpowers/**` and `backend/migrations/versions/**`; the frontend guard excludes only itself. 5a's `test_services_streamlit_compat.py` survives as `test_services_storage_shape.py`. *(CI)*
4. **Legacy code gone.** A grep under `backend/` (tests excluded) finds no `migrate_to_db`, `notion_hymns`, `NotionHymnsDB`, `fill_from_hymnary`, `should_handle_gmail_callback`, `resolve_hymnary_audio_url`, `upsert_from_claims`, `list_saved_services`, `record_usage(` or `get_contacts_for_display`. `backend/requirements.txt` has none of `notion-client`, `playwright`, `beautifulsoup4`, `lxml`, `requests` or `streamlit`. *(CI)*
5. **Tests and CI.** `pytest.ini` has `testpaths = backend/tests`. `requirements-dev.txt` starts with `-r backend/requirements.txt`. The workflows folder holds exactly `backup.yml`, `ci.yml` and `keepalive.yml`. `backend/railway.toml`'s pre-deploy command is `python -m scripts.migrate` and its `healthcheckPath` is `"/health/ready"`, and `test_migrate_cli.py` passes (an `ahead` database is skipped with the WARNING). All CI jobs (`backend`, `backend-postgres`, `frontend`) are green. *(CI)*
6. **Configuration discipline.** `test_env_access.py`, `test_env_example.py` and `test_create_all_scope.py` pass. With `DATABASE_URL` unset or blank in development (as `backend/.env.example` now ships it), the database is `<repo>/data/app.db` regardless of the working directory. `init_db` appears nowhere under `backend/` (`test_engine.py` and the startup tests updated). `.gitignore` still ignores `data/*.json`, `data/*.db` and `.streamlit/secrets.toml`. `import_hymnal.py` and `scripts/catalog.py` exit 2 with the `require_head` message on a database behind head. *(test)*
7. **Catalog seed.** `backend/seed/catalog/hymn_catalog.csv` and its README are committed; `test_catalog_seed_file.py` and `test_catalog_cli.py` pass. `verify` against production exited 0 (recorded in 7-D). On a fresh SQLite database, `alembic upgrade head && python -m scripts.catalog seed` followed by creating a church seeds as many hymns as the file has rows. *(test + deployed)*
8. **Themes and usage dates.** After 7-C, the production rows with `theme LIKE '{%}'` in `hymns` and `hymn_catalog` are exactly the ambiguous ones `normalize_legacy_data` logged (expected none), and the round-trip test `parse_themes(_normalize(x)) == parse_themes(x)` passes, so hymn themes display exactly as before. `hymn_usage` has no `date_iso` longer than 10 characters except the logged unparseable rows (expected none). *(test + deployed)*
9. **Point of no return done.** The runbook records every P step. The Streamlit Cloud app is deleted. No Google OAuth client lists a `streamlit.app` or `localhost:8501` URI or origin. The Google client secret, OpenAI key and database password are rotated, and the old ones are disabled or revoked. `BACKUP_DATABASE_URL` is updated and a manual backup is green. The tag `streamlit-final` exists and `streamlit-frozen` does not. The Vercel legacy variable is gone. The Supabase Auth Site URL and allow-list are exactly as specified. The uptime monitor is active. The P message was sent. *(deployed)*
10. **Post-rotation health.** After P, on the production URL: sign-in, one AI liturgy card, a test bulletin email and `/health/ready` all succeed. *(deployed)*
11. **Token encryption.** After 7-G, `select count(*) from gmail_tokens where refresh_token not like 'enc:v1:%'` returns 0 in production, and a test bulletin sends. `token_crypto`, the token-function (including the encrypted conditional delete and its reconnect race), the `invalid_grant` API tests, `test_migration_encrypt_gmail_tokens.py`, startup and rotation-CLI tests pass. No log line contains a token, a ciphertext or a key (caplog tests). *(test + deployed)*
12. **Contract migration.** In production, `users.google_sub` does not exist and `hymnal` has no column default in either table. `alembic current` equals head. `alembic check` is clean with `compare_server_default=True` against production and CI Postgres. `test_google_sub_unreferenced.py` and the suite-wide `forbid_google_sub_sql` fixture passed on the release serving when 7-G merged, with `User.google_sub` unmapped (`exclude_properties`). *(test + deployed)*
13. **Migration hygiene.** `test_migrations.py` (up, compare, down, up) passes over every revision including `normalize_legacy_data`, `contract_after_cutover` and `encrypt_gmail_tokens` on SQLite and with no `GMAIL_TOKEN_ENCRYPTION_KEYS`; the `contract_after_cutover` downgrade runs in batch mode. `backend/migrations/README.md` contains "Rules after the cutover" and no Streamlit section. *(CI)*
14. **No API change.** `test_openapi_contract.py` passes without regenerating the snapshot, and `test_route_guards.py` passes with no allowlist change. *(CI)*
15. **No legacy copy, frontend or backend.** `src/lib/legacy.guard.test.ts` and `backend/tests/test_no_legacy_copy.py` pass: no file under `frontend/src/` and no backend string literal says "current app". In particular `usecases/email.py`'s `MALFORMED_CONTACT_HINT` reads "An admin can fix it in Settings → Contacts.", asserted by a test, and `legacy-settings-note.tsx` does not exist (6b). The production build succeeds with the Vercel legacy variable removed, and the release smoke test passes at 375 px and on desktop. *(CI + deployed)*
16. **Docs.** `README.md`, `frontend/README.md` and `docs/manual-verification.md` are rewritten as specified, and `test_docs.py` passes. `docs/ops-runbook.md` has a completed "Streamlit retirement record", a "Gmail token key" section (custody, generation, rotation CLI, loss procedure), a "Deleted churches" section (restore and purge on request, honoured only for the church's recorded owner, with the requester recorded), a "Rollback" section (the R2 table, including the order for rolling back across a migration), and Streamlit Cloud removed from "Environments". *(CI + review)*
17. **Foundations criterion 20 met.** No `streamlit` anywhere in the repo outside the allowlist in criterion 3, and no Streamlit deployment. Every inventory §6 checkbox is either checked or marked "No" with its reason in the coverage ledger. *(CI + deployed)*
18. **Usage on delete (C15).** After 7-G, deleting or re-dating a service dated today or later (church timezone) rebuilds that date's usage; a past date's usage is unchanged. The usage-rebuild tests pass, and the 7-G manual check is recorded. *(test + deployed)*

---

## Risks and open questions

**Open questions (owner)**

1. **Hymnary.org-derived catalog data in a public repo.** The export commits about 700 rows to the public repo: hymn numbers and titles plus the scripture references, themes and links gathered from Hymnary.org. Titles and numbers are facts, but the compiled references are Hymnary.org's work.
   - Default, if unanswered: commit the file with the attribution README. The app already credits Hymnary.org.
   - Alternative: commit `hymn_catalog.csv.age`, encrypted to the backup recipients (`.github/backup/age-recipients.txt`). `seed` then decrypts it with a key file given by `--identity`, and CI uses only the small fixture. This changes 7-D and `test_catalog_seed_file.py`, but no other part of this design.
2. **Backup retention after the cutover** (deferred from ops open question 3). GitHub artifacts last 30 days (90 at most).
   - Default, if unanswered: keep 30 days.
   - Anything longer means copying the encrypted artifacts to storage the owner controls, which would be a separate small ops change.

3. **Hymn usage when a service is deleted or re-dated** (5a open question 1, handed to this slice). Owner decision 9 says usage is recorded on save, replacing that date's entries; it does not cover deletes.
   - Default, if unanswered (C15, 7-G): rebuild the vacated date's usage only when that date is today or later in the church's timezone. A deleted or moved future service was never held, so its hymns should stop counting for the 12-week exclusion (decision 3). A past service's hymns were sung; deleting its archive entry keeps them counted, which also protects imported history and last Sunday (5a's two remaining concerns). 5a's coexistence concern is gone after P, because nothing else writes usage.
   - Alternatives: rebuild for every date (simplest, one line, but deleting last week's service would let its hymns be suggested again at once); or keep 5a's behavior (no rebuild), accepting that an abandoned plan's hymns stay excluded near that date until another save there.

**Risks**

4. **Rotating the Google client secret could break sign-in** if Supabase Auth uses the same client and is not updated. Mitigation: P step 2 records which service uses each client, and step 5 adds the new secret before disabling the old one, with a sign-in check in between.
5. **Refresh tokens after the secret rotation.** Google refresh tokens are bound to the client, not the secret, so existing Gmail connections are expected to keep working. P step 5 verifies this with a test email. If they fail, users reconnect once (the P message already says so).
6. **Someone else can claim the subdomain.** After deletion, anyone can create an app at `liturgy.streamlit.app`. Mitigations:
   - both messages tell the tester to drop the bookmark;
   - P step 2 removes the Google URIs and origins **before** step 3 deletes the app, so there is no moment when the subdomain is free and still a registered redirect URI or JavaScript origin of our OAuth client; a squatter therefore cannot run consent under our app's name.

   If the owner prefers to hold the name, a secretless tombstone app could stay deployed. Criterion 17 would then list it as the one exception. Not recommended; decision 7 says retire.
7. **`compare_server_default` false positives** on rendering differences. Mitigation: the normalizing comparator in `env.py` (Data and migrations). A real difference is fixed in `contract_after_cutover`.
8. **SQLite batch mode and the unnamed unique constraint on `google_sub`.** Both directions of `contract_after_cutover` use `batch_alter_table` (SQLite cannot `ALTER` constraints). Covered by `test_migration_contract_after_cutover.py`. If batch mode fails, the migration passes `reflect_args` or a `table_args` override so the constraint can be dropped by a known name.
9. **GitHub disables scheduled workflows after 60 days without repository activity**, and this also stops `backup.yml`. The uptime monitor covers keep-alive only. Mitigations:
   - re-enable the workflows when GitHub's warning e-mail arrives;
   - the quarterly restore drill and the manual-verification operations check confirm the newest backup is at most 48 h old.
10. **Losing the token key** makes every stored Gmail token unreadable. The impact is limited to one reconnect per user. Mitigation: the key is kept in the password manager with an offline copy, as for the backup `age` key.
11. **The dead-code sweep could delete something a later feature wants.** Mitigation: the grep rule plus vulture triage in the PR; everything stays in git history and in the tag `streamlit-final`.
