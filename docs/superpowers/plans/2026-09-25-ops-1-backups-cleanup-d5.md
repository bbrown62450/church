# Ops-1: Streamlit D5 Fix, Encrypted Backups and Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR ops-1 of the ops slice: fix the Streamlit hymn-loss bug (inv D5), make the daily database backup encrypted and correct, delete six dead modules, fix configuration drift (`backend/.env.example`, `shadcn`), and start `docs/ops-runbook.md`. Then hand the owner the manual steps that gate the next PR.

**Architecture:** The D5 fix is two pure helpers in the root `ui_helpers.py` that `app.py` calls. It changes nothing under `backend/`. It goes live on the production Streamlit app `liturgy-stg` (https://liturgy-stg.streamlit.app, used by the owner and the tester) as soon as ops-1 merges, provided `liturgy-stg` deploys from `main`; Task 0 checks that before any code is written. The backup is a rewritten GitHub Actions workflow. It runs in the GitHub Environment `backup` (the only holder of the secret; `main` only), splits the URL into libpq `PG*` variables with a small stdlib Python helper that first masks each part in the log, checks the server's Postgres major, and pipes `pg_dump` through `age` to public keys committed in the repo, so no plaintext dump ever exists on the runner. The parsed workflow, the URL helper, the recipients file and the runbook are all guarded by pytest tests in a new `backend/tests/test_ops_workflows.py`.

**Tech Stack:** Python 3.11, pytest, PyYAML (test only), Streamlit (root app, unchanged framework), bash, Python 3 standard library (`pg_env.py`, on the runner's system `python3`), GitHub Actions (`ubuntu-24.04`, `actions/checkout` v4.4.0 and `actions/upload-artifact` v4.6.2 pinned to commit SHAs, GitHub Environment `backup`), PostgreSQL client from the PGDG apt repo, `age`, npm (Next.js frontend, dependency move only).

**Spec:** `docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md` ("the ops spec"). Foundations: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` ("F"). Inventory: `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md` ("inv").

## Global Constraints

- Run every command from the repo root with `.venv/bin/python` (Python 3.11). The system `python3` is 3.9 and has no deps. If `.venv` is missing: `/Users/beaubrown/.local/bin/python3.11 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.
- Backend test command: `.venv/bin/python -m pytest -q` (pytest.ini: `pythonpath = . backend`, `testpaths = backend/tests streamlit_tests`). Baseline: `206 passed`.
- Frontend checks: `(cd frontend && npm ci && npm run lint && npm run typecheck && npm test && npm run build)`, with the CI placeholder `NEXT_PUBLIC_*` values for the build (Task 4, Step 5).
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Commits follow TDD: test first.
- Nothing under `backend/` may import `streamlit`. The D5 fix touches only the root Streamlit files `app.py` and `ui_helpers.py`. It imports the existing `hymn_usage.is_hymn_recently_used` and changes nothing under `backend/`.
- No schema changes and no Alembic (slice 1).
- The backup secret is named `BACKUP_DATABASE_URL`, never `DATABASE_URL`. It is an **environment secret** of the GitHub Environment `backup`, whose deployment-branch rule admits only `main`, never a repository secret. The owner creates the environment and adds the secret **only after ops-1 has merged** (the F §7.2 gate; Task 11).
- `backup.yml` runs daily at cron `"37 8 * * *"`, on `ubuntu-24.04`, with `timeout-minutes: 20` and `PG_MAJOR: "17"` (the server is 17.6, recorded 2026-09-25). It uploads artifact `db-backup` with files `backup-<UTC timestamp>.dump.age`, `retention-days: 30`.
- `PG_MAJOR` in `backup.yml` must equal the runbook line `- Postgres server major: <N>` (exactly one such line in `docs/ops-runbook.md`).
- An age recipient line matches `^age1[02-9ac-hj-np-z]{58}$`. The private key never goes to GitHub, Railway, the repo or chat.
- Exact copy (ops spec, "Exact server messages"): `::error::BACKUP_DATABASE_URL secret is not set` · `::error::.github/backup/age-recipients.txt has no age recipient` · `::error::Postgres server major is {N} but PG_MAJOR is {M}; update PG_MAJOR in backup.yml`.
- The agent never sees or types a secret: database URLs, the anon key, access tokens and age private keys are handled only in OWNER steps. An age **public** key is not a secret.
- Opening a PR, merging, and messaging the tester are outward-facing. Get the owner's explicit yes first.
- **Streamlit apps (owner correction, 2026-09-25; reverses the ops spec).** `liturgy-stg`, https://liturgy-stg.streamlit.app, is the production Streamlit app: the owner and the tester use it, and it is the app to keep, freeze on `streamlit-frozen` and keep awake. `liturgy`, https://liturgy.streamlit.app, is unused, and its Google sign-in already fails with `StreamlitAuthError` (its secrets config); the Freeze step deletes it and its redirect URIs. Every Streamlit check, log, secret and tester message in this plan uses `liturgy-stg`.
- **Step 0 is done (2026-09-25), except the `age` key pair.** The owner's results are pre-filled in the runbook (Task 6); never ask the owner to redo them. Data API already off (REST and GraphQL with the anon key return HTTP 503 `PGRST002`, no rows), so no incident; every `public` table owned by `postgres`; `current_user` `postgres` with `rolbypassrls = true`; RLS enabled and the REVOKE / ALTER DEFAULT PRIVILEGES statements run; the Vercel app and `liturgy-stg` still load the owner's church afterwards; `server_version` 17.6; Railway closes a request after 5 min with no data, up to 15 min while data flows. The `age` key pair is generated in Task 0, Step 3.
- **Pool budget (owner correction, 2026-09-25).** The Supabase session pooler (Supavisor, Nano compute) has Pool Size 15, so the ops spec's trigger 2 × (5 + 5) + 2 = 22 > 15 fires. The values are `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3` (2 × (3 + 3) + 2 = 14 ≤ 15): in `backend/.env.example` (Task 3), on Railway and in the `liturgy-stg` Streamlit Secrets (Task 9, Step 1), and as the code defaults that ops-2 must use.
- **Not in ops-1** (other PRs and slices; do not touch): `keepalive.yml`, `backend/keepalive.py`, `backend/tests/test_keepalive.py`, `keep-awake.yml`, the `app.py` FROZEN header, `docs/manual-verification.md` "Ops slice" section, the `errors.ts` check in `test_foundation_setup.py` (all ops-3); `db/upsert.py`, `ensure_user`, the identity cache, the pool settings in `db/engine.py` (ops-2, with code defaults 3 and 3), the `db/engine.py` comment (ops-2); `OPENAI_MODEL` (slice 3); root `.env.example`, `migrate_to_db.py`, `notion_hymns.py`, `fill_from_hymnary.py` (slice 7). Never create `backend/cache.py` or `backend/tests/test_cache.py` (slice 2).
- These tests stay unchanged and green: `test_auth.py`, `test_api_me.py`, `test_api_security.py`, `test_docs.py`, `test_ci_workflow.py`, `test_no_streamlit_in_core.py`, `test_keepalive.py`, and all of `streamlit_tests/`.

## Spec clarifications (recorded, not deviations of intent)

1. **Private-key scan.** The ops spec's Testing section says "no file under `.github/` or `docs/` contains `AGE-SECRET-KEY-`", but the spec file itself (under `docs/`, line 1043) contains that prefix, so a plain substring check would fail on the spec. The test therefore matches the shape of a real age private key: `AGE-SECRET-KEY-1` followed by 58 upper-case Bech32 characters (`AGE-SECRET-KEY-1[02-9AC-HJ-NP-Z]{58}`). A self-test proves that it catches a key and ignores a mention. The intent is unchanged: no private key can be committed there.
2. **Dead-module test spelling.** Acceptance criterion 6 requires the whole-word grep over `backend` to find nothing. So the new test builds the six file names from parts at runtime, and never spells them as whole words.
3. **PyYAML.** The ops spec says to parse `backup.yml` as YAML. PyYAML is installed today only through the `uvicorn[standard]` extra, so `requirements-dev.txt` names it explicitly (test-only).
4. **Docs tests.** The README "Backups" paragraph and the runbook get small tests in `test_ops_workflows.py`, so the docs task has a failing test first. `test_docs.py` stays unchanged.
5. **Runbook scope.** ops-1 creates `docs/ops-runbook.md` with the sections the delivery plan assigns to it: "Supabase lockdown record", "Backups", "Streamlit freeze" (the two Streamlit apps, bug triage and the D5 record), "Platform limits", plus "Incident response". Incident response belongs to the Step 0 lockdown record, whose results land in this runbook. ops-3 adds "Environments and variables" and "Keep-alive", and adds the freeze record and policy.
6. **Owner values in the runbook.** The Step 0 results and platform limits the owner supplied on 2026-09-25 are written into the runbook directly (Task 6). Values still pending are `[owner: …]` markers, filled in Task 7 (key), Task 9 (before merge) or Tasks 10–12 (after merge).
7. **Owner corrections (2026-09-25) override the ops spec.** (a) The Streamlit app names are swapped: keep and check `liturgy-stg`, retire `liturgy` (Global Constraints). (b) Step 0 is done except the `age` key pair. (c) Pool Size is 15, so the pool values are 3 and 3, not the spec's 5 and 5 (or its 3/2 fallback). Until ops-2, no code reads `DB_POOL_SIZE` or `DB_MAX_OVERFLOW`; ops-1 documents them and records the interim exposure rather than moving ops-2's engine change forward (the delivery plan keeps `db/engine.py` out of ops-1).
8. **`shadcn` move.** The spec's `npm install --save-dev shadcn@^4.21.0` re-resolves `shadcn` to the newest 4.x. Task 4 moves the line by hand and runs a plain `npm install`, which keeps every locked version; the result the spec asks for (dev-only, lockfile committed) is the same.
9. **D5 wiring.** The `keep` set is built by a second helper, `ui_helpers.picked_hymn_keys(session)`, so the D5 regression test exercises the same code `app.py` runs.
10. **D5 recovery.** The runbook adds a second recovery query for services that lost some of their hymns (loading an older archived service with one or two recent hymns), next to the spec's query for services with none.

## File Map

```
ui_helpers.py                                 + hymn_options_excluding_recent(), picked_hymn_keys() (D5 fix, pure)
app.py                                        uses it in the "exclude recent" filter (lines 34, 47-53, 735-746)
streamlit_tests/test_app_helpers.py           + 4 helper tests + D5 regression test
backend/email_send.py                         DELETED
backend/notion_archive.py                     DELETED
backend/notion_usage.py                       DELETED
backend/select_sunday_hymns.py                DELETED
backend/add_hymnary_links.py                  DELETED
backend/fix_hymn_titles.py                    DELETED
backend/tests/test_foundation_setup.py        + dead modules gone, .env.example keys, shadcn dev-only
backend/.env.example                          + APP_ENV, LOG_LEVEL, DB_POOL_SIZE=3, DB_MAX_OVERFLOW=3, ESV_API_KEY
frontend/package.json, package-lock.json      shadcn moved to devDependencies
requirements-dev.txt                          + PyYAML>=6.0 (test only)
.github/backup/pg_env.py                      NEW: stdin URL -> ::add-mask:: lines or PG* exports (fix round 1; replaced normalize-pg-url.sh)
.github/workflows/backup.yml                  REWRITTEN: version-matched pg_dump | age, encrypted artifact
.github/backup/age-recipients.txt             NEW: owner's age public key(s)
backend/tests/test_ops_workflows.py           NEW: parsed backup.yml, PG_MAJOR, pg_env.py, runbook, README, recipients
docs/ops-runbook.md                           NEW: lockdown record, backups, Streamlit apps + triage + D5, platform limits, incident response
README.md                                     "Backups (required)" paragraph rewritten (lines 151-156)
```

---

### Task 0 (OWNER, before Task 1): tester workaround, `liturgy-stg` deploy branch, `age` key

These are owner steps. The agent asks for them at the start and records the answers; Tasks 1–6 can proceed while Step 3 is under way.

**Files:** none changed here. The answers go into `docs/ops-runbook.md` in Task 6, Step 3 (if already known) or Task 9, Step 2.

- [ ] **Step 1 (OWNER): Make sure the tester has the D5 workaround message**

The ops spec sends it on day one (Step 0), but the owner's list of completed Step 0 items (2026-09-25) does not include it. Ask the owner whether it was sent, and when. If it was not, the owner sends it now to the tester, who uses https://liturgy-stg.streamlit.app. It is outward-facing, so only on the owner's explicit yes. Exact copy (ops spec, User experience):

> Quick tip until I tell you it's fixed: keep "Exclude hymns used in the last 12 weeks" unticked whenever you load a saved service, click "Prepare bulletin copy" or "Prepare pastor's copy", or save. You can tick it while you choose hymns, but untick it before those steps. Otherwise the app can silently clear your hymn choices and save the service without hymns.

Record the date it was sent (or "not sent" and why) for the runbook's D5 table.

- [ ] **Step 2 (OWNER): Check which branch `liturgy-stg` deploys from**

Streamlit Cloud (share.streamlit.io) → `liturgy-stg` → ⋮ → Settings: note the repository, branch and main file. Expected: `bbrown62450/church`, `main`, `app.py`. Give the agent the three values and the date.

- If the branch is `main`, the D5 fix goes live on `liturgy-stg` when ops-1 merges, and Task 10, Step 1 confirms the rebuild.
- If it is any other branch (origin still has old feature branches, for example `claude/multi-user-app-support-edd5eb`, 26 commits behind `main`), stop before Task 8 and decide with the owner: switch `liturgy-stg` to `main` (it then serves `main`'s current code; sign in and check that the owner's church loads before the tester next uses it), or also merge the D5 commit into that branch. Record the decision in the runbook next to the branch, and have Task 10 check the branch the app really serves.

- [ ] **Step 3 (OWNER, in parallel with Tasks 1–6): Generate the backup `age` key pair**

The key pair has not been generated yet (2026-09-25). Task 7, Step 5 needs its public line. On the owner's own machine:

```bash
brew install age
age-keygen -o ~/wsb-backup-key.txt      # prints "Public key: age1…"
```

1. Store the **whole** file in the password manager, plus one offline copy (for example, a printout or an encrypted USB stick kept at home).
2. Delete it from disk: `rm ~/wsb-backup-key.txt`.
3. Optional: repeat with `-o ~/wsb-backup-key-2.txt` for a second recovery key, stored apart from the first.
4. Give the agent **only** the `age1…` public line(s) (62 characters: `age1` plus 58), the password-manager entry name, the offline copy's location and the date. Never the key file or its `AGE-SECRET-KEY-…` line.

---

### Task 1: Streamlit D5 fix: never drop hymns already picked (S16)

This is the first commit of ops-1. It may ship as its own PR (Step 8) if the rest of ops-1 is delayed.

**Files:**
- Modify: `ui_helpers.py:1-3` (import) and append two functions after line 63
- Modify: `app.py:34`, `app.py:47-53`, `app.py:735-746`
- Test: `streamlit_tests/test_app_helpers.py:1-7` (imports) and append tests after line 50

**Interfaces:**
- Consumes: `hymn_usage.is_hymn_recently_used(number, title, recent_set) -> bool`, `hymn_usage.record_usage(church_id, date_str, hymns) -> bool`, `hymn_usage.get_recently_used_identifiers(church_id, weeks=12) -> set[tuple[int | None, str]]`, `ui_helpers.build_title_to_info(rows) -> dict[str, dict]` (keys are lower-cased titles), `ui_helpers.coerce_selectbox_value(current, options) -> str`, fixtures `tmp_db` and `make_church` (re-exported by `streamlit_tests/conftest.py`).
- Produces: `ui_helpers.hymn_options_excluding_recent(title_to_info: dict, recent_used: set, keep: set[str]) -> list[str]`, the sorted title keys minus recently used hymns, except keys in `keep` that exist in `title_to_info`; and `ui_helpers.picked_hymn_keys(session) -> set[str]`, the non-empty values of the slot keys `"opening"`, `"response"` and `"closing"` in any mapping with `.get` (`st.session_state` in `app.py`, a dict in tests).

- [ ] **Step 1: Start the branch and check the baseline**

```bash
git fetch origin
git merge-base --is-ancestor claude/full-migration-design origin/main && base=origin/main || base=claude/full-migration-design
git switch -c claude/ops-1-backups-cleanup-d5 "$base"
.venv/bin/python -m pytest -q | tail -1
```
Expected: `206 passed`. Leave this plan file uncommitted for now (Task 8, Step 4 commits it), so the D5 fix is the branch's first commit.

- [ ] **Step 2: Write the failing tests**

Replace the import block at the top of `streamlit_tests/test_app_helpers.py` (lines 1-7):

```python
import pytest
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    hymn_display_from_flat,
    build_title_to_info,
)
```

with:

```python
from datetime import date, timedelta

import pytest
from hymn_usage import get_recently_used_identifiers, record_usage
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    hymn_display_from_flat,
    build_title_to_info,
    coerce_selectbox_value,
    hymn_options_excluding_recent,
    picked_hymn_keys,
)
```

Append to the end of `streamlit_tests/test_app_helpers.py`:

```python


# --- inv D5: "Exclude hymns used in the last 12 weeks" must never drop a pick ---

def _hymnal(*titles_and_numbers):
    """title_to_info for a hymnal given as (title, number) pairs."""
    return build_title_to_info([
        {"id": str(number), "Hymn Title": title, "Hymn Number": number, "Hymnary.org Link": None}
        for title, number in titles_and_numbers
    ])


def test_excluding_recent_keeps_a_recent_hymn_that_is_already_picked():
    title_to_info = _hymnal(("A", 1), ("B", 2), ("C", 3))
    recent_used = {(1, "a"), (2, "b")}
    assert hymn_options_excluding_recent(title_to_info, recent_used, {"a"}) == ["a", "c"]


def test_excluding_recent_with_nothing_picked_hides_every_recent_hymn():
    title_to_info = _hymnal(("A", 1), ("B", 2), ("C", 3))
    recent_used = {(1, "a"), (2, "b")}
    assert hymn_options_excluding_recent(title_to_info, recent_used, set()) == ["c"]


def test_excluding_recent_always_offers_a_hymn_that_is_not_recent():
    title_to_info = _hymnal(("A", 1), ("B", 2), ("C", 3))
    assert hymn_options_excluding_recent(title_to_info, set(), set()) == ["a", "b", "c"]
    assert "c" in hymn_options_excluding_recent(title_to_info, {(1, "a")}, {"b"})


def test_excluding_recent_never_adds_a_kept_key_missing_from_the_hymnal():
    # A pick whose hymn was renamed or deleted in Settings is not brought back.
    title_to_info = _hymnal(("A", 1), ("C", 3))
    assert hymn_options_excluding_recent(title_to_info, {(1, "a")}, {"a", "gone"}) == ["a", "c"]


def test_d5_picks_survive_prepare_with_exclude_recent_ticked(tmp_db, make_church):
    """The D5 flow: Prepare records the three picks as used today and reruns. The
    rebuilt options must still contain the picks, or safe_hymn_selectbox resets
    them to '' and the next Prepare or Save stores the service without hymns."""
    church_id = make_church()
    title_to_info = _hymnal(
        ("Holy, Holy, Holy", 1), ("Amazing Grace", 378), ("Be Thou My Vision", 339),
        ("O God, Our Help in Ages Past", 210), ("Come, Thou Fount", 356),
    )
    picks = ["holy, holy, holy", "amazing grace", "be thou my vision"]
    # Prepare bulletin copy: record_usage(church_id, service_date_str, hymns_ordered)
    assert record_usage(church_id, date.today().isoformat(), [title_to_info[p] for p in picks])
    # A hymn used last week and not picked this time.
    assert record_usage(church_id, (date.today() - timedelta(weeks=1)).isoformat(),
                        [title_to_info["o god, our help in ages past"]])

    recent_used = get_recently_used_identifiers(church_id, weeks=12)
    # app.py builds `keep` as picked_hymn_keys(st.session_state); a dict stands in for it.
    session = {"opening": picks[0], "response": picks[1], "closing": picks[2], "sermon_title": "x"}
    keep = picked_hymn_keys(session)
    assert keep == set(picks)
    assert picked_hymn_keys({"opening": picks[0], "response": ""}) == {picks[0]}   # empty or missing slot
    options = hymn_options_excluding_recent(title_to_info, recent_used, keep)

    for pick in picks:
        assert coerce_selectbox_value(pick, [""] + options) == pick
    assert "o god, our help in ages past" not in options   # recent, not picked: still hidden
    assert "come, thou fount" in options                    # never used: offered

    # Without the picks in `keep` (the old app.py filter) every pick resets: the bug.
    old_options = hymn_options_excluding_recent(title_to_info, recent_used, set())
    for pick in picks:
        assert coerce_selectbox_value(pick, [""] + old_options) == ""
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q streamlit_tests/test_app_helpers.py`
Expected: collection error `ImportError: cannot import name 'hymn_options_excluding_recent' from 'ui_helpers'`, `1 error`.

- [ ] **Step 4: Add the helpers to `ui_helpers.py`**

In `ui_helpers.py`, directly after line 2 (`from __future__ import annotations`) and its blank line, add:

```python
from hymn_usage import is_hymn_recently_used

```

so that the top of the file reads:

```python
"""Pure, Streamlit-free helpers so page logic is importable and unit-testable."""
from __future__ import annotations

from hymn_usage import is_hymn_recently_used

# OAuth callback query keys we strip AFTER handling. Never a blanket
```

Append to the end of `ui_helpers.py` (after `coerce_selectbox_value`):

```python


def hymn_options_excluding_recent(title_to_info: dict, recent_used: set, keep: set[str]) -> list[str]:
    """Sorted title keys without recently used hymns, but never without a key in `keep`
    (the hymns already picked in the three slots).

    inv D5: Prepare records the picks as used today, so without `keep` the next
    rerun drops them from the options, safe_hymn_selectbox resets them to '' and
    the next Prepare or Save stores the service without hymns. A key in `keep`
    that is not in `title_to_info` (a renamed or deleted hymn) is not added.
    """
    return sorted(
        key for key, info in title_to_info.items()
        if key in keep
        or not is_hymn_recently_used(info.get("number"), info.get("title") or "", recent_used)
    )


def picked_hymn_keys(session) -> set[str]:
    """The title keys picked in the three hymn slots, without empty slots.

    `session` is anything with `.get`: st.session_state in app.py, a dict in tests.
    """
    return {session.get(slot) or "" for slot in ("opening", "response", "closing")} - {""}
```

- [ ] **Step 5: Run the helper tests to verify they pass**

Run: `.venv/bin/python -m pytest -q streamlit_tests/test_app_helpers.py`
Expected: `10 passed`

- [ ] **Step 6: Use the helpers in `app.py`**

`app.py:34`, replace:

```python
from hymn_usage import get_recently_used_identifiers, record_usage, is_hymn_recently_used
```

with:

```python
from hymn_usage import get_recently_used_identifiers, record_usage
```

`app.py:47-53`, replace:

```python
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    build_title_to_info,
    pick_invite_code,
    coerce_selectbox_value,
)
```

with:

```python
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    build_title_to_info,
    pick_invite_code,
    coerce_selectbox_value,
    hymn_options_excluding_recent,
    picked_hymn_keys,
)
```

`app.py:735-746`. Before this step the block reads:

```python
    if exclude_recent_hymns and title_to_info:
        recent_used = get_recently_used_identifiers(church_id, weeks=12)
        titles_sorted = sorted(
            k for k in title_to_info
            if not is_hymn_recently_used(
                title_to_info[k].get("number"), title_to_info[k].get("title") or "", recent_used)
        )
        excluded = len(title_to_info) - len(titles_sorted)
        if excluded > 0:
            st.caption(f"Hymns used in the last 12 weeks are excluded ({excluded} excluded).")
    else:
        titles_sorted = sorted(title_to_info.keys(), key=str.lower)
```

Replace it with:

```python
    if exclude_recent_hymns and title_to_info:
        recent_used = get_recently_used_identifiers(church_id, weeks=12)
        # Hymns already picked stay selectable (inv D5). Prepare records them as used
        # today; dropping them here would reset the slots and save the service without hymns.
        titles_sorted = hymn_options_excluding_recent(title_to_info, recent_used, picked_hymn_keys(st.session_state))
        excluded = len(title_to_info) - len(titles_sorted)
        if excluded > 0:
            st.caption(f"Hymns used in the last 12 weeks are excluded ({excluded} excluded).")
    else:
        titles_sorted = sorted(title_to_info.keys(), key=str.lower)
```

The caption still reports `len(title_to_info) - len(titles_sorted)`, so a kept pick is not counted as excluded. This covers every path. A pick recorded by Prepare is in `keep`. Loading an archived service writes its hymns into the three slot keys (`app.py:401-404`) before this block runs. An AI-applied pick is stored and followed by `st.rerun()` (`app.py:817`).

- [ ] **Step 7: Verify `app.py` and run the full suite**

```bash
.venv/bin/python -m py_compile app.py && echo compiled
grep -c "is_hymn_recently_used" app.py
grep -cF "hymn_options_excluding_recent(title_to_info, recent_used, picked_hymn_keys(st.session_state))" app.py
.venv/bin/python -m pytest -q | tail -1
```
Expected: `compiled`, then `0`, then `1` (the exact call the regression test mirrors), then `211 passed`.

- [ ] **Step 8: Commit**

```bash
git add ui_helpers.py app.py streamlit_tests/test_app_helpers.py
git commit -m "Streamlit: keep picked hymns when excluding recent ones (inv D5)

With 'Exclude hymns used in the last 12 weeks' ticked, Prepare recorded the
picks as used today, the next rerun dropped them from the options, and
safe_hymn_selectbox reset them, so the next Prepare or Save stored the
service without hymns. Hymns already picked in the three slots now stay
selectable; recent hymns that are not picked stay hidden.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 9 (optional; only if the owner asks to ship D5 ahead of the rest of ops-1): open a D5-only PR**

Opening a PR is outward-facing, so get the owner's yes first. Then:

```bash
d5=$(git rev-parse HEAD)
git switch -c claude/ops-1-d5-fix origin/main
git cherry-pick "$d5"
.venv/bin/python -m pytest -q | tail -1
git push -u origin claude/ops-1-d5-fix
gh pr create --base main --head claude/ops-1-d5-fix \
  --title "Streamlit: keep picked hymns when excluding recent ones (inv D5)" \
  --body "Data-safety fix for the live Streamlit app, liturgy-stg (ops spec S16, inv D5). With 'Exclude hymns used in the last 12 weeks' ticked, Prepare → Save stored services without hymns. After merge, run the D5 manual check (ops-1 plan, Task 10).

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
git switch claude/ops-1-backups-cleanup-d5
```
Expected: the cherry-picked branch passes (`206 passed` plus the 5 new tests = `211 passed`). Continue with Task 2 on `claude/ops-1-backups-cleanup-d5`. When the D5 PR has merged first, git treats the identical change as already applied when ops-1 merges.

---

### Task 2: Delete the six dead modules (S4)

**Files:**
- Delete: `backend/email_send.py`, `backend/notion_archive.py`, `backend/notion_usage.py`, `backend/select_sunday_hymns.py`, `backend/add_hymnary_links.py`, `backend/fix_hymn_titles.py`
- Test: `backend/tests/test_foundation_setup.py` (append after line 35)

**Interfaces:**
- Consumes: `ROOT` in `test_foundation_setup.py` (the repo root; already defined at line 3).
- Produces: `DELETED_DEAD_MODULES` (tuple of the six file names) in `test_foundation_setup.py`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_foundation_setup.py`:

```python


# --- ops slice (ops-1): dead code and configuration drift (inv H8, H10, H11, H12) ---

# Spelled in parts so that the ops spec's whole-word grep (acceptance criterion 6),
# which must find nothing under backend/, does not match this test.
DELETED_DEAD_MODULES = tuple("_".join(parts) + ".py" for parts in (
    ("email", "send"),
    ("notion", "archive"),
    ("notion", "usage"),
    ("select", "sunday", "hymns"),
    ("add", "hymnary", "links"),
    ("fix", "hymn", "titles"),
))


def test_dead_modules_are_deleted():
    found = [str(p.relative_to(ROOT)) for name in DELETED_DEAD_MODULES
             for p in (ROOT / "backend").rglob(name)]
    assert found == []
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py::test_dead_modules_are_deleted`
Expected: FAIL, `AssertionError: assert ['backend/email_send.py', 'backend/notion_archive.py', ...] == []`

- [ ] **Step 3: Delete the modules**

None of the six is imported anywhere (ops spec, "Zero-importer check"). `notion_hymns.py` and `hymn_utils.py`, which three of them import, stay.

```bash
git rm backend/email_send.py backend/notion_archive.py backend/notion_usage.py \
       backend/select_sunday_hymns.py backend/add_hymnary_links.py backend/fix_hymn_titles.py
```

- [ ] **Step 4: Run the test, the acceptance grep and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py::test_dead_modules_are_deleted
grep -rnwE '(email_send|notion_archive|notion_usage|select_sunday_hymns|add_hymnary_links|fix_hymn_titles)' --include='*.py' backend app.py streamlit_* ui_helpers.py; echo "grep exit $?"
.venv/bin/python -m pytest -q | tail -1
```
Expected: `1 passed`; then no grep matches and `grep exit 1`; then `212 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_foundation_setup.py
git commit -m "Delete six dead backend modules (inv H8, H10, H11)

email_send, notion_archive, notion_usage, select_sunday_hymns,
add_hymnary_links and fix_hymn_titles had no importers and no tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `backend/.env.example` gains the ops settings (S5)

**Files:**
- Modify: `backend/.env.example` (insert after line 13, the blank line after `CORS_ORIGINS=http://localhost:3000`)
- Test: `backend/tests/test_foundation_setup.py` (line 1 import; append a test)

**Interfaces:**
- Consumes: `ROOT` in `test_foundation_setup.py`.
- Produces: `backend/.env.example` documents `APP_ENV`, `LOG_LEVEL`, `DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=3`, `ESV_API_KEY`. `LOG_LEVEL` and `ESV_API_KEY` are read today (`backend/api/main.py:19`, `backend/scripture_fetcher.py:41`); `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` from ops-2 (whose code defaults must be 3 and 3); `APP_ENV` from ops-3. Until then `backend/db/engine.py` sets no pool size, so each process uses SQLAlchemy's 5 + 10; the runbook records that interim exposure (Task 6, "Platform limits").

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_foundation_setup.py`, replace line 1:

```python
from pathlib import Path
```

with:

```python
import re
from pathlib import Path
```

Append to `backend/tests/test_foundation_setup.py`:

```python


def test_backend_env_example_lists_the_ops_settings():
    text = (ROOT / "backend" / ".env.example").read_text()
    missing = [key for key in ("APP_ENV", "LOG_LEVEL", "DB_POOL_SIZE", "DB_MAX_OVERFLOW", "ESV_API_KEY")
               if not re.search(rf"^{key}=", text, re.MULTILINE)]
    assert missing == []
    # Supavisor Pool Size is 15 (Nano): 2 x (3 + 3) + 2 = 14 <= 15 (owner, 2026-09-25).
    assert re.search(r"^DB_POOL_SIZE=3$", text, re.MULTILINE)
    assert re.search(r"^DB_MAX_OVERFLOW=3$", text, re.MULTILINE)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py::test_backend_env_example_lists_the_ops_settings`
Expected: FAIL, `assert ['APP_ENV', 'LOG_LEVEL', 'DB_POOL_SIZE', 'DB_MAX_OVERFLOW', 'ESV_API_KEY'] == []`

- [ ] **Step 3: Add the lines**

In `backend/.env.example`, insert after line 13 (the blank line after `CORS_ORIGINS=http://localhost:3000`), so the block starts at line 14:

```
# development (default) or production (Railway). From ops-3, production refuses to
# start on SQLite and logs an error when CORS_ORIGINS lists only localhost.
APP_ENV=development

# API log level: DEBUG, INFO (default), WARNING, ERROR.
LOG_LEVEL=INFO

# Postgres pool per process, read from ops-2 on (defaults 3 and 3). Both apps share
# the Supabase session pooler (Pool Size 15): 2 x (3 + 3) + 2 = 14 <= 15.
DB_POOL_SIZE=3
DB_MAX_OVERFLOW=3

# Optional. Enables the ESV translation; the key stays on the backend.
ESV_API_KEY=

```

The block ends with its own blank line, so it sits between single blank lines. The `# Carried over for later slices …` block with `OPENAI_MODEL=gpt-3.5-turbo` stays unchanged (slice 3 owns it). Do not touch the root `.env.example` (slice 7).

- [ ] **Step 4: Run the test and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py
sed -n '11,28p' backend/.env.example
.venv/bin/python -m pytest -q | tail -1
```
Expected: `6 passed`; lines 11-28 show the comment for `CORS_ORIGINS`, then `CORS_ORIGINS=…`, a blank line, the five new settings with their comments (`DB_POOL_SIZE=3` at line 23, `DB_MAX_OVERFLOW=3` at line 24), `ESV_API_KEY=` at line 27, and a blank line 28; then `213 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/.env.example backend/tests/test_foundation_setup.py
git commit -m "backend/.env.example: add APP_ENV, LOG_LEVEL, DB pool and ESV_API_KEY (inv H12)

The pool defaults are 3 and 3: the Supabase session pooler's Pool Size is 15,
and 2 x (3 + 3) + 2 = 14 fits it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Move `shadcn` to devDependencies (S6)

`src/app/globals.css:3` imports `shadcn/tailwind.css`, which is resolved at build time. Vercel installs devDependencies for the build, and `frontend/vercel.json` sets no custom install command. The Vercel dashboard settings are checked in Task 9.

**Files:**
- Modify: `frontend/package.json` (line 24 moves into `devDependencies`), `frontend/package-lock.json` (regenerated by npm)
- Test: `backend/tests/test_foundation_setup.py` (line 1 import; append a test)

**Interfaces:**
- Consumes: `ROOT` in `test_foundation_setup.py`.
- Produces: `frontend/package.json` with `"shadcn": "^4.21.0"` under `devDependencies` only.

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_foundation_setup.py`, replace the first two lines:

```python
import re
from pathlib import Path
```

with:

```python
import json
import re
from pathlib import Path
```

Append to `backend/tests/test_foundation_setup.py`:

```python


def test_shadcn_is_a_dev_dependency_only():
    package = json.loads((ROOT / "frontend" / "package.json").read_text())
    assert "shadcn" in package["devDependencies"]
    assert "shadcn" not in package["dependencies"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py::test_shadcn_is_a_dev_dependency_only`
Expected: FAIL, `AssertionError: assert 'shadcn' in {'@tailwindcss/postcss': '^4', ...}`

- [ ] **Step 3: Move the line by hand, then let npm update the lockfile**

Naming the package (`npm install --save-dev shadcn@^4.21.0`, as the spec words it) would re-resolve it to the newest 4.x; a plain `npm install` keeps every locked version (Spec clarification 8).

In `frontend/package.json`, delete line 24 (`    "shadcn": "^4.21.0",`) from `dependencies`, and insert the same line in `devDependencies` directly after `    "eslint-config-next": "16.3.6",` and before `    "tailwindcss": "^4",` (alphabetical; both neighbours keep their commas). Then:

```bash
(cd frontend && npm install && node -e 'const p=require("./package.json"); console.log(p.devDependencies.shadcn, "shadcn" in p.dependencies)')
```
Expected: npm finishes without errors (audit notices are fine), then `^4.21.0 false`.

- [ ] **Step 4: Check that the lockfile changed no package version**

```bash
old_lock="${TMPDIR:-/tmp}/ops1-old-lock.json"
git show HEAD:frontend/package-lock.json > "$old_lock"
node -e '
const [a, b] = process.argv.slice(1).map(f => require(require("path").resolve(f)).packages);
const changed = Object.keys(a).filter(k => b[k] && a[k].version !== b[k].version);
const removed = Object.keys(a).filter(k => !b[k]);
const added = Object.keys(b).filter(k => !a[k] && !b[k].inBundle);
const bundled = Object.keys(b).filter(k => !a[k] && b[k].inBundle).length;
console.log(JSON.stringify({ changed, removed, added, bundled, shadcnDev: b["node_modules/shadcn"].dev === true }));
' "$old_lock" frontend/package-lock.json
```
Expected: `{"changed":[],"removed":[],"added":[],"bundled":6,"shadcnDev":true}` (checked in a scratch copy with npm 11.17 on 2026-09-25). The lock diff consists of `"dev": true` flags on shadcn's own dependency tree, plus `inBundle` entries that newer npm versions add under `@tailwindcss/oxide-wasm32-wasi/node_modules/` (`bundled`; 0 on an older npm is also fine). None of them installs a new package or changes a version; any entry in `added` or `changed` means stop and investigate.

- [ ] **Step 5: Run the frontend checks exactly as CI does**

```bash
(cd frontend && npm ci && npm run lint && npm run typecheck && npm test && \
  NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co \
  NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder \
  NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build)
```
Expected: lint reports no problems; typecheck prints nothing; Vitest prints `Test Files  3 passed (3)`; `next build` finishes with the route table and no error.

- [ ] **Step 6: Run the backend test and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_foundation_setup.py::test_shadcn_is_a_dev_dependency_only
.venv/bin/python -m pytest -q | tail -1
```
Expected: `1 passed`, then `214 passed`.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json backend/tests/test_foundation_setup.py
git commit -m "frontend: move shadcn to devDependencies (inv H12, F §4.11)

Only the build uses it (globals.css imports shadcn/tailwind.css).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

If `git status` shows `frontend/AGENTS.md`, `frontend/CLAUDE.md` or `frontend/next-env.d.ts` modified by the build, leave them out of the commit and restore them with `git checkout -- <file>`.

---

### Task 5: URL normalizer and the encrypted `backup.yml` (S2)

> **Fix round 1 (2026-09-26, owner-approved security review).** Task 5 was built as written below and then changed; the committed files are authoritative, and `.superpowers/sdd/ops1-task-5-report.md` → "Fix round 1" has the details. libpq quotes password fragments of a malformed URL in its errors, and GitHub masks only the whole secret, so `.github/backup/pg_env.py` replaced `normalize-pg-url.sh` (deleted). The dump step first runs `python3 .github/backup/pg_env.py --mask <<<"$BACKUP_DATABASE_URL"` (one escaped `::add-mask::` per part: password, user, host, whole URL), then `eval`s `pg_env.py --exports`, so `psql` and `pg_dump` get `PG*` variables (with `PGSSLMODE: require`) and no URL. The job has `environment: backup` (the secret lives there; only `main` may use it), the actions are pinned to commit SHAs (`actions/checkout` v4.4.0 with `persist-credentials: false`, `actions/upload-artifact` v4.6.2), and the size check prints `::error::Encrypted backup is unexpectedly small`. `test_ops_workflows.py` now checks the parsed YAML and `pg_env.py` (57 tests): `NORMALIZE_SCRIPT` became `PG_ENV_SCRIPT`, `_postgres_image_majors(text)` became `_postgres_service_majors(workflow)` (reads `jobs.*.services.*.image`), and `SERVER_MAJOR = "17"` was added. `ROOT`, `_read`, `_pg_major`, `AGE_RECIPIENT` and `re`, which Tasks 6 and 7 use, are unchanged. The suite is `271 passed` after this task.

**Files:**
- Create: `.github/backup/normalize-pg-url.sh`
- Modify: `.github/workflows/backup.yml:1-28` (full rewrite)
- Modify: `requirements-dev.txt:2` (add a line after it)
- Test: `backend/tests/test_ops_workflows.py` (new)

**Interfaces:**
- Consumes: `.github/workflows/ci.yml` (read only).
- Produces:
  - `bash .github/backup/normalize-pg-url.sh`: reads one URL on stdin and writes the libpq URL on stdout (`postgresql+psycopg2://` → `postgresql://`, `postgres://` → `postgresql://`); exit 0; nothing on stderr.
  - `backup.yml` with `jobs.dump.env.PG_MAJOR: "17"`, reading `.github/backup/age-recipients.txt` (created in Task 7).
  - In `backend/tests/test_ops_workflows.py`, used by Tasks 6 and 7: `ROOT` (repo root `pathlib.Path`), `BACKUP_YML`, `CI_YML`, `NORMALIZE_SCRIPT`, `AGE_RECIPIENT` (compiled `^age1[02-9ac-hj-np-z]{58}$`), `POSTGRES_IMAGE`, `_read(path) -> str`, `_pg_major() -> str`, `_postgres_image_majors(text) -> list[str]`; module imports `pathlib`, `re`, `subprocess`, `pytest`, `yaml`.

- [ ] **Step 1: Make PyYAML an explicit test dependency**

`requirements-dev.txt` currently reads:

```
-r requirements.txt
pytest>=8.0
```

Change it to:

```
-r requirements.txt
pytest>=8.0
# backend/tests/test_ops_workflows.py parses workflow YAML
PyYAML>=6.0
```

Run: `.venv/bin/pip install -q -r requirements-dev.txt && .venv/bin/python -c "import yaml; print(yaml.__version__)"`
Expected: a version such as `6.0.3`.

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/test_ops_workflows.py`:

```python
"""Ops workflows and their companion files (ops slice spec → Testing).

Built in ops-1 (backups, runbook, age recipients). ops-3 adds the keepalive.yml
and keep-awake.yml checks and deletes test_keepalive.py.
"""
import pathlib
import re
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]   # repo root
BACKUP_YML = ROOT / ".github" / "workflows" / "backup.yml"
CI_YML = ROOT / ".github" / "workflows" / "ci.yml"
NORMALIZE_SCRIPT = ".github/backup/normalize-pg-url.sh"   # relative: run exactly as backup.yml runs it

AGE_RECIPIENT = re.compile(r"^age1[02-9ac-hj-np-z]{58}$")
POSTGRES_IMAGE = re.compile(r"\bpostgres:(\d+)")


def _read(path):
    return path.read_text(encoding="utf-8")


def _pg_major():
    """PG_MAJOR from backup.yml, parsed as YAML (jobs.dump.env.PG_MAJOR)."""
    return str(yaml.safe_load(_read(BACKUP_YML))["jobs"]["dump"]["env"]["PG_MAJOR"])


# --- backup.yml -------------------------------------------------------------

BACKUP_MUST_CONTAIN = (
    "schedule:",
    "workflow_dispatch",
    "contents: read",
    "secrets.BACKUP_DATABASE_URL",
    "pipefail",
    "bash .github/backup/normalize-pg-url.sh",
    "--recipients-file .github/backup/age-recipients.txt",
    "postgresql-client-${PG_MAJOR}",
    "--schema=public",
    "--format=custom",
    ".dump.age",
    "retention-days: 30",
    # Exact copy from the ops spec's "Exact server messages" table.
    "::error::BACKUP_DATABASE_URL secret is not set",
    "::error::.github/backup/age-recipients.txt has no age recipient",
    "::error::Postgres server major is $major but PG_MAJOR is $PG_MAJOR; update PG_MAJOR in backup.yml",
)
BACKUP_MUST_NOT_CONTAIN = ("secrets.DATABASE_URL", ".sql.gz", ' -f "backup', "+psycopg2")


def test_backup_workflow_dumps_encrypts_and_uploads():
    text = _read(BACKUP_YML)
    assert [needle for needle in BACKUP_MUST_CONTAIN if needle not in text] == []


def test_backup_workflow_has_no_plaintext_dump_or_old_secret():
    text = _read(BACKUP_YML)
    assert [needle for needle in BACKUP_MUST_NOT_CONTAIN if needle in text] == []


def test_backup_workflow_checks_recipients_with_the_pattern_the_tests_use():
    assert AGE_RECIPIENT.pattern in _read(BACKUP_YML)


def test_backup_workflow_pins_pg_major_in_the_job_env():
    assert re.fullmatch(r"\d+", _pg_major())


# --- normalize-pg-url.sh ----------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("postgresql+psycopg2://u:p@h:5432/db", "postgresql://u:p@h:5432/db"),
    ("postgres://u:p@h/db", "postgresql://u:p@h/db"),
    ("postgresql://u:p@h/db", "postgresql://u:p@h/db"),
])
def test_normalize_pg_url(raw, expected):
    result = subprocess.run(
        ["bash", NORMALIZE_SCRIPT], input=raw, capture_output=True, text=True, cwd=ROOT,
    )
    assert result.returncode == 0
    assert result.stdout.rstrip("\n") == expected
    assert result.stderr == ""


# --- CI Postgres major (slice 1 adds the service container) ----------------

def _postgres_image_majors(text):
    return POSTGRES_IMAGE.findall(text)


def test_postgres_image_parser_finds_service_container_majors():
    sample = 'services:\n  db:\n    image: postgres:16-alpine\n  other:\n    image: "postgres:17"\n'
    assert _postgres_image_majors(sample) == ["16", "17"]


def test_ci_postgres_image_matches_pg_major():
    # Inert until slice 1 declares a postgres:<N> service container in ci.yml.
    # This is the only check of the CI Postgres major (ops spec, slice 1 row).
    majors = _postgres_image_majors(_read(CI_YML))
    assert [m for m in majors if m != _pg_major()] == []
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py`
Expected: `7 failed, 2 passed`. The four `backup.yml` tests fail on the old workflow (`KeyError: 'env'` for the `PG_MAJOR` one). The three `test_normalize_pg_url` cases fail with return code 127 (`No such file or directory`). The parser self-test passes, and the CI check passes because `ci.yml` has no `postgres:` image yet.

- [ ] **Step 4: Create `.github/backup/normalize-pg-url.sh`**

```bash
#!/usr/bin/env bash
# Reads one Postgres URL on stdin and writes a libpq-compatible URL on stdout.
# Strips a SQLAlchemy driver suffix (postgresql+psycopg2:// -> postgresql://),
# which pg_dump and psql reject (inventory H5), and turns postgres:// into
# postgresql://. Never writes to stderr: the URL holds the database password.
# backup.yml and backend/tests/test_ops_workflows.py both run it as
# `bash .github/backup/normalize-pg-url.sh`, so its file mode does not matter.
set -euo pipefail
sed -E 's#^postgres(ql)?(\+[A-Za-z0-9_]+)?://#postgresql://#'
```

- [ ] **Step 5: Rewrite `.github/workflows/backup.yml`**

Replace the whole file with:

```yaml
# Daily encrypted backup of the Supabase `public` schema (ops slice, S2).
# The dump is piped through `age` to the public keys in
# .github/backup/age-recipients.txt, so no plaintext dump ever touches the
# runner's disk, and only the owner's private key can open the artifact.
# Key custody, key rotation and the restore drill: docs/ops-runbook.md → Backups.
name: db-backup
on:
  schedule:
    - cron: "37 8 * * *"   # daily at 08:37 UTC
  workflow_dispatch: {}
permissions:
  contents: read
concurrency:
  group: db-backup
  cancel-in-progress: false
jobs:
  dump:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    env:
      PG_MAJOR: "17"          # MUST equal the Supabase server major recorded in step 0; the job checks it
    steps:
      - uses: actions/checkout@v4
      - name: Check prerequisites
        env:
          BACKUP_DATABASE_URL: ${{ secrets.BACKUP_DATABASE_URL }}
        run: |
          test -n "$BACKUP_DATABASE_URL" || { echo "::error::BACKUP_DATABASE_URL secret is not set"; exit 1; }
          grep -Eq '^age1[02-9ac-hj-np-z]{58}$' .github/backup/age-recipients.txt \
            || { echo "::error::.github/backup/age-recipients.txt has no age recipient"; exit 1; }
      - name: Install PostgreSQL client and age
        run: |
          sudo apt-get update
          sudo apt-get install -y postgresql-common age
          sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
          sudo apt-get install -y "postgresql-client-${PG_MAJOR}"
      - name: Dump, compress and encrypt (plaintext never touches disk)
        env:
          BACKUP_DATABASE_URL: ${{ secrets.BACKUP_DATABASE_URL }}
        run: |
          set -euo pipefail
          url=$(printf '%s' "$BACKUP_DATABASE_URL" | bash .github/backup/normalize-pg-url.sh)
          echo "::add-mask::$url"
          bin="/usr/lib/postgresql/${PG_MAJOR}/bin"
          server=$("$bin/psql" "$url" -Atc 'show server_version_num')
          major=$(( server / 10000 ))
          [ "$major" = "$PG_MAJOR" ] || { echo "::error::Postgres server major is $major but PG_MAJOR is $PG_MAJOR; update PG_MAJOR in backup.yml"; exit 1; }
          ts=$(date -u +%Y%m%dT%H%M%SZ)
          "$bin/pg_dump" "$url" --schema=public --no-owner --no-privileges --format=custom \
            | age --encrypt --recipients-file .github/backup/age-recipients.txt --output "backup-$ts.dump.age"
          test "$(stat -c %s "backup-$ts.dump.age")" -gt 1024
      - uses: actions/upload-artifact@v4
        with:
          name: db-backup
          path: backup-*.dump.age
          retention-days: 30
          if-no-files-found: error
          compression-level: 0
```

Keep the header comment free of the strings in `BACKUP_MUST_NOT_CONTAIN` (for example, never write the driver suffix `+psycopg2` in this file).

- [ ] **Step 6: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_keepalive.py
.venv/bin/python -m pytest -q | tail -1
```
Expected: `14 passed` (9 new tests plus the 5 in `test_keepalive.py`; its `test_backup_workflow_present` still finds `pg_dump` and `schedule:`), then `223 passed`.

- [ ] **Step 7: Commit**

```bash
git add requirements-dev.txt .github/backup/normalize-pg-url.sh .github/workflows/backup.yml backend/tests/test_ops_workflows.py
git commit -m "Encrypt the daily database backup and match pg_dump to the server (inv H5)

backup.yml now reads BACKUP_DATABASE_URL, strips the SQLAlchemy driver with
normalize-pg-url.sh, checks the server major against PG_MAJOR, and pipes a
custom-format pg_dump of the public schema through age, so no plaintext dump
exists on the runner. test_ops_workflows.py guards the workflow text, the
URL normalizer and the CI Postgres major.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Ops runbook and the README "Backups" paragraph (S15, S1/S12 records, S2 docs)

**Files:**
- Create: `docs/ops-runbook.md`
- Modify: `README.md:151-156`
- Test: `backend/tests/test_ops_workflows.py` (append)

**Interfaces:**
- Consumes: `ROOT`, `_read(path)`, `_pg_major()`, `re` from `test_ops_workflows.py` (Task 5).
- Produces: `docs/ops-runbook.md` with the sections `## Supabase lockdown record`, `## Backups`, `## Streamlit freeze` (with `### Streamlit apps`, `### Streamlit bug triage` and `### D5 fix and recovery record`), `## Platform limits` (containing exactly one line `- Postgres server major: 17`), `## Incident response`. The Step 0 results, platform limits and pool budget the owner supplied on 2026-09-25 are written in; only pending values are `[owner: …]` markers. ops-3 extends this file.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ops_workflows.py`:

```python


# --- docs/ops-runbook.md and README ------------------------------------------

RUNBOOK = ROOT / "docs" / "ops-runbook.md"
README = ROOT / "README.md"
PG_MAJOR_LINE = re.compile(r"^- Postgres server major: (\d+)\s*$", re.MULTILINE)
OPS1_RUNBOOK_SECTIONS = (
    "## Supabase lockdown record",
    "## Backups",
    "## Streamlit freeze",
    "## Platform limits",
    "## Incident response",
)
TRIAGE_ROWS = ("D5", "A7", "E6", "E4", "D6", "F6", "F7", "F10", "D3", "G7", "F4", "B2", "C1", "G5")


def test_runbook_postgres_server_major_matches_pg_major():
    majors = PG_MAJOR_LINE.findall(_read(RUNBOOK))
    assert len(majors) == 1, f"want exactly one '- Postgres server major: <N>' line, found {majors}"
    assert majors[0] == _pg_major()


def test_runbook_has_the_ops1_sections():
    headings = set(re.findall(r"^## .+$", _read(RUNBOOK), re.MULTILINE))
    assert [s for s in OPS1_RUNBOOK_SECTIONS if s not in headings] == []


def test_runbook_records_the_streamlit_bug_triage_and_d5_recovery():
    text = _read(RUNBOOK)
    assert "### Streamlit bug triage" in text
    assert [row for row in TRIAGE_ROWS if f"\n| {row}" not in text] == []
    assert "jsonb_array_length(hymns::jsonb) = 0" in text   # the D5 recovery query


def test_readme_backups_paragraph_describes_encrypted_backups():
    section = _read(README).split("### Backups (required)", 1)[1].split("\n### ", 1)[0]
    # "`age`" with backticks: a bare "age" is already a substring of "storage" in the old text.
    for needle in ("BACKUP_DATABASE_URL", "`age`", ".dump.age", "docs/ops-runbook.md"):
        assert needle in section, needle
    assert "compressed dump" not in section
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py`
Expected: `4 failed, 57 passed`. The three runbook tests fail with `FileNotFoundError` for `docs/ops-runbook.md`, and the README test fails with `AssertionError: BACKUP_DATABASE_URL`.

- [ ] **Step 3: Create `docs/ops-runbook.md`**

````markdown
# Operations runbook

The single place for the Supabase lockdown record, backup key custody and the
restore drill, the Streamlit freeze record, platform limits and incident
response. Design: `docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md`
("the ops spec").

- An entry marked `[owner: …]` is a value only the owner can see (a dashboard,
  a SQL result, a message sent). Replace the whole marker with the value and
  the date.
- Never paste a secret here: no database URL with its password, no API key,
  no access token, no `age` private key.
- ops-3 adds "Environments and variables" at the top and "Keep-alive" after
  "Backups", and adds the freeze record, the policy and the recorded versions
  to "Streamlit freeze".

## Supabase lockdown record

Project `worship-staging`, ref `tbecmwtitsoxzkrvxxxu`. Procedure: the ops spec →
Data and migrations → Step 0. Done on 2026-09-25; the results are below. To
check again, connect with the session-pooler URL the apps use, but never put
the URL on a command line: shell history keeps it, and libpq quotes parts of a
malformed URL, password included, in its errors. From the repo root, in bash
or zsh, `.github/backup/pg_env.py` turns it into `PG*` variables:

```
IFS= read -rs BACKUP_URL        # paste the URL and press Return; nothing is shown
eval "$(python3 .github/backup/pg_env.py --exports <<<"$BACKUP_URL")"; unset BACKUP_URL
docker run --rm -it -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE \
    -e PGSSLMODE=require postgres:17 psql
unset PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE    # when finished
```

If `psql` is installed, plain `PGSSLMODE=require psql` can replace the
`docker run` line.

**1. Exposure before the lockdown.** For each of `users`, `gmail_tokens`,
`invites` and `memberships`:

```
curl -s "https://tbecmwtitsoxzkrvxxxu.supabase.co/rest/v1/<table>?select=*&limit=1" \
  -H "apikey: <anon key>" -H "Authorization: Bearer <anon key>"
```

Then again with `Authorization: Bearer <your own access token>` (the
`authenticated` role, which any Google user can get by signing in).

| Role | Result | Date |
|---|---|---|
| anon | Not run as an exposure test: the Data API was already off. REST and GraphQL requests with the anon key return HTTP 503 `PGRST002` and no rows. | 2026-09-25 |
| authenticated | Not run: with the Data API off, `/rest/v1` serves no table to any role. | 2026-09-25 |

Any rows returned mean an incident: complete "Incident response" below. None
were returned, so there was no incident.

**2. Can RLS be enabled safely?** Through the pooler URL:

```sql
select tablename, tableowner from pg_tables where schemaname = 'public' order by 1;
select current_user, rolbypassrls from pg_roles where rolname = current_user;
show server_version;
```

| Check | Result (2026-09-25) |
|---|---|
| Owner of every `public` table | `postgres` |
| `current_user`, `rolbypassrls` | `postgres`, `true` |
| `server_version` (its major also goes in "Platform limits") | `17.6` |
| RLS safe: `current_user` owns every table or has BYPASSRLS | Yes (both) |

**3. Lockdown applied.**

| Action | Result | Date |
|---|---|---|
| (a) Dashboard → Project Settings → Data API: off | Already off before Step 0; left off. REST and GraphQL requests with the anon key return HTTP 503 `PGRST002` and no data. | 2026-09-25 |
| (b) Enable RLS on every `public` table (the `DO` block below) | Applied | 2026-09-25 |
| (b) The two REVOKEs from `anon` and `authenticated`, and the two `ALTER DEFAULT PRIVILEGES` (below) | Applied | 2026-09-25 |

```sql
-- Defense in depth; slice 1's 0003_lockdown repeats this idempotently.
DO $$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public REVOKE ALL ON SEQUENCES FROM anon, authenticated;
```

If step 2 said "no", skip the `DO` block: RLS with no policies would hide every
row from both apps. Apply (a) and the REVOKEs only; slice 1 decides between
transferring table ownership and adding policies (ops spec, Risks item 1).

**4. Confirmation.**

| Check | Result | Date |
|---|---|---|
| Step-1 curls with the anon key: no rows | HTTP 503 `PGRST002`, no rows | 2026-09-25 |
| Step-1 curls with your access token: no rows | Not run: the Data API is off for every role | 2026-09-25 |
| GraphQL introspection lists no app tables (no `usersCollection`) | HTTP 503 `PGRST002`, no data | 2026-09-25 |
| `/me` works on https://worship-service-builder.vercel.app | Yes: the Vercel app loads the owner's church | 2026-09-25 |
| https://liturgy-stg.streamlit.app loads the owner's church | Yes | 2026-09-25 |
| Incident response needed (step 1 returned rows)? | No: the Data API was already off | 2026-09-25 |

GraphQL check:

```
curl -s -X POST https://tbecmwtitsoxzkrvxxxu.supabase.co/graphql/v1 \
  -H "apikey: <anon key>" -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { queryType { fields { name } } } }"}'
```

**Rollback:** `ALTER TABLE public.<t> DISABLE ROW LEVEL SECURITY` for each
table, and turn the Data API back on. The REVOKEs need no rollback, because no
app uses those roles.

## Backups

- **Workflow:** `.github/workflows/backup.yml` (`db-backup`). Daily at 08:37 UTC,
  and by hand from `main`: Actions → db-backup → Run workflow (branch `main`),
  or `gh workflow run db-backup --ref main`.
- **What it does:** checks the server's Postgres major against `PG_MAJOR`,
  dumps the `public` schema with `pg_dump --format=custom --no-owner
  --no-privileges`, pipes it through `age` to every key in
  `.github/backup/age-recipients.txt`, and uploads
  `backup-<UTC timestamp>.dump.age` as the artifact `db-backup`, kept 30 days.
  No plaintext dump touches the runner's disk. Supabase-managed schemas
  (`auth`, `storage`) are not included; users sign in again with Google and are
  matched by email.
- **Secret:** `BACKUP_DATABASE_URL`, an **environment secret** of the GitHub
  Environment `backup` (repo Settings → Environments → `backup`), whose
  deployment-branch rule admits only `main`, so a workflow on any other branch
  cannot read it. There is no repository secret of that name. The value is
  the Supabase **session pooler** URL the apps use. The direct host is
  IPv6-only on Free and GitHub runners are IPv4. The SQLAlchemy form
  (`postgresql+psycopg2://…`) is fine: `.github/backup/pg_env.py` reads the
  URL as the app does, masks each part in the log (password, user, host,
  whole URL), and hands the parts to `psql` and `pg_dump` as `PG*` variables,
  so the URL never reaches a command line. The secret is added only after the
  encrypted workflow is on `main`; until then every run fails at "Check
  prerequisites", which is intended. Scheduled runs use `main`; a manual run
  from any other branch is refused by the environment.
- **Artifacts** are encrypted, so it is acceptable that anyone signed in to
  GitHub can download them from this public repo.

### Key custody

1. Created once with `brew install age`, then `age-keygen -o ~/wsb-backup-key.txt`.
2. The whole key file is stored in the owner's password manager, plus one
   offline copy; then the file is deleted from disk.
3. The private key never goes to GitHub, Railway, the repo or chat. Only the
   `age1…` public line is committed, in `.github/backup/age-recipients.txt`.
4. Every public key in that file can decrypt every new backup. An optional
   second recovery key, stored apart from the first, protects against losing
   the first.

| Key | Where the private key is kept | Created |
|---|---|---|
| [owner: first 12 characters of the `age1…` public key] | [owner: password manager entry name; offline copy location] | [owner] |

### Rotating the key

1. Generate and store the new key as in "Key custody".
2. PR: add its `age1…` line to `.github/backup/age-recipients.txt` next to the
   old one. After merging, run db-backup by hand and decrypt that artifact
   with the new key (restore drill, first two commands).
3. PR: remove the old line. Keep the old private key for 30 more days, until
   the last artifact encrypted to it has expired, then destroy every copy.
4. If a private key is exposed: remove its line at once, delete the existing
   `db-backup` artifacts (Actions → db-backup → each run → Artifacts), and run
   db-backup by hand so a fresh backup exists under the remaining keys.

### Restore drill (once in the ops slice, then quarterly)

```
cd "$(mktemp -d)"                                            # a fresh, empty folder
gh run download <run-id> -R bbrown62450/church -n db-backup  # or download from the Actions UI
ls backup-*.dump.age                                         # exactly one file: use its full name below
# Save the whole key file from the password manager as ~/wsb-backup-key.txt, then:
age --decrypt -i ~/wsb-backup-key.txt -o backup.dump backup-<timestamp>.dump.age
docker run --rm -d --name wsb-restore -e POSTGRES_PASSWORD=restore postgres:17
until docker exec wsb-restore pg_isready -h 127.0.0.1 -U postgres; do sleep 1; done
docker exec -i wsb-restore pg_restore -h 127.0.0.1 -U postgres -d postgres --no-owner --no-privileges < backup.dump
docker exec wsb-restore psql -h 127.0.0.1 -U postgres -Atc "select 'users', count(*) from users union all select 'churches', count(*) from churches union all select 'services', count(*) from services union all select 'hymns', count(*) from hymns"
docker stop wsb-restore
rm -f backup.dump ~/wsb-backup-key.txt backup-*.dump.age     # the plaintext dump holds Gmail refresh tokens; the key never stays on disk
```

- Use an image tag at least as new as the server major (`PG_MAJOR`).
- The wait uses TCP (`-h 127.0.0.1`) because the image first runs a temporary,
  socket-only server for initdb and then restarts; a socket connection can hit
  that temporary server and be cut off in the middle of the restore.
- Expected: at most the harmless `schema "public" already exists` error, and
  every table restored.
- Run the same count query on production (Supabase SQL editor) and compare.
  Rows written between the dump and the check are the only allowed difference.

| Date | Run | Artifact | Counts: restored / production (users, churches, services, hymns) | Result |
|---|---|---|---|---|
| [owner] | [owner: run URL] | [owner: backup-….dump.age] | [owner] | [owner] |

### Backup run record

| Date | Run | Result |
|---|---|---|
| [owner: first manual run after ops-1] | [owner: run URL] | [owner: green; artifact `backup-*.dump.age`; the log shows no URL or password] |

## Streamlit freeze

### Streamlit apps

The ops spec names `liturgy` as production and deletes `liturgy-stg`. The
owner corrected this on 2026-09-25: it is the other way round.

| App | URL | Status |
|---|---|---|
| `liturgy-stg` | https://liturgy-stg.streamlit.app/ | **Production.** The owner and the tester use it. Deploys from repo `bbrown62450/church`, main file `app.py`, branch [owner: branch shown in Streamlit Cloud → Settings, and the date checked]. The Freeze step moves it to `streamlit-frozen`, and `keep-awake` keeps it awake. |
| `liturgy` | https://liturgy.streamlit.app/ | **Unused.** Its Google sign-in fails with `StreamlitAuthError` (its secrets config). The Freeze step deletes it and removes its two Google redirect URIs (`https://liturgy.streamlit.app/oauth2callback` and the bare root `https://liturgy.streamlit.app/`). |

### Streamlit bug triage

Every Streamlit bug in the inventory, checked against the freeze policy's
definition of a data-safety fix: data loss, corruption, leakage or security.
"Stored data" means rows in the database; losing text typed but not yet saved
is a usability bug, not a data-safety one.

| Inventory | Bug | Meets the definition? | Disposition |
|---|---|---|---|
| D5, and F6 "drops a loaded service's own hymns" | With "Exclude hymns used in the last 12 weeks" ticked, Prepare records the picks and reruns; the picks are now "recent", `safe_hymn_selectbox` resets them to '', and the next Prepare or Save stores no hymns. Loading a recent archived service with the box ticked drops its hymns, and "Save changes" then overwrites the archived hymns. | **Yes: silent loss of stored data in the normal Prepare → Save flow** | **Fixed in ops-1** (below). Until the fix is live, the tester relies on the D5 workaround message; the date it was sent is in the D5 record below. |
| A7 | A Word file prepared for church A can be downloaded or emailed while church B is active, to church B's contacts. | Leakage, in principle | **Accepted.** The tester belongs to one church, and Streamlit offers no way to join or create a second one (onboarding runs only at zero churches, inv A5), so the switcher never renders (the pre-freeze smoke check confirms there is no "Church" selectbox in the sidebar). React keys the draft and documents by church (slice 2, 5a). |
| E6 | Raw provider error text, or the "[Configure OPENAI_API_KEY…]" placeholder, becomes the liturgy text and can be saved or printed. | Corruption, in principle | **Accepted.** The Preview shows the text before Prepare or Save, so it is never saved silently, and Streamlit blocks Generate entirely when no key is set (inv E6). The new app shows such stored text as ordinary text and never writes error text itself (F §6.2). |
| E4 | Generate replaces the liturgy wholesale, so an unticked section of a loaded service disappears, and "Save changes" then overwrites it. | Loss, but visible | **Accepted.** The section is visibly missing from the Preview before Save, and the loaded text is still in its "Your text" box, so ticking the section and generating again restores it verbatim (inv E2). |
| D6 | With no Opening hymn, the Response hymn is stored first and reloads into the Opening slot. | Corruption of the slot order, visible | **Accepted.** It happens only when Opening is left empty, and the shifted slot is visible in the pickers before the next Save. The new app always writes three positional entries (F §6.2). |
| F6 | A hymn renamed or deleted in Settings is silently dropped when a service that used it is loaded; the next Save stores it without that hymn. | Loss, rare and visible | **Accepted.** It needs a hymn rename or delete, and the empty slot is visible before Save. |
| F7 | Last write wins; any member can overwrite any service. | Loss under concurrent edits | **Accepted.** One person uses the app. `If-Match` arrives in 5a. |
| F10 | All recipients go in one visible To header. | Contacts see each other's addresses | **Accepted.** This is the behavior the tester already relies on, and the recipients are the church's own contacts. 5b moves them to BCC (owner decision 9). |
| D3, D7, E6, F9 | Member-editable hymn titles and links rendered as unescaped markdown; configuration details and raw exception text shown to members. | Security, low | **Accepted.** Only signed-in members of the tester's own church can write hymns or see these messages. The React UI escapes and uses fixed messages (F §1.5, §4.8). |
| G7, G8, B1 | Admins can grant owner; the role is not validated on invites; code-only invites can be reused. | Security | **Accepted** by F §6.2, because the owner is the tester. 6b fixes them. |
| F4 | Usage is recorded on Prepare and never removed; the check-then-insert can race. | Stale data, not loss | **Accepted** by F §6.2. 5a replaces usage per date on save. |
| B2, G2 | Timezones are free text. | No | Not data-safety. Slices 1, 2 and 6a validate them. |
| C1, C4 | No readings, or a reading-set switch, overwrites the occasion and scriptures typed but not yet saved. | No (nothing stored is touched) | Not data-safety. |
| G5 | On Postgres, hymns with no number beyond the first 50 can't be seen or deleted in Settings. | No (nothing is lost) | Not data-safety. 6a replaces the page. |
| inv §4 | The Data API exposed the tables; backups were unencrypted. | Security | **Fixed in ops** (Step 0, S2), outside the Streamlit code. Step 0 (2026-09-25) found the Data API already off, and added RLS and the REVOKEs. |
| inv §4 | Gmail refresh tokens are stored in plaintext. | Security | **Deferred to slice 7** (F §6.4), because the frozen app reads them. The lockdown and the encrypted backups remove the exposure paths. |

### D5 fix and recovery record

ops-1 adds `ui_helpers.hymn_options_excluding_recent`, which `app.py` uses when
"Exclude hymns used in the last 12 weeks" is ticked: hymns already picked in the
three slots stay selectable, so Prepare, Save and loading a recent service no
longer clear them. Recent hymns that are not picked stay hidden.

| Event | Date |
|---|---|
| D5 workaround message sent to the tester | [owner: date, or "not sent" and why] |
| ops-1 build live on https://liturgy-stg.streamlit.app/ | [owner] |
| D5 manual check passed on https://liturgy-stg.streamlit.app/ | [owner] |
| "Fixed" message sent to the tester | [owner] |

**Recovery queries** (Supabase SQL editor, after the fix is live).

1. Archived services saved without hymns:

```sql
select church_id, service_date_iso, occasion, saved_at from services
where case when hymns is null or jsonb_typeof(hymns::jsonb) <> 'array' then true
           else jsonb_array_length(hymns::jsonb) = 0 end
order by service_date_iso desc;
```

2. Services that lost some of their hymns. Loading an older archived service
   with the box ticked clears only the slots whose hymn is recent, so "Save
   changes" can store one or two hymns. `hymn_usage` keeps what was recorded
   when the service was prepared, so a service that stores fewer hymns than
   its usage rows (at most 3) is a candidate. It also lists query 1's rows
   that have usage, and a service whose picks were changed between two
   Prepares can show up without having lost anything, so ask before re-saving.

```sql
select s.church_id, s.service_date_iso, s.occasion, s.saved_at,
       case when jsonb_typeof(s.hymns::jsonb) = 'array' then jsonb_array_length(s.hymns::jsonb) else 0 end as stored,
       count(u.id) as used
from services s
left join hymn_usage u on u.church_id = s.church_id and u.date_iso = s.service_date_iso
group by s.id
having least(count(u.id), 3) >
       case when jsonb_typeof(s.hymns::jsonb) = 'array' then jsonb_array_length(s.hymns::jsonb) else 0 end
order by s.service_date_iso desc;
```

For each row of either query, this lists the hymns picked when the service was prepared:

```sql
select hymn_number, hymn_title from hymn_usage
where church_id = '<church_id>' and date_iso = '<service_date_iso>';
```

Ask the tester whether the service really had no hymns, or only the ones it
stores. If hymns are missing, the tester loads it, picks them again and clicks
"Save changes".

Result: [owner: "no rows" for both queries, or per row: the query, the date, the hymns `hymn_usage` lists, the tester's answer, and whether the service was re-saved]

## Platform limits

- Railway public networking: a request is closed after 5 minutes with no data
  transferred, and can run up to 15 minutes while data keeps flowing
  (https://docs.railway.com/networking/public-networking/specs-and-limits,
  checked 2026-09-25). F §1.8 needs at least 120 s: OK. Never add a test
  endpoint that sleeps.
- Postgres server major: 17
- Postgres `server_version`: 17.6 (2026-09-25)
- The `Postgres server major` line is read by
  `backend/tests/test_ops_workflows.py`, which fails unless it equals
  `PG_MAJOR` in `.github/workflows/backup.yml`. Change both together; the
  backup job also refuses to run when the server major differs.
- Supabase session pooler (Supavisor) Pool Size: 15 (Nano compute; max client
  connections 200), 2026-09-25 (Dashboard → Database → Connection pooling).
- Budget (ops spec, Risks item 2): 2 × (`DB_POOL_SIZE` + `DB_MAX_OVERFLOW`) + 2
  must not exceed the Pool Size; the 2 is the backup job's one session plus
  the owner's SQL editor. The spec's 5 + 5 needs 22 > 15, so the trigger
  fired. The values are `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3`:
  2 × (3 + 3) + 2 = 14 ≤ 15. `backend/.env.example` says the same.
- Hand-off to ops-2: the engine's code defaults must be 3 and 3, not the
  spec's 5 and 5.
- Until ops-2 merges, no code reads these variables: `backend/db/engine.py`
  sets no pool size, so each process can hold SQLAlchemy's default 5 + 10 = 15
  sessions. The API, `liturgy-stg` and (until it is deleted) `liturgy` can
  together ask for 45 against 15. Real use by one tester is 2–4. Deleting
  the unused `liturgy` app frees its share.
- Values set: `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3` as Railway service
  variables (API), and as top-level keys `DB_POOL_SIZE = "3"` and
  `DB_MAX_OVERFLOW = "3"` in the `liturgy-stg` app's Streamlit Secrets (not
  `liturgy`, which is being deleted): [owner: date set]
- GitHub Actions artifacts: `db-backup` keeps 30 days (GitHub's maximum is 90).

## Incident response

Only if Step 0, step 1 returned rows. Do it the same day (Supabase Free keeps
logs for a short time). Steps 1–3 come before any repair.

1. **Preserve evidence.** Take an encrypted dump before changing any row; it
   never exists in plaintext. First load the pooler URL into `PG*` variables
   (the `read` and `eval` lines in "Supabase lockdown record"), then:
   ```
   docker run --rm -e PGHOST -e PGPORT -e PGUSER -e PGPASSWORD -e PGDATABASE \
       -e PGSSLMODE=require postgres:17 pg_dump --schema=public --format=custom \
     | age --encrypt -r <your age1… public key> > incident-$(date -u +%Y%m%dT%H%M%SZ).dump.age
   unset PGHOST PGPORT PGUSER PGPASSWORD PGDATABASE
   ```
   Use an image tag at least as new as the server major. Keep the file
   offline next to the key, not in the repo or in GitHub.
2. **Review the API logs.** Dashboard → Logs → API: list the `/rest/v1` and
   `/graphql/v1` requests you didn't make, especially `POST`, `PATCH` and
   `DELETE`, with dates, methods, paths and IPs.
3. **Check for tampering** in every table the default grants let a caller
   write:
   - `users`, every row: compare `email`, `google_sub`, `name` and
     `created_at` with the known users. Identity is matched by email, so a
     changed `users.email` on the owner's row hands the owner's memberships to
     whoever signs in with that address. Look for rows created for people you
     don't know.
   - `memberships` (unexpected rows or roles) and `invites` (unexpected rows,
     especially with the admin or owner role).
   - `contacts`: unexpected recipients (bulletins are emailed to them).
   - `churches`: `name`, `settings` and `deleted_at`.
   - `services`, `hymns`, `hymn_usage`, `hymn_catalog`: rows or edits you
     don't recognize (`services.saved_at` shows recent writes).
   - `gmail_tokens`: recently changed rows.
   - Purge `oauth_states`: `DELETE FROM oauth_states;` (a state is valid for
     10 minutes, so the only cost is restarting a Gmail connect in progress).
4. **Repair** from the forensic dump or the known values: a changed
   `users.email` first, before anyone signs in again; then memberships,
   contacts and settings.
5. Revoke every active invite in Streamlit Settings → Invites and reissue
   those still needed (invite codes are bearer secrets).
6. Send the tester the Gmail message (ops spec, User experience): remove the
   app's access at https://myaccount.google.com/permissions, then "Connect
   your Gmail" again.
7. Record everything below.

### Incident record

None: the Data API was already off (2026-09-25). REST and GraphQL requests
with the anon key returned HTTP 503 `PGRST002` and no rows, so the owner
recorded no incident and no incident steps were needed.
````

If the owner has already given the Task 0 answers (workaround message date, `liturgy-stg` branch), write them in place of those two markers now; otherwise Task 9, Step 2 fills them.

- [ ] **Step 4: Rewrite the README "Backups" paragraph**

`README.md:151-156` currently reads:

```markdown
### Backups (required)

Supabase Free retains no backups. `.github/workflows/backup.yml` runs a daily
`pg_dump` and uploads the compressed dump as a build artifact. Artifacts are
short-lived — for durable retention, extend the job to push the dump to object
storage.
```

Replace it with:

```markdown
### Backups (required)

Supabase Free retains no backups. `.github/workflows/backup.yml` (`db-backup`)
runs daily at 08:37 UTC: it dumps the `public` schema with `pg_dump` (custom
format, client major matched to the server), encrypts the dump with `age` to
the public keys in `.github/backup/age-recipients.txt` before anything is
written to disk, and uploads `backup-<timestamp>.dump.age` as an artifact kept
30 days. Only the owner's `age` private key can open it. The job reads the
Supabase session-pooler URL from `BACKUP_DATABASE_URL`, a secret of the GitHub
Environment `backup` that only `main` can use, added only after the encrypted
workflow is on `main`. Key custody, key rotation and the restore drill are in
`docs/ops-runbook.md` → Backups.
```

Leave "Keep-alive (required)" and the rest of the README unchanged (ops-3 and slice 7).

- [ ] **Step 5: Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_docs.py
grep -c '^- Postgres server major:' docs/ops-runbook.md
.venv/bin/python -m pytest -q | tail -1
```
Expected: `64 passed` (61 in `test_ops_workflows.py`, 3 in `test_docs.py`), then `1`, then `275 passed`.

- [ ] **Step 6: Commit**

```bash
git add docs/ops-runbook.md README.md backend/tests/test_ops_workflows.py
git commit -m "Add the ops runbook and document encrypted backups in the README

The runbook holds the Supabase lockdown record (Step 0, done 2026-09-25),
backup key custody, key rotation and the restore drill, the Streamlit apps
(liturgy-stg is production; liturgy is unused), the bug triage and D5
recovery record, platform limits (Postgres 17.6, whose major PG_MAJOR must
match; pooler Pool Size 15 and the 3 + 3 pool budget) and incident response.
The remaining [owner: …] markers are values still pending.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Backup recipients file (the owner's `age` public key)

The spec requires that a test enforces the recipient format, so that a placeholder cannot merge. This task writes a clearly marked placeholder, watches the guard reject it, and then puts the owner's real public key in its place (OWNER step) before committing.

**Files:**
- Create: `.github/backup/age-recipients.txt`
- Test: `backend/tests/test_ops_workflows.py` (append)

**Interfaces:**
- Consumes: `ROOT`, `_read(path)`, `AGE_RECIPIENT`, `re` from `test_ops_workflows.py` (Task 5).
- Produces: `.github/backup/age-recipients.txt`, which contains `#` comments plus one or more `age1…` lines. `backup.yml` reads it with `--recipients-file`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ops_workflows.py`:

```python


# --- .github/backup/age-recipients.txt ----------------------------------------

RECIPIENTS = ROOT / ".github" / "backup" / "age-recipients.txt"
# A real age private key: the prefix, "1", then 58 upper-case Bech32 characters.
# A bare mention of the prefix (the ops spec has one) is not a key.
AGE_SECRET_KEY = re.compile(r"AGE-SECRET-KEY-1[02-9AC-HJ-NP-Z]{58}")


def test_age_recipients_lists_only_real_recipients():
    # Raw lines, as age reads them: it skips only empty lines and lines starting
    # with "#", so a stray space makes a key "malformed" at run time.
    entries = [line for line in _read(RECIPIENTS).splitlines()
               if line != "" and not line.startswith("#")]
    assert entries, "no age recipient in .github/backup/age-recipients.txt"
    bad = [line for line in entries if not AGE_RECIPIENT.match(line)]
    assert bad == [], (
        "every non-comment line must be an age1… public key; replace the placeholder "
        f"with the owner's key (ops-1 plan, Task 7, OWNER step): {bad}"
    )


def test_secret_key_pattern_matches_a_key_but_not_a_mention():
    fake_key = "AGE-SECRET-KEY-1" + "Q" * 58   # built at runtime so no key-shaped literal exists
    assert AGE_SECRET_KEY.search(f"# created: today\n{fake_key}\n")
    assert not AGE_SECRET_KEY.search("no file under .github/ or docs/ contains `AGE-SECRET-KEY-`.")


def test_no_age_private_key_is_committed_under_github_or_docs():
    leaks = [
        str(path.relative_to(ROOT))
        for base in (".github", "docs")
        for path in sorted((ROOT / base).rglob("*"))
        if path.is_file() and AGE_SECRET_KEY.search(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert leaks == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py`
Expected: `1 failed, 63 passed`. `test_age_recipients_lists_only_real_recipients` fails with `FileNotFoundError` for `.github/backup/age-recipients.txt`.

- [ ] **Step 3: Create the recipients file with the marked placeholder**

Create `.github/backup/age-recipients.txt`:

```
# age public keys ("recipients") for the encrypted database backups made by
# .github/workflows/backup.yml. One age1… key per line; every key listed can
# decrypt every new backup. Public keys only: the private keys stay in the
# owner's password manager (docs/ops-runbook.md → Backups → Key custody).
# backend/tests/test_ops_workflows.py rejects any other non-comment line.
OWNER-REPLACES-THIS-LINE-WITH-THEIR-age1-PUBLIC-KEY
```

The comment stays true after Step 6 replaces the placeholder, so it needs no second edit.

- [ ] **Step 4: Watch the guard reject the placeholder**

Run: `.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py::test_age_recipients_lists_only_real_recipients`
Expected: FAIL, `AssertionError: every non-comment line must be an age1… public key; replace the placeholder with the owner's key (ops-1 plan, Task 7, OWNER step): ['OWNER-REPLACES-THIS-LINE-WITH-THEIR-age1-PUBLIC-KEY']`

- [ ] **Step 5 (OWNER): Hand over the `age` public key from Task 0, Step 3**

The key pair had not been generated as of 2026-09-25; the owner generates it in Task 0, Step 3 (`brew install age`, `age-keygen`, whole file into the password manager plus an offline copy, then deleted from disk). Here the agent collects what that step produced, if it has not already: the `age1…` public line(s), the password-manager entry name, the offline copy's location and the creation date. The agent receives **only** those: never the key file and never its `AGE-SECRET-KEY-…` line.

- [ ] **Step 6: Replace the placeholder with the owner's key**

In `.github/backup/age-recipients.txt`, replace the line `OWNER-REPLACES-THIS-LINE-WITH-THEIR-age1-PUBLIC-KEY` with a comment line and the key line (one pair per key the owner gave):

```
# primary backup key (owner), created <YYYY-MM-DD>
<the age1… public key exactly as the owner gave it>
```

In `docs/ops-runbook.md` → Backups → Key custody, replace the table row's three `[owner: …]` markers with: the first 12 characters of each public key, the password-manager entry name and the offline copy's location (as the owner states them), and the creation date.

Then check that the workflow's own guard accepts the file:

```bash
grep -Eq '^age1[02-9ac-hj-np-z]{58}$' .github/backup/age-recipients.txt && echo "recipient ok"
```
Expected: `recipient ok`

**If the key from Task 0, Step 3 has still not arrived when Task 8 starts:** commit the file with the placeholder (message `Add backup recipients file (placeholder until the owner adds the age key)`), then continue with Task 8 and open the PR as a **draft**. CI will fail on exactly `test_age_recipients_lists_only_real_recipients`, which is the intended merge block. Do Steps 6–8 on the branch when the key arrives, and mark the PR ready only after that.

- [ ] **Step 7: Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py
.venv/bin/python -m pytest -q | tail -1
```
Expected: `64 passed`, then `278 passed`.

- [ ] **Step 8: Commit**

```bash
git add .github/backup/age-recipients.txt backend/tests/test_ops_workflows.py docs/ops-runbook.md
git commit -m "Add the owner's age public key as the backup recipient

A test rejects any non-comment line that is not an age1… public key and
scans .github/ and docs/ for anything shaped like an age private key.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Full verification and the ops-1 pull request

**Files:** none changed (verification and PR only)

**Interfaces:**
- Consumes: everything from Tasks 1–7.
- Produces: an open PR `claude/ops-1-backups-cleanup-d5` → `main`, with green CI.

- [ ] **Step 1: Run the whole backend suite and the acceptance checks**

```bash
.venv/bin/python -m pytest -q | tail -1
grep -rnwE '(email_send|notion_archive|notion_usage|select_sunday_hymns|add_hymnary_links|fix_hymn_titles)' --include='*.py' backend app.py streamlit_* ui_helpers.py; echo "grep exit $?"
ls backend/cache.py backend/tests/test_cache.py 2>&1 | grep -c "No such file"
git diff --stat origin/main...HEAD -- backend/api backend/db backend/repos backend/auth.py backend/keepalive.py .github/workflows/keepalive.yml .github/workflows/keep-awake.yml .github/workflows/ci.yml
```
Expected: `278 passed`; no grep matches and `grep exit 1`; `2`; the last command prints nothing, because ops-1 touches none of the ops-2/ops-3 files.

- [ ] **Step 2: Run the frontend checks one more time**

```bash
(cd frontend && npm ci && npm run lint && npm run typecheck && npm test && \
  NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co \
  NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder \
  NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build)
```
Expected: all four pass as in Task 4, Step 5.

- [ ] **Step 3: Check the `[owner: …]` markers left for the owner**

Run: `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked'`
Expected (the `grep -v` drops the runbook's own explanation of the marker): at most these 9 lines, and nothing from the Supabase lockdown record, the Railway, `server_version` or Pool Size lines, or the Incident record, which are pre-filled:
- before merge (Task 9): the `liturgy-stg` branch in "Streamlit apps" and the "D5 workaround message sent" row (both absent if the Task 0 answers were already written in Task 6), and the pool "Values set" line;
- after merge (Tasks 10–12): the D5 rows "ops-1 build live", "D5 manual check passed" and "Fixed message sent", the recovery "Result", the backup run record row and the restore drill row.
The key-custody row is filled (Task 7), unless the Task 7 placeholder contingency applies.

- [ ] **Step 4: Push and open the PR (get the owner's go-ahead first)**

```bash
git add docs/superpowers/plans/2026-09-25-ops-1-backups-cleanup-d5.md
git commit -m "Add the ops-1 implementation plan

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" || true   # "nothing to commit" is fine if it is already committed
git push -u origin claude/ops-1-backups-cleanup-d5
gh pr create --base main --head claude/ops-1-backups-cleanup-d5 \
  --title "ops-1: Streamlit D5 fix, encrypted backups, dead-code and config cleanup" \
  --body "PR ops-1 of the ops slice (docs/superpowers/specs/2026-09-25-slice-ops-cleanup-design.md; plan docs/superpowers/plans/2026-09-25-ops-1-backups-cleanup-d5.md).

- Streamlit data-safety fix (S16, inv D5): with 'Exclude hymns used in the last 12 weeks' ticked, hymns already picked are no longer cleared by Prepare, Save or loading a recent service. Goes live on merge on the production Streamlit app liturgy-stg (https://liturgy-stg.streamlit.app), which deploys from main (branch checked in plan Task 0, Step 2).
- backup.yml rewritten (S2): BACKUP_DATABASE_URL as a secret of the GitHub Environment backup (main only); .github/backup/pg_env.py masks each part of the URL and hands psql/pg_dump PG* variables, never a URL; actions pinned to commit SHAs; pg_dump matched to PG_MAJOR, age-encrypted before upload (backup-*.dump.age, 30 days). The environment and secret are added only after this merges.
- Deleted six dead modules (S4); backend/.env.example gains APP_ENV, LOG_LEVEL, DB_POOL_SIZE=3, DB_MAX_OVERFLOW=3 (Supavisor Pool Size 15: 2 x (3+3) + 2 = 14), ESV_API_KEY (S5); shadcn moved to devDependencies (S6).
- docs/ops-runbook.md: Step 0 lockdown record (done 2026-09-25, no incident), backups (key custody, rotation, restore drill), Streamlit apps (liturgy-stg is production, liturgy unused), bug triage and D5 recovery, platform limits, incident response. README Backups paragraph.
- Tests: +72 (278 total).

Owner steps before merge: plan Task 9. After merge: Tasks 10-12 (D5 check and recovery query, tester message, the backup environment and BACKUP_DATABASE_URL, manual backup run, restore drill).

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks --watch
```
Expected: the `backend` and `frontend` checks pass, and the Vercel preview deployment for the PR reports success. If the placeholder contingency in Task 7 applies, add `--draft` to `gh pr create`; `backend` then fails only on `test_age_recipients_lists_only_real_recipients`.

---

### Task 9 (OWNER, before merge): pool values, remaining records, Vercel settings, merge

Step 0 and the platform limits are already recorded (Task 6 wrote the owner's 2026-09-25 results into the runbook), so the owner is not asked for them again. Three pre-merge values remain. The owner reads dashboards and passes the values to the agent; the agent edits `docs/ops-runbook.md` and commits. No secret is ever pasted into chat or the runbook.

**Files:**
- Modify: `docs/ops-runbook.md` (the pre-merge `[owner: …]` markers)

**Interfaces:**
- Consumes: the Task 0 answers, Railway and Streamlit Cloud settings, the Vercel project settings.
- Produces: a runbook whose remaining `[owner: …]` markers are only the post-merge ones (D5 live/check/"fixed" rows, the recovery result, the backup run record, the restore drill row).

- [ ] **Step 1 (OWNER): Set the pool values in both apps**

The Supavisor Pool Size is 15, and 2 × (3 + 3) + 2 = 14 ≤ 15 (runbook → Platform limits). Set these now; they are harmless before ops-2 (today's engine ignores them) and must be in place before ops-2 merges:
- Railway → the API service → Variables: `DB_POOL_SIZE=3` and `DB_MAX_OVERFLOW=3`. Saving redeploys the API.
- Streamlit Cloud → `liturgy-stg` → ⋮ → Settings → Secrets: add the top-level keys `DB_POOL_SIZE = "3"` and `DB_MAX_OVERFLOW = "3"` above the first `[section]` header (Streamlit Cloud exposes top-level secrets as environment variables). Saving can restart the app, so do it when the tester is not using it. Not the `liturgy` app: it is unused and will be deleted.

- [ ] **Step 2 (OWNER → agent): Give the agent the remaining pre-merge values**

Only what the runbook does not have yet:
- the date the D5 workaround message was sent (Task 0, Step 1), or "not sent" and why;
- `liturgy-stg`'s deploy branch and the date checked (Task 0, Step 2), plus the decision if it is not `main`;
- the date the pool values were set (Step 1).

The agent replaces the matching markers: the "D5 workaround message sent" row, the `liturgy-stg` branch in "Streamlit apps", and the pool "Values set" line.

- [ ] **Step 3: Confirm the settled Step 0 items (no owner action)**

Both stop rules were settled on 2026-09-25: Railway allows 5 minutes idle and up to 15 minutes while data flows, above the 120 s F §1.8 needs, and the server is 17.6, so `PG_MAJOR: "17"` and the runbook line already agree. Nothing changes; check it:

```bash
grep -n '^- Postgres server major' docs/ops-runbook.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py
```
Expected: `<line>:- Postgres server major: 17`, then `64 passed`.

- [ ] **Step 4: Commit the records and push**

```bash
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked'
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: record the D5 workaround date, liturgy-stg branch and pool values

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```
Expected: `grep` lists only the 6 post-merge marker lines: three rows of the D5 table ("ops-1 build live", "D5 manual check passed", "Fixed message sent"), the D5 recovery "Result", the backup run record row and the restore drill row. The key-custody row (Task 7) and everything in the lockdown record, Platform limits and Incident record are filled. Then `278 passed`.

- [ ] **Step 5 (OWNER): Check the Vercel install settings and the preview build**

In Vercel → the `worship-service-builder` project → Settings → Build and Deployment, the Install Command is the default, or a command without `--omit=dev`. In Settings → Environment Variables there is no `NPM_CONFIG_PRODUCTION`. On the PR, the Vercel preview deployment is "Ready". Open it and sign in once.

- [ ] **Step 6 (OWNER): Approve and merge**

The owner reviews the PR. All CI checks must be green and every task above must be done. Merging is outward-facing: merge only on the owner's explicit yes:

```bash
gh pr merge --merge claude/ops-1-backups-cleanup-d5
```

Do **not** create the `backup` environment's `BACKUP_DATABASE_URL` secret before this merge completes.

---

### Task 10 (OWNER, after merge): D5 check on liturgy-stg, recovery queries, tester message

**Files:**
- Modify (by the agent, from the owner's results): `docs/ops-runbook.md` → "D5 fix and recovery record" (committed in Task 12, Step 5)

- [ ] **Step 1: Confirm both apps redeployed from the merge**

- Streamlit Cloud → `liturgy-stg` (the production app; `liturgy` is unused and is not checked) → ⋮ → Settings still shows branch `main` (or the branch decided in Task 0, Step 2, which must now contain the D5 commit), and Manage app → logs show a new build that started after the merge commit landed and finished. https://liturgy-stg.streamlit.app/ loads. Step 2 is the functional proof that this build has the fix.
- Vercel → Deployments: the Production deployment for the merge commit is "Ready". At 375 px (Chrome device mode, iPhone SE) and on desktop, on https://worship-service-builder.vercel.app: sign in, the church shows in the switcher, switch church if you have two, log out. (Acceptance criterion 8.)

Record the date `liturgy-stg` went live ("ops-1 build live").

- [ ] **Step 2: Run the D5 manual check in a throwaway church**

This keeps usage rows out of the tester's church. On https://liturgy-stg.streamlit.app/:
1. Sign in with a second Google account that has no church. Create a church named "Ops test" (its hymnal is seeded from the catalog).
2. Tick "Exclude hymns used in the last 12 weeks". Pick three hymns (Opening, After sermon, Closing).
3. Click "Generate liturgy" and wait for the Preview (the Prepare and Save buttons appear only after the liturgy is generated). **The three picks are still selected.**
4. Click "Prepare bulletin copy". **The three picks are still selected.**
5. Click "Prepare pastor's copy". Download both Word files: **both list the three hymns.**
6. Click "Save this service to archive". Load it again from the archive with the box still ticked: **its three hymns are in the slots** (the button now reads "Save changes").
7. Delete "Ops test" in Settings → Danger zone and sign out.

Any bolded check that fails means the fix is not working: stop and report it; do not send the "fixed" message.

- [ ] **Step 3: Run the recovery queries**

In the Supabase SQL editor, run both queries from `docs/ops-runbook.md` → Streamlit freeze → "D5 fix and recovery record": query 1 (services saved with no hymns) and query 2 (services that store fewer hymns than their `hymn_usage` rows, which catches the partial loss from loading an older service with one or two recent hymns). Query 1:

```sql
select church_id, service_date_iso, occasion, saved_at from services
where case when hymns is null or jsonb_typeof(hymns::jsonb) <> 'array' then true
           else jsonb_array_length(hymns::jsonb) = 0 end
order by service_date_iso desc;
```

Query 2:

```sql
select s.church_id, s.service_date_iso, s.occasion, s.saved_at,
       case when jsonb_typeof(s.hymns::jsonb) = 'array' then jsonb_array_length(s.hymns::jsonb) else 0 end as stored,
       count(u.id) as used
from services s
left join hymn_usage u on u.church_id = s.church_id and u.date_iso = s.service_date_iso
group by s.id
having least(count(u.id), 3) >
       case when jsonb_typeof(s.hymns::jsonb) = 'array' then jsonb_array_length(s.hymns::jsonb) else 0 end
order by s.service_date_iso desc;
```

For each row returned by either query:

```sql
select hymn_number, hymn_title from hymn_usage
where church_id = '<church_id>' and date_iso = '<service_date_iso>';
```

Ask the tester whether that service really had no hymns (query 1) or only the ones it stores (query 2; a service whose picks were changed between two Prepares can show up without having lost anything). If hymns are missing, the tester loads it, picks them again (with the list from `hymn_usage`) and clicks "Save changes".

- [ ] **Step 4: Send the tester the "fixed" message (exact copy)**

Only after Step 2 passed:

> The hymn problem is fixed: "Exclude hymns used in the last 12 weeks" no longer clears hymns you've already picked, so you can leave it ticked. If a service you saved recently shows no hymns, tell me its date and I'll tell you which hymns you had picked.

- [ ] **Step 5: Give the agent the results**

Pass on these dates: live, check passed, and message sent. Also pass on the recovery result: "no rows" for both queries, or for each row the query, the date, the `hymn_usage` hymns, the tester's answer and whether it was re-saved. The agent fills the four remaining D5 markers in Task 12, Step 5.

---

### Task 11 (OWNER, after merge): Create the `backup` environment, add `BACKUP_DATABASE_URL`, and run the backup by hand

- [ ] **Step 1: Confirm the encrypted workflow and a real recipient are on `main`**

```bash
git fetch origin
git show origin/main:.github/workflows/backup.yml | grep -c 'age --encrypt'
git show origin/main:.github/workflows/backup.yml | grep -c '^    environment: backup'
git show origin/main:.github/backup/age-recipients.txt | grep -Ec '^age1[02-9ac-hj-np-z]{58}$'
```
Expected: `1`, `1`, then `1` or more. If any is `0`, stop: the secret must not be added yet.

- [ ] **Step 2 (OWNER only): Create the `backup` environment and add the secret to it**

The secret goes in a GitHub Environment whose deployment-branch rule admits only `main`, so a workflow pushed to any other branch cannot read it. It is never a repository secret.

1. GitHub → `bbrown62450/church` → Settings → Environments. If `backup` is already listed (a scheduled run since the merge creates it automatically, with no rules), open it; otherwise New environment → Name: `backup` → Configure environment.
2. Deployment branches and tags: choose "Selected branches and tags" (older UI: "Selected branches") → Add deployment branch or tag rule → Ref type: Branch, Name pattern: `main` → Add rule. Add no other rule.
3. Environment secrets → Add environment secret:
   - Name: `BACKUP_DATABASE_URL`
   - Value: the Supabase **session pooler** URL with the database password. This is the same value as Railway's `DATABASE_URL`: Supabase Dashboard → Connect → Session pooler. The `postgresql+psycopg2://` form is fine.

   Alternatively, after item 2, run `gh secret set BACKUP_DATABASE_URL --env backup -R bbrown62450/church` in your own terminal and paste the value at its prompt. Never paste it into chat.
4. Settings → Secrets and variables → Actions → Repository secrets must not list `BACKUP_DATABASE_URL`. If it does, delete it: a repository secret is readable from every branch.

Check (no secret value is shown):

```bash
gh api repos/bbrown62450/church/environments/backup --jq '.deployment_branch_policy'
gh api repos/bbrown62450/church/environments/backup/deployment-branch-policies --jq '.branch_policies[] | "\(.type) \(.name)"'
gh secret list --env backup -R bbrown62450/church
gh secret list -R bbrown62450/church | grep -c BACKUP_DATABASE_URL
```
Expected: `{"custom_branch_policies":true,"protected_branches":false}`, then exactly `branch main`, then a line starting with `BACKUP_DATABASE_URL`, then `0`.

Scheduled runs use the default branch, `main`, so they satisfy the rule. Manual runs must be dispatched from `main` (Step 3 does); a run from any other branch is refused before the job starts.

- [ ] **Step 3: Run the workflow by hand**

```bash
gh workflow run db-backup --ref main
sleep 5; gh run list --workflow db-backup --limit 1
gh run watch <run-id> --exit-status
```
Expected: the run completes with success (the server was 17.6 on 2026-09-25, matching `PG_MAJOR: "17"`). If Supabase has since upgraded and it fails with `::error::Postgres server major is N but PG_MAJOR is M; update PG_MAJOR in backup.yml`, open a small PR from `origin/main` that changes `PG_MAJOR`, `SERVER_MAJOR` in `backend/tests/test_ops_workflows.py`, the runbook's major and `server_version` lines and the `postgres:` image tags together, merge it on the owner's yes, and run again:

```bash
N=18   # the major from the error message (example value)
sed -i '' "s/PG_MAJOR: \"17\"/PG_MAJOR: \"$N\"/" .github/workflows/backup.yml
sed -i '' "s/^SERVER_MAJOR = \"17\"/SERVER_MAJOR = \"$N\"/" backend/tests/test_ops_workflows.py
sed -i '' "s/^- Postgres server major: 17\$/- Postgres server major: $N/; s/postgres:17/postgres:$N/g" docs/ops-runbook.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py   # 64 passed
```
(On Linux use `sed -i` without `''`. Update the `server_version` line by hand from `show server_version;`.)

- [ ] **Step 4: Check the artifact and the log**

```bash
gh run view <run-id>
gh run view <run-id> --log | grep -Ei 'postgres(ql)?(\+[a-z0-9_]+)?://|pooler\.supabase\.com|password'; echo "grep exit $?"
```
Expected: the `ARTIFACTS` section lists `db-backup`; the grep prints nothing and `grep exit 1` (no URL, host or password in the log; GitHub shows the secret as `***`).

- [ ] **Step 5: Give the agent the run record**

Pass on the date, the run URL and "green; artifact `backup-<ts>.dump.age`; log shows no URL or password" for the runbook's "Backup run record" (filled in Task 12, Step 5).

---

### Task 12 (OWNER, after merge): Restore drill, and the records PR

Requires Docker, `age` (`brew install age`) and `gh` on the owner's machine.

- [ ] **Step 1: Put the key file on disk temporarily**

From the password manager, save the whole key file as `~/wsb-backup-key.txt` (it is deleted again in Step 3).

- [ ] **Step 2: Run the drill**

In a fresh, empty directory (outside the repo, so `gh` needs `-R`):

```bash
cd "$(mktemp -d)"
gh run download <run-id from Task 11> -R bbrown62450/church -n db-backup
ls backup-*.dump.age                      # exactly one file
age --decrypt -i ~/wsb-backup-key.txt -o backup.dump backup-<timestamp>.dump.age
docker run --rm -d --name wsb-restore -e POSTGRES_PASSWORD=restore postgres:17
until docker exec wsb-restore pg_isready -h 127.0.0.1 -U postgres; do sleep 1; done
docker exec -i wsb-restore pg_restore -h 127.0.0.1 -U postgres -d postgres --no-owner --no-privileges < backup.dump
docker exec wsb-restore psql -h 127.0.0.1 -U postgres -Atc "select 'users', count(*) from users union all select 'churches', count(*) from churches union all select 'services', count(*) from services union all select 'hymns', count(*) from hymns"
docker stop wsb-restore && rm backup.dump
```
(Use the `postgres:<N>` tag matching `PG_MAJOR` if it is not 17.)

Expected: `pg_restore` reports at most `schema "public" already exists`. The count query prints four lines such as `users|3`.

Now run the same query on production (Supabase SQL editor):

```sql
select 'users', count(*) from users union all select 'churches', count(*) from churches
union all select 'services', count(*) from services union all select 'hymns', count(*) from hymns;
```

The counts match. The only allowed difference is rows written between the dump and this check.

- [ ] **Step 3: Remove plaintext and key material**

In the same temporary directory:

```bash
rm -f ~/wsb-backup-key.txt backup.dump
rm -f backup-*.dump.age
```
The downloaded `.dump.age` is encrypted, but it is not needed after the drill. Run this even if Step 2 failed part-way, so the key never stays on disk.

- [ ] **Step 4: Give the agent the drill record**

Pass on the date, the run URL, the artifact name, the restored and production counts for users, churches, services and hymns, and the result (pass/fail).

- [ ] **Step 5 (agent): Record the after-merge results in a docs-only PR**

```bash
git fetch origin
git switch -c claude/ops-1-records origin/main
```

Edit `docs/ops-runbook.md`, replacing the remaining `[owner: …]` markers with the values from Tasks 10–12: the D5 table's three dates and the recovery "Result", "Backup run record", and the "Restore drill" row. Then:

```bash
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked'; echo "grep exit $?"
.venv/bin/python -m pytest -q | tail -1
git add docs/ops-runbook.md
git commit -m "Runbook: record the D5 check, first encrypted backup and restore drill

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin claude/ops-1-records
gh pr create --base main --head claude/ops-1-records \
  --title "Runbook: ops-1 after-merge records" \
  --body "Fills the ops-1 after-merge records in docs/ops-runbook.md: D5 manual check and recovery result, first encrypted backup run, restore drill.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```
Expected: no marker lines and `grep exit 1`, then `278 passed`. Merge after the owner's yes. The ops-1 gate is then passed, and ops-2 can start.

---

## Spec coverage

| Spec item / acceptance criterion (ops-1 share) | Task |
|---|---|
| S16: D5 fix, `ui_helpers.hymn_options_excluding_recent`, `app.py:735-746` `keep` set (built by `picked_hymn_keys`, clarification 9), own first commit, may ship as a separate PR | 1 |
| D5 fix goes live on the production Streamlit app: `liturgy-stg` deploys from `main` (owner correction 1) | 0 (Step 2), 10 (Step 1) |
| Testing → `streamlit_tests/test_app_helpers.py`: A,B recent with A kept → `["a","c"]`; empty keep → `["c"]`; non-recent always present; kept key missing from hymnal not added; D5 regression with `tmp_db`, `make_church`, `record_usage`, `get_recently_used_identifiers`, `coerce_selectbox_value` | 1 |
| Behavior change 17 (picked hymns stay selectable; unpicked recent stay hidden) | 1 |
| S4: delete the six modules; Testing → `test_foundation_setup.py` "none of the six exists"; AC 6 whole-word grep finds nothing | 2, 8 |
| Behavior change 15 (six dead modules removed; the `upsert_user` part is ops-2) | 2 |
| S5: `backend/.env.example` block after `CORS_ORIGINS`; `OPENAI_MODEL` untouched; Testing → the five keys, plus `DB_POOL_SIZE=3` / `DB_MAX_OVERFLOW=3` (owner correction 3); AC 7 | 3 |
| S6: `shadcn` to devDependencies (moved by hand plus `npm install`, clarification 8), lockfile committed with no version changed; Testing → `package.json` parsed as JSON; Frontend → CI checks pass | 4, 8 |
| Frontend: Vercel has no `--omit=dev` install and no `NPM_CONFIG_PRODUCTION`; preview build and production deploy succeed; AC 8 (sign-in at 375 px) | 9 (Step 5), 10 (Step 1) |
| S2: `backup.yml` exactly as specified (cron, `ubuntu-24.04`, `PG_MAJOR`, prerequisites, PGDG client, version check, `pg_dump | age`, size check, artifact settings), with fix round 1: `environment: backup`, SHA-pinned actions, URL parts masked and passed as `PG*` variables instead of `normalize-pg-url.sh` | 5 |
| S2 URL handling: `.github/backup/pg_env.py` replaces the spec's `normalize-pg-url.sh` (fix round 1: parsed as SQLAlchemy does, one escaped `::add-mask::` per part, `PG*` exports for `eval`, URL on stdin only, generic error with no input echoed) | 5 |
| Exact copy: the three `backup.yml` `::error::` messages | 5 |
| Testing → `test_ops_workflows.py` `backup.yml` contains / does not contain lists, plus checks of the parsed YAML (fix round 1) | 5 |
| Testing → URL handling (replaces the three `normalize-pg-url.sh` cases): the scheme forms, tricky passwords decoded exactly as SQLAlchemy does, escaped masks, `--exports` evaluated in bash, malformed URLs rejected without echo, run as `.github/backup/pg_env.py` from the repo root | 5 |
| Testing → `PG_MAJOR` parsed as YAML equals the runbook's `- Postgres server major: <N>` line | 5 (parse), 6 (runbook check) |
| Testing → a `postgres:<N>` image in `ci.yml` (`jobs.*.services.*.image`, parsed) must equal `PG_MAJOR` (inert until slice 1) | 5 |
| S2: `.github/backup/age-recipients.txt`, comments plus `age1…` lines; test enforces format so a placeholder cannot merge | 7 |
| Testing → `age-recipients.txt` exists, at least one recipient, every entry matches; no age private key under `.github/` or `docs/` (clarification 1) | 7 |
| Backups → key setup (owner): `age-keygen`, password manager plus offline copy, file deleted, optional second key, public line to the PR (not yet generated on 2026-09-25) | 0 (Step 3), 7 (Steps 5-6) |
| Backups → Order: 1 merge with real recipients → 2 add `BACKUP_DATABASE_URL` → 3 manual run → 4 restore drill | 9 (Step 6), 11, 12 |
| Backups → restore drill (commands, TCP wait, expected output, compare counts) | 6 (runbook), 12 |
| S15 (ops-1 share): runbook sections for the lockdown record, backups (key custody, schedule, restore drill, rotation), Streamlit apps, bug triage and D5 record, platform limits with the exact `- Postgres server major:` line, incident response | 6 |
| S15 (ops-1 share): README "Backups" describes encrypted artifacts, `BACKUP_DATABASE_URL`, and the runbook's key custody and restore drill | 6 |
| S1 / Step 0 record: exposure curls, table owners, BYPASSRLS, `server_version`, lockdown actions, confirmation, GraphQL, incident yes/no (done 2026-09-25: Data API already off, owners `postgres`, BYPASSRLS true, RLS and REVOKEs applied, 17.6, no incident; owner correction 2) | 6 (pre-filled) |
| S12: Railway request limit recorded with source and date; stop rule below 120 s (AC 19): 5 min idle, up to 15 min with data flowing, checked 2026-09-25, so the rule does not fire | 6 (pre-filled), 9 (Step 3) |
| Risks item 2: pooler Pool Size recorded (15, Nano; owner correction 3); trigger 22 > 15 fired; `DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=3` (14 ≤ 15) in `.env.example`, on Railway and in the `liturgy-stg` Secrets before ops-2; interim exposure and the ops-2 3/3 hand-off recorded | 3, 6 (runbook), 9 (Steps 1-2) |
| Streamlit bug triage table recorded in the runbook (AC 25) | 6 |
| After ops-1 is live: D5 manual check in a throwaway church (AC 25; Manual checks) | 10 |
| D5 recovery query run and recorded (AC 25), plus the partial-loss query (clarification 10) | 6 (runbook), 10, 12 (Step 5) |
| Tester "fixed" message, exact copy, only after the check passes (User experience; AC 25) | 10 |
| D5 workaround message sent to the tester and its date recorded (AC 25; not in the owner's list of completed Step 0 items, so checked and, if needed, sent on the owner's yes) | 0 (Step 1), 9 (Step 2) |
| Delivery gate: owner creates the `backup` environment (`main` only) and adds `BACKUP_DATABASE_URL` to it after merge, runs the workflow by hand, the log shows no URL or password (AC 3) | 11 |
| Delivery gate: restore drill restores every table, counts match production (AC 3) | 12 |
| AC 3: `backup.yml` matches the spec and `test_ops_workflows.py` passes with `PG_MAJOR` equal to the runbook's major (17, server 17.6) | 5, 6, 9 (Step 3) |
| AC 23 (ops-1 share): runbook sections filled in | 6, 9, 12 |
| AC 24 (ops-1 share): backend suite and frontend checks green on the ops-1 PR | 8 |
| AC 26: ops-1 creates no `backend/cache.py` or `backend/tests/test_cache.py` | 8 (Step 1) |
| Unchanged-and-green list (`test_auth`, `test_api_me`, `test_api_security`, `test_docs`, `test_ci_workflow`, `test_no_streamlit_in_core`, `test_keepalive`, all `streamlit_tests/`) | every task's full-suite run; 8 |

**Deliberately not in ops-1** (ops spec delivery plan): ops-2 (`db/upsert.py`, `ensure_user`, identity cache, pool and connect-timeout, comment fixes, `test_identity*.py`, `test_upsert.py`, `test_engine.py` additions); ops-3 (middleware, `request_id`, CORS lists, `redirect_slashes`, logging, startup guards, `/health/ready`, `keepalive.yml`, deleting `keepalive.py` and `test_keepalive.py`, the `keepalive.yml` / `keep-awake.yml` workflow tests, the `errors.ts` check, the `app.py` FROZEN header, `keep-awake.yml`, README keep-alive, the `docs/manual-verification.md` "Ops slice" section, and the runbook's environments, keep-alive and freeze-record sections); the Freeze step (cut `streamlit-frozen`, protect it, redeploy `liturgy-stg` from it; retire and delete the unused `liturgy` app and remove its redirect URIs; `keep-awake` pings only https://liturgy-stg.streamlit.app/; owner correction 1 reverses the spec's app names).
